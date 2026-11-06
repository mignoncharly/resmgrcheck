#include "common/plan.h"
#include "common/lab.h"
#include <sys/neutrino.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
static volatile sig_atomic_t signal_seen;
static void interruption(int number) { (void)number;signal_seen=1; }

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    rmc_plan plan;
    if (!rmc_plan_load(argv[1], &plan)) { fputs("invalid worker plan\n",stderr); return 2; }
    rmc_plan_environment(&plan);
    const char *op=argv[2];
    const char *roles[] = {"normal","message","hold","release","state","timed","health","negative","ready","signal"};
    int valid=0; for (unsigned i=0; i<sizeof(roles)/sizeof(roles[0]); ++i) if (!strcmp(op,roles[i])) valid=1;
    if (!valid) { cJSON_Delete(plan.root); return 2; }
    if ((!strcmp(op,"signal") && strcmp(plan.scenario,"signal")) || (!strcmp(op,"timed") && strcmp(plan.scenario,"timeout"))) { cJSON_Delete(plan.root);return 2; }
    event("worker","started","operation=%s",op);
    rmc_lab_worker(op);
    char path[256];
    snprintf(path,sizeof(path),"%s-%s",plan.path,json_string(plan.root,"service_instance_id"));
    int fd=open(path,O_RDWR);
    if (fd == -1) { event("worker","open_error","error=%d",errno); event("worker","worker_final","exit_code=2"); cJSON_Delete(plan.root); return 2; }
    int exit_code=0;
    if (!strcmp(op,"hold") || !strcmp(op,"release") || !strcmp(op,"state") || !strcmp(op,"ready")) {
        rmc_state state={0};
        int error=plan.adapter->control(fd,op,&state);
        rmc_emit_state(op,error,&state); if (error) exit_code=2;
    } else {
        rmc_result result={0};
        if (!strcmp(op,"normal") || !strcmp(op,"health") || !strcmp(op,"negative")) {
            if (!strcmp(op,"negative") && !(plan.adapter->capabilities & RMC_CAP_ERROR_PROBE)) exit_code=3;
            else plan.adapter->ordinary(fd,!strcmp(op,"negative"),&result);
        } else {
            rmc_prepared prepared;
            plan.adapter->prepare(&prepared);
            int raw, captured;
            if (!strcmp(op,"signal")) {
                struct sigaction action={0};action.sa_handler=interruption;sigemptyset(&action.sa_mask);
                sigset_t mask;sigemptyset(&mask);sigaddset(&mask,SIGUSR1);
                int error=0,masked=1;sigset_t current;
                if (sigaction(SIGUSR1,&action,NULL) || sigprocmask(SIG_UNBLOCK,&mask,NULL)) error=errno;
                if (!error) {
                    if (sigprocmask(SIG_BLOCK,NULL,&current) || (masked=sigismember(&current,SIGUSR1))<0) error=errno;
                }
                event("worker","signal_setup","name=SIGUSR1 signal=%d flags=0 retry=0 timeout_armed=0 masked=%d error=%d",SIGUSR1,masked<0 ? 1 : masked,error);
                if (error || masked) { exit_code=2;goto close_worker; }
                event("worker","operation_armed","operation=signal timeout_armed=0");
            }
            if (!strcmp(op,"timed")) {
                uint64_t deadline=mono_ns()+(uint64_t)plan.operation_ms*1000000ULL;
                event("worker","deadline","operation=timed deadline_ns=%" PRIu64 " timeout_ms=%u",deadline,plan.operation_ms);
                errno=0;
                if (TimerTimeout(CLOCK_MONOTONIC,TIMER_ABSTIME|_NTO_TIMEOUT_SEND|_NTO_TIMEOUT_REPLY,NULL,&deadline,NULL)==-1) {
                    event("worker","arm_error","error=%d",errno); exit_code=2; goto close_worker;
                }
                raw=MsgSendv(fd,prepared.send,prepared.send_parts,prepared.receive,prepared.receive_parts);
            } else {
                errno=0;
                raw=MsgSendv(fd,prepared.send,prepared.send_parts,prepared.receive,prepared.receive_parts);
            }
            captured=errno;
            if (!strcmp(op,"signal")) event("worker","signal_handler_observed","signal=%d seen=%d",SIGUSR1,signal_seen!=0);
            plan.adapter->finish(&prepared,raw,captured,&result);
        }
        if (!exit_code) rmc_emit_result(op,&result);
    }
close_worker:
    ;
    int rc=close(fd), error=rc==-1 ? errno : 0;
    event("worker","closed","rc=%d error=%d",rc,error);
    if (rc==-1) exit_code=2;
    event("worker","worker_final","exit_code=%d",exit_code);
    cJSON_Delete(plan.root);
    return exit_code;
}
