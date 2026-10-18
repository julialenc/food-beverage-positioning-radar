"""Offline transport, cutoff and resumable staging checks. No OFF calls."""
from contextlib import closing
from datetime import datetime, timezone
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.validation.check_08_incremental_ingestion import IngestionTests
from pipeline.rules import proxy_wave as proxy
from pipeline.maintenance import collect_off_snapshot as collector
from pipeline.maintenance.capture_database_baseline import sha256


def timestamp(value):
    return str(int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()))


def raw(code, created='2026-09-01T00:00:00', modified='2026-10-10T00:00:00', **fields):
    return dict(code=code, product_name='Synthetic snack', categories_tags='en:snacks',
                countries_tags='en:france', created_t=timestamp(created),
                last_modified_t=timestamp(modified), **fields)


def snapshot(path, records, corrupt=False):
    path.mkdir(exist_ok=True)
    columns = list(dict.fromkeys(key for record in records for key in record)) or sorted(proxy.REQUIRED)
    text = io.StringIO(newline='')
    out = csv.DictWriter(text, fieldnames=columns, delimiter='\t', quotechar=None,
                         quoting=csv.QUOTE_NONE, lineterminator='\n')
    out.writeheader()
    out.writerows(records)
    content = gzip.compress(text.getvalue().encode('utf-8'))
    if corrupt:
        content = content[:-8]
    source = path / 'source.csv.gz'
    source.write_bytes(content)
    collector.save(path / 'manifest.json', dict(status='complete', format='off-tsv-gzip-v1',
        file=source.name, bytes=len(content), sha256=sha256(source),
        retrieval_started_at='2026-10-17T10:00:00Z', retrieval_finished_at='2026-10-17T12:00:00Z',
        source='SYNTHETIC TEST; not an OFF retrieval'))
    return path


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = IngestionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.db
        self.directory = self.db.parent / 'snapshot'

    def stage(self, records, **kwargs):
        snapshot(self.directory, records)
        return proxy.stage(self.db, self.directory, wave_id='proxy', **kwargs)

    def decisions(self):
        return dict(self.fixture.rows('SELECT barcode,decision FROM proxy_observations'))

    def test_cutoff_end_of_local_day_and_october_modifications(self):
        report = self.stage([raw('0001', created='2026-09-29T21:59:59'),
                             raw('0002', created='2026-09-29T22:00:00'),
                             raw('0003', created='2026-09-30T00:00:00')])
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(self.decisions(), {'0001': 'process_new_candidate', '0002': 'exclude_after_cutoff', '0003': 'exclude_after_cutoff'})
        self.assertEqual(report['contract']['exclusive_cutoff_utc'], '2026-09-29T22:00:00+00:00')
        self.assertFalse(report['writer_connected'])

    def test_literal_off_quotes_are_preserved(self):
        record = raw('literal_quotes')
        record['product_name'] = '"mezzelune" semi circular stuffed pasta'
        record['categories_tags'] = 'en:dairies'
        self.stage([record])
        saved = self.fixture.rows("SELECT raw_json FROM proxy_observations WHERE barcode='literal_quotes'")[0][0]
        self.assertEqual(json.loads(saved)['product_name'], record['product_name'])

    def test_retained_scope_exit_missing_creation_and_absence(self):
        record = raw('B')
        record.update(created_t='', categories_tags='en:non-food', countries_tags='en:germany')
        before = self.fixture.rows('SELECT * FROM products ORDER BY barcode')
        self.stage([record])
        self.assertEqual(self.decisions()['B'], 'process_retained_scope_exit')
        self.assertEqual(before, self.fixture.rows('SELECT * FROM products ORDER BY barcode'))
        self.assertEqual(self.fixture.rows("SELECT membership FROM population_membership WHERE barcode='000A'"), [('retained',)])

    def test_invalid_creation_is_held_not_zero(self):
        records = []
        for i, value in enumerate(['', '0', 'nan', '-1', '1.5', '999999999999999999999999']):
            record = raw(str(i))
            record['created_t'] = value
            records.append(record)
        self.stage(records)
        self.assertEqual(set(self.decisions().values()), {'hold_creation_unknown'})
        saved = self.fixture.rows("SELECT raw_json FROM proxy_observations WHERE barcode='1'")[0][0]
        self.assertEqual(json.loads(saved)['created_t'], '0')

    def test_archived_reentry_hold_and_explicit_review(self):
        self.stage([raw('OLD')])
        self.assertEqual(self.decisions()['OLD'], 'hold_archived_reentry')
        with self.assertRaises(ValueError):
            proxy.stage(self.db, self.directory, wave_id='proxy', reviewed_reentries={'OLD': 'review'})

    def test_reviewed_archived_candidate(self):
        self.stage([raw('OLD')], reviewed_reentries={'OLD': 'reviewed fixture'})
        self.assertEqual(self.decisions()['OLD'], 'process_reviewed_reentry')
        self.assertEqual(self.fixture.rows("SELECT membership FROM population_membership WHERE barcode='OLD'"), [('archived',)])

    def test_revision_ordering(self):
        self.stage([raw('B', modified='2026-08-28T12:00:00'),
                    raw('000A', modified='2026-08-29T12:00:00'),
                    raw('future', modified='2026-10-18T12:00:00')])
        self.assertEqual(self.decisions(), {'B': 'hold_stale_revision', '000A': 'carry_forward_equal_revision', 'future': 'hold_revision_after_retrieval'})

    def test_duplicates_identical_and_conflicting(self):
        item = raw('same')
        result = self.stage([item, item])
        self.assertEqual((result['scanned_rows'], result['unique_source_records']), (2, 1))

    def test_conflicting_duplicates_hold_both_raw_rows(self):
        first = raw('same')
        second = raw('same', modified='2026-10-11T00:00:00')
        result = self.stage([first, second], checkpoint_size=1)
        self.assertEqual((result['status'], result['scanned_rows'], result['source_conflict_barcodes'],
                          result['source_conflict_rows']), ('complete', 2, 1, 1))
        self.assertEqual(self.decisions(), {'same': 'hold_conflicting_source_duplicates'})
        stored = self.fixture.rows('SELECT raw_json FROM proxy_observations')[0][0]
        conflict = self.fixture.rows('SELECT source_row,raw_json FROM proxy_conflicts')[0]
        self.assertEqual(json.loads(stored), first)
        self.assertEqual(conflict[0], 2)
        self.assertEqual(json.loads(conflict[1]), second)

    def test_conflict_after_out_of_scope_first_row_is_not_admitted(self):
        first = raw('same', created='2026-10-01T00:00:00')
        first['categories_tags'] = 'en:non-food'
        second = raw('same')
        result = self.stage([first, second], checkpoint_size=1)
        self.assertEqual(result['source_conflict_barcodes'], 1)
        self.assertEqual(self.decisions(), {})
        self.assertEqual(self.fixture.rows('SELECT barcode FROM proxy_conflicts'), [('same',)])

    def test_interruption_resume_and_exact_replay(self):
        snapshot(self.directory, [raw('1'), raw('2'), raw('3')])
        original = proxy.decide
        calls = 0
        def interrupt(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('synthetic interruption')
            return original(*args, **kwargs)
        with patch.object(proxy, 'decide', interrupt), self.assertRaises(RuntimeError):
            proxy.stage(self.db, self.directory, wave_id='proxy', checkpoint_size=1)
        self.assertEqual(self.fixture.rows('SELECT status,scanned_rows FROM proxy_waves'), [('incomplete', 1)])
        result = proxy.stage(self.db, self.directory, wave_id='proxy', checkpoint_size=1)
        self.assertEqual((result['status'], result['unique_source_records']), ('complete', 3))
        before = self.fixture.snapshot()
        self.assertEqual(proxy.stage(self.db, self.directory, wave_id='proxy'), result)
        self.assertEqual(self.fixture.snapshot(), before)

    def test_changed_source_cutoff_and_path_refused(self):
        self.stage([raw('1')])
        with self.assertRaises(ValueError):
            proxy.stage(self.db, self.directory, wave_id='proxy', cutoff='2026-09-28')
        with (self.directory / 'source.csv.gz').open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaises(ValueError):
            proxy.stage(self.db, self.directory, wave_id='proxy')
        with self.assertRaises(ValueError):
            proxy.stage(ROOT / 'pages/overview.py', self.directory, wave_id='proxy')

    def test_corrupt_gzip_never_completes(self):
        snapshot(self.directory, [raw('1')], corrupt=True)
        with self.assertRaises((EOFError, OSError)):
            proxy.stage(self.db, self.directory, wave_id='proxy')
        self.assertEqual(self.fixture.rows('SELECT status FROM proxy_waves'), [('incomplete',)])

    def test_empty_export_refused(self):
        with self.assertRaisesRegex(ValueError, 'Empty bulk'):
            self.stage([])


class Response:
    def __init__(self, content, status=200, headers=None, fail=False):
        self.content, self.status_code, self.fail = content, status, fail
        self.headers = {'Content-Length': str(len(content)), 'ETag': '"fixture"', **(headers or {})}
        self.url = collector.URL
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError('HTTP failure')
    def iter_content(self, chunk_size):
        yield self.content[:10]
        if self.fail: raise RuntimeError('network interruption')
        yield self.content[10:]


class Session:
    def __init__(self, responses): self.responses, self.calls = iter(responses), []
    def get(self, url, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


class TransportTests(unittest.TestCase):
    def setUp(self):
        collector.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=collector.SNAPSHOTS)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.content = gzip.compress(b'code\tproduct_name\n00001\tfixture\n')

    def test_download_resume_same_etag_and_replay(self):
        with self.assertRaises(RuntimeError):
            collector.collect(self.path, Session([Response(self.content, fail=True)]))
        self.assertFalse((self.path / 'manifest.json').exists())
        response = Response(self.content[10:], 206, {'Content-Range': f'bytes 10-{len(self.content)-1}/{len(self.content)}'})
        session = Session([response])
        manifest = collector.collect(self.path, session)
        self.assertEqual(session.calls[0]['headers']['If-Range'], '"fixture"')
        self.assertEqual(json.loads(manifest.read_text())['status'], 'complete')
        self.assertEqual((self.path / 'source.csv.gz').read_bytes(), self.content)
        self.assertEqual(collector.collect(self.path, Session([])), manifest)

    def test_changed_server_or_ignored_range_preserves_partial(self):
        with self.assertRaises(RuntimeError):
            collector.collect(self.path, Session([Response(self.content, fail=True)]))
        before = (self.path / 'source.csv.gz.part').read_bytes()
        with self.assertRaises(ValueError):
            collector.collect(self.path, Session([Response(self.content)]))
        self.assertEqual((self.path / 'source.csv.gz.part').read_bytes(), before)
        self.assertFalse((self.path / 'manifest.json').exists())

    def test_truncated_gzip_cannot_complete(self):
        with self.assertRaises((EOFError, OSError)):
            collector.collect(self.path, Session([Response(self.content[:-8])]))
        self.assertFalse((self.path / 'manifest.json').exists())


def full_size_trial(policy_trial):
    from pipeline.rules import incremental_ingestion as writer
    from pipeline.maintenance.capture_database_baseline import file_identity, protected_paths, read_connection
    from pipeline.maintenance.run_incremental_ingestion_trial import table_digest
    source_manifest = json.loads((policy_trial / 'manifest.json').read_text(encoding='utf-8'))
    baseline = Path(source_manifest['baseline_directory'])
    paths = protected_paths() + list(baseline.glob('*')) + list(policy_trial.glob('*'))
    paths += [ROOT / 'database/positioning_radar.db', ROOT / 'database/positioning_radar.db-wal']
    print('Recording protected-file hashes...', flush=True)
    protected = {str(p): file_identity(p) for p in paths if not p.is_dir()}
    directory = writer.TRIALS / datetime.now(timezone.utc).strftime('proxy_validation_%Y%m%dT%H%M%S_%fZ')
    print('Creating full-size copy...', flush=True)
    database = writer.create_copy(policy_trial, directory)
    print('Recording original table identities...', flush=True)
    with closing(read_connection(database)) as conn:
        original_schema = conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        original = {t: table_digest(conn, t) for t in tables}
        retained = conn.execute("SELECT barcode FROM retained_products WHERE last_modified_t < '2026-09-01' AND last_modified_t IS NOT NULL ORDER BY barcode LIMIT 2").fetchall()
        archived = conn.execute("SELECT barcode FROM population_membership WHERE membership='archived' ORDER BY barcode LIMIT 1").fetchone()[0]
        code_b, absent_a = retained[0][0], retained[1][0]
        labels = ['SYNTHETIC_PROXY_EARLY', 'SYNTHETIC_PROXY_LATE', 'SYNTHETIC_PROXY_UNKNOWN']
        for barcode in labels:
            if conn.execute('SELECT 1 FROM products WHERE barcode=?', (barcode,)).fetchone():
                raise ValueError('Synthetic barcode collision')
    retained_update = raw(code_b)
    retained_update.update(categories_tags='en:non-food', countries_tags='en:germany', created_t='')
    unknown = raw(labels[2])
    unknown['created_t'] = ''
    records = [retained_update, raw(labels[0]), raw(labels[1], created='2026-10-01T00:00:00'), unknown, raw(archived)]
    source_dir = snapshot(directory / 'synthetic_snapshot', records)
    print('Staging synthetic evidence and cutoff decisions...', flush=True)
    report = proxy.stage(database, source_dir, wave_id='synthetic_september_proxy', checkpoint_size=2)
    if report['decisions'] != {'process_retained_scope_exit': 1, 'process_new_candidate': 1,
                              'exclude_after_cutoff': 1, 'hold_creation_unknown': 1, 'hold_archived_reentry': 1}:
        raise AssertionError(report)
    saved_identity = file_identity(database)
    if proxy.stage(database, source_dir, wave_id='synthetic_september_proxy') != report:
        raise AssertionError('Staging replay differs')
    if file_identity(database) != saved_identity:
        raise AssertionError('Staging replay changed the copy')
    print('Verifying original rows, membership and protected artifacts...', flush=True)
    with closing(read_connection(database)) as conn:
        for table, expected in original.items():
            if table_digest(conn, table) != expected:
                raise AssertionError(f'Original table changed: {table}')
        schema = conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        if any(row not in schema for row in original_schema):
            raise AssertionError('Original schema changed')
        if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or conn.execute('PRAGMA foreign_key_check').fetchall():
            raise AssertionError('Integrity/foreign key check failed')
        if conn.execute('SELECT membership FROM population_membership WHERE barcode=?', (absent_a,)).fetchone() != ('retained',):
            raise AssertionError('Absent retained record lost membership')
    if any(file_identity(Path(p)) != identity for p, identity in protected.items()):
        raise AssertionError('Protected source/artifact changed')
    collector.save(directory / 'proxy_report.json', dict(report, synthetic=True,
        all_original_tables_sha256=original, original_schema_unchanged=True,
        protected_files_unchanged=protected, replay_byte_identity=True,
        integrity_check='ok', foreign_key_check='ok',
        code_sha256={str(p.relative_to(ROOT)): sha256(p) for p in
            [Path(__file__), ROOT / 'pipeline/rules/proxy_wave.py', ROOT / 'pipeline/maintenance/collect_off_snapshot.py']}))
    (directory / 'REPORT.md').write_text(
        '# Proxy cutoff staging validation\n\nCompleted on a full-size copy with five synthetic observations.\n\n'
        '- Retained scope exit and pre-cutoff new candidate staged for processing.\n'
        '- Post-cutoff candidate excluded; unknown creation and archived re-entry held.\n'
        '- All original tables and schema unchanged, including products, analysis and membership.\n'
        '- Exact replay preserved database byte identity; integrity/foreign keys passed.\n'
        '- Working DB, frozen baseline, source trial, deployment and presentation/reference artifacts unchanged.\n\n'
        'No live OFF retrieval or product admission occurred. Writer connection remains the next step.\n', encoding='utf-8')
    print(f'COMPLETE: {directory}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-size-policy-trial', type=Path)
    args = parser.parse_args()
    # Imported fixture class is not part of this suite.
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)
                               for c in (ProxyTests, TransportTests)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful() and args.full_size_policy_trial:
        full_size_trial(args.full_size_policy_trial)
    sys.exit(not result.wasSuccessful())
