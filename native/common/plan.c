#include "plan.h"
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <sys/utsname.h>
#include <sched.h>

int json_keys(const cJSON *o, const char *keys) {
    if (!cJSON_IsObject(o)) return 0;
    unsigned count = 0, expected = *keys ? 1 : 0;
    for (const char *p = keys; *p; ++p) if (*p == ' ') ++expected;
    for (const cJSON *item=o->child; item; item=item->next) {
        if (!item->string) return 0;
        const char *p = keys; int found = 0;
        while (*p) {
            size_t n = strcspn(p, " ");
            if (strlen(item->string) == n && !memcmp(p, item->string, n)) found = 1;
            p += n; if (*p) ++p;
        }
        if (!found) return 0;
        ++count;
    }
    return count == expected;
}
const char *json_string(const cJSON *o, const char *key) {
    const cJSON *v = cJSON_GetObjectItemCaseSensitive(o, key);
    return cJSON_IsString(v) ? v->valuestring : NULL;
}
int json_integer(const cJSON *o, const char *key, int min, int max, unsigned *out) {
    const cJSON *v = cJSON_GetObjectItemCaseSensitive(o, key);
    if (!cJSON_IsNumber(v) || v->valuedouble < min || v->valuedouble > max || floor(v->valuedouble) != v->valuedouble) return 0;
    if (out) *out = (unsigned)v->valuedouble;
    return 1;
}
int json_tree(const cJSON *o, unsigned depth) {
    if (depth > 12) return 0;
    unsigned count = 0;
    for (const cJSON *a=o->child; a; a=a->next) {
        if (++count > 2048 || !json_tree(a, depth+1)) return 0;
        if (cJSON_IsObject(o)) for (const cJSON *b=a->next; b; b=b->next)
            if (!strcmp(a->string, b->string)) return 0;
    }
    return 1;
}
static int ident(const char *s, size_t max) {
    if (!s || !*s || strlen(s) > max) return 0;
    for (; *s; ++s) if (!isalnum((unsigned char)*s) && *s != '-' && *s != '_') return 0;
    return 1;
}
static int hash(const char *s, size_t n) {
    if (!s || strlen(s) != n) return 0;
    for (; *s; ++s) if (!strchr("0123456789abcdef", *s)) return 0;
    return 1;
}
#define NEED(x) do { if (!(x)) goto bad; } while (0)
int rmc_plan_load(const char *path, rmc_plan *p) {
    memset(p, 0, sizeof(*p));
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    char *input = malloc(1048577), *compact = malloc(1048577);
    if (!input || !compact) { fclose(f); free(input); free(compact); return 0; }
    size_t size = fread(input, 1, 1048577, f); int ioerror = ferror(f); fclose(f);
    if (ioerror || size > 1048576 || memchr(input, 0, size)) { free(input); free(compact); return 0; }
    input[size] = 0;
    /* The v1 native command subset uses ASCII identifiers and no escaped strings.
     * Compare the compact input to cJSON's serialization to reject permissive
     * numeric syntax as well as trailing data. This is not a JSON parser. */
    int quoted = 0; size_t n = 0;
    for (size_t i=0; i<size; ++i) {
        unsigned char c = (unsigned char)input[i];
        if (c > 126 || c == '\\' || (c < 32 && c != '\n' && c != '\r' && c != '\t')) { free(input); free(compact); return 0; }
        if (c == '"') quoted = !quoted;
        if (quoted || !isspace(c)) compact[n++] = (char)c;
    }
    compact[n] = 0;
    const char *end = NULL;
    p->root = cJSON_ParseWithLengthOpts(input, size+1, &end, 1);
    free(input);
    char *rendered = p->root ? cJSON_PrintUnformatted(p->root) : NULL;
    int canonical = rendered && !strcmp(compact, rendered);
    cJSON_free(rendered); free(compact);
    if (!canonical) goto bad;
    NEED(json_tree(p->root, 0));
    NEED(json_keys(p->root, "kind schema_version run_id case_id attempt_id cycle service_instance_id profile profile_sha256 suite_sha256 fixture_mode builds"));
    NEED(json_string(p->root,"kind") && !strcmp(json_string(p->root,"kind"),"scenario-plan"));
    NEED(json_integer(p->root,"schema_version",1,1,NULL));
    const char *ids[] = {"run_id","case_id","attempt_id","service_instance_id"};
    for (unsigned i=0; i<4; ++i) NEED(ident(json_string(p->root,ids[i]),64));
    NEED(json_integer(p->root,"cycle",1,200,NULL));
    NEED(hash(json_string(p->root,"profile_sha256"),64) && hash(json_string(p->root,"suite_sha256"),64));
    p->mode = json_string(p->root,"fixture_mode");
    NEED(p->mode && (!strcmp(p->mode,"corrected") || !strcmp(p->mode,"ignore-unblock")));
    p->profile = cJSON_GetObjectItemCaseSensitive(p->root,"profile");
    NEED(json_keys(p->profile,"kind schema_version id version adapter service operation capabilities expectations timing suite"));
    NEED(json_string(p->profile,"kind") && !strcmp(json_string(p->profile,"kind"),"profile"));
    NEED(json_integer(p->profile,"schema_version",1,1,NULL) && json_integer(p->profile,"version",1,1000000,NULL));
    NEED(ident(json_string(p->profile,"id"),64));
    const cJSON *a = cJSON_GetObjectItemCaseSensitive(p->profile,"adapter");
    NEED(json_keys(a,"id abi") && json_integer(a,"abi",1,1,NULL));
    const char *adapter_id = json_string(a,"id"); NEED(adapter_id);
    p->adapter = rmc_adapter_find(adapter_id); NEED(p->adapter && p->adapter->abi == RMC_ADAPTER_ABI && p->adapter->struct_size == sizeof(rmc_adapter_v1));
    const cJSON *service = cJSON_GetObjectItemCaseSensitive(p->profile,"service");
    NEED(json_keys(service,"mode device"));
    const char *service_mode = json_string(service,"mode");
    NEED(service_mode && (!strcmp(service_mode,"managed-fixture") || !strcmp(service_mode,"external-attach")));
    p->external = !strcmp(service_mode,"external-attach");
    p->path = json_string(service,"device");
    NEED(p->path && !strncmp(p->path,"/dev/resmgrcheck-",17) && ident(p->path+17,96));
    const cJSON *operation = cJSON_GetObjectItemCaseSensitive(p->profile,"operation");
    NEED(json_keys(operation,"id parameters result_shape convention"));
    NEED(json_string(operation,"id") && !strcmp(json_string(operation,"id"),p->adapter->operation_id));
    NEED(p->adapter->validate_parameters(cJSON_GetObjectItemCaseSensitive(operation,"parameters")));
    NEED(json_string(operation,"result_shape") && !strcmp(json_string(operation,"result_shape"),"integer-record"));
    NEED(json_string(operation,"convention") && !strcmp(json_string(operation,"convention"),p->adapter->convention));
    const cJSON *expect = cJSON_GetObjectItemCaseSensitive(p->profile,"expectations");
    NEED(json_keys(expect,"cancel_error pending_after require_unblock health state_after"));
    NEED(json_string(expect,"cancel_error") && !strcmp(json_string(expect,"cancel_error"),"ETIMEDOUT"));
    NEED(json_integer(expect,"pending_after",0,0,NULL));
    const cJSON *requires_unblock = cJSON_GetObjectItemCaseSensitive(expect,"require_unblock");
    NEED(cJSON_IsBool(requires_unblock));
    const cJSON *fact_objects[] = {cJSON_GetObjectItemCaseSensitive(expect,"health"),cJSON_GetObjectItemCaseSensitive(expect,"state_after")};
    NEED(json_keys(fact_objects[0],p->adapter->result_fact_keys) && json_keys(fact_objects[1],p->adapter->state_fact_keys));
    for (unsigned i=0; i<2; ++i) for (const cJSON *v=fact_objects[i]->child; v; v=v->next)
        NEED(cJSON_IsNumber(v) && v->valuedouble >= INT32_MIN && v->valuedouble <= INT32_MAX && floor(v->valuedouble)==v->valuedouble);
    const cJSON *timing = cJSON_GetObjectItemCaseSensitive(p->profile,"timing");
    NEED(json_keys(timing,"setup_ms operation_ms cancellation_ms probe_ms execution_ms cleanup_ms"));
    NEED(json_integer(timing,"setup_ms",100,5000,&p->setup_ms));
    NEED(json_integer(timing,"operation_ms",100,5000,&p->operation_ms));
    NEED(json_integer(timing,"cancellation_ms",100,5000,&p->cancellation_ms));
    NEED(json_integer(timing,"probe_ms",100,5000,&p->probe_ms));
    NEED(json_integer(timing,"execution_ms",100,30000,&p->execution_ms));
    NEED(json_integer(timing,"cleanup_ms",100,5000,&p->cleanup_ms));
    NEED(p->execution_ms >= p->operation_ms + p->cancellation_ms + p->setup_ms + p->probe_ms);
    const cJSON *caps = cJSON_GetObjectItemCaseSensitive(p->profile,"capabilities");
    NEED(json_keys(caps,"required optional"));
    unsigned masks[2] = {0};
    const char *lists[] = {"required", "optional"};
    for (unsigned i=0; i<2; ++i) {
        const cJSON *list = cJSON_GetObjectItemCaseSensitive(caps,lists[i]);
        NEED(cJSON_IsArray(list) && cJSON_GetArraySize(list)<=16);
        for (const cJSON *c=list->child; c; c=c->next) {
            NEED(cJSON_IsString(c)); unsigned mask = rmc_cap_value(c->valuestring);
            NEED(mask && !(masks[i] & mask)); masks[i] |= mask;
        }
    }
    NEED(!(masks[0] & masks[1])); p->required_caps=masks[0];
    NEED(!cJSON_IsTrue(requires_unblock) || (masks[0] & RMC_CAP_UNBLOCK));
    NEED((masks[0] & (RMC_CAP_PENDING|RMC_CAP_STATE|RMC_CAP_HEALTH|RMC_CAP_TIMEOUT)) == (RMC_CAP_PENDING|RMC_CAP_STATE|RMC_CAP_HEALTH|RMC_CAP_TIMEOUT));
    const cJSON *suite = cJSON_GetObjectItemCaseSensitive(p->profile,"suite");
    NEED(json_keys(suite,"required optional cycles reset") && json_integer(suite,"cycles",1,1,NULL));
    NEED(json_string(suite,"reset") && !strcmp(json_string(suite,"reset"),"new-instance"));
    const cJSON *required = cJSON_GetObjectItemCaseSensitive(suite,"required");
    NEED(cJSON_IsArray(required) && cJSON_GetArraySize(required)==1 && cJSON_IsString(required->child) && !strcmp(required->child->valuestring,"timeout"));
    const cJSON *optional = cJSON_GetObjectItemCaseSensitive(suite,"optional");
    NEED(cJSON_IsArray(optional) && cJSON_GetArraySize(optional)<=3);
    unsigned optional_mask = 0;
    for (const cJSON *c=optional->child; c; c=c->next) {
        NEED(cJSON_IsString(c));
        unsigned mask = !strcmp(c->valuestring,"signal") ? 1 : !strcmp(c->valuestring,"departure") ? 2 : !strcmp(c->valuestring,"repeat") ? 4 : 0;
        NEED(mask && !(optional_mask & mask)); optional_mask |= mask;
    }
    const cJSON *b = cJSON_GetObjectItemCaseSensitive(p->root,"builds");
    NEED(json_keys(b,"source_revision dirty source_tree_sha256 compiler_variant recipe_id binaries"));
    NEED(hash(json_string(b,"source_tree_sha256"),64));
    NEED(hash(json_string(b,"source_revision"),40) && hash(json_string(b,"recipe_id"),64));
    NEED(cJSON_IsBool(cJSON_GetObjectItemCaseSensitive(b,"dirty")));
    NEED(json_string(b,"compiler_variant") && !strcmp(json_string(b,"compiler_variant"),"gcc_ntox86_64"));
    const cJSON *binaries = cJSON_GetObjectItemCaseSensitive(b,"binaries");
    NEED(json_keys(binaries,"runner worker fixture adapter"));
    for (const cJSON *v=binaries->child; v; v=v->next) NEED(cJSON_IsString(v) && hash(v->valuestring,64));
    return 1;
 bad:
    cJSON_Delete(p->root); memset(p,0,sizeof(*p)); return 0;
}
void rmc_plan_environment(const rmc_plan *p) {
    const char *keys[] = {"run_id","case_id","attempt_id","service_instance_id"};
    const char *names[] = {"RMC_RUN_ID","RMC_CASE_ID","RMC_ATTEMPT_ID","RMC_INSTANCE_ID"};
    for (unsigned i=0; i<4; ++i) if (setenv(names[i],json_string(p->root,keys[i]),1)) _exit(120);
    char cycle[16]; snprintf(cycle,sizeof(cycle),"%d",cJSON_GetObjectItemCaseSensitive(p->root,"cycle")->valueint);
    if (setenv("RMC_CYCLE",cycle,1)) _exit(120);
}
void rmc_manifest(const rmc_plan *p) {
    cJSON *m=json_object(), *target=json_object(), *caps=cJSON_CreateArray();
    if (!caps) _exit(120);
    add_string(m,"kind","target-run-manifest"); add_number(m,"schema_version",1); add_identity(m);
    add_string(m,"tool_version","0.3.0"); add_string(m,"adapter_id",p->adapter->id); add_number(m,"adapter_abi",p->adapter->abi);
    for (unsigned i=0; rmc_cap_name(i); ++i) if (p->adapter->capabilities & (1U<<i))
        if (!cJSON_AddItemToArray(caps,cJSON_CreateString(rmc_cap_name(i)))) _exit(120);
    if (!cJSON_AddItemToObject(m,"capabilities",caps)) _exit(120);
    add_string(m,"profile_sha256",json_string(p->root,"profile_sha256"));
    add_string(m,"suite_sha256",json_string(p->root,"suite_sha256"));
    if (!cJSON_AddItemToObject(m,"builds",cJSON_Duplicate(cJSON_GetObjectItemCaseSensitive(p->root,"builds"),1))) _exit(120);
    struct utsname u; if (uname(&u)) _exit(120);
    add_string(target,"sysname",u.sysname); add_string(target,"release",u.release);
    add_string(target,"version",u.version); add_string(target,"machine",u.machine);
    struct sched_param s; if (sched_getparam(0,&s)) _exit(120);
    add_number(target,"scheduling_policy",sched_getscheduler(0)); add_number(target,"priority",s.sched_priority);
    if (!cJSON_AddItemToObject(m,"target",target)) _exit(120);
    cJSON *errors=json_object();
    add_number(errors,"EOK",0); add_number(errors,"ETIMEDOUT",ETIMEDOUT);
    add_number(errors,"EINTR",EINTR); add_number(errors,"ENOENT",ENOENT);
    if (!cJSON_AddItemToObject(m,"error_codes",errors)) _exit(120);
    add_string(m,"fixture_mode",p->mode); json_write(m); cJSON_Delete(m);
}
