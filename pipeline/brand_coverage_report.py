"""
Brand coverage report — utility script, not part of the main pipeline.

Run after a full pipeline run to identify primary_brand values in the DB
that are not covered by company_brand_mapping.csv. Outputs a CSV of
candidate matches for review, ordered by product count (most impactful
unmapped brands first).

Usage:
    python pipeline/brand_coverage_report.py

Output:
    data/reference/brand_coverage_report.csv

Review the output and add confirmed mappings to
data/reference/company_brand_mapping.csv manually. The report never
writes to the mapping file itself — all edits are deliberate.
"""

from __future__ import annotations

import csv
import os
import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
MAPPING_PATH = ROOT / "data" / "reference" / "company_brand_mapping.csv"
OUTPUT_PATH = ROOT / "data" / "reference" / "brand_coverage_report.csv"


def _normalize(s: str) -> str:
    """Canonical form: lowercase, remove hyphens/punctuation, collapse spaces."""
    s = s.lower()
    s = re.sub(r"[-_./,]", " ", s)
    s = re.sub(r"\b(the|company|co|ltd|inc|s\.?a\.?|group|international|foods?)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_mapping() -> dict[str, list[str]]:
    """Returns {parent_company: [normalized primary_brand_db, ...]}."""
    mapping: dict[str, list[str]] = {}
    with open(MAPPING_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            company = row["parent_company"].strip()
            brand_db = _normalize(row["primary_brand_db"].strip())
            mapping.setdefault(company, []).append(brand_db)
    return mapping


def best_company_match(
    norm_brand: str, mapping: dict[str, list[str]]
) -> tuple[str, float]:
    """Return (best_company, similarity_score) for an unmapped brand.
    Uses token overlap + SequenceMatcher; score is 0–1."""
    best_company = ""
    best_score = 0.0
    brand_tokens = set(norm_brand.split())
    for company, brand_list in mapping.items():
        for mapped_brand in brand_list:
            mapped_tokens = set(mapped_brand.split())
            # Token overlap ratio
            overlap = len(brand_tokens & mapped_tokens) / max(
                len(brand_tokens | mapped_tokens), 1
            )
            # Sequence similarity
            seq = SequenceMatcher(None, norm_brand, mapped_brand).ratio()
            score = max(overlap, seq)
            if score > best_score:
                best_score = score
                best_company = company
    return best_company, round(best_score, 3)


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return
    if not MAPPING_PATH.exists():
        print(f"Mapping file not found: {MAPPING_PATH}")
        return

    mapping = load_mapping()
    all_mapped_norms = {nb for brands in mapping.values() for nb in brands}

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT primary_brand, COUNT(*) AS n
        FROM products
        WHERE primary_brand IS NOT NULL AND TRIM(primary_brand) != ''
        GROUP BY primary_brand
        ORDER BY n DESC
    """).fetchall()
    conn.close()

    results = []
    mapped_count = 0
    for brand, n in rows:
        norm = _normalize(brand)
        if norm in all_mapped_norms:
            mapped_count += 1
            continue  # already covered
        suggested_company, score = best_company_match(norm, mapping)
        results.append({
            "primary_brand_in_db":   brand,
            "product_count":         n,
            "normalized_form":       norm,
            "suggested_company":     suggested_company if score >= 0.4 else "",
            "similarity_score":      score if score >= 0.4 else "",
            "action":                "review",
        })

    total = len(rows)
    print(f"Total distinct primary_brand values: {total}")
    print(f"Already mapped: {mapped_count} ({100*mapped_count//total}%)")
    print(f"Unmapped (need review): {len(results)}")
    print(f"Top 10 unmapped by product count:")
    for r in results[:10]:
        suggestion = f" → maybe {r['suggested_company']} ({r['similarity_score']})" if r["suggested_company"] else ""
        print(f"  {r['primary_brand_in_db']:30s}  n={r['product_count']:4d}{suggestion}")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"\nFull report saved → {OUTPUT_PATH}")
    print("Review and add confirmed rows to data/reference/company_brand_mapping.csv")


if __name__ == "__main__":
    main()
