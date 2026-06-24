from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v141" / "scripts"
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


builder = _load_module("build_v141_release_candidate_evidence_pack", SCRIPT_DIR / "build_v141_release_candidate_evidence_pack.py")
validator = _load_module("validate_v141_release_candidate", SCRIPT_DIR / "validate_v141_release_candidate.py")
generator = _load_module("generate_v141_adversarial_cases", SCRIPT_DIR / "generate_v141_adversarial_cases.py")
runtime = _load_module("product_runtime_adapter", REPO_ROOT / "benchmark" / "benchmark_v141" / "runtime" / "product_runtime_adapter.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V141ProductRuntimeAdapterValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v141_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 43)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 20)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 40)
            self.assertEqual(adversarial["detected_defect_count"], 40)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_declared_handlers_resolve_to_callables(self) -> None:
        expected = {
            "handle_get_daily_outfit",
            "handle_get_action_surface",
            "handle_post_action_submission",
            "handle_get_action_result",
            "handle_unsupported_route",
        }
        self.assertTrue(expected.issubset(runtime.HANDLER_CALLABLES))
        for handler_name in expected:
            self.assertTrue(callable(getattr(runtime, handler_name, None)))
            self.assertTrue(callable(runtime.HANDLER_CALLABLES.get(handler_name)))

    def test_missing_supported_route_binding_is_detected(self) -> None:
        failed = self._mutate("*A02_route_registry_binds_each_supported_route_once.json", lambda case: case["product_route_registry"].__setitem__("routes", case["product_route_registry"]["routes"][:-1]))
        self.assertIn("adapter_route_registry_complete_rate", failed["v141_A02_route_registry_binds_each_supported_route_once"])

    def test_handler_name_mismatch_is_detected(self) -> None:
        failed = self._mutate("*A04_get_action_surface_handler_matches_v140_contract.json", lambda case: case["route_handler_invocation"].__setitem__("handler_name", "handle_wrong"))
        self.assertIn("route_handler_invocation_valid_rate", failed["v141_A04_get_action_surface_handler_matches_v140_contract"])

    def test_missing_dispatch_steps_are_detected(self) -> None:
        failed = self._mutate("*B04_route_handler_trace_records_dispatch_steps.json", lambda case: case["runtime_handler_execution_trace"].__setitem__("dispatch_steps", []))
        self.assertIn("handler_dispatch_trace_complete_rate", failed["v141_B04_route_handler_trace_records_dispatch_steps"])

    def test_missing_source_resolution_is_detected(self) -> None:
        failed = self._mutate("*B05_route_handler_trace_records_source_resolution.json", lambda case: case["runtime_handler_execution_trace"].__setitem__("source_resolution_refs", []))
        self.assertIn("handler_uses_raw_source_artifacts_rate", failed["v141_B05_route_handler_trace_records_source_resolution"])

    def test_report_source_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["runtime_source_resolution_proof"]["source_v140_artifact_ref"] = "clean_report.json"
            case["runtime_source_resolution_proof"]["forbidden_source_types_observed"] = ["clean_report.json"]
        failed = self._mutate("*B01_action_surface_handler_uses_raw_v140_artifact_not_report.json", mutate)
        self.assertIn("handler_uses_raw_source_artifacts_rate", failed["v141_B01_action_surface_handler_uses_raw_v140_artifact_not_report"])

    def test_missing_action_surface_body_is_detected(self) -> None:
        failed = self._mutate("*A04_get_action_surface_handler_matches_v140_contract.json", lambda case: case["route_handler_result"]["output_envelope"]["body"].pop("action_surface", None))
        self.assertIn("handler_output_matches_v140_contract_rate", failed["v141_A04_get_action_surface_handler_matches_v140_contract"])

    def test_missing_action_result_resource_is_detected(self) -> None:
        failed = self._mutate("*A05_get_action_result_handler_matches_v140_contract.json", lambda case: case.__setitem__("action_result_api_resource", None))
        self.assertIn("runtime_action_result_links_response_rate", failed["v141_A05_get_action_result_handler_matches_v140_contract"])

    def test_no_write_action_write_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["route_handler_result"]["production_write_executed"] = True
            case["handler_no_write_proof"]["production_write_executed"] = True
        failed = self._mutate("*C01_post_this_time_only_handler_no_write_matches_contract.json", mutate)
        self.assertIn("no_write_handler_preserves_memory_state_rate", failed["v141_C01_post_this_time_only_handler_no_write_matches_contract"])

    def test_duplicate_submission_new_result_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["route_handler_result"]["output_envelope"]["body"]["idempotency"]["duplicate_created_result"] = True
        failed = self._mutate("*C04_duplicate_submission_handler_is_idempotent.json", mutate)
        self.assertIn("idempotent_handler_replay_rate", failed["v141_C04_duplicate_submission_handler_is_idempotent"])

    def test_snapshot_hash_mismatch_is_detected(self) -> None:
        failed = self._mutate("*E01_runtime_adapter_snapshot_hashes_reproducible.json", lambda case: case["runtime_adapter_snapshot"].__setitem__("canonical_output_hash", "bogus"))
        self.assertIn("runtime_snapshot_hash_reproducible_rate", failed["v141_E01_runtime_adapter_snapshot_hashes_reproducible"])

    def test_golden_contract_diff_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["golden_contract_replay"]["response_match"] = False
            case["golden_contract_replay"]["diff"] = [{"path": "body", "actual": "changed"}]
        failed = self._mutate("*E03_golden_contract_replay_request_response_match.json", mutate)
        self.assertIn("golden_contract_replay_rate", failed["v141_E03_golden_contract_replay_request_response_match"])

    def test_missing_response_block_claim_ref_is_detected(self) -> None:
        failed = self._mutate("*F01_conversation_turn_claims_survive_handler_execution.json", lambda case: case["conversation_turn_state"]["user_visible_claims"][0].__setitem__("trace_refs", [case["route_handler_result"]["output_envelope"]["api_response_id"]]))
        self.assertIn("conversation_claims_trace_backed_after_handler_rate", failed["v141_F01_conversation_turn_claims_survive_handler_execution"])

    def test_stale_visible_response_block_ids_are_detected(self) -> None:
        failed = self._mutate("*F02_visible_response_block_ids_match_handler_output.json", lambda case: case["conversation_turn_state"].__setitem__("visible_response_block_ids", ["stale_response_block_id"]))
        self.assertIn("conversation_claims_trace_backed_after_handler_rate", failed["v141_F02_visible_response_block_ids_match_handler_output"])

    def test_unsafe_error_text_is_detected(self) -> None:
        failed = self._mutate("*A06_unsupported_route_handler_returns_safe_error.json", lambda case: case["route_handler_result"]["output_envelope"]["error"].__setitem__("safe_message", "Traceback raw_evidence"))
        self.assertIn("runtime_error_safety_rate", failed["v141_A06_unsupported_route_handler_returns_safe_error"])

    def test_missing_callable_handler_registry_entry_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["product_runtime_adapter"]["callable_handler_registry"] = [
                row for row in case["product_runtime_adapter"]["callable_handler_registry"] if row["handler_name"] != "handle_get_action_surface"
            ]
        failed = self._mutate("*A04_get_action_surface_handler_matches_v140_contract.json", mutate)
        self.assertIn("adapter_route_registry_complete_rate", failed["v141_A04_get_action_surface_handler_matches_v140_contract"])

    def test_registry_non_callable_handler_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            for row in case["product_route_registry"]["routes"]:
                if row["route"] == "GET /local/action-surface":
                    row["handler_name"] = "not_a_callable_handler"
            case["route_handler_invocation"]["handler_name"] = "not_a_callable_handler"
            case["route_handler_invocation"]["resolved_callable_name"] = "not_a_callable_handler"
            case["runtime_handler_execution_trace"]["handler_name"] = "not_a_callable_handler"
        failed = self._mutate("*A04_get_action_surface_handler_matches_v140_contract.json", mutate)
        self.assertIn("adapter_route_registry_complete_rate", failed["v141_A04_get_action_surface_handler_matches_v140_contract"])

    def test_invocation_direct_copy_bypass_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["route_handler_result"]["produced_by_callable"] = False
            case["runtime_handler_execution_trace"]["callable_execution_proof"]["direct_source_output_copy"] = True
            case["runtime_handler_execution_trace"]["callable_execution_proof"]["callable_invoked"] = False
        failed = self._mutate("*A04_get_action_surface_handler_matches_v140_contract.json", mutate)
        self.assertIn("handler_dispatch_trace_complete_rate", failed["v141_A04_get_action_surface_handler_matches_v140_contract"])

    def test_unsupported_route_missing_callable_is_detected(self) -> None:
        failed = self._mutate("*A06_unsupported_route_handler_returns_safe_error.json", lambda case: case["product_route_registry"]["unsupported_route_policy"].__setitem__("handler_name", "handle_missing_unsupported_route"))
        self.assertIn("adapter_route_registry_complete_rate", failed["v141_A06_unsupported_route_handler_returns_safe_error"])

    def test_invoke_handler_without_callable_execution_proof_is_detected(self) -> None:
        failed = self._mutate("*B04_route_handler_trace_records_dispatch_steps.json", lambda case: case["runtime_handler_execution_trace"].pop("callable_execution_proof", None))
        self.assertIn("handler_dispatch_trace_complete_rate", failed["v141_B04_route_handler_trace_records_dispatch_steps"])

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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 40)
            self.assertEqual(adversarial["detected_defect_count"], 40)

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
