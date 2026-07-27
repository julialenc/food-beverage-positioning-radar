"""
Reality band assignment for sampling.

Classifies each product into a reality band (low / typical / high) per
metric, within its own region x category distribution, using QUARTILE
cut-points (P25/P75) from region_category_benchmarks.

Two distinct band systems in this project — do not conflate (spec):
  - SAMPLING reality bands (this file): data-driven quartiles. Purpose is
    to spread the sample across the actual distribution shape, so we don't
    over-sample the crowded middle and miss the tails.
  - REPORTING bands (the dashboard's ↑/≈/↓): fixed 110/90 index vs.
    benchmark. Purpose is a human-readable, corporate-standard 10%
    tolerance. NOT used for sampling.

Metric selection per category (spec + the per-100ml work):
  - beverages -> per-100ml (_ml) metrics: per-100kcal is unstable for
    near-zero-energy drinks.
  - all other categories -> per-100kcal (_eff) metrics.
  energy_kcal itself is always used as-is (it IS the reality for energy).

ZERO-HEAVY FALLBACK (spec): standard quartile banding assumes P25 < P75
with a meaningful spread. When a metric has so many genuine zeros that
P25 == 0 (dairy fibre, beverage saturated fat, etc. — confirmed in the
null-vs-zero audit), the low/typical boundary collapses: "< P25" is empty
and every zero-value product lands in "typical", which is wrong — a
zero-fibre product is at the BOTTOM of the fibre distribution, not the
middle. Fallback rule when P25 == 0:
    value == 0            -> "low"        (zero is the bottom band)
    0 < value <= P75      -> "typical"
    value > P75           -> "high"
This keeps three bands and puts zeros where they belong. If P75 is ALSO 0
(a metric that is zero for >75% of products — e.g. fibre in a pure-water
beverage set), the distribution can't support 3 bands at all; we collapse
to two: value == 0 -> "low", value > 0 -> "high", and record band_method
= "binary_zero" so the sampler knows this metric has no usable middle.

Every classification records HOW it was banded (band_method) so the
sampler and any later audit can see which products got the normal
quartile rule vs. a fallback.

Usage: python pipeline/assign_reality_bands.py
Writes: pipeline/reality_bands.csv
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT_CSV = Path(__file__).resolve().parent / "reality_bands.csv"

DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}

# Same hard-plausibility rules as the benchmark script — a product with a
# hard-invalid value on a metric is not banded for that metric (band = None).
_HARD_RANGES: dict[str, tuple[float, float | None]] = {
    "energy_kcal":        (0.0, 900.0),
    "protein_per_kcal":   (0.0, 30.0),
    "satfat_per_kcal":    (0.0, 11.1),
    "fiber_per_kcal":     (0.0, None),
    "sugars_per_kcal":    (0.0, None),
    "protein_100g":       (0.0, 100.0),
    "sugars_100g":        (0.0, 100.0),
    "fiber_100g":         (0.0, 100.0),
    "saturated_fat_100g": (0.0, 100.0),
}

# Logical metric -> (per-kcal product column, per-kcal benchmark prefix,
#                    per-100ml product column, per-100ml benchmark prefix)
# The sampler picks the ml variant for beverages, eff otherwise.
_METRIC_MAP = {
    "energy":  ("energy_kcal",      "energy",      "energy_kcal",        "energy"),
    "protein": ("protein_per_kcal", "protein_eff", "protein_100g",       "protein_ml"),
    "fibre":   ("fiber_per_kcal",   "fibre_eff",   "fiber_100g",         "fibre_ml"),
    "satfat":  ("satfat_per_kcal",  "satfat_eff",  "saturated_fat_100g", "satfat_ml"),
    "sugars":  ("sugars_per_kcal",  "sugars_eff",  "sugars_100g",        "sugars_ml"),
}

BEVERAGE_CATEGORY = "beverages"


def load_products(conn) -> pd.DataFrame:
    df = pd.read_sql_query("""
        SELECT barcode, query_category AS category, observed_market_region_codes,
               energy_kcal, protein_100g, saturated_fat_100g, sugars_100g, fiber_100g
        FROM products
        WHERE primary_brand IS NOT NULL
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


def load_benchmarks(conn) -> pd.DataFrame:
    snapshot = conn.execute(
        "SELECT MAX(snapshot) FROM region_category_benchmarks"
    ).fetchone()[0]
    return pd.read_sql_query(
        "SELECT * FROM region_category_benchmarks WHERE snapshot = ?",
        conn, params=[snapshot],
    )


def _hard_valid_scalar(value, metric_col) -> bool:
    if pd.isna(value):
        return False
    lo, hi = _HARD_RANGES[metric_col]
    if value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


def assign_band(value, p25, p75) -> tuple[str | None, str]:
    """Return (band, band_method). value already confirmed hard-valid."""
    if p25 is None or p75 is None or pd.isna(p25) or pd.isna(p75):
        return None, "no_benchmark"

    # Zero-heavy fallbacks first.
    if p75 == 0:
        # >75% of products are zero — no usable middle band.
        return ("low" if value == 0 else "high"), "binary_zero"
    if p25 == 0:
        # Many zeros, but a usable upper spread. Zeros are the bottom band.
        if value == 0:
            return "low", "zero_floor"
        if value <= p75:
            return "typical", "zero_floor"
        return "high", "zero_floor"

    # Standard quartile banding.
    if value < p25:
        return "low", "quartile"
    if value <= p75:
        return "typical", "quartile"
    return "high", "quartile"


def region_of(codes) -> str | None:
    present = set(str(codes or "").split("|")) & DOWNLOAD_SCOPE_REGIONS
    return sorted(present)[0] if present else None


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    products = load_products(conn)
    benchmarks = load_benchmarks(conn)
    conn.close()

    # Index benchmarks by (region, category) for fast lookup.
    bench_idx = {(r["region_code"], r["category"]): r
                 for _, r in benchmarks.iterrows()}

    out_rows = []
    for _, p in products.iterrows():
        region = region_of(p["observed_market_region_codes"])
        category = str(p["category"]).lower()
        if region is None:
            continue
        bench = bench_idx.get((region, category))
        if bench is None:
            continue

        is_bev = (category == BEVERAGE_CATEGORY)
        row = {"barcode": p["barcode"], "region_code": region,
               "category": category, "metric_basis": "per_100ml" if is_bev else "per_100kcal"}

        for logical, (eff_col, eff_pref, ml_col, ml_pref) in _METRIC_MAP.items():
            if logical == "energy":
                # Energy uses the same raw kcal value and 'energy' benchmark
                # for every category — there's no per-ml vs per-kcal split.
                metric_col, pref = eff_col, eff_pref
            elif is_bev:
                metric_col, pref = ml_col, ml_pref
            else:
                metric_col, pref = eff_col, eff_pref

            value = p[metric_col]
            if not _hard_valid_scalar(value, metric_col):
                row[f"{logical}_band"] = None
                row[f"{logical}_band_method"] = "invalid_or_missing"
                continue
            band, method = assign_band(value, bench[f"{pref}_p25"], bench[f"{pref}_p75"])
            row[f"{logical}_band"] = band
            row[f"{logical}_band_method"] = method

        out_rows.append(row)

    out = pd.DataFrame(out_rows)
    out.to_csv(OUT_CSV, index=False)
    print(f"Banded {len(out):,} products (US/UK/FR in-scope with a benchmark).")
    print(f"Wrote {OUT_CSV}\n")

    # Audit: band distribution + which fallback method was used, per metric.
    for logical in _METRIC_MAP:
        bcol, mcol = f"{logical}_band", f"{logical}_band_method"
        print(f"--- {logical} ---")
        print("  bands:  " + out[bcol].value_counts(dropna=False).to_dict().__repr__())
        print("  method: " + out[mcol].value_counts(dropna=False).to_dict().__repr__())
    print()
    # Highlight metrics that fell back — those are where the naive quartile
    # rule would have mis-banded zeros.
    print("Metrics using a zero-heavy fallback anywhere (by region/category):")
    for logical in _METRIC_MAP:
        mcol = f"{logical}_band_method"
        fell_back = out[out[mcol].isin(["zero_floor", "binary_zero"])]
        if len(fell_back):
            combos = fell_back.groupby(["category", "region_code"])[mcol].agg(
                lambda s: s.value_counts().index[0])
            print(f"  {logical}: {dict(combos)}")


if __name__ == "__main__":
    main()
