"""Consolidated Wave 2 nutritional EDA. Rebuilds the three named baseline CSVs."""
import csv
import hashlib
import os
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT))
from shared.beverage_segments import beverage_view_segment

MASTER = HERE.parents[2] / "01_ingestion/05_master_parquet/output/master_products.parquet"
CEREAL = HERE.parent / "01_nutritional_composition/lens1_cereal_master_v1.parquet"
METRICS = dict(energy="energy_kcal", protein="protein_100g", fat="fat_100g",
               saturated_fat="saturated_fat_100g", carbohydrates="carbs_100g",
               sugars="sugars_100g", fibre="fiber_100g", salt="salt_100g")
REGIONS = ("FR", "UK-IE", "US-CA")
FILES = ("subtype_assignments.csv", "nutrient_availability.csv", "nutrient_distributions.csv")
STATS = ("min", "p5", "q1", "median", "q3", "p95", "max")
PROFILE = ("barcode", "region", "category", "product_name", "off_categories", "off_brands_raw",
           "normalized_brand", "quantity", "reviewed_nutrition_category_decision", "reviewed_beverage_status")
DECISIONS = ("membership", "subtype", "confidence", "reason", "basis_group",
             "beverage_view_segment", "cereal_bar_review_flag", "cereal_review_type_code")
# Ordered product-form cues. Boundaries, plurals and accent folding are explicit.
PATTERNS = {
    "snacks": {
        "FROZEN_DESSERT": r"ice creams?|cremes? glacees?|sorbets?|frozen yogurts?|popsicles?|^glaces?$|^glaces? (?:au|a la|aux|en)",
        "CEREAL_PROTEIN_SNACK_BAR": r"(?:snack|cereal|protein|energy|granola|breakfast|oat|fruit|nut|seed|chewy) bars?|barres? (?:de |aux )?(?:cereales?|proteines?|fruits?)|barres? (?:proteinees?|energetiques?)|musliriegel",
        "POPCORN": r"pop ?corn|mais souffle pour aperitif",
        "CHIPS_CRISPS_PUFFS": r"(?:potato|corn|tortilla|vegetable|lentil|pita|kettle|plantain|banana) chips|crisps|chips de|chips|cheese puffs|souffles aperitifs|extruded snacks",
        "CRACKERS_PRETZELS": r"crackers?|pretzels?|bretzels?|breadsticks?|gressins?|rice cakes?|galettes? de riz|biscuits? aperitifs?",
        "BISCUITS_WAFERS": r"biscuits?|cookies?|wafers?|gaufrettes?|sables?|macarons?|shortbread|speculoos|palets bretons|galettes bretonnes",
        "SWEET_BAKERY": r"cakes?|gateaux?|madeleines?|brownies?|muffins?|baklava|gaufres?|sweet waffles?|honey waffles?|croissants?|pains? au chocolat|brioche[s]?|panettone|pandoro|pastries|patisseries?|chaussons?|galettes? des rois|doughnuts?|donuts?",
        "CHOCOLATE_CONFECTIONERY": r"chocolates?|chocolats?|pralines?|truffes? au chocolat|chocolate candies|chocolate bars?",
        "SUGAR_CONFECTIONERY": r"cand(?:y|ies)|bonbons?|confiseries?|confectioner(?:y|ies)|gumm(?:y|ies)|sweets|nougats?|lollipops?|sucettes?|marshmallows?|toffees?|licorice|reglisse|chewing gum|caramels?",
        "NUTS_SEEDS_SNACK_MIX": r"trail mixes|trail mix|snack mix(?:es)?|mixed nuts|roasted (?:peanuts|almonds|nuts|cashews)|(?:noix|arachides|amandes|cacahuetes) (?:grillees|salees)|snacking nuts",
        "FRUIT_SNACKS": r"fruit (?:snacks?|rolls?|strips?|leathers?)|dried fruits?|fruits seches|raisins secs",
        "OTHER": r"jerky|meat snacks?|wasabi peas|pork rinds|couennes de porc",
    },
    "dairy": {
        "MILK_PREPARATIONS": r"milk powders?|powdered milk|dried milk|laits? en poudre|infant formula|laits? infantiles?|growing up milk|condensed milks?|evaporated milks?|laits? concentres?",
        "CULTURED_DAIRY_DRINK": r"kefirs?|drink(?:ing|able) (?:yogurts?|yoghurts?)|(?:yogurts?|yoghurts?) drinks?|yaourts? a boire|laits? fermentes?|buttermilk|lait ribot",
        "DAIRY_DESSERT": r"dairy desserts?|desserts? lactes?|cremes? desserts?|custards?|flans?|puddings?|mousses?|riz au lait|rice puddings?|panna cotta|cremes? brulees?",
        "YOGURT_CULTURED_FRESH": r"yoghurts?|yogurts?|yaourts?|yoghourts?|skyr|quark|fromages? blancs?|petits? suisses?|faisselles?",
        "CHEESE": r"cheeses?|fromages?|cheddar|mozzarella|comte|emmentals?|camembert|brie|reblochons?|roqueforts?|morbiers?|beaufort|parmigiano|parmesan|pecorino|picodons?|grana padano|pont l eveque|ossau iraty|fourme d ambert|raclette|saint nectaire|ricotta|mascarpone|gruyere|gouda|feta|edam|gorgonzola",
        "BUTTER": r"butters?|beurres?|ghee",
        "CREAM": r"creams?|cremes?|sour cream|creme fraiche",
        "MILK": r"milks?|laits?|leche|whole milk|skimmed milk",
        "OTHER": r"milk permeate|lactoserum|whey",
    },
    "beverages": {
        "SYRUP_CONCENTRATE": r"syrups?|sirops?|sirups?|cordials?|squash|concentrates?|concentres?|concentrado|concentrated juice",
        "DRY_MIX": r"powders?|powdered|poudres?|dehydrated beverages|boissons deshydratees|drink mix(?:es)?|instant drink|hot cocoa mix|chocolat en poudre|effervescent tablets?|pastilles effervescentes",
        "TEA_COFFEE_RTD": r"iced teas?|ice tea|thes? glaces?|cold brew|iced coffee|cafe glace|canned coffee",
        "ALCOHOLIC_STYLE": r"alcoholic beverages|boissons alcoolisees|beers?|bieres?|lagers?|ales?|cidres?|ciders?|sangria|bordeaux|chardonnay|pinot noir|merlot|wines?|vins?|champagnes?|whisk(?:e)?y|vodka|liqueurs?|spirits|spiritueux|prosecco|bourbon|tequila",
        "PLANT_DRINK": r"(?:oat|soy|soya|almond|rice|cashew) (?:milk|drinks?)|(?:oat|soy|almond)milk|(?:boissons?|laits?) (?:d |de |au |a base de )?(?:soja|avoine|amande|riz)|plant based milk alternatives|plant drinks?|(?:almond|oat|soy) based drinks",
        "ENERGY_SPORTS_DRINK": r"energy drinks?|sports drinks?|electrolyte drinks?|boissons? (?:energisantes?|energetiques?|isotoniques?)|boissons? (?:pour|de) (?:le )?sport|red bull|gatorade",
        "JUICE_SMOOTHIE_NECTAR": r"juices?|jus|smoothies?|nectars?|zumos?|nektar",
        "SOFT_DRINK": r"sodas?|colas?|lemonades?|limonades?|citronnades?|soft drinks?|coca cola|pepsi|root beer|ginger ale",
        "WATER": r"waters?|eaux|eau|seltzer|agua|acqua",
        "FERMENTED_SOFT_DRINK": r"kombuchas?|water kefir|kefir de fruits",
        "TEA_COFFEE_PREPARATION": r"tea bags?|tea leaves|tea pods?|loose (?:leaf )?tea|tea sachets?|coffee (?:pods?|capsules?|beans?)|ground coffee|instant coffee|cafes? (?:moulus?|solubles?|en (?:dosettes|grains|capsules))|thes? en sachets|tisanes?|infusions?|thes? verts?|green teas?|black teas?|earl grey|cafe (?:extra filtre )?soluble",
        "SHAKE_FORMAT_UNCLEAR": r"nutrition(?:al)? shakes?|protein shakes?|meal replacement shakes?|milkshakes?",
        "OTHER": r"coconut milk|lait de coco|coconut cream|creme de coco",
    },
}
CONTRADICTIONS = {
    "snacks": r"(?:cake|pancake|bread|brownie|muffin|baking) mix(?:es)?|preparations? pour (?:gateaux?|patisseries?)|pizza dough|pate a pizza",
    "dairy": r"mac(?:aroni)? (?:and |n )?cheese|macaroni au fromage|cheese sauces?|sauces? (?:au|pour) fromage|dessert mixes?",
    "beverages": r"soy sauces?|sauces? soja|olive oils?|huiles? d olive|coconut oils?|huiles? de coco",
}
def compile_terms(expr):
    return re.compile(r"\b(?:" + expr + r")\b")


RULES = {cat: [(label, compile_terms(expr)) for label, expr in terms.items()]
         for cat, terms in PATTERNS.items()}
OUT = {cat: compile_terms(expr) for cat, expr in CONTRADICTIONS.items()}
GENERIC = {cat: compile_terms(expr) for cat, expr in {
    "snacks": r"snacks?|encas|aperitifs?|snacking", "dairy": r"dairies|dairy|produits laitiers|laitiers",
    "beverages": r"beverages?|boissons?|drinks?|bebidas?"}.items()}
BASE_FOOD = "per_100g_food"
BASE_LIQUID = "per_100ml_liquid"
PREP = "as_reported_preparation_basis_unverified"
UNKNOWN = "as_reported_basis_unresolved"
MIXED = "as_reported_cream_form_unverified"


@lru_cache(maxsize=48000)
def normalize(value):
    folded = unicodedata.normalize("NFKD", value or "").lower()
    return " ".join(re.findall("[a-z0-9]+", folded.encode("ascii", "ignore").decode()))


@lru_cache(maxsize=35000)
def match_form(category, text):
    if category == "beverages":
        # Reconstituted juice explicitly sold as juice is distinct from a concentrate for dilution.
        text = re.sub(r"\b(?:from concentrates?|a base de jus concentres?|a base de concentres?)\b", "", text)
        if re.search(r"\b(?:root beer|ginger beer|ginger ale)\b", text):
            return "SOFT_DRINK"
        if re.search(r"\b(?:kombucha|water kefir|kefir de fruits)\b", text):
            return "FERMENTED_SOFT_DRINK"
    if category == "snacks":
        text = re.sub(r"\b(?:marrons? glaces?|panettone glace)\b", lambda m: m[0].split()[0], text)
        text = re.sub(r"\bchocolate chips?\b", "", text) if re.search(r"\b(?:cookies?|brownies?|muffins?|cakes?|biscuits?)\b", text) else text
        text = re.sub(r"\b(?:chocolate chips?|pepites de chocolat)\b", "chocolate", text)
    if category == "dairy" and re.search(r"\b(?:ice cream|creme glacee|peanut butter|beurre de cacahuete)\b", text):
        return None
    for label, pattern in RULES[category]:
        if pattern.search(text):
            return label
    return None


def basis(category, subtype, name, view):
    if subtype in {"OUT", "CATEGORY_UNKNOWN"}:
        return UNKNOWN
    if category == "cereal":
        if subtype == "OATS" or re.search(r"\b(?:porridge|prepared|ready to eat oatmeal|overnight oats)\b", name):
            return "as_reported_oats_preparation_unverified"
        return BASE_FOOD
    if category == "snacks":
        return BASE_FOOD
    if category == "dairy":
        if subtype == "MILK_PREPARATIONS":
            return PREP
        if subtype in {"MILK", "CULTURED_DAIRY_DRINK"}:
            return BASE_LIQUID
        if subtype == "CREAM":
            return MIXED
        return UNKNOWN if subtype in {"UNRESOLVED", "OTHER"} else BASE_FOOD
    if subtype in {"SYRUP_CONCENTRATE", "DRY_MIX", "TEA_COFFEE_PREPARATION"}:
        return PREP
    if subtype == "ALCOHOLIC_STYLE":
        return BASE_LIQUID
    if subtype in {"SHAKE_FORMAT_UNCLEAR", "OTHER", "UNRESOLVED"}:
        return UNKNOWN
    if view == "beverage_preparations_and_alcohol":
        return "as_reported_conflicting_beverage_form"
    return BASE_LIQUID


@lru_cache(maxsize=24000)
def tag_evidence(category, tags):
    texts = [normalize(re.sub(r"^\s*[a-z]{2}:", "", part)) for part in tags.split(",")]
    for text in reversed(texts):
        hit = match_form(category, text)
        if hit:
            return hit, text
    return None, ""


def classify(row, cereals):
    cat = row["category"]
    name = normalize(row["product_name"])
    if cat == "cereal":
        cr = cereals.pop((row["region"], row["barcode"]))
        member, code = cr["effective_membership"], cr["effective_type_code"]
        subtype = "CATEGORY_UNKNOWN" if member == "UNKNOWN" else code
        return (member, subtype, cr["confidence"] or "NOT_RATED", cr["decision_source"],
                basis(cat, subtype, name, ""), "", cr["original_bar_form_review"], code)
    tags = row["off_categories"] or ""
    all_tags = normalize(tags)
    view = beverage_view_segment(cat, row["product_name"], tags) if cat == "beverages" else ""
    n = match_form(cat, name)
    t, evidence = tag_evidence(cat, tags)
    # A contradiction must be corroborated by a category tag. No record is deleted.
    if OUT[cat].search(name) and OUT[cat].search(all_tags) and not row["reviewed_beverage_status"]:
        return ("NO", "OUT", "HIGH", "outside category form in name and tags", UNKNOWN, view, "", "")
    if cat == "dairy" and re.fullmatch(r"(?:bio |organic )?(?:datteln getrocknet|dried dates|dattes sechees)", name):
        return ("UNKNOWN", "CATEGORY_UNKNOWN", "LOW", "whole-product dried-fruit name conflicts with dairy assignment", UNKNOWN, view, "", "")
    if (OUT[cat].search(name) or OUT[cat].search(all_tags)) and not row["reviewed_beverage_status"]:
        return ("UNKNOWN", "CATEGORY_UNKNOWN", "LOW", "possible outside format; only one evidence source supports it", UNKNOWN, view, "")
    if n == t and n:
        sub, conf, reason = n, "HIGH", "name and specific tag: " + evidence
    elif n and t:
        # Named whole-product forms can be more specific than ingredient/parent tags.
        if n in {"CEREAL_PROTEIN_SNACK_BAR", "FROZEN_DESSERT", "POPCORN", "CULTURED_DAIRY_DRINK",
                 "MILK_PREPARATIONS", "DRY_MIX", "SYRUP_CONCENTRATE", "TEA_COFFEE_RTD"}:
            sub, conf, reason = n, "MEDIUM", "explicit named format; different tag: " + evidence
        elif (cat, n, t) in {("snacks", "CRACKERS_PRETZELS", "BISCUITS_WAFERS"),
                             ("dairy", "YOGURT_CULTURED_FRESH", "CHEESE")}:
            sub, conf, reason = n, "MEDIUM", "specific named format over broader category tag: " + evidence
        elif (cat, n, t) in {("dairy","MILK","CHEESE"), ("dairy","MILK","YOGURT_CULTURED_FRESH"),
                             ("snacks","CHOCOLATE_CONFECTIONERY","BISCUITS_WAFERS"),
                             ("snacks","CHOCOLATE_CONFECTIONERY","SWEET_BAKERY"),
                             ("beverages","WATER","JUICE_SMOOTHIE_NECTAR")}:
            sub, conf, reason = t, "MEDIUM", "specific product tag over ingredient wording: " + evidence
        else:
            sub, conf, reason = "UNRESOLVED", "LOW", f"conflicting name {n} and tag {t}: {evidence}"
    elif n or t:
        sub, conf = n or t, "MEDIUM"
        reason = "named product format" if n else "specific tag: " + evidence
    else:
        supported = bool(GENERIC[cat].search(name + " " + all_tags))
        sub = "UNRESOLVED" if supported else "CATEGORY_UNKNOWN"
        conf, reason = "LOW", "broad category only" if supported else "insufficient independent category evidence"
    member = "UNKNOWN" if sub == "CATEGORY_UNKNOWN" else "YES"
    return member, sub, conf, reason, basis(cat, sub, name, view), view, "", ""


def read_cereals():
    fields = ["region", "barcode", "effective_membership", "effective_type_code", "confidence",
              "decision_source", "original_bar_form_review"]
    table = pq.read_table(CEREAL, columns=fields)
    result = {(r["region"], r["barcode"]): r for r in table.to_pylist()}
    if len(result) != table.num_rows or len(result) != 17180:
        raise ValueError("Cereal master key mismatch.")
    return result


def collect(folder):
    cereals = read_cereals()
    frames = []
    fields = list(PROFILE) + ["product_scope_eligible", "include_in_product_table"]
    numeric = [field + suffix for field in METRICS.values() for suffix in ("", "_off_raw", "_missing")]
    keys = set()
    with (folder / FILES[0]).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow([*PROFILE, *DECISIONS])
        for batch in pq.ParquetFile(MASTER).iter_batches(columns=fields + numeric, batch_size=4096):
            b = batch.filter(batch["product_scope_eligible"])
            groups = []
            for row in b.select(fields).to_pylist():
                key = row["barcode"], row["region"], row["category"]
                if key in keys or not isinstance(key[0], str) or row["include_in_product_table"] != 1:
                    raise ValueError(f"Unexpected governed assignment: {key}")
                keys.add(key)
                result = classify(row, cereals)
                writer.writerow([*(row[f] for f in PROFILE), *result])
                groups.append((key[1], key[2], result[1], result[4]))
            frame = pd.DataFrame(groups, columns=["region", "category", "subtype", "basis_group"])
            data = b.select(numeric).to_pandas()
            for metric, field in METRICS.items():
                working = data[field].to_numpy(dtype=float, na_value=np.nan)
                raw = data[field + "_off_raw"].to_numpy(dtype=float, na_value=np.nan)
                cap = 900 if metric == "energy" else 50 if metric == "salt" else 100
                valid = (np.isfinite(working) & (working >= 0) & (working <= cap) & (working == raw)
                         & data[field + "_missing"].eq(0).fillna(False).to_numpy(dtype=bool))
                frame[metric] = np.where(valid, working, np.nan)
                frame[metric + "_source"] = ~np.isnan(raw)
                frame[metric + "_working"] = ~np.isnan(working)
                frame[metric + "_zero"] = working == 0
            frames.append(frame)
    if cereals or len(keys) != 376845:
        raise ValueError("Approved population or cereal join did not reconcile.")
    data = pd.concat(frames, ignore_index=True)
    for field in ["region", "category", "subtype", "basis_group"]:
        data[field] = data[field].astype("category")
    return data


def percent(count, denominator):
    return round(count * 100 / denominator, 4) if denominator else None


def summarize(region, cat, subtype, block, availability, distributions):
    total = len(block)
    row = dict(region=region, category=cat, subtype=subtype, eligible_n=total)
    for metric in METRICS:
        for label, count in (("source_available", block[metric + "_source"].sum()),
                             ("working_available", block[metric + "_working"].sum()),
                             ("valid", block[metric].count())):
            row[f"{metric}_{label}_n"] = int(count)
            row[f"{metric}_{label}_pct"] = percent(int(count), total)
        row[f"{metric}_observed_zero_n"] = int(block[metric + "_zero"].sum())
    availability.append(row)
    strata = list(block.groupby("basis_group", observed=True, sort=True)) if total else [("no_observations", block)]
    for unit, subset in strata:
        for metric in METRICS:
            vals = subset[metric].dropna().to_numpy(dtype=float)
            n = len(vals)
            record = dict(region=region, category=cat, subtype=subtype, basis_group=unit, metric=metric,
                          nutrient_unit="kcal" if metric == "energy" else "g", eligible_n=len(subset),
                          valid_n=n, valid_zero_n=int((vals == 0).sum()), small_n=n < 30)
            record.update(dict.fromkeys((*STATS, "iqr_low_fence", "iqr_high_fence", "outlier_low_n",
                                         "outlier_high_n", "outlier_n", "outlier_pct")))
            if n:
                quantiles = np.quantile(vals, [0, .05, .25, .5, .75, .95, 1], method="linear")
                record.update(zip(STATS, quantiles))
                iqr = record["q3"] - record["q1"]
                lo, hi = record["q1"] - 1.5 * iqr, record["q3"] + 1.5 * iqr
                below, above = int((vals < lo).sum()), int((vals > hi).sum())
                record.update(iqr_low_fence=lo, iqr_high_fence=hi, outlier_low_n=below, outlier_high_n=above,
                              outlier_n=below + above, outlier_pct=percent(below + above, n))
            distributions.append(record)


def tables(data, folder):
    availability, distributions = [], []
    for cat, category in data.groupby("category", observed=True, sort=True):
        subtypes = sorted(category["subtype"].unique())
        for region in REGIONS:
            block = category[category["region"] == region]
            summarize(region, cat, "ALL", block, availability, distributions)
            for subtype in subtypes:
                summarize(region, cat, subtype, block[block["subtype"] == subtype], availability, distributions)
    for name, records in zip(FILES[1:], [availability, distributions], strict=True):
        with (folder / name).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print(len(data), "assignments;", len(availability), "availability rows;", len(distributions), "distribution rows")


def main():
    with MASTER.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != "ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912":
            raise ValueError("Expected corrected Wave 2 master.")
    with CEREAL.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != "2f3859a401fada540b119424a91b2a924db6c084320f175cb0c8a58119027837":
            raise ValueError("Expected the validated Lens 1 cereal master v1.")
    with TemporaryDirectory(dir=HERE) as temp:
        folder = Path(temp)
        data = collect(folder)
        tables(data, folder)
        for filename in FILES:
            os.replace(folder / filename, HERE / filename)


if __name__ == "__main__":
    main()
