"""Build and validate the final Wave 2 OCR/LLM layer. Never writes source evidence."""
import csv
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pipeline.vision_ops.run_06b_runner import LegacyContract

ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
VERSION = "wave2_ocr_llm_lock_v1"
OUT = SEG / VERSION
SOURCE = SEG / "wave2_claims_reconciliation_v1/reconciled_review.csv"
APPROVAL = Path("C:/Users/julia/.codex/attachments/5072de8f-e50c-4009-82e9-afd70ad3f648/Pasted text.txt")
ENERGY_CHECK = SEG / "ENERGY_DRINK_COVERAGE_CHECK.md"
REVIEW = SEG / "wave2_claim_six_case_review_v1/REVIEW.md"
CONFIG = SEG / "run_06b_main_readiness_v1/runtime_configuration.json"
FLAGS = [f for f in LegacyContract(json.loads(CONFIG.read_text())).module.BOOL_CLAIM_FIELDS
         if f != "no_claims_detected"]
PREPARATIONS = {"4260715291179", "0889392080629", "889392080612", "0810030515098", "0696859110023"}
ENERGY_UNKNOWN = {"5070003278527", "5027492002423", "5060809670274", "5060895748796",
                  "810014530314", "0849429002420", "0850062286108", "0810175040547",
                  "850004884850", "0786162080004", "0028435600428"}
ENERGY_CONFLICT = {"3583788597605", "7649989242419", "0764460103854", "54492653",
    "49000554175", "0786162150004", "0810113833224", "0049000007909", "713789000757",
    "0098100101642", "0810113832012", "21136181609", "0887725000252", "810113830018",
    "0052000328660", "0810131955571", "36632024251", "0810113831367", "0028000310998",
    "0850069519940", "0887725000979", "887725000054", "0810125971143", "0017642781556", "0089094026479"}

# Evidence cues instantiate existing prompt examples; they never define negatives.
CUES = {
 "organic_claim": r"\b(?:bio|organic|biologique|biologisch|agriculture biologique)\b",
 "protein_claim": r"\b(?:high[- ](?:in[- ])?protein|rich in protein|source of protein|riche en proteines?|source de proteines?)\b|\+\s*protein|\b\d+(?:[.,]\d+)?\s*g\s+(?:of\s+)?protein",
 "fibre_claim": r"\b(?:high (?:in )?fib(?:re|er)|source of fib(?:re|er)|riche en fibres?|source de fibres?|added fibre)\b",
 "natural_claim": r"\b(?:100\s*%\s*natural|all natural|natural ingredients|ingredients naturels|aromes exclusivement naturels|exclusivement naturels)\b",
 "gluten_free_claim": r"\b(?:gluten[- ]free|sans gluten|glutenfrei|senza glutine)\b",
 "whole_grain_claim": r"\b(?:whole[- ]?grains?|whole[- ]?wheat|grains entiers|cereales completes|ble complet)\b",
 "no_artificial": r"\b(?:no preservatives|no artificial (?:colou?rs?|flavou?rs?)|no additives|sans (?:conservateurs?|colorants?|aromes artificiels|additifs)|aucun (?:colorant|conservateur|additif))\b",
 "origin_quality_claim": r"\b(?:100\s*%\s*francais|produit en france|fabrique en france|lait francais|lait frais|origine france|filiere francaise|agriculteurs francais|schweizer milch|lait suisse|aop|aoc|igp|label rouge)\b",
 "sugar_free_claim": r"\b(?:no added sugars?|without added sugar|sans sucres?(?: ajoutes)?|sugar[- ]free|zero sucre|zuckerfrei|ohne zuckerzusatz|senza zuccheri aggiunti)\b",
 "fortification_claim": r"\b(?:high in calcium|riche en calcium|(?:riche en|source de) vitamines?\s+[abcdek]|vitamins?\s+[abcdek]|opti[- ](?:start|grow|dej))\b",
 "vegan_claim": r"\b(?:vegan|vegano)\b",
 "plant_based_claim": r"\b(?:plant[- ]based|a base de plantes|base vegetale|pflanzenbasiert)\b",
 "energy_claim": r"\b(?:slow release|4 hours of steady energy|toute la matinee|steady energy|activgo|more power)\b",
 "reduced_fat_claim": r"\b(?:reduced fat|lower fat|less fat|low fat|fat[- ]free|allege en matieres grasses|reduit en matieres grasses|moins de graisses)\b|\b\d+\s*%\s*(?:less|reduced)\s*fat",
 "clean_label_claim": r"\b(?:clean label|simple ingredients|nothing artificial|ingredients you can see|sans additifs|no additives)\b",
 "reduced_sugar": r"\b(?:moins de sucres?|allege en sucres?|reduced sugar|less sugar)\b",
 "dairy_free_claim": r"\b(?:dairy[- ]free|non[- ]dairy|sans produits laitiers)\b",
 "gut_health_claim": r"\b(?:gut health|digestive health|supports digestion|digestive comfort|healthy digestion|microbiome support|intestinal flora|regularity|transit support|intestinal function|confort digestif|flore intestinale)\b",
 "no_palm_oil": r"\b(?:no palm oil|sans huile de palme)\b",
 "lactose_free_claim": r"\b(?:lactose[- ]free|sans lactose|laktosefrei|lactosevrij)\b",
 "heritage_claim": r"\b(?:the original|since 19\d\d|established|depuis (?:18|19)\d\d|recette originale|l.original)\b",
 "immune_claim": r"\b(?:immune support|supports the immune system|immunity|natural defences|immune defence|systeme immunitaire|defensas|difese)\b",
 "reformulation_claim": r"\b(?:nouvelle recette|new recipe|neue rezeptur|improved recipe)\b",
 "prebiotic_claim": r"\b(?:prebiotic|prebiotique|prebiotiques|feeds beneficial bacteria|supports beneficial gut bacteria)\b",
 "minimal_ingredients_claim": r"\b(?:only\s+\d+\s+ingredients|\d+\s+ingredients|nur\s+3\s+zutaten)\b",
 "vitalite_concept": r"\bvitalite\b",
 "brain_health_claim": r"\b(?:brain health|cognitive health|supports memory|mental performance|cognitive function)\b",
 "sleep_claim": r"\b(?:sleep support|restful sleep|supports sleep quality|helps you sleep|bedtime support|night[- ]time relaxation|sleep quality)\b",
}
CUES = {k: re.compile(v) for k, v in CUES.items()}
CONTEXT_SENSITIVE = {"fortification_claim", "probiotic_claim", "prebiotic_claim",
                     "gut_health_claim", "immune_claim", "brain_health_claim", "sleep_claim", "energy_claim"}
HUMAN = {
 "3760049720013": {"no_artificial": True},
 "898999000022": {"heritage_claim": True},
 "3286010034816": {"natural_claim": False},
 "0856100003294": {"protein_claim": True, "plant_based_claim": True, "gluten_free_claim": True},
 "3256228104335": {"fortification_claim": True},
 "5060120283061": {"organic_claim": False},
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def obj(value):
    if not value:
        return {}
    value = json.loads(value)
    return value if isinstance(value, dict) else {}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text.lower())
                           if not unicodedata.combining(c)).split())


def energy_members():
    body = ENERGY_CHECK.read_text(encoding="utf8")
    lists = re.findall(chr(96) + r"([0-9]+(?: [0-9]+){10,})" + chr(96), body)
    assert [len(s.split()) for s in lists] == [15, 38, 53]
    return {(b, region, "beverages") for region, s in zip(("FR", "UK-IE", "US-CA"), lists) for b in s.split()}


def historical_rows(roster, input_paths):
    cache = {}
    linked = []
    handoff = []
    for r in roster:
        if r["action"] != "Reuse core":
            continue
        sources = []
        reason = ""
        for ref in r["evidence"].split(" | "):
            filename, record = ref.rsplit(" record ", 1)
            path = ROOT / "data/05_vision_release" / filename
            input_paths.add(path)
            if path not in cache:
                cache[path] = csv_rows(path)
            source = cache[path][int(record) - 1]
            if any(source.get(k) != r[field] for k, field in
                   (("barcode", "barcode"), ("product_name", "product"), ("image_url", "image_url"))):
                reason = "Identity/reference mismatch"
            if source.get("ocr_status") != "success" or source.get("llm_status") != "success":
                reason = "Saved historical stages not successful"
            sources.append((ref, source))
        claims = [obj(s["claims_json"]) for _, s in sources]
        if len({dumps(c) for c in claims}) != 1 or len({s["ocr_text"] for _, s in sources}) != 1:
            reason = "Multiple linked payloads disagree"
        if reason:
            handoff.append(dict(barcode=r["barcode"], reason=reason, source_references=r["evidence"]))
            continue
        h = sources[0][1]
        core = claims[0]
        linked.append(dict(barcode=r["barcode"], product_name=r["product"], region="US-CA",
            category="dairy", image_url=r["image_url"], ocr_text_full=h["ocr_text"],
            core_raw_output_json="", core_normalized_output_json=dumps(core),
            overall_outcome="HISTORICAL_REUSE", issue_codes=r["claims_market_note"],
            v6_output_json="", v6_reconciled_output_json="", v6_disposition="NOT_APPLICABLE",
            normalization_reproduced="", evidence_cohort="historical_dairy_reuse",
            source_country_assignments=r["job_countries"], source_references=r["evidence"],
            historical_original_rows_json=dumps({ref: s for ref, s in sources}),
            historical_prompt_version=h.get("prompt_version", ""),
            historical_model=h.get("vision_model", ""),
            historical_source_region=h.get("sampling_region", ""),
            source_market_limitation=r["claims_market_note"]))
    return linked, handoff


def supported_cue(flag, text):
    match = CUES.get(flag)
    if match is None:
        return None
    found = match.search(normalize(text))
    return found.group(0) if found else None


def derive(row, members, module):
    raw = obj(row["core_raw_output_json"])
    norm = obj(row["core_normalized_output_json"])
    historical = row["evidence_cohort"] == "historical_dairy_reuse"
    model = norm if historical else raw
    text = row["ocr_text_full"]
    front = model.get("image_context") == "front_of_pack"
    marketing = norm.get("image_context") in {"front_of_pack", "mixed_pack_text"}
    quality = model.get("ocr_quality") == "good"
    complete = model.get("claim_extraction_status") == "completed"
    positive_present = any(model.get(f) is True for f in FLAGS)
    summary_consistent = (model.get("no_claims_detected") is False if positive_present else
                          model.get("no_claims_detected") is True)
    no_legal_clues = not re.search(r"\b(?:ingredients?|nutrition facts|valeurs nutritionnelles|may contain)\b", normalize(text))
    reliable = bool(text.strip()) and front and quality and complete and summary_consistent
    replayed = row.get("normalization_reproduced") == "true"
    decisions = {}
    for flag in FLAGS:
        raw_value, norm_value = model.get(flag), norm.get(flag)
        cue = supported_cue(flag, text)
        value, state, basis = None, "UNKNOWN", "INSUFFICIENT_ASSESSMENT"
        if (bool(text.strip()) and marketing and quality and norm.get("claim_extraction_status") == "completed"
                and cue and no_legal_clues):
            if norm_value is True or flag in {"no_artificial", "heritage_claim", "fortification_claim", "protein_claim", "gluten_free_claim", "plant_based_claim"}:
                value, state, basis = True, "USABLE_AUTOMATED_POSITIVE", "DIRECT_OCR_WORDING"
        if value is None and reliable and raw_value is True and norm_value is True:
            value, state, basis = True, "USABLE_AUTOMATED_POSITIVE", "SAVED_MODEL_ASSESSMENT"
        if (value is None and not historical and row["region"] == "UK-IE" and replayed
                and marketing and quality and norm_value is True and raw_value is not True
                and flag in {"origin_quality_claim", "clean_label_claim", "reduced_fat_claim", "protein_claim"}):
            value, state, basis = True, "USABLE_AUTOMATED_POSITIVE", "APPROVED_EXISTING_RULE"
        if value is None and reliable and raw_value is False and norm_value is False:
            if not historical or model.get("no_claims_detected") is True:
                value, state, basis = False, "DOCUMENTED_NOT_DETECTED", "SAVED_MODEL_ASSESSMENT"
        if value is None and historical and norm_value is True and quality and marketing and complete and text.strip():
            value, state, basis = True, "USABLE_AUTOMATED_POSITIVE", "HISTORICAL_SAVED_ASSESSMENT"
        # Existing cautions remain uncertainty conditions, not new negative definitions.
        phrases = normalize(" ".join(str(s) for s in (model.get("detected_claim_phrases") or [])))
        if flag == "natural_claim" and value is True and not cue and re.search(r"naturally flavo|natural flavo|arome naturel", phrases):
            value, state, basis = None, "UNCERTAIN", "FLAVOURING_VS_NATURALNESS"
        if flag in CONTEXT_SENSITIVE and value is True and basis == "DIRECT_OCR_WORDING" and not no_legal_clues:
            value, state, basis = None, "UNCERTAIN", "INGREDIENT_OR_TABLE_CONTEXT"
        if row["barcode"] in HUMAN and flag in HUMAN[row["barcode"]]:
            value = HUMAN[row["barcode"]][flag]
            state = "HUMAN_CONFIRMED_POSITIVE" if value else "HUMAN_CONFIRMED_NEGATIVE"
            basis = "JULIA_PHOTO_DECISION" if row["barcode"] != "5060120283061" else "JULIA_VARIANT_NAMING_DECISION"
        if row["barcode"] == "00976534":
            value, state, basis = None, "EXCLUDED", "JULIA_SOURCE_IDENTITY_DECISION"
        decisions[flag] = dict(value=value, state=state, basis=basis, raw=model.get(flag), normalized=norm.get(flag))
        if cue:
            decisions[flag]["ocr_wording_normalized"] = cue
        if basis.startswith("JULIA"):
            decisions[flag]["approval_source"] = "final_approval.md"
    key = (row["barcode"], row["region"], row["category"])
    member = key in members
    ambiguous = row["barcode"] in ENERGY_UNKNOWN and row["category"] == "beverages"
    conflict = row["barcode"] in ENERGY_CONFLICT and row["category"] == "beverages"
    membership = True if member else False if conflict else None
    energy = decisions["energy_claim"]
    explicit_energy = bool(supported_cue("energy_claim", text)) and energy["value"] is True
    # Respect the French benefit vocabulary, without turning category names into a general rule.
    if row["region"] == "FR" and energy["value"] is True and complete and quality:
        explicit_energy = explicit_energy or bool(
            no_legal_clues and re.search(r"\b(?:energie|tonus|coup de fouet|toute la matinee)\b", normalize(text)))
    assessed_energy_negative = (energy["value"] is False and
                               (row["category"] != "beverages" or membership is False))
    energy_value = True if member or (explicit_energy and not ambiguous) else False if assessed_energy_negative and not ambiguous else None
    energy_basis = ("SEGMENT_AND_EXPLICIT_BENEFIT" if member and explicit_energy else
                    "VERIFIED_SEGMENT" if member else "EXPLICIT_BENEFIT" if energy_value is True else
                    "DOCUMENTED_NOT_DETECTED_OUTSIDE_SEGMENT" if energy_value is False else "UNRESOLVED")
    if row["barcode"] == "00976534":
        energy_value, energy_basis = None, "EXCLUDED"
    v6 = obj(row.get("v6_reconciled_output_json", ""))
    usable_v6 = row.get("v6_disposition") in {"SAVED_ACCEPTED_PRESERVE_UNCERTAINTY", "REQUEST_ECHO_RECONCILED"}
    flat = dict(record_id=hashlib.sha256(dumps(key).encode()).hexdigest(),
        barcode=row["barcode"], region=row["region"], category=row["category"],
        product_name=row["product_name"], image_url=row["image_url"], evidence_cohort=row["evidence_cohort"],
        original_overall_outcome=row["overall_outcome"], source_country_assignments=row.get("source_country_assignments", ""),
        source_market_limitation=row.get("source_market_limitation", ""),
        analytical_eligible=row["barcode"] != "00976534",
        eligibility_reason="JULIA_VEGAN_SALAMI_EXCLUSION" if row["barcode"] == "00976534" else "RETAIN_SOURCE_POPULATION",
        energy_drink_membership=membership, energy_drink_format="preparation" if member and row["barcode"] in PREPARATIONS else "ready_to_drink" if member else "unresolved" if ambiguous else "",
        energy_positioning=energy_value, energy_positioning_basis=energy_basis,
        original_energy_claim=norm.get("energy_claim"),
        core_claim_evidence_json=dumps(decisions), source_references=row.get("source_references", ""),
        core_assessment_context=model.get("image_context", ""), core_assessment_quality=model.get("ocr_quality", ""),
        core_assessment_status=model.get("claim_extraction_status", ""), v6_disposition=row.get("v6_disposition", ""),
        v6_usable=usable_v6 and row["barcode"] != "00976534",
        nutrition_qa_hold="SALT_RECONCILIATION" if row["barcode"] in {"0641548550062", "0034500151849"} else "",
        population_qa_note="US_YOGURT_IMAGE_SELECTION_PENDING" if row["region"] == "US-CA" and row["category"] == "dairy" else "")
    for flag, decision in decisions.items():
        flat["claim_" + flag] = decision["value"]
        flat["state_" + flag] = decision["state"]
        flat["basis_" + flag] = decision["basis"]
    if row["barcode"] == "0856100003294":
        flat.update(protein_amount_g=15.0, protein_amount_basis="per_serving", protein_amount_provenance="JULIA_PHOTO_DECISION")
    else:
        amount = norm.get("protein_amount_g") if decisions["protein_claim"]["value"] is True else None
        flat.update(protein_amount_g=float(amount) if isinstance(amount, (int, float)) else None,
                    protein_amount_basis="UNSPECIFIED_PACK_CLAIM" if amount is not None else "",
                    protein_amount_provenance="SAVED_NORMALIZED_ASSESSMENT" if amount is not None else "")
    flat["fortification_nutrients_json"] = dumps(["Vitamin C"] if row["barcode"] == "3256228104335" else
        norm.get("fortification_nutrients", []) if decisions["fortification_claim"]["value"] is True else [])
    flat["fortification_meaning"] = "COMMUNICATED_NUTRIENT_POSITIONING_NOT_PROOF_OF_ADDITION"
    for benefit in ("hydration", "electrolyte"):
        assessment = v6.get(benefit, {}) if flat["v6_usable"] else {}
        flat[benefit + "_content_status"] = assessment.get("content_status", "unassessed")
        flat[benefit + "_front_status"] = assessment.get("front_status", "unassessed")
        front_status = assessment.get("front_status")
        flat[benefit + "_positioning"] = True if front_status == "detected" else False if front_status == "not_detected" else None
    return flat


def table(rows):
    names = list(dict.fromkeys(k for r in rows for k in r))
    bools = {"analytical_eligible", "energy_drink_membership", "energy_positioning", "v6_usable", "original_energy_claim",
             "hydration_positioning", "electrolyte_positioning"} | {"claim_" + f for f in FLAGS}
    schema = pa.schema([pa.field(k, pa.bool_() if k in bools else pa.float64() if k == "protein_amount_g" else pa.string(), nullable=True) for k in names])
    return pa.Table.from_pylist(rows, schema=schema)


def main():
    csv.field_size_limit(100_000_000)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-unlocked", action="store_true", help="Regenerate this output only before manifest lock")
    args = parser.parse_args()
    if (OUT / "manifest.json").exists():
        raise FileExistsError("Version has a manifest; create a new version for any change")
    if OUT.exists() and any(OUT.iterdir()) and not args.rebuild_unlocked:
        raise FileExistsError("Final lock directory already exists")
    paths = {SOURCE, CONFIG, ENERGY_CHECK, REVIEW, APPROVAL, Path(__file__).resolve(),
        SEG / "wave2_claims_reconciliation_v1/validation.json",
        SEG / "wave2_dairy_shortlist_v1/approved_selection.csv"}
    cfg = json.loads(CONFIG.read_text())
    paths.update(ROOT / p[key] for p in cfg["regional_profiles"].values() for key in ("prompt_path", "context_prompt_path"))
    paths.add(ROOT / "pipeline/stages/stage_10_extract_pack_claims.py")
    historical, handoff = historical_rows(csv_rows(SEG / "wave2_dairy_shortlist_v1/approved_selection.csv"), paths)
    before = {str(p): digest(p) for p in paths}
    assert digest(SOURCE) == json.loads((SEG / "wave2_claims_reconciliation_v1/validation.json").read_text())["csv_sha256"]
    members = energy_members()
    assert len(members) == 106 and len(historical) + len(handoff) == 35
    module = LegacyContract(cfg).module
    OUT.mkdir(exist_ok=True)
    writers = {}
    totals = Counter()
    outcomes, states, support, v6_states = Counter(), Counter(), Counter(), Counter()
    claim_counts = {f: Counter() for f in FLAGS}
    identities = set()
    human_seen = Counter()
    original_hashes = []
    def process_batch(batch, is_new):
        derived = [derive(row, members, module) for row in batch]
        thin = table(derived)
        if "join" not in writers:
            writers["join"] = pq.ParquetWriter(OUT / "claims_join.parquet", thin.schema, compression="zstd")
        writers["join"].write_table(thin)
        if is_new:
            audit = [dict(source, final_claim_evidence_json=record["core_claim_evidence_json"],
                          final_analytical_eligible=record["analytical_eligible"])
                     for source, record in zip(batch, derived)]
            arrow = pa.Table.from_pylist(audit)
            if "audit" not in writers:
                writers["audit"] = pq.ParquetWriter(OUT / "new_processed_audit.parquet", arrow.schema, compression="zstd")
            writers["audit"].write_table(arrow)
        for source, record in zip(batch, derived):
            assert record["record_id"] not in identities
            identities.add(record["record_id"])
            totals["eligible"] += record["analytical_eligible"]
            totals["excluded"] += not record["analytical_eligible"]
            decisions = obj(record["core_claim_evidence_json"])
            states.update(v["state"] for v in decisions.values())
            support.update(v["basis"] for v in decisions.values())
            if is_new:
                totals["new"] += 1
                outcomes[record["original_overall_outcome"]] += 1
                totals["members"] += record["energy_drink_membership"] is True
                totals["additional_energy"] += record["energy_drink_membership"] is True and record["original_energy_claim"] is False
                totals["preparations"] += record["energy_drink_format"] == "preparation"
                totals["energy_true"] += record["energy_positioning"] is True
                totals["outside_energy"] += record["energy_drink_membership"] is not True and record["energy_positioning"] is True
                totals["energy_false"] += record["energy_positioning"] is False
                v6_states[record["v6_disposition"]] += 1
                for f in FLAGS:
                    value = record["claim_" + f]
                    claim_counts[f]["unknown" if value is None else "true" if value else "false"] += 1
            if source["barcode"] in HUMAN:
                human_seen[source["barcode"]] += 1
                for flag,value in HUMAN[source["barcode"]].items():
                    assert record["claim_" + flag] is value
            if source["barcode"] == "0856100003294":
                assert record["protein_amount_g"] == 15 and record["protein_amount_basis"] == "per_serving"
            if source["barcode"] == "3256228104335":
                assert record["fortification_nutrients_json"] == '["Vitamin C"]'
            # Validate all typed derived values and JSON at the batch boundary.
            for f in FLAGS:
                assert record["claim_" + f] is None or type(record["claim_" + f]) is bool

    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        original_columns = list(reader.fieldnames)
        source_iter = iter(reader)
        finished = False
        while not finished:
            batch = []
            for _ in range(64):
                try:
                    source = next(source_iter)
                except StopIteration:
                    finished = True
                    break
                original_hashes.append(hashlib.sha256(dumps(source).encode()).hexdigest())
                batch.append(dict(source, evidence_cohort="new_processed",
                    source_country_assignments=source["region"],
                    source_references="wave2_claims_reconciliation_v1/reconciled_review.csv"))
            if batch:
                process_batch(batch, True)
    if historical:
        process_batch(historical, False)
        pq.write_table(pa.Table.from_pylist(historical), OUT / "historical_reuses.parquet", compression="zstd")
    for writer in writers.values():
        writer.close()
    assert totals["new"] == 12126 and outcomes == {"PASS": 8594, "HOLD": 3411, "OTHER": 121}
    assert totals["excluded"] == 2 and totals["members"] == 106 and totals["additional_energy"] == 63
    assert totals["preparations"] == 5 and v6_states["REQUEST_ECHO_RECONCILED"] == 33
    assert human_seen["0856100003294"] == 2 and human_seen["5060120283061"] == 1
    assert len(identities) == 12126 + len(historical)
    # Verify every original field after physical serialization, without loading the full audit into RAM.
    at = 0
    for batch in pq.ParquetFile(OUT / "new_processed_audit.parquet").iter_batches(batch_size=64):
        for row in batch.to_pylist():
            original = {k: row[k] for k in original_columns}
            assert hashlib.sha256(dumps(original).encode()).hexdigest() == original_hashes[at]
            at += 1
    assert at == 12126
    join_path = OUT / "claims_join.parquet"
    schema = pq.ParquetFile(join_path).schema_arrow
    assert schema.field("barcode").type == pa.string()
    assert all(schema.field("claim_" + f).type == pa.bool_() for f in FLAGS)
    sample_unknown = None
    sample_false = None
    joined_count = 0
    for batch in pq.ParquetFile(join_path).iter_batches(batch_size=64):
        for row in batch.to_pylist():
            joined_count += 1
            if row["claim_protein_claim"] is None:
                sample_unknown = row
            elif row["claim_protein_claim"] is False:
                sample_false = row
    assert joined_count == len(identities) and sample_unknown and sample_false
    right = pa.Table.from_pylist([sample_unknown, sample_false], schema=schema).select(["record_id", "claim_protein_claim"])
    probe = pa.table({"record_id": ["ABSENT", sample_unknown["record_id"], sample_false["record_id"]]}).join(
        right, keys="record_id", join_type="left outer")
    assert probe["claim_protein_claim"].null_count == 2
    assert probe["claim_protein_claim"].to_pylist().count(False) == 1
    assert all(digest(Path(path)) == h for path, h in before.items())
    (OUT / "historical_handoff.json").write_text(dumps(handoff), encoding="utf8")
    (OUT / "final_approval.md").write_bytes(APPROVAL.read_bytes())
    validation = dict(new_processed=12126, historical_linked=len(historical), historical_handoff=len(handoff),
        join_records=len(identities), eligible=totals["eligible"], excluded=2,
        new_original_outcomes=dict(outcomes), energy_segment=106, additional_segment_energy=63,
        energy_preparations=5, energy_positioning_true=totals["energy_true"],
        energy_positioning_false=totals["energy_false"],
        energy_unknown=12126-totals["energy_true"]-totals["energy_false"], energy_outside_segment_positive=totals["outside_energy"],
        states=dict(states), support=dict(support), new_claim_counts={f: dict(c) for f,c in claim_counts.items()},
        v6_states=dict(v6_states), unique_identities=True, original_fields_preserved=True,
        source_integrity=True, parquet_roundtrip_exact=True, null_join_probe_passed=True,
        sources=[{"path": path, "sha256": h} for path,h in sorted(before.items())])
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf8")
    print(json.dumps({k:v for k,v in validation.items() if k not in {"sources","new_claim_counts"}}, ensure_ascii=False))



if __name__ == "__main__":
    main()
