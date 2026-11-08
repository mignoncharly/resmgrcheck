#!/usr/bin/env python3
"""Temporary operator-installed, metadata-only probe in the REAL web unit context.

Default: print a plan. --install/--remove require local root and stopped dedicated
web service/socket. --probe reads metadata only and always leaves runtime_check
as the next ExecStartPre. No secret content is read, hashed, copied or modified.
"""
import argparse,errno,json,os,stat,struct,subprocess
from pathlib import Path

SCRIPT=Path('/run/resmgrcheck-credential-diagnostic.py')
DROP_ROOT=Path('/run/systemd/system/resmgrcheck-web.service.d')
DROP=DROP_ROOT/'50-resmgrcheck-credential-diagnostic.conf'
PERSISTENT_DROP_ROOT=Path('/etc/systemd/system/resmgrcheck-web.service.d')
UNIT=Path('/etc/systemd/system/resmgrcheck-web.service')
REFERENCE=Path(__file__).resolve().parent/'resmgrcheck-web.service'
IDS={'RMC_WEB_SECRET_KEY_FILE':'application-key','RMC_WEB_MFA_KEY_FILE':'mfa-key'}
TAGS={1:'user_obj',2:'user',4:'group_obj',8:'group',16:'mask',32:'other'}
OVERRIDE=(
    '# Temporary ResMgrCheck credential metadata probe; original runtime_check retained.\n'
    '[Service]\n'
    'ExecStartPre=\n'
    'ExecStartPre=/opt/resmgrcheck/current/.venv/bin/python /run/resmgrcheck-credential-diagnostic.py --probe\n'
    'ExecStartPre=/opt/resmgrcheck/current/.venv/bin/python manage.py runtime_check\n'
    'Restart=no\n'
).encode()


def acl_metadata(descriptor):
    try:raw=os.getxattr(descriptor,'system.posix_acl_access')
    except OSError as error:
        if error.errno in {errno.ENODATA,errno.ENOTSUP}:return None
        return {'error':'acl_unavailable','errno':error.errno}
    if len(raw)<4 or (len(raw)-4)%8 or struct.unpack_from('<I',raw)[0]!=2:
        return {'error':'invalid_acl_encoding'}
    return {'version':2,'entries':[{'tag':TAGS.get(tag,'unknown'),
        'id':None if identity==0xffffffff else identity,'permissions':permission}
        for tag,permission,identity in struct.iter_unpack('<HHI',raw[4:])]}


def file_metadata(directory,identity):
    result={'credential_id':identity}
    # No content read: open read-only solely for fstat/fgetxattr. Do not follow
    # a substituted directory or file symlink, including nonregular inputs.
    parent=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        info=os.stat(identity,dir_fd=parent,follow_symlinks=False)
        kind=('regular' if stat.S_ISREG(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode)
              else 'directory' if stat.S_ISDIR(info.st_mode) else 'other')
        result.update(uid=info.st_uid,gid=info.st_gid,mode=oct(stat.S_IMODE(info.st_mode)),file_type=kind)
        if kind!='regular':
            result['access_acl']=None
            return result
        descriptor=os.open(identity,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent)
        try:
            actual=os.fstat(descriptor)
            if (actual.st_dev,actual.st_ino)!=(info.st_dev,info.st_ino):
                return {'credential_id':identity,'metadata_error':'file_changed_during_inspection'}
            result.update(uid=actual.st_uid,gid=actual.st_gid,mode=oct(stat.S_IMODE(actual.st_mode)))
            result['access_acl']=acl_metadata(descriptor)
        finally:os.close(descriptor)
        return result
    finally:os.close(parent)


def probe():
    directory=os.environ.get('CREDENTIALS_DIRECTORY','')
    records=[]
    for variable,identity in IDS.items():
        filename=os.environ.get(variable,'')
        if not directory or not Path(directory).is_absolute() or Path(filename)!=Path(directory)/identity:
            records.append({'credential_id':identity,'metadata_error':'missing_or_unexpected_runtime_path'})
            continue
        try:records.append(file_metadata(directory,identity))
        except OSError as error:records.append({'credential_id':identity,'metadata_error':'unavailable','errno':error.errno})
    print(json.dumps({'probe':'resmgrcheck-credential-metadata','credentials':records}),flush=True)
    # This observer never replaces/waives runtime_check, even when metadata fails.
    return 0


def require_root():
    if os.geteuid()!=0:raise SystemExit('Diagnostic install/remove requires the local root operator')


def stopped():
    for unit in ['resmgrcheck-web.service','resmgrcheck-web.socket']:
        check=subprocess.run(['systemctl','show','--value','--property=ActiveState',unit],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=10,
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        if check.stdout.strip() not in {b'inactive',b'failed'}:
            raise RuntimeError('Stop only the dedicated web socket/service before diagnostic install/remove')


def known_file(path,content,modes):
    if not path.exists() and not path.is_symlink():return False
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or
            stat.S_IMODE(info.st_mode) not in modes or path.read_bytes()!=content):
        raise RuntimeError('Refusing to overwrite/remove unknown diagnostic or unit file: '+path.name)
    return True


def safe_directory(path):
    for parent in [path,*path.parents]:
        if parent.is_symlink():raise RuntimeError('Refusing diagnostic directory symlinks')
    if path.exists():
        info=path.stat()
        if not path.is_dir() or info.st_uid!=os.geteuid() or info.st_mode&0o022:
            raise RuntimeError('Unexpected diagnostic directory ownership/permissions')


def exclusive_file(path,content):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(content);stream.flush();os.fsync(stream.fileno());os.fchmod(stream.fileno(),0o644)


def change(install):
    require_root();stopped()
    source=Path(__file__).resolve().read_bytes()
    # Preflight every occupied path before making any changes. Installed canonical
    # unit contents are checked, never rewritten. No credential sources are opened.
    reference=REFERENCE.read_bytes()
    if [line for line in reference.splitlines() if line.startswith(b'ExecStartPre=')]!=[
            b'ExecStartPre=/opt/resmgrcheck/current/.venv/bin/python manage.py runtime_check']:
        raise RuntimeError('Additional startup checks require separate diagnostic review')
    if not known_file(UNIT,reference,{0o600,0o644}):
        raise RuntimeError('Expected installed private web unit')
    for parent in [SCRIPT.parent,DROP_ROOT.parent,DROP_ROOT,PERSISTENT_DROP_ROOT]:safe_directory(parent)
    if PERSISTENT_DROP_ROOT.exists() and any(PERSISTENT_DROP_ROOT.iterdir()):
        raise RuntimeError('Existing persistent web overrides require separate review')
    if DROP_ROOT.exists() and any(p!=DROP for p in DROP_ROOT.iterdir()):
        raise RuntimeError('Existing runtime web overrides require separate review')
    script_exists=known_file(SCRIPT,source,{0o644})
    drop_exists=known_file(DROP,OVERRIDE,{0o644})
    if install:
        if not DROP_ROOT.exists():DROP_ROOT.mkdir(mode=0o755)
        if not script_exists:exclusive_file(SCRIPT,source)
        if not drop_exists:exclusive_file(DROP,OVERRIDE)
    else:
        if drop_exists:DROP.unlink()
        if script_exists:SCRIPT.unlink()
        # Keep the empty directory: do not remove any unknown/existing directory.
    print(json.dumps({'temporary_diagnostic_installed':install,'secrets_changed':False,
        'canonical_unit_changed':False,'services_started_or_reloaded':False,
        'operator_next':'daemon-reload; see PRIVATE_INSTALL.md for the one-attempt capture and removal'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    flags=parser.add_mutually_exclusive_group()
    flags.add_argument('--probe',action='store_true');flags.add_argument('--install',action='store_true');flags.add_argument('--remove',action='store_true')
    args=parser.parse_args()
    if args.probe:return probe()
    if args.install or args.remove:change(args.install)
    else:print(json.dumps({'mode':'read-only diagnostic plan','temporary_script':str(SCRIPT),
        'temporary_web_override':str(DROP),'runtime_check_retained':True,'root_required_to_install_remove':True}))
    return 0


if __name__=='__main__':raise SystemExit(main())
