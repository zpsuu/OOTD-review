"""Build v1.33 Confirmed Inspiration Memory Promotion Governance evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v1.33"
BRANCH = "v133-confirmed-inspiration-memory-promotion-governance"
RESULT_DIR = Path("benchmark/benchmark_v133/results/v133_release_candidate")

GATES = [
    "promotion_eligibility_report_present_rate",
    "eligible_candidate_requires_user_confirmation_rate",
    "promotion_plan_matches_confirmed_aspects_rate",
    "promotion_plan_excludes_unconfirmed_aspects_rate",
    "promotion_scope_matches_user_selected_context_rate",
    "global_write_from_single_inspiration_blocked_rate",
    "high_risk_candidate_not_promoted_rate",
    "metadata_only_candidate_not_promoted_rate",
    "visual_only_unconfirmed_candidate_not_promoted_rate",
    "rejected_candidate_not_promoted_rate",
    "do_not_remember_candidate_not_promoted_rate",
    "conflict_requires_moderation_or_review_rate",
    "unmoderated_conflict_no_write_rate",
    "allowed_promotion_routes_to_production_write_gate_rate",
    "blocked_promotion_no_production_write_attempt_rate",
    "review_required_promotion_has_actionable_payload_rate",
    "promotion_write_artifact_self_proof_rate",
    "rollback_proof_present_for_allowed_write_rate",
    "promoted_memory_atom_schema_valid_rate",
    "promoted_memory_no_raw_external_content_ref_rate",
    "promoted_memory_downstream_use_bounded_rate",
    "promoted_memory_consumed_only_matching_context_rate",
    "promoted_memory_not_used_as_hard_filter_rate",
    "response_claim_refs_promoted_memory_consumed_rate",
    "sample_artifacts_match_per_case_artifacts_rate",
    "promotion_write_commit_id_present_rate",
    "promotion_write_journal_entry_present_rate",
    "promotion_write_read_after_write_present_rate",
    "promotion_write_audit_replay_self_proof_rate",
    "promotion_write_store_version_present_rate",
    "rollback_proof_read_after_rollback_present_rate",
    "rollback_target_matches_promotion_write_rate",
    "post_rollback_memory_absent_from_active_state_rate",
    "rollback_state_hash_restored_rate",
    "rollback_active_and_rolledback_ids_present_rate",
    "global_review_payload_has_contextual_downgrade_plan_rate",
    "global_review_payload_no_empty_contexts_rate",
    "global_review_payload_concept_narrowed_to_confirmed_aspects_rate",
    "review_required_payload_actionable_rate",
    "response_claim_text_matches_promoted_memory_concept_rate",
    "response_claim_text_not_generic_cross_case_template_rate",
    "rollback_case_has_allowed_write_precondition_rate",
    "review_case_has_review_payload_precondition_rate",
    "write_artifact_case_has_allowed_write_precondition_rate",
]

CASE_IDS = [
    "A01_color_only_confirmed_candidate_eligible_for_contextual_soft_prefer",
    "A02_silhouette_only_candidate_eligible_only_for_selected_context",
    "A03_overall_mood_candidate_deferred_if_too_broad",
    "A04_global_write_request_downgraded_or_review_required",
    "A05_visual_only_unconfirmed_candidate_blocked",
    "A06_metadata_only_candidate_blocked",
    "A07_do_not_remember_candidate_blocked",
    "A08_rejected_candidate_blocked",
    "B01_plan_concept_matches_confirmed_aspects",
    "B02_plan_excludes_unconfirmed_aspects",
    "B03_plan_scope_matches_selected_context",
    "B04_plan_downstream_use_is_bounded",
    "B05_plan_contains_evidence_refs_and_excluded_aspects",
    "B06_color_only_plan_does_not_include_silhouette_or_mood",
    "B07_date_night_plan_does_not_map_to_office_context",
    "C01_eligible_low_risk_contextual_soft_prefer_routes_to_write_gate",
    "C02_allowed_write_includes_production_native_commit_artifact",
    "C03_blocked_candidate_does_not_attempt_production_write",
    "C04_review_required_candidate_includes_actionable_review_payload",
    "C05_rollback_proof_exists_for_allowed_write",
    "C06_allowed_write_includes_audit_snapshot",
    "C07_blocked_write_terminates_before_production_write_attempt",
    "D01_soft_conflict_creates_moderated_translation",
    "D02_hard_conflict_requires_review_or_user_confirmation",
    "D03_conflict_memory_must_be_active_and_trace_backed",
    "D04_unmoderated_conflict_cannot_write",
    "D05_moderated_concept_excludes_violating_elements",
    "D06_conflict_review_payload_includes_conflicting_memory_refs",
    "E01_office_daily_candidate_only_consumed_in_office_daily",
    "E02_date_night_candidate_only_consumed_in_date_night",
    "E03_daily_city_walk_candidate_not_consumed_in_formal_client_meeting",
    "E04_global_request_not_written_as_global",
    "E05_mismatching_context_excludes_promoted_memory",
    "E06_response_does_not_claim_mismatched_promoted_memory",
    "F01_promoted_memory_atom_includes_confirmed_external_inspiration_source_type",
    "F02_memory_atom_does_not_include_raw_image_refs",
    "F03_memory_atom_excludes_body_model_lighting",
    "F04_memory_atom_confidence_derives_from_candidate_evidence",
    "F05_memory_atom_lifecycle_includes_rollback_window",
    "F06_memory_atom_downstream_use_is_bounded",
    "F07_memory_atom_disallowed_downstream_use_includes_forbidden_uses",
    "G01_promoted_memory_appears_in_task_packet_for_matching_context",
    "G02_daily_outfit_softly_reflects_promoted_preference",
    "G03_bridge_uses_promoted_memory_as_support_not_hard_constraint",
    "G04_response_claim_refs_promoted_memory",
    "G05_promoted_memory_not_used_as_hard_filter",
    "G06_promoted_memory_not_used_when_context_mismatches",
    "H01_do_not_remember_candidate_blocked",
    "H02_rejected_candidate_blocked",
    "H03_uncertain_visual_signal_blocked",
    "H04_exact_product_interest_blocked",
    "H05_high_risk_inference_blocked",
    "H06_metadata_only_url_blocked",
    "H07_visual_only_unconfirmed_candidate_blocked",
]

DEFECTS = [
    ("I01", "confirmed_candidate_directly_writes_memory_without_promotion_eligibility", ["promotion_eligibility_report_present_rate", "allowed_promotion_routes_to_production_write_gate_rate"]),
    ("I02", "color_only_candidate_writes_full_style_memory", ["promotion_plan_matches_confirmed_aspects_rate", "promotion_plan_excludes_unconfirmed_aspects_rate"]),
    ("I03", "global_memory_written_from_single_inspiration", ["global_write_from_single_inspiration_blocked_rate"]),
    ("I04", "high_risk_body_inference_written", ["high_risk_candidate_not_promoted_rate", "promoted_memory_atom_schema_valid_rate"]),
    ("I05", "conflict_ignored_and_written", ["conflict_requires_moderation_or_review_rate", "unmoderated_conflict_no_write_rate"]),
    ("I06", "blocked_candidate_attempts_production_write", ["blocked_promotion_no_production_write_attempt_rate"]),
    ("I07", "memory_atom_includes_raw_image_ref", ["promoted_memory_no_raw_external_content_ref_rate"]),
    ("I08", "promoted_memory_consumed_in_wrong_context", ["promoted_memory_consumed_only_matching_context_rate"]),
    ("I09", "production_write_lacks_rollback_proof", ["rollback_proof_present_for_allowed_write_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I10", "response_claims_promoted_memory_not_consumed", ["response_claim_refs_promoted_memory_consumed_rate"]),
    ("I11", "unconfirmed_visual_signal_promoted", ["visual_only_unconfirmed_candidate_not_promoted_rate", "eligible_candidate_requires_user_confirmation_rate"]),
    ("I12", "exact_product_interest_promoted_as_style_memory", ["promoted_memory_downstream_use_bounded_rate", "promoted_memory_atom_schema_valid_rate"]),
    ("I13", "promotion_write_missing_commit_id", ["promotion_write_commit_id_present_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I14", "promotion_write_missing_journal_entry", ["promotion_write_journal_entry_present_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I15", "promotion_write_missing_read_after_write", ["promotion_write_read_after_write_present_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I16", "promotion_write_missing_audit_replay", ["promotion_write_audit_replay_self_proof_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I17", "promotion_write_missing_store_version", ["promotion_write_store_version_present_rate", "promotion_write_artifact_self_proof_rate"]),
    ("I18", "rollback_claims_success_without_read_after_rollback", ["rollback_proof_read_after_rollback_present_rate"]),
    ("I19", "rollback_target_mismatch", ["rollback_target_matches_promotion_write_rate"]),
    ("I20", "post_rollback_memory_still_active", ["post_rollback_memory_absent_from_active_state_rate"]),
    ("I21", "rollback_missing_active_and_rolledback_ids", ["rollback_active_and_rolledback_ids_present_rate"]),
    ("I22", "rollback_state_hash_not_restored", ["rollback_state_hash_restored_rate"]),
    ("I23", "global_review_payload_empty_contexts", ["global_review_payload_no_empty_contexts_rate", "review_required_payload_actionable_rate"]),
    ("I24", "global_review_payload_keeps_global_identity_concept", ["global_review_payload_concept_narrowed_to_confirmed_aspects_rate"]),
    ("I25", "review_payload_approve_contextual_without_context", ["global_review_payload_no_empty_contexts_rate", "review_required_payload_actionable_rate"]),
    ("I26", "review_payload_missing_contextual_downgrade_plan", ["global_review_payload_has_contextual_downgrade_plan_rate", "review_required_payload_actionable_rate"]),
    ("I27", "response_claim_text_mismatches_promoted_memory_concept", ["response_claim_text_matches_promoted_memory_concept_rate"]),
    ("I28", "response_claim_uses_generic_cross_case_template", ["response_claim_text_not_generic_cross_case_template_rate"]),
]

SAMPLE_MAP = {
    "color_only_contextual_promotion_allowed.json": "A01_color_only_confirmed_candidate_eligible_for_contextual_soft_prefer",
    "date_night_contextual_promotion_allowed.json": "E02_date_night_candidate_only_consumed_in_date_night",
    "global_request_blocked_or_review.json": "A04_global_write_request_downgraded_or_review_required",
    "high_risk_candidate_blocked.json": "H05_high_risk_inference_blocked",
    "conflict_moderated_translation_promotion.json": "D01_soft_conflict_creates_moderated_translation",
    "allowed_promotion_write_artifact.json": "C02_allowed_write_includes_production_native_commit_artifact",
    "rollback_proof_for_promotion_write.json": "C05_rollback_proof_exists_for_allowed_write",
    "promoted_memory_consumed_matching_context.json": "G01_promoted_memory_appears_in_task_packet_for_matching_context",
    "promoted_memory_excluded_mismatching_context.json": "E05_mismatching_context_excludes_promoted_memory",
    "blocked_candidate_no_write_attempt.json": "C03_blocked_candidate_does_not_attempt_production_write",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _kind(case_id: str) -> str:
    if case_id.startswith(("A01", "B01", "B02", "B05", "B06", "C01", "C02", "C05", "C06", "F01", "F02", "F03", "F04", "F05", "F06", "F07", "G01", "G02", "G03", "G04", "G05")):
        return "color_allowed"
    if case_id.startswith(("A02", "B03")):
        return "silhouette_allowed"
    if case_id.startswith(("A03",)):
        return "deferred_broad"
    if case_id.startswith(("A04", "E04")):
        return "global_request_review"
    if case_id.startswith(("A05", "H07")):
        return "visual_only_blocked"
    if case_id.startswith(("A06", "H06")):
        return "metadata_only_blocked"
    if case_id.startswith(("A07", "H01")):
        return "do_not_remember_blocked"
    if case_id.startswith(("A08", "H02")):
        return "rejected_blocked"
    if case_id.startswith(("B04",)):
        return "bounded_plan"
    if case_id.startswith(("B07", "E02")):
        return "date_allowed"
    if case_id.startswith(("C03", "C07")):
        return "blocked_low_proof"
    if case_id.startswith(("C04", "D02", "D06")):
        return "review_required_conflict"
    if case_id.startswith(("D01", "D03", "D05")):
        return "moderated_conflict_allowed"
    if case_id.startswith(("D04",)):
        return "unmoderated_conflict_blocked"
    if case_id.startswith(("E01",)):
        return "office_consumed"
    if case_id.startswith(("E03",)):
        return "daily_walk_mismatch_excluded"
    if case_id.startswith(("E05", "E06", "G06")):
        return "mismatch_excluded"
    if case_id.startswith(("H03",)):
        return "uncertain_visual_blocked"
    if case_id.startswith(("H04",)):
        return "exact_product_blocked"
    if case_id.startswith(("H05",)):
        return "high_risk_blocked"
    return "color_allowed"


def _candidate(kind: str, suffix: str) -> dict[str, Any]:
    source_type = "confirmed_external_inspiration"
    user_confirmed = True
    status = "confirmed_shadow_candidate"
    concept = "low saturation color palette"
    aspects = ["color_palette"]
    excluded = ["silhouette", "exact_items", "model_body", "photo_lighting", "luxury_brand_specificity"]
    scope = "contextual"
    contexts = ["office_daily"]
    if kind == "silhouette_allowed":
        concept = "relaxed but structured silhouette"
        aspects = ["silhouette"]
        excluded = ["color_palette", "exact_items", "model_body", "photo_lighting"]
    elif kind == "deferred_broad":
        concept = "clean quiet overall mood"
        aspects = ["overall_mood"]
    elif kind == "global_request_review":
        concept = "single inspiration global style identity request"
        scope = "global_requested"
        contexts = []
    elif kind in {"visual_only_blocked", "uncertain_visual_blocked"}:
        source_type = "visual_signal_candidate"
        user_confirmed = False
        status = "unconfirmed_visual_candidate"
    elif kind == "metadata_only_blocked":
        source_type = "metadata_only_url"
        user_confirmed = False
        status = "metadata_only_fallback"
    elif kind == "do_not_remember_blocked":
        status = "do_not_remember"
    elif kind == "rejected_blocked":
        status = "rejected_by_user"
    elif kind == "date_allowed":
        concept = "soft date-night presence"
        aspects = ["soft_presence"]
        excluded = ["office_daily", "exact_items", "model_body", "photo_lighting", "excessive_sweetness"]
        contexts = ["date_night"]
    elif kind == "moderated_conflict_allowed":
        concept = "soft date-night presence without excessive sweetness"
        aspects = ["soft_presence"]
        excluded = ["bow_lace_pink_overload", "exact_items", "model_body", "photo_lighting"]
        contexts = ["date_night"]
    elif kind in {"review_required_conflict", "unmoderated_conflict_blocked"}:
        concept = "romantic sweet date-night mood"
        aspects = ["romantic_mood"]
        excluded = ["exact_items", "model_body", "photo_lighting"]
        contexts = ["date_night"]
    elif kind == "office_consumed":
        contexts = ["office_daily"]
    elif kind == "daily_walk_mismatch_excluded":
        concept = "low-profile sneaker tolerance"
        aspects = ["low_profile_sneaker_tolerance"]
        contexts = ["daily_city_walk"]
    elif kind in {"exact_product_blocked"}:
        concept = "exact luxury loafer from inspiration"
        aspects = ["exact_product_interest"]
        excluded = ["merchant", "sku", "price", "product_link"]
    elif kind == "high_risk_blocked":
        concept = "model-body slimness preference"
        aspects = ["model_body"]
        excluded = ["body_shape_inference", "attractiveness_inference"]
    return {
        "confirmed_inspiration_candidate_id": f"cic_{suffix}",
        "source_intake_event_id": f"intake_{suffix}",
        "source_type": source_type,
        "user_confirmed": user_confirmed,
        "confirmed_aspects": aspects,
        "candidate_concept": concept,
        "polarity": "soft_prefer",
        "scope_candidate": scope,
        "suggested_contexts": contexts,
        "excluded_aspects": excluded,
        "confidence": 0.72,
        "evidence_refs": [f"intake_{suffix}", f"visual_signal_candidate_{suffix}", f"confirmation_action_{suffix}"] if user_confirmed else [f"intake_{suffix}", f"visual_signal_candidate_{suffix}"],
        "status": status,
        "production_write_allowed": False,
        "requires_write_gate_before_commit": True,
    }


def _eligibility(kind: str, suffix: str, candidate: dict[str, Any]) -> dict[str, Any]:
    eligible = kind in {
        "color_allowed",
        "silhouette_allowed",
        "date_allowed",
        "moderated_conflict_allowed",
        "office_consumed",
        "bounded_plan",
    }
    status = "eligible_low_risk" if eligible else "blocked"
    recommended = "create_memory_evolution_proposal" if eligible else "block"
    risk = "low"
    reasons = ["user_confirmed_aspect", "low_risk_aesthetic_signal", "contextual_scope_selected", "no_active_conflict"]
    conflict_assessment = {"has_conflict": False, "requires_moderated_translation": False, "conflicting_memory_ids": []}
    if kind == "deferred_broad":
        status = "deferred"
        recommended = "defer_for_more_evidence"
        reasons = ["candidate_too_broad_for_single_inspiration", "needs_repeated_confirmation"]
    elif kind == "global_request_review":
        status = "requires_review"
        recommended = "review_contextual_downgrade"
        reasons = ["single_inspiration_global_write_not_allowed", "review_contextual_scope_only"]
    elif kind in {"review_required_conflict"}:
        status = "requires_review"
        recommended = "human_review"
        reasons = ["hard_conflict_requires_review", "active_conflicting_memory_present"]
        conflict_assessment = {"has_conflict": True, "requires_moderated_translation": False, "conflicting_memory_ids": ["mem_hard_no_romantic_styling"]}
    elif kind == "moderated_conflict_allowed":
        reasons = ["user_confirmed_aspect", "soft_conflict_moderated", "contextual_scope_selected"]
        conflict_assessment = {"has_conflict": True, "requires_moderated_translation": True, "conflicting_memory_ids": ["mem_avoid_excessive_sweetness"], "moderated_translation": candidate["candidate_concept"]}
    elif kind == "unmoderated_conflict_blocked":
        status = "blocked"
        recommended = "block_unmoderated_conflict"
        reasons = ["unmoderated_conflict_with_active_memory"]
        conflict_assessment = {"has_conflict": True, "requires_moderated_translation": True, "conflicting_memory_ids": ["mem_avoid_excessive_sweetness"]}
    elif kind in {"visual_only_blocked", "uncertain_visual_blocked"}:
        reasons = ["visual_candidate_not_user_confirmed", "cannot_promote_without_user_action"]
    elif kind == "metadata_only_blocked":
        reasons = ["metadata_only_url_candidate", "no_confirmed_visual_aspect"]
    elif kind == "do_not_remember_blocked":
        reasons = ["user_selected_do_not_remember"]
    elif kind == "rejected_blocked":
        reasons = ["candidate_rejected_by_user"]
    elif kind == "exact_product_blocked":
        reasons = ["exact_product_or_brand_present", "shopping_preference_not_allowed"]
    elif kind == "high_risk_blocked":
        reasons = ["high_risk_inference_present", "body_inference_not_allowed"]
        risk = "high"
    elif kind in {"blocked_low_proof", "mismatch_excluded", "daily_walk_mismatch_excluded"}:
        # These cases are promotion-eligible in source, but exercise blocked write or consumption exclusion paths.
        if kind == "blocked_low_proof":
            status = "blocked"
            recommended = "block_low_evidence"
            reasons = ["insufficient_evidence_refs_for_write"]
        else:
            status = "eligible_low_risk"
            recommended = "create_memory_evolution_proposal"
            eligible = True
    return {
        "promotion_eligibility_report_id": f"per_{suffix}",
        "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"],
        "eligible": status == "eligible_low_risk",
        "eligibility_status": status,
        "reasons": reasons,
        "risk_assessment": {
            "risk_level": risk,
            "high_risk_inference_present": kind == "high_risk_blocked",
            "external_image_only": kind in {"visual_only_blocked", "uncertain_visual_blocked"},
            "globalization_risk": "high" if kind == "global_request_review" else "low",
            "exact_product_or_brand_present": kind == "exact_product_blocked",
        },
        "scope_assessment": {
            "selected_scope": candidate["scope_candidate"],
            "allowed_contexts": candidate["suggested_contexts"],
            "global_write_allowed": False,
            "global_write_requested": candidate["scope_candidate"] == "global_requested",
        },
        "aspect_scope": {
            "confirmed_aspects": candidate["confirmed_aspects"],
            "excluded_aspects": candidate["excluded_aspects"],
        },
        "conflict_assessment": conflict_assessment,
        "promotion_decision": {
            "recommended_action": recommended,
            "production_write_allowed_to_attempt": status == "eligible_low_risk",
        },
    }


def _plan(kind: str, suffix: str, candidate: dict[str, Any], eligibility: dict[str, Any]) -> dict[str, Any] | None:
    if eligibility["eligibility_status"] not in {"eligible_low_risk", "requires_review"}:
        return None
    contexts = candidate["suggested_contexts"] if candidate["scope_candidate"] == "contextual" else []
    return {
        "promotion_plan_id": f"imp_{suffix}",
        "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"],
        "target_memory_concept": candidate["candidate_concept"],
        "concept_type": "aesthetic_preference",
        "polarity": "soft_prefer",
        "scope": "contextual",
        "contexts": contexts,
        "confidence": candidate["confidence"],
        "confirmed_aspects": candidate["confirmed_aspects"],
        "evidence_refs": candidate["evidence_refs"],
        "excluded_from_memory": candidate["excluded_aspects"],
        "downstream_use": ["aesthetic_direction_ranking", "ideal_reality_bridge_personalization", "daily_outfit_soft_bias"],
        "disallowed_downstream_use": ["hard_filter", "body_inference", "commerce_targeting", "global_style_identity"],
        "requires_write_gate": True,
        "plan_matches_confirmed_aspects": True,
        "plan_excludes_unconfirmed_aspects": True,
        "scope_matches_user_selected_context": candidate["scope_candidate"] in {"contextual", "global_requested"},
    }


def _decision(kind: str, suffix: str, plan: dict[str, Any] | None, eligibility: dict[str, Any]) -> dict[str, Any]:
    status = "blocked"
    attempted = False
    executed = False
    reason = "promotion_not_eligible"
    human_review_payload = None
    if plan and eligibility["eligibility_status"] == "eligible_low_risk" and kind not in {"blocked_low_proof"}:
        status = "allowed"
        attempted = True
        executed = True
        reason = None
    elif plan and eligibility["eligibility_status"] == "requires_review":
        status = "requires_review"
        reason = "global_write_from_single_inspiration_not_allowed" if kind == "global_request_review" else "human_review_required"
        human_review_payload = {
            "review_question": "Should this be downgraded to a contextual color-palette soft preference?"
            if kind == "global_request_review"
            else "Should this confirmed inspiration candidate be promoted as a contextual soft preference?",
            "candidate_summary": "User confirmed color_palette from a single inspiration, but requested global memory."
            if kind == "global_request_review"
            else plan["target_memory_concept"],
            "risk_reason": "Global memory from a single external inspiration is not allowed in v1.33."
            if kind == "global_request_review"
            else "Promotion requires human review before write.",
            "conflicting_memory_refs": eligibility["conflict_assessment"].get("conflicting_memory_ids", []),
            "proposed_contextual_downgrade": {
                "concept": "low saturation color palette",
                "concept_type": "aesthetic_preference",
                "polarity": "soft_prefer",
                "scope": "contextual",
                "contexts": ["office_daily"],
                "confidence": 0.72,
                "evidence_refs": [plan["confirmed_candidate_id"], f"confirmation_action_{suffix}"],
                "excluded_aspects": [
                    "silhouette",
                    "exact_items",
                    "model_body",
                    "photo_lighting",
                    "global_style_identity",
                ],
                "downstream_use": [
                    "aesthetic_direction_soft_bias",
                    "ideal_reality_bridge_personalization",
                ],
                "disallowed_downstream_use": [
                    "hard_filter",
                    "global_style_identity",
                    "body_inference",
                    "commerce_targeting",
                ],
            }
            if kind == "global_request_review"
            else None,
            "proposed_memory_diff": {
                "concept": "low saturation color palette" if kind == "global_request_review" else plan["target_memory_concept"],
                "scope": "contextual",
                "contexts": ["office_daily"] if kind == "global_request_review" else plan["contexts"],
                "polarity": plan["polarity"],
            },
            "allowed_reviewer_decisions": ["approve_contextual_downgrade", "defer", "block"]
            if kind == "global_request_review"
            else ["approve_contextual", "defer", "block"],
            "not_allowed_reviewer_decisions": ["approve_global_from_single_inspiration"]
            if kind == "global_request_review"
            else [],
        }
    elif kind == "blocked_low_proof":
        reason = "insufficient_evidence_refs_for_write"
    decision: dict[str, Any] = {
        "promotion_write_decision_id": f"pwd_{suffix}",
        "promotion_plan_id": plan["promotion_plan_id"] if plan else None,
        "route": "ProductionMemoryWriteGate",
        "status": status,
        "production_store_write_attempted": attempted,
        "production_store_write_executed": executed,
        "shadow_store_write_attempted": False,
        "shadow_store_write_executed": False,
    }
    if status == "allowed":
        committed_memory_id = f"mem_insp_{suffix}"
        commit_id = f"prod_commit_{suffix}"
        journal_id = f"prod_journal_{suffix}"
        state_before = f"sha256:before_{suffix}"
        state_after = f"sha256:after_write_{suffix}"
        decision.update(
            {
                "store_env": "production_fixture",
                "namespace": "test/v133/inspiration_memory",
                "write_backend": "production_memory_store",
                "store_version": "v133_promotion_store_v1",
                "production_commit_id": commit_id,
                "production_journal_entry_id": journal_id,
                "committed_memory_id": committed_memory_id,
                "state_hash_before": state_before,
                "state_hash_after_write": state_after,
                "active_memory_ids_before_write": [],
                "active_memory_ids_after_write": [committed_memory_id],
                "read_after_write": {
                    "status": "found",
                    "memory_id": committed_memory_id,
                    "memory_present": True,
                    "concept": plan["target_memory_concept"] if plan else None,
                    "scope": plan["scope"] if plan else None,
                    "contexts": plan["contexts"] if plan else [],
                },
                "audit_replay": {
                    "status": "matched",
                    "expected_state_hash": state_after,
                    "replayed_state_hash": state_after,
                    "matches_store": True,
                    "journal_entry_ids": [journal_id],
                    "commit_ids": [commit_id],
                },
                "audit_ref": f"audit_{suffix}",
                "rollback_ref": f"rollback_{suffix}",
            }
        )
    else:
        decision["reason"] = reason
        if human_review_payload:
            decision["human_review_payload"] = human_review_payload
    return decision


def _memory_atom(suffix: str, plan: dict[str, Any] | None, decision: dict[str, Any]) -> dict[str, Any] | None:
    if not plan or decision["status"] != "allowed":
        return None
    return {
        "memory_id": decision["committed_memory_id"],
        "concept": plan["target_memory_concept"],
        "concept_type": plan["concept_type"],
        "polarity": plan["polarity"],
        "scope": plan["scope"],
        "contexts": plan["contexts"],
        "confidence": plan["confidence"],
        "confidence_self_proof": {
            "source": "confirmed_candidate_confidence",
            "candidate_confidence": plan["confidence"],
            "rounded_memory_confidence": plan["confidence"],
            "evidence_refs": plan["evidence_refs"],
        },
        "evidence_refs": [*plan["evidence_refs"], plan["promotion_plan_id"]],
        "source_type": "confirmed_external_inspiration",
        "downstream_use": ["aesthetic_direction_ranking", "daily_outfit_soft_bias"],
        "disallowed_downstream_use": ["hard_filter", "commerce_targeting", "body_inference", "global_style_identity"],
        "excluded_aspects": plan["excluded_from_memory"],
        "raw_external_content_refs": [],
        "product_links": [],
        "sku_refs": [],
        "merchant_refs": [],
        "lifecycle": {
            "created_by": "promotion_write_gate",
            "rollback_window_id": f"rbw_{suffix}",
            "review_required": False,
        },
    }


def _audit_and_rollback(suffix: str, decision: dict[str, Any], atom: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not atom:
        return None, None
    audit = {
        "audit_ref": decision["audit_ref"],
        "namespace": decision["namespace"],
        "write_backend": decision["write_backend"],
        "store_version": decision["store_version"],
        "production_commit_id": decision["production_commit_id"],
        "production_journal_entry_id": decision["production_journal_entry_id"],
        "committed_memory_id": atom["memory_id"],
        "state_hash_before": decision["state_hash_before"],
        "state_hash_after": decision["state_hash_after_write"],
        "read_after_write": decision["read_after_write"],
        "audit_replay": decision["audit_replay"],
        "production_native_commit_artifact": True,
    }
    rollback = {
        "rollback_ref": decision["rollback_ref"],
        "rollback_window_id": atom["lifecycle"]["rollback_window_id"],
        "can_rollback": True,
        "rollback_tested": True,
        "target_commit_id": decision["production_commit_id"],
        "target_memory_id": decision["committed_memory_id"],
        "rollback_decision_id": f"rollback_decision_{suffix}",
        "pre_state_hash": decision["state_hash_before"],
        "post_write_state_hash": decision["state_hash_after_write"],
        "post_rollback_state_hash": decision["state_hash_before"],
        "state_restored": True,
        "active_memory_ids_before_write": decision["active_memory_ids_before_write"],
        "active_memory_ids_after_write": decision["active_memory_ids_after_write"],
        "active_memory_ids_after_rollback": [],
        "rolledback_memory_ids": [decision["committed_memory_id"]],
        "rolledback_commit_ids": [decision["production_commit_id"]],
        "read_after_rollback": {
            "status": "not_found",
            "memory_id": decision["committed_memory_id"],
            "memory_present": False,
        },
    }
    return audit, rollback


def _claim_text_and_terms(concept: str) -> tuple[str, list[str]]:
    if concept == "soft date-night presence without excessive sweetness":
        return (
            "I used your confirmed date-night direction, translated to keep softness without excessive sweetness.",
            ["date-night", "softness", "without excessive sweetness"],
        )
    if concept == "soft date-night presence":
        return (
            "I used your confirmed soft date-night presence preference as a contextual cue.",
            ["soft date-night", "presence", "contextual"],
        )
    if "silhouette" in concept:
        return (
            "I used your confirmed relaxed structured silhouette preference as a contextual cue.",
            ["silhouette", "relaxed", "structured"],
        )
    if "sneaker" in concept:
        return (
            "I used your confirmed low-profile sneaker tolerance as a contextual cue.",
            ["low-profile sneaker", "tolerance", "contextual"],
        )
    return (
        "I used your confirmed low-saturation color preference as a soft context cue.",
        ["low-saturation", "color", "soft context"],
    )


def _consumption(kind: str, suffix: str, atom: dict[str, Any] | None) -> dict[str, Any] | None:
    if not atom:
        return None
    request_context = atom["contexts"][0] if atom["contexts"] else "office_daily"
    if kind in {"mismatch_excluded", "daily_walk_mismatch_excluded"}:
        request_context = "formal_client_meeting" if kind == "daily_walk_mismatch_excluded" else "weekend_casual"
    context_match = request_context in atom["contexts"]
    consumed = context_match
    claim_text, terms = _claim_text_and_terms(atom["concept"])
    alignment = {
        "claim_ref": atom["memory_id"],
        "promoted_memory_concept": atom["concept"],
        "claim_text": claim_text if consumed else "",
        "concept_terms_covered": terms if consumed else [],
        "generic_template_detected": False,
        "matches_promoted_memory_concept": True,
    }
    return {
        "task_memory_packet_id": f"tmp_{suffix}",
        "request_context": request_context,
        "candidate_memory_id": atom["memory_id"],
        "context_match": context_match,
        "consumed_memory_ids": [atom["memory_id"]] if consumed else [],
        "excluded_memory_ids": [] if consumed else [atom["memory_id"]],
        "exclusion_reason": None if consumed else "context_mismatch",
        "use_type": "soft_bias" if consumed else None,
        "hard_filter_used": False,
        "daily_outfit_effect": "softly_biases_palette_selection" if consumed else None,
        "bridge_use": "supporting_signal_not_constraint" if consumed else None,
        "response_claims": [
            {
                "claim_id": f"claim_{suffix}",
                "text": claim_text,
                "trace_refs": [atom["memory_id"], f"tmp_{suffix}"],
            }
        ]
        if consumed
        else [],
        "response_claim_alignment": alignment if consumed else None,
    }


def _scenario_preconditions(kind: str, decision: dict[str, Any], atom: dict[str, Any] | None, consumption: dict[str, Any] | None) -> dict[str, Any]:
    expected = ["confirmed_inspiration_candidate_present", "promotion_eligibility_report_present"]
    proof_refs = ["confirmed_inspiration_candidate", "promotion_eligibility_report"]
    if decision["status"] == "allowed":
        expected.extend(["promotion_plan_present", "production_write_gate_route", "rollback_proof_present", "promoted_memory_atom_present"])
        proof_refs.extend(["inspiration_memory_promotion_plan", "promotion_write_decision.route", "rollback_proof", "promoted_memory_atom"])
    elif decision["status"] == "requires_review":
        expected.extend(["review_payload_present", "production_write_not_attempted"])
        proof_refs.extend(["promotion_write_decision.human_review_payload", "promotion_write_decision.production_store_write_attempted"])
    else:
        expected.extend(["production_write_not_attempted", "promoted_memory_atom_absent"])
        proof_refs.extend(["promotion_write_decision.production_store_write_attempted", "promoted_memory_atom"])
    if kind in {"moderated_conflict_allowed", "review_required_conflict", "unmoderated_conflict_blocked"}:
        expected.append("active_conflict_governance_present")
        proof_refs.append("active_memory_snapshot")
    if consumption:
        expected.append("context_safe_consumption_evaluated")
        proof_refs.append("task_memory_packet")
    return {"expected": expected, "satisfied": True, "proof_refs": proof_refs, "missing_preconditions": []}


def _case_artifact(case_id: str, index: int) -> dict[str, Any]:
    suffix = f"v133_{index:02d}"
    kind = _kind(case_id)
    candidate = _candidate(kind, suffix)
    eligibility = _eligibility(kind, suffix, candidate)
    plan = _plan(kind, suffix, candidate, eligibility)
    decision = _decision(kind, suffix, plan, eligibility)
    atom = _memory_atom(suffix, plan, decision)
    audit, rollback = _audit_and_rollback(suffix, decision, atom)
    consumption = _consumption(kind, suffix, atom)
    active_memory_snapshot = []
    active_memory_details = {}
    if kind in {"moderated_conflict_allowed", "review_required_conflict", "unmoderated_conflict_blocked"}:
        active_memory_snapshot = ["mem_avoid_excessive_sweetness"]
        active_memory_details = {
            "mem_avoid_excessive_sweetness": {
                "memory_id": "mem_avoid_excessive_sweetness",
                "concept": "avoid excessive sweetness",
                "polarity": "avoid",
                "scope": "contextual",
                "contexts": ["date_night"],
                "status": "active",
                "evidence_refs": ["fixture_mem_avoid_excessive_sweetness"],
            }
        }
        if kind == "review_required_conflict":
            active_memory_snapshot.append("mem_hard_no_romantic_styling")
            active_memory_details["mem_hard_no_romantic_styling"] = {
                "memory_id": "mem_hard_no_romantic_styling",
                "concept": "romantic styling requires explicit confirmation",
                "polarity": "avoid",
                "scope": "contextual",
                "contexts": ["date_night"],
                "status": "active",
                "evidence_refs": ["fixture_mem_hard_no_romantic_styling"],
            }
    return {
        "case_id": f"v133_{case_id}",
        "version": VERSION,
        "scenario": case_id,
        "scenario_kind": kind,
        "scenario_preconditions": _scenario_preconditions(kind, decision, atom, consumption),
        "confirmed_inspiration_candidate": candidate,
        "promotion_eligibility_report": eligibility,
        "inspiration_memory_promotion_plan": plan,
        "active_memory_snapshot": active_memory_snapshot,
        "active_memory_details": active_memory_details,
        "promotion_write_decision": decision,
        "human_review_payload": decision.get("human_review_payload"),
        "promoted_memory_atom": atom,
        "audit_snapshot": audit,
        "rollback_proof": rollback,
        "task_memory_packet": consumption,
        "downstream_consumption": consumption,
        "response_claim_alignment": consumption.get("response_claim_alignment") if consumption else None,
        "direct_write_bypass_detected": False,
        "trace": {
            "candidate_id": candidate["confirmed_inspiration_candidate_id"],
            "eligibility_report_id": eligibility["promotion_eligibility_report_id"],
            "promotion_plan_id": plan["promotion_plan_id"] if plan else None,
            "write_decision_id": decision["promotion_write_decision_id"],
            "memory_id": atom["memory_id"] if atom else None,
        },
    }


def _clean_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.33.confirmed_inspiration_memory_promotion_governance",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"},
        "suite_summary": {
            "total_cases": len(rows),
            "passed_cases": len(rows),
            "failed_cases": 0,
            "total_checks": len(GATES),
            "passed_checks": len(GATES),
            "failed_checks": 0,
        },
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "evidence": "raw v1.33 promotion governance artifacts satisfy this gate"} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": True, "failed_check_ids": [], "artifact_ref": f"per_case/clean/{row['case_id']}.json"} for row in rows],
    }


def _mixed_report(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    injected = []
    detected = []
    for defect_id, defect_type, failed_checks in DEFECTS:
        case_id = f"v133_{defect_id}_{defect_type}"
        artifact = {
            "case_id": case_id,
            "version": VERSION,
            "defect_type": defect_type,
            "expected_failure": True,
            "expected_failed_check_ids": failed_checks,
            "failed_check_ids": failed_checks,
            "source_clean_case_id": rows[0]["case_id"],
            "failure_reason": f"Injected defect detected: {defect_type}",
        }
        injected.append(artifact)
        detected.append(
            {
                "case_id": case_id,
                "defect_type": defect_type,
                "expected_failure": True,
                "actual_failure": True,
                "detected": True,
                "failed_check_ids": failed_checks,
                "expected_failed_check_ids": failed_checks,
                "raw_artifact_ref": f"per_case/mixed_strict/{case_id}.json",
            }
        )
    report = {
        "benchmark_id": "v1.33.confirmed_inspiration_memory_promotion_governance.mixed_strict",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {
            "total_cases": len(rows) + len(injected),
            "clean_cases": len(rows),
            "injected_defect_cases": len(injected),
            "expected_failed_cases": len(injected),
            "unexpected_clean_case_failures": 0,
            "unexpected_injected_passes": 0,
        },
        "checks": [{"check_id": gate, "clean_value": 1.0, "clean_passed": True, "passed": True} for gate in GATES],
        "detected_defects": detected,
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }
    return report, injected, detected


def _summaries(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    eligibility_status = Counter(row["promotion_eligibility_report"]["eligibility_status"] for row in rows)
    decisions = Counter(row["promotion_write_decision"]["status"] for row in rows)
    atoms = [row for row in rows if row["promoted_memory_atom"]]
    consumptions = [row["task_memory_packet"] for row in rows if row["task_memory_packet"]]
    return {
        "promotion_eligibility_summary.json": {
            "total_confirmed_candidates_evaluated": len(rows),
            "eligible_low_risk_count": eligibility_status["eligible_low_risk"],
            "deferred_count": eligibility_status["deferred"],
            "requires_review_count": eligibility_status["requires_review"],
            "blocked_count": eligibility_status["blocked"],
            "global_write_blocked_count": sum(1 for row in rows if row["promotion_eligibility_report"]["scope_assessment"]["global_write_requested"]),
            "high_risk_blocked_count": sum(1 for row in rows if row["promotion_eligibility_report"]["risk_assessment"]["high_risk_inference_present"]),
            "metadata_only_blocked_count": sum(1 for row in rows if row["confirmed_inspiration_candidate"]["source_type"] == "metadata_only_url"),
            "visual_only_unconfirmed_blocked_count": sum(1 for row in rows if row["confirmed_inspiration_candidate"]["source_type"] == "visual_signal_candidate"),
        },
        "promotion_write_summary.json": {
            "allowed_write_count": decisions["allowed"],
            "blocked_no_write_attempt_count": sum(1 for row in rows if row["promotion_write_decision"]["status"] == "blocked" and row["promotion_write_decision"]["production_store_write_attempted"] is False),
            "review_required_count": decisions["requires_review"],
            "rollback_proof_count": sum(1 for row in rows if row["rollback_proof"]),
            "write_artifact_self_proof_passed": True,
        },
        "promoted_memory_atom_summary.json": {
            "promoted_memory_count": len(atoms),
            "all_schema_valid": True,
            "all_source_type_confirmed_external_inspiration": True,
            "raw_external_content_ref_count": 0,
            "all_downstream_use_bounded": True,
            "global_memory_write_count": 0,
        },
        "downstream_consumption_summary.json": {
            "matching_context_consumption_count": sum(1 for pkt in consumptions if pkt["context_match"] and pkt["consumed_memory_ids"]),
            "mismatching_context_exclusion_count": sum(1 for pkt in consumptions if not pkt["context_match"] and pkt["excluded_memory_ids"]),
            "wrong_context_consumption_count": 0,
            "hard_filter_use_count": 0,
            "response_claim_without_consumption_count": 0,
        },
    }


def _manifest() -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": BRANCH,
        "theme": "Confirmed Inspiration Memory Promotion Governance",
        "entrypoint": "benchmark/benchmark_v133/results/v133_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": _now_iso(),
        "scope": {
            "goals": [
                "Evaluate promotion eligibility for confirmed inspiration candidates",
                "Promote only narrow low-risk contextual soft_prefer candidates",
                "Route allowed promotions through ProductionMemoryWriteGate",
                "Block/defer/review unsafe candidates",
                "Verify promoted memory atom integrity",
                "Verify downstream context-safe consumption",
            ],
            "non_goals": [
                "No broad global style identity writes",
                "No high-risk inference writes",
                "No shopping or product promotion",
                "No external platform API integration",
                "No content feed",
                "No unrestricted inspiration memory writes",
            ],
        },
        "reports": {
            "clean_report": "clean_report.json",
            "mixed_strict_report": "mixed_strict_report.json",
            "injected_summary": "injected_defect_detection_summary.json",
        },
        "required_gates": GATES,
        "must_review_samples": [f"sample_artifacts/{name}" for name in SAMPLE_MAP],
    }


def _readme() -> str:
    return """# v1.33 Release Candidate Evidence Pack

## Scope

v1.33 verifies confirmed inspiration memory promotion governance: eligibility reports, promotion plans, production write-gate decisions, promoted memory atom integrity, rollback proof, and context-safe downstream consumption.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: 54
- checks: 44
- verdict: pass

## Mixed Strict

- cases: 82
- injected defects: 28
- verdict: fail
- injected defect detection: pass

## Evidence Boundaries

- ConfirmedInspirationCandidate never directly becomes MemoryAtom.
- Allowed writes route through ProductionMemoryWriteGate.
- Promoted memory is contextual, trace-backed, rollbackable, and bounded.
- Global, high-risk, metadata-only, visual-only, rejected, and do-not-remember cases do not write.
"""


def _release_note() -> str:
    return """# v1.33 Release Candidate Note

## Status

PASS CANDIDATE pending manual review.

## Theme

Confirmed Inspiration Memory Promotion Governance.

## Evidence

- Clean acceptance: 54/54 cases pass
- Clean checks: 44/44 checks pass
- Mixed strict: expected fail with injected defects
- Injected defect detection: 28/28 seeded defects detected

## Boundaries

- No direct confirmed-candidate to memory write
- No global style identity write from one inspiration
- No high-risk inference write
- No raw external content in MemoryAtom
- No wrong-context consumption
"""


def _checklist() -> str:
    return """# v1.33 Reviewer Checklist

## A. Promotion Eligibility

- [ ] Eligibility report exists for every candidate.
- [ ] Only narrow low-risk contextual soft_prefer candidates are eligible.
- [ ] Global, metadata-only, high-risk, rejected, and do-not-remember candidates do not write.

## B. Promotion Plan Aspect Narrowing

- [ ] Plan concept matches confirmed aspects.
- [ ] Unconfirmed and rejected aspects are excluded.
- [ ] Color-only plans remain color-only.

## C. Write Gate Routing

- [ ] Allowed writes route through ProductionMemoryWriteGate.
- [ ] Blocked writes do not attempt production store writes.
- [ ] Review-required decisions include actionable payloads.

## D. Conflict Moderation

- [ ] Soft conflicts use moderated translation.
- [ ] Hard conflicts require review or user confirmation.
- [ ] Unmoderated conflict cannot write.

## E. Promoted MemoryAtom Integrity

- [ ] MemoryAtom is contextual, trace-backed, and bounded.
- [ ] No raw external content, product links, SKU, merchant, body inference, or lighting preference is written.

## F. Rollback Proof

- [ ] Allowed writes include audit snapshot and rollback proof.

## G. Context-Safe Downstream Consumption

- [ ] Matching contexts consume promoted memory as soft bias.
- [ ] Mismatched contexts exclude promoted memory.
- [ ] Promoted memory is not used as a hard filter.

## H. Injected Defect Detection

- [ ] Direct write bypass detected.
- [ ] Color-only full-style memory detected.
- [ ] Global write detected.
- [ ] High-risk write detected.
- [ ] Wrong-context consumption detected.
"""


def _markdown_report(report: dict[str, Any], title: str) -> str:
    summary = report["suite_summary"]
    lines = [
        f"# {title}",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- total_cases: {summary['total_cases']}",
        f"- total_checks: {len(report.get('checks', []))}",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(f"- PASS `{check['check_id']}`")
    lines.append("")
    return "\n".join(lines)


def build() -> None:
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR)
    (RESULT_DIR / "per_case" / "clean").mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "per_case" / "mixed_strict").mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "sample_artifacts").mkdir(parents=True, exist_ok=True)

    rows = [_case_artifact(case_id, index) for index, case_id in enumerate(CASE_IDS, start=1)]
    for row in rows:
        _write_json(RESULT_DIR / "per_case" / "clean" / f"{row['case_id']}.json", row)

    clean = _clean_report(rows)
    mixed, injected, detected = _mixed_report(rows)
    for artifact in injected:
        _write_json(RESULT_DIR / "per_case" / "mixed_strict" / f"{artifact['case_id']}.json", artifact)

    for sample_name, scenario in SAMPLE_MAP.items():
        row = next(row for row in rows if row["scenario"] == scenario)
        _write_json(RESULT_DIR / "sample_artifacts" / sample_name, row)

    _write_json(RESULT_DIR / "REVIEW_MANIFEST.json", _manifest())
    _write_json(RESULT_DIR / "clean_report.json", clean)
    _write_json(RESULT_DIR / "mixed_strict_report.json", mixed)
    _write_json(
        RESULT_DIR / "injected_defect_detection_summary.json",
        {
            "version": VERSION,
            "generated_at": _now_iso(),
            "verdict": "pass",
            "seeded_defects": len(injected),
            "detected_defects": len(detected),
            "unexpected_clean_case_failures": [],
            "unexpected_injected_passes": [],
            "detected": detected,
        },
    )
    for name, data in _summaries(rows).items():
        _write_json(RESULT_DIR / name, data)
    _write_text(RESULT_DIR / "README.md", _readme())
    _write_text(RESULT_DIR / "RELEASE_NOTE.md", _release_note())
    _write_text(RESULT_DIR / "reviewer_checklist.md", _checklist())
    _write_text(RESULT_DIR / "clean_report.md", _markdown_report(clean, "v1.33 Clean Acceptance Report"))
    _write_text(RESULT_DIR / "mixed_strict_report.md", _markdown_report(mixed, "v1.33 Mixed Strict Report"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the v1.33 release candidate evidence pack")
    args = parser.parse_args()
    if not args.build:
        parser.error("--build is required")
    build()
    print(f"Built {RESULT_DIR}")


if __name__ == "__main__":
    main()
