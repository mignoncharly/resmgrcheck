#include "lab.h"
#include <signal.h>
#include <errno.h>
#include <sys/resource.h>
static const char *control="none";
int rmc_lab_set(const char *name) {
    const char *valid[]={"none","worker_stuck","worker_crash","worker_start_failed","service_unavailable",
        "readiness_blocked","health_blocked","malformed","truncated","oversize","event_overflow","channel_full",
        "sink_unavailable","sink_quota","cleanup_failure","ownership_lost","manager_interference","manager_pending","late_malformed","fixture_evidence_loss"};
    for (unsigned i=0;i<sizeof(valid)/sizeof(valid[0]);++i) if (!strcmp(name,valid[i])) {
        control=valid[i];return setenv("RMC_LAB_CONTROL",control,1)==0;
    }
    return 0;
}
const char *rmc_lab_name(void) { return control; }
int rmc_lab_is(const char *name) { return !strcmp(control,name); }
void rmc_lab_worker(const char *role) {
    const char *env=getenv("RMC_LAB_CONTROL");
    if (!env) env="none";
    if (!rmc_lab_set(env)) _exit(121);
    int initial=!strcmp(role,"normal");
    int diagnostic=!strcmp(role,"state");
    if ((rmc_lab_is("worker_stuck") || rmc_lab_is("worker_crash")) && initial) {
        event("worker","lab_injection","name=%s operation=%s",control,role);
        if (rmc_lab_is("worker_crash")) { struct rlimit limit={0,0};setrlimit(RLIMIT_CORE,&limit);raise(SIGSEGV); _exit(121); }
        for (;;) nanosleep(&(struct timespec){.tv_sec=1},NULL);
    }
    if (!diagnostic) return;
    if (rmc_lab_is("malformed") || rmc_lab_is("late_malformed")) {
        (void)write(STDOUT_FILENO,"{not-json}\n",11);_exit(120);
    }
    if (rmc_lab_is("truncated")) { (void)write(STDOUT_FILENO,"{\"kind\":",8);_exit(0); }
    if (rmc_lab_is("oversize")) {
        char bytes[1024];memset(bytes,'x',sizeof(bytes));
        for (unsigned i=0;i<24;++i) {
            if (write(STDOUT_FILENO,bytes,sizeof(bytes))!=sizeof(bytes)) _exit(120);
            nanosleep(&(struct timespec){.tv_nsec=2000000},NULL);
        }
        _exit(0);
    }
    if (rmc_lab_is("event_overflow") || rmc_lab_is("channel_full")) {
        for (unsigned i=0;i<400;++i) {
            event("worker","lab_noise","index=%u",i);
            if (rmc_lab_is("event_overflow")) nanosleep(&(struct timespec){.tv_nsec=2000000},NULL);
        }
        _exit(0);
    }
}
