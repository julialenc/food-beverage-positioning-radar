"""Copy-only transactional processed-batch ingestion; not a production loader.

No retrieval, cutoff filtering, governance derivation or claim refresh occurs.
Callers supply reviewed/processed fields and completeness evidence. This module
checks the contract, not the truth of an upstream completeness assertion.
"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from pipeline.rules import population_policy as policy
from pipeline.maintenance.capture_database_baseline import backup_database, sha256

ROOT = Path(__file__).resolve().parents[2]
TRIALS = ROOT / 'data/06_brand_governance_outputs/incremental_ingestion_trials'
DDL = (
    "CREATE TABLE ingestion_copy (id INTEGER PRIMARY KEY CHECK(id=1), source_sha256 TEXT NOT NULL)",
    """CREATE TABLE incremental_batches (
        batch_id TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL,
        payload_json TEXT NOT NULL, completed_at TEXT NOT NULL)""",
    """CREATE TABLE incremental_history (
        batch_id TEXT NOT NULL REFERENCES incremental_batches(batch_id),
        barcode TEXT NOT NULL, before_product TEXT, after_product TEXT NOT NULL,
        before_analysis TEXT, after_analysis TEXT, PRIMARY KEY(batch_id,barcode))""",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':'))


def revision(value):
    # Legacy cleaned OFF timestamps are UTC without a timezone suffix.
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Source revision must be a nonempty ISO datetime')
    if 'T' not in value and ' ' not in value:
        raise ValueError('Source revision requires time of day')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def create_copy(source_dir, output_dir):
    """Create a new guarded copy from a checksum-verified completed policy trial."""
    source_dir, output_dir = Path(source_dir).resolve(), Path(output_dir).resolve()
    if not output_dir.is_relative_to(TRIALS.resolve()) or output_dir == TRIALS.resolve():
        raise ValueError('Output must be a new directory inside incremental_ingestion_trials')
    manifest = json.loads((source_dir / 'manifest.json').read_text(encoding='utf-8'))
    source = source_dir / 'trial.db'
    if manifest.get('status') != 'complete' or sha256(source) != manifest['trial_database']['sha256']:
        raise ValueError('Requires an unchanged completed population-policy trial')
    output_dir.mkdir(parents=True, exist_ok=False)
    target = output_dir / 'trial.db'
    backup_database(source, target)
    with closing(sqlite3.connect(target)) as conn:
        if conn.execute('SELECT policy_version FROM population_policy').fetchone() != (policy.POLICY_VERSION,):
            raise ValueError('Unsupported population policy')
        with policy.atomic(conn):
            for sql in DDL:
                conn.execute(sql)
            conn.execute('INSERT INTO ingestion_copy VALUES (1,?)', (manifest['trial_database']['sha256'],))
    if sha256(source) != manifest['trial_database']['sha256']:
        raise ValueError('Source trial changed during copy')
    return target


def _row(conn, table, barcode):
    cursor = conn.execute(f'SELECT * FROM {table} WHERE barcode=?', (barcode,))
    row = cursor.fetchone()
    return dict(zip([c[0] for c in cursor.description], row)) if row is not None else None


def _fields(conn, table, values, excluded):
    if not isinstance(values, dict):
        raise ValueError('Fields must be an object')
    columns = {r[1]: r[2].upper() for r in conn.execute(f'PRAGMA table_info({table})')}
    if set(values) - (columns.keys() - set(excluded)):
        raise ValueError(f'Unknown or loader-owned {table} field')
    for key, value in values.items():
        if value is None:
            continue
        kind = columns[key]
        if kind == 'TEXT' and not isinstance(value, str):
            raise ValueError(f'{key} must be text or NULL')
        if kind == 'INTEGER' and type(value) is not int:
            raise ValueError(f'{key} must be integer or NULL')
        if kind == 'REAL' and type(value) not in (int, float):
            raise ValueError(f'{key} must be numeric or NULL')
    canonical(values)  # rejects non-finite numbers and non-JSON values
    return set(columns) - set(excluded)


def _write(conn, table, barcode, values, timestamp_field, timestamp):
    if not values:
        return
    fields = {**values, timestamp_field: timestamp}
    names = list(fields)
    quoted = ','.join('"' + name + '"' for name in names)
    updates = ','.join(f'"{name}"=excluded."{name}"' for name in names)
    conn.execute(f'INSERT INTO {table} (barcode,{quoted}) VALUES ({",".join("?" for _ in range(len(names)+1))}) '
                 f'ON CONFLICT(barcode) DO UPDATE SET {updates}', [barcode, *fields.values()])


def apply_batch(database, batch, *, validate_context=None):
    """Apply one explicit JSON-shaped processed batch to a marked trial copy.

    Absent fields preserve values; explicit NULL clears them; zero stays zero.
    New products require every product field, with explicit NULLs where missing.
    Equal source revisions allow only unchanged supplied product/analysis values.
    Unknown baseline revisions fail closed. Whole-batch replay is an exact no-op.
    """
    database = Path(database).resolve(strict=True)
    if not database.is_relative_to(TRIALS.resolve()) or database.name != 'trial.db':
        raise ValueError('Only trial.db inside incremental_ingestion_trials is writable')
    required = {'batch_id', 'retrieved_at', 'source_reference', 'processing_reference',
                'completeness', 'records', 'reviewed_reentries'}
    if not isinstance(batch, dict) or set(batch) != required:
        raise ValueError('Batch fields differ from the explicit input contract')
    for key in ('batch_id', 'source_reference', 'processing_reference'):
        if not isinstance(batch[key], str) or not batch[key].strip():
            raise ValueError(f'{key} must be nonempty text')
    retrieved = revision(batch['retrieved_at'])
    evidence = batch['completeness']
    if (not isinstance(evidence, dict) or set(evidence) != {'complete', 'record_count', 'reference'}
            or evidence['complete'] is not True or type(evidence['record_count']) is not int
            or not isinstance(evidence['reference'], str) or not evidence['reference'].strip()
            or not isinstance(batch['records'], list)
            or evidence['record_count'] != len(batch['records'])):
        raise ValueError('Incomplete batch or inconsistent completeness evidence')
    if not isinstance(batch['reviewed_reentries'], dict):
        raise ValueError('reviewed_reentries must be an object')
    payload = canonical(batch)
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    with closing(sqlite3.connect(database)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        if conn.execute('SELECT COUNT(*) FROM ingestion_copy').fetchone()[0] != 1:
            raise ValueError('Missing copy-only marker')
        conn.execute('BEGIN IMMEDIATE')
        try:
            prior = conn.execute('SELECT payload_sha256 FROM incremental_batches WHERE batch_id=?',
                                 (batch['batch_id'],)).fetchone()
            if prior:
                if prior[0] != digest:
                    raise ValueError('Batch ID reused with different content')
                conn.rollback()
                return {'status': 'replayed', 'changed': 0}
            if validate_context is not None:
                # Validate a governed adapter's source/context while this
                # transaction holds the write lock, before any product writes.
                validate_context(conn)
            records = batch['records']
            if any(not isinstance(r, dict) or set(r) != {'barcode', 'product', 'analysis'} for r in records):
                raise ValueError('Each record requires barcode, product and analysis objects')
            ids = policy.preflight_batch(conn, [r['barcode'] for r in records], batch['reviewed_reentries'])
            planned = []
            for record in records:
                barcode, product, analysis = record['barcode'], record['product'], record['analysis']
                columns = _fields(conn, 'products', product, {'barcode', 'ingested_at'})
                _fields(conn, 'product_analysis', analysis, {'barcode', 'analyzed_at'})
                incoming = revision(product.get('last_modified_t'))
                if incoming > retrieved:
                    raise ValueError('Source revision is later than retrieval')
                before = _row(conn, 'products', barcode)
                before_analysis = _row(conn, 'product_analysis', barcode)
                if before is None and set(product) != columns:
                    raise ValueError('New products require all processed product fields')
                changed = before is None or any(before[k] != v for k, v in product.items())
                changed = changed or bool(analysis) and (before_analysis is None or any(before_analysis[k] != v for k, v in analysis.items()))
                if before is not None:
                    previous = revision(before['last_modified_t'])
                    if incoming < previous or incoming == previous and changed:
                        raise ValueError('Stale or conflicting equal source revision')
                planned.append((record, before, before_analysis, changed))
            # All validation precedes writes; history, upserts and membership are atomic.
            timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute('INSERT INTO incremental_batches VALUES (?,?,?,?)',
                         (batch['batch_id'], digest, payload, timestamp))
            changed_count = 0
            for record, before, before_analysis, changed in planned:
                if not changed:
                    continue
                barcode = record['barcode']
                _write(conn, 'products', barcode, record['product'], 'ingested_at', timestamp)
                _write(conn, 'product_analysis', barcode, record['analysis'], 'analyzed_at', timestamp)
                conn.execute('INSERT INTO incremental_history VALUES (?,?,?,?,?,?)', (
                    batch['batch_id'], barcode, canonical(before),
                    canonical(_row(conn, 'products', barcode)), canonical(before_analysis),
                    canonical(_row(conn, 'product_analysis', barcode))))
                changed_count += 1
            policy.record_accepted_batch(conn, ids, batch_id=batch['batch_id'],
                                         reviewed_reentries=batch['reviewed_reentries'])
            conn.commit()
            return {'status': 'completed', 'changed': changed_count}
        except BaseException:
            conn.rollback()
            raise
