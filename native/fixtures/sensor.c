#include "../spikes/phase2.h"
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>

#define MAX_PENDING 8
struct pending {
    int used;
    rcvid_t rcvid;
    pid_t pid;
    int tid, scoid, coid;
    unsigned logical, generation;
    size_t bytes;
    iofunc_ocb_t *ocb;
};
static struct pending queue[MAX_PENDING];
static struct sensor_state state = {.generation = 1};
static unsigned next_request;
static int hold, ignore_unblock;
static int sample_value=42;
static char sample[64]=SAMPLE;

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

#include "lifecycle.h"

static int sensor_read(resmgr_context_t *ctp, io_read_t *msg, iofunc_ocb_t *ocb) {
    int error = iofunc_read_verify(ctp, msg, ocb, NULL);
    if (error != EOK) return error;
    if ((msg->i.xtype & _IO_XTYPE_MASK) != _IO_XTYPE_NONE) return ENOSYS;
    if (!msg->i.nbytes) { _IO_SET_READ_NBYTES(ctp, 0); return EOK; }
    size_t bytes = msg->i.nbytes < strlen(sample) ? msg->i.nbytes : strlen(sample);
    unsigned logical = ++next_request;
    event("fixture", "received", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld",
          logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid);
    if (!hold) {
        _IO_SET_READ_NBYTES(ctp, bytes);
        event("fixture", "sample", "logical=%u generation=%u bytes=%zu", logical, state.generation, bytes);
        return _RESMGR_PTR(ctp, sample, bytes);
    }
    for (unsigned i = 0; i < MAX_PENDING; ++i) {
        if (queue[i].used) continue;
        queue[i] = (struct pending){.used = 1, .rcvid = ctp->rcvid,
            .pid = ctp->info.pid, .tid = ctp->info.tid, .scoid = ctp->info.scoid,
            .coid = ctp->info.coid, .logical = logical, .generation = state.generation,
            .bytes = bytes, .ocb = ocb};
        ++state.pending;
        request_ocb(&queue[i]);
        event("fixture", "pending", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld pending=%u",
              logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid, state.pending);
        return _RESMGR_NOREPLY;
    }
    return EAGAIN;
}

static int sensor_unblock(resmgr_context_t *ctp, io_pulse_t *msg, iofunc_ocb_t *ocb) {
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
              p->logical, p->generation, (int64_t)p->rcvid, fixture_mode);
        remember_unblock(p);
        if (completion_barrier) {
            completion_barrier=0;
            event("fixture","barrier_wait","logical=%u generation=%u rcvid=%" PRId64,p->logical,p->generation,(int64_t)p->rcvid);
            return _RESMGR_NOREPLY;
        }
        if (ignore_unblock) {
            event("fixture", "ignored_unblock", "logical=%u generation=%u pending=%u",
                  p->logical, p->generation, state.pending);
            return _RESMGR_NOREPLY;
        }
        /* -1 is valid only here: a live, owned, current unblock request. */
        int rc = MsgError(p->rcvid, -1);
        int error = rc == -1 ? errno : 0;
        terminal(p,"cancel",rc,error);
        if (rc == 0) ++state.completed;
        event("fixture", "cancel_completed", "logical=%u generation=%u rc=%d error=%d",
              p->logical, p->generation, rc, error);
        if (rc!=0 || !retain_waiter(p)) forget(p, rc == 0 ? "cancellation" : "reply_error");
        return _RESMGR_NOREPLY;
    }
    event("fixture", "unmatched_unblock", "rcvid=%" PRId64, (int64_t)ctp->rcvid);
    (void)unmatched_park(ctp,&info);
    return _RESMGR_NOREPLY;
}


static int sensor_devctl(resmgr_context_t *ctp, io_devctl_t *msg, iofunc_ocb_t *ocb) {
    int status = iofunc_devctl_default(ctp, msg, ocb);
    if (status != _RESMGR_DEFAULT) return status;
    int cmd = msg->i.dcmd;
    if (cmd==RMC_FIXTURE_COMMAND) {
        int next;int rc=fixture_command(ctp,msg,ocb,&next);
        if (next) {
            hold=1;++state.generation;sample_value=43;snprintf(sample,sizeof(sample),"sample=%d\n",sample_value);
        }
        return rc;
    }
    if (cmd != SENSOR_HOLD && cmd != SENSOR_RELEASE && cmd != SENSOR_STATE) return ENOTTY;
    if (msg->i.nbytes != sizeof(state)) return EINVAL;
    if (cmd == SENSOR_HOLD) {
        if (state.pending) return EBUSY;
        hold = 1;
        ++state.generation;
    } else if (cmd == SENSOR_RELEASE) {
        hold = 0;
        for (unsigned i = 0; i < MAX_PENDING; ++i) {
            struct pending *p = &queue[i];
            if (!p->used || p->rcvid<=0 || !p->ocb) continue;
            struct _msg_info info;
            int rc = -1;
            if (MsgInfo(p->rcvid, &info) == 0 && owner(p, &info))
                rc = MsgReply(p->rcvid, (long)p->bytes, sample, p->bytes);
            terminal(p,"reply",rc,rc<0 ? errno : 0);
            event("fixture", "released", "logical=%u generation=%u rc=%d", p->logical, p->generation, rc);
            forget(p, "release");
        }
    }
    memset(&msg->o, 0, sizeof(msg->o));
    msg->o.nbytes = sizeof(state);
    memcpy(_DEVCTL_DATA(msg->o), &state, sizeof(state));
    return _RESMGR_PTR(ctp, &msg->o, sizeof(msg->o) + sizeof(state));
}

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    const char *mode = argc == 2 ? "corrected" : argv[2];
    if (strcmp(mode,"corrected") && strcmp(mode,"ignore-unblock") && strcmp(mode,"retain-waiter") && strcmp(mode,"retain-third") && strcmp(mode,"duplicate-terminal")) return 2;
    fixture_mode=mode;
    ignore_unblock = !strcmp(mode, "ignore-unblock");
    dispatch_t *dpp = dispatch_create();
    if (!dpp) { perror("dispatch_create"); return 2; }
    resmgr_connect_funcs_t connect_funcs;
    resmgr_io_funcs_t io_funcs;
    iofunc_attr_t attr;
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &connect_funcs, _RESMGR_IO_NFUNCS, &io_funcs);
    io_funcs.read = sensor_read;
    io_funcs.unblock = sensor_unblock;
    io_funcs.close_dup = fixture_close_dup;
    io_funcs.close_ocb = fixture_close_ocb;
    io_funcs.devctl = sensor_devctl;
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
