/* The generic runner's scenario state machine. All service calls stay in workers. */
static int await_matching(rmc_child *source,const char *name,unsigned after,const char *key,int64_t value,uint64_t end) {
    end=bounded(end);
    do {
        pump(end);
        for (unsigned i=after;i<count;++i) if (field(events[i],"pid")==source->pid && named(events[i],name) && field(events[i],key)==value) return (int)i;
    } while (!run_error && source->owned && !source->reaped && mono_ns()<end);
    return -1;
}
static int facts_equal(const cJSON *observed,const cJSON *expected) {
    if (!cJSON_IsObject(observed) || !cJSON_IsObject(expected) || cJSON_GetArraySize(observed)!=cJSON_GetArraySize(expected)) return 0;
    for (const cJSON *v=expected->child;v;v=v->next) {
        const cJSON *got=cJSON_GetObjectItemCaseSensitive(observed,v->string);
        if (!cJSON_IsNumber(got) || got->valuedouble!=v->valuedouble) return 0;
    }
    return 1;
}
static int observation_ok(int index,int result,const char *predicate) {
    if (index<0) return 0;
    const cJSON *data=cJSON_GetObjectItemCaseSensitive(events[index],"data");
    const cJSON *expect=cJSON_GetObjectItemCaseSensitive(plan.profile,"expectations");
    if (result) return json_string(data,"normalized") && !strcmp(json_string(data,"normalized"),"OK") && facts_equal(cJSON_GetObjectItemCaseSensitive(data,"facts"),cJSON_GetObjectItemCaseSensitive(expect,predicate));
    return field(events[index],"error")==0 && field(events[index],"pending")==0 && facts_equal(cJSON_GetObjectItemCaseSensitive(data,"facts"),cJSON_GetObjectItemCaseSensitive(expect,predicate));
}
static int baseline(rmc_child *fixture) {
    if (!worker("ready",NULL) || !worker("normal",NULL) || !worker("message",NULL) || !worker("dup",NULL)) return 0;
    if ((plan.adapter->capabilities&RMC_CAP_ERROR_PROBE) && !worker("negative",NULL)) return 0;
    if (!worker("hold",NULL)) return 0;
    unsigned after=count;rmc_child *client=spawn_child(0,"normal");
    if (!client || await_matching(fixture,"pending",after,"client_pid",client->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0 || !worker("release",NULL)) return 0;
    await_child(client,mono_ns()+(uint64_t)plan.probe_ms*1000000ULL);
    if (!client->reaped || find_event(client->pid,"result",after)<0) { problem("evidence_incomplete",client,0);return 0; }
    event("supervisor","stage","name=deferred_release_complete");return !run_error;
}
static int wait_result(rmc_child *client,unsigned after,uint64_t end) {
    int result;
    do { pump(end);result=find_event(client->pid,"result",after);if (result>=0 && client->reaped) break; }
    while (!run_error && client->owned && mono_ns()<bounded(end));
    return result;
}
static int all_workers_reaped(unsigned first) {
    for (unsigned i=first;i<child_count;++i) if (!strcmp(children[i].producer,"worker") && !children[i].reaped) return 0;
    return 1;
}
static int repeat_scenario(rmc_child *fixture,rmc_child **last) {
    uint64_t run_end=mono_ns()+(uint64_t)plan.cycles*plan.execution_ms*1000000ULL;
    int stop=0;
    for (unsigned cycle=1;cycle<=plan.cycles;++cycle) {
        current_cycle=cycle;char value[16];snprintf(value,sizeof(value),"%u",cycle);if (setenv("RMC_CYCLE",value,1)) _exit(120);
        if (stop) { event("supervisor","cycle_not_run","cycle=%u reason=%s",cycle,run_error ? "prior_cycle_incomplete" : "prior_cycle_contaminated");continue; }
        execution_end=mono_ns()+(uint64_t)plan.execution_ms*1000000ULL;if (execution_end>run_end) execution_end=run_end;
        event("supervisor","cycle_begin","cycle=%u fixture_pid=%ld deadline_ns=%" PRIu64,cycle,(long)fixture->pid,execution_end);
        unsigned first=child_count;int state=-1,health=-1;rmc_child *client=NULL;int completed=0;
        if (!worker("cycle",NULL) || !worker("hold",NULL)) goto cycle_done;
        unsigned after=count;client=spawn_child(0,"timed");*last=client;if (!client) goto cycle_done;
        int timer=await_event(client,"deadline",after,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL);
        if (timer<0) { if (!run_error) problem("evidence_incomplete",client,0);goto cycle_done; }
        uint64_t end=(uint64_t)field(events[timer],"deadline_ns")+(uint64_t)plan.cancellation_ms*1000000ULL;
        int result=wait_result(client,after,end);
        event("supervisor","operation_bound","completion_bound_ns=%" PRIu64 " expired=%d result_observed=%d worker_reaped=%d",end,mono_ns()>=end,result>=0,client->reaped);
        if (!worker("state",&state)) goto cycle_done;
        if (result>=0 && client->reaped) {
            if (!worker("release",NULL) || !worker("health",&health)) goto cycle_done;
        } else event("supervisor","health_withheld","reason=operation_incomplete");
        completed=1;
cycle_done:
        ;int clean=all_workers_reaped(first);
        int safe=completed && clean && observation_ok(state,0,"state_after") && observation_ok(health,1,"health") && !run_error;
        event("supervisor","cycle_end","cycle=%u worker_pid=%ld worker_reaped=%d pending=%d state_observed=%d clean=%d safe=%d",cycle,(long)(client ? client->pid : 0),client ? client->reaped : 0,state>=0 ? (int)field(events[state],"pending") : 0,state>=0 && field(events[state],"error")==0,clean,safe);
        if (!safe) stop=1;
    }
    return !run_error;
}
static int departure_scenario(rmc_child *fixture,rmc_child **last) {
    if (!worker("hold",NULL)) return 0;
    unsigned after=count;rmc_child *client=spawn_child(0,"depart");*last=client;if (!client) return 0;
    int pending=await_matching(fixture,"pending",after,"client_pid",client->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL);
    if (pending<0) return 0;
    uint64_t end=mono_ns()+(uint64_t)plan.cancellation_ms*1000000ULL;
    event("supervisor","trigger_requested","child_pid=%ld signal=%d completion_bound_ns=%" PRIu64,(long)client->pid,SIGKILL,end);
    signal_owned(client,SIGKILL);await_child(client,end);
    event("supervisor","departure_bound","child_pid=%ld completion_bound_ns=%" PRIu64 " reaped=%d",(long)client->pid,end,client->reaped);
    if (!client->reaped) { event("supervisor","health_withheld","reason=departure_unobserved");return !run_error; }
    int linked=-1;
    for (unsigned i=after;i<count;++i) if (named(events[i],"request_ocb") && field(events[i],"logical")==field(events[pending],"logical") && field(events[i],"generation")==field(events[pending],"generation")) linked=(int)i;
    if (linked<0 || await_matching(fixture,"close_ocb_default",after,"ocb",field(events[linked],"ocb"),mono_ns()+(uint64_t)plan.probe_ms*1000000ULL)<0) { problem("evidence_incomplete",client,0);return 0; }
    return worker("state",NULL) && worker("release",NULL) && worker("health",NULL);
}
static int ordering_scenario(rmc_child *fixture,rmc_child **last) {
    int complete_first=!strcmp(plan.scenario,"complete-first");
    if (!worker("hold",NULL) || (complete_first && !worker("arm_complete",NULL))) return 0;
    unsigned after=count;rmc_child *client=spawn_child(0,"ordered");*last=client;if (!client) return 0;
    if (await_matching(fixture,"pending",after,"client_pid",client->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0) return 0;
    uint64_t end=mono_ns()+(uint64_t)plan.cancellation_ms*1000000ULL;
    event("supervisor","trigger_requested","child_pid=%ld signal=%d completion_bound_ns=%" PRIu64,(long)client->pid,SIGUSR1,end);
    signal_owned(client,SIGUSR1);
    if (complete_first) {
        if (await_event(fixture,"barrier_wait",after,end)<0 || !worker("release",NULL)) return 0;
    }
    int result=wait_result(client,after,end);
    event("supervisor","operation_bound","completion_bound_ns=%" PRIu64 " expired=%d result_observed=%d worker_reaped=%d",end,mono_ns()>=end,result>=0,client->reaped);
    if (result<0 || !client->reaped) { event("supervisor","health_withheld","reason=operation_incomplete");return !run_error; }
    event("supervisor","ordering_stage","name=first_terminal child_pid=%ld",(long)client->pid);
    if (!complete_first && !worker("release",NULL)) return 0;
    if (!worker("state_before",NULL) || !worker("hold_next",NULL)) return 0;
    after=count;rmc_child *fresh=spawn_child(0,"message");*last=fresh;if (!fresh) return 0;
    if (await_matching(fixture,"pending",after,"client_pid",fresh->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0 || !worker("drain_stale",NULL) || !worker("state_before",NULL) || !worker("release",NULL)) return 0;
    if (wait_result(fresh,after,mono_ns()+(uint64_t)plan.probe_ms*1000000ULL)<0 || !fresh->reaped) { problem("evidence_incomplete",fresh,0);return 0; }
    event("supervisor","ordering_stage","name=fresh_terminal child_pid=%ld",(long)fresh->pid);
    after=count;rmc_child *park=spawn_child(0,"park");*last=park;if (!park) return 0;
    if (await_matching(fixture,"parked",after,"client_pid",park->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0) return 0;
    end=mono_ns()+(uint64_t)plan.cancellation_ms*1000000ULL;
    event("supervisor","trigger_requested","child_pid=%ld signal=%d completion_bound_ns=%" PRIu64,(long)park->pid,SIGUSR1,end);signal_owned(park,SIGUSR1);await_child(park,end);
    if (!park->reaped || find_event(park->pid,"control_result",after)<0) { problem("probe_timeout",park,0);return 0; }
    if (complete_first) {
        if (!worker("hold_next",NULL)) return 0;
        after=count;rmc_child *finished=spawn_child(0,"finish_first");*last=finished;if (!finished) return 0;
        if (await_matching(fixture,"pending",after,"client_pid",finished->pid,mono_ns()+(uint64_t)plan.setup_ms*1000000ULL)<0 || !worker("release",NULL)) return 0;
        if (await_event(finished,"result",after,mono_ns()+(uint64_t)plan.probe_ms*1000000ULL)<0) return 0;
        event("supervisor","ordering_stage","name=completion_before_trigger child_pid=%ld",(long)finished->pid);
        end=mono_ns()+(uint64_t)plan.cancellation_ms*1000000ULL;
        event("supervisor","trigger_requested","child_pid=%ld signal=%d completion_bound_ns=%" PRIu64,(long)finished->pid,SIGUSR1,end);
        signal_owned(finished,SIGUSR1);await_child(finished,end);
        if (!finished->reaped) { problem("worker_timeout",finished,0);return 0; }
    }
    return worker("state",NULL) && worker("health_next",NULL);
}
static int extended_scenario(rmc_child *fixture,rmc_child **last) {
    observe_service_errors=1;
    if (!baseline(fixture)) {
        if (!strcmp(plan.scenario,"repeat")) for (unsigned cycle=1;cycle<=plan.cycles;++cycle) event("supervisor","cycle_not_run","cycle=%u reason=baseline_unestablished",cycle);
        return 0;
    }
    if (!strcmp(plan.scenario,"repeat")) return repeat_scenario(fixture,last);
    if (!strcmp(plan.scenario,"departure")) return departure_scenario(fixture,last);
    return ordering_scenario(fixture,last);
}
