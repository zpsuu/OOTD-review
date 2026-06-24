from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v143" / "scripts"
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


builder = _load_module("build_v143_release_candidate_evidence_pack", SCRIPT_DIR / "build_v143_release_candidate_evidence_pack.py")
validator = _load_module("validate_v143_release_candidate", SCRIPT_DIR / "validate_v143_release_candidate.py")
generator = _load_module("generate_v143_adversarial_cases", SCRIPT_DIR / "generate_v143_adversarial_cases.py")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V143ProductConversationRuntimeLoopValidatorTests(unittest.TestCase):
    def _build(self, tmp: str) -> Path:
        result_dir = Path(tmp) / "v143_release_candidate"
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
            self.assertEqual(clean["suite_summary"]["passed_cases"], 49)
            self.assertEqual(clean["suite_summary"]["passed_checks"], 23)
            self.assertEqual(adversarial["suite_summary"]["passed_cases"], 0)
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 38)
            self.assertEqual(adversarial["detected_defect_count"], 38)
            self.assertTrue(sample["passed"], sample["failures"])
            self.assertTrue(consistency["passed"], consistency["failures"])

    def test_turn_result_bypass_is_detected(self) -> None:
        failed = self._mutate("*A04_turn_results_match_v142_runtime_outputs.json", lambda case: case["conversation_turn_runtime_results"][0].__setitem__("source_v142_route_handler_result_ref", "ssrhr_bypassed"))
        self.assertIn("turn_result_matches_v142_runtime_output_rate", failed["v143_A04_turn_results_match_v142_runtime_outputs"])

    def test_missing_card_lifecycle_is_detected(self) -> None:
        failed = self._mutate("*B01_get_daily_outfit_offers_trace_backed_action_cards.json", lambda case: case.__setitem__("conversation_action_card_lifecycles", []))
        self.assertIn("action_card_lifecycle_complete_rate", failed["v143_B01_get_daily_outfit_offers_trace_backed_action_cards"])

    def test_boundary_audit_self_foreign_ref_is_detected(self) -> None:
        failed = self._mutate("*G05_conversation_boundary_audit_self_is_scoped.json", lambda case: case["conversation_boundary_audit"].setdefault("trace_refs", []).append("conv_B_001"))
        self.assertIn("conversation_boundary_audit_self_scoped_rate", failed["v143_G05_conversation_boundary_audit_self_is_scoped"])

    def test_snapshot_hash_mismatch_is_detected(self) -> None:
        failed = self._mutate("*A05_conversation_loop_snapshot_hashes_reproducible.json", lambda case: case["conversation_loop_snapshot"].__setitem__("canonical_turn_sequence_hash", "bogus"))
        self.assertIn("conversation_loop_snapshot_hash_reproducible_rate", failed["v143_A05_conversation_loop_snapshot_hashes_reproducible"])

    def test_visible_forbidden_terms_are_detected(self) -> None:
        failed = self._mutate("*H05_no_raw_review_evidence_internal_path_sensitive_commerce_or_aigc_terms.json", lambda case: case["conversation_turn_runtime_results"][0]["user_visible_claims"][0].__setitem__("text", "raw_evidence_refs merchant SKU AIGC"))
        self.assertIn("visible_claims_trace_backed_rate", failed["v143_H05_no_raw_review_evidence_internal_path_sensitive_commerce_or_aigc_terms"])

    def test_same_scope_duplicate_new_result_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            case["conversation_idempotency_replay_proofs"][0]["same_scope_reused"] = False
            case["conversation_idempotency_replay_proofs"][0]["duplicate_action_result_ref"] = "fresh_result"
        failed = self._mutate("*C01_same_turn_duplicate_submission_reuses_result.json", mutate)
        self.assertIn("same_scope_duplicate_reuses_result_across_turns_rate", failed["v143_C01_same_turn_duplicate_submission_reuses_result"])

    def test_different_conversation_reuse_is_detected(self) -> None:
        def mutate(case: dict) -> None:
            proof = case["conversation_idempotency_replay_proofs"][0]
            proof["different_scope_reused"] = True
            proof["different_scope_action_result_ref"] = proof["canonical_action_result_ref"]
        failed = self._mutate("*C03_same_raw_key_different_conversation_does_not_reuse_result.json", mutate)
        self.assertIn("different_scope_duplicate_does_not_reuse_result_rate", failed["v143_C03_same_raw_key_different_conversation_does_not_reuse_result"])

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
            self.assertEqual(adversarial["suite_summary"]["failed_cases"], 38)
            self.assertEqual(adversarial["detected_defect_count"], 38)

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
