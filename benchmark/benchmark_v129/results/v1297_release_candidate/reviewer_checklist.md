# v1.29.7 Reviewer Checklist

## A. Complete Small Closet
- [ ] ClosetBootstrapProfile exists
- [ ] ClosetReadinessReport exists
- [ ] minimum viable closet passes
- [ ] final outfit uses only closet items
- [ ] all required categories present
- [ ] item reliability profiles exist

## B. Missing Shoes Gap Disclosure
- [ ] closet has no shoes
- [ ] final outfit does not invent shoes
- [ ] gap note discloses missing shoes
- [ ] gap note is category-only
- [ ] no product recommendation included
- [ ] quality status is pass_with_disclosure or insufficient, not normal pass

## C. Missing Top / Blocking Category
- [ ] required top missing
- [ ] system does not generate complete outfit
- [ ] readiness_status is insufficient
- [ ] blocking reason is explicit
- [ ] no hallucinated top appears in card text

## D. Low-Confidence Formality
- [ ] item has low formality confidence
- [ ] formal meeting requires reliable formal item
- [ ] low-confidence item excluded
- [ ] card does not claim item is formal enough
- [ ] exclusion reason appears in trace

## E. Low-Confidence Weather
- [ ] rainy task exists
- [ ] item has low weather confidence or dry-only metadata
- [ ] item excluded from rain-safety claim
- [ ] uncertainty note or gap disclosure exists if needed

## F. Vision Candidate
- [ ] vision_candidate item exists
- [ ] item is not user-confirmed
- [ ] item is not used in clean planner
- [ ] item may appear only as candidate / needs confirmation
- [ ] no production memory write from vision candidate

## G. Swap Reliability
- [ ] visible swaps are closet-grounded
- [ ] visible swaps pass task guardrails
- [ ] unreliable swaps are hidden
- [ ] hidden swaps have hidden_reason
- [ ] swap claim refs are trace-backed

## H. Memory + Closet Reliability
- [ ] memory preference does not force unreliable item
- [ ] current task exception does not override missing category
- [ ] current task exception requires item reliability support
- [ ] memory claim does not depend on unconfirmed item metadata

## I. Injected Defect Detection
- [ ] missing shoes hallucination detected
- [ ] low-confidence formality misuse detected
- [ ] low-confidence weather misuse detected
- [ ] vision candidate misuse detected
- [ ] gap suggestion treated as closet item detected
- [ ] memory forces unreliable item detected
- [ ] insufficient closet normal pass detected

## J. Scenario Self-Proof
- [ ] each sample artifact has `scenario_preconditions`
- [ ] each scenario's expected preconditions are non-empty and scenario-appropriate
- [ ] `scenario_preconditions.satisfied == true`
- [ ] proof refs point to actual raw fields
- [ ] current-exception cases include current task exceptions
- [ ] missing-category cases include actual missing required categories
- [ ] gap cases include actual gap notes / disclosures / suggestions
- [ ] swap cases include visible swaps or hidden swaps as appropriate
- [ ] repair cases include pre-repair issue and repair report
- [ ] insufficient closet cases use `closet_insufficient_notice`, not normal Daily Outfit Card

## Final Manual Review Verdict
- [ ] PASS CANDIDATE confirmed
- [ ] PARTIAL PASS
- [ ] FAIL

Reviewer notes:
