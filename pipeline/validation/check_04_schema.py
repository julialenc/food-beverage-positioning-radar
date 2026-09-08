"""
check_04_schema.py
------------------
Compares the LIVE database's actual schema against what the current
pipeline code declares - the DDL constants in
stage_05_load_database.py, stage_13_build_app_summaries.py, and known helper-table scripts.
Reports any drift in either direction.

Why this exists: CREATE TABLE IF NOT EXISTS is a no-op if a table
already exists — it will NOT add new columns or rename old ones. If
positioning_radar.db was created under an older version of
stage_05_load_database.py or stage_13_build_app_summaries.py (e.g. before a column rename),
running the current
pipeline against it will silently NOT fix the schema. This script is
how you'd detect that before it causes confusing downstream errors —
see the "Known limitation" note in stage_05_load_database.py's module
docstring.

How it works: builds a reference schema in a fresh in-memory SQLite
database using the exact same DDL constants the pipeline scripts use
(not a hand-maintained column list, which would drift from the code
itself over time), then compares column sets against the live database
via PRAGMA table_info.

Usage:
    python pipeline/validation/check_04_schema.py

If drift is found:
    For a development database, the simplest fix is usually to delete
    database/positioning_radar.db and rerun the pipeline from
    stage_05_load_database.py onward. For a production database with data worth preserving,
    write an explicit ALTER TABLE migration instead of relying on
    CREATE TABLE IF NOT EXISTS.
"""

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.stages.stage_05_load_database import (
    DDL_PRODUCTS, DDL_PRODUCT_ANALYSIS,
    DDL_WEEKLY_BRAND_SUMMARY, DDL_INGESTION_LOG,
    DDL_MARKET_TREND_WEEKLY, DDL_CATEGORY_REGION_AVERAGES,
)
from pipeline.stages.stage_13_build_app_summaries import (
    DDL_WEEKLY_BRAND_POSITIONING_SUMMARY, DDL_POSITIONING_EXAMPLE_PRODUCTS,
)
from pipeline.stages.stage_16_build_chart_ranges import DDL as DDL_AXIS_RANGE_CONFIG
from pipeline.stages.stage_14_compute_region_benchmarks import DDL as DDL_REGION_CATEGORY_BENCHMARKS
from pipeline.stages.stage_15_compute_profile_intersections import DDL as DDL_PROFILE_INTERSECTIONS

DB_PATH = ROOT / "database" / "positioning_radar.db"

# Every table owned by pipeline DDL, keyed by table name to its current
# DDL constant. The DDL in the owning script is the source of truth for what
# "correct" looks like.
TABLE_DDL = {
    "products":                         DDL_PRODUCTS,
    "product_analysis":                 DDL_PRODUCT_ANALYSIS,
    "weekly_brand_summary":             DDL_WEEKLY_BRAND_SUMMARY,
    "ingestion_log":                    DDL_INGESTION_LOG,
    "market_trend_weekly":              DDL_MARKET_TREND_WEEKLY,
    "category_region_averages":         DDL_CATEGORY_REGION_AVERAGES,
    "weekly_brand_positioning_summary": DDL_WEEKLY_BRAND_POSITIONING_SUMMARY,
    "positioning_example_products":     DDL_POSITIONING_EXAMPLE_PRODUCTS,
    "axis_range_config":                DDL_AXIS_RANGE_CONFIG,
    "market_chart_bands":               DDL_AXIS_RANGE_CONFIG,
    "region_category_benchmarks":       DDL_REGION_CATEGORY_BENCHMARKS,
    "profile_intersections":            DDL_PROFILE_INTERSECTIONS,
}


def get_declared_columns(table_name, ddl_sql):
    """
    Build the table in a throwaway in-memory database and read back its
    actual column names — more reliable than regex-parsing column
    definitions out of the DDL text, since SQLite itself interprets
    the SQL exactly as it would for the real database.
    """
    ref_conn = sqlite3.connect(":memory:")
    ref_conn.executescript(ddl_sql)
    cols = {row[1] for row in ref_conn.execute(f"PRAGMA table_info({table_name})")}
    ref_conn.close()
    return cols


def get_live_columns(conn, table_name):
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def main():
    if not DB_PATH.exists():
        print(
            f"No database found at {DB_PATH}. "
            "Run pipeline/stages/stage_05_load_database.py first."
        )
        return

    conn = sqlite3.connect(DB_PATH)
    live_tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }

    print("\ncheck_04_schema.py - comparing live database against current DDL\n")

    any_drift = False

    for table_name, ddl in TABLE_DDL.items():
        declared_cols = get_declared_columns(table_name, ddl)

        if table_name not in live_tables:
            print(f"[{table_name}] NOT FOUND in live database - "
                  f"run the pipeline step that creates it.")
            any_drift = True
            continue

        live_cols = get_live_columns(conn, table_name)

        missing_in_db   = declared_cols - live_cols
        missing_in_code = live_cols - declared_cols

        if not missing_in_db and not missing_in_code:
            print(f"[{table_name}] in sync ({len(live_cols)} columns)")
            continue

        any_drift = True
        print(f"[{table_name}] DRIFT DETECTED")
        if missing_in_db:
            print(f"  Declared in code but missing from live DB: {sorted(missing_in_db)}")
        if missing_in_code:
            print(f"  Present in live DB but not declared in code "
                  f"(stale/legacy column): {sorted(missing_in_code)}")

    # Tables that exist in the live DB but aren't owned by any DDL checked here,
    # e.g. a leftover table from an older schema version.
    unexpected_tables = live_tables - set(TABLE_DDL.keys())
    if unexpected_tables:
        any_drift = True
        print(f"\nTables in live DB not declared by any known DDL "
              f"(possible legacy table from an older schema version): "
              f"{sorted(unexpected_tables)}")

    print()
    if any_drift:
        print("SCHEMA DRIFT FOUND. See docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md for "
              "the intended schema. For a development database, the "
              "simplest fix is usually to delete database/positioning_radar.db "
              "and rerun the pipeline from stage_05_load_database.py onward.")
    else:
        print("All tables in sync with current pipeline code.")

    conn.close()


if __name__ == "__main__":
    main()
