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
    10. Preserve raw nutrition values, flag hard data-quality errors, and
        keep legacy analysis columns capped to NaN for downstream compatibility
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
import unicodedata
from datetime import datetime

# -- Paths --------------------------------------------------------------------

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
REGION_MAPPING_PATH = os.path.join(ROOT, "data", "country_region_mapping.csv")
TOP_COMPANY_BRAND_MATRIX_PATH = os.path.join(
    ROOT, "data", "reference", "top_company_brand_portfolio_matrix.csv"
)
COMPANY_BRAND_MAPPING_PATH = os.path.join(
    ROOT, "data", "reference", "company_brand_mapping.csv"
)
PRODUCT_MAPPING_OVERRIDE_PATH = os.path.join(
    ROOT, "data", "reference", "reviewed_product_mapping_overrides.csv"
)
PRIVATE_LABEL_MAPPING_PATH = os.path.join(
    ROOT, "data", "reference", "private_label_brand_mapping.csv"
)
BRAND_MAPPING_REVIEW_DIR = os.path.join(ROOT, "data", "brand_mapping_review")

CURATED_MECHANICAL_BRAND_ALIASES = {
    "after eight": "After Eight",
    "almond joy": "Almond Joy",
    "cap n crunch": "Cap’n Crunch",
    "capn crunch": "Cap’n Crunch",
    "cadbury": "Cadbury",
    "cadbury bournville": "Cadbury Bournville",
    "cadbury brunch": "Cadbury Brunch",
    "cadbury dairy milk": "Cadbury Dairy Milk",
    "cadbury dairy milk fingers crossed": "Cadbury Dairy Milk",
    "cadbury fingers": "Cadbury Fingers",
    "clif": "Clif",
    "clif bar": "Clif",
    "coffee mate": "Coffee mate",
    "coffee-mate": "Coffee mate",
    "galak": "Galak",
    "gamesa": "Gamesa",
    "hersheys": "Hershey’s",
    "hershey s": "Hershey’s",
    "heinz": "Heinz",
    "hipro": "HiPRO",
    "hu": "Hu",
    "jell o": "Jell-O",
    "jello": "Jell-O",
    "kit kat": "KitKat",
    "kitkat": "KitKat",
    "kit kat ball": "KitKat",
    "kool aid": "Kool-Aid",
    "koolaid": "Kool-Aid",
    "kraft": "Kraft",
    "kraft singles": "Kraft Singles",
    "la laitiere": "La Laitière",
    "lays": "Lay’s",
    "lay s": "Lay’s",
    "les recettes de l atelier": "Les Recettes de l’Atelier",
    "light and fit": "Light & Fit",
    "light fit": "Light & Fit",
    "light and free": "Light & Free",
    "light free": "Light & Free",
    "l atelier": "Les Recettes de l’Atelier",
    "lu": "LU",
    "maxwell house": "Maxwell House",
    "nestle dessert": "Nestlé Dessert",
    "nescafe": "Nescafé",
    "nescafe dolce gusto": "Nescafé Dolce Gusto",
    "oscar mayer": "Oscar Mayer",
    "payday": "PayDay",
    "perugina": "Perugina",
    "perfect snacks": "Perfect Snacks",
    "popcorners": "PopCorners",
    "powerade": "Powerade",
    "quality street": "Quality Street",
    "quaker": "Quaker",
    "quaker oats": "Quaker",
    "quaker chewy": "Quaker Chewy",
    "s pellegrino": "San Pellegrino",
    "sabritas": "Sabritas",
    "san pellegrino": "San Pellegrino",
    "sanpellegrino": "San Pellegrino",
    "scharffen berger": "Scharffen Berger",
    "skinny pop": "SkinnyPop",
    "smartwater": "Smartwater",
    "so delicious": "So Delicious",
    "sun chips": "SunChips",
    "sunchips": "SunChips",
    "tate s bake shop": "Tate’s Bake Shop",
    "tates bake shop": "Tate’s Bake Shop",
    "toll house": "Toll House",
    "vitaminwater": "Vitaminwater",
    "vitamin water": "Vitaminwater",
    "yopro": "YoPRO",
    "lion": "Lion",
    "smarties": "Smarties",
    "crunch": "Crunch",
    "nesquik": "Nesquik",
    "aero": "Aero",
    "fitness": "Fitness",
    "quality street": "Quality Street",
    "rolo": "Rolo",
    "yorkie": "Yorkie",
    "milkybar": "Milkybar",
    "milky bar": "Milkybar",
    "chocapic": "Chocapic",
    "balaton": "Balaton",
    "coca cola": "Coca-Cola",
    "coca cola light": "Coca-Cola Light",
    "core power": "Core Power",
    "gold peak": "Gold Peak",
    "honest kids": "Honest Kids",
    "diet coke": "Diet Coke",
    "coke": "Coca-Cola",
    "dolce gusto": "Nescafé Dolce Gusto",
    "haagen dazs": "Häagen-Dazs",
    "haagen daz": "Häagen-Dazs",
    "kelloggs": "Kellogg's",
    "kellogg s": "Kellogg's",
    "m and s": "M&S",
    "marks and spencer": "M&S",
    "mcvities": "McVitie's",
    "mcvitie s": "McVitie's",
    "monster munch": "Monster Munch",
    "walkers baked": "Walkers Baked",
    "walkers max": "Walkers MAX",
    "walkers 45 less salt": "Walkers 45% Less Salt",
    "walkers 45 percent less salt": "Walkers 45% Less Salt",
    "walkers sensations": "Sensations",
    "walkers quavers": "Quavers",
    "walkers squares": "Squares",
    "walkers french fries": "French Fries",
    "walkers sunbites": "Sunbites",
    "walkers snack a jacks": "Snack a Jacks",
}

BRAND_FAMILY_BY_KEY = {
    "cadbury": "Cadbury",
    "cadbury bournville": "Cadbury",
    "cadbury brunch": "Cadbury",
    "cadbury dairy milk": "Cadbury",
    "cadbury fingers": "Cadbury",
    "quaker": "Quaker",
    "quaker chewy": "Quaker",
    "coca cola": "Coca-Cola",
    "coca cola light": "Coca-Cola",
    "diet coke": "Coca-Cola",
}

CURATED_LINE_BRAND_ALIASES = {
    "cadbury dairy milk fingers crossed": "Cadbury Dairy Milk",
}

NESTLE_FRANCE_SNACKS_PRODUCT_NAME_RECOVERY = [
    (re.compile(r"\bkit\s*[- ]?\s*kat\b|\bkitkat\b", re.IGNORECASE), "KitKat"),
    (
        re.compile(
            r"\bles\s+recettes\s+de\s+l[' ]?atelier\b|\bl[' ]?atelier\b",
            re.IGNORECASE,
        ),
        "Les Recettes de l’Atelier",
    ),
    (re.compile(r"\bnestl[eé]\s+dessert\b", re.IGNORECASE), "Nestlé Dessert"),
    (re.compile(r"\bperugina\b", re.IGNORECASE), "Perugina"),
    (re.compile(r"\bafter\s+eight\b", re.IGNORECASE), "After Eight"),
    (re.compile(r"\bgalak\b", re.IGNORECASE), "Galak"),
    (re.compile(r"\blion\b", re.IGNORECASE), "Lion"),
    (re.compile(r"\bsmarties\b", re.IGNORECASE), "Smarties"),
    (re.compile(r"\bcrunch\b", re.IGNORECASE), "Crunch"),
    (re.compile(r"\bnesquik\b", re.IGNORECASE), "Nesquik"),
    (re.compile(r"\baero\b", re.IGNORECASE), "Aero"),
    (re.compile(r"\bfitness\b", re.IGNORECASE), "Fitness"),
    (re.compile(r"\bquality\s+street\b", re.IGNORECASE), "Quality Street"),
    (re.compile(r"\brolo\b", re.IGNORECASE), "Rolo"),
    (re.compile(r"\bmilky\s*bar\b|\bmilkybar\b", re.IGNORECASE), "Milkybar"),
    (re.compile(r"\bchocapic\b", re.IGNORECASE), "Chocapic"),
    (re.compile(r"\bbalaton\b", re.IGNORECASE), "Balaton"),
]

NESTLE_UK_IE_SNACKS_PRODUCT_NAME_RECOVERY = [
    (re.compile(r"\bkit\s*[- ]?\s*kat\b|\bkitkat\b", re.IGNORECASE), "KitKat"),
    (re.compile(r"\baero\b", re.IGNORECASE), "Aero"),
    (re.compile(r"\bsmarties\b", re.IGNORECASE), "Smarties"),
    (re.compile(r"\byorkie\b", re.IGNORECASE), "Yorkie"),
    (re.compile(r"\bmilky\s*bar\b|\bmilkybar\b", re.IGNORECASE), "Milkybar"),
]

NESTLE_US_CANADA_SNACKS_PRODUCT_NAME_RECOVERY = [
    (re.compile(r"\bkit\s*[- ]?\s*kat\b|\bkitkat\b", re.IGNORECASE), "KitKat"),
    (re.compile(r"\bsmarties\b", re.IGNORECASE), "Smarties"),
]

NESTLE_PRODUCT_NAME_RECOVERY_SOURCES = {
    "FRANCE": "product_name_recovery_nestle_france_snacks",
    "UK_IE": "product_name_recovery_nestle_uk_ie_snacks",
    "US_CANADA": "product_name_recovery_nestle_us_canada_snacks",
}

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

RAW_NUTRIMENT_COLS = {
    col: f"{col}_off_raw" for col in NUTRIMENT_COLS
}

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

NUTRITION_QUALITY_COLS = [
    "nutrition_quality_status",
    "outlier_type",
    "include_in_product_table",
    "include_in_aggregates",
    "include_in_charts",
    "nutrition_quality_reason",
]

BASIC_IMPOSSIBLE_NEGATIVE_COLS = NUTRIMENT_COLS
MAX_ENERGY_KCAL_100G = 900
MAX_NUTRIENT_G_100G = 100
MAX_MACRO_SUM_G_100G = 105
NUTRIENT_DENSITY_LIMITS_PER_100KCAL = {
    "protein_100g": 28.0,
    "carbs_100g": 28.0,
    "fat_100g": 12.5,
}
ENERGY_CONSISTENCY_ABS_KCAL_THRESHOLD = 75
ENERGY_CONSISTENCY_REL_DIFF_THRESHOLD = 15.0
STRUCTURAL_MAX_COLS = [
    "protein_100g",
    "carbs_100g",
    "fat_100g",
    "fiber_100g",
    "salt_100g",
]

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


def normalize_brand_key(value):
    """Normalize brand text for matching only; do not use as display label."""
    if not isinstance(value, str):
        return ""
    text = value.strip().lower()
    if not text or text == "nan":
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_brand_tokens(value):
    """Split the OFF brands field into normalized tokens for audit/matching."""
    if not isinstance(value, str) or value.strip().lower() in ("", "nan"):
        return []
    tokens = []
    for part in re.split(r"[,;|/]+", value):
        token = normalize_brand_key(part)
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def first_brand_token(value):
    """Legacy first-token extraction, retained for traceability."""
    tokens = split_brand_tokens(value)
    return tokens[0] if tokens else "unknown"


GENERIC_BRAND_ENTITY_KEYS = {
    "bio",
    "organic",
    "classic",
    "original",
    "extra",
    "selection",
    "gourmet",
    "finest",
    "light",
    "zero",
    "diet",
    "naturals",
    "simply",
}

COLLISION_PRONE_GENERIC_BRAND_KEYS = {
    "boost",
    "chef",
    "deluxe",
    "gourmet",
    "impact",
    "munch",
    "selection",
    "simply",
    "walkers",
}

NESTLE_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "bakers",
    "boost",
    "chef",
    "felix",
    "gourmet",
    "impact",
    "munch",
}

PEPSICO_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "starbucks rtd",
    "tropicana",
    "walkers",
}

MONDELEZ_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "granola",
    "lulu",
    "mondelez",
    "pepito",
    "philadelphia",
    "prince",
    "royal",
    "trident",
}

DANONE_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "alpro",
    "assil",
    "danao",
    "danone",
    "dany",
    "fantasia",
    "fruchtzwerge",
    "gallia",
    "light free",
    "nutricia",
    "oikos",
    "oykos",
    "silk",
    "too good",
    "veloute",
    "vitasnella",
}

COCACOLA_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "coca cola company",
    "the coca cola company",
    "costa",
    "innocent kids",
    "simply",
}

KRAFT_HEINZ_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "capri sun",
    "cracker barrel",
    "gevalia",
    "kraft",
    "maxwell house",
    "mio",
    "philadelphia",
    "wyler",
    "wyler s",
}

HERSHEY_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "cadbury",
    "fulfil",
    "heath",
    "kitkat",
    "lily s",
    "oh henry",
    "one",
    "rolo",
    "york",
    "zero",
}

STARBUCKS_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "doubleshot",
    "frappuccino",
    "starbucks",
    "starbucks chilled frappuccino",
    "starbucks doubleshot canned",
    "starbucks rtd",
    "teavana",
    "tripleshot",
}

UNILEVER_AUDIT_TOP9_BRAND_BLOCK_KEYS = {
    "amora",
    "ben and jerry s",
    "best foods",
    "bovril",
    "boost",
    "breyers",
    "bru",
    "carte d or",
    "colman s",
    "cornetto",
    "good humor",
    "hellmann s",
    "horlicks",
    "klik",
    "knorr",
    "lipton",
    "lipton dry tea",
    "magnum",
    "magnum ice cream",
    "maille",
    "maizena",
    "marmite",
    "miko",
    "pg tips",
    "pot noodle",
    "red label",
    "royco",
    "solero",
    "taj mahal",
    "telma",
    "viennetta",
    "wall s",
    "wall s ice cream",
}

COCACOLA_CORPORATE_PRODUCT_NAME_RECOVERY = [
    (re.compile(r"\bcoca\s*[- ]?\s*cola\b|\bcoke\b", re.IGNORECASE), "Coca-Cola"),
    (re.compile(r"\bdiet\s+coke\b", re.IGNORECASE), "Diet Coke"),
    (re.compile(r"\bfanta\b", re.IGNORECASE), "Fanta"),
    (re.compile(r"\bgold\s+peak\b", re.IGNORECASE), "Gold Peak"),
    (re.compile(r"\bhawai\b", re.IGNORECASE), "Hawai"),
    (re.compile(r"\bhonest\s+kids\b", re.IGNORECASE), "Honest Kids"),
    (re.compile(r"\bhonest\s+tea\b", re.IGNORECASE), "Honest Tea"),
    (re.compile(r"\bmezzo\s+mix\b", re.IGNORECASE), "Mezzo Mix"),
    (re.compile(r"\bminute\s+maid\b", re.IGNORECASE), "Minute Maid"),
    (re.compile(r"\bsprite\b", re.IGNORECASE), "Sprite"),
    (re.compile(r"\baha\b", re.IGNORECASE), "AHA"),
    (re.compile(r"\bcappy\b", re.IGNORECASE), "Cappy"),
    (re.compile(r"\bdasani\b", re.IGNORECASE), "Dasani"),
    (re.compile(r"\bfinley\b", re.IGNORECASE), "Finley"),
    (re.compile(r"\bsparletta\b", re.IGNORECASE), "Sparletta"),
    (re.compile(r"\bthums\s+up\b", re.IGNORECASE), "Thums Up"),
]

SIMPLY_COCA_COLA_BEVERAGE_PATTERNS = [
    re.compile(
        r"\bsimply\s+(orange|lemonade|limeade|apple|cranberry|fruit\s+punch|"
        r"grapefruit|peach|tropical|smoothie|juice|juices|beverage|beverages)\b",
        re.IGNORECASE,
    ),
]

SIMPLY_SPECIFIC_PRODUCT_NAME_RECOVERY = [
    (re.compile(r"\btostitos\b", re.IGNORECASE), "Tostitos"),
    (re.compile(r"\bruffles\b", re.IGNORECASE), "Ruffles"),
    (re.compile(r"\bdoritos\b", re.IGNORECASE), "Doritos"),
    (re.compile(r"\blay['’]?s\b|\blays\b", re.IGNORECASE), "Lay’s"),
    (re.compile(r"\bpop\s*[- ]?\s*tarts\b", re.IGNORECASE), "Pop-Tarts"),
    (re.compile(r"\bsimply\s+7\b", re.IGNORECASE), "Simply 7"),
    (re.compile(r"\bsimply\s+artisan\s+reserve\b", re.IGNORECASE), "Simply Artisan Reserve"),
    (re.compile(r"\bsimply\s+roundy['’]?s\b|\bsimply\s+roundys\b", re.IGNORECASE), "Simply Roundy's"),
    (re.compile(r"\bway\s+better\b|\bsimply\s+sprouted\b", re.IGNORECASE), "Way Better Snacks"),
    (re.compile(r"\bsimply\s+protein\b|\bsimplyprotein\b", re.IGNORECASE), "SimplyProtein"),
]


def clean_carrefour_brand_key(value):
    """Clean common duplicated Carrefour line forms before curated matching."""
    key = normalize_brand_key(value)
    if not key:
        return ""
    key = re.sub(r"\bcarrefour\s+carrefour\b", "carrefour", key)
    key = re.sub(r"\s+", " ", key).strip()

    known_middle_lines = [
        "carrefour bio",
        "carrefour classic",
        "carrefour extra",
        "carrefour original",
        "carrefour selection",
        "carrefour sensation",
        "carrefour sensation vegetal",
        "carrefour kids",
        "carrefour simpl",
        "reflets de france",
        "filiere qualite carrefour",
    ]
    for line in known_middle_lines:
        if key == f"{line} carrefour":
            return line
        if key == f"carrefour {line}" and not line.startswith("carrefour"):
            return line
    return key


def load_brand_entity_reference():
    """
    Load conservative references used only for brand entity extraction.

    This layer extracts the consumer-facing brand candidate. It does not assign
    parent-company ownership.
    """
    ref = {
        "parent_keys": set(),
        "top9_parent_keys": set(),
        "top9_exact": {},
        "top9_compact": {},
        "private_label_exact": {},
        "private_label_compact": {},
        "mapped_exact": {},
        "mapped_compact": {},
    }

    default_parent_keys = [
        "nestle",
        "pepsico",
        "pepsi co",
        "the coca cola company",
        "coca cola company",
        "coca cola",
        "mondelez",
        "mondelez international",
        "danone",
        "kraft heinz",
        "the kraft heinz company",
        "hershey",
        "the hershey company",
        "starbucks",
        "unilever",
        "unilever foods",
        "carrefour",
    ]
    ref["parent_keys"].update(default_parent_keys)
    ref["top9_parent_keys"].update(default_parent_keys)

    def add_brand(target_exact, target_compact, key, label, source):
        key = normalize_brand_key(key)
        if (
            not key
            or key in ("unknown", "nan", "none", "null")
            or key in GENERIC_BRAND_ENTITY_KEYS
        ):
            return
        record = {
            "canonical_brand": label.strip() if isinstance(label, str) and label.strip() else key,
            "source": source,
        }
        target_exact[key] = record
        compact = key.replace(" ", "")
        if compact:
            target_compact[compact] = record

    if os.path.exists(TOP_COMPANY_BRAND_MATRIX_PATH):
        top9 = pd.read_csv(TOP_COMPANY_BRAND_MATRIX_PATH, dtype=str, encoding="utf-8-sig").fillna("")
        for _, row in top9.iterrows():
            for col in [
                "core_cpg_group",
                "default_assigned_company",
                "us_assigned_company",
                "ca_assigned_company",
                "uk_assigned_company",
                "ie_assigned_company",
                "fr_assigned_company",
            ]:
                parent_key = normalize_brand_key(row.get(col, ""))
                if parent_key:
                    ref["parent_keys"].add(parent_key)
                    ref["top9_parent_keys"].add(parent_key)
            brand_key = row.get("brand_key") or row.get("brand")
            canonical = row.get("canonical_brand") or row.get("brand")
            brand_key_norm = normalize_brand_key(brand_key)
            core_group = normalize_brand_key(row.get("core_cpg_group", ""))
            notes = str(row.get("notes", "") or "").lower()
            if (
                core_group == "nestle"
                and (
                    brand_key_norm in NESTLE_AUDIT_TOP9_BRAND_BLOCK_KEYS
                    or "likely outside food/beverage mvp scope" in notes
                )
            ):
                continue
            if core_group == "pepsico" and brand_key_norm in PEPSICO_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "mondelez international" and brand_key_norm in MONDELEZ_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "danone" and brand_key_norm in DANONE_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "coca cola" and brand_key_norm in COCACOLA_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "kraft heinz" and brand_key_norm in KRAFT_HEINZ_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "hershey" and brand_key_norm in HERSHEY_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "starbucks" and brand_key_norm in STARBUCKS_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            if core_group == "unilever" and brand_key_norm in UNILEVER_AUDIT_TOP9_BRAND_BLOCK_KEYS:
                continue
            add_brand(
                ref["top9_exact"],
                ref["top9_compact"],
                brand_key,
                canonical,
                "top9_portfolio_token_match",
            )

    if os.path.exists(PRIVATE_LABEL_MAPPING_PATH):
        private_labels = pd.read_csv(PRIVATE_LABEL_MAPPING_PATH, dtype=str, encoding="utf-8-sig").fillna("")
        confirmed = private_labels[
            private_labels["action"].str.strip().str.lower() == "confirm"
        ]
        for _, row in confirmed.iterrows():
            add_brand(
                ref["private_label_exact"],
                ref["private_label_compact"],
                row.get("raw_brand_pattern", ""),
                row.get("canonical_brand", ""),
                "curated_private_label_mapping",
            )

    if os.path.exists(COMPANY_BRAND_MAPPING_PATH):
        mapping = pd.read_csv(COMPANY_BRAND_MAPPING_PATH, dtype=str, encoding="utf-8-sig").fillna("")
        for _, row in mapping.iterrows():
            parent_key = normalize_brand_key(row.get("parent_company", ""))
            if parent_key:
                ref["parent_keys"].add(parent_key)
            canonical = (
                row.get("normalized_brand")
                or row.get("brand")
                or row.get("primary_brand_db")
                or ""
            )
            for source_col in ["normalized_brand", "brand", "primary_brand_db"]:
                add_brand(
                    ref["mapped_exact"],
                    ref["mapped_compact"],
                    row.get(source_col, ""),
                    canonical,
                    "existing_company_brand_mapping_token_match",
                )

    # Parent/company names are not consumer-facing brand candidates in this layer.
    for parent_key in list(ref["parent_keys"]):
        for exact_name in ["top9_exact", "mapped_exact"]:
            ref[exact_name].pop(parent_key, None)
        for compact_name in ["top9_compact", "mapped_compact"]:
            ref[compact_name].pop(parent_key.replace(" ", ""), None)

    return ref


def lookup_brand_record(key, exact_lookup, compact_lookup):
    key = normalize_brand_key(key)
    if not key:
        return None
    return exact_lookup.get(key) or compact_lookup.get(key.replace(" ", ""))


def normalize_brand_alias(value, ref):
    """Normalize spelling/punctuation variants of a brand entity."""
    key = normalize_brand_key(value)
    if not key:
        return "unknown", "empty_brand_entity_fallback", "fallback_unreviewed"

    curated = CURATED_MECHANICAL_BRAND_ALIASES.get(key)
    if curated:
        return curated, "curated_mechanical_brand_alias", "confirmed"

    for exact_name, compact_name, source in [
        ("private_label_exact", "private_label_compact", "curated_private_label_mapping"),
        ("top9_exact", "top9_compact", "top9_portfolio_brand_alias"),
        ("mapped_exact", "mapped_compact", "existing_company_brand_mapping_alias"),
    ]:
        record = lookup_brand_record(key, ref[exact_name], ref[compact_name])
        if record:
            return record["canonical_brand"], source, "confirmed"

    # Keep the extracted brand entity as-is when no safe alias is known.
    return value, "brand_entity_raw_fallback", "fallback_unreviewed"


def normalize_brand_alias_from_row(row, ref):
    """Normalize brand alias with access to OFF tokens for protected line cases."""
    tokens = row["off_brand_tokens_list"]
    if any("dolce gusto" in token for token in tokens):
        return (
            "Nescafé Dolce Gusto",
            "curated_mechanical_brand_alias",
            "confirmed",
        )
    return normalize_brand_alias(row["brand_entity_raw"], ref)


def recover_specific_brand_from_generic_tokens(tokens):
    """Prefer specific same-token brand evidence over a generic first token."""
    for token in sorted(tokens, key=len, reverse=True):
        key = normalize_brand_key(token)
        if not key or key in COLLISION_PRONE_GENERIC_BRAND_KEYS:
            continue
        for generic_key in COLLISION_PRONE_GENERIC_BRAND_KEYS:
            if key.startswith(f"{generic_key} "):
                return key.title()
    return None


def recover_simply_brand_from_product_name(row):
    """Recover strong product-name evidence for Simply collision rows."""
    if normalize_brand_key(row.get("brand_entity_raw", "")) != "simply":
        return None
    name = row.get("product_name", "")
    if not isinstance(name, str) or not name.strip():
        return None

    for pattern, brand in SIMPLY_SPECIFIC_PRODUCT_NAME_RECOVERY:
        if pattern.search(name):
            return brand, "generic_simply_product_name_recovery"

    if row.get("query_category") == "beverages":
        for pattern in SIMPLY_COCA_COLA_BEVERAGE_PATTERNS:
            if pattern.search(name):
                return "Simply", "coca_cola_simply_beverage_product_name_recovery"
    return None


def recover_cocacola_brand_from_product_name(row):
    """Recover specific Coca-Cola brands when OFF only exposes the owner string."""
    if normalize_brand_key(row.get("brand_entity_raw", "")) not in {
        "coca cola company",
        "the coca cola company",
    }:
        return None
    name = row.get("product_name", "")
    if not isinstance(name, str) or not name.strip():
        return None
    for pattern, brand in COCACOLA_CORPORATE_PRODUCT_NAME_RECOVERY:
        if pattern.search(name):
            return brand, "coca_cola_corporate_product_name_recovery"
    return None


def derive_brand_family(normalized_brand):
    """Return broader brand family only for explicitly approved roll-ups."""
    key = normalize_brand_key(normalized_brand)
    if not key:
        return "unknown"
    return BRAND_FAMILY_BY_KEY.get(key, normalized_brand)


def load_reviewed_product_mapping_overrides():
    """Load exact reviewed barcode-level brand/category overrides."""
    if not os.path.exists(PRODUCT_MAPPING_OVERRIDE_PATH):
        return {}

    overrides = {}
    product_scope_columns = [
        "gtin",
        "region",
        "reviewed_brand",
        "reviewed_company",
        "reviewed_category",
        "source",
        "status",
    ]
    overrides_df = pd.read_csv(
        PRODUCT_MAPPING_OVERRIDE_PATH,
        dtype=str,
        encoding="utf-8-sig",
    ).fillna("")
    missing = [col for col in product_scope_columns if col not in overrides_df.columns]
    if missing:
        raise ValueError(
            "Reviewed product mapping override file is missing columns: "
            + ", ".join(missing)
        )

    active = overrides_df[
        overrides_df["status"].str.strip().str.lower().eq("active")
    ]
    for _, row in active.iterrows():
        barcode = str(row["gtin"]).strip()
        if not barcode:
            continue
        region = str(row.get("region", "")).strip()
        overrides.setdefault(barcode, []).append({
            "region": region,
            "brand": str(row["reviewed_brand"]).strip(),
            "category": str(row["reviewed_category"]).strip(),
            "source": str(row["source"]).strip()
                      or "reviewed_product_mapping_overrides.csv",
        })
    return overrides


def _product_override_for_row(overrides, barcode, region_codes):
    candidates = overrides.get(str(barcode or "").strip()) or []
    if not candidates:
        return None
    row_regions = {
        value.strip()
        for value in str(region_codes or "").split("|")
        if value.strip()
    }
    unscoped = None
    for candidate in candidates:
        region = candidate.get("region", "")
        if not region:
            unscoped = candidate
            continue
        if region in row_regions:
            return candidate
    return unscoped


def apply_reviewed_product_mapping_overrides(df):
    """Apply exact reviewed GTIN decisions without changing raw OFF fields."""
    overrides = load_reviewed_product_mapping_overrides()
    if not overrides or "barcode" not in df.columns:
        return df

    matched = 0
    region_values = df.get("observed_market_region_codes", pd.Series("", index=df.index))
    for idx, barcode in df["barcode"].fillna("").astype(str).items():
        regions = region_values.fillna("").astype(str).loc[idx]
        override = _product_override_for_row(overrides, barcode, regions)
        if not override:
            continue
        matched += 1
        brand = override["brand"]
        category = override["category"]
        source = override["source"]

        if brand:
            df.at[idx, "brand_entity_raw"] = brand
            df.at[idx, "brand_entity_source"] = source
            df.at[idx, "normalized_brand"] = brand
            df.at[idx, "brand_family"] = derive_brand_family(brand)
            df.at[idx, "brand_alias_source"] = source
            df.at[idx, "brand_alias_review_status"] = "reviewed_product_override"
        if category:
            df.at[idx, "query_category"] = None if category == "OUT_OF_SCOPE" else category

    if matched:
        print(f"  Reviewed product mapping overrides applied: {matched:,} rows")
    return df


def recover_nestle_snacks_brand_from_product_name(row):
    """Recover only approved Nestlé snack portfolio brands from product names."""
    if row.get("query_category") != "snacks":
        return None
    countries = str(row.get("countries", "") or "").lower()
    if row.get("brand_entity_source") != "first_off_brand_token_fallback":
        return None
    if normalize_brand_key(row.get("legacy_primary_brand", "")) != "nestle":
        return None
    if normalize_brand_key(row.get("brand_entity_raw", "")) != "nestle":
        return None
    name = row.get("product_name", "")
    if not isinstance(name, str) or not name.strip():
        return None

    if "en:france" in countries:
        region = "FRANCE"
        patterns = NESTLE_FRANCE_SNACKS_PRODUCT_NAME_RECOVERY
    elif "en:united-kingdom" in countries or "en:ireland" in countries:
        region = "UK_IE"
        patterns = NESTLE_UK_IE_SNACKS_PRODUCT_NAME_RECOVERY
    elif "en:united-states" in countries or "en:canada" in countries:
        region = "US_CANADA"
        patterns = NESTLE_US_CANADA_SNACKS_PRODUCT_NAME_RECOVERY
    else:
        return None

    for pattern, brand in patterns:
        if pattern.search(name):
            return brand, NESTLE_PRODUCT_NAME_RECOVERY_SOURCES[region]
    return None


def derive_brand_entity_from_tokens(tokens, legacy, ref):
    """
    Derive brand_entity_raw from OFF brand tokens using conservative rules.

    Returns (brand_entity_raw, brand_entity_source).
    """
    parent_tokens = [token for token in tokens if token in ref["parent_keys"]]
    top9_parent_tokens = [
        token for token in tokens if token in ref["top9_parent_keys"]
    ]

    # 1. Known Top 9 parent/company token + known portfolio brand token.
    if top9_parent_tokens:
        for token in tokens:
            if token in ref["top9_parent_keys"]:
                continue
            record = lookup_brand_record(token, ref["top9_exact"], ref["top9_compact"])
            if record:
                return record["canonical_brand"], record["source"]

        # Also catch single dirty tokens such as "nestle kit kat".
        for token in tokens:
            for parent_key in sorted(ref["top9_parent_keys"], key=len, reverse=True):
                if token.startswith(parent_key + " "):
                    remainder = token[len(parent_key) + 1:].strip()
                    record = lookup_brand_record(
                        remainder, ref["top9_exact"], ref["top9_compact"]
                    )
                    if record:
                        return record["canonical_brand"], record["source"]

    # 2. Curated private-label line. Prefer the most specific reviewed line
    # when OFF lists both a retailer banner and a line, e.g. "Auchan, Auchan Bio".
    for token in sorted(tokens, key=len, reverse=True):
        cleaned = clean_carrefour_brand_key(token)
        record = lookup_brand_record(
            cleaned, ref["private_label_exact"], ref["private_label_compact"]
        )
        if record:
            return record["canonical_brand"], record["source"]

    # 3. Known mapped non-Top-9 brand token from existing company mapping.
    for token in tokens:
        if token in ref["parent_keys"]:
            continue
        record = lookup_brand_record(token, ref["mapped_exact"], ref["mapped_compact"])
        if record:
            return record["canonical_brand"], record["source"]

    # 4. If the first token is generic/collision-prone, preserve a more
    # specific same-field token rather than collapsing to the generic token.
    if legacy in COLLISION_PRONE_GENERIC_BRAND_KEYS:
        specific = recover_specific_brand_from_generic_tokens(tokens)
        if specific:
            return specific, "specific_token_over_generic_fallback"

    # 5. Traceable fallback.
    return legacy, "first_off_brand_token_fallback"


def derive_brand_entity(row, ref):
    return derive_brand_entity_from_tokens(
        row["off_brand_tokens_list"],
        row["legacy_primary_brand"],
        ref,
    )


def preserve_raw_nutrition_values(df):
    """Keep OFF-provided nutrition values before compatibility capping."""
    copied = 0
    for source_col, raw_col in RAW_NUTRIMENT_COLS.items():
        if source_col in df.columns and raw_col not in df.columns:
            df[raw_col] = df[source_col]
            copied += 1
    print(f"    Raw OFF nutrition columns preserved ({copied} columns)")
    return df


def _append_reason(existing, reason):
    if not isinstance(existing, str) or existing.strip() == "":
        return reason
    parts = [p for p in existing.split("|") if p]
    if reason not in parts:
        parts.append(reason)
    return "|".join(parts)


def _ensure_nutrition_quality_columns(df):
    for col in NUTRITION_QUALITY_COLS:
        if col not in df.columns:
            if col == "nutrition_quality_status":
                df[col] = "valid"
            elif col.startswith("include_in_"):
                df[col] = True
            else:
                df[col] = ""
    return df


def _apply_data_quality_error_flags(df, mask):
    df.loc[mask, "nutrition_quality_status"] = "data_quality_error"
    df.loc[mask, "outlier_type"] = "data_quality_error"
    df.loc[mask, "include_in_product_table"] = False
    df.loc[mask, "include_in_aggregates"] = False
    df.loc[mask, "include_in_charts"] = False
    return df


def flag_basic_impossible_values(df):
    """Flag the first governance step: biologically impossible values.

    Negative per-100g/100ml nutrition values and energy above 900
    kcal/100g are treated as basic impossible source-data errors. The
    raw OFF values remain available in *_off_raw columns; the
    compatibility analysis columns are set to NaN so existing downstream
    views do not display impossible numbers.
    """
    df = _ensure_nutrition_quality_columns(df)
    total_flagged_values = 0

    for col in BASIC_IMPOSSIBLE_NEGATIVE_COLS:
        if col not in df.columns:
            continue

        negative_mask = df[col] < 0
        negative_count = int(negative_mask.sum())
        if negative_count == 0:
            continue

        print(f"    Flagged {negative_count} negative value(s) in {col}")
        df.loc[negative_mask, "nutrition_quality_reason"] = df.loc[
            negative_mask, "nutrition_quality_reason"
        ].apply(lambda x: _append_reason(x, "negative_nutrient_value"))
        df.loc[negative_mask, col] = None
        df = _apply_data_quality_error_flags(df, negative_mask)
        total_flagged_values += negative_count

    if "energy_kcal" in df.columns:
        energy_over_cap_mask = df["energy_kcal"] > MAX_ENERGY_KCAL_100G
        energy_over_cap_count = int(energy_over_cap_mask.sum())
        if energy_over_cap_count > 0:
            print(f"    Flagged {energy_over_cap_count} energy value(s) "
                  f"above {MAX_ENERGY_KCAL_100G} kcal/100g")
            df.loc[energy_over_cap_mask, "nutrition_quality_reason"] = df.loc[
                energy_over_cap_mask, "nutrition_quality_reason"
            ].apply(lambda x: _append_reason(x, "energy_above_900_kcal"))
            df.loc[energy_over_cap_mask, "energy_kcal"] = None
            df = _apply_data_quality_error_flags(df, energy_over_cap_mask)
            total_flagged_values += energy_over_cap_count

    if total_flagged_values == 0:
        print(f"    No basic impossible values found")
    else:
        flagged_rows = int(
            df["nutrition_quality_reason"]
            .astype(str)
            .str.contains(
                "negative_nutrient_value|energy_above_900_kcal",
                regex=True,
            )
            .sum()
        )
        print(f"    Basic impossible values flagged: {flagged_rows} product row(s)")
    return df


def _apply_reason(df, mask, reason):
    if int(mask.sum()) == 0:
        return df
    df.loc[mask, "nutrition_quality_reason"] = df.loc[
        mask, "nutrition_quality_reason"
    ].apply(lambda x: _append_reason(x, reason))
    df = _apply_data_quality_error_flags(df, mask)
    return df


def flag_per_100g_structural_checks(df):
    """Flag per-100g structural contradictions and impossible totals."""
    df = _ensure_nutrition_quality_columns(df)
    structural_masks = []

    for col in STRUCTURAL_MAX_COLS:
        if col not in df.columns:
            continue
        mask = df[col] > MAX_NUTRIENT_G_100G
        count = int(mask.sum())
        if count == 0:
            continue
        print(f"    Flagged {count} value(s) above {MAX_NUTRIENT_G_100G}g in {col}")
        df = _apply_reason(df, mask, "nutrient_value_above_100g")
        df.loc[mask, col] = None
        structural_masks.append(mask)

    if {"sugars_100g", "carbs_100g"}.issubset(df.columns):
        mask = (
            df["sugars_100g"].notna()
            & df["carbs_100g"].notna()
            & (df["sugars_100g"] > df["carbs_100g"])
        )
        count = int(mask.sum())
        if count > 0:
            print(f"    Flagged {count} row(s) with sugars_100g > carbs_100g")
            df = _apply_reason(df, mask, "sugars_greater_than_carbohydrates")
            df.loc[mask, "sugars_100g"] = None
            structural_masks.append(mask)

    if {"saturated_fat_100g", "fat_100g"}.issubset(df.columns):
        mask = (
            df["saturated_fat_100g"].notna()
            & df["fat_100g"].notna()
            & (df["saturated_fat_100g"] > df["fat_100g"])
        )
        count = int(mask.sum())
        if count > 0:
            print(f"    Flagged {count} row(s) with saturated_fat_100g > fat_100g")
            df = _apply_reason(df, mask, "saturated_fat_greater_than_fat")
            df.loc[mask, "saturated_fat_100g"] = None
            structural_masks.append(mask)

    macro_cols = ["protein_100g", "carbs_100g", "fat_100g"]
    if set(macro_cols).issubset(df.columns):
        macro_sum = df[macro_cols].sum(axis=1, min_count=3)
        mask = macro_sum > MAX_MACRO_SUM_G_100G
        count = int(mask.sum())
        if count > 0:
            print(f"    Flagged {count} row(s) with protein + carbs + fat > "
                  f"{MAX_MACRO_SUM_G_100G}g")
            df = _apply_reason(df, mask, "macros_exceed_100g")
            df.loc[mask, macro_cols] = None
            structural_masks.append(mask)

    if not structural_masks:
        print(f"    No per-100g structural issues found")
    else:
        any_structural = structural_masks[0].copy()
        for mask in structural_masks[1:]:
            any_structural = any_structural | mask
        print(f"    Per-100g structural checks flagged: "
              f"{int(any_structural.sum())} product row(s)")
    return df


def flag_per_100kcal_nutrient_density_checks(df):
    """Flag nutrients that exceed plausible density per 100 kcal."""
    df = _ensure_nutrition_quality_columns(df)
    if "energy_kcal" not in df.columns:
        print(f"    No per-100 kcal density checks run; energy_kcal is missing")
        return df

    valid_energy = df["energy_kcal"].notna() & (df["energy_kcal"] > 0)
    density_masks = []

    for nutrient_col, limit in NUTRIENT_DENSITY_LIMITS_PER_100KCAL.items():
        if nutrient_col not in df.columns:
            continue

        density = (df[nutrient_col] / df["energy_kcal"] * 100).where(valid_energy)
        mask = density.notna() & (density > limit)
        count = int(mask.sum())
        if count == 0:
            continue

        print(f"    Flagged {count} row(s) with {nutrient_col} density > "
              f"{limit:g}g/100 kcal")
        df = _apply_reason(df, mask, "nutrient_density_exceeds_energy_limit")
        df.loc[mask, nutrient_col] = None
        density_masks.append(mask)

    if not density_masks:
        print(f"    No per-100 kcal nutrient-density issues found")
    else:
        any_density = density_masks[0].copy()
        for mask in density_masks[1:]:
            any_density = any_density | mask
        print(f"    Per-100 kcal nutrient-density checks flagged: "
              f"{int(any_density.sum())} product row(s)")
    return df


def _series_for_check(df, col):
    raw_col = RAW_NUTRIMENT_COLS.get(col)
    if raw_col in df.columns:
        return df[raw_col]
    return df[col]


def flag_energy_consistency_check(df):
    """Flag reported energy that is inconsistent with macro energy."""
    df = _ensure_nutrition_quality_columns(df)
    required = ["energy_kcal", "protein_100g", "carbs_100g", "fat_100g"]
    if not set(required).issubset(df.columns):
        print(f"    No energy consistency check run; required columns are missing")
        return df

    energy = _series_for_check(df, "energy_kcal")
    protein = _series_for_check(df, "protein_100g")
    carbs = _series_for_check(df, "carbs_100g")
    fat = _series_for_check(df, "fat_100g")

    calculated_energy = 4 * (protein + carbs) + 9 * fat
    abs_diff = (calculated_energy - energy).abs()
    rel_diff = (abs_diff / energy.abs() * 100).where(energy.notna() & (energy != 0))

    mask = (
        energy.notna()
        & protein.notna()
        & carbs.notna()
        & fat.notna()
        & (energy > 0)
        & (calculated_energy > 0)
        & (abs_diff > ENERGY_CONSISTENCY_ABS_KCAL_THRESHOLD)
        & (rel_diff > ENERGY_CONSISTENCY_REL_DIFF_THRESHOLD)
    )
    count = int(mask.sum())
    if count == 0:
        print(f"    No energy consistency issues found")
        return df

    print(f"    Flagged {count} row(s) where reported energy differs from "
          f"macro-calculated energy")
    df = _apply_reason(df, mask, "energy_inconsistent_with_macros")
    df.loc[mask, "energy_kcal"] = None
    return df


def apply_legacy_compatibility_caps(df):
    """Keep legacy capped analysis columns while raw OFF values are preserved.

    The *_off_raw columns preserve the source values. The main nutrition
    columns keep their historical downstream contract for now: values
    above old per-100g caps are set to NaN so existing app/precompute
    behavior does not change before later governance steps are reviewed.
    This is compatibility handling, not completion of the structural
    outlier-review steps.
    """
    total_capped = 0

    for col, cap in NUTRIMENT_CAPS.items():
        if col not in df.columns:
            continue

        over_cap_mask = df[col] > cap
        over_cap_count = int(over_cap_mask.sum())
        if over_cap_count > 0:
            print(f"    Legacy-capped {over_cap_count} value(s) in {col} "
                  f"(max was {df.loc[over_cap_mask, col].max():.1f}, cap={cap})")
            df.loc[over_cap_mask, col] = None
            total_capped += over_cap_count

    if total_capped == 0:
        print(f"    No legacy compatibility caps applied")
    else:
        print(f"    Legacy compatibility caps applied: {total_capped} value(s)")
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


def add_completeness_score(df):
    """Vectorized completeness score using the same field-population rule."""
    available = [col for col in COMPLETENESS_COLS if col in df.columns]
    if not available:
        df["completeness_score"] = 0
        return df
    filled = pd.DataFrame(index=df.index)
    for col in available:
        values = df[col]
        if values.dtype == object:
            filled[col] = (
                values.notna()
                & ~values.astype(str).str.strip().isin(["", "nan", "NaN", "none", "None"])
            )
        else:
            filled[col] = values.notna()
    df["completeness_score"] = (
        filled.sum(axis=1) / len(COMPLETENESS_COLS) * 100
    ).round().astype(int)
    return df


# -- Main cleaning pipeline ---------------------------------------------------

def load_region_mapping(path=REGION_MAPPING_PATH):
    """Load data/country_region_mapping.csv into a dict mapping each OFF
    country_tag (e.g. 'en:france') to its region_code (e.g. 'FRANCE').

    Returns ({} , None) if the file is missing, so the pipeline can run
    without it (the region column is then left as OTHER_MIXED everywhere
    and the app's region filter simply has one bucket). The CSV is the
    single source of truth — region groupings are never hardcoded here.

    Rows with an empty country_tag (the OTHER_MIXED sentinel row) are
    skipped: OTHER_MIXED is assigned by absence of any mapped tag, not by
    an explicit tag, so it must not enter the lookup table.
    """
    if not os.path.exists(path):
        print(f"  [region] mapping file not found at {path} — "
              f"all products will be tagged OTHER_MIXED")
        return {}

    mapping_df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    tag_to_region = {}
    for _, row in mapping_df.iterrows():
        tag = row.get("country_tag", "").strip().lower()
        region = row.get("region_code", "").strip()
        if tag and region:
            tag_to_region[tag] = region
    return tag_to_region


def derive_region_codes(countries_value, tag_to_region):
    """Map a product's pipe-separated OFF countries field (e.g.
    'en:france|en:belgium') to a pipe-separated, de-duplicated string of
    region codes (e.g. 'FRANCE|BENELUX'), preserving first-seen order.

    Rules (from the product brief, Market / region section):
    - A product can belong to multiple regions.
    - If at least one country tag maps to a region, use the mapped
      region(s) and do NOT add OTHER_MIXED.
    - Use OTHER_MIXED only when no country tag maps to any region
      (including when the countries field is empty/missing).
    """
    if not isinstance(countries_value, str) or countries_value.strip().lower() in ("", "nan"):
        return "OTHER_MIXED"

    seen = []
    for tag in countries_value.split("|"):
        tag = tag.strip().lower()
        region = tag_to_region.get(tag)
        if region and region not in seen:
            seen.append(region)

    return "|".join(seen) if seen else "OTHER_MIXED"


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

    # Step 4: Preserve OFF brands and derive traceable brand entity fields.
    # primary_brand remains the legacy downstream compatibility field for now.
    df["off_brands_raw"] = df["brands"]
    df["off_brand_tokens_list"] = df["off_brands_raw"].apply(split_brand_tokens)
    df["off_brand_tokens"] = df["off_brand_tokens_list"].apply(
        lambda tokens: "|".join(tokens) if tokens else ""
    )
    df["legacy_primary_brand"] = df["off_brands_raw"].apply(first_brand_token)

    brand_entity_ref = load_brand_entity_reference()
    unique_brand_patterns = (
        df[["off_brand_tokens", "legacy_primary_brand"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    brand_entity_cache = {}
    for _, pattern_row in unique_brand_patterns.iterrows():
        tokens = (
            pattern_row["off_brand_tokens"].split("|")
            if pattern_row["off_brand_tokens"]
            else []
        )
        cache_key = (
            pattern_row["off_brand_tokens"],
            pattern_row["legacy_primary_brand"],
        )
        brand_entity_cache[cache_key] = derive_brand_entity_from_tokens(
            tokens,
            pattern_row["legacy_primary_brand"],
            brand_entity_ref,
        )

    cache_keys = list(zip(df["off_brand_tokens"], df["legacy_primary_brand"]))
    derived_brand_entities = [brand_entity_cache[key] for key in cache_keys]
    df["brand_entity_raw"] = [value[0] for value in derived_brand_entities]
    df["brand_entity_source"] = [value[1] for value in derived_brand_entities]
    df["brand_entity_raw_before_product_name_recovery"] = df["brand_entity_raw"]
    df["brand_entity_source_before_product_name_recovery"] = df["brand_entity_source"]

    recovered_nestle = df.apply(
        recover_nestle_snacks_brand_from_product_name,
        axis=1,
    )
    recovery_mask = recovered_nestle.notna()
    if recovery_mask.any():
        df.loc[recovery_mask, "brand_entity_raw"] = [
            value[0] for value in recovered_nestle[recovery_mask]
        ]
        df.loc[recovery_mask, "brand_entity_source"] = [
            value[1] for value in recovered_nestle[recovery_mask]
        ]

    recovered_simply = df.apply(
        recover_simply_brand_from_product_name,
        axis=1,
    )
    simply_recovery_mask = recovered_simply.notna()
    if simply_recovery_mask.any():
        df.loc[simply_recovery_mask, "brand_entity_raw"] = [
            value[0] for value in recovered_simply[simply_recovery_mask]
        ]
        df.loc[simply_recovery_mask, "brand_entity_source"] = [
            value[1] for value in recovered_simply[simply_recovery_mask]
        ]

    recovered_cocacola = df.apply(
        recover_cocacola_brand_from_product_name,
        axis=1,
    )
    cocacola_recovery_mask = recovered_cocacola.notna()
    if cocacola_recovery_mask.any():
        df.loc[cocacola_recovery_mask, "brand_entity_raw"] = [
            value[0] for value in recovered_cocacola[cocacola_recovery_mask]
        ]
        df.loc[cocacola_recovery_mask, "brand_entity_source"] = [
            value[1] for value in recovered_cocacola[cocacola_recovery_mask]
        ]

    changed_brand_entity = (
        df["legacy_primary_brand"].fillna("") != df["brand_entity_raw"].fillna("")
    ).sum()
    print(
        f"  Step 4  - Brand entity extraction fields added "
        f"({changed_brand_entity:,} differ from legacy first token)"
    )
    print(
        f"            Nestlé snacks product-name recovery: "
        f"{int(recovery_mask.sum()):,} rows"
    )
    print(
        f"            Simply collision product-name recovery: "
        f"{int(simply_recovery_mask.sum()):,} rows"
    )
    print(
        f"            Coca-Cola corporate product-name recovery: "
        f"{int(cocacola_recovery_mask.sum()):,} rows"
    )

    # Step 4a: Normalize brand aliases from brand_entity_raw.
    unique_alias_patterns = (
        df[["brand_entity_raw", "off_brand_tokens"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    alias_cache = {}
    for _, pattern_row in unique_alias_patterns.iterrows():
        cache_key = (
            pattern_row["brand_entity_raw"],
            pattern_row["off_brand_tokens"],
        )
        tokens = (
            pattern_row["off_brand_tokens"].split("|")
            if pattern_row["off_brand_tokens"]
            else []
        )
        alias_cache[cache_key] = normalize_brand_alias_from_row(
            {
                "brand_entity_raw": pattern_row["brand_entity_raw"],
                "off_brand_tokens_list": tokens,
            },
            brand_entity_ref,
        )
    normalized_aliases = [
        alias_cache[key]
        for key in zip(df["brand_entity_raw"], df["off_brand_tokens"])
    ]
    df["normalized_brand"] = [value[0] for value in normalized_aliases]
    df["brand_alias_source"] = [value[1] for value in normalized_aliases]
    df["brand_alias_review_status"] = [value[2] for value in normalized_aliases]
    df["brand_family"] = df["normalized_brand"].map(derive_brand_family)
    changed_normalized_brand = (
        df["brand_entity_raw"].fillna("") != df["normalized_brand"].fillna("")
    ).sum()
    changed_brand_family = (
        df["normalized_brand"].fillna("") != df["brand_family"].fillna("")
    ).sum()
    print(
        f"  Step 4a - Brand alias normalization fields added "
        f"({changed_normalized_brand:,} differ from brand_entity_raw)"
    )
    print(
        f"            Brand family roll-up: "
        f"{changed_brand_family:,} rows differ from normalized_brand"
    )
    df = apply_reviewed_product_mapping_overrides(df)

    # Step 4b: Normalise brands for the legacy primary_brand field.
    df["brands"] = (
        df["brands"]
        .str.lower()
        .str.strip()
        .str.strip(",")
    )
    df["primary_brand"] = df["legacy_primary_brand"]
    # Strip accents for consistent grouping - nestle variants are already ASCII.
    # Full company normalisation now maintained in
    # data/reference/company_brand_mapping.csv (see docs/BRAND_COMPANY_MAPPING.md)
    df["primary_brand"] = df["primary_brand"]\
        .str.normalize("NFKD")\
        .str.encode("ascii", errors="ignore")\
        .str.decode("ascii")
    print(f"  Step 4b - Legacy primary_brand retained and accents stripped")

    # Step 4c: Apply legacy brand alias mapping to primary_brand only.
    alias_path = os.path.join(ROOT, "data", "reference", "brand_alias_mapping.csv")
    if os.path.exists(alias_path):
        alias_df = pd.read_csv(alias_path, encoding="utf-8-sig", dtype=str).fillna("")
        confirmed = alias_df[
            alias_df["action"].str.strip().str.lower() == "confirm"
        ]
        alias_map = dict(zip(
            confirmed["variant_brand"].str.strip(),
            confirmed["canonical_brand"].str.strip(),
        ))
        if alias_map:
            df["primary_brand"] = df["primary_brand"].replace(alias_map)
            print(f"  Step 4c - Legacy brand alias: {len(alias_map)} rules applied")
        else:
            print(f"  Step 4c - Legacy brand alias: file found but no confirmed rows")
    else:
        print(f"  Step 4c - Legacy brand alias: no mapping file found (skipped)")

    # Step 5: Detect ingredient language
    df["ingredients_lang"] = df["ingredients_text"].apply(detect_language)
    lang_counts = df["ingredients_lang"].value_counts().to_dict()
    print(f"  Step 5  - Language detection: {lang_counts}")

    # Step 6: Coerce nutritional columns to numeric
    for col in NUTRIMENT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"  Step 6  - Nutritional columns coerced to numeric")

    # Step 7: Preserve raw OFF values, flag hard data-quality errors, and
    # keep legacy caps for downstream compatibility.
    print(f"  Step 7  - Nutrition quality flags:")
    df = preserve_raw_nutrition_values(df)
    df = flag_basic_impossible_values(df)
    df = flag_per_100g_structural_checks(df)
    df = flag_per_100kcal_nutrient_density_checks(df)
    df = flag_energy_consistency_check(df)
    df = apply_legacy_compatibility_caps(df)

    # Step 8: Add missing value flags
    df = add_missing_flags(df)
    print(f"  Step 8  - Missing value flags added "
          f"({len(NUTRIMENT_COLS)} flag columns)")

    # Step 9: Normalise nutriscore to uppercase
    df["nutriscore_grade"] = (
        df["nutriscore_grade"]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace("NAN", None)
    )
    print(f"  Step 9  - Nutriscore normalised to uppercase")

    # Step 10: Convert Unix timestamps to readable dates
    for col in ["created_t", "last_modified_t"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
    print(f"  Step 10 - Timestamps converted to datetime")

    # Step 11: Add completeness score
    df = add_completeness_score(df)
    avg = df["completeness_score"].mean()
    print(f"  Step 11 - Completeness score added (avg: {avg:.1f}/100)")

    # Step 11b: Extract primary country from pipe-separated countries field
    df["primary_country"] = df["countries"].apply(
        lambda x: str(x).split("|")[0]
                         .replace("en:", "")
                         .replace("-", " ")
                         .title()
                  if isinstance(x, str) and x.strip() not in ("", "nan")
                  else "Unknown"
    )
    print(f"  Step 11b- Primary country extracted")
    print(f"            Top countries: "
          f"{df['primary_country'].value_counts().head(5).to_dict()}")

    # Step 11c: Derive observed_market_region_codes from the full
    # countries field (NOT primary_country — a product can map to
    # multiple regions). Grouping is defined entirely by
    # data/country_region_mapping.csv; see derive_region_codes() and
    # the brief's Market / region section. Used by the app's
    # Market / region filter.
    tag_to_region = load_region_mapping()
    df["observed_market_region_codes"] = df["countries"].apply(
        lambda x: derive_region_codes(x, tag_to_region)
    )
    region_preview = (
        df["observed_market_region_codes"].value_counts().head(5).to_dict()
    )
    print(f"  Step 11c- Market region codes derived")
    print(f"            Top region combinations: {region_preview}")

    # Step 12: Flag rows eligible for ingredient-marker analysis (EN and FR only)
    # OTHER/UNKNOWN rows retained for nutritional analysis but excluded
    # from Option A ingredient marker analysis.
    # BOTH = bilingual packaging, treated as eligible.
    # Coverage: ~84% of rows based on 18 May 2026 sample.
    # See docs/OBSERVATIONS.md OBS-001 and OBS-008.
    df["ingredient_analysis_eligible"] = df["ingredients_lang"].isin(["EN", "FR", "BOTH"])
    eligible = df["ingredient_analysis_eligible"].sum()
    print(f"  Step 12 - Ingredient analysis eligible: {eligible} of {len(df)} rows "
          f"({eligible/len(df)*100:.0f}%)")

    # Step 13: Add nullable product_segment_label (v2 stub)
    # Intentionally empty in v1. K-Means (Option B) will populate this.
    # Column exists now so SQLite schema and Power BI model don't break.
    # See docs/ADR.md ADR-005.
    if "product_segment_label" not in df.columns:
        df["product_segment_label"] = None
    print(f"  Step 13 - product_segment_label column added (null, v2 stub)")

    if "off_brand_tokens_list" in df.columns:
        df = df.drop(columns=["off_brand_tokens_list"])
    df.attrs["nestle_recovery_before_cols"] = [
        "brand_entity_raw_before_product_name_recovery",
        "brand_entity_source_before_product_name_recovery",
    ]

    return df


def write_brand_entity_extraction_review(df):
    """Write Layer 1 audit: legacy first token vs extracted brand entity."""
    os.makedirs(BRAND_MAPPING_REVIEW_DIR, exist_ok=True)
    output_path = os.path.join(
        BRAND_MAPPING_REVIEW_DIR,
        "brand_entity_extraction_review.csv",
    )

    changed = df[
        df["legacy_primary_brand"].fillna("")
        != df["brand_entity_raw"].fillna("")
    ].copy()

    if changed.empty:
        review = pd.DataFrame(columns=[
            "off_brands_raw",
            "off_brand_tokens",
            "legacy_primary_brand",
            "brand_entity_raw",
            "brand_entity_source",
            "product_count",
            "primary_country",
            "observed_market_region_codes",
            "query_category",
            "example_product_names",
        ])
    else:
        review = (
            changed.groupby(
                [
                    "off_brands_raw",
                    "off_brand_tokens",
                    "legacy_primary_brand",
                    "brand_entity_raw",
                    "brand_entity_source",
                    "primary_country",
                    "observed_market_region_codes",
                    "query_category",
                ],
                dropna=False,
            )
            .agg(
                product_count=("barcode", "count"),
                example_product_names=(
                    "product_name",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
            )
            .reset_index()
            .sort_values("product_count", ascending=False)
        )

    review.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"  Brand entity extraction review -> "
        f"data/brand_mapping_review/brand_entity_extraction_review.csv "
        f"({len(review):,} grouped rows)"
    )


def write_brand_alias_normalization_review(df):
    """Write Layer 2 audit: extracted brand entity vs normalized brand."""
    os.makedirs(BRAND_MAPPING_REVIEW_DIR, exist_ok=True)
    output_path = os.path.join(
        BRAND_MAPPING_REVIEW_DIR,
        "brand_alias_normalization_review.csv",
    )

    changed = df[
        df["brand_entity_raw"].fillna("")
        != df["normalized_brand"].fillna("")
    ].copy()

    if changed.empty:
        review = pd.DataFrame(columns=[
            "brand_entity_raw",
            "normalized_brand",
            "brand_alias_source",
            "brand_alias_review_status",
            "brand_entity_source",
            "product_count",
            "primary_country",
            "observed_market_region_codes",
            "query_category",
            "example_product_names",
            "example_off_brands_raw",
        ])
    else:
        review = (
            changed.groupby(
                [
                    "brand_entity_raw",
                    "normalized_brand",
                    "brand_alias_source",
                    "brand_alias_review_status",
                    "brand_entity_source",
                    "primary_country",
                    "observed_market_region_codes",
                    "query_category",
                ],
                dropna=False,
            )
            .agg(
                product_count=("barcode", "count"),
                example_product_names=(
                    "product_name",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
                example_off_brands_raw=(
                    "off_brands_raw",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
            )
            .reset_index()
            .sort_values("product_count", ascending=False)
        )

    review.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"  Brand alias normalization review -> "
        f"data/brand_mapping_review/brand_alias_normalization_review.csv "
        f"({len(review):,} grouped rows)"
    )


def load_single_parent_company_lookup():
    """Best-effort context lookup for alias audit only."""
    lookup = {}
    if not os.path.exists(COMPANY_BRAND_MAPPING_PATH):
        return lookup
    try:
        mapping = pd.read_csv(
            COMPANY_BRAND_MAPPING_PATH,
            encoding="utf-8-sig",
            dtype=str,
        ).fillna("")
    except Exception:
        return lookup

    mapping["brand_key"] = mapping["primary_brand_db"].map(normalize_brand_key)
    mapping = mapping[
        (mapping["brand_key"] != "")
        & (mapping["parent_company"].str.strip() != "")
        & ~mapping["parent_company"].str.lower().isin([
            "manual review",
            "other / not mapped to a company",
        ])
    ]
    for brand_key, group in mapping.groupby("brand_key", dropna=False):
        companies = sorted(set(group["parent_company"].str.strip()))
        if len(companies) == 1:
            lookup[brand_key] = companies[0]
        elif len(companies) > 1:
            lookup[brand_key] = "market_scoped_or_multiple"
    return lookup


def write_brand_alias_cleanup_audit(df):
    """Write audit for launch-safe alias cleanup and brand-family roll-up."""
    os.makedirs(BRAND_MAPPING_REVIEW_DIR, exist_ok=True)
    output_path = os.path.join(
        BRAND_MAPPING_REVIEW_DIR,
        "brand_alias_cleanup_audit.csv",
    )

    changed = df[
        (
            df["brand_entity_raw"].fillna("")
            != df["normalized_brand"].fillna("")
        )
        | (
            df["normalized_brand"].fillna("")
            != df["brand_family"].fillna("")
        )
    ].copy()
    parent_lookup = load_single_parent_company_lookup()

    if changed.empty:
        audit = pd.DataFrame(columns=[
            "old_normalized_brand",
            "new_normalized_brand",
            "brand_family",
            "parent_company",
            "product_count",
            "query_category",
            "primary_country",
            "observed_market_region_codes",
            "brand_alias_source",
            "brand_alias_review_status",
            "example_product_names",
            "example_off_brands_raw",
        ])
    else:
        changed["old_normalized_brand"] = changed["brand_entity_raw"]
        changed["new_normalized_brand"] = changed["normalized_brand"]
        changed["parent_company"] = changed["normalized_brand"].map(
            lambda value: parent_lookup.get(normalize_brand_key(value), "")
        )
        audit = (
            changed.groupby(
                [
                    "old_normalized_brand",
                    "new_normalized_brand",
                    "brand_family",
                    "parent_company",
                    "query_category",
                    "primary_country",
                    "observed_market_region_codes",
                    "brand_alias_source",
                    "brand_alias_review_status",
                ],
                dropna=False,
            )
            .agg(
                product_count=("barcode", "count"),
                example_product_names=(
                    "product_name",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
                example_off_brands_raw=(
                    "off_brands_raw",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
            )
            .reset_index()
            .sort_values("product_count", ascending=False)
        )

    audit.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"  Brand alias cleanup audit -> "
        f"data/brand_mapping_review/brand_alias_cleanup_audit.csv "
        f"({len(audit):,} grouped rows)"
    )


def write_nestle_france_snacks_product_name_recovery_audit(df):
    """Write QA audit for the controlled Nestlé snacks name recovery."""
    os.makedirs(BRAND_MAPPING_REVIEW_DIR, exist_ok=True)
    output_path = os.path.join(
        BRAND_MAPPING_REVIEW_DIR,
        "nestle_france_snacks_product_name_recovery_audit.csv",
    )
    summary_path = os.path.join(
        BRAND_MAPPING_REVIEW_DIR,
        "nestle_france_snacks_product_name_recovery_summary.csv",
    )

    recovery_sources = set(NESTLE_PRODUCT_NAME_RECOVERY_SOURCES.values())
    recovered = df[df["brand_entity_source"].isin(recovery_sources)].copy()

    if recovered.empty:
        audit = pd.DataFrame(columns=[
            "product_name",
            "off_brands_raw",
            "old_normalized_brand",
            "new_normalized_brand",
            "brand_entity_source",
            "parent_company",
            "query_category",
            "primary_country",
            "observed_market_region_codes",
        ])
        summary = pd.DataFrame(columns=[
            "recovered_brand",
            "product_count",
            "example_product_names",
        ])
    else:
        audit = recovered.assign(
            old_normalized_brand=recovered[
                "brand_entity_raw_before_product_name_recovery"
            ],
            new_normalized_brand=recovered["normalized_brand"],
            parent_company="Nestlé",
        )[[
            "product_name",
            "off_brands_raw",
            "old_normalized_brand",
            "new_normalized_brand",
            "brand_entity_source",
            "parent_company",
            "query_category",
            "primary_country",
            "observed_market_region_codes",
        ]].sort_values(["new_normalized_brand", "product_name"])

        summary = (
            recovered.groupby("normalized_brand", dropna=False)
            .agg(
                product_count=("barcode", "count"),
                example_product_names=(
                    "product_name",
                    lambda s: " | ".join(
                        [
                            x for x in s.dropna().astype(str).head(5)
                            if x and x.lower() != "nan"
                        ]
                    ),
                ),
            )
            .reset_index()
            .rename(columns={"normalized_brand": "recovered_brand"})
            .sort_values("product_count", ascending=False)
        )

    audit.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(
        f"  Nestlé France snacks recovery audit -> "
        f"data/brand_mapping_review/nestle_france_snacks_product_name_recovery_audit.csv "
        f"({len(audit):,} rows)"
    )
    if not summary.empty:
        print("  Nestlé France snacks recovery summary:")
        for _, row in summary.iterrows():
            print(f"    {row['recovered_brand']}: {int(row['product_count'])}")


# -- Run ----------------------------------------------------------------------

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar - clean.py")
    print(f"Run timestamp: {timestamp}")

    input_path = find_latest_sample(SAMPLE_DIR)
    df = clean(input_path)

    # Summary
    print(f"\n  -- Summary --------------------------------------------------")
    print(f"  Rows:    {len(df)}")
    print(f"  Columns: {len(df.columns)}")

    print(f"\n  Nulls in nutritional columns (after capping):")
    for col in NUTRIMENT_COLS:
        n   = df[col].isnull().sum()
        pct = (n / len(df)) * 100
        print(f"    {col:<25} {n:>3} missing ({pct:.0f}%)")

    print(f"\n  Language distribution:")
    print("  " + df["ingredients_lang"].value_counts().to_string()
          .replace("\n", "\n  "))

    print(f"\n  Nutriscore distribution:")
    print("  " + df["nutriscore_grade"].value_counts().to_string()
          .replace("\n", "\n  "))

    print(f"\n  Completeness score:")
    print("  " + df["completeness_score"].describe().round(1).to_string()
          .replace("\n", "\n  "))

    # Save FIRST — previously the MemoryError on the low-completeness print
    # crashed clean.py before the file was ever written, so aliases were lost.
    output_filename = f"clean_{timestamp}.csv"
    output_path     = os.path.join(SAMPLE_DIR, output_filename)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n  Saved -> {output_filename}")
    print(f"  ({len(df)} rows, {len(df.columns)} columns)\n")
    write_brand_entity_extraction_review(df)
    write_brand_alias_normalization_review(df)
    write_brand_alias_cleanup_audit(df)
    write_nestle_france_snacks_product_name_recovery_audit(df)

    print(f"\n  Product records with low data completeness (score < 50):")
    low = df[df["completeness_score"] < 50][
        ["product_name", "brands", "completeness_score"]
    ]
    if len(low):
        # Cap at 20 rows — printing thousands of rows causes MemoryError
        print("  " + low.head(20).to_string().replace("\n", "\n  "))
        if len(low) > 20:
            print(f"  ... and {len(low) - 20:,} more (showing first 20 only)")
    else:
        print("  None - all records score >= 50")


if __name__ == "__main__":
    main()
