"""Encode the approved population policy on a NEW local baseline copy only.

Usage:
 python -B pipeline/maintenance/prepare_population_policy_trial.py --baseline-dir PATH

Never opens the working database for writing. No ingestion, backfill filtering,
product updates, deployment export or paid analysis is performed. All outputs
stay under the existing Git-ignored governance-output directory.
"""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.maintenance.capture_database_baseline import (
    backup_database, file_identity, protected_paths, read_connection, sha256,
    write_json,
)
from pipeline.rules import population_policy as policy

TRIALS = ROOT / "data/06_brand_governance_outputs/population_policy_trials"
APPROVED_SEED = "20260903_030215"
APPROVED_RETAINED = 378835
APPROVED_ARCHIVED = 134102


def schema_rows(conn):
    return {row[1]: row for row in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")}


def original_data_guard(action, table, column, database, context):
    """Prevent DML against every original table while adding policy metadata."""
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        if table not in {"sqlite_master", "sqlite_temp_master", *policy.OBJECTS[:3]}:
            return sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_VIEW,
                  sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_ALTER_TABLE):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def run_trial(baseline_dir, output):
    baseline_dir = baseline_dir.resolve(strict=True)
    manifest_path = baseline_dir / "manifest.json"
    baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = baseline_dir / "baseline.db"
    if baseline.get("status") != "complete":
        raise ValueError("Requires a completed baseline capture")
    p = baseline["population"]
    if (p["latest_ingested_at"], p["latest_ingestion_population"]["count"],
        p["older_or_undated_population"]["count"]) != (
            APPROVED_SEED, APPROVED_RETAINED, APPROVED_ARCHIVED):
        raise ValueError("This baseline differs from the explicitly approved population")
    output = output.resolve()
    if not output.is_relative_to(TRIALS.resolve()):
        raise ValueError(f"Trial output must be under {TRIALS}")
    if subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--",
                       str(output / "trial.db")]).returncode != 0:
        raise ValueError("Output must be ignored by Git")
    if shutil.disk_usage(ROOT).free < source.stat().st_size * 2:
        raise OSError("Insufficient space for a separate trial copy")
    output.mkdir(parents=True, exist_ok=False)
    try:
        print("Verifying baseline and recording protected-file identities...", flush=True)
        if file_identity(source) != {k: baseline["backup"][k] for k in ("exists", "bytes", "sha256")}:
            raise ValueError("Frozen baseline checksum differs from its manifest")
        protection = {str(path): file_identity(path) for path in protected_paths()}
        protection.update({str(path): file_identity(path) for path in baseline_dir.iterdir() if path.is_file()})
        for name in ("positioning_radar.db", "positioning_radar.db-wal"):
            path = ROOT / "database" / name
            protection[str(path)] = file_identity(path)
        code_files = [Path(__file__), ROOT / "pipeline/rules/population_policy.py",
                      ROOT / "pipeline/validation/check_07_population_policy.py"]
        code_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in code_files}
        print("Creating and validating separate full database copy...", flush=True)
        trial = output / "trial.db"
        backup_validation = backup_database(source, trial)
        print("Encoding approved membership; original tables protected against writes...", flush=True)
        with closing(sqlite3.connect(trial)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            before_schema = schema_rows(conn)
            before_counts = backup_validation["source_snapshot"]["table_counts_including_sqlite_internal"]
            conn.set_authorizer(original_data_guard)
            result = policy.initialize(
                conn, baseline_id=baseline_dir.name, baseline_sha256=baseline["backup"]["sha256"],
                seed_ingested_at=APPROVED_SEED, expected_retained=APPROVED_RETAINED,
                expected_archived=APPROVED_ARCHIVED,
                expected_retained_digest=p["latest_ingestion_population"]["sorted_barcodes_sha256"],
                off_capture_date="2026-08-29", proxy_wave_2_cutoff="2026-09-29")
            guard_verified = False
            try:
                conn.execute("UPDATE products SET quantity=quantity WHERE 0")
            except sqlite3.DatabaseError as exc:
                if "not authorized" not in str(exc).lower():
                    raise
                guard_verified = True
            if not guard_verified:
                raise RuntimeError("Original-table write guard was not enforced")
            after_schema = schema_rows(conn)
            if any(after_schema.get(name) != value for name, value in before_schema.items()):
                raise RuntimeError("An original schema object changed")
            for name, count in before_counts.items():
                escaped = name.replace('"', '""')
                if conn.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0] != count:
                    raise RuntimeError(f"Original table count changed: {name}")
            expected_counts = {
                "all_products": p["all_products"]["count"], "retained": APPROVED_RETAINED,
                "archived": APPROVED_ARCHIVED,
                "deployment_scope": p["deployment_scope_candidate"]["count"],
                "display_eligible": p["display_eligible_unique_products"]["count"],
                "unregistered_products": 0}
            if result != expected_counts:
                raise RuntimeError(f"Starting population changed: {result}")
            identities = {}
            for view, baseline_key in (
                ("retained_products", "latest_ingestion_population"),
                ("retained_deployment_products", "deployment_scope_candidate"),
                ("retained_display_products", "display_eligible_unique_products"),
            ):
                identities[view] = policy.barcode_digest(conn, f"SELECT barcode FROM {view} ORDER BY barcode")
                if identities[view] != p[baseline_key]:
                    raise RuntimeError(f"Membership identity differs: {view}")
            if conn.execute("PRAGMA foreign_key_check(population_membership)").fetchall():
                raise RuntimeError("Membership foreign-key check failed")
        print("Verifying live files and frozen baseline are unchanged...", flush=True)
        for path, identity in protection.items():
            if file_identity(Path(path)) != identity:
                raise RuntimeError(f"Protected file changed: {path}")
        for path, digest in code_hashes.items():
            if sha256(ROOT / path) != digest:
                raise RuntimeError(f"Policy code changed during trial: {path}")
        audit = {
            "status": "complete", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_directory": str(baseline_dir), "baseline_manifest_sha256": sha256(manifest_path),
            "off_capture_date_owner_approved": "2026-08-29",
            "wave_2_proxy_cutoff_owner_approved": "2026-09-29",
            "cutoff_filter_implemented": False, "production_integration_implemented": False,
            "counts": result, "membership_identities": identities,
            "backup_validation": backup_validation,
            "original_schema_and_counts_unchanged": True,
            "original_table_write_guard_verified": guard_verified,
            "protected_file_identities_unchanged": protection,
            "code_sha256": code_hashes, "trial_database": file_identity(trial),
            "limitations": [
                "Trial adds three policy tables and three views; original product and analysis rows are unchanged.",
                "Synthetic A/B/C tests run separately in disposable databases using the existing stage-05 loader.",
                "Production loader, app filters, aggregation, history snapshots and ingestion completeness still need integration.",
                "Current stage-05 loader commits internally; the tested membership helper alone is not an atomic ingestion pipeline.",
            ],
        }
        report = ["# Population policy trial", "",
                  "Status: completed on a separate copy; production files unchanged.", "",
                  "Approved OFF capture date: 29 August 2026 (owner-confirmed).",
                  "Approved wave-2 proxy cutoff: 29 September 2026; metadata only, no filtering implemented.", "",
                  "| Population | Products |", "|---|---:|"]
        report += [f"| {key} | {value:,} |" for key, value in result.items()]
        report += ["", "## Verification", "",
                   "- Full backup integrity, schema and source-table counts verified before policy initialization.",
                   "- Original tables protected against INSERT, UPDATE and DELETE; protection verified.",
                   "- Original schema objects and table counts unchanged after initialization.",
                   "- Retained, deployment and display barcode identities exactly match the frozen baseline.",
                   "- Membership has no missing product references or unregistered products.",
                   "- Working DB, frozen baseline, deployment files, presentations and reference inputs unchanged.", "",
                   "## Files", "", "- trial.db: separate full database with policy metadata and views.",
                   "- manifest.json: counts, checksums, validation and implementation limits.", "",
                   "## Boundary of this step", "",
                   "No original products were changed in this full-size trial. A/B/C behavior is tested separately "
                   "in disposable databases. The live loader and app do not use these views yet. No new OFF "
                   "ingestion, backfill, deployment, commit or push was performed.", "",
                   "Next: integrate membership with transactional ingestion and align downstream population selection, "
                   "continuing to validate on a copy before production use.", ""]
        (output / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        write_json(output / "manifest.json", audit)
        print(f"COMPLETE: {output}", flush=True)
        return output
    except Exception as exc:
        write_json(output / "FAILED.json", {"status": "incomplete", "error": str(exc)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or TRIALS / datetime.now(timezone.utc).strftime("trial_%Y%m%dT%H%M%S_%fZ")
    run_trial(args.baseline_dir, output)
