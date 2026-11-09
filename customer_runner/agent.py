"""Bounded local engine bridge. Customer credentials never leave local CLI custody."""
import os,re,resource,selectors,signal,subprocess,time
from pathlib import Path
from . import protocol as wire
from .client import protected

def config(path):
    value=wire.parse(protected(Path(path),16384))
    wire.fields(value,'origin server_public_key target_id organization_id project_id engine_root target_config alias manifests attachment')
    import uuid
    for name in ['target_id','organization_id','project_id']:wire.require(str(uuid.UUID(value[name]))==value[name],'configuration_identity_invalid')
    wire.origin(value['origin']);wire.hex_value(value['server_public_key'])
    wire.require(re.fullmatch('[A-Za-z0-9_-]{1,40}',value['alias']) is not None,'configuration_alias_invalid')
    for name in ['engine_root','target_config']:
        path=Path(value[name]);wire.require(path.is_absolute() and not any(p.is_symlink() for p in [path,*path.parents]),'configuration_path_invalid')
    wire.require((Path(value['engine_root'])/'resmgrcheck/__main__.py').is_file(),'engine_unavailable')
    wire.require(value['attachment'] in {'managed-fixture','external-attach'},'attachment_invalid')
    wire.require(type(value['manifests']) is dict and len(value['manifests'])<=20,'manifest_allowlist_invalid')
    from resmgrcheck.contracts import load
    from resmgrcheck.deployment import Deployment
    for identity,path in value['manifests'].items():
        wire.hex_value(identity)
        selected=Deployment.parse(load(path));wire.require(selected.data['deployment_id']==identity,'local_build_binding_mismatch')
    return value

def limits():
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(620,620))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))

def command(configuration,args,heartbeat=lambda:None,timeout=600):
    argv=['/usr/bin/python3','-B','-m','resmgrcheck',*args]
    root=Path(configuration['engine_root'])
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1',
        'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':str(root)}
    process=subprocess.Popen(argv,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,preexec_fn=limits)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);selector.register(process.stderr,selectors.EVENT_READ)
    start=time.monotonic();last=0;total=0
    try:
        while selector.get_map() or process.poll() is None:
            now=time.monotonic();wire.require(now-start<=timeout,'local_execution_deadline')
            if now-last>=25:
                heartbeat();last=now
            for key,_ in selector.select(.15):
                block=os.read(key.fileobj.fileno(),8192)
                if not block:selector.unregister(key.fileobj)
                total+=len(block);wire.require(total<=262144,'local_output_bound')
        return process.wait(timeout=2)
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        selector.close();process.stdout.close();process.stderr.close()

def discover(configuration,output):
    from resmgrcheck.contracts import load
    from resmgrcheck.transport import Target
    from resmgrcheck.build_identity import source_hash
    args=['doctor','--target',configuration['alias'],'--config',configuration['target_config'],'--out',str(output)]
    command(configuration,args,timeout=90)
    result=load(output);checks={row['id']:row for row in result['checks']}
    wire.require(all(checks.get(name,{}).get('state')=='PASS' for name in ['target_reachable','target_compatibility','ssh_command_path','transfer','target_capabilities']),'target_discovery_unproven')
    caps=checks['target_capabilities']['detail']['compiled_adapter_capabilities']
    target=Target.read(configuration['alias'],configuration['target_config'])
    return {'protocol':wire.VERSION,'runner_version':'1','engine_sha256':source_hash(Path(configuration['engine_root'])),'route_sha256':route_fingerprint(configuration),
        'target_identity':target.public(),'compiled_adapters':caps,'attachment':configuration['attachment']}

def route_fingerprint(configuration):
    """Pin local routing without sending addresses or SSH configuration contents."""
    from resmgrcheck.transport import Target
    target=Target.read(configuration['alias'],configuration['target_config'])
    return wire.fingerprint({'target':target.data,'alias':configuration['alias'],
        'target_config_sha256':__import__('hashlib').sha256(protected(Path(configuration['target_config']))).hexdigest(),
        'ssh_config_sha256':__import__('hashlib').sha256(protected(Path(target.data['ssh_config']))).hexdigest()})
