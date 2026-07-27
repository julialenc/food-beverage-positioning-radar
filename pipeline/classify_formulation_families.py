"""
Rule-based formulation family classifier for sampling.

Purpose: prevent one dominant subtype from consuming a whole region-category
quota. NOT a final analytical segmentation — just enough structure to ensure
the sample covers different formulation types, e.g. that 2,450 dairy products
don't become 1,900 cheeses.

Design choice: rule-based, NOT KMeans. Real clustering deferred to a
post-run analytical step once 21,000 products have LLM-extracted claims
and full nutritional data. KMeans on sparse ingredient data would require
too many methodological decisions (normalization, cluster stability,
cross-region comparability) to trust as a sampling-only mechanism. See
llm_sampling_design_log.md for the reasoning.

IMPORTANT DISTINCTION FROM POSITIONING DETECTOR:
This script can use off_categories for sub-type detection. The contamination
issue in detect_positioning_signals.py was specific to pack COMMUNICATION
proxies — OFF's "Plant-based foods and beverages" ancestry was being used
as if it meant a deliberate claim. Here we're asking "what structural TYPE
of product is this" (cheese vs. yogurt vs. milk drink), and OFF's
sub-category tags (en:yogurts, en:cheeses, en:corn-flakes) are reliable
structural indicators, not inferred claims. Different purpose, different
trust level.

Families are MUTUALLY EXCLUSIVE per product (first-match-wins priority
order). Every product that matches no family gets "other_<category>".
The classifier records which rule matched (family_source) for audit.

Usage: python pipeline/classify_formulation_families.py
Writes: pipeline/formulation_families.csv
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT_CSV = Path(__file__).resolve().parent / "formulation_families.csv"

RULE_VERSION = "family-v1"

# ── Word-boundary matcher (same pattern as positioning detector) ────────────
_WB_CACHE: dict[str, re.Pattern] = {}

def _wb(term: str) -> re.Pattern:
    if term not in _WB_CACHE:
        _WB_CACHE[term] = re.compile(r"\b" + re.escape(term) + r"\b")
    return _WB_CACHE[term]

def _any_match(haystack: str, terms: list[str]) -> bool:
    return any(_wb(t).search(haystack) for t in terms)

def _any_in(text: str, substrings: list[str]) -> bool:
    return any(s in text for s in substrings)


# ── Category-specific family rules ─────────────────────────────────────────
# Each entry: (family_label, source_label, off_tag_matches, name_term_matches)
# off_tag_matches: substrings checked against LOWER(off_categories) — case
#   insensitive, substring (OFF tag structure makes this reliable for specific
#   sub-category tags like "en:yogurt", "en:cheese" etc.)
# name_term_matches: word-boundary terms checked against LOWER(product_name)
# First match wins -> mutually exclusive.

_DAIRY_RULES = [
    # Plant-based alternatives FIRST
    ("plant_based_dairy_alt",
     ["plant-based dairy", "non-dairy", "dairy-free", "dairy free",
      "oat drink", "soy drink", "almond drink", "rice drink",
      "plant-based beverages", "plant-based milk", "boissons végétales",
      "lait végétal", "boisson végétale", "boissons à base de végétaux"],
     ["oat drink", "oat milk", "almond drink", "almond milk", "soy drink",
      "soy milk", "soya milk", "coconut milk", "oat yogurt", "plant-based",
      "non-dairy", "dairy free", "dairy-free"]),
    # Ice cream & frozen BEFORE butter/cream
    ("ice_cream_frozen",
     ["ice creams", "gelatos", "frozen yogurt", "ice cream", "glaces",
      "crèmes glacées", "crème glacée", "sorbets", "ice lollies",
      "ice lolly"],
     ["ice cream", "gelato", "frozen yogurt", "sorbet", "ice lolly",
      "ice pop", "popsicle"]),
    # Butter / cream / high-fat — bare "cream" excluded from name terms
    ("butter_cream_fat",
     ["butters", "beurres", "creams", "crèmes", "creme fraiche",
      "crème fraîche", "ghee", "sour cream", "clotted cream"],
     ["butter", "beurre", "ghee", "creme fraiche", "crème fraîche",
      "sour cream", "clotted cream", "double cream", "whipping cream",
      "single cream"]),
    # Cheese
    ("cheese",
     ["cheeses", "fromages", "camembert", "brie", "cheddar", "gouda",
      "mozzarella", "parmesan", "cottage cheese", "cream cheese", "feta",
      "ricotta", "gruyère", "gruyere", "emmental", "fromage"],
     ["cheese", "fromage", "cheddar", "brie", "camembert", "gouda",
      "mozzarella", "parmesan", "parmigiano", "feta", "ricotta",
      "cottage cheese", "cream cheese", "blue cheese", "gorgonzola",
      "halloumi", "gruyère"]),
    # Dairy desserts (non-frozen)
    ("dairy_dessert",
     ["dairy desserts", "desserts lactés", "rice puddings", "custards",
      "mousses", "panna cotta", "cheesecakes", "flans", "crèmes desserts",
      "crème dessert"],
     ["pudding", "custard", "mousse", "panna cotta", "rice pudding",
      "crème brûlée", "tiramisu", "posset", "flan"]),
    # Yogurt & fermented
    ("yogurt_fermented",
     ["yogurts", "yoghurts", "yaourts", "fermented milks", "laits fermentés",
      "skyr", "kefir", "fromage frais", "quark", "labneh"],
     ["yogurt", "yoghurt", "yaourt", "skyr", "kefir", "fromage frais",
      "fromage blanc", "quark", "labneh", "filmjölk"]),
    # Protein-focused dairy
    ("protein_functional_dairy",
     [],
     ["protein drink", "protein shake", "protein pudding", "high protein",
      "whey drink", "casein shake"]),
    # Milk & flavoured milk
    ("milk_drink",
     ["milks", "laits", "flavoured milks", "milk drinks", "condensed milk",
      "evaporated milk", "powdered milk", "boissons lactées", "lait"],
     ["milk", "lait", "milkshake", "chocolate milk", "flavoured milk",
      "hot chocolate", "cocoa"]),
]

_SNACKS_RULES = [
    # Meat snacks
    ("meat_snack",
     ["jerky", "meat snacks", "biltong", "pork scratchings", "pork rinds"],
     ["jerky", "biltong", "meat snack", "pork scratching", "pork rind",
      "beef stick", "pepperoni stick"]),
    # Nuts & seeds
    ("nut_seed",
     ["nuts", "seeds", "peanuts", "almonds", "cashews", "mixed nuts",
      "roasted nuts", "noix", "graines", "amandes", "noisettes", "arachides"],
     ["nuts", "almonds", "cashews", "walnuts", "pecans", "pistachios",
      "peanuts", "seeds", "sunflower seeds", "trail mix"]),
    # Fruit snacks
    ("fruit_snack",
     ["dried fruits", "fruit snacks", "fruit leathers", "fruits séchés",
      "fruits desséchés"],
     ["dried fruit", "fruit leather", "fruit strip", "fruit pouch"]),
    # Confectionery BEFORE bars AND before biscuits
    # Uses display-text substrings from the diagnostic
    ("confectionery",
     ["confectioneries", "confiseries", "chocolats", "cacao et dérivés",
      "cocoa and its products", "cocoa and its product", "chocolat",
      "bonbons", "candies", "sweets", "gummies", "lollipops", "caramels",
      "marshmallows", "confiseries chocolatées", "chocolats noirs",
      "dark chocolate", "milk chocolate"],
     ["chocolate", "candy", "sweets", "gummy", "gummies", "lollipop",
      "caramel", "marshmallow", "fudge", "toffee", "truffle"]),
    # Savoury snacks — display-text from diagnostic
    ("savoury_snack",
     ["chips and crisps", "chips and fries", "crisps", "popcorn", "pretzels",
      "rice cakes", "corn chips", "veggie chips", "puffed snacks",
      "snacks salés", "amuse-gueules", "salty snacks", "snacks sale"],
     ["crisps", "chips", "popcorn", "pretzel", "rice cake", "corn chip",
      "puff", "cracker", "flatbread", "breadstick", "tortilla chip"]),
    # Bars — after confectionery
    ("bar",
     ["cereal bars", "protein bars", "energy bars", "granola bars",
      "snack bars", "barres"],
     ["protein bar", "energy bar", "cereal bar", "granola bar",
      "snack bar", "oat bar", "nut bar", "fruit bar", "fibre bar"]),
    # Biscuits & cookies — broad, catches remaining sweet baked goods
    # incl. viennoiseries/pâtisseries for sampling purposes
    ("biscuit_cookie",
     ["biscuits and cakes", "biscuits et gâteaux", "biscuits", "cookies",
      "crackers", "wafers", "shortbread", "gâteaux", "cakes",
      "pâtisseries", "patisseries", "viennoiseries", "sweet snacks",
      "snacks sucrés", "biscuits and cake"],
     ["biscuit", "cookie", "cookies", "cracker", "wafer", "shortbread",
      "digestive", "rich tea", "brioche", "madeleine", "financier"]),
]

_CEREALS_RULES = [
    ("muesli_granola",
     ["muesli", "granola", "müsli"],
     ["muesli", "granola", "bircher", "müsli"]),
    ("oats_porridge",
     ["rolled oats", "oatmeal", "porridge", "instant oatmeal",
      "flocons d'avoine", "flocons d avoine", "avoine"],
     ["porridge", "oatmeal", "rolled oat", "steel cut oat",
      "instant oat", "oat flake", "oats", "flocons d'avoine"]),
    ("corn_flakes_puffed",
     ["corn flakes", "corn-flakes", "puffed cereals", "rice cereals",
      "flaked cereals", "céréales soufflées", "cereales soufflees",
      "riz soufflé", "maïs soufflé", "soufflé"],
     ["corn flake", "cornflake", "rice krispie", "puffed rice",
      "puffed wheat", "rice cereal", "soufflé"]),
    ("bran_wholegrain",
     ["bran cereals", "whole grain cereals", "wholegrain cereals",
      "céréales complètes", "cereales completes"],
     ["bran", "all-bran", "weetabix", "shredded wheat", "whole wheat"]),
    ("coated_sugary",
     ["coated cereals", "chocolate cereals", "frosted cereals",
      "sweetened cereals", "honey cereals", "céréales enrobées",
      "cereales chocolatees"],
     ["frosted", "honey smack", "frosties", "coco pops", "choco",
      "honey nut", "loops", "pops", "shapes"]),
    ("nutrition_fortified",
     ["fortified cereals"],
     ["special k", "belvita", "total cereal", "smart start"]),
]

_BEVERAGES_RULES = [
    # Alcoholic — added from diagnostic (wines + beers = ~15k unclassified)
    # FIRST so beer/wine don't fall into juice/soft-drink rules
    ("alcoholic",
     ["boissons alcoolisées", "alcoholic beverages", "vins", "bières",
      "wines", "beers", "spirits", "alcool", "bière", "vin ",
      "vins français", "vins rouges", "vins blancs", "champagnes",
      "cidres", "ciders", "whiskies", "vodkas", "gins", "rums",
      "liqueurs", "aperitifs", "apéritifs"],
     ["wine", "beer", "cider", "whisky", "whiskey", "vodka", "gin",
      "rum", "champagne", "prosecco", "liqueur", "aperitif", "apéritif",
      "porter", "stout", "lager", "ale", "mead"]),
    # Water
    ("water",
     ["waters", "eaux", "eau minérale", "spring waters", "sparkling waters",
      "mineral waters", "flavoured waters", "eau de source", "eau gazeuse",
      "eaux minérales"],
     ["spring water", "mineral water", "sparkling water",
      "flavoured water", "flavored water", "coconut water", "eau de coco"]),
    # Plant milks
    ("plant_milk_alt",
     ["plant milks", "oat drinks", "soy drinks", "almond drinks",
      "rice drinks", "plant-based beverages", "plant-based drinks",
      "boissons végétales", "boisson végétale", "boissons à base de végétaux",
      "lait d'avoine", "lait d'amande", "lait de soja"],
     ["oat drink", "oat milk", "almond drink", "almond milk",
      "soy drink", "soy milk", "rice milk", "cashew milk",
      "coconut drink"]),
    # Coffee & tea — add French display names from diagnostic
    ("coffee_tea",
     ["coffees", "teas", "herbal teas", "green teas", "black teas",
      "iced teas", "cold brew", "thés", "cafés", "infusions",
      "boissons chaudes", "hot drinks", "tisanes", "thé ", "café ",
      "boissons à base de thé", "boissons au café"],
     ["coffee", "espresso", "latte", "cappuccino", "tea", "matcha",
      "kombucha", "herbal tea", "cold brew", "infusion", "tisane"]),
    # Juice — add French from diagnostic
    ("juice",
     ["juices", "fruit juices", "vegetable juices", "smoothies", "nectars",
      "jus de fruits", "jus de légumes", "boissons aux fruits",
      "boissons fruitées", "nectars de fruits"],
     ["juice", "jus", "smoothie", "nectar", "pressed"]),
    # Energy & sports
    ("energy_sports",
     ["energy drinks", "sports drinks", "isotonic drinks",
      "boissons énergétiques", "boissons sportives"],
     ["energy drink", "sports drink", "isotonic", "electrolyte drink"]),
    # Protein & functional
    ("protein_functional_bev",
     ["protein drinks", "meal replacement drinks", "boissons protéinées"],
     ["protein drink", "protein shake", "meal replacement"]),
    # Dairy drinks
    ("dairy_drink",
     ["milk drinks", "milkshakes", "kefir drinks", "fermented milk drinks",
      "boissons lactées", "milk-based beverages"],
     ["milkshake", "milk drink", "flavoured milk", "kefir drink",
      "drinking yogurt", "lassi"]),
    # Soft drinks — add French from diagnostic
    ("soft_drink",
     ["sodas", "colas", "lemonades", "carbonated drinks", "soft drinks",
      "boissons avec sucre ajouté", "boissons sucrées", "boissons gazeuses",
      "limonades", "boissons rafraîchissantes"],
     ["cola", "soda", "lemonade", "lemon-lime", "tonic", "ginger ale",
      "ginger beer", "fizzy"]),
]

# Assembled registry
_RULES: dict[str, list] = {
    "dairy":     _DAIRY_RULES,
    "snacks":    _SNACKS_RULES,
    "cereals":   _CEREALS_RULES,
    "beverages": _BEVERAGES_RULES,
}


def classify_product(category: str, product_name: str,
                     off_categories: str) -> tuple[str, str]:
    """Return (family_label, family_source). First-match-wins."""
    rules = _RULES.get(category.lower())
    if not rules:
        return f"other_{category}", "no_rules_for_category"

    name_low = str(product_name or "").lower()
    cats_low = str(off_categories or "").lower()

    for family, off_tag_patterns, name_terms in rules:
        if off_tag_patterns and _any_in(cats_low, off_tag_patterns):
            return family, "off_categories"
        if name_terms and _any_match(name_low, name_terms):
            return family, "product_name"

    return f"other_{category}", "no_match"


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    df = pd.read_sql_query("""
        SELECT barcode, product_name, query_category AS category, off_categories
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
          AND query_category IN ('dairy', 'snacks', 'cereals', 'beverages')
    """, conn)
    conn.close()

    families, sources = zip(*[
        classify_product(row["category"], row["product_name"], row["off_categories"])
        for _, row in df.iterrows()
    ])
    df["formulation_family"] = families
    df["family_source"] = sources
    df["family_rule_version"] = RULE_VERSION
    # Ensure barcode stays as string in the CSV — pandas otherwise infers
    # numeric type on read, causing barcode mismatches on downstream merges.
    df["barcode"] = df["barcode"].astype(str)

    df[["barcode", "category", "formulation_family", "family_source",
        "family_rule_version"]].to_csv(OUT_CSV, index=False)
    print(f"Classified {len(df):,} products.\nWrote {OUT_CSV}\n")

    # Audit: family distribution per category
    print("Family distribution per category:")
    for cat in ["dairy", "snacks", "cereals", "beverages"]:
        sub = df[df["category"] == cat]
        if len(sub) == 0:
            continue
        print(f"\n  {cat.upper()} ({len(sub):,} products)")
        counts = sub["formulation_family"].value_counts()
        for fam, n in counts.items():
            pct = n / len(sub) * 100
            print(f"    {fam:<30} {n:>7,}  ({pct:5.1f}%)")
        print(f"    -- family_source breakdown --")
        print("   ", sub["family_source"].value_counts().to_dict())

    # Flag other_X dominance — if "other" > 30% in any category, the rules
    # are too sparse and need widening before sampling.
    print("\nCoverage alert (other_* share — flag if > 30%):")
    for cat in ["dairy", "snacks", "cereals", "beverages"]:
        sub = df[df["category"] == cat]
        if len(sub) == 0:
            continue
        other_share = sub["formulation_family"].str.startswith("other_").mean()
        flag = "  *** NEEDS ATTENTION ***" if other_share > 0.30 else ""
        print(f"  {cat:<12} other: {other_share:.1%}{flag}")


if __name__ == "__main__":
    main()
