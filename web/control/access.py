"""One-time-display codes and server-side revocable browser sessions."""
from datetime import timedelta
import hashlib,hmac,re,secrets,uuid
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from .models import AccessCode,AccessGrant,AccessSession,Project,Target,Run,AuditEvent
from .security import organization_member,project_access,audit,session_valid,AccessPrincipal

GRAMMAR=re.compile(r'rmc_([0-9a-f]{32})_([A-Za-z0-9_-]{43})\Z')
def verifier(raw):return hmac.new(settings.SECRET_KEY.encode(),('resmgrcheck-access-code-v1:'+raw).encode(),hashlib.sha256).hexdigest()
def browser_binding(key):return hmac.new(settings.SECRET_KEY.encode(),('resmgrcheck-browser-session-v1:'+key).encode(),hashlib.sha256).hexdigest()

class RedemptionDenied(Exception):pass

@sensitive_variables('raw')
def create_code(actor,organization,description,grants,*,expires_at=None,max_redemptions=None,max_sessions=1,allow_live=False,allow_ai=False):
    organization_member(actor,organization.pk,'admin')
    if re.search(r'rmc_[0-9a-f]{32}_[A-Za-z0-9_-]{43}',description):raise ValueError('Do not store access secrets in metadata')
    if not 1<=max_sessions<=20 or max_redemptions is not None and not 1<=max_redemptions<=1000:raise ValueError('Invalid redemption/session limits')
    if expires_at and expires_at<=timezone.now():raise ValueError('Expiration must be in the future')
    if not grants or len(grants)>20:raise ValueError('Choose explicit project grants')
    identifier=uuid.uuid4();raw='rmc_'+identifier.hex+'_'+secrets.token_urlsafe(32)
    with transaction.atomic():
        code=AccessCode.objects.create(id=identifier,organization=organization,description=description,verifier=verifier(raw),created_by=actor,
            expires_at=expires_at,max_redemptions=max_redemptions,max_sessions=max_sessions,allow_live=allow_live,allow_ai=allow_ai)
        for selected in grants:
            project=selected['project'];project_access(actor,project.pk,'admin')
            if project.organization_id!=organization.pk:raise ValueError('Project organization mismatch')
            targets=list(selected.get('targets',[]));evidence=list(selected.get('evidence',[]))
            if any(t.project_id!=project.pk for t in targets) or any(r.project_id!=project.pk or r.target_id not in {t.pk for t in targets} for r in evidence):raise ValueError('Target/evidence scope mismatch')
            grant=AccessGrant.objects.create(code=code,project=project,can_run=selected.get('can_run',False) and allow_live,
                can_ai=selected.get('can_ai',False) and allow_ai,can_download=selected.get('can_download',False),all_evidence=selected.get('all_evidence',False))
            grant.targets.set(targets);grant.evidence.set(evidence)
        audit(actor,'access_code.created',organization,code.pk,project_ids=[str(g['project'].pk) for g in grants],allow_live=allow_live,allow_ai=allow_ai,max_sessions=max_sessions,max_redemptions=max_redemptions)
    return code,raw

@sensitive_variables('raw','calculated')
def redeem(request,raw):
    match=GRAMMAR.fullmatch(raw.strip()) if isinstance(raw,str) else None
    calculated=verifier(raw.strip() if isinstance(raw,str) else '')
    if not match:raise RedemptionDenied
    now=timezone.now()
    with transaction.atomic():
        code=AccessCode.objects.select_for_update(of=('self',)).select_related('organization').filter(pk=uuid.UUID(hex=match[1])).first()
        if not code or not hmac.compare_digest(code.verifier,calculated):raise RedemptionDenied
        if code.revoked_at or not code.organization.active or code.expires_at and code.expires_at<=now:raise RedemptionDenied
        if code.max_redemptions is not None and code.redemptions>=code.max_redemptions:raise RedemptionDenied
        active=code.sessions.filter(revoked_at=None,expires_at__gt=now,last_access__gt=now-timedelta(minutes=30),policy_version=code.policy_version).count()
        if active>=code.max_sessions or not code.grants.filter(project__active=True).exists():raise RedemptionDenied
        request.session.cycle_key()
        if not request.session.session_key:request.session.save()
        expires=min(now+timedelta(hours=12),code.expires_at) if code.expires_at else now+timedelta(hours=12)
        session=AccessSession.objects.create(code=code,browser_key_hash=browser_binding(request.session.session_key),policy_version=code.policy_version,last_access=now,expires_at=expires)
        code.redemptions+=1;code.last_access=now;code.save(update_fields=['redemptions','last_access'])
        request.session['rmc_access_session']=str(session.pk)
        audit(AccessPrincipal(session),'access_code.redeemed',code.organization,code.pk,redemption=code.redemptions)
    return session

def revoke_code(actor,identifier):
    with transaction.atomic():
        code=AccessCode.objects.select_for_update().select_related('organization').get(pk=identifier)
        organization_member(actor,code.organization_id,'admin')
        if code.revoked_at:return code
        now=timezone.now();code.revoked_at=now;code.policy_version+=1;code.save(update_fields=['revoked_at','policy_version'])
        count=code.sessions.filter(revoked_at=None).update(revoked_at=now)
        audit(actor,'access_code.revoked',code.organization,code.pk,sessions_revoked=count)
        return code
