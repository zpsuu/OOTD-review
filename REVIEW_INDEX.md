# OOTD Review Index

## Current Active Version

v1.38 - Runtime Governance Operations

Current branch:
`v138-runtime-governance-operations`

Current status:
`PASS CANDIDATE pending manual review`

## Current Review Focus

This iteration verifies deterministic local runtime governance operations across:

- RuntimeGovernanceQueue and GovernanceQueueItem derivation from runtime triggers
- clarification requests and resolutions without hidden memory mutation
- human review payloads with raw evidence refs and constrained reviewer actions
- reviewer approval still routed through ProductionMemoryWriteGate
- temporary hold expiry/release and post-resolution TaskMemoryPacket rebuild
- rollback and blocked-memory audit absence proofs
- append-only GovernanceDecisionLedger hash-chain replay
- independent validation, adversarial detection, sample consistency, report consistency, and v1.37 replay

## Latest Evidence Pack

`benchmark/benchmark_v138/results/v138_release_candidate/`

## Key Files To Review

- `benchmark/benchmark_v138/results/v138_release_candidate/REVIEW_MANIFEST.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/clean_report.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/independent_validation_report.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/adversarial_validation_report.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/report_consistency_report.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/sample_consistency_report.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/governance_queue_summary.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/resolution_decision_summary.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/governance_ledger_summary.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/post_resolution_packet_summary.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/per_case/clean/v138_B02_clarification_answer_this_time_only_no_write.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/per_case/clean/v138_C02_review_approve_write_still_uses_write_gate.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/per_case/adversarial/v138_ADV_L16_ledger_hash_chain_broken.json`
- `benchmark/benchmark_v138/results/v138_release_candidate/sample_artifacts/ledger_hash_chain_valid.json`

## v1.38 - Runtime Governance Operations

Status: PASS CANDIDATE pending manual review

Current review focus:
- queue items derive from runtime governance triggers
- clarification and review no-write paths preserve memory state
- write resolutions route through ProductionMemoryWriteGate
- temporary holds remain current-turn scoped unless resolved or expired
- post-resolution packets match resolved lifecycle state
- rollback and blocked audit proofs prevent future consumption
- ledger hash-chain replay remains valid
- v1.37 validation replay remains passing

## v1.37 - End-to-End Inspiration Memory Runtime Loop

Status: PASS CANDIDATE confirmed after targeted HOLD fix review, independent validation, adversarial validation, sample consistency, report consistency, v1.36 replay, and unit tests

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
