"""Build v1.29.3 Memory UX Minimal Loop release-candidate evidence pack."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "learned_feedback_card.json": ("case_id", "v1293_A01"),
    "task_exception_this_time_only.json": ("case_id", "v1293_C01"),
    "remember_long_term_write_gate_route.json": ("case_id", "v1293_B01"),
    "do_not_remember_no_write.json": ("case_id", "v1293_B04"),
    "correct_interpretation_supersedes_wrong_proposal.json": ("case_id", "v1293_B05"),
    "misuse_correction_user_visible_hygiene.json": ("case_id", "v1293_D01"),
    "why_changed_trace_consistency.json": ("case_id", "v1293_E01"),
    "high_risk_inference_suppressed.json": ("case_id", "v1293_A05"),
}

INJECTED_SAMPLE_CASES = {
    "injected_untraced_memory_claim_detected.json": "untraced_memory_claim_in_user_visible_text",
    "injected_current_exception_globalized_detected.json": "current_exception_offered_as_global_default",
    "injected_misuse_correction_positive_ux_detected.json": "misuse_correction_offered_as_positive_preference",
    "injected_do_not_remember_still_writes_detected.json": "do_not_remember_still_writes_production",
    "injected_high_risk_inference_exposed_detected.json": "high_risk_inference_shown_without_confirmation",
    "injected_remember_bypasses_write_gate_detected.json": "remember_long_term_bypasses_write_gate",
    "injected_why_changed_excluded_memory_detected.json": "why_changed_references_excluded_memory",
    "injected_correction_does_not_deprecate_detected.json": "correction_does_not_deprecate_wrong_proposal",
    "injected_claim_refs_not_subset_detected.json": "user_visible_claim_refs_not_subset_of_trace",
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


def _find_detection(mixed_report: dict[str, Any], defect_type: str) -> dict[str, Any]:
    return next(
        (item for item in mixed_report.get("detected_defects", []) if item.get("defect_type") == defect_type),
        {},
    )


def _sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row.get("case_id"),
        "scenario": row.get("scenario"),
        "raw_user_feedback": row.get("raw_user_feedback"),
        "old_memory_snapshot": row.get("old_memory_snapshot"),
        "current_task_exception": row.get("current_task_exception"),
        "residual_boundaries": row.get("residual_boundaries"),
        "memory_proposals": row.get("memory_proposals"),
        "memory_ux_event": row.get("memory_ux_event"),
        "memory_ux_block": row.get("memory_ux_block"),
        "user_memory_action": row.get("user_memory_action"),
        "write_gate_decision": row.get("write_gate_decision"),
        "memory_ux_trace": row.get("memory_ux_trace"),
        "response": row.get("response"),
        "future_response": row.get("future_response"),
        "active_positive_preferences": row.get("active_positive_preferences"),
        "retrieval_targets": row.get("retrieval_targets"),
        "high_risk_signal": row.get("high_risk_signal"),
        "proof_summary": row.get("proof_summary"),
    }


def _defect_sample(row: dict[str, Any], mixed_report: dict[str, Any]) -> dict[str, Any]:
    defect_type = row.get("defect_type")
    detected = _find_detection(mixed_report, defect_type)
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
        "raw_artifact": _sample(row),
    }


def _injected_summary(mixed_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite": "v1.29.3 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _readme() -> str:
    return """# v1.29.3 Release Candidate Evidence Pack

## Scope

v1.29.3 verifies the minimal user-visible memory trust loop.

It does not add external inspiration intake, aesthetic cards, full memory management UI, shopping, or beta expansion.

## Verdict Semantics

Clean acceptance suite is used for release acceptance.

Mixed strict suite includes injected defects and is expected to fail.

Release candidate status is derived from:

1. clean acceptance PASS
2. injected defect detection PASS
3. no unexpected clean failures
4. manual spot review

## Memory UX Semantics

User-visible memory claims must be trace-backed.

User confirmation is required before persistent writes.

Do-not-remember must not write production memory.

Current-task exceptions must not become global preferences.

Misuse corrections must not become positive preferences.

High-risk inferences must not be automatically exposed as learned memory.
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    return f"""# v1.29.3 Release Candidate Note

## Scope

v1.29.3 focuses on Memory UX Minimal Loop.

## Key Additions

- MemoryUXEvent
- UserMemoryAction
- MemoryUXTrace
- learned feedback cards
- task exception notes
- remember / do-not-remember controls
- correction flow
- why-changed trace-backed explanations
- high-risk inference suppression

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')}/{clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}

## Mixed Strict Suite With Injected Defects

- Cases: {mixed.get('total_cases')}
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected
- Injected defect detection: {mixed_report.get('verdicts', {}).get('injected_defect_detection_verdict')}

## Release Status

PASS CANDIDATE pending manual spot review
"""


def _checklist() -> str:
    return """# v1.29.3 Reviewer Checklist

## A. Learned Feedback Card

- [ ] user feedback is interpreted narrowly and accurately
- [ ] user-visible claim has trace refs
- [ ] card does not over-generalize one-time feedback
- [ ] user has control actions
- [ ] persistent write requires confirmation

## B. Task Exception

- [ ] system says this is this-time-only
- [ ] current exception is not globalized
- [ ] old memory remains preserved
- [ ] residual boundaries are surfaced
- [ ] response does not claim new positive preference

## C. Remember Long-Term

- [ ] user action routes to write gate
- [ ] write gate decision id exists
- [ ] no direct production write bypasses governance

## D. Do Not Remember

- [ ] production write not attempted
- [ ] production write not executed
- [ ] proposal rejected / not applicable
- [ ] future response does not claim rejected memory

## E. Correction

- [ ] wrong proposal deprecated / rejected / superseded
- [ ] corrected proposal is more precise
- [ ] wrong proposal cannot enter production memory

## F. Misuse Correction

- [ ] correction is not positive preference
- [ ] correction is not retrieval target
- [ ] user-visible text frames it as interpretation correction

## G. Why Changed

- [ ] explanation references consumed memory / current evidence / override / repair event
- [ ] explanation does not reference excluded memory
- [ ] explanation does not reference blocked memory
- [ ] explanation does not reference shadow-only memory

## H. High-Risk Inference

- [ ] high-risk inference is suppressed or safely reframed
- [ ] no sensitive inferred trait is shown as learned memory without confirmation
- [ ] no persistent write occurs unless explicitly confirmed and allowed

## I. Injected Defect Detection

- [ ] untraced memory claim detected
- [ ] current exception globalized detected
- [ ] misuse correction positive UX detected
- [ ] do-not-remember write detected
- [ ] high-risk inference exposure detected
- [ ] remember bypasses write gate detected
- [ ] why-changed references excluded memory detected
- [ ] correction does not deprecate wrong proposal detected
- [ ] claim refs not subset of trace detected
"""


def _copy_report(src_json: str, out_dir: Path, out_json_name: str, out_md_name: str) -> None:
    shutil.copyfile(src_json, out_dir / out_json_name)
    src_md = Path(src_json).with_suffix(".md")
    if src_md.exists():
        shutil.copyfile(src_md, out_dir / out_md_name)
    else:
        _write_text(out_dir / out_md_name, f"# {out_md_name}\n\nSource markdown was not present.\n")


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
        _write_json(sample_dir / name, _sample(_pick(clean_rows, key, value)))
    for name, defect_type in INJECTED_SAMPLE_CASES.items():
        row = _pick(mixed_rows, "defect_type", defect_type)
        _write_json(sample_dir / name, _defect_sample(row, mixed_report))

    print(json.dumps({"out_dir": str(out_dir), "sample_artifacts": len(SAMPLE_CASES) + len(INJECTED_SAMPLE_CASES)}, indent=2))


if __name__ == "__main__":
    main()
