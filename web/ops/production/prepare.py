#!/usr/bin/env python3
"""Prepare only dedicated PRIVATE production resources; never touches Nginx/DNS/TLS.

Default is a read-only plan. --apply requires root and an explicit committed SHA.
This is not a public deployment command or a release-acceptance claim.
"""
import argparse,grp,json,os,pwd,re,secrets,shlex,shutil,stat,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent;SOURCE=HERE.parents[2]
BASE=Path('/var/lib/resmgrcheck');CONFIG=Path('/etc/resmgrcheck');OPT=Path('/opt/resmgrcheck')
BACKUP=Path('/var/backups/resmgrcheck');UNIT_ROOT=Path('/etc/systemd/system');RUNTIME=[Path('/run/resmgrcheck-db'),Path('/run/resmgrcheck-web')]
USERS=['resmgr-web','resmgr-exec','resmgr-ai','resmgr-db'];GROUPS=['resmgr-evidence','resmgr-dbclients']
ENGINE='ca4f74e0fcff33b6f6ebf6c553b3f8379f6440e0'
UNITS=['resmgrcheck-db.service','resmgrcheck-web.socket','resmgrcheck-web.service','resmgrcheck-executor.service','resmgrcheck-ai.service','resmgrcheck-backup.service','resmgrcheck-backup.timer','resmgrcheck-status.service','resmgrcheck-status.timer']
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}

def run(argv,*,input=None,user=None,env=None):
    if user:argv=['/usr/sbin/runuser','-u',user,'--',*argv]
    result=subprocess.run(argv,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**ENV,**(env or {})},cwd='/',timeout=240)
    if result.returncode:
        # Persist diagnostics locally without dumping protected configuration to chat.
        if os.geteuid()==0 and CONFIG.is_dir():
            fd=os.open(CONFIG/'prepare-error.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'ab') as stream:stream.write(result.stderr[:16000]+b'\n')
        raise RuntimeError('Private preparation command failed: '+Path(argv[-1] if user else argv[0]).name+'; inspect protected local diagnostics')
    return result.stdout

def directory(path,mode=0o755,user='root',group='root'):
    path=Path(path)
    uid=pwd.getpwnam(user).pw_uid;gid=grp.getgrnam(group).gr_gid
    if any(parent.is_symlink() for parent in [path,*path.parents]):raise RuntimeError('Refusing a symlink directory')
    if path.exists():
        check_directory(path,mode,uid,gid)
        return
    path.mkdir();os.chown(path,uid,gid);path.chmod(mode)

def check_directory(path,mode,uid,gid):
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=uid or info.st_gid!=gid or stat.S_IMODE(info.st_mode)!=mode:
        raise RuntimeError('Existing directory protection mismatch: '+str(path))

def check_private_file(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or stat.S_IMODE(info.st_mode)!=0o600:
        raise RuntimeError('Preparation record protection mismatch: '+path.name)

def protected_json(path):
    check_private_file(path)
    return json.loads(path.read_text())

def write(path,raw,mode=0o600,user='root',group='root'):
    path=Path(path);raw=raw.encode() if isinstance(raw,str) else raw
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.stat().st_uid!=pwd.getpwnam(user).pw_uid or path.read_bytes()!=raw:raise RuntimeError('Refusing to overwrite existing configuration: '+path.name)
        return
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(descriptor,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.chown(path,pwd.getpwnam(user).pw_uid,grp.getgrnam(group).gr_gid)

def clone(destination,revision):
    receipt=destination.parent/('.'+destination.name+'.clone.json')
    identity={'kind':'resmgrcheck-private-clone','source':str(SOURCE),'destination':str(destination),'revision':revision}
    if destination.is_symlink():raise RuntimeError('Refusing a symlink release/engine root')
    if receipt.exists() or receipt.is_symlink():
        if protected_json(receipt)!=identity:raise RuntimeError('Clone receipt mismatch')
    elif destination.exists():raise RuntimeError('Occupied clone has no completion receipt; preserve for local inspection')
    if destination.exists():
        check_directory(destination,0o755,os.geteuid(),os.getegid())
        if (destination/'.git').is_symlink() or not (destination/'.git').is_dir():raise RuntimeError('Occupied clone metadata mismatch')
        actual=run(['git','-c','safe.directory='+str(destination),'-C',str(destination),'rev-parse','HEAD']).decode().strip()
        if actual!=revision:raise RuntimeError('Occupied release has another revision')
        origin=run(['git','-c','safe.directory='+str(destination),'-C',str(destination),'remote','get-url','origin']).decode().strip()
        if origin!=str(SOURCE):raise RuntimeError('Occupied clone has another source')
        changes=run(['git','-c','safe.directory='+str(destination),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(destination),'status','--porcelain','--untracked-files=no'])
        if changes:raise RuntimeError('Occupied clone has tracked changes')
        return
    if receipt.exists():raise RuntimeError('Completed clone is missing; preserve its receipt for inspection')
    # Git's local clone ownership check and upload-pack are separate processes.
    # -c on clone does not grant upload-pack trust. Force the transport route and
    # scope the exception to its exact source metadata path, in that command only.
    upload=shlex.join(['git','-c','safe.directory=','-c','safe.directory='+str(SOURCE/'.git'),'-c','core.hooksPath=/dev/null','upload-pack'])
    run(['git','-c','safe.directory=','-c','safe.directory='+str(SOURCE),'-c','core.hooksPath=/dev/null','clone','--no-local','--no-checkout','--upload-pack='+upload,str(SOURCE),str(destination)])
    run(['git','-c','safe.directory='+str(destination),'-c','core.hooksPath=/dev/null','-C',str(destination),'checkout','--detach',revision])
    destination.chmod(0o755)
    write(receipt,json.dumps(identity,sort_keys=True)+'\n')

def check_early_resume(revision):
    """Validate the known pre-clone layout before touching partially created resources.

    Later failures keep their own immutable clone/configuration checks. Unknown or
    interrupted clone trees are never removed or adopted automatically.
    """
    if any(p.exists() or p.is_symlink() for p in [OPT/'releases'/revision,OPT/'engine']):return
    layout={BASE:(0o755,'root','root',{'PROVISIONED.json','private','evidence','engine-state'}),
        CONFIG:(0o755,'root','root',{'keys','executor','ai','prepare-error.log'}),
        OPT:(0o755,'root','root',{'releases'}),OPT/'releases':(0o755,'root','root',set()),
        BASE/'private':(0o755,'root','root',{'web','executor','ai','operator','backup'}),
        BASE/'evidence':(0o2750,'resmgr-exec','resmgr-evidence',set()),
        BASE/'engine-state':(0o700,'resmgr-exec','resmgr-exec',set()),
        CONFIG/'keys':(0o700,'root','root',set()),CONFIG/'executor':(0o700,'resmgr-exec','resmgr-exec',set()),
        CONFIG/'ai':(0o700,'resmgr-ai','resmgr-ai',set()),BACKUP:(0o700,'root','root',set())}
    for role,user in [('web','resmgr-web'),('executor','resmgr-exec'),('ai','resmgr-ai'),('operator','root'),('backup','root')]:
        layout[BASE/'private'/role]=(0o700,user,user,set())
    for path,(mode,user,group,allowed) in layout.items():
        if path.exists() or path.is_symlink():
            check_directory(path,mode,pwd.getpwnam(user).pw_uid,grp.getgrnam(group).gr_gid)
            if any(child.name not in allowed for child in path.iterdir()):raise RuntimeError('Unknown resource in partial preparation: '+str(path))
    diagnostic=CONFIG/'prepare-error.log'
    if diagnostic.exists() or diagnostic.is_symlink():check_private_file(diagnostic)
    for path in RUNTIME+[UNIT_ROOT/name for name in UNITS]:
        if path.exists() or path.is_symlink():raise RuntimeError('Unexpected pre-clone resource: '+str(path))

def public_code_permissions(root):
    # These trees contain only public Git source/hash-pinned Python packages/static
    # assets. Never follow links into private state or chmod credential/data trees.
    for base,folders,files in os.walk(root,followlinks=False):
        Path(base).chmod(0o755)
        for name in files:
            path=Path(base)/name
            if not path.is_symlink():path.chmod(0o755 if path.stat().st_mode&0o111 else 0o644)

def configurations(revision):
    common={'RMC_WEB_ENV':'production','RMC_WEB_DB_HOST':'/run/resmgrcheck-db','RMC_WEB_DB_PORT':'5448','RMC_WEB_DB_NAME':'resmgrcheck_web',
        'RMC_WEB_ALLOWED_HOSTS':'qnx-resmgrcheck.gestionatech.de','RMC_WEB_CSRF_ORIGINS':'https://qnx-resmgrcheck.gestionatech.de',
        'RMC_WEB_STATIC_ROOT':str(BASE/'static'/revision),'RMC_WEB_ARTIFACT_ROOT':str(BASE/'evidence'),'RMC_WEB_ENGINE_ROOT':str(OPT/'engine')}
    for role,dbuser in [('web','resmgr_web'),('executor','resmgr_exec'),('ai','resmgr_ai'),('operator','resmgr_owner'),('backup','resmgr_backup')]:
        data={**common,'RMC_WEB_ROLE':role,'RMC_WEB_DB_USER':dbuser,'RMC_WEB_PRIVATE_ROOT':str(BASE/'private'/role)}
        if role=='executor':data['RMC_WEB_EXECUTOR_REGISTRY']='/etc/resmgrcheck/executor/registry.json'
        if role=='ai':data['RMC_WEB_AI_CONFIG']='/etc/resmgrcheck/ai/provider.json'
        if role=='operator':data.update(RMC_WEB_SECRET_KEY_FILE='/etc/resmgrcheck/keys/application-key',RMC_WEB_MFA_KEY_FILE='/etc/resmgrcheck/keys/mfa-key')
        if role=='backup':data['RMC_WEB_SECRET_KEY_FILE']='/etc/resmgrcheck/keys/application-key'
        write(CONFIG/(role+'.json'),json.dumps(data,sort_keys=True,indent=2)+'\n')
        if role not in {'operator','backup'}:write(CONFIG/(role+'.env'),'\n'.join(k+'='+v for k,v in data.items())+'\n')

def prepare(revision):
    if os.geteuid()!=0:raise SystemExit('--apply requires the local root operator; no credentials should be sent in chat')
    available=int(re.search(r'^MemAvailable:\s+([0-9]+)',Path('/proc/meminfo').read_text(),re.M)[1])*1024
    if available<1024**3 or shutil.disk_usage('/').free<2*1024**3:raise RuntimeError('Insufficient spare memory/disk; preserve existing services')
    marker=BASE/'PROVISIONED.json'
    existing_marker=marker.exists() or marker.is_symlink()
    if existing_marker:
        data=protected_json(marker)
        if data.get('kind')!='resmgrcheck-private-preparation' or data.get('revision')!=revision:raise RuntimeError('Existing preparation differs; use a separately reviewed upgrade/rollback procedure')
        check_early_resume(revision)
    else:
        for path in [BASE,CONFIG,OPT,BACKUP,*RUNTIME]+[UNIT_ROOT/name for name in UNITS]:
            if path.exists() or path.is_symlink():raise RuntimeError('Dedicated resource is already occupied: '+str(path))
        for name in USERS:
            try:pwd.getpwnam(name)
            except KeyError:pass
            else:raise RuntimeError('An existing account must not be adopted: '+name)
        for name in USERS+GROUPS:
            try:grp.getgrnam(name)
            except KeyError:pass
            else:raise RuntimeError('An existing group must not be adopted: '+name)
        directory(BASE);directory(CONFIG,0o755);directory(OPT)
        write(marker,json.dumps({'kind':'resmgrcheck-private-preparation','revision':revision})+'\n')
    for group in GROUPS:
        try:grp.getgrnam(group)
        except KeyError:run(['groupadd','--system',group])
    for name in USERS:
        try:account=pwd.getpwnam(name)
        except KeyError:
            run(['useradd','--system','--user-group','--no-create-home','--home-dir','/nonexistent','--shell','/usr/sbin/nologin',name]);account=pwd.getpwnam(name)
        if account.pw_dir!='/nonexistent' or account.pw_shell!='/usr/sbin/nologin':raise RuntimeError('Unexpected dedicated account properties')
        if name!='resmgr-db':run(['usermod','-a','-G','resmgr-dbclients,resmgr-evidence',name])
    directory(CONFIG/'keys',0o700);directory(CONFIG/'executor',0o700,'resmgr-exec','resmgr-exec');directory(CONFIG/'ai',0o700,'resmgr-ai','resmgr-ai')
    directory(BASE/'private')
    for role,user in [('web','resmgr-web'),('executor','resmgr-exec'),('ai','resmgr-ai'),('operator','root'),('backup','root')]:directory(BASE/'private'/role,0o700,user,user)
    directory(BASE/'evidence',0o2750,'resmgr-exec','resmgr-evidence');directory(BASE/'engine-state',0o700,'resmgr-exec','resmgr-exec')
    directory(BACKUP,0o700);directory(OPT/'releases')
    application=OPT/'releases'/revision;clone(application,revision);clone(OPT/'engine',ENGINE)
    local=OPT/'engine/.local';directory(local)
    state=local/'state'
    if not state.is_symlink() and not state.exists():state.symlink_to(BASE/'engine-state')
    if not state.is_symlink() or state.resolve()!=BASE/'engine-state':raise RuntimeError('Engine state location mismatch')
    venv=application/'.venv'
    if not (venv/'bin/python').exists():run(['/usr/bin/python3','-m','venv',str(venv)])
    run([str(venv/'bin/python'),'-m','pip','install','--require-hashes','--only-binary=:all:','--index-url','https://pypi.org/simple','--no-cache-dir','--disable-pip-version-check','-r',str(application/'web/requirements.lock')],env={'PIP_CONFIG_FILE':'/dev/null'})
    public_code_permissions(application);public_code_permissions(OPT/'engine')
    for filename,raw in [('application-key',secrets.token_urlsafe(64).encode()),('mfa-key',__import__('base64').urlsafe_b64encode(os.urandom(32))),('backup-key',os.urandom(32))]:
        key=CONFIG/'keys'/filename
        if not key.exists():write(key,raw)
        elif key.is_symlink() or key.stat().st_uid!=0 or key.stat().st_mode&0o077:raise RuntimeError('Existing private key protection mismatch')
    for name in UNITS:write(UNIT_ROOT/name,(application/'web/ops/production'/name).read_bytes(),0o644)
    directory(BASE/'database',0o700,'resmgr-db','resmgr-dbclients')
    pgdata=BASE/'database'
    if not (pgdata/'PG_VERSION').exists():
        run(['/usr/lib/postgresql/16/bin/initdb','-D',str(pgdata),'-U','resmgr_pg','--auth-local=peer','--auth-host=reject','--no-locale','--encoding=UTF8'],user='resmgr-db')
        # initdb's defaults are preserved, with a dedicated final include.
        with (pgdata/'postgresql.conf').open('a') as stream:stream.write("\ninclude='resmgrcheck.conf'\n")
    write(pgdata/'resmgrcheck.conf',"listen_addresses=''\nport=5448\nunix_socket_directories='/run/resmgrcheck-db'\nunix_socket_group='resmgr-dbclients'\nunix_socket_permissions=0770\nmax_connections=40\nshared_buffers='32MB'\nwork_mem='2MB'\nstatement_timeout='10s'\nlock_timeout='5s'\nlog_min_error_statement=panic\nlog_error_verbosity=terse\nlog_parameter_max_length_on_error=0\n",user='resmgr-db',group='resmgr-dbclients')
    # Dedicated fresh cluster only. Never edit any host-wide PostgreSQL service.
    hba="local all resmgr_pg peer map=resmgrcheck\nlocal all resmgr_owner peer map=resmgrcheck\nlocal resmgrcheck_web resmgr_web peer map=resmgrcheck\nlocal resmgrcheck_web resmgr_exec peer map=resmgrcheck\nlocal resmgrcheck_web resmgr_ai peer map=resmgrcheck\nlocal resmgrcheck_web resmgr_backup peer map=resmgrcheck\nlocal all all reject\n"
    mapping='resmgrcheck resmgr-db resmgr_pg\nresmgrcheck root resmgr_owner\nresmgrcheck root resmgr_backup\nresmgrcheck resmgr-web resmgr_web\nresmgrcheck resmgr-exec resmgr_exec\nresmgrcheck resmgr-ai resmgr_ai\n'
    # initdb creates these two files; replace only within the marked new private cluster.
    for name,value in [('pg_hba.conf',hba),('pg_ident.conf',mapping)]:
        path=pgdata/name
        if path.is_symlink() or path.stat().st_uid!=pwd.getpwnam('resmgr-db').pw_uid:raise RuntimeError('Private cluster configuration ownership mismatch')
        path.write_text(value);path.chmod(0o600)
    run(['systemctl','daemon-reload']);run(['systemctl','start','resmgrcheck-db.service'])
    pg_env={'PGHOST':'/run/resmgrcheck-db','PGPORT':'5448','PGUSER':'resmgr_pg'}
    for attempt in range(30):
        check=subprocess.run(['runuser','-u','resmgr-db','--','/usr/lib/postgresql/16/bin/pg_isready','-h','/run/resmgrcheck-db','-p','5448'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=ENV)
        if check.returncode==0:break
        time.sleep(1)
    else:raise RuntimeError('Private database did not become ready')
    exists=run(['psql','-X','-w','-A','-t','-d','postgres','-c',"SELECT 1 FROM pg_database WHERE datname='resmgrcheck_web'"],user='resmgr-db',env=pg_env).strip()
    if not exists:
        sql='CREATE ROLE resmgr_owner LOGIN NOSUPERUSER CREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;\n'
        for role in ['resmgr_web','resmgr_exec','resmgr_ai','resmgr_backup']:sql+='CREATE ROLE '+role+' LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12;\n'
        sql+='CREATE DATABASE resmgrcheck_web OWNER resmgr_owner TEMPLATE template0 ENCODING UTF8;\n'
        run(['psql','-X','-w','-v','ON_ERROR_STOP=1','-d','postgres'],input=sql.encode(),user='resmgr-db',env=pg_env)
    configurations(revision)
    directory(BASE/'static')
    runtime=[str(venv/'bin/python'),str(application/'web/ops/production/runtime.py'),'--config',str(CONFIG/'operator.json'),'manage.py']
    run(runtime+['migrate','--noinput']);run(runtime+['createcachetable']);run(runtime+['collectstatic','--noinput']);run(runtime+['production_check'])
    public_code_permissions(BASE/'static'/revision)
    run(['psql','-X','-w','-v','ON_ERROR_STOP=1','-U','resmgr_owner','-d','resmgrcheck_web','-f',str(application/'web/ops/production/database-grants.sql')],env=pg_env)
    current=OPT/'current'
    if current.is_symlink():
        if current.resolve()!=application:raise RuntimeError('Refusing to switch an existing release automatically')
    elif current.exists():raise RuntimeError('Current release path is occupied')
    else:current.symlink_to(application)
    run(['systemctl','start','resmgrcheck-web.socket','resmgrcheck-web.service'])
    print(json.dumps({'private_preparation_completed':True,'revision':revision,'public_deployment':False,'nginx_dns_firewall_changed':False,'qnx_credentials_created':False,'executor_started':False,'ai_started':False,'next':'Protected administrator provisioning, isolation checks, target approval, backup/restore/rollback, independent UAT. Public exposure remains gated.'}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True);parser.add_argument('--apply',action='store_true');options=parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}',options.revision):parser.error('revision must be an exact committed SHA')
    if not options.apply:
        print(json.dumps({'mode':'read-only plan','revision':options.revision,'new_users':USERS,'new_groups':GROUPS,'new_units':UNITS,'new_paths':[str(p) for p in [BASE,CONFIG,OPT,Path('/var/backups/resmgrcheck')]],'public_exposure':False,'root_required_to_apply':True}));return
    if run(['git','-c','safe.directory='+str(SOURCE),'-C',str(SOURCE),'rev-parse',options.revision+'^{commit}']).decode().strip()!=options.revision:raise SystemExit('Commit unavailable')
    os.umask(0o077);prepare(options.revision)

if __name__=='__main__':main()
