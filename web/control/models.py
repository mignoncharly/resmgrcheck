"""Durable, explicitly scoped control-plane records; canonical verdicts stay engine-owned."""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

class UserManager(BaseUserManager):
    def create_user(self,username,password=None,**extra):
        if not username: raise ValueError('Administrator username is required')
        extra.setdefault('is_staff',True)
        user=self.model(username=username.strip().lower(),**extra)
        user.set_password(password);user.save(using=self._db);return user
    def create_superuser(self,username,password=None,**extra):
        extra.update(is_staff=True,is_superuser=True)
        return self.create_user(username,password,**extra)

class User(AbstractUser):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    username=models.CharField(max_length=40,unique=True,null=True,blank=True)
    email=models.EmailField(unique=True,null=True,blank=True) # Legacy audit identity only; no email workflow.
    session_version=models.PositiveIntegerField(default=1)
    USERNAME_FIELD='username'; REQUIRED_FIELDS=[]
    objects=UserManager()
    class Meta:
        constraints=[models.UniqueConstraint(Lower('email'),name='user_email_casefold_unique'),models.UniqueConstraint(Lower('username'),name='administrator_username_casefold_unique'),models.CheckConstraint(condition=models.Q(is_active=False)|models.Q(is_staff=True,username__isnull=False),name='active_accounts_are_administrators')]
    def save(self,*args,**kwargs):
        if self.email:self.email=self.email.strip().lower()
        if self.username:self.username=self.username.strip().lower()
        super().save(*args,**kwargs)
    def _get_session_auth_hash(self,secret=None):
        from django.utils.crypto import salted_hmac
        return salted_hmac('resmgrcheck.User.session',f'{self.password}:{self.session_version}',secret=secret,algorithm='sha256').hexdigest()

class Organization(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100)
    created_at=models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)
    retention_days=models.PositiveIntegerField(default=30)
    def __str__(self):return self.name

class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER='owner','Owner';ADMIN='admin','Administrator';DEVELOPER='developer','Developer';VIEWER='viewer','Viewer'
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    user=models.ForeignKey(User,on_delete=models.PROTECT)
    role=models.CharField(max_length=16,choices=Role.choices)
    active=models.BooleanField(default=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['organization','user'],name='unique_organization_member')]

class Project(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    name=models.CharField(max_length=100)
    description=models.TextField(blank=True,max_length=2000)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)
    ai_enabled=models.BooleanField(default=False)
    ai_daily_budget_microusd=models.PositiveBigIntegerField(default=0)
    def __str__(self):return self.name
    class Meta:
        constraints=[models.UniqueConstraint(fields=['organization','name'],name='unique_project_name')]

class ProjectMembership(models.Model):
    project=models.ForeignKey(Project,on_delete=models.PROTECT)
    user=models.ForeignKey(User,on_delete=models.PROTECT)
    role=models.CharField(max_length=16,choices=[('developer','Developer'),('viewer','Viewer')])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['project','user'],name='unique_project_member')]

class AuditEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,null=True,on_delete=models.PROTECT)
    actor=models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    access_session=models.ForeignKey('AccessSession',null=True,on_delete=models.PROTECT)
    access_code=models.ForeignKey('AccessCode',null=True,on_delete=models.PROTECT)
    action=models.CharField(max_length=80)
    object_id=models.CharField(max_length=80,blank=True)
    details=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']

class RateBucket(models.Model):
    key=models.CharField(max_length=64,primary_key=True)
    count=models.PositiveIntegerField(default=0)
    expires_at=models.DateTimeField(db_index=True)

class Invitation(models.Model):
    """Archived historical row; no invitation route/task remains."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    email=models.EmailField()
    role=models.CharField(max_length=16,choices=Membership.Role.choices)
    token_hash=models.CharField(max_length=64,unique=True)
    invited_by=models.ForeignKey(User,on_delete=models.PROTECT)
    expires_at=models.DateTimeField()
    accepted_at=models.DateTimeField(null=True)

class AccountDeletion(models.Model):
    """Archived historical request; superseded public-account erasure is inactive."""
    user=models.OneToOneField(User,on_delete=models.PROTECT)
    requested_at=models.DateTimeField(auto_now_add=True)
    due_at=models.DateTimeField()
    completed_at=models.DateTimeField(null=True)

class Target(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey(Project,on_delete=models.PROTECT)
    name=models.CharField(max_length=100)
    kind=models.CharField(max_length=24,choices=[('managed-lab','Approved managed fixtures'),('external-health','External read-only health'),('customer-request','Legacy customer runner request'),('customer-runner','Customer-owned outbound runner')],default='customer-request')
    state=models.CharField(max_length=20,default='unknown',choices=[(s,s) for s in ['unknown','available','unavailable','unsupported','quarantined','pending-approval','connected','disconnected','incompatible']])
    approved=models.BooleanField(default=False)
    binding=models.CharField(max_length=64,blank=True)
    inventory=models.JSONField(default=dict)
    last_seen=models.DateTimeField(null=True)
    quarantine_reason=models.CharField(max_length=100,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):return self.name
    @property
    def connection_state(self):
        if self.kind=='customer-runner':
            from .runners import status
            try:return status(self.customerrunner)
            except CustomerRunner.DoesNotExist:return 'pending-approval'
        return self.state

class BuildRelease(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    target=models.ForeignKey(Target,on_delete=models.PROTECT)
    label=models.CharField(max_length=100)
    manifest=models.JSONField(default=dict)
    approved=models.BooleanField(default=False)
    binding=models.CharField(max_length=64,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):return self.label+' · '+self.manifest.get('build',{}).get('source_revision','unverified')[:12]

class CustomerRunner(models.Model):
    """One immutable cryptographic identity per exact target. No SSH/SDK material."""
    target=models.OneToOneField(Target,primary_key=True,on_delete=models.PROTECT)
    public_key=models.CharField(max_length=64,unique=True)
    inventory=models.JSONField(default=dict)
    inventory_sha256=models.CharField(max_length=64)
    approved_at=models.DateTimeField(null=True)
    revoked_at=models.DateTimeField(null=True)
    last_seen=models.DateTimeField(null=True)
    quarantined=models.BooleanField(default=False)
    daily_limit=models.PositiveSmallIntegerField(default=20)
    created_at=models.DateTimeField(auto_now_add=True)

class RunnerEnrollment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    target=models.ForeignKey(Target,on_delete=models.PROTECT)
    verifier=models.CharField(max_length=64)
    expires_at=models.DateTimeField()
    used_at=models.DateTimeField(null=True)
    revoked_at=models.DateTimeField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)

class RunnerNonce(models.Model):
    runner=models.ForeignKey(CustomerRunner,on_delete=models.PROTECT)
    nonce=models.CharField(max_length=32)
    expires_at=models.DateTimeField(db_index=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['runner','nonce'],name='runner_nonce_once')]

class RunnerJob(models.Model):
    run=models.OneToOneField('Run',primary_key=True,on_delete=models.PROTECT)
    runner=models.ForeignKey(CustomerRunner,on_delete=models.PROTECT)
    ticket=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    intent=models.JSONField()
    state=models.CharField(max_length=24,default='offered',db_index=True)
    offered_at=models.DateTimeField(auto_now_add=True)
    launch_granted_at=models.DateTimeField(null=True)
    archive_sha256=models.CharField(max_length=64,blank=True)
    archive_bytes=models.PositiveIntegerField(default=0)
    ingest_lease=models.DateTimeField(null=True)
    ingest_token=models.UUIDField(null=True)

class RunnerChunk(models.Model):
    job=models.ForeignKey(RunnerJob,on_delete=models.PROTECT)
    index=models.PositiveSmallIntegerField()
    data=models.BinaryField()
    sha256=models.CharField(max_length=64)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['job','index'],name='runner_upload_chunk_once')]

class Run(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey(Project,on_delete=models.PROTECT)
    target=models.ForeignKey(Target,on_delete=models.PROTECT)
    build=models.ForeignKey(BuildRelease,null=True,on_delete=models.PROTECT)
    actor=models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    access_session=models.ForeignKey('AccessSession',null=True,on_delete=models.PROTECT)
    actor_auth_hash=models.CharField(max_length=64)
    mfa_at=models.DateTimeField()
    native_run_id=models.CharField(max_length=40,unique=True)
    operation=models.CharField(max_length=16,choices=[('run','Run'),('replay','Replay'),('inventory','Inventory')])
    original=models.ForeignKey('self',null=True,on_delete=models.PROTECT)
    profile=models.CharField(max_length=16,choices=[('sensor','Sensor'),('job','Job')],default='sensor')
    suite=models.CharField(max_length=16,choices=[('profile','Timeout family'),('lifecycle','Complete lifecycle'),('health','Read-only external health')],default='profile')
    fixture_mode=models.CharField(max_length=24,default='fixed')
    idempotency_key=models.CharField(max_length=64)
    intent_sha256=models.CharField(max_length=64)
    state=models.CharField(max_length=24,default='queued',db_index=True)
    lease_token=models.UUIDField(null=True)
    lease_expires=models.DateTimeField(null=True)
    heartbeat_at=models.DateTimeField(null=True)
    cancel_requested=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    started_at=models.DateTimeField(null=True)
    finished_at=models.DateTimeField(null=True)
    summary=models.JSONField(default=dict)
    incidents=models.JSONField(default=list)
    error_code=models.CharField(max_length=100,blank=True)
    process_facts=models.JSONField(default=dict)
    progress=models.CharField(max_length=300,blank=True)
    target_cleanup_verified=models.BooleanField(default=False)
    purged_at=models.DateTimeField(null=True)
    retention_hold=models.BooleanField(default=False)
    purge_error=models.CharField(max_length=100,blank=True)
    def __str__(self):return self.native_run_id+' · '+self.profile+' / '+self.suite
    class Meta:
        constraints=[models.UniqueConstraint(fields=['project','actor','idempotency_key'],name='run_request_dedup'),models.UniqueConstraint(fields=['project','access_session','idempotency_key'],name='code_run_request_dedup'),models.CheckConstraint(condition=models.Q(actor__isnull=False,access_session__isnull=True)|models.Q(actor__isnull=True,access_session__isnull=False),name='run_exact_principal')]
        ordering=['-created_at']

class ExecutorSlot(models.Model):
    name=models.CharField(max_length=64,primary_key=True)
    run=models.ForeignKey(Run,null=True,on_delete=models.PROTECT)
    token=models.UUIDField(null=True)
    expires_at=models.DateTimeField(null=True)

class Artifact(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey(Run,on_delete=models.PROTECT)
    relative_path=models.CharField(max_length=500)
    sha256=models.CharField(max_length=64)
    byte_count=models.PositiveBigIntegerField()
    content_type=models.CharField(max_length=80)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','relative_path'],name='artifact_path_per_run')]

class SourceSubmission(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey(Project,on_delete=models.PROTECT)
    actor=models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    access_session=models.ForeignKey('AccessSession',null=True,on_delete=models.PROTECT)
    label=models.CharField(max_length=80)
    original_sha256=models.CharField(max_length=64)
    redacted_sha256=models.CharField(max_length=64)
    redacted_text=models.TextField()
    redactions=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()
    erased_at=models.DateTimeField(null=True)
    def __str__(self):return self.label+' · '+self.original_sha256[:12]
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(actor__isnull=False,access_session__isnull=True)|models.Q(actor__isnull=True,access_session__isnull=False),name='source_exact_principal')]

class AIAnalysis(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey(Run,on_delete=models.PROTECT)
    actor=models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    access_session=models.ForeignKey('AccessSession',null=True,on_delete=models.PROTECT)
    source=models.ForeignKey(SourceSubmission,null=True,on_delete=models.PROTECT)
    compared_run=models.ForeignKey(Run,null=True,on_delete=models.PROTECT,related_name='ai_comparisons')
    actor_auth_hash=models.CharField(max_length=64)
    mfa_at=models.DateTimeField()
    idempotency_key=models.CharField(max_length=64)
    task=models.CharField(max_length=24)
    input_sha256=models.CharField(max_length=64)
    payload=models.JSONField(default=dict)
    citations=models.JSONField(default=dict)
    provider=models.CharField(max_length=30)
    requested_model=models.CharField(max_length=100)
    resolved_model=models.CharField(max_length=100,blank=True)
    provider_response_id=models.CharField(max_length=150,blank=True)
    provider_request_id=models.CharField(max_length=150,blank=True)
    pricing=models.JSONField(default=dict)
    reserved_microusd=models.PositiveBigIntegerField()
    accounted_microusd=models.PositiveBigIntegerField()
    usage_established=models.BooleanField(default=False)
    usage=models.JSONField(default=dict)
    state=models.CharField(max_length=24,default='queued',db_index=True)
    result=models.JSONField(default=dict)
    output_sha256=models.CharField(max_length=64,blank=True)
    error_code=models.CharField(max_length=100,blank=True)
    consent_version=models.CharField(max_length=30,default='evidence-egress-v1')
    created_at=models.DateTimeField(auto_now_add=True)
    started_at=models.DateTimeField(null=True)
    finished_at=models.DateTimeField(null=True)
    erased_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['actor','run','idempotency_key'],name='ai_request_dedup'),models.UniqueConstraint(fields=['access_session','run','idempotency_key'],name='code_ai_request_dedup'),models.CheckConstraint(condition=models.Q(actor__isnull=False,access_session__isnull=True)|models.Q(actor__isnull=True,access_session__isnull=False),name='ai_exact_principal')]
        ordering=['-created_at']

class AIUsage(models.Model):
    scope=models.CharField(max_length=64)
    day=models.DateField()
    accounted_microusd=models.PositiveBigIntegerField(default=0)
    requests=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['scope','day'],name='ai_usage_scope_day')]

class AILease(models.Model):
    name=models.CharField(max_length=30,primary_key=True)
    analysis=models.ForeignKey(AIAnalysis,null=True,on_delete=models.PROTECT)
    token=models.UUIDField(null=True)
    expires_at=models.DateTimeField(null=True)

class AIProviderState(models.Model):
    name=models.CharField(primary_key=True,max_length=30)
    policy=models.JSONField(default=dict)
    available=models.BooleanField(default=False)
    refreshed_at=models.DateTimeField()
    verified_at=models.DateTimeField(null=True)

class AccessCode(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    description=models.CharField(max_length=160)
    verifier=models.CharField(max_length=64)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField(null=True)
    max_redemptions=models.PositiveIntegerField(null=True)
    max_sessions=models.PositiveIntegerField(default=1)
    redemptions=models.PositiveIntegerField(default=0)
    last_access=models.DateTimeField(null=True)
    revoked_at=models.DateTimeField(null=True)
    policy_version=models.PositiveIntegerField(default=1)
    allow_live=models.BooleanField(default=False)
    allow_ai=models.BooleanField(default=False)

class AccessGrant(models.Model):
    code=models.ForeignKey(AccessCode,on_delete=models.PROTECT,related_name='grants')
    project=models.ForeignKey(Project,on_delete=models.PROTECT)
    can_run=models.BooleanField(default=False)
    can_ai=models.BooleanField(default=False)
    can_download=models.BooleanField(default=False)
    all_evidence=models.BooleanField(default=False)
    targets=models.ManyToManyField(Target,blank=True)
    evidence=models.ManyToManyField(Run,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['code','project'],name='access_code_project_grant')]

class AccessSession(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    code=models.ForeignKey(AccessCode,on_delete=models.PROTECT,related_name='sessions')
    browser_key_hash=models.CharField(max_length=64,unique=True)
    policy_version=models.PositiveIntegerField()
    created_at=models.DateTimeField(auto_now_add=True)
    last_access=models.DateTimeField()
    expires_at=models.DateTimeField()
    revoked_at=models.DateTimeField(null=True)
