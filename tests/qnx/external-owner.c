/* Qualification-only owner of a separately launched lab fixture. The product
 * never owns or signals this process. STOP is an explicit driver instruction. */
#define _QNX_SOURCE 1
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <spawn.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
extern char **environ;
static unsigned long long now(void) { struct timespec t;if (clock_gettime(CLOCK_MONOTONIC,&t)) _exit(2);return (unsigned long long)t.tv_sec*1000000000ULL+t.tv_nsec; }
static int poll_child(pid_t pid,int *status) { return waitpid(pid,status,WNOHANG)==pid; }
int main(int argc,char **argv) {
    if (argc!=4 || strncmp(argv[2],"/dev/resmgrcheck-external-",strlen("/dev/resmgrcheck-external-"))) return 2;
    struct stat existing;
    if (!lstat(argv[2],&existing) || errno!=ENOENT) return 2;
    struct sigaction action={0};sigemptyset(&action.sa_mask);action.sa_handler=SIG_IGN;
    if (sigaction(SIGPIPE,&action,NULL)) return 2;
    int log=open(argv[3],O_WRONLY|O_CREAT|O_EXCL,0600);if (log<0) return 2;
    if (setenv("RMC_RUN_ID","external-owner",1) || setenv("RMC_CASE_ID","external-owner",1) ||
        setenv("RMC_ATTEMPT_ID","attempt1",1) || setenv("RMC_INSTANCE_ID","external-owner",1) || setenv("RMC_CYCLE","1",1)) return 2;
    posix_spawn_file_actions_t actions;if (posix_spawn_file_actions_init(&actions)) return 2;
    posix_spawn_file_actions_adddup2(&actions,log,STDOUT_FILENO);posix_spawn_file_actions_adddup2(&actions,log,STDERR_FILENO);
    posix_spawn_file_actions_addopen(&actions,STDIN_FILENO,"/dev/null",O_RDONLY,0);
    posix_spawn_file_actions_addclose(&actions,log);
    char *args[]={argv[1],argv[2],"corrected",NULL};pid_t child;
    int error=posix_spawn(&child,argv[1],&actions,NULL,args,environ);posix_spawn_file_actions_destroy(&actions);close(log);
    if (error) return 2;
    int status=0,reaped=0;unsigned long long end=now()+2000000000ULL;struct stat st;
    while (lstat(argv[2],&st) && now()<end && !(reaped=poll_child(child,&status))) nanosleep(&(struct timespec){.tv_nsec=1000000},NULL);
    int ready=!lstat(argv[2],&st) && !reaped;
    printf("{\"kind\":\"external-owner-ready\",\"child_pid\":\"%ld\",\"ready\":%d}\n",(long)child,ready);fflush(stdout);
    char command[32];
    while (ready && fgets(command,sizeof(command),stdin)) {
        if (!strcmp(command,"STOP\n")) break;
        if (strcmp(command,"STATUS\n")) continue;
        if (!reaped) reaped=poll_child(child,&status);
        printf("{\"kind\":\"external-owner-status\",\"child_pid\":\"%ld\",\"reaped\":%d,\"raw_status\":%d}\n",(long)child,reaped,status);fflush(stdout);
    }
    int rc=0,signal_error=0;
    if (!reaped) { rc=kill(child,SIGTERM);signal_error=rc<0 ? errno : 0;end=now()+2000000000ULL;
        while (!(reaped=poll_child(child,&status)) && now()<end) nanosleep(&(struct timespec){.tv_nsec=1000000},NULL); }
    if (!reaped) { rc=kill(child,SIGKILL);signal_error=rc<0 ? errno : 0;end=now()+2000000000ULL;
        while (!(reaped=poll_child(child,&status)) && now()<end) nanosleep(&(struct timespec){.tv_nsec=1000000},NULL); }
    printf("{\"kind\":\"external-owner-stop\",\"child_pid\":\"%ld\",\"signal_rc\":%d,\"signal_error\":%d,\"reaped\":%d,\"raw_status\":%d}\n",(long)child,rc,signal_error,reaped,status);fflush(stdout);
    return reaped ? 0 : 2;
}
