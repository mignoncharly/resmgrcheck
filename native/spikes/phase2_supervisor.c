#include "phase2.h"
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>

extern char **environ;
#define MAX_EVENTS 256
#define MAX_CHILDREN 16
struct child { pid_t pid; int reaped, status; };
static struct child children[MAX_CHILDREN];
static unsigned child_count, count;
static char events[MAX_EVENTS][512], partial[512];
static size_t used;
static int channel[2], evidence_error;
static uint64_t execution_end;
static char directory[1024], service_path[128], timeout_arg[16];

static uint64_t bounded(uint64_t deadline) {
    return execution_end && execution_end < deadline ? execution_end : deadline;
}

static int64_t field(const char *line, const char *key) {
    char token[64];
    snprintf(token, sizeof(token), " %s=", key);
    const char *p = strstr(line, token);
    if (!p) return -1;
    char *end;
    long long value = strtoll(p + strlen(token), &end, 10);
    return *end == ' ' || !*end ? value : -1;
}

static int named(const char *line, const char *name) {
    char token[64];
    snprintf(token, sizeof(token), " event=%s", name);
    const char *p = strstr(line, token);
    return p && (p[strlen(token)] == ' ' || p[strlen(token)] == 0);
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
    partial[used] = 0;
    if (count == MAX_EVENTS || strncmp(partial, "producer=", 9) ||
        field(partial, "pid") <= 0 || field(partial, "ns") < 0 || field(partial, "seq") <= 0 ||
        !strstr(partial, " event=")) { evidence_error = 1; used = 0; return; }
    int previous = 0;
    for (unsigned i = count; i > 0; --i) {
        if (field(events[i - 1], "pid") != field(partial, "pid")) continue;
        previous = 1;
        if (field(partial, "seq") != field(events[i - 1], "seq") + 1) evidence_error = 1;
        if (field(partial, "ns") < field(events[i - 1], "ns")) evidence_error = 1;
        break;
    }
    if (!previous && field(partial, "seq") != 1) evidence_error = 1;
    memcpy(events[count++], partial, used + 1);
    /* Only this supervisor writes the authoritative output stream. */
    partial[used++] = '\n';
    if (write(STDOUT_FILENO, partial, used) != (ssize_t)used) _exit(120);
    used = 0;
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

static struct child *spawn_child(const char *binary, const char *argument) {
    if (child_count == MAX_CHILDREN) { evidence_error = 1; return NULL; }
    char exe[1200];
    snprintf(exe, sizeof(exe), "%s/%s", directory, binary);
    char *args[] = {exe, service_path, (char *)argument, timeout_arg, NULL};
    if (!strcmp(binary, "sensor-fixture")) args[3] = NULL;
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
    struct child *c = spawn_child("sensor-client", op);
    if (!c) return 0;
    await_child(c, mono_ns() + 2000000000ULL);
    const char *name = !strcmp(op, "normal") || !strcmp(op, "message") ? "result" : "control_result";
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
    execution_end = 0; /* Cleanup has its own bound after execution stops. */
    uint64_t end = mono_ns() + 2000000000ULL;
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

static unsigned setting(const char *s, unsigned min, unsigned max) {
    char *end;
    unsigned long n = strtoul(s, &end, 10);
    return *s && !*end && n >= min && n <= max ? (unsigned)n : 0;
}

int main(int argc, char **argv) {
    if (argc != 4 || (strcmp(argv[1], "corrected") && strcmp(argv[1], "ignore-unblock"))) return 2;
    unsigned timeout_ms = setting(argv[2], 100, 5000), allowance_ms = setting(argv[3], 100, 3000);
    if (!timeout_ms || !allowance_ms) return 2;
    const char *slash = strrchr(argv[0], '/');
    if (!slash || (size_t)(slash - argv[0]) >= sizeof(directory)) return 2;
    memcpy(directory, argv[0], (size_t)(slash - argv[0]));
    snprintf(service_path, sizeof(service_path), "/dev/resmgrcheck-sensor-%ld", (long)getpid());
    snprintf(timeout_arg, sizeof(timeout_arg), "%u", timeout_ms);
    if (pipe2(channel, O_NONBLOCK | O_CLOEXEC) == -1) { perror("pipe2"); return 2; }
    execution_end = mono_ns() + 10000000000ULL;
    event("supervisor", "settings", "mode=%s timeout_ms=%u allowance_ms=%u path=%s case_ms=10000 cleanup_ms=2000",
          argv[1], timeout_ms, allowance_ms, service_path);
    struct child *fixture = spawn_child("sensor-fixture", argv[1]), *timed = NULL;
    int verdict = 2, state_index = -1;
    const char *reason = "setup_failed";
    if (!fixture || await_event(fixture->pid, "ready", 0, mono_ns() + 2000000000ULL) == -1) goto done;
    if (!worker("normal", NULL) || !worker("message", NULL) || !worker("hold", NULL)) goto done;

    /* First prove asynchronous release through a separate supervised control call. */
    unsigned after = count;
    struct child *released = spawn_child("sensor-client", "normal");
    if (!released || await_event(fixture->pid, "pending", after, mono_ns() + 2000000000ULL) == -1 ||
        !worker("release", NULL)) goto done;
    await_child(released, mono_ns() + 2000000000ULL);
    if (!released->reaped || !WIFEXITED(released->status) || WEXITSTATUS(released->status) != 0 ||
        find_event(released->pid, "result", after) == -1 || !worker("hold", NULL)) goto done;

    after = count;
    timed = spawn_child("sensor-client", "timed");
    if (!timed) goto done;
    int deadline_index = await_event(timed->pid, "deadline", after, mono_ns() + 2000000000ULL);
    if (deadline_index == -1) goto done;
    uint64_t deadline = (uint64_t)field(events[deadline_index], "deadline_ns");
    uint64_t completion_bound = deadline + (uint64_t)allowance_ms * 1000000ULL;
    int result_index;
    do {
        pump(completion_bound);
        result_index = find_event(timed->pid, "result", after);
        if (result_index >= 0 && timed->reaped) break;
    } while (!evidence_error && mono_ns() < completion_bound && mono_ns() < execution_end);
    if (mono_ns() >= execution_end) { reason = "case_deadline"; goto done; }
    int pending = find_event(fixture->pid, "pending", after);
    int unblock = find_event(fixture->pid, "unblock", after);
    reason = "precondition_not_established";
    if (pending < 0 || unblock < 0 || field(events[pending], "client_pid") != timed->pid ||
        (uint64_t)field(events[pending], "ns") >= deadline ||
        (uint64_t)field(events[unblock], "ns") < deadline ||
        field(events[pending], "logical") != field(events[unblock], "logical") ||
        field(events[pending], "generation") != field(events[unblock], "generation") ||
        field(events[unblock], "live") != 1) goto done;
    event("supervisor", "precondition", "established=1 pending_ns=%" PRId64 " deadline_ns=%" PRIu64 " unblock_ns=%" PRId64,
          field(events[pending], "ns"), deadline, field(events[unblock], "ns"));
    reason = "state_probe_failed";
    if (!worker("state", &state_index)) goto done;
    if (!strcmp(argv[1], "ignore-unblock")) {
        reason = "defect_not_reproduced";
        if (result_index < 0 && !timed->reaped && field(events[state_index], "pending") == 1 &&
            field(events[state_index], "unblocks") >= 1 &&
            find_event(fixture->pid, "ignored_unblock", after) >= 0) {
            verdict = 1; reason = "cancellation_deadline";
            event("supervisor", "watchdog", "responsive=1 completion_bound_ns=%" PRIu64 " pending=1", completion_bound);
        }
    } else {
        reason = "cancellation_contract_failed";
        int completed = find_event(fixture->pid, "cancel_completed", after);
        if (result_index < 0 || completed < 0 || !timed->reaped || !WIFEXITED(timed->status) || WEXITSTATUS(timed->status) ||
            field(events[result_index], "rc") != -1 || field(events[result_index], "error") != ETIMEDOUT ||
            (uint64_t)field(events[result_index], "ns") > completion_bound ||
            field(events[completed], "rc") != 0 || field(events[state_index], "pending") != 0 ||
            field(events[state_index], "completed") != 1 || !worker("release", NULL) || !worker("normal", NULL)) {
            verdict = 1; goto done;
        }
        verdict = 0; reason = "cancellation_completed_and_healthy";
    }
done:
    if (verdict == 2 && mono_ns() >= execution_end) reason = "case_deadline";
    if (!cleanup(fixture, timed)) { verdict = 2; reason = "cleanup_or_evidence_error"; }
    event("supervisor", "verdict", "result=%s reason=%s", verdict == 0 ? "PASS" : verdict == 1 ? "FAIL" : "ERROR", reason);
    event("supervisor", "final", "complete=1");
    close(channel[0]); close(channel[1]);
    return verdict;
}
