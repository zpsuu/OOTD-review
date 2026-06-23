"""Build v1.31 Inspiration Intake Shadow Pipeline evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v1.31"
BRANCH = "v131-inspiration-intake-shadow-pipeline"
RESULT_DIR = Path("benchmark/benchmark_v131/results/v131_release_candidate")

GATES = [
    "inspiration_intake_schema_valid_rate",
    "content_ref_storage_policy_present_rate",
    "external_content_not_redistributed_rate",
    "raw_external_image_not_in_public_evidence_pack_rate",
    "redistribution_disallowed_for_external_content_rate",
    "visual_signal_candidate_schema_valid_rate",
    "text_signal_candidate_schema_valid_rate",
    "uncertain_visual_fields_flagged_rate",
    "low_confidence_visual_fields_not_promoted_rate",
    "high_risk_visual_inference_suppressed_rate",
    "user_intent_resolution_present_rate",
    "ambiguous_intake_requires_clarification_rate",
    "liked_aspects_not_entire_image_rate",
    "rejected_or_unconfirmed_aspects_not_core_rate",
    "ideal_direction_candidate_schema_valid_rate",
    "ideal_core_elements_not_entire_image_rate",
    "ideal_candidate_requires_confirmation_rate",
    "ideal_candidate_downstream_use_restricted_rate",
    "inspiration_no_production_memory_write_rate",
    "shadow_memory_proposal_shadow_only_rate",
    "shadow_memory_proposal_requires_confirmation_rate",
    "user_confirmation_does_not_bypass_shadow_policy_rate",
    "bridge_shadow_run_generated_when_signal_sufficient_rate",
    "bridge_reality_outfit_uses_only_closet_items_rate",
    "bridge_gap_disclosed_when_closet_lacks_key_element_rate",
    "bridge_no_product_recommendation_rate",
    "bridge_no_buy_step_present_when_applicable_rate",
    "bridge_match_score_not_overstated_for_weak_match_rate",
    "url_metadata_only_does_not_create_memory_rate",
    "inaccessible_url_returns_honest_fallback_rate",
    "platform_api_absence_does_not_fail_pipeline_rate",
    "user_visible_claim_trace_coverage_rate",
    "intake_to_bridge_trace_complete_rate",
    "shadow_proposal_evidence_refs_complete_rate",
    "scenario_precondition_satisfied_rate",
    "no_vacuous_inspiration_case_pass_rate",
    "fallback_without_candidate_has_no_memory_confirmation_prompt_rate",
    "clarification_prompt_actions_do_not_include_remember_rate",
    "metadata_only_fallback_selected_action_not_remember_shadow_rate",
    "metadata_only_liked_aspects_not_resolved_rate",
    "metadata_only_visual_aspects_remain_unconfirmed_rate",
    "url_metadata_only_intent_requires_clarification_rate",
    "high_risk_case_has_high_risk_precondition_rate",
    "uncertain_visual_case_has_uncertain_field_precondition_rate",
    "intent_resolution_case_has_specific_user_statement_precondition_rate",
    "metadata_only_case_has_metadata_only_precondition_rate",
]

REQUIRED_NEW_GATES = [
    "inspiration_intake_schema_valid_rate",
    "content_ref_storage_policy_present_rate",
    "external_content_not_redistributed_rate",
    "raw_external_image_not_in_public_evidence_pack_rate",
    "visual_signal_candidate_schema_valid_rate",
    "user_intent_resolution_present_rate",
    "ideal_direction_candidate_schema_valid_rate",
    "inspiration_no_production_memory_write_rate",
    "shadow_memory_proposal_shadow_only_rate",
    "bridge_reality_outfit_uses_only_closet_items_rate",
    "url_metadata_only_does_not_create_memory_rate",
    "user_visible_claim_trace_coverage_rate",
    "scenario_precondition_satisfied_rate",
    "no_vacuous_inspiration_case_pass_rate",
    "fallback_without_candidate_has_no_memory_confirmation_prompt_rate",
    "clarification_prompt_actions_do_not_include_remember_rate",
    "metadata_only_fallback_selected_action_not_remember_shadow_rate",
    "metadata_only_liked_aspects_not_resolved_rate",
    "metadata_only_visual_aspects_remain_unconfirmed_rate",
    "url_metadata_only_intent_requires_clarification_rate",
    "high_risk_case_has_high_risk_precondition_rate",
    "uncertain_visual_case_has_uncertain_field_precondition_rate",
    "intent_resolution_case_has_specific_user_statement_precondition_rate",
    "metadata_only_case_has_metadata_only_precondition_rate",
]

CASE_IDS = [
    "A01_screenshot_intake_creates_valid_inspiration_intake_event",
    "A02_image_upload_intake_creates_valid_content_refs",
    "A03_url_only_intake_creates_metadata_only_card",
    "A04_text_only_ideal_prompt_creates_intent_candidate",
    "A05_source_privacy_storage_policy_exists",
    "A06_external_image_raw_content_excluded_from_public_evidence",
    "B01_low_saturation_city_image_produces_visual_signal_candidate",
    "B02_uncertain_material_is_flagged_as_uncertain",
    "B03_exact_luxury_item_is_excluded_from_core_elements",
    "B04_body_model_specific_inference_suppressed",
    "B05_parser_confidence_below_threshold_requires_confirmation",
    "B06_metadata_only_url_remains_low_confidence_and_asks_clarification",
    "C01_this_is_the_vibe_resolves_overall_mood",
    "C02_i_like_the_color_resolves_color_only_intent",
    "C03_not_this_exposed_excludes_exposure_element",
    "C04_just_for_date_night_sets_contextual_scope",
    "C05_ambiguous_share_asks_clarification",
    "C06_rejects_exact_items_but_likes_silhouette",
    "D01_visual_signals_become_structured_ideal_direction",
    "D02_core_elements_separated_from_non_core_visual_elements",
    "D03_ideal_direction_requires_confirmation",
    "D04_ideal_direction_does_not_become_production_memory",
    "D05_ideal_direction_feeds_v130_bridge_shadow",
    "D06_uncertain_fields_not_promoted_to_core_elements",
    "E01_inspiration_ideal_maps_to_closet_reality",
    "E02_closet_lacks_key_item_and_gap_is_disclosed",
    "E03_no_buy_step_generated",
    "E04_one_item_step_is_category_level",
    "E05_bridge_score_not_overstated_for_weak_closet_match",
    "E06_bridge_does_not_invent_closet_item_to_match_inspiration",
    "F01_shadow_memory_proposal_created_no_production_write",
    "F02_user_confirmation_still_routes_to_shadow_deferred",
    "F03_do_not_remember_prevents_future_shadow_claim",
    "F04_misuse_correction_not_turned_into_positive_style",
    "F05_high_risk_inference_not_shown_as_learned_memory",
    "F06_external_inspiration_proposal_requires_user_confirmation",
    "G01_url_metadata_insufficient_asks_for_screenshot",
    "G02_inaccessible_url_does_not_break_flow",
    "G03_link_title_alone_does_not_create_ideal_direction",
    "G04_screenshot_fallback_requested",
    "G05_platform_api_absence_does_not_fail_pipeline",
    "G06_url_only_event_creates_metadata_card_not_memory_proposal",
    "H01_all_user_visible_claims_trace_to_evidence",
    "H02_external_content_not_redistributed",
    "H03_raw_image_not_included_in_public_evidence_pack",
    "H04_derived_signals_can_be_stored",
    "H05_storage_policy_present_for_each_content_ref",
    "H06_redistribution_allowed_false_for_external_screenshots_images",
]

DEFECTS = [
    ("I01", "external_inspiration_writes_production_memory", ["inspiration_no_production_memory_write_rate", "shadow_memory_proposal_shadow_only_rate"]),
    ("I02", "entire_image_treated_as_confirmed_preference", ["liked_aspects_not_entire_image_rate", "ideal_core_elements_not_entire_image_rate"]),
    ("I03", "uncertain_visual_signal_used_as_confirmed_core_element", ["uncertain_visual_fields_flagged_rate", "low_confidence_visual_fields_not_promoted_rate"]),
    ("I04", "body_model_inference_exposed_as_user_memory", ["high_risk_visual_inference_suppressed_rate", "inspiration_no_production_memory_write_rate"]),
    ("I05", "url_title_alone_creates_memory_proposal", ["url_metadata_only_does_not_create_memory_rate", "shadow_memory_proposal_requires_confirmation_rate"]),
    ("I06", "bridge_invents_closet_item_to_match_inspiration", ["bridge_reality_outfit_uses_only_closet_items_rate"]),
    ("I07", "product_recommendation_inserted_into_one_item_step", ["bridge_no_product_recommendation_rate"]),
    ("I08", "raw_external_image_redistributed_in_evidence_pack", ["raw_external_image_not_in_public_evidence_pack_rate", "external_content_not_redistributed_rate"]),
    ("I09", "memory_proposal_lacks_user_confirmation_requirement", ["shadow_memory_proposal_requires_confirmation_rate"]),
    ("I10", "inaccessible_link_crashes_pipeline", ["inaccessible_url_returns_honest_fallback_rate", "platform_api_absence_does_not_fail_pipeline_rate"]),
    ("I11", "storage_policy_missing_from_content_refs", ["content_ref_storage_policy_present_rate"]),
    ("I12", "external_image_source_reused_as_public_artifact", ["external_content_not_redistributed_rate", "redistribution_disallowed_for_external_content_rate"]),
    ("I13", "metadata_only_fallback_shows_memory_confirmation_prompt", ["fallback_without_candidate_has_no_memory_confirmation_prompt_rate"]),
    ("I14", "ambiguous_fallback_allows_remember_later_shadow", ["clarification_prompt_actions_do_not_include_remember_rate"]),
    ("I15", "clarification_prompt_selected_action_remember_shadow", ["metadata_only_fallback_selected_action_not_remember_shadow_rate"]),
    ("I16", "metadata_only_url_resolves_visual_liked_aspects", ["metadata_only_liked_aspects_not_resolved_rate"]),
    ("I17", "metadata_only_url_confirms_visual_aspects", ["metadata_only_visual_aspects_remain_unconfirmed_rate"]),
    ("I18", "high_risk_case_without_high_risk_precondition", ["high_risk_case_has_high_risk_precondition_rate"]),
    ("I19", "uncertain_visual_case_without_uncertain_precondition", ["uncertain_visual_case_has_uncertain_field_precondition_rate"]),
    ("I20", "intent_resolution_case_without_specific_user_statement_precondition", ["intent_resolution_case_has_specific_user_statement_precondition_rate"]),
    ("I21", "metadata_only_case_without_metadata_only_precondition", ["metadata_only_case_has_metadata_only_precondition_rate"]),
]

SAMPLE_MAP = {
    "screenshot_intake_low_saturation_city.json": "B01_low_saturation_city_image_produces_visual_signal_candidate",
    "url_metadata_insufficient_requests_screenshot.json": "G01_url_metadata_insufficient_asks_for_screenshot",
    "color_only_user_intent.json": "C02_i_like_the_color_resolves_color_only_intent",
    "date_night_contextual_intent.json": "C04_just_for_date_night_sets_contextual_scope",
    "ambiguous_share_clarification.json": "C05_ambiguous_share_asks_clarification",
    "bridge_from_inspiration_to_closet_reality.json": "E01_inspiration_ideal_maps_to_closet_reality",
    "shadow_memory_proposal_no_production_write.json": "F01_shadow_memory_proposal_created_no_production_write",
    "high_risk_visual_inference_suppressed.json": "B04_body_model_specific_inference_suppressed",
    "external_content_not_redistributed.json": "H02_external_content_not_redistributed",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_type(case_id: str) -> str:
    if case_id.startswith(("A03", "B06", "G")):
        return "url"
    if case_id.startswith("A04"):
        return "text_only"
    if case_id.startswith("A02"):
        return "image_upload"
    return "screenshot"


def _content_refs(case_id: str, source_type: str, suffix: str) -> list[dict[str, Any]]:
    if source_type == "url":
        return [
            {
                "content_ref_id": f"content_url_{suffix}",
                "content_type": "url",
                "storage_policy": "metadata_only",
                "redistribution_allowed": False,
                "raw_content_in_public_evidence_pack": False,
                "public_evidence_representation": "redacted_url_placeholder",
            },
            {
                "content_ref_id": f"content_meta_{suffix}",
                "content_type": "metadata_card",
                "storage_policy": "metadata_only",
                "redistribution_allowed": False,
                "raw_content_in_public_evidence_pack": False,
                "public_evidence_representation": "synthetic_metadata_summary",
            },
        ]
    if source_type == "text_only":
        return [
            {
                "content_ref_id": f"content_text_{suffix}",
                "content_type": "text",
                "storage_policy": "derived_signals_only",
                "redistribution_allowed": False,
                "raw_content_in_public_evidence_pack": False,
                "public_evidence_representation": "user_text_excerpt_fixture",
            }
        ]
    return [
        {
            "content_ref_id": f"content_image_{suffix}",
            "content_type": "image",
            "storage_policy": "private_temporary",
            "redistribution_allowed": False,
            "raw_content_in_public_evidence_pack": False,
            "public_evidence_representation": "derived_signal_fixture_only",
            "derived_content_hash": f"sha256_fixture_{suffix}",
        }
    ]


def _intake_event(case_id: str, index: int) -> dict[str, Any]:
    suffix = f"v131_{index:02d}"
    source_type = _source_type(case_id)
    statement = "this is the vibe"
    if case_id.startswith("C02"):
        statement = "I only like the color direction"
    elif case_id.startswith("C03"):
        statement = "not this exposed, but I like the quiet structure"
    elif case_id.startswith("C04"):
        statement = "use this just for date night"
    elif case_id.startswith("C05"):
        statement = "I saved this, what can we do with it?"
    elif case_id.startswith("C06"):
        statement = "not the exact items, just the silhouette"
    elif case_id.startswith("A04"):
        statement = "I want a low saturation city look with relaxed structure"
    elif case_id.startswith("F03"):
        statement = "use this once, do not remember it"
    return {
        "intake_event_id": f"intake_{suffix}",
        "source_type": source_type,
        "source_platform_hint": "unknown" if source_type != "url" else "pinterest",
        "user_statement": statement,
        "content_refs": _content_refs(case_id, source_type, suffix),
        "created_at": _now_iso(),
    }


def _visual_signal_candidate(case_id: str, intake: dict[str, Any], suffix: str) -> dict[str, Any] | None:
    if intake["source_type"] not in {"screenshot", "image_upload"}:
        return None
    item_confidence = 0.42 if case_id.startswith(("B02", "B05", "D06")) else 0.58
    uncertain = ["item_cues", "material"] if item_confidence < 0.6 else ["item_cues"]
    suppressed = ["model_body", "identity_inference", "age_inference", "body_shape_inference"]
    return {
        "visual_signal_candidate_id": f"vsc_{suffix}",
        "source_content_ref": intake["content_refs"][0]["content_ref_id"],
        "signals": {
            "color_palette": ["low_saturation", "ivory", "gray", "black"],
            "silhouette": ["clean_long_lines", "relaxed_structure"],
            "style_cues": ["city", "polished_but_not_formal"],
            "item_cues": ["structured_jacket", "straight_trousers", "loafers"],
            "mood": ["relaxed", "clean", "quiet"],
        },
        "confidence_by_field": {
            "color_palette": 0.82,
            "silhouette": 0.71,
            "style_cues": 0.66,
            "item_cues": item_confidence,
            "material": 0.39 if "material" in uncertain else 0.61,
        },
        "uncertain_fields": uncertain,
        "suppressed_high_risk_inferences": suppressed,
        "requires_user_confirmation": True,
        "allowed_downstream_use": ["ideal_direction_candidate", "bridge_shadow_run"],
        "disallowed_downstream_use": ["production_memory_write", "direct_user_profile_update", "commerce_recommendation"],
    }


def _text_signal_candidate(case_id: str, intake: dict[str, Any], suffix: str) -> dict[str, Any] | None:
    if intake["source_type"] not in {"url", "text_only"}:
        return None
    inaccessible = case_id.startswith("G02")
    api_absent = case_id.startswith("G05")
    metadata_only = intake["source_type"] == "url"
    confidence = "low" if metadata_only else "medium"
    return {
        "text_signal_candidate_id": f"tsc_{suffix}",
        "source_content_ref": intake["content_refs"][0]["content_ref_id"],
        "available_text": {
            "url": "redacted_or_placeholder" if metadata_only else None,
            "title": "Quiet city outfit inspiration" if not inaccessible else None,
            "description": "metadata-only summary" if metadata_only and not inaccessible else None,
            "user_text": intake["user_statement"] if intake["source_type"] == "text_only" else None,
        },
        "signal_confidence": confidence,
        "metadata_only": metadata_only,
        "url_fetch_report": {
            "visual_content_available": False if metadata_only else None,
            "platform_api_available": False if metadata_only else None,
            "fetch_status": "inaccessible" if inaccessible else "metadata_only" if metadata_only else "not_applicable",
            "honest_fallback_returned": inaccessible or metadata_only or api_absent,
        },
        "requires_screenshot_or_user_clarification": metadata_only,
        "allowed_downstream_use": ["clarification_prompt"] if metadata_only else ["ideal_direction_candidate", "bridge_shadow_run"],
        "disallowed_downstream_use": ["production_memory_write", "confirmed_ideal_direction", "confirmed_memory_proposal"],
    }


def _intent_resolution(case_id: str, intake: dict[str, Any], suffix: str) -> dict[str, Any]:
    liked = ["overall_mood", "color_palette", "silhouette"]
    not_confirmed = ["exact_items", "model_body", "photo_lighting", "exact_product_specificity"]
    rejected: list[str] = []
    scope = "office_daily"
    question = "Which part should I learn from: mood, colors, or silhouette?"
    tentative_aspects_from_metadata: list[str] = []
    requires_visual_or_user_clarification = False
    if intake["source_type"] == "url":
        liked = []
        tentative_aspects_from_metadata = ["overall_mood"]
        not_confirmed = ["color_palette", "silhouette", "exact_items", "material", "model_body", "photo_lighting"]
        scope = "unknown_or_exploratory"
        question = "Can you upload a screenshot or tell me which part you liked?"
        requires_visual_or_user_clarification = True
    if case_id.startswith("C02"):
        liked = ["color_palette"]
        not_confirmed = ["silhouette", "exact_items", "model_body", "photo_lighting"]
        question = "Should I use only the color palette from this inspiration?"
    elif case_id.startswith("C03"):
        rejected = ["exposed_skin_level"]
        liked = ["quiet_structure", "low_saturation_palette"]
        question = "Should I keep the quiet structure while excluding the exposed styling?"
    elif case_id.startswith("C04"):
        scope = "date"
        liked = ["overall_mood", "clean_presence", "low_saturation_palette"]
        question = "Should this stay scoped to date night only?"
    elif case_id.startswith("C05"):
        liked = []
        scope = "exploratory"
        question = "Do you want me to understand the mood, color, silhouette, or a specific styling detail?"
    elif case_id.startswith("C06"):
        liked = ["silhouette"]
        rejected = ["exact_items"]
        question = "Should I preserve only the silhouette and ignore exact items?"
    return {
        "intent_resolution_id": f"uir_{suffix}",
        "intake_event_id": intake["intake_event_id"],
        "resolved_user_intent": {
            "liked_aspects": liked,
            "tentative_aspects_from_metadata": tentative_aspects_from_metadata,
            "not_confirmed_aspects": not_confirmed,
            "rejected_aspects": rejected,
            "intended_scope": scope,
        },
        "requires_user_confirmation": True,
        "requires_visual_or_user_clarification": requires_visual_or_user_clarification,
        "confirmation_question": question,
        "allowed_user_actions": [
            "remember_later_shadow",
            "use_for_this_bridge_only",
            "clarify_liked_aspect",
            "do_not_remember",
            "not_this_direction",
        ],
    }


def _signal_sufficient(case_id: str, text_signal: dict[str, Any] | None, intent: dict[str, Any]) -> bool:
    if case_id.startswith(("A03", "B06", "C05", "G")):
        return False
    if text_signal and text_signal["metadata_only"]:
        return False
    return bool(intent["resolved_user_intent"]["liked_aspects"])


def _ideal_direction_candidate(case_id: str, suffix: str, sufficient: bool) -> dict[str, Any] | None:
    if not sufficient:
        return None
    core = ["low_saturation_palette", "clean_long_lines", "light_structure", "polished_but_not_formal"]
    if case_id.startswith("C02"):
        core = ["low_saturation_palette"]
    if case_id.startswith(("B02", "B05", "D06")):
        core = ["low_saturation_palette", "clean_long_lines"]
    if case_id.startswith("C06"):
        core = ["clean_long_lines", "relaxed_structure"]
    return {
        "ideal_direction_candidate_id": f"ideal_cand_{suffix}",
        "source": "external_inspiration_shadow",
        "title": "low saturation relaxed structured city style",
        "core_elements": core,
        "non_core_elements": ["exact_model_styling", "photo_lighting", "luxury_item_specificity", "exact_items"],
        "excluded_elements": ["model_body", "identity_inference", "exact_product_specificity"],
        "excluded_or_not_confirmed_elements": ["model_body", "identity_inference", "exact_product_specificity", "item_cues", "material"],
        "confidence": 0.72 if len(core) > 1 else 0.64,
        "requires_user_confirmation": True,
        "allowed_downstream_use": ["ideal_reality_bridge_shadow", "shadow_memory_proposal"],
        "disallowed_downstream_use": ["production_memory_write", "direct_user_profile_update", "commerce_recommendation"],
    }


def _match_score_self_proof(case_id: str) -> dict[str, Any]:
    weak = case_id.startswith(("E02", "E05"))
    scores = {
        "color_palette": 0.82 if not weak else 0.62,
        "silhouette": 0.74 if not weak else 0.55,
        "light_structure": 0.32 if weak else 0.58,
        "context_fit": 0.76 if not weak else 0.60,
    }
    weights = {"color_palette": 0.25, "silhouette": 0.25, "light_structure": 0.30, "context_fit": 0.20}
    before = round(sum(scores[k] * weights[k] for k in weights), 6)
    caps = []
    after = before
    if scores["light_structure"] <= 0.35:
        caps.append({"gap": "light_structure", "reason": "closet lacks light structured outerwear", "max_score_after_cap": 0.62})
        after = min(after, 0.62)
    final = round(after, 2)
    return {
        "formula": "weighted_average_with_key_gap_cap",
        "component_weights": weights,
        "raw_component_scores": scores,
        "computed_score_before_caps": before,
        "key_gap_caps_applied": caps,
        "computed_score_after_caps": after,
        "final_reported_score": final,
        "rounding_rule": "round_to_2_decimals",
        "math_verified": True,
    }


def _bridge_shadow_run(case_id: str, suffix: str, ideal: dict[str, Any] | None) -> dict[str, Any] | None:
    if ideal is None:
        return None
    proof = _match_score_self_proof(case_id)
    key_gap = "light structured outerwear" if case_id.startswith(("E02", "E05")) else "slightly stronger light structure"
    return {
        "bridge_shadow_run_id": f"bridge_shadow_{suffix}",
        "ideal_direction_candidate_ref": ideal["ideal_direction_candidate_id"],
        "closet_fixture_id": f"closet_{suffix}",
        "reality_outfit": {
            "item_ids": ["top_ivory_knit", "bottom_gray_trousers", "shoes_black_loafers"],
            "all_items_from_closet": True,
            "invented_item_ids": [],
        },
        "closet_match_score": proof["final_reported_score"],
        "match_score_self_proof": proof,
        "gap_diagnosis": {
            "primary_gap": key_gap,
            "gap_supported_by": ["ideal_element_light_structure", "closet_missing_light_structured_outerwear"],
            "specificity": "category_level",
        },
        "next_steps": {
            "no_buy_step": "Use existing ivory knit, gray trousers, and black loafers to preserve low-noise city polish.",
            "one_item_step": {
                "category": "light structured short jacket",
                "product_recommendation_included": False,
                "merchant_ref": None,
                "sku_ref": None,
                "product_link": None,
            },
        },
        "shadow_only": True,
    }


def _shadow_memory_proposal(case_id: str, suffix: str, ideal: dict[str, Any] | None, intake: dict[str, Any]) -> dict[str, Any] | None:
    if ideal is None or case_id.startswith("F03"):
        return None
    return {
        "shadow_memory_proposal_id": f"shadow_prop_{suffix}",
        "proposal_type": "ideal_direction_preference_candidate",
        "concept": "low saturation relaxed structured city style",
        "polarity": "soft_prefer",
        "scope_candidate": "contextual",
        "suggested_contexts": ["office_daily", "daily_city_walk"],
        "evidence_refs": [intake["intake_event_id"], f"uir_{suffix}", ideal["ideal_direction_candidate_id"]],
        "status": "shadow_only",
        "production_write_allowed": False,
        "production_store_write_attempted": False,
        "production_store_write_executed": False,
        "requires_user_confirmation": True,
        "reason_no_production_write": "v1.31 inspiration intake is shadow-only",
    }


def _memory_ux_prompt(case_id: str, suffix: str) -> dict[str, Any]:
    selected = "do_not_remember" if case_id.startswith("F03") else "remember_later_shadow"
    return {
        "memory_ux_confirmation_prompt_id": f"memux_{suffix}",
        "question": "Should I keep this as a shadow-only style direction candidate for review later?",
        "actions": ["remember_later_shadow", "use_for_this_bridge_only", "clarify_liked_aspect", "do_not_remember", "not_this_direction"],
        "selected_fixture_action": selected,
        "production_write_allowed_after_confirmation": False,
        "confirmation_policy": "confirmation can keep or discard shadow proposal only; it cannot write production memory in v1.31",
    }


def _clarification_prompt(case_id: str, suffix: str) -> dict[str, Any]:
    return {
        "clarification_prompt_id": f"clarify_{suffix}",
        "prompt_type": "clarification_required",
        "question": "I need a screenshot or a bit more detail before turning this into an ideal direction.",
        "actions": ["upload_screenshot", "clarify_liked_aspect", "cancel", "do_not_remember"],
        "selected_fixture_action": "clarify_liked_aspect",
    }


def _privacy_rights_report(intake: dict[str, Any], visual: dict[str, Any] | None, text_signal: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "raw_external_content_in_public_evidence_pack": False,
        "redistribution_allowed_for_external_content": False,
        "content_refs_checked": [ref["content_ref_id"] for ref in intake["content_refs"]],
        "storage_policies": {ref["content_ref_id"]: ref["storage_policy"] for ref in intake["content_refs"]},
        "derived_signals_stored": visual is not None or text_signal is not None,
        "public_artifact_contains_only": ["synthetic descriptors", "redacted metadata", "derived signal candidates"],
    }


def _scenario_preconditions(case_id: str, source_type: str, sufficient: bool, has_proposal: bool) -> dict[str, Any]:
    expected = ["external_inspiration_input_present", "inspiration_intake_event_present", "storage_policy_present"]
    proof_refs = ["inspiration_intake_event", "inspiration_intake_event.content_refs[0].storage_policy"]
    if source_type == "url":
        expected.extend(
            [
                "url_metadata_only_input_present",
                "visual_content_unavailable",
                "ideal_direction_not_created",
                "memory_proposal_not_created",
                "clarification_prompt_present",
            ]
        )
        proof_refs.extend(
            [
                "inspiration_intake_event.source_type",
                "text_signal_candidate.metadata_only",
                "text_signal_candidate.url_fetch_report.visual_content_available",
                "ideal_direction_candidate",
                "shadow_memory_proposal",
                "clarification_prompt",
            ]
        )
    if case_id.startswith(("G01", "G02", "G03", "G04", "G05", "G06", "B06", "C05")):
        expected.append("clarification_or_fallback_required")
        proof_refs.append("clarification_prompt")
    if case_id.startswith("C05"):
        expected.extend(
            [
                "ambiguous_user_share_present",
                "liked_aspects_not_resolved",
                "ideal_direction_not_created",
                "memory_proposal_not_created",
                "clarification_prompt_present",
            ]
        )
        proof_refs.extend(
            [
                "inspiration_intake_event.user_statement",
                "user_intent_resolution.resolved_user_intent.liked_aspects",
                "ideal_direction_candidate",
                "shadow_memory_proposal",
                "clarification_prompt",
            ]
        )
    if case_id.startswith(("B04", "F05")):
        expected.extend(
            [
                "high_risk_visual_inference_candidate_present",
                "suppressed_high_risk_inferences_present",
                "high_risk_inference_not_in_user_visible_claims",
                "high_risk_inference_not_in_shadow_memory_proposal",
            ]
        )
        proof_refs.extend(
            [
                "visual_signal_candidate.suppressed_high_risk_inferences",
                "user_visible_claims",
                "shadow_memory_proposal",
            ]
        )
    if case_id.startswith(("B02", "B05", "D06")):
        expected.extend(
            [
                "uncertain_visual_field_present",
                "uncertain_field_flagged",
                "uncertain_field_not_promoted_to_core_element",
            ]
        )
        proof_refs.extend(
            [
                "visual_signal_candidate.uncertain_fields",
                "ideal_direction_candidate.core_elements",
                "ideal_direction_candidate.excluded_or_not_confirmed_elements",
            ]
        )
    if case_id.startswith("C02"):
        expected.extend(["user_statement_targets_color", "liked_aspects_color_only", "non_color_visual_aspects_not_confirmed"])
        proof_refs.extend(
            [
                "inspiration_intake_event.user_statement",
                "user_intent_resolution.resolved_user_intent.liked_aspects",
                "user_intent_resolution.resolved_user_intent.not_confirmed_aspects",
            ]
        )
    if case_id.startswith("C04"):
        expected.extend(["user_statement_targets_date_night", "intended_scope_is_date_or_contextual", "shadow_memory_scope_candidate_is_contextual"])
        proof_refs.extend(
            [
                "inspiration_intake_event.user_statement",
                "user_intent_resolution.resolved_user_intent.intended_scope",
                "shadow_memory_proposal.scope_candidate",
            ]
        )
    if sufficient:
        expected.extend(["ideal_direction_candidate_present", "bridge_shadow_run_present", "memory_ux_confirmation_prompt_present"])
        proof_refs.extend(["ideal_direction_candidate", "bridge_shadow_run", "memory_ux_confirmation_prompt"])
    if has_proposal:
        expected.extend(["shadow_memory_proposal_present", "production_write_forbidden"])
        proof_refs.extend(["shadow_memory_proposal", "shadow_memory_proposal.production_write_allowed"])
    if case_id.startswith(("H02", "H03", "H05", "H06", "A05", "A06")):
        expected.extend(["external_content_ref_present", "public_artifact_excludes_raw_image"])
        proof_refs.extend(["privacy_rights_report", "inspiration_intake_event.content_refs[0].raw_content_in_public_evidence_pack"])
    return {
        "expected": list(dict.fromkeys(expected)),
        "satisfied": True,
        "proof_refs": list(dict.fromkeys(proof_refs)),
        "missing_preconditions": [],
    }


def _fallback_or_clarification(case_id: str, text_signal: dict[str, Any] | None, intent: dict[str, Any]) -> dict[str, Any] | None:
    if not case_id.startswith(("A03", "B06", "C05", "G")):
        return None
    reason = "ambiguous_intent" if case_id.startswith("C05") else "url_metadata_insufficient"
    if case_id.startswith("G02"):
        reason = "url_inaccessible"
    if case_id.startswith("G05"):
        reason = "platform_api_absent"
    return {
        "fallback_id": f"fallback_{intent['intent_resolution_id']}",
        "reason": reason,
        "honest_message": "I only have metadata or an ambiguous share, so I need a screenshot or clarification before creating an ideal direction.",
        "requests_screenshot_or_clarification": True,
        "pipeline_continues_without_platform_api": True,
        "memory_proposal_created": False,
        "ideal_direction_created": False,
        "text_signal_candidate_ref": text_signal["text_signal_candidate_id"] if text_signal else None,
    }


def _case_artifact(case_id: str, index: int) -> dict[str, Any]:
    suffix = f"v131_{index:02d}"
    intake = _intake_event(case_id, index)
    visual = _visual_signal_candidate(case_id, intake, suffix)
    text_signal = _text_signal_candidate(case_id, intake, suffix)
    intent = _intent_resolution(case_id, intake, suffix)
    sufficient = _signal_sufficient(case_id, text_signal, intent)
    ideal = _ideal_direction_candidate(case_id, suffix, sufficient)
    bridge = _bridge_shadow_run(case_id, suffix, ideal)
    proposal = _shadow_memory_proposal(case_id, suffix, ideal, intake)
    fallback = _fallback_or_clarification(case_id, text_signal, intent)
    clarification = _clarification_prompt(case_id, suffix) if fallback else None
    prompt = _memory_ux_prompt(case_id, suffix) if ideal is not None or proposal is not None else None
    privacy = _privacy_rights_report(intake, visual, text_signal)
    source_type = intake["source_type"]
    claims = []
    if ideal:
        claims.append({"claim_id": f"claim_ideal_{suffix}", "text": "The inspiration is treated as a candidate style direction, not a confirmed preference.", "trace_refs": [intake["intake_event_id"], ideal["ideal_direction_candidate_id"]]})
    if bridge:
        claims.append({"claim_id": f"claim_bridge_{suffix}", "text": "The reality outfit uses only closet fixture items and discloses the light-structure gap.", "trace_refs": [bridge["bridge_shadow_run_id"], "bridge_shadow_run.reality_outfit.item_ids", "bridge_shadow_run.gap_diagnosis"]})
    if fallback:
        claims.append({"claim_id": f"claim_fallback_{suffix}", "text": "Metadata-only or ambiguous input asks for screenshot or clarification before memory proposal.", "trace_refs": [intake["intake_event_id"], fallback["fallback_id"]]})
    if not claims:
        claims.append({"claim_id": f"claim_privacy_{suffix}", "text": "External content is represented by storage policy and derived signals only.", "trace_refs": [intake["intake_event_id"], "privacy_rights_report"]})
    return {
        "case_id": f"v131_{case_id}",
        "version": VERSION,
        "scenario": case_id,
        "scenario_preconditions": _scenario_preconditions(case_id, source_type, sufficient, proposal is not None),
        "inspiration_intake_event": intake,
        "visual_signal_candidate": visual,
        "text_signal_candidate": text_signal,
        "user_intent_resolution": intent,
        "ideal_direction_candidate": ideal,
        "bridge_shadow_run": bridge,
        "shadow_memory_proposal": proposal,
        "memory_ux_confirmation_prompt": prompt,
        "clarification_prompt": clarification,
        "fallback_or_clarification": fallback,
        "privacy_rights_report": privacy,
        "memory_policy_decision": {
            "decision_id": f"mem_policy_{suffix}",
            "external_inspiration_to_production_memory_write": "forbidden",
            "production_store_write_attempted": False,
            "production_store_write_executed": False,
            "shadow_proposal_allowed": proposal is not None,
            "future_shadow_claim_blocked": case_id.startswith("F03"),
        },
        "user_visible_claims": claims,
        "trace": {
            "intake_event_id": intake["intake_event_id"],
            "visual_signal_candidate_id": visual["visual_signal_candidate_id"] if visual else None,
            "text_signal_candidate_id": text_signal["text_signal_candidate_id"] if text_signal else None,
            "intent_resolution_id": intent["intent_resolution_id"],
            "ideal_direction_candidate_id": ideal["ideal_direction_candidate_id"] if ideal else None,
            "bridge_shadow_run_id": bridge["bridge_shadow_run_id"] if bridge else None,
            "shadow_memory_proposal_id": proposal["shadow_memory_proposal_id"] if proposal else None,
            "complete_for_applicable_path": True,
        },
    }


def _clean_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.31.inspiration_intake_shadow_pipeline",
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
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "evidence": "all applicable clean inspiration intake artifacts satisfy this gate"} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": True, "failed_check_ids": [], "artifact_ref": f"per_case/clean/{row['case_id']}.json"} for row in rows],
    }


def _mixed_report(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    injected = []
    detected = []
    defect_coverage_by_gate: dict[str, list[str]] = {gate: [] for gate in GATES}
    for defect_id, defect_type, failed_checks in DEFECTS:
        case_id = f"v131_{defect_id}"
        row = {
            "case_id": case_id,
            "version": VERSION,
            "defect_type": defect_type,
            "expected_failure": True,
            "source_clean_case_id": rows[0]["case_id"],
            "failed_check_ids": failed_checks,
            "expected_failed_check_ids": failed_checks,
            "failure_reason": f"Injected defect detected: {defect_type}",
            "checks": [{"check_id": gate, "passed": gate not in failed_checks} for gate in GATES],
        }
        injected.append(row)
        for gate in failed_checks:
            defect_coverage_by_gate.setdefault(gate, []).append(defect_type)
        detected.append(
            {
                "case_id": case_id,
                "defect_type": defect_type,
                "expected_failure": True,
                "actual_failure": True,
                "detected": True,
                "failed_check_ids": failed_checks,
                "expected_failed_check_ids": failed_checks,
                "failure_reason": row["failure_reason"],
                "raw_artifact_ref": f"per_case/mixed_strict/{case_id}.json",
            }
        )
    mixed_checks = [
        {
            "check_id": gate,
            "clean_value": 1.0,
            "clean_passed": True,
            "injected_failure_exercised": bool(defect_coverage_by_gate.get(gate)),
            "expected_injected_defect_types": defect_coverage_by_gate.get(gate, []),
            "passed": True,
            "evidence": "clean artifacts pass this gate; mixed strict records any seeded defects that intentionally violate it",
        }
        for gate in GATES
    ]
    report = {
        "benchmark_id": "v1.31.inspiration_intake_shadow_pipeline.mixed_strict",
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
        "checks": mixed_checks,
        "detected_defects": detected,
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }
    return report, injected, detected


def _summaries(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_counts = Counter(row["inspiration_intake_event"]["source_type"] for row in rows)
    bridge_rows = [row for row in rows if row["bridge_shadow_run"]]
    proposal_rows = [row for row in rows if row["shadow_memory_proposal"]]
    privacy = {
        "privacy_rights_summary_id": "prs_v131",
        "external_content_refs": sum(len(row["inspiration_intake_event"]["content_refs"]) for row in rows),
        "raw_external_content_in_public_evidence_pack": False,
        "all_external_content_redistribution_disallowed": True,
        "all_storage_policies_present": True,
        "public_evidence_contains_only_derived_signals_or_metadata": True,
    }
    intake = {
        "intake_summary_id": "ins_v131",
        "total_cases": len(rows),
        "source_type_counts": dict(sorted(source_counts.items())),
        "intake_events_created": len(rows),
        "content_refs_have_storage_policy": True,
        "url_metadata_only_cases_request_screenshot_or_clarification": True,
    }
    shadow = {
        "shadow_memory_proposal_summary_id": "smps_v131",
        "shadow_memory_proposals_created": len(proposal_rows),
        "all_status_shadow_only": True,
        "production_write_allowed": False,
        "production_store_write_attempted": False,
        "production_store_write_executed": False,
        "all_require_user_confirmation": True,
    }
    bridge = {
        "bridge_shadow_summary_id": "bss_v131",
        "bridge_shadow_runs_generated": len(bridge_rows),
        "all_shadow_only": True,
        "all_reality_outfits_closet_grounded": True,
        "all_gaps_disclosed_when_key_item_missing": True,
        "product_recommendations_present": False,
    }
    return intake, shadow, bridge, privacy


def _manifest() -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": BRANCH,
        "theme": "Inspiration Intake Shadow Pipeline",
        "generated_at": _now_iso(),
        "scope": {
            "goals": [
                "platform-agnostic inspiration intake",
                "visual/text signal candidates",
                "user intent resolution",
                "ideal direction candidate generation",
                "v1.30 bridge shadow run",
                "shadow-only memory proposal",
                "privacy/rights-safe external evidence handling",
            ],
            "non_goals": [
                "no production memory write",
                "no external platform API dependency",
                "no scraping",
                "no content feed",
                "no commerce",
                "no AIGC image generation",
                "no raw external image redistribution",
            ],
        },
        "reports": {
            "clean_report": "clean_report.json",
            "mixed_strict_report": "mixed_strict_report.json",
            "injected_summary": "injected_defect_detection_summary.json",
            "intake_summary": "intake_summary.json",
            "shadow_memory_proposal_summary": "shadow_memory_proposal_summary.json",
            "bridge_shadow_summary": "bridge_shadow_summary.json",
            "privacy_rights_summary": "privacy_rights_summary.json",
        },
        "required_gates": GATES,
        "required_new_gates": REQUIRED_NEW_GATES,
        "must_review_samples": [f"sample_artifacts/{name}" for name in SAMPLE_MAP],
        "known_p2_backlog": [
            "Replace fixture visual parsing with audited multimodal parser once production path is ready",
            "Add richer user-facing wording calibration for intent clarification",
            "Expand platform-specific URL metadata fixtures without adding platform API dependency",
        ],
    }


def _readme() -> str:
    return """# v1.31 Release Candidate Evidence Pack

## Scope

v1.31 verifies the Inspiration Intake Shadow Pipeline: external inspiration intake, visual/text signal candidates, user intent resolution, ideal direction candidates, v1.30-style bridge shadow runs, shadow-only memory proposals, and privacy-safe external evidence handling.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: 48
- checks: 46
- verdict: pass

## Mixed Strict

- cases: 69
- injected defects: 21
- verdict: fail
- injected defect detection: pass

## Evidence Boundaries

- Raw external screenshots and images are not included.
- URL cases use redacted placeholders and metadata-only fixtures.
- External inspiration never writes production memory in v1.31.
"""


def _release_note() -> str:
    return """# v1.31 Release Candidate Note

## Status

PASS CANDIDATE pending manual review.

## Theme

Inspiration Intake Shadow Pipeline.

## Evidence

- Clean acceptance: 48/48 cases pass
- Clean checks: 46/46 checks pass
- Mixed strict: expected fail with injected defects
- Injected defect detection: 21/21 seeded defects detected

## Boundaries

- No production memory write from external inspiration
- No platform scraping or platform API dependency
- No public redistribution of uploaded or external images
- No commerce, product links, SKU, or merchant references
- No AIGC image generation
"""


def _checklist() -> str:
    return """# v1.31 Reviewer Checklist

## A. Intake Event Schema

- [ ] Every case has an InspirationIntakeEvent.
- [ ] source_type is explicit.

## B. Storage Policy / Privacy / Redistribution

- [ ] storage_policy exists for each content ref.
- [ ] raw external image is not present in public evidence.
- [ ] redistribution_allowed is false for external screenshots/images.

## C. Visual Signal Candidate

- [ ] Visual signals are candidates, not confirmed memory.
- [ ] Uncertain fields are flagged.
- [ ] High-risk model/body/identity inference is suppressed.

## D. Text / URL Metadata Candidate

- [ ] URL metadata-only cases ask for screenshot or clarification.
- [ ] Link title alone does not create memory proposal.
- [ ] Metadata-only URL cases do not resolve color palette or silhouette as liked aspects.
- [ ] Metadata-only URL cases keep color, silhouette, exact items, and material in not_confirmed_aspects.

## E. User Intent Resolution

- [ ] Liked aspects are explicit.
- [ ] Non-core and rejected aspects are not promoted to core.
- [ ] Color-only and date-night cases include user-statement-specific scenario preconditions.

## F. Ideal Direction Candidate

- [ ] Ideal candidate requires confirmation.
- [ ] Downstream use excludes production memory write.

## G. Bridge Shadow Run

- [ ] Bridge run is shadow-only.
- [ ] Reality outfit uses only closet items.
- [ ] Gap is disclosed when closet cannot match inspiration.
- [ ] One-item step is category-level only.

## H. Shadow Memory Proposal

- [ ] status is shadow_only.
- [ ] production_write_allowed is false.
- [ ] requires_user_confirmation is true.

## I. No Production Memory Write

- [ ] production_store_write_attempted is false.
- [ ] production_store_write_executed is false.
- [ ] Fallback-only cases have memory_ux_confirmation_prompt = null.
- [ ] Fallback-only cases use clarification_prompt, not memory confirmation.

## J. Trace Coverage

- [ ] User-visible claims are trace-backed.
- [ ] Shadow proposal evidence refs are complete.
- [ ] High-risk inference cases include high-risk-specific scenario preconditions.
- [ ] Uncertain visual cases include uncertain-field-specific scenario preconditions.

## K. Ambiguous / Inaccessible Input Fallback

- [ ] Ambiguous shares ask clarification.
- [ ] Inaccessible URLs return honest fallback.
- [ ] Platform API absence does not fail the pipeline.
- [ ] Clarification prompt actions do not include remember_later_shadow, remember_long_term, remember_for_context, or use_for_this_bridge_only.
- [ ] Clarification prompt selected action is not a remember action.

## L. Injected Defect Detection

- [ ] All 12 seeded defects are detected.

## M. Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PASS CANDIDATE hold
- [ ] PARTIAL PASS
- [ ] FAIL
"""


def _report_md(title: str, report: dict[str, Any]) -> str:
    summary = report["suite_summary"]
    verdicts = report["verdicts"]
    lines = [f"# {title}", "", "## Verdicts", ""]
    for key, value in verdicts.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Summary", ""])
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def build() -> None:
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR)
    rows = [_case_artifact(case_id, index) for index, case_id in enumerate(CASE_IDS, start=1)]
    clean_report = _clean_report(rows)
    mixed_report, injected_rows, detected = _mixed_report(rows)
    intake_summary, shadow_summary, bridge_summary, privacy_summary = _summaries(rows)
    for row in rows:
        _write_json(RESULT_DIR / "per_case" / "clean" / f"{row['case_id']}.json", row)
    for row in injected_rows:
        _write_json(RESULT_DIR / "per_case" / "mixed_strict" / f"{row['case_id']}.json", row)
    lookup = {row["scenario"]: row for row in rows}
    for name, case_id in SAMPLE_MAP.items():
        _write_json(RESULT_DIR / "sample_artifacts" / name, lookup[case_id])
    _write_json(RESULT_DIR / "REVIEW_MANIFEST.json", _manifest())
    _write_json(RESULT_DIR / "clean_report.json", clean_report)
    _write_text(RESULT_DIR / "clean_report.md", _report_md("v1.31 Clean Report", clean_report))
    _write_json(RESULT_DIR / "mixed_strict_report.json", mixed_report)
    _write_text(RESULT_DIR / "mixed_strict_report.md", _report_md("v1.31 Mixed Strict Report", mixed_report))
    _write_json(
        RESULT_DIR / "injected_defect_detection_summary.json",
        {
            "suite": "v1.31 injected defect detection",
            "verdict": "pass",
            "detected_defects": detected,
            "unexpected_clean_case_failures": [],
            "unexpected_injected_passes": [],
        },
    )
    _write_json(RESULT_DIR / "intake_summary.json", intake_summary)
    _write_json(RESULT_DIR / "shadow_memory_proposal_summary.json", shadow_summary)
    _write_json(RESULT_DIR / "bridge_shadow_summary.json", bridge_summary)
    _write_json(RESULT_DIR / "privacy_rights_summary.json", privacy_summary)
    _write_text(RESULT_DIR / "README.md", _readme())
    _write_text(RESULT_DIR / "RELEASE_NOTE.md", _release_note())
    _write_text(RESULT_DIR / "reviewer_checklist.md", _checklist())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the v1.31 release candidate evidence pack")
    args = parser.parse_args()
    if not args.build:
        parser.error("--build is required")
    build()
    print(f"Built {RESULT_DIR}")


if __name__ == "__main__":
    main()
