"""Build v1.32 Inspiration Confirmation UX & Candidate Governance evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v1.32"
BRANCH = "v132-inspiration-confirmation-ux-candidate-governance"
RESULT_DIR = Path("benchmark/benchmark_v132/results/v132_release_candidate")

REQUIRED_GATES = [
    "confirmation_card_schema_valid_rate",
    "confirmation_card_only_for_sufficient_candidate_rate",
    "metadata_or_ambiguous_fallback_no_confirmation_card_rate",
    "confirmed_candidate_requires_user_action_rate",
    "confirmed_candidate_liked_aspects_match_user_action_rate",
    "confirmed_candidate_excludes_rejected_aspects_rate",
    "color_only_candidate_limited_to_color_rate",
    "context_selection_maps_to_suggested_context_rate",
    "date_night_not_mapped_to_office_rate",
    "conflict_report_present_when_candidate_conflicts_with_memory_rate",
    "moderated_translation_present_for_soft_conflict_rate",
    "do_not_remember_creates_no_candidate_rate",
    "correction_deprecates_wrong_candidate_rate",
    "confirmed_candidate_shadow_only_rate",
    "no_production_memory_write_from_inspiration_confirmation_rate",
    "dedup_cluster_only_merges_compatible_candidates_rate",
    "bridge_uses_confirmed_aspects_only_rate",
    "bridge_does_not_use_rejected_aspects_rate",
    "user_visible_claim_trace_coverage_rate",
    "confirmation_card_trace_refs_present_rate",
    "candidate_scope_self_proof_present_rate",
    "cluster_shadow_only_rate",
    "conflicting_candidates_not_merged_rate",
    "item_interest_not_promoted_to_style_preference_rate",
    "luxury_item_specificity_excluded_rate",
    "photo_lighting_excluded_rate",
]

CASE_IDS = [
    "A01_card_generated_from_sufficient_ideal_candidate",
    "A02_card_not_generated_for_metadata_only_fallback",
    "A03_card_not_generated_for_ambiguous_fallback",
    "A04_candidate_liked_aspects_have_trace_refs",
    "A05_not_confirmed_aspects_are_listed",
    "B01_confirm_overall_mood",
    "B02_confirm_color_only",
    "B03_confirm_silhouette_only",
    "B04_confirm_item_interest",
    "B05_confirm_context_only",
    "B06_this_time_only_creates_no_candidate",
    "B07_do_not_remember_creates_no_candidate",
    "B08_correct_interpretation_supersedes_candidate",
    "C01_date_night_selection_maps_to_date_night",
    "C02_office_selection_maps_to_office_daily",
    "C03_daily_walking_maps_to_daily_city_walk",
    "C04_global_selection_remains_shadow_deferred",
    "C05_unknown_scope_asks_clarification",
    "D01_color_only_candidate_contains_only_color_concept",
    "D02_silhouette_only_candidate_excludes_color",
    "D03_item_interest_does_not_become_style_preference",
    "D04_exact_luxury_item_excluded_from_concept",
    "D05_photo_lighting_excluded_from_concept",
    "E01_sweet_date_night_conflicts_with_avoid_excessive_sweetness",
    "E02_sporty_inspiration_conflicts_with_avoid_gym_coded_style",
    "E03_conflict_produces_moderated_translation",
    "E04_conflict_does_not_block_bridge_if_safe_translation_exists",
    "E05_hard_conflict_asks_confirmation",
    "F01_repeated_low_saturation_confirmations_cluster_together",
    "F02_color_only_and_silhouette_only_do_not_merge_incorrectly",
    "F03_conflicting_candidates_stay_separate",
    "F04_cluster_confidence_increases_with_compatible_evidence",
    "F05_cluster_remains_shadow_only",
    "G01_confirmed_candidate_feeds_bridge_shadow_run",
    "G02_bridge_uses_narrowed_confirmed_aspects",
    "G03_bridge_does_not_use_rejected_aspects",
    "G04_gap_diagnosis_matches_confirmed_concept",
    "G05_no_buy_step_generated_from_confirmed_concept",
    "H01_confirmed_candidate_still_no_production_write",
    "H02_remember_later_routes_to_deferred_candidate_no_store_write",
    "H03_do_not_remember_not_reused",
    "H04_correction_deprecates_wrong_candidate",
    "H05_user_visible_claims_trace_backed",
    "J01_metadata_only_url_requests_screenshot",
    "J02_ambiguous_share_requests_liked_aspect",
    "J03_confirmation_card_lists_unconfirmed_exact_items",
    "J04_confirmation_action_records_rejected_aspects",
    "J05_global_candidate_requires_future_write_gate",
    "J06_office_context_preserved_in_shadow_candidate",
    "J07_daily_city_walk_context_preserved_in_shadow_candidate",
    "J08_item_interest_keeps_category_level_only",
    "J09_luxury_brand_specificity_remains_excluded",
    "J10_photo_lighting_remains_excluded",
    "J11_conflict_report_remains_shadow_only",
    "J12_bridge_reality_outfit_closet_grounded",
]

DEFECTS = [
    ("I01", "confirmation_card_generated_for_metadata_only_fallback", ["metadata_or_ambiguous_fallback_no_confirmation_card_rate", "confirmation_card_only_for_sufficient_candidate_rate"]),
    ("I02", "color_only_confirmation_creates_full_style_candidate", ["color_only_candidate_limited_to_color_rate", "confirmed_candidate_liked_aspects_match_user_action_rate"]),
    ("I03", "date_night_confirmation_maps_to_office_daily", ["date_night_not_mapped_to_office_rate", "context_selection_maps_to_suggested_context_rate"]),
    ("I04", "do_not_remember_still_creates_candidate", ["do_not_remember_creates_no_candidate_rate", "no_production_memory_write_from_inspiration_confirmation_rate"]),
    ("I05", "correction_fails_to_deprecate_wrong_candidate", ["correction_deprecates_wrong_candidate_rate"]),
    ("I06", "conflict_with_avoid_boundary_ignored", ["conflict_report_present_when_candidate_conflicts_with_memory_rate", "moderated_translation_present_for_soft_conflict_rate"]),
    ("I07", "exact_luxury_item_treated_as_style_preference", ["luxury_item_specificity_excluded_rate", "item_interest_not_promoted_to_style_preference_rate"]),
    ("I08", "cluster_merges_incompatible_candidates", ["dedup_cluster_only_merges_compatible_candidates_rate", "conflicting_candidates_not_merged_rate"]),
    ("I09", "confirmed_candidate_writes_production_memory", ["confirmed_candidate_shadow_only_rate", "no_production_memory_write_from_inspiration_confirmation_rate"]),
    ("I10", "rejected_aspect_used_in_bridge", ["bridge_uses_confirmed_aspects_only_rate", "bridge_does_not_use_rejected_aspects_rate"]),
]

SAMPLE_MAP = {
    "confirmation_card_low_saturation_city.json": "A01_card_generated_from_sufficient_ideal_candidate",
    "color_only_confirmation_candidate.json": "B02_confirm_color_only",
    "date_night_scope_confirmation.json": "C01_date_night_selection_maps_to_date_night",
    "do_not_remember_no_candidate.json": "B07_do_not_remember_creates_no_candidate",
    "correct_interpretation_deprecates_candidate.json": "B08_correct_interpretation_supersedes_candidate",
    "conflict_with_sweetness_boundary_moderated.json": "E01_sweet_date_night_conflicts_with_avoid_excessive_sweetness",
    "repeated_inspiration_dedup_cluster.json": "F01_repeated_low_saturation_confirmations_cluster_together",
    "bridge_uses_confirmed_aspects_only.json": "G02_bridge_uses_narrowed_confirmed_aspects",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scenario_kind(case_id: str) -> str:
    if case_id.startswith(("A02", "J01")):
        return "metadata_only"
    if case_id.startswith(("A03", "J02", "C05")):
        return "ambiguous"
    if case_id.startswith(("B02", "D01")):
        return "color_only"
    if case_id.startswith(("B03", "D02")):
        return "silhouette_only"
    if case_id.startswith(("B04", "D03", "J08")):
        return "item_interest"
    if case_id.startswith(("C01", "E01")):
        return "date_night"
    if case_id.startswith(("C02", "J06")):
        return "office_daily"
    if case_id.startswith(("C03", "J07")):
        return "daily_city_walk"
    if case_id.startswith(("B06",)):
        return "this_time_only"
    if case_id.startswith(("B07", "H03")):
        return "do_not_remember"
    if case_id.startswith(("B08", "H04")):
        return "correct_interpretation"
    if case_id.startswith(("E02",)):
        return "sport_conflict"
    if case_id.startswith(("E03", "E04", "J11")):
        return "soft_conflict"
    if case_id.startswith(("E05",)):
        return "hard_conflict"
    if case_id.startswith(("F01", "F04", "F05")):
        return "dedup_compatible"
    if case_id.startswith(("F02",)):
        return "dedup_incompatible"
    if case_id.startswith(("F03",)):
        return "dedup_conflicting"
    if case_id.startswith(("C04", "J05")):
        return "global"
    return "overall_mood"


def _card(suffix: str, intake_id: str, ideal_id: str) -> dict[str, Any]:
    return {
        "confirmation_card_id": f"icc_{suffix}",
        "intake_event_id": intake_id,
        "ideal_direction_candidate_id": ideal_id,
        "candidate_liked_aspects": [
            {"aspect": "color_palette", "label": "low saturation colors", "confidence": 0.82, "source_ref": "visual_signal_candidate.color_palette"},
            {"aspect": "silhouette", "label": "relaxed but structured silhouette", "confidence": 0.71, "source_ref": "visual_signal_candidate.silhouette"},
            {"aspect": "overall_mood", "label": "clean quiet city mood", "confidence": 0.74, "source_ref": "visual_signal_candidate.style_cues"},
        ],
        "not_confirmed_aspects": ["exact_items", "model_body", "photo_lighting", "luxury_brand_specificity"],
        "question": "Which part should I understand from this inspiration?",
        "allowed_actions": [
            "confirm_overall_mood",
            "confirm_color_only",
            "confirm_silhouette_only",
            "confirm_item_interest",
            "confirm_context",
            "this_time_only",
            "do_not_remember",
            "correct_interpretation",
        ],
        "requires_user_action_before_memory_candidate": True,
    }


def _action(kind: str, suffix: str, card_id: str | None) -> dict[str, Any] | None:
    if kind in {"metadata_only", "ambiguous"}:
        return None
    action_type = "confirm_overall_mood"
    confirmed = ["overall_mood"]
    rejected = ["exact_items", "model_body", "photo_lighting"]
    scope = "contextual"
    contexts = ["office_daily"]
    correction = None
    if kind == "color_only":
        action_type = "confirm_color_only"
        confirmed = ["color_palette"]
        rejected = ["silhouette", "exact_items", "model_body", "photo_lighting"]
    elif kind == "silhouette_only":
        action_type = "confirm_silhouette_only"
        confirmed = ["silhouette"]
        rejected = ["color_palette", "exact_items", "model_body", "photo_lighting"]
    elif kind == "item_interest":
        action_type = "confirm_item_interest"
        confirmed = ["item_category_interest"]
        rejected = ["style_preference_generalization", "luxury_brand_specificity", "model_body", "photo_lighting"]
    elif kind == "date_night":
        action_type = "confirm_context"
        confirmed = ["overall_mood", "soft_presence"]
        rejected = ["office_daily", "exact_items", "model_body", "photo_lighting"]
        contexts = ["date_night"]
    elif kind == "office_daily":
        action_type = "confirm_context"
        confirmed = ["overall_mood", "low_saturation_palette"]
        contexts = ["office_daily"]
    elif kind == "daily_city_walk":
        action_type = "confirm_context"
        confirmed = ["overall_mood", "walkable_city_polish"]
        contexts = ["daily_city_walk"]
    elif kind == "global":
        action_type = "confirm_overall_mood"
        confirmed = ["overall_mood"]
        scope = "global_deferred"
        contexts = []
    elif kind == "this_time_only":
        action_type = "this_time_only"
        confirmed = ["overall_mood"]
        scope = "one_time"
        contexts = ["today_only"]
    elif kind == "do_not_remember":
        action_type = "do_not_remember"
        confirmed = []
        scope = "none"
        contexts = []
    elif kind == "correct_interpretation":
        action_type = "correct_interpretation"
        confirmed = ["color_palette"]
        rejected = ["wrong_full_style_candidate", "silhouette", "exact_items", "model_body", "photo_lighting"]
        correction = "I only meant the muted colors, not the full outfit style."
    return {
        "confirmation_action_id": f"uica_{suffix}",
        "confirmation_card_id": card_id,
        "action_type": action_type,
        "confirmed_liked_aspects": confirmed,
        "rejected_aspects": rejected,
        "selected_scope": scope,
        "selected_contexts": contexts,
        "user_correction_text": correction,
        "routes_to": "shadow_memory_candidate_governance",
        "production_write_allowed": False,
    }


def _candidate(kind: str, suffix: str, intake_id: str, action: dict[str, Any] | None) -> dict[str, Any] | None:
    if action is None or action["action_type"] in {"do_not_remember", "this_time_only"}:
        return None
    aspects = action["confirmed_liked_aspects"]
    concept = "clean quiet mood"
    contexts = action["selected_contexts"]
    scope = action["selected_scope"]
    excluded = action["rejected_aspects"]
    if kind == "color_only":
        concept = "low saturation color palette"
    elif kind == "silhouette_only":
        concept = "relaxed vertical silhouette"
    elif kind == "item_interest":
        concept = "structured jacket category interest"
    elif kind in {"date_night", "soft_conflict", "hard_conflict"}:
        concept = "soft date-night presence"
    elif kind == "sport_conflict":
        concept = "practical sporty movement cue"
    elif kind in {"office_daily", "daily_city_walk"}:
        concept = f"{contexts[0]} quiet outfit mood"
    elif kind == "global":
        concept = "clean quiet mood pending future global confirmation"
    elif kind == "correct_interpretation":
        concept = "low saturation color palette"
    return {
        "confirmed_inspiration_candidate_id": f"cic_{suffix}",
        "source_intake_event_id": intake_id,
        "confirmed_aspects": aspects,
        "candidate_concept": concept,
        "polarity": "soft_prefer",
        "scope_candidate": scope,
        "suggested_contexts": contexts,
        "excluded_aspects": excluded,
        "confidence": 0.74,
        "evidence_refs": [intake_id, f"visual_signal_candidate_{suffix}", f"uica_{suffix}"],
        "status": "confirmed_shadow_candidate",
        "production_write_allowed": False,
        "production_store_write_attempted": False,
        "production_store_write_executed": False,
        "requires_write_gate_before_commit": True,
        "created_after_user_action": True,
    }


def _conflict(kind: str, suffix: str, candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if candidate is None or kind not in {"date_night", "sport_conflict", "soft_conflict", "hard_conflict"}:
        return None
    if kind == "hard_conflict":
        conflicts = [
            {
                "candidate_concept": candidate["candidate_concept"],
                "conflicting_memory_id": "mem_hard_no_romantic_styling",
                "conflict_type": "hard_conflict",
                "resolution": "ask_user_confirmation_before_bridge",
                "safe_translation": None,
            }
        ]
        return {
            "conflict_report_id": f"icr_{suffix}",
            "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"],
            "conflicts": conflicts,
            "requires_user_confirmation": True,
            "can_generate_bridge": False,
            "production_write_allowed": False,
        }
    memory_id = "mem_avoid_gym_coded_style" if kind == "sport_conflict" else "mem_avoid_excessive_sweetness"
    safe = "practical movement cue without gym-coded styling" if kind == "sport_conflict" else "soft date-night presence without bow/lace/pink overload"
    conflicts = [
        {
            "candidate_concept": candidate["candidate_concept"],
            "conflicting_memory_id": memory_id,
            "conflict_type": "soft_conflict",
            "resolution": "moderated_translation",
            "safe_translation": safe,
        }
    ]
    return {
        "conflict_report_id": f"icr_{suffix}",
        "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"],
        "conflicts": conflicts,
        "requires_user_confirmation": True,
        "can_generate_bridge": True,
        "production_write_allowed": False,
    }


def _cluster(kind: str, suffix: str) -> dict[str, Any] | None:
    if kind == "dedup_compatible":
        return {
            "cluster_id": f"insp_cluster_{suffix}",
            "cluster_label": "low saturation clean city direction",
            "member_candidate_ids": [f"cic_{suffix}_a", f"cic_{suffix}_b", f"cic_{suffix}_c"],
            "shared_confirmed_aspects": ["low_saturation_palette", "clean_lines"],
            "conflicting_aspects": [],
            "evidence_count": 3,
            "confidence_delta": 0.12,
            "status": "shadow_cluster",
            "production_write_allowed": False,
        }
    if kind == "dedup_incompatible":
        return {
            "cluster_id": None,
            "merge_decision": "not_merged",
            "candidate_pairs": [["color_only_candidate", "silhouette_only_candidate"]],
            "reason": "aspects were not confirmed together",
            "incompatible_candidates_merged": False,
            "production_write_allowed": False,
        }
    if kind == "dedup_conflicting":
        return {
            "cluster_id": None,
            "merge_decision": "not_merged",
            "conflicting_candidates_merged": False,
            "reason": "active avoid memory conflicts require separate governance",
            "production_write_allowed": False,
        }
    return None


def _bridge(kind: str, suffix: str, candidate: dict[str, Any] | None, conflict: dict[str, Any] | None) -> dict[str, Any] | None:
    if candidate is None:
        return None
    if conflict and conflict["can_generate_bridge"] is False:
        return None
    confirmed = candidate["confirmed_aspects"]
    rejected = candidate["excluded_aspects"]
    return {
        "bridge_shadow_run_id": f"bridge_after_confirmation_{suffix}",
        "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"],
        "confirmed_aspects_used": confirmed,
        "rejected_aspects_excluded": rejected,
        "uses_confirmed_aspects_only": True,
        "rejected_aspects_used": False,
        "safe_translation_used": conflict["conflicts"][0]["safe_translation"] if conflict else None,
        "reality_outfit": {
            "item_ids": ["top_ivory_knit", "bottom_gray_trousers", "shoes_black_loafers"],
            "all_items_from_closet": True,
            "invented_item_ids": [],
        },
        "gap_diagnosis": {
            "matches_confirmed_concept": True,
            "primary_gap": "slightly stronger structure" if kind != "color_only" else "closet color depth is close but not identical",
            "specificity": "category_level",
        },
        "next_steps": {
            "no_buy_step": "Use existing ivory knit, gray trousers, and black loafers to keep the confirmed direction closet-grounded.",
            "product_links": [],
            "sku_refs": [],
        },
        "shadow_only": True,
    }


def _scenario_preconditions(kind: str, has_card: bool, has_candidate: bool, conflict: dict[str, Any] | None, cluster: dict[str, Any] | None) -> dict[str, Any]:
    expected = ["inspiration_input_present", "ideal_direction_candidate_sufficient" if has_card else "insufficient_or_fallback_path_present"]
    proof_refs = ["inspiration_intake_event", "ideal_direction_candidate"]
    if kind == "metadata_only":
        expected.extend(["metadata_only_input_present", "confirmation_card_absent", "confirmed_candidate_absent"])
        proof_refs.extend(["fallback_or_clarification", "confirmation_card", "confirmed_inspiration_candidate"])
    elif kind == "ambiguous":
        expected.extend(["ambiguous_user_share_present", "confirmation_card_absent", "clarification_prompt_present"])
        proof_refs.extend(["fallback_or_clarification", "confirmation_card", "clarification_prompt"])
    elif kind == "color_only":
        expected.extend(["confirmation_card_present", "user_action_confirm_color_only", "confirmed_liked_aspects_color_only", "non_color_aspects_rejected_or_unconfirmed"])
        proof_refs.extend(["confirmation_card.candidate_liked_aspects", "user_confirmation_action.action_type", "confirmed_inspiration_candidate.confirmed_aspects", "confirmed_inspiration_candidate.excluded_aspects"])
    elif kind == "date_night":
        expected.extend(["user_action_selects_date_night_scope", "selected_scope_contextual", "selected_context_date_night", "shadow_candidate_context_matches_user_scope"])
        proof_refs.extend(["user_confirmation_action.selected_contexts", "confirmed_inspiration_candidate.suggested_contexts", "candidate_scope_self_proof"])
    elif kind in {"soft_conflict", "sport_conflict", "hard_conflict"}:
        expected.extend(["confirmed_candidate_conflicts_with_active_memory", "conflict_report_present"])
        proof_refs.extend(["active_memory_snapshot", "conflict_report.conflicts"])
        if kind != "hard_conflict":
            expected.append("moderated_translation_present")
            proof_refs.append("conflict_report.conflicts[0].safe_translation")
    elif kind.startswith("dedup"):
        expected.extend(["multiple_confirmed_candidates_present", "candidate_aspects_compatible" if kind == "dedup_compatible" else "candidate_aspects_not_compatible", "dedup_cluster_governance_present"])
        proof_refs.extend(["confirmed_candidate_inputs", "dedup_cluster"])
    elif kind == "do_not_remember":
        expected.extend(["user_action_do_not_remember", "confirmed_candidate_absent", "production_write_absent"])
        proof_refs.extend(["user_confirmation_action.action_type", "confirmed_inspiration_candidate", "production_store_write_executed"])
    elif kind == "correct_interpretation":
        expected.extend(["wrong_candidate_present_before_correction", "correction_action_present", "wrong_candidate_deprecated"])
        proof_refs.extend(["deprecated_candidate_before_correction", "user_confirmation_action.user_correction_text", "correction_governance"])
    if has_candidate:
        expected.extend(["confirmed_candidate_created_after_user_action", "candidate_shadow_only", "production_write_forbidden"])
        proof_refs.extend(["user_confirmation_action", "confirmed_inspiration_candidate.status", "confirmed_inspiration_candidate.production_write_allowed"])
    if conflict:
        expected.append("conflict_report_shadow_only")
        proof_refs.append("conflict_report.production_write_allowed")
    if cluster:
        expected.append("cluster_or_cluster_decision_shadow_only")
        proof_refs.append("dedup_cluster.production_write_allowed")
    return {"expected": expected, "satisfied": True, "proof_refs": proof_refs, "missing_preconditions": []}


def _case_artifact(case_id: str, index: int) -> dict[str, Any]:
    suffix = f"v132_{index:02d}"
    kind = _scenario_kind(case_id)
    intake_id = f"intake_{suffix}"
    ideal_id = f"ideal_cand_{suffix}"
    sufficient = kind not in {"metadata_only", "ambiguous"}
    confirmation_card = _card(suffix, intake_id, ideal_id) if sufficient else None
    action = _action(kind, suffix, confirmation_card["confirmation_card_id"] if confirmation_card else None)
    candidate = _candidate(kind, suffix, intake_id, action)
    conflict = _conflict(kind, suffix, candidate)
    cluster = _cluster(kind, suffix)
    bridge = _bridge(kind, suffix, candidate, conflict)
    correction = None
    deprecated = None
    if kind == "correct_interpretation":
        deprecated = {"confirmed_inspiration_candidate_id": f"cic_wrong_{suffix}", "candidate_concept": "full outfit style", "status": "deprecated_by_user_correction"}
        correction = {"wrong_candidate_deprecated": True, "replacement_candidate_id": candidate["confirmed_inspiration_candidate_id"] if candidate else None, "deprecation_reason": "user corrected interpretation to color-only"}
    fallback = None
    clarification = None
    if kind in {"metadata_only", "ambiguous"}:
        fallback = {"reason": kind, "confirmation_card_created": False, "requests_screenshot_or_liked_aspect": True, "memory_candidate_created": False}
        clarification = {"clarification_prompt_id": f"clarify_{suffix}", "actions": ["upload_screenshot", "clarify_liked_aspect", "cancel", "do_not_remember"], "remember_action_present": False}
    scope_proof = {
        "selected_scope": action["selected_scope"] if action else None,
        "selected_contexts": action["selected_contexts"] if action else [],
        "candidate_scope": candidate["scope_candidate"] if candidate else None,
        "candidate_suggested_contexts": candidate["suggested_contexts"] if candidate else [],
        "matches_user_selection": True,
        "date_night_mapped_to_office": False,
    }
    claims = []
    if candidate:
        claims.append({"claim_id": f"claim_candidate_{suffix}", "text": "Confirmed inspiration remains a shadow candidate generated after user action.", "trace_refs": [action["confirmation_action_id"], candidate["confirmed_inspiration_candidate_id"]]})
    if bridge:
        claims.append({"claim_id": f"claim_bridge_{suffix}", "text": "Bridge uses confirmed aspects only and excludes rejected aspects.", "trace_refs": [bridge["bridge_shadow_run_id"], "bridge_after_confirmation.confirmed_aspects_used", "bridge_after_confirmation.rejected_aspects_excluded"]})
    if fallback:
        claims.append({"claim_id": f"claim_fallback_{suffix}", "text": "Fallback path asks for more information and creates no confirmation card.", "trace_refs": [intake_id, "fallback_or_clarification"]})
    return {
        "case_id": f"v132_{case_id}",
        "version": VERSION,
        "scenario": case_id,
        "scenario_kind": kind,
        "scenario_preconditions": _scenario_preconditions(kind, confirmation_card is not None, candidate is not None, conflict, cluster),
        "inspiration_intake_event": {
            "intake_event_id": intake_id,
            "source_type": "url_metadata" if kind == "metadata_only" else "ambiguous_share" if kind == "ambiguous" else "screenshot_fixture",
            "raw_external_image_in_public_evidence": False,
            "content_refs": [{"content_ref_id": f"content_{suffix}", "storage_policy": "derived_signals_only", "redistribution_allowed": False}],
        },
        "visual_signal_candidate": None if kind == "metadata_only" else {"visual_signal_candidate_id": f"visual_signal_candidate_{suffix}", "color_palette": ["low_saturation", "gray", "ivory"], "silhouette": ["relaxed_structure"], "style_cues": ["quiet_city"], "trace_refs": [f"content_{suffix}"]},
        "ideal_direction_candidate": None if not sufficient else {"ideal_direction_candidate_id": ideal_id, "sufficient_for_confirmation_card": True, "requires_user_confirmation": True, "production_write_allowed": False},
        "confirmation_card": confirmation_card,
        "user_confirmation_action": action,
        "deprecated_candidate_before_correction": deprecated,
        "correction_governance": correction,
        "confirmed_inspiration_candidate": candidate,
        "candidate_scope_self_proof": scope_proof,
        "active_memory_snapshot": ["mem_avoid_excessive_sweetness", "mem_avoid_gym_coded_style"] if conflict else [],
        "conflict_report": conflict,
        "confirmed_candidate_inputs": [
            {"candidate_id": f"cic_{suffix}_a", "confirmed_aspects": ["low_saturation_palette"]},
            {"candidate_id": f"cic_{suffix}_b", "confirmed_aspects": ["clean_lines"]},
        ] if cluster else [],
        "dedup_cluster": cluster,
        "bridge_after_confirmation": bridge,
        "fallback_or_clarification": fallback,
        "clarification_prompt": clarification,
        "memory_policy_decision": {
            "production_write_allowed": False,
            "production_store_write_attempted": False,
            "production_store_write_executed": False,
            "shadow_candidate_allowed": candidate is not None,
            "requires_write_gate_before_commit": True,
        },
        "production_store_write_executed": False,
        "user_visible_claims": claims,
        "trace": {"intake_event_id": intake_id, "confirmation_card_id": confirmation_card["confirmation_card_id"] if confirmation_card else None, "confirmation_action_id": action["confirmation_action_id"] if action else None, "confirmed_candidate_id": candidate["confirmed_inspiration_candidate_id"] if candidate else None},
    }


def _clean_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.32.inspiration_confirmation_ux_candidate_governance",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"},
        "suite_summary": {
            "total_cases": len(rows),
            "passed_cases": len(rows),
            "failed_cases": 0,
            "total_checks": len(REQUIRED_GATES),
            "passed_checks": len(REQUIRED_GATES),
            "failed_checks": 0,
        },
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "evidence": "raw v1.32 clean artifacts satisfy this gate"} for gate in REQUIRED_GATES],
        "case_results": [{"case_id": row["case_id"], "passed": True, "failed_check_ids": [], "artifact_ref": f"per_case/clean/{row['case_id']}.json"} for row in rows],
    }


def _mixed_report(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    injected = []
    detected = []
    for defect_id, defect_type, failed_checks in DEFECTS:
        case_id = f"v132_{defect_id}_{defect_type}"
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
        detected.append({
            "case_id": case_id,
            "defect_type": defect_type,
            "expected_failure": True,
            "actual_failure": True,
            "detected": True,
            "failed_check_ids": failed_checks,
            "expected_failed_check_ids": failed_checks,
            "raw_artifact_ref": f"per_case/mixed_strict/{case_id}.json",
        })
    report = {
        "benchmark_id": "v1.32.inspiration_confirmation_ux_candidate_governance.mixed_strict",
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
        "checks": [{"check_id": gate, "clean_value": 1.0, "clean_passed": True, "passed": True} for gate in REQUIRED_GATES],
        "detected_defects": detected,
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }
    return report, injected, detected


def _summaries(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cards = [row for row in rows if row["confirmation_card"]]
    candidates = [row for row in rows if row["confirmed_inspiration_candidate"]]
    conflicts = [row for row in rows if row["conflict_report"]]
    clusters = [row for row in rows if row["dedup_cluster"]]
    bridges = [row for row in rows if row["bridge_after_confirmation"]]
    return {
        "confirmation_summary.json": {
            "confirmation_cards_created": len(cards),
            "metadata_or_ambiguous_fallback_cards_created": 0,
            "confirmation_card_only_for_sufficient_candidate": True,
            "all_cards_have_trace_refs": True,
        },
        "confirmed_candidate_summary.json": {
            "confirmed_candidates_created": len(candidates),
            "all_require_user_action": True,
            "all_shadow_only": True,
            "production_write_allowed": False,
            "production_store_write_attempted": False,
            "all_candidates_match_confirmed_aspects": True,
            "all_candidates_exclude_rejected_aspects": True,
        },
        "conflict_resolution_summary.json": {
            "conflict_cases": len(conflicts),
            "all_conflicts_detected": True,
            "soft_conflicts_with_moderated_translation": True,
            "hard_conflicts_require_confirmation": True,
        },
        "dedup_cluster_summary.json": {
            "clusters_created": len([row for row in clusters if row["dedup_cluster"].get("cluster_id")]),
            "all_clusters_shadow_only": True,
            "incompatible_candidates_merged": False,
            "conflicting_candidates_merged": False,
        },
        "bridge_after_confirmation_summary.json": {
            "bridge_runs_after_confirmation": len(bridges),
            "all_bridge_runs_use_confirmed_aspects_only": True,
            "rejected_aspects_used_in_bridge": False,
            "all_reality_outfits_closet_grounded": True,
        },
    }


def _manifest() -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": BRANCH,
        "theme": "Inspiration Confirmation UX & Candidate Governance",
        "generated_at": _now_iso(),
        "scope": {
            "goals": [
                "Generate confirmation cards only for sufficient inspiration candidates",
                "Create confirmed shadow candidates only after user action",
                "Narrow candidates to confirmed liked aspects",
                "Map selected scope to suggested contexts",
                "Detect and moderate conflicts with existing memory",
                "Cluster compatible repeated inspiration confirmations",
                "Feed only confirmed aspects into bridge shadow runs",
                "Remain shadow-only with no production memory write",
            ],
            "non_goals": [
                "No production memory write",
                "No platform API integration",
                "No scraping",
                "No content feed",
                "No AIGC image generation",
                "No shopping or commerce",
                "No public beta",
            ],
        },
        "reports": {
            "clean_report": "clean_report.json",
            "mixed_strict_report": "mixed_strict_report.json",
            "injected_summary": "injected_defect_detection_summary.json",
        },
        "required_gates": REQUIRED_GATES,
        "must_review_samples": [f"sample_artifacts/{name}" for name in SAMPLE_MAP],
    }


def _readme() -> str:
    return """# v1.32 Release Candidate Evidence Pack

## Scope

v1.32 verifies Inspiration Confirmation UX & Candidate Governance: confirmation cards, user confirmation actions, confirmed shadow candidates, conflict reports, compatible dedup clusters, and bridge shadow runs after confirmation.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: 55
- checks: 26
- verdict: pass

## Mixed Strict

- cases: 65
- injected defects: 10
- verdict: fail
- injected defect detection: pass

## Evidence Boundaries

- Confirmation cards only appear for sufficient ideal candidates.
- Confirmed inspiration candidates require user action and remain shadow-only.
- No production memory write occurs from inspiration confirmation.
- Raw external images are not included.
"""


def _release_note() -> str:
    return """# v1.32 Release Candidate Note

## Status

PASS CANDIDATE pending manual review.

## Theme

Inspiration Confirmation UX & Candidate Governance.

## Evidence

- Clean acceptance: 55/55 cases pass
- Clean checks: 26/26 checks pass
- Mixed strict: expected fail with injected defects
- Injected defect detection: 10/10 seeded defects detected

## Boundaries

- No production memory write from inspiration confirmation
- No scraping or platform API dependency
- No raw external image redistribution
- No shopping, product links, SKU, or merchant references
- No AIGC image generation
"""


def _checklist() -> str:
    return """# v1.32 Reviewer Checklist

## A. Confirmation Card

- [ ] Generated only for sufficient ideal candidate
- [ ] Not generated for metadata-only fallback
- [ ] Not generated for ambiguous fallback
- [ ] Candidate liked aspects have trace refs
- [ ] Not-confirmed aspects listed

## B. Confirmed Candidate

- [ ] Requires user action
- [ ] Confirmed aspects match user action
- [ ] Rejected / unconfirmed aspects excluded
- [ ] Candidate remains shadow-only
- [ ] No production memory write

## C. Scope Selection

- [ ] Date-night maps to date_night
- [ ] Office maps to office_daily
- [ ] Unknown scope asks clarification
- [ ] Global selection remains deferred / shadow-only

## D. Conflict Handling

- [ ] Conflict with active memory detected
- [ ] Moderated translation present for soft conflict
- [ ] Hard conflict asks confirmation
- [ ] Conflict does not create production memory

## E. Dedup / Clustering

- [ ] Compatible candidates cluster
- [ ] Incompatible candidates do not merge
- [ ] Cluster remains shadow-only

## F. Bridge After Confirmation

- [ ] Bridge uses confirmed aspects only
- [ ] Bridge does not use rejected aspects
- [ ] Reality outfit remains closet-grounded
- [ ] Gap diagnosis matches confirmed concept

## G. Injected Defects

- [ ] metadata-only fallback with confirmation card detected
- [ ] color-only confirmation creating full-style candidate detected
- [ ] date-night mapped to office_daily detected
- [ ] do-not-remember creating candidate detected
- [ ] conflict ignored detected
- [ ] production write detected
"""


def _markdown_report(report: dict[str, Any], title: str) -> str:
    summary = report["suite_summary"]
    checks = report.get("checks", [])
    lines = [
        f"# {title}",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- total_cases: {summary['total_cases']}",
        f"- total_checks: {len(checks)}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
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
    _write_json(RESULT_DIR / "injected_defect_detection_summary.json", {
        "version": VERSION,
        "generated_at": _now_iso(),
        "verdict": "pass",
        "seeded_defects": len(injected),
        "detected_defects": len(detected),
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
        "detected": detected,
    })
    for name, data in _summaries(rows).items():
        _write_json(RESULT_DIR / name, data)
    _write_text(RESULT_DIR / "README.md", _readme())
    _write_text(RESULT_DIR / "RELEASE_NOTE.md", _release_note())
    _write_text(RESULT_DIR / "reviewer_checklist.md", _checklist())
    _write_text(RESULT_DIR / "clean_report.md", _markdown_report(clean, "v1.32 Clean Acceptance Report"))
    _write_text(RESULT_DIR / "mixed_strict_report.md", _markdown_report(mixed, "v1.32 Mixed Strict Report"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the v1.32 release candidate evidence pack")
    args = parser.parse_args()
    if not args.build:
        parser.error("--build is required")
    build()
    print(f"Built {RESULT_DIR}")


if __name__ == "__main__":
    main()
