"""
Compute By Region's fixed 12-row (3 region x 4 category) benchmark table.

Medians and P25/P75, not means — deliberately. Two reasons:
1. Section 3 itself displays medians (spec section 6).
2. compute_profile_intersections.py's benchmark MUST use the same
   statistic as what's displayed here, per spec section 14 ("this avoids
   a situation in which Section 3 displays medians while Section 2
   silently compares products with a different statistic"). That script
   now reads its benchmark from THIS table rather than computing its own
   mean — see the note in that file. Run this script BEFORE
   compute_profile_intersections.py; the latter depends on this one's
   output.

Hard-invalid values (same _HARD_RANGES as compute_axis_ranges.py and
compute_profile_intersections.py) are excluded from every median/quantile
calculation. Genuine extreme-but-valid values are NOT trimmed here (no
P99.5) — that trimming exists only to keep Product Landscape's scatter
visually usable; medians/quartiles are naturally robust to a few extreme
values, so there's no equivalent need here (spec section 13).

PER-100ML METRICS (protein_ml/sugars_ml/fibre_ml/satfat_ml): per-100kcal
ratios are unstable for beverages — a near-zero-energy drink (water,
diet soda) produces an exploding or undefined ratio. Per-100ml doesn't
divide by energy at all, so it's the stable reality metric for beverages.
OFF stores liquids normalized to 100ml under the _100g column name
(density ~1 for most drinks), so per-100ml IS the raw per-100g nutrient
value directly — no derivation. Computed for all categories (cheap,
harmless), but analytically these are the beverage benchmark; solids keep
using the per-100kcal (_eff) metrics.

Usage: python pipeline/compute_region_benchmarks.py
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).resolve().parent.parent
DB_PATH  = ROOT / "database" / "positioning_radar.db"
SNAPSHOT = date.today().isoformat()

DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}

# Same hard-plausibility rules as the other two precompute scripts.
_HARD_RANGES: dict[str, tuple[float, float | None]] = {
    "energy_kcal":      (0.0, 900.0),
    "protein_per_kcal": (0.0, 30.0),
    "satfat_per_kcal":  (0.0, 11.1),
    "fiber_per_kcal":   (0.0, None),
    "sugars_per_kcal":  (0.0, None),
    # Raw per-100g (= per-100ml for liquids — OFF normalizes liquids to
    # 100ml and stores under the _100g name; density ~1 for most drinks).
    # These are the STABLE beverage reality metrics: per-100kcal ratios
    # blow up for near-zero-energy drinks, but per-100ml doesn't divide by
    # energy at all. 0-100g physical bounds, same as bootstrap's per-100g
    # ceilings.
    "protein_100g": (0.0, 100.0),
    "sugars_100g":  (0.0, 100.0),
    "fiber_100g":   (0.0, 100.0),
    "saturated_fat_100g": (0.0, 100.0),
}

DDL = """
CREATE TABLE IF NOT EXISTS region_category_benchmarks (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot             TEXT NOT NULL,
    region_code          TEXT NOT NULL,
    category             TEXT NOT NULL,
    product_count        INTEGER,
    energy_median        REAL, energy_p25 REAL, energy_p75 REAL, energy_valid_n INTEGER,
    protein_eff_median   REAL, protein_eff_p25 REAL, protein_eff_p75 REAL, protein_eff_valid_n INTEGER,
    fibre_eff_median     REAL, fibre_eff_p25 REAL, fibre_eff_p75 REAL, fibre_eff_valid_n INTEGER,
    satfat_eff_median    REAL, satfat_eff_p25 REAL, satfat_eff_p75 REAL, satfat_eff_valid_n INTEGER,
    sugars_eff_median    REAL, sugars_eff_p25 REAL, sugars_eff_p75 REAL, sugars_eff_valid_n INTEGER,
    -- Per-100ml (raw per-100g) reality metrics — the STABLE beverage
    -- benchmark (per-100kcal is unstable for near-zero-energy drinks).
    -- Populated for all categories; used analytically for beverages.
    protein_ml_median    REAL, protein_ml_p25 REAL, protein_ml_p75 REAL, protein_ml_valid_n INTEGER,
    sugars_ml_median     REAL, sugars_ml_p25 REAL, sugars_ml_p75 REAL, sugars_ml_valid_n INTEGER,
    fibre_ml_median      REAL, fibre_ml_p25 REAL, fibre_ml_p75 REAL, fibre_ml_valid_n INTEGER,
    satfat_ml_median     REAL, satfat_ml_p25 REAL, satfat_ml_p75 REAL, satfat_ml_valid_n INTEGER,
    nova_classified_n    INTEGER,
    nova4_n              INTEGER,
    nova4_pct            REAL,
    computed_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_region_benchmarks_lookup
    ON region_category_benchmarks(snapshot, region_code, category);
"""

# metric_key -> (raw column producing it, display name used in table columns)
_METRICS = {
    "energy":      "energy_kcal",
    "protein_eff": "protein_per_kcal",
    "fibre_eff":   "fiber_per_kcal",
    "satfat_eff":  "satfat_per_kcal",
    "sugars_eff":  "sugars_per_kcal",
    # Per-100ml (raw per-100g) — stable beverage reality metrics.
    "protein_ml":  "protein_100g",
    "sugars_ml":   "sugars_100g",
    "fibre_ml":    "fiber_100g",
    "satfat_ml":   "saturated_fat_100g",
}


def load_data(conn) -> pd.DataFrame:
    df = pd.read_sql_query("""
        SELECT energy_kcal, protein_100g, saturated_fat_100g, sugars_100g,
               fiber_100g, nova_group, query_category AS category,
               observed_market_region_codes
        FROM products
        WHERE primary_brand IS NOT NULL
          AND ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(include_in_product_table, 1) = 1
          AND COALESCE(include_in_aggregates, 1) = 1
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    """, conn)
    for col in ["energy_kcal", "protein_100g", "saturated_fat_100g",
                "sugars_100g", "fiber_100g"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid_energy = df["energy_kcal"].notna() & (df["energy_kcal"] > 0)
    kcal = df["energy_kcal"].where(valid_energy)
    df["protein_per_kcal"] = (df["protein_100g"]       / kcal * 100).where(valid_energy)
    df["fiber_per_kcal"]   = (df["fiber_100g"]         / kcal * 100).where(valid_energy)
    df["satfat_per_kcal"]  = (df["saturated_fat_100g"] / kcal * 100).where(valid_energy)
    df["sugars_per_kcal"]  = (df["sugars_100g"]        / kcal * 100).where(valid_energy)
    return df


def _hard_valid(series: pd.Series, metric_key: str) -> pd.Series:
    lo, hi = _HARD_RANGES[metric_key]
    mask = series.notna() & (series >= lo)
    if hi is not None:
        mask = mask & (series <= hi)
    return mask


def compute_row(scope: pd.DataFrame) -> dict:
    row: dict = {"product_count": len(scope)}

    for prefix, metric_key in _METRICS.items():
        valid = scope.loc[_hard_valid(scope[metric_key], metric_key), metric_key]
        if len(valid) >= 10:
            row[f"{prefix}_median"]  = float(valid.median())
            row[f"{prefix}_p25"]     = float(valid.quantile(0.25))
            row[f"{prefix}_p75"]     = float(valid.quantile(0.75))
        else:
            row[f"{prefix}_median"] = row[f"{prefix}_p25"] = row[f"{prefix}_p75"] = None
        row[f"{prefix}_valid_n"] = int(len(valid))

    nova_classified = scope["nova_group"].dropna()
    nova_classified = nova_classified[nova_classified.isin([1, 2, 3, 4])]
    nova4_n = int((nova_classified == 4).sum())
    row["nova_classified_n"] = int(len(nova_classified))
    row["nova4_n"] = nova4_n
    row["nova4_pct"] = (nova4_n / len(nova_classified) * 100) if len(nova_classified) else None

    return row


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    df = load_data(conn)
    categories = sorted(df["category"].dropna().str.lower().unique())

    all_rows: list[dict] = []
    for region_code in sorted(DOWNLOAD_SCOPE_REGIONS):
        for category in categories:
            scope = df[
                df["category"].str.lower().eq(category)
                & df["observed_market_region_codes"].str.contains(region_code, na=False)
            ]
            row = compute_row(scope)
            row.update(
                snapshot=SNAPSHOT, region_code=region_code, category=category,
                computed_at=pd.Timestamp.now().isoformat(timespec="seconds"),
            )
            all_rows.append(row)

    conn.execute("DELETE FROM region_category_benchmarks WHERE snapshot = ?", (SNAPSHOT,))
    if all_rows:
        cols = list(all_rows[0].keys())
        conn.executemany(
            f"INSERT INTO region_category_benchmarks ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)})",
            [tuple(r[c] for c in cols) for r in all_rows],
        )
    conn.commit()

    print(f"Computed region/category benchmarks: {len(all_rows)} rows "
          f"({len(DOWNLOAD_SCOPE_REGIONS)} regions x {len(categories)} categories), "
          f"snapshot {SNAPSHOT}.")
    conn.close()


if __name__ == "__main__":
    main()
