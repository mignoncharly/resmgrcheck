#!/usr/bin/env python3
"""Create a new private lab configuration from explicit local routing and IFS bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resmgrcheck.transport import Target
from resmgrcheck.contracts import Invalid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='lab')
    parser.add_argument('--ssh-alias', required=True)
    parser.add_argument('--ssh-config', required=True, type=Path)
    parser.add_argument('--ifs', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=Path('config/target.local.json'))
    args = parser.parse_args()
    try:
        if not args.ssh_config.is_file() or not args.ifs.is_file():
            raise Invalid('SSH configuration and booted IFS must be existing local files')
        digest = hashlib.sha256()
        with args.ifs.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        value = {'kind': 'target-configuration', 'schema_version': 1, 'targets': {
            args.name: {'ssh_alias': args.ssh_alias, 'ssh_config': str(args.ssh_config.resolve()),
                        'uid': 0, 'processor': 'x86_64', 'machine': 'x86pc', 'release': '8.0.0',
                        'recipe_id': digest.hexdigest(), 'root': '/data/resmgrcheck', 'timeout_s': 8}}}
        # Validate using the product parser before creating the destination. The
        # temporary file contains routing metadata, never keys or license content.
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / 'target.json'
            candidate.write_text(json.dumps(value))
            Target.read(args.name, candidate)
        descriptor = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            json.dump(value, output, indent=2); output.write('\n')
        print('Created private configuration:', args.out)
        print('QNX compatibility, SSH trust and transfer still require doctor/deploy checks.')
        return 0
    except (Invalid, OSError) as error:
        print('Configuration not created:', str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
