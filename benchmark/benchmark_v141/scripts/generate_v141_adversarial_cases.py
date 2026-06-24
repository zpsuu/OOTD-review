"""Generate v1.41 adversarial raw artifacts from mixed_strict defects."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.common.raw_artifact_validation import now_iso, write_json


DEFAULT_SOURCE_DIR = Path("benchmark/benchmark_v141/results/v141_release_candidate")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(source_dir: Path) -> None:
    adversarial_dir = source_dir / "per_case" / "adversarial"
    if adversarial_dir.exists():
        shutil.rmtree(adversarial_dir)
    adversarial_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"version": "v1.41", "generated_at": now_iso(), "source_result_dir": str(source_dir), "cases": []}
    for path in sorted((source_dir / "per_case" / "mixed_strict").glob("*.json")):
        case = _read_json(path)
        out = adversarial_dir / path.name
        write_json(out, case)
        manifest["cases"].append({"case_id": case["case_id"], "artifact_ref": str(out.relative_to(source_dir)), "defect_type": case.get("defect_type"), "expected_failed_check_ids": case.get("expected_failed_check_ids", [])})
    write_json(source_dir / "ADVERSARIAL_MANIFEST.json", manifest)
    print(f"Built adversarial cases under {adversarial_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result-dir", default=str(DEFAULT_SOURCE_DIR))
    args = parser.parse_args()
    build(Path(args.source_result_dir))


if __name__ == "__main__":
    main()
