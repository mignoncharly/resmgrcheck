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
#include "../../native/fixtures/job_protocol.h"
#include "../../native/fixtures/control_v1.h"

static size_t expected_state_bytes;
static int check(int fd,const char *name,const void *send,size_t size,size_t receive,int expected) {
    union { max_align_t alignment;unsigned char bytes[256]; } storage={0};
    unsigned char *output=storage.bytes;uint64_t bound=1000000000;
    if (TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&bound,NULL)==-1) return 1;
    int raw=MsgSend(fd,send,size,output,receive),error=raw==-1 ? errno : 0;
    int good=expected ? raw==-1 && error==expected : raw==0;
    if (!expected && raw==0) {
        const io_devctl_t *reply=(const io_devctl_t *)output;
        good=good && reply->o.nbytes==expected_state_bytes && !reply->o.ret_val && !reply->o.zero && !reply->o.zero2;
    }
    printf("{\"case\":\"%s\",\"raw\":%d,\"error\":%d,\"expected_error\":%d,\"matched\":%s}\n",name,raw,error,expected,good ? "true":"false");
    return !good;
}
static int get_state(int fd,int job,uint32_t *generation) {
    union { struct sensor_state sensor;struct job_state job; } state={0};
    int error=devctl(fd,job ? JOB_STATE:SENSOR_STATE,&state,job ? sizeof(state.job):sizeof(state.sensor),NULL);
    if (error || (job ? state.job.pending:state.sensor.pending)) return 1;
    *generation=job ? state.job.generation:state.sensor.generation;return 0;
}
static int worker(const char *path,int job) {
    expected_state_bytes=job ? sizeof(struct job_state):sizeof(struct sensor_state);
    int fd=-1;uint64_t limit=mono_ns()+2000000000;
    while (mono_ns()<limit) {
        fd=open(path,O_RDWR);if (fd>=0) break;
        struct timespec delay={0,10000000};nanosleep(&delay,NULL);
    }
    if (fd<0) return 2;
    int ro=open(path,O_RDONLY);if (ro<0) { close(fd);return 2; }
    uint32_t initial=0,final=0;int failures=get_state(fd,job,&initial);
    io_devctl_t header={0};header.i.type=_IO_DEVCTL;header.i.combine_len=sizeof(header.i);
    header.i.dcmd=job ? JOB_STATE:SENSOR_STATE;
    header.i.nbytes=job ? sizeof(struct job_state):sizeof(struct sensor_state);
    failures+=check(fd,"state-baseline",&header.i,sizeof(header.i),256,0);
    header.i.nbytes=1;failures+=check(fd,"wrong-declared-size",&header.i,sizeof(header.i),256,EINVAL);
    header.i.nbytes=job ? sizeof(struct job_state):sizeof(struct sensor_state);
    failures+=check(fd,"short-reply-buffer",&header.i,sizeof(header.i),8,EMSGSIZE);
    struct { io_devctl_t header;struct rmc_fixture_command command;uint32_t excess; } packet={0};
    packet.header.i.type=_IO_DEVCTL;packet.header.i.combine_len=sizeof(packet.header.i);
    packet.header.i.dcmd=RMC_FIXTURE_COMMAND;packet.header.i.nbytes=sizeof(packet.command);
    packet.command.action=RMC_HOLD_NEXT;
    failures+=check(fd,"truncated-control",&packet,sizeof(packet.header.i),256,EINVAL);
    failures+=check(fd,"surplus-control",&packet,sizeof(packet.header.i)+sizeof(packet.command)+4,256,EINVAL);
    failures+=check(ro,"readonly-control",&packet,sizeof(packet.header.i)+sizeof(packet.command),256,EBADF);
    packet.command.action=0;
    failures+=check(fd,"unknown-control-action",&packet,sizeof(packet.header.i)+sizeof(packet.command),256,EINVAL);
    header.i.dcmd=job ? JOB_SUBMIT:SENSOR_HOLD;
    failures+=check(ro,"readonly-mutation",&header.i,sizeof(header.i),256,EBADF);
    /* No custom operation may run as a nonfinal combine component. */
    union { max_align_t alignment;unsigned char data[2064]; } combined={0};
    memcpy(combined.data,&packet,sizeof(packet.header.i)+sizeof(packet.command));
    io_devctl_t *first=(io_devctl_t *)combined.data;
    first->i.combine_len=(sizeof(first->i)+sizeof(packet.command))|_IO_COMBINE_FLAG;
    ((struct rmc_fixture_command *)(combined.data+sizeof(first->i)))->action=RMC_HOLD_NEXT;
    header.i.dcmd=job ? JOB_STATE:SENSOR_STATE;
    memcpy(combined.data+sizeof(first->i)+sizeof(packet.command),&header.i,sizeof(header.i));
    failures+=check(fd,"combined-custom-framework-rejection",combined.data,sizeof(first->i)+sizeof(packet.command)+sizeof(header.i),256,EBADMSG);
    /* This QNX framework rejects GETFLAGS as an intermediate response-bearing
     * component. Observe EBADMSG; do not claim the custom tail was executed. */
    memset(&combined,0,sizeof(combined));first=(io_devctl_t *)combined.data;
    first->i.type=_IO_DEVCTL;first->i.combine_len=2016|_IO_COMBINE_FLAG;
    first->i.dcmd=DCMD_ALL_GETFLAGS;first->i.nbytes=sizeof(int);
    memcpy(combined.data+2016,&header.i,sizeof(header.i));
    failures+=check(fd,"combined-prefix-framework-rejection",combined.data,2016+sizeof(header.i),256,EBADMSG);
    if (job) {
        struct { io_devctl_t header;struct job_result value; } message={0};
        message.header.i.type=_IO_DEVCTL;message.header.i.combine_len=sizeof(message.header.i);
        message.header.i.dcmd=JOB_WAIT_RESULT;message.header.i.nbytes=sizeof(message.value);
        message.value.job_id=1;message.value.reserved=1;
        failures+=check(fd,"reserved-job-input",&message,sizeof(message.header.i)+sizeof(message.value),256,EINVAL);
        message.value.reserved=0;message.value.job_id=2;
        failures+=check(fd,"unknown-job",&message,sizeof(message.header.i)+sizeof(message.value),256,ENOENT);
        failures+=check(fd,"truncated-job-input",&message,sizeof(message.header.i),256,EINVAL);
    } else {
        io_read_t read_message={0};read_message.i.type=_IO_READ;read_message.i.combine_len=sizeof(read_message.i);read_message.i.nbytes=10;
        failures+=check(fd,"truncated-read-framework-rejection",&read_message,4,256,EBADMSG);
        failures+=check(fd,"short-read-buffer",&read_message,sizeof(read_message.i),1,EMSGSIZE);
    }
    failures+=get_state(fd,job,&final);failures+=initial!=final;
    close(fd);close(ro);
    int fresh=open(path,O_RDONLY);
    if (fresh<0) return 2;
    uint32_t fresh_generation=0;failures+=get_state(fresh,job,&fresh_generation);failures+=fresh_generation!=initial;
    if (job) {
        struct job_result result={.job_id=1};
        int error=devctl(fresh,JOB_WAIT_RESULT,&result,sizeof(result),NULL);
        failures+=error || result.value!=420 || result.job_id!=1 || result.reserved;
    } else {
        char data[64]={0};ssize_t size=read(fresh,data,sizeof(data));
        failures+=size!=(ssize_t)strlen(SAMPLE) || memcmp(data,SAMPLE,strlen(SAMPLE));
    }
    close(fresh);
    printf("{\"case\":\"same-instance-fresh-client\",\"initial_generation\":%u,\"final_generation\":%u,\"fresh_generation\":%u,\"failures\":%d}\n",initial,final,fresh_generation,failures);
    return failures ? 1:0;
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
    if (argc!=5 || (strcmp(argv[3],"sensor") && strcmp(argv[3],"job"))) return 2;
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
    if (probe==0) _exit(worker(argv[2],!strcmp(argv[3],"job")));
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
