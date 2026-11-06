#ifndef RMC_LAB_H
#define RMC_LAB_H
#include "event.h"
/* Explicit lab-only CLI controls. Never profile expectations or shell commands. */
int rmc_lab_set(const char *name);
const char *rmc_lab_name(void);
int rmc_lab_is(const char *name);
void rmc_lab_worker(const char *role);
#endif
