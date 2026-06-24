"""Independent raw-artifact validator for v1.41 runtime adapter evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.benchmark_v141.runtime.product_runtime_adapter import SUPPORTED_ROUTES
from benchmark.common.adversarial_validation import detected_defect_rows
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


VERSION = "v1.41"
CONTRACT_VERSION = "v1.40"
SCHEMA_VERSION = "product_runtime_adapter.v1"
API_SCHEMA_VERSION = "product_api.v1"
V140_DIR = Path("benchmark/benchmark_v140/results/v140_release_candidate")
V139_DIR = Path("benchmark/benchmark_v139/results/v139_release_candidate")

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
FORBIDDEN_SOURCE_NAMES = {"clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "README.md", "RELEASE_NOTE.md"}
FORBIDDEN_TERMS = {"raw_evidence", "risk_reasons", "internal_only", "/ssd2/", "traceback", "global memory", "globalize", "body", "identity", "attractive", "sku", "merchant", "affiliate", "aigc", "image generation"}
NO_WRITE_ACTIONS = {"this_time_only", "do_not_change_memory"}


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _same_state(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return {k: v for k, v in a.items() if k != "state_snapshot_id"} == {k: v for k, v in b.items() if k != "state_snapshot_id"}


def _texts(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_texts(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_texts(item))
        return out
    if isinstance(value, str):
        return [value.lower()]
    return []


def _response_blocks_from_body(body: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(body.get("response_blocks"), list):
        return body["response_blocks"]
    if isinstance((body.get("action_surface") or {}).get("response_blocks"), list):
        return body["action_surface"]["response_blocks"]
    if isinstance((body.get("daily_outfit_card") or {}).get("response_blocks"), list):
        return body["daily_outfit_card"]["response_blocks"]
    return []


def _source_artifact(artifact: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
    ref = artifact.get("runtime_source_resolution_proof", {}).get("source_v140_artifact_ref") or artifact.get("source_v140_artifact_ref")
    if not ref:
        return None, None
    path = V140_DIR / ref
    if not path.exists() or path.name in FORBIDDEN_SOURCE_NAMES:
        return path, None
    return path, read_json(path)


def _registry_handler(registry: dict[str, Any], route: str) -> str | None:
    matches = [row for row in registry.get("routes") or [] if row.get("route") == route]
    if len(matches) != 1:
        return None
    return matches[0].get("handler_name")


def _visible_texts(output: dict[str, Any], error: dict[str, Any] | None, conversation: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    body = output.get("body") or {}
    for block in body.get("response_blocks") or []:
        texts.append(str(block.get("text") or "").lower())
    for card in (body.get("action_surface") or {}).get("cards") or []:
        texts.append(str(card.get("title") or "").lower())
        texts.append(str(card.get("body") or "").lower())
    for card in (body.get("daily_outfit_card") or {}).get("cards") or []:
        texts.append(str(card.get("title") or "").lower())
        texts.append(str(card.get("body") or "").lower())
    if error:
        texts.append(str(error.get("safe_message") or "").lower())
        texts.append(str(error.get("developer_debug_ref") or "").lower())
    for claim in conversation.get("user_visible_claims") or []:
        texts.append(str(claim.get("text") or "").lower())
    return texts


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    adapter = artifact.get("product_runtime_adapter") or {}
    registry = artifact.get("product_route_registry") or {}
    invocation = artifact.get("route_handler_invocation") or {}
    result = artifact.get("route_handler_result") or {}
    trace = artifact.get("runtime_handler_execution_trace") or {}
    source_proof = artifact.get("runtime_source_resolution_proof") or {}
    snapshot = artifact.get("runtime_adapter_snapshot") or {}
    replay = artifact.get("golden_contract_replay") or {}
    output = result.get("output_envelope") or {}
    body = output.get("body") or {}
    error = output.get("error")
    submission = artifact.get("action_submission_api_resource")
    action_result = artifact.get("action_result_api_resource")
    conversation_raw = artifact.get("conversation_turn_state")
    conversation = conversation_raw if isinstance(conversation_raw, dict) else {}
    scenario = artifact.get("scenario_kind")
    source_path, source = _source_artifact(artifact)

    supported = list(SUPPORTED_ROUTES)
    routes = registry.get("routes") or []
    route_keys = [row.get("route") for row in routes]
    if adapter.get("version") != VERSION or adapter.get("contract_version") != CONTRACT_VERSION or adapter.get("schema_version") != SCHEMA_VERSION:
        failures.append("adapter_route_registry_complete_rate")
    if adapter.get("supported_routes") != supported or adapter.get("route_registry_id") != registry.get("product_route_registry_id"):
        failures.append("adapter_route_registry_complete_rate")
    if sorted(route_keys) != sorted(supported) or len(route_keys) != len(set(route_keys)) or len(routes) != len(supported):
        failures.append("adapter_route_registry_complete_rate")
    for route, (method, handler_name) in SUPPORTED_ROUTES.items():
        matches = [row for row in routes if row.get("route") == route]
        if len(matches) != 1 or matches[0].get("method") != method or matches[0].get("handler_name") != handler_name or matches[0].get("source_contract") != API_SCHEMA_VERSION:
            failures.append("adapter_route_registry_complete_rate")
    unsupported = registry.get("unsupported_route_policy") or {}
    if unsupported.get("handler_name") != "handle_unsupported_route" or unsupported.get("safe_error_only") is not True:
        failures.append("adapter_route_registry_complete_rate")

    request = invocation.get("input_envelope") or {}
    route = invocation.get("route")
    method = invocation.get("method")
    expected_method = SUPPORTED_ROUTES.get(route, (request.get("method"), "handle_unsupported_route"))[0]
    expected_handler = _registry_handler(registry, route) if route in SUPPORTED_ROUTES else "handle_unsupported_route"
    if request.get("contract_version") != CONTRACT_VERSION or output.get("contract_version") != CONTRACT_VERSION:
        failures.append("handler_output_matches_v140_contract_rate")
    if request.get("schema_version") != API_SCHEMA_VERSION or output.get("schema_version") != API_SCHEMA_VERSION:
        failures.append("handler_output_matches_v140_contract_rate")
    if request.get("route") != route or request.get("method") != method or method != expected_method:
        failures.append("route_handler_invocation_valid_rate")
    if invocation.get("handler_name") != expected_handler:
        failures.append("route_handler_invocation_valid_rate")
    if result.get("route_handler_invocation_id") != invocation.get("route_handler_invocation_id") or result.get("api_response_id") != output.get("api_response_id"):
        failures.append("route_handler_invocation_valid_rate")
    if request.get("api_request_id") != output.get("api_request_id"):
        failures.append("route_handler_invocation_valid_rate")
    if method == "POST" and output.get("response_type") != "error" and not invocation.get("idempotency_key"):
        failures.append("route_handler_invocation_valid_rate")
        failures.append("action_submission_handler_contract_rate")

    if trace.get("route_handler_invocation_id") != invocation.get("route_handler_invocation_id") or trace.get("route_handler_result_id") != result.get("route_handler_result_id") or trace.get("handler_name") != invocation.get("handler_name"):
        failures.append("handler_dispatch_trace_complete_rate")
    operations = {step.get("operation") for step in trace.get("dispatch_steps") or []}
    if not {"resolve_route", "invoke_handler", "produce_response"}.issubset(operations):
        failures.append("handler_dispatch_trace_complete_rate")
    if not trace.get("source_resolution_refs"):
        failures.append("handler_dispatch_trace_complete_rate")
        failures.append("handler_uses_raw_source_artifacts_rate")
    if not trace.get("contract_projection_refs"):
        failures.append("handler_dispatch_trace_complete_rate")
    if result.get("route_handler_invocation_id") not in (result.get("trace_refs") or []) or trace.get("runtime_handler_execution_trace_id") not in (result.get("trace_refs") or []):
        failures.append("handler_dispatch_trace_complete_rate")

    source_ref = source_proof.get("source_v140_artifact_ref")
    if not source_ref or any(name in source_ref for name in FORBIDDEN_SOURCE_NAMES) or source_proof.get("forbidden_source_types_observed"):
        failures.append("handler_uses_raw_source_artifacts_rate")
    if source_path is None or source is None:
        failures.append("handler_uses_raw_source_artifacts_rate")
        failures.append("runtime_source_hashes_match_raw_rate")
        failures.append("handler_output_matches_v140_contract_rate")
    else:
        if source_ref != artifact.get("source_v140_artifact_ref"):
            failures.append("handler_uses_raw_source_artifacts_rate")
        if source_proof.get("source_v140_artifact_hash") != file_json_hash(source_path):
            failures.append("runtime_source_hashes_match_raw_rate")
        if artifact.get("source_v140_artifact_hash") != file_json_hash(source_path):
            failures.append("runtime_source_hashes_match_raw_rate")
        v139_ref = source.get("source_v139_artifact_ref")
        v139_hash = source.get("source_v139_artifact_hash")
        if source_proof.get("source_v139_artifact_ref") != v139_ref or source_proof.get("source_v139_artifact_hash") != v139_hash:
            failures.append("runtime_source_hashes_match_raw_rate")
        if v139_ref and (not (V139_DIR / v139_ref).exists() or file_json_hash(V139_DIR / v139_ref) != v139_hash):
            failures.append("runtime_source_hashes_match_raw_rate")
        if request != source.get("local_api_request_envelope") or output != source.get("local_api_response_envelope"):
            failures.append("handler_output_matches_v140_contract_rate")

    if replay.get("source_v140_case_id") != artifact.get("source_v140_case_id") or replay.get("runtime_case_id") != artifact.get("case_id"):
        failures.append("golden_contract_replay_rate")
    if replay.get("request_match") is not True or replay.get("response_match") is not True or replay.get("trace_semantics_match") is not True or replay.get("snapshot_hash_match") is not True or replay.get("replay_status") != "pass" or replay.get("diff") != []:
        failures.append("golden_contract_replay_rate")
    if source and (request != source.get("local_api_request_envelope") or output != source.get("local_api_response_envelope")):
        failures.append("golden_contract_replay_rate")

    if method == "POST":
        if not isinstance(submission, dict):
            failures.append("action_submission_handler_contract_rate")
        else:
            request_body = request.get("body") or {}
            if request_body.get("submitted_action") != submission.get("submitted_action") or request_body.get("user_action_card_id") != submission.get("user_action_card_id"):
                failures.append("action_submission_handler_contract_rate")
            if request.get("idempotency_key") != submission.get("idempotency_key"):
                failures.append("action_submission_handler_contract_rate")
            action = submission.get("submitted_action")
            allowed = submission.get("allowed_actions_at_submission") or []
            accepted = submission.get("accepted") is True
            if accepted and action not in allowed:
                failures.append("action_submission_handler_contract_rate")
            if accepted and submission.get("card_display_state_at_submission") not in {"active", "resolved"}:
                failures.append("action_submission_handler_contract_rate")
            if accepted and not submission.get("idempotency_key"):
                failures.append("action_submission_handler_contract_rate")
            if action == "remember_for_context" and ((artifact.get("production_memory_write_gate") or {}).get("decision") != "allow" or (artifact.get("production_memory_write_gate") or {}).get("production_write_executed") is not True):
                failures.append("action_submission_handler_contract_rate")

    before = artifact.get("before_memory_lifecycle_state") or {}
    after = artifact.get("after_memory_lifecycle_state") or {}
    no_write_proof = artifact.get("handler_no_write_proof") or {}
    action = (submission or {}).get("submitted_action")
    no_write_expected = output.get("response_type") == "error" or action in NO_WRITE_ACTIONS or scenario in {"expired_action_handler_returns_expired_error_no_write", "stale_action_handler_returns_stale_error_no_write"}
    if no_write_expected:
        if result.get("production_write_executed") is True or no_write_proof.get("production_write_executed") is True or (submission or {}).get("production_write_executed") is True or (action_result or {}).get("production_write_executed") is True or not _same_state(before, after):
            failures.append("no_write_handler_preserves_memory_state_rate")

    idem = body.get("idempotency") or {}
    idem_proof = artifact.get("handler_idempotency_proof") or {}
    if scenario in {"duplicate_submission_handler_is_idempotent", "duplicate_handler_reuses_canonical_action_result", "idempotency_scope_is_trace_backed"} or (submission or {}).get("idempotency_key"):
        if scenario.startswith("duplicate") and (idem.get("duplicate_created_result") is not False or not idem.get("canonical_action_result_packet_id")):
            failures.append("idempotent_handler_replay_rate")
        if scenario.startswith("duplicate") and idem_proof.get("canonical_action_result_packet_id") != idem.get("canonical_action_result_packet_id"):
            failures.append("idempotent_handler_replay_rate")
        if submission and invocation.get("idempotency_key") != submission.get("idempotency_key"):
            failures.append("idempotent_handler_replay_rate")

    if scenario in {"expired_action_handler_returns_expired_error_no_write", "stale_action_handler_returns_stale_error_no_write"} or (error or {}).get("error_type") in {"expired_action", "stale_action"}:
        expected = "expired_action" if "expired" in str(scenario) else "stale_action"
        if output.get("response_type") != "error" or not error or error.get("error_type") != expected or error.get("production_write_executed") is not False or result.get("production_write_executed") is True:
            failures.append("expired_stale_handler_no_write_rate")

    body_result = body.get("action_result")
    result_bearing = (route == "GET /local/action-result" and output.get("response_type") == "action_result") or (route == "POST /local/action-submission" and output.get("response_type") == "action_submission_result") or "conversation" in str(scenario) or isinstance(body_result, dict)
    if result_bearing:
        if not isinstance(action_result, dict) or not isinstance(body_result, dict) or body_result != action_result:
            failures.append("runtime_action_result_links_response_rate")
    if isinstance(action_result, dict):
        surface_blocks = {block.get("response_block_id") for block in (artifact.get("action_surface_api_resource") or {}).get("response_blocks") or []}
        for block_id in action_result.get("user_visible_response_block_ids") or []:
            if block_id not in surface_blocks or block_id not in set(action_result.get("response_block_refs") or []):
                failures.append("runtime_action_result_links_response_rate")

    visible_blocks = _response_blocks_from_body(body)
    visible_block_ids = [block.get("response_block_id") for block in visible_blocks]
    claims = conversation.get("user_visible_claims") or []
    response_block_ids = {block.get("response_block_id") for block in (artifact.get("action_surface_api_resource") or {}).get("response_blocks") or []}
    result_id = (action_result or {}).get("action_result_packet_id")
    decision_id = (action_result or {}).get("governance_resolution_decision_id")
    if not isinstance(conversation_raw, dict):
        failures.append("conversation_claims_trace_backed_after_handler_rate")
    else:
        if conversation.get("api_request_id") != request.get("api_request_id") or conversation.get("api_response_id") != output.get("api_response_id"):
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        if visible_block_ids and conversation.get("visible_response_block_ids") != visible_block_ids:
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        if visible_blocks and not claims:
            failures.append("conversation_claims_trace_backed_after_handler_rate")
    claim_refs: set[Any] = set()
    for claim in claims:
        refs = set(claim.get("trace_refs") or [])
        if output.get("api_response_id") not in refs:
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        if visible_block_ids and not refs.intersection(response_block_ids):
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        if result_id and result_id not in refs:
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        if decision_id and decision_id not in refs:
            failures.append("conversation_claims_trace_backed_after_handler_rate")
        claim_refs.update(refs)
    for block_id in visible_block_ids:
        if block_id not in claim_refs:
            failures.append("conversation_claims_trace_backed_after_handler_rate")

    if snapshot.get("canonical_input_hash") != canonical_json_hash(request) or snapshot.get("canonical_output_hash") != canonical_json_hash(output) or snapshot.get("canonical_handler_trace_hash") != canonical_json_hash(trace):
        failures.append("runtime_snapshot_hash_reproducible_rate")
    source_hashes = snapshot.get("source_artifact_hashes") or {}
    if source_path is None or source is None or source_hashes.get(artifact.get("source_v140_artifact_ref")) != artifact.get("source_v140_artifact_hash"):
        failures.append("runtime_snapshot_hash_reproducible_rate")
        failures.append("runtime_source_hashes_match_raw_rate")

    texts = _visible_texts(output, error, conversation)
    if error:
        if error.get("production_write_executed") is not False or not str(error.get("developer_debug_ref", "")).startswith("trace:") or "/" in str(error.get("developer_debug_ref", "")):
            failures.append("runtime_error_safety_rate")
            failures.append("runtime_redaction_policy_safe_rate")
    if output.get("response_type") == "error" and not error:
        failures.append("runtime_error_safety_rate")
    if any(term in text for text in texts for term in FORBIDDEN_TERMS):
        failures.append("runtime_error_safety_rate" if output.get("response_type") == "error" else "runtime_redaction_policy_safe_rate")
        failures.append("runtime_redaction_policy_safe_rate")
    claims_memory_change_without_write = any("saved" in text or "applied" in text for text in texts) and not conversation.get("production_write_executed")
    if (source and source.get("scenario_kind") == "open_review" and claims_memory_change_without_write) or ("review_pending" in str(scenario) and claims_memory_change_without_write):
        failures.append("conversation_claims_trace_backed_after_handler_rate")
        failures.append("runtime_redaction_policy_safe_rate")
    audit = artifact.get("policy_surface_audit") or {}
    if audit.get("no_raw_review_evidence_exposed") is not True or audit.get("no_internal_debug_exposed") is not True or audit.get("no_global_memory_claim") is not True or audit.get("no_sensitive_or_commerce_or_aigc") is not True:
        failures.append("runtime_redaction_policy_safe_rate")

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v140_replay_proof") or {}).get("run_v140_validation_suite") != "PASS":
        failures.append("v140_validation_replay_pass_rate")
    return sorted(set(failures))


def validate_case(path: Path, subset: str, base_dir: Path) -> dict[str, Any]:
    artifact = read_json(path)
    failed = _structural_failures(artifact)
    return {
        "case_id": artifact.get("case_id") or path.stem,
        "artifact_ref": str(path.relative_to(base_dir)),
        "passed": not failed,
        "failed_check_ids": failed,
        "expected_failed_check_ids": artifact.get("expected_failed_check_ids", []),
        "defect_type": artifact.get("defect_type"),
    }


def validate_directory(result_dir: Path, subset: str) -> dict[str, Any]:
    cases = [validate_case(path, subset, result_dir) for path in json_files(_artifact_dir(result_dir, subset))]
    checks: list[dict[str, Any]] = []
    for gate in GATES:
        passed = [case for case in cases if gate not in case["failed_check_ids"]]
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw v1.41 runtime adapter validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.41.independent.in_process_product_runtime_adapter_validator",
        "generated_at": now_iso(),
        "result_dir": str(result_dir),
        "subset": subset,
        "suite_summary": {
            "total_cases": len(cases),
            "passed_cases": sum(1 for case in cases if case["passed"]),
            "failed_cases": sum(1 for case in cases if not case["passed"]),
            "total_checks": len(GATES),
            "passed_checks": sum(1 for check in checks if check["passed"]),
            "failed_checks": sum(1 for check in checks if not check["passed"]),
        },
        "checks": checks,
        "case_results": cases,
    }
    if subset in {"adversarial", "mixed_strict"}:
        report["detected_defects"] = detected_defect_rows(cases)
        report["detected_defect_count"] = sum(1 for row in report["detected_defects"] if row["detected"])
    return report


def write_consistency_reports(result_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sample = check_sample_consistency(result_dir)
    write_json(result_dir / "sample_consistency_report.json", {**sample, "generated_at": now_iso()})
    write_json(result_dir / "report_consistency_report.json", {"validator": "benchmark.common.report_consistency", "generated_at": now_iso(), "passed": False, "status": "generating"})
    report = check_report_consistency(result_dir, GATES)
    write_json(result_dir / "report_consistency_report.json", {**report, "generated_at": now_iso()})
    return sample, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="benchmark/benchmark_v141/results/v141_release_candidate")
    parser.add_argument("--subset", choices=["clean", "adversarial", "mixed_strict"], default="clean")
    parser.add_argument("--output")
    parser.add_argument("--write-consistency", action="store_true")
    args = parser.parse_args()
    result_dir = Path(args.result_dir)
    report = validate_directory(result_dir, args.subset)
    if args.output:
        write_json(Path(args.output), report)
    if args.subset == "adversarial":
        rows = report.get("detected_defects", [])
        seeded = len(rows)
        detected = sum(1 for row in rows if row.get("detected"))
        write_json(result_dir / "injected_defect_detection_summary.json", {"version": VERSION, "generated_at": now_iso(), "verdict": "pass" if detected == seeded else "fail", "seeded_defects": seeded, "detected_defects": detected, "unexpected_injected_passes": [row for row in rows if not row.get("detected")], "detected": rows})
    if args.write_consistency:
        write_consistency_reports(result_dir)
    print(json.dumps(report["suite_summary"], ensure_ascii=False, indent=2))
    if args.subset == "clean" and report["suite_summary"]["failed_cases"]:
        raise SystemExit(1)
    if args.subset in {"adversarial", "mixed_strict"} and report["suite_summary"]["passed_cases"]:
        raise SystemExit(1)
    if args.subset == "adversarial" and report.get("detected_defect_count") != report["suite_summary"]["total_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
