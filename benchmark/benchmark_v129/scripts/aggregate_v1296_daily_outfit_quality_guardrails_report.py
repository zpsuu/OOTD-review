"""Aggregate v1.29.6 Daily Outfit Quality Guardrails reports."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve()
for parent in ROOT.parents:
    code_root = parent / "code"
    if (code_root / "mvp" / "services").is_dir():
        sys.path.insert(0, str(code_root))
        break

from mvp.services.outfit_quality.daily_outfit_quality_guardrails import (  # noqa: E402
    QUALITY_SCHEMA_VERSION,
    categories_for,
    detect_quality_issues,
    item_map,
    required_categories,
    swap_option_violations,
)


BENCHMARK_ID = "v1.29.6.daily_outfit_quality_guardrails"

THRESHOLDS = {
    "daily_outfit_quality_artifact_schema_valid_rate": 1.0,
    "daily_outfit_card_schema_valid_rate": 1.0,
    "quality_outfit_uses_only_closet_items_rate": 1.0,
    "quality_swap_options_grounded_rate": 1.0,
    "card_text_no_hallucinated_item_rate": 1.0,
    "outfit_required_categories_present_rate": 1.0,
    "closet_insufficiency_disclosed_rate": 1.0,
    "occasion_fit_pass_rate": 1.0,
    "weather_fit_pass_rate": 1.0,
    "weather_issue_repaired_or_disclosed_rate": 1.0,
    "formality_target_alignment_rate": 1.0,
    "quality_memory_boundary_violation_free_rate": 1.0,
    "quality_residual_boundary_respected_rate": 1.0,
    "misuse_correction_quality_hygiene_rate": 1.0,
    "style_semantic_conflict_free_rate": 1.0,
    "quality_issue_detection_rate": 1.0,
    "quality_repair_has_triggering_issue_ref_rate": 1.0,
    "post_repair_quality_validation_present_rate": 1.0,
    "post_repair_final_quality_pass_rate": 1.0,
    "repair_result_matches_final_outfit_diff_rate": 1.0,
    "card_explanation_matches_final_outfit_rate": 1.0,
    "card_quality_claim_trace_coverage_rate": 1.0,
    "card_does_not_explain_removed_candidate_item_rate": 1.0,
    "quality_exact_recent_outfit_not_repeated_without_reason_rate": 1.0,
    "quality_repeat_allowed_reason_present_rate": 1.0,
    "recent_outfit_history_in_quality_trace_rate": 1.0,
    "memory_personalization_does_not_break_context_fit_rate": 1.0,
    "swap_options_context_fit_rate": 1.0,
    "swap_options_weather_fit_rate": 1.0,
    "swap_options_temperature_fit_rate": 1.0,
    "swap_options_formality_fit_rate": 1.0,
    "swap_option_claim_trace_coverage_rate": 1.0,
}

EXPECTED_DEFECTS = {
    "final_outfit_uses_non_closet_item": ["quality_outfit_uses_only_closet_items_rate"],
    "swap_option_uses_non_closet_item": ["quality_swap_options_grounded_rate"],
    "outfit_missing_required_category": ["outfit_required_categories_present_rate", "closet_insufficiency_disclosed_rate"],
    "office_daily_gymwear_not_detected": ["occasion_fit_pass_rate", "style_semantic_conflict_free_rate"],
    "rainy_day_weather_mismatch_not_detected": ["weather_fit_pass_rate", "weather_issue_repaired_or_disclosed_rate"],
    "formal_meeting_too_casual_not_detected": ["occasion_fit_pass_rate", "formality_target_alignment_rate"],
    "memory_boundary_violation_not_detected": ["quality_memory_boundary_violation_free_rate"],
    "residual_boundary_violation_not_detected": ["quality_residual_boundary_respected_rate", "misuse_correction_quality_hygiene_rate"],
    "repair_claims_success_but_final_still_bad": ["post_repair_final_quality_pass_rate", "repair_result_matches_final_outfit_diff_rate"],
    "card_explains_removed_candidate_item": ["card_explanation_matches_final_outfit_rate", "card_does_not_explain_removed_candidate_item_rate"],
    "card_claims_rain_ready_without_evidence": ["weather_fit_pass_rate", "card_explanation_matches_final_outfit_rate"],
    "exact_recent_outfit_repeated_without_reason": ["quality_exact_recent_outfit_not_repeated_without_reason_rate", "quality_repeat_allowed_reason_present_rate"],
    "memory_overfit_breaks_context_fit": ["memory_personalization_does_not_break_context_fit_rate", "occasion_fit_pass_rate"],
    "hallucinated_item_in_card_text": ["card_text_no_hallucinated_item_rate", "card_explanation_matches_final_outfit_rate"],
    "style_semantic_conflict_not_detected": ["style_semantic_conflict_free_rate"],
    "closet_insufficiency_not_disclosed": ["outfit_required_categories_present_rate", "closet_insufficiency_disclosed_rate"],
    "swap_option_formality_mismatch": ["swap_options_context_fit_rate", "swap_options_formality_fit_rate"],
    "swap_option_weather_mismatch": ["swap_options_weather_fit_rate"],
    "swap_option_temperature_mismatch": ["swap_options_temperature_fit_rate"],
    "swap_option_untraced_conditional_claim": ["swap_option_claim_trace_coverage_rate"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _load_raw_dir(path: str) -> list[dict[str, Any]]:
    results = os.path.join(path, "results.json")
    if os.path.exists(results):
        with open(results, encoding="utf-8") as f:
            return json.load(f)
    per_case = os.path.join(path, "per_case")
    rows = []
    for name in sorted(os.listdir(per_case)):
        if name.endswith(".json"):
            with open(os.path.join(per_case, name), encoding="utf-8") as f:
                rows.append(json.load(f))
    return rows


def _card(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("final_daily_outfit_card") or {}


def _closet(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("closet_fixture") or {}


def _task(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("task_context") or {}


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("task_memory_packet") or {}


def _history(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("outfit_history") or {}


def _final_item_ids(row: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in _card(row).get("outfit_items", []) if item.get("item_id")]


def _swap_item_ids(row: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in _card(row).get("swap_options", []) if item.get("item_id")]


def _visible_swaps(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        option for option in _card(row).get("swap_options", [])
        if option.get("visible", True) is not False
    ]


def _swap_trace_refs(row: dict[str, Any]) -> set[str]:
    card = _card(row)
    trace = row.get("quality_trace") or {}
    refs = set(card.get("current_task_evidence_refs") or [])
    refs |= set(card.get("conditional_swap_rationale_refs") or [])
    refs |= set(trace.get("current_task_evidence_refs") or [])
    refs |= set(trace.get("conditional_swap_rationale_refs") or [])
    refs |= set(trace.get("card_claim_refs") or [])
    refs |= set(_packet(row).get("consumed_memory_ids") or [])
    return refs


def _swap_violations(row: dict[str, Any], option: dict[str, Any]) -> set[str]:
    return set(
        swap_option_violations(
            option,
            closet=_closet(row),
            task_context=_task(row),
            trace_refs=_swap_trace_refs(row),
        )
    )


def _issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    return detect_quality_issues(
        item_ids=_final_item_ids(row),
        closet=_closet(row),
        task_context=_task(row),
        task_memory_packet=_packet(row),
        outfit_history=_history(row),
        card=_card(row),
    )


def _issue_types(row: dict[str, Any]) -> set[str]:
    return {issue.get("issue_type") for issue in _issues(row)}


def _issue_ids(row: dict[str, Any]) -> set[str]:
    return {issue.get("quality_issue_id") for issue in _issues(row)}


def _has_issue(row: dict[str, Any], issue_type: str) -> bool:
    return issue_type in _issue_types(row)


def _schema_valid(row: dict[str, Any]) -> bool:
    required = {
        "run_id",
        "case_id",
        "task_context",
        "closet_fixture",
        "memory_fixture",
        "outfit_history",
        "task_memory_packet",
        "aesthetic_direction",
        "candidate_outfits",
        "pre_quality_report",
        "quality_repair_events",
        "final_daily_outfit_card",
        "final_quality_report",
        "quality_trace",
    }
    report_required = {
        "quality_report_id",
        "quality_schema_version",
        "evaluated_outfit_id",
        "guardrail_results",
        "quality_issues",
        "repair_required",
        "final_quality_status",
    }
    report = row.get("final_quality_report") or {}
    return (
        required <= set(row)
        and row.get("schema_version") == QUALITY_SCHEMA_VERSION
        and report_required <= set(report)
        and report.get("quality_schema_version") == QUALITY_SCHEMA_VERSION
        and bool(row.get("candidate_outfits"))
    )


def _card_schema_valid(row: dict[str, Any]) -> bool:
    required = {"card_id", "card_schema_version", "headline", "direction", "outfit_items", "why_this_works", "swap_options", "feedback_actions"}
    card = _card(row)
    return required <= set(card) and card.get("card_schema_version") == QUALITY_SCHEMA_VERSION and bool(card.get("outfit_items"))


def _outfit_closet(row: dict[str, Any]) -> bool:
    closet_ids = set(item_map(_closet(row)))
    return set(_final_item_ids(row)) <= closet_ids


def _swap_grounded(row: dict[str, Any]) -> bool:
    closet_ids = set(item_map(_closet(row)))
    return set(_swap_item_ids(row)) <= closet_ids


def _card_text_no_hallucinated(row: dict[str, Any]) -> bool:
    closet_ids = set(item_map(_closet(row)))
    return set(_card(row).get("mentioned_item_ids") or []) <= closet_ids


def _required_categories(row: dict[str, Any]) -> bool:
    missing = required_categories(_task(row)) - categories_for(_final_item_ids(row), _closet(row))
    return not missing or bool(_card(row).get("closet_insufficiency_note"))


def _insufficiency_disclosed(row: dict[str, Any]) -> bool:
    missing = required_categories(_task(row)) - categories_for(_final_item_ids(row), _closet(row))
    return not missing or bool(_card(row).get("closet_insufficiency_note"))


def _occasion_fit(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "occasion_mismatch")


def _weather_fit(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "weather_mismatch")


def _weather_repaired_or_disclosed(row: dict[str, Any]) -> bool:
    if not _has_issue(row, "weather_mismatch"):
        return True
    return bool(_card(row).get("weather_limitation_note") or _card(row).get("closet_insufficiency_note"))


def _formality_fit(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "formality_mismatch")


def _memory_boundary(row: dict[str, Any]) -> bool:
    return not any(
        issue.get("issue_type") == "memory_boundary_violation"
        and issue.get("quality_issue_id") != "qi_residual_athletic"
        for issue in _issues(row)
    )


def _residual_boundary(row: dict[str, Any]) -> bool:
    return "qi_residual_athletic" not in _issue_ids(row)


def _misuse_correction_hygiene(row: dict[str, Any]) -> bool:
    consumed = set(_packet(row).get("consumed_memory_ids") or [])
    if "mem_corrected_running_shoe_boundary" not in consumed:
        return True
    return "qi_running_shoe_boundary" not in _issue_ids(row) and "qi_residual_athletic" not in _issue_ids(row)


def _style_conflict(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "style_semantic_conflict")


def _quality_issue_detection(row: dict[str, Any]) -> bool:
    for candidate in row.get("candidate_outfits") or []:
        candidate_issues = detect_quality_issues(
            item_ids=candidate.get("item_ids") or [],
            closet=_closet(row),
            task_context=_task(row),
            task_memory_packet=_packet(row),
            outfit_history=_history(row),
        )
        if candidate_issues:
            recorded = {issue.get("quality_issue_id") for issue in (row.get("pre_quality_report") or {}).get("quality_issues", [])}
            if not {issue.get("quality_issue_id") for issue in candidate_issues} <= recorded:
                return False
    return True


def _repair_trigger_refs(row: dict[str, Any]) -> bool:
    issues = {issue.get("quality_issue_id") for issue in (row.get("pre_quality_report") or {}).get("quality_issues", [])}
    return all(event.get("triggering_issue_id") in issues for event in row.get("quality_repair_events") or [])


def _post_repair_validation_present(row: dict[str, Any]) -> bool:
    repairs = row.get("quality_repair_events") or []
    validation = row.get("post_repair_quality_validation")
    return not repairs or (isinstance(validation, dict) and validation.get("validated") is True)


def _post_repair_final_pass(row: dict[str, Any]) -> bool:
    repairs = row.get("quality_repair_events") or []
    if not repairs:
        return True
    validation = row.get("post_repair_quality_validation") or {}
    return validation.get("final_outfit_quality_passed") is True and not _issues(row)


def _repair_diff(row: dict[str, Any]) -> bool:
    final_ids = _final_item_ids(row)
    for event in row.get("quality_repair_events") or []:
        if event.get("after_item_ids") != final_ids:
            return False
        if set(event.get("removed_item_ids") or []) & set(final_ids):
            return False
        if not set(event.get("added_item_ids") or []) <= set(final_ids):
            return False
    return True


def _explanation_matches(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "explanation_mismatch")


def _claim_trace(row: dict[str, Any]) -> bool:
    trace_refs = set((_card(row).get("claim_refs") or [])) | set((row.get("quality_trace") or {}).get("card_claim_refs") or [])
    why_refs = {item.get("claim_ref") for item in _card(row).get("why_this_works", []) if item.get("claim_ref")}
    swap_refs = {item.get("claim_ref") for item in _card(row).get("swap_options", []) if item.get("claim_ref")}
    return (why_refs | swap_refs) <= trace_refs


def _no_removed_item_explained(row: dict[str, Any]) -> bool:
    removed = set(_card(row).get("removed_candidate_item_ids") or [])
    mentioned = set(_card(row).get("mentioned_item_ids") or [])
    why_items = {item_id for why in _card(row).get("why_this_works", []) for item_id in why.get("item_ids", [])}
    return not (removed & (mentioned | why_items))


def _exact_repeat(row: dict[str, Any]) -> bool:
    return not _has_issue(row, "repetition_without_reason")


def _repeat_reason(row: dict[str, Any]) -> bool:
    recent = {tuple(item.get("item_ids") or []) for item in _history(row).get("recent_outfits", [])}
    final = tuple(_final_item_ids(row))
    return final not in recent or bool(_card(row).get("repeat_allowed_reason"))


def _history_trace(row: dict[str, Any]) -> bool:
    return bool((row.get("quality_trace") or {}).get("recent_outfit_history"))


def _memory_overfit(row: dict[str, Any]) -> bool:
    return _task(row).get("memory_preference_applied_too_hard") is not True and not any(
        issue.get("quality_issue_id") == "qi_memory_overfit" for issue in _issues(row)
    )


def _swap_context_fit(row: dict[str, Any]) -> bool:
    return all("context_mismatch" not in _swap_violations(row, option) for option in _visible_swaps(row))


def _swap_weather_fit(row: dict[str, Any]) -> bool:
    return all("weather_mismatch" not in _swap_violations(row, option) for option in _visible_swaps(row))


def _swap_temperature_fit(row: dict[str, Any]) -> bool:
    return all("temperature_mismatch" not in _swap_violations(row, option) for option in _visible_swaps(row))


def _swap_formality_fit(row: dict[str, Any]) -> bool:
    return all("formality_mismatch" not in _swap_violations(row, option) and "context_mismatch" not in _swap_violations(row, option) for option in _visible_swaps(row))


def _swap_claim_trace(row: dict[str, Any]) -> bool:
    return all("claim_trace_missing" not in _swap_violations(row, option) for option in _visible_swaps(row))


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "daily_outfit_quality_artifact_schema_valid_rate": _schema_valid,
    "daily_outfit_card_schema_valid_rate": _card_schema_valid,
    "quality_outfit_uses_only_closet_items_rate": _outfit_closet,
    "quality_swap_options_grounded_rate": _swap_grounded,
    "card_text_no_hallucinated_item_rate": _card_text_no_hallucinated,
    "outfit_required_categories_present_rate": _required_categories,
    "closet_insufficiency_disclosed_rate": _insufficiency_disclosed,
    "occasion_fit_pass_rate": _occasion_fit,
    "weather_fit_pass_rate": _weather_fit,
    "weather_issue_repaired_or_disclosed_rate": _weather_repaired_or_disclosed,
    "formality_target_alignment_rate": _formality_fit,
    "quality_memory_boundary_violation_free_rate": _memory_boundary,
    "quality_residual_boundary_respected_rate": _residual_boundary,
    "misuse_correction_quality_hygiene_rate": _misuse_correction_hygiene,
    "style_semantic_conflict_free_rate": _style_conflict,
    "quality_issue_detection_rate": _quality_issue_detection,
    "quality_repair_has_triggering_issue_ref_rate": _repair_trigger_refs,
    "post_repair_quality_validation_present_rate": _post_repair_validation_present,
    "post_repair_final_quality_pass_rate": _post_repair_final_pass,
    "repair_result_matches_final_outfit_diff_rate": _repair_diff,
    "card_explanation_matches_final_outfit_rate": _explanation_matches,
    "card_quality_claim_trace_coverage_rate": _claim_trace,
    "card_does_not_explain_removed_candidate_item_rate": _no_removed_item_explained,
    "quality_exact_recent_outfit_not_repeated_without_reason_rate": _exact_repeat,
    "quality_repeat_allowed_reason_present_rate": _repeat_reason,
    "recent_outfit_history_in_quality_trace_rate": _history_trace,
    "memory_personalization_does_not_break_context_fit_rate": _memory_overfit,
    "swap_options_context_fit_rate": _swap_context_fit,
    "swap_options_weather_fit_rate": _swap_weather_fit,
    "swap_options_temperature_fit_rate": _swap_temperature_fit,
    "swap_options_formality_fit_rate": _swap_formality_fit,
    "swap_option_claim_trace_coverage_rate": _swap_claim_trace,
}


def _case_failures(row: dict[str, Any]) -> list[str]:
    return [cid for cid, fn in CHECKS.items() if not fn(row)]


def _aggregate(rows: list[dict[str, Any]], suite_mode: str) -> dict[str, Any]:
    checks = []
    for cid, fn in CHECKS.items():
        passed = sum(1 for row in rows if fn(row))
        value = _rate(passed, len(rows))
        checks.append({
            "check_id": cid,
            "value": value,
            "threshold": THRESHOLDS[cid],
            "passed": value >= THRESHOLDS[cid],
            "numerator": passed,
            "denominator": len(rows),
        })

    case_results = []
    for row in rows:
        failed = _case_failures(row)
        case_results.append({
            "case_id": row.get("case_id"),
            "scenario": row.get("scenario"),
            "is_injected_defect": row.get("is_injected_defect") is True,
            "defect_type": row.get("defect_type"),
            "failed_check_ids": failed,
            "passed": not failed,
        })

    unexpected_clean = [r for r in case_results if not r["is_injected_defect"] and r["failed_check_ids"]]
    unexpected_injected_passes = [r for r in case_results if r["is_injected_defect"] and not r["failed_check_ids"]]
    detected_defects = []
    for result in case_results:
        defect_type = result.get("defect_type")
        if not defect_type:
            continue
        expected = EXPECTED_DEFECTS.get(defect_type, [])
        failed = result.get("failed_check_ids") or []
        detected = bool(set(expected) & set(failed)) if expected else bool(failed)
        detected_defects.append({
            "case_id": result.get("case_id"),
            "defect_type": defect_type,
            "expected_failure": True,
            "actual_failure": bool(failed),
            "detected": detected,
            "failed_check_ids": failed,
            "expected_failed_check_ids": expected,
            "failure_reason": f"Detected seeded defect: {defect_type}",
            "raw_artifact_ref": f"per_case/{result.get('case_id')}.json",
        })

    failed_gates = [c["check_id"] for c in checks if not c["passed"]]
    clean_pass = not failed_gates and not unexpected_clean
    injected_pass = bool(detected_defects) and all(d["detected"] for d in detected_defects) and not unexpected_clean and not unexpected_injected_passes
    if suite_mode == "clean_acceptance":
        verdicts = {
            "clean_acceptance_verdict": "pass" if clean_pass else "fail",
            "mixed_strict_verdict": "not_applicable",
            "injected_defect_detection_verdict": "not_applicable",
            "release_candidate_verdict": "pass_candidate" if clean_pass else "fail",
        }
    else:
        verdicts = {
            "clean_acceptance_verdict": "not_applicable",
            "mixed_strict_verdict": "fail" if failed_gates else "pass",
            "injected_defect_detection_verdict": "pass" if injected_pass else "fail",
            "release_candidate_verdict": "not_applicable",
        }

    return {
        "benchmark_id": BENCHMARK_ID,
        "schema_version": QUALITY_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "suite_summary": {
            "suite_mode": suite_mode,
            "total_cases": len(rows),
            "clean_cases": sum(1 for row in rows if not row.get("is_injected_defect")),
            "injected_cases": sum(1 for row in rows if row.get("is_injected_defect")),
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "failed_checks": sum(1 for c in checks if not c["passed"]),
        },
        "verdicts": verdicts,
        "checks": checks,
        "case_results": case_results,
        "detected_defects": detected_defects,
        "unexpected_clean_case_failures": unexpected_clean,
        "unexpected_injected_passes": unexpected_injected_passes,
        "interpretation": "Mixed strict suite is expected to fail when injected defects are present and detected." if suite_mode == "mixed_strict_with_injected" else "Clean acceptance suite is used for release acceptance.",
    }


def _write_md(report: dict[str, Any], path: str) -> None:
    summary = report["suite_summary"]
    verdicts = report["verdicts"]
    lines = [
        "# v1.29.6 Daily Outfit Quality Guardrails Report",
        "",
        f"- suite_mode: `{summary['suite_mode']}`",
        f"- cases: `{summary['total_cases']}`",
        f"- checks: `{summary['passed_checks']}/{summary['total_checks']}` PASS",
        f"- clean_acceptance_verdict: `{verdicts.get('clean_acceptance_verdict')}`",
        f"- mixed_strict_verdict: `{verdicts.get('mixed_strict_verdict')}`",
        f"- injected_defect_detection_verdict: `{verdicts.get('injected_defect_detection_verdict')}`",
        f"- release_candidate_verdict: `{verdicts.get('release_candidate_verdict')}`",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        lines.append(f"- `{check['check_id']}`: {check['value']} ({'PASS' if check['passed'] else 'FAIL'})")
    defects = report.get("detected_defects") or []
    if defects:
        lines.extend(["", "## Injected Defects"])
        for defect in defects:
            lines.append(f"- `{defect['case_id']}` `{defect['defect_type']}`: {'detected' if defect['detected'] else 'missed'}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", required=True, choices=["clean_acceptance", "mixed_strict_with_injected"])
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    rows = _load_raw_dir(args.raw_dir)
    report = _aggregate(rows, args.suite_mode)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _write_md(report, args.out_md)
    print(json.dumps(report["suite_summary"], indent=2))


if __name__ == "__main__":
    main()
