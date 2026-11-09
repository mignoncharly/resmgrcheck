#!/usr/bin/env python3
"""Read-only, metadata-only inspection of this deployment. Never prints logs/configs."""
import hashlib,http.client,json,os,re,socket,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as deployment

def inspect():
    deployment.require_root()
    state=json.loads(deployment.read(deployment.STATE/'state.json',private=True))
    result={'read_only':True,'secrets_printed':False,'state':{}}
    active=deployment.OPT/'current';revision=active.resolve().name if active.is_symlink() else ''
    result['active_application_revision']=revision if re.fullmatch('[0-9a-f]{40}',revision) else None
    for key in ['driver_revision','application_revision','phase','failure']:
        value=state.get(key)
        result['state'][key]=value if isinstance(value,str) and re.fullmatch('[a-z0-9_]{1,100}',value) else None
    result['state']['renewal_completed_and_recorded']=bool(state.get('renewal_verified_certificate'))
    result['state']['rollback_verified']=bool(state.get('rollback_verified'))
    result['files']={}
    for name,path in [('site',deployment.SITE),('http',deployment.HTTP),('hook',deployment.HOOK)]:
        expected=state['before'][name]
        exists=path.exists() or path.is_symlink()
        raw=deployment.read(path) if exists else None
        backup=deployment.read(deployment.STATE/(name+'.before'),private=True) if expected is not None else None
        info=path.lstat() if exists else None
        result['files'][name]={'present':exists,'matches_original_backup':raw==backup,
            'backup_hash_matches_record':expected is None or deployment.digest(backup)==expected,
            'uid':info.st_uid if info else None,'gid':info.st_gid if info else None,'mode':oct(info.st_mode&0o7777) if info else None}
        if name in {'site','http'}:
            bootstrap=deployment.HERE/('nginx-bootstrap-'+('site.conf' if name=='site' else 'http.conf'))
            result['files'][name]['matches_committed_bootstrap']=raw==bootstrap.read_bytes()
    result['enabled_symlink_correct']=deployment.ENABLED.is_symlink() and deployment.ENABLED.resolve()==deployment.SITE and deployment.ENABLED.lstat().st_uid==0
    result['certificate_links']={}
    for name in ['fullchain.pem','privkey.pem']:
        path=deployment.LE/'live'/deployment.HOST/name
        result['certificate_links'][name]={'symlink':path.is_symlink(),'trusted_archive_target':path.is_symlink() and path.resolve().parent==deployment.LE/'archive'/deployment.HOST,
            'root_owned':path.lstat().st_uid==0 and path.stat().st_uid==0,'target_mode':oct(path.stat().st_mode&0o777)}
    diagnostic=deployment.STATE/'diagnostic.log';result['diagnostic']={'present':diagnostic.exists()}
    if diagnostic.exists():
        # Prior failed-command output may contain private paths. Only report metadata.
        raw=deployment.read(diagnostic,private=True)
        result['diagnostic']={'present':True,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'certbot_error_marker_present':any(marker in raw.lower() for marker in [b'failed to renew',b'challenge failed',b'some challenges have failed'])}
    # Only the dedicated structured confidential format is eligible for output.
    # No request IDs, addresses, URLs, body, cookies or raw error text are returned.
    access=deployment.LOGS/'resmgrcheck-access.log'
    descriptor=os.open(access,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(descriptor)
        import stat
        deployment.require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and stat.S_IMODE(info.st_mode) in {0o600,0o640},'own_log_protection')
        os.lseek(descriptor,max(0,info.st_size-65536),os.SEEK_SET);tail=os.read(descriptor,65536).decode(errors='replace')
        rows=[]
        for line in tail.splitlines():
            match=re.fullmatch(r'[0-9a-f]{32} (GET|POST|HEAD) (public|administrator|access|application|api|runner-disabled|playback) ([1-5][0-9]{2}) [0-9.]+',line)
            if match:rows.append({'method':match[1],'area':match[2],'status':int(match[3])})
        result['recent_own_request_statuses']=rows[-64:]
    finally:os.close(descriptor)
    intents=sorted(deployment.STATE.glob('acceptance-*.intent.json'),key=lambda p:p.stat().st_mtime_ns)
    if intents:
        cleanup=intents[-1].with_name(intents[-1].name.replace('.intent.json','.cleanup.json'))
        result['latest_acceptance_cleanup']={'receipt_present':cleanup.exists()}
        if cleanup.exists():
            closed=json.loads(deployment.read(cleanup,private=True))
            result['latest_acceptance_cleanup'].update({k:closed.get(k) for k in ['temporary_account_disabled','temporary_codes_revoked','existing_users_changed','audit_runs_evidence_preserved','own_native_work_still_active']})
    checked=subprocess.run(['/usr/sbin/nginx','-T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,env=deployment.ENV)
    result['nginx_configuration_test_passed']=checked.returncode==0
    result['nginx_disk_configuration_includes_own_files']=all(('# configuration file '+str(p)+':').encode() in checked.stdout for p in [deployment.ENABLED,deployment.HTTP])
    for unit in ['nginx.service','resmgrcheck-web.service','resmgrcheck-web.socket']:
        status=subprocess.run(['systemctl','is-active',unit],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,env=deployment.ENV)
        result[unit+'_active']=status.returncode==0 and status.stdout.strip()==b'active'
    client=deployment.Client(address='127.0.0.1')
    status,headers,_=client.request('/',secure=False)
    result['current_HTTP']={'status':status,'redirects_to_own_HTTPS':headers.get('location')=='https://'+deployment.HOST+'/'}
    try:
        status,_,body=client.request('/readyz/')
        result['current_HTTPS']={'certificate_verified':True,'readiness_status':status,'ready':json.loads(body)=={'status':'ready'}}
    except (OSError,ValueError):result['current_HTTPS']={'certificate_verified':False}
    connection=http.client.HTTPConnection('localhost',timeout=4)
    stream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);stream.settimeout(4)
    try:
        stream.connect('/run/resmgrcheck-web/application.sock');connection.sock=stream
        connection.request('GET','/readyz/',headers={'Host':deployment.HOST,'X-Forwarded-Proto':'https'})
        response=connection.getresponse();body=response.read(1024)
        result['private_readiness']={'status':response.status,'ready':json.loads(body)=={'status':'ready'}}
    finally:connection.close();stream.close()
    return result

if __name__=='__main__':
    try:print(json.dumps(inspect(),sort_keys=True))
    except Exception as error:
        print(json.dumps({'read_only':True,'inspection_failed':type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
