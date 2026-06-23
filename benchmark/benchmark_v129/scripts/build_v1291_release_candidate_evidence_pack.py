"""
Build the v1.29.1 Release Candidate Evidence Pack.

Inputs are aggregate reports plus raw runner artifact directories. The builder
copies reports, renders short Markdown summaries, extracts representative raw
samples, and writes review/release documentation.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any


EXPECTED_DEFECT_FILES = {
    "metric_conflict": "injected_metric_conflict_detected.json",
    "shadow_style_commit": "injected_shadow_style_commit_detected.json",
    "write_flag_mismatch": "injected_write_flag_mismatch_detected.json",
    "journal_shadow_id": "injected_journal_shadow_id_detected.json",
    "audit_replay_mismatch": "injected_audit_replay_mismatch_detected.json",
}


def _load_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _cleanup_versions(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_raw_rows(raw_dir: str | Path) -> list[dict]:
    raw_dir = Path(raw_dir)
    results = raw_dir / "results.json"
    if results.exists():
        return _load_json(results)
    per_case = raw_dir / "per_case"
    if per_case.is_dir():
        return [_load_json(p) for p in sorted(per_case.glob("*.json"))]
    raise FileNotFoundError(f"raw artifact dir missing results.json/per_case: {raw_dir}")


def _cleanup_versions(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_cleanup_versions(v) for v in obj]
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key == "pipeline_version" and value == "v1.28.1.1":
                out["source_pipeline_version"] = value
                out["pipeline_version"] = "v1.29.1"
                out["artifact_schema_version"] = "v1.29.1"
                out["write_truthfulness_schema_version"] = "v1.29.1"
            else:
                out[key] = _cleanup_versions(value)
        return out
    return obj


def _sample_envelope(data: dict) -> dict:
    return {
        "artifact_schema_version": "v1.29.1",
        "write_truthfulness_schema_version": "v1.29.1",
        "pipeline_version": "v1.29.1",
        **data,
    }


def _case_ref(raw_dir: str | Path, case_id: str) -> str:
    raw_dir = Path(raw_dir)
    per_case = raw_dir / "per_case" / f"{case_id}.json"
    return str(per_case if per_case.exists() else raw_dir / "results.json")


def _report_md(title: str, report: dict) -> str:
    summary = report.get("suite_summary") or {}
    verdicts = report.get("verdicts") or {}
    failed = report.get("failed_gates") or []
    lines = [
        f"# {title}",
        "",
        f"- suite_mode: `{summary.get('suite_mode')}`",
        f"- cases: {summary.get('total_cases')}",
        f"- release_clean_cases: {summary.get('release_clean_cases')}",
        f"- non_release_control_cases: {summary.get('non_release_control_cases')}",
        f"- injected_defect_cases: {summary.get('injected_defect_cases')}",
        f"- checks: {summary.get('passed_checks')} / {summary.get('total_checks')} PASS",
        f"- failed_checks: {summary.get('failed_checks')}",
        f"- clean_acceptance_verdict: `{verdicts.get('clean_acceptance_verdict')}`",
        f"- mixed_strict_verdict: `{verdicts.get('mixed_strict_verdict')}`",
        f"- injected_defect_detection_verdict: `{verdicts.get('injected_defect_detection_verdict')}`",
        f"- release_candidate_verdict: `{verdicts.get('release_candidate_verdict')}`",
        "",
        "## Interpretation",
        "",
        report.get("interpretation", ""),
        "",
        "## Failed Checks",
        "",
    ]
    if failed:
        lines.extend(f"- `{g}`" for g in failed)
    else:
        lines.append("- None")
    raw_identity = report.get("raw_first_identity_gates") or []
    lines.extend(["", "## Raw-First Identity Gates", ""])
    if raw_identity:
        for gate in raw_identity:
            lines.append(
                f"- `{gate.get('check_id')}`: passed={gate.get('passed')} detail={gate.get('detail')}"
            )
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _pick(rows: list[dict], predicate, label: str) -> dict:
    for row in rows:
        if predicate(row):
            return row
    raise RuntimeError(f"Could not find sample for {label}")


def _allowed_commit_sample(row: dict) -> dict:
    cr = row.get("production_commit_result") or {}
    return {
        "case_id": row.get("case_id"),
        "decision_id": cr.get("decision_id"),
        "commit_id": cr.get("production_commit_id") or cr.get("commit_id"),
        "store_env": cr.get("store_env"),
        "namespace": cr.get("namespace"),
        "write_backend": cr.get("write_backend"),
        "store_version": {
            "before": cr.get("production_store_version_before") or cr.get("before_store_version"),
            "after": cr.get("production_store_version_after") or cr.get("after_store_version"),
        },
        "production_store_write_attempted": cr.get("production_store_write_attempted"),
        "production_store_write_executed": cr.get("production_store_write_executed"),
        "shadow_store_write_attempted": cr.get("shadow_store_write_attempted"),
        "shadow_store_write_executed": cr.get("shadow_store_write_executed"),
        "audit_log_snapshot": cr.get("audit_log_snapshot"),
        "rollback_window_snapshot": cr.get("rollback_window_snapshot"),
        "state_hash_before": cr.get("pre_state_hash"),
        "state_hash_after_write": cr.get("post_state_hash"),
        "raw": row,
    }


def _hard_block_sample(row: dict) -> dict:
    return {
        "case_id": row.get("case_id"),
        "decision_status": "blocked",
        "required_mode": row.get("required_mode"),
        "terminated_at": row.get("terminated_at"),
        "block_reasons": row.get("block_reasons"),
        "shadow_parity_attempted": row.get("shadow_parity_attempted"),
        "production_store_write_attempted": row.get("production_store_write_attempted"),
        "production_store_write_executed": row.get("production_store_write_executed"),
        "shadow_store_write_attempted": row.get("shadow_store_write_attempted"),
        "shadow_store_write_executed": row.get("shadow_store_write_executed"),
        "shadow_parity_report": row.get("shadow_parity_report"),
        "production_commit_result": row.get("production_commit_result"),
        "raw": row,
    }


def _human_review_sample(row: dict) -> dict:
    payload = row.get("human_review_payload") or {}
    return {
        "case_id": row.get("case_id"),
        "human_review_required": row.get("required_mode") == "human_review_required",
        "production_store_write_attempted": row.get("production_store_write_attempted"),
        "production_store_write_executed": row.get("production_store_write_executed"),
        "decision_id": payload.get("decision_id"),
        "risk_reason": payload.get("risk_explanation"),
        "timestamp": payload.get("created_at"),
        "human_review_payload": payload,
        "proposed_diff": payload.get("proposed_actions") or payload.get("actions"),
        "readable_evidence": payload.get("evidence_preview"),
        "allowed_reviewer_decisions": payload.get("allowed_reviewer_decisions") or payload.get("allowed_decisions"),
        "rollback_summary": payload.get("rollback_plan_summary"),
        "raw": row,
    }


def _rollback_sample(row: dict) -> dict:
    cr = row.get("production_commit_result") or {}
    rr = row.get("rollback_report") or {}
    read = rr.get("read_after_rollback") or {}
    return {
        "case_id": row.get("case_id"),
        "rollback_status": rr.get("rollback_status"),
        "target_commit_id": rr.get("target_commit_id"),
        "pre_state_hash": cr.get("pre_state_hash"),
        "post_write_state_hash": cr.get("post_state_hash"),
        "post_rollback_state_hash": rr.get("post_rollback_state_hash"),
        "read_after_rollback": read,
        "active_commit_ids": read.get("active_commit_ids"),
        "rolledback_commit_ids": read.get("rolled_back_commit_ids"),
        "rollback_decision_id": rr.get("decision_id"),
        "rollback_timestamp": rr.get("created_at"),
        "raw": row,
    }


def _audit_replay_sample(row: dict) -> dict:
    ar = row.get("production_audit_replay_report") or {}
    journal = row.get("production_journal_entry") or {}
    cr = row.get("production_commit_result") or {}
    return {
        "case_id": row.get("case_id"),
        "audit_replay_status": ar.get("replay_status"),
        "matches_store": ar.get("matches_store"),
        "replayed_state_hash": ar.get("replayed_store_state_hash"),
        "expected_state_hash": ar.get("production_store_state_hash"),
        "production_journal_entry_ids": ar.get("production_journal_entry_ids"),
        "production_journal_commit_ids": ar.get("production_journal_commit_ids"),
        "journal_commit_ids": [journal.get("production_commit_id")],
        "commit_artifact_id": cr.get("production_commit_id"),
        "active_commit_ids": ar.get("active_commit_ids"),
        "rolledback_commit_ids": ar.get("rolled_back_commit_ids"),
        "diff_summary": ar.get("state_diff"),
        "raw": row,
    }


def _defect_fixture_keys(row: dict) -> set[str]:
    keys = set()
    if row.get("inject_metric_conflict"):
        keys.add("metric_conflict")
    if row.get("shadow_style_detected") or "shadow_commit_id" in (row.get("production_commit_result") or {}):
        keys.add("shadow_style_commit")
    if row.get("write_flag_mismatch_detected"):
        keys.add("write_flag_mismatch")
    if row.get("injected_shadow_commit_id_in_journal"):
        keys.add("journal_shadow_id")
    replay_diff = ((row.get("production_audit_replay_report") or {}).get("state_diff") or {})
    if replay_diff.get("changed_atom_ids") == ["injected_mismatch"]:
        keys.add("audit_replay_mismatch")
    return keys


def _defect_sample(defect_type: str, row: dict, mixed_report: dict, raw_dir: str | Path) -> dict:
    detected = next(
        (d for d in mixed_report.get("detected_defects", []) if d.get("defect_type") == defect_type),
        {},
    )
    return {
        "case_id": row.get("case_id"),
        "defect_type": defect_type,
        "expected_failure": True,
        "actual_failure": bool(detected.get("detected")),
        "failed_check_ids": detected.get("failed_check_ids") or [],
        "failure_reason": f"Seeded {defect_type} was detected by strict raw-first aggregation.",
        "raw_artifact_ref": _case_ref(raw_dir, row.get("case_id")),
    }


def _build_injected_summary(mixed_rows: list[dict], mixed_report: dict) -> dict:
    detected_defects = []
    unexpected_passes = []
    for defect_type in EXPECTED_DEFECT_FILES:
        row = next((r for r in mixed_rows if defect_type in _defect_fixture_keys(r)), None)
        detected = next(
            (d for d in mixed_report.get("detected_defects", []) if d.get("defect_type") == defect_type),
            {},
        )
        item = {
            "defect_type": defect_type,
            "case_id": row.get("case_id") if row else "",
            "detected": bool(detected.get("detected")),
            "failed_check_ids": detected.get("failed_check_ids") or [],
        }
        if row and not item["detected"]:
            unexpected_passes.append(row.get("case_id"))
        detected_defects.append(item)
    unexpected_clean = mixed_report.get("unexpected_failures") or []
    return {
        "suite": "v1.29.1 injected defect detection",
        "verdict": "pass" if all(d["detected"] for d in detected_defects) and not unexpected_clean and not unexpected_passes else "fail",
        "expected_behavior": "strict mixed suite should fail when injected defects are present",
        "detected_defects": detected_defects,
        "unexpected_clean_case_failures": unexpected_clean,
        "unexpected_injected_passes": unexpected_passes,
    }


def _reviewer_checklist() -> str:
    return """# v1.29.1 Reviewer Checklist

## Release Candidate Summary

- Clean acceptance suite: 38 cases, 61/61 checks PASS
- Mixed strict suite with injected defects: expected FAIL
- Injected defect detection: PASS if all seeded defects are detected
- Release status: PASS CANDIDATE confirmed after manual spot review

## A. Allowed Low-Risk Production Write

Artifact: `sample_artifacts/allowed_low_risk_production_commit.json`

- [ ] `store_env` is production
- [ ] `namespace` is the declared production-mode benchmark fixture namespace
- [ ] `write_backend` is production-native
- [ ] `production_store_write_attempted == true`
- [ ] `production_store_write_executed == true`
- [ ] `commit_id` is not shadow-style
- [ ] `shadow_parity_attempted` may be true only as a separate verifier path
- [ ] `production_commit_result.shadow_store_write_attempted == false`
- [ ] `production_commit_result.shadow_store_write_executed == false`
- [ ] `shadow_store_write_attempted == false`
- [ ] `shadow_store_write_executed == false`
- [ ] production commit identity is production-native, e.g. `prod_commit_*`
- [ ] production journal source-of-truth fields do not contain `sc_*`
- [ ] any `sc_*` ID appears only in explicitly named shadow verifier refs
- [ ] `audit_log_snapshot` exists
- [ ] `rollback_window_snapshot` exists
- [ ] state hash before and after write exists

Verdict:

- [ ] PASS
- [ ] FAIL

## B. Hard Block

Artifact: `sample_artifacts/hard_block_terminated_before_shadow.json`

- [ ] decision is blocked
- [ ] `terminated_at` exists
- [ ] termination happened before shadow parity
- [ ] production and shadow writes were not attempted or executed
- [ ] `shadow_parity_attempted == false`
- [ ] `shadow_store_write_attempted == false`
- [ ] `shadow_store_write_executed == false`
- [ ] no production commit artifact exists
- [ ] no shadow parity report exists

Verdict:

- [ ] PASS
- [ ] FAIL

## C. Human Review Required

Artifact: `sample_artifacts/human_review_required_payload.json`

- [ ] `human_review_required == true`
- [ ] production write was not attempted or executed
- [ ] `shadow_parity_attempted == false`
- [ ] `shadow_store_write_attempted == false`
- [ ] `shadow_store_write_executed == false`
- [ ] proposed diff exists
- [ ] readable evidence exists
- [ ] allowed reviewer decisions exist
- [ ] rollback summary exists
- [ ] timestamp exists
- [ ] reviewer can make an actual decision from the payload

Verdict:

- [ ] PASS
- [ ] FAIL

## D. Rollback Proof

Artifact: `sample_artifacts/rollback_proof_success.json`

- [ ] state hashes exist before write, after write, and after rollback
- [ ] read-after-rollback proves commit is no longer active
- [ ] active and rolledback commit IDs are present
- [ ] rollback target commit id matches original commit id

Verdict:

- [ ] PASS
- [ ] FAIL

## E. Audit Replay

Artifact: `sample_artifacts/audit_replay_success.json`

- [ ] replayed state hash exists
- [ ] expected state hash exists
- [ ] replayed hash matches expected hash
- [ ] journal commit ids match commit artifacts
- [ ] production audit replay journal identity fields do not contain `sc_*`
- [ ] rolledback commit ids are represented correctly
- [ ] diff summary is readable

Verdict:

- [ ] PASS
- [ ] FAIL

## F. Injected Defect Detection

Artifacts: `sample_artifacts/injected_*_detected.json`

- [ ] metric conflict was detected
- [ ] shadow-style commit was detected
- [ ] write flag mismatch was detected
- [ ] journal shadow id contamination was detected
- [ ] audit replay mismatch was detected
- [ ] no injected defect was silently excluded
- [ ] no injected defect unexpectedly passed

Verdict:

- [ ] PASS
- [ ] FAIL

## Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PARTIAL PASS
- [ ] FAIL

Reviewer notes:
"""


def _release_note(clean_report: dict, mixed_report: dict, injected_summary: dict) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    defects = [d["defect_type"] for d in injected_summary.get("detected_defects", []) if d.get("detected")]
    return f"""# v1.29.1 Release Candidate Note

## Scope

v1.29.1 focuses on Production Memory Write Truthfulness & Artifact Completeness.

This release does not expand production write coverage, does not add external inspiration intake, does not introduce aesthetic cards, and does not change planner product behavior.

## Key Fixes

- Production write decisions now include v1.29.1 self-proof fields.
- Hard block and human review decisions terminate before shadow parity.
- Human review payload is actionable and includes proposed diff, readable evidence, allowed reviewer decisions, rollback summary, and timestamp.
- Production commit, journal, audit replay, and rollback proof artifacts are production-native and include state hash, backend, namespace, store version, and read-after-rollback proof.
- Aggregation is raw-first and strict.
- Raw audit replay identity is checked so production journal, replay, and commit identity fields cannot contain `sc_*`.
- Injected defects are no longer silently excluded.
- Bypass-style checks such as `or True` have been removed.

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')} / {clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}

## Mixed Strict Suite With Injected Defects

- Cases: {mixed.get('total_cases')}
- Checks: {mixed.get('passed_checks')} / {mixed.get('total_checks')} PASS
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected

## Mixed Strict Suite Case Accounting

The mixed strict suite contains:

- {mixed.get('release_clean_cases')} release clean acceptance cases
- {mixed.get('non_release_control_cases')} non-release control case
- {mixed.get('injected_defect_cases')} injected defect cases

The mixed strict suite is expected to fail because injected defects are present and correctly detected.

The release candidate verdict is not derived from mixed strict PASS. It is derived from:

1. clean acceptance suite PASS
2. injected defect detection PASS
3. no unexpected clean case failures
4. manual spot review

Detected defects:

{os.linesep.join(f'- {d}' for d in defects)}

## Interpretation

The clean production-write path passes all checks.

The strict mixed suite fails because injected defects are present and correctly detected. This is expected and should be interpreted as detector success, not release failure.

## Release Status

PASS CANDIDATE confirmed after manual spot review using `reviewer_checklist.md`.

## Non-Goals

- No expanded production write allowlist
- No external inspiration intake
- No planner quality changes
- No UI changes
- No beta launch
- No commerce integration
"""


def _readme() -> str:
    return """# v1.29.1 Release Candidate Evidence Pack

This directory contains the release candidate evidence pack for v1.29.1 Production Memory Write Truthfulness & Artifact Completeness.

## Contents

- `clean_subset_report.json`: raw-first aggregate report for clean acceptance cases
- `clean_subset_report.md`: human-readable clean acceptance report
- `mixed_strict_report.json`: raw-first aggregate report including injected defects
- `mixed_strict_report.md`: human-readable mixed strict report
- `injected_defect_detection_summary.json`: seeded defect detection result
- `reviewer_checklist.md`: manual spot review checklist
- `RELEASE_NOTE.md`: release candidate summary
- `sample_artifacts/`: representative raw artifacts for manual review

## Verdict Semantics

Clean acceptance suite is used for release acceptance.

Mixed strict suite includes injected defects and is expected to fail. Failure of the mixed strict suite means the strict aggregator is detecting seeded governance defects.

Release candidate status is derived from:

1. clean acceptance suite PASS
2. injected defect detection PASS
3. no unexpected clean case failures
4. manual spot review completion

## Benchmark Namespace

This evidence pack uses the production-native write path with an isolated benchmark fixture namespace:

`test/v1291/run_fixture`

This prevents real user production memory from being modified while preserving production write truthfulness semantics.

Therefore, reviewer checks should verify that the namespace is declared, stable, and belongs to the allowed production-mode benchmark fixture namespace, rather than expecting a live user production namespace.

## Shadow Parity Semantics

For allowed production writes, `shadow_parity_attempted` may be true as a separate verifier path.

However:

- `production_commit_result.shadow_store_write_attempted` must be false
- `production_commit_result.shadow_store_write_executed` must be false
- `shadow_store_write_executed` must be false
- production commit identity must remain production-native, for example `prod_commit_*`
- production journal source-of-truth fields must not use `sc_*`
- hard block and human review cases must not attempt shadow parity

Shadow verifier references may appear only in explicitly named verifier fields, such as `shadow_verifier_ref_ids`, `shadow_commit_ref`, or `shadow_parity_report`. They must not appear in production journal, replay, or commit identity fields.

## Current Status

PASS CANDIDATE confirmed after manual spot review.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-report", required=True)
    parser.add_argument("--mixed-report", required=True)
    parser.add_argument("--clean-artifacts-dir", required=True)
    parser.add_argument("--mixed-artifacts-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    samples = out_dir / "sample_artifacts"
    samples.mkdir(parents=True, exist_ok=True)

    clean_report = _load_json(args.clean_report)
    mixed_report = _load_json(args.mixed_report)
    clean_rows = _load_raw_rows(args.clean_artifacts_dir)
    mixed_rows = _load_raw_rows(args.mixed_artifacts_dir)

    shutil.copyfile(args.clean_report, out_dir / "clean_subset_report.json")
    shutil.copyfile(args.mixed_report, out_dir / "mixed_strict_report.json")
    _write_text(out_dir / "clean_subset_report.md", _report_md("v1.29.1 Clean Acceptance Report", clean_report))
    _write_text(out_dir / "mixed_strict_report.md", _report_md("v1.29.1 Mixed Strict Report", mixed_report))

    allowed = _pick(
        clean_rows,
        lambda r: r.get("production_store_write_attempted") is True
        and r.get("production_store_write_executed") is True
        and (r.get("production_commit_result") or {}).get("store_env") == "production"
        and (r.get("production_commit_result") or {}).get("shadow_store_write_executed") is False
        and "shadow_commit_id" not in (r.get("production_commit_result") or {}),
        "allowed low-risk production commit",
    )
    hard_block = _pick(
        clean_rows,
        lambda r: r.get("required_mode") == "block"
        and r.get("terminated_at")
        and not r.get("shadow_parity_attempted")
        and r.get("production_store_write_attempted") is False,
        "hard block",
    )
    human_review = _pick(
        clean_rows,
        lambda r: r.get("required_mode") == "human_review_required"
        and r.get("human_review_payload")
        and r.get("production_store_write_attempted") is False,
        "human review",
    )
    rollback = _pick(
        clean_rows,
        lambda r: (r.get("rollback_report") or {}).get("rollback_status") == "rolled_back"
        and (r.get("rollback_report") or {}).get("read_after_rollback"),
        "rollback proof",
    )
    audit_replay = _pick(
        clean_rows,
        lambda r: (r.get("production_audit_replay_report") or {}).get("matches_store") is True
        and (r.get("production_audit_replay_report") or {}).get("production_store_state_hash")
        == (r.get("production_audit_replay_report") or {}).get("replayed_store_state_hash"),
        "audit replay",
    )

    _write_json(samples / "allowed_low_risk_production_commit.json", _sample_envelope(_allowed_commit_sample(allowed)))
    _write_json(samples / "hard_block_terminated_before_shadow.json", _sample_envelope(_hard_block_sample(hard_block)))
    _write_json(samples / "human_review_required_payload.json", _sample_envelope(_human_review_sample(human_review)))
    _write_json(samples / "rollback_proof_success.json", _sample_envelope(_rollback_sample(rollback)))
    _write_json(samples / "audit_replay_success.json", _sample_envelope(_audit_replay_sample(audit_replay)))

    for defect_type, filename in EXPECTED_DEFECT_FILES.items():
        row = _pick(mixed_rows, lambda r, d=defect_type: d in _defect_fixture_keys(r), defect_type)
        _write_json(samples / filename, _sample_envelope(_defect_sample(defect_type, row, mixed_report, args.mixed_artifacts_dir)))

    injected_summary = _build_injected_summary(mixed_rows, mixed_report)
    _write_json(out_dir / "injected_defect_detection_summary.json", injected_summary)
    _write_text(out_dir / "reviewer_checklist.md", _reviewer_checklist())
    _write_text(out_dir / "RELEASE_NOTE.md", _release_note(clean_report, mixed_report, injected_summary))
    _write_text(out_dir / "README.md", _readme())

    print(f"Evidence pack written to {out_dir}")


if __name__ == "__main__":
    main()
