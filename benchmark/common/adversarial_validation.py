"""Tiny helpers for adversarial validation reports."""
from __future__ import annotations

from typing import Any


def detected_defect_rows(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in case_results:
        expected = case.get("expected_failed_check_ids", [])
        actual = case.get("failed_check_ids", [])
        rows.append(
            {
                "case_id": case["case_id"],
                "defect_type": case.get("defect_type"),
                "expected_failed_check_ids": expected,
                "failed_check_ids": actual,
                "detected": bool(actual) and set(expected).issubset(set(actual)),
            }
        )
    return rows

