"""
bootstrap.py
------------
One-time bootstrap of the database from the Open Food Facts full CSV export.
Use this instead of ingest.py for initial database population.

The OFF search API rate-limits bulk scraping (see docs/ADR.md ADR-013).
The correct path for initial population is this script: it downloads the
full OFF CSV export (~800 MB compressed), streams it in 50,000-row chunks
to avoid loading it entirely into memory, filters by target countries and
categories, and writes a sample_all_<timestamp>.csv in exactly the same
format as ingest.py produces — so clean.py and the rest of the pipeline
are unaffected.

The compressed file is cached in data/raw/ after the first download. Delete
it manually to force a fresh download (e.g. for a quarterly refresh). Do
not commit it to git — it is gitignored.

Usage:
    python pipeline/bootstrap.py

Output:
    data/raw/en.openfoodfacts.org.products.csv.gz   (cached download)
    data/sample/sample_all_<timestamp>.csv           (pipeline input)

Next step: python pipeline/clean.py
"""

from __future__ import annotations

import gzip
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── Configuration ─────────────────────────────────────────────────────────────

OFF_CSV_URL = (
    "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
)

# Countries to include — matched against the countries_tags field.
# OFF crowdsources country tags from contributors, not from barcode prefixes.
# A product gets tagged with a country when a contributor in that country
# enters it. This is the correct signal for "sold in this market."
TARGET_COUNTRIES = {"en:france", "en:united-kingdom", "en:united-states"}

# Category priority mapping: first match wins.
# Dairies checked first because dairy products often also appear in snacks/
# beverages and we want the most specific classification.
CATEGORY_MAP = [
    ("dairies",   ["en:dairies", "en:dairy-products",
                   "en:fermented-milk-products", "en:dairy"]),
    ("cereals",   ["en:cereals-and-their-products",
                   "en:breakfast-cereals", "en:cereals"]),
    ("snacks",    ["en:snacks", "en:sweet-snacks", "en:salty-snacks"]),
    ("beverages", ["en:beverages", "en:drinks", "en:plant-based-beverages"]),
]

CHUNK_SIZE = 50_000  # rows per chunk — ~200 MB RAM peak per chunk

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT       = Path(__file__).resolve().parent.parent
RAW_DIR    = ROOT / "data" / "raw"
SAMPLE_DIR = ROOT / "data" / "sample"
GZ_PATH    = RAW_DIR / "en.openfoodfacts.org.products.csv.gz"

# ── Column mapping: OFF CSV name → internal pipeline name ─────────────────────

COL_MAP = {
    "code":               "barcode",
    "product_name":       "product_name",
    "brands":             "brands",
    "quantity":           "quantity",
    "packaging":          "packaging",
    "categories":         "off_categories",
    "ingredients_text":   "ingredients_text",
    "energy-kcal_100g":   "energy_kcal",
    "fat_100g":           "fat_100g",
    "saturated-fat_100g": "saturated_fat_100g",
    "carbohydrates_100g": "carbs_100g",
    "sugars_100g":        "sugars_100g",
    "fiber_100g":         "fiber_100g",
    "proteins_100g":      "protein_100g",
    "salt_100g":          "salt_100g",
    "nutriscore_grade":   "nutriscore_grade",
    "nova_group":         "nova_group",
    "created_t":          "created_t",
    "last_modified_t":    "last_modified_t",
    "image_url":          "image_url",
}

# Tag columns: comma-separated in OFF CSV → pipe-separated in our format
TAG_COL_MAP = {
    "countries_tags": "countries",
    "labels_tags":    "labels",
    "additives_tags": "additives_tags",
}

ALL_NEEDED = set(COL_MAP) | set(TAG_COL_MAP) | {"categories_tags"}

OUTPUT_COLS = [
    "barcode", "product_name", "brands", "quantity", "packaging",
    "query_category", "off_categories", "countries", "labels",
    "ingredients_text",
    "energy_kcal", "fat_100g", "saturated_fat_100g", "carbs_100g",
    "sugars_100g", "fiber_100g", "protein_100g", "salt_100g",
    "nutriscore_grade", "nova_group",
    "created_t", "last_modified_t",
    "additives_tags", "image_url",
]


# ── Download ───────────────────────────────────────────────────────────────────

def download_if_needed() -> None:
    """Download the OFF full CSV export if not already cached locally."""
    if GZ_PATH.exists():
        mb = GZ_PATH.stat().st_size / 1_048_576
        print(f"  Using cached OFF export: {GZ_PATH.name} ({mb:.0f} MB)")
        print(f"  Delete {GZ_PATH} to force a fresh download.\n")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading OFF full export (~800 MB)...")
    print(f"  URL: {OFF_CSV_URL}")
    print(f"  Destination: {GZ_PATH}\n")

    headers = {"User-Agent": "FoodBeveragePositioningRadar/1.0 (github.com/julialenc/food-beverage-positioning-radar)"}
    with requests.get(OFF_CSV_URL, stream=True, timeout=600, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(GZ_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=1_048_576):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(
                        f"    {downloaded/1_048_576:6.0f} MB / "
                        f"{total/1_048_576:.0f} MB ({pct:.0f}%)",
                        end="\r",
                    )
    print(f"\n  Download complete: {GZ_PATH.stat().st_size/1_048_576:.0f} MB\n")


# ── Filter helpers ─────────────────────────────────────────────────────────────

# Tags that confirm a product is a genuine snack chip
# — checked first, before any exclusion rules
_PROTECT_AS_SNACKS = {
    "en:tortilla-chips", "en:corn-chips", "en:crisps",
    "en:chips-and-crackers",
}

# Tags that exclude a product from snacks even when en:snacks is present.
# Covers pasta, plain tortillas/wraps, and identifiable pizza products.
_EXCLUDE_FROM_SNACKS = {
    # Pasta
    "en:gnocchi", "en:potato-gnocchi", "en:cooked-gnocchis",
    "en:tortellini", "en:tortellini-ricotta-spinach",
    "en:ravioli", "en:cheese-ravioli", "en:fresh-ravioli",
    "en:ravioli-with-vegetables",
    "en:pastas", "en:fresh-pasta",
    # Tortillas (not chips — protected above)
    "en:tortillas", "en:flour-tortillas", "en:corn-tortillas",
    # Pizza
    "en:pizzas", "en:frozen-pizzas", "en:frozen-pizzas-and-pies",
    "en:mini-appetizer-pizzas", "en:pizza-with-ham-and-cheese",
    "en:vegetable-pizza",
}


def assign_category(cats_val) -> str | None:
    """Return the first matching query_category, or None to exclude.
    For snacks: tortilla chips are explicitly protected; pasta, plain
    tortillas, and pizza products are excluded even when en:snacks is
    present in their OFF category tags."""
    if not isinstance(cats_val, str) or not cats_val:
        return None
    tags = cats_val.lower()
    for label, match_tags in CATEGORY_MAP:
        if any(t in tags for t in match_tags):
            if label == "snacks":
                if any(p in tags for p in _PROTECT_AS_SNACKS):
                    return "snacks"
                if any(ex in tags for ex in _EXCLUDE_FROM_SNACKS):
                    return None
            return label
    return None


def matches_country(countries_val) -> bool:
    """True if any target country tag appears in the product's countries_tags."""
    if not isinstance(countries_val, str) or not countries_val:
        return False
    tags = countries_val.lower()
    return any(c in tags for c in TARGET_COUNTRIES)


def comma_to_pipe(val) -> str:
    """Convert comma-separated OFF tag list to pipe-separated."""
    if not isinstance(val, str) or not val:
        return ""
    return val.replace(",", "|")


# ── Chunk processing ───────────────────────────────────────────────────────────

def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Filter and reshape one chunk from the OFF export."""
    # Country filter
    mask = chunk.get("countries_tags", pd.Series(dtype=str)).apply(matches_country)
    chunk = chunk[mask]
    if chunk.empty:
        return pd.DataFrame()

    chunk = chunk.copy()

    # Category assignment
    chunk["query_category"] = chunk.get(
        "categories_tags", pd.Series(dtype=str)
    ).apply(assign_category)
    chunk = chunk[chunk["query_category"].notna()]
    if chunk.empty:
        return pd.DataFrame()

    # Rename nutritional / identity columns
    chunk = chunk.rename(columns={k: v for k, v in COL_MAP.items() if k in chunk.columns})

    # Convert tag columns to pipe-separated
    for src, dst in TAG_COL_MAP.items():
        if src in chunk.columns:
            chunk[dst] = chunk[src].apply(comma_to_pipe)

    # Return only the expected output columns that exist
    available = [c for c in OUTPUT_COLS if c in chunk.columns]
    return chunk[available]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar — bootstrap.py")
    print(f"Run timestamp:     {timestamp}")
    print(f"Target countries:  France, United Kingdom, United States")
    print(f"Target categories: {[label for label, _ in CATEGORY_MAP]}\n")

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1 — download
    download_if_needed()

    # Step 2 — stream, filter, reshape
    print(f"  Streaming OFF export in chunks of {CHUNK_SIZE:,} rows...")
    print(f"  (This takes 10-20 minutes depending on disk speed)\n")

    chunks: list[pd.DataFrame] = []
    seen_barcodes: set[str] = set()
    rows_seen = rows_kept = chunk_n = 0

    with gzip.open(GZ_PATH, "rt", encoding="utf-8", errors="replace") as f:
        reader = pd.read_csv(
            f,
            sep="\t",
            chunksize=CHUNK_SIZE,
            dtype=str,
            usecols=lambda c: c in ALL_NEEDED,
            on_bad_lines="skip",
            low_memory=False,
        )
        for chunk in reader:
            chunk_n  += 1
            rows_seen += len(chunk)

            processed = process_chunk(chunk)
            if not processed.empty:
                # Cross-chunk deduplication on barcode
                new_mask = ~processed["barcode"].isin(seen_barcodes)
                processed = processed[new_mask]
                seen_barcodes.update(processed["barcode"].dropna())
                rows_kept += len(processed)
                chunks.append(processed)

            if chunk_n % 10 == 0 or chunk_n == 1:
                print(
                    f"    Chunk {chunk_n:3d}: "
                    f"{rows_seen:>9,} rows scanned, "
                    f"{rows_kept:>7,} kept"
                )

    print(f"\n  Streaming complete.")
    print(f"  Total rows in OFF export : {rows_seen:,}")
    print(f"  Rows kept after filtering: {rows_kept:,}")
    print(f"  Unique barcodes:           {len(seen_barcodes):,}")

    if not chunks:
        print("\n  ERROR: No rows passed the filters.")
        print("  Check that the OFF export downloaded correctly and the")
        print("  TARGET_COUNTRIES / CATEGORY_MAP settings are correct.")
        return

    # Step 3 — combine and save
    print(f"\n  Combining chunks...")
    df = pd.concat(chunks, ignore_index=True)

    print(f"\n  Distribution by category:")
    for cat, n in df["query_category"].value_counts().items():
        print(f"    {cat:<15} {n:>8,} products")

    out = SAMPLE_DIR / f"sample_all_{timestamp}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    size_mb = out.stat().st_size / 1_048_576
    print(f"\n  Saved -> {out.name}  ({len(df):,} rows, {len(df.columns)} columns, {size_mb:.0f} MB)")
    print(f"\n  Next step: python pipeline/clean.py\n")

    print("=" * 52)
    print("BOOTSTRAP SUMMARY")
    print("=" * 52)
    for cat, _ in CATEGORY_MAP:
        n = (df["query_category"] == cat).sum()
        print(f"  {cat:<15} {n:>8,} products")
    print(f"  {'TOTAL':<15} {len(df):>8,} products")
    print("=" * 52)


if __name__ == "__main__":
    main()
