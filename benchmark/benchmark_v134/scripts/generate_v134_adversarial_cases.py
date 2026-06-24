"""Generate full raw adversarial v1.34 artifacts from clean cases.

The existing mixed_strict artifacts are minimal defect records. These adversarial
artifacts are stronger: each one starts from a complete clean raw artifact and
mutates the exact fields a downstream regression would corrupt.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_SOURCE_DIR = Path("benchmark/benchmark_v134/results/v134_release_candidate")
DEFAULT_OUTPUT_DIR = Path("benchmark/benchmark_v134/results/v134_adversarial_validation")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_clean(source_dir: Path, scenario_fragment: str) -> dict[str, Any]:
    matches = sorted((source_dir / "per_case" / "clean").glob(f"*{scenario_fragment}*.json"))
    if not matches:
        raise FileNotFoundError(f"No clean v1.34 artifact matched {scenario_fragment!r}")
    return _read_json(matches[0])


def _memory_id(case: dict[str, Any]) -> str:
    return case["promoted_memory_atom"]["memory_id"]


def _prepare_case(source_dir: Path, scenario_fragment: str, adversarial_id: str, defect_type: str) -> dict[str, Any]:
    case = copy.deepcopy(_load_clean(source_dir, scenario_fragment))
    case["source_clean_case_id"] = case.get("case_id")
    case["case_id"] = f"v134_ADV_{adversarial_id}_{defect_type}"
    case["adversarial_defect_type"] = defect_type
    case["expected_failure"] = True
    return case


def _wrong_context_consumption(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "A01_office_daily_low_saturation_memory_consumed_in_office_daily", "I01", "promoted_memory_consumed_in_wrong_context")
    case["task_memory_packet"]["request_context"] = "date_night"
    case["promoted_memory_consumption_report"]["current_task_context"] = {"occasion": "date_night", "context_tags": ["date_night"]}
    case["promoted_memory_consumption_report"]["context_match"] = {
        "matched": True,
        "matched_by": "occasion",
        "matched_context": "date_night",
    }
    case["consumption_report"] = copy.deepcopy(case["promoted_memory_consumption_report"])
    return case, ["promoted_memory_consumed_in_matching_context_rate"]


def _color_used_as_full_style(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "C01_color_only_memory_affects_color_only", "I02", "color_only_memory_used_as_full_style_preference")
    for report_key in ["promoted_memory_consumption_report", "consumption_report"]:
        case[report_key]["confirmed_aspects_used"] = ["color_palette", "silhouette"]
        case[report_key]["used_for"].extend(["silhouette_preference", "full_style_identity"])
    case["daily_outfit_card"]["used_for"].extend(["silhouette_preference", "full_style_identity"])
    return case, [
        "promoted_memory_aspect_use_matches_confirmed_aspects_rate",
        "excluded_aspects_not_resurrected_rate",
    ]


def _soft_prefer_hard_filter(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "D05_soft_preference_not_used_as_explicit_reject", "I03", "soft_prefer_used_as_hard_filter")
    memory_id = _memory_id(case)
    case["task_memory_packet"]["explicit_reject"] = [memory_id]
    for report_key in ["promoted_memory_consumption_report", "consumption_report"]:
        case[report_key]["consumption_mode"] = "hard_filter"
        case[report_key]["used_for"].append("hard_filter")
    return case, [
        "promoted_memory_used_as_soft_bias_only_rate",
        "soft_prefer_not_used_as_hard_filter_rate",
    ]


def _weather_regression(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "E02_promoted_memory_ignored_when_it_would_break_weather_fit", "I04", "promoted_memory_causes_weather_regression")
    case["daily_outfit_card"]["weather_fit"] = "fail"
    quality = case["consumption_delta_proof"]["quality_non_regression"]
    quality["weather_fit"] = "fail"
    quality["quality_non_regression"] = False
    case["consumption_delta_proof"]["harmful_delta"] = True
    return case, [
        "daily_outfit_quality_non_regression_with_promoted_memory_rate",
        "promoted_memory_does_not_break_weather_fit_rate",
    ]


def _formality_regression(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "E03_promoted_memory_ignored_when_it_would_break_formality_fit", "I05", "promoted_memory_causes_formality_regression")
    case["daily_outfit_card"]["formality_fit"] = "fail"
    quality = case["consumption_delta_proof"]["quality_non_regression"]
    quality["formality_fit"] = "fail"
    quality["quality_non_regression"] = False
    case["consumption_delta_proof"]["harmful_delta"] = True
    return case, [
        "daily_outfit_quality_non_regression_with_promoted_memory_rate",
        "promoted_memory_does_not_break_formality_fit_rate",
    ]


def _response_overclaims(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "H02_response_does_not_claim_full_style_from_color_memory", "I06", "response_claims_unconfirmed_aspect")
    case["response_claims"] = [
        {
            "claim_id": "claim_adv_overclaim",
            "text": "I know your full style is relaxed structured city dressing now.",
            "trace_refs": [_memory_id(case), case["task_memory_packet"]["task_memory_packet_id"]],
        }
    ]
    case["response_claim_alignment"]["claim_text"] = case["response_claims"][0]["text"]
    case["response_claim_alignment"]["matches_promoted_memory_concept"] = False
    case["response_claim_alignment"]["overstates_promoted_memory"] = True
    return case, [
        "response_claim_text_matches_promoted_memory_concept_rate",
        "response_claim_does_not_overstate_promoted_memory_rate",
    ]


def _rolledback_consumed(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "G05_rollback_removes_memory_from_later_consumption", "I07", "rolled_back_promoted_memory_consumed_later")
    memory_id = _memory_id(case)
    case["task_memory_packet"]["consumed_promoted_memory_ids"] = [memory_id]
    case["task_memory_packet"]["excluded_memory_ids"] = []
    case["task_memory_packet"]["exclusion_reasons"] = {}
    case["rollback_proof"]["not_consumed_after_rollback"] = False
    case["response_claims"] = [
        {
            "claim_id": "claim_adv_rolledback",
            "text": "I used your rolled-back low-saturation memory.",
            "trace_refs": [memory_id],
        }
    ]
    return case, ["rolledback_promoted_memory_not_consumed_rate"]


def _commerce_targeting(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "A01_office_daily_low_saturation_memory_consumed_in_office_daily", "I08", "promoted_memory_used_as_commerce_targeting")
    memory_id = _memory_id(case)
    case["task_memory_packet"]["commerce_targeting_memory_ids"] = [memory_id]
    for report_key in ["promoted_memory_consumption_report", "consumption_report"]:
        case[report_key]["used_for"].append("commerce_targeting")
    case["daily_outfit_card"]["used_for"].append("commerce_targeting")
    return case, ["promoted_memory_not_used_for_commerce_targeting_rate"]


def _bridge_score_inflated(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "F03_promoted_memory_does_not_inflate_overall_match_score", "I09", "bridge_match_score_inflated_by_promoted_memory")
    bridge = case["bridge_consumption_report"]
    bridge["overall_score_after"] = bridge["overall_score_before"] + bridge["max_allowed_overall_delta"] + 0.20
    bridge["score_inflation_detected"] = False
    return case, ["bridge_match_score_not_overstated_by_promoted_memory_rate"]


def _excluded_aspect_resurrected(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    case = _prepare_case(source_dir, "C01_color_only_memory_affects_color_only", "I10", "excluded_aspect_resurrected_in_daily_outfit")
    case["daily_outfit_card"]["used_for"].append("silhouette_preference")
    case["bridge_consumption_report"]["affected_component"] = "silhouette"
    return case, [
        "excluded_aspects_not_resurrected_rate",
        "bridge_match_score_not_overstated_by_promoted_memory_rate",
    ]


MUTATORS: list[Callable[[Path], tuple[dict[str, Any], list[str]]]] = [
    _wrong_context_consumption,
    _color_used_as_full_style,
    _soft_prefer_hard_filter,
    _weather_regression,
    _formality_regression,
    _response_overclaims,
    _rolledback_consumed,
    _commerce_targeting,
    _bridge_score_inflated,
    _excluded_aspect_resurrected,
]


def build(source_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    adversarial_dir = output_dir / "per_case" / "adversarial"
    adversarial_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": "v1.34",
        "generated_at": _now_iso(),
        "source_result_dir": str(source_dir),
        "output_dir": str(output_dir),
        "cases": [],
    }
    for mutator in MUTATORS:
        case, expected_failed = mutator(source_dir)
        case["expected_failed_check_ids"] = expected_failed
        path = adversarial_dir / f"{case['case_id']}.json"
        _write_json(path, case)
        manifest["cases"].append(
            {
                "case_id": case["case_id"],
                "artifact_ref": str(path.relative_to(output_dir)),
                "source_clean_case_id": case["source_clean_case_id"],
                "defect_type": case["adversarial_defect_type"],
                "expected_failed_check_ids": expected_failed,
            }
        )
    _write_json(output_dir / "ADVERSARIAL_MANIFEST.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    build(Path(args.source_result_dir), output_dir)
    print(f"Built adversarial cases under {output_dir}")


if __name__ == "__main__":
    main()

