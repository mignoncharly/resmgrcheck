#!/bin/sh
# Run inside the dedicated QNX lab with the three executables in this directory.
# Fixed saved reproduction inputs: kernel timeout 500 ms; completion allowance 2000 ms.
set -u
for mode in ignore-unblock corrected; do
    ./phase2-supervisor "$mode" 500 2000 > "phase2-$mode.log"
    result=$?
    if [ "$mode" = ignore-unblock ]; then
        [ "$result" -eq 1 ] || exit 2
        grep -q 'event=verdict result=FAIL reason=cancellation_deadline' "phase2-$mode.log" || exit 2
    else
        [ "$result" -eq 0 ] || exit 2
        grep -q 'event=verdict result=PASS reason=cancellation_completed_and_healthy' "phase2-$mode.log" || exit 2
    fi
    grep -q 'event=cleanup all_reaped=1 evidence_error=0' "phase2-$mode.log" || exit 2
    grep -q 'event=final complete=1' "phase2-$mode.log" || exit 2
    echo "$mode: expected verdict and cleanup observed (supervisor exit $result)"
done
