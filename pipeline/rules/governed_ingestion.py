"""Connect a complete proxy wave to governed processing and the copy-only writer.

No auto-latest input discovery, global audit exports, API calls or aggregate
rebuilds. Staged raw observations are immutable evidence. Held observations
are explicitly inventoried, never silently admitted or deleted.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

import pandas as pd

from pipeline.rules import incremental_ingestion as writer
from pipeline.rules import proxy_wave
from pipeline.stages import stage_01a_bootstrap_from_off_bulk as bulk
from pipeline.stages import stage_02_clean_products as cleaning
from pipeline.stages import stage_03_build_nutrition_quality_flags as quality
from pipeline.stages import stage_04_build_product_analysis as analysis
from pipeline.stages import stage_05_load_database as loader
from pipeline.maintenance.capture_database_baseline import sha256, read_connection, write_json

ROOT = writer.ROOT
PROCESS = {'process_retained_update', 'process_retained_scope_exit',
           'process_new_candidate', 'process_reviewed_reentry'}
ANALYSIS_FIELDS = [
    'processing_marker_count', 'processing_markers_found', 'processing_marker_max_severity',
    'has_processing_markers', 'e_number_count', 'e_numbers_found', 'has_artificial_sweetener',
    'composition_marker_score', 'composition_marker_band', 'ingredient_based_claim_signal_count',
    'ingredient_based_claim_signals_found', 'absence_reduction_claim_count', 'absence_reduction_claims_found',
    'sugar_positioning_intersection_flag', 'protein_fat_intersection_flag',
    'fibre_sugar_processing_intersection_flag', 'plant_based_nutrition_intersection_flag',
]
PEER_FIELDS = ['barcode', 'primary_brand', 'query_category', 'observed_market_region_codes',
               'include_in_product_table', *cleaning.NUTRIMENT_COLS, *cleaning.RAW_NUTRIMENT_COLS.values()]


def fingerprint(value):
    # json.dumps builds a second, multi-gigabyte string for real OFF waves.
    # iterencode emits the same canonical bytes without that allocation.
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False,
                               separators=(',', ':'))
    _update_json(digest, encoder, value)
    return digest.hexdigest()


def _update_json(digest, encoder, value):
    for chunk in encoder.iterencode(value):
        digest.update(chunk.encode('utf-8'))


def rule_identity():
    paths = [Path(__file__), Path(writer.__file__), Path(cleaning.__file__), Path(quality.__file__),
             Path(analysis.__file__), Path(loader.__file__), Path(bulk.__file__),
             ROOT / 'shared/beverage_segments.py', ROOT / 'pipeline/rules/category_rules.py']
    paths += sorted((ROOT / 'data/01_reference_inputs').glob('*.csv'))
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def staged_identity(conn, wave_id):
    wave = conn.execute('SELECT contract_json,status,scanned_rows FROM proxy_waves WHERE wave_id=?', (wave_id,)).fetchone()
    if wave is None or wave[1] != 'complete':
        raise ValueError('A completed proxy wave is required')
    contract = json.loads(wave[0])
    if contract['rule_sha256'] != sha256(Path(proxy_wave.__file__)) or contract['category_rule_sha256'] != sha256(ROOT / 'pipeline/rules/category_rules.py'):
        raise ValueError('Staging rules changed; restage on a fresh copy')
    # Preserve the original canonical [wave, rows, conflicts] identity without
    # retaining gigabytes of raw JSON in a Python list.
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False,
                               separators=(',', ':'))
    digest.update(b'[')
    _update_json(digest, encoder, wave)
    digest.update(b',[')
    observations = conn.execute('SELECT barcode,raw_json,decision,category_candidate,membership_before,source_modified_utc,review_reference '
                                'FROM proxy_observations WHERE wave_id=? ORDER BY barcode', (wave_id,))
    for index, row in enumerate(observations):
        saved = conn.execute('SELECT source_sha256 FROM proxy_seen WHERE wave_id=? AND barcode=?', (wave_id, row[0])).fetchone()
        if saved != (hashlib.sha256(row[1].encode('utf-8')).hexdigest(),):
            raise ValueError('Staged raw evidence differs from its scan identity')
        if index:
            digest.update(b',')
        _update_json(digest, encoder, row)
    digest.update(b'],[')
    conflicts = conn.execute('SELECT barcode,source_row,first_source_sha256,conflicting_sha256,raw_json '
                             'FROM proxy_conflicts WHERE wave_id=? ORDER BY source_row', (wave_id,))
    for index, row in enumerate(conflicts):
        barcode, source_row, first_hash, conflicting_hash, raw_json = row
        if (conn.execute('SELECT source_sha256 FROM proxy_seen WHERE wave_id=? AND barcode=?',
                         (wave_id, barcode)).fetchone() != (first_hash,) or
                hashlib.sha256(raw_json.encode('utf-8')).hexdigest() != conflicting_hash):
            raise ValueError('Conflicting source evidence differs from its scan identity')
        if index:
            digest.update(b',')
        _update_json(digest, encoder, row)
    digest.update(b']]')
    return digest.hexdigest(), contract


def peer_snapshot(conn):
    columns = ','.join('"' + c + '"' for c in PEER_FIELDS)
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False,
                               separators=(',', ':'))
    digest.update(b'[')
    for index, row in enumerate(conn.execute(f'SELECT {columns} FROM retained_products ORDER BY barcode')):
        if index:
            digest.update(b',')
        _update_json(digest, encoder, row)
    digest.update(b']')
    return digest.hexdigest()


def relevant_peers(database, cleaned):
    columns = ','.join('"' + c + '"' for c in PEER_FIELDS)
    brands = set(cleaned['primary_brand'].map(quality.normalize_key))
    categories = set(cleaned['query_category'])
    incoming = set(cleaned['barcode'])
    selected = []
    with closing(read_connection(database)) as conn:
        for chunk in pd.read_sql_query(f'SELECT {columns} FROM retained_products ORDER BY barcode',
                                       conn, chunksize=5000):
            matches = chunk['primary_brand'].map(quality.normalize_key).isin(brands)
            matches &= chunk['query_category'].isin(categories) & ~chunk['barcode'].isin(incoming)
            if matches.any():
                selected.append(chunk.loc[matches])
    return pd.concat(selected, ignore_index=True) if selected else pd.DataFrame(columns=PEER_FIELDS)


def scalar(value, kind):
    if value is None or pd.isna(value):
        return None
    if kind == 'TEXT':
        return value.isoformat() if isinstance(value, pd.Timestamp) else str(value)
    if kind == 'INTEGER':
        if float(value) != int(value):
            raise ValueError('Non-integral value in an integer output field')
        return int(value)
    return float(value)


def prepare(database, wave_id):
    """Build an explicit, replayable processing bundle without database writes."""
    database = Path(database).resolve(strict=True)
    if not database.is_relative_to(writer.TRIALS.resolve()) or database.name != 'trial.db':
        raise ValueError('Only a copy-only trial database is allowed')
    rules = rule_identity()
    with closing(read_connection(database)) as conn:
        stage_hash, contract = staged_identity(conn, wave_id)
        context_hash = peer_snapshot(conn)
        schema = {table: {r[1]: r[2] for r in conn.execute(f'PRAGMA table_info({table})')}
                  for table in ('products', 'product_analysis')}
        existing_batches = conn.execute('SELECT COUNT(*) FROM incremental_batches').fetchone()[0]
        if existing_batches:
            raise ValueError('Prepare on a fresh staged copy; replay uses its saved bundle')
    holds, raw_brands, rows, reviews, membership_by_code, staged_decisions = {}, {}, [], {}, {}, {}
    regions = cleaning.load_region_mapping()
    with closing(read_connection(database)) as conn:
        observations = conn.execute('SELECT barcode,raw_json,decision,category_candidate,membership_before,source_modified_utc,review_reference '
                                    'FROM proxy_observations WHERE wave_id=? ORDER BY barcode', (wave_id,))
        for barcode, payload, decision, category, membership, modified, review in observations:
            staged_decisions[barcode] = decision
            if decision not in PROCESS:
                continue
            raw = json.loads(payload)
            if not bulk.ALL_NEEDED.issubset(raw):
                holds[barcode] = 'missing_source_columns:' + ','.join(sorted(bulk.ALL_NEEDED - raw.keys()))
                continue
            if not raw['product_name'].strip() and not raw['ingredients_text'].strip():
                holds[barcode] = 'no_product_name_or_ingredients'
                continue
            row = {target: raw[source] for source, target in bulk.COL_MAP.items()}
            row.update({target: bulk.comma_to_pipe(raw[source]) for source, target in bulk.TAG_COL_MAP.items()})
            row['query_category'] = category  # None represents a source category exit.
            row['observed_market_region_codes'] = cleaning.derive_region_codes(row['countries'], regions)
            for field in ('created_t', 'last_modified_t'):
                try:
                    row[field] = int(proxy_wave.epoch(raw[field]).timestamp())
                except ValueError:
                    row[field] = None
            row['nova_group'] = pd.to_numeric(row['nova_group'], errors='coerce')
            rows.append(row)
            raw_brands[barcode] = raw['brands']
            membership_by_code[barcode] = membership
            if review:
                reviews[barcode] = review
    records = []
    if rows:
        frame = pd.DataFrame(rows)
        del rows
        # These are derived transforms only; their default CLI behavior is untouched.
        cleaned = cleaning.clean(input_frame=frame, peer_warnings=False)
        if set(cleaned['barcode']) != set(raw_brands) or cleaned['barcode'].duplicated().any():
            raise ValueError('Cleaning lost or duplicated explicit staged identifiers')
        cleaned = loader.add_resolved_company_column(cleaned)
        final_scope = cleaned['query_category'].isin(['snacks', 'cereals', 'dairies', 'beverages']) & cleaned['observed_market_region_codes'].fillna('').map(
            lambda value: bool(set(value.split('|')) & {'FRANCE', 'UK_IE', 'US_CANADA'}))
        retained = cleaned['barcode'].map(membership_by_code).eq('retained')
        for barcode in cleaned.loc[~final_scope & ~retained, 'barcode']:
            holds[barcode] = 'outside_final_governed_scope'
        cleaned = cleaned[final_scope | retained].copy().reset_index(drop=True)
        if len(cleaned):
            # Stream the baseline and retain only the complete peer groups
            # needed by the incoming products.
            peers = relevant_peers(database, cleaned)
            flagged = quality.build_nutrition_quality_flags(cleaned, peer_context=peers)
            eligible = flagged['ingredient_analysis_eligible'].eq(True)
            # Stage 04's empty-eligible path assumes a nonempty denominator.
            # Analyze the eligible subset and explicitly clear obsolete ingredient
            # outputs for ineligible records, without touching pack observations.
            analyzed = analysis.analyze(input_frame=flagged[eligible].copy()) if eligible.any() else pd.DataFrame()
            outputs = {row['barcode']: row for _, row in analyzed.iterrows()}
            for _, product_row in flagged.iterrows():
                barcode = product_row['barcode']
                product_row = product_row.copy()
                product_row['off_brands_raw'] = raw_brands[barcode]
                missing = set(loader.PRODUCT_COLS) - set(product_row.index)
                if missing:
                    raise ValueError(f'Missing processed product fields: {sorted(missing)}')
                product = {k: scalar(product_row[k], schema['products'][k]) for k in loader.PRODUCT_COLS if k != 'barcode'}
                result = outputs.get(barcode)
                derived = {k: scalar(result[k], schema['product_analysis'][k]) if result is not None else None
                           for k in ANALYSIS_FIELDS}
                records.append(dict(barcode=barcode, product=product, analysis=derived))
    records.sort(key=lambda r: r['barcode'])
    ids = {r['barcode'] for r in records}
    reviews = {k: v for k, v in reviews.items() if k in ids}
    identity = fingerprint(dict(wave_id=wave_id, staged=stage_hash, peers=context_hash, rules=rules))
    batch = dict(batch_id=f'governed:{wave_id}:{identity[:16]}', retrieved_at=contract['retrieved_at'],
                 source_reference=f'proxy:{wave_id}:{stage_hash}', processing_reference=f'governed:{identity}',
                 completeness=dict(complete=True, record_count=len(records), reference=f'proxy-complete:{stage_hash};holds:{fingerprint(holds)}'),
                 records=records, reviewed_reentries=reviews)
    if rule_identity() != rules:
        raise ValueError('Processing rules/reference inputs changed during preparation')
    return dict(wave_id=wave_id, stage_sha256=stage_hash, context_sha256=context_hash,
                rule_sha256=rules, holds=holds, staged_decisions=staged_decisions,
                batch=batch, batch_sha256=fingerprint(batch),
                limitations=['Pack fields are preserved, not certified fresh.',
                             'Peer context informs incoming warnings; unchanged peers are not rewritten.',
                             'No downstream aggregate or deployment rebuild.'])


def connect(database, wave_id):
    """Prepare once, persist evidence, then apply/replay one atomic writer batch."""
    database = Path(database).resolve(strict=True)
    if not database.is_relative_to(writer.TRIALS.resolve()) or database.name != 'trial.db':
        raise ValueError('Only a copy-only trial database is allowed')
    output = database.parent / 'governed_processing'
    output.mkdir(exist_ok=True)
    prepared = output / 'prepared.json'
    if prepared.exists():
        bundle = json.loads(prepared.read_text(encoding='utf-8'))
    else:
        bundle = prepare(database, wave_id)
        write_json(prepared, bundle)
    if bundle['wave_id'] != wave_id or bundle['batch_sha256'] != fingerprint(bundle['batch']):
        raise ValueError('Prepared bundle identity mismatch')
    if rule_identity() != bundle['rule_sha256']:
        raise ValueError('Processing rules/references changed; use a fresh copy')
    with closing(read_connection(database)) as conn:
        if staged_identity(conn, wave_id)[0] != bundle['stage_sha256']:
            raise ValueError('Staged evidence changed after preparation')
    def validate(conn):
        if (staged_identity(conn, wave_id)[0] != bundle['stage_sha256'] or
                peer_snapshot(conn) != bundle['context_sha256'] or rule_identity() != bundle['rule_sha256']):
            raise ValueError('Source, retained context or rules changed before commit')
    result = writer.apply_batch(database, bundle['batch'], validate_context=validate)
    report = dict(status='complete', writer_connected=True, result=result,
                  accepted=len(bundle['batch']['records']), holds=bundle['holds'],
                  prepared_sha256=sha256(prepared), limitations=bundle['limitations'])
    # A failed/interrupted report write is recoverable by exact writer replay.
    report_path = output / 'REPORT.json'
    if not report_path.exists():
        write_json(report_path, report)
    return report
