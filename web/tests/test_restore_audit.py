"""Real encrypted pg_dump/pg_restore audit checks. All mutation probes use new DBs."""
import io,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
import psycopg
from django.conf import settings
from django.db import connection
from django.core.management import call_command
from django.test import TransactionTestCase,override_settings
from control import backup
from control.engine import PolicyError
from control.models import AuditEvent


class RestoredAuditTests(TransactionTestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.key=self.root/'key';self.key.write_bytes(os.urandom(32));self.key.chmod(0o600)
        self.override=override_settings(PRIVATE_ROOT=self.root,MEDIA_ROOT=self.root/'evidence');self.override.enable();self.addCleanup(self.override.disable)
        self.archive=self.root/'snapshot.rmc';self.names=[];self.pg_calls=[];self.original_pg=backup.pg

    def save(self):
        result=backup.snapshot(self.archive,self.key);self.archive_digest=result['encrypted_sha256']
        with connection.cursor() as cursor:self.source_identity=backup.identity(cursor)

    def connect(self,name):
        env=backup.pg_env()
        return psycopg.connect(dbname=name,host=env['PGHOST'],port=env['PGPORT'],user=env['PGUSER'],
            autocommit=True,connect_timeout=5,options=env['PGOPTIONS'])

    def run_restore(self,diagnostic=False,after_restore=None,before_drop=None):
        def pg(tool,args,**kwargs):
            self.pg_calls.append((tool,args))
            if tool=='createdb':
                name=args[-1];self.assertRegex(name,r'^resmgrcheck_restore_[0-9a-f]{12}$')
                self.assertNotEqual(name,settings.DATABASES['default']['NAME']);self.names.append(name)
            if tool=='dropdb' and before_drop:before_drop(args[-1])
            result=self.original_pg(tool,args,**kwargs)
            if tool=='pg_restore' and after_restore:after_restore(args[args.index('--dbname')+1])
            return result
        with patch.object(backup,'pg',side_effect=pg):
            return backup.restore_drill(self.archive,self.key,diagnostic_only=diagnostic)

    def preserved(self):
        self.assertEqual(backup.digest_file(self.archive),self.archive_digest)
        with connection.cursor() as cursor:
            self.assertEqual(backup.identity(cursor),self.source_identity)
            for name in self.names:
                cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s',[name]);self.assertEqual(cursor.fetchone()[0],0)
        self.assertEqual(self.pg_calls.count(('dropdb',['-w',self.names[-1]])),1)
        self.assertTrue(all(args==['-w',args[-1]] and args[-1] in self.names for tool,args in self.pg_calls if tool=='dropdb'))

    def test_empty_restored_table_old_update_is_zero_but_new_probe_proves_both_guards(self):
        self.assertEqual(AuditEvent.objects.count(),0);self.save();observed={}
        def old_check(name):
            with self.connect(name) as restored:
                observed.update(backup.restored_audit_metadata(restored))
                with restored.transaction(force_rollback=True):
                    with restored.cursor() as cursor:
                        cursor.execute('UPDATE public.control_auditevent SET action=action WHERE id=(SELECT id FROM public.control_auditevent LIMIT 1)')
                        observed['old_update_rowcount']=cursor.rowcount
        result=self.run_restore(after_restore=old_check)
        self.assertEqual(observed['audit_rows'],0);self.assertEqual(observed['old_update_rowcount'],0)
        self.assertTrue(observed['function_definition_matches']);self.assertTrue(observed['trigger_definition_matches']);self.assertEqual(observed['trigger_enabled'],'O')
        self.assertTrue(result['passed']);self.assertTrue(result['audit_update_denied']);self.assertTrue(result['audit_delete_denied'])
        self.assertTrue(result['audit_probe_rolled_back']);self.assertEqual(result['audit_rows_after_rollback'],0);self.preserved()

    def test_populated_restored_table_uses_only_a_new_synthetic_row(self):
        event=AuditEvent.objects.create(action='fixture.original',object_id='private-fixture',details={'sensitive':'not-returned'})
        self.save();result=self.run_restore()
        self.assertEqual(result['audit_metadata']['audit_rows'],1);self.assertEqual(result['audit_rows_after_rollback'],1)
        self.assertEqual(AuditEvent.objects.get(pk=event.pk).object_id,'private-fixture')
        self.assertNotIn('private-fixture',json.dumps(result));self.assertNotIn('not-returned',json.dumps(result));self.preserved()

    def test_inspection_reports_metadata_without_mutation_or_false_pass(self):
        self.save()
        with patch.object(backup,'prove_restored_audit',side_effect=AssertionError('No probe in diagnostic mode')):
            result=self.run_restore(diagnostic=True)
        self.assertFalse(result['passed']);self.assertTrue(result['diagnostic_only']);self.assertFalse(result['audit_behavior_tested'])
        self.assertEqual(result['audit_metadata']['audit_rows'],0);self.assertTrue(result['audit_metadata']['function_present']);self.preserved()

    def test_missing_disabled_replica_or_wrong_function_trigger_never_passes(self):
        self.save()
        changes=[
            'DROP TRIGGER control_audit_no_update_delete ON public.control_auditevent',
            'ALTER TABLE public.control_auditevent DISABLE TRIGGER control_audit_no_update_delete',
            'ALTER TABLE public.control_auditevent ENABLE REPLICA TRIGGER control_audit_no_update_delete',
            'DROP FUNCTION public.control_audit_append_only() CASCADE',
            "CREATE OR REPLACE FUNCTION public.control_audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$"]
        for sql in changes:
            with self.subTest(change=sql.split()[0:4]):
                def tamper(name):
                    with self.connect(name) as restored:restored.execute(sql)
                with self.assertRaisesRegex(PolicyError,'backup_restored_audit_metadata_invalid'):
                    self.run_restore(after_restore=tamper)
                self.preserved()

    def test_when_filtered_trigger_is_not_the_restored_definition(self):
        self.save()
        def tamper(name):
            with self.connect(name) as restored:
                restored.execute('DROP TRIGGER control_audit_no_update_delete ON public.control_auditevent')
                restored.execute('CREATE TRIGGER control_audit_no_update_delete BEFORE UPDATE OR DELETE ON public.control_auditevent FOR EACH ROW WHEN (false) EXECUTE FUNCTION public.control_audit_append_only()')
        with self.assertRaisesRegex(PolicyError,'backup_restored_audit_metadata_invalid'):self.run_restore(after_restore=tamper)
        self.preserved()

    def test_metadata_alone_cannot_replace_the_behavioral_test_and_failed_probe_rolls_back(self):
        self.save();metadata={};read_metadata=backup.restored_audit_metadata
        def tamper(name):
            with self.connect(name) as restored:
                metadata.update(read_metadata(restored))
                restored.execute('DROP TRIGGER control_audit_no_update_delete ON public.control_auditevent')
        def rolled_back(name):
            with self.connect(name) as restored:
                self.assertEqual(restored.execute('SELECT count(*) FROM public.control_auditevent').fetchone()[0],0)
        with patch.object(backup,'restored_audit_metadata',side_effect=lambda restored:dict(metadata)):
            with self.assertRaisesRegex(PolicyError,'backup_restored_audit_trigger_unproven'):
                self.run_restore(after_restore=tamper,before_drop=rolled_back)
        self.preserved()

    def test_permission_error_is_not_accepted_as_an_append_only_trigger(self):
        self.save()
        def tamper(name):
            with self.connect(name) as restored:
                restored.execute("CREATE FUNCTION public.fixture_denial() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Audit events are append-only'; END; $$")
                restored.execute('CREATE TRIGGER aaa_fixture_denial BEFORE UPDATE ON public.control_auditevent FOR EACH ROW EXECUTE FUNCTION public.fixture_denial()')
        with self.assertRaisesRegex(PolicyError,'backup_restored_audit_trigger_unexpected'):self.run_restore(after_restore=tamper)
        self.preserved()

    def test_restore_failure_drops_only_the_database_it_created(self):
        self.save();original=self.original_pg
        def fail(tool,args,**kwargs):
            if tool=='pg_restore':raise PolicyError('backup_pg_restore_failed')
            return original(tool,args,**kwargs)
        self.original_pg=fail
        with self.assertRaisesRegex(PolicyError,'backup_pg_restore_failed'):self.run_restore()
        self.preserved()

    def test_createdb_failure_never_drops_an_unowned_database(self):
        self.save();original=self.original_pg
        def fail(tool,args,**kwargs):
            if tool=='createdb':raise PolicyError('backup_createdb_failed')
            return original(tool,args,**kwargs)
        self.original_pg=fail
        with self.assertRaisesRegex(PolicyError,'backup_createdb_failed'):self.run_restore()
        self.assertFalse(any(tool=='dropdb' for tool,args in self.pg_calls))
        self.assertEqual(backup.digest_file(self.archive),self.archive_digest)

    def test_tampered_archive_never_creates_a_database(self):
        self.save();raw=bytearray(self.archive.read_bytes());raw[-1]^=1;self.archive.write_bytes(raw)
        with patch.object(backup,'pg',side_effect=AssertionError('No DB before authentication')):
            from cryptography.exceptions import InvalidTag
            with self.assertRaises(InvalidTag):backup.restore_drill(self.archive,self.key)

    def test_probe_refuses_the_source_database_before_any_modification(self):
        self.save()
        env=backup.pg_env()
        with self.connect(env['PGDATABASE'] if 'PGDATABASE' in env else settings.DATABASES['default']['NAME']) as source:
            with self.assertRaisesRegex(PolicyError,'requires_isolated_restore'):backup.prove_restored_audit(source,settings.DATABASES['default']['NAME'])
            with self.assertRaisesRegex(PolicyError,'database_mismatch'):backup.prove_restored_audit(source,'resmgrcheck_restore_'+'0'*12)
        self.assertEqual(AuditEvent.objects.count(),0)

    def test_missing_function_is_reported_by_inspection_without_a_pass(self):
        self.save()
        def tamper(name):
            with self.connect(name) as restored:restored.execute('DROP FUNCTION public.control_audit_append_only() CASCADE')
        result=self.run_restore(diagnostic=True,after_restore=tamper)
        self.assertFalse(result['passed']);self.assertFalse(result['audit_behavior_tested'])
        self.assertFalse(result['audit_metadata']['function_present']);self.assertFalse(result['audit_metadata']['trigger_present']);self.preserved()

    def test_cleanup_failure_is_not_returned_as_restore_success(self):
        self.save();original=self.original_pg;left=[]
        def fail(tool,args,**kwargs):
            if tool=='dropdb':left.append(args[-1]);raise PolicyError('backup_dropdb_failed')
            return original(tool,args,**kwargs)
        self.original_pg=fail
        try:
            with self.assertRaisesRegex(PolicyError,'backup_dropdb_failed'):self.run_restore()
        finally:
            for name in left:original('dropdb',['-w',name])  # only this test's known created DB
        self.preserved()

    def test_cli_inspection_and_restore_are_explicit_and_keep_operator_guard(self):
        for operation,diagnostic in [('inspect-restore',True),('restore-drill',False)]:
            output=io.StringIO()
            with patch('control.management.commands.backup_snapshot.restore_drill',return_value={'passed':not diagnostic,'diagnostic_only':diagnostic}) as restore:
                call_command('backup_snapshot',operation,archive=str(self.archive),key_file=str(self.key),stdout=output)
            restore.assert_called_once_with(str(self.archive),str(self.key),diagnostic_only=diagnostic)
            self.assertEqual(json.loads(output.getvalue())['passed'],not diagnostic)
