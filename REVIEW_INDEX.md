# OOTD Review Index

## Current Active Version

v1.35 - Runtime Path Independent Validation & Evidence Hardening

Current branch:
`v135-runtime-path-independent-validation`

Current status:
`PASS CANDIDATE pending manual review`

## Current Review Focus

This iteration verifies runtime-path independent validation evidence across:

- independent raw-artifact validation as a release requirement
- builder / validator separation proof
- report-vs-validator consistency checks
- sample_artifacts vs per_case consistency checks
- full raw adversarial mutation detection
- v1.34 replay of independent and adversarial validation
- one-command validation runner

## Latest Evidence Pack

`benchmark/benchmark_v135/results/v135_release_candidate/`

## Key Files To Review

- `benchmark/benchmark_v135/results/v135_release_candidate/REVIEW_MANIFEST.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/clean_report.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/independent_validation_report.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/adversarial_validation_report.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/report_consistency_report.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/sample_consistency_report.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/injected_defect_detection_summary.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/per_case/clean/v135_A01_clean_report_matches_independent_validation.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/per_case/adversarial/v135_ADV_I01_clean_report_pass_but_independent_validation_fail.json`
- `benchmark/benchmark_v135/results/v135_release_candidate/sample_artifacts/sample_artifact_matches_per_case.json`

## v1.35 - Runtime Path Independent Validation & Evidence Hardening

Status: PASS CANDIDATE pending manual review

Current review focus:
- independent validator recomputes gates from raw artifacts
- report-only pass cannot override raw validation failure
- sample artifacts are canonical full-copy matches of per_case artifacts
- adversarial mutation suite is complete and detected
- v1.34 replay remains reproducible
