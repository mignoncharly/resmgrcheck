"""Expand validated contracts; no transport and no user-supplied commands."""
from pathlib import Path
import hashlib
import subprocess
from .contracts import Profile, Plan, digest, IDENTITY, text
from .registrations import REGISTRY
from .build_identity import source_hash
from .contracts import load, require

def expand(profile, run_id, mode='corrected', root=Path('.')):
    if not isinstance(profile, Profile): profile=Profile.parse(profile)
    text(run_id)
    reg=REGISTRY[profile.data['adapter']['id']]
    root=Path(root)
    binary_root=root/'build/qnx-x86_64'
    names={'runner':'runner','worker':'worker','fixture':reg.fixture,'adapter':'worker'}
    binaries={key:hashlib.sha256((binary_root/name).read_bytes()).hexdigest() for key,name in names.items()}
    build=load(binary_root/'build-info.json')
    require(source_hash(root)==build['source_tree_sha256'], 'build source has changed: run make qnx')
    require(all(binaries[k]==build['binaries'][n] for k,n in names.items()), 'build artifact mismatch: run make qnx')
    revision=build['source_revision']; dirty=build['dirty']
    recipe=root/'.local/qnx-lab/output/ifs.bin'
    data={'kind':'scenario-plan','schema_version':1,'run_id':run_id,'case_id':'timeout', 'attempt_id':'attempt1',
          'cycle':1,'service_instance_id':run_id,'profile':profile.data,
          'profile_sha256':digest(profile.data),'suite_sha256':digest(profile.data['suite']),
          'fixture_mode':mode,'builds':{'source_revision':revision,'dirty':dirty,'source_tree_sha256':build['source_tree_sha256'],'compiler_variant':'gcc_ntox86_64',
                                      'recipe_id':hashlib.sha256(recipe.read_bytes()).hexdigest(),'binaries':binaries}}
    return Plan.parse(data)
