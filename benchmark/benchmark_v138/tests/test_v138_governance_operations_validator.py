from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v138" / "scripts"
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


builder = _load_module("build_v138_release_candidate_evidence_pack", SCRIPT_DIR / "build_v138_release_candidate_evidence_pack.py")
validator = _load_module("validate_v138_release_candidate", SCRIPT_DIR / "validate_v138_release_candidate.py")
generator = _load_module("generate_v138_adversarial_cases", SCRIPT_DIR / "generate_v138_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V138GovernanceOperationsValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v138_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 32)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 23)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 26)
            self.assertEqual(adversarial["detected_defect_count"], 26)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_queue_item_without_trigger_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_clarification_trigger_creates_open_queue_item.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_trigger"]["governance_trigger_id"] = "missing_trigger"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("governance_queue_created_from_runtime_trigger_rate", failed["v138_A01_clarification_trigger_creates_open_queue_item"])

    def test_duplicate_open_items_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*E01_duplicate_clarification_items_dedupe.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            item = copy.deepcopy(case["runtime_governance_queue"]["queue_items"][0])
            item["governance_queue_item_id"] = "gqi_bad_duplicate"
            item["status"] = "open"
            item["resolution_ref"] = None
            case["runtime_governance_queue"]["queue_items"].append(item)
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("queue_dedupe_blocks_duplicate_open_items_rate", failed["v138_E01_duplicate_clarification_items_dedupe"])

    def test_clarification_no_write_mutation_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B02_clarification_answer_this_time_only_no_write.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["after_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("clarification_no_write_preserves_memory_state_rate", failed["v138_B02_clarification_answer_this_time_only_no_write"])

    def test_review_approval_without_gate_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C02_review_approve_write_still_uses_write_gate.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["production_memory_write_gate"]["decision"] = "block"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_resolution_uses_write_gate_rate", failed["v138_C02_review_approve_write_still_uses_write_gate"])

    def test_open_clarification_item_requires_matching_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C04_review_request_clarification_creates_clarification_item.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            open_item_ids = {
                item["governance_queue_item_id"]
                for item in case["runtime_governance_queue"]["queue_items"]
                if item.get("status") == "open" and item.get("trigger_type") == "clarification_required"
            }
            case["clarification_requests"] = [
                request
                for request in case.get("clarification_requests", [])
                if request.get("governance_queue_item_id") not in open_item_ids
            ]
            case["clarification_request"] = case["clarification_requests"][0] if case["clarification_requests"] else None
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("clarification_request_trace_backed_rate", failed["v138_C04_review_request_clarification_creates_clarification_item"])

    def test_open_human_review_item_requires_matching_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A02_human_review_trigger_creates_open_queue_item.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"] = None
            case["human_review_payloads"] = []
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_A02_human_review_trigger_creates_open_queue_item"])

    def test_open_human_review_payload_requires_raw_runtime_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A02_human_review_trigger_creates_open_queue_item.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"]["raw_evidence_refs"] = ["not_runtime_evidence"]
            case["human_review_payloads"][0]["raw_evidence_refs"] = ["not_runtime_evidence"]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_A02_human_review_trigger_creates_open_queue_item"])

    def test_open_human_review_item_rejects_duplicate_matching_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A02_human_review_trigger_creates_open_queue_item.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            duplicate = copy.deepcopy(case["human_review_payloads"][0])
            duplicate["human_review_payload_id"] = "hrp_duplicate"
            case["human_review_payloads"].append(duplicate)
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_A02_human_review_trigger_creates_open_queue_item"])

    def test_resolved_clarification_item_requires_matching_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B02_clarification_answer_this_time_only_no_write.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["clarification_request"] = None
            case["clarification_requests"] = []
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("clarification_request_trace_backed_rate", failed["v138_B02_clarification_answer_this_time_only_no_write"])

    def test_resolved_review_rejection_requires_matching_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C03_review_reject_no_write_preserves_memory_state.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"] = None
            case["human_review_payloads"] = []
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_C03_review_reject_no_write_preserves_memory_state"])

    def test_resolved_review_rejection_payload_requires_raw_runtime_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C03_review_reject_no_write_preserves_memory_state.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"]["raw_evidence_refs"] = ["not_runtime_evidence"]
            case["human_review_payloads"][0]["raw_evidence_refs"] = ["not_runtime_evidence"]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_C03_review_reject_no_write_preserves_memory_state"])

    def test_resolved_review_approval_requires_matching_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C02_review_approve_write_still_uses_write_gate.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"] = None
            case["human_review_payloads"] = []
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_C02_review_approve_write_still_uses_write_gate"])

    def test_resolved_review_approval_payload_requires_raw_runtime_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C02_review_approve_write_still_uses_write_gate.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["human_review_payload"]["raw_evidence_refs"] = ["not_runtime_evidence"]
            case["human_review_payloads"][0]["raw_evidence_refs"] = ["not_runtime_evidence"]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_C02_review_approve_write_still_uses_write_gate"])

    def test_resolved_human_review_item_rejects_duplicate_matching_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C02_review_approve_write_still_uses_write_gate.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            duplicate = copy.deepcopy(case["human_review_payloads"][0])
            duplicate["human_review_payload_id"] = "hrp_duplicate"
            case["human_review_payloads"].append(duplicate)
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("human_review_payload_has_raw_evidence_rate", failed["v138_C02_review_approve_write_still_uses_write_gate"])

    def test_expired_hold_write_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D03_temporary_hold_expiry_no_write.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_resolution_decision"]["production_write_executed"] = True
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("expired_item_no_write_rate", failed["v138_D03_temporary_hold_expiry_no_write"])

    def test_post_resolution_packet_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*F01_post_resolution_packet_matches_approved_write.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            memory_id = case["before_memory_lifecycle_state"]["memory_id"]
            case["post_resolution_task_memory_packet"]["consumed_promoted_memory_ids"] = []
            case["post_resolution_task_memory_packet"]["excluded_memory_ids"] = [memory_id]
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("post_resolution_packet_matches_resolution_rate", failed["v138_F01_post_resolution_packet_matches_approved_write"])

    def test_ledger_hash_break_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*H01_ledger_hash_chain_valid.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_decision_ledger"]["ledger_entries"][0]["entry_hash"] = "sha256-bad"
            _write_json(path, case)
            report = validator.validate_directory(result_dir, "clean")
            failed = {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}
            self.assertIn("ledger_hash_chain_valid_rate", failed["v138_H01_ledger_hash_chain_valid"])

    def test_stale_sample_artifact_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            _write_json(result_dir / "independent_validation_report.json", validator.validate_directory(result_dir, "clean"))
            generator.build(result_dir)
            _write_json(result_dir / "adversarial_validation_report.json", validator.validate_directory(result_dir, "adversarial"))
            sample_path = result_dir / "sample_artifacts" / "clarification_this_time_only_no_write.json"
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            sample["manual_only_patch"] = True
            _write_json(sample_path, sample)
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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 26)
            self.assertEqual(adversarial["detected_defect_count"], 26)


if __name__ == "__main__":
    unittest.main()
