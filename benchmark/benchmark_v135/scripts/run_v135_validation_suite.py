"""Run the v1.35 validation workflow end to end."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
V135_RESULT_DIR = REPO_ROOT / "benchmark" / "benchmark_v135" / "results" / "v135_release_candidate"


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    py = sys.executable
    _run([py, "benchmark/benchmark_v134/scripts/build_v134_release_candidate_evidence_pack.py", "--build"])
    _run(
        [
            py,
            "benchmark/benchmark_v134/scripts/validate_v134_release_candidate.py",
            "--result-dir",
            "benchmark/benchmark_v134/results/v134_release_candidate",
            "--subset",
            "clean",
            "--output",
            "benchmark/benchmark_v134/results/v134_release_candidate/v134_independent_validation_report.json",
        ]
    )
    _run(
        [
            py,
            "benchmark/benchmark_v134/scripts/generate_v134_adversarial_cases.py",
            "--source-result-dir",
            "benchmark/benchmark_v134/results/v134_release_candidate",
            "--output-dir",
            "benchmark/benchmark_v134/results/v134_adversarial_validation",
        ]
    )
    _run(
        [
            py,
            "benchmark/benchmark_v134/scripts/validate_v134_release_candidate.py",
            "--result-dir",
            "benchmark/benchmark_v134/results/v134_adversarial_validation",
            "--subset",
            "adversarial",
            "--output",
            "benchmark/benchmark_v134/results/v134_adversarial_validation/v134_adversarial_validation_report.json",
        ]
    )
    _run([py, "-m", "unittest", "benchmark/benchmark_v134/tests/test_v134_acceptance_validator.py"])

    _run([py, "benchmark/benchmark_v135/scripts/build_v135_release_candidate_evidence_pack.py", "--build"])
    _run(
        [
            py,
            "benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py",
            "--result-dir",
            "benchmark/benchmark_v135/results/v135_release_candidate",
            "--subset",
            "clean",
            "--output",
            "benchmark/benchmark_v135/results/v135_release_candidate/independent_validation_report.json",
        ]
    )
    _run(
        [
            py,
            "benchmark/benchmark_v135/scripts/validate_v135_release_candidate.py",
            "--result-dir",
            "benchmark/benchmark_v135/results/v135_release_candidate",
            "--subset",
            "adversarial",
            "--output",
            "benchmark/benchmark_v135/results/v135_release_candidate/adversarial_validation_report.json",
            "--write-consistency",
        ]
    )
    consistency = _read_json(V135_RESULT_DIR / "report_consistency_report.json")
    sample = _read_json(V135_RESULT_DIR / "sample_consistency_report.json")
    if consistency.get("passed") is not True:
        raise SystemExit(f"report consistency failed: {consistency.get('failures')}")
    if sample.get("passed") is not True:
        raise SystemExit(f"sample consistency failed: {sample.get('failures')}")
    _run([py, "-m", "unittest", "discover", "-s", "benchmark/benchmark_v135/tests"])
    print("v1.35 validation suite PASS")


if __name__ == "__main__":
    main()

