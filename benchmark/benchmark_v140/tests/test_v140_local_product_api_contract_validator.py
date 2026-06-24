from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v140" / "scripts"
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


builder = _load_module("build_v140_release_candidate_evidence_pack", SCRIPT_DIR / "build_v140_release_candidate_evidence_pack.py")
validator = _load_module("validate_v140_release_candidate", SCRIPT_DIR / "validate_v140_release_candidate.py")
generator = _load_module("generate_v140_adversarial_cases", SCRIPT_DIR / "generate_v140_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V140LocalProductAPIContractValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v140_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 36)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 18)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 24)
            self.assertEqual(adversarial["detected_defect_count"], 24)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_missing_response_contract_version_is_detected(self) -> None:
        failed = self._mutate("*A01_get_daily_outfit_returns_contract_envelope.json", lambda case: case["local_api_response_envelope"].pop("contract_version", None))
        self.assertIn("api_request_response_envelope_valid_rate", failed["v140_A01_get_daily_outfit_returns_contract_envelope"])

    def test_route_handler_report_source_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["product_route_handler_proof"]["source_artifact_refs"] = ["clean_report.json"]
            case["product_route_handler_proof"]["field_mapping"][0]["source"] = "report_summary"
        failed = self._mutate("*A02_get_action_surface_returns_cards_and_response_blocks.json", mutate)
        self.assertIn("route_handler_maps_to_raw_artifacts_rate", failed["v140_A02_get_action_surface_returns_cards_and_response_blocks"])

    def test_action_surface_missing_card_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["action_surface_api_resource"]["cards"] = []
            case["local_api_response_envelope"]["body"]["action_surface"]["cards"] = []
        failed = self._mutate("*B02_open_clarification_card_contract_shape.json", mutate)
        self.assertIn("action_surface_api_matches_v139_surface_rate", failed["v140_B02_open_clarification_card_contract_shape"])

    def test_disallowed_action_submission_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["action_submission_api_resource"]["submitted_action"] = "globalize_memory"
            case["local_api_request_envelope"]["body"]["submitted_action"] = "globalize_memory"
        failed = self._mutate("*C01_post_this_time_only_submission_no_write.json", mutate)
        self.assertIn("action_submission_contract_valid_rate", failed["v140_C01_post_this_time_only_submission_no_write"])

    def test_no_write_action_write_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["action_submission_api_resource"]["production_write_executed"] = True
            case["action_result_api_resource"]["production_write_executed"] = True
        failed = self._mutate("*C01_post_this_time_only_submission_no_write.json", mutate)
        self.assertIn("no_write_error_preserves_memory_state_rate", failed["v140_C01_post_this_time_only_submission_no_write"])

    def test_duplicate_submission_new_result_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["local_api_response_envelope"]["body"]["idempotency"]["duplicate_created_result"] = True
        failed = self._mutate("*C04_duplicate_submission_returns_idempotent_result.json", mutate)
        self.assertIn("idempotent_submission_contract_rate", failed["v140_C04_duplicate_submission_returns_idempotent_result"])

    def test_expired_error_write_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["api_error_envelope"]["production_write_executed"] = True
            case["local_api_response_envelope"]["error"]["production_write_executed"] = True
        failed = self._mutate("*D02_expired_action_submission_returns_expired_error_no_write.json", mutate)
        self.assertIn("expired_stale_action_contract_rate", failed["v140_D02_expired_action_submission_returns_expired_error_no_write"])

    def test_unsafe_error_text_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["api_error_envelope"]["safe_message"] = "Traceback with raw_evidence_refs"
            case["local_api_response_envelope"]["error"]["safe_message"] = case["api_error_envelope"]["safe_message"]
        failed = self._mutate("*D05_malformed_payload_returns_contract_error_no_write.json", mutate)
        self.assertIn("redaction_policy_safe_response_rate", failed["v140_D05_malformed_payload_returns_contract_error_no_write"])

    def test_snapshot_hash_mismatch_is_detected(self) -> None:
        failed = self._mutate("*F01_contract_snapshot_hashes_reproducible.json", lambda case: case["contract_snapshot"].__setitem__("canonical_response_hash", "bogus"))
        self.assertIn("contract_snapshot_hash_reproducible_rate", failed["v140_F01_contract_snapshot_hashes_reproducible"])

    def test_source_hash_missing_is_detected(self) -> None:
        failed = self._mutate("*F02_source_artifact_hashes_match_raw_per_case.json", lambda case: case["contract_snapshot"].__setitem__("source_artifact_hashes", {}))
        self.assertIn("source_artifact_hashes_match_raw_rate", failed["v140_F02_source_artifact_hashes_match_raw_per_case"])

    def test_backward_compatibility_stale_schema_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["schema_compatibility_report"]["current_schema_version"] = "product_api.v0"
            case["contract_replay_trace"]["replay_result"] = "fail"
        failed = self._mutate("*F03_backward_compatibility_replay_stable.json", mutate)
        self.assertIn("backward_compatibility_replay_rate", failed["v140_F03_backward_compatibility_replay_stable"])

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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 24)
            self.assertEqual(adversarial["detected_defect_count"], 24)

    def _mutate(self, pattern: str, mutate) -> dict[str, list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = self._build(tmp)
            path = next((result_dir / "per_case" / "clean").glob(pattern))
            case = json.loads(path.read_text(encoding="utf-8"))
            mutate(case)
            _write_json(path, case)
            return self._failed(result_dir)

    def _failed(self, result_dir: Path) -> dict[str, list[str]]:
        report = validator.validate_directory(result_dir, "clean")
        return {case["case_id"]: case["failed_check_ids"] for case in report["case_results"] if not case["passed"]}


if __name__ == "__main__":
    unittest.main()
