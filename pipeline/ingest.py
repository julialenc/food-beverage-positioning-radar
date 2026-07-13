"""
ingest.py
---------
Pulls products from the Open Food Facts Live JSON API by category.
Saves raw JSON to data/raw/ and a flat CSV to data/sample/.

Usage:
    python pipeline/ingest.py

Output:
    data/raw/raw_<category>_<timestamp>.json   (one per category)
    data/sample/sample_all_<timestamp>.csv     (all categories combined, flat)
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────────

USER_AGENT = "FoodBeveragePositioningRadar/1.0 (github.com/julialenc/food-beverage-positioning-radar)"

CATEGORIES = [
    "snacks",
    "beverages",
    "cereals",
    "dairies",     # added: Emmi, Arla, Danone dairy, FrieslandCampina, etc.
]

PRODUCTS_PER_CATEGORY = 10_000  # 4 categories × 10,000 = 40,000 total
                                 # fits in one overnight at ~5-6 hours
                                 # increase to 50,000 for a deeper production run

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

# Fields pulled from the OFF API — kept selective to keep response size light.
# See docs/ADR.md ADR-002 for the full field-selection rationale.
FIELDS = ",".join([
    "code",
    "product_name",
    "brands",
    "categories",
    "ingredients_text",
    "nutriments",
    "nutriscore_grade",
    "nova_group",
    "countries_tags",
    "labels_tags",
    "quantity",
    "packaging",
    "created_t",
    "last_modified_t",
    "additives_tags",       # E-number list pre-parsed by OFF, used in analyze.py
    "image_url",            # front-of-pack image, used by vision_extract.py
])

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR    = os.path.join(ROOT, "data", "raw")
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")

# ── Fetch ─────────────────────────────────────────────────────────────────────

PAGE_SIZE   = 100   # OFF API hard cap per page
PAGE_DELAY  = 15    # seconds between successful pages — 8s triggered 401 rate-limiting
MAX_RETRIES = 5     # attempts per page before skipping it

# Progressive backoff for 503s: 30s, 60s, 120s, 240s, 300s.
# Longer waits let the OFF server recover from burst load rather than hammering
# it with rapid retries (which worsens the 503 rate).
RETRY_BACKOFFS = [30, 60, 120, 240, 300]

# Number of consecutive failed pages before abandoning a whole category.
# A single failed page now triggers a skip (not a full stop), so this
# guard only fires when multiple consecutive pages are unrecoverable.
MAX_CONSECUTIVE_SKIPS = 3

# Pause between categories so we don't re-trigger server-side rate limiting
# immediately after a busy category fetch.
INTER_CATEGORY_PAUSE = 30  # seconds


def fetch_page(category: str, page: int, headers: dict):
    """
    Fetch a single page of products for a category.

    Returns:
        list[dict]  — products on this page (may be empty if genuinely exhausted)
        None        — server gave up after MAX_RETRIES; caller should skip this page
    """
    import time

    params = {
        "action":           "process",
        "tagtype_0":        "categories",
        "tag_contains_0":   "contains",
        "tag_0":            category,
        "fields":           FIELDS,
        "page_size":        PAGE_SIZE,
        "page":             page,
        "json":             1,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                BASE_URL, params=params,
                headers=headers, timeout=30
            )
            if response.status_code in (401, 503):
                wait = RETRY_BACKOFFS[min(attempt, len(RETRY_BACKOFFS) - 1)]
                label = "503 (server busy)" if response.status_code == 503 else "401 (rate-limited)"
                print(f"    {label} on page {page}, "
                      f"retrying in {wait}s "
                      f"(attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
                continue

            response.raise_for_status()

            if not response.text.strip():
                print(f"    Empty response on page {page}, skipping")
                return None

            data = response.json()
            return data.get("products", [])

        except Exception as e:
            print(f"    Error on page {page} attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(20)

    print(f"    Giving up on page {page} after {MAX_RETRIES} attempts — will skip")
    return None          # ← None signals "skip this page", not "stop the category"


def fetch_category(category: str,
                   target: int = PRODUCTS_PER_CATEGORY) -> list[dict]:
    """
    Fetch up to `target` products for a category using pagination.

    Key behaviour:
    - fetch_page returning None  → server error on that page; skip and continue
    - fetch_page returning []    → OFF returned no products; category is genuinely
                                   exhausted; stop
    - MAX_CONSECUTIVE_SKIPS consecutive None returns → give up on the category
      (guards against a permanently broken endpoint)
    """
    import time

    headers          = {"User-Agent": USER_AGENT}
    all_products     = []
    seen_codes       = set()
    page             = 1
    consecutive_skip = 0

    print(f"  Fetching '{category}' (target: {target:,} products, "
          f"{PAGE_SIZE}/page)...")

    while len(all_products) < target:
        page_products = fetch_page(category, page, headers)

        # ── Server error: skip this page, keep going ──────────────────────
        if page_products is None:
            consecutive_skip += 1
            print(f"    Page {page} skipped "
                  f"({consecutive_skip}/{MAX_CONSECUTIVE_SKIPS} consecutive skips)")
            if consecutive_skip >= MAX_CONSECUTIVE_SKIPS:
                print(f"    {MAX_CONSECUTIVE_SKIPS} consecutive page failures — "
                      f"stopping '{category}'")
                break
            page += 1
            continue

        # ── Genuine exhaustion: OFF says there are no more products ────────
        if not page_products:
            print(f"    No products on page {page} — category exhausted")
            break

        # ── Successful page ───────────────────────────────────────────────
        consecutive_skip = 0   # reset skip counter on any success
        new = [p for p in page_products if p.get("code") not in seen_codes]
        for p in new:
            seen_codes.add(p.get("code"))
        all_products.extend(new)

        print(f"    Page {page}: {len(new)} new products "
              f"(total so far: {len(all_products):,})")

        if len(page_products) < PAGE_SIZE:
            print(f"    Reached end of category at page {page}")
            break

        page += 1

        if len(all_products) < target:
            time.sleep(PAGE_DELAY)

    print(f"  -> {len(all_products):,} total products for '{category}'")
    return all_products[:target]


# ── Flatten ───────────────────────────────────────────────────────────────────

def flatten_product(product: dict, category: str) -> dict:
    """
    Flatten a single product dict into a row suitable for a DataFrame.
    Nutriments are a nested dict — we extract the key macros only.
    """
    nutriments = product.get("nutriments", {})

    return {
        # identifiers
        "barcode":              product.get("code", ""),
        "product_name":         product.get("product_name", ""),
        "brands":               product.get("brands", ""),
        "quantity":             product.get("quantity", ""),
        "packaging":            product.get("packaging", ""),

        # categorisation
        "query_category":       category,
        "off_categories":       product.get("categories", ""),
        "countries":            "|".join(product.get("countries_tags", [])),
        "labels":               "|".join(product.get("labels_tags", [])),

        # ingredients (raw text — clean.py will parse this)
        "ingredients_text":     product.get("ingredients_text", ""),

        # nutrition (per 100g)
        "energy_kcal":          nutriments.get("energy-kcal_100g", None),
        "fat_100g":             nutriments.get("fat_100g", None),
        "saturated_fat_100g":   nutriments.get("saturated-fat_100g", None),
        "carbs_100g":           nutriments.get("carbohydrates_100g", None),
        "sugars_100g":          nutriments.get("sugars_100g", None),
        "fiber_100g":           nutriments.get("fiber_100g", None),
        "protein_100g":         nutriments.get("proteins_100g", None),
        "salt_100g":            nutriments.get("salt_100g", None),

        # reference scores, pre-computed by OFF
        "nutriscore_grade":     product.get("nutriscore_grade", ""),
        "nova_group":           product.get("nova_group", None),

        # timestamps
        "created_t":            product.get("created_t", None),
        "last_modified_t":      product.get("last_modified_t", None),

        # additives (pre-parsed E-number list from OFF)
        # stored as pipe-separated string e.g. "en:e407|en:e950|en:e952"
        "additives_tags":       "|".join(product.get("additives_tags", [])),

        # front-of-pack image, used by vision_extract.py for claim extraction
        "image_url":            product.get("image_url", ""),
    }


# ── Save ──────────────────────────────────────────────────────────────────────

def save_raw(products: list[dict], category: str, timestamp: str) -> None:
    """Save raw API response to data/raw/ as JSON."""
    filename = f"raw_{category}_{timestamp}.json"
    path = os.path.join(RAW_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"  Raw JSON saved -> {filename}")


def save_sample(df: pd.DataFrame, timestamp: str) -> None:
    """Save combined flat CSV to data/sample/."""
    filename = f"sample_all_{timestamp}.csv"
    path = os.path.join(SAMPLE_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  Sample CSV saved -> {filename}  "
          f"({len(df):,} rows, {len(df.columns)} columns)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar — ingest.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Categories: {CATEGORIES}")
    print(f"Products per category: {PRODUCTS_PER_CATEGORY:,}\n")

    all_rows = []

    for i, category in enumerate(CATEGORIES):
        if i > 0:
            print(f"  Pausing {INTER_CATEGORY_PAUSE}s before '{category}'...")
            import time; time.sleep(INTER_CATEGORY_PAUSE)
        products = fetch_category(category)
        save_raw(products, category, timestamp)

        rows = [flatten_product(p, category) for p in products]
        all_rows.extend(rows)
        print()

    df = pd.DataFrame(all_rows)
    save_sample(df, timestamp)

    print(f"\nDone. {len(df):,} total products across {len(CATEGORIES)} categories.")
    print(f"Nulls per column:\n{df.isnull().sum().to_string()}\n")

    # Run summary — useful for unattended overnight runs
    partial_threshold = PRODUCTS_PER_CATEGORY * 0.5
    print(f"{'='*50}")
    print(f"RUN SUMMARY")
    print(f"{'='*50}")
    for category in CATEGORIES:
        cat_count = len(df[df['query_category'] == category])
        status = ("OK"      if cat_count >= PRODUCTS_PER_CATEGORY * 0.9
                  else "PARTIAL" if cat_count >= partial_threshold
                  else "FAILED"  if cat_count == 0
                  else "LOW")
        print(f"  {category:<15} {cat_count:>7,} products  {status}")
    print(f"  {'TOTAL':<15} {len(df):>7,} products")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
