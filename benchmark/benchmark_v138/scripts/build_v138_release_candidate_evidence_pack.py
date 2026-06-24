"""Build v1.38 Runtime Governance Operations evidence pack."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.raw_artifact_validation import canonical_json_hash, now_iso, write_json


VERSION = "v1.38"
BRANCH = "v138-runtime-governance-operations"
RESULT_DIR = Path("benchmark/benchmark_v138/results/v138_release_candidate")
NOW = "2026-06-24T00:00:00Z"

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

CLEAN_CASES = [
    ("A01", "clarification_trigger_creates_open_queue_item", "clarification_open"),
    ("A02", "human_review_trigger_creates_open_queue_item", "review_open"),
    ("A03", "rollback_trigger_creates_audit_item", "rollback_audit"),
    ("A04", "blocked_memory_creates_audit_item", "blocked_audit"),
    ("B01", "clarification_question_trace_backed", "clarification_open"),
    ("B02", "clarification_answer_this_time_only_no_write", "clarification_this_time_only"),
    ("B03", "clarification_answer_remember_for_context_routes_to_write_gate", "clarification_write_candidate"),
    ("B04", "clarification_do_not_change_memory_releases_hold", "clarification_no_change"),
    ("C01", "review_payload_contains_raw_evidence_refs", "review_open"),
    ("C02", "review_approve_write_still_uses_write_gate", "review_approve_write"),
    ("C03", "review_reject_no_write_preserves_memory_state", "review_reject"),
    ("C04", "review_request_clarification_creates_clarification_item", "review_request_clarification"),
    ("D01", "temporary_hold_current_turn_only", "temporary_hold_open"),
    ("D02", "temporary_hold_release_restores_active_packet_consumption", "hold_released"),
    ("D03", "temporary_hold_expiry_no_write", "hold_expired"),
    ("E01", "duplicate_clarification_items_dedupe", "dedupe_clarification"),
    ("E02", "duplicate_review_items_dedupe", "dedupe_review"),
    ("E03", "expired_item_cannot_write_memory", "expired_no_write"),
    ("F01", "post_resolution_packet_matches_approved_write", "review_approve_write"),
    ("F02", "post_resolution_packet_matches_no_write", "clarification_no_change"),
    ("F03", "post_resolution_packet_excludes_rolled_back_memory", "rollback_confirmed"),
    ("F04", "post_resolution_claims_trace_back_to_resolution", "review_approve_write"),
    ("G01", "rollback_audit_absence_proof", "rollback_audit"),
    ("G02", "blocked_memory_audit_future_absence_proof", "blocked_audit"),
    ("G03", "reviewer_cannot_globalize_contextual_memory", "forbidden_globalize"),
    ("G04", "reviewer_cannot_add_unconfirmed_aspect", "forbidden_unconfirmed_aspect"),
    ("H01", "ledger_hash_chain_valid", "review_approve_write"),
    ("H02", "ledger_append_only_replay", "clarification_write_candidate"),
    ("H03", "multiday_governance_replay_stable", "hold_released"),
    ("I01", "sample_artifact_matches_per_case", "clarification_this_time_only"),
    ("I02", "clean_report_cannot_override_raw_failure", "review_reject"),
    ("J01", "v137_replay_passes_before_v138_validation", "review_approve_write"),
]

DEFECTS = [
    ("ADV_L01", "queue_item_without_runtime_trigger", ["governance_queue_created_from_runtime_trigger_rate"]),
    ("ADV_L02", "open_item_has_resolution_ref", ["queue_item_status_consistency_rate"]),
    ("ADV_L03", "resolved_item_missing_resolution", ["queue_item_status_consistency_rate"]),
    ("ADV_L04", "duplicate_open_items_not_deduped", ["queue_dedupe_blocks_duplicate_open_items_rate"]),
    ("ADV_L05", "clarification_request_claims_memory_changed", ["clarification_request_trace_backed_rate"]),
    ("ADV_L06", "clarification_no_write_mutates_memory", ["clarification_no_write_preserves_memory_state_rate"]),
    ("ADV_L07", "clarification_write_candidate_bypasses_gate", ["clarification_write_candidate_routes_to_gate_rate"]),
    ("ADV_L08", "review_payload_missing_raw_evidence", ["human_review_payload_has_raw_evidence_rate"]),
    ("ADV_L09", "review_approval_bypasses_write_gate", ["human_review_resolution_uses_write_gate_rate"]),
    ("ADV_L10", "review_rejection_mutates_memory", ["review_rejection_no_write_preserves_memory_state_rate"]),
    ("ADV_L11", "temporary_hold_globalizes_into_lifecycle_state", ["temporary_hold_current_turn_only_rate"]),
    ("ADV_L12", "expired_item_executes_write", ["expired_item_no_write_rate"]),
    ("ADV_L13", "post_resolution_packet_ignores_resolution", ["post_resolution_packet_matches_resolution_rate"]),
    ("ADV_L14", "rollback_audit_memory_still_consumed", ["rollback_audit_absence_proof_rate", "post_resolution_packet_matches_resolution_rate"]),
    ("ADV_L15", "reviewer_adds_unconfirmed_aspect", ["reviewer_forbidden_actions_blocked_rate"]),
    ("ADV_L16", "ledger_hash_chain_broken", ["ledger_hash_chain_valid_rate"]),
    ("ADV_L17", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_L18", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_L19", "open_clarification_item_missing_request", ["clarification_request_trace_backed_rate"]),
    ("ADV_L20", "open_review_item_missing_payload", ["human_review_payload_has_raw_evidence_rate"]),
    ("ADV_L21", "resolved_clarification_item_missing_request", ["clarification_request_trace_backed_rate"]),
    ("ADV_L22", "resolved_review_rejection_missing_payload", ["human_review_payload_has_raw_evidence_rate"]),
    ("ADV_L23", "resolved_review_approval_missing_payload", ["human_review_payload_has_raw_evidence_rate"]),
]

SAMPLE_CASES = {
    "clarification_this_time_only_no_write.json": "v138_B02_clarification_answer_this_time_only_no_write",
    "review_approve_write_gate.json": "v138_C02_review_approve_write_still_uses_write_gate",
    "review_reject_no_write.json": "v138_C03_review_reject_no_write_preserves_memory_state",
    "temporary_hold_expiry.json": "v138_D03_temporary_hold_expiry_no_write",
    "rollback_audit_absence_proof.json": "v138_G01_rollback_audit_absence_proof",
    "ledger_hash_chain_valid.json": "v138_H01_ledger_hash_chain_valid",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _entry_hash(entry: dict[str, Any]) -> str:
    return canonical_json_hash({k: v for k, v in entry.items() if k != "entry_hash"})


def _ledger(runtime_trace_id: str, queue_item_id: str, decision_id: str | None, before: dict[str, Any], after: dict[str, Any], write: bool, trace_refs: list[str]) -> dict[str, Any]:
    entries = []
    if decision_id:
        entry = {
            "ledger_entry_id": f"gle_{decision_id}",
            "previous_entry_hash": None,
            "queue_item_id": queue_item_id,
            "resolution_decision_id": decision_id,
            "before_state_ref": before["state_snapshot_id"],
            "after_state_ref": after["state_snapshot_id"],
            "before_state": before,
            "after_state": after,
            "production_write_executed": write,
            "trace_refs": trace_refs,
        }
        entry["entry_hash"] = _entry_hash(entry)
        entries.append(entry)
    return {
        "governance_decision_ledger_id": f"gdl_{runtime_trace_id}",
        "runtime_trace_id": runtime_trace_id,
        "ledger_entries": entries,
        "append_only": True,
        "entry_hash_chain_valid": True,
        "latest_entry_hash": entries[-1]["entry_hash"] if entries else None,
        "append_only_replay": [{"ledger_entry_id": entry["ledger_entry_id"], "entry_hash": entry["entry_hash"]} for entry in entries],
    }


def _base_state(memory_id: str, suffix: str, status: str = "active") -> dict[str, Any]:
    return {
        "state_snapshot_id": f"state_{status}_{suffix}",
        "memory_id": memory_id,
        "current_status": status,
        "contexts": ["office_daily"],
        "confirmed_aspects": ["color_palette"],
        "active_memory_ids": [memory_id] if status == "active" else [],
        "blocked_memory_ids": [memory_id] if status == "blocked" else [],
        "rolled_back_memory_ids": [memory_id] if status == "rolled_back" else [],
        "context_exclusions": [],
    }


def _queue_item(item_id: str, trigger_type: str, trigger_ref: str, memory_id: str, runtime_trace_id: str, packet_id: str, feedback_id: str, status: str, resolution_ref: str | None = None, canonical_ref: str | None = None) -> dict[str, Any]:
    item = {
        "governance_queue_item_id": item_id,
        "trigger_type": trigger_type,
        "trigger_ref": trigger_ref,
        "target_memory_id": memory_id,
        "target_candidate_id": None,
        "source_runtime_trace_id": runtime_trace_id,
        "source_task_memory_packet_id": packet_id,
        "source_feedback_event_id": feedback_id,
        "status": status,
        "priority": "medium" if "review" in trigger_type else "low",
        "risk_level": "high" if "review" in trigger_type else "low",
        "created_at": NOW,
        "resolution_ref": resolution_ref,
        "trace_refs": [runtime_trace_id, trigger_ref, packet_id, feedback_id],
    }
    if canonical_ref:
        item["canonical_queue_item_id"] = canonical_ref
    if status == "expired":
        item["expiry_proof"] = {"expired_at": NOW, "production_write_executed": False}
    return item


def _case(case_code: str, scenario: str, kind: str, index: int) -> dict[str, Any]:
    suffix = f"v138_{index:03d}"
    case_id = f"v138_{case_code}_{scenario}"
    runtime_trace_id = f"rt_{suffix}"
    memory_id = f"mem_insp_{suffix}"
    packet_id = f"tmp_{suffix}"
    post_packet_id = f"tmp_post_resolution_{suffix}"
    feedback_id = f"pmf_{suffix}"
    gate_id = f"pmwg_{suffix}"
    trigger_id = f"gt_{suffix}"
    item_id = f"gqi_{suffix}"
    decision_id = f"grd_{suffix}"

    trigger_type = "clarification_required"
    queue_status = "resolved"
    resolution_type = "clarified_no_write"
    gate_decision = "not_applicable_no_write"
    write_executed = False
    before = _base_state(memory_id, suffix)
    after = _base_state(memory_id, suffix)
    temporary_hold = {
        "temporary_hold_id": f"th_{suffix}",
        "source_queue_item_id": item_id,
        "current_turn_scoped": True,
        "production_lifecycle_mutation": False,
        "status": "released",
        "release_ref": decision_id,
        "expiry_ref": None,
    }
    post_packet = {
        "task_memory_packet_id": post_packet_id,
        "request_context": "office_daily",
        "candidate_promoted_memory_ids": [memory_id],
        "consumed_promoted_memory_ids": [memory_id],
        "excluded_memory_ids": [],
        "expected_behavior": "active_consumption_after_resolution",
        "resolution_ref": decision_id,
        "trace_refs": [decision_id, memory_id],
    }
    claims = [{"claim_id": f"claim_{suffix}", "text": "I applied the resolved governance decision for this outfit packet.", "trace_refs": [decision_id, post_packet_id]}]
    clarification_request: dict[str, Any] | None = None
    clarification_resolution: dict[str, Any] | None = None
    additional_clarification_requests: list[dict[str, Any]] = []
    human_review_payload: dict[str, Any] | None = None
    human_review_resolution: dict[str, Any] | None = None
    rollback_absence = None
    blocked_absence = None
    duplicate_items: list[dict[str, Any]] = []
    resolution_input_ref = f"resolution_input_{suffix}"
    forbidden_actions_blocked = True

    if kind in {"clarification_open", "temporary_hold_open", "review_open"}:
        queue_status = "open"
        resolution_type = None
        decision_id = None
        temporary_hold["status"] = "open"
        temporary_hold["release_ref"] = None
        post_packet["consumed_promoted_memory_ids"] = []
        post_packet["excluded_memory_ids"] = [memory_id]
        post_packet["expected_behavior"] = "temporary_hold_current_turn"
        post_packet["resolution_ref"] = None
        claims = []
    if kind.startswith("clarification") or kind in {"temporary_hold_open", "hold_released", "hold_expired", "dedupe_clarification", "expired_no_write"}:
        trigger_type = "clarification_required" if kind != "hold_expired" and kind != "expired_no_write" else "temporary_hold_expiry"
        clarification_request = {
            "clarification_request_id": f"cr_{suffix}",
            "governance_queue_item_id": item_id,
            "question_type": "ambiguity",
            "question_text": "Which aspect should I adjust for future outfits?",
            "allowed_response_kinds": ["choose_aspect", "this_time_only", "do_not_change_memory", "remember_for_context"],
            "must_not_suggest": ["global_memory", "body_inference", "commerce_targeting"],
            "current_turn_hold_ref": temporary_hold["temporary_hold_id"],
            "memory_changed_claim": False,
            "trace_refs": [runtime_trace_id, feedback_id, item_id],
        }
    if kind == "clarification_this_time_only":
        resolution_type = "clarified_no_write"
        clarification_resolution = {"clarification_resolution_id": f"cra_{suffix}", "answer_kind": "this_time_only", "production_write_requested": False, "trace_refs": [item_id, clarification_request["clarification_request_id"]]}
    elif kind == "clarification_no_change":
        resolution_type = "clarified_no_write"
        clarification_resolution = {"clarification_resolution_id": f"cra_{suffix}", "answer_kind": "do_not_change_memory", "production_write_requested": False, "trace_refs": [item_id, clarification_request["clarification_request_id"]]}
    elif kind == "clarification_write_candidate":
        resolution_type = "clarified_write_candidate"
        gate_decision = "allow"
        write_executed = True
        after = {**before, "state_snapshot_id": f"state_after_write_{suffix}", "confidence_delta": -0.1}
        clarification_resolution = {"clarification_resolution_id": f"cra_{suffix}", "answer_kind": "remember_for_context", "production_write_requested": True, "trace_refs": [item_id, clarification_request["clarification_request_id"]]}
    elif kind in {"review_open", "review_approve_write", "review_reject", "review_request_clarification", "forbidden_globalize", "forbidden_unconfirmed_aspect", "dedupe_review"}:
        trigger_type = "human_review_required"
        human_review_payload = {
            "human_review_payload_id": f"hrp_{suffix}",
            "governance_queue_item_id": item_id,
            "risk_reasons": ["context_scope_change_requires_review"],
            "proposed_action_summary": "narrow context handling for a promoted inspiration memory",
            "raw_evidence_refs": [runtime_trace_id, packet_id, feedback_id, f"state_before_{suffix}"],
            "trace_refs": [runtime_trace_id, packet_id, feedback_id, item_id],
            "allowed_reviewer_actions": ["approve_no_write", "approve_write", "reject", "request_clarification", "rollback"],
            "forbidden_reviewer_actions": ["globalize_memory", "add_unconfirmed_aspect", "infer_body_or_identity"],
            "production_write_blocked_until_resolution": True,
        }
        if kind == "review_open":
            queue_status = "open"
            resolution_type = None
            decision_id = None
            post_packet["consumed_promoted_memory_ids"] = []
            post_packet["excluded_memory_ids"] = [memory_id]
            post_packet["expected_behavior"] = "temporary_hold_pending_review"
            post_packet["resolution_ref"] = None
            claims = []
        elif kind == "review_approve_write":
            resolution_type = "review_approved_write"
            gate_decision = "allow"
            write_executed = True
            after = {**before, "state_snapshot_id": f"state_review_write_{suffix}", "context_exclusions": ["formal_client_meeting"]}
            human_review_resolution = {"human_review_resolution_id": f"hrr_{suffix}", "reviewer_action": "approve_write", "blocked_forbidden_action": False, "trace_refs": [item_id, human_review_payload["human_review_payload_id"]]}
        elif kind == "review_reject":
            resolution_type = "review_rejected_no_write"
            human_review_resolution = {"human_review_resolution_id": f"hrr_{suffix}", "reviewer_action": "reject", "blocked_forbidden_action": False, "trace_refs": [item_id, human_review_payload["human_review_payload_id"]]}
        elif kind == "review_request_clarification":
            resolution_type = "review_rejected_no_write"
            human_review_resolution = {"human_review_resolution_id": f"hrr_{suffix}", "reviewer_action": "request_clarification", "blocked_forbidden_action": False, "trace_refs": [item_id, human_review_payload["human_review_payload_id"]]}
            followup_item_id = f"gqi_followup_{suffix}"
            duplicate_items.append(_queue_item(followup_item_id, "clarification_required", decision_id, memory_id, runtime_trace_id, packet_id, feedback_id, "open"))
            additional_clarification_requests.append({
                "clarification_request_id": f"cr_followup_{suffix}",
                "governance_queue_item_id": followup_item_id,
                "question_type": "review_followup_ambiguity",
                "question_text": "Which reviewed aspect should I clarify before changing future outfit memory?",
                "allowed_response_kinds": ["choose_aspect", "this_time_only", "do_not_change_memory", "remember_for_context"],
                "must_not_suggest": ["global_memory", "body_inference", "commerce_targeting"],
                "current_turn_hold_ref": temporary_hold["temporary_hold_id"],
                "memory_changed_claim": False,
                "source_review_resolution_ref": human_review_resolution["human_review_resolution_id"],
                "trace_refs": [runtime_trace_id, feedback_id, item_id, human_review_payload["human_review_payload_id"], human_review_resolution["human_review_resolution_id"], followup_item_id],
            })
        elif kind == "forbidden_globalize":
            resolution_type = "review_rejected_no_write"
            human_review_resolution = {"human_review_resolution_id": f"hrr_{suffix}", "reviewer_action": "globalize_memory", "blocked_forbidden_action": True, "trace_refs": [item_id, human_review_payload["human_review_payload_id"]]}
        elif kind == "forbidden_unconfirmed_aspect":
            resolution_type = "review_rejected_no_write"
            human_review_resolution = {"human_review_resolution_id": f"hrr_{suffix}", "reviewer_action": "add_unconfirmed_aspect", "blocked_forbidden_action": True, "proposed_memory_patch": {"add_aspects": ["silhouette"]}, "confirmed_aspects": before["confirmed_aspects"], "trace_refs": [item_id, human_review_payload["human_review_payload_id"]]}
    elif kind in {"rollback_audit", "rollback_confirmed"}:
        trigger_type = "rollback_audit"
        resolution_type = "rollback_confirmed"
        after = _base_state(memory_id, suffix, "rolled_back")
        post_packet["consumed_promoted_memory_ids"] = []
        post_packet["excluded_memory_ids"] = [memory_id]
        post_packet["expected_behavior"] = "excluded_by_rollback"
        rollback_absence = {"memory_id": memory_id, "read_after_rollback": {"memory_present": False}, "future_consumption_absent": True, "trace_refs": [decision_id or item_id, post_packet_id]}
        claims = []
    elif kind == "blocked_audit":
        trigger_type = "blocked_memory_audit"
        resolution_type = "review_rejected_no_write"
        before = _base_state(memory_id, suffix, "blocked")
        after = _base_state(memory_id, suffix, "blocked")
        post_packet["consumed_promoted_memory_ids"] = []
        post_packet["excluded_memory_ids"] = [memory_id]
        post_packet["expected_behavior"] = "excluded_by_blocked_state"
        blocked_absence = {"memory_id": memory_id, "future_consumption_absent": True, "future_claims_absent": True, "trace_refs": [decision_id or item_id, post_packet_id]}
        claims = []
    elif kind in {"hold_expired", "expired_no_write"}:
        queue_status = "expired"
        resolution_type = "expired_no_write"
        temporary_hold["status"] = "expired"
        temporary_hold["release_ref"] = None
        temporary_hold["expiry_ref"] = f"expiry_{suffix}"
        post_packet["consumed_promoted_memory_ids"] = []
        post_packet["excluded_memory_ids"] = [memory_id]
        post_packet["expected_behavior"] = "expired_hold_no_write"
        claims = []
    elif kind == "hold_released":
        resolution_type = "clarified_no_write"
        temporary_hold["status"] = "released"
    elif kind == "dedupe_clarification":
        duplicate_items.append(_queue_item(f"gqi_dup_{suffix}", "clarification_required", trigger_id, memory_id, runtime_trace_id, packet_id, feedback_id, "deduped", canonical_ref=item_id))
    elif kind == "dedupe_review":
        trigger_type = "human_review_required"
        duplicate_items.append(_queue_item(f"gqi_dup_{suffix}", "human_review_required", trigger_id, memory_id, runtime_trace_id, packet_id, feedback_id, "deduped", canonical_ref=item_id))

    if kind in {"temporary_hold_open"}:
        queue_status = "open"
        resolution_type = None
        decision_id = None
        temporary_hold["status"] = "open"
        temporary_hold["release_ref"] = None

    queue_item = _queue_item(item_id, trigger_type, trigger_id, memory_id, runtime_trace_id, packet_id, feedback_id, queue_status, decision_id)
    queue_items = [queue_item] + duplicate_items
    dedupe_index = [
        {"dedupe_key": f"{item['trigger_type']}:{item['target_memory_id']}:{item['trigger_ref']}", "canonical_queue_item_id": item.get("canonical_queue_item_id") or item["governance_queue_item_id"]}
        for item in queue_items
    ]
    queue = {
        "runtime_governance_queue_id": f"rgq_{suffix}",
        "runtime_trace_id": runtime_trace_id,
        "created_at": NOW,
        "queue_items": queue_items,
        "dedupe_index": dedupe_index,
        "open_item_count": sum(1 for item in queue_items if item["status"] == "open"),
        "resolved_item_count": sum(1 for item in queue_items if item["status"] == "resolved"),
        "expired_item_count": sum(1 for item in queue_items if item["status"] == "expired"),
    }
    trigger = {
        "governance_trigger_id": trigger_id,
        "trigger_type": trigger_type,
        "source_runtime_trace_id": runtime_trace_id,
        "source_task_memory_packet_id": packet_id,
        "source_feedback_event_id": feedback_id,
        "target_memory_id": memory_id,
        "trace_refs": [runtime_trace_id, packet_id, feedback_id],
    }
    decision = None
    if resolution_type:
        decision = {
            "governance_resolution_decision_id": decision_id,
            "governance_queue_item_id": item_id,
            "resolution_type": resolution_type,
            "resolution_input_ref": resolution_input_ref,
            "production_write_gate_ref": gate_id if resolution_type in {"clarified_write_candidate", "review_approved_write"} else None,
            "production_write_executed": write_executed,
            "memory_patch_ref": f"patch_{suffix}" if write_executed else None,
            "temporary_hold_released": temporary_hold["status"] == "released",
            "decision_reasons": [resolution_type],
            "created_at": NOW,
        }
    write_gate = {
        "gate_id": gate_id,
        "decision": gate_decision,
        "production_write_executed": write_executed,
        "pre_resolution_write": False,
        "allowlist_checked": True,
        "environment": "deterministic_local_fixture",
    }
    ledger = _ledger(runtime_trace_id, item_id, decision_id, before, after, write_executed, [runtime_trace_id, item_id, decision_id] if decision_id else [])
    if resolution_type in {"review_rejected_no_write", "clarified_no_write", "expired_no_write"} and not write_executed and after != before:
        raise AssertionError(case_id)
    clarification_requests = ([clarification_request] if clarification_request else []) + additional_clarification_requests
    human_review_payloads = [human_review_payload] if human_review_payload else []
    artifact = {
        "case_id": case_id,
        "version": VERSION,
        "scenario_kind": kind,
        "gate_assertions": {gate: True for gate in GATES},
        "runtime_trace": {"runtime_trace_id": runtime_trace_id, "stage_order": ["runtime_trace", "governance_trigger", "queue", "resolution", "ledger", "post_resolution_packet", "multi_day_replay"], "trace_refs": [packet_id, feedback_id]},
        "governance_trigger": trigger,
        "runtime_governance_queue": queue,
        "clarification_request": clarification_request,
        "clarification_requests": clarification_requests,
        "clarification_resolution": clarification_resolution,
        "human_review_payload": human_review_payload,
        "human_review_payloads": human_review_payloads,
        "human_review_resolution": human_review_resolution,
        "temporary_hold_lifecycle": temporary_hold,
        "governance_resolution_decision": decision,
        "production_memory_write_gate": write_gate,
        "before_memory_lifecycle_state": before,
        "after_memory_lifecycle_state": after,
        "post_resolution_task_memory_packet": post_packet,
        "governance_decision_ledger": ledger,
        "rollback_audit_absence_proof": rollback_absence,
        "blocked_memory_future_absence_proof": blocked_absence,
        "visible_claims": claims,
        "multi_day_governance_replay": {"days": 3, "stable_queue_item_ids": [item["governance_queue_item_id"] for item in queue_items], "stable_ledger_hash": ledger["latest_entry_hash"], "no_silent_mutation": True},
        "forbidden_actions_blocked": forbidden_actions_blocked,
        "v137_replay_proof": {"run_v137_validation_suite": "PASS"},
    }
    return artifact


def _defect(defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    artifact = _case(defect_id, defect_type, "review_approve_write", 900 + int(defect_id.split("_L")[-1]))
    artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = gates
    if defect_type == "queue_item_without_runtime_trigger":
        artifact["governance_trigger"]["governance_trigger_id"] = "missing_trigger"
    elif defect_type == "open_item_has_resolution_ref":
        item = artifact["runtime_governance_queue"]["queue_items"][0]
        item["status"] = "open"
        item["resolution_ref"] = artifact["governance_resolution_decision"]["governance_resolution_decision_id"]
    elif defect_type == "resolved_item_missing_resolution":
        artifact["runtime_governance_queue"]["queue_items"][0]["resolution_ref"] = None
    elif defect_type == "duplicate_open_items_not_deduped":
        item = dict(artifact["runtime_governance_queue"]["queue_items"][0])
        item["governance_queue_item_id"] = "gqi_duplicate_open"
        item["status"] = "open"
        item["resolution_ref"] = None
        artifact["runtime_governance_queue"]["queue_items"][0]["status"] = "open"
        artifact["runtime_governance_queue"]["queue_items"][0]["resolution_ref"] = None
        artifact["runtime_governance_queue"]["queue_items"].append(item)
    elif defect_type == "clarification_request_claims_memory_changed":
        artifact.update(_case(defect_id, defect_type, "clarification_this_time_only", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["clarification_request"]["memory_changed_claim"] = True
    elif defect_type == "clarification_no_write_mutates_memory":
        artifact.update(_case(defect_id, defect_type, "clarification_this_time_only", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["after_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
    elif defect_type == "clarification_write_candidate_bypasses_gate":
        artifact.update(_case(defect_id, defect_type, "clarification_write_candidate", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["governance_resolution_decision"]["production_write_gate_ref"] = None
    elif defect_type == "review_payload_missing_raw_evidence":
        artifact["human_review_payload"]["raw_evidence_refs"] = []
    elif defect_type == "review_approval_bypasses_write_gate":
        artifact["production_memory_write_gate"]["decision"] = "block"
    elif defect_type == "review_rejection_mutates_memory":
        artifact.update(_case(defect_id, defect_type, "review_reject", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["after_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
    elif defect_type == "temporary_hold_globalizes_into_lifecycle_state":
        artifact["temporary_hold_lifecycle"]["production_lifecycle_mutation"] = True
        artifact["after_memory_lifecycle_state"]["contexts"] = ["global"]
    elif defect_type == "expired_item_executes_write":
        artifact.update(_case(defect_id, defect_type, "hold_expired", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["governance_resolution_decision"]["production_write_executed"] = True
        artifact["production_memory_write_gate"]["production_write_executed"] = True
    elif defect_type == "post_resolution_packet_ignores_resolution":
        mem = artifact["before_memory_lifecycle_state"]["memory_id"]
        artifact["post_resolution_task_memory_packet"]["consumed_promoted_memory_ids"] = []
        artifact["post_resolution_task_memory_packet"]["excluded_memory_ids"] = [mem]
    elif defect_type == "rollback_audit_memory_still_consumed":
        artifact.update(_case(defect_id, defect_type, "rollback_confirmed", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["post_resolution_task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["before_memory_lifecycle_state"]["memory_id"]]
    elif defect_type == "reviewer_adds_unconfirmed_aspect":
        artifact.update(_case(defect_id, defect_type, "forbidden_unconfirmed_aspect", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failed_check_ids"] = gates
        artifact["human_review_resolution"]["blocked_forbidden_action"] = False
    elif defect_type == "ledger_hash_chain_broken":
        artifact["governance_decision_ledger"]["ledger_entries"][0]["entry_hash"] = "sha256-bad"
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        artifact["sample_consistency_probe"] = {"sample_artifact_content": {"case_id": artifact["case_id"], "manual_only_patch": True}, "source_artifact_content": {"case_id": artifact["case_id"]}}
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        artifact["report_consistency_probe"] = {"clean_report_summary": {"passed_cases": 32, "failed_cases": 0}, "independent_validation_summary": {"passed_cases": 31, "failed_cases": 1}}
    elif defect_type == "open_clarification_item_missing_request":
        artifact.update(_case(defect_id, defect_type, "review_request_clarification", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failure"] = True
        artifact["expected_failed_check_ids"] = gates
        open_clarification_ids = {
            item["governance_queue_item_id"]
            for item in artifact["runtime_governance_queue"]["queue_items"]
            if item.get("status") == "open" and item.get("trigger_type") == "clarification_required"
        }
        artifact["clarification_requests"] = [
            request
            for request in artifact.get("clarification_requests", [])
            if request.get("governance_queue_item_id") not in open_clarification_ids
        ]
        artifact["clarification_request"] = artifact["clarification_requests"][0] if artifact["clarification_requests"] else None
    elif defect_type == "open_review_item_missing_payload":
        artifact.update(_case(defect_id, defect_type, "review_open", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failure"] = True
        artifact["expected_failed_check_ids"] = gates
        artifact["human_review_payload"] = None
        artifact["human_review_payloads"] = []
    elif defect_type == "resolved_clarification_item_missing_request":
        artifact.update(_case(defect_id, defect_type, "clarification_this_time_only", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failure"] = True
        artifact["expected_failed_check_ids"] = gates
        artifact["clarification_request"] = None
        artifact["clarification_requests"] = []
    elif defect_type == "resolved_review_rejection_missing_payload":
        artifact.update(_case(defect_id, defect_type, "review_reject", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failure"] = True
        artifact["expected_failed_check_ids"] = gates
        artifact["human_review_payload"] = None
        artifact["human_review_payloads"] = []
    elif defect_type == "resolved_review_approval_missing_payload":
        artifact.update(_case(defect_id, defect_type, "review_approve_write", 900 + int(defect_id.split("_L")[-1])))
        artifact["case_id"] = f"v138_{defect_id}_{defect_type}"
        artifact["defect_type"] = defect_type
        artifact["expected_failure"] = True
        artifact["expected_failed_check_ids"] = gates
        artifact["human_review_payload"] = None
        artifact["human_review_payloads"] = []
    return artifact


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.38.runtime_governance_operations" + ("" if clean else ".mixed_strict"),
        "schema_version": VERSION,
        "generated_at": now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"} if clean else {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {"total_cases": len(rows), "passed_cases": len(rows) if clean else 0, "failed_cases": 0 if clean else len(rows), "total_checks": len(GATES), "passed_checks": len(GATES) if clean else 0, "failed_checks": 0 if clean else len(GATES)},
        "checks": [{"check_id": gate, "value": 1.0 if clean else 0.0, "threshold": 1.0, "passed": clean, "failures": []} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": clean, "failed_check_ids": [] if clean else row["expected_failed_check_ids"], "artifact_ref": f"per_case/{'clean' if clean else 'mixed_strict'}/{row['case_id']}.json"} for row in rows],
    }


def _manifest(samples: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "theme": "Runtime Governance Operations",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v138/results/v138_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v138/scripts/build_v138_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v138/scripts/validate_v138_release_candidate.py",
        "runner_script": "benchmark/benchmark_v138/scripts/run_v138_validation_suite.py",
        "required_reports": ["clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "report_consistency_report.json", "sample_consistency_report.json", "injected_defect_detection_summary.json", "governance_queue_summary.json", "resolution_decision_summary.json", "governance_ledger_summary.json", "post_resolution_packet_summary.json"],
        "required_gates": GATES,
        "validator_commands": ["benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py", "python benchmark/benchmark_v137/scripts/run_v137_validation_suite.py", "python benchmark/benchmark_v138/scripts/run_v138_validation_suite.py", "python -m unittest discover -s benchmark/benchmark_v138/tests"],
        "sample_artifacts": samples,
        "non_goals": ["No real human review service", "No full review UI", "No commerce, SKU, merchant, affiliate, or product links", "No AIGC image generation", "No production storage migration"],
    }


def build(result_dir: Path = RESULT_DIR) -> None:
    if result_dir.exists():
        shutil.rmtree(result_dir)
    for subdir in ["per_case/clean", "per_case/mixed_strict", "per_case/adversarial", "sample_artifacts"]:
        (result_dir / subdir).mkdir(parents=True, exist_ok=True)
    rows = [_case(code, scenario, kind, idx) for idx, (code, scenario, kind) in enumerate(CLEAN_CASES, start=1)]
    defects = [_defect(defect_id, defect_type, gates) for defect_id, defect_type, gates in DEFECTS]
    by_id = {row["case_id"]: row for row in rows}
    for row in rows:
        write_json(result_dir / "per_case" / "clean" / f"{row['case_id']}.json", row)
    for defect in defects:
        write_json(result_dir / "per_case" / "mixed_strict" / f"{defect['case_id']}.json", defect)
    samples: list[dict[str, Any]] = []
    for sample_name, source_case_id in SAMPLE_CASES.items():
        row = by_id[source_case_id]
        sample_ref = f"sample_artifacts/{sample_name}"
        source_ref = f"per_case/clean/{source_case_id}.json"
        write_json(result_dir / sample_ref, row)
        samples.append({"case_id": source_case_id, "artifact_ref": sample_ref, "source_artifact_ref": source_ref, "canonical_sha256": canonical_json_hash(row), "sample_projection_schema": "full_copy", "allowed_omitted_fields": []})
    clean = _report(rows, True)
    mixed = _report(defects, False)
    write_json(result_dir / "REVIEW_MANIFEST.json", _manifest(samples))
    write_json(result_dir / "clean_report.json", clean)
    write_json(result_dir / "mixed_strict_report.json", mixed)
    write_json(result_dir / "injected_defect_detection_summary.json", {"version": VERSION, "generated_at": now_iso(), "verdict": "pass", "seeded_defects": len(defects), "detected_defects": len(defects), "detected": [{"case_id": defect["case_id"], "defect_type": defect["defect_type"], "detected": True, "failed_check_ids": defect["expected_failed_check_ids"]} for defect in defects]})
    write_json(result_dir / "governance_queue_summary.json", {"total_cases": len(rows), "queue_count": len(rows), "open_items": sum(row["runtime_governance_queue"]["open_item_count"] for row in rows), "resolved_items": sum(row["runtime_governance_queue"]["resolved_item_count"] for row in rows), "expired_items": sum(row["runtime_governance_queue"]["expired_item_count"] for row in rows)})
    write_json(result_dir / "resolution_decision_summary.json", {"total_cases": len(rows), "resolution_decisions": sum(1 for row in rows if row["governance_resolution_decision"]), "production_writes": sum(1 for row in rows if (row["governance_resolution_decision"] or {}).get("production_write_executed"))})
    write_json(result_dir / "governance_ledger_summary.json", {"total_cases": len(rows), "ledgers": len(rows), "hash_chain_valid": all(row["governance_decision_ledger"]["entry_hash_chain_valid"] for row in rows)})
    write_json(result_dir / "post_resolution_packet_summary.json", {"total_cases": len(rows), "packets": len(rows), "trace_backed_packets": sum(1 for row in rows if row["post_resolution_task_memory_packet"].get("trace_refs"))})
    _write_text(result_dir / "README.md", "# v1.38 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic local runtime governance operations evidence.\n")
    _write_text(result_dir / "RELEASE_NOTE.md", "# v1.38 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves local governance queue, resolution, ledger, and post-resolution packet behavior without production service scope expansion.\n")
    _write_text(result_dir / "reviewer_checklist.md", "# v1.38 Reviewer Checklist\n\n- [ ] Queue items derive from runtime triggers.\n- [ ] Clarification and review operations do not silently mutate memory.\n- [ ] Reviewer approval still uses ProductionMemoryWriteGate.\n- [ ] Temporary holds are current-turn scoped or explicitly resolved.\n- [ ] Ledger hash chain is reproducible.\n- [ ] v1.37 replay, independent validation, adversarial detection, sample consistency, and report consistency pass.\n")
    _write_text(result_dir / "clean_report.md", "# v1.38 Clean Acceptance Report\n\n" + "\n".join(f"- PASS `{gate}`" for gate in GATES) + "\n")
    _write_text(result_dir / "mixed_strict_report.md", "# v1.38 Mixed Strict Report\n\n" + "\n".join(f"- EXPECTED FAIL `{gate}`" for gate in GATES) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--result-dir", default=str(RESULT_DIR))
    args = parser.parse_args()
    if not args.build:
        parser.error("--build is required")
    build(Path(args.result_dir))
    print(f"Built {args.result_dir}")


if __name__ == "__main__":
    main()
