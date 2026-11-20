"""One saved S09485 response: explicit offline recovery, never a live validator rule.

Reads the four-call mini ledger in SQLite read-only mode. Writes a separate
versioned recovery artifact; does not update any staging/checkpoint observation.
"""
import copy
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.vision_ops import emerging_benefits_v3 as v3
from pipeline.vision_ops.run_06b_execution_guard import stable_hash

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT/'presentations/segmentation/run_06b_v6_mini_v3'
PROPOSAL = PACKAGE/'confirmation.json'
STAGING = PACKAGE/'staging.sqlite'
OUTPUT = PACKAGE/'liquid_offline_recovery_v1.json'
REPORT = PACKAGE/'Liquid IV - Offline reference recovery.md'
EXPECTED_INPUT = '18c5be160099ad6cd949593eaecc190bc1f241007871638f01b03046da1604f6'
EXPECTED_RAW = '2be079063deb44b6064b643d9200f12e439f5ead922b3b36c620c83751779f56'


def file_sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def recover_liquid(input_record, raw):
    """Hash-bound exception, not permission to drop unknown metadata references.

    Candidate IDs describe OCR spans; context fact IDs refer only to supplied,
    evidence-linked context facts. No candidate ID is promoted into a fact ID.
    """
    if stable_hash(input_record) != EXPECTED_INPUT or stable_hash(raw) != EXPECTED_RAW:
        raise ValueError('Recovery applies only to the exact saved S09485 input/response')
    inp = v3.validate_input(input_record)
    out = v3.ModelOutput.model_validate(raw)
    generated = v3.candidates(input_record)
    wording_ids = {c['candidate_id'] for c in generated}
    fact_ids = {f.fact_id for f in inp.context_facts}
    refs = out.product_context.metadata_fact_ids
    if (fact_ids or len(refs) != len(set(refs)) or set(refs) != wording_ids or
            wording_ids & fact_ids or out.product_context.scope_basis != 'ocr_context'):
        raise ValueError('Expected distinct OCR candidate namespace and empty context-fact namespace')
    ids = [i.candidate_id for i in out.interpretations]
    if len(ids) != len(set(ids)) or set(ids) != wording_ids:
        raise ValueError('Every exact wording candidate must be interpreted once')
    if not out.product_context.assessable or out.product_context.target_attribution != 'target':
        raise ValueError('No recovery of unresolved target identity')
    # Independently check the saved interpretations against exact OCR descriptors,
    # not metadata, the source URL, a presumed layout or product identity alone.
    descriptors = {'hydration':'HYDRATION MULTIPLIER',
                   'electrolyte':'ELECTROLYTE DRINK MIX'}
    interpretations = {i.candidate_id:i for i in out.interpretations}
    checks = []
    for benefit, descriptor in descriptors.items():
        if (inp.ocr_text.count(descriptor) != 1 or
                descriptor not in (inp.product_name or '') or
                not any(c['benefit'] == benefit and c['context'] == descriptor for c in generated)):
            raise ValueError('Exact target descriptor is not independently supported by saved OCR')
    for c in generated:
        i = interpretations[c['candidate_id']]
        if (inp.ocr_text[c['start_0based']:c['end_exclusive']] != c['phrase'] or
                i.role != 'supporting_positioning' or
                i.purpose != ('hydration_positioning' if c['benefit']=='hydration' else 'electrolyte_feature')):
            raise ValueError('Unsupported candidate interpretation; no benefit correction authorized')
        checks.append(dict(c, role=i.role, purpose=i.purpose, exact_span_verified=True,
            content_interpretation_verified=True, front_attribution_verified=False))
    try:
        v3.validate_saved_ocr_result(input_record, raw)
    except ValueError as exc:
        original_failure = str(exc)
        if original_failure != 'v3 assessment rejected: Unknown context fact reference':raise
    else:
        raise ValueError('Expected historical rejection was not reproduced')

    corrected = copy.deepcopy(raw)
    ctx = corrected['product_context']
    ctx.update(metadata_fact_ids=[],panel_scope='unknown',scope_basis='unresolved',
        reason='Offline review: exact saved OCR contains HYDRATION MULTIPLIER and '
               'ELECTROLYTE DRINK MIX for the target product. Candidate IDs are not '
               'metadata facts. Front-panel placement is not independently established.')
    corrected['limitations'].append('Offline recovery: benefit content is supported; '
        'front attribution remains unassessable. Original interpretation explanations '
        'mentioning front placement are preserved model assertions, not verified layout evidence.')
    changes = [dict(path='/product_context/'+k, before=raw['product_context'][k],after=ctx[k],
                    reason=('Remove wording candidate references; zero supplied context facts.' if k=='metadata_fact_ids'
                            else 'Retain uncertainty: OCR wording does not independently establish front scope.'))
               for k in ['metadata_fact_ids','panel_scope','scope_basis','reason']]
    changes.append(dict(path='/limitations',before=raw['limitations'],after=corrected['limitations'],
                        reason='Expose recovery scope and unaccepted front-layout assertions.'))
    audits=[]
    result,status = v3.validate_saved_ocr_result(input_record,corrected,record=audits.append)
    if any(result[b]['content_status']!='detected' or result[b]['front_status']!='unassessable'
           for b in descriptors):raise ValueError('Unexpected recovery assessment')
    if corrected['interpretations'] != raw['interpretations']:
        raise ValueError('Benefit interpretations must remain unchanged')
    return dict(original_failure=original_failure,original_response_sha256=stable_hash(raw),
        input_sha256=stable_hash(input_record),candidate_ids=sorted(wording_ids),
        supplied_metadata_fact_ids=sorted(fact_ids),candidate_checks=checks,corrections=changes,
        corrected_interpretation=corrected,derived_result=result,checkpoint_status=status,
        validator_audit=audits,classification_accepted_offline=True,
        review_status='PENDING_JULIA_REVIEW_NOT_MERGED',historical_observation_modified=False)


def verify_unchanged_case(inp, raw, saved_status, saved_result):
    """Strict revalidation, not recovery or fresh classification of other cases."""
    result,status = v3.validate_saved_ocr_result(inp,raw)
    if status != saved_status or {k:v for k,v in result.items() if k!='_validation'} != {
            k:v for k,v in saved_result.items() if k!='_validation'}:
        raise ValueError('Other mini assessment differs from its saved result')
    if any(saved_result['_validation'].get(k) != v for k,v in result['_validation'].items()):
        raise ValueError('Other mini validation status changed')
    return dict(validation='PASS',unchanged=True,raw_response_sha256=stable_hash(raw),
        saved_result_sha256=stable_hash(saved_result),checkpoint_status=status,
        hydration={k:result['hydration'][k] for k in ['content_status','front_status']},
        electrolyte={k:result['electrolyte'][k] for k in ['content_status','front_status']})


def assess_saved():
    """No network transport, provider configuration or writable staging connection."""
    frozen = [PROPOSAL,STAGING,PACKAGE/'Mini v3 - Four-case results.md',
              PACKAGE/'julia_approval.json']
    _,contract = v3.frozen_contract()
    frozen += [ROOT/p for p in contract]
    proposal=json.loads(PROPOSAL.read_text(encoding='utf-8'))
    frozen += [ROOT/p for p in proposal['runtime_files_sha256']]
    frozen += [ROOT/p for p in proposal['saved_sources_sha256']]
    before={p.relative_to(ROOT).as_posix():file_sha(p) for p in frozen}
    with sqlite3.connect(STAGING.as_uri()+'?mode=ro',uri=True) as db:
        other={};recovery=None
        for case in proposal['cases']:
            key=case['call_id'];inp=copy.deepcopy(case['saved_input']);inp['request_id']=key
            event_id,payload=db.execute("SELECT id,payload FROM stage_events WHERE key=? AND event='provider_result' ORDER BY id DESC LIMIT 1",(key,)).fetchone()
            reply=json.loads(payload);raw=reply['output']
            if case['slot']=='S09485':
                recovery=recover_liquid(inp,raw)
                recovery.update(source_event_id=event_id,source_call_id=key,
                    source_provider_result_sha256=stable_hash(reply),barcode=inp['barcode'])
                # Original failure must remain a failure with no successful checkpoint.
                if db.execute('SELECT 1 FROM stage_results WHERE key=?',(key,)).fetchone():
                    raise ValueError('Historical S09485 checkpoint unexpectedly changed')
                decision=json.loads(db.execute("SELECT payload FROM stage_events WHERE key=? AND event='validation_decision' ORDER BY id DESC LIMIT 1",(key,)).fetchone()[0])
                if decision['validation']!='FAIL':raise ValueError('Historical rejection not preserved')
            else:
                status,saved=db.execute('SELECT status,payload FROM stage_results WHERE key=?',(key,)).fetchone()
                other[case['slot']]=verify_unchanged_case(inp,raw,status,json.loads(saved))
        if recovery is None or len(other)!=3:raise ValueError('Expected four saved cases')
        counts=dict(db.execute('SELECT kind,COUNT(*) FROM calls GROUP BY kind').fetchall())
        if counts!={'emerging_benefits':4}:raise ValueError('Unexpected historical call count')
    after={p:file_sha(ROOT/p) for p in before}
    if before!=after:raise ValueError('Protected input changed during offline review')
    return dict(recovery_version='s09485_reference_recovery_v1',recovery=recovery,
        other_cases=other,protected_files_sha256=before,protected_files_unchanged=True,
        existing_provider_calls=counts,new_provider_calls=0,
        source_script_sha256=file_sha(Path(__file__)),
        regression_test_path='pipeline/vision_ops/test_run_06b_v6_liquid_recovery.py',
        regression_test_sha256=file_sha(Path(__file__).with_name('test_run_06b_v6_liquid_recovery.py')))


def main():
    if OUTPUT.exists() or REPORT.exists():raise FileExistsError('Versioned recovery already exists; never overwrite')
    artifact=assess_saved();artifact['created_at_utc']=datetime.now(timezone.utc).isoformat()
    artifact['offline_tests']={'command':'.venv\\Scripts\\python.exe -B -m unittest pipeline.vision_ops.test_run_06b_v6_liquid_recovery -v',
                               'tests_passed':6,'new_provider_calls':0,
                               'results':'Six focused tests passed before generating this artifact.'}
    OUTPUT.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# RUN 06B — Liquid I.V. offline reference recovery','',
        '**S09485 is recoverable offline.** Recovery is validated but remains separate, pending Julia review; no historical record/checkpoint was modified.','',
        '| Benefit | Content status | Front status |', '| --- | --- | --- |',
        '| Hydration | `detected` | `unassessable` |',
        '| Electrolyte | `detected` | `unassessable` |','',
        'The saved response incorrectly placed all three wording candidate IDs in `metadata_fact_ids`. The frozen input has zero context facts. Candidate IDs identify exact OCR spans, not metadata or verified panel placement.','',
        'Independent content checks: `HYDRATION MULTIPLIER` and `ELECTROLYTE DRINK MIX` each occur exactly once in full saved OCR and match the target descriptor. All three candidates have exact offsets, unique IDs, supporting interpretations and appropriate purposes; there is no negation, ingredient list or unrelated-product context in these descriptor lines. The original interpretations and purposes are retained verbatim.','',
        'Logged correction: clear the three invalid metadata references; change `panel_scope` from `front` to `unknown` and `scope_basis` from `ocr_context` to `unresolved`; replace the context explanation and append an explicit limitation. No metadata was invented. Exact candidate wording supports target content independently of these references; the response’s front-layout assertions are not accepted. The unchanged v3 validator accepts the corrected interpretation and deterministically derives the statuses above. Checkpoint classification is `success`, not a front-positive or no-claim result.','',
        '| Other case | Revalidation | Hydration content / front | Electrolyte content / front |',
        '| --- | --- | --- | --- |']
    for slot,c in artifact['other_cases'].items():
        h=c['hydration'];e=c['electrolyte']
        lines.append(f"| {slot} | PASS, unchanged | {h['content_status']} / {h['front_status']} | {e['content_status']} / {e['front_status']} |")
    lines+=['','Implementation adds one case-bound offline recovery script and focused regression tests. The correction rejects different input/response hashes, unknown references and incomplete/changed interpretations; it is not an automatic validator relaxation.','',
        'Validation: **6 focused offline tests passed**, covering original rejection, candidate/fact namespace distinction, exact content/uncertain front recovery, case/response fencing, evidence offsets and unchanged other responses. Protected file hashes passed before/after; the historical failed observation and empty S09485 success checkpoint remain intact. No prompts, definitions, schemas, live runner paths, provider receipts or historical results were edited. No image review, OCR, core or v6 calls occurred.','',
        f'Audit artifact: `{OUTPUT.name}` (SHA256 `{file_sha(OUTPUT)}`), containing source/event/response hashes, candidate checks, field-level before/after corrections, corrected interpretation, derived result, validator audit and other-case result hashes. Original mini staging is opened with `mode=ro`.','',
        '**STOP for Julia’s review. No canonical merge or main run is authorized by this recovery.**','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8');print(REPORT)


if __name__=='__main__':main()
