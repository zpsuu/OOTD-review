"""Independent raw-artifact validator for v1.34 evidence packs.

This validator deliberately ignores clean_report.json verdicts. It recomputes
the v1.34 gates from per-case raw JSON artifacts so release evidence cannot pass
only because an aggregate report says it passed.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


GATES = [
    "promoted_memory_consumption_report_present_rate",
    "promoted_memory_consumed_in_matching_context_rate",
    "promoted_memory_excluded_in_mismatching_context_rate",
    "promoted_memory_context_match_proof_present_rate",
    "promoted_memory_aspect_use_matches_confirmed_aspects_rate",
    "excluded_aspects_not_resurrected_rate",
    "promoted_memory_used_as_soft_bias_only_rate",
    "soft_prefer_not_used_as_hard_filter_rate",
    "daily_outfit_quality_non_regression_with_promoted_memory_rate",
    "promoted_memory_does_not_break_weather_fit_rate",
    "promoted_memory_does_not_break_formality_fit_rate",
    "promoted_memory_does_not_violate_active_avoid_rate",
    "consumption_delta_self_proof_present_rate",
    "targeted_promoted_memory_changes_visible_output_rate",
    "bridge_match_score_not_overstated_by_promoted_memory_rate",
    "response_claim_text_matches_promoted_memory_concept_rate",
    "response_claim_does_not_overstate_promoted_memory_rate",
    "rolledback_promoted_memory_not_consumed_rate",
    "promoted_memory_not_used_for_commerce_targeting_rate",
]

PROHIBITED_DOWNSTREAM_USES = {
    "hard_filter",
    "global_style_identity",
    "commerce_targeting",
    "body_inference",
}

EXCLUDED_ASPECT_FORBIDDEN_TOKENS = {
    "silhouette": ["silhouette"],
    "exact_items": ["exact_item", "item_preference", "sku", "merchant", "product_link"],
    "model_body": ["body", "model_body", "body_inference"],
    "photo_lighting": ["lighting", "photo_lighting"],
    "excessive_sweetness": ["sweetness", "sweet"],
    "gym_coded_style": ["gym", "athletic", "sport"],
    "merchant": ["merchant"],
    "sku": ["sku"],
    "style_identity": ["style_identity", "full_style", "full-style"],
    "luxury_brand_specificity": ["luxury", "brand"],
    "color_palette": ["color_palette", "color"],
}


@dataclass
class GateResult:
    check_id: str
    applicable: bool
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class CaseValidation:
    case_id: str
    artifact_ref: str
    passed: bool
    failed_check_ids: list[str]
    checks: list[GateResult]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _contains_any(value: Any, tokens: list[str]) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower()
    return any(token.lower() in text for token in tokens)


def _memory(case: dict[str, Any]) -> dict[str, Any]:
    return case.get("promoted_memory_atom") or {}


def _packet(case: dict[str, Any]) -> dict[str, Any]:
    return case.get("task_memory_packet") or {}


def _report(case: dict[str, Any]) -> dict[str, Any] | None:
    report = case.get("promoted_memory_consumption_report")
    return report if isinstance(report, dict) else None


def _proof(case: dict[str, Any]) -> dict[str, Any] | None:
    proof = case.get("mismatch_exclusion_proof")
    return proof if isinstance(proof, dict) else None


def _memory_id(case: dict[str, Any]) -> str | None:
    return _memory(case).get("memory_id")


def _consumed_ids(case: dict[str, Any]) -> list[str]:
    return _as_list(_packet(case).get("consumed_promoted_memory_ids"))


def _excluded_ids(case: dict[str, Any]) -> list[str]:
    return _as_list(_packet(case).get("excluded_memory_ids"))


def _rolledback_ids(case: dict[str, Any]) -> list[str]:
    return _as_list(_packet(case).get("rolledback_memory_ids"))


def _request_context(case: dict[str, Any]) -> str | None:
    return _packet(case).get("request_context")


def _memory_contexts(case: dict[str, Any]) -> list[str]:
    return _as_list(_memory(case).get("contexts"))


def _is_consumption_case(case: dict[str, Any]) -> bool:
    return bool(_consumed_ids(case) or _report(case))


def _is_context_mismatch_case(case: dict[str, Any]) -> bool:
    memory_id = _memory_id(case)
    reasons = _packet(case).get("exclusion_reasons") or {}
    return bool(memory_id and memory_id in _excluded_ids(case) and reasons.get(memory_id) == "context_mismatch")


def _is_rollback_case(case: dict[str, Any]) -> bool:
    memory_id = _memory_id(case)
    return bool(memory_id and (memory_id in _rolledback_ids(case) or case.get("rollback_proof")))


def _pass(check_id: str, applicable: bool = True) -> GateResult:
    return GateResult(check_id=check_id, applicable=applicable, passed=True)


def _fail(check_id: str, failures: list[str], applicable: bool = True) -> GateResult:
    return GateResult(check_id=check_id, applicable=applicable, passed=False, failures=failures)


def check_consumption_report_present(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_consumption_report_present_rate"
    if not _is_consumption_case(case):
        return _pass(check_id, applicable=False)
    memory_id = _memory_id(case)
    packet = _packet(case)
    report = _report(case)
    failures: list[str] = []
    if not report:
        failures.append("missing promoted_memory_consumption_report for consumed memory")
    else:
        if report.get("promoted_memory_id") != memory_id:
            failures.append("report promoted_memory_id does not match promoted_memory_atom.memory_id")
        if memory_id not in _as_list(packet.get("consumed_promoted_memory_ids")):
            failures.append("packet does not list promoted memory as consumed")
        trace_refs = report.get("trace_refs") or {}
        if trace_refs.get("task_memory_packet_id") != packet.get("task_memory_packet_id"):
            failures.append("report trace_refs.task_memory_packet_id does not match packet id")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_consumed_in_matching_context(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_consumed_in_matching_context_rate"
    if not _is_consumption_case(case):
        return _pass(check_id, applicable=False)
    memory_id = _memory_id(case)
    report = _report(case)
    failures: list[str] = []
    if memory_id not in _consumed_ids(case):
        failures.append("promoted memory is not in consumed_promoted_memory_ids")
    if memory_id in _excluded_ids(case):
        failures.append("promoted memory is both consumed and excluded")
    if not report:
        failures.append("missing consumption report")
    else:
        context_match = report.get("context_match") or {}
        current_context = (report.get("current_task_context") or {}).get("occasion")
        if context_match.get("matched") is not True:
            failures.append("report context_match.matched is not true")
        if context_match.get("matched_context") not in _memory_contexts(case):
            failures.append("matched_context is not included in memory contexts")
        if current_context != _request_context(case):
            failures.append("report current task context does not match packet request_context")
        if _request_context(case) not in _memory_contexts(case):
            failures.append("packet request_context is outside promoted memory contexts")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_excluded_in_mismatching_context(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_excluded_in_mismatching_context_rate"
    if not _is_context_mismatch_case(case):
        return _pass(check_id, applicable=False)
    memory_id = _memory_id(case)
    proof = _proof(case)
    failures: list[str] = []
    if memory_id in _consumed_ids(case):
        failures.append("context-mismatched memory is still consumed")
    if _report(case):
        failures.append("context-mismatched memory has a consumption report")
    if not proof:
        failures.append("missing mismatch_exclusion_proof")
    else:
        if memory_id not in _as_list(proof.get("excluded_memory_ids")):
            failures.append("mismatch proof does not include promoted memory id")
        if (proof.get("exclusion_reasons") or {}).get(memory_id) != "context_mismatch":
            failures.append("mismatch proof reason is not context_mismatch")
        if (proof.get("context_match") or {}).get("matched") is not False:
            failures.append("mismatch proof context_match.matched is not false")
    if _request_context(case) in _memory_contexts(case):
        failures.append("request_context unexpectedly matches memory contexts")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_context_match_proof_present(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_context_match_proof_present_rate"
    report = _report(case)
    proof = _proof(case)
    failures: list[str] = []
    if report:
        context_match = report.get("context_match") or {}
        if context_match.get("matched") is not True:
            failures.append("consumption report context proof does not mark matched=true")
        if not context_match.get("matched_by"):
            failures.append("consumption report lacks matched_by")
        if not context_match.get("matched_context"):
            failures.append("consumption report lacks matched_context")
    elif proof:
        context_match = proof.get("context_match") or {}
        if context_match.get("matched") is not False:
            failures.append("exclusion proof context_match does not mark matched=false")
        if _memory_id(case) not in _as_list(proof.get("excluded_memory_ids")):
            failures.append("exclusion proof does not include promoted memory")
    else:
        failures.append("neither consumption report nor exclusion proof is present")
    return _fail(check_id, failures) if failures else _pass(check_id)


def _used_surfaces(case: dict[str, Any]) -> list[Any]:
    report = _report(case) or {}
    daily = case.get("daily_outfit_card") or {}
    bridge = case.get("bridge_consumption_report") or {}
    return [
        report.get("used_for"),
        report.get("confirmed_aspects_used"),
        daily.get("used_for"),
        bridge.get("affected_component"),
        bridge.get("used_as"),
    ]


def check_aspect_use_matches(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_aspect_use_matches_confirmed_aspects_rate"
    if not _is_consumption_case(case):
        return _pass(check_id, applicable=False)
    memory = _memory(case)
    report = _report(case) or {}
    failures: list[str] = []
    confirmed = set(_as_list(memory.get("confirmed_aspects")))
    used = set(_as_list(report.get("confirmed_aspects_used")))
    if used != confirmed:
        failures.append(f"confirmed_aspects_used {sorted(used)} does not match memory confirmed_aspects {sorted(confirmed)}")
    used_surfaces = _used_surfaces(case)
    for excluded in _as_list(memory.get("excluded_aspects")):
        tokens = EXCLUDED_ASPECT_FORBIDDEN_TOKENS.get(str(excluded), [str(excluded)])
        if _contains_any(used_surfaces, tokens):
            failures.append(f"excluded aspect {excluded} appears in downstream used surfaces")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_excluded_aspects_not_resurrected(case: dict[str, Any]) -> GateResult:
    check_id = "excluded_aspects_not_resurrected_rate"
    memory = _memory(case)
    surfaces = {
        "used_surfaces": _used_surfaces(case),
        "response_claims": case.get("response_claims"),
        "bridge": case.get("bridge_consumption_report"),
    }
    failures: list[str] = []
    for excluded in _as_list(memory.get("excluded_aspects")):
        tokens = EXCLUDED_ASPECT_FORBIDDEN_TOKENS.get(str(excluded), [str(excluded)])
        if _contains_any(surfaces, tokens):
            failures.append(f"excluded aspect {excluded} is resurrected in downstream artifact")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_soft_bias_only(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_used_as_soft_bias_only_rate"
    if not _is_consumption_case(case):
        return _pass(check_id, applicable=False)
    memory = _memory(case)
    report = _report(case) or {}
    bridge = case.get("bridge_consumption_report") or {}
    failures: list[str] = []
    if memory.get("polarity") != "soft_prefer":
        failures.append("promoted memory polarity is not soft_prefer")
    if report.get("consumption_mode") != "soft_bias":
        failures.append("consumption_mode is not soft_bias")
    if _contains_any(report.get("used_for"), ["hard_filter", "explicit_reject"]):
        failures.append("used_for contains hard filter behavior")
    if bridge and bridge.get("used_as") not in {None, "component_support_signal"}:
        failures.append("bridge does not use promoted memory as component support signal")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_soft_prefer_not_hard_filter(case: dict[str, Any]) -> GateResult:
    check_id = "soft_prefer_not_used_as_hard_filter_rate"
    memory_id = _memory_id(case)
    packet = _packet(case)
    report = _report(case) or {}
    failures: list[str] = []
    if memory_id in _as_list(packet.get("explicit_reject")):
        failures.append("promoted soft_prefer memory appears in explicit_reject")
    if report.get("consumption_mode") == "hard_filter":
        failures.append("soft_prefer memory is consumed as hard_filter")
    if _contains_any(_used_surfaces(case), ["hard_filter", "explicit_reject"]):
        failures.append("downstream surfaces contain hard filter semantics")
    return _fail(check_id, failures) if failures else _pass(check_id)


def _quality(case: dict[str, Any]) -> dict[str, Any]:
    return (case.get("consumption_delta_proof") or {}).get("quality_non_regression") or {}


def check_quality_non_regression(case: dict[str, Any]) -> GateResult:
    check_id = "daily_outfit_quality_non_regression_with_promoted_memory_rate"
    quality = _quality(case)
    daily = case.get("daily_outfit_card") or {}
    delta = case.get("consumption_delta_proof") or {}
    failures: list[str] = []
    if not daily.get("closet_grounded"):
        failures.append("daily outfit is not closet grounded")
    if daily.get("weather_fit") != "pass":
        failures.append("daily outfit weather_fit is not pass")
    if daily.get("formality_fit") != "pass":
        failures.append("daily outfit formality_fit is not pass")
    if daily.get("active_avoid_violations"):
        failures.append("daily outfit has active avoid violations")
    if quality.get("quality_non_regression") is not True:
        failures.append("quality_non_regression is not true")
    if delta.get("harmful_delta") is True:
        failures.append("delta is marked harmful")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_weather(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_does_not_break_weather_fit_rate"
    failures = []
    if (case.get("daily_outfit_card") or {}).get("weather_fit") != "pass":
        failures.append("daily weather_fit is not pass")
    if _quality(case).get("weather_fit") != "pass":
        failures.append("delta quality weather_fit is not pass")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_formality(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_does_not_break_formality_fit_rate"
    failures = []
    if (case.get("daily_outfit_card") or {}).get("formality_fit") != "pass":
        failures.append("daily formality_fit is not pass")
    if _quality(case).get("formality_fit") != "pass":
        failures.append("delta quality formality_fit is not pass")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_active_avoid(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_does_not_violate_active_avoid_rate"
    failures = []
    if (case.get("daily_outfit_card") or {}).get("active_avoid_violations"):
        failures.append("active_avoid_violations is non-empty")
    if _quality(case).get("boundary_violation_free") is not True:
        failures.append("boundary_violation_free is not true")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_delta_self_proof(case: dict[str, Any]) -> GateResult:
    check_id = "consumption_delta_self_proof_present_rate"
    delta = case.get("consumption_delta_proof") or {}
    failures: list[str] = []
    if not delta:
        failures.append("missing consumption_delta_proof")
    else:
        if delta.get("promoted_memory_id") != _memory_id(case):
            failures.append("delta promoted_memory_id does not match promoted memory")
        if not delta.get("baseline_without_promoted_memory") or not delta.get("with_promoted_memory"):
            failures.append("delta lacks baseline or with_promoted_memory")
        if delta.get("delta_is_trace_backed") is not True:
            failures.append("delta_is_trace_backed is not true")
        changed = bool(delta.get("changed_elements"))
        visible = delta.get("visible_output_changed_when_claimed")
        if delta.get("beneficial_delta") and not (changed and visible):
            failures.append("beneficial delta lacks visible changed elements")
        if delta.get("neutral_delta") and (changed or visible):
            failures.append("neutral delta unexpectedly has visible changed elements")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_visible_delta(case: dict[str, Any]) -> GateResult:
    check_id = "targeted_promoted_memory_changes_visible_output_rate"
    delta = case.get("consumption_delta_proof") or {}
    if not delta.get("beneficial_delta"):
        return _pass(check_id, applicable=False)
    failures = []
    if not delta.get("changed_elements"):
        failures.append("beneficial delta has no changed_elements")
    if delta.get("visible_output_changed_when_claimed") is not True:
        failures.append("beneficial delta does not mark visible_output_changed_when_claimed")
    baseline = delta.get("baseline_without_promoted_memory") or {}
    with_memory = delta.get("with_promoted_memory") or {}
    if baseline.get("outfit_items") == with_memory.get("outfit_items") and baseline.get("direction") == with_memory.get("direction"):
        failures.append("beneficial delta baseline and with-memory outputs are identical")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_bridge_score(case: dict[str, Any]) -> GateResult:
    check_id = "bridge_match_score_not_overstated_by_promoted_memory_rate"
    bridge = case.get("bridge_consumption_report")
    if not isinstance(bridge, dict):
        return _pass(check_id, applicable=False)
    failures = []
    before = bridge.get("overall_score_before")
    after = bridge.get("overall_score_after")
    cap = bridge.get("max_allowed_overall_delta")
    if bridge.get("score_inflation_detected") is not False:
        failures.append("score_inflation_detected is not false")
    if not all(isinstance(v, (int, float)) for v in [before, after, cap]):
        failures.append("bridge score fields are not numeric")
    elif after - before > cap + 1e-9:
        failures.append("overall score delta exceeds max_allowed_overall_delta")
    affected = bridge.get("affected_component")
    if affected and affected not in _as_list(_memory(case).get("confirmed_aspects")):
        failures.append("bridge affected_component is not a confirmed aspect")
    if bridge.get("used_as") != "component_support_signal":
        failures.append("bridge used_as is not component_support_signal")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_claim_matches_concept(case: dict[str, Any]) -> GateResult:
    check_id = "response_claim_text_matches_promoted_memory_concept_rate"
    claims = _as_list(case.get("response_claims"))
    if not claims:
        return _pass(check_id, applicable=False)
    alignment = case.get("response_claim_alignment") or {}
    failures = []
    if alignment.get("matches_promoted_memory_concept") is not True:
        failures.append("claim alignment does not match promoted memory concept")
    if alignment.get("claim_refs_subset_of_consumed_memory_ids") is not True:
        failures.append("claim refs are not a subset of consumed memory ids")
    consumed = set(_consumed_ids(case))
    for claim in claims:
        refs = set(_as_list(claim.get("trace_refs")))
        if not refs & consumed:
            failures.append(f"claim {claim.get('claim_id')} lacks consumed memory trace ref")
    if not alignment.get("concept_terms_covered"):
        failures.append("claim alignment lacks concept_terms_covered")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_claim_not_overstated(case: dict[str, Any]) -> GateResult:
    check_id = "response_claim_does_not_overstate_promoted_memory_rate"
    claims = _as_list(case.get("response_claims"))
    if not claims:
        return _pass(check_id, applicable=False)
    alignment = case.get("response_claim_alignment") or {}
    text = " ".join(str(claim.get("text", "")) for claim in claims).lower()
    failures = []
    if alignment.get("overstates_promoted_memory") is True:
        failures.append("claim alignment marks overstatement")
    if any(term in text for term in ["global style", "full style", "always", "hard rule", "shopping target"]):
        failures.append("claim text contains overstated or hard-rule wording")
    for excluded in _as_list(_memory(case).get("excluded_aspects")):
        tokens = EXCLUDED_ASPECT_FORBIDDEN_TOKENS.get(str(excluded), [str(excluded)])
        if any(token.replace("_", " ") in text or token in text for token in tokens):
            failures.append(f"claim text references excluded aspect {excluded}")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_rolledback_not_consumed(case: dict[str, Any]) -> GateResult:
    check_id = "rolledback_promoted_memory_not_consumed_rate"
    if not _is_rollback_case(case):
        return _pass(check_id, applicable=False)
    memory_id = _memory_id(case)
    rollback = case.get("rollback_proof") or {}
    read_after = rollback.get("read_after_rollback") or {}
    failures = []
    if memory_id in _consumed_ids(case):
        failures.append("rolled-back memory is consumed")
    if _report(case):
        failures.append("rolled-back memory has a consumption report")
    if case.get("response_claims"):
        failures.append("rolled-back memory is cited in response claims")
    if memory_id not in _rolledback_ids(case):
        failures.append("packet rolledback_memory_ids does not include promoted memory")
    if read_after.get("memory_present") is not False or read_after.get("status") != "not_found":
        failures.append("rollback read_after_rollback does not prove memory absence")
    if rollback.get("not_consumed_after_rollback") is not True:
        failures.append("rollback proof does not mark not_consumed_after_rollback")
    return _fail(check_id, failures) if failures else _pass(check_id)


def check_no_commerce(case: dict[str, Any]) -> GateResult:
    check_id = "promoted_memory_not_used_for_commerce_targeting_rate"
    packet = _packet(case)
    report = _report(case) or {}
    daily = case.get("daily_outfit_card") or {}
    text = json.dumps(case.get("response_claims") or [], ensure_ascii=False).lower()
    failures = []
    if packet.get("commerce_targeting_memory_ids"):
        failures.append("packet commerce_targeting_memory_ids is non-empty")
    if _contains_any(report.get("used_for"), ["commerce_targeting", "sku", "merchant", "product_link"]):
        failures.append("consumption report used_for contains commerce targeting")
    if _contains_any(daily.get("used_for"), ["commerce_targeting", "sku", "merchant", "product_link"]):
        failures.append("daily card used_for contains commerce targeting")
    if any(term in text for term in ["sku", "merchant", "product link", "commerce targeting"]):
        failures.append("response claim contains commerce targeting wording")
    return _fail(check_id, failures) if failures else _pass(check_id)


CHECKS: list[Callable[[dict[str, Any]], GateResult]] = [
    check_consumption_report_present,
    check_consumed_in_matching_context,
    check_excluded_in_mismatching_context,
    check_context_match_proof_present,
    check_aspect_use_matches,
    check_excluded_aspects_not_resurrected,
    check_soft_bias_only,
    check_soft_prefer_not_hard_filter,
    check_quality_non_regression,
    check_weather,
    check_formality,
    check_active_avoid,
    check_delta_self_proof,
    check_visible_delta,
    check_bridge_score,
    check_claim_matches_concept,
    check_claim_not_overstated,
    check_rolledback_not_consumed,
    check_no_commerce,
]


def validate_case(path: Path, base_dir: Path | None = None) -> CaseValidation:
    artifact = _read_json(path)
    checks = [check(artifact) for check in CHECKS]
    failed = [check.check_id for check in checks if check.applicable and not check.passed]
    ref = str(path if base_dir is None else path.relative_to(base_dir))
    return CaseValidation(
        case_id=artifact.get("case_id") or path.stem,
        artifact_ref=ref,
        passed=not failed,
        failed_check_ids=failed,
        checks=checks,
    )


def _collect_artifacts(result_dir: Path, subset: str) -> list[Path]:
    if subset == "clean":
        pattern_dir = result_dir / "per_case" / "clean"
    elif subset in {"adversarial", "mixed_strict"}:
        pattern_dir = result_dir / "per_case" / subset
    else:
        pattern_dir = result_dir
    return sorted(pattern_dir.glob("*.json"))


def validate_directory(result_dir: Path, subset: str) -> dict[str, Any]:
    paths = _collect_artifacts(result_dir, subset)
    cases = [validate_case(path, result_dir) for path in paths]
    gate_stats: dict[str, dict[str, Any]] = {}
    for gate in GATES:
        applicable = [
            check
            for case in cases
            for check in case.checks
            if check.check_id == gate and check.applicable
        ]
        passed = [check for check in applicable if check.passed]
        failures = [
            {
                "case_id": case.case_id,
                "artifact_ref": case.artifact_ref,
                "failures": check.failures,
            }
            for case in cases
            for check in case.checks
            if check.check_id == gate and check.applicable and not check.passed
        ]
        denominator = len(applicable)
        value = 1.0 if denominator == 0 else len(passed) / denominator
        gate_stats[gate] = {
            "check_id": gate,
            "applicable_cases": denominator,
            "passed_cases": len(passed),
            "value": value,
            "threshold": 1.0,
            "passed": value >= 1.0,
            "failures": failures,
        }
    return {
        "validator": "v1.34.independent.raw_artifact_validator",
        "generated_at": _now_iso(),
        "result_dir": str(result_dir),
        "subset": subset,
        "suite_summary": {
            "total_cases": len(cases),
            "passed_cases": sum(1 for case in cases if case.passed),
            "failed_cases": sum(1 for case in cases if not case.passed),
            "total_checks": len(GATES),
            "passed_checks": sum(1 for gate in gate_stats.values() if gate["passed"]),
            "failed_checks": sum(1 for gate in gate_stats.values() if not gate["passed"]),
        },
        "checks": list(gate_stats.values()),
        "case_results": [
            {
                "case_id": case.case_id,
                "artifact_ref": case.artifact_ref,
                "passed": case.passed,
                "failed_check_ids": case.failed_check_ids,
            }
            for case in cases
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="benchmark/benchmark_v134/results/v134_release_candidate")
    parser.add_argument("--subset", choices=["clean", "adversarial", "mixed_strict"], default="clean")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    report = validate_directory(Path(args.result_dir), args.subset)
    if args.output:
        _write_json(Path(args.output), report)
    print(json.dumps(report["suite_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

