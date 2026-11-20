"""Prepare schemas and exercise offline contract fixtures; no model execution.

Hand-authored fixture responses are not LLM predictions or human gold. Full
saved OCR is read for readiness/hash checks, without exporting the corpus.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'presentations/segmentation'
OUT = BASE / 'emerging_benefits_prompt_v1'
PROMPTS = ROOT / 'pipeline/vision_prompts/emerging_benefits'
PROMPT = PROMPTS / 'prompt_emerging_benefits_v1.txt'
REPORT = BASE / 'Emerging benefits - Prompt v1 preparation.md'
APPROVED = BASE / 'beverage_03_approved_v1'
CORE = ['prompt_uk_test_09.2026_final.txt', 'prompt_v5_en.txt', 'prompt_v5_fr.txt', 'prompt_en_context_review.txt', 'prompt_fr_context_review.txt']


def mod(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


v = mod('independent_contract', 'pipeline/vision_ops/validate_emerging_benefits_v1.py')
b = mod('audit_readonly', 'pipeline/segmentation/beverage_01_ocr_evidence_audit.py')


def h(data):
    return hashlib.sha256(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()


def rel(p):
    return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()


def jb(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def input_record(case_id, text, name=None, front=True):
    sha = h(text) if text is not None else None
    return {'schema_version': 'emerging_benefits_input_v1', 'request_id': case_id, 'barcode': '0000000000001',
            'product_name': name, 'regions': ['FR'], 'country_assignments': [], 'ocr_text': text, 'ocr_sha256': sha,
            'source_reference': 'SYNTHETIC_CONTRACT_FIXTURE_NOT_OBSERVED_PRODUCT', 'source_artifact_sha256': None,
            'original_image_URL': None, 'image_provenance_note': 'Synthetic text-only contract fixture; no actual image or human gold',
            'prior_panel_context': 'front_of_pack' if front else 'uncertain', 'prior_profile': 'en', 'context_facts': []}


def fact(inp, fact_id='review_scope', panel='front', attribution='target', verification='human_review_same_evidence'):
    inp['context_facts'].append({'fact_id': fact_id, 'target_attribution': attribution, 'panel_scope': panel,
                                 'verification': verification, 'source_reference': 'SYNTHETIC_SCOPE_FACT_NOT_REAL_REVIEW',
                                 'applies_to_ocr_sha256': inp['ocr_sha256'], 'note': 'Authored contract fixture scope, not a benefit label'})


def assessment(front='not_detected', content='not_detected', panel='front', attribution='target', basis='ocr_context', ids=None, purpose=None):
    return {'content_status': content, 'front_status': front, 'target_attribution': attribution, 'panel_scope': panel,
            'scope_basis': basis, 'metadata_fact_ids': ids or [], 'purpose': purpose, 'evidence': [],
            'reason': 'Hand-authored expected contract example; not a model prediction'}


def response(inp, hydration=None, electrolyte=None):
    return {'schema_version': 'emerging_benefits_output_v1', 'prompt_version': 'emerging_benefits_v1', 'definition_version': '1.0.0',
            'request_id': inp['request_id'], 'barcode': inp['barcode'], 'ocr_sha256': inp['ocr_sha256'],
            'hydration': hydration or assessment(), 'electrolyte': electrolyte or assessment(), 'limitations': []}


def quote(inp, obj, phrase, role='supporting_positioning'):
    start = inp['ocr_text'].index(phrase)
    obj['evidence'].append({'phrase': phrase, 'start_0based': start, 'end_exclusive': start+len(phrase), 'role': role})


def fixtures():
    cases = []
    def add(name, inp, out):
        cases.append({'fixture_id': name, 'synthetic': True, 'hand_authored_not_model_or_gold': True,
                      'input': inp, 'authored_output': out, 'expected_validation': 'accept'})
    inp = input_record('mineral_only', 'COCOA\n7 VITAMINS + MAGNESIUM')
    out = response(inp); quote(inp, out['electrolyte'], 'MAGNESIUM', 'mineral_only'); add('mineral_only', inp, out)
    inp = input_record('taste', 'WATER\nWITH ELECTROLYTES\nFOR TASTE')
    out = response(inp, electrolyte=assessment('detected', 'detected', purpose='taste'))
    quote(inp, out['electrolyte'], 'WITH ELECTROLYTES\nFOR TASTE'); add('taste', inp, out)
    inp = input_record('identity_OCR_supported', 'PRIME\nHYDRATION', 'PRIME hydration drink')
    out = response(inp, hydration=assessment('detected', 'detected', purpose='hydration_positioning'))
    quote(inp, out['hydration'], 'PRIME\nHYDRATION'); add('identity_OCR_supported', inp, out)
    inp = input_record('replenisher_context', 'ULTIMA\nREPLENISHER\nelectrolyte drink mix', 'Ultima Replenisher')
    fact(inp)
    out = response(inp, assessment('detected', 'detected', basis='reliable_metadata', ids=['review_scope'], purpose='hydration_positioning'),
                   assessment('detected', 'detected', basis='reliable_metadata', ids=['review_scope'], purpose='electrolyte_feature'))
    quote(inp, out['hydration'], 'ULTIMA\nREPLENISHER\nelectrolyte drink mix'); quote(inp, out['electrolyte'], 'electrolyte drink mix'); add('replenisher_context', inp, out)
    inp = input_record('back_feature', 'INGREDIENTS: citrate (electrolytes)\nPlus Electrolytes', front=False)
    fact(inp, panel='back')
    out = response(inp, assessment('unassessable', panel='back', basis='reliable_metadata', ids=['review_scope']),
                   assessment('unassessable', 'detected', panel='back', basis='reliable_metadata', ids=['review_scope'], purpose='electrolyte_feature'))
    quote(inp, out['electrolyte'], 'citrate (electrolytes)', 'ingredient_mention'); quote(inp, out['electrolyte'], 'Plus Electrolytes', 'back_panel_feature'); add('back_feature', inp, out)
    inp = input_record('background', 'BABY JUICE\nElectrolyte Solution', 'Baby juice')
    fact(inp); fact(inp, 'background_words', attribution='unrelated')
    out = response(inp, electrolyte=assessment(basis='reliable_metadata', ids=['review_scope', 'background_words']))
    quote(inp, out['electrolyte'], 'Electrolyte Solution', 'unrelated_product_wording'); add('background', inp, out)
    inp = input_record('unknown_attribution', 'Electrolyte Solution\nBABY JUICE', 'Baby juice')
    fact(inp, verification='historical_classifier_unverified')
    out = response(inp, assessment('unassessable', panel='unknown', attribution='unresolved', basis='unresolved'),
                   assessment('ambiguous', 'ambiguous', panel='unknown', attribution='unresolved', basis='unresolved'))
    quote(inp, out['electrolyte'], 'Electrolyte Solution', 'ambiguous_wording'); add('unknown_attribution', inp, out)
    inp = input_record('identity_not_evidence', 'WATER', 'Hydration electrolyte drink')
    add('identity_not_evidence', inp, response(inp))
    for name, text in [('missing_OCR', None), ('empty_OCR', '')]:
        inp = input_record(name, text, front=False)
        ua = assessment('unassessable', 'unassessable', panel='unknown', attribution='unresolved', basis='unresolved')
        add(name, inp, response(inp, copy.deepcopy(ua), copy.deepcopy(ua)))
    inp = input_record('French_positive', 'BOISSON HYDRATANTE\nAVEC ÉLECTROLYTES')
    out = response(inp, assessment('detected', 'detected', purpose='hydration_positioning'), assessment('detected', 'detected', purpose='electrolyte_feature'))
    quote(inp, out['hydration'], 'BOISSON HYDRATANTE'); quote(inp, out['electrolyte'], 'AVEC ÉLECTROLYTES'); add('French_positive', inp, out)
    inp = input_record('tail_beyond_2000', 'x'*2100 + '\nHYDRATION DRINK\nWITH ELECTROLYTES')
    out = response(inp, assessment('detected', 'detected'), assessment('detected', 'detected'))
    quote(inp, out['hydration'], 'HYDRATION DRINK'); quote(inp, out['electrolyte'], 'WITH ELECTROLYTES'); add('tail_beyond_2000', inp, out)
    inp = input_record('descriptor_unknown', 'REPLENISHER', front=False)
    out = response(inp, assessment('ambiguous', 'ambiguous', panel='unknown', attribution='unresolved', basis='unresolved'),
                   assessment('unassessable', panel='unknown', attribution='unresolved', basis='unresolved'))
    quote(inp, out['hydration'], 'REPLENISHER', 'ambiguous_wording'); add('descriptor_unknown', inp, out)
    inp = input_record('ingredient_only', 'Ingredients: potassium citrate (electrolytes)', front=False)
    out = response(inp, assessment('unassessable', panel='ingredient_or_nutrition'), assessment('unassessable', panel='ingredient_or_nutrition'))
    quote(inp, out['electrolyte'], 'potassium citrate (electrolytes)', 'ingredient_mention'); add('ingredient_only', inp, out)
    inp = input_record('negated', 'WATER\nNO ADDED ELECTROLYTES')
    out = response(inp); quote(inp, out['electrolyte'], 'NO ADDED ELECTROLYTES', 'negated_wording'); add('negated', inp, out)
    inp = input_record('unsupported_language', 'نص غير قابل للتقييم ضمن هذه التجربة', front=False)
    ua = assessment('unassessable', 'unassessable', panel='unknown', attribution='unresolved', basis='unresolved')
    add('unsupported_language', inp, response(inp, copy.deepcopy(ua), copy.deepcopy(ua)))
    inp = input_record('historical_context_not_truth', 'HYDRATION DRINK\nWITH ELECTROLYTES')
    inp['prior_panel_context'] = 'ingredient_or_legal_panel'; fact(inp)
    out = response(inp, assessment('detected', 'detected', basis='reliable_metadata', ids=['review_scope']),
                   assessment('detected', 'detected', basis='reliable_metadata', ids=['review_scope']))
    quote(inp, out['hydration'], 'HYDRATION DRINK'); quote(inp, out['electrolyte'], 'WITH ELECTROLYTES'); add('historical_context_not_truth', inp, out)
    inp = copy.deepcopy(cases[4]['input']); inp['request_id'] = 'historical_front_not_truth'; inp['prior_panel_context'] = 'front_of_pack'
    out = copy.deepcopy(cases[4]['authored_output']); out['request_id'] = inp['request_id']; add('historical_front_not_truth', inp, out)
    inp = input_record('French_rehydration_inflection', 'BOISSON RÉHYDRATANTE\nAVEC ÉLECTROLYTES')
    out = response(inp, assessment('detected', 'detected', purpose='hydration_positioning'), assessment('detected', 'detected', purpose='electrolyte_feature'))
    quote(inp, out['hydration'], 'BOISSON RÉHYDRATANTE'); quote(inp, out['electrolyte'], 'AVEC ÉLECTROLYTES'); add('French_rehydration_inflection', inp, out)
    return cases


def mutation_tests(cases):
    results = []
    lookup = {c['fixture_id']: c for c in cases}
    def reject(name, fixture, edit):
        inp = copy.deepcopy(lookup[fixture]['input']); out = copy.deepcopy(lookup[fixture]['authored_output'])
        edit(inp, out)
        try:
            v.validate_pair(inp, out)
        except (ValueError, TypeError) as error:
            results.append({'test': name, 'expected': 'reject', 'actual': 'reject', 'passed': True, 'error': str(error).split('\n')[0]})
        else:
            raise AssertionError('Unsafe fixture accepted: ' + name)
    reject('legacy_flag_extra_key', 'taste', lambda i,o:o.update({'fortification_claim': True}))
    reject('missing_proposition_key', 'taste', lambda i,o:o.pop('hydration'))
    reject('boolean_status_not_enum', 'taste', lambda i,o:o['electrolyte'].update({'front_status': True}))
    reject('wrong_response_hash', 'taste', lambda i,o:o.update({'ocr_sha256': '0'*64}))
    reject('leading_zero_identity_loss', 'taste', lambda i,o:o.update({'barcode': '1'}))
    reject('invented_phrase', 'taste', lambda i,o:o['electrolyte']['evidence'][0].update({'phrase': 'added ELECTROLYTES'}))
    reject('bad_offset', 'taste', lambda i,o:o['electrolyte']['evidence'][0].update({'start_0based': 0}))
    reject('truncated_input', 'tail_beyond_2000', lambda i,o:i.update({'ocr_text': i['ocr_text'][:2000]}))
    reject('back_positive_front', 'back_feature', lambda i,o:o['electrolyte'].update({'front_status': 'detected'}))
    reject('unknown_target_positive', 'taste', lambda i,o:o['electrolyte'].update({'target_attribution': 'unresolved'}))
    reject('unknown_scope_positive', 'taste', lambda i,o:o['electrolyte'].update({'panel_scope': 'unknown'}))
    reject('mineral_only_electrolyte_positive', 'mineral_only', lambda i,o:o['electrolyte'].update({'content_status': 'detected', 'front_status': 'detected', 'evidence': [{**o['electrolyte']['evidence'][0], 'role': 'supporting_positioning'}]}))
    reject('product_name_only_hydration', 'identity_not_evidence', lambda i,o:o['hydration'].update({'content_status': 'detected','front_status': 'detected'}))
    reject('electrolytes_imply_hydration', 'taste', lambda i,o:o.update({'hydration': copy.deepcopy(o['electrolyte'])}))
    reject('unknown_metadata_id', 'replenisher_context', lambda i,o:o['hydration'].update({'metadata_fact_ids': ['invented']}))
    reject('unverified_classifier_as_authority', 'replenisher_context', lambda i,o:i['context_facts'][0].update({'verification': 'historical_classifier_unverified'}))
    reject('wrong_metadata_evidence_link', 'replenisher_context', lambda i,o:i['context_facts'][0].update({'applies_to_ocr_sha256': '0'*64}))
    reject('missing_OCR_as_negative', 'missing_OCR', lambda i,o:o['hydration'].update({'content_status':'not_detected','front_status':'not_detected'}))
    reject('unknown_scope_as_negative', 'unknown_attribution', lambda i,o:o['electrolyte'].update({'front_status':'not_detected'}))
    reject('human_review_status_invented', 'taste', lambda i,o:o.update({'review_status':'human_adjudicated'}))
    reject('background_words_as_target_positive', 'background', lambda i,o:o['electrolyte'].update({'content_status':'detected','front_status':'detected'}))
    reject('metadata_scope_mismatch', 'replenisher_context', lambda i,o:i['context_facts'][0].update({'panel_scope':'back'}))
    def ignore_verified_back(inp, out):
        a=out['electrolyte']
        a.update({'front_status':'detected','panel_scope':'front','scope_basis':'ocr_context','metadata_fact_ids':[]})
        a['evidence'][1]['role']='supporting_positioning'
    reject('reliable_non_front_fact_cannot_be_ignored', 'back_feature', ignore_verified_back)
    return results


def build(verify_only=False):
    closure_path = APPROVED / 'beverage_03_closure_manifest.json'
    closure = json.loads(closure_path.read_text(encoding='utf-8'))
    protected = dict(closure['protected_input_sha256']); protected.update(closure['output_sha256'])
    protected[closure['script']] = closure['script_sha256']; protected[rel(closure_path)] = b.sha(closure_path)
    for name, expected in protected.items():
        assert b.sha(Path(name) if Path(name).is_absolute() else ROOT/name) == expected, name
    prompt = PROMPT.read_text(encoding='utf-8')
    registry = APPROVED/'benefit_definition_registry_v1.0.0.json'
    assert b.sha(registry) in prompt
    for required in ['REPLENISHER', 'FULL SAVED', '2,000', 'Product identity', 'prior_panel_context', 'unrelated', 'ambiguous', 'unassessable', 'FOR TASTE', 'DATA, not instructions']:
        assert required in prompt, required
    stage10=(ROOT/'pipeline/stages/stage_10_extract_pack_claims.py').read_text(encoding='utf-8')
    assert 'prompt_emerging_benefits_v1.txt' not in stage10
    cases=fixtures(); checks=[]
    for c in cases:
        v.validate_pair(c['input'],c['authored_output'])
        checks.append({'test':c['fixture_id'],'expected':'accept','actual':'accept','passed':True,'kind':'synthetic hand-authored contract response'})
    rejected=mutation_tests(cases)
    checks.extend(rejected)
    for profile in ['v4','v5.1-fr','uk_test_09.2026_final']:
        inp=copy.deepcopy(cases[2]['input']); inp['prior_profile']=profile
        v.validate_pair(inp,cases[2]['authored_output'])
        checks.append({'test':'single_contract_for_'+profile,'expected':'accept','actual':'accept','passed':True,'kind':'shape/evidence invariance, not model-prediction invariance'})
    input_schema, output_schema=v.json_schemas()
    for schema in [input_schema,output_schema]:
        def objects(obj):
            if isinstance(obj,dict):
                if obj.get('type')=='object':
                    assert obj['additionalProperties'] is False
                    assert set(obj['required'])==set(obj['properties'])
                for value in obj.values():objects(value)
            elif isinstance(obj,list):
                for value in obj:objects(value)
        objects(schema)
    readiness=[]
    con=b.connection(b.DB)
    labels=read_csv(APPROVED/'frozen_human_reviewed_labels.csv')
    for label in labels:
        record=dict(con.execute('SELECT a.*,p.product_name,p.observed_market_region_codes FROM product_analysis a JOIN products p USING(barcode) WHERE barcode=?',(label['barcode'],)).fetchone())
        inp=input_record('OFFLINE_READINESS_'+label['barcode'],record['ocr_text'],record['product_name'],front=False)
        inp.update({'barcode':label['barcode'],'regions':[b.REGION_MAP[r] for r in (record['observed_market_region_codes'] or '').split('|') if r in b.REGION_MAP],
                    'source_reference':label['source_OCR_reference'],'source_artifact_sha256':protected['database/positioning_radar.db'],
                    'original_image_URL':label['original_image_URL_preserved'], 'image_provenance_note':'Preserved OFF reference; historical pixels not verified',
                    'prior_panel_context':record['image_context'],'prior_profile':record['prompt_version']})
        # Do not transmit human labels or convert approved visual decisions
        # into invented same-pixel metadata. This check keeps facts empty.
        assert h(inp['ocr_text'])==label['source_OCR_sha256']
        v.validate_input(inp)
        assert not any('label' in key or 'claim' in key for key in inp)
        readiness.append({'barcode':inp['barcode'],'regions_from_saved_source':inp['regions'],'prior_profile_provenance_only':inp['prior_profile'],
                          'prior_panel_context_provenance_only':inp['prior_panel_context'],'full_OCR_characters':len(inp['ocr_text']),
                          'full_OCR_sha256':inp['ocr_sha256'],'input_contract_valid':True,'reliable_scope_facts_in_model_payload':0,
                          'human_gold_sent_to_model':False,'model_calls':0,'model_prediction':None})
    # Also verify both genuinely long successful beverage OCR observations
    # previously audited, which are outside the approved positive cases.
    long_texts=[]
    for code in ['3245678093795','3560071472276']:
        text=con.execute('SELECT ocr_text FROM product_analysis WHERE barcode=?',(code,)).fetchone()[0]
        inp=input_record('LONG_READINESS_'+code,text); inp['barcode']=code; v.validate_input(inp)
        assert len(text)>2000
        long_texts.append({'barcode':code,'characters':len(text),'full_OCR_sha256':h(text),'no_truncation':True,'model_calls':0})
    con.close()
    schemas={PROMPTS/'emerging_benefits_input_v1.schema.json':jb(input_schema),PROMPTS/'emerging_benefits_output_v1.schema.json':jb(output_schema)}
    results={'status':'Offline contract checks passed; no LLM inference or semantic accuracy measured',
             'accepted_hand_authored_fixtures':len(cases),'rejected_invalid_mutations':len(rejected),'profile_contract_checks':3,'checks':checks,
             'approved_product_input_readiness_checks':len(readiness),'additional_full_OCR_over_2000_checks':long_texts,
             'schema_objects_all_required_no_extra_fields':True,'five_core_prompts_unchanged':True,'paid_calls':0,'deployment':False,
             'limitations':['Fixtures are synthetic contract tests, not observed labels, model predictions or independent validation.',
                            'Evidence-role and scope assertions still require semantic review; structural validation cannot prove a model read an image, attributed words correctly or applied the policy accurately.',
                            'No provider schema negotiation, model/version compatibility, refusals, latency, cost or live call behavior tested.']}
    contract=f'''# Independent emerging-benefit contract v1 — prepared, not deployed

Prompt: [prompt_emerging_benefits_v1.txt](prompt_emerging_benefits_v1.txt).
Approved definitions: [BEVERAGE 03 v1.0.0](../../../presentations/segmentation/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json).

## Input and provenance

The [input JSON Schema](emerging_benefits_input_v1.schema.json) describes one target product's full saved OCR, exact string barcode, region/country links, source hash/reference, original image reference, prior profile/context, and optional version-linked scope facts. Empty region/country arrays mean unavailable assignments, never a fabricated region. Use the full original UTF-8 text and hash; do not strip, normalize or truncate. Unknown text/hash is null. The first 2,000 characters are not the input unit. If a future deployment cannot fit the text, it must report an execution limitation rather than silently truncate; a chunking protocol would require separate preparation.

Identity is only an attribution aid for OCR-supported wording. No legacy flags, approved human labels, taxonomy priorities or image pixels belong in the model input. Prior profile and panel classification are provenance only. Reliable scope facts require a source reference, an actual verification basis and a link to the exact OCR hash; historical classifier output and URL naming are insufficient by themselves. Human visual decisions not supplied as reliable same-evidence facts must not be invented from the reviewed label file.

## Response

The [output JSON Schema](emerging_benefits_output_v1.schema.json) requires hydration and electrolyte assessments independently, each with content_status, front_status, target attribution, panel scope/basis, metadata fact IDs, purpose, exact phrases/code-point offsets and a brief reason. Four statuses preserve uncertainty. A back-panel feature may have detected content and unassessable front scope. Negative front conclusions also need suitable target/front evidence. Ingredient-only or unrelated-product words stay reviewable evidence without becoming target positioning. All object fields are required, unknown fields are rejected, and nullables are explicit.

The new [standalone offline validator](../../vision_ops/validate_emerging_benefits_v1.py) checks schema shape and input-linked invariants. The legacy validator is untouched. Pydantic models generate the schemas; cross-field/hash/span checks run separately. Schema constraints cannot prove semantic correctness. English/French wording guards reject obvious mineral-only or identity-only positives; additional language equivalents require versioned validation before use.

## Caller-owned observation envelope

The future caller, not the model, must assign run/observation IDs, actual execution time, region/country assignments, full OCR/source hashes, definition/prompt/schema/config hashes, actual model/deployment version and review status. Append independent observations; never overwrite OCR or the 34 legacy flags. Missing assessment means no observation, not false. Transport failures, invalid/incomplete/refused responses are execution outcomes outside the classification object; no automatic negative or authorized retry follows.

## Offline review and boundaries

Hand-authored fixtures cover scope/attribution, taste, mineral negatives, identity, approved REPLENISHER context, French wording, uncertainty, unsupported language and a synthetic positive beyond 2,000 characters. They do not test an LLM's behavior. Fifty approved product records are checked for full-text input readiness without exporting their OCR or producing new classifications. Two additional real long texts are checked without inference. Later model evaluation must separate OCR-visible conclusions from image-derived human labels; correct abstention where evidence is unavailable is not automatically an extraction regression.

General schema design follows [official Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs): required fields and forbidden extra properties. Actual deployment/provider support has not been tested. No API settings, client or execution path is installed. Further benefits require their own approved definition and a new contract/prompt version; this v1 assesses only hydration and electrolytes.
'''
    report=f'''# Emerging benefits — Independent prompt v1 preparation

**Prepared for review. No paid calls, model inference, deployment or historical backfill.**

## Files to review

- [Independent prompt](../../pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v1.txt)
- [Input/output contract and caller obligations](../../pipeline/vision_prompts/emerging_benefits/CONTRACT_v1.md)
- [Output JSON Schema](../../pipeline/vision_prompts/emerging_benefits/emerging_benefits_output_v1.schema.json)
- [Input JSON Schema](../../pipeline/vision_prompts/emerging_benefits/emerging_benefits_input_v1.schema.json)

The prompt uses approved BEVERAGE 03 definition registry **v1.0.0**, SHA256 `{b.sha(registry)}`. It lives outside `current/` and is not registered in Stage 10. All three existing extraction prompts and both context-review prompts remain byte-identical, including the English v4/French v5.1-fr labels.

## Evidence rules

The same policy applies to all regions; earlier regional product-name rules are not inherited. Full saved OCR supplies proposition wording. Product identity helps attribution or interpretation of an OCR-supported descriptor, but never supplies absent claims. Hydration includes the approved contextual REPLENISHER descriptor. Electrolytes require explicit wording, with taste purpose independent of hydration. Fortification, all 34 flags, taxonomy and historical classifications are unchanged.

The output separates **target-product content** from **front-pack positioning**. Exact phrases retain original offsets/spelling and can be marked as back-panel, ingredient or unrelated-product evidence. Prior panel classifications are provenance, not truth. When target/front scope is unavailable, return ambiguous/unassessable. This includes positive-looking text whose attribution cannot be established; negative front conclusions also require suitable evidence. No claim of image inspection is allowed.

## Offline validation performed

- **{len(cases)} hand-authored synthetic response fixtures** accepted by the standalone contract validator.
- **{len(rejected)} deliberately invalid mutations** rejected: invented/shifted quotes, source/identity mismatch, truncation, legacy keys, mineral-only positives, unsupported identity claims, unknown/unverified metadata, bypassed reliable non-front metadata and unsafe front decisions.
- **3 prior-profile contract checks** use the same prompt/schema/invariants. These are not model-prediction comparisons.
- **50 frozen reviewed products** pass full saved-OCR input/hash checks. No human labels were passed to a model, no model was called, and no new product classifications were generated.
- **Two real texts of 2,080 and 2,351 characters** retain their full hashes; a separate synthetic tail-positive fixture exercises offsets after character 2,000.

[Detailed checks](emerging_benefits_prompt_v1/offline_validation_results.json), [synthetic fixtures](emerging_benefits_prompt_v1/contract_fixtures.json), [50-record readiness metadata](emerging_benefits_prompt_v1/input_readiness.json) and [source/output hashes](emerging_benefits_prompt_v1/preparation_manifest.json) remain local. The OCR corpus was not exported.

**These checks establish contract/evidence mechanics, not prompt accuracy.** No LLM precision/recall, semantic robustness, provider compatibility or independent-validation result is claimed. An eventual model comparison must account for human visual information absent from OCR; it must not force the frozen image-derived labels into an insufficient text-only input.

The schema uses explicit required keys, nullable unknown values and forbidden extras, following [official Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs). Live provider support and an exact model/configuration remain untested; this preparation installs no API caller.

## Preservation and STOP

New artifacts only: isolated prompt, two schemas, contract guide, independent validator and offline preparation evidence. All approved BEVERAGE 03 artifacts, five existing prompts, Stage 10/11/12, legacy validator, OCR, claims, databases and upstream sampling evidence are hash-protected and unchanged. **STOP for review. Paid tests, deployment and bulk backfill remain unauthorized.**
'''
    payloads={**schemas,PROMPTS/'CONTRACT_v1.md':contract.encode('utf-8'),OUT/'contract_fixtures.json':jb(cases),
              OUT/'offline_validation_results.json':jb(results),OUT/'input_readiness.json':jb(readiness),REPORT:report.encode('utf-8')}
    manifest={'preparation':'independent_emerging_benefits_prompt_v1','status':'Prepared offline only; not approved for paid testing or deployment',
              'definition_version':'1.0.0','prompt':rel(PROMPT),'prompt_sha256':b.sha(PROMPT),
              'script':rel(Path(__file__)),'script_sha256':b.sha(Path(__file__)),
              'standalone_validator':'pipeline/vision_ops/validate_emerging_benefits_v1.py',
              'standalone_validator_sha256':b.sha(ROOT/'pipeline/vision_ops/validate_emerging_benefits_v1.py'),
              'protected_input_sha256':protected,
              'unchanged_core_prompt_sha256':{name:b.sha(ROOT/'pipeline/vision_prompts/current'/name) for name in CORE},
              'offline_checks':{'synthetic_valid_responses':len(cases),'rejected_mutations':len(rejected),'profile_checks':3,'real_input_records':50,'extra_real_long_texts':2},
              'paid_calls':0,'model_predictions':0,'deployment':False,'legacy_changes':False,
              'documentation_source':'https://developers.openai.com/api/docs/guides/structured-outputs',
              'output_sha256':{rel(p):h(data) for p,data in payloads.items()}}
    payloads[OUT/'preparation_manifest.json']=jb(manifest)
    for name,expected in protected.items():assert b.sha(Path(name) if Path(name).is_absolute() else ROOT/name)==expected,name
    if verify_only:
        for p,data in payloads.items():assert p.read_bytes()==data,'Reproduction mismatch: '+rel(p)
        print(json.dumps({'reproduced_generated_files':len(payloads),'unchanged_protected_inputs':len(protected),'checks':len(checks),'model_calls':0}))
    else:
        if OUT.exists():
            old=json.loads((OUT/'preparation_manifest.json').read_text(encoding='utf-8'))
            assert old['status']==manifest['status'],'Only this unapproved preparation draft may be regenerated'
            for name,value in old['output_sha256'].items():assert b.sha(ROOT/name)==value,'Independently edited draft: '+name
        else:
            assert not REPORT.exists(),'New preparation version only'
            OUT.mkdir()
        for p,data in payloads.items():
            p.write_bytes(data)
        print(json.dumps({'report':rel(REPORT),'generated_files':len(payloads),'valid_fixtures':len(cases),'rejected_mutations':len(rejected),'profile_checks':3,'real_full_text_checks':52,'protected_inputs':len(protected),'model_calls':0},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    build(parser.parse_args().verify_only)
