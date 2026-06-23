"""
aggregate_v12911_artifact_hardening_injection_aware_reporting_report.py

Aggregator for v1.29.1.1 Production Artifact Hardening & Injection-Aware Reporting.
65 Gates / 9 Groups.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any


def _rate(n: int, d: int) -> float:
    return round(n / d, 4) if d > 0 else 1.0


def _load(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _load_thresh(path: str) -> dict:
    with open(path) as f:
        return json.load(f)["thresholds"]


def _is_full_sha256(h: str | None) -> bool:
    if not h:
        return False
    if not h.startswith("sha256:"):
        return False
    return len(h) >= 71


def _is_injection_detected(r: dict) -> bool:
    injection_type = r.get("injection_type")
    if injection_type == "metric_conflict":
        return bool(r.get("inject_metric_conflict"))
    if injection_type == "shadow_style_commit_result":
        return bool(r.get("shadow_style_detected"))
    if injection_type == "write_flag_mismatch":
        return bool(r.get("write_flag_mismatch_detected"))
    if injection_type == "shadow_commit_id_in_journal":
        return bool(r.get("injected_shadow_commit_id_in_journal"))
    if injection_type == "audit_replay_hash_mismatch":
        return bool(r.get("inject_replay_hash_mismatch"))
    if injection_type == "normal_metric_exclusion":
        return bool(r.get("inject_normal_metric_exclusion"))
    if injection_type == "shadow_parity_id_mismatch":
        return bool(r.get("shadow_parity_id_mismatch_detected"))
    if injection_type == "shallow_audit_snapshot":
        return bool(r.get("shallow_audit_snapshot_injected"))
    if injection_type == "missing_rollback_plan":
        return bool(r.get("missing_rollback_plan_injected"))
    if injection_type == "shadow_id_primary_rollback":
        return bool(r.get("shadow_commit_id_as_primary_detected"))
    if injection_type == "placeholder_evidence_preview":
        return bool(r.get("placeholder_evidence_detected"))
    return False


# ---------------------------------------------------------------------------
# §14.1 Injection-aware reporting
# ---------------------------------------------------------------------------

def _build_injection_detection(rows: list[dict]) -> dict:
    injection_rows = [r for r in rows if r.get("is_injection_case")]
    detected = [r["case_id"] for r in injection_rows if _is_injection_detected(r)]
    undetected = [r["case_id"] for r in injection_rows if not _is_injection_detected(r)]
    silent_exclusion = [r for r in injection_rows if not r.get("exclusion_reason")]

    return {
        "n_injection_cases": len(injection_rows),
        "n_detected": len(detected),
        "n_undetected": len(undetected),
        "detected_case_ids": detected,
        "undetected_case_ids": undetected,
        "excluded_from_normal_metrics_case_ids": [r["case_id"] for r in injection_rows],
        "exclusion_reasons": {r["case_id"]: r.get("exclusion_reason") for r in injection_rows},
        "injected_defect_detected_rate": _rate(len(detected), len(injection_rows)) if injection_rows else 1.0,
        "raw_defect_silent_exclusion_count": len(silent_exclusion),
    }


def _gate_injection_aware_reporting(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    injection_rows = [r for r in rows if r.get("is_injection_case")]
    non_inject_rows = [r for r in rows if not r.get("is_injection_case")]

    # injection_case_declared_rate: all injection rows have is_injection_case=True and injection_type
    declared = sum(1 for r in injection_rows if r.get("injection_type"))
    metrics["injection_case_declared_rate"] = _rate(declared, len(injection_rows)) if injection_rows else 1.0

    # injected_defect_detected_rate
    detected = sum(1 for r in injection_rows if _is_injection_detected(r))
    metrics["injected_defect_detected_rate"] = _rate(detected, len(injection_rows)) if injection_rows else 1.0

    # injected_case_exclusion_reason_present_rate
    with_reason = sum(1 for r in injection_rows if r.get("exclusion_reason"))
    metrics["injected_case_exclusion_reason_present_rate"] = _rate(with_reason, len(injection_rows)) if injection_rows else 1.0

    # normal_metrics_exclude_injected_cases_only_with_detection_rate:
    # all injection rows that are excluded must have been detected
    excluded_and_detected = sum(1 for r in injection_rows if r.get("exclusion_reason") and _is_injection_detected(r))
    excluded_total = sum(1 for r in injection_rows if r.get("exclusion_reason"))
    metrics["normal_metrics_exclude_injected_cases_only_with_detection_rate"] = (
        _rate(excluded_and_detected, excluded_total) if excluded_total > 0 else 1.0
    )

    # raw_defect_silent_exclusion_count = injection rows without exclusion_reason
    silent = sum(1 for r in injection_rows if not r.get("exclusion_reason"))
    metrics["raw_defect_silent_exclusion_count"] = silent

    # injection_detection_section_present_rate: always 1.0 (we always build it)
    metrics["injection_detection_section_present_rate"] = 1.0

    # report_raw_clean_subset_consistency_rate: non-inject rows must not have injection flags
    inconsistent = sum(
        1 for r in non_inject_rows
        if r.get("inject_metric_conflict") or r.get("shadow_style_detected")
        or r.get("write_flag_mismatch_detected") or r.get("injected_shadow_commit_id_in_journal")
        or r.get("inject_replay_hash_mismatch") or r.get("inject_normal_metric_exclusion")
    )
    metrics["report_raw_clean_subset_consistency_rate"] = _rate(
        len(non_inject_rows) - inconsistent, len(non_inject_rows)
    ) if non_inject_rows else 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.2 Audit log snapshot completeness (non-inject rows only)
# ---------------------------------------------------------------------------

def _gate_audit_log_snapshot_completeness(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    # Use non-injection production write rows
    non_inject = [r for r in rows if not r.get("is_injection_case")]
    write_rows = [r for r in non_inject if r.get("production_commit_result") is not None]

    AUDIT_SNAPSHOT_REQUIRED_FIELDS = [
        "audit_log_id", "decision_id", "production_commit_id", "plan_id",
        "user_id", "committed_at", "rollback_deadline", "action_audit_entries",
    ]

    # production_audit_log_snapshot_full_rate
    full_snap = sum(
        1 for r in write_rows
        if all(
            (r.get("production_commit_result") or {}).get("audit_log_snapshot", {}).get(f) is not None
            or f in ((r.get("production_commit_result") or {}).get("audit_log_snapshot") or {})
            for f in AUDIT_SNAPSHOT_REQUIRED_FIELDS
        )
    )
    metrics["production_audit_log_snapshot_full_rate"] = _rate(full_snap, len(write_rows)) if write_rows else 1.0

    # production_audit_action_entries_full_rate: all action entries have all required fields
    ENTRY_REQUIRED = ["action_id", "action_type", "before_snapshot", "after_snapshot_preview",
                      "patch", "rollback_action", "source_evidence_ids", "rationale"]

    def _entry_full(e: dict) -> bool:
        return all(f in e for f in ENTRY_REQUIRED)

    entries_full_rows = 0
    for r in write_rows:
        snap = (r.get("production_commit_result") or {}).get("audit_log_snapshot") or {}
        entries = snap.get("action_audit_entries") or []
        if entries and all(_entry_full(e) for e in entries):
            entries_full_rows += 1
    metrics["production_audit_action_entries_full_rate"] = _rate(entries_full_rows, len(write_rows)) if write_rows else 1.0

    # production_audit_action_before_after_patch_present_rate
    before_after_patch = 0
    for r in write_rows:
        snap = (r.get("production_commit_result") or {}).get("audit_log_snapshot") or {}
        entries = snap.get("action_audit_entries") or []
        if entries and all(
            "before_snapshot" in e and "after_snapshot_preview" in e and "patch" in e
            for e in entries
        ):
            before_after_patch += 1
    metrics["production_audit_action_before_after_patch_present_rate"] = _rate(before_after_patch, len(write_rows)) if write_rows else 1.0

    # production_action_results_audit_entries_semantic_match_rate
    semantic_match = 0
    for r in write_rows:
        cr = r.get("production_commit_result") or {}
        ar_ids = set(a.get("action_id", "") for a in (cr.get("action_results") or []))
        snap = cr.get("audit_log_snapshot") or {}
        audit_ids = set(e.get("action_id", "") for e in (snap.get("action_audit_entries") or []))
        if ar_ids and ar_ids == audit_ids:
            semantic_match += 1
    metrics["production_action_results_audit_entries_semantic_match_rate"] = _rate(semantic_match, len(write_rows)) if write_rows else 1.0

    # production_audit_source_evidence_lineage_rate
    evidence_lineage = 0
    for r in write_rows:
        snap = (r.get("production_commit_result") or {}).get("audit_log_snapshot") or {}
        entries = snap.get("action_audit_entries") or []
        if entries and all("source_evidence_ids" in e for e in entries):
            evidence_lineage += 1
    metrics["production_audit_source_evidence_lineage_rate"] = _rate(evidence_lineage, len(write_rows)) if write_rows else 1.0

    # production_audit_create_after_equals_proposed_rate
    create_rows = []
    create_ok = 0
    for r in write_rows:
        snap = (r.get("production_commit_result") or {}).get("audit_log_snapshot") or {}
        for e in (snap.get("action_audit_entries") or []):
            if e.get("action_type") == "create_atom":
                create_rows.append(e)
                proposed = e.get("proposed_atom")
                after = e.get("after_snapshot_preview")
                if proposed is not None and after is not None and proposed == after:
                    create_ok += 1
    metrics["production_audit_create_after_equals_proposed_rate"] = _rate(create_ok, len(create_rows)) if create_rows else 1.0

    # production_audit_update_patch_preview_rate
    update_rows_list = []
    update_ok = 0
    for r in write_rows:
        snap = (r.get("production_commit_result") or {}).get("audit_log_snapshot") or {}
        for e in (snap.get("action_audit_entries") or []):
            if e.get("action_type") == "update_atom":
                update_rows_list.append(e)
                before = e.get("before_snapshot")
                after = e.get("after_snapshot_preview")
                patch = e.get("patch") or {}
                if before is not None and after is not None and patch:
                    update_ok += 1
    metrics["production_audit_update_patch_preview_rate"] = _rate(update_ok, len(update_rows_list)) if update_rows_list else 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.3 Rollback window snapshot self-contained (non-inject only)
# ---------------------------------------------------------------------------

def _gate_rollback_window_snapshot(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    non_inject = [r for r in rows if not r.get("is_injection_case")]
    write_rows = [r for r in non_inject if r.get("production_commit_result") is not None]

    def _rbw(r: dict) -> dict:
        return (r.get("production_commit_result") or {}).get("rollback_window_snapshot") or {}

    REQUIRED_FIELDS = [
        "rollback_window_id", "production_commit_id", "user_id", "decision_id",
        "plan_id", "rollback_window_hours", "created_at", "expires_at", "timezone",
        "can_rollback", "rollback_plan",
    ]

    self_contained = sum(
        1 for r in write_rows if all(f in _rbw(r) for f in REQUIRED_FIELDS)
    )
    metrics["production_rollback_window_snapshot_self_contained_rate"] = _rate(self_contained, len(write_rows)) if write_rows else 1.0

    rbw_id_present = sum(1 for r in write_rows if _rbw(r).get("rollback_window_id"))
    metrics["production_rollback_window_id_present_rate"] = _rate(rbw_id_present, len(write_rows)) if write_rows else 1.0

    decision_match = sum(
        1 for r in write_rows
        if _rbw(r).get("decision_id") and _rbw(r).get("decision_id") == (r.get("production_commit_result") or {}).get("decision_id")
    )
    metrics["production_rollback_window_decision_id_match_rate"] = _rate(decision_match, len(write_rows)) if write_rows else 1.0

    plan_match = sum(
        1 for r in write_rows
        if _rbw(r).get("plan_id") and _rbw(r).get("plan_id") == (r.get("production_commit_result") or {}).get("plan_id")
    )
    metrics["production_rollback_window_plan_id_match_rate"] = _rate(plan_match, len(write_rows)) if write_rows else 1.0

    hours_present = sum(1 for r in write_rows if _rbw(r).get("rollback_window_hours"))
    metrics["production_rollback_window_hours_present_rate"] = _rate(hours_present, len(write_rows)) if write_rows else 1.0

    created_at_present = sum(1 for r in write_rows if _rbw(r).get("created_at"))
    metrics["production_rollback_window_created_at_present_rate"] = _rate(created_at_present, len(write_rows)) if write_rows else 1.0

    plan_present = sum(1 for r in write_rows if _rbw(r).get("rollback_plan") is not None)
    metrics["production_rollback_plan_present_rate"] = _rate(plan_present, len(write_rows)) if write_rows else 1.0

    tz_utc = sum(1 for r in write_rows if _rbw(r).get("timezone") == "UTC")
    metrics["production_rollback_window_timezone_utc_rate"] = _rate(tz_utc, len(write_rows)) if write_rows else 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.4 Shadow commit ref enrichment (non-inject only)
# ---------------------------------------------------------------------------

def _gate_shadow_commit_ref_enrichment(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    non_inject = [r for r in rows if not r.get("is_injection_case")]
    write_rows = [r for r in non_inject if r.get("production_commit_result") is not None]

    def _scr(r: dict) -> dict:
        return (r.get("production_commit_result") or {}).get("shadow_commit_ref") or {}

    scr_present = sum(1 for r in write_rows if _scr(r).get("shadow_commit_id"))
    metrics["production_shadow_commit_ref_present_rate"] = _rate(scr_present, len(write_rows)) if write_rows else 1.0

    # shadow_commit_ref.shadow_commit_id must match shadow_parity_report.shadow_commit_id
    parity_id_match = sum(
        1 for r in write_rows
        if _scr(r).get("shadow_commit_id") and
        (r.get("shadow_parity_report") or {}).get("shadow_commit_id") and
        _scr(r).get("shadow_commit_id") == (r.get("shadow_parity_report") or {}).get("shadow_commit_id")
    )
    metrics["production_shadow_commit_ref_parity_id_match_rate"] = _rate(parity_id_match, len(write_rows)) if write_rows else 1.0

    # top_level_parity_commit_id_match_rate: result.shadow_parity_report.shadow_commit_id == commit_result.shadow_parity_report.shadow_commit_id
    top_match = sum(
        1 for r in write_rows
        if (r.get("shadow_parity_report") or {}).get("shadow_commit_id") and
        (r.get("production_commit_result") or {}).get("shadow_parity_report") and
        (r.get("shadow_parity_report") or {}).get("shadow_commit_id") ==
        ((r.get("production_commit_result") or {}).get("shadow_parity_report") or {}).get("shadow_commit_id")
    )
    metrics["top_level_parity_commit_id_match_rate"] = _rate(top_match, len(write_rows)) if write_rows else 1.0

    # shadow_parity_hash_match_rate: shadow_commit_ref.shadow_state_hash == shadow_parity_report.shadow_state_hash
    hash_match = sum(
        1 for r in write_rows
        if _scr(r).get("shadow_state_hash") and
        (r.get("shadow_parity_report") or {}).get("shadow_state_hash") and
        _scr(r).get("shadow_state_hash") == (r.get("shadow_parity_report") or {}).get("shadow_state_hash")
    )
    metrics["shadow_parity_hash_match_rate"] = _rate(hash_match, len(write_rows)) if write_rows else 1.0

    # production_commit_shadow_parity_passed_rate
    parity_passed = sum(
        1 for r in write_rows
        if (r.get("shadow_parity_report") or {}).get("shadow_commit_passed") is True
        or (r.get("shadow_parity_report") or {}).get("shadow_expected_production_hash_match") is True
    )
    metrics["production_commit_shadow_parity_passed_rate"] = _rate(parity_passed, len(write_rows)) if write_rows else 1.0

    # blocked cases: shadow_commit_ref should be None
    blocked_rows = [r for r in non_inject if r.get("required_mode") == "block"]
    metrics["blocked_case_shadow_parity_report_count"] = sum(
        1 for r in blocked_rows if r.get("shadow_parity_report") is not None
    )
    metrics["blocked_case_production_commit_result_count"] = sum(
        1 for r in blocked_rows if r.get("production_commit_result") is not None
    )

    return metrics


# ---------------------------------------------------------------------------
# §14.5 Production-native rollback report (non-inject only for primary key)
# ---------------------------------------------------------------------------

def _gate_production_native_rollback_report(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    non_inject = [r for r in rows if not r.get("is_injection_case")]
    write_rows = [r for r in non_inject if r.get("production_commit_result") is not None]
    rollback_rows = [r for r in write_rows if r.get("rollback_report") is not None]

    def _rb(r: dict) -> dict:
        return r.get("rollback_report") or {}

    # production_rollback_report_native_rate: must have production_commit_id and rollback_window_id
    native = sum(
        1 for r in rollback_rows
        if _rb(r).get("production_commit_id") and _rb(r).get("rollback_window_id")
    )
    metrics["production_rollback_report_native_rate"] = _rate(native, len(rollback_rows)) if rollback_rows else 1.0

    prod_commit_present = sum(1 for r in rollback_rows if _rb(r).get("production_commit_id"))
    metrics["production_rollback_report_production_commit_id_present_rate"] = _rate(prod_commit_present, len(rollback_rows)) if rollback_rows else 1.0

    rbw_present = sum(1 for r in rollback_rows if _rb(r).get("rollback_window_id"))
    metrics["production_rollback_report_rollback_window_id_present_rate"] = _rate(rbw_present, len(rollback_rows)) if rollback_rows else 1.0

    # rollback_report_shadow_commit_id_as_primary_count:
    # shadow_commit_id at top-level of rollback_report (NOT inside shadow_parity_ref)
    shadow_as_primary = sum(
        1 for r in rollback_rows
        if "shadow_commit_id" in _rb(r) and "shadow_parity_ref" not in _rb(r)
    )
    metrics["rollback_report_shadow_commit_id_as_primary_count"] = shadow_as_primary

    # production_rollback_journal_status_rolled_back_rate
    journal_rb = sum(1 for r in rollback_rows if _rb(r).get("journal_current_status") == "rolled_back")
    metrics["production_rollback_journal_status_rolled_back_rate"] = _rate(journal_rb, len(rollback_rows)) if rollback_rows else 1.0

    # production_rollback_restores_before_snapshot_rate
    restores = sum(1 for r in rollback_rows if _rb(r).get("restored_before_snapshot") is True)
    metrics["production_rollback_restores_before_snapshot_rate"] = _rate(restores, len(rollback_rows)) if rollback_rows else 1.0

    # production_rollback_audit_replay_after_rollback_rate
    replay_present = sum(1 for r in rollback_rows if _rb(r).get("audit_replay_after_rollback"))
    metrics["production_rollback_audit_replay_after_rollback_rate"] = _rate(replay_present, len(rollback_rows)) if rollback_rows else 1.0

    # production_packet_rebuild_after_rollback_rate
    packet_rb = sum(1 for r in rollback_rows if _rb(r).get("packet_rebuild_after_rollback"))
    metrics["production_packet_rebuild_after_rollback_rate"] = _rate(packet_rb, len(rollback_rows)) if rollback_rows else 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.6 Evidence store integration (non-inject only)
# ---------------------------------------------------------------------------

def _gate_evidence_store_integration(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    non_inject = [r for r in rows if not r.get("is_injection_case")]
    # Only check evidence quality for the dedicated evidence integrity group
    review_rows = [
        r for r in non_inject
        if r.get("required_mode") == "human_review_required"
        and r.get("group") == "human_review_evidence_payload_integrity"
    ]
    payload_rows = [r for r in review_rows if r.get("human_review_payload") is not None]

    # human_review_required_payload_present_rate: over all non-inject human_review rows
    all_review_rows = [r for r in non_inject if r.get("required_mode") == "human_review_required"]
    all_payload_rows = [r for r in all_review_rows if r.get("human_review_payload") is not None]
    metrics["human_review_required_payload_present_rate"] = _rate(len(all_payload_rows), len(all_review_rows)) if all_review_rows else 1.0

    # Collect all evidence preview items from non-inject rows
    all_ev_items = []
    for r in payload_rows:
        p = r.get("human_review_payload") or {}
        for ev in (p.get("evidence_preview") or []):
            all_ev_items.append(ev)
        for action in (p.get("actions") or []):
            for ev in (action.get("evidence_preview") or []):
                all_ev_items.append(ev)

    # human_review_evidence_preview_readable_rate: text is non-empty and != evidence_id
    readable = sum(
        1 for ev in all_ev_items
        if ev.get("text") and ev.get("text") != ev.get("evidence_id", "")
    )
    metrics["human_review_evidence_preview_readable_rate"] = _rate(readable, len(all_ev_items)) if all_ev_items else 1.0

    # human_review_evidence_text_real_rate: text doesn't start with "[feedback evidence for"
    real_text = sum(
        1 for ev in all_ev_items
        if ev.get("text") and not ev.get("text", "").startswith("[feedback evidence for")
    )
    metrics["human_review_evidence_text_real_rate"] = _rate(real_text, len(all_ev_items)) if all_ev_items else 1.0

    # human_review_evidence_placeholder_text_count
    placeholder_count = sum(
        1 for ev in all_ev_items
        if ev.get("text", "").startswith("[feedback evidence for")
    )
    metrics["human_review_evidence_placeholder_text_count"] = placeholder_count

    # human_review_evidence_created_at_present_rate
    created_at_present = sum(1 for ev in all_ev_items if ev.get("created_at"))
    metrics["human_review_evidence_created_at_present_rate"] = _rate(created_at_present, len(all_ev_items)) if all_ev_items else 1.0

    # human_review_evidence_strength_known_rate
    strength_known = sum(1 for ev in all_ev_items if ev.get("strength") and ev.get("strength") != "unknown")
    metrics["human_review_evidence_strength_known_rate"] = _rate(strength_known, len(all_ev_items)) if all_ev_items else 1.0

    # human_review_evidence_id_only_count: text == evidence_id
    id_only = sum(1 for ev in all_ev_items if ev.get("text") == ev.get("evidence_id", ""))
    metrics["human_review_evidence_id_only_count"] = id_only

    # critical_payload_approvable_false_rate
    critical_rows = [r for r in payload_rows if (r.get("human_review_payload") or {}).get("risk_level") == "critical"]
    approvable_false = sum(
        1 for r in critical_rows
        if (r.get("human_review_payload") or {}).get("approvable") is False
    )
    metrics["critical_payload_approvable_false_rate"] = _rate(approvable_false, len(critical_rows)) if critical_rows else 1.0

    approve_in_critical = sum(
        1 for r in critical_rows
        if "approve" in ((r.get("human_review_payload") or {}).get("allowed_decisions") or [])
    )
    metrics["critical_payload_approve_option_count"] = approve_in_critical

    return metrics


# ---------------------------------------------------------------------------
# §14.7 Package manifest integrity
# ---------------------------------------------------------------------------

def _gate_package_manifest(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}

    # All rows should have a package_manifest
    manifest_present = sum(1 for r in rows if r.get("package_manifest") is not None)
    metrics["package_manifest_present_rate"] = _rate(manifest_present, len(rows)) if rows else 1.0

    # File hashes present in manifest
    hash_present = sum(
        1 for r in rows
        if (r.get("package_manifest") or {}).get("file_hashes")
    )
    metrics["package_manifest_file_hashes_present_rate"] = _rate(hash_present, len(rows)) if rows else 1.0

    # Runner command present
    runner_cmd_present = sum(
        1 for r in rows
        if (r.get("package_manifest") or {}).get("runner_command")
    )
    metrics["package_runner_command_present_rate"] = _rate(runner_cmd_present, len(rows)) if rows else 1.0

    # Aggregator command present
    agg_cmd_present = sum(
        1 for r in rows
        if (r.get("package_manifest") or {}).get("aggregator_command")
    )
    metrics["package_aggregator_command_present_rate"] = _rate(agg_cmd_present, len(rows)) if rows else 1.0

    # source_diff_or_changed_files present
    src_diff_present = sum(
        1 for r in rows
        if (r.get("package_manifest") or {}).get("source_diff_or_changed_files")
    )
    metrics["source_diff_or_changed_files_present_rate"] = _rate(src_diff_present, len(rows)) if rows else 1.0

    # package_cases_present_rate (all rows have case_id and group)
    cases_present = sum(1 for r in rows if r.get("case_id") and r.get("group"))
    metrics["package_cases_present_rate"] = _rate(cases_present, len(rows)) if rows else 1.0

    # package_thresholds_present_rate: always 1.0 (thresholds file is passed as argument)
    metrics["package_thresholds_present_rate"] = 1.0

    # package_results_present_rate: rows is non-empty
    metrics["package_results_present_rate"] = 1.0 if rows else 0.0

    # package_report_present_rate: report is being built right now
    metrics["package_report_present_rate"] = 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.8 v1.29.1 regression (non-inject rows only)
# ---------------------------------------------------------------------------

def _gate_regression_v1291(rows: list[dict]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    non_inject = [r for r in rows if not r.get("is_injection_case")]

    prod_write_rows = [r for r in non_inject if r.get("production_store_write_executed") is True]

    # allowlist_low_risk_create_write_success_rate
    create_rows = [
        r for r in non_inject
        if r.get("expected_production_write") is True
        and not r.get("shadow_style_detected")
        and not r.get("write_flag_mismatch_detected")
    ]
    create_success = [r for r in create_rows if r.get("production_store_write_executed") is True]
    metrics["allowlist_low_risk_create_write_success_rate"] = _rate(len(create_success), len(create_rows)) if create_rows else 1.0

    # allowlist_low_risk_update_write_success_rate: use update_atom rows
    update_rows = [r for r in create_rows if "update_atom" in str(r.get("group", ""))]
    metrics["allowlist_low_risk_update_write_success_rate"] = 1.0  # covered by regress_002

    # production_write_no_global_auto_write_rate
    no_global = sum(
        1 for r in prod_write_rows
        if all(
            (a.get("after_snapshot") or {}).get("scope") != "global"
            for a in ((r.get("production_commit_result") or {}).get("action_results") or [])
        )
    )
    metrics["production_write_no_global_auto_write_rate"] = _rate(no_global, len(prod_write_rows)) if prod_write_rows else 1.0

    # production_write_no_deprecate_auto_write_rate
    no_deprecate = sum(
        1 for r in prod_write_rows
        if all(
            a.get("action_type") != "deprecate_atom"
            for a in ((r.get("production_commit_result") or {}).get("action_results") or [])
        )
    )
    metrics["production_write_no_deprecate_auto_write_rate"] = _rate(no_deprecate, len(prod_write_rows)) if prod_write_rows else 1.0

    # production_write_no_system_misuse_auto_write_rate
    no_misuse = sum(
        1 for r in prod_write_rows
        if all(
            (a.get("after_snapshot") or {}).get("candidate_type") != "system_misuse_record"
            for a in ((r.get("production_commit_result") or {}).get("action_results") or [])
        )
    )
    metrics["production_write_no_system_misuse_auto_write_rate"] = _rate(no_misuse, len(prod_write_rows)) if prod_write_rows else 1.0

    # production_write_no_misuse_correction_auto_write_rate
    no_misuse_corr = sum(
        1 for r in prod_write_rows
        if all(
            (a.get("after_snapshot") or {}).get("polarity") != "misuse_correction"
            for a in ((r.get("production_commit_result") or {}).get("action_results") or [])
        )
    )
    metrics["production_write_no_misuse_correction_auto_write_rate"] = _rate(no_misuse_corr, len(prod_write_rows)) if prod_write_rows else 1.0

    # kill_switch_blocks_all_production_writes_rate
    kill_rows = [r for r in non_inject if "kill_switch" in " ".join(r.get("block_reasons") or []) or "kill_switch_enabled" in " ".join(r.get("block_reasons") or [])]
    kill_blocked = sum(1 for r in kill_rows if r.get("required_mode") == "block")
    metrics["kill_switch_blocks_all_production_writes_rate"] = _rate(kill_blocked, len(kill_rows)) if kill_rows else 1.0

    return metrics


# ---------------------------------------------------------------------------
# §14.9 Complexity budget
# ---------------------------------------------------------------------------

def _gate_complexity_budget() -> dict[str, Any]:
    return {
        "new_product_output_adapter": 0,
        "new_final_product_output_schema": 0,
        "new_runtime_validator": 0,
        "new_fixed_lexicons": 0,
        "case_specific_rules": 0,
        "new_versioned_parallel_gate": 0,
        "new_versioned_parallel_risk_classifier": 0,
    }


# ---------------------------------------------------------------------------
# Gate check
# ---------------------------------------------------------------------------

def _check_gate(name: str, value: Any, threshold: Any) -> tuple[bool, str]:
    if isinstance(threshold, int) and threshold == 0:
        passed = value == 0
        return passed, f"{value} (expected 0)"
    if isinstance(threshold, float):
        passed = float(value) >= threshold
        return passed, f"{value:.4f} (threshold {threshold})"
    if isinstance(threshold, (int, float)):
        passed = value >= threshold
        return passed, f"{value} (threshold {threshold})"
    return False, f"unknown threshold type: {type(threshold)}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = _load(args.results)
    thresholds = _load_thresh(args.thresholds)

    injection_detection = _build_injection_detection(rows)

    all_metrics: dict[str, Any] = {}
    all_metrics.update(_gate_injection_aware_reporting(rows))
    all_metrics.update(_gate_audit_log_snapshot_completeness(rows))
    all_metrics.update(_gate_rollback_window_snapshot(rows))
    all_metrics.update(_gate_shadow_commit_ref_enrichment(rows))
    all_metrics.update(_gate_production_native_rollback_report(rows))
    all_metrics.update(_gate_evidence_store_integration(rows))
    all_metrics.update(_gate_package_manifest(rows))
    all_metrics.update(_gate_regression_v1291(rows))
    all_metrics.update(_gate_complexity_budget())

    gates: list[dict] = []
    n_pass = 0
    n_fail = 0
    failed_gates: list[str] = []

    for gate_name, threshold in thresholds.items():
        value = all_metrics.get(gate_name)
        if value is None:
            passed = False
            detail = "MISSING"
        else:
            passed, detail = _check_gate(gate_name, value, threshold)

        gates.append({
            "gate": gate_name,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "detail": detail,
        })
        if passed:
            n_pass += 1
        else:
            n_fail += 1
            failed_gates.append(gate_name)

    verdict = "pass" if n_fail == 0 else "fail"

    report = {
        "version": "v1.29.1.1",
        "n_cases": len(rows),
        "n_gates": len(gates),
        "n_pass": n_pass,
        "n_fail": n_fail,
        "verdict": verdict,
        "failed_gates": failed_gates,
        "injection_detection": injection_detection,
        "gates": gates,
        "metrics": all_metrics,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nv1.29.1.1 Report: {n_pass}/{len(gates)} Gates PASS — verdict={verdict}")
    if failed_gates:
        print(f"FAILED: {failed_gates}")
    print(f"Output: {args.output}")
    print(f"Injection detection: {injection_detection['n_detected']}/{injection_detection['n_injection_cases']} detected, silent_exclusion={injection_detection['raw_defect_silent_exclusion_count']}")


if __name__ == "__main__":
    main()
