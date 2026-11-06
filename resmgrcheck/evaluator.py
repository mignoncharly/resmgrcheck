"""Deterministic evaluation of trustworthy observations, including incomplete runs."""
import hashlib
from .contracts import (Plan,ProducerEvent,TargetManifest,EvaluatedResult,Invalid,IDENTITY,
                        MAX_FRAME,MAX_EVENTS,loads,require,RunStatus,digest)
from .reasons import NATIVE_ERRORS,ASSERTION_REASONS

class Evidence:
    def __init__(self,raw,plan):
        self.events=[];self.index={};self.read_error=None
        lines=raw.splitlines(keepends=True)
        require(lines and lines[0].endswith(b'\n') and len(lines[0])<=MAX_FRAME,'manifest missing')
        self.manifest=TargetManifest.parse(loads(lines[0],MAX_FRAME)).data
        m=self.manifest
        require(all(m[k]==plan.data[k] for k in IDENTITY.split()),'manifest identity')
        for k in ('profile_sha256','suite_sha256','builds','fixture_mode'):require(m[k]==plan.data[k],'manifest binding')
        require(m['adapter_id']==plan.profile.data['adapter']['id'] and m['adapter_abi']==plan.profile.data['adapter']['abi'],'adapter binding')
        seen={};supervisors=set()
        for i,line in enumerate(lines[1:],1):
            if i>=MAX_EVENTS:self.read_error='evidence_capacity_exceeded';break
            if not line.endswith(b'\n'):self.read_error='evidence_incomplete';break
            try:
                require(len(line)<=MAX_FRAME,'oversize')
                d=ProducerEvent.parse(loads(line,MAX_FRAME)).data
                require(all(d[k]==plan.data[k] for k in IDENTITY.split()),'cross-run event')
                key=(d['producer'],d['pid']);seq,ns=seen.get(key,(0,-1))
                require(d['seq']==seq+1 and int(d['ns'])>=ns,'sequence/time')
                seen[key]=(d['seq'],int(d['ns']))
                if d['producer']=='supervisor':supervisors.add(d['pid'])
                require(len(supervisors)<=1,'multiple supervisors')
                self.index[id(d)]=i;self.events.append(d)
            except (Invalid,KeyError,TypeError,ValueError,OverflowError):
                self.read_error='evidence_invalid';break
        self.supervisors=supervisors
        self.spawned={};self.child_producers={}
        controls=self.select('lab_control')
        self.lab_control=controls[0]['data']['name'] if len(controls)==1 else 'none'
        for d in self.select('spawned'):
            child=d['data']['child_pid'];binary=d['data']['binary']
            if child in self.spawned:self.read_error='evidence_invalid';continue
            if binary=='worker':producer='worker'
            elif binary==plan.profile.registration.fixture:producer='fixture'
            elif binary=='lab-manager' and self.lab_control in {'manager_interference','manager_pending'}:producer='manager'
            else:self.read_error='evidence_invalid';continue
            self.spawned[child]=d['data']['operation'];self.child_producers[child]=producer
        for d in self.events:
            if d['producer']!='supervisor':
                if d['pid'] not in self.spawned or d['producer']!=self.child_producers[d['pid']]:self.read_error='evidence_invalid'
                if d['event']=='started' and d['data']['operation']!=self.spawned.get(d['pid']):self.read_error='evidence_invalid'
        exits=self.select('process_exit');exit_ids=[d['data']['child_pid'] for d in exits]
        if len(set(exit_ids))!=len(exit_ids) or any(pid not in self.spawned for pid in exit_ids):self.read_error='evidence_invalid'
        final=self.select('run_final')
        self.final=final[-1] if len(final)==1 and self.events and self.events[-1] is final[0] else None
        if self.final is None and not self.read_error:self.read_error='evidence_incomplete'
        self.problems=self.select('problem')
        if any(p['data']['reason'] not in NATIVE_ERRORS for p in self.problems):self.read_error='evidence_invalid'
        if not self.select('unsupported') and not self.select('case_not_run'):
            ready=self.select('ready')
            expected=plan.profile.data['service']['device']+'-'+plan.data['service_instance_id']
            if len(ready)>1 or (ready and ready[0]['data']!={'path':expected,'mode':plan.data['fixture_mode']}):self.read_error='service_interference'
            if sum(p=='fixture' for p in self.child_producers.values())>1:self.read_error='service_interference'
            settings=self.select('settings')
            expected_settings={'mode':plan.data['fixture_mode'],'timeout_ms':plan.profile.timing.operation_ms,
              'allowance_ms':plan.profile.timing.cancellation_ms,'path':expected,
              'case_ms':plan.profile.timing.execution_ms,'cleanup_ms':plan.profile.timing.cleanup_ms}
            if settings and (len(settings)!=1 or settings[0]['data']!=expected_settings):self.read_error='evidence_invalid'

    def select(self,name,*,producer=None,operation=None,pid=None):
        return [d for d in self.events if d['event']==name and (producer is None or d['producer']==producer)
          and (operation is None or d['data'].get('operation')==operation) and (pid is None or d['pid']==pid)]
    def refs(self,records):return [self.index[id(d)] for d in records]


def evaluate(plan,raw):
    if not isinstance(plan,Plan):plan=Plan.parse(plan)
    if type(raw) is str:raw=raw.encode()
    require(type(raw) is bytes,'evidence bytes required')
    result={'kind':'evaluated-result','schema_version':1,**{k:plan.data[k] for k in IDENTITY.split()},
      'fixture_mode':plan.data['fixture_mode'],'verdict':'ERROR','reasons':[],'completion':'incomplete','assertions':[],
      'profile_sha256':plan.data['profile_sha256'],'event_sha256':hashlib.sha256(raw).hexdigest()}
    try:ev=Evidence(raw,plan)
    except (Invalid,KeyError,TypeError,ValueError,OverflowError):
        result['reasons']=['evidence_invalid'];result['assertions']=[{'id':'evidence_invalid','verdict':'ERROR','event_refs':[]}]
        return EvaluatedResult.parse(result)
    def assertion(name,verdict,records=()):
        result['assertions'].append({'id':name,'verdict':verdict,'event_refs':ev.refs(records) if records else []})
    for code in sorted({p['data']['reason'] for p in ev.problems}):
        assertion(code,'ERROR',[p for p in ev.problems if p['data']['reason']==code])
    if ev.read_error and ev.read_error not in {a['id'] for a in result['assertions']}:assertion(ev.read_error,'ERROR')
    # Historical writer errors have no per-source problem envelope, but remain invalid.
    if ev.select('evidence_error'):assertion('evidence_invalid','ERROR',ev.select('evidence_error'))
    final=ev.final;cleanup=ev.select('cleanup')
    structural=ev.read_error is not None
    required=set(plan.profile.data['capabilities']['required'])
    bad_signal_mode=plan.profile.data['suite'].get('signal_mode','non-restart-no-retry')!='non-restart-no-retry'
    unsupported=required-set(ev.manifest['capabilities']) or plan.profile.data['service']['mode']!='managed-fixture' or bad_signal_mode
    withheld=ev.select('case_not_run')
    if withheld:
        valid=len(withheld)==1 and not ev.spawned and not structural and final and final['data']['cleanup_ok']==1
        assertion(withheld[0]['data']['reason'] if valid else 'evidence_invalid','NOT_RUN' if valid else 'ERROR',withheld)
        result['completion']='aborted'
    elif unsupported:
        valid=len(ev.select('unsupported'))==1 and not ev.spawned and not structural and len(cleanup)==1 and cleanup[0]['data']=={'all_reaped':1,'evidence_error':0} and final and final['data']['cleanup_ok']==1
        assertion(('required_capability_missing' if required-set(ev.manifest['capabilities']) else 'signal_mode_unsupported' if bad_signal_mode else 'service_mode_unsupported') if valid else 'capability_preflight','UNSUPPORTED' if valid else 'ERROR',ev.select('unsupported'))
        if valid:assertion('evidence_completeness','PASS',[final]);result['completion']='complete'
    else:
        expected=plan.profile.data['expectations'];timing=plan.profile.timing
        baselines=ev.select('result',operation='normal')+ev.select('result',operation='message')
        ordinary={'errno':'read','devctl':'devctl'}[plan.profile.data['operation']['convention']]
        bad_baselines=[d for d in baselines if not (d['data']['normalized']=='OK' and d['data']['facts']==expected['health'] and d['data']['api']==('MsgSendv' if d['data']['operation']=='message' else ordinary))]
        good_baselines=not bad_baselines
        baseline_ok=len(ev.select('result',operation='normal'))==2 and len(ev.select('result',operation='message'))==1 and good_baselines and any(d['data']['name']=='deferred_release_complete' for d in ev.select('stage'))
        # A transport-style error during established fixture interference does
        # not establish a service reply violation. A returned bad payload does.
        interference=ev.read_error=='service_interference' or any(p['data']['reason']=='service_interference' for p in ev.problems)
        forbidden=[d for d in bad_baselines if not interference or d['data']['normalized'] in {'OK','INVALID_REPLY'}]
        if forbidden:assertion('unexpected_operation_result','FAIL',forbidden)
        assertion('baseline_validity','PASS' if baseline_ok else 'NOT_RUN' if ev.problems or structural else 'ERROR',baselines)
        signal_case=plan.data['case_id']=='signal';operation='signal' if signal_case else 'timed'
        deadlines=ev.select('operation_armed',operation='signal') if signal_case else ev.select('deadline',operation='timed')
        pending=[];unblocks=[];established=False;bound=None;deadline=None;timed_pid=None
        if len(deadlines)==1:
            t=deadlines[0];timed_pid=t['pid']
            if not signal_case:deadline=int(t['data']['deadline_ns']);bound=deadline+timing.cancellation_ms*1000000
            pending=[d for d in ev.select('pending',producer='fixture') if d['data']['client_pid']==timed_pid]
            if len(pending)==1:
                p=pending[0]
                unblocks=[d for d in ev.select('unblock',producer='fixture') if all(d['data'][k]==p['data'][k] for k in ('logical','generation','rcvid'))]
                if signal_case:
                    triggers=ev.select('trigger_requested');setup=ev.select('signal_setup',pid=timed_pid)
                    sends=ev.select('signal_sent');sends=[s for s in sends if s['data']['child_pid']==timed_pid and setup and s['data']['signal']==setup[0]['data']['signal']]
                    established=(len(triggers)==len(setup)==len(sends)==1 and triggers[0]['data']['child_pid']==timed_pid and
                      triggers[0]['data']['signal']==setup[0]['data']['signal']==ev.manifest.get('signal_codes',{}).get('SIGUSR1') and setup[0]['data']['name']=='SIGUSR1' and setup[0]['data']['flags']==setup[0]['data']['retry']==setup[0]['data']['timeout_armed']==setup[0]['data']['masked']==setup[0]['data']['error']==0 and
                      t['data']['timeout_armed']==0 and sends[0]['data']['rc']==sends[0]['data']['error']==0 and not ev.select('deadline') and
                      int(setup[0]['ns'])<=int(t['ns'])<=int(p['ns'])<=int(triggers[0]['ns'])<=int(sends[0]['ns']))
                    if triggers:
                        deadline=int(triggers[0]['ns']);bound=int(triggers[0]['data']['completion_bound_ns'])
                        established=established and 0<bound-deadline<=timing.cancellation_ms*1000000
                    established=established and all(int(p['data'][k])>0 for k in ('logical','generation','rcvid')) and p['data']['pending']==1
                else:
                    established=(int(t['ns'])<=int(p['ns'])<deadline and all(int(p['data'][k])>0 for k in ('logical','generation','rcvid')) and p['data']['pending']==1 and
                      t['data']['timeout_ms']==timing.operation_ms and 0<deadline-int(t['ns'])<=timing.operation_ms*1000000)
                if expected['require_unblock']:established=established and len(unblocks)==1 and unblocks[0]['data']['live']==1 and deadline is not None and int(unblocks[0]['ns'])>=deadline
        assertion('pending_precondition','PASS' if established else 'NOT_RUN' if not baseline_ok else 'ERROR',deadlines+pending+unblocks)
        completion=ev.select('result',operation=operation,pid=timed_pid) if timed_pid else []
        if not baseline_ok or not established:assertion('cancellation_completion','NOT_RUN')
        elif not completion:
            bounds=ev.select('operation_bound')
            reached=len(bounds)==1 and bounds[0]['data']['expired']==1 and bounds[0]['data']['worker_reaped']==0 and int(bounds[0]['ns'])>=bound and int(bounds[0]['data']['completion_bound_ns'])==bound
            assertion('cancellation_not_completed' if reached else 'evidence_incomplete','FAIL' if reached else 'ERROR',bounds)
        else:
            good=len(completion)==1 and completion[0]['data']['api']=='MsgSendv' and completion[0]['data']['raw_return']==-1 and completion[0]['data']['normalized']==('INTERRUPTED' if signal_case else 'TIMEOUT') and completion[0]['data']['error_name']==expected['cancel_error'] and completion[0]['data']['api_error']==ev.manifest['error_codes'][expected['cancel_error']] and deadline<=int(completion[0]['ns'])<=bound
            assertion('cancellation_completion','PASS' if good else 'FAIL',completion)
            if signal_case:
                handlers=ev.select('signal_handler_observed',pid=timed_pid)
                handler_ok=len(handlers)==1 and handlers[0]['data']['seen']==1 and handlers[0]['data']['signal']==setup[0]['data']['signal'] and deadline<=int(handlers[0]['ns'])<=int(completion[0]['ns'])
                assertion('signal_handler_observation','PASS' if handler_ok else 'ERROR',handlers)
            terminal=[d for d in ev.select('cancel_completed') if all(d['data'][k]==pending[0]['data'][k] for k in ('logical','generation'))]
            removed=[d for d in ev.select('removed') if all(d['data'][k]==pending[0]['data'][k] for k in ('logical','generation')) and d['data']['reason']=='cancellation']
            good_terminal=len(terminal)==len(removed)==1 and terminal[0]['data']['rc']>=0 and terminal[0]['data']['error']==0 and removed[0]['data']['pending']==0
            assertion('terminal_reply_observation','PASS' if good_terminal else 'ERROR',terminal+removed)
        states=ev.select('control_result',operation='state')
        if baseline_ok and established:
            state_good=len(states)==1 and states[0]['data']['error']==0 and states[0]['data']['generation']==pending[0]['data']['generation']
            assertion('state_observation','PASS' if state_good else 'NOT_RUN' if ev.problems else 'ERROR',states)
            if state_good:
                assertion('pending_state_cleanup','PASS' if states[0]['data']['pending']==expected['pending_after'] else 'FAIL',states)
                assertion('state_facts','PASS' if states[0]['data']['facts']==expected['state_after'] else 'FAIL',states)
        health=ev.select('result',operation='health');stops=ev.select('fixture_stop')
        if not health and (ev.select('health_withheld') or ev.problems or not baseline_ok or not established):assertion('fresh_client_health','NOT_RUN',ev.select('health_withheld'))
        else:
            healthy=len(health)==1 and health[0]['pid']!=timed_pid and health[0]['data']['normalized']=='OK' and health[0]['data']['facts']==expected['health'] and len(stops)==1 and int(health[0]['ns'])<int(stops[0]['ns']) and len(states)==1 and int(health[0]['ns'])>=int(states[0]['ns'])
            assertion('fresh_client_health','PASS' if healthy else 'FAIL' if health else 'ERROR',health)
        reaped=ev.select('reaped');ids={d['data']['child_pid'] for d in reaped}
        cleanup_ok=len(cleanup)==1 and cleanup[0]['data']['all_reaped']==1 and final and final['data']['cleanup_ok']==1 and ids==set(ev.spawned) and len(reaped)==len(ev.spawned)
        assertion('owned_process_cleanup' if cleanup_ok or cleanup else 'cleanup_unestablished','PASS' if cleanup_ok else 'ERROR',cleanup+reaped)
        finals={d['pid']:d for d in ev.select('worker_final')};statuses={d['data']['child_pid']:d['data']['raw_status'] for d in reaped}
        natural={d['pid'] for d in ev.select('result')+ev.select('control_result')};closed={d['pid']:d for d in ev.select('closed')}
        failed_closes=[d for d in ev.select('closed') if d['data']['rc']==-1]
        if failed_closes and not any(a['id']=='worker_close_failed' for a in result['assertions']):assertion('worker_close_failed','ERROR',failed_closes)
        exits={d['data']['child_pid']:d['data'] for d in ev.select('process_exit')}
        close_pids={d['pid'] for d in failed_closes}
        failed_exits=[d for d in ev.select('process_exit') if d['data']['child_pid'] in natural-close_pids and d['data']['exited']==1 and d['data']['exit_code']!=0]
        if failed_exits and not any(a['id']=='worker_exit_failed' for a in result['assertions']):assertion('worker_exit_failed','ERROR',failed_exits)
        natural_good=all(pid in finals and pid in closed and pid in statuses and (
          (pid in exits and exits[pid]['exited']==1 and exits[pid]['exit_code']==finals[pid]['data']['exit_code']) or
          (pid not in exits and finals[pid]['data']['exit_code']==0 and statuses[pid]==0)) for pid in natural)
        evidence_complete=not structural and final and final['data']['evidence_error']==0 and natural_good
        assertion('evidence_completeness','PASS' if evidence_complete else 'ERROR',[final] if final else [])
        if final and final['data']['flow_complete']!=1:
            assertion('scenario_execution','NOT_RUN' if ev.problems or structural else 'ERROR',[final])
        result['completion']='complete' if evidence_complete and cleanup_ok and final['data']['flow_complete']==1 else 'incomplete'
    verdicts={a['verdict'] for a in result['assertions']}
    result['verdict']='ERROR' if 'ERROR' in verdicts else 'UNSUPPORTED' if 'UNSUPPORTED' in verdicts else 'FAIL' if 'FAIL' in verdicts else 'NOT_RUN' if 'NOT_RUN' in verdicts else 'PASS'
    codes=[]
    for a in result['assertions']:
        if a['verdict'] in {'ERROR','FAIL','UNSUPPORTED'} or (result['verdict']=='NOT_RUN' and a['verdict']=='NOT_RUN'):
            code='evidence_incomplete' if a['verdict']=='ERROR' and a['id'] in {'fresh_client_health','scenario_execution'} else ASSERTION_REASONS.get(a['id'],a['id'])
            if code not in codes:codes.append(code)
    result['reasons']=codes or ['all_obligations_satisfied']
    return EvaluatedResult.parse(result)


def evaluate_persistent(plan,raw,status):
    if not isinstance(plan,Plan):plan=Plan.parse(plan)
    result=evaluate(plan,raw).data
    try:
        if not isinstance(status,RunStatus):status=RunStatus.parse(status)
        d=status.data
        require(all(d[k]==plan.data[k] for k in IDENTITY.split()),'status identity')
        require(d['profile_sha256']==plan.data['profile_sha256'] and d['source_tree_sha256']==plan.data['builds']['source_tree_sha256'],'status binding')
        ev=Evidence(raw,plan);require(ev.supervisors=={d['supervisor_pid']},'status owner')
        require(d.get('lab_control','none')==ev.lab_control,'status lab control mismatch')
        final=ev.final;require(final is not None and not ev.read_error,'writer not finalized')
        known={p['data']['child_pid'] for p in ev.select('reaped')}
        unresolved=set(ev.spawned)-known
        require({p['pid'] for p in d['unresolved']}==unresolved,'status ownership ledger mismatch')
        require(d['cleanup_ok']==bool(final['data']['cleanup_ok']),'status cleanup mismatch')
        finalized=(d['state']=='complete' and d['cleanup_ok'] and not unresolved and d['exit_code'] in (0,3)) or (
          d['state']=='not-run' and result['verdict']=='NOT_RUN' and d['exit_code']==4 and not ev.spawned) or (
          d['state']=='incomplete' and d['exit_code']==2 and result['verdict']=='ERROR')
        result['status_sha256']=digest(d)
    except (Invalid,KeyError,TypeError,ValueError):finalized=False
    result['assertions'].append({'id':'target_completion_status','verdict':'PASS' if finalized else 'ERROR','event_refs':[]})
    if not finalized:
        result['verdict']='ERROR';result['completion']='incomplete'
        result['reasons']=[r for r in result['reasons'] if r!='all_obligations_satisfied']+['target_completion_unestablished']
    return EvaluatedResult.parse(result)
