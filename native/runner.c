#include "common/plan.h"
#include <errno.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>

extern char **environ;
#define MAX_EVENTS 256
#define MAX_CHILDREN 16
struct child { pid_t pid; int reaped, status; const char *producer; };
static struct child children[MAX_CHILDREN];
static unsigned child_count, count;
static cJSON *events[MAX_EVENTS];
static char partial[RMC_FRAME_MAX];
static size_t used;
static int channel[2], evidence_error;
static uint64_t execution_end;
static char directory[1024], service_path[256];
static rmc_plan plan;
static const char *plan_path;

static uint64_t bounded(uint64_t deadline) {
    return execution_end && execution_end < deadline ? execution_end : deadline;
}

static int64_t field(const cJSON *record, const char *key) {
    const cJSON *d = (!strcmp(key,"pid") || !strcmp(key,"seq") || !strcmp(key,"ns")) ? record : cJSON_GetObjectItemCaseSensitive(record,"data");
    const cJSON *v=cJSON_GetObjectItemCaseSensitive(d,key);
    if (cJSON_IsNumber(v)) return (int64_t)v->valuedouble;
    if (!cJSON_IsString(v)) return -1;
    char *end; errno=0;
    long long n=strtoll(v->valuestring,&end,10);
    return !errno && *v->valuestring && !*end ? n : -1;
}
static int named(const cJSON *record, const char *name) {
    const char *v=json_string(record,"event");
    return v && !strcmp(v,name);
}

static int find_event(pid_t pid, const char *name, unsigned after) {
    for (unsigned i = after; i < count; ++i)
        if (field(events[i], "pid") == pid && named(events[i], name)) return (int)i;
    return -1;
}

static void reap_all(void) {
    for (unsigned i = 0; i < child_count; ++i) {
        struct child *c = &children[i];
        if (c->reaped) continue;
        pid_t rc = waitpid(c->pid, &c->status, WNOHANG);
        if (rc == c->pid) {
            c->reaped = 1;
            if (WIFEXITED(c->status) && WEXITSTATUS(c->status) == 120) evidence_error = 1;
            event("supervisor", "reaped", "child_pid=%ld raw_status=%d", (long)c->pid, c->status);
        } else if (rc == -1 && errno != EINTR) evidence_error = 1;
    }
}

static void receive_line(void) {
    partial[used]=0;
    const char *end;
    cJSON *o=cJSON_ParseWithLengthOpts(partial,used+1,&end,1);
    char *render=o ? cJSON_PrintUnformatted(o) : NULL;
    int valid=render && !strcmp(render,partial);
    cJSON_free(render);
    if (!valid || !json_tree(o,0) || !json_keys(o,"kind schema_version run_id case_id attempt_id cycle service_instance_id producer pid seq ns event data") ||
        !json_string(o,"kind") || strcmp(json_string(o,"kind"),"producer-event") ||
        !json_integer(o,"schema_version",1,1,NULL) || !cJSON_IsObject(cJSON_GetObjectItemCaseSensitive(o,"data"))) goto invalid;
    const char *ids[]={"run_id","case_id","attempt_id","service_instance_id"};
    for (unsigned i=0; i<4; ++i)
        if (!json_string(o,ids[i]) || strcmp(json_string(o,ids[i]),json_string(plan.root,ids[i]))) goto invalid;
    const cJSON *cycle=cJSON_GetObjectItemCaseSensitive(o,"cycle");
    if (!cJSON_IsNumber(cycle) || cycle->valuedouble!=cJSON_GetObjectItemCaseSensitive(plan.root,"cycle")->valuedouble) goto invalid;
    int known=0;
    const char *producer=json_string(o,"producer");
    for (unsigned i=0; i<child_count; ++i)
        if (field(o,"pid")==children[i].pid && producer && !strcmp(producer,children[i].producer)) known=1;
    if (!known || field(o,"ns")<0 || field(o,"seq")<1 || !json_string(o,"event") || count==MAX_EVENTS) goto invalid;
    int previous=0;
    for (unsigned i=count; i>0; --i) {
        if (field(events[i-1],"pid")!=field(o,"pid")) continue;
        previous=1;
        if (field(o,"seq")!=field(events[i-1],"seq")+1 || field(o,"ns")<field(events[i-1],"ns")) goto invalid;
        break;
    }
    if (!previous && field(o,"seq")!=1) goto invalid;
    events[count++]=o;
    json_write(o); used=0; return;
 invalid:
    cJSON_Delete(o); used=0; evidence_error=1;
    event("supervisor","evidence_error","reason=invalid_producer_frame");
}

static void pump(uint64_t deadline) {
    deadline = bounded(deadline);
    uint64_t now = mono_ns();
    int ms = now >= deadline ? 0 : (int)((deadline - now + 999999ULL) / 1000000ULL);
    if (ms > 25) ms = 25;
    struct pollfd pfd = {.fd = channel[0], .events = POLLIN};
    int result = poll(&pfd, 1, ms);
    if (result == -1 && errno != EINTR) evidence_error = 1;
    if (result > 0 && (pfd.revents & (POLLERR | POLLNVAL | POLLHUP))) evidence_error = 1;
    if (result > 0 && (pfd.revents & POLLIN)) {
        char chunk[1024];
        ssize_t n = read(channel[0], chunk, sizeof(chunk));
        if (n <= 0 && errno != EAGAIN && errno != EINTR) evidence_error = 1;
        for (ssize_t i = 0; i < n; ++i) {
            if (chunk[i] == '\n') receive_line();
            else if (used < sizeof(partial) - 2) partial[used++] = chunk[i];
            else { evidence_error = 1; used = 0; }
        }
    }
    reap_all();
}

static struct child *spawn_child(int fixture, const char *argument) {
    const char *binary=fixture ? plan.adapter->fixture_binary : "worker";
    if (child_count == MAX_CHILDREN) { evidence_error = 1; return NULL; }
    char exe[1200];
    snprintf(exe, sizeof(exe), "%s/%s", directory, binary);
    char *args[] = {exe, fixture ? service_path : (char *)plan_path, (char *)argument, NULL};
    posix_spawn_file_actions_t actions;
    int error = posix_spawn_file_actions_init(&actions);
    if (error) { evidence_error = 1; return NULL; }
    error = posix_spawn_file_actions_adddup2(&actions, channel[1], STDOUT_FILENO);
    if (!error) error = posix_spawn_file_actions_addclose(&actions, channel[0]);
    if (!error) error = posix_spawn_file_actions_addclose(&actions, channel[1]);
    struct child *c = &children[child_count];
    if (!error) error = posix_spawn(&c->pid, exe, &actions, NULL, args, environ);
    posix_spawn_file_actions_destroy(&actions);
    if (error) { event("supervisor", "spawn_error", "binary=%s error=%d", binary, error); evidence_error = 1; return NULL; }
    c->producer=fixture ? "fixture" : "worker";
    ++child_count;
    event("supervisor", "spawned", "binary=%s child_pid=%ld operation=%s", binary, (long)c->pid, argument);
    return c;
}

static int await_event(pid_t pid, const char *name, unsigned after, uint64_t deadline) {
    deadline = bounded(deadline);
    int index;
    do {
        pump(deadline);
        index = find_event(pid, name, after);
        if (index != -1) return index;
    } while (!evidence_error && mono_ns() < deadline);
    return -1;
}

static void await_child(struct child *c, uint64_t deadline) {
    deadline = bounded(deadline);
    while (!c->reaped && mono_ns() < deadline) pump(deadline);
    /* Drain already queued final producer events after observing child exit. */
    for (unsigned i = 0; i < 4; ++i) pump(mono_ns());
}

static int worker(const char *op, int *event_index) {
    unsigned after = count;
    struct child *c = spawn_child(0, op);
    if (!c) return 0;
    await_child(c, mono_ns() + (uint64_t)plan.probe_ms*1000000ULL);
    const char *name = !strcmp(op, "normal") || !strcmp(op, "message") || !strcmp(op,"health") || !strcmp(op,"negative") ? "result" : "control_result";
    int index = find_event(c->pid, name, after);
    if (event_index) *event_index = index;
    return !evidence_error && index >= 0 && c->reaped && WIFEXITED(c->status) && WEXITSTATUS(c->status) == 0;
}

static void signal_owned(struct child *c, int sig) {
    reap_all();
    if (c->reaped) return;
    int rc = kill(c->pid, sig);
    int error = rc == -1 ? errno : 0;
    event("supervisor", "signal_sent", "child_pid=%ld signal=%d rc=%d error=%d", (long)c->pid, sig, rc, error);
    if (rc == -1 && error != ESRCH) evidence_error = 1;
}

static int cleanup(struct child *fixture, struct child *timed) {
    uint64_t end = mono_ns() + (uint64_t)plan.cleanup_ms*1000000ULL;
    execution_end = end; /* All stage waits share the separate cleanup bound. */
    if (timed && !timed->reaped) {
        signal_owned(timed, SIGTERM);
        await_child(timed, mono_ns() + 100000000ULL);
        event("supervisor", "termination_observation", "child_pid=%ld signal=%d reaped=%d",
              (long)timed->pid, SIGTERM, timed->reaped);
        if (!timed->reaped) {
            signal_owned(timed, SIGKILL);
            await_child(timed, mono_ns() + 100000000ULL);
            event("supervisor", "termination_observation", "child_pid=%ld signal=%d reaped=%d",
                  (long)timed->pid, SIGKILL, timed->reaped);
        }
    }
    if (fixture && !fixture->reaped) {
        event("supervisor", "fixture_stop", "child_pid=%ld blocked_worker_reaped=%d",
              (long)fixture->pid, timed ? timed->reaped : 1);
        signal_owned(fixture, SIGTERM);
        await_child(fixture, mono_ns() + 200000000ULL);
        if (!fixture->reaped) signal_owned(fixture, SIGKILL);
    }
    /* Includes any setup/probe worker that failed its own deadline. */
    for (unsigned i = 0; i < child_count; ++i)
        if (!children[i].reaped) signal_owned(&children[i], SIGKILL);
    for (unsigned i = 0; i < child_count; ++i) await_child(&children[i], end);
    int all = 1;
    for (unsigned i = 0; i < child_count; ++i) if (!children[i].reaped) all = 0;
    if (used) evidence_error = 1;
    event("supervisor", "cleanup", "all_reaped=%d evidence_error=%d", all, evidence_error);
    return all && !evidence_error;
}

int main(int argc, char **argv) {
    if (argc!=2 || !rmc_plan_load(argv[1],&plan)) { fputs("invalid scenario plan\n",stderr); return 2; }
    plan_path=argv[1]; rmc_plan_environment(&plan);
    const char *slash=strrchr(argv[0],'/');
    if (!slash || (size_t)(slash-argv[0])>=sizeof(directory)) return 2;
    memcpy(directory,argv[0],(size_t)(slash-argv[0]));
    snprintf(service_path,sizeof(service_path),"%s-%s",plan.path,json_string(plan.root,"service_instance_id"));
    rmc_manifest(&plan);
    if (plan.external || (plan.required_caps & ~plan.adapter->capabilities)) {
        event("supervisor","unsupported","reason=%s",plan.external ? "external_attach_not_implemented" : "missing_capability");
        event("supervisor","cleanup","all_reaped=1 evidence_error=0");
        event("supervisor","run_final","flow_complete=1 cleanup_ok=1 evidence_error=0");
        cJSON_Delete(plan.root); return 3;
    }
    if (pipe2(channel,O_NONBLOCK|O_CLOEXEC)==-1) { perror("pipe2"); return 2; }
    execution_end=mono_ns()+(uint64_t)plan.execution_ms*1000000ULL;
    event("supervisor","settings","mode=%s timeout_ms=%u allowance_ms=%u path=%s case_ms=%u cleanup_ms=%u",
          plan.mode,plan.operation_ms,plan.cancellation_ms,service_path,plan.execution_ms,plan.cleanup_ms);
    struct child *fixture=spawn_child(1,plan.mode), *timed=NULL;
    int flow_complete=0;
    const char *error="setup_failed";
    if (!fixture || await_event(fixture->pid,"ready",0,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)==-1) goto done;
    if (!worker("normal",NULL) || !worker("message",NULL)) goto done;
    if ((plan.adapter->capabilities & RMC_CAP_ERROR_PROBE) && !worker("negative",NULL)) goto done;
    if (!worker("hold",NULL)) goto done;
    unsigned after=count;
    struct child *released=spawn_child(0,"normal");
    if (!released || await_event(fixture->pid,"pending",after,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)==-1 ||
        !worker("release",NULL)) goto done;
    await_child(released,mono_ns()+(uint64_t)plan.probe_ms*1000000ULL);
    if (!released->reaped || !WIFEXITED(released->status) || WEXITSTATUS(released->status) ||
        find_event(released->pid,"result",after)<0 || !worker("hold",NULL)) goto done;
    event("supervisor","stage","name=deferred_release_complete");
    after=count; timed=spawn_child(0,"timed");
    if (!timed) goto done;
    int deadline_index=await_event(timed->pid,"deadline",after,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL);
    if (deadline_index<0) goto done;
    uint64_t deadline=(uint64_t)field(events[deadline_index],"deadline_ns");
    if (!deadline || deadline>execution_end) { error="invalid_operation_deadline"; goto done; }
    uint64_t completion_bound=deadline+(uint64_t)plan.cancellation_ms*1000000ULL;
    int result_index;
    do {
        pump(completion_bound);
        result_index=find_event(timed->pid,"result",after);
        if (result_index>=0 && timed->reaped) break;
    } while (!evidence_error && mono_ns()<completion_bound && mono_ns()<execution_end);
    if (mono_ns()>=execution_end) { error="case_deadline"; goto done; }
    event("supervisor","operation_bound","completion_bound_ns=%" PRIu64 " expired=%d result_observed=%d worker_reaped=%d",
          completion_bound,mono_ns()>=completion_bound,result_index>=0,timed->reaped);
    if (!worker("state",NULL)) { error="state_probe_failed"; goto done; }
    if (result_index>=0 && timed->reaped && WIFEXITED(timed->status) && !WEXITSTATUS(timed->status)) {
        if (!worker("release",NULL) || !worker("health",NULL)) { error="health_probe_failed"; goto done; }
    } else event("supervisor","health_withheld","reason=operation_incomplete");
    flow_complete=1;
 done:
    if (!flow_complete) event("supervisor","execution_error","reason=%s",mono_ns()>=execution_end ? "case_deadline" : error);
    int cleaned=cleanup(fixture,timed);
    event("supervisor","run_final","flow_complete=%d cleanup_ok=%d evidence_error=%d",flow_complete,cleaned,evidence_error);
    close(channel[0]); close(channel[1]);
    for (unsigned i=0; i<count; ++i) cJSON_Delete(events[i]);
    cJSON_Delete(plan.root);
    return flow_complete && cleaned && !evidence_error ? 0 : 2;
}
