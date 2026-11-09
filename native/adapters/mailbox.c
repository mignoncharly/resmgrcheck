#include "../adapter_v1.h"
#include "../fixtures/mailbox_protocol.h"
#include <sys/iomsg.h>
#include <errno.h>
#include "fixture_control.h"
static int parameters(const cJSON *o) {
    if (!cJSON_IsObject(o) || !o->child || o->child->next || strcmp(o->child->string, "channel")) return 0;
    return cJSON_IsNumber(o->child) && o->child->valuedouble == 1;
}
static int control(int fd, const char *op, rmc_state *out) {
    struct mailbox_state s = {0};
    int command = !strcmp(op, "hold") ? MAILBOX_ARM : !strcmp(op, "release") ? MAILBOX_PUBLISH : MAILBOX_STATE;
    int handled;int error=barrier_control(fd,op,&handled);
    if (!handled || !error) error=devctl(fd, command, &s, sizeof(s), NULL);
    *out = (rmc_state){.pending=s.pending, .unblocks=s.unblocks, .completed=s.completed, .generation=s.generation,
        .facts={{"message_exists", (int)s.message_exists}, {"message_ready", (int)s.message_ready}, {"acknowledgements", (int)s.acknowledgements}}, .fact_count=3};
    return error;
}
static void decode(const struct mailbox_result *out, rmc_result *r) {
    if (out->channel != 1 || out->reserved) { r->outcome = RMC_INVALID_REPLY; return; }
    r->facts[0] = (rmc_fact){"value", out->value};
    r->facts[1] = (rmc_fact){"channel", (int)out->channel}; r->fact_count = 2;
}
static void ordinary(int fd, int negative, rmc_result *r) {
    struct mailbox_result out = {.channel=negative ? 2 : 1};
    int info = -1; errno = 0;
    int raw = devctl(fd, MAILBOX_FETCH, &out, sizeof(out), &info);
    r->raw_return = raw; r->raw_errno = errno; r->api = "devctl";
    /* devctl returns an error value directly. errno is preserved as an independent observation. */
    rmc_normalize(r, raw);
    if (r->outcome == RMC_OK) {
        if (info != 0) r->outcome = RMC_INVALID_REPLY;
        else decode(&out, r);
    }
}
struct message { io_devctl_t header; struct mailbox_result payload; };
static void prepare(rmc_prepared *p) {
    memset(p, 0, sizeof(*p));
    struct message *m = (struct message *)p->input.bytes;
    m->header.i.type = _IO_DEVCTL; m->header.i.combine_len = sizeof(m->header.i);
    m->header.i.dcmd = MAILBOX_FETCH; m->header.i.nbytes = sizeof(m->payload);
    m->payload.channel = 1;
    SETIOV(&p->send[0], &m->header.i, sizeof(m->header.i));
    SETIOV(&p->send[1], &m->payload, sizeof(m->payload));
    SETIOV(&p->receive[0], p->output.bytes, sizeof(struct message));
    p->send_parts = 2; p->receive_parts = 1;
}
static void finish(const rmc_prepared *p, int raw, int error, rmc_result *r) {
    r->api = "MsgSendv"; r->raw_return = raw; r->raw_errno = error;
    rmc_normalize(r, raw == -1 ? error : 0);
    if (r->outcome == RMC_OK) {
        const struct message *m = (const struct message *)p->output.bytes;
        if (raw != 0 || m->header.o.ret_val || m->header.o.nbytes != sizeof(m->payload) || m->header.o.zero || m->header.o.zero2)
            r->outcome = RMC_INVALID_REPLY;
        else decode(&m->payload, r);
    }
}
const rmc_adapter_v1 mailbox_adapter_v1 = {
    .abi=RMC_ADAPTER_ABI, .struct_size=sizeof(rmc_adapter_v1), .id="mailbox-v1", .operation_id="fetch-message",
    .fixture_binary="mailbox-v1-fixture", .convention="devctl", .result_fact_keys="value channel", .state_fact_keys="message_exists message_ready acknowledgements",
    /* Only the initial qualified timeout/read-only surface is advertised.
     * Signal/departure/repeat/ordering need separate native qualification. */
    .capabilities=RMC_BASE_CAPS | RMC_CAP_ERROR_PROBE | RMC_CAP_EXTERNAL_HEALTH, .validate_parameters=parameters, .control=control, .ordinary=ordinary, .prepare=prepare, .finish=finish
};
