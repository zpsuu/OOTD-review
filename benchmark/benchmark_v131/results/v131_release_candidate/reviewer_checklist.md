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

## E. User Intent Resolution

- [ ] Liked aspects are explicit.
- [ ] Non-core and rejected aspects are not promoted to core.

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

## I. No Production Memory Write

- [ ] production_store_write_attempted is false.
- [ ] production_store_write_executed is false.

## J. Trace Coverage

- [ ] User-visible claims are trace-backed.
- [ ] Shadow proposal evidence refs are complete.

## K. Ambiguous / Inaccessible Input Fallback

- [ ] Ambiguous shares ask clarification.
- [ ] Inaccessible URLs return honest fallback.
- [ ] Platform API absence does not fail the pipeline.

## L. Injected Defect Detection

- [ ] All 12 seeded defects are detected.

## M. Final Manual Review Verdict

- [ ] PASS CANDIDATE confirmed
- [ ] PASS CANDIDATE hold
- [ ] PARTIAL PASS
- [ ] FAIL
