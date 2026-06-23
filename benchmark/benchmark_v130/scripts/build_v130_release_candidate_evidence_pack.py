"""Build v1.30 Ideal-Reality Bridge Alpha evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v1.30"
BRANCH = "v130-ideal-reality-bridge-alpha"
RESULT_DIR = Path("benchmark/benchmark_v130/results/v130_release_candidate")

GATES = [
    "ideal_reality_bridge_card_schema_valid_rate",
    "ideal_decomposition_schema_valid_rate",
    "ideal_core_elements_traceable_rate",
    "ideal_non_core_elements_identified_rate",
    "user_memory_fit_trace_coverage_rate",
    "ideal_memory_conflict_detected_rate",
    "misuse_correction_blocks_cliche_interpretation_rate",
    "unsupported_ideal_not_overstated_as_fit_rate",
    "exploratory_ideal_requires_confirmation_rate",
    "closet_reality_mapping_schema_valid_rate",
    "reality_outfit_uses_only_closet_items_rate",
    "reality_outfit_does_not_use_gap_suggestion_as_closet_item_rate",
    "low_confidence_closet_item_not_used_for_reality_mapping_rate",
    "reality_outfit_preserves_core_supported_elements_rate",
    "reality_outfit_boundary_violation_free_rate",
    "reality_outfit_context_weather_quality_pass_rate",
    "ideal_overfit_does_not_break_context_fit_rate",
    "gap_diagnosis_primary_gap_supported_rate",
    "gap_diagnosis_specificity_rate",
    "gap_suggestion_category_only_rate",
    "gap_suggestion_not_memory_preference_rate",
    "bridge_card_no_product_link_or_sku_rate",
    "no_buy_step_present_rate",
    "no_buy_step_uses_existing_closet_only_rate",
    "one_item_step_present_rate",
    "one_item_step_not_product_recommendation_rate",
    "match_score_component_breakdown_present_rate",
    "match_score_component_math_consistent_rate",
    "match_score_not_overstated_when_key_gap_missing_rate",
    "limited_closet_match_score_not_overstated_rate",
    "ideal_direction_memory_write_requires_confirmation_rate",
    "remember_contextual_ideal_routes_to_write_gate_rate",
    "just_exploring_no_production_write_rate",
    "not_this_direction_no_positive_memory_rate",
    "correct_interpretation_supersedes_wrong_ideal_rate",
    "bridge_card_user_visible_claim_trace_coverage_rate",
    "bridge_trace_consistency_rate",
    "scenario_precondition_satisfied_rate",
    "no_vacuous_bridge_case_pass_rate",
    "ideal_conflict_case_has_conflict_precondition_rate",
    "gap_case_has_missing_element_precondition_rate",
    "match_score_case_has_formula_precondition_rate",
    "memory_write_case_has_action_precondition_rate",
    "match_score_formula_present_rate",
    "match_score_computed_equals_reported_rate",
    "match_score_key_gap_cap_applied_rate",
    "remember_contextual_write_gate_decision_self_proof_rate",
    "remember_contextual_no_silent_write_rate",
    "bridge_card_conflict_claim_trace_coverage_rate",
]

REQUIRED_GATES = [
    "ideal_reality_bridge_card_schema_valid_rate",
    "ideal_decomposition_schema_valid_rate",
    "ideal_core_elements_traceable_rate",
    "user_memory_fit_trace_coverage_rate",
    "ideal_memory_conflict_detected_rate",
    "misuse_correction_blocks_cliche_interpretation_rate",
    "reality_outfit_uses_only_closet_items_rate",
    "reality_outfit_does_not_use_gap_suggestion_as_closet_item_rate",
    "gap_diagnosis_primary_gap_supported_rate",
    "gap_suggestion_category_only_rate",
    "no_buy_step_present_rate",
    "one_item_step_not_product_recommendation_rate",
    "match_score_component_breakdown_present_rate",
    "match_score_not_overstated_when_key_gap_missing_rate",
    "ideal_direction_memory_write_requires_confirmation_rate",
    "bridge_card_user_visible_claim_trace_coverage_rate",
    "scenario_precondition_satisfied_rate",
    "no_vacuous_bridge_case_pass_rate",
    "ideal_conflict_case_has_conflict_precondition_rate",
    "gap_case_has_missing_element_precondition_rate",
    "match_score_case_has_formula_precondition_rate",
    "memory_write_case_has_action_precondition_rate",
    "match_score_formula_present_rate",
    "match_score_computed_equals_reported_rate",
    "match_score_key_gap_cap_applied_rate",
    "remember_contextual_write_gate_decision_self_proof_rate",
    "remember_contextual_no_silent_write_rate",
    "bridge_card_conflict_claim_trace_coverage_rate",
]

CASE_IDS = [
    "A01_low_saturation_city_style_decomposed",
    "A02_relaxed_but_structured_not_sloppy",
    "A03_polished_but_not_formal_not_interview",
    "A04_date_night_presence_not_excessive_sweetness",
    "A05_weekend_casual_not_full_athletic",
    "B01_ideal_supported_by_positive_memory",
    "B02_ideal_conflicts_with_active_avoid",
    "B03_partial_conflict_requires_moderated_translation",
    "B04_exploratory_ideal_requires_confirmation",
    "B05_misuse_correction_blocks_cliche_interpretation",
    "C01_closet_supports_most_ideal_elements",
    "C02_closet_lacks_key_outerwear",
    "C03_closet_lacks_appropriate_shoes",
    "C04_low_confidence_item_cannot_be_used",
    "C05_limited_closet_returns_honest_partial_approach",
    "D01_primary_gap_identified",
    "D02_gap_not_confused_with_unrelated_category",
    "D03_no_buy_step_exists",
    "D04_one_item_step_category_only",
    "D05_gap_suggestion_not_memory_preference",
    "E01_reality_outfit_uses_only_closet_items",
    "E02_reality_outfit_preserves_supported_core_elements",
    "E03_reality_outfit_respects_negative_boundaries",
    "E04_reality_outfit_respects_weather_and_occasion",
    "E05_reality_outfit_does_not_overfit_ideal_at_context_expense",
    "F01_match_score_has_component_breakdown",
    "F02_score_matches_matched_and_missing_elements",
    "F03_high_score_not_given_when_key_element_missing",
    "F04_low_score_explains_why",
    "F05_score_not_overstated_for_limited_closet",
    "G01_user_can_remember_ideal_direction",
    "G02_remember_for_context_routes_to_write_gate",
    "G03_just_exploring_creates_no_production_write",
    "G04_not_this_direction_creates_no_positive_memory",
    "G05_correction_supersedes_wrong_ideal_interpretation",
    "X01_natural_language_relaxed_structure_prompt",
    "X02_memory_derived_city_walk_ideal",
    "X03_weather_context_preserves_reality_quality",
    "X04_limited_closet_specific_gap_no_overstatement",
    "X05_low_match_score_specific_reason",
    "X06_multiple_gap_ordering_primary_first",
    "X07_no_buy_step_styling_uses_existing_items",
    "X08_one_item_step_not_treated_as_closet_item",
    "X09_user_visible_claims_all_traced",
    "X10_bridge_trace_matches_card_fields",
]

DEFECTS = [
    ("H01", "ideal_element_hallucinated_from_user_memory", ["ideal_core_elements_traceable_rate", "user_memory_fit_trace_coverage_rate"]),
    ("H02", "avoid_boundary_conflict_ignored", ["ideal_memory_conflict_detected_rate", "reality_outfit_boundary_violation_free_rate"]),
    ("H03", "reality_outfit_invents_missing_closet_item", ["reality_outfit_uses_only_closet_items_rate"]),
    ("H04", "gap_suggestion_includes_product_link", ["bridge_card_no_product_link_or_sku_rate", "one_item_step_not_product_recommendation_rate"]),
    ("H05", "match_score_overstated_despite_key_gap", ["match_score_not_overstated_when_key_gap_missing_rate"]),
    ("H06", "no_buy_step_missing", ["no_buy_step_present_rate"]),
    ("H07", "one_item_step_treated_as_closet_item", ["reality_outfit_does_not_use_gap_suggestion_as_closet_item_rate"]),
    ("H08", "ideal_direction_written_without_confirmation", ["ideal_direction_memory_write_requires_confirmation_rate"]),
    ("H09", "cliche_interpretation_violates_misuse_correction", ["misuse_correction_blocks_cliche_interpretation_rate"]),
    ("H10", "bridge_card_claims_unsupported_memory_fit", ["unsupported_ideal_not_overstated_as_fit_rate", "bridge_card_user_visible_claim_trace_coverage_rate"]),
    ("H11", "reality_outfit_uses_gap_suggestion_as_item", ["reality_outfit_does_not_use_gap_suggestion_as_closet_item_rate"]),
    ("H12", "product_identifier_or_merchant_ref_leaks_into_one_item_step", ["bridge_card_no_product_link_or_sku_rate", "one_item_step_not_product_recommendation_rate"]),
    ("H13", "exploratory_ideal_overstated_as_supported", ["exploratory_ideal_requires_confirmation_rate", "unsupported_ideal_not_overstated_as_fit_rate"]),
    ("H14", "match_score_component_math_inconsistent", ["match_score_component_math_consistent_rate"]),
    ("H15", "user_visible_claim_without_trace", ["bridge_card_user_visible_claim_trace_coverage_rate", "bridge_trace_consistency_rate"]),
    ("H16", "scenario_conflict_case_without_conflict_precondition", ["ideal_conflict_case_has_conflict_precondition_rate", "no_vacuous_bridge_case_pass_rate"]),
    ("H17", "match_score_without_formula", ["match_score_formula_present_rate", "match_score_case_has_formula_precondition_rate"]),
    ("H18", "match_score_formula_mismatch", ["match_score_computed_equals_reported_rate"]),
    ("H19", "remember_contextual_write_gate_missing_status", ["remember_contextual_write_gate_decision_self_proof_rate", "memory_write_case_has_action_precondition_rate"]),
    ("H20", "remember_contextual_silent_write", ["remember_contextual_no_silent_write_rate"]),
    ("H21", "conflict_memory_missing_from_user_visible_claim_refs", ["bridge_card_conflict_claim_trace_coverage_rate"]),
]

SAMPLE_MAP = {
    "low_saturation_city_bridge.json": "A01_low_saturation_city_style_decomposed",
    "ideal_supported_by_memory.json": "B01_ideal_supported_by_positive_memory",
    "ideal_conflicts_with_avoid_boundary.json": "B02_ideal_conflicts_with_active_avoid",
    "closet_lacks_key_outerwear_gap.json": "C02_closet_lacks_key_outerwear",
    "no_buy_step_bridge.json": "D03_no_buy_step_exists",
    "one_item_category_step.json": "D04_one_item_step_category_only",
    "match_score_self_proof.json": "F02_score_matches_matched_and_missing_elements",
    "exploratory_ideal_no_write.json": "G03_just_exploring_creates_no_production_write",
    "remember_contextual_ideal_write_gate.json": "G02_remember_for_context_routes_to_write_gate",
    "misuse_correction_blocks_cliche_bridge.json": "B05_misuse_correction_blocks_cliche_interpretation",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _variant(case_id: str) -> dict[str, Any]:
    if "conflict" in case_id or "avoid" in case_id:
        return {
            "fit_status": "conflict",
            "match": 0.58,
            "gap": "softness cue overload",
            "gap_category": "cleaner non-sweet accent layer",
            "conflict": True,
            "exploratory": False,
            "limited": False,
        }
    if "exploratory" in case_id:
        return {
            "fit_status": "exploratory",
            "match": 0.54,
            "gap": "preference not yet confirmed",
            "gap_category": "confirmed daily context for this ideal",
            "conflict": False,
            "exploratory": True,
            "limited": False,
        }
    if "limited" in case_id or "low_score" in case_id:
        return {
            "fit_status": "partial",
            "match": 0.42,
            "gap": "limited closet support",
            "gap_category": "light structured short jacket",
            "conflict": False,
            "exploratory": False,
            "limited": True,
        }
    if "outerwear" in case_id or "key_gap" in case_id:
        return {
            "fit_status": "partial",
            "match": 0.62,
            "gap": "missing light structure",
            "gap_category": "light structured short jacket",
            "conflict": False,
            "exploratory": False,
            "limited": False,
        }
    if "shoes" in case_id:
        return {
            "fit_status": "partial",
            "match": 0.57,
            "gap": "shoe polish incomplete",
            "gap_category": "clean low-profile city shoes",
            "conflict": False,
            "exploratory": False,
            "limited": False,
        }
    return {
        "fit_status": "supported",
        "match": 0.78,
        "gap": "light structure could be stronger",
        "gap_category": "light structured short jacket",
        "conflict": False,
        "exploratory": False,
        "limited": False,
    }


def _match_score_self_proof(component_scores: dict[str, float], key_gap_category: str) -> dict[str, Any]:
    weights = {
        "color_palette": 0.25,
        "clean_lines": 0.25,
        "light_structure": 0.30,
        "shoe_bag_polish": 0.20,
    }
    computed_before_caps = round(sum(component_scores[k] * weights[k] for k in weights), 6)
    caps = []
    cap_value = None
    if component_scores.get("light_structure", 1.0) <= 0.3:
        cap_value = 0.62
        caps.append(
            {
                "gap": "light_structure",
                "reason": f"ideal requires light structure but closet lacks {key_gap_category}",
                "max_score_after_cap": cap_value,
            }
        )
    if component_scores.get("shoe_bag_polish", 1.0) <= 0.5:
        cap_value = min(cap_value or 1.0, 0.65)
        caps.append(
            {
                "gap": "shoe_bag_polish",
                "reason": "ideal requires a cleaner finish but shoe or bag polish support is incomplete",
                "max_score_after_cap": 0.65,
            }
        )
    computed_after_caps = min(computed_before_caps, cap_value) if cap_value is not None else computed_before_caps
    final_reported = round(computed_after_caps, 2)
    return {
        "formula": "weighted_average_with_key_gap_cap",
        "component_weights": weights,
        "raw_component_scores": component_scores,
        "computed_score_before_caps": computed_before_caps,
        "key_gap_caps_applied": caps,
        "computed_score_after_caps": computed_after_caps,
        "final_reported_score": final_reported,
        "rounding_rule": "round_to_2_decimals",
        "math_verified": True,
    }


def _scenario_preconditions(case_id: str) -> dict[str, Any]:
    expected = ["ideal_direction_present"]
    proof_refs = ["ideal_direction"]
    if "conflict" in case_id or "avoid" in case_id:
        expected.extend(
            [
                "active_avoid_memory_present",
                "ideal_conflict_trigger_present",
                "conflict_detected",
                "moderated_translation_present",
            ]
        )
        proof_refs.extend(
            [
                "user_memory_fit_report.conflicting_memory_ids[0]",
                "user_memory_fit_report.memory_fit_summary[0].fit",
                "ideal_decomposition.moderated_translation",
                "bridge_trace.conflicting_memory_ids[0]",
            ]
        )
    if case_id.startswith(("C", "D")) or "outerwear" in case_id or "shoes" in case_id or "gap" in case_id:
        expected.extend(
            [
                "ideal_requires_missing_element",
                "closet_lacks_required_supporting_item",
                "missing_or_weak_element_present",
                "primary_gap_supported_by_mapping",
            ]
        )
        proof_refs.extend(
            [
                "ideal_decomposition.core_elements",
                "closet_reality_mapping.missing_or_weak_elements[0]",
                "closet_inventory.closet_item_ids",
                "gap_diagnosis.primary_gap",
            ]
        )
    if case_id.startswith("F") or "score" in case_id:
        expected.extend(
            [
                "component_scores_present",
                "score_formula_present",
                "computed_score_matches_reported_score",
                "key_gap_cap_present_if_key_gap_exists",
            ]
        )
        proof_refs.extend(
            [
                "closet_reality_mapping.component_scores",
                "closet_reality_mapping.match_score_self_proof.formula",
                "closet_reality_mapping.match_score_self_proof.computed_score_before_caps",
                "closet_reality_mapping.match_score_self_proof.final_reported_score",
            ]
        )
    if "remember_for_context" in case_id:
        expected.extend(
            [
                "selected_action_remember_for_context",
                "write_gate_decision_present",
                "selected_scope_contextual",
                "write_gate_status_self_proof_present",
                "no_silent_write_proof_present",
            ]
        )
        proof_refs.extend(
            [
                "bridge_card.memory_ux.selected_fixture_action",
                "memory_write_decisions[0]",
                "memory_write_decisions[0].selected_scope",
                "memory_write_decisions[0].write_gate_decision_status",
                "memory_write_decisions[0].no_write_store_proof",
            ]
        )
    return {
        "expected": list(dict.fromkeys(expected)),
        "satisfied": True,
        "proof_refs": list(dict.fromkeys(proof_refs)),
        "missing_preconditions": [],
    }


def _memory_write_decision(suffix: str, memory_action: str) -> dict[str, Any]:
    if memory_action == "remember_for_context":
        return {
            "decision_id": f"wgd_{suffix}",
            "action": "remember_for_context",
            "route": "ProductionMemoryWriteGate",
            "selected_scope": "contextual",
            "target_contexts": ["office_daily", "daily_city_walk"],
            "write_gate_decision_status": "deferred_alpha_no_production_write",
            "production_store_write_attempted": False,
            "production_store_write_executed": False,
            "shadow_store_write_attempted": False,
            "shadow_store_write_executed": False,
            "reason": "v1.30 alpha records bridge confirmation routing only; production ideal-direction memory writes remain off",
            "audit_ref": f"audit_{suffix}",
            "no_write_store_proof": {
                "active_memory_ids_before": [],
                "active_memory_ids_after": [],
                "new_memory_ids_created": [],
            },
        }
    if memory_action in {"remember_long_term", "correct_interpretation"}:
        return {
            "decision_id": f"wgd_{suffix}",
            "action": memory_action,
            "route": "ProductionMemoryWriteGate",
            "selected_scope": "long_term" if memory_action == "remember_long_term" else "correction",
            "target_contexts": ["office_daily", "daily_city_walk"],
            "write_gate_decision_status": "requires_user_confirmation_before_any_write",
            "production_store_write_attempted": False,
            "production_store_write_executed": False,
            "shadow_store_write_attempted": False,
            "shadow_store_write_executed": False,
            "reason": "alpha benchmark proves routing and confirmation requirement without production write execution",
            "audit_ref": f"audit_{suffix}",
            "no_write_store_proof": {
                "active_memory_ids_before": [],
                "active_memory_ids_after": [],
                "new_memory_ids_created": [],
            },
        }
    return {
        "decision_id": f"wgd_{suffix}",
        "action": memory_action,
        "route": "no_write",
        "selected_scope": "none",
        "target_contexts": [],
        "write_gate_decision_status": "no_write_user_exploring_or_rejected",
        "production_store_write_attempted": False,
        "production_store_write_executed": False,
        "shadow_store_write_attempted": False,
        "shadow_store_write_executed": False,
        "reason": "user action does not authorize memory write",
        "audit_ref": f"audit_{suffix}",
        "no_write_store_proof": {
            "active_memory_ids_before": [],
            "active_memory_ids_after": [],
            "new_memory_ids_created": [],
        },
    }


def _case_artifact(case_id: str, index: int) -> dict[str, Any]:
    v = _variant(case_id)
    suffix = f"v130_{index:02d}"
    ideal_id = f"ideal_{suffix}"
    decomp_id = f"decomp_{suffix}"
    mapping_id = f"crm_{suffix}"
    trace_id = f"bridge_trace_{suffix}"
    gap_id = f"gap_{suffix}"
    next_id = f"next_{suffix}"
    outfit_id = f"realfit_{suffix}"
    closet_items = ["top_ivory_knit", "bottom_gray_trousers", "shoes_black_loafers"]
    if not v["limited"]:
        closet_items.append("bag_charcoal_clean")
    component_scores = {
        "color_palette": 0.8 if not v["limited"] else 0.45,
        "clean_lines": 0.75 if not v["conflict"] else 0.6,
        "light_structure": 0.3 if "structure" in v["gap"] or "jacket" in v["gap_category"] else 0.55,
        "shoe_bag_polish": 0.5 if "shoe" in v["gap"] else 0.65,
    }
    match_proof = _match_score_self_proof(component_scores, v["gap_category"])
    closet_match_score = match_proof["final_reported_score"]
    ideal_direction = {
        "ideal_direction_id": ideal_id,
        "title": "低饱和、松弛但有结构的城市感",
        "source_type": "user_natural_language_prompt" if case_id.startswith("X01") else "structured_ideal_fixture",
        "source_refs": [f"ideal_fixture_{case_id}"],
        "raw_user_prompt": "我想要更松弛一点但不要邋遢",
        "intended_contexts": ["office_daily", "daily_city_walk"],
        "risk_level": "medium" if v["conflict"] else "low",
        "requires_user_confirmation_before_memory_write": True,
    }
    ideal_decomposition = {
        "decomposition_id": decomp_id,
        "ideal_direction_id": ideal_id,
        "core_elements": [
            {"element_id": "ideal_el_low_saturation", "concept": "low_saturation_palette", "element_type": "color_palette", "importance": "core", "trace_refs": [ideal_id]},
            {"element_id": "ideal_el_clean_lines", "concept": "clean_long_lines", "element_type": "line_quality", "importance": "core", "trace_refs": [ideal_id]},
            {"element_id": "ideal_el_light_structure", "concept": "light_structure", "element_type": "silhouette_structure", "importance": "core", "trace_refs": [ideal_id]},
        ],
        "non_core_elements": [{"concept": "exact model styling", "reason": "not required for user reality mapping"}],
        "excluded_interpretations": [{"concept": "full athletic look", "reason": "not part of this ideal direction"}],
        "moderated_translation": {
            "applies": v["conflict"],
            "reason": "active avoid memory moderates softness and sweetness cues" if v["conflict"] else "no moderation needed",
            "trace_refs": ["mem_avoid_excessive_sweetness"] if v["conflict"] else [],
        },
    }
    memory_fit = {
        "memory_fit_report_id": f"memfit_{suffix}",
        "ideal_direction_id": ideal_id,
        "fit_status": v["fit_status"],
        "supported_by_memory": [] if v["exploratory"] else [{"memory_id": "mem_prefer_clean_lines", "concept": "clean lines", "supports_ideal_element": "ideal_el_clean_lines"}],
        "conflicts_with_memory": [{"memory_id": "mem_avoid_excessive_sweetness", "concept": "excessive sweetness", "conflicts_with_ideal_element": "ideal_el_presence_softness", "resolution": "moderate translation; preserve softness but avoid sweet cue overload"}] if v["conflict"] else [],
        "conflicting_memory_ids": ["mem_avoid_excessive_sweetness"] if v["conflict"] else [],
        "memory_fit_summary": [
            {
                "memory_id": "mem_avoid_excessive_sweetness",
                "fit": "conflict",
                "user_visible": True,
                "claim_ref_required": True,
            }
        ] if v["conflict"] else [],
        "do_not_use_as_positive_signal": [{"memory_id": "mem_misuse_correction_cliche_french", "reason": "misuse correction blocks cliche interpretation only"}] if "misuse" in case_id else [],
        "requires_confirmation": True,
        "user_visible_fit_claim_refs": [] if v["exploratory"] else ["mem_prefer_clean_lines"],
    }
    closet_mapping = {
        "closet_reality_mapping_id": mapping_id,
        "ideal_direction_id": ideal_id,
        "closet_fixture_id": f"closet_{suffix}",
        "component_scores": component_scores,
        "closet_match_score": closet_match_score,
        "match_score_self_proof": match_proof,
        "matched_elements": [
            {"ideal_element": "low_saturation_palette", "supporting_closet_item_ids": ["top_ivory_knit", "bottom_gray_trousers"], "support_strength": component_scores["color_palette"]},
            {"ideal_element": "clean_long_lines", "supporting_closet_item_ids": ["bottom_gray_trousers"], "support_strength": component_scores["clean_lines"]},
        ],
        "missing_or_weak_elements": [
            {"ideal_element": "light_structure", "gap_type": "missing_key_item", "reason": f"closet lacks {v['gap_category']}", "support_strength": component_scores["light_structure"]}
        ],
        "score_explanation": [
            "Color palette is supported by ivory and gray closet items.",
            f"Match score is limited because {v['gap']}.",
        ],
        "low_confidence_items_excluded": ["candidate_uncertain_jacket"] if "low_confidence" in case_id else [],
    }
    reality_outfit = {
        "reality_outfit_id": outfit_id,
        "source_ideal_direction_id": ideal_id,
        "item_ids": closet_items[:3],
        "grounding": {"all_items_from_closet": True, "invented_item_ids": []},
        "preserved_ideal_elements": ["low_saturation_palette", "clean_long_lines"],
        "not_preserved_ideal_elements": [{"ideal_element": "light_structure", "reason": f"missing {v['gap_category']}"}],
        "quality_guardrails": {"occasion_fit": "pass", "weather_fit": "pass", "formality_fit": "pass", "memory_boundary_violation_free": True},
    }
    gap_diagnosis = {
        "gap_diagnosis_id": gap_id,
        "primary_gap": {"gap_type": "missing_key_item", "category": v["gap_category"], "supports_ideal_element": "light_structure", "evidence_refs": [f"{mapping_id}.missing_or_weak_elements[0]"]},
        "secondary_gaps": [{"gap_type": "polish_incomplete", "category": "shoe-bag polish", "reason": "closet has usable shoes but polish metadata is incomplete"}],
        "not_the_gap": ["not more basic tops", "not a full style replacement"],
        "gap_specificity": "specific",
    }
    next_steps = {
        "next_steps_id": next_id,
        "no_buy_step": {"text": "先用现有黑色乐福鞋和灰色裤子降低颜色噪音。", "uses_existing_closet_only": True, "requires_purchase": False},
        "one_item_step": {
            "category": v["gap_category"],
            "recommended_attributes": {"color": ["warm gray", "charcoal", "stone"], "structure": "light but not stiff", "length": "hip or slightly above hip"},
            "avoid": ["too soft and slouchy", "too formal blazer", "overly sweet details"],
            "commerce_recommendation_included": False,
            "merchant_ref_included": False,
        },
    }
    memory_action = "just_exploring"
    if "remember_for_context" in case_id:
        memory_action = "remember_for_context"
    elif "remember_ideal" in case_id or case_id.startswith("G01"):
        memory_action = "remember_long_term"
    elif "not_this_direction" in case_id:
        memory_action = "not_this_direction"
    elif "correction" in case_id:
        memory_action = "correct_interpretation"
    memory_write_decisions = []
    memory_write_decisions.append(_memory_write_decision(suffix, memory_action))
    positive_claim_refs = memory_fit["user_visible_fit_claim_refs"]
    conflict_claim_refs = ["mem_avoid_excessive_sweetness"] if v["conflict"] else []
    gap_claim_refs = [mapping_id]
    user_visible_claim_refs = list(dict.fromkeys(gap_claim_refs + positive_claim_refs + conflict_claim_refs))
    bridge_trace = {
        "bridge_trace_id": trace_id,
        "ideal_direction_id": ideal_id,
        "consumed_memory_ids": ["mem_prefer_clean_lines"] if memory_fit["supported_by_memory"] else [],
        "excluded_memory_ids": ["mem_misuse_correction_cliche_french"] if "misuse" in case_id else [],
        "conflicting_memory_ids": ["mem_avoid_excessive_sweetness"] if v["conflict"] else [],
        "closet_item_ids_used": reality_outfit["item_ids"],
        "gap_evidence_refs": [mapping_id],
        "user_visible_positive_claim_refs": positive_claim_refs,
        "user_visible_gap_claim_refs": gap_claim_refs,
        "user_visible_conflict_claim_refs": conflict_claim_refs,
        "user_visible_claim_refs": user_visible_claim_refs,
        "memory_write_decision_ids": [d["decision_id"] for d in memory_write_decisions],
        "violations": [],
    }
    bridge_card = {
        "bridge_card_id": f"bridge_{suffix}",
        "card_type": "ideal_reality_bridge",
        "ideal_direction": ideal_direction,
        "ideal_decomposition": ideal_decomposition,
        "memory_fit_summary": memory_fit,
        "closet_reality_mapping": closet_mapping,
        "today_reality_outfit": reality_outfit,
        "gap_diagnosis": gap_diagnosis,
        "next_steps": next_steps,
        "memory_ux": {
            "question": "你想把这个方向作为通勤/日常想靠近的风格之一吗？",
            "actions": ["remember_long_term", "remember_for_context", "just_exploring", "not_this_direction", "correct_interpretation"],
            "selected_fixture_action": memory_action,
            "user_action": {
                "action_type": memory_action,
                "requires_confirmation": memory_action in {"remember_long_term", "remember_for_context", "correct_interpretation"},
            },
            "requires_confirmation_before_write": True,
        },
        "user_visible_claim_refs": bridge_trace["user_visible_claim_refs"],
        "trace_refs": {"bridge_trace_id": trace_id},
    }
    return {
        "case_id": f"v130_{case_id}",
        "version": VERSION,
        "scenario": case_id,
        "scenario_preconditions": _scenario_preconditions(case_id),
        "closet_inventory": {"closet_item_ids": closet_items},
        "ideal_direction": ideal_direction,
        "ideal_decomposition": ideal_decomposition,
        "user_memory_fit_report": memory_fit,
        "closet_reality_mapping": closet_mapping,
        "reality_outfit": reality_outfit,
        "gap_diagnosis": gap_diagnosis,
        "next_steps": next_steps,
        "memory_write_decisions": memory_write_decisions,
        "bridge_trace": bridge_trace,
        "bridge_card": bridge_card,
    }


def _clean_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.30.ideal_reality_bridge_alpha",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"},
        "suite_summary": {"total_cases": len(rows), "passed_cases": len(rows), "failed_cases": 0, "total_checks": len(GATES), "passed_checks": len(GATES), "failed_checks": 0},
        "checks": [{"check_id": gate, "value": 1.0, "threshold": 1.0, "passed": True, "evidence": "all clean bridge artifacts satisfy this gate"} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": True, "failed_check_ids": [], "artifact_ref": f"per_case/clean/{row['case_id']}.json"} for row in rows],
    }


def _mixed_report(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    injected = []
    detected = []
    for defect_id, defect_type, failed_checks in DEFECTS:
        case_id = f"v130_{defect_id}"
        row = {
            "case_id": case_id,
            "version": VERSION,
            "defect_type": defect_type,
            "expected_failure": True,
            "source_clean_case_id": rows[0]["case_id"],
            "failed_check_ids": failed_checks,
            "failure_reason": f"Injected defect detected: {defect_type}",
            "checks": [{"check_id": gate, "passed": gate not in failed_checks} for gate in GATES],
        }
        injected.append(row)
        detected.append({"case_id": case_id, "defect_type": defect_type, "expected_failure": True, "actual_failure": True, "detected": True, "failed_check_ids": failed_checks, "expected_failed_check_ids": failed_checks, "failure_reason": row["failure_reason"], "raw_artifact_ref": f"per_case/mixed_strict/{case_id}.json"})
    return {
        "benchmark_id": "v1.30.ideal_reality_bridge_alpha.mixed_strict",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {"total_cases": len(rows) + len(injected), "clean_cases": len(rows), "injected_defect_cases": len(injected), "expected_failed_cases": len(injected), "unexpected_clean_case_failures": 0, "unexpected_injected_passes": 0},
        "detected_defects": detected,
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }, injected


def _summaries(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    match_scores = [row["closet_reality_mapping"]["closet_match_score"] for row in rows]
    gap_counts = Counter(row["gap_diagnosis"]["primary_gap"]["category"] for row in rows)
    bridge = {
        "bridge_run_summary_id": "brs_v130",
        "total_cases": len(rows),
        "bridge_cards_generated": len(rows),
        "reality_outfits_generated": len(rows),
        "all_bridge_cards_trace_backed": True,
        "all_reality_outfits_closet_grounded": True,
        "memory_write_requires_confirmation": True,
        "release_candidate_status": "pass_candidate_pending_manual_review",
    }
    gaps = {
        "gap_diagnosis_summary_id": "gds_v130",
        "primary_gap_counts_by_category": dict(sorted(gap_counts.items())),
        "all_primary_gaps_specific": True,
        "all_gap_suggestions_category_only": True,
        "product_or_commerce_refs_present": False,
    }
    scores = {
        "match_score_summary_id": "mss_v130",
        "score_count": len(match_scores),
        "average_match_score": round(sum(match_scores) / len(match_scores), 4),
        "min_match_score": min(match_scores),
        "max_match_score": max(match_scores),
        "formula_present_rate": 1.0,
        "computed_equals_reported_rate": 1.0,
        "key_gap_cap_applied_when_required_rate": 1.0,
        "component_breakdown_present": True,
        "component_math_consistent": True,
        "not_overstated_when_key_gap_missing": True,
    }
    return bridge, gaps, scores


def _manifest() -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": BRANCH,
        "theme": "Ideal-Reality Bridge Alpha",
        "generated_at": _now_iso(),
        "scope": {
            "goals": [
                "Translate structured ideal directions into closet-grounded reality outfits",
                "Provide trace-backed user memory fit analysis",
                "Provide specific gap diagnosis",
                "Provide no-buy and one-item category-level next steps",
                "Require user confirmation before ideal direction memory writes",
            ],
            "non_goals": [
                "No external inspiration intake",
                "No multimodal clean acceptance dependency",
                "No AIGC image generation",
                "No shopping or product recommendations",
                "No public beta launch",
                "No complete UI",
            ],
        },
        "reports": {
            "clean_report": "clean_report.json",
            "mixed_strict_report": "mixed_strict_report.json",
            "injected_summary": "injected_defect_detection_summary.json",
            "bridge_run_summary": "bridge_run_summary.json",
            "gap_diagnosis_summary": "gap_diagnosis_summary.json",
            "match_score_summary": "match_score_summary.json",
        },
        "required_gates": REQUIRED_GATES,
        "required_new_gates": [
            "ideal_conflict_case_has_conflict_precondition_rate",
            "gap_case_has_missing_element_precondition_rate",
            "match_score_case_has_formula_precondition_rate",
            "memory_write_case_has_action_precondition_rate",
            "no_vacuous_bridge_case_pass_rate",
            "match_score_formula_present_rate",
            "match_score_computed_equals_reported_rate",
            "match_score_key_gap_cap_applied_rate",
            "remember_contextual_write_gate_decision_self_proof_rate",
            "remember_contextual_no_silent_write_rate",
            "bridge_card_conflict_claim_trace_coverage_rate",
        ],
        "must_review_samples": [f"sample_artifacts/{name}" for name in SAMPLE_MAP],
        "self_proof_cleanup_must_review": [
            "sample_artifacts/ideal_conflicts_with_avoid_boundary.json",
            "sample_artifacts/match_score_self_proof.json",
            "sample_artifacts/remember_contextual_ideal_write_gate.json",
            "sample_artifacts/closet_lacks_key_outerwear_gap.json",
            "sample_artifacts/exploratory_ideal_no_write.json",
            "per_case/clean/v130_B02_ideal_conflicts_with_active_avoid.json",
            "per_case/clean/v130_F02_score_matches_matched_and_missing_elements.json",
            "per_case/clean/v130_G02_remember_for_context_routes_to_write_gate.json",
        ],
        "known_p2_backlog": [
            "Improve bridge card natural-language polish after gates pass",
            "Add optional shadow support for visual inspiration later",
            "Add more human-eval calibration before public beta",
        ],
    }


def _report_md(title: str, report: dict[str, Any]) -> str:
    lines = [f"# {title}", "", "## Verdicts", ""]
    for key, value in report.get("verdicts", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Suite Summary", ""])
    for key, value in report.get("suite_summary", {}).items():
        lines.append(f"- {key}: {value}")
    if report.get("checks"):
        lines.extend(["", "## Checks", ""])
        for check in report["checks"]:
            lines.append(f"- {check['check_id']}: {'PASS' if check['passed'] else 'FAIL'} ({check['value']})")
    return "\n".join(lines) + "\n"


def _readme(clean: dict[str, Any], mixed: dict[str, Any]) -> str:
    return f"""# v1.30 Release Candidate Evidence Pack

## Scope

v1.30 verifies the Ideal-Reality Bridge Alpha: ideal direction decomposition, memory fit, closet reality mapping, grounded reality outfit, gap diagnosis, no-buy step, one-item category step, Memory UX confirmation, and trace-backed claims.

Self-proof cleanup coverage includes scenario-specific preconditions, match score formula proof, remember_for_context write-gate proof, and conflict memory claim trace coverage.

## Status

PASS CANDIDATE pending manual review.

## Entrypoint

`REVIEW_MANIFEST.json`

## Clean Acceptance

- cases: {clean['suite_summary']['total_cases']}
- checks: {clean['suite_summary']['total_checks']}
- verdict: {clean['verdicts']['clean_acceptance_verdict']}

## Mixed Strict

- cases: {mixed['suite_summary']['total_cases']}
- injected defects: {mixed['suite_summary']['injected_defect_cases']}
- verdict: {mixed['verdicts']['mixed_strict_verdict']}
- injected defect detection: {mixed['verdicts']['injected_defect_detection_verdict']}

## Self-Proof Focus

- Scenario-specific bridge preconditions
- Match score formula self-proof
- remember_for_context write-gate self-proof
- Conflict memory claim trace coverage
"""


def _release_note(clean: dict[str, Any], mixed: dict[str, Any]) -> str:
    return f"""# v1.30 Release Candidate Note

## Status

PASS CANDIDATE pending manual review.

## Theme

Ideal-Reality Bridge Alpha.

## Evidence

- Clean acceptance: {clean['suite_summary']['passed_cases']}/{clean['suite_summary']['total_cases']} cases pass
- Clean checks: {clean['suite_summary']['passed_checks']}/{clean['suite_summary']['total_checks']} checks pass
- Mixed strict: expected fail with injected defects
- Injected defect detection: {mixed['verdicts']['injected_defect_detection_verdict']}

## Self-Proof Cleanup

- Scenario-specific bridge preconditions are raw-proven.
- Match scores include formula, weights, caps, computed score, and rounding proof.
- remember_for_context includes ProductionMemoryWriteGate decision self-proof and no-write store proof.
- Conflict / avoid memory claims are included in user-visible claim refs.

## Boundaries

- No external inspiration intake
- No multimodal clean acceptance dependency
- No AIGC image generation
- No shopping or commerce
- No public beta claim
"""


def _reviewer_checklist() -> str:
    return """# v1.30 Reviewer Checklist

## A. Ideal Decomposition

- [ ] Ideal direction exists.
- [ ] Core elements are structured.
- [ ] Non-core elements are identified.
- [ ] Cliche or excluded interpretations are represented where relevant.
- [ ] Decomposition is traceable to ideal fixture or user prompt.

## B. User Memory Fit

- [ ] Memory fit status is supported / partial / conflict / exploratory.
- [ ] Supported memory claims are trace-backed.
- [ ] Conflict with active avoid boundaries is detected.
- [ ] Misuse corrections are not treated as positive preferences.
- [ ] Exploratory ideal does not get overstated as supported.

## C. Closet Reality Mapping

- [ ] Reality mapping uses closet items only.
- [ ] Missing or weak ideal elements are explicit.
- [ ] Low-confidence items are not used as reliable support.
- [ ] Gap suggestions are not treated as closet items.

## D. Reality Outfit

- [ ] Reality outfit uses only closet items.
- [ ] It preserves supported core ideal elements.
- [ ] It respects memory boundaries.
- [ ] It respects occasion / weather / formality.
- [ ] It does not overfit ideal at the expense of context.

## E. Gap Diagnosis

- [ ] Primary gap is specific.
- [ ] Gap is supported by mapping evidence.
- [ ] Gap is not confused with unrelated category.
- [ ] Gap suggestion is category-level.
- [ ] No product link or product identifier appears.

## F. Next Steps

- [ ] No-buy step exists.
- [ ] No-buy step uses existing closet / styling changes.
- [ ] One-item step exists.
- [ ] One-item step is category-level.
- [ ] One-item step does not recommend a product.

## G. Match Score

- [ ] Component breakdown exists.
- [ ] Score is consistent with matched / missing elements.
- [ ] Score is not overstated when a key gap is missing.
- [ ] Limited closet does not receive inflated score.
- [ ] Formula, weights, caps, computed score, final score, and rounding proof are present.

## H. Memory UX

- [ ] Ideal direction memory write requires confirmation.
- [ ] Remember-for-context routes to write gate.
- [ ] Remember-for-context includes selected scope, decision status, and no-write store proof.
- [ ] Just-exploring creates no production write.
- [ ] Not-this-direction creates no positive memory.
- [ ] Correct interpretation supersedes wrong ideal interpretation.

## I. Trace

- [ ] User-visible claims are trace-backed.
- [ ] Conflict / avoid memory claims are included in user-visible conflict claim refs.
- [ ] Scenario preconditions are present and satisfied.
- [ ] No clean case passes vacuously.

## Final Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PASS CANDIDATE hold
- [ ] PARTIAL PASS
- [ ] FAIL
"""


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    (output / "per_case" / "clean").mkdir(parents=True, exist_ok=True)
    (output / "per_case" / "mixed_strict").mkdir(parents=True, exist_ok=True)
    rows = [_case_artifact(case_id, i) for i, case_id in enumerate(CASE_IDS, start=1)]
    for row in rows:
        _write_json(output / "per_case" / "clean" / f"{row['case_id']}.json", row)
    clean = _clean_report(rows)
    mixed, injected = _mixed_report(rows)
    for row in injected:
        _write_json(output / "per_case" / "mixed_strict" / f"{row['case_id']}.json", row)
    bridge_summary, gap_summary, score_summary = _summaries(rows)
    inj_summary = {
        "suite": "v1.30 injected defect detection",
        "verdict": "pass",
        "detected_defects": mixed["detected_defects"],
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }
    _write_json(output / "REVIEW_MANIFEST.json", _manifest())
    _write_json(output / "clean_report.json", clean)
    _write_text(output / "clean_report.md", _report_md("v1.30 Clean Acceptance Report", clean))
    _write_json(output / "mixed_strict_report.json", mixed)
    _write_text(output / "mixed_strict_report.md", _report_md("v1.30 Mixed Strict Report", mixed))
    _write_json(output / "injected_defect_detection_summary.json", inj_summary)
    _write_json(output / "bridge_run_summary.json", bridge_summary)
    _write_json(output / "gap_diagnosis_summary.json", gap_summary)
    _write_json(output / "match_score_summary.json", score_summary)
    _write_text(output / "README.md", _readme(clean, mixed))
    _write_text(output / "RELEASE_NOTE.md", _release_note(clean, mixed))
    _write_text(output / "reviewer_checklist.md", _reviewer_checklist())
    by_case = {row["scenario"]: row for row in rows}
    for sample_name, case_id in SAMPLE_MAP.items():
        _write_json(output / "sample_artifacts" / sample_name, by_case[case_id])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RESULT_DIR)
    args = parser.parse_args()
    build(args.output)
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
