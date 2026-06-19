"""
clean.py
--------
Cleans the raw CSV produced by ingest.py and outputs an analysis-ready CSV.
 
Cleaning decisions based on data exploration (18 May 2026):
    - 300 rows, 22 columns
    - 80% FR ingredients, 10% EN, 9% OTHER, 1% BOTH
    - Nulls in nutritional cols only (8-21%), zero nulls in text fields
    - energy_kcal max was 3833 (physically impossible - data error)
    - HTML entities present: &quot; &lt; &gt;
    - Whitespace artifacts: \r\n in ingredients text
 
What this script does:
    1.  Load latest sample_all_*.csv automatically
    2.  Drop exact duplicate barcodes
    3.  Drop rows with no product name AND no ingredients
    4.  Clean HTML entities from text fields
    5.  Clean whitespace artifacts (\r\n etc.)
    6.  Detect language of ingredients_text (FR / EN / BOTH / OTHER / UNKNOWN)
    7.  Normalise text fields (strip, collapse whitespace)
    8.  Lowercase brands for consistent Power BI grouping
    9.  Coerce nutritional columns to numeric
    10. Cap physically impossible nutritional outliers (set to NaN)
    11. Add missing value flag columns (boolean) - we flag, never impute
    12. Normalise nutriscore_grade to uppercase
    13. Convert Unix timestamps to readable dates
    14. Add completeness_score (0-100) - data completeness indicator
    15. Add nullable product_segment_label column (v2 stub)
    16. Save clean CSV to data/sample/
 
Usage:
    python pipeline/clean.py
 
Input:
    data/sample/sample_all_<timestamp>.csv   (latest file auto-detected)
 
Output:
    data/sample/clean_<timestamp>.csv
"""
 
import pandas as pd
import os
import re
import html
from datetime import datetime
 
# -- Paths --------------------------------------------------------------------
 
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
 
# -- Language detection -------------------------------------------------------
# Keyword-based detection - no external dependencies.
# Covers EN/FR which is ~90% of our data (confirmed by check_languages.py).
# OTHER covers Bulgarian, German, Spanish, Arabic etc. - valid nutritional
# data, excluded from ingredient-marker analysis in v1 but retained in dataset.
 
FRENCH_MARKERS = [
    "farine", "sucre", "huile", "beurre", "lait", "eau", "sel",
    "arome", "emulsifiant", "colorant",
    "conservateur", "acidifiant", "epaississant",
    "sirop", "poudre", "extrait", "naturel", "vegetal",
    "contient", "peut contenir", "ingredients", "farine de ble",
    "huile de palme", "lecithine", "amidon",
]
 
ENGLISH_MARKERS = [
    "flour", "sugar", "oil", "butter", "milk", "water", "salt",
    "flavour", "flavor", "emulsifier", "colouring", "coloring",
    "preservative", "thickener", "syrup", "powder", "extract",
    "natural", "contains", "may contain", "wheat flour",
    "palm oil", "lecithin", "starch",
]
 
 
def detect_language(text):
    """
    Returns 'FR', 'EN', 'BOTH', 'OTHER', or 'UNKNOWN'.
    BOTH = bilingual packaging (Switzerland, Belgium, Canada).
    OTHER = language with no EN/FR markers (retained, excluded from
    ingredient-marker analysis in v1).
    """
    if not isinstance(text, str) or len(text.strip()) < 10:
        return "UNKNOWN"
 
    text_lower = text.lower()
    fr = any(kw in text_lower for kw in FRENCH_MARKERS)
    en = any(kw in text_lower for kw in ENGLISH_MARKERS)
 
    if fr and en:
        return "BOTH"
    if fr:
        return "FR"
    if en:
        return "EN"
    return "OTHER"
 
 
# -- Nutritional columns ------------------------------------------------------
 
NUTRIMENT_COLS = [
    "energy_kcal",
    "fat_100g",
    "saturated_fat_100g",
    "carbs_100g",
    "sugars_100g",
    "fiber_100g",
    "protein_100g",
    "salt_100g",
]
 
# Physically impossible values per 100g
# energy_kcal max was 3833 in our sample (pure fat = ~900 kcal max)
NUTRIMENT_CAPS = {
    "energy_kcal":        900,
    "fat_100g":           100,
    "saturated_fat_100g": 100,
    "carbs_100g":         100,
    "sugars_100g":        100,
    "fiber_100g":         100,
    "protein_100g":       100,
    "salt_100g":          100,
}
 
# Fields used to calculate completeness_score — see docs/METHODOLOGY.md
# for the full metric definition and scope statement.
COMPLETENESS_COLS = [
    "product_name",
    "brands",
    "ingredients_text",
    "energy_kcal",
    "fat_100g",
    "carbs_100g",
    "sugars_100g",
    "protein_100g",
    "salt_100g",
    "nutriscore_grade",
    "nova_group",
]
 
 
# -- Helpers ------------------------------------------------------------------
 
def find_latest_sample(sample_dir):
    """Auto-detect the most recently created sample_all_*.csv file."""
    files = [
        f for f in os.listdir(sample_dir)
        if f.startswith("sample_all_") and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError(
            f"No sample_all_*.csv found in {sample_dir}. "
            "Run ingest.py first."
        )
    files.sort(reverse=True)
    return os.path.join(sample_dir, files[0])
 
 
def clean_text(text):
    """
    1. Decode HTML entities  (&quot; -> "  &lt; -> <  etc.)
    2. Replace \r\n and \n with a single space
    3. Collapse multiple spaces into one
    4. Strip leading/trailing whitespace
    """
    if not isinstance(text, str):
        return text
    text = html.unescape(text)
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
 
 
def cap_outliers(df):
    """Set physically impossible nutritional values to NaN and report them."""
    total_capped = 0
    for col, cap in NUTRIMENT_CAPS.items():
        if col in df.columns:
            mask = df[col] > cap
            count = mask.sum()
            if count > 0:
                print(f"    Capped {count} outlier(s) in {col} "
                      f"(max was {df.loc[mask, col].max():.1f}, cap={cap})")
                df.loc[mask, col] = None
                total_capped += count
    if total_capped == 0:
        print(f"    No outliers found")
    return df
 
 
def add_missing_flags(df):
    """
    Add boolean flag columns for missing nutritional values.
    We FLAG rather than IMPUTE - imputation would corrupt ingredient-based
    analysis and mislead future segmentation. Flags are useful as a
    Power BI dimension.
    """
    for col in NUTRIMENT_COLS:
        if col in df.columns:
            df[f"{col}_missing"] = df[col].isnull()
    return df
 
 
def completeness_score(row):
    """
    Score a product 0-100 based on key structured field population.
    This is a data-quality indicator, not a quality score for the
    product itself. See docs/METHODOLOGY.md for the full metric
    definition and scope statement.
    """
    filled = sum(
        1 for col in COMPLETENESS_COLS
        if col in row.index
        and row[col] is not None
        and str(row[col]).strip() not in ("", "nan", "NaN", "none", "None")
    )
    return round((filled / len(COMPLETENESS_COLS)) * 100)
 
 
# -- Main cleaning pipeline ---------------------------------------------------
 
def clean(input_path):
 
    print(f"\n  Input file: {os.path.basename(input_path)}")
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"  Rows on load: {len(df)}")
 
    # Step 1: Drop exact duplicate barcodes
    before = len(df)
    df = df.drop_duplicates(subset=["barcode"])
    dropped = before - len(df)
    print(f"\n  Step 1  - Duplicates: dropped {dropped} duplicate barcode(s)")
 
    # Step 2: Drop rows with no product name AND no ingredients
    before = len(df)
    df = df[~(df["product_name"].isnull() & df["ingredients_text"].isnull())]
    print(f"  Step 2  - Empty rows: dropped {before - len(df)} "
          f"(no name + no ingredients)")
 
    # Step 3: Clean HTML entities and whitespace artifacts
    for col in ["product_name", "brands", "ingredients_text",
                "off_categories", "packaging"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)
    print(f"  Step 3  - HTML entities, whitespace, and quantity commas cleaned")

    # Normalise European decimal commas in quantity field
    # e.g. "1,15 L" -> "1.15 L" (prevents multipack parser misreading)
    if "quantity" in df.columns:
        df["quantity"] = df["quantity"].str.replace(
            r"(\d),(\d)", r"\1.\2", regex=True
        )

 
    # Step 4: Normalise brands
    df["brands"] = (
        df["brands"]
        .str.lower()
        .str.strip()
        .str.strip(",")
    )
    df["primary_brand"] = df["brands"].apply(
        lambda x: str(x).split(",")[0].strip()
        if isinstance(x, str) and x.strip() not in ("", "nan")
        else "unknown"
    )
    # Strip accents for consistent grouping — nestlé -> nestle
    # Full company normalisation now maintained in
    # data/reference/company_brand_mapping.csv (see docs/BRAND_COMPANY_MAPPING.md)
    df["primary_brand"] = df["primary_brand"]\
        .str.normalize("NFKD")\
        .str.encode("ascii", errors="ignore")\
        .str.decode("ascii")
    print(f"  Step 4  - Brands normalised, primary_brand extracted, accents stripped")

 
    # Step 5: Detect ingredient language
    df["ingredients_lang"] = df["ingredients_text"].apply(detect_language)
    lang_counts = df["ingredients_lang"].value_counts().to_dict()
    print(f"  Step 5  - Language detection: {lang_counts}")
 
    # Step 6: Coerce nutritional columns to numeric
    for col in NUTRIMENT_COLS: