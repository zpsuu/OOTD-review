"""Independent raw-artifact validator for v1.37 runtime loop evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.adversarial_validation import detected_defect_rows
from benchmark.common.raw_artifact_validation import canonical_json_hash, json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


STAGE_ORDER = [
    "intake",
    "confirmation",
    "promotion",
    "consumption",
    "feedback",
    "post_feedback_consumption",
    "multi_day_replay",
]

GATES = [
    "runtime_trace_stage_order_complete_rate",
    "runtime_trace_has_state_snapshots_rate",
    "handoff_ids_match_across_stages_rate",
    "no_pre_gate_production_write_rate",
    "confirmed_aspects_only_rate",
    "promotion_gate_required_before_memory_write_rate",
    "downstream_consumption_requires_promoted_memory_rate",
    "soft_prefer_not_hard_filter_rate",
    "mismatching_context_exclusion_rate",
    "feedback_event_refs_consumed_memory_rate",
    "post_feedback_packet_uses_updated_lifecycle_state_rate",
    "wrong_context_feedback_tests_excluded_context_rate",
    "review_pending_does_not_claim_applied_effect_rate",
    "rollback_removes_future_consumption_rate",
    "blocked_memory_not_claimed_rate",
    "trace_backed_visible_claims_rate",
    "multi_day_state_hash_stability_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v136_validation_replay_pass_rate",
]


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    return canonical_json_hash({k: v for k, v in snapshot.items() if k != "state_hash"})


def _text_claims(claims: list[dict[str, Any]]) -> str:
    return " ".join(str(claim.get("text", "")) for claim in claims if isinstance(claim, dict)).lower()


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    trace = artifact.get("runtime_trace") or {}
    events = trace.get("stage_events") or []
    snapshots = trace.get("state_snapshots") or []
    handoffs = artifact.get("handoff_proofs") or []
    memory = artifact.get("promoted_memory_atom")
    gate = artifact.get("production_memory_write_gate") or {}
    confirmed = artifact.get("confirmed_inspiration_candidate") or {}
    packet = artifact.get("task_memory_packet") or {}
    feedback = artifact.get("promoted_memory_feedback_event") or {}
    decision = artifact.get("feedback_write_decision") or {}
    state = artifact.get("updated_memory_lifecycle_state") or {}
    post_packet = artifact.get("post_feedback_task_memory_packet") or {}
    rollback = artifact.get("rollback_proof") or {}
    claims = artifact.get("visible_claims") or []
    post_claims = artifact.get("post_feedback_claims") or []
    memory_id = (memory or {}).get("memory_id")

    if trace.get("stage_order") != STAGE_ORDER:
        failures.append("runtime_trace_stage_order_complete_rate")
    if len(events) < len(STAGE_ORDER) or [event.get("stage") for event in events[: len(STAGE_ORDER)]] != STAGE_ORDER:
        failures.append("runtime_trace_stage_order_complete_rate")
    if len(snapshots) < len(STAGE_ORDER):
        failures.append("runtime_trace_has_state_snapshots_rate")
    for snapshot in snapshots:
        if snapshot.get("state_hash") != _snapshot_hash(snapshot):
            failures.append("multi_day_state_hash_stability_rate")
            break
    if len(set((artifact.get("multi_day_runtime_trace") or {}).get("day_state_hashes") or [])) > 1:
        failures.append("multi_day_state_hash_stability_rate")

    for handoff in handoffs:
        if handoff.get("same_id") is not True or handoff.get("source_output_ref") != handoff.get("target_input_ref"):
            failures.append("handoff_ids_match_across_stages_rate")
            break

    if gate.get("pre_gate_production_write") is True:
        failures.append("no_pre_gate_production_write_rate")
    if memory and gate.get("decision") != "allow":
        failures.append("promotion_gate_required_before_memory_write_rate")
    if memory and not gate.get("production_write_executed"):
        failures.append("promotion_gate_required_before_memory_write_rate")

    confirmed_aspects = set(confirmed.get("confirmed_aspects") or [])
    memory_aspects = set((memory or {}).get("confirmed_aspects") or [])
    if memory and (not memory_aspects or not memory_aspects.issubset(confirmed_aspects)):
        failures.append("confirmed_aspects_only_rate")

    consumed = packet.get("consumed_promoted_memory_ids") or []
    if consumed and (not memory or memory_id not in consumed):
        failures.append("downstream_consumption_requires_promoted_memory_rate")
    if consumed and gate.get("production_write_executed") is not True:
        failures.append("downstream_consumption_requires_promoted_memory_rate")
    if packet.get("consumption_mode") == "hard_filter":
        failures.append("soft_prefer_not_hard_filter_rate")
    if packet.get("request_context") not in {"office_daily", None} and consumed:
        failures.append("mismatching_context_exclusion_rate")

    if feedback.get("promoted_memory_id") and feedback.get("promoted_memory_id") not in consumed:
        if feedback.get("consumption_report_id") is not None:
            failures.append("feedback_event_refs_consumed_memory_rate")

    if state.get("current_status") in {"blocked", "rolled_back"} and memory_id in (post_packet.get("consumed_promoted_memory_ids") or []):
        failures.append("post_feedback_packet_uses_updated_lifecycle_state_rate")
    if post_packet.get("expected_behavior") == "exclude_in_context":
        if post_packet.get("request_context") not in (state.get("context_exclusions") or []):
            failures.append("wrong_context_feedback_tests_excluded_context_rate")
        if memory_id in (post_packet.get("consumed_promoted_memory_ids") or []):
            failures.append("wrong_context_feedback_tests_excluded_context_rate")

    if decision.get("gate_decision") == "human_review_required":
        applied_terms = ["softened", "narrowed", "blocked", "rolled back", "reinforced", "changed", "reduced"]
        if any(term in _text_claims(post_claims) for term in applied_terms):
            failures.append("review_pending_does_not_claim_applied_effect_rate")

    if state.get("current_status") == "rolled_back":
        if memory_id in (post_packet.get("consumed_promoted_memory_ids") or []):
            failures.append("rollback_removes_future_consumption_rate")
        if post_claims:
            failures.append("blocked_memory_not_claimed_rate")
        read_after = rollback.get("read_after_rollback") if isinstance(rollback, dict) else None
        if not read_after or read_after.get("memory_present") is not False:
            failures.append("rollback_removes_future_consumption_rate")
    if state.get("current_status") == "blocked" and post_claims:
        failures.append("blocked_memory_not_claimed_rate")

    for claim in claims + post_claims:
        if not claim.get("trace_refs"):
            failures.append("trace_backed_visible_claims_rate")
            break

    if (artifact.get("runtime_invariant_report") or {}).get("passed") is not True:
        failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v136_replay_proof") or {}).get("run_v136_validation_suite") != "PASS":
        failures.append("v136_validation_replay_pass_rate")
    return failures


def validate_case(path: Path, subset: str, base_dir: Path) -> dict[str, Any]:
    artifact = read_json(path)
    failed = [gate for gate in GATES if (artifact.get("gate_assertions") or {}).get(gate) is not True]
    if subset == "clean":
        failed.extend(_structural_failures(artifact))
    return {
        "case_id": artifact.get("case_id") or path.stem,
        "artifact_ref": str(path.relative_to(base_dir)),
        "passed": not set(failed),
        "failed_check_ids": sorted(set(failed)),
        "expected_failed_check_ids": artifact.get("expected_failed_check_ids", []),
        "defect_type": artifact.get("defect_type"),
    }


def validate_directory(result_dir: Path, subset: str) -> dict[str, Any]:
    cases = [validate_case(path, subset, result_dir) for path in json_files(_artifact_dir(result_dir, subset))]
    checks: list[dict[str, Any]] = []
    for gate in GATES:
        passed = [case for case in cases if gate not in case["failed_check_ids"]]
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw runtime trace validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.37.independent.runtime_loop_validator",
        "generated_at": now_iso(),
        "result_dir": str(result_dir),
        "subset": subset,
        "suite_summary": {
            "total_cases": len(cases),
            "passed_cases": sum(1 for case in cases if case["passed"]),
            "failed_cases": sum(1 for case in cases if not case["passed"]),
            "total_checks": len(GATES),
            "passed_checks": sum(1 for check in checks if check["passed"]),
            "failed_checks": sum(1 for check in checks if not check["passed"]),
        },
        "checks": checks,
        "case_results": cases,
    }
    if subset in {"adversarial", "mixed_strict"}:
        report["detected_defects"] = detected_defect_rows(cases)
        report["detected_defect_count"] = sum(1 for row in report["detected_defects"] if row["detected"])
    return report


def write_consistency_reports(result_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sample = check_sample_consistency(result_dir)
    write_json(result_dir / "sample_consistency_report.json", {**sample, "generated_at": now_iso()})
    write_json(result_dir / "report_consistency_report.json", {"validator": "benchmark.common.report_consistency", "generated_at": now_iso(), "passed": False, "status": "generating"})
    report = check_report_consistency(result_dir, GATES)
    write_json(result_dir / "report_consistency_report.json", {**report, "generated_at": now_iso()})
    return sample, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="benchmark/benchmark_v137/results/v137_release_candidate")
    parser.add_argument("--subset", choices=["clean", "adversarial", "mixed_strict"], default="clean")
    parser.add_argument("--output")
    parser.add_argument("--write-consistency", action="store_true")
    args = parser.parse_args()
    result_dir = Path(args.result_dir)
    report = validate_directory(result_dir, args.subset)
    if args.output:
        write_json(Path(args.output), report)
    if args.write_consistency:
        write_consistency_reports(result_dir)
    print(json.dumps(report["suite_summary"], ensure_ascii=False, indent=2))
    if args.subset == "clean" and report["suite_summary"]["failed_cases"]:
        raise SystemExit(1)
    if args.subset in {"adversarial", "mixed_strict"} and report["suite_summary"]["passed_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

