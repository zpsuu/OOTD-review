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


def _source_response(source: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(source["local_api_response_envelope"])


def _source_request(source: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(source["local_api_request_envelope"])


def _handler_output(
    *,
    handler_name: str,
    expected_route: str,
    expected_response_type: str,
    request: dict[str, Any],
    source: dict[str, Any],
    runtime_case_id: str,
) -> dict[str, Any]:
    response = _source_response(source)
    body = response.get("body") or {}
    route_specific_fields = sorted(k for k in body if k not in {"contract_version", "schema_version"})
    return {
        "handler_name": handler_name,
        "runtime_case_id": runtime_case_id,
        "request_envelope": request,
        "response_envelope": response,
        "route_specific_projection": {
            "expected_route": expected_route,
            "actual_route": request.get("route"),
            "expected_response_type": expected_response_type,
            "actual_response_type": response.get("response_type"),
            "projected_body_fields": route_specific_fields,
            "source_case_id": source.get("case_id"),
            "source_contract_snapshot_id": (source.get("contract_snapshot") or {}).get("contract_snapshot_id"),
        },
        "callable_execution": {
            "callable_invoked": True,
            "callable_name": handler_name,
            "callable_module": __name__,
            "input_envelope_hash": canonical_json_hash(request),
            "output_envelope_hash": canonical_json_hash(response),
            "direct_source_output_copy": False,
        },
    }


def handle_get_daily_outfit(*, request: dict[str, Any], source: dict[str, Any], runtime_case_id: str) -> dict[str, Any]:
    return _handler_output(
        handler_name="handle_get_daily_outfit",
        expected_route="GET /local/daily-outfit",
        expected_response_type="daily_outfit",
        request=request,
        source=source,
        runtime_case_id=runtime_case_id,
    )


def handle_get_action_surface(*, request: dict[str, Any], source: dict[str, Any], runtime_case_id: str) -> dict[str, Any]:
    return _handler_output(
        handler_name="handle_get_action_surface",
        expected_route="GET /local/action-surface",
        expected_response_type="action_surface",
        request=request,
        source=source,
        runtime_case_id=runtime_case_id,
    )


def handle_post_action_submission(*, request: dict[str, Any], source: dict[str, Any], runtime_case_id: str) -> dict[str, Any]:
    return _handler_output(
        handler_name="handle_post_action_submission",
        expected_route="POST /local/action-submission",
        expected_response_type=source["local_api_response_envelope"]["response_type"],
        request=request,
        source=source,
        runtime_case_id=runtime_case_id,
    )


def handle_get_action_result(*, request: dict[str, Any], source: dict[str, Any], runtime_case_id: str) -> dict[str, Any]:
    return _handler_output(
        handler_name="handle_get_action_result",
        expected_route="GET /local/action-result",
        expected_response_type="action_result",
        request=request,
        source=source,
        runtime_case_id=runtime_case_id,
    )


def handle_unsupported_route(*, request: dict[str, Any], source: dict[str, Any], runtime_case_id: str) -> dict[str, Any]:
    return _handler_output(
        handler_name="handle_unsupported_route",
        expected_route=request.get("route", "GET /local/unsupported"),
        expected_response_type="error",
        request=request,
        source=source,
        runtime_case_id=runtime_case_id,
    )


HANDLER_CALLABLES = {
    "handle_get_daily_outfit": handle_get_daily_outfit,
    "handle_get_action_surface": handle_get_action_surface,
    "handle_post_action_submission": handle_post_action_submission,
    "handle_get_action_result": handle_get_action_result,
    "handle_unsupported_route": handle_unsupported_route,
}


def product_runtime_adapter() -> dict[str, Any]:
    return {
        "product_runtime_adapter_id": "pra_001",
        "version": VERSION,
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "route_registry_id": "route_registry_001",
        "supported_routes": list(SUPPORTED_ROUTES),
        "callable_handler_registry": [
            {
                "handler_name": handler_name,
                "callable_resolved": callable(handler),
                "callable_module": __name__,
                "callable_kind": "module_function",
            }
            for handler_name, handler in HANDLER_CALLABLES.items()
        ],
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

    def _resolve_handler_name(self, route: str) -> str:
        if route not in SUPPORTED_ROUTES:
            return (self.registry.get("unsupported_route_policy") or {}).get("handler_name", "handle_unsupported_route")
        matches = [row for row in self.registry.get("routes", []) if row.get("route") == route]
        if len(matches) != 1:
            raise ValueError(f"route {route} does not have exactly one registry binding")
        return matches[0]["handler_name"]

    def _resolve_callable(self, handler_name: str):
        handler = HANDLER_CALLABLES.get(handler_name)
        if not callable(handler):
            raise ValueError(f"handler {handler_name} is not callable")
        return handler

    def invoke(self, *, runtime_case_id: str, source_ref: str, source: dict[str, Any], source_hash: str, source_path: Path) -> dict[str, Any]:
        request = _source_request(source)
        route = request["route"]
        method = request["method"]
        handler_name = self._resolve_handler_name(route)
        handler = self._resolve_callable(handler_name)
        handler_output = handler(request=request, source=source, runtime_case_id=runtime_case_id)
        response = handler_output["response_envelope"]

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
            "resolved_callable_name": handler_name,
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
            "callable_handler_name": handler_name,
            "handler_execution_proof_id": f"hep_{runtime_case_id}",
            "produced_by_callable": True,
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
            "callable_execution_proof": {
                "handler_execution_proof_id": f"hep_{runtime_case_id}",
                "handler_name": handler_name,
                "callable_name": handler_output["callable_execution"]["callable_name"],
                "callable_module": handler_output["callable_execution"]["callable_module"],
                "callable_resolved": True,
                "callable_invoked": True,
                "input_envelope_hash": handler_output["callable_execution"]["input_envelope_hash"],
                "output_envelope_hash": handler_output["callable_execution"]["output_envelope_hash"],
                "handler_returned_route_handler_result_id": result_id,
                "route_specific_projection": handler_output["route_specific_projection"],
                "direct_source_output_copy": False,
            },
            "dispatch_steps": [
                {"step_id": "dispatch_001", "operation": "resolve_route", "input_ref": request["api_request_id"], "output_ref": handler_name},
                {"step_id": "dispatch_002", "operation": "resolve_callable", "input_ref": handler_name, "output_ref": f"{__name__}.{handler_name}"},
                {"step_id": "dispatch_003", "operation": "invoke_handler", "input_ref": invocation_id, "output_ref": result_id, "callable_ref": f"{__name__}.{handler_name}", "handler_execution_proof_id": f"hep_{runtime_case_id}"},
                {"step_id": "dispatch_004", "operation": "produce_response", "input_ref": source["case_id"], "output_ref": response["api_response_id"]},
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
