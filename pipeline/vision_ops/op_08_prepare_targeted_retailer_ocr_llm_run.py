"""
op_08_prepare_targeted_retailer_ocr_llm_run.py
----------------------------------------------
Resolve reviewed retailer OCR-LLM selections to GTINs and prepare the
explicit input files used by stage_10_extract_pack_claims.py.

The reviewed CSVs are treated as data only. Sampling decisions are not
recomputed here: rows marked OCR_LLM_Run == "run", run == "run", or
vision_additional_run == "run" are the execution list.

Default mode validates and writes stage-10-ready sample files without making
Azure calls. Use --execute to run stage 10 from this wrapper after validation.

Usage:
    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --execute

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set carrefour

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set carrefour --execute

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set mainstream_france

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set mainstream_uk_ie

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set mainstream_uk_ie_topup

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set mainstream_us_canada

    python pipeline/vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py --retailer-set mainstream_us_canada_topup

After a successful extraction run, merge the produced vision_results files with
stage_11_merge_vision_results.py, then run stage_12_build_claim_taxonomy.py and
the downstream app rebuild stages before publishing.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "database" / "positioning_radar.db"
VISION_SAMPLING_DIR = REPO_ROOT / "data" / "04_vision_sampling"
VISION_RELEASE_DIR = REPO_ROOT / "data" / "05_vision_release"
STAGE_10_PATH = REPO_ROOT / "pipeline" / "stages" / "stage_10_extract_pack_claims.py"

DEFAULT_INPUTS = {
    "Aldi": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\aldi_products_ocr_llm_run_sample.csv"
    ),
    "Lidl": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\lidl_products_ocr_llm_run_sample.csv"
    ),
    "Carrefour": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\carrefour_france_products_full_macro_positioning_details_OCR_run_selection.csv"
    ),
    "Groupe Casino": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\groupe_casino_france_products_full_macro_positioning_details_OCR_run_selection.csv"
    ),
    "Groupe U": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\groupe_u_france_products_full_macro_positioning_details_OCR_run_selection.csv"
    ),
    "Auchan": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\auchan_france_products_full_macro_positioning_details_OCR_run_selection_FINAL.csv"
    ),
    "Intermarch\u00e9": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\intermarche_france_products_full_macro_positioning_details_OCR_run_selection.csv"
    ),
    "E.Leclerc": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\e_leclerc_france_products_full_macro_positioning_details_OCR_run_selection.csv"
    ),
    "Tesco": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\tesco_uk_ie_products_ocr_llm_tagged.csv"
    ),
    "Asda": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\asda_uk_ie_products_ocr_llm_tagged.csv"
    ),
    "Sainsbury's": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\sainsbury_uk_ie_products_ocr_llm_tagged.csv"
    ),
    "Morrisons": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\morrisons_uk_ie_products_ocr_llm_tagged.csv"
    ),
    "Waitrose": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\waitrose_uk_ie_products_ocr_llm_tagged.csv"
    ),
    "Tesco UK_IE topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\tesco_uk_ie_products_vision_topup.csv"
    ),
    "Asda UK_IE topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\asda_uk_ie_products_vision_topup.csv"
    ),
    "Sainsbury's UK_IE topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\sainsbury_uk_ie_products_vision_topup.csv"
    ),
    "Morrisons UK_IE topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\morrisons_uk_ie_products_vision_topup.csv"
    ),
    "Waitrose UK_IE topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\waitrose_uk_ie_products_vision_topup.csv"
    ),
    "Walmart": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\walmart_us_canada_products_ocr_llm_tagged.csv"
    ),
    "Costco": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\costco_us_canada_products_ocr_llm_tagged.csv"
    ),
    "Kroger": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\kroger_us_canada_products_ocr_llm_tagged.csv"
    ),
    "Target": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\target_us_canada_products_ocr_llm_tagged.csv"
    ),
    "Walgreens": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\walgreens_us_canada_products_ocr_llm_tagged.csv"
    ),
    "Walmart US_CANADA topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\walmart_us_canada_products_full_macro_positioning_details_VISION_TOPUP.csv"
    ),
    "Kroger US_CANADA topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\kroger_us_canada_VISION_TOPUP.csv"
    ),
    "Target US_CANADA topup": Path(
        r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
        r"\target_us_canada_VISION_TOPUP.csv"
    ),
}

EXPECTED_TAGGED_ROWS = {
    "Aldi": 500,
    "Lidl": 350,
    "Carrefour": 238,
    "Groupe Casino": 189,
    "Groupe U": 211,
    "Auchan": 268,
    "Intermarch\u00e9": 153,
    "E.Leclerc": 265,
    "Tesco": 163,
    "Asda": 111,
    "Sainsbury's": 148,
    "Morrisons": 90,
    "Waitrose": 82,
    "Tesco UK_IE topup": 65,
    "Asda UK_IE topup": 33,
    "Sainsbury's UK_IE topup": 46,
    "Morrisons UK_IE topup": 41,
    "Waitrose UK_IE topup": 36,
    "Walmart": 414,
    "Costco": 45,
    "Kroger": 334,
    "Target": 280,
    "Walgreens": 39,
    "Walmart US_CANADA topup": 20,
    "Kroger US_CANADA topup": 80,
    "Target US_CANADA topup": 2,
}

RETAILER_SETS = {
    "aldi_lidl": ["Aldi", "Lidl"],
    "carrefour": ["Carrefour"],
    "mainstream_france": [
        "Carrefour",
        "Groupe Casino",
        "Groupe U",
        "Auchan",
        "Intermarch\u00e9",
        "E.Leclerc",
    ],
    "mainstream_uk_ie": [
        "Tesco",
        "Asda",
        "Sainsbury's",
        "Morrisons",
        "Waitrose",
    ],
    "mainstream_uk_ie_topup": [
        "Tesco UK_IE topup",
        "Asda UK_IE topup",
        "Sainsbury's UK_IE topup",
        "Morrisons UK_IE topup",
        "Waitrose UK_IE topup",
    ],
    "mainstream_us_canada": [
        "Walmart",
        "Costco",
        "Kroger",
        "Target",
        "Walgreens",
    ],
    "mainstream_us_canada_topup": [
        "Walmart US_CANADA topup",
        "Kroger US_CANADA topup",
        "Target US_CANADA topup",
    ],
}

DEFAULT_RUN_SLUGS = {
    "aldi_lidl": "aldi_lidl_targeted",
    "carrefour": "carrefour_targeted",
    "mainstream_france": "mainstream_france_additional_targeted",
    "mainstream_uk_ie": "mainstream_uk_ie_targeted",
    "mainstream_uk_ie_topup": "mainstream_uk_ie_additional_targeted",
    "mainstream_us_canada": "mainstream_us_canada_targeted",
    "mainstream_us_canada_topup": "mainstream_us_canada_additional_targeted",
}

LANGUAGE_PROFILE_OVERRIDES = {
    "mainstream_uk_ie": {"en": "uk_test_09_2026_final"},
    "mainstream_uk_ie_topup": {"en": "uk_test_09_2026_final"},
}

DB_COMPANY_BY_SELECTION = {
    "Tesco UK_IE topup": "Tesco",
    "Asda UK_IE topup": "Asda",
    "Sainsbury's UK_IE topup": "Sainsbury's",
    "Morrisons UK_IE topup": "Morrisons",
    "Waitrose UK_IE topup": "Waitrose",
    "Walmart US_CANADA topup": "Walmart",
    "Kroger US_CANADA topup": "Kroger",
    "Target US_CANADA topup": "Target",
}

REGION_ORDER = ["FRANCE", "UK_IE", "US_CANADA"]
REGION_SET = set(REGION_ORDER)
CATEGORY_ORDER = ["beverages", "cereals", "dairies", "snacks"]

BASE_COLUMNS = [
    "region",
    "category",
    "company",
    "brand",
    "product",
    "energy_kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "saturated_fat_per_100g",
    "carbohydrates_per_100g",
    "sugars_per_100g",
    "fiber_per_100g",
    "NOVA",
    "Nutriscore",
    "Positioning",
]

RUN_COLUMN_CANDIDATES = ["OCR_LLM_Run", "run", "vision_additional_run"]


def clean_num(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(round(float(value), 4))
    except (TypeError, ValueError):
        return str(value)


def clean_intish(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value)


def positioning(pack_claims_found: object, claim_source: object) -> str:
    if claim_source != "vision":
        return "NOT_ANALYZED"
    if pack_claims_found is None:
        return "NOT_ANALYZED"
    claims = str(pack_claims_found).strip()
    return claims if claims else "NO_CLAIM_IDENTIFIED"


def sort_key(row: dict[str, str]) -> tuple[object, ...]:
    region = row["region"]
    category = row["category"]
    return (
        REGION_ORDER.index(region) if region in REGION_SET else 99,
        CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99,
        row.get("brand", "").lower(),
        row.get("product", "").lower(),
    )


def base_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(col, "")) for col in BASE_COLUMNS)


def is_run(value: object) -> bool:
    return str(value or "").strip().lower() == "run"


def clean_gtin(value: object) -> str:
    return str(value or "").strip()


def load_review_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [c for c in BASE_COLUMNS if c not in fieldnames]
        if missing:
            raise ValueError(f"{path} is missing columns: {missing}")
        run_column = next((c for c in RUN_COLUMN_CANDIDATES if c in fieldnames), None)
        if not run_column:
            raise ValueError(
                f"{path} is missing a run marker column. Expected one of: "
                f"{RUN_COLUMN_CANDIDATES}"
            )
        rows = []
        for row in reader:
            cleaned = {k: str(v or "") for k, v in row.items()}
            cleaned["OCR_LLM_Run"] = cleaned.get(run_column, "")
            rows.append(cleaned)
        return rows


def load_company_extract_from_db(conn: sqlite3.Connection, company: str) -> list[dict[str, str]]:
    brand_expr = (
        "COALESCE(NULLIF(TRIM(p.normalized_brand), ''), "
        "NULLIF(TRIM(p.primary_brand), ''), p.brands)"
    )
    query = f"""
        SELECT
            p.barcode,
            p.product_name,
            p.query_category,
            p.observed_market_region_codes,
            p.resolved_company,
            {brand_expr} AS brand,
            p.energy_kcal,
            p.protein_100g,
            p.fat_100g,
            p.saturated_fat_100g,
            p.carbs_100g,
            p.sugars_100g,
            p.fiber_100g,
            p.nova_group,
            p.nutriscore_grade,
            p.image_url,
            a.pack_claims_found,
            a.claim_source
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        WHERE p.ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(p.include_in_product_table, 1) = 1
          AND p.resolved_company = ?
          AND {brand_expr} IS NOT NULL
          AND TRIM(LOWER({brand_expr})) NOT IN ('unknown', '', 'nan')
    """
    rows: list[dict[str, str]] = []
    for r in conn.execute(query, (company,)):
        regions = [
            x
            for x in str(r["observed_market_region_codes"] or "").split("|")
            if x in REGION_SET
        ]
        for region in regions:
            rows.append(
                {
                    "region": region,
                    "category": str(r["query_category"] or ""),
                    "company": str(r["resolved_company"] or ""),
                    "brand": str(r["brand"] or ""),
                    "product": str(r["product_name"] or ""),
                    "energy_kcal_per_100g": clean_num(r["energy_kcal"]),
                    "protein_per_100g": clean_num(r["protein_100g"]),
                    "fat_per_100g": clean_num(r["fat_100g"]),
                    "saturated_fat_per_100g": clean_num(r["saturated_fat_100g"]),
                    "carbohydrates_per_100g": clean_num(r["carbs_100g"]),
                    "sugars_per_100g": clean_num(r["sugars_100g"]),
                    "fiber_per_100g": clean_num(r["fiber_100g"]),
                    "NOVA": clean_intish(r["nova_group"]),
                    "Nutriscore": ""
                    if r["nutriscore_grade"] is None
                    else str(r["nutriscore_grade"]).upper(),
                    "Positioning": positioning(
                        r["pack_claims_found"], r["claim_source"]
                    ),
                    "barcode": str(r["barcode"] or ""),
                    "image_url": str(r["image_url"] or ""),
                }
            )
    rows.sort(key=sort_key)
    return rows


def infer_language(row: dict[str, str]) -> str:
    image_url = row.get("image_url", "").lower()
    if "/front_fr" in image_url or "_fr." in image_url:
        return "fr"
    if "/front_en" in image_url or "_en." in image_url:
        return "en"
    return "fr" if row.get("region") == "FRANCE" else "en"


def resolve_company(
    conn: sqlite3.Connection,
    selection_name: str,
    db_company: str,
    review_path: Path,
    expected_tagged_rows: int,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    review_rows = load_review_csv(review_path)
    db_rows = load_company_extract_from_db(conn, db_company)
    tagged_indexes = [i for i, row in enumerate(review_rows) if is_run(row["OCR_LLM_Run"])]

    if len(tagged_indexes) != expected_tagged_rows:
        raise ValueError(
            f"{selection_name}: expected {expected_tagged_rows} OCR_LLM_Run == 'run' rows, "
            f"found {len(tagged_indexes)}"
        )

    non_not_analyzed = [
        i
        for i in tagged_indexes
        if review_rows[i].get("Positioning") != "NOT_ANALYZED"
    ]

    positional_match = len(review_rows) == len(db_rows) and all(
        base_key(review_rows[i]) == base_key(db_rows[i])
        for i in range(len(review_rows))
    )

    key_to_db_rows: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    barcode_to_db_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in db_rows:
        key_to_db_rows[base_key(row)].append(row)
        if row.get("barcode"):
            barcode_to_db_rows[row["barcode"]].append(row)
    used_key_offsets: Counter[tuple[str, ...]] = Counter()

    resolved: list[dict[str, str]] = []
    unresolved: list[int] = []
    ambiguous: list[int] = []
    for idx in tagged_indexes:
        review_row = review_rows[idx]
        db_row = None
        review_gtin = clean_gtin(review_row.get("GTIN"))
        if review_gtin:
            candidates = barcode_to_db_rows.get(review_gtin, [])
            if len(candidates) == 1:
                db_row = candidates[0]
            elif len(candidates) > 1:
                matching_candidates = [
                    candidate
                    for candidate in candidates
                    if base_key(review_row) == base_key(candidate)
                ]
                if len(matching_candidates) == 1:
                    db_row = matching_candidates[0]
                else:
                    ambiguous.append(idx + 2)
        elif idx < len(db_rows) and base_key(review_row) == base_key(db_rows[idx]):
            db_row = db_rows[idx]
        else:
            candidates = key_to_db_rows.get(base_key(review_row), [])
            offset = used_key_offsets[base_key(review_row)]
            if len(candidates) > 1:
                ambiguous.append(idx + 2)
            if offset < len(candidates):
                db_row = candidates[offset]
                used_key_offsets[base_key(review_row)] += 1
        if db_row is None or not db_row.get("barcode"):
            unresolved.append(idx + 2)
            continue

        resolved.append(
            {
                "barcode": db_row["barcode"],
                "sampling_region": review_row["region"],
                "sampling_category": review_row["category"],
                "sample_component": "targeted_private_label",
                "primary_stratum_id": (
                    f"{db_company}|{review_row['region']}|{review_row['category']}"
                ),
                "sampling_weight": "",
                "weight_status": "targeted_unweighted",
                "target_company": db_company,
                "source_review_file": review_path.name,
                "source_review_row": str(idx + 2),
                "reviewed_positioning": review_row["Positioning"],
                "image_language": infer_language(db_row),
                "image_url_present": "1" if db_row.get("image_url") else "0",
            }
        )

    barcode_counts = Counter(row["barcode"] for row in resolved)
    duplicate_gtin_rows = sum(n - 1 for n in barcode_counts.values() if n > 1)
    image_url_missing = sum(1 for row in resolved if row["image_url_present"] != "1")

    summary = {
        "company": selection_name,
        "db_company": db_company,
        "review_rows": len(review_rows),
        "db_rows": len(db_rows),
        "tagged_rows": len(tagged_indexes),
        "resolved_rows": len(resolved),
        "unique_gtins": len(barcode_counts),
        "duplicate_gtin_rows": duplicate_gtin_rows,
        "unresolved_rows": len(unresolved),
        "ambiguous_rows": len(ambiguous),
        "non_not_analyzed_rows": len(non_not_analyzed),
        "image_url_missing_rows": image_url_missing,
        "positional_match": positional_match,
        "unresolved_csv_rows": unresolved[:20],
        "ambiguous_csv_rows": ambiguous[:20],
        "non_not_analyzed_csv_rows": [i + 2 for i in non_not_analyzed[:20]],
    }
    return resolved, summary


def dedupe_records(records: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in records:
        barcode = row["barcode"]
        if barcode in seen:
            continue
        seen.add(barcode)
        deduped.append(row)
    return deduped, len(records) - len(deduped)


def write_sample(path: Path, rows: list[dict[str, str]]) -> None:
    columns = [
        "barcode",
        "sampling_region",
        "sampling_category",
        "sample_component",
        "primary_stratum_id",
        "sampling_weight",
        "weight_status",
        "target_company",
        "source_review_file",
        "source_review_row",
        "reviewed_positioning",
        "image_language",
        "image_url_present",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def result_path_for(run_slug: str, language: str) -> Path:
    return VISION_RELEASE_DIR / f"vision_results_{run_slug}_{language}.csv"


def result_path_for_profile(run_slug: str, profile: str) -> Path:
    return VISION_RELEASE_DIR / f"vision_results_{run_slug}_{profile}.csv"


def run_stage_10(
    python_exe: str,
    sample_path: Path,
    run_slug: str,
    language: str,
    language_profile: str | None = None,
) -> None:
    profile = language_profile or language
    output_path = result_path_for_profile(run_slug, profile)
    cmd = [
        python_exe,
        str(STAGE_10_PATH),
        "--input",
        str(sample_path),
        "--language",
        profile,
        "--output",
        str(output_path),
    ]
    print("\nRunning stage 10:")
    print("  " + " ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Prepare and optionally execute a targeted retailer OCR-LLM run."
    )
    ap.add_argument(
        "--retailer-set",
        choices=sorted(RETAILER_SETS),
        default="aldi_lidl",
        help="Reviewed retailer selection set to prepare.",
    )
    ap.add_argument(
        "--run-slug",
        default=None,
        help="Output filename slug. Defaults from --retailer-set.",
    )
    ap.add_argument("--aldi-input", default=str(DEFAULT_INPUTS["Aldi"]))
    ap.add_argument("--lidl-input", default=str(DEFAULT_INPUTS["Lidl"]))
    ap.add_argument("--carrefour-input", default=str(DEFAULT_INPUTS["Carrefour"]))
    ap.add_argument(
        "--groupe-casino-input",
        default=str(DEFAULT_INPUTS["Groupe Casino"]),
    )
    ap.add_argument("--groupe-u-input", default=str(DEFAULT_INPUTS["Groupe U"]))
    ap.add_argument("--auchan-input", default=str(DEFAULT_INPUTS["Auchan"]))
    ap.add_argument(
        "--intermarche-input",
        default=str(DEFAULT_INPUTS["Intermarch\u00e9"]),
    )
    ap.add_argument("--e-leclerc-input", default=str(DEFAULT_INPUTS["E.Leclerc"]))
    ap.add_argument("--tesco-input", default=str(DEFAULT_INPUTS["Tesco"]))
    ap.add_argument("--asda-input", default=str(DEFAULT_INPUTS["Asda"]))
    ap.add_argument(
        "--sainsbury-input",
        default=str(DEFAULT_INPUTS["Sainsbury's"]),
    )
    ap.add_argument("--morrisons-input", default=str(DEFAULT_INPUTS["Morrisons"]))
    ap.add_argument("--waitrose-input", default=str(DEFAULT_INPUTS["Waitrose"]))
    ap.add_argument("--walmart-input", default=str(DEFAULT_INPUTS["Walmart"]))
    ap.add_argument("--costco-input", default=str(DEFAULT_INPUTS["Costco"]))
    ap.add_argument("--kroger-input", default=str(DEFAULT_INPUTS["Kroger"]))
    ap.add_argument("--target-input", default=str(DEFAULT_INPUTS["Target"]))
    ap.add_argument("--walgreens-input", default=str(DEFAULT_INPUTS["Walgreens"]))
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--output-dir", default=str(VISION_SAMPLING_DIR))
    ap.add_argument(
        "--execute",
        action="store_true",
        help="After validation, run stage_10_extract_pack_claims.py for each sample.",
    )
    ap.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use when --execute calls stage 10.",
    )
    args = ap.parse_args()

    run_slug = args.run_slug or DEFAULT_RUN_SLUGS[args.retailer_set]
    language_profiles = LANGUAGE_PROFILE_OVERRIDES.get(args.retailer_set, {})
    selected_companies = RETAILER_SETS[args.retailer_set]
    review_inputs = {
        "Aldi": Path(args.aldi_input),
        "Lidl": Path(args.lidl_input),
        "Carrefour": Path(args.carrefour_input),
        "Groupe Casino": Path(args.groupe_casino_input),
        "Groupe U": Path(args.groupe_u_input),
        "Auchan": Path(args.auchan_input),
        "Intermarch\u00e9": Path(args.intermarche_input),
        "E.Leclerc": Path(args.e_leclerc_input),
        "Tesco": Path(args.tesco_input),
        "Asda": Path(args.asda_input),
        "Sainsbury's": Path(args.sainsbury_input),
        "Morrisons": Path(args.morrisons_input),
        "Waitrose": Path(args.waitrose_input),
        "Walmart": Path(args.walmart_input),
        "Costco": Path(args.costco_input),
        "Kroger": Path(args.kroger_input),
        "Target": Path(args.target_input),
        "Walgreens": Path(args.walgreens_input),
    }
    for selection_name, default_path in DEFAULT_INPUTS.items():
        review_inputs.setdefault(selection_name, default_path)

    print("\nFood & Beverage Positioning Radar - targeted retailer OCR-LLM prep")
    print(f"Retailer set: {args.retailer_set}")
    print(f"Run slug: {run_slug}")
    print("Reviewed CSVs are treated as data only.")

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    all_records: list[dict[str, str]] = []
    summaries = []
    for company in selected_companies:
        db_company = DB_COMPANY_BY_SELECTION.get(company, company)
        records, summary = resolve_company(
            conn,
            company,
            db_company,
            review_inputs[company],
            EXPECTED_TAGGED_ROWS[company],
        )
        all_records.extend(records)
        summaries.append(summary)

    conn.close()

    print("\nValidation summary:")
    for summary in summaries:
        print(f"\n  {summary['company']}")
        print(f"    review rows:              {summary['review_rows']:,}")
        print(f"    db extract rows:           {summary['db_rows']:,}")
        print(f"    positional match:          {summary['positional_match']}")
        print(f"    tagged rows:               {summary['tagged_rows']:,}")
        print(f"    resolved rows:             {summary['resolved_rows']:,}")
        print(f"    unique GTINs:              {summary['unique_gtins']:,}")
        print(f"    duplicate GTIN rows:       {summary['duplicate_gtin_rows']:,}")
        print(f"    unresolved rows:           {summary['unresolved_rows']:,}")
        print(f"    ambiguous rows:            {summary['ambiguous_rows']:,}")
        print(f"    not NOT_ANALYZED rows:     {summary['non_not_analyzed_rows']:,}")
        print(f"    missing image URL rows:    {summary['image_url_missing_rows']:,}")
        if summary["unresolved_csv_rows"]:
            print(f"    unresolved CSV rows:       {summary['unresolved_csv_rows']}")
        if summary["ambiguous_csv_rows"]:
            print(f"    ambiguous CSV rows:        {summary['ambiguous_csv_rows']}")
        if summary["non_not_analyzed_csv_rows"]:
            print(
                "    not NOT_ANALYZED CSV rows: "
                f"{summary['non_not_analyzed_csv_rows']}"
            )

    blocking = [
        s
        for s in summaries
        if s["unresolved_rows"]
        or s["ambiguous_rows"]
        or s["non_not_analyzed_rows"]
    ]
    if blocking:
        raise SystemExit(
            "\nStopping before sample creation because validation found "
            "unresolved, ambiguous, or already-positioned tagged rows."
        )

    deduped, duplicate_rows = dedupe_records(all_records)
    by_language = {
        "fr": [r for r in deduped if r["image_language"] == "fr"],
        "en": [r for r in deduped if r["image_language"] == "en"],
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        language: output_dir / f"{run_slug}_ocr_llm_{language}.csv"
        for language in by_language
        if by_language[language]
    }
    combined_path = output_dir / f"{run_slug}_ocr_llm_all_gtins.csv"

    write_sample(combined_path, deduped)
    for language, path in output_paths.items():
        write_sample(path, by_language[language])

    print("\nPrepared stage-10 input files:")
    print(f"  combined manifest: {combined_path} ({len(deduped):,} unique GTINs)")
    print(f"  duplicate rows removed after GTIN dedupe: {duplicate_rows:,}")
    for language, path in output_paths.items():
        print(f"  {language}: {path} ({len(by_language[language]):,} GTINs)")

    if args.execute:
        for language in ["fr", "en"]:
            path = output_paths.get(language)
            if path:
                run_stage_10(
                    args.python,
                    path,
                    run_slug,
                    language,
                    language_profiles.get(language),
                )
    else:
        print("\nNo OCR/LLM calls made. To run extraction from cmd:")
        for language in ["fr", "en"]:
            path = output_paths.get(language)
            if path:
                profile = language_profiles.get(language, language)
                print(
                    "  python pipeline\\stages\\stage_10_extract_pack_claims.py "
                    f"--input {path} --language {profile} "
                    f"--output {result_path_for_profile(run_slug, profile)}"
                )
        print("\nOr run this wrapper with --execute:")
        print(
            "  python pipeline\\vision_ops\\"
            "op_08_prepare_targeted_retailer_ocr_llm_run.py "
            f"--retailer-set {args.retailer_set} --execute"
        )
        print("\nExpected merge commands after extraction completes:")
        release_id = f"release_2026_09_{run_slug}"
        for language in ["fr", "en"]:
            if language in output_paths:
                profile = language_profiles.get(language, language)
                print(
                    "  python pipeline\\stages\\stage_11_merge_vision_results.py "
                    f"--input {result_path_for_profile(run_slug, profile)} "
                    f"--release-id {release_id}"
                )


if __name__ == "__main__":
    main()
