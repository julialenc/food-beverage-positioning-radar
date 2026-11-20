# F&B Positioning Radar — Segmentation

**Current navigation · 20 November 2026.** This is the permanent public methodology. The [first-run guide](first_run/README.md) distinguishes published code/audit evidence from local sources and keyed outputs. [Accepted findings](first_run/03_lenses/AUDIT_v1.md) and the [frozen release contract](first_run/04_analytical_package/ARTIFACT_INDEX.md) are the current result entry points. The dated delivery schedule and October execution history below preserve prior planning; they do not authorize another RUN. Communication and bounded processing/boundary findings are accepted. The final isolated pipeline smoke test, any further cleanup and Lovable layout remain separate pending steps.

The original hypothesis document and `learning_plan.md` remain local working/provenance documents. Local-only paths below are shown as code rather than public download links. Their original evidence is retained; the public audit consolidates the accepted narrative. Future-wave operator documentation remains local; only required shared master dependencies have been published.

**Authoritative project purpose, analytical logic and execution rules**  
**Wave 2 data preparation is closed.** The corrected master Parquet from the October 17, 2026 retrieval with the September 29 reporting cutoff is the authoritative analytical source. The commercial classification and nutritional formulation chapter is closed for the investigated product families. [Accepted formulation findings](first_run/03_lenses/AUDIT_v1.md#format-first-findings) · [Decision register](first_run/03_lenses/FORMULATION_DECISIONS_v1.csv). Accepted communication, processing and category-boundary findings are consolidated in the public research audit. Learning plan (local-only: `learning_plan.md`)

The master contains 374,840 governed products represented by 382,527 unique barcode–region–category rows. Of those rows, 12,161 matched locked claims evidence. The other 370,366 retain null claims. Open the verified master Parquet (local-only: `first_run/01_ingestion/05_master_parquet/output/master_products.parquet`), check the [master manifest](first_run/01_ingestion/05_master_parquet/output/manifest.json), or follow the [first-run audit guide](first_run/README.md) from source to output.

## START HERE — locked evidence and integration

### Authoritative outputs

The master build used the locked claims layer at `presentations/segmentation/first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/`.
Its [manifest.json](first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/manifest.json) records
`status=LOCKED`, exact source identities, hashes and schema. Use these files:

| Artifact | Purpose |
|---|---|
| claims_join.parquet (local-only: `first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/claims_join.parquet`) | Nullable claim and positioning input used in the completed master join |
| [RULES.md](first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/RULES.md) | Effective decisions, source namespaces and full join contract |
| [CHECK.md](first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/CHECK.md) | Approved population, final coverage, exclusions and residual limitations |
| [validation.json](first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/validation.json) | Source integrity, uniqueness, serialization and null-join checks |
| new_processed_audit.parquet (local-only: `first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/new_processed_audit.parquet`) | Original OCR, raw/normalized responses and original outcomes for all new observations |
| historical_reuses.parquet (local-only: `first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/historical_reuses.parquet`) | Separately linked historical dairy evidence, original source rows and market limitations |
| historical_handoff.json (local-only: `first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/historical_handoff.json`) | Unlinked historical cases; empty because all 35 linked |
| [final_approval.md](first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/final_approval.md) | Julia's final decision authority |

There are **12,126 newly processed observations and 35 linked historical reuses**,
giving **12,161 join rows**. The two FR and UK/IE salami assignments for exact
barcode `00976534` remain in the audit with `analytical_eligible=false`.
The claims lock marks the other 12,159 observations analytically eligible. The master separately records eligibility under the governed product and reviewed category rules.
Keep the historical cohort separate from the newly processed denominator.

### Effective methodology and limitations

- Historical operational normalization is preserved alongside original model
  output. Original PASS/HOLD/OTHER does not determine each derived claim's usability.
  Nullable claim values and their state/basis fields distinguish usable positives,
  documented non-detection, uncertainty, insufficient evidence and excluded identity.
- Julia's photographed decisions cover colorant-free, heritage, naturalness,
  YAM energy positioning, both regional protein/plant-based/gluten-free observations
  with 15 g protein per serving, and vitamin C positioning. The latter does not
  assert physical nutrient addition. Retain the exact Rude Health organic=false
  exception and the salami exclusion. Effective details are in RULES.md.
- **Use `energy_positioning` downstream.** All 106 approved energy-drink
  observations, including five preparations, are positive, adding 63 segment-based
  positives. Preserve raw/normalized `energy_claim`, format and evidence basis.
  Category conflicts and unresolved candidates retain their documented treatment.
- Preserve accepted beverage v6 states, all 33 identifier-only recoveries and
  unresolved/ambiguous evidence independently of core claims. Original responses
  and operational outcomes remain unchanged.
- This evidence covers selected observations. Missing or undetected claims do
  not establish package-wide absence or a complete assessment of every master
  product. The [denominator CHECK](first_run/01_ingestion/04_reviewed_claims/02_reconciliation_and_exceptions/CLAIM_STATE_DENOMINATORS_CHECK.md)
  explains conservative UNKNOWN gates; it changes no locked rule.

Remaining dairy salt reconciliation, US yogurt image-selection QA, nutrient-unit
and zero-energy treatment, nutritional feature/model comparisons and sampling
representativeness belong to analytical QA and segmentation. They do not reopen
the completed OCR/LLM preparation workstream. Ingredient-feature development
remains outside immediate scope.

<a id="next-active-task--master-product-parquet-integration"></a>

The [first-run audit guide](first_run/README.md) links the source, cleaning decisions, validation and final output. Archived path strings resolve through the recorded relocation map.

## Active delivery scope · approved 17 November 2026

Deliver the analytical package for Lovable by Saturday 21 November 2026. Julia reserves Sunday 22 November for layout work. The package comprises keyed commercial/formulation assignments for the investigated families, supported communication overlays, bounded processing and category-boundary findings, coverage and uncertainty, reproducible rules, a data dictionary and a concise artifact index.

The accepted architecture is **commercial identity → nutritional formulation → communicated positioning**. Commercial identity can include physical format, named composition, base and construction. Geography, nutrient density, processing and trade-offs provide additional analytical views. Five descriptive profiles are accepted; their thresholds are research conventions and imply no natural cluster boundary or market prevalence. Unknown commercial or claim evidence remains explicit.

This scope governs current execution. Historical sampling RUNs and earlier October targets below remain provenance. The November scope uses feature-specific eligibility, existing corrected Wave 2 evidence and one consolidated review per bounded work package.

**First-release wording decision, approved 18 November 2026.** Display **sugar-related communication** for the locked sugar_free_claim field. Preserve the original field, state, wording and provenance in the analytical package. Its positive evidence includes “no added sugar,” literal “sugar free” and saved model assessments. The 62.8 percentage-point UK/Irish soda result concerns this locked-field comparison among known assessments. Exact wording is a separate evidence attribute. [Soda wording and focused record](first_run/03_lenses/AUDIT_v1.md#communication-evidence)

**Thursday research accepted, 19 November 2026.** Julia approved the bounded processing/category-boundary findings, retaining French muesli organic × recorded NOVA 4 only as a conditional association among selected, jointly assessed observations (6/24 versus 25/48). The corrected juice layer is the authoritative analytical interpretation after the final sensitivity excluding 1,090 newly assigned French MEDIUM-confidence juices: median salt in the low-sugar group changes from 0.02 to 0.03 g/100 ml, and the headline interpretation remains stable. All assignments and evidence remain preserved. [Final sensitivity and acceptance](first_run/03_lenses/AUDIT_v1.md#format-first-findings) · [Processing approval](first_run/03_lenses/AUDIT_v1.md#processing-and-boundaries). The next phase is consolidation and equivalence validation; no further juice-classification or OCR iteration is required for this question. Presentation integration follows analytical acceptance.

## 1. Research objective and definition of success

Develop **interpretable, reproducible food and beverage product segments** using nutritional composition and evidence of **communicated on-pack benefits/claims**, then examine how product profiles and marketed propositions differ by category and geography.

The analysis is intended to help explain **how products are positioned** and to make the Food & Beverage Positioning Radar useful for research and market intelligence. It does **not** infer consumer demand, willingness to pay, actual purchase behaviour, sales-weighted prevalence, or market share from Open Food Facts (OFF) records.

Historical preliminary nutritional groups supported sampling. The completed k=5 control is an exploratory reference. The accepted format-first result comprises five descriptive profiles, commercial refinements and documented decisions against further subdivision. Communication can profile these groups or describe territories across a supported category population.

**Release success criteria.** Reproduce accepted assignments and counts; state the commercial and measurement population for each result; preserve claim-specific positive, documented non-detection and unknown states; document evidence selection and limitations; supply concise business explanations and a stable data contract for Lovable. Uninvestigated branches, alcohol exclusion and deferred preparation comparisons remain explicit.

**Decision usefulness over sophistication:** prefer simple, robust models and meaningful differences to excessive experiments or hyperparameter searching. A result that cannot be explained or traced to its evidence is not ready for release, however good its numerical metrics appear.

## 2. Universe, evidence, and interpretation boundaries

- **Geographies:** France, UK/Ireland and US/Canada; preserve the individual country assignments inside combined regions, including Ireland and Canada. One dual-country record may cover both countries while occupying one approved sampling slot.
- **Categories:** approved snacks, cereals, dairy and beverage groups. US/CA dairy was excluded from the historical 12,000-attempt design. Its separately completed 224 new US observations and 35 historical reuses now belong to the locked evidence layer. Preserve the original allocation history.
- **Physical and nutritional eligibility:** preserve existing physical-validity rules and require only the measurements needed for the specific approved profile or comparison. Fibre is optional unless the question requires it; missing values are **never zero**. Retain warnings and unusual products unless an explicit exclusion is approved.
- **Beverage eligibility:** follow locked **BEVERAGE FINAL** exact `(barcode, region)` decisions. Confirmed non-beverages are excluded; unresolved intended-use or identity cases are held; concentrates, powders, syrups and legitimate drink preparations are not broadly excluded because of format or nutrient content. Preserve source data and reasons for decisions.
- **Nutrition units:** use per 100 g (foods) or per 100 ml (beverages) consistently; document any conversion. Evaluate nutrient-density alternatives (including nutrients per 100 kcal) without silently changing the analytical universe. **Zero-energy products have undefined per-kcal ratios** and need an explicit approved policy, not a zero or arbitrary replacement denominator.
- **Claims and benefits:** an OCR/LLM output is evidence about recorded packaging text, not automatically a verified front-of-pack proposition. Preserve wording, panel/target attribution, source image/GTIN evidence, model/prompt version and uncertainty. Keep `detected`, `not_detected`, `ambiguous`, `unassessable`, unsuccessful and not-yet-assessed distinct. **Unassessable is not a negative claim.**
- **Representativeness:** the 12,000-slot allocation is a **designed analytical sample**, deliberately balancing 24 preliminary groups across 11 region/category combinations, not proportional to product universes, shoppers or revenue. Counts or cluster shares derived from this sample or OFF cannot be presented as market shares or population claim prevalence.

## 2.1 Decision-based uncertainty · approved 19 November 2026

**We can tolerate uncertainty in the observations, but not uncertainty about which observations support a conclusion.**

Use the decision affected by uncertainty to choose its treatment. There is no universal confidence or completeness threshold that makes every observation suitable for every analysis.

| Type of uncertainty | Acceptable for v1? | Treatment |
|---|---|---|
| Missing or ambiguous commercial subtype | Yes | Retain unresolved identity and the broader category; do not force a subtype. |
| Genuine overlap of commercial descriptors | Yes | Preserve multiple descriptors and distinguish compatible overlap from contradictory evidence. |
| Questionable or internally discordant recorded nutrition | Yes, with field-specific caution | Preserve source observations and flag their interpretation for the affected fields/comparisons. Do not silently correct them, treat them as missing, infer an unusual formulation, or automatically exclude the product from every analysis. |
| Continuous nutrition without a segment boundary | Yes | Report variation; do not invent clusters. |
| Sparse or selected claim/NOVA evidence | Yes | Restrict conclusions to assessed observations, with exact known/unknown and joint eligibility denominators. |
| Material classification error changing results | Only after correction | Correct the derived interpretation, recalculate affected outputs and dependencies, and withdraw superseded conclusions. Preserve source observations and original analytical identities. |
| Untraceable identity or irreproducible result | No | Hold the finding out of the release until its evidence and execution can be traced. This does not authorize global deletion of source products. |

Missing nutrition and questionable recorded nutrition are different states. For example, apple juice with zero reported sugars and substantial recorded energy retains both source observations, with the discordance flagged for field-specific interpretation. Its eligibility depends on the measurements needed for the question; the unusual combination alone does not establish an unusual formulation.

`HIGH` and `MEDIUM` commercial-classification confidence describe the strength of available textual evidence. They do not mean independently verified package identity. Original confidence, revised interpretation and any human verification stay separate.

For each released finding, make the exact source/version, product keys, starting population, exclusions, required measurements, claim states and comparison denominator reconstructible. When a remaining uncertainty could materially change a conclusion, use a bounded sensitivity tied to that decision. Stable descriptive findings can be retained with their limitations; sensitivity analysis does not independently validate identity, establish representativeness or prove a natural cluster boundary.

Statistical support among selected observations remains conditional on their eligibility and evidence. Organic communication and recorded NOVA are distinct attributes. Their association does not establish healthfulness, causality, claim compliance or market prevalence; documented non-detection concerns only the assessed evidence.

## 3. End-to-end analytical logic

| Stage | Why it exists | Decision or output that should survive |
|---|---|---|
| Define eligible universe | Identify relevant, physically valid, nutrition-complete products | Versioned eligibility rules, reasons, population counts |
| Profile and simplify features | Understand missingness, scales, redundancy and potential nutrition representations | Approved candidate features and exclusions with rationale |
| Preliminary nutritional grouping | Create sufficiently different profiles for **sampling**, not final segments | Provisional group assignments and interpretation limits |
| Historical OCR/LLM coverage | Avoid paying again for previously successful extractions, **including valid no-claim** | Evidence-aware history and first-attempt eligibility |
| Stratified sample design | Cover regions/categories/country cells and scarce nutritional profiles | Approved allocation, seed, selection reasons, exact GTINs and reserves |
| Additional vision enrichment | Add reliable on-pack claim evidence without overwriting historical records | Full OCR, core claims, beverage benefits, statuses, costs and provenance |
| Final analytical integration | Join nutrition, evidence and uncertainty to the right exact records | Versioned analytical matrix and coverage/missingness tables |
| Formulation and positioning evaluation | Test meaningful within-commercial-type distinctions and assess observed pack communication | Accepted profiles or variation, explicit eligibility, uncertainty and reproducible assignments |
| Analytical handover | Supply an understandable and auditable Lovable data package | Versioned assignments, summary tables, data contract and methodology/limitations |

Each experiment must state **which decision it informs**. Once decided, promote **one approved conclusion and its canonical output** into the analytical layer; retain intermediate artifacts as supporting evidence rather than competing answers.

## 4. Authority, lineage and file discipline

### 4.1 Sources of truth — different documents have different jobs

1. **This project’s authoritative `SEGMENTATION.md`** defines the overarching goal, scientific boundaries, workflow and execution discipline. It is *not* a substitute for a frozen record-level manifest.
2. **Approved CHECK/closure records** establish which methodological choices, exclusions and exceptions were accepted. A proposed result is not an approved decision.
3. **Frozen, hashed manifests/registries** establish exact product identities, populations, prompt versions, configurations, selection slots and lineage. Historical versions must not be overwritten.
4. **Versioned analytical outputs** are the designated source for final features, claims and segment assignments. They may refer to frozen evidence but must never silently mutate it.
5. **RUN reports, trials, tests, spreadsheets, cached images and debugging files** are supporting evidence, not alternative authoritative datasets simply because they are newer or more numerous.
6. **ONBOARDING** is an operational handover/current next-action guide, not the overall research design or an approval authority.

Do not infer authority from a filename, modification date, folder position or an apparent duplicate. When two files appear to disagree, identify the approved decision, exact artifact hash and version before changing anything. Never delete or move a hashed file solely to simplify a directory listing.

### 4.2 Thirty-second lineage requirement

For any published product, feature, benefit or segment, a reviewer should be able to find, without traversing dozens of folders:

**Displayed finding / segment → approved analytical view and version → exact GTIN + region/category → feature/claim evidence and uncertainty → source population, OCR/image/configuration and approved RUN decision.**

At final release, provide a short **canonical artifact index** and a **decision log** (approved choice, rationale, evidence reference, superseded alternatives, approval date). The index should point to existing frozen files; avoid duplicating large datasets or rehashing them unnecessarily.

The accepted v1 package is organized under `first_run/04_analytical_package/`: [artifact index and protected code dependencies](first_run/04_analytical_package/ARTIFACT_INDEX.md), [data dictionary and presentation rules](first_run/04_analytical_package/DATA_DICTIONARY.md), and [equivalence CHECK](first_run/04_analytical_package/CHECK.md). Accepted and frozen on 19 November 2026: the [freeze receipt](first_run/04_analytical_package/RELEASE_FREEZE_v1.json) protects canonical code, outputs, manifest and release documentation. The builder refuses frozen-v1 overwrite; the verifier checks integrity without writes. Uninvestigated formats must remain distinct from completed research that found no additional segment. The existing research reports remain decision evidence; no retention decision is implied by removing research runners from routine execution. The controlled housekeeping proposal (local-only: `first_run/HOUSEKEEPING_PROPOSAL_v1.md`) requires Julia's approval before any deletion, rename or move.

### 4.3 Artifact controls for every future RUN

- **Housekeeping v1 completed, 19 November 2026:** Julia approved removal of six placeholders, a placeholder-only directory and a junction entry, preserving its target and all frozen dependencies. Execution log (local-only: `first_run/logs.md`). For the next pass, aim for the minimum reproducible source/script/decision chain: derived experimental CSVs need not be retained permanently when reproducible and unused. Preserve reviewed or irrecoverable observations and necessary outputs/validation; explicitly resolve/version frozen references before removing a referenced artifact. This principle does not authorize broader deletions without an exact proposal.
- Specify in advance: **decision to inform, exact inputs, expected deliverable(s), CHECK, and STOP point**. If there is no decision, do not create an experimental run.
- Prefer **one compact report, one manifest/decision register and only the indispensable machine-readable outputs**. Do not generate dozens of alternative reports, duplicate exports, contact sheets or metadata files by default.
- Use existing files, scripts, indexes, caches and fixtures before inventing new pipelines or rerunning expensive processing.
- Record exact versions/hashes, counts, exceptions and paths; make provisional versus approved status unmistakable.
- Keep temporary work outside canonical output directories where feasible, but never relocate protected active paths or alter historical hashes.
- **Repository-wide cleanup remains deferred.** The current bounded segmentation review follows the November housekeeping handover above. File count alone is not the quality metric; uncontrolled competing artifacts are.
- No automatic top-up, supplementary dataset, extra feature family, new model, prompt revision or additional paid processing without a separate decision.

## 5. Execution constraints — mandatory

1. Execute only the **explicitly requested RUN / bounded task**. Do not proceed automatically to the next RUN.
2. Do not introduce additional features, models, preprocessing techniques or external data sources without approval.
3. Reuse existing database structures, validation functions, OCR/LLM pipelines and claim taxonomy whenever possible.
4. All processing must be reproducible, with recorded inputs, configuration, identity, outputs, uncertainty and source hashes.
5. Never silently exclude, impute, correct, merge, reclassify or relabel products. Preserve exact, leading-zero-sensitive GTIN strings and region/country assignments.
6. Do not modify original product records or historical valid results. Store derived data and changes as independently versioned, append-only observations or sidecars.
7. **Codex must not make paid OCR/LLM calls. Julia launches authorized batches from her machine using the scripts.** Do not bypass default-deny execution controls.
8. Before paid processing, provide an exact authorized manifest, projected calls by stage, approved spending ceiling, and enforceable reservation/receipt/checkpoint behaviour. Price forecasts are not invoice facts.
9. At the end of every RUN, produce the agreed CHECK, explain material exceptions and **STOP for Julia's review**. One requested step at a time.
10. Do not invent interpretations, optimize beyond scope, or treat unapproved choices as accepted.
11. Avoid exploratory full-production-database runs: they can take **20–30 minutes**. Prefer existing ledgers, indexed key lookups and a small fixed fixture. Do not repeat previously approved verification merely to be thorough.
12. A safe pilot must not turn into a new methodological project. Fix concrete failures, preserve successes, and distinguish genuine execution blockers from optional refinements.
13. Keep **data eligibility**, **OCR-processing outcome**, **claim validity**, and **nutrition-model eligibility** distinct; a blank name, failed extraction or unassessable benefit is not automatically exclusion from nutritional segmentation.

**Code and output locations:** current ad hoc analytical scripts and outputs belong in their existing `presentations/segmentation/first_run/` locations. Reuse shared analytical implementations. Production refresh logic remains in its established pipeline locations. Do not relocate working scripts merely to satisfy a directory convention. Segmentation documentation, decisions and run packages belong under `presentations/segmentation/`; preserve authoritative operational databases, caches and configuration at their existing protected paths.

**Required after each RUN:** input/output counts; agreed compact CHECK with `Proceed / Adjust / Stop`; material quality/execution issues; created or updated paths; approved decisions versus proposals; and any decision needing Julia's approval. Then STOP.

## 6. RUN map — what each stage means

| Step | Role and current interpretation | Required checkpoint |
|---|---|---|
| **01** | Build eligibility dataset | Country/category counts, exclusions, warning types |
| **02** | Profile candidate nutritional features | Missingness, distribution, scale, correlations/redundancy |
| **03** | Prepare reduced nutritional feature candidates | Retained products, documented choices; not automatically the final feature set |
| **04 / 04B** | Preliminary nutrition grouping and corrections | Sizes, stability and profiles **for sampling purposes** |
| **05** | Existing vision coverage/history and missing first attempts | Prior successes incl. no-claim, failures/retries and eligible unprocessed candidates |
| **06A** | Stratified allocation | Approved 12,000 slots, 24 groups, 11 strata, country/component quota rules |
| **06B** | Exact sample, beverage eligibility, image/duplicate/history preflight and guarded runner | Executable candidates, reserves, accepted vacancies, stage keys, spending/checkpoint protection |
| **07** | Julia's authorized OCR + regional core LLM + beverage v6 execution | Successful/failed stages, raw evidence, claims, costs, completeness |
| **08 (optional)** | Coverage top-up only if separately justified and approved | Incremental evidence value, cost, explicit authorization; **never automatic success chasing** |
| **09** | Final nutrition + claims analysis and segmentation | Compare configurations, validate robustness and meanings, release versioned assignments |

**BEVERAGE 01–FINAL** is a cross-cutting cleaning/benefit-definition workstream, **not another RUN 06 sample draw**. Current-wave BEVERAGE FINAL eligibility is locked and applied to analysis/Streamlit. Hydration and electrolytes are independent, evidence-scoped benefit signals, not replacements for the existing 34-flag taxonomy. Wave 3 cleaning implementation and any US/CA dairy reconciliation are separately scoped.

## 7. Historical status and protected decisions (25 October 2026)

This snapshot is retained for approval history. The 12 November lock and
START HERE section govern current activity; the following execution instructions
are historical.

- **Current-wave beverages:** locked. Preserve `BEVERAGE FINAL - Implementation and lock.md`, the final hashed sidecars/manifest and frozen human decisions; do not revisit individual beverage cases as part of core execution.
- **RUN 06B proposed processing population:** 11,902 regional primary records, including 172 matching reserve replacements; 98 approved-slot vacancies are documented and need not be filled. US/CA dairy is excluded. The 96-record paid pilot is a **subset** of the 11,902, not additional allocation.
- **Vision routing:** after a successful Azure OCR operation, execute the correct existing regional **core LLM** for every eligible category; for **every beverage**, also execute independent **v6 `emerging_benefits_v1`** against the **same complete saved OCR**. Core no-claim or a core-stage failure must not suppress v6. Other categories never receive v6. Conditional dairy review/re-extraction follows its pre-existing rules. Save/checkpoint each stage independently.
- **Pilot:** 96 OCR operations succeeded; the pilot revealed French-core and one v6 rate-limit errors, contradictory core statuses, and v6 schema/evidence/semantic validation failures. Existing observations are preserved. Offline repair recovered 16 v6 outputs as **unassessable** (not negatives), left three semantically unresolved and one HTTP 429; 19 contradictory core results were held. The repaired export now uses authoritative exact-text GTINs; saved dairy context review/re-extraction was verified. These are real pilot findings, **not** permission to erase raw statuses or issue blind paid retries.
- **Main RUN 06B processing:** not yet authorized in this status snapshot. Reuse the existing runner and append-only staging; do not redraw or rerun successful pilot stages. Spending controls and real rate-limit handling remain mandatory.
- **Cost:** pilot-measured usage and eventual Azure billing must be distinguished from provisional model-rate estimates. Do not grow prompts or loosen evidence/validation rules solely for operational convenience; do not demand unrealistic worst-case full-run authorization. Approve a bounded real run after controls are verified.

## 8. Immediate next tasks — priority order

Wave 2 preparation is complete. The verified master is the input to the next analytical phase.

### Historical October execution sequence — completed/superseded

The sequence below preserves the original plan and is not an outstanding task list.

1. **Compare original proven Stage 10 vision execution against the new RUN 06B runner.** Identify the *material* differences in request pacing, token load, deployment use and existing core normalization that explain the pilot's 429 cluster and contradictory status handling. Do not rebuild working components or repeat broad tests without evidence.
2. **Correct v6 minimally.** Align the response example/JSON-null representation, enforce compatible structured output where supported, and deterministically validate exact OCR evidence. Separate **wording detection** from **front/target attribution**; a clear example such as Liquid I.V. must not yield contradictory negative benefit statuses. Use **saved OCR and saved responses** for focused tests; no new OCR, no prompt proliferation or wholesale rewrite. If a prompt change is necessary, version it without overwriting the frozen prior prompt.
3. **Julia reviews and authorizes the remaining guarded core + v6 processing.** Preserve immutable history, exact assignments, partial pilot successes and checkpoints; no reprocessing successful OCR/LLM. Use approved manifest, default-deny cost guard and documented restart/resume procedure. Report measured success, uncertainty, costs and failures; do not silently retry, top up or expand scope.

**Then:** begin/continue final feature experiments and claims integration while vision results accumulate. A separate, bounded US/CA dairy reconciliation can run in parallel if it does not jeopardize delivery. Repository housekeeping and broader documentation cleanup are deferred until after stable segmentation.

## 9. Final analytical QA and release

Before declaring final segments, explicitly review:

- Population/region/category inclusion and exclusion; meaningful sampling and OFF coverage caveats.
- Nutritional units, complete M1 versus missing fibre/M2, scaling, outliers and zero-energy nutrient-density handling.
- Accepted formulation rules, commercial identity, population counts, stability/sensitivity findings and geographic composition; the completed pooled control remains an exploratory reference.
- Evidence versions, OCR/LLM processing status, explicit/ambiguous/unassessable benefits, and how missing or uncertain claims affect the analysis.
- Exact product-to-segment lineage, approved model/configuration, segment definitions, versioned assignments and consumer-facing explanation.
- Clear distinction between **observed marketed propositions** and actual consumer choice or market performance.

The active release target is the Lovable analytical package described above. Validate keyed assignments, display-ready summaries, evidence denominators and lineage before freezing it. Retain the interpretive summary and canonical artifact index. A Streamlit segmentation tab was an earlier publication target.

**Historical October planning target:** Thursday **29 October 2026, noon**, for a private analytical release with transparent scope and limitations. The 27 October travel/contingency plan is historical. No replacement release date is set by this handover. Use Europe/Zurich when documenting a new analytical schedule.

**Enduring rule:** *RUN → CHECK → Julia's approval → next task*. Preserve evidence, but promote only approved decisions into the canonical analytical layer.
