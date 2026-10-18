"""Assess stored claims against explicit local extraction evidence; no network calls."""
import csv
import hashlib
import json
import re
from pathlib import Path
from collections import defaultdict


def text(value):
    return '' if value is None else str(value).strip()


def evidence_key(row):
    return tuple(text(row.get(k)) for k in ('barcode', 'pack_analysis_timestamp', 'prompt_version', 'claims_json'))


def load_evidence(directory):
    index = defaultdict(list)
    manifest = {}
    # Stage 10 results preserve the actual prompt inputs. Merged exports join
    # current DB metadata and cannot establish the analyzed image/text context.
    for path in sorted(Path(directory).glob('vision_results*.csv')):
        if 'checkpoint' in path.name.lower():
            continue
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            required = {'barcode', 'image_url', 'pack_analysis_timestamp', 'prompt_version', 'claims_json', 'llm_status'}
            if not required.issubset(reader.fieldnames or []):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest[str(path.resolve())] = digest
            for row in reader:
                if row['llm_status'] == 'success' and row['pack_analysis_timestamp'] and row['prompt_version'] and row['claims_json']:
                    index[evidence_key(row)].append({k: row.get(k) for k in ('image_url', 'product_name', 'brands')} | {'source': str(path.resolve()), 'sha256': digest})
    return index, manifest


def assess(product, analysis, index):
    if analysis.get('pack_claims_found') is None:
        return 'no_stored_observation', None
    if analysis.get('llm_status') != 'success' or analysis.get('claim_extraction_status') != 'completed':
        return 'unknown_attempt_provenance', None
    matches = index.get(evidence_key(analysis), [])
    if not matches:
        return 'unknown_image_provenance', None
    identities = {(text(r['image_url']), text(r['product_name']), text(r['brands'])) for r in matches}
    if len(identities) != 1:
        return 'conflicting_image_provenance', matches
    old_url, old_name, old_brands = next(iter(identities))
    if not old_url or not text(product.get('image_url')):
        return 'unknown_image_reference', matches
    if old_url != text(product['image_url']):
        return 'image_reference_changed', matches
    # Only revision-bearing OFF URLs support carrying forward by reference.
    if not re.search(r'/front_[a-z-]+\.\d+\.\d+\.(?:jpg|png)$', old_url):
        return 'unversioned_image_reference', matches
    if not old_name or not old_brands:
        return 'unknown_text_context', matches
    if old_name != text(product.get('product_name')) or old_brands != text(product.get('primary_brand', product.get('brands'))):
        return 'text_context_changed', matches
    return 'matched_image_reference', matches


def audit(conn, evidence_dir):
    index, evidence_manifest = load_evidence(evidence_dir)
    conn.execute("CREATE TABLE claim_freshness (barcode TEXT PRIMARY KEY, status TEXT NOT NULL, evidence_json TEXT, prior_analysis_json TEXT NOT NULL)")
    conn.row_factory = __import__('sqlite3').Row
    counts = defaultdict(int)
    # Preserve every original observation before masking only the derived release.
    for row in conn.execute('SELECT p.barcode,p.image_url,p.product_name,p.primary_brand FROM products p JOIN population_membership m ON m.barcode=p.barcode WHERE m.membership=\'retained\'').fetchall():
        product = dict(row)
        found = conn.execute('SELECT * FROM product_analysis WHERE barcode=?', (product['barcode'],)).fetchone()
        analysis = dict(found) if found else {'barcode': product['barcode']}
        status, evidence = assess(product, analysis, index)
        counts[status] += 1
        conn.execute('INSERT INTO claim_freshness VALUES (?,?,?,?)', (product['barcode'], status, json.dumps(evidence), json.dumps(analysis)))
        if status != 'matched_image_reference':
            conn.execute("UPDATE product_analysis SET pack_claims_found=NULL, pack_analysis_attempted=0, positioning_composition_gap=NULL, positioning_composition_gap_band=NULL WHERE barcode=?", (product['barcode'],))
    conn.row_factory = None
    conn.commit()
    return dict(counts), evidence_manifest
