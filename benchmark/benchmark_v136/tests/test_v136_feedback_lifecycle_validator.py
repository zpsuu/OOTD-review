from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v136" / "scripts"
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


builder = _load_module("build_v136_release_candidate_evidence_pack", SCRIPT_DIR / "build_v136_release_candidate_evidence_pack.py")
validator = _load_module("validate_v136_release_candidate", SCRIPT_DIR / "validate_v136_release_candidate.py")
generator = _load_module("generate_v136_adversarial_cases", SCRIPT_DIR / "generate_v136_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V136FeedbackLifecycleValidatorTests(unittest.TestCase):
    def test_clean_adversarial_and_consistency_reports_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            clean = validator.validate_directory(result_dir, "clean")
            _write_json(result_dir / "independent_validation_report.json", clean)
            generator.build(result_dir)
            adversarial = validator.validate_directory(result_dir, "adversarial")
            _write_json(result_dir / "adversarial_validation_report.json", adversarial)
            sample, consistency = validator.write_consistency_reports(result_dir)

            self.assertEqual(clean["suite_summary"]["passed_cases"], 50)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 25)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 13)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_too_strong_delete_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            path = next((result_dir / "per_case" / "clean").glob("*C01_use_was_too_strong_reduces_weight.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["updated_memory_lifecycle_state"]["current_status"] = "rolled_back"
            _write_json(path, case)

            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("v136_C01_use_was_too_strong_reduces_weight", failed)
            self.assertIn("too_strong_feedback_reduces_weight_not_deletes_rate", failed["v136_C01_use_was_too_strong_reduces_weight"])

    def test_wrong_context_globalization_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            path = next((result_dir / "per_case" / "clean").glob("*E01_wrong_context_adds_context_exclusion.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["updated_memory_lifecycle_state"]["contexts"] = ["global"]
            _write_json(path, case)

            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("single_feedback_does_not_globalize_rate", failed["v136_E01_wrong_context_adds_context_exclusion"])

    def test_wrong_context_exclusion_must_test_excluded_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            path = next((result_dir / "per_case" / "clean").glob("*E04_future_mismatching_context_excludes_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["post_feedback_consumption_proof"]["task_memory_packet_after_feedback"]["request_context"] = "office_daily"
            _write_json(path, case)

            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("wrong_context_future_exclusion_rate", failed["v136_E04_future_mismatching_context_excludes_memory"])

    def test_review_pending_applied_effect_claim_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            path = next((result_dir / "per_case" / "clean").glob("*H01_globalize_request_from_feedback_requires_review.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["post_feedback_consumption_proof"]["response_claims_after_feedback"] = [
                {
                    "claim_id": "bad_review_pending_claim",
                    "trace_refs": [case["promoted_memory_atom"]["memory_id"]],
                    "text": "I softened this memory for future outfits.",
                }
            ]
            _write_json(path, case)

            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn(
                "review_pending_does_not_claim_applied_lifecycle_effect_rate",
                failed["v136_H01_globalize_request_from_feedback_requires_review"],
            )

    def test_stale_sample_artifact_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp) / "v136_release_candidate"
            builder.build(result_dir)
            _write_json(result_dir / "independent_validation_report.json", validator.validate_directory(result_dir, "clean"))
            generator.build(result_dir)
            _write_json(result_dir / "adversarial_validation_report.json", validator.validate_directory(result_dir, "adversarial"))
            sample_path = result_dir / "sample_artifacts" / "wrong_context_future_exclusion.json"
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            mutated = copy.deepcopy(sample)
            mutated["manual_only_patch"] = True
            _write_json(sample_path, mutated)

            sample_report = validator.write_consistency_reports(result_dir)[0]
            self.assertFalse(sample_report["passed"])
            self.assertEqual(sample_report["failed_samples"], 1)


if __name__ == "__main__":
    unittest.main()
