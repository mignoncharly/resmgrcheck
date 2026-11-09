"""Bind customer-local effective SSH routing and public host-key trust; no upload."""
import hashlib,os,re,signal,stat,subprocess,tempfile,time
from pathlib import Path
from . import protocol as wire
from .client import protected


def public_hash(path,required=False):
    path=Path(path)
    wire.require(path.is_absolute() and '..' not in path.parts and not any(p.is_symlink() for p in [path,*path.parents]),'ssh_trust_path_invalid')
    try:descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:
        wire.require(not required,'ssh_trust_unavailable');return None
    try:
        before=os.fstat(descriptor)
        wire.require(stat.S_ISREG(before.st_mode) and before.st_uid in {0,os.geteuid()} and before.st_nlink==1 and
            not before.st_mode&0o022 and before.st_size<=1024**2,'ssh_trust_file_invalid')
        raw=os.read(descriptor,1024**2+1);after=os.fstat(descriptor)
        wire.require(len(raw)==before.st_size and len(raw)<=1024**2 and (before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
            (after.st_size,after.st_mtime_ns,after.st_ctime_ns),'ssh_trust_file_changed')
        wire.require(not required or raw.strip(),'ssh_trust_unavailable')
        return hashlib.sha256(raw).hexdigest() if raw.strip() else None
    finally:os.close(descriptor)


def effective(configuration,target):
    """ssh -G evaluates config without connecting. Retain neither stdout nor stderr."""
    from resmgrcheck.transport import Transport
    raw=protected(Path(target.data['ssh_config']))
    # A dedicated stable Host config is required. Match can depend on the remote
    # command; includes can conceal it. Neither can be proved by one -G evaluation.
    for line in raw.decode('utf-8').splitlines():
        key=re.match(r'\s*([a-zA-Z][a-zA-Z0-9]*)[\s=]',line)
        wire.require(not key or key[1].lower() not in {'match','include'},'ssh_dynamic_configuration_unsupported')
    argv=['/usr/bin/ssh','-G',*Transport(target)._options(),target.data['ssh_alias']]
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C.UTF-8'}
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as diagnostic:
        process=subprocess.Popen(argv,cwd=configuration['engine_root'],env=env,stdin=subprocess.DEVNULL,
            stdout=output,stderr=diagnostic,start_new_session=True)
        try:
            end=time.monotonic()+5
            while process.poll() is None:
                wire.require(output.tell()<=65536 and diagnostic.tell()<=16384,'ssh_configuration_bound')
                wire.require(time.monotonic()<end,'ssh_configuration_deadline');time.sleep(.02)
            wire.require(process.returncode==0 and output.tell()<=65536 and diagnostic.tell()<=16384,'ssh_configuration_invalid')
            output.seek(0);value=output.read(65537)
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.wait(timeout=2)
    rows={}
    for line in value.decode('utf-8').splitlines():
        key,separator,entry=line.partition(' ');key=key.lower()
        wire.require(separator and re.fullmatch('[a-z0-9]+',key) and entry,'ssh_configuration_invalid')
        rows.setdefault(key,[]).append(entry)
    def one(key,default=None):
        values=rows.get(key,[default]);wire.require(len(values)==1,'ssh_configuration_ambiguous');return values[0]
    required={'stricthostkeychecking':'true','batchmode':'yes','verifyhostkeydns':'false',
        'canonicalizehostname':'false','controlmaster':'false','forwardagent':'no','forwardx11':'no','permitlocalcommand':'no'}
    wire.require(all(one(key)==expected for key,expected in required.items()),'ssh_security_configuration_invalid')
    wire.require(all(one(key,'none')=='none' for key in ['knownhostscommand','controlpath','remotecommand']),
        'ssh_dynamic_trust_or_multiplexing_unsupported')
    wire.require(not any(key in rows for key in ['localforward','remoteforward','dynamicforward']),'ssh_forwarding_unsupported')
    files={};available=False
    for key in ['userknownhostsfile','globalknownhostsfile']:
        names=one(key,'none').split()
        wire.require(1<=len(names)<=8,'ssh_trust_file_bound')
        for name in names:
            if name=='none':continue
            wire.require('%' not in name and '$' not in name,'ssh_trust_path_tokens_unsupported')
            path=Path(name).expanduser()
            if not path.is_absolute():path=Path(configuration['engine_root'])/path
            digest=public_hash(path);files[str(path)]=digest;available|=digest is not None
    wire.require(available,'ssh_trust_unavailable')
    revoked=one('revokedhostkeys','none')
    if revoked!='none':
        wire.require('%' not in revoked and '$' not in revoked,'ssh_trust_path_tokens_unsupported')
        path=Path(revoked).expanduser()
        if not path.is_absolute():path=Path(configuration['engine_root'])/path
        files['revoked:'+str(path)]=public_hash(path,required=True)
    return {'effective_sha256':hashlib.sha256(value).hexdigest(),'public_trust_sha256':wire.fingerprint(files)}
