# Final Wave 2 OCR/LLM lock — CHECK

**LOCKED — OCR/LLM preparation layer.** Julia's final decisions and bounded framework are implemented. The next workstream is integration into the master Parquet dataset and segmentation.

## Essential counts

| Population | Records |
|---|---:|
| Newly processed audit population | 12,126 |
| Original PASS / HOLD / OTHER | 8,594 / 3,411 / 121 |
| Historical dairy reuses linked separately | 35 |
| Historical reuses without an unambiguous link | 0 |
| Join extract, including historical and excluded records | 12,161 |
| Salami assignments marked analytically excluded | 2 |
| Retained evidence observations after that exclusion | 12,159 |

Retained evidence eligibility does not certify nutritional validity or claim certainty. Original outcomes remain unchanged.

## Decisions applied

- All **106** approved energy-drink observations have energy_positioning=true, including **five preparations**. This adds **63** segment-based positives compared with their original energy_claim. The 25 category conflicts remain outside verified membership; the 11 unresolved candidates retain unknown membership/positioning.
- **Ten additional observations** outside the verified segment have usable explicit energy-benefit evidence. Across the 12,126 new observations, energy_positioning is **true for 116, documented false for 4,604 and unknown for 7,406**. Unknown is not a negative.
- The six photographed cases are applied in the derived claim namespace. Protein is positive in both regional observations of 0856100003294, with **15 g per serving**. The saved OCR remains 159. The vitamin C decision preserves WILMINE C in OCR and identifies nutrient positioning without asserting physical nutrient addition.
- Rude Health organic=false is retained as the exact variant-naming exception. Both FR and UK/IE assignments of vegan salami 00976534 are retained in the audit and excluded from analytical eligibility.
- **33 recovered v6 assessments** remain recovered. Saved accepted dispositions number 3,327, with two further observations explicitly identity-excluded. There are 173 unresolved beverage v6 observations, including unavailable OCR. Core claims do not erase those limitations.

## Core usability and uncertainty

Across the full 12,161-row join population, the 34 taxonomy fields contain the following derived claim-level states. These are claim observations, not product counts.

| State | Claim observations |
|---|---:|
| Usable automated positive | 8,226 |
| Human-confirmed positive | 9 |
| Documented not detected in assessed evidence | 214,082 |
| Human-confirmed negative | 2 |
| Unknown / insufficient assessment | 190,975 |
| Uncertain natural-flavouring/naturalness interpretation | 112 |
| Excluded identity | 68 |

Positive support is distinguished between direct OCR wording, saved model assessment, approved existing-rule derivation, linked historical assessment and Julia's decisions. A conservative keyword-screen failure does not automatically reject a reliable model assertion. Conversely, non-front, failed, inconsistent or inadequate evidence does not become false.

Usable automated positives are observations of communicated positioning. They remain subject to ordinary extraction error and do not substantiate nutritional accuracy, regulatory compliance, market availability or clinical benefit. Documented negatives describe the assessed evidence rather than verified absence over the full package.

## Historical dairy handoff

All 35 references linked to the exact saved barcode, product and selected image, with successful OCR/LLM records. Where two references were supplied, their claim payloads and OCR agreed. The normalized historical claims and source rows are preserved in historical_reuses.parquet. They remain distinguishable from newly processed observations in every join row.

Historical raw-model responses were not present in these release CSVs. That limitation is explicit. The Canadian-tagged Carrefour pack retains its French-source market limitation. Historical sampling-region metadata remains available in the historical audit. Neither a country tag nor a reusable image proves market-specific distribution.

## Contract and remaining work

Use [claims_join.parquet](claims_join.parquet) and the [join contract in RULES.md](RULES.md#join-contract). Join on exact barcode, region and category strings after explicit receiving-key alignment. Keep original master fields in their namespace. Do not fill null claims or positioning fields with zero.

The master product Parquet database was not changed. Integration must apply the master population's validity gates, retain source-market limitations, respect claim-specific denominators and complete nutritional QA. The two dairy salt discrepancies and US yogurt image-selection comparison remain pending in their respective analytical workstreams. These are recorded residual limitations, not blockers to a defensible evidence-layer lock.

## Validation and integrity

All required invariants passed:

- All 12,126 original rows and every original review field survive physical Parquet serialization.
- Composite identities and record_id are unique across all 12,161 rows.
- All seven regional observations for the six photographed products, both salami assignments and the Rude Health decision have the specified derived values.
- Approved energy membership, preparation counts and 63 additional segment positives reconcile exactly.
- All 33 accepted v6 recoveries and original v6 evidence remain preserved.
- Historical links and source payload agreement passed.
- Nullable boolean schemas and Parquet round trips passed. A physical left-join probe preserved two nulls (one unmatched record and one known unknown) and one explicit false.
- Source hashes were verified before and after generation. [validation.json](validation.json) records source identities, distributions and test results. [manifest.json](manifest.json) seals all final artifact hashes and schema.
- No provider calls, image downloads, prompt edits, canonical evidence edits or master Parquet writes occurred.

**Material blockers — none.** This lock freezes the derived evidence contract, approved exceptions and uncertainty states. No additional extraction or SKU investigation is required before the integration workstream.

