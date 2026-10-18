"""Create a fresh ingestion copy and apply an explicit batch or synthetic check.

python -B pipeline/maintenance/run_incremental_ingestion_trial.py --policy-trial PATH --synthetic-check
No API access, paid analysis, production changes or deployment export.
"""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules import incremental_ingestion as ingestion
from pipeline.rules import population_policy as policy
from pipeline.maintenance.capture_database_baseline import (
    file_identity, protected_paths, read_connection, write_json,
)


def table_digest(conn, table, exclude=None):
    sql = 'SELECT * FROM "' + table.replace('"', '""') + '"'
    params = ()
    if exclude is not None:
        sql += ' WHERE barcode<>?'
        params = (exclude,)
    digest = hashlib.sha256()
    # Rowid order is stable for this non-destructive trial.
    for row in conn.execute(sql + ' ORDER BY rowid', params):
        digest.update((ingestion.canonical(row) + '\n').encode('utf-8'))
    return digest.hexdigest()


def run(policy_trial, batch_file=None, synthetic=False):
    policy_trial = policy_trial.resolve()
    manifest = json.loads((policy_trial / 'manifest.json').read_text(encoding='utf-8'))
    baseline_dir = Path(manifest['baseline_directory'])
    protected = protected_paths() + list(baseline_dir.glob('*')) + list(policy_trial.glob('*'))
    protected += [ROOT / 'database/positioning_radar.db', ROOT / 'database/positioning_radar.db-wal']
    print('Recording protected-file hashes...', flush=True)
    before = {str(p): file_identity(p) for p in protected if not p.is_dir()}
    output = ingestion.TRIALS / datetime.now(timezone.utc).strftime('trial_%Y%m%dT%H%M%S_%fZ')
    print('Creating verified database copy...', flush=True)
    database = ingestion.create_copy(policy_trial, output)
    try:
        with closing(read_connection(database)) as conn:
            initial_counts = policy.counts(conn)
            if synthetic:
                cursor = conn.execute("SELECT * FROM retained_products WHERE last_modified_t IS NOT NULL "
                                      "AND last_modified_t < '2026-09-01' ORDER BY barcode LIMIT 1")
                row = cursor.fetchone()
                if row is None:
                    raise ValueError('No suitable synthetic update fixture')
                product = dict(zip([c[0] for c in cursor.description], row))
                barcode = product.pop('barcode')
                product.pop('ingested_at')
                new_barcode = '000000000000000000_SYNTHETIC_TRIAL'
                if conn.execute('SELECT 1 FROM products WHERE barcode=?', (new_barcode,)).fetchone():
                    raise ValueError('Synthetic barcode collision')
                source_time = (ingestion.revision(product['last_modified_t']) + timedelta(seconds=1)).isoformat()
                product.update(product_name='SYNTHETIC COPY-ONLY VALIDATION', last_modified_t=source_time)
                batch = dict(batch_id='synthetic_copy_trial', retrieved_at='2026-10-17T12:00:00Z',
                             source_reference='Synthetic fixtures, not an OFF download',
                             processing_reference='Existing governed values copied for transaction tests only',
                             completeness=dict(complete=True, record_count=2, reference='two synthetic records'),
                             reviewed_reentries={}, records=[
                                 dict(barcode=barcode, product={'last_modified_t': source_time, 'quantity': None},
                                      analysis={'processing_markers_found': 'SYNTHETIC VALIDATION'}),
                                 dict(barcode=new_barcode, product=product, analysis={})])
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                          "AND name NOT LIKE 'sqlite_%' AND name NOT IN "
                          "('ingestion_copy','incremental_batches','incremental_history','population_membership','population_admissions')")]
                unaffected = {t: table_digest(conn, t, barcode if t in ('products', 'product_analysis') else None) for t in tables}
                write_json(output / 'synthetic_batch.json', batch)
            else:
                batch = json.loads(batch_file.read_text(encoding='utf-8'))
        print('Applying transactional batch...', flush=True)
        result = ingestion.apply_batch(database, batch)
        after_apply = file_identity(database)
        replay = ingestion.apply_batch(database, batch)
        if file_identity(database) != after_apply or replay['status'] != 'replayed':
            raise RuntimeError('Exact replay changed the database')
        with closing(read_connection(database)) as conn:
            final_counts = policy.counts(conn)
            if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('Integrity check failed')
            if conn.execute('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Foreign-key check failed')
            if synthetic:
                # Exclude the deliberately added fixture as well as updated B.
                for table, expected in unaffected.items():
                    if table == 'products':
                        digest = hashlib.sha256()
                        for row in conn.execute('SELECT * FROM products WHERE barcode NOT IN (?,?) ORDER BY rowid', (barcode, new_barcode)):
                            digest.update((ingestion.canonical(row) + '\n').encode('utf-8'))
                        actual = digest.hexdigest()
                    else:
                        actual = table_digest(conn, table, barcode if table == 'product_analysis' else None)
                    if actual != expected:
                        raise RuntimeError(f'Unaffected table/rows changed: {table}')
                if final_counts['all_products'] != initial_counts['all_products'] + 1 or final_counts['retained'] != initial_counts['retained'] + 1:
                    raise RuntimeError('Unexpected population change')
                if final_counts['archived'] != initial_counts['archived'] or final_counts['unregistered_products']:
                    raise RuntimeError('Archived/unregistered population changed')
                if conn.execute('SELECT COUNT(*) FROM incremental_history').fetchone()[0] != 2:
                    raise RuntimeError('Expected two complete history snapshots')
        print('Verifying source, baseline and production artifacts unchanged...', flush=True)
        if any(file_identity(Path(path)) != identity for path, identity in before.items()):
            raise RuntimeError('A protected file changed during the trial')
        report = dict(status='complete', synthetic=synthetic, result=result, replay=replay,
                      initial_counts=initial_counts, final_counts=final_counts,
                      protected_files_unchanged=before, integrity_check='ok', foreign_key_check='ok',
                      unaffected_rows_verified=synthetic, database=file_identity(database),
                      code_sha256={str(p.relative_to(ROOT)): file_identity(p)['sha256'] for p in
                          [Path(__file__), ROOT / 'pipeline/rules/incremental_ingestion.py',
                           ROOT / 'pipeline/validation/check_08_incremental_ingestion.py']},
                      limitations=['No OFF collection or September cutoff filtering.',
                                   'No claim freshness, downstream integration or completed deployment release.',
                                   'Caller completeness/processing references are assertions, not independently certified.'])
        write_json(output / 'manifest.json', report)
        (output / 'REPORT.md').write_text(
            '# Transactional ingestion trial\n\nCompleted on a separate copy.\n\n'
            f'- Synthetic fixtures: {synthetic}\n- Changed products: {result["changed"]}\n'
            '- Exact replay preserved database byte identity.\n'
            '- Integrity and foreign-key checks passed.\n'
            f'- Unaffected original rows/tables verified: {synthetic}\n'
            '- Source trial, frozen baseline, working DB and protected artifacts unchanged.\n\n'
            'This is not a real OFF ingestion or a production-readiness certification.\n', encoding='utf-8')
        print(f'COMPLETE: {output}', flush=True)
        return output
    except BaseException as exc:
        write_json(output / 'FAILED.json', {'status': 'incomplete', 'error': str(exc)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy-trial', type=Path, required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--batch-file', type=Path)
    choice.add_argument('--synthetic-check', action='store_true')
    args = parser.parse_args()
    run(args.policy_trial, args.batch_file, args.synthetic_check)
