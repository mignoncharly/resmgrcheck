#!/usr/bin/env python3
"""Reviewed initial private expansion from3821952. Plans are read-only.

Operator-only stage/prepare/activate/rollback; never starts or reloads services,
changes units/configuration/keys, or contacts QNX. Customer endpoints stay disabled.
"""
import argparse,hashlib,json,os,re,secrets,shutil,stat,time
from pathlib import Path
import recover_restore_drill as previous

release=previous.release;p=previous.p
ACTIVE='3821952e6c99cf8c6d548e59301166dde590b8a0'
MANIFEST='.private-web-release.json'
UNIT_NAMES=p.UNITS
FROZEN=['web/requirements.lock','web/ops/gunicorn.conf.py','web/ops/production/runtime.py',
    *['web/ops/production/'+name for name in UNIT_NAMES],
    *['web/control/migrations/'+name for name in [
        '0001_initial.py','0002_ratebucket_user_session_version_accountdeletion_and_more.py','0003_audit_append_only.py',
        '0004_buildrelease_run_executorslot_target_run_target_and_more.py','0005_run_intent_guard.py','0006_immutable_artifacts.py',
        '0007_retention_metadata.py','0008_sealed_graph.py','0009_optional_ai.py','0010_ai_intent_guard.py','0011_ai_output_integrity.py',
        '0012_ai_output_guard.py','0013_administrator_access_codes.py','0014_access_authority_guards.py',
        '0015_source_principal_constraint.py','0016_administrator_only_accounts.py','0017_session_and_scope_integrity.py']]]


def identity(revision):
    return {'kind':'resmgrcheck-private-web-release','from_revision':ACTIVE,'revision':revision,
        'source':str(p.SOURCE),'venv':previous.identity(ACTIVE)['venv'],'runner_enabled':False}


def check_scope(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision) or revision==ACTIVE:raise RuntimeError('Expected exact descendant release commit')
    if release.git(p.SOURCE,'rev-parse',revision+'^{commit}').decode().strip()!=revision:raise RuntimeError('Commit unavailable')
    release.git(p.SOURCE,'merge-base','--is-ancestor',ACTIVE,revision)
    # Freeze historical migration files by tree enumeration as well as explicit paths.
    historical=release.git(p.SOURCE,'ls-tree','-r','--name-only',ACTIVE,'web/control/migrations/').decode().splitlines()
    if release.git(p.SOURCE,'diff','--name-only',ACTIVE,revision,'--',*FROZEN,*historical).strip():
        raise RuntimeError('Historical schema, dependencies, runtime launcher or unit changes require separate review')
    for name in ['web/ops/production/upgrade_private.py','web/control/management/commands/private_release.py','web/ops/production/runner-grants.sql']:
        release.git(p.SOURCE,'cat-file','-e',revision+':'+name)


def validate(path,revision):
    release.owned_directory(path)
    if not (path/MANIFEST).exists() and not (path/MANIFEST).is_symlink():raise RuntimeError('Occupied release has no private completion manifest')
    if p.protected_json(path/MANIFEST)!=identity(revision):raise RuntimeError('Private release manifest differs')
    release.check_clean(path,revision,{MANIFEST,'.venv'})
    release.check_venv(path/'.venv',Path(identity(revision)['venv']))


def stage(revision,new):
    if new.exists() or new.is_symlink():validate(new,revision);return
    if shutil.disk_usage(p.OPT).free<2*1024**3:raise RuntimeError('Keep2 GiB spare disk for other services')
    attempt=new.parent/('.private-web-stage-'+revision+'-'+secrets.token_hex(12))
    p.clone(attempt,revision);release.check_clean(attempt,revision,set());p.public_code_permissions(attempt)
    (attempt/'.venv').symlink_to(Path(identity(revision)['venv']),target_is_directory=True)
    p.write(attempt/MANIFEST,json.dumps(identity(revision),sort_keys=True)+'\n');validate(attempt,revision)
    release.publish_new_release(attempt,new)
    descriptor=os.open(new.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def check_installation(revision):
    release.check_quiet()
    if p.protected_json(p.BASE/'PROVISIONED.json')!={'kind':'resmgrcheck-private-preparation','revision':release.INSTALLED_REVISION}:
        raise RuntimeError('Original preparation record differs')
    if p.protected_json(p.BASE/'CREDENTIAL_RELEASE.json')!=release.identity(previous.sockets.ACTIVE):raise RuntimeError('Credential record differs')
    if p.protected_json(p.BASE/'SOCKET_RELEASE.json')!=previous.sockets.identity(previous.ACTIVE):raise RuntimeError('Socket record differs')
    if p.protected_json(p.BASE/'RESTORE_RELEASE.json')!=previous.identity(ACTIVE):raise RuntimeError('Restore record differs')
    old=p.OPT/'releases'/ACTIVE;new=p.OPT/'releases'/revision
    release.check_current(p.OPT/'current',old,new);previous.validate(old,ACTIVE)
    for name in UNIT_NAMES:
        previous.sockets.check_unit(p.UNIT_ROOT/name,[(old/'web/ops/production'/name).read_bytes()])
        if p.run(['systemctl','show','--value','--property=DropInPaths',name]).strip():raise RuntimeError('Unit overrides require separate review')
        for root in release.DROP_ROOTS:
            path=root.parent/(name+'.d')
            if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()) or
                    path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o022)):
                raise RuntimeError('Unknown unit override path')
    venv=Path(identity(revision)['venv']);release.owned_directory(venv)
    if not (venv/'bin/python').is_file():raise RuntimeError('Original virtualenv unavailable')
    for name in ['application-key','mfa-key','backup-key']:
        path=p.CONFIG/'keys'/name;p.check_private_file(path);info=path.lstat()
        if info.st_gid!=os.getegid() or not 0<info.st_size<=4096:raise RuntimeError('Source key metadata differs')
    # Existing operator config stays unopened here and is never rewritten.
    p.check_private_file(p.CONFIG/'operator.json')
    return old,new


def runtime(new,operation,revision):
    raw=p.run([str(new/'.venv/bin/python'),'-B',str(new/'web/ops/production/runtime.py'),
        '--config',str(p.CONFIG/'operator.json'),'manage.py','private_release',operation,'--revision',revision])
    value=json.loads(raw)
    if value.get('passed') is not True or value.get('revision')!=revision or value.get('operation')!=operation or value.get('runner_enabled') is not False:
        raise RuntimeError('Private schema/assets gate did not pass')


def verify_backup(new,binding):
    raw=p.run([str(new/'.venv/bin/python'),'-B',str(new/'web/ops/production/runtime.py'),
        '--config',str(p.CONFIG/'operator.json'),'manage.py','backup_snapshot','restore-drill',
        '--archive',binding['archive'],'--key-file',str(p.CONFIG/'keys/backup-key')])
    value=json.loads(raw)
    required=['passed','audit_behavior_tested','audit_update_denied','audit_delete_denied','audit_probe_rolled_back',
        'database_identity_matches','temporary_database_removed_on_exit','original_database_preserved']
    if (any(value.get(key) is not True for key in required) or value.get('diagnostic_only') is not False or
            value.get('qnx_contacted') is not False or value.get('encrypted_sha256')!=binding['encrypted_sha256']):
        raise RuntimeError('Fresh pre-upgrade isolated restore did not pass')


def backup_binding(archive,intent,fresh=True):
    if archive is None:raise RuntimeError('prepare requires the new protected pre-upgrade archive')
    path=Path(archive)
    if path.parent!=p.BACKUP or not re.fullmatch('snapshot_[0-9]{8}T[0-9]{6}Z[.]rmc',path.name):
        raise RuntimeError('Expected exact dedicated snapshot path')
    release.owned_directory(p.BACKUP,0o700)
    receipt=Path(str(path)+'.receipt.json');p.check_private_file(path);record=p.protected_json(receipt)
    info=path.lstat()
    if (info.st_gid!=os.getegid() or (fresh and (info.st_mtime<intent.stat().st_mtime or not 0<=time.time()-info.st_mtime<=86400)) or
            not 0<info.st_size<=16*1024**3 or record.get('passed') is not True or record.get('qnx_contacted') is not False):
        raise RuntimeError('Expected fresh completed protected pre-upgrade snapshot')
    digest=hashlib.sha256();descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(descriptor)
        if (before.st_dev,before.st_ino,before.st_size)!=(info.st_dev,info.st_ino,info.st_size):raise RuntimeError('Snapshot changed')
        with os.fdopen(descriptor,'rb',closefd=False) as stream:
            for block in iter(lambda:stream.read(1024**2),b''):digest.update(block)
        after=os.fstat(descriptor)
        if (after.st_size,after.st_mtime_ns,after.st_ctime_ns)!=(before.st_size,before.st_mtime_ns,before.st_ctime_ns):raise RuntimeError('Snapshot changed')
    finally:os.close(descriptor)
    if digest.hexdigest()!=record.get('encrypted_sha256'):raise RuntimeError('Snapshot receipt hash differs')
    return {'archive':str(path),'encrypted_sha256':digest.hexdigest()}


def apply(revision,operation,archive=None):
    release.require_root();os.umask(0o077);check_scope(revision)
    for path in [p.OPT,p.OPT/'releases',p.BASE]:release.owned_directory(path)
    with release.release_lock():
        old,new=check_installation(revision);intent=p.BASE/'PRIVATE_WEB_RELEASE.json'
        if intent.exists() or intent.is_symlink():
            if p.protected_json(intent)!=identity(revision):raise RuntimeError('Another private release is recorded')
        elif operation!='stage':raise RuntimeError('Stage this exact release first')
        else:p.write(intent,json.dumps(identity(revision),sort_keys=True)+'\n')
        if operation=='stage':stage(revision,new)
        else:
            validate(new,revision);prepared=p.BASE/'PRIVATE_WEB_PREPARED.json'
            if operation=='prepare':
                backup=p.BASE/'PRIVATE_WEB_PREUPGRADE_BACKUP.json'
                binding={**identity(revision),**backup_binding(archive,intent,fresh=not (backup.exists() or backup.is_symlink()))}
                if backup.exists() or backup.is_symlink():
                    if p.protected_json(backup)!=binding:raise RuntimeError('Keep the original bound pre-upgrade snapshot')
                else:p.write(backup,json.dumps(binding,sort_keys=True)+'\n')
                verified=p.BASE/'PRIVATE_WEB_BACKUP_VERIFIED.json'
                if verified.exists() or verified.is_symlink():
                    if p.protected_json(verified)!=binding:raise RuntimeError('Verified backup record differs')
                else:
                    verify_backup(new,binding)
                    p.write(verified,json.dumps(binding,sort_keys=True)+'\n')
                runtime(new,'prepare',revision)
                p.write(prepared,json.dumps(binding,sort_keys=True)+'\n')
            else:
                binding=p.protected_json(p.BASE/'PRIVATE_WEB_PREUPGRADE_BACKUP.json')
                if (p.protected_json(prepared)!=binding or p.protected_json(p.BASE/'PRIVATE_WEB_BACKUP_VERIFIED.json')!=binding or
                        any(binding.get(k)!=v for k,v in identity(revision).items())):
                    raise RuntimeError('Prepared release record differs')
                runtime(new,'rollback-check' if operation=='rollback' else 'check',revision)
                release.check_current(p.OPT/'current',old,new)
                release.switch_current(p.OPT/'current',old if operation=='rollback' else new)
        print(json.dumps({'operation':operation,'revision':revision,'runner_enabled':False,'units_keys_configs_changed':False,
            'services_started_or_reloaded':False,'public_exposure':False,'qualification':'PENDING actual private runtime/readiness/isolation and compatible rollback'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    parser.add_argument('--operation',choices=['stage','prepare','activate','rollback'],default='stage')
    parser.add_argument('--archive');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if args.apply:apply(args.revision,args.operation,args.archive)
    else:
        check_scope(args.revision)
        print(json.dumps({'mode':'read-only plan',**identity(args.revision),'operation':args.operation,
            'new_release_directory':str(p.OPT/'releases'/args.revision),'additive_migrations':['0018','0019','0020'],
            'requires_fresh_encrypted_backup_before_prepare':True,'reverses_migrations':False,'changes_units_keys_configs':False,
            'root_required_to_apply':True,'starts_services':False,'public_deployment':False}))


if __name__=='__main__':main()
