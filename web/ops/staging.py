#!/usr/bin/env python3
"""Own socket-only staging PG; no sudo, unrelated DB, public port or auth reuse."""
from pathlib import Path
import os,secrets,subprocess,sys
from cryptography.fernet import Fernet
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'.local/web'
BASE.mkdir(mode=0o700,parents=True,exist_ok=True)
pgbin=Path('/usr/lib/postgresql/16/bin')
data=BASE/'pgdata';sock=BASE/'pgsocket';runtime=BASE/'runtime'
for p in (sock,runtime):p.mkdir(mode=0o700,exist_ok=True)
for name,value in [('secret-key',secrets.token_urlsafe(64)),('mfa-key',Fernet.generate_key().decode())]:
 p=runtime/name
 if not p.exists():
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:f.write(value+'\n')
if not data.exists():
 subprocess.run([str(pgbin/'initdb'),'-D',str(data),'--auth-local=peer','--auth-host=scram-sha-256','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
 with (data/'postgresql.conf').open('a') as f:
  f.write("\nlisten_addresses=''\nunix_socket_directories='"+str(sock)+"'\nport=5438\nmax_connections=20\nshared_buffers='16MB'\nwork_mem='2MB'\nlog_min_messages=warning\n")
if subprocess.run([str(pgbin/'pg_ctl'),'-D',str(data),'status'],stdout=subprocess.DEVNULL).returncode:
 subprocess.run([str(pgbin/'pg_ctl'),'-D',str(data),'-l',str(BASE/'postgres.log'),'start'],check=True,stdout=subprocess.DEVNULL)
env=dict(os.environ,PGHOST=str(sock),PGPORT='5438')
exists=subprocess.check_output(['psql','-X','-w','-d','postgres','-Atc',"SELECT 1 FROM pg_database WHERE datname='resmgrcheck_web_stage'"],env=env,text=True).strip()
if not exists:subprocess.run(['createdb','resmgrcheck_web_stage'],env=env,check=True)
# This private staging role is the current development user, not a production role.
web_env={'RMC_WEB_ENV':'staging','RMC_WEB_SECRET_KEY_FILE':str(runtime/'secret-key'),'RMC_WEB_MFA_KEY_FILE':str(runtime/'mfa-key'),
 'RMC_WEB_DB_HOST':str(sock),'RMC_WEB_DB_PORT':'5438','RMC_WEB_DB_USER':os.environ.get('USER','mignon'),'RMC_WEB_DB_NAME':'resmgrcheck_web_stage',
 'RMC_WEB_ALLOWED_HOSTS':'127.0.0.1,localhost,testserver','RMC_WEB_CSRF_ORIGINS':'http://127.0.0.1:8431','RMC_WEB_EMAIL_BACKEND':'django.core.mail.backends.filebased.EmailBackend',
 'EMAIL_FILE_PATH':str(BASE/'mail')}
# Only paths/options go in this file; keys remain separately permissioned. Never print it.
import json
operator_config=runtime/'operator-settings.json'
if operator_config.exists():
 if operator_config.is_symlink() or operator_config.stat().st_mode & 0o077:
  raise SystemExit('Private operator settings must be0600 and nonsymlink')
 overrides=json.loads(operator_config.read_text())
 allowed={'RMC_WEB_EXECUTOR_REGISTRY','RMC_WEB_ENGINE_ROOT','RMC_WEB_EMAIL_BACKEND','RMC_WEB_EMAIL_HOST','RMC_WEB_EMAIL_PORT','RMC_WEB_EMAIL_USER','RMC_WEB_EMAIL_PASSWORD','RMC_WEB_EMAIL_TLS','RMC_WEB_FROM_EMAIL'}
 if not set(overrides)<=allowed:raise SystemExit('Unsupported staging operator setting')
 web_env.update({key:str(value) for key,value in overrides.items()})
p=runtime/'staging-config.json';p.write_text(json.dumps(web_env));p.chmod(0o600)
if len(sys.argv)>1:
 os.environ.update(web_env)
 os.chdir(ROOT/'web')
 os.execv(sys.executable,[sys.executable,*sys.argv[1:]])
print('Socket-only isolated PostgreSQL staging ready; runtime keys remain private.')
