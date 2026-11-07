"""Configured OpenSSH transport. Authentication stays in the operator's SSH files."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time

from .artifacts import atomic_write
from .contracts import HASH, Invalid, canonical, enum, integer, load, obj, require, text, version


class TransportError(Invalid):
    pass


class Unsupported(Invalid):
    pass


@dataclass(frozen=True)
class Target:
    name: str
    data: dict

    @classmethod
    def read(cls, name, path='config/target.local.json'):
        text(name)
        try:
            config = load(path)
            obj(config, 'kind schema_version targets', 'target configuration')
            version(config, 'target-configuration')
            require(type(config['targets']) is dict and 1 <= len(config['targets']) <= 16, 'targets: expected 1..16 named targets')
            require(name in config['targets'], 'target: unknown name ' + name + '; configure it locally')
            d = config['targets'][name]
            obj(d, 'ssh_alias ssh_config uid processor machine release recipe_id root timeout_s', 'target ' + name)
            require(type(d['ssh_alias']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', d['ssh_alias']), 'ssh_alias: unsafe alias')
            require(type(d['ssh_config']) is str and 1 <= len(d['ssh_config']) <= 4096 and '\x00' not in d['ssh_config'], 'ssh_config: expected local file path')
            integer(d['uid'], 0, 65535)
            enum(d['processor'], {'x86_64', 'aarch64'})
            require(type(d['machine']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', d['machine']), 'machine: invalid name')
            require(type(d['release']) is str and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', d['release']), 'release: expected major.minor.patch')
            text(d['recipe_id'], HASH)
            require(d['root'] == '/data/resmgrcheck', 'root: this native version requires /data/resmgrcheck')
            integer(d['timeout_s'], 1, 30)
            return cls(name, dict(d))
        except OSError as error:
            raise Invalid('target configuration unavailable: ' + str(path) + '; copy config/targets.example.json and set local routing') from error

    def public(self):
        return {k: self.data[k] for k in ('uid', 'processor', 'machine', 'release', 'recipe_id', 'root')}


class Transport:
    def __init__(self, target, record=None):
        self.target = target
        self.record = record if record is not None else []

    def _options(self):
        return ['-F', self.target.data['ssh_config'], '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectionAttempts=1',
                '-o', 'ConnectTimeout=' + str(self.target.data['timeout_s'])]

    def call(self, argv, *, data=None, timeout=None, exits=(0,)):
        timeout = self.target.data['timeout_s'] if timeout is None else timeout
        entry = {'argv': list(map(str, argv)), 'exit': None, 'error': None}
        self.record.append(entry)
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                       stdout=output, stderr=diagnostic)
            end = time.monotonic() + timeout
            try:
                first = True
                while True:
                    remaining = end - time.monotonic()
                    if remaining <= 0:
                        raise TransportError('transport_timeout: target response not established; recover the existing run ID')
                    try:
                        process.communicate(input=data if first else None, timeout=min(.05, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        first = False
                    require(output.tell() <= 32 * 1024 * 1024 and diagnostic.tell() <= 1024 * 1024, 'transport output exceeds bound')
                entry['exit'] = process.returncode
                require(diagnostic.tell() <= 1024 * 1024, 'transport diagnostic output exceeds bound')
                output.seek(0); raw = output.read(32 * 1024 * 1024 + 1)
                diagnostic.seek(0); detail = diagnostic.read(4096).decode('utf-8', errors='replace')
                if process.returncode not in exits:
                    entry['error'] = 'transport_command_failed'
                    raise TransportError('transport_command_failed: exit ' + str(process.returncode) + ('; ' + detail.strip() if detail else ''))
                require(len(raw) <= 32 * 1024 * 1024, 'transport output exceeds bound')
                return raw
            except BaseException as error:
                entry['error'] = type(error).__name__
                # Only this exact owned local SSH/SFTP child is terminated. Remote
                # persistent supervisors are neither guessed nor signalled here.
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
                entry['exit'] = process.returncode
                raise

    def ssh(self, command, **options):
        return self.call(['ssh', *self._options(), self.target.data['ssh_alias'], command], **options)

    def command(self, executable, *arguments, **options):
        return self.ssh(' '.join(shlex.quote(str(v)) for v in (executable, *arguments)), **options)

    def download(self, remote, local):
        return self.call(['scp', *self._options(), self.target.data['ssh_alias'] + ':' + remote, str(Path(local).resolve())])

    def upload(self, local, remote):
        return self.call(['scp', *self._options(), str(Path(local).resolve()), self.target.data['ssh_alias'] + ':' + remote])

    def save(self, path):
        atomic_write(Path(path), canonical(self.record) + b'\n')


def target_identity(transport):
    values = {}
    for key, command in [('processor', 'uname -p'), ('machine', 'uname -m'), ('release', 'uname -r'), ('uid', 'id -u')]:
        value = transport.ssh(command).decode('ascii').strip()
        values[key] = int(value) if key == 'uid' else value
    return values


def compatible(target, identity):
    for key in ('processor', 'machine', 'release', 'uid'):
        require(identity[key] == target.data[key], key + ': incompatible target (expected ' + str(target.data[key]) + ', observed ' + str(identity[key]) + ')')
    require(identity['processor'] == 'x86_64' and identity['release'].startswith('8.'), 'target: only QNX 8 x86_64 is qualified')
