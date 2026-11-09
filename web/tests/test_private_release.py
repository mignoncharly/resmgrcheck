"""Actual disposable PG upgrade/grant gate and filesystem static publication."""
import io,json,os,tempfile,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase,SimpleTestCase,override_settings
from control.management.commands import private_release as gate
from .helpers import tenant

class StaticReleaseTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.revision='1'*40
        self.root.chmod(0o755);self.mock=patch.object(gate,'STATIC',self.root);self.mock.start();self.addCleanup(self.mock.stop)
    def test_new_static_tree_is_hash_bound_retryable_and_never_overwrites_old_tree(self):
        old=self.root/('0'*40);old.mkdir();(old/'keep').write_bytes(b'old static')
        target=Path(gate.assets(self.revision));saved=(target/'control/app.css').read_bytes()
        self.assertEqual(gate.assets(self.revision),str(target));self.assertEqual((old/'keep').read_bytes(),b'old static')
        (target/'control/app.css').write_bytes(saved+b'changed')
        with self.assertRaisesRegex(CommandError,'inventory changed'):gate.assets(self.revision)
        self.assertEqual((target/'control/app.css').read_bytes(),saved+b'changed')
    def test_unknown_tree_or_symlink_or_interrupted_collection_is_retained(self):
        occupied=self.root/self.revision;occupied.mkdir(mode=0o755);(occupied/'unknown').write_text('keep')
        with self.assertRaises(FileNotFoundError):gate.assets(self.revision)
        self.assertEqual((occupied/'unknown').read_text(),'keep')
        with patch.object(gate,'call_command',side_effect=RuntimeError('interrupted')),self.assertRaisesRegex(RuntimeError,'interrupted'):gate.assets('2'*40)
        self.assertEqual(len(list(self.root.glob('.stage-*'))),1)
        path=Path(gate.assets('2'*40));(path/'bad').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(CommandError,'static member'):gate.verify_assets('2'*40)
    def test_unexpected_migrations_or_backwards_plan_are_refused(self):
        for name,backwards in [('0021_unreviewed',False),(gate.MIGRATIONS[0],True)]:
            executor=SimpleNamespace(loader=SimpleNamespace(check_consistent_history=lambda connection:None,applied_migrations={('control','0017_session_and_scope_integrity')},graph=SimpleNamespace(leaf_nodes=lambda:[])),
                migration_plan=lambda leaves:[(SimpleNamespace(name=name,app_label='control'),backwards)])
            with self.assertRaisesRegex(CommandError,'Unexpected migration plan'):gate.schema_plan(executor)

@override_settings(RUNNER_ENABLED=False)
class PrivateSchemaTests(TransactionTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.revision='3'*40
        suffix=uuid.uuid4().hex[:12];self.roles=['rmctest_'+name+'_'+suffix for name in ['web','exec','ai','backup']]
        with connection.cursor() as cursor:
            for role in self.roles:cursor.execute('CREATE ROLE '+connection.ops.quote_name(role)+' NOLOGIN')
        self.addCleanup(self.clean_roles)
        self.role_patch=patch.object(gate,'ROLES',self.roles);self.role_patch.start();self.addCleanup(self.role_patch.stop)
        self.root.chmod(0o755);self.static_patch=patch.object(gate,'STATIC',self.root);self.static_patch.start();self.addCleanup(self.static_patch.stop)
        self.read=Path.read_text
        def sql(path,*args,**kwargs):
            value=self.read(path,*args,**kwargs)
            if path.name=='runner-grants.sql':
                for original,role in zip(['resmgr_web','resmgr_exec','resmgr_ai','resmgr_backup'],self.roles):value=value.replace(original,role)
            return value
        self.sql_patch=patch.object(Path,'read_text',sql);self.sql_patch.start();self.addCleanup(self.sql_patch.stop)
    def clean_roles(self):
        with connection.cursor() as cursor:
            for role in self.roles:
                cursor.execute('DROP OWNED BY '+connection.ops.quote_name(role));cursor.execute('DROP ROLE '+connection.ops.quote_name(role))
    def command(self,operation):
        stream=io.StringIO();call_command('private_release',operation,revision=self.revision,stdout=stream);return json.loads(stream.getvalue())
    def test_additive_upgrade_and_retry_preserve_legacy_rows_and_rollback_keeps_schema(self):
        user,org,project=tenant('Upgrade preservation','upgrade-preservation@example.test')
        from control.models import User,Project,AuditEvent,Target
        ids=(user.pk,project.pk);count=AuditEvent.objects.count()
        executor=MigrationExecutor(connection);executor.migrate([('control','0017_session_and_scope_integrity')])
        self.assertTrue(self.command('prepare')['passed']);self.assertTrue(self.command('prepare')['passed'])
        self.assertTrue(User.objects.filter(pk=ids[0]).exists());self.assertTrue(Project.objects.filter(pk=ids[1]).exists());self.assertEqual(AuditEvent.objects.count(),count)
        self.assertTrue(self.command('rollback-check')['passed'])
        self.assertIn(('control',gate.MIGRATIONS[-1]),MigrationExecutor(connection).loader.applied_migrations)
        Target.objects.create(project=project,name='Retained customer route',kind='customer-runner')
        with self.assertRaisesRegex(CommandError,'Rollback incompatible'):self.command('rollback-check')
        self.assertTrue(Target.objects.filter(kind='customer-runner').exists());self.assertTrue(self.command('check')['passed'])
    def test_excess_privilege_and_mailbox_data_block_gates_without_deletion(self):
        self.command('prepare')
        with connection.cursor() as cursor:cursor.execute('GRANT UPDATE ON control_runnerchunk TO '+connection.ops.quote_name(self.roles[0]))
        with self.assertRaisesRegex(CommandError,'permissions differ'):self.command('check')
        with connection.cursor() as cursor:cursor.execute('REVOKE UPDATE ON control_runnerchunk FROM '+connection.ops.quote_name(self.roles[0]))
        from control.models import BuildRelease,Target
        _,_,project=tenant('Mailbox rollback','mailbox-rollback@example.test');target=Target.objects.create(project=project,name='Lab',kind='managed-lab')
        build=BuildRelease.objects.create(target=target,label='Retained mailbox build',manifest={'files':{'mailbox-v1-fixture':{}}})
        with self.assertRaisesRegex(CommandError,'Rollback incompatible'):self.command('rollback-check')
        self.assertTrue(BuildRelease.objects.filter(pk=build.pk).exists())
