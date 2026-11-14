"""Shared lifecycle assertions over original, source-stamped native observations."""
from .contracts import EvaluatedResult,CycleResult,Invalid
from .reasons import ASSERTION_REASONS

REASONS={**ASSERTION_REASONS,'client_departure':'departure_unobserved','ocb_lifetime':'ocb_lifetime_unestablished',
 'single_instance':'service_interference','ordering_result':'unexpected_operation_result',
 'terminal_ownership':'duplicate_terminal_attempt','stale_notification':'stale_notification_unsafe',
 'fresh_result':'stale_result','unmatched_notification':'unmatched_notification_unsafe',
 'completion_before_trigger':'ordering_unestablished','repeat_coverage':'repetition_incomplete',
 'worker_cleanup':'cycle_cleanup_unestablished','cycle_boundary':'evidence_incomplete'}
REASONS['completion_control']='unexpected_operation_result'
REASONS['control_contract']='unexpected_operation_result'
REASONS['counter_continuity']='counter_reset'
REASONS['ordering_coverage']='ordering_incomplete'
REASONS['directed_order']='ordering_unestablished'

def finish(data,completion):
    assertions=data['assertions'];verdicts={a['verdict'] for a in assertions}
    if 'cycles' in data:verdicts.update(c['verdict'] for c in data['cycles'])
    data['verdict']=next(v for v in ('ERROR','UNSUPPORTED','FAIL','NOT_RUN','PASS') if v in verdicts)
    reasons=[]
    for a in assertions:
        if a['verdict'] in {'ERROR','FAIL','UNSUPPORTED'} or a['id'] in {'repeat_coverage','ordering_coverage'} and a['verdict']=='NOT_RUN' or data['verdict']=='NOT_RUN' and a['verdict']=='NOT_RUN':
            code=REASONS.get(a['id'],a['id'])
            if code not in reasons:reasons.append(code)
    for c in data.get('cycles',[]):
        if c['verdict'] in {'ERROR','FAIL'}:
            for code in c['reasons']:
                if code not in reasons:reasons.append(code)
    data['reasons']=reasons or ['all_obligations_satisfied'];data['completion']=completion
    return data

class Rules:
    def __init__(self,plan,ev,data):
        self.plan=plan;self.ev=ev;self.data=data;self.expected=plan.profile.data['expectations'];self.timing=plan.profile.timing
    def add(self,name,verdict,records=(),target=None):
        (self.data if target is None else target)['assertions'].append({'id':name,'verdict':verdict,'event_refs':self.ev.refs([r for r in records if r is not None])})
    def one(self,name,**kw):
        rows=self.ev.select(name,**kw);return rows[0] if len(rows)==1 else None
    def condition(self,name,good,records=(),target=None,missing=False):
        self.add(name,'PASS' if good else 'ERROR' if missing else 'FAIL',records,target)
    def result_good(self,row,predicate):
        return row and row['data']['normalized']=='OK' and row['data']['facts']==self.expected[predicate]
    def linked(self,name,pending):
        return [] if not pending else [r for r in self.ev.select(name,producer='fixture') if all(r['data'].get(k)==pending['data'][k] for k in ('logical','generation'))]
    def pending(self,pid):
        rows=[r for r in self.ev.select('pending',producer='fixture') if r['data']['client_pid']==pid]
        return rows[0] if len(rows)==1 else None
    def native_exit(self,pid):return next(iter([r for r in self.ev.select('process_exit') if r['data']['child_pid']==pid]),None)
    def baseline(self):
        stage=self.one('stage');end=int(stage['ns']) if stage else 0
        rows=[r for r in self.ev.select('result') if int(r['ns'])<end and r['data']['operation'] in {'normal','message','dup'}]
        ordinary={'errno':'read','devctl':'devctl'}[self.plan.profile.data['operation']['convention']]
        good=len(rows)==4 and sum(r['data']['operation']=='normal' for r in rows)==2 and sum(r['data']['operation']=='message' for r in rows)==1 and sum(r['data']['operation']=='dup' for r in rows)==1 and all(self.result_good(r,'health') and r['data']['api']==('MsgSendv' if r['data']['operation']=='message' else ordinary) for r in rows)
        self.add('baseline_validity','PASS' if good else 'NOT_RUN' if self.ev.problems else 'ERROR',rows+[stage]);return good
    def state(self,row,pending,target=None):
        observed=row is not None and row['data']['error']==0 and pending is not None and row['data']['generation']==pending['data']['generation']
        self.add('state_observation','PASS' if observed else 'FAIL' if row and row['data']['error'] else 'ERROR',[row],target)
        if observed:
            self.condition('pending_state_cleanup',row['data']['pending']==0,[row],target)
            self.condition('state_facts',row['data']['facts']==self.expected['state_after'],[row],target)
        else:
            self.add('pending_state_cleanup','NOT_RUN',target=target);self.add('state_facts','NOT_RUN',target=target)
        return observed
    def health(self,row,pending,predicate='health',target=None):
        stops=self.ev.select('fixture_stop')
        good=self.result_good(row,predicate) and pending and row['pid']!=pending['data']['client_pid'] and len(stops)==1 and int(row['ns'])<int(stops[0]['ns'])
        self.add('fresh_client_health','PASS' if good else 'FAIL' if row else 'NOT_RUN',[row],target)
    def signal(self,pid,pending,armed='operation_armed'):
        setup=self.one('signal_setup',pid=pid);arm=self.one(armed,pid=pid)
        triggers=[r for r in self.ev.select('trigger_requested') if r['data']['child_pid']==pid]
        trigger=triggers[0] if len(triggers)==1 else None
        sends=[r for r in self.ev.select('signal_sent') if r['data']['child_pid']==pid and setup and r['data']['signal']==setup['data']['signal']]
        good=(pending and setup and arm and trigger and len(sends)==1 and setup['data']=={'name':'SIGUSR1','signal':self.ev.manifest.get('signal_codes',{}).get('SIGUSR1'),'flags':0,'retry':0,'timeout_armed':0,'masked':0,'error':0} and
              trigger['data']['signal']==setup['data']['signal'] and sends[0]['data']['rc']==sends[0]['data']['error']==0 and
              int(arm['ns'])<=int(pending['ns'])<=int(trigger['ns'])<=int(sends[0]['ns']) and not self.ev.select('deadline',pid=pid))
        return bool(good),trigger
    def terminal_once(self,pending,target=None):
        rows=self.linked('terminal_attempt',pending)
        if len(rows)>1:self.add('duplicate_terminal_attempt','FAIL',rows,target)
        good=bool(rows) and rows[0]['data']['rc']==0 and rows[0]['data']['error']==0
        self.condition('terminal_reply_observation',good,rows,target,missing=not rows)
    def common(self):
        fixture=[p for p,role in self.ev.child_producers.items() if role=='fixture'];ready=self.ev.select('ready')
        self.add('single_instance','PASS' if len(fixture)==len(ready)==1 else 'ERROR',ready)
        groups={}
        for row in self.ev.select('terminal_attempt'):groups.setdefault((row['data']['logical'],row['data']['generation']),[]).append(row)
        duplicates=[r for rows in groups.values() if len(rows)>1 for r in rows]
        if duplicates and not any(a['id'] in {'terminal_ownership','duplicate_terminal_attempt'} for a in self.data['assertions']):self.add('duplicate_terminal_attempt','FAIL',duplicates)
        control_errors=[r for r in self.ev.select('control_result') if r['data']['error'] and r['data']['operation']!='park']
        if control_errors and not any(p['data']['reason']=='service_interference' for p in self.ev.problems):self.add('control_contract','FAIL',control_errors)
        reaped=self.ev.select('reaped');cleanup=self.ev.select('cleanup');final=self.ev.final
        clean=len(cleanup)==1 and cleanup[0]['data']['all_reaped']==1 and final and final['data']['cleanup_ok']==1 and len(reaped)==len(self.ev.spawned) and {r['data']['child_pid'] for r in reaped}==set(self.ev.spawned)
        self.add('owned_process_cleanup','PASS' if clean else 'ERROR',cleanup+reaped)
        natural={r['pid'] for r in self.ev.select('result')+self.ev.select('control_result')}
        finals={r['pid']:r for r in self.ev.select('worker_final')};closed={r['pid']:r for r in self.ev.select('closed')}
        complete=not self.ev.read_error and final and final['data']['evidence_error']==0
        for pid in natural:
            end=self.native_exit(pid);worker=finals.get(pid);close=closed.get(pid)
            complete=complete and end and worker and close and end['data']['exited']==1 and end['data']['exit_code']==worker['data']['exit_code']
            if close and close['data']['rc']!=0 and not any(a['id']=='worker_close_failed' for a in self.data['assertions']):self.add('worker_close_failed','ERROR',[close])
            api_error=any(r['data']['error']>0 for r in self.ev.select('control_result',pid=pid))
            if end and end['data']['exited'] and end['data']['exit_code'] and not api_error and close and close['data']['rc']==0 and not any(a['id']=='worker_exit_failed' for a in self.data['assertions']):self.add('worker_exit_failed','ERROR',[end])
        self.add('evidence_completeness','PASS' if complete else 'ERROR',[final])
        if final and final['data']['flow_complete']!=1 and not self.ev.problems:self.add('scenario_execution','ERROR',[final])
        return bool(complete and clean and final and final['data']['flow_complete']==1)
    def departure(self,baseline):
        armed=self.one('operation_armed',operation='depart');pid=armed['pid'] if armed else None;p=self.pending(pid) if pid else None
        triggers=[r for r in self.ev.select('trigger_requested') if r['data']['child_pid']==pid];trigger=triggers[0] if len(triggers)==1 else None
        number=self.ev.manifest.get('signal_codes',{}).get('SIGKILL')
        sends=[r for r in self.ev.select('signal_sent') if r['data']['child_pid']==pid and r['data']['signal']==number and trigger and int(trigger['ns'])<=int(r['ns'])<=int(trigger['data']['completion_bound_ns'])]
        pre=baseline and p and armed and trigger and len(sends)==1 and trigger['data']['signal']==number and sends[0]['data']['rc']==sends[0]['data']['error']==0 and int(armed['ns'])<=int(p['ns'])<=int(trigger['ns']) and p['data']['pending']==1 and not self.ev.select('deadline',pid=pid)
        self.add('pending_precondition','PASS' if pre else 'ERROR',[armed,p,trigger]+sends)
        exit=self.native_exit(pid);bounds=[r for r in self.ev.select('departure_bound') if r['data']['child_pid']==pid]
        departed=pre and len(bounds)==1 and bounds[0]['data']['reaped']==1 and exit and exit['data']['exited']==0 and exit['data']['signal']==number and int(exit['ns'])<=int(trigger['data']['completion_bound_ns'])
        self.add('client_departure','PASS' if departed else 'ERROR',[exit]+bounds)
        links=self.linked('request_ocb',p);ocb=links[0]['data']['ocb'] if len(links)==1 else None
        closes=[r for r in self.ev.select('close_dup') if r['data']['ocb']==ocb]
        defaults=[r for r in self.ev.select('close_dup_default') if r['data']['ocb']==ocb]
        finals=[r for r in self.ev.select('close_ocb') if r['data']['ocb']==ocb];done=[r for r in self.ev.select('close_ocb_default') if r['data']['ocb']==ocb]
        lifetime=departed and len(closes)==len(defaults)==2 and len(finals)==len(done)==1 and int(closes[0]['ns'])<int(p['ns']) and int(closes[1]['ns'])>=int(trigger['ns']) and all(r['data']['status']==0 for r in defaults+done) and int(finals[0]['ns'])>=int(closes[1]['ns']) and int(done[0]['ns'])>=int(finals[0]['ns'])
        self.add('ocb_lifetime','PASS' if lifetime else 'ERROR' if departed else 'NOT_RUN',links+closes+defaults+finals+done)
        if departed:
            self.state(self.one('control_result',operation='state'),p)
            releases=self.ev.select('control_result',operation='release')
            release=releases[-1] if releases else None
            self.condition('completion_control',release and release['data']['error']==0,[release],missing=release is None)
            self.health(self.one('result',operation='health'),p)
        else:
            for name in ('pending_state_cleanup','state_facts','fresh_client_health'):self.add(name,'NOT_RUN')
    def repeat(self,baseline):
        count=self.plan.profile.data['suite']['cycles'];cycles=[];stopped=False;timed_pids=set();last_generation=0
        for number in range(1,count+1):
            data={'cycle':number,'verdict':'ERROR','reasons':[],'completion':'incomplete','assertions':[]}
            skipped=[r for r in self.ev.select('cycle_not_run') if r['data']['cycle']==number]
            begin=[r for r in self.ev.select('cycle_begin') if r['data']['cycle']==number]
            ends=[r for r in self.ev.select('cycle_end') if r['data']['cycle']==number]
            native=[r for r in self.ev.problems if len(begin)==len(ends)==1 and int(begin[0]['ns'])<=int(r['ns'])<=int(ends[0]['ns'])]
            for code in sorted({r['data']['reason'] for r in native}):self.add(code,'ERROR',[r for r in native if r['data']['reason']==code],data)
            if skipped:
                self.add(skipped[0]['data']['reason'],'NOT_RUN' if len(skipped)==1 and not begin and not ends else 'ERROR',skipped,data)
                cycles.append(CycleResult.parse(finish(data,'aborted')).data);stopped=True;continue
            timers=self.ev.select('deadline',operation='timed',cycle=number);t=timers[0] if len(timers)==1 else None;pid=t['pid'] if t else None;p=self.pending(pid) if pid else None
            unblocks=self.linked('unblock',p)
            ready=self.ev.select('cycle_ready',cycle=number)
            pre=baseline and not stopped and len(begin)==len(ends)==len(ready)==1 and begin[0]['cycle']==ends[0]['cycle']==ready[0]['data']['cycle']==number and t and p and p['data']['pending']==1 and pid not in timed_pids and len(unblocks)==1 and unblocks[0]['data']['live']==1 and int(t['ns'])<=int(p['ns'])<int(t['data']['deadline_ns'])<=int(unblocks[0]['ns']) and int(p['data']['generation'])>last_generation
            self.add('pending_precondition','PASS' if pre else 'ERROR',timers+[p]+unblocks+ready,data)
            if pid:timed_pids.add(pid)
            if p:last_generation=int(p['data']['generation'])
            result=self.one('result',operation='timed',cycle=number);bound=int(t['data']['deadline_ns'])+self.timing.cancellation_ms*1000000 if t else 0
            bounds=self.ev.select('operation_bound',cycle=number)
            if pre and result:
                good=result['pid']==pid and result['data']['api']=='MsgSendv' and result['data']['raw_return']==-1 and result['data']['normalized']=='TIMEOUT' and result['data']['error_name']=='ETIMEDOUT' and result['data']['api_error']==self.ev.manifest['error_codes']['ETIMEDOUT'] and int(t['data']['deadline_ns'])<=int(result['ns'])<=bound
                self.condition('cancellation_completion',good,[result],data);self.terminal_once(p,data)
            elif pre:
                expired=len(bounds)==1 and bounds[0]['data']['expired']==1 and int(bounds[0]['ns'])>=bound
                self.add('cancellation_not_completed','FAIL' if expired else 'ERROR',bounds,data)
                self.add('terminal_reply_observation','NOT_RUN',target=data)
            else:
                self.add('cancellation_completion','NOT_RUN',target=data);self.add('terminal_reply_observation','NOT_RUN',target=data)
            state=self.one('control_result',operation='state',cycle=number)
            if pre and state:self.state(state,p,data)
            else:
                for name in ('pending_state_cleanup','state_facts'):self.add(name,'NOT_RUN',target=data)
            if state and state['data']['error']==0:self.condition('counter_continuity',state['data']['unblocks']==number,[state],data)
            self.health(self.one('result',operation='health',cycle=number),p,target=data)
            spawned={pid for pid,role in self.ev.child_producers.items() if role=='worker' and self.ev.spawn_cycles[pid]==number and (not begin or int(next(r for r in self.ev.select('spawned') if r['data']['child_pid']==pid)['ns'])>=int(begin[0]['ns']))}
            reaped=[r for r in self.ev.select('reaped',cycle=number) if r['data']['child_pid'] in spawned]
            clean=len(ends)==1 and ends[0]['data']['clean']==1 and {r['data']['child_pid'] for r in reaped}==spawned
            self.add('worker_cleanup','PASS' if clean else 'NOT_RUN' if native or pre and not result else 'ERROR',reaped+ends,data)
            safe=len(ends)==1 and ends[0]['data']['safe']==1
            self.add('cycle_boundary','PASS' if len(begin)==len(ends)==1 and (safe or any(a['verdict'] in {'FAIL','ERROR'} for a in data['assertions'])) else 'ERROR',begin+ends,data)
            if not safe:stopped=True
            cycles.append(CycleResult.parse(finish(data,'complete' if safe else 'aborted')).data)
        self.data['cycle_count']=count;self.data['cycles']=cycles
        complete=all(c['completion']=='complete' for c in cycles)
        # A known failure can abort the final requested cycle too. There is no
        # later cycle_not_run record in that case; its absence is not uncertainty.
        known_final_abort=(cycles[-1]['verdict']=='FAIL' and cycles[-1]['completion']=='aborted'
                           and all(c['verdict']=='PASS' and c['completion']=='complete' for c in cycles[:-1]))
        self.add('repeat_coverage','PASS' if complete else 'NOT_RUN' if known_final_abort or any(c['verdict']=='NOT_RUN' for c in cycles) else 'ERROR',self.ev.select('cycle_begin')+self.ev.select('cycle_not_run'))
    def ordering(self,baseline):
        arm=self.one('operation_armed',operation='ordered');pid=arm['pid'] if arm else None;p=self.pending(pid) if pid else None
        pre,trigger=self.signal(pid,p)
        pre=pre and baseline and len(self.linked('unblock',p))==1
        self.add('pending_precondition','PASS' if pre else 'ERROR',[arm,p,trigger]+self.linked('unblock',p))
        result=self.one('result',operation='ordered');complete_first=self.plan.data['case_id']=='complete-first'
        end=int(trigger['data']['completion_bound_ns']) if trigger else 0
        if pre and result is None:
            bounds=self.ev.select('operation_bound')
            expired=len(bounds)==1 and bounds[0]['data']['expired']==1 and int(bounds[0]['ns'])>=end
            self.add('cancellation_not_completed','FAIL' if expired else 'ERROR',bounds)
            for name in ('ordering_result','signal_handler_observation','terminal_ownership','terminal_reply_observation','stale_notification','fresh_result','unmatched_notification','state_observation','pending_state_cleanup','state_facts','fresh_client_health','ordering_coverage'):
                self.add(name,'NOT_RUN')
            if complete_first:self.add('completion_before_trigger','NOT_RUN')
            return
        good=(self.result_good(result,'health') and result['data']['api']=='MsgSendv' if complete_first else result and result['data']['api']=='MsgSendv' and result['data']['raw_return']==-1 and result['data']['api_error']==self.ev.manifest['error_codes']['EINTR'] and result['data']['error_name']=='EINTR' and result['data']['normalized']=='INTERRUPTED')
        good=good and pre and int(result['ns'])<=end
        self.condition('ordering_result',good,[result],missing=result is None)
        handler=self.one('signal_handler_observed',pid=pid) if pid else None
        self.add('signal_handler_observation','PASS' if handler and result and handler['data']['seen']==1 and handler['data']['signal']==self.ev.manifest['signal_codes']['SIGUSR1'] and pre and int(trigger['ns'])<=int(handler['ns'])<=int(result['ns']) else 'ERROR',[handler])
        terminals=self.linked('terminal_attempt',p)
        barriers=self.linked('barrier_wait',p)
        releases=[r for r in self.ev.select('control_result',operation='release') if p and r['data']['generation']==p['data']['generation']]
        release_start=self.one('started',pid=releases[0]['pid']) if len(releases)==1 else None
        observed_order=bool(terminals and release_start and result and len(releases)==1 and releases[0]['data']['error']==0)
        if complete_first:
            observed_order=observed_order and len(barriers)==1 and int(barriers[0]['ns'])<=int(terminals[0]['ns']) and int(release_start['ns'])<=int(terminals[0]['ns'])<=int(releases[0]['ns'])
        else:
            observed_order=observed_order and not barriers and int(result['ns'])<int(release_start['ns'])
        self.add('directed_order','PASS' if observed_order else 'ERROR',barriers+terminals+releases+[release_start])
        groups={}
        for row in self.ev.select('terminal_attempt'):groups.setdefault((row['data']['logical'],row['data']['generation']),[]).append(row)
        self.condition('terminal_ownership',bool(terminals) and all(len(rows)==1 for rows in groups.values()),[r for rows in groups.values() for r in rows],missing=not terminals)
        good_reply=bool(terminals) and terminals[0]['data']['rc']==0 and terminals[0]['data']['error']==0 and terminals[0]['data']['action']==('reply' if complete_first else 'cancel') and all(rows[0]['data']['rc']==0 for rows in groups.values())
        self.add('terminal_reply_observation','PASS' if good_reply else 'ERROR',terminals)
        stale=self.linked('stale_checked',p)
        self.condition('stale_notification',len(stale)==1 and stale[0]['data']['matched']==0 and terminals and int(stale[0]['ns'])>int(terminals[0]['ns']),stale,missing=not stale)
        stages=[r for r in self.ev.select('ordering_stage') if r['data']['name']=='fresh_terminal'];fresh_pid=stages[0]['data']['child_pid'] if len(stages)==1 else None
        fresh=self.one('result',pid=fresh_pid) if fresh_pid else None;fresh_pending=self.pending(fresh_pid) if fresh_pid else None
        fresh_good=self.result_good(fresh,'next_health') and fresh['data']['api']=='MsgSendv' and fresh_pending and p and fresh_pending['data']['logical']!=p['data']['logical'] and int(fresh_pending['data']['generation'])>int(p['data']['generation']) and stale and int(fresh_pending['ns'])<=int(stale[0]['ns'])<int(fresh['ns'])
        self.condition('fresh_result',fresh_good,[fresh,fresh_pending],missing=fresh is None)
        parked=self.one('parked');park_pid=parked['data']['client_pid'] if parked else None;done=self.one('park_completed');control=self.one('control_result',operation='park')
        notifications=[r for r in self.ev.select('unmatched_unblock') if parked and done and r['data']['rcvid']==parked['data']['rcvid'] and int(parked['ns'])<=int(r['ns'])<=int(done['ns'])]
        handler=self.one('signal_handler_observed',pid=park_pid) if park_pid else None
        unmatched=parked and done and control and done['data']['client_pid']==park_pid and done['data']['rc']==done['data']['error']==0 and control['pid']==park_pid and control['data']['error']==self.ev.manifest['error_codes']['EINTR'] and len(notifications)==1 and handler and handler['data']['seen']==1
        self.condition('unmatched_notification',unmatched,[parked,done,control,handler]+notifications,missing=parked is None)
        if complete_first:
            first=self.one('result',operation='finish_first');first_pid=first['pid'] if first else None
            triggers=[r for r in self.ev.select('trigger_requested') if r['data']['child_pid']==first_pid]
            after=self.one('signal_handler_observed',pid=first_pid) if first_pid else None
            sends=[r for r in self.ev.select('signal_sent') if r['data']['child_pid']==first_pid and r['data']['signal']==self.ev.manifest['signal_codes']['SIGUSR1']]
            first_good=self.result_good(first,'next_health') and first['data']['api']=='MsgSendv' and len(triggers)==len(sends)==1 and sends[0]['data']['rc']==sends[0]['data']['error']==0 and after and after['data']['seen']==1 and int(first['ns'])<int(triggers[0]['ns'])<=int(after['ns'])
            self.condition('completion_before_trigger',first_good,[first,after]+triggers,missing=first is None)
        state=self.one('control_result',operation='state')
        self.state(state,fresh_pending if not complete_first else self.pending(first_pid) if first_pid else None)
        self.health(self.one('result',operation='health_next'),fresh_pending,'next_health')
        self.add('ordering_coverage','PASS' if result and fresh and parked and done and state else 'ERROR',stages)

def evaluate_family(plan,ev,data):
    rules=Rules(plan,ev,data)
    try:
        baseline=rules.baseline()
        if plan.data['case_id']=='departure':rules.departure(baseline)
        elif plan.data['case_id']=='repeat':rules.repeat(baseline)
        else:rules.ordering(baseline)
        complete=rules.common()
    except (Invalid,KeyError,IndexError,TypeError,ValueError,OverflowError):
        rules.add('evidence_invalid','ERROR');complete=False
    aborted=any(c['completion']=='aborted' for c in data.get('cycles',[])) or any(a['id']=='ordering_coverage' and a['verdict']=='NOT_RUN' for a in data['assertions'])
    finished=finish(data,'incomplete' if not complete else 'aborted' if aborted else 'complete')
    if finished['verdict']=='ERROR':finished['completion']='incomplete'
    return EvaluatedResult.parse(finished)
