#ifndef RMC_PERSISTENCE_H
#define RMC_PERSISTENCE_H
#include "plan.h"
/* Returns 0 in the detached supervisor, 1 in a successful launch parent,
 * -1 on launch uncertainty/error. Persistence is opt-in, foreground is unchanged. */
int rmc_detach_run(const rmc_plan *plan);
int rmc_status_write(const rmc_plan *plan, const char *state, int cleanup_ok,
                     int exit_code, cJSON *unresolved);
int rmc_is_persistent(void);
#endif
