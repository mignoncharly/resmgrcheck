#ifndef RMC_EVENT_H
#define RMC_EVENT_H
#include "clock.h"
#include "cJSON.h"
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RMC_FRAME_MAX 16384
void event(const char *producer, const char *name, const char *format, ...);
void event_json(const char *producer, const char *name, cJSON *data);
void json_write(const cJSON *value);
void add_string(cJSON *obj, const char *key, const char *value);
void add_number(cJSON *obj, const char *key, int value);
void add_decimal(cJSON *obj, const char *key, int64_t value);
cJSON *json_object(void);
void add_identity(cJSON *object);
#endif
