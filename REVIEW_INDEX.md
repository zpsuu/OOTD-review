# OOTD Review Index

## Current Active Version

v1.29.7 - Closet Bootstrapping & Item Reliability

Current branch:
`v1297-scenario-self-proof-cleanup`

Current status:
`PASS CANDIDATE confirmed`

## Current Review Focus

v1.29.7 Closet Bootstrapping & Item Reliability is PASS CANDIDATE confirmed.

Clean acceptance suite passes 46/46 cases and 44/44 checks.
Scenario preconditions are present and raw-proven.
Non-vacuous gates are included in clean_report.
G03/G04 current exception cases trigger real current-task exception conditions.
D-series gap cases include actual gap/missing-category triggers.
E-series repair cases include pre-repair reliability issues or no-reliable-alternative proof.
F-series swap reliability cases include visible swaps, hidden swaps, and no-swap reasons.
Insufficient closet cards use closet_insufficient_notice instead of partial Daily Outfit Cards.
Manual spot review passes.

## Confirmed Review Focus

- all clean cases include `scenario_preconditions`
- non-vacuous gates exist in `clean_report.json`
- G03 / G04 actually trigger current exception conditions
- D-series gap / missing category cases are no longer vacuous
- E-series repair / unreliable item cases have real pre-repair issues
- F-series swap reliability cases have real visible / hidden swap triggers
- insufficient closet card uses `closet_insufficient_notice`

## Latest Evidence Pack

`benchmark/benchmark_v129/results/v1297_release_candidate/`

## Key Files To Review

- `benchmark/benchmark_v129/results/v1297_release_candidate/REVIEW_MANIFEST.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/clean_report.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/mixed_strict_report.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/injected_defect_detection_summary.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_G03.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_G04.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_D02.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_D03.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_D04.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_D05.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_D07.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_E06.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_E07.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_F01.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_F03.json`
- `benchmark/benchmark_v129/results/v1297_release_candidate/per_case/clean/v1297_A05.json`
