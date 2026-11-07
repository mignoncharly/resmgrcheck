from django import forms
from .models import Membership,Project,Organization

class OrganizationForm(forms.ModelForm):
    class Meta:model=Organization;fields=['name']
class ProjectForm(forms.ModelForm):
    class Meta:model=Project;fields=['name','description']
class InvitationForm(forms.Form):
    email=forms.EmailField()
    role=forms.ChoiceField(choices=Membership.Role.choices)
class PasswordConfirmation(forms.Form):
    password=forms.CharField(widget=forms.PasswordInput)
class MemberForm(forms.Form):
    role=forms.ChoiceField(choices=Membership.Role.choices)
    active=forms.BooleanField(required=False)
class ProjectMemberForm(forms.Form):
    user_id=forms.UUIDField()
    role=forms.ChoiceField(choices=[('developer','Developer'),('viewer','Viewer')])
