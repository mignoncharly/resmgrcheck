# Dependencies and supported environment

| Component | Role | Distribution |
| --- | --- | --- |
| Original C11/Python/Make/HTML code | Product | Top-level MIT license |
| cJSON1.7.19, c859b25da02955fef659d658b8f324b5cde87be3 | Native bounded JSON | Vendored MIT source/license/revision hashes in third_party/cjson |
| Python3.10+ standard library | Host runtime/HTML/XML | External interpreter; no pip product dependencies |
| QNX SDP8.0/qcc gcc_ntox86_64 | Cross compiler and headers | Operator-installed/licensed; excluded from Git |
| QNX8.0.0 x86_64 OS/libc/libm | Target | Existing owned guest; proprietary image/binaries excluded |
| Git | Source revision/dirty-state provenance | External tool; use a Git checkout, not an unversioned archive |
| Make and OpenSSH ssh/scp with SFTP | Build and transfer | External locally installed tools, separately licensed |
| QEMU/KVM | Qualified virtual lab | External tools; disk/IFS artifacts excluded |
| Playwright1.64.1 / Chromium156.0.8078.4 | Optional browser qualification | Ignored local development environment; not product dependencies or redistributed binaries |
| GitHub checkout/setup-python actions | Optional host CI | External hosted CI; no native QNX claim |

Exact cJSON hashes/license are in [REVISION.json](../third_party/cjson/REVISION.json)
and [third-party notices](../THIRD_PARTY_NOTICES.md). Local SDK/package credentials,
license locks, SSH private keys and authenticated configuration are never source
release inputs. Runtime executables, target images, Python test environments and
browser binaries are generated/external and ignored.

The qualified host is Ubuntu Linux x86_64 with Python3.12.3, installed Make/OpenSSH
and the existing QNX8.0 environment. Hosted Python3.10/3.12 CI is supplied; local
results do not assert that a hosted workflow ran. The complete SDK update level
is unknown; do not label it8.0.5 from a compiler or baseline package alone.

The qualified target is the existing QNX8.0.0 x86_64/x86pc KVM guest, one CPU/1GiB,
UID0, loopback SSH and /data/resmgrcheck. Its IFS recipe hash and actual uname/build
are preserved in deployment/manifests. Phase9 will explicitly reuse this target;
no fresh-target creation claim is made. Clean source checkout/build is separate
from a fresh OS image. Required startup, licensing and local SSH setup are manual
prerequisites in README/cli.md. TCG and other architectures/releases are unqualified.

Follow-up E019 (2026-11-14) adds actual fresh-image/guest reproduction with newly
generated guest host keys: four native cases, source-fixed replay and observed
cleanup. It reuses the installed licensed SDK/client authentication on the same
development host. Independent developer usability/adoption remains unverified.
Use [fresh-lab.md](fresh-lab.md) rather than the historical bootstrap-copy steps.

Only the two registered fixture protocols and scoped external-health attachment
are supported. Combined custom wire operations, dynamic adapters and external
lifecycle/build identity without instrumentation are unavailable. A passing lab
run is not a hardware timing, security/safety-certification, production-readiness,
exhaustive-concurrency or memory-leak-absence claim. See known limitations.
