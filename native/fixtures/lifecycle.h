/* Included after the fixture's private queue/owner/forget definitions.
 * One dispatch thread serializes the queue, callbacks and all barriers. */
#include "control_v1.h"
static const char *fixture_mode="corrected";
static int completion_barrier;
static struct pending saved_notification;
static rcvid_t parked_rcvid;
static struct _msg_info parked_owner;
static iofunc_ocb_t *parked_ocb;
static struct { iofunc_ocb_t *pointer;unsigned id; } ocbs[32];
static unsigned next_ocb;
static int defect(const char *name) { return !strcmp(fixture_mode,name); }
static unsigned ocb_id(iofunc_ocb_t *ocb) {
    for (unsigned i=0;i<32;++i) if (ocbs[i].pointer==ocb) return ocbs[i].id;
    for (unsigned i=0;i<32;++i) if (!ocbs[i].pointer) { ocbs[i].pointer=ocb;ocbs[i].id=++next_ocb;return ocbs[i].id; }
    _exit(120);
}
static void request_ocb(struct pending *p) {
    event("fixture","request_ocb","logical=%u generation=%u client_pid=%ld ocb=%u",p->logical,p->generation,(long)p->pid,ocb_id(p->ocb));
}
static void remember_unblock(struct pending *p) {
    saved_notification=*p;
    /* A saved notification owns immutable identifiers, never an OCB reference. */
    saved_notification.ocb=NULL;
}
static void terminal(struct pending *p,const char *action,int rc,int error) {
    event("fixture","terminal_attempt","logical=%u generation=%u rcvid=%" PRId64 " action=%s rc=%d error=%d",p->logical,p->generation,(int64_t)p->rcvid,action,rc,error);
    if (defect("duplicate-terminal") && saved_notification.logical==p->logical && saved_notification.generation==p->generation) {
        int again=MsgError(p->rcvid,ECANCELED),err=again<0 ? errno : 0;
        event("fixture","terminal_attempt","logical=%u generation=%u rcvid=%" PRId64 " action=duplicate rc=%d error=%d",p->logical,p->generation,(int64_t)p->rcvid,again,err);
    }
}
static int retain_waiter(struct pending *p) {
    if (!defect("retain-waiter") && !(defect("retain-third") && state.unblocks>=3)) return 0;
    /* Deliberate logical leak. Retire all live IPC/OCB references so the negative
     * control cannot dereference a freed OCB or reply to a reused receive ID. */
    p->rcvid=0;p->ocb=NULL;
    event("fixture","retained_request","logical=%u generation=%u pending=%u",p->logical,p->generation,state.pending);
    return 1;
}
static void close_requests(resmgr_context_t *ctp,iofunc_ocb_t *ocb,int final) {
    for (unsigned i=0;i<MAX_PENDING;++i) {
        struct pending *p=&queue[i];
        if (!p->used || p->ocb!=ocb || (!final && p->scoid!=ctp->info.scoid)) continue;
        struct _msg_info info;
        if (p->rcvid>0 && MsgInfo(p->rcvid,&info)==0 && owner(p,&info)) {
            int rc=MsgError(p->rcvid,ECANCELED);terminal(p,"close",rc,rc<0 ? errno : 0);
        }
        forget(p,"close");p->ocb=NULL;
    }
    if (parked_ocb==ocb) { parked_ocb=NULL;parked_rcvid=0; }
}
static int fixture_close_dup(resmgr_context_t *ctp,io_close_t *msg,iofunc_ocb_t *ocb) {
    unsigned id=ocb_id(ocb);
    event("fixture","close_dup","ocb=%u client_pid=%ld rcvid=%" PRId64 " synthetic=%d",id,(long)ctp->info.pid,(int64_t)ctp->rcvid,ctp->rcvid==0);
    close_requests(ctp,ocb,0);
    int rc=iofunc_close_dup_default(ctp,msg,ocb);
    /* Do not touch ocb after delegation. Only the saved scalar is used. */
    event("fixture","close_dup_default","ocb=%u status=%d",id,rc);
    return rc;
}
static int fixture_close_ocb(resmgr_context_t *ctp,void *reserved,iofunc_ocb_t *ocb) {
    unsigned id=ocb_id(ocb);
    close_requests(ctp,ocb,1);
    event("fixture","close_ocb","ocb=%u",id);
    for (unsigned i=0;i<32;++i) if (ocbs[i].pointer==ocb) ocbs[i].pointer=NULL;
    int rc=iofunc_close_ocb_default(ctp,reserved,ocb);
    event("fixture","close_ocb_default","ocb=%u status=%d",id,rc);
    return rc;
}
static void drain_stale(void) {
    struct pending *p=&saved_notification;struct _msg_info info;
    int valid=p->rcvid>0 && MsgInfo(p->rcvid,&info)==0 && (info.flags&_NTO_MI_UNBLOCK_REQ);
    int matched=0;
    for (unsigned i=0;i<MAX_PENDING;++i) if (queue[i].used && queue[i].rcvid==p->rcvid && queue[i].logical==p->logical && queue[i].generation==p->generation && valid && owner(p,&info)) matched=1;
    event("fixture","stale_checked","logical=%u generation=%u rcvid=%" PRId64 " live=%d matched=%d",p->logical,p->generation,(int64_t)p->rcvid,valid,matched);
    if (!valid) event("fixture","obsolete_unblock","rcvid=%" PRId64,(int64_t)p->rcvid);
    else if (!matched) event("fixture","unmatched_unblock","rcvid=%" PRId64,(int64_t)p->rcvid);
    /* No replayed cancellation is committed; an active match is an explicit
     * failed ordering precondition, never permission to reply to a cached ID. */
}
static int fixture_command(resmgr_context_t *ctp,io_devctl_t *msg,iofunc_ocb_t *ocb,int *next) {
    struct rmc_fixture_command command;
    if (msg->i.nbytes!=sizeof(command) || ctp->info.srcmsglen<(ssize_t)(sizeof(msg->i)+sizeof(command)) || resmgr_msgread(ctp,&command,sizeof(command),sizeof(msg->i))!=sizeof(command)) return EINVAL;
    *next=0;
    switch(command.action) {
    case RMC_SET_CYCLE: {
        if (!command.cycle || command.cycle>20 || state.pending) return EINVAL;
        char value[16];snprintf(value,sizeof(value),"%u",command.cycle);
        if (setenv("RMC_CYCLE",value,1)) return errno;
        event("fixture","cycle_ready","cycle=%u pending=%u generation=%u",command.cycle,state.pending,state.generation);break;
    }
    case RMC_ARM_COMPLETE: if (command.cycle) return EINVAL;completion_barrier=1;break;
    case RMC_DRAIN_STALE: if (command.cycle || !saved_notification.logical) return EINVAL;drain_stale();break;
    case RMC_HOLD_NEXT: if (command.cycle || state.pending) return EBUSY;*next=1;break;
    case RMC_PARK:
        if (command.cycle || parked_rcvid) return EBUSY;
        parked_rcvid=ctp->rcvid;parked_owner=ctp->info;parked_ocb=ocb;
        event("fixture","parked","client_pid=%ld rcvid=%" PRId64,(long)ctp->info.pid,(int64_t)ctp->rcvid);
        return _RESMGR_NOREPLY;
    default:return EINVAL;
    }
    memset(&msg->o,0,sizeof(msg->o));msg->o.nbytes=sizeof(command);
    memcpy(_DEVCTL_DATA(msg->o),&command,sizeof(command));
    return _RESMGR_PTR(ctp,&msg->o,sizeof(msg->o)+sizeof(command));
}
static int unmatched_park(resmgr_context_t *ctp,const struct _msg_info *info) {
    if (parked_rcvid!=ctp->rcvid || parked_owner.pid!=info->pid || parked_owner.tid!=info->tid || parked_owner.scoid!=info->scoid || parked_owner.coid!=info->coid) return 0;
    int rc=MsgError(parked_rcvid,-1),error=rc<0 ? errno : 0;
    event("fixture","park_completed","client_pid=%ld rcvid=%" PRId64 " rc=%d error=%d",(long)info->pid,(int64_t)parked_rcvid,rc,error);
    parked_rcvid=0;parked_ocb=NULL;return 1;
}
