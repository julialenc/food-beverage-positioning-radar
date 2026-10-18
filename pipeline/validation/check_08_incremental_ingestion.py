"""Disposable copy-only ingestion checks. Run with python -B; no network use."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules import incremental_ingestion as ingestion
from pipeline.rules import population_policy as policy
from pipeline.stages.stage_05_load_database import DDL_PRODUCTS, DDL_PRODUCT_ANALYSIS, PRODUCT_COLS


class IngestionTests(unittest.TestCase):
    def setUp(self):
        ingestion.TRIALS.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ingestion.TRIALS)
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'trial.db'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(DDL_PRODUCTS)
            conn.execute(DDL_PRODUCT_ANALYSIS)
            for barcode, timestamp in [('000A', 'seed'), ('B', 'seed'), ('OLD', 'older')]:
                conn.execute('INSERT INTO products (barcode,ingested_at,last_modified_t,quantity,normalized_brand,'
                             'query_category,observed_market_region_codes,include_in_product_table,protein_100g) '
                             'VALUES (?,?,?,?,?,?,?,?,?)',
                             (barcode, timestamp, '2026-08-29 12:00:00', '500 g', 'Test', 'snacks', 'FRANCE', 1, 0))
            conn.execute("INSERT INTO product_analysis (barcode,claim_source,pack_claims_found) VALUES ('B','vision','old evidence')")
            digest = policy.barcode_digest(conn, "SELECT barcode FROM products WHERE ingested_at='seed' ORDER BY barcode")
            policy.initialize(conn, baseline_id='fixture', baseline_sha256='fixture', seed_ingested_at='seed',
                              expected_retained=2, expected_archived=1,
                              expected_retained_digest=digest['sorted_barcodes_sha256'],
                              off_capture_date='2026-08-29', proxy_wave_2_cutoff='2026-09-29')
            for sql in ingestion.DDL:
                conn.execute(sql)
            conn.execute("INSERT INTO ingestion_copy VALUES (1,'fixture')")

    def batch(self, records=None, name='wave1'):
        records = records if records is not None else [self.record()]
        return dict(batch_id=name, retrieved_at='2026-10-17T12:00:00Z',
                    source_reference='synthetic fixture', processing_reference='reviewed test pipeline',
                    completeness=dict(complete=True, record_count=len(records), reference='fixture inventory'),
                    records=records, reviewed_reentries={})

    def record(self, barcode='B', **changes):
        return dict(barcode=barcode, product=dict(last_modified_t='2026-09-20 12:00:00', **changes), analysis={})

    def rows(self, sql):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            return conn.execute(sql).fetchall()

    def snapshot(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            return '\n'.join(conn.iterdump())

    def rejected_unchanged(self, batch):
        before = self.snapshot()
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            ingestion.apply_batch(self.db, batch)
        self.assertEqual(before, self.snapshot())

    def test_carry_forward_new_product_history_and_presence(self):
        new = dict.fromkeys(set(PRODUCT_COLS) - {'barcode'})
        new.update(last_modified_t='2026-10-01 12:00:00', normalized_brand='Test',
                   query_category='snacks', observed_market_region_codes='FRANCE', include_in_product_table=1)
        record = self.record(quantity=None, protein_100g=0)
        record['analysis'] = {'processing_marker_count': 0}
        batch = self.batch([record, dict(barcode='00000003', product=new, analysis={})])
        self.assertEqual(ingestion.apply_batch(self.db, batch)['changed'], 2)
        self.assertEqual(self.rows("SELECT barcode FROM retained_products ORDER BY barcode"), [('00000003',), ('000A',), ('B',)])
        self.assertEqual(self.rows("SELECT quantity,protein_100g,normalized_brand FROM products WHERE barcode='B'"), [(None, 0.0, 'Test')])
        self.assertEqual(self.rows("SELECT pack_claims_found FROM product_analysis WHERE barcode='B'"), [('old evidence',)])
        history = self.rows("SELECT before_product,after_product,before_analysis,after_analysis FROM incremental_history WHERE barcode='B'")[0]
        self.assertEqual(json.loads(history[0])['quantity'], '500 g')
        self.assertIsNone(json.loads(history[1])['quantity'])
        self.assertEqual(json.loads(history[2])['pack_claims_found'], 'old evidence')
        self.assertEqual(json.loads(history[3])['processing_marker_count'], 0)

    def test_old_exact_replay_does_not_rewind_membership(self):
        first = self.batch()
        ingestion.apply_batch(self.db, first)
        second = self.batch(name='wave2')
        second['records'][0]['product']['last_modified_t'] = '2026-10-01 12:00:00'
        ingestion.apply_batch(self.db, second)
        before = self.snapshot()
        self.assertEqual(ingestion.apply_batch(self.db, first)['status'], 'replayed')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.rows("SELECT last_accepted_batch FROM population_membership WHERE barcode='B'"), [('wave2',)])

    def test_conflicting_batch_id(self):
        batch = self.batch()
        ingestion.apply_batch(self.db, batch)
        batch['records'][0]['product']['quantity'] = 'changed'
        self.rejected_unchanged(batch)

    def test_stale_equal_conflict_and_future_revision(self):
        for revision in ['2026-08-01 12:00:00', '2026-08-29 12:00:00', '2026-11-01 12:00:00']:
            with self.subTest(revision=revision):
                record = self.record(quantity='changed')
                record['product']['last_modified_t'] = revision
                self.rejected_unchanged(self.batch([record]))

    def test_unchanged_revision_no_history_and_empty_wave(self):
        record = self.record()
        record['product']['last_modified_t'] = '2026-08-29 12:00:00'
        self.assertEqual(ingestion.apply_batch(self.db, self.batch([record]))['changed'], 0)
        self.assertEqual(ingestion.apply_batch(self.db, self.batch([], name='empty'))['changed'], 0)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM incremental_history'), [(0,)])

    def test_archived_review_and_scope_visibility(self):
        batch = self.batch([self.record('OLD')])
        self.rejected_unchanged(batch)
        batch['reviewed_reentries'] = {'OLD': 'explicit fixture review'}
        ingestion.apply_batch(self.db, batch)
        ingestion.apply_batch(self.db, self.batch([self.record(query_category='OUT_OF_SCOPE')], name='scope'))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM retained_products WHERE barcode='B'"), [(1,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM retained_display_products WHERE barcode='B'"), [(0,)])

    def test_failure_after_product_and_history_writes_rolls_everything_back(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("CREATE TRIGGER inject_failure BEFORE INSERT ON population_admissions BEGIN SELECT RAISE(ABORT,'injected'); END")
        self.rejected_unchanged(self.batch([self.record(quantity='450 g')]))

    def test_entire_batch_preflight_before_writes(self):
        self.rejected_unchanged(self.batch([self.record(quantity='450 g'), self.record('NEW')]))
        self.rejected_unchanged(self.batch([self.record(), self.record()]))
        self.rejected_unchanged(self.batch([self.record(123)]))

    def test_contract_types_and_completeness(self):
        for key, value in [('quantity', 1), ('include_in_product_table', '1'),
                           ('protein_100g', float('nan')), ('bad_column', 'x'), ('ingested_at', 'x')]:
            with self.subTest(key=key):
                self.rejected_unchanged(self.batch([self.record(**{key: value})]))
        batch = self.batch()
        batch['completeness']['complete'] = False
        self.rejected_unchanged(batch)
        batch = self.batch()
        batch['completeness']['record_count'] = 2
        self.rejected_unchanged(batch)
        batch = self.batch()
        del batch['records'][0]['product']['last_modified_t']
        self.rejected_unchanged(batch)

    def test_unknown_baseline_revision_fails_closed(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE products SET last_modified_t=NULL WHERE barcode='B'")
        self.rejected_unchanged(self.batch())

    def test_successive_history_and_dynamic_gate(self):
        ingestion.apply_batch(self.db, self.batch([self.record(include_in_product_table=0)]))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM retained_display_products WHERE barcode='B'"), [(0,)])
        second = self.batch([self.record(include_in_product_table=1)], name='wave2')
        second['records'][0]['product']['last_modified_t'] = '2026-10-01 12:00:00'
        ingestion.apply_batch(self.db, second)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM retained_display_products WHERE barcode='B'"), [(1,)])
        history = self.rows("SELECT before_product,after_product FROM incremental_history WHERE barcode='B' ORDER BY batch_id")
        self.assertEqual(json.loads(history[0][1]), json.loads(history[1][0]))

    def test_path_guard(self):
        with self.assertRaises(ValueError):
            ingestion.apply_batch(ROOT / 'pipeline/rules/population_policy.py', self.batch())


if __name__ == '__main__':
    unittest.main(verbosity=2)
