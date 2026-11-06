#ifndef RMC_CLOCK_H
#define RMC_CLOCK_H
#define _QNX_SOURCE 1
#include <stdint.h>
#include <time.h>
#include <unistd.h>
static inline uint64_t mono_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(120);
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}
#endif
