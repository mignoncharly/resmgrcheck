/* Small file/ownership control surface for the configured owned QNX lab.
 * No process signalling, service calls, recursive removal or arbitrary paths. */
#include "common/plan.h"
#include <sys/stat.h>
#include <sys/utsname.h>
#include <dirent.h>
#include <fcntl.h>
#include <errno.h>
#include <ctype.h>

#define ROOT "/data/resmgrcheck"
#define JSON_LIMIT (1024U*1024U)
static int identifier(const char *s) {
    if (!s || !*s || strlen(s)>64 || !isalnum((unsigned char)*s)) return 0;
    for (;*s;++s) if (!isalnum((unsigned char)*s) && *s!='-' && *s!='_') return 0;
    return 1;
}
static int hash(const char *s) {
    if (!s || strlen(s)!=64) return 0;
    for (;*s;++s) if (!strchr("0123456789abcdef",*s)) return 0;
    return 1;
}
static int owned(int fd,int directory) {
    struct stat st;
    return fd>=0 && !fstat(fd,&st) && st.st_uid==geteuid() && !(st.st_mode&0022) &&
        (directory ? S_ISDIR(st.st_mode) : S_ISREG(st.st_mode));
}
static int dirat(int fd,const char *name,int create) {
    if (create && mkdirat(fd,name,0700) && errno!=EEXIST) return -1;
    int out=openat(fd,name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (!owned(out,1)) { if (out>=0) close(out);return -1; }
    return out;
}
static int write_all(int fd,const char *bytes,size_t n) {
    while (n) { ssize_t k=write(fd,bytes,n);if (k<0 && errno==EINTR) continue;if (k<=0) return 0;bytes+=k;n-=(size_t)k; }
    return 1;
}
static int put(int fd,const char *name,const char *bytes,size_t n) {
    int out=openat(fd,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if (out<0) return 0;
    int ok=write_all(out,bytes,n) && !fsync(out);if (close(out)) ok=0;return ok;
}
static char *read_file(int fd,const char *name,size_t limit,size_t *size) {
    int in=openat(fd,name,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;
    if (!owned(in,0) || fstat(in,&st) || st.st_size<0 || (uint64_t)st.st_size>limit) { if (in>=0) close(in);return NULL; }
    size_t n=(size_t)st.st_size,used=0;char *bytes=malloc(n+1);
    if (!bytes) { close(in);return NULL; }
    while (used<n) { ssize_t k=read(in,bytes+used,n-used);if (k<0 && errno==EINTR) continue;if (k<=0) break;used+=(size_t)k; }
    close(in);if (used!=n) { free(bytes);return NULL; }bytes[n]=0;*size=n;return bytes;
}
static cJSON *document(int fd,const char *name) {
    size_t n;char *bytes=read_file(fd,name,JSON_LIMIT,&n);if (!bytes) return NULL;
    const char *end;cJSON *o=cJSON_ParseWithLengthOpts(bytes,n+1,&end,1);free(bytes);
    if (!o || !json_tree(o,0)) { cJSON_Delete(o);return NULL; }return o;
}
static int marker(int fd,const char *kind,const char *id,const char *binding) {
    cJSON *o=json_object();add_string(o,"kind",kind);add_number(o,"schema_version",1);
    add_string(o,"id",id);add_string(o,"binding",binding);add_number(o,"uid",(int)geteuid());
    char *bytes=cJSON_PrintUnformatted(o);cJSON_Delete(o);if (!bytes) return 0;
    int ok=put(fd,"owner.json",bytes,strlen(bytes));cJSON_free(bytes);return ok;
}
static int marked(int fd,const char *kind,const char *id) {
    cJSON *o=document(fd,"owner.json");
    int ok=o && json_keys(o,"kind schema_version id binding uid") && json_integer(o,"schema_version",1,1,NULL) &&
        json_integer(o,"uid",(int)geteuid(),(int)geteuid(),NULL) && json_string(o,"kind") && !strcmp(json_string(o,"kind"),kind) &&
        json_string(o,"id") && !strcmp(json_string(o,"id"),id) && hash(json_string(o,"binding"));
    cJSON_Delete(o);return ok;
}
static int session_name(const char *name) {
    if (!strcmp(name,"request.json") || !strcmp(name,"owner.json")) return 1;
    const char *suffixes[]={"-plan.json","-launch.json","-ack.json"};
    for (unsigned i=0;i<3;++i) {
        size_t n=strlen(name),k=strlen(suffixes[i]);char first[65];
        if (n>k && n-k<sizeof(first) && !strcmp(name+n-k,suffixes[i])) { memcpy(first,name,n-k);first[n-k]=0;return identifier(first); }
    }
    return 0;
}
static int publish(int base,const char *stage,const char *destination,const char *binding) {
    int source=dirat(base,stage,0);if (!marked(source,"owned-stage",stage)) return 0;
    cJSON *manifest=document(source,"manifest.json");
    const cJSON *files=cJSON_GetObjectItemCaseSensitive(manifest,"files");
    if (!manifest || !json_string(manifest,"kind") || strcmp(json_string(manifest,"kind"),"deployed-build") ||
        !json_string(manifest,"deployment_id") || strcmp(json_string(manifest,"deployment_id"),binding) ||
        !cJSON_IsObject(files) || cJSON_GetArraySize(files)<3 || cJSON_GetArraySize(files)>8) return 0;
    for (const cJSON *v=files->child;v;v=v->next) {
        if (!identifier(v->string) || !json_keys(v,"sha256 bytes") || !hash(json_string(v,"sha256")) || !json_integer(v,"bytes",1,32*1024*1024,NULL)) return 0;
        int file=openat(source,v->string,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);struct stat st;
        int ok=owned(file,0) && !fstat(file,&st) && st.st_nlink==1 && st.st_size==cJSON_GetObjectItemCaseSensitive(v,"bytes")->valueint;
        if (file>=0) close(file);
        if (!ok) return 0;
    }
    /* mkdir is the exclusive publication reservation. Never replace an existing
     * destination, even an empty directory or a matching-looking name. */
    if (mkdirat(base,destination,0700)) return 0;
    int dest=dirat(base,destination,0);if (dest<0) return 0;
    for (const cJSON *v=files->child;v;v=v->next) {
        if (linkat(source,v->string,dest,v->string,0)) return 0;
        int file=openat(dest,v->string,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
        if (!owned(file,0) || fchmod(file,0555)) return 0;
        close(file);
    }
    if (!marker(dest,"published-build",destination,binding)) return 0;
    if (linkat(source,"manifest.json",dest,"manifest.json",0)) return 0;
    int file=openat(dest,"manifest.json",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if (!owned(file,0) || fchmod(file,0444) || fchmodat(base,destination,0555,0)) return 0;
    close(file);close(dest);close(source);cJSON_Delete(manifest);return 1;
}
int main(int argc,char **argv) {
    if (argc==2 && !strcmp(argv[1],"info")) {
        struct utsname u;if (uname(&u)) return 2;
        cJSON *o=json_object();add_string(o,"kind","target-info");add_number(o,"schema_version",1);
        add_number(o,"management_protocol",1);
        add_string(o,"sysname",u.sysname);add_string(o,"release",u.release);add_string(o,"version",u.version);
        add_string(o,"machine",u.machine);add_number(o,"uid",(int)geteuid());
        add_decimal(o,"monotonic_ns",(int64_t)mono_ns());json_write(o);cJSON_Delete(o);return 0;
    }
    int base=open(ROOT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if (!owned(base,1)) return 2;
    int ok=0;
    if (argc==4 && !strcmp(argv[1],"create-stage") && identifier(argv[2]) && hash(argv[3])) {
        if (!mkdirat(base,argv[2],0700)) { int fd=dirat(base,argv[2],0);ok=fd>=0 && marker(fd,"owned-stage",argv[2],argv[3]);if (fd>=0) close(fd); }
    } else if (argc==5 && !strcmp(argv[1],"publish") && identifier(argv[2]) && identifier(argv[3]) && hash(argv[4])) {
        ok=publish(base,argv[2],argv[3],argv[4]);
    } else if (argc==4 && !strcmp(argv[1],"create-session") && identifier(argv[2]) && hash(argv[3])) {
        int parent=dirat(base,"sessions",1);
        if (parent>=0 && !mkdirat(parent,argv[2],0700)) { int fd=dirat(parent,argv[2],0);ok=fd>=0 && marker(fd,"owned-session",argv[2],argv[3]);if (fd>=0) close(fd); }
        if (parent>=0) close(parent);
    } else if (argc==4 && (!strcmp(argv[1],"read-session") || !strcmp(argv[1],"put-session")) && identifier(argv[2]) && session_name(argv[3])) {
        int parent=dirat(base,"sessions",0),fd=parent<0 ? -1 : dirat(parent,argv[2],0);
        if (fd>=0 && marked(fd,"owned-session",argv[2])) {
            if (!strcmp(argv[1],"read-session")) { size_t n;char *bytes=read_file(fd,argv[3],JSON_LIMIT,&n);ok=bytes && write_all(STDOUT_FILENO,bytes,n);free(bytes); }
            else if (strcmp(argv[3],"owner.json")) {
                char *bytes=malloc(JSON_LIMIT+1);size_t n=0;ssize_t got;
                if (bytes) { while (n<=JSON_LIMIT && (got=read(STDIN_FILENO,bytes+n,JSON_LIMIT+1-n))>0) n+=(size_t)got;
                    if (n && n<=JSON_LIMIT) { const char *end;bytes[n]=0;cJSON *o=cJSON_ParseWithLengthOpts(bytes,n+1,&end,1);ok=o && json_tree(o,0) && put(fd,argv[3],bytes,n);cJSON_Delete(o); }free(bytes); }
            }
        }
        if (fd>=0) close(fd);
        if (parent>=0) close(parent);
    } else if (argc==4 && !strcmp(argv[1],"read-run") && identifier(argv[2]) &&
        (!strcmp(argv[3],"status.json") || !strcmp(argv[3],"events.jsonl") || !strcmp(argv[3],"recovery.jsonl") || !strcmp(argv[3],"stderr.log"))) {
        int parent=dirat(base,"runs",0),fd=parent<0 ? -1 : dirat(parent,argv[2],0);
        if (fd>=0) { size_t n;char *bytes=read_file(fd,argv[3],32U*1024U*1024U,&n);ok=bytes && write_all(STDOUT_FILENO,bytes,n);free(bytes);close(fd); }
        if (parent>=0) close(parent);
    } else if (argc==4 && (!strcmp(argv[1],"read-build") || !strcmp(argv[1],"exists")) && identifier(argv[2]) && !strcmp(argv[3],"manifest.json")) {
        int fd=dirat(base,argv[2],0);
        if (fd>=0) {
            struct stat st;
            if (marked(fd,"published-build",argv[2]) && !fstat(fd,&st) && (st.st_mode&0777)==0555) {
                size_t n;char *bytes=read_file(fd,"manifest.json",JSON_LIMIT,&n);
                cJSON *manifest=bytes ? cJSON_ParseWithLength(bytes,n+1) : NULL;
                cJSON *owner=document(fd,"owner.json");
                const char *id=json_string(manifest,"deployment_id"),*binding=json_string(owner,"binding");
                ok=id && binding && !strcmp(id,binding) && (!strcmp(argv[1],"exists") || write_all(STDOUT_FILENO,bytes,n));
                cJSON_Delete(manifest);cJSON_Delete(owner);free(bytes);
            }
            close(fd);
        }
    }
    close(base);if (!ok) { fprintf(stderr,"targetctl: %s rejected (ownership, identity or file check), errno=%d\n",argc>1 ? argv[1] : "command",errno);return 2; }return 0;
}
