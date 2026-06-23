# v1.31 Reviewer Checklist

## A. Intake Event Schema

- [ ] Every case has an InspirationIntakeEvent.
- [ ] source_type is explicit.

## B. Storage Policy / Privacy / Redistribution

- [ ] storage_policy exists for each content ref.
- [ ] raw external image is not present in public evidence.
- [ ] redistribution_allowed is false for external screenshots/images.

## C. Visual Signal Candidate

- [ ] Visual signals are candidates, not confirmed memory.
- [ ] Uncertain fields are flagged.
- [ ] High-risk model/body/identity inference is suppressed.

## D. Text / URL Metadata Candidate

- [ ] URL metadata-only cases ask for screenshot or clarification.
- [ ] Link title alone does not create memory proposal.
- [ ] Metadata-only URL cases do not resolve color palette or silhouette as liked aspects.
- [ ] Metadata-only URL cases keep color, silhouette, exact items, and material in not_confirmed_aspects.

## E. User Intent Resolution

- [ ] Liked aspects are explicit.
- [ ] Non-core and rejected aspects are not promoted to core.
- [ ] Color-only and date-night cases include user-statement-specific scenario preconditions.

## F. Ideal Direction Candidate

- [ ] Ideal candidate requires confirmation.
- [ ] Downstream use excludes production memory write.

## G. Bridge Shadow Run

- [ ] Bridge run is shadow-only.
- [ ] Reality outfit uses only closet items.
- [ ] Gap is disclosed when closet cannot match inspiration.
- [ ] One-item step is category-level only.

## H. Shadow Memory Proposal

- [ ] status is shadow_only.
- [ ] production_write_allowed is false.
- [ ] requires_user_confirmation is true.
- [ ] Date-night-only intent maps to date/date_night shadow contexts, not office_daily.
- [ ] Color-only intent creates a color/palette-only shadow proposal.
- [ ] Shadow proposals exclude unconfirmed aspects from the user intent.
- [ ] Key sample artifacts match their corresponding per-case raw artifacts.

## I. No Production Memory Write

- [ ] production_store_write_attempted is false.
- [ ] production_store_write_executed is false.
- [ ] Fallback-only cases have memory_ux_confirmation_prompt = null.
- [ ] Fallback-only cases use clarification_prompt, not memory confirmation.

## J. Trace Coverage

- [ ] User-visible claims are trace-backed.
- [ ] Shadow proposal evidence refs are complete.
- [ ] High-risk inference cases include high-risk-specific scenario preconditions.
- [ ] Uncertain visual cases include uncertain-field-specific scenario preconditions.

## K. Ambiguous / Inaccessible Input Fallback

- [ ] Ambiguous shares ask clarification.
- [ ] Inaccessible URLs return honest fallback.
- [ ] Platform API absence does not fail the pipeline.
- [ ] Clarification prompt actions do not include remember_later_shadow, remember_long_term, remember_for_context, or use_for_this_bridge_only.
- [ ] Clarification prompt selected action is not a remember action.

## L. Injected Defect Detection

- [ ] All 12 seeded defects are detected.

## M. Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PASS CANDIDATE hold
- [ ] PARTIAL PASS
- [ ] FAIL
