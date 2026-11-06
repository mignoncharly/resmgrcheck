#include "persistence.h"
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <errno.h>

static int run_fd=-1;
static uint64_t started_ns;
int rmc_is_persistent(void) { return run_fd!=-1; }

int rmc_status_write(const rmc_plan *p, const char *state, int cleanup_ok,
                     int exit_code, cJSON *unresolved) {
    if (run_fd==-1) { cJSON_Delete(unresolved); return 1; }
    cJSON *status=json_object(); add_string(status,"kind","run-status");
    add_number(status,"schema_version",1); add_identity(status);
    add_decimal(status,"supervisor_pid",getpid()); add_decimal(status,"started_ns",(int64_t)started_ns);
    add_string(status,"state",state);
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
