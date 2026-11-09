"""Actual loopback TLS + Django + customer client; not a separate customer host."""
from datetime import datetime,timedelta,timezone as tz
import contextlib,ipaddress,secrets,ssl,tempfile,threading
from pathlib import Path
from wsgiref.simple_server import make_server,WSGIRequestHandler
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.test import TransactionTestCase,override_settings
from django.core.handlers.wsgi import WSGIHandler
from django.db import connections
from customer_runner import protocol as wire
from customer_runner.client import Client,protected,create
from control import runners
from control.models import CustomerRunner
from .helpers import tenant
from .test_runners import discovery

class QuietHandler(WSGIRequestHandler):
    def log_message(self,*args):pass

def certificate(root):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.now(tz.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
        .sign(key,hashes.SHA256()))
    create(root/'tls-key',key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    create(root/'ca.pem',cert.public_bytes(serialization.Encoding.PEM))

@override_settings(RUNNER_ENABLED=True,RUNNER_SIGNING_KEY='c'*64,ALLOWED_HOSTS=['localhost'])
class RunnerTLSJourneyTests(TransactionTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        certificate(self.root);self.server=make_server('127.0.0.1',0,WSGIHandler(),handler_class=QuietHandler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.root/'ca.pem',self.root/'tls-key');self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.origin='https://localhost:'+str(self.server.server_port)
        self.settings=override_settings(RUNNER_ORIGIN=self.origin);self.settings.enable();self.addCleanup(self.settings.disable)
        self.thread=threading.Thread(target=self.serve,daemon=True);self.thread.start();self.addCleanup(self.stop)
        self.user,self.org,self.project=tenant('TLS customer','tls-runner@example.test')
        self.target,self.token=runners.issue(self.user,self.project,'TLS QNX discovery fixture')
        self.seed=secrets.token_hex(32)
        self.client=Client(self.origin,wire.public('c'*64),self.seed,str(self.target.pk),ca_file=str(self.root/'ca.pem'))

    def serve(self):
        try:self.server.serve_forever(poll_interval=.05)
        finally:connections.close_all()

    def stop(self):
        self.server.shutdown();self.thread.join(timeout=5);self.server.server_close()
        self.assertFalse(self.thread.is_alive())

    def test_real_tls_enrollment_approval_heartbeat_disconnect_and_revocation(self):
        result=self.client.enroll(self.token,discovery());self.assertEqual(result['state'],'pending-approval')
        runner=CustomerRunner.objects.select_related('target').get(pk=self.target.pk)
        runners.approve(self.user,self.target,runner.inventory_sha256)
        beat=self.client.exchange({'operation':'heartbeat','inventory':discovery()})
        self.assertEqual(beat['state'],'connected');self.assertFalse(beat['lifecycle_qualified_by_connection'])
        runner=CustomerRunner.objects.select_related('target').get(pk=self.target.pk)
        runner.last_seen-=timedelta(seconds=91);self.assertEqual(runners.status(runner),'disconnected')
        runners.revoke(self.user,self.target)
        with self.assertRaises(wire.ProtocolError):self.client.exchange({'operation':'heartbeat','inventory':discovery()})

    def test_untrusted_tls_and_wrong_control_plane_signing_key_fail_closed(self):
        untrusted=Client(self.origin,wire.public('c'*64),self.seed,str(self.target.pk))
        with self.assertRaises(wire.ProtocolError):untrusted.enroll(self.token,discovery())
        wrong=Client(self.origin,wire.public('d'*64),self.seed,str(self.target.pk),ca_file=str(self.root/'ca.pem'))
        with self.assertRaises(wire.ProtocolError):wrong.enroll(self.token,discovery())

    def test_customer_private_files_reject_symlinks_public_modes_and_overwrite(self):
        path=self.root/'local-key';create(path,b'private test fixture')
        self.assertEqual(protected(path),b'private test fixture')
        with self.assertRaises(FileExistsError):create(path,b'replace')
        link=self.root/'link';link.symlink_to(path)
        with self.assertRaises(wire.ProtocolError):protected(link)
        path.chmod(0o644)
        with self.assertRaises(wire.ProtocolError):protected(path)

    def test_real_tls_signed_job_and_recorded_evidence_ingestion_without_new_native_claim(self):
        from .runner_fixture import local
        from control.models import BuildRelease,Run
        from control.jobs import auth_fingerprint
        from control import runner_ingest
        from customer_runner import work
        from unittest.mock import patch
        import shutil
        source,request,configuration,inventory=local(self.root,self.target.pk,self.project.pk,self.org.pk)
        self.client.enroll(self.token,inventory)
        runner=CustomerRunner.objects.select_related('target').get(pk=self.target.pk)
        runners.approve(self.user,self.target,runner.inventory_sha256)
        self.client.exchange({'operation':'heartbeat','inventory':inventory})
        build=BuildRelease.objects.create(target=self.target,label='Recorded native fixture',manifest=request['deployment'],approved=True)
        run=Run.objects.create(project=self.project,target=self.target,build=build,actor=self.user,
            actor_auth_hash=auth_fingerprint(self.user),mfa_at=self.user.date_joined,native_run_id=request['run_id'],
            operation='run',profile='sensor',suite='profile',fixture_mode='fixed',idempotency_key='tls-recorded-evidence-only',intent_sha256='1'*64,state='queued')
        def recorded_copy(configuration,args,**kwargs):shutil.copytree(source,Path(args[args.index('--out')+1]));return 0
        with override_settings(MEDIA_ROOT=self.root/'sealed',PRIVATE_ROOT=self.root/'private'),patch.object(work,'storage',return_value={}),patch.object(work,'command',side_effect=recorded_copy):
            result=work.run_once(self.client,configuration,self.root,inventory)
            self.assertEqual(result['state'],'received');self.assertTrue(runner_ingest.execute(*runner_ingest.claim()))
        run.refresh_from_db();self.assertEqual(run.state,'completed');self.assertTrue(run.target_cleanup_verified)
        self.assertEqual(run.native_run_id,request['run_id'])
