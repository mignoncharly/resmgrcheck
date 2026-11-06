#include "process.h"
#include <sys/wait.h>
#include <signal.h>
#include <errno.h>
int rmc_child_poll(rmc_child *c) {
    if (c->reaped) return 1;
    if (!c->owned || c->pid<=0) { c->owned=0;return -1; }
    pid_t rc=waitpid(c->pid,&c->status,WNOHANG);
    if (rc==c->pid) { c->reaped=1;return 1; }
    if (rc==0 || (rc==-1 && errno==EINTR)) return 0;
    c->owned=0;return -1;
}
int rmc_child_signal(rmc_child *c,int sig,int *error) {
    int state=rmc_child_poll(c);*error=0;
    if (state==1) return 1;
    if (state<0) { *error=ECHILD;return -1; }
    c->expected_stop=1;
    if (sig>0 && sig<32) c->termination_mask |= 1U << sig;
    int rc=kill(c->pid,sig);*error=rc==-1 ? errno : 0;
    return rc;
}
