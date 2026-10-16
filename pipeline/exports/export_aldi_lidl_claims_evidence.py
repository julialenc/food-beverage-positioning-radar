"""Reconstruct Aldi/Lidl claims evidence from frozen local CSVs, never the live DB.

The 2026-10-15 rules are a documented reconstruction, not the original chat code.
Reviewed product-specific interpretations supplement, never replace, claim codes.
Run with --check to validate existing outputs without writing any files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/private_label_analysis/aldi_lidl"
VERSION = "2026-10-15_reviewed_v1"
REGIONS = ("FRANCE", "UK_IE", "US_CANADA")
RETAILERS = ("Aldi", "Lidl")
TERRITORIES = {
    "Protein": "protein_claim",
    "Fibre / wholegrain": "fibre_claim|whole_grain_claim",
    "Fortification": "fortification_claim",
    "Energy": "energy_claim",
    "Gut health": "gut_health_claim|prebiotic_claim|probiotic_claim",
    "Immune": "immune_claim",
    "Sugar / fat reduction": "sugar_free_claim|reduced_sugar|reduced_fat_claim",
    "Free-from (gluten / lactose / dairy)": "gluten_free_claim|lactose_free_claim|dairy_free_claim",
    "Organic / natural": "organic_claim|natural_claim",
    "Origin / provenance / quality": "origin_quality_claim|heritage_claim|artisan_claim",
    "Clean label / no-additives": "clean_label_claim|no_artificial|no_palm_oil",
    "Plant-based / vegan": "plant_based_claim|vegan_claim",
    "Sustainability": "sustainability_halo",
}
# Manually transcribed from slide 4 of the PDF identified in snapshot_manifest.json.
# Column order: France Aldi/Lidl, UK_IE Aldi/Lidl, US_CANADA Aldi/Lidl.
PUBLISHED = dict(zip(TERRITORIES, (
    (10, 27, 31, 33, 17, 31), (12, 10, 14, 23, 18, 19),
    (10, 13, 8, 6, 14, 12), (10, 0, 1, 2, 3, 0),
    (1, 0, 1, 2, 4, 4), (0, 0, 3, 1, 2, 0),
    (12, 14, 27, 19, 19, 15), (6, 3, 5, 5, 22, 8),
    (33, 21, 12, 16, 44, 35), (10, 22, 7, 9, 1, 8),
    (0, 3, 9, 5, 11, 15), (10, 6, 5, 9, 6, 4),
    (4, 3, 3, 2, 2, 0),
), strict=True))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tags(row: dict[str, str]) -> set[str]:
    value = row["Positioning"]
    if not value:
        raise ValueError("Unexpected blank positioning: missing is not no-claim")
    if value in {"NOT_ANALYZED", "NO_CLAIM_IDENTIFIED"}:
        return set()
    result = set(value.split("|"))
    if "" in result or result & {"NOT_ANALYZED", "NO_CLAIM_IDENTIFIED"}:
        raise ValueError(f"Malformed positioning: {value}")
    return result


def key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return row["company"], row["region"], row["category"], row["GTIN"]


def pct(numerator: int, denominator: int, places: int | None = None) -> str:
    if not denominator:
        return ""  # Undefined is not zero.
    value = Decimal(numerator) * 100 / Decimal(denominator)
    if places is not None:
        value = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return str(value)


def build(base: Path) -> tuple[list[dict], list[dict]]:
    manifest = json.loads((base / "snapshot_manifest.json").read_text(encoding="utf-8"))
    originals = {r["original_path"]: r for r in manifest["files"]}
    pdf_hash = originals["aldi_lidl_architecture.pdf"]["sha256"]
    data = {}
    hashes = {}
    history = {}
    for retailer, number in zip(RETAILERS, ("02", "03"), strict=True):
        filename = f"{retailer.lower()}_products_full_macro_positioning_details.csv"
        path = base / "source_snapshots" / filename
        hashes[retailer] = digest(path)
        if hashes[retailer] != originals[filename]["sha256"]:
            raise ValueError(f"Frozen input changed: {filename}")
        rows = read_csv(path)
        if len({key(r) for r in rows}) != len(rows):
            raise ValueError(f"Duplicate region/category/GTIN keys: {filename}")
        for row in rows:
            if row["company"] != retailer or row["region"] not in REGIONS:
                raise ValueError(f"Unexpected scope: {row}")
            tags(row)
        data[retailer] = rows
        evidence = f"conclusion_{number}_{retailer.lower()}_positioning_evidence.csv"
        evidence_path = base / "source_snapshots" / evidence
        if digest(evidence_path) != originals[evidence]["sha256"]:
            raise ValueError(f"Frozen evidence changed: {evidence}")
        for row in read_csv(evidence_path):
            history[key(row)] = row

    all_rows = {key(r): r for rows in data.values() for r in rows}
    decisions = read_csv(base / "reviewed_territory_decisions.csv")
    reviewed = {}
    for decision in decisions:
        k = (decision["retailer"], decision["region"], decision["category"], decision["GTIN"])
        if k in reviewed or k not in all_rows or k not in history:
            raise ValueError(f"Duplicate or unmatched review: {k}")
        row, prior = all_rows[k], history[k]
        if (row["Positioning"] != decision["original_positioning"]
                or prior["territories"] != decision["original_territories"]
                or row["product"] != decision["product"]):
            raise ValueError(f"Review does not match source evidence: {k}")
        if (decision["reporting_territory"] != "Plant-based / vegan"
                or decision["reviewed_classification"] != "vegan"
                or not tags(row)):
            raise ValueError(f"Unsupported review: {k}")
        reviewed[k] = decision

    checks = []
    summaries = []
    decisions_hash = digest(base / "reviewed_territory_decisions.csv")
    for retailer in RETAILERS:
        for region in (*REGIONS, "ALL_REGIONS_RECORDS"):
            rows = [r for r in data[retailer] if region == "ALL_REGIONS_RECORDS" or r["region"] == region]
            analyzed = [r for r in rows if r["Positioning"] != "NOT_ANALYZED"]
            claimed = [r for r in analyzed if tags(r)]
            stacking = sum(len(tags(r)) >= 2 for r in claimed)
            summaries.append({
                "region": region, "retailer": retailer, "total_products": len(rows),
                "analyzed_products_including_no_claim": len(analyzed),
                "claimed_products_denominator": len(claimed),
                "no_claim_identified_products": len(analyzed) - len(claimed),
                "not_analyzed_products": len(rows) - len(analyzed),
                "claim_detection_rate_among_analyzed_pct": pct(len(claimed), len(analyzed), 1),
                "stacked_claimed_products_ge2_tags": stacking,
                "stacking_pct_among_claimed_products": pct(stacking, len(claimed), 1),
                "rules_version": VERSION, "source_sha256": hashes[retailer],
            })
            if region == "ALL_REGIONS_RECORDS":
                continue
            column = REGIONS.index(region) * 2 + RETAILERS.index(retailer)
            for territory, code_string in TERRITORIES.items():
                codes = set(code_string.split("|"))
                code_keys = {key(r) for r in claimed if tags(r) & codes}
                review_keys = {key(r) for r in claimed if key(r) in reviewed
                               and reviewed[key(r)]["reporting_territory"] == territory}
                final_keys = code_keys | review_keys
                n, denominator = len(final_keys), len(claimed)
                rounded = pct(n, denominator, 0)
                published = PUBLISHED[territory][column]
                checks.append({
                    "region": region, "retailer": retailer, "benefit_territory": territory,
                    "claim_codes_counted": code_string,
                    "code_only_numerator_products_with_territory": len(code_keys),
                    "reviewed_context_additions": len(review_keys - code_keys),
                    "numerator_products_with_territory": n,
                    "denominator_claimed_products": denominator,
                    "pct_code_only_among_claimed_products_exact": pct(len(code_keys), denominator),
                    "pct_among_claimed_products_exact": pct(n, denominator),
                    "pct_among_claimed_products_rounded_0dp": rounded,
                    "denominator_analyzed_products_including_no_claim": len(analyzed),
                    "pct_among_analyzed_products_including_no_claim_exact": pct(n, len(analyzed)),
                    "pct_among_analyzed_products_including_no_claim_rounded_0dp": pct(n, len(analyzed), 0),
                    "reviewed_gtins": "|".join(sorted(k[3] for k in review_keys)),
                    "published_pdf_pct_rounded_0dp": published,
                    "difference_from_published_pdf_ppt": int(rounded) - published if rounded else "",
                    "published_pdf_sha256": pdf_hash,
                    "rules_version": VERSION,
                    "source_sha256": hashes[retailer],
                    "review_decisions_sha256": decisions_hash,
                })
    return checks, summaries


def encode_csv(rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    checks, summaries = build(args.base)
    outputs = {
        args.base / "aldi_lidl_claims_denominator_check.csv": encode_csv(checks),
        args.base / "aldi_lidl_claims_denominator_summary.csv": encode_csv(summaries),
    }
    # Preflight every output before any writes. Never silently replace a release.
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"Existing evidence differs; review before replacement: {path}")
        if args.check and not path.exists():
            raise FileNotFoundError(path)
    if not args.check:
        for path, content in outputs.items():
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(content)
    differences = [r for r in checks if r["difference_from_published_pdf_ppt"] != 0]
    print(f"Validated {len(checks)} territory cells and {len(summaries)} scope summaries.")
    print(f"Reviewed differences from original PDF: {len(differences)} (see evidence and OBS-025).")


if __name__ == "__main__":
    main()
