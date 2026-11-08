#!/usr/bin/env python3
"""Operator-only immutable credential-fix release activation; default is a plan.

No key contents, DB connection, migrations, dependency installation, unit writes,
service starts/reloads, engine/QNX or network access. This is not a general upgrade.
Interrupted staging attempts are retained; retry stages a fresh private attempt.
"""
import argparse,ctypes,fcntl,json,os,re,secrets,shutil,stat
from contextlib import contextmanager
from pathlib import Path
import prepare

INSTALLED_REVISION='4ed4855f7633176baea06f2be53154630a9d4d1f'
RUNTIME_CHANGES={'web/resmgr_web/settings.py','web/resmgr_web/credentials.py',
    'web/ops/production/recover_credentials.py','web/ops/production/prepare.py',
    'web/ops/production/credential_diagnostic.py'}
QUIET_UNITS=['resmgrcheck-'+name for name in ['web.service','web.socket','executor.service',
    'ai.service','backup.service','backup.timer','status.service','status.timer']]
DROP_ROOTS=[Path('/etc/systemd/system/resmgrcheck-web.service.d'),Path('/run/systemd/system/resmgrcheck-web.service.d')]
DIAGNOSTIC=Path('/run/resmgrcheck-credential-diagnostic.py')
MANIFEST='.credential-release.json'


def require_root():
    if os.geteuid()!=0:raise SystemExit('--apply requires the local root operator')


def git(root,*args):
    return prepare.run(['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(root),
        '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(root),*args])


def check_scope(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision) or revision==INSTALLED_REVISION:
        raise RuntimeError('Expected exact credential-correction commit')
    if git(prepare.SOURCE,'rev-parse',revision+'^{commit}').decode().strip()!=revision:
        raise RuntimeError('Correction commit unavailable')
    git(prepare.SOURCE,'merge-base','--is-ancestor',INSTALLED_REVISION,revision)
    changed=git(prepare.SOURCE,'diff','--name-only','-z',INSTALLED_REVISION,revision).decode().split('\0')
    if any(p and p not in RUNTIME_CHANGES and not p.startswith(('docs/web/','web/tests/')) for p in changed):
        raise RuntimeError('Release contains changes outside credential recovery')
    for required in ['web/resmgr_web/credentials.py','web/ops/production/recover_credentials.py']:
        git(prepare.SOURCE,'cat-file','-e',revision+':'+required)


def check_quiet():
    for unit in QUIET_UNITS:
        state=prepare.run(['systemctl','show','--value','--property=ActiveState',unit]).decode().strip()
        if state not in {'inactive','failed'}:
            raise RuntimeError('Dedicated unit must be inactive for this initial-install recovery: '+unit)
    if prepare.run(['systemctl','show','--value','--property=DropInPaths','resmgrcheck-web.service']).strip():
        raise RuntimeError('Web overrides must be removed/reviewed first')
    for path in DROP_ROOTS:
        if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
            raise RuntimeError('Unknown web override path')
        if path.exists() and (path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o022):
            raise RuntimeError('Untrusted web override directory')
    if DIAGNOSTIC.exists() or DIAGNOSTIC.is_symlink():raise RuntimeError('Temporary diagnostic has not been removed')


def identity(revision):
    return {'kind':'resmgrcheck-credential-release','from_revision':INSTALLED_REVISION,
        'revision':revision,'source':str(prepare.SOURCE),
        'venv':str(prepare.OPT/'releases'/INSTALLED_REVISION/'.venv')}


def owned_directory(path,mode=0o755):
    if any(p.is_symlink() for p in [path,*path.parents]):raise RuntimeError('Unexpected release directory symlink')
    prepare.check_directory(path,mode,os.geteuid(),os.getegid())


def check_venv(path,expected):
    if not path.is_symlink() or path.lstat().st_uid!=os.geteuid() or os.readlink(path)!=str(expected):
        raise RuntimeError('Correction virtualenv is not the exact original immutable virtualenv')


def check_clean(path,revision,allowed):
    if (path/'.git').is_symlink() or not (path/'.git').is_dir():raise RuntimeError('Unexpected release Git metadata')
    if git(path,'rev-parse','HEAD').decode().strip()!=revision:raise RuntimeError('Release revision differs')
    if git(path,'remote','get-url','origin').decode().strip()!=str(prepare.SOURCE):raise RuntimeError('Release source differs')
    if git(path,'status','--porcelain','--untracked-files=no').strip():raise RuntimeError('Release has tracked changes')
    if allowed is not None:
        for flags in [[],['--ignored']]:
            names=git(path,'ls-files','--others','--exclude-standard','-z',*flags).decode().split('\0')
            if any(name and name not in allowed for name in names):raise RuntimeError('Unknown untracked release content')


def validate_release(path,revision):
    owned_directory(path)
    if not (path/MANIFEST).exists() and not (path/MANIFEST).is_symlink():
        raise RuntimeError('Occupied release lacks protected completion manifest')
    if prepare.protected_json(path/MANIFEST)!=identity(revision):raise RuntimeError('Correction release manifest mismatch')
    check_clean(path,revision,{MANIFEST,'.venv'})
    check_venv(path/'.venv',Path(identity(revision)['venv']))


def check_current(current,old,new):
    if (not current.is_symlink() or current.lstat().st_uid!=os.geteuid() or
            os.readlink(current) not in {str(old),str(new)}):
        raise RuntimeError('Unexpected current release pointer')


@contextmanager
def release_lock():
    path=prepare.OPT/'.credential-release.lock'
    descriptor=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_gid!=os.getegid() or
                info.st_nlink!=1 or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size!=0):
            raise RuntimeError('Unexpected release lock protection')
        fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:os.close(descriptor)


def switch_current(current,target):
    temporary=prepare.OPT/('.current-credential-'+secrets.token_hex(12))
    temporary.symlink_to(target,target_is_directory=True)
    try:os.replace(temporary,current)
    finally:
        if temporary.is_symlink():temporary.unlink()
    descriptor=os.open(prepare.OPT,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def publish_new_release(attempt,new):
    # Ubuntu/glibc renameat2(RENAME_NOREPLACE) also protects an empty destination
    # created between preflight and publication. Plain rename() could replace it.
    libc=ctypes.CDLL(None,use_errno=True)
    try:rename=libc.renameat2
    except AttributeError:raise RuntimeError('Atomic no-replace publication unavailable') from None
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(attempt),-100,os.fsencode(new),1)!=0:
        error=ctypes.get_errno()
        raise OSError(error,os.strerror(error),str(new))


def stage(revision,new):
    # A prior completed publication is validated and reused. Never adopt an
    # occupied path without our protected complete manifest and clean Git tree.
    if new.exists() or new.is_symlink():
        validate_release(new,revision)
        return
    if shutil.disk_usage(prepare.OPT).free<1024**3:raise RuntimeError('Keep at least 1 GiB spare disk for other services')
    attempt=new.parent/('.credential-stage-'+revision+'-'+secrets.token_hex(12))
    prepare.clone(attempt,revision)
    check_clean(attempt,revision,set())
    prepare.public_code_permissions(attempt)
    (attempt/'.venv').symlink_to(Path(identity(revision)['venv']),target_is_directory=True)
    prepare.write(attempt/MANIFEST,json.dumps(identity(revision),sort_keys=True)+'\n')
    validate_release(attempt,revision)
    if new.exists() or new.is_symlink():raise RuntimeError('Correction release path became occupied')
    # Parent is root-owned/nonwritable to other users; the release lock serializes
    # this procedure. Publish only a fully checked tree, then atomically activate.
    publish_new_release(attempt,new)
    descriptor=os.open(new.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def apply(revision,rollback=False):
    require_root();os.umask(0o077);check_scope(revision)
    owned_directory(prepare.OPT);owned_directory(prepare.OPT/'releases');owned_directory(prepare.BASE)
    with release_lock():
        check_quiet()
        marker=prepare.protected_json(prepare.BASE/'PROVISIONED.json')
        if marker!={'kind':'resmgrcheck-private-preparation','revision':INSTALLED_REVISION}:
            raise RuntimeError('Unexpected preparation marker; do not reset it')
        old=prepare.OPT/'releases'/INSTALLED_REVISION;new=prepare.OPT/'releases'/revision;current=prepare.OPT/'current'
        check_current(current,old,new);owned_directory(old)
        # Validate without index refresh/writes; never recreate or modify the
        # original immutable release, including its Git index.
        original_receipt=old.parent/('.'+old.name+'.clone.json')
        if prepare.protected_json(original_receipt)!={'kind':'resmgrcheck-private-clone',
                'source':str(prepare.SOURCE),'destination':str(old),'revision':INSTALLED_REVISION}:
            raise RuntimeError('Original clone completion receipt differs')
        check_clean(old,INSTALLED_REVISION,None)
        owned_directory(old/'.venv')
        if not (old/'.venv/bin/python').is_file():raise RuntimeError('Original virtualenv unavailable')
        for name in ['application-key','mfa-key','backup-key']:
            key=prepare.CONFIG/'keys'/name
            prepare.check_private_file(key)  # stat only: source secrets remain unopened
            if key.lstat().st_gid!=os.getegid() or not 0<key.lstat().st_size<=4096:
                raise RuntimeError('Unexpected source credential group/size')
        unit=prepare.UNIT_ROOT/'resmgrcheck-web.service';info=unit.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or
                stat.S_IMODE(info.st_mode) not in {0o600,0o644} or
                unit.read_bytes()!=(old/'web/ops/production/resmgrcheck-web.service').read_bytes()):
            raise RuntimeError('Canonical web unit changed; preserve for separate review')
        intent=prepare.BASE/'CREDENTIAL_RELEASE.json'
        if intent.exists() or intent.is_symlink():
            if prepare.protected_json(intent)!=identity(revision):raise RuntimeError('Another credential release is recorded')
        elif rollback:raise RuntimeError('No owned credential deployment to roll back')
        if rollback:
            validate_release(new,revision)
        else:
            # Immutable intent makes retry/rollback identify the exact owned release.
            if not intent.exists():prepare.write(intent,json.dumps(identity(revision),sort_keys=True)+'\n')
            stage(revision,new)
        check_current(current,old,new)
        switch_current(current,old if rollback else new)
        print(json.dumps({'credential_release_activated':not rollback,'rollback_to_failed_original':rollback,
            'revision':revision,'secrets_changed':False,'database_changed':False,'units_changed':False,
            'preparation_marker_changed':False,'services_started_or_reloaded':False,
            'qualification':'PENDING actual nonroot runtime_check and Unix-socket readiness'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.revision):parser.error('revision must be an exact committed SHA')
    if args.apply:apply(args.revision,args.rollback)
    else:
        check_scope(args.revision)
        print(json.dumps({'mode':'read-only rollback plan' if args.rollback else 'read-only release plan',
            **identity(args.revision),'new_release_directory':str(prepare.OPT/'releases'/args.revision),
            'reuse_existing_venv':True,'secrets_changed':False,'database_changed':False,'units_changed':False,
            'root_required_to_apply':True}))


if __name__=='__main__':main()
