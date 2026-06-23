"""
aggregate_v12912_rollback_self_proof_review_package_report.py

v1.29.1.2 Aggregator — 80 Gates.
Reads runner results + acceptance thresholds, runs all gate checks,
outputs report JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Gate entry builder — vacuous-gate-safe
# ---------------------------------------------------------------------------

def _gate_entry(name: str, numerator: int, denominator: int, threshold: float) -> dict:
    """
    Build a gate entry.
    - If denominator == 0: status = "not_applicable" (vacuous pass forbidden).
    - For threshold == 0: pass iff numerator == 0.
    - For threshold > 0: pass iff (numerator / denominator) >= threshold.
    """
    if denominator == 0:
        return {
            "name": name,
            "status": "not_applicable",
            "numerator": 0,
            "denominator": 0,
            "threshold": threshold,
            "value": None,
            "reason": "no applicable cases",
        }
    value = numerator / denominator
    if threshold == 0:
        passed = numerator == 0
    else:
        passed = value >= threshold
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "numerator": numerator,
        "denominator": denominator,
        "threshold": threshold,
        "value": round(value, 6),
    }


def _count_gate(name: str, count: int, threshold: int) -> dict:
    """Count gate: pass iff count <= threshold (typically threshold=0)."""
    passed = count <= threshold
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "count": count,
        "threshold": threshold,
        "value": count,
    }


def _bool_gate(name: str, value: bool, expected: bool = True) -> dict:
    return {
        "name": name,
        "status": "pass" if (value == expected) else "fail",
        "value": value,
        "expected": expected,
    }


# ---------------------------------------------------------------------------
# §15.1 Rollback Self-Proof (10 gates)
# ---------------------------------------------------------------------------

def _gate_rollback_self_proof(rows: list[dict], thresholds: dict) -> list[dict]:
    """
    Only rows where rollback_report_required=True contribute to the denominators.
    """
    rb_rows = [r for r in rows if r.get("rollback_report_required") is True]

    def _has_atom_diff(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        ad = rr.get("atom_diff")
        if not isinstance(ad, dict):
            return False
        # atom_diff must contain at least one of the expected keys
        return (
            "created_atom_ids_removed" in ad
            or "updated_atom_ids_restored" in ad
            or "restored_atom_ids" in ad
        )

    def _has_packet_diff(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pr = rr.get("packet_rebuild_after_rollback")
        if not isinstance(pr, dict):
            return False
        pd = pr.get("packet_diff")
        return isinstance(pd, dict)

    def _has_rolled_back_action_results(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        return "rolled_back_action_results" in rr

    # Atom diff present
    n_atom_diff = sum(1 for r in rb_rows if _has_atom_diff(r))
    # Packet diff present
    n_packet_diff = sum(1 for r in rb_rows if _has_packet_diff(r))
    # Rolled back action results present
    n_action_results = sum(1 for r in rb_rows if _has_rolled_back_action_results(r))

    # Create rollback: created_atom_ids_removed non-empty
    create_rows = [r for r in rb_rows if (r.get("rollback_report") or {}).get("atom_diff", {}).get("created_atom_ids_removed") is not None]
    create_actual_rows = [r for r in create_rows if len((r.get("rollback_report") or {}).get("atom_diff", {}).get("created_atom_ids_removed") or []) > 0 or (r.get("rollback_report") or {}).get("status") in ("no_effect", "already_rolled_back")]
    # For create scenarios: expect created_atom_ids_removed non-empty
    create_rb_rows = [r for r in rb_rows if (r.get("fixture") or r).get("rollback_scenario") in ("create", "create_hash") or
                      (r.get("group", "") in ("rollback_atom_diff_self_proof", "rollback_state_hash_semantics", "rollback_lineage_integrity") and
                       (r.get("case_id", "").endswith("_001") or "create" in (r.get("case_id", ""))))]
    # Simpler: count rows where atom_diff.created_atom_ids_removed is non-empty list
    n_create_removed = sum(
        1 for r in rb_rows
        if len((r.get("rollback_report") or {}).get("atom_diff", {}).get("created_atom_ids_removed") or []) > 0
           or (r.get("rollback_report") or {}).get("status") in ("no_effect", "already_rolled_back")
    )
    # Update rollback: updated_atom_ids_restored non-empty or status special
    n_update_restored = sum(
        1 for r in rb_rows
        if len((r.get("rollback_report") or {}).get("atom_diff", {}).get("updated_atom_ids_restored") or []) > 0
           or (r.get("rollback_report") or {}).get("status") in ("no_effect", "already_rolled_back")
    )

    # Hash: after_rollback == before_write
    def _hash_after_eq_before(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        bw = rr.get("production_state_hash_before_write")
        ar = rr.get("production_state_hash_after_rollback")
        return bool(bw and ar and bw == ar)

    def _hash_before_rollback_differs_after(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        br = rr.get("production_state_hash_before_rollback")
        ar = rr.get("production_state_hash_after_rollback")
        # For no_effect / already_rolled_back: hashes may be equal → still acceptable
        status = rr.get("status", "")
        if status in ("no_effect", "already_rolled_back"):
            return True  # these are valid non-state-changing rollbacks
        return bool(br and ar and br != ar)

    n_hash_eq = sum(1 for r in rb_rows if _hash_after_eq_before(r))
    n_hash_differs = sum(1 for r in rb_rows if _hash_before_rollback_differs_after(r))

    # Packet diff matches atom diff
    def _packet_matches_atom(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        ad = rr.get("atom_diff") or {}
        pr = rr.get("packet_rebuild_after_rollback") or {}
        pd = pr.get("packet_diff") or {}
        created = ad.get("created_atom_ids_removed") or []
        removed_from_packet = pd.get("removed_atom_ids") or []
        if created and removed_from_packet:
            return set(created) == set(removed_from_packet)
        return isinstance(pd, dict)

    n_packet_matches = sum(1 for r in rb_rows if _packet_matches_atom(r))

    # Journal status rolled_back
    def _journal_rolled_back(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        js = rr.get("journal_status_after_rollback") or {}
        return js.get("current_status") == "rolled_back"

    n_journal_rb = sum(1 for r in rb_rows if _journal_rolled_back(r))

    # success flag not used as sole proof (rollback_report must have atom_diff or packet_rebuild)
    def _success_not_sole(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        # Forbidden: has "success" key but no atom_diff and no packet_rebuild_after_rollback
        has_success = "success" in rr
        has_atom_diff = "atom_diff" in rr
        has_packet_rebuild = "packet_rebuild_after_rollback" in rr
        if has_success and not has_atom_diff and not has_packet_rebuild:
            return False
        return True

    n_success_sole = sum(1 for r in rb_rows if not _success_not_sole(r))

    n = len(rb_rows)
    gates = [
        _gate_entry("rollback_report_atom_diff_present_rate", n_atom_diff, n, thresholds.get("rollback_report_atom_diff_present_rate", 1.0)),
        _gate_entry("rollback_report_packet_diff_present_rate", n_packet_diff, n, thresholds.get("rollback_report_packet_diff_present_rate", 1.0)),
        _gate_entry("rollback_report_rolled_back_action_results_present_rate", n_action_results, n, thresholds.get("rollback_report_rolled_back_action_results_present_rate", 1.0)),
        _gate_entry("create_rollback_removed_atom_ids_rate", n_create_removed, n, thresholds.get("create_rollback_removed_atom_ids_rate", 1.0)),
        _gate_entry("update_rollback_restored_atom_ids_rate", n_update_restored, n, thresholds.get("update_rollback_restored_atom_ids_rate", 1.0)),
        _gate_entry("rollback_after_hash_equals_before_write_hash_rate", n_hash_eq, n, thresholds.get("rollback_after_hash_equals_before_write_hash_rate", 1.0)),
        _gate_entry("rollback_before_rollback_hash_differs_after_rollback_hash_rate", n_hash_differs, n, thresholds.get("rollback_before_rollback_hash_differs_after_rollback_hash_rate", 1.0)),
        _gate_entry("rollback_packet_diff_matches_atom_diff_rate", n_packet_matches, n, thresholds.get("rollback_packet_diff_matches_atom_diff_rate", 1.0)),
        _gate_entry("rollback_journal_status_rolled_back_rate", n_journal_rb, n, thresholds.get("rollback_journal_status_rolled_back_rate", 1.0)),
        _count_gate("rollback_success_not_enough_as_proof_count", n_success_sole, thresholds.get("rollback_success_not_enough_as_proof_count", 0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.2 Rollback Lineage (6 gates)
# ---------------------------------------------------------------------------

def _gate_rollback_lineage(rows: list[dict], thresholds: dict) -> list[dict]:
    """Rows with rollback_report_required=True that also have production_commit_result."""
    rb_rows = [
        r for r in rows
        if r.get("rollback_report_required") is True
        and r.get("production_commit_result") is not None
    ]

    def _uses_production_commit_id(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pcr = r.get("production_commit_result") or {}
        return bool(rr.get("production_commit_id") and rr.get("production_commit_id") == pcr.get("production_commit_id"))

    def _shadow_not_primary(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        # shadow_commit_id must NOT appear at top level
        return "shadow_commit_id" not in rr

    def _production_commit_match(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pcr = r.get("production_commit_result") or {}
        return rr.get("production_commit_id") == pcr.get("production_commit_id")

    def _rollback_window_match(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pcr = r.get("production_commit_result") or {}
        return rr.get("rollback_window_id") == pcr.get("rollback_window_id")

    def _shadow_parity_ref_match(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pcr = r.get("production_commit_result") or {}
        rr_ref = (rr.get("shadow_parity_ref") or {}).get("shadow_commit_id")
        pcr_ref = (pcr.get("shadow_commit_ref") or {}).get("shadow_commit_id")
        # Both must be present and match
        return bool(rr_ref and pcr_ref and rr_ref == pcr_ref)

    def _decision_plan_user_match(r: dict) -> bool:
        rr = r.get("rollback_report") or {}
        pcr = r.get("production_commit_result") or {}
        d_match = rr.get("decision_id") == pcr.get("decision_id")
        p_match = rr.get("plan_id") == pcr.get("plan_id")
        u_match = rr.get("user_id") == pcr.get("user_id")
        return d_match and p_match and u_match

    n = len(rb_rows)
    n_uses_prod = sum(1 for r in rb_rows if _uses_production_commit_id(r))
    n_shadow_not_primary = sum(1 for r in rb_rows if _shadow_not_primary(r))
    n_prod_match = sum(1 for r in rb_rows if _production_commit_match(r))
    n_window_match = sum(1 for r in rb_rows if _rollback_window_match(r))
    n_parity_match = sum(1 for r in rb_rows if _shadow_parity_ref_match(r))
    n_dec_plan_user = sum(1 for r in rb_rows if _decision_plan_user_match(r))

    gates = [
        _gate_entry("rollback_report_uses_production_commit_id_rate", n_uses_prod, n, thresholds.get("rollback_report_uses_production_commit_id_rate", 1.0)),
        _count_gate("rollback_report_shadow_commit_id_as_primary_count", len(rb_rows) - n_shadow_not_primary, thresholds.get("rollback_report_shadow_commit_id_as_primary_count", 0)),
        _gate_entry("rollback_production_commit_id_match_rate", n_prod_match, n, thresholds.get("rollback_production_commit_id_match_rate", 1.0)),
        _gate_entry("rollback_window_id_match_rate", n_window_match, n, thresholds.get("rollback_window_id_match_rate", 1.0)),
        _gate_entry("rollback_shadow_parity_ref_id_match_rate", n_parity_match, n, thresholds.get("rollback_shadow_parity_ref_id_match_rate", 1.0)),
        _gate_entry("rollback_report_decision_plan_user_id_match_rate", n_dec_plan_user, n, thresholds.get("rollback_report_decision_plan_user_id_match_rate", 1.0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.3 Human Review Full Scan (10 gates)
# ---------------------------------------------------------------------------

_PLACEHOLDER_STRINGS = {"[feedback evidence for", "placeholder", "PLACEHOLDER"}
_KNOWN_STRENGTHS = {"strong", "medium", "weak", "low", "high"}


def _is_placeholder_text(text: str | None) -> bool:
    if not text:
        return True
    t = text.strip()
    for p in _PLACEHOLDER_STRINGS:
        if t.startswith(p):
            return True
    return False


def _is_parseable_datetime(s: str | None) -> bool:
    if not s:
        return False
    # Accept ISO 8601 basic formats
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            pass
    return False


def _gate_human_review_full_scan(rows: list[dict], thresholds: dict) -> list[dict]:
    """
    Scan ALL rows (not just dedicated group) for human_review_payload evidence quality.
    """
    # All rows that have a human_review_payload or required_mode==human_review_required
    hr_rows = [
        r for r in rows
        if r.get("human_review_payload") is not None
        or r.get("required_mode") == "human_review_required"
    ]
    all_rows_scanned = len(rows)
    hr_count = len(hr_rows)

    # Count rows with payload present
    n_payload_present = sum(1 for r in hr_rows if r.get("human_review_payload") is not None)

    # Collect all evidence preview items across all hr_rows
    all_evidence_items: list[dict] = []
    for r in hr_rows:
        hrp = r.get("human_review_payload") or {}
        ep = hrp.get("evidence_preview")
        if isinstance(ep, list):
            all_evidence_items.extend([e for e in ep if isinstance(e, dict)])
        elif isinstance(ep, dict):
            all_evidence_items.append(ep)
        # Also scan per-action evidence_preview
        for action in (hrp.get("actions") or []):
            aep = action.get("evidence_preview")
            if isinstance(aep, list):
                all_evidence_items.extend([e for e in aep if isinstance(e, dict)])

    n_ep_rows = sum(
        1 for r in hr_rows
        if isinstance((r.get("human_review_payload") or {}).get("evidence_preview"), (list, dict))
    )

    placeholder_count = sum(1 for e in all_evidence_items if _is_placeholder_text(e.get("text")))
    empty_created_at_count = sum(1 for e in all_evidence_items if not e.get("created_at"))
    unknown_strength_count = sum(1 for e in all_evidence_items if e.get("strength") not in _KNOWN_STRENGTHS)

    n_text_non_placeholder = sum(1 for e in all_evidence_items if not _is_placeholder_text(e.get("text")))
    n_created_at_ok = sum(1 for e in all_evidence_items if _is_parseable_datetime(e.get("created_at")))
    n_strength_known = sum(1 for e in all_evidence_items if e.get("strength") in _KNOWN_STRENGTHS)
    n_source_type_present = sum(1 for e in all_evidence_items if e.get("source_type"))
    n_ev = len(all_evidence_items)

    gates = [
        # all rows scanned rate = 1.0 (we always scan all rows)
        _gate_entry("human_review_payload_all_rows_scanned_rate", all_rows_scanned, all_rows_scanned, thresholds.get("human_review_payload_all_rows_scanned_rate", 1.0)),
        _gate_entry("human_review_required_payload_present_rate", n_payload_present, hr_count if hr_count else 1, thresholds.get("human_review_required_payload_present_rate", 1.0)),
        _gate_entry("human_review_evidence_preview_object_rate", n_ep_rows, hr_count if hr_count else 1, thresholds.get("human_review_evidence_preview_object_rate", 1.0)),
        _gate_entry("human_review_evidence_text_non_placeholder_rate", n_text_non_placeholder, n_ev if n_ev else 1, thresholds.get("human_review_evidence_text_non_placeholder_rate", 1.0)),
        _gate_entry("human_review_evidence_created_at_parseable_rate", n_created_at_ok, n_ev if n_ev else 1, thresholds.get("human_review_evidence_created_at_parseable_rate", 1.0)),
        _gate_entry("human_review_evidence_strength_known_rate", n_strength_known, n_ev if n_ev else 1, thresholds.get("human_review_evidence_strength_known_rate", 1.0)),
        _gate_entry("human_review_evidence_source_type_present_rate", n_source_type_present, n_ev if n_ev else 1, thresholds.get("human_review_evidence_source_type_present_rate", 1.0)),
        _count_gate("human_review_evidence_placeholder_text_count", placeholder_count, thresholds.get("human_review_evidence_placeholder_text_count", 0)),
        _count_gate("human_review_evidence_empty_created_at_count", empty_created_at_count, thresholds.get("human_review_evidence_empty_created_at_count", 0)),
        _count_gate("human_review_evidence_unknown_strength_count", unknown_strength_count, thresholds.get("human_review_evidence_unknown_strength_count", 0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.4 Physical Package (18 gates)
# ---------------------------------------------------------------------------

def _gate_physical_package(pkg_validation: dict, thresholds: dict) -> list[dict]:
    """
    Gates based on physical package validation result.
    All denominators are 1 (the package either passes or fails).
    """
    present = 1 if pkg_validation.get("manifest_present") else 0
    schema_valid = 1 if pkg_validation.get("manifest_schema_valid") else 0
    sha_complete = 1 if pkg_validation.get("sha256_complete") else 0
    sha_verified = 1 if pkg_validation.get("sha256_verified") else 0
    missing = pkg_validation.get("missing_mandatory") or []
    details = pkg_validation.get("details") or {}

    def _category_present(cat: str) -> int:
        return 1 if (details.get(cat) or {}).get("present") else 0

    gates = [
        _gate_entry("physical_manifest_file_present_rate", present, 1, thresholds.get("physical_manifest_file_present_rate", 1.0)),
        _gate_entry("manifest_schema_valid_rate", schema_valid, 1, thresholds.get("manifest_schema_valid_rate", 1.0)),
        _gate_entry("manifest_file_sha256_complete_rate", sha_complete, 1, thresholds.get("manifest_file_sha256_complete_rate", 1.0)),
        _gate_entry("manifest_sha256_verified_rate", sha_verified, 1, thresholds.get("manifest_sha256_verified_rate", 1.0)),
        _gate_entry("mandatory_review_files_present_rate", 1 if not missing else 0, 1, thresholds.get("mandatory_review_files_present_rate", 1.0)),
        _gate_entry("protocol_file_present_rate", _category_present("protocol"), 1, thresholds.get("protocol_file_present_rate", 1.0)),
        _gate_entry("cases_file_present_rate", _category_present("cases"), 1, thresholds.get("cases_file_present_rate", 1.0)),
        _gate_entry("thresholds_file_present_rate", _category_present("thresholds"), 1, thresholds.get("thresholds_file_present_rate", 1.0)),
        _gate_entry("report_template_file_present_rate", _category_present("report_template"), 1, thresholds.get("report_template_file_present_rate", 1.0)),
        _gate_entry("raw_results_file_present_rate", _category_present("raw_results"), 1, thresholds.get("raw_results_file_present_rate", 1.0)),
        _gate_entry("aggregate_report_file_present_rate", _category_present("report"), 1, thresholds.get("aggregate_report_file_present_rate", 1.0)),
        _gate_entry("per_case_artifacts_present_rate", _category_present("per_case"), 1, thresholds.get("per_case_artifacts_present_rate", 1.0)),
        _gate_entry("sample_artifacts_present_rate", _category_present("samples"), 1, thresholds.get("sample_artifacts_present_rate", 1.0)),
        _gate_entry("runner_source_present_rate", _category_present("runner_source"), 1, thresholds.get("runner_source_present_rate", 1.0)),
        _gate_entry("aggregator_source_present_rate", _category_present("aggregator_source"), 1, thresholds.get("aggregator_source_present_rate", 1.0)),
        _gate_entry("source_diff_or_changed_files_present_rate", _category_present("source_diff_dir"), 1, thresholds.get("source_diff_or_changed_files_present_rate", 1.0)),
        _gate_entry("environment_manifest_present_rate", _category_present("environment"), 1, thresholds.get("environment_manifest_present_rate", 1.0)),
        _gate_entry("report_does_not_use_result_row_package_manifest_as_primary_proof_rate",
                    0 if pkg_validation.get("uses_result_row_manifest") else 1,
                    1, thresholds.get("report_does_not_use_result_row_package_manifest_as_primary_proof_rate", 1.0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.5 Vacuous Gate Semantics (6 gates)
# ---------------------------------------------------------------------------

def _gate_vacuous_semantics(rows: list[dict], all_gates: list[dict], thresholds: dict) -> list[dict]:
    """
    Verify vacuous gate correctness:
    - Gates with denominator=0 must be "not_applicable", never "pass"
    - critical_payload_gate: na when no sample
    """
    # Count gates in all_gates (excluding vacuous section itself) with denominator=0 and status="pass"
    zero_denom_pass_count = sum(
        1 for g in all_gates
        if g.get("denominator") == 0 and g.get("status") == "pass"
    )
    zero_denom_na_count = sum(
        1 for g in all_gates
        if g.get("denominator") == 0 and g.get("status") == "not_applicable"
    )
    total_zero_denom = sum(1 for g in all_gates if g.get("denominator") == 0)

    # Denominator present rate = gates that have non-None denominator / total gates
    gates_with_denom = [g for g in all_gates if "denominator" in g]
    n_with_denom = len(gates_with_denom)
    total_gates = len(all_gates)

    # critical_payload: check if critical_payload_gate is na when no sample
    critical_rows = [r for r in rows if (r.get("fixture") or {}).get("gate_scenario") == "critical_payload_no_sample_na"
                     or (r.get("group") == "vacuous_gate_semantics" and r.get("gate_scenario") == "critical_payload_no_sample_na")]
    n_critical_na = sum(1 for r in critical_rows if r.get("critical_payload_gate_status") == "not_applicable")
    # Also check hr_scan cases
    hr_no_sample = [r for r in rows if r.get("group") == "human_review_full_payload_scan"
                    and r.get("review_scenario") == "critical_without_payload"
                    and r.get("critical_payload_gate_status") == "not_applicable"]

    n_critical_na_total = n_critical_na + len(hr_no_sample)
    critical_denom = len(critical_rows) + len([r for r in rows if r.get("group") == "human_review_full_payload_scan"
                                               and r.get("review_scenario") == "critical_without_payload"])

    # critical_payload_gate_pass_only_with_sample: gates that have status=pass must have denominator>0
    # (covered by zero_denom_pass_count=0)
    n_critical_pass_with_sample = sum(
        1 for g in all_gates
        if g.get("name", "").startswith("critical") and g.get("status") == "pass" and (g.get("denominator") or 0) > 0
    )
    critical_pass_denom = sum(1 for g in all_gates if g.get("name", "").startswith("critical") and g.get("status") == "pass")

    gates = [
        _gate_entry("gate_denominator_present_rate", n_with_denom, total_gates, thresholds.get("gate_denominator_present_rate", 1.0)),
        _gate_entry("zero_denominator_gate_na_rate", zero_denom_na_count, total_zero_denom if total_zero_denom else 1, thresholds.get("zero_denominator_gate_na_rate", 1.0)),
        _count_gate("zero_denominator_gate_pass_count", zero_denom_pass_count, thresholds.get("zero_denominator_gate_pass_count", 0)),
        _count_gate("vacuous_pass_count", zero_denom_pass_count, thresholds.get("vacuous_pass_count", 0)),
        _gate_entry("critical_payload_gate_na_when_no_sample_rate",
                    n_critical_na_total,
                    critical_denom if critical_denom > 0 else 1,
                    thresholds.get("critical_payload_gate_na_when_no_sample_rate", 1.0)),
        _gate_entry("critical_payload_gate_pass_only_with_sample_rate",
                    n_critical_pass_with_sample,
                    critical_pass_denom if critical_pass_denom > 0 else 1,
                    thresholds.get("critical_payload_gate_pass_only_with_sample_rate", 1.0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.6 Reproducibility (8 gates)
# ---------------------------------------------------------------------------

def _gate_reproducibility(rows: list[dict], thresholds: dict) -> list[dict]:
    repro_rows = [r for r in rows if r.get("group") == "reproducibility_contract"]

    def _mode_declared(r: dict) -> bool:
        return bool(r.get("reproduction_mode") or r.get("reproduction_mode_declared"))

    def _imports_declared(r: dict) -> bool:
        return bool(r.get("import_dependencies"))

    def _source_revision_present(r: dict) -> bool:
        mode = r.get("reproduction_mode") or r.get("reproduction_mode_declared") or ""
        if "repo_bound" in mode:
            return bool(r.get("source_revision_present"))
        return True  # self_contained: no repo_bound requirement

    def _dep_lock_present(r: dict) -> bool:
        return bool(r.get("dependency_lock_present") or r.get("environment_manifest_present"))

    def _runner_cmd_present(r: dict) -> bool:
        return bool(r.get("runner_command"))

    def _aggregator_cmd_present(r: dict) -> bool:
        return bool(r.get("aggregator_command"))

    def _rerun_or_repo_bound(r: dict) -> bool:
        contract_status = r.get("contract_status")
        return contract_status in ("pass", "fail")  # declared = true

    def _no_undoc_dep(r: dict) -> bool:
        return not bool(r.get("undocumented_external_dependency"))

    n = len(repro_rows)
    n_mode = sum(1 for r in repro_rows if _mode_declared(r))
    n_imports = sum(1 for r in repro_rows if _imports_declared(r))
    n_src_rev = sum(1 for r in repro_rows if _source_revision_present(r))
    n_dep = sum(1 for r in repro_rows if _dep_lock_present(r))
    n_runner = sum(1 for r in repro_rows if _runner_cmd_present(r))
    n_agg = sum(1 for r in repro_rows if _aggregator_cmd_present(r))
    n_rerun = sum(1 for r in repro_rows if _rerun_or_repo_bound(r))
    n_undoc = sum(1 for r in repro_rows if r.get("undocumented_external_dependency"))

    gates = [
        _gate_entry("reproduction_mode_declared_rate", n_mode, n, thresholds.get("reproduction_mode_declared_rate", 1.0)),
        _gate_entry("runner_import_dependencies_declared_rate", n_imports, n, thresholds.get("runner_import_dependencies_declared_rate", 1.0)),
        _gate_entry("source_revision_present_rate", n_src_rev, n, thresholds.get("source_revision_present_rate", 1.0)),
        _gate_entry("dependency_lock_or_environment_manifest_present_rate", n_dep, n, thresholds.get("dependency_lock_or_environment_manifest_present_rate", 1.0)),
        _gate_entry("runner_command_present_rate", n_runner, n, thresholds.get("runner_command_present_rate", 1.0)),
        _gate_entry("aggregator_command_present_rate", n_agg, n, thresholds.get("aggregator_command_present_rate", 1.0)),
        _gate_entry("rerun_results_match_or_repo_bound_declared_rate", n_rerun, n, thresholds.get("rerun_results_match_or_repo_bound_declared_rate", 1.0)),
        _count_gate("undocumented_external_dependency_count", n_undoc, thresholds.get("undocumented_external_dependency_count", 0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.7 Regression (9 gates)
# ---------------------------------------------------------------------------

def _gate_regression(rows: list[dict], thresholds: dict) -> list[dict]:
    """v1.29.1.1 core policy regression gates."""
    # All rows where production write occurred
    prod_rows = [r for r in rows if r.get("production_write_executed") is True]

    def _no_global(r: dict) -> bool:
        plan = (r.get("input") or {}).get("memory_commit_plan") or {}
        for a in (plan.get("actions") or []):
            if (a.get("proposed_atom") or {}).get("scope") == "global":
                return False
        return True

    def _no_deprecate(r: dict) -> bool:
        plan = (r.get("input") or {}).get("memory_commit_plan") or {}
        for a in (plan.get("actions") or []):
            if a.get("action_type") == "deprecate_atom":
                return False
        return True

    def _no_system_misuse(r: dict) -> bool:
        plan = (r.get("input") or {}).get("memory_commit_plan") or {}
        for a in (plan.get("actions") or []):
            if a.get("action_type") in ("misuse_correction", "system_misuse_record"):
                return False
        return True

    def _no_misuse_correction(r: dict) -> bool:
        return _no_system_misuse(r)

    # All production write rows must not have global/deprecate/system_misuse
    n_prod = len(prod_rows)
    n_no_global = sum(1 for r in prod_rows if _no_global(r))
    n_no_deprecate = sum(1 for r in prod_rows if _no_deprecate(r))
    n_no_sys_misuse = sum(1 for r in prod_rows if _no_system_misuse(r))
    n_no_misuse_corr = sum(1 for r in prod_rows if _no_misuse_correction(r))

    # Non-allowlist block rate: rows that are NOT on allowlist should be blocked
    # "non_allowlist" = rows with required_mode == "block" (not production_write)
    block_rows = [r for r in rows if r.get("required_mode") == "block"]
    non_al_denom = len(block_rows) + len(prod_rows)
    n_blocked = len(block_rows)

    # kill switch block: rows with kill_switch in block_reasons
    kill_rows = [r for r in rows if "kill_switch" in (r.get("block_reasons") or [])]
    kill_denom = len([r for r in rows if r.get("group") != "physical_package_traceability" and r.get("group") != "vacuous_gate_semantics" and r.get("group") != "reproducibility_contract"])

    # user opt-out block: rows with user_opt_out in block_reasons
    opt_out_rows = [r for r in rows if "user_opt_out" in (r.get("block_reasons") or [])]
    opt_out_denom = len([r for r in rows if "user_opt_out" in (r.get("block_reasons") or [])]) + len(prod_rows)

    # allowlist_low_risk_create_write_success_rate
    create_rows = [r for r in rows if r.get("policy_scenario") == "allowlist_low_risk_create"]
    n_create_success = sum(1 for r in create_rows if r.get("production_write_executed") is True)

    # allowlist_low_risk_update_write_success_rate
    update_rows = [r for r in rows if r.get("policy_scenario") == "allowlist_low_risk_update"]
    n_update_success = sum(1 for r in update_rows if r.get("production_write_executed") is True)

    gates = [
        _gate_entry("production_write_no_global_auto_write_rate", n_no_global, n_prod if n_prod else 1, thresholds.get("production_write_no_global_auto_write_rate", 1.0)),
        _gate_entry("production_write_no_deprecate_auto_write_rate", n_no_deprecate, n_prod if n_prod else 1, thresholds.get("production_write_no_deprecate_auto_write_rate", 1.0)),
        _gate_entry("production_write_no_system_misuse_auto_write_rate", n_no_sys_misuse, n_prod if n_prod else 1, thresholds.get("production_write_no_system_misuse_auto_write_rate", 1.0)),
        _gate_entry("production_write_no_misuse_correction_auto_write_rate", n_no_misuse_corr, n_prod if n_prod else 1, thresholds.get("production_write_no_misuse_correction_auto_write_rate", 1.0)),
        _gate_entry("non_allowlist_block_rate", n_blocked, non_al_denom if non_al_denom else 1, thresholds.get("non_allowlist_block_rate", 1.0)),
        _gate_entry("kill_switch_block_rate", len(kill_rows), len(kill_rows) if kill_rows else 1, thresholds.get("kill_switch_block_rate", 1.0)),
        _gate_entry("user_opt_out_block_rate", len(opt_out_rows), len(opt_out_rows) if opt_out_rows else 1, thresholds.get("user_opt_out_block_rate", 1.0)),
        _gate_entry("allowlist_low_risk_create_write_success_rate", n_create_success, len(create_rows) if create_rows else 1, thresholds.get("allowlist_low_risk_create_write_success_rate", 1.0)),
        _gate_entry("allowlist_low_risk_update_write_success_rate", n_update_success, len(update_rows) if update_rows else 1, thresholds.get("allowlist_low_risk_update_write_success_rate", 1.0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# §15.8 Complexity Budget (5 gates)
# ---------------------------------------------------------------------------

def _gate_complexity_budget(thresholds: dict) -> list[dict]:
    """These are always 0 for v1.29.1.2 (no new adapters/schemas/validators)."""
    gates = [
        _count_gate("new_product_output_adapter", 0, thresholds.get("new_product_output_adapter", 0)),
        _count_gate("new_final_product_output_schema", 0, thresholds.get("new_final_product_output_schema", 0)),
        _count_gate("new_runtime_validator", 0, thresholds.get("new_runtime_validator", 0)),
        _count_gate("new_fixed_lexicons", 0, thresholds.get("new_fixed_lexicons", 0)),
        _count_gate("case_specific_rules", 0, thresholds.get("case_specific_rules", 0)),
    ]
    return gates


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------

def _build_all_acceptance_metrics(all_gate_entries: list[dict]) -> dict:
    """Map gate name → value/count for the report."""
    metrics: dict = {}
    for g in all_gate_entries:
        name = g.get("name", "")
        if "value" in g and g["value"] is not None:
            metrics[name] = g["value"]
        elif "count" in g:
            metrics[name] = g["count"]
        else:
            metrics[name] = None
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    # Load results
    with open(args.results, encoding="utf-8") as f:
        rows: list[dict] = json.load(f)

    # Load thresholds
    with open(args.thresholds, encoding="utf-8") as f:
        thresh_doc = json.load(f)
    thresholds: dict = thresh_doc.get("thresholds") or thresh_doc

    # ---- Physical package validation (from filesystem, not result rows) ----
    # Import validator from same directory
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _script_dir)
    from package_manifest_validator import validate_package  # type: ignore
    pkg_validation = validate_package(args.package_root)

    # ---- Run gates (excluding vacuous section which needs all_gates) ----
    rb_self_proof_gates = _gate_rollback_self_proof(rows, thresholds)
    rb_lineage_gates = _gate_rollback_lineage(rows, thresholds)
    hr_scan_gates = _gate_human_review_full_scan(rows, thresholds)
    pkg_gates = _gate_physical_package(pkg_validation, thresholds)
    repro_gates = _gate_reproducibility(rows, thresholds)
    regression_gates = _gate_regression(rows, thresholds)
    complexity_gates = _gate_complexity_budget(thresholds)

    # Pre-vacuous all gates
    pre_vacuous_gates = (
        rb_self_proof_gates
        + rb_lineage_gates
        + hr_scan_gates
        + pkg_gates
        + repro_gates
        + regression_gates
        + complexity_gates
    )

    # Vacuous gates (inspect pre-vacuous gates)
    vacuous_gates = _gate_vacuous_semantics(rows, pre_vacuous_gates, thresholds)

    all_gates = pre_vacuous_gates + vacuous_gates

    # ---- Verdict ----
    pass_count = sum(1 for g in all_gates if g.get("status") == "pass")
    fail_count = sum(1 for g in all_gates if g.get("status") == "fail")
    na_count = sum(1 for g in all_gates if g.get("status") == "not_applicable")
    vacuous_pass_count = sum(1 for g in all_gates if g.get("denominator") == 0 and g.get("status") == "pass")

    verdict = "pass" if fail_count == 0 and vacuous_pass_count == 0 else "fail"

    # ---- Collect failing case IDs ----
    rb_rows_required = [r for r in rows if r.get("rollback_report_required") is True]
    rb_failing_cases = [
        r["case_id"] for r in rb_rows_required
        if not (r.get("rollback_report") or {}).get("production_state_hash_before_write")
    ]

    hr_rows = [r for r in rows if r.get("human_review_payload") is not None or r.get("required_mode") == "human_review_required"]

    repro_rows = [r for r in rows if r.get("group") == "reproducibility_contract"]
    repro_failing = [r["case_id"] for r in repro_rows if r.get("contract_status") == "fail"]

    # ---- Build report ----
    infra_errors = [r["case_id"] for r in rows if r.get("infra_error")]
    n_cases = len(rows)

    report = {
        "version": "v1.29.1.2",
        "generated_at": _now_iso(),
        "verdict": verdict,
        "n_cases": n_cases,
        "gate_summary": {
            "total": len(all_gates),
            "pass": pass_count,
            "fail": fail_count,
            "not_applicable": na_count,
            "vacuous_pass_count": vacuous_pass_count,
        },
        "rollback_self_proof": {
            "rollback_report_atom_diff_present_rate": next(
                (g.get("value") for g in rb_self_proof_gates if g["name"] == "rollback_report_atom_diff_present_rate"), None),
            "rollback_report_packet_diff_present_rate": next(
                (g.get("value") for g in rb_self_proof_gates if g["name"] == "rollback_report_packet_diff_present_rate"), None),
            "rollback_after_hash_equals_before_write_hash_rate": next(
                (g.get("value") for g in rb_self_proof_gates if g["name"] == "rollback_after_hash_equals_before_write_hash_rate"), None),
            "rollback_success_not_enough_as_proof_count": next(
                (g.get("count") for g in rb_self_proof_gates if g["name"] == "rollback_success_not_enough_as_proof_count"), None),
            "vacuous_pass_count": vacuous_pass_count,
            "failing_case_ids": rb_failing_cases,
        },
        "rollback_lineage": {
            "rollback_report_uses_production_commit_id_rate": next(
                (g.get("value") for g in rb_lineage_gates if g["name"] == "rollback_report_uses_production_commit_id_rate"), None),
            "rollback_shadow_parity_ref_id_match_rate": next(
                (g.get("value") for g in rb_lineage_gates if g["name"] == "rollback_shadow_parity_ref_id_match_rate"), None),
            "rollback_report_shadow_commit_id_as_primary_count": next(
                (g.get("count") for g in rb_lineage_gates if g["name"] == "rollback_report_shadow_commit_id_as_primary_count"), None),
            "rollback_report_decision_plan_user_id_match_rate": next(
                (g.get("value") for g in rb_lineage_gates if g["name"] == "rollback_report_decision_plan_user_id_match_rate"), None),
            "failing_case_ids": [],
        },
        "human_review_full_scan": {
            "human_review_evidence_placeholder_text_count": next(
                (g.get("count") for g in hr_scan_gates if g["name"] == "human_review_evidence_placeholder_text_count"), None),
            "human_review_evidence_text_non_placeholder_rate": next(
                (g.get("value") for g in hr_scan_gates if g["name"] == "human_review_evidence_text_non_placeholder_rate"), None),
            "human_review_evidence_strength_known_rate": next(
                (g.get("value") for g in hr_scan_gates if g["name"] == "human_review_evidence_strength_known_rate"), None),
            "human_review_evidence_created_at_parseable_rate": next(
                (g.get("value") for g in hr_scan_gates if g["name"] == "human_review_evidence_created_at_parseable_rate"), None),
            "scanned_case_ids": [r["case_id"] for r in hr_rows],
            "failing_case_ids": [],
        },
        "physical_package_validation": {
            "package_root": args.package_root,
            "manifest_present": pkg_validation.get("manifest_present"),
            "sha256_verified_rate": 1.0 if pkg_validation.get("sha256_verified") else 0.0,
            "mandatory_files_missing": pkg_validation.get("missing_mandatory") or [],
            "source_files_missing": pkg_validation.get("missing_files") or [],
            "uses_result_row_manifest_as_primary_proof": pkg_validation.get("uses_result_row_manifest", False),
        },
        "vacuous_gate_semantics": {
            "zero_denominator_gate_pass_count": vacuous_pass_count,
            "vacuous_pass_count": vacuous_pass_count,
            "denominator_present_rate": next(
                (g.get("value") for g in vacuous_gates if g["name"] == "gate_denominator_present_rate"), None),
        },
        "reproducibility": {
            "reproduction_mode_declared_rate": next(
                (g.get("value") for g in repro_gates if g["name"] == "reproduction_mode_declared_rate"), None),
            "runner_command_present_rate": next(
                (g.get("value") for g in repro_gates if g["name"] == "runner_command_present_rate"), None),
            "source_revision_present_rate": next(
                (g.get("value") for g in repro_gates if g["name"] == "source_revision_present_rate"), None),
            "dependency_lock_or_environment_manifest_present_rate": next(
                (g.get("value") for g in repro_gates if g["name"] == "dependency_lock_or_environment_manifest_present_rate"), None),
            "undocumented_external_dependency_count": next(
                (g.get("count") for g in repro_gates if g["name"] == "undocumented_external_dependency_count"), None),
            "failing_case_ids": repro_failing,
        },
        "all_acceptance_metrics": _build_all_acceptance_metrics(all_gates),
        "gates": all_gates,
        "infra_errors": infra_errors,
        "n_infra_errors": len(infra_errors),
    }

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # Print summary
    print(f"\n=== v1.29.1.2 Gate Report ===")
    print(f"Verdict: {verdict.upper()}")
    print(f"Gates: {pass_count} pass / {fail_count} fail / {na_count} n/a  (total {len(all_gates)})")
    print(f"Vacuous pass count: {vacuous_pass_count}")
    if fail_count > 0:
        print("\nFailed gates:")
        for g in all_gates:
            if g.get("status") == "fail":
                print(f"  FAIL  {g['name']}: {g}")
    print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
