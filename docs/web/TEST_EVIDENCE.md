# Production web test evidence

## W000 — P0 baseline and read-only inventory

2026-11-07. Specification commit3d9048a, published baselineca4f74e. Working tree
was clean when checked out. Remote fetch was explicitly scoped to the requested
branch; the original single-branch refspec did not initially contain it.
Original engine fingerprint remains02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b.

[Sanitized inventory](evidence/p0/inventory.json) records the actual host findings.
47 running service units and12 enabled Nginx sites were inventoried without dumping
protected configuration. Existing PostgreSQL clusters were preserved. The account
is nonroot; noninteractive sudo requires a password. Existing PostgreSQL role is
not superuser and cannot create databases. Requested DNS did not resolve. No
matching Nginx vhost exists. No production changes were made.

The installed SDP was sourced normally; actual qcc discovery reported GCC12.2.0
gcc_ntox86_64. Read-only SSH to the existing guest returned QNX8.0.0/x86pc and UID0.
Guest data space:415 free entries,2992 free4096-byte blocks. This is capability/
storage inventory, not a new lifecycle execution claim. [All107 baseline host tests](evidence/p0/engine-host-tests.txt) passed in13.872
seconds; no unchanged native matrix was repeated.

Supported dependency candidates were checked against official Django/allauth docs
and PyPI, with [version metadata](evidence/p0/dependency-selection.json). Actual
installation/lock, audit and compatibility tests are P1 work. Django5.2 LTS is
listed supported through April2028 by https://www.djangoproject.com/download/.
MFA integration follows https://docs.allauth.org/en/latest/mfa/introduction.html.

P0 passes inventory/threat-model readiness with explicit downstream production
blockers. P1–P10 are not passed by this record. No AI provider or public HTTPS result
is claimed. See SECURITY, DEPLOYMENT and OPERATIONS for constraints and rollback.
