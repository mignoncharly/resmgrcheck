"""Customer-local HTTPS client. No inbound listener, proxy inheritance or redirects."""
import json,os,ssl,stat
from pathlib import Path
from urllib import request,error
from . import protocol as wire

def protected(path,limit=16384):
    path=Path(path)
    wire.require(path.is_absolute() and '..' not in path.parts and not any(p.is_symlink() for p in [path,*path.parents]),'private_path_invalid')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        wire.require(stat.S_ISREG(info.st_mode) and info.st_uid in {0,os.geteuid()} and
            info.st_nlink==1 and stat.S_IMODE(info.st_mode) in {0o400,0o600} and info.st_size<=limit,'private_file_invalid')
        raw=os.read(fd,limit+1);wire.require(len(raw)<=limit,'private_file_bound');return raw
    finally:os.close(fd)

def create(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class Client:
    def __init__(self,origin,server_key,seed,runner_id,*,ca_file=None):
        self.origin=wire.origin(origin);self.server_key=wire.hex_value(server_key);self.seed=seed;self.runner_id=runner_id
        self.opener=request.build_opener(request.ProxyHandler({}),NoRedirect(),request.HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))

    def send(self,operation,value,nonce):
        wire.require(operation in {'enroll','exchange'},'runner_operation_invalid')
        raw=wire.canonical(value);wire.require(len(raw)<=wire.MAX_MESSAGE,'message_size_invalid')
        req=request.Request(self.origin+'/runner/v1/'+operation+'/',data=raw,headers={'Content-Type':'application/json'},method='POST')
        try:
            with self.opener.open(req,timeout=10) as reply:
                wire.require(reply.status==200 and reply.headers.get_content_type()=='application/json','runner_response_invalid')
                data=wire.parse(reply.read(wire.MAX_MESSAGE+1))
        except (OSError,error.URLError):raise wire.ProtocolError('runner_connection_unavailable') from None
        payload=wire.verify(self.server_key,'response',data)
        wire.fields(payload,'version audience timestamp nonce body');wire.fresh(payload,self.origin)
        wire.require(payload['nonce']==nonce,'runner_response_replayed');return payload['body']

    def exchange(self,body):
        value=wire.request(self.seed,self.runner_id,self.origin,body)
        return self.send('exchange',value,value['payload']['nonce'])

    def enroll(self,token,inventory):
        value=wire.request(self.seed,self.runner_id,self.origin,{})['payload']
        value.pop('runner_id');value.pop('body');value.update(public_key=wire.public(self.seed),inventory=inventory)
        result=self.send('enroll',{'token':token,'message':wire.sign(self.seed,'enrollment',value)},value['nonce'])
        wire.require(result['runner_id']==self.runner_id and result['server_public_key']==self.server_key,'runner_enrollment_binding_mismatch')
        return result
