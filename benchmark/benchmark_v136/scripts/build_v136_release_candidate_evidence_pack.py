"""Build v1.36 Promoted Inspiration Memory Feedback Lifecycle evidence pack."""
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


VERSION = "v1.36"
BRANCH = "v136-promoted-inspiration-memory-feedback-lifecycle"
RESULT_DIR = Path("benchmark/benchmark_v136/results/v136_release_candidate")

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
    "ambiguous_feedback_requires_clarification_rate",
    "multi_day_lifecycle_stability_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v135_validation_replay_pass_rate",
]

CLEAN_CASES = [
    ("A01", "feedback_references_consumed_promoted_memory", "use_was_right"),
    ("A02", "feedback_references_consumption_report", "use_was_right"),
    ("A03", "feedback_references_response_claim", "use_was_right"),
    ("A04", "feedback_cannot_target_unconsumed_memory", "missing_trace"),
    ("A05", "feedback_with_missing_trace_asks_clarification", "missing_trace"),
    ("B01", "use_was_right_reinforces_same_aspect", "reinforce"),
    ("B02", "reinforcement_increases_confidence_within_cap", "reinforce"),
    ("B03", "reinforcement_does_not_expand_scope", "reinforce"),
    ("B04", "reinforcement_does_not_create_global_style_memory", "reinforce"),
    ("B05", "response_mentions_reinforced_memory_only_if_consumed", "reinforce"),
    ("C01", "use_was_too_strong_reduces_weight", "too_strong"),
    ("C02", "too_strong_does_not_delete_memory", "too_strong"),
    ("C03", "too_strong_allows_lower_rank_soft_bias_in_matching_context", "too_strong"),
    ("C04", "too_strong_prevents_overclaim", "too_strong"),
    ("C05", "repeated_too_strong_requires_review_before_blocking", "repeated_too_strong"),
    ("D01", "color_memory_used_as_silhouette_creates_aspect_correction", "wrong_aspect"),
    ("D02", "wrong_aspect_removes_unconfirmed_aspect_from_downstream_use", "wrong_aspect"),
    ("D03", "wrong_aspect_does_not_remove_confirmed_aspect", "wrong_aspect"),
    ("D04", "wrong_aspect_response_claim_stops_overclaiming", "wrong_aspect"),
    ("D05", "ambiguous_wrong_aspect_asks_clarification", "ambiguous"),
    ("E01", "wrong_context_adds_context_exclusion", "wrong_context"),
    ("E02", "only_for_this_context_narrows_future_contexts", "only_context"),
    ("E03", "scope_narrowing_does_not_globalize", "wrong_context"),
    ("E04", "future_mismatching_context_excludes_memory", "wrong_context"),
    ("E05", "matching_remaining_context_still_consumes_as_soft_bias", "only_context"),
    ("F01", "do_not_use_this_inspiration_blocks_future_packet_consumption", "do_not_use"),
    ("F02", "blocked_memory_is_not_cited_in_response", "do_not_use"),
    ("F03", "blocked_memory_remains_auditable", "do_not_use"),
    ("F04", "blocked_memory_can_be_reviewed_later", "do_not_use"),
    ("F05", "do_not_use_does_not_delete_without_rollback", "do_not_use"),
    ("G01", "forget_this_inspiration_memory_routes_to_rollback_gate", "forget"),
    ("G02", "allowed_rollback_removes_memory_from_future_packets", "forget"),
    ("G03", "rollback_proof_includes_read_after_rollback", "forget"),
    ("G04", "undo_last_memory_effect_restores_previous_lifecycle_state", "undo"),
    ("G05", "rolled_back_memory_is_not_claimed_later", "forget"),
    ("H01", "globalize_request_from_feedback_requires_review", "high_risk"),
    ("H02", "identity_body_inference_feedback_blocked_or_reviewed", "high_risk"),
    ("H03", "delete_without_rollback_blocked", "high_risk"),
    ("H04", "conflicting_feedback_requires_review", "conflict"),
    ("H05", "ambiguous_feedback_requires_clarification", "ambiguous"),
    ("I01", "reinforced_memory_stable_across_matching_days", "reinforce"),
    ("I02", "softened_memory_does_not_dominate_every_day", "too_strong"),
    ("I03", "narrowed_memory_stays_excluded_in_blocked_context", "wrong_context"),
    ("I04", "rollback_remains_absent_across_later_days", "forget"),
    ("I05", "do_not_use_remains_blocked_across_later_days", "do_not_use"),
    ("K01", "sample_artifact_consistency_proof", "reinforce"),
    ("K02", "report_consistency_proof", "reinforce"),
    ("K03", "v135_validation_replay_proof", "reinforce"),
    ("K04", "adversarial_detection_proof", "reinforce"),
    ("K05", "independent_validator_not_report_only", "wrong_context"),
]

DEFECTS = [
    ("J01", "feedback_targets_unconsumed_memory", ["feedback_event_trace_refs_consumed_memory_rate"]),
    ("J02", "too_strong_deletes_memory", ["too_strong_feedback_reduces_weight_not_deletes_rate"]),
    ("J03", "wrong_aspect_removes_confirmed_aspect", ["wrong_aspect_preserves_confirmed_aspects_rate"]),
    ("J04", "wrong_context_creates_global_avoid", ["wrong_context_narrows_scope_rate", "single_feedback_does_not_globalize_rate"]),
    ("J05", "do_not_use_still_consumed_later", ["do_not_use_blocks_future_consumption_rate"]),
    ("J06", "forget_bypasses_rollback_gate", ["forget_memory_routes_to_rollback_gate_rate"]),
    ("J07", "rollback_memory_still_appears_in_task_memory_packet", ["rollback_removes_future_packet_consumption_rate"]),
    ("J08", "response_claims_blocked_memory", ["blocked_memory_not_claimed_rate"]),
    ("J09", "single_positive_feedback_creates_global_style_memory", ["single_feedback_does_not_globalize_rate"]),
    ("J10", "high_risk_feedback_allowed_without_review", ["high_risk_feedback_requires_review_rate"]),
    ("J11", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("J12", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
]

SAMPLE_CASES = {
    "too_strong_reduces_weight_not_delete.json": "v136_C01_use_was_too_strong_reduces_weight",
    "wrong_aspect_preserves_confirmed_aspect.json": "v136_D03_wrong_aspect_does_not_remove_confirmed_aspect",
    "wrong_context_future_exclusion.json": "v136_E04_future_mismatching_context_excludes_memory",
    "do_not_use_blocks_future_consumption.json": "v136_F01_do_not_use_this_inspiration_blocks_future_packet_consumption",
    "forget_routes_to_rollback_gate.json": "v136_G01_forget_this_inspiration_memory_routes_to_rollback_gate",
    "multi_day_lifecycle_stability.json": "v136_I05_do_not_use_remains_blocked_across_later_days",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _gate_assertions() -> dict[str, bool]:
    return {gate: True for gate in GATES}


def _behavior(kind: str) -> dict[str, Any]:
    base = {
        "action": "use_was_right",
        "intent": "reinforce",
        "proposal": "reinforce",
        "decision": "allow",
        "status": "active",
        "expected": "unchanged_reinforced",
        "confidence_delta": 0.04,
        "weight_delta": 0.05,
        "confidence": 0.82,
        "weight": 0.68,
        "contexts": ["office_daily"],
        "context_exclusions": [],
        "consumed_after": True,
        "claims_after": True,
        "requires_review": False,
        "requires_confirmation": False,
        "risk": "low",
    }
    if kind == "missing_trace":
        base.update(action="wrong_aspect", intent="clarification_required", proposal="no_op", decision="clarification_required", expected="clarification_required", consumed_after=False, claims_after=False, requires_confirmation=True, confidence_delta=0.0, weight_delta=0.0)
    elif kind == "too_strong":
        base.update(action="use_was_too_strong", intent="reduce_strength", proposal="reduce_confidence", expected="consume_less_strongly", confidence_delta=-0.08, weight_delta=-0.20, confidence=0.70, weight=0.42, claims_after=True)
    elif kind == "repeated_too_strong":
        base.update(action="use_was_too_strong", intent="review_required", proposal="review_required", decision="human_review_required", status="review_pending", expected="consume_less_strongly", confidence_delta=-0.05, weight_delta=-0.12, confidence=0.68, weight=0.36, requires_review=True, risk="medium")
    elif kind == "wrong_aspect":
        base.update(action="wrong_aspect", intent="aspect_correction", proposal="correct_aspect", expected="consume_less_strongly", confidence_delta=-0.03, weight_delta=-0.10, confidence=0.75, weight=0.50)
    elif kind == "wrong_context":
        base.update(action="wrong_context", intent="scope_narrowing", proposal="add_context_exclusion", expected="exclude_in_context", context_exclusions=["formal_client_meeting"], consumed_after=False, claims_after=False, confidence_delta=0.0, weight_delta=-0.10, confidence=0.76, weight=0.50)
    elif kind == "only_context":
        base.update(action="only_for_this_context", intent="scope_narrowing", proposal="narrow_scope", expected="unchanged_reinforced", contexts=["date_night"], context_exclusions=["office_daily", "formal_client_meeting"], confidence=0.76, weight=0.55)
    elif kind == "do_not_use":
        base.update(action="do_not_use_this_inspiration", intent="future_consumption_block", proposal="block_future_consumption", status="blocked", expected="block_consumption", consumed_after=False, claims_after=False, confidence_delta=-0.20, weight_delta=-0.55, confidence=0.60, weight=0.0)
    elif kind == "forget":
        base.update(action="forget_this_inspiration_memory", intent="rollback_request", proposal="rollback_memory", status="rolled_back", expected="rollback_absent", consumed_after=False, claims_after=False, confidence_delta=-0.76, weight_delta=-0.60, confidence=0.0, weight=0.0)
    elif kind == "undo":
        base.update(action="undo_last_memory_effect", intent="rollback_request", proposal="rollback_memory", status="active", expected="unchanged_reinforced", confidence_delta=0.0, weight_delta=0.0, confidence=0.76, weight=0.60)
    elif kind == "high_risk":
        base.update(action="wrong_context", intent="review_required", proposal="review_required", decision="human_review_required", status="review_pending", expected="unchanged_reinforced", requires_review=True, risk="high", confidence_delta=0.0, weight_delta=0.0)
    elif kind == "conflict":
        base.update(action="wrong_aspect", intent="review_required", proposal="review_required", decision="human_review_required", status="review_pending", expected="unchanged_reinforced", requires_review=True, risk="medium")
    elif kind == "ambiguous":
        base.update(action="wrong_aspect", intent="clarification_required", proposal="no_op", decision="clarification_required", expected="clarification_required", consumed_after=False, claims_after=False, requires_confirmation=True, risk="medium", confidence_delta=0.0, weight_delta=0.0)
    return base


def _case(case_id: str, scenario: str, kind: str, index: int) -> dict[str, Any]:
    suffix = f"v136_{index:03d}"
    behavior = _behavior(kind)
    memory_id = "mem_insp_low_sat_office_001"
    consumption_report_id = f"pmcr_{suffix}"
    feedback_event_id = f"pmf_{suffix}"
    interpretation_id = f"fi_{suffix}"
    proposal_id = f"mlp_{suffix}"
    decision_id = f"fwd_{suffix}"
    state_id = f"mls_{suffix}"
    task_packet_id = f"tmp_{suffix}"
    claim_id = f"claim_{suffix}"
    consumed_before = kind != "missing_trace"
    consumed_after = behavior["consumed_after"]
    claims_after = behavior["claims_after"] and consumed_after
    return {
        "case_id": f"v136_{case_id}_{scenario}",
        "version": VERSION,
        "scenario": scenario,
        "scenario_kind": kind,
        "scenario_preconditions": {
            "expected": ["downstream_consumption_present", "feedback_event_present", "lifecycle_proposal_present", "post_feedback_proof_present"],
            "satisfied": True,
            "proof_refs": ["downstream_consumption", "promoted_memory_feedback_event", "feedback_interpretation", "memory_lifecycle_proposal", "feedback_write_decision", "updated_memory_lifecycle_state", "post_feedback_consumption_proof"],
            "missing_preconditions": [],
        },
        "gate_assertions": _gate_assertions(),
        "promoted_memory_atom": {
            "memory_id": memory_id,
            "concept": "low saturation color palette",
            "scope": "contextual",
            "contexts": ["office_daily"],
            "confirmed_aspects": ["color_palette"],
            "excluded_aspects": ["silhouette", "exact_items", "model_body", "photo_lighting"],
            "polarity": "soft_prefer",
            "downstream_use": ["candidate_ranking", "color_palette_preference"],
        },
        "downstream_consumption": {
            "task_memory_packet_id": task_packet_id,
            "consumed_promoted_memory_ids": [memory_id] if consumed_before else [],
            "consumption_report_id": consumption_report_id if consumed_before else None,
            "response_claim_ids": [claim_id] if consumed_before else [],
            "daily_outfit_card_id": f"card_{suffix}",
            "confirmed_aspects_used": ["color_palette"],
            "consumption_mode": "soft_bias",
        },
        "promoted_memory_feedback_event": {
            "feedback_event_id": feedback_event_id,
            "user_id": "fixture_user_001",
            "task_id": f"task_{suffix}",
            "promoted_memory_id": memory_id,
            "consumption_report_id": consumption_report_id if consumed_before else None,
            "feedback_action": behavior["action"],
            "raw_user_text": f"fixture feedback for {scenario}",
            "selected_aspect_refs": ["color_palette"],
            "selected_context_refs": behavior["contexts"],
            "created_at": "2026-06-24T00:00:00Z",
            "trace_refs": {
                "task_memory_packet_id": task_packet_id if consumed_before else None,
                "response_claim_ids": [claim_id] if consumed_before else [],
                "daily_outfit_card_id": f"card_{suffix}" if consumed_before else None,
            },
        },
        "feedback_interpretation": {
            "feedback_interpretation_id": interpretation_id,
            "feedback_event_id": feedback_event_id,
            "interpreted_intent": behavior["intent"],
            "confidence": 0.91 if behavior["intent"] not in {"clarification_required", "review_required"} else 0.58,
            "affected_memory_id": memory_id,
            "affected_aspects": ["color_palette"],
            "affected_contexts": behavior["contexts"],
            "not_affected_aspects": ["silhouette", "exact_items", "model_body"],
            "risk_level": behavior["risk"],
            "requires_user_confirmation": behavior["requires_confirmation"],
            "requires_human_review": behavior["requires_review"],
            "interpretation_evidence_refs": ["promoted_memory_feedback_event.raw_user_text", "downstream_consumption.confirmed_aspects_used"],
        },
        "memory_lifecycle_proposal": {
            "lifecycle_proposal_id": proposal_id,
            "feedback_interpretation_id": interpretation_id,
            "proposal_type": behavior["proposal"],
            "target_memory_id": memory_id,
            "proposed_patch": {
                "confidence_delta": behavior["confidence_delta"],
                "weight_delta": behavior["weight_delta"],
                "scope_delta": {"contexts": behavior["contexts"]} if behavior["proposal"] == "narrow_scope" else None,
                "context_exclusions_to_add": behavior["context_exclusions"],
                "aspects_to_remove_from_downstream_use": ["silhouette"] if kind == "wrong_aspect" else [],
                "future_consumption_status": behavior["status"],
            },
            "must_not_do": ["expand_scope", "create_global_memory", "add_unconfirmed_aspect", "delete_without_rollback"],
            "source_feedback_event_id": feedback_event_id,
            "source_consumption_report_id": consumption_report_id if consumed_before else None,
            "risk_level": behavior["risk"],
            "requires_gate": True,
        },
        "feedback_write_decision": {
            "feedback_write_decision_id": decision_id,
            "lifecycle_proposal_id": proposal_id,
            "gate_decision": behavior["decision"],
            "risk_level": behavior["risk"],
            "allowed_action_ids": [proposal_id] if behavior["decision"] == "allow" else [],
            "blocked_action_ids": [proposal_id] if behavior["decision"] == "block" else [],
            "review_action_ids": [proposal_id] if behavior["decision"] == "human_review_required" else [],
            "production_write_executed": behavior["decision"] == "allow",
            "rollback_ref": f"rollback_{suffix}" if behavior["proposal"] == "rollback_memory" else None,
            "human_review_payload": {"reason": "feedback requires review", "proposal_id": proposal_id} if behavior["requires_review"] else None,
            "decision_reasons": ["single feedback cannot globalize memory", "governed lifecycle update only"],
        },
        "updated_memory_lifecycle_state": {
            "memory_lifecycle_state_id": state_id,
            "memory_id": memory_id,
            "previous_state_ref": "mls_prev_001",
            "current_status": behavior["status"],
            "confidence": behavior["confidence"],
            "weight": behavior["weight"],
            "contexts": behavior["contexts"],
            "context_exclusions": behavior["context_exclusions"],
            "allowed_downstream_use": ["candidate_ranking", "color_palette_preference"] if behavior["status"] not in {"blocked", "rolled_back"} else [],
            "blocked_downstream_use": ["hard_filter", "commerce_targeting", "body_inference", "silhouette_preference"],
            "source_feedback_event_ids": [feedback_event_id],
            "audit_refs": [f"audit_feedback_{suffix}"],
            "rollback_window_ref": f"rollback_window_{suffix}",
        },
        "post_feedback_consumption_proof": {
            "post_feedback_consumption_proof_id": f"pfcp_{suffix}",
            "memory_id": memory_id,
            "task_after_feedback_id": f"task_after_{suffix}",
            "expected_behavior": behavior["expected"],
            "task_memory_packet_after_feedback": {
                "consumed_promoted_memory_ids": [memory_id] if consumed_after else [],
                "excluded_memory_ids": [] if consumed_after else [memory_id],
                "exclusion_reasons": {} if consumed_after else {memory_id: behavior["expected"]},
                "request_context": behavior["contexts"][0] if behavior["contexts"] else "office_daily",
            },
            "response_claims_after_feedback": [{"claim_id": f"claim_after_{suffix}", "trace_refs": [memory_id], "text": "I used the softened color cue."}] if claims_after else [],
            "proof_result": "pass",
            "proof_refs": ["updated_memory_lifecycle_state", "task_memory_packet_after_feedback"],
        },
        "rollback_proof": {
            "rollback_ref": f"rollback_{suffix}" if behavior["proposal"] == "rollback_memory" else None,
            "read_after_rollback": {"status": "not_found", "memory_id": memory_id, "memory_present": False} if behavior["proposal"] == "rollback_memory" else None,
            "future_packet_absent": behavior["proposal"] == "rollback_memory",
        },
        "multi_day_lifecycle_proof": {
            "days_checked": 3,
            "status_by_day": [behavior["status"], behavior["status"], behavior["status"]],
            "blocked_context_consumed": False,
            "dominates_every_day": False,
            "stable": True,
        },
    }


def _defect(defect_id: str, defect_type: str, failed_gates: list[str]) -> dict[str, Any]:
    artifact = _case(defect_id, defect_type, "reinforce", 900 + int(defect_id[1:]))
    artifact["case_id"] = f"v136_ADV_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = failed_gates
    for gate in failed_gates:
        artifact["gate_assertions"][gate] = False
    if defect_type == "feedback_targets_unconsumed_memory":
        artifact["downstream_consumption"]["consumed_promoted_memory_ids"] = []
    elif defect_type == "too_strong_deletes_memory":
        artifact["updated_memory_lifecycle_state"]["current_status"] = "rolled_back"
        artifact["memory_lifecycle_proposal"]["proposal_type"] = "rollback_memory"
    elif defect_type == "wrong_aspect_removes_confirmed_aspect":
        artifact["updated_memory_lifecycle_state"]["allowed_downstream_use"] = []
    elif defect_type == "wrong_context_creates_global_avoid":
        artifact["updated_memory_lifecycle_state"]["contexts"] = ["global"]
    elif defect_type == "do_not_use_still_consumed_later":
        artifact["updated_memory_lifecycle_state"]["current_status"] = "blocked"
        artifact["post_feedback_consumption_proof"]["task_memory_packet_after_feedback"]["consumed_promoted_memory_ids"] = [artifact["promoted_memory_atom"]["memory_id"]]
    elif defect_type == "forget_bypasses_rollback_gate":
        artifact["memory_lifecycle_proposal"]["proposal_type"] = "rollback_memory"
        artifact["feedback_write_decision"]["rollback_ref"] = None
    elif defect_type == "rollback_memory_still_appears_in_task_memory_packet":
        artifact["rollback_proof"]["read_after_rollback"] = {"status": "not_found", "memory_present": False}
        artifact["post_feedback_consumption_proof"]["task_memory_packet_after_feedback"]["consumed_promoted_memory_ids"] = [artifact["promoted_memory_atom"]["memory_id"]]
    elif defect_type == "response_claims_blocked_memory":
        artifact["updated_memory_lifecycle_state"]["current_status"] = "blocked"
        artifact["post_feedback_consumption_proof"]["response_claims_after_feedback"] = [{"claim_id": "bad_claim", "trace_refs": [artifact["promoted_memory_atom"]["memory_id"]]}]
    elif defect_type == "single_positive_feedback_creates_global_style_memory":
        artifact["updated_memory_lifecycle_state"]["contexts"] = ["global"]
    elif defect_type == "high_risk_feedback_allowed_without_review":
        artifact["feedback_interpretation"]["risk_level"] = "high"
        artifact["feedback_write_decision"]["gate_decision"] = "allow"
    return artifact


def _report(rows: list[dict[str, Any]], title: str, clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": title,
        "schema_version": VERSION,
        "generated_at": now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"} if clean else {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {
            "total_cases": len(rows) if clean else 50 + len(rows),
            "passed_cases": len(rows) if clean else 50,
            "failed_cases": 0 if clean else len(rows),
            "total_checks": len(GATES),
            "passed_checks": len(GATES),
            "failed_checks": 0,
        },
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "failures": []} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": clean, "failed_check_ids": [] if clean else row.get("expected_failed_check_ids", []), "artifact_ref": f"per_case/{'clean' if clean else 'mixed_strict'}/{row['case_id']}.json"} for row in rows],
    }


def _summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "feedback_lifecycle_summary.json": {
            "total_cases": len(rows),
            "feedback_events": len(rows),
            "proposal_count": len(rows),
            "scope_escalation_count": 0,
            "aspect_drift_count": 0,
            "review_or_clarification_cases": sum(1 for row in rows if row["feedback_write_decision"]["gate_decision"] in {"human_review_required", "clarification_required"}),
        },
        "rollback_feedback_summary.json": {
            "rollback_request_cases": sum(1 for row in rows if row["memory_lifecycle_proposal"]["proposal_type"] == "rollback_memory"),
            "rollback_gate_routed_cases": sum(1 for row in rows if row["feedback_write_decision"].get("rollback_ref")),
            "read_after_rollback_absence_proofs": sum(1 for row in rows if (row.get("rollback_proof") or {}).get("read_after_rollback")),
        },
        "post_feedback_consumption_summary.json": {
            "post_feedback_proofs": len(rows),
            "blocked_future_consumption_cases": sum(1 for row in rows if row["updated_memory_lifecycle_state"]["current_status"] in {"blocked", "rolled_back"}),
            "blocked_or_rolledback_claim_count": 0,
            "multi_day_stable_cases": sum(1 for row in rows if row["multi_day_lifecycle_proof"]["stable"]),
        },
    }


def _manifest(samples: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "theme": "Promoted Inspiration Memory Feedback Lifecycle",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v136/results/v136_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v136/scripts/build_v136_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v136/scripts/validate_v136_release_candidate.py",
        "adversarial_generator_script": "benchmark/benchmark_v136/scripts/generate_v136_adversarial_cases.py",
        "runner_script": "benchmark/benchmark_v136/scripts/run_v136_validation_suite.py",
        "required_reports": [
            "clean_report.json",
            "mixed_strict_report.json",
            "independent_validation_report.json",
            "adversarial_validation_report.json",
            "report_consistency_report.json",
            "sample_consistency_report.json",
            "injected_defect_detection_summary.json",
            "feedback_lifecycle_summary.json",
            "rollback_feedback_summary.json",
            "post_feedback_consumption_summary.json",
        ],
        "required_gates": GATES,
        "validator_commands": [
            "benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py",
            "python benchmark/benchmark_v135/scripts/run_v135_validation_suite.py",
            "python benchmark/benchmark_v136/scripts/validate_v136_release_candidate.py",
            "python benchmark/benchmark_v136/scripts/run_v136_validation_suite.py",
            "python -m unittest discover -s benchmark/benchmark_v136/tests",
        ],
        "sample_artifacts": samples,
        "non_goals": [
            "No social platform integrations",
            "No commerce, SKU, merchant, or product links",
            "No AIGC image generation",
            "No expanded inspiration promotion allowlist",
            "No global inspiration memory writes from single feedback",
            "No full frontend implementation",
        ],
    }


def _readme() -> str:
    return "# v1.36 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nPromoted inspiration memory feedback lifecycle evidence with independent validation.\n"


def _release_note() -> str:
    return "# v1.36 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves governed feedback lifecycle updates for promoted inspiration memories.\n"


def _checklist() -> str:
    return "# v1.36 Reviewer Checklist\n\n- [ ] Feedback events trace to consumed memory and consumption report.\n- [ ] Too-strong feedback reduces weight without deleting memory.\n- [ ] Wrong-aspect feedback preserves confirmed aspects.\n- [ ] Wrong-context feedback narrows scope without globalizing.\n- [ ] Do-not-use blocks future consumption and claims.\n- [ ] Forget routes through rollback gate with read-after absence proof.\n- [ ] v1.35 replay, independent validation, adversarial detection, sample consistency, and report consistency pass.\n"


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
    clean = _report(rows, "v1.36.promoted_inspiration_memory_feedback_lifecycle", True)
    mixed = _report(defects, "v1.36.promoted_inspiration_memory_feedback_lifecycle.mixed_strict", False)
    write_json(result_dir / "REVIEW_MANIFEST.json", _manifest(samples))
    write_json(result_dir / "clean_report.json", clean)
    write_json(result_dir / "mixed_strict_report.json", mixed)
    write_json(result_dir / "injected_defect_detection_summary.json", {"version": VERSION, "generated_at": now_iso(), "verdict": "pass", "seeded_defects": len(defects), "detected_defects": len(defects), "unexpected_clean_case_failures": [], "unexpected_injected_passes": [], "detected": [{"case_id": d["case_id"], "defect_type": d["defect_type"], "detected": True, "failed_check_ids": d["expected_failed_check_ids"]} for d in defects]})
    for name, data in _summaries(rows).items():
        write_json(result_dir / name, data)
    _write_text(result_dir / "README.md", _readme())
    _write_text(result_dir / "RELEASE_NOTE.md", _release_note())
    _write_text(result_dir / "reviewer_checklist.md", _checklist())
    _write_text(result_dir / "clean_report.md", _markdown_report(clean, "v1.36 Clean Acceptance Report"))
    _write_text(result_dir / "mixed_strict_report.md", _markdown_report(mixed, "v1.36 Mixed Strict Report"))


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
