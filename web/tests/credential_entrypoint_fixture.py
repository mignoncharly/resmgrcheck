"""Subprocess-only compatibility fixture. Simulates UID982/stat/ACL, NOT OS isolation.

Uses synthetic credentials only. Never starts a server or connects to a database.
The production unit's real runtime_check and readiness remain operator gates.
"""
import contextlib,errno,json,os,pwd,runpy,stat,struct,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from resmgr_web import credentials as c


def main():
    directory=Path(sys.argv[1]);reader=sys.argv[2]
    insecure_acl=len(sys.argv)>3 and sys.argv[3]=='insecure-acl'
    service_uid=982
    real_stat=os.fstat;real_acl=os.getxattr;real_user=pwd.getpwnam;real_uid=pwd.getpwuid
    files={(directory/name).stat().st_ino for name in ['application-key','mfa-key']}
    directory_inode=directory.stat().st_ino
    def metadata(fd):
        info=real_stat(fd)
        if info.st_ino not in files|{directory_inode}:return info
        return SimpleNamespace(st_uid=0,st_gid=0,st_nlink=1,st_size=info.st_size,
            st_mode=(stat.S_IFDIR|0o550) if info.st_ino==directory_inode else (stat.S_IFREG|0o440))
    def acl(fd,name):
        info=real_stat(fd)
        if info.st_ino not in files|{directory_inode}:return real_acl(fd,name)
        entries=c.systemd_acl(service_uid,directory=info.st_ino==directory_inode)
        if insecure_acl and info.st_ino in files:
            entries=[(tag,4 if tag==4 else permission,uid) for tag,permission,uid in entries]
        return struct.pack('<I',2)+b''.join(struct.pack('<HHI',*entry) for entry in entries)
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(c.os,'fstat',side_effect=metadata))
        stack.enter_context(patch.object(c.os,'getxattr',side_effect=acl))
        stack.enter_context(patch.object(c.os,'geteuid',return_value=service_uid))
        stack.enter_context(patch.object(c.pwd,'getpwnam',side_effect=lambda name:SimpleNamespace(pw_uid=service_uid) if name=='resmgr-web' else real_user(name)))
        stack.enter_context(patch.object(c.pwd,'getpwuid',side_effect=lambda uid:SimpleNamespace(pw_name='resmgr-web') if uid==service_uid else real_uid(uid)))
        stack.enter_context(patch.dict(c.SYSTEMD_DIRECTORIES,{'web':directory}))
        if reader=='gunicorn':
            sys.argv=['gunicorn','--check-config','--config',str(ROOT/'ops/gunicorn.conf.py'),'resmgr_web.wsgi:application']
            try:runpy.run_module('gunicorn',run_name='__main__')
            except SystemExit as result:
                if result.code not in {0,None}:raise
            assert 'resmgr_web.wsgi' in sys.modules
        else:
            import django
            django.setup()
            from control.management.commands import runtime_check as runtime
            from django.core.management import call_command
            cursor=MagicMock();cursor.fetchone.side_effect=[(False,)*5,(0,),(False,),(False,)]
            connection=MagicMock();connection.cursor.return_value.__enter__.return_value=cursor
            with patch.object(runtime,'connection',connection),patch.object(runtime.os,'access',return_value=False), \
                    patch.object(runtime.socket,'socket',side_effect=OSError(errno.EAFNOSUPPORT,'synthetic sandbox denial')):
                call_command('runtime_check')
        from django.conf import settings
        assert settings.SECRET_KEY=='synthetic-application-'+'x'*64
        assert settings.MFA_ENCRYPTION_KEY
        print(json.dumps({'compatibility_fixture':reader,'credential_read_succeeded':True,
            'simulated_service_uid':service_uid,'production_runtime_qualification':False}))


if __name__=='__main__':main()
