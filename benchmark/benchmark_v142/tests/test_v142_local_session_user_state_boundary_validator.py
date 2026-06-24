from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v142" / "scripts"
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


builder = _load_module("build_v142_release_candidate_evidence_pack", SCRIPT_DIR / "build_v142_release_candidate_evidence_pack.py")
validator = _load_module("validate_v142_release_candidate", SCRIPT_DIR / "validate_v142_release_candidate.py")
generator = _load_module("generate_v142_adversarial_cases", SCRIPT_DIR / "generate_v142_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V142LocalSessionUserStateBoundaryValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v142_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 44)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 21)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 52)
            self.assertEqual(adversarial["detected_defect_count"], 52)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_shared_memory_namespace_is_detected(self) -> None:
        failed = self._mutate("*A01_two_local_users_have_distinct_namespaces.json", lambda case: case["local_user_fixtures"][1].__setitem__("memory_namespace_id", case["local_user_fixtures"][0]["memory_namespace_id"]))
        self.assertIn("local_user_fixture_namespace_complete_rate", failed["v142_A01_two_local_users_have_distinct_namespaces"])

    def test_session_wrong_user_is_detected(self) -> None:
        failed = self._mutate("*A02_session_envelope_binds_to_exactly_one_user.json", lambda case: case["local_session_envelope"].__setitem__("local_user_id", "local_user_B"))
        self.assertIn("session_envelope_valid_rate", failed["v142_A02_session_envelope_binds_to_exactly_one_user"])

    def test_foreign_output_ref_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["session_scoped_route_handler_result"]["output_envelope"].setdefault("body", {}).setdefault("session_boundary_refs", []).append("local_user_B")
        failed = self._mutate("*B02_user_A_get_action_surface_does_not_include_user_B_refs.json", mutate)
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B02_user_A_get_action_surface_does_not_include_user_B_refs"])

    def test_idempotency_scope_missing_user_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            key = case["session_scoped_idempotency_record"]["idempotency_scope_key"].replace("local_user_A:", "")
            case["session_scoped_idempotency_record"]["idempotency_scope_key"] = key
            case["session_scoped_runtime_invocation"]["idempotency_scope_key"] = key
        failed = self._mutate("*D04_idempotency_scope_key_contains_user_session_route_card_key.json", mutate)
        self.assertIn("idempotency_scope_is_user_session_bound_rate", failed["v142_D04_idempotency_scope_key_contains_user_session_route_card_key"])

    def test_different_user_reuse_foreign_result_is_detected(self) -> None:
        failed = self._mutate("*D03_different_user_same_key_does_not_reuse_result.json", lambda case: case["session_scoped_idempotency_record"].__setitem__("canonical_action_result_ref", "action_result_local_user_A_sess_A_001_foreign"))
        self.assertIn("different_scope_duplicate_does_not_reuse_result_rate", failed["v142_D03_different_user_same_key_does_not_reuse_result"])

    def test_expired_session_success_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["session_expiry_and_stale_action_proof"]["accepted_action"] = True
            case["session_scoped_route_handler_result"]["response_type"] = "action_submission_result"
        failed = self._mutate("*E01_expired_session_rejects_action_no_write.json", mutate)
        self.assertIn("expired_session_no_write_error_rate", failed["v142_E01_expired_session_rejects_action_no_write"])

    def test_stale_session_write_is_detected(self) -> None:
        failed = self._mutate("*E02_advanced_session_state_suppresses_stale_action.json", lambda case: case["session_scoped_route_handler_result"].__setitem__("production_write_executed", True))
        self.assertIn("stale_session_action_no_write_rate", failed["v142_E02_advanced_session_state_suppresses_stale_action"])

    def test_boundary_trace_missing_user_resolution_is_detected(self) -> None:
        failed = self._mutate("*F01_session_boundary_trace_records_user_namespace_resolution.json", lambda case: case["session_boundary_trace"].__setitem__("boundary_steps", [s for s in case["session_boundary_trace"]["boundary_steps"] if s["operation"] != "resolve_user_namespace"]))
        self.assertIn("session_boundary_trace_complete_rate", failed["v142_F01_session_boundary_trace_records_user_namespace_resolution"])

    def test_snapshot_hash_mismatch_is_detected(self) -> None:
        failed = self._mutate("*F05_session_boundary_snapshot_hashes_reproducible.json", lambda case: case["session_boundary_snapshot"].__setitem__("canonical_boundary_trace_hash", "bogus"))
        self.assertIn("session_boundary_snapshot_hash_reproducible_rate", failed["v142_F05_session_boundary_snapshot_hashes_reproducible"])

    def test_foreign_snapshot_trace_ref_is_detected(self) -> None:
        failed = self._mutate("*B02_user_A_get_action_surface_does_not_include_user_B_refs.json", lambda case: case["session_boundary_snapshot"].setdefault("trace_refs", []).append("local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B02_user_A_get_action_surface_does_not_include_user_B_refs"])

    def test_foreign_boundary_trace_trace_ref_is_detected(self) -> None:
        failed = self._mutate("*F01_session_boundary_trace_records_user_namespace_resolution.json", lambda case: case["session_boundary_trace"].setdefault("trace_refs", []).append("local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_F01_session_boundary_trace_records_user_namespace_resolution"])

    def test_foreign_boundary_step_ref_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["session_boundary_trace"]["boundary_steps"][0]["output_ref"] += ":sess_B_001"
        failed = self._mutate("*F01_session_boundary_trace_records_user_namespace_resolution.json", mutate)
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_F01_session_boundary_trace_records_user_namespace_resolution"])

    def test_foreign_invocation_trace_ref_is_detected(self) -> None:
        failed = self._mutate("*A04_adapter_invocation_preserves_user_session_scope.json", lambda case: case["session_scoped_runtime_invocation"].setdefault("trace_refs", []).append("sess_B_001"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_A04_adapter_invocation_preserves_user_session_scope"])

    def test_foreign_route_handler_result_trace_ref_is_detected(self) -> None:
        failed = self._mutate("*B02_user_A_get_action_surface_does_not_include_user_B_refs.json", lambda case: case["session_scoped_route_handler_result"].setdefault("trace_refs", []).append("local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B02_user_A_get_action_surface_does_not_include_user_B_refs"])

    def test_foreign_expiry_proof_trace_ref_is_detected(self) -> None:
        failed = self._mutate("*E01_expired_session_rejects_action_no_write.json", lambda case: case["session_expiry_and_stale_action_proof"].setdefault("trace_refs", []).append("sess_B_001"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_E01_expired_session_rejects_action_no_write"])

    def test_audit_coverage_omission_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["cross_user_leakage_audit"]["audited_artifact_refs"] = [
                ref for ref in case["cross_user_leakage_audit"]["audited_artifact_refs"] if ref != "session_boundary_snapshot"
            ]
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", mutate)
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_foreign_audit_trace_user_ref_is_detected(self) -> None:
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", lambda case: case["cross_user_leakage_audit"].setdefault("trace_refs", []).append("local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_foreign_audit_trace_session_ref_is_detected(self) -> None:
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", lambda case: case["cross_user_leakage_audit"].setdefault("trace_refs", []).append("sess_B_001"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_audit_local_user_mismatch_is_detected(self) -> None:
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", lambda case: case["cross_user_leakage_audit"].__setitem__("local_user_id", "local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_audit_local_session_mismatch_is_detected(self) -> None:
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", lambda case: case["cross_user_leakage_audit"].__setitem__("local_session_id", "sess_B_001"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_foreign_audit_audited_artifact_ref_is_detected(self) -> None:
        failed = self._mutate("*B05_cross_user_leakage_audit_scans_output_and_refs.json", lambda case: case["cross_user_leakage_audit"].setdefault("audited_artifact_refs", []).append("mem_ns_local_user_B"))
        self.assertIn("cross_user_leakage_absent_rate", failed["v142_B05_cross_user_leakage_audit_scans_output_and_refs"])

    def test_debug_path_is_detected(self) -> None:
        failed = self._mutate("*H01_debug_refs_do_not_expose_filesystem_paths.json", lambda case: case["trace_safe_debug_ref"].__setitem__("debug_ref", "/ssd2/private/session.log"))
        self.assertIn("trace_safe_debug_refs_rate", failed["v142_H01_debug_refs_do_not_expose_filesystem_paths"])

    def test_v141_result_bypass_is_detected(self) -> None:
        failed = self._mutate("*A04_adapter_invocation_preserves_user_session_scope.json", lambda case: case["session_scoped_route_handler_result"].__setitem__("route_handler_result_ref", "rhr_bypassed"))
        self.assertIn("session_scoped_invocation_matches_v141_adapter_rate", failed["v142_A04_adapter_invocation_preserves_user_session_scope"])

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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 52)
            self.assertEqual(adversarial["detected_defect_count"], 52)

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
