"""Bounded startup history check; no images, providers or database scans."""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.vision_ops.run_06b_execution_guard import stable_hash


def refresh(root, rows, manifest_sha, config_sha, receipt_path, reconciliation=None):
    from pipeline.vision_ops.run_06b_runner import sha
    baseline = root / 'presentations/segmentation/run_06b_v2'
    cutoff = datetime.fromisoformat('2026-10-23T20:56:41.172018+00:00')
    inventory_path = baseline / 'history_source_inventory_refreshed.csv'
    inventory = list(csv.DictReader(inventory_path.open(encoding='utf-8-sig', newline='')))
    sources = []
    known = set()
    for item in inventory:
        if item['source'].startswith('data/') and item['source'].endswith('.csv'):
            path = root / item['source']
            digest = sha(path.read_bytes())
            if digest != item['hash']:
                raise PermissionError('Historical result changed; reconcile before launch: ' + str(path))
            known.add(path.resolve())
            sources.append({'path': str(path), 'sha256': digest})
    # Discover newly saved results/checkpoints in the canonical legacy output folder.
    # Older merged files are already represented by the frozen history baseline.
    for pattern in ('vision_results*.csv', 'merged_results*.csv', '*checkpoint*.csv'):
        for path in (root / 'data/05_vision_release').glob(pattern):
            if path.resolve() not in known and path.stat().st_mtime > cutoff.timestamp():
                raise PermissionError('New historical output needs reconciliation: ' + str(path))
    links_path = root / 'presentations/segmentation/run_06b_final_candidates_v1/secondary_coverage_proposal.csv'
    links = list(csv.DictReader(links_path.open(encoding='utf-8-sig', newline='')))
    codes = {r['barcode'] for r in rows} | {r['secondary_barcode'] for r in links}
    history_path = baseline / 'history_observations_refreshed.csv'
    recorded = {}
    with history_path.open(encoding='utf-8-sig', newline='') as stream:
        for event in csv.DictReader(stream):
            if event['source'] == 'database/positioning_radar.db::product_analysis' and event['barcode'] in codes:
                recorded.setdefault(event['barcode'], set()).add(event['timestamp'])
    db_path = root / 'database/positioning_radar.db'
    query = ('SELECT pack_analysis_attempted,ocr_status,llm_status,pack_analysis_timestamp '
             'FROM product_analysis WHERE barcode=?')
    checked = 0
    with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as connection:
        plan = ' '.join(str(r[3]) for r in connection.execute('EXPLAIN QUERY PLAN ' + query, ('',)))
        if 'SCAN' in plan.upper() or 'SEARCH' not in plan.upper() or 'INDEX' not in plan.upper():
            raise PermissionError('History lookup must use the exact-barcode index')
        observations = []
        for code in sorted(codes):
            result = connection.execute(query, (code,)).fetchone()
            checked += 1
            if not result:
                continue
            attempted, ocr_status, llm_status, stamp = result
            if attempted or ocr_status or llm_status:
                if (stamp or '') not in recorded.get(code, set()):
                    raise PermissionError('New or changed database vision history requires reconciliation: ' + code)
                observations.append([code, *result])
    snapshot_path = Path(receipt_path).with_name('bounded_database_history.json')
    snapshot_path.write_text(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'query_plan': plan, 'exact_barcode_lookups': checked, 'observations': observations,
        'scope': 'All proposed primary and saved secondary GTINs; no database-wide evidence search.'}, indent=2), encoding='utf-8')
    for path in (inventory_path, history_path, links_path, snapshot_path):
        sources.append({'path': str(path), 'sha256': sha(path.read_bytes())})
    if reconciliation:
        binding=root/reconciliation['path']
        if sha(binding.read_bytes())!=reconciliation['sha256']:
            raise PermissionError('Saved mini/pilot reconciliation changed')
        proof=json.loads(binding.read_text(encoding='utf-8'))
        if proof['manifest_sha256']!=manifest_sha:
            raise PermissionError('Reconciliation is for a different manifest')
        for rel,digest in proof['immutable_sources_sha256'].items():
            path=root/rel
            if sha(path.read_bytes())!=digest:raise PermissionError('Reconciled history source changed: '+rel)
            sources.append({'path':str(path),'sha256':digest})
        sources.append({'path':str(binding),'sha256':reconciliation['sha256']})
    receipt = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'manifest_sha256': manifest_sha, 'configuration_sha256': config_sha,
        'primary_identities_sha256': stable_hash(sorted({(r['barcode'], r['region']) for r in rows})),
        'all_saved_sources_reconciled': True, 'secondary_identities_included': True,
        'unresolved_matches': 0, 'new_ineligible_events': 0,
        'reviewed_by': 'Automated bounded unchanged-source / exact-indexed-history check',
        'source_inventory': sources,
        'reconciled_mini_cases': sorted(proof['v6_reuse']) if reconciliation else [],
        'limitation': 'Uses declared local history sources and linked GTINs; does not discover arbitrary external runs or unknown other-GTIN image equivalence.'}
    Path(receipt_path).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt
