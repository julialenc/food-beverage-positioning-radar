# Claim-state denominators — read-only CHECK

Prepared 12 November 2026 against the **LOCKED** wave2_ocr_llm_lock_v1 layer. Data, rules and lock status are unchanged.

## What the two counts measure

The [join extract](wave2_ocr_llm_lock_v1/claims_join.parquet) contains **12,161 distinct product-region observations** with unique barcode/region/category keys. These comprise **12,126 newly processed observations and 35 linked historical dairy reuses**. No unselected master products are present. The two excluded salami observations remain in this audit population.

Each row has **34 taxonomy fields**. Therefore the claim-state denominator is **12,161 × 34 = 413,474 individual field assessments**. It excludes the no_claims_detected summary field, energy_positioning and the independent beverage v6 fields.

| Locked state | Claim observations |
|---|---:|
| DOCUMENTED_NOT_DETECTED | **214,082** |
| UNKNOWN | **190,975** |
| USABLE_AUTOMATED_POSITIVE | 8,226 |
| HUMAN_CONFIRMED_POSITIVE | 9 |
| HUMAN_CONFIRMED_NEGATIVE | 2 |
| UNCERTAIN | 112 |
| EXCLUDED | 68 |
| **Total** | **413,474** |

The 214,082 documented negatives occur across **6,528 distinct product-region observations**, including 6,519 newly processed observations and nine historical reuses. They are saved negative assessments of the available evidence, not certification that a claim is absent everywhere on the package.

The 190,975 UNKNOWN fields occur across **5,646 distinct product-region observations**. Total null-valued claim fields are **191,155**, because the additional 112 UNCERTAIN fields and 68 identity-excluded fields also serialize as null. An implementation must not interpret a null solely as state UNKNOWN.

## UNKNOWN by underlying cause

The following is a mutually exclusive row-level hierarchy, counted only for fields whose locked state is UNKNOWN. Causes are assigned from the original raw status/context/quality, saved OCR availability, original technical issue codes and the implemented eligibility gates. A row can have usable positive fields alongside its unknown fields.

| Primary cause | UNKNOWN fields | Distinct product-region observations |
|---|---:|---:|
| Raw non-completed front/mixed result, historically normalized to completed | **94,709** | **2,790** |
| Raw completed/good/front result, but inconsistent no-claims summary prevents negative support | **61,275** | **1,806** |
| Raw completed/good mixed panel; negative gate requires front_of_pack | **9,799** | **293** |
| Non-front ingredient/legal/nutrition/price context | **9,724** | **286** |
| Raw completed, but poor/partial/missing quality | **4,760** | **140** |
| Uncertain context | **3,842** | **113** |
| No reusable saved OCR | **3,638** | **107** |
| Invalid panel-context output | **1,870** | **55** |
| Historical reuse lacks sufficient raw negative-assessment evidence | **833** | **26** |
| Technical/incomplete core processing after OCR | **476** | **14** |
| Explicit content-filter rejection | **34** | **1** |
| Completed/good/front record with a claim-level raw/normalized disagreement | **15** | **15** |
| **Total** | **190,975** | **5,646** |

“Raw non-completed” is different from failed transport. These 2,790 observations have saved responses and front/mixed context, but their raw extraction status contradicts that context. The locked layer preserves that distinction.

The quality and processing counts above are primary causes, not estimates of actual photographic quality. Context and status causes can also carry quality warnings. The 112 separate UNCERTAIN fields concern natural-flavouring/naturalness interpretation and are outside this UNKNOWN table.

## Is the negative policy driving UNKNOWN?

**Yes, a large portion is rule-driven despite otherwise completed saved processing.** It is not evidence of equivalent amounts of OCR/LLM failure.

- **94,709 fields (49.6% of UNKNOWN)** arise from raw status contradictions that normalize to completed. Of these, **94,592 have raw=false and normalized=false**. The gate refuses to treat those false values as documented negatives because the raw response says extraction was non-applicable.
- **75,849 fields (39.7%) across 2,254 observations** have both raw and normalized completed status. These include the summary, mixed-panel, quality and field-disagreement groups above.
- Within that completed population, **71,074 fields (37.2% of all UNKNOWN), across 2,099 observations**, are blocked by the summary-consistency or mixed-panel negative gates despite good model-reported quality.
- Overall, **170,558 fields (89.3%) across 5,044 observations** have normalized completed status. This combines the status-conflict population and the raw-completed population.

The **61,275-field summary group** consists of:

| Saved contradiction | UNKNOWN fields | Observations |
|---|---:|---:|
| No raw positive flag, but no_claims_detected=false | **60,535** | **1,784** |
| Raw positive flag present, but no_claims_detected=true | **740** | **22** |

The 1,784-row group is larger than the earlier 1,754 priority cohort because the latter also required no normalized positive flags; existing normalization/rule additions distinguish the other 30 rows.

In the summary group, **61,258 of 61,275 UNKNOWN fields are raw=false and normalized=false**. The mixed-panel group similarly contains **9,498 false/false UNKNOWN fields**. This demonstrates that much of UNKNOWN reflects the locked rule's refusal to substantiate negatives, rather than missing field values.

**Interpretation.** The negative-assessment policy is materially more conservative than operational completion. Whether it is overly conservative for a particular analytical denominator is a policy judgment; these counts do not establish that every false/false field is a defensible negative. The contradictory-summary group includes genuinely omitted claims already identified in the bounded reviews. A blanket conversion would conceal those exceptions.

This CHECK identifies that denominator effect without changing the approved gates. Integration can preserve the locked states faithfully. Analysts must not describe the 190,975 UNKNOWN fields as unprocessed products or failed OCR/LLM calls, or combine them with documented negatives when reporting claim prevalence.

## Distinguishing never-selected products after the join

The master Parquet integration has not run. The locked schema and contract support the distinction, and the saved lock validation includes a left-join probe that preserves unmatched and known-unknown nulls separately.

Use a left join on exact **barcode, region, category**, retaining the claims-layer record_id and evidence_cohort:

| Post-join condition | Meaning |
|---|---|
| Claims record_id is null | No matching observation in this locked layer |
| record_id exists; evidence_cohort=new_processed | One of the 12,126 newly processed observations |
| record_id exists; evidence_cohort=historical_dairy_reuse | One of the 35 historical reuses |
| record_id exists; a claim is null with state UNKNOWN/UNCERTAIN | Selected/matched evidence, with that claim unresolved |
| record_id exists; analytical_eligible=false | Preserved evidence for an excluded salami assignment |

An unmatched record is **not selected or represented in this layer**. It is not proof of never having been processed in any historical project run. Establishing lifetime processing history would require a different evidence source and is outside this CHECK.

Do not fill null booleans with false. Keep the matched/unmatched marker independent of per-field states. Preserve explicit state EXCLUDED separately. This retains the distinction between population coverage, completed processing and claim usability.

## Integrity and conclusion

The counts were recomputed from the locked Parquet evidence and original audit fields. Composite-key and product-region distinct counts both equal 12,161. Every cause count sums to 190,975; all 34-field states sum to 413,474.

The report was written outside the lock directory. All locked output hashes were checked against [manifest.json](wave2_ocr_llm_lock_v1/manifest.json). The status remains LOCKED. Only this CHECK file was created.

**Finding.** Both requested numbers are field-level counts within selected evidence. A substantial majority of UNKNOWN is tied to completed/normalized-completed records under conservative negative-evidence gates. Master coverage and matched claim uncertainty must therefore remain separate denominators during integration.

