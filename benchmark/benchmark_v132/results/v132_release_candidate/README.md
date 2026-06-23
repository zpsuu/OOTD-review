# v1.32 Release Candidate Evidence Pack

## Scope

v1.32 verifies Inspiration Confirmation UX & Candidate Governance: confirmation cards, user confirmation actions, confirmed shadow candidates, conflict reports, compatible dedup clusters, and bridge shadow runs after confirmation.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: 55
- checks: 33
- verdict: pass

## Mixed Strict

- cases: 69
- injected defects: 14
- verdict: fail
- injected defect detection: pass

## Evidence Boundaries

- Confirmation cards only appear for sufficient ideal candidates.
- Confirmed inspiration candidates require user action and remain shadow-only.
- No production memory write occurs from inspiration confirmation.
- Raw external images are not included.
