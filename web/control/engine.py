"""Private execution bridge. Only approved fixed argument vectors reach the CLI."""
from dataclasses import dataclass
import fcntl,hashlib,json,os,re,resource,selectors,signal,stat,subprocess,time
from pathlib import Path
from django.conf import settings
from resmgrcheck.contracts import Profile,load,canonical,digest
from resmgrcheck.registrations import PROFILES
from resmgrcheck.deployment import Deployment
from resmgrcheck.transport import Target as EngineTarget

class PolicyError(Exception):pass
class EngineUncertain(Exception):pass

@dataclass(frozen=True)
class Binding:
    engine_root:Path
    config:Path
    alias:str
    manifests:dict
    organization_id:str
    project_id:str


def registry(target,build=None):
    path=Path(settings.EXECUTOR_REGISTRY)
    if not path.is_file() or path.is_symlink():raise PolicyError('executor_registry_unavailable')
    info=path.stat()
    if info.st_uid not in {0,os.getuid()} or info.st_mode & 0o077:raise PolicyError('executor_registry_permissions')
    data=json.loads(path.read_text())
    if set(data)!={'schema_version','targets'} or data['schema_version']!=1:raise PolicyError('executor_registry_schema')
    row=data['targets'].get(str(target.pk))
    expected={'organization_id','project_id','engine_root','config','alias','builds'}
    if not isinstance(row,dict) or set(row)!=expected:raise PolicyError('target_not_operator_approved')
    if row['organization_id']!=str(target.project.organization_id) or row['project_id']!=str(target.project_id):raise PolicyError('target_tenant_binding_mismatch')
    if not target.approved or target.binding!=str(target.pk):raise PolicyError('target_not_operator_approved')
    root=Path(row['engine_root']).resolve();config=Path(row['config']).resolve()
    if not root.is_absolute() or not (root/'resmgrcheck/__main__.py').is_file() or not config.is_file():raise PolicyError('engine_path_unavailable')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',row['alias']):raise PolicyError('target_alias_invalid')
    EngineTarget.read(row['alias'],config)
    if build:
        filename=row['builds'].get(str(build.pk))
        if not filename or not build.approved or build.target_id!=target.pk or build.binding!=str(build.pk):raise PolicyError('build_not_operator_approved')
        selected=Deployment.parse(load(filename))
        if selected.data!=build.manifest:raise PolicyError('approved_build_identity_changed')
    return Binding(root,config,row['alias'],dict(row['builds']),row['organization_id'],row['project_id'])


def run_path(run):
    return settings.MEDIA_ROOT/str(run.project.organization_id)/str(run.project_id)/str(run.pk)


def fixed_argv(run,binding,output):
    prefix=[settings.ENGINE_PYTHON,'-m','resmgrcheck']
    target=['--target',binding.alias,'--config',str(binding.config)]
    if run.operation=='inventory':return prefix+['doctor',*target,'--out',str(output/'inventory.json')]
    manifest=str(Path(binding.manifests[str(run.build_id)]).resolve())
    common=[*target,'--candidate-manifest',manifest,'--out',str(output),'--run-id',run.native_run_id]
    if run.operation=='replay':
        original=run_path(run.original)
        return prefix+['replay',str(original/'replay.json'),*common]
    if run.operation!='run' or run.profile not in PROFILES or run.suite not in {'profile','lifecycle','health'} or run.fixture_mode not in {'fixed','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'}:
        raise PolicyError('execution_selection_invalid')
    if run.profile=='sensor' and run.fixture_mode=='drop-job':raise PolicyError('fixture_control_unsupported')
    if run.fixture_mode=='retain-third' and run.suite=='profile':raise PolicyError('required_repeat_coverage_unavailable')
    external=run.target.kind=='external-health'
    if external and run.suite!='health':raise PolicyError('external_lifecycle_unsupported')
    profile=binding.engine_root/'profiles'/(run.profile+('-external' if external else '')+'.json')
    Profile.parse(load(profile))
    return prefix+['run',*common,'--profile',str(profile),'--suite',run.suite,'--fixture-mode',run.fixture_mode]


def limits():
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(620,620))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))


def command(argv,binding,heartbeat,timeout=600,on_started=None,start_guard=None):
    # No shell, inherited API keys, SDK authentication, arbitrary cwd or environment.
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C.UTF-8','PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1',
         'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':str(binding.engine_root)}
    from contextlib import nullcontext
    process=None
    try:
        with start_guard if start_guard is not None else nullcontext():
            process=subprocess.Popen(argv,cwd=binding.engine_root,env=env,stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limits)
    except BaseException:
        if process is not None:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.wait(timeout=3)
            process.stdout.close();process.stderr.close()
        raise
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);selector.register(process.stderr,selectors.EVENT_READ)
    captured=bytearray();start=time.monotonic();last=0;reason=None
    try:
        if on_started:on_started(process.pid)
        while selector.get_map() or process.poll() is None:
            now=time.monotonic()
            if now-last>=1:
                heartbeat();last=now
            if now-start>timeout:raise EngineUncertain('host_execution_deadline')
            for key,_ in selector.select(.15):
                data=os.read(key.fileobj.fileno(),8192)
                if not data:selector.unregister(key.fileobj);continue
                captured.extend(data)
                if len(captured)>262144:raise EngineUncertain('host_output_bound')
        process.wait(timeout=2)
        return process.returncode,bytes(captured),{'local_child_exit_observed':True,'local_child_returncode':process.returncode,'local_elapsed_ms':round((time.monotonic()-start)*1000)}
    except BaseException:
        if process.poll() is None:
            # Exact live owned local group only; never signal QNX PIDs from records.
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        raise
    finally:
        selector.close();process.stdout.close();process.stderr.close()


def storage_available(binding,minimum,start_guard=None):
    target=EngineTarget.read(binding.alias,binding.config)
    # Fixed read-only OS inventory command, never a service operation/profile command.
    argv=['ssh','-F',target.data['ssh_config'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
          '-o','ConnectTimeout=5',target.data['ssh_alias'],'df -g /data']
    code,raw,_=command(argv,binding,lambda:None,timeout=8,start_guard=start_guard)
    match=re.search(rb'Files\s*:\s*([0-9]+) total\s+([0-9]+) avail',raw)
    if code or not match:raise PolicyError('target_storage_unknown')
    free=int(match[2])
    if free<minimum:raise PolicyError('target_storage_insufficient')
    return free
