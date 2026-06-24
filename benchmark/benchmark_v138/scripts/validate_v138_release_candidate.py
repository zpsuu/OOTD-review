"""Independent raw-artifact validator for v1.38 governance operations evidence."""
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


GATES = [
    "governance_queue_created_from_runtime_trigger_rate",
    "queue_item_status_consistency_rate",
    "queue_dedupe_blocks_duplicate_open_items_rate",
    "clarification_request_trace_backed_rate",
    "clarification_no_write_preserves_memory_state_rate",
    "clarification_write_candidate_routes_to_gate_rate",
    "human_review_payload_has_raw_evidence_rate",
    "human_review_resolution_uses_write_gate_rate",
    "review_rejection_no_write_preserves_memory_state_rate",
    "temporary_hold_current_turn_only_rate",
    "temporary_hold_release_packet_rebuild_rate",
    "expired_item_no_write_rate",
    "post_resolution_packet_matches_resolution_rate",
    "rollback_audit_absence_proof_rate",
    "blocked_memory_future_absence_proof_rate",
    "reviewer_forbidden_actions_blocked_rate",
    "ledger_hash_chain_valid_rate",
    "ledger_append_only_replay_rate",
    "trace_backed_resolution_claims_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v137_validation_replay_pass_rate",
]


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _entry_hash(entry: dict[str, Any]) -> str:
    return canonical_json_hash({k: v for k, v in entry.items() if k != "entry_hash"})


def _same_state(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ignored = {"state_snapshot_id"}
    return {k: v for k, v in a.items() if k not in ignored} == {k: v for k, v in b.items() if k not in ignored}


def _artifact_list(artifact: dict[str, Any], list_key: str, singleton_key: str) -> list[dict[str, Any]]:
    values = artifact.get(list_key)
    if isinstance(values, list):
        return [value for value in values if isinstance(value, dict)]
    singleton = artifact.get(singleton_key)
    return [singleton] if isinstance(singleton, dict) else []


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    trigger = artifact.get("governance_trigger") or {}
    queue = artifact.get("runtime_governance_queue") or {}
    items = queue.get("queue_items") or []
    decision = artifact.get("governance_resolution_decision")
    gate = artifact.get("production_memory_write_gate") or {}
    before = artifact.get("before_memory_lifecycle_state") or {}
    after = artifact.get("after_memory_lifecycle_state") or {}
    post = artifact.get("post_resolution_task_memory_packet") or {}
    hold = artifact.get("temporary_hold_lifecycle") or {}
    clarification_requests = _artifact_list(artifact, "clarification_requests", "clarification_request")
    clarification = artifact.get("clarification_request")
    clarification_resolution = artifact.get("clarification_resolution")
    human_review_payloads = _artifact_list(artifact, "human_review_payloads", "human_review_payload")
    payload = artifact.get("human_review_payload")
    review = artifact.get("human_review_resolution")
    ledger = artifact.get("governance_decision_ledger") or {}
    claims = artifact.get("visible_claims") or []
    memory_id = before.get("memory_id")
    trigger_id = trigger.get("governance_trigger_id")
    valid_trigger_refs = {trigger_id}
    if decision:
        valid_trigger_refs.add(decision.get("governance_resolution_decision_id"))

    if not trigger_id:
        failures.append("governance_queue_created_from_runtime_trigger_rate")
    for item in items:
        if item.get("trigger_ref") not in valid_trigger_refs or item.get("source_runtime_trace_id") != trigger.get("source_runtime_trace_id") or item.get("target_memory_id") != trigger.get("target_memory_id"):
            failures.append("governance_queue_created_from_runtime_trigger_rate")
            break
        if not (set(item.get("trace_refs") or []) & valid_trigger_refs):
            failures.append("governance_queue_created_from_runtime_trigger_rate")
            break

    counts = {
        "open": queue.get("open_item_count"),
        "resolved": queue.get("resolved_item_count"),
        "expired": queue.get("expired_item_count"),
    }
    if counts["open"] != sum(1 for item in items if item.get("status") == "open") or counts["resolved"] != sum(1 for item in items if item.get("status") == "resolved") or counts["expired"] != sum(1 for item in items if item.get("status") == "expired"):
        failures.append("queue_item_status_consistency_rate")
    resolution_ids = {decision.get("governance_resolution_decision_id")} if decision else set()
    item_ids = {item.get("governance_queue_item_id") for item in items}
    for item in items:
        status = item.get("status")
        if status == "open" and item.get("resolution_ref"):
            failures.append("queue_item_status_consistency_rate")
        if status == "resolved" and item.get("resolution_ref") not in resolution_ids:
            failures.append("queue_item_status_consistency_rate")
        if status == "expired" and ((item.get("expiry_proof") or {}).get("production_write_executed") is not False):
            failures.append("queue_item_status_consistency_rate")
        if status == "deduped" and item.get("canonical_queue_item_id") not in item_ids:
            failures.append("queue_item_status_consistency_rate")

    active_keys: set[tuple[Any, Any, Any]] = set()
    for item in items:
        if item.get("status") in {"open", "resolved", "expired"}:
            key = (item.get("trigger_type"), item.get("target_memory_id"), item.get("trigger_ref"))
            if item.get("status") == "open" and key in active_keys:
                failures.append("queue_dedupe_blocks_duplicate_open_items_rate")
            active_keys.add(key)
    for item in items:
        if item.get("status") == "deduped" and not item.get("canonical_queue_item_id"):
            failures.append("queue_dedupe_blocks_duplicate_open_items_rate")

    clarification_by_item = {request.get("governance_queue_item_id"): request for request in clarification_requests}
    for request in clarification_requests:
        if not request.get("trace_refs") or request.get("memory_changed_claim") is True or "global_memory" not in (request.get("must_not_suggest") or []):
            failures.append("clarification_request_trace_backed_rate")
        if not request.get("current_turn_hold_ref"):
            failures.append("clarification_request_trace_backed_rate")
    for item in items:
        if item.get("status") == "open" and item.get("trigger_type") == "clarification_required":
            item_id = item.get("governance_queue_item_id")
            request = clarification_by_item.get(item_id)
            if not request:
                failures.append("clarification_request_trace_backed_rate")
                continue
            if item_id not in (request.get("trace_refs") or []) or request.get("current_turn_hold_ref") != hold.get("temporary_hold_id"):
                failures.append("clarification_request_trace_backed_rate")
    if decision and decision.get("resolution_type") == "clarified_no_write":
        if decision.get("production_write_executed") is True or not _same_state(before, after):
            failures.append("clarification_no_write_preserves_memory_state_rate")
    if decision and decision.get("resolution_type") == "clarified_write_candidate":
        if not decision.get("production_write_gate_ref") or gate.get("decision") != "allow" or gate.get("production_write_executed") is not True:
            failures.append("clarification_write_candidate_routes_to_gate_rate")
        if not clarification_resolution or clarification_resolution.get("production_write_requested") is not True:
            failures.append("clarification_write_candidate_routes_to_gate_rate")

    human_review_payload_by_item = {review_payload.get("governance_queue_item_id"): review_payload for review_payload in human_review_payloads}
    for review_payload in human_review_payloads:
        if not review_payload.get("raw_evidence_refs") or review_payload.get("production_write_blocked_until_resolution") is not True:
            failures.append("human_review_payload_has_raw_evidence_rate")
        if not review_payload.get("forbidden_reviewer_actions"):
            failures.append("human_review_payload_has_raw_evidence_rate")
    for item in items:
        if item.get("status") == "open" and item.get("trigger_type") == "human_review_required":
            item_id = item.get("governance_queue_item_id")
            review_payload = human_review_payload_by_item.get(item_id)
            if not review_payload:
                failures.append("human_review_payload_has_raw_evidence_rate")
                continue
            trace_refs = set(review_payload.get("raw_evidence_refs") or []) | set(review_payload.get("trace_refs") or [])
            if not trace_refs or review_payload.get("production_write_blocked_until_resolution") is not True:
                failures.append("human_review_payload_has_raw_evidence_rate")
    if decision and decision.get("resolution_type") == "review_approved_write":
        if not decision.get("production_write_gate_ref") or gate.get("decision") != "allow" or gate.get("production_write_executed") is not True:
            failures.append("human_review_resolution_uses_write_gate_rate")
    if decision and decision.get("resolution_type") == "review_rejected_no_write":
        if decision.get("production_write_executed") is True or not _same_state(before, after):
            failures.append("review_rejection_no_write_preserves_memory_state_rate")

    if hold:
        if hold.get("current_turn_scoped") is not True or hold.get("production_lifecycle_mutation") is not False:
            failures.append("temporary_hold_current_turn_only_rate")
        if hold.get("status") == "released" and memory_id not in (post.get("consumed_promoted_memory_ids") or []) and after.get("current_status") == "active":
            failures.append("temporary_hold_release_packet_rebuild_rate")
        if hold.get("status") == "expired":
            if (decision or {}).get("production_write_executed") is True or gate.get("production_write_executed") is True:
                failures.append("expired_item_no_write_rate")

    post_consumed = post.get("consumed_promoted_memory_ids") or []
    post_excluded = post.get("excluded_memory_ids") or []
    resolution_type = (decision or {}).get("resolution_type")
    if after.get("current_status") == "active" and hold.get("status") == "released" and post.get("request_context") in (after.get("contexts") or []) and memory_id not in post_consumed:
        failures.append("post_resolution_packet_matches_resolution_rate")
    if after.get("current_status") in {"rolled_back", "blocked"} and memory_id in post_consumed:
        failures.append("post_resolution_packet_matches_resolution_rate")
    if resolution_type in {"clarified_no_write", "review_rejected_no_write"} and not _same_state(before, after):
        failures.append("post_resolution_packet_matches_resolution_rate")
    if resolution_type in {"clarified_write_candidate", "review_approved_write"} and (gate.get("decision") != "allow" or gate.get("production_write_executed") is not True):
        failures.append("post_resolution_packet_matches_resolution_rate")
    if post_excluded and post.get("expected_behavior") not in {"temporary_hold_current_turn", "temporary_hold_pending_review", "expired_hold_no_write", "excluded_by_rollback", "excluded_by_blocked_state"}:
        failures.append("post_resolution_packet_matches_resolution_rate")

    rollback = artifact.get("rollback_audit_absence_proof") or {}
    if resolution_type == "rollback_confirmed" or rollback:
        if (rollback.get("read_after_rollback") or {}).get("memory_present") is not False or rollback.get("future_consumption_absent") is not True or memory_id in post_consumed:
            failures.append("rollback_audit_absence_proof_rate")
    blocked = artifact.get("blocked_memory_future_absence_proof") or {}
    if before.get("current_status") == "blocked" or blocked:
        if blocked.get("future_consumption_absent") is not True or blocked.get("future_claims_absent") is not True or memory_id in post_consumed:
            failures.append("blocked_memory_future_absence_proof_rate")

    if review and review.get("reviewer_action") in {"globalize_memory", "add_unconfirmed_aspect", "infer_body_or_identity"}:
        if review.get("blocked_forbidden_action") is not True or (decision or {}).get("production_write_executed") is True:
            failures.append("reviewer_forbidden_actions_blocked_rate")
        proposed = (review.get("proposed_memory_patch") or {}).get("add_aspects") or []
        confirmed = review.get("confirmed_aspects") or before.get("confirmed_aspects") or []
        if any(aspect not in confirmed for aspect in proposed) and review.get("blocked_forbidden_action") is not True:
            failures.append("reviewer_forbidden_actions_blocked_rate")
    for review_payload in human_review_payloads:
        if not {"globalize_memory", "add_unconfirmed_aspect"}.issubset(set(review_payload.get("forbidden_reviewer_actions") or [])):
            failures.append("reviewer_forbidden_actions_blocked_rate")
            break

    previous = None
    for entry in ledger.get("ledger_entries") or []:
        if entry.get("previous_entry_hash") != previous or entry.get("entry_hash") != _entry_hash(entry):
            failures.append("ledger_hash_chain_valid_rate")
            break
        previous = entry.get("entry_hash")
    if ledger.get("entry_hash_chain_valid") is not True:
        failures.append("ledger_hash_chain_valid_rate")
    replay_hashes = [row.get("entry_hash") for row in ledger.get("append_only_replay") or []]
    ledger_hashes = [entry.get("entry_hash") for entry in ledger.get("ledger_entries") or []]
    if ledger.get("append_only") is not True or replay_hashes != ledger_hashes:
        failures.append("ledger_append_only_replay_rate")

    for claim in claims:
        if not claim.get("trace_refs") or (decision and decision.get("governance_resolution_decision_id") not in claim.get("trace_refs", [])):
            failures.append("trace_backed_resolution_claims_rate")
            break

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v137_replay_proof") or {}).get("run_v137_validation_suite") != "PASS":
        failures.append("v137_validation_replay_pass_rate")
    return sorted(set(failures))


def validate_case(path: Path, subset: str, base_dir: Path) -> dict[str, Any]:
    artifact = read_json(path)
    failed = _structural_failures(artifact)
    return {
        "case_id": artifact.get("case_id") or path.stem,
        "artifact_ref": str(path.relative_to(base_dir)),
        "passed": not failed,
        "failed_check_ids": failed,
        "expected_failed_check_ids": artifact.get("expected_failed_check_ids", []),
        "defect_type": artifact.get("defect_type"),
    }


def validate_directory(result_dir: Path, subset: str) -> dict[str, Any]:
    cases = [validate_case(path, subset, result_dir) for path in json_files(_artifact_dir(result_dir, subset))]
    checks: list[dict[str, Any]] = []
    for gate in GATES:
        passed = [case for case in cases if gate not in case["failed_check_ids"]]
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw governance validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.38.independent.governance_operations_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v138/results/v138_release_candidate")
    parser.add_argument("--subset", choices=["clean", "adversarial", "mixed_strict"], default="clean")
    parser.add_argument("--output")
    parser.add_argument("--write-consistency", action="store_true")
    args = parser.parse_args()
    result_dir = Path(args.result_dir)
    report = validate_directory(result_dir, args.subset)
    if args.output:
        write_json(Path(args.output), report)
    if args.subset == "adversarial":
        rows = report.get("detected_defects", [])
        seeded = len(rows)
        detected = sum(1 for row in rows if row.get("detected"))
        write_json(result_dir / "injected_defect_detection_summary.json", {"version": "v1.38", "generated_at": now_iso(), "verdict": "pass" if detected == seeded else "fail", "seeded_defects": seeded, "detected_defects": detected, "unexpected_injected_passes": [row for row in rows if not row.get("detected")], "detected": rows})
    if args.write_consistency:
        write_consistency_reports(result_dir)
    print(json.dumps(report["suite_summary"], ensure_ascii=False, indent=2))
    if args.subset == "clean" and report["suite_summary"]["failed_cases"]:
        raise SystemExit(1)
    if args.subset in {"adversarial", "mixed_strict"} and report["suite_summary"]["passed_cases"]:
        raise SystemExit(1)
    if args.subset == "adversarial" and report.get("detected_defect_count") != report["suite_summary"]["total_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
