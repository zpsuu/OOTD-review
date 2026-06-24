from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v135" / "scripts"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_module("build_v135_release_candidate_evidence_pack", SCRIPT_DIR / "build_v135_release_candidate_evidence_pack.py")
validator = _load_module("validate_v135_release_candidate", SCRIPT_DIR / "validate_v135_release_candidate.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V135ValidationWorkflowTests(unittest.TestCase):
    def test_clean_adversarial_and_consistency_reports_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v135_release_candidate"
            builder.build(result_dir)
            clean = validator.validate_directory(result_dir, "clean")
            _write_json(result_dir / "independent_validation_report.json", clean)
            adversarial = validator.validate_directory(result_dir, "adversarial")
            _write_json(result_dir / "adversarial_validation_report.json", adversarial)
            sample, consistency = validator.write_consistency_reports(result_dir)

            self.assertEqual(clean["suite_summary"]["passed_cases"], 15)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 15)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 10)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_report_only_pass_is_blocked_by_independent_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v135_release_candidate"
            builder.build(result_dir)
            case_path = next((result_dir / "per_case" / "clean").glob("*B05_raw_case_failure_overrides_aggregate_pass.json"))
            case = json.loads(case_path.read_text(encoding="utf-8"))
            case["gate_assertions"]["raw_case_failure_overrides_aggregate_pass_rate"] = False
            _write_json(case_path, case)

            clean = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in clean["case_results"] if not case["passed"]}
            self.assertIn("v135_B05_raw_case_failure_overrides_aggregate_pass", failed)
            self.assertIn("raw_case_failure_overrides_aggregate_pass_rate", failed["v135_B05_raw_case_failure_overrides_aggregate_pass"])

    def test_stale_sample_artifact_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v135_release_candidate"
            builder.build(result_dir)
            _write_json(result_dir / "independent_validation_report.json", validator.validate_directory(result_dir, "clean"))
            _write_json(result_dir / "adversarial_validation_report.json", validator.validate_directory(result_dir, "adversarial"))
            sample_path = result_dir / "sample_artifacts" / "sample_artifact_matches_per_case.json"
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            mutated = copy.deepcopy(sample)
            mutated["manual_only_patch"] = True
            _write_json(sample_path, mutated)

            sample_report = validator.write_consistency_reports(result_dir)[0]
            self.assertFalse(sample_report["passed"])
            self.assertEqual(sample_report["failed_samples"], 1)


if __name__ == "__main__":
    unittest.main()
