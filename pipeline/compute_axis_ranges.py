"""
Compute axis display ranges for Market Overview's Product Landscape scatter.

Two different kinds of number, two different treatments:

1. HARD PLAUSIBILITY CEILINGS — fixed domain constants (chemistry/physics),
   not data-dependent. Defined once below as _HARD_RANGES. Checked live in
   the app too (cheap, vectorized) — nothing about these needs storing.
   Values outside a hard ceiling are EXCLUDED from the percentile
   computation below (they are invalid records, not legitimate outliers —
   e.g. protein/100kcal above ~30 implies a bad energy denominator, unit
   error, or per-pack/per-100g mixup).

2. THE P99.5 DISPLAY RANGE — genuinely depends on the actual data
   distribution per region x category x metric, so THIS is what gets
   precomputed and stored here, once per pipeline snapshot. Streamlit
   looks this up rather than recomputing percentiles on every rerun.

display_max = min(hard_max, P99.5 * 1.05) when a hard ceiling exists,
else just P99.5 * 1.05 (fibre/sugars per kcal have no hard physical
ceiling — a legitimately low-energy, high-fibre product can produce a
large ratio; only protein and (sat)fat per kcal have a clean physical
ceiling, since protein/fat have a fixed kcal/g conversion).

ratio_unstable: per-100kcal metrics divide by energy, so a very small
(but valid, nonzero) energy denominator can blow up an otherwise-correct
ratio. This is flagged, not excluded — the value stays in the "valid"
population feeding the percentile computation (per-spec: do not assume a
large fibre/100kcal value is wrong).

Usage: python pipeline/compute_axis_ranges.py
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"

SNAPSHOT = date.today().isoformat()

# Energy below this (but > 0) makes any per-100kcal ratio numerically
# unstable — small denominator amplifies rounding/measurement noise.
ENERGY_UNSTABLE_THRESHOLD = 10.0  # kcal/100g or 100ml

# Same scope as shared/db.py's DOWNLOAD_SCOPE_REGIONS. Duplicated rather
# than imported (this script has no Streamlit dependency), but MUST be
# kept in sync — see docs/ONBOARDING.md for the authoritative scope.
# observed_market_region_codes can legitimately contain codes outside this
# set too (a French product can also carry a German/Italian OFF country
# tag), but Market Overview only ever offers these 3 as a selectable
# Region — computing ranges for the others is wasted work for a region
# nobody can select.
DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}

# metric_key -> (raw/derived column, hard_min, hard_max or None)
# hard_max=None means no physical ceiling exists for this metric
# (fibre/sugars per kcal) — only the ratio_unstable flag applies.
_HARD_RANGES: dict[str, tuple[str, float, float | None]] = {
    "energy_kcal":        ("energy_kcal",        0.0, 900.0),
    "protein_100g":       ("protein_100g",        0.0, 100.0),
    "fat_100g":           ("fat_100g",            0.0, 100.0),
    "saturated_fat_100g": ("saturated_fat_100g",  0.0, 100.0),
    "carbs_100g":         ("carbs_100g",          0.0, 100.0),
    "sugars_100g":        ("sugars_100g",         0.0, 100.0),
    "fiber_100g":         ("fiber_100g",          0.0, 100.0),
    "salt_100g":          ("salt_100g",           0.0, 100.0),
    "protein_per_kcal":   ("protein_per_kcal",    0.0, 30.0),
    "satfat_per_kcal":    ("satfat_per_kcal",     0.0, 11.1),
    "fiber_per_kcal":     ("fiber_per_kcal",      0.0, None),
    "sugars_per_kcal":    ("sugars_per_kcal",     0.0, None),
}
_PER_KCAL_KEYS = {"protein_per_kcal", "fiber_per_kcal", "satfat_per_kcal", "sugars_per_kcal"}

DDL = """
CREATE TABLE IF NOT EXISTS axis_range_config (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot                TEXT NOT NULL,
    region_code             TEXT NOT NULL,
    category                TEXT NOT NULL,
    metric_key              TEXT NOT NULL,
    hard_min                REAL,
    hard_max                REAL,
    p99_5                   REAL,
    display_max             REAL,
    n_valid                 INTEGER,     -- passes hard-range check
    n_flagged_invalid       INTEGER,     -- fails hard-range check, excluded
    n_ratio_unstable        INTEGER,     -- valid but tiny-energy-denominator (per-kcal metrics only)
    n_outside_display_range INTEGER,     -- valid, but above display_max
    computed_at             TEXT
);
CREATE INDEX IF NOT EXISTS idx_axis_range_lookup
    ON axis_range_config(snapshot, region_code, category, metric_key);
"""


def load_region_category_data(conn) -> pd.DataFrame:
    """Same population and per-kcal derivation as shared/db.py's
    get_market_products — deliberately duplicated rather than imported,
    since this is a pipeline script (no Streamlit dependency) and the
    logic is simple enough that duplication is clearer than a shared
    import across the pipeline/app boundary."""
    df = pd.read_sql_query("""
        SELECT energy_kcal, protein_100g, fat_100g, saturated_fat_100g,
               carbs_100g, sugars_100g, fiber_100g, salt_100g,
               query_category AS category, observed_market_region_codes
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    """, conn)

    for col in ["energy_kcal", "protein_100g", "fat_100g", "saturated_fat_100g",
                "carbs_100g", "sugars_100g", "fiber_100g", "salt_100g"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid_energy = df["energy_kcal"].notna() & (df["energy_kcal"] > 0)
    kcal = df["energy_kcal"].where(valid_energy)
    df["protein_per_kcal"] = (df["protein_100g"]       / kcal * 100).where(valid_energy)
    df["fiber_per_kcal"]   = (df["fiber_100g"]         / kcal * 100).where(valid_energy)
    df["satfat_per_kcal"]  = (df["saturated_fat_100g"] / kcal * 100).where(valid_energy)
    df["sugars_per_kcal"]  = (df["sugars_100g"]        / kcal * 100).where(valid_energy)
    df["_energy_unstable"] = valid_energy & (df["energy_kcal"] < ENERGY_UNSTABLE_THRESHOLD)

    return df


def compute_ranges_for_scope(df: pd.DataFrame, region_code: str, category: str) -> list[dict]:
    scope = df[
        df["category"].str.lower().eq(category.lower())
        & df["observed_market_region_codes"].str.contains(region_code, na=False)
    ]
    rows = []
    for metric_key, (col, hard_min, hard_max) in _HARD_RANGES.items():
        series = scope[col]
        non_null = series.dropna()
        if hard_max is not None:
            valid_mask = (non_null >= hard_min) & (non_null <= hard_max)
        else:
            valid_mask = non_null >= hard_min
        valid = non_null[valid_mask]
        n_flagged_invalid = int((~valid_mask).sum())

        if metric_key in _PER_KCAL_KEYS:
            n_ratio_unstable = int(scope.loc[valid.index, "_energy_unstable"].sum())
        else:
            n_ratio_unstable = 0

        if len(valid) == 0:
            p99_5 = None
            display_max = hard_max
            n_outside = 0
        else:
            p99_5 = float(valid.quantile(0.995))
            padded = p99_5 * 1.05
            display_max = min(hard_max, padded) if hard_max is not None else padded
            n_outside = int((valid > display_max).sum())

        rows.append(dict(
            snapshot=SNAPSHOT, region_code=region_code, category=category,
            metric_key=metric_key, hard_min=hard_min, hard_max=hard_max,
            p99_5=p99_5, display_max=display_max,
            n_valid=len(valid), n_flagged_invalid=n_flagged_invalid,
            n_ratio_unstable=n_ratio_unstable, n_outside_display_range=n_outside,
            computed_at=pd.Timestamp.now().isoformat(timespec="seconds"),
        ))
    return rows


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    df = load_region_category_data(conn)
    all_codes_present = set(
        code
        for codes in df["observed_market_region_codes"].dropna()
        for code in str(codes).split("|") if code
    )
    region_codes = sorted(all_codes_present & DOWNLOAD_SCOPE_REGIONS)
    _out_of_scope = all_codes_present - DOWNLOAD_SCOPE_REGIONS
    if _out_of_scope:
        print(f"Note: ignoring {len(_out_of_scope)} out-of-scope region code(s) "
              f"present in the data (secondary OFF country tags, not a "
              f"selectable Region): {sorted(_out_of_scope)}")
    categories = sorted(df["category"].dropna().str.lower().unique())

    all_rows: list[dict] = []
    for region_code in region_codes:
        for category in categories:
            all_rows.extend(compute_ranges_for_scope(df, region_code, category))

    conn.execute("DELETE FROM axis_range_config WHERE snapshot = ?", (SNAPSHOT,))
    conn.executemany(f"""
        INSERT INTO axis_range_config
        ({', '.join(all_rows[0].keys())})
        VALUES ({', '.join('?' for _ in all_rows[0])})
    """, [tuple(r.values()) for r in all_rows])
    conn.commit()

    print(f"Computed axis ranges for {len(region_codes)} regions x "
          f"{len(categories)} categories x {len(_HARD_RANGES)} metrics "
          f"= {len(all_rows)} rows, snapshot {SNAPSHOT}.")
    total_flagged = sum(r["n_flagged_invalid"] for r in all_rows)
    print(f"Total hard-implausible values flagged across all combinations: {total_flagged}")
    conn.close()


if __name__ == "__main__":
    main()
