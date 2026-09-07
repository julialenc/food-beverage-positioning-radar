"""
Brand mapping diagnostics.

This utility groups read-only brand/company mapping checks behind one CLI.
It is not part of the main production pipeline.

Modes:
    --counts
        Write data/reference/brand_counts.csv and print the largest brands.

    --coverage
        Write data/reference/brand_coverage_report.csv and
        data/reference/brand_alias_candidates.csv.

    --check-brand PREFIX
        Print brand variants whose primary_brand starts with PREFIX.

    --unmapped
        Print brand mapping coverage against company_brand_mapping.csv.

If no mode is provided, --coverage is used. Reference mapping files are read
only; candidate outputs are review material and never overwrite curated
brand_alias_mapping.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT          = Path(__file__).resolve().parent.parent
DB_PATH       = ROOT / "database" / "positioning_radar.db"
MAPPING_PATH  = ROOT / "data" / "reference" / "company_brand_mapping.csv"
BRAND_COUNTS_OUT = ROOT / "data" / "reference" / "brand_counts.csv"
COVERAGE_OUT  = ROOT / "data" / "reference" / "brand_coverage_report.csv"
ALIAS_OUT     = ROOT / "data" / "reference" / "brand_alias_candidates.csv"

# Geographic / legal suffixes whose removal reveals a canonical brand.
# Ordered longest-first so "north america" is tried before "america".
GEO_SUFFIXES = [
    " north america", " south america", " latin america",
    " europe", " european", " middle east",
    " schweiz", " suisse", " switzerland",
    " italia", " italy", " france", " espana", " spain",
    " deutschland", " germany", " uk", " usa", " us",
    " international", " worldwide",
    " gmbh", " ag", " sa", " s.a.", " nv", " bv", " srl",
    " inc", " ltd", " llc", " corp", " company", " co",
    " group", " holding", " holdings",
]

CompanyCandidate = tuple[str, str, set[str], int]


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Canonical form for company-match scoring only (not for alias detection)."""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", errors="ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[-_./,]", " ", s)
    s = re.sub(r"\b(the|company|co|ltd|inc|s\.?a\.?|group|international|foods?)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _simple_brand_key(value: str) -> str:
    return value.lower().replace("-", " ").strip()


def load_brand_counts() -> list[tuple[str, int, str]]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT
            primary_brand,
            COUNT(*) as total_products,
            GROUP_CONCAT(DISTINCT query_category) as categories
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
        GROUP BY primary_brand
        ORDER BY total_products DESC
    """).fetchall()
    conn.close()
    return rows


def run_counts() -> None:
    rows = load_brand_counts()

    with open(BRAND_COUNTS_OUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["primary_brand", "total_products", "categories", "action"])
        for brand, n, cats in rows:
            writer.writerow([brand, n, cats, ""])

    print(f"Saved {len(rows):,} brands -> {BRAND_COUNTS_OUT}")
    print(f"\nTop 30 brands by product count:")
    print(f"{'Brand':<40} {'Products':>8}  Categories")
    print("-" * 75)
    for brand, n, cats in rows[:30]:
        print(f"{brand:<40} {n:>8}  {cats}")


def run_check_brand(prefix: str) -> None:
    prefix = prefix.lower()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT primary_brand, COUNT(*) as n
        FROM products
        WHERE LOWER(primary_brand) LIKE ?
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
        GROUP BY primary_brand
        ORDER BY n DESC
    """, (f"{prefix}%",)).fetchall()
    conn.close()

    if not rows:
        print(f"\nNo brands starting with '{prefix}' found.")
        return

    total = sum(n for _, n in rows)
    main = rows[0][1]
    pct = main / total * 100

    print(f"\nBrands starting with '{prefix}': {len(rows)} variants, {total:,} total products")
    print(f"Largest variant: '{rows[0][0]}' ({main:,} products = {pct:.1f}% of group)\n")
    print(f"{'Brand':<50} {'Products':>8}  {'% of group':>10}")
    print("-" * 73)
    for brand, n in rows:
        bar = "#" * min(int(n / total * 40), 40)
        print(f"{brand:<50} {n:>8}  {n/total*100:>9.1f}%  {bar}")

    print(f"\n{'TOTAL':<50} {total:>8}")
    print(f"\n95% threshold: {total * 0.95:.0f} products")
    print(f"Already unified under '{rows[0][0]}': {main:,} ({pct:.1f}%)")
    if pct >= 95:
        print("Above 95% - done, no further action needed.")
    else:
        print(f"Below 95% - {total - main:,} products in {len(rows)-1} variants still unmatched.")


def run_unmapped() -> None:
    mapped_statuses = {}
    with open(MAPPING_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            brand = row.get("primary_brand_db", "").strip()
            if brand:
                status = row.get("ownership_resolution_status", "").strip().lower() or "direct"
                mapped_statuses.setdefault(_simple_brand_key(brand), set()).add(status)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT primary_brand, COUNT(*) as n
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
        GROUP BY primary_brand
        ORDER BY n DESC
    """).fetchall()
    conn.close()

    direct_mapped = []
    scoped_or_review = []
    unmapped = []

    for brand, n in rows:
        statuses = mapped_statuses.get(_simple_brand_key(brand))
        if not statuses:
            unmapped.append((brand, n))
        elif statuses == {"direct"}:
            direct_mapped.append((brand, n))
        else:
            scoped_or_review.append((brand, n, statuses))

    total_unmapped_products = sum(n for _, n in unmapped)
    total_scoped_products = sum(n for _, n, _ in scoped_or_review)
    total_products = sum(n for _, n in rows)
    brands_under_10 = sum(1 for _, n in unmapped if n < 10)
    manual_review_brands = [
        (brand, n, statuses)
        for brand, n, statuses in scoped_or_review
        if "manual_review" in statuses
    ]

    print(f"Total distinct brands in DB:    {len(rows):,}")
    print(f"Total products with a brand:     {total_products:,}")
    print(f"Resolved direct mappings:        {len(direct_mapped):,}")
    print(f"Scoped/manual-review mappings:   {len(scoped_or_review):,}  ({total_scoped_products:,} products)")
    print(f"  with manual-review fallback:   {len(manual_review_brands):,} brands")
    print(f"Unmapped (Other):               {len(unmapped):,}  ({total_unmapped_products:,} products)")
    print(f"  of which < 10 products:       {brands_under_10:,} brands")
    print(f"  of which >= 10 products:      {len(unmapped) - brands_under_10:,} brands")
    print(f"\nTop 40 unmapped brands (>= 10 products):")
    print(f"{'Brand':<45} {'Products':>8}")
    print("-" * 56)
    shown = 0
    for brand, n in unmapped:
        if n >= 10:
            print(f"{brand:<45} {n:>8}")
            shown += 1
            if shown >= 40:
                break

    if scoped_or_review:
        print(f"\nTop scoped/manual-review mapped brands:")
        print(f"{'Brand':<45} {'Products':>8}  Statuses")
        print("-" * 75)
        for brand, n, statuses in scoped_or_review[:20]:
            status_text = ", ".join(sorted(statuses))
            print(f"{brand:<45} {n:>8}  {status_text}")


# ── Existing: company coverage report ─────────────────────────────────────────

def load_mapping() -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    """Returns company match hints and ownership statuses by normalized brand."""
    mapping: dict[str, list[str]] = {}
    statuses_by_brand: dict[str, set[str]] = {}
    with open(MAPPING_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            company  = row["parent_company"].strip()
            brand_db = _normalize(row["primary_brand_db"].strip())
            status = row.get("ownership_resolution_status", "").strip().lower() or "direct"
            if not brand_db:
                continue
            statuses_by_brand.setdefault(brand_db, set()).add(status)
            if status == "manual_review" or company.lower() == "manual review":
                continue
            mapping.setdefault(company, []).append(brand_db)
    return mapping, statuses_by_brand


def flatten_company_candidates(mapping: dict[str, list[str]]) -> list[CompanyCandidate]:
    candidates: list[CompanyCandidate] = []
    for company, brand_list in mapping.items():
        for mapped_brand in brand_list:
            candidates.append(
                (company, mapped_brand, set(mapped_brand.split()), len(mapped_brand))
            )
    return candidates


def best_company_match(
    norm_brand: str, candidates: list[CompanyCandidate]
) -> tuple[str, float]:
    """Fuzzy match an unmapped brand against the company mapping.
    Returns (best_company, score). Score is 0–1; suggestions below 0.4
    are suppressed as too unreliable (see ADR-2026-07)."""
    best_company = ""
    best_score = 0.0
    brand_tokens = set(norm_brand.split())
    brand_len = len(norm_brand)
    for company, mapped_brand, mapped_tokens, mapped_len in candidates:
        overlap = len(brand_tokens & mapped_tokens) / max(
            len(brand_tokens | mapped_tokens), 1
        )
        if overlap > best_score:
            best_score = overlap
            best_company = company

        max_seq_ratio = (
            2 * min(brand_len, mapped_len) / (brand_len + mapped_len)
            if brand_len + mapped_len
            else 1.0
        )
        if max_seq_ratio > best_score:
            matcher = SequenceMatcher(None, norm_brand, mapped_brand)
            if matcher.quick_ratio() > best_score:
                seq = matcher.ratio()
                if seq > best_score:
                    best_score = seq
                    best_company = company
    return best_company, round(best_score, 3)


# ── New: alias detection ───────────────────────────────────────────────────────

def detect_prefix_aliases(brand_counts: dict[str, int]) -> list[dict]:
    """
    Prefix pattern: "emmi" exists as a standalone brand AND "emmi schweiz"
    starts with "emmi ". The shorter name is canonical.

    Uses set lookup (O(n × max_words)) instead of nested iteration (O(n²))
    so it runs in seconds even with 50,000+ distinct brands.

    For each brand, we try every word-boundary prefix and check if that
    prefix exists as a standalone brand in the DB.
    """
    brand_set = set(brand_counts.keys())
    results: list[dict] = []
    seen_variants: set[str] = set()

    for brand in sorted(brand_counts.keys(), key=lambda b: -brand_counts[b]):
        if brand in seen_variants:
            continue
        words = brand.split()
        if len(words) < 2:
            continue
        # Try progressively shorter prefixes, shortest first
        for i in range(1, len(words)):
            canonical = " ".join(words[:i])
            if canonical in brand_set and canonical != brand:
                c_count = brand_counts[canonical]
                v_count = brand_counts[brand]
                # Only flag when the canonical is more established than
                # the variant AND has meaningful presence in the DB.
                # This eliminates false positives like "red bull" → "red"
                # where "red" has far fewer products than "red bull" —
                # in that case "red bull" IS the canonical brand name.
                MIN_CANONICAL_PRODUCTS = 50
                if c_count <= v_count or c_count < MIN_CANONICAL_PRODUCTS:
                    continue
                confidence = "high" if c_count >= v_count * 5 else "medium"
                results.append({
                    "variant_brand":   brand,
                    "canonical_brand": canonical,
                    "pattern":         "prefix",
                    "variant_count":   v_count,
                    "canonical_count": c_count,
                    "confidence":      confidence,
                    "action":          "",
                    "notes":           "",
                })
                seen_variants.add(brand)
                break  # use shortest matching prefix
    return results


def detect_punctuation_variants(brand_counts: dict[str, int]) -> list[dict]:
    """
    Punctuation pattern: "chin-chin" and "chin chin" are the same brand.
    After replacing hyphens/underscores with spaces, identical strings
    are grouped; the one with more products is canonical.
    """
    norm_to_brands: dict[str, list[str]] = {}
    for brand in brand_counts:
        norm = re.sub(r"[-_]+", " ", brand).strip()
        norm_to_brands.setdefault(norm, []).append(brand)

    results: list[dict] = []
    for norm, brand_list in norm_to_brands.items():
        if len(brand_list) < 2:
            continue
        brand_list.sort(key=lambda b: brand_counts[b], reverse=True)
        canonical = brand_list[0]
        for variant in brand_list[1:]:
            results.append({
                "variant_brand":   variant,
                "canonical_brand": canonical,
                "pattern":         "punctuation",
                "variant_count":   brand_counts[variant],
                "canonical_count": brand_counts[canonical],
                "confidence":      "high",
                "action":          "",
                "notes":           "",
            })
    return results


def detect_geo_suffix_variants(brand_counts: dict[str, int]) -> list[dict]:
    """
    Geographic / legal suffix pattern: "nestle france" → "nestle"
    when "nestle" exists as a standalone brand in the DB.

    Only flags when the stripped form is itself a brand in the DB.
    """
    brands = set(brand_counts.keys())
    results: list[dict] = []
    seen_variants: set[str] = set()

    for brand in sorted(brand_counts.keys(), key=lambda b: -brand_counts[b]):
        if brand in seen_variants:
            continue
        for suffix in GEO_SUFFIXES:
            if brand.endswith(suffix) and len(brand) > len(suffix) + 2:
                canonical = brand[: -len(suffix)].strip()
                if canonical in brands and canonical != brand:
                    c_count = brand_counts[canonical]
                    v_count = brand_counts[brand]
                    confidence = "high" if c_count >= v_count else "medium"
                    results.append({
                        "variant_brand":   brand,
                        "canonical_brand": canonical,
                        "pattern":         "geo_suffix",
                        "variant_count":   v_count,
                        "canonical_count": c_count,
                        "confidence":      confidence,
                        "action":          "",
                        "notes":           f"suffix removed: '{suffix.strip()}'",
                    })
                    seen_variants.add(brand)
                    break  # apply only the longest matching suffix
    return results


def merge_alias_candidates(
    prefix_results: list[dict],
    punct_results: list[dict],
    geo_results: list[dict],
) -> list[dict]:
    """
    Merge alias candidates from all three detectors. When a brand is
    detected by multiple patterns, keep the highest-confidence one and
    annotate the pattern. Sorted by confidence then variant_count.
    """
    conf_rank = {"high": 0, "medium": 1, "low": 2}
    seen: dict[str, dict] = {}

    for row in punct_results + prefix_results + geo_results:
        v = row["variant_brand"]
        if v not in seen or conf_rank[row["confidence"]] < conf_rank[seen[v]["confidence"]]:
            seen[v] = row

    merged = list(seen.values())
    merged.sort(key=lambda r: (conf_rank[r["confidence"]], -r["variant_count"]))
    return merged


# ── Main ──────────────────────────────────────────────────────────────────────

def run_coverage() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return
    if not MAPPING_PATH.exists():
        print(f"Mapping file not found: {MAPPING_PATH}")
        return

    # ── 1. Company coverage report ───────────────────────────────────────────
    mapping, statuses_by_brand = load_mapping()
    match_candidates = flatten_company_candidates(mapping)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT primary_brand, COUNT(*) AS n
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(primary_brand) != ''
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
        GROUP BY primary_brand
        ORDER BY n DESC
    """).fetchall()
    conn.close()

    brand_counts: dict[str, int] = {brand: n for brand, n in rows}
    total = len(rows)

    coverage_results = []
    direct_count = 0
    scoped_review_count = 0
    for brand, n in rows:
        norm = _normalize(brand)
        statuses = statuses_by_brand.get(norm)
        if statuses == {"direct"}:
            direct_count += 1
            continue
        if statuses:
            scoped_review_count += 1
            coverage_results.append({
                "primary_brand_in_db":    brand,
                "product_count":          n,
                "normalized_form":        norm,
                "coverage_status":        "scoped_or_manual_review",
                "mapping_statuses":       "|".join(sorted(statuses)),
                "weak_similarity_hint":   "",
                "similarity_score":       "",
                "requires_review_reason": "mapped, but ownership is market-scoped or has a manual-review fallback",
                "action":                 "review_scope",
            })
            continue
        # Fuzzy matching is only a weak review hint, not ownership attribution.
        # Limit it to material brands so this diagnostic stays fast.
        if n >= 10:
            suggested_company, score = best_company_match(norm, match_candidates)
        else:
            suggested_company, score = "", 0.0
        coverage_results.append({
            "primary_brand_in_db":    brand,
            "product_count":          n,
            "normalized_form":        norm,
            "coverage_status":        "unmapped",
            "mapping_statuses":       "",
            "weak_similarity_hint":   suggested_company if score >= 0.8 else "",
            "similarity_score":       score if score >= 0.8 else "",
            "requires_review_reason": "no primary_brand_db match in company_brand_mapping.csv",
            "action":                 "review",
        })

    print(f"\n{'='*60}")
    print(f"COMPANY COVERAGE REPORT")
    print(f"{'='*60}")
    print(f"Total distinct brands in DB: {total:,}")
    print(f"Resolved direct mappings:    {direct_count:,} ({100*direct_count/total:.1f}%)")
    print(f"Scoped/manual-review mapped: {scoped_review_count:,}")
    print(f"Need review in report:       {len(coverage_results):,}")
    print(f"\nTop 10 report rows by product count:")
    for r in coverage_results[:10]:
        hint = (
            f" -> weak hint {r['weak_similarity_hint']} ({r['similarity_score']})"
            if r["weak_similarity_hint"]
            else ""
        )
        print(
            f"  {r['primary_brand_in_db']:35s}  "
            f"n={r['product_count']:5,}  "
            f"{r['coverage_status']}{hint}"
        )

    if coverage_results:
        with open(COVERAGE_OUT, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(coverage_results[0].keys()))
            writer.writeheader()
            writer.writerows(coverage_results)
        print(f"\nSaved -> {COVERAGE_OUT.name}")

    # ── 2. Brand alias candidates (new) ───────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"BRAND ALIAS DETECTION")
    print(f"{'='*60}")

    prefix_r = detect_prefix_aliases(brand_counts)
    punct_r  = detect_punctuation_variants(brand_counts)
    geo_r    = detect_geo_suffix_variants(brand_counts)
    all_r    = merge_alias_candidates(prefix_r, punct_r, geo_r)

    high   = [r for r in all_r if r["confidence"] == "high"]
    medium = [r for r in all_r if r["confidence"] == "medium"]

    print(f"Prefix variants detected:       {len(prefix_r):,}")
    print(f"Punctuation variants detected:  {len(punct_r):,}")
    print(f"Geographic suffix detected:     {len(geo_r):,}")
    print(f"Total after deduplication:      {len(all_r):,}")
    print(f"  High confidence:   {len(high):,}")
    print(f"  Medium confidence: {len(medium):,}")

    print(f"\nTop 15 candidates (high confidence first):")
    for r in all_r[:15]:
        print(
            f"  [{r['confidence']:6s}] {r['variant_brand']:35s} "
            f"-> {r['canonical_brand']:25s}  "
            f"({r['pattern']}, n={r['variant_count']})"
        )

    if all_r:
        with open(ALIAS_OUT, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f, fieldnames=["variant_brand", "canonical_brand", "pattern",
                               "variant_count", "canonical_count",
                               "confidence", "action", "notes"]
            )
            writer.writeheader()
            writer.writerows(all_r)
        print(f"\nSaved -> {ALIAS_OUT.name}")

    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print(f"1. Open data/reference/brand_alias_candidates.csv")
    print(f"2. Review candidate rows individually; do not bulk-confirm by confidence alone")
    print(f"3. Append approved rows to the existing curated file:")
    print(f"   data/reference/brand_alias_mapping.csv")
    print(f"4. Do not overwrite brand_alias_mapping.csv with the candidate file")
    print(f"5. Re-run the pipeline from clean.py onward")


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand/company mapping diagnostics.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--counts", action="store_true", help="Write and print brand counts.")
    mode.add_argument("--coverage", action="store_true", help="Write coverage and alias-candidate reports.")
    mode.add_argument("--check-brand", metavar="PREFIX", help="Print variants starting with a brand prefix.")
    mode.add_argument("--unmapped", action="store_true", help="Print unmapped/scoped mapping coverage.")
    args = parser.parse_args()

    if args.counts:
        run_counts()
    elif args.check_brand:
        run_check_brand(args.check_brand)
    elif args.unmapped:
        run_unmapped()
    else:
        run_coverage()


if __name__ == "__main__":
    main()
