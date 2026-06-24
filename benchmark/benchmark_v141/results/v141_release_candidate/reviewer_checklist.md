# v1.41 Reviewer Checklist

- [ ] Inspect route registry bindings.
- [ ] Inspect GET daily outfit handler invocation/result/trace.
- [ ] Inspect GET action surface handler invocation/result/trace.
- [ ] Inspect POST this_time_only no-write handler proof.
- [ ] Inspect remember_for_context write-gated handler proof.
- [ ] Inspect duplicate submission idempotency replay.
- [ ] Inspect expired/stale and unsupported safe errors.
- [ ] Recompute runtime adapter snapshot hashes.
- [ ] Inspect golden contract replay against v1.40.
- [ ] Inspect adversarial report-source bypass failure.
