#define _QNX_SOURCE 1
#include <sys/neutrino.h>
#include <sys/iomsg.h>
#include <sys/dcmd_all.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "../../native/spikes/phase2.h"
#include "../../native/fixtures/mailbox_protocol.h"
#include "../../native/fixtures/control_v1.h"

static int failures;
static void check(const char *name,int observed,int expected) {
    int matched=observed==expected;failures+=!matched;
    printf("{\"case\":\"%s\",\"observed\":%d,\"expected\":%d,\"matched\":%s}\n",name,observed,expected,matched?"true":"false");
}
static int raw(int fd,const void *input,size_t length,size_t reply) {
    unsigned char out[256]={0};uint64_t bound=1000000000;
    if (TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&bound,NULL)==-1) return errno;
    int rc=MsgSend(fd,input,length,out,reply);return rc==-1 ? errno:rc;
}
static int worker(const char *path,pid_t expected_pid) {
    uint64_t until=mono_ns()+2000000000;int fd=-1;
    while (mono_ns()<until) { fd=open(path,O_RDWR);if (fd>=0) break;struct timespec pause={0,10000000};nanosleep(&pause,NULL); }
    if (fd<0) return 2;
    int ro=open(path,O_RDONLY);if (ro<0) { close(fd);return 2; }
    struct mailbox_state before={0},after={0};
    check("state-baseline",devctl(fd,MAILBOX_STATE,&before,sizeof(before),NULL),0);
    check("initial-message-custody",before.message_exists==1 && before.message_ready==1 && before.acknowledgements==0 && before.pending==0,1);
    struct mailbox_identity identity={0};
    check("readonly-service-identity",devctl(ro,MAILBOX_IDENTITY,&identity,sizeof(identity),NULL),0);
    const char *tag=strrchr(path,'/');tag=tag?tag+1:path;
    check("same-owned-service-identity",identity.protocol==1 && identity.pid==(uint32_t)expected_pid && !strcmp(identity.instance,tag),1);
    io_devctl_t header={0};header.i.type=_IO_DEVCTL;header.i.combine_len=sizeof(header.i);header.i.dcmd=MAILBOX_STATE;
    header.i.nbytes=1;check("wrong-state-size",raw(fd,&header.i,sizeof(header.i),256),EINVAL);
    header.i.nbytes=sizeof(before);check("short-state-reply",raw(fd,&header.i,sizeof(header.i),8),EMSGSIZE);
    struct { io_devctl_t header;struct mailbox_result body;uint32_t surplus; } packet={0};
    packet.header.i.type=_IO_DEVCTL;packet.header.i.combine_len=sizeof(packet.header.i);packet.header.i.dcmd=MAILBOX_FETCH;packet.header.i.nbytes=sizeof(packet.body);packet.body.channel=1;
    check("truncated-fetch",raw(fd,&packet,sizeof(packet.header.i),256),EINVAL);
    check("surplus-fetch",raw(fd,&packet,sizeof(packet.header.i)+sizeof(packet.body)+4,256),EINVAL);
    struct mailbox_result result={.channel=1,.reserved=1};
    check("reserved-fetch",devctl(fd,MAILBOX_FETCH,&result,sizeof(result),NULL),EINVAL);
    result=(struct mailbox_result){.channel=2};check("unregistered-channel",devctl(fd,MAILBOX_FETCH,&result,sizeof(result),NULL),ENOENT);
    struct mailbox_ack ack={.channel=1,.generation=before.generation};
    check("readonly-ack",devctl(ro,MAILBOX_ACK,&ack,sizeof(ack),NULL),EBADF);
    ack.reserved=1;check("reserved-ack",devctl(fd,MAILBOX_ACK,&ack,sizeof(ack),NULL),EINVAL);
    ack.reserved=0;ack.generation=before.generation+1;check("stale-generation-ack",devctl(fd,MAILBOX_ACK,&ack,sizeof(ack),NULL),ESTALE);
    check("rejected-input-state-query",devctl(fd,MAILBOX_STATE,&after,sizeof(after),NULL),0);
    check("rejections-preserve-state",memcmp(&before,&after,sizeof(before))==0,1);
    ack.generation=before.generation;check("explicit-ack",devctl(fd,MAILBOX_ACK,&ack,sizeof(ack),NULL),0);
    check("ack-state-query",devctl(fd,MAILBOX_STATE,&after,sizeof(after),NULL),0);
    check("ack-consumes-only-message",after.message_exists==0 && after.message_ready==0 && after.pending==0 && after.acknowledgements==1 && after.generation==before.generation,1);
    check("duplicate-ack",devctl(fd,MAILBOX_ACK,&ack,sizeof(ack),NULL),ENOENT);
    check("new-generation-arm",devctl(fd,MAILBOX_ARM,&after,sizeof(after),NULL),0);
    check("new-generation-publish",devctl(fd,MAILBOX_PUBLISH,&after,sizeof(after),NULL),0);
    result=(struct mailbox_result){.channel=1};check("fresh-client-fetch",devctl(ro,MAILBOX_FETCH,&result,sizeof(result),NULL),0);
    check("fresh-message-result",result.value==7 && result.channel==1 && result.reserved==0 && after.acknowledgements==1 && after.generation==before.generation+1,1);
    close(ro);close(fd);return failures?1:0;
}
static int reap(pid_t pid,int *status,uint64_t deadline) {
    while (mono_ns()<deadline) {
        pid_t result=waitpid(pid,status,WNOHANG);
        if (result==pid) return 1;
        if (result<0) return -1;
        struct timespec delay={0,10000000};nanosleep(&delay,NULL);
    }
    return 0;
}
int main(int argc,char **argv) {
    if (argc!=5 || strcmp(argv[3],"mailbox")) return 2;
    setvbuf(stdout,NULL,_IONBF,0);
    /* Even the preoccupied-device stat stays in an owned bounded worker. */
    pid_t preflight=fork();
    if (preflight==0) {
        struct stat existing;
        _exit(lstat(argv[2],&existing)<0 && errno==ENOENT ? 0:2);
    }
    if (preflight<0) return 2;
    int preflight_status=0,preflight_state=reap(preflight,&preflight_status,mono_ns()+1000000000);
    int preflight_good=preflight_state==1 && WIFEXITED(preflight_status) && WEXITSTATUS(preflight_status)==0;
    if (preflight_state==0) { kill(preflight,SIGKILL);preflight_state=reap(preflight,&preflight_status,mono_ns()+1000000000); }
    printf("{\"preflight_waitpid_observed\":%s,\"preflight_status\":%d}\n",preflight_state==1?"true":"false",preflight_status);
    if (!preflight_good) return 2;
    int log=open(argv[4],O_WRONLY|O_CREAT|O_EXCL,0600);if (log<0) return 2;
    pid_t fixture=fork();if (fixture==0) {
        const char *identity=strrchr(argv[2],'/');identity=identity ? identity+1:argv[2];
        if (setenv("RMC_RUN_ID",identity,1) || setenv("RMC_CASE_ID","input-bounds",1) ||
            setenv("RMC_INSTANCE_ID",identity,1) || setenv("RMC_ATTEMPT_ID","attempt1",1) ||
            setenv("RMC_CYCLE","1",1) || setenv("RMC_LAB_CONTROL","none",1)) _exit(2);
        dup2(log,STDOUT_FILENO);dup2(log,STDERR_FILENO);close(log);
        execl(argv[1],argv[1],argv[2],"corrected",NULL);_exit(127);
    }
    close(log);if (fixture<0) return 2;
    pid_t probe=fork();
    if (probe==0) _exit(worker(argv[2],fixture));
    int status=0,probe_state=probe>0 ? reap(probe,&status,mono_ns()+8000000000) : -1;
    int passed=probe_state==1 && WIFEXITED(status) && WEXITSTATUS(status)==0;
    if (probe_state==1) printf("{\"owned_probe_pid\":%ld,\"waitpid_observed\":true,\"status\":%d}\n",(long)probe,status);
    /* Only direct unreaped fork children are signalled. Unknown wait status is
     * neither live ownership nor permission to signal a possibly reused PID. */
    int fixture_status=0,fixture_state=reap(fixture,&fixture_status,mono_ns()+1000000);
    if (fixture_state!=0) passed=0;
    if (fixture_state==0) {
        int rc=kill(fixture,SIGTERM);printf("{\"owned_fixture_pid\":%ld,\"signal\":%d,\"rc\":%d}\n",(long)fixture,SIGTERM,rc);
        fixture_state=reap(fixture,&fixture_status,mono_ns()+1000000000);
        if (fixture_state==0) { kill(fixture,SIGKILL);fixture_state=reap(fixture,&fixture_status,mono_ns()+1000000000); }
    }
    if (probe_state==0) {
        kill(probe,SIGKILL);probe_state=reap(probe,&status,mono_ns()+1000000000);
    }
    printf("{\"fixture_waitpid_observed\":%s,\"probe_waitpid_observed\":%s,\"fixture_status\":%d,\"passed\":%s}\n",fixture_state==1?"true":"false",probe_state==1?"true":"false",fixture_status,passed && fixture_state==1?"true":"false");
    return passed && fixture_state==1 ? 0:2;
}
