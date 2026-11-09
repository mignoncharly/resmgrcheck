"""Validate retained derived Python caches without loading/executing their code."""
import importlib.util,marshal,os,stat,struct
from pathlib import Path
from https_checks import require
import deploy_https as deployment

def trusted_payloads(source,filename):
    # CPython 3.12 marshal output is sensitive to compiler constant sharing.
    # Keep the first code object alive while compiling the identical source
    # again. Both accepted byte strings come from optimize=0 trusted compilation;
    # the candidate is never decoded, normalized, imported or executed.
    first=compile(source,filename,'exec',dont_inherit=True,optimize=0)
    cold=marshal.dumps(first)
    second=compile(source,filename,'exec',dont_inherit=True,optimize=0)
    return cold,marshal.dumps(second)

def validate_cache(path,root,revision):
    relative=path.relative_to(root)
    require(path.parent.name=='__pycache__','unexpected_release_resource')
    deployment.directory(path.parent)
    source=Path(importlib.util.source_from_cache(str(path)))
    require(str(path)==importlib.util.cache_from_source(str(source),optimization=''),'unexpected_bytecode_interpreter_tag')
    require(not source.is_symlink() and source.is_file(),'bytecode_source_not_regular')
    git=['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(root),
        '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',root]
    source_name=source.relative_to(root).as_posix()
    entry=deployment.command([*git,'ls-tree','-z',revision,'--',source_name])
    require(entry.endswith(b'\t'+source_name.encode()+b'\0') and entry.count(b'\0')==1,'bytecode_source_untracked')
    metadata=entry.split(b'\t',1)[0].split()
    require(len(metadata)==3 and metadata[0] in {b'100644',b'100755'} and metadata[1]==b'blob','bytecode_source_not_regular')
    require(stat.S_IMODE(source.lstat().st_mode)==int(metadata[0][-3:],8),'bytecode_source_mode_differs')
    trusted=deployment.command([*git,'show',revision+':'+source_name])
    require(len(trusted)<=1024**2 and deployment.read(source,limit=1024**2)==trusted,'bytecode_source_differs')
    raw=deployment.read(path);info=path.lstat()
    require(stat.S_IMODE(info.st_mode) in {0o600,0o640,0o644} and info.st_gid==os.getegid(),'bytecode_protection')
    require(len(raw)>=16 and raw[:4]==importlib.util.MAGIC_NUMBER,'bytecode_header_invalid')
    flags=struct.unpack('<I',raw[4:8])[0]
    require(flags in {0,1,3},'bytecode_flags_invalid')
    if flags==0:
        require(raw[8:16]==struct.pack('<II',int(source.stat().st_mtime)&0xffffffff,len(trusted)&0xffffffff),'bytecode_timestamp_invalid')
    else:require(raw[8:16]==importlib.util.source_hash(trusted),'bytecode_hash_invalid')
    # Compare to fresh compilation of trusted committed source. Never unmarshal
    # the untrusted cache, import it, delete it or change its permissions.
    candidates=trusted_payloads(trusted,str(source))
    require(raw[16:] in candidates,'bytecode_payload_differs')
    return {'path':relative.as_posix(),'sha256':deployment.digest(raw),'bytes':len(raw),'source_sha256':deployment.digest(trusted),
        'trusted_compile_pass':candidates.index(raw[16:])+1}

def retained_caches(root,revision,names,allowed):
    result={}
    for name in sorted(names):
        if name in allowed:continue
        path=root/name
        if name.endswith('/__pycache__/') or name=='__pycache__/':
            path=root/name.rstrip('/');deployment.directory(path)
            children=list(path.iterdir());require(0<len(children)<=256,'bytecode_directory_bound')
        else:children=[path]
        for child in sorted(children):
            require(not child.is_symlink() and child.is_file() and child.suffix=='.pyc','unexpected_release_resource')
            record=validate_cache(child,root,revision);result[record['path']]=record
    require(len(result)<=512,'bytecode_inventory_bound')
    return sorted(result.values(),key=lambda x:x['path'])
