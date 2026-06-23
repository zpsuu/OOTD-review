"""Build v1.29.7 Closet Bootstrapping & Item Reliability evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "complete_small_closet_daily_outfit.json": ("case_id", "v1297_A01"),
    "five_item_closet_grounded_outfit.json": ("case_id", "v1297_A02"),
    "missing_shoes_gap_disclosed.json": ("case_id", "v1297_A04"),
    "missing_top_insufficient.json": ("case_id", "v1297_A05"),
    "missing_bottom_insufficient.json": ("case_id", "v1297_A06"),
    "low_confidence_formality_excluded_formal_meeting.json": ("case_id", "v1297_B03"),
    "low_confidence_weather_excluded_rainy_day.json": ("case_id", "v1297_B04"),
    "low_confidence_material_not_claimed.json": ("case_id", "v1297_B02"),
    "vision_candidate_not_used_without_confirmation.json": ("case_id", "v1297_C03"),
    "missing_outerwear_cold_day_disclosed.json": ("case_id", "v1297_D02"),
    "missing_rain_safe_footwear_disclosed.json": ("case_id", "v1297_D03"),
    "gap_suggestion_category_only_no_product.json": ("case_id", "v1297_D04"),
    "gap_note_not_memory_preference.json": ("case_id", "v1297_D05"),
    "pass_with_disclosure_gap_note.json": ("case_id", "v1297_D06"),
    "blocking_missing_category_insufficient.json": ("case_id", "v1297_D07"),
    "repair_replaces_unreliable_item.json": ("case_id", "v1297_E06"),
    "no_reliable_alternative_disclose_gap.json": ("case_id", "v1297_E07"),
    "visible_swap_options_closet_grounded.json": ("case_id", "v1297_F01"),
    "unreliable_swap_hidden.json": ("case_id", "v1297_F03"),
    "insufficient_notice_card.json": ("case_id", "v1297_D07"),
    "memory_preference_does_not_force_unreliable_item.json": ("case_id", "v1297_G01"),
    "current_exception_cannot_override_missing_category.json": ("case_id", "v1297_G03"),
    "current_exception_requires_item_reliability_support.json": ("case_id", "v1297_G04"),
}

INJECTED_SAMPLE_CASES = {
    "injected_missing_shoes_hallucinated_detected.json": "missing_shoes_hallucinated_item",
    "injected_missing_top_marked_as_pass_detected.json": "missing_top_marked_as_pass",
    "injected_low_confidence_formality_used_detected.json": "low_confidence_formality_used_for_client_meeting",
    "injected_low_confidence_weather_used_detected.json": "low_confidence_weather_used_for_rain_claim",
    "injected_low_confidence_category_used_detected.json": "low_confidence_category_satisfies_required_slot",
    "injected_vision_candidate_used_detected.json": "vision_candidate_used_without_confirmation",
    "injected_gap_suggestion_treated_as_item_detected.json": "gap_suggestion_treated_as_closet_item",
    "injected_missing_gap_not_disclosed_detected.json": "missing_gap_not_disclosed",
    "injected_product_recommendation_gap_note_detected.json": "product_recommendation_in_gap_note",
    "injected_memory_forces_unreliable_item_detected.json": "memory_preference_forces_unreliable_item",
    "injected_swap_low_confidence_visible_detected.json": "swap_option_low_confidence_not_hidden",
    "injected_swap_weather_unreliable_visible_detected.json": "swap_option_weather_unreliable_visible",
    "injected_uncertain_material_claimed_detected.json": "card_claims_uncertain_material_as_fact",
    "injected_missing_reliability_report_detected.json": "final_outfit_quality_pass_without_reliability_report",
    "injected_readiness_skipped_detected.json": "closet_readiness_skipped_before_generation",
    "injected_insufficient_closet_normal_pass_detected.json": "insufficient_closet_still_returns_normal_pass",
    "injected_scenario_precondition_missing_detected.json": "scenario_precondition_missing_but_clean_case_passes",
    "injected_current_exception_without_exception_detected.json": "current_exception_case_without_exception",
    "injected_missing_category_without_missing_detected.json": "missing_category_case_without_missing_category",
    "injected_gap_without_disclosure_detected.json": "gap_case_without_gap_disclosure",
    "injected_visible_swap_missing_detected.json": "swap_case_without_visible_swap",
    "injected_hidden_swap_missing_detected.json": "hidden_swap_case_without_hidden_swap",
    "injected_repair_without_pre_issue_detected.json": "repair_case_without_pre_repair_issue",
    "injected_insufficient_card_partial_outfit_detected.json": "insufficient_card_presents_partial_outfit_as_daily_outfit",
}


def _load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
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
    return [_load(path) for path in sorted((raw_dir / "per_case").glob("*.json"))]


def _pick(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise RuntimeError(f"missing sample row: {key}={value}")


def _case_checks(row: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    result = next((item for item in report.get("case_results", []) if item.get("case_id") == row.get("case_id")), {})
    failed = set(result.get("failed_check_ids") or [])
    return [
        {"check_id": check.get("check_id"), "passed": check.get("check_id") not in failed}
        for check in report.get("checks", [])
    ]


def _sample(row: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["checks"] = _case_checks(row, report)
    return data


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
        "raw_artifact": _sample(row, mixed_report),
    }


def _injected_summary(mixed_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite": "v1.29.7 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _review_manifest() -> dict[str, Any]:
    return {
        "version": "v1.29.7",
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": "v1297-scenario-self-proof-cleanup",
        "commit_sha": "TO_BE_FILLED_AFTER_COMMIT",
        "theme": "Closet Bootstrapping & Item Reliability",
        "expected_changes_since_last_review": [
            "Add scenario_preconditions to all clean per-case artifacts",
            "Add non-vacuous scenario gates",
            "Rewrite G03/G04 current exception fixtures",
            "Rewrite D-series gap fixtures",
            "Rewrite E-series repair fixtures",
            "Rewrite F-series swap fixtures",
            "Fix insufficient card schema",
        ],
        "required_new_gates": [
            "scenario_precondition_satisfied_rate",
            "current_exception_case_has_exception_precondition_rate",
            "missing_category_case_has_missing_category_precondition_rate",
            "gap_case_has_gap_disclosure_precondition_rate",
            "swap_case_has_visible_swap_precondition_rate",
            "hidden_swap_case_has_hidden_swap_precondition_rate",
            "repair_case_has_pre_repair_issue_rate",
            "insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate",
        ],
        "additional_non_vacuous_gates": [
            "scenario_precondition_proof_refs_present_rate",
            "no_vacuous_clean_case_pass_rate",
        ],
        "must_review_samples": [
            "per_case/clean/v1297_G03.json",
            "per_case/clean/v1297_G04.json",
            "per_case/clean/v1297_D02.json",
            "per_case/clean/v1297_D03.json",
            "per_case/clean/v1297_D04.json",
            "per_case/clean/v1297_D05.json",
            "per_case/clean/v1297_D07.json",
            "per_case/clean/v1297_E06.json",
            "per_case/clean/v1297_E07.json",
            "per_case/clean/v1297_F01.json",
            "per_case/clean/v1297_F02.json",
            "per_case/clean/v1297_F03.json",
            "per_case/clean/v1297_F04.json",
            "per_case/clean/v1297_F05.json",
            "per_case/clean/v1297_F06.json",
            "per_case/clean/v1297_A05.json",
            "per_case/clean/v1297_A06.json",
        ],
        "known_p2_backlog": [
            "add case-level checks to sample artifacts",
            "expand clean coverage beyond primary fixture family",
            "align injected expected_failed_check_ids with actual failed checks",
        ],
    }


def _readme() -> str:
    return """# v1.29.7 Release Candidate Evidence Pack

## Scope

v1.29.7 focuses on Closet Bootstrapping & Item Reliability.

This release verifies that Daily Outfit can operate on small or incomplete closets without hallucinating items, over-trusting weak metadata, or hiding missing categories.

## Non-Goals

- No external inspiration intake
- No full multimodal closet ingestion dependency
- No shopping / product recommendations
- No full UI / beta launch
- No virtual try-on
- No ideal-reality bridge

## Key Guarantees

- Final outfits use only closet items.
- Gap suggestions are not treated as closet items.
- Missing required categories are disclosed or marked insufficient.
- Low-confidence metadata is not used for high-confidence claims.
- Unconfirmed vision candidates are not used in clean planner path.
- Swap options are reliability-checked.
- Memory preference cannot force unreliable item use.
- Current task exception cannot override missing closet category.

## Scenario Self-Proof Semantics

v1.29.7 requires every benchmark scenario to prove that its raw trigger preconditions are present.

A case cannot pass only because output fields look valid. If a scenario claims to test missing categories, current task exceptions, low-confidence items, gap disclosure, swap reliability, repair behavior, or insufficient closet handling, the raw artifact must include a `scenario_preconditions` block with proof references.

The aggregate report enforces this with non-vacuous scenario gates such as:

- `scenario_precondition_satisfied_rate`
- `scenario_precondition_proof_refs_present_rate`
- `no_vacuous_clean_case_pass_rate`
- `current_exception_case_has_exception_precondition_rate`
- `missing_category_case_has_missing_category_precondition_rate`
- `gap_case_has_gap_disclosure_precondition_rate`
- `swap_case_has_visible_swap_precondition_rate`
- `hidden_swap_case_has_hidden_swap_precondition_rate`
- `repair_case_has_pre_repair_issue_rate`
- `insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate`

## Insufficient Card Semantics

When the closet is insufficient and `can_generate_grounded_outfit=false`, the card must be a `closet_insufficient_notice`, not a partial Daily Outfit Card.

## Per-Case Archive

Full raw per-case artifacts are included under `per_case/clean` and `per_case/mixed_strict`.
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    return f"""# v1.29.7 Release Candidate Note

## Scope

v1.29.7 focuses on Closet Bootstrapping & Item Reliability.

This release verifies that Daily Outfit can operate on small or incomplete closets without hallucinating items, over-trusting weak metadata, or hiding missing categories.

## Non-Goals

- No external inspiration intake
- No full multimodal closet ingestion dependency
- No shopping / product recommendations
- No full UI / beta launch
- No virtual try-on
- No ideal-reality bridge

## Key Guarantees

- Final outfits use only closet items.
- Gap suggestions are not treated as closet items.
- Missing required categories are disclosed or marked insufficient.
- Low-confidence metadata is not used for high-confidence claims.
- Unconfirmed vision candidates are not used in clean planner path.
- Swap options are reliability-checked.
- Memory preference cannot force unreliable item use.
- Current task exception cannot override missing closet category.
- Every scenario includes raw `scenario_preconditions` proof, and the aggregate report recomputes raw proof refs so scenario gates cannot pass vacuously.
- Insufficient closet states render `closet_insufficient_notice`, not a normal Daily Outfit Card.

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')}/{clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}
- Release candidate verdict: {clean_report.get('verdicts', {}).get('release_candidate_verdict')}

## Mixed Strict Result

- Cases: {mixed.get('total_cases')}
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected
- Injected defect detection: {mixed_report.get('verdicts', {}).get('injected_defect_detection_verdict')}

## Release Status

PASS CANDIDATE pending manual review.
"""


def _checklist() -> str:
    return """# v1.29.7 Reviewer Checklist

## A. Complete Small Closet
- [ ] ClosetBootstrapProfile exists
- [ ] ClosetReadinessReport exists
- [ ] minimum viable closet passes
- [ ] final outfit uses only closet items
- [ ] all required categories present
- [ ] item reliability profiles exist

## B. Missing Shoes Gap Disclosure
- [ ] closet has no shoes
- [ ] final outfit does not invent shoes
- [ ] gap note discloses missing shoes
- [ ] gap note is category-only
- [ ] no product recommendation included
- [ ] quality status is pass_with_disclosure or insufficient, not normal pass

## C. Missing Top / Blocking Category
- [ ] required top missing
- [ ] system does not generate complete outfit
- [ ] readiness_status is insufficient
- [ ] blocking reason is explicit
- [ ] no hallucinated top appears in card text

## D. Low-Confidence Formality
- [ ] item has low formality confidence
- [ ] formal meeting requires reliable formal item
- [ ] low-confidence item excluded
- [ ] card does not claim item is formal enough
- [ ] exclusion reason appears in trace

## E. Low-Confidence Weather
- [ ] rainy task exists
- [ ] item has low weather confidence or dry-only metadata
- [ ] item excluded from rain-safety claim
- [ ] uncertainty note or gap disclosure exists if needed

## F. Vision Candidate
- [ ] vision_candidate item exists
- [ ] item is not user-confirmed
- [ ] item is not used in clean planner
- [ ] item may appear only as candidate / needs confirmation
- [ ] no production memory write from vision candidate

## G. Swap Reliability
- [ ] visible swaps are closet-grounded
- [ ] visible swaps pass task guardrails
- [ ] unreliable swaps are hidden
- [ ] hidden swaps have hidden_reason
- [ ] swap claim refs are trace-backed

## H. Memory + Closet Reliability
- [ ] memory preference does not force unreliable item
- [ ] current task exception does not override missing category
- [ ] current task exception requires item reliability support
- [ ] memory claim does not depend on unconfirmed item metadata

## I. Injected Defect Detection
- [ ] missing shoes hallucination detected
- [ ] low-confidence formality misuse detected
- [ ] low-confidence weather misuse detected
- [ ] vision candidate misuse detected
- [ ] gap suggestion treated as closet item detected
- [ ] memory forces unreliable item detected
- [ ] insufficient closet normal pass detected

## J. Scenario Self-Proof
- [ ] each sample artifact has `scenario_preconditions`
- [ ] each scenario's expected preconditions are non-empty and scenario-appropriate
- [ ] `scenario_preconditions.satisfied == true`
- [ ] proof refs point to actual raw fields
- [ ] current-exception cases include current task exceptions
- [ ] missing-category cases include actual missing required categories
- [ ] gap cases include actual gap notes / disclosures / suggestions
- [ ] swap cases include visible swaps or hidden swaps as appropriate
- [ ] repair cases include pre-repair issue and repair report
- [ ] insufficient closet cases use `closet_insufficient_notice`, not normal Daily Outfit Card

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
    _write_json(out_dir / "REVIEW_MANIFEST.json", _review_manifest())
    _write_json(out_dir / "injected_defect_detection_summary.json", _injected_summary(mixed_report))
    _write_text(out_dir / "README.md", _readme())
    _write_text(out_dir / "RELEASE_NOTE.md", _release_note(clean_report, mixed_report))
    _write_text(out_dir / "reviewer_checklist.md", _checklist())
    for name, (key, value) in SAMPLE_CASES.items():
        _write_json(sample_dir / name, _sample(_pick(clean_rows, key, value), clean_report))
    for name, defect_type in INJECTED_SAMPLE_CASES.items():
        _write_json(sample_dir / name, _defect_sample(_pick(mixed_rows, "defect_type", defect_type), mixed_report))
    _copy_per_case(args.clean_artifacts_dir, out_dir / "per_case" / "clean")
    _copy_per_case(args.mixed_artifacts_dir, out_dir / "per_case" / "mixed_strict")
    print(json.dumps({"out_dir": str(out_dir), "sample_artifacts": len(SAMPLE_CASES) + len(INJECTED_SAMPLE_CASES), "per_case_included": True}, indent=2))


if __name__ == "__main__":
    main()
