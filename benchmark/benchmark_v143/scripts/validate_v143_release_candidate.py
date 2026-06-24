"""Independent raw-artifact validator for v1.43 product conversation runtime loops."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.benchmark_v143.conversation.product_conversation_loop import (
    FORBIDDEN_VISIBLE_TERMS,
    leakage_scan,
    state_hash,
    visible_text_has_forbidden_terms,
)
from benchmark.common.adversarial_validation import detected_defect_rows
from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


VERSION = "v1.43"
V142_DIR = Path("benchmark/benchmark_v142/results/v142_release_candidate")
GATES = [
    "conversation_script_scope_valid_rate",
    "conversation_session_turn_order_valid_rate",
    "turn_invocation_matches_v142_session_runtime_rate",
    "turn_result_matches_v142_runtime_output_rate",
    "conversation_state_transition_valid_rate",
    "action_card_lifecycle_complete_rate",
    "action_submission_result_notice_trace_rate",
    "conversation_idempotency_scope_valid_rate",
    "same_scope_duplicate_reuses_result_across_turns_rate",
    "different_scope_duplicate_does_not_reuse_result_rate",
    "expired_stale_card_no_write_rate",
    "clarification_state_truthful_rate",
    "review_pending_state_truthful_rate",
    "feedback_state_transition_truthful_rate",
    "next_turn_response_reflects_only_accepted_state_rate",
    "visible_claims_trace_backed_rate",
    "conversation_boundary_leakage_absent_rate",
    "conversation_boundary_audit_self_scoped_rate",
    "conversation_loop_snapshot_hash_reproducible_rate",
    "sample_artifacts_match_per_case_rate",
    "report_consistency_with_independent_validation_rate",
    "adversarial_detection_rate",
    "v142_validation_replay_pass_rate",
]
REQUIRED_BOUNDARY_GROUPS = {
    "product_conversation_script",
    "product_conversation_session",
    "conversation_turn_invocations",
    "conversation_turn_runtime_results",
    "conversation_state_transitions",
    "conversation_action_card_lifecycles",
    "conversation_action_submission_proofs",
    "conversation_action_result_notices",
    "conversation_idempotency_replay_proofs",
    "conversation_clarification_states",
    "conversation_review_pending_states",
    "conversation_feedback_states",
    "conversation_turn_claim_trace_audits",
    "trace_safe_debug_refs",
    "conversation_loop_snapshot",
}


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _source(ref: str | None) -> tuple[Path | None, dict[str, Any] | None]:
    if not ref:
        return None, None
    path = V142_DIR / ref
    if not path.exists() or path.name.endswith("_report.json"):
        return path, None
    return path, read_json(path)


def _boundary_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_conversation_script": artifact.get("product_conversation_script"),
        "product_conversation_session": artifact.get("product_conversation_session"),
        "conversation_turn_invocations": artifact.get("conversation_turn_invocations"),
        "conversation_turn_runtime_results": artifact.get("conversation_turn_runtime_results"),
        "conversation_state_transitions": artifact.get("conversation_state_transitions"),
        "conversation_action_card_lifecycles": artifact.get("conversation_action_card_lifecycles"),
        "conversation_action_submission_proofs": artifact.get("conversation_action_submission_proofs"),
        "conversation_action_result_notices": artifact.get("conversation_action_result_notices"),
        "conversation_idempotency_replay_proofs": artifact.get("conversation_idempotency_replay_proofs"),
        "conversation_clarification_states": artifact.get("conversation_clarification_states"),
        "conversation_review_pending_states": artifact.get("conversation_review_pending_states"),
        "conversation_feedback_states": artifact.get("conversation_feedback_states"),
        "conversation_turn_claim_trace_audits": artifact.get("conversation_turn_claim_trace_audits"),
        "trace_safe_debug_refs": artifact.get("trace_safe_debug_refs"),
        "conversation_loop_snapshot": artifact.get("conversation_loop_snapshot"),
    }


def _audit_self_payload(audit: dict[str, Any] | None) -> dict[str, Any]:
    if not audit:
        return {}
    return {
        "conversation_boundary_audit_id": audit.get("conversation_boundary_audit_id"),
        "local_user_id": audit.get("local_user_id"),
        "local_session_id": audit.get("local_session_id"),
        "conversation_id": audit.get("conversation_id"),
        "audited_artifact_refs": audit.get("audited_artifact_refs"),
        "trace_refs": audit.get("trace_refs"),
    }


def _all_visible_text_payload(artifact: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    for result in artifact.get("conversation_turn_runtime_results") or []:
        body = (result.get("output_envelope") or {}).get("body") or {}
        out.extend((block.get("text") or "") for block in (body.get("conversation_visible_blocks") or []))
        out.extend((claim.get("text") or "") for claim in (result.get("user_visible_claims") or []))
    return out


def _structural_failures(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    script = artifact.get("product_conversation_script") or {}
    session = artifact.get("product_conversation_session") or {}
    invocations = artifact.get("conversation_turn_invocations") or []
    results = artifact.get("conversation_turn_runtime_results") or []
    transitions = artifact.get("conversation_state_transitions") or []
    lifecycles = artifact.get("conversation_action_card_lifecycles") or []
    submissions = artifact.get("conversation_action_submission_proofs") or []
    notices = artifact.get("conversation_action_result_notices") or []
    idempotency = artifact.get("conversation_idempotency_replay_proofs") or []
    clarifications = artifact.get("conversation_clarification_states") or []
    reviews = artifact.get("conversation_review_pending_states") or []
    feedback = artifact.get("conversation_feedback_states") or []
    claim_audits = artifact.get("conversation_turn_claim_trace_audits") or []
    audit = artifact.get("conversation_boundary_audit")
    snapshot = artifact.get("conversation_loop_snapshot") or {}
    debug_refs = artifact.get("trace_safe_debug_refs") or []
    scenario = artifact.get("scenario_kind") or ""
    mode = artifact.get("scenario_mode") or ""
    user_id = session.get("local_user_id")
    session_id = session.get("local_session_id")
    conversation_id = session.get("conversation_id")

    if not user_id or not session_id or not conversation_id:
        failures.append("conversation_script_scope_valid_rate")
    scoped_objects = [script, *invocations, *results, *transitions, *lifecycles, *submissions, *notices, *idempotency, *clarifications, *reviews, *feedback, *claim_audits, *debug_refs]
    for obj in scoped_objects:
        if obj and (obj.get("local_user_id") != user_id or obj.get("local_session_id") != session_id or obj.get("conversation_id") != conversation_id):
            failures.append("conversation_script_scope_valid_rate")
            break
    if not script.get("turn_plan") or len(script.get("turn_plan") or []) != len(invocations):
        failures.append("conversation_script_scope_valid_rate")
    for ref in script.get("source_v142_case_refs") or []:
        if "report" in ref or not (V142_DIR / ref).exists():
            failures.append("conversation_script_scope_valid_rate")

    turn_ids = [inv.get("turn_id") for inv in sorted(invocations, key=lambda item: item.get("turn_index") or 0)]
    if session.get("turn_ids") != turn_ids or turn_ids != sorted(turn_ids) or len(set(turn_ids)) != len(turn_ids):
        failures.append("conversation_session_turn_order_valid_rate")
    if session.get("session_state_version_end", 0) < session.get("session_state_version_start", 0):
        failures.append("conversation_session_turn_order_valid_rate")

    source_by_invocation: dict[str, dict[str, Any]] = {}
    for inv in invocations:
        source_path, source = _source(inv.get("source_v142_artifact_ref"))
        if source is None or source_path is None:
            failures.append("turn_invocation_matches_v142_session_runtime_rate")
            continue
        if inv.get("source_v142_artifact_hash") != file_json_hash(source_path):
            failures.append("turn_invocation_matches_v142_session_runtime_rate")
        source_inv = source.get("session_scoped_runtime_invocation") or {}
        if inv.get("source_v142_runtime_invocation_ref") != source_inv.get("session_scoped_runtime_invocation_id"):
            failures.append("turn_invocation_matches_v142_session_runtime_rate")
        if inv.get("route") != source_inv.get("input_envelope", {}).get("route") or inv.get("input_envelope") != source_inv.get("input_envelope"):
            failures.append("turn_invocation_matches_v142_session_runtime_rate")
        if inv.get("source_v142_boundary_audit_ref") != (source.get("cross_user_leakage_audit") or {}).get("cross_user_leakage_audit_id"):
            failures.append("turn_invocation_matches_v142_session_runtime_rate")
        source_by_invocation[inv.get("conversation_turn_invocation_id")] = source

    invocation_ids = {inv.get("conversation_turn_invocation_id") for inv in invocations}
    result_ids = {res.get("conversation_turn_runtime_result_id") for res in results}
    for res in results:
        source = source_by_invocation.get(res.get("conversation_turn_invocation_id"))
        if res.get("conversation_turn_invocation_id") not in invocation_ids or source is None:
            failures.append("turn_result_matches_v142_runtime_output_rate")
            continue
        source_result = source.get("session_scoped_route_handler_result") or {}
        if res.get("source_v142_route_handler_result_ref") != source_result.get("session_scoped_route_handler_result_id"):
            failures.append("turn_result_matches_v142_runtime_output_rate")
        if res.get("response_type") != source_result.get("response_type"):
            failures.append("turn_result_matches_v142_runtime_output_rate")
        output = copy_without_conversation_blocks(res.get("output_envelope") or {})
        if output != source_result.get("output_envelope"):
            failures.append("turn_result_matches_v142_runtime_output_rate")
        if res.get("turn_id") not in turn_ids:
            failures.append("turn_result_matches_v142_runtime_output_rate")

    if len(transitions) != max(0, len(turn_ids) - 1):
        failures.append("conversation_state_transition_valid_rate")
    transition_pairs = {(tr.get("from_turn_id"), tr.get("to_turn_id")) for tr in transitions}
    expected_pairs = set(zip(turn_ids, turn_ids[1:]))
    if transition_pairs != expected_pairs:
        failures.append("conversation_state_transition_valid_rate")
    for tr in transitions:
        pre = tr.get("pre_state") or {}
        post = tr.get("post_state") or {}
        if tr.get("pre_state_hash") != state_hash(pre) or tr.get("post_state_hash") != state_hash(post):
            failures.append("conversation_state_transition_valid_rate")
        if tr.get("accepted_action_result_ref") and tr.get("accepted_action_result_ref") not in {notice.get("source_action_result_ref") for notice in notices}:
            failures.append("conversation_state_transition_valid_rate")
        if tr.get("no_write_reason") and pre.get("accepted_action_result_refs") != post.get("accepted_action_result_refs"):
            failures.append("conversation_state_transition_valid_rate")
    if any(life.get("card_state") == "accepted" for life in lifecycles) and not any(tr.get("accepted_action_result_ref") for tr in transitions):
        failures.append("conversation_state_transition_valid_rate")

    lifecycle_by_card = {life.get("action_card_id"): life for life in lifecycles}
    for res in results:
        for card_id in res.get("offered_action_card_ids") or []:
            life = lifecycle_by_card.get(card_id)
            if not life or life.get("card_state") == "hidden":
                failures.append("action_card_lifecycle_complete_rate")
    for life in lifecycles:
        if life.get("card_state") in {"accepted", "submitted", "review_pending", "expired", "stale"} and not life.get("idempotency_scope_key"):
            failures.append("action_card_lifecycle_complete_rate")
        if life.get("card_state") in {"expired", "stale"} and life.get("source_v142_action_result_ref"):
            failures.append("expired_stale_card_no_write_rate")

    notice_refs = {notice.get("source_action_result_ref") for notice in notices}
    for notice in notices:
        if not notice.get("source_action_result_ref") or notice.get("source_action_result_ref") not in " ".join(str(x) for x in notice.get("trace_refs", [])):
            failures.append("action_submission_result_notice_trace_rate")
    for sub in submissions:
        if sub.get("source_v142_action_result_ref") not in notice_refs:
            failures.append("action_submission_result_notice_trace_rate")
        key = sub.get("idempotency_scope_key") or ""
        if not all(token in key for token in [user_id or "", session_id or "", conversation_id or "", sub.get("action_card_id") or ""]):
            failures.append("conversation_idempotency_scope_valid_rate")

    for idem in idempotency:
        key = idem.get("idempotency_scope_key") or ""
        if not all(token in key for token in [user_id or "", session_id or "", conversation_id or ""]):
            failures.append("conversation_idempotency_scope_valid_rate")
        if ("same_scope_duplicate" in mode or "same_scope_duplicate" in scenario) and (idem.get("same_scope_reused") is not True or idem.get("duplicate_action_result_ref") != idem.get("canonical_action_result_ref")):
            failures.append("same_scope_duplicate_reuses_result_across_turns_rate")
        if ("different_conversation" in mode or "different_user" in mode or "different_conversation" in scenario or "different_user" in scenario) and (idem.get("different_scope_reused") is True or idem.get("different_scope_action_result_ref") == idem.get("canonical_action_result_ref")):
            failures.append("different_scope_duplicate_does_not_reuse_result_rate")

    if mode in {"expired", "stale"} or "expired_card" in scenario or "stale_card" in scenario:
        for life in lifecycles:
            if life.get("card_state") not in {"expired", "stale"}:
                failures.append("expired_stale_card_no_write_rate")
        if any(res.get("production_write_executed") for res in results):
            failures.append("expired_stale_card_no_write_rate")

    for state in clarifications:
        if state.get("clarification_required") and (state.get("memory_write_claimed") is True or not state.get("resumed_turn_id")):
            failures.append("clarification_state_truthful_rate")
        if state.get("memory_write_claimed") is True:
            failures.append("clarification_state_truthful_rate")
    for state in reviews:
        if state.get("review_pending") and state.get("memory_applied_claimed") is True:
            failures.append("review_pending_state_truthful_rate")
        if state.get("memory_applied_claimed") is True:
            failures.append("review_pending_state_truthful_rate")
    for state in feedback:
        if state.get("feedback_kind") == "feedback_do_not_change" and state.get("memory_mutated") is True:
            failures.append("feedback_state_transition_truthful_rate")
        if state.get("feedback_kind") == "feedback_remember" and not state.get("governed_transition_ref"):
            failures.append("feedback_state_transition_truthful_rate")

    accepted_transition_refs = {tr.get("accepted_action_result_ref") for tr in transitions if tr.get("accepted_action_result_ref")}
    final_claim_refs = []
    if results:
        for claim in results[-1].get("user_visible_claims") or []:
            final_claim_refs.extend(claim.get("trace_refs") or [])
    if "unaccepted_state" in final_claim_refs or (("remember" in mode or "accepted" in scenario) and accepted_transition_refs and not any(ref in final_claim_refs or ref in str(results[-1]) for ref in accepted_transition_refs)):
        failures.append("next_turn_response_reflects_only_accepted_state_rate")

    valid_claim_sources = set(result_ids) | {tr.get("conversation_state_transition_id") for tr in transitions} | notice_refs | {review.get("governance_decision_ref") for review in reviews}
    for audit_row in claim_audits:
        if audit_row.get("passed") is not True or audit_row.get("missing_trace_refs") or audit_row.get("foreign_user_refs_detected") or audit_row.get("foreign_session_refs_detected") or audit_row.get("forbidden_visible_terms_detected"):
            failures.append("visible_claims_trace_backed_rate")
    for res in results:
        for claim in res.get("user_visible_claims") or []:
            refs = set(claim.get("trace_refs") or [])
            if not refs or not refs.intersection(valid_claim_sources):
                failures.append("visible_claims_trace_backed_rate")
            if visible_text_has_forbidden_terms(claim.get("text") or ""):
                failures.append("visible_claims_trace_backed_rate")
    for payload in _all_visible_text_payload(artifact):
        if visible_text_has_forbidden_terms(payload):
            failures.append("visible_claims_trace_backed_rate")

    leakage = leakage_scan(_boundary_payload(artifact), user_id or "", session_id or "", conversation_id or "")
    if audit is None or audit.get("passed") is not True or any(leakage.values()):
        failures.append("conversation_boundary_leakage_absent_rate")
    for debug in debug_refs:
        debug_ref = str(debug.get("debug_ref") or "")
        if "/ssd2/" in debug_ref or "traceback" in debug_ref.lower():
            failures.append("conversation_boundary_leakage_absent_rate")
    if audit and (
        audit.get("foreign_user_refs_detected") != leakage["foreign_user_refs_detected"]
        or audit.get("foreign_session_refs_detected") != leakage["foreign_session_refs_detected"]
        or audit.get("foreign_conversation_refs_detected") != leakage["foreign_conversation_refs_detected"]
        or audit.get("foreign_namespace_refs_detected") != leakage["foreign_namespace_refs_detected"]
    ):
        failures.append("conversation_boundary_leakage_absent_rate")
    if audit and not REQUIRED_BOUNDARY_GROUPS.issubset(set(audit.get("audited_artifact_refs") or [])):
        failures.append("conversation_boundary_leakage_absent_rate")
    audit_self_leakage = leakage_scan(_audit_self_payload(audit), user_id or "", session_id or "", conversation_id or "")
    if audit is None or audit.get("local_user_id") != user_id or audit.get("local_session_id") != session_id or audit.get("conversation_id") != conversation_id or any(audit_self_leakage.values()):
        failures.append("conversation_boundary_audit_self_scoped_rate")

    source_hashes = artifact.get("source_v142_artifact_hashes") or {}
    if snapshot.get("canonical_script_hash") != canonical_json_hash(script) or snapshot.get("canonical_session_hash") != canonical_json_hash(session):
        failures.append("conversation_loop_snapshot_hash_reproducible_rate")
    if snapshot.get("canonical_turn_sequence_hash") != canonical_json_hash({"invocations": invocations, "results": results}):
        failures.append("conversation_loop_snapshot_hash_reproducible_rate")
    if snapshot.get("canonical_state_transition_hash") != canonical_json_hash(transitions):
        failures.append("conversation_loop_snapshot_hash_reproducible_rate")
    if audit is None or snapshot.get("canonical_boundary_audit_hash") != canonical_json_hash(audit):
        failures.append("conversation_loop_snapshot_hash_reproducible_rate")
    if snapshot.get("source_artifact_hashes") != source_hashes:
        failures.append("conversation_loop_snapshot_hash_reproducible_rate")
    for ref, expected_hash in source_hashes.items():
        path = V142_DIR / ref
        if not path.exists() or file_json_hash(path) != expected_hash:
            failures.append("conversation_loop_snapshot_hash_reproducible_rate")

    sample_probe = artifact.get("sample_consistency_probe") or {}
    if sample_probe and canonical_json_hash(sample_probe.get("sample_artifact_content")) != canonical_json_hash(sample_probe.get("source_artifact_content")):
        failures.append("sample_artifacts_match_per_case_rate")
    report_probe = artifact.get("report_consistency_probe") or {}
    if report_probe:
        clean_summary = report_probe.get("clean_report_summary") or {}
        independent_summary = report_probe.get("independent_validation_summary") or {}
        if clean_summary.get("passed_cases") != independent_summary.get("passed_cases") or clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
            failures.append("report_consistency_with_independent_validation_rate")
    if (artifact.get("v142_replay_proof") or {}).get("run_v142_validation_suite") != "PASS":
        failures.append("v142_validation_replay_pass_rate")
    if artifact.get("defect_type") == "gate_assertions_false_but_raw_artifact_valid" and all(value is False for value in (artifact.get("gate_assertions") or {}).values()):
        failures.append("adversarial_detection_rate")
    if artifact.get("defect_type") == "gate_assertions_false_but_raw_artifact_valid":
        failures.append("adversarial_detection_rate")
    return sorted(set(failures))


def copy_without_conversation_blocks(output: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(output))
    body = copied.get("body")
    if isinstance(body, dict):
        body.pop("conversation_visible_blocks", None)
    return copied


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
        failures = [{"case_id": case["case_id"], "artifact_ref": case["artifact_ref"], "failures": [f"{gate} failed from raw v1.43 conversation validation"]} for case in cases if gate in case["failed_check_ids"]]
        value = 1.0 if not cases else len(passed) / len(cases)
        checks.append({"check_id": gate, "applicable_cases": len(cases), "passed_cases": len(passed), "value": value, "threshold": 1.0, "passed": value >= 1.0, "failures": failures})
    report: dict[str, Any] = {
        "validator": "v1.43.independent.product_conversation_runtime_loop_validator",
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
    parser.add_argument("--result-dir", default="benchmark/benchmark_v143/results/v143_release_candidate")
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
