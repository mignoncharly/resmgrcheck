#ifndef RMC_ADAPTER_V1_H
#define RMC_ADAPTER_V1_H
#define _QNX_SOURCE 1
#include <sys/neutrino.h>
#include <stdint.h>
#include "common/event.h"
#define RMC_ADAPTER_ABI 1
#define RMC_CAP_PENDING (1U << 0)
#define RMC_CAP_UNBLOCK (1U << 1)
#define RMC_CAP_STATE (1U << 2)
#define RMC_CAP_RELEASE (1U << 3)
#define RMC_CAP_HEALTH (1U << 4)
#define RMC_CAP_TIMEOUT (1U << 5)
#define RMC_CAP_SIGNAL (1U << 6)
#define RMC_CAP_DEPARTURE (1U << 7)
#define RMC_CAP_ERROR_PROBE (1U << 8)
#define RMC_BASE_CAPS (RMC_CAP_PENDING | RMC_CAP_UNBLOCK | RMC_CAP_STATE | RMC_CAP_RELEASE | RMC_CAP_HEALTH | RMC_CAP_TIMEOUT)

typedef enum { RMC_OK, RMC_TIMEOUT, RMC_INTERRUPTED, RMC_API_ERROR, RMC_INVALID_REPLY } rmc_outcome;
typedef struct { const char *name; int value; } rmc_fact;
typedef struct {
    const char *api; /* read/devctl/MsgSendv; retained with the raw values */
    long raw_return;
    int raw_errno, api_error;
    rmc_outcome outcome;
    rmc_fact facts[4];
    unsigned fact_count;
} rmc_result;
typedef struct {
    unsigned pending, unblocks, completed, generation;
    rmc_fact facts[4];
    unsigned fact_count;
} rmc_state;
/* Prepared entirely before TimerTimeout. The core owns the one intended send.
 * Aligned storage is private to each adapter, never a serialized ABI object. */
typedef struct {
    iov_t send[2], receive[2];
    int send_parts, receive_parts;
    union { uint64_t align; unsigned char bytes[512]; } input, output;
} rmc_prepared;
typedef struct rmc_adapter_v1 {
    unsigned abi;
    size_t struct_size;
    const char *id, *operation_id, *fixture_binary;
    const char *convention, *result_fact_keys, *state_fact_keys;
    unsigned capabilities;
    int (*validate_parameters)(const cJSON *parameters);
    int (*control)(int fd, const char *operation, rmc_state *state);
    void (*ordinary)(int fd, int negative_probe, rmc_result *result);
    void (*prepare)(rmc_prepared *prepared);
    void (*finish)(const rmc_prepared *prepared, int raw, int error, rmc_result *result);
} rmc_adapter_v1;
const rmc_adapter_v1 *rmc_adapter_find(const char *id);
const char *rmc_cap_name(unsigned bit);
unsigned rmc_cap_value(const char *name);
void rmc_normalize(rmc_result *result, int error);
void rmc_emit_result(const char *operation, const rmc_result *result);
void rmc_emit_state(const char *operation, int error, const rmc_state *state);
#endif
