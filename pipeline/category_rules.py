"""
Shared Open Food Facts category assignment rules.

Both bootstrap.py (bulk export) and ingest.py (incremental API pull) must use
the same rules. Otherwise a clean bulk refresh can be contaminated again by a
later incremental run.
"""

from __future__ import annotations

import re

# Countries to include — matched against the countries_tags field.
# OFF crowdsources country tags from contributors, not from barcode prefixes.
# A product gets tagged with a country when a contributor in that country
# enters it. This is the correct signal for "sold in this market."
TARGET_COUNTRIES = {"en:france", "en:united-kingdom", "en:united-states"}

# Category priority mapping: first match wins.
# Dairies checked first because dairy products often also appear in snacks/
# beverages and we want the most specific classification. For MVP, all
# milk-related products stay in dairies even when they are snack-sized or
# snack-occasion products; a future snacking-occasion lens can add secondary
# assignment without weakening the primary dairy base.
CATEGORY_MAP = [
    ("dairies",   ["en:dairies", "en:dairy-products",
                   "en:fermented-milk-products", "en:dairy"]),
    ("cereals",   ["en:cereals-and-their-products",
                   "en:breakfast-cereals", "en:cereals"]),
    ("snacks",    ["en:snacks", "en:sweet-snacks", "en:salty-snacks"]),
    ("beverages", ["en:beverages", "en:drinks", "en:plant-based-beverages"]),
]

# Tags that confirm a product is a genuine snack chip — checked first, before
# snack exclusions.
_PROTECT_AS_SNACKS = {
    "en:tortilla-chips", "en:corn-chips", "en:crisps",
    "en:chips-and-crackers",
}

# Tags that route products to snacks even when they also inherit broad cereal
# parent tags. Cereal bars / snack bars are snacks in the project definition,
# not breakfast cereals.
_ROUTE_TO_SNACKS = {
    "en:bars", "en:cereal-bars", "en:chocolate-cereal-bars",
    "en:nut-cereal-bars", "en:fruit-cereal-bars", "en:protein-bars",
    "en:energy-bars", "en:snack-bars", "en:granola-bars",
    "en:muesli-bars", "en:nut-bars", "en:fruit-bars",
}

_SNACK_BAR_NAME_RE = re.compile(
    r"\b(bars|barre|barres|cereal\s+bars?|granola\s+bars?|"
    r"muesli\s+bars?|protein\s+bars?|energy\s+bars?|snack\s+bars?|"
    r"fruit\s+bars?|nut\s+bars?|oat\s+bars?|oaty\s+bars?|"
    r"rice\s+bars?|seed\s+bars?|chewy\s+bars?|breakfast\s+bars?|"
    r"flapjacks?|treat\s+bars?)\b",
    re.IGNORECASE,
)

_BREAKFAST_CEREAL_NAME_RE = re.compile(
    r"\b(muesli|granola|corn\s*flakes?|cornflakes?|flocons?|flakes?|"
    r"porridge|oats?|avoine|choco\s*balls?|cereal\s+clusters?|"
    r"cereales?|petales?)\b",
    re.IGNORECASE,
)

# Tags that exclude a product from snacks even when en:snacks is present.
# Covers pasta, noodles, plain tortillas/wraps, and identifiable pizza products.
# Keep this conservative: many bread/flour/tortilla terms are legitimate snacks
# (gingerbread, shortbread, tortilla chips, breadstick snack packs).
_EXCLUDE_FROM_SNACKS = {
    # Pasta
    "en:gnocchi", "en:potato-gnocchi", "en:cooked-gnocchis",
    "en:tortellini", "en:tortellini-ricotta-spinach",
    "en:ravioli", "en:cheese-ravioli", "en:fresh-ravioli",
    "en:ravioli-with-vegetables",
    "en:pastas", "en:fresh-pasta",
    # Noodles
    "en:noodles", "en:instant-noodles", "en:dried-noodles",
    "en:rice-noodles", "en:dried-rice-noodles",
    # Tortillas (not chips — protected above)
    "en:tortillas", "en:flour-tortillas", "en:corn-tortillas",
    # Pizza
    "en:pizzas", "en:frozen-pizzas", "en:frozen-pizzas-and-pies",
    "en:mini-appetizer-pizzas", "en:pizza-with-ham-and-cheese",
    "en:vegetable-pizza",
}

# Tags that exclude a product from cereals even when
# en:cereals-and-their-products is present. That OFF tag is a broad parent
# category covering far more than breakfast cereal: OFF's categories_tags field
# carries a product's full ancestor chain, so pasta/bread inherit it too.
#
# Scope: "cereal" = what a CPG manufacturer would put in a cereal aisle:
# muesli, granola, cooking oats, corn flakes, sugary breakfast cereals, etc.
# Cereal bars are excluded from this definition too (they belong in snacks) but
# that overlap is not addressed by this rule.
_EXCLUDE_FROM_CEREALS = {
    # Bread
    "en:breads", "en:flatbreads", "en:wraps",
    "en:tortillas", "en:flour-tortillas", "en:corn-tortillas",
    "en:rusks", "en:breadsticks",
    # Flour and semolina (ingredients or pasta-making wheat products, not breakfast cereal)
    "en:flours", "en:common-wheat-flours",
    "en:cereal-semolinas",
    # Pasta / stuffed pasta / noodles
    "en:cereal-pastas", "en:pastas", "en:fresh-pasta",
    "en:gnocchi", "en:potato-gnocchi", "en:cooked-gnocchis",
    "en:tortellini", "en:tortellini-ricotta-spinach",
    "en:ravioli", "en:cheese-ravioli", "en:fresh-ravioli",
    "en:ravioli-with-vegetables",
    "en:noodles", "en:instant-noodles", "en:dried-noodles",
    "en:rice-noodles", "en:dried-rice-noodles",
    # Rice
    "en:rices", "en:precooked-rices",
    # Dough / pastry
    "en:pie-dough", "en:puff-pastry",
    "en:puff-pastry-molds-for-vol-au-vent", "en:brick-sheets",
    # Batter mixes
    "en:dosa-batter-mixes", "en:idly-batter-mixes", "en:pancake-mixes",
    # Canned goods (canned corn and similar)
    "en:canned-cereals",
    # Belongs in beverages — deferred reclassification, excluded for now
    "en:cereal-based-drinks",
    # Other grain-derived, non-breakfast-cereal products
    "en:seitan", "en:rice-paper", "en:groats",
}


def assign_category(cats_val, product_name: str | None = None) -> str | None:
    """Return the first matching project query_category, or None to exclude."""
    if isinstance(cats_val, list):
        tags = "|".join(str(v) for v in cats_val).lower()
    elif isinstance(cats_val, str):
        tags = cats_val.lower()
    else:
        return None

    if not tags:
        return None

    dairy_tags = CATEGORY_MAP[0][1]
    if any(t in tags for t in dairy_tags):
        return "dairies"

    if any(t in tags for t in _ROUTE_TO_SNACKS):
        name = str(product_name or "")
        if _SNACK_BAR_NAME_RE.search(name):
            return "snacks"
        if name and _BREAKFAST_CEREAL_NAME_RE.search(name):
            pass
        elif any(t in tags for t in {"en:protein-bars", "en:energy-bars", "en:snack-bars"}):
            return "snacks"

    for label, match_tags in CATEGORY_MAP[1:]:
        if any(t in tags for t in match_tags):
            if label == "snacks":
                if any(p in tags for p in _PROTECT_AS_SNACKS):
                    return "snacks"
                if any(ex in tags for ex in _EXCLUDE_FROM_SNACKS):
                    return None
            if label == "cereals":
                if any(ex in tags for ex in _EXCLUDE_FROM_CEREALS):
                    return None
            return label
    return None


def matches_country(countries_val) -> bool:
    """True if any target country tag appears in the product's countries_tags."""
    if isinstance(countries_val, list):
        tags = "|".join(str(v) for v in countries_val).lower()
    elif isinstance(countries_val, str):
        tags = countries_val.lower()
    else:
        return False

    if not tags:
        return False
    return any(c in tags for c in TARGET_COUNTRIES)
