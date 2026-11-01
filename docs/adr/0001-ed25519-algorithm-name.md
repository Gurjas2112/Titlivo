# ADR-0001: Passport JWS header uses `alg: "Ed25519"`, not `"EdDSA"`

- Status: accepted (1 Nov 2026)
- Spec reference: §6.10, build rule 12

## Context

The specification names the passport algorithm `EdDSA` (Ed25519 keys). RFC 9864 deprecated the polymorphic `EdDSA` identifier in favour of fully specified names. `joserfc` 1.7 now emits a security warning for `EdDSA`, while both `joserfc` (server) and `jose` 6 (browser) support `Ed25519`.

## Decision

Sign and verify passports and status lists with `alg: "Ed25519"`. The keys (OKP, crv Ed25519), the signature bytes and the `vc+jwt` media type are unchanged.

## Consequences

- Verifiers that only accept `EdDSA` must add `Ed25519`; both reference verifiers in this repo do.
- Shared behaviour is covered by the tests in `api/tests/test_passport.py` and by verifying Python-signed passports in the browser verifier.
