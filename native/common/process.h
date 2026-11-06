#ifndef RMC_PROCESS_H
#define RMC_PROCESS_H
#include "event.h"
#include <sys/types.h>
typedef struct {
    pid_t pid;
    int owned,reaped,status,reported,expected_stop;
    unsigned termination_mask;
    const char *producer,*operation;
    int fd,bad,eof;
    size_t used;
    unsigned last_seq;
    int64_t last_ns;
    uint64_t spawned_ns;
    char partial[RMC_FRAME_MAX];
} rmc_child;
/* 1 reaped, 0 still owned/running, -1 ownership cannot be established. */
int rmc_child_poll(rmc_child *child);
/* No signal to zero/negative, reaped or ownership-unknown PID. */
int rmc_child_signal(rmc_child *child,int signal_number,int *error);
#endif
