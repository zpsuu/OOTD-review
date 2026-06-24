from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "benchmark" / "benchmark_v134" / "scripts"
RESULT_DIR = REPO_ROOT / "benchmark" / "benchmark_v134" / "results" / "v134_release_candidate"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_module("validate_v134_release_candidate", SCRIPT_DIR / "validate_v134_release_candidate.py")
adversarial = _load_module("generate_v134_adversarial_cases", SCRIPT_DIR / "generate_v134_adversarial_cases.py")


class V134AcceptanceValidatorTests(unittest.TestCase):
    def test_representative_clean_artifacts_pass(self) -> None:
        representative = [
            "v134_A01_office_daily_low_saturation_memory_consumed_in_office_daily.json",
            "v134_B01_office_daily_memory_excluded_in_date_night.json",
            "v134_F03_promoted_memory_does_not_inflate_overall_match_score.json",
            "v134_G05_rollback_removes_memory_from_later_consumption.json",
        ]
        for name in representative:
            with self.subTest(name=name):
                result = validator.validate_case(RESULT_DIR / "per_case" / "clean" / name, RESULT_DIR)
                self.assertTrue(result.passed, result.failed_check_ids)

    def test_full_raw_adversarial_mutations_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "v134_adversarial"
            adversarial.build(RESULT_DIR, output_dir)
            report = validator.validate_directory(output_dir, "adversarial")

            self.assertEqual(report["suite_summary"]["total_cases"], 10)
            self.assertEqual(report["suite_summary"]["passed_cases"], 0)
            self.assertEqual(report["suite_summary"]["failed_cases"], 10)

            by_case = {case["case_id"]: case for case in report["case_results"]}
            expected = {
                "v134_ADV_I01_promoted_memory_consumed_in_wrong_context": "promoted_memory_consumed_in_matching_context_rate",
                "v134_ADV_I02_color_only_memory_used_as_full_style_preference": "promoted_memory_aspect_use_matches_confirmed_aspects_rate",
                "v134_ADV_I03_soft_prefer_used_as_hard_filter": "soft_prefer_not_used_as_hard_filter_rate",
                "v134_ADV_I04_promoted_memory_causes_weather_regression": "promoted_memory_does_not_break_weather_fit_rate",
                "v134_ADV_I05_promoted_memory_causes_formality_regression": "promoted_memory_does_not_break_formality_fit_rate",
                "v134_ADV_I06_response_claims_unconfirmed_aspect": "response_claim_does_not_overstate_promoted_memory_rate",
                "v134_ADV_I07_rolled_back_promoted_memory_consumed_later": "rolledback_promoted_memory_not_consumed_rate",
                "v134_ADV_I08_promoted_memory_used_as_commerce_targeting": "promoted_memory_not_used_for_commerce_targeting_rate",
                "v134_ADV_I09_bridge_match_score_inflated_by_promoted_memory": "bridge_match_score_not_overstated_by_promoted_memory_rate",
                "v134_ADV_I10_excluded_aspect_resurrected_in_daily_outfit": "excluded_aspects_not_resurrected_rate",
            }
            for case_id, expected_gate in expected.items():
                self.assertIn(case_id, by_case)
                self.assertIn(expected_gate, by_case[case_id]["failed_check_ids"])


if __name__ == "__main__":
    unittest.main()
