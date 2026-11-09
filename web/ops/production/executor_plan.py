"""Reviewed fixed lab bindings. No browser-controlled hosts, commands or paths."""
import hashlib,json,os,stat,uuid
from pathlib import Path

APPLICATION='3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58'
ENGINE='ca4f74e0fcff33b6f6ebf6c553b3f8379f6440e0'
SOURCE=Path('/home/mignon/projects/resmgrcheck')
CONFIG=Path('/etc/resmgrcheck/executor')
STATE=Path('/var/lib/resmgrcheck/private/operator/native-acceptance')
ENGINE_ROOT=Path('/opt/resmgrcheck/engine')
PUBLIC_TARGET={'uid':0,'processor':'x86_64','machine':'x86pc','release':'8.0.0',
 'recipe_id':'6cb923cc6f93fb122c8d36d63a8359663681db0357d826d6890ea7ddbfdc254f','root':'/data/resmgrcheck'}
MANIFESTS={
 'before':('docs/evidence/phase10/original-deployment.json','abe191304ede875bdd88f2749214ea2fee2439ab33e4c7ac5121fcd52c6b45ac'),
 'after':('docs/evidence/phase10/candidate-deployment.json','600f56ac7b370da6eb1cc3dd8c64f091b01c3948a0f509c528021cdcac5aef4c')}
NAMESPACE=uuid.uuid5(uuid.NAMESPACE_URL,'https://qnx-resmgrcheck.gestionatech.de/operator-approved-lab/v1')
IDS={key:str(uuid.uuid5(NAMESPACE,key)) for key in ['custodian','organization','project','target','before','after']}
KNOWN_HOSTS_SHA='91e8f929fcbf1f9454e28ec78bb2740a8ceea4cf6c8eef9c15d9aa58811045e7'
INPUT_CONFIG_SHA='84c1a656f6e0e78ebcecffde5eefba6ef95f1b45c0b4b89044e2239defc3c9db'

def require(value,code):
    if not value:raise ValueError(code)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def probe_file(driver):return Path('/var/lib/resmgrcheck/private/executor')/('production-probe-'+driver+'.json')

def read_owned(path,uid,modes,limit=1024**2):
    path=Path(path)
    require(path.is_absolute() and '..' not in path.parts,'absolute_path_required')
    require(not any(p.is_symlink() for p in [path,*path.parents]),'resource_symlink')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid==uid and info.st_nlink==1 and
            stat.S_IMODE(info.st_mode) in modes and info.st_size<=limit,'resource_protection')
        raw=os.read(fd,limit+1);after=os.fstat(fd)
        require(len(raw)==info.st_size and (info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)==
            (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'resource_changed')
        return raw
    finally:os.close(fd)

def target_config():
    return {'kind':'target-configuration','schema_version':1,'targets':{'lab':{
        **PUBLIC_TARGET,'ssh_alias':'resmgrcheck-lab','ssh_config':str(CONFIG/'ssh-config'),'timeout_s':10}}}

def ssh_config():
    return ('Host resmgrcheck-lab\n HostName 127.0.0.1\n Port 22220\n User root\n'
        ' BatchMode yes\n IdentitiesOnly yes\n StrictHostKeyChecking yes\n'
        ' IdentityFile '+str(CONFIG/'ssh-key')+'\n UserKnownHostsFile '+str(CONFIG/'known-hosts')+'\n'
        ' GlobalKnownHostsFile /dev/null\n PasswordAuthentication no\n KbdInteractiveAuthentication no\n'
        ' ForwardAgent no\n ClearAllForwardings yes\n PermitLocalCommand no\n RequestTTY no\n').encode()

def registry():
    return {'schema_version':1,'targets':{IDS['target']:{'organization_id':IDS['organization'],
        'project_id':IDS['project'],'engine_root':str(ENGINE_ROOT),'config':str(CONFIG/'target.json'),
        'alias':'lab','builds':{IDS[role]:str(CONFIG/(role+'-deployment.json')) for role in MANIFESTS}}}}

def manifest_pair(root):
    from resmgrcheck.deployment import Deployment
    result={}
    for role,(name,expected) in MANIFESTS.items():
        raw=(root/name).read_bytes();require(digest(raw)==expected,'manifest_hash_differs')
        d=Deployment.parse(json.loads(raw)).data
        require(not d['build']['dirty'] and set(d['candidates'])=={'sensor-v1','job-v1'},'manifest_scope')
        for key,other in [('uid','uid'),('architecture','processor'),('machine','machine'),('release','release'),('recipe_id','recipe_id')]:
            require(d[key]==PUBLIC_TARGET[other],'manifest_target_identity')
        result[role]=d
    a,b=result['before'],result['after']
    require(a['build']['source_tree_sha256']!=b['build']['source_tree_sha256'] and
        a['files']['sensor-v1-fixture']!=b['files']['sensor-v1-fixture'],'source_correction_required')
    require(all(a['files'][name]==b['files'][name] for name in ['runner','worker']),'common_engine_changed')
    return result
