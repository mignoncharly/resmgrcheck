"""Real local ssh -G, dummy public pins; no network or native observations."""
import os,tempfile,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from customer_runner import trust,work,protocol as wire
from customer_runner.agent import route_fingerprint
from .runner_fixture import local

class RunnerTrustTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source,self.record,self.config,self.inventory=local(self.root,uuid.uuid4(),uuid.uuid4(),uuid.uuid4())
        self.ssh=self.root/'ssh-config';self.original=self.ssh.read_text();self.pins=self.root/'known-hosts'
    def test_effective_ssh_and_public_pin_contents_bind_route_without_remote_connection(self):
        before=route_fingerprint(self.config)
        with patch('resmgrcheck.transport.Transport.ssh',side_effect=AssertionError('No connection')):
            self.assertEqual(route_fingerprint(self.config),before)
        self.pins.write_text('fixture-only ssh-ed25519 ANOTHERPUBLICFIXTURE\n')
        self.assertNotEqual(route_fingerprint(self.config),before)
        self.ssh.write_text(self.original+' HostKeyAlias alternate-fixture\n')
        self.assertNotEqual(route_fingerprint(self.config),before)
    def test_missing_dynamic_unpinned_or_forwarded_trust_is_refused(self):
        for directive in ['Include /etc/ssh/ssh_config','Match all','KnownHostsCommand /bin/true',
                'VerifyHostKeyDNS yes','ControlMaster auto','ControlPath /tmp/shared-control',
                'CanonicalizeHostname yes','LocalForward 127.0.0.1:9000 127.0.0.1:9001',
                'ForwardAgent yes','PermitLocalCommand yes','UserKnownHostsFile /dev/null']:
            # UserKnownHostsFile must precede the original stanza: first value wins.
            self.ssh.write_text('Host fixture-only\n '+directive+'\n'+self.original)
            with self.subTest(directive=directive),self.assertRaises(wire.ProtocolError):route_fingerprint(self.config)
        self.ssh.write_text(self.original);self.pins.unlink()
        with self.assertRaisesRegex(wire.ProtocolError,'trust_unavailable'):route_fingerprint(self.config)
    def test_public_files_allow_readable_modes_but_reject_writes_links_types_owners_and_size(self):
        for mode in [0o400,0o440,0o600,0o644]:
            self.pins.chmod(mode);self.assertEqual(len(trust.public_hash(self.pins)),64)
        self.pins.chmod(0o666)
        with self.assertRaisesRegex(wire.ProtocolError,'file_invalid'):trust.public_hash(self.pins)
        self.pins.chmod(0o600);other=self.root/'hardlink';os.link(self.pins,other)
        with self.assertRaises(wire.ProtocolError):trust.public_hash(self.pins)
        other.unlink();self.pins.write_bytes(b'x'*(1024**2+1))
        with self.assertRaises(wire.ProtocolError):trust.public_hash(self.pins)
        self.pins.write_bytes(b'PUBLICFIXTURE')
        actual=self.pins.stat();fake=SimpleNamespace(**{name:getattr(actual,name) for name in ['st_mode','st_uid','st_nlink','st_size','st_mtime_ns','st_ctime_ns']});fake.st_uid=987654
        with patch.object(trust.os,'fstat',return_value=fake),self.assertRaises(wire.ProtocolError):trust.public_hash(self.pins)
        other.symlink_to(self.pins)
        with self.assertRaises(wire.ProtocolError):trust.public_hash(other)
        fifo=self.root/'fifo';os.mkfifo(fifo,0o600)
        with self.assertRaises(wire.ProtocolError):trust.public_hash(fifo)
    def test_trust_drift_prevents_a_job_before_any_launch_grant(self):
        job={'run_id':str(uuid.uuid4()),'native_run_id':self.record['run_id'],'target_id':self.config['target_id'],
            'project_id':self.config['project_id'],'organization_id':self.config['organization_id'],
            'inventory_sha256':wire.fingerprint(self.inventory),'operation':'run','profile':'sensor','suite':'profile','fixture_mode':'fixed',
            'build':self.record['deployment'],'intent_sha256':'1'*64,'original_native_run_id':None}
        work.validate(self.config,self.inventory,job)
        self.pins.write_text('fixture-only ssh-ed25519 CHANGEDPUBLICFIXTURE\n')
        with self.assertRaisesRegex(wire.ProtocolError,'job_route_changed'):work.validate(self.config,self.inventory,job)
