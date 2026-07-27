# Front-of-pack claim extraction — process documentation

This document records how the Food & Beverage Positioning Radar samples
products for front-of-pack image analysis, how it extracts and classifies
claims, and how each component of that process evolved. It is written for
technical contributors and methodology reviewers. Open Food Facts is
abbreviated **OFF** throughout.

**Pipeline in one sentence:** draw a stratified sample from image-eligible
OFF products → OCR the pack image with Azure AI Vision → extract explicit
claims with a language-specific LLM prompt → validate the structured output
→ map claims into a common taxonomy → compare observed positioning with
formulation and nutrition reality.

**Current active prompts:** `prompt_v4.txt` (English, US+UK release);
`prompt_v5_1_fr.txt` + `prompt_fr_context_review.txt` (French release).

**Release naming:** "Release 01" and "Release 02" refer to extraction runs
in ordinal order. `release_2026_01_us_uk` and `release_2026_01_fr` are the
`release_run_id` values stamped in the database — they identify the 2026
analytical release and its two regional components. The mismatch between
ordinal labels and database identifiers is intentional: both extraction runs
together form one analytical release.

**What this document covers:**
- The sampling universe and design rationale
- Prompt version history and the reasoning behind each change
- Extraction pipeline mechanics
- Release record for all three runs
- Known limitations specific to the extraction process

**What to read elsewhere:**
- Metric definitions and "what it measures / what it does not measure" →
  `docs/METHODOLOGY.md`
- Interpretation caveats and data-source limitations → `docs/LIMITATIONS.md`
- Architectural decisions (language-profile design, release-ID scheme) →
  `docs/ADR.md`
- Field names and types → `docs/COLUMN_DESCRIPTIONS.md`

---

## 1. Why front-of-pack extraction exists

Ingredient-based analysis (`claim_source = ingredient_text_only`) can infer
positioning signals from what a product contains. It cannot observe what the
manufacturer actually says to consumers. A product adding probiotic cultures
without a front-of-pack claim occupies a different analytical position from one
that leads with "SUPPORTS GUT HEALTH" in a green callout.

The extraction layer closes that gap. It uses OCR on the Open Food Facts
product image followed by an LLM extraction call to read what the pack
actually communicates, independently of the ingredient list. This is the
independent measurement that makes the sampling design valid (see section 2).

OBS-016 (Dinosaurus Chocolat, May 2026) was the first documented product
where this distinction mattered: pea protein detected in ingredients, no
front-of-pack protein claim visible.

---

## 2. Sampling design

### 2.1 The non-circularity constraint

The purpose of the LLM run is to compare, per product, what the pack
communicates against what the product actually is. For that comparison to remain interpretable, the sampling proxy, formulation
evidence and measured pack claim must come from distinct, non-overlapping
evidence layers. The observed LLM claim output must not be used to construct
the strata in which it is subsequently measured — that would be circular
derivation.

This constraint was named the **"ouroboros" problem** in the working design
log: a snake eating its own tail — if ingredients drove both "likely
positioning" and "product reality," the two sides would be partly circular and
we would be measuring a relationship we had partly baked in.

The solution has three axes:

- **Positioning axis** (what the pack likely communicates): derived from
  product name text only. Product names are the only OFF field that reliably
  reflects deliberate pack communication. Category ancestry tags inflate
  territories artificially (e.g., "Plant-based foods and beverages" is an
  ancestor of any juice, inflating plant-based hits by ~300×). Inferred labels
  (`en:vegetarian`) are applied algorithmically by OFF, not written on pack.
  Both were dropped after finding false-positive rates of 39.5% and 22.7%;
  the name-only rate of 12.4% is credible for product names alone.

- **Reality axis** (what the product is): derived from ingredients and
  nutrition — a separate axis from positioning.

- **LLM output** (the measured variable): the observed claim label, kept
  entirely out of the sampling proxy.

### 2.2 The four-cell matrix

| Positioning signal | Formulation signal | n (US/UK) | Share |
|---|---|---|---|
| Explicit | Present | 10,782 | 6.8% |
| Explicit | Absent | 8,858 | 5.6% |
| None | Present | 45,748 | 28.9% |
| None | Absent | 92,690 | 58.6% |

The off-diagonal cells are analytically interesting precisely because the two
axes are derived from distinct evidence layers rather than from each other:
- **Explicit + Absent** (8,858): the product name contains positioning
  language that the formulation proxy does not obviously support.
- **None + Present** (45,748): the formulation could support a claim the name
  does not communicate — the Danone case, where functional ingredients like
  probiotic cultures carry the claim on a badge rather than in the product
  name.

A biased proxy would have collapsed these cells into the diagonal and hidden
exactly the relationship the tool exists to study.

### 2.3 Name-confidence flag

Some product names are too sparse to trust a "no signal" result: a blank,
single-word or numeric-only name ("Yogurt", "500ml") means genuinely unknown
rather than confirmed absent. Rather than reintroducing labels or categories
to rescue these, the design adds a separate `name_confidence` quality flag.
On the US/UK universe, 8,650 products (5.5%) are classified
`low_confidence_name` — retained as a separate quality flag so unknown name
evidence can be distinguished downstream from a confident absence of
positioning language.

### 2.4 Image eligibility

The initial 12,029-product clean sample was discarded after preflight showed
2,177 of the 5,951 initially sampled US products (36.6%) had no usable `image_url`.
Submitting `nan` to Azure OCR produced HTTP 400 errors labelled as
`invalid_image`. The fix was applied to the sampler: `smart_sample.py` now
filters `image_url IS NOT NULL AND TRIM(image_url) <> '' AND LOWER(TRIM(image_url)) LIKE 'http%'`.
A preflight HTTP check (`preflight_images.py`) confirmed 100% availability
before the locked run was drawn.

### 2.5 Three sampling components

Each region-category quota is filled by three components, with the following
quota allocation shares:

| Component | Allocation | Description |
|---|---|---|
| Backbone | 35% | Proportional within formulation family, random selection, brand cap 15%, approximate design inclusion probabilities and weights after brand capping |
| Matrix | 50% | Positioning × reality per territory, filled in priority order |
| Calibration | 15% | Rare territory enrichment (immune, gut, fibre formulation pools) plus prompt-comparison panel (prior run products) |

Only the **backbone** carries a sampling weight. It is the probability-oriented
component, with random selection within formulation strata and approximate
design weights after brand capping. Matrix and calibration are purposive: they
deliberately enrich analytically important or rare cases and therefore have no
population inclusion probability to invert.

This produces two different quantities:

- **Sample proportion** (45.7% for release-01): the observed proportion among
  all sampled products. It reflects the intentional over-representation of
  matrix and calibration cases and is not a population or market estimate.
- **Backbone design-weighted estimate within the image-eligible OFF sampling
  frame** (37.7%, n=4,679): the estimate used when describing prevalence within
  that frame. Weights are approximate after brand capping, and OFF itself is not
  a probability sample of retail sales or SKUs on shelf.

The gap is driven primarily by sample composition. The purposive components
have 50.9% claim prevalence versus 38.2% in the unweighted backbone, while
applying the backbone weights moves 38.2% to 37.7%. Thus most of the
difference between the 45.7% raw sample proportion and the 37.7%
design-weighted backbone estimate comes from deliberate enrichment, not from
weighting. The decomposition confirms that the purposive components enriched
the sample as intended.

### 2.6 Formulation families

`classify_formulation_families.py` assigns each product to a mutually
exclusive formulation family within its category, using OFF sub-category tags
and product name keywords under first-match-wins priority rules. The purpose is
to prevent one dominant sub-type from consuming an entire sampling quota — not
a final analytical segmentation. Cereals is a structural exception: 84% fall
into `other_cereals` because OFF's category data is sparse for standard cereal
products. Cereals uses positioning and reality bands as primary strata; family
is used where available (~16%).

---

## 3. Claim taxonomy

The taxonomy maps detected pack text to 34 boolean claim fields, grouped into
five Cut-1 categories. Cut-2 assigns a sub-category to the highest-priority
detected claim. Field → category mapping is defined in `tag_claims.py`.

| Cut-1 category | Sub-categories included |
|---|---|
| `FUNCTIONAL` | protein, fiber, gut_health, vitamins, immune, energy, whole_grain, sleep, brain_health |
| `FREE_OF` | free_from (dairy-free, vegan, lactose-free, gluten-free), no_added_x, no_artificial, reduced_fat |
| `NATURAL_ORGANIC` | natural, organic |
| `OTHER` | comparative, heritage, sustainability, reformulation, other |
| `NO_CLAIM` | — |

The 34 claim fields are documented in `docs/COLUMN_DESCRIPTIONS.md`. The
taxonomy reached its current shape through four prompt versions, each adding
fields in response to specific observed gaps.

---

## 4. Prompt version history

All prompts live in `pipeline/prompts/`. The active version is loaded at
run time by `vision_extract.py --language`; nothing is pasted inline. This
means the file IS the record: the archive and the active prompt cannot drift
apart.

### 4.1 v1/v2 — single-pass extraction (used for the ~4,700-product pilot)

**Architecture:** one LLM call per product. Claims and `no_claims_detected`
returned together. No image context classification.

**Critical methodological defect:** a non-front image (ingredient sticker,
nutrition label, price sticker) returned `no_claims_detected = true` — the
same value as a valid front pack that genuinely carries no claims. A
photographed back label was indistinguishable from a confirmed-no-claim front.

**Taxonomy at v1/v2:** 29 boolean fields plus `ocr_quality`. Missing:
`gut_health_claim`, `prebiotic_claim`, `sleep_claim`, `brain_health_claim`,
`reduced_fat_claim`, `whole_grain_claim`, `detected_claim_phrases`,
`image_context`, `claim_extraction_status`.

**Known issue caught early:** "DOUBLE ZERO" and "ZERO SWEETENERS" were being
mapped to both `no_added_sugar = true` and `no_artificial = true`.
"Zero sweeteners" does not mean no added sugar; the two can coexist. Fixed by
routing ambiguous zero claims to `other_claims` unless the pack explicitly
states what the zeros refer to.

### 4.2 v3 — image context classification and expanded taxonomy

**The structural redesign.** Two breaking changes:

1. `image_context` added as the first output field, classified before any
   claim extraction. Allowed values: `front_of_pack`, `mixed_pack_text`,
   `ingredient_or_legal_panel`, `nutrition_label`, `price_sticker`,
   `uncertain`.

2. `claim_extraction_status` added: `completed` / `not_applicable_non_front`
   / `unreadable`. Non-front images now set every claim field to false and
   `no_claims_detected = null` (not true). This distinguishes three states
   that v1/v2 could not separate: valid front with claims, valid front without
   claims, and not a valid front-pack observation.

**New taxonomy fields:** `gut_health_claim`, `prebiotic_claim`, `sleep_claim`,
`brain_health_claim`, `reduced_fat_claim` (+ `fat_reduction_pct`),
`whole_grain_claim`, `detected_claim_phrases`, `other_claims`.

**Classification rules established:** text length above 25 words is supporting
evidence only; never triggers `ingredient_or_legal_panel` by itself. Multiple
signals required: starts-with-INGREDIENTS, comma-separated compound text,
percentages, allergens, storage details, addresses.

**Key boundary established:** probiotic positioning must be a front-of-pack
benefit claim, not an inference from ingredient list entries. A yoghurt
listing "L. casei" in its ingredient text is not a `probiotic_claim` unless
the pack highlights the cultures as a benefit.

**Immunity separated from fortification:** vitamins C/D, zinc or selenium
highlighted WITHOUT explicit immunity wording → `fortification_claim` only.
Explicit immunity language → `immune_claim`.

### 4.3 v4 — two targeted fixes and one new field

**New field:** `lactose_free_claim`, separated from `dairy_free_claim`.
Lactose-free milk is still dairy; the two claims are conceptually and
taxonomically distinct.

**Renamed field:** `no_added_sugar` was consolidated into the raw extraction
field `sugar_free_claim`, which captures both "sugar free" and "no added
sugar" wording and maps downstream to the `no_added_x` taxonomy code. This is
an operational field-naming choice in the extraction schema — it does not
imply "sugar free" and "no added sugar" are nutritionally or legally
equivalent claims. The two were previously separate fields with practical
wording overlap in the OCR text; the taxonomy layer, not this field, is where
the conceptual distinction should be drawn if needed.

**Two classification rules added:**

- *Front-of-pack nutrition boxes:* a small front-of-pack nutrition panel,
  traffic-light box or nutrient summary does not make the image a
  `nutrition_label`. Classify as `front_of_pack` if branding is clearly
  visible; ignore the nutrient values when extracting claims.

- *Small legal text on an otherwise valid front:* a small ingredients or
  manufacturer block at the edge of a clearly branded front panel does not
  make the whole image `ingredient_or_legal_panel`. Classify as
  `mixed_pack_text` and extract only the marketing-oriented statements.

These two rules were added in direct response to the KIND product review
(release-01 US): two ingredient stickers had been classified as
`mixed_pack_text`, producing completed observations with no claims, when
they should have been `ingredient_or_legal_panel`.

**v4 is the frozen English prompt for release-01 (US & Canada + UK & Ireland).**

### 4.4 v5-fr — French expansion of v4

**Architecture decision:** standalone prompts per language, not a shared core.
The JSON schema block is byte-identical between v4 and v5-fr, so the taxonomy
stays comparable across releases. Only phrase coverage differs.

v4 was already more multilingual than it appeared — it carried
`RICHE EN FIBRES`, `SANS HUILE DE PALME`, `ORIGINE FRANCE`, `NOUVELLE RECETTE`,
`VITALITÉ`, and the `NATURE` rule. The French work was expansion, not rewrite.

**What was expanded (18 targeted replacements, 275 → 340 lines):**

| Territory | New French terms added |
|---|---|
| Protein | `HYPERPROTÉINÉ`, `PROTÉINES AJOUTÉES`, `SOURCE DE PROTÉINES` forms |
| Fibre | `SOURCE DE FIBRES`, `HAUTE TENEUR EN FIBRES` |
| Gut health | `CONFORT DIGESTIF`, `TRANSIT INTESTINAL`, `MICROBIOTE`, `FLORE INTESTINALE` |
| Immunity | `DÉFENSES NATURELLES`, `IMMUNITÉ`, `SYSTÈME IMMUNITAIRE` |
| Energy | `ÉNERGISANT/E`, `TONUS`, `COUP DE FOUET`, `SPORT & ÉNERGIE` |
| Reduced fat | `0% MG`, `PAUVRE EN MATIÈRES GRASSES`, `ALLÉGÉ/E` forms |
| Whole grain | `FARINE COMPLÈTE`, `PAIN COMPLET`, `INTÉGRAL/E` |
| Fortification | `SOURCE DE MAGNÉSIUM`, `GERME DE BLÉ` |
| Free-from | `AUCUN/AUCUNE` negation forms, `SANS ÉDULCORANTS`, `SANS OGM` |
| Organic | `AGRICULTURE BIOLOGIQUE`, `ISSU DE L'AGRICULTURE BIOLOGIQUE` |
| Artisan | `ARTISANAL/E`, `À L'ANCIENNE`, `FERMIER/FERMIÈRE`, `DU TERROIR` |
| Origin | `FILIÈRE MAÎTRISÉE`, `AOP`, `AOC`, `IGP`, `LABEL ROUGE` |

**Root cause of the initial thin French signal rate (8.8%):** the first French
dictionary had only plural forms — `sans conservateurs`, `sans additifs`.
`analyze.py`, which was the vocabulary source, uses singular forms:
`sans conservateur`, `sans additif`. Word-boundary regex means
`\bsans conservateur\b` does not match "sans conservateurs." Both forms now
present throughout.

**An over-match Claude introduced and fixed:** `purity_simplicity` territory
fired 4,155 times in France versus 7 in US/UK because "pur jus", "100%
fruits" and "pur beurre" were included. In French those are category and legal
descriptors, not positioning. The English equivalents ("just fruit",
"nothing but") are marketing slogans. Removed; now 3 vs 7.

**Five French-specific cautions written into the prompt:**
- `ferments lactiques` in an ingredient list is a standard dairy ingredient,
  not a `probiotic_claim` (only qualifies when highlighted as a front-of-pack
  benefit)
- `allégé` defaults to fat unless the pack says `allégé en sucres`
- `boisson énergisante` as a bare category is a product type, not an
  energy benefit claim
- `PUR JUS`, `100% FRUITS`, `PUR BEURRE` are legal descriptors and should
  route to `other_claims` only
- `BONNE NUIT` used as a flavour name is not a `sleep_claim`

**Territory structure principle established:** territory STRUCTURE stays
symmetric (same 15 keys in both English and French dictionaries). Individual
TERMS are market-specific. `sans huile de palme` is a major French front-of-pack
claim with no common US/UK equivalent, so it lives in the French dictionary
only. This is documented design, not an accident.

**Regulatory context as a possible market factor:** the remaining gap between
French and English signal rates (9.0% vs 12.4%) may partly reflect genuine
differences in pack communication. The EU nutrition and health-claims regime
(Regulation 432/2012) is one plausible contributor — it constrains what
manufacturers can say on French packs more tightly than FDA/FTC standards in
the US, particularly for protein and energy claims (OBS-025) — but this
pipeline does not isolate regulatory effects from category mix, sampling-frame
differences, or other market factors. The gap is an observation, not a
causal finding.

### 4.5 v5.1-fr — panel-classification fix

**Triggered by:** the first 100-product France test, which produced a 7%
false-exclusion rate. Seven valid front packs were classified as
`ingredient_or_legal_panel`: La Bergère Pérail Bio, Comté Bio JuraFlore,
Twinings Summer Berry, Le Gall Beurre de Bretagne, St Môret, Saint-Nectaire
AOP, and Plenish Organic Hazelnut.

**Root cause:** OCR strips visual hierarchy. The model received flattened text
with no logo size, font size, colour or position information, and no knowledge
of the product. The prompt listed many legal-panel clues (starts with
INGRÉDIENTS, many commas, allergens, addresses) with no equally weighted
front-identity clues. Every one of the seven had its brand name in the OCR
but no way to use it.

**What v5.1-fr adds:**

1. A `PANEL CLASSIFICATION PRIORITY` block prepended to the existing
   classification section: explains that line order proves nothing, lists
   front-identity evidence, names certification marks, AOP/AOC/IGP, origin
   language, heritage statements, medals, producer names, batch codes and
   short ingredient declarations as **common front-of-pack elements** that
   alone never make a legal panel.

2. Brand and product name are now passed to the model as reference identity —
   explicitly usable for panel-context judgement, never as claim evidence.

3. Three new deterministic hints appended to the context block:
   `brand_token_overlap` and `product_name_token_overlap` (share of the brand
   or product name's distinctive de-accented tokens present in the OCR) and
   `contains_ingredient_header` (whether the OCR contains "INGRÉDIENTS:" with
   a colon). The existing hints all pointed toward legal text; these point back.

4. A worked example for Plenish: `"3 NATURAL INGREDIENTS / HAZELNUTS, WATER,
   SEA SALT"` is `minimal_ingredients_claim` on a `front_of_pack`, not an
   ingredient panel. An ingredient list can BE the claim.

5. `mixed_pack_text IS NOT A FALLBACK`: if ingredient/nutrition/legal text
   dominates, classify `ingredient_or_legal_panel` even when a brand name is
   visible — a brand name on a sticker does not make the sticker a front pack.

**Result of the second 100-product test:** false-exclusion rate fell 7% → 2%.
The two remaining misses were both French cheese packs with organic
certification and short ingredient declarations visible on the front. The wine
case (one product with heavy regulatory text on the front) was declared
tolerable and the general prompt left unchanged for it.

**v5.1-fr is the frozen French prompt for release-02 (France).**

---

## 5. Second-pass panel-context review

After v5.1-fr, a 2% false-exclusion rate remained — both errors in dairy,
specifically French cheese and organic products. Within the dairy category the
rate was materially higher than 2%.

Rather than tightening the general prompt further (which would risk admitting
genuine legal panels), a **narrow second-pass review** was added:

**Trigger conditions** (all four must be true):
1. Language profile defines a `context_review_prompt`
2. First-pass `image_context == ingredient_or_legal_panel`
3. `sampling_category` is `dairies` or `dairy`
4. OCR succeeded

**Mechanics:** one small LLM call (max_tokens 60) using the saved OCR — no
second Azure Vision call. Returns only `{"image_context": "..."}`.

**Critical design constraint:** when the review rescues a row, claims must be
extracted again via `extract_claims(forced_context=...)`. The first pass
already zeroed every claim field when it decided the image was a legal panel.
Changing only the status would create a `completed` observation with no claims,
which passes QA checks and silently understates claim prevalence. A status-only
fix is worse than the original error.

**Audit trail:** four fields are written per row:
`v3_initial_image_context`, `v3_context_review_attempted`,
`v3_reviewed_image_context`, `v3_context_review_changed`.

Two review prompts exist:
- `prompt_fr_context_review.txt` — French dairy; lists what French cheese
  fronts normally carry (AB/BIO, AOP/AOC/IGP, regional origin, fromagerie
  identity, affinage statements, a short ingredient declaration)
- `prompt_en_context_review.txt` — English; lists US/UK equivalents
  (USDA ORGANIC, NON-GMO PROJECT VERIFIED, FAIRTRADE, RED TRACTOR, royal
  warrants, EST. 18xx, creamery/mill/farm identity, batch codes)

**France production results:** 243 rows triggered the review, 187 were
rescued. Without the second-pass review, total non-completion would have been roughly
11%; with the review it fell to 7.3% (451 of 6,170). Within that, the
non-front rate was 4.4% (269 products) and failed/not attempted 3.0%
(182 products). The reviewer correctly kept the true legal panels: a Comté AOP
label dominated by the health mark `FR 25.039.003`, a manufacturer address,
and a full ingredient list.

`--no-context-review` disables the step. `CONTEXT_REVIEW_CATEGORIES` is a
visible module constant. The English review prompt is wired but not yet
tested on release-01.

---

## 6. Extraction pipeline mechanics

### 6.1 OCR (Azure AI Vision Read API)

One HTTP call per product image URL. The OCR response is the raw text
extracted from the image; geometric information (bounding boxes) is discarded.
This is the fundamental constraint the classification hierarchy exists to
manage: with no visual hierarchy, only text signals are available.

`ocr_status` values: `success`, `invalid_image`, `timeout`, `no_image`,
`no_credentials`.

### 6.2 LLM extraction (Azure OpenAI gpt-4.1-nano)

One HTTP call per product, conditional on OCR success. The system prompt is
the active language profile prompt. The user message contains:

- Reference identity (brand and product name) — for panel context only,
  never as claim evidence
- Deterministic OCR context hints (word count, comma count, semicolon count,
  starts-with-ingredients flag, ingredient-header flag, nutrition term count,
  currency detection, brand token overlap, product name token overlap)
- OCR text, truncated to 2,000 characters

`llm_status` values: `success`, `skipped_empty`, `skipped`,
`json_parse_error`, `http_400_*`, `error_*`.

### 6.3 Validator

Every LLM response passes through `validate_and_normalise()` before any field
is written. The validator enforces:

1. `image_context → claim_extraction_status` contract:
   `front_of_pack` / `mixed_pack_text` → `completed`;
   `ingredient_or_legal_panel` / `nutrition_label` / `price_sticker` →
   `not_applicable_non_front`; `uncertain` → `unreadable`.
   Overrides the model's self-reported status when they conflict. This
   override fired on 33–35% of rows in both releases. The model's
   self-reported `claim_extraction_status` conflicted with the status implied
   deterministically by `image_context` on roughly one third of products. The
   validator therefore carries a substantial status-consistency burden, though
   it does not correct the underlying panel classification: if `image_context`
   is wrong, the validator propagates that error with a correct status for the
   wrong context.

2. Non-front images: all boolean claim fields set to false, all numeric fields
   set to null, `no_claims_detected = null`.

3. Unmapped-claim reconciliation: `completed` rows where no boolean field
   mapped to true and `other_claims`/`detected_claim_phrases` contain text
   → `no_claims_detected = True`, `unmapped_pack_text = True`. The model
   was using `no_claims_detected = False` to mean "I noted text worth
   recording"; the pipeline needs it to mean "a taxonomy claim is present."
   ~1,127 rows in release-01 were resolved this way; ~2% of those carried
   genuinely mappable content (estimated ~2pp understatement of claim
   prevalence).

4. Numeric-implies-flag (range check runs FIRST): if `protein_amount_g` is
   set and within 0–100, `protein_claim = True`. If out of range, null the
   numeric field before the flag check so an invalid value cannot create a
   claim. Same for `sugar_reduction_pct`, `fat_reduction_pct`,
   `comparative_reference`.

5. `unmapped_pack_text` and `numeric_out_of_range` audit flags written per row.

### 6.4 Cost and throughput

| Metric | Release-01 US+UK | Release-02 France |
|---|---|---|
| Products | 11,850 | 6,170 |
| Azure spend | ~12 CHF | ~8 CHF |
| Runtime | ~38 hours (two nights) | ~18 hours |
| Completion rate | 96.0% US / 96.5% UK | 92.7% FR |

The French completion rate is lower primarily because the non-front rate is
higher (7.3% total non-completion vs ~4% for English; non-front specifically
4.4%): French dairy and cheese packs carry
more certification, origin and legal text that the prompt classifies as
non-front, even after the v5.1-fr fixes.

---

## 7. Release record

### Release 01 — US & Canada + UK & Ireland

| | US/Canada | UK/Ireland | Total |
|---|---|---|---|
| Sample | 5,894 | 5,956 | 11,850 |
| Completed | 5,660 | 5,748 | **11,408** |
| With claims | 2,760 | 2,455 | **5,215** |
| No claims | 2,900 | 3,293 | 6,193 |
| Non-front | 155 | 114 | 269 |
| Failed/not attempted | 79 | 94 | 173 |

**Release ID:** `release_2026_01_us_uk`  
**Prompt:** `prompt_v4.txt` (v4), no second-pass review  
**Sample file:** `pipeline/sample_clean_run.csv` (RUN_ID `release-01-image-eligible`)  
**Archived results:** `vision_results_us_canada_final.csv`, `vision_results_uk_ie_final.csv`  
**Normalised results (feed merge_scores):** `*_normalised.csv`  
**Claim prevalence:** 45.7% sample proportion (n=11,408); 37.7% design-weighted
estimate within the image-eligible OFF sampling frame (backbone n=4,679).
Note: backbone weights are approximate design weights after brand capping; OFF
is not a probability sample of retail sales or SKUs on shelf.  
**By region:** US & Canada 48.8% / 40.2% weighted; UK & Ireland 42.7% / 32.1% weighted  
**By category:** dairies 52.6% / 47.3% weighted; cereals 47.9% / 39.9%;
snacks 39.7% / 33.8%; beverages 38.5% / 33.5%

### Release 02 — France

| | France | 
|---|---|
| Sample | 6,170 |
| Completed | 5,719 |
| With claims | 2,323 |
| No claims | 3,396 |
| Non-front | 269 |
| Failed/not attempted | 182 |

**Release ID:** `release_2026_01_fr`  
**Prompt:** `prompt_v5_1_fr.txt` (v5.1-fr) with `prompt_fr_context_review.txt`  
**Sample file:** `pipeline/sample_france_run.csv` (RUN_ID `release-02-france`)  
**Archived results:** `vision_results_20260724_014247.csv`  
**Context review:** 243 triggered, 187 rescued  
**Claim prevalence:** 40.6% sample proportion (France); weighted estimate
pending backbone weight analysis  
**By category:** cereals 46.8% (contaminated by pasta/bread — see section 9);
dairies 41.2%; snacks 38.2%; beverages 35.5%

**Combined release denominator:** 11,408 (US/UK) + 5,719 (France) = **17,127**
valid front-of-pack observations.

---

## 8. Data flow

```
Open Food Facts image URL
  → Azure AI Vision OCR
    → ocr_text, ocr_status

ocr_text + brand + product_name + context hints + system prompt
  → Azure OpenAI gpt-4.1-nano
    → raw JSON response

raw JSON
  → validate_and_normalise()
    → image_context, claim_extraction_status, 34 boolean fields,
       numeric fields, audit flags

[optional, FR dairies only]
  → review_image_context() on saved OCR
    → reassessed image_context
  → if rescued: extract_claims(forced_context=...)
    → claims re-extracted from saved OCR

→ vision_results_<timestamp>.csv  (one row per product)

→ merge_scores.py --release-id <id>
    → pack_claims_found (pipe-separated claim keys)
    → sampling frame columns written to product_analysis
    → merged_results_<timestamp>.csv

→ tag_claims.py
    → claim_category_1, claim_category_2
    → claim_source = 'vision' for the 17,127 release products
    → nutrition_benchmark_flags, claim_benchmark_intersections

→ db_summary.py
    → weekly_brand_positioning_summary
    → powerbi_final_*.csv
```

**Key invariant:** `pack_claims_found = None` means no valid observation.
`pack_claims_found = ""` means the front pack was assessed and carried no
taxonomy claim. These are distinct states. Loading with `keep_default_na=False`
is required to preserve the distinction.

**Release scoping:** `claim_source = 'vision'` correctly identifies the
release population only because `clear_stale_vision.py` was run before
`merge_scores.py`, retiring 3,858 superseded pilot rows (3,789 prompt-v2,
69 v4 test artifacts). For future releases, filter on `release_run_id`.

---

## 9. Known limitations

**OCR quality and pack design.** Azure AI Vision's Read API performs well on
standard packs but degrades on: white text on dark backgrounds, angled or
edge-cropped images, small thumbnail images, and highly stylized typography.
OBS-021 documents the Oatly case: all 23 products returned near-zero
claim scores because large artistic typography fragmented into disconnected
tokens. The OCR text is present in `v3_ocr_text` and auditable per product.
The limitation biases the results against brands that use dark-background or
artistic pack design. `v3_ocr_quality` records `good`, `partial`, or `poor`
per product.

**Panel classification residual error.** The second 100-product v5.1-fr test
still showed a 2% false-exclusion rate, concentrated in French cheese packs.
This motivated the targeted dairy second-pass review (section 5). In
production, 243 rows triggered the review and 187 were rescued. Residual
error after the review has not been exhaustively estimated; some genuine
front packs are likely still classified as non-front, particularly outside
the dairy category the review targets. The same panel-classification problem
is likely present at low rates in release-01 (English v4, no panel priority
block, brand not passed to the model). 141 candidates identified for review.

**Unmapped claims (~2pp understatement).** Approximately 20–25% of the 1,127
release-01 products resolved to `pack_claims_found = ""` by the validator
carried genuine taxonomy-relevant text in `other_claims` or
`detected_claim_phrases` (e.g., "FAT FREE FOOD", "GF|V|DF", "No Added Sugars",
"PROTEIN BALLS"). These were not rescued because the census is incomplete and
non-random — only the products where the model happened to record something
in `other_claims`, not all products carrying those claims. Rescuing them would
inflate specific fields by an unknown and non-uniform fraction of the true
miss rate. The estimated understatement is ~2 percentage points.

**Cereals category contamination.** The cereals category in all three releases
contains pasta, bread, flour, rusks, breadsticks, and puff pastry products. In
OFF, `en:cereals-and-their-products` is a parent category covering far more
than breakfast cereal; the exclusion list in `bootstrap.py` correctly removes
`en:cereal-pastas` and `en:cereal-semolinas` but not plain `en:pastas`, which
most pasta products carry. The contamination is especially visible in the
France run, which included many Italian products via the FRANCE|SOUTHERN_EUROPE
multi-region tag. Cereals claim figures in all releases describe a
contaminated category. The fix requires both updating `bootstrap.py` and
explicitly re-categorising existing contaminated rows, since `load.py` never
removes products. Deferred to the next bootstrap/cleansing cycle.

**Validator override rate.** The deterministic validator overrode the model's
self-reported `claim_extraction_status` on 33.3% of US, 34.6% of UK and
approximately 30–35% of France rows. This means the validator is applying the
correct `image_context → status` mapping on roughly one product in three.
The underlying LLM reliability on this field is lower than the completion
rates suggest. A future prompt version should consider dropping
`claim_extraction_status` from the schema and deriving it from `image_context`
alone, removing a field the model cannot reliably populate.

**Canada is bilingual.** `US_CANADA` includes Quebec, where packs carry French
text by law alongside English. The English prompt (v4) catches both since many
French claim terms were already present. A dedicated bilingual profile would
be cleaner for future runs.

**Multilingual European packs.** `BENELUX|FRANCE` (5,619 products) and
`FRANCE|DACH` (12,994) are genuinely trilingual. Each is routed to the first
in-scope region's language profile. The French prompt explicitly notes that
English keywords remain valid for multilingual packs.

---

## 10. Future development

- **English v5:** apply the v5.1-fr panel-classification improvements
  (PANEL CLASSIFICATION PRIORITY block, brand identity hints) to the English
  prompt, which ran on v4 without these fixes. Label as `v5-en` to distinguish
  it from the locked release-01 v4 run.
- **English calibration panel:** re-extract a set of already-processed English
  products through the French prompt and compare against stored v4 results.
  Measures prompt drift. Should be run before any future multilingual release.
- **Spanish and German profiles:** when these markets are added, create
  standalone `prompt_vN_es.txt` and `prompt_vN_de.txt` following the same
  structure: identical JSON schema, same 34 claim fields, translated phrase
  coverage, market-specific cautions.
- **`claim_extraction_status` from schema:** remove the field from the LLM
  prompt entirely and derive it deterministically from `image_context` in the
  validator. The model's self-reported value is overridden a third of the time
  and adds noise without improving accuracy.
- **Cereals contamination fix:** update `_EXCLUDE_FROM_CEREALS` in
  `bootstrap.py` and run an explicit DB cleanup. See section 9.
- **Panel-context review for English:** run `review_context_check.py` with
  `--language en --all-categories` on the release-01 CSVs to measure the
  false-exclusion rate. 141 candidate rows identified.
