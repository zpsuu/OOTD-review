"""
package_manifest_validator.py

Physical package validator: reads MANIFEST.json from package_root and verifies
that all declared files are present on disk and their sha256 hashes match.

Used by the v1.29.1.2 aggregator to enforce physical package traceability.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any


# Mandatory file categories and their representative paths (relative to pkg_root)
_MANDATORY_FILE_PATTERNS = {
    "protocol": [
        "OOTD_vNext_v1_29_1_2_Rollback_Self_Proof_Review_Package_Reproducibility_Protocol.md",
    ],
    "cases": [
        os.path.join("ootd_v12912", "v12912_rollback_self_proof_review_package_cases.jsonl"),
        "v12912_rollback_self_proof_review_package_cases.jsonl",
    ],
    "thresholds": [
        os.path.join("ootd_v12912", "acceptance_thresholds_v12912.json"),
        "acceptance_thresholds_v12912.json",
    ],
    "report_template": [
        os.path.join("ootd_v12912", "report_template_v12912.json"),
        "report_template_v12912.json",
    ],
    "raw_results": ["v12912_results.json"],
    "report": ["v12912_report.json"],
    "runner_source": [
        os.path.join("source_diff", "run_v12912_rollback_self_proof_review_package.py"),
    ],
    "aggregator_source": [
        os.path.join("source_diff", "aggregate_v12912_rollback_self_proof_review_package_report.py"),
    ],
    "source_diff_dir": ["source_diff"],
    "environment": [
        os.path.join("environment", "environment.json"),
    ],
    "per_case": [
        os.path.join("artifacts", "per_case"),
    ],
    "samples": [
        os.path.join("artifacts", "samples"),
    ],
}


def _sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def _file_present(pkg_root: str, candidates: list[str]) -> tuple[bool, str | None]:
    """Check if any candidate path exists; return (found, found_path)."""
    for rel in candidates:
        abs_path = os.path.join(pkg_root, rel)
        if os.path.exists(abs_path):
            return True, abs_path
    return False, None


def validate_package(package_root: str) -> dict:
    """
    Physically validate the package at package_root.

    Returns a dict with:
      status: "pass" | "fail"
      manifest_present: bool
      manifest_schema_valid: bool
      sha256_complete: bool        — all files in manifest have a sha256 entry
      sha256_verified: bool        — all sha256 entries match actual files
      sha_mismatches: list[str]    — file paths with mismatched sha256
      missing_mandatory: list[str] — mandatory categories with no file present
      missing_files: list[str]     — individual file paths that are missing
      uses_result_row_manifest: bool — True if validation was based on result row (bad)
      details: dict                 — per-category presence check
    """
    result: dict[str, Any] = {
        "status": "pass",
        "manifest_present": False,
        "manifest_schema_valid": False,
        "sha256_complete": False,
        "sha256_verified": False,
        "sha_mismatches": [],
        "missing_mandatory": [],
        "missing_files": [],
        "uses_result_row_manifest": False,
        "details": {},
    }

    manifest_path = os.path.join(package_root, "MANIFEST.json")
    if not os.path.exists(manifest_path):
        result["status"] = "fail"
        result["manifest_present"] = False
        result["missing_files"].append("MANIFEST.json")
        return result

    result["manifest_present"] = True

    # Load and validate manifest schema
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        result["status"] = "fail"
        result["manifest_schema_valid"] = False
        result["details"]["manifest_parse_error"] = str(e)
        return result

    required_schema_keys = {"package_version", "generated_at", "source_revision", "files"}
    if not required_schema_keys.issubset(set(manifest.keys())):
        result["status"] = "fail"
        result["manifest_schema_valid"] = False
        result["details"]["missing_schema_keys"] = sorted(
            required_schema_keys - set(manifest.keys())
        )
        return result

    result["manifest_schema_valid"] = True

    # Verify sha256 for all declared files
    declared_files = manifest.get("files") or {}
    sha256_complete = True
    sha256_verified = True
    sha_mismatches: list[str] = []

    for rel_path, file_info in declared_files.items():
        expected_sha = (file_info or {}).get("sha256")
        if not expected_sha:
            sha256_complete = False
            continue
        abs_path = os.path.join(package_root, rel_path)
        if not os.path.exists(abs_path):
            sha256_verified = False
            sha_mismatches.append(rel_path)
            continue
        actual_sha = _sha256_file(abs_path)
        if actual_sha != expected_sha:
            sha256_verified = False
            sha_mismatches.append(rel_path)

    result["sha256_complete"] = sha256_complete
    result["sha256_verified"] = sha256_verified
    result["sha_mismatches"] = sha_mismatches

    # Check mandatory file categories
    missing_mandatory: list[str] = []
    missing_files: list[str] = []
    details: dict[str, Any] = {}

    for category, candidates in _MANDATORY_FILE_PATTERNS.items():
        found, found_path = _file_present(package_root, candidates)
        details[category] = {"present": found, "path": found_path}
        if not found:
            missing_mandatory.append(category)
            missing_files.extend(candidates[:1])  # report first candidate as missing

    result["missing_mandatory"] = missing_mandatory
    result["missing_files"] = missing_files
    result["details"] = details

    # Determine overall status
    if (
        not result["manifest_present"]
        or not result["manifest_schema_valid"]
        or not result["sha256_verified"]
        or missing_mandatory
    ):
        result["status"] = "fail"

    return result
