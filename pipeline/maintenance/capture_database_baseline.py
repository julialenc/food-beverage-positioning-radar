"""Preserve a local baseline without modifying the working SQLite database.

Uses SQLite's backup API through a read-only connection, including committed
WAL contents. Reports the existing population policy; does not choose a future
population, migrate schemas, ingest products, or publish an artifact.

Run from the repository root:
    python -B pipeline/maintenance/capture_database_baseline.py

Output is a new, ignored directory under
data/06_brand_governance_outputs/baseline_captures/. Existing captures are never
overwritten. An incomplete capture retains FAILED.json instead of manifest.json.
Python standard library only; no production stage is imported or executed.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "data/06_brand_governance_outputs/baseline_captures"
REGIONS = ("FRANCE", "UK_IE", "US_CANADA")
CATEGORIES = ("snacks", "cereals", "dairies", "beverages")
LATEST = "ingested_at = (SELECT MAX(ingested_at) FROM products)"
BRAND = "COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand)"
DISPLAY_GATE = (
    f"COALESCE(include_in_product_table, 1) = 1 AND {BRAND} IS NOT NULL "
    f"AND TRIM(LOWER({BRAND})) NOT IN ('unknown', '', 'nan')"
)
LAUNCH_SCOPE = (
    "query_category IN ('snacks','cereals','dairies','beverages') AND "
    "(observed_market_region_codes LIKE '%FRANCE%' OR "
    "observed_market_region_codes LIKE '%UK_IE%' OR "
    "observed_market_region_codes LIKE '%US_CANADA%')"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_identity(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    return {"exists": True, "bytes": path.stat().st_size, "sha256": sha256(path)}


def read_connection(path: Path) -> sqlite3.Connection:
    # immutable=1 would incorrectly ignore an existing WAL; do not use it.
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def rows(conn: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    cursor = conn.execute(sql, params)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor]


def schema_identity(conn: sqlite3.Connection) -> dict:
    schema = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
    ).fetchall()
    counts = {
        name: conn.execute(f"SELECT COUNT(*) FROM {quote(name)}").fetchone()[0]
        for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    }
    return {
        "schema_sha256": hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
        "table_counts_including_sqlite_internal": counts,
        "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        "page_size": conn.execute("PRAGMA page_size").fetchone()[0],
    }


def backup_database(source: Path, destination: Path) -> dict:
    """Pin a read snapshot, back it up, then validate all table counts/schema."""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination:
        raise ValueError("Backup destination must differ from source")
    # Exclusive creation prevents accidental replacement, including in a race.
    with destination.open("xb"):
        pass
    with closing(read_connection(source)) as src:
        src.execute("BEGIN")
        src.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        snapshot_opened = utc_now()
        source_identity = schema_identity(src)
        deadline = time.monotonic() + 1800

        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("SQLite backup exceeded 30 minutes")

        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst, pages=4096, progress=progress, sleep=0.1)
            # Make the backup a self-contained file, even when source uses WAL.
            dst.execute("PRAGMA journal_mode=DELETE").fetchone()
        src.rollback()
    with closing(read_connection(destination)) as check:
        integrity = [row[0] for row in check.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise RuntimeError(f"Backup integrity check failed: {integrity[:10]}")
        if schema_identity(check) != source_identity:
            raise RuntimeError("Backup schema/table counts differ from pinned source")
    return {"snapshot_opened_at_utc": snapshot_opened,
            "source_snapshot": source_identity, "integrity_check": integrity,
            "schema_and_all_table_counts_match": True}


def barcode_identity(conn: sqlite3.Connection, where: str = "1=1") -> dict:
    digest = hashlib.sha256()
    count = 0
    for (barcode,) in conn.execute(
        f"SELECT barcode FROM products WHERE {where} ORDER BY barcode"
    ):
        digest.update((json.dumps(barcode, ensure_ascii=False) + "\n").encode())
        count += 1
    return {"count": count, "sorted_barcodes_sha256": digest.hexdigest()}


def describe_baseline(conn: sqlite3.Connection) -> dict:
    latest = conn.execute("SELECT MAX(ingested_at) FROM products").fetchone()[0]
    if latest is None:
        raise ValueError("No dated ingestion population; requires separate review")
    groups = rows(conn, """
        SELECT ingested_at, COUNT(*) AS product_count FROM products
        GROUP BY ingested_at ORDER BY ingested_at DESC
    """)
    launch = f"({LATEST}) AND ({LAUNCH_SCOPE})"
    visible = f"({launch}) AND ({DISPLAY_GATE})"
    scopes = []
    for region in REGIONS:
        for category in CATEGORIES:
            count = conn.execute(
                f"SELECT COUNT(*) FROM products WHERE ({LATEST}) "
                f"AND ({DISPLAY_GATE}) AND query_category=? "
                "AND observed_market_region_codes LIKE ?",
                (category, f"%{region}%"),
            ).fetchone()[0]
            scopes.append({"region": region, "category": category,
                           "display_eligible_products": count})
    return {
        "latest_ingested_at": latest,
        "ingestion_groups": groups,
        "all_products": barcode_identity(conn),
        "latest_ingestion_population": barcode_identity(conn, LATEST),
        "older_or_undated_population": barcode_identity(
            conn, f"NOT ({LATEST}) OR ingested_at IS NULL"),
        "deployment_scope_candidate": barcode_identity(conn, launch),
        "display_eligible_unique_products": barcode_identity(conn, visible),
        "display_eligibility_by_scope": scopes,
        "scope_count_note": "Multi-region products count in each applicable region.",
        "recorded_queries": {"latest": LATEST, "launch_scope": LAUNCH_SCOPE,
                             "display_gate": DISPLAY_GATE},
        "ingestion_log": rows(conn, "SELECT * FROM ingestion_log ORDER BY id"),
        "off_timestamps": rows(conn, """
            SELECT ingested_at, COUNT(created_t) AS nonnull_created_t,
                   COUNT(last_modified_t) AS nonnull_last_modified_t,
                   MIN(created_t) AS created_min_text, MAX(created_t) AS created_max_text,
                   MIN(last_modified_t) AS modified_min_text,
                   MAX(last_modified_t) AS modified_max_text
            FROM products GROUP BY ingested_at ORDER BY ingested_at DESC
        """),
        "claim_enrichment": rows(conn, """
            SELECT a.release_run_id, a.prompt_version, a.claim_source,
                   COUNT(*) AS rows,
                   MIN(a.pack_analysis_timestamp) AS first_analysis_timestamp_text,
                   MAX(a.pack_analysis_timestamp) AS last_analysis_timestamp_text,
                   SUM(CASE WHEN p.ingested_at=(SELECT MAX(ingested_at) FROM products)
                       THEN 1 ELSE 0 END) AS latest_ingestion_rows
            FROM product_analysis a LEFT JOIN products p ON p.barcode=a.barcode
            WHERE a.pack_analysis_attempted=1 OR a.claim_source='vision'
            GROUP BY a.release_run_id, a.prompt_version, a.claim_source
            ORDER BY a.release_run_id, a.prompt_version, a.claim_source
        """),
        "vision_rows_total": conn.execute(
            "SELECT COUNT(*) FROM product_analysis WHERE claim_source='vision'"
        ).fetchone()[0],
    }


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE
    ).decode("utf-8").strip()


def protected_paths() -> list[Path]:
    paths = [ROOT / "database/positioning_radar_public_mvp.db",
             ROOT / "database/positioning_radar_public_mvp.db.gz"]
    paths += list((ROOT / "presentations").rglob("*"))
    paths += list((ROOT / "data/01_reference_inputs").glob("*"))
    return sorted(p for p in paths if p.is_file())


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def capture(source: Path, output: Path, off_capture_label: str) -> Path:
    source = source.resolve(strict=True)
    output = output.resolve()
    if not output.is_relative_to(CAPTURES.resolve()):
        raise ValueError(f"Output must be under {CAPTURES}")
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", "--",
         str(output / "manifest.json")], check=False
    )
    if ignored.returncode != 0:
        raise ValueError("Capture output must be Git-ignored")
    required = source.stat().st_size * 2 + 100 * 1024 * 1024
    if shutil.disk_usage(ROOT).free < required:
        raise OSError("Insufficient free space for baseline and validation")
    output.mkdir(parents=True, exist_ok=False)
    started = utc_now()
    try:
        print("Recording source and protected-artifact hashes...", flush=True)
        source_before = file_identity(source)
        wal = Path(str(source) + "-wal")
        wal_before = file_identity(wal)
        protected = {p.relative_to(ROOT).as_posix(): file_identity(p)
                     for p in protected_paths()}
        code_state = {"commit": git("rev-parse", "HEAD"),
                      "branch": git("branch", "--show-current"),
                      "status_porcelain": git("status", "--porcelain"),
                      "capture_script_sha256": sha256(Path(__file__)),
                      "python": sys.version, "sqlite": sqlite3.sqlite_version}
        tracked_code = git("ls-files", "pipeline", "shared", "pages", "app.py",
                           "requirements.txt", "database/schema.sql").splitlines()
        code_state["existing_code_hashes"] = {
            p: sha256(ROOT / p) for p in tracked_code if (ROOT / p).is_file()}
        print("Creating consistent SQLite backup (source opened read-only)...", flush=True)
        backup = output / "baseline.db"
        validation = backup_database(source, backup)
        print("Backup integrity passed; identifying populations and provenance...", flush=True)
        with closing(read_connection(backup)) as conn:
            population = describe_baseline(conn)
        public_db = ROOT / "database/positioning_radar_public_mvp.db"
        public_population = None
        if public_db.exists():
            with closing(read_connection(public_db)) as conn:
                public_population = barcode_identity(conn)
        print("Verifying source and protected artifacts are unchanged...", flush=True)
        source_after, wal_after = file_identity(source), file_identity(wal)
        if source_before != source_after or wal_before != wal_after:
            raise RuntimeError("Source DB/WAL changed during capture; review concurrent writers")
        for p, identity in protected.items():
            if file_identity(ROOT / p) != identity:
                raise RuntimeError(f"Protected artifact changed during capture: {p}")
        for p, digest in code_state["existing_code_hashes"].items():
            if sha256(ROOT / p) != digest:
                raise RuntimeError(f"Existing code changed during capture: {p}")
        shutil.copyfile(Path(__file__), output / "capture_script.py")
        manifest = {
            "format_version": 1, "status": "complete",
            "capture_started_at_utc": started, "capture_completed_at_utc": utc_now(),
            "off_capture_label": off_capture_label,
            "off_capture_label_basis": "Repo owner statement; not inferred from ingestion time",
            "interpretation": [
                "August OFF capture with subsequent claim enrichment and reviewed corrections.",
                "Owner confirms private-label work added OCR/LLM coverage, not OFF ingestion.",
                "This is today's preserved working state, not a reconstruction of every August field.",
                "Stored ingestion time is a local load time, not necessarily the OFF download date.",
                "Current population is reported, not approved or changed for future waves.",
                "Current observations are preserved; overwritten earlier versions are not recovered.",
            ],
            "source_path": str(source), "source_file_before": source_before,
            "source_wal_before": wal_before, "source_file_after": source_after,
            "source_wal_after": wal_after,
            "source_shm_note": "SQLite coordination file; excluded from byte-identity checks.",
            "backup": {"file": "baseline.db", **file_identity(backup)},
            "validation": validation, "population": population,
            "local_compact_db_product_identity": public_population,
            "compact_membership_matches_working_deployment_candidate": (
                public_population == population["deployment_scope_candidate"]
                if public_population is not None else None),
            "compact_comparison_note": "Local uncompressed artifact membership only; not a live app test.",
            "code": code_state, "protected_files_unchanged": protected,
        }
        report = render_report(manifest)
        with (output / "REPORT.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(report)
        # The manifest is the completion marker, created only after all checks pass.
        write_json(output / "manifest.json", manifest)
        print(f"COMPLETE: {output}", flush=True)
        return output
    except Exception as exc:
        write_json(output / "FAILED.json", {
            "status": "incomplete", "started_at_utc": started,
            "failed_at_utc": utc_now(), "error": str(exc)})
        raise


def render_report(manifest: dict) -> str:
    p = manifest["population"]
    counts = manifest["validation"]["source_snapshot"]["table_counts_including_sqlite_internal"]
    lines = ["# Preserved baseline", "",
             f"Capture completed (UTC): {manifest['capture_completed_at_utc']}", "",
             f"OFF capture label: **{manifest['off_capture_label']}** (owner-confirmed).", "",
             "August product capture, subsequently enriched through OCR/LLM and reviewed corrections. "
             "Private-label work did not ingest additional OFF products. This backup preserves the "
             "current database, not historical August claim results or overwritten product versions.", "",
             "## Population inventory", "", "| Group | Products |", "|---|---:|",
             f"| All working-database products | {p['all_products']['count']:,} |",
             f"| Latest ingestion group ({p['latest_ingested_at']}) | {p['latest_ingestion_population']['count']:,} |",
             f"| Older or undated records, preserved separately in the inventory | {p['older_or_undated_population']['count']:,} |",
             f"| Latest group within deployment regions/categories | {p['deployment_scope_candidate']['count']:,} |",
             f"| Unique display-eligible products within that scope | {p['display_eligible_unique_products']['count']:,} |", "",
             "These are descriptions of current selection rules, not approval of future membership. "
             "The full backup retains all groups. No record was deleted or reactivated.", "",
             "### Stored ingestion groups", "", "| ingested_at | Products |", "|---|---:|"]
    for r in p["ingestion_groups"]:
        lines.append(f"| {r['ingested_at']} | {r['product_count']:,} |")
    lines += ["", "Local load timestamps must not be substituted for OFF capture dates. "
              "The complete ingestion log is in manifest.json and the backup.", "",
              "### Display eligibility by region/category", "",
              "| Region | Category | Products |", "|---|---|---:|"]
    for r in p["display_eligibility_by_scope"]:
        lines.append(f"| {r['region']} | {r['category']} | {r['display_eligible_products']:,} |")
    lines += ["", p["scope_count_note"], "", "## Enrichment and provenance", "",
              f"Vision-sourced analysis rows across the working database: **{p['vision_rows_total']:,}**.", "",
              "Release IDs, prompts and analysis-date ranges are preserved in the manifest. "
              "All product and analysis values, mappings, flags, summaries and ingestion-log entries "
              "are preserved in baseline.db. Reference-file and existing-code checksums are recorded.", "",
              f"Code commit: `{manifest['code']['commit']}`. The capture script is also frozen alongside the backup.", "",
              "## Validation", "",
              "- Source opened read-only; SQLite backup includes committed WAL data.",
              "- Backup integrity_check: ok.",
              f"- Schema and row counts match the pinned source across {len(counts)} tables, including SQLite internal tables.",
              "- Source DB and WAL byte identities are unchanged.",
              f"- {len(manifest['protected_files_unchanged'])} deployment, presentation and reference files are unchanged.",
              "- Existing tracked code files are unchanged.",
              f"- Local compact DB barcode membership matches the working deployment candidate: {manifest['compact_membership_matches_working_deployment_candidate']}.",
              "- This capture did not rerun Streamlit, ingest data, migrate schemas, commit or push.", "",
              "## Files", "",
              "- baseline.db: complete consistent database backup; keep local.",
              "- manifest.json: provenance, populations, counts, checksums and validation results.",
              "- capture_script.py: exact capture tool used.",
              "- REPORT.md: this readable summary.", "",
              f"Backup SHA-256: `{manifest['backup']['sha256']}`", "",
              "Next step: review population membership before implementing incremental updates. "
              "This directory is Git-ignored; it is not part of the public deployment.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "database/positioning_radar.db")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--off-capture-label", default="August 2026 OFF product capture")
    args = parser.parse_args()
    output = args.output_dir or CAPTURES / datetime.now(timezone.utc).strftime("baseline_%Y%m%dT%H%M%S_%fZ")
    capture(args.source, output, args.off_capture_label)


if __name__ == "__main__":
    main()
