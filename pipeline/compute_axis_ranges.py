"""
Compute precomputed Market Overview chart-range bands.

The app uses these rows for Product Map range controls:

Lower 3% / Middle 94% / Upper 3% / All

This is chart-display governance only. It does not change raw OFF values,
Product Explorer inclusion, Product Explorer warnings, or aggregate
eligibility.

Beverages are included, but percentile bounds are computed inside the existing
beverage_view_segment groups so ready-to-drink beverages, preparations/alcohol,
and unknown beverage records do not borrow one another's tails.

Usage: python pipeline/compute_axis_ranges.py
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
AUDIT_DIR = (
    ROOT
    / "data"
    / "nutrition_outlier_review"
    / "audits"
    / "market_overview_chart_ranges"
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.beverage_segments import beverage_view_segment

SNAPSHOT = date.today().isoformat()

ENERGY_UNSTABLE_THRESHOLD = 10.0
DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}
PERCENTILE_TRIM_CATEGORIES = {"beverages", "cereals", "dairies", "snacks"}

_HARD_RANGES: dict[str, tuple[str, float, float | None]] = {
    "energy_kcal": ("energy_kcal", 0.0, 900.0),
    "protein_100g": ("protein_100g", 0.0, 100.0),
    "fat_100g": ("fat_100g", 0.0, 100.0),
    "saturated_fat_100g": ("saturated_fat_100g", 0.0, 100.0),
    "carbs_100g": ("carbs_100g", 0.0, 100.0),
    "sugars_100g": ("sugars_100g", 0.0, 100.0),
    "fiber_100g": ("fiber_100g", 0.0, 100.0),
    "salt_100g": ("salt_100g", 0.0, 100.0),
    "protein_per_kcal": ("protein_per_kcal", 0.0, 30.0),
    "satfat_per_kcal": ("satfat_per_kcal", 0.0, 11.1),
    "fiber_per_kcal": ("fiber_per_kcal", 0.0, None),
    "sugars_per_kcal": ("sugars_per_kcal", 0.0, None),
}
_PER_KCAL_KEYS = {
    "protein_per_kcal",
    "fiber_per_kcal",
    "satfat_per_kcal",
    "sugars_per_kcal",
}

METRIC_BAND_COLS = {
    "energy_kcal": "energy_chart_band",
    "protein_100g": "protein_chart_band",
    "fat_100g": "fat_chart_band",
    "saturated_fat_100g": "saturated_fat_chart_band",
    "carbs_100g": "carbs_chart_band",
    "sugars_100g": "sugars_chart_band",
    "fiber_100g": "fiber_chart_band",
    "salt_100g": "salt_chart_band",
    "protein_per_kcal": "protein_per_kcal_chart_band",
    "satfat_per_kcal": "satfat_per_kcal_chart_band",
    "fiber_per_kcal": "fiber_per_kcal_chart_band",
    "sugars_per_kcal": "sugars_per_kcal_chart_band",
}

AXIS_RANGE_COLUMNS = [
    "snapshot",
    "region_code",
    "category",
    "beverage_view_segment",
    "metric_key",
    "hard_min",
    "hard_max",
    "p03",
    "p97",
    "p99_5",
    "display_max",
    "n_valid",
    "n_flagged_invalid",
    "n_ratio_unstable",
    "n_below_p03",
    "n_above_p97",
    "n_trimmed",
    "n_outside_display_range",
    "computed_at",
]

MARKET_CHART_BAND_COLUMNS = [
    "snapshot",
    "region_code",
    "category",
    "beverage_view_segment",
    "barcode",
    *METRIC_BAND_COLS.values(),
    "computed_at",
]

DDL = """
CREATE TABLE IF NOT EXISTS axis_range_config (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot                TEXT NOT NULL,
    region_code             TEXT NOT NULL,
    category                TEXT NOT NULL,
    beverage_view_segment   TEXT NOT NULL DEFAULT 'all',
    metric_key              TEXT NOT NULL,
    hard_min                REAL,
    hard_max                REAL,
    p03                     REAL,
    p97                     REAL,
    p99_5                   REAL,
    display_max             REAL,
    n_valid                 INTEGER,
    n_flagged_invalid       INTEGER,
    n_ratio_unstable        INTEGER,
    n_below_p03             INTEGER,
    n_above_p97             INTEGER,
    n_trimmed               INTEGER,
    n_outside_display_range INTEGER,
    computed_at             TEXT
);
CREATE INDEX IF NOT EXISTS idx_axis_range_lookup
    ON axis_range_config(snapshot, region_code, category, beverage_view_segment, metric_key);

CREATE TABLE IF NOT EXISTS market_chart_bands (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot                        TEXT NOT NULL,
    region_code                     TEXT NOT NULL,
    category                        TEXT NOT NULL,
    beverage_view_segment           TEXT NOT NULL DEFAULT 'all',
    barcode                         TEXT NOT NULL,
    energy_chart_band               TEXT,
    protein_chart_band              TEXT,
    fat_chart_band                  TEXT,
    saturated_fat_chart_band        TEXT,
    carbs_chart_band                TEXT,
    sugars_chart_band               TEXT,
    fiber_chart_band                TEXT,
    salt_chart_band                 TEXT,
    protein_per_kcal_chart_band     TEXT,
    satfat_per_kcal_chart_band      TEXT,
    fiber_per_kcal_chart_band       TEXT,
    sugars_per_kcal_chart_band      TEXT,
    computed_at                     TEXT
);
CREATE INDEX IF NOT EXISTS idx_market_chart_bands_lookup
    ON market_chart_bands(snapshot, region_code, category, beverage_view_segment, barcode);
"""

AXIS_RANGE_EXTRA_COLUMNS = {
    "beverage_view_segment": "TEXT NOT NULL DEFAULT 'all'",
    "p03": "REAL",
    "p97": "REAL",
    "n_below_p03": "INTEGER",
    "n_above_p97": "INTEGER",
    "n_trimmed": "INTEGER",
}

MARKET_CHART_BAND_EXTRA_COLUMNS = {
    "beverage_view_segment": "TEXT NOT NULL DEFAULT 'all'",
}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _region_codes(value: Any) -> set[str]:
    return {code for code in str(value or "").split("|") if code}


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = pos - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def _metric_band(
    value: float | None,
    p03: float | None,
    p97: float | None,
) -> str | None:
    if value is None or p03 is None or p97 is None:
        return None
    if value < p03:
        return "L"
    if value > p97:
        return "U"
    return "M"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_columns(
    conn: sqlite3.Connection,
    table: str,
    extra_columns: dict[str, str],
) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, col_type in extra_columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")


def load_region_category_data(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT energy_kcal, protein_100g, fat_100g, saturated_fat_100g,
               carbs_100g, sugars_100g, fiber_100g, salt_100g,
               query_category AS category, observed_market_region_codes,
               barcode, product_name, off_categories
        FROM products
        WHERE primary_brand IS NOT NULL
          AND ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(include_in_product_table, 1) = 1
          AND query_category IN ('beverages', 'cereals', 'dairies', 'snacks')
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
        """
    ).fetchall()

    data: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        for col in [
            "energy_kcal",
            "protein_100g",
            "fat_100g",
            "saturated_fat_100g",
            "carbs_100g",
            "sugars_100g",
            "fiber_100g",
            "salt_100g",
        ]:
            record[col] = _to_float(record[col])

        energy = record["energy_kcal"]
        valid_energy = energy is not None and energy > 0
        if valid_energy:
            record["protein_per_kcal"] = (
                None if record["protein_100g"] is None else record["protein_100g"] / energy * 100
            )
            record["fiber_per_kcal"] = (
                None if record["fiber_100g"] is None else record["fiber_100g"] / energy * 100
            )
            record["satfat_per_kcal"] = (
                None
                if record["saturated_fat_100g"] is None
                else record["saturated_fat_100g"] / energy * 100
            )
            record["sugars_per_kcal"] = (
                None if record["sugars_100g"] is None else record["sugars_100g"] / energy * 100
            )
        else:
            record["protein_per_kcal"] = None
            record["fiber_per_kcal"] = None
            record["satfat_per_kcal"] = None
            record["sugars_per_kcal"] = None

        category = str(record.get("category") or "").lower()
        record["category"] = category
        record["_region_codes"] = _region_codes(record.get("observed_market_region_codes"))
        record["_energy_unstable"] = bool(valid_energy and energy < ENERGY_UNSTABLE_THRESHOLD)
        record["beverage_view_segment"] = (
            beverage_view_segment(
                category,
                record.get("product_name") or "",
                record.get("off_categories") or "",
            )
            if category == "beverages"
            else "all"
        )
        data.append(record)
    return data


def _scope(
    data: list[dict[str, Any]],
    region_code: str,
    category: str,
    segment: str | None = None,
) -> list[dict[str, Any]]:
    records = [
        row
        for row in data
        if row["category"] == category and region_code in row["_region_codes"]
    ]
    if category == "beverages" and segment is not None:
        records = [row for row in records if row["beverage_view_segment"] == segment]
    return records


def compute_ranges_for_scope(
    data: list[dict[str, Any]],
    region_code: str,
    category: str,
    segment: str,
) -> list[dict[str, Any]]:
    records = _scope(data, region_code, category, segment)
    rows: list[dict[str, Any]] = []
    computed_at = _now()
    for metric_key, (col, hard_min, hard_max) in _HARD_RANGES.items():
        non_null = [row[col] for row in records if row[col] is not None]
        valid = [
            value
            for value in non_null
            if value >= hard_min and (hard_max is None or value <= hard_max)
        ]
        n_flagged_invalid = len(non_null) - len(valid)

        if metric_key in _PER_KCAL_KEYS:
            n_ratio_unstable = sum(
                1
                for row in records
                if row[col] is not None
                and row[col] >= hard_min
                and (hard_max is None or row[col] <= hard_max)
                and row["_energy_unstable"]
            )
        else:
            n_ratio_unstable = 0

        p03 = _quantile(valid, 0.03)
        p97 = _quantile(valid, 0.97)
        p99_5 = _quantile(valid, 0.995)
        if p99_5 is None:
            display_max = hard_max
            n_below_p03 = 0
            n_above_p97 = 0
            n_outside = 0
        else:
            padded = p99_5 * 1.05
            display_max = min(hard_max, padded) if hard_max is not None else padded
            n_below_p03 = sum(
                1
                for value in valid
                if p03 is not None and value < p03
            )
            n_above_p97 = sum(1 for value in valid if p97 is not None and value > p97)
            n_outside = sum(1 for value in valid if value > display_max)

        rows.append(
            {
                "snapshot": SNAPSHOT,
                "region_code": region_code,
                "category": category,
                "beverage_view_segment": segment,
                "metric_key": metric_key,
                "hard_min": hard_min,
                "hard_max": hard_max,
                "p03": p03,
                "p97": p97,
                "p99_5": p99_5,
                "display_max": display_max,
                "n_valid": len(valid),
                "n_flagged_invalid": n_flagged_invalid,
                "n_ratio_unstable": n_ratio_unstable,
                "n_below_p03": n_below_p03,
                "n_above_p97": n_above_p97,
                "n_trimmed": n_below_p03 + n_above_p97,
                "n_outside_display_range": n_outside,
                "computed_at": computed_at,
            }
        )
    return rows


def build_chart_bands(
    data: list[dict[str, Any]],
    bounds_rows: list[dict[str, Any]],
    region_codes: list[str],
    categories: list[str],
) -> list[dict[str, Any]]:
    bounds = {
        (
            row["region_code"],
            row["category"],
            row["beverage_view_segment"],
            row["metric_key"],
        ): row
        for row in bounds_rows
    }
    band_rows: list[dict[str, Any]] = []
    computed_at = _now()

    for region_code in region_codes:
        for category in categories:
            base_scope = _scope(data, region_code, category)
            segments = (
                sorted({row["beverage_view_segment"] for row in base_scope})
                if category == "beverages"
                else ["all"]
            )
            for segment in segments:
                records = _scope(data, region_code, category, segment)
                for record in records:
                    out = {
                        "snapshot": SNAPSHOT,
                        "region_code": region_code,
                        "category": category,
                        "beverage_view_segment": segment,
                        "barcode": str(record["barcode"]),
                        "computed_at": computed_at,
                    }
                    for metric_key, band_col in METRIC_BAND_COLS.items():
                        bound = bounds.get((region_code, category, segment, metric_key))
                        out[band_col] = _metric_band(
                            record[metric_key],
                            None if bound is None else bound["p03"],
                            None if bound is None else bound["p97"],
                        )
                    band_rows.append(out)
    return band_rows


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_audits(bounds_rows: list[dict[str, Any]], band_rows: list[dict[str, Any]]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        AUDIT_DIR / "market_overview_chart_percentile_bounds.csv",
        [
            {
                "region": row["region_code"],
                "category": row["category"],
                "beverage_view_segment": row["beverage_view_segment"],
                "metric": row["metric_key"],
                "non_null_n": row["n_valid"],
                "p03": row["p03"],
                "p97": row["p97"],
            }
            for row in bounds_rows
        ],
        [
            "region",
            "category",
            "beverage_view_segment",
            "metric",
            "non_null_n",
            "p03",
            "p97",
        ],
    )
    _write_csv(
        AUDIT_DIR / "market_overview_percentile_bounds.csv",
        [
            {
                "region": row["region_code"],
                "category": row["category"],
                "beverage_view_segment": row["beverage_view_segment"],
                "metric": row["metric_key"],
                "n_valid": row["n_valid"],
                "p03": row["p03"],
                "p97": row["p97"],
                "computed_at": row["computed_at"],
            }
            for row in bounds_rows
        ],
        [
            "region",
            "category",
            "beverage_view_segment",
            "metric",
            "n_valid",
            "p03",
            "p97",
            "computed_at",
        ],
    )

    summary_rows: list[dict[str, Any]] = []
    for bound in bounds_rows:
        band_col = METRIC_BAND_COLS[bound["metric_key"]]
        matching = [
            row
            for row in band_rows
            if row["region_code"] == bound["region_code"]
            and row["category"] == bound["category"]
            and row["beverage_view_segment"] == bound["beverage_view_segment"]
        ]
        lower = sum(1 for row in matching if row[band_col] == "L")
        middle = sum(1 for row in matching if row[band_col] == "M")
        upper = sum(1 for row in matching if row[band_col] == "U")
        null_count = sum(1 for row in matching if row[band_col] is None)
        non_null_n = lower + middle + upper
        total_trimmed = lower + upper
        summary_rows.append(
            {
                "region": bound["region_code"],
                "category": bound["category"],
                "beverage_view_segment": bound["beverage_view_segment"],
                "metric": bound["metric_key"],
                "non_null_n": non_null_n,
                "eligible_non_null_products": non_null_n,
                "below_p03": lower,
                "above_p97": upper,
                "total_trimmed": total_trimmed,
                "trimmed_pct": (
                    round(total_trimmed / non_null_n * 100, 2) if non_null_n else None
                ),
                "lower_count": lower,
                "lower_pct": round(lower / non_null_n * 100, 2) if non_null_n else None,
                "middle_count": middle,
                "middle_pct": round(middle / non_null_n * 100, 2) if non_null_n else None,
                "upper_count": upper,
                "upper_pct": round(upper / non_null_n * 100, 2) if non_null_n else None,
                "null_count": null_count,
            }
        )
    _write_csv(
        AUDIT_DIR / "market_overview_trim_summary.csv",
        summary_rows,
        [
            "region",
            "category",
            "beverage_view_segment",
            "metric",
            "eligible_non_null_products",
            "below_p03",
            "above_p97",
            "total_trimmed",
            "trimmed_pct",
        ],
    )
    _write_csv(
        AUDIT_DIR / "market_overview_chart_band_summary.csv",
        summary_rows,
        [
            "region",
            "category",
            "beverage_view_segment",
            "metric",
            "non_null_n",
            "lower_count",
            "lower_pct",
            "middle_count",
            "middle_pct",
            "upper_count",
            "upper_pct",
            "null_count",
        ],
    )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)
    _ensure_columns(conn, "axis_range_config", AXIS_RANGE_EXTRA_COLUMNS)
    _ensure_columns(conn, "market_chart_bands", MARKET_CHART_BAND_EXTRA_COLUMNS)

    data = load_region_category_data(conn)
    all_codes_present = {code for row in data for code in row["_region_codes"] if code}
    region_codes = sorted(all_codes_present & DOWNLOAD_SCOPE_REGIONS)
    out_of_scope = all_codes_present - DOWNLOAD_SCOPE_REGIONS
    if out_of_scope:
        print(
            f"Note: ignoring {len(out_of_scope)} out-of-scope region code(s): "
            f"{sorted(out_of_scope)}"
        )
    categories = sorted(
        {row["category"] for row in data if row["category"] in PERCENTILE_TRIM_CATEGORIES}
    )

    bounds_rows: list[dict[str, Any]] = []
    for region_code in region_codes:
        for category in categories:
            base_scope = _scope(data, region_code, category)
            segments = (
                sorted({row["beverage_view_segment"] for row in base_scope})
                if category == "beverages"
                else ["all"]
            )
            for segment in segments:
                bounds_rows.extend(
                    compute_ranges_for_scope(data, region_code, category, segment)
                )
    if not bounds_rows:
        raise RuntimeError("No axis range rows computed.")

    band_rows = build_chart_bands(data, bounds_rows, region_codes, categories)

    conn.execute("DELETE FROM axis_range_config WHERE snapshot = ?", (SNAPSHOT,))
    conn.executemany(
        f"""
        INSERT INTO axis_range_config
        ({', '.join(AXIS_RANGE_COLUMNS)})
        VALUES ({', '.join('?' for _ in AXIS_RANGE_COLUMNS)})
        """,
        [tuple(row[col] for col in AXIS_RANGE_COLUMNS) for row in bounds_rows],
    )
    conn.execute("DELETE FROM market_chart_bands WHERE snapshot = ?", (SNAPSHOT,))
    if band_rows:
        conn.executemany(
            f"""
            INSERT INTO market_chart_bands
            ({', '.join(MARKET_CHART_BAND_COLUMNS)})
            VALUES ({', '.join('?' for _ in MARKET_CHART_BAND_COLUMNS)})
            """,
            [tuple(row[col] for col in MARKET_CHART_BAND_COLUMNS) for row in band_rows],
        )
    conn.commit()

    scope_count = len(
        {
            (row["region_code"], row["category"], row["beverage_view_segment"])
            for row in bounds_rows
        }
    )
    print(
        f"Computed axis ranges for {scope_count} region-category-segment scopes "
        f"x {len(_HARD_RANGES)} metrics = {len(bounds_rows)} rows, "
        f"snapshot {SNAPSHOT}."
    )
    total_flagged = sum(row["n_flagged_invalid"] for row in bounds_rows)
    print(f"Total hard-implausible values flagged across all combinations: {total_flagged}")
    print(f"Computed chart band rows: {len(band_rows):,}")
    write_audits(bounds_rows, band_rows)
    conn.close()


if __name__ == "__main__":
    main()
