"""
build_brand_alias_bottom_up_review.py
-------------------------------------
Generate the first-pass bottom-up brand alias review file.

This script proposes normalized brand candidates only. It does not assign
parent-company ownership and does not modify reference mapping files.

Usage:
    python pipeline/build_brand_alias_bottom_up_review.py
"""

from __future__ import annotations

import argparse
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "sample" / "clean_20260822_220423.csv"
ALIAS_PATH = ROOT / "data" / "reference" / "brand_alias_mapping.csv"
PRIVATE_LABEL_MAPPING_PATH = ROOT / "data" / "reference" / "private_label_brand_mapping.csv"
OUTPUT_DIR = ROOT / "data" / "brand_mapping_review"
DEFAULT_OUTPUT = OUTPUT_DIR / "brand_alias_suggestions_bottom_up.csv"
DEFAULT_REVIEWED_OUTPUT = (
    OUTPUT_DIR / "brand_alias_suggestions_bottom_up_reviewed.csv"
)
DEFAULT_SUMMARY_OUTPUT = OUTPUT_DIR / "brand_alias_bottom_up_review_summary.csv"
DEFAULT_CARREFOUR_AUDIT_OUTPUT = (
    OUTPUT_DIR / "carrefour_private_label_mapping_audit.csv"
)
DEFAULT_CARREFOUR_ROW_AUDIT_OUTPUT = (
    OUTPUT_DIR / "carrefour_private_label_row_level_audit.csv"
)

UNKNOWN_VALUES = {"", "nan", "none", "null", "unknown", "sans marque"}

GENERIC_STANDALONE_CANDIDATES = {
    "bio",
    "classic",
    "collection",
    "company",
    "delice",
    "delices",
    "discount",
    "extra",
    "fine ligne",
    "fit",
    "gourmet",
    "greek",
    "kids",
    "light",
    "market",
    "natural",
    "nature",
    "organic",
    "original",
    "premium",
    "protein",
    "saveur",
    "saveurs",
    "selection",
    "simply",
    "skyr",
    "societe",
    "zero",
}

PARENT_PORTFOLIO_GUARDS = {
    "coca-cola": {"dr pepper", "fanta", "sprite", "tropico"},
    "danone": {"activia", "actimel", "volvic", "yopro"},
    "lu": {"prince"},
    "mars": {"m and m's", "mms", "snickers", "twix"},
    "milka": {"oreo"},
    "mondelez": {"belvita", "cadbury", "oreo", "ritz", "toblerone"},
    "nestle": {
        "aero",
        "kit kat",
        "kitkat",
        "nescafe",
        "nespresso",
        "nesquik",
        "pure life",
        "san pellegrino",
    },
    "pepsi": {"7up", "doritos", "gatorade", "lays", "mountain dew", "pepsi"},
}

PRIVATE_LABEL_RETAILER_GUARDS = {
    "aldi": {
        "bellarom",
        "crownfield",
        "milsani",
    },
    "lidl": {
        "bellarom",
        "crownfield",
        "envia",
        "lord nelson",
        "milbona",
        "sondey",
        "solevita",
    },
}

CARREFOUR_STORE_FORMAT_KEYS = {
    "carrefour city",
    "carrefour le marche",
    "carrefour market",
}

CARREFOUR_CURATED_CLEAN_KEYS = {
    "carrefour baby",
    "carrefour bio",
    "carrefour classic",
    "carrefour companino",
    "carrefour discount",
    "carrefour extra",
    "carrefour kids",
    "carrefour light",
    "carrefour original",
    "carrefour selection",
    "carrefour sensation",
    "carrefour sensation vegetal",
    "filiere qualite carrefour",
    "fqc",
    "my carrefour baby",
    "my carrefour baby 0",
    "reflets de france",
    "simpl",
}

CARREFOUR_CONFIRMED_CLEAN_KEYS = {
    "carrefour bio",
    "carrefour classic",
    "carrefour companino",
    "carrefour extra",
    "carrefour kids",
    "carrefour light",
    "carrefour original",
    "carrefour selection",
    "carrefour sensation",
    "carrefour sensation vegetal",
    "filiere qualite carrefour",
    "my carrefour baby",
    "my carrefour baby 0",
    "reflets de france",
    "simpl",
}

CARREFOUR_REVERSED_PRIVATE_LABEL_KEYS = {
    "bio carrefour": "Carrefour Bio",
    "classic carrefour": "Carrefour Classic",
    "extra carrefour": "Carrefour Extra",
    "original carrefour": "Carrefour Original",
    "reflets de france carrefour": "Reflets de France",
    "selection carrefour": "Carrefour Sélection",
    "sensation carrefour": "Carrefour Sensation",
    "simpl carrefour": "Simpl",
}

CARREFOUR_SUPPLIER_NOISE_PHRASES = {
    "bernard bremont reflets de france",
    "carrefour cidres le brun reflets de france",
    "carrefour interdis",
    "cmi carrefour marchandises internationales",
}

RETAILER_BANNERS = {
    "aldi",
    "asda",
    "auchan",
    "carrefour",
    "casino",
    "co-op",
    "coop",
    "e.leclerc",
    "intermarche",
    "leader price",
    "leclerc",
    "lidl",
    "m and s",
    "marks and spencer",
    "monoprix",
    "morrisons",
    "paturages",
    "sainsbury's",
    "sainsburys",
    "tesco",
    "u",
    "waitrose",
}

STRATEGIC_PARENT_PREFIXES = {
    "coca cola",
    "coca-cola",
    "danone",
    "ferrero",
    "kellogg",
    "kellogg's",
    "kelloggs",
    "mars",
    "mondelez",
    "nestle",
    "pepsi",
    "unilever",
}

SUFFIX_STRIP_PROTECTED_PREFIXES = RETAILER_BANNERS | STRATEGIC_PARENT_PREFIXES

RETAILER_PRIVATE_LABEL_LINE_TOKENS = {
    "bio",
    "classic",
    "delice",
    "delices",
    "extra",
    "extra special",
    "finest",
    "free from",
    "freefrom",
    "gourmet",
    "mmm",
    "organic",
    "saveur",
    "saveurs",
    "selection",
    "so organic",
    "taste the difference",
    "tout petits",
}

KNOWN_RETAILER_SUBBRANDS = {
    "aldi": {
        "bellarom",
        "crownfield",
        "milsani",
    },
    "lidl": {
        "bellarom",
        "crownfield",
        "envia",
        "lord nelson",
        "milbona",
        "sondey",
        "solevita",
    },
}

LEGAL_SUFFIX_RE = re.compile(
    r"\b("
    r"inc|inc\.|incorporated|ltd|ltd\.|limited|llc|corp|corp\.|"
    r"corporation|company|co\.|gmbh|s\.a\.|sa|sarl|sas|plc"
    r")\b",
    re.IGNORECASE,
)

PRODUCT_LINE_TOKENS = {
    "bio",
    "organic",
    "finest",
    "gourmet",
    "classic",
    "original",
    "zero",
    "diet",
    "selection",
    "naturals",
}


def normalize_key(value: object) -> str:
    """Normalize a brand-like value into the current project key style."""
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.lower().strip().strip(",")
    text = text.replace("&", " and ")
    text = re.sub(r"[’`´]", "'", text)
    text = re.sub(r"[^a-z0-9'&+.-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    return text


def display_brand(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    return re.sub(r"\s+", " ", text)


def compact_key(value: str) -> str:
    """Remove punctuation and spaces for variant clustering."""
    return re.sub(r"[^a-z0-9]+", "", normalize_key(value))


def raw_primary_brand(value: object) -> str:
    text = normalize_key(value)
    if not text or text in UNKNOWN_VALUES:
        return ""
    return text.split(",")[0].strip()


def strip_legal_suffix(value: str) -> str:
    stripped = LEGAL_SUFFIX_RE.sub("", value)
    stripped = re.sub(r"\s+", " ", stripped).strip(" .,-")
    return stripped


def strip_product_line_suffix(value: str) -> str:
    tokens = value.split()
    while len(tokens) > 1 and tokens[-1].strip(" .,-") in PRODUCT_LINE_TOKENS:
        tokens.pop()
    return " ".join(tokens).strip()


def protected_suffix_prefix(value: str) -> str:
    text = normalize_key(value)
    for prefix in sorted(SUFFIX_STRIP_PROTECTED_PREFIXES, key=len, reverse=True):
        if text == prefix or text.startswith(f"{prefix} "):
            return prefix
    return ""


def collapse_repeated_brand_prefix(value: str) -> str:
    tokens = normalize_key(value).split()
    if len(tokens) < 2:
        return " ".join(tokens)

    max_prefix_len = min(4, len(tokens) // 2)
    for size in range(max_prefix_len, 0, -1):
        first = " ".join(tokens[:size])
        second = " ".join(tokens[size : size * 2])
        if compact_key(first) == compact_key(second):
            return " ".join(tokens[:size] + tokens[size * 2 :]).strip()
    return " ".join(tokens)


def clean_carrefour_brand_key(raw_brand: str) -> str:
    text = normalize_key(raw_brand).strip(" .,-'")
    text = re.sub(r"\bcarrefour-le-marche\b", "carrefour le marche", text)
    text = re.sub(r"\b(bio|classic|extra|kids|original|selection|sensation)s?carrefour\b", r"\1 carrefour", text)
    text = re.sub(r"\bcarrefour\s+carrefour\b", "carrefour", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-'")
    if any(phrase in text for phrase in CARREFOUR_SUPPLIER_NOISE_PHRASES):
        return text

    if text.startswith("carrefour "):
        remainder = text[len("carrefour ") :].strip(" .,-'")
        if remainder.startswith("carrefour "):
            remainder = remainder[len("carrefour ") :].strip(" .,-'")
        if remainder.startswith("reflets de france"):
            text = "reflets de france"
        elif remainder.startswith("filiere qualite carrefour"):
            text = "filiere qualite carrefour"
        elif remainder.startswith("fqc"):
            text = "fqc"
        elif remainder:
            text = f"carrefour {remainder}"

    for line in sorted(CARREFOUR_CURATED_CLEAN_KEYS, key=len, reverse=True):
        if text == f"{line} carrefour" or text.startswith(f"{line} carrefour "):
            text = line
            break
        if text.startswith(f"{line} "):
            text = line
            break

    text = re.sub(r"classic'+$", "classic", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-'")
    return text


def is_carrefour_store_format_key(value: str) -> bool:
    key = clean_carrefour_brand_key(value)
    return any(
        key == store_format or key.startswith(f"{store_format} ")
        for store_format in CARREFOUR_STORE_FORMAT_KEYS
    )


def carrefour_store_format_candidate(value: str) -> str:
    key = clean_carrefour_brand_key(value)
    if key.startswith("carrefour le marche"):
        return "Carrefour Le Marché"
    return "Carrefour"


def is_carrefour_supplier_noise_key(value: str) -> bool:
    key = clean_carrefour_brand_key(value)
    return any(phrase in key for phrase in CARREFOUR_SUPPLIER_NOISE_PHRASES)


def matched_retailer_banner(value: str) -> str:
    text = normalize_key(value)
    for banner in sorted(RETAILER_BANNERS, key=len, reverse=True):
        if text == banner or text.startswith(f"{banner} "):
            return banner
    return ""


def retailer_line_remainder(value: str, banner: str) -> str:
    text = normalize_key(value)
    if text == banner:
        return ""
    if text.startswith(f"{banner} "):
        remainder = text[len(banner) + 1 :].strip(" .,-'")
        if remainder.startswith(f"{banner} "):
            remainder = remainder[len(banner) + 1 :].strip(" .,-'")
        return remainder
    return ""


def known_retailer_subbrand_alias(value: str) -> str:
    text = normalize_key(value)
    for retailer, subbrands in KNOWN_RETAILER_SUBBRANDS.items():
        for subbrand in sorted(subbrands, key=len, reverse=True):
            if text == f"{retailer} {subbrand}" or text == f"{subbrand} {retailer}":
                return subbrand
    return ""


def is_retailer_private_label_line(value: str) -> bool:
    banner = matched_retailer_banner(value)
    if not banner:
        return False
    remainder = retailer_line_remainder(value, banner)
    if not remainder:
        return False
    if known_retailer_subbrand_alias(value):
        return False
    return any(
        remainder == token
        or remainder.startswith(f"{token} ")
        or compact_key(remainder).startswith(compact_key(token))
        for token in RETAILER_PRIVATE_LABEL_LINE_TOKENS
    )


def load_confirmed_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    required = {"variant_brand", "canonical_brand", "action"}
    if not required.issubset(df.columns):
        return {}
    confirmed = df[df["action"].str.strip().str.lower() == "confirm"].copy()
    return {
        normalize_key(row["variant_brand"]): normalize_key(row["canonical_brand"])
        for _, row in confirmed.iterrows()
        if normalize_key(row["variant_brand"]) and normalize_key(row["canonical_brand"])
    }


def load_private_label_mappings(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    required = {
        "retailer_banner",
        "raw_brand_pattern",
        "canonical_brand",
        "action",
    }
    if not required.issubset(df.columns):
        return []
    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        pattern = normalize_key(row["raw_brand_pattern"])
        canonical = display_brand(row["canonical_brand"])
        action = normalize_key(row["action"]).replace(" ", "_")
        if not pattern or not canonical or action not in {"confirm", "manual_review"}:
            continue
        rows.append(
            {
                "retailer_banner": display_brand(row["retailer_banner"]),
                "pattern": pattern,
                "pattern_compact": compact_key(pattern),
                "canonical_brand": canonical,
                "market_scope": normalize_key(row.get("market_scope", "")),
                "action": action,
            }
        )
    return sorted(rows, key=lambda item: len(item["pattern_compact"]), reverse=True)


def private_label_match_values(value: str) -> list[str]:
    normalized = clean_carrefour_brand_key(value)
    collapsed = collapse_repeated_brand_prefix(normalized)
    values = [normalized]
    if collapsed and collapsed not in values:
        values.append(collapsed)

    for candidate in list(values):
        if candidate.startswith("carrefour "):
            remainder = retailer_line_remainder(candidate, "carrefour")
            if remainder and remainder not in values:
                values.append(remainder)
    return values


def curated_private_label_match(
    brand: str,
    country_or_market: str,
    private_label_mappings: list[dict[str, str]],
) -> dict[str, str] | None:
    match_values = private_label_match_values(brand)
    for mapping in private_label_mappings:
        for value in match_values:
            value_compact = compact_key(value)
            pattern_compact = mapping["pattern_compact"]
            if value_compact == pattern_compact:
                return mapping
    return None


def representative_by_compact_key(
    brand_counts: Counter[str],
    confirmed_aliases: dict[str, str],
) -> dict[str, str]:
    grouped: dict[str, Counter[str]] = {}
    for brand, count in brand_counts.items():
        key = compact_key(brand)
        if not key:
            continue
        grouped.setdefault(key, Counter())[brand] += count
    for canonical in confirmed_aliases.values():
        key = compact_key(canonical)
        if key:
            grouped.setdefault(key, Counter())[canonical] += 10_000_000

    reps: dict[str, str] = {}
    for key, counts in grouped.items():
        reps[key] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return reps


def candidate_for_brand(
    brand: str,
    country_or_market: str,
    brand_counts: Counter[str],
    confirmed_aliases: dict[str, str],
    compact_reps: dict[str, str],
    private_label_mappings: list[dict[str, str]],
) -> tuple[str, str, str, str, str, str, str]:
    cleaned_key = clean_carrefour_brand_key(brand)
    if is_carrefour_store_format_key(brand):
        return (
            carrefour_store_format_candidate(brand),
            "carrefour_store_format",
            "retailer_banner_or_store_format",
            "",
            cleaned_key,
            "manual_review_store_format",
            "Carrefour store-format/banner string; do not mix with private-label lines",
        )

    if is_carrefour_supplier_noise_key(brand):
        return (
            brand,
            "carrefour_supplier_noise_preserved",
            "none",
            "",
            cleaned_key,
            "manual_review",
            "Carrefour supplier/source string preserved; not curated for launch",
        )

    if cleaned_key in CARREFOUR_REVERSED_PRIVATE_LABEL_KEYS:
        return (
            CARREFOUR_REVERSED_PRIVATE_LABEL_KEYS[cleaned_key],
            "curated_private_label_mapping_reversed_order",
            "curated_private_label_mapping",
            "confirm",
            cleaned_key,
            "approve_alias",
            "curated Carrefour private-label mapping, reversed-order variant",
        )

    private_label_match = curated_private_label_match(
        brand,
        country_or_market,
        private_label_mappings,
    )
    if private_label_match:
        reason = f"curated_private_label_mapping_{private_label_match['action']}"
        decision = (
            "approve_alias"
            if private_label_match["action"] == "confirm"
            else "manual_review_private_label_line"
        )
        review_reason = (
            "curated Carrefour private-label mapping"
            if private_label_match["action"] == "confirm"
            else "curated Carrefour private-label mapping requires manual confirmation"
        )
        return (
            private_label_match["canonical_brand"],
            reason,
            "curated_private_label_mapping",
            private_label_match["action"],
            cleaned_key,
            decision,
            review_reason,
        )

    retailer_subbrand = known_retailer_subbrand_alias(brand)
    if retailer_subbrand:
        return retailer_subbrand, "retailer_subbrand_alias", "heuristic", "", cleaned_key, "", ""

    collapsed = collapse_repeated_brand_prefix(brand)
    if collapsed != brand:
        return collapsed, "repeated_prefix_collapsed", "heuristic", "", cleaned_key, "", ""

    if brand in confirmed_aliases:
        confirmed = confirmed_aliases[brand]
        if is_retailer_private_label_line(brand) and confirmed in RETAILER_BANNERS:
            return brand, "retailer_private_label_line_preserved", "heuristic", "", cleaned_key, "", ""
        return confirmed, "existing_confirmed_alias", "brand_alias_mapping", "", cleaned_key, "", ""

    if is_retailer_private_label_line(brand):
        return brand, "retailer_private_label_line_preserved", "heuristic", "", cleaned_key, "", ""

    legal_stripped = strip_legal_suffix(brand)
    if legal_stripped != brand and legal_stripped in brand_counts:
        return legal_stripped, "legal_suffix_removed", "heuristic", "", cleaned_key, "", ""

    if not protected_suffix_prefix(brand):
        product_line_stripped = strip_product_line_suffix(brand)
        if product_line_stripped != brand:
            compact = compact_key(product_line_stripped)
            candidate = compact_reps.get(compact, product_line_stripped)
            if candidate in brand_counts or candidate in confirmed_aliases.values():
                return candidate, "product_line_suffix_removed", "heuristic", "", cleaned_key, "", ""

    compact = compact_key(brand)
    compact_candidate = compact_reps.get(compact, brand)
    if compact_candidate != brand:
        return compact_candidate, "punctuation_spacing_variant", "heuristic", "", cleaned_key, "", ""

    return brand, "no_alias_suggestion", "none", "", cleaned_key, "", ""


def example_names(values: pd.Series, limit: int = 5) -> str:
    seen: list[str] = []
    for value in values.dropna().astype(str):
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.append(cleaned)
        if len(seen) >= limit:
            break
    return " | ".join(seen)


def variant_counts_text(group: pd.DataFrame) -> str:
    counts = (
        group.groupby("raw_brand", dropna=False)["product_name"]
        .size()
        .sort_values(ascending=False)
    )
    return "; ".join(f"{brand}={count}" for brand, count in counts.items())


def variants_text(group: pd.DataFrame) -> str:
    counts = (
        group.groupby("raw_brand", dropna=False)["product_name"]
        .size()
        .sort_values(ascending=False)
    )
    return "; ".join(str(brand) for brand in counts.index)


def mapping_reasons_text(values: pd.Series) -> str:
    counts = values.value_counts()
    return "; ".join(f"{reason}={count}" for reason, count in counts.items())


def mapping_sources_text(values: pd.Series) -> str:
    counts = values.value_counts()
    return "; ".join(f"{source}={count}" for source, count in counts.items())


def tokenish_contains(text: str, pattern: str) -> bool:
    compact_text = compact_key(text)
    compact_pattern = compact_key(pattern)
    if not compact_pattern:
        return False
    return compact_pattern in compact_text


def split_variant_text(variants: str) -> list[str]:
    return [normalize_key(variant) for variant in str(variants).split(";") if variant.strip()]


def is_child_variant(candidate: str, variant: str) -> bool:
    return variant != candidate and variant.startswith(f"{candidate} ")


def has_parent_portfolio_signal(candidate: str, variants: str) -> bool:
    guarded_terms = PARENT_PORTFOLIO_GUARDS.get(candidate, set())
    variant_texts = split_variant_text(variants)
    if candidate in PARENT_PORTFOLIO_GUARDS:
        if any(is_child_variant(candidate, variant) for variant in variant_texts):
            return True
        if any(tokenish_contains(variants, term) for term in guarded_terms):
            return True

    for parent, portfolio_terms in PARENT_PORTFOLIO_GUARDS.items():
        parent_in_candidate = tokenish_contains(candidate, parent)
        parent_in_variants = any(tokenish_contains(variant, parent) for variant in variant_texts)
        if not (parent_in_candidate or parent_in_variants):
            continue
        if any(
            tokenish_contains(candidate, term)
            or any(tokenish_contains(variant, term) for variant in variant_texts)
            for term in portfolio_terms
        ):
            return True
    return False


def has_parent_brand_mix_signal(candidate: str, variants: str) -> bool:
    values = [candidate] + split_variant_text(variants)
    for value in values:
        for parent in STRATEGIC_PARENT_PREFIXES:
            if (
                tokenish_contains(value, parent)
                and normalize_key(value) != parent
                and not has_parent_portfolio_signal(value, value)
            ):
                return True
    return False


def has_repeated_prefix_signal(candidate: str, variants: str) -> bool:
    values = [candidate] + split_variant_text(variants)
    return any(collapse_repeated_brand_prefix(value) != normalize_key(value) for value in values)


def has_private_label_subbrand_signal(candidate: str, variants: str) -> bool:
    if candidate not in PRIVATE_LABEL_RETAILER_GUARDS:
        return False
    if any(is_child_variant(candidate, variant) for variant in split_variant_text(variants)):
        return True
    guarded_terms = PRIVATE_LABEL_RETAILER_GUARDS[candidate]
    return any(tokenish_contains(variants, term) for term in guarded_terms)


def has_retailer_private_label_line_signal(candidate: str, variants: str) -> bool:
    if candidate not in RETAILER_BANNERS:
        return False
    for variant in split_variant_text(variants):
        if variant == candidate:
            continue
        if is_child_variant(candidate, variant) or is_retailer_private_label_line(variant):
            return True
    return False


def review_alias_cluster(row: pd.Series) -> tuple[str, str, str, str]:
    candidate = normalize_key(row["normalized_brand_candidate"])
    variants = str(row["raw_brand_variants"])
    mapping_reason = str(row.get("mapping_reason", ""))
    mapping_source = str(row.get("mapping_source", ""))
    row_decisions = str(row.get("row_decisions", ""))

    if "manual_review_store_format" in row_decisions:
        return (
            "manual_review_store_format",
            row["normalized_brand_candidate"],
            "Carrefour store-format/banner string; do not mix with private-label lines",
            "retailer_banner_or_store_format",
        )

    if "manual_review_private_label_line" in row_decisions:
        return (
            "manual_review_private_label_line",
            row["normalized_brand_candidate"],
            "curated Carrefour private-label mapping requires manual confirmation",
            "curated_private_label_mapping",
        )

    if "approve_alias" in row_decisions:
        return (
            "approve_alias",
            row["normalized_brand_candidate"],
            "curated Carrefour private-label mapping",
            "curated_private_label_mapping",
        )

    if "curated_private_label_mapping_manual_review" in mapping_reason:
        return (
            "manual_review_private_label_line",
            row["normalized_brand_candidate"],
            "curated Carrefour private-label mapping requires manual confirmation",
            "curated_private_label_mapping",
        )

    if "curated_private_label_mapping_confirm" in mapping_reason:
        return (
            "approve_alias",
            row["normalized_brand_candidate"],
            "curated Carrefour private-label mapping",
            "curated_private_label_mapping",
        )

    if "repeated_prefix_collapsed" in mapping_reason or has_repeated_prefix_signal(
        candidate, variants
    ):
        return (
            "manual_review_repeated_prefix",
            "",
            "dirty repeated brand prefix was detected or collapsed before alias review",
            mapping_source or "heuristic",
        )

    if has_retailer_private_label_line_signal(candidate, variants):
        return (
            "manual_review_private_label_line",
            "",
            "retailer private-label line should not collapse to retailer banner",
            mapping_source or "heuristic",
        )

    if candidate in GENERIC_STANDALONE_CANDIDATES:
        return (
            "reject_generic_alias",
            "",
            "normalized candidate is a generic descriptor, not a consumer-facing brand",
            mapping_source or "heuristic",
        )

    if has_private_label_subbrand_signal(candidate, variants):
        return (
            "manual_review",
            "",
            "private-label subbrand should not collapse to retailer-level brand",
            mapping_source or "heuristic",
        )

    if has_parent_portfolio_signal(candidate, variants):
        return (
            "defer_to_top_down_portfolio_mapping",
            "",
            "cluster includes portfolio-brand signal; ownership and brand level need top-down review",
            mapping_source or "heuristic",
        )

    if has_parent_brand_mix_signal(candidate, variants):
        return (
            "manual_review_parent_brand_mix",
            "",
            "strategic parent/company prefix is mixed with brand text and needs manual review",
            mapping_source or "heuristic",
        )

    return (
        "approve_alias",
        row["normalized_brand_candidate"],
        "mechanical spelling, punctuation, spacing, suffix, or confirmed-alias variant",
        mapping_source or "heuristic",
    )


def build_reviewed_decisions(review: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "country_or_market",
        "observed_market_region_codes",
        "category",
        "raw_brand_variants",
        "normalized_brand_candidate",
        "total_product_count",
        "example_product_names",
        "alias_review_decision",
        "approved_normalized_brand",
        "review_reason",
        "mapping_source",
    ]
    if review.empty:
        return pd.DataFrame(columns=columns)

    reviewed = review.copy()
    decisions = reviewed.apply(review_alias_cluster, axis=1, result_type="expand")
    reviewed["alias_review_decision"] = decisions[0]
    reviewed["approved_normalized_brand"] = decisions[1]
    reviewed["review_reason"] = decisions[2]
    reviewed["mapping_source"] = decisions[3]
    return reviewed[columns].sort_values(
        ["alias_review_decision", "total_product_count", "normalized_brand_candidate"],
        ascending=[True, False, True],
    )


def build_review_summary(reviewed: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "summary_level",
        "alias_review_decision",
        "category",
        "country_or_market",
        "cluster_count",
        "product_count",
    ]
    if reviewed.empty:
        return pd.DataFrame(columns=columns)

    frames: list[pd.DataFrame] = []
    for level, group_cols in [
        ("alias_review_decision", ["alias_review_decision"]),
        ("category", ["alias_review_decision", "category"]),
        ("country_or_market", ["alias_review_decision", "country_or_market"]),
    ]:
        summary = (
            reviewed.groupby(group_cols, dropna=False)
            .agg(
                cluster_count=("normalized_brand_candidate", "size"),
                product_count=("total_product_count", "sum"),
            )
            .reset_index()
        )
        summary["summary_level"] = level
        if "category" not in summary.columns:
            summary["category"] = ""
        if "country_or_market" not in summary.columns:
            summary["country_or_market"] = ""
        frames.append(summary[columns])

    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values(
        ["summary_level", "alias_review_decision", "product_count"],
        ascending=[True, True, False],
    )


def is_carrefour_audit_row(row: pd.Series) -> bool:
    haystack = " ".join(
        str(row.get(col, ""))
        for col in [
            "raw_brand_variants",
            "normalized_brand_candidate",
            "approved_normalized_brand",
        ]
    )
    normalized = normalize_key(haystack)
    return (
        "carrefour" in normalized
        or "reflets de france" in normalized
        or "filiere qualite" in normalized
        or re.search(r"\bsimpl\b", normalized) is not None
        or re.search(r"\bfqc\b", normalized) is not None
    )


def build_carrefour_audit(reviewed: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    columns = [
        "country_or_market",
        "observed_market_region_codes",
        "category",
        "raw_brand_variants",
        "normalized_brand_candidate",
        "approved_normalized_brand",
        "alias_review_decision",
        "mapping_source",
        "review_reason",
        "total_product_count",
        "example_product_names",
    ]
    if reviewed.empty:
        audit = pd.DataFrame(columns=columns)
    else:
        audit = reviewed[reviewed.apply(is_carrefour_audit_row, axis=1)].copy()
        audit = audit[columns].sort_values(
            ["mapping_source", "total_product_count", "normalized_brand_candidate"],
            ascending=[True, False, True],
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_path, index=False, encoding="utf-8-sig")
    return audit


def build_carrefour_row_level_audit(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    columns = [
        "raw_brand",
        "cleaned_brand_key",
        "approved_normalized_brand",
        "alias_review_decision",
        "mapping_source",
        "review_reason",
        "product_count",
        "country_or_market",
        "observed_market_region_codes",
        "category",
        "example_product_names",
    ]

    carrefour_like = df[
        df.apply(
            lambda row: is_carrefour_audit_row(
                pd.Series(
                    {
                        "raw_brand_variants": row["raw_brand"],
                        "normalized_brand_candidate": row["normalized_brand_candidate"],
                        "approved_normalized_brand": (
                            row["normalized_brand_candidate"]
                            if row["row_alias_review_decision"]
                            else ""
                        ),
                    }
                )
            ),
            axis=1,
        )
    ].copy()

    rows: list[dict[str, object]] = []
    group_cols = [
        "raw_brand",
        "cleaned_brand_key",
        "normalized_brand_candidate",
        "mapping_source",
        "row_alias_review_decision",
        "row_review_reason",
        "primary_country",
        "observed_market_region_codes",
        "query_category",
    ]
    for keys, group in carrefour_like.groupby(group_cols, dropna=False):
        (
            raw_brand,
            cleaned_key,
            normalized_candidate,
            mapping_source,
            row_decision,
            row_reason,
            country,
            region_codes,
            category,
        ) = keys
        decision = row_decision
        approved = normalized_candidate if row_decision else ""
        reason = row_reason
        if not decision:
            pseudo_row = pd.Series(
                {
                    "normalized_brand_candidate": normalized_candidate,
                    "raw_brand_variants": raw_brand,
                    "mapping_reason": "",
                    "mapping_source": mapping_source,
                }
            )
            decision, approved, reason, mapping_source = review_alias_cluster(pseudo_row)
        rows.append(
            {
                "raw_brand": raw_brand,
                "cleaned_brand_key": cleaned_key,
                "approved_normalized_brand": approved,
                "alias_review_decision": decision,
                "mapping_source": mapping_source,
                "review_reason": reason,
                "product_count": len(group),
                "country_or_market": country,
                "observed_market_region_codes": region_codes,
                "category": category,
                "example_product_names": example_names(group["product_name"]),
            }
        )

    audit = pd.DataFrame(rows, columns=columns)
    if not audit.empty:
        audit = audit.sort_values(
            ["mapping_source", "product_count", "raw_brand"],
            ascending=[True, False, True],
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_path, index=False, encoding="utf-8-sig")
    return audit


def assert_carrefour_private_label_mapping(reviewed: pd.DataFrame) -> None:
    if reviewed.empty:
        return

    forbidden_patterns = [
        "carrefour bio",
        "carrefour classic",
        "carrefour extra",
        "carrefour kids",
        "carrefour original",
        "carrefour selection",
        "carrefour light",
        "carrefour sensation",
    ]
    for pattern in forbidden_patterns:
        bad_rows = reviewed[
            reviewed["raw_brand_variants"].map(lambda value: tokenish_contains(value, pattern))
            & reviewed["approved_normalized_brand"].map(
                lambda value: normalize_key(value) == "carrefour"
            )
        ]
        if not bad_rows.empty:
            raise AssertionError(
                f"Curated Carrefour line collapsed to Carrefour: {pattern}"
            )

    expected_mappings = {
        "carrefour bio": "Carrefour Bio",
        "carrefour classic": "Carrefour Classic",
        "carrefour extra": "Carrefour Extra",
        "carrefour original": "Carrefour Original",
        "carrefour kids": "Carrefour Kids",
        "carrefour sensation": "Carrefour Sensation",
        "carrefour sensation vegetal": "Carrefour Sensation VÉGÉtal",
        "my carrefour baby": "My Carrefour Baby",
        "carrefour companino": "Carrefour Companino",
        "companino": "Carrefour Companino",
        "reflets de france": "Reflets de France",
        "simpl": "Simpl",
        "filiere qualite carrefour": "Filière Qualité Carrefour",
    }
    for pattern, expected in expected_mappings.items():
        rows = reviewed[
            reviewed["normalized_brand_candidate"].map(normalize_key).eq(
                normalize_key(expected)
            )
            & reviewed["mapping_source"].eq("curated_private_label_mapping")
        ]
        if rows.empty:
            continue
        incorrect = rows[
            rows["approved_normalized_brand"].map(normalize_key)
            != normalize_key(expected)
        ]
        if not incorrect.empty:
            raise AssertionError(
                f"Curated Carrefour mapping mismatch for {pattern}; expected {expected}"
            )


def assert_carrefour_row_level_mapping(audit: pd.DataFrame) -> None:
    if audit.empty:
        return

    known = audit[
        audit["cleaned_brand_key"].isin(CARREFOUR_CONFIRMED_CLEAN_KEYS)
    ].copy()
    if known.empty:
        return

    bad_source = known[
        known["mapping_source"].isin({"heuristic", "none"})
        | known["mapping_source"].eq("")
    ]
    if not bad_source.empty:
        examples = bad_source[
            ["raw_brand", "cleaned_brand_key", "mapping_source"]
        ].head(10)
        raise AssertionError(
            "Known Carrefour cleaned keys fell through to heuristic/none:\n"
            + examples.to_string(index=False)
        )

    collapsed = known[
        known["approved_normalized_brand"].map(normalize_key).eq("carrefour")
    ]
    if not collapsed.empty:
        examples = collapsed[
            ["raw_brand", "cleaned_brand_key", "approved_normalized_brand"]
        ].head(10)
        raise AssertionError(
            "Known Carrefour private-label line collapsed to Carrefour:\n"
            + examples.to_string(index=False)
        )

    raw_string_outputs = known[
        known["approved_normalized_brand"].eq(known["raw_brand"])
        | known["approved_normalized_brand"].eq(known["cleaned_brand_key"])
    ]
    if not raw_string_outputs.empty:
        examples = raw_string_outputs[
            ["raw_brand", "cleaned_brand_key", "approved_normalized_brand"]
        ].head(10)
        raise AssertionError(
            "Known Carrefour keys approved lowercase/raw strings:\n"
            + examples.to_string(index=False)
        )


def build_review(input_path: Path, output_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    usecols = [
        "product_name",
        "brands",
        "primary_brand",
        "query_category",
        "primary_country",
        "observed_market_region_codes",
    ]
    df = pd.read_csv(
        input_path,
        encoding="utf-8-sig",
        dtype=str,
        usecols=lambda col: col in usecols,
        low_memory=False,
    ).fillna("")

    df["raw_brand"] = df["brands"].map(raw_primary_brand)
    df = df[~df["raw_brand"].isin(UNKNOWN_VALUES)].copy()
    df = df[df["raw_brand"] != ""].copy()

    brand_counts = Counter(df["raw_brand"])
    confirmed_aliases = load_confirmed_aliases(ALIAS_PATH)
    private_label_mappings = load_private_label_mappings(PRIVATE_LABEL_MAPPING_PATH)
    compact_reps = representative_by_compact_key(brand_counts, confirmed_aliases)

    candidate_keys = df[["raw_brand", "primary_country"]].drop_duplicates()
    candidate_map = {
        (row["raw_brand"], row["primary_country"]): candidate_for_brand(
            row["raw_brand"],
            row["primary_country"],
            brand_counts,
            confirmed_aliases,
            compact_reps,
            private_label_mappings,
        )
        for _, row in candidate_keys.iterrows()
    }
    df["normalized_brand_candidate"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][0],
        axis=1,
    )
    df["mapping_reason"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][1],
        axis=1,
    )
    df["mapping_source"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][2],
        axis=1,
    )
    df["private_label_action"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][3],
        axis=1,
    )
    df["cleaned_brand_key"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][4],
        axis=1,
    )
    df["row_alias_review_decision"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][5],
        axis=1,
    )
    df["row_review_reason"] = df.apply(
        lambda row: candidate_map[(row["raw_brand"], row["primary_country"])][6],
        axis=1,
    )

    candidate_rows = df[
        df["mapping_reason"].isin(
            {
                "existing_confirmed_alias",
                "legal_suffix_removed",
                "product_line_suffix_removed",
                "punctuation_spacing_variant",
                "repeated_prefix_collapsed",
                "retailer_subbrand_alias",
                "curated_private_label_mapping_confirm",
                "curated_private_label_mapping_manual_review",
                "carrefour_store_format",
            }
        )
    ].copy()
    candidate_rows = candidate_rows[
        candidate_rows["raw_brand"].str.strip()
        != candidate_rows["normalized_brand_candidate"].str.strip()
    ].copy()

    cluster_keys = [
        "primary_country",
        "observed_market_region_codes",
        "query_category",
        "normalized_brand_candidate",
    ]
    candidate_clusters = candidate_rows[cluster_keys].drop_duplicates()
    scoped = df.merge(candidate_clusters, on=cluster_keys, how="inner")

    rows: list[dict[str, object]] = []
    for keys, group in scoped.groupby(cluster_keys, dropna=False):
        country, region_codes, category, candidate = keys
        variants = sorted(group["raw_brand"].dropna().unique())
        variant_count = len(variants)
        has_curated_private_label = group["mapping_source"].eq(
            "curated_private_label_mapping"
        ).any()
        if variant_count < 2 and not has_curated_private_label:
            continue
        rows.append(
            {
                "country_or_market": country,
                "observed_market_region_codes": region_codes,
                "category": category,
                "normalized_brand_candidate": candidate,
                "raw_brand_variant_count": variant_count,
                "raw_brand_variants": variants_text(group),
                "raw_brand_variant_counts": variant_counts_text(group),
                "total_product_count": len(group),
                "example_product_names": example_names(group["product_name"]),
                "mapping_reason": mapping_reasons_text(
                    candidate_rows.merge(
                        group[["raw_brand", "primary_country"]].drop_duplicates(),
                        on=["raw_brand", "primary_country"],
                        how="inner",
                    )["mapping_reason"]
                ),
                "mapping_source": mapping_sources_text(
                    candidate_rows.merge(
                        group[["raw_brand", "primary_country"]].drop_duplicates(),
                        on=["raw_brand", "primary_country"],
                        how="inner",
                    )["mapping_source"]
                ),
                "row_decisions": mapping_reasons_text(
                    group["row_alias_review_decision"].replace("", pd.NA).dropna()
                ),
                "review_note": "",
            }
        )

    review = pd.DataFrame(rows)
    if review.empty:
        review = pd.DataFrame(
            columns=[
                "country_or_market",
                "observed_market_region_codes",
                "category",
                "normalized_brand_candidate",
                "raw_brand_variant_count",
                "raw_brand_variants",
                "raw_brand_variant_counts",
                "total_product_count",
                "example_product_names",
                "mapping_reason",
                "mapping_source",
                "row_decisions",
                "review_note",
            ]
        )
    else:
        review = review.sort_values(
            ["total_product_count", "raw_brand_variant_count", "normalized_brand_candidate"],
            ascending=[False, False, True],
        )

    review = review[
        [
            "country_or_market",
            "observed_market_region_codes",
            "category",
            "normalized_brand_candidate",
            "raw_brand_variant_count",
            "raw_brand_variants",
            "raw_brand_variant_counts",
            "total_product_count",
            "example_product_names",
            "mapping_reason",
            "mapping_source",
            "row_decisions",
            "review_note",
        ]
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_path, index=False, encoding="utf-8-sig")
    return review, df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--reviewed-output", default=str(DEFAULT_REVIEWED_OUTPUT))
    parser.add_argument("--summary-output", default=str(DEFAULT_SUMMARY_OUTPUT))
    parser.add_argument("--carrefour-audit-output", default=str(DEFAULT_CARREFOUR_AUDIT_OUTPUT))
    parser.add_argument(
        "--carrefour-row-audit-output",
        default=str(DEFAULT_CARREFOUR_ROW_AUDIT_OUTPUT),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    reviewed_output_path = Path(args.reviewed_output)
    summary_output_path = Path(args.summary_output)
    carrefour_audit_output_path = Path(args.carrefour_audit_output)
    carrefour_row_audit_output_path = Path(args.carrefour_row_audit_output)
    review, row_level = build_review(input_path, output_path)
    reviewed = build_reviewed_decisions(review)
    assert_carrefour_private_label_mapping(reviewed)
    summary = build_review_summary(reviewed)
    carrefour_row_audit = build_carrefour_row_level_audit(
        row_level,
        carrefour_row_audit_output_path,
    )
    assert_carrefour_row_level_mapping(carrefour_row_audit)
    carrefour_audit = build_carrefour_audit(reviewed, carrefour_audit_output_path)

    reviewed_output_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed.to_csv(reviewed_output_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_output_path, index=False, encoding="utf-8-sig")

    print("Bottom-up brand alias review")
    print(f"Run timestamp: {datetime.now().strftime('%Y%m%d_%H%M%S')}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Reviewed output: {reviewed_output_path}")
    print(f"Summary output: {summary_output_path}")
    print(f"Carrefour row-level audit output: {carrefour_row_audit_output_path}")
    print(f"Carrefour audit output: {carrefour_audit_output_path}")
    print(f"Clusters: {len(review):,}")
    if not review.empty:
        print(f"Products in clusters: {int(review['total_product_count'].sum()):,}")
        print("\nTop mapping_reason combinations:")
        print(review["mapping_reason"].value_counts().head(10).to_string())
    if not reviewed.empty:
        print("\nAlias review decisions:")
        print(
            reviewed["alias_review_decision"]
            .value_counts()
            .rename_axis("decision")
            .to_string()
        )
        print(f"\nCarrefour row-level audit rows: {len(carrefour_row_audit):,}")
        print(f"\nCarrefour audit rows: {len(carrefour_audit):,}")


if __name__ == "__main__":
    main()
