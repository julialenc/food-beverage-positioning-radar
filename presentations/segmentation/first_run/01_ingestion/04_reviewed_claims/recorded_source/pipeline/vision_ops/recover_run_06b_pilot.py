"""Offline, versioned recovery/export of the saved pilot. Never writes staging."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.vision_ops.run_06b_execution_guard import stable_hash
from pipeline.vision_ops.validate_emerging_benefits_v1 import validate_pair, H_WORDING, E_WORDING

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'presentations/segmentation/run_06b_pilot_recovery_v1'
STAGING = ROOT / 'presentations/segmentation/run_06b_execution_staging_v1/staging.sqlite'
KINDS = ('ocr', 'core', 'dairy_review', 'dairy_reextract', 'emerging_benefits')


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_conflicts(raw):
    """A panel classifier cannot silently override a conflicting extraction status."""
    context = raw.get('image_context')
    expected = ('completed' if context in {'front_of_pack', 'mixed_pack_text'} else
                'not_applicable_non_front' if context in {'ingredient_or_legal_panel', 'nutrition_label', 'price_sticker'} else
                'unreadable' if context == 'uncertain' else None)
    return ([f"image_context={context} conflicts with claim_extraction_status={raw.get('claim_extraction_status')}; expected {expected}"]
            if expected and raw.get('claim_extraction_status') != expected else [])


def recover_v6(inp, raw):
    """Conservative repair of representation/offsets; never infer positive labels."""
    candidate = copy.deepcopy(raw)
    changes, unresolved = [], []
    text = inp['ocr_text']

    def change(obj, field, value, path, reason):
        if obj[field] != value:
            changes.append(dict(path=path+'.'+field, before=obj[field], after=value, reason=reason))
            obj[field] = value

    # Record semantic contradictions BEFORE downgrading statuses. Abstention must
    # not disguise an affirmative phrase that the model erroneously rejected.
    for name, pattern in (('hydration', H_WORDING), ('electrolyte', E_WORDING)):
        a = candidate[name]
        support = [e for e in a['evidence'] if e['role'] in {'supporting_positioning', 'back_panel_feature'}]
        if a['content_status'] == 'not_detected' and any(pattern.search(e['phrase']) for e in support):
            unresolved.append(name + ': negative status contradicts explicit supporting wording')
        if a['content_status'] == 'not_detected' and re.search(r'\b(?:supports?|supporting)\b.*\bpositioning\b', a['reason'], re.I):
            unresolved.append(name + ': negative status contradicts affirmative explanation')
        if any(not pattern.search(e['phrase']) for e in support):
            unresolved.append(name + ': supporting evidence contains no qualifying benefit wording')
        if a['content_status'] == 'not_detected' and pattern.search(text) and not a['evidence']:
            unresolved.append(name + ': negative result omits relevant OCR wording; requires context review')
        for i, evidence in enumerate(a['evidence']):
            start, end, phrase = evidence['start_0based'], evidence['end_exclusive'], evidence['phrase']
            if text[start:end] == phrase and 0 <= start < end <= len(text):
                continue
            hits = [m.start() for m in re.finditer(re.escape(phrase), text)] if phrase else []
            if len(hits) != 1:
                unresolved.append(f'{name}.evidence[{i}]: exact phrase has {len(hits)} matches; quote not rewritten')
            else:
                path = f'{name}.evidence[{i}]'
                change(evidence, 'start_0based', hits[0], path, 'Unique exact phrase in original full OCR')
                change(evidence, 'end_exclusive', hits[0]+len(phrase), path, 'Unique exact phrase in original full OCR')
        if a['purpose'] == 'null':
            if a['content_status'] in {'not_detected', 'unassessable', 'ambiguous'}:
                change(a, 'purpose', None, name, 'Quoted null meant missing purpose; no positive proposition established')
            else:
                unresolved.append(name + ': quoted null on positive assessment requires review')
        if a['target_attribution'] != 'target':
            change(a, 'content_status', 'unassessable', name, 'Target attribution not established; no target negative inferred')
        if a['target_attribution'] != 'target' or a['panel_scope'] != 'front' or a['scope_basis'] == 'unresolved':
            change(a, 'front_status', 'unassessable', name, 'Target front scope not established')
        if a['content_status'] == 'unassessable':
            change(a, 'purpose', None, name, 'No target proposition purpose established')
            change(a, 'reason', a['reason'] + ' Offline reconciliation: target attribution is unresolved or unrelated; this is an abstention, not a negative target assessment.', name, 'Make the preserved original explanation consistent with abstention')
    try:
        validate_pair(inp, candidate)
    except Exception as exc:
        unresolved.append(type(exc).__name__ + ': ' + str(exc))
    status = 'UNRESOLVED' if unresolved else ('ACCEPTED_ABSTENTION' if any(
        candidate[n]['front_status'] in {'unassessable', 'ambiguous'} for n in ('hydration', 'electrolyte')) else 'ACCEPTED_ASSESSMENT')
    return dict(status=status, corrected_candidate=candidate, corrections=changes,
                unresolved=list(dict.fromkeys(unresolved)), raw_output_sha256=stable_hash(raw), input_sha256=stable_hash(inp))


def exact_gtin(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+', value):
        raise ValueError('GTIN must come from an exact digit string, never a float/scientific export')
    return value


def excel_gtin(value):
    # A digit-only constant formula is safe and keeps CSV double-click in Excel
    # from rounding or stripping zeros. The adjacent barcode_exact column is the
    # untouched machine-readable identifier; XLSX exports use a text cell.
    return '="' + exact_gtin(value) + '"'


def load_pilot():
    package = ROOT / 'presentations/segmentation/run_06b_pilot_launch_v1'
    config = json.loads((package/'pilot_configuration.json').read_text())
    policy = json.loads((package/'pilot_policy.json').read_text())
    manifest = ROOT/'presentations/segmentation/run_06b_final_candidates_v1/proposed_primary_processing_manifest.csv'
    assert sha_file(manifest) == policy['manifest_sha256']
    with manifest.open(encoding='utf-8-sig', newline='') as stream:
        rows = [r for r in csv.DictReader(stream) if r['proposed_primary_slot_id'] in set(policy['authorized_primary_slots'])]
    assert len(rows) == 96
    by_slot = {r['proposed_primary_slot_id']:r for r in rows}
    with sqlite3.connect(STAGING.as_uri()+'?mode=ro', uri=True) as db:
        events = defaultdict(list)
        for key, event, payload, stamp in db.execute('SELECT key,event,payload,recorded_at_utc FROM stage_events ORDER BY id'):
            events[key].append(dict(event=event, payload=json.loads(payload), timestamp=stamp))
        results = {k:dict(kind=kind,status=status,payload=json.loads(p)) for k,kind,status,p in db.execute('SELECT key,kind,status,payload FROM stage_results')}
        calls = {k:kind for k,kind in db.execute('SELECT call_id,kind FROM calls')}
    config_sha = stable_hash(config)

    def key(row,kind,source=None):
        identity = ({'image':row['image_sha256'],'ocr':config['ocr'],'provider_endpoint':config['provider']['vision_endpoint']}
                    if kind == 'ocr' else {'row':row,'runtime':config_sha,'source':source})
        return stable_hash({'stage':kind,'identity':identity})

    fixtures=[]
    for row in rows:
        ocr_key=key(row,'ocr'); ocr=results[ocr_key]['payload']['text']; source=hashlib.sha256(ocr.encode()).hexdigest()
        review=results.get(key(row,'dairy_review',source),{}).get('payload')
        stages={}
        for kind in KINDS:
            k=(key(row,kind,stable_hash([source,review])) if kind=='dairy_reextract' and review else key(row,kind,source))
            ev=events.get(k,[])
            for event in ev:
                if event['event']=='dispatch':
                    dispatched_row=event['payload']['row']
                    assert dispatched_row==by_slot[dispatched_row['proposed_primary_slot_id']], 'Frozen row differs from original dispatch'
                    if kind!='ocr':
                        assert dispatched_row==row
                    else:
                        assert dispatched_row['image_sha256']==row['image_sha256'], 'Shared OCR image differs'
            stages[kind]=dict(key=k,events=ev,result=results.get(k),dispatched=k in calls)
        fixtures.append(dict(row=row,ocr=ocr,stages=stages))
    return fixtures, config, policy


def provider_output(stage):
    return next((e['payload'].get('output') for e in stage['events'] if e['event']=='provider_result'),None)


def write_csv(path, rows):
    columns=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)


def finalize_export(record):
    for kind in ('core','dairy_reextract'):
        raw=record.get(kind+'_raw_output') or {}
        record[kind+'_raw_image_context']=raw.get('image_context')
        record[kind+'_raw_claim_extraction_status']=raw.get('claim_extraction_status')
    record.setdefault('core_review_status','UNRESOLVED_HTTP_429')
    record.setdefault('v6_recovery_status','not_applicable')
    source='dairy_reextract' if record.get('dairy_reextract_review_status')=='ACCEPTED_EXISTING' else 'core'
    record['effective_core_source']=source
    record['effective_core_review_status']=record[source+'_review_status']
    return record


def main():
    if OUTPUT.exists() and any(p.name!='.gitignore' for p in OUTPUT.iterdir()):
        raise FileExistsError('Recovery version already populated; preserve it and choose a new version')
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT/'.gitignore').write_text('*\n')
    before=sha_file(STAGING)
    fixtures, config, policy=load_pilot()
    exports=[]; recovered=[]; core_register=[]; limits=[]; timings=[]
    for fixture in fixtures:
        row=fixture['row']; stages=fixture['stages']; slot=row['proposed_primary_slot_id']
        record=dict(GTIN=excel_gtin(row['barcode']),barcode_exact=exact_gtin(row['barcode']),slot=slot,
                    product_name=row['product_name'],brands=row['brands'],region=row['region'],category=row['category'],
                    countries=row['countries'],picture_URL=row['original_image_url'],ocr_text=fixture['ocr'])
        for kind,stage in stages.items():
            raw=provider_output(stage); saved=stage['result']; failures=[e for e in stage['events'] if e['event'] in {'failure_or_uncertain','input_bound_hold','saved_result_validation_failed'}]
            applicable=(kind in {'ocr','core'} or kind=='emerging_benefits' and row['category']=='beverages' or kind.startswith('dairy_') and row['category'] in {'dairy','dairies'})
            record[kind+'_saved_status']=saved['status'] if saved else 'failed_or_unresolved' if stage['dispatched'] or failures else 'not_triggered' if applicable else 'not_applicable'
            record[kind+'_errors']=failures
            if kind!='ocr':
                record[kind+'_raw_output']=raw
                record[kind+'_saved_result']=saved['payload'] if saved else None
            for ev in stage['events']:
                if ev['event']=='dispatch' and kind!='ocr':
                    body=ev['payload']['body']
                    timings.append(dict(slot=slot,kind=kind,region=row['region'],timestamp=ev['timestamp'],
                        request_utf8_bytes=len(json.dumps(body,ensure_ascii=False).encode()),max_output_tokens=body['max_tokens']))
                if ev['event']=='raw_response' and ev['payload']['status_code']==429:
                    limits.append(dict(slot=slot,kind=kind,region=row['region'],timestamp=ev['timestamp'],response=ev['payload'],disposition='HOLD; no retry or reservation release performed'))
            if kind in {'core','dairy_reextract'} and raw:
                conflicts=core_conflicts(raw)
                disposition='HOLD_STATUS_CONFLICT' if conflicts else 'UNUSABLE' if saved and saved['status']=='unusable' else 'ACCEPTED_EXISTING'
                record[kind+'_review_status']=disposition
                core_register.append(dict(slot=slot,barcode_exact=row['barcode'],kind=kind,raw_image_context=raw.get('image_context'),
                    raw_claim_extraction_status=raw.get('claim_extraction_status'),saved_status=saved['status'] if saved else None,
                    saved_claim_extraction_status=saved['payload'].get('claim_extraction_status') if saved else None,
                    disposition=disposition,conflicts=conflicts))
                if kind=='core':
                    for field,value in (saved['payload'] if saved else {}).items():record['core_'+field]=value
        if row['category']=='beverages':
            stage=stages['emerging_benefits']; raw=provider_output(stage)
            dispatch=next((e['payload'] for e in stage['events'] if e['event']=='dispatch'),None)
            if raw:
                inp=json.loads(dispatch['body']['messages'][1]['content'])
                assert inp['ocr_text']==fixture['ocr']
                recovery=recover_v6(inp,raw)
            else: recovery=dict(status='UNRESOLVED_HTTP_429',corrections=[],unresolved=['No returned model assessment'],corrected_candidate=None)
            recovery.update(slot=slot,barcode_exact=row['barcode'],product_name=row['product_name'],raw_output=raw,
                original_stage_key=stage['key'],original_validation_failures=record['emerging_benefits_errors'])
            recovered.append(recovery)
            record['v6_recovery_status']=recovery['status'];record['v6_unresolved']=recovery['unresolved']
            if recovery['status'].startswith('ACCEPTED'):
                for name in ('hydration','electrolyte'):
                    for field,value in recovery['corrected_candidate'][name].items():record[name+'_'+field]=value
            else:
                # Unaccepted candidates cannot masquerade as analysis labels.
                for name in ('hydration','electrolyte'):
                    record[name+'_content_status']='unresolved';record[name+'_front_status']='unresolved'
        exports.append(finalize_export(record))
    summary=dict(records=len(exports),exact_GTIN_dispatch_matches=96,source_database_sha256=before,
        v6= dict(Counter(x['status'] for x in recovered)),core=dict(Counter(x['disposition'] for x in core_register if x['kind']=='core')),
        http_429=dict(Counter(x['kind'] for x in limits)),additional_provider_calls=0,
        recovery_policy='v1: representation and unique exact offsets only; unresolved attribution abstains; semantic contradictions held',
        source_config_sha256=stable_hash(config),source_policy_sha256=stable_hash(policy))
    for name,value in [('saved_pilot_regression_fixtures.json',fixtures),('v6_offline_recovery.json',recovered),
                       ('rate_limit_findings.json',dict(errors=limits,dispatches=timings)),('export_rows.json',exports),('summary.json',summary)]:
        (OUTPUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(OUTPUT/'RUN_06B_pilot_96_corrected.csv',exports)
    write_csv(OUTPUT/'core_consistency_register.csv',core_register)
    write_csv(OUTPUT/'v6_recovery_register.csv',[dict(GTIN=excel_gtin(x['barcode_exact']),slot=x['slot'],status=x['status'],corrections=x['corrections'],unresolved=x['unresolved']) for x in recovered])
    assert sha_file(STAGING)==before, 'Source staging changed during offline recovery'
    with (OUTPUT/'RUN_06B_pilot_96_corrected.csv').open(encoding='utf-8-sig',newline='') as stream:
        readback=list(csv.DictReader(stream))
    assert len(readback)==96 and [x['barcode_exact'] for x in readback]==[x['row']['barcode'] for x in fixtures]
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
