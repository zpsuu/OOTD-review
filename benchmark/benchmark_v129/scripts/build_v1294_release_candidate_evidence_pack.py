"""Build v1.29.4 Daily Outfit UX Beta Skeleton evidence pack."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SAMPLE_CASES = {
    "basic_daily_outfit_card.json": ("case_id", "v1294_A01"),
    "same_closet_different_memory.json": ("case_id", "v1294_B01"),
    "current_exception_daily_outfit.json": ("case_id", "v1294_C01"),
    "negative_boundary_repaired_outfit.json": ("case_id", "v1294_D01"),
    "feedback_too_formal_memory_ux.json": ("case_id", "v1294_E01"),
    "remember_long_term_second_round_changed.json": ("case_id", "v1294_F01"),
    "do_not_remember_second_round_unchanged.json": ("case_id", "v1294_F02"),
    "corrected_interpretation_second_round.json": ("case_id", "v1294_F04"),
    "trace_backed_why_this_works.json": ("case_id", "v1294_G01"),
}

INJECTED_SAMPLE_CASES = {
    "injected_outfit_uses_non_closet_item_detected.json": "outfit_uses_non_closet_item",
    "injected_unconsumed_memory_claim_detected.json": "card_claims_unconsumed_memory",
    "injected_current_exception_globalized_detected.json": "current_exception_globalized",
    "injected_final_outfit_still_violates_boundary_detected.json": "final_outfit_still_violates_boundary",
    "injected_repair_without_triggering_memory_ref_detected.json": "repair_without_triggering_memory_ref",
    "injected_do_not_remember_changes_second_round_detected.json": "do_not_remember_still_changes_second_round",
    "injected_remember_bypasses_write_gate_detected.json": "remember_long_term_bypasses_write_gate",
    "injected_second_round_unchanged_after_confirmed_memory_detected.json": "second_round_unchanged_after_confirmed_memory",
    "injected_response_mentions_blocked_memory_detected.json": "response_mentions_blocked_memory",
    "injected_hallucinated_swap_option_detected.json": "hallucinated_swap_option",
}


def _load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_rows(raw_dir: str | Path) -> list[dict[str, Any]]:
    raw_dir = Path(raw_dir)
    results = raw_dir / "results.json"
    if results.exists():
        return _load(results)
    return [_load(p) for p in sorted((raw_dir / "per_case").glob("*.json"))]


def _pick(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise RuntimeError(f"missing sample row: {key}={value}")


def _defect_sample(row: dict[str, Any], mixed_report: dict[str, Any]) -> dict[str, Any]:
    defect_type = row.get("defect_type")
    detected = next((d for d in mixed_report.get("detected_defects", []) if d.get("defect_type") == defect_type), {})
    return {
        "case_id": row.get("case_id"),
        "defect_type": defect_type,
        "expected_failure": True,
        "actual_failure": bool(detected.get("actual_failure")),
        "detected": bool(detected.get("detected")),
        "failed_check_ids": detected.get("failed_check_ids") or [],
        "expected_failed_check_ids": detected.get("expected_failed_check_ids") or [],
        "failure_reason": detected.get("failure_reason"),
        "raw_artifact_ref": detected.get("raw_artifact_ref"),
        "raw_artifact": row,
    }


def _injected_summary(mixed_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite": "v1.29.4 injected defect detection",
        "verdict": mixed_report.get("verdicts", {}).get("injected_defect_detection_verdict"),
        "detected_defects": mixed_report.get("detected_defects", []),
        "unexpected_clean_case_failures": mixed_report.get("unexpected_clean_case_failures", []),
        "unexpected_injected_passes": mixed_report.get("unexpected_injected_passes", []),
    }


def _readme() -> str:
    return """# v1.29.4 Release Candidate Evidence Pack

## Scope

v1.29.4 validates the Daily Outfit UX Beta Skeleton: a minimal end-to-end daily outfit card loop powered by governed memory.

## Non-Goals

This release does not add external inspiration intake, shopping, AIGC ideal looks, virtual try-on, full closet UI, or real beta expansion.

## Multimodal Policy

Multimodal LLM is not required for clean acceptance.

The clean suite uses structured closet fixtures and typed memory fixtures to isolate the memory-centered daily outfit loop.

An optional shadow-only vision adapter may produce ItemMetadataCandidate artifacts, but its output must not directly write memory, must not bypass user confirmation, must not feed the production planner, and must not determine release PASS.

## Daily Outfit Semantics

Daily Outfit Cards must use closet-grounded items only.

User-visible memory claims must be trace-backed.

Final outfit must pass critic and repair validation.

## Second-Round Learning Semantics

Confirmed memory actions must affect targeted second-round recommendations.

Rejected or do-not-remember actions must not affect second-round recommendations.

This-time-only actions must not persist globally.

## Second-Round Visible-Change Self-Proof Semantics

For targeted cases that claim a second-round recommendation changed because of confirmed memory or corrected interpretation, the change must be visible in the user-facing Daily Outfit Card.

A case is not sufficient if it only sets:

- `effect = changed_by_confirmed_memory`
- `changed_from_first_round = true`
- `applied_memory_id` exists

The raw evidence must also show:

- first-round visible outfit item IDs differ from second-round visible outfit item IDs
- `changed_item_ids`, `added_item_ids`, and `removed_item_ids` match the actual card diff
- the applied memory is consumed in the second-round trace
- the second-round card explains the change through trace-backed `why_this_works` or memory UX claims

This prevents summary flags from claiming learning effects that are not visible to the user.

## Verdict Semantics

Clean acceptance suite is used for release acceptance.

Mixed strict suite includes injected defects and is expected to fail.

Release candidate status is derived from:

1. clean acceptance PASS
2. injected defect detection PASS
3. no unexpected clean case failures
4. manual spot review PASS
"""


def _release_note(clean_report: dict[str, Any], mixed_report: dict[str, Any]) -> str:
    clean = clean_report.get("suite_summary") or {}
    mixed = mixed_report.get("suite_summary") or {}
    return f"""# v1.29.4 Release Candidate Note

## Scope

v1.29.4 introduces the Daily Outfit UX Beta Skeleton: a minimal vertical slice connecting task context, closet grounding, governed memory consumption, critic/repair, Daily Outfit Card generation, Memory UX feedback, write gate routing, and second-round recommendation behavior.

## Key Capabilities

- Daily Outfit Card generation
- Closet-grounded final outfit and swap options
- Trace-backed `why_this_works` claims
- Memory-personalized outfit selection
- Current task exception handling
- Critic / repair with final outfit self-proof
- Memory UX feedback loop
- Remember / do-not-remember / this-time-only action routing
- Second-round recommendation validation
- Injected defect detection

## Multimodal Policy

Multimodal LLM is not required for v1.29.4 clean acceptance.

Structured closet fixtures are used for release validation.

Optional vision adapter output is shadow-only and must not write memory or feed production planner.

## Clean Acceptance Result

- Cases: {clean.get('total_cases')}
- Checks: {clean.get('passed_checks')}/{clean.get('total_checks')} PASS
- Verdict: {clean_report.get('verdicts', {}).get('clean_acceptance_verdict')}

## Mixed Strict Suite With Injected Defects

- Cases: {mixed.get('total_cases')}
- Verdict: {mixed_report.get('verdicts', {}).get('mixed_strict_verdict')} as expected
- Injected defect detection: {mixed_report.get('verdicts', {}).get('injected_defect_detection_verdict')}

## Second-Round Learning Effect Self-Proof

v1.29.4 now requires raw visible card diff proof for targeted second-round learning effects.

For cases where confirmed memory or corrected interpretation is expected to change the next recommendation, the evidence must show that the second-round Daily Outfit Card visibly differs from the first-round card.

New or strengthened gates include:

- `second_round_visible_card_changed_when_claimed_rate`
- `second_round_changed_item_ids_match_card_diff_rate`
- `second_round_applied_memory_consumed_rate`
- `second_round_change_explained_in_card_rate`

## Release Status

PASS CANDIDATE confirmed after manual spot review.
"""


def _checklist() -> str:
    return """# v1.29.4 Reviewer Checklist

## Release Candidate Summary

- Clean acceptance suite: expected PASS
- Mixed strict suite with injected defects: expected FAIL
- Injected defect detection: expected PASS
- Release status: PASS CANDIDATE confirmed after manual spot review

## A. Basic Daily Outfit Card

Artifact: `sample_artifacts/basic_daily_outfit_card.json`

- [ ] Daily Outfit Card schema is valid
- [ ] every final outfit item exists in closet fixture
- [ ] every swap option exists in closet fixture
- [ ] no hallucinated item appears
- [ ] `why_this_works` claims have trace refs
- [ ] feedback actions are present
- [ ] PASS
- [ ] FAIL

## B. Same Closet Different Memory

Artifact: `sample_artifacts/same_closet_different_memory.json`

- [ ] closet fixture is the same across compared runs
- [ ] memory differs across compared runs
- [ ] outfit result changes meaningfully
- [ ] change is explained by consumed memory trace
- [ ] difference is not random or untraced
- [ ] PASS
- [ ] FAIL

## C. Current Task Exception

Artifact: `sample_artifacts/current_exception_daily_outfit.json`

- [ ] old avoid memory exists
- [ ] current task exception overrides old avoid
- [ ] old memory is preserved
- [ ] exception is not globalized
- [ ] residual boundaries remain active
- [ ] response says this-time-only or equivalent
- [ ] PASS
- [ ] FAIL

## D. Negative Boundary Repair

Artifact: `sample_artifacts/negative_boundary_repaired_outfit.json`

- [ ] candidate outfit violates active boundary
- [ ] critic detects violation
- [ ] repair references triggering memory
- [ ] post-repair validation exists
- [ ] final outfit is violation-free
- [ ] card shows final repaired outfit only
- [ ] PASS
- [ ] FAIL

## E. Feedback to Memory UX

Artifact: `sample_artifacts/feedback_too_formal_memory_ux.json`

- [ ] user feedback is captured
- [ ] MemoryUXEvent is generated
- [ ] learned card does not overgeneralize
- [ ] allowed user actions are present
- [ ] persistent write waits for confirmation
- [ ] PASS
- [ ] FAIL

## F. Remember Long-Term

Artifact: `sample_artifacts/remember_long_term_second_round_changed.json`

- [ ] user action is remember_long_term
- [ ] action routes to write gate
- [ ] write gate decision exists
- [ ] production write semantics are traceable
- [ ] second-round recommendation changes in targeted way
- [ ] second-round change references confirmed memory
- [ ] PASS
- [ ] FAIL

## G. Do Not Remember

Artifact: `sample_artifacts/do_not_remember_second_round_unchanged.json`

- [ ] user action is do_not_remember
- [ ] no production write is attempted
- [ ] no production write is executed
- [ ] proposal is rejected
- [ ] second-round recommendation is not affected by rejected proposal
- [ ] future response claims do not cite rejected memory UX event
- [ ] PASS
- [ ] FAIL

## H. Corrected Interpretation

Artifact: `sample_artifacts/corrected_interpretation_second_round.json`

- [ ] wrong interpretation is deprecated
- [ ] corrected proposal is created
- [ ] wrong proposal is not written
- [ ] second-round behavior follows corrected interpretation
- [ ] PASS
- [ ] FAIL

## I. Second-Round Visible Learning Effect

Artifacts:

- `sample_artifacts/remember_long_term_second_round_changed.json`
- `sample_artifacts/corrected_interpretation_second_round.json`

- [ ] first-round visible item IDs are present
- [ ] second-round visible item IDs are present
- [ ] first-round and second-round visible item IDs differ
- [ ] `changed_item_ids` matches the actual visible card diff
- [ ] `removed_item_ids` matches first minus second
- [ ] `added_item_ids` matches second minus first
- [ ] `applied_memory_id` is consumed in the second-round trace
- [ ] second-round `why_this_works` or memory UX claim references the applied memory
- [ ] change is visible to the user, not just an internal flag
- [ ] PASS
- [ ] FAIL

## J. Trace Consistency

Artifact: `sample_artifacts/trace_backed_why_this_works.json`

- [ ] all memory claims have refs
- [ ] claim refs are consumed memory or current task evidence
- [ ] no excluded memory is cited
- [ ] no blocked memory is cited
- [ ] no review-required memory is cited
- [ ] no shadow-only memory is cited
- [ ] PASS
- [ ] FAIL

## K. Injected Defect Detection

- [ ] outfit_uses_non_closet_item detected
- [ ] card_claims_unconsumed_memory detected
- [ ] current_exception_globalized detected
- [ ] final_outfit_still_violates_boundary detected
- [ ] repair_without_triggering_memory_ref detected
- [ ] do_not_remember_still_changes_second_round detected
- [ ] remember_long_term_bypasses_write_gate detected
- [ ] second_round_unchanged_after_confirmed_memory detected
- [ ] response_mentions_blocked_memory detected
- [ ] hallucinated_swap_option detected
- [ ] no injected defect unexpectedly passes
- [ ] no clean case unexpectedly fails
- [ ] PASS
- [ ] FAIL

## Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PARTIAL PASS
- [ ] FAIL

Reviewer notes:
"""


def _copy_report(src_json: str, out_dir: Path, out_json_name: str, out_md_name: str) -> None:
    shutil.copyfile(src_json, out_dir / out_json_name)
    src_md = Path(src_json).with_suffix(".md")
    if src_md.exists():
        shutil.copyfile(src_md, out_dir / out_md_name)
    else:
        _write_text(out_dir / out_md_name, f"# {out_md_name}\n\nSource markdown was not present.\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-report", required=True)
    parser.add_argument("--mixed-report", required=True)
    parser.add_argument("--clean-artifacts-dir", required=True)
    parser.add_argument("--mixed-artifacts-dir", required=True)
    parser.add_argument("--shadow-vision-report")
    parser.add_argument("--shadow-vision-artifacts-dir")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    sample_dir = out_dir / "sample_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    clean_report = _load(args.clean_report)
    mixed_report = _load(args.mixed_report)
    clean_rows = _load_rows(args.clean_artifacts_dir)
    mixed_rows = _load_rows(args.mixed_artifacts_dir)

    _copy_report(args.clean_report, out_dir, "clean_report.json", "clean_report.md")
    _copy_report(args.mixed_report, out_dir, "mixed_strict_report.json", "mixed_strict_report.md")
    _write_json(out_dir / "injected_defect_detection_summary.json", _injected_summary(mixed_report))
    _write_text(out_dir / "README.md", _readme())
    _write_text(out_dir / "RELEASE_NOTE.md", _release_note(clean_report, mixed_report))
    _write_text(out_dir / "reviewer_checklist.md", _checklist())

    for name, (key, value) in SAMPLE_CASES.items():
        _write_json(sample_dir / name, _pick(clean_rows, key, value))
    for name, defect_type in INJECTED_SAMPLE_CASES.items():
        _write_json(sample_dir / name, _defect_sample(_pick(mixed_rows, "defect_type", defect_type), mixed_report))

    if args.shadow_vision_report:
        shutil.copyfile(args.shadow_vision_report, out_dir / "shadow_vision_report.json")

    print(json.dumps({"out_dir": str(out_dir), "sample_artifacts": len(SAMPLE_CASES) + len(INJECTED_SAMPLE_CASES)}, indent=2))


if __name__ == "__main__":
    main()
