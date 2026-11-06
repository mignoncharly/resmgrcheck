#ifndef RESMGRCHECK_PHASE2_H
#define RESMGRCHECK_PHASE2_H
#define _QNX_SOURCE 1
#include <devctl.h>
#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define SAMPLE "sample=42\n"
struct sensor_state { unsigned pending, unblocks, completed, generation; };
#define SENSOR_HOLD __DIOF(_DCMD_MISC, 0x81, struct sensor_state)
#define SENSOR_RELEASE __DIOF(_DCMD_MISC, 0x82, struct sensor_state)
#define SENSOR_STATE __DIOF(_DCMD_MISC, 0x83, struct sensor_state)

#include "../common/clock.h"

#ifdef RMC_EVENT_V1
#include "../common/event.h"
#else
/* One bounded write per producer event. Supervisor sets producer pipes nonblocking.
 * A missing event is an evidence error, never an implicit success. */
static inline void event(const char *producer, const char *name, const char *fmt, ...) {
    static unsigned seq;
    char line[512];
    int n = snprintf(line, sizeof(line), "producer=%s pid=%ld seq=%u ns=%" PRIu64 " event=%s ",
                     producer, (long)getpid(), ++seq, mono_ns(), name);
    va_list ap;
    va_start(ap, fmt);
    int m = vsnprintf(line + n, sizeof(line) - (size_t)n, fmt, ap);
    va_end(ap);
    if (m < 0 || n + m + 1 >= (int)sizeof(line)) _exit(120);
    n += m;
    line[n++] = '\n';
    if (write(STDOUT_FILENO, line, (size_t)n) != n) _exit(120);
}
#endif /* RMC_EVENT_V1 */
#endif
