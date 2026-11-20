"""BEVERAGE 03: offline reconciliation of Julia's workbook and preserved OCR.

Writes a new review package only. No network, image requests, OCR/LLM calls,
production edits, source corrections, taxonomy changes or database writes.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'presentations/segmentation'
OUT = BASE / 'beverage_03_v1'
SOURCE = BASE / 'beverage_02_v1/hydration_electrolyte_product_reviewed.xlsx'
REPORT = BASE / 'BEVERAGE 03 - Human pack review reconciliation.md'
VERSION = '0.2.0-proposal'
STATES = {'detected', 'not_detected', 'ambiguous', 'unassessable'}
BENEFITS = ['hydration', 'electrolyte']


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'pipeline/segmentation' / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


b01 = module('bev01', 'beverage_01_ocr_evidence_audit.py')
b02 = module('bev02', 'beverage_02_validation_preparation.py')


def rel(p):
    return p.relative_to(ROOT).as_posix()


def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def jb(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def cb(records):
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=list(records[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode('utf-8-sig')


def j(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def markdown_table(rows, columns):
    def value(v):
        return str(v).replace('|', '/').replace('\n', ' ') if v is not None else '—'
    return '\n'.join(['| ' + ' | '.join(label for key, label in columns) + ' |',
                      '|' + '---|' * len(columns),
                      *['| ' + ' | '.join(value(row[key]) for key, label in columns) + ' |' for row in rows]])


def evidence_span(text, start, end, role):
    return {'phrase': text[start:end], 'start_0based': start, 'end_exclusive': end, 'role': role}


def line_span(text, match, role):
    left = text.rfind('\n', 0, match.start()) + 1
    right = text.find('\n', match.end())
    return evidence_span(text, left, len(text) if right < 0 else right, role)


H = b01.COMPILED['hydration_wording']
E = b01.COMPILED['electrolyte_wording']
REPLENISHER = re.compile(r'\breplenisher\b', re.I)


def proposed_detect(text, benefit, saved_context):
    """Generic draft; no case IDs, human labels/notes or product names as inputs.

    Returns independent content and front-scope statuses. A back-panel
    positive is retained as text evidence without promotion to front evidence.
    """
    if not text or not text.strip():
        return 'unassessable', 'unassessable', [], None, 'No exact joined saved OCR'
    gate = b02.assessability(text)
    matches = list((H if benefit == 'hydration' else E).finditer(text))
    purpose = None
    if benefit == 'hydration':
        if matches:
            affirmative = []
            for m in matches:
                local = text[max(0, m.start()-45):min(len(text), m.end()+70)]
                if not re.search(r'does not|no hydration benefit|sans effet|ne\b.{0,25}\bpas|\bdehydration\b|\bd[ée]shydratation\b', local, re.I):
                    affirmative.append(line_span(text, m, 'hydration_wording_or_descriptor'))
            content = 'detected' if affirmative else 'ambiguous'
            evidence = affirmative or [line_span(text, matches[0], 'negation_or_dehydration_context')]
            reason = 'Explicit hydration wording/descriptor; no inference from water, electrolytes or format'
            purpose = 'hydration_positioning' if affirmative else None
        elif REPLENISHER.search(text):
            m = REPLENISHER.search(text)
            content, evidence = 'ambiguous', [line_span(text, m, 'descriptor_policy_pending')]
            reason = 'REPLENISHER is exact wording; hydration attribution needs a separate descriptor policy'
        else:
            content, evidence, reason = 'not_detected', [], 'No explicit hydration wording; no category/mineral/format inference'
    else:
        affirmative, non_claim, negated = [], [], []
        for m in matches:
            span = line_span(text, m, 'electrolyte_feature_wording')
            line = span['phrase']
            local = text[max(0, m.start()-60):min(len(text), m.end()+80)]
            if re.search(r'\b(?:no|without|sans)\s+(?:added\s+)?[ée]lectrolytes?', local, re.I):
                span['role'] = 'negated_mention'
                negated.append(span)
            elif re.search(r'ingredients?|ingr[ée]dients?|citrate|chloride|chlorure|potass|sodium|nutrition', line, re.I):
                span['role'] = 'ingredient_or_nutrition_mention'
                non_claim.append(span)
            elif re.search(r'\b(?:zero|z[ée]ro)\s+[ée]lectrolytes?\b', text, re.I) and not re.search(r'[ée]lectrolytes?\s+(?:sports?\s+drink|drink|water)', text, re.I):
                span['role'] = 'uncertain_negation'
                non_claim.append(span)
            else:
                affirmative.append(span)
        if affirmative:
            content, evidence = 'detected', affirmative
            purpose = 'taste' if re.search(r'for\s+taste|pour le go[uû]t', text, re.I) else 'feature_purpose_not_established'
            reason = 'Explicit electrolyte feature; mineral proxies never trigger this classification'
        else:
            content, evidence = 'not_detected', non_claim + negated
            reason = 'No affirmative consumer-facing electrolyte wording; individual minerals are insufficient'
    front = content
    if saved_context == 'ingredient_or_legal_panel' or gate:
        front = 'unassessable'
        reason += '; front scope unavailable in saved context' if not gate else '; ' + gate
    return content, front, evidence, purpose, reason


def definitions():
    return {
        'definition_version': VERSION, 'status': 'Refined proposal; human-review exceptions and final approval pending',
        'policy_source': 'Julia BEVERAGE 03 instructions; human workbook preserved separately',
        'independence': 'Hydration and electrolyte positioning are independent additive signals; neither implies the other.',
        'hydration': {
            'positive': 'Explicit hydration/rehydration communication or a clearly presented hydration product/range descriptor. PRIME HYDRATION, HYDRATE, HYDRATION DRINK and SPARKLING HYDRATION can qualify as positioning, without an efficacy assertion.',
            'negative': 'Water/coconut water, sports-drink category, powder/tablet/sachet format, minerals or electrolytes alone establish no hydration signal.',
            'pending_boundary': 'REPLENISHER without explicit hydration/rehydration wording: preserve Julia detected labels, propose ambiguous pending an explicit descriptor policy; do not derive hydration solely from accompanying electrolytes.',
            'examples_en': ['hydration by nature.', 'HYDRATION DRINK', 'HYDRATE', 'HYDRATES', 'REHYDRATE REPLENISH. REFUEL', 'SPARKLING HYDRATION'],
            'examples_fr_illustrative_not_observed_gold': ['boisson hydratante', 'hydratation', 'réhydratation'],
        },
        'electrolyte': {
            'positive': 'Explicit consumer-facing electrolyte(s) wording or its language equivalent, including an electrolyte product descriptor or highlighted feature.',
            'negative': 'Magnesium, potassium, sodium, other individual minerals, ingredients/nutrition values and sports-drink/powder identity alone are insufficient. Ingredient-only electrolyte mention is not automatically positioning.',
            'taste': 'Electrolytes explicitly advertised for taste qualify as an electrolyte feature; record taste purpose independently and infer no hydration.',
            'ZERO_descriptor': 'Human pack review resolves B01_019 as a positive electrolyte sports-drink descriptor. Generic rules must distinguish an identity such as ZERO / ELECTROLYTE SPORTS DRINK from an explicit without/no-electrolytes negation.',
            'examples_en': ['WITH ELECTROLYTES', 'natural electrolytes', 'ELECTROLYTE SPORTS DRINK', 'Plus Electrolytes', '6 Essential Electrolytes'],
            'examples_fr_illustrative_not_observed_gold': ['avec électrolytes', 'boisson aux électrolytes', 'électrolytes ajoutés pour le goût'],
        },
        'scope_and_evidence': {
            'positioning_observation': 'Preserve exact claim wording, source OCR hash, image URL/provenance and purpose/context separately from four-state interpretation.',
            'front_eligibility': 'A consumer-facing back-panel proposition may be retained as a panel-specific observation. It does not prove front-pack positioning. A separate front-scope assessment is unassessable until qualifying front evidence exists.',
            'missing_front': 'Keep Julia ambiguous labels intact; suggest a separate unassessable front-scope result, never a forced negative.',
            'images': 'Image checked=Yes is a human review statement, not an independently verified immutable image-pixel hash. Current URL equality does not prove historical pixel identity.',
            'source_disagreement': 'Do not alter saved OCR when reviewed imagery and OCR disagree. Hold attribution/version uncertainty separately.',
        },
        'status_values': sorted(STATES),
        'taxonomy_compatibility': 'Fortification already exists in the 34 flags. Create no new mineral-fortification category, reclassify no existing fortification observation, change no priority mapping. Multiple existing and emerging signals may coexist.',
        'legacy_and_absence': 'Old flags, successful no-claim observations and OCR remain unchanged. No emerging assessment is not a false result.',
    }


def exception_spec():
    # Review annotations only. These never change imported human labels and
    # are not consulted by either deterministic detector.
    return {
        '85239610305': ('mineral_only_positive_conflict', 'Enhanced with / Minerals for Taste; no electrolyte wording in saved OCR or quoted human note.', 'Suggest electrolyte not_detected for observed wording; front scope unassessable from the historical non-front context. Preserve human detected pending approval.'),
        '78742077130': ('resolved_explicit_electrolyte', 'ELECTROLYTE» above Vitamin Enhanced / Grape / Drink Mix.', 'Retain electrolyte detected: supported by exact OCR, independently of powder format. No hydration inferred.'),
        '89094026479': ('resolved_explicit_electrolyte', 'WITH ELECTROLYTES appears twice next to CLEAR PROTEIN.', 'Retain electrolyte detected: explicit wording, independent of the protein claim or sachet format.'),
        '3288110161324': ('non_front_and_missing_explicit_electrolyte_evidence', 'Human note confirms back panel; saved OCR contains minerals/preparation and no electrolyte word.', 'Preserve raw electrolyte detected; propose unassessable for front scope and request exact electrolyte phrase/image before accepting an affirmative observed proposition. Sports-drink identity alone is insufficient.'),
        '813694022469': ('back_panel_marketing_vs_ingredient', 'citrate (electrolytes) is ingredient context; Plus Electrolytes is separate promotional wording in the same OCR.', 'Retain explicit panel-specific electrolyte evidence; front-scope unassessable. Do not convert the back-panel feature to a front-pack positive.'),
        '3564700590461': ('missing_front_evidence', 'Human note confirms back panel and uncertainty; OCR is mineral analysis.', 'Keep raw ambiguous labels; suggest separate front-scope unassessable outcomes. Minerals do not establish either proposition.'),
        '5000462001022': ('missing_front_evidence', 'Human note confirms back panel and uncertainty; OCR is storage/mineral information.', 'Keep raw ambiguous labels; suggest separate front-scope unassessable outcomes.'),
        '810003420213': ('replenisher_descriptor_policy', 'Replenisher™; electrolyte drink mix. No explicit hydration word.', 'Keep human hydration detected; propose ambiguous hydration until REPLENISHER is explicitly approved as a qualifying descriptor. Electrolyte positive remains supported.'),
        '853218000931': ('replenisher_descriptor_policy', "REPLENISHER'; 6 Essential / Electrolytes·; DAILY ELECTROLYTE DRINK MIX.", 'Keep human hydration detected; propose ambiguous hydration pending descriptor approval. Electrolyte positive remains supported.'),
        '5336636935634': ('OCR_image_attribution_conflict', 'OCR says Electrolyte / Solution, while Julia describes a regular juice and labels neither signal.', 'Preserve both. Hold image/version/word-attribution reconciliation; do not override the human negative or erase OCR. A saved-OCR classifier cannot resolve this visual conflict.'),
        '197644314881': ('image_uncertain_word_not_in_OCR', 'OCR: HYDRATE & ENERGITE; Julia reports hydrate and energize, but possible electrolyte word is unreadable.', 'Hydration positive is supported despite a non-essential OCR spelling error. Retain electrolyte ambiguous; do not call the absent electrolyte token a confirmed OCR miss.'),
        '92000111102229400000': ('exact_barcode_join_hold', 'Workbook identity differs from export 92000111102229400149; identical image URL gives one candidate only.', 'Approve/reject the proposed identity correction separately. Do not join on floats, padding, name, URL or approximate digits. Preserve the human label against the original workbook string.'),
    }


def affected_benefits(code):
    if code in {'810003420213', '853218000931'}:
        return {'hydration'}
    if code in {'85239610305', '78742077130', '89094026479', '197644314881'}:
        return {'electrolyte'}
    return set(BENEFITS)


def build(verify_only=False):
    upstream = json.loads((BASE / 'beverage_02_v1/beverage_02_manifest.json').read_text(encoding='utf-8'))
    inputs = dict(upstream['input_sha256'])
    inputs.update(upstream['output_sha256'])
    inputs[upstream['script']] = upstream['script_sha256']
    for p in [BASE / 'beverage_02_v1/beverage_02_manifest.json', SOURCE,
              BASE / 'beverage_02_v1/hydration_electrolyte_image_review.csv']:
        inputs[rel(p)] = b01.sha(p)
    for name, digest in inputs.items():
        assert b01.sha(ROOT / name) == digest, 'Protected input changed: ' + name

    exported = {r['GTIN']: r for r in read_csv(BASE / 'beverage_02_v1/hydration_electrolyte_image_review.csv')}
    earlier = {r['barcode']: r for r in read_csv(BASE / 'beverage_02_v1/proposed_gold_label_review.csv')}
    cases_by_id = {r['case_id']: r for r in earlier.values()}
    wb = load_workbook(SOURCE, data_only=False, read_only=False)
    sheet = wb['hydration_electrolyte_image_rev']
    headers = [c.value for c in sheet[1]]
    assert len(headers) == 15 and sheet.max_row == 51
    imported, snapshot_sheets = [], []
    for s in wb:
        snapshot_sheets.append({'sheet': s.title, 'rows': s.max_row, 'columns': s.max_column,
                                'cells': [{'cell': c.coordinate, 'value': c.value, 'data_type': c.data_type,
                                           'number_format': c.number_format,
                                           'hyperlink': c.hyperlink.target if c.hyperlink else None,
                                           'comment': c.comment.text if c.comment else None,
                                           'comment_author': c.comment.author if c.comment else None}
                                          for row in s.iter_rows() for c in row if c.value is not None or c.comment]})
    for row_number, cells in enumerate(sheet.iter_rows(min_row=2), 2):
        raw = {headers[i]: c.value for i, c in enumerate(cells)}
        code = raw['GTIN']
        assert isinstance(code, str) and code.isdigit(), 'GTIN must remain exact text; no numeric coercion'
        assert raw['Your hydration label'] in STATES and raw['Your electrolyte-feature label'] in STATES
        assert raw['Image checked?'] == 'Yes'
        imported.append({'review_sheet': sheet.title, 'review_row': row_number, 'GTIN': code,
                         'product_name_as_reviewed': raw['product name'], 'image_URL_as_reviewed': raw['URL to picture (from OFF)'],
                         'human_hydration_label': raw['Your hydration label'], 'human_electrolyte_label': raw['Your electrolyte-feature label'],
                         'human_purpose_context_raw': raw['Purpose / context'], 'image_checked_raw': raw['Image checked?'],
                         'reviewer_notes_raw': raw['Reviewer notes'], 'reviewer': 'Julia',
                         'hydration_label_cell': f'K{row_number}', 'electrolyte_label_cell': f'L{row_number}',
                         'notes_cell': f'O{row_number}', 'all_original_columns_json': j(raw),
                         'workbook_sha256': inputs[rel(SOURCE)]})
    wb.close()
    assert len(imported) == len({r['GTIN'] for r in imported}) == 50
    exact = {r['GTIN'] for r in imported if r['GTIN'] in exported}
    assert len(exact) == 49

    con = b01.connection(b01.DB)
    db = {}
    # Preserve BEVERAGE 01's original logical query-row locator, not a new
    # filtered-query row number.
    query = '''SELECT a.*,p.query_category,p.product_name,p.image_url AS current_product_image_url
               FROM product_analysis a JOIN products p USING(barcode)
               WHERE a.pack_analysis_attempted=1 OR a.ocr_text IS NOT NULL OR a.llm_status IS NOT NULL
               ORDER BY a.barcode'''
    for ordinal, item in enumerate(con.execute(query), 1):
        row = dict(item)
        if row['barcode'] in exported:
            db[row['barcode']] = (row, b01.normalize(row, 'database/positioning_radar.db::product_analysis', ordinal, 'merged_database'))
    con.close()
    assert len(db) == 50
    observations = defaultdict(list)
    for code, (raw, obs) in db.items():
        observations[code].append(obs)
    inventory = read_csv(BASE / 'beverage_01_v1/source_inventory.csv')
    for source in inventory:
        if source['ocr_column'] != 'True' or not source['source'].endswith('.csv'):
            continue
        layer = 'raw_result_or_checkpoint' if Path(source['source']).name.startswith('vision_results') else 'merged_result_snapshot'
        with (ROOT / source['source']).open(encoding='utf-8-sig', newline='') as f:
            for row_number, raw in enumerate(csv.DictReader(f), 2):
                if raw.get('barcode') in exported:
                    observations[raw['barcode']].append(b01.normalize(raw, source['source'], row_number, layer))

    reconciliation, overlap, positives, results, exceptions = [], [], [], [], []
    specs = exception_spec()
    all_unchanged_legacy = []
    for review in imported:
        code = review['GTIN']
        joined = code if code in exact else None
        candidates = [k for k, v in exported.items() if v['URL to picture (from OFF)'] == review['image_URL_as_reviewed']] if not joined else []
        raw, obs = db[joined] if joined else ({}, None)
        text = obs['text'] if obs else ''
        earlier_case = earlier.get(joined)
        original = json.loads(review['all_original_columns_json'])
        declared_case = original['BEVERAGE 02 case']
        if declared_case:
            assert declared_case in cases_by_id and earlier_case and earlier_case['case_id'] == declared_case
            assert earlier_case['barcode'] == joined
            assert earlier_case['source_ocr_sha256'] == obs['text_sha256']
            overlap.append({'case_id': declared_case, 'barcode': code, 'review_row': review['review_row'],
                            'old_Codex_hydration_proposal': earlier_case['proposed_hydration'],
                            'human_hydration': review['human_hydration_label'],
                            'old_Codex_electrolyte_proposal': earlier_case['proposed_electrolyte'],
                            'human_electrolyte': review['human_electrolyte_label'],
                            'hydration_changed': earlier_case['proposed_hydration'] != review['human_hydration_label'],
                            'electrolyte_changed': earlier_case['proposed_electrolyte'] != review['human_electrolyte_label'],
                            'change_basis': 'Julia workbook columns K/L; three changes additionally confirmed by BEVERAGE 03 instruction',
                            'source_ocr_sha256': obs['text_sha256']})
        else:
            assert earlier_case is None
        if joined:
            assert review['image_URL_as_reviewed'] == exported[joined]['URL to picture (from OFF)']
            all_unchanged_legacy.append({'barcode': joined, 'legacy_claims_json_sha256': b01.text_sha(raw['claims_json'] or ''),
                                         'legacy_pack_claims_found': raw['pack_claims_found'], 'saved_OCR_sha256': obs['text_sha256']})
        note = review['reviewer_notes_raw'] or ''
        if re.search(r'back of|back of the|not fron', note, re.I):
            front_context = 'human_reported_non_front'
        elif obs and obs['context'] == 'front_of_pack':
            front_context = 'human_image_checked_saved_front_context_not_pixel_verified'
        elif obs and obs['context'] == 'mixed_pack_text':
            front_context = 'human_image_checked_saved_mixed_context'
        else:
            front_context = 'historical_non_front_or_no_exact_evidence_review_required'
        urls = sorted({o['request_url'] for o in observations.get(joined, []) if obs and o['text_sha256'] == obs['text_sha256'] and o['request_url']})
        original_URL_supported = review['image_URL_as_reviewed'] in urls
        derived_purpose = 'taste' if re.search('for taste', note, re.I) else None
        if code in specs:
            issue, finding, suggestion = specs[code]
            exceptions.append({'GTIN_as_reviewed': code, 'case_id': declared_case, 'human_hydration_unchanged': review['human_hydration_label'],
                               'human_electrolyte_unchanged': review['human_electrolyte_label'], 'issue': issue,
                               'affected_positioning_propositions': '|'.join(sorted(affected_benefits(code))),
                               'finding': finding, 'suggestion_NOT_applied': suggestion,
                               'candidate_barcode_NOT_joined': '|'.join(candidates), 'image_URL_as_reviewed': review['image_URL_as_reviewed'],
                               'status': 'Resolved evidence location; keep human label' if issue.startswith('resolved_') else 'Pending approval / evidence review'})
        reconciliation.append({
            'GTIN_as_reviewed': code, 'exact_join_barcode': joined, 'identity_status': 'exact_text_match' if joined else 'held_unmatched_review_identity',
            'candidate_barcode_NOT_joined': '|'.join(candidates), 'BEVERAGE_02_case_id': declared_case,
            'product_name_as_reviewed': review['product_name_as_reviewed'], 'image_URL_as_reviewed': review['image_URL_as_reviewed'],
            'human_hydration_unchanged': review['human_hydration_label'], 'human_electrolyte_unchanged': review['human_electrolyte_label'],
            'human_purpose_context_raw': review['human_purpose_context_raw'], 'purpose_derived_from_human_notes_NOT_raw': derived_purpose,
            'image_checked_raw': review['image_checked_raw'], 'reviewer_notes_raw': review['reviewer_notes_raw'],
            'reviewed_front_context_annotation': front_context, 'saved_context_unchanged': obs['context'] if obs else None,
            'review_image_is_saved_original_request_URL_for_same_OCR': original_URL_supported if obs else None,
            'saved_original_request_URLs_for_same_OCR': '|'.join(urls),
            'source_ocr_reference': obs['source'] if obs else None, 'source_ocr_row': obs['source_row'] if obs else None,
            'source_ocr_sha256': obs['text_sha256'] if obs else None, 'source_ocr_characters': len(text) if obs else None,
            'all_saved_text_versions_count': len(b01.dedup_texts(observations[joined])) if joined else 0,
            'old_raw_34_flags_json_unchanged': j(obs['flags']) if obs else None,
            'old_pack_claims_found_unchanged': raw.get('pack_claims_found'), 'old_success_and_no_claim': bool(obs and obs['valid_success'] and obs['claim_state'] == 'no_claims'),
            'review_exception': specs[code][0] if code in specs else None,
            'assessment_state': 'Human labels recorded; BEVERAGE 03 acceptance pending approval',
        })
        for benefit in BENEFITS:
            human = review['human_' + benefit + '_label']
            content, revised, ev, purpose, reason = proposed_detect(text, benefit, obs['context'] if obs else None)
            if human == 'detected':
                support = ev
                support_state = 'exact_OCR_proposition_support' if content == 'detected' else 'no_qualifying_exact_OCR_proposition'
                if not joined:
                    support = []
                    support_state = 'identity_hold_no_exact_join'
                elif content == 'ambiguous':
                    support_state = 'exact_descriptor_present_policy_pending'
                elif code == '3288110161324' and benefit == 'electrolyte':
                    support_state = 'human_positive_no_explicit_electrolyte_word_in_OCR'
                elif code == '85239610305' and benefit == 'electrolyte':
                    support_state = 'human_positive_mineral_only_definition_conflict'
                positives.append({'GTIN_as_reviewed': code, 'benefit': benefit, 'human_label_unchanged': human,
                                  'exact_join_barcode': joined, 'evidence_state': support_state, 'exact_saved_OCR_evidence_json': j(support),
                                  'human_note_unchanged': review['reviewer_notes_raw'], 'source_ocr_sha256': obs['text_sha256'] if obs else None,
                                  'front_context_annotation': front_context, 'detector_content_status': content,
                                  'purpose_from_saved_OCR': purpose, 'image_URL_as_reviewed': review['image_URL_as_reviewed'],
                                  'review_acceptance': 'Pending BEVERAGE 03 approval; positive words do not settle front eligibility'})
            methods = []
            if joined:
                old_status, old_reason, old_ev, old_purpose = b02.detect(text, benefit, 'context_rules_v0.1.0-draft')
            else:
                old_status, old_reason, old_ev, old_purpose = 'unassessable', 'Identity hold; no exact joined OCR', [], None
            methods.append(('existing_context_rules_v0.1.0-draft_UNCHANGED', old_status, old_status, old_ev, old_purpose, old_reason))
            methods.append(('revised_rules_v0.2.0-proposal', revised, content, ev, purpose, reason))
            for method, status, content_status, support, method_purpose, method_reason in methods:
                assert status in STATES and content_status in STATES
                for span in support:
                    assert text[span['start_0based']:span['end_exclusive']] == span['phrase']
                if not joined:
                    agreement = 'identity_hold_excluded_from_metrics'
                elif human in {'ambiguous', 'unassessable'}:
                    agreement = 'human_indeterminate:' + status
                elif status == 'detected':
                    agreement = 'TP_against_raw_human' if human == 'detected' else 'FP_against_raw_human'
                elif status == 'not_detected':
                    agreement = 'FN_against_raw_human' if human == 'detected' else 'TN_against_raw_human'
                else:
                    agreement = 'abstention_on_human_positive' if human == 'detected' else 'abstention_on_human_negative'
                held = code in specs and not specs[code][0].startswith('resolved_') and benefit in affected_benefits(code)
                results.append({'GTIN_as_reviewed': code, 'exact_join_barcode': joined, 'benefit': benefit, 'method_version': method,
                                'raw_human_label_unchanged': human, 'method_assessment_status': status, 'content_status_before_front_gate': content_status,
                                'comparison_to_raw_human': agreement, 'reason': method_reason, 'exact_OCR_evidence_json': j(support),
                                'purpose_from_saved_OCR': method_purpose, 'source_ocr_sha256': obs['text_sha256'] if obs else None,
                                'review_exception_hold': held, 'source_front_context_unchanged': obs['context'] if obs else None,
                                'comparison_scope': 'Reviewed/development cases; not independent validation'})

    assert len(overlap) == 11
    changed = {r['case_id'] for r in overlap if r['hydration_changed'] or r['electrolyte_changed']}
    assert changed == {'B01_006', 'B01_019', 'B01_028'}
    assert len(positives) == 46 and len(results) == 200
    metrics = []
    for method in sorted({r['method_version'] for r in results}):
        for benefit in BENEFITS:
            rr = [r for r in results if r['method_version'] == method and r['benefit'] == benefit and r['exact_join_barcode']]
            counts = Counter(r['comparison_to_raw_human'] for r in rr)
            tp = counts['TP_against_raw_human']; fp = counts['FP_against_raw_human']
            pos = sum(r['raw_human_label_unchanged'] == 'detected' for r in rr)
            metrics.append({'method_version': method, 'benefit': benefit, 'exactly_joined_products': len(rr), 'unmatched_review_identity_excluded': 1,
                            'raw_human_positive': pos, 'raw_human_negative': sum(r['raw_human_label_unchanged'] == 'not_detected' for r in rr),
                            'raw_human_indeterminate': sum(r['raw_human_label_unchanged'] in {'ambiguous', 'unassessable'} for r in rr),
                            'TP_against_raw_human': tp, 'TN_against_raw_human': counts['TN_against_raw_human'], 'FP_against_raw_human': fp,
                            'FN_binary_against_raw_human': counts['FN_against_raw_human'],
                            'abstentions_on_positive': counts['abstention_on_human_positive'], 'abstentions_on_negative': counts['abstention_on_human_negative'],
                            'FN_including_positive_abstention': pos - tp,
                            'precision_against_raw_human_DEVELOPMENT_ONLY': round(tp / (tp + fp), 6) if tp + fp else None,
                            'recall_against_raw_human_DEVELOPMENT_ONLY': round(tp / pos, 6) if pos else None,
                            'confirmed_TP_without_unresolved_exception': sum(r['comparison_to_raw_human'] == 'TP_against_raw_human' and not r['review_exception_hold'] for r in rr),
                            'confirmed_TN_without_unresolved_exception': sum(r['comparison_to_raw_human'] == 'TN_against_raw_human' and not r['review_exception_hold'] for r in rr),
                            'predicted_ambiguous': sum(r['method_assessment_status'] == 'ambiguous' for r in rr),
                            'predicted_unassessable': sum(r['method_assessment_status'] == 'unassessable' for r in rr),
                            'confusion_counts_including_indeterminate_json': j(counts),
                            'interpretation': 'Against literal human labels with unresolved conflicts retained; development only, not approved gold accuracy or holdout performance'})

    holdout = {
        'status': 'Proposal only; no holdout products selected or processed', 'size_proposal': 12,
        'region_design': '4 unique barcodes each from FR, UK+IE, US+CA; preserve country assignments',
        'exclusions_from_validation_design_NOT_population_exclusions': 'Exclude all 50 review-source/export identities and all 33 frozen BEVERAGE 01/02 cases from the holdout.',
        'blind_review': 'Freeze v0.2 policy, generic rules and candidate selection protocol before labels; human reviewers see exact saved image/OCR provenance, not predicted labels. Resolve identities and context before scoring.',
        'coverage': 'Seek independent real EN/FR positives, mineral/ingredient negatives, taste-only, descriptors and non-front controls. The 50-case review already exhausts the original hydration/electrolyte/mineral lexical candidates in the scoped saved corpus.',
        'positive_gap': 'No additional positive can be assumed. Inspect other saved OCR for predeclared alternative wording; if none qualifies, use the 12 as a negative/abstention holdout and defer positive recall validation to separately approved new evidence. Do not invent positives or recast reviewed products as independent holdout.',
        'gates': ['Approve BEVERAGE 03 exceptions/identity and descriptor policy', 'Freeze definitions and independent holdout protocol', 'Human adjudicate and hash labels before scoring'],
        'paid_calls': 0, 'core_RUN06_allocation_change': False, 'selected_barcodes': [],
    }
    return write_package(imported, snapshot_sheets, reconciliation, overlap, positives, results, exceptions, metrics,
                         holdout, all_unchanged_legacy, inputs, verify_only)


def write_package(imported, snapshot, reconciliation, overlap, positives, results, exceptions, metrics, holdout, legacy, inputs, verify_only):
    state_counts = [{ 'benefit': benefit, **{state: sum(r['human_' + benefit + '_label'] == state for r in imported) for state in ['detected', 'not_detected', 'ambiguous', 'unassessable']} } for benefit in BENEFITS]
    changes = [r for r in overlap if r['hydration_changed'] or r['electrolyte_changed']]
    confirmed = [m for m in metrics if m['method_version'].startswith('revised_')]
    pending = [e for e in exceptions if e['status'].startswith('Pending')]
    positive_states = Counter(r['evidence_state'] for r in positives)
    rows_for_report = [{**e, 'short_issue': e['issue'].replace('_', ' ')} for e in exceptions]
    report = f'''# BEVERAGE 03 — Human pack review reconciliation

**Prepared for approval. No paid calls, bulk backfill, prompt/taxonomy edits or RUN 06 changes.**

## 1. Human source and exact matching

Source: Julia's [reviewed workbook](beverage_02_v1/hydration_electrolyte_product_reviewed.xlsx), sheet `hydration_electrolyte_image_rev`, rows 2–51. Its SHA256 is `{inputs[rel(SOURCE)]}`. Only **K/L** supply human labels, **M** supplies raw purpose/context, **N** records image checked, and **O** supplies reviewer notes. Columns D–J and the policy sheet contain earlier guidance/proposals, preserved as source material rather than human decisions. All 50 rows say Image checked=Yes; all purpose/context cells are blank, so inferred purpose is stored in a separate derived field.

{markdown_table(state_counts, [('benefit','Human label'),('detected','Detected'),('not_detected','Not detected'),('ambiguous','Ambiguous'),('unassessable','Unassessable')])}

All workbook GTIN cells are text; their exact strings are preserved, without numeric conversion or padding. **49/50** match the original image export by exact barcode and image URL. The remaining workbook string **92000111102229400000** does not match any exported product. Its identical image URL points uniquely to **92000111102229400149**, whose saved OCR contains `PLANT-BASED HYDRATION`. This suggests a precision-loss/copy issue, but the cause is unverified. The candidate is **not joined**, its human label is retained against the original workbook string, and its two assessments are excluded from detector metrics until identity correction is approved.

The [human import](beverage_03_v1/human_review_import.csv), [workbook snapshot](beverage_03_v1/human_review_workbook_snapshot.json) and [reconciliation ledger](beverage_03_v1/review_reconciliation.csv) preserve the labels, notes, original preliminary columns, exact image URLs, source cells, OCR/legacy references and provenance. **49 exact products have saved OCR**, including the 38 exactly joined products outside the BEVERAGE 02 test set; the old template note about only 11 OCR counterparts describes its earlier preparation state, not current evidence availability.

## 2. Eleven BEVERAGE 02 overlaps and three confirmed changes

All 11 declared case IDs match both exact barcode and original full-OCR hash. Eight cases retain the proposed statuses; the three human changes are:

{markdown_table(changes, [('case_id','Case'),('barcode','Barcode'),('old_Codex_hydration_proposal','Old H proposal'),('human_hydration','Human H'),('old_Codex_electrolyte_proposal','Old E proposal'),('human_electrolyte','Human E')])}

B01_006 and B01_028 resolve hydration descriptor policy; B01_019 resolves the ZERO/electrolyte product presentation. These changes are recorded only in the new [overlap table](beverage_03_v1/beverage_02_overlap.csv). BEVERAGE 01/02 proposals and outputs remain unchanged; no Codex proposal is promoted to a human label for the other 22 frozen cases.

## 3. Revised positioning definitions

- **Hydration:** explicit hydration/rehydration communication and clearly presented hydration product/range descriptors qualify. This covers `PRIME / HYDRATION`, `HYDRATE`, `HYDRATION DRINK`, `SPARKLING HYDRATION`, `HYDRATES`, and `REHYDRATE`. Water, sports drink, powders/tablets/sachets or electrolytes alone establish no hydration positioning.
- **Electrolytes:** require explicit consumer-facing electrolyte(s) wording or its language equivalent. Individual magnesium, potassium, sodium and other minerals are insufficient. Ingredient/nutrition mentions remain distinct from a marketed feature.
- **Taste:** explicit electrolyte wording advertised for taste qualifies as an electrolyte feature, with purpose=taste; hydration is independently assessed. A blue water-drop graphic does not establish a textual hydration proposition.
- **Scope:** retain panel-specific consumer-facing wording, purpose and exact evidence. A back-panel electrolyte feature does not establish front-pack eligibility. Missing front evidence should produce a separate unassessable front-scope result, while Julia's original labels remain intact.
- **Compatibility:** fortification already exists among the 34 flags. Create no new mineral-fortification category, reclassify no historical fortification observation and change no priority taxonomy. Existing claims, hydration and electrolytes may coexist.

The [versioned definition proposal](beverage_03_v1/benefit_definition_registry_v0.2.0.json) incorporates Julia's requested policy. **REPLENISHER remains an exception:** the exact descriptor is present on 810003420213 and 853218000931, but does not explicitly say what is replenished. Preserve Julia's hydration-positive labels; suggest ambiguous hydration until that descriptor is expressly accepted. Accompanying electrolytes must not supply the hydration inference.

## 4. Exception decisions for approval

{markdown_table(rows_for_report, [('GTIN_as_reviewed','GTIN as reviewed'),('short_issue','Issue'),('suggestion_NOT_applied','Suggested treatment — not applied')])}

The [exception table](beverage_03_v1/exceptions_for_approval.csv) contains **{len(exceptions)} rows: {len(pending)} pending and two resolved evidence-location requests**. In particular:

- **78742077130:** exact OCR `ELECTROLYTE»` precedes `Vitamin Enhanced / Grape / Drink Mix`. **89094026479:** `WITH ELECTROLYTES` occurs twice. Their positive labels are supported by wording, independently of powder format, protein or other existing claims.
- **85239610305:** human note and OCR say minerals for taste, without electrolyte wording. The proposed electrolyte-negative wording assessment is a suggested change only; the original human positive remains untouched.
- **3288110161324:** Julia identifies a back panel and labels electrolytes positive, but the saved OCR contains no electrolyte word. Neither a sports-drink category nor listed minerals verifies that positive. **813694022469** differs: both ingredient `citrate (electrolytes)` and separate promotional `Plus Electrolytes` occur. Preserve the latter as back-panel wording, with front scope unassessable.
- **3564700590461 / 5000462001022:** preserve Julia's ambiguous labels; suggest front-scope unassessable, not negative. Their mineral panels do not show the unknown front.
- **5336636935634:** Julia reports a regular juice and negative labels, but saved OCR repeatedly says `Electrolyte / Solution`. This is an attribution/image-evidence conflict, not grounds to rewrite the human label or OCR. Original pixel identity/word attribution has not been independently verified here.

## 5. OCR capture versus human image observations

The [positive-evidence table](beverage_03_v1/positive_evidence.csv) covers **all 46 human-positive assessments**. Evidence states: `{j(dict(positive_states))}`. Each supported positive has exact uncorrected OCR phrases and offsets. Unsupported positives keep blank qualifying evidence and an explicit reason; nothing is invented to make a positive label appear supported.

The inspected exceptions establish **no confirmed lost positive phrase in a matched, immutable historical image**. For 197644314881 the hydration token is captured as `HYDRATE & ENERGITE`; the non-essential OCR error differs from Julia's “hydrate and energize,” while her possible electrolyte word is explicitly unreadable. For 3288110161324 the claimed electrolyte word is absent from OCR and no exact visible phrase was supplied; this is an unresolved evidence gap, not a proven OCR miss. For the unmatched juice identity the candidate OCR does contain `PLANT-BASED HYDRATION`, but is not attached to the workbook row without identity approval.

Julia's image review is the visual evidence source for this reconciliation. A separate direct-image fetch was unsuccessful; no new images/pixels were archived or independently visually adjudicated. Do not infer that current URL equality proves the OCR saw the same pixels. The ledger records matching original-request URL provenance separately from current/joined OFF references.

## 6. Re-evaluation of deterministic rules — development evidence

Ran the **unchanged BEVERAGE 02 context rules** and a **new isolated v0.2 proposal** on saved OCR. The new detector uses no barcodes, product names, human notes or labels as classification inputs. It accepts explicit hydration descriptors, requires electrolyte wording, treats REPLENISHER as policy-ambiguous, separates ingredient mentions from a promotional line, and reports content status separately from front-scope status. Historical non-front context produces an unassessable front-scope outcome, even where the content contains an electrolyte feature. No production extraction rule was edited.

{markdown_table(metrics, [('method_version','Method'),('benefit','Signal'),('TP_against_raw_human','TP'),('TN_against_raw_human','TN'),('FP_against_raw_human','FP'),('FN_binary_against_raw_human','Binary FN'),('abstentions_on_positive','Abstain on positive'),('abstentions_on_negative','Abstain on negative'),('predicted_ambiguous','Ambiguous'),('predicted_unassessable','Unassessable')])}

Each row uses **49 exactly joined products**, with human ambiguous/unassessable labels reported outside the definite positive/negative confusion counts. Positive abstentions count as recall misses; negative abstentions are not true negatives. Confusion counts, denominators, development precision/recall and every disagreement remain in [metrics](beverage_03_v1/deterministic_metrics.csv) and [200 per-assessment results](beverage_03_v1/deterministic_results.csv). Unresolved exception labels remain in raw-human comparisons; they are not silently corrected or dropped to improve performance.

On the revised method, evidence-confirmed agreement without an unresolved exception affecting that particular proposition is:

{markdown_table(confirmed, [('benefit','Signal'),('confirmed_TP_without_unresolved_exception','Confirmed TP'),('confirmed_TN_without_unresolved_exception','Confirmed TN')])}

The revised method still has the juice/OCR electrolyte disagreement, abstains on REPLENISHER hydration and missing-front evidence, and cannot reconstruct the unreadable electrolyte word from the image. A hydration descriptor hold does not invalidate separately supported electrolyte wording on the same product. **These are reviewed/development cases, not independent validation.** Final approved-gold scoring remains contingent on exception and identity decisions.

## 7. Holdout and approval boundary

Propose a **12-product holdout**, four per region, outside both this 50-product review and all 33 frozen BEVERAGE 01/02 cases. Freeze definitions, rules and selection protocol before blinded human labels. The original lexical-positive candidate pool has already been reviewed, so additional positives are not guaranteed. Look for predeclared alternative wording in other saved OCR; if none qualifies, use the holdout for negative/abstention challenges and defer positive recall validation to separately approved evidence. Do not reuse reviewed cases as independent validation or invent positives. The [holdout proposal](beverage_03_v1/holdout_proposal.json) selects no barcodes and authorizes no calls.

**Approval needed:** the exact barcode correction, the mineral-only positive, REPLENISHER descriptor policy, front-scope treatment and unresolved word/image attribution. All human labels remain preserved pending these decisions. No paid test, bulk backfill, core RUN 06 allocation change, prompt deployment or taxonomy update is authorized by this package.

## Evidence and preservation checks

Added one offline reconciliation script and this new versioned package. Verified 50 source rows / 100 human labels, 49 exact joins plus one identity hold, 11 case/barcode/OCR-hash overlaps, exactly three changed cases, all evidence offsets, 34 legacy flags and successful no-claim references. The [manifest](beverage_03_v1/beverage_03_manifest.json) records source/configuration/output hashes. All protected BEVERAGE 01/02 artifacts, saved OCR, databases, prompts, existing flags and upstream allocation evidence remain unchanged. **STOP for approval.**
'''
    payloads = {
        OUT / 'human_review_import.csv': cb(imported),
        OUT / 'review_reconciliation.csv': cb(reconciliation),
        OUT / 'beverage_02_overlap.csv': cb(overlap),
        OUT / 'positive_evidence.csv': cb(positives),
        OUT / 'exceptions_for_approval.csv': cb(exceptions),
        OUT / 'deterministic_results.csv': cb(results),
        OUT / 'deterministic_metrics.csv': cb(metrics),
        OUT / 'benefit_definition_registry_v0.2.0.json': jb(definitions()),
        OUT / 'holdout_proposal.json': jb(holdout),
        OUT / 'human_review_workbook_snapshot.json': jb({'source': rel(SOURCE), 'source_sha256': inputs[rel(SOURCE)], 'sheets': snapshot}),
        REPORT: report.encode('utf-8'),
    }
    manifest = {
        'audit': 'BEVERAGE_03_V1', 'status': 'Prepared; STOP for approval; no labels overwritten',
        'source_workbook': rel(SOURCE), 'source_workbook_sha256': inputs[rel(SOURCE)],
        'script': rel(Path(__file__)), 'script_sha256': b01.sha(Path(__file__)),
        'input_sha256': inputs, 'human_review_source_columns': {'hydration': 'K', 'electrolyte': 'L', 'purpose': 'M', 'image_checked': 'N', 'notes': 'O'},
        'review_rows': 50, 'human_assessments': 100, 'human_counts': state_counts,
        'exact_barcode_joins': 49, 'identity_holds': 1, 'overlapping_cases': 11,
        'changed_cases': sorted(r['case_id'] for r in changes),
        'exceptions': len(exceptions), 'pending_exception_rows': len(pending), 'human_positive_evidence_rows': len(positives),
        'deterministic_result_rows': len(results), 'metric_unit': '49 exact product matches; raw human labels; reviewed/development only',
        'legacy_and_OCR_reference_integrity': legacy,
        'external_image_verification': 'Direct-image web/browser access unsuccessful; visual statements attributed to Julia workbook, no local image export or independent image adjudication',
        'invariants': {'human_labels_changed': 0, 'database_writes': 0, 'paid_calls': 0, 'OCR_calls': 0,
                       'bulk_backfill': False, 'production_prompts_changed': False, 'core_RUN06_changed': False,
                       'new_mineral_fortification_taxonomy': False},
        'output_sha256': {rel(p): b01.text_sha(data.decode('utf-8')) for p, data in payloads.items()},
    }
    payloads[OUT / 'beverage_03_manifest.json'] = jb(manifest)
    for name, digest in inputs.items():
        assert b01.sha(ROOT / name) == digest, 'Protected input changed during preparation: ' + name
    if verify_only:
        for p, data in payloads.items():
            assert p.read_bytes() == data, 'Reproduction mismatch: ' + rel(p)
        print(j({'reproduced_files': len(payloads), 'unchanged_inputs_verified': len(inputs), 'paid_calls': 0}))
    else:
        if OUT.exists():
            old = json.loads((OUT / 'beverage_03_manifest.json').read_text(encoding='utf-8'))
            assert old['status'] == manifest['status'], 'Only an unapproved draft can be regenerated'
            for name, digest in old['output_sha256'].items():
                assert b01.sha(ROOT / name) == digest, 'Draft output was edited independently: ' + name
        else:
            assert not REPORT.exists(), 'New version only; never overwrite an existing report'
            OUT.mkdir()
        for p, data in payloads.items():
            p.write_bytes(data)
        print(json.dumps({'report': rel(REPORT), 'human_counts': state_counts, 'exact_joins': 49, 'overlap': 11,
                          'changes': [r['case_id'] for r in changes], 'exceptions': len(exceptions), 'metrics': metrics,
                          'positive_evidence_states': positive_states, 'files': len(payloads)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    build(parser.parse_args().verify_only)
