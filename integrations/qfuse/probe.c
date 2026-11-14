/* SPDX-License-Identifier: MIT
 * Original test filesystem/harness; the independently authored QFuse backend
 * is linked unchanged. No ABI1 adapter or general external lifecycle claim.
 */
#define FUSE_USE_VERSION 31
#include <fuse.h>
#include <qfuse/admin.h>
#include <sys/neutrino.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static pid_t owner, service, client;
static int notice[2], release_callback[2], finish_client[2];
static char mountpoint[128];
static void cleanup(void) {
    if (getpid() != owner) return;
    if (client > 0) { kill(client, SIGKILL); waitpid(client, NULL, 0); client = 0; }
    if (service > 0) { kill(service, SIGKILL); waitpid(service, NULL, 0); service = 0; }
}
static void expired(int signal_number) { (void)signal_number; cleanup(); _exit(124); }
static void interrupted(int signal_number) { (void)signal_number; }
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"probe error line %d errno=%d\n",__LINE__,errno); exit(2); } } while (0)
static uint64_t now(void) {
    struct timespec t; CHECK(!clock_gettime(CLOCK_MONOTONIC, &t));
    return (uint64_t)t.tv_sec * 1000000000ULL + t.tv_nsec;
}
static void pause_short(void) { struct timespec t = {0, 1000000}; nanosleep(&t, NULL); }
static int receive(int fd, void *out, size_t size) {
    unsigned char *p = out; size_t have = 0; uint64_t end = now() + 5000000000ULL;
    while (have < size && now() < end) {
        ssize_t n = read(fd, p + have, size - have);
        if (n > 0) have += n;
        else if (n == 0) return 0;
        else CHECK(errno == EAGAIN || errno == EINTR);
        pause_short();
    }
    return have == size;
}
static int attributes(const char *path, struct stat *st, struct fuse_file_info *fi) {
    (void)fi; memset(st, 0, sizeof(*st));
    if (!strcmp(path,"/")) { st->st_mode=S_IFDIR|0755; st->st_nlink=2; return 0; }
    if (strcmp(path,"/waiter") && strcmp(path,"/health")) return -ENOENT;
    st->st_mode=S_IFREG|0444; st->st_nlink=1; st->st_size=1; return 0;
}
static int file_open(const char *path, struct fuse_file_info *fi) {
    (void)fi; return strcmp(path,"/waiter") && strcmp(path,"/health") ? -ENOENT : 0;
}
static int file_read(const char *path, char *out, size_t size, off_t offset, struct fuse_file_info *fi) {
    (void)fi;
    if (!strcmp(path,"/waiter")) {
        char token;
        if (write(notice[1], "H", 1) != 1 || read(release_callback[0], &token, 1) != 1) return -EIO;
    }
    if (offset || !size) return 0;
    out[0]='Q'; return 1;
}
static struct qfuse_admin_status status_of(const struct qfuse_admin_advert *advert) {
    struct qfuse_admin_status status; memset(&status,0,sizeof(status));
    int coid = ConnectAttach(0,advert->pid,advert->channel,_NTO_SIDE_CHANNEL,0); CHECK(coid >= 0);
    struct qfuse_admin_request request = {.magic=QFUSE_ADMIN_MAGIC,.version=QFUSE_ADMIN_VERSION,.command=QFUSE_ADMIN_STATUS};
    memcpy(request.instance,advert->instance,sizeof(request.instance));
    uint64_t ns=1000000000ULL;
    CHECK(!TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&ns,NULL));
    int r=MsgSend(coid,&request,sizeof(request),&status,sizeof(status));
    CHECK(!ConnectDetach(coid)); CHECK(r==0);
    CHECK(status.magic==QFUSE_ADMIN_MAGIC && status.version==QFUSE_ADMIN_VERSION && status.size==sizeof(status));
    CHECK(status.pid==advert->pid && !memcmp(status.instance,advert->instance,sizeof(status.instance)));
    return status;
}
int main(int argc, char **argv) {
    int use_signal = argc==2 && !strcmp(argv[1],"--signal"); CHECK(argc==1 || use_signal);
    owner=getpid(); setvbuf(stdout,NULL,_IOLBF,0); atexit(cleanup); signal(SIGALRM,expired); alarm(25);
    CHECK(!pipe(notice) && !pipe(release_callback) && !pipe(finish_client));
    int admin[2], outcome[2]; CHECK(!pipe(admin) && !pipe(outcome));
    CHECK(fcntl(notice[0],F_SETFL,O_NONBLOCK)!=-1 && fcntl(admin[0],F_SETFL,O_NONBLOCK)!=-1 && fcntl(outcome[0],F_SETFL,O_NONBLOCK)!=-1);
    snprintf(mountpoint,sizeof(mountpoint),"/dev/resmgrcheck-qfuse-%ld",(long)getpid());
    struct stat existing; CHECK(lstat(mountpoint,&existing)==-1 && errno==ENOENT);
    service=fork(); CHECK(service>=0);
    if (!service) {
        close(admin[0]); close(outcome[0]); close(outcome[1]);
        char descriptor[32]; snprintf(descriptor,sizeof(descriptor),"%d",admin[1]); CHECK(!setenv("QFUSE_ADMIN_FD",descriptor,1));
        struct fuse_operations ops={.getattr=attributes,.open=file_open,.read=file_read};
        char *args[]={"resmgrcheck-qfuse-probe","-f",mountpoint,NULL};
        _exit(fuse_main_real(3,args,&ops,sizeof(ops),NULL));
    }
    close(admin[1]); close(notice[1]); close(release_callback[0]);
    struct qfuse_admin_advert advert; CHECK(receive(admin[0],&advert,sizeof(advert)));
    CHECK(advert.magic==QFUSE_ADMIN_MAGIC && advert.version==QFUSE_ADMIN_VERSION && advert.pid==(uint32_t)service);
    struct qfuse_admin_status initial;
    uint64_t end=now()+5000000000ULL;
    do { initial=status_of(&advert); if(initial.phase==QFUSE_ADMIN_SERVING) break; pause_short(); } while(now()<end);
    CHECK(initial.phase==QFUSE_ADMIN_SERVING);
    printf("{\"event\":\"ready\",\"service_pid\":%ld,\"channel\":%u,\"mode\":\"%s\"}\n",(long)service,advert.channel,use_signal?"signal":"timeout");
    client=fork(); CHECK(client>=0);
    if (!client) {
        close(outcome[0]); close(finish_client[1]);
        struct sigaction action={0}; action.sa_handler=interrupted; sigemptyset(&action.sa_mask); CHECK(!sigaction(SIGUSR1,&action,NULL));
        char path[256]; snprintf(path,sizeof(path),"%s/waiter",mountpoint);
        int fd=open(path,O_RDONLY); CHECK(fd>=0);
        if (!use_signal) { uint64_t ns=500000000ULL; CHECK(!TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&ns,NULL)); }
        char byte; errno=0; int r=pread(fd,&byte,1,0); int result[2]={r,errno};
        CHECK(write(outcome[1],result,sizeof(result))==sizeof(result));
        CHECK(read(finish_client[0],&byte,1)==1); CHECK(!close(fd)); _exit(0);
    }
    close(outcome[1]); close(finish_client[0]);
    char token; CHECK(receive(notice[0],&token,1) && token=='H');
    puts("{\"event\":\"callback_held\"}");
    if(use_signal) CHECK(!kill(client,SIGUSR1));
    int result[2]; CHECK(receive(outcome[0],result,sizeof(result)));
    printf("{\"event\":\"cancel_return\",\"raw_return\":%d,\"api_error\":%d,\"expected_error\":%d}\n",result[0],result[1],use_signal?EINTR:ETIMEDOUT);
    struct qfuse_admin_status held=status_of(&advert);
    printf("{\"event\":\"held_status\",\"active_operations\":%u,\"cancelled_waits\":%u,\"cleanup_pending\":%u}\n",held.active_operations,held.cancelled_waits,held.cleanup_pending);
    char healthy[256]; snprintf(healthy,sizeof(healthy),"%s/health",mountpoint);
    uint64_t ns=1000000000ULL; CHECK(!TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&ns,NULL));
    int fd=open(healthy,O_RDONLY); CHECK(fd>=0);
    ns=1000000000ULL; CHECK(!TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&ns,NULL));
    int health=pread(fd,&token,1,0); CHECK(!close(fd));
    printf("{\"event\":\"independent_health\",\"raw_return\":%d,\"value\":%d}\n",health,(unsigned char)token);
    CHECK(write(release_callback[1],"R",1)==1);
    struct qfuse_admin_status drained; end=now()+5000000000ULL;
    do { drained=status_of(&advert); if(!drained.active_operations && !drained.cleanup_pending) break; pause_short(); } while(now()<end);
    printf("{\"event\":\"drained_status\",\"active_operations\":%u,\"cancelled_waits\":%u,\"cleanup_pending\":%u}\n",drained.active_operations,drained.cancelled_waits,drained.cleanup_pending);
    CHECK(write(finish_client[1],"F",1)==1);
    int status; CHECK(waitpid(client,&status,0)==client); client=0; CHECK(WIFEXITED(status) && !WEXITSTATUS(status));
    CHECK(!kill(service,SIGTERM)); CHECK(waitpid(service,&status,0)==service); service=0;
    CHECK(WIFEXITED(status) && !WEXITSTATUS(status));
    CHECK(lstat(mountpoint,&existing)==-1 && errno==ENOENT);
    puts("{\"event\":\"cleanup\",\"children_reaped\":true,\"mount_absent\":true}");
    alarm(0); return 0;
}
