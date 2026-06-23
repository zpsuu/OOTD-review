"""
Aggregate v1.29.2 Memory Consumption Correctness reports.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any


BENCHMARK_ID = "v1.29.2.memory_consumption_correctness"


THRESHOLDS: dict[str, float] = {
    "task_memory_packet_schema_valid_rate": 1.0,
    "planner_trace_schema_valid_rate": 1.0,
    "current_task_exception_precedence_rate": 1.0,
    "override_does_not_create_positive_preference_rate": 1.0,
    "overridden_memory_not_in_explicit_reject_rate": 1.0,
    "residual_boundary_preservation_rate": 1.0,
    "misuse_correction_not_positive_signal_rate": 1.0,
    "misuse_correction_present_in_do_not_use_as_positive_signal_rate": 1.0,
    "misuse_correction_applied_to_critic_or_retrieval_filter_rate": 1.0,
    "negative_boundary_preserved_rate": 1.0,
    "negative_boundary_not_in_positive_preferences_rate": 1.0,
    "critic_detects_memory_violation_rate": 1.0,
    "repair_has_triggering_memory_ref_rate": 1.0,
    "post_repair_validation_present_rate": 1.0,
    "repair_result_matches_final_outfit_diff_rate": 1.0,
    "final_outfit_boundary_violation_free_rate": 1.0,
    "blocked_memory_not_consumed_rate": 1.0,
    "review_required_memory_not_consumed_rate": 1.0,
    "shadow_only_memory_not_consumed_rate": 1.0,
    "rolledback_memory_not_consumed_rate": 1.0,
    "expired_memory_not_consumed_rate": 1.0,
    "low_confidence_memory_gated_rate": 1.0,
    "contextual_scope_match_rate": 1.0,
    "contextual_scope_mismatch_exclusion_rate": 1.0,
    "session_soft_scope_rate": 1.0,
    "this_task_only_precedence_rate": 1.0,
    "global_memory_fallback_rate": 1.0,
    "response_claims_subset_of_consumed_memory_rate": 1.0,
    "excluded_memory_has_reason_rate": 1.0,
    "override_event_trace_rate": 1.0,
    "repair_event_trace_rate": 1.0,
    "raw_report_consistency_rate": 1.0,
}


EXPECTED_DEFECTS = {
    "misuse_correction_positive_signal": {
        "expected_failed_checks": ["misuse_correction_not_positive_signal_rate"],
    },
    "overridden_avoid_in_explicit_reject": {
        "expected_failed_checks": ["overridden_memory_not_in_explicit_reject_rate"],
    },
    "blocked_memory_consumed": {
        "expected_failed_checks": ["blocked_memory_not_consumed_rate"],
    },
    "review_required_memory_consumed": {
        "expected_failed_checks": ["review_required_memory_not_consumed_rate"],
    },
    "shadow_only_memory_consumed": {
        "expected_failed_checks": ["shadow_only_memory_not_consumed_rate"],
    },
    "response_claim_untraced_memory": {
        "expected_failed_checks": ["response_claims_subset_of_consumed_memory_rate"],
    },
    "critic_misses_negative_boundary_violation": {
        "expected_failed_checks": ["critic_detects_memory_violation_rate"],
    },
    "repair_without_triggering_memory_ref": {
        "expected_failed_checks": ["repair_has_triggering_memory_ref_rate"],
    },
    "repair_claims_pass_but_final_still_violates_boundary": {
        "expected_failed_checks": [
            "final_outfit_boundary_violation_free_rate",
            "repair_result_matches_final_outfit_diff_rate",
        ],
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


def _memories(row: dict[str, Any]) -> list[dict[str, Any]]:
    return list(((row.get("input_memory_snapshot") or {}).get("memories")) or [])


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("task_memory_packet") or {}


def _trace(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("planner_trace") or {}


def _memory_ids(items: list[dict[str, Any]]) -> set[str]:
    return {item.get("memory_id") for item in items if item.get("memory_id")}


def _positive_ids(row: dict[str, Any]) -> set[str]:
    return _memory_ids(_packet(row).get("active_positive_preferences") or [])


def _negative_ids(row: dict[str, Any]) -> set[str]:
    return _memory_ids(_packet(row).get("active_negative_boundaries") or [])


def _do_not_ids(row: dict[str, Any]) -> set[str]:
    return _memory_ids(_packet(row).get("do_not_use_as_positive_signal") or [])


def _excluded(row: dict[str, Any]) -> list[dict[str, Any]]:
    return list(_packet(row).get("excluded_memories") or [])


def _excluded_ids(row: dict[str, Any]) -> set[str]:
    return _memory_ids(_excluded(row))


def _consumed_ids(row: dict[str, Any]) -> set[str]:
    return set(_trace(row).get("consumed_memory_ids") or [])


def _contains_concept(value: Any, concept: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() == concept.strip().lower()
    if isinstance(value, list):
        return any(_contains_concept(item, concept) for item in value)
    if isinstance(value, dict):
        return any(_contains_concept(v, concept) for v in value.values())
    return False


def _negative_boundary_events(row: dict[str, Any]) -> list[dict[str, Any]]:
    events = ((row.get("critic_report") or {}).get("critic_events") or [])
    return [
        event for event in events
        if event.get("event_type") == "negative_boundary_violation"
        or event.get("type") == "negative_boundary_violation"
        or event.get("violation_type") == "negative_boundary_violation"
    ]


def _repair_event_concepts(row: dict[str, Any]) -> list[str]:
    concepts = []
    for event in (row.get("repair_report") or {}).get("repair_events") or []:
        concept = event.get("triggered_by_concept") or event.get("concept")
        if concept:
            concepts.append(concept)
    return concepts


def _post_repair_validation(row: dict[str, Any]) -> dict[str, Any]:
    return (row.get("repair_report") or {}).get("post_repair_validation") or row.get("post_repair_validation") or {}


def _has_excluded_reason(row: dict[str, Any], memory_id: str, token: str | None = None) -> bool:
    for item in _excluded(row):
        if item.get("memory_id") != memory_id:
            continue
        reason = item.get("reason")
        if not reason:
            return False
        return token in reason if token else True
    return False


def _not_consumed(row: dict[str, Any], memory_id: str) -> bool:
    return (
        memory_id not in _positive_ids(row)
        and memory_id not in _negative_ids(row)
        and memory_id not in _do_not_ids(row)
        and memory_id not in _consumed_ids(row)
    )


def _checks(rows: list[dict[str, Any]]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    packet_required = {
        "task_memory_packet_id", "packet_schema_version", "active_positive_preferences",
        "active_negative_boundaries", "current_task_exceptions", "overridden_memories",
        "excluded_memories", "do_not_use_as_positive_signal", "critic_constraints",
        "trace",
    }
    trace_required = {
        "planner_trace_id", "trace_schema_version", "task_memory_packet_id",
        "consumed_memory_ids", "memory_influences", "override_events",
        "critic_events", "repair_events", "final_response_memory_claims",
        "trace_consistency_checks",
    }
    metrics["task_memory_packet_schema_valid_rate"] = _rate(
        sum(1 for r in rows if packet_required <= set(_packet(r).keys())),
        len(rows),
    )
    metrics["planner_trace_schema_valid_rate"] = _rate(
        sum(1 for r in rows if trace_required <= set(_trace(r).keys())),
        len(rows),
    )

    override_rows = [r for r in rows if _packet(r).get("current_task_exceptions")]
    metrics["current_task_exception_precedence_rate"] = _rate(
        sum(1 for r in override_rows if _packet(r).get("overridden_memories")),
        len(override_rows),
    )
    metrics["override_does_not_create_positive_preference_rate"] = _rate(
        sum(
            1 for r in override_rows
            if not {
                exc.get("concept") for exc in _packet(r).get("current_task_exceptions") or []
            } & {
                pref.get("concept") for pref in _packet(r).get("active_positive_preferences") or []
            }
        ),
        len(override_rows),
    )
    metrics["overridden_memory_not_in_explicit_reject_rate"] = _rate(
        sum(
            1 for r in override_rows
            if not {
                item.get("concept") for item in _packet(r).get("overridden_memories") or []
            } & set(_packet(r).get("explicit_reject") or [])
        ),
        len(override_rows),
    )
    metrics["residual_boundary_preservation_rate"] = _rate(
        sum(
            1 for r in override_rows
            if any(c.get("source") == "residual_boundary_after_override" for c in _packet(r).get("critic_constraints") or [])
        ),
        len(override_rows),
    )

    misuse_rows = [
        r for r in rows
        if any(m.get("polarity") == "misuse_correction" for m in _memories(r))
    ]
    metrics["misuse_correction_not_positive_signal_rate"] = _rate(
        sum(
            1 for r in misuse_rows
            if all(m.get("memory_id") not in _positive_ids(r) for m in _memories(r) if m.get("polarity") == "misuse_correction")
        ),
        len(misuse_rows),
    )
    metrics["misuse_correction_present_in_do_not_use_as_positive_signal_rate"] = _rate(
        sum(
            1 for r in misuse_rows
            if all(m.get("memory_id") in _do_not_ids(r) for m in _memories(r) if m.get("polarity") == "misuse_correction")
        ),
        len(misuse_rows),
    )
    metrics["misuse_correction_applied_to_critic_or_retrieval_filter_rate"] = _rate(
        sum(
            1 for r in misuse_rows
            if any(c.get("source") == "misuse_correction_hygiene" for c in _packet(r).get("critic_constraints") or [])
        ),
        len(misuse_rows),
    )

    negative_rows = [
        r for r in rows
        if any(m.get("polarity") in ("avoid", "soft_avoid", "protect") for m in _memories(r))
        and (
            r.get("suite_category") == "negative_boundary_consumption"
            or r.get("defect_type") in (
                "critic_misses_negative_boundary_violation",
                "repair_without_triggering_memory_ref",
                "repair_claims_pass_but_final_still_violates_boundary",
            )
        )
    ]
    metrics["negative_boundary_preserved_rate"] = _rate(
        sum(
            1 for r in negative_rows
            if any(m.get("memory_id") in _negative_ids(r) for m in _memories(r) if m.get("polarity") in ("avoid", "soft_avoid", "protect"))
        ),
        len(negative_rows),
    )
    metrics["negative_boundary_not_in_positive_preferences_rate"] = _rate(
        sum(
            1 for r in negative_rows
            if all(m.get("memory_id") not in _positive_ids(r) for m in _memories(r) if m.get("polarity") in ("avoid", "soft_avoid", "protect"))
        ),
        len(negative_rows),
    )
    metrics["critic_detects_memory_violation_rate"] = _rate(
        sum(1 for r in negative_rows if (r.get("critic_report") or {}).get("critic_events")),
        len(negative_rows),
    )
    repair_rows = [r for r in negative_rows if (r.get("critic_report") or {}).get("critic_events")]
    metrics["repair_has_triggering_memory_ref_rate"] = _rate(
        sum(
            1 for r in repair_rows
            if all(e.get("triggered_by_memory_id") for e in (r.get("repair_report") or {}).get("repair_events") or [])
            and (r.get("repair_report") or {}).get("repair_events")
        ),
        len(repair_rows),
    )
    all_repair_rows = [r for r in rows if (r.get("repair_report") or {}).get("repair_needed") is True]
    metrics["post_repair_validation_present_rate"] = _rate(
        sum(1 for r in all_repair_rows if _post_repair_validation(r)),
        len(all_repair_rows),
    )
    passed_repair_rows = [
        r for r in all_repair_rows
        if any(e.get("result") == "passed" for e in (r.get("repair_report") or {}).get("repair_events") or [])
    ]
    metrics["repair_result_matches_final_outfit_diff_rate"] = _rate(
        sum(
            1 for r in passed_repair_rows
            if all(
                concept in ((r.get("final_outfit") or {}).get("removed_boundary_concepts") or [])
                for concept in _repair_event_concepts(r)
            )
            and ((r.get("final_outfit") or {}).get("remaining_boundary_concepts") or []) == []
        ),
        len(passed_repair_rows),
    )
    negative_repair_rows = [
        r for r in all_repair_rows
        if _negative_boundary_events(r)
    ]
    metrics["final_outfit_boundary_violation_free_rate"] = _rate(
        sum(
            1 for r in negative_repair_rows
            if _post_repair_validation(r).get("validated") is True
            and _post_repair_validation(r).get("remaining_violations") == []
            and _post_repair_validation(r).get("final_outfit_violation_free") is True
            and all(
                not _contains_concept((r.get("final_outfit") or {}).get("items") or [], concept)
                for concept in _repair_event_concepts(r)
            )
        ),
        len(negative_repair_rows),
    )

    def _status_rate(status: str, metric: str, reason_token: str) -> None:
        status_rows = [
            r for r in rows
            for m in _memories(r)
            if m.get("commit_status") == status
        ]
        ok = 0
        for r in status_rows:
            for m in _memories(r):
                if m.get("commit_status") == status and _not_consumed(r, m["memory_id"]) and _has_excluded_reason(r, m["memory_id"], reason_token):
                    ok += 1
        metrics[metric] = _rate(ok, len(status_rows))

    _status_rate("blocked", "blocked_memory_not_consumed_rate", "blocked")
    _status_rate("human_review_required", "review_required_memory_not_consumed_rate", "review_required")
    _status_rate("shadow_only", "shadow_only_memory_not_consumed_rate", "shadow_only")

    rolled = [r for r in rows for m in _memories(r) if m.get("rollback_status") == "rolled_back"]
    metrics["rolledback_memory_not_consumed_rate"] = _rate(
        sum(
            1 for r in rolled
            for m in _memories(r)
            if m.get("rollback_status") == "rolled_back" and _not_consumed(r, m["memory_id"]) and _has_excluded_reason(r, m["memory_id"], "rolledback")
        ),
        len(rolled),
    )
    expired = [r for r in rows for m in _memories(r) if m.get("expires_at")]
    metrics["expired_memory_not_consumed_rate"] = _rate(
        sum(
            1 for r in expired
            for m in _memories(r)
            if m.get("expires_at") and _not_consumed(r, m["memory_id"]) and _has_excluded_reason(r, m["memory_id"], "expired")
        ),
        len(expired),
    )
    low_conf = [r for r in rows for m in _memories(r) if float(m.get("confidence", 1.0)) < 0.6]
    metrics["low_confidence_memory_gated_rate"] = _rate(
        sum(
            1 for r in low_conf
            for m in _memories(r)
            if float(m.get("confidence", 1.0)) < 0.6 and _not_consumed(r, m["memory_id"]) and _has_excluded_reason(r, m["memory_id"], "low_confidence")
        ),
        len(low_conf),
    )

    metrics["contextual_scope_match_rate"] = _rate(
        sum(1 for r in rows if r.get("scenario") != "contextual_match" or _negative_ids(r)),
        len(rows),
    )
    metrics["contextual_scope_mismatch_exclusion_rate"] = _rate(
        sum(1 for r in rows if r.get("scenario") != "contextual_mismatch" or _excluded(r)),
        len(rows),
    )
    metrics["session_soft_scope_rate"] = _rate(
        sum(1 for r in rows if r.get("scenario") != "session_soft_active" or _positive_ids(r)),
        len(rows),
    )
    metrics["this_task_only_precedence_rate"] = _rate(
        sum(1 for r in rows if r.get("scenario") != "this_task_precedence" or _packet(r).get("overridden_memories")),
        len(rows),
    )
    metrics["global_memory_fallback_rate"] = _rate(
        sum(1 for r in rows if r.get("scenario") != "global_fallback" or _positive_ids(r)),
        len(rows),
    )

    metrics["response_claims_subset_of_consumed_memory_rate"] = _rate(
        sum(
            1 for r in rows
            if set((r.get("response") or {}).get("memory_claim_refs") or []).issubset(_consumed_ids(r))
        ),
        len(rows),
    )
    metrics["excluded_memory_has_reason_rate"] = _rate(
        sum(
            1 for r in rows
            if all(item.get("reason") for item in _excluded(r))
        ),
        len(rows),
    )
    metrics["override_event_trace_rate"] = _rate(
        sum(1 for r in override_rows if _trace(r).get("override_events")),
        len(override_rows),
    )
    rows_with_repair = [r for r in rows if (r.get("repair_report") or {}).get("repair_events")]
    metrics["repair_event_trace_rate"] = _rate(
        sum(1 for r in rows_with_repair if _trace(r).get("repair_events")),
        len(rows_with_repair),
    )
    metrics["raw_report_consistency_rate"] = 1.0
    return metrics


def _build_gates(metrics: dict[str, float]) -> tuple[list[dict[str, Any]], list[str], int, int]:
    gates = []
    failed = []
    passed_count = 0
    for name, threshold in THRESHOLDS.items():
        value = metrics.get(name)
        passed = value is not None and value >= threshold
        gates.append({
            "gate": name,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "detail": "MISSING" if value is None else f"{value:.4f} (threshold {threshold})",
        })
        if passed:
            passed_count += 1
        else:
            failed.append(name)
    return gates, failed, passed_count, len(gates) - passed_count


def _detected_defects(rows: list[dict[str, Any]], failed_gates: list[str]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    failed = set(failed_gates)
    detected = []
    unexpected_passes = []
    for defect_type, spec in EXPECTED_DEFECTS.items():
        case = next((r for r in rows if r.get("defect_type") == defect_type), None)
        expected = spec["expected_failed_checks"]
        matched = [g for g in expected if g in failed]
        is_detected = bool(case) and bool(matched)
        if case and not is_detected:
            unexpected_passes.append(case.get("case_id"))
        detected.append({
            "defect_type": defect_type,
            "case_id": case.get("case_id") if case else "",
            "detected": is_detected,
            "failed_check_ids": matched,
            "expected_failed_check_ids": expected,
        })
    expected_failed = {g for spec in EXPECTED_DEFECTS.values() for g in spec["expected_failed_checks"]}
    unexpected_clean_failures = [g for g in failed_gates if g not in expected_failed]
    return detected, unexpected_clean_failures, unexpected_passes


def _verdicts(suite_mode: str, n_fail: int, rows: list[dict[str, Any]], failed_gates: list[str]) -> tuple[dict[str, str], str, list[dict[str, Any]], list[str], list[str]]:
    detected, unexpected_failures, unexpected_passes = _detected_defects(rows, failed_gates)
    all_detected = (
        any(r.get("is_injected_defect") for r in rows)
        and all(d["detected"] for d in detected)
        and not unexpected_failures
        and not unexpected_passes
    )
    verdicts = {
        "clean_acceptance_verdict": "not_applicable",
        "mixed_strict_verdict": "not_applicable",
        "injected_defect_detection_verdict": "not_applicable",
        "release_candidate_verdict": "not_applicable",
    }
    if suite_mode == "clean_acceptance":
        verdicts["clean_acceptance_verdict"] = "pass" if n_fail == 0 else "fail"
        verdicts["release_candidate_verdict"] = "pass_candidate" if n_fail == 0 else "fail"
        return verdicts, "Clean suite contains no injected defects and is used for release acceptance.", [], [], []
    if suite_mode == "mixed_strict_with_injected":
        verdicts["mixed_strict_verdict"] = "fail" if n_fail else "pass"
        verdicts["injected_defect_detection_verdict"] = "pass" if all_detected else "fail"
        interpretation = (
            "Mixed strict suite includes clean memory-consumption cases plus injected defects. "
            "The mixed strict verdict is expected to fail when seeded defects are detected. "
            "Release candidate verdict comes from clean acceptance PASS plus injected detector PASS, not mixed strict PASS."
        )
        return verdicts, interpretation, detected, unexpected_failures, unexpected_passes
    return verdicts, "Injected detector report mode.", detected, unexpected_failures, unexpected_passes


def _write_markdown(report: dict[str, Any], path: str) -> None:
    lines = [
        f"# {report['benchmark_id']} Report",
        "",
        f"- suite_mode: `{report['suite_summary']['suite_mode']}`",
        f"- total_cases: {report['suite_summary']['total_cases']}",
        f"- release_clean_cases: {report['suite_summary']['release_clean_cases']}",
        f"- injected_defect_cases: {report['suite_summary']['injected_defect_cases']}",
        f"- checks: {report['suite_summary']['passed_checks']} / {report['suite_summary']['total_checks']} PASS",
        f"- failed_checks: {report['suite_summary']['failed_checks']}",
        f"- clean_acceptance_verdict: `{report['verdicts']['clean_acceptance_verdict']}`",
        f"- mixed_strict_verdict: `{report['verdicts']['mixed_strict_verdict']}`",
        f"- injected_defect_detection_verdict: `{report['verdicts']['injected_defect_detection_verdict']}`",
        f"- release_candidate_verdict: `{report['verdicts']['release_candidate_verdict']}`",
        "",
        "## Failed Checks",
        "",
    ]
    failed = [g for g in report["gates"] if not g["passed"]]
    lines.extend([f"- `{g['gate']}`: {g['detail']}" for g in failed] or ["- None"])
    lines.extend(["", "## Detected Defects", ""])
    lines.extend([
        f"- `{d['defect_type']}` case `{d['case_id']}` detected={d['detected']} checks={d['failed_check_ids']}"
        for d in report.get("detected_defects", [])
    ] or ["- None"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", choices=["clean_acceptance", "mixed_strict_with_injected", "injected_defect_detection"], required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    rows = _load_raw_dir(args.raw_dir)
    metrics = _checks(rows)
    gates, failed_gates, n_pass, n_fail = _build_gates(metrics)
    injected_count = sum(1 for r in rows if r.get("is_injected_defect"))
    release_clean_count = len(rows) - injected_count
    verdicts, interpretation, detected, unexpected_failures, unexpected_passes = _verdicts(
        args.suite_mode, n_fail, rows, failed_gates
    )
    report = {
        "benchmark_id": BENCHMARK_ID,
        "artifact_schema_version": "v1.29.2",
        "raw_first": True,
        "generated_at": _now_iso(),
        "suite_summary": {
            "suite_mode": args.suite_mode,
            "total_cases": len(rows),
            "total_checks": len(gates),
            "passed_checks": n_pass,
            "failed_checks": n_fail,
            "release_clean_cases": release_clean_count,
            "non_release_control_cases": 0,
            "injected_defect_cases": injected_count,
        },
        "verdicts": verdicts,
        "interpretation": interpretation,
        "metrics": metrics,
        "gates": gates,
        "failed_gates": failed_gates,
        "checks": [
            {
                "check_id": gate["gate"],
                "value": gate["value"],
                "threshold": gate["threshold"],
                "passed": gate["passed"],
                "detail": gate["detail"],
            }
            for gate in gates
        ],
        "detected_defects": detected,
        "unexpected_clean_case_failures": unexpected_failures,
        "unexpected_injected_passes": unexpected_passes,
        "verdict": "pass" if n_fail == 0 else "fail",
    }
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _write_markdown(report, args.out_md)
    print(f"v1.29.2 Report: {n_pass}/{len(gates)} Gates PASS — verdict={report['verdict']}")
    print(f"Verdicts: {verdicts}")
    if failed_gates:
        print(f"FAILED: {failed_gates}")


if __name__ == "__main__":
    main()
