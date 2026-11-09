"""Synthetic WSGI readiness fixture for REAL Gunicorn/Unix FD tests. No DB or keys."""
import json,os


def application(environ,start_response):
    status=int(os.environ.get('RMC_SOCKET_FIXTURE_STATUS','200'))
    body=json.dumps({'status':'ready' if status==200 else 'unavailable'}).encode()
    if environ.get('PATH_INFO')=='/transport-identity/':
        body=json.dumps({'remote_addr':environ.get('REMOTE_ADDR'),'x_real_ip':environ.get('HTTP_X_REAL_IP')}).encode()
    start_response(str(status)+(' OK' if status==200 else ' Service Unavailable'),[
        ('Content-Type','application/json'),('Content-Length',str(len(body)))])
    return [body]
