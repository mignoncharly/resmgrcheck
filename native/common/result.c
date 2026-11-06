#include "../adapter_v1.h"
#include <errno.h>
void rmc_normalize(rmc_result *r, int error) {
    r->api_error = error;
    r->outcome = !error ? RMC_OK : error == ETIMEDOUT ? RMC_TIMEOUT : error == EINTR ? RMC_INTERRUPTED : RMC_API_ERROR;
}
void rmc_emit_result(const char *operation, const rmc_result *r) {
    static const char *const outcomes[] = {"OK", "TIMEOUT", "INTERRUPTED", "API_ERROR", "INVALID_REPLY"};
    cJSON *d = json_object(), *facts = json_object();
    add_string(d, "operation", operation); add_string(d, "api", r->api);
    add_number(d, "raw_return", (int)r->raw_return); add_number(d, "raw_errno", r->raw_errno);
    add_number(d, "api_error", r->api_error); add_string(d, "normalized", outcomes[r->outcome]);
    const char *error_name = !r->api_error ? "EOK" : r->api_error == ETIMEDOUT ? "ETIMEDOUT" :
                             r->api_error == EINTR ? "EINTR" : r->api_error == ENOENT ? "ENOENT" : "API_ERROR";
    add_string(d, "error_name", error_name); add_string(d, "result_shape", "integer-record");
    if (r->outcome == RMC_OK) {
        for (unsigned i = 0; i < r->fact_count && i < 4; ++i) add_number(facts, r->facts[i].name, r->facts[i].value);
    }
    if (!cJSON_AddItemToObject(d, "facts", facts)) _exit(120);
    event_json("worker", "result", d);
}
void rmc_emit_state(const char *operation, int error, const rmc_state *s) {
    cJSON *d = json_object(), *facts = json_object();
    add_string(d, "operation", operation); add_number(d, "error", error);
    add_number(d, "pending", (int)s->pending); add_number(d, "unblocks", (int)s->unblocks);
    add_number(d, "completed", (int)s->completed); add_decimal(d, "generation", s->generation);
    for (unsigned i = 0; i < s->fact_count && i < 4; ++i) add_number(facts, s->facts[i].name, s->facts[i].value);
    if (!cJSON_AddItemToObject(d, "facts", facts)) _exit(120);
    event_json("worker", "control_result", d);
}
