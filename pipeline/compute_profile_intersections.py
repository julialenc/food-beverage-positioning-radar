"""
Compute Product Profile Landscape intersection counts.

Two subtleties that drove this design, both from the spec:

1. CONSTANT DENOMINATOR (spec section 8): the "eligible" population for a
   3-step profile uses valid data for ALL 3 dimensions — including at
   level 1. So if a user later adds a 3rd step, level 1's percentage
   actually changes (its denominator got stricter). This means what must
   be precomputed isn't "count matching each dimension alone" — it's,
   for every possible FULL 1-3 dimension profile S, the eligible count for
   S, and the matching count of every non-empty sub-collection of S
   *within that same eligible(S) population*. Since AND-intersection is
   commutative, only the unordered subset matters for counts — the user's
   chosen step ORDER only determines which stored sub-collection to look
   up and how to label it, not a new computation.

2. HARD-INVALID EXCLUSION AT THE PRODUCT-DIMENSION LEVEL, not just the
   benchmark (spec section 15): a product with a hard-implausible
   protein/100kcal value isn't just excluded from the benchmark — it's
   ineligible for the "protein" dimension entirely, in any profile that
   includes it. Genuine-but-extreme values (e.g. a legitimately
   low-energy high-fibre product) are NOT excluded — they stay eligible
   and get classified normally. Same _HARD_RANGES rules as
   compute_axis_ranges.py, duplicated rather than imported (no shared
   pipeline/app dependency), must stay in sync with that file.

3. BENCHMARK SOURCE (spec section 14): the benchmark used for each
   dimension's index calculation is READ from
   region_category_benchmarks (computed by compute_region_benchmarks.py),
   not computed independently here. Earlier versions of this script used
   their own protected mean — changed to reading Section 3's median once
   Section 3 existed, per the spec's explicit requirement that Section 2
   never silently compare products against a different reference
   statistic than what Section 3 displays. RUN ORDER MATTERS: run
   compute_region_benchmarks.py BEFORE this script.

Usage:
    python pipeline/compute_region_benchmarks.py    (first)
    python pipeline/compute_profile_intersections.py (second)
"""

from __future__ import annotations

import itertools
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).resolve().parent.parent
DB_PATH  = ROOT / "database" / "positioning_radar.db"
SNAPSHOT = date.today().isoformat()

DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}

# Same hard-plausibility rules as compute_axis_ranges.py.
_HARD_RANGES: dict[str, tuple[float, float | None]] = {
    "energy_kcal":      (0.0, 900.0),
    "protein_per_kcal": (0.0, 30.0),
    "satfat_per_kcal":  (0.0, 11.1),
    "fiber_per_kcal":   (0.0, None),
    "sugars_per_kcal":  (0.0, None),
}

# slot -> (metric_col, direction). NOVA is categorical, handled separately.
_DIMENSIONS: dict[str, tuple[str | None, str | None]] = {
    "protein": ("protein_per_kcal", "higher"),
    "fibre":   ("fiber_per_kcal",   "higher"),
    "sugar":   ("sugars_per_kcal",  "lower"),
    "satfat":  ("satfat_per_kcal",  "lower"),
    "energy":  ("energy_kcal",      "lower"),
    "nova":    (None, None),
}
_SLOTS = list(_DIMENSIONS.keys())
_NOVA_VARIANTS = ["nova_1_3", "nova_4"]
_CONDITION_KEY = {
    "protein": "protein_hi", "fibre": "fibre_hi", "sugar": "sugar_lo",
    "satfat": "satfat_lo", "energy": "energy_lo",
}

DDL = """
CREATE TABLE IF NOT EXISTS profile_intersections (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot           TEXT NOT NULL,
    region_code        TEXT NOT NULL,
    category           TEXT NOT NULL,
    full_subset_key    TEXT NOT NULL,
    sub_collection_key TEXT NOT NULL,
    eligible_count     INTEGER,
    matching_count     INTEGER,
    computed_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_profile_lookup
    ON profile_intersections(snapshot, region_code, category, full_subset_key, sub_collection_key);
"""


def load_data(conn) -> pd.DataFrame:
    df = pd.read_sql_query("""
        SELECT energy_kcal, protein_100g, saturated_fat_100g, sugars_100g,
               fiber_100g, nova_group, query_category AS category,
               observed_market_region_codes
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


def _hard_valid(series: pd.Series, metric_key: str) -> pd.Series:
    lo, hi = _HARD_RANGES[metric_key]
    mask = series.notna() & (series >= lo)
    if hi is not None:
        mask = mask & (series <= hi)
    return mask


def get_benchmarks(conn, region_code: str, category: str) -> dict[str, float | None]:
    """Reads the median benchmark from region_category_benchmarks
    (computed by compute_region_benchmarks.py — run that script FIRST)
    rather than computing an independent mean here. This is deliberate:
    spec section 14 requires Section 2's index calculation to use the
    exact same reference statistic Section 3 displays, so that a product
    is never silently compared against two different numbers depending
    on which part of the page you're looking at. A single stored table is
    the only way to guarantee that stays true rather than "should" stay
    true across two independently-computed values."""
    row = conn.execute("""
        SELECT protein_eff_median, fibre_eff_median, satfat_eff_median,
               sugars_eff_median, energy_median
        FROM region_category_benchmarks
        WHERE region_code = ? AND category = ?
        ORDER BY snapshot DESC LIMIT 1
    """, (region_code, category)).fetchone()
    if row is None:
        return {k: None for k in
                ["protein_per_kcal", "fiber_per_kcal", "satfat_per_kcal",
                 "sugars_per_kcal", "energy_kcal"]}
    return {
        "protein_per_kcal": row[0], "fiber_per_kcal": row[1],
        "satfat_per_kcal":  row[2], "sugars_per_kcal": row[3],
        "energy_kcal":       row[4],
    }


def compute_dimension_flags(scope: pd.DataFrame, benchmarks: dict) -> pd.DataFrame:
    """Per-product eligibility + condition-met flags for each of the 6
    slots. Eligibility excludes hard-invalid values, not just missing
    ones — a product with an implausible ratio is ineligible for that
    dimension in any profile, same as a product with no value at all."""
    flags = pd.DataFrame(index=scope.index)

    for dim, (metric_key, direction) in _DIMENSIONS.items():
        if dim == "nova":
            continue
        bench = benchmarks.get(metric_key)
        eligible = _hard_valid(scope[metric_key], metric_key)
        flags[f"eligible_{dim}"] = eligible
        if bench is None or bench == 0:
            flags[f"meets_{dim}"] = False
        else:
            idx = scope[metric_key] / bench * 100
            flags[f"meets_{dim}"] = (idx >= 110) if direction == "higher" else (idx <= 90)

    nova_valid = scope["nova_group"].notna() & scope["nova_group"].isin([1, 2, 3, 4])
    flags["eligible_nova"]  = nova_valid
    flags["meets_nova_1_3"] = nova_valid & scope["nova_group"].isin([1, 2, 3])
    flags["meets_nova_4"]   = nova_valid & (scope["nova_group"] == 4)

    return flags


def _condition_key(slot: str, nova_variant: str | None) -> str:
    return nova_variant if slot == "nova" else _CONDITION_KEY[slot]


def generate_full_subsets():
    """Every full subset of size 1-3 from the 6 slots, expanding NOVA
    into its 2 mutually-exclusive variants."""
    for size in (1, 2, 3):
        for combo in itertools.combinations(_SLOTS, size):
            if "nova" in combo:
                for variant in _NOVA_VARIANTS:
                    yield combo, variant
            else:
                yield combo, None


def compute_intersections_for_scope(flags: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for slot_combo, nova_variant in generate_full_subsets():
        eligible_mask = pd.Series(True, index=flags.index)
        for slot in slot_combo:
            eligible_mask = eligible_mask & flags[f"eligible_{slot}"]
        eligible_count = int(eligible_mask.sum())

        full_subset_key = "|".join(sorted(
            _condition_key(s, nova_variant) for s in slot_combo
        ))

        for r in range(1, len(slot_combo) + 1):
            for sub_combo in itertools.combinations(slot_combo, r):
                sub_collection_key = "|".join(sorted(
                    _condition_key(s, nova_variant) for s in sub_combo
                ))
                matching_mask = eligible_mask.copy()
                for s in sub_combo:
                    meets_col = f"meets_{nova_variant}" if s == "nova" else f"meets_{s}"
                    matching_mask = matching_mask & flags[meets_col]
                matching_count = int(matching_mask.sum())

                rows.append(dict(
                    full_subset_key=full_subset_key,
                    sub_collection_key=sub_collection_key,
                    eligible_count=eligible_count,
                    matching_count=matching_count,
                ))
    return rows


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
            if len(scope) < 10:
                continue
            benchmarks = get_benchmarks(conn, region_code, category)
            flags = compute_dimension_flags(scope, benchmarks)
            for row in compute_intersections_for_scope(flags):
                row.update(
                    snapshot=SNAPSHOT, region_code=region_code, category=category,
                    computed_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                )
                all_rows.append(row)

    conn.execute("DELETE FROM profile_intersections WHERE snapshot = ?", (SNAPSHOT,))
    if all_rows:
        cols = list(all_rows[0].keys())
        conn.executemany(
            f"INSERT INTO profile_intersections ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)})",
            [tuple(r[c] for c in cols) for r in all_rows],
        )
    conn.commit()

    n_combos = len(DOWNLOAD_SCOPE_REGIONS) * len(categories)
    print(f"Computed profile intersections for up to {n_combos} region x category "
          f"combinations, {len(all_rows)} rows, snapshot {SNAPSHOT}.")
    conn.close()


if __name__ == "__main__":
    main()
