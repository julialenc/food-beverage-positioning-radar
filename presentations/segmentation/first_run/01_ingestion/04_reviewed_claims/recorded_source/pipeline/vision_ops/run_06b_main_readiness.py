"""Final operational binding/preparation; no provider dispatch or sample selection."""
import argparse
import copy
import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from pipeline.vision_ops.run_06b_execution_guard import stable_hash, main_authorization_spec
from pipeline.vision_ops import emerging_benefits_v3 as v3

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'presentations/segmentation/run_06b_main_readiness_v1'
OLD=ROOT/'presentations/segmentation/run_06b_pilot_launch_v1'
MINI=ROOT/'presentations/segmentation/run_06b_v6_mini_v3'
CANONICAL=ROOT/'presentations/segmentation/run_06b_execution_staging_v1/staging.sqlite'
SAMPLE=ROOT/'presentations/segmentation/run_06b_final_candidates_v1/proposed_primary_processing_manifest.csv'
CONFIG=OUT/'runtime_configuration.json'
POLICY=OUT/'main_policy.NOT_AUTHORIZED.json'
PROOF=OUT/'reconciliation.json'
REPORT=OLD/'Launch and readiness.md'


def sha_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def ro(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def mini_response_format(adapter,provider):
    if (adapter.PROMPT_VERSION!='emerging_benefits_v3' or
            provider['deployment']!='gpt-4.1-mini-v6-test' or
            provider['response_model']!='gpt-4.1-mini-2025-04-14' or not provider['deployment_verified']):
        raise PermissionError('Locked v3/mini stage routing required')
    meta=Path(provider['verification_source_path'])
    if sha_file(meta)!=provider['verification_source_sha256']:raise PermissionError('Mini metadata changed')
    m=read(meta)['metadata']
    if (m['model']['name']!='gpt-4.1-mini' or m['model']['version']!='2025-04-14' or
            m['name']!=provider['deployment'] or m['provisioningState']!='Succeeded'):
        raise PermissionError('Mini deployment identity mismatch')
    def compact(value):
        if isinstance(value,dict):return {k:compact(v) for k,v in value.items() if k!='title'}
        if isinstance(value,list):return [compact(v) for v in value]
        return value
    return {'type':'json_schema','json_schema':{'name':'emerging_benefits_interpretations_v3',
                                               'strict':True,'schema':compact(adapter.schema())}}


def load_reconciliation(config,rows,manifest_sha):
    b=config['main_reconciliation'];path=ROOT/b['path']
    if sha_file(path)!=b['sha256']:raise PermissionError('Reconciliation changed')
    proof=read(path)
    if proof['manifest_sha256']!=manifest_sha or proof['primary_rows_sha256']!=stable_hash(rows):
        raise PermissionError('Reconciliation does not cover exact frozen sample')
    for path,digest in proof['immutable_sources_sha256'].items():
        if sha_file(ROOT/path)!=digest:raise PermissionError('Reconciled source changed: '+path)
    return proof


def reuse_mini_result(runner,row,inp):
    reuse=runner.main_reconciliation['v6_reuse'].get(row['proposed_primary_slot_id'])
    if not reuse:return None
    normalize=lambda x:{k:v for k,v in x.items() if k!='request_id'}
    if (stable_hash(normalize(inp))!=reuse['input_without_request_id_sha256'] or
            stable_hash(row)!=reuse['row_sha256'] or
            runner.config['v6_provider']!=reuse['provider'] or
            runner.config['v6_max_output_tokens']!=reuse['max_output_tokens'] or
            runner.config['emerging_contract_sha256']!=reuse['contract_sha256']):
        raise PermissionError('Mini reuse evidence/configuration is not equivalent')
    result,status=v3.validate_saved_ocr_result(reuse['input'],reuse['interpretation'])
    if stable_hash(result)!=reuse['validated_result_sha256']:
        raise PermissionError('Mini reuse result differs from verified source')
    provenance={k:reuse[k] for k in ['source_call_id','source_path','source_event_id','recovery_path']}
    provenance.update(target_work_key=runner.key(row,'emerging_benefits',inp['ocr_sha256']),
                      status=status,no_new_paid_call=True,original_request_id_retained=True)
    result['_reuse_provenance']=provenance
    runner.staging.event(provenance['target_work_key'],'external_assessment_reused',provenance)
    return result  # No manufactured stage result, receipt or successful call.


def estimate_throughput(rows,proof):
    """Quota-based estimate from saved request sizes, not another processing run."""
    from pipeline.vision_ops.run_06b_rate_limit import pacing_tokens
    samples=defaultdict(list)
    with ro(CANONICAL) as db:
        for kind,payload in db.execute("SELECT c.kind,e.payload FROM stage_events e JOIN calls c ON c.call_id=e.key WHERE e.event='dispatch'"):
            event=json.loads(payload)
            if kind!='ocr':samples[(kind,event['row']['region'],event['row']['category'])].append(pacing_tokens(event['body']))
    nano=0
    for row in rows:
        if row['proposed_primary_slot_id'] in proof['pilot_core_keys']:continue
        values=samples[('core',row['region'],row['category'])]
        nano+=sum(values)/len(values)
    for kind in ['dairy_review','dairy_reextract']:
        values=[v for (k,_,_),vs in samples.items() if k==kind for v in vs]
        nano+=proof['workload']['remaining_dairy_products_subject_to_conditionals']*proof['cost_forecast']['measured_dairy_incidence'][kind]*sum(values)/len(values)
    with ro(MINI/'staging.sqlite') as db:
        mini=[pacing_tokens(json.loads(p[0])['body']) for p in db.execute("SELECT payload FROM stage_events WHERE event='dispatch'")]
    mini_minutes=proof['workload']['remaining_mini_v6_calls']*sum(mini)/len(mini)/200000
    nano_minutes=nano/44000
    lower=max(nano_minutes,mini_minutes)/60
    return dict(nano_verified_rpm=55,nano_verified_tpm=55000,nano_pacing_rpm=44,nano_pacing_tpm=44000,
        mini_verified_rpm=250,mini_verified_tpm=250000,mini_pacing_rpm=200,mini_pacing_tpm=200000,
        nano_quota_minutes=nano_minutes,mini_quota_minutes=mini_minutes,pacing_only_lower_bound_hours=lower,
        indicative_elapsed_hours=[math.ceil(lower*1.1),math.ceil(lower*1.4)],
        limitation='Quota-only estimate from saved rendered requests; indicative range adds 10-40% scheduling/latency allowance. OCR/API latency, long OCR text, 429 cooldowns, sleep and network outages can extend it. No measured full-run throughput claim.')


def prepare():
    from pipeline.vision_ops.run_06b_runner import Runner,LegacyContract,load_manifest,stage_tariffs,sha,priced_tokens,KINDS,core_reuse_configuration_sha
    if CONFIG.exists() or PROOF.exists():raise FileExistsError('Prepared package already exists; do not overwrite frozen proposals')
    OUT.mkdir(exist_ok=True)
    approved=read(SAMPLE.parent/'manifest.json');manifest_sha=approved['outputs_sha256'][SAMPLE.name]
    rows=load_manifest(SAMPLE,manifest_sha)
    if len(rows)!=11902:raise ValueError('Approved sample must contain 11902 records')
    old=read(OLD/'pilot_configuration.json');old_policy=read(OLD/'pilot_policy.json')
    pilot=csv_rows(ROOT/'presentations/segmentation/run_06b_runner_validation_v1/proposed_pilot_96.csv')
    by_slot={r['proposed_primary_slot_id']:r for r in rows}
    if len(pilot)!=96 or any(r!=by_slot.get(r['proposed_primary_slot_id']) for r in pilot):
        raise ValueError('Frozen pilot identities changed')
    mini=read(MINI/'confirmation.json');recovered=read(MINI/'liquid_offline_recovery_v1.json')
    core_register=ROOT/'presentations/segmentation/run_06b_pilot_recovery_v1/core_consistency_register.csv'
    overlays=csv_rows(core_register)
    holds={r['slot']:r for r in overlays if r['disposition']=='HOLD_STATUS_CONFLICT'}
    if len(holds)!=19 or any(by_slot[s]['barcode']!=r['barcode_exact'] for s,r in holds.items()):
        raise ValueError('Expected exact nineteen core HOLD overlays')
    config=copy.deepcopy(old)
    config.update(configuration_version='run06b_main_nano_mini_v1',status='PREPARED_NOT_AUTHORIZED',
        emerging_prompt_version='emerging_benefits_v3',emerging_contract_sha256=v3.frozen_contract()[1],
        core_ocr_reuse_configuration={'path':(OLD/'pilot_configuration.json').relative_to(ROOT).as_posix(),'sha256':sha_file(OLD/'pilot_configuration.json')},
        v6_provider=mini['configuration']['provider'],v6_tariffs=mini['configuration']['tariffs'])
    immutable=[ROOT/'presentations/segmentation/BEVERAGE FINAL - Implementation and lock.md',
        OLD/'pilot_configuration.json',OLD/'pilot_policy.json',
        ROOT/'presentations/segmentation/run_06b_runner_validation_v1/proposed_pilot_96.csv',
        core_register,MINI/'confirmation.json',MINI/'staging.sqlite',MINI/'liquid_offline_recovery_v1.json',
        ROOT/'presentations/segmentation/run_06b_v6_confirmation_v1/staging.sqlite']
    immutable += [ROOT/p for p in config['emerging_contract_sha256']]
    immutable += [Path(config[k]['verification_source_path']) for k in ['provider','v6_provider']]
    immutable += [Path(config[k]['source_path']) for k in ['tariffs','v6_tariffs']]
    # Source SHA binds historical meaning, not the append-only live ledger's future bytes.
    proof=dict(manifest_sha256=manifest_sha,primary_rows_sha256=stable_hash(rows),
        canonical_initial_sha256=sha_file(CANONICAL),core_hold_slots=holds,v6_reuse={},
        immutable_sources_sha256={p.relative_to(ROOT).as_posix():sha_file(p) for p in immutable})
    with ro(CANONICAL) as db,ro(MINI/'staging.sqlite') as md:
        saved_policy=json.loads(db.execute('SELECT payload FROM policy_payload ORDER BY rowid DESC LIMIT 1').fetchone()[0])
        if saved_policy!=old_policy:raise PermissionError('Canonical pilot policy differs from frozen binding')
        if db.execute('SELECT 1 FROM circuit_breaker').fetchone():raise PermissionError('Unresolved global circuit breaker')
        for case in mini['cases']:
            slot=case['slot'];row=by_slot[slot]
            if case['row']!=row:raise ValueError('Mini exact row mismatch')
            inp=copy.deepcopy(case['saved_input']);inp['request_id']=case['call_id']
            event_id,reply=md.execute("SELECT id,payload FROM stage_events WHERE key=? AND event='provider_result' ORDER BY id DESC LIMIT 1",(case['call_id'],)).fetchone()
            reply=json.loads(reply)
            if json.loads(reply['raw']['body'])['model']!=config['v6_provider']['response_model']:
                raise ValueError('Mini provider identity not evidenced')
            raw=reply['output'];recovery_path=None
            if slot=='S09485':
                rec=recovered['recovery']
                if stable_hash(raw)!=rec['original_response_sha256'] or stable_hash(inp)!=rec['input_sha256']:
                    raise ValueError('Recovery does not match saved observation')
                raw=rec['corrected_interpretation'];recovery_path=(MINI/'liquid_offline_recovery_v1.json').relative_to(ROOT).as_posix()
            result,status=v3.validate_saved_ocr_result(inp,raw)
            if slot=='S09485':
                if result!=recovered['recovery']['derived_result']:raise ValueError('Recovered derivation changed')
            else:
                original=md.execute('SELECT status,payload FROM stage_results WHERE key=?',(case['call_id'],)).fetchone()
                stored=json.loads(original[1])
                if status!=original[0] or any(result[k]!=stored[k] for k in result if k!='_validation'):
                    raise ValueError('Mini accepted observation changed')
            proof['v6_reuse'][slot]=dict(source_call_id=case['call_id'],source_event_id=event_id,
                source_path=(MINI/'staging.sqlite').relative_to(ROOT).as_posix(),recovery_path=recovery_path,
                input=inp,interpretation=raw,input_without_request_id_sha256=stable_hash({k:v for k,v in inp.items() if k!='request_id'}),
                row_sha256=stable_hash(row),provider=config['v6_provider'],max_output_tokens=config['v6_max_output_tokens'],
                contract_sha256=config['emerging_contract_sha256'],validated_result_sha256=stable_hash(result))
        proof['canonical_prior_policy_sha256']=stable_hash(saved_policy)
        # A lightweight Runner identity object avoids any staging mutation/provider work.
        identity=object.__new__(Runner);identity.config=old;identity.config_sha=stable_hash(old)
        identity.core_config_sha=identity.config_sha
        existing_ocr={};corekeys={};pilot_source={}
        for row in rows:
            key=identity.key(row,'ocr');existing=db.execute('SELECT payload FROM stage_results WHERE key=? AND kind=?',(key,'ocr')).fetchone()
            if existing:existing_ocr[row['proposed_primary_slot_id']]=json.loads(existing[0])
        for row in pilot:
            ocr=existing_ocr.get(row['proposed_primary_slot_id'])
            if not ocr:raise ValueError('Missing successful pilot OCR')
            source=sha(ocr['text'].encode());key=identity.key(row,'core',source)
            if not db.execute('SELECT 1 FROM calls WHERE call_id=? AND kind=?',(key,'core')).fetchone():raise ValueError('Pilot core key changed')
            corekeys[row['proposed_primary_slot_id']]=key;pilot_source[key]=row
        call_counts=dict(db.execute('SELECT kind,COUNT(*) FROM calls GROUP BY kind').fetchall())
        receipts=db.execute('SELECT SUM(actual_nanochf) FROM receipts').fetchone()[0]
        pending=db.execute('SELECT SUM(reserved_nanochf) FROM calls c LEFT JOIN receipts r USING(call_id) WHERE r.call_id IS NULL').fetchone()[0]
        usage=defaultdict(list)
        for kind,key,rawusage in db.execute('SELECT c.kind,c.call_id,r.usage_json FROM calls c JOIN receipts r USING(call_id)'):
            u=json.loads(rawusage)
            if kind=='core':
                row=pilot_source[key];usage[(kind,row['region'],row['category'])].append(u)
            elif kind in ['dairy_review','dairy_reextract']:usage[(kind,'ALL','dairy')].append(u)
        external=0
        for source in [MINI/'staging.sqlite',ROOT/'presentations/segmentation/run_06b_v6_confirmation_v1/staging.sqlite']:
            with ro(source) as external_db:
                external+=external_db.execute('SELECT COALESCE(SUM(COALESCE(r.actual_nanochf,c.reserved_nanochf)),0) FROM calls c LEFT JOIN receipts r USING(call_id)').fetchone()[0]
        proof['external_prior_exposure_nanochf']=external
        proof['pilot_core_keys']=corekeys
        ocr_remaining=len({identity.key(r,'ocr') for r in rows})-call_counts['ocr']
        core_remaining=len(rows)-call_counts['core']
        v6_remaining=sum(r['category']=='beverages' for r in rows)-len(proof['v6_reuse'])
        dairy_remaining=sum(r['category'] in ['dairy','dairies'] for r in rows)-sum(r['category'] in ['dairy','dairies'] for r in pilot)
        remaining_ocr_cost=ocr_remaining*config['tariffs']['ocr_nanochf']
        core_cost=0
        for row in rows:
            if row['proposed_primary_slot_id'] in corekeys:continue
            examples=usage[('core',row['region'],row['category'])]
            if not examples:raise ValueError('Missing measured pilot cell for forecast')
            core_cost+=sum(priced_tokens(u['prompt_tokens'],u['completion_tokens'],config['tariffs']) for u in examples)/len(examples)
        with ro(MINI/'staging.sqlite') as mini_db:
            mini_usages=[json.loads(r[0]) for r in mini_db.execute('SELECT usage_json FROM receipts')]
        v6_cost=v6_remaining*sum(priced_tokens(u['prompt_tokens'],u['completion_tokens'],config['v6_tariffs'],cached_tokens=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)) for u in mini_usages)/4
        dairy_cost=0;dairy_incidence={}
        for kind in ['dairy_review','dairy_reextract']:
            examples=usage[(kind,'ALL','dairy')];incidence=len(examples)/20;dairy_incidence[kind]=incidence
            dairy_cost+=dairy_remaining*incidence*sum(priced_tokens(u['prompt_tokens'],u['completion_tokens'],config['tariffs']) for u in examples)/len(examples)
        expected=(remaining_ocr_cost+core_cost+v6_cost+dairy_cost)/1e9
        proof['workload']=dict(primary_records=11902,pilot_records=96,not_yet_started_primary_records=11806,
            accepted_vacancies=98,total_distinct_ocr_units=ocr_remaining+call_counts['ocr'],
            completed_ocr_units=call_counts['ocr'],pilot_products_with_ocr=96,remaining_ocr_units=ocr_remaining,
            remaining_initial_core_calls=core_remaining,pilot_core_unresolved_429=8,
            pilot_core_analytical_holds=19,pilot_initial_core_unusable=4,pilot_dairy_rescued=1,
            remaining_mini_v6_calls=v6_remaining,pilot_mini_v6_remaining=16,mini_v3_reuse=4,
            remaining_dairy_products_subject_to_conditionals=dairy_remaining,
            historical_calls=call_counts,no_automatic_retries=True)
        proof['cost_forecast']=dict(currency='CHF',account_tariffs_verified=False,expected_remaining_chf=expected,
            remaining_components_chf={'ocr':remaining_ocr_cost/1e9,'core':core_cost/1e9,'mini_v6':v6_cost/1e9,'dairy_conditionals':dairy_cost/1e9},
            prior_canonical_settled_chf=receipts/1e9,prior_canonical_unresolved_reserved_chf=pending/1e9,
            prior_external_exposure_chf=external/1e9,expected_total_exposure_chf=expected+(receipts+pending+external)/1e9,
            measured_dairy_incidence=dairy_incidence,variation_allowance_fraction=0.25,
            proposed_aggregate_hard_ceiling_chf=math.ceil((expected*1.25+(receipts+pending+external)/1e9)/5)*5,
            limitation='Pilot cell means for nano; four mini cases are a limited OCR/length/context sample. Dairy incidence 1/20 for each stage is uncertain; no added retry allowance. Historical OCR price, public-model planning rates and CHF/USD=1 remain provisional, not invoiced prices.')
    proof['throughput']=estimate_throughput(rows,proof)
    write(PROOF,proof)
    config['main_reconciliation']={'path':PROOF.relative_to(ROOT).as_posix(),'sha256':sha_file(PROOF)}
    if core_reuse_configuration_sha(config)!=stable_hash(old):raise ValueError('Core identity migration failed')
    write(CONFIG,config)
    runtime=['pipeline/vision_ops/'+name+'.py' for name in ['run_06b_runner','run_06b_execution_guard','run_06b_rate_limit','run_06b_pilot_history','run_06b_main_readiness','run_06b_v6_liquid_recovery','emerging_benefits_v3','emerging_benefits_stage','validate_emerging_benefits_v1']]
    runtime+=['pipeline/stages/stage_10_extract_pack_claims.py','presentations/segmentation/run_06b_v6_contract_v3.json']
    policy=copy.deepcopy(old_policy)
    policy.update(execution_authorized=False,spending_mode='bounded_main_v3_mini',
        configuration_sha256=stable_hash(config),authorized_primary_slots=sorted(by_slot),
        approval_sha256=None,approval_record_path=None,authorization_valid_until_utc=None,
        ceiling_nanochf=proof['cost_forecast']['proposed_aggregate_hard_ceiling_chf']*10**9,
        history_receipt_path=str(OUT/'prepayment_history_receipt.json'),
        migration_from_policy_sha256=proof['canonical_prior_policy_sha256'],
        preserved_core_configuration_sha256=stable_hash(old),external_prior_exposure_nanochf=external,
        runtime_files_sha256={p:sha_file(ROOT/p) for p in runtime})
    for kind,maximum in [('core',800),('dairy_review',60),('dairy_reextract',800),('emerging_benefits',2000)]:
        t=stage_tariffs(config,kind)
        policy['worst_case_nanochf_per_call'][kind]=(32768+1024)*t['input_nanochf_per_token']+maximum*t['output_nanochf_per_token']
    write(POLICY,policy)
    print(json.dumps({'workload':proof['workload'],'cost':proof['cost_forecast']},indent=2))


def authorize(ceiling_chf,accept_provisional):
    """Only an explicit operator CLI action creates payment authorization."""
    if not accept_provisional:raise PermissionError('Explicit acceptance of provisional tariffs required')
    policy=read(POLICY);config=read(CONFIG)
    proof=load_reconciliation(config,csv_rows(SAMPLE),policy['manifest_sha256'])
    if stable_hash(config)!=policy['configuration_sha256']:raise PermissionError('Prepared configuration changed')
    for file,digest in policy['runtime_files_sha256'].items():
        if sha_file(ROOT/file)!=digest:raise PermissionError('Reviewed runtime changed')
    with ro(CANONICAL) as db:
        prior=db.execute('SELECT identity FROM policy ORDER BY rowid DESC LIMIT 1').fetchone()[0]
    if prior==policy['migration_from_policy_sha256'] and sha_file(CANONICAL)!=proof['canonical_initial_sha256']:
        raise PermissionError('Pilot ledger changed since reconciliation; do not overwrite preparation')
    amount=Decimal(ceiling_chf)*10**9
    if amount!=amount.to_integral_value() or amount<=0:raise ValueError('Positive exact CHF ceiling required')
    policy.update(execution_authorized=True,ceiling_nanochf=int(amount))
    now=datetime.now(timezone.utc);end=now+timedelta(days=7)
    a=dict(approved_by='Julia',execute_remaining_main_run=True,accept_provisional_tariffs=True,
           ceiling_nanochf=int(amount),authorization_spec_sha256=main_authorization_spec(policy),
           approved_at_utc=now.isoformat(),valid_until_utc=end.isoformat(),
           source='Explicit local CLI --authorize --ceiling-chf --accept-provisional-tariffs after Julia readiness review')
    approval=OUT/'julia_main_approval.json';authorized=OUT/'main_policy.AUTHORIZED.json'
    if approval.exists() or authorized.exists():raise FileExistsError('Existing authorization is preserved; use its resume command')
    write(approval,a);policy.update(approval_record_path=str(approval),approval_sha256=sha_file(approval),authorization_valid_until_utc=end.isoformat())
    write(authorized,policy);print(authorized)


def validate_main_startup(config,policy,rows):
    proof=load_reconciliation(config,rows,policy['manifest_sha256'])
    if policy.get('external_prior_exposure_nanochf')!=proof['external_prior_exposure_nanochf']:
        raise PermissionError('Prior confirmation spending omitted or changed')
    if policy.get('migration_from_policy_sha256')!=proof['canonical_prior_policy_sha256']:
        raise PermissionError('Unbound pilot policy migration')
    with ro(CANONICAL) as db:
        prior=db.execute('SELECT identity FROM policy ORDER BY rowid DESC LIMIT 1').fetchone()[0]
    if prior==proof['canonical_prior_policy_sha256'] and sha_file(CANONICAL)!=proof['canonical_initial_sha256']:
        raise PermissionError('Canonical pilot ledger changed since reviewed reconciliation')
    return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--authorize',action='store_true')
    parser.add_argument('--ceiling-chf');parser.add_argument('--accept-provisional-tariffs',action='store_true')
    parser.add_argument('--check-history',action='store_true',help='Read-only indexed history checks and saved-source receipt; no payment')
    args=parser.parse_args()
    if args.prepare and args.authorize:parser.error('Preparation does not authorize execution')
    if args.authorize:
        if not args.ceiling_chf:parser.error('Explicit ceiling required')
        authorize(args.ceiling_chf,args.accept_provisional_tariffs)
    elif args.prepare:prepare()
    elif args.check_history:
        from pipeline.vision_ops.run_06b_pilot_history import refresh
        p=read(POLICY);c=read(CONFIG)
        rows=csv_rows(SAMPLE)
        validate_main_startup(c,p,rows)
        receipt=refresh(ROOT,rows,p['manifest_sha256'],stable_hash(c),p['history_receipt_path'],c['main_reconciliation'])
        print(json.dumps({'checked_at_utc':receipt['checked_at_utc'],'new_ineligible_events':receipt['new_ineligible_events'],
                          'unresolved_matches':receipt['unresolved_matches'],'source_count':len(receipt['source_inventory'])}))
    else:print('Readiness only; use --prepare or explicit --authorize after review. No provider calls.')


if __name__=='__main__':main()
