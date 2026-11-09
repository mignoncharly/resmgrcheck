"""Only allowlisted authentication status metadata may leave browser memory."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
from public_acceptance import Journey,HOST

class AuthenticationReportingTests(unittest.TestCase):
    def test_records_status_without_credentials_headers_body_or_arbitrary_urls(self):
        with tempfile.TemporaryDirectory() as temporary:
            journey=Journey('https://'+HOST,Path(temporary),{'native':{'status':'blocked'},'password':'private-password-marker','totp_secret':'private-MFA-marker'})
            journey.step='administrator-password-submit'
            class Response:
                url='https://'+HOST+'/administrator/login/?sensitive-query-marker'
                status=429
                request=SimpleNamespace(method='POST')
                def all_headers(self):raise AssertionError('Never inspect cookies/headers')
                def body(self):raise AssertionError('Never inspect response or credentials')
            journey.authentication_response(Response())
            journey.authentication_response(SimpleNamespace(url='https://'+HOST+'/administrator/2fa/authenticate/',status=302,request=SimpleNamespace(method='POST')))
            for url,method in [('https://untrusted.invalid/administrator/login/','POST'),('https://'+HOST+'/arbitrary-private-route','POST'),('https://'+HOST+'/administrator/login/','GET')]:
                journey.authentication_response(SimpleNamespace(url=url,status=200,request=SimpleNamespace(method=method)))
            raw=(Path(temporary)/'browser-report.json').read_text();result=json.loads(raw)
            self.assertEqual(result['authentication_requests'],[
                {'stage':'administrator-password-submit','endpoint':'password','status':429},
                {'stage':'administrator-password-submit','endpoint':'MFA','status':302}])
            for marker in ['private-password-marker','private-MFA-marker','sensitive-query-marker','arbitrary-private-route','untrusted.invalid']:
                self.assertNotIn(marker,raw)
