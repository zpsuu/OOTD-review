# v1.31 Release Candidate Evidence Pack

## Scope

v1.31 verifies the Inspiration Intake Shadow Pipeline: external inspiration intake, visual/text signal candidates, user intent resolution, ideal direction candidates, v1.30-style bridge shadow runs, shadow-only memory proposals, and privacy-safe external evidence handling.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: 48
- checks: 46
- verdict: pass

## Mixed Strict

- cases: 69
- injected defects: 21
- verdict: fail
- injected defect detection: pass

## Evidence Boundaries

- Raw external screenshots and images are not included.
- URL cases use redacted placeholders and metadata-only fixtures.
- External inspiration never writes production memory in v1.31.
