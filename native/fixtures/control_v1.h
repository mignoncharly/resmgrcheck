#ifndef RMC_FIXTURE_CONTROL_V1_H
#define RMC_FIXTURE_CONTROL_V1_H
#include <devctl.h>
#include <stdint.h>
/* Lab-only typed barriers. No executable strings or supplied receive IDs. */
enum { RMC_SET_CYCLE=1, RMC_ARM_COMPLETE, RMC_DRAIN_STALE, RMC_HOLD_NEXT, RMC_PARK };
struct rmc_fixture_command { uint32_t action, cycle; };
#define RMC_FIXTURE_COMMAND __DIOTF(_DCMD_MISC,0xa1,struct rmc_fixture_command)
#endif
