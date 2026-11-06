# Pinned cJSON review

Upstream: https://github.com/DaveGamble/cJSON/releases/tag/v1.7.19

Pinned tag/revision and SHA256 of the three unmodified upstream files are in
REVISION.json. LICENSE is preserved verbatim. Only cJSON.c is compiled; cJSON_Utils,
upstream build systems and tests are not included. Builds do not access the network.

Reviewed on 2026-11-06: official release notes, README parsing APIs/caveats, and the
ParseWithLengthOpts/object lookup/printing paths relevant to this integration.
This is an integration review, not a complete security audit of upstream.

Our use:

- QNX qcc, C11, -Wall -Wextra -Werror; CJSON_NESTING_LIMIT=12; libm required by
  the installed QNX implementation of numeric classification/printing.
- ParseWithLengthOpts with full consumption and per-call end pointer, bounded
  1 MiB plan input; case-sensitive object lookup; explicit duplicate traversal.
- Native commands use canonical ASCII string values without escapes; compact
  serialization comparison rejects cJSON's permissive numeric forms and NUL
  ambiguity. Context-specific validators reject unknown fields, non-integral
  numbers, wrong types, booleans as integers, unsafe paths and unknown ABI/versions.
- Producers serialize through cJSON into bounded frames. The supervisor rejects
  duplicate/noncanonical frames and wrong identity/sequence; the host validates
  the exact event-specific field contracts.
- No cJSON global allocation hooks, locale changes, or global error pointer API.
  Each producer is single-threaded. Required allocation/write failures are
  evidence errors, not silently dropped events.

The native executable does not provide a general-purpose JSON parser to users.
The host validates profile/snapshot hashes and narrower service contracts before
expansion. Hash declarations are not a cryptographic attestation by the guest.
Actual deployment is checked by SFTP readback in the retained qualification.
