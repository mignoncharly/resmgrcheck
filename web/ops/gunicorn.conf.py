"""Dedicated service configuration; disable the version's shared user control socket."""
import os
import socket

# Systemd discovery supplies fd 3 once. An explicit fd://3 bind would add it
# again in Gunicorn26.2.0 and consume an already-closed descriptor. No default TCP.
bind=[]
_ACTIVATION_SOCKET='/run/resmgrcheck-web/application.sock'


def on_starting(server):
    if os.environ.get('RMC_WEB_ENV')!='production':return
    if server.cfg.address:
        raise RuntimeError('Production must use systemd discovery without an explicit bind')
    if os.environ.get('LISTEN_PID')!=str(os.getpid()) or os.environ.get('LISTEN_FDS')!='1':
        raise RuntimeError('Production requires exactly one systemd Unix listener for this PID')
    # Duplicate only for inspection; keep the original fd and LISTEN_* intact
    # for Gunicorn's own systemd.listen_fds()/create_sockets() path.
    with socket.fromfd(3,socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        if (listener.getsockopt(socket.SOL_SOCKET,socket.SO_DOMAIN)!=socket.AF_UNIX or
                listener.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_STREAM or
                not listener.getsockopt(socket.SOL_SOCKET,socket.SO_ACCEPTCONN) or
                listener.getsockname()!=_ACTIVATION_SOCKET):
            raise RuntimeError('Production inherited listener must match the private systemd Unix socket')
    server.log.info('Validated systemd Unix listener fd=3 count=1; using automatic discovery')


control_socket_disable=True
workers=1
threads=2
timeout=30
graceful_timeout=30
max_requests=1000
max_requests_jitter=50
accesslog=None
limit_request_line=4094
limit_request_fields=50
limit_request_field_size=4094
