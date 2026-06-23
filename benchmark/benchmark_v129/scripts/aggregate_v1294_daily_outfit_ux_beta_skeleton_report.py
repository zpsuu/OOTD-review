"""Aggregate v1.29.4 Daily Outfit UX Beta Skeleton reports."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable


BENCHMARK_ID = "v1.29.4.daily_outfit_ux_beta_skeleton"

THRESHOLDS = {
    "daily_outfit_card_schema_valid_rate": 1.0,
    "outfit_uses_only_closet_items_rate": 1.0,
    "swap_options_grounded_in_closet_rate": 1.0,
    "daily_card_claim_trace_coverage_rate": 1.0,
    "daily_card_claim_refs_subset_of_consumed_memory_rate": 1.0,
    "daily_card_no_blocked_or_excluded_memory_claim_rate": 1.0,
    "final_outfit_boundary_violation_free_rate": 1.0,
    "post_repair_validation_present_rate": 1.0,
    "repair_has_triggering_memory_ref_rate": 1.0,
    "current_exception_not_globalized_rate": 1.0,
    "remember_long_term_routes_to_write_gate_rate": 1.0,
    "do_not_remember_no_production_write_rate": 1.0,
    "this_time_only_no_global_write_rate": 1.0,
    "targeted_confirmed_memory_changes_second_round_rate": 1.0,
    "do_not_remember_second_round_unchanged_rate": 1.0,
    "this_time_only_not_persisted_next_task_rate": 1.0,
    "second_round_visible_card_changed_when_claimed_rate": 1.0,
    "second_round_changed_item_ids_match_card_diff_rate": 1.0,
    "second_round_applied_memory_consumed_rate": 1.0,
    "second_round_change_explained_in_card_rate": 1.0,
}

EXPECTED_DEFECTS = {
    "outfit_uses_non_closet_item": {
        "expected_failed_checks": ["outfit_uses_only_closet_items_rate"],
        "failure_reason": "Final outfit contains item_id not present in closet fixture.",
    },
    "card_claims_unconsumed_memory": {
        "expected_failed_checks": ["daily_card_claim_refs_subset_of_consumed_memory_rate"],
        "failure_reason": "Daily Outfit Card cites memory that was not consumed or current-task evidence.",
    },
    "current_exception_globalized": {
        "expected_failed_checks": ["current_exception_not_globalized_rate"],
        "failure_reason": "Current-task exception creates or defaults to global preference.",
    },
    "final_outfit_still_violates_boundary": {
        "expected_failed_checks": ["final_outfit_boundary_violation_free_rate"],
        "failure_reason": "Final outfit still violates an active negative boundary.",
    },
    "repair_without_triggering_memory_ref": {
        "expected_failed_checks": ["repair_has_triggering_memory_ref_rate"],
        "failure_reason": "Repair event lacks triggering memory ref.",
    },
    "do_not_remember_still_changes_second_round": {
        "expected_failed_checks": ["do_not_remember_second_round_unchanged_rate"],
        "failure_reason": "Rejected memory changes second-round recommendation.",
    },
    "remember_long_term_bypasses_write_gate": {
        "expected_failed_checks": ["remember_long_term_routes_to_write_gate_rate"],
        "failure_reason": "Remember-long-term action bypasses ProductionMemoryWriteGate.",
    },
    "second_round_unchanged_after_confirmed_memory": {
        "expected_failed_checks": [
            "second_round_visible_card_changed_when_claimed_rate",
            "second_round_changed_item_ids_match_card_diff_rate",
        ],
        "failure_reason": "Second-round recommendation claims changed, but visible Daily Outfit Card items did not change.",
    },
    "response_mentions_blocked_memory": {
        "expected_failed_checks": ["daily_card_no_blocked_or_excluded_memory_claim_rate"],
        "failure_reason": "Card cites blocked, review-required, shadow-only, or excluded memory.",
    },
    "hallucinated_swap_option": {
        "expected_failed_checks": ["swap_options_grounded_in_closet_rate"],
        "failure_reason": "Swap option contains item_id not present in closet fixture.",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rate(n: int, d: int) -> float:
    return round(n / d, 4) if d else 1.0


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


def _trace(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("daily_outfit_trace") or {}


def _closet_ids(row: dict[str, Any]) -> set[str]:
    return {
        item.get("item_id")
        for item in (row.get("closet_fixture_snapshot") or {}).get("closet_items", [])
        if item.get("item_id")
    }


def _card_claim_refs(row: dict[str, Any]) -> list[str]:
    refs = [item.get("claim_ref") for item in _card(row).get("why_this_works", []) if item.get("claim_ref")]
    refs += [item.get("claim_ref") for item in _card(row).get("swap_options", []) if item.get("claim_ref")]
    for block in _card(row).get("memory_ux_blocks", []) or []:
        refs += block.get("user_visible_claim_refs") or []
        if block.get("claim_ref"):
            refs.append(block["claim_ref"])
    for event in row.get("memory_ux_events") or []:
        refs += event.get("user_visible_claim_refs") or []
        for claim in event.get("user_visible_memory_claims") or []:
            refs += claim.get("trace_refs") or []
    return [ref for ref in refs if ref]


def _extract_visible_item_ids(card: dict[str, Any] | None) -> list[str]:
    if not card:
        return []
    items = card.get("outfit_items") or card.get("outfit", {}).get("items") or []
    ids = []
    for item in items:
        if isinstance(item, dict):
            item_id = item.get("item_id") or item.get("closet_item_id")
        else:
            item_id = item
        if item_id:
            ids.append(item_id)
    return ids


def _compute_card_diff(first_ids: list[str], second_ids: list[str]) -> dict[str, Any]:
    removed = [item_id for item_id in first_ids if item_id not in second_ids]
    added = [item_id for item_id in second_ids if item_id not in first_ids]
    return {
        "changed": first_ids != second_ids,
        "removed_item_ids": removed,
        "added_item_ids": added,
        "changed_item_ids": removed + added,
    }


def _second_round_effect(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("second_round_effect") or (row.get("second_round_recommendation") or {}).get("second_round_effect") or {}


def _second_round_trace(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("second_round_trace") or (row.get("second_round_recommendation") or {}).get("second_round_trace") or {}


def _targeted_second_round_effect(row: dict[str, Any]) -> bool:
    return _second_round_effect(row).get("effect") in {
        "changed_by_confirmed_memory",
        "changed_by_corrected_interpretation",
    }


def _second_round_first_ids(row: dict[str, Any]) -> list[str]:
    effect = _second_round_effect(row)
    return effect.get("first_round_visible_item_ids") or _extract_visible_item_ids(_card(row))


def _second_round_second_ids(row: dict[str, Any]) -> list[str]:
    effect = _second_round_effect(row)
    return effect.get("second_round_visible_item_ids") or _extract_visible_item_ids(row.get("second_round_outfit_card") or {})


def _second_round_card_claim_refs(row: dict[str, Any]) -> set[str]:
    card = row.get("second_round_outfit_card") or {}
    refs = {item.get("claim_ref") for item in card.get("why_this_works", []) if item.get("claim_ref")}
    refs |= {item.get("claim_ref") for item in card.get("memory_ux_blocks", []) if isinstance(item, dict) and item.get("claim_ref")}
    trace = _second_round_trace(row)
    refs |= set(trace.get("response_claim_refs") or [])
    refs |= set(trace.get("user_visible_memory_claim_refs") or [])
    return {ref for ref in refs if ref}


def _allowed_claim_refs(row: dict[str, Any]) -> set[str]:
    trace = _trace(row)
    return set(trace.get("consumed_memory_ids") or []) | set(trace.get("current_task_evidence_ids") or [])


def _disallowed_claim_refs(row: dict[str, Any]) -> set[str]:
    trace = _trace(row)
    return set(trace.get("excluded_memory_ids") or []) | set(trace.get("blocked_memory_ids") or []) | set(
        trace.get("review_required_memory_ids") or []
    ) | set(trace.get("shadow_only_memory_ids") or [])


def _schema_ok(row: dict[str, Any]) -> bool:
    required = {"card_id", "headline", "direction", "outfit_items", "why_this_works", "feedback_actions"}
    card = _card(row)
    return required <= set(card) and bool(card.get("outfit_items")) and bool(card.get("feedback_actions"))


def _outfit_grounded_ok(row: dict[str, Any]) -> bool:
    ids = _closet_ids(row)
    return all(item.get("item_id") in ids for item in _card(row).get("outfit_items", []))


def _swap_grounded_ok(row: dict[str, Any]) -> bool:
    ids = _closet_ids(row)
    return all(item.get("item_id") in ids for item in _card(row).get("swap_options", []))


def _claim_trace_coverage_ok(row: dict[str, Any]) -> bool:
    refs = set(_card_claim_refs(row))
    trace_refs = set(_trace(row).get("response_claim_refs") or []) | set(_trace(row).get("user_visible_memory_claim_refs") or []) | _allowed_claim_refs(row)
    return bool(refs) and refs <= trace_refs


def _claim_subset_ok(row: dict[str, Any]) -> bool:
    return set(_card_claim_refs(row)) <= _allowed_claim_refs(row)


def _no_blocked_excluded_claim_ok(row: dict[str, Any]) -> bool:
    return not (set(_card_claim_refs(row)) & _disallowed_claim_refs(row))


def _final_boundary_ok(row: dict[str, Any]) -> bool:
    repair = row.get("repair_report") or {}
    validation = repair.get("post_repair_validation")
    if row.get("final_outfit_boundary_concepts"):
        return False
    if validation:
        return validation.get("remaining_violations") == [] and validation.get("final_outfit_violation_free") is True
    return True


def _post_repair_validation_ok(row: dict[str, Any]) -> bool:
    critic = row.get("critic_report") or {}
    repair = row.get("repair_report") or {}
    if critic.get("violations") or repair.get("repair_events"):
        return bool(repair.get("post_repair_validation"))
    return True


def _repair_trigger_ok(row: dict[str, Any]) -> bool:
    repair = row.get("repair_report") or {}
    events = repair.get("repair_events") or []
    if not events:
        return True
    if not repair.get("triggering_memory_ids"):
        return False
    return all(event.get("triggering_memory_id") for event in events)


def _current_exception_ok(row: dict[str, Any]) -> bool:
    exceptions = (row.get("task_memory_packet") or {}).get("current_task_exceptions") or []
    if not exceptions:
        return True
    old_ids = set((row.get("daily_outfit_trace") or {}).get("overridden_memory_ids") or [])
    return (
        row.get("current_task_exception_globalized") is False
        and not row.get("active_global_positive_preferences_created")
        and all(exc.get("scope") == "this_task_only" for exc in exceptions)
        and all(exc.get("creates_global_preference") is False for exc in exceptions)
        and all(exc.get("old_memory_preserved") is True for exc in exceptions)
        and bool(old_ids)
        and all(exc.get("residual_boundaries") for exc in exceptions)
    )


def _remember_route_ok(row: dict[str, Any]) -> bool:
    for action in row.get("user_memory_actions") or []:
        if action.get("action_type") == "remember_long_term":
            decisions = row.get("write_gate_decisions") or []
            return (
                action.get("routes_to_write_gate") is True
                and bool(action.get("write_gate_decision_id"))
                and any(d.get("write_gate_decision_id") == action.get("write_gate_decision_id") for d in decisions)
                and action.get("write_gate_decision_status") not in {"bypassed_write", "not_applicable"}
            )
    return True


def _do_not_remember_ok(row: dict[str, Any]) -> bool:
    for action in row.get("user_memory_actions") or []:
        if action.get("action_type") == "do_not_remember":
            return (
                action.get("production_store_write_attempted") is False
                and action.get("production_store_write_executed") is False
                and action.get("creates_global_memory") is False
                and action.get("proposal_status") == "rejected"
            )
    return True


def _this_time_only_ok(row: dict[str, Any]) -> bool:
    for action in row.get("user_memory_actions") or []:
        if action.get("action_type") == "this_time_only":
            return (
                action.get("production_store_write_attempted") is False
                and action.get("production_store_write_executed") is False
                and action.get("creates_global_memory") is False
            )
    return True


def _confirmed_second_round_ok(row: dict[str, Any]) -> bool:
    actions = row.get("user_memory_actions") or []
    if not any(a.get("action_type") == "remember_long_term" for a in actions):
        return True
    second = row.get("second_round_recommendation") or {}
    return (
        second.get("effect") == "changed_by_confirmed_memory"
        and second.get("changed_from_first_round") is True
        and bool(second.get("trace_refs"))
    )


def _do_not_second_round_ok(row: dict[str, Any]) -> bool:
    actions = row.get("user_memory_actions") or []
    if not any(a.get("action_type") == "do_not_remember" for a in actions):
        return True
    second = row.get("second_round_recommendation") or {}
    future_refs = set((_trace(row).get("second_round_claim_refs") or []))
    rejected = {rid for action in actions for rid in action.get("rejected_memory_ux_event_ids", [])}
    return (
        second.get("effect") in {"unchanged_by_rejected_memory", None}
        and second.get("changed_from_first_round") is not True
        and not (future_refs & rejected)
    )


def _this_time_second_round_ok(row: dict[str, Any]) -> bool:
    actions = row.get("user_memory_actions") or []
    if not any(a.get("action_type") == "this_time_only" for a in actions):
        return True
    second = row.get("second_round_recommendation") or {}
    return second.get("effect") == "current_task_only_not_persisted" and second.get("changed_from_first_round") is False


def _second_round_visible_changed_ok(row: dict[str, Any]) -> bool:
    if not _targeted_second_round_effect(row):
        return True
    return _second_round_first_ids(row) != _second_round_second_ids(row)


def _second_round_changed_ids_match_diff_ok(row: dict[str, Any]) -> bool:
    if not _targeted_second_round_effect(row):
        return True
    effect = _second_round_effect(row)
    diff = _compute_card_diff(_second_round_first_ids(row), _second_round_second_ids(row))
    return (
        effect.get("removed_item_ids") == diff["removed_item_ids"]
        and effect.get("added_item_ids") == diff["added_item_ids"]
        and effect.get("changed_item_ids") == diff["changed_item_ids"]
        and effect.get("visible_card_diff_validated") is True
        and effect.get("changed_item_ids_match_visible_card_diff") is True
    )


def _second_round_applied_memory_consumed_ok(row: dict[str, Any]) -> bool:
    if not _targeted_second_round_effect(row):
        return True
    effect = _second_round_effect(row)
    applied = effect.get("applied_memory_id")
    second = row.get("second_round_recommendation") or {}
    consumed = set(_second_round_trace(row).get("consumed_memory_ids") or [])
    consumed |= set((second.get("task_memory_packet") or {}).get("consumed_memory_ids") or [])
    return bool(applied) and applied in consumed


def _second_round_change_explained_ok(row: dict[str, Any]) -> bool:
    if not _targeted_second_round_effect(row):
        return True
    applied = _second_round_effect(row).get("applied_memory_id")
    return bool(applied) and applied in _second_round_card_claim_refs(row)


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "daily_outfit_card_schema_valid_rate": _schema_ok,
    "outfit_uses_only_closet_items_rate": _outfit_grounded_ok,
    "swap_options_grounded_in_closet_rate": _swap_grounded_ok,
    "daily_card_claim_trace_coverage_rate": _claim_trace_coverage_ok,
    "daily_card_claim_refs_subset_of_consumed_memory_rate": _claim_subset_ok,
    "daily_card_no_blocked_or_excluded_memory_claim_rate": _no_blocked_excluded_claim_ok,
    "final_outfit_boundary_violation_free_rate": _final_boundary_ok,
    "post_repair_validation_present_rate": _post_repair_validation_ok,
    "repair_has_triggering_memory_ref_rate": _repair_trigger_ok,
    "current_exception_not_globalized_rate": _current_exception_ok,
    "remember_long_term_routes_to_write_gate_rate": _remember_route_ok,
    "do_not_remember_no_production_write_rate": _do_not_remember_ok,
    "this_time_only_no_global_write_rate": _this_time_only_ok,
    "targeted_confirmed_memory_changes_second_round_rate": _confirmed_second_round_ok,
    "do_not_remember_second_round_unchanged_rate": _do_not_second_round_ok,
    "this_time_only_not_persisted_next_task_rate": _this_time_second_round_ok,
    "second_round_visible_card_changed_when_claimed_rate": _second_round_visible_changed_ok,
    "second_round_changed_item_ids_match_card_diff_rate": _second_round_changed_ids_match_diff_ok,
    "second_round_applied_memory_consumed_rate": _second_round_applied_memory_consumed_ok,
    "second_round_change_explained_in_card_rate": _second_round_change_explained_ok,
}


def _case_failures(row: dict[str, Any]) -> list[str]:
    return [cid for cid, fn in CHECKS.items() if not fn(row)]


def _aggregate(rows: list[dict[str, Any]], suite_mode: str) -> dict[str, Any]:
    checks = []
    for cid, fn in CHECKS.items():
        passed_count = sum(1 for row in rows if fn(row))
        value = _rate(passed_count, len(rows))
        checks.append(
            {
                "check_id": cid,
                "value": value,
                "threshold": THRESHOLDS[cid],
                "passed": value >= THRESHOLDS[cid],
                "numerator": passed_count,
                "denominator": len(rows),
            }
        )
    failed_gates = [c["check_id"] for c in checks if not c["passed"]]

    case_results = []
    for row in rows:
        failed = _case_failures(row)
        case_results.append(
            {
                "case_id": row.get("case_id"),
                "scenario": row.get("scenario"),
                "is_injected_defect": row.get("is_injected_defect") is True,
                "defect_type": row.get("defect_type"),
                "passed": not failed,
                "failed_check_ids": failed,
                "raw_artifact_ref": f"per_case/{row.get('case_id')}.json",
            }
        )

    unexpected_clean = [r for r in case_results if not r["is_injected_defect"] and r["failed_check_ids"]]
    unexpected_injected_passes = [r for r in case_results if r["is_injected_defect"] and not r["failed_check_ids"]]
    detected_defects = []
    for result in case_results:
        defect_type = result.get("defect_type")
        if not defect_type:
            continue
        expected = EXPECTED_DEFECTS.get(defect_type, {})
        expected_checks = expected.get("expected_failed_checks") or []
        failed = result.get("failed_check_ids") or []
        detected = bool(set(expected_checks) & set(failed))
        detected_defects.append(
            {
                "case_id": result.get("case_id"),
                "defect_type": defect_type,
                "expected_failure": True,
                "actual_failure": bool(failed),
                "detected": detected,
                "failed_check_ids": failed,
                "expected_failed_check_ids": expected_checks,
                "failure_reason": expected.get("failure_reason"),
                "raw_artifact_ref": result.get("raw_artifact_ref"),
            }
        )

    clean_pass = not failed_gates and not unexpected_clean
    injected_pass = bool(detected_defects) and all(d.get("detected") for d in detected_defects) and not unexpected_clean and not unexpected_injected_passes
    if suite_mode == "clean_acceptance":
        verdicts = {
            "clean_acceptance_verdict": "pass" if clean_pass else "fail",
            "mixed_strict_verdict": "not_applicable",
            "injected_defect_detection_verdict": "not_applicable",
            "release_candidate_verdict": "pass_candidate" if clean_pass else "fail",
        }
    elif suite_mode == "mixed_strict_with_injected":
        verdicts = {
            "clean_acceptance_verdict": "not_applicable",
            "mixed_strict_verdict": "fail" if failed_gates else "pass",
            "injected_defect_detection_verdict": "pass" if injected_pass else "fail",
            "release_candidate_verdict": "not_applicable",
        }
    else:
        verdicts = {
            "clean_acceptance_verdict": "not_applicable",
            "mixed_strict_verdict": "not_applicable",
            "injected_defect_detection_verdict": "not_applicable",
            "release_candidate_verdict": "not_applicable",
        }

    return {
        "benchmark_id": BENCHMARK_ID,
        "artifact_schema_version": "v1.29.4",
        "generated_at": _now_iso(),
        "raw_first": True,
        "suite_summary": {
            "suite_mode": suite_mode,
            "total_cases": len(rows),
            "clean_cases": sum(1 for row in rows if not row.get("is_injected_defect")),
            "injected_cases": sum(1 for row in rows if row.get("is_injected_defect")),
            "total_checks": len(checks),
            "passed_checks": sum(1 for check in checks if check["passed"]),
            "failed_checks": sum(1 for check in checks if not check["passed"]),
        },
        "verdicts": verdicts,
        "checks": checks,
        "failed_gates": failed_gates,
        "case_results": case_results,
        "detected_defects": detected_defects,
        "unexpected_clean_case_failures": unexpected_clean,
        "unexpected_injected_passes": unexpected_injected_passes,
    }


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_md(path: str, report: dict[str, Any]) -> None:
    summary = report.get("suite_summary") or {}
    verdicts = report.get("verdicts") or {}
    lines = [
        "# v1.29.4 Daily Outfit UX Beta Skeleton Report",
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
        "## Checks",
        "",
    ]
    for check in report.get("checks") or []:
        lines.append(f"- `{check.get('check_id')}`: {check.get('value')} ({'PASS' if check.get('passed') else 'FAIL'})")
    lines.extend(["", "## Detected Defects", ""])
    defects = report.get("detected_defects") or []
    if defects:
        for defect in defects:
            lines.append(f"- `{defect.get('case_id')}` `{defect.get('defect_type')}`: {'detected' if defect.get('detected') else 'missed'}")
    else:
        lines.append("- None")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", required=True, choices=["clean_acceptance", "mixed_strict_with_injected", "shadow_vision"])
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    rows = _load_raw_dir(args.raw_dir)
    report = _aggregate(rows, args.suite_mode)
    _write_json(args.out_json, report)
    _write_md(args.out_md, report)
    print(json.dumps(report["suite_summary"], indent=2))


if __name__ == "__main__":
    main()
