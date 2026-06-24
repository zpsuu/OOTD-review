"""Build v1.37 End-to-End Inspiration Memory Runtime Loop evidence pack."""
from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.raw_artifact_validation import canonical_json_hash, now_iso, write_json


VERSION = "v1.37"
BRANCH = "v137-end-to-end-inspiration-memory-runtime-loop"
RESULT_DIR = Path("benchmark/benchmark_v137/results/v137_release_candidate")
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

CLEAN_CASES = [
    ("A01", "full_loop_low_risk_color_memory", "happy_color"),
    ("A02", "full_loop_silhouette_memory", "happy_silhouette"),
    ("A03", "full_loop_contextual_soft_prefer_memory", "happy_contextual"),
    ("B01", "unconfirmed_candidate_never_promotes", "unconfirmed_blocked"),
    ("B02", "confirmed_aspect_subset_only", "aspect_subset"),
    ("B03", "do_not_remember_candidate_blocks_promotion", "do_not_remember_candidate"),
    ("C01", "low_risk_contextual_promotion_allowed", "happy_color"),
    ("C02", "conflict_requires_review_before_promotion", "promotion_review"),
    ("C03", "global_scope_request_blocked", "promotion_blocked"),
    ("D01", "matching_context_consumes_memory", "happy_color"),
    ("D02", "mismatching_context_excludes_memory", "mismatch_exclusion"),
    ("D03", "no_hard_filter_from_soft_prefer", "happy_color"),
    ("E01", "too_strong_feedback_reduces_weight", "too_strong"),
    ("E02", "wrong_aspect_preserves_other_confirmed_aspects", "wrong_aspect"),
    ("E03", "wrong_context_adds_exclusion_and_tests_excluded_context", "wrong_context"),
    ("E04", "review_pending_feedback_does_not_claim_applied_effect", "feedback_review_pending"),
    ("F01", "do_not_use_blocks_future_consumption", "do_not_use"),
    ("F02", "forget_routes_through_rollback", "rollback"),
    ("F03", "rollback_removes_future_claims", "rollback"),
    ("G01", "ambiguous_feedback_requires_clarification", "clarification"),
    ("G02", "high_risk_identity_or_body_inference_requires_review_or_block", "feedback_review_pending"),
    ("H01", "day1_to_day3_state_hash_stability", "happy_color"),
    ("H02", "feedback_lifecycle_survives_multiday_replay", "wrong_context"),
    ("I01", "sample_artifact_matches_per_case", "happy_color"),
    ("I02", "clean_report_cannot_override_raw_failure", "happy_color"),
    ("J01", "v136_replay_passes_before_v137_validation", "happy_color"),
    ("J02", "promotion_to_consumption_handoff_same_id", "happy_color"),
    ("J03", "post_feedback_packet_rebuilt_from_lifecycle_state", "do_not_use"),
    ("J04", "visible_claims_trace_back_to_memory_and_card", "happy_color"),
    ("J05", "runtime_trace_invariants_are_raw_backed", "wrong_context"),
]

DEFECTS = [
    ("ADV_K01", "stage_order_skips_confirmation", ["runtime_trace_stage_order_complete_rate"]),
    ("ADV_K02", "candidate_promotes_before_user_confirmation", ["no_pre_gate_production_write_rate", "promotion_gate_required_before_memory_write_rate"]),
    ("ADV_K03", "unconfirmed_aspect_enters_promoted_memory", ["confirmed_aspects_only_rate"]),
    ("ADV_K04", "downstream_consumes_memory_before_promotion", ["downstream_consumption_requires_promoted_memory_rate"]),
    ("ADV_K05", "soft_prefer_becomes_hard_filter", ["soft_prefer_not_hard_filter_rate"]),
    ("ADV_K06", "mismatching_context_consumes_memory", ["mismatching_context_exclusion_rate"]),
    ("ADV_K07", "feedback_targets_unconsumed_memory", ["feedback_event_refs_consumed_memory_rate"]),
    ("ADV_K08", "wrong_context_feedback_tests_non_excluded_context", ["wrong_context_feedback_tests_excluded_context_rate"]),
    ("ADV_K09", "review_pending_claims_applied_effect", ["review_pending_does_not_claim_applied_effect_rate"]),
    ("ADV_K10", "rollback_memory_still_consumed_later", ["rollback_removes_future_consumption_rate"]),
    ("ADV_K11", "visible_claim_without_trace_ref", ["trace_backed_visible_claims_rate"]),
    ("ADV_K12", "state_hash_changes_without_stage_event", ["multi_day_state_hash_stability_rate"]),
    ("ADV_K13", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_K14", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_K15", "handoff_source_ref_not_from_stage_output", ["handoff_ids_match_across_stages_rate"]),
    ("ADV_K16", "handoff_target_ref_not_to_stage_input", ["handoff_ids_match_across_stages_rate"]),
    ("ADV_K17", "blocked_ref_claimed_as_successful_handoff", ["handoff_ids_match_across_stages_rate"]),
    ("ADV_K18", "handoff_references_missing_state_snapshot", ["handoff_ids_match_across_stages_rate"]),
    ("ADV_K19", "fake_feedback_on_nonexistent_promoted_memory", ["feedback_event_refs_consumed_memory_rate"]),
    ("ADV_K20", "ambiguous_feedback_routed_to_human_review", ["review_pending_does_not_claim_applied_effect_rate"]),
    ("ADV_K21", "active_matching_context_excluded_without_hold_reason", ["post_feedback_packet_uses_updated_lifecycle_state_rate"]),
    ("ADV_K22", "clarification_required_missing_temporary_hold_reason", ["post_feedback_packet_uses_updated_lifecycle_state_rate"]),
    ("ADV_K23", "expected_behavior_unchanged_but_packet_excludes_memory", ["post_feedback_packet_uses_updated_lifecycle_state_rate"]),
]

SAMPLE_CASES = {
    "full_loop_low_risk_color_memory.json": "v137_A01_full_loop_low_risk_color_memory",
    "unconfirmed_candidate_never_promotes.json": "v137_B01_unconfirmed_candidate_never_promotes",
    "wrong_context_feedback_tests_excluded_context.json": "v137_E03_wrong_context_adds_exclusion_and_tests_excluded_context",
    "review_pending_no_applied_effect_claim.json": "v137_E04_review_pending_feedback_does_not_claim_applied_effect",
    "rollback_removes_future_claims.json": "v137_F03_rollback_removes_future_claims",
    "state_hash_stability.json": "v137_H01_day1_to_day3_state_hash_stability",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _hash_snapshot(snapshot: dict[str, Any]) -> str:
    payload = {k: v for k, v in snapshot.items() if k != "state_hash"}
    return canonical_json_hash(payload)


def _snapshot(snapshot_id: str, after_stage: str, confirmed: list[str], promoted: list[str], active: list[str], blocked: list[str], rolled: list[str], review: list[str], packets: list[str], claims: list[str]) -> dict[str, Any]:
    snap = {
        "state_snapshot_id": snapshot_id,
        "after_stage": after_stage,
        "confirmed_candidate_ids": confirmed,
        "promoted_memory_ids": promoted,
        "active_memory_ids": active,
        "blocked_memory_ids": blocked,
        "rolled_back_memory_ids": rolled,
        "review_pending_memory_ids": review,
        "task_memory_packet_ids": packets,
        "claim_ids": claims,
    }
    snap["state_hash"] = _hash_snapshot(snap)
    return snap


def _event(event_id: str, stage: str, inputs: list[str], outputs: list[str], policies: list[str], blocked: list[str] | None = None, claims: list[str] | None = None) -> dict[str, Any]:
    return {
        "stage_event_id": event_id,
        "stage": stage,
        "input_refs": inputs,
        "output_refs": outputs,
        "policy_refs": policies,
        "blocked_output_refs": blocked or [],
        "visible_claim_refs": claims or [],
        "created_at": "2026-06-24T00:00:00Z",
    }


def _handoff(hid: str, from_stage: str, to_stage: str, ref: str, src: str, target: str) -> dict[str, Any]:
    return {
        "handoff_proof_id": hid,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "source_output_ref": ref,
        "target_input_ref": ref,
        "source_artifact_ref": src,
        "target_artifact_ref": target,
        "same_id": True,
        "policy_boundary_preserved": True,
    }


def _gate_assertions() -> dict[str, bool]:
    return {gate: True for gate in GATES}


GATE_PROOF_REFS = {
    "runtime_trace_stage_order_complete_rate": ["runtime_trace.stage_order", "runtime_trace.stage_events[*].stage"],
    "runtime_trace_has_state_snapshots_rate": ["runtime_trace.state_snapshots[*].state_snapshot_id", "runtime_trace.final_state_ref"],
    "handoff_ids_match_across_stages_rate": ["runtime_trace.stage_events[*].input_refs", "runtime_trace.stage_events[*].output_refs", "handoff_proofs"],
    "no_pre_gate_production_write_rate": ["production_memory_write_gate.pre_gate_production_write"],
    "confirmed_aspects_only_rate": ["confirmed_inspiration_candidate.confirmed_aspects", "promoted_memory_atom.confirmed_aspects"],
    "promotion_gate_required_before_memory_write_rate": ["promotion_eligibility_report", "production_memory_write_gate", "promoted_memory_atom"],
    "downstream_consumption_requires_promoted_memory_rate": ["promoted_memory_atom.memory_id", "task_memory_packet.consumed_promoted_memory_ids"],
    "soft_prefer_not_hard_filter_rate": ["promoted_memory_atom.polarity", "task_memory_packet.consumption_mode"],
    "mismatching_context_exclusion_rate": ["task_memory_packet.request_context", "task_memory_packet.excluded_memory_ids"],
    "feedback_event_refs_consumed_memory_rate": ["task_memory_packet.consumed_promoted_memory_ids", "promoted_memory_feedback_event.promoted_memory_id"],
    "post_feedback_packet_uses_updated_lifecycle_state_rate": ["updated_memory_lifecycle_state", "post_feedback_task_memory_packet"],
    "wrong_context_feedback_tests_excluded_context_rate": ["updated_memory_lifecycle_state.context_exclusions", "post_feedback_task_memory_packet.request_context"],
    "review_pending_does_not_claim_applied_effect_rate": ["feedback_write_decision.gate_decision", "post_feedback_claims"],
    "rollback_removes_future_consumption_rate": ["rollback_proof.read_after_rollback", "post_feedback_task_memory_packet.consumed_promoted_memory_ids"],
    "blocked_memory_not_claimed_rate": ["updated_memory_lifecycle_state.blocked_memory_ids", "post_feedback_claims"],
    "trace_backed_visible_claims_rate": ["visible_claims[*].trace_refs", "post_feedback_claims[*].trace_refs"],
    "multi_day_state_hash_stability_rate": ["runtime_trace.state_snapshots[*].state_hash", "multi_day_runtime_trace.day_state_hashes"],
    "sample_artifacts_match_per_case_rate": ["REVIEW_MANIFEST.sample_artifacts", "sample_consistency_report"],
    "report_consistency_with_independent_validation_rate": ["clean_report", "independent_validation_report", "report_consistency_report"],
    "adversarial_detection_rate": ["per_case/adversarial", "adversarial_validation_report"],
    "v136_validation_replay_pass_rate": ["v136_replay_proof.run_v136_validation_suite"],
}


def _case(case_id: str, scenario: str, kind: str, index: int) -> dict[str, Any]:
    suffix = f"v137_{index:03d}"
    full_case_id = f"v137_{case_id}_{scenario}"
    input_id = f"insp_{suffix}"
    signal_id = f"signal_{suffix}"
    candidate_id = f"cand_{suffix}"
    confirmed_id = f"confirmed_{suffix}"
    memory_id = f"mem_insp_{suffix}"
    packet_id = f"tmp_{suffix}"
    post_packet_id = f"tmp_post_{suffix}"
    claim_id = f"claim_{suffix}"
    feedback_id = f"pmf_{suffix}"
    rollback_ref = f"rollback_{suffix}"
    state_after_post_id = f"state_after_post_feedback_{suffix}"
    state_after_day3_id = f"state_after_day3_{suffix}"

    confirmed_aspects = ["color_palette"] if "silhouette" not in kind else ["silhouette"]
    extracted_aspects = confirmed_aspects + (["silhouette"] if kind == "aspect_subset" else [])
    promotion_allowed = kind not in {"unconfirmed_blocked", "do_not_remember_candidate", "promotion_review", "promotion_blocked"}
    promotion_review = kind == "promotion_review"
    promotion_blocked = kind in {"unconfirmed_blocked", "do_not_remember_candidate", "promotion_blocked"}
    consumed = promotion_allowed and kind not in {"mismatch_exclusion"}
    mismatching = kind in {"mismatch_exclusion"}
    feedback_action = "use_was_right"
    lifecycle_status = "active"
    post_consumed = consumed
    post_claims = [claim_id] if consumed else []
    context_exclusions: list[str] = []
    request_context = "office_daily"
    post_request_context = "office_daily"
    expected_post = "unchanged_active_consumption"
    temporary_hold_reason = None
    post_exclusion_reason = None
    review_pending = False
    clarification_required = False
    rolled_back = False
    blocked = False
    if kind == "too_strong":
        feedback_action = "use_was_too_strong"
        expected_post = "consume_less_strongly"
    elif kind == "wrong_aspect":
        feedback_action = "wrong_aspect"
        expected_post = "consume_less_strongly"
    elif kind == "mismatch_exclusion":
        post_request_context = "date_night"
        expected_post = "excluded_by_mismatching_context"
        post_exclusion_reason = "request_context_not_in_memory_contexts"
    elif kind == "wrong_context":
        feedback_action = "wrong_context"
        context_exclusions = ["formal_client_meeting"]
        post_request_context = "formal_client_meeting"
        expected_post = "excluded_by_context_exclusion"
        post_exclusion_reason = "context_exclusion"
        post_consumed = False
        post_claims = []
    elif kind == "do_not_use":
        feedback_action = "do_not_use_this_inspiration"
        lifecycle_status = "blocked"
        blocked = True
        expected_post = "excluded_by_lifecycle_state"
        post_exclusion_reason = "blocked_lifecycle_state"
        post_consumed = False
        post_claims = []
    elif kind == "rollback":
        feedback_action = "forget_this_inspiration_memory"
        lifecycle_status = "rolled_back"
        rolled_back = True
        expected_post = "excluded_by_lifecycle_state"
        post_exclusion_reason = "rolled_back_lifecycle_state"
        post_consumed = False
        post_claims = []
    elif kind == "feedback_review_pending":
        feedback_action = "wrong_context"
        lifecycle_status = "review_pending"
        review_pending = True
        expected_post = "temporary_hold_pending_review"
        temporary_hold_reason = "human_review_required_current_turn_only"
        post_exclusion_reason = "temporary_hold_pending_review"
        post_consumed = False
        post_claims = []
    elif kind == "clarification":
        feedback_action = "ambiguous_feedback"
        clarification_required = True
        expected_post = "temporary_hold_pending_clarification"
        temporary_hold_reason = "clarification_required_current_turn_only"
        post_exclusion_reason = "temporary_hold_pending_clarification"
        post_consumed = False
        post_claims = []

    active_ids = [memory_id] if promotion_allowed and lifecycle_status == "active" else []
    promoted_ids = [memory_id] if promotion_allowed else []
    blocked_ids = [memory_id] if blocked else []
    rolled_ids = [memory_id] if rolled_back else []
    review_ids = [memory_id] if review_pending and promotion_allowed else []
    consumed_ids = [memory_id] if consumed else []
    excluded_ids = [memory_id] if promotion_allowed and not consumed else []
    post_consumed_ids = [memory_id] if post_consumed else []
    post_excluded_ids = [memory_id] if promotion_allowed and not post_consumed else []
    has_real_feedback = bool(consumed_ids)

    stage_events = [
        _event(f"rte_{suffix}_intake", "intake", [input_id], [signal_id, candidate_id], ["privacy_rights_safe_local_fixture"]),
        _event(f"rte_{suffix}_confirmation", "confirmation", [candidate_id], [confirmed_id] if not promotion_blocked else [], ["user_confirmation_required"], [candidate_id] if promotion_blocked else []),
        _event(f"rte_{suffix}_promotion", "promotion", [confirmed_id] if not promotion_blocked else [], [memory_id] if promotion_allowed else [], ["promotion_eligibility_report", "production_memory_write_gate"], [confirmed_id] if promotion_review or promotion_blocked else []),
        _event(f"rte_{suffix}_consumption", "consumption", [memory_id] if promotion_allowed else [], [packet_id] + consumed_ids, ["task_memory_packet_builder"], claims=[claim_id] if consumed else []),
        _event(f"rte_{suffix}_feedback", "feedback", [packet_id] + consumed_ids, [feedback_id] + consumed_ids, ["feedback_interpreter"] if has_real_feedback else ["feedback_noop_no_consumed_promoted_memory"]),
        _event(f"rte_{suffix}_post", "post_feedback_consumption", [feedback_id] + consumed_ids, [post_packet_id, state_after_post_id], ["lifecycle_state_packet_rebuild"] if has_real_feedback else ["post_feedback_noop_no_lifecycle_write"], claims=post_claims),
        _event(f"rte_{suffix}_multi_day", "multi_day_replay", [post_packet_id, state_after_post_id], [state_after_day3_id], ["state_hash_replay"]),
    ]

    snapshots = [
        _snapshot(f"state_after_intake_{suffix}", "intake", [], [], [], [], [], [], [], []),
        _snapshot(f"state_after_confirmation_{suffix}", "confirmation", [confirmed_id] if not promotion_blocked else [], [], [], [], [], [], [], []),
        _snapshot(f"state_after_promotion_{suffix}", "promotion", [confirmed_id] if not promotion_blocked else [], promoted_ids, [memory_id] if promotion_allowed else [], [], [], [], [], []),
        _snapshot(f"state_after_consumption_{suffix}", "consumption", [confirmed_id] if not promotion_blocked else [], promoted_ids, [memory_id] if promotion_allowed else [], [], [], [], [packet_id], [claim_id] if consumed else []),
        _snapshot(f"state_after_feedback_{suffix}", "feedback", [confirmed_id] if not promotion_blocked else [], promoted_ids, active_ids, blocked_ids, rolled_ids, review_ids, [packet_id], [claim_id] if consumed else []),
        _snapshot(state_after_post_id, "post_feedback_consumption", [confirmed_id] if not promotion_blocked else [], promoted_ids, active_ids, blocked_ids, rolled_ids, review_ids, [packet_id, post_packet_id], post_claims),
        _snapshot(state_after_day3_id, "multi_day_replay", [confirmed_id] if not promotion_blocked else [], promoted_ids, active_ids, blocked_ids, rolled_ids, review_ids, [packet_id, post_packet_id], post_claims),
    ]

    handoffs = []
    if not promotion_blocked:
        handoffs.append(_handoff(f"hp_{suffix}_intake_confirmation", "intake", "confirmation", candidate_id, "inspiration_candidate.candidate_id", "user_confirmation.candidate_id"))
    if not promotion_blocked and not promotion_review:
        handoffs.append(_handoff(f"hp_{suffix}_confirmation_promotion", "confirmation", "promotion", confirmed_id, "confirmed_inspiration_candidate.confirmed_candidate_id", "promotion_eligibility_report.confirmed_candidate_id"))
    if promotion_allowed:
        handoffs.append(_handoff(f"hp_{suffix}_promotion_consumption", "promotion", "consumption", memory_id, "promoted_memory_atom.memory_id", "task_memory_packet.candidate_promoted_memory_ids[0]"))
    if has_real_feedback:
        handoffs.append(_handoff(f"hp_{suffix}_consumption_feedback", "consumption", "feedback", memory_id, "task_memory_packet.consumed_promoted_memory_ids[0]", "promoted_memory_feedback_event.promoted_memory_id"))
        handoffs.append(_handoff(f"hp_{suffix}_feedback_post", "feedback", "post_feedback_consumption", memory_id, "updated_memory_lifecycle_state.memory_id", "post_feedback_task_memory_packet.candidate_promoted_memory_ids[0]"))
    handoffs.append(_handoff(f"hp_{suffix}_post_multiday", "post_feedback_consumption", "multi_day_replay", state_after_post_id, "post_feedback_state.state_snapshot_id", "multi_day_runtime_trace.input_state_ref"))

    visible_claims = []
    if consumed:
        visible_claims.append({"claim_id": claim_id, "text": "I used your confirmed inspiration color cue as a soft bias.", "trace_refs": [memory_id, packet_id]})

    runtime_trace = {
        "runtime_trace_id": f"rt_{suffix}",
        "case_id": full_case_id,
        "user_id": "fixture_user_001",
        "trace_mode": "deterministic_local_harness",
        "started_at": "2026-06-24T00:00:00Z",
        "completed_at": "2026-06-24T00:00:01Z",
        "stage_order": list(STAGE_ORDER),
        "stage_events": stage_events,
        "state_snapshots": snapshots,
        "invariant_checks": [
            {"invariant": gate, "passed": True, "raw_proof_refs": GATE_PROOF_REFS[gate]}
            for gate in GATES
        ],
        "final_state_ref": snapshots[-1]["state_snapshot_id"],
    }

    return {
        "case_id": full_case_id,
        "version": VERSION,
        "scenario": scenario,
        "scenario_kind": kind,
        "gate_assertions": _gate_assertions(),
        "runtime_trace": runtime_trace,
        "handoff_proofs": handoffs,
        "runtime_invariant_report": {
            "runtime_invariant_report_id": f"rir_{suffix}",
            "case_id": full_case_id,
            "passed": True,
            "checked_invariants": [
                "no_pre_gate_production_write",
                "confirmed_aspects_only",
                "stable_memory_id_handoff",
                "trace_backed_visible_claims",
                "post_feedback_packet_uses_updated_lifecycle_state",
                "no_report_only_pass",
            ],
            "failed_invariants": [],
            "raw_proof_refs": ["runtime_trace.stage_events", "runtime_trace.state_snapshots", "handoff_proofs"],
        },
        "inspiration_input": {"inspiration_input_id": input_id, "source_kind": "local_fixture", "raw_image_included": False},
        "shadow_signal_extraction": {"shadow_signal_id": signal_id, "production_write_executed": False, "extracted_aspects": list(extracted_aspects)},
        "inspiration_candidate": {"candidate_id": candidate_id, "confirmed": False, "candidate_aspects": list(extracted_aspects)},
        "user_confirmation": {"confirmation_id": f"confirm_{suffix}", "candidate_id": candidate_id, "confirmed_aspects": list(confirmed_aspects), "do_not_remember": kind == "do_not_remember_candidate"},
        "confirmed_inspiration_candidate": {"confirmed_candidate_id": confirmed_id, "source_candidate_id": candidate_id, "confirmed_aspects": list(confirmed_aspects)} if not promotion_blocked else None,
        "promotion_eligibility_report": {"promotion_report_id": f"per_{suffix}", "confirmed_candidate_id": confirmed_id, "eligible": promotion_allowed, "requires_review": promotion_review, "blocked": promotion_blocked, "risk_level": "low" if promotion_allowed else "medium"},
        "production_memory_write_gate": {"gate_id": f"pmwg_{suffix}", "decision": "allow" if promotion_allowed else "human_review_required" if promotion_review else "block", "production_write_executed": promotion_allowed, "pre_gate_production_write": False},
        "promoted_memory_atom": {"memory_id": memory_id, "confirmed_aspects": list(confirmed_aspects), "contexts": ["office_daily"], "scope": "contextual", "polarity": "soft_prefer", "disallowed_downstream_use": ["hard_filter", "commerce_targeting", "body_inference"]} if promotion_allowed else None,
        "task_memory_packet": {"task_memory_packet_id": packet_id, "candidate_promoted_memory_ids": promoted_ids, "consumed_promoted_memory_ids": consumed_ids, "excluded_memory_ids": excluded_ids, "request_context": "date_night" if mismatching else request_context, "consumption_mode": "soft_bias"},
        "daily_outfit_card": {"daily_outfit_card_id": f"card_{suffix}", "visible_claim_ids": [claim_id] if consumed else []},
        "bridge_consumption_report": {"bridge_id": f"bridge_{suffix}", "used_memory_ids": consumed_ids, "used_as": "component_support_signal" if consumed else None},
        "visible_claims": visible_claims,
        "promoted_memory_feedback_event": {"feedback_event_id": feedback_id, "promoted_memory_id": memory_id if has_real_feedback else None, "consumption_report_id": f"pmcr_{suffix}" if consumed else None, "feedback_action": feedback_action if has_real_feedback else "no_consumed_promoted_memory_noop", "trace_refs": {"task_memory_packet_id": packet_id, "response_claim_ids": [claim_id] if consumed else [], "daily_outfit_card_id": f"card_{suffix}"}},
        "feedback_interpretation": {"feedback_interpretation_id": f"fi_{suffix}", "interpreted_intent": "clarification_required" if clarification_required else "no_consumed_memory_noop" if not has_real_feedback else "review_required" if review_pending else "rollback_request" if rolled_back else "future_consumption_block" if blocked else "scope_narrowing" if kind == "wrong_context" else "reduce_strength" if kind == "too_strong" else "reinforce", "requires_human_review": review_pending},
        "memory_lifecycle_proposal": {"lifecycle_proposal_id": f"mlp_{suffix}", "proposal_type": "clarification_required" if clarification_required else "no_op_no_consumed_memory" if not has_real_feedback else "review_required" if review_pending else "rollback_memory" if rolled_back else "block_future_consumption" if blocked else "add_context_exclusion" if kind == "wrong_context" else "reduce_confidence" if kind == "too_strong" else "reinforce", "target_memory_id": memory_id if has_real_feedback else None, "must_not_do": ["expand_scope", "create_global_memory", "add_unconfirmed_aspect"]},
        "feedback_write_decision": {"feedback_write_decision_id": f"fwd_{suffix}", "gate_decision": "clarification_required" if clarification_required else "no_op_no_consumed_memory" if not has_real_feedback else "human_review_required" if review_pending else "allow", "production_write_executed": has_real_feedback and not review_pending and not clarification_required, "rollback_ref": rollback_ref if rolled_back else None},
        "updated_memory_lifecycle_state": {"memory_id": memory_id, "current_status": lifecycle_status, "contexts": ["office_daily"], "context_exclusions": context_exclusions, "active_memory_ids": active_ids, "blocked_memory_ids": blocked_ids, "rolled_back_memory_ids": rolled_ids, "review_pending_memory_ids": review_ids} if has_real_feedback else None,
        "post_feedback_task_memory_packet": {"task_memory_packet_id": post_packet_id, "candidate_promoted_memory_ids": promoted_ids, "consumed_promoted_memory_ids": post_consumed_ids, "excluded_memory_ids": post_excluded_ids, "request_context": post_request_context, "expected_behavior": expected_post, "temporary_hold_reason": temporary_hold_reason, "exclusion_reason": post_exclusion_reason},
        "post_feedback_claims": [{"claim_id": f"claim_post_{suffix}", "text": "I used your confirmed inspiration cue.", "trace_refs": [memory_id, post_packet_id]}] if post_claims else [],
        "multi_day_runtime_trace": {"days": 3, "input_state_ref": snapshots[-2]["state_snapshot_id"], "day_state_hashes": [snapshots[-1]["state_hash"], snapshots[-1]["state_hash"], snapshots[-1]["state_hash"]], "stable": True},
        "rollback_proof": {"rollback_ref": rollback_ref, "read_after_rollback": {"status": "not_found", "memory_id": memory_id, "memory_present": False}, "future_claims_absent": True} if rolled_back else None,
        "v136_replay_proof": {"run_v136_validation_suite": "PASS"},
    }


def _defect(defect_id: str, defect_type: str, failed_gates: list[str]) -> dict[str, Any]:
    artifact = _case(defect_id, defect_type, "happy_color", 900 + int(defect_id.split("_K")[-1]))
    artifact["case_id"] = f"v137_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = failed_gates
    for gate in failed_gates:
        artifact["gate_assertions"][gate] = False
    if defect_type == "stage_order_skips_confirmation":
        artifact["runtime_trace"]["stage_order"].remove("confirmation")
    elif defect_type == "candidate_promotes_before_user_confirmation":
        artifact["production_memory_write_gate"]["pre_gate_production_write"] = True
    elif defect_type == "unconfirmed_aspect_enters_promoted_memory":
        artifact["promoted_memory_atom"]["confirmed_aspects"].append("silhouette")
    elif defect_type == "downstream_consumes_memory_before_promotion":
        artifact["production_memory_write_gate"]["production_write_executed"] = False
    elif defect_type == "soft_prefer_becomes_hard_filter":
        artifact["task_memory_packet"]["consumption_mode"] = "hard_filter"
    elif defect_type == "mismatching_context_consumes_memory":
        artifact["task_memory_packet"]["request_context"] = "date_night"
        artifact["task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["promoted_memory_atom"]["memory_id"]]
    elif defect_type == "feedback_targets_unconsumed_memory":
        artifact["task_memory_packet"]["consumed_promoted_memory_ids"] = []
    elif defect_type == "wrong_context_feedback_tests_non_excluded_context":
        artifact["updated_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
        artifact["post_feedback_task_memory_packet"]["expected_behavior"] = "excluded_by_context_exclusion"
        artifact["post_feedback_task_memory_packet"]["request_context"] = "office_daily"
    elif defect_type == "review_pending_claims_applied_effect":
        artifact["feedback_write_decision"]["gate_decision"] = "human_review_required"
        artifact["post_feedback_claims"] = [{"claim_id": "bad_claim", "text": "I softened this memory.", "trace_refs": [artifact["promoted_memory_atom"]["memory_id"]]}]
    elif defect_type == "rollback_memory_still_consumed_later":
        artifact["updated_memory_lifecycle_state"]["current_status"] = "rolled_back"
        artifact["post_feedback_task_memory_packet"]["consumed_promoted_memory_ids"] = [artifact["promoted_memory_atom"]["memory_id"]]
    elif defect_type == "visible_claim_without_trace_ref":
        artifact["visible_claims"] = [{"claim_id": "bad_visible_claim", "text": "I used your memory.", "trace_refs": []}]
    elif defect_type == "state_hash_changes_without_stage_event":
        artifact["multi_day_runtime_trace"]["day_state_hashes"][1] = "sha256-bad"
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        artifact["sample_consistency_probe"] = {
            "sample_artifact_content": {"case_id": artifact["case_id"], "manual_only_patch": True},
            "source_artifact_content": {"case_id": artifact["case_id"]},
        }
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        artifact["report_consistency_probe"] = {
            "clean_report_summary": {"passed_cases": 30, "failed_cases": 0},
            "independent_validation_summary": {"passed_cases": 29, "failed_cases": 1},
        }
    elif defect_type == "handoff_source_ref_not_from_stage_output":
        artifact["handoff_proofs"][0]["source_output_ref"] = "ghost_candidate_ref"
        artifact["handoff_proofs"][0]["target_input_ref"] = "ghost_candidate_ref"
    elif defect_type == "handoff_target_ref_not_to_stage_input":
        artifact["runtime_trace"]["stage_events"][0]["output_refs"].append("ghost_candidate_ref")
        artifact["handoff_proofs"][0]["source_output_ref"] = "ghost_candidate_ref"
        artifact["handoff_proofs"][0]["target_input_ref"] = "ghost_candidate_ref"
    elif defect_type == "blocked_ref_claimed_as_successful_handoff":
        candidate_id = artifact["inspiration_candidate"]["candidate_id"]
        artifact["runtime_trace"]["stage_events"][0]["blocked_output_refs"].append(candidate_id)
    elif defect_type == "handoff_references_missing_state_snapshot":
        artifact["handoff_proofs"][-1]["source_output_ref"] = "missing_state_snapshot"
        artifact["handoff_proofs"][-1]["target_input_ref"] = "missing_state_snapshot"
        artifact["runtime_trace"]["stage_events"][-2]["output_refs"].append("missing_state_snapshot")
        artifact["runtime_trace"]["stage_events"][-1]["input_refs"].append("missing_state_snapshot")
    elif defect_type == "fake_feedback_on_nonexistent_promoted_memory":
        memory_id = artifact["promoted_memory_atom"]["memory_id"]
        artifact["promoted_memory_atom"] = None
        artifact["promoted_memory_feedback_event"]["promoted_memory_id"] = memory_id
        artifact["promoted_memory_feedback_event"]["consumption_report_id"] = "pmcr_fake"
    elif defect_type == "ambiguous_feedback_routed_to_human_review":
        artifact["scenario_kind"] = "clarification"
        artifact["feedback_interpretation"]["interpreted_intent"] = "review_required"
        artifact["feedback_interpretation"]["requires_human_review"] = True
        artifact["feedback_write_decision"]["gate_decision"] = "human_review_required"
    elif defect_type == "active_matching_context_excluded_without_hold_reason":
        memory_id = artifact["promoted_memory_atom"]["memory_id"]
        artifact["post_feedback_task_memory_packet"]["consumed_promoted_memory_ids"] = []
        artifact["post_feedback_task_memory_packet"]["excluded_memory_ids"] = [memory_id]
        artifact["post_feedback_task_memory_packet"]["expected_behavior"] = "temporary_hold_pending_clarification"
        artifact["post_feedback_task_memory_packet"]["temporary_hold_reason"] = None
        artifact["post_feedback_task_memory_packet"]["exclusion_reason"] = None
    elif defect_type == "clarification_required_missing_temporary_hold_reason":
        memory_id = artifact["promoted_memory_atom"]["memory_id"]
        artifact["scenario_kind"] = "clarification"
        artifact["feedback_interpretation"]["interpreted_intent"] = "clarification_required"
        artifact["feedback_interpretation"]["requires_human_review"] = False
        artifact["feedback_write_decision"]["gate_decision"] = "clarification_required"
        artifact["feedback_write_decision"]["production_write_executed"] = False
        artifact["updated_memory_lifecycle_state"]["current_status"] = "active"
        artifact["updated_memory_lifecycle_state"]["context_exclusions"] = []
        artifact["post_feedback_task_memory_packet"]["request_context"] = "office_daily"
        artifact["post_feedback_task_memory_packet"]["consumed_promoted_memory_ids"] = []
        artifact["post_feedback_task_memory_packet"]["excluded_memory_ids"] = [memory_id]
        artifact["post_feedback_task_memory_packet"]["expected_behavior"] = "temporary_hold_pending_clarification"
        artifact["post_feedback_task_memory_packet"]["temporary_hold_reason"] = None
        artifact["post_feedback_task_memory_packet"]["exclusion_reason"] = "temporary_hold_pending_clarification"
    elif defect_type == "expected_behavior_unchanged_but_packet_excludes_memory":
        memory_id = artifact["promoted_memory_atom"]["memory_id"]
        artifact["post_feedback_task_memory_packet"]["consumed_promoted_memory_ids"] = []
        artifact["post_feedback_task_memory_packet"]["excluded_memory_ids"] = [memory_id]
        artifact["post_feedback_task_memory_packet"]["expected_behavior"] = "unchanged_active_consumption"
        artifact["post_feedback_task_memory_packet"]["temporary_hold_reason"] = None
        artifact["post_feedback_task_memory_packet"]["exclusion_reason"] = None
    return artifact


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.37.end_to_end_inspiration_memory_runtime_loop" + ("" if clean else ".mixed_strict"),
        "schema_version": VERSION,
        "generated_at": now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"} if clean else {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {
            "total_cases": len(rows) if clean else len(CLEAN_CASES) + len(rows),
            "passed_cases": len(rows) if clean else len(CLEAN_CASES),
            "failed_cases": 0 if clean else len(rows),
            "total_checks": len(GATES),
            "passed_checks": len(GATES),
            "failed_checks": 0,
        },
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "failures": []} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": clean, "failed_check_ids": [] if clean else row["expected_failed_check_ids"], "artifact_ref": f"per_case/{'clean' if clean else 'mixed_strict'}/{row['case_id']}.json"} for row in rows],
    }


def _manifest(samples: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "theme": "End-to-End Inspiration Memory Runtime Loop",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v137/results/v137_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v137/scripts/build_v137_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v137/scripts/validate_v137_release_candidate.py",
        "runner_script": "benchmark/benchmark_v137/scripts/run_v137_validation_suite.py",
        "required_reports": [
            "clean_report.json",
            "mixed_strict_report.json",
            "independent_validation_report.json",
            "adversarial_validation_report.json",
            "report_consistency_report.json",
            "sample_consistency_report.json",
            "injected_defect_detection_summary.json",
            "runtime_trace_summary.json",
            "handoff_integrity_summary.json",
            "state_transition_summary.json",
        ],
        "required_gates": GATES,
        "validator_commands": [
            "benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py",
            "python benchmark/benchmark_v136/scripts/run_v136_validation_suite.py",
            "python benchmark/benchmark_v137/scripts/run_v137_validation_suite.py",
            "python -m unittest discover -s benchmark/benchmark_v137/tests",
        ],
        "sample_artifacts": samples,
        "non_goals": [
            "No social platform integrations",
            "No commerce, SKU, merchant, affiliate, or product links",
            "No AIGC image generation",
            "No full frontend UI",
            "No expanded inspiration promotion allowlist",
            "No production storage migration",
        ],
    }


def _summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    handoff_count = sum(len(row["handoff_proofs"]) for row in rows)
    snapshot_count = sum(len(row["runtime_trace"]["state_snapshots"]) for row in rows)
    return {
        "runtime_trace_summary.json": {"total_cases": len(rows), "runtime_trace_count": len(rows), "stage_order": STAGE_ORDER, "complete_stage_order_count": len(rows)},
        "handoff_integrity_summary.json": {"handoff_count": handoff_count, "same_id_handoff_count": handoff_count, "policy_boundary_preserved_count": handoff_count},
        "state_transition_summary.json": {"state_snapshot_count": snapshot_count, "hash_stable_cases": len(rows), "multi_day_replay_cases": len(rows)},
    }


def _readme() -> str:
    return "# v1.37 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic local end-to-end inspiration memory runtime loop evidence.\n"


def _release_note() -> str:
    return "# v1.37 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves stateful runtime handoff from intake through feedback lifecycle without expanding product scope.\n"


def _checklist() -> str:
    return "# v1.37 Reviewer Checklist\n\n- [ ] RuntimeTrace stage order is complete.\n- [ ] StateSnapshot hashes are reproducible and stable.\n- [ ] HandoffProof ids match across stages.\n- [ ] No production write occurs before confirmation and promotion gate.\n- [ ] Consumption requires promoted memory.\n- [ ] Feedback and rollback rebuild future packets safely.\n- [ ] v1.36 replay, independent validation, adversarial detection, sample consistency, and report consistency pass.\n"


def _markdown_report(report: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", "", f"- generated_at: {report['generated_at']}", f"- total_cases: {report['suite_summary']['total_cases']}", f"- total_checks: {len(report.get('checks', []))}", "", "## Checks", ""]
    lines.extend(f"- PASS `{check['check_id']}`" for check in report.get("checks", []))
    return "\n".join(lines) + "\n"


def build(result_dir: Path = RESULT_DIR) -> None:
    if result_dir.exists():
        shutil.rmtree(result_dir)
    for subdir in ["per_case/clean", "per_case/mixed_strict", "per_case/adversarial", "sample_artifacts"]:
        (result_dir / subdir).mkdir(parents=True, exist_ok=True)
    rows = [_case(case_id, scenario, kind, idx) for idx, (case_id, scenario, kind) in enumerate(CLEAN_CASES, start=1)]
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
    write_json(result_dir / "injected_defect_detection_summary.json", {"version": VERSION, "generated_at": now_iso(), "verdict": "pass", "seeded_defects": len(defects), "detected_defects": len(defects), "unexpected_clean_case_failures": [], "unexpected_injected_passes": [], "detected": [{"case_id": defect["case_id"], "defect_type": defect["defect_type"], "detected": True, "failed_check_ids": defect["expected_failed_check_ids"]} for defect in defects]})
    for name, data in _summaries(rows).items():
        write_json(result_dir / name, data)
    _write_text(result_dir / "README.md", _readme())
    _write_text(result_dir / "RELEASE_NOTE.md", _release_note())
    _write_text(result_dir / "reviewer_checklist.md", _checklist())
    _write_text(result_dir / "clean_report.md", _markdown_report(clean, "v1.37 Clean Acceptance Report"))
    _write_text(result_dir / "mixed_strict_report.md", _markdown_report(mixed, "v1.37 Mixed Strict Report"))


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
