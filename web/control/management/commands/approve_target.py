"""Local operator action, never an HTTP approval or arbitrary customer SSH route."""
from pathlib import Path
import json,os
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from control.models import Project,Target,BuildRelease
from control.security import audit
from resmgrcheck.transport import Target as EngineTarget
from resmgrcheck.deployment import Deployment
from resmgrcheck.contracts import load,canonical
from resmgrcheck.artifacts import atomic_write

class Command(BaseCommand):
    help='Approve an existing private engine route/build for one explicit project. Local operator only.'
    def add_arguments(self,p):
        for name in ['project','engine-root','config','alias','manifest','registry']:p.add_argument('--'+name,required=True)
        p.add_argument('--target');p.add_argument('--name',default='Approved private QNX lab');p.add_argument('--build-label',default='Operator-verified build')
        p.add_argument('--kind',choices=['managed-lab','external-health'],default='managed-lab')
    def handle(self,*args,**o):
        project=Project.objects.get(pk=o['project']);root=Path(o['engine_root']).resolve();configuration=Path(o['config']).resolve()
        if not (root/'resmgrcheck/__main__.py').is_file():raise CommandError('Pinned CLI checkout is required')
        target_data=EngineTarget.read(o['alias'],configuration)
        selected=Deployment.parse(load(o['manifest']))
        for a,b in [('recipe_id','recipe_id'),('architecture','processor'),('machine','machine'),('release','release'),('uid','uid')]:
            if selected.data[a]!=target_data.data[b]:raise CommandError('Build/target compatibility mismatch: '+a)
        path=Path(o['registry']).resolve();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        if path.exists():
            if path.is_symlink() or path.stat().st_mode & 0o077:raise CommandError('Private registry must be0600 and nonsymlink')
            registry=load(path)
            if set(registry)!={'schema_version','targets'} or registry['schema_version']!=1:raise CommandError('Unknown existing registry schema')
        else:registry={'schema_version':1,'targets':{}}
        with transaction.atomic():
            if o['target']:
                target=Target.objects.select_for_update().get(pk=o['target'],project=project)
            else:target=Target.objects.create(project=project,name=o['name'],kind=o['kind'])
            row=registry['targets'].get(str(target.pk))
            expected={'organization_id':str(project.organization_id),'project_id':str(project.pk),'engine_root':str(root),'config':str(configuration),'alias':o['alias']}
            if row and any(row[k]!=v for k,v in expected.items()):raise CommandError('Existing target route cannot be silently replaced; register a new target')
            row=row or {**expected,'builds':{}}
            build=BuildRelease.objects.create(target=target,label=o['build_label'],manifest=selected.data)
            build.binding=str(build.pk);build.approved=True;build.save(update_fields=['binding','approved'])
            row['builds'][str(build.pk)]=str(Path(o['manifest']).resolve());registry['targets'][str(target.pk)]=row
            atomic_write(path,canonical(registry)+b'\n');path.chmod(0o600)
            target.binding=str(target.pk);target.approved=True;target.kind=o['kind'];target.save(update_fields=['binding','approved','kind'])
            active=root/'.local/state'/o['alias']/'deployment.json';active.parent.mkdir(parents=True,exist_ok=True)
            if not active.exists():atomic_write(active,canonical(selected.data)+b'\n')
            audit(None,'operator.target_build_approved',project.organization,target.pk,build_id=str(build.pk),deployment_id=selected.data['deployment_id'])
        self.stdout.write(json.dumps({'target_id':str(target.pk),'build_id':str(build.pk),'approved':True,'reachability':'unknown until actual inventory'}))
