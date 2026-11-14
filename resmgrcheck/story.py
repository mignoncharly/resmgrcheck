"""Plain-language views of saved assertions. No evaluation or inferred observations."""

STEPS = (
    ('Pending request', ('pending_precondition',),
     'A pending request was established before the trigger.',
     'The pending-request precondition was not established.'),
    ('Client operation', ('cancellation_not_completed', 'cancellation_completion', 'client_departure', 'ordering_result'),
     'The recorded client operation satisfied its declared obligation.',
     'The recorded client operation violated its declared obligation.'),
    ('Pending state', ('pending_state_cleanup',),
     'The observed pending state matched the contract after the trigger.',
     'The observed pending state did not match the contract after the trigger.'),
    ('Service-owned work', ('state_facts',),
     'The observed service-owned state matched the declared contract.',
     'The observed service-owned state violated the declared contract.'),
    ('Next client', ('fresh_client_health',),
     'A fresh client satisfied the declared health check.',
     'The fresh-client health check failed its declared obligation.'),
    ('Test cleanup', ('owned_process_cleanup', 'cleanup_unestablished'),
     'All owned test children were observed reaped.',
     'Cleanup did not satisfy its declared obligation.'),
)


def assertion_story(result):
    """Select saved facts for reading; retain exact verdicts and source references.

    Unsupported, incomplete and withheld assertions never receive success prose.
    A missing assertion remains unrecorded, including aggregate-only scenarios.
    """
    assertions = {item['id']: item for item in result.get('assertions', [])}
    rows = []
    for label, identifiers, success, failure in STEPS:
        assertion = next((assertions[key] for key in identifiers if key in assertions), None)
        verdict = assertion['verdict'] if assertion else 'UNRECORDED'
        if verdict == 'PASS':
            description = success
        elif verdict == 'FAIL':
            description = failure
        elif verdict == 'NOT_RUN':
            description = 'This check was withheld; no successful observation is inferred.'
        elif verdict == 'UNSUPPORTED':
            description = 'The required capability is unavailable for this check.'
        elif verdict == 'ERROR':
            description = 'An evidence, harness or infrastructure condition prevents this conclusion.'
        else:
            description = 'No separate assertion was recorded here. Inspect the detailed obligations and cycles.'
        rows.append({'label': label, 'verdict': verdict, 'description': description,
                     'assertion_id': assertion['id'] if assertion else None,
                     'event_refs': list(assertion.get('event_refs', [])) if assertion else []})
    return rows
