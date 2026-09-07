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
    r"\b(muesli|granola|corn\s*flakes?|cornflakes?|bran\s*flakes?|"
    r"wheat\s*flakes?|flocons?|flakes?|frosties|porridge|oats?|"
    r"oatmeal|avoine|choco\s*balls?|coco\s*pops|rice\s*krispies|"
    r"cereal\s+clusters?|clusters?|cereals?|cereales?|petales?|"
    r"loops?|hoops?|pillows?|puffs?|weetabix|shredded\s*wheat|"
    r"wheat\s+biscuits?|cinnamon\s+chips?|cereal\s+chips?)\b",
    re.IGNORECASE,
)

_SNACK_POSITIVE_NAME_RE = re.compile(
    r"\b(chocolate|candy|candies|sweets?|gumm(?:y|ies)|jell(?:y|ies)|"
    r"licori[cs]e|marshmallows?|nougat|caramels?|toffees?|lollipops?|"
    r"chewing\s+gum|ice\s*cream|sorbets?|crisps|chips?|crackers?|"
    r"baked\s+snack\s+crackers?|sticks?|pretzels?|popcorn|rice\s+cakes?|"
    r"pork\s+scratchings?|crackling|jerky|snack\s+pot|snacks?|snacking|"
    r"ap[eé]ro|apero|party\s+snacks?|biscuits?|cookies?|wafers?|"
    r"shortbread|croissants?|panettone|pandoro|belgian\s+buns?|churros?|"
    r"profiteroles?|choux\s+buns?|madeleines?|brownies?|muffins?|"
    r"fruit\s+rolls?|fruit\s+strips?)\b",
    re.IGNORECASE,
)

_SNACK_EXCLUDE_NAME_RE = re.compile(
    r"\b(macaron[ia]|pasta|lasagne|ravioli|gnocchi|tagliatelle|penne|"
    r"noodles?|dumplings?|gyoza|shumai|dim\s*sum|bao|banh\s+bao|"
    r"sausage\s+rolls?|pork\s+pies?|scotch\s+eggs?|quiches?|"
    r"sandwich(?:es)?|wraps?|baguette\s+sandwich|pain\s+surprise|"
    r"coleslaw|salads?|meal\s+kits?|lunch\s+kits?|lunch\s+kitz|"
    r"dinner\s+kits?|"
    r"onigiri|pakora|samosas?|matzo\s+ball|soup\s+mix|cooking\s+mix|"
    r"bread|buns?|rolls?|garlic\s+bread|pizza|dips?|sauces?|"
    r"dressings?|spreads?|toppings?|seasonings?|prepared\s+meals?)\b",
    re.IGNORECASE,
)

_CEREAL_ROUTE_TO_SNACKS_NAME_RE = re.compile(
    r"\b(cereal\s+bars?|granola\s+bars?|snack\s+bars?|protein\s+bars?|"
    r"energy\s+bars?|fruit\s+(?:and\s+)?nut\s+bars?|nut\s+bars?|"
    r"fruit\s+bars?|muesli\s+bars?|breakfast\s+bars?|flapjacks?|"
    r"rice\s+cakes?|crackers?|crisps|bagged\s+chips?|potato\s+skins?|"
    r"breakfast\s+cookies?|muesli\s+breakfast\s+bounties|"
    r"snack\s+bites?|fruit\s+and\s+nut\s+bites?)\b",
    re.IGNORECASE,
)

_CEREAL_EXCLUDE_NAME_RE = re.compile(
    r"\b(spaghetti|pastas?|gnocchi|tortellini|ravioli|noodles?|bread|"
    r"buns?|brioche|rolls?|rusks?|crisp\s+toasts?|toastie|sandwich|"
    r"sesame\s+oil|potatoes?|pommes?\s+de\s+terre|frozen\s+chips?|"
    r"crinkle\s+cut\s+chips?|fries|frites|wedges?|hash\s+browns?|"
    r"mashed\s+potatoes?|mash|tater\s+tots?|rice|couscous|polenta|"
    r"flours?|semolina|starch|pancake\s+mix|waffle\s+mix|cake\s+mix|"
    r"pancakes?|waffles?|pizza|wraps?|tortillas?|galettes?|crepes?|"
    r"prepared\s+meals?|bowls?|salads?|soups?|sauces?|toppings?|"
    r"tahini|beans?|pork\s+panko|breakfast\s+hash)\b",
    re.IGNORECASE,
)

_CEREAL_FORMAT_OVERRIDE_NAME_RE = re.compile(
    r"\b(cereal|granola|muesli|oatmeal|porridge|corn\s*flakes?|"
    r"bran\s*flakes?|wheat\s*flakes?|coco\s*pops|rice\s*krispies|"
    r"frosties|weetabix|shredded\s*wheat)\b",
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
    # Dumplings / buns / prepared foods
    "en:gyoza", "en:dumplings", "en:shumai", "en:bao-buns",
    "en:sausage-rolls", "en:pork-pies", "en:scotch-eggs",
    "en:sandwiches", "en:wraps", "en:salads", "en:meal-kits",
    "en:prepared-meals", "en:cooking-mixes", "en:soup-mixes",
    "en:breads", "en:dips", "en:sauces", "en:toppings",
    "en:prepared-salads", "en:coleslaw",
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
    "en:rices", "en:precooked-rices", "en:couscous", "en:polenta",
    # Dough / pastry
    "en:pie-dough", "en:puff-pastry",
    "en:puff-pastry-molds-for-vol-au-vent", "en:brick-sheets",
    # Batter mixes
    "en:dosa-batter-mixes", "en:idly-batter-mixes", "en:pancake-mixes",
    "en:waffle-mixes", "en:cake-mixes",
    # Canned goods (canned corn and similar)
    "en:canned-cereals",
    # Belongs in beverages — deferred reclassification, excluded for now
    "en:cereal-based-drinks",
    # Other grain-derived, non-breakfast-cereal products
    "en:seitan", "en:rice-paper", "en:groats",
    # Potatoes / meal sides
    "en:potatoes", "en:sweet-potatoes", "en:frozen-chips",
    "en:hash-browns", "en:mashed-potatoes",
    # Prepared / sauce / topping / ingredient noise
    "en:pancakes", "en:waffles", "en:pizzas", "en:salads",
    "en:sauces", "en:toppings", "en:tahini", "en:oils",
    "en:prepared-meals", "en:sandwiches", "en:breadcrumbs",
}

_SNACK_CANDIDATE_TAGS = {
    "en:snacks", "en:sweet-snacks", "en:salty-snacks",
}

_CEREAL_CANDIDATE_TAGS = {
    "en:cereals-and-their-products", "en:breakfast-cereals", "en:cereals",
}

_BEVERAGE_TAGS = {"en:beverages", "en:drinks", "en:plant-based-beverages"}

_SNACK_POSITIVE_TAGS = {
    "en:chocolates", "en:candies", "en:gummies", "en:licorice",
    "en:toffees", "en:ice-creams", "en:sorbets", "en:frozen-desserts",
    "en:tortilla-chips", "en:corn-chips", "en:crisps",
    "en:chips-and-crackers", "en:crackers", "en:popcorn",
    "en:rice-cakes", "en:pork-scratchings", "en:jerky",
    "en:biscuits", "en:cookies", "en:viennoiseries", "en:panettone",
    "en:pandoro", "en:pastries",
}

_CEREAL_ROUTE_TO_SNACKS_TAGS = _ROUTE_TO_SNACKS | {
    "en:rice-cakes", "en:crackers", "en:crisps", "en:chips-and-crackers",
    "en:biscuits", "en:cookies",
}

_CEREAL_POSITIVE_TAGS = {
    "en:breakfast-cereals", "en:mueslis", "en:granolas", "en:oatmeal",
}


def _normalise_tags(cats_val) -> set[str]:
    if isinstance(cats_val, list):
        raw = "|".join(str(v) for v in cats_val)
    elif isinstance(cats_val, str):
        raw = cats_val
    else:
        return set()
    return {tag.strip().lower() for tag in re.split(r"[,|]", raw) if tag.strip()}


def _has_any(tagset: set[str], values: set[str]) -> bool:
    return bool(tagset & values)


def _is_snack_positive(tagset: set[str], name: str) -> bool:
    return _has_any(tagset, _SNACK_POSITIVE_TAGS | _PROTECT_AS_SNACKS | _ROUTE_TO_SNACKS) or bool(
        _SNACK_POSITIVE_NAME_RE.search(name) or _SNACK_BAR_NAME_RE.search(name)
    )


def _is_not_snack(tagset: set[str], name: str) -> bool:
    return _has_any(tagset, _EXCLUDE_FROM_SNACKS) or bool(_SNACK_EXCLUDE_NAME_RE.search(name))


def _assign_snack(tagset: set[str], name: str) -> str | None:
    # Specific snack formats win over meal-like flavour words only when the
    # snack format is explicit.
    if re.search(r"\b(lunch\s+kit[sz]?|dinner\s+kits?|coleslaw|salad\s+kit)\b", name, re.IGNORECASE):
        return None
    if _is_not_snack(tagset, name) and not re.search(
        r"\b(candy|candies|chips?|crisps|crackers?|snack\s+pot|"
        r"snack\s+crackers?|baked\s+snack\s+crackers?|ap[eé]ro|apero|"
        r"biscuits?|cookies?|wafers?|belgian\s+buns?|croissants?|"
        r"panettone|pandoro|churros?|profiteroles?|choux\s+buns?)\b",
        name,
        re.IGNORECASE,
    ):
        return None
    if _is_snack_positive(tagset, name):
        return "snacks"
    if _is_not_snack(tagset, name):
        return None
    return None


def _is_cereal_route_to_snacks(tagset: set[str], name: str) -> bool:
    if re.search(r"\bcliff?\b", name, re.IGNORECASE):
        return True
    if re.search(r"\b(crisp\s+toasts?|dry\s+bread|toastie|sandwich)\b", name, re.IGNORECASE):
        return False
    if _has_any(tagset, _CEREAL_ROUTE_TO_SNACKS_TAGS):
        if re.search(r"\b(frozen|crinkle\s+cut|wedges?|hash\s+browns?|mashed|mash)\b", name, re.IGNORECASE):
            return False
        return True
    if _CEREAL_ROUTE_TO_SNACKS_NAME_RE.search(name):
        return True
    if re.search(r"\bwalkers\s+french\s+fries\b", name, re.IGNORECASE):
        return True
    return False


def _is_cereal_positive(tagset: set[str], name: str) -> bool:
    return _has_any(tagset, _CEREAL_POSITIVE_TAGS) or bool(_BREAKFAST_CEREAL_NAME_RE.search(name))


def _is_not_cereal(tagset: set[str], name: str) -> bool:
    return _has_any(tagset, _EXCLUDE_FROM_CEREALS) or bool(_CEREAL_EXCLUDE_NAME_RE.search(name))


def _assign_cereal(tagset: set[str], name: str) -> str | None:
    if _is_cereal_route_to_snacks(tagset, name):
        return "snacks"
    if _is_not_cereal(tagset, name) and not _CEREAL_FORMAT_OVERRIDE_NAME_RE.search(name):
        return None
    if _is_cereal_positive(tagset, name):
        return "cereals"
    if _is_not_cereal(tagset, name):
        return None
    return None


def assign_category(cats_val, product_name: str | None = None) -> str | None:
    """Return the first matching project query_category, or None to exclude."""
    tagset = _normalise_tags(cats_val)
    if not tagset:
        return None

    name = str(product_name or "")

    dairy_tags = CATEGORY_MAP[0][1]
    if _has_any(tagset, set(dairy_tags)):
        return "dairies"

    cereal_candidate = _has_any(tagset, _CEREAL_CANDIDATE_TAGS)
    snack_candidate = _has_any(tagset, _SNACK_CANDIDATE_TAGS)

    # Cereal route-to-snacks decisions must happen before generic cereal keep.
    if cereal_candidate and _is_cereal_route_to_snacks(tagset, name):
        return "snacks"

    if snack_candidate:
        snack_result = _assign_snack(tagset, name)
        if snack_result is not None:
            return snack_result
        if _is_not_snack(tagset, name):
            return None

    if cereal_candidate:
        return _assign_cereal(tagset, name)

    if _has_any(tagset, _BEVERAGE_TAGS):
        return "beverages"

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
