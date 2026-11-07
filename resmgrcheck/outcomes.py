"""Host infrastructure outcomes never invent target observations or cleanup."""
import hashlib
from .contracts import Plan,EvaluatedResult,IDENTITY,require

def infrastructure_error(plan,reason,partial=b''):
    if not isinstance(plan,Plan):plan=Plan.parse(plan)
    require(reason in {'target_unreachable','transport_incomplete','target_completion_unestablished'},'unknown infrastructure reason')
    data={'kind':'evaluated-result','schema_version':1,**{k:plan.data[k] for k in IDENTITY.split()},
      'fixture_mode':plan.data['fixture_mode'],'verdict':'ERROR','reasons':[reason],'completion':'incomplete',
      'profile_sha256':plan.data['profile_sha256'],'event_sha256':hashlib.sha256(partial).hexdigest(),
      'assertions':[{'id':reason,'verdict':'ERROR','event_refs':[]},
                    {'id':'scenario_execution','verdict':'NOT_RUN','event_refs':[]},
                    {'id':'remote_cleanup','verdict':'NOT_RUN','event_refs':[]}]}
    from .assertions import explain
    return EvaluatedResult.parse(explain(data,plan,partial))
