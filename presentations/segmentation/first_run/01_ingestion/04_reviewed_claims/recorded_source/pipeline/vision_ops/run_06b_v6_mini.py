"""Authorized four-case mini/v3 confirmation. No OCR/core path or retries."""
import argparse
import copy
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.vision_ops import emerging_benefits_v3 as v3
from pipeline.vision_ops import run_06b_v6_confirmation as shared
from pipeline.vision_ops.run_06b_execution_guard import approved_uncapped_mini_confirmation, stable_hash
from pipeline.vision_ops.run_06b_runner import Staging, request_reservation, priced_tokens, response_layers
from pipeline.vision_ops.run_06b_rate_limit import SharedLLMPacer

ROOT = shared.ROOT
PACKAGE = ROOT / 'presentations/segmentation/run_06b_v6_mini_v3'
PROPOSAL = PACKAGE / 'confirmation.json'
APPROVAL = PACKAGE / 'julia_approval.json'
STAGING = PACKAGE / 'staging.sqlite'
REPORT = PACKAGE / 'Mini v3 - Four-case results.md'
DEPLOYMENT = 'gpt-4.1-mini-v6-test'
MODEL = 'gpt-4.1-mini-2025-04-14'


def strict_format(provider):
    """Mini capability adapter; the frozen v3 classification contract is unchanged."""
    path = Path(provider['verification_source_path'])
    if shared.file_sha(path) != provider['verification_source_sha256']:
        raise PermissionError('Mini metadata changed')
    m = json.loads(path.read_text(encoding='utf-8'))['metadata']
    if not (provider.get('deployment_verified') and provider['deployment'] == DEPLOYMENT and
            provider['response_model'] == MODEL and provider['model_version'] == '2025-04-14' and
            m['name'] == DEPLOYMENT and m['model']['name'] == 'gpt-4.1-mini' and
            m['model']['version'] == '2025-04-14' and m['provisioningState'] == 'Succeeded'):
        raise PermissionError('Mini deployment/version not verified')
    def compact(x):
        if isinstance(x, dict):return {k:compact(v) for k,v in x.items() if k!='title'}
        if isinstance(x, list):return [compact(v) for v in x]
        return x
    return {'type':'json_schema','json_schema':{'name':'emerging_benefits_interpretations_v3',
                                               'strict':True,'schema':compact(v3.schema())}}


def build_body(case, config):
    inp = copy.deepcopy(case['saved_input']); inp['request_id'] = case['call_id']
    prompt, _ = v3.prepare_saved_ocr(inp)
    body = dict(model=DEPLOYMENT, messages=[{'role':'system','content':prompt},
        {'role':'user','content':json.dumps(v3.model_input(inp),ensure_ascii=False)}],
        temperature=0,max_tokens=2000,response_format=strict_format(config['provider']))
    return inp, body


def load_proposal():
    p = json.loads(PROPOSAL.read_text(encoding='utf-8'))
    if tuple(c['slot'] for c in p['cases']) != shared.SLOTS or p['ceiling_nanochf'] is not None:
        raise PermissionError('Exact four-case no-ceiling proposal required')
    if Path(p['staging_path']).resolve() != STAGING.resolve():raise PermissionError('Fixed checkpoint required')
    for rel,digest in {**p['runtime_files_sha256'],**p['saved_sources_sha256']}.items():
        if shared.file_sha(ROOT/rel) != digest:raise PermissionError('Source changed: '+rel)
    for case in p['cases']:
        if case['row']['category'] != 'beverages':raise PermissionError('Only beverages authorized')
        inp,body = build_body(case,p['configuration'])
        amount,_ = request_reservation(shared.KIND,body,p['configuration']['tariffs'])
        if stable_hash(body) != case['body_sha256'] or amount != case['reservation_nanochf']:
            raise PermissionError('Frozen request/cost quote changed')
        if len(json.dumps(body,ensure_ascii=False).encode())>32768:raise PermissionError('Input bound exceeded')
    if len({c['call_id'] for c in p['cases']})!=4:raise PermissionError('Duplicate call identity')
    return p


def policy(proposal):
    if not APPROVAL.is_file():raise PermissionError('Explicit Julia approval required')
    p = dict(execution_authorized=True,tariffs_validated=False,
        spending_mode='uncapped_four_case_v3_mini',ceiling_nanochf=None,attempt_cap=4,
        authorized_primary_slots=list(shared.SLOTS),model_deployment=DEPLOYMENT,response_model=MODEL,
        approval_record_path=str(APPROVAL),approval_sha256=shared.file_sha(APPROVAL),
        manifest_sha256=shared.file_sha(PROPOSAL),reservation_method='rendered_request_utf8_upper_bound_v1',
        worst_case_nanochf_per_call={shared.KIND:max(c['reservation_nanochf'] for c in proposal['cases'])},
        max_calls_per_job={shared.KIND:1})
    if not approved_uncapped_mini_confirmation(p):raise PermissionError('Missing/mismatched/expired mini-only approval')
    return p


def validate_reply(store, case, reply, tariffs):
    key=case['call_id']; layers=response_layers(reply)
    store.event(key,'response_layers',layers)
    if store.db.execute('SELECT 1 FROM receipts WHERE call_id=?',(key,)).fetchone() is None:
        usage=reply['usage']
        cost=priced_tokens(usage['prompt_tokens'],usage['completion_tokens'],tariffs,
            cached_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0))
        store.guard.receipt(key,reply['provider_request_id'],cost,'provider_response_received',usage=usage,
            tariff_sha256=stable_hash(tariffs),raw_receipt_sha256=stable_hash(reply))
        store.guard._authorized()
    inp=copy.deepcopy(case['saved_input']);inp['request_id']=key
    try:
        result,status=v3.validate_saved_ocr_result(inp,reply['output'],
            record=lambda audit:store.event(key,'v6_postprocessing',audit))
        shared.case_acceptance(case,result)
    except (ValueError,TypeError,KeyError) as exc:
        store.event(key,'validation_decision',{'schema_validation':
            json.loads(store.db.execute("SELECT payload FROM stage_events WHERE key=? AND event='v6_postprocessing' ORDER BY id DESC LIMIT 1",(key,)).fetchone()[0])['schema_validation'],
            'validation':'FAIL','reason':str(exc)})
        store.guard.append_observation(key,'failed',{'reason':str(exc)})
        return
    result['_validation'].update(layers)
    store.finish(key,shared.KIND,status,result)
    store.guard.append_observation(key,status,result)
    store.event(key,'validation_decision',{'schema_validation':'PASS','validation':'PASS','reason':'v3 contract and four-case acceptance passed'})


def results(proposal, db):
    rows=[]
    for case in proposal['cases']:
        key=case['call_id'];events=[(e,json.loads(p)) for e,p in db.execute('SELECT event,payload FROM stage_events WHERE key=? ORDER BY id',(key,))]
        reply=next((p for e,p in reversed(events) if e=='provider_result'),{})
        raw=next((p for e,p in reversed(events) if e=='raw_response'),{})
        audit=next((p for e,p in reversed(events) if e=='v6_postprocessing'),{})
        decision=next((p for e,p in reversed(events) if e=='validation_decision'),{})
        saved=db.execute('SELECT payload FROM stage_results WHERE key=?',(key,)).fetchone()
        payload=json.loads(saved[0]) if saved else {}
        usage=reply.get('usage') or {};cost=None
        if {'prompt_tokens','completion_tokens'}.issubset(usage):
            cost=priced_tokens(usage['prompt_tokens'],usage['completion_tokens'],proposal['configuration']['tariffs'],
                cached_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0))
        rows.append(dict(slot=case['slot'],http=raw.get('status_code','NOT_DISPATCHED'),
            json_parse=reply.get('json_parse_status','NOT_RUN'),schema=audit.get('schema_validation','NOT_RUN'),
            validation=decision.get('validation','FAIL' if events else 'NOT_RUN'),
            hydration=' / '.join(payload.get('hydration',{}).get(k,'—') for k in ['content_status','front_status']),
            electrolyte=' / '.join(payload.get('electrolyte',{}).get(k,'—') for k in ['content_status','front_status']),
            reason=decision.get('reason', next((p.get('reason','') for e,p in reversed(events) if e=='failure_or_uncertain'),'Unresolved; no retry')),
            input_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens'),estimated_nanochf=cost))
    return rows


def write_report(proposal, rows):
    fields=['slot','http','json_parse','schema','hydration','electrolyte','validation','input_tokens','output_tokens','estimated_nanochf','reason']
    lines=['# Mini v3 — Four-case live results','',f'Deployment: `{DEPLOYMENT}`; model: `{MODEL}`. Maximum four v6 calls; no OCR/core and no retries. Julia authorized no monetary ceiling.','',
        '| Case | HTTP | JSON | Schema | Hydration content / front | Electrolyte content / front | Assessment | Input tokens | Output tokens | Estimated CHF | Reason |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        values=[f"{row[f]/1e9:.8f}" if f=='estimated_nanochf' and row[f] is not None else str(row[f] if row[f] is not None else '—') for f in fields]
        lines.append('| '+' | '.join(v.replace('|','\\|').replace('\n',' ') for v in values)+' |')
    passed=sum(r['validation']=='PASS' for r in rows)
    lines += ['',f'Accepted: {passed}/4. Estimated total CHF {sum(r["estimated_nanochf"] or 0 for r in rows)/1e9:.8f}.',
        'Costs use provisional input/output rates CHF 0.40/1.60 per million tokens (cached input CHF 0.10); Azure account tariffs/invoice charges remain unverified. Actual provider token usage is recorded.',
        '', 'All requests/responses, usage, reservations, receipts and interpretation/validation decisions are retained in the append-only `staging.sqlite` beside this report. Original v1/v2 evidence, OCR and core checkpoints were not changed.',
        '', '**STOP. This confirmation does not authorize the main run.**','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    proposal=load_proposal()
    if not args.execute:
        if STAGING.exists():
            with sqlite3.connect(STAGING.as_uri()+'?mode=ro',uri=True) as db:write_report(proposal,results(proposal,db))
        print(REPORT);return
    approved=policy(proposal)
    # This process must be launched with its mini-only deployment override.
    # No .env, core configuration or permanent environment setting is changed.
    provider=shared.V6OnlyProvider(proposal['configuration']);provider.validate()
    store=Staging(STAGING,approved)
    try:
        provider.pacer=SharedLLMPacer(store.db,provider.rate_limits['request'],provider.rate_limits['token'])
        shared.execute_cases(proposal,approved,store,provider,authorize=lambda:policy(proposal),
                             build_request=build_body,validate_reply=validate_reply)
    finally:
        rows=results(proposal,store.db);write_report(proposal,rows);store.guard.close()
    for row in rows:print(json.dumps(row,ensure_ascii=False),flush=True)
    print(REPORT)
    return 0 if all(r['validation']=='PASS' for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
