#!/usr/bin/env python3
"""Read-only cache/source/receipt comparison; outputs metadata, never file contents."""
import importlib.util,json,marshal,os,re,stat,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as deployment
import recover_https_auth as recovery
from release_bytecode import trusted_payloads,validate_cache

def inspect():
    deployment.require_root();root=deployment.OPT/'releases'/recovery.ACTIVE
    recovery.release.owned_directory(root)
    manifest=deployment.read(root/recovery.previous.MANIFEST,private=True)
    manifest_ok=json.loads(manifest)==recovery.previous.identity(recovery.ACTIVE)
    recovery.release.check_clean(root,recovery.ACTIVE,None)
    recovery.release.check_venv(root/'.venv',Path(recovery.previous.identity(recovery.ACTIVE)['venv']))
    tracked=set(recovery.release.git(root,'ls-tree','-rz','--name-only',recovery.ACTIVE).decode().split('\0'))
    names=set()
    for flags in [[],['--ignored']]:names.update(recovery.release.git(root,'ls-files','--others','--exclude-standard','-z',*flags).decode().split('\0'))
    rows=[]
    for name in sorted(names-{'',recovery.previous.MANIFEST,'.venv'}):
        path=root/name.rstrip('/')
        if name.endswith('/__pycache__/') or name=='__pycache__/':
            deployment.directory(path)
            children=sorted(path.iterdir());deployment.require(0<len(children)<=256,'bytecode_directory_bound')
        else:children=[path]
        for child in children:
            row={'category':'unrecognized_resource','name_sha256':deployment.digest(str(child.relative_to(root)).encode())}
            try:
                source=Path(importlib.util.source_from_cache(str(child)))
                relative=source.relative_to(root).as_posix()
                if relative not in tracked:rows.append(row);continue
                row={'category':'tracked_source_cache','path':str(child),'source':str(source)}
                deployment.directory(child.parent);raw=deployment.read(child);info=child.lstat()
                source_bytes=recovery.release.git(root,'show',recovery.ACTIVE+':'+relative)
                row.update(uid=info.st_uid,gid=info.st_gid,mode=oct(stat.S_IMODE(info.st_mode)),bytes=len(raw),
                    sha256=deployment.digest(raw),source_sha256=deployment.digest(source_bytes),source_matches_Git=source.read_bytes()==source_bytes,
                    mtime_ns=info.st_mtime_ns,header_magic_matches=len(raw)>=16 and raw[:4]==importlib.util.MAGIC_NUMBER)
                if len(raw)<16:rows.append(row);continue
                row['header_flags']=struct.unpack('<I',raw[4:8])[0]
                filenames={'canonical_release':str(source),'current_alias':str(deployment.OPT/'current'/relative),
                    'workspace_source':str(deployment.SOURCE/relative),'relative_source':relative}
                candidates=trusted_payloads(source_bytes,str(source))
                row['trusted_compilation_matches']=[{'filename':'canonical_release','optimize':0,'marshal_version':marshal.version,'compile_pass':i+1}
                    for i,expected in enumerate(candidates) if raw[16:]==expected]
                row['trusted_payload_sizes']=[len(payload) for payload in candidates]
                try:validate_cache(child,root,recovery.ACTIVE);row['strict_validation']='passed'
                except deployment.CheckFailed as error:row['strict_validation']=str(error) if re.fullmatch('[a-z0-9_]{1,100}',str(error)) else 'failed'
                row['known_filename_strings_present']=[kind for kind,value in filenames.items() if value.encode() in raw[16:]]
            except Exception as error:row['inspection_error']=type(error).__name__
            rows.append(row)
    journal=json.loads(deployment.read(deployment.STATE/'auth-upgrade.json',private=True))
    safe_journal={key:value for key,value in journal.items() if key in {'kind','phase','step','revision','driver_revision','backup_verified'} and
        (isinstance(value,bool) or isinstance(value,str) and re.fullmatch('[A-Za-z0-9_-]{1,100}',value))}
    safe_journal['backup_bound']=bool(journal.get('backup'))
    health={}
    try:recovery.private_ready();health['private_readiness_200']=True
    except Exception:health['private_readiness_200']=False
    health['HTTP_status']=deployment.Client(address='127.0.0.1').request('/',secure=False)[0]
    health['original_HTTP_files_match']=deployment.read(deployment.SITE)==(deployment.HERE/'nginx-bootstrap-site.conf').read_bytes() and deployment.read(deployment.HTTP)==(deployment.HERE/'nginx-bootstrap-http.conf').read_bytes()
    health['enabled_symlink_correct']=deployment.ENABLED.is_symlink() and deployment.ENABLED.resolve()==deployment.SITE
    health['units_active']={unit:deployment.command(['systemctl','show','--value','--property=ActiveState',unit]).strip()==b'active'
        for unit in ['nginx.service','resmgrcheck-web.service','resmgrcheck-web.socket','resmgrcheck-db.service']}
    return {'read_only':True,'secrets_printed':False,'health':health,'interpreter':{'cache_tag':sys.implementation.cache_tag,'version':sys.version.split()[0],
        'executable':os.path.realpath(sys.executable),'optimize':sys.flags.optimize,'no_debug_ranges':bool(sys._xoptions.get('no_debug_ranges'))},
        'active_revision':(deployment.OPT/'current').resolve().name,'manifest_matches_recorded_identity':manifest_ok,
        'manifest_sha256':deployment.digest(manifest),'tracked_source_and_origin_clean':True,'venv_identity_verified':True,
        'auth_upgrade':safe_journal,'resources':rows}

if __name__=='__main__':
    try:print(json.dumps(inspect(),sort_keys=True))
    except Exception as error:
        print(json.dumps({'read_only':True,'inspection_failed':type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
