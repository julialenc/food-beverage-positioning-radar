# Energy-drink coverage — bounded CHECK

**PENDING JULIA'S APPROVAL.** Prepared 12 November 2026. Julia's analytical decision is that genuine energy drinks communicate energy positioning, including energy in a product name. This CHECK proposes a derived indicator; no classifications or claim fields have changed.

## Scope and identification

Reviewed the **3,535 processed beverage region/product observations**, using the [derived review CSV](wave2_claims_reconciliation_v1/reconciled_review.csv) and preserved Wave 2 OFF identity/category fields. The latter came from the [September release working snapshot](../../data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/release_work.db), through 3,501 exact-barcode indexed lookups. Query-plan verification showed index searches; there was no database-wide scan or production-database access.

Selection never used energy_claim. A broad category/name/OCR screen produced 399 candidates, including ordinary coffee, tea and cola. The focused review retained 142 observations with energy-drink category/type evidence or a corroborated energy-brand/product identity:

- **106 identifiable energy-drink observations**, representing 105 exact barcode strings. Category plus product identity and compatible OCR were assessed together. Explicit energy-drink wording or a concordant named energy-product identity could establish membership even where OFF omitted the energy-drink tag.
- **25 category conflicts**, with saved identity/OCR instead indicating sports hydration, electrolyte beverages, protein/nutritional shakes or another format. These are outside the proposed membership set; this is not an executed category correction.
- **11 unresolved candidates**, where saved evidence is insufficient or the sports-fuel/energy boundary remains unclear.

Examples deliberately left outside include PRIME Hydration, Powerade, Gatorade, BodyArmor sports drinks, Electrolit and plain Liquid I.V. hydration mixes, plus protein shakes. Capri-Sun Monsteralarm was not selected as an energy drink merely because its name contains Monster. Ordinary energy values, caffeine-free tea and guarana alone did not establish membership.

Membership is a bounded saved-evidence assessment, not verification of market distribution or of the photograph. Poor OCR does not erase a clearly identified energy product from the source population. Conversely, a category tag or an opaque brand name alone was insufficient. Borderline candidates remain unresolved below.

## Coverage by region

Raw and normalized counts are identical within the 106-member set. Missing includes an absent/unavailable flag; there are no such cases in this identifiable set.

| Region | Identifiable observations | Raw true | Raw false | Raw missing | Normalized true | Normalized false | Normalized missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| FR | 15 | 10 | 5 | 0 | 10 | 5 | 0 |
| UK/IE | 38 | 16 | 22 | 0 | 16 | 22 | 0 |
| US/CA | 53 | 17 | 36 | 0 | 17 | 36 | 0 |
| **Total** | **106** | **43** | **63** | **0** | **43** | **63** | **0** |

The existing flag captures 40.6% of this identifiable segment. The 63 false values comprise **44 original PASS and 19 HOLD** observations. They must not all be interpreted as assessed negatives.

The 106 include **101 ready-to-drink observations and five explicit energy preparations**. Preparations are Holy Energy 4260715291179 (FR), Celsius 0889392080629 and 889392080612, Alani energy sticks 0810030515098, and G Fuel 0696859110023 (US/CA). Keep their format explicit. The approved beverage scope permits preparations, but Julia may prefer a ready-to-drink-only segment view.

## Why the energy flag is false

These exclusive evidence groups total 63. They describe saved-response patterns rather than proven causal diagnoses.

| Pattern | FR | UK/IE | US/CA | Total | Interpretation |
|---|---:|---:|---:|---:|---|
| Raw core not completed | 4 | 5 | 9 | 18 | Context/status conflict or unreadable assessment; false is not a reliable negative |
| Completed, good OCR, explicit energy-drink wording | 1 | 3 | 2 | 6 | Clear gap against Julia's intended segment-positioning definition |
| Completed, good OCR, energy word/fragment without complete type phrase | 0 | 8 | 13 | 21 | Product-name/benefit restriction, inconsistent interpretation and OCR fragmentation overlap |
| Completed, good OCR label, identity clearer in source fields than OCR | 0 | 4 | 5 | 9 | Source membership can be identifiable while the photographed text is incomplete |
| Completed but poor/partial OCR | 0 | 2 | 7 | 9 | Readability limits extraction; quality labels are model-reported |
| **Total** | **5** | **22** | **36** | **63** | |

All 63 saved OCR texts are within 2,000 characters. The known core OCR input cap therefore does not explain these omissions.

Representative exact observations:

| Barcode / region | Saved evidence | Finding |
|---|---|---|
| 3760401290178 / FR | YAM “energy”; source category identifies an energy drink | Already true. Julia's intended membership rule supports its energy positioning |
| 0180854000101 / US/CA | “Red Bull” and “ENERGY DRINK”; completed, good OCR | Raw and normalized false despite clear energy-product identity |
| 5061013967235 / UK/IE | “Relentless” and “ENERGY DRINK”; completed, good OCR | Same gap |
| 2098765839100 / UK/IE | “ENERGY DRINK”; completed, good OCR | Same gap |
| 4260715291179 / FR | “Next-Gen Energy Drink”, “MIX WITH 0.5L WATER” | False on an explicit energy preparation |
| 0070847002901 / US/CA | Monster Energy identity, OCR includes “ENERGY” | False; naming/category membership and benefit extraction diverge |
| 3608330157455 / FR | “TAURINE DRINK”; energy-drink category | Raw non-applicable status despite front context; retain separate extraction uncertainty |

The six completed/good-OCR observations with an explicit drink-type phrase are Holy Energy 4260715291179 (FR); Relentless 5061013967235, REV UP 2098765839100 and Relentless 5060466510296 (UK/IE); Red Bull 0180854000101 and 0611269174526 (US/CA).

## Frozen instructions and cause

Current prompt bytes matched all three recorded frozen regional prompt hashes in [runtime_configuration.json](run_06b_main_readiness_v1/runtime_configuration.json).

- **FR** explicitly maps energy-benefit expressions, but says a bare “boisson énergisante” product descriptor requires consumer-benefit context. That is narrower than Julia's newly stated segment-positioning decision. [FR Energy section, lines 255–262](../../pipeline/vision_prompts/current/prompt_v5_fr.txt#L255)
- **US/CA** lists “SLOW RELEASE,” “4 HOURS OF STEADY ENERGY,” “STEADY ENERGY,” “ACTIVGO” and “MORE POWER.” It does not explicitly instruct that every genuine energy drink counts. [English Energy section, lines 172–174](../../pipeline/vision_prompts/current/prompt_v5_en.txt#L172)
- **UK/IE** includes energy_claim in the output schema but has no dedicated energy interpretation rule. Its mapped-rule section specifies other benefits. [UK schema, line 26](../../pipeline/vision_prompts/current/prompt_uk_test_09.2026_final.txt#L26) · [Mapped rules, lines 143–156](../../pipeline/vision_prompts/current/prompt_uk_test_09.2026_final.txt#L143)
- **Stage 10** supplies no energy-drink membership rescue. It can clear booleans for non-front/unreadable status. UK contextual rescue handles free-from, fat and origin rather than energy membership. [Stage 10, lines 376–388](../../pipeline/stages/stage_10_extract_pack_claims.py#L376) · [UK rescue, lines 494–530](../../pipeline/stages/stage_10_extract_pack_claims.py#L494)

**Conclusion.** The primary structural mismatch is the target concept: segment-level energy positioning versus extraction of particular benefit wording. Inconsistent LLM interpretation and imperfect OCR add gaps. Misleading OFF categories create a separate risk of over-inclusion. No raw/normalized energy flag changes occurred in the 106 records, so postprocessing is not the direct source of their measured true/false gap. Saved evidence cannot attribute every false flag specifically to prompt restriction or model omission.

## Smallest proposed adjustment

Create a separate, provenance-bearing **energy_positioning** indicator after Julia approves the membership treatment:

1. TRUE when saved evidence establishes genuine energy-drink membership, even when Energy belongs to the product name.
2. Also TRUE for an independently usable energy-benefit claim on another beverage, such as an explicitly positioned tea. The original energy_claim alone is not proof of that claim's usability.
3. Preserve UNKNOWN where membership and benefit evidence are insufficient. Do not turn unresolved or failed extraction into an assessed negative.
4. Retain a basis field distinguishing segment identity, accepted benefit wording, both and unresolved. Keep preparation format and all original OCR/core/v6 statuses separate.

**Quantified effect.** Under the proposed 106-member scope, 43 records already have normalized energy_claim=true and **63 additional observations would receive positive derived energy positioning**—FR 5, UK/IE 22, US/CA 36. This does not promote their core or v6 assessments to PASS. Under a ready-to-drink-only scope, membership is 101 and the increment is **60**, with three false-flagged preparations deferred.

Across all processed beverages, normalized energy_claim=true occurs in 114 observations. Seventy-one are outside this identified segment set; their benefit usability was not re-reviewed here. Therefore this CHECK quantifies the membership increment, not a newly approved total of usable energy-benefit claims.

## Unresolved membership and category boundaries

| Barcode / region | Saved identity | Why unresolved |
|---|---|---|
| 5070003278527 / UK/IE | Mai chai magic cherry charged energiser | Energiser/tea positioning does not by itself settle energy-drink membership |
| 5027492002423 / UK/IE | High 5 sports nutrition energy drnk | Sports carbohydrate-fuel versus energy-drink segment boundary |
| 5060809670274 / UK/IE | Voom Fusion Gel | Gel name versus energy-drink OCR and sports-fuel wording |
| 5060895748796 / UK/IE | nom | Generic identity and fragmentary “ENERG FOCUS”; no corroborating saved brand |
| 810014530314 / US/CA | Peach Paradise / accelerator | Sparse identity-only OCR; category corroboration insufficient for this bounded decision |
| 0849429002420 / US/CA | Watermelon / Zevia | Brand has multiple beverage types; sparse poor OCR |
| 0850062286108 / US/CA | Solar Mango / abeo energy | No saved OCR |
| 0810175040547 / US/CA | Cotton Candy / aimuu | No OCR and weak source identity |
| 850004884850 / US/CA | Pink Lotus Plant Power Drink | Saved wording does not establish the segment |
| 0786162080004 / US/CA | Vitaminwater Tropical Citrus Energy | Enhanced-water/energy boundary; retain separately from verified membership |
| 0028435600428 / US/CA | BUBBL'R antioxidant sparkling water | Poor OCR and functional-water/energy boundary |

These are 11 observations in addition to the 106, not hidden negatives. Category conflicts comprise 2 FR, 2 UK/IE and 21 US/CA observations. Neither group is automatically added to the proposed indicator.

## Exact proposed membership for reproducibility

Each identifier below is an exact CSV barcode string, including leading zeros. Membership counts are region/product observations.

**FR — 15**

`8710398521743 3760401290178 8480000282637 3608330157455 8711900013831 3770007351012 5060166690984 3608330145650 20917661 9002490211028 90415760 611508171378 9002490290276 4260715291179 8851123229883`

**UK/IE — 38**

`5449000265104 889392001549 0889392001709 5900552065760 5054267010727 4088600157474 90446412 5061013967235 5900552079613 5054267009288 90456978 5061013944199 5054267007086 5060232812029 4088600541075 9002490260224 90456596 96126080 5060947541795 5056784900031 2098765839100 5060608742172 5908260257248 5060947545816 5020379174572 5000382108870 5061013944250 5060947549715 0059780908846 90446085 5060639122899 8855790001759 9002490248420 7340131602647 5060466510296 5060896625669 90493102 5060896628974`

**US/CA — 53**

`0180854000101 0070847002901 61500017820 0070847030157 701648010115 0850029843313 0611269991000 0850057175295 0196633831446 0810193920944 0889392080629 0889392010145 0196633831439 5056784900185 0611269174526 51000201768 0842595119831 0842595138214 889392080612 1220000250147 0611269546019 0840344600272 0810030515098 0070847899884 70847811169 0196633831415 0889392001709 0070847811268 0611269818994 0070847012474 0810085812203 0889392001761 0850059374078 0850069104672 0070847894087 20190330 0696859110023 0818094005746 0842595139266 0842595109368 842595135060 0070847898405 0051000196200 611269331240 196633831422 0850014216368 0070847899488 0070847029120 810175041650 0889392010015 0070847020905 4560292291372 0070847900856`

**CHECK.** Exactly one CHECK file created. Saved records and indexed source lookups only; no provider calls, image downloads, new classification experiment, taxonomy edits or dataset changes. No classifications are applied. Julia's approval is requested for the proposed membership scope, separate preparation reporting and derived indicator.

