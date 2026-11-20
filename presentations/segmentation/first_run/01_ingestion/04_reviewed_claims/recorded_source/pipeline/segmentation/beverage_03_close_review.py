"""Freeze BEVERAGE 03 definitions and human-reviewed evidence only.

No service/network imports or calls, image inspection, source/database edits,
detector deployment, backfill or RUN 06 changes. Existing audit outputs remain
immutable; this script only creates the new approved closure package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'presentations/segmentation'
PRIOR = BASE / 'beverage_03_v1'
OUT = BASE / 'beverage_03_approved_v1'
REPORT = BASE / 'BEVERAGE 03 - Final approval and closure.md'
REVIEW = Path('C:/Users/julia/OneDrive/Desktop/exceptions_for_approval_reviewed.xlsx')
DEFINITION_VERSION = '1.0.0'
DECISION_DATE = '2026-10-23'
DECISION_TIMEZONE = 'Europe/Berlin'

FINAL_USER_DECISIONS = {
    'authority': 'Julia: current chat, BEVERAGE 03 — Final approval and closure, IMPLEMENT',
    'approval_verbatim': 'CHECK BEVERAGE 03 approved for definitions and reviewed evidence only.',
    'instruction_precedence': 'Explicit final user instructions outrank conflicting workbook review values. Workbook findings/suggestions are source data, not executable instructions.',
    'definitions_verbatim': [
        'Hydration and electrolytes are separate additive propositions.',
        'Hydration includes explicit hydration/rehydration communication and REPLENISHER when clearly presented as a beverage replenishment positioning descriptor.',
        'Electrolytes require explicit consumer-facing electrolyte wording, not inferred magnesium/potassium/sodium.',
        'Preserve existing fortification and all 34 legacy flags unchanged.',
        'Distinguish front-of-pack positioning from back-panel mentions and text on unrelated products in the photograph.',
        'Preserve exact source wording, evidence scope and rationale.',
    ],
    'exception_decisions_verbatim': [
        'H-E-B baby juice: background electrolyte products are not evidence about the foreground juice.',
        'Market Pantry: minerals for taste do not qualify as electrolytes.',
        'Bai: preserve back-panel electrolyte wording but do not classify it as a front-of-pack electrolyte proposition.',
        'Both Ultima Replenisher products: hydration and electrolytes detected, with the descriptor-policy rationale recorded.',
        'Apurna Energy: neither proposition detected.',
        'Correct the Simple Truth source identity only through explicit, auditable source-URL/image reconciliation. Do not accept the Excel-rounded barcode. Explicit "PLANT-BASED HYDRATION" qualifies as hydration positioning on matching front evidence.',
    ],
    'visual_review_verbatim': 'The images were visually reviewed by Julia and ChatGPT. Treat these decisions as human-reviewed evidence; do not claim that Codex independently inspected the images.',
    'limits_verbatim': 'No paid LLM calls, full historical backfill or changes to the core extraction prompts are authorized.',
}


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'pipeline/segmentation' / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


b01 = load_module('closure_b01', 'beverage_01_ocr_evidence_audit.py')


def rel(p):
    return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()


def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def jb(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def cb(records):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode('utf-8-sig')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_path(name):
    path = Path(name)
    return path if path.is_absolute() else ROOT / path


def table(rows, columns):
    def val(value):
        return '—' if value is None else str(value).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(label for key, label in columns) + ' |', '|' + '---|' * len(columns),
                      *['| ' + ' | '.join(val(row[key]) for key, label in columns) + ' |' for row in rows]])


def approved_exception_decisions():
    # Human adjudication, not a new detector. Every entry is traced to the
    # reviewed workbook and final chat direction in the decision log.
    return {
        '197644314881': ('detected', 'ambiguous', 'Hydration explicitly stated; the possible electrolyte word remains unreadable. Approved ambiguity is retained, not forced to a negative.'),
        '3288110161324': ('not_detected', 'not_detected', 'Apurna ENERGY product: neither explicit hydration nor electrolyte positioning established; sports-brand/category identity and minerals do not qualify.'),
        '3564700590461': ('not_detected', 'not_detected', 'Final human front review reports neither proposition on Marque Repère mineral water; earlier uncertainty is resolved by that review.'),
        '5000462001022': ('not_detected', 'not_detected', 'Final human review classifies Tesco natural mineral water as neither proposition; individual minerals do not establish positioning.'),
        '5336636935634': ('not_detected', 'not_detected', 'H-E-B foreground baby juice: electrolyte wording belongs to unrelated background products. Preserve OCR text but reject attribution to this product.'),
        '78742077130': ('not_detected', 'detected', 'Explicit ELECTROLYTE wording supports the product feature; powder/soluble format alone establishes neither signal.'),
        '810003420213': ('detected', 'detected', 'REPLENISHER is approved in this clearly presented beverage-replenishment positioning context; explicit electrolyte drink mix wording independently supports electrolytes. No hydration inference from minerals, electrolytes or graphics.'),
        '813694022469': ('not_detected', 'not_detected', 'Final human front review classifies neither proposition. Preserve Plus Electrolytes as a back-panel feature and citrate (electrolytes) as ingredient context; neither creates a front-pack positive.'),
        '85239610305': ('not_detected', 'not_detected', 'Market Pantry minerals for taste is not explicit electrolyte positioning and provides no hydration proposition.'),
        '853218000931': ('detected', 'detected', 'REPLENISHER is approved as beverage replenishment positioning in the reviewed presentation; 6 Essential Electrolytes and DAILY ELECTROLYTE DRINK MIX independently support electrolyte positioning.'),
        '89094026479': ('not_detected', 'detected', 'WITH ELECTROLYTES explicitly supports the electrolyte feature, independently of protein and sachet format.'),
        '92000111102229400000': ('detected', 'not_detected', 'Explicit final user instruction overrides workbook NO: reconciled Simple Truth front evidence says PLANT-BASED HYDRATION. Canonical source identity is proved by original URL/export/database reconciliation, never by Excel-rounded numeric cells.'),
    }


def approved_definitions():
    return {
        'registry_id': 'independent_beverage_positioning', 'definition_version': DEFINITION_VERSION,
        'status': 'Approved and frozen', 'decision_date': DECISION_DATE, 'decision_timezone': DECISION_TIMEZONE,
        'approved_by': 'Julia', 'scope': 'Definitions and human-reviewed evidence only; no production implementation approval',
        'propositions_independent_and_additive': True,
        'hydration': {
            'positive': 'Explicit hydration/rehydration communication, clearly presented hydration product/range descriptors, and REPLENISHER when clearly presented as a beverage replenishment positioning descriptor.',
            'descriptor_context': 'Accept the reviewed Ultima Replenisher presentations under the descriptor policy. Do not treat every occurrence of replenish/replenisher in any context as hydration.',
            'non_evidence': 'Water, coconut-water or sports-drink category, powder/tablet/sachet format, individual minerals, electrolytes alone and water/fruit graphics alone do not establish hydration positioning.',
            'examples_en': ['HYDRATION DRINK', 'HYDRATE', 'hydration by nature.', 'PLANT-BASED HYDRATION', 'REPLENISHER in a clearly presented beverage replenishment positioning descriptor'],
            'examples_fr_illustrative_not_new_gold': ['hydratation', 'réhydratation', 'boisson hydratante'],
        },
        'electrolyte': {
            'positive': 'Explicit consumer-facing electrolyte(s) wording or its language equivalent attributed to the reviewed product.',
            'non_evidence': 'Magnesium, potassium, sodium or other individual minerals, nutrition values, ingredient-only mentions, sports category and powder format alone are insufficient.',
            'taste': 'Explicit electrolytes advertised for taste qualify as an electrolyte feature; preserve stated purpose separately and infer no hydration.',
            'examples_en': ['WITH ELECTROLYTES', 'natural electrolytes', 'ELECTROLYTE SPORTS DRINK', 'electrolytes added for taste'],
            'examples_fr_illustrative_not_new_gold': ['avec électrolytes', 'électrolytes ajoutés pour le goût'],
        },
        'attribution_and_scope': {
            'front': 'Front-of-pack positioning labels refer to the target product and approved reviewed front evidence.',
            'back': 'Preserve back-panel ingredient and promotional mentions separately; a back-panel feature is not a front-pack positive.',
            'background': 'Words on unrelated products in a photograph are excluded as evidence for the target product, even when present in saved OCR.',
            'purpose': 'Store exact wording, stated/derived purpose, evidence scope and rationale separately from the two labels.',
            'negative': 'not_detected means no qualifying proposition in the approved reviewed scope, not a universal statement about every pack version.',
            'uncertainty': 'Retain detected / not_detected / ambiguous / unassessable. Approved ambiguity is valid reviewed evidence. No assessment must never be coerced to a negative.',
        },
        'taxonomy_compatibility': 'Fortification is already tracked. Preserve fortification and all 34 legacy flags, successful no-claim results and priority taxonomy unchanged. Create no mineral-fortification category. Emerging propositions are independent additive evidence.',
        'image_review_attribution': 'Julia and ChatGPT, as explicitly confirmed by Julia. Codex independently inspected no images.',
        'provenance_limitations_do_not_reopen_definitions': True,
    }


def read_review(prior_exceptions):
    wb = load_workbook(REVIEW, data_only=False, read_only=False)
    assert wb.sheetnames == ['exceptions_for_approval']
    sheet = wb.worksheets[0]
    assert sheet.max_row == 13 and sheet.max_column == 11
    headers = [c.value for c in sheet[1]]
    assert headers[-1] == "julia's review"
    by_url = {r['image_URL_as_reviewed']: r for r in prior_exceptions}
    assert len(by_url) == 12
    with ZipFile(REVIEW) as archive:
        tree = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    xml_values = {c.attrib['r']: (c.find('m:v', ns).text if c.find('m:v', ns) is not None else None)
                  for c in tree.findall('.//m:c', ns)}
    imported = {}
    snapshot = []
    for number, row in enumerate(sheet.iter_rows(min_row=2), 2):
        raw = {headers[i]: c.value for i, c in enumerate(row)}
        url = raw['image_URL_as_reviewed']
        assert url in by_url
        old = by_url[url]
        code = old['GTIN_as_reviewed']
        assert raw['issue'] == old['issue'] and raw['finding'] == old['finding']
        assert raw['human_hydration_unchanged'] == old['human_hydration_unchanged']
        assert raw['human_electrolyte_unchanged'] == old['human_electrolyte_unchanged']
        if code != '92000111102229400000':
            value = raw['GTIN_as_reviewed']
            assert isinstance(value, int) and value < 10**15 and str(value) == code
            match_basis = 'Exact representable integer equals original exception barcode; original URL and issue also match'
        else:
            # A13 and I13 are rounded scientific-number cells. Neither is
            # interpreted as a product identifier. Link this review row to
            # its prior exception by exact preserved URL plus issue/finding.
            assert row[0].data_type == 'n' and row[8].data_type == 'n'
            match_basis = 'Exact original exception URL, issue and finding; numeric A/I cells explicitly rejected as identifiers'
        assert isinstance(raw["julia's review"], str) and raw["julia's review"].strip()
        imported[code] = {'review_row': number, 'review_cell': f'K{number}', 'review_note': raw["julia's review"],
                          'raw_GTIN_cell_repr': repr(row[0].value), 'raw_GTIN_XML_numeric_literal': xml_values.get(f'A{number}'),
                          'raw_candidate_cell_repr': repr(row[8].value), 'raw_candidate_XML_numeric_literal': xml_values.get(f'I{number}'),
                          'row_match_basis': match_basis, 'original_columns': raw}
        snapshot.append({'row': number, 'matched_prior_exception_id': code, 'cells': [
            {'cell': c.coordinate, 'value_repr': repr(c.value), 'value_type': c.data_type, 'number_format': c.number_format,
             'raw_XML_v': xml_values.get(c.coordinate), 'comment': c.comment.text if c.comment else None,
             'hyperlink': c.hyperlink.target if c.hyperlink else None} for c in row]})
    wb.close()
    assert len(imported) == 12
    return imported, snapshot


def build(verify_only=False):
    previous = json.loads((PRIOR / 'beverage_03_manifest.json').read_text(encoding='utf-8'))
    inputs = dict(previous['input_sha256'])
    inputs.update(previous['output_sha256'])
    inputs[previous['script']] = previous['script_sha256']
    inputs[rel(PRIOR / 'beverage_03_manifest.json')] = b01.sha(PRIOR / 'beverage_03_manifest.json')
    inputs[rel(REVIEW)] = b01.sha(REVIEW)
    # Protect all files in the three original audit directories, including
    # authored proposal inputs and Julia's first workbook, not just manifests.
    for folder in [BASE / 'beverage_01_v1', BASE / 'beverage_02_v1', PRIOR]:
        for p in folder.rglob('*'):
            if p.is_file():
                key = rel(p)
                actual = b01.sha(p)
                if key in inputs:
                    assert actual == inputs[key], 'Protected artifact changed before closure: ' + key
                inputs[key] = actual
    for name, expected in inputs.items():
        assert b01.sha(source_path(name)) == expected, 'Protected input changed: ' + name

    initial = read_csv(PRIOR / 'human_review_import.csv')
    recon = {r['GTIN_as_reviewed']: r for r in read_csv(PRIOR / 'review_reconciliation.csv')}
    old_exceptions = read_csv(PRIOR / 'exceptions_for_approval.csv')
    reviewed, snapshot = read_review(old_exceptions)
    decisions = approved_exception_decisions()
    assert set(decisions) == set(reviewed) == {r['GTIN_as_reviewed'] for r in old_exceptions}
    original_export = read_csv(BASE / 'beverage_02_v1/hydration_electrolyte_image_review.csv')
    by_source_code = {r['GTIN']: r for r in original_export}
    b02_cases = {r['barcode']: r for r in read_csv(BASE / 'beverage_02_v1/proposed_gold_label_review.csv')}

    original_bad = '92000111102229400000'
    old_hold = recon[original_bad]
    url = old_hold['image_URL_as_reviewed']
    matches = [r for r in original_export if r['URL to picture (from OFF)'] == url]
    assert len(matches) == 1
    parsed = urlparse(url)
    assert parsed.hostname == 'images.openfoodfacts.org'
    match = re.fullmatch(r'/images/products/(\d+)/(\d+)/(\d+)/(\d+)/front_[^/]+\.jpg', parsed.path)
    assert match
    canonical = ''.join(match.groups())
    assert canonical == matches[0]['GTIN'] == old_hold['candidate_barcode_NOT_joined'] == '92000111102229400149'
    con = b01.connection(b01.DB)
    con.row_factory = __import__('sqlite3').Row
    source_records = {}
    for exported in original_export:
        code = exported['GTIN']
        item = con.execute('SELECT a.*,p.product_name,p.image_url FROM product_analysis a JOIN products p USING(barcode) WHERE barcode=?', (code,)).fetchone()
        assert item is not None
        source_records[code] = dict(item)
    con.close()
    corrected = source_records[canonical]
    assert corrected['image_url'] == url and corrected['image_context'] == 'front_of_pack'
    assert 'PLANT-BASED HYDRATION' in corrected['ocr_text']
    identity = {
        'reconciliation_id': 'BEV03-SIMPLE-TRUTH-IDENTITY-001', 'status': 'Approved source-identity reconciliation only; no database correction',
        'original_review_barcode_text_preserved': original_bad,
        'rejected_exception_workbook_numeric_cells': {'A13': reviewed[original_bad]['raw_GTIN_XML_numeric_literal'], 'I13': reviewed[original_bad]['raw_candidate_XML_numeric_literal']},
        'numeric_cells_used_as_identity': False, 'canonical_source_barcode': canonical,
        'original_OFF_image_URL_preserved': url, 'barcode_derived_from_exact_image_URL_path': canonical,
        'original_export': rel(BASE / 'beverage_02_v1/hydration_electrolyte_image_review.csv'),
        'export_unique_same_URL_match': matches[0], 'database_source': 'database/positioning_radar.db',
        'database_lookup': {'table': 'products JOIN product_analysis USING(barcode)', 'exact_barcode': canonical},
        'database_image_URL_equals_original_export_and_review_URL': True,
        'database_saved_context_unchanged': corrected['image_context'],
        'database_saved_OCR_sha256': b01.text_sha(corrected['ocr_text']), 'exact_saved_OCR_phrase': 'PLANT-BASED HYDRATION',
        'matching_front_image_review': 'Confirmed by Julia final user instruction; visual review by Julia and ChatGPT, not independently by Codex',
        'workbook_review_note_verbatim': reviewed[original_bad]['review_note'],
        'final_instruction_overrides_workbook_NO': True,
        'authority': FINAL_USER_DECISIONS['exception_decisions_verbatim'][-1],
        'remaining_limitations': ['Historical pixel hashes absent; URL/source reconciliation does not reconstruct original pixels',
                                  'No source numeric normalization, broad barcode repair or other identity correction authorized'],
    }

    labels, decision_log, changes, evidence = [], [], [], []
    for old in initial:
        original_code = old['GTIN']
        code = canonical if original_code == original_bad else original_code
        record = source_records[code]
        previous_row = recon[original_code]
        text = record['ocr_text']
        raw_claims = json.loads(record['claims_json'] or '{}')
        flags = {k: b01.boolean(raw_claims.get(k)) for k in b01.FIELDS}
        assert len(flags) == 34
        if original_code != original_bad:
            assert flags == json.loads(previous_row['old_raw_34_flags_json_unchanged'])
            assert b01.text_sha(text) == previous_row['source_ocr_sha256']
        assert old['image_URL_as_reviewed'] == by_source_code[code]['URL to picture (from OFF)']
        h, e, rationale = decisions.get(original_code, (old['human_hydration_label'], old['human_electrolyte_label'], 'Original Julia pack-review labels retained under the approved independent positioning definitions.'))
        override = original_code == original_bad
        rev = reviewed.get(original_code)
        if original_code in decisions:
            decision_log.append({
                'original_review_barcode': original_code, 'canonical_source_barcode': code, 'case_id': previous_row['BEVERAGE_02_case_id'],
                'issue': previous_row['review_exception'], 'initial_hydration': old['human_hydration_label'], 'initial_electrolyte': old['human_electrolyte_label'],
                'final_front_hydration': h, 'final_front_electrolyte': e,
                'hydration_changed_from_initial_human': h != old['human_hydration_label'],
                'electrolyte_changed_from_initial_human': e != old['human_electrolyte_label'],
                'reviewed_exception_cell': rev['review_cell'], 'reviewed_exception_note_verbatim': rev['review_note'],
                'explicit_final_user_instruction_overrides_workbook': override,
                'final_rationale': rationale,
                'decision_status': 'Closed; approved ambiguity retained' if e == 'ambiguous' else 'Closed; final human-reviewed decision',
                'raw_workbook_GTIN_repr_NOT_join_key': rev['raw_GTIN_cell_repr'],
                'raw_workbook_GTIN_XML_numeric_literal_NOT_join_key': rev['raw_GTIN_XML_numeric_literal'],
                'raw_workbook_candidate_XML_numeric_literal_NOT_join_key': rev['raw_candidate_XML_numeric_literal'],
                'review_row_reconciliation_basis': rev['row_match_basis'], 'original_image_URL_preserved': old['image_URL_as_reviewed'],
                'visual_review_attribution': 'Julia and ChatGPT; explicitly confirmed by Julia; not independent Codex inspection',
            })
        for benefit, final in [('hydration', h), ('electrolyte', e)]:
            original = old['human_' + benefit + '_label']
            if original != final:
                changes.append({'original_review_barcode': original_code, 'canonical_source_barcode': code, 'proposition_front_scope': benefit,
                                'initial_human_label': original, 'approved_final_label': final,
                                'decision_basis': rationale, 'reviewed_exception_cell': rev['review_cell'],
                                'reviewed_exception_note_verbatim': rev['review_note']})

        back = 'detected' if code == '813694022469' else None
        attribution = 'foreground_product_front' if code not in {'813694022469', '5336636935634'} else ('back_panel_feature_separate_from_front' if back else 'electrolyte_words_on_unrelated_background_products')
        case = b02_cases.get(code, {})
        source_urls = previous_row['saved_original_request_URLs_for_same_OCR']
        # The approved canonical identity was previously held, so find any
        # actual same-text raw request reference rather than claiming the
        # joined current database URL is an original request URL.
        if original_code == original_bad:
            source_urls = ''
        labels.append({
            'barcode': code, 'product_name_as_initially_reviewed': old['product_name_as_reviewed'],
            'hydration_positioning_front': h, 'electrolyte_positioning_front': e,
            'electrolyte_back_panel_feature_observation': back,
            'initial_review_barcode_preserved': original_code,
            'initial_human_hydration_preserved': old['human_hydration_label'], 'initial_human_electrolyte_preserved': old['human_electrolyte_label'],
            'BEVERAGE_02_case_id': previous_row['BEVERAGE_02_case_id'],
            'BEVERAGE_02_Codex_hydration_proposal_NOT_human': case.get('proposed_hydration'),
            'BEVERAGE_02_Codex_electrolyte_proposal_NOT_human': case.get('proposed_electrolyte'),
            'original_image_URL_preserved': old['image_URL_as_reviewed'],
            'saved_original_request_URLs_same_OCR': source_urls,
            'original_request_URL_provenance': 'known_saved_raw_reference_not_pixel_verification' if source_urls else 'not_established_current_or_joined_reference_only',
            'evidence_scope_and_attribution': attribution,
            'initial_reviewer_notes_preserved': old['reviewer_notes_raw'],
            'final_exception_review_note_preserved': rev['review_note'] if rev else None,
            'purpose_context_separate_from_labels': 'taste' if re.search('for taste', old['reviewer_notes_raw'] or '', re.I) else None,
            'approved_rationale': rationale, 'source_OCR_sha256': b01.text_sha(text),
            'source_OCR_reference': f'database/positioning_radar.db::product_analysis[barcode={code}]',
            'saved_OCR_context_unchanged': record['image_context'],
            'legacy_34_flags_json_unchanged': compact(flags), 'legacy_claims_json_sha256_unchanged': b01.text_sha(record['claims_json'] or ''),
            'legacy_pack_claims_found_unchanged': record['pack_claims_found'],
            'identity_reconciliation_id': identity['reconciliation_id'] if override else None,
            'visual_reviewers_user_confirmed': 'Julia and ChatGPT', 'independent_Codex_image_inspection': False,
            'review_status': 'human_reviewed_approved_frozen', 'definition_version': DEFINITION_VERSION,
            'approval_date': DECISION_DATE, 'approval_timezone': DECISION_TIMEZONE,
        })

        # Preserve literal wording from the unchanged OCR, including wording
        # rejected because it belongs to a different panel or product.
        observations = []
        for benefit, expression in [('hydration', b01.COMPILED['hydration_wording']),
                                    ('electrolyte', b01.COMPILED['electrolyte_wording']),
                                    ('hydration_descriptor', re.compile(r'\breplenisher\b', re.I))]:
            for m in expression.finditer(text):
                left = text.rfind('\n', 0, m.start()) + 1
                right = text.find('\n', m.end())
                right = len(text) if right < 0 else right
                phrase = text[left:right]
                role = 'target_product_front_positioning'
                if code == '5336636935634' and benefit == 'electrolyte':
                    role = 'unrelated_background_product_not_target_evidence'
                elif code == '813694022469' and benefit == 'electrolyte':
                    role = 'back_panel_ingredient_mention' if re.search(r'citrate', phrase, re.I) else 'back_panel_promotional_feature_not_front'
                elif benefit == 'hydration_descriptor':
                    role = 'approved_contextual_beverage_replenishment_descriptor'
                observations.append((benefit, phrase, left, right, role))
        for expression, role, benefit in [
            (r'\b(?:for taste|Added for Taste)\b', 'taste_purpose_not_hydration_inference', 'purpose'),
            (r'Minerals for Taste', 'individual_minerals_not_electrolyte_positioning', 'mineral_wording'),
            (r'\bENERGIE\b', 'energy_identity_not_hydration_or_electrolytes', 'product_identity'),
        ]:
            for m in re.finditer(expression, text, re.I):
                observations.append((benefit, m.group(), m.start(), m.end(), role))
        for benefit, phrase, left, right, role in observations:
            assert text[left:right] == phrase
            evidence.append({'barcode': code, 'wording_family_NOT_legacy_taxonomy': benefit, 'exact_saved_OCR_wording': phrase,
                             'start_0based': left, 'end_exclusive': right, 'wording_attribution_and_scope': role,
                             'front_hydration_label': h, 'front_electrolyte_label': e, 'back_electrolyte_feature': back,
                             'source_OCR_sha256': b01.text_sha(text), 'original_image_URL_preserved': old['image_URL_as_reviewed'],
                             'image_attribution_authority': 'Julia and ChatGPT visual review, user-confirmed; no independent Codex image inspection',
                             'rationale': rationale if rev else 'Literal OCR wording retained with approved human review scope'})

    assert len(labels) == len({r['barcode'] for r in labels}) == 50
    assert len(decision_log) == 12 and len(changes) == 9
    assert Counter(r['hydration_positioning_front'] for r in labels) == {'detected': 23, 'not_detected': 27}
    assert Counter(r['electrolyte_positioning_front'] for r in labels) == {'detected': 20, 'not_detected': 29, 'ambiguous': 1}
    return write(labels, decision_log, changes, evidence, identity, snapshot, inputs, verify_only)


def write(labels, decisions, changes, evidence, identity, snapshot, inputs, verify_only):
    summary = [{'proposition': name, **{status: sum(r[field] == status for r in labels) for status in ['detected', 'not_detected', 'ambiguous', 'unassessable']}}
               for name, field in [('Hydration — front', 'hydration_positioning_front'), ('Electrolytes — front', 'electrolyte_positioning_front')]]
    limitations = {
        'status': 'Documented limitations; no unresolved approval holds and no reopening of approved definitions',
        'visual_review_attribution': 'Julia and ChatGPT, as confirmed by Julia; Codex independently inspected no images',
        'items': [
            'Original OFF image URLs are preserved, but immutable historical pixels, pixel hashes, OCR geometry and confidence are unavailable. A URL/reference reconciliation is not historical pixel reconstruction.',
            'Bai back-panel Plus Electrolytes is retained separately from its negative front-of-pack electrolyte label; citrate (electrolytes) remains ingredient evidence.',
            'H-E-B OCR captured words on unrelated background products; those exact words remain saved but are not attributed to the foreground baby juice.',
            '197644314881 retains an approved ambiguous electrolyte label because the word is unreadable; hydration is detected. This is a final reviewed uncertainty, not an open definition decision.',
            'Final human front reviews for previously back-panel/uncertain products are recorded from the reviewed workbook/user instruction; replacement front-image URLs/pixels were not supplied and are not fabricated. Original URLs are preserved even when they depict the back.',
            'REPLENISHER acceptance is contextual beverage positioning, not an automatic match for every replenish/replenisher token or a physiological efficacy conclusion.',
            'The 50 reviewed/development cases are not an independent validation set, do not measure market prevalence, and do not approve the earlier draft detector or establish production accuracy.',
            'Earlier no-claim outcomes are unchanged taxonomy-relative observations; additional human positioning labels do not rewrite historical results.',
        ],
    }
    payloads = {
        OUT / 'frozen_human_reviewed_labels.csv': cb(labels),
        OUT / 'exception_decision_log.csv': cb(decisions),
        OUT / 'classification_changes.csv': cb(changes),
        OUT / 'wording_evidence.csv': cb(evidence),
        OUT / 'benefit_definition_registry_v1.0.0.json': jb(approved_definitions()),
        OUT / 'source_identity_reconciliation.json': jb(identity),
        OUT / 'reviewed_exception_workbook_snapshot.json': jb({'source': rel(REVIEW), 'sha256': inputs[rel(REVIEW)], 'rows': snapshot}),
        OUT / 'exceptions_for_approval_reviewed.xlsx': REVIEW.read_bytes(),
        OUT / 'approval_authority.json': jb(FINAL_USER_DECISIONS),
        OUT / 'documented_limitations.json': jb(limitations),
    }
    report = f'''# BEVERAGE 03 — Final approval and closure

**CHECK BEVERAGE 03 APPROVED AND CLOSED — {DECISION_DATE}, {DECISION_TIMEZONE}.**

Approval covers **positioning definitions and the 50-product human-reviewed evidence set only**. Visual review is attributed to **Julia and ChatGPT**, as confirmed by Julia. **Codex independently inspected no images.** No paid calls, backfill, core prompt changes or RUN 06 changes were made or authorized.

## Frozen definitions — v{DEFINITION_VERSION}

- Hydration and electrolytes are independent, additive propositions.
- Hydration includes explicit hydration/rehydration communication, clearly presented hydration product/range descriptors, and **REPLENISHER when clearly presented as beverage replenishment positioning**. The reviewed Ultima presentations qualify. This does not create a rule that every replenish token, water graphic, electrolyte product or sports drink implies hydration.
- Electrolytes require explicit consumer-facing electrolyte wording or a language equivalent. Individual magnesium, potassium, sodium and other minerals are insufficient. An explicit taste-purpose electrolyte feature qualifies, with purpose recorded separately and no automatic hydration inference.
- Front-pack target-product positioning, back-panel features/ingredients and text on unrelated background products remain separate evidence scopes.
- Fortification and **all 34 legacy flags**, priority taxonomy and historical successful no-claim outcomes remain unchanged. No new mineral-fortification category was created.

The [approved definition registry](beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json) is frozen. Approval does not deploy a detector or change the core extraction pipeline.

## Approved reviewed label set

{table(summary, [('proposition','Front positioning'),('detected','Detected'),('not_detected','Not detected'),('ambiguous','Ambiguous'),('unassessable','Unassessable')])}

All **50 canonical source barcodes** are unique. The [frozen labels](beverage_03_approved_v1/frozen_human_reviewed_labels.csv) preserve original labels, notes, source URLs, old Codex proposals for the 11 overlaps, saved OCR hashes, legacy references, final rationale and review attribution. One approved ambiguous electrolyte result remains on **197644314881**; it is a documented final outcome, not a pending exception.

## Twelve exceptions resolved

{table(decisions, [('canonical_source_barcode','Canonical source barcode'),('final_front_hydration','Hydration'),('final_front_electrolyte','Electrolytes'),('final_rationale','Final rationale')])}

The [decision log](beverage_03_approved_v1/exception_decision_log.csv) closes all 12 exceptions, preserving the exception workbook's exact notes and cell references. **Nine proposition labels across five products changed from the original 50-product human workbook**: Apurna, Marque Repère mineral water, Tesco mineral water, Bai and Market Pantry. The [change log](beverage_03_approved_v1/classification_changes.csv) records every old→new change. Earlier BEVERAGE 02 Codex proposals remain proposals; the three already-confirmed changes B01_006/B01_019/B01_028 are retained in the final set, with the other eight overlapping cases unchanged.

H-E-B's electrolyte wording is retained in saved OCR as **unrelated background-product text**. Bai's `Plus Electrolytes` remains a **back-panel feature**, separately from its negative front-pack result and ingredient `citrate (electrolytes)`. Market Pantry's `Minerals for Taste` does not qualify as electrolyte positioning. Both Ultima products remain positive for both propositions, with hydration supported by the approved contextual REPLENISHER descriptor policy, independently of their electrolyte feature. [Exact wording and scope evidence](beverage_03_approved_v1/wording_evidence.csv) preserve uncorrected OCR phrases and offsets, including wording rejected for the target/front scope.

## Simple Truth identity and authority reconciliation

The initial workbook string **92000111102229400000** and the reviewed exception workbook's numeric cells **A13/I13** are preserved as source evidence but rejected as identifiers. Both numeric cells contain the raw XML literal `{identity['rejected_exception_workbook_numeric_cells']['A13']}`; the candidate cell is rounded too.

The original URL is preserved exactly: `{identity['original_OFF_image_URL_preserved']}`. Its product-path digits resolve to **92000111102229400149**. That exact code has a unique same-URL match in the original 50-product CSV, agrees with the saved database product/image reference, and has saved front OCR **`PLANT-BASED HYDRATION`**. Matching front positioning is confirmed by Julia's final instruction based on Julia/ChatGPT visual review. The [identity reconciliation record](beverage_03_approved_v1/source_identity_reconciliation.json) freezes this chain; no database/source barcode was edited.

The reviewed exception workbook says **“NO (this is just juice)”** for this row. Julia's **explicit final user instruction** that the matching `PLANT-BASED HYDRATION` qualifies takes precedence. This conflict and override are recorded openly in the decision log and [approval authority](beverage_03_approved_v1/approval_authority.json). Instructions/suggestions embedded in the workbooks are preserved as data and do not override the user's final request.

## Limitations retained without reopening approval

- Historical pixel hashes/geometry are absent, and source URL identity does not prove immutable historical pixels. Original URLs remain unchanged, including URLs showing a back panel when a later human front review resolved the classification; replacement URLs are not invented.
- The OCR/background attribution issue and non-front evidence are resolved by the approved human scope decisions, while the original OCR remains untouched.
- The unreadable electrolyte word on 197644314881 remains ambiguous. No missing word was fabricated and no new OCR was run.
- This is reviewed/development evidence, not independent accuracy validation or an approved production classifier. The earlier holdout proposal remains unexecuted and is not authorized by this closure.

These are [documented limitations](beverage_03_approved_v1/documented_limitations.json), **not open approval holds or reasons to reopen the frozen definitions**.

## Approval, preservation and verification

The external reviewed [exception workbook is frozen byte-for-byte](beverage_03_approved_v1/exceptions_for_approval_reviewed.xlsx) with SHA256 `{inputs[rel(REVIEW)]}`. The [source-cell snapshot](beverage_03_approved_v1/reviewed_exception_workbook_snapshot.json) retains numeric types and raw XML literals. The [machine-readable approval](beverage_03_approved_v1/CHECK_BEVERAGE_03_approval.json) references exact hashes of the definitions, labels, decisions, evidence, identity correction and source review. The [closure manifest](beverage_03_approved_v1/beverage_03_closure_manifest.json) ties the package to protected source hashes and the closure script.

Original BEVERAGE 01/02/03 reports and outputs remain unchanged, including their earlier “pending review” statuses as historical snapshots; **this separate closure record supersedes their open BEVERAGE 03 approval status**. Saved OCR, databases, historical claim flags, fortification and sampling decisions remain unchanged. This closure records an approved evidence set, without rewriting history.

**STOP after closure and verification. No paid LLM calls, historical bulk backfill, core extraction prompt changes or additional execution approval.**
'''
    payloads[REPORT] = report.encode('utf-8')
    approval = {
        'decision': 'CHECK BEVERAGE 03 approved and closed', 'decision_date': DECISION_DATE, 'decision_timezone': DECISION_TIMEZONE,
        'approved_by': 'Julia', 'approval_scope': ['Versioned human-reviewed positioning definitions', 'Frozen 50-product reviewed evidence and final classifications', 'Twelve resolved exceptions and the explicit Simple Truth source-identity reconciliation'],
        'authority_record': rel(OUT / 'approval_authority.json'), 'authority_sha256': digest(payloads[OUT / 'approval_authority.json']),
        'visual_reviewers_as_confirmed_by_user': ['Julia', 'ChatGPT'], 'Codex_independent_image_inspection': False,
        'definition_version': DEFINITION_VERSION, 'canonical_products': 50, 'front_assessments': 100,
        'resolved_exception_rows': 12, 'pending_approval_holds': 0, 'approved_ambiguous_front_electrolyte_cases': ['197644314881'],
        'initial_human_label_changes': 9, 'changed_products': sorted({r['canonical_source_barcode'] for r in changes}),
        'reviewed_workbook_SHA256': inputs[rel(REVIEW)], 'reviewed_workbook_copy': rel(OUT / 'exceptions_for_approval_reviewed.xlsx'),
        'Simple_Truth_user_instruction_overrides_conflicting_workbook_NO': True,
        'provenance_limitations': 'Accepted documented limitations; do not reopen approved definitions',
        'not_authorized': ['Paid LLM/OCR calls', 'Historical bulk backfill', 'Core extraction prompt/schema/taxonomy changes', 'Legacy flag or fortification reclassification', 'RUN 06 allocation changes', 'Production detector deployment or independent-validation claims'],
        'approved_artifact_sha256': {rel(p): digest(data) for p, data in payloads.items()},
    }
    payloads[OUT / 'CHECK_BEVERAGE_03_approval.json'] = jb(approval)
    manifest = {
        'package': 'BEVERAGE_03_APPROVED_V1', 'status': 'Approved; closed; immutable review package',
        'decision_date': DECISION_DATE, 'decision_timezone': DECISION_TIMEZONE,
        'script': rel(Path(__file__)), 'script_sha256': b01.sha(Path(__file__)),
        'protected_input_sha256': inputs,
        'counts': {'frozen_unique_products': 50, 'front_labels': 100, 'resolved_exceptions': 12, 'label_changes': 9, 'wording_evidence_rows': len(evidence)},
        'label_counts': summary,
        'invariants': {'legacy_flag_sets_preserved': 50, 'legacy_flags_per_set': 34, 'source_database_writes': 0, 'original_audit_files_modified': 0,
                       'paid_calls': 0, 'bulk_backfill': False, 'core_prompt_changes': False, 'RUN06_changes': False,
                       'independent_Codex_image_inspection': False, 'reviewed_numeric_Excel_barcode_used_as_identity': False},
        'output_sha256': {rel(p): digest(data) for p, data in payloads.items()},
    }
    payloads[OUT / 'beverage_03_closure_manifest.json'] = jb(manifest)
    for name, expected in inputs.items():
        assert b01.sha(source_path(name)) == expected, 'Input changed during closure: ' + name
    if verify_only:
        for p, data in payloads.items():
            assert p.read_bytes() == data, 'Frozen output mismatch: ' + rel(p)
        print(compact({'frozen_files_reproduced': len(payloads), 'protected_inputs_unchanged': len(inputs), 'approval_holds': 0, 'paid_calls': 0}))
    else:
        assert not OUT.exists() and not REPORT.exists(), 'Closure already frozen; use --verify-only'
        OUT.mkdir()
        for p, data in payloads.items():
            p.write_bytes(data)
        print(json.dumps({'closure_report': rel(REPORT), 'label_counts': summary, 'products': 50, 'exceptions_closed': 12,
                          'label_changes': 9, 'approved_artifact_files': len(payloads), 'unchanged_protected_inputs': len(inputs)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    build(parser.parse_args().verify_only)
