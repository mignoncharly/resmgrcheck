#define _QNX_SOURCE 1
#include <sys/dispatch.h>
#include <sys/iofunc.h>
#include <sys/neutrino.h>
#include <sys/wait.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

extern char **environ;
#define CHECK(x) do { if (!(x)) { perror(#x); return 1; } } while (0)

static uint64_t monotonic_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == -1) { perror("clock_gettime"); exit(1); }
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static int reap(pid_t pid) {
    uint64_t deadline = monotonic_ns() + 2000000000ULL;
    int status;
    do {
        pid_t result = waitpid(pid, &status, WNOHANG);
        if (result == pid) return WIFEXITED(status) && WEXITSTATUS(status) == 0;
        if (result == -1) return 0;
        nanosleep(&(struct timespec){.tv_nsec = 1000000}, NULL);
    } while (monotonic_ns() < deadline);
    kill(pid, SIGKILL);
    return 0;
}

int main(int argc, char **argv) {
    dispatch_t *dpp = dispatch_create();
    CHECK(dpp != NULL);
    resmgr_connect_funcs_t connect_funcs;
    resmgr_io_funcs_t io_funcs;
    iofunc_attr_t attr;
    resmgr_attr_t rattr = {.nparts_max = 1, .msg_max_size = 2048};
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &connect_funcs, _RESMGR_IO_NFUNCS, &io_funcs);
    iofunc_attr_init(&attr, S_IFCHR | 0600, NULL, NULL);
    int id = resmgr_attach(dpp, &rattr, "/dev/resmgrcheck-capability", _FTYPE_ANY,
                           0, &connect_funcs, &io_funcs, &attr);
    CHECK(id != -1);
    dispatch_context_t *ctx = dispatch_context_alloc(dpp);
    CHECK(ctx != NULL);
    dispatch_context_free(ctx);
    CHECK(resmgr_detach(dpp, id, _RESMGR_DETACH_ALL) != -1);
    CHECK(dispatch_destroy(dpp) != -1);
    puts("PASS dispatch/resource-manager attach/detach");

    uint64_t start = monotonic_ns();
    int chid = ChannelCreate(0);
    CHECK(chid != -1);
    int fds[2];
    CHECK(pipe(fds) == 0);
    pid_t child = fork();
    CHECK(child != -1);
    if (child == 0) {
        close(fds[0]);
        int coid = ConnectAttach(0, getppid(), chid, _NTO_SIDE_CHANNEL, 0);
        char reply[8] = {0};
        uint64_t limit = 1000000000ULL;
        if (coid == -1) _exit(2);
        if (TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                         NULL, &limit, NULL) == -1) _exit(3);
        int result = MsgSend(coid, "probe", 6, reply, sizeof(reply));
        if (result != 0 || strcmp(reply, "ok") != 0) _exit(4);
        if (ConnectDetach(coid) == -1 || write(fds[1], "P", 1) != 1) _exit(5);
        close(fds[1]);
        _exit(0);
    }
    close(fds[1]);
    char buffer[64] = {0};
    uint64_t limit = 2000000000ULL;
    CHECK(TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &limit, NULL) == 0);
    rcvid_t rcvid = MsgReceive(chid, buffer, sizeof(buffer), NULL);
    CHECK(rcvid > 0 && strcmp(buffer, "probe") == 0);
    CHECK(MsgReply(rcvid, 0, "ok", 3) == 0);
    struct pollfd pfd = {.fd = fds[0], .events = POLLIN};
    CHECK(poll(&pfd, 1, 2000) == 1 && (pfd.revents & POLLIN));
    CHECK(read(fds[0], buffer, 1) == 1 && buffer[0] == 'P');
    close(fds[0]);
    CHECK(reap(child));
    puts("PASS fork/wait, bounded pipe/poll, Channel/Connect/MsgSend/Receive/Reply");

    limit = 10000000ULL;
    CHECK(TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &limit, NULL) == 0);
    rcvid = MsgReceive(chid, buffer, sizeof(buffer), NULL);
    CHECK(rcvid == -1 && errno == ETIMEDOUT);
    CHECK(monotonic_ns() > start);
    CHECK(ChannelDestroy(chid) == 0);
    puts("PASS CLOCK_MONOTONIC, TimerTimeout receive cancellation (ETIMEDOUT)");

    char *args[] = {argc > 1 ? argv[1] : "/proc/boot/hello-qnx", NULL};
    int error = posix_spawn(&child, args[0], NULL, NULL, args, environ);
    if (error) { errno = error; perror("posix_spawn"); return 1; }
    CHECK(reap(child));
    puts("PASS posix_spawn/wait");
    return 0;
}
