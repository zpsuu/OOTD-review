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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 20)
            self.assertEqual(adversarial["detected_defect_count"], 20)
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

    def test_handoff_missing_source_output_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_full_loop_low_risk_color_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["handoff_proofs"][0]["source_output_ref"] = "ghost_ref"
            case["handoff_proofs"][0]["target_input_ref"] = "ghost_ref"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("handoff_ids_match_across_stages_rate", failed["v137_A01_full_loop_low_risk_color_memory"])

    def test_handoff_missing_target_input_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_full_loop_low_risk_color_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["runtime_trace"]["stage_events"][0]["output_refs"].append("ghost_ref")
            case["handoff_proofs"][0]["source_output_ref"] = "ghost_ref"
            case["handoff_proofs"][0]["target_input_ref"] = "ghost_ref"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("handoff_ids_match_across_stages_rate", failed["v137_A01_full_loop_low_risk_color_memory"])

    def test_blocked_handoff_ref_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_full_loop_low_risk_color_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            candidate_id = case["inspiration_candidate"]["candidate_id"]
            case["runtime_trace"]["stage_events"][0]["blocked_output_refs"].append(candidate_id)
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("handoff_ids_match_across_stages_rate", failed["v137_A01_full_loop_low_risk_color_memory"])

    def test_missing_state_snapshot_handoff_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_full_loop_low_risk_color_memory.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["handoff_proofs"][-1]["source_output_ref"] = "state_missing"
            case["handoff_proofs"][-1]["target_input_ref"] = "state_missing"
            case["runtime_trace"]["stage_events"][-2]["output_refs"].append("state_missing")
            case["runtime_trace"]["stage_events"][-1]["input_refs"].append("state_missing")
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("handoff_ids_match_across_stages_rate", failed["v137_A01_full_loop_low_risk_color_memory"])

    def test_fake_feedback_without_promoted_memory_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B01_unconfirmed_candidate_never_promotes.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["promoted_memory_feedback_event"]["promoted_memory_id"] = "mem_fake"
            case["promoted_memory_feedback_event"]["consumption_report_id"] = "pmcr_fake"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("feedback_event_refs_consumed_memory_rate", failed["v137_B01_unconfirmed_candidate_never_promotes"])

    def test_clarification_misrouting_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*G01_ambiguous_feedback_requires_clarification.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["feedback_interpretation"]["interpreted_intent"] = "review_required"
            case["feedback_write_decision"]["gate_decision"] = "human_review_required"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("review_pending_does_not_claim_applied_effect_rate", failed["v137_G01_ambiguous_feedback_requires_clarification"])

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

    def test_adversarial_detection_does_not_depend_on_gate_assertions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            generator.build(result_dir)
            for path in (result_dir / "per_case" / "adversarial").glob("*.json"):
                case = json.loads(path.read_text(encoding="utf-8"))
                for key in list((case.get("gate_assertions") or {}).keys()):
                    case["gate_assertions"][key] = True
                _write_json(path, case)
            adversarial = validator.validate_directory(result_dir, "adversarial")
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 20)
            self.assertEqual(adversarial["detected_defect_count"], 20)


if __name__ == "__main__":
    unittest.main()
