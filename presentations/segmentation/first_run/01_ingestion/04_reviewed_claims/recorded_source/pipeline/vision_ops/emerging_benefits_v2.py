"""Minimal successor to the frozen v1 contract. No transport or paid execution.

Approved definitions and input schema are unchanged. Exact span repair is
deterministic; semantic conflicts remain held. Raw output is never mutated.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pipeline.vision_ops import emerging_benefits_stage as v1
from pipeline.vision_ops.validate_emerging_benefits_v1 import (
    EmergingOutput, H_WORDING, E_WORDING, validate_input, validate_pair,
)

ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = 'emerging_benefits_v2'
PROMPT = ROOT / 'pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v2.txt'
SCHEMA = PROMPT.with_name('emerging_benefits_output_v2.schema.json')
REGISTRY = ROOT / 'presentations/segmentation/run_06b_v6_contract_v2.json'
build_input = v1.build_input
SUPPORT = {'supporting_positioning', 'back_panel_feature'}


class EmergingOutputV2(EmergingOutput):
    schema_version: Literal['emerging_benefits_output_v2']
    prompt_version: Literal['emerging_benefits_v2']


def output_schema():
    """Same v1 schema/constraints, with successor version identifiers only."""
    schema = json.loads(v1.PROMPT.with_name('emerging_benefits_output_v1.schema.json').read_text(encoding='utf-8'))
    schema['properties']['schema_version']['enum'] = ['emerging_benefits_output_v2']
    schema['properties']['prompt_version']['enum'] = [PROMPT_VERSION]
    return schema


def frozen_contract():
    _, original = v1.frozen_contract()
    expected = json.loads(REGISTRY.read_text(encoding='utf-8'))['contract_sha256']
    required = set(original) | {PROMPT.relative_to(ROOT).as_posix(),
        SCHEMA.relative_to(ROOT).as_posix(), Path(__file__).relative_to(ROOT).as_posix()}
    if set(expected) != required:
        raise ValueError('Incomplete v2 contract registry')
    for relative, digest in expected.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError('v2 contract hash mismatch: ' + relative)
    if json.loads(SCHEMA.read_text(encoding='utf-8')) != output_schema():
        raise ValueError('v2 schema differs from the version-only v1 successor')
    return PROMPT.read_text(encoding='utf-8'), expected


def prepare_saved_ocr(input_record):
    inp = validate_input(input_record)
    if not inp.ocr_text or not inp.ocr_text.strip():
        raise ValueError('Reusable full OCR is required')
    return frozen_contract()


def response_format(provider):
    # Documented support, not a live capability probe. No silent fallback/retry.
    if not (provider.get('deployment_verified') and
            provider.get('response_model') == 'gpt-4.1-nano-2025-04-14' and
            provider.get('model_version') == '2025-04-14'):
        raise ValueError('v2 structured output requires the verified supported deployment')
    schema = output_schema()

    def wire(value):
        if isinstance(value, dict):
            # Azure excludes minimum; local typed/span validation retains it.
            return {k: wire(v) for k, v in value.items() if k not in {'minimum', 'title'}}
        if isinstance(value, list):
            return [wire(v) for v in value]
        return value

    return {'type': 'json_schema', 'json_schema': {
        'name': 'emerging_benefits_output_v2', 'strict': True, 'schema': wire(schema)}}


def _semantic_errors(output, text):
    """Bounded checks for demonstrated contradictions; not a semantic oracle."""
    errors = []
    for name, pattern in [('hydration', H_WORDING), ('electrolyte', E_WORDING)]:
        a = output.get(name)
        if not isinstance(a, dict):
            continue  # Typed validation reports missing/malformed assessments.
        evidence = a.get('evidence')
        if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
            continue
        supporting = [e for e in evidence if e.get('role') in SUPPORT]
        qualifying = [e for e in supporting if isinstance(e.get('phrase'), str) and pattern.search(e['phrase'])]
        if any(not isinstance(e.get('phrase'), str) or not pattern.search(e['phrase']) for e in supporting):
            errors.append(name + ': supporting evidence has no qualifying benefit wording')
        if a.get('content_status') == 'not_detected':
            if qualifying:
                errors.append(name + ': negative status contradicts explicit supporting wording')
            if pattern.search(text) and not any(isinstance(e.get('phrase'), str) and pattern.search(e['phrase']) for e in evidence):
                errors.append(name + ': negative omits relevant OCR wording; context review required')
            reason = a.get('reason', '')
            if isinstance(reason, str) and re.search(rf'(?<!not )\bsupport(?:s|ing)?\s+{name}\s+positioning\b', reason, re.I):
                errors.append(name + ': negative status contradicts affirmative explanation')
        if a.get('content_status') == 'detected':
            terms = r'(?:hydration|hydratation)' if name == 'hydration' else r'(?:[ée]lectrolytes?|electrolytes?)'
            if any(re.search(rf'\b(?:no|without|sans)\s+(?:any\s+)?{terms}\b', e['phrase'], re.I) for e in qualifying):
                errors.append(name + ': supporting phrase contains explicit negation')
            if (name == 'hydration' and a.get('purpose') in {'electrolyte_feature', 'taste'}) or (name == 'electrolyte' and a.get('purpose') == 'hydration_positioning'):
                errors.append(name + ': purpose belongs to a different proposition')
        if a.get('front_status') == 'not_detected' and a.get('content_status') != 'not_detected':
            errors.append(name + ': confident front negative conflicts with content status')
        if a.get('content_status') == 'not_detected' and a.get('purpose') in {'hydration_positioning', 'electrolyte_feature', 'taste'}:
            errors.append(name + ': absent proposition has an affirmative purpose')
    return errors


def postprocess(input_record, raw_output, *, recover_v1=False):
    """Return a derived candidate/audit. Only recovery may lower scope to abstain.

    Semantic conflicts are collected BEFORE recovery, so an abstention cannot
    hide a contradictory negative. Repair never adds words or positive labels.
    """
    inp = validate_input(input_record)
    candidate = copy.deepcopy(raw_output)
    audit = {'raw_output_sha256': hashlib.sha256(json.dumps(raw_output, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
             'postprocess_version': PROMPT_VERSION, 'corrections': [], 'errors': [], 'recovery_of_v1': recover_v1}
    if not isinstance(candidate, dict):
        audit['errors'].append('Missing/non-object provider response; no assessment inferred')
        return None, audit
    text = inp.ocr_text or ''
    # Cross-field purpose conflicts can be safely cleared only in explicit
    # legacy abstention recovery. Other semantic contradictions remain errors.
    audit['errors'] = [e for e in _semantic_errors(candidate, text)
        if not (recover_v1 and e.endswith('absent proposition has an affirmative purpose') and
                candidate[e.split(':')[0]].get('target_attribution') in {'unresolved', 'unrelated'})]

    def change(obj, key, value, path, reason):
        if obj.get(key) != value:
            audit['corrections'].append({'path': path + '.' + key, 'before': obj.get(key), 'after': value, 'reason': reason})
            obj[key] = value

    if recover_v1:
        if (candidate.get('schema_version'), candidate.get('prompt_version')) != ('emerging_benefits_output_v1', 'emerging_benefits_v1'):
            audit['errors'].append('Recovery requires an original v1 response')
    for name in ['hydration', 'electrolyte']:
        a = candidate.get(name)
        if not isinstance(a, dict):
            continue
        if a.get('purpose') == 'null' and a.get('content_status') in {'not_detected', 'ambiguous', 'unassessable'}:
            change(a, 'purpose', None, name, 'Quoted null normalized as missing purpose; no positive inference')
        evidence = a.get('evidence')
        if isinstance(evidence, list):
            for i, e in enumerate(evidence):
                if not isinstance(e, dict):
                    continue
                phrase, start, end = e.get('phrase'), e.get('start_0based'), e.get('end_exclusive')
                if not isinstance(phrase, str) or not phrase:
                    continue
                if type(start) is int and type(end) is int and 0 <= start < end <= len(text) and text[start:end] == phrase:
                    continue
                first = text.find(phrase)
                if first < 0 or text.find(phrase, first + 1) >= 0:
                    audit['errors'].append(f'{name}.evidence[{i}]: exact quote absent or non-unique; quote not rewritten')
                elif type(start) is int and type(end) is int:
                    path = f'{name}.evidence[{i}]'
                    change(e, 'start_0based', first, path, 'Unique exact substring in full saved OCR')
                    change(e, 'end_exclusive', first + len(phrase), path, 'Unique exact substring in full saved OCR')
        if recover_v1:
            if a.get('target_attribution') in {'unresolved', 'unrelated'}:
                change(a, 'content_status', 'unassessable', name, 'Target not established; abstention, not a negative')
            if a.get('target_attribution') in {'unresolved', 'unrelated'} or a.get('panel_scope') != 'front' or a.get('scope_basis') == 'unresolved':
                change(a, 'front_status', 'unassessable', name, 'Target-front scope not established')
            if a.get('content_status') == 'unassessable':
                change(a, 'purpose', None, name, 'No target proposition purpose established')
                if isinstance(a.get('reason'), str):
                    change(a, 'reason', a['reason'] + ' Offline recovery: insufficient target proposition evidence; no target-negative conclusion.', name, 'Preserve original explanation with explicit abstention qualification')
    audit['errors'].extend(_semantic_errors(candidate, text))
    try:
        validation_view = copy.deepcopy(candidate)
        if recover_v1:
            # Internal compatibility view only: returned recovery retains the
            # actual v1 model provenance, never claims a v2 model execution.
            validation_view.update(schema_version='emerging_benefits_output_v2', prompt_version=PROMPT_VERSION)
        out = EmergingOutputV2.model_validate(validation_view)
        # Reuse every frozen v1 invariant via a version-only compatibility view.
        compat = out.model_dump()
        compat.update(schema_version='emerging_benefits_output_v1', prompt_version='emerging_benefits_v1')
        validate_pair(input_record, compat)
        for name in ['hydration', 'electrolyte']:
            a = getattr(out, name)
            if a.target_attribution != 'target' and a.content_status in {'detected', 'not_detected'}:
                raise ValueError('Unestablished target cannot support confident target content')
    except (ValueError, TypeError, KeyError) as exc:
        audit['errors'].append(str(exc))
    audit['errors'] = list(dict.fromkeys(audit['errors']))
    return (candidate if not audit['errors'] else None), audit


def validate_saved_ocr_result(input_record, output, *, record=lambda audit: None):
    candidate, audit = postprocess(input_record, output)
    record(audit)  # Includes failed repairs; raw provider output stays separate.
    if candidate is None:
        raise ValueError('v2 contract HOLD: ' + '; '.join(audit['errors']))
    statuses = [candidate[name]['front_status'] for name in ['hydration', 'electrolyte']]
    status = ('success_with_claims' if 'detected' in statuses else
              'success_no_claims' if all(s == 'not_detected' for s in statuses) else 'unusable')
    return candidate, status
