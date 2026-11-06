#ifndef RMC_JOB_PROTOCOL_H
#define RMC_JOB_PROTOCOL_H
#include <stdint.h>
#include <devctl.h>
struct job_result { uint64_t job_id; int32_t value; uint32_t reserved; };
struct job_state {
    uint32_t pending, unblocks, completed, generation;
    uint32_t job_exists, job_ready;
};
#define JOB_SUBMIT __DIOF(_DCMD_MISC, 0x91, struct job_state)
#define JOB_COMPLETE __DIOF(_DCMD_MISC, 0x92, struct job_state)
#define JOB_STATE __DIOF(_DCMD_MISC, 0x93, struct job_state)
#define JOB_WAIT_RESULT __DIOTF(_DCMD_MISC, 0x94, struct job_result)
#endif
