"""Create the approved derived claims-review layer from immutable saved exports."""
import copy
import csv
import hashlib
import json
import sqlite3
import argparse
from collections import Counter
from pathlib import Path

from pipeline.vision_ops.run_06b_runner import LegacyContract
from pipeline.vision_ops import emerging_benefits_v3 as v3

ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
OUT = SEG / "wave2_claims_reconciliation_v1"
SOURCE = SEG / "wave2_combined_ocr_llm_review_v1/all_processed_products.csv"
IGNORE = {"claim_extraction_status", "status_normalised", "raw_image_context",
          "raw_claim_extraction_status", "core_consistency_status", "numeric_out_of_range", "unmapped_pack_text"}
CONFIG = SEG / "run_06b_main_readiness_v1/runtime_configuration.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def obj(text):
    if not text:
        return {}
    value = json.loads(text)
    return value if isinstance(value, dict) else {}


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def pattern(row, raw, normalized):
    differences = sorted(k for k in raw.keys() & normalized.keys() if k not in IGNORE and raw[k] != normalized[k])
    if row["overall_outcome"] == "HOLD" and normalized.get("claim_extraction_status") == "completed" and "CORE_STATUS_CONFLICT" in row["issue_codes"]:
        group = "STATUS_ONLY" if not differences else "STATUS_NO_CLAIMS" if differences == ["no_claims_detected"] else "CONTENT_DIFFERENCE"
    else:
        group = "EXISTING_ASSESSMENT"
    return group, differences


def main():
    csv.field_size_limit(100_000_000)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the derived review version before approval")
    args = parser.parse_args()
    if not args.rebuild and ((OUT / "reconciled_review.csv").exists() or (OUT / "validation.json").exists()):
        raise FileExistsError("Versioned reconciliation already exists")
    evidence_path = SEG / "run_06b_completion_quality_v1/product_evidence.jsonl"
    manifest_path = SEG / "run_06b_final_candidates_v1/proposed_primary_processing_manifest.csv"
    dairy_path = SEG / "wave2_dairy_completion_quality_v1/products.csv"
    ledger_path = SEG / "run_06b_execution_staging_v1/staging.sqlite"
    ledger_before = sha(ledger_path)
    inputs = [SOURCE, CONFIG, evidence_path, manifest_path, dairy_path,
              ROOT / "pipeline/stages/stage_10_extract_pack_claims.py",
              ROOT / "pipeline/vision_ops/emerging_benefits_v3.py"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    rows = load_rows(SOURCE)
    manifests = {r["proposed_primary_slot_id"]: r for r in load_rows(manifest_path)}
    dairy = {r["barcode"]: r for r in load_rows(dairy_path)}
    with evidence_path.open(encoding="utf8") as stream:
        evidence = {}
        for line in stream:
            e = json.loads(line)
            row = manifests[e["slot"]]
            evidence[(row["barcode"], row["region"].replace("+", "-"), row["category"].replace("dairies", "dairy").replace("cereals", "cereal"))] = (e, row)
    contract = LegacyContract(json.loads(CONFIG.read_text(encoding="utf8")))
    module = contract.module
    flags = [f for f in module.BOOL_CLAIM_FIELDS if f != "no_claims_detected"]
    outputs = []
    counts = Counter()
    v6_counts = Counter()
    for row in rows:
        raw, norm = obj(row["core_raw_output_json"]), obj(row["core_normalized_output_json"])
        group, diffs = pattern(row, raw, norm)
        counts[group] += 1
        key = (row["barcode"], row["region"], row["category"])
        entry = evidence.get(key)
        brand = manifests[entry[0]["slot"]]["brands"] if entry else dairy[row["barcode"]]["brand"]
        replay = {}
        replay_ok = False
        if raw.get("image_context") in module.VALID_IMAGE_CONTEXTS:
            replay = module.validate_and_normalise(copy.deepcopy(raw))
            if row["region"] == "UK-IE":
                replay = module.apply_uk_claim_rescue_rules(replay, ocr_text=row["ocr_text_full"],
                                                          product_name=row["product_name"], brand=brand)
            compare_keys = set(replay) | (set(norm) - {"raw_image_context", "raw_claim_extraction_status", "core_consistency_status"})
            replay_ok = all(replay.get(k) == norm.get(k) for k in compare_keys)
        notes = []
        operational = "UNRESOLVED"
        if row["overall_outcome"] == "OTHER":
            operational = "TECHNICAL_OR_MISSING_OUTPUT"
        elif norm.get("claim_extraction_status") == "completed":
            operational = "COMPLETED_REPRODUCED" if replay_ok else "COMPLETED_REPLAY_REVIEW"
            if group != "EXISTING_ASSESSMENT":
                notes.append(group)
        elif norm.get("claim_extraction_status") == "not_applicable_non_front":
            operational = "NON_FRONT_ASSESSMENT"
        elif norm.get("claim_extraction_status") == "unreadable":
            operational = "UNREADABLE_OR_UNCERTAIN"
        positive = {f: {"raw": raw.get(f), "normalized": norm.get(f),
                        "provenance": "RAW_LLM_ASSERTION" if raw.get(f) is True else "EXISTING_RULE_DERIVATION",
                        "usability": "SUBSTANTIVE_EVIDENCE_REVIEW"}
                    for f in flags if raw.get(f) is True or norm.get(f) is True}
        if row["barcode"] == "5060120283061":
            assert raw.get("organic_claim") is False and norm.get("organic_claim") is False
            notes.append("JULIA_ORGANIC_VARIANT_FALSE_CONFIRMED")
        full_negative = (bool(raw) and raw.get("claim_extraction_status") == "completed"
                         and raw.get("image_context") == "front_of_pack" and raw.get("ocr_quality") == "good"
                         and raw.get("no_claims_detected") is True
                         and all(f in raw and raw[f] is False for f in flags)
                         and not raw.get("other_claims") and not raw.get("detected_claim_phrases")
                         and replay_ok and not positive)
        absence = "RAW_EXPLICIT_TAXONOMY_NEGATIVE_REVIEWABLE" if full_negative else "UNVERIFIED_OR_NOT_ASSESSED"
        if norm.get("no_claims_detected") is True and not full_negative:
            notes.append("NORMALIZED_NO_CLAIMS_DOES_NOT_VERIFY_ABSENCE")
        if raw.get("no_claims_detected") != norm.get("no_claims_detected") or ("no_claims_detected" not in raw and "no_claims_detected" in norm):
            notes.append("NO_CLAIMS_VALUE_CHANGE" if "no_claims_detected" in raw else "NO_CLAIMS_FIELD_COMPLETION")
        excluded = row["barcode"] == "00976534"
        if excluded:
            operational = "EXCLUDED_IDENTITY"
            notes.append("JULIA_SELECTED_IMAGE_IS_VEGAN_FOUR_PEPPER_SALAMI")
            absence = "NOT_USABLE_IDENTITY_EXCLUDED"
            for value in positive.values():
                value["usability"] = "NOT_USABLE_IDENTITY_EXCLUDED"
        v6_disposition = "NOT_APPLICABLE" if row["category"] != "beverages" else "UNRESOLVED"
        derived_v6 = {}
        v6_reason = ""
        if entry and row["category"] == "beverages":
            e, m = entry
            if e["row_assessment"].get("classification_accepted"):
                v6_disposition = "SAVED_ACCEPTED_PRESERVE_UNCERTAINTY"
                derived_v6 = e["accepted_v6"]
            else:
                v6_reason = e["row_assessment"].get("reason", "")
                if "V6_REQUEST_ID" in row["issue_codes"]:
                    work_key = e["source_keys"]["v6"]
                    events = e["stage_events"].get(work_key, {})
                    event_id = events.get("dispatch", {}).get("id")
                    dispatch = {}
                    reply = {}
                    # Exact primary-key lookup into the immutable original ledger.
                    with sqlite3.connect(ledger_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                        saved = db.execute("SELECT key,event,payload FROM stage_events WHERE id=?", (event_id,)).fetchone()
                        saved_reply = db.execute("SELECT key,event,payload FROM stage_events WHERE id=?",
                                                 (events.get("provider_result", {}).get("id"),)).fetchone()
                    if saved and saved[0] == work_key and saved[1] == "dispatch":
                        dispatch = json.loads(saved[2])
                    if saved_reply and saved_reply[0] == work_key and saved_reply[1] == "provider_result":
                        reply = json.loads(saved_reply[2])
                    original = e["raw_v6"]
                    inp = v3.build_input(barcode=m["barcode"], product_name=m["product_name"],
                        regions=[m["region"]], country_assignments=m["countries"].split("|"),
                        ocr_text=e["ocr_text"], source_reference="staging:ocr:" + e["source_keys"]["ocr"],
                        source_artifact_sha256=hashlib.sha256(e["ocr_text"].encode()).hexdigest(),
                        original_image_url=m["original_image_url"],
                        image_provenance_note="Frozen source URL; OCR submitted frozen bytes, no runtime URL identity inferred.",
                        prior_panel_context=None, prior_profile=m["proposed_regional_profile"], request_id=work_key)
                    body = dispatch.get("body", {})
                    body_inputs = [obj(message.get("content", "")) for message in body.get("messages", []) if message.get("role") == "user"]
                    linked = (dispatch.get("row") == m and reply.get("output") == original
                              and bool(reply.get("provider_request_id"))
                              and reply.get("raw", {}).get("status_code") == 200
                              and body_inputs == [v3.model_input(inp)])
                    if linked:
                        repaired = copy.deepcopy(original)
                        repaired["request_id"] = work_key
                        try:
                            derived_v6, _ = v3.validate_saved_ocr_result(inp, repaired)
                            v6_disposition = "REQUEST_ECHO_RECONCILED"
                            v6_reason = "Only request_id changed after exact dispatch/body/response binding and complete v3 validation"
                        except ValueError as exc:
                            v6_reason = str(exc)
                    else:
                        v6_reason = "Saved dispatch/body/response linkage did not meet the exact recovery conditions"
        if excluded:
            v6_disposition = "NOT_USABLE_IDENTITY_EXCLUDED"
            derived_v6 = {}
        v6_counts[v6_disposition] += 1
        if operational.endswith("REVIEW") or positive or absence == "UNVERIFIED_OR_NOT_ASSESSED":
            notes.append("CLAIM_USABILITY_REVIEW_REMAINS")
        outputs.append(dict(row, reconciliation_pattern=group, content_changed_fields="|".join(diffs),
            normalization_reproduced=str(replay_ok).lower(), operational_disposition=operational,
            positive_claim_usability="NOT_USABLE_IDENTITY_EXCLUDED" if excluded else "SUBSTANTIVE_EVIDENCE_REVIEW" if positive else "NO_POSITIVE_ASSERTED",
            positive_claim_review_json=dump(positive), absence_assessment_usability=absence,
            v6_disposition=v6_disposition, v6_reconciled_output_json=dump(derived_v6) if derived_v6 else "",
            v6_reconciliation_reason=v6_reason, segmentation_eligibility="EXCLUDED_EXACT_BARCODE" if excluded else "PENDING_FINAL_QA",
            reconciliation_reasons="|".join(notes)))
    assert len(outputs) == 12126
    assert {k: counts[k] for k in ["STATUS_ONLY", "STATUS_NO_CLAIMS", "CONTENT_DIFFERENCE"]} == {"STATUS_ONLY": 2100, "STATUS_NO_CLAIMS": 663, "CONTENT_DIFFERENCE": 29}
    assert Counter(r["overall_outcome"] for r in outputs) == {"PASS": 8594, "HOLD": 3411, "OTHER": 121}
    assert sum(r["segmentation_eligibility"] == "EXCLUDED_EXACT_BARCODE" for r in outputs) == 2
    for source, output in zip(rows, outputs):
        assert all(output[k] == value for k, value in source.items())
    assert all(sha(ROOT / name) == value for name, value in before.items())
    assert sha(ledger_path) == ledger_before
    OUT.mkdir(exist_ok=True)
    path = OUT / "reconciled_review.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(outputs[0]))
        writer.writeheader()
        writer.writerows(outputs)
    assert load_rows(path) == outputs
    validation = dict(records=len(outputs), source_sha256=before, pattern_counts=dict(counts),
        operational_dispositions=dict(Counter(r["operational_disposition"] for r in outputs)),
        positive_usability=dict(Counter(r["positive_claim_usability"] for r in outputs)),
        absence_usability=dict(Counter(r["absence_assessment_usability"] for r in outputs)),
        v6_dispositions=dict(v6_counts), all_original_fields_preserved=True, csv_round_trip_exact=True,
        source_hashes_unchanged=True, csv_sha256=sha(path), readonly_ledger_sha256=ledger_before,
        human_decisions={"5060120283061": "organic_claim=false retained; no general rule changed",
                         "00976534": "derived-only exclusion in FR and UK-IE; exact-barcode rule applies to any future assignment"},
        authorizing_user_request="Create derived review dataset and apply bounded rules; document and update handoffs. IMPLEMENT.")
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf8")
    print(json.dumps(validation, ensure_ascii=False))


if __name__ == "__main__":
    main()

