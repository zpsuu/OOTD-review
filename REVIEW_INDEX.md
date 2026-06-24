# OOTD Review Index

## Current Active Version

v1.36 - Promoted Inspiration Memory Feedback Lifecycle

Current branch:
`v136-promoted-inspiration-memory-feedback-lifecycle`

Current status:
`PASS CANDIDATE pending manual review`

## Current Review Focus

This iteration verifies promoted inspiration memory feedback lifecycle evidence across:

- feedback events traced to consumed promoted memory
- feedback interpretation and lifecycle proposals
- governed write decisions through existing gate semantics
- too-strong, wrong-aspect, wrong-context, do-not-use, forget, and undo behavior
- post-feedback consumption proof
- rollback and multi-day lifecycle stability
- independent validation, adversarial detection, sample consistency, and report consistency

## Latest Evidence Pack

`benchmark/benchmark_v136/results/v136_release_candidate/`

## Key Files To Review

- `benchmark/benchmark_v136/results/v136_release_candidate/REVIEW_MANIFEST.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/clean_report.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/independent_validation_report.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/adversarial_validation_report.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/report_consistency_report.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/sample_consistency_report.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/feedback_lifecycle_summary.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/rollback_feedback_summary.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/post_feedback_consumption_summary.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/per_case/clean/v136_C01_use_was_too_strong_reduces_weight.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/per_case/clean/v136_E04_future_mismatching_context_excludes_memory.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/per_case/adversarial/v136_ADV_J05_do_not_use_still_consumed_later.json`
- `benchmark/benchmark_v136/results/v136_release_candidate/sample_artifacts/forget_routes_to_rollback_gate.json`

## v1.36 - Promoted Inspiration Memory Feedback Lifecycle

Status: PASS CANDIDATE pending manual review

Current review focus:
- feedback must not directly mutate promoted memory
- lifecycle proposals must route through gate/write decision artifacts
- single feedback must not globalize contextual memory
- wrong-aspect feedback must not remove confirmed aspects
- do-not-use and rollback must block future consumption and claims
- v1.35 validation replay remains passing
