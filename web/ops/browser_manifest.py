from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from control.models import Run,Target,Project
credentials=json.loads((settings.PRIVATE_ROOT/'acceptance-administrator.json').read_text())
project=Project.objects.get(pk=credentials['project_id']);target=Target.objects.get(project=project,approved=True,kind='managed-lab')
runs=Run.objects.filter(project=project)
result={'project_id':str(project.pk),'organization_id':str(project.organization_id),'target_id':str(target.pk),
 'fixed':str(runs.filter(operation='run',profile='sensor',fixture_mode='fixed',summary__execution_exit=0).first().pk),
 'broken':str(runs.filter(operation='run',profile='sensor',fixture_mode='ignore-unblock',summary__execution_exit=1).first().pk),
 'replay':str(runs.filter(operation='replay').first().pk),'job':str(runs.filter(operation='run',profile='job').first().pk),
 'transfer':str(runs.filter(error_code='prelaunch_infrastructure_error').first().pk)}
(settings.PRIVATE_ROOT/'browser-manifest.json').write_text(json.dumps(result))
print('Browser acceptance references written privately; no credentials printed.')
