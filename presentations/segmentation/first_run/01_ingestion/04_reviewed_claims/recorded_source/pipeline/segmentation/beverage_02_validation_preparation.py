"""BEVERAGE 02 offline experiment preparation on the frozen 33 audit cases.

No OCR, LLM, image requests, bulk backfill, database writes or production
prompt/taxonomy changes. Proposed gold is authored separately from detectors;
all comparisons are provisional until human adjudication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B01 = ROOT / "presentations/segmentation/beverage_01_v1"
OUT = ROOT / "presentations/segmentation/beverage_02_v1"
REPORT = ROOT / "presentations/segmentation/BEVERAGE 02 - Benefit definitions and validation.md"
GOLD = OUT / "gold_label_proposals_v0.1.0.json"
DB = ROOT / "database/positioning_radar.db"
VERSION = "0.1.0-draft"
BENEFITS = ["hydration", "electrolyte"]
STATUSES = ["detected", "not_detected", "ambiguous", "unassessable"]
DATE = "2026-10-23"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def csv_bytes(records):
    b = io.StringIO(newline="")
    writer = csv.DictWriter(b, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return b.getvalue().encode("utf-8-sig")


def spans(text, quote, role="supporting_proposition"):
    if not quote:
        return []
    start = text.find(quote)
    assert start >= 0, f"Proposed evidence is not an exact OCR substring: {quote}"
    return [{"phrase": quote, "start_0based": start, "end_exclusive": start + len(quote), "role": role}]


def table(records, fields):
    def v(value):
        return "n/a" if value is None else str(value).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(t for _, t in fields) + " |", "|" + "---|" * len(fields),
                      *["| " + " | ".join(v(r[k]) for k, _ in fields) + " |" for r in records]])


def definition_registry():
    return {
        "registry_version": VERSION, "status": "Proposed definitions pending Julia's review; Option B architecture approved only",
        "definition_scope": "Consumer-facing positioning expressed in preserved OCR, not product efficacy, composition truth or legal compliance",
        "supported_assessment_languages": ["en", "fr"],
        "independence": "Assess each proposition independently. Electrolytes never imply hydration. One product may express both.",
        "example_warning": "Definition examples below are illustrative English/French strings, NOT additional observed test cases or gold evidence.",
        "definitions": [
            {"benefit_id": "hydration", "definition_version": VERSION,
             "name": "Hydration / rehydration benefit proposition",
             "positive_rule": "Explicit consumer-facing assertion that the product hydrates/rehydrates, helps maintain hydration, or is described as hydrating. An explicit marketing phrase/product descriptor qualifies; efficacy is not verified.",
             "negative_rule": "No such proposition in assessable OCR. Water, coconut water, sports drink, minerals, electrolyte presence, nutrition values and ordinary preparation/reconstitution instructions alone do not qualify. Explicit negation is not affirmative support.",
             "ambiguous_rule": "Standalone HYDRATE/HYDRATION identity, unclear brand/range versus benefit, mixed ingredient/marketing attribution, or unreadable negation that could change meaning.",
             "unassessable_rule": "Relevant wording cannot be assessed: missing/unreadable evidence, unsupported dominant language, or only instructions/legal/nutrition material without assessable marketing. This is task-specific and never rewrites historical context/status.",
             "positive_examples_en": ["helps you stay hydrated", "hydrating bubbly water", "fast rehydration", "hydration by nature"],
             "positive_examples_fr": ["aide à maintenir l'hydratation", "boisson hydratante", "favorise la réhydratation"],
             "negative_examples_en": ["coconut water", "with electrolytes", "add 200 ml water", "does not provide a hydration benefit"],
             "negative_examples_fr": ["eau de coco", "avec électrolytes", "ajouter 200 ml d'eau", "sans effet revendiqué sur l'hydratation"],
             "ambiguous_examples_en": ["BRAND HYDRATION", "HYDRATE"],
             "ambiguous_examples_fr": ["HYDRATATION used as a range name", "HYDRATEZ-VOUS without a clear product link"]},
            {"benefit_id": "electrolyte", "definition_version": VERSION,
             "name": "Electrolyte proposition / explicitly highlighted product feature",
             "positive_rule": "Consumer-facing marketing highlights electrolytes as a product feature: with/added/natural electrolytes, electrolyte drink, or a standalone electrolyte feature banner. Broader than a physiological benefit claim.",
             "negative_rule": "Ingredient-list-only or nutrition-table-only entries, named minerals without explicit electrolyte wording, ordinary water/sports-drink category, or an unambiguous no/without-electrolytes statement without an affirmative proposition.",
             "ambiguous_rule": "Unclear brand/company name, uncertain product link, conflicting/ambiguous negation such as ZERO adjacent to ELECTROLYTE SPORTS DRINK, or inseparable ingredient versus marketing context.",
             "unassessable_rule": "Same evidence/assessability contract as hydration; lack of an assessment is not a negative.",
             "taste_policy_proposed": "Explicit FRONT marketing 'with electrolytes added for taste' counts as electrolyte detected with asserted_purpose=taste; hydration remains independently assessed and is not inferred. Ordinary taste/flavour wording without electrolyte assertion does not qualify. This policy requires definition review.",
             "positive_examples_en": ["with electrolytes", "electrolyte sports drink", "with electrolytes added for taste"],
             "positive_examples_fr": ["avec électrolytes", "boisson aux électrolytes", "électrolytes ajoutés pour le goût"],
             "negative_examples_en": ["Ingredients: potassium chloride, magnesium", "Sodium 10 mg (nutrition table)", "sports drink", "no added electrolytes"],
             "negative_examples_fr": ["Ingrédients : chlorure de potassium, magnésium", "Sodium 10 mg (tableau nutritionnel)", "boisson pour sportifs", "sans électrolytes ajoutés"],
             "ambiguous_examples_en": ["ZERO / ELECTROLYTE / SPORTS DRINK", "Electrolyte Co."],
             "ambiguous_examples_fr": ["ZÉRO / ÉLECTROLYTES with unclear scope", "Les Électrolytes used only as a brand name"]},
        ],
        "status_semantics": {
            "detected": "Affirmative proposition supported by exact OCR phrase(s) under this definition.",
            "not_detected": "Assessment completed on suitable observed OCR; no qualifying affirmative proposition. Not proof of whole-pack absence.",
            "ambiguous": "Relevant evidence exists but its meaning/scope/attribution cannot be resolved confidently.",
            "unassessable": "Evidence or assessment coverage is insufficient for a decision.",
            "no_observation": "No assessment exists; do not create a not_detected record or coerce NULL to false."},
        "legacy_boundary": "Independent IDs only; never add these concepts to the existing 34 flags or priority taxonomy without a separate decision.",
    }


def observation_contract():
    return {
        "contract_id": "independent_emerging_benefit_observation", "contract_version": VERSION,
        "status": "Proposed specification only; no database schema, API or production storage implemented",
        "unit": "One product-region assignment x immutable OCR evidence x benefit definition version x method/configuration version x assessment run",
        "fields": {
            "observation_id": "Required SHA256 of canonical product/region, OCR hash, benefit id/version, method/config hash and run id; append-only identity",
            "run_id": "Required immutable assessment run identifier",
            "contract_version": "Required version of this observation contract",
            "product": {"barcode": "Required string, preserving leading zeros", "region": "Required FR / UK+IE / US+CA for current scope",
                        "category": "Required current audit category", "country_assignments": "Required original country array, not expanded paid units"},
            "source_ocr": {"text_sha256": "Required exact UTF-8 full text hash", "source_file": "Required local file/database reference",
                           "source_sha256": "Required frozen artifact hash", "source_row": "Required logical record/query locator",
                           "capture_timestamp": "Original value or null; do not invent timezone", "original_image_references": "Known references or empty array; origin trust recorded",
                           "image_pixel_hash": "Actual historical image bytes hash or null", "image_provenance_state": "Required known/unknown description"},
            "base_extraction_reference": "Required source observation id plus frozen legacy-result hash; legacy flags are referenced, never rewritten",
            "benefit_definition": {"id": "Required registry id; extensible, not a fixed 34-flag enum", "version": "Required", "sha256": "Required definition-content hash"},
            "detection_method": {"name": "Required deterministic/manual/LLM method", "version": "Required", "configuration_sha256": "Required",
                                 "model_deployment_version": "Required for LLM, otherwise null", "prompt_sha256": "Required for LLM, otherwise null"},
            "assessment_status": STATUSES,
            "status_reason": "Required concise reason tied to definition and observed evidence",
            "asserted_purpose": "hydration / composition_feature / taste / unspecified / null; describes wording, not efficacy",
            "evidence": "Array of exact phrase, start_0based, end_exclusive, role=supporting_proposition/ambiguous_mention/non_claim_context/negated_mention. Preserve raw spelling/newlines.",
            "review": {"status": "proposed_gold_pending_human / unreviewed_method_output / human_adjudicated / rejected / superseded",
                       "reviewer": "Required when adjudicated, otherwise null", "reviewed_at": "Actual timestamp or null",
                       "adjudicated_label": "One of four statuses only when adjudicated; otherwise null"},
            "assessed_at": "Actual assessment time; never a fabricated OCR capture time",
            "supersedes_observation_id": "Earlier independent observation id or null; no overwrite"},
        "invariants": ["detected requires >=1 exact supporting_proposition span",
                       "No existing assessment -> no observation; unassessable/ambiguous must not become false",
                       "not_detected is limited to assessed OCR, not a whole-pack absence guarantee",
                       "Unknown historical image/engine/prompt-content provenance stays null/unknown",
                       "Same evidence can have both propositions detected; neither label is derived from the other",
                       "Each new definition/method version appends observations; raw OCR and legacy claims remain unchanged",
                       "Independent observations do not change priority claim_category_1/2",
                       "A future keratin definition uses the same contract after its own wording, ingredient/marketing rules and validation are reviewed"],
    }


H_PATTERN = re.compile(r"\b(?:re)?hydrat(?:ion|ation|e|es|ed|ing|ant|ante|ants|antes)\b|\br[ée]hydratation\b", re.I)
E_PATTERN = re.compile(r"\b[ée]lectrolytes?\b|\b[ée]lectrolytiques?\b", re.I)
MINERAL_PROXY = re.compile(r"\b(?:sodium citrate|potassium chloride|potassium citrate|magnesium|magn[ée]sium|citrate de (?:sodium|potassium)|chlorure de potassium)\b", re.I)


def assessability(text):
    arabic = sum("\u0600" <= c <= "\u06ff" and c.isalpha() for c in text)
    letters = sum(c.isalpha() for c in text)
    if len(text.strip()) < 10 or letters < 3:
        return "Insufficient readable text"
    if arabic >= 10 and arabic / max(letters, 1) > .35:
        return "Dominant Arabic script outside first English/French method coverage"
    instruction_groups = [r"pr[ée]paration|bereiding|preparaci[oó]n", r"conservation|bewaring|conservez", r"ingr[ée]dients?|lagr[ée]dients"]
    if len(text) > 600 and sum(bool(re.search(p, text, re.I)) for p in instruction_groups) >= 2 and not (H_PATTERN.search(text) or E_PATTERN.search(text)):
        return "Instructions/ingredients/storage dominate; front marketing not assessable for this task"
    return None


def detect(text, benefit, method):
    matches = list((H_PATTERN if benefit == "hydration" else E_PATTERN).finditer(text))
    if method == "lexical_screen_v0":
        if benefit == "electrolyte":
            matches += list(MINERAL_PROXY.finditer(text))
        if matches:
            m = sorted(matches, key=lambda x: x.start())[0]
            return "detected", "Broad lexical screen only; no context or assessability handling", spans(text, m.group()), "unspecified"
        return "not_detected", "No lexical search token", [], None
    gate = assessability(text)
    if gate:
        return "unassessable", gate, [], None
    if not matches:
        return "not_detected", "No explicit proposition wording; no inference from category, named minerals or the other benefit", [], None
    m = matches[0]
    prefix = text[max(0, m.start() - 150):m.start()]
    local = text[max(0, m.start() - 100):min(len(text), m.end() + 130)]
    if benefit == "electrolyte":
        if re.search(r"\b(?:zero|0|z[ée]ro)\s+[ée]lectrolytes?\b", text, re.I) and re.search(r"sports?\s+drink|boisson", text, re.I):
            return "ambiguous", "ZERO may be naming or negation; OCR hierarchy does not resolve scope", spans(text, text[max(0, m.start() - 5):m.end() + 13], "ambiguous_mention"), None
        if re.search(r"\b(?:no|without|sans)\s+(?:added\s+|ajout[ée]s?\s+)?[ée]lectrolytes?\b", local, re.I):
            return "not_detected", "Explicit negated electrolyte proposition", spans(text, m.group(), "negated_mention"), None
        section = re.search(r"\b(?:ingredients?|ingr[ée]dients?|nutrition(?: facts)?|valeurs? nutritionnelles?)\s*[:\n]", prefix, re.I)
        if section:
            return "ambiguous" if re.search(r"with|avec|plus|added|ajout", local, re.I) else "not_detected", "Ingredient/nutrition context; marketing attribution needs separation", spans(text, m.group(), "non_claim_context"), None
        purpose = "taste" if re.search(r"for\s+taste|pour le go[uû]t", text, re.I) else "composition_feature"
        return "detected", "Explicit electrolyte feature; taste is a purpose, not hydration evidence", spans(text, m.group()), purpose
    if re.search(r"does not|no hydration benefit|sans effet|ne.*pas", local, re.I):
        return "not_detected", "Negated hydration proposition", spans(text, m.group(), "negated_mention"), None
    if re.search(r"\bhydrat(?:ing|ant|ante|ants|antes)\b", local, re.I) or re.search(r"by nature|helps?|supports?|maintain|fast|rapid|favorise|aide|maintenir|boisson|drink", local, re.I):
        return "detected", "Explicit hydrating characterization or contextual hydration assertion", spans(text, m.group()), "hydration"
    return "ambiguous", "Standalone hydration identity: brand/range versus benefit is unresolved", spans(text, m.group(), "ambiguous_mention"), None


def metrics(records):
    result = []
    for method in ["lexical_screen_v0", "context_rules_v0.1.0-draft"]:
        for benefit in BENEFITS:
            subset = [r for r in records if r["method_version"] == method and r["benefit_id"] == benefit]
            definite = [r for r in subset if r["proposed_gold_status"] in {"detected", "not_detected"}]
            tp = sum(r["proposed_gold_status"] == "detected" and r["method_status"] == "detected" for r in definite)
            fp = sum(r["proposed_gold_status"] == "not_detected" and r["method_status"] == "detected" for r in definite)
            p = sum(r["proposed_gold_status"] == "detected" for r in definite)
            result.append({"method_version": method, "benefit_id": benefit, "cases": len(subset),
                           "proposed_definite_positive": p, "proposed_definite_negative": len(definite) - p,
                           "true_positive_vs_proposal": tp, "false_positive_vs_proposal": fp,
                           "false_negative_including_abstention_vs_proposal": p - tp,
                           "abstentions_on_proposed_definite": sum(r["method_status"] in {"ambiguous", "unassessable"} for r in definite),
                           "provisional_precision_on_definite": round(tp / (tp + fp), 6) if tp + fp else None,
                           "provisional_recall_on_definite": round(tp / p, 6) if p else None,
                           "four_state_matches_vs_proposal": sum(r["proposed_gold_status"] == r["method_status"] for r in subset),
                           "forced_binary_on_proposed_indeterminate": sum(r["proposed_gold_status"] in {"ambiguous", "unassessable"} and r["method_status"] in {"detected", "not_detected"} for r in subset),
                           "human_adjudicated_assessments": 0, "adjudicated_precision": None, "adjudicated_recall": None,
                           "evaluation_status": "Provisional same-set comparison to Codex proposals; not validated human-gold accuracy"})
    return result


def acceptance_criteria():
    values = [
        ("GOLD", "Human adjudication", "Review all 66 proposition proposals. Record reviewer, label and rationale; resolve definition-policy questions before scoring.", "No result may be called human-gold precision/recall while adjudicated labels are absent."),
        ("EVIDENCE", "Exact evidence", "Each detected result quotes an exact full-OCR substring with correct offsets and source hash.", "100% span/hash validity; no corrected OCR invented as evidence."),
        ("P", "Precision", "TP/(TP+FP) on adjudicated definite positives/negatives; predicted positives on ambiguous/unassessable gold are reported separately.", "Zero false positives on adjudicated negative challenge cases before promotion; report the small denominator, not population accuracy."),
        ("R", "Recall", "TP/all adjudicated definite positives. Abstention on a definite positive is a miss; do not omit it to inflate recall.", "Recover every adjudicated explicit positive in this small challenge set; unclear gold cases are not silently positive or negative."),
        ("ABSTAIN", "Ambiguous/unassessable safety", "Report all four-state confusion counts and binary decisions on indeterminate cases.", "No automatic confident promotion of unresolved brand/negation/language/context cases."),
        ("INDEPENDENT", "Independent propositions", "Assess hydration and electrolyte separately, including taste-only electrolyte and hydration-without-electrolytes controls.", "No hydration inference solely from electrolyte or mineral/category presence. A new dual-positive holdout remains a coverage gap."),
        ("LEGACY", "Legacy preservation", "Verify exact old 34-flag JSON, codes, no-claim state and source artifacts before/after preparation or later layer run.", "Zero legacy mutations; this audit performs no main-extractor rerun or new legacy accuracy claim."),
        ("GENERALIZE", "Holdout gaps", "After definition review, separately approve real French positives, ingredient-only and nutrition-only electrolyte cases, negated propositions, dual positive, long-tail positive and unsupported/non-front controls.", "No production-generalization claim from 33 in-sample cases; no synthetic examples counted as observed gold."),
        ("LLM", "Bounded optional comparison", "Eight fixed saved-OCR requests maximum, one response containing both propositions; no automatic retry expansion, OCR or new images.", "Separate approval of definitions/gold/input manifest/model/config/request cap/spending guard before any call."),
        ("VERSION", "Reuse for future benefits", "Freeze definition/examples, gold revision, OCR hashes, detector config and contract; append versioned observations.", "New benefits such as keratin require their own definition and tests; no reuse of missing assessment as false or automatic taxonomy insertion."),
    ]
    return [{"criterion_id": k, "criterion": name, "measurement": measure, "proposed_acceptance": criterion,
             "status": "Proposed; pending definition and human-label review"} for k, name, measure, criterion in values]


def build(verify_only=False, replace_draft=False):
    b01_manifest = B01 / "beverage_01_manifest.json"
    b01 = json.loads(b01_manifest.read_text(encoding="utf-8"))
    inputs = dict(b01["input_hashes_sha256"])
    inputs.update(b01["output_sha256"])
    inputs[rel(b01_manifest)] = sha(b01_manifest)
    inputs[b01["audit_script"]] = b01["audit_script_sha256"]
    inputs[rel(GOLD)] = sha(GOLD)
    for name, value in inputs.items():
        assert sha(ROOT / name) == value, f"Frozen input changed: {name}"
    cases = read_csv(B01 / "proposed_fixed_test_set.csv")
    proposals = json.loads(GOLD.read_text(encoding="utf-8"))["case_proposals"]
    assert len(cases) == len(proposals) == 33
    assert [r["case_id"] for r in cases] == [r["case_id"] for r in proposals]
    countries = {}
    wanted = {(r["barcode"], r["region"]) for r in cases}
    country_regions = {"FR": "FR", "UK": "UK+IE", "IE": "UK+IE", "US": "US+CA", "CA": "US+CA"}
    ledger = ROOT / "presentations/segmentation/run_01/eligibility_ledger.csv"
    with ledger.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            region = country_regions.get(row["country"])
            key = row["barcode"], region
            if row["category"] == "beverages" and key in wanted:
                countries.setdefault(key, set()).add(row["country"])
    assert len(countries) == 33
    wal = Path(str(DB) + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0
    con = sqlite3.connect(DB.as_uri() + "?mode=ro&immutable=1", uri=True)
    con.execute("PRAGMA query_only=ON")
    con.row_factory = sqlite3.Row
    gold_review, results, legacy, texts = [], [], [], {}
    registry = definition_registry()
    for case, proposal in zip(cases, proposals):
        assert case["source"] == "database/positioning_radar.db::product_analysis"
        row = dict(con.execute("SELECT * FROM product_analysis WHERE barcode=?", (case["barcode"],)).fetchone())
        text = row["ocr_text"]
        assert hash_text(text) == case["ocr_sha256"] and len(text) == int(case["ocr_length"])
        # BEVERAGE 01 records the sorted union of true raw flags and stored
        # codes. Compare that same interpretation; retain the frozen raw JSON
        # and source artifact hash separately without rewriting either.
        saved_flags = json.loads(row["claims_json"])
        old_flags = json.loads(case["old_raw_flags_json"])
        assert all(saved_flags.get(k) == v for k, v in old_flags.items())
        normalized_codes = {k for k, v in old_flags.items() if v is True}
        normalized_codes |= set((row["pack_claims_found"] or "").split("|")) & set(old_flags)
        assert "|".join(sorted(normalized_codes)) == case["old_claim_codes"]
        assert row["image_context"] == case["old_context"]
        assert row["llm_status"] == "success" and row["claim_extraction_status"] == "completed"
        assert len(old_flags) == 34
        texts[case["case_id"]] = text
        review_evidence = spans(text, proposal["review_quote"], "review_context_not_positive_proof")
        prop_evidence = {}
        for benefit in BENEFITS:
            state = proposal[benefit]
            assert state in STATUSES
            quote = proposal.get(benefit + "_quote", "")
            prop_evidence[benefit] = spans(text, quote, "supporting_proposition" if state == "detected" else "ambiguous_mention")
            if state == "detected":
                assert prop_evidence[benefit]
            for method in ["lexical_screen_v0", "context_rules_v0.1.0-draft"]:
                status, reason, support, purpose = detect(text, benefit, method)
                assert status in STATUSES
                for s in support:
                    assert text[s["start_0based"]:s["end_exclusive"]] == s["phrase"]
                results.append({"case_id": case["case_id"], "barcode": case["barcode"], "region": case["region"],
                                "benefit_id": benefit, "definition_version": VERSION, "method_version": method,
                                "method_status": status, "reason": reason, "asserted_purpose": purpose,
                                "exact_evidence_json": json.dumps(support, ensure_ascii=False),
                                "proposed_gold_status": state, "matches_proposal_not_human_gold": status == state,
                                "human_gold_status": None, "full_OCR_sha256": case["ocr_sha256"],
                                "evaluation_status": "Provisional only; human adjudication pending"})
        gold_review.append({"case_id": case["case_id"], "barcode": case["barcode"], "region": case["region"],
                            "country_assignments": "|".join(sorted(countries[(case["barcode"], case["region"])])),
                            "product_name_reference_only": case["product_name"], "frozen_test_role": case["role"],
                            "proposed_hydration": proposal["hydration"], "proposed_electrolyte": proposal["electrolyte"],
                            "hydration_exact_evidence_json": json.dumps(prop_evidence["hydration"], ensure_ascii=False),
                            "electrolyte_exact_evidence_json": json.dumps(prop_evidence["electrolyte"], ensure_ascii=False),
                            "electrolyte_asserted_purpose": proposal.get("electrolyte_purpose"),
                            "review_excerpt_json": json.dumps(review_evidence, ensure_ascii=False),
                            "proposal_reason": proposal["reason"], "proposed_by": "Codex textual review; not human adjudication",
                            "human_hydration_label": None, "human_electrolyte_label": None, "human_reviewer": None,
                            "review_status": "proposed_gold_pending_human", "definition_version": VERSION,
                            "source": case["source"], "source_row": case["source_row"], "source_sha256": case["source_sha256"],
                            "source_ocr_sha256": case["ocr_sha256"], "source_ocr_length": len(text),
                            "base_observation_id": case["observation_id"], "old_claim_state": case["old_claim_state"],
                            "old_claim_codes": case["old_claim_codes"], "old_raw_flags_json": case["old_raw_flags_json"],
                            "old_prompt_version": case["old_prompt_version"], "old_context": case["old_context"],
                            "original_image_references": case["same_text_original_request_URLs"],
                            "image_provenance_state": case["image_provenance_state"]})
        reference = {key: case[key] for key in ["old_raw_flags_json", "old_claim_state", "old_claim_codes", "old_prompt_version", "old_context", "observation_id", "ocr_sha256"]}
        reference_hash = hash_text(json.dumps(reference, sort_keys=True, separators=(",", ":")))
        legacy.append({"case_id": case["case_id"], "barcode": case["barcode"], "base_reference_sha256": reference_hash,
                       "copied_legacy_flags_sha256": hash_text(gold_review[-1]["old_raw_flags_json"]),
                       "original_legacy_flags_sha256": hash_text(case["old_raw_flags_json"]),
                       "raw_flags_count": 34, "unchanged": True,
                       "valid_no_claim_retained": case["old_claim_state"] == "no_claims",
                       "scope": "Reference integrity only; no main-extractor rerun or regression-accuracy claim"})
    con.close()
    assert len(results) == 132
    assert all(r["old_raw_flags_json"] == c["old_raw_flags_json"] for r, c in zip(gold_review, cases))
    stats = metrics(results)
    llm_ids = ["B01_006", "B01_007", "B01_012", "B01_018", "B01_019", "B01_028", "B01_030", "B01_031"]
    llm_reasons = {
        "B01_006": "Unresolved brand/range versus hydration assertion; LLM may explain but cannot choose business policy",
        "B01_007": "Clear hydration-positive anchor without electrolyte wording",
        "B01_012": "Long instructions-only context; compare task-specific unassessable behaviour without changing old mixed-pack status",
        "B01_018": "Clear electrolyte-feature anchor, with old fibre claim preserved and no hydration inference",
        "B01_019": "ZERO/ELECTROLYTE scope ambiguity; spatial hierarchy absent, abstention may remain correct",
        "B01_028": "Electrolyte positive plus standalone HYDRATE identity; prevent cross-proposition inference",
        "B01_030": "Taste-purpose electrolyte feature; do not turn it into a physiological hydration claim",
        "B01_031": "Clean electrolyte heading plus garbled taste phrase; use exact OCR, no spelling repair as evidence",
    }
    llm_rows = []
    for case in cases:
        if case["case_id"] in llm_ids:
            llm_rows.append({"case_id": case["case_id"], "barcode": case["barcode"], "region": case["region"],
                             "source": case["source"], "source_sha256": case["source_sha256"], "source_ocr_sha256": case["ocr_sha256"],
                             "full_ocr_characters": case["ocr_length"], "comparison_reason": llm_reasons[case["case_id"]],
                             "max_LLM_requests_including_retries": 1, "OCR_requests": 0,
                             "gold_labels_transmitted_to_model": False, "legacy_flags_transmitted_to_model": False,
                             "status": "Optional proposed comparison; not authorized to execute"})
    return render(cases, gold_review, results, stats, legacy, llm_rows, registry, inputs, texts, verify_only, replace_draft)


def render(cases, gold_review, results, stats, legacy, llm_rows, registry, inputs, texts, verify_only, replace_draft):
    state_summary = []
    for benefit in BENEFITS:
        counts = Counter(r["proposed_" + benefit] for r in gold_review)
        state_summary.append({"benefit": benefit, **{s: counts[s] for s in STATUSES}})
    status_labels = {r["case_id"]: (r["proposed_hydration"], r["proposed_electrolyte"]) for r in gold_review}
    selected_edges = [r for r in gold_review if r["case_id"] in {"B01_004", "B01_006", "B01_007", "B01_008", "B01_009", "B01_012", "B01_018", "B01_019", "B01_020", "B01_028", "B01_029", "B01_030", "B01_031"}]
    for r in selected_edges:
        r["short_review_wording"] = json.loads(r["review_excerpt_json"])[0]["phrase"]
    # Do not mutate the frozen 33-case input: the extra field is a review-table
    # convenience on a newly derived row and is normalized across all rows.
    for r in gold_review:
        r.setdefault("short_review_wording", json.loads(r["review_excerpt_json"])[0]["phrase"])
    definitions_path = OUT / "benefit_definition_registry_v0.1.0.json"
    definitions_data = json_bytes(registry)
    llm_data = csv_bytes(llm_rows)
    llm_plan = {
        "experiment_id": "BEVERAGE02_OPTION_B_LLM_COMPARISON_V0.1.0_DRAFT", "status": "Proposed only; no paid calls authorized",
        "architecture": "Independent emerging-benefit observations; never rerun or overwrite old 34-flag extraction",
        "case_manifest": rel(OUT / "llm_only_comparison_cases.csv"), "case_manifest_sha256": hash_text(llm_data.decode("utf-8")),
        "case_ids": [r["case_id"] for r in llm_rows], "max_billable_LLM_requests_including_retries": 8,
        "max_requests_per_case_including_retries": 1, "propositions_per_response": 2,
        "expected_assessments_if_all_responses_valid": 16, "OCR_requests": 0, "image_requests": 0,
        "automatic_retries_or_repeats": False, "bulk_backfill": False,
        "input": {"full_original_OCR": "Required, fetched by exact frozen source/hash; not truncated to 2000",
                  "case_id": "Required opaque identifier", "definitions": "Both exact approved definitions and output status/evidence contract",
                  "language_coverage": ["English", "French"],
                  "excluded": ["proposed gold labels", "human labels", "old 34 flags", "old priority taxonomy", "product-name inference", "images"]},
        "output": {"hydration": "One four-state assessment plus exact OCR spans/reason", "electrolyte": "Independent four-state assessment, exact OCR spans/reason and stated purpose where available",
                   "missing_or_invalid": "Record unresolved execution/validation failure separately; never not_detected"},
        "model": "Use the project's existing text extraction deployment, with exact deployment/model version frozen and approved before execution; no model change made here",
        "prompt_status": "Instruction requirements only; no existing prompt edited and no live prompt installed",
        "request_controls": "One response assesses both propositions; exact input hash, config/prompt/model versions, request log and billable-call guard required",
        "before_execution": ["Approve definitions, especially claim-bearing identity and taste policy", "Human-adjudicate the comparison cases or explicitly retain ambiguous/unassessable gold",
                             "Freeze adjudicated-gold revision/hash", "Approve exact request/input manifest, model/configuration, request cap and spending guard"],
        "not_resolvable_by_LLM_alone": ["Business definition choice about brand/range naming", "Missing spatial hierarchy/pixels", "Unapproved language coverage", "Missing historical evidence"],
        "after_execution": "Compare to adjudicated labels and evidence; no automatic promotion or bulk backfill",
        "current_paid_cost": 0, "future_price_or_spend_authorization": None,
    }
    architecture_approval = {
        "decision_date": DATE, "approved_by": "Julia", "decision": "BEVERAGE 01 Option B architecture approved",
        "scope": "Independent, versioned emerging-benefit layer using preserved OCR and leaving old classifications unchanged",
        "source_report": "presentations/segmentation/BEVERAGE 01 - OCR and benefits audit.md",
        "source_report_sha256": inputs["presentations/segmentation/BEVERAGE 01 - OCR and benefits audit.md"],
        "source_manifest": rel(B01 / "beverage_01_manifest.json"), "source_manifest_sha256": inputs[rel(B01 / "beverage_01_manifest.json")],
        "frozen_test_set": rel(B01 / "proposed_fixed_test_set.csv"), "frozen_test_set_sha256": inputs[rel(B01 / "proposed_fixed_test_set.csv")],
        "specific_definitions_approved": False, "proposed_gold_labels_human_adjudicated": False,
        "paid_calls_approved": False, "historical_bulk_backfill_approved": False,
        "legacy_flag_or_priority_changes_approved": False,
    }
    definite_human_count = 0
    retained_no_claim = sum(r["old_claim_state"] == "no_claims" for r in gold_review)
    old_no_claim_new_positive = [r["case_id"] for r in gold_review if r["old_claim_state"] == "no_claims" and "detected" in status_labels[r["case_id"]]]
    languages = {"B01_004": "Arabic-dominant (unsupported in first EN/FR method)", "B01_012": "French/Dutch/Spanish instructions"}
    gaps = [
        "No clear observed French-language hydration/electrolyte positive in the fixed 33; French definition examples are illustrative only.",
        "No unequivocal ingredient-list-only electrolyte case: B01_008/009 and B01_020 are front mineral highlights, not ingredient lists.",
        "No explicit electrolyte nutrition-table-only positive-token control and no unequivocal no/without-electrolytes control.",
        "No unambiguous dual-positive product; both propositions must remain independently representable.",
        "Only one >2000-character case (B01_012), with no new-benefit wording after the cutoff; no long-tail positive recovery test.",
        "No historically non-front/uncertain case in the frozen successful test set; B01_012 is new-task unassessability with old mixed-pack status retained.",
        "One Arabic-dominant case needs a qualified language reviewer or a separately approved language extension; region is not language.",
        "No keratin evidence/case in this fixed set; reuse is a method proposal, not keratin validation.",
    ]
    report = f"""# BEVERAGE 02 — Benefit definitions and validation

**23 October 2026 — Preparation complete; STOP for review. No paid calls or historical backfill.**

## Decision and scope

Julia approved **Option B**, an independent versioned emerging-benefit layer using preserved OCR. This architecture approval is recorded [separately](beverage_02_v1/beverage_01_option_b_approval.json), referencing the unchanged BEVERAGE 01 report/manifest and frozen **33-product test set**. The definitions, proposed labels and experiment below remain pending review; Option B approval does not approve a paid trial, deployment or bulk backfill.

All 33 original case IDs, exact full OCR hashes, regional identifiers and old results were preserved. No replacement/additional products were selected. Full OCR was reviewed, including B01_012's 2,351 characters; the old 2,000-character LLM input limit was not applied to this preparation. No product-name, nutrition-value or ingredient-metadata inference supplies benefit evidence.

## 1. Proposed independent definitions — v{VERSION}

**Hydration / rehydration benefit:** explicit consumer-facing wording that the product hydrates/rehydrates, helps maintain hydration, or is characterized as hydrating. This detects positioning, not efficacy or legal validity. Ordinary water, coconut water, sports drink, preparation instructions or mineral/electrolyte presence do not establish it. Standalone HYDRATE/HYDRATION identities remain ambiguous until claim-bearing brand/range policy or text attribution is resolved.

**Electrolyte proposition:** consumer-facing emphasis on electrolytes as a product feature. This is deliberately broader than a physiological benefit: 'with electrolytes', an electrolyte feature banner or an electrolyte-drink descriptor can qualify. Named minerals alone, ingredient-list-only/nutrition-table-only mentions and plain product categories do not. Negated or scope-unclear text is not affirmative evidence.

**Definition choice requiring review:** front-pack 'with electrolytes added for taste' is proposed as **electrolyte detected, stated purpose=taste**; it is **not a hydration detection or a physiological-benefit inference**. A taste/flavour description without an electrolyte feature does not qualify. If the intended electrolyte concept is narrower than a highlighted product feature, revise this definition and re-adjudicate B01_030/031 before any trial.

| Proposition | Positive examples | Negative examples | Ambiguous examples |
|---|---|---|---|
| Hydration — EN | 'hydrating bubbly water'; 'helps you stay hydrated' | 'coconut water'; 'with electrolytes'; 'add 200 ml water' | standalone 'HYDRATE'; 'BRAND HYDRATION' |
| Hydration — FR | 'boisson hydratante'; 'aide à maintenir l’hydratation' | 'eau de coco'; 'avec électrolytes'; 'ajouter de l’eau' | HYDRATATION as a range name without a clear product-benefit link |
| Electrolyte — EN | 'with electrolytes'; 'electrolytes added for taste' (purpose=taste) | ingredient-only potassium chloride; nutrition-table sodium; 'no added electrolytes' | ZERO / ELECTROLYTE / SPORTS DRINK with unclear scope |
| Electrolyte — FR | 'avec électrolytes'; 'électrolytes ajoutés pour le goût' | 'Ingrédients : chlorure de potassium'; tableau nutritionnel; 'sans électrolytes ajoutés' | unclear ZÉRO / ÉLECTROLYTES scope or a brand/company name only |

Examples in this definition table are **illustrative definition examples, not invented observed cases or added gold data**. A product can be positive for both, e.g. an explicit hydration assertion plus an electrolyte feature; neither assessment is derived from the other. Complete rules/examples are versioned in the [definition registry](beverage_02_v1/benefit_definition_registry_v0.1.0.json).

Use four states: **detected** (exact affirmative evidence), **not_detected** (assessed OCR lacks a qualifying proposition), **ambiguous** (relevant wording but unresolved meaning), **unassessable** (insufficient evidence/language/context). Not detected is limited to observed OCR, not proof of absence from the full pack. **No assessment means no observation, never false.**

## 2. Proposed gold review — 33 cases / 66 assessments

The [gold-label review table](beverage_02_v1/proposed_gold_label_review.csv) contains case-specific reasoning, exact OCR excerpts/offsets, full-text hashes/provenance, country assignments and the original 34-flag JSON/no-claim state. Labels were proposed by Codex after reading the full OCR. **Human adjudication is pending for all 66 assessments**; reviewer/label cells are blank, and no result is presented as human gold.

{table(state_summary, [('benefit','Proposition'),('detected','Proposed detected'),('not_detected','Proposed not detected'),('ambiguous','Ambiguous'),('unassessable','Unassessable')])}

Principal boundaries and positive cases:

{table(selected_edges, [('case_id','Case'),('region','Region'),('short_review_wording','OCR wording (line breaks flattened)'),('proposed_hydration','Hydration'),('proposed_electrolyte','Electrolyte')])}

- B01_006 and B01_028 have standalone identity words; a model cannot choose the business policy for us.
- B01_019's ZERO may be naming or negation. OCR discarded visual hierarchy, so an LLM cannot recover missing pixels.
- B01_004 is Arabic-dominant, outside the first EN/FR method. B01_012 is mostly multilingual instructions/storage/ingredients. Their proposed unassessable outcomes belong to the **new task only**; old fortification/mixed-pack/no-claim outcomes are untouched.
- Mineral-highlight cases B01_008/009/020 are negative for the new propositions under this definition. A visible mineral highlight might raise an old fortification question; this preparation does not repair historical flags.

The 33 regression references include six sugar-preservation cases, six other-functional cases and three organic/multiple-claim cases, plus {retained_no_claim} valid old no-claim outcomes across roles. Existing zero/no-added-sugar phrases share the old `sugar_free_claim` flag, so retain phrases as well as flags. All 34 old flags and source hashes are unchanged. A new proposition on old no-claim cases {', '.join(old_no_claim_new_positive)} is a potential taxonomy extension, not a retroactive rewrite or proof the earlier outcome was wrong.

Human workflow: review the proposed statuses and exact excerpts, settle definition choices, then save a **separate adjudicated revision** with reviewer/date and source hashes. Do not overwrite BEVERAGE 01 or call a proposal human-adjudicated. Legacy flags are preserved references, not newly verified ground truth.

## 3. Independent observation contract

The [v{VERSION} observation specification](beverage_02_v1/emerging_benefit_observation_spec_v0.1.0.json) defines one append-only observation per product/region × immutable OCR × benefit-definition version × method/config version × run. It records:

- Barcode, region/category and original country assignments.
- Exact source OCR hash, file/database locator/hash, capture timestamp and known/unknown original image provenance. Unknown historical image/prompt/provider versions remain unknown.
- Base extraction reference/hash, benefit-definition ID/version/hash, detection method/version/config hash and model/prompt hashes when applicable.
- One four-state assessment, concise reason, stated purpose, exact OCR spans and review/adjudication status.
- Observation/run identifiers and a supersedes link for later revisions; no overwritten history.

Detected requires an exact supporting span. Review excerpts for negative/unassessable cases are not positive evidence. Source OCR and old results remain separate. **Neither new proposition enters the existing 34 flags, `pack_claims_found`, `claim_category_1/2` or their priority mapping.** No production schema/store/API has been installed; this is a versioned specification.

## 4. Offline deterministic assessment

Compared two explicitly versioned methods on the same full saved OCR: a broad **lexical screen v0** (including the BEVERAGE 01 mineral proxies), and **context rules v{VERSION}** with language/marketing assessability, independent proposition rules, taste-purpose handling and ambiguity/negation safeguards. Neither detector looks up case IDs or proposed labels. These are local experiment functions, not changes to the production extraction pipeline.

{table(stats, [('method_version','Method'),('benefit_id','Proposition'),('true_positive_vs_proposal','TP'),('false_positive_vs_proposal','FP'),('false_negative_including_abstention_vs_proposal','FN incl abstention'),('provisional_precision_on_definite','Provisional precision'),('provisional_recall_on_definite','Provisional recall'),('forced_binary_on_proposed_indeterminate','Forced binary on indeterminate')])}

All figures compare to **unadjudicated proposals on the same set used to prepare the rules**. They are diagnostic/resubstitution results, not independent accuracy validation. Human-gold precision/recall fields remain unavailable. The broad screen's mineral matches must not be promoted as electrolyte claims; binary outputs on ambiguous or unassessable proposals are reported separately rather than hidden in precision. A perfect same-set context-rule match would still not establish generalization.

[Per-assessment results](beverage_02_v1/deterministic_test_results.csv) retain all 132 outputs (33 × 2 propositions × 2 methods), reasons, exact evidence and proposed comparators. [Compact metrics](beverage_02_v1/deterministic_metrics.csv) expose denominators and abstentions. [Legacy integrity](beverage_02_v1/regression_reference_integrity.csv) records unchanged reference hashes; no main-prompt rerun/regression-accuracy experiment occurred.

After human adjudication: **precision = TP/(TP+FP)** on definite gold, **recall = TP/all definite positives**, counting abstention on a positive as a miss. Undefined ratios stay unavailable. Report false-positive cases individually, four-state confusion, abstention rate and any confident binary output on indeterminate gold. Before promotion require correct spans, zero unexplained legacy mutations, zero false positives on adjudicated negative challenges and recovery of every adjudicated explicit positive in this small set. Ambiguity may remain unresolved; do not force a binary label to improve metrics. These small denominators do not support market prevalence or population accuracy claims.

## 5. Optional bounded LLM-only comparison

**No case inherently requires a paid LLM.** Human review can adjudicate text. The useful question is whether an LLM applies the approved definitions and abstains consistently on semantic boundaries. It cannot decide definition policy, recover spatial hierarchy or fix an unsupported-language gap by assertion.

Propose **8 saved-OCR requests maximum**, one request per fixed case, each returning both proposition assessments: B01_006, 007, 012, 018, 019, 028, 030 and 031. B01_007 and 018 are clear positive anchors; the others test identity/negation, assessability, taste purpose or OCR corruption. B01_004 goes to a qualified language reviewer or a separately approved language extension, not automatic EN/FR interpretation.

Use full exact OCR plus the two approved definitions/status/span contract; **do not send gold labels or old flags to the model**. Preserve source hashes and original spelling; no new image/OCR and no product-name inference. One response assesses both propositions. The eight-request cap includes billable retries; failed requests consume their slot, with no automatic retries/repeats or corpus expansion. Missing/invalid responses are execution/validation failures, not negative assessments. Exact existing text deployment/model version, experimental instructions, input manifest, adjudicated-gold revision, request cap and spending guard need separate approval. No active prompt was created or changed and no future price guarantee is asserted.

The [eight-case manifest](beverage_02_v1/llm_only_comparison_cases.csv) and [bounded comparison plan](beverage_02_v1/llm_only_comparison_plan.json) are proposed only. Current paid cost/calls: **zero**. The core 12,000-attempt allocation and its CHF 24 estimate / CHF 30 planning budget are unchanged; no beverage backfill or paid pilot is authorized here.

## 6. Gaps and reuse for future benefits

{chr(10).join('- ' + gap for gap in gaps)}

For a future benefit such as keratin: define the proposition and ingredient/marketing/identity boundaries first; version the definition and language examples; inspect preserved OCR; propose/adjudicate real positives, negatives and ambiguous cases; freeze a holdout; compare a generic deterministic/optional semantic method; append new observations using the same contract. **Do not inherit electrolyte-specific rules or automatically add a new legacy flag.** New assessments can reuse the same immutable OCR indefinitely while their definition/method versions remain explicit.

## Review package and validation

- [33-case proposed gold-label review table](beverage_02_v1/proposed_gold_label_review.csv)
- [Authored gold proposals — separate from detector rules](beverage_02_v1/gold_label_proposals_v0.1.0.json)
- [Versioned English/French definitions](beverage_02_v1/benefit_definition_registry_v0.1.0.json)
- [Independent observation specification](beverage_02_v1/emerging_benefit_observation_spec_v0.1.0.json)
- [Deterministic assessment results](beverage_02_v1/deterministic_test_results.csv) and [metrics](beverage_02_v1/deterministic_metrics.csv)
- [Eight-case LLM-only manifest](beverage_02_v1/llm_only_comparison_cases.csv) and [plan](beverage_02_v1/llm_only_comparison_plan.json)
- [Legacy-reference integrity](beverage_02_v1/regression_reference_integrity.csv)
- [Acceptance criteria](beverage_02_v1/validation_acceptance_criteria.csv)
- [Option B architecture approval](beverage_02_v1/beverage_01_option_b_approval.json)
- [Source/configuration/output hashes and validation](beverage_02_v1/beverage_02_manifest.json)
- [Offline preparation script](../../pipeline/segmentation/beverage_02_validation_preparation.py)

Validated exact membership of all 33 frozen cases, full OCR/source hashes, excerpt offsets, country assignments, 34-flag reference preservation, state/count reconciliation and reproducibility. All protected prior files remain unchanged; no full corpus export, active prompt/schema change, database write, image request, paid call or historical backfill. **STOP for definition and proposed-gold review.**
"""
    payloads = {
        OUT / "proposed_gold_label_review.csv": csv_bytes(gold_review),
        OUT / "deterministic_test_results.csv": csv_bytes(results),
        OUT / "deterministic_metrics.csv": csv_bytes(stats),
        OUT / "regression_reference_integrity.csv": csv_bytes(legacy),
        OUT / "llm_only_comparison_cases.csv": llm_data,
        OUT / "validation_acceptance_criteria.csv": csv_bytes(acceptance_criteria()),
        definitions_path: definitions_data,
        OUT / "emerging_benefit_observation_spec_v0.1.0.json": json_bytes(observation_contract()),
        OUT / "llm_only_comparison_plan.json": json_bytes(llm_plan),
        OUT / "beverage_01_option_b_approval.json": json_bytes(architecture_approval),
        REPORT: report.encode("utf-8"),
    }
    manifest = {
        "experiment_preparation": "BEVERAGE_02_V0.1.0_DRAFT", "date": DATE, "status": "Prepared; definitions and gold proposals pending review",
        "architecture_approval": "Option B approved by Julia; no paid trial, backfill or legacy taxonomy changes approved",
        "script": rel(Path(__file__)), "script_sha256": sha(Path(__file__)), "input_sha256": inputs,
        "frozen_cases": 33, "gold_proposals": 66, "human_adjudicated_assessments": definite_human_count,
        "proposed_state_counts": state_summary, "deterministic_result_rows": len(results),
        "detectors": ["lexical_screen_v0", "context_rules_v0.1.0-draft"], "definition_version": VERSION,
        "definition_registry_sha256": hash_text(definitions_data.decode("utf-8")),
        "lexical_patterns": {"hydration": H_PATTERN.pattern, "electrolyte": E_PATTERN.pattern, "broad_screen_mineral_proxy": MINERAL_PROXY.pattern},
        "method_limitations": "English/French draft rules; threshold/context heuristics and proposals prepared from same cases; no independent holdout or human-gold accuracy claim",
        "case_language_exceptions": languages, "test_gaps": gaps,
        "optional_LLM_requests_cap_including_retries": 8, "paid_test_authorized": False,
        "output_sha256": {rel(p): hash_text(data.decode("utf-8")) for p, data in payloads.items()},
        "validation": {"exact_33_case_membership": True, "old_34_flags_per_case_preserved": True,
                       "valid_no_claim_references_retained": retained_no_claim, "source_hashes_unchanged": len(inputs),
                       "no_existing_prompt_schema_data_or_processing_changes": True,
                       "service_calls": 0, "database_writes": 0, "historical_bulk_backfill": False},
    }
    payloads[OUT / "beverage_02_manifest.json"] = json_bytes(manifest)
    assert all(sha(ROOT / name) == value for name, value in inputs.items())
    if verify_only:
        for p, data in payloads.items():
            assert p.read_bytes() == data, f"Reproducibility mismatch: {rel(p)}"
        print(json.dumps({"reproduced_files": len(payloads), "verified_unchanged_input_hashes": len(inputs), "service_calls": 0}, indent=2))
    else:
        if replace_draft:
            old = json.loads((OUT / "beverage_02_manifest.json").read_text(encoding="utf-8"))
            assert old["status"] == manifest["status"]
            for name, value in old["output_sha256"].items():
                assert sha(ROOT / name) == value, name
        else:
            assert not (OUT / "beverage_02_manifest.json").exists() and not REPORT.exists()
        for p, data in payloads.items():
            p.write_bytes(data)
        print(json.dumps({"report": rel(REPORT), "gold_counts": state_summary, "metrics": stats,
                          "outputs": len(payloads), "proposed_LLM_cases": len(llm_rows), "old_no_claim_retained": retained_no_claim}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--replace-own-draft", action="store_true")
    args = parser.parse_args()
    assert not (args.verify_only and args.replace_own_draft)
    build(args.verify_only, args.replace_own_draft)


if __name__ == "__main__":
    main()
