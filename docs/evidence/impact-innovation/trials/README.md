# Preserved trials

`final-cycle-error` is the original sealed recording/evaluation from clean source
21bf7f4, run `r-20261114140707-81036e2cd168-repeat`. Its producer bytes establish
two passing cycles followed by retained pending state and successful owned-process
cleanup on the third and final requested cycle. The original evaluator reports
ERROR because its repeat-coverage logic expected later withheld cycles to mark
coverage NOT_RUN. The reducer correctly stopped at that ERROR.

The subsequent classification correction retains the final cycle's established
FAIL and marks coverage NOT_RUN. Original files here remain unchanged. Inspect
this **historical** sealed bundle with source21bf7f4; the regression evaluates
its same raw observations explicitly under the corrected rules without rewriting
the old result or manifest. A missing final state observation still yields ERROR.
