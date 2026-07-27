"""
Pre-LLM positioning signal detector — clean-run sampling input.

THE CORE PRINCIPLE (spec, "breaks the ouroboros cleanly"):
    Communication-like metadata (product name, labels, structured claim
    tags) defines the POSITIONING proxy.
    Ingredients and nutrition define PRODUCT REALITY or FORMULATION
    LIKELIHOOD — a SEPARATE axis.
    The new LLM output remains the independent observed claim label.

If ingredients drove both "likely positioning" and "product reality," the
two sides of the sampling matrix would be partly circular. So this module
splits the existing analyze.py keyword material into two strictly separate
piles:
  - EXPLICIT (communication) terms  -> pre_llm_positioning_signal
  - FORMULATION (ingredient/nutrition) terms -> formulation_likelihood_signal

Three-level positioning output per the spec (not binary):
  explicit  : a direct claim-like expression in name/labels/tags
  none      : no explicit communication signal found
  (formulation-likelihood is stored separately, NOT as a positioning level)

NOTE on formulation_likelihood_signal = "absent": this means "No
formulation signal detected" — NOT that the formulation cannot support
the claim. The detection rules are deliberately incomplete (name/tag/
ingredient keywords only); absence of a detected signal is a statement
about our metadata, not about the product.

SCOPE: one language profile per run, selected with --region.
French products carry French pack text ("riche en protéines", "sans
sucres ajoutés"), so English-only matching would systematically
under-detect explicit signals in France and bias its sample toward "no
signal" cells. Each profile therefore has its own term dictionary and
its own output file.

The French profile deliberately mirrors the English TERRITORY STRUCTURE
exactly — same keys, translated terms, no French-only territories. The
proxy does not need to be exhaustive (the LLM is the measurement); it
needs to be SYMMETRICALLY incomplete, so a France sample is not
stratified against a different set of territories than US/UK.

Usage:
    python pipeline/detect_positioning_signals.py --region us_uk
    python pipeline/detect_positioning_signals.py --region france

Writes: pipeline/positioning_signals_us_uk.csv
        pipeline/positioning_signals_fr.csv
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT_CSV = Path(__file__).resolve().parent / "positioning_signals_us_uk.csv"

# Rebound in main() from the selected profile — do not edit directly.
RULE_VERSION     = "positioning-v1-en"
IN_SCOPE_REGIONS = {"US_CANADA", "UK_IE"}
OUT_CSV          = Path(__file__).resolve().parent / "positioning_signals_us_uk.csv"
STRIP_ACCENTS    = False

# ── EXPLICIT positioning terms (communication-like text ONLY) ───────────────
# These are things a marketer writes on a pack.
# Territory -> list of substrings searched in product_name.
# Deliberately EXCLUDES ingredient names (whey, casein, inulin, chicory,
# lactobacillus, etc.) — those are formulation, handled separately below.
EXPLICIT_TERMS_EN: dict[str, list[str]] = {
    "protein": [
        "high protein", "high in protein", "source of protein",
        "protein rich", "rich in protein", "added protein", "extra protein",
        "protein packed", "packed with protein", "20g protein", "protein",
    ],
    "fibre": [
        "high fibre", "high fiber", "high in fibre", "high in fiber",
        "source of fibre", "source of fiber", "fibre rich", "fiber rich",
        "added fibre", "added fiber",
    ],
    "whole_grain": [
        "whole grain", "wholegrain", "whole grains", "whole wheat",
        "wholewheat", "multigrain", "multi-grain",
    ],
    "sugar": [
        "no added sugar", "no added sugars", "sugar free", "sugar-free",
        "reduced sugar", "less sugar", "lower sugar", "unsweetened",
        "zero sugar", "no sugar",
    ],
    "fat": [
        "low fat", "reduced fat", "fat free", "fat-free",
        "low in fat", "reduced saturated fat", "half the fat",
        "98% fat free", "95% fat free",
    ],
    # Plant-based family — SPLIT into distinct subtypes per spec, because
    # "plant-based" is a broad umbrella that conflates several different
    # claims. Each is stored separately; they roll up to a parent for
    # quota control but stay individually queryable.
    #
    # CRITICAL: these are matched against COMMUNICATION fields only
    # (product_name + labels), NEVER off_categories — OFF's category
    # ancestry contains the literal string "Plant-based foods and
    # beverages" as a top-level parent, which a juice/biscuit/cereal
    # inherits automatically with zero plant-based positioning on pack.
    # Matching that ancestry inflated this territory to a false 22%.
    "explicit_plant_based_positioning": [
        "plant-based", "plant based", "vegan", "100% plant-based",
        "plant powered", "plant-powered",
    ],
    "explicit_vegetarian_signal": [
        "vegetarian",   # suitability, NOT plant-based — kept separate
    ],
    "explicit_dairy_free_signal": [
        "dairy free", "dairy-free", "non-dairy", "non dairy", "no dairy",
    ],
    "plant_origin_identity": [
        "oat drink", "oat milk", "almond drink", "almond milk",
        "soy drink", "soy milk", "soya drink", "coconut yogurt",
        "coconut milk", "soy dessert", "soy yogurt", "rice drink",
        "oat original", "soy original",
    ],
    "natural_name_signal": [
        "natural", "all natural", "100% natural", "nothing artificial",
        "no artificial", "no additives", "no preservatives",
    ],
    "organic_name_signal": [
        "organic", "bio", "biologique",
    ],
    "purity_simplicity_signal": [
        "clean label", "simple ingredients", "no nonsense",
        "just fruit", "just oats", "nothing but",
    ],
    "traditional_origin_signal": [
        "traditional", "farmhouse", "authentic", "original recipe",
        "time-honoured", "time honored",
    ],
    "energy": [
        "energy", "boost", "sustained energy", "slow release energy",
        "steady energy",
    ],
    "immune": [
        "immune", "immunity", "immune support", "supports immunity",
        "defences", "natural defences",
    ],
}

# Sub-signals that roll up to a parent territory for quota management.
# Detection stays granular (above); this maps granular -> parent so the
# sampler can quota on either level. NOTE: vegetarian and dairy-free
# deliberately do NOT roll up to plant_based — they are distinct claims
# (vegetarian = suitability, may contain dairy/eggs; dairy-free =
# free-from). They roll up to a broad "plant_based_related" parent only
# for coarse quota control, but stay individually distinguishable.
TERRITORY_ROLLUP = {
    "explicit_plant_based_positioning": "plant_based_related",
    "explicit_vegetarian_signal":       "plant_based_related",
    "explicit_dairy_free_signal":       "plant_based_related",
    "plant_origin_identity":            "plant_based_related",
    "natural_name_signal":       "naturalness",
    "organic_name_signal":       "naturalness",
    "purity_simplicity_signal":  "naturalness",
    "traditional_origin_signal": "naturalness",
}

# ── FORMULATION-likelihood terms (ingredients/nutrition) — ENRICHMENT ONLY ──
# NEVER used as the positioning proxy. Ingredient substrings searched in
# ingredients_text. Presence suggests a claim MAY be likely, but does not
# prove any front-of-pack communication.
FORMULATION_INGREDIENT_TERMS_EN: dict[str, list[str]] = {
    "protein": [
        "whey", "casein", "milk protein", "pea protein", "soy protein",
        "protein isolate", "protein concentrate",
    ],
    "fibre": [
        "inulin", "chicory", "bran", "psyllium", "oat fibre", "oat fiber",
    ],
    "whole_grain": [
        "whole grain", "wholemeal", "whole oats", "whole wheat flour",
    ],
    "sugar": [
        "erythritol", "stevia", "sucralose", "aspartame", "acesulfame",
        "maltitol", "xylitol", "sweetener",
    ],
    "plant_based": [
        "oat base", "soy base", "almond", "pea protein", "coconut milk",
        "oat drink", "soy drink",
    ],
    # Immunity and gut-health are almost never in product NAMES (spec:
    # "it would just sound strange to consumers"), but ARE detectable via
    # ingredients — vitamins, zinc, probiotic cultures. These products
    # stay pre_llm_positioning_signal = none unless the name explicitly
    # says immunity; the formulation signal is what flags them as worth
    # sampling so the LLM can check whether the pack communicates it.
    "immune": [
        "vitamin c", "vitamin d", "zinc", "vitamin b", "selenium",
    ],
    "gut_health": [
        "lactobacillus", "bifidobacterium", "bifidus", "live cultures",
        "ferments lactiques", "probiotic", "inulin", "chicory",
    ],
}



# ── FRENCH equivalents ──────────────────────────────────────────────────────
# Same territory keys as EXPLICIT_TERMS_EN, deliberately. Terms are written
# with accents for readability and stripped at profile-application time, so
# they match OFF names whether or not the contributor typed the accents.
#
# CRITICAL EXCLUSION: "nature" is NOT a naturalness term. On French,
# Belgian and Swiss packs "Yaourt Nature" / "Briochettes Nature" means
# plain / unflavoured. Only explicit naturalness wording counts —
# "naturel", "100% naturel", "sans additifs". This mirrors the rule that
# has been in the extraction prompt since v1.
EXPLICIT_TERMS_FR: dict[str, list[str]] = {
    "protein": [
        "protéines", "protéine", "riche en protéines", "riche en protéine",
        "source de protéines", "sources de protéines", "protéines ajoutées",
        "haute teneur en protéines", "teneur élevée en protéines",
        "forte teneur en protéines", "enrichi en protéines",
        "enrichie en protéines", "plus de protéines", "protéiné",
        "protéinée", "protéinés", "protéinées",
        "hyperprotéiné", "hyperprotéinée", "hyperprotéinés", "hyperprotéinées",
        "high protein", "protein",
    ],
    "fibre": [
        "fibres", "fibre", "riche en fibres", "riche en fibre",
        "source de fibres", "sources de fibres", "haute teneur en fibres",
        "enrichi en fibres", "enrichie en fibres", "plus de fibres",
        "high fibre", "high fiber",
    ],
    "whole_grain": [
        "céréales complètes", "céréale complète", "blé complet", "blé entier",
        "farine complète", "farines complètes", "farine de blé complet",
        "avoine complète", "pain complet", "riz complet", "pâtes complètes",
        "multicéréales", "multi-céréales", "grains entiers", "grain entier",
        "intégral", "intégrale", "intégrales", "wholegrain", "whole grain",
    ],
    "sugar": [
        "sans sucres ajoutés", "sans sucre ajouté", "sans sucres", "sans sucre",
        "réduit en sucres", "réduit en sucre", "allégé en sucres",
        "allégé en sucre", "moins de sucres", "moins de sucre",
        "teneur réduite en sucres", "faible en sucres", "peu sucré",
        "zéro sucre", "zéro sucres", "0% sucres", "0% sucre",
        "non sucré", "non sucrée", "sans édulcorants", "sans édulcorant",
        "no added sugar", "sugar free", "zero sugar",
    ],
    "fat": [
        "allégé en matières grasses", "allégée en matières grasses",
        "réduit en matières grasses", "sans matières grasses",
        "sans matière grasse", "faible en matières grasses",
        "faible en matières", "pauvre en matières grasses",
        "matières grasses réduites", "0% de matières grasses", "0% mg",
        "allégé", "allégée", "allégés", "allégées", "léger", "légère",
        "low fat", "light",
    ],
    "explicit_plant_based_positioning": [
        "végétal", "végétale", "végétaux", "végétales", "100% végétal",
        "à base de plantes", "origine végétale", "vegan", "végan", "végane",
        "végétalien", "végétalienne", "plant-based", "plant based",
    ],
    "explicit_vegetarian_signal": [
        "végétarien", "végétarienne", "végétariens", "végétariennes",
        "vegetarian",
    ],
    "explicit_dairy_free_signal": [
        # "sans lactose" is deliberately absent — lactose-free milk is still
        # dairy. The distinction is enforced in the extraction prompt (v4).
        "sans produits laitiers", "sans produit laitier", "sans lait",
        "dairy free", "dairy-free",
    ],
    "plant_origin_identity": [
        "boisson avoine", "boisson à l'avoine", "boisson amande",
        "boisson à l'amande", "boisson soja", "boisson au soja",
        "boisson riz", "boisson au riz", "boisson végétale",
        "boissons végétales", "lait de coco", "lait d'amande",
        "lait d'avoine", "lait de soja", "lait de riz", "crème de coco",
        "dessert soja", "dessert au soja", "yaourt soja", "yaourt au soja",
        "yaourt coco", "jus de soja",
        "oat drink", "almond drink", "soy drink",
    ],
    "natural_name_signal": [
        # NB: bare "nature" deliberately absent — on French, Belgian and
        # Swiss packs "Yaourt Nature" means plain / unflavoured, not a
        # naturalness claim. This mirrors the rule in the prompt since v1.
        "naturel", "naturelle", "naturels", "naturelles", "100% naturel",
        "ingrédients naturels", "sans additifs", "sans additif",
        "sans conservateurs", "sans conservateur", "sans colorants",
        "sans colorant", "sans arômes artificiels", "sans arôme artificiel",
        "sans arômes", "sans arôme", "rien d'artificiel",
        "sans ogm", "no artificial",
        # French also negates with "aucun/aucune", not only "sans"
        # (OBS-024: Gerblé "Aucun colorant").
        "aucun colorant", "aucun conservateur", "aucun additif",
        "aucun arôme artificiel", "aucun arôme", "aucune matière grasse",
        "exclusivement naturels", "arômes exclusivement naturels",
        "sans exhausteur de goût",
        # Palm-oil absence is a major French front-of-pack claim
        # (OBS-024, OBS-025). The English dictionary has no palm-oil term
        # because it is not common US/UK pack language — territory
        # STRUCTURE stays symmetric, individual terms are market-specific.
        "sans huile de palme",
    ],
    "organic_name_signal": [
        "bio", "biologique", "biologiques", "100% bio",
        "agriculture biologique", "issu de l'agriculture biologique",
        "organic",
    ],
    "purity_simplicity_signal": [
        # NB: "pur jus", "100% fruits" and "pur beurre" are deliberately
        # absent. On French juice, compote and pastry they are category or
        # legal descriptors, not positioning — the English equivalents in
        # this territory ("just fruit", "nothing but") are marketing
        # slogans. Including them produced 4,155 FR hits against 7 EN.
        "ingrédients simples", "2 ingrédients", "3 ingrédients",
        "4 ingrédients", "5 ingrédients", "clean label",
        "rien que", "que du bon",
    ],
    "traditional_origin_signal": [
        "traditionnel", "traditionnelle", "traditionnels", "traditionnelles",
        "recette traditionnelle", "artisanal", "artisanale", "artisanaux",
        "artisanales", "artisan", "à l'ancienne", "authentique",
        "fermier", "fermière", "fermiers", "fermières", "terroir",
        "recette originale", "origine france", "origine française",
        "fabriqué en france", "produit en france", "made in france",
        "filière maîtrisée", "maîtrisée", "fait maison", "savoir-faire",
    ],
    "energy": [
        "énergie", "énergies", "énergétique", "énergétiques", "vitalité",
        "tonus", "boost", "sport & énergie", "sport et énergie",
        "toute la matinée", "énergie longue durée", "coup de fouet",
        "énergisant", "énergisante", "énergisants", "énergisantes",
        "boisson énergisante",
    ],
    "immune": [
        "défenses naturelles", "défense naturelle", "défenses", "défense",
        "immunité", "immunitaire", "immunitaires", "système immunitaire",
    ],
}

# French ingredient vocabulary. Same territory keys as the English version.
FORMULATION_INGREDIENT_TERMS_FR: dict[str, list[str]] = {
    "protein": [
        "protéines de lait", "protéines de lactosérum", "lactosérum",
        "caséine", "caséinate", "caséinates", "protéines de pois",
        "protéines de soja", "protéines de blé", "isolat de protéines",
        "concentré de protéines", "gluten de blé",
    ],
    "fibre": [
        "inuline", "inuline de chicorée", "extrait de chicorée", "chicorée",
        "son de blé", "son d'avoine", "psyllium", "fibres d'avoine",
        "fibre d'acacia", "fibres de chicorée",
    ],
    "whole_grain": [
        "farine complète", "farine de blé complet", "blé complet",
        "avoine complète", "céréales complètes", "germe de blé",
        "flocons d'avoine",
    ],
    "sugar": [
        "érythritol", "stévia", "stevia", "sucralose", "aspartame",
        "acésulfame", "maltitol", "xylitol", "édulcorant", "édulcorants",
    ],
    "plant_based": [
        "base d'avoine", "base de soja", "amande", "amandes", "avoine",
        "soja", "lait de coco", "boisson avoine", "boisson soja",
        "protéines de pois",
    ],
    "immune": [
        "vitamine c", "vitamine d", "vitamine b", "zinc", "sélénium",
        "vitamines",
    ],
    "gut_health": [
        "lactobacillus", "bifidobacterium", "bifidus", "ferments lactiques",
        "cultures vivantes", "probiotique", "probiotiques", "prébiotique",
        "prébiotiques", "inuline", "chicorée", "l. casei",
    ],
}


# ── Region profiles ─────────────────────────────────────────────────────────
REGION_PROFILES: dict[str, dict] = {
    "us_uk": {
        "regions":           {"US_CANADA", "UK_IE"},
        "rule_version":      "positioning-v1-en",
        "out_csv":           "positioning_signals_us_uk.csv",
        "explicit_terms":    EXPLICIT_TERMS_EN,
        "formulation_terms": FORMULATION_INGREDIENT_TERMS_EN,
        # False preserves the exact behaviour that produced the locked
        # release-01 sample. Do not change without re-running that sample.
        "strip_accents":     False,
    },
    "france": {
        "regions":           {"FRANCE"},
        "rule_version":      "positioning-v1-fr",
        "out_csv":           "positioning_signals_fr.csv",
        "explicit_terms":    EXPLICIT_TERMS_FR,
        "formulation_terms": FORMULATION_INGREDIENT_TERMS_FR,
        # OFF contributors type French names with and without accents.
        # Stripping both sides makes matching robust to that.
        "strip_accents":     True,
    },
}

# Rebound in main() from the selected profile.
EXPLICIT_TERMS               = EXPLICIT_TERMS_EN
FORMULATION_INGREDIENT_TERMS = FORMULATION_INGREDIENT_TERMS_EN


def _strip_accents(text: str) -> str:
    t = unicodedata.normalize("NFKD", text)
    return "".join(c for c in t if not unicodedata.combining(c))


def _prepare_terms(term_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """Lowercase and, when the profile requires it, de-accent every term so
    terms and haystack are normalised identically."""
    if not STRIP_ACCENTS:
        return term_map
    return {k: [_strip_accents(t.lower()) for t in v] for k, v in term_map.items()}


def _norm(text) -> str:
    s = str(text or "").lower()
    return _strip_accents(s) if STRIP_ACCENTS else s


# Cache compiled word-boundary patterns per term (built once, reused
# across all ~158k rows).
_WB_CACHE: dict[str, re.Pattern] = {}


def _wb(term: str) -> re.Pattern:
    if term not in _WB_CACHE:
        # \b word boundaries around the whole term. Handles hyphens/spaces
        # inside multi-word terms fine — the boundary is only enforced at
        # the outer edges, so "low fat" still matches "low fat yogurt" but
        # "light" no longer matches inside "starlight".
        _WB_CACHE[term] = re.compile(r"\b" + re.escape(term) + r"\b")
    return _WB_CACHE[term]


def _match_territories(haystack: str, term_map: dict[str, list[str]]) -> list[str]:
    found = []
    for territory, terms in term_map.items():
        if any(_wb(t).search(haystack) for t in terms):
            found.append(territory)
    return found


def detect_row(row) -> dict:
    # Explicit proxy: product_name ONLY. Both off_categories AND labels are
    # excluded — both carry OFF-inferred tags applied algorithmically, not
    # written on pack. off_categories carries "Plant-based foods and
    # beverages" ancestry; labels carries auto-applied en:vegetarian (put
    # on anything meatless), en:vegan, etc. The precision review showed
    # products like "Rice Cakes Salted" and "Aunt Millie's" matching
    # "vegetarian" with no such word in the name — the match came from an
    # inferred label. Product name is the only field that reliably
    # reflects deliberate pack communication.
    comm_text = _norm(row.get("product_name"))
    explicit_territories = _match_territories(comm_text, EXPLICIT_TERMS)

    # Name-quality flag (spec): product_name is the ONLY communication
    # field we trust, but some names are too sparse to trust the "none"
    # result — a blank/one-word/numeric-only name means we genuinely
    # can't tell whether positioning exists, as opposed to confidently
    # observing its absence. This is a SEPARATE quality dimension, not a
    # third positioning level: signal stays explicit/none, but a
    # none-signal with a low-confidence name is "unknown", not "confirmed
    # absent". The sampler can then treat these as their own stratum
    # rather than lumping them with genuine no-positioning products.
    # Deliberately does NOT pull in labels/off_categories to "rescue"
    # these — that reintroduces exactly the inferred-tag contamination
    # just removed. Sparse names stay flagged, not backfilled.
    name_raw = str(row.get("product_name") or "").strip()
    word_count = len(name_raw.split())
    alpha_chars = sum(c.isalpha() for c in name_raw)
    low_confidence_name = (
        name_raw == ""              # missing entirely
        or word_count <= 1          # single token ("Yogurt", a brand code)
        or alpha_chars < 3          # numeric/near-empty ("500ml", "2%")
    )

    # Formulation likelihood: ingredients ONLY. Kept strictly separate.
    ingredients = _norm(row.get("ingredients_text"))
    formulation_territories = _match_territories(ingredients, FORMULATION_INGREDIENT_TERMS)

    # Naturalness formulation signal also draws on additive count + NOVA
    # (raw fields — NOT the deprecated composition_marker_score).
    additives = _norm(row.get("additives_tags"))
    additive_count = additives.count("en:e") if additives else 0
    nova = row.get("nova_group")
    if additive_count == 0 and nova in (1, 1.0):
        formulation_territories.append("naturalness")

    signal = "explicit" if explicit_territories else "none"
    # Confidence: an explicit match is trustworthy regardless of name
    # length (the positioning word IS present). Only a "none" result on a
    # sparse name is untrustworthy — that's where "none" might really be
    # "unknown".
    if signal == "explicit":
        name_confidence = "ok"
    elif low_confidence_name:
        name_confidence = "low_confidence_name"
    else:
        name_confidence = "ok"

    return {
        "pre_llm_positioning_signal": signal,
        "pre_llm_positioning_territories": "|".join(explicit_territories),
        "name_confidence": name_confidence,
        "formulation_likelihood_signal": "present" if formulation_territories else "absent",
        "formulation_territories": "|".join(sorted(set(formulation_territories))),
        "positioning_rule_version": RULE_VERSION,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect pre-LLM positioning signals for one region profile."
    )
    parser.add_argument("--region", choices=sorted(REGION_PROFILES),
                        default="us_uk",
                        help="Language/region profile to run (default: us_uk)")
    args = parser.parse_args()

    global RULE_VERSION, IN_SCOPE_REGIONS, OUT_CSV, STRIP_ACCENTS
    global EXPLICIT_TERMS, FORMULATION_INGREDIENT_TERMS
    profile          = REGION_PROFILES[args.region]
    RULE_VERSION     = profile["rule_version"]
    IN_SCOPE_REGIONS = profile["regions"]
    OUT_CSV          = Path(__file__).resolve().parent / profile["out_csv"]
    STRIP_ACCENTS    = profile["strip_accents"]
    EXPLICIT_TERMS               = _prepare_terms(profile["explicit_terms"])
    FORMULATION_INGREDIENT_TERMS = _prepare_terms(profile["formulation_terms"])
    _WB_CACHE.clear()

    print(f"\nRegion profile: {args.region}")
    print(f"  Regions:       {sorted(IN_SCOPE_REGIONS)}")
    print(f"  Rule version:  {RULE_VERSION}")
    print(f"  Accent-strip:  {STRIP_ACCENTS}")
    print(f"  Output:        {OUT_CSV.name}\n")

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    df = pd.read_sql_query("""
        SELECT barcode, product_name, labels, off_categories, ingredients_text,
               additives_tags, nova_group, query_category,
               observed_market_region_codes
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    """, conn)
    conn.close()

    # A product is in scope if it carries ANY of the profile's region codes.
    # Region codes are multi-valued and their order is OFF contributor
    # insertion order, so membership — not position — is what counts.
    def in_scope(codes) -> bool:
        present = set(str(codes or "").split("|"))
        return bool(present & IN_SCOPE_REGIONS)

    scope_mask = df["observed_market_region_codes"].apply(in_scope)
    n_total = len(df)
    df = df[scope_mask].copy()
    print(f"Products in {'/'.join(sorted(IN_SCOPE_REGIONS))} scope: "
          f"{len(df):,} of {n_total:,} (out of scope: {n_total - len(df):,})")

    signals = df.apply(detect_row, axis=1, result_type="expand")
    out = pd.concat([df[["barcode", "product_name", "query_category"]], signals], axis=1)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} rows to {OUT_CSV}\n")

    # Audit summary — is explicit-signal detection landing sensibly?
    print("Pre-LLM positioning signal distribution:")
    print(out["pre_llm_positioning_signal"].value_counts().to_string())
    print(f"\nExplicit-signal rate: {(out['pre_llm_positioning_signal'] == 'explicit').mean():.1%}")

    print("\nName-confidence distribution:")
    print(out["name_confidence"].value_counts().to_string())
    n_low = (out["name_confidence"] == "low_confidence_name").sum()
    print(f"\nProducts with a 'none' signal AND a low-confidence name "
          f"(genuinely 'unknown', not confirmed-absent): {n_low:,} "
          f"({n_low/len(out):.1%} of in-scope products)")

    print("\nExplicit positioning territories (granular, share of all products):")
    terr_counts: dict[str, int] = {}
    for terrs in out["pre_llm_positioning_territories"]:
        for t in (terrs.split("|") if terrs else []):
            terr_counts[t] = terr_counts.get(t, 0) + 1
    for t, c in sorted(terr_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:<34} {c:>6} ({c/len(out):.1%})")

    print("\nExplicit positioning territories (rolled up to parent):")
    parent_counts: dict[str, int] = {}
    for t, c in terr_counts.items():
        parent = TERRITORY_ROLLUP.get(t, t)
        parent_counts[parent] = parent_counts.get(parent, 0) + c
    for t, c in sorted(parent_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:<34} {c:>6} ({c/len(out):.1%})")

    print("\nFormulation-likelihood signal distribution:")
    print(out["formulation_likelihood_signal"].value_counts().to_string())

    # The analytically interesting cross-tab: explicit vs formulation.
    # "explicit but no formulation" and "formulation but no explicit" are
    # exactly the non-circular, interesting cells the spec cares about.
    print("\nExplicit x Formulation cross-tab:")
    print(pd.crosstab(out["pre_llm_positioning_signal"],
                      out["formulation_likelihood_signal"]).to_string())


if __name__ == "__main__":
    main()
