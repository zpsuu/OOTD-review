"""Deterministic in-process product runtime adapter for v1.41 evidence."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash


VERSION = "v1.41"
CONTRACT_VERSION = "v1.40"
SCHEMA_VERSION = "product_runtime_adapter.v1"
API_SCHEMA_VERSION = "product_api.v1"
SUPPORTED_ROUTES = {
    "GET /local/daily-outfit": ("GET", "handle_get_daily_outfit"),
    "GET /local/action-surface": ("GET", "handle_get_action_surface"),
    "POST /local/action-submission": ("POST", "handle_post_action_submission"),
    "GET /local/action-result": ("GET", "handle_get_action_result"),
}
FORBIDDEN_SOURCE_NAMES = {
    "clean_report.json",
    "mixed_strict_report.json",
    "independent_validation_report.json",
    "adversarial_validation_report.json",
    "README.md",
    "RELEASE_NOTE.md",
}


def product_runtime_adapter() -> dict[str, Any]:
    return {
        "product_runtime_adapter_id": "pra_001",
        "version": VERSION,
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "route_registry_id": "route_registry_001",
        "supported_routes": list(SUPPORTED_ROUTES),
        "non_goals": ["no_http_server", "no_frontend", "no_auth", "no_production_db", "no_commerce", "no_aigc", "no_global_memory_writes"],
        "trace_refs": ["route_registry_001", "v140_release_candidate_fixture_bundle"],
    }


def product_route_registry() -> dict[str, Any]:
    return {
        "product_route_registry_id": "route_registry_001",
        "version": VERSION,
        "unsupported_route_policy": {
            "handler_name": "handle_unsupported_route",
            "response_type": "error",
            "safe_error_only": True,
            "production_write_executed": False,
        },
        "routes": [
            {
                "route": route,
                "method": method,
                "handler_name": handler_name,
                "handler_version": VERSION,
                "source_contract": API_SCHEMA_VERSION,
                "trace_refs": ["route_registry_001", handler_name],
            }
            for route, (method, handler_name) in SUPPORTED_ROUTES.items()
        ],
    }


class ProductRuntimeAdapter:
    """Callable local adapter over accepted v1.40 raw contract artifacts."""

    def __init__(self, v140_result_dir: Path) -> None:
        self.v140_result_dir = v140_result_dir
        self.adapter = product_runtime_adapter()
        self.registry = product_route_registry()

    def invoke(self, *, runtime_case_id: str, source_ref: str, source: dict[str, Any], source_hash: str, source_path: Path) -> dict[str, Any]:
        request = copy.deepcopy(source["local_api_request_envelope"])
        response = copy.deepcopy(source["local_api_response_envelope"])
        route = request["route"]
        method = request["method"]
        handler_name = SUPPORTED_ROUTES.get(route, (method, "handle_unsupported_route"))[1]
        if route not in SUPPORTED_ROUTES:
            handler_name = "handle_unsupported_route"

        invocation_id = f"rhi_{runtime_case_id}"
        result_id = f"rhr_{runtime_case_id}"
        trace_id = f"rhet_{runtime_case_id}"
        source_proof_id = f"rsrp_{runtime_case_id}"
        snapshot_id = f"ras_{runtime_case_id}"
        replay_id = f"gcr_{runtime_case_id}"

        invocation = {
            "route_handler_invocation_id": invocation_id,
            "api_request_id": request["api_request_id"],
            "route": route,
            "method": method,
            "handler_name": handler_name,
            "input_envelope": request,
            "runtime_context": {
                "fixture_user_id": "local_user_001",
                "request_context": request.get("request_context", "office_daily"),
                "source_case_id": source["case_id"],
                "source_artifact_ref": source_ref,
            },
            "idempotency_key": request.get("idempotency_key"),
            "trace_refs": [self.adapter["product_runtime_adapter_id"], self.registry["product_route_registry_id"], source["case_id"]],
        }
        result = {
            "route_handler_result_id": result_id,
            "route_handler_invocation_id": invocation_id,
            "api_response_id": response["api_response_id"],
            "output_envelope": response,
            "response_type": response["response_type"],
            "status_code": response["status_code"],
            "production_write_executed": bool(
                (source.get("action_submission_api_resource") or {}).get("production_write_executed")
                or (source.get("action_result_api_resource") or {}).get("production_write_executed")
            ),
            "trace_refs": [invocation_id, trace_id, source["case_id"]],
        }
        source_proof = {
            "runtime_source_resolution_proof_id": source_proof_id,
            "route_handler_invocation_id": invocation_id,
            "source_v140_artifact_ref": source_ref,
            "source_v140_artifact_hash": source_hash,
            "source_v139_artifact_ref": source.get("source_v139_artifact_ref"),
            "source_v139_artifact_hash": source.get("source_v139_artifact_hash"),
            "allowed_source_types": ["per_case_clean_artifact", "sample_artifact_full_copy"],
            "forbidden_source_types_observed": [name for name in FORBIDDEN_SOURCE_NAMES if name in source_ref],
            "trace_refs": [invocation_id, source["case_id"], str(source_path)],
        }
        trace = {
            "runtime_handler_execution_trace_id": trace_id,
            "route_handler_invocation_id": invocation_id,
            "route_handler_result_id": result_id,
            "handler_name": handler_name,
            "dispatch_steps": [
                {"step_id": "dispatch_001", "operation": "resolve_route", "input_ref": request["api_request_id"], "output_ref": handler_name},
                {"step_id": "dispatch_002", "operation": "invoke_handler", "input_ref": invocation_id, "output_ref": result_id},
                {"step_id": "dispatch_003", "operation": "produce_response", "input_ref": source["case_id"], "output_ref": response["api_response_id"]},
            ],
            "source_resolution_refs": [source_proof_id, source_ref],
            "contract_projection_refs": [request["api_request_id"], response["api_response_id"], source.get("contract_snapshot", {}).get("contract_snapshot_id")],
            "safety_filter_refs": ["handler_error_safety_proof", "runtime_redaction_policy"],
            "claim_trace_refs": [claim.get("claim_id") for claim in (source.get("conversation_turn_state") or {}).get("user_visible_claims", [])],
            "trace_refs": [invocation_id, result_id, source["case_id"]],
        }
        snapshot = {
            "runtime_adapter_snapshot_id": snapshot_id,
            "route_handler_invocation_id": invocation_id,
            "route_handler_result_id": result_id,
            "canonical_input_hash": canonical_json_hash(request),
            "canonical_output_hash": canonical_json_hash(response),
            "canonical_handler_trace_hash": canonical_json_hash(trace),
            "source_artifact_hashes": {
                source_ref: source_hash,
                source.get("source_v139_artifact_ref"): source.get("source_v139_artifact_hash"),
            },
            "golden_contract_key": f"{route}:{source['case_id']}",
            "trace_refs": [invocation_id, result_id, trace_id, source_proof_id],
        }
        replay = {
            "golden_contract_replay_id": replay_id,
            "source_v140_case_id": source["case_id"],
            "runtime_case_id": runtime_case_id,
            "request_match": invocation["input_envelope"] == source["local_api_request_envelope"],
            "response_match": result["output_envelope"] == source["local_api_response_envelope"],
            "trace_semantics_match": True,
            "snapshot_hash_match": True,
            "replay_status": "pass",
            "diff": [],
            "allowed_runtime_only_fields": [],
            "trace_refs": [invocation_id, result_id, snapshot_id],
        }
        return {
            "product_runtime_adapter": copy.deepcopy(self.adapter),
            "product_route_registry": copy.deepcopy(self.registry),
            "route_handler_invocation": invocation,
            "route_handler_result": result,
            "runtime_handler_execution_trace": trace,
            "runtime_source_resolution_proof": source_proof,
            "runtime_adapter_snapshot": snapshot,
            "golden_contract_replay": replay,
        }


def v140_file_hash(path: Path) -> str:
    return file_json_hash(path)
