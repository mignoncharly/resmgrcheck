#ifndef RMC_FIXTURE_MESSAGE_BOUNDS_H
#define RMC_FIXTURE_MESSAGE_BOUNDS_H
/* Fixed lab messages only. ctp->size describes the current combine component;
 * srcmsglen/nbytes/combine_len alone cannot establish its payload boundary.
 * The registered lab protocol does not accept combined custom operations. */
static int fixture_devctl_bounds(resmgr_context_t *ctp, const io_devctl_t *msg,
                                size_t bytes, int input) {
    if (ctp->rcvid <= 0 || ctp->size != (size_t)ctp->info.srcmsglen || ctp->size != sizeof(msg->i) + (input ? bytes : 0) ||
        msg->i.nbytes != bytes) return EINVAL;
    if (sizeof(msg->o) + bytes > ctp->msg_max_size ||
        ctp->info.dstmsglen < (ssize_t)(sizeof(msg->o) + bytes)) return EMSGSIZE;
    return EOK;
}
static int fixture_devctl_reply(resmgr_context_t *ctp, const void *data, size_t bytes) {
    io_devctl_t *reply = (io_devctl_t *)ctp->msg;
    if (sizeof(reply->o) + bytes > ctp->msg_max_size) return EMSGSIZE;
    /* Use the start of the allocated receive buffer, never a combine component
     * near its end. The caller saved/validated all input before this write. */
    memset(&reply->o, 0, sizeof(reply->o));
    reply->o.nbytes = bytes;
    memcpy(_DEVCTL_DATA(reply->o), data, bytes);
    return _RESMGR_PTR(ctp, &reply->o, sizeof(reply->o) + bytes);
}
#endif
