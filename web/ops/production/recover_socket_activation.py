#!/usr/bin/env python3
"""Reviewed immutable upgrade from the credential-corrected private installation.

Default is a read-only plan. Root apply/rollback requires stopped dedicated units.
Changes only the new release/current pointer and one known web ExecStart suffix.
Never reads key contents, migrates DB, changes other units, or starts/reloads services.
"""
import argparse,json,os,re,secrets,shutil,stat,tempfile
from pathlib import Path
import recover_credentials as release

p=release.prepare
ACTIVE='d6513ba2ccaf13fa4c7491b5cac095d5ab572a16'
MANIFEST='.socket-release.json'
SERVICE='web/ops/production/resmgrcheck-web.service'
ALLOWED={SERVICE,'web/ops/gunicorn.conf.py','web/ops/production/recover_socket_activation.py'}


def identity(revision):
    return {'kind':'resmgrcheck-socket-release','from_revision':ACTIVE,'revision':revision,
        'source':str(p.SOURCE),'venv':release.identity(ACTIVE)['venv']}


def unit_contents(revision):
    original=release.git(p.SOURCE,'show',ACTIVE+':'+SERVICE)
    target=release.git(p.SOURCE,'show',revision+':'+SERVICE)
    suffix=b' --bind fd://3\n'
    if original.count(suffix)!=1 or target!=original.replace(suffix,b'\n',1):
        raise RuntimeError('Only the reviewed web ExecStart fd bind removal is allowed')
    return original,target


def check_scope(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision) or revision==ACTIVE:raise RuntimeError('Expected exact socket correction commit')
    if release.git(p.SOURCE,'rev-parse',revision+'^{commit}').decode().strip()!=revision:raise RuntimeError('Commit unavailable')
    release.git(p.SOURCE,'merge-base','--is-ancestor',ACTIVE,revision)
    changed=release.git(p.SOURCE,'diff','--name-only','-z',ACTIVE,revision).decode().split('\0')
    if any(name and name not in ALLOWED and not name.startswith(('docs/web/','web/tests/')) for name in changed):
        raise RuntimeError('Changes exceed this socket-only upgrade; credentials/DB/dependencies/engine must remain unchanged')
    release.git(p.SOURCE,'cat-file','-e',revision+':web/ops/production/recover_socket_activation.py')
    return unit_contents(revision)


def check_unit(path,known):
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or
            stat.S_IMODE(info.st_mode) not in {0o600,0o644} or path.read_bytes() not in known):
        raise RuntimeError('Unknown installed web unit; preserve for separate review')


def replace_unit(path,content,known):
    check_unit(path,known)
    if path.read_bytes()==content:return
    descriptor,temporary=tempfile.mkstemp(prefix='.resmgrcheck-web-socket-',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(content);os.fchmod(stream.fileno(),stat.S_IMODE(path.stat().st_mode))
            stream.flush();os.fsync(stream.fileno())
        check_unit(path,known)
        os.replace(temporary,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def validate(path,revision):
    release.owned_directory(path)
    if not (path/MANIFEST).exists() and not (path/MANIFEST).is_symlink():raise RuntimeError('Unknown release has no completion manifest')
    if p.protected_json(path/MANIFEST)!=identity(revision):raise RuntimeError('Socket release manifest differs')
    release.check_clean(path,revision,{MANIFEST,'.venv'})
    release.check_venv(path/'.venv',Path(identity(revision)['venv']))


def stage(revision,new):
    if new.exists() or new.is_symlink():validate(new,revision);return
    if shutil.disk_usage(p.OPT).free<1024**3:raise RuntimeError('Keep 1 GiB spare disk for other services')
    attempt=new.parent/('.socket-stage-'+revision+'-'+secrets.token_hex(12))
    p.clone(attempt,revision);release.check_clean(attempt,revision,set())
    p.public_code_permissions(attempt)
    (attempt/'.venv').symlink_to(Path(identity(revision)['venv']),target_is_directory=True)
    p.write(attempt/MANIFEST,json.dumps(identity(revision),sort_keys=True)+'\n');validate(attempt,revision)
    release.publish_new_release(attempt,new)
    directory=os.open(new.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)


def apply(revision,rollback=False):
    release.require_root();os.umask(0o077);original,target=check_scope(revision)
    for path in [p.OPT,p.OPT/'releases',p.BASE]:release.owned_directory(path)
    with release.release_lock():
        release.check_quiet()
        if p.protected_json(p.BASE/'PROVISIONED.json')!={'kind':'resmgrcheck-private-preparation','revision':release.INSTALLED_REVISION}:
            raise RuntimeError('Original preparation marker differs')
        if p.protected_json(p.BASE/'CREDENTIAL_RELEASE.json')!=release.identity(ACTIVE):
            raise RuntimeError('Verified credential deployment identity differs')
        old=p.OPT/'releases'/ACTIVE;new=p.OPT/'releases'/revision;current=p.OPT/'current'
        release.check_current(current,old,new);release.validate_release(old,ACTIVE)
        venv=Path(identity(revision)['venv']);release.owned_directory(venv)
        if not (venv/'bin/python').is_file():raise RuntimeError('Original shared virtualenv unavailable')
        for name in ['application-key','mfa-key','backup-key']:
            key=p.CONFIG/'keys'/name;p.check_private_file(key)
            if key.lstat().st_gid!=os.getegid() or not 0<key.lstat().st_size<=4096:raise RuntimeError('Source credential metadata differs')
        unit=p.UNIT_ROOT/'resmgrcheck-web.service';check_unit(unit,[original,target])
        # The socket's path/mode/identity are also part of the verified handoff;
        # inspect it, but never rewrite it as part of this correction.
        socket_name='resmgrcheck-web.socket'
        check_unit(p.UNIT_ROOT/socket_name,[(old/'web/ops/production'/socket_name).read_bytes()])
        if p.run(['systemctl','show','--value','--property=DropInPaths',socket_name]).strip():
            raise RuntimeError('Unknown socket overrides require separate review')
        for root in release.DROP_ROOTS:
            overrides=root.parent/(socket_name+'.d')
            if overrides.is_symlink() or (overrides.exists() and
                    (not overrides.is_dir() or any(overrides.iterdir()) or
                     overrides.stat().st_uid!=os.geteuid() or overrides.stat().st_mode&0o022)):
                raise RuntimeError('Unknown socket overrides require separate review')
        intent=p.BASE/'SOCKET_RELEASE.json'
        if intent.exists() or intent.is_symlink():
            if p.protected_json(intent)!=identity(revision):raise RuntimeError('Another socket upgrade is recorded')
        elif rollback:raise RuntimeError('No recorded socket upgrade to roll back')
        if not rollback:
            if not intent.exists():p.write(intent,json.dumps(identity(revision),sort_keys=True)+'\n')
            stage(revision,new)
        elif new.exists() or new.is_symlink():validate(new,revision)
        # Both known interrupted combinations are resumable while web is stopped.
        # No other unit directive, key/config or data file is changed.
        replace_unit(unit,original if rollback else target,[original,target])
        release.check_current(current,old,new)
        release.switch_current(current,old if rollback else new)
        print(json.dumps({'socket_release_activated':not rollback,'rollback_to_socket_failing_release':rollback,
            'revision':revision,'secrets_changed':False,'database_changed':False,'other_units_changed':False,
            'daemon_reload_required':True,'services_started_or_reloaded':False,
            'qualification':'PENDING real root-managed service runtime_check, socket activation and HTTP200 readiness'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.revision):parser.error('revision must be an exact committed SHA')
    if args.apply:apply(args.revision,args.rollback)
    else:
        check_scope(args.revision)
        print(json.dumps({'mode':'read-only socket rollback plan' if args.rollback else 'read-only socket upgrade plan',
            **identity(args.revision),'new_release_directory':str(p.OPT/'releases'/args.revision),
            'web_unit_change':'remove only --bind fd://3','secrets_changed':False,'database_changed':False,
            'other_units_changed':False,'root_required_to_apply':True}))


if __name__=='__main__':main()
