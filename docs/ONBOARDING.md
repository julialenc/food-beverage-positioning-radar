# Food & Beverage Positioning Radar — Project Onboarding

This document briefs a new Claude conversation to continue development.
Read it fully before touching any file.

**GitHub repo (public):**
https://github.com/julialenc/food-beverage-positioning-radar/tree/main

**Local working directory:** `C:\Users\julia\food-beverage-positioning-radar`

**Context:** Julia is a data scientist specialising in retail and nutrition
forecasting, based in Geneva. Strong in model training and deployment;
more limited exposure to production infrastructure, CI/CD and auth systems.
Her preferred working style is methodical: validate each piece with synthetic
data that has a known ground truth before building on top of it.

---

## 1. Project in one sentence

A Streamlit market intelligence tool for CPG professionals and dietitians
that shows what packaged food products **ARE** (nutritional reality vs
category benchmark) and what they **TELL** (on-pack claims detected by
OCR + LLM), using Open Food Facts data as the source.
No health verdicts. No proprietary scores shown to users.

---

## 2. Non-negotiable principles

**Neutral language everywhere.** "Higher protein efficiency", never
"healthier". "Lower saturated fat", never "better". This applies to UI
labels, code comments, prompts, and methodology text.

**No proprietary composite scores in the UI.** The old
`positioning_composition_gap` / `composition_marker_score` still exists in
`analyze.py` and `merge_scores.py` but is not displayed anywhere and will
be removed from the clean-run pipeline after the run completes.

**No ingredient-derived claims as UI output.** The fallback path in
`tag_claims.py` (ingredient text to inferred claim) is used only when
`pack_claims_found` is NULL (no valid pack observation). An empty string ""
means "front pack assessed, no claims found" and must NOT trigger the
fallback. This distinction was explicitly fixed in July 2026.

**Missing != zero, ever.** The null-vs-zero audit confirmed this for the
full database. Every pipeline script treats NULL and 0.0 as semantically
distinct values.

---

## 3. Tech stack

- **Language:** Python 3.12 (Windows, CMD)
- **App:** Streamlit >= 1.36 with st.Page / st.navigation
- **DB:** SQLite (database/positioning_radar.db, gitignored)
- **OCR:** Azure AI Vision (Read API)
- **LLM:** Azure OpenAI gpt-4.1-nano (PROMPT_VERSION v3 — see below)
- **Venv:** .venv\Scripts\activate
- **Cost benchmark:** ~1.60 CHF per 1,000 products for OCR + LLM combined

---

## 4. Repository structure (key files)

```
app.py
pages/
  search.py         # Product Explorer — FINAL, do not reopen
  overview.py       # Market Overview — COMPLETE (3 sections)
shared/
  db.py             # DB helpers, cached lookups, region/category options
  components.py     # Shared UI colours (PRIMARY_ACCENT etc.)
  labels.py         # Parses docs/UI_LABELS.md at runtime
pipeline/
  bootstrap.py                   # Downloads OFF, category assignment
  clean.py                       # Brand alias normalisation
  analyze.py                     # Ingredient analysis (composite score, not shown in UI)
  load.py                        # SQLite DDL + initial load (v3 columns included)

  # Market Overview precompute — run in this order:
  compute_axis_ranges.py           # P99.5 display ranges + hard-plausibility flags
  compute_region_benchmarks.py     # 12-row median/P25/P75 table (+ per-100ml beverages)
  compute_profile_intersections.py # Funnel precompute — reads benchmarks (run second)

  # LLM clean-run sampling — run in this order:
  detect_positioning_signals.py    # Pre-LLM positioning proxy (US+UK only, EN keywords)
  assign_reality_bands.py          # P25/P75 quartile bands per product-metric
  classify_formulation_families.py # Rule-based product-type families
  smart_sample.py                  # 3-component sampler -> sample_clean_run.csv
  vision_extract.py               # OCR + GPT-4.1-nano (PROMPT_VERSION v3)
  merge_scores.py                  # Joins vision results to DB
  tag_claims.py                    # CLAIM_TAXONOMY classification

  # Diagnostic / local-only (not committed):
  check_axis_ranges.py, check_null_vs_zero_audit.py, check_family_others.py
  check_positioning_diagnostics.py, check_top_outliers.py
  export_vision_analyzed_dataset.py

database/
  schema.sql            # Reference DDL
  positioning_radar.db  # Gitignored, rebuilt from pipeline

docs/
  ADR.md, OBSERVATIONS.md, METHODOLOGY.md, UI_LABELS.md, ONBOARDING.md

data/
  country_region_mapping.csv
  reference/
    company_brand_mapping.csv
    brand_alias_mapping.csv

# LOCAL ONLY — never committed, critical context:
llm_sampling_design_log.md
market_overview_phase_documentation.md
notes_data_quality_local.md
docs/prompt_feedback.txt       # already implemented
docs/pre-run_feedback.txt      # already implemented
```

---

## 5. Current state — 20 July 2026

### COMPLETE

**Product Explorer (pages/search.py) — FINAL. Do not reopen.**

**Market Overview (pages/overview.py) — COMPLETE, 3 sections:**
1. Product Landscape: ScatterGL, 12 metrics, 15k stratified display threshold,
   NOVA 2-bucket colouring, click-to-detail, left-pane navigation.
2. Product Profile Landscape: 6 dimensions x NOVA variants, constant
   denominator across all funnel levels, precomputed intersections.
3. By Region: HTML-rendered 12-row table (not st.dataframe), median+IQR,
   Sugars g/100kcal column, selected-row highlight, CSV download.

**Market Overview pipeline precomputes:**
- compute_axis_ranges.py -> axis_range_config (done)
- compute_region_benchmarks.py -> region_category_benchmarks (done, per-100ml included)
- compute_profile_intersections.py -> profile_intersections (done)

**LLM sampling pipeline — all 4 input layers built and validated:**
- detect_positioning_signals.py -> pipeline/positioning_signals_us_uk.csv (done)
- assign_reality_bands.py -> pipeline/reality_bands.csv (done)
- classify_formulation_families.py -> pipeline/formulation_families.csv (done)
- smart_sample.py -> pipeline/sample_clean_run.csv, 12,029 products locked (done)
- vision_extract.py, merge_scores.py, tag_claims.py — all updated to v3 (done)

### WHERE WE STOPPED — 100-product test NOT YET RUN

All files have been moved/copied to the local repo. Next action:

```bat
python pipeline\vision_extract.py --test
```

(--test mode processes 10 products as a smoke test. vision_extract.py now
auto-discovers pipeline\sample_clean_run.csv and joins the DB for
product_name, brands, image_url.)

After smoke test passes: run 50 US + 50 UK from sample_clean_run.csv,
then merge_scores.py, then tag_claims.py, then review results before the
full US run.

---

## 6. Locked sample — final quotas

```
Region        Snacks  Dairy   Cereals  Beverages  Total
US & Canada   2,039   2,160   1,108    644        5,951
UK & Ireland  2,063   2,263   1,101    651        6,078
Total         4,102   4,423   2,209    1,295      12,029
```

Under-fill is stratum shortage (no valid reality band for a matrix cell),
not product shortage. These are the final locked numbers, not targets.

France is deferred: needs a French keyword dictionary for
detect_positioning_signals.py before sampling. Raw French terms exist in
analyze.py and clean.py.

---

## 7. Sampling design — critical context

**The ouroboros fix (most important decision of the sampling phase):**
The positioning proxy (what the pack SAYS) uses product_name keywords only.
The reality band (what the product IS) uses nutrition and ingredients.
These axes must never overlap. See llm_sampling_design_log.md for the full
reasoning — this local file is the most important context document.

Three components per region-category:
- 35% backbone: proportional within formulation family, brand-capped 15%,
  weight_status = "approximate_brand_capped"
- 50% matrix: positioning-proxy x reality-band per territory, 6 cells,
  priority-weighted, weight_status = "approximate"
- 15% calibration: rare territory enrichment (immune/gut/fibre) + 5%
  prompt-comparison panel from the ~5,030 prior LLM-analyzed products

All sampling metadata (component, stratum, inclusion_probability, reality bands,
positioning proxy, formulation family) passes through to every output row in
vision_extract.py automatically via sampling_meta dict.

---

## 8. PROMPT_VERSION v3 — what changed and why

Never reuse old prompt versions (ADR-006). v3 key changes:

1. Image context classified FIRST (6 values: front_of_pack, mixed_pack_text,
   ingredient_or_legal_panel, nutrition_label, price_sticker, uncertain).
   Non-front images get claim_extraction_status = "not_applicable_non_front"
   and no_claims_detected = null. This was the critical v2 bug: ingredient
   stickers were returning no_claims_detected=true, making them
   indistinguishable from genuine no-claim front packs.
2. Multi-indicator panel detection (not word count alone).
3. Product name is "context only, not claim evidence" — claim must appear in OCR.
4. Deterministic context hints before OCR text (advisory, not authoritative).
5. New fields: gut_health_claim, prebiotic_claim, sleep_claim,
   brain_health_claim, reduced_fat_claim, whole_grain_claim,
   detected_claim_phrases[], image_context, claim_extraction_status.
6. Immunity separated from fortification. Brain health requires explicit
   wording (omega-3 alone stays fortification_claim).
7. DOUBLE ZERO narrowed: "ZERO SWEETENERS" alone -> other_claims only.
8. stylized_text removed from schema (nano can't detect typography geometry).
9. Response validator: validate_and_normalise() fills missing booleans,
   validates enums, zeroes claims for non-front images.
10. max_tokens 800 (was 500).

---

## 9. Critical cross-script invariants

These were explicitly fixed and must not be reverted:

pack_claims_found = None  -> no valid pack observation (not analyzed, non-front, or failed)
pack_claims_found = ""    -> front pack assessed, no claims found (do NOT use fallback)
pack_claims_found = "..."  -> actual claims pipe-separated

pd.isna(pack_claims) triggers ingredient fallback in tag_claims.py (NOT pd.notna).
get_pack_claims_found() returns None for non-front images (NON_FRONT_STATUSES guard).
valid_claim_observation = has_vision & (claim_extraction_status == "completed").

compute_region_benchmarks.py MUST run before compute_profile_intersections.py
(Section 2 reads its benchmark from Section 3's table — single source of truth).

Reality bands use P25/P75 quartiles for sampling, NOT the 110/90 index (different purpose).

---

## 10. Known data quality issues

See notes_data_quality_local.md for full detail.

- Vodka/tea: near-zero energy paired with full-strength macros -> 500-18,800
  protein/kcal. Excluded by hard-plausibility ceilings in precompute scripts.
- get_category_region_averages() in shared/db.py has no implausibility
  protection -> may distort Product Explorer arrows for beverages. Deferred.
- US cereals satfat median = 0.0: FDA 21 CFR 101.9 labelling convention,
  not a data error.
- off_categories stores display text, not en:xxx canonical slugs. Always use
  display-text substrings ("yogurts", "yaourts") not "en:yogurts" for matching.

---

## 11. Next steps in priority order

### Immediate: 100-product test
```bat
python pipeline\vision_extract.py --test
# if smoke test clean:
python pipeline\vision_extract.py --input pipeline\sample_clean_run.csv
# (run only 100 rows initially by using --test or editing source to limit rows)
python pipeline\merge_scores.py
python pipeline\tag_claims.py
```
Review: image_context distribution, claim_extraction_status breakdown,
new claim fields (sleep, brain, gut_health), detected_claim_phrases quality.

### After test: full US run (~6,000 products)
```bat
python pipeline\vision_extract.py --input pipeline\sample_clean_run.csv
```
(auto-discovers sample_clean_run.csv, joins DB for product fields)

### After US: UK run -> France (after French dictionary)

### Deferred (after full run)
- Bootstrap re-run (OBS-029 cereals exclusion for bread/pasta contamination)
- axis_range_config UI wiring (scatter default range, "Show full range" toggle)
- Remove deprecated composite score from analyze.py and merge_scores.py
- Clean up db_summary.py (deprecated table references)
- Methodology page, About page, README update

---

## 12. Precompute run order (Market Overview)

```bat
python pipeline\compute_axis_ranges.py
python pipeline\compute_region_benchmarks.py        # run before next line
python pipeline\compute_profile_intersections.py    # reads from above
```

If region_category_benchmarks schema changes (new columns), drop and rebuild:
```bat
python -c "import sqlite3; c=sqlite3.connect('database/positioning_radar.db'); c.execute('DROP TABLE IF EXISTS region_category_benchmarks'); c.commit()"
python pipeline\compute_region_benchmarks.py
python pipeline\compute_profile_intersections.py
```

---

## 13. Sampling pipeline run order

```bat
python pipeline\detect_positioning_signals.py    # US+UK only; France excluded (expected)
python pipeline\assign_reality_bands.py
python pipeline\classify_formulation_families.py
python pipeline\smart_sample.py --dry-run        # check eligible counts
python pipeline\smart_sample.py                   # -> pipeline/sample_clean_run.csv
```

---

## 14. App

```bat
taskkill /F /IM streamlit.exe /T
streamlit run app.py
```

---

## 15. Local-only documentation (never committed)

These are the most important context files not in the repo:

llm_sampling_design_log.md          -- Full LLM sampling design decisions.
                                       READ THIS before touching sampling code.
market_overview_phase_documentation.md -- Full Market Overview build docs.
notes_data_quality_local.md         -- Data quality findings, deferred fixes.
docs/prompt_feedback.txt            -- Prompt v3 specification (implemented).
docs/pre-run_feedback.txt           -- Pre-run checklist (implemented).
