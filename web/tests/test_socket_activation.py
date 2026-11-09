"""Real inherited AF_UNIX/Gunicorn tests with modeled LISTEN_*; no systemd claim."""
import http.client,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import unittest

WEB=Path(__file__).resolve().parents[1]


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self,path,timeout=1):super().__init__('localhost',timeout=timeout);self.path=str(path)
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout);self.sock.connect(self.path)


def ready(path,timeout=1):
    connection=UnixHTTP(path,timeout)
    try:
        connection.request('GET','/readyz/',headers={'Host':'qnx-resmgrcheck.gestionatech.de','X-Forwarded-Proto':'https'})
        response=connection.getresponse();body=response.read(4096)
        return response.status==200 and json.loads(body)=={'status':'ready'}
    finally:connection.close()


class SocketActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rmc-activation-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'application.sock'
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(self.listener.close);self.listener.bind(str(self.path));self.listener.listen(8)
        self.inode=self.path.stat().st_ino;self.processes=[]
        self.addCleanup(self.stop_processes)
        # Test-only path substitution; production has no environment path escape.
        self.config=self.root/'gunicorn.conf.py'
        self.config.write_text((WEB/'ops/gunicorn.conf.py').read_text()+
            '\n_ACTIVATION_SOCKET='+repr(str(self.path))+'\n')
        self.old_config=self.root/'old.conf.py';self.old_config.write_text('control_socket_disable=True\nworkers=1\nthreads=2\n')

    def stop_processes(self):
        for process,log in self.processes:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=6)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            log.close()

    def launch(self,mode='valid',old=False,extra=(),response=200,fd=None):
        log=(self.root/('run-'+str(len(self.processes))+'.log')).open('w+')
        descriptor=self.listener.fileno() if fd is None else fd
        args=[sys.executable,'-B',str(WEB/'tests/socket_activation_exec.py'),mode,str(descriptor),
            'socket_activation_fixture:application','--config',str(self.old_config if old else self.config),*extra]
        process=subprocess.Popen(args,pass_fds=(descriptor,),stdout=log,stderr=log,cwd=WEB,
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONPATH':str(WEB/'tests'),
                 'PYTHONDONTWRITEBYTECODE':'1','RMC_WEB_ENV':'production','RMC_SOCKET_FIXTURE_STATUS':str(response)})
        self.processes.append((process,log));return process,log

    def logs(self,log):log.flush();log.seek(0);return log.read()

    def rejected(self,**kwargs):
        process,log=self.launch(**kwargs);process.wait(timeout=7)
        self.assertNotEqual(process.returncode,0);self.assertEqual(self.path.stat().st_ino,self.inode)
        return self.logs(log)

    def test_old_explicit_bind_and_systemd_discovery_double_consumes_live_fd(self):
        raw=self.rejected(old=True,extra=('--bind','fd://3'))
        self.assertIn('"fd3_socket_before_exec": true',raw)
        self.assertIn('"listen_pid_matches": true',raw)
        self.assertIn('OSError: [Errno 9] Bad file descriptor',raw)

    def test_corrected_discovery_serves_private_ready_without_rebinding(self):
        process,log=self.launch();deadline=time.monotonic()+7
        while time.monotonic()<deadline:
            if process.poll() is not None:self.fail(self.logs(log))
            try:
                if ready(self.path,0.3):break
            except (OSError,http.client.HTTPException):pass
            time.sleep(0.03)
        else:self.fail(self.logs(log))
        self.assertEqual(self.path.stat().st_ino,self.inode)
        self.assertIn('Validated systemd Unix listener fd=3 count=1',self.logs(log))

    def test_actual_gunicorn_unix_transport_has_no_peer_IP_and_keeps_explicit_proxy_header(self):
        process,log=self.launch();deadline=time.monotonic()+7
        while time.monotonic()<deadline:
            if process.poll() is not None:self.fail(self.logs(log))
            try:
                if ready(self.path,.3):break
            except (OSError,http.client.HTTPException):pass
            time.sleep(.03)
        else:self.fail(self.logs(log))
        connection=UnixHTTP(self.path)
        try:
            connection.request('GET','/transport-identity/',headers={'X-Real-IP':'198.51.100.20'})
            response=connection.getresponse();self.assertEqual(response.status,200)
            self.assertEqual(json.loads(response.read(1024)),{'remote_addr':'','x_real_ip':'198.51.100.20'})
        finally:connection.close()

    def test_missing_or_wrong_pid_extra_or_closed_fd_fail_without_fallback(self):
        for mode in ['missing','wrong-pid','extra','closed']:
            with self.subTest(mode=mode):
                raw=self.rejected(mode=mode)
                self.assertNotIn('Listening at:',raw)

    def test_duplicate_bind_is_rejected_before_consuming_descriptors(self):
        raw=self.rejected(extra=('--bind','fd://3'))
        self.assertIn('without an explicit bind',raw);self.assertNotIn('Listening at:',raw)

    def test_unexpected_socket_path_or_non_socket_descriptor_is_rejected(self):
        self.config.write_text((WEB/'ops/gunicorn.conf.py').read_text()+"\n_ACTIVATION_SOCKET='/unexpected'\n")
        self.assertIn('must match the private systemd Unix socket',self.rejected())
        self.config.write_text((WEB/'ops/gunicorn.conf.py').read_text()+'\n_ACTIVATION_SOCKET='+repr(str(self.path))+'\n')
        with (self.root/'plain-file').open('w+') as plain:
            raw=self.rejected(fd=plain.fileno());self.assertNotIn('Listening at:',raw)

    def test_http_503_and_socket_timeout_never_pass_readiness(self):
        with self.assertRaises((TimeoutError,OSError,http.client.HTTPException)):ready(self.path,0.1)
        process,log=self.launch(response=503);deadline=time.monotonic()+7
        while time.monotonic()<deadline:
            if process.poll() is not None:self.fail(self.logs(log))
            connection=UnixHTTP(self.path,0.3)
            try:
                connection.request('GET','/readyz/');response=connection.getresponse()
                if response.status==503:break
            except (OSError,http.client.HTTPException):pass
            finally:connection.close()
            time.sleep(0.03)
        else:self.fail(self.logs(log))
        self.assertFalse(ready(self.path))


if __name__=='__main__':unittest.main(verbosity=2)
