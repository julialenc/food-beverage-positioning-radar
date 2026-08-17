# Data observations

This document records durable observations that affect methodology,
interpretation, or future data-quality work in Food & Beverage Positioning
Radar. It is not a worklog. Short-lived implementation notes, prompt iteration
details, and one-off debugging trails should live in more specific documents or
scripts.

The observations below describe Open Food Facts data, pipeline behavior, and
market-positioning patterns. They are not product verdicts, health ratings,
legal assessments, or market-share estimates. See `docs/METHODOLOGY.md` for
metric definitions, `docs/LIMITATIONS.md` for interpretation caveats, and
`docs/CLAIM_EXTRACTION.md` for the full OCR/LLM sampling and prompt history.

---

## 1. Data quality and source caveats

### OBS-001 - Open Food Facts is rich but uneven

Open Food Facts is the core data source because it is open, large, structured,
and reproducible. Its open contribution model also creates uneven coverage,
variable completeness, category noise, duplicate category membership, and
occasional nutrition-entry errors.

These issues are expected source characteristics, not failures of the tool. The
pipeline should therefore preserve provenance, keep nulls distinct from zeros,
and surface data-quality caveats rather than silently correcting or imputing
values.

### OBS-002 - Language coverage is strongest for English and French

Early validation showed strong French representation in the source data, which
is structurally expected because Open Food Facts originated in France and has
deep European coverage. Ingredient-marker analysis currently works best for
English and French ingredient text. German remains a plausible extension
because many processing-marker terms overlap with English and French.

Products outside the supported language scope can still retain valid nutrition,
category, brand, and image-analysis data. They should not receive silent
ingredient-marker false negatives.

### OBS-003 - Missing values are not zero

Null values, failed observations, empty strings, and confirmed numeric zeros
carry different meanings. This distinction is especially important for:

- nutrition fields, where a missing value is not a declared zero;
- `pack_claims_found`, where `NULL` means no valid pack observation and `""`
  means a valid front pack was assessed with no taxonomy claim found;
- benchmark and completeness reporting, where absence of source data should not
  be interpreted as a product property.

No pipeline step should silently impute missing values as zero.

### OBS-004 - Nutrition data contains plausible gaps and occasional errors

Open Food Facts nutrition data is broadly usable but includes predictable gaps
and occasional contributor errors:

- Fibre is more often missing than core macronutrients because fibre labelling
  is not mandatory in all markets.
- Waters and unsweetened drinks may have near-zero nutrition values that are
  correct but incompletely entered.
- Hot drink powders and concentrates can look implausible if interpreted as
  ready-to-drink beverages.
- Some values are clear unit-entry errors, such as kcal/kJ confusion or
  sodium/salt confusion.

Physically impossible values are capped to null where the pipeline has hard
plausibility limits. More subtle errors, such as a product reporting a value
several times higher than comparable brand/category peers, require future
data-quality flagging rather than silent correction.

### OBS-005 - Category assignment needs active cleansing

Open Food Facts categories are contributor-assigned folksonomy tags. They are
useful for broad retrieval but are not clean retail shelf definitions. Products
can inherit broad parent tags that put them into analytical categories where
they do not belong.

The most important current issues are:

- **Cereals contamination:** `en:cereals-and-their-products` includes pasta,
  bread, flour, rusks, breadsticks, puff pastry, and related grain products.
  Current cereals release figures are therefore contaminated and should be
  interpreted with that caveat.
- **Snacks contamination:** noodles and related products appear to contaminate
  snacks. The exact Open Food Facts tags still need to be inspected before
  final exclusion rules are changed.

Fixing category contamination requires two steps: update category exclusion
logic in `bootstrap.py`, then explicitly clean or reclassify existing database
rows. A re-bootstrap alone does not revisit contaminated rows that disappear
from the newly filtered input.

### OBS-006 - Use canonical tags where available

The database field `off_categories` stores display/free-text category strings
and can mix languages depending on contributor input. It is useful for display
and exploratory review, but unreliable for systematic exclusion matching.

Where available, category filtering should use `categories_tags`, because the
tag ancestry is language-independent and more consistent for pipeline logic.

### OBS-007 - Duplicate category membership is normal

The same barcode can appear in multiple Open Food Facts categories. For
example, a cereal bar may be tagged as both snacks and cereals. Barcode-level
deduplication is therefore necessary before product-level analysis.

When category overlap is analytically meaningful, it should be captured as
provenance or diagnostic metadata rather than resolved by arbitrary duplicate
rows.

### OBS-008 - Open Food Facts is not a market-share source

Open Food Facts records product presence in a crowdsourced database. It does
not contain sales volume, distribution weight, retail facings, price, or
household penetration. Observed product counts and claim prevalence should not
be described as market share.

The strongest claims this project can make are about patterns in the observed
Open Food Facts sampling frame, with explicit caveats about coverage and
sampling design.

---

## 2. Pipeline and methodology observations

### OBS-009 - Bulk export and incremental API have different jobs

The Open Food Facts search API is suitable for small incremental updates, but
it is not the right mechanism for initial database population at scale. The
production path is:

- `bootstrap.py` for one-time or periodic bulk-export population;
- `ingest.py` for small API-based incremental updates.

These paths should not be conflated. Initial population should use the bulk
export; weekly or monthly updates can use the API with modest batch sizes.

### OBS-010 - Ingredient and pack evidence are separate layers

Ingredient text describes what a product contains. Front-of-pack text describes
what the manufacturer communicates. These are related but not equivalent.

This distinction explains several design choices:

- Ingredient-marker analysis must remain auditable and conservative.
- Front-pack claim extraction comes from OCR/LLM image observation, not from
  ingredient inference.
- Ingredient/name fallback may be used only when no valid pack observation
  exists, and must be labelled as weaker evidence through `claim_source`.

The distinction is central to interpreting claim-benchmark intersections.

### OBS-011 - Ingredient dictionaries need validation before scaling

Early validation found false positives from ingredient terms that were present
for technical or sensory reasons rather than positioning reasons. Examples
included colorants, chicory fibre used as a texture ingredient, and whey in
confectionery.

The durable lesson is that dictionary expansion must be validated on known
examples before scaling to a new language or category. Broad ingredient terms
should require context when they can appear for non-positioning reasons.

### OBS-012 - Nutrition benchmark thresholds use UK FSA references

Nutrition benchmark flags use the UK Food Standards Agency front-of-pack
thresholds as a single comparison scheme. EU Regulation 1169/2011 requires
nutrition declaration in a standard format, but does not define the high/low
thresholds used here.

The flags are neutral reference indicators, not legal compliance statements,
health-risk classifications, or product recommendations. US products use the
same per-100g/per-100ml reference scheme for comparability.

### OBS-013 - Sports and functional-use contexts require caution

Sports nutrition products, energy gels, protein bars, and endurance drinks can
show benchmark flags that reflect intended product use rather than unexpected
composition. The current pipeline does not infer use occasion, channel, or
consumer context.

These products can remain in the analysis, but interpretation should avoid
treating benchmark flags as product defects.

### OBS-014 - OCR quality affects claim visibility

OCR performs well on clear pack images but degrades on dark backgrounds,
angled or cropped photos, small thumbnails, and highly stylized typography.
This can understate claims for brands whose pack design is visually rich but
hard to read from Open Food Facts images.

The Oatly case is the clearest example: claims exist on packaging, but
thumbnail OCR fragmented large typography into disconnected tokens. This is an
image-quality limitation, not a brand or product characteristic.

### OBS-015 - Panel classification can falsely exclude front packs

Some valid front packs look like legal or ingredient panels after OCR flattens
visual hierarchy. French cheese and organic dairy packs are especially prone
to this problem because front labels often contain certification, origin,
producer, and short ingredient information.

The French release added a narrow second-pass panel-context review for dairy
products, which rescued many valid observations. The same issue may exist at a
lower rate in the English release. See `docs/CLAIM_EXTRACTION.md` for the full
review design, release counts, and remaining caveats.

### OBS-016 - Some claim-like text remains unmapped

The OCR/LLM process can capture claim-like phrases in `other_claims` or
`detected_claim_phrases` without mapping them into a boolean taxonomy field.
In release-01 this likely understated claim prevalence by a small amount.

The current approach is conservative: do not rescue a non-random subset of
unmapped text unless the rescue rule can be applied consistently and audited.

### OBS-017 - Composite scores are legacy/internal

`composition_marker_score` and `positioning_composition_gap` remain in parts
of the historical pipeline, but they are not user-facing MVP metrics. The
current Streamlit product should emphasize observed evidence layers,
benchmark flags, intersections, completeness, and category/brand/region
patterns rather than proprietary composite scores.

### OBS-018 - Reporting tables must not confuse updates with the market snapshot

`weekly_brand_summary` is an ingredient-stage QA table. It is not the final
claim or market-intelligence summary.

`weekly_brand_positioning_summary`, produced by `db_summary.py`, is the
reporting-stage summary. It should be computed from the full current database
snapshot, not only the products changed in a given update period. Otherwise a
trend chart could confuse "products changed this week" with "the observed
market this week."

---

## 3. Market-pattern observations

### OBS-019 - Brand-level analysis is usually more interpretable than company-level analysis

Brand-level patterns are more meaningful than parent-company averages because
large companies own heterogeneous portfolios. A company may span mineral
water, yogurt, cereals, snacks, and sports products; averaging across those
products can erase the positioning logic.

Company mapping remains useful for navigation and roll-up views, but category
and brand filters should be applied before interpreting patterns.

### OBS-020 - Specialist and mainstream brands behave differently

Specialist functional brands often show high claim density because the whole
portfolio is built around a benefit territory. These brands are useful
reference points for claim intensity, but they can dominate rankings.

Mainstream brands with dedicated functional product lines are often more
analytically interesting because they show how established brand equity is
extended into a specific positioning territory.

### OBS-021 - Some brands use portfolio-level claim architecture

Large brands can distribute claim territories across sub-brands or product
tiers. Examples observed during development include:

- Danone dairy sub-brands occupying different territories such as immune
  support, gut health, protein, and light/low-fat positioning.
- Kellogg's/Special K using fortification, protein, fibre, heritage, and
  comparative claims across different product tiers.
- Gerble using dense multi-claim positioning across a focused biscuit/snack
  portfolio.

These examples support sub-brand and category-level analysis rather than only
company-level aggregation.

### OBS-022 - Communication style differs by market and brand heritage

Observed packs use different communication styles:

- authorized health-claim style language;
- numeric claims such as grams of protein or percentage reduction;
- transparency or minimal-ingredient positioning;
- proprietary branded nutrient or ingredient systems;
- free-from, organic, sustainability, origin, and heritage claims.

Differences between US/UK and French claim density may reflect a mixture of
category mix, sampling-frame differences, pack design, and regulatory context.
This project observes those patterns but does not isolate causal regulatory
effects.

### OBS-023 - Private label can indicate mainstreaming of a claim territory

When private label products adopt a claim type, that claim may have moved from
premium-brand differentiation toward category expectation. Examples observed
during development include no-added-sugar claims on private label fruit purees
and functional/free-from language on lower-price products.

This is a market-positioning signal, not a claim about product quality.

### OBS-024 - Product examples are illustrative, not representative

Named products and brands in this document are examples used to explain
methodology or interpretation. They should not be treated as representative
samples, endorsements, criticisms, or legal assessments.
