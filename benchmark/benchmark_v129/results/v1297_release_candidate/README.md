# v1.29.7 Release Candidate Evidence Pack

## Scope

v1.29.7 focuses on Closet Bootstrapping & Item Reliability.

This release verifies that Daily Outfit can operate on small or incomplete closets without hallucinating items, over-trusting weak metadata, or hiding missing categories.

## Release Status

v1.29.7 Closet Bootstrapping & Item Reliability is PASS CANDIDATE confirmed.

Clean acceptance suite passes 46/46 cases and 44/44 checks.
Scenario preconditions are present and raw-proven.
Non-vacuous gates are included in clean_report.
G03/G04 current exception cases trigger real current-task exception conditions.
D-series gap cases include actual gap/missing-category triggers.
E-series repair cases include pre-repair reliability issues or no-reliable-alternative proof.
F-series swap reliability cases include visible swaps, hidden swaps, and no-swap reasons.
Insufficient closet cards use closet_insufficient_notice instead of partial Daily Outfit Cards.
Manual spot review passes.

## Non-Goals

- No external inspiration intake
- No full multimodal closet ingestion dependency
- No shopping / product recommendations
- No full UI / beta launch
- No virtual try-on
- No ideal-reality bridge

## Key Guarantees

- Final outfits use only closet items.
- Gap suggestions are not treated as closet items.
- Missing required categories are disclosed or marked insufficient.
- Low-confidence metadata is not used for high-confidence claims.
- Unconfirmed vision candidates are not used in clean planner path.
- Swap options are reliability-checked.
- Memory preference cannot force unreliable item use.
- Current task exception cannot override missing closet category.

## Scenario Self-Proof Semantics

v1.29.7 requires every benchmark scenario to prove that its raw trigger preconditions are present.

A case cannot pass only because output fields look valid. If a scenario claims to test missing categories, current task exceptions, low-confidence items, gap disclosure, swap reliability, repair behavior, or insufficient closet handling, the raw artifact must include a `scenario_preconditions` block with proof references.

The aggregate report enforces this with non-vacuous scenario gates such as:

- `scenario_precondition_satisfied_rate`
- `scenario_precondition_proof_refs_present_rate`
- `no_vacuous_clean_case_pass_rate`
- `current_exception_case_has_exception_precondition_rate`
- `missing_category_case_has_missing_category_precondition_rate`
- `gap_case_has_gap_disclosure_precondition_rate`
- `swap_case_has_visible_swap_precondition_rate`
- `hidden_swap_case_has_hidden_swap_precondition_rate`
- `repair_case_has_pre_repair_issue_rate`
- `insufficient_card_does_not_present_partial_outfit_as_daily_outfit_rate`

## Insufficient Card Semantics

When the closet is insufficient and `can_generate_grounded_outfit=false`, the card must be a `closet_insufficient_notice`, not a partial Daily Outfit Card.

## Per-Case Archive

Full raw per-case artifacts are included under `per_case/clean` and `per_case/mixed_strict`.
