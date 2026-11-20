"""BEVERAGE 01: offline, read-only OCR evidence audit; no service imports/calls.

New audit outputs only. This does not change the production taxonomy, prompts,
schemas, extraction or merge scripts, source databases, RUN 05 or RUN 06A.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "presentations/segmentation/beverage_01_v1"
REPORT = ROOT / "presentations/segmentation/BEVERAGE 01 - OCR and benefits audit.md"
FRAME = ROOT / "presentations/segmentation/run_05_v1/candidate_ledger.csv"
FULL_FRAME = ROOT / "presentations/segmentation/run_01/eligibility_ledger.csv"
DB = ROOT / "database/positioning_radar.db"
PUBLIC_DB = ROOT / "database/positioning_radar_public_mvp.db"
REGIONS = ["FR", "UK+IE", "US+CA"]
REGION_MAP = {"FRANCE": "FR", "FR": "FR", "UK_IE": "UK+IE", "UK+IE": "UK+IE",
              "US_CANADA": "US+CA", "US+CA": "US+CA"}
FRONT = {"front_of_pack", "mixed_pack_text"}
STAGES = [ROOT / f"pipeline/stages/stage_{n}" for n in [
    "10_extract_pack_claims.py", "11_merge_vision_results.py", "12_build_claim_taxonomy.py"]]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def constant(path, name):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return ast.literal_eval(node.value)
    raise ValueError(name)


FIELDS = constant(STAGES[1], "PACK_CLAIM_FIELDS")


def plain(value):
    return "" if value is None else str(value)


def boolean(value):
    if value is True or plain(value).strip().lower() in {"true", "1", "1.0"}:
        return True
    if value is False or plain(value).strip().lower() in {"false", "0", "0.0"}:
        return False
    return None


def parsed_json(value):
    try:
        obj = json.loads(value or "")
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def timestamp(value):
    value = plain(value).strip()
    try:
        return datetime.strptime(value, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp()
        except ValueError:
            return 0


def pct(n, denominator):
    return round(100 * n / denominator, 4) if denominator else None


def quantile(values, p):
    if not values:
        return None
    values = sorted(values)
    x = (len(values) - 1) * p
    a, b = math.floor(x), math.ceil(x)
    return round(values[a] + (values[b] - values[a]) * (x - a), 2)


def connection(path):
    wal = Path(str(path) + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0, "Nonempty WAL; immutable reads would miss uncheckpointed data."
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def load_frame():
    corrected = defaultdict(dict)
    with FRAME.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["category"] == "beverages":
                corrected[row["barcode"]][row["region"]] = {
                    "countries": row["countries"], "name": row["product_name"],
                    "image_url": row["image_url"], "historical_success": row["existing_successful_ocr_llm"] == "1",
                    "m1_complete": row["m1_eligible"] == "1"}
    assert sum(len(v) for v in corrected.values()) == 158258
    frame = defaultdict(dict)
    countries = defaultdict(set)
    country_region = {"FR": "FR", "UK": "UK+IE", "IE": "UK+IE", "US": "US+CA", "CA": "US+CA"}
    with FULL_FRAME.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["category"] != "beverages" or row["country"] not in country_region:
                continue
            code, region = row["barcode"], country_region[row["country"]]
            countries[(code, region)].add(row["country"])
            retained = region in corrected.get(code, {})
            frame[code][region] = dict(corrected[code][region]) if retained else {
                "name": row["product_name"], "image_url": row["image_url"],
                "historical_success": False, "m1_complete": False}
            frame[code][region]["in_corrected_RUN05_frame"] = retained
    for (code, region), assignment in countries.items():
        frame[code][region]["countries"] = "|".join(sorted(assignment))
    assert sum(v["in_corrected_RUN05_frame"] for rr in frame.values() for v in rr.values()) == 158258
    return frame


def normalize(row, source, source_row, layer):
    code = plain(row.get("barcode")).strip()
    claims = parsed_json(row.get("claims_json"))
    flags = {}
    for field in FIELDS:
        if "v3_" + field in row:
            flags[field] = boolean(row["v3_" + field])
        else:
            flags[field] = boolean(claims.get(field))
    stored_codes = row.get("pack_claims_found")
    codes = {k for k, v in flags.items() if v is True}
    if stored_codes is not None:
        codes |= set(plain(stored_codes).split("|")) & set(FIELDS)
    llm = plain(row.get("llm_status")).strip().lower()
    extraction = plain(row.get("v3_claim_extraction_status", row.get("claim_extraction_status", claims.get("claim_extraction_status")))).strip()
    context = plain(row.get("v3_image_context", row.get("image_context", claims.get("image_context")))).strip()
    quality = plain(row.get("v3_ocr_quality", claims.get("ocr_quality"))).strip()
    raw_text = row.get("ocr_text")
    text = plain(raw_text)
    stripped = text.strip()
    if "ocr_text" not in row:
        state = "missing_field"
    elif raw_text is None:
        state = "missing_NULL"
    elif text == "":
        state = "empty_string"
    elif not stripped:
        state = "whitespace_only"
    elif stripped.lower() in {"nan", "none", "null"}:
        state = "placeholder_string"
    elif len(stripped) < 10 or sum(c.isalpha() for c in stripped) < 3:
        state = "short_or_nonlinguistic"
    else:
        state = "substantive_saved_text"
    ocr = plain(row.get("ocr_status")).strip().lower()
    technical = state == "substantive_saved_text" and ocr == "success"
    valid = llm == "success" and extraction == "completed"
    claim_state = ("with_claims" if codes else "no_claims" if valid and (
        stored_codes == "" or all(v is False for v in flags.values())) else "claim_state_unknown")
    request_url = plain(row.get("image_url")) if layer == "raw_result_or_checkpoint" else ""
    t = plain(row.get("pack_analysis_timestamp"))
    return {"barcode": code, "source": source, "source_row": source_row, "layer": layer,
            "text": text, "text_sha256": text_sha(text), "text_state": state,
            "ocr_status": ocr, "quality": quality or "not_saved", "technical_reuse": technical,
            "reuse_without_quality_hold": technical and quality != "poor", "valid_success": valid,
            "claim_state": claim_state, "flags": flags, "codes": sorted(codes),
            "claims_json_present": bool(claims), "context": context or "not_saved", "extraction": extraction or "not_saved",
            "prompt": plain(row.get("prompt_version")), "model": plain(row.get("vision_model")),
            "timestamp": t, "sort_time": timestamp(t), "request_url": request_url,
            "joined_product_url": plain(row.get("image_url")) if layer == "merged_result_snapshot" else plain(row.get("current_product_image_url")),
            "sampling_region": REGION_MAP.get(plain(row.get("sampling_region")), ""),
            "sampling_category": plain(row.get("sampling_category")),
            "query_category": plain(row.get("query_category")), "product_name": plain(row.get("product_name")),
            "observation_id": text_sha(json.dumps([code, text_sha(text), plain(row.get("prompt_version")),
                                                 plain(row.get("vision_model")), t, context, extraction,
                                                 sorted(codes)], separators=(",", ":")))[:20]}


def load_evidence(frame):
    inventory, evidence, outside = [], [], []
    con = connection(DB)
    query = """SELECT a.*,p.query_category,p.product_name,p.image_url AS current_product_image_url
               FROM product_analysis a JOIN products p USING(barcode)
               WHERE a.pack_analysis_attempted=1 OR a.ocr_text IS NOT NULL OR a.llm_status IS NOT NULL
               ORDER BY a.barcode"""
    inspected = 0
    for i, item in enumerate(con.execute(query), 1):
        inspected += 1
        row = dict(item)
        if row["barcode"] in frame or row["query_category"] == "beverages" or row["sampling_category"] == "beverages":
            evidence.append(normalize(row, rel(DB) + "::product_analysis", i, "merged_database"))
    con.close()
    inventory.append({"source": rel(DB), "kind": "read_only_merged_database", "rows_inspected": inspected,
                      "beverage_or_frame_evidence_rows": len(evidence), "ocr_column": True, "sha256": sha(DB), "bytes": DB.stat().st_size})
    for path in sorted((ROOT / "data/05_vision_release").glob("*.csv")):
        if not path.name.startswith(("vision_results", "merged_results", "products_vision_merged")):
            continue
        layer = "raw_result_or_checkpoint" if path.name.startswith("vision_results") else "merged_result_snapshot"
        count, used = 0, 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            has_ocr = "ocr_text" in reader.fieldnames
            for count, row in enumerate(reader, 1):
                if not has_ocr:
                    continue
                if row.get("barcode") in frame or row.get("sampling_category") == "beverages" or row.get("query_category") == "beverages":
                    evidence.append(normalize(row, rel(path), count + 1, layer))
                    used += 1
        inventory.append({"source": rel(path), "kind": ("saved_checkpoint" if "checkpoint" in path.name else layer) if has_ocr else "product_export_without_OCR",
                          "rows_inspected": count, "beverage_or_frame_evidence_rows": used, "ocr_column": has_ocr,
                          "sha256": sha(path), "bytes": path.stat().st_size})
    con = connection(PUBLIC_DB)
    public_cols = [r[1] for r in con.execute("PRAGMA table_info(product_analysis)")]
    con.close()
    inventory.append({"source": rel(PUBLIC_DB), "kind": "public_database_schema_only_no_OCR" if "ocr_text" not in public_cols else "public_database",
                      "rows_inspected": 0, "beverage_or_frame_evidence_rows": 0, "ocr_column": "ocr_text" in public_cols,
                      "sha256": sha(PUBLIC_DB), "bytes": PUBLIC_DB.stat().st_size})
    # Exact mirrored classification observations are not independent attempts.
    by_product = defaultdict(list)
    for item in evidence:
        if item["barcode"] in frame:
            by_product[item["barcode"]].append(item)
        elif item["sampling_category"] == "beverages" or item["query_category"] == "beverages":
            outside.append(item)
    return evidence, by_product, inventory, outside


def preference(o):
    return (o["valid_success"], o["reuse_without_quality_hold"], o["technical_reuse"],
            o["sort_time"], {"merged_database": 3, "raw_result_or_checkpoint": 2, "merged_result_snapshot": 1}[o["layer"]],
            o["source"], str(o["source_row"]))


# Search-family names below are audit buckets, NOT new production taxonomy codes.
PATTERNS = {
    "hydration_wording": r"\b(?:re)?hydrat(?:ion|ation|e|es|ed|ing|er|ant|ante|antes|ants|[ée]e?s?)\b|\br[ée]hydrat(?:ation|ant|er|[ée]e?)\b|\b(?:d[ée]shydratation|dehydration)\b",
    "electrolyte_wording": r"\b[ée]lectrolytes?\b|\b[ée]lectrolytiques?\b",
    "electrolyte_ingredient_proxy": r"\b(?:sodium citrate|potassium chloride|potassium citrate|magnesium|magn[ée]sium|citrate de (?:sodium|potassium)|chlorure de potassium)\b",
    "recovery_wording": r"\b(?:recovery|recover|r[ée]cup[ée]ration|r[ée]cup[ée]rer)\b",
    "stress_calm_wording": r"\b(?:stress|calm|calming|relaxation|relax|d[ée]tente|apaisant|anti-stress)\b",
    "skin_beauty_collagen_wording": r"\b(?:collagen|collag[èe]ne|skin health|healthy skin|beauty|beaut[ée]|sant[ée] de la peau)\b",
    "heart_cholesterol_wording": r"\b(?:heart health|healthy heart|cholesterol|cholest[ée]rol|cardiovascular|cardiovasculaire|sant[ée] cardiaque)\b",
    "joint_mobility_wording": r"\b(?:joint health|joint support|mobility|articulations|mobilit[ée])\b",
    "antioxidant_wording": r"\b(?:antioxidants?|anti-?oxydants?)\b",
    "adaptogen_wording": r"\b(?:adaptogens?|adaptog[èe]nes?|ashwagandha)\b",
}
COMPILED = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
SECTION = re.compile(r"\b(ingredients?|ingr[ée]dients?|nutrition(?:al)?(?: facts| information)?|valeurs? nutritionnelles?)\s*[:\n]", re.I)
PROMO = re.compile(r"\b(supports?|helps?|improv\w*|promotes?|boost\w*|enhanced|enriched|with|added|for|aide|contribue|favorise|soutient|am[ée]liore|renforce|enrichi|avec|pour)\b", re.I)


def find_wording(item):
    text = item["text"]
    hits = []
    for family, expression in COMPILED.items():
        for m in expression.finditer(text):
            left, right = max(0, m.start() - 110), min(len(text), m.end() + 140)
            context = text[left:right]
            prefix = text[max(0, m.start() - 240):m.start()]
            section = list(SECTION.finditer(prefix))
            section_type = section[-1].group(1).lower() if section else ""
            taste = bool(re.search(r"\b(?:added\s+)?for\s+taste\b|\bpour le go[uû]t\b", context, re.I))
            matched_line = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end()) if text.find("\n", m.end()) >= 0 else len(text)]
            promo_line = bool(re.search(r"\b(?:plus|with|added|avec|enrichi|natural)\b", matched_line, re.I))
            if family == "electrolyte_wording" and taste:
                meaning = "taste_statement_not_hydration_claim"
            elif family == "heart_cholesterol_wording" and re.search(r"(?:no\s+cholesterol|cholesterol\s+free|sans\s+cholest[ée]rol)", context, re.I):
                meaning = "cholesterol_absence_not_heart_benefit"
            elif section_type and promo_line:
                meaning = "ambiguous_mixed_ingredient_marketing"
            elif section_type:
                meaning = "ingredient_or_nutrition_context"
            elif family == "electrolyte_ingredient_proxy":
                meaning = "mineral_mention_not_hydration_evidence"
            elif (family in {"hydration_wording", "electrolyte_wording"} or PROMO.search(context)):
                meaning = "possible_benefit_proposition"
            else:
                meaning = "ambiguous_wording_or_ingredient"
            zone = "after_2000" if m.start() >= 2000 else "straddles_2000" if m.end() > 2000 else "within_2000"
            hits.append({"family": family, "meaning": meaning, "zone": zone, "match": m.group(),
                         "match_start_0based": m.start(), "match_end_exclusive": m.end(),
                         "context_start_0based": left, "exact_context": context,
                         "matched_line": matched_line, "ingredient_nutrition_header_nearby": section_type,
                         "front_pack_context": item["context"] in FRONT,
                         "review_state": "Literal wording confirmed by substring; semantic interpretation pending review"})
    return hits


ACTION = re.compile(r"\b(?:supports?|helps?|contributes? to|promotes?|aide [àa]|contribue [àa]|favorise|soutient|renforce|am[ée]liore)\b[^\n.!?]{3,105}", re.I)


def action_phrases(item):
    result = []
    for m in ACTION.finditer(item["text"]):
        # No known-benefit whitelist: open phrase exploration, not classification.
        left, right = max(0, m.start() - 65), min(len(item["text"]), m.end() + 65)
        result.append({"family": "open_action_phrase_discovery", "meaning": "unclassified_action_phrase_review",
                       "zone": "after_2000" if m.start() >= 2000 else "straddles_2000" if m.end() > 2000 else "within_2000",
                       "match": m.group(), "match_start_0based": m.start(), "match_end_exclusive": m.end(),
                       "context_start_0based": left, "exact_context": item["text"][left:right],
                       "matched_line": m.group(), "ingredient_nutrition_header_nearby": "",
                       "front_pack_context": item["context"] in FRONT,
                       "review_state": "Exploratory wording only; may be an existing benefit, instruction or boilerplate"})
    return result


def csv_bytes(records):
    assert records
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8-sig")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def md_table(records, fields):
    def show(value):
        if value is None:
            return "n/a"
        return f"{value:,}" if isinstance(value, int) else str(value).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(label for _, label in fields) + " |",
                      "|" + "---|" * len(fields),
                      *["| " + " | ".join(show(row[key]) for key, _ in fields) + " |" for row in records]])


def profile_inventory():
    profiles = constant(STAGES[0], "LANGUAGE_PROFILES")
    result = []
    for profile, config in profiles.items():
        path = ROOT / "pipeline/vision_prompts/current" / config["prompt_file"]
        text = path.read_text(encoding="utf-8")
        obj = text[text.index("{"):text.index("\n}") + 2]
        keys = re.findall(r'^\s*"([^"\n]+)"\s*:', obj, re.M)
        result.append({"profile": profile, "role": "extraction", "path": rel(path),
                       "active_version_label": config["version"], "sha256": sha(path),
                       "schema_keys_count": len(keys), "schema_keys": json.dumps(keys),
                       "mapped_claim_fields_in_schema": len(set(keys) & set(FIELDS)),
                       "mapped_claim_fields_missing_from_prompt": "|".join(sorted(set(FIELDS) - set(keys))),
                       "context_review_file": config["context_review_prompt"],
                       "review_gate": "ingredient_or_legal_panel AND category in {dairies,dairy}; not beverages",
                       "llm_ocr_input_max_characters": 2000, "max_output_tokens": 800,
                       "image_input_to_llm": False, "UK_contextual_rescues": bool(config.get("apply_uk_claim_rescue_rules")),
                       "full_size_image_preference": bool(config.get("prefer_full_size_off_image"))})
    for name in ["prompt_en_context_review.txt", "prompt_fr_context_review.txt"]:
        path = ROOT / "pipeline/vision_prompts/current" / name
        result.append({"profile": "en/uk" if "_en_" in name else "fr", "role": "context_review", "path": rel(path),
                       "active_version_label": "No separate persisted reviewer version; file content hashed for this audit",
                       "sha256": sha(path), "schema_keys_count": 1, "schema_keys": '["image_context"]',
                       "mapped_claim_fields_in_schema": 0, "mapped_claim_fields_missing_from_prompt": "not a benefit extractor",
                       "context_review_file": "", "review_gate": "dairy legal-panel gate only",
                       "llm_ocr_input_max_characters": 2000, "max_output_tokens": 60,
                       "image_input_to_llm": False, "UK_contextual_rescues": False,
                       "full_size_image_preference": False})
    return result


def dedup_texts(observations):
    by_hash = {}
    for obs in observations:
        if obs["text_state"] == "substantive_saved_text":
            h = obs["text_sha256"]
            by_hash[h] = max(obs, by_hash.get(h, obs), key=preference)
    return list(by_hash.values())


def image_provenance(item, observations, current_url):
    urls = sorted({o["request_url"] for o in observations if o["text_sha256"] == item["text_sha256"] and o["request_url"]})
    def revision(url):
        return re.sub(r"\.(?:\d+|full)\.(?:jpg|png)$", "", url)
    if not urls:
        state = "no_same_text_original_request_URL"
    elif current_url in urls:
        state = "original_request_URL_equals_current_URL_not_pixel_verification"
    elif current_url and any(revision(u) == revision(current_url) for u in urls):
        state = "same_URL_image_revision_different_derivative_not_pixel_verification"
    else:
        state = "different_or_missing_current_URL_unverified_evidence_change"
    return urls, state


def validation_rows():
    data = [
        ("V01", "Freeze evidence and test set", "Audit case_id, source SHA256, source row, OCR SHA256/full length, original flags/context/prompt/model are fixed; source files unchanged.", "100% references resolvable; no silently substituted image, text or historical result."),
        ("V02", "Old raw flags preserved", "Compare all 34 PACK_CLAIM_FIELDS per same-evidence case, including sugar_free_claim/reduced_sugar, other functional and organic flags; track old true -> new false/NULL and false -> true separately.", "Zero unexplained old-positive losses. Missing output keys are unavailable, not negative. Every discrepancy adjudicated before promotion."),
        ("V03", "Option B isolation", "Store emerging observations separately; compare legacy flags, pack_claims_found, claims_json and historical records before/after.", "Byte-identical legacy outputs; zero overwrites. Added benefit does not erase an old no-claim observation."),
        ("V04", "Positive and negative wording review", "Humans mark exact spans as benefit proposition / product-feature statement / taste statement / ingredient / nutrition table / ambiguous. Review both English and French wording and contextual counterexamples.", "All claimed positives have exact supporting spans and human-approved interpretation; zero unreviewed ingredient-only or for-taste matches promoted as hydration."),
        ("V05", "No-claim semantics", "Include valid historical no-claim cases plus failures/non-front controls; a new hydration detection may coexist with historical no tracked claim.", "New detection on genuine saved wording is a taxonomy extension; old no-claim history is retained. Failed/unassessable is never interpreted as negative."),
        ("V06", "Truncation separation", "First compare old/new main prompt using identical first-2000 input, metadata and model. Evaluate full-text/chunked evidence separately for added tail detections.", "No attribution of a longer-input detection to schema-only improvement; recover every adjudicated tail span. Do not invent long UK/US examples when none are present."),
        ("V07", "Taxonomy versus extraction", "Compare raw flags and exact evidence before comparing priority category_1/category_2; adding a functional benefit may change priority while old flags remain.", "Priority relabelling alone is not regression. A disappearing old raw flag is a regression candidate even if the primary group is unchanged."),
        ("V08", "Non-determinism control", "If Option A is tested, pair frozen unchanged-prompt controls with extended-prompt runs on the same OCR; repeat a small prespecified difficult subset. Option B compares emerging output against adjudicated spans only.", "Report control-vs-history drift separately from candidate-vs-control drift; unresolved losses block main-prompt replacement."),
        ("V09", "Coverage and uncertainty", "Report precision/recall against adjudicated test labels per family/language/context; denominators and missing/unassessed outputs explicit. This is a challenge set, not a prevalence sample.", "Zero unexplained misses among adjudicated explicit hydration/electrolyte positives; zero promoted confirmed negatives; ambiguous cases may remain unresolved. Small-set results are not population accuracy."),
        ("V10", "Execution authorization", "Exact test cases, extraction configuration, prompt/layer version, allowed call count and spending guard approved separately. No OCR needed for suitable saved text; unsuitable evidence remains a separate decision.", "Audit performs zero service calls. Future Option B trial <= number of approved cases; Option A paired trial <=2x cases plus separately approved repeats."),
    ]
    return [{"criterion_id": code, "test": title, "method": method, "proposed_acceptance": acceptance,
             "status": "Proposed validation design; no paid test run"} for code, title, method, acceptance in data]


def output_audit(verify_only=False, replace_draft=False):
    frame = load_frame()
    evidence, products, inventory, outside = load_evidence(frame)
    profiles = profile_inventory()
    source_hashes = {row["source"]: row["sha256"] for row in inventory}
    protected = [FRAME, FULL_FRAME, *STAGES, ROOT / "pipeline/stages/stage_05_load_database.py",
                 ROOT / "presentations/segmentation/beverages_to_check.md",
                 ROOT / "presentations/segmentation/run_05_v1/run_05_manifest.json",
                 ROOT / "presentations/segmentation/run_05_v1/check_05_approval.json",
                 ROOT / "presentations/segmentation/run_06a_v1/check_06a_approval.json",
                 ROOT / "docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md",
                 ROOT / "docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md",
                 ROOT / "docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md",
                 ROOT / "shared/db.py", ROOT / "shared/labels.py"]
    protected += [ROOT / row["path"] for row in profiles]
    for path in protected:
        source_hashes[rel(path)] = sha(path)
    baseline_approval = json.loads((ROOT / "presentations/segmentation/run_05_v1/check_05_approval.json").read_text())
    assert source_hashes[rel(FRAME)] == baseline_approval["ledger"]["sha256"]
    summaries, diagnostics, discoveries = [], [], []
    selected_success = {}
    wording_pool, all_tests = [], []
    test_gaps, seen_test_products = [], set()
    all_hits = {}
    for region in REGIONS:
        codes = sorted(code for code, rr in frame.items() if region in rr)
        with_history = [code for code in codes if products.get(code)]
        successes = {}
        for code in with_history:
            valid = [o for o in products[code] if o["valid_success"]]
            if valid:
                successes[code] = max(valid, key=preference)
        selected_success[region] = successes
        success_list = list(successes.values())
        db_success = {code for code in with_history if any(o["valid_success"] and o["layer"] == "merged_database" for o in products[code])}
        saved_success = {code for code in with_history if any(o["valid_success"] and o["layer"] != "merged_database" for o in products[code])}
        technical = [o for o in success_list if o["technical_reuse"]]
        nonpoor = [o for o in success_list if o["reuse_without_quality_hold"]]
        original_urls = [image_provenance(o, products[o["barcode"]], frame[o["barcode"]][region]["image_url"]) for o in success_list]
        db_latest = [next(o for o in products[code] if o["layer"] == "merged_database") for code in with_history
                     if any(o["layer"] == "merged_database" for o in products[code])]
        frozen_success = {code for code in codes if frame[code][region]["historical_success"]}
        summary = {
            "region": region, "all_scoped_beverage_products": len(codes),
            "physically_valid_beverage_products": sum(frame[code][region]["in_corrected_RUN05_frame"] for code in codes),
            "products_with_any_saved_attempt_evidence": len(with_history),
            "recognized_success_products": len(successes), "valid_no_claim_success_products": sum(o["claim_state"] == "no_claims" for o in success_list),
            "with_claim_success_products": sum(o["claim_state"] == "with_claims" for o in success_list),
            "unknown_claim_state_success_products": sum(o["claim_state"] == "claim_state_unknown" for o in success_list),
            "success_with_substantive_stored_text": sum(o["text_state"] == "substantive_saved_text" for o in success_list),
            "success_with_technical_reuse_text": len(technical), "success_reusable_without_poor_quality_hold": len(nonpoor),
            "success_missing_NULL_or_field": sum(o["text_state"] in {"missing_NULL", "missing_field"} for o in success_list),
            "success_empty_or_whitespace": sum(o["text_state"] in {"empty_string", "whitespace_only"} for o in success_list),
            "success_short_placeholder_or_nonlinguistic": sum(o["text_state"] in {"short_or_nonlinguistic", "placeholder_string"} for o in success_list),
            "success_OCR_status_not_success": sum(o["ocr_status"] != "success" for o in success_list),
            "success_reported_OCR_quality_poor": sum(o["quality"] == "poor" for o in success_list),
            "attempted_products_without_valid_success": len(with_history) - len(successes),
            "attempted_products_without_any_technical_text": sum(not any(o["technical_reuse"] for o in products[code]) for code in with_history),
            "unattempted_in_saved_sources": len(codes) - len(with_history),
            "DB_attempts_with_missing_NULL_text": sum(o["text_state"] in {"missing_NULL", "missing_field"} for o in db_latest),
            "DB_attempts_with_empty_or_whitespace_text": sum(o["text_state"] in {"empty_string", "whitespace_only"} for o in db_latest),
            "DB_attempts_with_short_placeholder_or_nonlinguistic_text": sum(o["text_state"] in {"short_or_nonlinguistic", "placeholder_string"} for o in db_latest),
            "DB_attempts_with_OCR_status_not_success": sum(o["ocr_status"] != "success" for o in db_latest),
            "success_text_over_2000": sum(len(o["text"]) > 2000 for o in success_list),
            "success_text_over_2000_pct": pct(sum(len(o["text"]) > 2000 for o in success_list), len(success_list)),
            "merged_database_success_products": len(db_success), "saved_file_success_products": len(saved_success),
            "success_in_both_database_and_files": len(db_success & saved_success),
            "success_database_only": len(db_success - saved_success), "success_files_only": len(saved_success - db_success),
            "success_outside_corrected_RUN05_population": sum(not frame[code][region]["in_corrected_RUN05_frame"] for code in successes),
            "success_not_in_frozen_RUN05_history": sum(frame[code][region]["in_corrected_RUN05_frame"] and code not in frozen_success for code in successes),
            "frozen_success_not_recovered_in_current_sources": len(frozen_success - set(successes)),
            "success_with_same_text_original_request_URL": sum(bool(urls) for urls, state in original_urls),
            "success_request_URL_equals_current_URL": sum(state.startswith("original_request_URL_equals") for urls, state in original_urls),
            "success_same_revision_different_derivative": sum(state.startswith("same_URL_image_revision") for urls, state in original_urls),
            "success_request_URL_different_or_current_missing": sum(state.startswith("different_or_missing") for urls, state in original_urls),
            "success_original_request_URL_unknown": sum(not urls for urls, state in original_urls),
            "historical_pixel_hashes_available": 0,
            "success_with_original_OFF_URL_language_revision": sum(any(re.search(r"/[a-z]+_[a-z]{2}(?:-[A-Za-z]+)?\.\d+\.(?:\d+|full)\.(?:jpg|png)$", url) for url in urls) for urls, state in original_urls),
            "success_with_saved_prompt_version": sum(bool(o["prompt"]) for o in success_list),
            "success_with_saved_model_name": sum(bool(o["model"]) for o in success_list),
            "success_with_saved_capture_timestamp": sum(bool(o["timestamp"]) for o in success_list),
            "old_structured_JSON_available": sum(o["claims_json_present"] for o in success_list),
        }
        assert summary["recognized_success_products"] == summary["valid_no_claim_success_products"] + summary["with_claim_success_products"] + summary["unknown_claim_state_success_products"]
        summaries.append(summary)
        regional_rows = [o for code in with_history for o in products[code]]
        for layer in ["preferred_success_per_product", "distinct_stored_text_per_product", "merged_database", "saved_files_deduplicated_classifications"]:
            if layer == "preferred_success_per_product":
                obs = success_list
            elif layer == "distinct_stored_text_per_product":
                obs = [o for code in with_history for o in dedup_texts(products[code])]
            else:
                items = [o for o in regional_rows if (o["layer"] == "merged_database") == (layer == "merged_database")]
                obs = list({o["observation_id"]: o for o in items}.values())
            lengths = [len(o["text"]) for o in obs if o["text_state"] == "substantive_saved_text"]
            values = {
                "observation_count": len(obs), "substantive_text_n": len(lengths),
                "length_p05": quantile(lengths, .05), "length_median": quantile(lengths, .50),
                "length_p95": quantile(lengths, .95), "length_max": max(lengths) if lengths else None,
                "length_over_2000_n": sum(n > 2000 for n in lengths),
                "length_over_2000_pct_of_substantive": pct(sum(n > 2000 for n in lengths), len(lengths)),
                "length_exactly_2000_n": sum(n == 2000 for n in lengths),
            }
            values.update({"context_" + k: v for k, v in Counter(o["context"] for o in obs).items()})
            values.update({"OCR_quality_" + k: v for k, v in Counter(o["quality"] for o in obs).items()})
            values.update({"text_state_" + k: v for k, v in Counter(o["text_state"] for o in obs).items()})
            values.update({"prompt_" + k: v for k, v in Counter(o["prompt"] or "not_saved" for o in obs).items()})
            values.update({"model_" + k: v for k, v in Counter(o["model"] or "not_saved" for o in obs).items()})
            for metric, value in values.items():
                diagnostics.append({"region": region, "evidence_population": layer, "metric": metric, "value": value,
                                    "denominator": "specified population; text percent denominator=substantive_text_n"})
        regional_hits = []
        for code in with_history:
            for o in dedup_texts(products[code]):
                hits = find_wording(o) + action_phrases(o)
                all_hits[(region, code, o["text_sha256"])] = hits
                for h in hits:
                    regional_hits.append((o, h))
        buckets = defaultdict(list)
        for o, h in regional_hits:
            key = (h["family"], h["meaning"], h["zone"], o["context"] in FRONT and o["valid_success"])
            buckets[key].append((o, h))
        for (family, meaning, zone, valid_front), hits in sorted(buckets.items()):
            discoveries.append({"region": region, "search_family_NOT_taxonomy": family, "interpretation_hint_NOT_label": meaning,
                                "position_relative_to_2000": zone, "valid_success_front_context": valid_front,
                                "literal_matches": len(hits), "distinct_products": len({o["barcode"] for o, h in hits}),
                                "distinct_product_texts": len({(o["barcode"], o["text_sha256"]) for o, h in hits}),
                                "review_state": "Text matches only; no benefit labels created"})
            # Representative excerpts, bounded per bucket, never full OCR exports.
            order = sorted(hits, key=lambda pair: text_sha(pair[0]["barcode"] + pair[0]["text_sha256"] + str(pair[1]["match_start_0based"])))
            seen = set()
            for o, h in order:
                if o["barcode"] in seen:
                    continue
                seen.add(o["barcode"])
                wording_pool.append({"region": region, "barcode": o["barcode"], "observation_id": o["observation_id"],
                                     "source": o["source"], "source_row": o["source_row"], "source_sha256": source_hashes[o["source"].split("::")[0]],
                                     "ocr_sha256": o["text_sha256"], "ocr_length": len(o["text"]),
                                     "old_context": o["context"], "old_claim_codes": "|".join(o["codes"]),
                                     "old_OCR_quality": o["quality"],
                                     "old_valid_success": o["valid_success"], "old_prompt_version": o["prompt"], **h})
                if len(seen) == (1 if family == "open_action_phrase_discovery" else 2):
                    break

        def valid_case(o):
            return o["valid_success"] and o["reuse_without_quality_hold"] and o["context"] in FRONT
        tests = list(successes.values())
        def hits_for(o):
            return all_hits.get((region, o["barcode"], o["text_sha256"]), [])
        definitions = [
            ("sugar_claim_preservation", 2, lambda o: bool(set(o["codes"]) & {"sugar_free_claim", "reduced_sugar"})),
            ("other_functional_preservation", 2, lambda o: bool(set(o["codes"]) & {"protein_claim", "fibre_claim", "gut_health_claim", "probiotic_claim", "fortification_claim", "energy_claim"})),
            ("organic_or_multiple_benefits", 1, lambda o: "organic_claim" in o["codes"] or len(o["codes"]) >= 3),
            ("likely_hydration_electrolyte_wording", 2, lambda o: any(h["family"] in {"hydration_wording", "electrolyte_wording"} and h["meaning"] == "possible_benefit_proposition" for h in hits_for(o))),
            ("ingredient_taste_or_ambiguous_electrolyte", 2, lambda o: any(h["family"] in {"electrolyte_ingredient_proxy", "electrolyte_wording"} and h["meaning"] != "possible_benefit_proposition" for h in hits_for(o))),
            ("valid_historical_no_claim", 2, lambda o: o["claim_state"] == "no_claims"),
            ("OCR_over_2000", 1, lambda o: len(o["text"]) > 2000),
        ]
        # Select challenge cases, not RUN 06B OCR candidates. Frozen exact identities.
        for role, requested, predicate in definitions:
            available = [o for o in tests if valid_case(o) and predicate(o)]
            ordered = sorted(available, key=lambda o: text_sha("BEVERAGE01|20261023|" + role + "|" + o["barcode"] + "|" + o["text_sha256"]))
            chosen = []
            for o in ordered:
                if o["barcode"] not in seen_test_products:
                    chosen.append(o)
                    seen_test_products.add(o["barcode"])
                if len(chosen) == requested:
                    break
            test_gaps.append({"region": region, "role": role, "requested": requested, "available_before_other_roles": len(available), "chosen": len(chosen)})
            for o in chosen:
                urls, image_state = image_provenance(o, products[o["barcode"]], frame[o["barcode"]][region]["image_url"])
                all_tests.append({"case_id": "B01_" + str(len(all_tests) + 1).zfill(3), "region": region,
                                  "barcode": o["barcode"], "role": role, "product_name": frame[o["barcode"]][region]["name"],
                                  "source": o["source"], "source_row": o["source_row"], "source_sha256": source_hashes[o["source"].split("::")[0]],
                                  "observation_id": o["observation_id"], "ocr_sha256": o["text_sha256"], "ocr_length": len(o["text"]),
                                  "old_prompt_version": o["prompt"], "old_model": o["model"], "old_context": o["context"],
                                  "old_claim_state": o["claim_state"], "old_claim_codes": "|".join(o["codes"]),
                                  "old_raw_flags_json": json.dumps(o["flags"], sort_keys=True),
                                  "same_text_original_request_URLs": "|".join(urls), "image_provenance_state": image_state,
                                  "matched_audit_families": "|".join(sorted({h["family"] for h in hits_for(o)})),
                                  "has_matched_wording_after_2000": any(h["zone"] != "within_2000" for h in hits_for(o)),
                                  "gold_benefit_label": "Pending human adjudication; no automatic taxonomy label",
                                  "authorization": "Proposed fixed audit test case only; no paid run or RUN06B selection authorized"})

    # Compact output tables follow; source files, old classifications and all
    # underlying OCR remain untouched and are not copied into review outputs.
    return render_outputs(frame, evidence, products, inventory, outside, profiles, source_hashes,
                          summaries, diagnostics, discoveries, wording_pool, all_tests, test_gaps,
                          verify_only, replace_draft)


def render_outputs(frame, evidence, products, inventory, outside, profiles, source_hashes,
                   summaries, diagnostics, discoveries, wording_pool, tests, test_gaps,
                   verify_only, replace_draft):
    success_codes = {code for code, obs in products.items() if any(o["valid_success"] for o in obs)}
    unique_success_texts = [max([o for o in products[code] if o["valid_success"]], key=preference) for code in success_codes]
    success_assignments = sum(r["recognized_success_products"] for r in summaries)
    reusable_assignments = sum(r["success_reusable_without_poor_quality_hold"] for r in summaries)
    unique_reusable = sum(o["reuse_without_quality_hold"] for o in unique_success_texts)
    raw_db_rows = [o for o in evidence if o["layer"] == "merged_database"]
    layers = Counter(row["kind"] for row in inventory)
    length_rows = []
    for region in REGIONS:
        metrics = {r["metric"]: r["value"] for r in diagnostics if r["region"] == region and r["evidence_population"] == "preferred_success_per_product"}
        length_rows.append({"region": region, **{k: metrics[k] for k in ["substantive_text_n", "length_p05", "length_median", "length_p95", "length_max", "length_over_2000_n", "length_over_2000_pct_of_substantive"]}})
    hit_counts = []
    for family in PATTERNS:
        record = {"family": family}
        for region in REGIONS:
            record[region] = len({r["barcode"] for r in wording_pool if r["region"] == region and r["family"] == family})
            # Derive full counts from stored text, not the bounded excerpt table.
            full = set()
            for code, rr in frame.items():
                if region in rr:
                    for o in dedup_texts(products.get(code, [])):
                        if COMPILED[family].search(o["text"]):
                            full.add(code)
            record[region] = len(full)
        hit_counts.append(record)
    tail_counts = {region: sum(r["literal_matches"] for r in discoveries if r["region"] == region and r["position_relative_to_2000"] != "within_2000") for region in REGIONS}
    family_tail_counts = {region: sum(r["literal_matches"] for r in discoveries if r["region"] == region and r["position_relative_to_2000"] != "within_2000" and r["search_family_NOT_taxonomy"] in {"hydration_wording", "electrolyte_wording"}) for region in REGIONS}
    context_rows = []
    for region in REGIONS:
        obs = [o for code, rr in frame.items() if region in rr for o in dedup_texts(products.get(code, []))]
        context_rows.append({"region": region, "product_texts": len(obs),
                             "valid_front": sum(o["valid_success"] and o["context"] in FRONT for o in obs),
                             "non_front": sum(o["context"] in {"ingredient_or_legal_panel", "nutrition_label", "price_sticker"} for o in obs),
                             "uncertain": sum(o["context"] in {"uncertain", "not_saved"} for o in obs)})
    outside_codes = {o["barcode"] for o in outside}
    example_keys = ["3800048223549", "5025324005208", "11110902764", "813694022469", "3770010324461", "96619490004"]
    examples = []
    for code in example_keys:
        matches = [r for r in wording_pool if r["barcode"] == code]
        if not matches and code in products:
            for o in dedup_texts(products[code]):
                hh = find_wording(o)
                if hh:
                    h = hh[0]
                    examples.append({"barcode": code, "wording": h["matched_line"], "meaning": h["meaning"]})
                    break
        elif matches:
            m = sorted(matches, key=lambda r: (r["family"] == "open_action_phrase_discovery", r["match_start_0based"]))[0]
            examples.append({"barcode": code, "wording": m["matched_line"], "meaning": m["meaning"]})
    test_roles = Counter(row["role"] for row in tests)
    tests_by_region = Counter(row["region"] for row in tests)
    old_no_claim_n = sum(row["old_claim_state"] == "no_claims" for row in tests)
    all_scoped_assignments = sum(len(rr) for rr in frame.values())
    long_cases = [{"barcode": o["barcode"], "characters": len(o["text"])} for o in sorted(unique_success_texts, key=lambda o: o["barcode"]) if len(o["text"]) > 2000]
    missing_roles = [r for r in test_gaps if r["chosen"] < r["requested"]]
    schema_counts = [r["schema_keys_count"] for r in profiles if r["role"] == "extraction"]
    dependencies = [
        "pipeline/stages/stage_10_extract_pack_claims.py: LANGUAGE_PROFILES, BOOL_CLAIM_FIELDS, validate_and_normalise, extract_claims, result flattening, UK rescues, checkpoint",
        "pipeline/stages/stage_11_merge_vision_results.py: PACK_CLAIM_FIELDS, valid-observation gate, barcode UPDATE product_analysis, merged snapshots",
        "pipeline/stages/stage_12_build_claim_taxonomy.py: CLAIM_TAXONOMY, CATEGORY_1_PRIORITY, downstream flags/intersections",
        "docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md and shared/labels.py: code/display mappings",
        "shared/db.py and Streamlit claim filters/profile summaries: pack_claims_found and priority-category consumers",
        "pipeline/stages/stage_05_load_database.py and docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md: existing JSON/TEXT storage contract",
    ]
    report = f"""# BEVERAGE 01 — OCR evidence and benefit-extraction audit

**23 October 2026 — Audit complete; pending review. No service calls or production changes.**

## Recommendation

Use **Option B: an independent, versioned emerging-benefit layer on saved OCR**. Keep existing claims immutable. Use deterministic searches for discovery and adjudication; add a small LLM classification pass only if needed and separately approved. For the upcoming approved 12,000-product allocation, retain the existing main extraction method and preserve its full OCR evidence for later reuse. Validate the already-required evidence-aware checkpoint/merge before paid execution. No change to the approved allocation or budget is made here.

All **{success_assignments:,} successful regional beverage assignments ({len(success_codes):,} unique barcodes)** have substantive saved OCR with successful OCR status. **{reusable_assignments:,} assignments ({unique_reusable:,} unique barcodes)** have no saved 'poor' OCR-quality flag. The remaining {success_assignments - reusable_assignments:,} assignments need quality review, not automatic rerunning or exclusion. Only {sum(r['success_text_over_2000'] for r in summaries)} preferred successful texts exceed 2,000 characters. The audit found hydration/electrolyte wording, but also taste-only and ingredient/nutrition counterexamples. No word match has been promoted to a benefit or a new taxonomy code.

## Scope, units and reuse definitions

Primary frame: all beverage assignments in the preserved [RUN 01 ledger](run_01/eligibility_ledger.csv): **{all_scoped_assignments:,} regional products / {len(frame):,} unique barcodes** across FR, UK+IE and US+CA. This retains products regardless of nutrition validity. The exact [RUN 05 ledger](run_05_v1/candidate_ledger.csv) identifies the **158,258 corrected physically valid regional beverage products** as a subset; missing-M1 and valid no-claim outcomes remain included. This is an OCR evidence audit, not RUN 06B eligibility/selection. Country assignments are merged once per region; sums across regions can repeat barcodes. Historic sampling region and the product's primary country are different fields.

Read-only sources: working `database/positioning_radar.db::product_analysis`, all locally available `vision_results*.csv` (including normalized copies/checkpoint), and `merged_results*.csv` in `data/05_vision_release/`. Also inventoried product exports and the public database. **{len(inventory)} artifacts** inspected: {sum(r['ocr_column'] for r in inventory)} contain an OCR column. Product exports and the public MVP database do not retain raw OCR. Old initial-release result CSVs cited in the process documentation are absent from this local folder; many initial-release texts survive only in the working database. No external archive was accessed.

Success uses the existing strict **LLM success + completed extraction** contract, including valid no-claim observations. Substantive text means a non-placeholder string of at least 10 trimmed characters and at least 3 letters. Technical reuse additionally requires successful OCR status; the existing main extractor's own short-text check is 10 characters. The audit's descriptive text-quality buckets do not change any eligibility or source values. Saved `ocr_quality=poor` is an LLM assessment, not a measured OCR accuracy score or an automatic rejection. Complete pixel transcription cannot be proven: 'full OCR' here means the saved unsliced recognized text, not every word physically visible on a pack.

Repeated artifact rows are not independent paid attempts. Counts below use one preferred successful observation per barcode and region: prefer technical, non-poor saved text, then recorded time, then database/raw/snapshot provenance. This can choose an older better-quality success; it does not overwrite the latest result. Discovery searches all distinct `(barcode, exact OCR text hash)` variants, including non-front/uncertain observations. Alternative prompt/classification versions on identical text are not independent OCR reads. There are {len(evidence):,} relevant artifact/database rows in memory, {len(products):,} scoped barcodes with any evidence, and {len(outside_codes)} additional historical beverage barcodes outside the frozen physical frame ({len(outside)} rows); the latter are inventoried separately and not added to its denominator.

## Current implementation and active contracts

| Profile | Current file under `pipeline/vision_prompts/current/` | Actual stored version |
|---|---|---|
| English | `prompt_v5_en.txt` | `v4` |
| French | `prompt_v5_fr.txt` | `v5.1-fr` |
| Approved UK/Ireland | `prompt_uk_test_09.2026_final.txt` | `uk_test_09.2026_final` |

The three extraction objects contain {', '.join(str(n) for n in schema_counts)} keys respectively; [active_prompt_schema.csv](beverage_01_v1/active_prompt_schema.csv) records every exact key, file hash and missing-field comparison. The validator declares {len(constant(STAGES[0], 'BOOL_CLAIM_FIELDS'))} boolean-style fields including the no-claim indicator; Stage 11 and Stage 12 recognize **{len(FIELDS)} claim flags**. None has a dedicated hydration/electrolyte flag. The object also carries context/status, OCR quality, numeric claim values, nutrients/certification lists, `other_claims` and a selective phrase list. This is a prompt-defined JSON contract with Python validation, not a separately loaded formal JSON Schema. Unknown JSON keys alone would not enter the flattened/merged claim list.

The English and French context-review prompts return only `image_context` (no benefit extraction), have no separately persisted reviewer-version field, and are hashed here. They receive at most 2,000 OCR characters and 60 output tokens. Automatic review requires an initial legal-panel classification **and dairy category**; beverages do not receive this review. Extraction uses 800 output tokens, temperature 0, OCR text plus reference identity/context hints. The LLM receives no image. Code default deployment is `gpt-4.1-nano`; actual saved model/version distributions are in `ocr_diagnostics.csv`. No credentials/environment secrets were inspected.

Confirmed in actual [Stage 10](../../pipeline/stages/stage_10_extract_pack_claims.py): Azure Read receives only the image URL, independently of the benefit prompt. All returned line strings are joined and saved without a local 2,000-character slice. **The 2,000-character slice is applied to the LLM user message and context reviewer, not to stored `ocr_text`.** Full-text context hints and UK deterministic rescues can use text beyond that prefix, so a tail phrase was not necessarily invisible to every downstream rule. Result CSV/checkpoint saves `ocr_text`, statuses, prompt/model, `claims_json`, flags and phrases. Coordinates, word confidence, raw provider response and image pixels/hashes are not saved. UK full-size preference can try `.full.jpg` then the supplied URL, but the actual successful request URL is not separately persisted.

[Stage 11](../../pipeline/stages/stage_11_merge_vision_results.py) writes OCR/JSON and attempt metadata even for unsuccessful/non-front outcomes. `product_analysis` is a mutable latest-per-barcode store, not an observation history. Its OCR text is not truncated on write. Its image URL comes from `products`, not an original-image field in `product_analysis`. Important limitation: merged-result CSVs join the current database product URL after dropping the raw input URL; their `image_url` cannot automatically prove the original OCR image. Original request URL provenance is therefore credited only to raw `vision_results` records with identical OCR text.

Validation fills absent claim booleans with false, enforces context -> status, clears claims for non-front/unreadable observations, checks numeric ranges and reconciles unmapped/no-claim output. It uses Python truthiness for some non-boolean values; future extension tests must not assume a strict schema validator. The UK profile additionally uses approved product-name/brand/OCR rescues. `other_claims` and the at-most-five selected claim phrases are not substitutes for full raw OCR. Stage 12 maps raw flags into taxonomy and priority categories; adding a higher-priority benefit can change a displayed primary category while leaving old raw claims intact.

## Historical beverage evidence

{md_table(summaries, [('region','Region'),('all_scoped_beverage_products','All scoped'),('physically_valid_beverage_products','Corrected physical subset'),('products_with_any_saved_attempt_evidence','Any saved attempt'),('recognized_success_products','Successful'),('valid_no_claim_success_products','Valid no-claim'),('success_reusable_without_poor_quality_hold','Without poor-quality flag')])}

Successful rows have **zero missing/NULL, empty, placeholder or short/nonlinguistic OCR** in this audit. The [summary](beverage_01_v1/beverage_ocr_summary.csv) separates failed/unassessable attempts, absent/short text, poor-quality flags and unattempted products. No-claim observations remain successful. It also separates successes outside the corrected physical subset from genuine history differences inside it, reconciling the older `beverages_to_check.md` count without silently applying nutrition exclusions to OCR.

All attempted working-database observations, including failures:

{md_table(summaries, [('region','Region'),('DB_attempts_with_missing_NULL_text','Missing/NULL OCR'),('DB_attempts_with_empty_or_whitespace_text','Empty/whitespace OCR'),('DB_attempts_with_short_placeholder_or_nonlinguistic_text','Short/placeholder text'),('DB_attempts_with_OCR_status_not_success','OCR not successful'),('attempted_products_without_valid_success','No valid extraction')])}

These columns describe different states and may overlap; do not sum them as unique unusable products. A failed classification can still retain reusable OCR.

### Stored text lengths — preferred successful observations

{md_table(length_rows, [('region','Region'),('length_p05','P5 chars'),('length_median','Median'),('length_p95','P95'),('length_max','Max'),('length_over_2000_n','>2,000'),('length_over_2000_pct_of_substantive','% >2,000')])}

Length is exact Python character count of saved text, not tokens; P5/median/P95 use linear interpolation and nonempty substantive-text denominators. All text-state, quality, prompt/model and context distributions, plus database and deduplicated-file comparisons, are in [ocr_diagnostics.csv](beverage_01_v1/ocr_diagnostics.csv).

### Front/non-front evidence — distinct product/text observations

{md_table(context_rows, [('region','Region'),('product_texts','Distinct product/texts'),('valid_front','Valid front/mixed success'),('non_front','Non-front context'),('uncertain','Uncertain/not saved')])}

Context counts describe historical assessments, not new visual verification. Non-front or uncertain text can support discovery/review, but is not automatically a front-pack benefit. Complete context distributions include any status/context inconsistency, rather than silently fixing it.

### Saved files versus merged database

{md_table(summaries, [('region','Region'),('merged_database_success_products','DB success'),('saved_file_success_products','File success'),('success_in_both_database_and_files','Both'),('success_database_only','DB only'),('success_files_only','Files only'),('success_outside_corrected_RUN05_population','Outside RUN05 scope')])}

This reconciles coverage, not attempts. File/DB duplicates, normalized copies and checkpoint rows are not summed. No frozen RUN 05 history is modified. The public MVP database has only `barcode`, `pack_claims_found`, `claim_source` in `product_analysis`; it is not an OCR archive. The working database has {len(raw_db_rows):,} beverage/frame-related evidence rows before regional aggregation.

### Image and evidence provenance — successful products

{md_table(summaries, [('region','Region'),('success_with_same_text_original_request_URL','Original request URL'),('success_request_URL_equals_current_URL','URL exact match'),('success_same_revision_different_derivative','Same URL revision/other size'),('success_original_request_URL_unknown','Original URL unknown'),('old_structured_JSON_available','Old JSON available')])}

Historical pixel hashes/immutable image bytes and OCR engine/configuration versions are **not saved**. The summary quantifies original OFF URL language/revision tokens and saved prompt/model/timestamps. URL equality is not pixel verification; current URL differences are not proof of a changed pack. Hashes assigned to OCR now identify stored text, not an original image version. Current prompt hashes do not prove those bytes were used historically. Image-only graphics cannot be reconstructed from OCR. Original claims/JSON remain available as quantified above.

## Emerging wording discovery — saved OCR only

English/French deterministic patterns searched hydration/rehydration, hydratation/réhydratation, electrolyte/électrolyte, plus recovery/récupération, calm/détente, collagen/collagène/beauty, heart/cholesterol, joint/mobility, antioxidants and adaptogens. Mineral ingredient proxies were examined separately. A second exploratory pass extracts short action phrases beginning supports/helps/contributes/promotes/aide/contribue/favorise/soutient/renforce/améliore, without an approved-benefit whitelist. It can surface instructions or existing benefits as well as new candidates. No product-name, brand, nutrient value or ingredient metadata was searched as discovery evidence.

{md_table(hit_counts, [('family','Audit search family — NOT a taxonomy'),('FR','FR products'),('UK+IE','UK+IE products'),('US+CA','US+CA products')])}

These are **literal match counts across all stored text variants**, not validated claim prevalence. Families overlap and products can belong to several regions. Examples preserve exact matched substrings, character offsets and surrounding OCR (including spelling errors/newlines), plus source row/hash, old claims/context and prompt in [benefit_wording_evidence.csv](beverage_01_v1/benefit_wording_evidence.csv). Excerpts are bounded per region/family/interpretation/position bucket; the [counts table](beverage_01_v1/benefit_discovery_counts.csv) uses all matches. Automatic interpretation hints are review triage, not ground truth; ingredient and marketing text may be mixed.

{md_table(examples, [('barcode','Barcode'),('wording','Exact OCR line'),('meaning','Interpretation requiring review')])}

In particular, **electrolytes 'for taste' must not automatically become hydration**. A mineral in ingredients/nutrition is not a benefit proposition; 'cholesterol free' is an absence proposition, not proof of heart-health wording. Recovery/collagen/antioxidant wording can overlap existing protein, fortification or sleep categories. Hypothesized emerging territories therefore need explicit definitions before any label is approved. No joint/mobility hit means no match to these patterns, not proof of absence from all packs.

**Truncation check:** hydration/electrolyte match occurrences after/straddling character 2,000: {family_tail_counts}. Across all searched families plus open action phrases: {tail_counts}. The observed hydration/electrolyte results therefore must be interpreted from these actual position counts, not a presumed truncation problem. Long-tail cases are retained for the experiment even where no emerging wording is found. Most texts are short, but the future layer should process full saved text or documented overlapping chunks and retain exact spans.

## Options and implementation dependencies — design only

| | A — Extend main extraction | B — Independent emerging-benefit observations |
|---|---|---|
| Changes | New extraction keys/rules in EN/FR/UK prompts, validator/default/list handling, Stage 10 flattening, Stage 11 claim whitelist, Stage 12 taxonomy/priority, display mappings and downstream filters/tests | New separately versioned definition/extractor and append-only observation store linked to frozen OCR and base results; no rewriting old flags |
| Storage | Existing `claims_json` and pipe-separated claim TEXT can technically hold new keys/codes; SQL column additions are not inherently required, but consumers/contracts must be updated | Separate local JSONL/SQLite/Parquet store is a future implementation choice requiring approval; absent assessment remains unavailable, not false |
| Historical compatibility | Need same-evidence regression checks and backfill; replacing a mutable row can erase original evidence/classification | Base classifications stay immutable; each new benefit/definition/model version gets a new observation |
| Regression/maintenance | Every new benefit reopens a shared prompt and legacy flags; prefix limitation and panel behaviour also matter | Small independent additions; legacy benefit disappearance is structurally prevented, while new-benefit errors still need validation |
| Calls | LLM-only replay is possible for suitable saved OCR, but current main CLI always calls OCR first and has no saved-OCR-only mode; a replay path would need separate work | Deterministic discovery uses zero paid calls; any approved semantic pass calls only the new layer on suitable OCR. No OCR rerun merely to add a benefit |
| Upcoming 12,000 | Main-prompt changes would need validation before the core run | Keep approved main configuration, persist full new OCR; run any emerging-benefit layer separately after its own approval |

Relevant dependencies: {'; '.join(dependencies)}. Neither approach needs new images when suitable saved text exists. Missing/unreadable evidence or a verified need for a new image is a separate OCR decision. **Current checkpoint/resume is barcode-only and Stage 11 overwrites by barcode**; both require evidence-aware work before future paid execution regardless of which benefit approach is chosen.

Minimum future observation design: source barcode and exact regional links; image reference/provenance state and pixel hash when actually available; immutable full OCR and text hash; OCR status/capture/configuration provenance; base extraction reference; benefit-definition version; detector/prompt/model/config hashes; exact matched spans/chunk offsets; separate proposition/ingredient/taste/ambiguous/unassessable status; run/time and reviewer decision. This is a proposal, not a schema implemented by this audit. Never backfill an invented historical image hash or OCR-provider version.

## Proposed fixed validation experiment

The [fixed test set](beverage_01_v1/proposed_fixed_test_set.csv) contains **{len(tests)} unique-barcode cases**: {dict(tests_by_region)}. Frozen source rows/hashes, OCR hashes, old raw flags/codes/context, prompt/model, length and image provenance are recorded without exporting the full text. This is a proposed challenge set, **not** the 12,000-product RUN 06B sample and not authorization to execute a test. It includes {old_no_claim_n} valid historical no-claim cases overall. Human gold labels remain pending; deterministic candidate hints are not gold labels.

Requested roles per region: sugar-claim preservation 2, other functional 2, organic/multiple claims 1, likely hydration/electrolyte 2, ingredient/taste/ambiguous 2, valid no-claim 2, >2,000-character OCR 1. Observed coverage: {dict(test_roles)}. Unfilled cells: {json.dumps(missing_roles, ensure_ascii=False)}. Do not fabricate a long UK/US example or silently substitute a different role. Long successful OCR evidence: {json.dumps(long_cases, ensure_ascii=False)}. Geographic assignment is not OCR language; gold review must explicitly check French/English wording and add separately approved cases if a required negative/language condition is absent.

1. Freeze and human-adjudicate the exact stored OCR spans, proposition context and old-positive expectations. Distinguish zero/no-added sugar using the original phrases: both currently share `sugar_free_claim`, so raw flags alone cannot separate them.
2. **Recommended B trial:** run only the independent benefit task on full saved OCR; old classifications remain byte-identical. At most {len(tests)} LLM calls for one approved pass, zero OCR, before separately approved chunking/repeats. Start with deterministic review only if sufficient. This audit has made zero calls and does not quote a guaranteed price.
3. **If A is still considered:** pair unchanged-prompt control and extended-prompt candidate on the same original 2,000-character prefix and reference metadata/model; at most {2 * len(tests)} calls before separately approved repeats. Compare saved history -> control and control -> candidate separately to identify non-deterministic drift. A separate full-text/chunked arm tests tail recovery; do not mix longer input with the schema comparison.
4. Compare all 34 old raw claim flags, not just the single primary taxonomy label. Every unexplained old true -> false/NULL is a blocker for replacing the main extraction. A new hydration detection on old no-claim OCR can be a valid extension if supported; it does not retroactively invalidate the old taxonomy-relative outcome.
5. Review ingredient-only, taste-only and ambiguous matches as false-positive challenges. For B require zero legacy overwrites; for either approach, zero unexplained old-positive losses and no promotion of confirmed negatives without review. Report precision/recall on adjudicated cases with exact denominators; this small challenge set cannot establish population accuracy.

Detailed proposed criteria and call-approval boundaries are in [validation_criteria.csv](beverage_01_v1/validation_criteria.csv). Test cases, definitions/prompt, model/configuration, call budget and any paid pilot still require separate approval. No hydration/electrolyte taxonomy or prompt changes are authorized here.

## Outputs, limitations and stop

- [Beverage coverage, quality, reconciliation and provenance summary](beverage_01_v1/beverage_ocr_summary.csv)
- [Length/context/status/prompt/model diagnostics](beverage_01_v1/ocr_diagnostics.csv)
- [All 56 source artifacts and checksums](beverage_01_v1/source_inventory.csv)
- [Actual active prompt/schema inventory](beverage_01_v1/active_prompt_schema.csv)
- [Complete deterministic discovery counts](beverage_01_v1/benefit_discovery_counts.csv)
- [Compact exact wording and open-phrase evidence](beverage_01_v1/benefit_wording_evidence.csv)
- [Proposed fixed validation cases](beverage_01_v1/proposed_fixed_test_set.csv)
- [Validation design and acceptance criteria](beverage_01_v1/validation_criteria.csv)
- [Audit configuration, source/output hashes and validation](beverage_01_v1/beverage_01_manifest.json)
- [Standalone read-only audit script](../../pipeline/segmentation/beverage_01_ocr_evidence_audit.py)

Missing original images/provider geometry, mutable database history, absent initial raw CSVs, OCR errors and semantic ambiguity limit certainty. Search patterns are exploratory, not exhaustive; absence is not a negative claim. No files containing the full OCR corpus were exported for review. Existing prompts, schemas, processing scripts, databases, claims, RUN 05 and CHECK 06A were unchanged. **STOP for review; no prompt changes or paid tests.**
"""
    payloads = {
        OUT / "beverage_ocr_summary.csv": csv_bytes(summaries),
        OUT / "ocr_diagnostics.csv": csv_bytes(diagnostics),
        OUT / "source_inventory.csv": csv_bytes(inventory),
        OUT / "active_prompt_schema.csv": csv_bytes(profiles),
        OUT / "benefit_discovery_counts.csv": csv_bytes(discoveries),
        OUT / "benefit_wording_evidence.csv": csv_bytes(wording_pool),
        OUT / "proposed_fixed_test_set.csv": csv_bytes(tests),
        OUT / "validation_criteria.csv": csv_bytes(validation_rows()),
        REPORT: report.encode("utf-8"),
    }
    manifest = {
        "audit": "BEVERAGE_01_OCR_EVIDENCE_AND_BENEFITS_V1", "status": "Audit complete; pending review",
        "audit_date": "2026-10-23", "audit_script": rel(Path(__file__)), "audit_script_sha256": sha(Path(__file__)),
        "input_hashes_sha256": source_hashes,
        "scope": {"all_scoped_regional_beverage_products": all_scoped_assignments,
                  "regional_physical_beverage_products": 158258, "unique_frame_barcodes": len(frame),
                  "success_regional_assignments": success_assignments, "success_unique_barcodes": len(success_codes),
                  "quality_unheld_success_assignments": reusable_assignments, "quality_unheld_success_unique_barcodes": unique_reusable,
                  "source_artifacts": len(inventory), "source_evidence_rows_in_memory": len(evidence),
                  "outside_frame_historical_beverage_barcodes": len(outside_codes)},
        "rules": {"success": "llm_status=success AND extraction=completed; valid no-claim retained",
                  "text_quality": "substantive >=10 trimmed chars and >=3 letters; technical OCR status success; poor quality flag held for review only",
                  "preferred_success": "valid success; non-poor technical text; technical text; saved timestamp; DB/raw/merged artifact priority; stable source/row",
                  "discovery_unit": "(barcode, exact stored OCR hash), mapped to each frozen region; all contexts inspected",
                  "original_request_URL": "only raw vision_results; merged_result URLs are product joins, not trusted original image evidence",
                  "timestamp_limitation": "Naive/compact timestamps ordered as recorded with UTC surrogate; original timezone unverified",
                  "match_offsets": "Python characters, zero-based start / exclusive end, on original unsliced text",
                  "source_row": "CSV logical record ordinal with header=1; database query ordinal ordered by barcode; not physical text line number",
                  "database_query": "attempted/non-NULL OCR or LLM product_analysis joined to products, ORDER BY barcode; read-only immutable mode with empty WAL"},
        "audit_search_patterns": PATTERNS, "exploratory_action_pattern": ACTION.pattern,
        "test_set": {"cases": len(tests), "seed": "BEVERAGE01|20261023", "roles": dict(test_roles),
                     "regions": dict(tests_by_region), "unfilled_cells": missing_roles,
                     "human_gold_labels": "Pending", "paid_execution_authorized": False,
                     "not_RUN06B_sample": True},
        "output_sha256": {rel(path): text_sha(data.decode("utf-8")) for path, data in payloads.items()},
        "validation": {"source_hashes_verified_unchanged": len(source_hashes), "no_full_OCR_corpus_export": True,
                       "old_classifications_unchanged": True, "no_processing_script_changes": True,
                       "no_prompt_schema_taxonomy_changes": True, "service_calls": 0, "image_requests": 0},
    }
    payloads[OUT / "beverage_01_manifest.json"] = json_bytes(manifest)
    # Recheck all data/code sources after reads; no credentials or service clients.
    assert all(sha(ROOT / source) == digest for source, digest in source_hashes.items())
    for row in wording_pool:
        obs = next(o for o in evidence if o["source"] == row["source"] and o["source_row"] == row["source_row"])
        assert obs["text"][row["match_start_0based"]:row["match_end_exclusive"]] == row["match"]
        assert obs["text"][row["context_start_0based"]:row["context_start_0based"] + len(row["exact_context"])] == row["exact_context"]
    assert len({r["barcode"] for r in tests}) == len(tests)
    if verify_only:
        for path, data in payloads.items():
            assert path.read_bytes() == data, f"Audit reproducibility mismatch: {rel(path)}"
        print(json.dumps({"reproduced_files": len(payloads), "unchanged_source_hashes": len(source_hashes), "service_calls": 0}, indent=2))
    else:
        if replace_draft:
            old = json.loads((OUT / "beverage_01_manifest.json").read_text())
            assert old["status"] == "Audit complete; pending review"
            for name, digest in old["output_sha256"].items():
                assert sha(ROOT / name) == digest, name
        else:
            assert not OUT.exists() and not REPORT.exists(), "Audit version already exists; use --verify-only."
            OUT.mkdir()
        for path, data in payloads.items():
            path.write_bytes(data)
        print(json.dumps({"report": rel(REPORT), "summary": summaries, "wording_excerpt_rows": len(wording_pool),
                          "test_cases": len(tests), "test_gaps": missing_roles,
                          "tail_hydration_electrolyte_matches": family_tail_counts,
                          "tail_all_matches": tail_counts}, ensure_ascii=False, indent=2))
    return manifest


def inspect():
    frame = load_frame()
    evidence, products, inventory, outside = load_evidence(frame)
    print(json.dumps({"source_artifacts": len(inventory), "evidence_rows": len(evidence),
                      "scoped_barcodes_with_evidence": len(products), "outside_frame_evidence_rows": len(outside)}, indent=2))
    for region in REGIONS:
        codes = [code for code, regions in frame.items() if region in regions]
        successful = [max([o for o in products.get(code, []) if o["valid_success"]], key=preference)
                      for code in codes if any(o["valid_success"] for o in products.get(code, []))]
        found = defaultdict(list)
        for code in codes:
            texts = {}
            for o in products.get(code, []):
                if o["text_state"] == "substantive_saved_text":
                    texts[o["text_sha256"]] = max(o, texts.get(o["text_sha256"], o), key=preference)
            for o in texts.values():
                for h in find_wording(o):
                    found[h["family"]].append((o, h))
        print(json.dumps({"region": region, "frame": len(codes), "success": len(successful),
                          "reusable_success": sum(o["reuse_without_quality_hold"] for o in successful),
                          "no_claim_success": sum(o["claim_state"] == "no_claims" for o in successful),
                          "over2000_success": sum(len(o["text"]) > 2000 for o in successful),
                          "matches_distinct_products": {k: len({o['barcode'] for o, h in v}) for k, v in found.items()}}, indent=2))
        for family in ["hydration_wording", "electrolyte_wording", "recovery_wording", "heart_cholesterol_wording"]:
            for o, h in found[family][:3]:
                print(json.dumps({"barcode": o["barcode"], "family": family, "meaning": h["meaning"],
                                  "zone": h["zone"], "context": h["exact_context"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--replace-own-draft", action="store_true")
    args = parser.parse_args()
    if args.inspect:
        inspect()
    else:
        output_audit(args.verify_only, args.replace_own_draft)


if __name__ == "__main__":
    main()
