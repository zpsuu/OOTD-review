from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v139" / "scripts"
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


builder = _load_module("build_v139_release_candidate_evidence_pack", SCRIPT_DIR / "build_v139_release_candidate_evidence_pack.py")
validator = _load_module("validate_v139_release_candidate", SCRIPT_DIR / "validate_v139_release_candidate.py")
generator = _load_module("generate_v139_adversarial_cases", SCRIPT_DIR / "generate_v139_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V139GovernanceUserActionSurfaceValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v139_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 34)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 20)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 29)
            self.assertEqual(adversarial["detected_defect_count"], 29)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_card_without_queue_item_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*A01_open_clarification_queue_item_creates_active_action_card.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_action_surface"]["cards"][0]["governance_queue_item_id"] = "gqi_missing"
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("action_card_matches_queue_item_rate", failed["v139_A01_open_clarification_queue_item_creates_active_action_card"])

    def test_clarification_card_unallowed_action_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B05_clarification_allowed_actions_match_request.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_action_surface"]["cards"][0]["allowed_actions"].append("globalize_memory")
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("clarification_card_trace_backed_rate", failed["v139_B05_clarification_allowed_actions_match_request"])

    def test_this_time_only_write_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B02_this_time_only_submission_no_write_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_resolution_decision"]["production_write_executed"] = True
            case["after_memory_lifecycle_state"]["context_exclusions"] = ["formal_client_meeting"]
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("no_write_action_preserves_memory_state_rate", failed["v139_B02_this_time_only_submission_no_write_result"])

    def test_remember_for_context_without_gate_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B04_remember_for_context_submission_routes_to_write_gate.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_resolution_decision"]["production_write_gate_ref"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("remember_for_context_routes_to_write_gate_rate", failed["v139_B04_remember_for_context_submission_routes_to_write_gate"])

    def test_review_pending_internal_evidence_leak_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*C01_review_pending_notice_hides_raw_review_evidence.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["governance_action_surface"]["response_blocks"][0]["text"] = "Pending raw_evidence_refs and risk_reasons."
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("review_pending_notice_hides_internal_evidence_rate", failed["v139_C01_review_pending_notice_hides_raw_review_evidence"])

    def test_expired_submission_write_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D03_expired_action_submission_noop.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_result_packet"]["production_write_executed"] = True
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("expired_action_disabled_noop_rate", failed["v139_D03_expired_action_submission_noop"])

    def test_duplicate_submission_second_resolution_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D04_duplicate_action_submission_idempotent.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_idempotency_record"]["duplicate_created_resolution"] = True
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("duplicate_submission_idempotent_rate", failed["v139_D04_duplicate_action_submission_idempotent"])

    def test_stale_action_not_suppressed_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D05_stale_action_suppressed_after_resolution.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["stale_action_suppression_proof"]["suppressed"] = False
            case["governance_action_surface"]["cards"][0]["display_state"] = "active"
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("stale_action_suppressed_rate", failed["v139_D05_stale_action_suppressed_after_resolution"])

    def test_response_claim_without_trace_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*G01_response_claims_trace_to_action_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["response_claim_traces"][0]["trace_refs"] = []
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("response_claims_trace_backed_rate", failed["v139_G01_response_claims_trace_to_action_result"])

    def test_missing_idempotency_record_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D04_duplicate_action_submission_idempotent.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_idempotency_record"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("duplicate_submission_idempotent_rate", failed["v139_D04_duplicate_action_submission_idempotent"])

    def test_missing_stale_suppression_proof_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D05_stale_action_suppressed_after_resolution.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["stale_action_suppression_proof"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("stale_action_suppressed_rate", failed["v139_D05_stale_action_suppressed_after_resolution"])

    def test_missing_action_submission_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B02_this_time_only_submission_no_write_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_submission_envelope"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("action_submission_allowed_and_active_rate", failed["v139_B02_this_time_only_submission_no_write_result"])

    def test_missing_action_result_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*B02_this_time_only_submission_no_write_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_result_packet"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("post_action_packet_matches_resolution_rate", failed["v139_B02_this_time_only_submission_no_write_result"])

    def test_missing_expired_action_result_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*D03_expired_action_submission_noop.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_result_packet"] = None
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("expired_action_disabled_noop_rate", failed["v139_D03_expired_action_submission_noop"])
            self.assertIn("post_action_packet_matches_resolution_rate", failed["v139_D03_expired_action_submission_noop"])

    def test_missing_response_claim_trace_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*G01_response_claims_trace_to_action_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["response_claim_traces"] = []
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("response_claims_trace_backed_rate", failed["v139_G01_response_claims_trace_to_action_result"])

    def test_action_result_response_block_ids_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob("*G01_response_claims_trace_to_action_result.json"))
            case = json.loads(path.read_text(encoding="utf-8"))
            case["action_result_packet"]["user_visible_response_block_ids"] = ["urb_missing"]
            _write_json(path, case)
            failed = self._failed(result_dir)
            self.assertIn("response_claims_trace_backed_rate", failed["v139_G01_response_claims_trace_to_action_result"])

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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 29)
            self.assertEqual(adversarial["detected_defect_count"], 29)

    def _failed(self, result_dir: Path) -> dict[str, list[str]]:
        report = validator.validate_directory(result_dir, "clean")
        return {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}


if __name__ == "__main__":
    unittest.main()
