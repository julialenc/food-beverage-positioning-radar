"""Build and validate a separate release candidate from a completed ingestion copy."""
import argparse
from collections import Counter
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import gzip
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules.incremental_ingestion import TRIALS
from pipeline.rules.claim_freshness import audit
from pipeline.maintenance.capture_database_baseline import sha256, read_connection, write_json, file_identity, protected_paths
from shared.release_population import install_population
from pipeline.stages import stage_05_load_database as loader
from pipeline.stages import stage_17_build_deployment_database as deployment
import pandas as pd

SNAPSHOT_TABLES = ('region_category_benchmarks', 'profile_intersections', 'axis_range_config', 'market_chart_bands', 'category_region_averages')
STAGING_ONLY_TABLES = frozenset({'proxy_seen', 'proxy_observations', 'proxy_conflicts'})


def release_work_copy(source, destination):
    """Copy the governed database without duplicating the pinned proxy scan.

    The complete scan stays in the source trial database. Release stages need
    product/history/population data and wave metadata, but never the raw proxy
    observations or the scan's four-million-barcode identity index.
    """
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if destination.exists() or source == destination:
        raise ValueError('Release work copy must be a new file distinct from its source')
    with closing(sqlite3.connect(destination, uri=True)) as dst:
        dst.execute('PRAGMA journal_mode=OFF')  # disposable candidate; source is untouched
        dst.execute('PRAGMA synchronous=OFF')
        dst.execute('ATTACH DATABASE ? AS pinned', (source.as_uri() + '?mode=ro',))
        objects = dst.execute("SELECT type,name,tbl_name,sql FROM pinned.sqlite_master "
                              "WHERE sql IS NOT NULL ORDER BY type,name").fetchall()
        tables = [(name, sql) for kind, name, _, sql in objects
                  if kind == 'table' and name not in STAGING_ONLY_TABLES and name != 'sqlite_sequence']
        if 'proxy_waves' not in {name for kind, name, _, _ in objects if kind == 'table'}:
            raise ValueError('Missing proxy wave metadata in governed copy')
        dst.execute('BEGIN')
        for name, sql in tables:
            dst.execute(sql)
            quoted = '"' + name.replace('"', '""') + '"'
            dst.execute(f'INSERT INTO main.{quoted} SELECT * FROM pinned.{quoted}')
        # AUTOINCREMENT state can be higher than the largest retained row ID.
        dst.execute('DELETE FROM sqlite_sequence')
        dst.execute('INSERT INTO sqlite_sequence SELECT * FROM pinned.sqlite_sequence '
                    'WHERE name NOT IN (?,?,?)', tuple(STAGING_ONLY_TABLES))
        for kind, name, table, sql in objects:
            if kind == 'index' and table not in STAGING_ONLY_TABLES:
                dst.execute(sql)
        for kind, name, table, sql in objects:
            if kind == 'view':
                dst.execute(sql)
        dst.commit()
        counts = {}
        for name, _ in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            source_count = dst.execute(f'SELECT COUNT(*) FROM pinned.{quoted}').fetchone()[0]
            work_count = dst.execute(f'SELECT COUNT(*) FROM main.{quoted}').fetchone()[0]
            if source_count != work_count:
                raise ValueError(f'Release work copy count mismatch: {name}')
            counts[name] = work_count
        expected_schema = {(kind, name, table, sql) for kind, name, table, sql in objects
                           if name not in STAGING_ONLY_TABLES and table not in STAGING_ONLY_TABLES
                           and name != 'sqlite_sequence'}
        actual_schema = set(dst.execute("SELECT type,name,tbl_name,sql FROM main.sqlite_master "
                                        "WHERE sql IS NOT NULL AND name!='sqlite_sequence'"))
        if actual_schema != expected_schema:
            raise ValueError('Release work copy schema differs from included source objects')
        if dst.execute('PRAGMA main.integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Release work copy integrity failure')
        if dst.execute('PRAGMA main.foreign_key_check').fetchall():
            raise ValueError('Release work copy foreign-key failure')
        dst.execute('DETACH DATABASE pinned')
        dst.execute('PRAGMA journal_mode=DELETE')
    return counts


def code_identity():
    paths = [Path(__file__), ROOT / 'pipeline/rules/claim_freshness.py',
             ROOT / 'shared/release_population.py', ROOT / 'shared/db.py']
    paths += list((ROOT / 'pipeline/stages').glob('stage_1[234567]*.py'))
    paths += [ROOT / 'pipeline/stages/stage_05_load_database.py']
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


@contextmanager
def settings(module, **values):
    old = {key: getattr(module, key) for key in values}
    try:
        for key, value in values.items():
            setattr(module, key, value)
        yield
    finally:
        for key, value in old.items():
            setattr(module, key, value)


def build(database, output, evidence_dir):
    database, output = Path(database).resolve(strict=True), Path(output).resolve()
    if not database.is_relative_to(TRIALS.resolve()) or database.name != 'trial.db':
        raise ValueError('Requires a marked ingestion trial copy')
    if not output.is_relative_to(TRIALS.resolve()) or output == TRIALS.resolve() or output.exists():
        raise ValueError('Output must be a new directory under incremental_ingestion_trials')
    rules = code_identity()
    protected = {str(p): file_identity(p) for p in protected_paths() +
                 [ROOT / 'database/positioning_radar.db', ROOT / 'database/positioning_radar.db-wal']}
    if database.with_name(database.name + '-wal').exists():
        raise ValueError('Checkpoint the ingestion copy before release construction')
    source_hash = sha256(database)
    with closing(read_connection(database)) as src:
        if src.execute('SELECT COUNT(*) FROM ingestion_copy').fetchone()[0] != 1:
            raise ValueError('Missing copy marker')
        waves = src.execute("SELECT wave_id,contract_json FROM proxy_waves WHERE status='complete'").fetchall()
        batches = src.execute('SELECT payload_json,payload_sha256 FROM incremental_batches').fetchall()
        if len(waves) != 1 or len(batches) != 1:
            raise ValueError('Requires exactly one complete wave and writer batch')
        wave_id, contract_json = waves[0]
        contract = json.loads(contract_json)
        if contract['cutoff_timezone'] != 'Europe/Berlin':
            raise ValueError('Reporting currently requires the approved Europe/Berlin cutoff')
        batch = json.loads(batches[0][0])
        if not batch['batch_id'].startswith('governed:' + wave_id + ':'):
            raise ValueError('Writer batch is not governed for this wave')
        report = json.loads((database.parent / 'governed_processing/REPORT.json').read_text(encoding='utf-8'))
        if report.get('status') != 'complete' or not report.get('writer_connected'):
            raise ValueError('Governed connection report incomplete')
        output.mkdir()
        work = output / 'release_work.db'
        print('Copying governed release state without proxy scan tables...', flush=True)
        copied_counts = release_work_copy(database, work)
    period = contract['cutoff']
    with closing(sqlite3.connect(work)) as conn, conn:
        conn.execute('CREATE TABLE release_manifest (wave_id TEXT PRIMARY KEY, reporting_date TEXT, retrieved_at TEXT, source_sha256 TEXT, status TEXT)')
        conn.execute('INSERT INTO release_manifest VALUES (?,?,?,?,?)', (wave_id, period, contract['retrieved_at'], source_hash, 'building'))
        conn.execute('CREATE TABLE release_population (barcode TEXT PRIMARY KEY)')
        conn.execute('INSERT INTO release_population SELECT barcode FROM retained_display_products')
        for table in SNAPSHOT_TABLES:
            conn.execute('DELETE FROM ' + table)
    print('Checking claim evidence freshness...', flush=True)
    with closing(sqlite3.connect(work)) as conn:
        freshness, evidence_manifest = audit(conn, evidence_dir)
    write_json(output / 'claim_freshness.json', {'counts': freshness, 'evidence_files': evidence_manifest,
        'meaning': 'Matched revision-bearing image reference and text context; image bytes were not downloaded.'})
    print('Rebuilding taxonomy and reporting from the retained display population...', flush=True)
    for number in (12,13,14,15,16):
        path = next((ROOT / 'pipeline/stages').glob(f'stage_{number}_*.py'))
        module = importlib.import_module('pipeline.stages.' + path.stem)
        overrides = {'DB_PATH': work}
        if number == 12:
            overrides['PIPELINE_INTERMEDIATE_DIR'] = output / 'audits'
        if number == 13:
            overrides['SOURCE_SCOPE'] = 'retained_display_population'
        if number in (14,15,16):
            overrides['SNAPSHOT'] = period
        if number == 16:
            overrides['AUDIT_DIR'] = output / 'audits'
        with settings(module, **overrides):
            module.main(reporting_date=period) if number == 13 else module.main()
    with closing(sqlite3.connect(work)) as conn:
        frame = pd.read_sql_query('SELECT * FROM retained_display_products', conn)
        loader.compute_category_region_averages(frame, conn, period)
    public = output / 'release_public.db'
    print('Building separate deployment candidate...', flush=True)
    with closing(sqlite3.connect(work)) as src, closing(sqlite3.connect(public)) as dst:
        dst.execute('ATTACH DATABASE ? AS src', (str(work),))
        for table in sorted(deployment.APP_TABLES):
            deployment.copy_schema(src, dst, table)
        columns = ','.join(deployment.quote_ident(c) for c in deployment.PUBLIC_PRODUCT_COLUMNS)
        dst.execute(f'INSERT INTO products ({columns}) SELECT {columns} FROM src.retained_deployment_products')
        deployment.copy_product_analysis(dst)
        for table in SNAPSHOT_TABLES:
            dst.execute(f'INSERT INTO {table} SELECT * FROM src.{table} WHERE snapshot=?', (period,))
        dst.execute('CREATE TABLE release_population (barcode TEXT PRIMARY KEY)')
        dst.execute('INSERT INTO release_population SELECT barcode FROM src.release_population')
        dst.execute('CREATE TABLE release_manifest AS SELECT * FROM src.release_manifest')
        dst.execute('CREATE TABLE claim_freshness AS SELECT barcode,status FROM src.claim_freshness WHERE barcode IN (SELECT barcode FROM products)')
        deployment.create_indexes(dst)
        dst.commit()
        expected = src.execute('SELECT COUNT(*) FROM retained_deployment_products').fetchone()[0]
        if dst.execute('SELECT COUNT(*) FROM products').fetchone()[0] != expected:
            raise ValueError('Deployment population mismatch')
        if dst.execute('SELECT COUNT(*) FROM release_population WHERE barcode NOT IN (SELECT barcode FROM products)').fetchone()[0]:
            raise ValueError('Display population contains absent products')
        for table in SNAPSHOT_TABLES:
            if dst.execute(f'SELECT COUNT(*) FROM {table} WHERE snapshot<>?', (period,)).fetchone()[0]:
                raise ValueError('Mixed release snapshots')
        if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or dst.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Deployment integrity failure')
        counts = {table: dst.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in sorted(deployment.APP_TABLES)}
        install_population(dst)
        display_count = dst.execute('SELECT COUNT(*) FROM current_product_barcodes').fetchone()[0]
        if display_count != src.execute('SELECT COUNT(*) FROM retained_display_products').fetchone()[0]:
            raise ValueError('App population mismatch')
        for region, category, count in dst.execute('SELECT region_code,category,product_count FROM region_category_benchmarks'):
            expected_count = dst.execute('SELECT COUNT(*) FROM products WHERE barcode IN (SELECT barcode FROM release_population) AND query_category=? AND observed_market_region_codes LIKE ?', (category, '%' + region + '%')).fetchone()[0]
            if count != expected_count:
                raise ValueError('Benchmark population differs from app population')
    print('Verifying working-copy integrity and source preservation...', flush=True)
    with closing(sqlite3.connect(work)) as conn:
        if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Working release integrity failure')
    if sha256(database) != source_hash:
        raise ValueError('Ingestion source changed during build')
    if any(sha256(Path(p)) != digest for p, digest in evidence_manifest.items()):
        raise ValueError('Extraction evidence changed during build')
    if code_identity() != rules:
        raise ValueError('Release code changed during build')
    if any(file_identity(Path(p)) != identity for p, identity in protected.items()):
        raise ValueError('Protected artifact changed during build')
    for path in (work, public):
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute("UPDATE release_manifest SET status='complete'")
    with public.open('rb') as src, gzip.open(public.with_suffix('.db.gz'), 'wb') as dst:
        shutil.copyfileobj(src, dst)
    manifest = dict(status='complete', wave_id=wave_id, reporting_date=period, retrieved_at=contract['retrieved_at'],
        source_sha256=source_hash, counts=counts, claim_freshness=freshness,
        release_work_copy={'included_table_counts': copied_counts, 'omitted_staging_tables': sorted(STAGING_ONLY_TABLES)},
        display_count=display_count, code_sha256=rules, protected_files_unchanged=protected,
        public_sha256=sha256(public), gzip_sha256=sha256(public.with_suffix('.db.gz')),
        limitations=['Proxy cutoff selects eligible records using retrieval-time source values; it does not reconstruct cutoff-date values.',
                     'No paid OCR/LLM in this release build.', 'Image-reference matching does not verify image bytes.',
                     'Release candidate only; not deployed.'])
    write_json(output / 'manifest.json', manifest)
    (output / 'REPORT.md').write_text('# Incremental release validation\n\n'
        + 'Completed on a separate copy; source ingestion state preserved.\n\n'
        + f'Reporting cutoff: {period}. Wave: {wave_id}.\n\n'
        + 'The release work copy omits proxy scan tables; full scan evidence remains in the unchanged ingestion source.\n'
        + 'Taxonomy, summaries, averages, benchmarks, intersections and chart ranges rebuilt.\n'
        + 'Deployment candidate uses retained membership and one reporting snapshot.\n'
        + 'Integrity, foreign keys and source/evidence preservation passed.\n\n'
        + 'Claim freshness counts: `' + json.dumps(freshness, sort_keys=True) + '`.\n'
        + 'Original claim observations remain in claim_freshness.prior_analysis_json and the unchanged source.\n'
        + 'No production update, deployment or OCR/LLM run.\n', encoding='utf-8')
    print('COMPLETE: ' + str(output), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, default=ROOT / 'data/05_vision_release')
    args = parser.parse_args()
    build(args.database, args.output, args.evidence_dir)
