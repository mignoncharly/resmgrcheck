"""Actual encrypted PostgreSQL backup/restore and hostile archive qualification."""
import io,json,os,tarfile,tempfile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from cryptography.exceptions import InvalidTag
from django.test import TransactionTestCase,SimpleTestCase,override_settings
from django.db import connection,connections,close_old_connections,OperationalError
from control.backup import EncryptWriter,decrypt,snapshot,restore_drill,media_lock
from control.engine import PolicyError
from control.models import AuditEvent
from .test_dashboard import DashboardTests

class ArchiveTests(SimpleTestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
        self.key=self.root/'key';self.key.write_bytes(os.urandom(32));self.key.chmod(0o600)
    def encrypted(self,raw):
        archive=self.root/'snapshot.rmc'
        with archive.open('wb') as stream:
            writer=EncryptWriter(stream,self.key.read_bytes());writer.write(raw);writer.finish()
        return archive
    def test_modified_ciphertext_or_tag_is_rejected_before_extraction(self):
        original=self.encrypted(b'private database payload').read_bytes()
        for index in [22,len(original)-1]:
            raw=bytearray(original);raw[index]^=1;archive=self.root/'damaged';archive.write_bytes(raw);destination=self.root/'decrypted'
            with self.assertRaises(InvalidTag):decrypt(archive,destination,self.key)
            self.assertFalse(destination.exists())
    def test_key_permissions_and_symlinks_are_denied(self):
        archive=self.encrypted(b'protected');self.key.chmod(0o644)
        with self.assertRaises(PolicyError):decrypt(archive,self.root/'decrypted',self.key)
        self.key.chmod(0o600);link=self.root/'link';link.symlink_to(self.key)
        with self.assertRaises(OSError):decrypt(archive,self.root/'decrypted',link)
    def test_authenticated_archive_still_cannot_extract_traversal_or_links(self):
        for kind in ['traversal','symlink']:
            body=io.BytesIO()
            with tarfile.open(fileobj=body,mode='w:') as archive:
                member=tarfile.TarInfo('../escape' if kind=='traversal' else 'evidence/link')
                if kind=='symlink':member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd'
                archive.addfile(member)
            encrypted=self.encrypted(body.getvalue())
            with override_settings(PRIVATE_ROOT=self.root),self.assertRaises(PolicyError):restore_drill(encrypted,self.key)
            self.assertFalse((self.root.parent/'escape').exists())

class PostgreSQLBackupTests(TransactionTestCase):
    setUp=DashboardTests.setUp
    recorded=DashboardTests.recorded
    def test_actual_snapshot_restore_preserves_data_evidence_and_audit_guards(self):
        run=self.recorded('after');AuditEvent.objects.create(actor=self.owner,organization=self.org,action='backup.test')
        with tempfile.TemporaryDirectory() as temporary,override_settings(PRIVATE_ROOT=Path(temporary)):
            root=Path(temporary);key=root/'key';key.write_bytes(os.urandom(32));key.chmod(0o600);archive=root/'checkpoint.rmc'
            saved=snapshot(archive,key);restored=restore_drill(archive,key)
            self.assertTrue(saved['passed']);self.assertEqual(saved['sealed_runs'],1);self.assertEqual(restored['restored_collected_executions'],1)
            self.assertEqual(saved['encrypted_sha256'],restored['encrypted_sha256']);self.assertTrue(restored['audit_update_denied'])
            self.assertFalse(restored['qnx_contacted']);self.assertEqual(run.__class__.objects.get(pk=run.pk).native_run_id,run.native_run_id)
            with self.assertRaises(PolicyError):snapshot(archive,key)
    def test_retention_cannot_obtain_exclusive_lock_during_snapshot(self):
        def retention_attempt():
            close_old_connections()
            try:
                with connection.cursor() as cursor:cursor.execute("SET lock_timeout='100ms'")
                try:
                    with media_lock():return 'unexpectedly-acquired'
                except OperationalError:return 'bounded-lock-denial'
            finally:connections.close_all()
        with media_lock(shared=True),ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual(pool.submit(retention_attempt).result(timeout=5),'bounded-lock-denial')

class OperationalStatusTests(TestCase):
    setUp=DashboardTests.setUp
    def test_a_receipt_without_an_archive_cannot_satisfy_backup_freshness(self):
        from django.utils import timezone
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);receipt=root/'missing.rmc.receipt.json'
            receipt.write_text(json.dumps({'passed':True,'created_at':timezone.now().isoformat(),'encrypted_sha256':'0'*64}));receipt.chmod(0o600)
            output=io.StringIO()
            with self.assertRaises(CommandError):call_command('operations_status',backup_dir=str(root),stdout=output)
            record=json.loads(output.getvalue());self.assertIsNone(record['backup_age_seconds']);self.assertIn('missing_or_stale_backup_receipt',record['concerns'])
            self.assertFalse(record['backup_receipt_is_restore_proof']);self.assertEqual(record['native_service_health'],'not_measured')
