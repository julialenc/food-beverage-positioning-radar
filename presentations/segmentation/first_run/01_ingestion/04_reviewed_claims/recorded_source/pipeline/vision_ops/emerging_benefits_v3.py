"""Frozen wording candidates -> one interpretation call -> derived assessments.

No transport, taxonomy expansion, or automatic acceptance of additional wording.
The model never generates final statuses, candidate quotes, or candidate offsets.
"""
import copy
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pipeline.vision_ops import emerging_benefits_stage as v1
from pipeline.vision_ops.validate_emerging_benefits_v1 import (
    H_WORDING, E_WORDING, Attribution, Panel, validate_input, validate_pair,
)

ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = 'emerging_benefits_v3'
PROMPT = ROOT / 'pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v3.txt'
SCHEMA = PROMPT.with_name('emerging_benefits_interpretations_v3.schema.json')
REGISTRY = ROOT / 'presentations/segmentation/run_06b_v6_contract_v3.json'
PATTERNS = {'hydration': H_WORDING, 'electrolyte': E_WORDING}
build_input = v1.build_input


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Context(Record):
    assessable: bool
    target_attribution: Attribution
    panel_scope: Panel
    scope_basis: Literal['ocr_context', 'reliable_metadata', 'unresolved']
    metadata_fact_ids: list[str]
    reason: str


class Interpretation(Record):
    candidate_id: str
    role: Literal['supporting_positioning', 'back_panel_feature', 'ingredient_mention',
                  'unrelated_product_wording', 'ambiguous_wording', 'negated_wording',
                  'mineral_only', 'ordinary_category']
    purpose: Literal['hydration_positioning', 'electrolyte_feature', 'taste', 'unspecified'] | None
    reason: str


class AdditionalWording(Record):
    benefit: Literal['hydration', 'electrolyte']
    phrase: str
    reason: str


class ModelOutput(Record):
    schema_version: Literal['emerging_benefits_interpretations_v3']
    request_id: str
    product_context: Context
    interpretations: list[Interpretation]
    additional_wording: list[AdditionalWording]
    limitations: list[str]


def schema():
    value = ModelOutput.model_json_schema()
    def visit(item):
        if isinstance(item, dict):
            if 'const' in item:item['enum'] = [item.pop('const')]
            for v in item.values():visit(v)
        elif isinstance(item, list):
            for v in item:visit(v)
    visit(value)
    return value


def frozen_contract():
    _, original = v1.frozen_contract()
    expected = json.loads(REGISTRY.read_text(encoding='utf-8'))['contract_sha256']
    required = set(original) | {PROMPT.relative_to(ROOT).as_posix(), SCHEMA.relative_to(ROOT).as_posix(),
                               Path(__file__).relative_to(ROOT).as_posix()}
    if set(expected) != required:raise ValueError('Incomplete v3 contract registry')
    for path, digest in expected.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen v3 contract changed: ' + path)
    if json.loads(SCHEMA.read_text(encoding='utf-8')) != schema():raise ValueError('v3 schema/model mismatch')
    return PROMPT.read_text(encoding='utf-8'), expected


def candidates(input_record):
    inp = validate_input(input_record); text = inp.ocr_text or ''; result = []
    for benefit, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            start, end = match.span()
            identity = json.dumps([inp.ocr_sha256, benefit, start, end], separators=(',', ':'))
            result.append(dict(candidate_id=benefit[0]+'_'+hashlib.sha256(identity.encode()).hexdigest()[:20],
                benefit=benefit, phrase=text[start:end], start_0based=start, end_exclusive=end,
                context=text[text.rfind('\n', 0, start)+1:(text.find('\n', end) if '\n' in text[end:] else len(text))]))
    return sorted(result, key=lambda c:(c['start_0based'],c['benefit']))


def model_input(input_record):
    validate_input(input_record)
    return dict(copy.deepcopy(input_record), candidates=candidates(input_record))


def prepare_saved_ocr(input_record):
    if not (validate_input(input_record).ocr_text or '').strip():raise ValueError('Reusable full OCR required')
    return frozen_contract()


def response_format(provider):
    if not (provider.get('deployment_verified') and provider.get('response_model') == 'gpt-4.1-nano-2025-04-14' and
            provider.get('model_version') == '2025-04-14'):
        raise ValueError('Verified supported deployment required')
    def compact(value):
        if isinstance(value, dict):return {k:compact(v) for k,v in value.items() if k != 'title'}
        if isinstance(value, list):return [compact(v) for v in value]
        return value
    return {'type':'json_schema','json_schema':{'name':'emerging_benefits_interpretations_v3',
                                              'strict':True,'schema':compact(schema())}}


def derive(input_record, raw):
    """All known IDs must be interpreted exactly once before any final decision."""
    inp = validate_input(input_record); text = inp.ocr_text or ''; generated = candidates(input_record)
    out = ModelOutput.model_validate(raw)
    if out.request_id != inp.request_id:raise ValueError('Response request identity mismatch')
    ids = [i.candidate_id for i in out.interpretations]
    if len(ids) != len(set(ids)) or set(ids) != {c['candidate_id'] for c in generated}:
        raise ValueError('Missing, duplicate or unknown candidate ID; no negative may ignore known wording')
    if not out.product_context.reason.strip() or any(not i.reason.strip() for i in out.interpretations):
        raise ValueError('Context and interpretation reasons required')
    by_id = {i.candidate_id:i for i in out.interpretations}; additions = []
    for flag in out.additional_wording:
        if not flag.phrase or not flag.reason.strip():raise ValueError('Additional wording needs exact text and reason')
        positions = []; at = text.find(flag.phrase)
        while at >= 0:
            positions.append({'start_0based':at,'end_exclusive':at+len(flag.phrase)})
            at = text.find(flag.phrase, at+1)
        if not positions:raise ValueError('Additional wording is not an exact full-OCR substring')
        additions.append(dict(flag.model_dump(), occurrences=positions, review_required=True, accepted_positive=False))
    ctx = out.product_context
    assessments = {}
    for benefit in PATTERNS:
        cs = [c for c in generated if c['benefit'] == benefit]
        items = [by_id[c['candidate_id']] for c in cs]
        support = [i for i in items if i.role in {'supporting_positioning','back_panel_feature'}]
        uncertain = any(i.role in {'ambiguous_wording','ordinary_category','mineral_only'} for i in items)
        additional = any(a['benefit'] == benefit for a in additions)
        target = bool(text.strip()) and ctx.assessable and ctx.target_attribution == 'target'
        if ctx.assessable and text.strip() and ctx.target_attribution == 'unresolved' and (cs or additional):content = 'ambiguous'
        elif not target:content = 'unassessable'
        elif support:content = 'detected'
        elif uncertain or additional:content = 'ambiguous'
        else:content = 'not_detected'  # Every known candidate is explicitly accounted for.
        front_known = target and ctx.panel_scope == 'front' and ctx.scope_basis != 'unresolved'
        front = ('detected' if front_known and content == 'detected' and any(i.role == 'supporting_positioning' for i in support) else
                 'not_detected' if front_known and content == 'not_detected' else
                 'ambiguous' if front_known and content == 'ambiguous' else 'unassessable')
        purpose = None
        if content == 'detected':
            allowed = {None,'unspecified','hydration_positioning'} if benefit == 'hydration' else {None,'unspecified','electrolyte_feature','taste'}
            if any(i.purpose not in allowed for i in support):raise ValueError('Purpose contradicts candidate benefit')
            purpose = ('taste' if benefit == 'electrolyte' and any(i.purpose == 'taste' for i in support) else
                       'hydration_positioning' if benefit == 'hydration' else 'electrolyte_feature')
        evidence = [dict(phrase=c['phrase'],start_0based=c['start_0based'],end_exclusive=c['end_exclusive'],role=by_id[c['candidate_id']].role) for c in cs]
        assessments[benefit] = dict(content_status=content,front_status=front,
            target_attribution=ctx.target_attribution,panel_scope=ctx.panel_scope,scope_basis=ctx.scope_basis,
            metadata_fact_ids=ctx.metadata_fact_ids,purpose=purpose,evidence=evidence,
            reason=f'Derived from {len(cs)} fully accounted candidates; {len(support)} affirmative interpretations; '
                   f'target={ctx.target_attribution}, panel={ctx.panel_scope}, assessable={ctx.assessable}.')
    derived = dict(schema_version='emerging_benefits_output_v3',prompt_version=PROMPT_VERSION,definition_version='1.0.0',
        request_id=inp.request_id,barcode=inp.barcode,ocr_sha256=inp.ocr_sha256,**assessments,limitations=out.limitations)
    # Keep all approved exact-evidence / reliable-scope invariants, unchanged.
    compat = copy.deepcopy(derived)
    compat.update(schema_version='emerging_benefits_output_v1',prompt_version='emerging_benefits_v1')
    validate_pair(input_record, compat)
    return derived, additions


def validate_saved_ocr_result(input_record, raw, *, record=lambda audit:None):
    audit = dict(schema_validation='FAIL',classification_accepted=False,reason='',candidates=candidates(input_record))
    try:
        ModelOutput.model_validate(raw)
        audit['schema_validation'] = 'PASS'
        result, additions = derive(input_record, raw)
        audit.update(classification_accepted=True,additional_wording=additions,
                     reason='All candidate IDs accounted for; final states derived and evidence/scope validated')
    except (ValueError,TypeError,KeyError) as exc:
        audit['reason'] = str(exc); record(audit)
        raise ValueError('v3 assessment rejected: '+str(exc)) from exc
    record(audit)
    result['_validation'] = {k:audit[k] for k in ['schema_validation','classification_accepted','reason']}
    result['candidate_interpretations'] = copy.deepcopy(raw)
    result['additional_wording_review'] = additions
    fronts = [result[n]['front_status'] for n in PATTERNS]
    status = ('success_with_claims' if 'detected' in fronts else 'success_no_claims' if all(s == 'not_detected' for s in fronts) else 'success')
    return result, status  # Accepted abstention is successful assessment, never a negative.
