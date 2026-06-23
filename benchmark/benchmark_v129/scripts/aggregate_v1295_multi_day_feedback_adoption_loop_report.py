"""Aggregate v1.29.5 Multi-Day Feedback & Adoption Loop reports."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable


BENCHMARK_ID = "v1.29.5.multi_day_feedback_adoption_loop"

THRESHOLDS = {
    "multi_day_run_schema_valid_rate": 1.0,
    "daily_artifact_schema_valid_rate": 1.0,
    "daily_outfit_card_schema_valid_rate": 1.0,
    "multi_day_outfits_use_only_closet_items_rate": 1.0,
    "multi_day_swap_options_grounded_in_closet_rate": 1.0,
    "wear_this_updates_outfit_history_rate": 1.0,
    "wear_this_no_direct_global_memory_rate": 1.0,
    "save_not_treated_as_wear_this_rate": 1.0,
    "skip_without_reason_no_hard_avoid_rate": 1.0,
    "swap_item_slot_level_feedback_rate": 1.0,
    "current_exception_expires_after_task_rate": 1.0,
    "current_exception_not_globalized_multiday_rate": 1.0,
    "old_contextual_avoid_preserved_after_exception_rate": 1.0,
    "contextual_memory_applies_in_matching_context_rate": 1.0,
    "contextual_memory_excluded_in_mismatching_context_rate": 1.0,
    "contextual_mismatch_reason_recorded_rate": 1.0,
    "do_not_remember_no_production_write_rate": 1.0,
    "rejected_proposal_not_reused_across_days_rate": 1.0,
    "response_does_not_claim_rejected_memory_rate": 1.0,
    "correction_supersedes_wrong_proposal_rate": 1.0,
    "deprecated_wrong_proposal_not_consumed_later_rate": 1.0,
    "corrected_interpretation_used_later_rate": 1.0,
    "exact_outfit_not_repeated_without_reason_rate": 1.0,
    "recent_outfit_history_in_trace_rate": 1.0,
    "repeat_allowed_reason_present_rate": 1.0,
    "final_memory_snapshot_matches_timeline_rate": 1.0,
    "memory_evolution_event_order_valid_rate": 1.0,
    "temporary_memory_expiry_recorded_rate": 1.0,
    "no_memory_drift_from_unrelated_adoption_signals_rate": 1.0,
    "multi_day_response_claim_trace_coverage_rate": 1.0,
    "no_blocked_review_shadow_rejected_memory_claim_rate": 1.0,
    "active_memory_has_authorized_source_rate": 1.0,
    "corrected_memory_activation_has_write_gate_or_session_scope_rate": 1.0,
    "final_snapshot_no_unauthorized_active_memory_rate": 1.0,
    "post_day_store_snapshot_includes_allowed_commits_rate": 1.0,
    "next_day_pre_store_snapshot_matches_previous_post_store_snapshot_rate": 1.0,
    "task_active_snapshot_scope_labeled_rate": 1.0,
    "store_snapshot_task_active_snapshot_not_conflated_rate": 1.0,
    "adoption_event_context_matches_task_context_rate": 1.0,
    "consumed_contextual_memory_context_match_rate": 1.0,
    "response_claim_context_authorized_rate": 1.0,
    "corrected_contextual_memory_later_use_has_context_proof_rate": 1.0,
}

EXPECTED_DEFECTS = {
    "wear_this_creates_global_preference_without_confirmation": ["wear_this_no_direct_global_memory_rate", "no_memory_drift_from_unrelated_adoption_signals_rate"],
    "skip_creates_hard_avoid_without_reason": ["skip_without_reason_no_hard_avoid_rate"],
    "current_exception_persists_next_day": ["current_exception_expires_after_task_rate", "temporary_memory_expiry_recorded_rate"],
    "do_not_remember_reused_on_day7": ["rejected_proposal_not_reused_across_days_rate", "response_does_not_claim_rejected_memory_rate"],
    "contextual_memory_applied_to_wrong_context": ["contextual_memory_excluded_in_mismatching_context_rate"],
    "deprecated_wrong_proposal_consumed_later": ["deprecated_wrong_proposal_not_consumed_later_rate"],
    "exact_outfit_repeated_without_reason": ["exact_outfit_not_repeated_without_reason_rate", "repeat_allowed_reason_present_rate"],
    "second_day_response_claims_untraced_memory": ["multi_day_response_claim_trace_coverage_rate"],
    "save_treated_as_wear_this": ["save_not_treated_as_wear_this_rate"],
    "correction_does_not_supersede_wrong_proposal": ["correction_supersedes_wrong_proposal_rate"],
    "final_memory_snapshot_mismatches_timeline": ["final_memory_snapshot_matches_timeline_rate"],
    "temporary_exception_not_expired": ["temporary_memory_expiry_recorded_rate", "current_exception_expires_after_task_rate"],
    "corrected_memory_active_without_write_gate": [
        "active_memory_has_authorized_source_rate",
        "corrected_memory_activation_has_write_gate_or_session_scope_rate",
        "final_snapshot_no_unauthorized_active_memory_rate",
    ],
    "adoption_event_wrong_context": ["adoption_event_context_matches_task_context_rate"],
    "post_day_snapshot_missing_allowed_commit": ["post_day_store_snapshot_includes_allowed_commits_rate"],
    "pre_post_store_snapshot_discontinuity_without_event": ["next_day_pre_store_snapshot_matches_previous_post_store_snapshot_rate"],
    "corrected_contextual_memory_consumed_outside_committed_context": [
        "consumed_contextual_memory_context_match_rate",
        "response_claim_context_authorized_rate",
        "corrected_contextual_memory_later_use_has_context_proof_rate",
    ],
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
    per_case = os.path.join(path, "per_case")
    rows = []
    for name in sorted(os.listdir(per_case)):
        if name.endswith(".json"):
            with open(os.path.join(per_case, name), encoding="utf-8") as f:
                rows.append(json.load(f))
    return rows


def _days(row: dict[str, Any]) -> list[dict[str, Any]]:
    return list(row.get("days") or [])


def _closet_ids(row: dict[str, Any]) -> set[str]:
    return {item.get("item_id") for item in (row.get("closet_fixture_snapshot") or {}).get("closet_items", []) if item.get("item_id")}


def _item_ids(day: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in (day.get("daily_outfit_card") or {}).get("outfit_items", []) if item.get("item_id")]


def _swap_ids(day: dict[str, Any]) -> list[str]:
    return [item.get("item_id") for item in (day.get("daily_outfit_card") or {}).get("swap_options", []) if item.get("item_id")]


def _claim_refs(day: dict[str, Any]) -> list[str]:
    card = day.get("daily_outfit_card") or {}
    refs = [item.get("claim_ref") for item in card.get("why_this_works", []) if item.get("claim_ref")]
    refs += [item.get("claim_ref") for item in card.get("swap_options", []) if item.get("claim_ref")]
    return [ref for ref in refs if ref]


def _response_and_ux_claim_refs(day: dict[str, Any]) -> list[str]:
    refs = list((day.get("trace") or {}).get("response_claim_refs") or [])
    refs += _claim_refs(day)
    for block in day.get("memory_ux_blocks") or []:
        if block.get("claim_ref"):
            refs.append(block["claim_ref"])
    for event in day.get("memory_ux_events") or []:
        refs.extend(event.get("user_visible_claim_refs") or [])
    return [ref for ref in refs if ref]


def _all_consumed(row: dict[str, Any]) -> set[str]:
    return {mid for day in _days(row) for mid in (day.get("task_memory_packet") or {}).get("consumed_memory_ids", [])}


def _rejected_ids(row: dict[str, Any]) -> set[str]:
    return set((row.get("multi_day_trace") or {}).get("rejected_proposal_ids") or []) | set((row.get("final_memory_snapshot") or {}).get("rejected_proposal_ids") or [])


def _deprecated_ids(row: dict[str, Any]) -> set[str]:
    return set((row.get("multi_day_trace") or {}).get("deprecated_proposal_ids") or []) | set((row.get("final_memory_snapshot") or {}).get("deprecated_proposal_ids") or [])


def _derived_final_active(row: dict[str, Any]) -> set[str]:
    active = set()
    for event in row.get("memory_evolution_timeline") or []:
        if event.get("event") == "initial_memory_active" and event.get("memory_id"):
            active.add(event["memory_id"])
        if event.get("event") in {"production_write_allowed", "corrected_memory_created"} and event.get("committed_memory_id"):
            active.add(event["committed_memory_id"])
        if event.get("event") in {"proposal_rejected", "proposal_deprecated"} and event.get("proposal_id"):
            active.discard(event["proposal_id"])
    return active


def _active_final_ids(row: dict[str, Any]) -> set[str]:
    final = row.get("final_memory_snapshot") or {}
    return set(final.get("active_production_memory_ids") or final.get("active_memory_ids") or [])


def _allowed_write_commits(row: dict[str, Any]) -> dict[str, str]:
    commits = {}
    for day in _days(row):
        for dec in day.get("write_gate_decisions") or []:
            if dec.get("status") != "allowed" or dec.get("production_store_write_executed") is False:
                continue
            committed = []
            if dec.get("committed_memory_id"):
                committed.append(dec["committed_memory_id"])
            committed.extend(dec.get("committed_memory_ids") or [])
            for mid in committed:
                commits[mid] = dec.get("write_gate_decision_id")
    return commits


def _committed_memory_metadata(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for day in _days(row):
        for dec in day.get("write_gate_decisions") or []:
            committed = []
            if dec.get("committed_memory_id"):
                committed.append(dec["committed_memory_id"])
            committed.extend(dec.get("committed_memory_ids") or [])
            for mid in committed:
                item = metadata.setdefault(mid, {})
                if dec.get("committed_scope"):
                    item["scope"] = dec.get("committed_scope")
                if dec.get("committed_contexts"):
                    item["committed_contexts"] = list(dec.get("committed_contexts") or [])
                if dec.get("memory_proposal_ref"):
                    item["memory_proposal_ref"] = dec.get("memory_proposal_ref")
                if dec.get("write_gate_decision_id"):
                    item["write_gate_decision_id"] = dec.get("write_gate_decision_id")
                item["committed_day_index"] = day.get("day_index")
    for event in row.get("memory_evolution_timeline") or []:
        mid = event.get("committed_memory_id")
        if not mid:
            continue
        item = metadata.setdefault(mid, {})
        if event.get("scope"):
            item["scope"] = event.get("scope")
        if event.get("proposal_id"):
            item["memory_proposal_ref"] = event.get("proposal_id")
        if event.get("day_index") is not None:
            item.setdefault("committed_day_index", event.get("day_index"))
    return metadata


def _context_match_proof(day: dict[str, Any], memory_id: str) -> dict[str, Any]:
    packet = day.get("task_memory_packet") or {}
    trace = day.get("trace") or {}
    return (
        (packet.get("memory_context_match_proof") or {}).get(memory_id)
        or (trace.get("memory_context_match_proof") or {}).get(memory_id)
        or {}
    )


def _response_claim_authorization(day: dict[str, Any], memory_id: str) -> dict[str, Any]:
    trace = day.get("trace") or {}
    return (trace.get("response_claim_context_authorization") or {}).get(memory_id) or {}


def _context_authorized(day: dict[str, Any], memory_id: str, committed_contexts: set[str], *, allow_response_auth: bool = False) -> bool:
    if not committed_contexts:
        return True
    task_context = day.get("task_context") or {}
    if task_context.get("occasion") in committed_contexts:
        return True
    if set(task_context.get("context_tags") or []) & committed_contexts:
        return True
    proof = _context_match_proof(day, memory_id)
    if (
        proof.get("authorized_for_current_task") is True
        and proof.get("matched_context") in committed_contexts
    ):
        return True
    if allow_response_auth:
        auth = _response_claim_authorization(day, memory_id)
        if (
            auth.get("authorized_for_current_task") is True
            and auth.get("matched_context") in committed_contexts
        ):
            return True
    return False


def _explicit_context_proof(day: dict[str, Any], memory_id: str, committed_contexts: set[str]) -> bool:
    proof = _context_match_proof(day, memory_id)
    return (
        proof.get("authorized_for_current_task") is True
        and proof.get("matched_context") in committed_contexts
        and bool(proof.get("task_context_tags") or proof.get("task_occasion"))
    )


def _initial_active_ids(row: dict[str, Any]) -> set[str]:
    initial = set((row.get("initial_memory_snapshot") or {}).get("active_memories") or [])
    initial |= {
        event.get("memory_id")
        for event in row.get("memory_evolution_timeline") or []
        if event.get("event") == "initial_memory_active" and event.get("memory_id")
    }
    return initial


def _run_schema(row: dict[str, Any]) -> bool:
    required = {"multi_day_run_id", "schema_version", "user_fixture_id", "closet_fixture_id", "initial_memory_fixture_id", "days", "outfit_history", "memory_evolution_timeline", "adoption_summary", "final_memory_snapshot", "multi_day_trace"}
    return required <= set(row) and row.get("schema_version") == "v1.29.5" and bool(row.get("days"))


def _daily_schema(row: dict[str, Any]) -> bool:
    required = {"day_index", "date_label", "task_context", "pre_day_memory_snapshot", "task_memory_packet", "daily_outfit_card", "user_adoption_event", "post_day_memory_snapshot", "outfit_history_update", "trace"}
    return all(required <= set(day) and day.get("schema_version") == "v1.29.5" for day in _days(row))


def _card_schema(row: dict[str, Any]) -> bool:
    required = {"card_id", "headline", "direction", "outfit_items", "why_this_works", "feedback_actions"}
    return all(required <= set(day.get("daily_outfit_card") or {}) and _item_ids(day) for day in _days(row))


def _outfits_grounded(row: dict[str, Any]) -> bool:
    ids = _closet_ids(row)
    return all(all(item_id in ids for item_id in _item_ids(day)) for day in _days(row))


def _swaps_grounded(row: dict[str, Any]) -> bool:
    ids = _closet_ids(row)
    return all(all(item_id in ids for item_id in _swap_ids(day)) for day in _days(row))


def _wear_updates_history(row: dict[str, Any]) -> bool:
    wear_days = [day for day in _days(row) if (day.get("user_adoption_event") or {}).get("event_type") == "wear_this"]
    return bool(wear_days) and all((day.get("outfit_history_update") or {}).get("created_history_entry") is True for day in wear_days)


def _wear_no_global(row: dict[str, Any]) -> bool:
    return all(
        (day.get("user_adoption_event") or {}).get("creates_global_memory_proposal") is not True
        for day in _days(row)
        if (day.get("user_adoption_event") or {}).get("event_type") == "wear_this"
    )


def _save_not_wear(row: dict[str, Any]) -> bool:
    return all(
        (day.get("user_adoption_event") or {}).get("treated_as_wear_this") is False
        and (day.get("outfit_history_update") or {}).get("created_history_entry") is False
        for day in _days(row)
        if (day.get("user_adoption_event") or {}).get("event_type") == "save"
    )


def _skip_no_hard(row: dict[str, Any]) -> bool:
    return all(
        (day.get("user_adoption_event") or {}).get("hard_avoid_created") is False
        for day in _days(row)
        if (day.get("user_adoption_event") or {}).get("event_type") == "skip"
    )


def _swap_slot_level(row: dict[str, Any]) -> bool:
    return all(
        (day.get("user_adoption_event") or {}).get("slot_level_feedback_only") is True
        and (day.get("outfit_history_update") or {}).get("created_history_entry") is False
        for day in _days(row)
        if (day.get("user_adoption_event") or {}).get("event_type") == "swap_item"
    )


def _exception_expires(row: dict[str, Any]) -> bool:
    trace = row.get("multi_day_trace") or {}
    created = set(trace.get("temporary_exception_ids") or [])
    expired = set(trace.get("expired_exception_ids") or [])
    if not created:
        return True
    if not created <= expired:
        return False
    for day in _days(row):
        if day.get("day_index", 0) > 2 and (day.get("task_memory_packet") or {}).get("temporary_exceptions"):
            return False
    return True


def _exception_not_global(row: dict[str, Any]) -> bool:
    for day in _days(row):
        for exc in (day.get("task_memory_packet") or {}).get("temporary_exceptions") or []:
            if exc.get("creates_global_preference") is True or exc.get("scope") != "this_task_only":
                return False
    return True


def _old_contextual_avoid_preserved(row: dict[str, Any]) -> bool:
    old_ids = set((row.get("initial_memory_snapshot") or {}).get("old_contextual_avoid_ids") or [])
    if not old_ids:
        return True
    return any(
        old_ids & set(exc.get("overrides_memory_ids") or [])
        and exc.get("old_memory_preserved") is True
        and bool(exc.get("residual_boundaries"))
        for day in _days(row)
        for exc in (day.get("task_memory_packet") or {}).get("temporary_exceptions") or []
    )


def _context_applies(row: dict[str, Any]) -> bool:
    return "mem_avoid_interview_formality" in ((row.get("multi_day_trace") or {}).get("consumed_memory_by_day") or {}).get("day_3", [])


def _context_excluded(row: dict[str, Any]) -> bool:
    for day_key in ("day_5", "day_7"):
        consumed = set(((row.get("multi_day_trace") or {}).get("consumed_memory_by_day") or {}).get(day_key, []))
        if "mem_avoid_interview_formality" in consumed:
            return False
    return True


def _context_reason(row: dict[str, Any]) -> bool:
    excluded = (row.get("multi_day_trace") or {}).get("excluded_memory_by_day") or {}
    reasons = [item.get("reason", "") for day in ("day_5", "day_7") for item in excluded.get(day, [])]
    return any("context_mismatch" in reason for reason in reasons)


def _dnr_no_write(row: dict[str, Any]) -> bool:
    actions = [action for day in _days(row) for action in day.get("user_memory_actions") or [] if action.get("action_type") == "do_not_remember"]
    return bool(actions) and all(action.get("production_store_write_attempted") is False and action.get("production_store_write_executed") is False and action.get("proposal_status") == "rejected" for action in actions)


def _rejected_not_reused(row: dict[str, Any]) -> bool:
    return not (_rejected_ids(row) & _all_consumed(row))


def _response_not_rejected(row: dict[str, Any]) -> bool:
    rejected = _rejected_ids(row)
    return all(not (set(_claim_refs(day)) & rejected) for day in _days(row))


def _correction_supersedes(row: dict[str, Any]) -> bool:
    deprecated = _deprecated_ids(row)
    actions = [action for day in _days(row) for action in day.get("user_memory_actions") or [] if action.get("action_type") == "correct_interpretation"]
    return bool(deprecated) and all(action.get("deprecated_memory_proposal_refs") for action in actions)


def _deprecated_not_consumed(row: dict[str, Any]) -> bool:
    return not (_deprecated_ids(row) & _all_consumed(row))


def _corrected_used(row: dict[str, Any]) -> bool:
    return "mem_corrected_running_shoe_boundary" in _all_consumed(row)


def _exact_repeat_no_reason(row: dict[str, Any]) -> bool:
    seen: dict[tuple[str, ...], int] = {}
    for day in _days(row):
        sig = tuple(_item_ids(day))
        idx = day.get("day_index", 0)
        if sig in seen and idx - seen[sig] <= 2:
            return False
        seen[sig] = idx
    for event in (row.get("multi_day_trace") or {}).get("repeat_outfit_events") or []:
        if not event.get("repeat_allowed_reason"):
            return False
    return True


def _recent_history_in_trace(row: dict[str, Any]) -> bool:
    return any((day.get("trace") or {}).get("recent_outfit_history") for day in _days(row) if day.get("day_index", 0) > 2)


def _repeat_reason(row: dict[str, Any]) -> bool:
    return all(event.get("repeat_allowed_reason") for event in (row.get("multi_day_trace") or {}).get("repeat_outfit_events") or [])


def _final_snapshot_matches(row: dict[str, Any]) -> bool:
    return set((row.get("final_memory_snapshot") or {}).get("active_memory_ids") or []) == _derived_final_active(row)


def _event_order(row: dict[str, Any]) -> bool:
    last = 0
    for event in row.get("memory_evolution_timeline") or []:
        day = event.get("day_index", 0)
        if day < last:
            return False
        last = day
    return True


def _temporary_expiry(row: dict[str, Any]) -> bool:
    final = row.get("final_memory_snapshot") or {}
    trace = row.get("multi_day_trace") or {}
    return set(trace.get("temporary_exception_ids") or []) <= set(trace.get("expired_exception_ids") or []) and set(trace.get("temporary_exception_ids") or []) <= set(final.get("expired_temporary_exception_ids") or [])


def _no_drift(row: dict[str, Any]) -> bool:
    derived = _derived_final_active(row)
    final = set((row.get("final_memory_snapshot") or {}).get("active_memory_ids") or [])
    adoption_global = any(
        event.get("event") == "direct_global_preference_created_from_wear_this"
        for event in row.get("memory_evolution_timeline") or []
    )
    return final == derived and not adoption_global


def _claim_trace_coverage(row: dict[str, Any]) -> bool:
    for day in _days(row):
        allowed = set((day.get("task_memory_packet") or {}).get("consumed_memory_ids") or [])
        allowed |= {ref for ref in (day.get("trace") or {}).get("response_claim_refs", []) if str(ref).startswith("current_task_evidence_")}
        if not set(_claim_refs(day)) <= allowed:
            return False
    return True


def _no_disallowed_claim(row: dict[str, Any]) -> bool:
    disallowed = _rejected_ids(row) | _deprecated_ids(row)
    trace = row.get("multi_day_trace") or {}
    for key in ("blocked_memory_claims", "review_required_memory_claims", "shadow_only_memory_claims"):
        disallowed |= set(trace.get(key) or [])
    return all(not (set(_claim_refs(day)) & disallowed) for day in _days(row))


def _active_memory_authorized(row: dict[str, Any]) -> bool:
    final = row.get("final_memory_snapshot") or {}
    auth = final.get("active_memory_authorization") or {}
    initial = _initial_active_ids(row)
    commits = _allowed_write_commits(row)
    for mid in _active_final_ids(row):
        item = auth.get(mid) or {}
        if item.get("authorized") is not True:
            return False
        source = item.get("source")
        if source == "initial_memory_fixture" and mid in initial:
            continue
        if source == "write_gate_allowed" and mid in commits and item.get("decision_id") == commits[mid]:
            continue
        if source == "session_runtime_with_expiry" and item.get("expires_after_run") is True:
            continue
        return False
    return True


def _corrected_activation_authorized(row: dict[str, Any]) -> bool:
    target = "mem_corrected_running_shoe_boundary"
    consumed_later = any(
        day.get("day_index", 0) > 4
        and target in set((day.get("task_memory_packet") or {}).get("consumed_memory_ids") or [])
        for day in _days(row)
    )
    final_active = target in _active_final_ids(row)
    if not consumed_later and not final_active:
        return True
    commits = _allowed_write_commits(row)
    if target in commits:
        return True
    final = row.get("final_memory_snapshot") or {}
    session_ids = set(final.get("active_session_correction_ids") or [])
    return "prop_corrected_running_shoe_boundary" in session_ids and bool(final.get("session_correction_expiry"))


def _final_no_unauthorized(row: dict[str, Any]) -> bool:
    return _active_memory_authorized(row)


def _post_store_includes_commits(row: dict[str, Any]) -> bool:
    for day in _days(row):
        post_ids = set((day.get("post_day_store_memory_snapshot") or {}).get("active_memory_ids") or [])
        for dec in day.get("write_gate_decisions") or []:
            if dec.get("status") != "allowed":
                continue
            committed = []
            if dec.get("committed_memory_id"):
                committed.append(dec["committed_memory_id"])
            committed.extend(dec.get("committed_memory_ids") or [])
            for mid in committed:
                if mid not in post_ids:
                    return False
    return True


def _store_snapshot_continuity(row: dict[str, Any]) -> bool:
    days = _days(row)
    for prev, cur in zip(days, days[1:]):
        prev_ids = set((prev.get("post_day_store_memory_snapshot") or {}).get("active_memory_ids") or [])
        cur_ids = set((cur.get("pre_day_store_memory_snapshot") or {}).get("active_memory_ids") or [])
        if prev_ids != cur_ids:
            transitions = cur.get("state_transition_events") or cur.get("memory_evolution_events") or []
            if not transitions:
                return False
    return True


def _task_active_scope_labeled(row: dict[str, Any]) -> bool:
    for day in _days(row):
        occasion = (day.get("task_context") or {}).get("occasion")
        for key in ("pre_day_task_active_memory_snapshot", "post_day_task_active_memory_snapshot"):
            snap = day.get(key) or {}
            if (snap.get("task_context") or {}).get("occasion") != occasion:
                return False
            if "excluded_memory_ids" not in snap or "exclusion_reasons" not in snap:
                return False
    return True


def _snapshots_not_conflated(row: dict[str, Any]) -> bool:
    required = {
        "pre_day_store_memory_snapshot",
        "post_day_store_memory_snapshot",
        "pre_day_task_active_memory_snapshot",
        "post_day_task_active_memory_snapshot",
    }
    return all(required <= set(day) for day in _days(row))


def _adoption_context_matches(row: dict[str, Any]) -> bool:
    for day in _days(row):
        adoption = day.get("user_adoption_event") or {}
        if not adoption or adoption.get("event_type") == "no_action":
            continue
        if adoption.get("cross_task_feedback") is True:
            continue
        if adoption.get("occasion") != (day.get("task_context") or {}).get("occasion"):
            return False
    return True


def _consumed_contextual_memory_context_match(row: dict[str, Any]) -> bool:
    metadata = _committed_memory_metadata(row)
    for day in _days(row):
        consumed = set((day.get("task_memory_packet") or {}).get("consumed_memory_ids") or [])
        for mid in consumed:
            meta = metadata.get(mid) or {}
            if meta.get("scope") != "contextual":
                continue
            contexts = set(meta.get("committed_contexts") or [])
            if not _context_authorized(day, mid, contexts):
                return False
    return True


def _response_claim_context_authorized(row: dict[str, Any]) -> bool:
    metadata = _committed_memory_metadata(row)
    for day in _days(row):
        for mid in set(_response_and_ux_claim_refs(day)):
            meta = metadata.get(mid) or {}
            if meta.get("scope") != "contextual":
                continue
            contexts = set(meta.get("committed_contexts") or [])
            if not _context_authorized(day, mid, contexts, allow_response_auth=True):
                return False
    return True


def _corrected_contextual_later_use_has_context_proof(row: dict[str, Any]) -> bool:
    metadata = _committed_memory_metadata(row)
    corrected_ids = {
        mid
        for mid, meta in metadata.items()
        if meta.get("scope") == "contextual"
        and "corrected" in str(meta.get("memory_proposal_ref") or "")
    }
    for mid in corrected_ids:
        meta = metadata.get(mid) or {}
        committed_day = meta.get("committed_day_index") or 0
        contexts = set(meta.get("committed_contexts") or [])
        for day in _days(row):
            if day.get("day_index", 0) <= committed_day:
                continue
            consumed = set((day.get("task_memory_packet") or {}).get("consumed_memory_ids") or [])
            claimed = set(_response_and_ux_claim_refs(day))
            if mid in consumed or mid in claimed:
                if not _explicit_context_proof(day, mid, contexts):
                    return False
    return True


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "multi_day_run_schema_valid_rate": _run_schema,
    "daily_artifact_schema_valid_rate": _daily_schema,
    "daily_outfit_card_schema_valid_rate": _card_schema,
    "multi_day_outfits_use_only_closet_items_rate": _outfits_grounded,
    "multi_day_swap_options_grounded_in_closet_rate": _swaps_grounded,
    "wear_this_updates_outfit_history_rate": _wear_updates_history,
    "wear_this_no_direct_global_memory_rate": _wear_no_global,
    "save_not_treated_as_wear_this_rate": _save_not_wear,
    "skip_without_reason_no_hard_avoid_rate": _skip_no_hard,
    "swap_item_slot_level_feedback_rate": _swap_slot_level,
    "current_exception_expires_after_task_rate": _exception_expires,
    "current_exception_not_globalized_multiday_rate": _exception_not_global,
    "old_contextual_avoid_preserved_after_exception_rate": _old_contextual_avoid_preserved,
    "contextual_memory_applies_in_matching_context_rate": _context_applies,
    "contextual_memory_excluded_in_mismatching_context_rate": _context_excluded,
    "contextual_mismatch_reason_recorded_rate": _context_reason,
    "do_not_remember_no_production_write_rate": _dnr_no_write,
    "rejected_proposal_not_reused_across_days_rate": _rejected_not_reused,
    "response_does_not_claim_rejected_memory_rate": _response_not_rejected,
    "correction_supersedes_wrong_proposal_rate": _correction_supersedes,
    "deprecated_wrong_proposal_not_consumed_later_rate": _deprecated_not_consumed,
    "corrected_interpretation_used_later_rate": _corrected_used,
    "exact_outfit_not_repeated_without_reason_rate": _exact_repeat_no_reason,
    "recent_outfit_history_in_trace_rate": _recent_history_in_trace,
    "repeat_allowed_reason_present_rate": _repeat_reason,
    "final_memory_snapshot_matches_timeline_rate": _final_snapshot_matches,
    "memory_evolution_event_order_valid_rate": _event_order,
    "temporary_memory_expiry_recorded_rate": _temporary_expiry,
    "no_memory_drift_from_unrelated_adoption_signals_rate": _no_drift,
    "multi_day_response_claim_trace_coverage_rate": _claim_trace_coverage,
    "no_blocked_review_shadow_rejected_memory_claim_rate": _no_disallowed_claim,
    "active_memory_has_authorized_source_rate": _active_memory_authorized,
    "corrected_memory_activation_has_write_gate_or_session_scope_rate": _corrected_activation_authorized,
    "final_snapshot_no_unauthorized_active_memory_rate": _final_no_unauthorized,
    "post_day_store_snapshot_includes_allowed_commits_rate": _post_store_includes_commits,
    "next_day_pre_store_snapshot_matches_previous_post_store_snapshot_rate": _store_snapshot_continuity,
    "task_active_snapshot_scope_labeled_rate": _task_active_scope_labeled,
    "store_snapshot_task_active_snapshot_not_conflated_rate": _snapshots_not_conflated,
    "adoption_event_context_matches_task_context_rate": _adoption_context_matches,
    "consumed_contextual_memory_context_match_rate": _consumed_contextual_memory_context_match,
    "response_claim_context_authorized_rate": _response_claim_context_authorized,
    "corrected_contextual_memory_later_use_has_context_proof_rate": _corrected_contextual_later_use_has_context_proof,
}


def _case_failures(row: dict[str, Any]) -> list[str]:
    return [cid for cid, fn in CHECKS.items() if not fn(row)]


def _aggregate(rows: list[dict[str, Any]], suite_mode: str) -> dict[str, Any]:
    checks = []
    for cid, fn in CHECKS.items():
        passed_count = sum(1 for row in rows if fn(row))
        value = _rate(passed_count, len(rows))
        checks.append({"check_id": cid, "value": value, "threshold": THRESHOLDS[cid], "passed": value >= THRESHOLDS[cid], "numerator": passed_count, "denominator": len(rows)})

    case_results = []
    for row in rows:
        failed = _case_failures(row)
        case_results.append({
            "case_id": row.get("case_id"),
            "scenario": row.get("scenario"),
            "is_injected_defect": row.get("is_injected_defect") is True,
            "defect_type": row.get("defect_type"),
            "passed": not failed,
            "failed_check_ids": failed,
            "raw_artifact_ref": f"per_case/{row.get('case_id')}.json",
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
        detected = bool(set(expected) & set(failed))
        detected_defects.append({
            "case_id": result.get("case_id"),
            "defect_type": defect_type,
            "expected_failure": True,
            "actual_failure": bool(failed),
            "detected": detected,
            "failed_check_ids": failed,
            "expected_failed_check_ids": expected,
            "failure_reason": f"Detected seeded defect: {defect_type}",
            "raw_artifact_ref": result.get("raw_artifact_ref"),
        })

    failed_gates = [c["check_id"] for c in checks if not c["passed"]]
    clean_pass = not failed_gates and not unexpected_clean
    injected_pass = bool(detected_defects) and all(d["detected"] for d in detected_defects) and not unexpected_clean and not unexpected_injected_passes
    if suite_mode == "clean_acceptance":
        verdicts = {
            "clean_acceptance_verdict": "pass" if clean_pass else "fail",
            "mixed_strict_verdict": "not_applicable",
            "injected_defect_detection_verdict": "not_applicable",
            "release_candidate_verdict": "pass_candidate" if clean_pass else "fail",
        }
    else:
        verdicts = {
            "clean_acceptance_verdict": "not_applicable",
            "mixed_strict_verdict": "fail" if failed_gates else "pass",
            "injected_defect_detection_verdict": "pass" if injected_pass else "fail",
            "release_candidate_verdict": "not_applicable",
        }
    return {
        "benchmark_id": BENCHMARK_ID,
        "artifact_schema_version": "v1.29.5",
        "generated_at": _now_iso(),
        "raw_first": True,
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
        "failed_gates": failed_gates,
        "case_results": case_results,
        "detected_defects": detected_defects,
        "unexpected_clean_case_failures": unexpected_clean,
        "unexpected_injected_passes": unexpected_injected_passes,
    }


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_md(path: str, report: dict[str, Any]) -> None:
    summary = report.get("suite_summary") or {}
    verdicts = report.get("verdicts") or {}
    lines = [
        "# v1.29.5 Multi-Day Feedback & Adoption Loop Report",
        "",
        f"- suite_mode: `{summary.get('suite_mode')}`",
        f"- cases: {summary.get('total_cases')}",
        f"- checks: {summary.get('passed_checks')} / {summary.get('total_checks')} PASS",
        f"- failed_checks: {summary.get('failed_checks')}",
        f"- clean_acceptance_verdict: `{verdicts.get('clean_acceptance_verdict')}`",
        f"- mixed_strict_verdict: `{verdicts.get('mixed_strict_verdict')}`",
        f"- injected_defect_detection_verdict: `{verdicts.get('injected_defect_detection_verdict')}`",
        f"- release_candidate_verdict: `{verdicts.get('release_candidate_verdict')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks") or []:
        lines.append(f"- `{check.get('check_id')}`: {check.get('value')} ({'PASS' if check.get('passed') else 'FAIL'})")
    lines.extend(["", "## Detected Defects", ""])
    defects = report.get("detected_defects") or []
    if defects:
        for defect in defects:
            lines.append(f"- `{defect.get('case_id')}` `{defect.get('defect_type')}`: {'detected' if defect.get('detected') else 'missed'}")
    else:
        lines.append("- None")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--suite-mode", required=True, choices=["clean_acceptance", "mixed_strict_with_injected"])
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()
    rows = _load_raw_dir(args.raw_dir)
    report = _aggregate(rows, args.suite_mode)
    _write_json(args.out_json, report)
    _write_md(args.out_md, report)
    print(json.dumps(report["suite_summary"], indent=2))


if __name__ == "__main__":
    main()
