"""
analyze.py
----------
Option A — rule-based ingredient marker analysis.
Computes the composition_marker_score from ingredient text and additives,
independent of any front-of-pack claim. See docs/ADR.md ADR-004 and
ADR-010 for the full architectural rationale.

Architecture:
    composition_marker_score (Component A, this file) is combined with
    front-of-pack claim weight and processing/nutrition context
    (Components B and C, from vision_extract.py) in merge_scores.py to
    produce positioning_composition_gap. See docs/METHODOLOGY.md.

    Claim-signal fields are detected and stored here from ingredient
    text and product name — they support benchmark intersection
    detection and Power BI filtering, but do not feed into
    composition_marker_score itself. Front-of-pack claims are extracted
    separately via vision_extract.py and are a different evidence layer
    (see docs/OBSERVATIONS.md OBS-016).

    The four benchmark intersection pattern flags below are based on
    ingredient/name-derived signals and nutrition values only. They are
    useful for broad filtering and early pattern detection, but they
    are not substitutes for pack-image claim extraction — see
    docs/METHODOLOGY.md for how this differs from claim_benchmark_intersections.

Usage:
    python pipeline/analyze.py

Input:
    data/sample/clean_<timestamp>.csv   (latest file auto-detected)
    OR data/sample/bulk_clean_<timestamp>.csv

Output:
    data/sample/analyzed_<timestamp>.csv
"""

import pandas as pd
import os
import re
from datetime import datetime
from collections import Counter

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")


# ── Dictionary scope ──────────────────────────────────────────────────────────
# These marker lists are intentionally not exhaustive. They reflect the
# current project scope, observed OFF records, OCR validation, and domain
# review. New markers should be added through validation on real product
# examples and documented in docs/OBSERVATIONS.md or docs/METHODOLOGY.md.


# ── Ingredient composition markers ───────────────────────────────────────────
# These feed Component A only — the ingredient composition signal.
# Do NOT add claim language here. Claims are captured separately via
# front-of-pack vision extraction (see vision_extract.py).
# See docs/ADR.md ADR-010.

ULTRA_PROCESSED_MARKERS = [
    # Artificial sweeteners
    ("aspartame",              "artificial_sweetener", 3),
    ("acesulfame",             "artificial_sweetener", 3),
    ("saccharin",              "artificial_sweetener", 3),
    ("sucralose",              "artificial_sweetener", 3),
    ("cyclamate",              "artificial_sweetener", 3),
    ("stevia",                 "sweetener_natural",    1),
    ("steviol",                "sweetener_natural",    1),
    ("maltitol",               "polyol_sweetener",     2),
    ("sorbitol",               "polyol_sweetener",     2),
    ("xylitol",                "polyol_sweetener",     2),
    ("erythritol",             "polyol_sweetener",     1),
    # Emulsifiers
    ("lecithin",               "emulsifier",           1),
    ("lecithine",              "emulsifier",           1),
    ("mono- and diglycerides", "emulsifier",           2),
    ("monoglycerides",         "emulsifier",           2),
    ("diglycerides",           "emulsifier",           2),
    ("carrageenan",            "high_severity_emulsifier", 3),
    ("carraghenane",           "high_severity_emulsifier", 3),
    ("xanthan",                "thickener",            2),
    ("xanthane",               "thickener",            2),
    ("guar",                   "thickener",            1),
    ("carboxymethyl",          "thickener",            2),
    ("pectin",                 "thickener",            1),
    ("pectine",                "thickener",            1),
    # Preservatives
    ("sodium benzoate",        "preservative",         2),
    ("benzoate de sodium",     "preservative",         2),
    ("potassium sorbate",      "preservative",         2),
    ("sorbate de potassium",   "preservative",         2),
    ("sodium nitrite",         "preservative",         3),
    ("nitrite de sodium",      "preservative",         3),
    ("bha",                    "preservative",         3),
    ("bht",                    "preservative",         3),
    ("tbhq",                   "preservative",         3),
    # Flavourings
    ("artificial flavour",     "artificial_flavour",   3),
    ("artificial flavor",      "artificial_flavour",   3),
    ("natural flavour",        "added_flavour",        2),
    ("natural flavor",         "added_flavour",        2),
    ("arome naturel",          "added_flavour",        2),
    ("arome artificiel",       "artificial_flavour",   3),
    ("arome",                  "added_flavour",        1),
    ("flavouring",             "added_flavour",        1),
    ("flavoring",              "added_flavour",        1),
    # Glucose syrups and refined sugars
    ("glucose syrup",          "glucose_syrup",        3),
    ("sirop de glucose",       "glucose_syrup",        3),
    ("high fructose",          "glucose_syrup",        3),
    ("corn syrup",             "glucose_syrup",        3),
    ("dextrose",               "refined_sugar",        2),
    ("maltodextrin",           "maltodextrin",         3),
    ("maltodextrine",          "maltodextrin",         3),
    # Refined starches
    ("modified starch",        "modified_starch",      2),
    ("amidon modifie",         "modified_starch",      2),
    ("amidon",                 "starch",               1),
    ("starch",                 "starch",               1),
    # Industrial fats
    ("palm oil",               "palm_oil",             2),
    ("huile de palme",         "palm_oil",             2),
    ("partially hydrogenated", "trans_fat",            3),
    ("interesterified",        "industrial_fat",       2),
    # Raising agents
    ("sodium carbonate",       "raising_agent",        1),
    ("carbonate de sodium",    "raising_agent",        1),
    ("ammonium carbonate",     "raising_agent",        1),
    ("sodium bicarbonate",     "raising_agent",        1),
    ("bicarbonate de sodium",  "raising_agent",        1),
    # Colours
    ("caramel colour",         "artificial_colour",    2),
    ("caramel color",          "artificial_colour",    2),
    ("tartrazine",             "artificial_colour",    3),
    ("sunset yellow",          "artificial_colour",    3),
    ("brilliant blue",         "artificial_colour",    3),
    ("allura red",             "artificial_colour",    3),
    ("colorant",               "colour",               1),
    # Acid regulators
    ("phosphoric acid",        "acid_regulator",       2),
    ("acide phosphorique",     "acid_regulator",       2),
    ("citric acid",            "acid_regulator",       1),
    ("acide citrique",         "acid_regulator",       1),
]

# ── E-number markers ──────────────────────────────────────────────────────────

E_NUMBER_MARKERS = [
    ("e950",  "artificial_sweetener", 3),
    ("e951",  "artificial_sweetener", 3),
    ("e952",  "artificial_sweetener", 3),
    ("e954",  "artificial_sweetener", 3),
    ("e955",  "artificial_sweetener", 3),
    ("e960",  "sweetener_natural",    1),
    ("e407",  "high_severity_emulsifier", 3),
    ("e322",  "emulsifier",           1),
    ("e471",  "emulsifier",           2),
    ("e415",  "thickener",            2),
    ("e412",  "thickener",            1),
    ("e150d", "artificial_colour",    2),
    ("e250",  "preservative",         3),
    ("e251",  "preservative",         3),
    ("e211",  "preservative",         2),
    ("e202",  "preservative",         2),
    ("e338",  "acid_regulator",       2),
    ("e330",  "acid_regulator",       1),
    ("e621",  "flavour_enhancer",     2),
]

# ── Positioning signal markers ────────────────────────────────────────────────
# DETECTED AND STORED but NOT used in composition_marker_score (ADR-010).
# Purpose: ingredient_based_claim_signals_found field, benchmark
# intersection detection, Power BI filtering. Front-of-pack claims are
# extracted separately via vision_extract.py.

POSITIONING_SIGNAL_MARKERS = [
    # Protein — require explicit claim context, not bare ingredient
    ("high protein",          "protein_claim"),
    ("high-protein",          "protein_claim"),
    ("protein bar",           "protein_claim"),
    ("protein shake",         "protein_claim"),
    ("protein powder",        "protein_claim"),
    ("whey protein",          "protein_claim"),
    ("pea protein",           "protein_claim"),
    ("soy protein isolate",   "protein_claim"),
    ("plant protein",         "protein_claim"),
    ("added protein",         "protein_claim"),
    ("riche en proteines",    "protein_claim"),
    ("proteines ajoutees",    "protein_claim"),
    ("source de proteines",   "protein_claim"),
    ("proteinangereichert",   "protein_claim"),   # DE v1.5
    ("proteinquelle",         "protein_claim"),   # DE v1.5
    # Probiotic
    ("probiotic",             "probiotic_claim"),
    ("probiotique",           "probiotic_claim"),
    ("lactobacillus",         "probiotic_claim"),
    ("bifidobacterium",       "probiotic_claim"),
    ("bifidus",               "probiotic_claim"),
    ("live cultures",         "probiotic_claim"),
    ("ferments lactiques",    "probiotic_claim"),
    # Prebiotic / fibre
    ("prebiotic",             "prebiotic_claim"),
    ("prebiotique",           "prebiotic_claim"),
    ("inulin de chicoree",    "prebiotic_claim"),
    ("extrait de chicoree",   "prebiotic_claim"),
    ("chicory root",          "prebiotic_claim"),
    ("source de fibres",      "fibre_claim"),
    ("source of fibre",       "fibre_claim"),
    ("source of fiber",       "fibre_claim"),
    ("riche en fibres",       "fibre_claim"),
    ("high in fibre",         "fibre_claim"),
    ("ballaststoffquelle",    "fibre_claim"),      # DE v1.5
    # Vitamins / fortification
    ("vitamin",               "fortification_claim"),
    ("vitamine",              "fortification_claim"),
    ("calcium",               "fortification_claim"),
    ("magnesium",             "fortification_claim"),
    ("zinc",                  "fortification_claim"),
    ("omega-3",               "fortification_claim"),
    ("omega 3",               "fortification_claim"),
    ("collagen",              "fortification_claim"),
    ("collagene",             "fortification_claim"),
    ("germe de ble",          "fortification_claim"),
    ("wheat germ",            "fortification_claim"),
    # Adaptogens — require extract context (not bare colorant ingredient)
    ("ashwagandha",           "adaptogen_claim"),
    ("maca",                  "adaptogen_claim"),
    ("turmeric extract",      "adaptogen_claim"),
    ("curcumin extract",      "adaptogen_claim"),
    ("extrait de curcuma",    "adaptogen_claim"),
    ("ginseng",               "adaptogen_claim"),
    ("matcha",                "adaptogen_claim"),
    ("spirulina",             "adaptogen_claim"),
    ("spiruline",             "adaptogen_claim"),
    ("chlorella",             "adaptogen_claim"),
    ("moringa",               "adaptogen_claim"),
    # Keto
    ("keto",                  "keto_claim"),
    ("ketogenic",             "keto_claim"),
    ("low carb",              "keto_claim"),
    ("low-carb",              "keto_claim"),
    # Energy — stored but excluded from scoring (ADR-010, OBS-017)
    ("caffeine",              "energy_claim"),
    ("cafeine",               "energy_claim"),
    ("guarana",               "energy_claim"),
    ("taurine",               "energy_claim"),
    ("creatine",              "energy_claim"),
    ("electrolyte",           "energy_claim"),
    # German v1.5 stubs
    ("proteinangereichert",   "protein_claim"),
    ("proteinquelle",         "protein_claim"),
    ("ballaststoffquelle",    "fibre_claim"),

    # ── Vegan positioning ────────────────────────────────────────────────────
    ("100% vegan",            "vegan_claim"),
    ("totally vegan",         "vegan_claim"),
    ("vegan",                 "vegan_claim"),
    ("vegane",                "vegan_claim"),
    ("végan",                 "vegan_claim"),

    # ── Organic / Bio ────────────────────────────────────────────────────────
    ("bio",                   "organic_claim"),
    ("organic",               "organic_claim"),
    ("biologisch",            "organic_claim"),
    ("biologique",            "organic_claim"),
    ("100% bio",              "organic_claim"),

    # ── Dairy-free / plant-based ─────────────────────────────────────────────
    ("no dairy",              "dairy_free_claim"),
    ("dairy free",            "dairy_free_claim"),
    ("dairy-free",            "dairy_free_claim"),
    ("no milk",               "dairy_free_claim"),
    ("plant-based",           "plant_based_claim"),
    ("plant based",           "plant_based_claim"),

    # ── Climate / environmental ──────────────────────────────────────────────
    ("climate footprint",     "sustainability_positioning"),
    ("carbon footprint",      "sustainability_positioning"),
    ("carbon neutral",        "sustainability_positioning"),
    ("net zero",              "sustainability_positioning"),
    ("climate positive",      "sustainability_positioning"),

    # ── Heritage ─────────────────────────────────────────────────────────────
    ("the original",          "heritage_claim"),

    # ── Weight management adjacent ───────────────────────────────────────────
    ("low calorie",           "weight_management_positioning"),
    ("weight management",     "weight_management_positioning"),

    # ── Gender targeting ──────────────────────────────────────────────────────
    ("created for women",        "gender_targeting_claim"),
    ("for women",                "gender_targeting_claim"),
    ("pour les femmes",          "gender_targeting_claim"),

    # ── Clean label / transparency ────────────────────────────────────────────
    ("simply good",              "clean_label_claim"),
    ("simply bon",               "clean_label_claim"),
    ("ingredients you can see",  "clean_label_claim"),
    ("see & pronounce",          "clean_label_claim"),
    ("from real food",           "clean_label_claim"),

    # ── Gerblé VITALITÉ concept ───────────────────────────────────────────────
    ("vitalité",                 "vitalite_concept"),
    ("vitalite",                 "vitalite_concept"),

    # ── No palm oil (FR market) ───────────────────────────────────────────────
    ("sans huile de palme",      "no_palm_oil"),

    # ── Sustainability / sourcing ─────────────────────────────────────────────
    ("engagé cacao durable",     "sustainability_positioning"),
    ("blé filière durable",      "sustainability_positioning"),

    # ── Energy claims ─────────────────────────────────────────────────────────
    ("sport & énergie",          "energy_claim"),
    ("sport et énergie",         "energy_claim"),
    ("slow release",             "energy_claim"),
    ("4 hours of",               "energy_claim"),
    ("toute la matinée",         "energy_claim"),
    ("steady energy",            "energy_claim"),
    ("nutritious energy",        "energy_claim"),
    ("sustained energy",         "energy_claim"),
    ("more power",               "energy_claim"),
    ("activgo",                  "energy_claim"),

    # ── Sugar reduction (FR/ES) ───────────────────────────────────────────────
    ("moins de sucres",          "reduced_sugar"),
    ("allégé en sucres",         "reduced_sugar"),
    ("menos azúcar",             "reduced_sugar"),

    # ── Fortification additions ───────────────────────────────────────────────
    ("riche en vitamines",       "fortification_claim"),
    ("whole grain",              "fortification_claim"),
    ("whole grains",             "fortification_claim"),
    ("wholegrain",               "fortification_claim"),
    ("céréales complètes",       "fortification_claim"),
    ("heart healthy",            "fortification_claim"),
    ("bon pour le coeur",        "fortification_claim"),
    ("super grains",             "fortification_claim"),
    ("ancient grains",           "fortification_claim"),
    ("riche en omega",           "fortification_claim"),
    ("rich in omega",            "fortification_claim"),
    ("opti-start",               "fortification_claim"),
    ("opti-grow",                "fortification_claim"),
    ("opti-dej",                 "fortification_claim"),
    ("opti-déj",                 "fortification_claim"),
    ("hierro",                   "fortification_claim"),  # ES iron
    ("eisen",                    "fortification_claim"),  # DE iron

    # ── Immune claims ─────────────────────────────────────────────────────────
    ("immune system",            "immune_claim"),
    ("immune support",            "immune_claim"),
    ("système immunitaire",      "immune_claim"),
    ("sistema inmunitario",      "immune_claim"),
    ("sistema imunitário",       "immune_claim"),
    ("defensas",                 "immune_claim"),
    ("défenses",                 "immune_claim"),
    ("difese immunitarie",       "immune_claim"),

    # ── Comparative claims ────────────────────────────────────────────────────
    ("#1",                       "comparative_claim"),
    ("numéro 1",                 "comparative_claim"),
    ("n°1",                      "comparative_claim"),
    ("nº1",                      "comparative_claim"),
    ("no. 1",                    "comparative_claim"),
    ("2 fois plus",              "comparative_claim"),
    ("-40% azúcar",              "comparative_claim"),

    # ── Weight management additions ──────────────────────────────────────────
    ("low glycemic",             "weight_management_positioning"),
    ("glycemic index",           "weight_management_positioning"),
    ("faible en matières",       "weight_management_positioning"),
    ("low fat",                  "weight_management_positioning"),

    # ── No artificial (US format) ─────────────────────────────────────────────
    ("no artificial flavors",    "no_artificial"),
    ("no artificial sweeteners", "no_artificial"),
    ("no high fructose",         "no_artificial"),

    # ── Heritage ──────────────────────────────────────────────────────────────
    ("crafted in",               "heritage_claim"),
    ("established",              "heritage_claim"),

    # ── Minimal ingredients ───────────────────────────────────────────────────
    ("3 zutaten",                "minimal_ingredients_claim"),
    ("3 ingredients",            "minimal_ingredients_claim"),
    ("3 ingrédients",            "minimal_ingredients_claim"),
    ("nur 3",                    "minimal_ingredients_claim"),

    # ── No added sugar additions ──────────────────────────────────────────────
    ("no sugars",                "no_added_sugar"),
    ("unsweetened",              "no_added_sugar"),
    ("double zero",              "no_added_sugar"),

    # ── No artificial additions ───────────────────────────────────────────────
    ("zero sweeteners",          "no_artificial"),

    # ── Artisan / origin ──────────────────────────────────────────────────────
    ("freshly brewed",           "artisan_claim"),
    ("maîtrisée",                "origin_quality_claim"),

    # ── Plant-based / dairy-free additions ───────────────────────────────────
    ("this is not milk",         "dairy_free_claim"),
    ("pflanzlich",               "plant_based_claim"),  # DE
    ("plantaardig",              "plant_based_claim"),  # NL
    ("végétal",                  "plant_based_claim"),  # FR
]

# ── Absence / reduction claim markers ─────────────────────────────────────────

ABSENCE_REDUCTION_CLAIM_MARKERS = [
    ("no added sugar",        "no_added_sugar"),
    ("no sugar added",        "no_added_sugar"),
    ("sugar free",            "no_added_sugar"),
    ("sugar-free",            "no_added_sugar"),
    ("no lactose",            "no_lactose"),
    ("lactose free",          "no_lactose"),
    ("lactose-free",          "no_lactose"),
    ("no gluten",             "no_gluten"),
    ("gluten free",           "no_gluten"),
    ("gluten-free",           "no_gluten"),
    ("no preservatives",      "no_preservatives"),
    ("no artificial",         "no_artificial"),
    ("all natural",           "natural_claim"),
    ("100% natural",          "natural_claim"),
    ("clean label",           "clean_label"),
    ("no palm oil",           "no_palm_oil"),
    ("palm oil free",         "no_palm_oil"),
    ("non gmo",               "non_gmo"),
    ("non-gmo",               "non_gmo"),
    ("sans sucre ajoute",     "no_added_sugar"),
    ("sans sucres ajoutes",   "no_added_sugar"),
    ("sans sucre",            "no_added_sugar"),
    ("sans lactose",          "no_lactose"),
    ("sans gluten",           "no_gluten"),
    ("sans conservateur",     "no_preservatives"),
    ("sans additif",          "no_additives"),
    ("sans colorant",         "no_artificial"),
    ("naturel",               "natural_claim"),
    ("100% naturel",          "natural_claim"),
    ("sans huile de palme",   "no_palm_oil"),
    ("moins de sucre",        "reduced_sugar"),
    ("reduit en sucres",      "reduced_sugar"),
    ("ohne zuckerzusatz",     "no_added_sugar"),   # DE v1.5
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_latest_clean(sample_dir):
    files = [
        f for f in os.listdir(sample_dir)
        if (f.startswith("clean_") or f.startswith("bulk_clean_"))
        and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError(
            f"No clean_*.csv found in {sample_dir}. Run clean.py first."
        )
    files.sort(reverse=True)
    return os.path.join(sample_dir, files[0])


def flag_text(text, markers):
    """Scan lowercased text against markers. Returns list of matching tuples."""
    if not isinstance(text, str) or text.strip() == "":
        return []
    text_lower = text.lower()
    found = []
    seen_labels = set()
    for marker in markers:
        keyword = marker[0]
        label   = marker[1]
        if label in seen_labels:
            continue
        if len(keyword) < 5:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found.append(marker)
                seen_labels.add(label)
        else:
            if keyword in text_lower:
                found.append(marker)
                seen_labels.add(label)
    return found


def flag_additives(additives_str, e_markers):
    """Scan pipe-separated additives_tags against E-number markers."""
    if not isinstance(additives_str, str) or additives_str.strip() == "":
        return []
    additives_lower = additives_str.lower()
    found = []
    seen_labels = set()
    for e_num, label, severity in e_markers:
        if label in seen_labels:
            continue
        if e_num in additives_lower:
            found.append((e_num, label, severity))
            seen_labels.add(label)
    return found


def strip_parenthetical_enrichment(text):
    """
    Strip parenthetical sub-lists before checking claim-signal markers.
    Prevents 'enriched flour (niacin, riboflavin, folic acid...)' from
    triggering a fortification signal on mandatory US flour enrichment.
    Also strips colorant context phrases identified during validation.
    See docs/ADR.md ADR-010 and docs/OBSERVATIONS.md OBS-010.
    """
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r'\([^)]*\)', ' ', text)
    color_phrases = [
        r'pour la couleur[\w\s]*',
        r'a pouvoir colorant[\w\s]*',
        r'colorant\s*:[\w\s]*',
        r'farbgebendes lebensmittel[\w\s]*',
        r'farbstoff\s*:[\w\s]*',
    ]
    for cp in color_phrases:
        cleaned = re.sub(cp, ' ', cleaned.lower())
    return cleaned


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_composition_marker_score(upf_flags):
    """
    Component A only: ingredient composition signal (0-40 points).
    Severity-weighted count of detected processing-related markers,
    one count per unique marker category.

    Components B and C (claim weight + processing/nutrition context)
    are added in merge_scores.py from front-of-pack vision extraction.
    See docs/ADR.md ADR-010 and docs/METHODOLOGY.md.
    """
    if not upf_flags:
        return 0
    severity_total = sum(f[2] for f in upf_flags)
    return min(severity_total * 3, 40)


def classify_composition_marker_band(score):
    if score >= 30:
        return "Extensive markers"
    elif score >= 20:
        return "Moderate markers"
    elif score >= 10:
        return "Limited markers"
    else:
        return "Minimal markers"


# ── Benchmark intersection pattern detectors ──────────────────────────────────
# Each detector identifies a specific, recurring co-occurrence between an
# ingredient-based claim signal and a nutrition value. These describe
# co-occurrence patterns, not product verdicts. Thresholds here are
# project-defined pattern thresholds, distinct from the formal
# nutrition_benchmark_flags thresholds (UK FSA front-of-pack scheme) —
# see docs/METHODOLOGY.md for both.
#
# These pattern flags are based on ingredient/name-derived signals and
# nutrition values only. They are useful for broad filtering and early
# pattern detection, but they are not substitutes for pack-image claim
# extraction (see claim_benchmark_intersections in docs/METHODOLOGY.md).

def detect_sugar_positioning_intersection(row):
    """
    A sugar-reduction or absence claim signal co-occurring with sugar
    content above the project-defined pattern threshold.
    Observed in product categories such as fruit drinks, snack bars,
    and flavoured milk.
    """
    neg = str(row.get("absence_reduction_claims_found", "") or "")
    has_claim = "no_added_sugar" in neg or "reduced_sugar" in neg
    try:
        sugars = float(row.get("sugars_100g"))
    except (TypeError, ValueError):
        sugars = None
    return bool(has_claim and sugars is not None and sugars > 8)


def detect_protein_fat_intersection(row):
    """
    A protein claim signal co-occurring with energy or saturated fat
    above the project-defined pattern threshold.
    """
    func = str(row.get("ingredient_based_claim_signals_found", "") or "")
    if "protein_claim" not in func:
        return False
    try:
        kcal    = float(row.get("energy_kcal"))
        sat_fat = float(row.get("saturated_fat_100g"))
    except (TypeError, ValueError):
        kcal = None
        sat_fat = None
    if kcal is not None and kcal > 400:
        return True
    if sat_fat is not None and sat_fat > 5:
        return True
    return False


def detect_fibre_sugar_processing_intersection(row):
    """
    A fibre or prebiotic claim signal co-occurring with NOVA group 4
    and sugar content above the project-defined pattern threshold.
    """
    func = str(row.get("ingredient_based_claim_signals_found", "") or "")
    if "fibre_claim" not in func and "prebiotic_claim" not in func:
        return False
    try:
        nova   = float(row.get("nova_group"))
        sugars = float(row.get("sugars_100g"))
    except (TypeError, ValueError):
        nova = None
        sugars = None
    return bool(nova == 4.0 and sugars is not None and sugars > 15)


def detect_plant_based_nutrition_intersection(row):
    """
    A fortification claim signal on a plant-milk category product with
    energy above the project-defined pattern threshold (60 kcal/100ml,
    the approximate dairy-milk benchmark).
    """
    func = str(row.get("ingredient_based_claim_signals_found", "") or "")
    if "fortification_claim" not in func:
        return False
    off_cats = str(row.get("off_categories", "") or "").lower()
    is_plant_milk = any(kw in off_cats for kw in [
        "plant-based", "oat-milk", "almond-milk", "soy-milk",
        "coconut-milk", "rice-milk", "hafer", "mandel", "avoine",
        "amande", "soja", "oat drink", "almond drink",
    ])
    if not is_plant_milk:
        return False
    try:
        kcal = float(row.get("energy_kcal"))
    except (TypeError, ValueError):
        kcal = None
    return bool(kcal is not None and kcal > 60)


# ── Main analysis pipeline ────────────────────────────────────────────────────

def analyze(input_path):
    print(f"\n  Input file: {os.path.basename(input_path)}")
    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False,
                     dtype={"barcode": str})
    print(f"  Rows on load: {len(df):,}")

    eligible   = df[df["ingredient_analysis_eligible"] == True].copy()
    ineligible = df[df["ingredient_analysis_eligible"] != True].copy()
    print(f"\n  Step 1  - Ingredient analysis eligible: {len(eligible):,} rows")
    print(f"            Ingredient analysis excluded: {len(ineligible):,} rows")

    # Step 2: processing markers — Component A
    print(f"\n  Step 2  - Flagging ingredient composition markers (Component A)...")
    eligible["_upf_flags"] = eligible["ingredients_text"].apply(
        lambda x: flag_text(x, ULTRA_PROCESSED_MARKERS)
    )
    eligible["processing_marker_count"]      = eligible["_upf_flags"].apply(len)
    eligible["processing_markers_found"]     = eligible["_upf_flags"].apply(
        lambda f: "|".join(x[1] for x in f) if f else ""
    )
    eligible["processing_marker_max_severity"] = eligible["_upf_flags"].apply(
        lambda f: max((x[2] for x in f), default=0)
    )
    eligible["has_processing_markers"] = eligible["processing_marker_count"] > 0
    n = eligible["has_processing_markers"].sum()
    print(f"            {n:,} of {len(eligible):,} ({n/len(eligible)*100:.0f}%) have composition markers")

    # Step 3: E-numbers
    print(f"\n  Step 3  - Cross-checking E-numbers...")
    eligible["_e_flags"] = eligible["additives_tags"].apply(
        lambda x: flag_additives(x, E_NUMBER_MARKERS)
    )
    eligible["e_number_count"]  = eligible["_e_flags"].apply(len)
    eligible["e_numbers_found"] = eligible["_e_flags"].apply(
        lambda f: "|".join(x[0] for x in f) if f else ""
    )
    sw_kw = [m for m in ULTRA_PROCESSED_MARKERS if m[1] == "artificial_sweetener"]
    eligible["has_artificial_sweetener"] = eligible.apply(
        lambda row: (
            any(f[1] == "artificial_sweetener" for f in row["_e_flags"]) or
            bool(flag_text(row["ingredients_text"], sw_kw))
        ), axis=1
    )
    e_n  = (eligible["e_number_count"] > 0).sum()
    sw_n = eligible["has_artificial_sweetener"].sum()
    print(f"            {e_n:,} products have flagged E-numbers")
    print(f"            {sw_n:,} products contain artificial sweeteners")

    # Step 4: Ingredient-based claim signals — stored, NOT used in scoring
    print(f"\n  Step 4  - Detecting ingredient-based claim signals "
          f"(stored for downstream comparison, not scored)...")
    eligible["_claim_flags"] = eligible.apply(
        lambda row: flag_text(
            strip_parenthetical_enrichment(str(row["ingredients_text"])) +
            " " + str(row["product_name"]),
            POSITIONING_SIGNAL_MARKERS
        ), axis=1
    )
    eligible["ingredient_based_claim_signal_count"]  = eligible["_claim_flags"].apply(len)
    eligible["ingredient_based_claim_signals_found"] = eligible["_claim_flags"].apply(
        lambda f: "|".join(x[1] for x in f) if f else ""
    )
    claim_n = (eligible["ingredient_based_claim_signal_count"] > 0).sum()
    print(f"            {claim_n:,} products have detectable claim-signal language")
    all_claims = []
    for f in eligible["_claim_flags"]:
        all_claims.extend(x[1] for x in f)
    if all_claims:
        print(f"            Top claim-signal categories:")
        for claim, count in Counter(all_claims).most_common(8):
            print(f"              {claim:<30} {count:,}")

    # Step 5: Absence/reduction claim signals — stored for downstream comparison
    print(f"\n  Step 5  - Detecting absence/reduction claim signals "
          f"(stored for downstream comparison)...")
    eligible["_neg_flags"] = eligible.apply(
        lambda row: flag_text(
            str(row["product_name"]) + " " + str(row.get("labels", "")),
            ABSENCE_REDUCTION_CLAIM_MARKERS
        ), axis=1
    )
    eligible["absence_reduction_claim_count"]  = eligible["_neg_flags"].apply(len)
    eligible["absence_reduction_claims_found"] = eligible["_neg_flags"].apply(
        lambda f: "|".join(x[1] for x in f) if f else ""
    )
    neg_n = (eligible["absence_reduction_claim_count"] > 0).sum()
    print(f"            {neg_n:,} products have absence/reduction claim-signal language")

    # Step 6: composition_marker_score — Component A only
    print(f"\n  Step 6  - Computing composition_marker_score (Component A only)...")
    eligible["composition_marker_score"] = eligible["_upf_flags"].apply(
        compute_composition_marker_score
    )
    eligible["composition_marker_band"] = eligible["composition_marker_score"].apply(
        classify_composition_marker_band
    )
    # Placeholders — populated by merge_scores.py after joining vision results
    eligible["positioning_composition_gap"]      = None
    eligible["positioning_composition_gap_band"] = None
    eligible["pack_claims_found"]                = None

    dist = eligible["composition_marker_band"].value_counts()
    print(f"            Distribution:")
    for cat, n in dist.items():
        print(f"              {cat:<25} {n:,}")

    # Step 7: Benchmark intersection pattern detection
    print(f"\n  Step 7  - Benchmark intersection pattern detection...")
    eligible["sugar_positioning_intersection_flag"] = eligible.apply(
        detect_sugar_positioning_intersection, axis=1)
    eligible["protein_fat_intersection_flag"] = eligible.apply(
        detect_protein_fat_intersection, axis=1)
    eligible["fibre_sugar_processing_intersection_flag"] = eligible.apply(
        detect_fibre_sugar_processing_intersection, axis=1)
    eligible["plant_based_nutrition_intersection_flag"] = eligible.apply(
        detect_plant_based_nutrition_intersection, axis=1)
    print(f"            Sugar positioning intersection:       "
          f"{eligible['sugar_positioning_intersection_flag'].sum():,}")
    print(f"            Protein/fat intersection:             "
          f"{eligible['protein_fat_intersection_flag'].sum():,}")
    print(f"            Fibre/processing intersection:        "
          f"{eligible['fibre_sugar_processing_intersection_flag'].sum():,}")
    print(f"            Plant-based/nutrition intersection:   "
          f"{eligible['plant_based_nutrition_intersection_flag'].sum():,}")

    # Step 8: Clean up, reattach ineligible rows
    drop_cols = ["_upf_flags", "_e_flags", "_claim_flags", "_neg_flags"]
    eligible  = eligible.drop(columns=[c for c in drop_cols if c in eligible.columns])
    analysis_cols = [
        "processing_marker_count", "processing_markers_found",
        "processing_marker_max_severity", "has_processing_markers",
        "e_number_count", "e_numbers_found",
        "has_artificial_sweetener", "ingredient_based_claim_signal_count",
        "ingredient_based_claim_signals_found", "absence_reduction_claim_count",
        "absence_reduction_claims_found", "composition_marker_score",
        "composition_marker_band", "positioning_composition_gap",
        "positioning_composition_gap_band", "pack_claims_found",
        "sugar_positioning_intersection_flag", "protein_fat_intersection_flag",
        "fibre_sugar_processing_intersection_flag",
        "plant_based_nutrition_intersection_flag",
    ]
    for col in analysis_cols:
        if col not in ineligible.columns:
            ineligible[col] = None

    df_out = pd.concat([eligible, ineligible], ignore_index=True)
    df_out = df_out.sort_values("barcode").reset_index(drop=True)
    return df_out


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar - analyze.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Architecture:  Component A (ingredient composition) only")
    print(f"               Components B+C added in merge_scores.py from vision results\n")

    input_path = find_latest_clean(SAMPLE_DIR)
    df = analyze(input_path)

    eligible = df[df["ingredient_analysis_eligible"] == True].copy()
    eligible["composition_marker_score"] = pd.to_numeric(
        eligible["composition_marker_score"], errors="coerce"
    )

    print(f"\n  -- Summary --------------------------------------------------")
    print(f"  Total rows:          {len(df):,}")
    print(f"  Ingredient analyzed: {len(eligible):,}")

    print(f"\n  Top 10 products by composition marker score:")
    top = eligible.nlargest(10, "composition_marker_score")[
        ["product_name", "brands", "composition_marker_score", "processing_markers_found"]
    ]
    pd.set_option("display.max_colwidth", 35)
    print("  " + top.to_string().replace("\n", "\n  "))

    print(f"\n  Benchmark intersection patterns:")
    for col, label in [
        ("sugar_positioning_intersection_flag",          "Sugar positioning intersection"),
        ("protein_fat_intersection_flag",                "Protein/fat intersection"),
        ("fibre_sugar_processing_intersection_flag",     "Fibre/processing intersection"),
        ("plant_based_nutrition_intersection_flag",      "Plant-based/nutrition intersection"),
    ]:
        subset = eligible[eligible[col] == True]
        if len(subset):
            top3 = subset["primary_brand"].value_counts().head(3)
            print(f"    {label}: {len(subset):,} | top: {dict(top3)}")
        else:
            print(f"    {label}: 0 products")

    output_path = os.path.join(SAMPLE_DIR, f"analyzed_{timestamp}.csv")
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n  Saved -> analyzed_{timestamp}.csv")
    print(f"  ({len(df):,} rows, {len(df.columns)} columns)")
    print(f"\n  positioning_composition_gap: computed in merge_scores.py,")
    print(f"  joined to vision results on 'barcode'\n")


if __name__ == "__main__":
    main()