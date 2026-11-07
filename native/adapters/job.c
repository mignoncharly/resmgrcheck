#include "../adapter_v1.h"
#include "../fixtures/job_protocol.h"
#include <sys/iomsg.h>
#include <errno.h>
#include "fixture_control.h"
static int parameters(const cJSON *o) {
    if (!cJSON_IsObject(o) || !o->child || o->child->next || strcmp(o->child->string, "job_id")) return 0;
    return cJSON_IsNumber(o->child) && o->child->valuedouble == 1;
}
static int control(int fd, const char *op, rmc_state *out) {
    struct job_state s = {0};
    int command = !strcmp(op, "hold") ? JOB_SUBMIT : !strcmp(op, "release") ? JOB_COMPLETE : JOB_STATE;
    int handled;int error=barrier_control(fd,op,&handled);
    if (!handled || !error) error=devctl(fd, command, &s, sizeof(s), NULL);
    *out = (rmc_state){.pending=s.pending, .unblocks=s.unblocks, .completed=s.completed, .generation=s.generation,
        .facts={{"job_exists", (int)s.job_exists}, {"job_ready", (int)s.job_ready}}, .fact_count=2};
    return error;
}
static void decode(const struct job_result *out, rmc_result *r) {
    if (out->job_id != 1 || out->reserved) { r->outcome = RMC_INVALID_REPLY; return; }
    r->facts[0] = (rmc_fact){"value", out->value};
    r->facts[1] = (rmc_fact){"job_id", (int)out->job_id}; r->fact_count = 2;
}
static void ordinary(int fd, int negative, rmc_result *r) {
    struct job_result out = {.job_id=negative ? 2 : 1};
    int info = -1; errno = 0;
    int raw = devctl(fd, JOB_WAIT_RESULT, &out, sizeof(out), &info);
    r->raw_return = raw; r->raw_errno = errno; r->api = "devctl";
    /* devctl returns an error value directly. errno is preserved as an independent observation. */
    rmc_normalize(r, raw);
    if (r->outcome == RMC_OK) {
        if (info != 0) r->outcome = RMC_INVALID_REPLY;
        else decode(&out, r);
    }
}
struct message { io_devctl_t header; struct job_result payload; };
static void prepare(rmc_prepared *p) {
    memset(p, 0, sizeof(*p));
    struct message *m = (struct message *)p->input.bytes;
    m->header.i.type = _IO_DEVCTL; m->header.i.combine_len = sizeof(m->header.i);
    m->header.i.dcmd = JOB_WAIT_RESULT; m->header.i.nbytes = sizeof(m->payload);
    m->payload.job_id = 1;
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
const rmc_adapter_v1 job_adapter_v1 = {
    .abi=RMC_ADAPTER_ABI, .struct_size=sizeof(rmc_adapter_v1), .id="job-v1", .operation_id="wait-result",
    .fixture_binary="job-v1-fixture", .convention="devctl", .result_fact_keys="value job_id", .state_fact_keys="job_exists job_ready",
    .capabilities=RMC_BASE_CAPS | RMC_CAP_ERROR_PROBE | RMC_CAP_SIGNAL | RMC_CAP_DEPARTURE | RMC_CAP_REPEAT | RMC_CAP_ORDERING | RMC_CAP_EXTERNAL_HEALTH, .validate_parameters=parameters, .control=control, .ordinary=ordinary, .prepare=prepare, .finish=finish
};
