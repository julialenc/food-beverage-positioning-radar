# FINAL OCR/LLM RECONCILIATION AND LOCK

**IMPLEMENT**

We are closing the OCR/LLM preparation workstream. This is the final planned reconciliation, not another exploratory iteration.

Use the existing saved evidence, reconciled review dataset, six-case visual review, and ENERGY_DRINK_COVERAGE_CHECK.md.

## STEP 1 — Apply final decisions

### A. Energy positioning

Julia approves all 106 identifiable energy-drink observations listed in ENERGY_DRINK_COVERAGE_CHECK.md, including five explicit energy preparations.

- Set derived energy positioning to TRUE for these 106 observations.
- This corrects 63 additional observations previously having energy_claim=false.
- Preserve original raw and normalized energy_claim fields unchanged.
- Include provenance and separate ready-to-drink versus preparation formats.
- Keep 25 category conflicts outside the verified segment and 11 unresolved candidates UNKNOWN.
- Do not classify all products containing the word "energy" as energy drinks.
- Preserve independently usable explicit energy-benefit claims on products outside the energy-drink segment.

Make the derived energy-positioning field, not the original undercounting energy_claim flag, the documented input for downstream energy-positioning analysis.

### B. Six visually reviewed cases

Apply Julia's approved interpretations from the photographs:

- 3760049720013: Sans colorant → no_artificial positive.
- 898999000022: THE ORIGINAL → heritage positive.
- 3286010034816: Organic/quality wording does not substantiate naturalness; naturalness positive not usable.
- 3760401290178: YAM Energy → energy positioning positive.
- 0856100003294: protein, plant-based and gluten-free positioning positive; photograph confirms 15 g protein per serving. Respect both regional observations and preserve the original OCR.
- 3256228104335: Riche en vitamine C → fortification-positioning positive, vitamin C. This does not assert that vitamin C was physically added.

Preserve raw model observations and document derived overrides. Apply established equivalent rules to other records only when their evidence meets the same conditions.

Retain Julia's earlier Rude Health decision and exact-barcode vegan salami exclusion.

### C. Final core claim usability

Across PASS and HOLD, apply one reproducible claim-level framework:

- Usable automated positive where the model assertion or approved existing rule is supported by sufficiently reliable evidence.
- Record direct wording support separately from model-only support.
- Preserve claims with inadequate evidence as uncertain; do not automatically reject them because a conservative keyword screen failed.
- Distinguish a documented negative assessment from an undetected or unassessed claim.
- Do not turn UNKNOWN into FALSE.
- Keep core usability independent from operational completion and beverage v6 usability.

Do not introduce new general claim definitions or request manual review of thousands of products.

Preserve the 33 recovered beverage v6 assessments, accepted v6 states and unresolved v6 evidence according to the existing reconciliation rules. No further provider calls.

## STEP 2 — Validate and lock

Create a new versioned OCR/LLM lock directory containing:

1. Final reproducible derived data, including a join-ready Parquet extract.
2. RULES.md — effective transformations, approved exceptions and data contract.
3. CHECK.md — before/after counts, coverage, exclusions, unknowns, residual limitations and integrity checks.
4. Manifest containing source identifiers, hashes, version and lock status.

Requirements:

- Preserve all 12,126 original newly processed observations in the audit population.
- Mark the two vegan salami regional observations excluded from analytical eligibility without deleting their evidence.
- Account separately for the 35 historical dairy reuses. Include them in analytical output only when their saved evidence can be linked unambiguously; otherwise document them as an explicit separate handoff.
- Preserve barcode strings, including leading zeros.
- Preserve raw OCR, raw LLM results, normalized results and original PASS/HOLD/OTHER outcomes.
- Record every derived decision with its provenance.
- No silent replacement of existing claim fields.
- Check uniqueness of record identities, counts, source integrity, schema and serialization.
- Confirm that missing or uncertain claims cannot silently become zero during the subsequent Parquet join.

If every validation invariant passes, mark the OCR/LLM layer **LOCKED**.

If a demonstrable systemic failure prevents a defensible lock, STOP and report the exact blocker. Do not initiate another broad investigation or additional extraction.

Do not modify the master product Parquet database in this task. Produce the locked claims layer and an explicit join contract for the subsequent integration.

No new OCR/LLM calls, no new prompt experiments, no further SKU hunting.

Return the final directory path, lock status, essential counts and any material blockers.

**STOP. The next workstream is integration into the master Parquet dataset and segmentation.**