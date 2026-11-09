"""Derived-cache validation never imports/unmarshals an untrusted pyc."""
import importlib.util,os,py_compile,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import release_bytecode as cache
from https_checks import CheckFailed

class RetainedBytecodeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'module.py';self.raw=b'from __future__ import annotations\nraise RuntimeError("Never execute this cache")\n'
        self.source.write_bytes(self.raw);self.path=Path(py_compile.compile(str(self.source),doraise=True));self.path.chmod(0o640);self.path.parent.chmod(0o750)
    def valid(self):
        with patch.object(cache.deployment,'command',return_value=self.raw):return cache.retained_caches(self.root,'5'*40,['__pycache__/'],set())
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
