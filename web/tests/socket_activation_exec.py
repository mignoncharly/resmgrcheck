"""Model systemd's FD placement/environment, then exec; never fork a server wrapper.

This is a TEST launcher only. The production unit executes Python/Gunicorn directly.
"""
import json,os,stat,sys

mode=sys.argv[1];inherited=int(sys.argv[2]);arguments=sys.argv[3:]
if inherited!=3:os.dup2(inherited,3,inheritable=True)
else:os.set_inheritable(3,True)
env=dict(os.environ,LISTEN_PID=str(os.getpid()),LISTEN_FDS='1')
if mode=='wrong-pid':env['LISTEN_PID']=str(os.getpid()+1)
elif mode=='missing':env.pop('LISTEN_PID');env.pop('LISTEN_FDS')
elif mode=='extra':env['LISTEN_FDS']='2'
elif mode=='closed':os.close(3)
try:is_socket=stat.S_ISSOCK(os.fstat(3).st_mode)
except OSError:is_socket=False
print(json.dumps({'modeled_activation':True,'fd3_socket_before_exec':is_socket,
    'listen_pid_matches':env.get('LISTEN_PID')==str(os.getpid()),
    'listen_fds':env.get('LISTEN_FDS'),'os_uid':os.geteuid()}),flush=True)
os.execve(sys.executable,[sys.executable,'-B','-m','gunicorn',*arguments],env)
