from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v137" / "scripts"
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


builder = _load_module("build_v137_release_candidate_evidence_pack", SCRIPT_DIR / "build_v137_release_candidate_evidence_pack.py")
validator = _load_module("validate_v137_release_candidate", SCRIPT_DIR / "validate_v137_release_candidate.py")
generator = _load_module("generate_v137_adversarial_cases", SCRIPT_DIR / "generate_v137_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V137RuntimeLoopValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v137_release_candidate"
        builder.build(result_dir)
        return result_dir

    def test_clean_adversarial_and_consistency_reports_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            clean = validator.validate_directory(result_dir, "clean")
            _write_json(result_dir / "independent_validation_report.json", clean)
            generator.build(result_dir)
            adversarial = validator.validate_directory(result_dir, "adversarial")
            _write_json(result_dir / "adversarial_validation_report.json", adversarial)
            sample, consistency = validator.write_consistency_reports(result_dir)

            self.assertEqual(clean["suite_summary"]["passed_cases"], 30)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 21)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 14)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_stage_order_skip_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_full_loop_low_risk_color_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["runtime_trace"]["stage_order"].remove("confirmation")
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("runtime_trace_stage_order_complete_rate", failed["v137_A01_full_loop_low_risk_color_memory"])

    def test_pre_gate_write_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C01_low_risk_contextual_promotion_allowed.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["production_memory_write_gate"]["pre_gate_production_write"] = True
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("no_pre_gate_production_write_rate", failed["v137_C01_low_risk_contextual_promotion_allowed"])

    def test_handoff_id_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*J02_promotion_to_consumption_handoff_same_id.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["handoff_proofs"][2]["target_input_ref"] = "different_memory_id"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("handoff_ids_match_across_stages_rate", failed["v137_J02_promotion_to_consumption_handoff_same_id"])

    def test_review_pending_applied_claim_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*E04_review_pending_feedback_does_not_claim_applied_effect.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["post_feedback_claims"] = [{"claim_id": "bad_claim", "text": "I softened this memory.", "trace_refs": [case["promoted_memory_atom"]["memory_id"]]}]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("review_pending_does_not_claim_applied_effect_rate", failed["v137_E04_review_pending_feedback_does_not_claim_applied_effect"])

    def test_rollback_future_consumption_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*F03_rollback_removes_future_claims.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["post_feedback_task_memory_packet"]["consumed_promoted_memory_ids"] = [case["promoted_memory_atom"]["memory_id"]]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("rollback_removes_future_consumption_rate", failed["v137_F03_rollback_removes_future_claims"])

    def test_stale_sample_artifact_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            _write_json(result_dir / "independent_validation_report.json", validator.validate_directory(result_dir, "clean"))
            generator.build(result_dir)
            _write_json(result_dir / "adversarial_validation_report.json", validator.validate_directory(result_dir, "adversarial"))
            sample_path = result_dir / "sample_artifacts" / "full_loop_low_risk_color_memory.json"
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            mutated = copy.deepcopy(sample)
            mutated["manual_only_patch"] = True
            _write_json(sample_path, mutated)
            sample_report = validator.write_consistency_reports(result_dir)[0]
            self.assertFalse(sample_report["passed"])
            self.assertEqual(sample_report["failed_samples"], 1)


if __name__ == "__main__":
    unittest.main()

