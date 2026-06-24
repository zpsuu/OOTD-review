"""Run the v1.40 validation workflow end to end."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_DIR = REPO_ROOT / "benchmark" / "benchmark_v140" / "results" / "v140_release_candidate"


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    py = sys.executable
    _run([py, "benchmark/benchmark_v139/scripts/run_v139_validation_suite.py"])
    _run([py, "benchmark/benchmark_v140/scripts/build_v140_release_candidate_evidence_pack.py", "--build"])
    _run([py, "benchmark/benchmark_v140/scripts/validate_v140_release_candidate.py", "--result-dir", "benchmark/benchmark_v140/results/v140_release_candidate", "--subset", "clean", "--output", "benchmark/benchmark_v140/results/v140_release_candidate/independent_validation_report.json"])
    _run([py, "benchmark/benchmark_v140/scripts/generate_v140_adversarial_cases.py", "--source-result-dir", "benchmark/benchmark_v140/results/v140_release_candidate"])
    _run([py, "benchmark/benchmark_v140/scripts/validate_v140_release_candidate.py", "--result-dir", "benchmark/benchmark_v140/results/v140_release_candidate", "--subset", "adversarial", "--output", "benchmark/benchmark_v140/results/v140_release_candidate/adversarial_validation_report.json", "--write-consistency"])
    consistency = _read_json(RESULT_DIR / "report_consistency_report.json")
    sample = _read_json(RESULT_DIR / "sample_consistency_report.json")
    injected = _read_json(RESULT_DIR / "injected_defect_detection_summary.json")
    if consistency.get("passed") is not True:
        raise SystemExit(f"report consistency failed: {consistency.get('failures')}")
    if sample.get("passed") is not True:
        raise SystemExit(f"sample consistency failed: {sample.get('failures')}")
    if injected.get("detected_defects") != injected.get("seeded_defects"):
        raise SystemExit("not every v1.40 injected defect was detected")
    _run([py, "-m", "unittest", "discover", "-s", "benchmark/benchmark_v140/tests"])
    print("v1.40 validation suite PASS")


if __name__ == "__main__":
    main()
