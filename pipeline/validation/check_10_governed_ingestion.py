"""Integration checks using the real governance transforms and copy-only writer."""
from contextlib import closing, redirect_stdout
import argparse
from datetime import datetime, timezone
import io
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.validation.check_08_incremental_ingestion import IngestionTests
from pipeline.validation.check_09_proxy_wave import raw, snapshot
from pipeline.rules import proxy_wave, governed_ingestion as governed
from pipeline.stages import stage_01a_bootstrap_from_off_bulk as bulk


def product(code, **changes):
    record = dict.fromkeys(bulk.ALL_NEEDED, '')
    record.update(raw(code))
    record.update(brands='Test', quantity='500 g', ingredients_text='Ingredients: wheat flour, sugar, salt',
                  **{'energy-kcal_100g': '400', 'fat_100g': '15', 'saturated-fat_100g': '3',
                     'carbohydrates_100g': '60', 'sugars_100g': '10', 'fiber_100g': '3',
                     'proteins_100g': '5', 'salt_100g': '0.5', 'nova_group': '3',
                     'nutriscore_grade': 'c', 'image_url': 'https://example.invalid/fixture.jpg'})
    record.update(changes)
    return record


class GovernedTests(unittest.TestCase):
    def test_streaming_fingerprint_matches_canonical_json(self):
        value = [{'z': ['crème', None, 0.0], 'a': {'b': True}}, ('001', 'milk')]
        expected = hashlib.sha256(governed.writer.canonical(value).encode('utf-8')).hexdigest()
        self.assertEqual(governed.fingerprint(value), expected)

    def test_streamed_stage_and_peer_identities_match_original_shape(self):
        self.stage([product('B'), product('00000003')])
        with closing(sqlite3.connect(self.db)) as conn:
            wave = conn.execute('SELECT contract_json,status,scanned_rows FROM proxy_waves').fetchone()
            rows = conn.execute('SELECT barcode,raw_json,decision,category_candidate,membership_before,source_modified_utc,review_reference '
                                'FROM proxy_observations ORDER BY barcode').fetchall()
            conflicts = conn.execute('SELECT barcode,source_row,first_source_sha256,conflicting_sha256,raw_json '
                                     'FROM proxy_conflicts ORDER BY source_row').fetchall()
            self.assertEqual(governed.staged_identity(conn, 'wave')[0], governed.fingerprint([wave, rows, conflicts]))
            columns = ','.join('"' + c + '"' for c in governed.PEER_FIELDS)
            peers = conn.execute(f'SELECT {columns} FROM retained_products ORDER BY barcode').fetchall()
            self.assertEqual(governed.peer_snapshot(conn), governed.fingerprint(peers))

    def setUp(self):
        self.fixture = IngestionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.db
        self.source = self.db.parent / 'snapshot'
        self.quiet = redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def stage(self, records):
        snapshot(self.source, records)
        proxy_wave.stage(self.db, self.source, wave_id='wave')

    def test_full_connection_preserves_history_pack_evidence_and_leading_zero(self):
        self.stage([product('B', **{'proteins_100g': '0', 'fiber_100g': ''}), product('00000003'),
                    product('LATE', created_t='1790812800')])
        report = governed.connect(self.db, 'wave')
        self.assertEqual(report['accepted'], 2)
        self.assertEqual(self.fixture.rows("SELECT barcode FROM products WHERE barcode IN ('00000003','LATE')"), [('00000003',)])
        self.assertEqual(self.fixture.rows("SELECT protein_100g_off_raw,fiber_100g_off_raw FROM products WHERE barcode='B'"), [(0.0, None)])
        self.assertEqual(self.fixture.rows("SELECT pack_claims_found,claim_source FROM product_analysis WHERE barcode='B'"), [('old evidence', 'vision')])
        self.assertEqual(self.fixture.rows('SELECT COUNT(*) FROM incremental_history'), [(2,)])
        self.assertEqual(self.fixture.rows("SELECT quantity FROM products WHERE barcode='000A'"), [('500 g',)])
        before = self.fixture.snapshot()
        self.assertEqual(governed.connect(self.db, 'wave')['result']['status'], 'replayed')
        self.assertEqual(self.fixture.snapshot(), before)

    def test_scope_exit_retained_and_reviewed_override_applied(self):
        self.stage([product('B', categories_tags='en:non-food', countries_tags='en:germany'),
                    product('4311596490202', brands='incorrect fixture brand')])
        governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.rows("SELECT membership FROM population_membership WHERE barcode='B'"), [('retained',)])
        self.assertEqual(self.fixture.rows("SELECT COUNT(*) FROM retained_deployment_products WHERE barcode='B'"), [(0,)])
        result = self.fixture.rows("SELECT normalized_brand,query_category,off_brands_raw FROM products WHERE barcode='4311596490202'")
        self.assertEqual(result, [('Boost', 'beverages', 'incorrect fixture brand')])

    def test_missing_columns_are_explicitly_held(self):
        self.stage([raw('B')])
        report = governed.connect(self.db, 'wave')
        self.assertEqual(report['accepted'], 0)
        self.assertIn('B', report['holds'])
        self.assertEqual(self.fixture.rows("SELECT quantity FROM products WHERE barcode='B'"), [('500 g',)])

    def test_empty_records_are_explicitly_held(self):
        self.stage([product('NEW', product_name='', ingredients_text='', categories_tags='en:beverages')])
        report = governed.connect(self.db, 'wave')
        self.assertEqual(report['accepted'], 0)
        self.assertEqual(report['holds']['NEW'], 'no_product_name_or_ingredients')

    def test_ineligible_ingredients_clear_only_owned_analysis(self):
        self.stage([product('B', ingredients_text='')])
        governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.rows("SELECT composition_marker_score,pack_claims_found FROM product_analysis WHERE barcode='B'"), [(None, 'old evidence')])

    def test_invalid_nutrition_preserved_but_hidden(self):
        self.stage([product('B', **{'salt_100g': '80'})])
        governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.rows("SELECT salt_100g_off_raw,include_in_product_table FROM products WHERE barcode='B'"), [(80.0, 0)])
        self.assertEqual(self.fixture.rows("SELECT membership FROM population_membership WHERE barcode='B'"), [('retained',)])

    def test_peer_warnings_use_retained_population(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            for i in range(12):
                code = f'PEER{i}'
                conn.execute("INSERT INTO products (barcode,primary_brand,normalized_brand,query_category,observed_market_region_codes,include_in_product_table,sugars_100g,sugars_100g_off_raw,last_modified_t) VALUES (?,'test','Test','snacks','FRANCE',1,?,?, '2026-08-29 12:00:00')", (code, i+1, i+1))
                conn.execute("INSERT INTO population_membership VALUES (?,'retained','seed','fixture','fixture','approved_baseline')", (code,))
        self.stage([product('B', **{'sugars_100g': '100', 'carbohydrates_100g': '100', 'fat_100g': '0',
                                  'saturated-fat_100g': '0', 'proteins_100g': '0', 'fiber_100g': '0', 'salt_100g': '0'})])
        governed.connect(self.db, 'wave')
        reason = self.fixture.rows("SELECT warning_types FROM products WHERE barcode='B'")[0][0]
        self.assertIn('within_brand_nutrition_outlier', reason)

    def test_failed_membership_rolls_back_products_analysis_and_history(self):
        self.stage([product('B')])
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("CREATE TRIGGER fail_membership BEFORE INSERT ON population_admissions BEGIN SELECT RAISE(ABORT,'injected'); END")
        before = self.fixture.snapshot()
        with self.assertRaises(sqlite3.IntegrityError):
            governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.snapshot(), before)

    def test_staging_tamper_refused(self):
        self.stage([product('B')])
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE proxy_observations SET raw_json='{}'")
        with self.assertRaisesRegex(ValueError, 'raw evidence'):
            governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.rows('SELECT COUNT(*) FROM incremental_batches'), [(0,)])

    def test_context_drift_between_prepare_and_write_refused(self):
        self.stage([product('B')])
        actual = governed.writer.apply_batch
        def drift(database, batch, **kwargs):
            with closing(sqlite3.connect(database)) as conn, conn:
                conn.execute("UPDATE products SET sugars_100g=42 WHERE barcode='000A'")
            return actual(database, batch, **kwargs)
        with patch.object(governed.writer, 'apply_batch', drift), self.assertRaisesRegex(ValueError, 'context'):
            governed.connect(self.db, 'wave')
        self.assertEqual(self.fixture.rows('SELECT COUNT(*) FROM incremental_batches'), [(0,)])
        self.assertEqual(self.fixture.rows("SELECT quantity FROM products WHERE barcode='B'"), [('500 g',)])


def full_size_trial(policy_trial):
    from pipeline.maintenance.capture_database_baseline import file_identity, protected_paths, read_connection, write_json
    from pipeline.maintenance.run_incremental_ingestion_trial import table_digest
    policy_trial = policy_trial.resolve()
    manifest = json.loads((policy_trial / 'manifest.json').read_text(encoding='utf-8'))
    paths = protected_paths() + list(Path(manifest['baseline_directory']).glob('*')) + list(policy_trial.glob('*'))
    paths += [ROOT / 'database/positioning_radar.db', ROOT / 'database/positioning_radar.db-wal']
    print('Recording protected file identities...', flush=True)
    protected = {str(p): file_identity(p) for p in paths if not p.is_dir()}
    output = governed.writer.TRIALS / datetime.now(timezone.utc).strftime('governed_validation_%Y%m%dT%H%M%S_%fZ')
    print('Creating full-size copy...', flush=True)
    database = governed.writer.create_copy(policy_trial, output)
    new_code = '000000000000_SYNTHETIC_GOVERNED'
    held_code = 'SYNTHETIC_GOVERNED_HELD'
    late_code = 'SYNTHETIC_GOVERNED_LATE'
    with closing(read_connection(database)) as conn:
        codes = [r[0] for r in conn.execute("SELECT barcode FROM retained_products WHERE last_modified_t < '2026-09-01' AND last_modified_t IS NOT NULL ORDER BY barcode LIMIT 3")]
        updated, exited, absent = codes
        for code in (new_code, held_code, late_code):
            if conn.execute('SELECT 1 FROM products WHERE barcode=?', (code,)).fetchone():
                raise ValueError('Synthetic identifier collision')
        totals = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        unaffected_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                             if r[0] not in {'products', 'product_analysis', 'population_membership', 'population_admissions', 'incremental_batches', 'incremental_history'}]
        unaffected = {t: table_digest(conn, t) for t in unaffected_tables}
        prior_pack = conn.execute('SELECT pack_claims_found,claim_source FROM product_analysis WHERE barcode=?', (updated,)).fetchone()
    source = output / 'synthetic_snapshot'
    snapshot(source, [product(updated, quantity='450 g'), product(exited, categories_tags='en:non-food', countries_tags='en:germany'),
                      product(new_code), product(held_code, product_name='', ingredients_text='', categories_tags='en:beverages'),
                      product(late_code, created_t='1790812800')])
    proxy_wave.stage(database, source, wave_id='synthetic_governed_wave')
    print('Running governed processing and transactional writer...', flush=True)
    result = governed.connect(database, 'synthetic_governed_wave')
    if result['accepted'] != 3 or result['holds'] != {held_code: 'no_product_name_or_ingredients'}:
        raise AssertionError(result)
    byte_identity = file_identity(database)
    if governed.connect(database, 'synthetic_governed_wave')['result']['status'] != 'replayed' or file_identity(database) != byte_identity:
        raise AssertionError('Replay changed copy')
    print('Verifying history, scope and protected artifacts...', flush=True)
    with closing(read_connection(database)) as conn:
        assert conn.execute('SELECT COUNT(*) FROM products').fetchone()[0] == totals + 1
        assert conn.execute('SELECT COUNT(*) FROM incremental_history').fetchone()[0] == 3
        assert conn.execute('SELECT COUNT(*) FROM retained_products WHERE barcode=?', (exited,)).fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM retained_deployment_products WHERE barcode=?', (exited,)).fetchone()[0] == 0
        assert conn.execute('SELECT membership FROM population_membership WHERE barcode=?', (absent,)).fetchone() == ('retained',)
        assert conn.execute('SELECT COUNT(*) FROM products WHERE barcode IN (?,?)', (held_code, late_code)).fetchone()[0] == 0
        if prior_pack is not None:
            assert conn.execute('SELECT pack_claims_found,claim_source FROM product_analysis WHERE barcode=?', (updated,)).fetchone() == prior_pack
        for table, expected in unaffected.items():
            assert table_digest(conn, table) == expected, table
        assert conn.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert all(file_identity(Path(p)) == identity for p, identity in protected.items())
    write_json(output / 'validation.json', dict(status='complete', synthetic=True, result=result,
        protected_files_unchanged=protected, unaffected_tables_sha256=unaffected,
        integrity_check='ok', foreign_key_check='ok', replay_byte_identity=True,
        code_sha256=governed.rule_identity()))
    (output / 'REPORT.md').write_text('# Governed writer connection validation\n\n'
        'Completed on a fresh full-size copy with synthetic source observations.\n\n'
        '- Three accepted records: retained update, retained scope exit and new product.\n'
        '- Empty record held; post-cutoff record excluded.\n'
        '- Product/analysis history and exact replay verified; pack evidence preserved.\n'
        '- Integrity, foreign keys, unaffected auxiliary tables and protected-file checks passed.\n'
        '- No live OFF collection, production write, aggregate rebuild or deployment.\n', encoding='utf-8')
    print(f'COMPLETE: {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-size-policy-trial', type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GovernedTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful() and args.full_size_policy_trial:
        full_size_trial(args.full_size_policy_trial)
    sys.exit(not result.wasSuccessful())
