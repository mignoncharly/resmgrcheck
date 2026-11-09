"""Bounded regular-file native evidence only. No executables, secrets or tar metadata."""
import ctypes,io,os,re,stat,tarfile
from pathlib import Path,PurePosixPath
from . import protocol as wire

ROOT={'request.json','replay.json','state.json','result.json'}
CASE={'result.json','plan.json','status.json','partial-events.jsonl','stderr.txt','replay.json'}
BUNDLE={'bundle.json','observations.jsonl','plan.json','profile.json','builds.json','target-manifest.json','status.json','result.json','replay.json','notes.txt'}
FAMILY={'timeout','signal','departure','repeat','cancel-first','complete-first','external-health'}

def allowed(name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or path.as_posix()!=name:return False
    parts=path.parts
    if len(parts)==1:return parts[0] in ROOT
    if len(parts) in {3,4} and parts[0]=='cases' and parts[1] in FAMILY:
        return parts[2] in CASE if len(parts)==3 else parts[2]=='bundle' and parts[3] in BUNDLE
    if len(parts) in {3,4} and parts[0]=='history' and re.fullmatch(r'collection-[0-9]{6}',parts[1]):
        return parts[2] in {'result.json','state.json'} if len(parts)==3 else parts[2] in FAMILY and parts[3] in {'result.json','status.json','partial-events.jsonl'}
    return False

def pack(source,destination):
    from resmgrcheck.workflow import inspect_execution
    source=Path(source);inspect_execution(source)
    total=0;count=0
    # The destination must be a fresh private regular file. Never overwrite.
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'wb') as output,tarfile.open(fileobj=output,mode='w|',format=tarfile.USTAR_FORMAT) as archive:
        for member in sorted(source.rglob('*')):
            if member.is_symlink():raise wire.ProtocolError('runner_evidence_symlink')
            name=member.relative_to(source).as_posix()
            if not member.is_file() or not allowed(name):continue
            descriptor=os.open(member,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(descriptor,'rb') as stream:
                info=os.fstat(stream.fileno());wire.require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=32*1024**2,'runner_evidence_type_or_bound')
                total+=info.st_size;count+=1
                wire.require(total<=wire.MAX_ARCHIVE-1024*1024 and count<=1200,'runner_evidence_bound')
                item=tarfile.TarInfo(name);item.size=info.st_size;item.mode=0o600;archive.addfile(item,stream)
        output.flush();os.fsync(output.fileno())
    wire.require(Path(destination).stat().st_size<=wire.MAX_ARCHIVE,'runner_evidence_bound')
    descriptor=os.open(destination,os.O_RDONLY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)

def unpack(source,destination):
    destination=Path(destination);wire.require(not destination.exists(),'runner_evidence_destination_occupied')
    destination.mkdir(mode=0o750)
    with tarfile.open(source,'r:') as archive:
        seen=set();total=0
        for item in archive:
            wire.require(item.isfile() and allowed(item.name) and item.name not in seen and 0<=item.size<=32*1024**2,'runner_evidence_member_invalid')
            seen.add(item.name);total+=item.size
            wire.require(total<=wire.MAX_ARCHIVE and len(seen)<=1200,'runner_evidence_bound')
            target=destination/item.name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
            descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o640)
            with archive.extractfile(item) as stream,os.fdopen(descriptor,'wb') as out:
                remaining=item.size
                while remaining:
                    block=stream.read(min(65536,remaining));wire.require(block,'runner_evidence_truncated')
                    out.write(block);remaining-=len(block)
                out.flush();os.fsync(out.fileno())
        wire.require(ROOT<=seen,'runner_evidence_missing_required')

def publish(source,destination):
    # Atomic publication without replacing even an empty unknown directory.
    libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(source),-100,os.fsencode(destination),1):
        number=ctypes.get_errno();raise OSError(number,os.strerror(number))
    descriptor=os.open(Path(destination).parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
