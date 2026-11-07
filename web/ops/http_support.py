"""Private qualification support; credentials/codes/cookies never printed or persisted."""
import http.cookiejar,json,time,urllib.parse,urllib.request,urllib.error,uuid
from html.parser import HTMLParser
from django.conf import settings
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value

class Inputs(HTMLParser):
    def __init__(self):super().__init__();self.data={};self.raw=[];self.secret=False
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag=='input' and 'name' in data:self.data[data['name']]=data.get('value','')
        if tag=='pre' and data.get('id')=='new-access-code':self.secret=True
    def handle_endtag(self,tag):
        if tag=='pre':self.secret=False
    def handle_data(self,value):
        if self.secret:self.raw.append(value)

class HTTP:
    def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(self,path):
        with self.opener.open('http://127.0.0.1:8431'+path,timeout=15) as response:return response.geturl(),response.read().decode()
    def post(self,path,data,csrf=None):
        if csrf is None:
            try:_,html=self.get(path)
            except urllib.error.HTTPError as error:
                if error.code!=405:raise
                _,html=self.get('/app/session/')
            parsed=Inputs();parsed.feed(html);csrf=parsed.data['csrfmiddlewaretoken']
        request=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
        with self.opener.open(request,timeout=15) as response:return response.geturl(),response.read().decode()

def administrator_client():
    credential=json.loads((settings.PRIVATE_ROOT/'acceptance-administrator.json').read_text());client=HTTP()
    client.post('/administrator/login/',{'login':credential['username'],'password':credential['password']})
    for attempt in range(3):
        code=format_hotp_value(hotp_value(credential['totp_secret'],int(time.time())//30))
        url,_=client.post('/administrator/2fa/authenticate/',{'code':code})
        if urllib.parse.urlsplit(url).path=='/app/':return client,credential
        if attempt>=2:raise RuntimeError('Actual MFA failed; no bypass or credential logging')
        time.sleep(30-time.time()%30+.1)

def issued_session(admin,project,target,description,*,live=False,ai=False):
    data={'description':description,'projects':str(project.pk),'targets':str(target.pk),'can_download':'on','all_evidence':'on','max_sessions':'1','max_redemptions':'1'}
    if live:data['allow_live']='on'
    if ai:data['allow_ai']='on'
    _,body=admin.post('/administrator/organizations/'+str(project.organization_id)+'/codes/',data)
    parsed=Inputs();parsed.feed(body);raw=''.join(parsed.raw).strip()
    if not raw.startswith('rmc_'):raise RuntimeError('No code was generated; preserve the response state without printing its body')
    identifier=str(uuid.UUID(hex=raw.split('_')[1]));client=HTTP();url,_=client.post('/access/',{'code':raw})
    if urllib.parse.urlsplit(url).path!='/app/':raise RuntimeError('Actual code redemption did not complete')
    return client,identifier
