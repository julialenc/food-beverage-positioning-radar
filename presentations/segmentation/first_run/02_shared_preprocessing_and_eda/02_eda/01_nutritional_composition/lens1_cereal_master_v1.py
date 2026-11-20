"""Build the Lens 1 cereal assignment master and print the six H2 coverage cells."""
import csv
import hashlib
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[2] / "01_ingestion/05_master_parquet/output/master_products.parquet"
MASTER_HASH = "ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912"
REVIEW = HERE / "lens1_cereal_classification.csv"
REVIEW_HASH = "912c6fce23a194ccc0eea3ffc4b8fe298e1dd6e47827e4416be60a6e10c7bcce"
OUTPUT = HERE / "lens1_cereal_master_v1.parquet"
REGIONS = {"fr": "FR", "uk_ie": "UK-IE", "us_ca": "US-CA"}
TYPE_CODES = {"granola": "GRANOLA", "flakes": "FLAKES", "oats": "OATS", "filled": "FILLED",
              "puffs": "PUFFED", "wheat biscuits": "WHEAT", "muesli": "MUESLI"}
# Five previously identified original assignments retain their original category and proposed format.
BAR_REVIEW = {"0016000503564", "0016000503571", "0030000438312", "0846675002457", "0016000507272"}
REVIEW_FIELDS = ("review_cereal", "review_type", "type_code", "confidence", "manual_review",
                 "manual_question", "decision_reason", "decision_basis", "evidence_source_url")
NUTRIENTS = ("energy_kcal", "sugars_100g", "protein_100g", "fat_100g", "saturated_fat_100g",
             "carbs_100g", "fiber_100g", "salt_100g")
SOURCE_FIELDS = ["barcode", "region", "category", "assignment_countries", "product_scope_eligible",
                 "reviewed_nutrition_category_decision", "product_name", "off_categories", "query_category",
                 "off_brands_raw", "brands", "normalized_brand", "image_url", "include_in_product_table",
                 "nutrition_quality_status", "nutrition_quality_reason", "outlier_type", "warning_flag",
                 "warning_types", "warning_summary",
                 *(key + suffix for key in NUTRIENTS for suffix in ("", "_off_raw", "_missing"))]
FORMAT_FLAGS = ["h2_format_candidate", "original_bar_form_review"]
NUTRITION_FLAGS = ["h2_both_present", "h2_numeric_valid", "h2_missing_flags_agree", "h2_pair_valid"]
TEXT_FIELDS = ["original_screen_status", "original_format", "original_cereal_proposal",
               "original_type_proposal", *REVIEW_FIELDS, "effective_membership", "effective_type_code",
               "decision_source", "h2_pair_status"]


def normalize(text):
    ascii_text = unicodedata.normalize("NFKD", text or "").lower().encode("ascii", "ignore").decode()
    return " ".join(re.findall("[a-z0-9]+", ascii_text))


def matches(pattern, text):
    return re.search(r"\b(?:" + pattern + r")\b", text) is not None


def category_tags(text):
    return [normalize(re.sub(r"^[a-z]{2}:", "", tag.strip())) for tag in (text or "").split(",")]


# Keep the historical screening vocabulary separate from the second-pass decisions.
GRANOLA = (r"granolas?|(?:mueslis?|muslis?) (?:crisp|crunch)|crunchy (?:cereal )?clusters?|"
           r"cereal clusters?|pepites de cereales croustillantes|"
           r"(?:mueslis?|muslis?) (?:croustillant\w*|crunchy|knusper\w*)|"
           r"crunchy (?:mueslis?|muslis?)|knuspermusli")
FORMATS = {
    "oats": (r"porridge|oatmeal|oat meal|rolled oats?|oat flakes?|quick (?:cooking )?oats?|"
             r"instant oats?|steel cut oats?|flocons d avoine|haferflocken|copos de avena"),
    "wheat biscuits": r"wheat bisks?|wheat biscuits?|shredded wheat",
    "flakes": (r"cornflakes?|corn flakes?|bran flakes?|wheat flakes?|rice flakes?|frosted flakes?|"
               r"extruded (?:wheat )?flakes?|flocons extrudes|petales(?: de (?:ble|mais))?|"
               r"whole grain flakes?|multigrain flakes?|multicereal flakes?"),
    "puffs": (r"puffed (?:grains?|rice|wheat|cereals?)|(?:riz|ble|grains?|cereales?) souffl\w*|"
              r"hoops?|loops?|puffs?|cereal balls?|honey cereal balls|boules de cereales"),
}
FILLED = r"filled cereals?|cereales (?:pour petit dejeuner )?fourrees"
OTHER_SCREEN = (r"granola bars?|cereal bars?|breakfast bars?|snack bars?|energy bars?|protein bars?|"
                r"barres? (?:de |aux )?cereales?|barres? granola|cookies?|pie dough|pie crusts?|"
                r"muffins?|pancake mix|waffles?|infant cereals?|baby cereals?|cereales infantiles|"
                r"baby foods?|granola bites?|cereal bites?|biscuits? granola|biscuits? au muesli|"
                r"granola biscuits?|yogurts?|yoghurts?|yaourts?|overnight oats?|prepared porridge|"
                r"ready to eat porridge|bircher|grits")


def original_formats(text):
    formats = {name for name, pattern in FORMATS.items() if matches(pattern, text)}
    if matches(GRANOLA, text):
        formats.add("granola")
    elif matches(r"mueslis?|muslis?", text):
        formats.add("muesli")
    if matches(FILLED, text) and not matches(r"non fourrees|unfilled", text):
        formats.add("filled")
    return formats


def held(name, tags):
    named = original_formats(name)
    tagged = set().union(*(original_formats(tag) for tag in tags))
    if "granola" in named | tagged:
        tagged.discard("muesli")
    if matches(r"weetabix original|original weetabix", name):
        named.add("wheat biscuits")
    if any(matches(OTHER_SCREEN, text) for text in [name, *tags]):
        return True
    return len(named | tagged) != 1 or (not named and tagged == {"muesli"})


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_reviews():
    if digest(REVIEW) != REVIEW_HASH:
        raise ValueError("The decision layer differs from the validated v1 input.")
    reviews = {}
    for row in csv_rows(REVIEW):
        key = (REGIONS[row["region"]], row["GTIN"])
        if key in reviews:
            raise ValueError(f"Duplicate review key: {key}")
        reviews[key] = row
    if len(reviews) != 6700:
        raise ValueError("Review keys differ from the held population.")
    return reviews


def decisions(row, reviews):
    name = normalize(row["product_name"])
    tags = category_tags(row["off_categories"])
    key = row["region"], row["barcode"]
    if held(name, tags):
        review = reviews.pop(key)
        details = {field: review[field] or None for field in REVIEW_FIELDS}
        details.update(original_screen_status="held", original_format=None,
                       original_cereal_proposal=review["cereal?"] or None,
                       original_type_proposal=review["type"] or None,
                       effective_membership=review["review_cereal"], effective_type_code=review["type_code"],
                       decision_source="review_layer")
    else:
        if key in reviews:
            raise ValueError(f"Unexpected reviewed key outside held cohort: {key}")
        named = original_formats(name)
        tagged = set().union(*(original_formats(tag) for tag in tags))
        if "granola" in named | tagged:
            tagged.discard("muesli")
        if matches(r"weetabix original|original weetabix", name):
            named.add("wheat biscuits")
        formats = named | tagged
        if len(formats) != 1:
            raise ValueError(f"Original screen has no unique format: {key}")
        original = formats.pop()
        details = dict.fromkeys(REVIEW_FIELDS)
        details.update(original_screen_status="assigned", original_format=original,
                       original_cereal_proposal=None, original_type_proposal=None,
                       effective_membership="YES", effective_type_code=TYPE_CODES[original],
                       decision_source="original_screen")
    details["original_bar_form_review"] = key[0] == "US-CA" and key[1] in BAR_REVIEW
    details["h2_format_candidate"] = (details["effective_membership"] == "YES" and
                                      details["effective_type_code"] in {"GRANOLA", "FLAKES"})
    return details


def check_pair(row, candidate):
    """Only assess the H2 formats. Keep coverage, physical checks and audit agreement distinct."""
    result = dict.fromkeys(NUTRITION_FLAGS)
    if not candidate:
        return dict(result, h2_pair_status=None)
    energy, sugars = row["energy_kcal"], row["sugars_100g"]
    present = energy is not None and sugars is not None
    flags_agree = (row["energy_kcal_missing"] == int(energy is None) and
                   row["sugars_100g_missing"] == int(sugars is None))
    result.update(h2_both_present=present, h2_missing_flags_agree=flags_agree, h2_pair_valid=False)
    if not present:
        status = "both_missing" if energy is None and sugars is None else (
            "energy_missing" if energy is None else "sugars_missing")
        return dict(result, h2_pair_status=status)
    # The governed product gate already covers physical contradictions across nutrients.
    numeric = (row["include_in_product_table"] == 1 and math.isfinite(energy) and 0 <= energy <= 900
               and math.isfinite(sugars) and 0 <= sugars <= 100)
    result["h2_numeric_valid"] = numeric
    if not numeric:
        status = "physical_check_failed"
    elif energy != row["energy_kcal_off_raw"] or sugars != row["sugars_100g_off_raw"]:
        status = "source_value_disagreement"
    elif not flags_agree:
        status = "missing_flag_disagreement"
    else:
        status = "valid"
        result["h2_pair_valid"] = True
    return dict(result, h2_pair_status=status)


def build():
    if digest(MASTER) != MASTER_HASH:
        raise ValueError("The corrected Wave 2 source hash differs.")
    source = pq.ParquetFile(MASTER)
    reviews = load_reviews()
    batches = []
    for batch in source.iter_batches(columns=SOURCE_FIELDS, batch_size=8192):
        keep = pc.and_(batch["product_scope_eligible"], pc.equal(batch["category"], "cereal"))
        selected = batch.filter(keep)
        if selected.num_rows:
            batches.append(selected)
    base = pa.Table.from_batches(batches).sort_by([("region", "ascending"), ("barcode", "ascending")])
    keys = list(zip(base["region"].to_pylist(), base["barcode"].to_pylist()))
    if len(set(keys)) != len(keys) or Counter(base["region"].to_pylist()) != {"FR":7361, "UK-IE":1739, "US-CA":8080}:
        raise ValueError("Cereal assignment keys or regional denominators differ.")
    added = []
    for row in base.to_pylist():
        detail = decisions(row, reviews)
        detail.update(check_pair(row, detail["h2_format_candidate"]))
        added.append(detail)
    if reviews:
        raise ValueError("Unmatched regional review decisions.")
    membership = Counter(row["effective_membership"] for row in added)
    if membership != {"YES":16833, "NO":97, "UNKNOWN":250}:
        raise ValueError(f"Combined membership differs: {membership}")
    for key in TEXT_FIELDS + FORMAT_FLAGS + NUTRITION_FLAGS:
        field_type = pa.string() if key in TEXT_FIELDS else pa.bool_()
        base = base.append_column(key, pa.array((row[key] for row in added), type=field_type))
    metadata = dict(source.schema_arrow.metadata or {})
    metadata.update({b"master_sha256": MASTER_HASH.encode(), b"review_sha256": REVIEW_HASH.encode(),
                     b"lens1_builder_sha256": digest(Path(__file__)).encode()})
    return base.replace_schema_metadata(metadata)


def coverage(table):
    cells = {}
    for row in table.filter(table["h2_format_candidate"]).to_pylist():
        key = row["region"], row["effective_type_code"]
        counts = cells.setdefault(key, Counter())
        counts["candidates"] += 1
        counts["both_present"] += int(row["h2_both_present"])
        counts["numeric_valid"] += int(row["h2_numeric_valid"] is True)
        counts[row["h2_pair_status"]] += 1
        counts["zero_energy"] += int(row["energy_kcal"] == 0)
        counts["zero_sugars"] += int(row["sugars_100g"] == 0)
        counts["low_confidence"] += int(row["confidence"] == "LOW")
    for region, totals in zip(("FR","UK-IE","US-CA"), ((1552,902),(395,228),(2009,743)), strict=True):
        for code, expected in zip(("GRANOLA","FLAKES"), totals, strict=True):
            counts = cells[region, code]
            if counts["candidates"] != expected:
                raise ValueError(f"H2 scope differs: {region} {code}")
            print(region, code, dict(counts))


def main():
    table = build()
    with TemporaryDirectory(dir=HERE) as temp:
        staged = Path(temp) / OUTPUT.name
        pq.write_table(table, staged, compression="zstd")
        reread = pq.read_table(staged)
        if not reread.equals(table, check_metadata=True):
            raise ValueError("Parquet round-trip differs.")
        coverage(reread)
        os.replace(staged, OUTPUT)
    print(OUTPUT.name, table.num_rows, digest(OUTPUT))


if __name__ == "__main__":
    main()
