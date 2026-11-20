"""Four fixed saved-OCR v6 calls only. Default mode reports without dispatch.

Reuses Guard, Staging, AzureProvider and SharedLLMPacer. Never calls run_row,
OCR, core extraction or the main batch. A separate approval file is required.
"""
import argparse
import copy
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.vision_ops import emerging_benefits_v2 as v2
from pipeline.vision_ops.run_06b_execution_guard import stable_hash
from pipeline.vision_ops.run_06b_rate_limit import SharedLLMPacer
from pipeline.vision_ops.run_06b_runner import (
    AzureProvider, Staging, ConfigurationMismatch, request_reservation, priced_tokens,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'presentations/segmentation/run_06b_v6_confirmation_v1'
PROPOSAL = PACKAGE / 'confirmation.json'
APPROVAL = PACKAGE / 'julia_approval.json'
STAGING = PACKAGE / 'staging.sqlite'
REPORT = PACKAGE / 'Four-case v6 confirmation.md'
SLOTS = ('S09485', 'S04845', 'S00006', 'S09587')
CEILING = 20_000_000  # nanoCHF: CHF 0.02, never CHF 20.
KIND = 'emerging_benefits'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class V6OnlyProvider(AzureProvider):
    def call(self, kind, row, body, event):
        if kind != KIND:
            raise PermissionError('Confirmation transport forbids OCR/core/dairy submissions')
        if body.get('response_format', {}).get('type') != 'json_schema':
            raise PermissionError('Strict v2 schema required')
        return super().call(kind, row, body, event)


def build_body(case, config):
    inp = copy.deepcopy(case['saved_input'])
    inp['request_id'] = case['call_id']  # Only request identity changes.
    prompt, _ = v2.prepare_saved_ocr(inp)
    return inp, dict(model=config['provider']['deployment'],
        messages=[{'role': 'system', 'content': prompt},
                  {'role': 'user', 'content': json.dumps(inp, ensure_ascii=False)}],
        temperature=0, max_tokens=2000, response_format=v2.response_format(config['provider']))


def load_proposal(path=PROPOSAL):
    p = json.loads(path.read_text(encoding='utf-8'))
    if tuple(c['slot'] for c in p['cases']) != SLOTS or p['ceiling_nanochf'] != CEILING:
        raise PermissionError('Exactly four fixed cases and CHF 0.02 required')
    if Path(p['staging_path']).resolve() != STAGING.resolve():
        raise PermissionError('Fixed confirmation checkpoint path required')
    for rel, digest in {**p['runtime_files_sha256'], **p['saved_sources_sha256']}.items():
        if file_sha(ROOT / rel) != digest:
            raise PermissionError('Source changed; reconcile before dispatch: ' + rel)
    v2.frozen_contract()
    for case in p['cases']:
        row = case['row']
        if row['category'] != 'beverages' or row['proposed_primary_slot_id'] != case['slot']:
            raise PermissionError('Frozen case identity mismatch')
        inp, body = build_body(case, p['configuration'])
        amount, _ = request_reservation(KIND, body, p['configuration']['tariffs'])
        if stable_hash(body) != case['body_sha256'] or amount != case['reservation_nanochf']:
            raise PermissionError('Prepared request/reservation mismatch')
        if len(json.dumps(body, ensure_ascii=False).encode()) > 32768:
            raise PermissionError('Request exceeds existing byte bound')
    if len({c['call_id'] for c in p['cases']}) != 4 or sum(c['reservation_nanochf'] for c in p['cases']) > CEILING:
        raise PermissionError('Duplicate keys or insufficient ceiling')
    return p


def approved_policy(proposal, approval_path=APPROVAL, now=None):
    now = now or datetime.now(timezone.utc)
    if not approval_path.is_file():
        raise PermissionError('Julia must approve four v6 calls, CHF 0.02 and provisional pricing before execution')
    a = json.loads(approval_path.read_text(encoding='utf-8'))
    expires = datetime.fromisoformat(a['valid_until_utc'])
    approved_at = datetime.fromisoformat(a['approved_at_utc'])
    if not (a.get('approved_by') == 'Julia' and a.get('execution_authorized') is True and
            a.get('accept_provisional_rates') is True and a.get('proposal_sha256') == file_sha(PROPOSAL) and
            a.get('ceiling_nanochf') == CEILING and a.get('max_v6_calls') == 4 and
            tuple(a.get('authorized_slots', [])) == SLOTS and approved_at <= now < expires and
            0 < (expires-approved_at).total_seconds() <= 86400 and a.get('user_authorization')):
        raise PermissionError('Missing, expired or different four-call authorization')
    return dict(execution_authorized=True, tariffs_validated=False,
        pricing_basis='user_accepted_provisional_rates', spending_mode='bounded_four_case_v6_confirmation',
        authorized_primary_slots=list(SLOTS), approval_record_path=str(approval_path),
        approval_sha256=file_sha(approval_path), manifest_sha256=file_sha(PROPOSAL), attempt_cap=4,
        ceiling_nanochf=CEILING, reservation_method='rendered_request_utf8_upper_bound_v1',
        worst_case_nanochf_per_call={KIND: max(c['reservation_nanochf'] for c in proposal['cases'])},
        max_calls_per_job={KIND: 1})


def case_acceptance(case, candidate):
    if case['slot'] == 'S09485' and any(candidate[n]['content_status'] != 'detected' for n in ['hydration', 'electrolyte']):
        raise ValueError('Liquid I.V. control did not recognize both explicit content propositions')
    if case['slot'] == 'S09587' and any(candidate[n][s] in {'detected', 'not_detected'}
            for n in ['hydration', 'electrolyte'] for s in ['content_status', 'front_status']):
        raise ValueError('Unrelated/non-product wording cannot support confident target conclusions')


def validate_and_store(store, case, reply, tariffs):
    key = case['call_id']
    if store.db.execute('SELECT 1 FROM receipts WHERE call_id=?', (key,)).fetchone() is None:
        usage = reply['usage']
        cost = priced_tokens(usage['prompt_tokens'], usage['completion_tokens'], tariffs,
            cached_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0))
        store.guard.receipt(key, reply['provider_request_id'], cost, 'provider_response_received', usage=usage,
            tariff_sha256=stable_hash(tariffs), raw_receipt_sha256=stable_hash(reply))
        store.guard._authorized()
    inp = copy.deepcopy(case['saved_input']); inp['request_id'] = key
    try:
        candidate, status = v2.validate_saved_ocr_result(inp, reply['output'],
            record=lambda audit: store.event(key, 'v6_postprocessing', audit))
        case_acceptance(case, candidate)
    except (ValueError, TypeError, KeyError) as exc:
        store.event(key, 'validation_decision', {'validation': 'FAIL', 'reason': str(exc)})
        store.guard.append_observation(key, 'failed', {'validation': 'FAIL', 'reason': str(exc)})
        return
    store.event(key, 'validation_decision', {'validation': 'PASS', 'reason': 'v2 contract and case checks passed'})
    store.finish(key, KIND, status, candidate)
    store.guard.append_observation(key, status, candidate)


def execute_cases(proposal, policy, store, provider, authorize=lambda: None, *, build_request=None, validate_reply=None):
    """Four immutable keys across starts; existing calls are never re-dispatched."""
    tariffs = proposal['configuration']['tariffs']
    build_request = build_request or build_body
    validate_reply = validate_reply or validate_and_store
    for case in proposal['cases']:
        authorize()
        key = case['call_id']
        if store.result(key):
            continue
        if store.db.execute('SELECT 1 FROM calls WHERE call_id=?', (key,)).fetchone():
            saved = store.db.execute("SELECT payload FROM stage_events WHERE key=? AND event='provider_result' ORDER BY id DESC LIMIT 1", (key,)).fetchone()
            if saved:
                validate_reply(store, case, json.loads(saved[0]), tariffs)
            else:
                store.event(key, 'pending_reconciliation_no_redispatch', {})
            continue
        _, body = build_request(case, proposal['configuration'])
        store.guard.begin_job(key, policy['manifest_sha256'])
        amount, basis = request_reservation(KIND, body, tariffs)
        store.guard.reserve_call(key, key, KIND, reservation_nanochf=amount, basis=basis)
        store.event(key, 'dispatch', {'slot': case['slot'], 'body': body,
            'original_ocr_key': case['original_ocr_key'], 'original_core_key': case['original_core_key'],
            'proposal_sha256': policy['manifest_sha256']})
        try:
            reply = provider.call(KIND, case['row'], body, lambda event, payload: store.event(key, event, payload))
            store.event(key, 'provider_result', reply)
            validate_reply(store, case, reply, tariffs)
        except Exception as exc:
            store.event(key, 'failure_or_uncertain', {'type': type(exc).__name__, 'reason': str(exc)})
            store.guard.append_observation(key, 'failed', {'type': type(exc).__name__, 'reason': str(exc)})
            raw = store.db.execute("SELECT payload FROM stage_events WHERE key=? AND event='raw_response' ORDER BY id DESC LIMIT 1", (key,)).fetchone()
            if isinstance(exc, ConfigurationMismatch) or (raw and json.loads(raw[0])['status_code'] == 400):
                store.db.execute('INSERT INTO circuit_breaker VALUES (?)', ('Model/schema configuration rejected; human review required',))
            store.guard._authorized()  # Circuit breaker stops remaining calls.


def result_rows(proposal, db=None):
    rows = []
    for case in proposal['cases']:
        key = case['call_id']; events = []
        if db:
            events = [(e,json.loads(p)) for e,p in db.execute('SELECT event,payload FROM stage_events WHERE key=? ORDER BY id', (key,))]
        reply = next((p for e,p in reversed(events) if e == 'provider_result'), None)
        raw = next((p for e,p in reversed(events) if e == 'raw_response'), None)
        decision = next((p for e,p in reversed(events) if e == 'validation_decision'), None)
        output = (reply or {}).get('output') or {}
        record = dict(slot=case['slot'], model_response_status='PENDING APPROVAL' if db is None and not APPROVAL.exists() else 'NOT DISPATCHED',
            hydration='—', electrolyte='—', validation='NOT RUN', reason='No paid call submitted', tokens='—', estimated_CHF='—')
        if decision:record.update(validation=decision['validation'], reason=decision['reason'])
        if reply:
            record['model_response_status'] = 'HTTP 200 / ' + (reply.get('extraction_error') or 'JSON returned')
            for name in ['hydration', 'electrolyte']:
                a = output.get(name, {})
                record[name] = str(a.get('content_status','—')) + ' / ' + str(a.get('front_status','—'))
            usage = reply.get('usage') or {}
            record['tokens'] = str(usage.get('prompt_tokens','?')) + ' / ' + str(usage.get('completion_tokens','?'))
            if {'prompt_tokens', 'completion_tokens'}.issubset(usage):
                cost = priced_tokens(usage['prompt_tokens'], usage['completion_tokens'], proposal['configuration']['tariffs'],
                    cached_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0))
                record['estimated_CHF'] = f'{cost/1e9:.8f}'
            if not decision:record.update(validation='FAIL', reason='Usage/response processing incomplete; inspect saved errors')
        elif raw:
            record.update(model_response_status=f"HTTP {raw['status_code']}", validation='FAIL',
                reason='Provider error; no retry; reservation remains unresolved')
        elif events:
            record.update(model_response_status='UNKNOWN / RESERVED', validation='FAIL', reason='Uncertain outcome; no redispatch')
        rows.append(record)
    return rows


def write_report(proposal, rows):
    headers = ['Case', 'Model response', 'Hydration content / front', 'Electrolyte content / front', 'Validation', 'Reason', 'Input / output tokens', 'Estimated CHF']
    keys = ['slot','model_response_status','hydration','electrolyte','validation','reason','tokens','estimated_CHF']
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
    lines = ['# RUN 06B — Four-case v6 confirmation', '',
        'Four v6 calls maximum. OCR/core submissions: zero. '+
        ('Awaiting Julia’s separate CHF 0.02 and provisional-pricing approval.' if not APPROVAL.exists() else
         'Separate approval recorded; see each execution outcome below.'), '',
        '| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']
    lines += ['| '+' | '.join(cell(row[k]) for k in keys)+' |' for row in rows]
    lines += ['', f"Prepared reservation total: CHF {sum(c['reservation_nanochf'] for c in proposal['cases'])/1e9:.8f}.",
        'Guard ceiling: CHF 0.02 (20,000,000 nanoCHF). Existing provisional input/output rates: CHF 0.10/0.40 per million tokens. Account tariffs remain unverified; costs are estimates, not invoice facts.', '',
        'Fixed supplemental ledger: `presentations/segmentation/run_06b_v6_confirmation_v1/staging.sqlite`, created only after approval. Existing Guard, Staging, pacing and transport are reused. Original pilot checkpoints are preserved; accepted v2 observations must be reconciled before any future main run.', '',
        'The guard itself requires a hash-matching, unexpired Julia approval record for this four-call pricing exception. No approval record has been created by preparation. Old v1/full-run policies cannot authorize this test.', '',
        'After separate approval is installed, Julia runs from the repository root in CMD:', '', '```cmd',
        '.venv\\Scripts\\python.exe -B -m pipeline.vision_ops.run_06b_v6_confirmation --execute', '```',
        'The same command resumes without resubmitting any reserved call. Default invocation only refreshes this report. Run this bounded test alone; the supplemental ledger shares pacing across its own workers, not unrelated Azure clients.', '',
        'Raw responses, usage, failures, receipts and validation/offset decisions remain append-only. Live schema acceptance and classification accuracy remain unverified until execution.', '',
        '**STOP after these four results. No automatic retries or main batch.**', '']
    verification = proposal.get('offline_verification')
    if verification:
        lines += [f"Offline verification: {verification['test_count']} focused tests passed; paid provider calls: zero during preparation.", '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    proposal = load_proposal()
    if not args.execute:
        if STAGING.exists():
            with sqlite3.connect(STAGING.as_uri()+'?mode=ro', uri=True) as db:rows = result_rows(proposal, db)
        else:rows = result_rows(proposal)
        write_report(proposal, rows); print(REPORT); return
    policy = approved_policy(proposal)  # No approval => no live DB or transport.
    provider = V6OnlyProvider(proposal['configuration']); provider.validate()
    store = Staging(STAGING, policy)
    try:
        provider.pacer = SharedLLMPacer(store.db, provider.rate_limits['request'], provider.rate_limits['token'])
        execute_cases(proposal, policy, store, provider, authorize=lambda: approved_policy(proposal))
    finally:
        write_report(proposal, result_rows(proposal, store.db)); store.guard.close()
    print(REPORT)


if __name__ == '__main__':main()
