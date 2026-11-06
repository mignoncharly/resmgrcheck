#include "../adapter_v1.h"
#include "../spikes/phase2.h"
#include <sys/iomsg.h>
#include <limits.h>
static int parameters(const cJSON *o) { return cJSON_IsObject(o) && !o->child; }
static int control(int fd, const char *op, rmc_state *out) {
    struct sensor_state s = {0};
    int command = !strcmp(op, "hold") ? SENSOR_HOLD : !strcmp(op, "release") ? SENSOR_RELEASE : SENSOR_STATE;
    int error = devctl(fd, command, &s, sizeof(s), NULL);
    *out = (rmc_state){.pending=s.pending, .unblocks=s.unblocks, .completed=s.completed, .generation=s.generation};
    return error;
}
static void decode(const char *buffer, int bytes, rmc_result *r) {
    if (bytes < 9 || bytes >= 64 || strncmp(buffer, "sample=", 7)) { r->outcome = RMC_INVALID_REPLY; return; }
    char copy[64]; memcpy(copy, buffer, (size_t)bytes); copy[bytes] = 0;
    char *end; errno = 0; long n = strtol(copy+7, &end, 10);
    if (errno || end != copy+bytes-1 || *end != '\n' || n < INT_MIN || n > INT_MAX) { r->outcome = RMC_INVALID_REPLY; return; }
    r->facts[0] = (rmc_fact){"value", (int)n}; r->fact_count = 1;
}
static void ordinary(int fd, int negative, rmc_result *r) {
    (void)negative;
    char buffer[64]; errno = 0;
    r->raw_return = read(fd, buffer, sizeof(buffer)); r->raw_errno = errno; r->api = "read";
    rmc_normalize(r, r->raw_return == -1 ? r->raw_errno : 0);
    if (r->outcome == RMC_OK) decode(buffer, (int)r->raw_return, r);
}
static void prepare(rmc_prepared *p) {
    memset(p, 0, sizeof(*p));
    io_read_t *m = (io_read_t *)p->input.bytes;
    m->i.type = _IO_READ; m->i.combine_len = sizeof(m->i); m->i.nbytes = 64; m->i.xtype = _IO_XTYPE_NONE;
    SETIOV(&p->send[0], &m->i, sizeof(m->i)); SETIOV(&p->receive[0], p->output.bytes, 64);
    p->send_parts = p->receive_parts = 1;
}
static void finish(const rmc_prepared *p, int raw, int error, rmc_result *r) {
    r->api = "MsgSendv"; r->raw_return = raw; r->raw_errno = error;
    rmc_normalize(r, raw == -1 ? error : 0);
    if (r->outcome == RMC_OK) decode((const char *)p->output.bytes, raw, r);
}
const rmc_adapter_v1 sensor_adapter_v1 = {
    .abi=RMC_ADAPTER_ABI, .struct_size=sizeof(rmc_adapter_v1), .id="sensor-v1", .operation_id="sample",
    .fixture_binary="sensor-v1-fixture", .convention="errno", .result_fact_keys="value", .state_fact_keys="",
    .capabilities=RMC_BASE_CAPS | RMC_CAP_SIGNAL, .validate_parameters=parameters, .control=control, .ordinary=ordinary, .prepare=prepare, .finish=finish
};
