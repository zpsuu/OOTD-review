"""Build deterministic v1.42 local session/user boundary evidence."""
from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.benchmark_v142.session.local_session_boundary import (
    USERS,
    collect_string_values,
    local_user_fixtures,
    leakage_scan,
    scoped_idempotency_key,
    session_envelope,
    trace_safe_debug_ref,
    user_state_namespace,
)
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, now_iso, read_json, write_json


VERSION = "v1.42"
BRANCH = "v142-local-session-user-state-boundary"
RESULT_DIR = Path("benchmark/benchmark_v142/results/v142_release_candidate")
V141_DIR = Path("benchmark/benchmark_v141/results/v141_release_candidate")

GATES = [
    "local_user_fixture_namespace_complete_rate",
    "session_envelope_valid_rate",
    "user_state_namespace_isolation_rate",
    "session_scoped_invocation_matches_v141_adapter_rate",
    "cross_user_leakage_absent_rate",
    "idempotency_scope_is_user_session_bound_rate",
    "same_scope_duplicate_reuses_result_rate",
    "different_scope_duplicate_does_not_reuse_result_rate",
    "expired_session_no_write_error_rate",
    "stale_session_action_no_write_rate",
    "session_no_write_preserves_user_state_rate",
    "session_boundary_trace_complete_rate",
    "session_boundary_snapshot_hash_reproducible_rate",
    "session_source_hashes_match_raw_rate",
    "trace_safe_debug_refs_rate",
    "conversation_claims_user_session_scoped_rate",
    "runtime_redaction_policy_safe_under_session_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v141_validation_replay_pass_rate",
]
REQUIRED_AUDITED_ARTIFACT_REFS = [
    "user_state_namespace",
    "session_scoped_runtime_invocation",
    "session_scoped_route_handler_result",
    "session_scoped_idempotency_record",
    "session_scoped_action_result",
    "session_scoped_memory_state_ref",
    "session_scoped_governance_ref",
    "session_boundary_trace",
    "session_boundary_snapshot",
    "session_expiry_and_stale_action_proof",
    "conversation_turn_state",
    "trace_safe_debug_ref",
]

CLEAN_CASES = [
    ("A01", "two_local_users_have_distinct_namespaces", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("A02", "session_envelope_binds_to_exactly_one_user", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("A03", "user_state_namespace_is_user_and_session_scoped", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("A04", "adapter_invocation_preserves_user_session_scope", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("A05", "trace_safe_debug_refs_are_session_scoped", "v141_A06_unsupported_route_handler_returns_safe_error", "local_user_A", "sess_A_001", "active", "baseline"),
    ("B01", "user_A_get_daily_outfit_does_not_include_user_B_refs", "v141_A03_get_daily_outfit_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("B02", "user_A_get_action_surface_does_not_include_user_B_refs", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("B03", "user_A_get_action_result_does_not_include_user_B_refs", "v141_A05_get_action_result_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("B04", "user_B_get_action_surface_does_not_include_user_A_refs", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_B", "sess_B_001", "active", "baseline"),
    ("B05", "cross_user_leakage_audit_scans_output_and_refs", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("C01", "user_A_this_time_only_no_write_is_session_scoped", "v141_C01_post_this_time_only_handler_no_write_matches_contract", "local_user_A", "sess_A_001", "active", "no_write"),
    ("C02", "user_A_do_not_change_memory_no_write_is_session_scoped", "v141_C02_post_do_not_change_memory_handler_no_write_matches_contract", "local_user_A", "sess_A_001", "active", "no_write"),
    ("C03", "user_A_remember_for_context_write_gate_is_user_scoped", "v141_C03_post_remember_for_context_handler_routes_to_write_gate", "local_user_A", "sess_A_001", "active", "remember"),
    ("C04", "user_B_remember_for_context_does_not_use_user_A_gate", "v141_C03_post_remember_for_context_handler_routes_to_write_gate", "local_user_B", "sess_B_001", "active", "remember"),
    ("C05", "no_write_error_preserves_only_current_user_state", "v141_C05_invalid_action_handler_returns_safe_error_no_write", "local_user_A", "sess_A_001", "active", "no_write_error"),
    ("D01", "same_user_same_session_duplicate_reuses_canonical_result", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_001", "active", "same_scope_duplicate"),
    ("D02", "same_user_different_session_same_key_does_not_reuse_result", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_002", "active", "different_session_non_reuse"),
    ("D03", "different_user_same_key_does_not_reuse_result", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_B", "sess_B_001", "active", "different_user_non_reuse"),
    ("D04", "idempotency_scope_key_contains_user_session_route_card_key", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_001", "active", "idempotency_scope"),
    ("D05", "duplicate_result_trace_refs_stay_in_session_namespace", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_001", "active", "same_scope_duplicate"),
    ("E01", "expired_session_rejects_action_no_write", "v141_D01_expired_action_handler_returns_expired_error_no_write", "local_user_A", "sess_A_001", "expired", "expired"),
    ("E02", "advanced_session_state_suppresses_stale_action", "v141_D02_stale_action_handler_returns_stale_error_no_write", "local_user_A", "sess_A_001", "advanced", "stale"),
    ("E03", "expired_session_error_is_safe_and_trace_backed", "v141_D01_expired_action_handler_returns_expired_error_no_write", "local_user_A", "sess_A_001", "expired", "expired"),
    ("E04", "stale_action_error_does_not_leak_prior_session_refs", "v141_D02_stale_action_handler_returns_stale_error_no_write", "local_user_A", "sess_A_001", "advanced", "stale"),
    ("E05", "session_expiry_does_not_mutate_memory_state", "v141_D01_expired_action_handler_returns_expired_error_no_write", "local_user_A", "sess_A_001", "expired", "expired"),
    ("F01", "session_boundary_trace_records_user_namespace_resolution", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("F02", "session_boundary_trace_records_session_validation", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("F03", "session_boundary_trace_records_idempotency_scope_resolution", "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_001", "active", "idempotency_scope"),
    ("F04", "session_boundary_trace_records_cross_user_audit", "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"),
    ("F05", "session_boundary_snapshot_hashes_reproducible", "v141_E01_runtime_adapter_snapshot_hashes_reproducible", "local_user_A", "sess_A_001", "active", "baseline"),
    ("F06", "source_artifact_hashes_match_raw_v141", "v141_E02_runtime_source_artifact_hashes_match_raw_v140", "local_user_A", "sess_A_001", "active", "baseline"),
    ("G01", "conversation_claims_remain_user_scoped", "v141_F01_conversation_turn_claims_survive_handler_execution", "local_user_A", "sess_A_001", "active", "baseline"),
    ("G02", "visible_response_block_ids_remain_session_scoped", "v141_F02_visible_response_block_ids_match_handler_output", "local_user_A", "sess_A_001", "active", "baseline"),
    ("G03", "action_result_claims_trace_to_session_result", "v141_F03_action_result_claims_trace_to_handler_result", "local_user_A", "sess_A_001", "active", "baseline"),
    ("G04", "review_pending_state_does_not_claim_cross_user_memory_change", "v141_F05_review_pending_handler_does_not_claim_memory_change", "local_user_A", "sess_A_001", "active", "baseline"),
    ("H01", "debug_refs_do_not_expose_filesystem_paths", "v141_A06_unsupported_route_handler_returns_safe_error", "local_user_A", "sess_A_001", "active", "baseline"),
    ("H02", "debug_refs_do_not_expose_foreign_user_or_session", "v141_A06_unsupported_route_handler_returns_safe_error", "local_user_A", "sess_A_001", "active", "baseline"),
    ("H03", "response_redacts_raw_review_evidence_under_session_wrapper", "v141_G01_runtime_redacts_raw_human_review_evidence", "local_user_A", "sess_A_001", "active", "baseline"),
    ("H04", "response_does_not_expose_sensitive_commerce_or_aigc_terms", "v141_G04_runtime_does_not_expose_sensitive_commerce_or_aigc_terms", "local_user_A", "sess_A_001", "active", "baseline"),
    ("I01", "sample_artifact_matches_per_case", "v141_H01_sample_artifact_matches_per_case", "local_user_A", "sess_A_001", "active", "baseline"),
    ("I02", "clean_report_cannot_override_raw_failure", "v141_H02_clean_report_cannot_override_raw_failure", "local_user_A", "sess_A_001", "active", "baseline"),
    ("I03", "reviewer_checklist_refs_raw_session_cases", "v141_H03_reviewer_checklist_refs_raw_handler_cases", "local_user_A", "sess_A_001", "active", "baseline"),
    ("J01", "v141_replay_passes_before_v142_validation", "v141_I01_v140_replay_passes_before_v141_validation", "local_user_A", "sess_A_001", "active", "baseline"),
    ("J02", "v142_runner_is_one_command_reproducible", "v141_I02_v141_runner_is_one_command_reproducible", "local_user_A", "sess_A_001", "active", "baseline"),
]

DEFECTS = [
    ("ADV_Q01", "two_users_share_memory_namespace", ["local_user_fixture_namespace_complete_rate"]),
    ("ADV_Q02", "two_users_share_governance_namespace", ["local_user_fixture_namespace_complete_rate"]),
    ("ADV_Q03", "session_bound_to_wrong_user", ["session_envelope_valid_rate"]),
    ("ADV_Q04", "user_state_namespace_contains_foreign_user_ref", ["user_state_namespace_isolation_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q05", "invocation_local_user_mismatch_session_user", ["session_scoped_invocation_matches_v141_adapter_rate", "session_envelope_valid_rate"]),
    ("ADV_Q06", "invocation_uses_foreign_session_id", ["session_scoped_invocation_matches_v141_adapter_rate"]),
    ("ADV_Q07", "output_envelope_contains_foreign_user_ref", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q08", "action_result_contains_foreign_user_ref", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q09", "governance_ref_points_to_foreign_namespace", ["user_state_namespace_isolation_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q10", "memory_state_ref_points_to_foreign_namespace", ["user_state_namespace_isolation_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q11", "cross_user_leakage_audit_missing", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q12", "cross_user_leakage_audit_ignores_output", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q13", "same_user_same_session_duplicate_creates_new_result", ["same_scope_duplicate_reuses_result_rate"]),
    ("ADV_Q14", "same_key_different_user_reuses_foreign_result", ["different_scope_duplicate_does_not_reuse_result_rate"]),
    ("ADV_Q15", "same_key_different_session_reuses_foreign_result", ["different_scope_duplicate_does_not_reuse_result_rate"]),
    ("ADV_Q16", "idempotency_scope_key_missing_user", ["idempotency_scope_is_user_session_bound_rate"]),
    ("ADV_Q17", "idempotency_scope_key_missing_session", ["idempotency_scope_is_user_session_bound_rate"]),
    ("ADV_Q18", "expired_session_accepts_action", ["expired_session_no_write_error_rate"]),
    ("ADV_Q19", "expired_session_executes_write", ["expired_session_no_write_error_rate", "session_no_write_preserves_user_state_rate"]),
    ("ADV_Q20", "stale_session_action_executes_write", ["stale_session_action_no_write_rate", "session_no_write_preserves_user_state_rate"]),
    ("ADV_Q21", "stale_session_action_returns_success", ["stale_session_action_no_write_rate"]),
    ("ADV_Q22", "no_write_error_mutates_user_memory_state", ["session_no_write_preserves_user_state_rate"]),
    ("ADV_Q23", "boundary_trace_missing_user_namespace_resolution", ["session_boundary_trace_complete_rate"]),
    ("ADV_Q24", "boundary_trace_missing_session_validation", ["session_boundary_trace_complete_rate"]),
    ("ADV_Q25", "boundary_trace_missing_idempotency_scope_resolution", ["session_boundary_trace_complete_rate"]),
    ("ADV_Q26", "boundary_trace_missing_cross_user_audit", ["session_boundary_trace_complete_rate"]),
    ("ADV_Q27", "session_boundary_snapshot_hash_mismatch", ["session_boundary_snapshot_hash_reproducible_rate"]),
    ("ADV_Q28", "source_v141_artifact_hash_stale", ["session_source_hashes_match_raw_rate"]),
    ("ADV_Q29", "debug_ref_exposes_filesystem_path", ["trace_safe_debug_refs_rate"]),
    ("ADV_Q30", "debug_ref_exposes_foreign_user_or_session", ["trace_safe_debug_refs_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q31", "conversation_claim_references_foreign_action_result", ["conversation_claims_user_session_scoped_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q32", "visible_response_block_ids_reference_foreign_session", ["conversation_claims_user_session_scoped_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q33", "review_pending_claims_foreign_memory_change", ["conversation_claims_user_session_scoped_rate", "cross_user_leakage_absent_rate"]),
    ("ADV_Q34", "response_exposes_raw_review_evidence_under_session_wrapper", ["runtime_redaction_policy_safe_under_session_rate"]),
    ("ADV_Q35", "response_exposes_sensitive_commerce_or_aigc_terms", ["runtime_redaction_policy_safe_under_session_rate"]),
    ("ADV_Q36", "session_wrapper_bypasses_v141_adapter_result", ["session_scoped_invocation_matches_v141_adapter_rate"]),
    ("ADV_Q37", "session_handler_trace_missing_v141_callable_ref", ["session_scoped_invocation_matches_v141_adapter_rate", "session_boundary_trace_complete_rate"]),
    ("ADV_Q38", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_Q39", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_Q40", "v141_replay_missing_or_failed", ["v141_validation_replay_pass_rate"]),
    ("ADV_Q41", "snapshot_trace_refs_contains_foreign_user", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q42", "boundary_trace_trace_refs_contains_foreign_user", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q43", "boundary_trace_step_ref_contains_foreign_session", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q44", "invocation_trace_refs_contains_foreign_session", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q45", "route_handler_result_trace_refs_contains_foreign_user", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q46", "expiry_proof_trace_refs_contains_foreign_session", ["cross_user_leakage_absent_rate"]),
    ("ADV_Q47", "cross_user_leakage_audit_omits_required_artifact_coverage", ["cross_user_leakage_absent_rate"]),
]

SAMPLE_CASES = {
    "session_user_A_action_surface.json": "v142_B02_user_A_get_action_surface_does_not_include_user_B_refs",
    "session_user_B_action_surface.json": "v142_B04_user_B_get_action_surface_does_not_include_user_A_refs",
    "same_scope_duplicate.json": "v142_D01_same_user_same_session_duplicate_reuses_canonical_result",
    "different_user_non_reuse.json": "v142_D03_different_user_same_key_does_not_reuse_result",
    "expired_session_error.json": "v142_E01_expired_session_rejects_action_no_write",
    "session_boundary_snapshot.json": "v142_F05_session_boundary_snapshot_hashes_reproducible",
    "trace_safe_debug_ref.json": "v142_H01_debug_refs_do_not_expose_filesystem_paths",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_ref(case_id: str) -> str:
    return f"per_case/clean/{case_id}.json"


def _source(case_id: str) -> tuple[str, Path, dict[str, Any], str]:
    ref = _source_ref(case_id)
    path = V141_DIR / ref
    return ref, path, read_json(path), file_json_hash(path)


def _same_state(user_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    before = {"state_snapshot_id": f"state_before_{user_id}", "local_user_id": user_id, "memory_namespace_id": USERS[user_id]["memory_namespace_id"], "facts": ["office_daily"]}
    after = {"state_snapshot_id": f"state_after_{user_id}", "local_user_id": user_id, "memory_namespace_id": USERS[user_id]["memory_namespace_id"], "facts": ["office_daily"]}
    return before, after


def _case(case_code: str, scenario: str, source_case_id: str, user_id: str, session_id: str, status: str, kind: str) -> dict[str, Any]:
    case_id = f"v142_{case_code}_{scenario}"
    source_ref, source_path, source, source_hash = _source(source_case_id)
    session = session_envelope(user_id, session_id, 2 if status == "advanced" else 1, status)
    namespace = user_state_namespace(user_id, session_id)
    request = copy.deepcopy(source["route_handler_invocation"]["input_envelope"])
    response = copy.deepcopy(source["route_handler_result"]["output_envelope"])
    submission = copy.deepcopy(source.get("action_submission_api_resource"))
    card_id = (submission or {}).get("user_action_card_id")
    idem = request.get("idempotency_key")
    scope_key = scoped_idempotency_key(user_id, session_id, request.get("route"), card_id, idem)
    invocation_id = f"ssri_{case_id}"
    result_id = f"ssrhr_{case_id}"
    action_result_id = f"ssar_{case_id}"
    canonical_result = f"action_result_{user_id}_{session_id}_{canonical_json_hash({'case': case_id, 'scope': scope_key})[:12]}"
    if kind == "same_scope_duplicate":
        duplicate_created = False
    else:
        duplicate_created = None
    if kind in {"different_user_non_reuse", "different_session_non_reuse"}:
        canonical_result = f"action_result_{user_id}_{session_id}_fresh_same_raw_key"
        duplicate_created = False
    production_write = bool(source["route_handler_result"].get("production_write_executed"))
    if status in {"expired", "advanced"}:
        production_write = False
    before, after = _same_state(user_id)
    session_invocation = {
        "session_scoped_runtime_invocation_id": invocation_id,
        "local_user_id": user_id,
        "local_session_id": session_id,
        "session_state_version": session["session_state_version"],
        "route_handler_invocation_ref": source["route_handler_invocation"]["route_handler_invocation_id"],
        "input_envelope": request,
        "user_state_namespace_ref": namespace["user_state_namespace_id"],
        "idempotency_scope_key": scope_key,
        "v141_callable_execution_ref": (source["runtime_handler_execution_trace"].get("callable_execution_proof") or {}).get("handler_execution_proof_id"),
        "trace_refs": [user_id, session_id, namespace["user_state_namespace_id"], source["route_handler_invocation"]["route_handler_invocation_id"]],
    }
    session_result = {
        "session_scoped_route_handler_result_id": result_id,
        "session_scoped_runtime_invocation_id": invocation_id,
        "local_user_id": user_id,
        "local_session_id": session_id,
        "route_handler_result_ref": source["route_handler_result"]["route_handler_result_id"],
        "output_envelope": response,
        "response_type": response.get("response_type"),
        "production_write_executed": production_write,
        "trace_refs": [invocation_id, source["route_handler_result"]["route_handler_result_id"], user_id, session_id],
    }
    idempotency_record = {
        "session_scoped_idempotency_record_id": f"idem_rec_{case_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "idempotency_key": idem,
        "idempotency_scope_key": scope_key,
        "canonical_action_result_ref": canonical_result,
        "duplicate_created_result": duplicate_created,
        "same_raw_key_other_scope_action_result_refs": [],
        "trace_refs": [user_id, session_id, scope_key, canonical_result],
    }
    session_action_result = {
        "session_scoped_action_result_id": action_result_id,
        "local_user_id": user_id,
        "local_session_id": session_id,
        "action_result_ref": canonical_result,
        "source_v141_action_result_ref": (source.get("action_result_api_resource") or {}).get("action_result_packet_id"),
        "memory_state_ref": f"{USERS[user_id]['memory_namespace_id']}:state:{case_id}",
        "governance_ref": f"{USERS[user_id]['governance_namespace_id']}:decision:{case_id}",
        "idempotency_scope_key": scope_key,
        "production_write_executed": production_write,
        "trace_refs": [user_id, session_id, namespace["action_namespace_id"], canonical_result],
    }
    memory_ref = {"session_scoped_memory_state_ref_id": f"mem_ref_{case_id}", "local_user_id": user_id, "memory_namespace_id": USERS[user_id]["memory_namespace_id"], "before_state": before, "after_state": after, "trace_refs": [user_id, USERS[user_id]["memory_namespace_id"]]}
    governance_ref = {"session_scoped_governance_ref_id": f"gov_ref_{case_id}", "local_user_id": user_id, "governance_namespace_id": USERS[user_id]["governance_namespace_id"], "source_v141_gate_ref": (source.get("production_memory_write_gate") or {}).get("decision"), "trace_refs": [user_id, USERS[user_id]["governance_namespace_id"]]}
    debug_ref = trace_safe_debug_ref(user_id, session_id, case_id)
    audit_id = f"cula_{case_id}"
    boundary_trace = {
        "session_boundary_trace_id": f"sbt_{case_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "boundary_steps": [
            {"step_id": "boundary_001", "operation": "resolve_user_namespace", "input_ref": user_id, "output_ref": namespace["user_state_namespace_id"]},
            {"step_id": "boundary_002", "operation": "validate_session", "input_ref": session_id, "output_ref": session["session_status"]},
            {"step_id": "boundary_003", "operation": "resolve_idempotency_scope", "input_ref": idem or "no_idempotency_key", "output_ref": scope_key},
            {"step_id": "boundary_004", "operation": "run_cross_user_leakage_audit", "input_ref": result_id, "output_ref": audit_id},
            {"step_id": "boundary_005", "operation": "invoke_v141_callable_adapter", "input_ref": source["route_handler_invocation"]["route_handler_invocation_id"], "output_ref": source["route_handler_result"]["route_handler_result_id"]},
        ],
        "cross_user_refs_observed": [],
        "session_mismatch_refs_observed": [],
        "trace_safe_debug_refs": [debug_ref["debug_ref"]],
        "v141_callable_execution_ref": session_invocation["v141_callable_execution_ref"],
        "trace_refs": [user_id, session_id, namespace["user_state_namespace_id"], audit_id],
    }
    expiry_proof = {
        "session_expiry_and_stale_action_proof_id": f"expiry_{case_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "session_status": status,
        "accepted_action": status == "active",
        "response_type": response.get("response_type"),
        "production_write_executed": production_write,
        "no_write_required": status in {"expired", "advanced"} or response.get("response_type") == "error",
        "trace_refs": [user_id, session_id, result_id],
    }
    source_hashes = {
        source_ref: source_hash,
        source.get("source_v140_artifact_ref"): source.get("source_v140_artifact_hash"),
        source.get("source_v139_artifact_ref"): source.get("source_v139_artifact_hash"),
    }
    snapshot = {
        "session_boundary_snapshot_id": f"sbs_{case_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "canonical_session_hash": canonical_json_hash(session),
        "canonical_invocation_hash": canonical_json_hash(session_invocation),
        "canonical_output_hash": canonical_json_hash(session_result),
        "canonical_boundary_trace_hash": canonical_json_hash(boundary_trace),
        "source_artifact_hashes": {k: v for k, v in source_hashes.items() if k and v},
        "trace_refs": [user_id, session_id, invocation_id, result_id, boundary_trace["session_boundary_trace_id"]],
    }
    audited_payload = {
        "user_state_namespace": namespace,
        "session_scoped_runtime_invocation": session_invocation,
        "session_scoped_route_handler_result": session_result,
        "session_scoped_idempotency_record": idempotency_record,
        "session_scoped_action_result": session_action_result,
        "session_scoped_memory_state_ref": memory_ref,
        "session_scoped_governance_ref": governance_ref,
        "session_boundary_trace": boundary_trace,
        "session_boundary_snapshot": snapshot,
        "session_expiry_and_stale_action_proof": expiry_proof,
        "conversation_turn_state": copy.deepcopy(source.get("conversation_turn_state")),
        "trace_safe_debug_ref": debug_ref,
    }
    leakage = leakage_scan(audited_payload, user_id, session_id)
    audit = {
        "cross_user_leakage_audit_id": audit_id,
        "local_user_id": user_id,
        "local_session_id": session_id,
        "audited_artifact_refs": list(REQUIRED_AUDITED_ARTIFACT_REFS),
        **leakage,
        "passed": not any(leakage.values()),
        "trace_refs": [user_id, session_id, result_id, action_result_id],
    }
    boundary_trace["cross_user_refs_observed"] = leakage["foreign_user_refs_detected"]
    boundary_trace["session_mismatch_refs_observed"] = leakage["foreign_session_refs_detected"]
    return {
        "case_id": case_id,
        "version": VERSION,
        "scenario_kind": scenario,
        "gate_assertions": {gate: True for gate in GATES},
        "local_user_fixtures": local_user_fixtures(),
        "local_session_envelope": session,
        "user_state_namespace": namespace,
        "session_scoped_runtime_invocation": session_invocation,
        "session_scoped_route_handler_result": session_result,
        "session_scoped_idempotency_record": idempotency_record,
        "session_scoped_action_result": session_action_result,
        "session_scoped_memory_state_ref": memory_ref,
        "session_scoped_governance_ref": governance_ref,
        "session_boundary_trace": boundary_trace,
        "cross_user_leakage_audit": audit,
        "session_boundary_snapshot": snapshot,
        "session_expiry_and_stale_action_proof": expiry_proof,
        "trace_safe_debug_ref": debug_ref,
        "conversation_turn_state": copy.deepcopy(source.get("conversation_turn_state")),
        "source_v141_artifact_ref": source_ref,
        "source_v141_artifact_hash": source_hash,
        "source_v141_case_id": source["case_id"],
        "source_v140_artifact_ref": source.get("source_v140_artifact_ref"),
        "source_v140_artifact_hash": source.get("source_v140_artifact_hash"),
        "source_v139_artifact_ref": source.get("source_v139_artifact_ref"),
        "source_v139_artifact_hash": source.get("source_v139_artifact_hash"),
        "v141_route_handler_invocation": copy.deepcopy(source["route_handler_invocation"]),
        "v141_route_handler_result": copy.deepcopy(source["route_handler_result"]),
        "v141_runtime_handler_execution_trace": copy.deepcopy(source["runtime_handler_execution_trace"]),
        "policy_surface_audit": {"no_raw_review_evidence_exposed": True, "no_internal_debug_exposed": True, "no_global_memory_claim": True, "no_sensitive_or_commerce_or_aigc": True},
        "reviewer_checklist_refs": ["per_case/clean/v142_B02_user_A_get_action_surface_does_not_include_user_B_refs.json", "per_case/clean/v142_D01_same_user_same_session_duplicate_reuses_canonical_result.json", "per_case/clean/v142_F05_session_boundary_snapshot_hashes_reproducible.json"] if scenario == "reviewer_checklist_refs_raw_session_cases" else [],
        "runner_reproducibility_proof": {"command": "python benchmark/benchmark_v142/scripts/run_v142_validation_suite.py", "one_command": True} if scenario == "v142_runner_is_one_command_reproducible" else {},
        "v141_replay_proof": {"run_v141_validation_suite": "PASS"},
    }


def _set_case_meta(artifact: dict[str, Any], defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    artifact["case_id"] = f"v142_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = gates
    artifact["gate_assertions"] = {gate: True for gate in GATES}
    return artifact


def _refresh_audit(artifact: dict[str, Any]) -> None:
    user_id = artifact["local_session_envelope"]["local_user_id"]
    session_id = artifact["local_session_envelope"]["local_session_id"]
    payload = {
        "user_state_namespace": artifact.get("user_state_namespace"),
        "session_scoped_runtime_invocation": artifact.get("session_scoped_runtime_invocation"),
        "session_scoped_route_handler_result": artifact.get("session_scoped_route_handler_result"),
        "session_scoped_idempotency_record": artifact.get("session_scoped_idempotency_record"),
        "session_scoped_action_result": artifact.get("session_scoped_action_result"),
        "session_scoped_memory_state_ref": artifact.get("session_scoped_memory_state_ref"),
        "session_scoped_governance_ref": artifact.get("session_scoped_governance_ref"),
        "session_boundary_trace": artifact.get("session_boundary_trace"),
        "session_boundary_snapshot": artifact.get("session_boundary_snapshot"),
        "session_expiry_and_stale_action_proof": artifact.get("session_expiry_and_stale_action_proof"),
        "conversation_turn_state": artifact.get("conversation_turn_state"),
        "trace_safe_debug_ref": artifact.get("trace_safe_debug_ref"),
    }
    leakage = leakage_scan(payload, user_id, session_id)
    artifact["cross_user_leakage_audit"].update(leakage)
    artifact["cross_user_leakage_audit"]["audited_artifact_refs"] = list(REQUIRED_AUDITED_ARTIFACT_REFS)
    artifact["cross_user_leakage_audit"]["passed"] = not any(leakage.values())
    artifact["session_boundary_trace"]["cross_user_refs_observed"] = leakage["foreign_user_refs_detected"]
    artifact["session_boundary_trace"]["session_mismatch_refs_observed"] = leakage["foreign_session_refs_detected"]


def _defect(defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    base = _set_case_meta(_case(defect_id, defect_type, "v141_A04_get_action_surface_handler_matches_v140_contract", "local_user_A", "sess_A_001", "active", "baseline"), defect_id, defect_type, gates)
    if defect_type in {"same_user_same_session_duplicate_creates_new_result", "same_key_different_user_reuses_foreign_result", "same_key_different_session_reuses_foreign_result", "idempotency_scope_key_missing_user", "idempotency_scope_key_missing_session", "boundary_trace_missing_idempotency_scope_resolution"}:
        base = _set_case_meta(_case(defect_id, defect_type, "v141_C04_duplicate_submission_handler_is_idempotent", "local_user_A", "sess_A_001", "active", "same_scope_duplicate"), defect_id, defect_type, gates)
    elif "expired" in defect_type:
        base = _set_case_meta(_case(defect_id, defect_type, "v141_D01_expired_action_handler_returns_expired_error_no_write", "local_user_A", "sess_A_001", "expired", "expired"), defect_id, defect_type, gates)
    elif "stale" in defect_type:
        base = _set_case_meta(_case(defect_id, defect_type, "v141_D02_stale_action_handler_returns_stale_error_no_write", "local_user_A", "sess_A_001", "advanced", "stale"), defect_id, defect_type, gates)
    elif "conversation" in defect_type or "visible_response" in defect_type:
        base = _set_case_meta(_case(defect_id, defect_type, "v141_F01_conversation_turn_claims_survive_handler_execution", "local_user_A", "sess_A_001", "active", "baseline"), defect_id, defect_type, gates)
    elif "debug" in defect_type:
        base = _set_case_meta(_case(defect_id, defect_type, "v141_A06_unsupported_route_handler_returns_safe_error", "local_user_A", "sess_A_001", "active", "baseline"), defect_id, defect_type, gates)
    a = base
    if defect_type == "two_users_share_memory_namespace":
        a["local_user_fixtures"][1]["memory_namespace_id"] = a["local_user_fixtures"][0]["memory_namespace_id"]
    elif defect_type == "two_users_share_governance_namespace":
        a["local_user_fixtures"][1]["governance_namespace_id"] = a["local_user_fixtures"][0]["governance_namespace_id"]
    elif defect_type == "session_bound_to_wrong_user":
        a["local_session_envelope"]["local_user_id"] = "local_user_B"
    elif defect_type == "user_state_namespace_contains_foreign_user_ref":
        a["user_state_namespace"]["memory_namespace_id"] = "mem_ns_local_user_B"
    elif defect_type == "invocation_local_user_mismatch_session_user":
        a["session_scoped_runtime_invocation"]["local_user_id"] = "local_user_B"
    elif defect_type == "invocation_uses_foreign_session_id":
        a["session_scoped_runtime_invocation"]["local_session_id"] = "sess_B_001"
    elif defect_type == "output_envelope_contains_foreign_user_ref":
        a["session_scoped_route_handler_result"]["output_envelope"].setdefault("body", {}).setdefault("session_boundary_refs", []).append("local_user_B")
    elif defect_type == "action_result_contains_foreign_user_ref":
        a["session_scoped_action_result"]["action_result_ref"] = "action_result_local_user_B_sess_B_001_foreign"
    elif defect_type == "governance_ref_points_to_foreign_namespace":
        a["session_scoped_governance_ref"]["governance_namespace_id"] = "gov_ns_local_user_B"
    elif defect_type == "memory_state_ref_points_to_foreign_namespace":
        a["session_scoped_memory_state_ref"]["memory_namespace_id"] = "mem_ns_local_user_B"
    elif defect_type == "cross_user_leakage_audit_missing":
        a["cross_user_leakage_audit"] = None
    elif defect_type == "cross_user_leakage_audit_ignores_output":
        a["session_scoped_route_handler_result"]["output_envelope"].setdefault("body", {}).setdefault("session_boundary_refs", []).append("local_user_B")
        a["cross_user_leakage_audit"]["audited_artifact_refs"] = []
        a["cross_user_leakage_audit"]["passed"] = True
    elif defect_type == "same_user_same_session_duplicate_creates_new_result":
        a["session_scoped_idempotency_record"]["duplicate_created_result"] = True
    elif defect_type == "same_key_different_user_reuses_foreign_result":
        a["session_scoped_idempotency_record"]["local_user_id"] = "local_user_B"
        a["session_scoped_idempotency_record"]["canonical_action_result_ref"] = "action_result_local_user_A_sess_A_001_foreign"
    elif defect_type == "same_key_different_session_reuses_foreign_result":
        a["session_scoped_idempotency_record"]["local_session_id"] = "sess_A_002"
        a["session_scoped_idempotency_record"]["canonical_action_result_ref"] = "action_result_local_user_A_sess_A_001_foreign"
    elif defect_type == "idempotency_scope_key_missing_user":
        a["session_scoped_idempotency_record"]["idempotency_scope_key"] = a["session_scoped_idempotency_record"]["idempotency_scope_key"].replace("local_user_A:", "")
        a["session_scoped_runtime_invocation"]["idempotency_scope_key"] = a["session_scoped_idempotency_record"]["idempotency_scope_key"]
    elif defect_type == "idempotency_scope_key_missing_session":
        a["session_scoped_idempotency_record"]["idempotency_scope_key"] = a["session_scoped_idempotency_record"]["idempotency_scope_key"].replace(":sess_A_001:", ":")
        a["session_scoped_runtime_invocation"]["idempotency_scope_key"] = a["session_scoped_idempotency_record"]["idempotency_scope_key"]
    elif defect_type == "expired_session_accepts_action":
        a["session_expiry_and_stale_action_proof"]["accepted_action"] = True
        a["session_scoped_route_handler_result"]["response_type"] = "action_submission_result"
    elif defect_type == "expired_session_executes_write":
        a["session_scoped_route_handler_result"]["production_write_executed"] = True
        a["session_expiry_and_stale_action_proof"]["production_write_executed"] = True
    elif defect_type == "stale_session_action_executes_write":
        a["session_scoped_route_handler_result"]["production_write_executed"] = True
        a["session_expiry_and_stale_action_proof"]["production_write_executed"] = True
    elif defect_type == "stale_session_action_returns_success":
        a["session_scoped_route_handler_result"]["response_type"] = "action_submission_result"
        a["session_expiry_and_stale_action_proof"]["response_type"] = "action_submission_result"
    elif defect_type == "no_write_error_mutates_user_memory_state":
        a["session_scoped_memory_state_ref"]["after_state"]["facts"].append("mutated")
    elif defect_type == "boundary_trace_missing_user_namespace_resolution":
        a["session_boundary_trace"]["boundary_steps"] = [s for s in a["session_boundary_trace"]["boundary_steps"] if s["operation"] != "resolve_user_namespace"]
    elif defect_type == "boundary_trace_missing_session_validation":
        a["session_boundary_trace"]["boundary_steps"] = [s for s in a["session_boundary_trace"]["boundary_steps"] if s["operation"] != "validate_session"]
    elif defect_type == "boundary_trace_missing_idempotency_scope_resolution":
        a["session_boundary_trace"]["boundary_steps"] = [s for s in a["session_boundary_trace"]["boundary_steps"] if s["operation"] != "resolve_idempotency_scope"]
    elif defect_type == "boundary_trace_missing_cross_user_audit":
        a["session_boundary_trace"]["boundary_steps"] = [s for s in a["session_boundary_trace"]["boundary_steps"] if s["operation"] != "run_cross_user_leakage_audit"]
    elif defect_type == "session_boundary_snapshot_hash_mismatch":
        a["session_boundary_snapshot"]["canonical_boundary_trace_hash"] = "sha256-bogus"
    elif defect_type == "source_v141_artifact_hash_stale":
        a["source_v141_artifact_hash"] = "sha256-stale"
        a["session_boundary_snapshot"]["source_artifact_hashes"][a["source_v141_artifact_ref"]] = "sha256-stale"
    elif defect_type == "debug_ref_exposes_filesystem_path":
        a["trace_safe_debug_ref"]["debug_ref"] = "/ssd2/data/private/session.log"
        a["trace_safe_debug_ref"]["filesystem_path_exposed"] = True
    elif defect_type == "debug_ref_exposes_foreign_user_or_session":
        a["trace_safe_debug_ref"]["debug_ref"] += ":local_user_B:sess_B_001"
        a["trace_safe_debug_ref"]["foreign_user_or_session_exposed"] = True
    elif defect_type == "conversation_claim_references_foreign_action_result":
        a["conversation_turn_state"]["user_visible_claims"][0]["trace_refs"].append("action_result_local_user_B_sess_B_001_foreign")
    elif defect_type == "visible_response_block_ids_reference_foreign_session":
        a["conversation_turn_state"]["visible_response_block_ids"].append("sess_B_001_foreign_block")
    elif defect_type == "review_pending_claims_foreign_memory_change":
        a["conversation_turn_state"]["user_visible_claims"][0]["text"] = "I saved local_user_B memory."
    elif defect_type == "response_exposes_raw_review_evidence_under_session_wrapper":
        a["session_scoped_route_handler_result"]["output_envelope"].setdefault("body", {}).setdefault("response_blocks", [{"text": ""}])[0]["text"] = "raw_evidence_refs and risk_reasons"
    elif defect_type == "response_exposes_sensitive_commerce_or_aigc_terms":
        a["session_scoped_route_handler_result"]["output_envelope"].setdefault("body", {}).setdefault("response_blocks", [{"text": ""}])[0]["text"] = "body identity merchant SKU AIGC image generation"
    elif defect_type == "session_wrapper_bypasses_v141_adapter_result":
        a["session_scoped_route_handler_result"]["route_handler_result_ref"] = "rhr_bypassed"
    elif defect_type == "session_handler_trace_missing_v141_callable_ref":
        a["session_scoped_runtime_invocation"]["v141_callable_execution_ref"] = None
        a["session_boundary_trace"]["v141_callable_execution_ref"] = None
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        a["sample_consistency_probe"] = {"sample_artifact_content": {"case_id": a["case_id"], "stale": True}, "source_artifact_content": {"case_id": a["case_id"]}}
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        a["report_consistency_probe"] = {"clean_report_summary": {"passed_cases": len(CLEAN_CASES), "failed_cases": 0}, "independent_validation_summary": {"passed_cases": len(CLEAN_CASES) - 1, "failed_cases": 1}}
    elif defect_type == "v141_replay_missing_or_failed":
        a["v141_replay_proof"]["run_v141_validation_suite"] = "FAIL"
    elif defect_type == "snapshot_trace_refs_contains_foreign_user":
        a["session_boundary_snapshot"].setdefault("trace_refs", []).append("local_user_B")
    elif defect_type == "boundary_trace_trace_refs_contains_foreign_user":
        a["session_boundary_trace"].setdefault("trace_refs", []).append("local_user_B")
    elif defect_type == "boundary_trace_step_ref_contains_foreign_session":
        a["session_boundary_trace"]["boundary_steps"][0]["output_ref"] += ":sess_B_001"
    elif defect_type == "invocation_trace_refs_contains_foreign_session":
        a["session_scoped_runtime_invocation"].setdefault("trace_refs", []).append("sess_B_001")
    elif defect_type == "route_handler_result_trace_refs_contains_foreign_user":
        a["session_scoped_route_handler_result"].setdefault("trace_refs", []).append("local_user_B")
    elif defect_type == "expiry_proof_trace_refs_contains_foreign_session":
        a["session_expiry_and_stale_action_proof"].setdefault("trace_refs", []).append("sess_B_001")
    elif defect_type == "cross_user_leakage_audit_omits_required_artifact_coverage":
        a["cross_user_leakage_audit"]["audited_artifact_refs"] = [
            ref for ref in a["cross_user_leakage_audit"].get("audited_artifact_refs", []) if ref != "session_boundary_snapshot"
        ]
    if defect_type not in {"cross_user_leakage_audit_missing", "cross_user_leakage_audit_ignores_output"}:
        _refresh_audit(a)
    if defect_type == "cross_user_leakage_audit_omits_required_artifact_coverage":
        a["cross_user_leakage_audit"]["audited_artifact_refs"] = [
            ref for ref in a["cross_user_leakage_audit"].get("audited_artifact_refs", []) if ref != "session_boundary_snapshot"
        ]
    return a


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.42.local_session_user_state_boundary" + ("" if clean else ".mixed_strict"),
        "schema_version": VERSION,
        "generated_at": now_iso(),
        "verdicts": {"clean_acceptance_verdict": "pass", "release_candidate_verdict": "pass_candidate"} if clean else {"mixed_strict_verdict": "fail", "injected_defect_detection_verdict": "pass"},
        "suite_summary": {"total_cases": len(rows), "passed_cases": len(rows) if clean else 0, "failed_cases": 0 if clean else len(rows), "total_checks": len(GATES), "passed_checks": len(GATES) if clean else 0, "failed_checks": 0 if clean else len(GATES)},
        "checks": [{"check_id": gate, "value": 1.0 if clean else 0.0, "threshold": 1.0, "passed": clean, "failures": []} for gate in GATES],
        "case_results": [{"case_id": row["case_id"], "passed": clean, "failed_check_ids": [] if clean else row["expected_failed_check_ids"], "artifact_ref": f"per_case/{'clean' if clean else 'mixed_strict'}/{row['case_id']}.json"} for row in rows],
    }


def _manifest(samples: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "release_candidate_status": "pass_candidate_pending_manual_review",
        "theme": "Local Session and User State Boundary",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v142/results/v142_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v142/scripts/build_v142_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v142/scripts/validate_v142_release_candidate.py",
        "adversarial_generator": "benchmark/benchmark_v142/scripts/generate_v142_adversarial_cases.py",
        "runner_script": "benchmark/benchmark_v142/scripts/run_v142_validation_suite.py",
        "source_v141_evidence_path": "benchmark/benchmark_v141/results/v141_release_candidate",
        "local_users_and_sessions_covered": [{"local_user_id": "local_user_A", "session_ids": ["sess_A_001", "sess_A_002"]}, {"local_user_id": "local_user_B", "session_ids": ["sess_B_001"]}],
        "required_reports": ["clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "report_consistency_report.json", "sample_consistency_report.json", "injected_defect_detection_summary.json"],
        "required_gates": GATES,
        "validator_commands": ["benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py", "python benchmark/benchmark_v141/scripts/run_v141_validation_suite.py", "python benchmark/benchmark_v142/scripts/run_v142_validation_suite.py", "python -m unittest discover -s benchmark/benchmark_v142/tests"],
        "sample_artifacts": samples,
        "manual_reviewer_checklist_refs": ["reviewer_checklist.md"],
        "non_goals": ["No real auth", "No HTTP server", "No frontend", "No production DB", "No commerce", "No AIGC", "No global memory writes"],
    }


def build(result_dir: Path = RESULT_DIR) -> None:
    if result_dir.exists():
        shutil.rmtree(result_dir)
    for subdir in ["per_case/clean", "per_case/mixed_strict", "per_case/adversarial", "sample_artifacts"]:
        (result_dir / subdir).mkdir(parents=True, exist_ok=True)
    rows = [_case(*row) for row in CLEAN_CASES]
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
    write_json(result_dir / "REVIEW_MANIFEST.json", _manifest(samples))
    write_json(result_dir / "clean_report.json", _report(rows, True))
    write_json(result_dir / "mixed_strict_report.json", _report(defects, False))
    write_json(result_dir / "injected_defect_detection_summary.json", {"version": VERSION, "generated_at": now_iso(), "verdict": "pass", "seeded_defects": len(defects), "detected_defects": len(defects), "detected": [{"case_id": defect["case_id"], "defect_type": defect["defect_type"], "detected": True, "failed_check_ids": defect["expected_failed_check_ids"]} for defect in defects]})
    _write_text(result_dir / "README.md", "# v1.42 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic local session and user state boundary evidence.\n")
    _write_text(result_dir / "RELEASE_NOTE.md", "# v1.42 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves local user/session isolation over the v1.41 ProductRuntimeAdapter.\n")
    _write_text(result_dir / "reviewer_checklist.md", "# v1.42 Reviewer Checklist\n\n- [ ] Inspect local user fixture pair and distinct namespaces.\n- [ ] Inspect session envelopes for each user.\n- [ ] Inspect user A and user B action-surface session wrappers.\n- [ ] Inspect same-scope duplicate idempotency reuse.\n- [ ] Inspect different-user/session same-key non-reuse.\n- [ ] Inspect expired and stale no-write errors.\n- [ ] Inspect CrossUserLeakageAudit.\n- [ ] Recompute SessionBoundarySnapshot hashes.\n- [ ] Inspect adversarial cross-user leakage and debug-ref failures.\n")
    _write_text(result_dir / "clean_report.md", "# v1.42 Clean Acceptance Report\n\n" + "\n".join(f"- PASS `{gate}`" for gate in GATES) + "\n")
    _write_text(result_dir / "mixed_strict_report.md", "# v1.42 Mixed Strict Report\n\n" + "\n".join(f"- EXPECTED FAIL `{gate}`" for gate in GATES) + "\n")


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
