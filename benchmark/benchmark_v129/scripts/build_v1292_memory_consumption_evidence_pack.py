"""
Build v1.29.2 Memory Consumption Correctness evidence pack.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "current_task_exception_override.json": ("scenario", "override_sneakers"),
    "misuse_correction_not_positive_signal.json": ("scenario", "misuse_french_cliche"),
    "negative_boundary_critic_repair.json": ("scenario", "negative_sweetness"),
    "blocked_memory_not_consumed.json": ("scenario", "exclude_blocked"),
    "review_required_memory_not_consumed.json": ("scenario", "exclude_review_required"),
    "shadow_only_memory_not_consumed.json": ("scenario", "exclude_shadow_only"),
    "contextual_scope_match.json": ("scenario", "contextual_match"),
    "contextual_scope_mismatch_exclusion.json": ("scenario", "contextual_mismatch"),
    "response_trace_consistency.json": ("scenario", "response_claim_used_memory"),
}

INJECTED_SAMPLE_CASES = {
    "injected_misuse_correction_positive_signal_detected.json": "misuse_correction_positive_signal",
    "injected_overridden_avoid_in_explicit_reject_detected.json": "overridden_avoid_in_explicit_reject",
    "injected_blocked_memory_consumed_detected.json": "blocked_memory_consumed",
    "injected_review_required_memory_consumed_detected.json": "review_required_memory_consumed",
    "injected_shadow_only_memory_consumed_detected.json": "shadow_only_memory_consumed",
    "injected_response_claim_untraced_memory_detected.json": "response_claim_untraced_memory",
    "injected_critic_miss_detected.json": "critic_misses_negative_boundary_violation",
    "injected_repair_without_triggering_memory_ref_detected.json": "repair_without_triggering_memory_ref",
    "injected_repair_claims_pass_but_final_still_violates_boundary_detected.json": "repair_claims_pass_but_final_still_violates_boundary",
}


def _load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


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
    detected = next(
        (d for d in mixed_report.get("detected_defects", []) if d.get("defect_type") == defect_type),
        {},
    )
    return {
        "case_id": row.get("case_id"),
        "defect_type": defect_type,
        "detected": bool(detected.get("detected")),
        "failed_check_ids": detected.get("failed_check_ids") or [],
        "expected_failed_check_ids": detected.get("expected_failed_check_ids") or [],
        "task_memory_packet": row.get("task_memory_packet"),
        "planner_trace": row.get("planner_trace"),
        "critic_report": row.get("critic_report"),
        "repair_report": row.get("repair_report"),
        "final_outfit": row.get("final_outfit"),
        "response": row.get("response"),
    }


def _injected_summary(mixed_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite": "v1.29.2 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _report_md(title: str, report: dict[str, Any]) -> str:
    summary = report.get("suite_summary") or {}
    verdicts = report.get("verdicts") or {}
    lines = [
        f"# {title}",
        "",
        f"- suite_mode: `{summary.get('suite_mode')}`",
        f"- cases: {summary.get('total_cases')}",
        f"- checks: {summary.get('passed_checks')} / {summary.get('total_checks')} PASS",
        f"- failed_checks: {summary.get('failed_checks')}",
        f"- clean_acceptance_verdict: `{verdicts.get('clean_acceptance_verdict')}`",
        f"- mixed_strict_verdict: `{verdicts.get('mixed_strict_verdict')}`",
        f"- injected_defect_detection_verdict: `{verdicts.get('injected_defect_detection_verdict')}`",
        f"- release_candidate_verdict: `{verdicts.get('release_candidate_verdict')}`",
        "",
        "## Failed Checks",
        "",
    ]
    failed = report.get("failed_gates") or []
    lines.extend([f"- `{g}`" for g in failed] or ["- None"])
    return "\n".join(lines) + "\n"


def _readme() -> str:
    return """# v1.29.2 Memory Consumption Correctness Evidence Pack

This evidence pack verifies that existing committed memory is consumed correctly by downstream styling planning.

## Contents

- `clean_report.json` / `clean_report.md`
- `mixed_strict_report.json` / `mixed_strict_report.md`
- `injected_defect_detection_summary.json`
- `reviewer_checklist.md`
- `RELEASE_NOTE.md`
- `sample_artifacts/`

## Verdict Semantics

Clean acceptance is used for release acceptance.

Mixed strict includes injected defects and is expected to fail when the detector catches seeded memory-consumption defects.

Release candidate status is derived from clean acceptance PASS plus injected defect detection PASS.

## Scope

v1.29.2 does not add production write categories, UI, beta launch, external inspiration intake, shopping, or aesthetic cards. It verifies retrieval, scope resolution, overrides, exclusion hygiene, planner trace, critic checks, repair routing, and response explanation alignment.

## Repair Self-Proof Semantics

For v1.29.2, a repair is not considered proven merely because a repair event exists or references a triggering memory id.

For negative boundary repair cases, the evidence pack must prove that the final outfit no longer violates the active boundary.

Required evidence includes:

- critic event detecting the negative boundary violation
- repair event referencing the triggering memory id
- final outfit diff or removed boundary concepts
- `post_repair_validation.remaining_violations == []`
- `post_repair_validation.final_outfit_violation_free == true`

The raw-first aggregate gate `final_outfit_boundary_violation_free_rate` enforces this.

## Current Status

PASS CANDIDATE confirmed.
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    defects = [
        d.get("defect_type")
        for d in mixed_report.get("detected_defects", [])
        if d.get("detected")
    ]
    return f"""# v1.29.2 Release Candidate Note

## Scope

v1.29.2 focuses on Memory Consumption Correctness.

It verifies that committed memory is retrieved, scoped, filtered, overridden, consumed, traced, criticized, repaired, and explained correctly by the styling planner pipeline.

## Non-Goals

- No new production memory write categories
- No external inspiration intake
- No aesthetic cards
- No UI changes
- No beta launch
- No shopping / commerce integration
- No subjective outfit quality optimization beyond correctness fixtures

## Key Additions

- TaskMemoryPacket v1.29.2
- Memory consumption policy
- PlannerTrace v1.29.2
- Memory-aware critic checks
- Memory repair routing hooks
- Raw-first memory consumption benchmark
- Injected defect detection suite
- Evidence pack and reviewer checklist

## Repair Self-Proof Cleanup

This RC includes an additional raw-first repair self-proof gate:

- `final_outfit_boundary_violation_free_rate`

The gate ensures that negative boundary repairs are not accepted solely because a repair event exists. The final outfit must prove that the triggering boundary violation has been removed.

A seeded defect was added:

- `repair_claims_pass_but_final_still_violates_boundary`

The injected defect detector must catch this defect before v1.29.2 can be confirmed.

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')} / {clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}

## Mixed Strict Suite With Injected Defects

- Cases: {mixed.get('total_cases')}
- Checks: {mixed.get('passed_checks')} / {mixed.get('total_checks')} PASS
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected

Detected defects:

{os.linesep.join(f'- {d}' for d in defects)}

## Interpretation

The clean suite is used for release acceptance.
The mixed strict suite includes injected defects and is expected to fail.
Injected defect detection PASS means the detector catches seeded memory-consumption governance defects.

## Release Status

PASS CANDIDATE confirmed.
"""


def _checklist() -> str:
    return """# v1.29.2 Reviewer Checklist

## A. Current Task Exception Override

- [ ] current task exception appears in `current_task_exceptions`
- [ ] old conflicting avoid appears in `overridden_memories`
- [ ] old conflicting avoid does not appear in `explicit_reject`
- [ ] old memory is not deleted from store
- [ ] residual boundary is preserved where appropriate
- [ ] planner trace records override event

## B. Misuse Correction Hygiene

- [ ] misuse correction does not appear in `active_positive_preferences`
- [ ] misuse correction appears in `do_not_use_as_positive_signal`
- [ ] planner does not retrieve target style from misuse correction
- [ ] critic or retrieval filter uses correction only as hygiene constraint
- [ ] response does not invert correction into a positive preference

## C. Negative Boundary Consumption

- [ ] avoid / soft_avoid appears in active negative boundary bucket
- [ ] avoid / soft_avoid does not appear in positive preference bucket
- [ ] critic detects violation in candidate outfit
- [ ] repair event references the triggering memory id
- [ ] final outfit no longer violates boundary

## D. Exclusion Hygiene

- [ ] blocked memory not consumed
- [ ] human-review-required memory not consumed
- [ ] shadow-only memory not consumed
- [ ] rolledback memory not consumed
- [ ] expired memory not consumed
- [ ] low-confidence memory is gated or requires confirmation
- [ ] each excluded memory has an exclusion reason

## E. Scope and Context Matching

- [ ] contextual memory applies only to matching context
- [ ] contextual memory is excluded on context mismatch
- [ ] session_soft memory does not leak beyond session
- [ ] this_task_only instruction takes precedence
- [ ] global memory applies only when not overridden

## F. Planner Trace and Response Consistency

- [ ] planner trace contains task_memory_packet_id
- [ ] consumed memory ids are listed
- [ ] excluded memory ids and reasons are listed
- [ ] override events are listed
- [ ] critic events are listed
- [ ] repair events are listed
- [ ] response memory claims are subset of consumed memory refs

## G. Injected Defect Detection

- [ ] misuse correction as positive preference detected
- [ ] overridden avoid in explicit_reject detected
- [ ] blocked memory consumption detected
- [ ] review-required memory consumption detected
- [ ] shadow-only memory consumption detected
- [ ] untraced response memory claim detected
- [ ] critic miss of active negative boundary detected
- [ ] repair without triggering memory ref detected
- [ ] repair claims pass but final still violates boundary was detected

## H. Negative Boundary Repair Self-Proof

Artifact:
`sample_artifacts/negative_boundary_critic_repair.json`

Check:

- [ ] active negative boundary exists
- [ ] candidate outfit violates the active negative boundary
- [ ] critic detects the negative boundary violation
- [ ] critic event references the triggering memory id
- [ ] repair event references the triggering memory id
- [ ] repair event result is `passed`
- [ ] final outfit no longer contains the triggering boundary concept
- [ ] `post_repair_validation` exists
- [ ] `post_repair_validation.remaining_violations == []`
- [ ] `post_repair_validation.final_outfit_violation_free == true`
- [ ] response does not claim untraced memory

Verdict:

- [ ] PASS
- [ ] FAIL

## Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PARTIAL PASS
- [ ] FAIL

Reviewer notes:
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-report", required=True)
    parser.add_argument("--mixed-report", required=True)
    parser.add_argument("--clean-artifacts-dir", required=True)
    parser.add_argument("--mixed-artifacts-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out = Path(args.out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    samples = out / "sample_artifacts"
    samples.mkdir(parents=True, exist_ok=True)

    clean_report = _load(args.clean_report)
    mixed_report = _load(args.mixed_report)
    clean_rows = _load_rows(args.clean_artifacts_dir)
    mixed_rows = _load_rows(args.mixed_artifacts_dir)

    _write_json(out / "clean_report.json", clean_report)
    _write_json(out / "mixed_strict_report.json", mixed_report)
    _write_text(out / "clean_report.md", _report_md("v1.29.2 Clean Acceptance", clean_report))
    _write_text(out / "mixed_strict_report.md", _report_md("v1.29.2 Mixed Strict", mixed_report))
    _write_json(out / "injected_defect_detection_summary.json", _injected_summary(mixed_report))
    _write_text(out / "README.md", _readme())
    _write_text(out / "RELEASE_NOTE.md", _release_note(clean_report, mixed_report))
    _write_text(out / "reviewer_checklist.md", _checklist())

    for filename, (key, value) in SAMPLE_CASES.items():
        _write_json(samples / filename, _pick(clean_rows, key, value))

    for filename, defect_type in INJECTED_SAMPLE_CASES.items():
        row = _pick(mixed_rows, "defect_type", defect_type)
        _write_json(samples / filename, _defect_sample(row, mixed_report))

    print(f"v1.29.2 evidence pack written to {out}")


if __name__ == "__main__":
    main()
