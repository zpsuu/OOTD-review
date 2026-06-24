# v1.42 Reviewer Checklist

- [ ] Inspect local user fixture pair and distinct namespaces.
- [ ] Inspect session envelopes for each user.
- [ ] Inspect user A and user B action-surface session wrappers.
- [ ] Inspect same-scope duplicate idempotency reuse.
- [ ] Inspect different-user/session same-key non-reuse.
- [ ] Inspect expired and stale no-write errors.
- [ ] Inspect CrossUserLeakageAudit.
- [ ] Recompute SessionBoundarySnapshot hashes.
- [ ] Inspect adversarial cross-user leakage and debug-ref failures.
