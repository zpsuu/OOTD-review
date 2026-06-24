"""Independent raw-artifact validator for v1.35 evidence packs."""
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
from benchmark.common.raw_artifact_validation import json_files, now_iso, read_json, write_json
from benchmark.common.report_consistency import check_report_consistency, check_sample_consistency


GATES = [
    "independent_validator_required_rate",
    "independent_validator_report_present_rate",
    "clean_report_matches_independent_validation_rate",
    "raw_case_failure_overrides_aggregate_pass_rate",
    "report_only_pass_prevented_rate",
    "builder_validator_separation_rate",
    "adversarial_mutation_suite_present_rate",
    "adversarial_mutation_detection_rate",
    "sample_artifacts_match_per_case_rate",
    "sample_artifact_staleness_detected_rate",
    "manifest_declares_validator_reports_rate",
    "validation_runner_reproducible_rate",
    "validator_unit_tests_pass_rate",
    "v134_replay_independent_validation_pass_rate",
    "v134_replay_adversarial_detection_pass_rate",
]


def _artifact_dir(result_dir: Path, subset: str) -> Path:
    if subset == "clean":
        return result_dir / "per_case" / "clean"
    if subset == "adversarial":
        return result_dir / "per_case" / "adversarial"
    if subset == "mixed_strict":
        return result_dir / "per_case" / "mixed_strict"
    raise ValueError(f"unknown subset {subset}")


def _validate_case(path: Path, subset: str, base_dir: Path) -> dict[str, Any]:
    artifact = read_json(path)
    assertions = artifact.get("gate_assertions") or {}
    failed: list[str] = []
    for gate in GATES:
        if assertions.get(gate) is not True:
            failed.append(gate)
    if subset == "clean":
        required_refs = {"gate_assertions", "runtime_path_evidence", "expected_validator_behavior"}
        proof_refs = set((artifact.get("scenario_preconditions") or {}).get("proof_refs") or [])
        if not required_refs.issubset(proof_refs):
            failed.append("raw_case_failure_overrides_aggregate_pass_rate")
        if (artifact.get("runtime_path_evidence") or {}).get("builder_and_validator_are_separate") is not True:
            failed.append("builder_validator_separation_rate")
    return {
        "case_id": artifact.get("case_id") or path.stem,
        "artifact_ref": str(path.relative_to(base_dir)),
        "passed": not failed,
        "failed_check_ids": sorted(set(failed)),
        "expected_failed_check_ids": artifact.get("expected_failed_check_ids", []),
        "defect_type": artifact.get("defect_type"),
    }


def validate_directory(result_dir: Path, subset: str) -> dict[str, Any]:
    paths = json_files(_artifact_dir(result_dir, subset))
    cases = [_validate_case(path, subset, result_dir) for path in paths]
    checks: list[dict[str, Any]] = []
    for gate in GATES:
        applicable = cases
        passed = [case for case in applicable if gate not in case["failed_check_ids"]]
        failures = [
            {
                "case_id": case["case_id"],
                "artifact_ref": case["artifact_ref"],
                "failures": [f"{gate} is false or missing in raw gate_assertions"],
            }
            for case in applicable
            if gate in case["failed_check_ids"]
        ]
        value = 1.0 if not applicable else len(passed) / len(applicable)
        checks.append(
            {
                "check_id": gate,
                "applicable_cases": len(applicable),
                "passed_cases": len(passed),
                "value": value,
                "threshold": 1.0,
                "passed": value >= 1.0,
                "failures": failures,
            }
        )
    report = {
        "validator": "v1.35.independent.runtime_path_validator",
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
    write_json(
        result_dir / "report_consistency_report.json",
        {"validator": "benchmark.common.report_consistency", "generated_at": now_iso(), "passed": False, "status": "generating"},
    )
    report = check_report_consistency(result_dir, GATES)
    write_json(result_dir / "report_consistency_report.json", {**report, "generated_at": now_iso()})
    return sample, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="benchmark/benchmark_v135/results/v135_release_candidate")
    parser.add_argument("--subset", choices=["clean", "adversarial", "mixed_strict"], default="clean")
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument("--write-consistency", action="store_true", help="Write sample and report consistency reports")
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    report = validate_directory(result_dir, args.subset)
    if args.output:
        write_json(Path(args.output), report)
    if args.write_consistency:
        write_consistency_reports(result_dir)
    print(json.dumps(report["suite_summary"], ensure_ascii=False, indent=2))
    if args.subset == "clean" and report["suite_summary"]["failed_cases"]:
        raise SystemExit(1)
    if args.subset in {"adversarial", "mixed_strict"} and report["suite_summary"]["passed_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
