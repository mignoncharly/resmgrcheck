"""Derived-cache validation never imports/unmarshals an untrusted pyc."""
import hashlib,importlib.util,json,os,py_compile,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import release_bytecode as cache
from https_checks import CheckFailed

class RetainedBytecodeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'module.py';self.raw=b'from __future__ import annotations\nraise RuntimeError("Never execute this cache")\n'
        self.source.write_bytes(self.raw);self.source.chmod(0o644);self.path=Path(py_compile.compile(str(self.source),doraise=True));self.path.chmod(0o640);self.path.parent.chmod(0o750)
    def git(self,argv):
        if 'ls-tree' in argv:
            return b'100644 blob '+b'0'*40+b'\tmodule.py\0' if argv[-1]=='module.py' else b''
        return self.raw
    def valid(self):
        with patch.object(cache.deployment,'command',side_effect=self.git):return cache.retained_caches(self.root,'5'*40,['__pycache__/'],set())
    def test_exact_compiled_source_is_preserved_without_import_or_unmarshal(self):
        before=(self.path.read_bytes(),self.path.stat().st_mtime_ns,self.path.stat().st_mode)
        with patch.object(cache.marshal,'loads',side_effect=AssertionError('No untrusted marshal load')):
            records=self.valid()
        self.assertEqual(len(records),1);self.assertEqual((self.path.read_bytes(),self.path.stat().st_mtime_ns,self.path.stat().st_mode),before)
    def test_modified_payload_or_header_rejected_without_repair(self):
        original=self.path.read_bytes()
        for modified in [original[:-1]+bytes([original[-1]^1]),b'bad!'+original[4:]]:
            self.path.write_bytes(modified)
            with self.assertRaises(CheckFailed):self.valid()
            self.assertEqual(self.path.read_bytes(),modified)
    def test_unknown_file_symlink_and_world_write_are_refused(self):
        unknown=self.path.parent/'unexpected';unknown.write_bytes(b'preserve unknown bytes')
        with self.assertRaises(CheckFailed):self.valid()
        self.assertEqual(unknown.read_bytes(),b'preserve unknown bytes');unknown.unlink()
        raw=self.path.read_bytes();self.path.unlink();self.path.symlink_to(self.source)
        with self.assertRaises(CheckFailed):self.valid()
        self.assertEqual(self.source.read_bytes(),self.raw);self.path.unlink();self.path.write_bytes(raw);self.path.chmod(0o666)
        with self.assertRaises(CheckFailed):self.valid()
    def test_isolated_Python_ignores_environment_but_B_prevents_writes(self):
        for args,expected in [(['-I'],b'False'),(['-I','-B'],b'True')]:
            output=subprocess.check_output([sys.executable,*args,'-c','import sys;print(sys.dont_write_bytecode)'],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(output.strip(),expected)
    def test_empty_tracked_source_is_valid(self):
        self.raw=b'';self.source.write_bytes(self.raw);py_compile.compile(str(self.source),doraise=True);self.path.chmod(0o640)
        self.assertEqual(len(self.valid()),1)
    def test_optimized_or_unknown_payload_is_not_accepted_under_plain_cache_tag(self):
        self.raw=b'assert False, "This check must remain in the trusted source"\n'
        self.source.write_bytes(self.raw);py_compile.compile(str(self.source),cfile=str(self.path),doraise=True,optimize=1);self.path.chmod(0o640)
        with self.assertRaisesRegex(CheckFailed,'payload_differs'):self.valid()
    def test_corrupted_or_executable_source_and_executable_cache_are_refused(self):
        self.source.write_bytes(self.raw+b'changed=1\n')
        with self.assertRaisesRegex(CheckFailed,'source_differs'):self.valid()
        self.source.write_bytes(self.raw);self.source.chmod(0o755)
        with self.assertRaisesRegex(CheckFailed,'source_mode_differs'):self.valid()
        self.source.chmod(0o644);py_compile.compile(str(self.source),doraise=True);self.path.chmod(0o755)
        with self.assertRaisesRegex(CheckFailed,'bytecode_protection'):self.valid()
    def test_untracked_cache_directory_and_directory_symlink_are_refused(self):
        directory=self.root/'unexpected/__pycache__';directory.mkdir(parents=True);directory.chmod(0o750);source=directory.parent/'module.py';source.write_bytes(self.raw);source.chmod(0o644)
        bytecode=Path(py_compile.compile(str(source),doraise=True));bytecode.chmod(0o640)
        with patch.object(cache.deployment,'command',side_effect=self.git),self.assertRaisesRegex(CheckFailed,'source_untracked'):
            cache.retained_caches(self.root,'5'*40,['unexpected/__pycache__/'],set())
        link=self.root/'linked';link.symlink_to(self.path.parent,target_is_directory=True)
        with patch.object(cache.deployment,'command',side_effect=self.git),self.assertRaises(CheckFailed):
            cache.retained_caches(self.root,'5'*40,['linked/'],set())

    @unittest.skipUnless(sys.version_info[:3]==(3,12,3),'Captured production serializer is CPython3.12.3')
    def test_exact_production_contracts_cache_hash_reproduced_without_import(self):
        repo=Path(__file__).resolve().parents[2]
        source=subprocess.check_output(['git','show','544f22c174ad48e1c8d741db0afdd3bf5b54f947:resmgrcheck/contracts.py'],cwd=repo)
        self.assertEqual(hashlib.sha256(source).hexdigest(),'6537b93f6662a0cf386b48dc02b6d62d0026d2d8d0eb6a4df16b3406c8de13b5')
        script='''import hashlib,importlib.util,json,struct,sys
sys.path.insert(0,sys.argv[1])
from release_bytecode import trusted_payloads
source=sys.stdin.buffer.read()
filename='/opt/resmgrcheck/releases/544f22c174ad48e1c8d741db0afdd3bf5b54f947/resmgrcheck/contracts.py'
cold,warm=trusted_payloads(source,filename)
header=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,1794212697,len(source))
print(json.dumps({'different':cold!=warm,'cold_bytes':len(cold),'warm_bytes':len(warm),'warm_sha256':hashlib.sha256(header+warm).hexdigest()}))
'''
        result=json.loads(subprocess.check_output([sys.executable,'-I','-B','-c',script,str(repo/'web/ops/production')],input=source))
        self.assertTrue(result['different']);self.assertEqual(result['cold_bytes'],46887);self.assertEqual(result['warm_bytes'],46902)
        self.assertEqual(result['warm_sha256'],'116ccaf3a6158dafae68f192f249286ce000275553c4eee0c67d2adc9c3084a1')
