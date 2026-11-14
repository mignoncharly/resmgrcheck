#!/usr/bin/env python3
"""Scoped QFuse integration evaluator, independent of the frozen ABI1 lifecycle suite."""
import json

ORDER = ['ready', 'callback_held', 'cancel_return', 'held_status', 'independent_health', 'drained_status', 'cleanup']


def evaluate(raw, native_exit):
    try:
        rows = [json.loads(line) for line in raw.splitlines()]
        if native_exit != 0 or [r['event'] for r in rows] != ORDER:
            raise ValueError('native execution incomplete')
        ready, _, returned, held, health, drained, cleanup = rows
        if ready['mode'] not in {'timeout', 'signal'} or type(ready['service_pid']) is not int or ready['service_pid'] <= 0:
            raise ValueError('invalid native identity')
        if returned['expected_error'] != (260 if ready['mode'] == 'timeout' else 4):
            raise ValueError('unexpected QNX 8 x86_64 error identity')
        for row in (held, drained):
            if any(type(row[k]) is not int or row[k] < 0 for k in ('active_operations', 'cancelled_waits', 'cleanup_pending')):
                raise ValueError('invalid counters')
        if cleanup['children_reaped'] is not True or cleanup['mount_absent'] is not True:
            raise ValueError('cleanup uncertain')
        checks = {
            'cancel_return': returned['raw_return'] == -1 and returned['api_error'] == returned['expected_error'],
            'callback_retained_while_wait_cancelled': held['active_operations'] >= 1 and held['cancelled_waits'] >= 1,
            'independent_path_health': health['raw_return'] == 1 and health['value'] == ord('Q'),
            'callback_drained_after_release': drained['active_operations'] == 0 and drained['cleanup_pending'] == 0,
            'cumulative_cancellations_stable_after_release': drained['cancelled_waits'] == held['cancelled_waits'],
        }
        return {'scope': 'qfuse-integration-probe-v1', 'verdict': 'PASS' if all(checks.values()) else 'FAIL',
                'assertions': {k: 'PASS' if v else 'FAIL' for k, v in checks.items()},
                'cleanup_verified': True, 'abi1_adapter': False}
    except (ValueError, KeyError, TypeError):
        return {'scope': 'qfuse-integration-probe-v1', 'verdict': 'ERROR',
                'reason': 'incomplete_or_invalid_native_observation', 'cleanup_verified': False, 'abi1_adapter': False}
