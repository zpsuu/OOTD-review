# v1.34 Reviewer Checklist

## A. Matching Context Consumption

- [ ] Promoted memory appears in TaskMemoryPacket.
- [ ] Current context matches memory contexts.
- [ ] Context match proof exists.
- [ ] Consumed memory id is trace-backed.

## B. Mismatching Context Exclusion

- [ ] Promoted memory excluded in wrong context.
- [ ] Exclusion reason is context_mismatch.
- [ ] Response does not cite excluded memory.

## C. Aspect Narrowing

- [ ] Color-only memory affects color only.
- [ ] Silhouette-only memory affects silhouette only.
- [ ] Unconfirmed aspects are not resurrected.

## D. Soft Bias vs Hard Filter

- [ ] consumption_mode is soft_bias.
- [ ] Promoted memory is not used as explicit reject.
- [ ] Soft preference yields to weather, formality, and reliability.

## E. Quality Non-Regression

- [ ] No weather regression.
- [ ] No formality regression.
- [ ] No boundary regression.
- [ ] No repetition regression.

## F. Bridge Use

- [ ] Bridge uses promoted memory at component level.
- [ ] Match score is not inflated.
- [ ] Gap diagnosis remains specific.

## G. Multi-Day / Rollback

- [ ] Rolled-back promoted memory is not consumed later.
- [ ] Response does not cite rolled-back memory.

## H. Response Claims

- [ ] Claim text matches promoted memory concept.
- [ ] No full-style overclaim from color-only memory.
- [ ] No commerce targeting claim.
