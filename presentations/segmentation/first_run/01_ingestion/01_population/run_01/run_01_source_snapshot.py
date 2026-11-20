"""Build RUN 01 country-category candidate and audit pulls from a completed release.

The source SQLite database is opened read-only. This script does not rerun
nutrition governance, preflight images, or call OCR/LLM services.
"""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RELEASE = ROOT / "data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1"
DEFAULT_OUTPUT = ROOT / "presentations/segmentation/run_01"
COUNTRY_CODES = {
    "en:france": "FR",
    "en:united-kingdom": "UK",
    "en:ireland": "IE",
    "en:united-states": "US",
    "en:canada": "CA",
}
COUNTRY_ORDER = {country: index for index, country in enumerate(("FR", "UK", "IE", "US", "CA"))}
CATEGORY_ORDER = {category: index for index, category in enumerate(("snacks", "cereals", "dairies", "beverages"))}
NUTRIENTS = {
    "energy": "energy_kcal",
    "protein": "protein_100g",
    "total_fat": "fat_100g",
    "saturated_fat": "saturated_fat_100g",
    "carbohydrates": "carbs_100g",
    "sugars": "sugars_100g",
    "fibre": "fiber_100g",
    "salt": "salt_100g",
}
OUTPUTS = (
    "eligibility_ledger.csv",
    "candidate_population.csv",
    "check_01_country_category.csv",
    "check_01_nutrient_completeness.csv",
    "check_01_warning_breakdown.csv",
    "check_01_ocr_coverage.csv",
    "run_01_manifest.json",
)
IMAGE_URL = re.compile(r"^https?://", re.IGNORECASE)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def country_mapping(path):
    mapping = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            tag = row["country_tag"].strip().lower()
            if tag in COUNTRY_CODES:
                mapping[tag] = (COUNTRY_CODES[tag], row["region_code"].strip())
    if set(mapping) != set(COUNTRY_CODES):
        raise ValueError("Country mapping does not contain all five launch country tags")
    return mapping


def assignments(countries, mapping):
    """Return each mapped country once, preserving all multi-country products."""
    tags = {tag.strip().lower() for tag in (countries or "").split("|")}
    return sorted((mapping[tag] for tag in tags if tag in mapping),
                  key=lambda pair: COUNTRY_ORDER[pair[0]])


def image_availability(url):
    value = (url or "").strip()
    if not value or value.lower() in {"nan", "none", "null"}:
        return False, "missing"
    if "/invalid/" in value.lower():
        return False, "placeholder"
    if not IMAGE_URL.match(value):
        return False, "invalid_url_structure"
    return True, "available"


def historical_ocr_status(prior_json):
    """Classify saved pre-masking attempt evidence, without inferring freshness."""
    if not prior_json:
        return "status_unclassifiable", "missing_prior_analysis"
    try:
        prior = json.loads(prior_json)
    except (TypeError, ValueError):
        return "status_unclassifiable", "invalid_prior_analysis_json"
    if not isinstance(prior, dict):
        return "status_unclassifiable", "invalid_prior_analysis_shape"
    llm = str(prior.get("llm_status") or "").strip().lower()
    extraction = str(prior.get("claim_extraction_status") or "").strip().lower()
    claims = prior.get("pack_claims_found")
    attempted = prior.get("pack_analysis_attempted")
    ocr = str(prior.get("ocr_status") or "").strip().lower()
    if llm == "success" and extraction == "completed" and claims is not None:
        return ("success_with_claims" if str(claims).strip() else "success_no_claims"), ""
    if llm == "success" and extraction == "completed" and claims is None:
        return "status_unclassifiable", "completed_without_claim_result"
    if attempted == 1 or llm or ocr:
        return "attempted_failed_or_unusable", ""
    if claims is not None or extraction:
        return "status_unclassifiable", "legacy_result_without_attempt_proof"
    return "not_processed", ""


def pct(numerator, denominator):
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def write_table(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run(source, output, mapping_path):
    source = source.resolve()
    output = output.resolve()
    mapping_path = mapping_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if any((output / name).exists() for name in OUTPUTS):
        raise FileExistsError(f"RUN 01 output already exists in {output}; refusing to overwrite")
    mapping = country_mapping(mapping_path)
    conn = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        release = conn.execute("SELECT wave_id, reporting_date, retrieved_at, source_sha256, status FROM release_manifest").fetchall()
        if len(release) != 1 or release[0]["status"] != "complete":
            raise ValueError("Source must have exactly one completed release")
        if release[0]["reporting_date"] != "2026-09-29" or not release[0]["retrieved_at"].startswith("2026-10-17"):
            raise ValueError("Source is not the approved September proxy / October retrieval")
        source_products = conn.execute("SELECT COUNT(*) FROM retained_deployment_products").fetchone()[0]
        if source_products != 522432:
            raise ValueError(f"Expected 522432 in-scope source products, found {source_products}")
        query = """
            SELECT p.barcode, p.product_name, p.brands, p.normalized_brand,
                   p.countries, p.observed_market_region_codes, p.query_category,
                   p.last_modified_t, p.ingested_at, p.image_url,
                   p.nutrition_quality_status, p.nutrition_quality_reason,
                   p.include_in_product_table, p.warning_flag, p.warning_types,
                   p.warning_summary, p.energy_kcal, p.protein_100g, p.fat_100g,
                   p.saturated_fat_100g, p.carbs_100g, p.sugars_100g,
                   p.fiber_100g, p.salt_100g,
                   p.energy_kcal_off_raw, p.protein_100g_off_raw,
                   p.fat_100g_off_raw, p.saturated_fat_100g_off_raw,
                   p.carbs_100g_off_raw, p.sugars_100g_off_raw,
                   p.fiber_100g_off_raw, p.salt_100g_off_raw,
                   f.status AS claim_freshness_status, f.prior_analysis_json
            FROM retained_deployment_products p
            LEFT JOIN claim_freshness f ON f.barcode = p.barcode
            ORDER BY p.barcode
        """
        ledger_columns = [
            "barcode", "country", "region_code", "category", "product_name",
            "brands", "normalized_brand", "countries", "observed_market_region_codes",
            "last_modified_t", "ingested_at", "image_url", "image_available",
            "image_availability_reason", "nutrition_quality_status",
            "nutrition_quality_reason", "include_in_product_table", "physically_valid",
            "warning_flag", "warning_types", "warning_summary", "nutrition_complete",
            "nutrition_incomplete", "nutrition_warning_present", "no_nutrition_warning",
            *NUTRIENTS.values(), *(f"{field}_off_raw" for field in NUTRIENTS.values()),
            "claim_freshness_status", "historical_ocr_status", "ocr_status_limitation",
        ]
        output.mkdir(parents=True, exist_ok=True)
        ledger_path = output / "eligibility_ledger.csv"
        candidate_path = output / "candidate_population.csv"
        stats = defaultdict(Counter)
        nutrient_counts = defaultdict(Counter)
        warning_counts = defaultdict(Counter)
        warning_barcodes = defaultdict(set)
        any_warning_barcodes = defaultdict(set)
        all_warning_barcodes = set()
        ocr_counts = defaultdict(Counter)
        ocr_limitations = Counter()
        quality_exceptions = Counter()
        no_country_products = 0
        source_seen = 0
        assigned_barcodes = set()
        candidate_barcodes = set()
        with ledger_path.open("w", encoding="utf-8", newline="") as ledger_stream, candidate_path.open("w", encoding="utf-8", newline="") as candidate_stream:
            ledger_writer = csv.DictWriter(ledger_stream, fieldnames=ledger_columns)
            candidate_writer = csv.DictWriter(candidate_stream, fieldnames=ledger_columns)
            ledger_writer.writeheader()
            candidate_writer.writeheader()
            for db_row in conn.execute(query):
                source_seen += 1
                item = dict(db_row)
                barcode = item["barcode"]
                country_assignments = assignments(item["countries"], mapping)
                if not country_assignments:
                    no_country_products += 1
                    continue
                assigned_barcodes.add(barcode)
                image_ok, image_reason = image_availability(item["image_url"])
                gate = item["include_in_product_table"]
                status = item["nutrition_quality_status"]
                if gate not in (0, 1):
                    quality_exceptions["missing_or_nonbinary_hard_gate"] += 1
                    raise ValueError(f"Missing/nonbinary physical gate for barcode {barcode}")
                valid = gate == 1
                if (status == "data_quality_error") == valid:
                    quality_exceptions["quality_status_gate_conflict"] += 1
                    raise ValueError(f"Physical gate conflicts with quality status for barcode {barcode}")
                warning_types = sorted({part.strip() for part in (item["warning_types"] or "").split("|") if part.strip()})
                if bool(item["warning_flag"]) != bool(warning_types):
                    quality_exceptions["warning_flag_type_conflict"] += 1
                complete = valid and all(item[field] is not None for field in NUTRIENTS.values())
                warning = valid and bool(warning_types or item["warning_flag"])
                ocr_status, ocr_limitation = historical_ocr_status(item.pop("prior_analysis_json"))
                if ocr_limitation:
                    ocr_limitations[ocr_limitation] += 1
                base = {
                    "barcode": barcode,
                    "product_name": item["product_name"],
                    "brands": item["brands"],
                    "normalized_brand": item["normalized_brand"],
                    "countries": item["countries"],
                    "observed_market_region_codes": item["observed_market_region_codes"],
                    "last_modified_t": item["last_modified_t"],
                    "ingested_at": item["ingested_at"],
                    "image_url": item["image_url"],
                    "image_available": int(image_ok),
                    "image_availability_reason": image_reason,
                    "nutrition_quality_status": status,
                    "nutrition_quality_reason": item["nutrition_quality_reason"],
                    "include_in_product_table": gate,
                    "physically_valid": int(valid),
                    "warning_flag": item["warning_flag"],
                    "warning_types": item["warning_types"],
                    "warning_summary": item["warning_summary"],
                    "nutrition_complete": int(complete),
                    "nutrition_incomplete": int(valid and not complete),
                    "nutrition_warning_present": int(warning),
                    "no_nutrition_warning": int(valid and not warning),
                    "claim_freshness_status": item["claim_freshness_status"],
                    "historical_ocr_status": ocr_status,
                    "ocr_status_limitation": ocr_limitation,
                }
                for field in NUTRIENTS.values():
                    base[field] = item[field]
                    base[f"{field}_off_raw"] = item[f"{field}_off_raw"]
                for country, region in country_assignments:
                    if region not in (item["observed_market_region_codes"] or "").split("|"):
                        quality_exceptions["country_region_mapping_mismatch"] += 1
                    key = (country, item["query_category"])
                    out = {**base, "country": country, "region_code": region, "category": item["query_category"]}
                    ledger_writer.writerow(out)
                    stat = stats[key]
                    stat["total_unique_assignments"] += 1
                    if valid:
                        candidate_writer.writerow(out)
                        candidate_barcodes.add(barcode)
                        stat["physically_valid"] += 1
                        stat["physically_valid_with_image" if image_ok else "physically_valid_without_image"] += 1
                        stat["complete_nutrition" if complete else "incomplete_nutrition"] += 1
                        stat["with_nutritional_warnings" if warning else "without_nutritional_warnings"] += 1
                        for nutrient, field in NUTRIENTS.items():
                            if item[field] is not None:
                                nutrient_counts[key][nutrient] += 1
                        if warning:
                            any_warning_barcodes[key].add(barcode)
                            all_warning_barcodes.add(barcode)
                            for warning_type in warning_types:
                                warning_counts[key][warning_type] += 1
                                warning_barcodes[(country, item["query_category"], warning_type)].add(barcode)
                            if not warning_types:
                                warning_counts[key]["unspecified_warning_type"] += 1
                                warning_barcodes[(country, item["query_category"], "unspecified_warning_type")].add(barcode)
                        if image_ok:
                            ocr_counts[key][ocr_status] += 1
                    else:
                        stat["physically_invalid"] += 1
        if source_seen != source_products:
            raise ValueError(f"Source scan mismatch: {source_seen} versus {source_products}")
        if no_country_products:
            raise ValueError(f"{no_country_products} in-scope products have no mapped launch country")
        if quality_exceptions["country_region_mapping_mismatch"]:
            raise ValueError("Country tags conflict with stored region assignments")
        keys = sorted(stats, key=lambda k: (COUNTRY_ORDER[k[0]], CATEGORY_ORDER[k[1]]))
        country_rows = []
        nutrient_rows = []
        warning_rows = []
        ocr_rows = []
        for country, category in keys:
            key = (country, category)
            stat = stats[key]
            valid = stat["physically_valid"]
            country_rows.append({
                "country": country, "category": category,
                **{name: stat[name] for name in (
                    "total_unique_assignments", "physically_valid", "physically_invalid",
                    "physically_valid_with_image", "physically_valid_without_image",
                    "complete_nutrition", "incomplete_nutrition", "with_nutritional_warnings",
                    "without_nutritional_warnings")},
                "complete_nutrition_pct_of_valid": pct(stat["complete_nutrition"], valid),
                "incomplete_nutrition_pct_of_valid": pct(stat["incomplete_nutrition"], valid),
                "with_warnings_pct_of_valid": pct(stat["with_nutritional_warnings"], valid),
                "without_warnings_pct_of_valid": pct(stat["without_nutritional_warnings"], valid),
            })
            for nutrient in NUTRIENTS:
                non_null = nutrient_counts[key][nutrient]
                nutrient_rows.append({"country": country, "category": category,
                                      "nutrient": nutrient, "physically_valid_denominator": valid,
                                      "non_null_count": non_null, "non_null_pct_of_valid": pct(non_null, valid)})
            warning_rows.append({"country": country, "category": category,
                                 "warning_type": "ANY_WARNING", "physically_valid_denominator": valid,
                                 "affected_assignments": stat["with_nutritional_warnings"],
                                 "affected_pct_of_valid": pct(stat["with_nutritional_warnings"], valid),
                                 "affected_unique_barcodes": len(any_warning_barcodes[key])})
            for warning_type in sorted(warning_counts[key]):
                count = warning_counts[key][warning_type]
                warning_rows.append({"country": country, "category": category,
                                     "warning_type": warning_type, "physically_valid_denominator": valid,
                                     "affected_assignments": count,
                                     "affected_pct_of_valid": pct(count, valid),
                                     "affected_unique_barcodes": len(warning_barcodes[(country, category, warning_type)])})
            image_count = stat["physically_valid_with_image"]
            for ocr_status in ("success_with_claims", "success_no_claims", "attempted_failed_or_unusable", "not_processed", "status_unclassifiable"):
                count = ocr_counts[key][ocr_status]
                ocr_rows.append({"country": country, "category": category,
                                 "historical_ocr_status": ocr_status,
                                 "physically_valid_with_image_denominator": image_count,
                                 "assignments": count, "pct_of_valid_with_image": pct(count, image_count)})
        warning_rows.append({"country": "ALL", "category": "ALL", "warning_type": "ANY_WARNING",
                             "physically_valid_denominator": sum(v["physically_valid"] for v in stats.values()),
                             "affected_assignments": sum(v["with_nutritional_warnings"] for v in stats.values()),
                             "affected_pct_of_valid": pct(sum(v["with_nutritional_warnings"] for v in stats.values()),
                                                          sum(v["physically_valid"] for v in stats.values())),
                             "affected_unique_barcodes": len(all_warning_barcodes)})
        write_table(output / "check_01_country_category.csv", list(country_rows[0]), country_rows)
        write_table(output / "check_01_nutrient_completeness.csv", list(nutrient_rows[0]), nutrient_rows)
        write_table(output / "check_01_warning_breakdown.csv", list(warning_rows[0]), warning_rows)
        write_table(output / "check_01_ocr_coverage.csv", list(ocr_rows[0]), ocr_rows)
        total_assignments = sum(row["total_unique_assignments"] for row in country_rows)
        valid_assignments = sum(row["physically_valid"] for row in country_rows)
        manifest = {
            "run": "RUN_01", "source_database": str(source), "source_database_sha256": sha256(source),
            "source_release": dict(release[0]), "country_mapping_file": str(mapping_path),
            "country_mapping_sha256": sha256(mapping_path),
            "script_sha256": sha256(Path(__file__)),
            "source_product_rows": source_seen, "products_with_launch_country": len(assigned_barcodes),
            "total_country_category_assignments": total_assignments,
            "physically_valid_assignments": valid_assignments,
            "physically_invalid_assignments": total_assignments - valid_assignments,
            "physically_valid_unique_barcodes": len(candidate_barcodes),
            "physically_valid_with_image_assignments": sum(row["physically_valid_with_image"] for row in country_rows),
            "unique_warning_flagged_barcodes": len(all_warning_barcodes),
            "ocr_status_limitations_by_product": dict(ocr_limitations),
            "quality_exceptions_by_product_or_assignment": dict(quality_exceptions),
            "field_definitions": {
                "assignment_key": ["barcode", "country", "category"],
                "countries": COUNTRY_CODES,
                "category": "Governed products.query_category; one category per barcode in this release",
                "physically_valid": "Stored include_in_product_table=1, consistent with nutrition_quality_status != data_quality_error",
                "nutrition_complete": "Physically valid with all eight working nutrition fields non-NULL; zero is present",
                "nutrition_incomplete": "Physically valid with at least one of eight working nutrition fields NULL",
                "nutrition_warning_present": "Physically valid with warning_flag or nonempty warning_types; warnings do not exclude",
                "image_available": "Stage 09 structural HTTP(S) URL check, excluding missing and /invalid/ placeholders; no network preflight",
                "historical_ocr_status": "Derived from claim_freshness.prior_analysis_json saved before current-release masking; not a claim-freshness certification",
                "claim_freshness_status": "Release audit link to extraction evidence; does not by itself determine prior processing",
                "nutrition_fields": NUTRIENTS,
            },
            "validation_rules": [
                "Completed October 18 release with September 29 cutoff and October 17 retrieval",
                "Retained deployment scope, not release_population or legacy MAX(ingested_at)",
                "Locked Stage 03 hard gate reused from stored governed fields; no new physical thresholds",
                "No complete-nutrition, warning, image, or claim-status exclusion from candidate_population",
                "No image downloads, HTTP checks, OCR/LLM, imputation, clustering or source writes",
            ],
            "output_files": {name: {"sha256": sha256(output / name), "bytes": (output / name).stat().st_size}
                             for name in OUTPUTS if name != "run_01_manifest.json"},
        }
        with (output / "run_01_manifest.json").open("w", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        print(json.dumps({k: manifest[k] for k in (
            "source_product_rows", "total_country_category_assignments",
            "physically_valid_assignments", "physically_invalid_assignments",
            "physically_valid_with_image_assignments", "unique_warning_flagged_barcodes",
            "ocr_status_limitations_by_product", "quality_exceptions_by_product_or_assignment")}, indent=2))
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_RELEASE / "release_work.db")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--country-mapping", type=Path,
                        default=ROOT / "data/01_reference_inputs/01_country_region_mapping.csv")
    args = parser.parse_args()
    run(args.source, args.output, args.country_mapping)


if __name__ == "__main__":
    main()
