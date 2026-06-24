"""Report consistency checks used by v1.35 release evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.common.raw_artifact_validation import canonical_json_hash, file_json_hash, read_json


REQUIRED_REPORTS = [
    "clean_report.json",
    "mixed_strict_report.json",
    "independent_validation_report.json",
    "adversarial_validation_report.json",
    "report_consistency_report.json",
    "sample_consistency_report.json",
    "injected_defect_detection_summary.json",
]


def check_sample_consistency(result_dir: Path) -> dict[str, Any]:
    manifest = read_json(result_dir / "REVIEW_MANIFEST.json")
    samples = manifest.get("sample_artifacts", [])
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for sample in samples:
        sample_path = result_dir / sample["artifact_ref"]
        source_path = result_dir / sample["source_artifact_ref"]
        row = {
            "artifact_ref": sample["artifact_ref"],
            "source_artifact_ref": sample["source_artifact_ref"],
            "case_id": sample["case_id"],
            "exists": sample_path.exists() and source_path.exists(),
        }
        if not row["exists"]:
            row["passed"] = False
            failures.append({**row, "reason": "sample or source artifact missing"})
        else:
            sample_hash = file_json_hash(sample_path)
            source_hash = file_json_hash(source_path)
            row.update(
                {
                    "sample_hash": sample_hash,
                    "source_hash": source_hash,
                    "manifest_hash": sample.get("canonical_sha256"),
                    "passed": sample_hash == source_hash == sample.get("canonical_sha256"),
                }
            )
            if not row["passed"]:
                failures.append({**row, "reason": "sample artifact differs from per_case source"})
        rows.append(row)
    return {
        "validator": "benchmark.common.sample_consistency",
        "total_samples": len(rows),
        "passed_samples": sum(1 for row in rows if row.get("passed")),
        "failed_samples": sum(1 for row in rows if not row.get("passed")),
        "passed": not failures,
        "failures": failures,
        "samples": rows,
    }


def check_report_consistency(result_dir: Path, required_gates: list[str]) -> dict[str, Any]:
    manifest = read_json(result_dir / "REVIEW_MANIFEST.json")
    clean = read_json(result_dir / "clean_report.json")
    independent = read_json(result_dir / "independent_validation_report.json")
    adversarial = read_json(result_dir / "adversarial_validation_report.json")
    injected = read_json(result_dir / "injected_defect_detection_summary.json")
    sample = read_json(result_dir / "sample_consistency_report.json")

    failures: list[str] = []
    required_reports = manifest.get("required_reports", [])
    for report in REQUIRED_REPORTS:
        if report not in required_reports:
            failures.append(f"manifest missing required report {report}")
        if not (result_dir / report).exists():
            failures.append(f"required report file missing {report}")

    if manifest.get("builder_script") == manifest.get("validator_script"):
        failures.append("builder and validator scripts are identical")
    if "benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py" not in manifest.get("validator_commands", []):
        failures.append("manifest omits v1.35 validator command")

    clean_summary = clean.get("suite_summary", {})
    independent_summary = independent.get("suite_summary", {})
    if clean_summary.get("passed_cases") != independent_summary.get("passed_cases"):
        failures.append("clean_report passed_cases differs from independent validation")
    if clean_summary.get("failed_cases") != independent_summary.get("failed_cases"):
        failures.append("clean_report failed_cases differs from independent validation")
    if independent_summary.get("failed_cases") != 0:
        failures.append("independent validation has failed clean cases")

    independent_gates = {check.get("check_id"): check for check in independent.get("checks", [])}
    for gate in required_gates:
        if gate not in independent_gates:
            failures.append(f"independent validation missing gate {gate}")
        elif independent_gates[gate].get("passed") is not True:
            failures.append(f"independent validation gate failed {gate}")

    adversarial_summary = adversarial.get("suite_summary", {})
    if adversarial_summary.get("failed_cases", 0) <= 0:
        failures.append("adversarial validation did not fail injected cases")
    if adversarial_summary.get("passed_cases") != 0:
        failures.append("at least one adversarial case unexpectedly passed")
    if injected.get("detected_defects") != injected.get("seeded_defects"):
        failures.append("injected defect detection did not detect every seeded defect")
    if injected.get("verdict") != "pass":
        failures.append("injected defect detection verdict is not pass")
    if sample.get("passed") is not True:
        failures.append("sample consistency report failed")

    return {
        "validator": "benchmark.common.report_consistency",
        "manifest_hash": canonical_json_hash(manifest),
        "required_reports": REQUIRED_REPORTS,
        "checked_gates": required_gates,
        "passed": not failures,
        "failures": failures,
    }

