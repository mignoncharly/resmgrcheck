#include "common/plan.h"
#include "common/persistence.h"
#include "common/process.h"
#include "common/protocol.h"
#include "common/journal.h"
#include "common/lab.h"
#include <errno.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <ctype.h>

extern char **environ;
#define MAX_EVENTS 4096
#define MAX_CHILDREN 256
static rmc_child children[MAX_CHILDREN];
static unsigned child_count,count,current_cycle=1;
static int observe_service_errors;
static cJSON *events[MAX_EVENTS];
static int evidence_error,run_error,in_cleanup;
static uint64_t execution_end;
static char directory[1024],service_path[256];
static rmc_plan plan;
static const char *plan_path;
static struct { const char *reason;pid_t pid; } problems[64];
static unsigned problem_count;

static void problem(const char *reason,rmc_child *c,int error) {
    pid_t pid=c ? c->pid : 0;
    for (unsigned i=0;i<problem_count;++i) if (problems[i].pid==pid && !strcmp(problems[i].reason,reason)) return;
    if (problem_count==64) { evidence_error=run_error=1;return; }
    problems[problem_count].reason=reason;problems[problem_count++].pid=pid;run_error=1;
    if (!strncmp(reason,"evidence_",9) || !strcmp(reason,"event_sink_failed")) evidence_error=1;
    event("supervisor","problem","reason=%s child_pid=%ld operation=%s error=%d",reason,(long)pid,c ? c->operation : "none",error);
}
static void journal_check(void) {
    if (rmc_journal_sink_error()) problem("event_sink_failed",NULL,rmc_journal_sink_error());
    if (rmc_journal_overflow()) problem("evidence_capacity_exceeded",NULL,0);
}
static int status_snapshot(const char *state,int clean,int code) {
    cJSON *list=cJSON_CreateArray();if (!list) _exit(120);
    for (unsigned i=0;i<child_count;++i) if (!children[i].reaped) {
        cJSON *o=json_object();add_decimal(o,"pid",children[i].pid);add_string(o,"role",children[i].producer);
        if (!cJSON_AddItemToArray(list,o)) _exit(120);
    }
    char saved_cycle[16];snprintf(saved_cycle,sizeof(saved_cycle),"%u",current_cycle);
    if (setenv("RMC_CYCLE","1",1)) _exit(120);
    int ok=rmc_status_write(&plan,state,clean,code,list);
    if (setenv("RMC_CYCLE",saved_cycle,1)) _exit(120);
    if (!ok) problem("status_write_failed",NULL,errno);
    return ok;
}
static uint64_t bounded(uint64_t end) { return execution_end && execution_end<end ? execution_end : end; }
static int64_t field(const cJSON *o,const char *key) {
    const cJSON *container=(!strcmp(key,"pid") || !strcmp(key,"seq") || !strcmp(key,"ns")) ? o : cJSON_GetObjectItemCaseSensitive(o,"data");
    const cJSON *v=cJSON_GetObjectItemCaseSensitive(container,key);
    if (cJSON_IsNumber(v)) return (int64_t)v->valuedouble;
    if (!cJSON_IsString(v)) return -1;
    char *end;errno=0;long long n=strtoll(v->valuestring,&end,10);
    return !errno && *v->valuestring && !*end ? n : -1;
}
static int decimal_field(const cJSON *o,const char *key) {
    const char *s=json_string(o,key);
    if (!s || !*s || strlen(s)>19 || (s[0]=='0' && s[1])) return 0;
    for (const char *p=s;*p;++p) if (!isdigit((unsigned char)*p)) return 0;
    errno=0;strtoll(s,NULL,10);return !errno;
}
static int named(const cJSON *o,const char *name) { const char *v=json_string(o,"event");return v && !strcmp(v,name); }
static int find_event(pid_t pid,const char *name,unsigned after) {
    for (unsigned i=after;i<count;++i) if (field(events[i],"pid")==pid && named(events[i],name)) return (int)i;
    return -1;
}
static void reap_all(void) {
    for (unsigned i=0;i<child_count;++i) {
        rmc_child *c=&children[i];
        int result=rmc_child_poll(c);
        if (result<0) { problem("ownership_unknown",c,ECHILD);continue; }
        if (!c->reaped || c->reported) continue;
        c->reported=1;
        event("supervisor","reaped","child_pid=%ld raw_status=%d",(long)c->pid,c->status);
        event("supervisor","process_exit","child_pid=%ld exited=%d exit_code=%d signal=%d",(long)c->pid,WIFEXITED(c->status)!=0,WIFEXITED(c->status) ? WEXITSTATUS(c->status) : 0,WIFSIGNALED(c->status) ? WTERMSIG(c->status) : 0);
        int expected_signal=WIFSIGNALED(c->status) && WTERMSIG(c->status)<32 && (c->termination_mask & (1U << WTERMSIG(c->status)));
        if (!c->expected_stop || (WIFSIGNALED(c->status) && !expected_signal)) {
            if (!strcmp(c->producer,"fixture")) {
                problem("service_interference",c,0);
                if (!c->bad && WIFEXITED(c->status) && WEXITSTATUS(c->status)==120) problem("evidence_loss",c,0);
            }
            else if (!c->bad && WIFEXITED(c->status) && WEXITSTATUS(c->status)==120) problem("evidence_loss",c,0);
            else if (WIFSIGNALED(c->status) || !WIFEXITED(c->status)) problem("worker_crashed",c,0);
        }
    }
}
static void bad_source(rmc_child *c,const char *reason) {
    if (c->bad) return;
    c->bad=1;
    char hex[129];size_t n=c->used<64 ? c->used : 64;
    for (size_t i=0;i<n;++i) snprintf(hex+2*i,3,"%02x",(unsigned char)c->partial[i]);
    hex[2*n]=0;
    event("supervisor","invalid_frame","child_pid=%ld reason=%s size=%zu prefix_hex=%s",(long)c->pid,reason,c->used,hex);
    problem(reason,c,0);
    if (c->fd!=-1) close(c->fd);
    c->fd=-1;c->eof=1;c->used=0;
}
static void receive_line(rmc_child *c) {
    c->partial[c->used]=0;const char *end;
    cJSON *o=cJSON_ParseWithLengthOpts(c->partial,c->used+1,&end,1);
    char *render=o ? cJSON_PrintUnformatted(o) : NULL;
    int valid=render && !strcmp(render,c->partial);cJSON_free(render);
    if (!valid || !json_tree(o,0) || !json_keys(o,"kind schema_version run_id case_id attempt_id cycle service_instance_id producer pid seq ns event data") ||
        !json_string(o,"kind") || strcmp(json_string(o,"kind"),"producer-event") || !json_integer(o,"schema_version",1,1,NULL)) goto invalid;
    const char *ids[]={"run_id","case_id","attempt_id","service_instance_id"};
    for (unsigned i=0;i<4;++i) if (!json_string(o,ids[i]) || strcmp(json_string(o,ids[i]),json_string(plan.root,ids[i]))) goto invalid;
    if (!json_integer(o,"cycle",1,(int)plan.cycles,NULL) || (!strcmp(c->producer,"worker") && (unsigned)cJSON_GetObjectItemCaseSensitive(o,"cycle")->valueint!=c->cycle) ||
        !decimal_field(o,"pid") || !decimal_field(o,"ns") || !json_integer(o,"seq",1,4096,NULL) || field(o,"pid")!=c->pid ||
        !json_string(o,"producer") || strcmp(json_string(o,"producer"),c->producer) || field(o,"seq")!=c->last_seq+1 || field(o,"ns")<c->last_ns ||
        !rmc_producer_payload(o,plan.adapter)) goto invalid;
    if (count==(plan.cycles>1 ? MAX_EVENTS : plan.extended ? 1024U : 256U)) { cJSON_Delete(o);bad_source(c,"evidence_capacity_exceeded");return; }
    ++c->last_seq;c->last_ns=field(o,"ns");events[count++]=o;json_write(o);c->used=0;return;
 invalid:
    cJSON_Delete(o);bad_source(c,"evidence_invalid");
}
static void source_eof(rmc_child *c) {
    if (c->used) { bad_source(c,"evidence_incomplete");return; }
    close(c->fd);c->fd=-1;c->eof=1;
}
static void pump(uint64_t deadline) {
    deadline=bounded(deadline);uint64_t now=mono_ns();
    int ms=now>=deadline ? 0 : (int)((deadline-now+999999ULL)/1000000ULL);if (ms>25) ms=25;
    struct pollfd fds[MAX_CHILDREN];unsigned indices[MAX_CHILDREN],nfds=0;
    for (unsigned i=0;i<child_count;++i) if (children[i].fd!=-1) {
        fds[nfds]=(struct pollfd){.fd=children[i].fd,.events=POLLIN};indices[nfds++]=i;
    }
    int result=poll(fds,nfds,ms);
    if (result<0 && errno!=EINTR) problem("evidence_loss",NULL,errno);
    if (result>0) for (unsigned j=0;j<nfds;++j) {
        rmc_child *c=&children[indices[j]];
        if (fds[j].revents & (POLLERR|POLLNVAL)) { bad_source(c,"evidence_loss");continue; }
        if (!(fds[j].revents & (POLLIN|POLLHUP))) continue;
        char bytes[2048];ssize_t n=read(c->fd,bytes,sizeof(bytes));
        if (n==0) { source_eof(c);continue; }
        if (n<0) { if (errno!=EAGAIN && errno!=EINTR) bad_source(c,"evidence_loss");continue; }
        for (ssize_t k=0;k<n && c->fd!=-1;++k) {
            if (bytes[k]=='\n') receive_line(c);
            else if (c->used<sizeof(c->partial)-2) c->partial[c->used++]=bytes[k];
            else bad_source(c,"evidence_invalid");
        }
    }
    reap_all();journal_check();
    for (unsigned i=0;i<child_count;++i) {
        rmc_child *c=&children[i];
        if (c->eof && c->reaped && !c->bad && !c->expected_stop && !strcmp(c->producer,"worker") &&
            WIFEXITED(c->status) && WEXITSTATUS(c->status)==0 && find_event(c->pid,"worker_final",0)<0) problem("evidence_incomplete",c,0);
    }
}
static rmc_child *spawn_child(int fixture,const char *operation) {
    if (child_count==(plan.cycles>1 ? MAX_CHILDREN : plan.extended ? 64U : 16U)) { problem("worker_start_failed",NULL,0);return NULL; }
    const char *binary=fixture ? plan.adapter->fixture_binary : "worker";
    char exe[1200];snprintf(exe,sizeof(exe),"%s/%s",directory,binary);
    if (!fixture && rmc_lab_is("worker_start_failed")) snprintf(exe,sizeof(exe),"%s/missing-worker",directory);
    int pipefd[2];if (pipe2(pipefd,O_CLOEXEC|O_NONBLOCK)) { problem("worker_start_failed",NULL,errno);return NULL; }
    char cycle_value[16];snprintf(cycle_value,sizeof(cycle_value),"%u",current_cycle);
    char *args[]={exe,fixture ? service_path : (char *)plan_path,(char *)operation,fixture ? NULL : cycle_value,NULL};
    posix_spawn_file_actions_t actions;int error=posix_spawn_file_actions_init(&actions);
    if (error) { close(pipefd[0]);close(pipefd[1]);problem("worker_start_failed",NULL,error);return NULL; }
    error=posix_spawn_file_actions_adddup2(&actions,pipefd[1],STDOUT_FILENO);
    if (!error) error=posix_spawn_file_actions_addclose(&actions,pipefd[0]);
    if (!error) error=posix_spawn_file_actions_addclose(&actions,pipefd[1]);
    rmc_child *c=&children[child_count];
    if (!error) error=posix_spawn(&c->pid,exe,&actions,NULL,args,environ);
    posix_spawn_file_actions_destroy(&actions);close(pipefd[1]);
    if (error) { close(pipefd[0]);problem("worker_start_failed",NULL,error);return NULL; }
    c->cycle=current_cycle;c->owned=1;c->fd=pipefd[0];c->producer=fixture ? "fixture" : "worker";c->operation=operation;c->spawned_ns=mono_ns();++child_count;
    event("supervisor","spawned","binary=%s child_pid=%ld operation=%s",binary,(long)c->pid,operation);
    status_snapshot("running",0,-1);return c;
}
static int await_event(rmc_child *c,const char *name,unsigned after,uint64_t end) {
    end=bounded(end);int index;
    do { pump(end);index=find_event(c->pid,name,after);if (index>=0) return index; }
    while (!run_error && c->owned && !c->reaped && mono_ns()<end);
    return -1;
}
static void await_child(rmc_child *c,uint64_t end) {
    end=bounded(end);
    while (c->owned && !c->reaped && mono_ns()<end) pump(end);
    uint64_t drain=bounded(mono_ns()+50000000ULL);
    while (c->fd!=-1 && (c->reaped || !c->owned) && mono_ns()<drain) pump(drain);
}
static int worker(const char *op,int *index_out) {
    if (run_error) return 0;
    event("supervisor","phase","name=%s",op);
    unsigned after=count;rmc_child *c=spawn_child(0,op);if (!c) return 0;
    if (rmc_lab_is("channel_full") && !strcmp(op,"state")) nanosleep(&(struct timespec){.tv_nsec=100000000},NULL);
    uint64_t end=bounded(mono_ns()+(uint64_t)(!strcmp(op,"ready") ? plan.setup_ms : plan.probe_ms)*1000000ULL);
    if (rmc_lab_is("ownership_lost") && !strcmp(op,"ready")) {
        int ignored;
        pid_t observed;
        do { observed=waitpid(c->pid,&ignored,WNOHANG);if (!observed) nanosleep(&(struct timespec){.tv_nsec=1000000},NULL); }
        while (!observed && mono_ns()<end);
        if (observed==c->pid) event("supervisor","lab_discarded_wait","child_pid=%ld raw_status=%d",(long)c->pid,ignored);
    }
    await_child(c,end);
    event("supervisor","wait_bound","child_pid=%ld operation=%s deadline_ns=%" PRIu64 " timed_out=%d",(long)c->pid,op,end,c->owned && !c->reaped);
    if (c->owned && !c->reaped) problem((!strcmp(op,"ready") || !strcmp(op,"health") || !strcmp(op,"state")) ? "probe_timeout" : "worker_timeout",c,0);
    int result=find_event(c->pid,(!strcmp(op,"normal") || !strcmp(op,"message") || !strcmp(op,"health") || !strcmp(op,"negative") || !strcmp(op,"dup") || !strcmp(op,"health_next")) ? "result" : "control_result",after);
    if (index_out) *index_out=result;
    if (find_event(c->pid,"open_error",after)>=0) problem("service_unavailable",c,0);
    if (!run_error && (result<0 || !c->reaped || !WIFEXITED(c->status) || WEXITSTATUS(c->status))) {
        int closed=find_event(c->pid,"closed",after);
        if (closed>=0 && field(events[closed],"rc")==-1) problem("worker_close_failed",c,(int)field(events[closed],"error"));
        else if (!(observe_service_errors && result>=0 && named(events[result],"control_result") && field(events[result],"error")>0)) problem(result<0 ? "evidence_incomplete" : "worker_exit_failed",c,c->status);
    }
    return !run_error;
}
static void signal_owned(rmc_child *c,int sig) {
    reap_all();if (c->reaped) return;
    if (!c->owned) { problem("ownership_unknown",c,ECHILD);return; }
    int error;int rc=rmc_child_signal(c,sig,&error);
    if (rc==1) { reap_all();return; }
    event("supervisor","signal_sent","child_pid=%ld signal=%d rc=%d error=%d",(long)c->pid,sig,rc,error);
    if (error==ECHILD) problem("ownership_unknown",c,error);
    else if (rc<0 && error!=ESRCH) problem(in_cleanup ? "cleanup_signal_failed" : "scenario_trigger_failed",c,error);
    else if (rc<0 && !in_cleanup) problem("scenario_trigger_failed",c,error);
    reap_all();
}
static int cleanup(rmc_child *fixture,rmc_child *timed) {
    in_cleanup=1;uint64_t end=mono_ns()+(uint64_t)plan.cleanup_ms*1000000ULL;execution_end=end;
    event("supervisor","phase","name=cleanup");
    if (timed && !timed->reaped && timed->owned) {
        signal_owned(timed,SIGTERM);await_child(timed,mono_ns()+100000000ULL);
        event("supervisor","termination_observation","child_pid=%ld signal=%d reaped=%d",(long)timed->pid,SIGTERM,timed->reaped);
        if (!timed->reaped) { signal_owned(timed,SIGKILL);await_child(timed,mono_ns()+100000000ULL);
            event("supervisor","termination_observation","child_pid=%ld signal=%d reaped=%d",(long)timed->pid,SIGKILL,timed->reaped); }
    }
    if (fixture && !fixture->reaped && fixture->owned && !rmc_lab_is("cleanup_failure")) {
        event("supervisor","fixture_stop","child_pid=%ld blocked_worker_reaped=%d",(long)fixture->pid,timed ? timed->reaped : 1);
        signal_owned(fixture,SIGTERM);await_child(fixture,mono_ns()+200000000ULL);
        if (!fixture->reaped) signal_owned(fixture,SIGKILL);
    }
    for (unsigned i=0;i<child_count;++i) {
        rmc_child *c=&children[i];
        if (!c->reaped && !(rmc_lab_is("cleanup_failure") && c==fixture)) signal_owned(c,SIGKILL);
    }
    for (unsigned i=0;i<child_count;++i) await_child(&children[i],end);
    int all=1;
    for (unsigned i=0;i<child_count;++i) if (!children[i].reaped) all=0;
    if (!all) problem("cleanup_failed",NULL,0);
    journal_check();
    event("supervisor","cleanup","all_reaped=%d evidence_error=%d",all,evidence_error);
    return all;
}
/* A named fault injector is a separately owned child, not an inferred external
 * monitor. Unexpected fixture exit is always interference; actor stays unknown. */
static void manager_injection(rmc_child *fixture) {
    if (child_count==(plan.cycles>1 ? MAX_CHILDREN : plan.extended ? 64U : 16U)) { problem("worker_start_failed",NULL,0);return; }
    rmc_child *c=&children[child_count];pid_t pid=fork();
    if (pid==0) _exit(kill(fixture->pid,SIGTERM)==0 ? 0 : 2);
    if (pid<0) { problem("worker_start_failed",NULL,errno);return; }
    c->pid=pid;c->owned=1;c->fd=-1;c->producer="manager";c->operation="management";c->expected_stop=1;++child_count;
    event("supervisor","spawned","binary=lab-manager child_pid=%ld operation=management",(long)pid);
    await_child(c,mono_ns()+500000000ULL);await_child(fixture,mono_ns()+500000000ULL);
}
static void lab_recovery(void) {
    cJSON *root=json_object(),*list=cJSON_CreateArray();if (!list) _exit(120);
    add_string(root,"kind","lab-recovery");add_number(root,"schema_version",1);add_identity(root);
    add_decimal(root,"started_ns",(int64_t)mono_ns());
    uint64_t end=mono_ns()+2000000000ULL;
    for (unsigned i=0;i<child_count;++i) {
        rmc_child *c=&children[i];if (c->reaped || !c->owned) continue;
        cJSON *o=json_object();add_decimal(o,"pid",c->pid);add_string(o,"role",c->producer);
        int error;int rc=rmc_child_signal(c,SIGKILL,&error);add_number(o,"signal_rc",rc);add_number(o,"signal_error",error);
        if (!cJSON_AddItemToArray(list,o)) _exit(120);
    }
    int all=0;
    do {
        all=1;
        for (unsigned i=0;i<child_count;++i) if (!children[i].reaped && rmc_child_poll(&children[i])!=1) all=0;
        if (!all) nanosleep(&(struct timespec){.tv_nsec=1000000},NULL);
    } while (!all && mono_ns()<end);
    for (cJSON *o=list->child;o;o=o->next) for (unsigned i=0;i<child_count;++i) if (field(o,"pid")==children[i].pid) { /* pid is top-level here */
        add_number(o,"reaped",children[i].reaped);add_number(o,"raw_status",children[i].status);
    }
    add_number(root,"all_reaped",all);add_decimal(root,"finished_ns",(int64_t)mono_ns());
    if (!cJSON_AddItemToObject(root,"processes",list)) _exit(120);
    int fd=rmc_run_file("recovery.json");char *s=cJSON_PrintUnformatted(root);
    if (fd>=0 && s) { size_t n=strlen(s);(void)write(fd,s,n);(void)write(fd,"\n",1);(void)fsync(fd);close(fd); }
    cJSON_free(s);cJSON_Delete(root);
}
#include "common/scenario_v1.h"

static int identifier(const char *s) {
    if (!s || !*s || strlen(s)>64 || !isalnum((unsigned char)*s)) return 0;
    for (;*s;++s) if (!isalnum((unsigned char)*s) && *s!='_' && *s!='-') return 0;
    return 1;
}
int main(int argc,char **argv) {
    if (argc==2 && !strcmp(argv[1],"--describe")) { rmc_describe();return 0; }
    int persist=0,lab_seen=0;const char *lab="none",*after=NULL;
    if (argc<2) return 2;
    for (int i=2;i<argc;++i) {
        if (!strcmp(argv[i],"--persist") && !persist) persist=1;
        else if (!strncmp(argv[i],"--lab=",6) && !lab_seen) { lab=argv[i]+6;lab_seen=1; }
        else if (!strncmp(argv[i],"--after=",8) && !after && identifier(argv[i]+8)) after=argv[i]+8;
        else return 2;
    }
    if (!rmc_lab_set(lab) || ((after || strcmp(lab,"none")) && !persist) || !rmc_plan_load(argv[1],&plan)) { fputs("invalid scenario plan/control\n",stderr);return 2; }
    plan_path=argv[1];rmc_plan_environment(&plan);
    const char *slash=strrchr(argv[0],'/');if (!slash || (size_t)(slash-argv[0])>=sizeof(directory)) return 2;
    memcpy(directory,argv[0],(size_t)(slash-argv[0]));
    if (plan.external) snprintf(service_path,sizeof(service_path),"%s",plan.path);
    else snprintf(service_path,sizeof(service_path),"%s-%s",plan.path,json_string(plan.root,"service_instance_id"));
    struct sigaction action={0};sigemptyset(&action.sa_mask);action.sa_handler=SIG_DFL;
    if (sigaction(SIGCHLD,&action,NULL)) return 2;
    action.sa_handler=SIG_IGN;if (sigaction(SIGPIPE,&action,NULL)) return 2;
    if (persist) {
        int detached=rmc_detach_run(&plan);
        if (detached<0) { perror("persistent start uncertain/rejected; inspect run directory before retrying");cJSON_Delete(plan.root);return 2; }
        if (detached>0) { cJSON_Delete(plan.root);return 0; }
    }
    int recovery_fd=rmc_is_persistent() ? rmc_run_file("recovery.jsonl") : -1;
    rmc_journal_limits(plan.cycles,plan.extended);rmc_journal_start();rmc_manifest(&plan);
    event("supervisor","lab_control","name=%s",lab);
    if (persist) event("supervisor","run_storage","run_id=%s",json_string(plan.root,"run_id"));
    int early=0;
    if (after) {
        int clean=rmc_dependency_clean(after);
        event("supervisor","dependency","predecessor_id=%s state=%s",after,clean==1 ? "clean" : clean==0 ? "contaminated" : "unestablished");
        if (clean!=1) { event("supervisor","case_not_run","predecessor_id=%s reason=%s",after,clean==0 ? "prior_cleanup_failed" : "predecessor_unestablished");early=4; }
    }
    if (!early && ((plan.external && strcmp(plan.scenario,"external-health")) || plan.signal_unsupported || (plan.required_caps & ~plan.adapter->capabilities))) {
        event("supervisor","unsupported","reason=%s",plan.external ? "external_attach_not_implemented" : plan.signal_unsupported ? "signal_mode_not_implemented" : "missing_capability");early=3;
    }
    rmc_child *fixture=NULL,*timed=NULL;int flow_complete=0,cleaned=1;
    if (early) {
        event("supervisor","cleanup","all_reaped=1 evidence_error=0");flow_complete=1;goto finish;
    }
    execution_end=mono_ns()+(uint64_t)plan.execution_ms*1000000ULL;
    event("supervisor","settings","mode=%s timeout_ms=%u allowance_ms=%u path=%s case_ms=%u cleanup_ms=%u",plan.mode,plan.operation_ms,plan.cancellation_ms,service_path,plan.execution_ms,plan.cleanup_ms);
    if (plan.external) {
        event("supervisor","external_scope","path=%s read_only=1 service_build_verified=0 instance_verified=0",service_path);
        if (!worker("ready",NULL) || !worker("normal",NULL) || !worker("message",NULL) || !worker("health",NULL) || !worker("state",NULL)) goto done;
        flow_complete=1;goto done;
    }
    fixture=spawn_child(1,plan.mode);
    if (!fixture || await_event(fixture,"ready",0,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0) { if (!run_error) problem("service_unavailable",fixture,0);goto done; }
    if (rmc_lab_is("service_unavailable")) { signal_owned(fixture,SIGTERM);await_child(fixture,mono_ns()+500000000ULL); }
    if (rmc_lab_is("manager_interference")) { manager_injection(fixture);goto done; }
    if (rmc_lab_is("readiness_blocked")) { int e;int r=kill(fixture->pid,SIGSTOP);e=r<0 ? errno : 0;event("supervisor","signal_sent","child_pid=%ld signal=%d rc=%d error=%d",(long)fixture->pid,SIGSTOP,r,e); }
    if (plan.extended) {
        flow_complete=extended_scenario(fixture,&timed);goto done;
    }
    if (!worker("ready",NULL) || !worker("normal",NULL) || !worker("message",NULL)) goto done;
    if ((plan.adapter->capabilities & RMC_CAP_ERROR_PROBE) && !worker("negative",NULL)) goto done;
    if (!worker("hold",NULL)) goto done;
    unsigned after_events=count;rmc_child *released=spawn_child(0,"normal");
    if (!released || await_event(fixture,"pending",after_events,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0) goto done;
    if (rmc_lab_is("manager_pending")) { manager_injection(fixture);await_child(released,mono_ns()+500000000ULL);goto done; }
    if (!worker("release",NULL)) goto done;
    await_child(released,mono_ns()+(uint64_t)plan.probe_ms*1000000ULL);
    if (!released->reaped || find_event(released->pid,"result",after_events)<0 || !worker("hold",NULL)) { if (!run_error) problem("evidence_incomplete",released,0);goto done; }
    event("supervisor","stage","name=deferred_release_complete");
    int is_signal=!strcmp(plan.scenario,"signal");
    after_events=count;timed=spawn_child(0,is_signal ? "signal" : "timed");if (!timed) goto done;
    int deadline_index=await_event(timed,is_signal ? "operation_armed" : "deadline",after_events,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL);
    if (deadline_index<0) { if (!run_error) problem("evidence_incomplete",timed,0);goto done; }
    uint64_t completion_bound;
    if (is_signal) {
        int pending=await_event(fixture,"pending",after_events,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL);
        if (pending<0 || field(events[pending],"client_pid")!=timed->pid) { if (!run_error) problem("precondition_not_established",timed,0);goto done; }
        completion_bound=mono_ns()+(uint64_t)plan.cancellation_ms*1000000ULL;
        event("supervisor","trigger_requested","child_pid=%ld signal=%d completion_bound_ns=%" PRIu64,(long)timed->pid,SIGUSR1,completion_bound);
        signal_owned(timed,SIGUSR1);
    } else completion_bound=(uint64_t)field(events[deadline_index],"deadline_ns")+(uint64_t)plan.cancellation_ms*1000000ULL;
    int result_index;
    do { pump(completion_bound);result_index=find_event(timed->pid,"result",after_events);if (result_index>=0 && timed->reaped) break; }
    while (!run_error && mono_ns()<completion_bound && mono_ns()<execution_end);
    if (mono_ns()>=execution_end) { problem("case_deadline",NULL,0);goto done; }
    event("supervisor","operation_bound","completion_bound_ns=%" PRIu64 " expired=%d result_observed=%d worker_reaped=%d",completion_bound,mono_ns()>=completion_bound,result_index>=0,timed->reaped);
    if (rmc_lab_is("sink_unavailable") || rmc_lab_is("sink_quota")) {
        rmc_journal_fault(rmc_lab_is("sink_quota"));event("supervisor","phase","name=state");journal_check();
    }
    if (!worker("state",NULL)) goto done;
    if (result_index>=0 && timed->reaped && WIFEXITED(timed->status) && !WEXITSTATUS(timed->status)) {
        if (!worker("release",NULL)) goto done;
        if (rmc_lab_is("health_blocked")) { int r=kill(fixture->pid,SIGSTOP);event("supervisor","signal_sent","child_pid=%ld signal=%d rc=%d error=%d",(long)fixture->pid,SIGSTOP,r,r<0 ? errno : 0); }
        if (!worker("health",NULL)) goto done;
    } else event("supervisor","health_withheld","reason=operation_incomplete");
    flow_complete=1;
 done:
    if (!flow_complete && !run_error) problem(mono_ns()>=execution_end ? "case_deadline" : "precondition_not_established",NULL,0);
    current_cycle=1;if (setenv("RMC_CYCLE","1",1)) _exit(120);
    cleaned=cleanup(fixture,timed);
 finish:
    if (persist && !rmc_journal_sink_error() && fsync(STDOUT_FILENO)) rmc_journal_sink_failed(errno);
    journal_check();
    if (rmc_journal_sink_error()) rmc_status_event_file("recovery.jsonl");
    int exit_code=early ? early : run_error || !cleaned ? 2 : 0;
    event("supervisor","run_final","flow_complete=%d cleanup_ok=%d evidence_error=%d",flow_complete,cleaned,evidence_error);
    journal_check();
    if (run_error) exit_code=2;
    if (rmc_journal_sink_error()) rmc_status_event_file("recovery.jsonl");
    int sealed=1;
    if (persist) {
        sealed=rmc_journal_seal(recovery_fd);
        if (!sealed) { run_error=evidence_error=1;exit_code=2; }
        if (!rmc_journal_sink_error() && fsync(STDOUT_FILENO)) {
            rmc_journal_sink_failed(errno);journal_check();rmc_status_event_file("recovery.jsonl");exit_code=2;
            /* The late diagnostic intentionally invalidates the final sequence.
             * Reseal the actual journal so this error is retained in recovery. */
            if (lseek(recovery_fd,0,SEEK_SET)<0 || ftruncate(recovery_fd,0) || !rmc_journal_seal(recovery_fd)) sealed=0;
        }
    }
    status_snapshot(early==4 ? "not-run" : exit_code==0 || exit_code==3 ? "complete" : "incomplete",cleaned,exit_code);
    if (recovery_fd>=0) close(recovery_fd);
    for (unsigned i=0;i<child_count;++i) if (children[i].fd!=-1) { close(children[i].fd);children[i].fd=-1; }
    if (rmc_lab_is("cleanup_failure")) lab_recovery();
    for (unsigned i=0;i<count;++i) cJSON_Delete(events[i]);
    cJSON_Delete(plan.root);rmc_journal_free();
    (void)in_cleanup;(void)sealed;
    return exit_code;
}
