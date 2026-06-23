# Review Principles

## Raw-first

Reports are not trusted unless supported by raw per-case artifacts.

If summary says PASS but raw artifacts do not self-prove the condition, the review result is HOLD.

## No vacuous pass

A benchmark case must actually trigger the scenario it claims to test.

Each clean case should include `scenario_preconditions` with explicit proof refs.

## No report-only fix

Do not fix review failures by editing only README, RELEASE_NOTE, or aggregate summaries.

If a reviewer requested a new gate, the gate must appear in `clean_report.json` and `mixed_strict_report.json`.

If a reviewer requested raw proof, the proof must appear in per-case raw artifacts.

## Trace-backed user-visible claims

Any user-visible memory or outfit claim must be trace-backed.

## Scope hygiene

Current task exceptions must not globalize.
Misuse corrections must not become positive preferences.
Do-not-remember must not create production writes or later claims.

## Evidence pack completeness

Each release candidate should include:

- REVIEW_MANIFEST.json
- clean_report.json / clean_report.md
- mixed_strict_report.json / mixed_strict_report.md
- injected_defect_detection_summary.json
- reviewer_checklist.md
- sample_artifacts/
- per_case/
