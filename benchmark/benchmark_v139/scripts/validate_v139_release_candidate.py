"""Independent raw-artifact validator for v1.39 governance action surfaces."""
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
    "surface_created_from_governance_queue_rate",
    "action_card_matches_queue_item_rate",
    "clarification_card_trace_backed_rate",
    "action_submission_allowed_and_active_rate",
    "no_write_action_preserves_memory_state_rate",
    "remember_for_context_routes_to_write_gate_rate",
    "review_pending_notice_hides_internal_evidence_rate",
    "review_resolution_response_truthful_rate",
    "expired_action_disabled_noop_rate",
    "duplicate_submission_idempotent_rate",
    "stale_action_suppressed_rate",
    "post_action_packet_matches_resolution_rate",
    "daily_outfit_status_rebuild_rate",
    "rollback_blocked_status_absence_proof_rate",
    "response_claims_trace_backed_rate",
    "policy_safe_user_visible_text_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v138_validation_replay_pass_rate",
]

NO_WRITE_ACTIONS = {"this_time_only", "do_not_change_memory", "dismiss", "retry_after_review"}
FORBIDDEN_TEXT = {"raw_evidence", "risk_reasons", "global memory", "globalize", "silhouette", "body", "identity", "attractive", "sku", "merchant", "affiliate", "aigc", "image generation"}
SUBMITTED_ACTION_SCENARIOS = {
    "this_time_only",
    "do_not_change_memory",
    "remember_for_context",
    "post_this_time_only",
    "post_write_candidate",
    "expired_submission",
    "duplicate_submission",
}
NO_RESULT_SCENARIOS = {"open_clarification", "open_review", "temporary_hold"}
STALE_PROOF_SCENARIOS = {"stale_suppressed", "stale_hold_removed"}


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _same_state(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ignored = {"state_snapshot_id"}
    return {k: v for k, v in a.items() if k not in ignored} == {k: v for k, v in b.items() if k not in ignored}


def _lower_texts(surface: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for card in surface.get("cards") or []:
        texts.append(str(card.get("title") or "").lower())
        texts.append(str(card.get("body") or "").lower())
    for block in surface.get("response_blocks") or []:
        texts.append(str(block.get("text") or "").lower())
    return texts


def _has_forbidden_text(surface: dict[str, Any]) -> bool:
    return any(term in text for text in _lower_texts(surface) for term in FORBIDDEN_TEXT)


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    runtime = artifact.get("runtime_trace") or {}
    trigger = artifact.get("governance_trigger") or {}
    queue = artifact.get("runtime_governance_queue") or {}
    items = queue.get("queue_items") or []
    item_by_id = {item.get("governance_queue_item_id"): item for item in items}
    surface = artifact.get("governance_action_surface") or {}
    cards = surface.get("cards") or []
    blocks = surface.get("response_blocks") or []
    cards_by_id = {card.get("user_action_card_id"): card for card in cards}
    clarification_requests = artifact.get("clarification_requests") or []
    requests_by_item: dict[Any, list[dict[str, Any]]] = {}
    for request in clarification_requests:
        requests_by_item.setdefault(request.get("governance_queue_item_id"), []).append(request)
    review_payloads = artifact.get("human_review_payloads") or []
    payloads_by_item: dict[Any, list[dict[str, Any]]] = {}
    for payload in review_payloads:
        payloads_by_item.setdefault(payload.get("governance_queue_item_id"), []).append(payload)
    submission = artifact.get("action_submission_envelope")
    result = artifact.get("action_result_packet")
    decision = artifact.get("governance_resolution_decision")
    gate = artifact.get("production_memory_write_gate") or {}
    before = artifact.get("before_memory_lifecycle_state") or {}
    after = artifact.get("after_memory_lifecycle_state") or {}
    post = artifact.get("post_action_task_memory_packet") or {}
    idempotency = artifact.get("action_idempotency_record")
    stale = artifact.get("stale_action_suppression_proof")
    claims = artifact.get("response_claim_traces") or []
    absence = artifact.get("rollback_blocked_absence_proof") or {}
    daily = artifact.get("daily_outfit_card_status_proof") or {}
    scenario = artifact.get("scenario_kind")
    memory_id = before.get("memory_id")

    submitted_action_required = scenario in SUBMITTED_ACTION_SCENARIOS
    result_required = scenario not in NO_RESULT_SCENARIOS
    if submitted_action_required and not submission:
        failures.append("action_submission_allowed_and_active_rate")
    if result_required and not result:
        failures.append("post_action_packet_matches_resolution_rate")
        if scenario in {"expired_card", "expired_submission"}:
            failures.append("expired_action_disabled_noop_rate")
    if scenario == "duplicate_submission" and not idempotency:
        failures.append("duplicate_submission_idempotent_rate")
    if scenario in STALE_PROOF_SCENARIOS and not stale:
        failures.append("stale_action_suppressed_rate")

    if surface.get("runtime_trace_id") != runtime.get("runtime_trace_id") or surface.get("source_governance_queue_ref") != queue.get("runtime_governance_queue_id"):
        failures.append("surface_created_from_governance_queue_rate")
    if not set([runtime.get("runtime_trace_id"), queue.get("runtime_governance_queue_id")]).issubset(set(surface.get("trace_refs") or [])):
        failures.append("surface_created_from_governance_queue_rate")
    for card in cards:
        if card.get("governance_queue_item_id") not in item_by_id:
            failures.append("action_card_matches_queue_item_rate")
        if not card.get("trace_refs") or card.get("governance_queue_item_id") not in (card.get("trace_refs") or []):
            failures.append("action_card_matches_queue_item_rate")
        item = item_by_id.get(card.get("governance_queue_item_id")) or {}
        if item.get("status") == "expired" and (card.get("display_state") != "expired" or card.get("disabled_reason") != "expired" or card.get("allowed_actions")):
            failures.append("expired_action_disabled_noop_rate")
            failures.append("action_card_matches_queue_item_rate")
        if card.get("card_type") in {"rollback_status", "blocked_status"} and card.get("allowed_actions"):
            failures.append("action_card_matches_queue_item_rate")

    for card in cards:
        if card.get("card_type") == "clarification":
            matches = requests_by_item.get(card.get("governance_queue_item_id"), [])
            if len(matches) != 1:
                failures.append("clarification_card_trace_backed_rate")
                continue
            request = matches[0]
            if not set(card.get("allowed_actions") or []).issubset(set(request.get("allowed_response_kinds") or [])):
                failures.append("clarification_card_trace_backed_rate")
            if not card.get("visible_text_source_refs") or request.get("clarification_request_id") not in (card.get("trace_refs") or []) and card.get("display_state") == "active":
                failures.append("clarification_card_trace_backed_rate")
            if request.get("memory_changed_claim") is True or "global_memory" not in (request.get("must_not_suggest") or []):
                failures.append("clarification_card_trace_backed_rate")

    if submission:
        card = cards_by_id.get(submission.get("user_action_card_id"))
        expired_noop = (result or {}).get("result_type") == "expired_noop"
        if not card:
            failures.append("action_submission_allowed_and_active_rate")
        elif card.get("display_state") in {"expired", "disabled"}:
            if not expired_noop:
                failures.append("action_submission_allowed_and_active_rate")
        elif submission.get("submitted_action") not in (card.get("allowed_actions") or []):
            failures.append("action_submission_allowed_and_active_rate")
        if submission.get("governance_queue_item_id") not in item_by_id or submission.get("user_action_card_id") not in (submission.get("trace_refs") or []):
            failures.append("action_submission_allowed_and_active_rate")

    action = (submission or {}).get("submitted_action")
    if action in NO_WRITE_ACTIONS and action != "retry_after_review":
        if (decision or {}).get("production_write_executed") is True or (result or {}).get("production_write_executed") is True or not _same_state(before, after):
            failures.append("no_write_action_preserves_memory_state_rate")
    if action == "remember_for_context":
        if not decision or decision.get("production_write_gate_ref") != gate.get("gate_id") or gate.get("decision") != "allow" or gate.get("production_write_executed") is not True:
            failures.append("remember_for_context_routes_to_write_gate_rate")
        if (result or {}).get("result_type") != "write_candidate_submitted":
            failures.append("remember_for_context_routes_to_write_gate_rate")

    for card in cards:
        if card.get("card_type") == "review_pending":
            item_id = card.get("governance_queue_item_id")
            if item_id not in payloads_by_item:
                failures.append("review_pending_notice_hides_internal_evidence_rate")
    for block in blocks:
        text = str(block.get("text") or "").lower()
        if block.get("block_type") == "review_pending_notice":
            if "saved" in text or "applied" in text or "approved" in text or "rejected" in text:
                failures.append("review_pending_notice_hides_internal_evidence_rate")
            if "raw_evidence" in text or "risk_reasons" in text:
                failures.append("review_pending_notice_hides_internal_evidence_rate")
        if "saved" in text and not (decision or {}).get("production_write_executed"):
            failures.append("review_resolution_response_truthful_rate")
        if "applied the rejected" in text:
            failures.append("review_resolution_response_truthful_rate")
        if (decision or {}).get("resolution_type") == "review_rejected_no_write" and ("applied" in text or "saved" in text):
            failures.append("review_resolution_response_truthful_rate")

    expired_items = [item for item in items if item.get("status") == "expired"]
    if expired_items:
        if not all((item.get("expiry_proof") or {}).get("production_write_executed") is False for item in expired_items):
            failures.append("expired_action_disabled_noop_rate")
        if result and (result.get("result_type") != "expired_noop" or result.get("production_write_executed") is True):
            failures.append("expired_action_disabled_noop_rate")

    if idempotency:
        if idempotency.get("duplicate_created_resolution") is not False or not idempotency.get("canonical_action_result_packet_id") or not idempotency.get("duplicate_action_submission_ids"):
            failures.append("duplicate_submission_idempotent_rate")
        if result and idempotency.get("canonical_action_result_packet_id") != result.get("action_result_packet_id"):
            failures.append("duplicate_submission_idempotent_rate")
    if stale:
        if stale.get("suppressed") is not True or stale.get("production_write_executed") is not False:
            failures.append("stale_action_suppressed_rate")
        stale_card = cards_by_id.get(stale.get("stale_user_action_card_id"))
        if stale_card and stale_card.get("display_state") == "active":
            failures.append("stale_action_suppressed_rate")

    if result:
        if result.get("post_action_task_memory_packet_id") != post.get("post_action_task_memory_packet_id"):
            failures.append("post_action_packet_matches_resolution_rate")
        if decision and result.get("governance_resolution_decision_id") != decision.get("governance_resolution_decision_id"):
            failures.append("post_action_packet_matches_resolution_rate")
        consumed = post.get("consumed_promoted_memory_ids") or []
        expected = post.get("expected_behavior")
        if expected in {"this_time_only_no_write", "declined_no_write", "expired_noop", "current_turn_only", "excluded_by_rollback", "excluded_by_blocked_state"} and memory_id in consumed:
            failures.append("post_action_packet_matches_resolution_rate")
        if expected == "write_gate_allowed" and memory_id not in consumed:
            failures.append("post_action_packet_matches_resolution_rate")
        if action in NO_WRITE_ACTIONS and memory_id in consumed:
            failures.append("post_action_packet_matches_resolution_rate")
    if daily:
        if daily.get("stale_hold_banner_present") is True or post.get("stale_hold_banner_present") is True:
            failures.append("daily_outfit_status_rebuild_rate")
        if daily.get("status") != post.get("daily_outfit_card_status"):
            failures.append("daily_outfit_status_rebuild_rate")

    if scenario in {"rollback_status", "rollback_absence", "blocked_status", "blocked_absence", "no_active_blocked"}:
        if memory_id in (post.get("consumed_promoted_memory_ids") or []) or absence.get("future_consumption_absent") is not True:
            failures.append("rollback_blocked_status_absence_proof_rate")
        if scenario in {"blocked_status", "blocked_absence", "no_active_blocked"} and absence.get("future_claims_absent") is not True:
            failures.append("rollback_blocked_status_absence_proof_rate")
        if scenario == "no_active_blocked" and any(card.get("display_state") == "active" for card in cards):
            failures.append("rollback_blocked_status_absence_proof_rate")

    result_id = (result or {}).get("action_result_packet_id")
    decision_id = (decision or {}).get("governance_resolution_decision_id")
    block_ids = {block.get("response_block_id") for block in blocks}
    claim_refs_by_block = [ref for block in blocks for ref in (block.get("claim_refs") or [])]
    claims_by_id: dict[Any, list[dict[str, Any]]] = {}
    for claim in claims:
        claims_by_id.setdefault(claim.get("claim_id"), []).append(claim)
    if result:
        response_block_ids = result.get("user_visible_response_block_ids") or []
        if not response_block_ids:
            failures.append("response_claims_trace_backed_rate")
        for response_block_id in response_block_ids:
            if response_block_id not in block_ids:
                failures.append("response_claims_trace_backed_rate")
    for claim in claims:
        refs = set(claim.get("trace_refs") or [])
        if result_id and result_id not in refs:
            failures.append("response_claims_trace_backed_rate")
        if decision_id and decision_id not in refs:
            failures.append("response_claims_trace_backed_rate")
        if claim.get("claim_id") not in claim_refs_by_block:
            failures.append("response_claims_trace_backed_rate")
    for block in blocks:
        if not block.get("trace_refs") or not block.get("claim_refs"):
            failures.append("response_claims_trace_backed_rate")
        for claim_ref in block.get("claim_refs") or []:
            if len(claims_by_id.get(claim_ref, [])) != 1:
                failures.append("response_claims_trace_backed_rate")

    audit = artifact.get("policy_surface_audit") or {}
    if _has_forbidden_text(surface) or audit.get("no_internal_review_evidence_exposed") is not True or audit.get("no_global_memory_claim") is not True or audit.get("no_unconfirmed_aspect_claim") is not True or audit.get("no_sensitive_or_internal_data") is not True or audit.get("no_commerce_or_aigc") is not True:
        failures.append("policy_safe_user_visible_text_rate")

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v138_replay_proof") or {}).get("run_v138_validation_suite") != "PASS":
        failures.append("v138_validation_replay_pass_rate")
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
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw v1.39 action-surface validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.39.independent.governance_user_action_surface_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v139/results/v139_release_candidate")
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
        write_json(result_dir / "injected_defect_detection_summary.json", {"version": "v1.39", "generated_at": now_iso(), "verdict": "pass" if detected == seeded else "fail", "seeded_defects": seeded, "detected_defects": detected, "unexpected_injected_passes": [row for row in rows if not row.get("detected")], "detected": rows})
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
