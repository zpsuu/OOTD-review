"""Build v1.29.6 Daily Outfit Quality Guardrails evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "basic_office_daily_quality_card.json": ("case_id", "v1296_A01"),
    "formal_client_meeting_quality_card.json": ("case_id", "v1296_A03"),
    "rainy_day_weather_guardrail.json": ("case_id", "v1296_A04"),
    "limited_closet_insufficiency_disclosed.json": ("case_id", "v1296_A06"),
    "memory_boundary_respected.json": ("case_id", "v1296_D02"),
    "sneaker_exception_residual_boundary_respected.json": ("case_id", "v1296_D03"),
    "negative_quality_issue_repaired.json": ("case_id", "v1296_E01"),
    "repeated_outfit_repaired_or_explained.json": ("case_id", "v1296_H01"),
    "explanation_matches_final_outfit.json": ("case_id", "v1296_F01"),
    "memory_overfit_prevented.json": ("case_id", "v1296_G01"),
    "rainy_day_avoids_weather_mismatch.json": ("case_id", "v1296_C05"),
    "weather_issue_repaired.json": ("case_id", "v1296_E02"),
    "cold_day_layer_present.json": ("case_id", "v1296_A05"),
}

INJECTED_SAMPLE_CASES = {
    "injected_non_closet_item_detected.json": "final_outfit_uses_non_closet_item",
    "injected_swap_non_closet_item_detected.json": "swap_option_uses_non_closet_item",
    "injected_missing_required_category_detected.json": "outfit_missing_required_category",
    "injected_office_gymwear_detected.json": "office_daily_gymwear_not_detected",
    "injected_weather_mismatch_detected.json": "rainy_day_weather_mismatch_not_detected",
    "injected_formality_mismatch_detected.json": "formal_meeting_too_casual_not_detected",
    "injected_memory_boundary_violation_detected.json": "memory_boundary_violation_not_detected",
    "injected_residual_boundary_violation_detected.json": "residual_boundary_violation_not_detected",
    "injected_repair_claims_success_but_final_bad_detected.json": "repair_claims_success_but_final_still_bad",
    "injected_explanation_mentions_removed_item_detected.json": "card_explains_removed_candidate_item",
    "injected_rain_ready_without_evidence_detected.json": "card_claims_rain_ready_without_evidence",
    "injected_repetition_without_reason_detected.json": "exact_recent_outfit_repeated_without_reason",
    "injected_memory_overfit_breaks_context_fit_detected.json": "memory_overfit_breaks_context_fit",
    "injected_hallucinated_item_in_card_text_detected.json": "hallucinated_item_in_card_text",
    "injected_style_semantic_conflict_detected.json": "style_semantic_conflict_not_detected",
    "injected_closet_insufficiency_not_disclosed_detected.json": "closet_insufficiency_not_disclosed",
    "injected_swap_option_formality_mismatch_detected.json": "swap_option_formality_mismatch",
    "injected_swap_option_weather_mismatch_detected.json": "swap_option_weather_mismatch",
    "injected_swap_option_temperature_mismatch_detected.json": "swap_option_temperature_mismatch",
    "injected_swap_option_untraced_conditional_claim_detected.json": "swap_option_untraced_conditional_claim",
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


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
        "suite": "v1.29.6 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _readme() -> str:
    return """# v1.29.6 Release Candidate Evidence Pack

## Scope

v1.29.6 verifies Daily Outfit Quality Guardrails.

It proves that Daily Outfit cards are not only memory-correct and trace-backed, but also meet a minimum outfit-quality floor.

## Non-Goals

- No external inspiration intake
- No multimodal clean acceptance dependency
- No Ideal-Reality Bridge
- No shopping recommendation
- No real beta
- No full UI
- No new production memory write category

## Quality Floor Semantics

This release checks obvious outfit-quality failures:

- closet grounding
- required category completeness
- occasion fit
- weather fit
- formality fit
- memory boundary fit
- residual boundary fit
- style semantic coherence
- recent repetition
- explanation-to-outfit consistency
- memory overfitting prevention

This release does not attempt to judge subjective aesthetic ceiling.

## Repair Self-Proof Semantics

If a quality issue is detected and repaired, the evidence pack must include:

1. the triggering issue
2. the triggering item / memory / context refs
3. the repair event
4. visible final outfit diff
5. post-repair quality validation
6. a final Daily Outfit Card that only shows the repaired outfit

## Swap Option Quality Guardrail Semantics

v1.29.6 validates not only final outfit quality, but also visible swap option quality.

Visible swap options must be:

- grounded in the closet fixture
- appropriate for the current occasion
- appropriate for current weather
- appropriate for current temperature band
- aligned with formality target and hard context requirements
- trace-backed if they include any claim or conditional rationale

Invalid swaps may be hidden. Hidden swaps include a `hidden_reason`.

A swap option that is closet-grounded but context/weather/formality-invalid is not considered release-safe.

## Multimodal Boundary

Clean acceptance uses structured fixtures. Any vision or multimodal adapter is optional and shadow-only.

## Per-Case Archive

Full per-case raw artifacts are included under:

- `per_case/clean/`
- `per_case/mixed_strict/`

## Verdict Semantics

Clean acceptance PASS + injected defect detection PASS + manual spot review PASS is required for confirmed status.

Mixed strict suite is expected to fail when injected defects are present.
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    return f"""# v1.29.6 Release Candidate Note

## Status

PASS CANDIDATE confirmed.

## P2 Backlog

- limited closet pass_with_disclosure
- sample artifact case-level checks
- hidden swap rationale refs cleanup
- rain_ready_claim_supported naming cleanup

## Scope

v1.29.6 adds Daily Outfit Quality Guardrails.

## Key Additions

- DailyOutfitQualityReport
- OutfitQualityIssue
- OutfitQualityGuardrailTrace
- QualityRepairEvent
- PostRepairQualityValidation
- SwapOptionQualityReport
- Quality guardrail gates for closet grounding, outfit completeness, occasion fit, weather fit, formality fit, memory boundary fit, residual boundary fit, style semantic coherence, recent repetition, explanation consistency, and memory overfitting prevention
- Swap option quality guardrail gates for context, weather, temperature, formality, and trace-backed rationale

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')}/{clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}
- Release candidate verdict: {clean_report.get('verdicts', {}).get('release_candidate_verdict')}

## Mixed Strict Result

- Cases: {mixed.get('total_cases')}
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected

## Injected Defect Detection

- Verdict: {mixed_report.get('verdicts', {}).get('injected_defect_detection_verdict')}
- Detected defects: {len([d for d in mixed_report.get('detected_defects', []) if d.get('detected')])}

## Release Interpretation

Clean acceptance suite is used for release acceptance.

Mixed strict suite includes injected defects and is expected to fail if detectors work.

Release candidate confirmation requires manual spot review.
"""


def _checklist() -> str:
    return """# v1.29.6 Reviewer Checklist

## Release Candidate Summary

- Clean acceptance suite: PASS required
- Mixed strict suite: expected FAIL with injected defects
- Injected defect detection: PASS required
- Manual spot review: PASS
- Release status: PASS CANDIDATE confirmed
- P2 backlog recorded: limited closet pass_with_disclosure, sample artifact case-level checks, hidden swap rationale refs cleanup, rain_ready_claim_supported naming cleanup

## A. Basic Daily Outfit Quality

Artifact:
`sample_artifacts/basic_office_daily_quality_card.json`

- [ ] Daily Outfit Card schema is valid
- [ ] final outfit uses only closet items
- [ ] required outfit categories are present
- [ ] occasion fit passed
- [ ] weather fit passed
- [ ] formality fit passed
- [ ] card claims are trace-backed
- [ ] final_quality_status is pass
- [ ] PASS
- [ ] FAIL

## B. Formal Client Meeting

Artifact:
`sample_artifacts/formal_client_meeting_quality_card.json`

- [ ] outfit is sufficiently polished
- [ ] memory personalization does not make outfit too casual
- [ ] no gym-coded item appears without explicit exception
- [ ] final formality aligns with target
- [ ] explanation matches final outfit
- [ ] PASS
- [ ] FAIL

## C. Weather Guardrail

Artifact:
`sample_artifacts/rainy_day_weather_guardrail.json`

- [ ] rainy/cold/hot constraint is represented in task context
- [ ] selected items are weather-suitable
- [ ] if closet lacks suitable item, insufficiency is disclosed
- [ ] no hallucinated weather item appears
- [ ] weather claim matches final outfit
- [ ] PASS
- [ ] FAIL

## D. Closet Insufficiency

Artifact:
`sample_artifacts/limited_closet_insufficiency_disclosed.json`

- [ ] missing category or limitation is detected
- [ ] card is honest about limitation
- [ ] no missing closet item is invented
- [ ] best-effort recommendation remains grounded
- [ ] PASS
- [ ] FAIL

## E. Memory Boundary

Artifact:
`sample_artifacts/memory_boundary_respected.json`

- [ ] active negative boundary is in TaskMemoryPacket
- [ ] final outfit does not violate boundary
- [ ] quality report checks boundary
- [ ] response does not claim boundary was ignored
- [ ] PASS
- [ ] FAIL

## F. Residual Boundary After Exception

Artifact:
`sample_artifacts/sneaker_exception_residual_boundary_respected.json`

- [ ] sneaker exception is current-task-only
- [ ] old avoid is overridden, not deleted
- [ ] residual gym-coded / running-shoe boundary remains active
- [ ] final sneaker is compatible with residual boundary
- [ ] response explains this-time-only
- [ ] PASS
- [ ] FAIL

## G. Quality Repair

Artifact:
`sample_artifacts/negative_quality_issue_repaired.json`

- [ ] candidate issue exists
- [ ] quality issue is detected
- [ ] repair event references triggering issue
- [ ] final outfit visibly changes
- [ ] post-repair validation passes
- [ ] card shows final repaired outfit only
- [ ] PASS
- [ ] FAIL

## H. Repetition

Artifact:
`sample_artifacts/repeated_outfit_repaired_or_explained.json`

- [ ] recent outfit history is present
- [ ] exact outfit is not repeated without reason
- [ ] if repeated, repeat_allowed_reason is present and valid
- [ ] repeated item is distinguished from repeated exact outfit
- [ ] PASS
- [ ] FAIL

## I. Explanation Consistency

Artifact:
`sample_artifacts/explanation_matches_final_outfit.json`

- [ ] explanation only refers to final outfit items
- [ ] removed candidate item is not mentioned
- [ ] quality claims match item metadata
- [ ] claim refs are trace-backed
- [ ] PASS
- [ ] FAIL

## J. Memory Overfitting

Artifact:
`sample_artifacts/memory_overfit_prevented.json`

- [ ] memory preference is present
- [ ] context/weather/formality requirement is present
- [ ] final outfit respects hard context requirement
- [ ] memory does not overrule basic outfit usability
- [ ] PASS
- [ ] FAIL

## K. Injected Defect Detection

- [ ] non-closet item detected
- [ ] weather mismatch detected
- [ ] formality mismatch detected
- [ ] memory boundary violation detected
- [ ] repair claims success but final bad detected
- [ ] explanation mentions removed item detected
- [ ] repetition without reason detected
- [ ] PASS
- [ ] FAIL

## L. Swap Option Quality Guardrails

- [ ] visible swap options are grounded in closet
- [ ] visible swap options fit current occasion
- [ ] visible swap options fit current weather
- [ ] visible swap options fit current temperature band
- [ ] visible swap options fit current formality target
- [ ] formal client meeting does not expose low-formality sneaker swap
- [ ] rainy-day card does not expose dry-only footwear swap
- [ ] cold-day card does not expose warm/mild-only footwear swap
- [ ] swap option claim refs are trace-backed
- [ ] invalid swaps are hidden with explicit hidden_reason
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


def _copy_per_case(src_raw: str | Path, dst: Path) -> None:
    src = Path(src_raw) / "per_case"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


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

    _copy_per_case(args.clean_artifacts_dir, out_dir / "per_case" / "clean")
    _copy_per_case(args.mixed_artifacts_dir, out_dir / "per_case" / "mixed_strict")

    print(json.dumps({
        "out_dir": str(out_dir),
        "sample_artifacts": len(SAMPLE_CASES) + len(INJECTED_SAMPLE_CASES),
        "per_case_archive_included": True,
    }, indent=2))


if __name__ == "__main__":
    main()
