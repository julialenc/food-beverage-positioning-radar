"""One-pass current-wave beverage eligibility and saved-OCR materialization.

Source databases, RUN 06B v2 manifests, legacy claims and old RUN 03 matrices
are read-only. Outputs are versioned sidecars. Re-running a completed, verified
version is a no-op; a partial version is a hard stop for investigation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from shared.beverage_eligibility import RULE_VERSION, explicit_non_beverage_rule
from pipeline.vision_ops.detect_emerging_benefits_offline import METHOD_VERSION, assess, self_test

ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
OUT = SEG / "beverage_final_v1"
DB = ROOT / "database/positioning_radar.db"
FRAME = SEG / "run_05_v1/candidate_ledger.csv"
FROZEN = {
    "presentations/segmentation/beverage_05b_decision_register.csv": "c47bb949f24b5748e3c90c078dc3d68bbebad7dfd6a288d108962c33283083c5",
    "presentations/segmentation/beverage_05c_coconut_decisions_human_reviewed.csv": "9dd5a092c13fa47e1c5dcd474f55c104797ce65523be0f2968f9c5f5ae8a662e",
    "presentations/segmentation/beverage_05d_identity_decisions.csv": "62e3278f69b54ecbec49b90a43222b48c39c2ecb617d34abea30e0ec6542b8ef",
    "presentations/segmentation/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json": "09325d40f432e7607b3f0cd123af1353c3297cbfb03591f358392fc4b2d3b90d",
    "presentations/segmentation/beverage_03_approved_v1/frozen_human_reviewed_labels.csv": "386b1378c10c0799bde5780526d35d348d17df79278c1550d3807a3e4645a242",
    "presentations/segmentation/beverage_03_approved_v1/wording_evidence.csv": "b9aec88a97fb0b6f6ebe4d95e935d6f85ec822b0b8e251e8e3c799c322247fbd",
    "pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v1.txt": "f80bab0bb07aa9f80ab46d08141621c21ba317c5832a9e11fd09339c0c6d9662",
    "pipeline/vision_prompts/emerging_benefits/emerging_benefits_input_v1.schema.json": "8155aaa43f64885e764c58c9e9abf85199c0f86cdd5e078103d6785526893e25",
    "pipeline/vision_prompts/emerging_benefits/emerging_benefits_output_v1.schema.json": "42cdfeb86ea32d93aa63dd45bac95e7a96f00f2a57abe71408604f882f4ff4c9",
    "presentations/segmentation/run_06b_v2/selected_manifest.csv": "ce98cbb88120543819756459c253d56d69bc71abd3deb5271ce24e1eddcacdbb",
    "presentations/segmentation/run_06b_v2/reserve_manifest.csv": "753ce5b29e599e50e37c4f4a0a522d37a9c81cc3015312839f5c3ff67b6a6d89",
}
REGIONS = {"FR", "UK+IE", "US+CA"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def source_decisions() -> dict[tuple[str, str], dict[str, str]]:
    b = read(SEG / "beverage_05b_decision_register.csv")
    c = {(r["barcode"], r["region"]): r for r in read(SEG / "beverage_05c_coconut_decisions_human_reviewed.csv")}
    d = {(r["barcode_exact_text"], r["region"]): r for r in read(SEG / "beverage_05d_identity_decisions.csv")}
    assert len(b) == 121 and len(c) == 47 and len(d) == 15
    result = {}
    for row in b:
        key = (row["barcode"], row["region"])
        assert key not in result
        if key in c:
            x = c[key]
            final = x["final_classification"].upper()
            authority = x["decision_authority"]
            reason = x["decision_reason"]
            evidence = x["supporting_reason"]
            review_note = x["human_review_note_original"]
            source = "BEVERAGE_05C_HUMAN_REGISTER"
        elif key in d:
            x = d[key]
            final = x["proposed_disposition"].split(" ")[0].upper()
            authority = "Codex evidence proposal; consolidated implementation authorized by Julia"
            reason = x["image_and_source_finding"]
            evidence = x["limitations"]
            review_note = ""
            source = "BEVERAGE_05D_TECHNICAL_REGISTER"
        else:
            final = row["proposed_disposition"].split(" ")[0].upper()
            authority = "Codex evidence proposal; consolidated implementation authorized by Julia"
            reason = row["disposition_rationale"]
            evidence = row["evidence"]
            review_note = ""
            source = "BEVERAGE_05B_REGISTER"
        assert final in {"EXCLUDE", "RETAIN", "HOLD"}
        result[key] = dict(barcode=key[0], region=key[1], category="beverages",
                           status={"EXCLUDE": "excluded", "RETAIN": "eligible", "HOLD": "hold"}[final],
                           reason=reason, evidence=evidence, decision_source=source,
                           decision_authority=authority, human_review_note=review_note,
                           reviewed_case="1", rule_version=RULE_VERSION)
    assert Counter(x["status"] for x in result.values()) == {"excluded": 45, "eligible": 3, "hold": 73}
    return result


def timestamp(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def observation(row: dict, source: str, source_kind: str):
    text = row.get("ocr_text") or ""
    if len(text.strip()) < 10 or (row.get("ocr_status") or "").lower() != "success":
        return None
    claims = row.get("claims_json") or ""
    try:
        extracted = json.loads(claims).get("claim_extraction_status", "")
    except (ValueError, TypeError, AttributeError):
        extracted = ""
    extraction = row.get("v3_claim_extraction_status") or row.get("claim_extraction_status") or extracted
    valid_core = (row.get("llm_status") or "").lower() == "success" and extraction == "completed"
    return dict(barcode=row["barcode"], text=text,
                ocr_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                source=source, source_kind=source_kind, valid_core=valid_core,
                no_claim_success=valid_core and not (row.get("pack_claims_found") or "").strip(),
                prior_context=row.get("v3_image_context") or row.get("image_context") or "",
                image_url=row.get("image_url") or row.get("current_product_image_url") or "",
                timestamp=timestamp(row.get("pack_analysis_timestamp") or ""))


def load_ocr(frame_codes: set[str]):
    evidence = defaultdict(list)
    sources = []
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    for row in con.execute("""SELECT a.barcode,a.ocr_text,a.ocr_status,a.llm_status,a.claim_extraction_status,
                          a.claims_json,a.pack_claims_found,a.image_context,a.pack_analysis_timestamp,
                          p.image_url AS current_product_image_url
                          FROM products p JOIN product_analysis a ON a.barcode=p.barcode
                          WHERE p.query_category='beverages' AND a.ocr_text IS NOT NULL"""):
        if row["barcode"] in frame_codes:
            item = observation(dict(row), "database/positioning_radar.db::product_analysis", "merged_database")
            if item:
                evidence[item["barcode"]].append(item)
    con.close()
    sources.append("database/positioning_radar.db::product_analysis")
    for path in sorted((ROOT / "data/05_vision_release").glob("*.csv")):
        if not path.name.startswith(("vision_results", "merged_results")):
            continue
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if "ocr_text" not in (reader.fieldnames or []):
                continue
            used = False
            for row in reader:
                if row.get("barcode") not in frame_codes:
                    continue
                item = observation(row, path.relative_to(ROOT).as_posix(), "saved_csv")
                if item:
                    evidence[item["barcode"]].append(item)
                    used = True
            if used:
                sources.append(path.relative_to(ROOT).as_posix())
    return evidence, sources


def preferred(items: list[dict], gold_hash: str = "") -> dict:
    matching_gold = [x for x in items if gold_hash and x["ocr_sha256"] == gold_hash]
    pool = matching_gold or items
    return max(pool, key=lambda x: (x["valid_core"], x["source_kind"] == "merged_database",
                                    x["timestamp"], x["source"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args()
    self_test()
    assert explicit_non_beverage_rule("Olive oil", "Edible oils") == "explicit_edible_oil"
    assert explicit_non_beverage_rule("Chocolate drink powder", "Chocolate bars") is None
    if args.fixture_only:
        print("Offline fixtures and narrow category-rule checks passed")
        return
    for name, expected in FROZEN.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    manifest_path = OUT / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if all(sha(ROOT / p) == h for p, h in old["output_sha256"].items()):
            print("Completed version already verified; no-op")
            return
        raise ValueError("Existing beverage final output differs; refusing rewrite")
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError("Partial output directory exists; inspect before resume")
    reviewed = source_decisions()
    gold = {r["barcode"]: r for r in read(SEG / "beverage_03_approved_v1/frozen_human_reviewed_labels.csv")}
    wording = defaultdict(list)
    for row in read(SEG / "beverage_03_approved_v1/wording_evidence.csv"):
        wording[(row["barcode"], row["wording_family_NOT_legacy_taxonomy"])].append(row)
    db = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    metadata = {r[0]: (r[1] or "", r[2] or "") for r in db.execute(
        "SELECT barcode,product_name,off_categories FROM products WHERE query_category='beverages'")}
    db.close()
    frame = {}
    with FRAME.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["category"] != "beverages":
                continue
            key = (row["barcode"], row["region"])
            if key in frame:
                raise ValueError(f"Duplicate regional candidate: {key}")
            frame[key] = row
    if len(frame) != 158258 or not set(reviewed).issubset(frame):
        raise ValueError("Frozen candidate population or reviewed-case join mismatch")
    decisions = dict(reviewed)
    for (barcode, region), row in frame.items():
        if (barcode, region) in decisions:
            continue
        name, categories = metadata.get(barcode, (row["product_name"], ""))
        rule = explicit_non_beverage_rule(name, categories)
        if rule:
            decisions[(barcode, region)] = dict(barcode=barcode, region=region, category="beverages",
                status="excluded", reason=f"Explicit product name and category corroborate {rule}",
                evidence=f"name={name}; OFF categories={categories}", decision_source=f"rule:{rule}",
                decision_authority="Conservative current-wave analytical rule; Julia authorized policy",
                human_review_note="", reviewed_case="0", rule_version=RULE_VERSION)
    states = {key: decisions[key]["status"] if key in decisions else "eligible" for key in frame}
    # Eligibility is keyed by exact (barcode, region). The same barcode may
    # legitimately have a different decision in another analytical region.
    ocr, ocr_sources = load_ocr({barcode for barcode, _ in frame})
    observations, overlay = [], {}
    for (barcode, region), row in sorted(frame.items()):
        if states[(barcode, region)] != "eligible" or barcode not in ocr:
            continue
        item = preferred(ocr[barcode], gold.get(barcode, {}).get("source_OCR_sha256", ""))
        for family in ("hydration", "electrolyte"):
            assessed = assess(item["text"], item["prior_context"], family)
            human = gold.get(barcode)
            authority = "deterministic_saved_ocr"
            if human:
                status = human[f"{family}_positioning_front"]
                if status == "not_detected":
                    assessed.update(status="not_detected", content_status="not_detected", phrase="",
                                    start=None, end=None, evidence_scope="approved_human_front_review",
                                    reason=human["approved_rationale"])
                else:
                    hits = wording.get((barcode, family), [])
                    supporting = next((h for h in hits if h["wording_attribution_and_scope"] == "target_product_front_positioning"), None)
                    if supporting and supporting["exact_saved_OCR_wording"] in item["text"]:
                        phrase = supporting["exact_saved_OCR_wording"]
                        start = item["text"].find(phrase)
                        assessed.update(status=status, content_status=status, phrase=phrase,
                                        start=start, end=start + len(phrase), evidence_scope="approved_human_front_review",
                                        reason=human["approved_rationale"])
                    else:
                        assessed.update(status=status, content_status=status, phrase="", start=None, end=None,
                                        evidence_scope="approved_human_front_review_OCR_wording_unavailable",
                                        reason=human["approved_rationale"])
                authority = "Julia_ChatGPT_human_review_not_Codex_image_review"
            observations.append(dict(barcode=barcode, region=region, category="beverages", proposition=family,
                front_status=assessed["status"], content_status=assessed["content_status"],
                exact_ocr_phrase=assessed["phrase"], phrase_start_0based=assessed["start"],
                phrase_end_exclusive=assessed["end"], evidence_scope=assessed["evidence_scope"],
                purpose=assessed["purpose"], rationale=assessed["reason"],
                detection_method="human_reviewed_exception_v1" if human else METHOD_VERSION,
                review_status="approved_human" if human else "unreviewed_deterministic",
                review_authority=authority, source_ocr_sha256=item["ocr_sha256"],
                source_ocr_reference=item["source"], original_image_url=row["image_url"],
                prior_panel_context=item["prior_context"], historical_core_success=int(item["valid_core"]),
                historical_no_claim_success=int(item["no_claim_success"]),
                definition_version="1.0.0", rule_version=METHOD_VERSION))
    per_code = defaultdict(dict)
    for obs in observations:
        if obs["front_status"] == "detected":
            per_code[obs["barcode"]][obs["proposition"]] = obs
    for barcode, families in sorted(per_code.items()):
        h, e = families.get("hydration"), families.get("electrolyte")
        overlay[barcode] = dict(barcode=barcode,
            hydration_positioning="detected" if h else "", electrolyte_positioning="detected" if e else "",
            display_group="Hydration / Electrolytes", hydration_wording=h["exact_ocr_phrase"] if h else "",
            electrolyte_wording=e["exact_ocr_phrase"] if e else "",
            evidence_scope="approved_human_front_review" if any(x and x["review_status"] == "approved_human" for x in (h,e)) else "ocr_supported_front_context")
    impact = []
    for role, path in (("selected", SEG / "run_06b_v2/selected_manifest.csv"),
                       ("reserve", SEG / "run_06b_v2/reserve_manifest.csv")):
        for row in read(path):
            if row["category"] != "beverages":
                continue
            key = (row["barcode"], row["region"])
            status = states.get(key)
            if status is None:
                raise ValueError(f"RUN 06B key absent from frozen candidate frame: {key}")
            decision = decisions.get(key, {})
            impact.append(dict(barcode=key[0], region=key[1], role=role,
                sampling_group_id=row["sampling_group_id"], country_cell=row["country_cell"],
                sampling_component=row["accounting_component"], eligibility=status,
                reason=decision.get("reason", ""), decision_source=decision.get("decision_source", ""),
                manifest_sha256=sha(path)))
    assert len(impact) == 3563 + 593
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "eligibility_decisions.csv", sorted(decisions.values(), key=lambda r:(r["region"],r["barcode"])),
          ["barcode","region","category","status","reason","evidence","decision_source","decision_authority",
           "human_review_note","reviewed_case","rule_version"])
    write(OUT / "segmentation_beverage_eligible_keys.csv",
          [dict(barcode=b, region=r, category="beverages") for b,r in sorted(frame) if states[(b,r)] == "eligible"],
          ["barcode","region","category"])
    write(OUT / "benefit_observations.csv", observations, list(observations[0]) if observations else
          ["barcode","region","proposition","front_status"])
    write(OUT / "benefit_app_overlay.csv", list(overlay.values()),
          ["barcode","hydration_positioning","electrolyte_positioning","display_group",
           "hydration_wording","electrolyte_wording","evidence_scope"])
    write(OUT / "run_06b_eligibility_impact.csv", impact,
          ["barcode","region","role","sampling_group_id","country_cell","sampling_component",
           "eligibility","reason","decision_source","manifest_sha256"])
    counts = dict(population=len(frame), reviewed=Counter(x["status"] for x in reviewed.values()),
        full=Counter(states.values()), observed_product_regions=len(observations)//2,
        source_ocr_barcodes=len(ocr), source_ocr_files=ocr_sources,
        hydration_detected=sum(o["front_status"] == "detected" and o["proposition"] == "hydration" for o in observations),
        electrolyte_detected=sum(o["front_status"] == "detected" and o["proposition"] == "electrolyte" for o in observations),
        overlap=sum(len(x) == 2 for x in per_code.values()),
        impact={role: dict(Counter(x["eligibility"] for x in impact if x["role"] == role)) for role in ("selected","reserve")})
    output_hashes = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.glob("*.csv"))}
    manifest = dict(version=RULE_VERSION, definition_version="1.0.0", method_version=METHOD_VERSION,
        frozen_input_sha256=FROZEN, source_frame_sha256=sha(FRAME),
        output_sha256=output_hashes, counts=counts, source_db=DB.relative_to(ROOT).as_posix(),
        source_db_preserved=True, no_paid_calls=True, run_06b_v2_preserved=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
