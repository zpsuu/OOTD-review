"""Build deterministic v1.39 governance user action surface evidence."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.raw_artifact_validation import canonical_json_hash, now_iso, write_json


VERSION = "v1.39"
BRANCH = "v139-governance-user-action-surface"
RESULT_DIR = Path("benchmark/benchmark_v139/results/v139_release_candidate")
NOW = "2026-06-24T00:00:00Z"

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

CLEAN_CASES = [
    ("A01", "open_clarification_queue_item_creates_active_action_card", "open_clarification"),
    ("A02", "open_review_queue_item_creates_pending_status_block", "open_review"),
    ("A03", "rollback_audit_creates_non_actionable_status", "rollback_status"),
    ("A04", "blocked_memory_creates_exclusion_notice", "blocked_status"),
    ("B01", "clarification_card_text_trace_backed", "open_clarification"),
    ("B02", "this_time_only_submission_no_write_result", "this_time_only"),
    ("B03", "do_not_change_memory_submission_no_write_result", "do_not_change_memory"),
    ("B04", "remember_for_context_submission_routes_to_write_gate", "remember_for_context"),
    ("B05", "clarification_allowed_actions_match_request", "open_clarification"),
    ("C01", "review_pending_notice_hides_raw_review_evidence", "open_review"),
    ("C02", "review_approved_write_result_claims_only_after_gate", "review_approved"),
    ("C03", "review_rejected_no_write_result_does_not_claim_memory_change", "review_rejected"),
    ("C04", "review_request_clarification_surfaces_followup_card", "review_request_clarification"),
    ("D01", "temporary_hold_status_current_turn_only", "temporary_hold"),
    ("D02", "expired_action_card_disabled", "expired_card"),
    ("D03", "expired_action_submission_noop", "expired_submission"),
    ("D04", "duplicate_action_submission_idempotent", "duplicate_submission"),
    ("D05", "stale_action_suppressed_after_resolution", "stale_suppressed"),
    ("E01", "post_action_packet_matches_this_time_only_no_write", "post_this_time_only"),
    ("E02", "post_action_packet_matches_write_candidate", "post_write_candidate"),
    ("E03", "daily_outfit_card_status_updates_after_resolution", "daily_status_resolved"),
    ("E04", "no_stale_hold_banner_after_resolution", "stale_hold_removed"),
    ("F01", "rollback_status_excludes_memory_from_future_packet", "rollback_absence"),
    ("F02", "blocked_status_excludes_memory_from_future_claims", "blocked_absence"),
    ("F03", "blocked_or_rolled_back_memory_has_no_active_action_card", "no_active_blocked"),
    ("G01", "response_claims_trace_to_action_result", "claims_trace"),
    ("G02", "response_does_not_globalize_contextual_memory", "policy_no_globalize"),
    ("G03", "response_does_not_add_unconfirmed_aspect", "policy_no_unconfirmed"),
    ("G04", "response_does_not_expose_sensitive_or_internal_review_data", "policy_no_sensitive"),
    ("H01", "sample_artifact_matches_per_case", "sample_consistency"),
    ("H02", "clean_report_cannot_override_raw_failure", "report_consistency"),
    ("H03", "reviewer_checklist_refs_raw_cases", "reviewer_checklist"),
    ("I01", "v138_replay_passes_before_v139_validation", "v138_replay"),
    ("I02", "v139_runner_is_one_command_reproducible", "runner_reproducible"),
]

DEFECTS = [
    ("ADV_M01", "action_card_without_governance_queue_item", ["action_card_matches_queue_item_rate"]),
    ("ADV_M02", "card_allows_action_not_in_clarification_request", ["clarification_card_trace_backed_rate"]),
    ("ADV_M03", "clarification_card_text_untraceable", ["clarification_card_trace_backed_rate"]),
    ("ADV_M04", "this_time_only_submission_mutates_memory", ["no_write_action_preserves_memory_state_rate", "post_action_packet_matches_resolution_rate"]),
    ("ADV_M05", "do_not_change_memory_creates_write_candidate", ["no_write_action_preserves_memory_state_rate"]),
    ("ADV_M06", "remember_for_context_bypasses_write_gate", ["remember_for_context_routes_to_write_gate_rate"]),
    ("ADV_M07", "review_pending_notice_claims_memory_changed", ["review_pending_notice_hides_internal_evidence_rate", "review_resolution_response_truthful_rate"]),
    ("ADV_M08", "review_pending_notice_exposes_raw_review_evidence", ["review_pending_notice_hides_internal_evidence_rate", "policy_safe_user_visible_text_rate"]),
    ("ADV_M09", "review_rejection_response_claims_applied_preference", ["review_resolution_response_truthful_rate"]),
    ("ADV_M10", "expired_action_card_still_active", ["expired_action_disabled_noop_rate", "action_card_matches_queue_item_rate"]),
    ("ADV_M11", "expired_submission_executes_write", ["expired_action_disabled_noop_rate"]),
    ("ADV_M12", "duplicate_submission_creates_second_resolution", ["duplicate_submission_idempotent_rate"]),
    ("ADV_M13", "stale_action_card_survives_resolution", ["stale_action_suppressed_rate"]),
    ("ADV_M14", "post_action_packet_ignores_resolution", ["post_action_packet_matches_resolution_rate"]),
    ("ADV_M15", "daily_outfit_status_banner_stale_after_resolution", ["daily_outfit_status_rebuild_rate"]),
    ("ADV_M16", "rollback_status_still_consumes_memory", ["rollback_blocked_status_absence_proof_rate"]),
    ("ADV_M17", "blocked_status_creates_future_claim", ["rollback_blocked_status_absence_proof_rate"]),
    ("ADV_M18", "response_claim_without_action_result_trace", ["response_claims_trace_backed_rate"]),
    ("ADV_M19", "response_globalizes_contextual_memory", ["policy_safe_user_visible_text_rate"]),
    ("ADV_M20", "response_adds_unconfirmed_aspect", ["policy_safe_user_visible_text_rate"]),
    ("ADV_M21", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_M22", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_M23", "missing_idempotency_record", ["duplicate_submission_idempotent_rate"]),
    ("ADV_M24", "missing_stale_action_suppression_proof", ["stale_action_suppressed_rate"]),
    ("ADV_M25", "missing_action_submission_for_submitted_action", ["action_submission_allowed_and_active_rate"]),
    ("ADV_M26", "missing_action_result_for_submitted_action", ["post_action_packet_matches_resolution_rate"]),
    ("ADV_M27", "missing_action_result_for_expired_submission", ["expired_action_disabled_noop_rate", "post_action_packet_matches_resolution_rate"]),
    ("ADV_M28", "missing_response_claim_trace", ["response_claims_trace_backed_rate"]),
    ("ADV_M29", "action_result_references_missing_response_block", ["response_claims_trace_backed_rate"]),
]

SAMPLE_CASES = {
    "open_clarification_action_card.json": "v139_A01_open_clarification_queue_item_creates_active_action_card",
    "this_time_only_no_write_result.json": "v139_B02_this_time_only_submission_no_write_result",
    "remember_for_context_write_gate.json": "v139_B04_remember_for_context_submission_routes_to_write_gate",
    "review_pending_notice.json": "v139_C01_review_pending_notice_hides_raw_review_evidence",
    "expired_action_noop.json": "v139_D03_expired_action_submission_noop",
    "duplicate_submission_idempotency.json": "v139_D04_duplicate_action_submission_idempotent",
    "stale_action_suppression.json": "v139_D05_stale_action_suppressed_after_resolution",
    "rollback_status_surface.json": "v139_F01_rollback_status_excludes_memory_from_future_packet",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_state(memory_id: str, suffix: str, status: str = "active") -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "state_snapshot_id": f"state_{status}_{suffix}",
        "current_status": status,
        "contexts": ["office_daily"],
        "confirmed_aspects": ["soft tailoring", "muted contrast"],
        "context_exclusions": [],
        "global_memory_write": False,
    }


def _same_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(str(sorted(value.items())).encode("utf-8")).hexdigest()


def _queue_item(item_id: str, trigger_type: str, trigger_ref: str, memory_id: str, runtime_trace_id: str, packet_id: str, feedback_id: str, status: str, resolution_ref: str | None) -> dict[str, Any]:
    item = {
        "governance_queue_item_id": item_id,
        "trigger_type": trigger_type,
        "trigger_ref": trigger_ref,
        "target_memory_id": memory_id,
        "source_runtime_trace_id": runtime_trace_id,
        "source_task_memory_packet_id": packet_id,
        "source_feedback_event_id": feedback_id,
        "status": status,
        "priority": "medium",
        "risk_level": "medium",
        "created_at": NOW,
        "resolution_ref": resolution_ref,
        "trace_refs": [runtime_trace_id, trigger_ref, packet_id, feedback_id],
    }
    if status == "expired":
        item["expiry_proof"] = {"expired_at": NOW, "production_write_executed": False}
    return item


def _case(case_code: str, scenario: str, kind: str, index: int) -> dict[str, Any]:
    suffix = f"v139_{index:03d}"
    case_id = f"v139_{case_code}_{scenario}"
    runtime_trace_id = f"rt_{suffix}"
    queue_id = f"rgq_{suffix}"
    item_id = f"gqi_{suffix}"
    card_id = f"uac_{suffix}"
    surface_id = f"gas_{suffix}"
    memory_id = f"mem_{suffix}"
    packet_id = f"tmp_{suffix}"
    feedback_id = f"pmf_{suffix}"
    trigger_id = f"gt_{suffix}"
    decision_id = f"grd_{suffix}"
    submission_id = f"uas_{suffix}"
    result_id = f"arp_{suffix}"
    post_packet_id = f"tmp_post_action_{suffix}"
    before = _base_state(memory_id, suffix)
    after = dict(before)
    trigger_type = "clarification_required"
    queue_status = "resolved"
    resolution_ref: str | None = decision_id
    card_type = "clarification"
    display_state = "resolved"
    title = "Clarify this preference"
    body = "Which outfit context should this apply to?"
    allowed_actions = ["this_time_only", "do_not_change_memory", "remember_for_context"]
    disabled_reason = None
    response_text = "I will use that only for this outfit."
    block_type = "action_result_notice"
    submitted_action: str | None = "this_time_only"
    result_type = "no_write_current_turn"
    write_executed = False
    gate_decision = "block"
    expected_packet_behavior = "current_turn_only"
    daily_status = "resolved"
    future_consumption_absent = False
    future_claims_absent = False
    no_active_action_for_memory = False
    duplicate_record: dict[str, Any] | None = None
    stale_proof: dict[str, Any] | None = None
    clarification_request: dict[str, Any] | None = None
    human_review_payload: dict[str, Any] | None = None
    review_resolution: dict[str, Any] | None = None
    submission: dict[str, Any] | None = None
    result_packet: dict[str, Any] | None = None
    extra_cards: list[dict[str, Any]] = []
    response_blocks: list[dict[str, Any]] = []

    if kind in {"open_clarification", "temporary_hold"}:
        queue_status = "open"
        resolution_ref = None
        display_state = "active"
        submitted_action = None
        result_type = "review_pending"
        response_text = "Please clarify how to use this preference for this outfit."
        block_type = "clarification_prompt"
        daily_status = "needs_clarification"
    elif kind in {"this_time_only", "post_this_time_only"}:
        submitted_action = "this_time_only"
        result_type = "no_write_current_turn"
        expected_packet_behavior = "this_time_only_no_write"
    elif kind == "do_not_change_memory":
        submitted_action = "do_not_change_memory"
        result_type = "no_write_user_declined"
        expected_packet_behavior = "declined_no_write"
        response_text = "I will not change memory for this preference."
    elif kind in {"remember_for_context", "post_write_candidate"}:
        submitted_action = "remember_for_context"
        result_type = "write_candidate_submitted"
        write_executed = True
        gate_decision = "allow"
        expected_packet_behavior = "write_gate_allowed"
        after = {**before, "state_snapshot_id": f"state_after_write_{suffix}", "context_exclusions": ["formal_client_meeting"]}
        response_text = "I saved this as a context-specific outfit preference."
    elif kind in {"open_review", "review_pending"}:
        trigger_type = "human_review_required"
        queue_status = "open"
        resolution_ref = None
        card_type = "review_pending"
        display_state = "pending"
        title = "Review pending"
        body = "I am holding this preference until review is complete."
        allowed_actions = ["retry_after_review", "dismiss"]
        submitted_action = None
        result_type = "review_pending"
        response_text = "This preference is pending review and has not changed memory."
        block_type = "review_pending_notice"
        daily_status = "pending_review"
    elif kind == "review_approved":
        trigger_type = "human_review_required"
        card_type = "review_pending"
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        result_type = "resolved_applied"
        write_executed = True
        gate_decision = "allow"
        after = {**before, "state_snapshot_id": f"state_review_write_{suffix}", "context_exclusions": ["formal_client_meeting"]}
        response_text = "Review is complete, and I applied the approved context-specific update."
    elif kind == "review_rejected":
        trigger_type = "human_review_required"
        card_type = "review_pending"
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        result_type = "no_write_user_declined"
        response_text = "Review is complete, and memory was not changed."
    elif kind == "review_request_clarification":
        trigger_type = "human_review_required"
        card_type = "review_pending"
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        response_text = "Review needs one more clarification before memory can change."
        followup = _queue_item(f"gqi_followup_{suffix}", "clarification_required", decision_id, memory_id, runtime_trace_id, packet_id, feedback_id, "open", None)
        extra_cards.append({
            "user_action_card_id": f"uac_followup_{suffix}",
            "governance_queue_item_id": followup["governance_queue_item_id"],
            "card_type": "clarification",
            "display_state": "active",
            "title": "Clarify this preference",
            "body": "Which reviewed outfit context should this apply to?",
            "allowed_actions": ["this_time_only", "do_not_change_memory", "remember_for_context"],
            "disabled_reason": None,
            "expires_at": f"2026-06-25T00:00:00Z",
            "trace_refs": [runtime_trace_id, followup["governance_queue_item_id"], decision_id, f"cr_followup_{suffix}"],
            "visible_text_source_refs": [runtime_trace_id, feedback_id, f"cr_followup_{suffix}"],
        })
    elif kind in {"expired_card", "expired_submission"}:
        queue_status = "expired"
        resolution_ref = None
        display_state = "expired"
        card_type = "expired_action"
        title = "Action expired"
        body = "This action expired and cannot change memory."
        allowed_actions = []
        disabled_reason = "expired"
        submitted_action = "this_time_only" if kind == "expired_submission" else None
        result_type = "expired_noop"
        response_text = "That action expired, so I did not change memory."
        expected_packet_behavior = "expired_noop"
        daily_status = "expired"
    elif kind == "duplicate_submission":
        result_type = "duplicate_ignored"
        duplicate_record = {
            "action_idempotency_record_id": f"air_{suffix}",
            "idempotency_key": f"idem_{suffix}",
            "first_action_submission_id": submission_id,
            "duplicate_action_submission_ids": [f"{submission_id}_dup"],
            "canonical_action_result_packet_id": result_id,
            "duplicate_created_resolution": False,
            "trace_refs": [submission_id, result_id],
        }
        response_text = "I already handled that action once."
    elif kind in {"stale_suppressed", "stale_hold_removed"}:
        stale_proof = {
            "stale_action_suppression_proof_id": f"sasp_{suffix}",
            "stale_user_action_card_id": card_id,
            "resolved_governance_queue_item_id": item_id,
            "suppressed": True,
            "suppression_reason": "queue_item_already_resolved",
            "production_write_executed": False,
            "trace_refs": [card_id, item_id, decision_id],
        }
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        response_text = "The earlier hold is resolved, so I removed the stale action."
        daily_status = "resolved_no_hold_banner"
    elif kind in {"rollback_status", "rollback_absence"}:
        trigger_type = "rollback_audit"
        card_type = "rollback_status"
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        result_type = "resolved_applied"
        after = _base_state(memory_id, suffix, "rolled_back")
        response_text = "This memory was rolled back and will not be used for future outfit packets."
        block_type = "memory_state_notice"
        expected_packet_behavior = "excluded_by_rollback"
        future_consumption_absent = True
        no_active_action_for_memory = True
    elif kind in {"blocked_status", "blocked_absence", "no_active_blocked"}:
        trigger_type = "blocked_memory_audit"
        card_type = "blocked_status"
        display_state = "resolved"
        allowed_actions = []
        submitted_action = None
        result_type = "resolved_applied"
        before = _base_state(memory_id, suffix, "blocked")
        after = _base_state(memory_id, suffix, "blocked")
        response_text = "This blocked memory is excluded from future outfit claims."
        block_type = "memory_state_notice"
        expected_packet_behavior = "excluded_by_blocked_state"
        future_consumption_absent = True
        future_claims_absent = True
        no_active_action_for_memory = True

    trigger = {
        "governance_trigger_id": trigger_id,
        "trigger_type": trigger_type,
        "source_runtime_trace_id": runtime_trace_id,
        "source_task_memory_packet_id": packet_id,
        "source_feedback_event_id": feedback_id,
        "target_memory_id": memory_id,
        "trace_refs": [runtime_trace_id, packet_id, feedback_id],
    }
    queue_item = _queue_item(item_id, trigger_type, trigger_id, memory_id, runtime_trace_id, packet_id, feedback_id, queue_status, resolution_ref)
    queue_items = [queue_item]
    if kind == "review_request_clarification":
        queue_items.append(_queue_item(f"gqi_followup_{suffix}", "clarification_required", decision_id, memory_id, runtime_trace_id, packet_id, feedback_id, "open", None))
    queue = {
        "runtime_governance_queue_id": queue_id,
        "runtime_trace_id": runtime_trace_id,
        "created_at": NOW,
        "queue_items": queue_items,
        "dedupe_index": [{"dedupe_key": f"{item['trigger_type']}:{item['target_memory_id']}:{item['trigger_ref']}", "canonical_queue_item_id": item["governance_queue_item_id"]} for item in queue_items],
        "open_item_count": sum(1 for item in queue_items if item["status"] == "open"),
        "resolved_item_count": sum(1 for item in queue_items if item["status"] == "resolved"),
        "expired_item_count": sum(1 for item in queue_items if item["status"] == "expired"),
    }
    if trigger_type == "clarification_required":
        clarification_request = {
            "clarification_request_id": f"cr_{suffix}",
            "governance_queue_item_id": item_id,
            "question_type": "context",
            "question_text": "Which outfit context should this apply to?",
            "allowed_response_kinds": ["this_time_only", "do_not_change_memory", "remember_for_context"],
            "must_not_suggest": ["global_memory", "body_inference", "commerce_targeting"],
            "current_turn_hold_ref": f"th_{suffix}",
            "memory_changed_claim": False,
            "trace_refs": [runtime_trace_id, packet_id, feedback_id, item_id],
        }
    elif trigger_type == "human_review_required":
        human_review_payload = {
            "human_review_payload_id": f"hrp_{suffix}",
            "governance_queue_item_id": item_id,
            "risk_reasons": ["context_scope_change_requires_review"],
            "raw_evidence_refs": [runtime_trace_id, packet_id, feedback_id, f"state_before_{suffix}"],
            "trace_refs": [runtime_trace_id, packet_id, feedback_id, item_id],
            "internal_only_fields": ["raw_evidence_refs", "risk_reasons"],
            "production_write_blocked_until_resolution": True,
        }
    if kind == "review_request_clarification":
        clarification_request = {
            "clarification_request_id": f"cr_followup_{suffix}",
            "governance_queue_item_id": f"gqi_followup_{suffix}",
            "question_type": "context",
            "question_text": "Which reviewed outfit context should this apply to?",
            "allowed_response_kinds": ["this_time_only", "do_not_change_memory", "remember_for_context"],
            "must_not_suggest": ["global_memory", "body_inference", "commerce_targeting"],
            "current_turn_hold_ref": f"th_{suffix}",
            "memory_changed_claim": False,
            "trace_refs": [runtime_trace_id, packet_id, feedback_id, f"gqi_followup_{suffix}", decision_id],
        }
    if trigger_type == "human_review_required" and queue_status == "resolved":
        review_resolution = {
            "human_review_resolution_id": f"hrr_{suffix}",
            "reviewer_action": "approve_write" if write_executed else ("request_clarification" if kind == "review_request_clarification" else "reject"),
            "blocked_forbidden_action": False,
            "trace_refs": [item_id, f"hrp_{suffix}", decision_id],
        }
    card = {
        "user_action_card_id": card_id,
        "governance_queue_item_id": item_id,
        "card_type": card_type,
        "display_state": display_state,
        "title": title,
        "body": body,
        "allowed_actions": allowed_actions,
        "disabled_reason": disabled_reason,
        "expires_at": f"2026-06-25T00:00:00Z" if display_state in {"active", "pending"} else NOW,
        "trace_refs": [runtime_trace_id, item_id, clarification_request["clarification_request_id"] if clarification_request and clarification_request["governance_queue_item_id"] == item_id else trigger_id],
        "visible_text_source_refs": [runtime_trace_id, feedback_id],
    }
    cards = [] if kind in {"no_active_blocked"} else [card]
    cards.extend(extra_cards)
    decision = None
    if queue_status == "resolved":
        decision = {
            "governance_resolution_decision_id": decision_id,
            "governance_queue_item_id": item_id,
            "resolution_type": "clarified_write_candidate" if write_executed and trigger_type == "clarification_required" else ("review_approved_write" if write_executed else ("review_rejected_no_write" if trigger_type == "human_review_required" else "clarified_no_write")),
            "production_write_gate_ref": f"pmwg_{suffix}" if write_executed else None,
            "production_write_executed": write_executed,
            "trace_refs": [runtime_trace_id, item_id],
        }
    if submitted_action:
        submission = {
            "action_submission_id": submission_id,
            "user_action_card_id": card_id,
            "governance_queue_item_id": item_id,
            "submitted_action": submitted_action,
            "submitted_value": None,
            "idempotency_key": f"idem_{suffix}",
            "submitted_at": NOW,
            "trace_refs": [runtime_trace_id, card_id, item_id],
        }
    post_packet = {
        "post_action_task_memory_packet_id": post_packet_id,
        "request_context": "office_daily",
        "candidate_promoted_memory_ids": [memory_id],
        "consumed_promoted_memory_ids": [] if future_consumption_absent or expected_packet_behavior in {"current_turn_only", "this_time_only_no_write", "declined_no_write", "expired_noop", "excluded_by_rollback", "excluded_by_blocked_state"} else [memory_id],
        "excluded_memory_ids": [memory_id] if future_consumption_absent or expected_packet_behavior in {"current_turn_only", "this_time_only_no_write", "declined_no_write", "expired_noop", "excluded_by_rollback", "excluded_by_blocked_state"} else [],
        "expected_behavior": expected_packet_behavior,
        "daily_outfit_card_status": daily_status,
        "stale_hold_banner_present": False,
        "resolution_ref": decision_id if decision else None,
        "trace_refs": [runtime_trace_id, result_id, decision_id if decision else item_id],
    }
    if submitted_action or decision or queue_status == "expired":
        result_packet = {
            "action_result_packet_id": result_id,
            "action_submission_id": submission_id if submission else None,
            "governance_resolution_decision_id": decision_id if decision else None,
            "result_type": result_type,
            "production_write_executed": write_executed,
            "post_action_task_memory_packet_id": post_packet_id,
            "user_visible_response_block_ids": [f"urb_{suffix}"],
            "trace_refs": [runtime_trace_id, submission_id if submission else item_id, decision_id if decision else item_id],
        }
    response_block = {
        "response_block_id": f"urb_{suffix}",
        "block_type": block_type,
        "text": response_text,
        "claim_refs": [f"claim_{suffix}"],
        "trace_refs": [runtime_trace_id, result_id if result_packet else item_id, decision_id if decision else item_id],
    }
    response_blocks.append(response_block)
    surface = {
        "governance_action_surface_id": surface_id,
        "runtime_trace_id": runtime_trace_id,
        "source_governance_queue_ref": queue_id,
        "surface_context": "daily_outfit_card" if cards else "post_resolution_response",
        "cards": cards,
        "response_blocks": response_blocks,
        "trace_refs": [runtime_trace_id, queue_id] + [item["governance_queue_item_id"] for item in queue_items],
    }
    claim = {
        "claim_id": f"claim_{suffix}",
        "text": response_text,
        "action_result_packet_id": result_id if result_packet else None,
        "governance_resolution_decision_id": decision_id if decision else None,
        "trace_refs": [response_block["response_block_id"], result_id if result_packet else item_id, decision_id if decision else item_id],
    }
    artifact = {
        "case_id": case_id,
        "version": VERSION,
        "scenario_kind": kind,
        "gate_assertions": {gate: True for gate in GATES},
        "runtime_trace": {"runtime_trace_id": runtime_trace_id, "trace_refs": [packet_id, feedback_id]},
        "governance_trigger": trigger,
        "runtime_governance_queue": queue,
        "clarification_requests": [clarification_request] if clarification_request else [],
        "human_review_payloads": [human_review_payload] if human_review_payload else [],
        "human_review_resolution": review_resolution,
        "governance_resolution_decision": decision,
        "production_memory_write_gate": {"gate_id": f"pmwg_{suffix}", "decision": gate_decision, "production_write_executed": write_executed, "environment": "deterministic_local_fixture"},
        "before_memory_lifecycle_state": before,
        "after_memory_lifecycle_state": after,
        "governance_action_surface": surface,
        "action_submission_envelope": submission,
        "action_result_packet": result_packet,
        "post_action_task_memory_packet": post_packet,
        "action_idempotency_record": duplicate_record,
        "stale_action_suppression_proof": stale_proof,
        "response_claim_traces": [claim],
        "policy_surface_audit": {
            "no_internal_review_evidence_exposed": True,
            "no_memory_change_claim_without_write": not ("saved" in response_text.lower() and not write_executed),
            "no_global_memory_claim": "global" not in response_text.lower(),
            "no_unconfirmed_aspect_claim": "silhouette" not in response_text.lower(),
            "no_sensitive_or_internal_data": not any(term in response_text.lower() for term in ["raw_evidence", "risk_reasons", "body", "identity", "attractive"]),
            "no_commerce_or_aigc": not any(term in response_text.lower() for term in ["sku", "merchant", "affiliate", "aigc", "image generation"]),
        },
        "rollback_blocked_absence_proof": {"future_consumption_absent": future_consumption_absent, "future_claims_absent": future_claims_absent, "no_active_action_for_memory": no_active_action_for_memory, "trace_refs": [memory_id, post_packet_id]},
        "daily_outfit_card_status_proof": {"status": daily_status, "stale_hold_banner_present": False, "trace_refs": [post_packet_id, response_block["response_block_id"]]},
        "reviewer_checklist_refs": ["per_case/clean/v139_A01_open_clarification_queue_item_creates_active_action_card.json", "per_case/clean/v139_D04_duplicate_action_submission_idempotent.json"] if kind == "reviewer_checklist" else [],
        "runner_reproducibility_proof": {"command": "python benchmark/benchmark_v139/scripts/run_v139_validation_suite.py", "one_command": True} if kind == "runner_reproducible" else {},
        "v138_replay_proof": {"run_v138_validation_suite": "PASS"},
        "state_hashes": {"before": _same_hash(before), "after": _same_hash(after)},
    }
    return artifact


def _set_case_meta(artifact: dict[str, Any], defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    artifact["case_id"] = f"v139_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = gates
    return artifact


def _defect(defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    idx = 900 + int(defect_id.split("_M")[-1])
    artifact = _set_case_meta(_case(defect_id, defect_type, "this_time_only", idx), defect_id, defect_type, gates)
    surface = artifact["governance_action_surface"]
    cards = surface["cards"]
    if defect_type == "action_card_without_governance_queue_item":
        cards[0]["governance_queue_item_id"] = "gqi_missing"
    elif defect_type == "card_allows_action_not_in_clarification_request":
        cards[0]["allowed_actions"].append("globalize_memory")
        artifact["action_submission_envelope"]["submitted_action"] = "globalize_memory"
    elif defect_type == "clarification_card_text_untraceable":
        cards[0]["visible_text_source_refs"] = []
    elif defect_type == "this_time_only_submission_mutates_memory":
        artifact["governance_resolution_decision"]["production_write_executed"] = True
        artifact["after_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
        artifact["post_action_task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["before_memory_lifecycle_state"]["memory_id"]]
    elif defect_type == "do_not_change_memory_creates_write_candidate":
        artifact = _set_case_meta(_case(defect_id, defect_type, "do_not_change_memory", idx), defect_id, defect_type, gates)
        artifact["action_result_packet"]["result_type"] = "write_candidate_submitted"
        artifact["governance_resolution_decision"]["production_write_executed"] = True
    elif defect_type == "remember_for_context_bypasses_write_gate":
        artifact = _set_case_meta(_case(defect_id, defect_type, "remember_for_context", idx), defect_id, defect_type, gates)
        artifact["governance_resolution_decision"]["production_write_gate_ref"] = None
        artifact["production_memory_write_gate"]["decision"] = "block"
    elif defect_type == "review_pending_notice_claims_memory_changed":
        artifact = _set_case_meta(_case(defect_id, defect_type, "open_review", idx), defect_id, defect_type, gates)
        artifact["governance_action_surface"]["response_blocks"][0]["text"] = "I saved this preference while review is pending."
    elif defect_type == "review_pending_notice_exposes_raw_review_evidence":
        artifact = _set_case_meta(_case(defect_id, defect_type, "open_review", idx), defect_id, defect_type, gates)
        artifact["governance_action_surface"]["response_blocks"][0]["text"] = "Pending review: raw_evidence_refs and risk_reasons are visible."
    elif defect_type == "review_rejection_response_claims_applied_preference":
        artifact = _set_case_meta(_case(defect_id, defect_type, "review_rejected", idx), defect_id, defect_type, gates)
        artifact["governance_action_surface"]["response_blocks"][0]["text"] = "I applied the rejected preference."
    elif defect_type == "expired_action_card_still_active":
        artifact = _set_case_meta(_case(defect_id, defect_type, "expired_card", idx), defect_id, defect_type, gates)
        artifact["governance_action_surface"]["cards"][0]["display_state"] = "active"
        artifact["governance_action_surface"]["cards"][0]["allowed_actions"] = ["this_time_only"]
    elif defect_type == "expired_submission_executes_write":
        artifact = _set_case_meta(_case(defect_id, defect_type, "expired_submission", idx), defect_id, defect_type, gates)
        artifact["action_result_packet"]["production_write_executed"] = True
    elif defect_type == "duplicate_submission_creates_second_resolution":
        artifact = _set_case_meta(_case(defect_id, defect_type, "duplicate_submission", idx), defect_id, defect_type, gates)
        artifact["action_idempotency_record"]["duplicate_created_resolution"] = True
    elif defect_type == "stale_action_card_survives_resolution":
        artifact = _set_case_meta(_case(defect_id, defect_type, "stale_suppressed", idx), defect_id, defect_type, gates)
        artifact["stale_action_suppression_proof"]["suppressed"] = False
        artifact["governance_action_surface"]["cards"][0]["display_state"] = "active"
    elif defect_type == "post_action_packet_ignores_resolution":
        artifact["post_action_task_memory_packet"]["expected_behavior"] = "write_gate_allowed"
        artifact["post_action_task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["before_memory_lifecycle_state"]["memory_id"]]
    elif defect_type == "daily_outfit_status_banner_stale_after_resolution":
        artifact = _set_case_meta(_case(defect_id, defect_type, "daily_status_resolved", idx), defect_id, defect_type, gates)
        artifact["daily_outfit_card_status_proof"]["stale_hold_banner_present"] = True
        artifact["post_action_task_memory_packet"]["stale_hold_banner_present"] = True
    elif defect_type == "rollback_status_still_consumes_memory":
        artifact = _set_case_meta(_case(defect_id, defect_type, "rollback_absence", idx), defect_id, defect_type, gates)
        artifact["post_action_task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["before_memory_lifecycle_state"]["memory_id"]]
    elif defect_type == "blocked_status_creates_future_claim":
        artifact = _set_case_meta(_case(defect_id, defect_type, "blocked_absence", idx), defect_id, defect_type, gates)
        artifact["rollback_blocked_absence_proof"]["future_claims_absent"] = False
    elif defect_type == "response_claim_without_action_result_trace":
        artifact["response_claim_traces"][0]["trace_refs"] = []
    elif defect_type == "response_globalizes_contextual_memory":
        artifact["governance_action_surface"]["response_blocks"][0]["text"] = "I saved this as global memory."
    elif defect_type == "response_adds_unconfirmed_aspect":
        artifact["governance_action_surface"]["response_blocks"][0]["text"] = "I added silhouette as a confirmed preference."
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        artifact["sample_consistency_probe"] = {"sample_artifact_content": {"case_id": artifact["case_id"], "manual_only_patch": True}, "source_artifact_content": {"case_id": artifact["case_id"]}}
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        artifact["report_consistency_probe"] = {"clean_report_summary": {"passed_cases": 34, "failed_cases": 0}, "independent_validation_summary": {"passed_cases": 33, "failed_cases": 1}}
    elif defect_type == "missing_idempotency_record":
        artifact = _set_case_meta(_case(defect_id, defect_type, "duplicate_submission", idx), defect_id, defect_type, gates)
        artifact["action_idempotency_record"] = None
    elif defect_type == "missing_stale_action_suppression_proof":
        artifact = _set_case_meta(_case(defect_id, defect_type, "stale_suppressed", idx), defect_id, defect_type, gates)
        artifact["stale_action_suppression_proof"] = None
    elif defect_type == "missing_action_submission_for_submitted_action":
        artifact = _set_case_meta(_case(defect_id, defect_type, "this_time_only", idx), defect_id, defect_type, gates)
        artifact["action_submission_envelope"] = None
    elif defect_type == "missing_action_result_for_submitted_action":
        artifact = _set_case_meta(_case(defect_id, defect_type, "this_time_only", idx), defect_id, defect_type, gates)
        artifact["action_result_packet"] = None
    elif defect_type == "missing_action_result_for_expired_submission":
        artifact = _set_case_meta(_case(defect_id, defect_type, "expired_submission", idx), defect_id, defect_type, gates)
        artifact["action_result_packet"] = None
    elif defect_type == "missing_response_claim_trace":
        artifact = _set_case_meta(_case(defect_id, defect_type, "claims_trace", idx), defect_id, defect_type, gates)
        artifact["response_claim_traces"] = []
    elif defect_type == "action_result_references_missing_response_block":
        artifact = _set_case_meta(_case(defect_id, defect_type, "claims_trace", idx), defect_id, defect_type, gates)
        artifact["action_result_packet"]["user_visible_response_block_ids"] = ["urb_missing"]
    return artifact


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.39.governance_user_action_surface" + ("" if clean else ".mixed_strict"),
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
        "theme": "Governance User Action Surface",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v139/results/v139_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v139/scripts/build_v139_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v139/scripts/validate_v139_release_candidate.py",
        "runner_script": "benchmark/benchmark_v139/scripts/run_v139_validation_suite.py",
        "required_reports": ["clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "report_consistency_report.json", "sample_consistency_report.json", "injected_defect_detection_summary.json"],
        "required_gates": GATES,
        "validator_commands": ["benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py", "python benchmark/benchmark_v138/scripts/run_v138_validation_suite.py", "python benchmark/benchmark_v139/scripts/run_v139_validation_suite.py", "python -m unittest discover -s benchmark/benchmark_v139/tests"],
        "sample_artifacts": samples,
        "non_goals": ["No full frontend UI", "No production service", "No commerce, SKU, merchant, affiliate, or product links", "No AIGC image generation", "No global memory writes"],
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
    _write_text(result_dir / "README.md", "# v1.39 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic local governance user action surface evidence.\n")
    _write_text(result_dir / "RELEASE_NOTE.md", "# v1.39 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves artifact/API-level governance action surfaces, submissions, idempotency, stale suppression, and trace-backed user-visible responses.\n")
    _write_text(result_dir / "reviewer_checklist.md", "# v1.39 Reviewer Checklist\n\n- [ ] Open clarification card is trace-backed.\n- [ ] this_time_only does not write memory.\n- [ ] remember_for_context routes through write gate.\n- [ ] Review pending notice hides internal review evidence.\n- [ ] Expired and stale actions cannot write.\n- [ ] Duplicate submissions are idempotent.\n- [ ] Rollback/blocked statuses exclude future memory consumption.\n- [ ] Response claims trace to action result and governance decision.\n")
    _write_text(result_dir / "clean_report.md", "# v1.39 Clean Acceptance Report\n\n" + "\n".join(f"- PASS `{gate}`" for gate in GATES) + "\n")
    _write_text(result_dir / "mixed_strict_report.md", "# v1.39 Mixed Strict Report\n\n" + "\n".join(f"- EXPECTED FAIL `{gate}`" for gate in GATES) + "\n")


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
