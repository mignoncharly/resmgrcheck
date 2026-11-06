#include "phase2.h"
#include <sys/iomsg.h>
#include <sys/neutrino.h>
#include <fcntl.h>

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    const char *op = argv[2];
    event("worker", "started", "operation=%s", op);
    int fd = open(argv[1], O_RDWR);
    if (fd == -1) { event("worker", "open_error", "error=%d", errno); return 2; }
    if (!strcmp(op, "hold") || !strcmp(op, "release") || !strcmp(op, "state")) {
        int cmd = !strcmp(op, "hold") ? SENSOR_HOLD : !strcmp(op, "release") ? SENSOR_RELEASE : SENSOR_STATE;
        struct sensor_state state = {0};
        int error = devctl(fd, cmd, &state, sizeof(state), NULL);
        event("worker", "control_result", "operation=%s error=%d pending=%u unblocks=%u completed=%u generation=%u",
              op, error, state.pending, state.unblocks, state.completed, state.generation);
        int rc = close(fd);
        return error == 0 && rc == 0 ? 0 : 2;
    }
    char buffer[64] = {0};
    io_read_t msg = {.i = {.type = _IO_READ, .combine_len = sizeof(msg.i),
                          .nbytes = sizeof(buffer), .xtype = _IO_XTYPE_NONE}};
    iov_t send, receive;
    SETIOV(&send, &msg.i, sizeof(msg.i));
    SETIOV(&receive, buffer, sizeof(buffer));
    int timed = !strcmp(op, "timed");
    ssize_t result;
    if (timed) {
        unsigned ms = (unsigned)strtoul(argv[3], NULL, 10);
        if (!ms || ms > 5000) return 2;
        uint64_t deadline = mono_ns() + (uint64_t)ms * 1000000ULL;
        event("worker", "deadline", "operation=timed deadline_ns=%" PRIu64 " timeout_ms=%u", deadline, ms);
        errno = 0;
        if (TimerTimeout(CLOCK_MONOTONIC, TIMER_ABSTIME | _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                         NULL, &deadline, NULL) == -1) {
            event("worker", "arm_error", "error=%d", errno); return 2;
        }
        /* Nothing except the intended send intervenes after successful arming. */
        result = MsgSendv(fd, &send, 1, &receive, 1);
    } else if (!strcmp(op, "message")) {
        errno = 0;
        result = MsgSendv(fd, &send, 1, &receive, 1);
    } else if (!strcmp(op, "normal")) {
        errno = 0;
        result = read(fd, buffer, sizeof(buffer));
    } else return 2;
    int error = errno;
    int match = result == (ssize_t)(sizeof(SAMPLE) - 1) && !memcmp(buffer, SAMPLE, sizeof(SAMPLE) - 1);
    event("worker", "result", "operation=%s api=%s rc=%zd error=%d match=%d",
          op, !strcmp(op, "normal") ? "read" : "MsgSendv", result, error, match);
    int rc = close(fd);
    int close_error = rc == -1 ? errno : 0;
    event("worker", "closed", "rc=%d error=%d", rc, close_error);
    return rc == 0 && (timed ? result == -1 && error == ETIMEDOUT : match) ? 0 : 1;
}
