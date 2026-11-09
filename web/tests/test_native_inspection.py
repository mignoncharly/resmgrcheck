"""Diagnostic metadata only; actual read-only PostgreSQL, modeled service state."""
import json,os,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch,Mock
from django.test import TransactionTestCase,override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from control.models import User,Organization,Project,Target,BuildRelease,Run,AccessCode,AccessSession,AccessGrant,AuditEvent
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import inspect_native_acceptance as probe
import acceptance_operator as acceptance
import executor_operator as operator
from executor_native_browser import NativeJourney,failure_check

class SafeInspectionFilesTests(unittest.TestCase):
    def test_observer_check_names_are_retained_without_arbitrary_exception_text(self):
        self.assertEqual(operator.observer_failure(ValueError('native_cleanup_unproven')),
            {'error_class':'ValueError','failed_check':'native_cleanup_unproven'})
        for error in [ValueError('PRIVATE-SSH-DIAGNOSTIC'),OSError('PRIVATE-PATH')]:
            self.assertEqual(operator.observer_failure(error)['failed_check'],'unclassified')
            self.assertNotIn('PRIVATE',json.dumps(operator.observer_failure(error)))

    def test_terminal_collection_failure_records_only_safe_state_and_preserves_verdict(self):
        journey=NativeJourney('https://qnx-resmgrcheck.gestionatech.de',Path('/tmp'),{'native':{}})
        page=Mock();page.context.request.get.return_value.status=200
        page.context.request.get.return_value.json.return_value={'native_run_id':'w274989f6c30645818f','state':'blocked',
            'cleanup_verified':False,'evidence_integrity':'verified','summary':{'cases':[{'verdict':'ERROR'}]},'private':'PRIVATE-SSH-DETAIL'}
        row={'web_run_id':probe.RUN,'native_run_id':'w274989f6c30645818f','profile':'sensor','status':'pending'}
        with patch.object(journey,'checkpoint') as checkpoint,self.assertRaises(AssertionError) as caught:
            journey.wait(page,row,'FAIL')
        self.assertEqual(failure_check(caught.exception),'native_or_cleanup_not_complete');checkpoint.assert_called_once()
        self.assertEqual(row['last_observation'],{'state':'blocked','cleanup_verified':False,'evidence_integrity':'verified','verdicts':['ERROR']})
        self.assertEqual(row['status'],'pending');self.assertNotIn('PRIVATE',json.dumps(row))
        self.assertEqual(failure_check(AssertionError('PRIVATE-DIAGNOSTIC')),'unclassified')

    def test_failed_evidence_with_null_summary_remains_a_collection_failure(self):
        journey=NativeJourney('https://qnx-resmgrcheck.gestionatech.de',Path('/tmp'),{'native':{}})
        page=Mock();page.context.request.get.return_value.status=200
        page.context.request.get.return_value.json.return_value={'native_run_id':'w274989f6c30645818f','state':'completed',
            'cleanup_verified':False,'evidence_integrity':'failed','summary':None}
        row={'web_run_id':probe.RUN,'native_run_id':'w274989f6c30645818f','profile':'sensor'}
        with patch.object(journey,'checkpoint'),self.assertRaises(AssertionError) as caught:journey.wait(page,row,'FAIL')
        self.assertEqual(failure_check(caught.exception),'native_or_cleanup_not_complete')
        self.assertEqual(row['last_observation']['evidence_integrity'],'failed');self.assertEqual(row['last_observation']['verdicts'],[])

    def test_private_payload_never_in_metadata_and_known_error_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'partial-events.jsonl'
            path.write_bytes(b'PRIVATE CONTENT MUST NOT APPEAR');path.chmod(0o600)
            row=probe.file_metadata(path,root,os.getuid())
            self.assertEqual(row['read_validation'],'passed');self.assertNotIn('PRIVATE',json.dumps(row))
            self.assertEqual(probe.safe_error(ValueError('resource_protection')),'resource_protection')
            self.assertEqual(probe.safe_error(ValueError('secret-value')),'ValueError')
            path.chmod(0o666);self.assertEqual(probe.file_metadata(path,root,os.getuid())['read_validation'],'resource_protection')

    def test_no_follow_metadata_reports_symlink_or_wrong_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);target=root/'source';target.write_bytes(b'secret');target.chmod(0o600)
            alias=root/'alias';alias.symlink_to(target)
            row=probe.file_metadata(alias,root,os.getuid())
            self.assertTrue(row['symlink']);self.assertEqual(row['read_validation'],'resource_symlink')
            self.assertEqual(probe.file_metadata(target,root,os.getuid()+1)['read_validation'],'resource_protection')

class ReadOnlyNativeInspectionTests(TransactionTestCase):
    def test_exact_run_inspection_is_read_only_and_no_target_or_service_mutations(self):
        self.assertTrue(connection.settings_dict['NAME'].startswith('test_'))
        account=User.objects.create_user('accept-'+probe.ATTEMPT[:18],None,is_active=False)
        org=Organization.objects.create(pk=probe.plan.IDS['organization'],name='Fixture')
        project=Project.objects.create(pk=probe.plan.IDS['project'],organization=org,name='Fixture',created_by=account)
        target=Target.objects.create(pk=probe.plan.IDS['target'],project=project,name='Fixture',state='available')
        build=BuildRelease.objects.create(pk=probe.plan.IDS['before'],target=target,label='Fixture')
        now=timezone.now()
        code=AccessCode.objects.create(organization=org,created_by=account,verifier='0'*64,revoked_at=now)
        AccessGrant.objects.create(code=code,project=project,can_run=True)
        session=AccessSession.objects.create(code=code,browser_key_hash='0'*64,policy_version=1,last_access=now,expires_at=now,revoked_at=now)
        Run.objects.create(pk=probe.RUN,project=project,target=target,build=build,access_session=session,actor_auth_hash='0'*64,
            mfa_at=now,native_run_id='w274989f6c30645818f',operation='run',idempotency_key='fixture-inspection',intent_sha256='0'*64,
            state='completed',target_cleanup_verified=True)
        AuditEvent.objects.create(actor=account,action='https.acceptance.created',details={'acceptance_id':str(uuid.UUID(probe.ATTEMPT))})
        def inventory(run):
            with connection.cursor() as cursor:
                cursor.execute('SHOW transaction_read_only');self.assertEqual(cursor.fetchone(),('on',))
        with tempfile.TemporaryDirectory() as temporary,override_settings(MEDIA_ROOT=Path(temporary)),\
            patch.object(acceptance,'load_application'),patch.object(probe.ops,'read',return_value=json.dumps({'driver_revision':probe.DRIVER}).encode()),\
            patch.object(probe.ops,'command',return_value=b'active') as commands,patch.object(probe.ops.Client,'request',return_value=(200,{},b'{"status":"ready"}')),\
            patch('control.storage.verify_inventory',side_effect=inventory),CaptureQueriesContext(connection) as queries:
            result=probe.inspect()
        self.assertTrue(result['read_only']);self.assertTrue(result['HTTPS_readiness_200']);self.assertEqual(result['inventory'],'passed')
        self.assertTrue(result['cleanup']['all_codes_revoked']);self.assertEqual(result['run']['web_run_id'],probe.RUN)
        self.assertEqual(len(commands.call_args_list),4)
        for call in commands.call_args_list:self.assertEqual(call.args[0][:2],['systemctl','is-active'])
        for query in queries:
            self.assertFalse(query['sql'].lstrip().split()[0].upper() in {'UPDATE','INSERT','DELETE','GRANT','ALTER','CREATE','DROP'})
        self.assertEqual(Run.objects.count(),1);self.assertEqual(AuditEvent.objects.count(),1)
