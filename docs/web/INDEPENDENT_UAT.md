# Independent production acceptance checklist

Status: NOT RUN. Complete after the actual production executor/native receipt passes.
An agent-controlled browser on the VPS is not independent operator acceptance. Use a
separate desktop/mobile connection to https://qnx-resmgrcheck.gestionatech.de; keep
passwords, access codes, cookies, SSH and license material local. Record date, client,
active application revision, each passed/failed/blocked/not-run check and public run IDs.

- Verify trusted TLS, landing/explanation and genuine recorded before/after/job playback
  without a code. Confirm playback is clearly distinguished from live execution.
- Log in as a locally provisioned scoped administrator using username/password. MFA
  is deferred. No registration/email workflow exists. Confirm the intended administrator
  has explicit scope for the approved lab project; do not grant unrelated tenants.
  The disabled provisioning custodian and temporary acceptance account cannot log in.
- Issue a short-lived, bounded lab code. Redeem from the separate browser; confirm it
  shows only permitted projects/targets/evidence and no administrator controls.
- Select only the approved target/build and confirm a supported sensor/job scenario.
  Record canonical verdicts, native/web run IDs, source/build hashes and observed cleanup.
  Do not run extra native cases if the lab file-entry reserve is insufficient.
- Inspect the production qualification's intentional FAIL and corrected-source PASS;
  verify unchanged inputs/contracts, distinct fixture source/build identity, preserved
  partial incident history, canonical fixed comparison and verified evidence downloads.
- Revoke the code; confirm its active session and queued unauthorized work lose access.
  Supervised cleanup of an already-started run must retain its original identity.
- Confirm another project/organization and unapproved target/build cannot be accessed.
  Never test arbitrary external hosts or upload private credentials.
- Check mobile/no-JavaScript navigation, keyboard use, focus, labels and readable evidence.
  Automated zero-violation scans do not replace this manual accessibility check.
- Confirm customer machine endpoints and AI remain disabled and unavailable states are
  accurate. A connected runner or recorded demo does not prove external lifecycle support.
- Review the encrypted local backup/isolated restore receipt and executor recovery
  rehearsal. Full compatible application rollback remains a distinct unqualified gate.
  Off-server disaster recovery is deferred; keep that limitation in release notes.

Record safe results under docs/web/evidence after review. Do not mark P8–P10 complete
while production native, independent UAT, rollback or required security checks remain
blocked/unverified. Do not submit Devpost or change YouTube as part of this checklist.
