# OOTD Review Index

## Current Active Version

v1.37 - End-to-End Inspiration Memory Runtime Loop

Current branch:
`v137-end-to-end-inspiration-memory-runtime-loop`

Current status:
`PASS CANDIDATE pending manual review`

## Current Review Focus

This iteration verifies the deterministic end-to-end inspiration memory runtime loop across:

- runtime handoff from intake, confirmation, promotion, consumption, feedback, post-feedback consumption, and multi-day replay
- RuntimeTrace, StageEvent, StateSnapshot, HandoffProof, and RuntimeInvariantReport artifacts
- no production memory write before user confirmation and promotion gate
- confirmed-aspect-only promotion and downstream consumption
- soft preference consumption without hard-filter misuse
- wrong-context, review-pending, blocked, and rollback future-packet safety
- independent validation, adversarial detection, sample consistency, report consistency, and v1.36 replay

## Latest Evidence Pack

`benchmark/benchmark_v137/results/v137_release_candidate/`

## Key Files To Review

- `benchmark/benchmark_v137/results/v137_release_candidate/REVIEW_MANIFEST.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/clean_report.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/independent_validation_report.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/adversarial_validation_report.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/report_consistency_report.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/sample_consistency_report.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/runtime_trace_summary.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/handoff_integrity_summary.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/state_transition_summary.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/per_case/clean/v137_A01_full_loop_low_risk_color_memory.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/per_case/clean/v137_E03_wrong_context_adds_exclusion_and_tests_excluded_context.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/per_case/adversarial/v137_ADV_K10_rollback_memory_still_consumed_later.json`
- `benchmark/benchmark_v137/results/v137_release_candidate/sample_artifacts/state_hash_stability.json`

## v1.37 - End-to-End Inspiration Memory Runtime Loop

Status: PASS CANDIDATE pending manual review

Current review focus:
- stage order and state snapshots are complete and hash-backed
- handoff ids match across each runtime boundary
- promotion requires confirmation and ProductionMemoryWriteGate allow
- consumption requires promoted memory and remains a soft bias
- feedback updates lifecycle state before future packet rebuild
- rollback, blocked, and review-pending states do not leak future claims
- v1.36 validation replay remains passing

## v1.36 - Promoted Inspiration Memory Feedback Lifecycle

Status: PASS CANDIDATE confirmed after targeted P1 fix review, independent validation, adversarial validation, sample consistency, report consistency, v1.35 replay, and unit tests

Current review focus:
- feedback must not directly mutate promoted memory
- lifecycle proposals must route through gate/write decision artifacts
- single feedback must not globalize contextual memory
- wrong-aspect feedback must not remove confirmed aspects
- do-not-use and rollback must block future consumption and claims
- v1.35 validation replay remains passing
