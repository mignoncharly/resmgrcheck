"""Bounded TLS/HTTP checks; direct verified connections, no proxies or redirects."""
import hashlib,http.client,json,socket,ssl,time,uuid
from https_config import HOST

class CheckFailed(RuntimeError):pass

def require(value,code):
    if not value:raise CheckFailed(code)

class VerifiedHTTPS(http.client.HTTPSConnection):
    def __init__(self,address=None,port=443,ca_file=None,timeout=4):
        super().__init__(HOST,port=port,timeout=timeout,context=ssl.create_default_context(cafile=ca_file));self.address=address or HOST
    def connect(self):
        self.sock=self._context.wrap_socket(socket.create_connection((self.address,self.port),self.timeout),server_hostname=HOST)

class Client:
    def __init__(self,address=None,https_port=443,http_port=80,ca_file=None):
        self.address=address;self.https_port=https_port;self.http_port=http_port;self.ca_file=ca_file
    def request(self,path,method='GET',body=None,headers=None,secure=True,limit=1048576):
        require(path.startswith('/') and '\r' not in path and '\n' not in path,'invalid_probe_path')
        connection=VerifiedHTTPS(self.address,self.https_port,self.ca_file) if secure else http.client.HTTPConnection(self.address or HOST,self.http_port,timeout=4)
        try:
            connection.request(method,path,body=body,headers={'Host':HOST,**(headers or {})})
            response=connection.getresponse();data=response.read(limit+1);require(len(data)<=limit,'probe_body_bound')
            return response.status,{k.lower():v for k,v in response.getheaders()},data
        finally:connection.close()

def security(headers,private=False):
    require(headers.get('strict-transport-security')=='max-age=31536000','hsts_missing_or_wrong')
    require(headers.get('x-content-type-options')=='nosniff','nosniff_missing')
    require(headers.get('x-frame-options') in {'DENY','SAMEORIGIN'},'framing_policy_missing')
    require(headers.get('referrer-policy')=='same-origin','referrer_policy_missing')
    require(headers.get('permissions-policy')=='camera=(), microphone=(), geolocation=()','permissions_policy_missing')
    csp=headers.get('content-security-policy','')
    require("default-src" in csp and 'frame-ancestors' in csp and 'form-action' in csp,'csp_missing')
    if private:require('no-store' in headers.get('cache-control',''),'private_response_cacheable')

def checks(client,static_sha256,*,rate=True):
    results=[]
    for path,status in [('/',200),('/readyz/',200),('/access/',200),('/administrator/login/',200),
            ('/app/',302),('/api/projects/91116d07-5158-46ac-aeb0-790815735df6/',302),
            ('/administrator/signup/',404),('/not-a-resmgrcheck-route/',404),('/static/not-a-real-file.css',404)]:
        observed,headers,body=client.request(path);require(observed==status,'http_status_'+path.replace('/','_'))
        security(headers,path in {'/access/','/administrator/login/','/app/'})
        if path=='/readyz/':require(json.loads(body)=={'status':'ready'},'readiness_body_invalid')
        if status==302:require(headers.get('location')=='/access/','anonymous_redirect_invalid')
        if path in {'/access/','/administrator/login/'}:
            cookie=headers.get('set-cookie','').lower()
            require('resmgrcheck_csrf=' in cookie and 'secure' in cookie and 'httponly' in cookie and 'samesite=lax' in cookie,'csrf_cookie_flags_invalid')
        results.append({'check':path,'status':'passed','http_status':observed})
    status,headers,body=client.request('/static/control/app.css');security(headers)
    require(status==200 and headers.get('content-type','').startswith('text/css') and hashlib.sha256(body).hexdigest()==static_sha256,'static_asset_identity_invalid')
    results.append({'check':'immutable_static_css','status':'passed'})
    status,headers,_=client.request('/runner/v1/enroll/','POST',b'{}',{'Content-Type':'application/json'});security(headers,True)
    require(status==404,'customer_runner_not_disabled');results.append({'check':'customer_runner_disabled','status':'passed'})
    status,headers,_=client.request('/access/','POST',b'code=probe-invalid',{'Content-Type':'application/x-www-form-urlencoded','Origin':'https://untrusted.invalid'});security(headers,True)
    require(status in {403,429},'cross_origin_post_not_rejected');results.append({'check':'csrf_origin_rejected','status':'passed','http_status':status})
    # No actor/key is sent. Only the loopback probe address is rate limited.
    if rate:
        statuses=[]
        for _ in range(12):
            status,headers,_=client.request('/administrator/login/','POST',b'login=probe-invalid',{'Content-Type':'application/x-www-form-urlencoded'})
            security(headers,True);require(status in {403,429},'unexpected_rate_probe_status');statuses.append(status)
        require(429 in statuses,'authentication_rate_limit_unproven')
        status,_,_=client.request('/readyz/');require(status==200,'rate_limit_affected_readiness')
        results.append({'check':'authentication_post_limit_and_unlimited_readiness','status':'passed'})
    status,headers,_=client.request('/',secure=False)
    require(status==308 and headers.get('location')=='https://'+HOST+'/','http_redirect_invalid')
    results.append({'check':'http_https_redirect','status':'passed'})
    return results
