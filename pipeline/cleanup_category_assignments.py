"""
cleanup_category_assignments.py
--------------------------------
Audit and optionally apply category cleanup actions already stored in
database/positioning_radar.db.

Why this exists
  pipeline/category_rules.py now protects future bulk and incremental
  ingestion from obvious category contamination. Existing SQLite rows,
  however, can still carry old query_category values because a re-filtered
  ingest only upserts products present in the new input. Products excluded
  by the new rules may never be revisited, so their stale query_category
  remains visible in Streamlit.

Scope
  This script is deliberately conservative and DB-local. The current DB does
  not preserve canonical OFF categories_tags, so this is not a perfect replay
  of category_rules.assign_category(). It audits current query_category plus
  product_name/off_categories and writes separate action-bucket CSVs.

Actions
  reassign_to_snacks    cereal/snack/protein/energy/fruit/nut bars currently
                        trapped in cereals
  exclude_from_cereals  pasta, noodles, bread, flour, rice, grain staples,
                        dough, bakery staples, meal components
  exclude_from_snacks   snack rows explicitly reviewed as not snack
  keep_in_cereals       reviewed cereal rows that should remain cereals
  keep_in_snacks        reviewed snack rows that should remain snacks
  manual_review         unresolved cereal/snack rows; never changed by --apply

What is changed with --apply
  - reassign_to_snacks rows get products.query_category = 'snacks'
  - exclude_from_cereals / exclude_from_snacks rows get query_category = NULL
  - keep_in_cereals / keep_in_snacks / manual_review rows are not changed

What is never touched
  product_analysis, OCR/LLM fields, release samples, nutrition values, images,
  brand mapping, and all analysis history.

Usage
  Dry run:
    python pipeline/cleanup_category_assignments.py

  Dry run using Julia-reviewed snack files:
    python pipeline/cleanup_category_assignments.py ^
      --snack-high-confidence-review C:\\path\\set_2_snack_classified.xlsx ^
      --snack-manual-review C:\\path\\snacks_misfit_review_classified.csv

  Dry run using a completed France snack scope review:
    python pipeline/cleanup_category_assignments.py ^
      --france-snack-review C:\\path\\20.08.2026_france_snacks_or_not_snacks.csv ^
      --france-snack-review-source data\\sample\\france_snacks_scope_review_YYYYMMDD_HHMMSS.csv

  Dry run using a completed France cereal scope review:
    python pipeline/cleanup_category_assignments.py ^
      --france-cereal-review C:\\path\\france_cereals_review_classified.csv ^
      --france-cereal-review-source data\\sample\\france_cereals_review_YYYYMMDD_HHMMSS.csv

  Apply after reviewing the audit CSVs:
    python pipeline/cleanup_category_assignments.py --apply [same review args]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
AUDIT_DIR = ROOT / "data" / "sample"


CEREAL_BAR_TO_SNACK_RE = re.compile(
    r"\b("
    r"bars|barre|barres|cereal\s+bars?|granola\s+bars?|"
    r"muesli\s+bars?|museli\s+bars?|protein\s+bars?|energy\s+bars?|"
    r"snack\s+bars?|fruit\s+bars?|nut\s+bars?|oat\s+bars?|"
    r"oaty\s+bars?|rice\s+bars?|seed\s+bars?|chewy\s+bars?|"
    r"breakfast\s+bars?|flapjacks?|treat\s+bars?"
    r")\b",
    re.IGNORECASE,
)

BREAKFAST_CEREAL_NAME_RE = re.compile(
    r"\b("
    r"muesli|granola|corn\s*flakes?|cornflakes?|flocons?|flakes?|"
    r"porridge|oats?|avoine|oatmeal|choco\s*balls?|cereal\s+clusters?|"
    r"cereales?|petales?|weetabix|shreddies|rice\s+krispies|cocoa\s+rice"
    r")\b",
    re.IGNORECASE,
)

PASTA_NOODLE_RE = re.compile(
    r"\b("
    r"pasta|pastas|pates\s+alimentaires|spaghetti|penne|rigatoni|fusilli|"
    r"tagliatelle|linguine|macaroni|farfalle|orecchiette|gnocchi|"
    r"tortellini|ravioli|lasagn\w*|noodle|noodles|ramen|udon|soba|"
    r"pad\s*thai"
    r")\b",
    re.IGNORECASE,
)

CEREALS_BREAD_FLOUR_RE = re.compile(
    r"\b("
    r"bread|breads|flatbread|flat\s*bread|wrap|wraps|tortilla|"
    r"tortillas|rusk|rusks|breadstick|breadsticks|grissini|flour|"
    r"flours|farine|semolina|semoule|puff\s*pastry|pie\s*dough|"
    r"dough|pate\s*feuilletee|brick\s*sheets|bagel|bagels|bun|buns|"
    r"brioche|croissant|pizza\s+base|pizza\s+bases|pizza\s+dough"
    r")\b",
    re.IGNORECASE,
)

CEREALS_RICE_GRAIN_STAPLE_RE = re.compile(
    r"\b("
    r"rice|rices|precooked\s+rice|cereal\s+grains?|grains?|quinoa|"
    r"bulgur|couscous|wheat\s+berries|groats|pearl\s+barley|"
    r"potato\s+starch|corn\s+starch|cooking\s+mix|baking\s+mix"
    r")\b",
    re.IGNORECASE,
)

SNACK_PROTECT_RE = re.compile(
    r"\b("
    r"tortilla\s*chips?|corn\s*chips?|crisps?|chips?\s*and\s*crackers?|"
    r"potato\s*chips?|nachos?|snack\s+pot|snacking|apero|aperitif|"
    r"aperomix|party\s+snacks?|candy|gummy|jelly\s+sweets?|crackers?"
    r")\b",
    re.IGNORECASE,
)

SNACK_REVIEW_CANDIDATE_RE = re.compile(
    r"\b("
    r"pasta|pastas|pates\s+alimentaires|spaghetti|penne|rigatoni|"
    r"fusilli|tagliatelle|linguine|macaroni|farfalle|orecchiette|"
    r"lasagn\w*|noodle|noodles|instant\s*noodle|ramen|udon|soba|"
    r"pad\s*thai|gyoza|dumplings?|ravioli|tortellini|gnocchi|"
    r"banh\s*bao|shumai|dim\s*sum"
    r")\b",
    re.IGNORECASE,
)


FIELDNAMES = [
    "review_status",
    "cleanup_action",
    "barcode",
    "product_name",
    "brands",
    "primary_brand",
    "current_query_category",
    "proposed_query_category",
    "reason",
    "off_categories",
    "review_note",
]


def _normalise_text(*parts: object) -> str:
    raw = " | ".join(str(p or "") for p in parts)
    without_accents = unicodedata.normalize("NFKD", raw).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return without_accents.lower()


def _safe_console(value: object) -> str:
    text = str(value or "")
    return text.encode("ascii", "replace").decode("ascii")


def _decision_value(value: object) -> str:
    return _normalise_text(value).strip().replace(" ", "_")


def _read_snack_decisions(
    high_confidence_path: str | None,
    manual_path: str | None,
    france_review_path: str | None,
    france_review_source_path: str | None,
) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}

    if high_confidence_path:
        df = pd.read_excel(high_confidence_path, dtype={"barcode": str})
        for _, row in df.iterrows():
            barcode = str(row.get("barcode") or "").strip()
            decision = _decision_value(row.get("snack_classification"))
            if not barcode or decision not in {"snack", "not_snack", "???"}:
                continue
            decisions[barcode] = {
                "decision": decision,
                "note": str(row.get("classification_reason") or ""),
                "source": Path(high_confidence_path).name,
            }

    if manual_path:
        df = pd.read_csv(manual_path, dtype={"barcode": str})
        for _, row in df.iterrows():
            barcode = str(row.get("barcode") or "").strip()
            decision = _decision_value(row.get("snack_review_status"))
            suggested_action = _decision_value(row.get("suggested_action"))
            if suggested_action == "keep_in_snacks":
                decision = "snack"
            elif suggested_action == "exclude_from_snacks":
                decision = "not_snack"
            elif suggested_action == "manual_review":
                decision = "???"
            if not barcode or decision not in {"snack", "not_snack", "???"}:
                continue
            decisions[barcode] = {
                "decision": decision,
                "note": str(row.get("snack_review_note") or ""),
                "source": Path(manual_path).name,
            }

    if france_review_path:
        if not france_review_source_path:
            raise ValueError(
                "--france-snack-review requires --france-snack-review-source "
                "so reviewed rows can be aligned to trustworthy barcodes."
            )
        source_df = pd.read_csv(france_review_source_path, dtype={"barcode": str})
        review_df = pd.read_csv(france_review_path, dtype={"barcode": str})
        if len(source_df) != len(review_df):
            raise ValueError(
                "France snack review and source CSV row counts do not match: "
                f"{len(review_df):,} vs {len(source_df):,}"
            )
        for idx, row in review_df.iterrows():
            barcode = str(source_df.iloc[idx].get("barcode") or "").strip()
            decision = _decision_value(row.get("reviewer_decision"))
            if decision == "not_snack":
                normalized_decision = "not_snack"
            elif decision == "snack":
                normalized_decision = "snack"
            elif decision == "???":
                normalized_decision = "not_snack"
            else:
                continue
            decisions[barcode] = {
                "decision": normalized_decision,
                "note": str(
                    row.get("reviewer_decision_reason")
                    or row.get("review_note")
                    or ""
                ),
                "source": Path(france_review_path).name,
            }

    return decisions


def _read_cereal_decisions(
    france_review_path: str | None,
    france_review_source_path: str | None,
) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}
    if not france_review_path:
        return decisions

    if not france_review_source_path:
        raise ValueError(
            "--france-cereal-review requires --france-cereal-review-source "
            "so reviewed rows can be aligned to trustworthy barcodes."
        )

    source_df = pd.read_csv(france_review_source_path, dtype={"barcode": str})
    review_df = pd.read_csv(france_review_path, dtype={"barcode": str})
    if len(source_df) != len(review_df):
        raise ValueError(
            "France cereal review and source CSV row counts do not match: "
            f"{len(review_df):,} vs {len(source_df):,}"
        )

    for idx, row in review_df.iterrows():
        barcode = str(source_df.iloc[idx].get("barcode") or "").strip()
        decision = _decision_value(row.get("reviewer_decision"))
        proposed_status = _decision_value(row.get("proposed_status"))
        if decision in {"cereal", "keep_cereal", "???"}:
            normalized_decision = "keep_cereal"
        elif decision in {"not_cereal", "route_to_snacks", "manual_review"}:
            normalized_decision = decision
        elif proposed_status == "route_to_snacks":
            normalized_decision = "route_to_snacks"
        else:
            continue
        if not barcode:
            continue
        decisions[barcode] = {
            "decision": normalized_decision,
            "note": str(row.get("review_note") or ""),
            "source": Path(france_review_path).name,
        }

    return decisions


def _audit_row(row: sqlite3.Row, review_status: str, cleanup_action: str,
               proposed_query_category: str, reason: str,
               review_note: str = "") -> dict[str, object]:
    return {
        "review_status": review_status,
        "cleanup_action": cleanup_action,
        "barcode": row["barcode"],
        "product_name": row["product_name"],
        "brands": row["brands"],
        "primary_brand": row["primary_brand"],
        "current_query_category": row["query_category"],
        "proposed_query_category": proposed_query_category,
        "reason": reason,
        "off_categories": row["off_categories"],
        "review_note": review_note,
    }


def classify_row(row: sqlite3.Row,
                 snack_decisions: dict[str, dict[str, str]],
                 cereal_decisions: dict[str, dict[str, str]]) -> dict[str, object] | None:
    category = str(row["query_category"] or "").strip().lower()
    barcode = str(row["barcode"] or "").strip()
    name_text = _normalise_text(row["product_name"])
    category_text = _normalise_text(row["off_categories"])
    text = f"{name_text} | {category_text}"

    if category == "snacks" and barcode in snack_decisions:
        decision = snack_decisions[barcode]
        if decision["decision"] == "snack":
            return _audit_row(
                row, "reviewed_keep", "keep_in_snacks", "snacks",
                "reviewed_as_snack", decision["note"]
            )
        return _audit_row(
            row, "reviewed_cleanup", "exclude_from_snacks", "",
            "reviewed_as_not_snack_or_unclassifiable", decision["note"]
        )

    if category == "cereals":
        if barcode in cereal_decisions:
            decision = cereal_decisions[barcode]
            if decision["decision"] == "keep_cereal":
                return _audit_row(
                    row, "reviewed_keep", "keep_in_cereals", "cereals",
                    "reviewed_as_breakfast_cereal", decision["note"]
                )
            if decision["decision"] == "route_to_snacks":
                return _audit_row(
                    row, "reviewed_cleanup", "reassign_to_snacks", "snacks",
                    "reviewed_as_snack_format", decision["note"]
                )
            if decision["decision"] == "not_cereal":
                return _audit_row(
                    row, "reviewed_cleanup", "exclude_from_cereals", "",
                    "reviewed_as_not_breakfast_cereal", decision["note"]
                )
            return _audit_row(
                row, "manual_review", "manual_review", "",
                "reviewed_cereal_manual_review", decision["note"]
            )

        if "code-barres" not in text and CEREAL_BAR_TO_SNACK_RE.search(name_text):
            return _audit_row(
                row, "high_confidence_cleanup", "reassign_to_snacks", "snacks",
                "cereal_bar_or_snack_bar"
            )
        if PASTA_NOODLE_RE.search(text):
            return _audit_row(
                row, "high_confidence_cleanup", "exclude_from_cereals", "",
                "cereals_pasta_noodles"
            )
        if CEREALS_BREAD_FLOUR_RE.search(text):
            return _audit_row(
                row, "high_confidence_cleanup", "exclude_from_cereals", "",
                "cereals_bread_flour_dough_bakery"
            )
        if CEREALS_RICE_GRAIN_STAPLE_RE.search(text) and not BREAKFAST_CEREAL_NAME_RE.search(name_text):
            return _audit_row(
                row, "high_confidence_cleanup", "exclude_from_cereals", "",
                "cereals_rice_grain_staple"
            )

    if category == "snacks":
        if SNACK_PROTECT_RE.search(text):
            return None
        if SNACK_REVIEW_CANDIDATE_RE.search(text):
            return _audit_row(
                row, "manual_review", "manual_review", "",
                "snacks_meal_language_ambiguous"
            )

    return None


def fetch_audit_rows(conn: sqlite3.Connection,
                     snack_decisions: dict[str, dict[str, str]],
                     cereal_decisions: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT barcode, product_name, brands, primary_brand, query_category,
               off_categories
        FROM products
        WHERE query_category IN ('cereals', 'snacks')
        ORDER BY query_category, primary_brand, product_name, barcode
        """
    ).fetchall()

    flagged: list[dict[str, object]] = []
    for row in rows:
        audit_row = classify_row(row, snack_decisions, cereal_decisions)
        if audit_row:
            flagged.append(audit_row)
    return flagged


def write_audit_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=FIELDNAMES).to_csv(
        output_path, index=False, encoding="utf-8-sig"
    )


def write_action_files(rows: list[dict[str, object]],
                       output_prefix: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for action in [
        "reassign_to_snacks",
        "exclude_from_cereals",
        "exclude_from_snacks",
        "keep_in_cereals",
        "keep_in_snacks",
        "manual_review",
    ]:
        action_rows = [r for r in rows if r["cleanup_action"] == action]
        path = output_prefix.with_name(f"{output_prefix.name}_{action}.csv")
        write_audit_csv(action_rows, path)
        paths[action] = path
    return paths


def apply_cleanup(conn: sqlite3.Connection, rows: list[dict[str, object]]) -> int:
    reassign = [
        (str(r["barcode"]),)
        for r in rows
        if r.get("barcode") and r.get("cleanup_action") == "reassign_to_snacks"
    ]
    exclude = [
        (str(r["barcode"]),)
        for r in rows
        if r.get("barcode")
        and r.get("cleanup_action") in {"exclude_from_cereals", "exclude_from_snacks"}
    ]

    conn.executemany(
        """
        UPDATE products
        SET query_category = 'snacks'
        WHERE barcode = ?
          AND query_category = 'cereals'
        """,
        reassign,
    )
    conn.executemany(
        """
        UPDATE products
        SET query_category = NULL
        WHERE barcode = ?
          AND query_category IN ('cereals', 'snacks')
        """,
        exclude,
    )
    conn.commit()
    return conn.total_changes


def print_summary(rows: list[dict[str, object]], paths: dict[str, Path]) -> None:
    print("\nFood & Beverage Positioning Radar - cleanup_category_assignments.py")
    print("\nFlagged category assignment actions:")
    if not rows:
        print("  none")
        return

    by_action = Counter(str(r["cleanup_action"]) for r in rows)
    by_reason = Counter((str(r["cleanup_action"]), str(r["reason"])) for r in rows)

    print("\n  By cleanup action:")
    for action, n in sorted(by_action.items()):
        print(f"    {action:<24} {n:>7,}")

    print("\n  By cleanup action and reason:")
    for (action, reason), n in sorted(by_reason.items()):
        print(f"    {action:<24} {reason:<44} {n:>7,}")

    print("\n  Sample rows that would change:")
    change_rows = [
        r for r in rows
        if r["cleanup_action"] in {
            "reassign_to_snacks", "exclude_from_cereals", "exclude_from_snacks"
        }
    ]
    for row in change_rows[:14]:
        action = str(row["cleanup_action"])
        category = str(row["current_query_category"])
        brand = _safe_console(row["primary_brand"])[:20]
        name = _safe_console(row["product_name"])[:58]
        print(f"    {action:<22} {category:<8} {brand:<20} {name}")

    print("\n  Output CSVs:")
    for action, path in paths.items():
        print(f"    {action:<24} {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit/apply conservative cleanup of stale category assignments."
    )
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite database path")
    parser.add_argument(
        "--output",
        default=None,
        help="Output prefix. Defaults to data/sample/category_cleanup_<timestamp>",
    )
    parser.add_argument(
        "--snack-high-confidence-review",
        default=None,
        help="Reviewed XLSX for the prior high-confidence snack candidates.",
    )
    parser.add_argument(
        "--snack-manual-review",
        default=None,
        help="Reviewed CSV for the prior manual-review snack candidates.",
    )
    parser.add_argument(
        "--france-snack-review",
        default=None,
        help="Completed France snack review CSV with reviewer_decision values.",
    )
    parser.add_argument(
        "--france-snack-review-source",
        default=None,
        help="Original generated France snack review CSV used as barcode source.",
    )
    parser.add_argument(
        "--france-cereal-review",
        default=None,
        help="Completed France cereal review CSV with reviewer_decision values.",
    )
    parser.add_argument(
        "--france-cereal-review-source",
        default=None,
        help="Original generated France cereal review CSV used as barcode source.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply reassign/exclude actions. Manual-review and keep rows are unchanged.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    snack_decisions = _read_snack_decisions(
        args.snack_high_confidence_review,
        args.snack_manual_review,
        args.france_snack_review,
        args.france_snack_review_source,
    )
    cereal_decisions = _read_cereal_decisions(
        args.france_cereal_review,
        args.france_cereal_review_source,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_prefix = (
        Path(args.output)
        if args.output
        else AUDIT_DIR / f"category_cleanup_{timestamp}"
    )

    mode = "" if args.apply else "?mode=ro"
    conn = sqlite3.connect(f"file:{db_path}{mode}", uri=True)
    try:
        rows = fetch_audit_rows(conn, snack_decisions, cereal_decisions)
        paths = write_action_files(rows, output_prefix)
        print_summary(rows, paths)

        change_count = sum(
            1 for r in rows
            if r["cleanup_action"] in {
                "reassign_to_snacks", "exclude_from_cereals", "exclude_from_snacks"
            }
        )
        keep_count = sum(
            1 for r in rows
            if r["cleanup_action"] in {"keep_in_cereals", "keep_in_snacks"}
        )
        manual_count = sum(1 for r in rows if r["cleanup_action"] == "manual_review")

        if not args.apply:
            print(
                f"\nDRY RUN: would change {change_count:,} rows. "
                f"{keep_count:,} reviewed keep rows would be left unchanged. "
                f"{manual_count:,} rows require manual review and would not be changed."
            )
            return

        changed = apply_cleanup(conn, rows)
        print(f"\nLIVE RUN: changed {changed:,} rows.")
        print("product_analysis and analysis history were not touched.\n")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
