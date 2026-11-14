"""Regression checks for identity preservation and deterministic alias handling."""
import io
import sqlite3
import unittest
from unittest.mock import patch
import pandas as pd
from pipeline.rules import barcode_identity as identity
from pipeline.rules import population_policy

class BarcodeIdentityTests(unittest.TestCase):
    def test_leading_zero_csv_round_trip(self):
        frame = pd.read_csv(io.StringIO("barcode,name\n0010700105417,Candy\n"), dtype={"barcode":str})
        restored = pd.read_csv(io.StringIO(frame.to_csv(index=False)),dtype={"barcode":str})
        self.assertEqual(restored.barcode.iloc[0],"0010700105417")

    def test_known_alias(self):
        with patch.object(identity,"aliases",return_value={"10700105417":"0010700105417"}):
            self.assertEqual(identity.resolve("10700105417"),"0010700105417")
            self.assertEqual(identity.identity_key("10700105417"),identity.identity_key("0010700105417"))

    def test_nonstandard_is_preserved(self):
        for value in ("92000111102229400149","abc-001","12345","00000001","00000000"):
            self.assertFalse(identity.valid_gtin(value))
            self.assertEqual(identity.resolve(value),value)
        with self.assertRaises(ValueError): identity.resolve(10700105417)

    def test_repeat_admission_and_governance(self):
        db = sqlite3.connect(":memory:")
        db.executescript("CREATE TABLE products(barcode TEXT PRIMARY KEY);CREATE TABLE population_membership(barcode TEXT PRIMARY KEY,membership TEXT,seed_ingested_at TEXT,first_retained_batch TEXT,last_accepted_batch TEXT,decision_reason TEXT);CREATE TABLE population_admissions(batch_id TEXT,barcode TEXT,admission_kind TEXT,review_reference TEXT,PRIMARY KEY(batch_id,barcode));INSERT INTO products VALUES ('0010700105417');INSERT INTO population_membership VALUES ('0010700105417','retained',NULL,'base','base','approved');")
        with patch.object(identity,"aliases",return_value={"10700105417":"0010700105417"}), patch.object(population_policy,"counts",return_value={}):
            population_policy.record_accepted_batch(db,["10700105417"],batch_id="repeat")
            population_policy.record_accepted_batch(db,["0010700105417"],batch_id="repeat")
            self.assertEqual(db.execute("SELECT count(*) FROM population_membership").fetchone()[0],1)
            db.execute("UPDATE population_membership SET membership='archived'")
            with self.assertRaises(ValueError): population_policy.preflight_batch(db,["10700105417"])
        db.close()

    def test_deployed_register(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE barcode_aliases(source_barcode TEXT,canonical_barcode TEXT)")
        db.execute("INSERT INTO barcode_aliases VALUES ('legacy-test','full-test')")
        with patch.object(identity,"aliases",return_value={}):
            identity.bind_aliases(db)
            self.assertEqual(identity.resolve("legacy-test"),"full-test")
        db.close()

    def test_regional_averages_count_each_product_once(self):
        from pipeline.stages import stage_05_load_database as loader
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE category_region_averages(snapshot TEXT,query_category TEXT,region TEXT,energy_kcal REAL,protein_per_kcal REAL,fiber_per_kcal REAL,satfat_per_kcal REAL,sugars_per_kcal REAL,sugars_100g REAL,salt_100g REAL)")
        rows=[dict(barcode=str(index),query_category="snacks",primary_country="France",normalized_brand="brand",primary_brand="brand",observed_market_region_codes="FRANCE|US_CANADA",energy_kcal=100,protein_100g=5) for index in range(20)]
        rows.append(dict(rows[0],barcode="extra",observed_market_region_codes="US_CANADA",energy_kcal=200))
        loader.compute_category_region_averages(pd.DataFrame(rows),db,"2026-09-29")
        values=dict(db.execute("SELECT region,energy_kcal FROM category_region_averages"))
        self.assertAlmostEqual(values["FRANCE"],100)
        self.assertAlmostEqual(values["US_CANADA"],2200/21)
        self.assertAlmostEqual(values["ALL"],2200/21)
        db.close()

    def test_valid_gtin_governance_spelling(self):
        from pipeline.stages import stage_05_load_database as loader
        with patch.object(identity,"aliases",return_value={}):
            reviewed={identity.identity_key("010700105417"):[{"region":"US_CANADA","brand":"approved"}]}
            self.assertEqual(loader._product_override_for_row(reviewed,"0010700105417","US_CANADA")["brand"],"approved")

if __name__ == "__main__": unittest.main()
