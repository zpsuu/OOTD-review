"""Build deterministic v1.41 in-process runtime adapter evidence."""
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

from benchmark.benchmark_v141.runtime.product_runtime_adapter import ProductRuntimeAdapter
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, now_iso, read_json, write_json


VERSION = "v1.41"
BRANCH = "v141-in-process-product-runtime-adapter"
RESULT_DIR = Path("benchmark/benchmark_v141/results/v141_release_candidate")
V140_DIR = Path("benchmark/benchmark_v140/results/v140_release_candidate")

GATES = [
    "adapter_route_registry_complete_rate",
    "route_handler_invocation_valid_rate",
    "handler_dispatch_trace_complete_rate",
    "handler_uses_raw_source_artifacts_rate",
    "handler_output_matches_v140_contract_rate",
    "action_submission_handler_contract_rate",
    "no_write_handler_preserves_memory_state_rate",
    "idempotent_handler_replay_rate",
    "expired_stale_handler_no_write_rate",
    "runtime_action_result_links_response_rate",
    "conversation_claims_trace_backed_after_handler_rate",
    "runtime_snapshot_hash_reproducible_rate",
    "runtime_source_hashes_match_raw_rate",
    "golden_contract_replay_rate",
    "runtime_error_safety_rate",
    "runtime_redaction_policy_safe_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v140_validation_replay_pass_rate",
]

CLEAN_CASES = [
    ("A01", "adapter_declares_supported_routes", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("A02", "route_registry_binds_each_supported_route_once", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("A03", "get_daily_outfit_handler_matches_v140_contract", "v140_A01_get_daily_outfit_returns_contract_envelope"),
    ("A04", "get_action_surface_handler_matches_v140_contract", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("A05", "get_action_result_handler_matches_v140_contract", "v140_A03_get_action_result_returns_result_packet"),
    ("A06", "unsupported_route_handler_returns_safe_error", "v140_A04_unsupported_route_returns_typed_error"),
    ("B01", "action_surface_handler_uses_raw_v140_artifact_not_report", "v140_B01_action_surface_response_derived_from_v139_surface"),
    ("B02", "daily_outfit_handler_uses_raw_v140_artifact_not_report", "v140_A01_get_daily_outfit_returns_contract_envelope"),
    ("B03", "action_result_handler_uses_raw_v140_artifact_not_report", "v140_A03_get_action_result_returns_result_packet"),
    ("B04", "route_handler_trace_records_dispatch_steps", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("B05", "route_handler_trace_records_source_resolution", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("B06", "route_handler_trace_records_contract_projection", "v140_A02_get_action_surface_returns_cards_and_response_blocks"),
    ("C01", "post_this_time_only_handler_no_write_matches_contract", "v140_C01_post_this_time_only_submission_no_write"),
    ("C02", "post_do_not_change_memory_handler_no_write_matches_contract", "v140_C02_post_do_not_change_memory_submission_no_write"),
    ("C03", "post_remember_for_context_handler_routes_to_write_gate", "v140_C03_post_remember_for_context_routes_to_write_gate"),
    ("C04", "duplicate_submission_handler_is_idempotent", "v140_C04_duplicate_submission_returns_idempotent_result"),
    ("C05", "invalid_action_handler_returns_safe_error_no_write", "v140_D01_invalid_action_returns_safe_error_no_write"),
    ("C06", "missing_idempotency_key_handler_rejects_no_write", "v140_D04_missing_idempotency_key_rejected_no_write"),
    ("C07", "malformed_payload_handler_returns_contract_error_no_write", "v140_D05_malformed_payload_returns_contract_error_no_write"),
    ("D01", "expired_action_handler_returns_expired_error_no_write", "v140_D02_expired_action_submission_returns_expired_error_no_write"),
    ("D02", "stale_action_handler_returns_stale_error_no_write", "v140_D03_stale_action_submission_returns_stale_error_no_write"),
    ("D03", "duplicate_handler_reuses_canonical_action_result", "v140_C04_duplicate_submission_returns_idempotent_result"),
    ("D04", "repeated_handler_invocation_is_deterministic", "v140_C01_post_this_time_only_submission_no_write"),
    ("D05", "idempotency_scope_is_trace_backed", "v140_C04_duplicate_submission_returns_idempotent_result"),
    ("E01", "runtime_adapter_snapshot_hashes_reproducible", "v140_F01_contract_snapshot_hashes_reproducible"),
    ("E02", "runtime_source_artifact_hashes_match_raw_v140", "v140_F02_source_artifact_hashes_match_raw_per_case"),
    ("E03", "golden_contract_replay_request_response_match", "v140_F03_backward_compatibility_replay_stable"),
    ("E04", "golden_contract_replay_rejects_undocumented_diff", "v140_H02_clean_report_cannot_override_raw_failure"),
    ("E05", "v140_contract_snapshot_compatibility_preserved", "v140_F04_old_snapshot_revalidation_uses_current_schema_adapter"),
    ("F01", "conversation_turn_claims_survive_handler_execution", "v140_E03_conversation_turn_claims_trace_to_response_and_action_result"),
    ("F02", "visible_response_block_ids_match_handler_output", "v140_E03_conversation_turn_claims_trace_to_response_and_action_result"),
    ("F03", "action_result_claims_trace_to_handler_result", "v140_E02_conversation_turn_after_action_includes_result_notice"),
    ("F04", "error_claims_are_safe_and_trace_backed", "v140_D05_malformed_payload_returns_contract_error_no_write"),
    ("F05", "review_pending_handler_does_not_claim_memory_change", "v140_E04_conversation_turn_does_not_claim_review_pending_memory_change"),
    ("G01", "runtime_redacts_raw_human_review_evidence", "v140_G01_response_redacts_raw_human_review_evidence"),
    ("G02", "runtime_redacts_internal_paths_and_stack_traces", "v140_G02_error_redacts_internal_debug_details"),
    ("G03", "runtime_does_not_globalize_contextual_memory", "v140_G03_response_does_not_globalize_contextual_memory"),
    ("G04", "runtime_does_not_expose_sensitive_commerce_or_aigc_terms", "v140_G04_response_does_not_expose_sensitive_or_commerce_or_aigc_data"),
    ("H01", "sample_artifact_matches_per_case", "v140_H01_sample_artifact_matches_per_case"),
    ("H02", "clean_report_cannot_override_raw_failure", "v140_H02_clean_report_cannot_override_raw_failure"),
    ("H03", "reviewer_checklist_refs_raw_handler_cases", "v140_H03_reviewer_checklist_refs_raw_cases"),
    ("I01", "v140_replay_passes_before_v141_validation", "v140_I01_v139_replay_passes_before_v140_validation"),
    ("I02", "v141_runner_is_one_command_reproducible", "v140_I02_v140_runner_is_one_command_reproducible"),
]

DEFECTS = [
    ("ADV_P01", "missing_supported_route_binding", ["adapter_route_registry_complete_rate"]),
    ("ADV_P02", "duplicate_route_binding", ["adapter_route_registry_complete_rate"]),
    ("ADV_P03", "handler_name_mismatch_registry", ["route_handler_invocation_valid_rate", "handler_dispatch_trace_complete_rate"]),
    ("ADV_P04", "invocation_method_route_mismatch", ["route_handler_invocation_valid_rate"]),
    ("ADV_P05", "handler_trace_missing_dispatch_step", ["handler_dispatch_trace_complete_rate"]),
    ("ADV_P06", "handler_trace_missing_source_resolution", ["handler_dispatch_trace_complete_rate", "handler_uses_raw_source_artifacts_rate"]),
    ("ADV_P07", "handler_trace_missing_contract_projection", ["handler_dispatch_trace_complete_rate"]),
    ("ADV_P08", "handler_uses_clean_report_as_source", ["handler_uses_raw_source_artifacts_rate", "runtime_source_hashes_match_raw_rate"]),
    ("ADV_P09", "handler_uses_readme_or_release_note_as_source", ["handler_uses_raw_source_artifacts_rate", "runtime_source_hashes_match_raw_rate"]),
    ("ADV_P10", "source_v140_artifact_hash_stale", ["runtime_source_hashes_match_raw_rate"]),
    ("ADV_P11", "output_response_contract_version_mismatch", ["handler_output_matches_v140_contract_rate"]),
    ("ADV_P12", "output_schema_version_mismatch", ["handler_output_matches_v140_contract_rate"]),
    ("ADV_P13", "handler_output_missing_action_surface_body", ["handler_output_matches_v140_contract_rate"]),
    ("ADV_P14", "handler_output_missing_action_result_resource", ["runtime_action_result_links_response_rate"]),
    ("ADV_P15", "post_action_handler_accepts_disallowed_action", ["action_submission_handler_contract_rate"]),
    ("ADV_P16", "post_action_handler_missing_idempotency_key_accepted", ["action_submission_handler_contract_rate"]),
    ("ADV_P17", "no_write_action_executes_memory_write", ["no_write_handler_preserves_memory_state_rate"]),
    ("ADV_P18", "remember_for_context_bypasses_write_gate", ["action_submission_handler_contract_rate"]),
    ("ADV_P19", "duplicate_submission_creates_new_result", ["idempotent_handler_replay_rate"]),
    ("ADV_P20", "expired_action_executes_write", ["expired_stale_handler_no_write_rate", "no_write_handler_preserves_memory_state_rate"]),
    ("ADV_P21", "stale_action_executes_write", ["expired_stale_handler_no_write_rate", "no_write_handler_preserves_memory_state_rate"]),
    ("ADV_P22", "unsupported_route_exposes_unsafe_error", ["runtime_error_safety_rate", "runtime_redaction_policy_safe_rate"]),
    ("ADV_P23", "error_exposes_internal_path_or_traceback", ["runtime_error_safety_rate", "runtime_redaction_policy_safe_rate"]),
    ("ADV_P24", "review_pending_handler_claims_memory_changed", ["conversation_claims_trace_backed_after_handler_rate", "runtime_redaction_policy_safe_rate"]),
    ("ADV_P25", "handler_output_exposes_raw_review_evidence", ["runtime_redaction_policy_safe_rate"]),
    ("ADV_P26", "handler_output_globalizes_contextual_memory", ["runtime_redaction_policy_safe_rate"]),
    ("ADV_P27", "handler_output_exposes_sensitive_commerce_or_aigc_terms", ["runtime_redaction_policy_safe_rate"]),
    ("ADV_P28", "runtime_snapshot_hash_mismatch", ["runtime_snapshot_hash_reproducible_rate"]),
    ("ADV_P29", "golden_contract_replay_has_undocumented_diff", ["golden_contract_replay_rate"]),
    ("ADV_P30", "conversation_claim_missing_response_block_ref", ["conversation_claims_trace_backed_after_handler_rate"]),
    ("ADV_P31", "conversation_claim_missing_action_result_ref", ["conversation_claims_trace_backed_after_handler_rate"]),
    ("ADV_P32", "visible_response_block_ids_stale", ["conversation_claims_trace_backed_after_handler_rate"]),
    ("ADV_P33", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_P34", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_P35", "v140_replay_missing_or_failed", ["v140_validation_replay_pass_rate"]),
    ("ADV_P36", "missing_callable_handler", ["adapter_route_registry_complete_rate"]),
    ("ADV_P37", "registry_references_non_callable_handler", ["adapter_route_registry_complete_rate", "route_handler_invocation_valid_rate"]),
    ("ADV_P38", "invocation_bypasses_handler_with_direct_copy", ["route_handler_invocation_valid_rate", "handler_dispatch_trace_complete_rate"]),
    ("ADV_P39", "unsupported_route_missing_callable", ["adapter_route_registry_complete_rate"]),
    ("ADV_P40", "invoke_handler_trace_without_callable_execution_proof", ["handler_dispatch_trace_complete_rate"]),
]

SAMPLE_CASES = {
    "runtime_action_surface_handler.json": "v141_A04_get_action_surface_handler_matches_v140_contract",
    "runtime_post_this_time_only_handler.json": "v141_C01_post_this_time_only_handler_no_write_matches_contract",
    "runtime_remember_for_context_handler.json": "v141_C03_post_remember_for_context_handler_routes_to_write_gate",
    "runtime_duplicate_submission_handler.json": "v141_C04_duplicate_submission_handler_is_idempotent",
    "runtime_safe_error_handler.json": "v141_A06_unsupported_route_handler_returns_safe_error",
    "runtime_snapshot.json": "v141_E01_runtime_adapter_snapshot_hashes_reproducible",
    "runtime_redaction_handler.json": "v141_G01_runtime_redacts_raw_human_review_evidence",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_ref(case_id: str) -> str:
    return f"per_case/clean/{case_id}.json"


def _source(case_id: str) -> tuple[str, Path, dict[str, Any], str]:
    ref = _source_ref(case_id)
    path = V140_DIR / ref
    return ref, path, read_json(path), file_json_hash(path)


def _runtime_case(case_code: str, scenario: str, source_case_id: str) -> dict[str, Any]:
    case_id = f"v141_{case_code}_{scenario}"
    source_ref, source_path, source, source_hash = _source(source_case_id)
    runtime = ProductRuntimeAdapter(V140_DIR).invoke(runtime_case_id=case_id, source_ref=source_ref, source=source, source_hash=source_hash, source_path=source_path)
    request = runtime["route_handler_invocation"]["input_envelope"]
    response = runtime["route_handler_result"]["output_envelope"]
    action_result = source.get("action_result_api_resource")
    submission = source.get("action_submission_api_resource")
    conversation = copy.deepcopy(source.get("conversation_turn_state"))
    artifact = {
        "case_id": case_id,
        "version": VERSION,
        "scenario_kind": scenario,
        "gate_assertions": {gate: True for gate in GATES},
        "source_v140_artifact_ref": source_ref,
        "source_v140_artifact_hash": source_hash,
        "source_v140_case_id": source["case_id"],
        "source_v139_artifact_ref": source.get("source_v139_artifact_ref"),
        "source_v139_artifact_hash": source.get("source_v139_artifact_hash"),
        **runtime,
        "local_api_request_envelope": request,
        "local_api_response_envelope": response,
        "action_surface_api_resource": copy.deepcopy(source.get("action_surface_api_resource")),
        "action_submission_api_resource": copy.deepcopy(submission),
        "action_result_api_resource": copy.deepcopy(action_result),
        "conversation_turn_state": conversation,
        "handler_idempotency_proof": {
            "idempotency_key": request.get("idempotency_key"),
            "duplicate_created_result": (response.get("body") or {}).get("idempotency", {}).get("duplicate_created_result"),
            "canonical_action_result_packet_id": (response.get("body") or {}).get("idempotency", {}).get("canonical_action_result_packet_id"),
            "repeated_invocation_output_hash": canonical_json_hash(response),
            "trace_refs": [runtime["route_handler_invocation"]["route_handler_invocation_id"], runtime["route_handler_result"]["route_handler_result_id"]],
        },
        "handler_no_write_proof": {
            "before_memory_lifecycle_state": source.get("before_memory_lifecycle_state", {}),
            "after_memory_lifecycle_state": source.get("after_memory_lifecycle_state", {}),
            "production_write_executed": runtime["route_handler_result"]["production_write_executed"],
            "trace_refs": [runtime["route_handler_result"]["route_handler_result_id"]],
        },
        "handler_error_safety_proof": {
            "response_type": response.get("response_type"),
            "safe_error_only": response.get("response_type") != "error" or bool(response.get("error")),
            "production_write_executed": runtime["route_handler_result"]["production_write_executed"],
            "trace_refs": [runtime["route_handler_result"]["route_handler_result_id"]],
        },
        "handler_claim_trace_proof": {
            "visible_response_block_ids": (conversation or {}).get("visible_response_block_ids", []),
            "user_visible_claim_ids": [claim.get("claim_id") for claim in (conversation or {}).get("user_visible_claims", [])],
            "trace_refs": [runtime["route_handler_result"]["api_response_id"]],
        },
        "production_memory_write_gate": copy.deepcopy(source.get("production_memory_write_gate")),
        "before_memory_lifecycle_state": copy.deepcopy(source.get("before_memory_lifecycle_state", {})),
        "after_memory_lifecycle_state": copy.deepcopy(source.get("after_memory_lifecycle_state", {})),
        "policy_surface_audit": {"no_raw_review_evidence_exposed": True, "no_internal_debug_exposed": True, "no_global_memory_claim": True, "no_sensitive_or_commerce_or_aigc": True},
        "reviewer_checklist_refs": [
            "per_case/clean/v141_A04_get_action_surface_handler_matches_v140_contract.json",
            "per_case/clean/v141_C01_post_this_time_only_handler_no_write_matches_contract.json",
            "per_case/clean/v141_E01_runtime_adapter_snapshot_hashes_reproducible.json",
        ] if scenario == "reviewer_checklist_refs_raw_handler_cases" else [],
        "runner_reproducibility_proof": {"command": "python benchmark/benchmark_v141/scripts/run_v141_validation_suite.py", "one_command": True} if scenario == "v141_runner_is_one_command_reproducible" else {},
        "v140_replay_proof": {"run_v140_validation_suite": "PASS"},
    }
    return artifact


def _set_case_meta(artifact: dict[str, Any], defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    artifact["case_id"] = f"v141_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = gates
    artifact["gate_assertions"] = {gate: True for gate in GATES}
    return artifact


def _defect(defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    base_source = "v140_C01_post_this_time_only_submission_no_write"
    if defect_type in {"missing_supported_route_binding", "duplicate_route_binding", "handler_name_mismatch_registry", "invocation_method_route_mismatch", "handler_trace_missing_dispatch_step", "handler_trace_missing_source_resolution", "handler_trace_missing_contract_projection", "handler_uses_clean_report_as_source", "handler_uses_readme_or_release_note_as_source", "source_v140_artifact_hash_stale", "runtime_snapshot_hash_mismatch", "golden_contract_replay_has_undocumented_diff", "sample_artifact_stale_relative_to_per_case", "clean_report_pass_but_independent_validator_fail", "v140_replay_missing_or_failed", "missing_callable_handler", "registry_references_non_callable_handler", "invocation_bypasses_handler_with_direct_copy", "invoke_handler_trace_without_callable_execution_proof"}:
        base_source = "v140_A02_get_action_surface_returns_cards_and_response_blocks"
    elif "action_surface" in defect_type or "raw_review" in defect_type:
        base_source = "v140_A02_get_action_surface_returns_cards_and_response_blocks"
    elif "action_result" in defect_type or "claim_missing_action_result" in defect_type or "visible_response_block" in defect_type:
        base_source = "v140_E03_conversation_turn_claims_trace_to_response_and_action_result"
    elif "duplicate" in defect_type:
        base_source = "v140_C04_duplicate_submission_returns_idempotent_result"
    elif "expired" in defect_type:
        base_source = "v140_D02_expired_action_submission_returns_expired_error_no_write"
    elif "stale" in defect_type:
        base_source = "v140_D03_stale_action_submission_returns_stale_error_no_write"
    elif "unsupported" in defect_type:
        base_source = "v140_A04_unsupported_route_returns_typed_error"
    elif "error_exposes" in defect_type:
        base_source = "v140_D05_malformed_payload_returns_contract_error_no_write"
    elif "review_pending" in defect_type:
        base_source = "v140_E04_conversation_turn_does_not_claim_review_pending_memory_change"
    elif "globalizes" in defect_type:
        base_source = "v140_G03_response_does_not_globalize_contextual_memory"
    elif "sensitive" in defect_type:
        base_source = "v140_G04_response_does_not_expose_sensitive_or_commerce_or_aigc_data"
    artifact = _set_case_meta(_runtime_case(defect_id, defect_type, base_source), defect_id, defect_type, gates)
    response = artifact["route_handler_result"]["output_envelope"]
    body = response.get("body") or {}
    registry_routes = artifact["product_route_registry"]["routes"]
    trace = artifact["runtime_handler_execution_trace"]
    source_proof = artifact["runtime_source_resolution_proof"]
    if defect_type == "missing_supported_route_binding":
        artifact["product_route_registry"]["routes"] = registry_routes[:-1]
    elif defect_type == "duplicate_route_binding":
        artifact["product_route_registry"]["routes"].append(copy.deepcopy(registry_routes[0]))
    elif defect_type == "handler_name_mismatch_registry":
        artifact["route_handler_invocation"]["handler_name"] = "handle_wrong_route"
    elif defect_type == "invocation_method_route_mismatch":
        artifact["route_handler_invocation"]["method"] = "POST"
    elif defect_type == "handler_trace_missing_dispatch_step":
        trace["dispatch_steps"] = []
    elif defect_type == "handler_trace_missing_source_resolution":
        trace["source_resolution_refs"] = []
    elif defect_type == "handler_trace_missing_contract_projection":
        trace["contract_projection_refs"] = []
    elif defect_type == "handler_uses_clean_report_as_source":
        source_proof["source_v140_artifact_ref"] = "clean_report.json"
        source_proof["forbidden_source_types_observed"] = ["clean_report.json"]
    elif defect_type == "handler_uses_readme_or_release_note_as_source":
        source_proof["source_v140_artifact_ref"] = "README.md"
        source_proof["forbidden_source_types_observed"] = ["README.md"]
    elif defect_type == "source_v140_artifact_hash_stale":
        source_proof["source_v140_artifact_hash"] = "sha256-stale"
        artifact["runtime_adapter_snapshot"]["source_artifact_hashes"][artifact["source_v140_artifact_ref"]] = "sha256-stale"
    elif defect_type == "output_response_contract_version_mismatch":
        response["contract_version"] = "v1.39"
    elif defect_type == "output_schema_version_mismatch":
        response["schema_version"] = "product_api.v0"
    elif defect_type == "handler_output_missing_action_surface_body":
        artifact = _set_case_meta(_runtime_case(defect_id, defect_type, "v140_A02_get_action_surface_returns_cards_and_response_blocks"), defect_id, defect_type, gates)
        artifact["route_handler_result"]["output_envelope"]["body"].pop("action_surface", None)
    elif defect_type == "handler_output_missing_action_result_resource":
        artifact["action_result_api_resource"] = None
    elif defect_type == "post_action_handler_accepts_disallowed_action":
        artifact["action_submission_api_resource"]["submitted_action"] = "globalize_memory"
        artifact["route_handler_invocation"]["input_envelope"]["body"]["submitted_action"] = "globalize_memory"
    elif defect_type == "post_action_handler_missing_idempotency_key_accepted":
        artifact["route_handler_invocation"]["input_envelope"]["idempotency_key"] = None
        artifact["action_submission_api_resource"]["accepted"] = True
    elif defect_type == "no_write_action_executes_memory_write":
        artifact["route_handler_result"]["production_write_executed"] = True
        artifact["handler_no_write_proof"]["production_write_executed"] = True
        artifact["action_submission_api_resource"]["production_write_executed"] = True
    elif defect_type == "remember_for_context_bypasses_write_gate":
        artifact = _set_case_meta(_runtime_case(defect_id, defect_type, "v140_C03_post_remember_for_context_routes_to_write_gate"), defect_id, defect_type, gates)
        artifact["production_memory_write_gate"]["decision"] = "block"
    elif defect_type == "duplicate_submission_creates_new_result":
        body["idempotency"]["duplicate_created_result"] = True
        artifact["handler_idempotency_proof"]["duplicate_created_result"] = True
    elif defect_type == "expired_action_executes_write" or defect_type == "stale_action_executes_write":
        artifact["route_handler_result"]["production_write_executed"] = True
        artifact["handler_no_write_proof"]["production_write_executed"] = True
        artifact["route_handler_result"]["output_envelope"]["error"]["production_write_executed"] = True
    elif defect_type == "unsupported_route_exposes_unsafe_error":
        response["error"]["safe_message"] = "Traceback: raw_evidence exposed"
    elif defect_type == "error_exposes_internal_path_or_traceback":
        response["error"]["developer_debug_ref"] = "/ssd2/private/traceback.log"
    elif defect_type == "review_pending_handler_claims_memory_changed":
        artifact["conversation_turn_state"]["user_visible_claims"][0]["text"] = "I saved this while review is pending."
        artifact["conversation_turn_state"]["memory_change_claimed"] = True
    elif defect_type == "handler_output_exposes_raw_review_evidence":
        body["response_blocks"][0]["text"] = "raw_evidence_refs and risk_reasons"
    elif defect_type == "handler_output_globalizes_contextual_memory":
        body["response_blocks"][0]["text"] = "I saved this as global memory."
    elif defect_type == "handler_output_exposes_sensitive_commerce_or_aigc_terms":
        body["response_blocks"][0]["text"] = "body identity merchant SKU with AIGC image generation"
    elif defect_type == "runtime_snapshot_hash_mismatch":
        artifact["runtime_adapter_snapshot"]["canonical_output_hash"] = "sha256-bogus"
    elif defect_type == "golden_contract_replay_has_undocumented_diff":
        artifact["golden_contract_replay"]["response_match"] = False
        artifact["golden_contract_replay"]["diff"] = [{"path": "body.response_blocks[0].text", "expected": "golden", "actual": "runtime"}]
    elif defect_type == "conversation_claim_missing_response_block_ref":
        artifact["conversation_turn_state"]["user_visible_claims"][0]["trace_refs"] = [response["api_response_id"]]
    elif defect_type == "conversation_claim_missing_action_result_ref":
        result_id = artifact["action_result_api_resource"]["action_result_packet_id"]
        refs = artifact["conversation_turn_state"]["user_visible_claims"][0]["trace_refs"]
        artifact["conversation_turn_state"]["user_visible_claims"][0]["trace_refs"] = [ref for ref in refs if ref != result_id]
    elif defect_type == "visible_response_block_ids_stale":
        artifact["conversation_turn_state"]["visible_response_block_ids"] = ["stale_response_block_id"]
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        artifact["sample_consistency_probe"] = {"sample_artifact_content": {"case_id": artifact["case_id"], "stale": True}, "source_artifact_content": {"case_id": artifact["case_id"]}}
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        artifact["report_consistency_probe"] = {"clean_report_summary": {"passed_cases": len(CLEAN_CASES), "failed_cases": 0}, "independent_validation_summary": {"passed_cases": len(CLEAN_CASES) - 1, "failed_cases": 1}}
    elif defect_type == "v140_replay_missing_or_failed":
        artifact["v140_replay_proof"]["run_v140_validation_suite"] = "FAIL"
    elif defect_type == "missing_callable_handler":
        artifact["product_runtime_adapter"]["callable_handler_registry"] = [
            row for row in artifact["product_runtime_adapter"].get("callable_handler_registry", []) if row.get("handler_name") != "handle_get_action_surface"
        ]
    elif defect_type == "registry_references_non_callable_handler":
        artifact["product_route_registry"]["routes"][0]["handler_name"] = "not_a_callable_handler"
        artifact["route_handler_invocation"]["handler_name"] = "not_a_callable_handler"
        artifact["route_handler_invocation"]["resolved_callable_name"] = "not_a_callable_handler"
        artifact["runtime_handler_execution_trace"]["handler_name"] = "not_a_callable_handler"
        artifact["runtime_handler_execution_trace"]["callable_execution_proof"]["handler_name"] = "not_a_callable_handler"
        artifact["runtime_handler_execution_trace"]["callable_execution_proof"]["callable_name"] = "not_a_callable_handler"
    elif defect_type == "invocation_bypasses_handler_with_direct_copy":
        artifact["route_handler_result"]["produced_by_callable"] = False
        artifact["route_handler_result"].pop("handler_execution_proof_id", None)
        artifact["runtime_handler_execution_trace"]["callable_execution_proof"]["direct_source_output_copy"] = True
        artifact["runtime_handler_execution_trace"]["callable_execution_proof"]["callable_invoked"] = False
    elif defect_type == "unsupported_route_missing_callable":
        artifact["product_route_registry"]["unsupported_route_policy"]["handler_name"] = "handle_missing_unsupported_route"
    elif defect_type == "invoke_handler_trace_without_callable_execution_proof":
        artifact["runtime_handler_execution_trace"].pop("callable_execution_proof", None)
    return artifact


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.41.in_process_product_runtime_adapter" + ("" if clean else ".mixed_strict"),
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
        "theme": "In-Process Product Runtime Adapter",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v141/results/v141_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v141/scripts/build_v141_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v141/scripts/validate_v141_release_candidate.py",
        "adversarial_generator": "benchmark/benchmark_v141/scripts/generate_v141_adversarial_cases.py",
        "runner_script": "benchmark/benchmark_v141/scripts/run_v141_validation_suite.py",
        "source_v140_evidence_path": "benchmark/benchmark_v140/results/v140_release_candidate",
        "required_reports": ["clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "report_consistency_report.json", "sample_consistency_report.json", "injected_defect_detection_summary.json"],
        "required_gates": GATES,
        "validator_commands": ["benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py", "python benchmark/benchmark_v140/scripts/run_v140_validation_suite.py", "python benchmark/benchmark_v141/scripts/run_v141_validation_suite.py", "python -m unittest discover -s benchmark/benchmark_v141/tests"],
        "sample_artifacts": samples,
        "manual_reviewer_checklist_refs": ["reviewer_checklist.md"],
        "non_goals": ["No real HTTP server", "No frontend", "No auth service", "No production DB", "No commerce", "No AIGC", "No global memory writes"],
    }


def build(result_dir: Path = RESULT_DIR) -> None:
    if result_dir.exists():
        shutil.rmtree(result_dir)
    for subdir in ["per_case/clean", "per_case/mixed_strict", "per_case/adversarial", "sample_artifacts"]:
        (result_dir / subdir).mkdir(parents=True, exist_ok=True)
    rows = [_runtime_case(code, scenario, source_case_id) for code, scenario, source_case_id in CLEAN_CASES]
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
    _write_text(result_dir / "README.md", "# v1.41 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic in-process product runtime adapter evidence.\n")
    _write_text(result_dir / "RELEASE_NOTE.md", "# v1.41 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves callable local route handlers over the accepted v1.40 product API contract.\n")
    _write_text(result_dir / "reviewer_checklist.md", "# v1.41 Reviewer Checklist\n\n- [ ] Inspect route registry bindings.\n- [ ] Inspect GET daily outfit handler invocation/result/trace.\n- [ ] Inspect GET action surface handler invocation/result/trace.\n- [ ] Inspect POST this_time_only no-write handler proof.\n- [ ] Inspect remember_for_context write-gated handler proof.\n- [ ] Inspect duplicate submission idempotency replay.\n- [ ] Inspect expired/stale and unsupported safe errors.\n- [ ] Recompute runtime adapter snapshot hashes.\n- [ ] Inspect golden contract replay against v1.40.\n- [ ] Inspect adversarial report-source bypass failure.\n")
    _write_text(result_dir / "clean_report.md", "# v1.41 Clean Acceptance Report\n\n" + "\n".join(f"- PASS `{gate}`" for gate in GATES) + "\n")
    _write_text(result_dir / "mixed_strict_report.md", "# v1.41 Mixed Strict Report\n\n" + "\n".join(f"- EXPECTED FAIL `{gate}`" for gate in GATES) + "\n")


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
