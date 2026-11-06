"""Service registration is outside the execution and evaluation cores."""
from dataclasses import dataclass

CAPABILITIES = frozenset({'pending', 'unblock', 'state', 'release', 'health', 'timeout', 'signal', 'departure', 'error-probe'})

@dataclass(frozen=True)
class Registration:
    operation: str
    fixture: str
    convention: str
    parameters: dict[str, tuple[int, int]]
    state_facts: frozenset[str]
    result_facts: frozenset[str]

REGISTRY = {
    'sensor-v1': Registration('sample', 'sensor-v1-fixture', 'errno', {}, frozenset(), frozenset({'value'})),
    'job-v1': Registration('wait-result', 'job-v1-fixture', 'devctl', {'job_id': (1, 1)},
                           frozenset({'job_exists', 'job_ready'}), frozenset({'value', 'job_id'})),
}
