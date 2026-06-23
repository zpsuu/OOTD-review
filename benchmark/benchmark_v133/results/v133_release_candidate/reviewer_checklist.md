# v1.33 Reviewer Checklist

## A. Promotion Eligibility

- [ ] Eligibility report exists for every candidate.
- [ ] Only narrow low-risk contextual soft_prefer candidates are eligible.
- [ ] Global, metadata-only, high-risk, rejected, and do-not-remember candidates do not write.

## B. Promotion Plan Aspect Narrowing

- [ ] Plan concept matches confirmed aspects.
- [ ] Unconfirmed and rejected aspects are excluded.
- [ ] Color-only plans remain color-only.

## C. Write Gate Routing

- [ ] Allowed writes route through ProductionMemoryWriteGate.
- [ ] Blocked writes do not attempt production store writes.
- [ ] Review-required decisions include actionable payloads.

## D. Conflict Moderation

- [ ] Soft conflicts use moderated translation.
- [ ] Hard conflicts require review or user confirmation.
- [ ] Unmoderated conflict cannot write.

## E. Promoted MemoryAtom Integrity

- [ ] MemoryAtom is contextual, trace-backed, and bounded.
- [ ] No raw external content, product links, SKU, merchant, body inference, or lighting preference is written.

## F. Rollback Proof

- [ ] Allowed writes include audit snapshot and rollback proof.

## G. Context-Safe Downstream Consumption

- [ ] Matching contexts consume promoted memory as soft bias.
- [ ] Mismatched contexts exclude promoted memory.
- [ ] Promoted memory is not used as a hard filter.

## H. Injected Defect Detection

- [ ] Direct write bypass detected.
- [ ] Color-only full-style memory detected.
- [ ] Global write detected.
- [ ] High-risk write detected.
- [ ] Wrong-context consumption detected.
