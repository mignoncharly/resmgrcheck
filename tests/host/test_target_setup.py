"""Private config creation binds IFS bytes and preserves occupied destinations."""
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/configure-target.py'


class TargetSetupTests(unittest.TestCase):
    def test_exact_image_hash_permissions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); ssh = root/'ssh'; image = root/'ifs'; output = root/'target.json'
            ssh.write_text('Host owned-lab\n'); image.write_bytes(b'synthetic image identity only')
            args = [sys.executable, str(SCRIPT), '--ssh-alias', 'owned-lab', '--ssh-config', str(ssh),
                    '--ifs', str(image), '--out', str(output)]
            first = subprocess.run(args, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = json.loads(output.read_text())['targets']['lab']
            self.assertEqual(data['recipe_id'], hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            original = output.read_bytes()
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            for alias in ('-oProxyCommand=bad', 'bad;command'):
                changed = args.copy(); changed[changed.index('--ssh-alias')+1] = alias
                self.assertEqual(subprocess.run(changed, capture_output=True).returncode, 2)
                self.assertEqual(output.read_bytes(), original)

    def test_symlink_destination_preserves_referent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); ssh = root/'ssh'; image = root/'ifs'; keep = root/'keep'; output = root/'target'
            ssh.write_text('local routing'); image.write_bytes(b'synthetic'); keep.write_bytes(b'preserve')
            output.symlink_to(keep)
            result = subprocess.run([sys.executable, str(SCRIPT), '--ssh-alias', 'lab', '--ssh-config', str(ssh),
                                     '--ifs', str(image), '--out', str(output)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(keep.read_bytes(), b'preserve')
