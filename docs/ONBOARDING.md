# Food & Beverage Positioning Radar — Project Onboarding

This document briefs a new Claude conversation to continue development.
Read it fully before touching any file. The GitHub repo is public:
**https://github.com/julialenc/food-beverage-positioning-radar**

---

## 1. Project in one sentence

A Streamlit market intelligence tool for CPG professionals that shows
what packaged food products **IS** (nutritional metrics vs category average)
and what they **TELL** (on-pack claims detected by OCR/LLM), using Open
Food Facts data as the source. No health verdicts, no proprietary scores,
no ingredient-based judgments shown to users.

---

## 2. Core philosophy — non-negotiable

**No-blame principle:** The tool records observable facts (what's on pack,
what's in the nutrition table). It never judges whether a product is
healthy, misleading, or good/bad. Every column, label, and tooltip must
reflect this. If you find yourself writing "health-washing" or "blind spot"
or "loophole" anywhere, stop.

**No proprietary scores in the UI:** We removed the positioning-composition
gap score and composition marker score from the interface. Users see only:
- External validated metrics: NOVA group, Nutri-Score (from OFF)
- Nutritional ratios indexed vs country-category average (from OFF fields)
- LLM-extracted pack claims (from vision_extract.py on front-of-pack images)

**IS vs TELLS architecture:**
- **IS table:** Energy kcal/100g, Protein g/100kcal, Fibre g/100kcal,
  Saturated fat g/100kcal — all with 🟢🟡🔴 vs country-category average
- **TELLS:** Pack claims detected by OCR/LLM for vision-analyzed products;
  "Not tested" for everything else. Never show ingredient-derived claims
  as positioning signals (ferments lactiques in cheese → gut health was
  a notorious false positive we removed).

---

## 3. Tech stack

- **Language:** Python 3.12 (Windows, CMD)
- **App:** Streamlit ≥1.36 with `st.Page`/`st.navigation`
- **DB:** SQLite (`database/positioning_radar.db`, gitignored)
- **Data source:** Open Food Facts bulk CSV
  (`https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`)
- **LLM:** Azure OpenAI gpt-4.1-nano (vision + claim extraction)
- **Working dir:** `C:\Users\julia\food-beverage-positioning-radar`
- **Venv activation:** `.venv\Scripts\activate`

---

## 4. Repository structure

```
pipeline/           # Data pipeline scripts (run in order below)
  bootstrap.py      # ONE-TIME: downloads OFF bulk CSV, filters to target markets/categories
  clean.py          # Step 4b: applies brand_alias_mapping.csv
  analyze.py        # Ingredient analysis, composition markers (internal only, not shown in UI)
  load.py           # Loads to SQLite, creates market_trend_weekly table (Ozempic tracker)
  smart_sample.py   # Selects priority products for vision extraction
  vision_extract.py # OCR + LLM claim extraction (v2 prompt, Azure OpenAI)
  merge_scores.py   # Joins vision results to DB
  tag_claims.py     # Tags claim categories (internal; ingredient-derived NOT shown in UI)
  db_summary.py     # Weekly brand summaries + market_trend_weekly (Ozempic tracker)
  brand_coverage_report.py  # Generates brand_alias_candidates.csv + coverage report
  brand_counts.py           # All brands by product count → data/reference/brand_counts.csv
  check_brand.py            # python pipeline/check_brand.py <prefix> — 95% rule check
  check_unmapped.py         # Shows brands in "Other / not mapped to a company"
  check_excluded.py         # Shows pasta/pizza/tortilla products in snacks
  check_tags.py             # Shows OFF category tags for exclusion analysis
  append_mapping.py         # Programmatically appends to company_brand_mapping.csv
  fix_mapping.py            # One-off fixes to company_brand_mapping.csv

pages/
  search.py         # Product Explorer (main page — most of the work lives here)

shared/
  db.py             # SQLite access, company/region filter helpers, IS metric averages
  components.py     # Shared UI components
  labels.py         # Parses docs/UI_LABELS.md at runtime

data/
  country_region_mapping.csv        # Maps countries → region codes (FRANCE, UK_IE, US_CANADA)
  reference/
    company_brand_mapping.csv       # ~400 rows: brand → parent company
    brand_alias_mapping.csv         # ~2,323 confirmed aliases (bio sub-brands etc.)
    vision_results_20260713_*.csv   # Cached v2 vision run output
    README.md

docs/
  ADR.md            # Architecture Decision Records (ADR-001 through ADR-014)
  OBSERVATIONS.md   # Data quality and analytical observations (OBS-001 through OBS-028)
  UI_LABELS.md      # Single source of truth for all display labels
```

---

## 5. Pipeline run sequence

**Full pipeline (after re-bootstrap):**
```bat
del database\positioning_radar.db
python pipeline\bootstrap.py         # ~20 min — uses cached .gz file, no re-download
python pipeline\clean.py
python pipeline\analyze.py
python pipeline\load.py
python pipeline\smart_sample.py
python pipeline\vision_extract.py    # ~8 CHF per 5k products, can use --resume
python pipeline\merge_scores.py
python pipeline\tag_claims.py
python pipeline\db_summary.py
```

**Incremental (after changes to clean.py/analyze.py):**
```bat
del database\positioning_radar.db
python pipeline\clean.py
python pipeline\analyze.py
python pipeline\load.py
python pipeline\merge_scores.py
python pipeline\tag_claims.py
python pipeline\db_summary.py
```

**App:**
```bat
taskkill /F /IM streamlit.exe /T
streamlit run app.py
```

---

## 6. Current database state (as of July 2026)

- **512,937 products** (France, UK, US — from OFF bulk CSV)
- **Markets:** France (largest), UK & Ireland, US & Canada
- **Categories:** snacks, beverages, cereals, dairies
- **Vision-analyzed:** 5,198 products (v2 prompt), 5,026 LLM successes (96.7%)
- **Actual cost:** ~8 CHF for 5,198 products (Azure showed ~8 CHF, not 0.73 CHF
  as the script estimated — the estimate was wrong)
- **market_trend_weekly:** 4 rows (first Ozempic tracker snapshot, July 2026)
- **company_brand_mapping.csv:** ~400 rows, ~55 companies

---

## 7. Key conventions

### 95% rule (OBS-028)
A brand is considered sufficiently unified when ≥95% of products sharing
a common name prefix are under the canonical brand name. Use:
```bat
python pipeline\check_brand.py <prefix>
```

### Brand alias mapping
`data/reference/brand_alias_mapping.csv` — reviewed by user, only rows
with `action = confirm` are applied in `clean.py` Step 4b.
Generator: `python pipeline\brand_coverage_report.py`
The old SequenceMatcher-based company suggestion is unreliable (ignore it).
The prefix detection is now O(n × words) not O(n²).

### Company assignment
`data/reference/company_brand_mapping.csv` — brand = company for private
labels. Adding new rows does NOT require pipeline re-run (app-layer join,
cached at session start). To add rows programmatically:
```bat
python pipeline\append_mapping.py   # or edit directly in Notepad
```

### Region scope
`DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}` in `shared/db.py`
Only these three appear in the Market/region filter. Adding a new market
= add its code here + re-run bootstrap.py for that market.

### Snacks exclusions (bootstrap.py)
Pasta (gnocchi, tortellini, ravioli, fresh-pasta), plain tortillas (not
tortilla chips — those are protected), and pizza products are excluded from
snacks even when OFF tags them as `en:snacks`. See `assign_category()` in
bootstrap.py for the tag lists.

---

## 8. What's done

- ✅ Full IS/TELLS table UI with colour-coded nutritional metrics
- ✅ Positioning filter (vision-only, friendly claim names)
- ✅ Status vs country-category average sidebar filters
  (Protein / Fibre / Sat fat / Sugars g/100kcal)
- ✅ Configurable column selector (defaults pre-selected, user can add/remove)
- ✅ Company/owner filter with Other bucket and brand dependency
- ✅ Market/region filter scoped to download coverage only
- ✅ Brand-category dependency in Brand dropdown
- ✅ No-letter brands excluded from Brand dropdown and display
- ✅ Product card: removed proprietary scores, "Not tested" for non-vision,
  full ingredient list collapsible
- ✅ Brand alias mapping (2,323 aliases, Kellogg's unified to 99.6%)
- ✅ Company mapping: ~55 companies including all major retailers and CPG brands
- ✅ Ozempic tracker (market_trend_weekly): silently accumulates weekly snapshots
- ✅ bootstrap.py: downloads OFF bulk CSV, filters to France/UK/US,
  snacks exclusion for pasta/tortilla/pizza
- ✅ vision_extract.py v2 prompt: added French claim vocabulary (CALCIUM,
  RICHE EN CALCIUM, 100% FRANÇAIS, SANS CONSERVATEURS, AOC/AOP, NOUVELLE
  RECETTE), image context detection (ingredient lists, nutrition tables,
  price stickers → no claims extracted)

---

## 9. What's pending — in priority order

### IMMEDIATE — run before next user session
**Expanded LLM run (smart_sample.py needs updating first):**
The current smart_sample.py takes 15 products per named Tier 1 brand.
The plan is to run ALL products from CPG manufacturer brands (not retailer
private labels). Need to:
1. Update smart_sample.py to add a new tier that takes ALL products from
   mapped non-retailer companies (Nestlé, Danone, Kellogg's, Mars,
   Mondelez, Ferrero, General Mills, etc.)
2. Run smart_sample.py → vision_extract.py overnight
   Budget: ~8-15 CHF estimated for 20-40k products (based on 8 CHF/5k)
3. Run merge_scores.py → tag_claims.py → db_summary.py after

### NEXT — pipeline maintenance pass
These all require a full pipeline re-run (clean.py onward):
- `clean.py`: add title case for product names (`.str.title()` in Step 3)
- `analyze.py`: remove `ferments lactiques` and `live cultures` from
  `probiotic_claim` triggers — these are standard dairy manufacturing
  ingredients, not marketing claims (caused Bel/Emmi false positives)
- A full re-bootstrap after the above: the cached `.gz` file is still in
  `data/raw/` so bootstrap.py will filter without re-downloading (~20 min)

### CONTENT — pages not yet built
- Market Overview page (scaffold exists, content not started)
- Methodology page (5-section structure confirmed, content not started)
- About page (scaffold exists)

### DEFERRED — separate sessions
- Frozen foods category addition to bootstrap.py (different analytical
  universe, needs its own cleaning/validation pass)
- OFF data quality flagging: flag products where energy_kcal > 3× brand-
  category median (OBS-027: Hipro Saveur Coco 238 kcal error)
- License change on GitHub (not MIT — attribution required)
- Power BI / segmentation (needs full vision coverage first)
- RGM / price tracking (ToS complexity, retailer scraping)

---

## 10. Known data quality issues

**OBS-027:** Hipro Saveur Coco has 238 kcal/100g in OFF; actual is ~60
kcal/100g. Appears as 🔴 red on Energy. Heuristic to detect: flag products
where energy > 3× brand-category median. Implementation deferred.

**Coca-Cola variants:** ~44 residual products not yet unified (cocatech,
coca nasa, coca coms are NOT Coca-Cola — do not alias them).

**Pasta/pizza in snacks:** bootstrap.py now excludes the tag-identifiable
ones, but many pizza products hide under `en:savoury-cake-with-cheese...`
tag and aren't caught. Acceptable noise for now.

---

## 11. Important context for code changes

When modifying db.py or search.py, always test with:
```bat
taskkill /F /IM streamlit.exe /T
streamlit run app.py
```
The app uses `@st.cache_data` for company_brand_mapping, region options,
and category averages. Changes to CSV files require app restart to take
effect. Changes to the DB require restart AND the cache TTL to expire
(600 seconds) or a manual `st.cache_data.clear()`.

The `get_category_region_averages()` function in db.py precomputes nutritional
averages by (query_category × primary_country mapped to region). These are
the denominators for all 🟢🟡🔴 colour coding. Thresholds: >110% = above
(green for good metrics, red for bad), 90-110% = parity (yellow), <90% =
below. Energy, sat fat, sugars: higher = red. Protein, fibre: higher = green.

The company/brand filter in the app is an app-layer join (not SQL): the
company_brand_mapping.csv is loaded into a dict at session start, brands are
expanded to a list, and a `LOWER(REPLACE(primary_brand, '-', ' ')) IN (...)`
clause is added to the WHERE. This means adding companies to the CSV takes
effect on next app restart, no pipeline re-run needed.
