"""Independent raw-artifact validator for v1.36 feedback lifecycle evidence."""
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
from benchmark.common.raw_artifact_validation import json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


GATES = [
    "feedback_event_trace_refs_consumed_memory_rate",
    "feedback_event_consumption_report_ref_present_rate",
    "feedback_missing_trace_requires_clarification_rate",
    "right_feedback_reinforces_without_scope_expansion_rate",
    "reinforcement_confidence_cap_respected_rate",
    "too_strong_feedback_reduces_weight_not_deletes_rate",
    "too_strong_future_consumption_softened_rate",
    "wrong_aspect_creates_aspect_correction_rate",
    "wrong_aspect_preserves_confirmed_aspects_rate",
    "wrong_context_narrows_scope_rate",
    "wrong_context_future_exclusion_rate",
    "single_feedback_does_not_globalize_rate",
    "do_not_use_blocks_future_consumption_rate",
    "blocked_memory_not_claimed_rate",
    "forget_memory_routes_to_rollback_gate_rate",
    "rollback_removes_future_packet_consumption_rate",
    "rollback_read_after_absence_proof_rate",
    "high_risk_feedback_requires_review_rate",
    "review_pending_does_not_claim_applied_lifecycle_effect_rate",
    "ambiguous_feedback_requires_clarification_rate",
    "multi_day_lifecycle_stability_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v135_validation_replay_pass_rate",
]


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    memory_id = (artifact.get("promoted_memory_atom") or {}).get("memory_id")
    downstream = artifact.get("downstream_consumption") or {}
    event = artifact.get("promoted_memory_feedback_event") or {}
    interp = artifact.get("feedback_interpretation") or {}
    proposal = artifact.get("memory_lifecycle_proposal") or {}
    decision = artifact.get("feedback_write_decision") or {}
    state = artifact.get("updated_memory_lifecycle_state") or {}
    proof = artifact.get("post_feedback_consumption_proof") or {}
    rollback = artifact.get("rollback_proof") or {}

    consumed_before = memory_id in (downstream.get("consumed_promoted_memory_ids") or [])
    action = event.get("feedback_action")
    intent = interp.get("interpreted_intent")
    proposal_type = proposal.get("proposal_type")
    status = state.get("current_status")

    if consumed_before:
        if event.get("promoted_memory_id") != memory_id:
            failures.append("feedback_event_trace_refs_consumed_memory_rate")
        if event.get("consumption_report_id") != downstream.get("consumption_report_id"):
            failures.append("feedback_event_consumption_report_ref_present_rate")
    elif intent not in {"clarification_required", "review_required"}:
        failures.append("feedback_missing_trace_requires_clarification_rate")

    if action == "use_was_right":
        if state.get("contexts") != (artifact.get("promoted_memory_atom") or {}).get("contexts"):
            failures.append("right_feedback_reinforces_without_scope_expansion_rate")
        if state.get("confidence", 0) > 0.95:
            failures.append("reinforcement_confidence_cap_respected_rate")
    if action == "use_was_too_strong":
        patch = proposal.get("proposed_patch") or {}
        if decision.get("gate_decision") != "human_review_required":
            if status == "rolled_back" or patch.get("weight_delta", 0) >= 0:
                failures.append("too_strong_feedback_reduces_weight_not_deletes_rate")
            if proof.get("expected_behavior") != "consume_less_strongly":
                failures.append("too_strong_future_consumption_softened_rate")
    if action == "wrong_aspect" and intent == "aspect_correction":
        if proposal_type != "correct_aspect":
            failures.append("wrong_aspect_creates_aspect_correction_rate")
        if "color_palette_preference" not in (state.get("allowed_downstream_use") or []):
            failures.append("wrong_aspect_preserves_confirmed_aspects_rate")
    if action in {"wrong_context", "only_for_this_context"} and intent == "scope_narrowing":
        if "global" in (state.get("contexts") or []):
            failures.append("single_feedback_does_not_globalize_rate")
        if not state.get("context_exclusions") and proposal_type != "narrow_scope":
            failures.append("wrong_context_narrows_scope_rate")
        packet = proof.get("task_memory_packet_after_feedback") or {}
        if proof.get("expected_behavior") == "exclude_in_context":
            if memory_id in (packet.get("consumed_promoted_memory_ids") or []):
                failures.append("wrong_context_future_exclusion_rate")
            if packet.get("request_context") not in (state.get("context_exclusions") or []):
                failures.append("wrong_context_future_exclusion_rate")
    if action == "do_not_use_this_inspiration":
        packet = proof.get("task_memory_packet_after_feedback") or {}
        if status != "blocked" or memory_id in (packet.get("consumed_promoted_memory_ids") or []):
            failures.append("do_not_use_blocks_future_consumption_rate")
        if proof.get("response_claims_after_feedback"):
            failures.append("blocked_memory_not_claimed_rate")
    if action in {"forget_this_inspiration_memory", "undo_last_memory_effect"}:
        if proposal_type != "rollback_memory" or not decision.get("rollback_ref"):
            failures.append("forget_memory_routes_to_rollback_gate_rate")
        packet = proof.get("task_memory_packet_after_feedback") or {}
        if action == "forget_this_inspiration_memory" and memory_id in (packet.get("consumed_promoted_memory_ids") or []):
            failures.append("rollback_removes_future_packet_consumption_rate")
        read_after = rollback.get("read_after_rollback") or {}
        if action == "forget_this_inspiration_memory" and read_after.get("memory_present") is not False:
            failures.append("rollback_read_after_absence_proof_rate")
    if interp.get("risk_level") in {"high", "critical"} and decision.get("gate_decision") not in {"human_review_required", "block"}:
        failures.append("high_risk_feedback_requires_review_rate")
    if decision.get("gate_decision") == "human_review_required":
        claims_text = " ".join(
            str(claim.get("text", ""))
            for claim in (proof.get("response_claims_after_feedback") or [])
            if isinstance(claim, dict)
        ).lower()
        applied_effect_terms = ["softened", "narrowed", "blocked", "rolled back", "reinforced", "reduced", "changed"]
        if any(term in claims_text for term in applied_effect_terms):
            failures.append("review_pending_does_not_claim_applied_lifecycle_effect_rate")
    if intent == "clarification_required" and decision.get("gate_decision") != "clarification_required":
        failures.append("ambiguous_feedback_requires_clarification_rate")
    if (artifact.get("multi_day_lifecycle_proof") or {}).get("stable") is not True:
        failures.append("multi_day_lifecycle_stability_rate")
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
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw artifact validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.36.independent.feedback_lifecycle_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v136/results/v136_release_candidate")
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
