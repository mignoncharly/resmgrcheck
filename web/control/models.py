"""Durable, explicitly scoped control-plane records; canonical verdicts stay engine-owned."""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

class UserManager(BaseUserManager):
    def create_user(self,email,password=None,**extra):
        if not email: raise ValueError('Email is required')
        user=self.model(email=self.normalize_email(email).lower(),**extra)
        user.set_password(password);user.save(using=self._db);return user
    def create_superuser(self,email,password=None,**extra):
        extra.update(is_staff=True,is_superuser=True)
        return self.create_user(email,password,**extra)

class User(AbstractUser):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    username=None
    email=models.EmailField(unique=True)
    USERNAME_FIELD='email'; REQUIRED_FIELDS=[]
    objects=UserManager()
    class Meta:
        constraints=[models.UniqueConstraint(Lower('email'),name='user_email_casefold_unique')]
    def save(self,*args,**kwargs):
        self.email=self.email.strip().lower();super().save(*args,**kwargs)

class Organization(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100)
    created_at=models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)
    retention_days=models.PositiveIntegerField(default=30)

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
    action=models.CharField(max_length=80)
    object_id=models.CharField(max_length=80,blank=True)
    details=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
