#include "persistence.h"
#include "lab.h"
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <errno.h>
#include <ctype.h>
#include <limits.h>

static int run_fd=-1;
static uint64_t started_ns;
static const char *event_file="events.jsonl";
void rmc_status_event_file(const char *name) { event_file=name; }
int rmc_run_file(const char *name) {
    return run_fd<0 ? -1 : openat(run_fd,name,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
}
int rmc_is_persistent(void) { return run_fd!=-1; }

int rmc_status_write(const rmc_plan *p, const char *state, int cleanup_ok,
                     int exit_code, cJSON *unresolved) {
    if (run_fd==-1) { cJSON_Delete(unresolved); return 1; }
    cJSON *status=json_object(); add_string(status,"kind","run-status");
    add_number(status,"schema_version",1); add_identity(status);
    add_decimal(status,"supervisor_pid",getpid()); add_decimal(status,"started_ns",(int64_t)started_ns);
    add_string(status,"state",state);
    add_string(status,"event_file",event_file);
    add_string(status,"lab_control",rmc_lab_name());
    if (!cJSON_AddBoolToObject(status,"cleanup_ok",cleanup_ok)) _exit(120);
    add_number(status,"exit_code",exit_code);
    add_string(status,"profile_sha256",json_string(p->root,"profile_sha256"));
    add_string(status,"source_tree_sha256",json_string(cJSON_GetObjectItemCaseSensitive(p->root,"builds"),"source_tree_sha256"));
    if (!cJSON_AddItemToObject(status,"unresolved",unresolved)) _exit(120);
    char *text=cJSON_PrintUnformatted(status); cJSON_Delete(status);
    if (!text) _exit(120);
    size_t n=strlen(text);
    int fd=openat(run_fd,".status.next",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    if (fd==-1) { cJSON_free(text); return 0; }
    int ok=write(fd,text,n)==(ssize_t)n && write(fd,"\n",1)==1 && fsync(fd)==0;
    cJSON_free(text);
    if (close(fd)) ok=0;
    if (ok && renameat(run_fd,".status.next",run_fd,"status.json")) ok=0;
    return ok;
}

static int storage(const rmc_plan *p) {
    const char *base="/data/resmgrcheck/runs";
    if (mkdir(base,0700) && errno!=EEXIST) return 0;
    int base_fd=open(base,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (base_fd==-1) return 0;
    const char *id=json_string(p->root,"run_id");
    if (mkdirat(base_fd,id,0700)) { close(base_fd); return 0; }
    run_fd=openat(base_fd,id,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    close(base_fd);
    if (run_fd==-1) return 0;
    int output=openat(run_fd,"events.jsonl",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    int diagnostic=openat(run_fd,"stderr.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    int input=open("/dev/null",O_RDONLY|O_CLOEXEC);
    if (output==-1 || diagnostic==-1 || input==-1) return 0;
    if (dup2(output,STDOUT_FILENO)==-1 || dup2(diagnostic,STDERR_FILENO)==-1 || dup2(input,STDIN_FILENO)==-1) return 0;
    close(output); close(diagnostic); close(input);
    started_ns=mono_ns();
    cJSON *empty=cJSON_CreateArray(); if (!empty) _exit(120);
    return rmc_status_write(p,"running",0,-1,empty);
}

int rmc_detach_run(const rmc_plan *p) {
    int ack[2];
    if (pipe2(ack,O_CLOEXEC)==-1) return -1;
    pid_t child=fork();
    if (child==-1) { close(ack[0]); close(ack[1]); return -1; }
    struct acknowledgement { pid_t pid; int error; } message={.pid=0,.error=EIO};
    if (child>0) {
        close(ack[1]);
        struct pollfd poller={.fd=ack[0],.events=POLLIN};
        int result=poll(&poller,1,2000);
        ssize_t bytes=result>0 ? read(ack[0],&message,sizeof(message)) : -1;
        close(ack[0]);
        if (bytes!=sizeof(message) || message.error || message.pid!=child) {
            int status; waitpid(child,&status,WNOHANG);
            errno=message.error ? message.error : EIO;
            return -1; /* A timeout requires status inspection; never blind restart. */
        }
        cJSON *started=json_object(); add_string(started,"kind","run-started");
        add_number(started,"schema_version",1); add_identity(started);
        add_decimal(started,"supervisor_pid",child); json_write(started); cJSON_Delete(started);
        return 1;
    }
    close(ack[0]);
    message.pid=getpid();
    int ok=setsid()!=-1 && storage(p);
    message.error=ok ? 0 : errno ? errno : EIO;
    int sent=write(ack[1],&message,sizeof(message))==sizeof(message);
    close(ack[1]);
    if (!ok) _exit(2);
    /* An already detached, bounded run continues even if its start acknowledgement
     * could not reach the launch parent. The exclusive directory resolves ambiguity. */
    (void)sent;
    return 0;
}

static int status_word(const cJSON *o,const char *key,int hash) {
    const char *s=json_string(o,key);
    if (!s || !*s || strlen(s)>(hash ? 64U : 64U) || (hash && strlen(s)!=64)) return 0;
    for (;*s;++s) if (hash ? !strchr("0123456789abcdef",*s) : (!isalnum((unsigned char)*s) && *s!='_' && *s!='-')) return 0;
    return 1;
}
static int status_decimal(const cJSON *o,const char *key) {
    const char *s=json_string(o,key);
    if (!s || !*s || strlen(s)>19 || (s[0]=='0' && s[1])) return 0;
    for (const char *p=s;*p;++p) if (!isdigit((unsigned char)*p)) return 0;
    errno=0;long long n=strtoll(s,NULL,10);return !errno && n>0;
}
static int valid_status(const cJSON *o) {
    const char *keys="kind schema_version run_id case_id attempt_id cycle service_instance_id supervisor_pid started_ns state cleanup_ok exit_code unresolved profile_sha256 source_tree_sha256";
    const char *new_keys="kind schema_version run_id case_id attempt_id cycle service_instance_id supervisor_pid started_ns state cleanup_ok exit_code unresolved profile_sha256 source_tree_sha256 event_file lab_control";
    if (!o || !json_tree(o,0) || (!json_keys(o,keys) && !json_keys(o,new_keys)) || !json_integer(o,"schema_version",1,1,NULL) ||
        !json_string(o,"kind") || strcmp(json_string(o,"kind"),"run-status") || !json_integer(o,"cycle",1,200,NULL) ||
        !status_decimal(o,"supervisor_pid") || !status_decimal(o,"started_ns") ||
        !status_word(o,"run_id",0) || !status_word(o,"case_id",0) || !status_word(o,"attempt_id",0) || !status_word(o,"service_instance_id",0) ||
        !status_word(o,"profile_sha256",1) || !status_word(o,"source_tree_sha256",1) || !json_integer(o,"exit_code",-1,255,NULL) ||
        !cJSON_IsBool(cJSON_GetObjectItemCaseSensitive(o,"cleanup_ok"))) return 0;
    const char *file=json_string(o,"event_file");
    if (file && (strcmp(file,"events.jsonl") && strcmp(file,"recovery.jsonl"))) return 0;
    if (file && !status_word(o,"lab_control",0)) return 0;
    const cJSON *list=cJSON_GetObjectItemCaseSensitive(o,"unresolved");
    if (!cJSON_IsArray(list) || cJSON_GetArraySize(list)>16) return 0;
    for (const cJSON *p=list->child;p;p=p->next) {
        const char *role=json_string(p,"role");
        if (!json_keys(p,"pid role") || !status_decimal(p,"pid") || !role ||
            (strcmp(role,"worker") && strcmp(role,"fixture") && strcmp(role,"manager"))) return 0;
        for (const cJSON *q=list->child;q!=p;q=q->next) if (!strcmp(json_string(p,"pid"),json_string(q,"pid"))) return 0;
    }
    const char *state=json_string(o,"state");
    if (!state) return 0;
    int code=cJSON_GetObjectItemCaseSensitive(o,"exit_code")->valueint;
    int clean=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(o,"cleanup_ok"));
    if (!strcmp(state,"complete")) return clean && !list->child && (code==0 || code==3);
    if (!strcmp(state,"not-run")) return clean && !list->child && code==4;
    if (!strcmp(state,"running")) return code==-1;
    return !strcmp(state,"incomplete") && code==2;
}
int rmc_dependency_clean(const char *id) {
    int base=open("/data/resmgrcheck/runs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (base<0) return -1;
    int dir=openat(base,id,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);close(base);
    if (dir<0) return -1;
    int fd=openat(dir,"status.json",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);close(dir);
    if (fd<0) return -1;
    char bytes[16385];ssize_t n=read(fd,bytes,sizeof(bytes)-1);close(fd);
    if (n<=0 || n==sizeof(bytes)-1) return -1;
    bytes[n]=0;const char *end;
    cJSON *o=cJSON_ParseWithLengthOpts(bytes,(size_t)n+1,&end,1);
    int result=-1;
    if (valid_status(o) && !strcmp(json_string(o,"run_id"),id)) {
        const char *state=json_string(o,"state");
        const cJSON *list=cJSON_GetObjectItemCaseSensitive(o,"unresolved");
        const cJSON *clean=cJSON_GetObjectItemCaseSensitive(o,"cleanup_ok");
        if (state && cJSON_IsArray(list) && cJSON_IsBool(clean)) {
            if (!strcmp(state,"complete") && cJSON_IsTrue(clean) && !list->child) result=1;
            else if (!strcmp(state,"incomplete") && (!cJSON_IsTrue(clean) || list->child)) result=0;
        }
    }
    cJSON_Delete(o);return result;
}
