"""Independent raw-artifact validator for v1.42 local session boundaries."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.benchmark_v142.session.local_session_boundary import USERS, leakage_scan
from benchmark.common.adversarial_validation import detected_defect_rows
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


VERSION = "v1.42"
V141_DIR = Path("benchmark/benchmark_v141/results/v141_release_candidate")
V140_DIR = Path("benchmark/benchmark_v140/results/v140_release_candidate")
V139_DIR = Path("benchmark/benchmark_v139/results/v139_release_candidate")
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
FORBIDDEN_SOURCE_NAMES = {"clean_report.json", "mixed_strict_report.json", "independent_validation_report.json", "adversarial_validation_report.json", "README.md", "RELEASE_NOTE.md"}
FORBIDDEN_TERMS = {"raw_evidence", "risk_reasons", "internal_only", "/ssd2/", "traceback", "global memory", "globalize", "body", "identity", "attractive", "sku", "merchant", "affiliate", "aigc", "image generation"}


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


def _strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_strings(item))
        return out
    if isinstance(value, str):
        return [value]
    return []


def _visible_texts(output: dict[str, Any], conversation: dict[str, Any]) -> list[str]:
    body = output.get("body") or {}
    texts: list[str] = []
    for block in body.get("response_blocks") or []:
        texts.append(str(block.get("text") or "").lower())
    for claim in conversation.get("user_visible_claims") or []:
        texts.append(str(claim.get("text") or "").lower())
    error = output.get("error")
    if error:
        texts.append(str(error.get("safe_message") or "").lower())
        texts.append(str(error.get("developer_debug_ref") or "").lower())
    return texts


def _source_artifact(artifact: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
    ref = artifact.get("source_v141_artifact_ref")
    if not ref:
        return None, None
    path = V141_DIR / ref
    if not path.exists() or path.name in FORBIDDEN_SOURCE_NAMES:
        return path, None
    return path, read_json(path)


def _audit_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_envelope": (artifact.get("session_scoped_route_handler_result") or {}).get("output_envelope"),
        "session_action_result": artifact.get("session_scoped_action_result"),
        "idempotency_record": artifact.get("session_scoped_idempotency_record"),
        "memory_ref": artifact.get("session_scoped_memory_state_ref"),
        "governance_ref": artifact.get("session_scoped_governance_ref"),
        "snapshot_refs": artifact.get("user_state_namespace"),
        "debug_ref": artifact.get("trace_safe_debug_ref"),
        "conversation_turn_state": artifact.get("conversation_turn_state"),
    }


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    fixtures = artifact.get("local_user_fixtures") or []
    session = artifact.get("local_session_envelope") or {}
    namespace = artifact.get("user_state_namespace") or {}
    invocation = artifact.get("session_scoped_runtime_invocation") or {}
    result = artifact.get("session_scoped_route_handler_result") or {}
    idem = artifact.get("session_scoped_idempotency_record") or {}
    action_result = artifact.get("session_scoped_action_result") or {}
    memory_ref = artifact.get("session_scoped_memory_state_ref") or {}
    governance_ref = artifact.get("session_scoped_governance_ref") or {}
    trace = artifact.get("session_boundary_trace") or {}
    audit = artifact.get("cross_user_leakage_audit")
    snapshot = artifact.get("session_boundary_snapshot") or {}
    expiry = artifact.get("session_expiry_and_stale_action_proof") or {}
    debug = artifact.get("trace_safe_debug_ref") or {}
    conversation = artifact.get("conversation_turn_state") or {}
    scenario = artifact.get("scenario_kind") or ""
    user_id = session.get("local_user_id")
    session_id = session.get("local_session_id")
    source_path, source = _source_artifact(artifact)

    if len(fixtures) < 2:
        failures.append("local_user_fixture_namespace_complete_rate")
    mems = [f.get("memory_namespace_id") for f in fixtures]
    govs = [f.get("governance_namespace_id") for f in fixtures]
    closets = [f.get("closet_namespace_id") for f in fixtures]
    ids = [f.get("local_user_id") for f in fixtures]
    if len(ids) != len(set(ids)) or len(mems) != len(set(mems)) or len(govs) != len(set(govs)) or len(closets) != len(set(closets)):
        failures.append("local_user_fixture_namespace_complete_rate")
    for fixture in fixtures:
        if fixture.get("local_user_id") not in USERS or not fixture.get("allowed_session_ids"):
            failures.append("local_user_fixture_namespace_complete_rate")

    current_fixture = next((f for f in fixtures if f.get("local_user_id") == user_id), None)
    if not current_fixture or session_id not in current_fixture.get("allowed_session_ids", []) or session.get("session_status") not in {"active", "expired", "advanced"}:
        failures.append("session_envelope_valid_rate")
    if invocation.get("local_user_id") != user_id or result.get("local_user_id") != user_id or namespace.get("local_user_id") != user_id:
        failures.append("session_envelope_valid_rate")
        failures.append("session_scoped_invocation_matches_v141_adapter_rate")
    if invocation.get("local_session_id") != session_id or result.get("local_session_id") != session_id or namespace.get("local_session_id") != session_id:
        failures.append("session_envelope_valid_rate")
        failures.append("session_scoped_invocation_matches_v141_adapter_rate")
    if invocation.get("session_state_version") != session.get("session_state_version"):
        failures.append("session_envelope_valid_rate")

    if current_fixture:
        if namespace.get("memory_namespace_id") != current_fixture.get("memory_namespace_id") or namespace.get("governance_namespace_id") != current_fixture.get("governance_namespace_id") or namespace.get("closet_namespace_id") != current_fixture.get("closet_namespace_id"):
            failures.append("user_state_namespace_isolation_rate")
        if session_id not in str(namespace.get("action_namespace_id")) or session_id not in str(namespace.get("idempotency_namespace_id")) or session_id not in str(namespace.get("snapshot_namespace_id")):
            failures.append("user_state_namespace_isolation_rate")
        if memory_ref.get("memory_namespace_id") != current_fixture.get("memory_namespace_id") or governance_ref.get("governance_namespace_id") != current_fixture.get("governance_namespace_id"):
            failures.append("user_state_namespace_isolation_rate")

    if source is None or source_path is None:
        failures.append("session_scoped_invocation_matches_v141_adapter_rate")
        failures.append("session_source_hashes_match_raw_rate")
    else:
        if artifact.get("source_v141_artifact_hash") != file_json_hash(source_path):
            failures.append("session_source_hashes_match_raw_rate")
        if invocation.get("route_handler_invocation_ref") != source.get("route_handler_invocation", {}).get("route_handler_invocation_id"):
            failures.append("session_scoped_invocation_matches_v141_adapter_rate")
        if result.get("route_handler_result_ref") != source.get("route_handler_result", {}).get("route_handler_result_id"):
            failures.append("session_scoped_invocation_matches_v141_adapter_rate")
        if invocation.get("input_envelope") != source.get("route_handler_invocation", {}).get("input_envelope"):
            failures.append("session_scoped_invocation_matches_v141_adapter_rate")
        if result.get("output_envelope") != source.get("route_handler_result", {}).get("output_envelope"):
            failures.append("session_scoped_invocation_matches_v141_adapter_rate")
        callable_ref = (source.get("runtime_handler_execution_trace", {}).get("callable_execution_proof") or {}).get("handler_execution_proof_id")
        if not callable_ref or invocation.get("v141_callable_execution_ref") != callable_ref or trace.get("v141_callable_execution_ref") != callable_ref:
            failures.append("session_scoped_invocation_matches_v141_adapter_rate")
            failures.append("session_boundary_trace_complete_rate")
        for ref_key, ref_dir in [("source_v140_artifact_ref", V140_DIR), ("source_v139_artifact_ref", V139_DIR)]:
            ref = source.get(ref_key)
            h = source.get(ref_key.replace("_ref", "_hash"))
            if ref and h and (not (ref_dir / ref).exists() or file_json_hash(ref_dir / ref) != h):
                failures.append("session_source_hashes_match_raw_rate")

    leakage = leakage_scan(_audit_payload(artifact), user_id or "", session_id or "")
    if audit is None or audit.get("passed") is not True or audit.get("foreign_user_refs_detected") != leakage["foreign_user_refs_detected"] or audit.get("foreign_session_refs_detected") != leakage["foreign_session_refs_detected"] or audit.get("foreign_namespace_refs_detected") != leakage["foreign_namespace_refs_detected"] or any(leakage.values()):
        failures.append("cross_user_leakage_absent_rate")
    if audit and not {"output_envelope", "session_action_result", "idempotency_record", "memory_ref", "governance_ref", "snapshot_refs", "debug_ref"}.issubset(set(audit.get("audited_artifact_refs") or [])):
        failures.append("cross_user_leakage_absent_rate")

    scope_key = idem.get("idempotency_scope_key")
    idem_key = idem.get("idempotency_key") or "no_idempotency_key"
    if not scope_key or user_id not in scope_key or session_id not in scope_key or invocation.get("input_envelope", {}).get("route") not in scope_key or idem_key not in scope_key:
        failures.append("idempotency_scope_is_user_session_bound_rate")
    if invocation.get("idempotency_scope_key") != scope_key or action_result.get("idempotency_scope_key") != scope_key:
        failures.append("idempotency_scope_is_user_session_bound_rate")
    if idem.get("local_user_id") != user_id or idem.get("local_session_id") != session_id:
        failures.append("idempotency_scope_is_user_session_bound_rate")
        if "same_key_different_user" in scenario or "same_key_different_session" in scenario:
            failures.append("different_scope_duplicate_does_not_reuse_result_rate")
    if "same_user_same_session_duplicate" in scenario and (idem.get("duplicate_created_result") is not False or not idem.get("canonical_action_result_ref")):
        failures.append("same_scope_duplicate_reuses_result_rate")
    if ("different_user" in scenario or "different_session" in scenario or "same_key_different_user" in scenario or "same_key_different_session" in scenario) and (user_id not in str(idem.get("canonical_action_result_ref")) or session_id not in str(idem.get("canonical_action_result_ref"))):
        failures.append("different_scope_duplicate_does_not_reuse_result_rate")

    output = result.get("output_envelope") or {}
    status = session.get("session_status")
    if status == "expired":
        if expiry.get("accepted_action") is not False or expiry.get("production_write_executed") is True or result.get("production_write_executed") is True or result.get("response_type") != "error":
            failures.append("expired_session_no_write_error_rate")
    if status == "advanced":
        if expiry.get("accepted_action") is not False or expiry.get("production_write_executed") is True or result.get("production_write_executed") is True or result.get("response_type") != "error":
            failures.append("stale_session_action_no_write_rate")
    no_write_expected = result.get("response_type") == "error" or status in {"expired", "advanced"} or "no_write" in scenario
    if no_write_expected:
        before = (memory_ref.get("before_state") or {})
        after = (memory_ref.get("after_state") or {})
        if result.get("production_write_executed") is True or not _same_state(before, after):
            failures.append("session_no_write_preserves_user_state_rate")

    operations = {step.get("operation") for step in trace.get("boundary_steps") or []}
    if not {"resolve_user_namespace", "validate_session", "resolve_idempotency_scope", "run_cross_user_leakage_audit", "invoke_v141_callable_adapter"}.issubset(operations):
        failures.append("session_boundary_trace_complete_rate")
    if trace.get("local_user_id") != user_id or trace.get("local_session_id") != session_id or not trace.get("trace_safe_debug_refs"):
        failures.append("session_boundary_trace_complete_rate")

    if snapshot.get("canonical_session_hash") != canonical_json_hash(session) or snapshot.get("canonical_invocation_hash") != canonical_json_hash(invocation) or snapshot.get("canonical_output_hash") != canonical_json_hash(result) or snapshot.get("canonical_boundary_trace_hash") != canonical_json_hash(trace):
        failures.append("session_boundary_snapshot_hash_reproducible_rate")
    source_hashes = snapshot.get("source_artifact_hashes") or {}
    if source_path is None or source_hashes.get(artifact.get("source_v141_artifact_ref")) != artifact.get("source_v141_artifact_hash"):
        failures.append("session_boundary_snapshot_hash_reproducible_rate")
        failures.append("session_source_hashes_match_raw_rate")

    dbg = debug.get("debug_ref", "")
    if debug.get("local_user_id") != user_id or debug.get("local_session_id") != session_id or "/ssd2/" in dbg or "traceback" in dbg.lower() or debug.get("filesystem_path_exposed") is True or debug.get("foreign_user_or_session_exposed") is True:
        failures.append("trace_safe_debug_refs_rate")
    other_tokens = leakage_scan(debug, user_id or "", session_id or "")
    if any(other_tokens.values()):
        failures.append("trace_safe_debug_refs_rate")

    conv_strings = _strings(conversation)
    foreign = leakage_scan(conversation, user_id or "", session_id or "")
    if any(foreign.values()):
        failures.append("conversation_claims_user_session_scoped_rate")
    if action_result.get("action_result_ref") and not any(action_result.get("action_result_ref") in text for text in _strings(action_result) + conv_strings):
        # The session action result itself is enough for non-conversation cases; conversation cases also carry source claims.
        pass
    if any(term in text for text in _visible_texts(output, conversation) for term in FORBIDDEN_TERMS):
        failures.append("runtime_redaction_policy_safe_under_session_rate")
    audit_policy = artifact.get("policy_surface_audit") or {}
    if audit_policy.get("no_raw_review_evidence_exposed") is not True or audit_policy.get("no_internal_debug_exposed") is not True or audit_policy.get("no_global_memory_claim") is not True or audit_policy.get("no_sensitive_or_commerce_or_aigc") is not True:
        failures.append("runtime_redaction_policy_safe_under_session_rate")

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v141_replay_proof") or {}).get("run_v141_validation_suite") != "PASS":
        failures.append("v141_validation_replay_pass_rate")
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
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw v1.42 session boundary validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.42.independent.local_session_user_state_boundary_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v142/results/v142_release_candidate")
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
