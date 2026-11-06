#include "protocol.h"
#include <ctype.h>
#include <math.h>
#include <errno.h>
struct field_spec { const char *name,*producer,*keys,*types; };
#include "producer_fields.h"
static int identifier(const char *s) {
    if (!s || !*s || strlen(s)>64 || !isalnum((unsigned char)*s)) return 0;
    for (;*s;++s) if (!isalnum((unsigned char)*s) && *s!='_' && *s!='-') return 0;
    return 1;
}
static int decimal(const char *s) {
    if (!s || !*s || strlen(s)>19 || (s[0]=='0' && s[1])) return 0;
    for (const char *p=s;*p;++p) if (!isdigit((unsigned char)*p)) return 0;
    errno=0;strtoll(s,NULL,10);return !errno;
}
static int facts(const cJSON *o) {
    if (!cJSON_IsObject(o)) return 0;
    unsigned count=0;
    for (const cJSON *v=o->child;v;v=v->next)
        if (++count>16 || !identifier(v->string) || !cJSON_IsNumber(v) ||
            v->valuedouble<INT32_MIN || v->valuedouble>INT32_MAX || floor(v->valuedouble)!=v->valuedouble) return 0;
    return 1;
}
int rmc_producer_payload(const cJSON *o,const rmc_adapter_v1 *adapter) {
    const char *name=json_string(o,"event"),*producer=json_string(o,"producer");
    const cJSON *data=cJSON_GetObjectItemCaseSensitive(o,"data");
    if (!name || !producer) return 0;
    const struct field_spec *spec=NULL;
    for (unsigned i=0;i<sizeof(producer_fields)/sizeof(producer_fields[0]);++i)
        if (!strcmp(name,producer_fields[i].name) && !strcmp(producer,producer_fields[i].producer)) spec=&producer_fields[i];
    if (!spec || !json_keys(data,spec->keys)) return 0;
    const char *key=spec->keys;
    for (unsigned i=0;*key;++i) {
        size_t n=strcspn(key," ");char field[64];
        if (n>=sizeof(field)) return 0;
        memcpy(field,key,n);field[n]=0;key+=n;if (*key) ++key;
        const cJSON *v=cJSON_GetObjectItemCaseSensitive(data,field);
        char type=spec->types[i];
        if (type=='s' && (!cJSON_IsString(v) || !identifier(v->valuestring))) return 0;
        if (type=='d' && (!cJSON_IsString(v) || !decimal(v->valuestring))) return 0;
        if (type=='p') {
            if (!cJSON_IsString(v) || strncmp(v->valuestring,"/dev/resmgrcheck-",17) || strlen(v->valuestring)>198) return 0;
            for (const char *p=v->valuestring+17;*p;++p) if (!isalnum((unsigned char)*p) && *p!='-' && *p!='_') return 0;
        }
        if ((type=='i' || type=='n' || type=='b') && (!cJSON_IsNumber(v) || floor(v->valuedouble)!=v->valuedouble ||
            v->valuedouble<(type=='i' ? INT32_MIN : 0) || v->valuedouble>(type=='b' ? 1 : type=='n' ? 1000000 : INT32_MAX))) return 0;
        if (type=='f' && !facts(v)) return 0;
    }
    if (!strcmp(name,"result")) {
        const char *status=json_string(data,"normalized");
        if (!status) return 0;
        const cJSON *f=cJSON_GetObjectItemCaseSensitive(data,"facts");
        if (!strcmp(status,"OK")) return json_keys(f,adapter->result_fact_keys);
        return !strcmp(status,"TIMEOUT") || !strcmp(status,"INTERRUPTED") || !strcmp(status,"API_ERROR") || !strcmp(status,"INVALID_REPLY");
    }
    if (!strcmp(name,"control_result") && !cJSON_GetObjectItemCaseSensitive(data,"error")->valueint)
        return json_keys(cJSON_GetObjectItemCaseSensitive(data,"facts"),adapter->state_fact_keys);
    return 1;
}
