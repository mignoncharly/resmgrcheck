"""Bounded secret-file validation, including systemd's root-owned read ACL.

The group mode bits of a POSIX ACL file encode its ACL mask, not necessarily
permissions granted to the owning group. Never treat 0440 alone as sufficient.
"""
from contextlib import contextmanager
import errno
import os
import pwd
from pathlib import Path
import stat
import struct

MAX_CREDENTIAL_BYTES = 4096
SYSTEMD_DIRECTORIES = {
    role: Path('/run/credentials/resmgrcheck-'+unit+'.service')
    for role, unit in [('web', 'web'), ('executor', 'executor'), ('ai', 'ai')]
}
SERVICE_USERS = {'web': 'resmgr-web', 'executor': 'resmgr-exec', 'ai': 'resmgr-ai'}
CREDENTIAL_IDS = {'RMC_WEB_SECRET_KEY': 'application-key', 'RMC_WEB_MFA_KEY': 'mfa-key'}
ACL_XATTR = 'system.posix_acl_access'


class CredentialError(ValueError):
    """Carries no credential contents or decoding fragments."""


def access_acl(descriptor):
    try:
        raw = os.getxattr(descriptor, ACL_XATTR)
    except OSError as error:
        if error.errno in {errno.ENODATA, errno.ENOTSUP}: return None
        raise CredentialError('Credential ACL unavailable') from None
    if len(raw) < 4 or (len(raw)-4) % 8 or struct.unpack_from('<I', raw)[0] != 2:
        raise CredentialError('Invalid credential ACL')
    return [tuple(entry) for entry in struct.iter_unpack('<HHI', raw[4:])]


def systemd_acl(uid, directory=False):
    permission = 5 if directory else 4  # read/search for directory; read for file
    undefined = 0xffffffff
    return [(1, permission, undefined), (2, permission, uid), (4, 0, undefined),
            (16, permission, undefined), (32, 0, undefined)]


@contextmanager
def open_file(filename):
    """Open through directory descriptors; refuse symlinks in every component."""
    path = Path(filename)
    if not path.is_absolute() or '..' in path.parts:
        raise CredentialError('Credential path must be absolute without traversal')
    # Ancestors need search permission, not directory-listing permission. O_PATH
    # pins them without adding a new read requirement to private-file validation.
    directory = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    descriptor = None
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory)
            os.close(directory); directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                             dir_fd=directory)
        yield descriptor, directory
    finally:
        if descriptor is not None: os.close(descriptor)
        os.close(directory)


def validate_descriptor(descriptor, directory, filename, name, role):
    info = os.fstat(descriptor)
    uid = os.geteuid()
    mode = stat.S_IMODE(info.st_mode)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid not in {0, uid} or
            info.st_nlink != 1 or not 0 <= info.st_size <= MAX_CREDENTIAL_BYTES):
        raise CredentialError('Credential file permissions/type invalid')
    acl = access_acl(descriptor)
    if mode in {0o400, 0o600} and acl is None:
        return
    # This exception is limited to systemd's known per-role directory and exact
    # credential ID. An environment variable or a 0440 mode alone grants no trust.
    expected_directory = SYSTEMD_DIRECTORIES.get(role)
    expected_id = CREDENTIAL_IDS.get(name)
    try: service_uid = pwd.getpwnam(SERVICE_USERS.get(role, '')).pw_uid
    except KeyError: service_uid = None
    if (uid == 0 or expected_directory is None or expected_id is None or
            uid != service_uid or
            Path(filename) != expected_directory/expected_id or
            os.environ.get('CREDENTIALS_DIRECTORY') != str(expected_directory) or
            info.st_uid != 0 or info.st_gid != 0 or mode != 0o440 or acl != systemd_acl(uid)):
        raise CredentialError('Credential file permissions/type invalid')
    parent = os.fstat(directory)
    if parent.st_uid != 0 or parent.st_gid != 0 or stat.S_IMODE(parent.st_mode) != 0o550:
        raise CredentialError('Systemd credential directory protection invalid')
    directory_reader = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=directory)
    try:
        if access_acl(directory_reader) != systemd_acl(uid, directory=True):
            raise CredentialError('Systemd credential directory protection invalid')
    finally: os.close(directory_reader)


def read_credential(filename, name, role):
    with open_file(filename) as (descriptor, directory):
        validate_descriptor(descriptor, directory, filename, name, role)
        raw = os.read(descriptor, MAX_CREDENTIAL_BYTES+1)
        if len(raw) > MAX_CREDENTIAL_BYTES:
            raise CredentialError('Credential exceeds size bound')
        if b'\0' in raw: raise CredentialError('Credential encoding invalid')
        try: return raw.decode('utf-8').strip()
        except UnicodeError: raise CredentialError('Credential encoding invalid') from None
