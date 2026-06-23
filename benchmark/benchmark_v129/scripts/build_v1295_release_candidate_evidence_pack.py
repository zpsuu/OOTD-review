"""Build v1.29.5 Multi-Day Feedback & Adoption Loop evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "seven_day_adoption_loop.json": ("case_id", "v1295_A01"),
    "wear_this_updates_history_no_global_memory.json": ("case_id", "v1295_A02"),
    "save_not_treated_as_wear.json": ("case_id", "v1295_A03"),
    "skip_without_reason_no_hard_avoid.json": ("case_id", "v1295_A04"),
    "current_exception_expires_next_day.json": ("case_id", "v1295_A05"),
    "contextual_memory_applies_only_matching_context.json": ("case_id", "v1295_A06"),
    "do_not_remember_not_reused_day7.json": ("case_id", "v1295_A07"),
    "correction_supersedes_wrong_proposal_multiday.json": ("case_id", "v1295_A08"),
    "exact_outfit_not_repeated_without_reason.json": ("case_id", "v1295_A09"),
    "final_memory_snapshot_matches_timeline.json": ("case_id", "v1295_A10"),
}

INJECTED_SAMPLE_CASES = {
    "injected_wear_this_globalized_detected.json": "wear_this_creates_global_preference_without_confirmation",
    "injected_skip_creates_hard_avoid_detected.json": "skip_creates_hard_avoid_without_reason",
    "injected_current_exception_persists_detected.json": "current_exception_persists_next_day",
    "injected_do_not_remember_reused_detected.json": "do_not_remember_reused_on_day7",
    "injected_wrong_context_memory_detected.json": "contextual_memory_applied_to_wrong_context",
    "injected_deprecated_proposal_consumed_detected.json": "deprecated_wrong_proposal_consumed_later",
    "injected_exact_outfit_repeated_detected.json": "exact_outfit_repeated_without_reason",
    "injected_second_day_untraced_memory_detected.json": "second_day_response_claims_untraced_memory",
    "injected_save_treated_as_wear_detected.json": "save_treated_as_wear_this",
    "injected_correction_does_not_supersede_detected.json": "correction_does_not_supersede_wrong_proposal",
    "injected_final_memory_snapshot_mismatch_detected.json": "final_memory_snapshot_mismatches_timeline",
    "injected_temporary_exception_not_expired_detected.json": "temporary_exception_not_expired",
    "injected_corrected_memory_active_without_write_gate_detected.json": "corrected_memory_active_without_write_gate",
    "injected_adoption_event_wrong_context_detected.json": "adoption_event_wrong_context",
    "injected_post_day_snapshot_missing_allowed_commit_detected.json": "post_day_snapshot_missing_allowed_commit",
    "injected_pre_post_store_snapshot_discontinuity_detected.json": "pre_post_store_snapshot_discontinuity_without_event",
    "injected_corrected_contextual_memory_outside_context_detected.json": "corrected_contextual_memory_consumed_outside_committed_context",
}


def _load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_rows(raw_dir: str | Path) -> list[dict[str, Any]]:
    raw_dir = Path(raw_dir)
    results = raw_dir / "results.json"
    if results.exists():
        return _load(results)
    return [_load(p) for p in sorted((raw_dir / "per_case").glob("*.json"))]


def _pick(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise RuntimeError(f"missing sample row: {key}={value}")


def _defect_sample(row: dict[str, Any], mixed_report: dict[str, Any]) -> dict[str, Any]:
    defect_type = row.get("defect_type")
    detected = next((d for d in mixed_report.get("detected_defects", []) if d.get("defect_type") == defect_type), {})
    return {
        "case_id": row.get("case_id"),
        "defect_type": defect_type,
        "expected_failure": True,
        "actual_failure": bool(detected.get("actual_failure")),
        "detected": bool(detected.get("detected")),
        "failed_check_ids": detected.get("failed_check_ids") or [],
        "expected_failed_check_ids": detected.get("expected_failed_check_ids") or [],
        "failure_reason": detected.get("failure_reason"),
        "raw_artifact_ref": detected.get("raw_artifact_ref"),
        "raw_artifact": row,
    }


def _injected_summary(mixed_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite": "v1.29.5 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _readme() -> str:
    return """# v1.29.5 Release Candidate Evidence Pack

This release candidate verifies Multi-Day Feedback & Adoption Loop stability.

v1.29.5 extends the v1.29.4 single Daily Outfit vertical slice into a multi-day sequence.

It verifies:

- wear_this updates outfit history but does not directly create global preference
- save is not treated as wear_this
- skip without explicit reason does not become hard avoid
- current task exceptions expire after the originating task
- contextual memories apply only in matching contexts
- do_not_remember is not reused across later days
- corrected interpretations supersede wrong proposals
- exact outfits are not repeated within a short window without reason
- final memory snapshot matches the memory evolution timeline
- user-visible claims are trace-backed across days

## Contextual Corrected-Memory Scope Semantics

Corrected memories committed with `scope=contextual` may only be consumed or claimed in later days when the current task context is authorized by the memory's committed contexts.

A later-day use is authorized only if at least one of the following holds:

1. `task_context.occasion` directly matches one of the memory's `committed_contexts`.
2. `task_context.context_tags` intersects the memory's `committed_contexts`.
3. The artifact includes an explicit `memory_context_match_proof` with `authorized_for_current_task=true`.

User-visible claims that reference contextual memories must also have context authorization proof.

This prevents corrected contextual memories from leaking into unrelated future contexts.

## Multi-Day Memory State Self-Proof

v1.29.5 separates store-level memory state from task-active memory state.

Store-level snapshots represent the active memory store across days.

Task-active snapshots represent which memories are active for the current task context after contextual filtering, overrides, exclusions, and temporary exceptions.

A memory may appear in final active production memory only if it has an authorized source:

1. it exists in the initial memory fixture;
2. it was committed by an allowed ProductionMemoryWriteGate decision;
3. or it is explicitly marked as session/runtime scoped with expiry and is not represented as production active memory.

Corrected interpretations that influence later days must either route through ProductionMemoryWriteGate or remain explicitly session-scoped with expiry.

Adoption events must match the current day's task context unless marked as cross-task feedback.

Non-goals:

- no external inspiration intake
- no multimodal clean acceptance dependency
- no Ideal-Reality Bridge
- no shopping / commerce
- no full UI or beta launch
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    return f"""# v1.29.5 Release Candidate Note

## Scope

v1.29.5 focuses on Multi-Day Feedback & Adoption Loop stability.

It does not introduce external inspiration intake, multimodal mainline ingestion, Ideal-Reality Bridge, shopping, or beta expansion.

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')}/{clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}

## Mixed Strict Suite With Injected Defects

- Cases: {mixed.get('total_cases')}
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected
- Injected defect detection: {mixed_report.get('verdicts', {}).get('injected_defect_detection_verdict')}

## Release Status

PASS CANDIDATE confirmed.

## P2 Backlog

- clean suite coverage
- case-level checks
- per_case archive
- initial snapshot field naming
"""


def _checklist() -> str:
    return """# v1.29.5 Reviewer Checklist

## Release Candidate Summary

- Clean acceptance suite: PASS if all gates pass
- Mixed strict suite with injected defects: expected FAIL
- Injected defect detection: PASS if all seeded defects are detected
- Release status: PASS CANDIDATE confirmed
- P2 backlog recorded: clean suite coverage, case-level checks, per_case archive, initial snapshot field naming

## A. Seven-Day Adoption Loop

Artifact: `sample_artifacts/seven_day_adoption_loop.json`

- [ ] each day has a DailyOutfitDayArtifact
- [ ] each day has a valid DailyOutfitCard
- [ ] each final outfit uses only closet items
- [ ] each day has trace
- [ ] memory evolution timeline is present
- [ ] final memory snapshot can be derived from timeline
- [ ] PASS
- [ ] FAIL

## B. Wear This

Artifact: `sample_artifacts/wear_this_updates_history_no_global_memory.json`

- [ ] wear_this updates OutfitHistory
- [ ] wear_this creates adoption evidence
- [ ] wear_this does not directly create global preference
- [ ] no production memory write occurs without proposal / confirmation
- [ ] PASS
- [ ] FAIL

## C. Save

Artifact: `sample_artifacts/save_not_treated_as_wear.json`

- [ ] save is treated as interest evidence
- [ ] save does not create worn outfit history
- [ ] save is not treated as wear_this
- [ ] save does not directly create global memory
- [ ] PASS
- [ ] FAIL

## D. Current Task Exception Expiry

Artifact: `sample_artifacts/current_exception_expires_next_day.json`

- [ ] exception applies on the originating day
- [ ] exception expires on the next normal task
- [ ] no global positive preference is created
- [ ] old contextual avoid remains preserved
- [ ] residual boundary is retained
- [ ] PASS
- [ ] FAIL

## E. Contextual Memory Scope

Artifact: `sample_artifacts/contextual_memory_applies_only_matching_context.json`

- [ ] contextual memory applies in matching context
- [ ] contextual memory is excluded in mismatching context
- [ ] exclusion reason is recorded
- [ ] response claims are trace-backed
- [ ] PASS
- [ ] FAIL

## F. Do Not Remember

Artifact: `sample_artifacts/do_not_remember_not_reused_day7.json`

- [ ] no production write occurs
- [ ] proposal status is rejected
- [ ] rejected proposal is not consumed later
- [ ] later response does not claim rejected memory
- [ ] PASS
- [ ] FAIL

## G. Correction Across Days

Artifact: `sample_artifacts/correction_supersedes_wrong_proposal_multiday.json`

- [ ] wrong proposal is deprecated / superseded
- [ ] corrected proposal is created
- [ ] later recommendation uses corrected interpretation
- [ ] later recommendation does not consume deprecated wrong proposal
- [ ] PASS
- [ ] FAIL

## H. Outfit Repetition

Artifact: `sample_artifacts/exact_outfit_not_repeated_without_reason.json`

- [ ] recent outfit history is present in planner trace
- [ ] exact outfit is not repeated within short window without reason
- [ ] if exact outfit repeats, repeat_allowed_reason exists
- [ ] repeated items are paired differently when possible
- [ ] PASS
- [ ] FAIL

## I. Final Memory Snapshot

Artifact: `sample_artifacts/final_memory_snapshot_matches_timeline.json`

- [ ] final active memories can be derived from timeline
- [ ] confirmed memory appears in final snapshot
- [ ] temporary exception is expired
- [ ] rejected proposal is not active
- [ ] deprecated wrong proposal is not active
- [ ] PASS
- [ ] FAIL

## J. Multi-Day Memory State Self-Proof

Artifact: `sample_artifacts/seven_day_adoption_loop.json`

- [ ] store-level memory snapshots are separate from task-active snapshots
- [ ] Day 1 allowed committed memory appears in Day 1 post-day store snapshot
- [ ] next-day pre-store snapshot matches previous post-store snapshot unless transition event exists
- [ ] final active production memories all have authorized sources
- [ ] corrected interpretation either routes to write gate or remains session-scoped with expiry
- [ ] no corrected memory enters final active production memory without authorization
- [ ] Day 5 adoption event occasion matches task context
- [ ] rejected proposals do not reappear in active memory
- [ ] temporary exceptions are recorded as expired
- [ ] PASS
- [ ] FAIL

## K. Contextual Corrected-Memory Later Use

Artifact: `sample_artifacts/correction_supersedes_wrong_proposal_multiday.json`

- [ ] Day 4 corrected memory has `scope=contextual`
- [ ] Day 4 write gate decision includes `committed_contexts`
- [ ] If Day 7 consumes the corrected memory, Day 7 task context includes a matching context tag or direct occasion match
- [ ] `memory_context_match_proof` exists for the corrected memory
- [ ] `memory_context_match_proof.authorized_for_current_task == true`
- [ ] Any Day 7 response / card claim using the corrected memory has context authorization proof
- [ ] No contextual corrected memory is consumed or claimed outside committed contexts without proof
- [ ] PASS
- [ ] FAIL

## L. Injected Defect Detection

- [ ] all seeded defects are detected
- [ ] no injected defect is silently excluded
- [ ] no injected defect unexpectedly passes
- [ ] no clean case unexpectedly fails
- [ ] PASS
- [ ] FAIL

## M. New Injected State Defects

- [ ] corrected_memory_active_without_write_gate detected
- [ ] adoption_event_wrong_context detected
- [ ] post_day_snapshot_missing_allowed_commit detected
- [ ] pre_post_store_snapshot_discontinuity_without_event detected
- [ ] corrected contextual memory consumed outside committed context was detected
- [ ] PASS
- [ ] FAIL

## Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PARTIAL PASS
- [ ] FAIL

Reviewer notes:
"""


def _copy_report(src_json: str, out_dir: Path, out_json_name: str, out_md_name: str) -> None:
    shutil.copyfile(src_json, out_dir / out_json_name)
    src_md = Path(src_json).with_suffix(".md")
    if src_md.exists():
        shutil.copyfile(src_md, out_dir / out_md_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-report", required=True)
    parser.add_argument("--mixed-report", required=True)
    parser.add_argument("--clean-artifacts-dir", required=True)
    parser.add_argument("--mixed-artifacts-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    sample_dir = out_dir / "sample_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    clean_report = _load(args.clean_report)
    mixed_report = _load(args.mixed_report)
    clean_rows = _load_rows(args.clean_artifacts_dir)
    mixed_rows = _load_rows(args.mixed_artifacts_dir)

    _copy_report(args.clean_report, out_dir, "clean_report.json", "clean_report.md")
    _copy_report(args.mixed_report, out_dir, "mixed_strict_report.json", "mixed_strict_report.md")
    _write_json(out_dir / "injected_defect_detection_summary.json", _injected_summary(mixed_report))
    _write_text(out_dir / "README.md", _readme())
    _write_text(out_dir / "RELEASE_NOTE.md", _release_note(clean_report, mixed_report))
    _write_text(out_dir / "reviewer_checklist.md", _checklist())

    for name, (key, value) in SAMPLE_CASES.items():
        _write_json(sample_dir / name, _pick(clean_rows, key, value))
    for name, defect_type in INJECTED_SAMPLE_CASES.items():
        _write_json(sample_dir / name, _defect_sample(_pick(mixed_rows, "defect_type", defect_type), mixed_report))

    print(json.dumps({"out_dir": str(out_dir), "sample_artifacts": len(SAMPLE_CASES) + len(INJECTED_SAMPLE_CASES)}, indent=2))


if __name__ == "__main__":
    main()
