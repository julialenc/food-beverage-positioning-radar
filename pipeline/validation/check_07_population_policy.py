"""Test population membership with the real stage-05 product upsert function.

All product writes are to disposable in-memory databases. No OFF/API calls,
source-data changes, paid analysis, or production database writes occur.
Run: python -B pipeline/validation/check_07_population_policy.py
"""

from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
from pipeline.rules import population_policy as policy
from pipeline.stages.stage_05_load_database import DDL_PRODUCTS, PRODUCT_COLS, load_products


class PopulationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(DDL_PRODUCTS)
        self.write([self.product("ARCHIVED")], "20260715_225015")
        self.write([self.product("A"), self.product("B"),
                    self.product("HIDDEN", include_in_product_table=0)], "20260903_030215")
        self.seed()

    def product(self, barcode, **changes):
        row = dict.fromkeys(PRODUCT_COLS)
        row.update(barcode=barcode, product_name="Synthetic test product", quantity="500 g",
                   normalized_brand="Test", primary_brand="Test", query_category="snacks",
                   observed_market_region_codes="FRANCE", include_in_product_table=1,
                   include_in_aggregates=1, include_in_charts=1, protein_100g=0,
                   last_modified_t="2026-08-29 12:00:00")
        row.update(changes)
        return row

    def write(self, records, timestamp):
        # Real loader, full processed rows: does not reproduce its implementation.
        return load_products(pd.DataFrame(records, columns=PRODUCT_COLS), self.conn, timestamp)

    def seed(self, **changes):
        identity = policy.barcode_digest(self.conn,
            "SELECT barcode FROM products WHERE ingested_at=? ORDER BY barcode", ("20260903_030215",))
        kwargs = dict(baseline_id="fixture", baseline_sha256="fixture_only",
                      seed_ingested_at="20260903_030215", expected_retained=3,
                      expected_archived=1, expected_retained_digest=identity["sorted_barcodes_sha256"],
                      off_capture_date="2026-08-29", proxy_wave_2_cutoff="2026-09-29")
        kwargs.update(changes)
        return policy.initialize(self.conn, **kwargs)

    def members(self, view="retained_products"):
        return {r[0] for r in self.conn.execute(f"SELECT barcode FROM {view}")}

    def test_a_carried_b_updated_c_inserted_and_repeat_safe(self):
        records = [self.product("B", quantity="450 g", last_modified_t="2026-10-10 12:00:00"),
                   self.product("00000003", created_t="2026-10-12 12:00:00")]
        ids = [r["barcode"] for r in records]
        policy.preflight_batch(self.conn, ids)
        self.assertEqual(self.write(records, "20261017_120000"), (1, 1))
        policy.record_accepted_batch(self.conn, ids, batch_id="synthetic_future_wave")
        self.assertEqual(self.members(), {"A", "B", "HIDDEN", "00000003"})
        self.assertEqual(self.members("retained_display_products"), {"A", "B", "00000003"})
        self.assertEqual(self.conn.execute("SELECT quantity,ingested_at FROM products WHERE barcode='A'").fetchone(),
                         ("500 g", "20260903_030215"))
        self.assertEqual(self.conn.execute("SELECT quantity FROM products WHERE barcode='B'").fetchone()[0], "450 g")
        # Old MAX(ingested_at) rule would lose A; the new membership view does not.
        legacy = {r[0] for r in self.conn.execute("SELECT barcode FROM products WHERE ingested_at=(SELECT MAX(ingested_at) FROM products)")}
        self.assertNotIn("A", legacy)
        self.write(records, "20261017_120000")
        policy.record_accepted_batch(self.conn, ids, batch_id="synthetic_future_wave")
        self.assertEqual(policy.counts(self.conn)["all_products"], 5)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM population_admissions").fetchone()[0], 2)
        # October observations are deliberately accepted: September cutoff is metadata only.
        self.assertIn("00000003", self.members())

    def test_display_flag_changes_do_not_change_retention(self):
        self.write([self.product("HIDDEN", include_in_product_table=1),
                    self.product("B", include_in_product_table=0)], "20261017_120000")
        policy.record_accepted_batch(self.conn, ["HIDDEN", "B"], batch_id="quality_update")
        self.assertEqual(self.members(), {"A", "B", "HIDDEN"})
        self.assertEqual(self.members("retained_display_products"), {"A", "HIDDEN"})

    def test_scope_exit_is_retained_but_not_displayed(self):
        self.write([self.product("B", query_category="OUT_OF_SCOPE")], "20261017_120000")
        policy.record_accepted_batch(self.conn, ["B"], batch_id="scope_update")
        self.assertIn("B", self.members())
        self.assertNotIn("B", self.members("retained_deployment_products"))

    def test_archived_reentry_requires_review(self):
        with self.assertRaisesRegex(ValueError, "explicit review"):
            policy.preflight_batch(self.conn, ["ARCHIVED"])
        self.assertNotIn("ARCHIVED", self.members())
        review = {"ARCHIVED": "test-review-reference"}
        policy.preflight_batch(self.conn, ["ARCHIVED"], review)
        self.write([self.product("ARCHIVED")], "20261017_120000")
        policy.record_accepted_batch(self.conn, ["ARCHIVED"], batch_id="reviewed", reviewed_reentries=review)
        policy.record_accepted_batch(self.conn, ["ARCHIVED"], batch_id="reviewed", reviewed_reentries=review)
        self.assertIn("ARCHIVED", self.members())
        self.assertEqual(self.conn.execute("SELECT admission_kind,review_reference FROM population_admissions").fetchone(),
                         ("reviewed_reentry", "test-review-reference"))

    def test_empty_batch_and_invalid_batch_leave_membership_unchanged(self):
        before = policy.counts(self.conn)
        self.assertEqual(policy.record_accepted_batch(self.conn, [], batch_id="empty"), before)
        with self.assertRaises(ValueError):
            policy.record_accepted_batch(self.conn, ["A", "MISSING"], batch_id="failed")
        with self.assertRaises(ValueError):
            policy.preflight_batch(self.conn, ["A", "A"])
        with self.assertRaises(ValueError):
            policy.preflight_batch(self.conn, [123])
        self.assertEqual(policy.counts(self.conn), before)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM population_admissions").fetchone()[0], 0)

    def test_policy_refuses_reseeding(self):
        before = policy.counts(self.conn)
        with self.assertRaisesRegex(ValueError, "refusing to reseed"):
            self.seed()
        self.assertEqual(policy.counts(self.conn), before)

    def test_outer_transaction_can_roll_back_registration(self):
        self.conn.execute("BEGIN")
        policy.record_accepted_batch(self.conn, ["A"], batch_id="rolled_back")
        self.conn.rollback()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM population_admissions").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
