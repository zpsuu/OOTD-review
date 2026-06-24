"""Independent raw-artifact validator for v1.40 local product API contracts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.adversarial_validation import detected_defect_rows
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


CONTRACT_VERSION = "v1.40"
SCHEMA_VERSION = "product_api.v1"
V139_DIR = Path("benchmark/benchmark_v139/results/v139_release_candidate")

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

ROUTE_METHODS = {
    "GET /local/daily-outfit": "GET",
    "GET /local/action-surface": "GET",
    "POST /local/action-submission": "POST",
    "GET /local/action-result": "GET",
    "GET /local/unsupported": "GET",
}
ERROR_TYPES = {"unsupported_route", "invalid_action", "expired_action", "stale_action", "duplicate_submission", "missing_required_field", "contract_violation"}
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
    texts: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            texts.extend(_texts(item))
    elif isinstance(value, list):
        for item in value:
            texts.extend(_texts(item))
    elif isinstance(value, str):
        texts.append(value.lower())
    return texts


def _visible_texts(response: dict[str, Any], error: dict[str, Any] | None, conversation: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    body = response.get("body") or {}
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


def _response_blocks_from_body(body: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(body.get("response_blocks"), list):
        return body["response_blocks"]
    action_surface = body.get("action_surface") or {}
    if isinstance(action_surface.get("response_blocks"), list):
        return action_surface["response_blocks"]
    daily = body.get("daily_outfit_card") or {}
    if isinstance(daily.get("response_blocks"), list):
        return daily["response_blocks"]
    return []


def _project_v139_surface(source: dict[str, Any]) -> dict[str, Any]:
    surface = source["governance_action_surface"]
    return {
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
    }


def _source_artifact(artifact: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
    ref = artifact.get("source_v139_artifact_ref")
    if not ref:
        return None, None
    path = V139_DIR / ref
    if not path.exists():
        return path, None
    return path, read_json(path)


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    request = artifact.get("local_api_request_envelope") or {}
    response = artifact.get("local_api_response_envelope") or {}
    route_proof = artifact.get("product_route_handler_proof") or {}
    snapshot = artifact.get("contract_snapshot") or {}
    error = artifact.get("api_error_envelope")
    surface = artifact.get("action_surface_api_resource") or {}
    submission = artifact.get("action_submission_api_resource")
    action_result = artifact.get("action_result_api_resource")
    conversation_raw = artifact.get("conversation_turn_state")
    conversation = conversation_raw if isinstance(conversation_raw, dict) else {}
    compatibility = artifact.get("schema_compatibility_report") or {}
    replay = artifact.get("contract_replay_trace") or {}
    before = artifact.get("before_memory_lifecycle_state") or {}
    after = artifact.get("after_memory_lifecycle_state") or {}
    gate = artifact.get("production_memory_write_gate") or {}
    scenario = artifact.get("scenario_kind")
    source_path, source = _source_artifact(artifact)
    body = response.get("body") or {}

    if request.get("contract_version") != CONTRACT_VERSION or response.get("contract_version") != CONTRACT_VERSION:
        failures.append("api_request_response_envelope_valid_rate")
        failures.append("schema_version_consistency_rate")
    if request.get("schema_version") != SCHEMA_VERSION or response.get("schema_version") != SCHEMA_VERSION:
        failures.append("api_request_response_envelope_valid_rate")
        failures.append("schema_version_consistency_rate")
    if request.get("method") != ROUTE_METHODS.get(request.get("route")):
        failures.append("api_request_response_envelope_valid_rate")
    if response.get("api_request_id") != request.get("api_request_id") or request.get("api_request_id") not in (response.get("trace_refs") or []):
        failures.append("api_request_response_envelope_valid_rate")
    if response.get("response_type") == "error":
        if not error or response.get("error") != error or error.get("error_type") not in ERROR_TYPES or error.get("status_code") != response.get("status_code"):
            failures.append("api_request_response_envelope_valid_rate")
        if error and (not error.get("trace_refs") or error.get("production_write_executed") is not False):
            failures.append("api_request_response_envelope_valid_rate")
    elif response.get("status_code") != 200 or response.get("error") is not None:
        failures.append("api_request_response_envelope_valid_rate")
    if request.get("method") == "POST" and response.get("response_type") != "error" and not request.get("idempotency_key"):
        failures.append("action_submission_contract_valid_rate")

    source_refs = route_proof.get("source_artifact_refs") or []
    if not source_refs or artifact.get("source_v139_artifact_ref") not in source_refs:
        failures.append("route_handler_maps_to_raw_artifacts_rate")
    for mapping in route_proof.get("field_mapping") or []:
        if str(mapping.get("source", "")).startswith("report") or "report" in str(mapping.get("source", "")):
            failures.append("route_handler_maps_to_raw_artifacts_rate")
    redaction = route_proof.get("redaction_proof") or {}
    if redaction.get("raw_human_review_evidence_exposed") is not False or redaction.get("internal_only_fields_exposed") is not False:
        failures.append("route_handler_maps_to_raw_artifacts_rate")
        failures.append("redaction_policy_safe_response_rate")

    if source is None:
        failures.append("source_artifact_hashes_match_raw_rate")
        failures.append("action_surface_api_matches_v139_surface_rate")
    else:
        projected = _project_v139_surface(source)
        if surface.get("cards") != projected["cards"] or surface.get("response_blocks") != projected["response_blocks"]:
            failures.append("action_surface_api_matches_v139_surface_rate")
        route = request.get("route")
        response_type = response.get("response_type")
        if route == "GET /local/action-surface" and response_type == "action_surface":
            body_surface = body.get("action_surface")
            if not isinstance(body_surface, dict) or body_surface.get("cards") != projected["cards"] or body_surface.get("response_blocks") != projected["response_blocks"]:
                failures.append("action_surface_api_matches_v139_surface_rate")
            if body.get("response_blocks") != projected["response_blocks"]:
                failures.append("action_surface_api_matches_v139_surface_rate")
        elif route == "GET /local/daily-outfit" and response_type == "daily_outfit":
            daily = body.get("daily_outfit_card")
            if not isinstance(daily, dict) or daily.get("cards") != projected["cards"] or daily.get("response_blocks") != projected["response_blocks"]:
                failures.append("action_surface_api_matches_v139_surface_rate")
        elif body.get("response_blocks") is not None and body.get("response_blocks") != projected["response_blocks"]:
            failures.append("action_surface_api_matches_v139_surface_rate")

        if response_type in {"action_surface", "daily_outfit", "action_result", "action_submission_result"} and not _response_blocks_from_body(body):
            failures.append("action_surface_api_matches_v139_surface_rate")

    post_action_submission = request.get("route") == "POST /local/action-submission"
    if post_action_submission and not isinstance(submission, dict):
        failures.append("action_submission_contract_valid_rate")
    if post_action_submission and isinstance(submission, dict):
        request_body = request.get("body") or {}
        if request_body.get("submitted_action") != submission.get("submitted_action") or request_body.get("user_action_card_id") != submission.get("user_action_card_id"):
            failures.append("action_submission_contract_valid_rate")
        if request.get("idempotency_key") != submission.get("idempotency_key"):
            failures.append("action_submission_contract_valid_rate")
        if response.get("response_type") == "action_submission_result" and (body.get("action_submission") or {}) != submission:
            failures.append("action_submission_contract_valid_rate")
        if response.get("response_type") == "error":
            if submission.get("accepted") is not False or submission.get("production_write_executed") is not False:
                failures.append("action_submission_contract_valid_rate")
                failures.append("no_write_error_preserves_memory_state_rate")

    if submission:
        action = submission.get("submitted_action")
        allowed = submission.get("allowed_actions_at_submission") or []
        accepted = submission.get("accepted") is True
        if accepted and action not in allowed:
            failures.append("action_submission_contract_valid_rate")
        if accepted and submission.get("card_display_state_at_submission") not in {"active", "resolved"}:
            failures.append("action_submission_contract_valid_rate")
        if accepted and not submission.get("idempotency_key"):
            failures.append("action_submission_contract_valid_rate")
        if accepted and request.get("idempotency_key") != submission.get("idempotency_key"):
            failures.append("action_submission_contract_valid_rate")
        if action == "remember_for_context" and (gate.get("decision") != "allow" or gate.get("production_write_executed") is not True):
            failures.append("action_submission_contract_valid_rate")
        if action in NO_WRITE_ACTIONS and (submission.get("production_write_executed") is True or (action_result or {}).get("production_write_executed") is True or not _same_state(before, after)):
            failures.append("no_write_error_preserves_memory_state_rate")

    body = response.get("body") or {}
    idem = body.get("idempotency") or {}
    if scenario == "duplicate_submission":
        if idem.get("duplicate_created_result") is not False or not idem.get("canonical_action_result_packet_id"):
            failures.append("idempotent_submission_contract_rate")
        if action_result and idem.get("canonical_action_result_packet_id") != action_result.get("action_result_packet_id"):
            failures.append("idempotent_submission_contract_rate")

    if scenario in {"expired_action", "stale_action"}:
        if response.get("response_type") != "error" or not error:
            failures.append("expired_stale_action_contract_rate")
        expected = "expired_action" if scenario == "expired_action" else "stale_action"
        if error and (error.get("error_type") != expected or error.get("production_write_executed") is not False):
            failures.append("expired_stale_action_contract_rate")
            failures.append("no_write_error_preserves_memory_state_rate")

    route = request.get("route")
    response_type = response.get("response_type")
    body_result = body.get("action_result")
    result_bearing = (
        (route == "GET /local/action-result" and response_type == "action_result")
        or (route == "POST /local/action-submission" and response_type == "action_submission_result" and response.get("status_code") == 200)
        or scenario == "conversation_result"
        or isinstance(body_result, dict)
    )
    if result_bearing:
        if not isinstance(action_result, dict) or not isinstance(body_result, dict):
            failures.append("action_result_api_links_response_rate")
        elif body_result != action_result:
            failures.append("action_result_api_links_response_rate")

    if isinstance(action_result, dict):
        response_block_ids = {block.get("response_block_id") for block in surface.get("response_blocks") or []}
        for block_id in action_result.get("user_visible_response_block_ids") or []:
            if block_id not in response_block_ids or block_id not in set(action_result.get("response_block_refs") or []):
                failures.append("action_result_api_links_response_rate")

    response_block_ids = {block.get("response_block_id") for block in surface.get("response_blocks") or []}
    result_id = (action_result or {}).get("action_result_packet_id")
    decision_id = (action_result or {}).get("governance_resolution_decision_id")
    visible_blocks = _response_blocks_from_body(body)
    claims = conversation.get("user_visible_claims") or []
    if not isinstance(conversation_raw, dict):
        failures.append("conversation_turn_claims_trace_backed_rate")
    else:
        if conversation.get("api_request_id") != request.get("api_request_id") or conversation.get("api_response_id") != response.get("api_response_id"):
            failures.append("conversation_turn_claims_trace_backed_rate")
        if visible_blocks and not claims:
            failures.append("conversation_turn_claims_trace_backed_rate")
        visible_block_ids = [block.get("response_block_id") for block in visible_blocks]
        if visible_block_ids and conversation.get("visible_response_block_ids") != visible_block_ids:
            failures.append("conversation_turn_claims_trace_backed_rate")
    claim_refs: set[Any] = set()
    for claim in claims:
        refs = set(claim.get("trace_refs") or [])
        if conversation.get("api_response_id") not in refs:
            failures.append("conversation_turn_claims_trace_backed_rate")
        if not refs.intersection(response_block_ids):
            failures.append("conversation_turn_claims_trace_backed_rate")
        if result_id and result_id not in refs:
            failures.append("conversation_turn_claims_trace_backed_rate")
        if decision_id and decision_id not in refs:
            failures.append("conversation_turn_claims_trace_backed_rate")
        claim_refs.update(refs)
    for block in visible_blocks:
        if block.get("response_block_id") not in claim_refs:
            failures.append("conversation_turn_claims_trace_backed_rate")
    visible_texts = _visible_texts(response, error, conversation)
    claims_memory_change_without_write = any("saved" in text or "applied" in text for text in visible_texts) and not conversation.get("production_write_executed")
    if source and source.get("scenario_kind") == "open_review" and claims_memory_change_without_write:
        failures.append("conversation_turn_claims_trace_backed_rate")

    if snapshot.get("canonical_request_hash") != canonical_json_hash(request) or snapshot.get("canonical_response_hash") != canonical_json_hash(response):
        failures.append("contract_snapshot_hash_reproducible_rate")
    source_hashes = snapshot.get("source_artifact_hashes") or {}
    if source_path is None or not source_hashes:
        failures.append("source_artifact_hashes_match_raw_rate")
    elif source_hashes.get(artifact.get("source_v139_artifact_ref")) != file_json_hash(source_path):
        failures.append("source_artifact_hashes_match_raw_rate")
    if artifact.get("source_v139_artifact_hash") != source_hashes.get(artifact.get("source_v139_artifact_ref")):
        failures.append("source_artifact_hashes_match_raw_rate")

    if compatibility.get("current_schema_version") != SCHEMA_VERSION or compatibility.get("required_fields_present") is not True or compatibility.get("removed_fields") != [] or compatibility.get("replay_status") != "pass":
        failures.append("backward_compatibility_replay_rate")
        failures.append("schema_version_consistency_rate")
    if replay.get("replay_result") != "pass" or replay.get("backward_compatibility_key") != snapshot.get("backward_compatibility_key") or replay.get("reproduced_request_hash") != snapshot.get("canonical_request_hash") or replay.get("reproduced_response_hash") != snapshot.get("canonical_response_hash"):
        failures.append("backward_compatibility_replay_rate")

    if any(term in text for text in visible_texts for term in FORBIDDEN_TERMS):
        failures.append("redaction_policy_safe_response_rate")
    if source and source.get("scenario_kind") == "open_review" and claims_memory_change_without_write:
        failures.append("redaction_policy_safe_response_rate")
    audit = artifact.get("policy_surface_audit") or {}
    if audit.get("no_raw_review_evidence_exposed") is not True or audit.get("no_internal_debug_exposed") is not True or audit.get("no_global_memory_claim") is not True or audit.get("no_sensitive_or_commerce_or_aigc") is not True:
        failures.append("redaction_policy_safe_response_rate")
    if error:
        if not str(error.get("developer_debug_ref", "")).startswith("trace:") or "/" in str(error.get("developer_debug_ref", "")):
            failures.append("redaction_policy_safe_response_rate")

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v139_replay_proof") or {}).get("run_v139_validation_suite") != "PASS":
        failures.append("v139_validation_replay_pass_rate")
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
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw v1.40 local API contract validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.40.independent.local_product_api_contract_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v140/results/v140_release_candidate")
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
        write_json(result_dir / "injected_defect_detection_summary.json", {"version": "v1.40", "generated_at": now_iso(), "verdict": "pass" if detected == seeded else "fail", "seeded_defects": seeded, "detected_defects": detected, "unexpected_injected_passes": [row for row in rows if not row.get("detected")], "detected": rows})
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
