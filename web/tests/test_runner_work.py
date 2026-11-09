"""Durable journal/partial upload tests. Saved evidence is never new native activity."""
import base64,hashlib,json,shutil,tempfile,time,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from customer_runner import work,protocol as wire
from .runner_fixture import local

class RunnerWorkTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source,self.record,self.configuration,self.inventory=local(self.root,uuid.uuid4(),uuid.uuid4(),uuid.uuid4())
        self.identifier=str(uuid.uuid4());self.ticket=str(uuid.uuid4());self.calls=[];self.remote_chunks={};self.failed=False
        self.job={'run_id':self.identifier,'native_run_id':self.record['run_id'],'target_id':self.configuration['target_id'],
            'project_id':self.configuration['project_id'],'organization_id':self.configuration['organization_id'],
            'inventory_sha256':wire.fingerprint(self.inventory),'operation':'run','profile':'sensor','suite':'profile','fixture_mode':'fixed',
            'build':self.record['deployment'],'intent_sha256':'1'*64,'original_native_run_id':None}
        self.offer={'state':'connected','job':self.job,'ticket':self.ticket,'job_state':'offered','launch_allowed':False}

    def exchange(self,body):
        operation=body['operation'];self.calls.append(operation)
        if operation=='poll':return self.offer
        if operation=='begin':
            self.offer['job_state']='launch-authorized'
            return {'launch_allowed':True,'run_id':self.identifier,'native_run_id':self.record['run_id'],'intent_sha256':'1'*64,'grant_expires_at':int(time.time())+30}
        if operation=='chunk':
            self.offer['job_state']='receiving';raw=base64.b64decode(body['data']);index=body['index']
            if index in self.remote_chunks:self.assertEqual(raw,self.remote_chunks[index])
            self.remote_chunks[index]=raw
            # Lose one acknowledgement after storage, not the authenticated bytes.
            if index==0 and not self.failed:
                self.failed=True;raise wire.ProtocolError('fixture connection lost')
            return {'chunk_stored':index,'sha256':hashlib.sha256(raw).hexdigest()}
        if operation=='finish':self.offer['job_state']='received';return {'job_state':'received'}
        return {}

    def test_lost_upload_ack_resumes_same_archive_without_native_relaunch_or_recollection(self):
        client=SimpleNamespace(exchange=self.exchange)
        def recorded_copy(configuration,args,**kwargs):shutil.copytree(self.source,Path(args[args.index('--out')+1]));return 0
        with patch.object(work,'storage',return_value={}),patch.object(work,'command',side_effect=recorded_copy) as command:
            with self.assertRaises(wire.ProtocolError):work.run_once(client,self.configuration,self.root,self.inventory)
            journal=self.root/('job-'+self.identifier);saved=(journal/'upload.json').read_bytes()
            self.assertEqual(command.call_count,1);self.assertEqual(self.calls.count('begin'),1)
            result=work.run_once(client,self.configuration,self.root,self.inventory)
            self.assertEqual(result['state'],'received');self.assertEqual(command.call_count,1)
            self.assertEqual(self.calls.count('begin'),1);self.assertEqual(saved,(journal/'upload.json').read_bytes())
            self.assertEqual(self.calls.count('uncertain'),1)
            self.assertEqual(work.run_once(client,self.configuration,self.root,self.inventory)['state'],'received')
            self.assertEqual(command.call_count,1)

    def test_remote_job_cannot_switch_target_build_profile_or_local_route(self):
        for name,value in [('target_id',str(uuid.uuid4())),('profile','../../etc/passwd'),('fixture_mode','drop-job')]:
            changed=dict(self.job);changed[name]=value
            with self.assertRaises(wire.ProtocolError):work.validate(self.configuration,self.inventory,changed)
        (self.root/'ssh-config').write_text('Host changed\n')
        with self.assertRaises(wire.ProtocolError):work.validate(self.configuration,self.inventory,self.job)

    def test_storage_preflight_is_fixed_read_only_and_refuses_unknown_or_low_budget(self):
        from customer_runner.agent import storage
        with patch('resmgrcheck.transport.Transport.ssh',return_value=b'Files: 3072 total 500 avail\nBlocks: 4000 total 1000 avail') as ssh:
            self.assertEqual(storage(self.configuration,'lifecycle')['free_entries'],500)
            ssh.assert_called_once_with('df -g /data')
        for raw in [b'unknown',b'Files: 3072 total 31 avail\nBlocks: 4000 total 1000 avail',b'Files: 3072 total 500 avail\nBlocks: 4000 total 100 avail']:
            with patch('resmgrcheck.transport.Transport.ssh',return_value=raw),self.assertRaises(wire.ProtocolError):storage(self.configuration,'profile')
