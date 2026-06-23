"""Aggregate v1.29.7 Closet Bootstrapping & Item Reliability reports."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


BENCHMARK_ID = "v1.29.7.closet_bootstrapping_item_reliability"
SCHEMA_VERSION = "v1.29.7"

CHECK_IDS = [
    "closet_bootstrap_profile_schema_valid_rate",
    "closet_readiness_report_present_rate",
    "closet_readiness_before_generation_rate",
    "item_reliability_profile_present_rate",
    "final_outfit_items_exist_in_closet_rate",
    "swap_options_exist_in_closet_rate",
    "gap_suggestions_not_treated_as_closet_items_rate",
    "card_text_no_hallucinated_item_rate",
    "minimum_viable_closet_status_correct_rate",
    "missing_required_category_disclosed_rate",
    "blocking_missing_category_returns_insufficient_rate",
    "non_blocking_gap_returns_pass_with_disclosure_rate",
    "low_confidence_category_not_used_as_required_slot_rate",
    "low_confidence_formality_not_used_for_formal_claim_rate",
    "low_confidence_weather_not_used_for_weather_claim_rate",
    "low_confidence_material_not_claimed_as_fact_rate",
    "uncertain_fields_surface_uncertainty_note_rate",
    "unconfirmed_vision_candidate_not_used_in_clean_planner_rate",
    "low_reliability_item_excluded_from_high_stakes_context_rate",
    "item_reliability_tier_trace_coverage_rate",
    "final_quality_pass_requires_reliability_report_rate",
    "pass_with_disclosure_has_gap_disclosure_rate",
    "insufficient_status_has_blocking_reason_rate",
    "closet_gap_note_no_product_recommendation_rate",
    "reliable_swap_options_visible_rate",
    "unreliable_swap_options_hidden_rate",
    "hidden_swap_options_have_reason_rate",
    "swap_option_uncertain_claim_trace_coverage_rate",
    "memory_preference_does_not_force_unreliable_item_rate",
    "memory_claim_not_based_on_unconfirmed_metadata_rate",
    "current_exception_cannot_override_missing_category_rate",
    "current_exception_requires_item_reliability_support_rate",
    "scenario_precondition_satisfied_rate",
    "scenario_precondition_proof_refs_present_rate",
    "no_vacuous_clean_case_pass_rate",
    "current_exception_case_has_exception_precondition_rate",
    "missing_category_case_has_missing_category_precondition_rate",
    "gap_case_has_gap_disclosure_precondition_rate",
    "gap_suggestion_category_only_rate",
    "swap_case_has_visible_swap_precondition_rate",
    "hidden_swap_case_has_hidden_swap_precondition_rate",
    "repair_case_has_pre_repair_issue_rate",
    "low_confidence_case_has_low_confidence_item_precondition_rate",
    "insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate",
]

THRESHOLDS = {cid: 1.0 for cid in CHECK_IDS}

EXPECTED_DEFECTS = {
    "missing_shoes_hallucinated_item": ["final_outfit_items_exist_in_closet_rate", "card_text_no_hallucinated_item_rate"],
    "missing_top_marked_as_pass": ["blocking_missing_category_returns_insufficient_rate", "insufficient_status_has_blocking_reason_rate"],
    "low_confidence_formality_used_for_client_meeting": ["low_confidence_formality_not_used_for_formal_claim_rate", "low_reliability_item_excluded_from_high_stakes_context_rate"],
    "low_confidence_weather_used_for_rain_claim": ["low_confidence_weather_not_used_for_weather_claim_rate"],
    "low_confidence_category_satisfies_required_slot": ["low_confidence_category_not_used_as_required_slot_rate"],
    "vision_candidate_used_without_confirmation": ["unconfirmed_vision_candidate_not_used_in_clean_planner_rate"],
    "gap_suggestion_treated_as_closet_item": ["gap_suggestions_not_treated_as_closet_items_rate", "final_outfit_items_exist_in_closet_rate"],
    "missing_gap_not_disclosed": ["missing_required_category_disclosed_rate", "pass_with_disclosure_has_gap_disclosure_rate"],
    "product_recommendation_in_gap_note": ["closet_gap_note_no_product_recommendation_rate"],
    "memory_preference_forces_unreliable_item": ["memory_preference_does_not_force_unreliable_item_rate"],
    "swap_option_low_confidence_not_hidden": ["unreliable_swap_options_hidden_rate", "reliable_swap_options_visible_rate"],
    "swap_option_weather_unreliable_visible": ["unreliable_swap_options_hidden_rate", "swap_option_uncertain_claim_trace_coverage_rate"],
    "card_claims_uncertain_material_as_fact": ["low_confidence_material_not_claimed_as_fact_rate"],
    "final_outfit_quality_pass_without_reliability_report": ["final_quality_pass_requires_reliability_report_rate"],
    "closet_readiness_skipped_before_generation": ["closet_readiness_before_generation_rate"],
    "insufficient_closet_still_returns_normal_pass": ["blocking_missing_category_returns_insufficient_rate", "insufficient_status_has_blocking_reason_rate"],
    "scenario_precondition_missing_but_clean_case_passes": ["scenario_precondition_satisfied_rate", "no_vacuous_clean_case_pass_rate"],
    "current_exception_case_without_exception": ["current_exception_case_has_exception_precondition_rate"],
    "missing_category_case_without_missing_category": ["missing_category_case_has_missing_category_precondition_rate"],
    "gap_case_without_gap_disclosure": ["gap_case_has_gap_disclosure_precondition_rate"],
    "swap_case_without_visible_swap": ["swap_case_has_visible_swap_precondition_rate"],
    "hidden_swap_case_without_hidden_swap": ["hidden_swap_case_has_hidden_swap_precondition_rate"],
    "repair_case_without_pre_repair_issue": ["repair_case_has_pre_repair_issue_rate"],
    "insufficient_card_presents_partial_outfit_as_daily_outfit": ["insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rate(n: int, d: int) -> float:
    return round(n / d, 4) if d else 1.0


def _load_raw_dir(path: str) -> list[dict[str, Any]]:
    results = os.path.join(path, "results.json")
    if os.path.exists(results):
        with open(results, encoding="utf-8") as f:
            return json.load(f)
    rows = []
    per_case = os.path.join(path, "per_case")
    for name in sorted(os.listdir(per_case)):
        if name.endswith(".json"):
            with open(os.path.join(per_case, name), encoding="utf-8") as f:
                rows.append(json.load(f))
    return rows


def _closet_ids(row: dict[str, Any]) -> set[str]:
    return {item["item_id"] for item in (row.get("closet_fixture") or {}).get("closet_items", [])}


def _profiles(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["item_id"]: p for p in row.get("item_reliability_profiles") or []}


def _outfit_ids(row: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in ((row.get("final_daily_outfit_card") or {}).get("outfit_items") or []) if item.get("item_id")]


def _swap_ids(row: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in ((row.get("final_daily_outfit_card") or {}).get("swap_options") or []) if item.get("item_id")]


def _card(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("final_daily_outfit_card") or {}


def _readiness(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("closet_readiness_report") or {}


def _scenario(row: dict[str, Any]) -> str:
    return str(row.get("scenario") or "")


def _has_any_token(row: dict[str, Any], tokens: set[str]) -> bool:
    scenario = _scenario(row)
    return any(token in scenario for token in tokens)


def _ref_exists(row: Any, ref: str) -> bool:
    cur = row
    for part in ref.split("."):
        while "[" in part and part.endswith("]"):
            name, raw_index = part[:-1].split("[", 1)
            if name:
                if not isinstance(cur, dict) or name not in cur:
                    return False
                cur = cur[name]
            try:
                index = int(raw_index)
            except ValueError:
                return False
            if not isinstance(cur, list) or index >= len(cur):
                return False
            cur = cur[index]
            part = ""
        if not part:
            continue
        if isinstance(cur, dict):
            if part not in cur:
                return False
            cur = cur[part]
        else:
            return False
    if isinstance(cur, (list, dict)):
        return bool(cur)
    return cur is not None


def _bootstrap_schema(row: dict[str, Any]) -> bool:
    profile = row.get("closet_bootstrap_profile") or {}
    required = {"closet_bootstrap_profile_id", "closet_fixture_id", "source_type", "item_count", "category_counts", "metadata_completeness_score", "minimum_viable_closet_status", "created_at"}
    return required <= set(profile)


def _readiness_present(row: dict[str, Any]) -> bool:
    return bool(row.get("closet_readiness_report"))


def _readiness_before_generation(row: dict[str, Any]) -> bool:
    order = (row.get("trace") or {}).get("pipeline_order") or []
    try:
        return order.index("closet_readiness_report") < order.index("candidate_outfit_generation") and all(c.get("generated_after_readiness_report") for c in row.get("candidate_outfits") or [])
    except ValueError:
        return False


def _profiles_present(row: dict[str, Any]) -> bool:
    return bool(row.get("item_reliability_profiles")) and len(row.get("item_reliability_profiles")) == len((row.get("closet_fixture") or {}).get("closet_items", []))


def _outfit_closet(row: dict[str, Any]) -> bool:
    return set(_outfit_ids(row)) <= _closet_ids(row)


def _swap_closet(row: dict[str, Any]) -> bool:
    return set(_swap_ids(row)) <= _closet_ids(row)


def _gap_not_item(row: dict[str, Any]) -> bool:
    card = _card(row)
    return all(g.get("treated_as_outfit_item") is not True for g in card.get("gap_suggestions") or []) and all(item.get("source") != "closet_gap" for item in card.get("outfit_items") or [])


def _no_hallucinated_text(row: dict[str, Any]) -> bool:
    return set(_card(row).get("mentioned_item_ids") or []) <= _closet_ids(row)


def _mvc_status(row: dict[str, Any]) -> bool:
    boot = row.get("closet_bootstrap_profile") or {}
    readiness = _readiness(row)
    missing = set(readiness.get("missing_required_categories") or [])
    expected = "fail" if missing & {"top", "bottom"} else ("pass_with_gap" if missing else "pass")
    return boot.get("minimum_viable_closet_status") == expected


def _missing_disclosed(row: dict[str, Any]) -> bool:
    missing = set(_readiness(row).get("missing_required_categories") or [])
    disclosed = {cat for d in row.get("missing_category_disclosures") or [] for cat in d.get("missing_categories", [])}
    return not missing or missing <= disclosed


def _blocking_insufficient(row: dict[str, Any]) -> bool:
    blocking = set(_readiness(row).get("missing_required_categories") or []) & {"top", "bottom"}
    if not blocking:
        return True
    return _readiness(row).get("readiness_status") == "insufficient" and _card(row).get("quality_status") == "insufficient"


def _nonblocking_gap_disclosure(row: dict[str, Any]) -> bool:
    missing = set(_readiness(row).get("missing_required_categories") or []) - {"top", "bottom"}
    if not missing:
        return True
    return _card(row).get("quality_status") == "pass_with_disclosure" and bool(row.get("missing_category_disclosures"))


def _low_category_not_used(row: dict[str, Any]) -> bool:
    profiles = _profiles(row)
    return all(profiles.get(item_id, {}).get("field_confidence", {}).get("category", 1.0) >= 0.85 for item_id in _outfit_ids(row) if item_id in profiles)


def _low_formality_no_claim(row: dict[str, Any]) -> bool:
    if (row.get("task_context") or {}).get("occasion") != "formal_client_meeting":
        return True
    profiles = _profiles(row)
    if any(profiles.get(item_id, {}).get("field_confidence", {}).get("formality", 1.0) < 0.80 for item_id in _outfit_ids(row)):
        return False
    return all("low_confidence_formality" != why.get("claim_ref") for why in _card(row).get("why_this_works") or [])


def _low_weather_no_claim(row: dict[str, Any]) -> bool:
    if not ((row.get("task_context") or {}).get("weather") or {}).get("rain"):
        return True
    return all("low_confidence_weather" != why.get("claim_ref") for why in _card(row).get("why_this_works") or [])


def _low_material_no_fact(row: dict[str, Any]) -> bool:
    return all("low_confidence_material" != why.get("claim_ref") for why in _card(row).get("why_this_works") or [])


def _uncertain_note(row: dict[str, Any]) -> bool:
    has_uncertain = any(p.get("uncertain_fields") for p in row.get("item_reliability_profiles") or [])
    return not has_uncertain or bool(_card(row).get("uncertainty_notes")) or not _outfit_ids(row)


def _vision_not_used(row: dict[str, Any]) -> bool:
    profiles = _profiles(row)
    return not any(profiles.get(item_id, {}).get("metadata_source") == "vision_candidate" for item_id in _outfit_ids(row)) and (row.get("trace") or {}).get("vision_candidate_used_without_confirmation") is not True


def _low_reliability_excluded_high_stakes(row: dict[str, Any]) -> bool:
    if (row.get("task_context") or {}).get("occasion") != "formal_client_meeting":
        return True
    profiles = _profiles(row)
    return not any(profiles.get(item_id, {}).get("reliability_tier") == "low" for item_id in _outfit_ids(row))


def _tier_trace(row: dict[str, Any]) -> bool:
    refs = set((row.get("trace") or {}).get("item_reliability_profile_refs") or [])
    return set(_profiles(row)) <= refs


def _quality_requires_reliability(row: dict[str, Any]) -> bool:
    status = (row.get("quality_report") or {}).get("final_quality_status")
    return status not in {"pass", "pass_with_disclosure"} or bool(row.get("reliability_report"))


def _pass_with_disclosure_has_gap(row: dict[str, Any]) -> bool:
    return _card(row).get("quality_status") != "pass_with_disclosure" or bool(row.get("missing_category_disclosures"))


def _insufficient_blocking(row: dict[str, Any]) -> bool:
    return _card(row).get("quality_status") != "insufficient" or bool(set(_readiness(row).get("missing_required_categories") or []) & {"top", "bottom"})


def _no_product_gap(row: dict[str, Any]) -> bool:
    card = _card(row)
    if card.get("product_recommendation_included") is True:
        return False
    return all(note.get("product_recommendation_included") is not True for note in card.get("closet_gap_notes") or [])


def _reliable_swaps(row: dict[str, Any]) -> bool:
    profiles = _profiles(row)
    return all(profiles.get(item_id, {}).get("reliability_tier") != "low" for item_id in _swap_ids(row) if item_id in profiles)


def _unreliable_swaps_hidden(row: dict[str, Any]) -> bool:
    profiles = _profiles(row)
    hidden = {item.get("item_id") for item in (row.get("swap_option_reliability_report") or {}).get("hidden_swap_options", [])}
    visible_low = {item_id for item_id in _swap_ids(row) if profiles.get(item_id, {}).get("reliability_tier") == "low"}
    return not visible_low and all(item_id in hidden or profiles[item_id].get("metadata_source") != "vision_candidate" for item_id in profiles if profiles[item_id].get("reliability_tier") == "low")


def _hidden_reasons(row: dict[str, Any]) -> bool:
    return all(item.get("hidden_reason") for item in (row.get("swap_option_reliability_report") or {}).get("hidden_swap_options", []))


def _swap_claim_trace(row: dict[str, Any]) -> bool:
    refs = set((row.get("swap_option_reliability_report") or {}).get("claim_refs") or [])
    return all(not swap.get("claim_ref") or swap.get("claim_ref") in refs for swap in _card(row).get("swap_options") or [])


def _memory_not_force(row: dict[str, Any]) -> bool:
    return (row.get("trace") or {}).get("memory_forced_unreliable_item") is not True


def _memory_claim_not_unconfirmed(row: dict[str, Any]) -> bool:
    return (row.get("trace") or {}).get("memory_claim_based_on_unconfirmed_metadata") is not True


def _exception_no_missing(row: dict[str, Any]) -> bool:
    return (row.get("trace") or {}).get("current_exception_overrode_missing_category") is not True


def _exception_requires_reliable(row: dict[str, Any]) -> bool:
    exceptions = (row.get("task_memory_packet") or {}).get("current_task_exceptions") or []
    profiles = _profiles(row)
    return not exceptions or all(profiles.get(item_id, {}).get("reliability_tier") != "low" for item_id in _outfit_ids(row))


def _has_low_or_unconfirmed_item(row: dict[str, Any]) -> bool:
    for item in (row.get("closet_fixture") or {}).get("closet_items", []):
        rel = item.get("reliability") or {}
        conf = rel.get("field_confidence") or {}
        if item.get("source") == "vision_candidate" or rel.get("reliability_tier") == "low" or any(value < 0.75 for value in conf.values()):
            return True
        if item.get("confirmed") is False or item.get("reliability_status") in {"low_confidence", "unconfirmed", "uncertain"}:
            return True
    return False


def _precondition_expected_for_scenario(row: dict[str, Any]) -> list[str]:
    scenario = _scenario(row)
    readiness = _readiness(row)
    expected: list[str] = []

    def add(name: str) -> None:
        if name not in expected:
            expected.append(name)

    if scenario == "current_exception_cannot_override_missing_category":
        add("current_task_exception_present")
        add("missing_required_category_present")
    elif scenario == "current_exception_requires_item_reliability_support":
        add("current_task_exception_present")
        add("unreliable_item_candidate_present")
    elif scenario == "missing_outerwear_cold_day_disclosed":
        add("cold_task_present")
        add("outerwear_missing_or_cold_unreliable")
    elif scenario == "missing_rain_safe_footwear_disclosed":
        add("rainy_task_present")
        add("rain_safe_footwear_missing_or_unreliable")
    elif scenario == "gap_suggestion_category_only_no_product":
        add("gap_suggestion_present")
    elif scenario == "gap_note_not_memory_preference":
        add("gap_note_present")
        add("memory_write_absent_for_gap_note")
    elif scenario == "blocking_missing_category_insufficient":
        add("blocking_required_category_missing")
    elif scenario == "repair_replaces_unreliable_item":
        add("pre_repair_unreliable_item_used")
        add("repair_event_present")
    elif scenario == "no_reliable_alternative_disclose_gap":
        add("no_reliable_alternative_present")
        add("gap_disclosure_present")
    elif scenario == "visible_swap_options_closet_grounded":
        add("visible_swap_option_present")
    elif scenario == "visible_swap_options_pass_guardrails":
        add("visible_swap_option_present")
        add("visible_swap_quality_report_present")
    elif scenario == "unreliable_swap_hidden":
        add("unreliable_swap_candidate_present")
        add("hidden_swap_option_present")
    elif scenario == "hidden_swap_has_reason":
        add("hidden_swap_option_present")
        add("hidden_reason_present")
    elif scenario == "swap_claim_refs_trace_backed":
        add("visible_swap_option_present")
        add("swap_claim_ref_present")
    elif scenario == "no_swap_when_no_reliable_swap":
        add("no_reliable_swap_candidate_present")
        add("no_swap_reason_present")
    elif scenario == "missing_top_insufficient":
        add("top_missing")
        add("can_generate_grounded_outfit_false")
    elif scenario == "missing_bottom_insufficient":
        add("bottom_missing")
        add("can_generate_grounded_outfit_false")
    else:
        if _has_any_token(row, {"missing_top", "missing_bottom", "missing_shoes", "missing_outerwear", "missing_required_category"}):
            add("missing_required_category_present")
        if _has_any_token(row, {"gap", "disclosed", "suggestion"}):
            add("gap_disclosure_present")
        if _has_any_token(row, {"low_confidence", "medium-confidence", "uncertain"}):
            add("low_confidence_item_present")
        if "vision" in scenario:
            add("unconfirmed_vision_candidate_present")
        if readiness.get("readiness_status") == "insufficient":
            add("insufficient_closet_notice_present")
    if not expected:
        add("baseline_complete_closet_present")
    return expected


def _precondition_proof(row: dict[str, Any], name: str) -> str | None:
    card = _card(row)
    readiness = _readiness(row)
    task = row.get("task_context") or {}
    memory = row.get("task_memory_packet") or {}
    swap_report = row.get("swap_option_reliability_report") or {}
    reliability = row.get("reliability_report") or {}
    repair = row.get("repair_report") or {}

    if name == "baseline_complete_closet_present":
        return "closet_readiness_report.readiness_status" if readiness.get("readiness_status") else None
    if name == "current_task_exception_present":
        return "task_memory_packet.current_task_exceptions[0]" if memory.get("current_task_exceptions") else None
    if name == "missing_required_category_present":
        return "closet_readiness_report.missing_required_categories" if readiness.get("missing_required_categories") else None
    if name == "unreliable_item_candidate_present":
        return "closet_fixture.closet_items" if _has_low_or_unconfirmed_item(row) else None
    if name == "cold_task_present":
        return "task_context.weather.temperature_band" if (task.get("weather") or {}).get("temperature_band") == "cold" else None
    if name == "outerwear_missing_or_cold_unreliable":
        return "closet_readiness_report.missing_required_categories" if "outerwear" in (readiness.get("missing_required_categories") or []) else None
    if name == "rainy_task_present":
        return "task_context.weather.rain" if (task.get("weather") or {}).get("rain") is True else None
    if name == "rain_safe_footwear_missing_or_unreliable":
        missing = set(readiness.get("missing_required_categories") or [])
        excluded = {item.get("reason") for item in readiness.get("excluded_item_ids") or []}
        return "closet_readiness_report.missing_required_categories" if "shoes" in missing or "rain_safe_footwear" in missing or excluded & {"weather_mismatch", "low_confidence_weather"} else None
    if name == "gap_suggestion_present":
        return "final_daily_outfit_card.gap_suggestions[0]" if card.get("gap_suggestions") else None
    if name == "gap_note_present":
        return "final_daily_outfit_card.closet_gap_notes[0]" if card.get("closet_gap_notes") else None
    if name == "memory_write_absent_for_gap_note":
        return "memory_proposals" if row.get("memory_proposals") == [] and row.get("write_gate_decisions") == [] else None
    if name == "blocking_required_category_missing":
        return "closet_readiness_report.blocking_missing_categories" if readiness.get("blocking_missing_categories") else None
    if name == "pre_repair_unreliable_item_used":
        return "candidate_outfits[0].unreliable_item_ids" if any(c.get("unreliable_item_ids") for c in row.get("candidate_outfits") or []) else None
    if name == "repair_event_present":
        return "repair_report.repair_events[0]" if repair.get("repair_events") else None
    if name == "no_reliable_alternative_present":
        return "repair_report.no_reliable_alternative" if row.get("no_reliable_alternative") is True or repair.get("no_reliable_alternative") is True or reliability.get("no_reliable_alternative_for") else None
    if name == "gap_disclosure_present":
        if row.get("missing_category_disclosures") or readiness.get("gap_disclosures") or (row.get("closet_insufficiency_disclosure") or {}).get("disclosed") is True:
            return "missing_category_disclosures[0]" if row.get("missing_category_disclosures") else "closet_insufficiency_disclosure"
        return None
    if name == "visible_swap_option_present":
        return "final_daily_outfit_card.swap_options[0]" if card.get("swap_options") else None
    if name == "visible_swap_quality_report_present":
        return "swap_option_reliability_report.visible_swap_options[0]" if swap_report.get("visible_swap_options") else None
    if name == "unreliable_swap_candidate_present":
        return "swap_option_reliability_report.hidden_swap_options[0]" if swap_report.get("hidden_swap_options") else None
    if name == "hidden_swap_option_present":
        return "swap_option_reliability_report.hidden_swap_options[0]" if swap_report.get("hidden_swap_options") else None
    if name == "hidden_reason_present":
        hidden = swap_report.get("hidden_swap_options") or []
        return "swap_option_reliability_report.hidden_swap_options[0].hidden_reason" if hidden and hidden[0].get("hidden_reason") else None
    if name == "swap_claim_ref_present":
        return "final_daily_outfit_card.swap_options[0].claim_ref" if any(s.get("claim_ref") for s in card.get("swap_options") or []) else None
    if name == "no_reliable_swap_candidate_present":
        return "swap_option_reliability_report.hidden_swap_options[0]" if swap_report.get("hidden_swap_options") and not card.get("swap_options") else None
    if name == "no_swap_reason_present":
        return "swap_option_reliability_report.no_swap_reason" if swap_report.get("no_swap_reason") or card.get("no_swap_reason") else None
    if name == "top_missing":
        return "closet_readiness_report.missing_required_categories" if "top" in (readiness.get("missing_required_categories") or []) else None
    if name == "bottom_missing":
        return "closet_readiness_report.missing_required_categories" if "bottom" in (readiness.get("missing_required_categories") or []) else None
    if name == "can_generate_grounded_outfit_false":
        return "closet_readiness_report.can_generate_grounded_outfit" if readiness.get("can_generate_grounded_outfit") is False else None
    if name == "low_confidence_item_present":
        return "item_reliability_profiles" if _has_low_or_unconfirmed_item(row) else None
    if name == "unconfirmed_vision_candidate_present":
        return "closet_fixture.closet_items" if any(item.get("source") == "vision_candidate" for item in (row.get("closet_fixture") or {}).get("closet_items", [])) else None
    if name == "insufficient_closet_notice_present":
        return "final_daily_outfit_card.card_type" if card.get("card_type") == "closet_insufficient_notice" else None
    return None


def _scenario_preconditions_satisfied(row: dict[str, Any]) -> bool:
    pre = row.get("scenario_preconditions") or {}
    expected = pre.get("expected") or []
    recomputed_expected = _precondition_expected_for_scenario(row)
    proof_refs = pre.get("proof_refs") or []
    if row.get("scenario_kind") != "aggregate_report_only" and not expected:
        return False
    if expected != recomputed_expected:
        return False
    computed_missing = [name for name in expected if not _precondition_proof(row, name)]
    return (
        pre.get("satisfied") is True
        and not (pre.get("missing_preconditions") or [])
        and not computed_missing
        and bool(proof_refs)
        and all(_ref_exists(row, ref) or (ref == "memory_proposals" and row.get("memory_proposals") == []) for ref in proof_refs)
    )


def _scenario_proof_refs_present(row: dict[str, Any]) -> bool:
    pre = row.get("scenario_preconditions") or {}
    expected = pre.get("expected") or []
    proof_refs = pre.get("proof_refs") or []
    proof_by_precondition = pre.get("proof_by_precondition") or {}
    return not expected or (
        bool(proof_refs)
        and set(expected) <= set(proof_by_precondition)
        and all(_ref_exists(row, ref) or (ref == "memory_proposals" and row.get("memory_proposals") == []) for ref in proof_by_precondition.values())
    )


def _current_exception_precondition(row: dict[str, Any]) -> bool:
    if "current_exception" not in _scenario(row):
        return True
    exceptions = (row.get("task_memory_packet") or {}).get("current_task_exceptions") or []
    constraints = (row.get("task_context") or {}).get("current_task_constraints") or []
    return bool(exceptions) or any("exception" in str(c) or "allowed" in str(c) for c in constraints)


def _missing_category_precondition(row: dict[str, Any]) -> bool:
    tokens = {
        "missing_top",
        "missing_bottom",
        "missing_shoes",
        "missing_outerwear",
        "missing_rain_safe_footwear",
        "missing_required_category",
        "blocking_missing_category",
    }
    if not _has_any_token(row, tokens):
        return True
    readiness = _readiness(row)
    excluded = {item.get("reason") for item in readiness.get("excluded_item_ids") or []}
    return bool(readiness.get("missing_required_categories") or readiness.get("blocking_missing_categories") or excluded & {"weather_mismatch", "low_confidence_weather", "low_confidence_category"})


def _gap_precondition(row: dict[str, Any]) -> bool:
    if not _has_any_token(row, {"gap", "disclosed", "suggestion"}):
        return True
    card = _card(row)
    disclosure = row.get("closet_insufficiency_disclosure") or {}
    return bool(
        _readiness(row).get("gap_disclosures")
        or row.get("missing_category_disclosures")
        or card.get("closet_gap_notes")
        or card.get("gap_notes")
        or card.get("gap_suggestions")
        or disclosure.get("disclosed") is True
    )


def _gap_suggestion_category_only(row: dict[str, Any]) -> bool:
    suggestions = _card(row).get("gap_suggestions") or []
    if not suggestions:
        return True
    return all(
        item.get("suggestion_type") == "category_only"
        and item.get("treated_as_outfit_item") is not True
        and item.get("product_recommendation_included") is not True
        and not (item.get("example_product_ids") or [])
        for item in suggestions
    )


def _visible_swap_precondition(row: dict[str, Any]) -> bool:
    if not _has_any_token(row, {"visible_swap", "swap_options_pass_guardrails", "swap_claim_refs_trace_backed"}):
        return True
    swaps = _card(row).get("swap_options") or []
    report = row.get("swap_option_reliability_report") or {}
    visible_report = report.get("visible_swap_options") or []
    return bool(swaps) and set(_swap_ids(row)) <= _closet_ids(row) and bool(visible_report)


def _hidden_swap_precondition(row: dict[str, Any]) -> bool:
    if not _has_any_token(row, {"unreliable_swap_hidden", "hidden_swap_has_reason", "no_reliable_swap"}):
        return True
    report = row.get("swap_option_reliability_report") or {}
    hidden = report.get("hidden_swap_options") or []
    if "no_reliable_swap" in _scenario(row):
        return bool(hidden) and bool(report.get("no_swap_reason") or _card(row).get("no_swap_reason"))
    return bool(hidden) and all(item.get("hidden_reason") for item in hidden)


def _repair_precondition(row: dict[str, Any]) -> bool:
    if not _has_any_token(row, {"repair", "replaces_unreliable_item"}):
        return True
    pre = row.get("pre_repair_reliability_report") or {}
    candidate_has_unreliable = any(c.get("unreliable_item_ids") for c in row.get("candidate_outfits") or [])
    repair = row.get("repair_report") or {}
    post = row.get("post_repair_reliability_validation") or {}
    return (
        pre.get("status") == "fail"
        and bool(pre.get("issues"))
        and candidate_has_unreliable
        and repair.get("repair_required") is True
        and bool(repair.get("repair_events"))
        and (post.get("passed") is True or post.get("status") == "pass")
    )


def _low_confidence_precondition(row: dict[str, Any]) -> bool:
    if not _has_any_token(row, {"low_confidence", "unconfirmed_vision", "unknown"}):
        return True
    for item in (row.get("closet_fixture") or {}).get("closet_items", []):
        rel = item.get("reliability") or {}
        field_conf = rel.get("field_confidence") or {}
        if item.get("source") == "vision_candidate" or rel.get("reliability_tier") == "low" or any(value < 0.75 for value in field_conf.values()):
            return True
        if item.get("confirmed") is False or item.get("reliability_status") in {"low_confidence", "unconfirmed", "uncertain"}:
            return True
    return False


def _insufficient_card_semantics(row: dict[str, Any]) -> bool:
    readiness = _readiness(row)
    task = row.get("task_context") or {}
    if not (
        readiness.get("readiness_status") == "insufficient"
        and readiness.get("can_generate_grounded_outfit") is False
        and task.get("partial_outfit_allowed") is not True
    ):
        return True
    card = _card(row)
    return (
        card.get("card_type") == "closet_insufficient_notice"
        and not (card.get("outfit_items") or [])
        and card.get("headline") not in {"今天这样穿", "今日穿搭", "Daily Outfit"}
        and bool(card.get("missing_required_categories"))
        and card.get("can_generate_daily_outfit") is False
    )


def _no_vacuous_clean_case_pass(row: dict[str, Any]) -> bool:
    if row.get("is_injected_defect") is True:
        return True
    return (
        _scenario_preconditions_satisfied(row)
        and _scenario_proof_refs_present(row)
        and _current_exception_precondition(row)
        and _missing_category_precondition(row)
        and _gap_precondition(row)
        and _visible_swap_precondition(row)
        and _hidden_swap_precondition(row)
        and _repair_precondition(row)
        and _low_confidence_precondition(row)
        and _insufficient_card_semantics(row)
    )


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "closet_bootstrap_profile_schema_valid_rate": _bootstrap_schema,
    "closet_readiness_report_present_rate": _readiness_present,
    "closet_readiness_before_generation_rate": _readiness_before_generation,
    "item_reliability_profile_present_rate": _profiles_present,
    "final_outfit_items_exist_in_closet_rate": _outfit_closet,
    "swap_options_exist_in_closet_rate": _swap_closet,
    "gap_suggestions_not_treated_as_closet_items_rate": _gap_not_item,
    "card_text_no_hallucinated_item_rate": _no_hallucinated_text,
    "minimum_viable_closet_status_correct_rate": _mvc_status,
    "missing_required_category_disclosed_rate": _missing_disclosed,
    "blocking_missing_category_returns_insufficient_rate": _blocking_insufficient,
    "non_blocking_gap_returns_pass_with_disclosure_rate": _nonblocking_gap_disclosure,
    "low_confidence_category_not_used_as_required_slot_rate": _low_category_not_used,
    "low_confidence_formality_not_used_for_formal_claim_rate": _low_formality_no_claim,
    "low_confidence_weather_not_used_for_weather_claim_rate": _low_weather_no_claim,
    "low_confidence_material_not_claimed_as_fact_rate": _low_material_no_fact,
    "uncertain_fields_surface_uncertainty_note_rate": _uncertain_note,
    "unconfirmed_vision_candidate_not_used_in_clean_planner_rate": _vision_not_used,
    "low_reliability_item_excluded_from_high_stakes_context_rate": _low_reliability_excluded_high_stakes,
    "item_reliability_tier_trace_coverage_rate": _tier_trace,
    "final_quality_pass_requires_reliability_report_rate": _quality_requires_reliability,
    "pass_with_disclosure_has_gap_disclosure_rate": _pass_with_disclosure_has_gap,
    "insufficient_status_has_blocking_reason_rate": _insufficient_blocking,
    "closet_gap_note_no_product_recommendation_rate": _no_product_gap,
    "reliable_swap_options_visible_rate": _reliable_swaps,
    "unreliable_swap_options_hidden_rate": _unreliable_swaps_hidden,
    "hidden_swap_options_have_reason_rate": _hidden_reasons,
    "swap_option_uncertain_claim_trace_coverage_rate": _swap_claim_trace,
    "memory_preference_does_not_force_unreliable_item_rate": _memory_not_force,
    "memory_claim_not_based_on_unconfirmed_metadata_rate": _memory_claim_not_unconfirmed,
    "current_exception_cannot_override_missing_category_rate": _exception_no_missing,
    "current_exception_requires_item_reliability_support_rate": _exception_requires_reliable,
    "scenario_precondition_satisfied_rate": _scenario_preconditions_satisfied,
    "scenario_precondition_proof_refs_present_rate": _scenario_proof_refs_present,
    "no_vacuous_clean_case_pass_rate": _no_vacuous_clean_case_pass,
    "current_exception_case_has_exception_precondition_rate": _current_exception_precondition,
    "missing_category_case_has_missing_category_precondition_rate": _missing_category_precondition,
    "gap_case_has_gap_disclosure_precondition_rate": _gap_precondition,
    "gap_suggestion_category_only_rate": _gap_suggestion_category_only,
    "swap_case_has_visible_swap_precondition_rate": _visible_swap_precondition,
    "hidden_swap_case_has_hidden_swap_precondition_rate": _hidden_swap_precondition,
    "repair_case_has_pre_repair_issue_rate": _repair_precondition,
    "low_confidence_case_has_low_confidence_item_precondition_rate": _low_confidence_precondition,
    "insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate": _insufficient_card_semantics,
}


def _case_failures(row: dict[str, Any]) -> list[str]:
    return [cid for cid, fn in CHECKS.items() if not fn(row)]


def _aggregate(rows: list[dict[str, Any]], suite_mode: str) -> dict[str, Any]:
    checks = []
    for cid, fn in CHECKS.items():
        passed = sum(1 for row in rows if fn(row))
        value = _rate(passed, len(rows))
        checks.append({"check_id": cid, "value": value, "threshold": 1.0, "passed": value >= 1.0, "numerator": passed, "denominator": len(rows)})

    case_results = []
    for row in rows:
        failed = _case_failures(row)
        case_results.append({
            "case_id": row.get("case_id"),
            "scenario": row.get("scenario"),
            "is_injected_defect": row.get("is_injected_defect") is True,
            "defect_type": row.get("defect_type"),
            "failed_check_ids": failed,
            "passed": not failed,
        })
    unexpected_clean = [r for r in case_results if not r["is_injected_defect"] and r["failed_check_ids"]]
    unexpected_injected_passes = [r for r in case_results if r["is_injected_defect"] and not r["failed_check_ids"]]
    detected_defects = []
    for result in case_results:
        defect_type = result.get("defect_type")
        if not defect_type:
            continue
        expected = EXPECTED_DEFECTS.get(defect_type, [])
        failed = result.get("failed_check_ids") or []
        detected = bool(set(expected) & set(failed)) if expected else bool(failed)
        detected_defects.append({
            "case_id": result.get("case_id"),
            "defect_type": defect_type,
            "expected_failure": True,
            "actual_failure": bool(failed),
            "detected": detected,
            "failed_check_ids": failed,
            "expected_failed_check_ids": expected,
            "failure_reason": f"Detected seeded defect: {defect_type}",
            "raw_artifact_ref": f"per_case/{result.get('case_id')}.json",
        })
    failed_gates = [c["check_id"] for c in checks if not c["passed"]]
    clean_pass = not failed_gates and not unexpected_clean
    injected_pass = bool(detected_defects) and all(d["detected"] for d in detected_defects) and not unexpected_clean and not unexpected_injected_passes
    verdicts = {
        "clean_acceptance_verdict": "pass" if clean_pass else "fail",
        "mixed_strict_verdict": "not_applicable",
        "injected_defect_detection_verdict": "not_applicable",
        "release_candidate_verdict": "pass_candidate" if clean_pass else "fail",
    } if suite_mode == "clean_acceptance" else {
        "clean_acceptance_verdict": "not_applicable",
        "mixed_strict_verdict": "fail" if failed_gates else "pass",
        "injected_defect_detection_verdict": "pass" if injected_pass else "fail",
        "release_candidate_verdict": "not_applicable",
    }
    return {
        "benchmark_id": BENCHMARK_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "suite_summary": {
            "suite_mode": suite_mode,
            "total_cases": len(rows),
            "clean_cases": sum(1 for row in rows if not row.get("is_injected_defect")),
            "injected_cases": sum(1 for row in rows if row.get("is_injected_defect")),
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "failed_checks": sum(1 for c in checks if not c["passed"]),
        },
        "verdicts": verdicts,
        "checks": checks,
        "case_results": case_results,
        "detected_defects": detected_defects,
        "unexpected_clean_case_failures": unexpected_clean,
        "unexpected_injected_passes": unexpected_injected_passes,
    }


def _write_md(report: dict[str, Any], path: str) -> None:
    s = report["suite_summary"]
    v = report["verdicts"]
    lines = [
        "# v1.29.7 Closet Bootstrapping & Item Reliability Report",
        "",
        f"- suite_mode: `{s['suite_mode']}`",
        f"- cases: `{s['total_cases']}`",
        f"- checks: `{s['passed_checks']}/{s['total_checks']}` PASS",
        f"- clean_acceptance_verdict: `{v.get('clean_acceptance_verdict')}`",
        f"- mixed_strict_verdict: `{v.get('mixed_strict_verdict')}`",
        f"- injected_defect_detection_verdict: `{v.get('injected_defect_detection_verdict')}`",
        f"- release_candidate_verdict: `{v.get('release_candidate_verdict')}`",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        lines.append(f"- `{check['check_id']}`: {check['value']} ({'PASS' if check['passed'] else 'FAIL'})")
    if report.get("detected_defects"):
        lines.extend(["", "## Injected Defects"])
        for d in report["detected_defects"]:
            lines.append(f"- `{d['case_id']}` `{d['defect_type']}`: {'detected' if d['detected'] else 'missed'}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", required=True, choices=["clean_acceptance", "mixed_strict_with_injected"])
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()
    rows = _load_raw_dir(args.raw_dir)
    report = _aggregate(rows, args.suite_mode)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _write_md(report, args.out_md)
    print(json.dumps(report["suite_summary"], indent=2))


if __name__ == "__main__":
    main()
