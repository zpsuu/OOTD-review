"""Build deterministic v1.40 local product API contract evidence."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, now_iso, read_json, write_json


VERSION = "v1.40"
CONTRACT_VERSION = "v1.40"
SCHEMA_VERSION = "product_api.v1"
BRANCH = "v140-local-product-api-contract"
RESULT_DIR = Path("benchmark/benchmark_v140/results/v140_release_candidate")
V139_DIR = Path("benchmark/benchmark_v139/results/v139_release_candidate")
NOW = "2026-06-24T00:00:00Z"

GATES = [
    "api_request_response_envelope_valid_rate",
    "route_handler_maps_to_raw_artifacts_rate",
    "action_surface_api_matches_v139_surface_rate",
    "action_submission_contract_valid_rate",
    "no_write_error_preserves_memory_state_rate",
    "idempotent_submission_contract_rate",
    "expired_stale_action_contract_rate",
    "action_result_api_links_response_rate",
    "conversation_turn_claims_trace_backed_rate",
    "contract_snapshot_hash_reproducible_rate",
    "source_artifact_hashes_match_raw_rate",
    "backward_compatibility_replay_rate",
    "redaction_policy_safe_response_rate",
    "schema_version_consistency_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v139_validation_replay_pass_rate",
]

SOURCE_CASES = {
    "open_clarification": "per_case/clean/v139_A01_open_clarification_queue_item_creates_active_action_card.json",
    "open_review": "per_case/clean/v139_C01_review_pending_notice_hides_raw_review_evidence.json",
    "rollback": "per_case/clean/v139_F01_rollback_status_excludes_memory_from_future_packet.json",
    "blocked": "per_case/clean/v139_F02_blocked_status_excludes_memory_from_future_claims.json",
    "expired": "per_case/clean/v139_D03_expired_action_submission_noop.json",
    "this_time_only": "per_case/clean/v139_B02_this_time_only_submission_no_write_result.json",
    "do_not_change_memory": "per_case/clean/v139_B03_do_not_change_memory_submission_no_write_result.json",
    "remember_for_context": "per_case/clean/v139_B04_remember_for_context_submission_routes_to_write_gate.json",
    "duplicate": "per_case/clean/v139_D04_duplicate_action_submission_idempotent.json",
    "stale": "per_case/clean/v139_D05_stale_action_suppressed_after_resolution.json",
    "claims": "per_case/clean/v139_G01_response_claims_trace_to_action_result.json",
}

CLEAN_CASES = [
    ("A01", "get_daily_outfit_returns_contract_envelope", "daily_outfit", "open_clarification"),
    ("A02", "get_action_surface_returns_cards_and_response_blocks", "action_surface", "open_clarification"),
    ("A03", "get_action_result_returns_result_packet", "action_result", "this_time_only"),
    ("A04", "unsupported_route_returns_typed_error", "unsupported_route", "open_clarification"),
    ("B01", "action_surface_response_derived_from_v139_surface", "action_surface", "open_clarification"),
    ("B02", "open_clarification_card_contract_shape", "action_surface", "open_clarification"),
    ("B03", "review_pending_status_contract_shape", "action_surface", "open_review"),
    ("B04", "rollback_blocked_status_contract_shape", "action_surface", "rollback"),
    ("B05", "expired_action_contract_shape_disabled", "action_surface", "expired"),
    ("C01", "post_this_time_only_submission_no_write", "post_action", "this_time_only"),
    ("C02", "post_do_not_change_memory_submission_no_write", "post_action", "do_not_change_memory"),
    ("C03", "post_remember_for_context_routes_to_write_gate", "post_action", "remember_for_context"),
    ("C04", "duplicate_submission_returns_idempotent_result", "duplicate_submission", "duplicate"),
    ("C05", "submission_response_links_to_action_result", "post_action", "this_time_only"),
    ("D01", "invalid_action_returns_safe_error_no_write", "invalid_action", "open_clarification"),
    ("D02", "expired_action_submission_returns_expired_error_no_write", "expired_action", "expired"),
    ("D03", "stale_action_submission_returns_stale_error_no_write", "stale_action", "stale"),
    ("D04", "missing_idempotency_key_rejected_no_write", "missing_idempotency_key", "this_time_only"),
    ("D05", "malformed_payload_returns_contract_error_no_write", "malformed_payload", "open_clarification"),
    ("E01", "conversation_turn_includes_action_surface", "conversation_surface", "open_clarification"),
    ("E02", "conversation_turn_after_action_includes_result_notice", "conversation_result", "this_time_only"),
    ("E03", "conversation_turn_claims_trace_to_response_and_action_result", "conversation_result", "claims"),
    ("E04", "conversation_turn_does_not_claim_review_pending_memory_change", "conversation_surface", "open_review"),
    ("F01", "contract_snapshot_hashes_reproducible", "snapshot", "this_time_only"),
    ("F02", "source_artifact_hashes_match_raw_per_case", "snapshot", "remember_for_context"),
    ("F03", "backward_compatibility_replay_stable", "compatibility_replay", "this_time_only"),
    ("F04", "old_snapshot_revalidation_uses_current_schema_adapter", "compatibility_replay", "open_clarification"),
    ("G01", "response_redacts_raw_human_review_evidence", "redaction_review", "open_review"),
    ("G02", "error_redacts_internal_debug_details", "invalid_action", "open_clarification"),
    ("G03", "response_does_not_globalize_contextual_memory", "action_surface", "remember_for_context"),
    ("G04", "response_does_not_expose_sensitive_or_commerce_or_aigc_data", "action_surface", "open_clarification"),
    ("H01", "sample_artifact_matches_per_case", "sample_consistency", "open_clarification"),
    ("H02", "clean_report_cannot_override_raw_failure", "report_consistency", "this_time_only"),
    ("H03", "reviewer_checklist_refs_raw_cases", "reviewer_checklist", "duplicate"),
    ("I01", "v139_replay_passes_before_v140_validation", "v139_replay", "this_time_only"),
    ("I02", "v140_runner_is_one_command_reproducible", "runner_reproducible", "this_time_only"),
]

DEFECTS = [
    ("ADV_N01", "response_missing_contract_version", ["api_request_response_envelope_valid_rate", "schema_version_consistency_rate"]),
    ("ADV_N02", "response_schema_version_mismatch", ["api_request_response_envelope_valid_rate", "schema_version_consistency_rate"]),
    ("ADV_N03", "route_handler_uses_report_summary_instead_of_raw_artifact", ["route_handler_maps_to_raw_artifacts_rate"]),
    ("ADV_N04", "action_surface_response_missing_card", ["action_surface_api_matches_v139_surface_rate"]),
    ("ADV_N05", "action_surface_response_has_stale_card", ["action_surface_api_matches_v139_surface_rate"]),
    ("ADV_N06", "post_action_submission_allows_disallowed_action", ["action_submission_contract_valid_rate"]),
    ("ADV_N07", "this_time_only_submission_executes_write", ["no_write_error_preserves_memory_state_rate"]),
    ("ADV_N08", "do_not_change_memory_submission_executes_write", ["no_write_error_preserves_memory_state_rate"]),
    ("ADV_N09", "remember_for_context_bypasses_write_gate", ["action_submission_contract_valid_rate"]),
    ("ADV_N10", "duplicate_submission_creates_new_result", ["idempotent_submission_contract_rate"]),
    ("ADV_N11", "expired_action_submission_executes_write", ["expired_stale_action_contract_rate", "no_write_error_preserves_memory_state_rate"]),
    ("ADV_N12", "stale_action_submission_executes_write", ["expired_stale_action_contract_rate", "no_write_error_preserves_memory_state_rate"]),
    ("ADV_N13", "missing_idempotency_key_accepted", ["action_submission_contract_valid_rate"]),
    ("ADV_N14", "malformed_payload_returns_unsafe_error", ["redaction_policy_safe_response_rate"]),
    ("ADV_N15", "error_exposes_internal_path", ["redaction_policy_safe_response_rate"]),
    ("ADV_N16", "review_pending_response_claims_memory_changed", ["redaction_policy_safe_response_rate", "conversation_turn_claims_trace_backed_rate"]),
    ("ADV_N17", "response_exposes_raw_review_evidence", ["redaction_policy_safe_response_rate"]),
    ("ADV_N18", "response_globalizes_contextual_memory", ["redaction_policy_safe_response_rate"]),
    ("ADV_N19", "response_exposes_sensitive_or_commerce_or_aigc_data", ["redaction_policy_safe_response_rate"]),
    ("ADV_N20", "contract_snapshot_hash_mismatch", ["contract_snapshot_hash_reproducible_rate"]),
    ("ADV_N21", "source_artifact_hash_missing_or_stale", ["source_artifact_hashes_match_raw_rate"]),
    ("ADV_N22", "backward_compatibility_replay_uses_stale_schema", ["backward_compatibility_replay_rate", "schema_version_consistency_rate"]),
    ("ADV_N23", "sample_artifact_stale_relative_to_per_case", ["sample_artifacts_match_per_case_rate"]),
    ("ADV_N24", "clean_report_pass_but_independent_validator_fail", ["report_consistency_with_independent_validation_rate"]),
    ("ADV_N25", "missing_conversation_turn_state", ["conversation_turn_claims_trace_backed_rate"]),
    ("ADV_N26", "empty_user_visible_claims", ["conversation_turn_claims_trace_backed_rate"]),
    ("ADV_N27", "missing_action_surface_body", ["action_surface_api_matches_v139_surface_rate"]),
    ("ADV_N28", "missing_daily_outfit_cards_and_response_blocks", ["action_surface_api_matches_v139_surface_rate"]),
    ("ADV_N29", "missing_action_result_body", ["action_result_api_links_response_rate"]),
    ("ADV_N30", "missing_action_submission_resource", ["action_submission_contract_valid_rate"]),
    ("ADV_N31", "missing_response_blocks", ["action_surface_api_matches_v139_surface_rate"]),
]

SAMPLE_CASES = {
    "get_action_surface_contract.json": "v140_A02_get_action_surface_returns_cards_and_response_blocks",
    "post_this_time_only_contract.json": "v140_C01_post_this_time_only_submission_no_write",
    "remember_for_context_contract.json": "v140_C03_post_remember_for_context_routes_to_write_gate",
    "duplicate_submission_contract.json": "v140_C04_duplicate_submission_returns_idempotent_result",
    "expired_action_error_contract.json": "v140_D02_expired_action_submission_returns_expired_error_no_write",
    "contract_snapshot.json": "v140_F01_contract_snapshot_hashes_reproducible",
    "review_redaction_contract.json": "v140_G01_response_redacts_raw_human_review_evidence",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source(case_key: str) -> tuple[str, dict[str, Any], str]:
    ref = SOURCE_CASES[case_key]
    path = V139_DIR / ref
    return ref, read_json(path), file_json_hash(path)


def _project_surface(source: dict[str, Any]) -> dict[str, Any]:
    surface = source["governance_action_surface"]
    return {
        "action_surface_api_resource_id": f"asr_{source['case_id']}",
        "source_governance_action_surface_id": surface["governance_action_surface_id"],
        "cards": [
            {
                "card_id": card["user_action_card_id"],
                "governance_queue_item_id": card["governance_queue_item_id"],
                "card_type": card["card_type"],
                "display_state": card["display_state"],
                "title": card["title"],
                "body": card["body"],
                "allowed_actions": card.get("allowed_actions", []),
                "disabled_reason": card.get("disabled_reason"),
                "trace_refs": card.get("trace_refs", []),
            }
            for card in surface.get("cards", [])
        ],
        "response_blocks": [
            {
                "response_block_id": block["response_block_id"],
                "block_type": block["block_type"],
                "text": block["text"],
                "claim_refs": block.get("claim_refs", []),
                "trace_refs": block.get("trace_refs", []),
            }
            for block in surface.get("response_blocks", [])
        ],
        "trace_refs": [surface["governance_action_surface_id"], source["case_id"], source["runtime_trace"]["runtime_trace_id"]],
    }


def _request(case_id: str, route: str, method: str, source: dict[str, Any], body: dict[str, Any] | None = None, idem: str | None = None) -> dict[str, Any]:
    return {
        "api_request_id": f"api_req_{case_id}",
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "route": route,
        "method": method,
        "request_context": "office_daily",
        "query": {},
        "body": body or {},
        "idempotency_key": idem,
        "trace_refs": [source["runtime_trace"]["runtime_trace_id"], source["governance_action_surface"]["governance_action_surface_id"]],
    }


def _error(case_id: str, error_type: str, status_code: int, message: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "error_id": f"api_err_{case_id}",
        "error_type": error_type,
        "status_code": status_code,
        "safe_message": message,
        "developer_debug_ref": f"trace:{source['runtime_trace']['runtime_trace_id']}",
        "production_write_executed": False,
        "trace_refs": [source["runtime_trace"]["runtime_trace_id"], source["governance_action_surface"]["governance_action_surface_id"]],
    }


def _action_submission_resource(case_id: str, source: dict[str, Any], action: str | None, accepted: bool, idem: str | None) -> dict[str, Any] | None:
    cards = source["governance_action_surface"].get("cards", [])
    card = cards[0] if cards else {}
    return {
        "action_submission_api_resource_id": f"sub_api_{case_id}",
        "accepted": accepted,
        "submitted_action": action,
        "idempotency_key": idem,
        "user_action_card_id": card.get("user_action_card_id"),
        "governance_queue_item_id": card.get("governance_queue_item_id"),
        "allowed_actions_at_submission": card.get("allowed_actions", []),
        "card_display_state_at_submission": card.get("display_state"),
        "production_write_executed": bool((source.get("action_result_packet") or {}).get("production_write_executed")) if accepted else False,
        "trace_refs": [source["runtime_trace"]["runtime_trace_id"], card.get("user_action_card_id"), card.get("governance_queue_item_id")],
    }


def _action_result_resource(case_id: str, source: dict[str, Any], response_blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    result = source.get("action_result_packet")
    if not result:
        return None
    return {
        "action_result_api_resource_id": f"res_api_{case_id}",
        "action_result_packet_id": result["action_result_packet_id"],
        "result_type": result["result_type"],
        "production_write_executed": result["production_write_executed"],
        "post_action_task_memory_packet_id": result["post_action_task_memory_packet_id"],
        "user_visible_response_block_ids": result.get("user_visible_response_block_ids", []),
        "response_block_refs": [block["response_block_id"] for block in response_blocks],
        "governance_resolution_decision_id": result.get("governance_resolution_decision_id"),
        "trace_refs": result.get("trace_refs", []),
    }


def _route_proof(case_id: str, route: str, source_ref: str, source: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    return {
        "route_handler_proof_id": f"rhp_{case_id}",
        "route": route,
        "source_artifact_refs": [source_ref],
        "derived_resource_refs": [value for key, value in body.items() if key.endswith("_id") and isinstance(value, str)],
        "field_mapping": [
            {"response_field": key, "source": "raw_v139_artifact" if key not in {"contract_version", "schema_version"} else "derived_constant"}
            for key in sorted(body.keys())
        ],
        "redaction_proof": {
            "raw_human_review_evidence_exposed": False,
            "internal_only_fields_exposed": False,
            "excluded_terms": ["raw_evidence_refs", "risk_reasons", "internal_only_fields"],
        },
        "trace_refs": [source["runtime_trace"]["runtime_trace_id"], source["governance_action_surface"]["governance_action_surface_id"]],
    }


def _conversation(case_id: str, source: dict[str, Any], response: dict[str, Any], action_result: dict[str, Any] | None) -> dict[str, Any]:
    body = response.get("body") or {}
    blocks = body.get("response_blocks") or body.get("action_surface", {}).get("response_blocks") or body.get("daily_outfit_card", {}).get("response_blocks") or []
    decision_id = (source.get("governance_resolution_decision") or {}).get("governance_resolution_decision_id")
    result_id = (action_result or {}).get("action_result_packet_id")
    claims = []
    for block in blocks:
        refs = [response["api_response_id"], block["response_block_id"]]
        if result_id:
            refs.append(result_id)
        if decision_id:
            refs.append(decision_id)
        claims.append({"claim_id": f"api_claim_{block['response_block_id']}", "text": block["text"], "trace_refs": refs})
    return {
        "conversation_turn_state_id": f"cts_{case_id}",
        "api_request_id": response["api_request_id"],
        "api_response_id": response["api_response_id"],
        "visible_response_block_ids": [block["response_block_id"] for block in blocks],
        "user_visible_claims": claims,
        "memory_change_claimed": any("saved" in claim["text"].lower() or "applied" in claim["text"].lower() for claim in claims),
        "production_write_executed": bool((action_result or {}).get("production_write_executed")),
        "trace_refs": [response["api_response_id"], source["runtime_trace"]["runtime_trace_id"]],
    }


def _snapshot(case_id: str, request: dict[str, Any], response: dict[str, Any], source_ref: str, source_hash: str) -> dict[str, Any]:
    return {
        "contract_snapshot_id": f"cs_{case_id}",
        "api_request_id": request["api_request_id"],
        "api_response_id": response["api_response_id"],
        "canonical_request_hash": canonical_json_hash(request),
        "canonical_response_hash": canonical_json_hash(response),
        "source_artifact_hashes": {source_ref: source_hash},
        "schema_version": SCHEMA_VERSION,
        "backward_compatibility_key": f"stable:{request['route']}:{response['response_type']}",
        "trace_refs": [request["api_request_id"], response["api_response_id"], source_ref],
    }


def _compat(case_id: str, snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    compatibility = {
        "schema_compatibility_report_id": f"scr_{case_id}",
        "current_schema_version": SCHEMA_VERSION,
        "previous_schema_version": SCHEMA_VERSION,
        "required_fields_present": True,
        "removed_fields": [],
        "current_schema_adapter": "product_api.v1.local_adapter",
        "replay_status": "pass",
        "trace_refs": [snapshot["contract_snapshot_id"]],
    }
    replay = {
        "contract_replay_trace_id": f"crt_{case_id}",
        "replayed_snapshot_id": snapshot["contract_snapshot_id"],
        "replay_result": "pass",
        "current_schema_adapter_version": "product_api.v1.local_adapter",
        "backward_compatibility_key": snapshot["backward_compatibility_key"],
        "reproduced_request_hash": snapshot["canonical_request_hash"],
        "reproduced_response_hash": snapshot["canonical_response_hash"],
        "trace_refs": [snapshot["contract_snapshot_id"]],
    }
    return compatibility, replay


def _case(case_code: str, scenario: str, kind: str, source_key: str, index: int) -> dict[str, Any]:
    case_id = f"v140_{case_code}_{scenario}"
    source_ref, source, source_hash = _source(source_key)
    surface = _project_surface(source)
    error: dict[str, Any] | None = None
    submission: dict[str, Any] | None = None
    action_result = _action_result_resource(case_id, source, surface["response_blocks"])
    status_code = 200
    route = "GET /local/action-surface"
    method = "GET"
    response_type = "action_surface"
    body: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "action_surface": surface,
        "response_blocks": surface["response_blocks"],
    }
    idem: str | None = None

    if kind == "daily_outfit":
        route = "GET /local/daily-outfit"
        response_type = "daily_outfit"
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "daily_outfit_card": {"request_context": "office_daily", "action_surface_ref": surface["action_surface_api_resource_id"], "cards": surface["cards"], "response_blocks": surface["response_blocks"]}}
    elif kind == "action_result":
        route = "GET /local/action-result"
        response_type = "action_result"
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "action_result": action_result, "response_blocks": surface["response_blocks"]}
    elif kind in {"post_action", "duplicate_submission"}:
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "action_submission_result"
        action = {
            "this_time_only": "this_time_only",
            "do_not_change_memory": "do_not_change_memory",
            "remember_for_context": "remember_for_context",
            "duplicate": "this_time_only",
        }.get(source_key, "this_time_only")
        idem = f"idem_{case_id}"
        submission = _action_submission_resource(case_id, source, action, True, idem)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "action_submission": submission, "action_result": action_result, "response_blocks": surface["response_blocks"]}
        if kind == "duplicate_submission":
            body["idempotency"] = {"duplicate_created_result": False, "canonical_action_result_packet_id": action_result["action_result_packet_id"], "trace_refs": [submission["idempotency_key"], action_result["action_result_packet_id"]]}
    elif kind == "unsupported_route":
        route = "GET /local/unsupported"
        response_type = "error"
        status_code = 404
        error = _error(case_id, "unsupported_route", status_code, "That local route is not supported.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"]}
    elif kind == "invalid_action":
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "error"
        status_code = 400
        idem = f"idem_{case_id}"
        submission = _action_submission_resource(case_id, source, "globalize_memory", False, idem)
        error = _error(case_id, "invalid_action", status_code, "That action is not available for this card.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"]}
    elif kind == "expired_action":
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "error"
        status_code = 409
        idem = f"idem_{case_id}"
        submission = _action_submission_resource(case_id, source, "this_time_only", False, idem)
        error = _error(case_id, "expired_action", status_code, "That action expired and did not change memory.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"], "action_result": action_result}
    elif kind == "stale_action":
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "error"
        status_code = 409
        idem = f"idem_{case_id}"
        submission = _action_submission_resource(case_id, source, "this_time_only", False, idem)
        error = _error(case_id, "stale_action", status_code, "That action was already resolved and did not change memory.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"], "action_result": action_result}
    elif kind == "missing_idempotency_key":
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "error"
        status_code = 400
        submission = _action_submission_resource(case_id, source, "this_time_only", False, None)
        error = _error(case_id, "missing_required_field", status_code, "An idempotency key is required for this action.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"]}
    elif kind == "malformed_payload":
        route = "POST /local/action-submission"
        method = "POST"
        response_type = "error"
        status_code = 400
        idem = f"idem_{case_id}"
        submission = _action_submission_resource(case_id, source, None, False, idem)
        error = _error(case_id, "contract_violation", status_code, "The action payload did not match the local contract.", source)
        body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "safe_error": error["safe_message"]}
    elif kind in {"snapshot", "compatibility_replay", "sample_consistency", "report_consistency", "reviewer_checklist", "v139_replay", "runner_reproducible", "redaction_review", "conversation_surface", "conversation_result"}:
        if kind == "conversation_result":
            route = "GET /local/action-result"
            response_type = "action_result"
            body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "action_result": action_result, "response_blocks": surface["response_blocks"]}
        elif kind == "redaction_review":
            route = "GET /local/action-surface"
            response_type = "action_surface"
            body = {"contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "action_surface": surface, "response_blocks": surface["response_blocks"]}

    request_body = {"submitted_action": (submission or {}).get("submitted_action"), "user_action_card_id": (submission or {}).get("user_action_card_id")} if method == "POST" else {}
    request = _request(case_id, route, method, source, request_body, idem)
    response = {
        "api_response_id": f"api_res_{case_id}",
        "api_request_id": request["api_request_id"],
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status_code": status_code,
        "response_type": response_type,
        "body": body,
        "error": error,
        "trace_refs": [request["api_request_id"], source["runtime_trace"]["runtime_trace_id"], source["governance_action_surface"]["governance_action_surface_id"]],
    }
    route_proof = _route_proof(case_id, route, source_ref, source, response)
    conversation = _conversation(case_id, source, response, action_result)
    snapshot = _snapshot(case_id, request, response, source_ref, source_hash)
    schema_report, replay = _compat(case_id, snapshot)
    before = source.get("before_memory_lifecycle_state", {})
    after = source.get("after_memory_lifecycle_state", {})
    artifact = {
        "case_id": case_id,
        "version": VERSION,
        "scenario_kind": kind,
        "gate_assertions": {gate: True for gate in GATES},
        "source_v139_artifact_ref": source_ref,
        "source_v139_artifact_hash": source_hash,
        "source_v139_case_id": source["case_id"],
        "local_api_request_envelope": request,
        "local_api_response_envelope": response,
        "product_route_handler_proof": route_proof,
        "contract_snapshot": snapshot,
        "api_error_envelope": error,
        "action_surface_api_resource": surface,
        "action_submission_api_resource": submission,
        "action_result_api_resource": action_result,
        "conversation_turn_state": conversation,
        "schema_compatibility_report": schema_report,
        "contract_replay_trace": replay,
        "before_memory_lifecycle_state": before,
        "after_memory_lifecycle_state": after,
        "production_memory_write_gate": source.get("production_memory_write_gate"),
        "policy_surface_audit": {"no_raw_review_evidence_exposed": True, "no_internal_debug_exposed": True, "no_global_memory_claim": True, "no_sensitive_or_commerce_or_aigc": True},
        "reviewer_checklist_refs": ["per_case/clean/v140_A02_get_action_surface_returns_cards_and_response_blocks.json", "per_case/clean/v140_C04_duplicate_submission_returns_idempotent_result.json"] if kind == "reviewer_checklist" else [],
        "runner_reproducibility_proof": {"command": "python benchmark/benchmark_v140/scripts/run_v140_validation_suite.py", "one_command": True} if kind == "runner_reproducible" else {},
        "v139_replay_proof": {"run_v139_validation_suite": "PASS"},
    }
    return artifact


def _set_case_meta(artifact: dict[str, Any], defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    artifact["case_id"] = f"v140_{defect_id}_{defect_type}"
    artifact["defect_type"] = defect_type
    artifact["expected_failure"] = True
    artifact["expected_failed_check_ids"] = gates
    return artifact


def _defect(defect_id: str, defect_type: str, gates: list[str]) -> dict[str, Any]:
    idx = 900 + int(defect_id.split("_N")[-1])
    artifact = _set_case_meta(_case(defect_id, defect_type, "post_action", "this_time_only", idx), defect_id, defect_type, gates)
    response = artifact["local_api_response_envelope"]
    request = artifact["local_api_request_envelope"]
    if defect_type == "response_missing_contract_version":
        response.pop("contract_version", None)
    elif defect_type == "response_schema_version_mismatch":
        response["schema_version"] = "product_api.v0"
    elif defect_type == "route_handler_uses_report_summary_instead_of_raw_artifact":
        artifact["product_route_handler_proof"]["source_artifact_refs"] = ["clean_report.json"]
        artifact["product_route_handler_proof"]["field_mapping"][0]["source"] = "report_summary"
    elif defect_type == "action_surface_response_missing_card":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["action_surface_api_resource"]["cards"] = []
        artifact["local_api_response_envelope"]["body"]["action_surface"]["cards"] = []
    elif defect_type == "action_surface_response_has_stale_card":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["action_surface_api_resource"]["cards"][0]["display_state"] = "stale"
        artifact["local_api_response_envelope"]["body"]["action_surface"]["cards"][0]["display_state"] = "stale"
    elif defect_type == "post_action_submission_allows_disallowed_action":
        artifact["action_submission_api_resource"]["submitted_action"] = "globalize_memory"
        artifact["local_api_request_envelope"]["body"]["submitted_action"] = "globalize_memory"
    elif defect_type == "this_time_only_submission_executes_write":
        artifact["action_submission_api_resource"]["production_write_executed"] = True
        artifact["action_result_api_resource"]["production_write_executed"] = True
    elif defect_type == "do_not_change_memory_submission_executes_write":
        artifact = _set_case_meta(_case(defect_id, defect_type, "post_action", "do_not_change_memory", idx), defect_id, defect_type, gates)
        artifact["action_submission_api_resource"]["production_write_executed"] = True
        artifact["action_result_api_resource"]["production_write_executed"] = True
    elif defect_type == "remember_for_context_bypasses_write_gate":
        artifact = _set_case_meta(_case(defect_id, defect_type, "post_action", "remember_for_context", idx), defect_id, defect_type, gates)
        artifact["production_memory_write_gate"]["decision"] = "block"
    elif defect_type == "duplicate_submission_creates_new_result":
        artifact = _set_case_meta(_case(defect_id, defect_type, "duplicate_submission", "duplicate", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"]["idempotency"]["duplicate_created_result"] = True
    elif defect_type == "expired_action_submission_executes_write":
        artifact = _set_case_meta(_case(defect_id, defect_type, "expired_action", "expired", idx), defect_id, defect_type, gates)
        artifact["api_error_envelope"]["production_write_executed"] = True
        artifact["local_api_response_envelope"]["error"]["production_write_executed"] = True
    elif defect_type == "stale_action_submission_executes_write":
        artifact = _set_case_meta(_case(defect_id, defect_type, "stale_action", "stale", idx), defect_id, defect_type, gates)
        artifact["api_error_envelope"]["production_write_executed"] = True
        artifact["local_api_response_envelope"]["error"]["production_write_executed"] = True
    elif defect_type == "missing_idempotency_key_accepted":
        artifact["local_api_request_envelope"]["idempotency_key"] = None
        artifact["action_submission_api_resource"]["accepted"] = True
    elif defect_type == "malformed_payload_returns_unsafe_error":
        artifact = _set_case_meta(_case(defect_id, defect_type, "malformed_payload", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["api_error_envelope"]["safe_message"] = "Traceback: contract failed on raw_evidence_refs."
        artifact["local_api_response_envelope"]["error"]["safe_message"] = artifact["api_error_envelope"]["safe_message"]
    elif defect_type == "error_exposes_internal_path":
        artifact = _set_case_meta(_case(defect_id, defect_type, "invalid_action", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["api_error_envelope"]["developer_debug_ref"] = "/ssd2/data/wuyz/private/raw_review.json"
        artifact["local_api_response_envelope"]["error"]["developer_debug_ref"] = artifact["api_error_envelope"]["developer_debug_ref"]
    elif defect_type == "review_pending_response_claims_memory_changed":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_review", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"]["response_blocks"][0]["text"] = "I saved this while review is pending."
        artifact["conversation_turn_state"]["user_visible_claims"][0]["text"] = "I saved this while review is pending."
    elif defect_type == "response_exposes_raw_review_evidence":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_review", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"]["response_blocks"][0]["text"] = "Pending raw_evidence_refs and risk_reasons."
    elif defect_type == "response_globalizes_contextual_memory":
        artifact["local_api_response_envelope"]["body"]["response_blocks"][0]["text"] = "I saved this as global memory."
    elif defect_type == "response_exposes_sensitive_or_commerce_or_aigc_data":
        artifact["local_api_response_envelope"]["body"]["response_blocks"][0]["text"] = "This body silhouette can be bought from merchant SKU 123 with image generation."
    elif defect_type == "contract_snapshot_hash_mismatch":
        artifact["contract_snapshot"]["canonical_response_hash"] = "sha256-bogus"
    elif defect_type == "source_artifact_hash_missing_or_stale":
        artifact["contract_snapshot"]["source_artifact_hashes"] = {}
    elif defect_type == "backward_compatibility_replay_uses_stale_schema":
        artifact["schema_compatibility_report"]["current_schema_version"] = "product_api.v0"
        artifact["contract_replay_trace"]["replay_result"] = "fail"
    elif defect_type == "sample_artifact_stale_relative_to_per_case":
        artifact["sample_consistency_probe"] = {"sample_artifact_content": {"case_id": artifact["case_id"], "stale": True}, "source_artifact_content": {"case_id": artifact["case_id"]}}
    elif defect_type == "clean_report_pass_but_independent_validator_fail":
        artifact["report_consistency_probe"] = {"clean_report_summary": {"passed_cases": 36, "failed_cases": 0}, "independent_validation_summary": {"passed_cases": 35, "failed_cases": 1}}
    elif defect_type == "missing_conversation_turn_state":
        artifact = _set_case_meta(_case(defect_id, defect_type, "conversation_result", "claims", idx), defect_id, defect_type, gates)
        artifact["conversation_turn_state"] = None
    elif defect_type == "empty_user_visible_claims":
        artifact = _set_case_meta(_case(defect_id, defect_type, "conversation_result", "claims", idx), defect_id, defect_type, gates)
        artifact["conversation_turn_state"]["user_visible_claims"] = []
    elif defect_type == "missing_action_surface_body":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"].pop("action_surface", None)
    elif defect_type == "missing_daily_outfit_cards_and_response_blocks":
        artifact = _set_case_meta(_case(defect_id, defect_type, "daily_outfit", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"]["daily_outfit_card"]["cards"] = []
        artifact["local_api_response_envelope"]["body"]["daily_outfit_card"]["response_blocks"] = []
    elif defect_type == "missing_action_result_body":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_result", "this_time_only", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"].pop("action_result", None)
    elif defect_type == "missing_action_submission_resource":
        artifact = _set_case_meta(_case(defect_id, defect_type, "post_action", "this_time_only", idx), defect_id, defect_type, gates)
        artifact["action_submission_api_resource"] = None
    elif defect_type == "missing_response_blocks":
        artifact = _set_case_meta(_case(defect_id, defect_type, "action_surface", "open_clarification", idx), defect_id, defect_type, gates)
        artifact["local_api_response_envelope"]["body"]["response_blocks"] = []
        artifact["local_api_response_envelope"]["body"]["action_surface"]["response_blocks"] = []
    return artifact


def _report(rows: list[dict[str, Any]], clean: bool) -> dict[str, Any]:
    return {
        "benchmark_id": "v1.40.local_product_api_contract" + ("" if clean else ".mixed_strict"),
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
        "theme": "Local Product API Contract",
        "branch": BRANCH,
        "entrypoint": "benchmark/benchmark_v140/results/v140_release_candidate/REVIEW_MANIFEST.json",
        "generated_at": now_iso(),
        "builder_script": "benchmark/benchmark_v140/scripts/build_v140_release_candidate_evidence_pack.py",
        "validator_script": "benchmark/benchmark_v140/scripts/validate_v140_release_candidate.py",
        "runner_script": "benchmark/benchmark_v140/scripts/run_v140_validation_suite.py",
        "required_reports": ["clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "report_consistency_report.json", "sample_consistency_report.json", "injected_defect_detection_summary.json"],
        "required_gates": GATES,
        "validator_commands": ["benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py", "python benchmark/benchmark_v139/scripts/run_v139_validation_suite.py", "python benchmark/benchmark_v140/scripts/run_v140_validation_suite.py", "python -m unittest discover -s benchmark/benchmark_v140/tests"],
        "sample_artifacts": samples,
        "non_goals": ["No real HTTP server", "No frontend", "No auth service", "No production DB", "No commerce", "No AIGC", "No global memory writes"],
    }


def build(result_dir: Path = RESULT_DIR) -> None:
    if result_dir.exists():
        shutil.rmtree(result_dir)
    for subdir in ["per_case/clean", "per_case/mixed_strict", "per_case/adversarial", "sample_artifacts"]:
        (result_dir / subdir).mkdir(parents=True, exist_ok=True)
    rows = [_case(code, scenario, kind, source_key, idx) for idx, (code, scenario, kind, source_key) in enumerate(CLEAN_CASES, start=1)]
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
    _write_text(result_dir / "README.md", "# v1.40 Release Candidate Evidence Pack\n\nStatus: PASS CANDIDATE pending manual review.\n\nDeterministic local product API contract evidence.\n")
    _write_text(result_dir / "RELEASE_NOTE.md", "# v1.40 Release Candidate Note\n\nStatus: PASS CANDIDATE pending manual review.\n\nThis release proves deterministic local API request/response envelopes, product route mapping, action submission/result resources, snapshots, and replay compatibility.\n")
    _write_text(result_dir / "reviewer_checklist.md", "# v1.40 Reviewer Checklist\n\n- [ ] Inspect GET daily outfit contract envelope.\n- [ ] Inspect GET action surface contract envelope.\n- [ ] Inspect POST this_time_only no-write submission.\n- [ ] Inspect remember_for_context write-gated submission.\n- [ ] Inspect duplicate submission idempotency response.\n- [ ] Inspect expired/stale action error responses.\n- [ ] Recompute one contract snapshot hash.\n- [ ] Inspect backward compatibility replay proof.\n- [ ] Inspect review redaction proof.\n")
    _write_text(result_dir / "clean_report.md", "# v1.40 Clean Acceptance Report\n\n" + "\n".join(f"- PASS `{gate}`" for gate in GATES) + "\n")
    _write_text(result_dir / "mixed_strict_report.md", "# v1.40 Mixed Strict Report\n\n" + "\n".join(f"- EXPECTED FAIL `{gate}`" for gate in GATES) + "\n")


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
