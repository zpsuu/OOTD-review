# v1.37 Reviewer Checklist

- [ ] RuntimeTrace stage order is complete.
- [ ] StateSnapshot hashes are reproducible and stable.
- [ ] HandoffProof ids match across stages.
- [ ] No production write occurs before confirmation and promotion gate.
- [ ] Consumption requires promoted memory.
- [ ] Feedback and rollback rebuild future packets safely.
- [ ] v1.36 replay, independent validation, adversarial detection, sample consistency, and report consistency pass.
