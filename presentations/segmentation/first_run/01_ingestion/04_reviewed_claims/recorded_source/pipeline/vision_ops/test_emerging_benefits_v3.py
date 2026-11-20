"""Bounded offline fixtures only. Authored interpretations are not model results."""
import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.vision_ops import emerging_benefits_v3 as v3
from pipeline.vision_ops.run_06b_runner import Runner, Staging, AzureProvider, KINDS, stable_hash, sha, core_reuse_configuration_sha, response_layers

ROOT = Path(__file__).resolve().parents[2]
FOUR = ROOT / 'presentations/segmentation/run_06b_v6_confirmation_v1'


def authored(inp, *, target='target', panel='front', assessable=True, roles=None, additional=None):
    """Hand-authored expected interpretation helper, never an inferred result."""
    rows=[]
    for c in v3.candidates(inp):
        role=(roles or {}).get(c['candidate_id'],'supporting_positioning')
        rows.append(dict(candidate_id=c['candidate_id'],role=role,purpose=None,reason='Hand-authored fixture interpretation'))
    return dict(schema_version='emerging_benefits_interpretations_v3',request_id=inp['request_id'],
        product_context=dict(assessable=assessable,target_attribution=target,panel_scope=panel,
            scope_basis='unresolved' if target!='target' else 'ocr_context',metadata_fact_ids=[],
            reason='Hand-authored context, not a model prediction or image review'),
        interpretations=rows,additional_wording=additional or [],limitations=[])


class V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block=patch('requests.sessions.Session.request',side_effect=AssertionError('No network'))
        cls.block.start()
        p=json.loads((FOUR/'confirmation.json').read_text(encoding='utf-8'))
        cls.cases={c['slot']:c for c in p['cases']}
        cls.fixtures=json.loads((ROOT/'presentations/segmentation/emerging_benefits_prompt_v1/contract_fixtures.json').read_text(encoding='utf-8'))
        cls.by_id={f['fixture_id']:f for f in cls.fixtures}
        cls.source=ROOT/'presentations/segmentation/run_06b_pilot_launch_v1/pilot_configuration.json'
        cls.oldconfig=json.loads(cls.source.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):cls.block.stop()

    def config(self):
        value=copy.deepcopy(self.oldconfig)
        value.update(emerging_prompt_version=v3.PROMPT_VERSION,emerging_contract_sha256=v3.frozen_contract()[1],
            configuration_version='synthetic_v3_offline',status='NOT_AUTHORIZED',
            core_ocr_reuse_configuration={'path':self.source.relative_to(ROOT).as_posix(),'sha256':sha(self.source.read_bytes())})
        return value

    def store(self):
        policy=dict(execution_authorized=True,tariffs_validated=True,approval_sha256='SYNTHETIC_ONLY',
            manifest_sha256='SYNTHETIC_ONLY',attempt_cap=100,ceiling_nanochf=100_000_000,
            worst_case_nanochf_per_call={k:10_000_000 for k in KINDS},max_calls_per_job={k:1 for k in KINDS})
        return Staging(':memory:',policy),policy

    def test_frozen_patterns_exact_candidates_all_existing_fixture_texts(self):
        for fixture in self.fixtures:
            inp=fixture['input'];text=inp['ocr_text'] or '';candidates=v3.candidates(inp)
            self.assertEqual(candidates,v3.candidates(inp))
            self.assertEqual(len({c['candidate_id'] for c in candidates}),len(candidates))
            for c in candidates:self.assertEqual(text[c['start_0based']:c['end_exclusive']],c['phrase'])
        tail=v3.candidates(self.by_id['tail_beyond_2000']['input'])
        self.assertTrue(tail);self.assertTrue(all(c['start_0based']>2000 for c in tail))
        self.assertIs(v3.PATTERNS['hydration'],__import__('pipeline.vision_ops.validate_emerging_benefits_v1',fromlist=['H_WORDING']).H_WORDING)

    def test_four_saved_cases_liquid_both_content_front_unknown(self):
        for slot,case in self.cases.items():
            inp=case['saved_input'];before=copy.deepcopy(inp)
            wire=v3.model_input(inp);self.assertEqual(wire['ocr_text'],inp['ocr_text'])
            raw=authored(inp,target='target' if slot=='S09485' else 'unresolved',panel='unknown',assessable=slot!='S09587')
            out,status=v3.validate_saved_ocr_result(inp,raw)
            self.assertTrue(out['_validation']['classification_accepted'])
            self.assertEqual(inp,before)
            for name in ['hydration','electrolyte']:
                self.assertEqual(out[name]['front_status'],'unassessable')
                self.assertEqual(out[name]['content_status'],'detected' if slot=='S09485' else 'unassessable')
            self.assertEqual(status,'success')

    def test_known_candidates_cannot_be_omitted_duplicated_or_replaced(self):
        inp=self.cases['S09485']['saved_input'];good=authored(inp)
        for mode in ['missing','duplicate','unknown']:
            bad=copy.deepcopy(good)
            if mode=='missing':bad['interpretations'].pop()
            elif mode=='duplicate':bad['interpretations'].append(copy.deepcopy(bad['interpretations'][0]))
            else:bad['interpretations'][0]['candidate_id']='invented'
            audits=[]
            with self.assertRaises(ValueError):v3.validate_saved_ocr_result(inp,bad,record=audits.append)
            self.assertEqual(audits[-1]['schema_validation'],'PASS')
            self.assertFalse(audits[-1]['classification_accepted'])

    def test_ordinary_or_unresolved_known_wording_never_becomes_negative(self):
        inp=self.cases['S09485']['saved_input']
        for role in ['ordinary_category','mineral_only','ambiguous_wording']:
            roles={c['candidate_id']:role for c in v3.candidates(inp)}
            out,_=v3.validate_saved_ocr_result(inp,authored(inp,roles=roles))
            self.assertTrue(all(out[n]['content_status']=='ambiguous' for n in v3.PATTERNS))
        out,_=v3.validate_saved_ocr_result(inp,authored(inp,target='unresolved',panel='unknown'))
        self.assertTrue(all(out[n]['content_status']=='ambiguous' for n in v3.PATTERNS))

    def test_existing_taste_replenisher_french_and_negative_controls(self):
        for name in ['taste','replenisher_context','French_positive','identity_OCR_supported','mineral_only','identity_not_evidence']:
            inp=self.by_id[name]['input'];raw=authored(inp)
            if name=='taste':
                for i in raw['interpretations']:i['purpose']='taste'
            out,_=v3.validate_saved_ocr_result(inp,raw)
            for benefit in v3.PATTERNS:
                self.assertEqual(out[benefit]['content_status'],self.by_id[name]['authored_output'][benefit]['content_status'])
            if name=='taste':self.assertEqual(out['electrolyte']['purpose'],'taste');self.assertEqual(out['hydration']['content_status'],'not_detected')

    def test_negated_ingredient_back_and_unrelated_roles(self):
        for name,role in [('negated','negated_wording'),('ingredient_only','ingredient_mention'),('background','unrelated_product_wording')]:
            inp=self.by_id[name]['input'];raw=authored(inp,roles={c['candidate_id']:role for c in v3.candidates(inp)})
            out,_=v3.validate_saved_ocr_result(inp,raw)
            self.assertEqual(out['electrolyte']['content_status'],'not_detected')
        inp=self.by_id['back_feature']['input'];cs=v3.candidates(inp)
        roles={c['candidate_id']:('ingredient_mention' if 'INGREDIENTS' in c['context'] else 'back_panel_feature') for c in cs}
        out,_=v3.validate_saved_ocr_result(inp,authored(inp,panel='back',roles=roles))
        self.assertEqual(out['electrolyte']['content_status'],'detected')
        self.assertEqual(out['electrolyte']['front_status'],'unassessable')

    def test_additional_wording_is_exact_review_only_not_new_positive(self):
        inp=self.by_id['identity_not_evidence']['input']
        raw=authored(inp,additional=[dict(benefit='hydration',phrase='WATER',reason='Synthetic review flag only')])
        out,_=v3.validate_saved_ocr_result(inp,raw)
        self.assertEqual(out['hydration']['content_status'],'ambiguous')
        self.assertFalse(out['additional_wording_review'][0]['accepted_positive'])
        raw['additional_wording'][0]['phrase']='invented words'
        with self.assertRaises(ValueError):v3.validate_saved_ocr_result(inp,raw)

    def test_model_cannot_supply_statuses_quotes_or_offsets(self):
        inp=self.cases['S09485']['saved_input'];raw=authored(inp)
        for field in ['content_status','front_status','phrase','start_0based']:
            invalid=copy.deepcopy(raw);invalid['interpretations'][0][field]='invented'
            audit=[]
            with self.assertRaises(ValueError):v3.validate_saved_ocr_result(inp,invalid,record=audit.append)
            self.assertEqual(audit[-1]['schema_validation'],'FAIL')

    def test_real_v1_v2_results_are_not_relabelled_as_v3_predictions(self):
        before=sha((FOUR/'staging.sqlite').read_bytes());count=0
        with sqlite3.connect((FOUR/'staging.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            for key,payload in db.execute("select key,payload from stage_events where event='dispatch'"):
                dispatch=json.loads(payload);slot=dispatch['slot'];record=db.execute("select payload from stage_events where key=? and event='provider_result'",(key,)).fetchone()
                raw=json.loads(record[0])['output'];original=copy.deepcopy(raw)
                with self.assertRaises(ValueError):v3.validate_saved_ocr_result(self.cases[slot]['saved_input'],raw)
                self.assertEqual(raw,original);count+=1
        self.assertEqual(count,4);self.assertEqual(sha((FOUR/'staging.sqlite').read_bytes()),before)

    def test_v6_only_config_changes_keep_original_ocr_core_and_dairy_keys(self):
        cfg=self.config();self.assertEqual(core_reuse_configuration_sha(cfg),stable_hash(self.oldconfig))
        store,policy=self.store();runner=Runner([self.cases['S09485']['row']],'SYNTHETIC_ONLY',cfg,policy,store,FakeProvider())
        row=self.cases['S09485']['row'];source=self.cases['S09485']['saved_input']['ocr_sha256']
        old=object.__new__(Runner);old.config=self.oldconfig;old.config_sha=stable_hash(self.oldconfig)
        for kind in ['ocr','core','dairy_review','dairy_reextract']:
            self.assertEqual(runner.key(row,kind,source),old.key(row,kind,source))
        self.assertNotEqual(runner.key(row,'emerging_benefits',source),old.key(row,'emerging_benefits',source))
        cfg['v6_max_output_tokens']=1900
        self.assertEqual(core_reuse_configuration_sha(cfg),stable_hash(self.oldconfig))
        for field,value in [('temperature',.5),('core_llm_ocr_input_character_cap',1000)]:
            bad=copy.deepcopy(cfg);bad[field]=value
            with self.assertRaises(PermissionError):core_reuse_configuration_sha(bad)
        store.guard.close()

    def test_existing_saved_ocr_core_reused_and_one_v3_call_then_resume(self):
        original=json.loads((ROOT/'presentations/segmentation/run_06b_pilot_recovery_v1/saved_pilot_regression_fixtures.json').read_text(encoding='utf-8'))
        store,policy=self.store();provider=FakeProvider()
        rows=[self.cases[s]['row'] for s in self.cases]
        runner=Runner(rows,'SYNTHETIC_ONLY',self.config(),policy,store,provider)
        for row in rows:
            fixture=next(f for f in original if f['row']==row)
            for kind in ['ocr','core']:
                result=fixture['stages'][kind]['result'];source=None if kind=='ocr' else self.cases[row['proposed_primary_slot_id']]['saved_input']['ocr_sha256']
                store.finish(runner.key(row,kind,source),kind,result['status'],result['payload'])
            outcome=runner.run_row(row);self.assertTrue(outcome['v6']['_validation']['classification_accepted'])
            if row['proposed_primary_slot_id']=='S00006':
                self.assertFalse(runner.row_checks(row,outcome)['core_accepted'])  # Existing HOLD remains a HOLD, without reprocessing.
            runner.run_row(row)
        self.assertEqual(provider.kinds,['emerging_benefits']*4)
        store.guard.close()

    def test_core_failure_still_one_v3_call_and_other_categories_no_v3(self):
        case=self.cases['S09485'];row=case['row'];store,policy=self.store();provider=FakeProvider()
        runner=Runner([row],'SYNTHETIC_ONLY',self.config(),policy,store,provider)
        store.finish(runner.key(row,'ocr'),'ocr','success',{'text':case['saved_input']['ocr_text']})
        original_call=provider.call;attempts=[]
        def fail_core(kind,row,body,event):
            if kind=='core':attempts.append(kind);raise TimeoutError('Synthetic core timeout')
            return original_call(kind,row,body,event)
        provider.call=fail_core
        self.assertTrue(runner.run_row(row)['v6']['_validation']['classification_accepted'])
        runner.run_row(row)
        self.assertEqual(attempts,['core']);self.assertEqual(provider.kinds,['emerging_benefits'])
        store.guard.close()
        fixtures=json.loads((ROOT/'presentations/segmentation/run_06b_pilot_recovery_v1/saved_pilot_regression_fixtures.json').read_text(encoding='utf-8'))
        for category in ['snacks','cereals','dairies']:
            f=next(f for f in fixtures if f['row']['category']==category and f['stages']['core']['result'] and
                f['stages']['core']['result']['payload']['image_context']=='front_of_pack')
            store,policy=self.store();provider=FakeProvider();row=f['row']
            runner=Runner([row],'SYNTHETIC_ONLY',self.config(),policy,store,provider)
            source=hashlib.sha256(f['ocr'].encode()).hexdigest()
            for kind in ['ocr','core']:
                r=f['stages'][kind]['result'];store.finish(runner.key(row,kind,None if kind=='ocr' else source),kind,r['status'],r['payload'])
            self.assertIsNone(runner.run_row(row)['v6']);self.assertEqual(provider.kinds,[])
            store.guard.close()

    def test_reporting_does_not_equate_http200_with_accepted_classification(self):
        self.assertEqual(response_layers({'raw':{'status_code':200},'json_parse_status':'FAIL','output':None}),{'http_status':200,'json_parse':'FAIL'})
        inp=self.cases['S09485']['saved_input'];audit=[]
        bad=authored(inp);bad['interpretations']=[]
        with self.assertRaises(ValueError):v3.validate_saved_ocr_result(inp,bad,record=audit.append)
        self.assertEqual(audit[0]['schema_validation'],'PASS');self.assertFalse(audit[0]['classification_accepted'])

    def test_transport_parsing_and_schema_are_separate(self):
        from unittest.mock import Mock
        for text,expected in [('{','FAIL'),('null','PASS'),('{}','PASS')]:
            provider=object.__new__(AzureProvider);provider.openai='https://offline.invalid';provider.lkey='SYNTHETIC'
            provider.config={'provider':{'response_model':'gpt-4.1-nano-2025-04-14'}}
            provider.pacer=SimpleNamespace(wait=lambda *a:None)
            response=SimpleNamespace(status_code=200,text='SYNTHETIC',headers={},raise_for_status=lambda:None,
                json=lambda:dict(model='gpt-4.1-nano-2025-04-14',id='synthetic',usage={'prompt_tokens':1,'completion_tokens':1},
                    choices=[dict(finish_reason='stop',message={'content':text})]))
            provider.http=SimpleNamespace(post=Mock(return_value=response))
            reply=provider.call('emerging_benefits',{}, {'response_format':{'type':'json_schema'}},lambda *a:None)
            self.assertEqual(response_layers(reply)['http_status'],200)
            self.assertEqual(reply['json_parse_status'],expected)
            self.assertEqual(provider.http.post.call_count,1)
            with self.assertRaises(ValueError):v3.validate_saved_ocr_result(self.cases['S09485']['saved_input'],reply['output'])

    def test_verified_nonfront_scope_cannot_be_overridden(self):
        inp=self.by_id['historical_front_not_truth']['input'];raw=authored(inp,panel='front')
        with self.assertRaises(ValueError):v3.validate_saved_ocr_result(inp,raw)
        raw=authored(inp,panel='back',roles={c['candidate_id']:'back_panel_feature' for c in v3.candidates(inp)})
        raw['product_context'].update(scope_basis='reliable_metadata',metadata_fact_ids=['review_scope'])
        out,_=v3.validate_saved_ocr_result(inp,raw)
        self.assertTrue(all(out[n]['front_status']=='unassessable' for n in v3.PATTERNS))

    def test_cli_returns_failure_and_stops_after_rejected_assessment(self):
        from pipeline.vision_ops import run_06b_runner as module
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC_v3_cli_',dir=ROOT/'pipeline/local_only') as directory:
            directory=Path(directory).resolve();assert directory.is_relative_to((ROOT/'pipeline/local_only').resolve())
            configpath=directory/'synthetic_config.json';policypath=directory/'synthetic_policy.json'
            configpath.write_text(json.dumps(self.config()),encoding='utf-8')
            policypath.write_text(json.dumps({'execution_authorized':True,'approval_sha256':'SYNTHETIC_ONLY',
                'manifest_sha256':'SYNTHETIC_ONLY','staging_path':str(ROOT/'presentations/segmentation/run_06b_execution_staging_v1/staging.sqlite'),
                'authorized_primary_slots':['S09485'],'ceiling_nanochf':1}),encoding='utf-8')
            runner=Mock();runner.run_row.return_value={};runner.row_checks.return_value={
                'http_status':200,'json_parse':'PASS','schema_validation':'PASS','classification_accepted':False,'accepted':False}
            with (patch('sys.argv',['runner','--execute','--configuration',str(configpath),'--policy',str(policypath)]),
                  patch.object(module,'load_manifest',return_value=[self.cases['S09485']['row']]),
                  patch.object(module,'Staging'),patch.object(module,'AzureProvider'),
                  patch.object(module,'Runner',return_value=runner),patch('sys.stdout',new_callable=io.StringIO) as printed):
                self.assertEqual(module.main(),1)
                self.assertIn('Assessment rejected',printed.getvalue())
                self.assertEqual(runner.run_row.call_count,1)


class FakeProvider:
    offline=True
    def __init__(self):self.kinds=[]
    def validate(self):pass
    def call(self,kind,row,body,event):
        if kind!='emerging_benefits':raise AssertionError('Existing OCR/core must not be re-executed')
        self.kinds.append(kind);inp=json.loads(body['messages'][1]['content'])
        clean={k:v for k,v in inp.items() if k!='candidates'}
        raw=authored(clean,target='target' if row['proposed_primary_slot_id']=='S09485' else 'unresolved',panel='unknown',assessable=row['proposed_primary_slot_id']!='S09587')
        return {'output':raw,'raw':{'status_code':200},'json_parse_status':'PASS'}


if __name__=='__main__':unittest.main(verbosity=2)
