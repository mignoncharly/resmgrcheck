#include "../common/event.h"
#include "mailbox_protocol.h"
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#include <errno.h>
#define MAX_PENDING 8
struct pending {
    int used; rcvid_t rcvid; pid_t pid; int tid, scoid, coid;
    unsigned logical, generation; iofunc_ocb_t *ocb;
};
static struct pending queue[MAX_PENDING];
/* One retained mailbox message with up to eight waiting consumers. FETCH does
 * not acknowledge it. Cancellation retires the waiter, never the message. */
static struct mailbox_state state = {.generation=1, .message_exists=1, .message_ready=1};
static unsigned next_request;
static int ignore_unblock;
static int mailbox_value=7;
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

static int mailbox_unblock(resmgr_context_t *ctp, io_pulse_t *msg, iofunc_ocb_t *ocb) {
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


static int mailbox_devctl(resmgr_context_t *ctp, io_devctl_t *msg, iofunc_ocb_t *ocb) {
    if (ctp->size < sizeof(msg->i)) return EINVAL;
    int status = iofunc_devctl_default(ctp, msg, ocb);
    if (status != _RESMGR_DEFAULT) return status;
    int cmd = msg->i.dcmd;
    if (cmd==RMC_FIXTURE_COMMAND) {
        int next=0;int rc=fixture_command(ctp,msg,ocb,&next);
        if (next) {
            state.message_exists=1;state.message_ready=0;++state.generation;mailbox_value=8;
        }
        return rc;
    }
    if (cmd == MAILBOX_IDENTITY) {
        if (!(ocb->ioflag & _IO_FLAG_RD)) return EBADF;
        int bounds=fixture_devctl_bounds(ctp,msg,sizeof(struct mailbox_identity),0);
        if (bounds) return bounds;
        struct mailbox_identity identity={.protocol=1,.pid=(uint32_t)getpid()};
        const char *tag=getenv("RMC_INSTANCE_ID");
        if (tag && strnlen(tag,sizeof(identity.instance))<sizeof(identity.instance))
            memcpy(identity.instance,tag,strlen(tag)+1);
        return fixture_devctl_reply(ctp,&identity,sizeof(identity));
    }
    if (cmd == MAILBOX_ACK) {
        if (!(ocb->ioflag & _IO_FLAG_WR)) return EBADF;
        struct mailbox_ack request;
        int bounds=fixture_devctl_bounds(ctp,msg,sizeof(request),1);
        if (bounds) return bounds;
        if (resmgr_msgread(ctp,&request,sizeof(request),sizeof(msg->i))!=sizeof(request) || request.reserved) return EINVAL;
        if (request.channel!=1 || !state.message_exists || !state.message_ready) return ENOENT;
        if (request.generation!=state.generation) return ESTALE;
        if (state.acknowledgements>=INT32_MAX) return EOVERFLOW;
        state.message_exists=state.message_ready=0;++state.acknowledgements;
        event("fixture","state_changed","action=ack generation=%u",state.generation);
        return fixture_devctl_reply(ctp,&request,sizeof(request));
    }
    if (cmd == MAILBOX_FETCH) {
        struct mailbox_result request;
        if (!(ocb->ioflag & _IO_FLAG_RD)) return EBADF;
        int bounds=fixture_devctl_bounds(ctp,msg,sizeof(request),1);
        if (bounds) return bounds;
        if (resmgr_msgread(ctp, &request, sizeof(request), sizeof(msg->i)) != sizeof(request)) return EINVAL;
        if (request.reserved) return EINVAL;
        if (!state.message_exists || request.channel != 1) return ENOENT;
        unsigned logical = ++next_request;
        event("fixture", "received", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld",
              logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid);
        if (state.message_ready) {
            request.value = mailbox_value;
            event("fixture", "sample", "logical=%u generation=%u bytes=%zu", logical, state.generation, sizeof(request));
            return fixture_devctl_reply(ctp,&request,sizeof(request));
        }
        for (unsigned i = 0; i < MAX_PENDING; ++i) {
            if (queue[i].used) continue;
            queue[i] = (struct pending){.used=1, .rcvid=ctp->rcvid, .pid=ctp->info.pid, .tid=ctp->info.tid,
                .scoid=ctp->info.scoid, .coid=ctp->info.coid, .logical=logical, .generation=state.generation, .ocb=ocb};
            ++state.pending;
            request_ocb(&queue[i]);
            event("fixture", "pending", "logical=%u generation=%u rcvid=%" PRId64 " client_pid=%ld pending=%u",
                  logical, state.generation, (int64_t)ctp->rcvid, (long)ctp->info.pid, state.pending);
            return _RESMGR_NOREPLY;
        }
        return EAGAIN;
    }
    if (cmd != MAILBOX_ARM && cmd != MAILBOX_PUBLISH && cmd != MAILBOX_STATE) return ENOTTY;
    if (!(ocb->ioflag & (cmd==MAILBOX_STATE ? _IO_FLAG_RD : _IO_FLAG_WR))) return EBADF;
    int bounds=fixture_devctl_bounds(ctp,msg,sizeof(state),0);
    if (bounds) return bounds;
    if (cmd == MAILBOX_ARM) {
        if (state.pending) return EBUSY;
        state.message_exists = 1; state.message_ready = 0; ++state.generation;
        event("fixture", "state_changed", "action=submit generation=%u", state.generation);
    } else if (cmd == MAILBOX_PUBLISH) {
        if (!state.message_exists) return ENOENT;
        state.message_ready = 1;
        for (unsigned i = 0; i < MAX_PENDING; ++i) {
            struct pending *p = &queue[i];
            if (!p->used || p->rcvid<=0 || !p->ocb) continue;
            struct { io_devctl_t header; struct mailbox_result result; } reply = {0};
            reply.header.o.nbytes = sizeof(reply.result);
            reply.result = (struct mailbox_result){.channel=1, .value=mailbox_value};
            struct _msg_info info;
            int rc = -1;
            if (MsgInfo(p->rcvid, &info) == 0 && owner(p, &info)) rc = MsgReply(p->rcvid, 0, &reply, sizeof(reply));
            terminal(p,"reply",rc,rc<0 ? errno : 0);
            event("fixture", "released", "logical=%u generation=%u rc=%d", p->logical, p->generation, rc);
            forget(p, "release");
        }
        event("fixture", "state_changed", "action=complete generation=%u", state.generation);
    }
    return fixture_devctl_reply(ctp,&state,sizeof(state));
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
    io_funcs.unblock = mailbox_unblock;
    io_funcs.close_dup = fixture_close_dup;
    io_funcs.close_ocb = fixture_close_ocb;
    io_funcs.devctl = mailbox_devctl;
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
