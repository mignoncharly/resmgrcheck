#!/usr/bin/env python3
"""One operator command for the existing private release's dedicated HTTPS vhost.

Default: unprivileged review plan. --apply requires local root. Never patches an
immutable release or changes another site, application unit, database role or key.
"""
import argparse,errno,fcntl,grp,hashlib,json,os,pwd,re,secrets,signal,stat,struct,subprocess,sys,time
from contextlib import contextmanager
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from https_config import HOST,http_config,site_config,renewal_hook
from https_checks import Client,CheckFailed,checks,require

HERE=Path(__file__).resolve().parent;SOURCE=HERE.parents[2]
NGINX=Path('/etc/nginx');SITE=NGINX/'sites-available'/HOST;HTTP=NGINX/'conf.d/resmgrcheck-security.conf'
ENABLED=NGINX/'sites-enabled'/HOST
LE=Path('/etc/letsencrypt');HOOK=LE/'renewal-hooks/deploy/resmgrcheck-nginx'
STATE=Path('/var/lib/resmgrcheck/private/operator/https-deployment')
OPT=Path('/opt/resmgrcheck');CONFIG=Path('/etc/resmgrcheck');ACME=Path('/var/www/resmgrcheck-acme/.well-known/acme-challenge')
LOGS=Path('/var/log/nginx');ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
DIAGNOSTIC=None
RECOVERABLE_DRIVERS={'f8a6009b32eb5e2f3c683ae69a8df32c50b6c0f9','e1ef88c413ee30e7e467512d3610f05a8343c3f1','8000144314684674c2d672c83956c0732498edff'}

def require_root():require(os.geteuid()==0,'local_root_operator_required')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def metadata(path):
    info=path.lstat();return (info.st_dev,info.st_ino,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode),info.st_size,info.st_mtime_ns)

def directory(path,mode=None):
    require(not any(p.is_symlink() for p in [path,*path.parents]),'directory_symlink')
    info=path.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid() and not info.st_mode&0o022,'directory_protection')
    if mode is not None:require(stat.S_IMODE(info.st_mode)==mode,'directory_mode')

def read(path,*,private=False,limit=2*1024**2):
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1 and not info.st_mode&0o022 and info.st_size<=limit,'file_protection')
        if private:require(stat.S_IMODE(info.st_mode)==0o600,'private_file_protection')
        raw=os.read(descriptor,limit+1);after=os.fstat(descriptor)
        require(len(raw)==info.st_size and (info.st_size,info.st_mtime_ns,info.st_ctime_ns)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns),'file_changed_during_read')
        return raw
    finally:os.close(descriptor)

def fsync_directory(path):
    descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)

def static_asset(path):
    raw=read(path);require(stat.S_IMODE(path.lstat().st_mode)==0o644,'static_asset_permissions');return raw

def new_file(path,raw,mode=0o600,owner=None):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(raw);stream.flush();os.fchmod(stream.fileno(),mode)
        if owner is not None:os.fchown(stream.fileno(),*owner)
        os.fsync(stream.fileno())
    fsync_directory(path.parent)

def replace_owned(path,raw,expected,mode=0o644):
    if path.exists() or path.is_symlink():require(read(path)==expected,'configuration_changed_concurrently')
    else:require(expected is None,'configuration_disappeared')
    temporary=path.parent/('.resmgrcheck-'+secrets.token_hex(12))
    new_file(temporary,raw,mode)
    try:
        if expected is not None:require(read(path)==expected,'configuration_changed_concurrently')
        else:require(not path.exists() and not path.is_symlink(),'configuration_became_occupied')
        os.replace(temporary,path);fsync_directory(path.parent)
    finally:
        if temporary.exists():temporary.unlink()

def record(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    if path.exists():replace_owned(path,raw,read(path,private=True),0o600)
    else:new_file(path,raw)

def command(argv,*,data=None,timeout=30,progress=None):
    # Never reflect stdout/stderr/configs into an exception or the operator summary.
    process=subprocess.Popen(list(map(str,argv)),stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd='/',env=ENV,start_new_session=True)
    try:
        if progress:
            started=time.monotonic();first=True
            while True:
                remaining=timeout-(time.monotonic()-started)
                if remaining<=0:raise subprocess.TimeoutExpired(argv,timeout)
                try:
                    output,diagnostic=process.communicate(input=data if first else None,timeout=min(30,remaining));break
                except subprocess.TimeoutExpired:
                    first=False
                    print(json.dumps({'step':progress,'status':'running','elapsed_seconds':round(time.monotonic()-started)}),flush=True)
        else:output,diagnostic=process.communicate(input=data,timeout=timeout)
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=3)
        raise
    if process.returncode:
        if DIAGNOSTIC is not None:
            descriptor=os.open(DIAGNOSTIC,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
            info=os.fstat(descriptor)
            if not (stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600):
                os.close(descriptor);raise CheckFailed('diagnostic_log_protection')
            with os.fdopen(descriptor,'ab') as stream:stream.write(output[:32768]+diagnostic[:32768]+b'\n')
        raise CheckFailed('command_failed_'+Path(str(argv[0])).name)
    require(len(output)<=8*1024**2,'command_output_bound')
    return output

def git(*args):
    return command(['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(SOURCE),
        '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',SOURCE,*args])

def source_check(revision,driver):
    require(re.fullmatch('[0-9a-f]{40}',revision) and re.fullmatch('[0-9a-f]{40}',driver),'exact_commits_required')
    git('merge-base','--is-ancestor',driver,'HEAD')
    require(not git('diff','--name-only',driver,'HEAD','--','web/ops/production').strip(),'driver_code_differs')
    require(not git('status','--porcelain','--untracked-files=no').strip(),'driver_has_tracked_changes')
    git('merge-base','--is-ancestor',revision,driver)
    # Driver/tests/docs only. No unreviewed application upgrade gets published.
    require(not git('diff','--name-only',revision,driver,'--','web/control','web/resmgr_web','web/requirements.lock',
        'web/ops/gunicorn.conf.py','web/ops/production/resmgrcheck-*','resmgrcheck','native','profiles').strip(),'application_change_requires_immutable_upgrade')

def unrelated_snapshot():
    result={}
    for path in sorted(NGINX.rglob('*')):
        if path in {SITE,HTTP}:continue
        info=path.lstat()
        if stat.S_ISLNK(info.st_mode):value={'link':os.readlink(path)}
        elif stat.S_ISREG(info.st_mode):
            require(info.st_size<=4*1024**2,'nginx_inventory_member_bound');value={'sha256':digest(path.read_bytes())}
        elif stat.S_ISDIR(info.st_mode):continue
        else:raise CheckFailed('unexpected_nginx_resource')
        result[str(path.relative_to(NGINX))]={'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode),**value}
    require(len(result)<=2000,'nginx_inventory_bound');return result

def units_and_runtime(revision):
    expected=OPT/'releases'/revision
    require((OPT/'current').is_symlink() and os.readlink(OPT/'current')==str(expected),'active_release_differs')
    directory(expected,0o755)
    head=command(['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(expected),'-c','core.fsmonitor=false','-C',expected,'rev-parse','HEAD']).decode().strip()
    require(head==revision,'installed_revision_differs')
    require(not command(['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(expected),'-c','core.fsmonitor=false','-C',expected,'diff','--name-only','HEAD']).strip(),'installed_release_modified')
    for name in ['resmgrcheck-web.service','resmgrcheck-web.socket']:
        require(read(Path('/etc/systemd/system')/name)==(expected/'web/ops/production'/name).read_bytes(),'canonical_unit_changed')
        require(not command(['systemctl','show','--value','--property=DropInPaths',name]).strip(),'unit_override_requires_review')
        require(command(['systemctl','show','--value','--property=ActiveState',name]).strip()==b'active','private_unit_not_active')
    require(command(['systemctl','show','--value','--property=User','resmgrcheck-web.service']).strip()==b'resmgr-web','web_not_nonroot_identity')
    pid=int(command(['systemctl','show','--value','--property=MainPID','resmgrcheck-web.service']).strip());require(pid>1,'web_pid_missing')
    identity=pwd.getpwnam('resmgr-web').pw_uid
    status=Path('/proc')/str(pid)/'status'
    uids=re.search(r'^Uid:\s+(.*)$',status.read_text(),re.M)
    require(uids and all(int(value)==identity for value in uids[1].split()),'web_process_uid_differs')
    process_env=dict(row.split(b'=',1) for row in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0') if b'=' in row)
    require(process_env.get(b'RMC_WEB_RUNNER_ENABLED',b'0')==b'0' and not process_env.get(b'RMC_WEB_AI_CONFIG',b''),'runner_or_ai_must_stay_disabled')
    invocation=command(['systemctl','show','--value','--property=InvocationID','resmgrcheck-web.service']).decode().strip()
    require(re.fullmatch('[0-9a-f]{32}',invocation),'current_invocation_missing')
    rows=command(['journalctl','--no-pager','-o','cat','_SYSTEMD_INVOCATION_ID='+invocation,'--grep=nonroot_process','-n','5'])
    values=[]
    for line in rows.splitlines():
        try:values.append(json.loads(line))
        except (ValueError,TypeError):continue
    required={'nonroot_process':True,'dedicated_os_identity':True,'nonprivileged_database_role':True,
        'forbidden_credentials_readable':False,'web_ip_socket_creation_denied':True,'evidence_write_matches_role':True,
        'owns_public_relations':False,'privileged_role_membership':False,'can_create_schema_objects':False,'home_tree_readable':False}
    require(any(all(row.get(k) is v for k,v in required.items()) for row in values),'current_runtime_check_unproven')
    socket_path=Path('/run/resmgrcheck-web/application.sock');info=socket_path.lstat()
    require(stat.S_ISSOCK(info.st_mode) and info.st_uid==identity and info.st_gid==grp.getgrnam('www-data').gr_gid and stat.S_IMODE(info.st_mode)==0o660,'private_socket_protection')
    return {'invocation_id':invocation,'nonroot_isolation':'passed','runner_enabled':False,'AI':'disabled'}

def certificate_and_renewal():
    lineage=LE/'live'/HOST;archive=LE/'archive'/HOST
    for name,pattern,private in [('fullchain.pem','fullchain[0-9]+[.]pem',False),('privkey.pem','privkey[0-9]+[.]pem',True)]:
        path=lineage/name;require(path.is_symlink() and path.lstat().st_uid==os.geteuid(),'certificate_link_untrusted')
        target=path.resolve();require(target.parent==archive and re.fullmatch(pattern,target.name),'certificate_link_outside_own_lineage')
        info=target.lstat();require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1 and not info.st_mode&0o022,'certificate_protection')
        if private:require(stat.S_IMODE(info.st_mode) in {0o400,0o600},'certificate_key_protection')
    certificate=lineage/'fullchain.pem';key=lineage/'privkey.pem'
    command(['openssl','x509','-in',certificate,'-noout','-checkend','604800'])
    command(['openssl','verify','-purpose','sslserver','-verify_hostname',HOST,'-CApath','/etc/ssl/certs','-untrusted',certificate,certificate])
    sans=command(['openssl','x509','-in',certificate,'-noout','-ext','subjectAltName']).decode()
    require(re.findall(r'DNS:([^,\s]+)',sans)==[HOST],'certificate_not_dedicated_to_host')
    public=command(['openssl','x509','-in',certificate,'-pubkey','-noout'])
    public=command(['openssl','pkey','-pubin','-outform','DER'],data=public)
    require(public==command(['openssl','pkey','-in',key,'-pubout','-outform','DER']),'certificate_key_mismatch')
    renewal=read(LE/'renewal'/(HOST+'.conf')).decode()
    require(re.search(r'^authenticator\s*=\s*webroot\s*$',renewal,re.M),'renewal_not_webroot')
    require(re.search(r'^webroot_path\s*=\s*/var/www/resmgrcheck-acme,?\s*$',renewal,re.M) or
        re.search(r'^'+re.escape(HOST)+r'\s*=\s*/var/www/resmgrcheck-acme\s*$',renewal,re.M),'renewal_webroot_differs')
    for value in [renewal,read(LE/'cli.ini').decode() if (LE/'cli.ini').exists() else '']:
        require(not re.search(r'^\s*(?:pre[-_]hook|post[-_]hook|deploy[-_]hook|renew[-_]hook)\s*=\s*\S',value,re.M),'configured_certbot_hooks_require_review')
    require(command(['systemctl','show','--value','--property=ActiveState','certbot.timer']).strip()==b'active','certbot_timer_inactive')
    require(b'--no-directory-hooks' not in command(['systemctl','show','--value','--property=ExecStart','certbot.service']),'certbot_timer_disables_deploy_hooks')
    return digest(certificate.read_bytes())

def acme_probe(client):
    directory(ACME);name='rmc-deploy-'+secrets.token_hex(16);path=ACME/name;raw=secrets.token_hex(24).encode()
    new_file(path,raw,0o644);before=metadata(path)
    try:
        status,_,body=client.request('/.well-known/acme-challenge/'+name,secure=False)
        require(status==200 and body==raw,'acme_http_challenge_failed')
    finally:
        require(metadata(path)==before and read(path)==raw,'acme_probe_changed');path.unlink();fsync_directory(path.parent)

def ensure_logs():
    directory(LOGS)
    result={}
    users={os.geteuid(),pwd.getpwnam('www-data').pw_uid}
    groups={os.getegid(),grp.getgrnam('adm').gr_gid,grp.getgrnam('www-data').gr_gid}
    for name in ['resmgrcheck-access.log','resmgrcheck-error.log']:
        path=LOGS/name
        if not path.exists():new_file(path,b'',0o640)
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            info=os.fstat(descriptor);mode=stat.S_IMODE(info.st_mode)
            require(stat.S_ISREG(info.st_mode) and info.st_uid in users and info.st_gid in groups and info.st_nlink==1 and
                mode in {0o600,0o640,0o644,0o660,0o664},'own_log_protection')
            try:acl=os.getxattr(descriptor,'system.posix_acl_access')
            except OSError as error:
                if error.errno not in {errno.ENODATA,errno.ENOTSUP,errno.EOPNOTSUPP}:raise
            else:
                # Never remove or reinterpret an unknown named-user/group ACL.
                require(len(acl)==28 and struct.unpack_from('<I',acl)[0]==2,'own_log_ACL_requires_review')
                entries=[struct.unpack_from('<HHI',acl,offset) for offset in [4,12,20]]
                require([row[0] for row in entries]==[1,4,32] and all(row[2]==0xffffffff and row[1]<=7 for row in entries),'own_log_ACL_requires_review')
            target=mode&0o640  # Reduction only: existing0600 never gains group read.
            if target!=mode:os.fchmod(descriptor,target)
            after=os.fstat(descriptor);current=path.lstat()
            require((current.st_dev,current.st_ino)==(info.st_dev,info.st_ino) and not stat.S_ISLNK(current.st_mode),'own_log_rotated_during_permission_check')
            require((after.st_uid,after.st_gid,after.st_nlink)==(info.st_uid,info.st_gid,1) and not after.st_mode&0o027,'own_log_protection')
            result[name]={'before_mode':format(mode,'04o'),'after_mode':format(stat.S_IMODE(after.st_mode),'04o'),
                'permissions_tightened':target!=mode,'contents_and_ownership_changed':False}
        finally:os.close(descriptor)
    return result


def recorded_candidate_hashes(driver,revision):
    site=git('show',driver+':web/ops/production/nginx-site.conf.example')
    require(('/var/lib/resmgrcheck/static/'+revision+'/').encode() in site,'previous_driver_application_differs')
    return {'site':digest(site),'http':digest(git('show',driver+':web/ops/production/nginx-http.conf.example')),
        'hook':digest(renewal_hook().encode())}

def resume_failed_driver(state,identity,targets,manifest):
    if state.get('driver_revision')==identity['driver_revision']:return state
    previous=state.get('driver_revision')
    require(state.get('kind')==identity['kind'] and state.get('application_revision')==identity['application_revision'] and
        previous in RECOVERABLE_DRIVERS and
        state.get('phase') in {'rolled_back_after_failure','rolled_back'},'another_https_deployment_recorded')
    git('merge-base','--is-ancestor',previous,identity['driver_revision'])
    require(state.get('after')==recorded_candidate_hashes(previous,identity['application_revision']),'previous_driver_candidate_hashes_differ')
    require(set(state.get('before',{}))=={name for name,_,_,_ in targets} and set(state.get('modes',{}))==set(state['before']),'deployment_record_shape_differs')
    for name,path,_,_ in targets:
        before=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
        require(before is None or digest(before)==state['before'][name],'backup_hash_differs')
        current=read(path) if path.exists() or path.is_symlink() else None
        require(current==before,'failed_driver_resources_not_rolled_back')
    require(read(STATE/'site.before',private=True)==(HERE/'nginx-bootstrap-site.conf').read_bytes() and
        read(STATE/'http.before',private=True)==(HERE/'nginx-bootstrap-http.conf').read_bytes(),'failed_driver_original_configuration_differs')
    history=STATE/('driver-'+previous+'.json')
    if history.exists():require(json.loads(read(history,private=True))==state,'driver_history_differs')
    else:new_file(history,(json.dumps(state,sort_keys=True,indent=2)+'\n').encode())
    updated={**state,**identity,'phase':'prepared_after_reviewed_driver_correction'}
    record(manifest,updated);return updated

def logging_probe(client):
    marker='rmc-confidential-probe-'+secrets.token_hex(12)
    paths=[LOGS/'resmgrcheck-access.log',LOGS/'resmgrcheck-error.log'];offsets=[p.stat().st_size for p in paths]
    status,_,_=client.request('/'+marker+'?credential='+marker);require(status==404,'confidential_probe_status')
    for path,offset in zip(paths,offsets):
        with path.open('rb') as stream:
            stream.seek(offset);raw=stream.read(65537)
        require(len(raw)<=65536 and marker.encode() not in raw,'confidential_request_leaked_in_own_logs')

@contextmanager
def locked():
    path=STATE/'lock';descriptor=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(descriptor);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600 and info.st_size==0,'deployment_lock_untrusted')
        fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
    finally:os.close(descriptor)

def restore(state,targets):
    for name,path,candidate,_ in targets:
        previous=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
        current=read(path) if path.exists() or path.is_symlink() else None
        require(current in {previous,candidate},'rollback_refuses_unknown_changes')
    for name,path,candidate,mode in reversed(targets):
        previous=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
        current=read(path) if path.exists() or path.is_symlink() else None
        require(current in {previous,candidate},'rollback_refuses_unknown_changes')
        if current==previous:continue
        if previous is None:
            require(read(path)==candidate,'rollback_resource_changed');path.unlink();fsync_directory(path.parent)
        else:replace_owned(path,previous,candidate,state['modes'][name])

def verify_original_http(state,targets,client):
    # Reload signals the master; old workers may briefly accept fresh connections.
    # First prove exact files/modes/link, then wait for the restored HTTP behavior.
    require(ENABLED.is_symlink() and ENABLED.lstat().st_uid==os.geteuid() and ENABLED.resolve()==SITE,'rollback_enabled_site_link_differs')
    for name,path,_,_ in targets:
        previous=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
        current=read(path) if path.exists() or path.is_symlink() else None
        require(current==previous and (previous is None or digest(previous)==state['before'][name]),'rollback_original_files_differ')
        if previous is not None:require(stat.S_IMODE(path.lstat().st_mode)==state['modes'][name],'rollback_original_mode_differs')
    observations=[];state['rollback_http_observations']=observations
    for attempt in range(6):
        try:
            status,headers,_=client.request('/',secure=False)
            observations.append({'status':status,'own_https_redirect':headers.get('location')=='https://'+HOST+'/'})
        except OSError:status=None;observations.append({'connection_failed':True})
        if status==404:
            require('location' not in headers,'rollback_original_http_redirects')
            acme_probe(client)
            return
        if attempt<5:time.sleep(1)
    raise CheckFailed('rollback_original_http_not_restored')

def verified_https_after_reload(client,static_hash,*,rate=True):
    for attempt in range(6):
        try:return checks(client,static_hash,rate=rate)
        except (OSError,CheckFailed):
            if attempt==5:raise
            time.sleep(1)

def apply(revision,driver,rollback=False,acceptance=True):
    global DIAGNOSTIC
    require_root();os.umask(0o027);source_check(revision,driver)
    for path in [NGINX,SITE.parent,HTTP.parent,ENABLED.parent,HOOK.parent,STATE.parent]:directory(path)
    require(ENABLED.is_symlink() and ENABLED.lstat().st_uid==os.geteuid() and ENABLED.resolve()==SITE,'enabled_site_link_differs')
    if not STATE.exists():STATE.mkdir(mode=0o700);STATE.chmod(0o700);fsync_directory(STATE.parent)
    directory(STATE,0o700);DIAGNOSTIC=STATE/'diagnostic.log'
    targets=[('site',SITE,site_config(revision).encode(),0o644),('http',HTTP,http_config().encode(),0o644),('hook',HOOK,renewal_hook().encode(),0o755)]
    identity={'kind':'resmgrcheck-https-deployment','application_revision':revision,'driver_revision':driver,
        'after':{name:digest(raw) for name,_,raw,_ in targets}}
    with locked():
        manifest=STATE/'state.json';existing=manifest.exists()
        if existing:
            state=json.loads(read(manifest,private=True))
            state=resume_failed_driver(state,identity,targets,manifest)
            require(all(state.get(k)==v for k,v in identity.items()),'another_https_deployment_recorded')
            for name in state['before']:
                if state['before'][name] is not None:require(digest(read(STATE/(name+'.before'),private=True))==state['before'][name],'backup_hash_differs')
        else:
            require(not rollback,'no_https_deployment_to_rollback')
            require(read(SITE)==(HERE/'nginx-bootstrap-site.conf').read_bytes(),'unknown_original_resmgrcheck_site')
            require(read(HTTP)==(HERE/'nginx-bootstrap-http.conf').read_bytes(),'unknown_original_resmgrcheck_http_settings')
            require(not HOOK.exists() and not HOOK.is_symlink(),'unknown_existing_renewal_hook')
            state={**identity,'before':{},'modes':{},'phase':'preparing'}
            for name,path,_,mode in targets:
                if path.exists():
                    raw=read(path);backup=STATE/(name+'.before')
                    if backup.exists():require(read(backup,private=True)==raw,'partial_backup_differs')
                    else:new_file(backup,raw)
                    state['before'][name]=digest(raw);state['modes'][name]=stat.S_IMODE(path.stat().st_mode)
                else:state['before'][name]=None;state['modes'][name]=mode
            record(manifest,state)
        unrelated=unrelated_snapshot()
        changed=any(path.exists() and read(path)==candidate for _,path,candidate,_ in targets)
        try:
            if rollback:
                restore(state,targets);require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
                command(['nginx','-t']);command(['systemctl','reload','nginx.service'])
                verify_original_http(state,targets,Client(address='127.0.0.1'))
                state['phase']='rolled_back';record(manifest,state)
                print(json.dumps({'operation':'rollback','passed':True,'scope':'own site/http settings/hook only','application_revision':revision,'other_nginx_files_unchanged':True}));return
            runtime=units_and_runtime(revision);certificate=certificate_and_renewal();log_permissions=ensure_logs()
            record(STATE/'log-permissions.json',log_permissions)
            client=Client(address='127.0.0.1');acme_probe(client)
            static=Path('/var/lib/resmgrcheck/static')/revision
            directory(static,0o755);directory(static/'control',0o755)
            css=static_asset(static/'control/app.css');javascript=static_asset(static/'control/app.js');static_hash=digest(css)
            # Baseline syntax must pass before any active configuration mutation.
            command(['nginx','-t']);require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
            for name,path,raw,mode in targets:
                before=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
                current=read(path) if path.exists() or path.is_symlink() else None
                require(current in {before,raw},'own_configuration_changed')
                if current!=raw:replace_owned(path,raw,current,mode);changed=True
            state['phase']='installed';record(manifest,state)
            require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed');command(['nginx','-t'])
            command(['systemctl','reload','nginx.service'])
            state['phase']='reloaded';record(manifest,state)
            results=verified_https_after_reload(client,static_hash)
            acme_probe(client);logging_probe(client)
            status,headers,body=client.request('/static/control/app.js')
            media_type=headers.get('content-type','').partition(';')[0].strip().lower()
            require(status==200 and media_type in {'application/javascript','text/javascript'} and digest(body)==digest(javascript),'static_javascript_identity_invalid')
            if state.get('renewal_verified_certificate')!=certificate:
                print(json.dumps({'step':'dedicated_certbot_webroot_dry_run','status':'running'}),flush=True)
                command(['certbot','renew','--cert-name',HOST,'--dry-run','--no-random-sleep-on-renew','--no-directory-hooks','--non-interactive'],timeout=180)
                state['renewal_verified_certificate']=certificate;record(manifest,state)
            if not state.get('rollback_verified'):
                # Exercise this deployment's own rollback before authenticated UAT.
                # The private app/DB/keys and all unrelated vhosts stay unchanged.
                restore(state,targets);require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
                command(['nginx','-t']);command(['systemctl','reload','nginx.service'])
                state['phase']='rollback_drill_restored_original';record(manifest,state)
                try:verify_original_http(state,targets,client)
                finally:
                    state['rollback_drill_http_observations']=list(state.get('rollback_http_observations',[]));record(manifest,state)
                for name,path,raw,mode in targets:
                    before=read(STATE/(name+'.before'),private=True) if state['before'][name] is not None else None
                    replace_owned(path,raw,before,mode)
                command(['nginx','-t']);command(['systemctl','reload','nginx.service'])
                verified_https_after_reload(client,static_hash,rate=False)
                state['rollback_verified']=True;record(manifest,state)
            require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
            report={'application_revision':revision,'driver_revision':driver,'origin':'https://'+HOST,'local_verified_https':'passed',
                'independent_external_https':'pending','checks':results,'current_runtime':runtime,'acme_webroot_dry_run':'passed',
                'renewal_deploy_hook_installed':True,'actual_renewal_hook_event':'not_run','other_nginx_files_unchanged':True,
                'own_log_permissions':log_permissions,
                'public_acceptance':'pending','customer_host_qualification':'blocked; no separate host','AI':'disabled','off_server_DR':'deferred',
                'rollback':'own HTTPS configuration restored and reactivated; private release/database unchanged',
                'rollback_drill_http_observations':state.get('rollback_drill_http_observations',[])}
            state['phase']='verified';record(manifest,state);record(STATE/'report.json',report)
            print(json.dumps({'deployment':'passed','application_revision':revision,'driver_revision':driver,'origin':report['origin'],
                'protected_report':str(STATE/'report.json'),'external_and_authenticated_acceptance':'pending'}),flush=True)
            if acceptance:
                print(json.dumps({'step':'authenticated_browser_acceptance','status':'running','maximum_seconds':1500}),flush=True)
                acceptance_result=command([str(OPT/'current/.venv/bin/python'),'-I',HERE/'acceptance_operator.py','--release',revision,'--driver-revision',driver,
                    '--state',str(STATE)],timeout=1800,progress='authenticated_browser_acceptance')
                value=json.loads(acceptance_result);report['authenticated_acceptance']=value
                report['public_acceptance']='passed' if value.get('overall_acceptance')=='passed' else 'in_progress'
                record(STATE/'report.json',report);print(json.dumps(value),flush=True)
        except BaseException as failure:
            error=str(failure) if isinstance(failure,CheckFailed) else type(failure).__name__
            state['failure']=error;record(manifest,state)
            # Never roll back another operator's changes, even when our probes fail.
            try:
                restore(state,targets)
                require(unrelated_snapshot()==unrelated,'unrelated_configuration_changed_during_rollback')
                if changed:command(['nginx','-t']);command(['systemctl','reload','nginx.service'])
                verify_original_http(state,targets,Client(address='127.0.0.1'))
                state['phase']='rolled_back_after_failure';record(manifest,state)
            except BaseException:
                state['phase']='rollback_requires_operator_review';record(manifest,state)
                raise CheckFailed('deployment_failed_and_safe_rollback_could_not_complete') from None
            print(json.dumps({'deployment':'failed','failed_check':error,'own_changes_rolled_back':True,'protected_state':str(manifest),
                'rollback_drill_http_observations':state.get('rollback_drill_http_observations',[]),
                'final_rollback_http_observations':state.get('rollback_http_observations',[])}),flush=True)
            raise CheckFailed('deployment_failed_own_configuration_rolled_back') from None

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--release',required=True);parser.add_argument('--driver-revision',required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');parser.add_argument('--skip-authenticated-acceptance',action='store_true')
    args=parser.parse_args()
    def interrupted(signum,frame):raise CheckFailed('operator_deployment_interrupted')
    if args.apply:signal.signal(signal.SIGTERM,interrupted)
    try:
        if args.apply:apply(args.release,args.driver_revision,args.rollback,not args.skip_authenticated_acceptance)
        else:
            source_check(args.release,args.driver_revision)
            print(json.dumps({'mode':'read-only plan','origin':'https://'+HOST,'application_revision':args.release,'driver_revision':args.driver_revision,
                'files':[str(SITE),str(HTTP),str(HOOK)],'root_required':True,'nginx_reload_after_syntax_validation':True,
                'modifies_existing_data_keys_releases_or_other_sites':False,'acceptance_appends_own_audited_records':not args.skip_authenticated_acceptance,
                'bounded_local_tls_acme_and_security_checks':True,
                'authenticated_acceptance_uses_new_temporary_local_identity':not args.skip_authenticated_acceptance,'independent_external_verification':'agent after deployment'}))
    except (CheckFailed,OSError,ValueError,subprocess.SubprocessError) as error:
        code=str(error) if isinstance(error,CheckFailed) else type(error).__name__
        print(json.dumps({'passed':False,'failed_check':code,'error':'deployment_withheld_or_failed; protected local report retained','secrets_printed':False}),flush=True)
        raise SystemExit(1) from None

if __name__=='__main__':main()
