#!/usr/bin/env python3
"""Actual UNPRIVILEGED user-manager socket tests; synthetic WSGI, no DB/keys.

Touches only fresh random resmgrcheck-socket-qualification-* user units. Never
qualifies the root-managed production service, credentials, DB or full sandbox.
"""
import argparse,http.client,json,os,secrets,subprocess,sys,tempfile,time
from pathlib import Path
from test_socket_activation import UnixHTTP

WEB=Path(__file__).resolve().parents[1]


def command(args,check=True):
    return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        check=check,timeout=15)


def run_case(root,label,old,triggered):
    unit='resmgrcheck-socket-qualification-'+secrets.token_hex(6)+'-'+label
    path=root/(label+'.sock');config=root/(label+'.py')
    initial='control_socket_disable=True\nworkers=1\nthreads=2\n' if old else (WEB/'ops/gunicorn.conf.py').read_text()
    hook='''
_guard=globals().get('on_starting')
def on_starting(server):
    import errno,json,os,socket,stat
    try:
        probe=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except OSError as error:denied=error.errno in {errno.EAFNOSUPPORT,errno.EPERM,errno.EACCES}
    else:probe.close();denied=False
    server.log.info('ACTIVATION_METADATA '+json.dumps({'uid':os.geteuid(),
        'fd3_socket':stat.S_ISSOCK(os.fstat(3).st_mode),
        'pid_matches':os.environ.get('LISTEN_PID')==str(os.getpid()),
        'listen_fds':os.environ.get('LISTEN_FDS'),'ip_socket_creation_denied':denied}))
    if _guard:_guard(server)
'''
    config.write_text(initial+'\n_ACTIVATION_SOCKET='+repr(str(path))+'\n'+hook)
    args=['systemd-run','--user','--no-ask-password','--unit='+unit,
        '--socket-property=ListenStream='+str(path),'--socket-property=SocketMode=0600',
        '--socket-property=RemoveOnStop=true','--property=Restart=no',
        '--property=Requires='+unit+'.socket','--property=After='+unit+'.socket',
        '--property=NoNewPrivileges=true','--property=RestrictAddressFamilies=AF_UNIX',
        '--property=WorkingDirectory='+str(WEB),'--property=Environment=RMC_WEB_ENV=production',
        '--property=Environment=PYTHONDONTWRITEBYTECODE=1',
        '--property=Environment=PYTHONPATH='+str(WEB/'tests'),
        sys.executable,'-B','-m','gunicorn','socket_activation_fixture:application','--config',str(config)]
    if old:args+=['--bind','fd://3']
    command(args)
    record={'case':label,'actual_user_systemd':True,'triggered_by_request':triggered,
        'production_qualification':False,'synthetic_wsgi_without_db_or_secrets':True}
    try:
        if not triggered:
            # Keep the transient socket active so its never-started service
            # definition is retained; persistent production units do not GC this way.
            command(['systemctl','--user','start',unit+'.service'],check=False)
        deadline=time.monotonic()+8;status=None;body='';failure=None
        while time.monotonic()<deadline:
            connection=UnixHTTP(path,0.5)
            try:
                connection.request('GET','/readyz/',headers={'Host':'qnx-resmgrcheck.gestionatech.de','X-Forwarded-Proto':'https'})
                response=connection.getresponse();status=response.status;body=response.read(4096).decode();break
            except (OSError,http.client.HTTPException) as error:
                failure=type(error).__name__
                if old:break
            finally:connection.close()
            time.sleep(0.05)
        # Only this new unit's invocation logs, containing synthetic fixture facts.
        journal=command(['journalctl','--user','-u',unit+'.service','--no-pager','-o','cat','-n','160']).stdout
        metadata=[]
        for line in journal.splitlines():
            if 'ACTIVATION_METADATA ' in line:metadata.append(json.loads(line.split('ACTIVATION_METADATA ',1)[1]))
        record.update(http_status=status,body=body,request_failure=failure,activation_metadata=metadata,
            bad_fd_observed='OSError: [Errno 9] Bad file descriptor' in journal,
            validated_listener='Validated systemd Unix listener fd=3 count=1' in journal)
        assert metadata and all(m['fd3_socket'] and m['pid_matches'] and m['listen_fds']=='1' and m['uid']!=0 for m in metadata),record
        assert all(m['ip_socket_creation_denied'] for m in metadata),record
        if old:assert status is None and record['bad_fd_observed'],record
        else:assert status==200 and json.loads(body)=={'status':'ready'} and record['validated_listener'],record
        return record
    finally:
        command(['systemctl','--user','stop',unit+'.socket',unit+'.service'],check=False)
        command(['systemctl','--user','reset-failed',unit+'.socket',unit+'.service'],check=False)
        states=command(['systemctl','--user','show','--value','--property=ActiveState',unit+'.socket',unit+'.service'],check=False).stdout.split()
        record['own_units_stopped']=len(states)==2 and all(state in {'inactive','failed'} for state in states)
        record['fixture_socket_removed']=not path.exists()
        assert record['own_units_stopped'] and record['fixture_socket_removed'],record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    if os.geteuid()==0:raise SystemExit('Run as the development user, never root')
    with tempfile.TemporaryDirectory(prefix='rmc-user-sd-') as tmp:
        cases=[run_case(Path(tmp),label,old,triggered) for label,old,triggered in [
            ('old-explicit',True,False),('old-triggered',True,True),
            ('fixed-explicit',False,False),('fixed-triggered',False,True)]]
    result={'scope':'actual user systemd; synthetic WSGI, no production DB/keys/runtime_check',
        'uid':os.geteuid(),'cases':cases,'unrelated_units_changed':False,'production_gate':'PENDING'}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
