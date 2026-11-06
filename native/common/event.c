#include "event.h"
#include <errno.h>
#include <limits.h>

cJSON *json_object(void) {
    cJSON *o = cJSON_CreateObject();
    if (!o) _exit(120);
    return o;
}
void add_string(cJSON *o, const char *key, const char *value) {
    if (!value || !cJSON_AddStringToObject(o, key, value)) _exit(120);
}
void add_number(cJSON *o, const char *key, int value) {
    if (!cJSON_AddNumberToObject(o, key, value)) _exit(120);
}
void add_decimal(cJSON *o, const char *key, int64_t value) {
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%" PRId64, value);
    add_string(o, key, buffer);
}
void add_identity(cJSON *o) {
    const char *keys[] = {"run_id", "case_id", "attempt_id", "service_instance_id"};
    const char *env[] = {"RMC_RUN_ID", "RMC_CASE_ID", "RMC_ATTEMPT_ID", "RMC_INSTANCE_ID"};
    for (unsigned i = 0; i < 4; ++i) add_string(o, keys[i], getenv(env[i]));
    const char *cycle = getenv("RMC_CYCLE");
    if (!cycle) _exit(120);
    add_number(o, "cycle", atoi(cycle));
}
static int (*custom_writer)(const cJSON *);
void rmc_set_writer(int (*writer)(const cJSON *)) { custom_writer=writer; }
void json_write(const cJSON *o) {
    if (custom_writer) { (void)custom_writer(o); return; }
    char *line = cJSON_PrintUnformatted(o);
    if (!line) _exit(120);
    size_t size = strlen(line);
    /* A complete producer frame fits one atomic nonblocking pipe write. */
    if (size + 1 >= RMC_FRAME_MAX || size + 1 > PIPE_BUF) _exit(120);
    char frame[RMC_FRAME_MAX];
    memcpy(frame, line, size); frame[size++] = '\n';
    cJSON_free(line);
    if (write(STDOUT_FILENO, frame, size) != (ssize_t)size) _exit(120);
}
void event_json(const char *producer, const char *name, cJSON *data) {
    static unsigned seq;
    cJSON *o = json_object();
    add_string(o, "kind", "producer-event"); add_number(o, "schema_version", 1);
    add_identity(o); add_string(o, "producer", producer); add_decimal(o, "pid", getpid());
    add_number(o, "seq", (int)++seq); add_decimal(o, "ns", (int64_t)mono_ns());
    add_string(o, "event", name);
    if (!cJSON_AddItemToObject(o, "data", data)) _exit(120);
#ifdef RMC_EVENT_V1
    /* Explicit owned-lab fault: exercise a real failed fixture producer write.
     * Exit 120 remains independent evidence loss as well as fixture death. */
    const char *lab=getenv("RMC_LAB_CONTROL");
    if (lab && !strcmp(lab,"fixture_evidence_loss") && !strcmp(producer,"fixture") && !strcmp(name,"ready")) close(STDOUT_FILENO);
#endif
    json_write(o); cJSON_Delete(o);
}
/* Compatibility for the already proven fixture observations. Format strings are
 * project-owned, bounded key=value tokens. This does not parse external JSON. */
void event(const char *producer, const char *name, const char *format, ...) {
    char text[1024];
    va_list ap; va_start(ap, format);
    int n = vsnprintf(text, sizeof(text), format, ap); va_end(ap);
    if (n < 0 || n >= (int)sizeof(text)) _exit(120);
    cJSON *data = json_object();
    char *save;
    for (char *token = strtok_r(text, " ", &save); token; token = strtok_r(NULL, " ", &save)) {
        char *equals = strchr(token, '=');
        if (!equals) _exit(120);
        *equals++ = 0;
        int opaque = strstr(token, "_ns") || strstr(token, "pid") || !strcmp(token, "rcvid") ||
                     !strcmp(token, "logical") || !strcmp(token, "generation");
        char *end; errno = 0;
        long value = strtol(equals, &end, 10);
        if (!opaque && *equals && !*end && !errno && value >= INT32_MIN && value <= INT32_MAX)
            add_number(data, token, (int)value);
        else add_string(data, token, equals);
    }
    event_json(producer, name, data);
}
