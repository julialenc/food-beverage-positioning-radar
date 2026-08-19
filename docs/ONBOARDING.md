# Food & Beverage Positioning Radar — Project Onboarding

This document briefs a new AI or human collaborator before they touch the
project. Read it fully, then read `README.md`, `docs/METHODOLOGY.md`,
`docs/ADR.md`, and the specific document/script relevant to the requested task.

**GitHub repo:**  
https://github.com/julialenc/food-beverage-positioning-radar/tree/main

**Local working directory:**  
`C:\Users\julia\food-beverage-positioning-radar`

**Current checkpoint:** 20 August 2026. The Streamlit MVP has just been
cleaned and frozen. The next workstream is data quality review, starting with
Open Food Facts category contamination.

---

## 1. Project in one sentence

Food & Beverage Positioning Radar is a neutral Streamlit market-intelligence
board for CPG professionals, analysts, consultants, and nutrition specialists.
It uses Open Food Facts data plus OCR/LLM pack-image extraction to show what
packaged products **are** (nutrition, ingredients, processing, ownership,
category context) and what they **tell** (front-of-pack claims).

It is not a product ranking tool, legal assessment, market-share estimate,
consumer recommendation app, or health-verdict system.

---

## 2. Working rules

- Default mode is review first. Do not edit unless Julia explicitly says
  `IMPLEMENT`.
- Work on one primary file/task at a time.
- Prefer minimal, explainable changes over broad refactors.
- Do not change research definitions without explicit approval.
- Preserve provenance, intermediate CSVs, and release reproducibility.
- NULL is not zero. Never silently impute missing values.
- Use neutral language: "observed records", "selected base", "higher/lower",
  "data coverage"; avoid "best", "worst", "healthier", "market leader", or
  "market share" unless explicitly discussing non-scope.
- Distinguish Open Food Facts structured data from OCR/LLM claim extraction.
  Market Overview aggregate views use OFF composition data only.

---

## 3. Tech stack

- **Language:** Python 3.12 on Windows
- **Shell Julia uses most:** CMD
- **Virtual environment:** `.venv\Scripts\activate`
- **App:** Streamlit with `st.Page` / `st.navigation`
- **Database:** SQLite at `database/positioning_radar.db` (gitignored)
- **Source:** Open Food Facts
- **OCR:** Azure AI Vision Read API
- **LLM:** Azure OpenAI `gpt-4.1-nano`
- **Current OCR/LLM cost record:** approximately 20 CHF for the US, UK, and
  France runs together

Run the app:

```bat
.venv\Scripts\activate
streamlit run app.py
```

`app.py` uses Market Overview as the default landing page.

---

## 4. Repository structure

```text
app.py                    # Streamlit entry point; Market Overview is default

pages/
  overview.py             # Market Overview — frozen MVP, 3 views
  search.py               # Product Explorer — frozen unless bug/factual issue
  methodology.py          # User-facing methodology page
  about.py                # User-facing project/about page

shared/
  db.py                   # DB helpers, resolver, cached lookups
  components.py           # Shared UI styling/components
  labels.py               # UI label parser

pipeline/
  bootstrap.py            # OFF bulk export download/filter/category assignment
  ingest.py               # Incremental OFF API ingestion
  clean.py                # Cleaning, brand normalization, completeness
  analyze.py              # Ingredient/composition analysis
  load.py                 # SQLite DDL/load contract
  vision_extract.py       # OCR + LLM extraction
  merge_scores.py         # Merge vision outputs into DB
  tag_claims.py           # Claim taxonomy + nutrition benchmark flags
  smart_sample.py         # Sampling for release extraction
  review_context_check.py # Second-pass panel-context review
  compute_axis_ranges.py
  compute_region_benchmarks.py
  compute_profile_intersections.py
  validate_tags.py
  verify_schema.py
  export_schema.py
  db_summary.py

data/
  country_region_mapping.csv
  reference/
    brand_alias_mapping.csv       # variant brand -> canonical brand
    company_brand_mapping.csv     # canonical brand -> parent/company owner
    README.md                     # reference-data notes

database/
  schema.sql
  positioning_radar.db            # local only, gitignored

docs/
  METHODOLOGY.md
  CLAIM_EXTRACTION.md
  COLUMN_DESCRIPTIONS.md
  BRAND_COMPANY_MAPPING.md
  UI_LABELS.md
  OBSERVATIONS.md
  LIMITATIONS.md
  ADR.md
  ONBOARDING.md
```

Generated/local files such as SQLite WAL/SHM files, `.claude/`, root local
notes, raw data, and sample/output CSVs should remain untracked unless Julia
explicitly decides otherwise.

---

## 5. Current app state

### Streamlit entry point

`app.py` navigation order:

1. Market Overview — default landing page
2. Product Explorer
3. Methodology
4. About

### Market Overview — frozen MVP

`pages/overview.py` has three frozen views:

1. **Category Report**  
   Summarizes one selected country-category base, then drills into company /
   owner, brand, and product records. Company rows are navigation only; brand
   summaries and product rows contain nutrition values. Uses OFF structured
   composition data only, not OCR/LLM claim extraction.

2. **Brand Compare**  
   Compares two brands side by side within the selected country-category base.
   Each side has optional Company / owner and Brand selectors. A brand can be
   selected without knowing the company. If a company is selected but no brand
   is selected, no company-level nutrition summary is shown.

3. **Product Map**  
   Scatter/WebGL map of observed product records across selected nutrition
   dimensions. Includes company/brand filters, reset filters, chart options,
   point selection, and a single selected-product detail card with image.

Default Market Overview scope:

```text
France · Snacks
```

Default Brand Compare brands in that scope:

```text
Brand A: kitkat
Brand B: mars
```

### Product Explorer — frozen

`pages/search.py` is considered frozen for MVP unless Julia reports a bug,
incorrect definition, or factual/UI trust issue. It supports product search,
filters, export of visible rows, selected product details, pack images, claims,
composition fields, and resolver-aware company filtering.

---

## 6. Current analytical release state

See `docs/CLAIM_EXTRACTION.md` for the detailed record.

- US/UK release: `release_2026_01_us_uk`
- France release: `release_2026_01_fr`
- Combined valid front-of-pack observations: **17,127**
- English prompt: frozen v4 for release-01
- French prompt: frozen v5.1-fr plus second-pass panel-context review for
  release-02

The release CSVs carry frozen sampling/category fields. Cleaning the live DB
does not invalidate historical release figures if those frozen release outputs
are kept intact and documented.

Open next extraction/prompt tasks:

- Run English panel-context review on release-01 candidates.
- Consider English v5 / prompt-drift calibration after data-quality cleanup.

---

## 7. Brand/company mapping state

The project now supports three ownership-resolution statuses in
`data/reference/company_brand_mapping.csv`:

- `direct`
- `market_scoped`
- `manual_review`

Scoped duplicate rows are allowed when ownership depends on market/country or
product scope. Examples include Cheerios, Kellogg's, KitKat, Lipton, and
Schweppes. `shared/db.py` resolves ownership using brand normalization,
country/region scope, direct rows, and manual-review fallbacks.

Important principle:

```text
Company / owner is a directional reporting filter, not a legal ownership audit.
```

Use Open Food Facts country tags honestly and preserve manual-review fallbacks
when scope is missing or conflicting.

---

## 8. Known data-quality issues

These are the next credibility risks to handle.

### Category contamination

**Cereals contamination is diagnosed but not fixed.** OFF parent category
`en:cereals-and-their-products` pulls in pasta, bread, flour, rusks, and
related products. This affects live category figures and historical cereals
release interpretation.

Known fix direction:

1. Update `_EXCLUDE_FROM_CEREALS` in `pipeline/bootstrap.py`.
2. Add an explicit DB cleanup pass because `load.py` upsert will not revisit
   products absent from a newly filtered CSV.
3. Document the finding in `docs/OBSERVATIONS.md`.

**Snacks contamination by noodles is also suspected.** The exact OFF tags need
to be inspected before updating `_EXCLUDE_FROM_SNACKS`.

### Other known issues

- Some release products lack product name / brand, likely due to barcode
  normalization or leading-zero mismatch.
- Some products database-wide have no product name; acceptable but should not
  be hidden.
- OFF source data contains extreme or implausible nutrition values. Missing
  values must remain missing; extreme values should be visible unless excluded
  by a documented plausibility rule.
- Dark or glossy packaging can degrade OCR quality.
- Cheese and dairy products have known false-exclusion / panel-context risk.

---

## 9. Pipeline run order

### Full OFF bulk population

```bat
python pipeline\bootstrap.py
python pipeline\clean.py
python pipeline\analyze.py
python pipeline\load.py
```

### Incremental OFF update

```bat
python pipeline\ingest.py
python pipeline\clean.py
python pipeline\analyze.py
python pipeline\load.py
```

`bootstrap.py` is for full repopulation / bulk export work. `ingest.py` is for
incremental monthly/API-style updates. Do not describe `ingest.py` as obsolete.

### Vision / claim extraction

```bat
python pipeline\detect_positioning_signals.py
python pipeline\assign_reality_bands.py
python pipeline\classify_formulation_families.py
python pipeline\smart_sample.py
python pipeline\vision_extract.py --test
python pipeline\vision_extract.py
python pipeline\merge_scores.py
python pipeline\tag_claims.py
```

### Market Overview precomputes

```bat
python pipeline\compute_axis_ranges.py
python pipeline\compute_region_benchmarks.py
python pipeline\compute_profile_intersections.py
```

If `region_category_benchmarks` schema changes, drop and rebuild it before
running `compute_profile_intersections.py`.

---

## 10. Critical invariants

These were explicitly fixed and must not be reverted.

```text
pack_claims_found = NULL  -> no valid pack observation
pack_claims_found = ""    -> front pack assessed, no claims found
pack_claims_found = "..." -> actual claims pipe-separated
```

- Ingredient fallback in `tag_claims.py` is allowed only when there is no valid
  pack observation. It must not overwrite genuine front-pack no-claim rows.
- `claim_source = vision` marks OCR/LLM pack observations.
- `product_analysis` claim fields should survive OFF re-ingestion unless an
  incoming file explicitly contains those columns.
- Market Overview aggregate views should not report OCR/LLM claim prevalence.
- Company-level rows in Category Report are navigational roll-ups only; no
  company-level nutrition aggregation.
- Brand-level and product-level summaries are observed-record summaries, not
  sales-weighted or distribution-weighted views.

---

## 11. Immediate next steps

Start the next workstream from data quality, not Streamlit:

1. Inspect real OFF tags for snacks/noodle contamination.
2. Review `pipeline/bootstrap.py` category exclusion lists for cereals and
   snacks.
3. Plan the companion cleanup pass for already-loaded DB rows so contaminated
   records do not remain under stale `query_category` values.

Do not begin another UI redesign unless Julia explicitly reopens Streamlit.

---

## 12. Useful commands

Run app:

```bat
.venv\Scripts\activate
streamlit run app.py
```

Stop stuck Streamlit process if needed:

```bat
taskkill /F /IM streamlit.exe /T
```

Schema utilities:

```bat
python pipeline\export_schema.py
python pipeline\verify_schema.py
```

Git checkpoint:

```bat
git status --short
git diff --stat
```
