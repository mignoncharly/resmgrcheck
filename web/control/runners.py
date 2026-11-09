"""Tenant-bound enrollment and machine authentication. Never opens an SSH route."""
from datetime import timedelta
import hashlib,hmac,re,secrets,uuid
from django.conf import settings
from django.db import IntegrityError,transaction
from django.utils import timezone
from customer_runner import protocol as wire
from resmgrcheck.registrations import CAPABILITIES,REGISTRY
from .models import CustomerRunner,RunnerEnrollment,RunnerNonce,Target,Project
from .security import audit,consume_rate

def enabled():
    wire.require(settings.RUNNER_ENABLED and settings.SERVICE_ROLE in {'web','operator'} and bool(settings.RUNNER_SIGNING_KEY),'runner_unavailable')

def token_verifier(token):
    return hmac.new(settings.SECRET_KEY.encode(),('runner-enrollment-v1:'+token).encode(),hashlib.sha256).hexdigest()

def issue(actor,project,name):
    enabled()
    with transaction.atomic():
        Project.objects.select_for_update().get(pk=project.pk)
        wire.require(Target.objects.filter(project=project,kind='customer-runner').count()<20,'runner_target_quota')
        target=Target.objects.create(project=project,name=name,kind='customer-runner',state='pending-approval')
        enrollment=RunnerEnrollment(target=target,expires_at=timezone.now()+timedelta(minutes=10))
        token='rme_'+enrollment.pk.hex+'_'+secrets.token_urlsafe(32)
        enrollment.verifier=token_verifier(token);enrollment.save()
        audit(actor,'runner.enrollment_issued',project.organization,target.pk,expires_seconds=600)
        return target,token

def inventory(value):
    wire.fields(value,'protocol runner_version engine_sha256 route_sha256 target_identity compiled_adapters attachment allowed_modes')
    wire.require(type(value['protocol']) is int and type(value['runner_version']) is str and len(value['runner_version'])<=40,'runner_version_invalid')
    wire.hex_value(value['engine_sha256']);wire.hex_value(value['route_sha256']);identity=value['target_identity']
    wire.fields(identity,'uid processor machine release recipe_id root')
    wire.require(type(identity['uid']) is int and 0<=identity['uid']<=65535,'target_identity_invalid')
    wire.hex_value(identity['recipe_id'])
    wire.require(identity['processor']=='x86_64' and identity['machine']=='x86pc' and identity['release']=='8.0.0' and identity['root']=='/data/resmgrcheck','target_incompatible')
    adapters=value['compiled_adapters']
    wire.require(type(adapters) is dict and len(adapters)<=16,'adapter_inventory_invalid')
    for name,caps in adapters.items():
        wire.require(name in REGISTRY and type(caps) is list and len(caps)==len(set(caps)) and set(caps)<=CAPABILITIES,'adapter_inventory_invalid')
    wire.require(value['attachment'] in {'managed-fixture','external-attach'},'attachment_invalid')
    wire.require(type(value['allowed_modes']) is list and value['allowed_modes'] and len(value['allowed_modes'])<=6 and
        set(value['allowed_modes'])<={'corrected','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'},'runner_modes_invalid')
    return value

def status(runner):
    if runner.revoked_at or runner.quarantined or runner.target.state=='quarantined':return 'quarantined'
    if runner.inventory['protocol']!=wire.VERSION or runner.inventory['runner_version']!='1':return 'incompatible'
    if not runner.approved_at or not runner.target.approved:return 'pending-approval'
    if not runner.inventory['compiled_adapters']:return 'unsupported'
    if not runner.last_seen or runner.last_seen<timezone.now()-timedelta(seconds=90):return 'disconnected'
    return 'connected'

def public_inventory(runner):
    return {'compiled_adapters':runner.inventory['compiled_adapters'],'runner_claims_sha256':runner.inventory_sha256,
        'service_instance':'unknown','capability_scope':'signed runner discovery; connection does not qualify lifecycle'}

def enroll(message):
    enabled();wire.fields(message,'token message')
    token=message['token']
    wire.require(type(token) is str and re.fullmatch(r'rme_[0-9a-f]{32}_[A-Za-z0-9_-]{43}',token),'enrollment_invalid')
    payload=message['message'].get('payload',{})
    wire.fields(payload,'version audience timestamp nonce public_key inventory')
    wire.fresh(payload,settings.RUNNER_ORIGIN)
    wire.verify(payload['public_key'],'enrollment',message['message']);info=inventory(payload['inventory'])
    with transaction.atomic():
        row=RunnerEnrollment.objects.select_for_update().select_related('target__project__organization').filter(pk=uuid.UUID(hex=token[4:36])).first()
        wire.require(row and not row.revoked_at and row.expires_at>timezone.now() and
            hmac.compare_digest(row.verifier,token_verifier(token)),'enrollment_invalid')
        target=Target.objects.select_for_update().get(pk=row.target_id)
        wire.require(target.kind=='customer-runner' and target.project.active and target.project.organization.active,'enrollment_invalid')
        runner=CustomerRunner.objects.filter(target=target).first()
        if row.used_at:
            wire.require(runner and runner.public_key==payload['public_key'] and not runner.revoked_at and
                not runner.quarantined and runner.inventory_sha256==wire.fingerprint(info),'enrollment_already_used')
        else:
            wire.require(runner is None,'runner_identity_exists')
            runner=CustomerRunner.objects.create(target=target,public_key=payload['public_key'],inventory=info,
                inventory_sha256=wire.fingerprint(info),last_seen=timezone.now())
            row.used_at=timezone.now();row.save(update_fields=['used_at'])
            target.state=status(runner);target.last_seen=runner.last_seen;target.inventory=public_inventory(runner)
            target.save(update_fields=['state','last_seen','inventory'])
            audit(None,'runner.enrolled',target.project.organization,target.pk,public_key_sha256=wire.fingerprint(runner.public_key),inventory_sha256=runner.inventory_sha256)
        return response(payload,{'runner_id':str(target.pk),'organization_id':str(target.project.organization_id),
            'project_id':str(target.project_id),'state':status(runner),'server_public_key':wire.public(settings.RUNNER_SIGNING_KEY)})

def response(request,body):
    return wire.sign(settings.RUNNER_SIGNING_KEY,'response',{'version':wire.VERSION,'audience':settings.RUNNER_ORIGIN,
        'timestamp':int(timezone.now().timestamp()),'nonce':request['nonce'],'body':body})

def authenticate(message):
    enabled();wire.fields(message,'payload signature');payload=message['payload']
    wire.fields(payload,'version runner_id audience timestamp nonce body');wire.fresh(payload,settings.RUNNER_ORIGIN)
    try:identifier=uuid.UUID(payload['runner_id'])
    except (ValueError,TypeError,AttributeError):raise wire.ProtocolError('runner_authentication_failed') from None
    runner=CustomerRunner.objects.select_related('target__project__organization').filter(pk=identifier).first()
    wire.require(runner and not runner.revoked_at and runner.target.project.active and runner.target.project.organization.active,'runner_authentication_failed')
    wire.verify(runner.public_key,'request',message)
    wire.require(consume_rate('runner-identity',str(identifier),120,60),'runner_rate_limited')
    try:
        with transaction.atomic():
            expired=RunnerNonce.objects.filter(runner=runner,expires_at__lt=timezone.now()).values_list('pk',flat=True)[:250]
            RunnerNonce.objects.filter(pk__in=list(expired)).delete()
            RunnerNonce.objects.create(runner=runner,nonce=payload['nonce'],expires_at=timezone.now()+timedelta(seconds=125))
    except IntegrityError:raise wire.ProtocolError('runner_request_replayed') from None
    CustomerRunner.objects.filter(pk=runner.pk,revoked_at__isnull=True).update(last_seen=timezone.now())
    return runner,payload

def heartbeat(runner,body):
    wire.fields(body,'operation inventory');info=inventory(body['inventory'])
    with transaction.atomic():
        runner=CustomerRunner.objects.select_for_update().select_related('target').get(pk=runner.pk)
        wire.require(not runner.revoked_at,'runner_authentication_failed')
        if wire.fingerprint(info)!=runner.inventory_sha256:
            runner.quarantined=True
            audit(None,'runner.identity_changed',runner.target.project.organization,runner.pk)
        runner.last_seen=timezone.now();runner.save(update_fields=['last_seen','quarantined'])
        state=status(runner)
        Target.objects.filter(pk=runner.pk).update(state=state,last_seen=runner.last_seen,
            inventory=public_inventory(runner))
    return {'state':state,'heartbeat_after_seconds':30,'lifecycle_qualified_by_connection':False}

def approve(actor,target,expected_fingerprint):
    with transaction.atomic():
        target=Target.objects.select_for_update().get(pk=target.pk)
        runner=CustomerRunner.objects.select_for_update().select_related('target').get(pk=target.pk)
        wire.require(not runner.revoked_at and not runner.quarantined and expected_fingerprint==runner.inventory_sha256,'runner_approval_changed')
        wire.require(status(runner)!='incompatible','runner_incompatible')
        runner.approved_at=timezone.now();runner.save(update_fields=['approved_at'])
        target.approved=True;runner.target=target;target.state=status(runner);target.save(update_fields=['approved','state'])
        audit(actor,'runner.approved',target.project.organization,target.pk,inventory_sha256=runner.inventory_sha256)

def revoke(actor,target):
    with transaction.atomic():
        target=Target.objects.select_for_update().get(pk=target.pk)
        runner=CustomerRunner.objects.select_for_update().get(pk=target.pk)
        runner.revoked_at=timezone.now();runner.save(update_fields=['revoked_at'])
        target.approved=False;target.state='quarantined';target.quarantine_reason='runner_revoked';target.save(update_fields=['approved','state','quarantine_reason'])
        audit(actor,'runner.revoked',target.project.organization,target.pk)
