"""Encrypted PostgreSQL/evidence snapshots and isolated restore drills.

No QNX contact or restoration over an existing database. Keys stay outside archives.
"""
from contextlib import contextmanager
import hashlib,io,json,os,re,secrets,stat,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
from django.conf import settings
from django.db import connection,transaction
from .models import Artifact,Run
from .storage import open_artifact,verify_inventory
from .engine import PolicyError

MAGIC=b'RMCBK001';LOCK=726301820497;BOUND=4*1024**3
TABLES=('control_user','control_organization','control_project','control_run','control_artifact','control_auditevent','control_accesscode','control_accesssession','control_sourcesubmission','control_aianalysis')

@contextmanager
def media_lock(shared=False):
    """Retention must not delete files while a consistent DB snapshot is copied."""
    suffix='_shared' if shared else ''
    with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_lock'+suffix+'(%s)',[LOCK])
    try:yield
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock'+suffix+'(%s)',[LOCK])

def key_bytes(path):
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid not in {0,os.getuid()} or info.st_mode&0o077 or info.st_size!=32:raise PolicyError('backup_key_requires_owned_private_32_byte_file')
        return os.read(descriptor,33)
    finally:os.close(descriptor)

def pg_env():
    d=settings.DATABASES['default']
    # Socket-only, fixed installed client tools; never arbitrary hosts or SQL input.
    if not str(d['HOST']).startswith('/') or not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',d['NAME']):raise PolicyError('backup_requires_private_local_database')
    return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PGHOST':str(d['HOST']),'PGPORT':str(d['PORT']),'PGUSER':d['USER'],'PGCONNECT_TIMEOUT':'5','PGOPTIONS':'-c statement_timeout=120000 -c lock_timeout=5000'}

def pg(tool,args,*,timeout=120,check=True):
    process=subprocess.run(['/usr/lib/postgresql/16/bin/'+tool,*args],env=pg_env(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if check and process.returncode:raise PolicyError('backup_'+tool+'_failed') # Never reflect database/credential diagnostics.
    return process

def identity(cursor):
    counts={}
    for table in TABLES:
        cursor.execute('SELECT count(*) FROM '+table);counts[table]=cursor.fetchone()[0]
    cursor.execute('SELECT id::text,sha256 FROM control_artifact ORDER BY id')
    return {'counts':counts,'artifact_sha256':hashlib.sha256(json.dumps(cursor.fetchall(),separators=(',',':')).encode()).hexdigest()}

class EncryptWriter:
    def __init__(self,stream,key):
        self.stream=stream;self.nonce=os.urandom(12);self.cipher=Cipher(algorithms.AES(key),modes.GCM(self.nonce)).encryptor()
        self.cipher.authenticate_additional_data(MAGIC);self.stream.write(MAGIC+self.nonce);self.total=0
    def write(self,value):
        self.total+=len(value)
        if self.total>BOUND:raise PolicyError('backup_size_bound_exceeded')
        self.stream.write(self.cipher.update(value));return len(value)
    def finish(self):self.stream.write(self.cipher.finalize());self.stream.write(self.cipher.tag)

def digest_file(path):
    result=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()

def add_bytes(archive,name,raw):
    item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o600;archive.addfile(item,io.BytesIO(raw))

def snapshot(destination,key_file):
    """Export one real DB snapshot and its sealed immutable artifacts, encrypted."""
    key=key_bytes(key_file);destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise PolicyError('backup_destination_occupied')
    if not destination.parent.is_dir() or destination.parent.is_symlink() or destination.parent.stat().st_mode&0o077:raise PolicyError('backup_directory_requires_private_permissions')
    with tempfile.TemporaryDirectory(prefix='snapshot-',dir=settings.PRIVATE_ROOT) as temporary,media_lock(shared=True):
        stage=Path(temporary);dump=stage/'database.dump'
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                cursor.execute('SELECT pg_export_snapshot()');snapshot_id=cursor.fetchone()[0];expected=identity(cursor)
            pg('pg_dump',['-w','--format=custom','--no-owner','--no-acl','--snapshot='+snapshot_id,'--file',str(dump),settings.DATABASES['default']['NAME']])
            if dump.stat().st_size>BOUND//2:raise PolicyError('backup_database_size_bound_exceeded')
            inventory={};runs=set();artifacts=list(Artifact.objects.select_related('run__project__organization').filter(run__purged_at=None).order_by('pk'))
            if len(artifacts)>100000:raise PolicyError('backup_file_count_bound_exceeded')
            # Work remains private until both complete encryption and fsync succeed.
            partial=destination.parent/('.partial-'+secrets.token_hex(16));descriptor=os.open(partial,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            try:
                with os.fdopen(descriptor,'wb') as stream:
                    writer=EncryptWriter(stream,key)
                    with tarfile.open(fileobj=writer,mode='w|') as archive:
                        item=tarfile.TarInfo('database.dump');item.size=dump.stat().st_size;item.mode=0o600
                        with dump.open('rb') as source:archive.addfile(item,source)
                        for artifact in artifacts:
                            if artifact.run_id not in runs:verify_inventory(artifact.run);runs.add(artifact.run_id)
                            relative='/'.join([str(artifact.run.project.organization_id),str(artifact.run.project_id),str(artifact.run_id),artifact.relative_path]);name='evidence/'+relative
                            if PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts:raise PolicyError('backup_artifact_path_invalid')
                            inventory[relative]={'sha256':artifact.sha256,'bytes':artifact.byte_count}
                            item=tarfile.TarInfo(name);item.size=artifact.byte_count;item.mode=0o600
                            with open_artifact(artifact) as source:archive.addfile(item,source)
                        record={'kind':'resmgrcheck-encrypted-snapshot','schema_version':1,'database':expected,'database_dump_sha256':digest_file(dump),'evidence':inventory,'sealed_runs':len(runs),'qnx_contacted':False}
                        add_bytes(archive,'snapshot.json',json.dumps(record,sort_keys=True).encode())
                    writer.finish();stream.flush();os.fsync(stream.fileno())
                # Atomic publication without replacing any existing backup.
                os.link(partial,destination);os.unlink(partial)
                directory=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(directory)
                finally:os.close(directory)
            finally:
                if partial.exists():partial.unlink()
    return {'passed':True,'encrypted_sha256':digest_file(destination),'files':len(inventory),'sealed_runs':len(runs),'qnx_contacted':False}

def decrypt(source,destination,key_file):
    key=key_bytes(key_file);size=Path(source).stat().st_size
    if size<36 or size>BOUND+36:raise PolicyError('backup_archive_size_invalid')
    try:
        with open(source,'rb') as stream:
            if stream.read(8)!=MAGIC:raise PolicyError('backup_format_invalid')
            nonce=stream.read(12);stream.seek(-16,2);tag=stream.read(16);stream.seek(20)
            cipher=Cipher(algorithms.AES(key),modes.GCM(nonce,tag)).decryptor();cipher.authenticate_additional_data(MAGIC)
            remaining=size-36
            with open(destination,'xb') as output:
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:raise PolicyError('backup_archive_truncated')
                    output.write(cipher.update(block));remaining-=len(block)
                output.write(cipher.finalize()) # Must authenticate before any extraction/restore.
    except Exception:
        Path(destination).unlink(missing_ok=True);raise

def restore_drill(source,key_file):
    """Restore only an exact new temporary DB; authenticate before parsing its data."""
    name='resmgrcheck_restore_'+secrets.token_hex(6);created=False
    with tempfile.TemporaryDirectory(prefix='restore-',dir=settings.PRIVATE_ROOT) as temporary:
        stage=Path(temporary);decrypted=stage/'authenticated.tar';decrypt(source,decrypted,key_file)
        with tarfile.open(decrypted,'r:') as archive:
            members=archive.getmembers();names=[m.name for m in members]
            if len(members)>100002 or len(names)!=len(set(names)):raise PolicyError('backup_archive_duplicate_or_count')
            if any(not m.isfile() or m.size>BOUND//2 or PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts for m in members):raise PolicyError('backup_archive_type_or_path')
            if names.count('snapshot.json')!=1 or names.count('database.dump')!=1:raise PolicyError('backup_archive_missing_required')
            marker=archive.getmember('snapshot.json')
            if marker.size>32*1024*1024:raise PolicyError('backup_inventory_size_bound')
            record=json.load(archive.extractfile(marker))
            if record.get('kind')!='resmgrcheck-encrypted-snapshot' or record.get('schema_version')!=1:raise PolicyError('backup_inventory_schema')
            expected={'database.dump','snapshot.json'}|{'evidence/'+n for n in record['evidence']}
            if set(names)!=expected:raise PolicyError('backup_archive_inventory_mismatch')
            # Only regular allowlisted files; never tar.extractall, links, modes or executable bits.
            for item in members:
                target=stage/item.name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                if item.name=='snapshot.json':continue
                digest=hashlib.sha256();count=0
                with archive.extractfile(item) as stream,open(target,'xb') as output:
                    for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block);count+=len(block);output.write(block)
                wanted={'sha256':record['database_dump_sha256'],'bytes':item.size} if item.name=='database.dump' else record['evidence'][item.name[9:]]
                if {'sha256':digest.hexdigest(),'bytes':count}!=wanted:raise PolicyError('backup_member_integrity_failed')
        try:
            pg('createdb',['-w',name]);created=True
            pg('pg_restore',['-w','--no-owner','--no-acl','--single-transaction','--exit-on-error','--dbname',name,str(stage/'database.dump')])
            # Independent connection to the restored database; never switch Django's live DB.
            import psycopg
            environment=pg_env()
            with psycopg.connect(dbname=name,user=environment['PGUSER'],host=environment['PGHOST'],port=environment['PGPORT'],connect_timeout=5) as restored:
                with restored.cursor() as cursor:
                    if identity(cursor)!=record['database']:raise PolicyError('backup_restored_database_mismatch')
                try:
                    with restored.cursor() as cursor:cursor.execute('UPDATE control_auditevent SET action=action WHERE id=(SELECT id FROM control_auditevent LIMIT 1)')
                except psycopg.Error as error:
                    restored.rollback()
                    if 'append-only' not in str(error):raise PolicyError('backup_restored_audit_trigger_unexpected') from None
                else:raise PolicyError('backup_restored_audit_trigger_unproven')
            from resmgrcheck.workflow import inspect_execution
            executions=0
            for request in (stage/'evidence').glob('*/*/*/request.json'):inspect_execution(request.parent);executions+=1
            return {'passed':True,'encrypted_sha256':digest_file(source),'restored_files':len(record['evidence']),'restored_collected_executions':executions,'database_identity_matches':True,'audit_update_denied':True,'temporary_database_removed_on_exit':True,'original_database_preserved':True,'qnx_contacted':False}
        finally:
            if created:pg('dropdb',['-w',name]) # Exact DB created above only; no force or broad termination.
