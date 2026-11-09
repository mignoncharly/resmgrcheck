from django import forms
from .models import Membership,Project,Organization

class OrganizationForm(forms.ModelForm):
    class Meta:model=Organization;fields=['name']
class ProjectForm(forms.ModelForm):
    class Meta:model=Project;fields=['name','description']
class PasswordConfirmation(forms.Form):
    password=forms.CharField(widget=forms.PasswordInput)
class MemberForm(forms.Form):
    role=forms.ChoiceField(choices=Membership.Role.choices)
    active=forms.BooleanField(required=False)
class ProjectMemberForm(forms.Form):
    user_id=forms.UUIDField()
    role=forms.ChoiceField(choices=[('developer','Developer'),('viewer','Viewer')])

import json
from .models import Target,BuildRelease
from resmgrcheck.deployment import Deployment
from resmgrcheck.contracts import Profile,load
from resmgrcheck.workflow import suite_profiles
from django.conf import settings

class TargetRequestForm(forms.ModelForm):
    class Meta:model=Target;fields=['name']

class RunForm(forms.Form):
    target=forms.ModelChoiceField(queryset=Target.objects.none())
    build=forms.ModelChoiceField(queryset=BuildRelease.objects.none())
    profile=forms.ChoiceField(choices=[('sensor','Sensor'),('job','Job')])
    suite=forms.ChoiceField(choices=[('profile','Timeout and baselines'),('lifecycle','Lifecycle and 20 reconnect cycles'),('health','External read-only health')])
    fixture_mode=forms.ChoiceField(choices=[('fixed','Fixed'),('ignore-unblock','Intentional ignore-unblock defect'),('retain-waiter','Intentional retained waiter'),('retain-third','Intentional third-cycle retention'),('duplicate-terminal','Intentional duplicate terminal'),('drop-job','Intentional dropped job')])
    idempotency_key=forms.RegexField(r'^[A-Za-z0-9_-]{16,64}$',widget=forms.HiddenInput)
    confirmation=forms.CharField(required=False,widget=forms.HiddenInput,max_length=2000)
    confirmed=forms.BooleanField(required=False,widget=forms.HiddenInput)
    def __init__(self,*args,project,principal=None,**kwargs):
        super().__init__(*args,**kwargs)
        from .security import visible_targets
        allowed=visible_targets(principal) if principal is not None else Target.objects.filter(project=project)
        self.fields['target'].queryset=allowed.filter(project=project,approved=True)
        self.fields['build'].queryset=BuildRelease.objects.filter(target__in=self.fields['target'].queryset,approved=True)
    def clean(self):
        data=super().clean();target=data.get('target');build=data.get('build')
        if target and build and build.target_id!=target.pk:self.add_error('build','Choose an approved build for this exact target.')
        if target and target.state=='quarantined':self.add_error('target','Target is quarantined pending owned-run recovery.')
        if target and target.kind=='external-health' and data.get('suite')!='health':self.add_error('suite','UNSUPPORTED: external lifecycle observers and build identity are not available.')
        if data.get('profile')=='sensor' and data.get('fixture_mode')=='drop-job':self.add_error('fixture_mode','UNSUPPORTED: the sensor adapter has no retained job obligation.')
        if data.get('fixture_mode')=='retain-third' and data.get('suite')=='profile':self.add_error('suite','Choose lifecycle to exercise the third reconnect cycle.')
        if target and data.get('profile'):
            external=target.kind=='external-health' or (target.kind=='customer-runner' and target.customerrunner.inventory['attachment']=='external-attach')
            profile=Profile.parse(load(settings.REPO_ROOT/'profiles'/(data['profile']+('-external' if external else '')+'.json')))
            caps=target.inventory.get('compiled_adapters',{}).get(profile.data['adapter']['id'])
            if caps is None:self.add_error('target','Capabilities are UNKNOWN. Request a private inventory first.')
            elif data.get('suite'):
                try:expanded=suite_profiles(profile,data['suite'])
                except ValueError:self.add_error('suite','This suite is unavailable for the selected attachment mode.')
                else:
                    required=set().union(*(set(p.data['capabilities']['required']) for p in expanded))
                    if not required<=set(caps):self.add_error('profile','UNSUPPORTED: required compiled capabilities are unavailable for the full suite.')
        return data

class BuildImportForm(forms.Form):
    label=forms.CharField(max_length=100)
    manifest=forms.FileField(help_text='Deployment manifest JSON only; approval requires an operator-verified local build. No binaries accepted.')
    def clean_manifest(self):
        upload=self.cleaned_data['manifest']
        if upload.size>131072:raise forms.ValidationError('Manifest exceeds 128 KiB.')
        try:value=json.loads(upload.read());return Deployment.parse(value).data
        except Exception:raise forms.ValidationError('manifest: expected a valid versioned deployed-build identity with matching hashes.')
