"""Offline population and claim freshness checks."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import sqlite3
import unittest
from pipeline.rules.claim_freshness import assess, evidence_key
from shared.release_population import install_population


class ReleaseTests(unittest.TestCase):
    def test_release_work_copy_preserves_governed_state_without_proxy_scan(self):
        import tempfile
        from contextlib import closing
        from pipeline.maintenance.build_incremental_release import release_work_copy
        with tempfile.TemporaryDirectory(dir=ROOT / 'data/06_brand_governance_outputs/incremental_ingestion_trials') as directory:
            source, work = Path(directory) / 'source.db', Path(directory) / 'work.db'
            with closing(sqlite3.connect(source)) as c:
                c.executescript('''
                    CREATE TABLE products(barcode TEXT PRIMARY KEY, product_name TEXT);
                    CREATE TABLE incremental_batches(batch_id TEXT PRIMARY KEY);
                    CREATE TABLE incremental_history(batch_id TEXT REFERENCES incremental_batches(batch_id), barcode TEXT REFERENCES products(barcode));
                    CREATE TABLE proxy_waves(wave_id TEXT PRIMARY KEY);
                    CREATE TABLE proxy_seen(wave_id TEXT REFERENCES proxy_waves(wave_id), barcode TEXT);
                    CREATE TABLE proxy_observations(wave_id TEXT REFERENCES proxy_waves(wave_id), raw_json TEXT);
                    CREATE TABLE proxy_conflicts(wave_id TEXT REFERENCES proxy_waves(wave_id), raw_json TEXT);
                    CREATE TABLE reports(id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT);
                    CREATE INDEX idx_products_name ON products(product_name);
                    CREATE VIEW retained_products AS SELECT * FROM products;
                    INSERT INTO products VALUES ('001','Milk');
                    INSERT INTO incremental_batches VALUES ('governed:wave:1');
                    INSERT INTO incremental_history VALUES ('governed:wave:1','001');
                    INSERT INTO proxy_waves VALUES ('wave');
                    INSERT INTO proxy_seen VALUES ('wave','001');
                    INSERT INTO proxy_observations VALUES ('wave','{"code":"001"}');
                    INSERT INTO proxy_conflicts VALUES ('wave','{"code":"001"}');
                    INSERT INTO reports(id,value) VALUES (10,'old');
                    DELETE FROM reports;
                    INSERT INTO reports(id,value) VALUES (1,'current');
                ''')
                c.commit()
            counts = release_work_copy(source, work)
            self.assertEqual(counts['products'], 1)
            with closing(sqlite3.connect(source)) as original, closing(sqlite3.connect(work)) as candidate:
                self.assertEqual(original.execute('SELECT COUNT(*) FROM proxy_seen').fetchone()[0], 1)
                self.assertEqual(candidate.execute('SELECT * FROM products').fetchall(), [('001','Milk')])
                self.assertEqual(candidate.execute('SELECT * FROM retained_products').fetchall(), [('001','Milk')])
                self.assertEqual(candidate.execute('SELECT * FROM incremental_history').fetchall(), [('governed:wave:1','001')])
                self.assertEqual(candidate.execute("SELECT name FROM sqlite_master WHERE name LIKE 'proxy_%' ORDER BY name").fetchall(), [('proxy_waves',)])
                self.assertEqual(candidate.execute("SELECT seq FROM sqlite_sequence WHERE name='reports'").fetchone(), (10,))
                self.assertEqual(candidate.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_legacy_selection(self):
        with sqlite3.connect(':memory:') as c:
            c.execute('CREATE TABLE products(barcode TEXT,ingested_at TEXT)')
            c.executemany('INSERT INTO products VALUES (?,?)',[('A','20260829'),('B','20261017')])
            install_population(c, require_complete=True)
            self.assertEqual(c.execute('SELECT * FROM current_product_barcodes').fetchall(), [('B',)])

    def test_retained_carry_forward_and_archive(self):
        with sqlite3.connect(':memory:') as c:
            c.execute('CREATE TABLE population_membership(barcode TEXT,membership TEXT)')
            c.executemany('INSERT INTO population_membership VALUES (?,?)',[('A','retained'),('B','retained'),('OLD','archived')])
            install_population(c)
            self.assertEqual(c.execute('SELECT * FROM current_product_barcodes').fetchall(), [('A',),('B',)])
            with self.assertRaisesRegex(ValueError, 'completed'):
                install_population(c, require_complete=True)

    def test_incomplete_release_refused_then_complete_population(self):
        with sqlite3.connect(':memory:') as c:
            c.execute('CREATE TABLE release_manifest(status TEXT)')
            c.execute("INSERT INTO release_manifest VALUES ('building')")
            c.execute('CREATE TABLE release_population(barcode TEXT)')
            c.execute("INSERT INTO release_population VALUES ('A')")
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                install_population(c, require_complete=True)
            c.execute("UPDATE release_manifest SET status='complete'")
            install_population(c, require_complete=True)
            self.assertEqual(c.execute('SELECT * FROM current_product_barcodes').fetchall(), [('A',)])

    def setUp(self):
        self.product = dict(barcode='001',image_url='https://images.openfoodfacts.org/images/products/001/front_en.3.400.jpg',product_name='Milk',brands='Test')
        self.analysis = dict(barcode='001',pack_claims_found='',llm_status='success',claim_extraction_status='completed',pack_analysis_timestamp='20260901',prompt_version='v5',claims_json='{}')
        self.index = {evidence_key(self.analysis): [self.product.copy()]}

    def test_confirmed_no_claim_is_observation(self):
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'matched_image_reference')

    def test_unanalyzed_is_unknown(self):
        self.analysis['pack_claims_found'] = None
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'no_stored_observation')

    def test_changed_image(self):
        self.product['image_url'] = self.product['image_url'].replace('.3.', '.4.')
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'image_reference_changed')

    def test_failed_attempt_cannot_certify_old_claims(self):
        self.analysis['llm_status'] = 'failed'
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'unknown_attempt_provenance')

    def test_missing_provenance(self):
        self.assertEqual(assess(self.product,self.analysis,{})[0], 'unknown_image_provenance')

    def test_changed_context(self):
        self.product['product_name'] = 'Free from milk'
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'text_context_changed')

    def test_conflicting_evidence(self):
        self.index[evidence_key(self.analysis)].append(self.product | {'image_url':'different'})
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'conflicting_image_provenance')

    def test_nutrition_edit_does_not_invalidate_pack(self):
        self.product['sugars_100g'] = 0
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'matched_image_reference')

    def test_reporting_dates_support_iso_epoch_and_exclude_after_cutoff(self):
        import pandas as pd
        from pipeline.stages.stage_13_build_app_summaries import compute_market_trend_weekly
        frame = pd.DataFrame([dict(query_category='snacks', created_t=value, pack_analysis_attempted=0,
            energy_kcal=100,protein_100g=5,fiber_100g=2,carbs_100g=20,sugars_100g=2,nova_group=1,
            quantity='100g',claim_category_1=None,additives_tags='') for value in
            ['2026-09-01T00:00:00', '1788220800', '2026-10-01T00:00:00', None]])
        result = compute_market_trend_weekly(frame, '2026-09-29', 'test')[0]
        self.assertEqual(result['new_product_count'], 2)
        self.assertEqual(result['product_count'], 4)
        self.assertIsNotNone(result['avg_protein_per_kcal'])

    def test_downstream_loaders_include_unchanged_retained_rows(self):
        from pipeline.stages.stage_05_load_database import DDL_PRODUCTS
        from pipeline.stages import stage_14_compute_region_benchmarks as benchmarks
        from pipeline.stages import stage_15_compute_profile_intersections as intersections
        from pipeline.stages import stage_16_build_chart_ranges as charts
        with sqlite3.connect(':memory:') as c:
            c.executescript(DDL_PRODUCTS)
            c.execute('CREATE TABLE population_membership(barcode TEXT,membership TEXT)')
            for code, stamp, membership in [('001','20260829','retained'),('002','20261017','retained'),('003','20261017','archived')]:
                c.execute("INSERT INTO products (barcode,ingested_at,primary_brand,normalized_brand,query_category,observed_market_region_codes,include_in_product_table,energy_kcal) VALUES (?,?,NULL,'test','snacks','FRANCE',1,100)", (code,stamp))
                c.execute('INSERT INTO population_membership VALUES (?,?)', (code,membership))
            self.assertEqual(len(benchmarks.load_data(c)), 2)
            self.assertEqual(len(intersections.load_data(c)), 2)
            self.assertEqual({r['barcode'] for r in charts.load_region_category_data(c)}, {'001','002'})

    def test_actual_prompt_brand_not_raw_brand_list(self):
        self.product['primary_brand'] = 'Test'
        self.product['brands'] = 'Test, Other'
        self.assertEqual(assess(self.product,self.analysis,self.index)[0], 'matched_image_reference')

    def test_merged_and_checkpoint_files_are_not_extraction_evidence(self):
        import tempfile,csv
        from pipeline.rules.claim_freshness import load_evidence
        with tempfile.TemporaryDirectory(dir=ROOT / "data/06_brand_governance_outputs/incremental_ingestion_trials") as directory:
            row = self.analysis | self.product
            for name in ('merged_results.csv','vision_results_checkpoint.csv','vision_results_final.csv'):
                with (Path(directory)/name).open('w',newline='',encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(row))
                    writer.writeheader();writer.writerow(row)
            index, manifest = load_evidence(directory)
            self.assertEqual(len(index[evidence_key(self.analysis)]), 1)
            self.assertEqual([Path(p).name for p in manifest], ['vision_results_final.csv'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
