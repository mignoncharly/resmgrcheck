"""Exact UI deployment scope and recovery; service/root operations modeled."""
import json,tempfile,unittest
from contextlib import ExitStack,nullcontext
from pathlib import Path
from unittest.mock import patch,Mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import deploy_security_page as deploy
from https_checks import CheckFailed

DRIVER='a'*40
class SecurityReleaseTests(unittest.TestCase):
    def test_static_site_change_is_exactly_one_revision_alias(self):
        self.assertEqual(deploy.site_bytes(deploy.CANDIDATE),deploy.site_bytes(deploy.ACTIVE).replace(deploy.ACTIVE.encode(),deploy.CANDIDATE.encode()))
        self.assertEqual(deploy.site_bytes(deploy.ACTIVE).count(deploy.ACTIVE.encode()),1)

    def test_scope_accepts_only_reviewed_application_files_and_clean_driver(self):
        def git(*args):
            if args[:2]==('diff','--name-only') and args[2:4]==(deploy.ACTIVE,deploy.CANDIDATE) and len(args)==4:
                return ('\n'.join(sorted(deploy.APP_FILES))+'\ndocs/web/STATUS.md\nweb/tests/example.py').encode()
            return b''
        with patch.object(deploy.ops,'git',side_effect=git):deploy.scope(DRIVER)
        for name in ['web/control/security.py','web/control/migrations/9999.py','native/runner.c','web/resmgr_web/settings.py']:
            def changed(*args):
                value=git(*args)
                return value+b'\n'+name.encode() if value else value
            with patch.object(deploy.ops,'git',side_effect=changed),self.assertRaises(CheckFailed):deploy.scope(DRIVER)
        with patch.object(deploy.ops,'git',return_value=b'dirty'),self.assertRaises(CheckFailed):deploy.scope(DRIVER)
        with self.assertRaises(CheckFailed):deploy.scope('HEAD')

    def test_helper_accepts_final_receipt_and_rejects_failed_receipt(self):
        with patch.object(deploy.ops,'command',return_value=b'{"progress":"done"}\n{"passed":true}\n'):
            deploy.helper('--acceptance',deploy.CANDIDATE,DRIVER)
        with patch.object(deploy.ops,'command',return_value=b'{"passed":false}'),self.assertRaises(CheckFailed):
            deploy.helper('--runtime',deploy.CANDIDATE,DRIVER)

    def test_unknown_site_refused_before_any_mutation(self):
        with patch.object(deploy.ops.ENABLED.__class__,'is_symlink',return_value=True),\
            patch.object(deploy.ops.ENABLED.__class__,'resolve',return_value=deploy.ops.SITE),\
            patch.object(deploy.ops,'read',return_value=b'unknown'),\
            patch.object(deploy.ops,'replace_owned') as replace,self.assertRaises(CheckFailed):deploy.validate_site()
        replace.assert_not_called()

    def test_restore_preserves_old_release_and_restarts_exact_owned_services(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);old=root/'old';new=root/'new';journal={'executor_before':'active'}
            stack.enter_context(patch.object(deploy,'validate_site'))
            stack.enter_context(patch.object(deploy.auth.release,'check_current'))
            switch=stack.enter_context(patch.object(deploy.auth.release,'switch_current'))
            web=stack.enter_context(patch.object(deploy.auth,'web'))
            commands=stack.enter_context(patch.object(deploy.ops,'command',return_value=b''))
            stack.enter_context(patch.object(deploy.ops,'read',return_value=deploy.site_bytes(deploy.CANDIDATE)))
            replace=stack.enter_context(patch.object(deploy.ops,'replace_owned'))
            stack.enter_context(patch.object(deploy,'health'))
            deploy.restore(old,new,journal,root/'journal.json')
            self.assertEqual(journal['phase'],'original_restored');switch.assert_called_once_with(deploy.ops.OPT/'current',old)
            self.assertEqual([c.args[0] for c in web.call_args_list],['stop','start'])
            self.assertEqual(commands.call_args_list[-1].args[0],['systemctl','start','resmgrcheck-executor.service'])
            self.assertEqual(replace.call_args.args[1],deploy.site_bytes(deploy.ACTIVE))

    def test_restore_refuses_foreign_site_before_stopping_services(self):
        with patch.object(deploy,'validate_site',side_effect=CheckFailed('unknown_site_configuration')),\
            patch.object(deploy.auth,'web') as web,self.assertRaises(CheckFailed):
            deploy.restore(Path('/old'),Path('/new'),{},Path('/unused'))
        web.assert_not_called()

    def test_activation_failure_restores_original_but_backup_failure_never_switches(self):
        for failure in ['backup','runtime']:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temporary,ExitStack() as stack:
                root=Path(temporary);state=root/'state';state.mkdir(mode=0o700)
                old=root/'old';new=root/'new';(root/'current').symlink_to(old)
                for target,name,value in [(deploy,'STATE',state),(deploy.ops,'OPT',root),(deploy.auth.p,'UNITS',[])]:
                    stack.enter_context(patch.object(target,name,value))
                for target,name in [(deploy.ops,'require_root'),(deploy,'scope'),(deploy,'validate_site'),(deploy,'health'),(deploy.auth,'web'),(deploy.auth.release,'check_current')]:
                    stack.enter_context(patch.object(target,name))
                stack.enter_context(patch.object(deploy,'stage',return_value=(old,new)))
                stack.enter_context(patch.object(deploy.auth.release,'release_lock',side_effect=nullcontext))
                stack.enter_context(patch.object(deploy.ops,'locked',side_effect=nullcontext))
                stack.enter_context(patch.object(deploy.ops,'read',return_value=deploy.site_bytes(deploy.ACTIVE)))
                stack.enter_context(patch.object(deploy.ops,'unrelated_snapshot',return_value={}))
                stack.enter_context(patch.object(deploy.ops,'command',return_value=b'active'))
                backup=stack.enter_context(patch.object(deploy.auth,'snapshot',side_effect=CheckFailed('backup_failed') if failure=='backup' else None))
                helper=stack.enter_context(patch.object(deploy,'helper',side_effect=lambda flag,*_: (_ for _ in ()).throw(CheckFailed('runtime_failed')) if flag=='--runtime' else None))
                switch=stack.enter_context(patch.object(deploy.auth.release,'switch_current'))
                restore=stack.enter_context(patch.object(deploy,'restore'))
                with self.assertRaises(CheckFailed):deploy.apply(DRIVER)
                backup.assert_called_once()
                if failure=='backup':switch.assert_not_called();restore.assert_not_called()
                else:switch.assert_called_once();restore.assert_called_once()
