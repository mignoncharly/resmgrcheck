#!/usr/bin/env python3
"""Immutable restore-verifier-only upgrade; no snapshot/key/DB/unit mutations.

Default is a read-only plan. Apply/rollback is a local-root operator action with
dedicated units stopped. Never runs a restore, migrations or service commands.
"""
import argparse,json,os,re,secrets,shutil
from pathlib import Path
import recover_socket_activation as sockets

release=sockets.release;p=sockets.p
ACTIVE='59158ade7da66475f3f1255e34aebd12fca29fce'
MANIFEST='.restore-release.json'
ALLOWED={'web/control/backup.py','web/control/management/commands/backup_snapshot.py',
    'web/ops/production/recover_restore_drill.py'}


def identity(revision):
    return {'kind':'resmgrcheck-restore-release','from_revision':ACTIVE,'revision':revision,
        'source':str(p.SOURCE),'venv':sockets.identity(ACTIVE)['venv']}


def check_scope(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision) or revision==ACTIVE:raise RuntimeError('Expected exact restore correction commit')
    if release.git(p.SOURCE,'rev-parse',revision+'^{commit}').decode().strip()!=revision:raise RuntimeError('Commit unavailable')
    release.git(p.SOURCE,'merge-base','--is-ancestor',ACTIVE,revision)
    paths=release.git(p.SOURCE,'diff','--name-only','-z',ACTIVE,revision).decode().split('\0')
    if any(name and name not in ALLOWED and not name.startswith(('docs/web/','web/tests/')) for name in paths):
        raise RuntimeError('Changes exceed restore verification; audit schema/units/credentials/dependencies must be unchanged')
    release.git(p.SOURCE,'cat-file','-e',revision+':web/ops/production/recover_restore_drill.py')


def validate(path,revision):
    release.owned_directory(path)
    if not (path/MANIFEST).exists() and not (path/MANIFEST).is_symlink():raise RuntimeError('Unknown restore release has no manifest')
    if p.protected_json(path/MANIFEST)!=identity(revision):raise RuntimeError('Restore release manifest differs')
    release.check_clean(path,revision,{MANIFEST,'.venv'})
    release.check_venv(path/'.venv',Path(identity(revision)['venv']))


def stage(revision,new):
    if new.exists() or new.is_symlink():validate(new,revision);return
    if shutil.disk_usage(p.OPT).free<1024**3:raise RuntimeError('Keep 1 GiB spare disk for other services')
    attempt=new.parent/('.restore-stage-'+revision+'-'+secrets.token_hex(12))
    p.clone(attempt,revision);release.check_clean(attempt,revision,set());p.public_code_permissions(attempt)
    (attempt/'.venv').symlink_to(Path(identity(revision)['venv']),target_is_directory=True)
    p.write(attempt/MANIFEST,json.dumps(identity(revision),sort_keys=True)+'\n');validate(attempt,revision)
    release.publish_new_release(attempt,new)
    directory=os.open(new.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)


def check_units(old):
    # No unit edits/reload in this upgrade, including the protected backup service.
    for name in ['resmgrcheck-web.service','resmgrcheck-web.socket','resmgrcheck-backup.service']:
        sockets.check_unit(p.UNIT_ROOT/name,[(old/'web/ops/production'/name).read_bytes()])
        if p.run(['systemctl','show','--value','--property=DropInPaths',name]).strip():raise RuntimeError('Unit overrides require separate review')
        for root in release.DROP_ROOTS:
            overrides=root.parent/(name+'.d')
            if overrides.is_symlink() or (overrides.exists() and
                    (not overrides.is_dir() or any(overrides.iterdir()) or
                     overrides.stat().st_uid!=os.geteuid() or overrides.stat().st_mode&0o022)):
                raise RuntimeError('Unknown unit override path')


def apply(revision,rollback=False):
    release.require_root();os.umask(0o077);check_scope(revision)
    for path in [p.OPT,p.OPT/'releases',p.BASE]:release.owned_directory(path)
    with release.release_lock():
        release.check_quiet()
        if p.protected_json(p.BASE/'PROVISIONED.json')!={'kind':'resmgrcheck-private-preparation','revision':release.INSTALLED_REVISION}:
            raise RuntimeError('Original preparation marker differs')
        if p.protected_json(p.BASE/'CREDENTIAL_RELEASE.json')!=release.identity(sockets.ACTIVE):
            raise RuntimeError('Credential deployment identity differs')
        if p.protected_json(p.BASE/'SOCKET_RELEASE.json')!=sockets.identity(ACTIVE):raise RuntimeError('Socket deployment identity differs')
        old=p.OPT/'releases'/ACTIVE;new=p.OPT/'releases'/revision;current=p.OPT/'current'
        release.check_current(current,old,new);sockets.validate(old,ACTIVE);check_units(old)
        venv=Path(identity(revision)['venv']);release.owned_directory(venv)
        if not (venv/'bin/python').is_file():raise RuntimeError('Original virtualenv unavailable')
        for name in ['application-key','mfa-key','backup-key']:
            key=p.CONFIG/'keys'/name;p.check_private_file(key)
            if key.lstat().st_gid!=os.getegid() or not 0<key.lstat().st_size<=4096:raise RuntimeError('Source credential metadata differs')
        intent=p.BASE/'RESTORE_RELEASE.json'
        if intent.exists() or intent.is_symlink():
            if p.protected_json(intent)!=identity(revision):raise RuntimeError('Another restore release is recorded')
        elif rollback:raise RuntimeError('No owned restore upgrade to roll back')
        if not rollback:
            if not intent.exists():p.write(intent,json.dumps(identity(revision),sort_keys=True)+'\n')
            stage(revision,new)
        elif new.exists() or new.is_symlink():validate(new,revision)
        release.check_current(current,old,new);release.switch_current(current,old if rollback else new)
        print(json.dumps({'restore_release_activated':not rollback,'rollback_to_original_verifier':rollback,
            'revision':revision,'snapshots_keys_database_audit_changed':False,'units_changed':False,
            'services_started_or_reloaded':False,'qualification':'PENDING real isolated production restore of the preserved snapshot'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.revision):parser.error('revision must be an exact committed SHA')
    if args.apply:apply(args.revision,args.rollback)
    else:
        check_scope(args.revision)
        print(json.dumps({'mode':'read-only restore rollback plan' if args.rollback else 'read-only restore upgrade plan',
            **identity(args.revision),'new_release_directory':str(p.OPT/'releases'/args.revision),
            'snapshots_keys_database_audit_changed':False,'units_changed':False,'root_required_to_apply':True}))


if __name__=='__main__':main()
