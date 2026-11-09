"""Customer-local configuration with dummy routing. Never contacts a target."""
import json
from pathlib import Path
from django.conf import settings
from customer_runner.client import create
from customer_runner.agent import route_fingerprint
from resmgrcheck.build_identity import source_hash
from .test_runners import discovery

def local(root,target_id,project_id,organization_id):
    source=settings.REPO_ROOT/'docs/evidence/phase10/executions/p10demo2-normal'
    request=json.loads((source/'request.json').read_text())
    create(root/'ssh-config',b'Host fixture-only\n HostName 192.0.2.1\n')
    route={**request['target_identity'],'ssh_alias':'fixture-only','ssh_config':str(root/'ssh-config'),'timeout_s':5}
    create(root/'target.json',json.dumps({'kind':'target-configuration','schema_version':1,'targets':{'fixture':route}}).encode())
    create(root/'build.json',json.dumps(request['deployment']).encode())
    config={'origin':'https://qnx-resmgrcheck.gestionatech.de','server_public_key':'0'*64,
        'target_id':str(target_id),'project_id':str(project_id),'organization_id':str(organization_id),
        'engine_root':str(settings.REPO_ROOT),'target_config':str(root/'target.json'),'alias':'fixture',
        'manifests':{request['deployment']['deployment_id']:str(root/'build.json')},'attachment':'managed-fixture','allowed_modes':['corrected']}
    inventory=discovery();inventory['target_identity']=request['target_identity']
    inventory['engine_sha256']=source_hash(settings.REPO_ROOT);inventory['route_sha256']=route_fingerprint(config)
    return source,request,config,inventory
