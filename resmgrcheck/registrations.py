"""Service registration is outside the execution and evaluation cores."""
from dataclasses import dataclass, field

CAPABILITIES = frozenset({'pending', 'unblock', 'state', 'release', 'health', 'timeout', 'signal', 'departure', 'error-probe', 'repeat', 'ordering', 'external-health'})
PROFILES={'sensor':'sensor-v1','job':'job-v1','mailbox':'mailbox-v1'}

@dataclass(frozen=True)
class Registration:
    operation: str
    fixture: str
    convention: str
    parameters: dict[str, tuple[int, int]]
    state_facts: frozenset[str]
    result_facts: frozenset[str]
    fixture_modes: frozenset[str] = frozenset({'corrected','ignore-unblock','retain-waiter','retain-third','duplicate-terminal'})
    ordering_state: dict[str, int] = field(default_factory=dict)
    next_deltas: tuple[tuple[str, int], ...] = (('value', 1),)

REGISTRY = {
    'sensor-v1': Registration('sample', 'sensor-v1-fixture', 'errno', {}, frozenset(), frozenset({'value'})),
    'job-v1': Registration('wait-result', 'job-v1-fixture', 'devctl', {'job_id': (1, 1)},
                           frozenset({'job_exists', 'job_ready'}), frozenset({'value', 'job_id'}), frozenset({'corrected','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'}), {'job_ready': 1}),
    'mailbox-v1': Registration('fetch-message','mailbox-v1-fixture','devctl',{'channel':(1,1)},
                            frozenset({'message_exists','message_ready','acknowledgements'}),frozenset({'value','channel'}),
                            ordering_state={'message_ready':1}),
}
