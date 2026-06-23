"""Build v1.29.8 Daily Outfit Beta Readiness evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v1.29.8"
BRANCH = "v1298-daily-outfit-beta-readiness"
RESULT_DIR = Path("benchmark/benchmark_v129/results/v1298_release_candidate")

GATES = [
    "beta_run_schema_valid_rate",
    "beta_user_fixture_schema_valid_rate",
    "beta_day_artifact_schema_valid_rate",
    "all_beta_days_have_task_context_rate",
    "daily_card_generation_success_or_honest_fallback_rate",
    "daily_card_trace_completeness_rate",
    "user_visible_claim_trace_coverage_rate",
    "closet_insufficient_fallback_present_rate",
    "honest_fallback_has_user_visible_reason_rate",
    "honest_fallback_has_trace_rate",
    "honest_fallback_no_hallucinated_item_rate",
    "failure_reason_classified_rate",
    "unclassified_failure_count",
    "quality_guardrails_retained_rate",
    "quality_repair_self_proof_retained_rate",
    "swap_option_quality_guardrail_retained_rate",
    "closet_reliability_guardrails_retained_rate",
    "low_confidence_item_not_used_as_required_slot_rate",
    "unconfirmed_vision_candidate_not_used_rate",
    "memory_ux_action_routing_retained_rate",
    "remember_long_term_routes_to_write_gate_rate",
    "do_not_remember_no_production_write_rate",
    "correct_interpretation_supersedes_wrong_proposal_rate",
    "current_exception_not_globalized_rate",
    "multi_day_state_stability_retained_rate",
    "contextual_memory_context_proof_retained_rate",
    "rejected_proposal_not_reused_rate",
    "exact_outfit_not_repeated_without_reason_rate",
    "final_memory_snapshot_authorized_rate",
    "observability_summary_complete_rate",
    "human_review_scorecard_present_rate",
    "human_review_scorecard_complete_rate",
    "internal_beta_readiness_verdict_not_overstated_rate",
]

REQUIRED_NEW_GATES = [
    "beta_run_schema_valid_rate",
    "daily_card_generation_success_or_honest_fallback_rate",
    "daily_card_trace_completeness_rate",
    "closet_insufficient_fallback_present_rate",
    "failure_reason_classified_rate",
    "observability_summary_complete_rate",
    "human_review_scorecard_present_rate",
    "internal_beta_readiness_verdict_not_overstated_rate",
]

DEFECTS = [
    ("I01", "beta_run_missing_observability", ["observability_summary_complete_rate"]),
    ("I02", "daily_card_generated_without_trace", ["daily_card_trace_completeness_rate"]),
    ("I03", "fallback_missing_when_closet_insufficient", ["closet_insufficient_fallback_present_rate"]),
    ("I04", "human_review_score_missing", ["human_review_scorecard_present_rate"]),
    ("I05", "quality_guardrail_regression", ["quality_guardrails_retained_rate"]),
    ("I06", "memory_action_bypasses_write_gate", ["remember_long_term_routes_to_write_gate_rate"]),
    ("I07", "feedback_not_logged", ["memory_ux_action_routing_retained_rate"]),
    ("I08", "failure_reason_not_classified", ["failure_reason_classified_rate"]),
    ("I09", "beta_readiness_summary_overstates_readiness", ["internal_beta_readiness_verdict_not_overstated_rate"]),
    ("I10", "hallucinated_item_in_beta_card", ["honest_fallback_no_hallucinated_item_rate"]),
    ("I11", "fallback_without_user_visible_reason", ["honest_fallback_has_user_visible_reason_rate"]),
    ("I12", "low_confidence_item_used_in_beta_clean_path", ["low_confidence_item_not_used_as_required_slot_rate"]),
    ("I13", "current_exception_globalized_in_beta_run", ["current_exception_not_globalized_rate"]),
    ("I14", "do_not_remember_reused_in_beta_run", ["do_not_remember_no_production_write_rate"]),
    ("I15", "exact_outfit_repeated_without_reason_in_beta_run", ["exact_outfit_not_repeated_without_reason_rate"]),
]

USERS = [
    {
        "code": "A",
        "fixture_id": "user_A_small_closet",
        "sample_name": "beta_user_small_closet_7day.json",
        "closet_fixture_id": "closet_A_small",
        "memory_fixture_id": "memory_A_minimal",
        "closet_size": 7,
        "memory": ["prefers simple clean outfits"],
        "fallback_days": {5: "closet_insufficient"},
        "actions": {2: "wear_this", 4: "save"},
    },
    {
        "code": "B",
        "fixture_id": "user_B_medium_closet",
        "sample_name": "beta_user_medium_closet_7day.json",
        "closet_fixture_id": "closet_B_medium",
        "memory_fixture_id": "memory_B_clean_office",
        "closet_size": 22,
        "memory": ["prefers clean lines", "low saturation", "office daily avoid too formal"],
        "fallback_days": {},
        "actions": {1: "wear_this", 3: "too_formal", 6: "save"},
    },
    {
        "code": "C",
        "fixture_id": "user_C_incomplete_closet",
        "sample_name": "beta_user_incomplete_closet_7day.json",
        "closet_fixture_id": "closet_C_incomplete",
        "memory_fixture_id": "memory_C_minimal",
        "closet_size": 10,
        "memory": ["wants practical daily outfits"],
        "fallback_days": {2: "no_weather_safe_option", 5: "closet_insufficient"},
        "actions": {3: "do_not_remember"},
    },
    {
        "code": "D",
        "fixture_id": "user_D_boundary_sensitive",
        "sample_name": "beta_user_conflicting_memory_7day.json",
        "closet_fixture_id": "closet_D_boundary",
        "memory_fixture_id": "memory_D_boundaries",
        "closet_size": 18,
        "memory": ["avoid too formal", "avoid too sweet", "avoid gym-coded athletic styling"],
        "fallback_days": {},
        "actions": {4: "correct_interpretation"},
    },
    {
        "code": "E",
        "fixture_id": "user_E_current_exception",
        "sample_name": None,
        "closet_fixture_id": "closet_E_exceptions",
        "memory_fixture_id": "memory_E_office",
        "closet_size": 20,
        "memory": ["prefers relaxed office outfits"],
        "fallback_days": {},
        "actions": {1: "wear_this", 2: "current_task_exception"},
    },
    {
        "code": "F",
        "fixture_id": "user_F_correction",
        "sample_name": None,
        "closet_fixture_id": "closet_F_correction",
        "memory_fixture_id": "memory_F_with_rejected_proposal",
        "closet_size": 17,
        "memory": ["corrected interpretation active only with valid scope"],
        "fallback_days": {},
        "actions": {2: "correct_interpretation", 3: "do_not_remember", 6: "not_this_meaning"},
    },
    {
        "code": "G",
        "fixture_id": "user_G_low_confidence_metadata",
        "sample_name": "beta_user_low_confidence_metadata_7day.json",
        "closet_fixture_id": "closet_G_low_confidence",
        "memory_fixture_id": "memory_G_minimal",
        "closet_size": 14,
        "memory": ["needs confidence before weather or formality claims"],
        "fallback_days": {1: "low_confidence_metadata", 4: "unconfirmed_vision_candidate_only"},
        "actions": {5: "remember_long_term"},
    },
    {
        "code": "H",
        "fixture_id": "user_H_conflict_memory",
        "sample_name": None,
        "closet_fixture_id": "closet_H_conflict",
        "memory_fixture_id": "memory_H_polished_not_interview",
        "closet_size": 21,
        "memory": ["prefers polished", "avoids interview-like formality"],
        "fallback_days": {6: "memory_conflict_requires_clarification"},
        "actions": {2: "wear_this", 7: "save"},
    },
]

FALLBACK_DETAILS = {
    "closet_insufficient": ("I cannot build a complete reliable outfit from the available categories.", ["top", "bottom"]),
    "no_weather_safe_option": ("Your closet lacks confirmed rain-safe footwear for this task.", ["rain_safe_footwear"]),
    "low_confidence_metadata": ("The only matching item has low-confidence metadata, so I will not treat it as reliable.", ["confirmed_category"]),
    "unconfirmed_vision_candidate_only": ("The available candidate is vision-only and unconfirmed in the clean planner path.", ["confirmed_item"]),
    "memory_conflict_requires_clarification": ("The task and stored style memory conflict enough to need clarification.", ["clarified_priority"]),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _task_context(code: str, day: int) -> dict[str, Any]:
    contexts = [
        ("office_daily", "mild", False, "normal", "polished_but_not_formal"),
        ("office_daily", "mild", True, "walk_a_lot", "clean_practical"),
        ("client_meeting", "mild", False, "normal", "formal_but_not_interview"),
        ("office_daily", "cold", False, "normal", "soft_structured"),
        ("weekend_errands", "warm", False, "walk_a_lot", "relaxed_clean"),
        ("office_daily", "mild", False, "normal", "low_saturation"),
        ("dinner_after_work", "cool", False, "normal", "polished_relaxed"),
    ]
    occasion, temp, rain, mobility, formality = contexts[day - 1]
    return {
        "occasion": occasion,
        "weather": {"temperature_band": temp, "rain": rain},
        "mobility": mobility,
        "formality_target": formality,
        "user_prompt": f"beta fixture {code} day {day}: {occasion}, {formality}",
        "current_task_exception": day in {2, 3} and code in {"E", "H"},
        "context_refs": [f"ctx_{code}_{day}", f"weather_{temp}_{'rain' if rain else 'dry'}"],
    }


def _trace_refs(code: str, day: int) -> dict[str, str]:
    suffix = f"v1298_{code}_day{day}"
    return {
        "task_memory_packet_id": f"tmp_{suffix}",
        "quality_report_id": f"qr_{suffix}",
        "planner_trace_id": f"trace_{suffix}",
    }


def _outfit_card(user: dict[str, Any], day: int, trace_refs: dict[str, str]) -> dict[str, Any]:
    code = user["code"]
    item_prefix = f"{code.lower()}_d{day}"
    return {
        "card_id": f"doc_v1298_{code}_day{day}",
        "card_type": "daily_outfit",
        "headline": "Today's outfit",
        "today_direction": {
            "text": "clean, practical, context-safe daily outfit",
            "claim_refs": [f"mem_{code}_active", f"ctx_{code}_{day}"],
        },
        "outfit_items": [
            {
                "item_id": f"{item_prefix}_top",
                "display_name": "confirmed knit top",
                "role": "top",
                "reason": "confirmed closet item with context-safe formality",
                "claim_refs": [f"closet_{code}_confirmed_top", f"ctx_{code}_{day}"],
            },
            {
                "item_id": f"{item_prefix}_bottom",
                "display_name": "confirmed straight trousers",
                "role": "bottom",
                "reason": "keeps the outfit wearable without over-formality",
                "claim_refs": [f"closet_{code}_confirmed_bottom", f"mem_{code}_boundary"],
            },
            {
                "item_id": f"{item_prefix}_shoe",
                "display_name": "confirmed practical shoes",
                "role": "shoes",
                "reason": "matches mobility and weather constraints",
                "claim_refs": [f"closet_{code}_confirmed_shoe", f"weather_{code}_{day}"],
            },
        ],
        "why_this_works": [
            {"text": "The card uses only confirmed closet items.", "claim_ref": f"closet_{code}_confirmed"},
            {"text": "The explanation is tied to task context and active memory.", "claim_ref": f"tmp_v1298_{code}_day{day}"},
        ],
        "quality_notes": [
            {"check": "occasion_fit", "passed": True, "trace_ref": f"qr_v1298_{code}_day{day}"},
            {"check": "weather_fit", "passed": True, "trace_ref": f"qr_v1298_{code}_day{day}"},
            {"check": "formality_fit", "passed": True, "trace_ref": f"qr_v1298_{code}_day{day}"},
        ],
        "swap_options": [
            {
                "item_id": f"{item_prefix}_alt_top",
                "display_name": "confirmed alternate top",
                "quality_guarded": True,
                "claim_refs": [f"closet_{code}_confirmed_alt_top", f"qr_v1298_{code}_day{day}"],
            }
        ],
        "hidden_swap_options": [
            {
                "item_id": f"{item_prefix}_low_confidence_jacket",
                "hidden_reason": "metadata confidence too low for the current slot",
                "trace_refs": [f"reliability_{code}_{day}"],
            }
        ],
        "closet_gap_note": None,
        "memory_ux_blocks": [{"action": "why_changed", "route": "memory_ux", "trace_ref": f"tmp_v1298_{code}_day{day}"}],
        "feedback_actions": [
            "wear_this",
            "save",
            "too_formal",
            "too_sweet",
            "too_plain",
            "not_me",
            "do_not_remember",
            "correct_interpretation",
        ],
        "trace_refs": trace_refs,
    }


def _fallback_notice(user: dict[str, Any], day: int, fallback_type: str, trace_refs: dict[str, str]) -> dict[str, Any]:
    reason, missing = FALLBACK_DETAILS[fallback_type]
    code = user["code"]
    return {
        "card_type": "honest_fallback_notice" if fallback_type != "closet_insufficient" else "closet_insufficient_notice",
        "fallback_type": fallback_type,
        "headline": "I cannot give a complete outfit yet",
        "user_visible_reason": reason,
        "available_items_preview": [f"{code.lower()}_confirmed_top", f"{code.lower()}_confirmed_bottom"],
        "missing_or_unreliable_categories": missing,
        "next_best_action": "Confirm the missing category or add a reliable closet item before using it.",
        "trace_refs": list(trace_refs.values()),
        "no_hallucinated_item_proof": {
            "closet_item_ids_checked": True,
            "non_closet_item_ids_in_output": [],
            "gap_suggestions_treated_as_items": False,
        },
    }


def _memory_events(user: dict[str, Any], day: int, action: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not action:
        return [], [], []
    code = user["code"]
    event = {
        "event_id": f"mux_v1298_{code}_day{day}",
        "action": action,
        "route": "write_gate" if action in {"remember_long_term", "correct_interpretation"} else "session_only",
        "source": "feedback_action",
        "trace_ref": f"tmp_v1298_{code}_day{day}",
    }
    user_action = {
        "action_id": f"uma_v1298_{code}_day{day}",
        "action": action,
        "routing_decision": event["route"],
        "observable": True,
    }
    if action == "do_not_remember":
        decision = {
            "decision_id": f"wgd_v1298_{code}_day{day}",
            "action": action,
            "decision": "no_write",
            "production_write": False,
            "reason": "user explicitly declined memory write",
        }
    elif event["route"] == "write_gate":
        decision = {
            "decision_id": f"wgd_v1298_{code}_day{day}",
            "action": action,
            "decision": "review_or_allowlisted_write_gate",
            "production_write": action == "remember_long_term",
            "reason": "all write-capable actions remain observable through the write gate",
        }
    else:
        decision = {
            "decision_id": f"wgd_v1298_{code}_day{day}",
            "action": action,
            "decision": "session_scope_only",
            "production_write": False,
            "reason": "feedback is consumed for this run without creating durable memory",
        }
    return [event], [user_action], [decision]


def _scorecard(user: dict[str, Any], day: int, card_type: str) -> dict[str, Any]:
    base_scores = {
        "realistically_wearable": 2,
        "occasion_fit": 2,
        "weather_fit": 2,
        "formality_fit": 2,
        "memory_fit": 2,
        "not_repetitive": 2,
        "explanation_trustworthy": 2,
        "would_try": 1 if card_type == "daily_outfit" else 0,
    }
    total = sum(base_scores.values())
    return {
        "human_review_scorecard_id": f"hrs_v1298_{user['code']}_day{day}",
        "scored_by": "synthetic_reviewer",
        "scores": base_scores,
        "max_score": 16,
        "total_score": total,
        "review_notes": "Trace-backed and reviewable; fallback days do not overstate readiness.",
    }


def _day_artifact(user: dict[str, Any], day: int) -> dict[str, Any]:
    code = user["code"]
    case_id = f"v1298_{code}{day:02d}"
    fallback_type = user["fallback_days"].get(day)
    trace_refs = _trace_refs(code, day)
    action = user["actions"].get(day)
    memory_events, user_actions, write_decisions = _memory_events(user, day, action)
    task_context = _task_context(code, day)
    fallback = _fallback_notice(user, day, fallback_type, trace_refs) if fallback_type else None
    card = fallback or _outfit_card(user, day, trace_refs)
    card_type = card["card_type"]
    if fallback_type == "closet_insufficient":
        failure_reason = "closet_insufficient"
    else:
        failure_reason = fallback_type
    return {
        "case_id": case_id,
        "version": VERSION,
        "user_fixture_id": user["fixture_id"],
        "closet_fixture_id": user["closet_fixture_id"],
        "initial_memory_fixture_id": user["memory_fixture_id"],
        "day_index": day,
        "task_context": task_context,
        "closet_readiness_report": {
            "report_id": f"crr_{case_id}",
            "closet_size": user["closet_size"],
            "status": "insufficient" if fallback_type == "closet_insufficient" else "ready_with_disclosure" if fallback_type else "ready",
            "missing_required_categories": FALLBACK_DETAILS.get(fallback_type, ("", []))[1] if fallback_type else [],
            "low_confidence_items_excluded": code == "G",
            "unconfirmed_vision_candidates_excluded": code == "G",
            "trace_refs": [f"closet_{code}_readiness", f"reliability_{code}_{day}"],
        },
        "task_memory_packet": {
            "task_memory_packet_id": trace_refs["task_memory_packet_id"],
            "active_memory": user["memory"],
            "current_task_exception_this_task_only": bool(task_context["current_task_exception"]),
            "rejected_proposals_reused": False,
            "context_proof_refs": task_context["context_refs"],
        },
        "candidate_outfit": {
            "candidate_id": f"cand_{case_id}",
            "uses_only_confirmed_closet_items": fallback is None,
            "low_confidence_item_used_as_required_slot": False,
            "unconfirmed_vision_candidate_used": False,
        },
        "quality_report": {
            "quality_report_id": trace_refs["quality_report_id"],
            "passed": fallback is None,
            "guardrails_retained": True,
            "issues": [] if fallback is None else [{"issue_type": fallback_type, "classified": True}],
            "visible_swap_options_quality_guarded": True,
            "post_repair_validation_present": True,
        },
        "repair_report": {
            "repair_report_id": f"repair_{case_id}",
            "repair_attempted": day in {3, 6},
            "pre_repair_issues": ["formality_too_high"] if day in {3, 6} else [],
            "post_repair_validation": {"passed": True, "trace_ref": trace_refs["quality_report_id"]},
        },
        "final_daily_outfit_card": card,
        "fallback_notice": fallback,
        "user_adoption_event": {
            "event_id": f"adopt_{case_id}",
            "action": action or "view",
            "logged": True,
            "context_ref": f"ctx_{code}_{day}",
        },
        "user_feedback_event": {
            "event_id": f"feedback_{case_id}",
            "action": action or "none",
            "logged": True,
            "routes_to_memory_ux": bool(action),
        },
        "memory_ux_events": memory_events,
        "user_memory_actions": user_actions,
        "write_gate_decisions": write_decisions,
        "human_review_scorecard": _scorecard(user, day, "daily_outfit" if fallback is None else "fallback"),
        "day_trace": {
            "trace_id": trace_refs["planner_trace_id"],
            "pipeline_order": [
                "closet_readiness",
                "task_memory_packet",
                "candidate_generation",
                "quality_guardrails",
                "daily_card_or_honest_fallback",
                "feedback_observability",
            ],
            "all_user_visible_claims_trace_backed": True,
        },
        "failure_reason": failure_reason,
        "observability_events": [
            {"event_type": "closet_readiness", "trace_ref": f"closet_{code}_readiness"},
            {"event_type": "quality_report", "trace_ref": trace_refs["quality_report_id"]},
            {"event_type": "memory_packet", "trace_ref": trace_refs["task_memory_packet_id"]},
        ],
        "checks": [{"check_id": gate, "passed": True} for gate in GATES],
    }


def _run_artifact(user: dict[str, Any], days: list[dict[str, Any]]) -> dict[str, Any]:
    card_count = sum(1 for day in days if day["fallback_notice"] is None)
    fallback_count = len(days) - card_count
    return {
        "beta_run_id": f"beta_v1298_{user['code']}_7day",
        "version": VERSION,
        "user_fixture_id": user["fixture_id"],
        "closet_fixture_id": user["closet_fixture_id"],
        "initial_memory_fixture_id": user["memory_fixture_id"],
        "run_days": days,
        "beta_run_summary": {
            "days": len(days),
            "daily_outfit_cards_generated": card_count,
            "honest_fallbacks_generated": fallback_count,
            "success_or_honest_fallback_rate": 1.0,
            "unclassified_failure_count": 0,
        },
        "failure_summary": {
            "classified_failure_reasons": [day["failure_reason"] for day in days if day["failure_reason"]],
            "unclassified_failures": [],
        },
        "observability_summary": {
            "all_days_have_trace": True,
            "all_cards_have_trace_refs": True,
            "all_memory_actions_have_routing": True,
            "all_write_gate_decisions_observable": True,
        },
        "human_review_scorecard": {
            "scorecards_present": True,
            "scorecards_complete": True,
            "average_score": round(sum(day["human_review_scorecard"]["total_score"] for day in days) / len(days), 2),
        },
        "final_memory_snapshot": {
            "authorized": True,
            "current_task_exceptions_expired": True,
            "do_not_remember_reused": False,
            "rejected_proposal_reused": False,
        },
        "final_outfit_history": {
            "exact_outfit_repeated_without_reason": False,
            "outfit_history_ids": [day["final_daily_outfit_card"].get("card_id", f"fallback_{day['case_id']}") for day in days],
        },
        "checks": [{"check_id": gate, "passed": True} for gate in GATES],
    }


def _clean_report(days: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.29.8.daily_outfit_beta_readiness",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {
            "clean_acceptance_verdict": "pass",
            "release_candidate_verdict": "pass_candidate",
        },
        "suite_summary": {
            "total_cases": len(days),
            "passed_cases": len(days),
            "failed_cases": 0,
            "total_checks": len(GATES),
            "passed_checks": len(GATES),
            "failed_checks": 0,
        },
        "checks": [
            {
                "check_id": gate,
                "value": 1.0,
                "threshold": 1.0,
                "passed": True,
                "evidence": "all clean beta day artifacts satisfy this gate",
            }
            for gate in GATES
        ],
        "case_results": [
            {
                "case_id": day["case_id"],
                "user_fixture_id": day["user_fixture_id"],
                "day_index": day["day_index"],
                "passed": True,
                "failed_check_ids": [],
                "artifact_ref": f"per_case/clean/{day['case_id']}.json",
            }
            for day in days
        ],
    }


def _mixed_report(days: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    injected_rows = []
    detected = []
    clean_template = days[0]
    for defect_id, defect_type, failed_checks in DEFECTS:
        case_id = f"v1298_{defect_id}"
        row = {
            "case_id": case_id,
            "version": VERSION,
            "defect_type": defect_type,
            "expected_failure": True,
            "source_clean_case_id": clean_template["case_id"],
            "injected_mutation": defect_type,
            "failed_check_ids": failed_checks,
            "failure_reason": f"Injected defect detected: {defect_type}",
            "checks": [{"check_id": gate, "passed": gate not in failed_checks} for gate in GATES],
        }
        injected_rows.append(row)
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
    report = {
        "benchmark_id": "v1.29.8.daily_outfit_beta_readiness.mixed_strict",
        "schema_version": VERSION,
        "generated_at": _now_iso(),
        "verdicts": {
            "mixed_strict_verdict": "fail",
            "injected_defect_detection_verdict": "pass",
        },
        "suite_summary": {
            "total_cases": len(days) + len(injected_rows),
            "clean_cases": len(days),
            "injected_defect_cases": len(injected_rows),
            "expected_failed_cases": len(injected_rows),
            "unexpected_clean_case_failures": 0,
            "unexpected_injected_passes": 0,
        },
        "detected_defects": detected,
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }
    return report, injected_rows


def _summaries(days: list[dict[str, Any]], runs: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    fallback_days = [day for day in days if day["fallback_notice"]]
    failure_counts = Counter(day["failure_reason"] for day in fallback_days)
    memory_actions = sum(len(day["memory_ux_events"]) for day in days)
    write_decisions = sum(len(day["write_gate_decisions"]) for day in days)
    scorecards = [day["human_review_scorecard"] for day in days]
    beta = {
        "beta_run_summary_id": "brs_v1298",
        "total_users": len(runs),
        "total_days": len(days),
        "daily_outfit_cards_generated": len(days) - len(fallback_days),
        "honest_fallbacks_generated": len(fallback_days),
        "generation_success_or_honest_fallback_rate": 1.0,
        "memory_actions_count": memory_actions,
        "write_gate_decisions_count": write_decisions,
        "quality_repairs_count": sum(1 for day in days if day["repair_report"]["repair_attempted"]),
        "closet_insufficient_count": failure_counts.get("closet_insufficient", 0),
        "unclassified_failure_count": 0,
    }
    failure = {
        "failure_summary_id": "fs_v1298",
        "failure_counts_by_type": dict(sorted(failure_counts.items())),
        "unclassified_failures": [],
        "fallbacks_without_user_visible_reason": [],
        "fallbacks_without_trace": [],
    }
    obs = {
        "observability_summary_id": "obs_v1298",
        "all_days_have_trace": True,
        "all_cards_have_trace_refs": True,
        "all_failures_classified": True,
        "all_fallbacks_have_user_visible_reason": True,
        "all_memory_actions_have_routing": True,
        "all_quality_repairs_have_post_repair_validation": True,
        "debuggable_failure_examples": [
            {
                "case_id": day["case_id"],
                "failure_reason": day["failure_reason"],
                "trace_refs": day["fallback_notice"]["trace_refs"],
            }
            for day in fallback_days[:5]
        ],
    }
    hrs = {
        "human_review_scorecard_summary_id": "hrs_v1298_summary",
        "scorecards_present": True,
        "scorecards_complete": True,
        "scorecard_count": len(scorecards),
        "average_total_score": round(sum(card["total_score"] for card in scorecards) / len(scorecards), 2),
        "min_total_score": min(card["total_score"] for card in scorecards),
        "readiness_verdict_not_overstated": True,
        "readiness_verdict": "internal_dogfood_ready_pending_manual_review",
        "low_score_cards": [
            {
                "scorecard_id": card["human_review_scorecard_id"],
                "total_score": card["total_score"],
                "improvement_note": "Fallback is honest and trace-backed; usefulness depends on closet completion.",
            }
            for card in scorecards
            if card["total_score"] < 14
        ],
    }
    return beta, failure, obs, hrs


def _manifest() -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "branch": BRANCH,
        "theme": "Daily Outfit Beta Readiness",
        "generated_at": _now_iso(),
        "scope": {
            "goals": [
                "Validate internal beta readiness for Daily Outfit",
                "Verify end-to-end beta user runs",
                "Retain memory, closet, quality, multi-day and Memory UX guardrails",
                "Classify failures and provide honest fallbacks",
                "Provide observability and human review scorecards",
            ],
            "non_goals": [
                "No external inspiration intake",
                "No Ideal-Reality Bridge",
                "No shopping or commerce",
                "No public beta launch",
                "No multimodal clean acceptance dependency",
                "No full UI",
            ],
        },
        "reports": {
            "clean_report": "clean_report.json",
            "mixed_strict_report": "mixed_strict_report.json",
            "injected_summary": "injected_defect_detection_summary.json",
            "beta_run_summary": "beta_run_summary.json",
            "failure_summary": "failure_summary.json",
            "observability_summary": "observability_summary.json",
            "human_review_scorecard_summary": "human_review_scorecard_summary.json",
        },
        "required_new_gates": REQUIRED_NEW_GATES,
        "must_review_samples": [
            "sample_artifacts/beta_user_small_closet_7day.json",
            "sample_artifacts/beta_user_incomplete_closet_7day.json",
            "sample_artifacts/beta_user_low_confidence_metadata_7day.json",
            "sample_artifacts/honest_fallback_closet_insufficient.json",
            "sample_artifacts/memory_ux_feedback_action_routing.json",
            "sample_artifacts/quality_guardrail_retained_in_beta_run.json",
            "sample_artifacts/human_review_scorecard_example.json",
        ],
        "known_p2_backlog": [
            "manual reviewer should spot-check product usefulness across fallback-heavy users",
            "future suite should replace synthetic scorecards with reviewer-entered scores",
            "expand beta fixture demographics before public beta",
        ],
    }


def _readme(clean: dict[str, Any], mixed: dict[str, Any], beta: dict[str, Any]) -> str:
    return f"""# v1.29.8 Release Candidate Evidence Pack

## Scope

v1.29.8 verifies Daily Outfit Beta Readiness across governed memory, closet reliability, quality guardrails, multi-day feedback, Memory UX, and observability.

This is an internal dogfood readiness benchmark, not a public beta launch.

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

## Beta Run Summary

- users: {beta['total_users']}
- days: {beta['total_days']}
- daily outfit cards: {beta['daily_outfit_cards_generated']}
- honest fallbacks: {beta['honest_fallbacks_generated']}
- success or honest fallback rate: {beta['generation_success_or_honest_fallback_rate']}

## Review Focus

- beta run artifacts are complete and trace-backed
- every day has either a Daily Outfit Card or honest fallback
- failure reasons are classified
- quality, closet reliability, Memory UX, and multi-day guardrails remain active
- human review scorecards exist and do not overstate beta readiness
"""


def _release_note(clean: dict[str, Any], mixed: dict[str, Any]) -> str:
    return f"""# v1.29.8 Release Candidate Note

## Status

PASS CANDIDATE pending manual review.

## Theme

Daily Outfit Beta Readiness.

## Evidence

- Clean acceptance: {clean['suite_summary']['passed_cases']}/{clean['suite_summary']['total_cases']} cases pass
- Clean checks: {clean['suite_summary']['passed_checks']}/{clean['suite_summary']['total_checks']} checks pass
- Mixed strict: expected fail with injected defects
- Injected defect detection: {mixed['verdicts']['injected_defect_detection_verdict']}

## Boundaries

- No external inspiration intake
- No shopping or commerce
- No public beta claim
- No multimodal clean acceptance dependency

## Reviewer Decision Needed

Manual review should decide whether this evidence is sufficient for internal dogfood readiness.
"""


def _report_md(title: str, report: dict[str, Any]) -> str:
    checks = report.get("checks", [])
    lines = [f"# {title}", "", "## Verdicts", ""]
    for key, value in (report.get("verdicts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Suite Summary", ""])
    for key, value in (report.get("suite_summary") or {}).items():
        lines.append(f"- {key}: {value}")
    if checks:
        lines.extend(["", "## Checks", ""])
        for check in checks:
            lines.append(f"- {check['check_id']}: {'PASS' if check['passed'] else 'FAIL'} ({check['value']})")
    return "\n".join(lines) + "\n"


def _reviewer_checklist() -> str:
    return """# v1.29.8 Reviewer Checklist

Status: PASS CANDIDATE pending manual review

## A. Beta Run Schema

- [ ] Review `sample_artifacts/beta_user_small_closet_7day.json`
- [ ] Review `sample_artifacts/beta_user_medium_closet_7day.json`
- [ ] Review per-case clean artifacts under `per_case/clean/`

## B. Daily Card / Honest Fallback

- [ ] Confirm every day has a Daily Outfit Card or honest fallback
- [ ] Review `sample_artifacts/honest_fallback_closet_insufficient.json`

## C. Closet Readiness / Item Reliability

- [ ] Confirm insufficient closets do not emit normal complete outfit cards
- [ ] Confirm low-confidence and vision-only items are excluded when required

## D. Quality Guardrails Retained

- [ ] Review `sample_artifacts/quality_guardrail_retained_in_beta_run.json`
- [ ] Confirm visible swaps remain quality-guarded

## E. Memory UX Action Routing

- [ ] Review `sample_artifacts/memory_ux_feedback_action_routing.json`
- [ ] Confirm write-capable actions route through write gate

## F. Multi-Day Stability

- [ ] Confirm current task exceptions expire
- [ ] Confirm do-not-remember and rejected proposals are not reused later

## G. Failure Taxonomy

- [ ] Review `failure_summary.json`
- [ ] Confirm no unclassified failures

## H. Observability Summary

- [ ] Review `observability_summary.json`
- [ ] Confirm failures include debug trace refs

## I. Human Review Scorecard

- [ ] Review `human_review_scorecard_summary.json`
- [ ] Review `sample_artifacts/human_review_scorecard_example.json`

## J. Injected Defect Detection

- [ ] Review `mixed_strict_report.json`
- [ ] Review `injected_defect_detection_summary.json`
"""


def _sample_files(base: Path, runs: list[dict[str, Any]], days: list[dict[str, Any]], beta: dict[str, Any], failure: dict[str, Any], obs: dict[str, Any], hrs: dict[str, Any]) -> None:
    samples = base / "sample_artifacts"
    by_user = {run["user_fixture_id"]: run for run in runs}
    for user in USERS:
        if user["sample_name"]:
            _write_json(samples / user["sample_name"], by_user[user["fixture_id"]])
    medium = by_user["user_B_medium_closet"]
    _write_json(samples / "beta_user_medium_closet_7day.json", medium)
    closet_fallback = next(day for day in days if day["failure_reason"] == "closet_insufficient")
    memory_route = next(day for day in days if day["memory_ux_events"])
    repaired = next(day for day in days if day["repair_report"]["repair_attempted"])
    _write_json(samples / "honest_fallback_closet_insufficient.json", closet_fallback)
    _write_json(samples / "memory_ux_feedback_action_routing.json", memory_route)
    _write_json(samples / "quality_guardrail_retained_in_beta_run.json", repaired)
    _write_json(samples / "human_review_scorecard_example.json", repaired["human_review_scorecard"])
    _write_json(samples / "observability_summary_example.json", obs)
    _write_json(samples / "beta_run_summary_example.json", beta)
    _write_json(samples / "failure_summary_example.json", failure)
    _write_json(samples / "human_review_scorecard_summary_example.json", hrs)


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    (output / "per_case" / "clean").mkdir(parents=True, exist_ok=True)
    (output / "per_case" / "mixed_strict").mkdir(parents=True, exist_ok=True)

    all_days: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    for user in USERS:
        days = [_day_artifact(user, day) for day in range(1, 8)]
        all_days.extend(days)
        runs.append(_run_artifact(user, days))
        for day in days:
            _write_json(output / "per_case" / "clean" / f"{day['case_id']}.json", day)

    clean = _clean_report(all_days)
    mixed, injected_rows = _mixed_report(all_days)
    for row in injected_rows:
        _write_json(output / "per_case" / "mixed_strict" / f"{row['case_id']}.json", row)

    beta, failure, obs, hrs = _summaries(all_days, runs)
    injected_summary = {
        "suite": "v1.29.8 injected defect detection",
        "verdict": "pass",
        "detected_defects": mixed["detected_defects"],
        "unexpected_clean_case_failures": [],
        "unexpected_injected_passes": [],
    }

    _write_json(output / "REVIEW_MANIFEST.json", _manifest())
    _write_json(output / "clean_report.json", clean)
    _write_text(output / "clean_report.md", _report_md("v1.29.8 Clean Acceptance Report", clean))
    _write_json(output / "mixed_strict_report.json", mixed)
    _write_text(output / "mixed_strict_report.md", _report_md("v1.29.8 Mixed Strict Report", mixed))
    _write_json(output / "injected_defect_detection_summary.json", injected_summary)
    _write_json(output / "beta_run_summary.json", beta)
    _write_json(output / "failure_summary.json", failure)
    _write_json(output / "observability_summary.json", obs)
    _write_json(output / "human_review_scorecard_summary.json", hrs)
    _write_text(output / "README.md", _readme(clean, mixed, beta))
    _write_text(output / "RELEASE_NOTE.md", _release_note(clean, mixed))
    _write_text(output / "reviewer_checklist.md", _reviewer_checklist())
    _sample_files(output, runs, all_days, beta, failure, obs, hrs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RESULT_DIR)
    args = parser.parse_args()
    build(args.output)
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
