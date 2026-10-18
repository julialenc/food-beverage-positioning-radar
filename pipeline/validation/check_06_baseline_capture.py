"""Focused, temporary-database checks for the baseline capture tool.

Run: python -B pipeline/validation/check_06_baseline_capture.py
No live project database is opened or modified.
"""

from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.maintenance.capture_database_baseline import (  # noqa: E402
    backup_database, describe_baseline, file_identity, read_connection,
)


class BaselineCaptureTests(unittest.TestCase):
    def test_committed_wal_and_source_preservation(self):
        test_root = ROOT / "data/06_brand_governance_outputs/baseline_captures/_tests"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(test_root.resolve()))
            source = Path(directory) / "source.db"
            backup = Path(directory) / "backup.db"
            with closing(sqlite3.connect(source)) as writer:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("PRAGMA wal_autocheckpoint=0")
                writer.execute("CREATE TABLE products (barcode TEXT PRIMARY KEY, value REAL)")
                writer.commit()
                writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                writer.executemany("INSERT INTO products VALUES (?, ?)",
                                   [("0001", None), ("0002", 0), ("0003", 450)])
                writer.commit()
                wal = Path(str(source) + "-wal")
                self.assertGreater(wal.stat().st_size, 0)
                before = (file_identity(source), file_identity(wal))
                result = backup_database(source, backup)
                self.assertTrue(result["schema_and_all_table_counts_match"])
                with closing(read_connection(backup)) as copy:
                    self.assertEqual(copy.execute("SELECT * FROM products ORDER BY barcode").fetchall(),
                                     [("0001", None), ("0002", 0.0), ("0003", 450.0)])
                self.assertEqual(before, (file_identity(source), file_identity(wal)))
                with closing(read_connection(source)) as reader:
                    with self.assertRaises(sqlite3.OperationalError):
                        reader.execute("DELETE FROM products")
                saved = file_identity(backup)
                with self.assertRaises(FileExistsError):
                    backup_database(source, backup)
                self.assertEqual(saved, file_identity(backup))
                with self.assertRaises(ValueError):
                    backup_database(source, source)

    def test_population_groups_are_preserved_and_not_reactivated(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.executescript("""
                CREATE TABLE products (
                    barcode TEXT PRIMARY KEY, ingested_at TEXT,
                    normalized_brand TEXT, primary_brand TEXT,
                    include_in_product_table INTEGER, query_category TEXT,
                    observed_market_region_codes TEXT, created_t TEXT, last_modified_t TEXT
                );
                CREATE TABLE product_analysis (
                    barcode TEXT, release_run_id TEXT, prompt_version TEXT,
                    claim_source TEXT, pack_analysis_timestamp TEXT,
                    pack_analysis_attempted INTEGER
                );
                CREATE TABLE ingestion_log (id INTEGER PRIMARY KEY, notes TEXT);
            """)
            conn.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)", [
                ("A", "20260903", "Brand", "Brand", 1, "snacks", "FRANCE|UK_IE", None, None),
                ("B", "20260903", "Brand", "Brand", 0, "snacks", "FRANCE", None, None),
                ("OLD", "20260715", "Brand", "Brand", 1, "snacks", "FRANCE", None, None),
                ("UNDATED", None, "Brand", "Brand", 1, "snacks", "FRANCE", None, None),
            ])
            conn.execute("INSERT INTO product_analysis VALUES ('A','later_enrichment','p1','vision','20260920',1)")
            report = describe_baseline(conn)
            self.assertEqual(report["all_products"]["count"], 4)
            self.assertEqual(report["latest_ingestion_population"]["count"], 2)
            self.assertEqual(report["older_or_undated_population"]["count"], 2)
            self.assertEqual(report["deployment_scope_candidate"]["count"], 2)
            self.assertEqual(report["display_eligible_unique_products"]["count"], 1)
            self.assertEqual(report["vision_rows_total"], 1)
            self.assertEqual(sum(r["display_eligible_products"] for r in report["display_eligibility_by_scope"]), 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
