# Data observations

Running notes on data quality, pipeline behaviour, and market patterns
observed during development of Food & Beverage Positioning Radar.

This file documents what was found, what was fixed, and what remains as
a known limitation. It is written for technical contributors and reviewers.
Market-pattern observations describe analytical signals, not product
verdicts. See `docs/LIMITATIONS.md` for a structured summary of limitations
relevant to interpretation. See `docs/METHODOLOGY.md` for metric definitions.

---

## Data quality observations

### OBS-001 — French language dominance in source data

**Date:** 18 May 2026

**Finding:** Language distribution across 286 clean rows: FR 69%, OTHER 14%,
EN 11%, BOTH 3% (bilingual packaging, common in Switzerland/Belgium/Canada),
UNKNOWN 2%.

French dominance is structural, not a sampling artifact. Open Food Facts was
founded in France and French contributors remain the most active globally.

**Implication for ingredient-based analysis:** Ingredient marker dictionaries
must cover both EN and FR variants. Most processing-related markers share
Latin roots across both languages (e.g. maltodextrin/maltodextrine,
lecithin/lecithine, glucose syrup/sirop de glucose).

**Implication for coverage:** Results are strongest for Western European
markets (France, Belgium, Switzerland). Findings should not be generalized
to global markets without the caveat in `docs/LIMITATIONS.md`.

---

### OBS-002 — Nutritional null rates

**Date:** 18 May 2026

**Finding:** Core macros (fat, carbs, protein, sugar) missing ~9%. Fibre
missing 22% — structurally expected, as fibre labelling is not mandatory in
all markets. Salt missing 6%. All within acceptable range for a crowdsourced
database.

**Implication for future segmentation:** Any clustering or segmentation
analysis will need a strategy for missing nutritional values. Options
include dropping rows missing more than two macro fields for clustering
only (while retaining all rows in the main dataset), or variable-feature
approaches. Imputation is not used in this pipeline.

---

### OBS-003 — Energy outliers (data errors)

**Date:** 18 May 2026

**Finding:** Two products had energy_kcal values of 3,833 kcal/100g.
Maximum physically possible is approximately 900 kcal/100g (pure fat).
Both were capped to null by `clean.py`. Likely cause: unit entry error —
a kJ value entered in the kcal field.

**Implication:** Outlier capping in `clean.py` is physically grounded, not
arbitrary. The cap values in NUTRIMENT_CAPS should be reviewed if the
category scope expands to include concentrated ingredients or supplements.

---

### OBS-004 — Low completeness products cluster in beverages and hot drinks

**Date:** 18 May 2026

**Finding:** 22 products scored below 50/100 on completeness. Two distinct
patterns: (a) waters (Ain Saïss, Aquafina, Oulmes) — nutritional values are
near-zero and technically correct but structurally unfilled; (b) hot drink
powders (Ricoré, Nesquik, Poulain) — serving-based nutrition more common
than per-100g in this category.

One barcode-only entry (product_name = "41022", score = 18) is a candidate
for removal in production. One Arabic-script product is correctly penalized
by the English/French-only language detection.

**Implication:** The completeness score conflates two distinct problems:
genuinely incomplete data entry, and products where near-zero values are
correct but unfilled (waters). Waters may warrant a category-specific
handling rule in a future version.

---

### OBS-005 — Nutri-Score distribution is contributor-biased

**Date:** 18 May 2026

**Finding:** A and B combined (126) outnumber D and E combined (94) in the
sample. This is not representative of supermarket shelves, where D and E
products are more prevalent in snack and beverage categories.

**Likely cause:** Contributor selection bias. Health-conscious people are
more likely to scan and submit products to Open Food Facts.

**Implication for analysis:** Trend analysis (e.g. claim category growth
over time) is more reliable than absolute prevalence estimates. Claim
distribution within Nutri-Score band is more defensible than overall
Nutri-Score distribution as a population estimate.

---

### OBS-006 — Duplicate barcodes from multi-category API queries

**Date:** 18 May 2026

**Finding:** 14 duplicate barcodes found in 300 raw rows (4.7%). All
resolved by keeping first occurrence. Cause: the same product appearing
in multiple OFF categories (e.g. a bar tagged as both "snacks" and
"cereals"). The query fetches by category, so cross-category products
appear multiple times.

**Implication:** Barcode-level deduplication in `clean.py` is correct and
sufficient. In future, logging which categories each barcode appeared in
before deduplication may be useful for category-overlap analysis.

---

### OBS-007 — Reality check results: data quality broadly sound

**Date:** 18 May 2026

**Finding:** Four calorie plausibility flags, zero sugar/carb or
saturated/total fat inconsistency flags. Main data quality issues are
category misclassification (one water in snacks) and quantity field
formatting (European decimal commas, spelled-out units), neither of which
affects nutritional or ingredient analysis.

One Carrefour cookie product had an energy value 10× too low, likely a
per-serving entry error. Nescafe Classic (267 kcal/100g instant powder)
and Caobel chocolate powder (366 kcal/100g) are plausible — hot drink
powders sit outside the standard beverage kcal range.

**Fix applied:** European decimal commas normalized in `clean.py` Step 3,
reducing quantity-field parse failures.

---

### OBS-015 — Salt outlier: 295g/100g detected and capped

**Date:** 20 May 2026

**Finding:** One product had salt_100g = 295 — physically impossible (pure
salt = 100g/100g). Likely contributor entered mg instead of g, or confused
sodium with salt (sodium × 2.5 = salt). Cap of 100g/100g caught it.

**Implication:** Sodium/salt unit confusion is a known Open Food Facts data
issue. A sodium-field cross-check may be worth adding to future validation.

---

### OBS-018 — Invalid image URL pattern in bulk export

**Date:** 22 May 2026

**Finding:** Products without a front-of-pack image have image_url containing
`/invalid/` (e.g. `.../images/products/invalid/front_en.6.400.jpg`) — this
is Open Food Facts' deliberate placeholder, not a random 404.

**Filter applied before image-based analysis:**
`df = df[~df["image_url"].str.contains("/invalid/", na=True)]`

Expected valid image rate: approximately 60–70% of full database.

---

## Coverage and language observations

### OBS-008 — Ingredient analysis scope: EN and FR only in v1

**Date:** 18 May 2026

**Finding:** `nlp_eligible` flag covers EN + FR + BOTH only. Coverage: 239
of 286 rows (84%). Excluded rows (OTHER and UNKNOWN) retain full nutrition
data and are included in benchmark flag computation and future segmentation.
They are excluded only from ingredient marker analysis, where an
English/French-only dictionary would produce silent false negatives.

---

### OBS-009 — German identified as v1.5 language extension candidate

**Date:** 19 May 2026

**Finding:** Austria accounts for approximately 3.5% of sample. German
ingredient vocabulary shares significant overlap with EN/FR (maltodextrin,
lecithin, glucose-sirup, palmöl), making dictionary extension low-effort.

**Decision:** Deferred to v1.5. Extension before validation of EN/FR
coverage risks introducing false positives.

---

### OBS-012 — Production data strategy: bulk export plus weekly API diff

**Date:** 19 May 2026

**Finding:** The Open Food Facts search API is unreliable for bulk pagination
at scale (503 errors), attributable to non-profit server infrastructure.

**Production strategy:** Phase 1 — one-time bulk export from OFF's full CSV
download, filtered to relevant categories (approximately 50,000–100,000
products). Phase 2 — weekly API diff on `last_modified_t > 7 days`. INSERT
OR REPLACE on barcode keeps the database idempotent across runs.

---

## Pipeline methodology observations

### OBS-010 — Ingredient marker false positives: colorant context

**Date:** 19 May 2026

**Finding:** Two false positive patterns found on the 286-product validation
sample:

1. Curcuma/paprika triggering a functional claim signal on Harry's brioche.
Root cause: used as natural colorants ("extraits végétaux à pouvoir
colorant"), not as functional ingredient claims. Fix: replaced "curcuma"
with "extrait de curcuma" — requires extract context to fire.

2. Chicory fibre triggering a prebiotic signal on Harry's sandwich bread.
Root cause: chicory fibre as a texture/bulk ingredient, not positioned as
a prebiotic supplement. Fix: replaced "chicorée" with specific prebiotic
forms only (inulin de chicorée, extrait de chicorée).

**Lesson:** Validate ingredient dictionaries on a known sample before
scaling. The validation loop (run → spot → fix → rerun) should be repeated
for each new category added.

**Remaining risk:** More false positives likely in the OTHER language group
and will surface when German is added in v1.5. French products using
saffron, beetroot, or spirulina as colorants may trigger adaptogen or
fortification signals. Manual review of the top 20 scored products before
any published analysis is recommended.

---

### OBS-013 — False positive: whey as texture ingredient

**Date:** 19 May 2026

**Product:** DINOSAURUS Chocolat (Lotus)

**Finding:** "Whey product" in chocolate confectionery ingredients triggered
a protein claim signal. Whey here is a texture/flavour ingredient, not a
protein supplement signal. Same class as the chicory fibre false positive
(OBS-010).

**Fix:** Replaced bare "whey" with "whey protein" and "whey protein isolate"
— requires explicit protein supplement context to fire.

---

### OBS-016 — Ingredient presence vs pack claim: a v1 pipeline distinction

**Date:** 21 May 2026

**Product:** DINOSAURUS Chocolat (Lotus)

**Finding:** A product with a functional ingredient (pea protein added for
texture) will be detected by ingredient-based analysis even when no
front-of-pack claim is made. This is technically correct behaviour but
represents a meaningful distinction: a product adding a functional
ingredient quietly is analytically different from a product claiming it
loudly on pack.

**Implication:** Ingredient-based claim signals (`ingredient_based_claim_signals_found`)
and pack claims (`pack_claims_found`) should be read as two separate evidence
layers, not as equivalents. The positioning-to-composition gap is most
meaningful for products where both layers are populated.

**No fix required** — the detection is technically correct. Documented here
as a known distinction relevant to interpretation.

---

### OBS-017 — Energy drink baseline calibration

**Date:** 21 May 2026

**Finding:** An energy drink claiming energy (caffeine, taurine) is making
a tautological claim, not a positioning claim in tension with composition.
Energy claim signals were excluded from the composition_marker_score
Components B and C computation accordingly.

**Result:** Products making only a basic energy claim receive lower
composition marker scores than products also making fortification or
adaptogen claims. Energy drinks with broader functional positioning
(fortification, performance concepts) are still captured.

---

### OBS-027 — Nutrition benchmark threshold sourcing

**Date:** 26 May 2026 (corrected: June 2026)

**Finding:** The reference thresholds used for nutrition benchmark flags
(sugar >22.5g, saturated fat >5g, fat >17.5g, salt >1.25g per 100g solid;
halved per 100ml liquid) follow the **UK Food Standards Agency's voluntary
front-of-pack labelling guidance**, not EU Regulation 1169/2011 directly.
EU 1169/2011 requires these nutrient values to be declared in a standard
format per 100g/100ml, but explicitly does not define high/low thresholds —
that was deliberately left to Member States and food businesses.

**Original entry attributed thresholds to "EU Regulation 1169/2011 HIGH
thresholds" — this has been corrected throughout all documentation.**

US-market products use the same per-100g thresholds as European products
for consistency; FDA per-serving daily-value percentages are not comparable
to per-100g data.

**Status:** Resolved. Correctly attributed in `docs/METHODOLOGY.md`,
`docs/COLUMN_DESCRIPTIONS.md`, and `docs/LIMITATIONS.md`.

---

### OBS-028 — Extraction calibration: sports context, promotional claims, taxonomy

**Date:** 10 June 2026

**Finding 1 — Sports nutrition context:**
Sports nutrition products (energy bars, protein gels, endurance drinks)
may show nutrition benchmark flags (high sugar, high energy) that reflect
intended product use rather than an unexpected product profile. The pipeline
does not detect distribution channel or intended use context. Documented in
`docs/LIMITATIONS.md`.

**Finding 2 — Promotional comparatives vs positioning comparatives:**
"+10% Gratuit", "+25% more" promotional stickers triggered a comparative
claim signal. These are commercial promotions (volume/price), not
positioning comparatives ("-30% sugar vs market average"). Fix applied:
prompt rule added specifying that "+X% free/gratuit/bonus pack" maps to
`other_claims` only, not `comparative_claim`.

**Finding 3 — `no_claims_detected` contradiction:**
Several products returned both a specific claim (e.g. `no_added_sugar=true`)
and `no_claims_detected=true` simultaneously. Fix applied: prompt rule
added specifying that `no_claims_detected` must be false if any specific
claim field is true.

**Finding 4 — Taxonomy mapping corrections applied:**
- `vegan_claim`, `plant_based_claim`: reclassified from NATURAL_ORGANIC to
  FREE_OF/free_from
- `gluten_free_claim`, `dairy_free_claim`: reclassified from
  FREE_OF/no_artificial to FREE_OF/free_from
- `no_added_sugar`, `reduced_sugar`: reclassified to FREE_OF/no_added_x
- `clean_label_claim`, `minimal_ingredients_claim`: reclassified from
  NATURAL_ORGANIC to FREE_OF/no_artificial

---

## Market pattern observations

These observations describe analytical patterns in the current dataset.
They describe what the data shows, not product quality or brand intent.

### OBS-011 — Gerblé: multi-claim positioning architecture

**Date:** 19 May 2026

**Product sample:** 17 Gerblé products in 286-product sample; 49 products
in full analyzed set.

**Finding:** The analyzed Gerblé product range shows a high density of
simultaneous claim types across its product range. A representative product
(Goûter Pépites de Chocolat) carries the following on-pack signals:

- VITALITÉ brand concept (proprietary positioning mark)
- Comparative sugar reduction vs market average
- Comparative saturated fat reduction vs market average
- Comparative salt reduction vs market average
- Source de magnésium
- Source de Vitamine E
- Aucun colorant
- Arômes exclusivement naturels
- Sans huile de palme
- Fabriqué en France (origin claim)
- Rainforest Alliance certified (sustainability claim)
- RECETTE ENCORE MEILLEURE (reformulation claim)

Composition context: NOVA 4, Nutri-Score C/D, contains emulsifier, added
flavour, dextrose, starch, and raising agents.

**Ingredient-based signals captured:** 4 of 12 claim types.
**Pack-image analysis expected to capture:** 10–12 of 12 claim types.
This product range is well-suited for demonstrating the analytical difference
between ingredient-only signals and pack-image claim extraction.

**Comparative claim note:** Claims 2–4 compare to "average biscuits on
the market," not to an absolute nutritional reference. The benchmark is
not stated on pack.

**Portfolio pattern:** In the analyzed set, all but 2 of the 49 Gerblé
products are NOVA 4. All make at least one fortification or functional claim.
This is a useful example of a focused brand portfolio with consistent
multi-claim positioning.

---

### OBS-014 — Brand-level aggregation is most meaningful for focused brands

**Date:** 20 May 2026

**Finding:** Brand-level metric averages produce different levels of
interpretive value depending on portfolio breadth.

Focused brands (Gerblé avg n=49, consistent biscuit/snack portfolio):
averages are meaningful and internally consistent.

Conglomerate brands (Nestlé, Danone, Unilever): portfolio spans from
mineral water (near-zero scores) to ultra-processed snacks, and
sub-brands appear as separate `primary_brand` entries (Chocapic, Nesquik,
Fitness as distinct from Nestlé), further fragmenting the picture.

**Implication for reporting:** Category filters should be applied before
brand comparisons. The company mapping in `data/reference/company_brand_mapping.csv`
supports roll-up views; these should be labeled as portfolio-level
aggregations and interpreted with awareness of portfolio heterogeneity.

---

### OBS-019 — Pack-image claim extraction: coverage and signal uplift

**Date:** 24 May 2026

**Finding:** After merging ingredient-based analysis with pack-image claim
extraction across 4,714 products:

- Products with uplift in positioning_composition_gap (v1→v3): mean +8.4
  points, max +55.0 points
- 1,302 products with gap uplift >20 points — front-of-pack communication
  adds meaningful analytical signal beyond ingredient text alone

**Intersection patterns confirmed at scale:**
- Sugar claim + sugars above reference threshold (>8g/100g): 95 products
- Protein claim + saturated fat or energy above reference threshold: 95 products
- Fibre claim + NOVA 4 + sugars above reference threshold (>15g): 82 products
- Plant-milk fortification claim + energy above reference threshold (>60 kcal/100ml): 112 products

**Implication:** Pack-image claim extraction provides meaningful analytical
signal beyond ingredient text. The two-layer architecture (ingredient-based
signals + vision-based claims) captures distinct product dimensions.

---

### OBS-020 — Claim density varies by brand positioning type

**Date:** 24 May 2026

**Finding:** The highest positioning_composition_gap scores in the vision-
analyzed sample belong predominantly to specialist functional brands (Fiber
One, Special K Protein, Atkins, Muscle Milk, Pure Protein) — brands whose
entire portfolio is built around functional positioning claims.

**Analytically more informative:** mainstream multi-category brands
(Kellogg's, Nestlé, Danone, Mars, Emmi) that apply functional claim
language to selected product lines within broader portfolios.

**Implication for reporting:** Filtering to brands with n ≥ 20 products in
the analyzed sample removes specialist brands with small product counts
and surfaces portfolio-scale patterns in mainstream brands.

**Brand fragmentation note:** "fiber one", "fibre one", and "fibre 1" are
the same brand — three separate entries due to EN/FR spelling variants and
accent stripping. Same issue as nestlé/nestle (OBS-014). Company mapping
handles parent-level roll-ups; sub-brand normalization may be needed for
specific analytical views.

---

### OBS-021 — OCR quality limit: stylized pack typography

**Date:** 24 May 2026

**Finding:** Oatly shows near-zero vision-extracted claim scores across 23
products. Initial interpretation attributed this to brand narrative
positioning (environmental/sustainability messaging rather than regulatory
claim language). This interpretation was incorrect.

**Corrected finding:** OCR quality is poor for all 23 Oatly products due
to large, stylized typography that fragments into disconnected tokens in
Open Food Facts thumbnail images. Claims are present on the actual
packaging (100% Vegan, No dairy/nuts/gluten, Organic, Climate footprint,
Bio) but are unreadable from available images.

**Implication:** Brands using decorative, large-format, or handwritten
typography are systematically under-represented in pack-image analysis.
This is an image quality limitation, not a product or brand
characteristic. See `docs/LIMITATIONS.md`.

**Other brands with similar OCR limitations:** Innocent (large playful
typography), Nakd (rustic packaging design). Both show lower extracted
claim counts than ingredient-text signals would predict.

---

### OBS-022 — Kellogg's/Special K: multi-claim positioning across product tiers

**Date:** 24 May 2026

**Finding:** The analyzed Kellogg's/Special K products show multiple claim
types across product tiers:

- Base cereals: fortification claims (vitamins, minerals)
- Premium cereals: protein claims (Xg per serving)
- Bars: protein + vitamin stack
- Children's products: no-artificial claims
- Heritage line: origin claims ("THE ORIGINAL" on Corn Flakes)
- Comparative claims: "30% LESS SUGAR", "TASTIER THAN EVER"
- Gender-targeted positioning: "CREATED FOR WOMEN" on Special K Protein,
  with vitamin D emphasis

A protein-fat benchmark intersection is observed on Special K Protein Meal
Bars: 12g protein appears alongside 5g saturated fat and 12g sugars visible
simultaneously on pack.

OCR quality: approximately 60% of products readable. Key claims are readable
across the readable subset.

**Implication:** Kellogg's/Special K is a useful example of how claim
architecture can vary across product tiers within a broader brand system.
It also illustrates why pack-image extraction adds value beyond ingredient
text alone: several positioning signals are visible on pack but would not
be reliably inferred from ingredients.

---

### OBS-023 — Claim density patterns: US-heritage vs European-heritage brands

**Date:** 24 May 2026

**Finding:** Brands with US market heritage tend to load front-of-pack with
more simultaneous claim types (badge + tick-box + circular callout +
comparative percentage) than brands with European market heritage, which
tend to use fewer claims with more ingredient or process focus.

Examples in the same category (breakfast biscuits):
- Gerblé: VITALITÉ concept + SANS HUILE DE PALME + comparative sugar
  reduction (3 distinct claim types)
- Belvita: "4 hours of steady energy" — a single energy duration claim
  without an explicit comparative reference

Both Gerblé and Belvita show the fibre-emphasis intersection pattern
(wholegrain claims on NOVA 4 products with Nutriscore D/E).

**Possible contributing factor:** EFSA's regulated health claim framework
constrains claim language more tightly in Europe than FDA/FTC standards
in the US. This affects both European brands and how US multinationals
localize claims for European markets.

---

### OBS-024 — Danone: distinct claim territories across sub-brands

**Date:** 24 May 2026

**Finding:** The analyzed Danone dairy sub-brands show distinct claim
territories within the dairy category:

- Actimel: immune support
- Activia: gut health
- HiPRO / YoPRO: protein
- Taillefine: low-fat / light positioning
- Danonino: kids / no added sugar

Each sub-brand appears to occupy a different segment of the functional
claim taxonomy.

Actimel uses authorized health-claim style language ("vitamines B6 & D
contribuent au fonctionnement normal du système immunitaire"). The immune
signal is partially captured via fortification and probiotic claim
detection; a dedicated `immune_claim` field would improve precision.

**Implication:** Danone is a useful example of sub-brand-level positioning
architecture. Company-level aggregation alone would flatten these
differences, so sub-brand and category-level views are more informative
for this type of portfolio.

---

### OBS-025 — Four positioning typologies identified

**Date:** 24 May 2026

**Finding:** Brand-by-brand analysis reveals four structurally distinct
positioning approaches:

1. **Regulatory language (Actimel):** EU Regulation 432/2012 approved
   claim language, applied to specific vitamin-delivery vehicles. Precise,
   jurisdiction-specific, and auditable.

2. **Numeric claims (Kellogg's Special K):** Hard numbers — Xg protein,
   Xg fibre — used as primary differentiators. Directly verifiable from
   nutrition panel.

3. **Transparency positioning (Kind):** Ingredient transparency itself
   used as a claim ("ingredients you can see & pronounce"). Positions
   ingredient simplicity as the brand's functional attribute.

4. **Proprietary positioning marks (Nestlé):** Branded ingredient or
   nutrition systems (OPTI-START, OPTI-GROW, OPTI-DÉJ, ACTIVGO) that
   bundle multiple nutrients under a single proprietary mark. These are
   not regulated claims; they are brand constructs.

**Emmi observation:** Two-tier portfolio — traditional dairy products with
minimal claims alongside Energy Milk/protein line with explicit numeric
positioning. PUR line uses minimal-ingredient positioning; ingredient list
shows three ingredients including sugar.

---

### OBS-026 — Private label adoption of functional claim language

**Date:** 24 May 2026

**Finding:** Intermarché "U" private label fruit purées carry "SANS SUCRES
AJOUTÉS" on pack, alongside the mandatory disclaimer "contient les sucres
naturellement présents dans les fruits" required by EU labelling regulation.
14 of 22 sampled products make this claim.

Private label brands (U, Carrefour, Lidl Vemondo) are adopting functional
claim language at lower price points. Sugar-reduction or absence claims are
present across the full price range in this category, not only in premium
branded products.

**Implication for category analysis:** Claim presence at private label level
indicates that a claim type has become a category-level expectation rather
than a brand differentiator.

---

### OBS-027 — Incorrect energy value in OFF: Hipro Saveur Coco
**Date:** 15 July 2026
**Status:** Deferred — candidate for future data quality sweep
**Brand:** hipro (Danone)

**Finding:** OFF reports 238 kcal per 100g for Hipro Saveur Coco. Comparable
Hipro products (Hipro Banana, Hipro Vanille, Hipro à Boire) all report
approximately 55–65 kcal per 100g, consistent with a high-protein low-fat
dairy drink format. Pack verification confirms the actual value is
approximately 60 kcal per 100g. The 238 kcal figure appears to be a
contributor data entry error.

**Impact in the tool:** Hipro Saveur Coco shows 🔴 red on Energy in the IS
table and appears as an outlier within the hipro brand view. The clean.py
outlier cap (900 kcal) does not catch this value as it is below the
physical maximum.

**Heuristic for systematic detection:** Flag products where energy_kcal
differs by more than 3× from the brand-category median. Hipro Saveur Coco
(238 kcal) vs hipro/dairies median (~60 kcal) = ~4× — would be caught by
this rule. Implementation deferred to the data quality flagging pass.

**Recommended action:** Report correction to Open Food Facts. In the app,
consider a per-product data quality warning when energy deviates more than
3× from the brand median, surfaced in the product card.
