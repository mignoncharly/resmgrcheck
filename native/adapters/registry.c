#include "../adapter_v1.h"
extern const rmc_adapter_v1 sensor_adapter_v1, job_adapter_v1;
static const rmc_adapter_v1 *const adapters[] = {&sensor_adapter_v1, &job_adapter_v1};
static const char *const caps[] = {"pending", "unblock", "state", "release", "health", "timeout", "signal", "departure", "error-probe"};
const rmc_adapter_v1 *rmc_adapter_find(const char *id) {
    for (unsigned i = 0; i < sizeof(adapters)/sizeof(adapters[0]); ++i)
        if (!strcmp(id, adapters[i]->id)) return adapters[i];
    return NULL;
}
const char *rmc_cap_name(unsigned bit) { return bit < sizeof(caps)/sizeof(caps[0]) ? caps[bit] : NULL; }
unsigned rmc_cap_value(const char *name) {
    for (unsigned i = 0; i < sizeof(caps)/sizeof(caps[0]); ++i) if (!strcmp(name, caps[i])) return 1U << i;
    return 0;
}
