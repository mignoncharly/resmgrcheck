#include "../common/event.h"
#include "job_protocol.h"
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#include <errno.h>
#define MAX_PENDING 8
struct pending {
    int used; rcvid_t rcvid; pid_t pid; int tid, scoid, coid;
    unsigned logical, generation; iofunc_ocb_t *ocb;
};
static struct pending queue[MAX_PENDING];
/* One bounded lab job slot, with up to eight independent waiters. The fixture
 * owns the job; short-lived submitters/waiters do not own its lifetime. */
static struct job_state state = {.generation=1, .job_exists=1, .job_ready=1};
static unsigned next_request;
static int ignore_unblock;
static int owner(const struct pending *p, const struct _msg_info *info) {
    return p->pid == info->pid && p->tid == info->tid &&
           p->scoid == info->scoid && p->coid == info->coid;
}

static void forget(struct pending *p, const char *reason) {
    p->used = 0;
    --state.pending;
    event("fixture", "removed", "logical=%u generation=%u pending=%u reason=%s",
          p->logical, p->generation, state.pending, reason);
}

static int job_unblock(resmgr_context_t *ctp, io_pulse_t *msg, iofunc_ocb_t *ocb) {
    int status = iofunc_unblock_default(ctp, msg, ocb);
    if (status != _RESMGR_DEFAULT) return status;
    struct _msg_info info;
    if (MsgInfo(ctp->rcvid, &info) == -1 || !(info.flags & _NTO_MI_UNBLOCK_REQ)) {
        event("fixture", "obsolete_unblock", "rcvid=%" PRId64, (int64_t)ctp->rcvid);
        return _RESMGR_NOREPLY;
    }
    for (unsigned i = 0; i < MAX_PENDING; ++i) {
        struct pending *p = &queue[i];
        if (!p->used || p->rcvid != ctp->rcvid || p->ocb != ocb || !owner(p, &info)) continue;
        ++state.unblocks;
        event("fixture", "unblock", "logical=%u generation=%u rcvid=%" PRId64 " live=1 mode=%s",
              p->logical, p->generation, (int64_t)p->rcvid, ignore_unblock ? "ignore-unblock" : "corrected");
        if (ignore_unblock) {
            event("fixture", "ignored_unblock", "logical=%u generation=%u pending=%u",
                  p->logical, p->generation, state.pending);
            return _RESMGR_NOREPLY;
        }
        /* -1 is valid only here: a live, owned, current unblock request. */
        int rc = MsgError(p->rcvid, -1);
        int error = rc == -1 ? errno : 0;
        if (rc == 0) ++state.completed;
        event("fixture", "cancel_completed", "logical=%u generation=%u rc=%d error=%d",
              p->logical, p->generation, rc, error);
        forget(p, rc == 0 ? "cancellation" : "reply_error");
        return _RESMGR_NOREPLY;
    }
    event("fixture", "unmatched_unblock", "rcvid=%" PRId64, (int64_t)ctp->rcvid);
    return _RESMGR_NOREPLY;
}

static int job_close(resmgr_context_t *ctp, io_close_t *msg, iofunc_ocb_t *ocb) {
    /* Single dispatch thread; the fixture's Phase 2 clients each own one fd.
     * Never reply to a synthetic close's rcvid (which may be zero). */
    for (unsigned i = 0; i < MAX_PENDING; ++i) {
        struct pending *p = &queue[i];
        if (!p->used || p->ocb != ocb || p->scoid != ctp->info.scoid) continue;
        struct _msg_info info;
        if (MsgInfo(p->rcvid, &info) == 0 && owner(p, &info)) MsgError(p->rcvid, ECANCELED);
        forget(p, "close");
    }
    return iofunc_close_dup_default(ctp, msg, ocb);
}

static int job_devctl(resmgr_context_t *ctp, io_devctl_t *msg, iofunc_ocb_t *ocb) {
    int status = iofunc_devctl_default(ctp, msg, ocb);
    if (status != _RESMGR_DEFAULT) return status;
    int cmd = msg->i.dcmd;
    if (cmd == JOB_WAIT_RESULT) {
        struct job_result request;
        if (msg->i.nbytes != sizeof(request) ||
            ctp->info.srcmsglen < (ssize_t)(sizeof(msg->i) + sizeof(request)) ||
            resmgr_msgread(ctp, &request, sizeof(request), sizeof(msg->i)) != sizeof(request)) return EINVAL;
        if (request.reserved) return EINVAL;
        if (!state.job_exists || request.job_id != 1) return ENOENT;
        unsigned logical = ++next_request;
        event("fixture", "received", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld",
              logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid);
        if (state.job_ready) {
            request.value = 420;
            memset(&msg->o, 0, sizeof(msg->o)); msg->o.nbytes = sizeof(request);
            memcpy(_DEVCTL_DATA(msg->o), &request, sizeof(request));
            event("fixture", "sample", "logical=%u generation=%u bytes=%zu", logical, state.generation, sizeof(request));
            return _RESMGR_PTR(ctp, &msg->o, sizeof(msg->o) + sizeof(request));
        }
        for (unsigned i = 0; i < MAX_PENDING; ++i) {
            if (queue[i].used) continue;
            queue[i] = (struct pending){.used=1, .rcvid=ctp->rcvid, .pid=ctp->info.pid, .tid=ctp->info.tid,
                .scoid=ctp->info.scoid, .coid=ctp->info.coid, .logical=logical, .generation=state.generation, .ocb=ocb};
            ++state.pending;
            event("fixture", "pending", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld pending=%u",
                  logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid, state.pending);
            return _RESMGR_NOREPLY;
        }
        return EAGAIN;
    }
    if (cmd != JOB_SUBMIT && cmd != JOB_COMPLETE && cmd != JOB_STATE) return ENOTTY;
    if (msg->i.nbytes != sizeof(state)) return EINVAL;
    if (cmd == JOB_SUBMIT) {
        if (state.pending) return EBUSY;
        state.job_exists = 1; state.job_ready = 0; ++state.generation;
        event("fixture", "state_changed", "action=submit generation=%u", state.generation);
    } else if (cmd == JOB_COMPLETE) {
        if (!state.job_exists) return ENOENT;
        state.job_ready = 1;
        for (unsigned i = 0; i < MAX_PENDING; ++i) {
            struct pending *p = &queue[i];
            if (!p->used) continue;
            struct { io_devctl_t header; struct job_result result; } reply = {0};
            reply.header.o.nbytes = sizeof(reply.result);
            reply.result = (struct job_result){.job_id=1, .value=420};
            struct _msg_info info;
            int rc = -1;
            if (MsgInfo(p->rcvid, &info) == 0 && owner(p, &info)) rc = MsgReply(p->rcvid, 0, &reply, sizeof(reply));
            event("fixture", "released", "logical=%u generation=%u rc=%d", p->logical, p->generation, rc);
            forget(p, "release");
        }
        event("fixture", "state_changed", "action=complete generation=%u", state.generation);
    }
    memset(&msg->o, 0, sizeof(msg->o)); msg->o.nbytes = sizeof(state);
    memcpy(_DEVCTL_DATA(msg->o), &state, sizeof(state));
    return _RESMGR_PTR(ctp, &msg->o, sizeof(msg->o) + sizeof(state));
}
int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    const char *mode = argc == 2 ? "corrected" : argv[2];
    if (strcmp(mode, "corrected") && strcmp(mode, "ignore-unblock")) return 2;
    ignore_unblock = !strcmp(mode, "ignore-unblock");
    dispatch_t *dpp = dispatch_create();
    if (!dpp) { perror("dispatch_create"); return 2; }
    resmgr_connect_funcs_t connect_funcs;
    resmgr_io_funcs_t io_funcs;
    iofunc_attr_t attr;
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &connect_funcs, _RESMGR_IO_NFUNCS, &io_funcs);
    io_funcs.unblock = job_unblock;
    io_funcs.close_dup = job_close;
    io_funcs.devctl = job_devctl;
    iofunc_attr_init(&attr, S_IFCHR | 0600, NULL, NULL);
    resmgr_attr_t rattr = {.nparts_max = 1, .msg_max_size = 2048};
    if (resmgr_attach(dpp, &rattr, argv[1], _FTYPE_ANY, 0, &connect_funcs, &io_funcs, &attr) == -1) {
        perror("resmgr_attach"); return 2;
    }
    dispatch_context_t *ctx = dispatch_context_alloc(dpp);
    if (!ctx) { perror("dispatch_context_alloc"); return 2; }
    event("fixture", "ready", "path=%s mode=%s", argv[1], mode);
    for (;;) {
        ctx = dispatch_block(ctx);
        if (!ctx) { perror("dispatch_block"); return 2; }
        dispatch_handler(ctx);
    }
}
