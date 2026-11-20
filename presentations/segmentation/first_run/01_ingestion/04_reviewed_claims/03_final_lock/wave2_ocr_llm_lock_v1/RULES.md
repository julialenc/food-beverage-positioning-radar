# Wave 2 OCR/LLM lock — effective rules and join contract

Version wave2_ocr_llm_lock_v1. Julia's final authorization is preserved verbatim in [final_approval.md](final_approval.md). The [manifest](manifest.json) establishes the lock status, source identities and output hashes. This is the final OCR/LLM preparation layer for subsequent integration and segmentation.

## Files and populations

- **claims_join.parquet** is the join-ready derived extract. Its exact identity is (barcode, region, category). It includes the newly processed observations and unambiguously linked historical dairy reuses, identified by evidence_cohort.
- **new_processed_audit.parquet** preserves all 12,126 newly processed observations, including every original reconciled-review column, full OCR, raw/normalized model outputs, v6 results and original outcomes. Derived evidence and analytical exclusion fields are added.
- **historical_reuses.parquet** separately preserves the 35 reuse identities, complete linked saved rows, source references, historical model/prompt/region and normalized historical claim payloads. Historical raw-model JSON is unavailable and explicitly blank. No new raw response is invented.
- **historical_handoff.json** accounts for any reuse lacking an unambiguous link. It is empty when all 35 links pass.
- **validation.json** and **CHECK.md** document invariants, coverage and residual limitations.

The join includes both analytically excluded salami observations so their evidence remains traceable. analytical_eligible is false only for that exact-barcode exclusion. True means retained in this evidence population; the subsequent integration must also apply the master population's nutrition/category validity rules.

## Core claim framework

Every existing taxonomy flag has a nullable boolean claim_<original_field>, plus state_<original_field> and basis_<original_field>. core_claim_evidence_json preserves the raw and normalized value, decision, evidence basis and any matching OCR wording. This is a derived namespace. Original claim fields remain unchanged in the audit.

1. **Direct wording.** Existing prompt examples are screened against saved OCR, ignoring case, accents and whitespace for matching only. Stored OCR is never rewritten. Reliable good-quality front/mixed context and a normalized completed assessment are required. Ingredient/nutrition/legal clues prevent a direct lexical recovery. A direct cue supports an existing positive. The established equivalent mappings for no-artificial, heritage, explicit protein, gluten-free, plant-based and explicit fortification wording may also recover an omitted flag. This creates no new claim definition.
2. **Model-supported positive.** A raw completed, good-quality front assessment with reusable OCR, a consistent no-claims summary and positive raw/normalized flag is usable automated evidence even when the conservative lexical screen fails. Its basis is SAVED_MODEL_ASSESSMENT. This describes the model assessment of available evidence and retains ordinary model error risk.
3. **Approved existing rules.** Reproduced UK contextual rescue and existing numeric protein implications can support normalized positives. The prior reconciliation's exact rule replay is required. The provenance remains APPROVED_EXISTING_RULE, including metadata-supported origin/free-from observations.
4. **Documented negative.** A false flag from a reliable completed assessment is DOCUMENTED_NOT_DETECTED only when the original summary is consistent and raw/normalized false values agree. The all-false/no_claims_detected=false population has an inconsistent summary and remains unknown except for independently supported positive recoveries. Documented non-detection refers to assessed evidence; it does not certify absence everywhere on the package.
5. **Unknown.** Missing, unreadable, non-front, invalid, incomplete, conflicting or insufficient assessments remain null unless direct evidence or an approved human decision supports a specific claim. A failed conservative phrase search never sets false.
6. **Existing naturalness caution.** A model-only naturalness flag whose saved supporting phrases are natural-flavouring declarations remains uncertain when no explicit naturalness cue is present. This follows the existing prompt's ingredient/flavouring restriction.
7. **Historical positives.** Unambiguously linked completed historical saved assessments may support positives with HISTORICAL_SAVED_ASSESSMENT provenance. Raw model output is not claimed to exist. Only an explicit saved historical no-claims assessment supports historical negatives; otherwise absence remains unknown.

Core completion, original operational PASS/HOLD/OTHER, individual claim usability and independent v6 usability remain separate. Automated evidence does not require human certification of every product. No additional prompts or provider calls are part of this layer.

## Approved human exceptions

The final authorization supersedes the pending outcomes in the six-case review.

| Exact barcode | Derived decision |
|---|---|
| 3760049720013 | no_artificial true from Sans colorant |
| 898999000022 | heritage_claim true from THE ORIGINAL |
| 3286010034816 | natural_claim false for the unsupported naturalness interpretation |
| 3760401290178 | energy_positioning true through approved YAM energy-drink membership |
| 0856100003294 | protein, plant-based and gluten-free true in both regional observations; protein_amount_g=15 and protein_amount_basis=per_serving |
| 3256228104335 | fortification_claim true and Vitamin C positioning; no assertion that vitamin C was physically added |
| 5060120283061 | organic_claim false retained under Julia's variant-naming decision |
| 00976534 | both regional observations analytically excluded as vegan salami; all derived claim values null |

Human claims carry JULIA_PHOTO_DECISION or the prior naming/identity decision as their basis. The source OCR, including WILMINE C and 159, remains exact. The 15 g amount is a photographed per-serving claim and must never be treated as per 100 g.

## Energy positioning

**Use energy_positioning for downstream energy-positioning analysis.** original_energy_claim is retained only as source evidence.

The approved exact registry is in [ENERGY_DRINK_COVERAGE_CHECK.md](../ENERGY_DRINK_COVERAGE_CHECK.md). All 106 observations receive true, including the five preparations. energy_drink_format distinguishes ready_to_drink and preparation. No source energy_claim is overwritten.

The 25 category conflicts have energy_drink_membership=false. The 11 unresolved candidates retain null membership and null energy_positioning. Other unassessed memberships also remain null. An independently usable explicit energy-benefit claim outside the segment can make energy_positioning true. A documented negative can make it false only outside the beverage segment by category or where non-membership is specifically established. Otherwise it remains null.

The vocabulary screen for this explicit energy-benefit route follows the existing energy prompt examples, including the French benefit expressions. Model-only positives without adequate explicit benefit support remain in claim_energy_claim with their model provenance, while energy_positioning remains unknown. This preserves evidence without converting a product descriptor, nutrition-table energy value or unresolved membership into a segment assertion.

## Beverage v6

Preserve the 33 accepted request-ID-only recoveries and all accepted saved content/front states. Unresolved v6 remains unresolved. hydration_positioning and electrolyte_positioning are true only for an accepted detected front assessment, false for an accepted not_detected front assessment, and null for ambiguity, unassessable, failed, unavailable or inapplicable states. The underlying content/front status strings and v6_disposition remain available.

## Join contract

1. Read identifiers as strings and flags as nullable Arrow booleans. Do not convert barcodes to numbers, remove leading zeros, pad identifiers, merge aliases or join solely on barcode.
2. Materialize compatible region/category keys in the receiving data. This layer uses FR, UK-IE, US-CA and snacks, beverages, dairy, cereal. Map receiving codes explicitly, preserving regional assignments and category lineage.
3. Validate the exact composite-key uniqueness before a left join. Use a dedicated claims namespace for collisions with master columns. An unmatched row means missing evidence and must retain null claim values.
4. Preserve evidence_cohort to distinguish new_processed from historical_dairy_reuse. Never add the 35 historical reuses to the 12,126 newly assessed denominator. New source_country_assignments describes the regional processing scope, not the full OFF distribution-country set. Historical country assignments retain the approved US/CA allocation. Source market is not established by an OFF country tag.
5. Exclude analytical_eligible=false rows from segmentation features while preserving them in the audit. A missing eligibility match is not automatically eligible. Apply the master nutrition/category population rules independently.
6. Never fill claim or positioning nulls with zero/false. Use explicit positive, documented-negative and unknown denominators. A zero observed-positive count with no assessable records is missing coverage, not a verified zero prevalence.
7. fortification_claim denotes communicated nutrient positioning. protein_amount_basis and protein_amount_provenance govern numeric interpretation. Claims do not substantiate actual nutritional benefit or clinical suitability.
8. Preserve the source-market limitation of Canadian-tagged Carrefour milk and historical source-region metadata. Linked wording is reusable evidence, not proof of Canadian positioning or distribution.

The master product Parquet database is outside this task. The OCR/LLM layer can be locked with explicit residual uncertainty. Nutritional reconciliation, including the two dairy salt discrepancies, US yogurt image-selection QA, feature/model selection and master integration remain subsequent work.

## Reproduction

[lock_wave2_ocr_llm.py](../../../pipeline/segmentation/lock_wave2_ocr_llm.py) processes bounded batches and verifies source hashes, source-field preservation, exact identities, approved overrides, nullable schemas and physical Parquet round trips. It refuses any version with a manifest. Regeneration requires a new version after lock. The --rebuild-unlocked option is restricted to implementation before a manifest exists.
