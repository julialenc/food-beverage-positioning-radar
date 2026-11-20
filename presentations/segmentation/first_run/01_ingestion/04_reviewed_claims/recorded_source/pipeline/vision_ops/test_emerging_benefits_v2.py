"""Focused offline contract regressions; saved OCR/responses, no database scans."""
import copy
import json
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pipeline.vision_ops import emerging_benefits_v2 as v2
from pipeline.vision_ops import emerging_benefits_stage as v1
from pipeline.vision_ops.validate_emerging_benefits_v1 import validate_pair
from pipeline.vision_ops.run_06b_runner import Runner, Staging, AzureProvider, KINDS

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'presentations/segmentation/run_06b_pilot_recovery_v1/saved_pilot_regression_fixtures.json'


def assessment(**changes):
    value = dict(content_status='not_detected', front_status='not_detected',
        target_attribution='target', panel_scope='front', scope_basis='ocr_context',
        metadata_fact_ids=[], purpose=None, evidence=[], reason='No qualifying wording in the assessed text.')
    value.update(changes)
    return value


def result(inp, **changes):
    value = dict(schema_version='emerging_benefits_output_v2', prompt_version=v2.PROMPT_VERSION,
        definition_version='1.0.0', request_id=inp['request_id'], barcode=inp['barcode'],
        ocr_sha256=inp['ocr_sha256'], hydration=assessment(), electrolyte=assessment(), limitations=[])
    value.update(changes)
    return value


def input_for(text):
    return v1.build_input(barcode='0000123456789', product_name='Synthetic test drink',
        regions=['FR'], country_assignments=['FR'], ocr_text=text,
        source_reference='synthetic-offline-fixture', source_artifact_sha256=None,
        original_image_url=None, image_provenance_note='Synthetic text, no image inspected',
        prior_panel_context=None, prior_profile=None, request_id='synthetic')


def evidence(text, phrase, role='supporting_positioning'):
    start = text.index(phrase)
    return dict(phrase=phrase, start_0based=start, end_exclusive=start + len(phrase), role=role)


def positive(inp, front=False):
    out = result(inp)
    for name, phrase, purpose in [('hydration', 'HYDRATION', 'hydration_positioning'),
                                  ('electrolyte', 'ELECTROLYTE', 'electrolyte_feature')]:
        out[name] = assessment(content_status='detected', front_status='detected' if front else 'unassessable',
            panel_scope='front' if front else 'unknown', purpose=purpose,
            evidence=[evidence(inp['ocr_text'], phrase)], reason='Explicit qualifying descriptor in saved OCR.')
    return out


class V2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block = patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden'))
        cls.block.start()
        cls.fixtures = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cls.beverages = [f for f in cls.fixtures if f['row']['category'] == 'beverages']
        cls.config = json.loads((ROOT / 'presentations/segmentation/run_06b_pilot_launch_v1/pilot_configuration.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.block.stop()

    def saved(self, slot):
        fixture = next(f for f in self.beverages if f['row']['proposed_primary_slot_id'] == slot)
        stage = fixture['stages']['emerging_benefits']
        body = next(e['payload']['body'] for e in stage['events'] if e['event'] == 'dispatch')
        raw = next((e['payload'].get('output') for e in stage['events'] if e['event'] == 'provider_result'), None)
        return json.loads(body['messages'][1]['content']), raw

    def test_frozen_definitions_and_schema_shape_unchanged(self):
        old = v1.PROMPT.read_text(encoding='utf-8')
        new = v2.PROMPT.read_text(encoding='utf-8')
        start, end = 'APPROVED DEFINITIONS:', 'ATTRIBUTION, PANEL SCOPE AND UNCERTAINTY'
        self.assertEqual(old.split(start)[1].split(end)[0], new.split(start)[1].split(end)[0])
        self.assertLess(len(new), len(old))
        self.assertIn('"purpose": null', new)
        self.assertNotIn('"purpose": "hydration_positioning |', new)
        v1.frozen_contract(); v2.frozen_contract()
        self.assertEqual(json.loads(v2.SCHEMA.read_text(encoding='utf-8')), v2.output_schema())

    def test_all_twenty_saved_cases_preserve_raw_and_recovery_boundary(self):
        outcomes = []; raw_accepted = 0
        self.assertEqual(len(self.beverages), 20)
        for fixture in self.beverages:
            inp, raw = self.saved(fixture['row']['proposed_primary_slot_id'])
            before = copy.deepcopy(raw)
            if raw is None:
                outcomes.append('no_response'); continue
            try:
                validate_pair(inp, raw); raw_accepted += 1
            except ValueError:
                pass
            candidate, audit = v2.postprocess(inp, raw, recover_v1=True)
            self.assertEqual(raw, before)
            if candidate:
                outcomes.append('abstention')
                self.assertEqual(candidate['prompt_version'], 'emerging_benefits_v1')
                self.assertEqual(audit['postprocess_version'], 'emerging_benefits_v2')
                for name in ['hydration', 'electrolyte']:
                    self.assertEqual(candidate[name]['content_status'], 'unassessable')
                    self.assertEqual(candidate[name]['front_status'], 'unassessable')
            else:
                outcomes.append('hold'); self.assertTrue(audit['errors'])
        self.assertEqual(raw_accepted, 0)
        self.assertEqual(outcomes.count('abstention'), 16)
        self.assertEqual(outcomes.count('hold'), 3)
        self.assertEqual(outcomes.count('no_response'), 1)

    def test_liquid_iv_original_held_and_explicit_two_benefit_control(self):
        inp, raw = self.saved('S09485')
        self.assertIn('HYDRATION MULTIPLIER', inp['ocr_text'])
        self.assertIn('ELECTROLYTE DRINK MIX', inp['ocr_text'])
        candidate, audit = v2.postprocess(inp, raw, recover_v1=True)
        self.assertIsNone(candidate)
        self.assertTrue(any('negative status contradicts' in e for e in audit['errors']))
        # Hand-authored expected response, NOT a recovered/new model prediction.
        expected = positive(inp)
        expected['hydration']['evidence'] = [evidence(inp['ocr_text'], 'HYDRATION MULTIPLIER')]
        expected['electrolyte']['evidence'] = [evidence(inp['ocr_text'], 'ELECTROLYTE DRINK MIX')]
        valid, audit = v2.postprocess(inp, expected)
        self.assertFalse(audit['errors'])
        for name in ['hydration', 'electrolyte']:
            self.assertEqual(valid[name]['content_status'], 'detected')
            self.assertEqual(valid[name]['front_status'], 'unassessable')

    def test_four_states_and_front_scope(self):
        inp = input_for('HYDRATION ELECTROLYTE DRINK')
        self.assertIsNotNone(v2.postprocess(inp, positive(inp, front=True))[0])
        inp = input_for('WATER SODIUM MAGNESIUM')
        self.assertIsNotNone(v2.postprocess(inp, result(inp))[0])
        inp = input_for('REPLENISHER')
        out = result(inp, hydration=assessment(content_status='ambiguous', front_status='ambiguous',
            panel_scope='unknown', scope_basis='unresolved', purpose='unspecified',
            evidence=[evidence(inp['ocr_text'], 'REPLENISHER', 'ambiguous_wording')], reason='Descriptor context unresolved.'))
        out['electrolyte'] = assessment(content_status='unassessable', front_status='unassessable', panel_scope='unknown')
        self.assertIsNotNone(v2.postprocess(inp, out)[0])
        inp.update(ocr_text=None, ocr_sha256=None)
        a = assessment(content_status='unassessable', front_status='unassessable',
            target_attribution='unresolved', panel_scope='unknown', scope_basis='unresolved')
        self.assertIsNotNone(v2.postprocess(inp, result(inp, hydration=a, electrolyte=copy.deepcopy(a)))[0])

    def test_back_content_positive_and_unresolved_target_never_front_negative(self):
        inp = input_for('WITH ELECTROLYTES')
        out = result(inp, electrolyte=assessment(content_status='detected', front_status='unassessable',
            panel_scope='back', purpose='electrolyte_feature', evidence=[evidence(inp['ocr_text'], 'WITH ELECTROLYTES', 'back_panel_feature')]))
        self.assertIsNotNone(v2.postprocess(inp, out)[0])
        out['electrolyte']['front_status'] = 'not_detected'
        self.assertIsNone(v2.postprocess(inp, out)[0])
        inp = input_for('WATER'); out = result(inp)
        out['hydration'].update(target_attribution='unrelated', panel_scope='unknown')
        self.assertIsNone(v2.postprocess(inp, out)[0])

    def test_negative_negated_and_ingredient_wording_not_forced_positive(self):
        for text, role in [('NO ELECTROLYTES', 'negated_wording'), ('INGREDIENTS: citrate (electrolytes)', 'ingredient_mention')]:
            inp = input_for(text); out = result(inp)
            out['electrolyte']['evidence'] = [evidence(text, text, role)]
            self.assertIsNotNone(v2.postprocess(inp, out)[0])
        out['electrolyte'].update(content_status='detected', purpose='electrolyte_feature')
        self.assertIsNone(v2.postprocess(inp, out)[0])
        inp = input_for('NO ELECTROLYTES'); out = result(inp)
        out['electrolyte'].update(content_status='detected', front_status='detected',
            evidence=[evidence(inp['ocr_text'], inp['ocr_text'])])
        self.assertIsNone(v2.postprocess(inp, out)[0])

    def test_taste_does_not_imply_hydration_and_purpose_conflicts_hold(self):
        inp = input_for('electrolytes added for taste'); out = result(inp)
        out['electrolyte'].update(content_status='detected', front_status='detected', purpose='taste', evidence=[evidence(inp['ocr_text'], inp['ocr_text'])])
        self.assertIsNotNone(v2.postprocess(inp, out)[0])
        out['electrolyte']['purpose'] = 'hydration_positioning'
        self.assertIsNone(v2.postprocess(inp, out)[0])

    def test_benefits_remain_independent_when_the_other_is_negated(self):
        inp = input_for('HYDRATION WITHOUT ELECTROLYTES'); out = result(inp)
        out['hydration'].update(content_status='detected',front_status='detected',purpose='hydration_positioning',
            evidence=[evidence(inp['ocr_text'],inp['ocr_text'])])
        out['electrolyte'].update(evidence=[evidence(inp['ocr_text'],'WITHOUT ELECTROLYTES','negated_wording')],
            reason='The drink supports hydration positioning, without an electrolyte proposition.')
        self.assertIsNotNone(v2.postprocess(inp,out)[0])

    def test_null_normalized_only_when_safe_and_audit_is_recorded(self):
        inp = input_for('WATER'); out = result(inp); out['hydration']['purpose'] = 'null'
        original = copy.deepcopy(out); records = []
        valid, _ = v2.validate_saved_ocr_result(inp, out, record=records.append)
        self.assertIsNone(valid['hydration']['purpose']); self.assertEqual(out, original)
        self.assertTrue(records[0]['corrections'])
        inp = input_for('HYDRATION ELECTROLYTE'); out = positive(inp); out['hydration']['purpose'] = 'null'
        with self.assertRaises(ValueError):v2.validate_saved_ocr_result(inp, out, record=records.append)
        self.assertTrue(records[-1]['errors'])

    def test_exact_offsets_unicode_and_unique_repair_only(self):
        inp = input_for('é 🥤 HYDRATION ELECTROLYTE'); out = positive(inp)
        out['hydration']['evidence'][0].update(start_0based=0, end_exclusive=0)
        valid, audit = v2.postprocess(inp, out)
        self.assertTrue(audit['corrections']); self.assertEqual(valid['hydration']['evidence'][0]['start_0based'], 4)
        out['hydration']['evidence'][0]['phrase'] = 'Hydration'
        self.assertIsNone(v2.postprocess(inp, out)[0])
        inp = input_for('HYDRATION HYDRATION ELECTROLYTE'); out = positive(inp)
        self.assertIsNotNone(v2.postprocess(inp, out)[0])  # Valid repeated quote offset is retained.
        out['hydration']['evidence'][0].update(start_0based=1, end_exclusive=2)
        self.assertIsNone(v2.postprocess(inp, out)[0])
        inp = input_for('AAA'); out = result(inp)
        out['hydration']['evidence'] = [dict(phrase='AA', start_0based=2, end_exclusive=3, role='ordinary_category')]
        self.assertIsNone(v2.postprocess(inp, out)[0])  # Overlapping matches are not unique.

    def test_false_negative_omission_and_explanation_contradiction(self):
        inp = input_for('HYDRATION ELECTROLYTE'); out = result(inp)
        self.assertIsNone(v2.postprocess(inp, out)[0])
        inp = input_for('WATER'); out = result(inp)
        out['hydration']['reason'] = 'This supports hydration positioning.'
        self.assertIsNone(v2.postprocess(inp, out)[0])
        out['hydration']['reason'] = 'This does not support hydration positioning.'
        self.assertIsNotNone(v2.postprocess(inp, out)[0])

    def test_schema_request_support_and_twenty_exact_full_ocr_inputs(self):
        fmt = v2.response_format(self.config['provider'])
        self.assertTrue(fmt['json_schema']['strict'])
        wire = fmt['json_schema']['schema']
        self.assertNotIn('"minimum"', json.dumps(wire))
        self.assertEqual(v2.output_schema()['$defs']['Evidence']['properties']['start_0based']['minimum'], 0)
        def required(o):
            if isinstance(o, dict):
                if o.get('type') == 'object':
                    self.assertFalse(o['additionalProperties'])
                    self.assertEqual(set(o['required']), set(o['properties']))
                for v in o.values():required(v)
            elif isinstance(o, list):
                for v in o:required(v)
        required(wire)
        for f in self.beverages:
            inp, _ = self.saved(f['row']['proposed_primary_slot_id'])
            prompt, _ = v2.prepare_saved_ocr(inp)
            body = dict(model=self.config['provider']['deployment'], messages=[{'role':'system','content':prompt},
                {'role':'user','content':json.dumps(inp,ensure_ascii=False)}],temperature=0,max_tokens=2000,response_format=fmt)
            self.assertEqual(json.loads(body['messages'][1]['content'])['ocr_text'], f['ocr'])
            self.assertLessEqual(len(json.dumps(body,ensure_ascii=False).encode()),self.config['max_request_utf8_bytes'])
        with self.assertRaises(ValueError):v2.response_format({'deployment_verified':False})

    def test_runner_explicit_v2_routing_independence_and_resume(self):
        for category, fail_core in [('beverages', True), ('beverages', False), ('snacks', False), ('cereals', False), ('dairies', False)]:
            config = copy.deepcopy(self.config);config.pop('tariffs')
            config.update(emerging_prompt_version=v2.PROMPT_VERSION, emerging_contract_sha256=v2.frozen_contract()[1])
            row = dict(self.beverages[0]['row'],category=category)
            provider = OfflineProvider(fail_core)
            policy = dict(execution_authorized=True,tariffs_validated=True,approval_sha256='synthetic',
                manifest_sha256='synthetic',attempt_cap=20,ceiling_nanochf=1000,
                worst_case_nanochf_per_call={k:10 for k in KINDS},max_calls_per_job={k:1 for k in KINDS})
            store = Staging(':memory:',policy)
            runner = Runner([row],'synthetic',config,policy,store,provider)
            runner.run_row(row); count=len(provider.calls);runner.run_row(row)
            self.assertEqual(len(provider.calls),count)
            stages = [k for k,b in provider.calls]
            self.assertEqual(stages.count('ocr'),1)
            self.assertEqual(stages.count('emerging_benefits'),int(category=='beverages'))
            core_body=next(b for k,b in provider.calls if k=='core')
            self.assertNotIn('response_format',core_body)
            if category=='beverages':
                b=next(b for k,b in provider.calls if k=='emerging_benefits')
                self.assertEqual(b['response_format']['type'],'json_schema')
                self.assertEqual(store.db.execute("select count(*) from stage_events where event='v6_postprocessing'").fetchone()[0],1)
            store.guard.close()

    def test_v1_configuration_keeps_original_adapter(self):
        config=copy.deepcopy(self.config); config.pop('tariffs')
        row=dict(self.beverages[0]['row'],category='snacks')
        policy=dict(execution_authorized=True,tariffs_validated=True,approval_sha256='synthetic',manifest_sha256='synthetic',
            attempt_cap=10,ceiling_nanochf=1000,worst_case_nanochf_per_call={k:10 for k in KINDS},max_calls_per_job={k:1 for k in KINDS})
        store=Staging(':memory:',policy)
        runner=Runner([row],'synthetic',config,policy,store,OfflineProvider(False))
        self.assertIs(runner.emerging,v1)
        store.guard.close()

    def test_failed_v2_logs_repairs_and_resume_never_repeats_paid_stages(self):
        config=copy.deepcopy(self.config);config.pop('tariffs')
        config.update(emerging_prompt_version=v2.PROMPT_VERSION,emerging_contract_sha256=v2.frozen_contract()[1])
        row=self.beverages[0]['row'];provider=OfflineProvider(False)
        original=provider.call
        def contradictory(kind,row,body,event):
            reply=original(kind,row,body,event)
            if kind=='emerging_benefits':
                reply['output']['electrolyte'].update(content_status='not_detected',front_status='not_detected')
            return reply
        provider.call=contradictory
        policy=dict(execution_authorized=True,tariffs_validated=True,approval_sha256='synthetic',manifest_sha256='synthetic',
            attempt_cap=10,ceiling_nanochf=1000,worst_case_nanochf_per_call={k:10 for k in KINDS},max_calls_per_job={k:1 for k in KINDS})
        store=Staging(':memory:',policy);runner=Runner([row],'synthetic',config,policy,store,provider)
        self.assertIsNone(runner.run_row(row)['v6']);before=len(provider.calls)
        runner.run_row(row);self.assertEqual(len(provider.calls),before)
        audit=store.db.execute("select payload from stage_events where event='v6_postprocessing' limit 1").fetchone()[0]
        self.assertTrue(json.loads(audit)['errors'])
        self.assertEqual(sum(k=='ocr' for k,b in provider.calls),1)
        self.assertEqual(sum(k=='core' for k,b in provider.calls),1)
        self.assertEqual(sum(k=='emerging_benefits' for k,b in provider.calls),1)
        store.guard.close()

    def test_refused_or_incomplete_structured_response_keeps_usage(self):
        for finish,refusal in [('length',None),('stop','Refused'),('content_filter',None)]:
            provider=object.__new__(AzureProvider);provider.openai='https://offline.invalid';provider.lkey='mock'
            provider.config={'provider':{'response_model':'gpt-4.1-nano-2025-04-14'}};provider.pacer=SimpleNamespace(wait=lambda *a:None)
            response=SimpleNamespace(status_code=200,headers={},text='synthetic',raise_for_status=lambda:None,
                json=lambda:dict(model='gpt-4.1-nano-2025-04-14',id='mock',usage={'prompt_tokens':10,'completion_tokens':1},
                    choices=[dict(finish_reason=finish,message={'content':'{}','refusal':refusal})]))
            provider.http=SimpleNamespace(post=Mock(return_value=response))
            reply=provider.call('emerging_benefits',{}, {'response_format':{'type':'json_schema'}},lambda *a:None)
            self.assertIsNone(reply['output']);self.assertEqual(reply['usage']['prompt_tokens'],10)
            self.assertEqual(provider.http.post.call_count,1)


class OfflineProvider:
    offline=True
    def __init__(self, fail_core):self.fail_core=fail_core;self.calls=[]
    def validate(self):pass
    def call(self,kind,row,body,event):
        self.calls.append((kind,body))
        if kind=='ocr':return {'text':'HYDRATION ELECTROLYTE DRINK','provider_request_id':'synthetic'}
        if kind=='core':
            if self.fail_core:raise TimeoutError('Synthetic core failure')
            return {'output':{'image_context':'front_of_pack','claim_extraction_status':'completed','no_claims_detected':True,'ocr_quality':'good'}}
        inp=json.loads(body['messages'][1]['content'])
        return {'output':positive(inp)}


if __name__=='__main__':unittest.main(verbosity=2)
