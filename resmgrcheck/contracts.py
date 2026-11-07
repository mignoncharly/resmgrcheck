"""Explicit v1 contracts. Unknown fields and ambiguous JSON are errors."""
from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from .registrations import REGISTRY, CAPABILITIES

MAX_INPUT = 1024 * 1024
MAX_FRAME = 16384
MAX_EVENTS = 4096
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
DECIMAL = re.compile(r'(0|[1-9][0-9]{0,18})\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
HEXREV = re.compile(r'[0-9a-f]{40}\Z')
SCENARIOS = {'timeout','signal','departure','repeat','complete-first','cancel-first'}
FIXTURE_MODES = {'corrected','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'}

VERDICTS = {'PASS', 'FAIL', 'ERROR', 'UNSUPPORTED', 'NOT_RUN'}

class Invalid(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def obj(value, keys, label='object'):
    require(type(value) is dict and set(value) == set(keys.split()), f'{label}: fields must be {keys}')
    return value

def integer(value, lo=0, hi=1000000):
    require(type(value) is int and lo <= value <= hi, f'integer outside {lo}..{hi}')
    return value

def text(value, pattern=ID):
    require(type(value) is str and pattern.fullmatch(value) is not None, 'invalid identifier/string')
    return value

def decimal(value):
    text(value, DECIMAL)
    require(int(value) <= 2**63-1, 'decimal exceeds int64')
    return value

def boolean(value):
    require(type(value) is bool, 'expected boolean')
    return value

def enum(value, choices):
    require(type(value) is str and value in choices, f'unknown value: {value!r}')
    return value

def device(value):
    require(type(value) is str and re.fullmatch(r'/dev/resmgrcheck-[A-Za-z0-9][A-Za-z0-9_-]{0,95}', value) is not None, 'unsafe lab device path')
    return value

def strings(value, allowed):
    require(type(value) is list and len(value) <= 16, 'expected bounded list')
    require(all(type(x) is str and x in allowed for x in value), 'unknown capability/scenario')
    require(len(set(value)) == len(value), 'duplicate list entry')
    return tuple(value)

def facts(value, allowed=None):
    require(type(value) is dict and len(value) <= 16, 'invalid facts')
    for k, v in value.items():
        text(k)
        if allowed is not None: require(k in allowed, 'unknown typed fact')
        integer(v, -2147483648, 2147483647)
    return value

def version(d, kind):
    require(d.get('kind') == kind, 'wrong contract kind')
    integer(d.get('schema_version'), 1, 1)

def _pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'duplicate JSON object key')
        result[k] = v
    return result

def _tree(v, depth=0):
    require(depth <= 12, 'JSON nesting exceeds 12')
    if type(v) is dict:
        for k, item in v.items():
            require(type(k) is str and '\x00' not in k and len(k) <= 128, 'invalid JSON key')
            _tree(item, depth+1)
    elif type(v) is list:
        require(len(v) <= MAX_EVENTS, 'array too large')
        for item in v: _tree(item, depth+1)
    elif type(v) is str:
        require('\x00' not in v and len(v) <= 4096 and v.isascii(), 'invalid string')
    elif v is not None and type(v) not in (bool, int):
        raise Invalid('unsupported JSON value')

def loads(data, limit=MAX_INPUT):
    if type(data) is str: data = data.encode('utf-8')
    require(type(data) is bytes and len(data) <= limit and b'\x00' not in data, 'invalid JSON size/NUL')
    def no_number(_): raise Invalid('non-integer JSON number')
    def bounded_int(s):
        require(len(s)<=20, 'JSON integer exceeds int64')
        n=int(s)
        require(-(2**63)<=n<=2**63-1, 'JSON integer exceeds int64')
        return n
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_float=no_number, parse_constant=no_number, parse_int=bounded_int)
        _tree(value)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as e:
        raise Invalid('invalid JSON') from e

def load(path):
    with Path(path).open('rb') as f: data = f.read(MAX_INPUT+1)
    return loads(data)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

@dataclass(frozen=True)
class Timing:
    setup_ms: int
    operation_ms: int
    cancellation_ms: int
    probe_ms: int
    execution_ms: int
    cleanup_ms: int

    @classmethod
    def parse(cls, d):
        obj(d, 'setup_ms operation_ms cancellation_ms probe_ms execution_ms cleanup_ms', 'timing')
        for k, v in d.items(): integer(v, 100, 30000 if k == 'execution_ms' else 5000)
        require(d['execution_ms'] >= d['operation_ms'] + d['cancellation_ms'] + d['setup_ms'] + d['probe_ms'], 'execution bound too small')
        return cls(**d)

@dataclass(frozen=True)
class Profile:
    data: dict
    timing: Timing

    @property
    def registration(self):
        return REGISTRY[self.data["adapter"]["id"]]

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version id version adapter service operation capabilities expectations timing suite', 'profile')
        version(d, 'profile'); text(d['id']); integer(d['version'], 1, 1000000)
        a = obj(d['adapter'], 'id abi'); enum(a['id'], REGISTRY); integer(a['abi'], 1, 1)
        reg = REGISTRY[a['id']]
        s = obj(d['service'], 'mode device'); enum(s['mode'], {'managed-fixture', 'external-attach'}); device(s['device'])
        o = obj(d['operation'], 'id parameters result_shape convention')
        enum(o['id'], {reg.operation}); enum(o['convention'], {reg.convention}); enum(o['result_shape'], {'integer-record'})
        require(type(o['parameters']) is dict and set(o['parameters']) == set(reg.parameters), 'wrong operation parameters')
        for k, bounds in reg.parameters.items(): integer(o['parameters'][k], *bounds)
        suite = obj(d['suite'], 'required optional cycles reset'+(' signal_mode' if type(d['suite']) is dict and 'signal_mode' in d['suite'] else ''), 'suite')
        scenarios=strings(suite['required'],SCENARIOS)
        require(len(scenarios)==1,'one explicit scenario family required')
        scenario=scenarios[0]
        optional_scenarios=strings(suite['optional'], {'signal', 'departure', 'repeat'})
        require(not set(scenarios)&set(optional_scenarios),'scenario required/optional overlap')
        if scenario=='signal':
            require('signal_mode' in suite,'signal mode required')
            enum(suite['signal_mode'],{'non-restart-no-retry','auto-restart'})
        else:require('signal_mode' not in suite,'unexpected signal mode')
        integer(suite['cycles'],1,20 if scenario=='repeat' else 200); enum(suite['reset'], {'same-instance' if scenario=='repeat' else 'new-instance'})
        c = obj(d['capabilities'], 'required optional')
        required = strings(c['required'], CAPABILITIES); optional = strings(c['optional'], CAPABILITIES)
        require(not set(required) & set(optional), 'required/optional overlap')
        require(({'pending','state','health','release'} | ({'repeat','timeout'} if scenario=='repeat' else {'ordering','signal'} if scenario in {'complete-first','cancel-first'} else {scenario})) <= set(required), 'strict scenario profile must require its observers')
        e = obj(d['expectations'], 'cancel_error pending_after require_unblock health state_after'+(' next_health' if scenario in {'complete-first','cancel-first'} else ''))
        enum(e['cancel_error'], {'PROCESS_EXIT' if scenario=='departure' else 'ETIMEDOUT' if scenario in {'timeout','repeat'} else 'EINTR'}); integer(e['pending_after'], 0, 0); boolean(e['require_unblock'])
        require(not e['require_unblock'] or 'unblock' in required, 'unblock observation must be required')
        facts(e['health'], reg.result_facts); require(set(e['health']) == reg.result_facts, 'incomplete result predicate')
        facts(e['state_after'], reg.state_facts); require(set(e['state_after']) == reg.state_facts, 'incomplete state predicate')
        if scenario in {'complete-first','cancel-first'}:
            facts(e['next_health'],reg.result_facts);require(set(e['next_health'])==reg.result_facts,'incomplete next-result predicate')
            require(e['next_health']!=e['health'],'next request must have a distinct result')
        timing = Timing.parse(d['timing'])
        return cls(loads(canonical(d)), timing)

IDENTITY = 'run_id case_id attempt_id cycle service_instance_id'

def identity(d):
    for k in IDENTITY.split():
        if k == 'cycle': integer(d[k], 1, 200)
        else: text(d[k])

def builds(d):
    obj(d, 'source_revision dirty source_tree_sha256 compiler_variant recipe_id binaries')
    text(d['source_tree_sha256'], HASH)
    text(d['source_revision'], HEXREV); boolean(d['dirty']); enum(d['compiler_variant'], {'gcc_ntox86_64'})
    text(d['recipe_id'], HASH)
    obj(d['binaries'], 'runner worker fixture adapter')
    for value in d['binaries'].values(): text(value, HASH)

@dataclass(frozen=True)
class Plan:
    data: dict
    profile: Profile

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version '+IDENTITY+' profile profile_sha256 suite_sha256 fixture_mode builds', 'plan')
        version(d, 'scenario-plan'); identity(d)
        profile = Profile.parse(d['profile'])
        require(d['case_id']==profile.data['suite']['required'][0],'case/scenario mismatch')
        text(d['profile_sha256'], HASH); require(d['profile_sha256'] == digest(profile.data), 'profile hash mismatch')
        text(d['suite_sha256'], HASH); require(d['suite_sha256'] == digest(profile.data['suite']), 'suite hash mismatch')
        enum(d['fixture_mode'], profile.registration.fixture_modes); builds(d['builds'])
        require(d['cycle']==1,'aggregate plan starts at cycle one')
        require(d['case_id']=='repeat' or profile.data['suite']['cycles']==1,'single-case cycle count')
        return cls(loads(canonical(d)), profile)

@dataclass(frozen=True)
class ProducerEvent:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version '+IDENTITY+' producer pid seq ns event data', 'event')
        version(d, 'producer-event'); identity(d)
        enum(d['producer'], {'fixture', 'worker', 'supervisor'}); decimal(d['pid']); require(int(d['pid']) > 0, 'zero pid')
        integer(d['seq'], 1, MAX_EVENTS); decimal(d['ns']); text(d['event'])
        require(type(d['data']) is dict and len(d['data']) <= 32, 'invalid event payload')
        _tree(d['data']); event_payload(d)
        return cls(d)

@dataclass(frozen=True)
class TargetManifest:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version '+IDENTITY+' tool_version adapter_id adapter_abi capabilities profile_sha256 suite_sha256 builds target fixture_mode error_codes'+(' signal_codes' if type(d) is dict and 'signal_codes' in d else ''), 'manifest')
        version(d, 'target-run-manifest'); identity(d)
        require(d['tool_version'] == '0.3.0', 'unknown tool version')
        enum(d['adapter_id'], REGISTRY); integer(d['adapter_abi'], 1, 1)
        strings(d['capabilities'], CAPABILITIES)
        text(d['profile_sha256'], HASH); text(d['suite_sha256'], HASH); builds(d['builds'])
        t = obj(d['target'], 'sysname release version machine scheduling_policy priority')
        require(t['sysname'] == 'QNX', 'not a QNX target')
        for k in ('release', 'version', 'machine'): require(type(t[k]) is str and 0 < len(t[k]) <= 128 and all(32<=ord(c)<=126 for c in t[k]), 'invalid target identity')
        integer(t['scheduling_policy'], 0, 100); integer(t['priority'], 0, 255)
        enum(d['fixture_mode'], FIXTURE_MODES)
        obj(d['error_codes'], 'EOK ETIMEDOUT EINTR ENOENT')
        integer(d['error_codes']['EOK'],0,0)
        for k in ('ETIMEDOUT','EINTR','ENOENT'): integer(d['error_codes'][k],1,65535)
        if 'signal_codes' in d:
            obj(d['signal_codes'],'SIGUSR1'+(' SIGKILL' if 'SIGKILL' in d['signal_codes'] else ''));integer(d['signal_codes']['SIGUSR1'],1,255)
            if 'SIGKILL' in d['signal_codes']:integer(d['signal_codes']['SIGKILL'],1,255)
        return cls(d)

@dataclass(frozen=True)
class CycleResult:
    data: dict

    @classmethod
    def parse(cls,d):
        obj(d,'cycle verdict reasons completion assertions','cycle result');integer(d['cycle'],1,20)
        enum(d['verdict'],VERDICTS);enum(d['completion'],{'complete','incomplete','aborted'})
        require(type(d['reasons']) is list and 1<=len(d['reasons'])<=32,'cycle reasons')
        for value in d['reasons']:text(value)
        require(type(d['assertions']) is list and len(d['assertions'])<=32,'cycle assertions')
        for a in d['assertions']:
            obj(a,'id verdict event_refs');text(a['id']);enum(a['verdict'],VERDICTS)
            require(type(a['event_refs']) is list and len(a['event_refs'])<=512,'cycle refs')
            for ref in a['event_refs']:integer(ref,0,MAX_EVENTS)
        require(len({a['id'] for a in d['assertions']})==len(d['assertions']),'duplicate cycle assertion')
        mandatory={'pending_precondition','cancellation_completion','terminal_reply_observation','pending_state_cleanup','state_facts','fresh_client_health','worker_cleanup','cycle_boundary','counter_continuity'}
        require(d['verdict']!='PASS' or (d['completion']=='complete' and mandatory<={a['id'] for a in d['assertions']} and all(a['verdict']=='PASS' for a in d['assertions'])),'inconsistent cycle PASS')
        return cls(d)

@dataclass(frozen=True)
class EvaluatedResult:
    data: dict

    @classmethod
    def parse(cls, d):
        keys='kind schema_version '+IDENTITY+' verdict reasons completion assertions profile_sha256 event_sha256 fixture_mode'
        if type(d) is dict and 'status_sha256' in d:
            keys+=' status_sha256'
            text(d['status_sha256'],HASH)
        if type(d) is dict and 'cycles' in d:
            keys+=' cycle_count cycles';integer(d['cycle_count'],1,20)
            require(d['case_id']=='repeat' and type(d['cycles']) is list and len(d['cycles'])==d['cycle_count'],'cycle coverage')
            for c in d['cycles']:CycleResult.parse(c)
            require([c['cycle'] for c in d['cycles']]==list(range(1,d['cycle_count']+1)),'cycle identities')
        obj(d, keys, 'result')
        version(d, 'evaluated-result'); identity(d); enum(d['verdict'], VERDICTS)
        enum(d['fixture_mode'], FIXTURE_MODES)
        enum(d['completion'], {'complete', 'incomplete', 'aborted'})
        require(type(d['reasons']) is list and 1 <= len(d['reasons']) <= 32, 'invalid reasons')
        for r in d['reasons']: text(r)
        require(len(set(d['reasons']))==len(d['reasons']), 'duplicate reason')
        text(d['profile_sha256'], HASH); text(d['event_sha256'], HASH)
        require(type(d['assertions']) is list and len(d['assertions']) <= 32, 'invalid assertions')
        for a in d['assertions']:
            obj(a, 'id verdict event_refs'); text(a['id']); enum(a['verdict'], VERDICTS)
            require(type(a['event_refs']) is list and len(a['event_refs']) <= 512, 'invalid evidence references')
            for ref in a['event_refs']: integer(ref, 0, MAX_EVENTS)
        ids=[a['id'] for a in d['assertions']]
        require(len(set(ids))==len(ids), 'duplicate assertion')
        require(d['verdict'] != 'PASS' or (d['completion'] == 'complete' and d['assertions'] and all(a['verdict'] == 'PASS' for a in d['assertions'])), 'inconsistent PASS')
        required={'baseline_validity','pending_precondition','cancellation_completion','terminal_reply_observation',
                  'state_observation','pending_state_cleanup','state_facts','fresh_client_health','owned_process_cleanup','evidence_completeness'}
        if d['case_id']=='signal':required.add('signal_handler_observation')
        if d['case_id']=='departure':required={'baseline_validity','pending_precondition','client_departure','ocb_lifetime','pending_state_cleanup','state_facts','fresh_client_health','single_instance','owned_process_cleanup','evidence_completeness'}
        if d['case_id'] in {'complete-first','cancel-first'}:required={'baseline_validity','pending_precondition','ordering_result','signal_handler_observation','terminal_ownership','terminal_reply_observation','stale_notification','fresh_result','unmatched_notification','pending_state_cleanup','state_facts','fresh_client_health','single_instance','owned_process_cleanup','evidence_completeness','ordering_coverage','directed_order'}
        if d['case_id']=='complete-first':required.add('completion_before_trigger')
        if d['case_id']=='repeat':
            required={'baseline_validity','single_instance','repeat_coverage','owned_process_cleanup','evidence_completeness'}
            require(d['verdict']!='PASS' or ('cycles' in d and all(c['verdict']=='PASS' for c in d['cycles'])),'missing passed cycles')
        require(d['verdict']!='PASS' or required<=set(ids), 'missing PASS obligations')
        return cls(d)

@dataclass(frozen=True)
class ReplayInput:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version original_plan original_event_sha256 selected_builds', 'replay')
        version(d, 'replay-input'); Plan.parse(d['original_plan']); text(d['original_event_sha256'], HASH)
        builds(d['selected_builds'])
        return cls(d)

# Exact per-event payloads. Service-specific values are typed facts, not code.
def _word(v): return text(v)
def _number(v): return integer(v, -2147483648, 2147483647)
def _count(v): return integer(v, 0, 1000000)
def _flag(v): return integer(v, 0, 1)
def _runtime_device(v):
    require(type(v) is str and re.fullmatch(r'/dev/resmgrcheck-[A-Za-z0-9_-]{1,180}', v) is not None, 'unsafe runtime device')
def _facts(v): return facts(v)

EVENT_FIELDS = {
 'request_ocb': {'logical':decimal,'generation':decimal,'client_pid':decimal,'ocb':_count},
 'close_dup': {'ocb':_count,'client_pid':decimal,'rcvid':decimal,'synthetic':_flag},
 'close_dup_default': {'ocb':_count,'status':_number},
 'close_ocb': {'ocb':_count},
 'close_ocb_default': {'ocb':_count,'status':_number},
 'terminal_attempt': {'logical':decimal,'generation':decimal,'rcvid':decimal,'action':_word,'rc':_number,'error':_count},
 'retained_request': {'logical':decimal,'generation':decimal,'pending':_count},
 'barrier_wait': {'logical':decimal,'generation':decimal,'rcvid':decimal},
 'stale_checked': {'logical':decimal,'generation':decimal,'rcvid':decimal,'live':_flag,'matched':_flag},
 'cycle_ready': {'cycle':_count,'pending':_count,'generation':decimal},
 'parked': {'client_pid':decimal,'rcvid':decimal},
 'park_completed': {'client_pid':decimal,'rcvid':decimal,'rc':_number,'error':_count},
 'descriptor_duplicated': {'rc':_number,'error':_count},
 'descriptor_closed': {'descriptor':_count,'rc':_number,'error':_count},
 'cycle_begin': {'cycle':_count,'fixture_pid':decimal,'deadline_ns':decimal},
 'cycle_end': {'cycle':_count,'worker_pid':decimal,'worker_reaped':_flag,'pending':_count,'state_observed':_flag,'clean':_flag,'safe':_flag},
 'cycle_not_run': {'cycle':_count,'reason':_word},
 'departure_bound': {'child_pid':decimal,'completion_bound_ns':decimal,'reaped':_flag},
 'ordering_stage': {'name':_word,'child_pid':decimal},

 'lab_control': {'name':_word},
 'lab_injection': {'name':_word,'operation':_word},
 'lab_noise': {'index':_count},
 'phase': {'name':_word},
 'problem': {'reason':_word,'child_pid':decimal,'operation':_word,'error':_count},
 'wait_bound': {'child_pid':decimal,'operation':_word,'deadline_ns':decimal,'timed_out':_flag},
 'invalid_frame': {'child_pid':decimal,'reason':_word,'size':_count,'prefix_hex':lambda v: text(v,re.compile(r'[0-9a-f]{0,128}\Z'))},
 'dependency': {'predecessor_id':_word,'state':_word},
 'case_not_run': {'predecessor_id':_word,'reason':_word},
 'run_storage': {'run_id':_word},
 'settings': {'mode':_word,'timeout_ms':_count,'allowance_ms':_count,'path':_runtime_device,'case_ms':_count,'cleanup_ms':_count},
 'spawned': {'binary':_word,'child_pid':decimal,'operation':_word},
 'reaped': {'child_pid':decimal,'raw_status':_count},
 'process_exit': {'child_pid':decimal,'exited':_flag,'exit_code':_count,'signal':_count},
 'lab_discarded_wait': {'child_pid':decimal,'raw_status':_count},
 'ready': {'path':_runtime_device,'mode':_word},
 'started': {'operation':_word},
 'result': {'operation':_word,'api':_word,'raw_return':_number,'raw_errno':_count,'api_error':_count,
            'normalized':_word,'error_name':_word,'result_shape':_word,'facts':_facts},
 'control_result': {'operation':_word,'error':_count,'pending':_count,'unblocks':_count,'completed':_count,'generation':decimal,'facts':_facts},
 'closed': {'rc':_number,'error':_count},
 'worker_final': {'exit_code':_count},
 'open_error': {'error':_count},
 'arm_error': {'error':_count},
 'deadline': {'operation':_word,'deadline_ns':decimal,'timeout_ms':_count},
 'signal_setup': {'name':_word,'signal':_count,'flags':_count,'retry':_flag,'timeout_armed':_flag,'masked':_flag,'error':_count},
 'operation_armed': {'operation':_word,'timeout_armed':_flag},
 'signal_handler_observed': {'signal':_count,'seen':_flag},
 'trigger_requested': {'child_pid':decimal,'signal':_count,'completion_bound_ns':decimal},
 'received': {'logical':decimal,'generation':decimal,'rcvid':decimal,'client_pid':decimal},
 'sample': {'logical':decimal,'generation':decimal,'bytes':_count},
 'pending': {'logical':decimal,'generation':decimal,'rcvid':decimal,'client_pid':decimal,'pending':_count},
 'released': {'logical':decimal,'generation':decimal,'rc':_number},
 'removed': {'logical':decimal,'generation':decimal,'pending':_count,'reason':_word},
 'unblock': {'logical':decimal,'generation':decimal,'rcvid':decimal,'live':_flag,'mode':_word},
 'ignored_unblock': {'logical':decimal,'generation':decimal,'pending':_count},
 'cancel_completed': {'logical':decimal,'generation':decimal,'rc':_number,'error':_count},
 'obsolete_unblock': {'rcvid':decimal},
 'unmatched_unblock': {'rcvid':decimal},
 'state_changed': {'action':_word,'generation':decimal},
 'stage': {'name':_word},
 'operation_bound': {'completion_bound_ns':decimal,'expired':_flag,'result_observed':_flag,'worker_reaped':_flag},
 'health_withheld': {'reason':_word},
 'signal_sent': {'child_pid':decimal,'signal':_count,'rc':_number,'error':_count},
 'termination_observation': {'child_pid':decimal,'signal':_count,'reaped':_flag},
 'fixture_stop': {'child_pid':decimal,'blocked_worker_reaped':_flag},
 'cleanup': {'all_reaped':_flag,'evidence_error':_flag},
 'run_final': {'flow_complete':_flag,'cleanup_ok':_flag,'evidence_error':_flag},
 'evidence_error': {'reason':_word},
 'execution_error': {'reason':_word},
 'unsupported': {'reason':_word},
 'spawn_error': {'binary':_word,'error':_count},
}

def event_payload(d):
    enum(d['event'], EVENT_FIELDS)
    fields = EVENT_FIELDS[d['event']]
    require(d['producer'] == EVENT_PRODUCERS[d['event']], 'event producer role mismatch')
    obj(d['data'], ' '.join(fields), 'event payload')
    for key, check in fields.items(): check(d['data'][key])
    if d['event']=='closed':
        r=d['data'];require((r['rc']==0 and r['error']==0) or (r['rc']==-1 and r['error']>0),'invalid close convention')
    if d['event']=='close_dup':require(d['data']['synthetic']==int(d['data']['rcvid']=='0'),'inconsistent synthetic-close marker')
    if d['event']=='process_exit':
        r=d['data'];integer(r['exit_code'],0,255);integer(r['signal'],0,255)
        require((r['exited']==1 and r['signal']==0) or (r['exited']==0 and r['exit_code']==0),'invalid native exit observation')
    if d['event'] == 'result':
        r=d['data']
        enum(r['api'], {'read','devctl','MsgSendv'})
        enum(r['normalized'], {'OK','TIMEOUT','INTERRUPTED','API_ERROR','INVALID_REPLY'})
        enum(r['error_name'], {'EOK','ETIMEDOUT','EINTR','ENOENT','API_ERROR'})
        enum(r['result_shape'], {'integer-record'})
        if r['api'] == 'devctl':
            require(r['raw_return'] >= 0 and r['api_error'] == r['raw_return'], 'invalid devctl convention')
        elif r['raw_return'] == -1:
            require(r['raw_errno'] > 0 and r['api_error'] == r['raw_errno'], 'invalid errno convention')
        else:
            require(r['raw_return'] >= 0 and r['api_error'] == 0, 'invalid successful API result')
        if r['normalized'] == 'OK': require(r['api_error'] == 0 and r['error_name'] == 'EOK', 'inconsistent OK')
        elif r['normalized'] != 'INVALID_REPLY': require(r['api_error'] > 0 and not r['facts'], 'inconsistent API error')

EVENT_PRODUCERS = {name:'supervisor' for name in EVENT_FIELDS}
for _name in ('request_ocb', 'close_dup', 'close_dup_default', 'close_ocb', 'close_ocb_default', 'terminal_attempt', 'retained_request', 'barrier_wait', 'stale_checked', 'cycle_ready', 'parked', 'park_completed'):EVENT_PRODUCERS[_name]='fixture'
EVENT_PRODUCERS['descriptor_closed']='worker'
EVENT_PRODUCERS['descriptor_duplicated']='worker'
for _name in ('ready','received','sample','pending','released','removed','unblock','ignored_unblock','cancel_completed','obsolete_unblock','unmatched_unblock','state_changed'):
    EVENT_PRODUCERS[_name]='fixture'
for _name in ('started','result','control_result','closed','worker_final','open_error','arm_error','deadline','lab_injection','lab_noise','signal_setup','operation_armed','signal_handler_observed'):
    EVENT_PRODUCERS[_name]='worker'


@dataclass(frozen=True)
class RunStarted:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version '+IDENTITY+' supervisor_pid', 'start acknowledgement')
        version(d,'run-started'); identity(d); decimal(d['supervisor_pid'])
        require(int(d['supervisor_pid'])>0,'zero supervisor pid')
        return cls(d)

@dataclass(frozen=True)
class RunStatus:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version '+IDENTITY+' supervisor_pid started_ns state cleanup_ok exit_code unresolved profile_sha256 source_tree_sha256'+(' event_file lab_control' if type(d) is dict and 'event_file' in d else ''), 'run status')
        version(d,'run-status'); identity(d); decimal(d['supervisor_pid']); decimal(d['started_ns'])
        require(int(d['supervisor_pid'])>0,'zero supervisor pid')
        enum(d['state'],{'running','complete','incomplete','not-run'}); boolean(d['cleanup_ok']); integer(d['exit_code'],-1,255)
        text(d['profile_sha256'],HASH); text(d['source_tree_sha256'],HASH)
        require(type(d['unresolved']) is list and len(d['unresolved'])<=16,'invalid unresolved process list')
        seen=set()
        for process in d['unresolved']:
            obj(process,'pid role'); decimal(process['pid']); enum(process['role'],{'worker','fixture','manager'})
            require(int(process['pid'])>0 and process['pid'] not in seen,'invalid/duplicate unresolved pid')
            seen.add(process['pid'])
        if 'event_file' in d:
            enum(d['event_file'],{'events.jsonl','recovery.jsonl'});text(d['lab_control'])
        if d['state']=='not-run': require(d['cleanup_ok'] and not d['unresolved'] and d['exit_code']==4,'inconsistent withheld status')
        if d['state']=='running': require(d['exit_code']==-1,'running status cannot declare an exit')
        if d['state']=='complete': require(d['cleanup_ok'] and not d['unresolved'] and d['exit_code'] in (0,3),'inconsistent complete status')
        return cls(d)
