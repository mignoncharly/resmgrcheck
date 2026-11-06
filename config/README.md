# Target configuration

`target.example.json` documents the intended nonsecret connection settings. The host application and configuration parser do not exist yet; no current command consumes this file.

Resolve the SSH alias through local OpenSSH configuration after validating the guest transport. Keep keys, passwords, authenticated connection details, and the real local target configuration outside Git. `target.local.json` is ignored.

The final executable configuration contract must be implemented and documented under the corresponding phase of the implementation plan.

