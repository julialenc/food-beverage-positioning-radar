"""Current-wave beverage eligibility overlay; source OFF records stay unchanged.

Only exact reviewed (barcode, region) decisions and narrowly corroborated
product/category rules can block a beverage. Missing overlay means that no
current-wave cleaning decision has been supplied, not that a product was
reviewed and approved.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

RULE_VERSION = "beverage_current_wave_v1"
ROOT = Path(__file__).resolve().parents[1]
DECISIONS_PATH = ROOT / "presentations/segmentation/beverage_final_v1/eligibility_decisions.csv"
ELIGIBLE_KEYS_PATH = ROOT / "presentations/segmentation/beverage_final_v1/segmentation_beverage_eligible_keys.csv"

# Require both explicit product form and matching specific category metadata.
# Broad parent tags and nutrition never decide eligibility.
_RULES = (
    ("explicit_sauce", re.compile(r"\b(?:sauce|mayonnaise|ketchup|salad dressing|vinaigrette)\b", re.I),
     re.compile(r"\b(?:sauces?|mayonnaises?|dressings?|vinaigrettes?)\b", re.I)),
    ("explicit_edible_oil", re.compile(r"\b(?:olive|sunflower|rapeseed|canola|vegetable|sesame) oil\b", re.I),
     re.compile(r"\b(?:edible oils?|vegetable oils?|olive oils?|cooking oils?)\b", re.I)),
    ("explicit_solid_food", re.compile(r"\b(?:hummus|muesli|beef jerky|ham slices|chocolate bars?)\b", re.I),
     re.compile(r"\b(?:hummus|muesli|jerky|hams?|chocolate bars?)\b", re.I)),
)
_PREPARATION = re.compile(
    r"\b(?:drink|beverage|boisson|cocktail|smoothie|syrup|sirop|squash|cordial|"
    r"mix|powder|poudre|tablet|pastille|brew|infusion|tea|thé|coffee|café)\b", re.I
)


def explicit_non_beverage_rule(product_name: str, off_categories: str) -> str | None:
    """Return a narrow, corroborated rule ID or None; reviewed GTINs override."""
    name, cats = product_name or "", off_categories or ""
    if _PREPARATION.search(name):
        return None
    for rule_id, name_re, cat_re in _RULES:
        if name_re.search(name) and cat_re.search(cats):
            return rule_id
    return None


def load_decisions(path: Path = DECISIONS_PATH) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    decisions = {(r["barcode"], r["region"]): r for r in rows}
    if len(decisions) != len(rows):
        raise ValueError("Duplicate exact beverage eligibility key")
    if any(r["status"] not in {"eligible", "excluded", "hold"} or
           r["rule_version"] != RULE_VERSION for r in rows):
        raise ValueError("Invalid beverage eligibility overlay")
    return decisions


def blocked_keys(path: Path = DECISIONS_PATH) -> set[tuple[str, str]]:
    """Exact regional holds/exclusions for app and analytical consumers."""
    decisions = load_decisions(path)
    return {key for key, row in decisions.items() if row["status"] in {"excluded", "hold"}}


def current_wave_eligible_keys(path: Path = ELIGIBLE_KEYS_PATH) -> set[tuple[str, str]]:
    """Exact regional keys for downstream beverage segmentation and RUN 06B.

    A missing current-wave sidecar fails closed; no frozen RUN 03/06B artifact
    is rewritten by this handoff.
    """
    if not path.exists():
        raise FileNotFoundError(f"Current-wave eligibility sidecar missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = {(row["barcode"], row["region"]) for row in rows}
    if len(keys) != len(rows) or any(row["category"] != "beverages" for row in rows):
        raise ValueError("Invalid current-wave beverage eligibility keys")
    return keys
