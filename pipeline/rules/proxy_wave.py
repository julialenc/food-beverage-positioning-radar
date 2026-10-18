"""Stage pinned OFF evidence and proxy admission decisions on an ingestion copy.

Does not write products, analysis or membership. Complete means the pinned
export was fully scanned, not that OFF represents the whole retail market.
"""
from contextlib import closing
import csv
from datetime import date, datetime, time, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from pipeline.rules import incremental_ingestion as writer
from pipeline.rules.category_rules import assign_category, matches_country
from pipeline.maintenance.capture_database_baseline import sha256

REQUIRED = {'code', 'product_name', 'categories_tags', 'countries_tags', 'created_t', 'last_modified_t'}
DDL = (
    """CREATE TABLE IF NOT EXISTS proxy_waves (
        wave_id TEXT PRIMARY KEY, contract_json TEXT NOT NULL, status TEXT NOT NULL,
        scanned_rows INTEGER NOT NULL DEFAULT 0, error TEXT)""",
    """CREATE TABLE IF NOT EXISTS proxy_seen (
        wave_id TEXT NOT NULL REFERENCES proxy_waves(wave_id), barcode TEXT NOT NULL,
        source_sha256 TEXT NOT NULL, PRIMARY KEY(wave_id,barcode))""",
    """CREATE TABLE IF NOT EXISTS proxy_observations (
        wave_id TEXT NOT NULL REFERENCES proxy_waves(wave_id), barcode TEXT NOT NULL,
        raw_json TEXT NOT NULL, decision TEXT NOT NULL, category_candidate TEXT,
        membership_before TEXT, source_modified_utc TEXT, review_reference TEXT,
        PRIMARY KEY(wave_id,barcode))""",
    """CREATE TABLE IF NOT EXISTS proxy_conflicts (
        wave_id TEXT NOT NULL REFERENCES proxy_waves(wave_id), barcode TEXT NOT NULL,
        source_row INTEGER NOT NULL, first_source_sha256 TEXT NOT NULL,
        conflicting_sha256 TEXT NOT NULL, raw_json TEXT NOT NULL,
        PRIMARY KEY(wave_id,source_row))""",
)


def epoch(value):
    # Keep raw input elsewhere; no empty/NULL/zero coercion or float rounding.
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError('Missing or invalid OFF timestamp')
    if int(value) <= 0:
        raise ValueError('Missing or invalid OFF timestamp')
    try:
        return datetime.fromtimestamp(int(value), timezone.utc)
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError('Out-of-range OFF timestamp') from exc


def cutoff_end(cutoff, timezone_name):
    return datetime.combine(date.fromisoformat(cutoff) + timedelta(days=1), time(),
                            ZoneInfo(timezone_name)).astimezone(timezone.utc)


def decide(raw, membership, prior_revision, retrieved_at, end, review=None):
    category = assign_category(raw['categories_tags'], raw['product_name'])
    in_scope = matches_country(raw['countries_tags']) and category is not None
    if membership is None and not in_scope:
        return 'outside_candidate_scope', category, None
    if membership == 'archived' and not review:
        return 'hold_archived_reentry', category, None
    if membership != 'retained':
        try:
            created = epoch(raw['created_t'])
        except ValueError:
            return 'hold_creation_unknown', category, None
        if created >= end:
            return 'exclude_after_cutoff', category, None
    try:
        modified = epoch(raw['last_modified_t'])
    except ValueError:
        return 'hold_revision_unknown', category, None
    if modified > retrieved_at:
        return 'hold_revision_after_retrieval', category, modified.isoformat()
    if membership is not None:
        try:
            previous = writer.revision(prior_revision)
        except ValueError:
            return 'hold_baseline_revision_unknown', category, modified.isoformat()
        if modified < previous:
            return 'hold_stale_revision', category, modified.isoformat()
        if modified == previous and membership == 'retained':
            return 'carry_forward_equal_revision', category, modified.isoformat()
    if membership == 'retained':
        return ('process_retained_update' if in_scope else 'process_retained_scope_exit'), category, modified.isoformat()
    if membership == 'archived':
        return 'process_reviewed_reentry', category, modified.isoformat()
    return 'process_new_candidate', category, modified.isoformat()


def _guard(action, table, column, database, trigger):
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        if table not in {'proxy_waves', 'proxy_seen', 'proxy_observations',
                         'proxy_conflicts', 'sqlite_master'}:
            return sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_ALTER_TABLE):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def stage(database, snapshot_dir, *, wave_id, cutoff='2026-09-29', cutoff_timezone='Europe/Berlin',
          reviewed_reentries=None, checkpoint_size=5000):
    database, snapshot_dir = Path(database).resolve(strict=True), Path(snapshot_dir).resolve(strict=True)
    if not database.is_relative_to(writer.TRIALS.resolve()) or database.name != 'trial.db':
        raise ValueError('Only copy-only trial.db destinations are allowed')
    if not isinstance(wave_id, str) or not wave_id.strip():
        raise ValueError('Nonempty wave ID required')
    if type(checkpoint_size) is not int or checkpoint_size < 1:
        raise ValueError('Positive checkpoint size required')
    reviews = reviewed_reentries or {}
    if not isinstance(reviews, dict) or any(not isinstance(k, str) or not k or
            not isinstance(v, str) or not v.strip() for k, v in reviews.items()):
        raise ValueError('Explicit review references required')
    manifest_path = snapshot_dir / 'manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get('status') != 'complete' or manifest.get('format') != 'off-tsv-gzip-v1' or manifest.get('file') != 'source.csv.gz':
        raise ValueError('Requires a completed pinned OFF TSV snapshot')
    source = snapshot_dir / 'source.csv.gz'
    if source.stat().st_size != manifest['bytes'] or sha256(source) != manifest['sha256']:
        raise ValueError('Source checksum/length changed')
    retrieved = writer.revision(manifest['retrieval_finished_at'])
    if writer.revision(manifest['retrieval_started_at']) > retrieved:
        raise ValueError('Retrieval chronology is invalid')
    end = cutoff_end(cutoff, cutoff_timezone)
    if end > retrieved:
        raise ValueError('Proxy cutoff must precede retrieval')
    contract = writer.canonical(dict(source_sha256=manifest['sha256'],
        snapshot_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        retrieved_at=manifest['retrieval_finished_at'], cutoff=cutoff,
        cutoff_timezone=cutoff_timezone, exclusive_cutoff_utc=end.isoformat(),
        reviewed_reentries=reviews, rule_sha256=sha256(Path(__file__)),
        category_rule_sha256=sha256(Path(__file__).with_name('category_rules.py'))))
    # A large text field must not silently truncate or abort at csv's small default.
    csv.field_size_limit(64 * 1024 * 1024)
    with closing(sqlite3.connect(database)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        if conn.execute('SELECT COUNT(*) FROM ingestion_copy').fetchone()[0] != 1:
            raise ValueError('Missing copy-only marker')
        if conn.execute('SELECT COUNT(*) FROM incremental_batches').fetchone()[0]:
            raise ValueError('Stage onto a fresh copy before applying writer batches')
        for barcode in reviews:
            if conn.execute('SELECT membership FROM population_membership WHERE barcode=?', (barcode,)).fetchone() != ('archived',):
                raise ValueError('Re-entry review must identify an archived product on this copy')
        conn.set_authorizer(_guard)
        for sql in DDL:
            conn.execute(sql)
        conn.commit()
        other = conn.execute('SELECT wave_id FROM proxy_waves WHERE wave_id<>?', (wave_id,)).fetchone()
        if other:
            raise ValueError('One proxy wave per fresh copy; create another copy')
        row = conn.execute('SELECT contract_json,status,scanned_rows FROM proxy_waves WHERE wave_id=?', (wave_id,)).fetchone()
        if row and row[0] != contract:
            raise ValueError('Wave/source/cutoff/rules changed; use a fresh copy')
        if row and row[1] == 'complete':
            return summary(conn, wave_id)
        resume_row = row[2] if row else 0
        conn.execute("INSERT INTO proxy_waves (wave_id,contract_json,status) VALUES (?,?,'scanning') "
                     "ON CONFLICT(wave_id) DO UPDATE SET status='scanning',error=NULL", (wave_id, contract))
        conn.commit()
        try:
            with gzip.open(source, 'rt', encoding='utf-8-sig', newline='') as stream:
                # OFF's TSV fields contain literal quotation marks (for example
                # a product name starting with '"mezzelune"'). They are not CSV
                # quoting syntax; tabs alone delimit the source columns.
                reader = csv.DictReader(stream, delimiter='\t', quotechar=None,
                                        quoting=csv.QUOTE_NONE, strict=True)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not REQUIRED.issubset(reader.fieldnames):
                    raise ValueError('Missing/duplicate OFF source columns')
                scanned = 0
                for scanned, raw in enumerate(reader, 1):
                    if scanned <= resume_row:
                        continue
                    if None in raw or any(v is None for v in raw.values()):
                        raise ValueError('Malformed TSV row')
                    barcode = raw['code']
                    if not barcode or barcode != barcode.strip():
                        raise ValueError('Missing/padded source barcode')
                    raw_json = writer.canonical(raw)
                    identity = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()
                    duplicate = conn.execute('SELECT source_sha256 FROM proxy_seen WHERE wave_id=? AND barcode=?', (wave_id, barcode)).fetchone()
                    if duplicate:
                        if duplicate[0] != identity:
                            # No arbitrary winner: preserve the conflicting raw
                            # row and prevent a previously staged first row
                            # from becoming an eligible writer observation.
                            conn.execute('INSERT INTO proxy_conflicts VALUES (?,?,?,?,?,?)',
                                         (wave_id, barcode, scanned, duplicate[0], identity, raw_json))
                            conn.execute("UPDATE proxy_observations SET decision='hold_conflicting_source_duplicates' "
                                         'WHERE wave_id=? AND barcode=?', (wave_id, barcode))
                    else:
                        conn.execute('INSERT INTO proxy_seen VALUES (?,?,?)', (wave_id, barcode, identity))
                        existing = conn.execute('SELECT m.membership,p.last_modified_t FROM products p '
                            'LEFT JOIN population_membership m USING(barcode) WHERE p.barcode=?', (barcode,)).fetchone()
                        if existing and existing[0] is None:
                            raise ValueError('Product lacks population membership')
                        membership, previous = existing if existing else (None, None)
                        decision, category, modified = decide(raw, membership, previous, retrieved, end, reviews.get(barcode))
                        if decision != 'outside_candidate_scope':
                            conn.execute('INSERT INTO proxy_observations VALUES (?,?,?,?,?,?,?,?)',
                                (wave_id, barcode, raw_json, decision, category, membership, modified, reviews.get(barcode)))
                    if scanned % checkpoint_size == 0:
                        conn.execute('UPDATE proxy_waves SET scanned_rows=? WHERE wave_id=?', (scanned, wave_id))
                        conn.commit()
                if scanned < resume_row:
                    raise ValueError('Checkpoint exceeds source length')
                if scanned == 0:
                    raise ValueError('Empty bulk export cannot establish a complete collection')
            if sha256(source) != manifest['sha256'] or manifest_path.read_bytes() != manifest_bytes:
                raise ValueError('Source evidence changed during scan')
            conn.execute("UPDATE proxy_waves SET status='complete',scanned_rows=?,error=NULL WHERE wave_id=?", (scanned, wave_id))
            conn.commit()
            return summary(conn, wave_id)
        except BaseException as exc:
            conn.rollback()
            conn.execute("UPDATE proxy_waves SET status='incomplete',error=? WHERE wave_id=?", (str(exc), wave_id))
            conn.commit()
            raise


def summary(conn, wave_id):
    status, scanned, contract = conn.execute('SELECT status,scanned_rows,contract_json FROM proxy_waves WHERE wave_id=?', (wave_id,)).fetchone()
    counts = dict(conn.execute('SELECT decision,COUNT(*) FROM proxy_observations WHERE wave_id=? GROUP BY decision', (wave_id,)))
    return dict(status=status, scanned_rows=scanned, unique_source_records=conn.execute(
        'SELECT COUNT(*) FROM proxy_seen WHERE wave_id=?', (wave_id,)).fetchone()[0],
        decisions=counts, source_conflict_barcodes=conn.execute(
            'SELECT COUNT(DISTINCT barcode) FROM proxy_conflicts WHERE wave_id=?', (wave_id,)).fetchone()[0],
        source_conflict_rows=conn.execute(
            'SELECT COUNT(*) FROM proxy_conflicts WHERE wave_id=?', (wave_id,)).fetchone()[0],
        contract=json.loads(contract), writer_connected=False)
