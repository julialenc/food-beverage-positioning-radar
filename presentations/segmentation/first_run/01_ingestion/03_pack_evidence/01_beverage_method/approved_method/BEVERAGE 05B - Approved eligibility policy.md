# BEVERAGE 05B — Approved beverage eligibility policy

**Decision date:** 24 October 2026. **Status:** Three general eligibility policies approved; the 121 case dispositions below are proposed for Julia's review and have not been applied.

## Approved policies

1. **Culinary coconut milk and cream.** Exclude only when the existing evidence establishes culinary use. Retain explicit drinking, cocktail or beverage preparations. Hold uncertain intended use. A can, concentration, powder format or high fat content does not establish culinary use.
2. **Multipurpose ingredients.** Retain cacao, seeds, powders, syrups, sweeteners and similar ingredients only when available evidence explicitly establishes intended beverage preparation. Otherwise record `HOLD — intended use unresolved`. Lack of evidence for beverage use is not, by itself, proof of non-beverage status.
3. **Product/image identity conflicts.** Record `TEMPORARY HOLD — identity verification required` when exact barcode, source identity or image attribution conflicts remain unresolved. Neither a possibly wrong name nor a possibly wrong image establishes a case decision. Exact GTIN and image verification is a separate task.

These are analytical eligibility policies for the current shortlist review, not automatic ingestion or category rules. A case-specific exclusion still requires Julia's confirmation before any shortlist or dataset change.

## Reconciliation with BEVERAGE 05A

The [decision register](beverage_05b_decision_register.csv) contains **exactly the existing 121 suspected records**. It preserves all 23 BEVERAGE 05A fields, including exact barcode strings and leading zeros, region, selected/reserve role, group/country/component, original product and image URLs, URL provenance, original classification, evidence, source category evidence and approval status. Added columns record the applicable policy, proposed disposition, rationale, unresolved reason, the original clear-proposal membership and the pending case-specific approval status. Import `barcode` as text in Excel.

| Proposed disposition | Selected | Reserve | Total |
|---|---:|---:|---:|
| `EXCLUDE — evidence sufficient` | 33 | 4 | 37 |
| `RETAIN — beverage evidence sufficient` | 0 | 0 | 0 |
| `HOLD — intended use unresolved` | 60 | 9 | 69 |
| `TEMPORARY HOLD — identity verification required` | 15 | 0 | 15 |
| **Total** | **108** | **13** | **121** |

The earlier **40 “Clearly non-beverage” cases remain identifiable as a distinct BEVERAGE 05A proposal set**, not 40 Julia-approved exclusions. Of these, 37 now have evidence-sufficient *proposed* exclusions and three have temporary identity holds: `710069312227` (blank source name/tomato-juice category versus a photographed tomato can), `940207` and `00940207` (source brand versus photographed retailer conflict; exact barcode strings remain separate). The other 51 likely cases remain intended-use holds. The 30 earlier ambiguous cases become 18 intended-use holds and 12 identity holds. No case in this suspected-only register has enough existing evidence to propose retention; BEVERAGE 05A's 106 visually reviewed legitimate beverage/preparation counterexamples were already outside this 121-case set and are not reclassified here.

### Unresolved cases for review

| Hold reason | Cases | Review need |
|---|---:|---|
| Coconut intended use | 47 | Establish culinary-only versus explicit drinking/cocktail preparation from existing case evidence or a separately authorized review. |
| Multipurpose ingredient or syrup intended use | 18 | Establish explicit beverage preparation; includes cacao, seeds, powders, agave and other dual-use syrups. |
| Cooking-wine intended use | 2 | Confirm whether the product is culinary-only. |
| Sports-gel beverage scope | 1 | Resolve whether the existing isotonic gel evidence supports a beverage preparation. |
| Category and intended use | 1 | `8003496004646`: tomato bottle remains sauce-versus-drink uncertain. |
| Identity or image provenance | 15 | Verify exact barcode/product/image association; includes `710069312227`, `940207`, `00940207`, `22592007014`, `3415587401015`, `00233040`, `00802864`, `01649147`, `29051045`, `4056489238102`, `5060425283810`, `9348207000616`, `0022592007014`, `0075720481279` and `12345678`. |

The register identifies every held case and retains its original evidence and source links. No new image inspection or classification outside the 121 records was performed.

## Potential RUN 06B quota effect — scenarios only

The frozen shortlist has **3,563 selected beverages**, **593 beverage reserves** and **63 existing project-wide unfilled slots** (37 beverages, 26 other categories). The 13 suspect reserves are withheld from theoretical replacement capacity pending review, leaving 580 technically available but not case-validated reserves. Matching is restricted to the same approved sampling group, exact country cell and sampling component. These calculations do not promote reserves or modify quotas.

| Hypothetical scenario | Additional selected unavailable | Beverage demand incl. existing 37 | Maximum matching reserve capacity | Beverage gaps left | Project gaps left incl. other-category 26 |
|---|---:|---:|---:|---:|---:|
| Only 37 proposed evidence-sufficient exclusions approved | 33 | 70 | 24 | 46 | 72 |
| All 121 suspects unavailable pending review | 108 | 145 | 83 | 62 | 88 |

With no replacement, the 33 selected proposed exclusions would raise the project shortfall from 63 to **96**; matching technical reserves could theoretically reduce it to **72**. For the first scenario, matching capacity is FR 9/9, UK+IE 13/13, US+CA C1 1/24, C2 1/11 and C3 0/13 (capacity/demand). Identity and intended-use holds are **not** applied now; the second row is only a review sensitivity. Technical reserve availability does not establish image usability or paid-run readiness.

## Source freeze and boundary

| Frozen input | SHA256 |
|---|---|
| `beverage_05a_v1/suspected_products_review.csv` | `67f6a5cea0ab549efaf6e18111eda153066d7d50609deaab79cc1ad9a5f94b3b` |
| `beverage_05a_v1/audit_tables.json` | `00b07c96200ffffda35ef9a021b52489e7da33c4b0784bde45a9cbba7b180e39` |
| `BEVERAGE 05A - Non-beverage shortlist audit.md` | `44d8a71c46d011b0a691278d2f7df22aa45601d740af6bc94e21bbdb4180d956` |
| `run_06b_v2/selected_manifest.csv` | `ce98cbb88120543819756459c253d56d69bc71abd3deb5271ce24e1eddcacdbb` |
| `run_06b_v2/reserve_manifest.csv` | `753ce5b29e599e50e37c4f4a0a522d37a9c81cc3015312839f5c3ff67b6a6d89` |
| `run_06b_v2/unfilled_slots.csv` | `f7455b1f1a641f55aab3c9353ec73ff67b41a073c8540e1c00f38c4874d466c5` |

The new register SHA256 is `c47bb949f24b5748e3c90c078dc3d68bbebad7dfd6a288d108962c33283083c5`. Every original BEVERAGE 05A field round-tripped unchanged for all 121 exact barcode–region cases. The frozen RUN 06B selected/reserve manifests, source/category data, segmentation, Streamlit, Wave 3, OCR, prompts and historical classifications remain unchanged. No exclusion, hold or reserve promotion has been implemented. **STOP for Julia's case-specific review.**
