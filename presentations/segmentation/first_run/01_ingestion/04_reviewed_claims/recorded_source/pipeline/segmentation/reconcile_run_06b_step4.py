"""RUN 06B Step 4: human decisions, attribution, proposed ownership and history.

Uses frozen manifests/ledgers and exact-barcode indexed metadata lookups only.
No image opens, sampling, provider calls, history changes or reserve promotion.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/segmentation"
OUT = BASE / "run_06b_step4_v1"
WORKBOOK = Path(r"C:\Users\julia\OneDrive\Desktop\Downloads_temp\RUN_06B_Step3_Julia_review_clarified_for_Step4.xlsx")
BRIEF = Path(r"C:\Users\julia\.codex\attachments\61a56fd3-40e4-4193-8e20-441e6b882f4c\Pasted text.txt")
DATABASE = ROOT / "data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/release_work.db"
INPUTS = [
    "run_06b_step2_v1/manifest.json", "run_06b_step2_v1/candidate_selected_manifest.csv",
    "run_06b_step2_v1/eligibility_reconciled_reserves.csv", "run_06b_step2_v1/secondary_coverage_links_frozen.csv",
    "run_06b_step2_v1/secondary_link_step2_annotations.csv", "run_06b_step2_v1/vacancies.csv",
    "run_06b_step2_v1/approved_group_quotas_frozen.csv", "run_06b_step2_v1/approved_country_component_plan_frozen.csv",
    "run_06b_step3_v1/manifest.json", "run_06b_step3_v1/image_usability_decisions.csv",
    "run_06b_step3_v1/image_evidence_assessment.csv", "run_06b_step3_v1/duplicate_evidence_exceptions.csv",
    "run_06b_v2/run_06b_manifest.json", "run_06b_v2/selected_manifest.csv", "run_06b_v2/selected_draw.csv",
    "run_06b_v2/reserve_audit.csv", "run_06b_v2/image_preflight_products.csv",
    "run_06b_v2/core_configuration_proposal.json", "run_06b_v2/history_observations_refreshed.csv",
    "run_06b_v2/history_status_refreshed.csv", "run_06b_v2/history_source_inventory_refreshed.csv",
    "run_06b_v2/historical_image_reference_overlap.csv", "beverage_final_v1/eligibility_decisions.csv",
]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HOLD = "PRE-EXECUTION HOLD"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def csv_data(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    return list(reader.fieldnames or []), list(reader)


def write_csv(name, rows, fields=None):
    fields = fields or list(rows[0])
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def identity(r):
    return r["barcode"], r["region"], r["category"]


def exact(r):
    return r["role"], *identity(r), r["image_sha256"]


def family(url):
    match = re.search(r"(https?://[^/]+/images/products/[0-9/]+/front_[a-z_]+\.\d+)\.(?:\d+|full)\.", url or "")
    return match.group(1) if match else ""


def workbook_cells(blob):
    """Read original OOXML values/types; never coerce GTIN through a float."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        sheets = ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS)
        assert len(sheets) == 1
        result = []
        for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall("s:sheetData/s:row", NS):
            cells = {}
            for c in row.findall("s:c", NS):
                node = c.find("s:v", NS)
                raw = node.text if node is not None else ""
                kind = c.get("t", "n")
                value = strings[int(raw)] if kind == "s" else raw
                if kind == "inlineStr":
                    value = "".join(c.find("s:is", NS).itertext())
                cells[re.sub(r"\d", "", c.get("r"))] = dict(cell=c.get("r"), type=kind, raw=raw, value=value or "")
            result.append(dict(row=int(row.get("r")), cells=cells))
        return sheets[0].get("name"), result


def main():
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite a versioned Step 4 package: {OUT}")
    blobs = {p: (BASE / p).read_bytes() for p in INPUTS}
    hashes = {p: sha(v) for p, v in blobs.items()}
    wb, brief = WORKBOOK.read_bytes(), BRIEF.read_bytes()
    tables = {p: csv_data(v)[1] for p, v in blobs.items() if p.endswith(".csv")}
    checks = {}

    def require(name, result):
        checks[name] = "PASS" if result else "FAIL"
        if not result:
            raise ValueError(f"STOP Step 4: {name}")

    for package, manifest_name in [("run_06b_step2_v1", "manifest.json"), ("run_06b_step3_v1", "manifest.json"),
                                    ("run_06b_v2", "run_06b_manifest.json")]:
        manifest = json.loads(blobs[package + "/" + manifest_name])
        for name, expected in manifest["outputs_sha256"].items():
            rel = name.removeprefix("presentations/segmentation/") if package == "run_06b_v2" else package + "/" + name
            if rel in hashes:
                require("input_hash_" + rel, hashes[rel] == expected)
    sf, original_selected = csv_data(blobs["run_06b_step2_v1/candidate_selected_manifest.csv"])
    rf, original_reserves = csv_data(blobs["run_06b_step2_v1/eligibility_reconciled_reserves.csv"])
    rows = []
    for role, originals in [("selected", original_selected), ("reserve", original_reserves)]:
        for i, r in enumerate(originals, 1):
            rows.append({**r, "role": role, "source_sequence": i})
    row_map = {exact(r): r for r in rows}
    reviews = tables["run_06b_step3_v1/image_usability_decisions.csv"]
    review_index = {(r["barcode"], r["role"], r["requested_url"]): r for r in reviews}
    sheet, cell_rows = workbook_cells(wb)
    require("workbook_expected_headers", cell_rows[0]["cells"]["G"]["value"] == "Exact frozen GTIN (text)"
            and cell_rows[0]["cells"]["I"]["value"] == "STEP 4 clarified interpretation")
    cell_rows = [r for r in cell_rows[1:] if r["cells"].get("G", {}).get("value")]
    human, human_by_exact, human_by_assignment = [], {}, {}
    for record in cell_rows:
        c = record["cells"]
        code, role, url = c["G"]["value"], c["H"]["value"], c["C"]["value"]
        require(f"workbook_gtin_text_{record['row']}", c["G"]["type"] in {"str", "s", "inlineStr"}
                and code.isdigit() and Decimal(c["A"]["value"]) == Decimal(code))
        review = review_index[(code, role, url)]
        r = row_map[(role, code, review["region"], review["category"], review["image_sha256"])]
        action = "EXCLUDE" if c["I"]["value"].startswith("EXCLUDE") else "ACCEPT" if c["I"]["value"].startswith("ACCEPT") else "REASSESS" if c["I"]["value"].startswith("REVIEW") else "INVALID"
        cause = ("category_mismatch" if review["category_issue"] == "True" else "identity_conflict"
                 if review["identity"] == "reference_brand_conflict_unresolved" else "image_unsuitability") if action == "EXCLUDE" else "missing_name_reassessment" if action == "REASSESS" else "human_accepted_image"
        item = dict(workbook_sheet=sheet, workbook_row=record["row"], workbook_sha256=sha(wb),
            original_gtin_cell=c["A"]["cell"], original_gtin_cell_type=c["A"]["type"], original_gtin_raw=c["A"]["raw"],
            original_gtin_display=c["A"]["value"], exact_gtin_cell=c["G"]["cell"], exact_gtin_text=code,
            leading_zeros_restored_from_text_column=c["A"]["value"] != code, clarified_action_cell=c["I"]["cell"],
            role=role, barcode=code, region=r["region"], category=r["category"], countries=r["countries"],
            sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"], accounting_component=r["accounting_component"],
            image_sha256=r["image_sha256"], picture_url=url, frozen_source_name=r["product_name"],
            prior_codex_classification=c["D"]["value"], prior_codex_rationale=c["E"]["value"],
            original_julia_comment=c["F"]["value"], clarified_interpretation=c["I"]["value"], instruction_reason=c["J"]["value"],
            step4_human_action=action, decision_kind=cause,
            identity_provenance="Exact G text + H role + C frozen picture URL uniquely match Step 3; region/category/hash inherited from that frozen row, then matched to Step 2.",
            original_comment_overridden=action == "REASSESS", resulting_attribution_status="pending" if action == "REASSESS" else action)
        require(f"unique_human_identity_{record['row']}", exact(r) not in human_by_exact and action != "INVALID")
        human.append(item)
        human_by_exact[exact(r)] = item
        human_by_assignment[(*identity(r), r["image_sha256"])] = item
    require("21_human_actions_12_exclude_2_accept_7_reassess", len(human) == 21 and Counter(r["step4_human_action"] for r in human) == {"EXCLUDE": 12, "ACCEPT": 2, "REASSESS": 7})
    require("human_excludes_7_selected_5_reserve", Counter(r["role"] for r in human if r["step4_human_action"] == "EXCLUDE") == {"selected": 7, "reserve": 5})

    # Preserve historical secondary assignments, including old primary/reserve
    # non-owners absent from Step 2. Metadata comes from existing frozen rows.
    links = tables["run_06b_step2_v1/secondary_coverage_links_frozen.csv"]
    old_selected = {identity(r): r for r in tables["run_06b_v2/selected_manifest.csv"]}
    context = {identity(r): r for r in tables["run_06b_v2/selected_draw.csv"] + tables["run_06b_v2/reserve_audit.csv"]}
    preflight = {identity(r): r for r in tables["run_06b_v2/image_preflight_products.csv"]}
    secondary = []
    for i, link in enumerate(links, 1):
        k = link["secondary_barcode"], link["secondary_region"], link["secondary_category"]
        source = context[k]
        evidence = preflight[k]
        secondary.append({**source, **evidence, "prompt_product_name": source["product_name"],
            "prompt_brand": source["brands"], "role": "secondary", "source_sequence": i,
            "case_key_step4": json.dumps(["secondary", *k], separators=(",", ":")),
            "step2_eligibility_qualified": "1", "link_source_index": i})
    nodes = rows + secondary
    beverage = {(r["barcode"], r["region"]): r for r in tables["beverage_final_v1/eligibility_decisions.csv"]}

    # At most one indexed lookup per unique missing-name barcode. No table scan.
    missing = [r for r in nodes if not r["prompt_product_name"].strip() and r["step2_eligibility_qualified"] == "1"]
    missing_codes = sorted({r["barcode"] for r in missing})
    db_before = (DATABASE.stat().st_size, DATABASE.stat().st_mtime_ns)
    connection = sqlite3.connect(DATABASE.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.execute("PRAGMA query_only=ON")
    columns = ["barcode", "product_name", "brands", "off_brands_raw", "query_category", "off_categories", "ingredients_text", "quantity", "packaging", "image_url"]
    query = "SELECT " + ",".join(columns) + " FROM products WHERE barcode=?"
    sql_plan = list(connection.execute("EXPLAIN QUERY PLAN " + query, (missing_codes[0],))) if missing_codes else []
    require("metadata_lookups_use_exact_barcode_index", all("SEARCH" in r[3] and "barcode=?" in r[3] for r in sql_plan))
    metadata = {}
    for code in missing_codes:
        value = connection.execute(query, (code,)).fetchone()
        metadata[code] = dict(zip(columns, value)) if value else None
    connection.close()
    require("read_only_metadata_database_stat_unchanged", db_before == (DATABASE.stat().st_size, DATABASE.stat().st_mtime_ns))
    missing_register, missing_by_node = [], {}
    for r in missing:
        m = metadata[r["barcode"]]
        same_image = bool(m and family(m["image_url"]) and family(m["image_url"]) == family(r["original_image_url"]))
        same_category = bool(m and m["query_category"] == r["category"])
        corroboration = [k for k in ["brands", "off_brands_raw", "off_categories", "ingredients_text", "quantity", "packaging"] if m and m[k] not in (None, "")]
        ok = bool(m and same_image and same_category and corroboration)
        reason = ("Exact frozen GTIN row, same recorded image revision and governed category, plus " + ", ".join(corroboration)
                  + "; no conflicting frozen attribution found. Missing names remain unchanged.") if ok else (
            "Insufficient or conflicting attribution beyond missing name: " + json.dumps(dict(indexed_row_found=bool(m), same_image_revision=same_image, same_governed_category=same_category, corroborating_fields=corroboration)))
        item = dict(role=r["role"], barcode=r["barcode"], region=r["region"], category=r["category"],
            image_sha256=r["image_sha256"], source_sequence=r["source_sequence"], name_missing=True,
            brand_also_missing=not bool(r["prompt_brand"].strip()), attribution_decision="PROCESS" if ok else HOLD,
            reason=reason, same_recorded_image_revision=same_image, same_governed_category=same_category,
            corroborating_fields="|".join(corroboration), indexed_metadata_json=json.dumps(m, ensure_ascii=False, sort_keys=True),
            original_name_preserved=r["prompt_product_name"], original_brand_preserved=r["prompt_brand"],
            nutrition_treatment="retain_existing_nutrition_eligibility" if ok else "hold_affected_assignment_until_attribution_resolved",
            paid_attempts_consumed=0, ocr_outcome="not_attempted", evidence_source="Frozen October release copy: indexed exact-barcode products lookup")
        missing_register.append(item)
        missing_by_node[exact(r)] = item
    for h in human:
        if h["step4_human_action"] == "REASSESS":
            h["resulting_attribution_status"] = missing_by_node[(h["role"], h["barcode"], h["region"], h["category"], h["image_sha256"])]["attribution_decision"]

    # Saved historical ledger is the existing history baseline. Verify the small
    # recorded CSV sources; never open the production database or rerun history.
    history = tables["run_06b_v2/history_observations_refreshed.csv"]
    source_checks = []
    for item in tables["run_06b_v2/history_source_inventory_refreshed.csv"]:
        if item["source"].endswith(".csv") and item["source"].startswith("data/"):
            path = ROOT / item["source"]
            actual = sha(path.read_bytes()) if path.is_file() else "MISSING"
            require("historical_csv_unchanged_" + path.name, actual == item["hash"])
            source_checks.append(dict(source=item["source"], recorded_sha256=item["hash"], actual_sha256=actual, status="PASS"))
    by_barcode, by_family = defaultdict(list), defaultdict(list)
    for event in history:
        by_barcode[event["barcode"]].append(event)
        if family(event["evidence_image_url"]):
            by_family[family(event["evidence_image_url"])].append(event)
    configuration = json.loads(blobs["run_06b_v2/core_configuration_proposal.json"])
    history_register, history_evidence = [], []
    state, reasons = {}, {}
    node_map = {exact(r): r for r in nodes}
    proposed_keys = {}
    for r in nodes:
        k = exact(r)
        action, why = "PROCESS", []
        human_decision = human_by_assignment.get((*identity(r), r["image_sha256"]))
        bv = beverage.get((r["barcode"], r["region"])) if r["category"] == "beverages" else None
        if r["step2_eligibility_qualified"] != "1" or (bv and bv["status"] in {"excluded", "hold"}):
            action = "EXCLUDE" if bv and bv["status"] == "excluded" else HOLD
            why.append("Locked beverage " + (bv["status"] if bv else "restriction") + ": " + (bv["reason"] if bv else r.get("step2_beverage_reason", "")))
        if human_decision and human_decision["step4_human_action"] == "EXCLUDE":
            action = "EXCLUDE"
            why.append("Julia confirmed " + human_decision["decision_kind"] + ": " + human_decision["original_julia_comment"])
        attribution = missing_by_node.get(k)
        if attribution and attribution["attribution_decision"] == HOLD and action != "EXCLUDE":
            action = HOLD
            why.append(attribution["reason"])
        direct = by_barcode.get(r["barcode"], [])
        direct_success = [e for e in direct if e["valid_success"] == "True"]
        direct_failures = [e for e in direct if e["failure_or_unusable"] == "True"]
        uncertain = [e for e in direct if e["uncertain"] == "True"]
        overlaps = [e for e in by_family.get(family(r["requested_url"]), []) if e["barcode"] != r["barcode"]]
        family_success = [e for e in overlaps if e["valid_success"] == "True"]
        family_failures = [e for e in overlaps if e["failure_or_unusable"] == "True"]
        if direct_success:
            history_status = "PRIOR_SUCCESS_FIRST_ATTEMPT_INELIGIBLE_EXACT_BARCODE"
            if action != "EXCLUDE":
                action = "EXCLUDE"
            why.append("Exact barcode has saved valid success (including no-claim); no first-attempt resubmission. Immutable evidence/config equivalence remains separately unproved.")
        elif direct_failures:
            history_status = "PRIOR_FAILURE_RETRY_OUTSIDE_ALLOCATION"
            action = "EXCLUDE" if action != "EXCLUDE" else action
            why.append("Saved exact-barcode failure/unusable attempt belongs to the excluded retry pool.")
        elif uncertain:
            history_status = "EXACT_BARCODE_HISTORY_UNCERTAIN"
            if action != "EXCLUDE": action = HOLD
            why.append("Saved exact-barcode history is unresolved; no billable attempt authorized.")
        elif family_success or family_failures:
            history_status = "POSSIBLE_PRIOR_IMAGE_WORK_EQUIVALENCE_UNRESOLVED"
            if action != "EXCLUDE": action = HOLD
            why.append("Same saved image revision appears under another historical barcode; historical pixel/byte hash and complete runtime configuration are unavailable. Hold possible redundant OCR pending reconciliation; no success/failure invented for this assignment.")
        else:
            history_status = "NO_MATCH_IN_FROZEN_HISTORY_LEDGER"
        matched = { (e["source"], e["source_row"]): e for e in direct + overlaps }
        for e in matched.values():
            history_evidence.append(dict(role=r["role"], barcode=r["barcode"], region=r["region"], category=r["category"],
                current_image_sha256=r["image_sha256"], historical_barcode=e["barcode"], historical_source=e["source"],
                historical_source_row=e["source_row"], historical_status=e["status"], historical_valid_success=e["valid_success"],
                historical_no_claim_success=e["valid_success"] == "True" and e["status"] == "success_no_claims",
                historical_failure_or_unusable=e["failure_or_unusable"], historical_prompt_version=e["prompt_version"],
                historical_model=e["vision_model"], historical_image_url=e["evidence_image_url"],
                exact_barcode_match=e["barcode"] == r["barcode"], same_image_revision=bool(family(e["evidence_image_url"]) and family(e["evidence_image_url"]) == family(r["requested_url"])),
                historical_immutable_image_hash_available=False, historical_full_configuration_available=False,
                certified_equivalent_paid_work=False, automatic_reuse_authorized=False))
        hr = dict(role=r["role"], barcode=r["barcode"], region=r["region"], category=r["category"], image_sha256=r["image_sha256"],
            history_status=history_status, exact_prior_success_observations=len(direct_success), exact_prior_failure_observations=len(direct_failures),
            other_barcode_same_revision_success_observations=len(family_success), other_barcode_same_revision_failure_observations=len(family_failures),
            valid_no_claim_success_observations=sum(e["valid_success"] == "True" and e["status"] == "success_no_claims" for e in matched.values()),
            first_attempt_history_status="retain_pending_other_gates" if history_status == "NO_MATCH_IN_FROZEN_HISTORY_LEDGER" else "blocked_or_held",
            certified_historical_work_equivalence=False, history_scope="Frozen RUN 06B v2 52274-observation ledger; small recorded CSV hashes checked, no live database history refresh")
        history_register.append(hr)
        state[k], reasons[k] = action, why
        region_profile = configuration["regional_profiles"][r["region"]]
        ocr_config = {f: configuration[f] for f in ["ocr_engine", "ocr_api_version", "ocr_options", "image_transform"]}
        ocr_key = stable(dict(kind="PROPOSED_OCR_v1_NOT_EXECUTABLE", image_sha256=r["image_sha256"], options=ocr_config))
        core_key = stable(dict(kind="PROPOSED_CORE_LLM_v1_NOT_EXECUTABLE", image_sha256=r["image_sha256"],
            full_configuration_proposal_sha256=hashes["run_06b_v2/core_configuration_proposal.json"], regional_profile=region_profile,
            frozen_context={f: r[f] for f in ["prompt_product_name", "prompt_brand", "category"]}))
        proposed_keys[k] = ocr_key, core_key

    # Current selection owners always take precedence over contingent reserves.
    # No reserve obtains a primary slot through this grouping operation.
    def owner_order(r):
        return (0 if r["role"] == "selected" else 1, int(r["frozen_group_frame_N"] or "0"), r["sampling_group_id"], *identity(r))
    ocr_groups, core_groups = defaultdict(list), defaultdict(list)
    for r in rows:
        if state[exact(r)] == "PROCESS":
            ocr_key, core_key = proposed_keys[exact(r)]
            ocr_groups[ocr_key].append(r)
            core_groups[core_key].append(r)
    ocr_owners = {k: sorted(v, key=owner_order)[0] for k, v in ocr_groups.items()}
    core_owners = {k: sorted(v, key=owner_order)[0] for k, v in core_groups.items()}
    ownership = []
    for r in rows:
        k = exact(r)
        ok, ck = proposed_keys[k]
        oowner = ocr_owners.get(ok) if state[k] == "PROCESS" else None
        cowner = core_owners.get(ck) if state[k] == "PROCESS" else None
        ownership.append(dict(role=r["role"], barcode=r["barcode"], region=r["region"], category=r["category"],
            countries=r["countries"], sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"], accounting_component=r["accounting_component"],
            source_image_sha256=r["image_sha256"], step4_status=state[k], proposed_ocr_key=ok, proposed_core_llm_key=ck,
            proposed_ocr_owner_identity=json.dumps([oowner["role"], *identity(oowner)]) if oowner else "",
            proposed_ocr_owner_slot=oowner.get("slot_id", "") if oowner else "",
            proposed_llm_owner_identity=json.dumps([cowner["role"], *identity(cowner)]) if cowner else "",
            proposed_llm_owner_slot=cowner.get("slot_id", "") if cowner else "",
            redundant_ocr_submission_under_proposal=bool(oowner and exact(oowner) != k),
            redundant_llm_submission_under_proposal=bool(cowner and exact(cowner) != k),
            ownership_scope="selected_candidate" if r["role"] == "selected" else "reserve_option_only_no_promotion",
            provider_configuration_verified=False, paid_execution_authorized=False))
    # Same-profile core equivalence would imply a redundant independent slot.
    # It is reported and removed from the processing shortlist, never filled.
    for r in rows:
        k = exact(r)
        if r["role"] == "selected" and state[k] == "PROCESS" and exact(core_owners[proposed_keys[k][1]]) != k:
            state[k] = "EXCLUDE"
            reasons[k].append("Equivalent proposed current core work already has another selected owner; no independent quota credit.")

    secondary_register, orphan_register = [], []
    old_orphans = {int(r["source_link_row"]) for r in tables["run_06b_step2_v1/secondary_link_step2_annotations.csv"] if r["owner_slot_step2_state"] == "vacant_pending_review"}
    selected_by_slot = {r["slot_id"]: r for r in rows if r["role"] == "selected"}
    for i, (link, node) in enumerate(zip(links, secondary), 1):
        k = exact(node)
        old_owner = selected_by_slot.get(link["owner_slot_id"])
        ck = proposed_keys[k][1]
        viable = [r for r in core_groups.get(ck, []) if r["role"] == "selected" and state[exact(r)] == "PROCESS"]
        chosen = old_owner if old_owner and state[exact(old_owner)] == "PROCESS" and proposed_keys[exact(old_owner)][1] == ck else (sorted(viable, key=owner_order)[0] if viable else None)
        if state[k] != "PROCESS":
            chosen = None
            link_status = "BLOCKED_OR_HELD_SECONDARY_ASSIGNMENT"
        elif chosen:
            link_status = "PROPOSED_RETAIN_ORIGINAL_OWNER" if chosen["slot_id"] == link["owner_slot_id"] else "PROPOSED_ALTERNATIVE_EXISTING_SELECTED_OWNER"
        else:
            link_status = "UNRESOLVED_NO_DEFENSIBLE_ACTIVE_SELECTED_OWNER"
        item = dict(source_link_row=i, **link, step4_secondary_status=state[k],
            secondary_reasons=" | ".join(reasons[k]), original_owner_now_available=bool(old_owner and state[exact(old_owner)] == "PROCESS"),
            proposed_owner_slot=chosen["slot_id"] if chosen else "", proposed_owner_barcode=chosen["barcode"] if chosen else "",
            proposed_owner_region=chosen["region"] if chosen else "", link_reconciliation_status=link_status,
            core_equivalence_proposal_sha256=ck, original_owner_blocked_in_step2=i in old_orphans,
            coverage_credited_now=False, owner_change_executed=False, reserve_promoted=False)
        secondary_register.append(item)
        if i in old_orphans:
            orphan_register.append(item)
    require("806_secondary_links_and_13_original_orphans_accounted", len(secondary_register) == 806 and len(orphan_register) == 13)

    duplicate_register = []
    row_by_key = {(r["role"], *identity(r)): r for r in rows}
    for pair in tables["run_06b_step3_v1/duplicate_evidence_exceptions.csv"]:
        a = row_by_key[tuple(pair["left_" + f] for f in ["role", "barcode", "region", "category"])]
        z = row_by_key[tuple(pair["right_" + f] for f in ["role", "barcode", "region", "category"])]
        same_bytes = pair["identical_image_bytes"] == "True"
        duplicate_register.append({**pair, "step4_left_status": state[exact(a)], "step4_right_status": state[exact(z)],
            "underlying_evidence_relationship": "identical_cached_bytes" if same_bytes else "same_saved_OFF_source_revision_lineage_but_different_raster_input",
            "proposed_ocr_reuse": "share_one_OCR_submission_if_both_active_and_actual_OCR_options_frozen" if same_bytes else "do_not_reuse_OCR_automatically_different_pixels_resolution",
            "core_llm_processing": "separate_regional_LLM_profiles_required" if pair["identical_regional_profile_proposal"] == "False" else "compare_full_core_context_key",
            "historical_OCR_reuse_certified": False, "image_variant_swapped": False, "execution_authorized": False})

    hr_map = {(r["role"], r["barcode"], r["region"], r["category"], r["image_sha256"]): r for r in history_register}
    reconciled = []
    for r in rows:
        k = exact(r)
        h = human_by_exact.get(k)
        attribution = missing_by_node.get(k)
        nutrition = "preserve_existing_nutrition_eligibility_no_new_rule"
        if h and h["step4_human_action"] == "EXCLUDE" and h["decision_kind"] in {"category_mismatch", "identity_conflict"}:
            nutrition = "exclude_affected_assignment_" + h["decision_kind"]
        elif attribution and attribution["attribution_decision"] == HOLD:
            nutrition = "hold_affected_assignment_unresolved_attribution"
        extras = dict(step4_status=state[k], step4_reasons=" | ".join(reasons[k]) or "Candidate retained pending technical/provider and final-manifest gates.",
            step4_human_action=h["step4_human_action"] if h else "not_in_21_case_workbook",
            step4_human_decision_kind=h["decision_kind"] if h else "", step4_workbook_row=h["workbook_row"] if h else "",
            step4_name_attribution=attribution["attribution_decision"] if attribution else "not_missing_name",
            step4_history_status=hr_map[k]["history_status"], step4_nutrition_treatment=nutrition,
            step4_proposed_ocr_key=proposed_keys[k][0], step4_proposed_core_key=proposed_keys[k][1],
            step4_execution_authorized=False, step4_paid_attempts_consumed=0,
            step4_processing_scope="candidate_only" if r["role"] == "selected" else "reserve_only_no_promotion")
        reconciled.append({**{f: r[f] for f in (sf if r["role"] == "selected" else rf)}, **extras})
    selected_records = reconciled[:len(original_selected)]
    reserve_records = reconciled[len(original_selected):]
    candidates = [r for r in selected_records if r["step4_status"] == "PROCESS"]
    blocked_selected = [r for r in selected_records if r["step4_status"] != "PROCESS"]
    qualified_reserves = [r for r in reserve_records if r["step4_status"] == "PROCESS"]
    require("source_row_columns_preserved_including_blank_names_and_gtins", all(
        all(src[f] == out[f] for f in fields) for srcs, outs, fields in [(original_selected, selected_records, sf), (original_reserves, reserve_records, rf)] for src, out in zip(srcs, outs)))
    require("selected_and_reserves_partition_once", len(candidates) + len(blocked_selected) == 11832
            and len(reserve_records) == 2233 and len({identity(r) for r in selected_records}) == 11832)
    require("missing_name_not_an_automatic_exclusion_or_failure", all(r["attribution_decision"] in {"PROCESS", HOLD} and r["paid_attempts_consumed"] == 0 for r in missing_register))
    for h in human:
        current = row_map[(h["role"], h["barcode"], h["region"], h["category"], h["image_sha256"])]
        h["step4_final_candidate_status"] = state[exact(current)]
        h["additional_history_or_ownership_reason"] = " | ".join(reasons[exact(current)])

    vacancies = []
    for r in tables["run_06b_step2_v1/vacancies.csv"]:
        vacancies.append({**r, "step4_vacancy_origin": "preexisting_step2_vacancy", "step4_reason": r["reason"]})
    for r in blocked_selected:
        vacancies.append(dict(slot_id=r["slot_id"], barcode=r["barcode"], region=r["region"], category=r["category"],
            sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"], accounting_component=r["accounting_component"],
            vacancy_origin="step4_candidate_restriction", reason=r["step4_reasons"], disposition="vacant_no_promotion",
            selected_source_row=r["step2_source_row"], original_draw_barcode=r["original_draw_barcode"],
            decision_source="Step4_human_attribution_history_ownership_registers", decision_authority="Julia_step4_instruction_and_clarified_workbook",
            decision_sidecar_sha256=sha(wb), replacement_promoted="False",
            step4_vacancy_origin=r["step4_status"], step4_reason=r["step4_reasons"]))
    def cell(r): return r["sampling_group_id"], r["country_cell"], r["accounting_component"]
    plan = tables["run_06b_step2_v1/approved_country_component_plan_frozen.csv"]
    target = {"upper_observed_fibre": "targeted_upper_fibre", "explicit_preparation_or_specialist": "targeted_beverage_preparation_or_specialist"}
    quota = Counter()
    for r in plan:
        quota[(r["sampling_group_id"], r["country_cell"], "random_baseline")] += int(r["random_baseline"])
        if int(r["targeted_attempts"]): quota[(r["sampling_group_id"], r["country_cell"], target[r["target_component"]])] += int(r["targeted_attempts"])
    cn, vn, rn = Counter(cell(r) for r in candidates), Counter(cell(r) for r in vacancies), Counter(cell(r) for r in qualified_reserves)
    availability = [dict(sampling_group_id=k[0], country_cell=k[1], accounting_component=k[2], approved_quota=n,
        retained_candidates=cn[k], vacancies=vn[k], matching_qualified_reserves=rn[k],
        arithmetic_shortfall_before_further_technical_losses=max(0, vn[k] - rn[k]), promoted_reserves=0)
        for k, n in quota.items()]
    require("24_groups_56_cells_12000_slots_preserved", len({r["sampling_group_id"] for r in plan}) == 24 and len(plan) == 56
            and sum(quota.values()) == len(candidates) + len(vacancies) == 12000
            and all(cn[k] + vn[k] == n for k, n in quota.items()) and len({r["slot_id"] for r in vacancies}) == len(vacancies))
    potential, sequence = [], Counter()
    for r in qualified_reserves:
        k = cell(r)
        if vn[k]:
            sequence[k] += 1
            potential.append(dict(barcode=r["barcode"], region=r["region"], category=r["category"], countries=r["countries"],
                sampling_group_id=k[0], country_cell=k[1], accounting_component=k[2], frozen_reserve_sequence=r["step2_source_row"],
                matching_sequence=sequence[k], matching_vacancies=vn[k], status="matching_reserve_option_not_promoted", promoted=False))
    require("no_country_component_transfers_or_promotion", all(cell(r) in quota and vn[cell(r)] > 0 and r["promoted"] is False for r in potential)
            and [int(r["frozen_reserve_sequence"]) for r in potential] == sorted(int(r["frozen_reserve_sequence"]) for r in potential))
    require("US_CA_dairy_still_excluded", not any(r["region"] == "US+CA" and r["category"] == "dairies" for r in rows))
    require("no_confirmed_historical_equivalence_inferred_from_URL_only", not any(r["certified_equivalent_paid_work"] for r in history_evidence))

    OUT.mkdir()
    (OUT / ".gitignore").write_text("# Local product-level Step 4 evidence; no publication approval.\n*\n", encoding="utf-8")
    (OUT / "reviewed_workbook_frozen.xlsx").write_bytes(wb)
    (OUT / "step4_instruction_frozen.txt").write_bytes(brief)
    write_json("workbook_cell_snapshot.json", dict(source=str(WORKBOOK), sha256=sha(wb), sheet=sheet, rows=cell_rows))
    write_json("indexed_metadata_snapshot.json", dict(database=str(DATABASE.relative_to(ROOT)), mode="read_only_immutable_exact_barcode_index",
        query=query, explain_query_plan=[list(x) for x in sql_plan], metadata=metadata,
        exact_lookup_count=len(missing_codes), database_stat_before=db_before,
        no_full_database_hash_or_scan=True))
    outputs = [("human_decision_reconciliation.csv", human), ("missing_name_attribution.csv", missing_register),
        ("proposed_paid_work_ownership.csv", ownership), ("secondary_link_reconciliation.csv", secondary_register),
        ("original_13_owner_exceptions.csv", orphan_register), ("duplicate_evidence_reconciliation.csv", duplicate_register),
        ("historical_overlap_reconciliation.csv", history_register), ("historical_match_evidence.csv", history_evidence),
        ("historical_source_hash_checks.csv", source_checks), ("selected_reconciliation_register.csv", selected_records),
        ("candidate_selected_manifest.csv", candidates), ("blocked_selected_register.csv", blocked_selected),
        ("reserve_reconciliation_register.csv", reserve_records), ("vacancies.csv", vacancies),
        ("matching_reserve_availability.csv", availability), ("potential_matching_reserves.csv", potential)]
    for name, values in outputs:
        write_csv(name, values)
    (OUT / "secondary_coverage_links_frozen.csv").write_bytes(blobs["run_06b_step2_v1/secondary_coverage_links_frozen.csv"])
    counts = dict(human_actions=dict(Counter(r["step4_human_action"] for r in human)),
        seven_reassessments=dict(Counter(r["resulting_attribution_status"] for r in human if r["step4_human_action"] == "REASSESS")),
        selected_status=dict(Counter(r["step4_status"] for r in selected_records)), reserve_status=dict(Counter(r["step4_status"] for r in reserve_records)),
        selected_candidates=len(candidates), vacancies=len(vacancies), matching_reserve_options=len(potential),
        qualified_reserves=len(qualified_reserves), selected_missing_names=sum(r["role"] == "selected" for r in missing_register),
        reserve_missing_names=sum(r["role"] == "reserve" for r in missing_register),
        missing_name_attribution={role: dict(Counter(r["attribution_decision"] for r in missing_register if r["role"] == role)) for role in ["selected", "reserve", "secondary"]},
        missing_both_attribution={role: dict(Counter(r["attribution_decision"] for r in missing_register if r["role"] == role and r["brand_also_missing"])) for role in ["selected", "reserve", "secondary"]},
        primary_history_status=dict(Counter(r["history_status"] for r in history_register if r["role"] == "selected")),
        reserve_history_status=dict(Counter(r["history_status"] for r in history_register if r["role"] == "reserve")),
        original_13_link_status=dict(Counter(r["link_reconciliation_status"] for r in orphan_register)),
        all_secondary_link_status=dict(Counter(r["link_reconciliation_status"] for r in secondary_register)),
        active_selected_proposed_OCR_units=len({proposed_keys[exact(r)][0] for r in rows if r["role"] == "selected" and state[exact(r)] == "PROCESS"}),
        active_selected_proposed_core_LLM_units=len({proposed_keys[exact(r)][1] for r in rows if r["role"] == "selected" and state[exact(r)] == "PROCESS"}),
        matched_historical_no_claim_observations=sum(r["historical_no_claim_success"] for r in history_evidence),
        unresolved_vacancies_without_enough_matching_reserves=sum(r["arithmetic_shortfall_before_further_technical_losses"] for r in availability))
    name_summary = []
    for role in ["selected", "reserve", "secondary"]:
        for both in [False, True]:
            members = [r for r in missing_register if r["role"] == role and r["brand_also_missing"] == both]
            name_summary.append(dict(role=role, missing_fields="name_and_brand" if both else "name_only", total=len(members),
                attribution_PROCESS=sum(r["attribution_decision"] == "PROCESS" for r in members), attribution_HOLD=sum(r["attribution_decision"] == HOLD for r in members),
                final_PROCESS=sum(state[(r["role"], r["barcode"], r["region"], r["category"], r["image_sha256"])] == "PROCESS" for r in members),
                final_HOLD=sum(state[(r["role"], r["barcode"], r["region"], r["category"], r["image_sha256"])] == HOLD for r in members),
                final_EXCLUDE=sum(state[(r["role"], r["barcode"], r["region"], r["category"], r["image_sha256"])] == "EXCLUDE" for r in members)))
    write_csv("missing_name_process_hold_summary.csv", name_summary)
    require("sources_workbook_and_brief_preserved", hashes == {p: sha((BASE / p).read_bytes()) for p in INPUTS}
            and sha(WORKBOOK.read_bytes()) == sha(wb) and sha(BRIEF.read_bytes()) == sha(brief))
    require("frozen_names_gtins_and_country_values_roundtrip", all(
        all(out[f] == src[f] for f in fields) for filename, originals, fields in [("selected_reconciliation_register.csv", original_selected, sf),
            ("reserve_reconciliation_register.csv", original_reserves, rf)]
        for out, src in zip(csv_data((OUT / filename).read_bytes())[1], originals)))
    write_json("validation.json", dict(status="PASS", checks=checks, counts=counts, indexed_lookup_query_plan_verified=True,
        paid_calls=0, reserve_promotions=0, history_modified=False, executable_manifest_created=False))
    name_table = "\n".join(f"| {r['role']} | {r['missing_fields']} | {r['total']} | {r['attribution_PROCESS']} | {r['attribution_HOLD']} | {r['final_PROCESS']} | {r['final_HOLD']} | {r['final_EXCLUDE']} |" for r in name_summary)
    report = f"""# RUN 06B — Step 4

Status: **Reconciliation complete; pending Julia's review before final manifest preparation.**

## Reconciled candidates and vacancies

| Population | PROCESS candidate | PRE-EXECUTION HOLD | EXCLUDE |
|---|---:|---:|---:|
| Step 2 selected (11,832) | {counts['selected_status'].get('PROCESS',0)} | {counts['selected_status'].get(HOLD,0)} | {counts['selected_status'].get('EXCLUDE',0)} |
| Frozen remaining reserves (2,233) | {counts['reserve_status'].get('PROCESS',0)} | {counts['reserve_status'].get(HOLD,0)} | {counts['reserve_status'].get('EXCLUDE',0)} |

There are **{counts['vacancies']} vacant slots**, including the 168 Step 2 vacancies. No reserve was promoted.
The approved allocation remains 12,000 across 24 groups and 56 group/country cells; US+CA dairy, missing-M1 jobs and retries remain excluded.
The human-only provisional count is 11,825 before attribution/history/ownership adjustments. It is not used as a fixed final target.
`PROCESS` means retained for further preparation. It does not authorize payment or certify every unreviewed front image.

## Julia's clarified review and missing names

All 21 workbook rows uniquely match the frozen Step 3 and Step 2 evidence by exact text GTIN, role, picture URL, region, category and image hash.
Workbook column G supplies the exact text identifiers; column A's original numeric literals, original comments and I/J clarifications are retained in the cell snapshot and decision register.
Region/category/hash are inherited from the unique frozen review match, not claimed to be columns supplied by the workbook.
Applied **12 EXCLUDE, 2 ACCEPT, 7 REASSESS**. The 12 exclusions comprise seven selected and five reserve assignments. Reasons distinguish image unsuitability, identity conflict and category mismatch.
The two accepted images remain candidates subject to history and ownership checks. The clarified column overrides earlier missing-name comments; those original comments are preserved unchanged.
Seven reassessments: {json.dumps(counts['seven_reassessments'])}.

The new instruction corrects Step 3's overly restrictive missing-name treatment. A missing name or brand alone is not an exclusion, failed OCR, paid attempt or nutritional-segmentation rejection.
Attribution uses exact frozen GTIN plus the existing image-revision association, matching governed category and available ingredients/OFF categories/brand/quantity/packaging from the frozen release copy.
Only exact indexed barcode lookups were run ({len(missing_codes)} unique barcodes including secondary cases); no table scan, new visual review, image decoding or URL preflight occurred.
Original NULL, blank names, brands and ingredient evidence remain preserved; no product name was manufactured or replaced by a visual guess.
Adequate attribution preserves existing nutritional eligibility. Material category/identity exclusions or unresolved attribution are marked for the affected assignment only.
Valid future no-claim observations count as successes even when the source name is blank.

| Role | Missing fields | Cases | Attribution PROCESS | Attribution HOLD | Final PROCESS | Final HOLD | Final EXCLUDE |
|---|---|---:|---:|---:|---:|---:|---:|
{name_table}

## Current evidence ownership proposal

The 201 Step 3 pairs and all 806 secondary links are retained and reconciled. Identical-byte cases are separated from 100 different-raster pairs sharing an OFF image revision.
The different-raster variants share recorded source lineage, but every saved pixel hash differs: their OCR inputs are not proven interchangeable. They retain separate source hashes and no image variant was substituted.
Identical bytes can share one proposed OCR submission only under the same actual OCR engine/version/options; provider/runtime validation remains a gate. France and US/Canada require distinct core LLM prompts, so raw-image equality does not merge those regional LLM jobs.
Proposed keys hash the frozen byte identity, OCR or regional core configuration proposal, and exact context. Empty names are permitted context values. No authorized paid-work key was created.
Existing selected candidates take precedence over reserves as proposed owners. Reserve owners are options only and cannot consume a selected quota or fill a vacancy.
Active selected proposal: **{counts['active_selected_proposed_OCR_units']} OCR units and {counts['active_selected_proposed_core_LLM_units']} core LLM units**. These are not prices or approved submissions.
Original 13 orphan-link outcomes: {json.dumps(counts['original_13_link_status'])}.
All secondary outcomes: {json.dumps(counts['all_secondary_link_status'])}.
No secondary coverage is credited now. Unresolved links remain preserved rather than assigned to an excluded, held or merely reserved owner.

## Historical processing

Used the saved **52,274-observation** RUN 06B v2 history ledger and image-reference evidence, with {len(source_checks)} small source CSV hashes verified unchanged.
The production database was not opened. No database history scan/refresh or historical observation was changed; completeness outside the saved inventory is not asserted.
Exact-barcode historical successes (including no-claim) are ineligible for a new first-attempt slot. Exact-barcode failures remain retries outside the allocation.
Historical image-family overlap under another barcode remains held where old immutable pixels and the complete actual provider/prompt configuration cannot be established. Shared URLs or matching prompt-version labels are not proof of equal work.
No historical equivalence was certified and no historical OCR/LLM reuse was authorized from URL-only evidence. Different images/configurations remain distinct observations.
Selected history outcomes: {json.dumps(counts['primary_history_status'])}.
Reserve history outcomes: {json.dumps(counts['reserve_history_status'])}.
Matched historical no-claim successes are explicitly retained in the evidence table ({counts['matched_historical_no_claim_observations']} observation-to-candidate links, not independent paid jobs).
History/paid-eligibility holds consume no attempt and do not themselves remove a nutritionally valid product from nutritional segmentation.

## Matching reserves and blockers

`matching_reserve_availability.csv` reconciles every approved group × country cell × component. `potential_matching_reserves.csv` preserves frozen sequence and contains {len(potential)} options, not promotions.
The arithmetic shortfall if all matching options passed later gates is {counts['unresolved_vacancies_without_enough_matching_reserves']}; technical losses may increase it.
Remaining blockers are unresolved historical evidence/configuration equivalence, contingent OCR reuse and actual provider identity, unresolved owner links, universal front-usability approval, runtime/checkpoint/merge integration and tariff/spending authorization.
Different-raster evidence is not automatically collapsed; the ownership proposal cannot be executed until its exact options are approved.

## Audit and validation

Created a new local Step 4 package and one reconciliation script. Step 2/3 sources, reviewed workbook, raw source fields, category/brand rules, prompts, segmentation and historical results remain unchanged.
All {len(checks)} checks PASS, including exact joins, leading-zero restoration, row partitions, blank-name preservation, no quota/country/component transfer, and before/after source hashes.
`human_decision_reconciliation.csv`, `missing_name_attribution.csv`, `proposed_paid_work_ownership.csv`, `secondary_link_reconciliation.csv`, `historical_overlap_reconciliation.csv` and the vacancy files are the primary evidence.
`manifest.json` records all source/output hashes. `checksums.sha256` includes this report and manifest. The frozen workbook and raw cell snapshot preserve original human provenance.

**STOP after Step 4 for Julia's review. No reserve promotion, executable paid manifest, OCR/LLM call, historical modification or runner execution.**
"""
    (OUT / "RUN 06B - Step 4.md").write_text(report, encoding="utf-8")
    output_hashes = {p.name: sha(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()}
    write_json("manifest.json", dict(package="RUN_06B_STEP4_V1", status="pending_Julia_review_no_execution",
        script="pipeline/segmentation/reconcile_run_06b_step4.py", script_sha256=sha(Path(__file__).read_bytes()),
        source_files_sha256=hashes, reviewed_workbook_sha256=sha(wb), authorized_brief_sha256=sha(brief),
        outputs_sha256=output_hashes, counts=counts, indexed_metadata_lookup_count=len(missing_codes),
        provider_configuration_verified=False, historical_equivalence_certified=False,
        reserve_promotions=0, paid_calls=0, execution_authorized=False, stop="after_Step_4_for_Julia_review"))
    output_hashes["manifest.json"] = sha((OUT / "manifest.json").read_bytes())
    (OUT / "checksums.sha256").write_text("".join(f"{value}  {name}\n" for name, value in sorted(output_hashes.items())), encoding="utf-8")
    print(json.dumps(dict(package=str(OUT), counts=counts, checks_passed=len(checks)), indent=2))


if __name__ == "__main__":
    main()
