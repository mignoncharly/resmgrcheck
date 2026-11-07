# Deployment record

Requested URL: `https://qnx-resmgrcheck.gestionatech.de`. Not deployed.
Read-only P0 inventory found 12 enabled Nginx sites, no matching vhost, many live
applications and PostgreSQL instances, Python 3.12.3, Nginx 1.24.0 and available
loopback port 8431. At P0 the requested DNS name did not resolve; a later read-only check found it resolves, without an application vhost or verified HTTPS. No existing site,
firewall, database, guest or host service was modified.

Staging uses a separate private Unix-socket PostgreSQL cluster and virtualenv
under ignored `.local/web`, with the app bound only to loopback. This isolates
test data from all existing databases without requiring root or borrowing secrets.
It is not a production OS isolation or public HTTPS acceptance result.

Production requires the dedicated accounts/directories/database, constrained
executor credential access, root-owned systemd units, reviewed vhost, valid TLS,
the revised administrator/access-code gate, backup/restore and rollback proofs. Provisioning and
external DNS/TLS changes must wait for the contract's applicable readiness gates.
[PRIVATE_INSTALL.md](PRIVATE_INSTALL.md) contains the concrete private root
preparation command, dedicated resources, tests and remaining gates. The script
starts no public listener and never touches Nginx/DNS/TLS. It is prepared, not
root-executed or production-qualified. Never send passwords/private configuration
or keys in chat.

Rollback baseline is the preserved published branch/revision `ca4f74e`. Web work
is isolated on `feature/production-web-ai`; removal/stop actions may name only the
new dedicated ResMgrCheck resources. Existing engine binaries/evidence and other
applications must survive a rollback.

The former SMTP prerequisite is superseded by ACCESS_MODEL.md. Production uses
protected local administrator provisioning/recovery, scoped access-code sessions,
mandatory administrator MFA and no public registration/email authentication.
