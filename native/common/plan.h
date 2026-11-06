#ifndef RMC_PLAN_H
#define RMC_PLAN_H
#include "../adapter_v1.h"
typedef struct {
    cJSON *root;
    const cJSON *profile;
    const rmc_adapter_v1 *adapter;
    const char *mode, *path, *scenario;
    unsigned setup_ms, operation_ms, cancellation_ms, probe_ms, execution_ms, cleanup_ms;
    unsigned required_caps;
    int external, signal_unsupported;
} rmc_plan;
int json_tree(const cJSON *value, unsigned depth);
int json_keys(const cJSON *object, const char *keys);
const char *json_string(const cJSON *object, const char *key);
int json_integer(const cJSON *object, const char *key, int min, int max, unsigned *out);
int rmc_plan_load(const char *path, rmc_plan *plan);
void rmc_plan_environment(const rmc_plan *plan);
void rmc_manifest(const rmc_plan *plan);
#endif
