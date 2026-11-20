# BEVERAGE FINAL — Current-wave implementation and lock

**Final decision date:** 25 October 2026. **Approved and locked by Julia.** The current-wave eligibility and saved-OCR integration lock of 24 October is preserved below. RUN 06B full-run integration, readiness verification and paid execution remain separately gated.

## Final approved execution architecture

**BEVERAGE METHODOLOGY AND MODEL SELECTION — LOCKED, 25 OCTOBER 2026.**

| Stage | Approved model / implementation | Scope and routing |
| --- | --- | --- |
| Azure OCR | Existing Azure OCR implementation | All selected products; preserve full captured OCR text. Reuse successful evidence/configuration checkpoints rather than repeating OCR for v6. |
| Regional core LLM | **GPT-4.1-nano** | **All categories: snacks, cereals, dairy and beverages.** Preserve the existing approved regional prompts, legacy 34-flag taxonomy, historical core methodology and conditional dairy context-review/re-extraction logic. |
| Independent additional v6 LLM | **GPT-4.1-mini**, `emerging_benefits_v3` | **Beverages only**, after successful OCR, using that same complete saved OCR. Execute both regional core and v6 for every selected beverage with successful OCR; core no-claim outcomes and core LLM failures must not suppress v6. No v6 for snacks, cereals or dairy, and no additional OCR request for v6. |

**GPT-4.1-mini is ONLY for v6. Base extraction for beverages remains GPT-4.1-nano.** The verified four-case mini deployment was `gpt-4.1-mini-v6-test`, model `gpt-4.1-mini-2025-04-14`. Its bounded confirmation configuration is evidence of that test, not an authorized full-run configuration.

## Final v6 methodology

The approved implementation is deterministic wording candidates → one mini interpretation call → deterministic validation and status derivation. [Candidate extraction and derivation](../../pipeline/vision_ops/emerging_benefits_v3.py) reuse the existing frozen wording patterns and preserve [benefit definitions v1.0.0](beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json). The [v3 prompt](../../pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v3.txt), interpretation schema and [contract hashes](run_06b_v6_contract_v3.json) remain versioned.

- Extract exact OCR wording candidates with deterministic IDs, phrases and offsets. Mini interprets their meaning, target-product attribution and context using the full saved OCR. Every candidate must be accounted for; candidate IDs are distinct from supplied product-context metadata fact IDs.
- Derive independent hydration and electrolyte assessments from validated interpretations. Keep content detection separate from front-pack attribution and preserve the four states: `detected`, `not_detected`, `ambiguous`, `unassessable`. Unknown front scope does not invalidate supported content detection.
- Accept no unsupported positive or negative. Exact quotations/offsets and evidence identity are checked deterministically; unresolved target, scope or meaning remain explicit. Additional potentially qualifying wording outside the frozen candidates is retained for review and cannot automatically create a positive or silently support a negative.
- Save independent, versioned v6 observations with evidence, model/configuration provenance and separate checkpoints. Preserve full OCR, raw provider replies, validation failures and any explicitly logged recovery. Distinguish HTTP success, JSON parsing, schema validity and accepted classification.

## Evidence supporting the final decision

The completed 96-product pilot exposed semantic and validation inconsistencies in the original nano v6 responses. A subsequent [four-case nano/v2 confirmation](run_06b_v6_confirmation_v1/Four-case%20v6%20confirmation.md) returned HTTP 200 for all four calls but no accepted assessments. The [v3 simplification](RUN%2006B%20-%20Final%20v6%20simplification.md) reduced the model task to interpretation of deterministic exact-evidence candidates without expanding benefit definitions.

The [four-case live mini/v3 confirmation](run_06b_v6_mini_v3/Mini%20v3%20-%20Four-case%20results.md) demonstrated Azure acceptance of strict structured output: all four returned HTTP 200, parseable JSON and schema-valid responses; three assessments passed immediately. Mini correctly interpreted Liquid I.V.'s hydration and electrolyte candidates, but its candidate IDs in `metadata_fact_ids` caused the original S09485 response to fail validation. HTTP success was not counted as an accepted classification.

Julia's final decision accepts the [auditable Liquid I.V. offline recovery](run_06b_v6_mini_v3/Liquid%20IV%20-%20Offline%20reference%20recovery.md) documented in the [field-level recovery artifact](run_06b_v6_mini_v3/liquid_offline_recovery_v1.json). The recovery clears invalid metadata references without inventing facts or changing candidate interpretations, and preserves uncertainty about panel placement. The earlier recovery report's pending-review label is its historical state; this final decision records approval of the documented recovery, without modifying the original report, failed observation or staging checkpoint.

| Mini confirmation case | Hydration content / front | Electrolyte content / front | Accepted outcome |
| --- | --- | --- | --- |
| S09485 — Liquid I.V. | `detected` / `unassessable` | `detected` / `unassessable` | Validated offline recovery; raw rejection retained |
| S04845 — Nescafé | `not_detected` / `not_detected` | `not_detected` / `not_detected` | Original mini result unchanged and valid |
| S00006 — Vega | `unassessable` / `unassessable` | `unassessable` / `unassessable` | Original mini result unchanged and valid |
| S09587 — unrelated wording | `unassessable` / `unassessable` | `unassessable` / `unassessable` | Original mini result unchanged and valid |

Six focused offline recovery tests passed; protected source hashes and the other three mini assessments were unchanged. No additional OCR/core/v6 call was needed for recovery. These bounded observations support Julia's approved model choice; they do not establish population-wide classification accuracy or complete full-run operational verification.

## Closure and remaining RUN 06B operational boundary

**Beverage methodology and model selection are CLOSED.** No additional beverage prompt experiments, new benefit definitions, taxonomy changes, broad historical reruns or manual product-review rounds are authorized. Historical saved-OCR benefit observations remain versioned; no historical core extraction is to be repeated merely because v6 now uses mini. Existing exclusions, HOLD decisions, human reviews, frozen v1/v2 evidence, sampling and Streamlit/segmentation eligibility integration remain in force. The Wave 3 handoff below is preserved for that separately scoped future cleaning work.

The only remaining beverage-related work is operational implementation within RUN 06B:

1. Bind mini specifically to the v6 stage in the reviewed runtime configuration while preserving nano for every regional core extraction, including beverages.
2. Preserve successful OCR/core checkpoints and existing HOLD decisions; use separate evidence/configuration-aware v6 identities and retain historical observations. Any canonical materialization of the approved offline recovery must preserve its provenance and original failure.
3. Verify actual runtime routing, cost controls, resume behavior and execution authorization before the remaining batch. Account tariffs, provisional estimates and provider usage must remain distinguishable.

The dedicated four-case mini transport and saved results verify that bounded test only. They do **not** establish that stage-specific mini routing in the full RUN 06B runner is integrated, operationally verified or authorized for payment. This documentation approval creates no new execution authorization and changes no runtime configuration, database or observation.

**STOP. Beverage workstream CLOSED. Return to RUN 06B execution readiness, then segmentation.**

## Historical implementation checkpoint — 24 October 2026

The following sections retain the original current-wave lock and its then-current RUN 06B/adapter status. Statements about a future adapter, pending pilot or unapplied v2 impact describe 24 October, not the final 25 October model decision above. Frozen lock manifests remain records of their original artifacts and were not regenerated for this documentation update.

## Implemented

- [Current-wave eligibility builder](../../pipeline/segmentation/implement_beverage_current_wave.py) reconciles the frozen BEVERAGE 05B, 05C and 05D evidence by exact `(barcode, region)`. The 121 reviewed cases remain **45 excluded, 3 eligible and 73 held**. The decision ledger retains the source, rationale and authority; the five Julia-reviewed coconut exclusions remain identifiable as human decisions. Other Codex proposals were applied under this consolidated instruction, not represented as individual Julia inspections.
- A narrow name **and** specific OFF-category corroboration rule identified 12 additional sauce products across regional assignments. It does not use nutrition values, parent beverage tags, pack shape or a high-fat heuristic. It protects beverage preparations. The [decision sidecar](beverage_final_v1/eligibility_decisions.csv) contains 57 excluded, 73 held and 3 explicit retains; products absent from that file have no current-wave cleaning decision. Of 158,258 physically valid beverage assignments, [158,128 exact regional keys](beverage_final_v1/segmentation_beverage_eligible_keys.csv) remain eligible. The reusable [eligibility loader](../../shared/beverage_eligibility.py) supplies these keys to subsequent beverage segmentation and RUN 06B reconciliation without rewriting frozen matrices or source data.
- [Streamlit database access](../../shared/db.py) applies exact regional holds/exclusions in Product Explorer search and Market Overview. [Product Explorer](../../pages/search.py) offers **Hydration / Electrolytes** as an additive positioning group and displays the two signals and supporting saved wording. The legacy 34 flags and fortification remain separate.
- [Independent saved-OCR observations](beverage_final_v1/benefit_observations.csv) cover 4,573 eligible regional assignments with substantive reusable OCR (including valid historical no-claim results), producing 9,146 proposition assessments. There are **29 hydration detections, 21 electrolyte detections and 7 regional products with both**, corresponding to 36 unique barcodes with either detected signal in the [app overlay](beverage_final_v1/benefit_app_overlay.csv). The 50-case frozen human set contributes 49 unique in-scope barcodes / 57 regional assignments; the remaining frozen case `3760116256209` is outside the physically valid RUN 05 beverage frame. These detections are from approved human-reviewed exceptions; the conservative [offline detector](../../pipeline/vision_ops/detect_emerging_benefits_offline.py) produced no additional front-confirmed positives from the other saved texts. It leaves front/target scope unresolved where evidence is insufficient. This does not imply zero emerging benefits among unassessed packs.
- The [future independent sixth-prompt adapter](../../pipeline/vision_ops/emerging_benefits_stage.py) validates the BEVERAGE 04 frozen prompt, schemas, validator and BEVERAGE 03 definition hashes; constructs the input from **full saved OCR**; requires a separate approved billable Guard reservation before dispatch; validates output and appends an independent versioned observation. It is opt-in and has no provider client or automatic call from the existing extractor. The three regional core prompts, two context-review prompts and old classifications remain unchanged. A separate authorized pilot is still required.

## RUN 06B impact, not applied

The [impact table](beverage_final_v1/run_06b_eligibility_impact.csv) reconciles the unchanged v2 shortlist: **selected 3,458 eligible / 39 excluded / 66 held** (3,563 total); **reserves 580 eligible / 6 excluded / 7 held** (593 total). The 105 selected and 13 reserve blocked beverage slots require subsequent RUN 06B review. No reserve was promoted, sample redrawn or quota changed. The prior 63-slot shortfall has not been recalculated into a new executable manifest.

## Verification and limitations

- Frozen input hashes matched before processing; the versioned [materialization manifest](beverage_final_v1/manifest.json) records output hashes and counts. The [final lock manifest](beverage_final_v1/final_lock_manifest.json) records implemented code, protected inputs and verification results.
- Offline wording and category fixtures passed. The detector treats prior front-panel classification as unverified provenance, so it cannot alone create a new front-positive. The app connection loaded 130 blocked exact regional keys and 36 detected-product overlays; search exposed the new positioning. Exact-region smoke test: barcode `22592007014` is blocked in FR and still available in US+CA; the FR Market Overview query also omitted it. The future adapter verified its frozen contract and preserved OCR beyond character 2,000; an unauthorized billable run did not invoke its provider callback.
- Source OFF/product-analysis records, saved OCR, historical claims, original RUN 03 outputs, and RUN 06B v2 selected/reserve manifests remain unchanged. No OCR/LLM call, image download, ingestion or clustering occurred. Historical image URLs and earlier panel context are provenance, not proof of image identity or front scope. Human-reviewed image decisions are attributed to Julia and ChatGPT, not independent Codex visual inspection. Deterministic unassessable/ambiguous results remain distinct from negative assessments.

## Wave 3 policy handoff

Use verified product-specific commercial intended use: exclude corroborated culinary coconut milk/cream and explicit non-beverage sauces/oils/foods; retain explicitly marketed drinks and beverage preparations including syrups, powders and concentrates; hold unresolved multipurpose use and image/GTIN identity conflicts. Do not infer use from can, fat, minerals or broad category alone. Preserve exact reviewed GTIN overrides and source evidence. These are future cleaning instructions; Wave 3 ingestion rules were not changed here.

**Lock boundary:** The current-wave eligibility and saved-OCR overlay are ready for local analytical use. Paid emerging-benefit enrichment and any RUN 06B execution require their own approval and validated spending controls.
