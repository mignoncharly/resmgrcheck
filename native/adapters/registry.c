#include "../adapter_v1.h"
#define RMC_ADAPTER(symbol) extern const rmc_adapter_v1 symbol;
#include "catalog_v1.h"
#undef RMC_ADAPTER
static const rmc_adapter_v1 *const adapters[] = {
#define RMC_ADAPTER(symbol) &symbol,
#include "catalog_v1.h"
#undef RMC_ADAPTER
};
static const char *const caps[] = {"pending", "unblock", "state", "release", "health", "timeout", "signal", "departure", "error-probe", "repeat", "ordering", "external-health"};
static int catalog_valid(void) {
    for (unsigned i=0;i<sizeof(adapters)/sizeof(adapters[0]);++i) {
        const rmc_adapter_v1 *a=adapters[i];
        if (!a || a->abi!=RMC_ADAPTER_ABI || a->struct_size!=sizeof(*a) ||
            !a->id || !a->operation_id || !a->fixture_binary || !a->convention ||
            !a->result_fact_keys || !a->state_fact_keys || !a->validate_parameters ||
            !a->control || !a->ordinary || !a->prepare || !a->finish ||
            !a->id[0] || strnlen(a->id,65)>64 || !a->operation_id[0] || strnlen(a->operation_id,65)>64 ||
            !a->fixture_binary[0] || strnlen(a->fixture_binary,65)>64 ||
            (strcmp(a->convention,"errno") && strcmp(a->convention,"devctl")) ||
            a->capabilities&~((1U<<(sizeof(caps)/sizeof(caps[0])))-1U)) return 0;
        for (const char *p=a->fixture_binary;*p;++p)
            if (!((*p>='a' && *p<='z') || (*p>='0' && *p<='9') || *p=='-')) return 0;
        for (unsigned j=0;j<i;++j) if (!strcmp(a->id,adapters[j]->id)) return 0;
    }
    return 1;
}
const rmc_adapter_v1 *rmc_adapter_at(unsigned index) {
    return catalog_valid() && index<sizeof(adapters)/sizeof(adapters[0]) ? adapters[index] : NULL;
}
int rmc_fixture_mode(const rmc_adapter_v1 *adapter,const char *mode) {
    if (!strcmp(mode,"corrected") || !strcmp(mode,"ignore-unblock") || !strcmp(mode,"retain-waiter") || !strcmp(mode,"retain-third") || !strcmp(mode,"duplicate-terminal")) return 1;
    return adapter==&job_adapter_v1 && !strcmp(mode,"drop-job");
}
const rmc_adapter_v1 *rmc_adapter_find(const char *id) {
    if (!catalog_valid() || !id) return NULL;
    for (unsigned i = 0; i < sizeof(adapters)/sizeof(adapters[0]); ++i)
        if (!strcmp(id, adapters[i]->id)) return adapters[i];
    return NULL;
}
const char *rmc_cap_name(unsigned bit) { return bit < sizeof(caps)/sizeof(caps[0]) ? caps[bit] : NULL; }
unsigned rmc_cap_value(const char *name) {
    for (unsigned i = 0; i < sizeof(caps)/sizeof(caps[0]); ++i) if (!strcmp(name, caps[i])) return 1U << i;
    return 0;
}
