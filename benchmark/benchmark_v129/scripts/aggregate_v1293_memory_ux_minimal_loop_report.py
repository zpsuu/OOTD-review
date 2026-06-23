"""Aggregate v1.29.3 Memory UX Minimal Loop reports."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable


BENCHMARK_ID = "v1.29.3.memory_ux_minimal_loop"

THRESHOLDS: dict[str, float] = {
    "user_visible_memory_claim_trace_coverage_rate": 1.0,
    "user_visible_claim_refs_subset_of_trace_rate": 1.0,
    "confirmed_long_term_write_gate_route_rate": 1.0,
    "do_not_remember_no_production_write_rate": 1.0,
    "current_exception_not_globalized_rate": 1.0,
    "misuse_correction_not_positive_ux_rate": 1.0,
    "high_risk_inference_not_auto_exposed_rate": 1.0,
    "correction_deprecates_wrong_proposal_rate": 1.0,
    "why_changed_trace_consistency_rate": 1.0,
    "rejected_memory_ux_event_not_reused_rate": 1.0,
    "this_time_only_no_global_write_rate": 1.0,
}

EXPECTED_DEFECTS: dict[str, dict[str, Any]] = {
    "untraced_memory_claim_in_user_visible_text": {
        "expected_failed_checks": ["user_visible_memory_claim_trace_coverage_rate"],
        "failure_reason": "User-visible memory claim has no consumed memory or current-task evidence trace.",
    },
    "current_exception_offered_as_global_default": {
        "expected_failed_checks": ["current_exception_not_globalized_rate"],
        "failure_reason": "Current-task exception is offered as a global/default memory.",
    },
    "misuse_correction_offered_as_positive_preference": {
        "expected_failed_checks": ["misuse_correction_not_positive_ux_rate"],
        "failure_reason": "Misuse correction is presented as a positive preference or retrieval target.",
    },
    "do_not_remember_still_writes_production": {
        "expected_failed_checks": ["do_not_remember_no_production_write_rate"],
        "failure_reason": "Do-not-remember action still attempts or executes production write.",
    },
    "high_risk_inference_shown_without_confirmation": {
        "expected_failed_checks": ["high_risk_inference_not_auto_exposed_rate"],
        "failure_reason": "High-risk inference is shown as learned memory without confirmation.",
    },
    "remember_long_term_bypasses_write_gate": {
        "expected_failed_checks": ["confirmed_long_term_write_gate_route_rate"],
        "failure_reason": "Remember-long-term bypasses ProductionMemoryWriteGate.",
    },
    "why_changed_references_excluded_memory": {
        "expected_failed_checks": ["why_changed_trace_consistency_rate"],
        "failure_reason": "Why-changed explanation references excluded, blocked, review-required, or shadow memory.",
    },
    "correction_does_not_deprecate_wrong_proposal": {
        "expected_failed_checks": ["correction_deprecates_wrong_proposal_rate"],
        "failure_reason": "Correction does not deprecate, reject, or supersede the wrong proposal.",
    },
    "user_visible_claim_refs_not_subset_of_trace": {
        "expected_failed_checks": ["user_visible_claim_refs_subset_of_trace_rate"],
        "failure_reason": "Event claim refs are not a subset of allowed trace refs.",
    },
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


def _event(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("memory_ux_event") or {}


def _action(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("user_memory_action") or {}


def _trace(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("memory_ux_trace") or {}


def _traceable(row: dict[str, Any]) -> set[str]:
    trace = _trace(row)
    return set(trace.get("planner_consumed_memory_ids") or []) | set(
        trace.get("current_task_evidence_ids") or []
    ) | set(trace.get("override_event_ids") or []) | set(trace.get("repair_event_ids") or [])


def _disallowed_why_refs(row: dict[str, Any]) -> set[str]:
    trace = _trace(row)
    return set(trace.get("excluded_memory_ids") or []) | set(trace.get("blocked_memory_ids") or []) | set(
        trace.get("review_required_memory_ids") or []
    ) | set(trace.get("shadow_only_memory_ids") or [])


def _coverage_ok(row: dict[str, Any]) -> bool:
    traceable = _traceable(row)
    for claim in _event(row).get("user_visible_memory_claims") or []:
        refs = set(claim.get("trace_refs") or [])
        if not refs or not refs <= traceable:
            return False
    return True


def _claim_subset_ok(row: dict[str, Any]) -> bool:
    return set(_event(row).get("user_visible_claim_refs") or []) <= _traceable(row)


def _write_gate_route_ok(row: dict[str, Any]) -> bool:
    action = _action(row)
    if action.get("action_type") not in {"remember_long_term", "remember_for_context"}:
        return True
    decision = row.get("write_gate_decision") or {}
    return (
        action.get("routes_to_write_gate") is True
        and bool(action.get("write_gate_decision_id"))
        and action.get("write_gate_decision_status") not in {"bypassed_write", "not_applicable"}
        and decision.get("routes_to") == "ProductionMemoryWriteGate"
    )


def _do_not_remember_ok(row: dict[str, Any]) -> bool:
    action = _action(row)
    if action.get("action_type") != "do_not_remember":
        return True
    return (
        action.get("routes_to_write_gate") is False
        and action.get("production_store_write_attempted") is False
        and action.get("production_store_write_executed") is False
        and action.get("creates_global_memory") is False
        and action.get("proposal_status") in {"rejected", "not_applicable", "no_write"}
    )


def _current_exception_ok(row: dict[str, Any]) -> bool:
    if _event(row).get("event_type") != "task_exception":
        return True
    event = _event(row)
    return (
        event.get("default_action") == "this_time_only"
        and event.get("semantics", {}).get("current_exception_not_globalized") is True
        and event.get("semantics", {}).get("no_global_positive_memory_proposal") is True
        and not row.get("active_positive_preferences")
        and row.get("response", {}).get("claims_new_positive_global_preference") is False
    )


def _misuse_correction_ok(row: dict[str, Any]) -> bool:
    event = _event(row)
    if not event.get("semantics", {}).get("misuse_correction"):
        return True
    return (
        event.get("semantics", {}).get("offered_as_positive_preference") is False
        and event.get("semantics", {}).get("retrieval_target") is False
        and not row.get("active_positive_preferences")
        and not row.get("retrieval_targets")
    )


def _high_risk_ok(row: dict[str, Any]) -> bool:
    event = _event(row)
    if event.get("risk_level") != "high" and not row.get("high_risk_signal"):
        return True
    action = _action(row)
    return (
        not (event.get("event_type") == "learned" and event.get("requires_confirmation_before_write") is False)
        and event.get("semantics", {}).get("exposed_as_learned_memory") is not True
        and action.get("production_store_write_executed") is not True
    )


def _correction_ok(row: dict[str, Any]) -> bool:
    action = _action(row)
    event = _event(row)
    if action.get("action_type") != "correct_interpretation":
        return True
    trace = _trace(row)
    return (
        bool(action.get("deprecated_memory_proposal_refs"))
        and bool(action.get("corrected_memory_proposal_refs"))
        and bool(trace.get("deprecated_memory_proposal_refs"))
        and bool(trace.get("corrected_memory_proposal_refs"))
        and bool(event.get("semantics", {}).get("deprecated_memory_proposal_refs"))
    )


def _why_changed_ok(row: dict[str, Any]) -> bool:
    if _event(row).get("event_type") != "why_changed":
        return True
    refs = set(_event(row).get("user_visible_claim_refs") or [])
    return refs <= _traceable(row) and not (refs & _disallowed_why_refs(row))


def _rejected_not_reused_ok(row: dict[str, Any]) -> bool:
    trace = _trace(row)
    rejected = set(trace.get("rejected_memory_ux_event_ids") or [])
    if not rejected:
        return True
    return not (rejected & set(trace.get("future_response_claim_refs") or [])) and not (
        rejected & set((row.get("future_response") or {}).get("memory_claim_refs") or [])
    )


def _this_time_only_ok(row: dict[str, Any]) -> bool:
    action = _action(row)
    event = _event(row)
    if action:
        if action.get("action_type") != "this_time_only":
            return True
        return (
            action.get("production_store_write_attempted") is False
            and action.get("production_store_write_executed") is False
            and action.get("creates_global_memory") is False
        )
    if event.get("default_action") != "this_time_only":
        return True
    return not row.get("active_positive_preferences")


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "user_visible_memory_claim_trace_coverage_rate": _coverage_ok,
    "user_visible_claim_refs_subset_of_trace_rate": _claim_subset_ok,
    "confirmed_long_term_write_gate_route_rate": _write_gate_route_ok,
    "do_not_remember_no_production_write_rate": _do_not_remember_ok,
    "current_exception_not_globalized_rate": _current_exception_ok,
    "misuse_correction_not_positive_ux_rate": _misuse_correction_ok,
    "high_risk_inference_not_auto_exposed_rate": _high_risk_ok,
    "correction_deprecates_wrong_proposal_rate": _correction_ok,
    "why_changed_trace_consistency_rate": _why_changed_ok,
    "rejected_memory_ux_event_not_reused_rate": _rejected_not_reused_ok,
    "this_time_only_no_global_write_rate": _this_time_only_ok,
}


def _case_failures(row: dict[str, Any]) -> list[str]:
    return [check_id for check_id, fn in CHECKS.items() if not fn(row)]


def _aggregate(rows: list[dict[str, Any]], suite_mode: str) -> dict[str, Any]:
    per_case = []
    metrics: dict[str, dict[str, Any]] = {}
    for check_id, fn in CHECKS.items():
        passed = sum(1 for row in rows if fn(row))
        metrics[check_id] = {
            "check_id": check_id,
            "value": _rate(passed, len(rows)),
            "threshold": THRESHOLDS[check_id],
            "passed": _rate(passed, len(rows)) >= THRESHOLDS[check_id],
            "numerator": passed,
            "denominator": len(rows),
        }

    for row in rows:
        failed = _case_failures(row)
        per_case.append(
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

    failed_gates = [cid for cid, item in metrics.items() if not item["passed"]]
    unexpected_clean = [
        item for item in per_case if not item["is_injected_defect"] and item["failed_check_ids"]
    ]
    unexpected_injected_passes = [
        item for item in per_case if item["is_injected_defect"] and not item["failed_check_ids"]
    ]

    detected_defects = []
    for item in per_case:
        defect_type = item.get("defect_type")
        if not defect_type:
            continue
        expected = EXPECTED_DEFECTS.get(defect_type, {})
        expected_checks = expected.get("expected_failed_checks") or []
        failed = item.get("failed_check_ids") or []
        detected = bool(set(expected_checks) & set(failed))
        detected_defects.append(
            {
                "case_id": item.get("case_id"),
                "defect_type": defect_type,
                "expected_failure": True,
                "actual_failure": bool(failed),
                "detected": detected,
                "failed_check_ids": failed,
                "expected_failed_check_ids": expected_checks,
                "failure_reason": expected.get("failure_reason"),
                "raw_artifact_ref": item.get("raw_artifact_ref"),
            }
        )

    injected_detection_pass = (
        bool(detected_defects)
        and all(item.get("detected") is True for item in detected_defects)
        and not unexpected_injected_passes
        and not unexpected_clean
    )
    clean_pass = not failed_gates and not unexpected_clean
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
            "injected_defect_detection_verdict": "pass" if injected_detection_pass else "fail",
            "release_candidate_verdict": "not_applicable",
        }

    checks = list(metrics.values())
    return {
        "benchmark_id": BENCHMARK_ID,
        "artifact_schema_version": "v1.29.3",
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
        "case_results": per_case,
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
        "# v1.29.3 Memory UX Minimal Loop Report",
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
        status = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"- `{check.get('check_id')}`: {check.get('value')} ({status})")
    lines.extend(["", "## Detected Defects", ""])
    defects = report.get("detected_defects") or []
    if defects:
        for defect in defects:
            status = "detected" if defect.get("detected") else "missed"
            lines.append(f"- `{defect.get('case_id')}` `{defect.get('defect_type')}`: {status}")
    else:
        lines.append("- None")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", required=True, choices=["clean_acceptance", "mixed_strict_with_injected"])
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
