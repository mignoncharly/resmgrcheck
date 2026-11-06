"""One deterministic evaluator, independent of service names and fixture defects."""
import hashlib
from .contracts import (Plan, ProducerEvent, TargetManifest, EvaluatedResult, Invalid,
                        IDENTITY, MAX_FRAME, MAX_EVENTS, loads, require)

class Evidence:
    def __init__(self, raw, plan):
        lines=raw.splitlines(keepends=True)
        require(1 <= len(lines) <= MAX_EVENTS and all(x.endswith(b'\n') and len(x) <= MAX_FRAME for x in lines), 'truncated/oversize event stream')
        records=[loads(line, MAX_FRAME) for line in lines]
        self.manifest=TargetManifest.parse(records[0]).data
        self.events=[ProducerEvent.parse(d).data for d in records[1:]]
        self.index={id(d):i+1 for i,d in enumerate(self.events)}
        for d in records:
            require(all(d[k] == plan.data[k] for k in IDENTITY.split()), 'cross-run identity mismatch')
        m=self.manifest
        for k in ('profile_sha256','suite_sha256','builds','fixture_mode'):
            require(m[k] == plan.data[k], 'manifest/plan mismatch')
        require(m['adapter_id'] == plan.profile.data['adapter']['id'] and m['adapter_abi'] == plan.profile.data['adapter']['abi'], 'wrong adapter')
        seen={}; supervisors=set()
        for d in self.events:
            key=(d['producer'],d['pid'])
            seq,ns=seen.get(key,(0,-1))
            require(d['seq'] == seq+1 and int(d['ns']) >= ns, 'producer sequence/time invalid')
            seen[key]=(d['seq'],int(d['ns']))
            if d['producer'] == 'supervisor': supervisors.add(d['pid'])
        require(len(supervisors)==1 and self.events and self.events[-1]['event']=='run_final' and self.events[-1]['producer']=='supervisor', 'missing final marker')
        require(len(self.select('run_final'))==1, 'multiple final markers')
        self.spawned={}
        self.child_producers={}
        for d in self.select('spawned'):
            child=d['data']['child_pid']
            require(child not in self.spawned, 'ambiguous child identity')
            require(d['data']['binary'] in {'worker', plan.profile.registration.fixture}, 'unregistered child executable')
            self.spawned[child]=d['data']['operation']
            self.child_producers[child]='worker' if d['data']['binary']=='worker' else 'fixture'
        for d in self.events:
            if d['producer'] in ('worker','fixture'):
                require(d['pid'] in self.spawned and d['producer']==self.child_producers[d['pid']], 'unowned/wrong-role producer')
                if d['event']=='started': require(d['data']['operation']==self.spawned[d['pid']], 'worker role mismatch')
            else: require(d['pid'] in supervisors, 'invalid supervisor source')
        require(not self.select('evidence_error') and not self.events[-1]['data']['evidence_error'], 'producer evidence error')
        if not self.select('unsupported'):
            require(sum(p=='fixture' for p in self.child_producers.values())==1, 'service instance changed')
            ready=self.select('ready')
            expected_path=plan.profile.data['service']['device']+'-'+plan.data['service_instance_id']
            require(len(ready)==1 and ready[0]['data']=={'path':expected_path,'mode':plan.data['fixture_mode']}, 'wrong service instance')
            settings=self.select('settings')
            expected_settings={'mode':plan.data['fixture_mode'],'timeout_ms':plan.profile.timing.operation_ms,
                               'allowance_ms':plan.profile.timing.cancellation_ms,'path':expected_path,
                               'case_ms':plan.profile.timing.execution_ms,'cleanup_ms':plan.profile.timing.cleanup_ms}
            require(len(settings)==1 and settings[0]['data']==expected_settings, 'wrong run settings')

    def select(self, name, *, producer=None, operation=None, pid=None):
        return [d for d in self.events if d['event']==name and
                (producer is None or d['producer']==producer) and
                (operation is None or d['data'].get('operation')==operation) and
                (pid is None or d['pid']==pid)]

    def refs(self, records): return [self.index[id(d)] for d in records]


def evaluate(plan, raw):
    if not isinstance(plan, Plan): plan=Plan.parse(plan)
    if type(raw) is str: raw=raw.encode()
    require(type(raw) is bytes, 'evidence must be bytes')
    result={'kind':'evaluated-result','schema_version':1, **{k:plan.data[k] for k in IDENTITY.split()},
            'fixture_mode':plan.data['fixture_mode'],'verdict':'ERROR','reasons':[], 'completion':'incomplete',
            'assertions':[], 'profile_sha256':plan.data['profile_sha256'], 'event_sha256':hashlib.sha256(raw).hexdigest()}
    def assertion(name, verdict, records=()):
        result['assertions'].append({'id':name,'verdict':verdict,'event_refs':ev.refs(records) if records else []})
    try:
        ev=Evidence(raw,plan)
    except (Invalid,KeyError,TypeError,ValueError,OverflowError):
        result['reasons']=['evidence_invalid_or_incomplete']
        result['assertions']=[{'id':'evidence_completeness','verdict':'ERROR','event_refs':[]}]
        return EvaluatedResult.parse(result)
    required=set(plan.profile.data['capabilities']['required'])
    unsupported=required-set(ev.manifest['capabilities']) or plan.profile.data['service']['mode'] != 'managed-fixture'
    cleanup=ev.select('cleanup')
    final=ev.events[-1]
    if unsupported:
        # A real preflight skip must be explicit and must not launch processes.
        if len(ev.select('unsupported'))!=1 or ev.spawned or len(cleanup)!=1 or not cleanup[0]['data']['all_reaped'] or cleanup[0]['data']['evidence_error'] or not final['data']['cleanup_ok'] or not final['data']['flow_complete']:
            assertion('capability_preflight','ERROR')
        else:
            assertion('required_capability_missing' if required-set(ev.manifest['capabilities']) else 'service_mode_unsupported','UNSUPPORTED',ev.select('unsupported'))
            assertion('evidence_completeness','PASS',[final])
            result['completion']='complete'
    else:
        expect=plan.profile.data['expectations']; timing=plan.profile.timing
        # Baseline must establish valid service behavior before cancellation conclusions.
        baseline=ev.select('result',operation='normal')+ev.select('result',operation='message')
        baseline_ok=len(ev.select('result',operation='normal'))==2 and len(ev.select('result',operation='message'))==1 and all(
            d['data']['normalized']=='OK' and d['data']['facts']==expect['health'] for d in baseline)
        ordinary_api={'errno':'read','devctl':'devctl'}[plan.profile.data['operation']['convention']]
        baseline_ok=baseline_ok and all(d['data']['api']==ordinary_api for d in ev.select('result',operation='normal')) and all(
            d['data']['api']=='MsgSendv' for d in ev.select('result',operation='message'))
        stage=ev.select('stage')
        baseline_ok=baseline_ok and any(d['data']['name']=='deferred_release_complete' for d in stage)
        assertion('baseline_validity','PASS' if baseline_ok else 'ERROR',baseline)
        deadlines=ev.select('deadline',operation='timed'); pending=[]; unblocks=[]; completion=[]; states=[]
        established=False; bound=None; timed_pid=None
        if len(deadlines)==1:
            t=deadlines[0]; timed_pid=t['pid']; deadline=int(t['data']['deadline_ns']); bound=deadline+timing.cancellation_ms*1000000
            pending=[d for d in ev.select('pending',producer='fixture') if d['data']['client_pid']==timed_pid]
            if len(pending)==1:
                p=pending[0]
                unblocks=[d for d in ev.select('unblock',producer='fixture') if all(d['data'][k]==p['data'][k] for k in ('logical','generation','rcvid'))]
                established=(int(t['ns'])<=int(p['ns'])<deadline and t['data']['timeout_ms']==timing.operation_ms and
                             0 < deadline-int(t['ns']) <= timing.operation_ms*1000000)
                if expect['require_unblock']:
                    established=established and len(unblocks)==1 and unblocks[0]['data']['live']==1 and int(unblocks[0]['ns'])>=deadline
        assertion('pending_precondition','PASS' if established else 'ERROR',deadlines+pending+unblocks)
        completion=ev.select('result',operation='timed',pid=timed_pid) if timed_pid else []
        states=ev.select('control_result',operation='state')
        if not baseline_ok or not established:
            assertion('cancellation_completion','NOT_RUN')
        elif not completion:
            bounds=ev.select('operation_bound')
            reached=len(bounds)==1 and bounds[0]['data']['expired']==1 and int(bounds[0]['ns'])>=bound and int(bounds[0]['data']['completion_bound_ns'])==bound
            assertion('cancellation_not_completed','FAIL' if reached else 'ERROR',bounds)
        else:
            good=len(completion)==1 and completion[0]['data']['api']=='MsgSendv' and completion[0]['data']['raw_return']==-1 and completion[0]['data']['normalized']=='TIMEOUT' and completion[0]['data']['error_name']==expect['cancel_error'] and completion[0]['data']['api_error']==ev.manifest['error_codes'][expect['cancel_error']] and deadline<=int(completion[0]['ns'])<=bound
            assertion('cancellation_completion','PASS' if good else 'FAIL',completion)
            terminal=[d for d in ev.select('cancel_completed') if all(d['data'][k]==pending[0]['data'][k] for k in ('logical','generation'))]
            removed=[d for d in ev.select('removed') if all(d['data'][k]==pending[0]['data'][k] for k in ('logical','generation')) and d['data']['reason']=='cancellation']
            terminal_good=len(terminal)==len(removed)==1 and terminal[0]['data']['rc']>=0 and terminal[0]['data']['error']==0 and removed[0]['data']['pending']==0
            assertion('terminal_reply_observation','PASS' if terminal_good else 'ERROR',terminal+removed)
        if baseline_ok and established:
            state_good=len(states)==1 and states[0]['data']['error']==0 and states[0]['data']['generation']==pending[0]['data']['generation']
            assertion('state_observation','PASS' if state_good else 'ERROR',states)
            if state_good:
                assertion('pending_state_cleanup','PASS' if states[0]['data']['pending']==expect['pending_after'] else 'FAIL',states)
                assertion('state_facts','PASS' if states[0]['data']['facts']==expect['state_after'] else 'FAIL',states)
        health=ev.select('result',operation='health')
        if not completion and ev.select('health_withheld'):
            assertion('fresh_client_health','NOT_RUN',ev.select('health_withheld'))
        else:
            stops=ev.select('fixture_stop')
            healthy=len(health)==1 and health[0]['pid']!=timed_pid and health[0]['data']['normalized']=='OK' and health[0]['data']['facts']==expect['health'] and len(stops)==1 and int(health[0]['ns'])<int(stops[0]['ns']) and len(states)==1 and int(health[0]['ns'])>=int(states[0]['ns'])
            assertion('fresh_client_health','PASS' if healthy else 'FAIL' if health else 'ERROR',health)
        reaped=ev.select('reaped')
        all_reaped={d['data']['child_pid'] for d in reaped}
        cleanup_ok=len(cleanup)==1 and cleanup[0]['data']['all_reaped']==1 and cleanup[0]['data']['evidence_error']==0 and final['data']['cleanup_ok']==1 and all_reaped==set(ev.spawned) and len(reaped)==len(ev.spawned)
        assertion('owned_process_cleanup','PASS' if cleanup_ok else 'ERROR',cleanup+ev.select('reaped'))
        finals={d['pid']:d for d in ev.select('worker_final')}
        natural={d['pid'] for d in ev.select('result')+ev.select('control_result')}
        statuses={d['data']['child_pid']:d['data']['raw_status'] for d in reaped}
        closed={d['pid']:d for d in ev.select('closed')}
        complete=final['data']['flow_complete']==1 and cleanup_ok and all(pid in finals and finals[pid]['data']['exit_code']==0 and statuses.get(pid)==0 and pid in closed and closed[pid]['data']['rc']==0 for pid in natural)
        assertion('evidence_completeness','PASS' if complete else 'ERROR',[final])
        result['completion']='complete' if complete else 'incomplete'
    verdicts={a['verdict'] for a in result['assertions']}
    if 'ERROR' in verdicts: result['verdict']='ERROR'
    elif 'UNSUPPORTED' in verdicts: result['verdict']='UNSUPPORTED'
    elif 'FAIL' in verdicts: result['verdict']='FAIL'
    elif verdicts=={'PASS'}: result['verdict']='PASS'
    else: result['verdict']='ERROR'
    result['reasons']=[a['id'] for a in result['assertions'] if a['verdict'] in {'FAIL','ERROR','UNSUPPORTED'}] or ['all_obligations_satisfied']
    return EvaluatedResult.parse(result)


def evaluate_persistent(plan, raw, status):
    """Bind a reconnect snapshot; a PID/status file is never cleanup authority."""
    from .contracts import RunStatus, digest
    if not isinstance(plan,Plan): plan=Plan.parse(plan)
    result=evaluate(plan,raw).data
    try:
        if not isinstance(status,RunStatus): status=RunStatus.parse(status)
        d=status.data
        require(all(d[k]==plan.data[k] for k in IDENTITY.split()),'status identity mismatch')
        require(d['profile_sha256']==plan.data['profile_sha256'] and d['source_tree_sha256']==plan.data['builds']['source_tree_sha256'],'status build/profile mismatch')
        evidence=Evidence(raw,plan)
        supervisor={e['pid'] for e in evidence.events if e['producer']=='supervisor'}
        require(supervisor=={d['supervisor_pid']},'status owner mismatch')
        finalized=(d['state']=='complete' and d['cleanup_ok'] and not d['unresolved'] and d['exit_code'] in (0,3))
        result['status_sha256']=digest(d)
    except (Invalid,KeyError,TypeError,ValueError):
        finalized=False
    result['assertions'].append({'id':'target_completion_status','verdict':'PASS' if finalized else 'ERROR','event_refs':[]})
    if not finalized:
        result['verdict']='ERROR'; result['completion']='incomplete'
        result['reasons']=[r for r in result['reasons'] if r!='all_obligations_satisfied']+['target_completion_unestablished']
    return EvaluatedResult.parse(result)
