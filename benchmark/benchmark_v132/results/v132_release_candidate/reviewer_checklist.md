# v1.32 Reviewer Checklist

## A. Confirmation Card

- [ ] Generated only for sufficient ideal candidate
- [ ] Not generated for metadata-only fallback
- [ ] Not generated for ambiguous fallback
- [ ] Candidate liked aspects have trace refs
- [ ] Not-confirmed aspects listed

## B. Confirmed Candidate

- [ ] Requires user action
- [ ] Confirmed aspects match user action
- [ ] Rejected / unconfirmed aspects excluded
- [ ] Candidate remains shadow-only
- [ ] No production memory write

## C. Scope Selection

- [ ] Date-night maps to date_night
- [ ] Office maps to office_daily
- [ ] Unknown scope asks clarification
- [ ] Global selection remains deferred / shadow-only

## D. Conflict Handling

- [ ] Conflict with active memory detected
- [ ] Moderated translation present for soft conflict
- [ ] Hard conflict asks confirmation
- [ ] Conflict does not create production memory

## E. Dedup / Clustering

- [ ] Compatible candidates cluster
- [ ] Incompatible candidates do not merge
- [ ] Cluster remains shadow-only

## F. Bridge After Confirmation

- [ ] Bridge uses confirmed aspects only
- [ ] Bridge does not use rejected aspects
- [ ] Reality outfit remains closet-grounded
- [ ] Gap diagnosis matches confirmed concept

## G. Injected Defects

- [ ] metadata-only fallback with confirmation card detected
- [ ] color-only confirmation creating full-style candidate detected
- [ ] date-night mapped to office_daily detected
- [ ] do-not-remember creating candidate detected
- [ ] conflict ignored detected
- [ ] production write detected
