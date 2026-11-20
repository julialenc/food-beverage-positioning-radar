"""RUN 05: exact approved groups, refreshed saved OCR history and candidate audit.

No clustering, image request, quota, sample selection, source write or service
call. All 476,626 corrected regional products remain in the candidate ledger.
"""

import ast
import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from run_04_preliminary_clustering import KEY, MODELS, sha

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared.beverage_segments import beverage_view_segment

SEG = ROOT / "presentations/segmentation"
R3 = SEG / "run_03_corrected_v1"
FOLLOW = SEG / "check_04_followup_v1"
OUT = SEG / "run_05_v1"
REPORT = SEG / "RUN 05_no US.md"
R4DOC = SEG / "RUN 04_no US.md"
FROZEN_R4DOC = OUT / "source_snapshots/RUN 04_no US_before_grouping_approval.md"
LEDGER01 = SEG / "run_01/eligibility_ledger.csv"
CURRENT_DB = ROOT / "database/positioning_radar.db"
FIELDS = {"protein": "protein_100g", "total_fat": "fat_100g", "carbohydrates": "carbs_100g",
          "sugars": "sugars_100g", "salt": "salt_100g"}
COUNTRY_REGION = {"FR": "FR", "UK": "UK+IE", "IE": "UK+IE", "US": "US+CA", "CA": "US+CA"}
SUCCESS = ["success_with_claims", "success_no_claims", "success_claim_state_unknown"]
UNASSIGNED = "UNASSIGNED_MISSING_M1"
REPLACE_OWN_DRAFT = False


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read(path, **kwargs):
    return pd.read_csv(path, dtype={c: str for c in KEY}, keep_default_na=False, low_memory=False, **kwargs)


def save(name, frame):
    path = OUT / name
    if path.exists() and not REPLACE_OWN_DRAFT:
        raise FileExistsError(f"Refusing to overwrite {path}")
    temporary = path.with_suffix(".csv.part")
    if temporary.exists():
        raise FileExistsError(temporary)
    frame.to_csv(temporary, index=False, encoding="utf-8", float_format="%.12g")
    temporary.replace(path)


def source_setup():
    if (OUT / "run_05_manifest.json").exists() or REPORT.exists():
        if not REPLACE_OWN_DRAFT:
            raise FileExistsError("RUN 05 outputs already exist")
        prior = json.loads((OUT / "run_05_manifest.json").read_text(encoding="utf-8"))
        for name, meta in prior["outputs"].items():
            if sha(OUT / name) != meta["sha256"]:
                raise ValueError(f"Draft output was modified; refusing replacement: {name}")
        if sha(REPORT) != prior["report"]["sha256"]:
            raise ValueError("Draft report was modified; refusing replacement")
    m = json.loads((FOLLOW / "proposal_manifest.json").read_text(encoding="utf-8"))
    hashes = {}
    for name, digest in m["protected_source_hashes"].items():
        path = FROZEN_R4DOC if name == rel(R4DOC) else ROOT / name
        if sha(path) != digest:
            raise ValueError(f"Protected source mismatch: {name}")
        hashes[rel(path)] = digest
    for p in FOLLOW.iterdir():
        if p.is_file():
            hashes[rel(p)] = sha(p)
    for p in (R4DOC, SEG / "For Wave 3.md", CURRENT_DB, OUT / "manual_review_policy.json",
              ROOT / "shared/beverage_segments.py", ROOT / "pipeline/stages/stage_11_merge_vision_results.py",
              R3 / "assignment_bridge.csv"):
        hashes[rel(p)] = sha(p)
    r1 = json.loads((SEG / "run_01/run_01_manifest.json").read_text(encoding="utf-8"))
    r3 = json.loads((R3 / "run_03_manifest.json").read_text(encoding="utf-8"))
    return hashes, r1, r3


def claim_fields():
    tree = ast.parse((ROOT / "pipeline/stages/stage_11_merge_vision_results.py").read_text(encoding="utf-8"))
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "PACK_CLAIM_FIELDS" for t in n.targets))


def history(base):
    """Union valid historical successes; later failure cannot erase prior work."""
    events, inventory = [], []
    code_scope = set(base.barcode)
    fields = claim_fields()
    b = base[["barcode", "historical_ocr_status"]].drop_duplicates()
    if b.barcode.duplicated().any():
        raise ValueError("Frozen historical statuses conflict across regional assignments")
    for row in b.itertuples(index=False):
        if row.historical_ocr_status == "not_processed":
            continue
        state = row.historical_ocr_status
        if state == "attempted_failed_or_unusable":
            state = "failed_or_unusable"
        if state not in SUCCESS + ["failed_or_unusable"]:
            state = "unclassifiable_saved_result"
        events.append({"barcode": row.barcode, "source": "frozen_RUN01_history", "source_row": row.barcode,
                       "status": state, "timestamp": "", "priority": 0, "llm_status": "", "extraction_status": "",
                       "prompt_version": "", "vision_model": "", "evidence_image_url": ""})
    inventory.append({"source": "frozen_RUN01_history", "rows_inspected": len(b), "hash": sha(LEDGER01),
                      "source_type": "pre-masking history already preserved in approved regional base"})
    print("RUN 05: reading current working-database processing history", flush=True)
    with sqlite3.connect(CURRENT_DB.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT barcode,pack_analysis_attempted,ocr_status,llm_status,
                   claim_extraction_status,pack_claims_found,claim_source,pack_analysis_timestamp,
                   prompt_version,vision_model FROM product_analysis
                   WHERE pack_analysis_attempted=1 OR COALESCE(llm_status,'')<>'' OR claim_source='vision'
                   ORDER BY barcode""").fetchall()
        for number, row in enumerate(rows, 1):
            llm, extraction = str(row["llm_status"] or "").lower(), str(row["claim_extraction_status"] or "").lower()
            if llm == "success" and extraction == "completed" and row["pack_claims_found"] is not None:
                state = "success_with_claims" if row["pack_claims_found"].strip() else "success_no_claims"
            elif row["claim_source"] == "vision" or (llm == "success" and extraction == "completed"):
                state = "unclassifiable_saved_result"
            else:
                state = "failed_or_unusable"
            events.append({"barcode": str(row["barcode"]), "source": rel(CURRENT_DB) + "::product_analysis",
                           "source_row": str(number), "status": state, "timestamp": row["pack_analysis_timestamp"] or "",
                           "priority": 40, "llm_status": llm, "extraction_status": extraction,
                           "prompt_version": row["prompt_version"] or "", "vision_model": row["vision_model"] or "",
                           "evidence_image_url": ""})
    inventory.append({"source": rel(CURRENT_DB) + "::product_analysis", "rows_inspected": len(rows),
                      "hash": sha(CURRENT_DB), "source_type": "current saved working-database observations, read-only"})
    csv_paths = sorted((ROOT / "data/05_vision_release").glob("vision_results*.csv"))
    if not csv_paths:
        raise ValueError("No current saved vision result CSVs found")
    for path in csv_paths:
        print(f"RUN 05: reconciling {path.name}", flush=True)
        header = pd.read_csv(path, nrows=0).columns
        use = [c for c in ["barcode", "pack_analysis_attempted", "ocr_status", "llm_status", "v3_claim_extraction_status",
                           "pack_analysis_timestamp", "prompt_version", "vision_model", "image_url", *[f"v3_{f}" for f in fields]] if c in header]
        d = pd.read_csv(path, usecols=use, dtype=str, keep_default_na=False, low_memory=False)
        if "barcode" not in d or "llm_status" not in d:
            raise ValueError(f"Saved result lacks required status fields: {path}")
        for number, row in enumerate(d.to_dict("records"), 2):
            if not row["barcode"].strip():
                raise ValueError(f"Empty barcode in saved results: {path}:{number}")
            llm = row.get("llm_status", "").strip().lower()
            extraction = row.get("v3_claim_extraction_status", "").strip().lower()
            if llm == "success" and extraction == "completed":
                tokens = [row[f"v3_{f}"].strip().lower() for f in fields if f"v3_{f}" in row]
                if any(t in ("true", "1", "1.0") for t in tokens):
                    state = "success_with_claims"
                elif tokens and all(t in ("false", "0", "0.0") for t in tokens):
                    state = "success_no_claims"
                else:
                    state = "success_claim_state_unknown"
            elif llm or row.get("ocr_status") or row.get("pack_analysis_attempted") in ("1", "True", "true"):
                state = "failed_or_unusable"
            else:
                state = "unclassifiable_saved_result"
            priority = 35 if "normalis" in path.name else (15 if "checkpoint" in path.name else 20)
            events.append({"barcode": row["barcode"], "source": rel(path), "source_row": str(number), "status": state,
                           "timestamp": row.get("pack_analysis_timestamp", ""), "priority": priority,
                           "llm_status": llm, "extraction_status": extraction,
                           "prompt_version": row.get("prompt_version", ""), "vision_model": row.get("vision_model", ""),
                           "evidence_image_url": row.get("image_url", "")})
        inventory.append({"source": rel(path), "rows_inspected": len(d), "hash": sha(path),
                          "source_type": "saved checkpoint rows" if "checkpoint" in path.name else "saved result CSV"})
    e = pd.DataFrame(events)
    e["in_current_regional_population"] = e.barcode.isin(code_scope).astype(int)
    e["valid_success"] = e.status.isin(SUCCESS)
    e["failure_or_unusable"] = e.status.eq("failed_or_unusable")
    e["uncertain"] = e.status.eq("unclassifiable_saved_result")
    parsed = pd.to_datetime(e.timestamp, utc=True, errors="coerce", format="mixed")
    compact = pd.to_datetime(e.timestamp, utc=True, errors="coerce", format="%Y%m%d_%H%M%S")
    compact_used = parsed.isna() & compact.notna()
    parsed = parsed.fillna(compact)
    e["timestamp_parse_state"] = np.select([e.timestamp.eq(""), compact_used, parsed.notna()],
             ["not_saved", "compact_stage_timestamp", "parsed_datetime"], default="unparsed_original")
    e["timestamp_sort_normalized"] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    e["parsed_event_time"] = parsed.fillna(pd.Timestamp("1900-01-01", tz="UTC"))
    e = e.sort_values(["barcode", "parsed_event_time", "priority", "source", "source_row"], kind="stable")
    agg = e.groupby("barcode", sort=False).agg(existing_successful_ocr_llm=("valid_success", "max"),
           prior_failed_or_unusable=("failure_or_unusable", "max"), history_uncertain_evidence=("uncertain", "max"),
           saved_evidence_rows=("source", "size"), history_sources=("source", lambda s: "|".join(sorted(set(s)))))
    latest = e.drop_duplicates("barcode", keep="last").set_index("barcode")
    agg["latest_saved_status"] = latest.status
    agg["latest_saved_timestamp"] = latest.timestamp
    agg["latest_saved_source"] = latest.source
    valid = e.loc[e.valid_success].drop_duplicates("barcode", keep="last").set_index("barcode")
    agg["latest_success_status"] = valid.status
    agg["latest_success_timestamp"] = valid.timestamp
    agg["latest_success_source"] = valid.source
    agg["latest_success_evidence_image_url"] = valid.evidence_image_url
    inv = pd.DataFrame(inventory)
    for idx, row in inv.iterrows():
        v = e.loc[e.source.eq(row.source)]
        scoped = v.loc[v.in_current_regional_population.eq(1)]
        inv.loc[idx, "scoped_barcodes_with_evidence"] = scoped.barcode.nunique()
        inv.loc[idx, "scoped_success_barcodes"] = scoped.loc[scoped.valid_success, "barcode"].nunique()
        inv.loc[idx, "scoped_failed_unusable_barcodes"] = scoped.loc[scoped.failure_or_unusable, "barcode"].nunique()
    return agg.reset_index(), e.drop(columns="parsed_event_time"), inv, csv_paths


def review_register(base):
    policy = json.loads((OUT / "manual_review_policy.json").read_text(encoding="utf-8"))
    findings = read(ROOT / policy["interpreted_findings_source"])
    rows = []
    for item in findings.to_dict("records"):
        assessment = item["assessment"]
        if assessment not in policy["hold_assessments"] + policy["flag_only_assessments"]:
            continue
        rows.append({**{k: item[k] for k in KEY}, "hold": assessment in policy["hold_assessments"],
                     "reason": assessment, "evidence": item["note"],
                     "provenance": policy["interpreted_findings_source"]})
    for item in policy["additional_exact_keys"]:
        rows.append({**item, "provenance": rel(OUT / "manual_review_policy.json")})
    register = pd.DataFrame(rows)
    keys = pd.MultiIndex.from_frame(base[KEY])
    if not pd.MultiIndex.from_frame(register[KEY]).isin(keys).all():
        raise ValueError("Manual review key is outside the current corrected population")
    register["disposition"] = np.where(register.hold, "candidate_hold_pending_manual_review", "review_flag_only_retained")
    register["category_mismatch_hold"] = register.reason.eq("category_mismatch_supported_by_saved_identity") & register.hold
    grouped = register.groupby(KEY, sort=False).agg(manual_review_hold=("hold", "max"),
                  manual_category_mismatch_hold=("category_mismatch_hold", "max"),
                  manual_review_reasons=("reason", lambda s: "|".join(sorted(set(s)))),
                  manual_review_evidence=("evidence", lambda s: " || ".join(s)),
                  manual_review_provenance=("provenance", lambda s: "|".join(sorted(set(s)))))
    return register, grouped.reset_index()


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "").lower()) if not unicodedata.combining(c))


POWDER = re.compile(r"\b(powder(?:s|ed)?|poudre(?:s)?|polvo|dehydrated|dehydrate[es]*|drink mix|boisson[^,;|]{0,25}poudre|instant coffee|cafe soluble|soluble coffee|coffee instant|instant drink|dehydrated beverages)\b")
SYRUP = re.compile(r"\b(syrup|sirop|cordial|squash|juice concentrate|frozen concentrate|concentre de jus|concentrado de zumo)\b")
BREW = re.compile(r"\b(tea bags?|teabags?|loose tea|loose leaf|ground coffee|coffee beans|roast coffee|coffee capsules?|coffee pods?|capsules? de cafe|cafe moulu|grains de cafe|the en sachets?|infusions? en sachets?)\b")
READY = re.compile(r"\b(ready.to.drink|pret a boire|iced tea|ice tea|iced coffee|cold brew|kombucha|coconut water|fruit juices?|jus de fruits?|sodas?|colas?|soft drinks?|carbonated drinks?|bottled waters?|mineral waters?|eaux minerales?|lemonades?|limonades?)\b")
FROM_CONCENTRATE = re.compile(r"(?:juice|jus|zumo).{0,30}(?:from concentrate|a base de concentre|a partir de concentre)")
ALCOHOL = re.compile(r"\b(wines?|vins?|bieres?|beers?|ciders?|cidres?|vodka|whisk[ey]+|spirits|spiritueux|alcoholic beverages|boissons alcoolisees)\b")
SPECIAL = re.compile(r"\b(protein|proteine[es]*|collagen|collagene|electrolytes?|electrolyte|isotonic|isotonique|meal replacement|substitut de repas|whey|mass gainer|nutrition shake|nutritional shake)\b")


def form_metadata(name, tags, category_hold):
    n, t = fold(name), fold(tags)
    text = n + " | " + t
    p, s, b, r, a, specialist = [pat.search(text) for pat in (POWDER, SYRUP, BREW, READY, ALCOHOL, SPECIAL)]
    protected_rtd = FROM_CONCENTRATE.search(n)
    if category_hold:
        group, evidence = "known_category_mismatch_under_review", "finite reviewed exact key"
    elif protected_rtd and not (p or s or b):
        group, evidence = "metadata_ready_to_drink_signal", protected_rtd.group(0)
    elif (p or s or b) and re.search(r"\b(ready.to.drink|pret a boire)\b", text):
        group, evidence = "unknown_or_conflicting_form", "explicit preparation and ready-to-drink signals conflict"
    elif p:
        group, evidence = "explicit_powder_or_dehydrated_preparation", p.group(0)
    elif s:
        group, evidence = "explicit_syrup_cordial_or_concentrate", s.group(0)
    elif b:
        group, evidence = "explicit_brewing_material", b.group(0)
    elif a:
        group, evidence = "alcohol_metadata_signal", a.group(0)
    elif r:
        group, evidence = "metadata_ready_to_drink_signal", r.group(0)
    else:
        group, evidence = "unknown_or_conflicting_form", "no sufficiently specific form metadata"
    return group, evidence, int(bool(specialist)), specialist.group(0) if specialist else ""


def summary(g):
    n = len(g)
    count = lambda col: int(g[col].sum())
    first, retry = count("available_first_attempt"), count("available_retry")
    available = first + retry
    w = int(g.loc[g.available_first_attempt.eq(1) | g.available_retry.eq(1), "nutrition_warning_present"].sum())
    return {"products": n, "m1_eligible": count("m1_eligible"), "missing_m1": count("missing_m1_nutrition"),
            "with_image": count("image_available"), "with_image_pct": 100*count("image_available")/n,
            "successful_ocr_llm": count("existing_successful_ocr_llm"),
            "successful_with_claims": int(g.latest_success_status.eq("success_with_claims").sum()),
            "successful_no_claims": int(g.latest_success_status.eq("success_no_claims").sum()),
            "successful_claim_state_unknown": int(g.latest_success_status.eq("success_claim_state_unknown").sum()),
            "prior_failed_or_unusable": count("prior_failed_or_unusable"),
            "failure_without_success": int((g.prior_failed_or_unusable.eq(1) & g.existing_successful_ocr_llm.eq(0)).sum()),
            "manual_review_hold": count("manual_review_hold"),
            "unprocessed_image_equipped_before_holds": count("unprocessed_image_equipped"),
            "held_among_unprocessed_image_equipped": int((g.unprocessed_image_equipped.eq(1)&g.manual_review_hold.eq(1)).sum()),
            "history_uncertain_without_success": int((g.history_uncertain_evidence.eq(1)&g.existing_successful_ocr_llm.eq(0)).sum()),
            "available_first_attempt": first, "available_retry": retry,
            "available_first_or_retry": available, "available_warning_records": w,
            "available_warning_pct": 100*w/available if available else np.nan,
            "first_attempt_warning_records": int(g.loc[g.available_first_attempt.eq(1), "nutrition_warning_present"].sum()),
            "warning_records_all": count("nutrition_warning_present"),
            "fibre_available": count("fibre_available"),
            "first_attempt_fibre_available": int(g.loc[g.available_first_attempt.eq(1), "fibre_available"].sum())}


def aggregate(frame, keys):
    rows = []
    for values, g in frame.groupby(keys, sort=False, dropna=False):
        if not isinstance(values, tuple):
            values = (values,)
        rows.append({**dict(zip(keys, values)), **summary(g)})
    result = pd.DataFrame(rows)
    order = {"region": {"FR": 0, "UK+IE": 1, "US+CA": 2},
             "country": {"FR": 0, "UK": 1, "IE": 2, "US": 3, "CA": 4},
             "category": {"snacks": 0, "cereals": 1, "dairies": 2, "beverages": 3}}
    return result.sort_values(keys, key=lambda col: col.map(order[col.name]) if col.name in order else col, kind="stable").reset_index(drop=True)


def main():
    frozen, r1, r3 = source_setup()
    print("RUN 05: reading approved regional population and memberships", flush=True)
    base = read(R3 / "regional_product_base.csv")
    if len(base) != 476626 or base.duplicated(KEY).any():
        raise ValueError("Approved regional population changed")
    for col in ["energy_kcal", "protein_100g", "fat_100g", "saturated_fat_100g", "carbs_100g", "sugars_100g", "fiber_100g", "salt_100g"]:
        base[col] = pd.to_numeric(base[col].replace("", np.nan), errors="raise")
    base["m1_eligible"] = base.eligible_M1.astype(int)
    base["missing_m1_nutrition"] = 1 - base.m1_eligible
    base["missing_m1_features"] = base.apply(lambda row: "|".join(f for f, col in FIELDS.items() if pd.isna(row[col])), axis=1)
    if not base.m1_eligible.eq(base[list(FIELDS.values())].notna().all(axis=1).astype(int)).all():
        raise ValueError("M1 eligibility disagrees with required non-NULL features")
    member = read(FOLLOW / "proposed_group_membership.csv")
    definitions = read(FOLLOW / "sampling_grouping_decisions.csv")
    if len(member) != 218115 or member.proposed_group_id.nunique() != 24 or len(definitions) != 11:
        raise ValueError("Approved sampling definitions differ from 11 designs / 24 groups")
    base = base.merge(member[KEY + ["proposed_group_id", "proposed_source", "source_k", "source_cluster_id"]],
                      on=KEY, how="left", validate="one_to_one")
    if not base.proposed_group_id.notna().eq(base.m1_eligible.eq(1)).all():
        raise ValueError("Saved membership does not exactly cover M1 products")
    base["sampling_group_id"] = base.proposed_group_id.fillna(UNASSIGNED)
    base["sampling_group_approval"] = np.where(base.m1_eligible.eq(1), "CHECK04_approved", "no_group_missing_M1")
    context_cols = KEY + ["country", "product_name", "brands", "normalized_brand", "image_url", "image_availability_reason", "warning_types", "warning_summary"]
    context = pd.read_csv(LEDGER01, usecols=[c for c in context_cols if c != "region"], dtype=str, keep_default_na=False, low_memory=False)
    context["region"] = context.country.map(COUNTRY_REGION)
    context = context.drop(columns="country").drop_duplicates(KEY)
    base = base.merge(context, on=KEY, how="left", validate="one_to_one")
    if base.product_name.isna().any():
        raise ValueError("A regional product has no frozen identity context row")
    history_agg, events, inventory, csv_paths = history(base)
    for path in csv_paths:
        frozen[rel(path)] = sha(path)
    base = base.merge(history_agg, on="barcode", how="left", validate="many_to_one")
    for col in ("existing_successful_ocr_llm", "prior_failed_or_unusable", "history_uncertain_evidence"):
        base[col] = base[col].fillna(False).astype(int)
    for col in ("latest_saved_status", "latest_saved_timestamp", "latest_saved_source", "latest_success_status", "latest_success_timestamp",
                "latest_success_source", "latest_success_evidence_image_url", "history_sources"):
        base[col] = base[col].fillna("")
    base["saved_evidence_rows"] = base.saved_evidence_rows.fillna(0).astype(int)
    base.loc[base.latest_saved_status.eq(""), "latest_saved_status"] = "not_processed"
    base["history_newly_recognized_success"] = (base.existing_successful_ocr_llm.eq(1) & ~base.historical_ocr_status.isin(SUCCESS)).astype(int)
    base["prior_success_latest_not_success"] = (base.existing_successful_ocr_llm.eq(1) & ~base.latest_saved_status.isin(SUCCESS)).astype(int)
    register, hold_flags = review_register(base)
    base = base.merge(hold_flags, on=KEY, how="left", validate="one_to_one")
    for col in ("manual_review_hold", "manual_category_mismatch_hold"):
        base[col] = base[col].fillna(False).astype(int)
    for col in ("manual_review_reasons", "manual_review_evidence", "manual_review_provenance"):
        base[col] = base[col].fillna("")
    base["fibre_available"] = base.fiber_100g.notna().astype(int)
    base["nutrition_population"] = np.where(base.m1_eligible.eq(1), "M1_complete_approved_group", "missing_M1_required_nutrition")
    base["unprocessed_image_equipped"] = (base.existing_successful_ocr_llm.eq(0) & base.image_available.eq(1)).astype(int)
    open_pool = base.unprocessed_image_equipped.eq(1) & base.manual_review_hold.eq(0) & base.history_uncertain_evidence.eq(0)
    base["available_first_attempt"] = (open_pool & base.prior_failed_or_unusable.eq(0)).astype(int)
    base["available_retry"] = (open_pool & base.prior_failed_or_unusable.eq(1)).astype(int)
    base["coverage_status"] = np.select([base.existing_successful_ocr_llm.eq(1), base.manual_review_hold.eq(1),
          base.history_uncertain_evidence.eq(1), base.image_available.eq(0), base.available_retry.eq(1)],
          ["already_successful", "manual_review_hold", "history_review_required", "no_image", "retry_available"], default="first_attempt_available")
    base["allocation_readiness"] = np.where(base.missing_m1_nutrition.eq(1), "missing_M1_population_decision_required", "approved_sampling_group")
    print("RUN 05: profiling beverage forms from saved metadata only", flush=True)
    beverage_codes = set(base.loc[base.category.eq("beverages"), "barcode"])
    tags = {}
    with sqlite3.connect(Path(r1["source_database"]).resolve().as_uri() + "?mode=ro", uri=True) as conn:
        for code, raw in conn.execute("SELECT barcode,off_categories FROM products WHERE query_category='beverages'"):
            if code in beverage_codes:
                tags[code] = raw or ""
    if not beverage_codes.issubset(tags):
        raise ValueError("Missing frozen beverage category metadata")
    mask = base.category.eq("beverages")
    beverage = base.loc[mask].copy()
    values = [form_metadata(row.product_name, tags[row.barcode], bool(row.manual_category_mismatch_hold)) for row in beverage.itertuples()]
    form = pd.DataFrame(values, columns=["beverage_form_metadata", "beverage_form_evidence", "beverage_specialist_signal", "beverage_specialist_evidence"], index=beverage.index)
    for col in form:
        base.loc[mask, col] = form[col]
    base.loc[~mask, "beverage_form_metadata"] = "not_beverages"
    for col in ("beverage_form_evidence", "beverage_specialist_evidence"):
        base[col] = base[col].fillna("")
    base["beverage_specialist_signal"] = base.beverage_specialist_signal.fillna(0).astype(int)
    base["legacy_mvp_beverage_view_segment"] = "not_beverage"
    base.loc[mask, "legacy_mvp_beverage_view_segment"] = [beverage_view_segment("beverages", row.product_name, tags[row.barcode]) for row in beverage.itertuples()]
    base["beverage_preparation_identified"] = base.beverage_form_metadata.isin(["explicit_powder_or_dehydrated_preparation", "explicit_syrup_cordial_or_concentrate", "explicit_brewing_material"]).astype(int)
    base["prior_image_url_comparison"] = np.where(base.latest_success_evidence_image_url.eq(""), "unknown_original_image", np.where(base.latest_success_evidence_image_url.eq(base.image_url), "same_url", "different_url"))
    base = base.sort_values(KEY).reset_index(drop=True)
    grouped = base.loc[base.m1_eligible.eq(1)]
    missing = base.loc[base.missing_m1_nutrition.eq(1)]
    coverage = aggregate(grouped, ["region", "category", "sampling_group_id"])
    missing_summary = aggregate(missing, ["region", "category"])
    overall = aggregate(base, ["region", "category"])
    beverage = base.loc[base.category.eq("beverages")]
    beverage_population = aggregate(beverage, ["region", "nutrition_population"])
    forms = aggregate(beverage, ["region", "nutrition_population", "sampling_group_id", "beverage_form_metadata", "beverage_specialist_signal"])
    for col in ("beverage_preparation_identified", "beverage_specialist_signal"):
        extra = beverage.groupby(["region", "nutrition_population"])[col].sum()
        beverage_population = beverage_population.merge(extra.reset_index(), on=["region", "nutrition_population"], validate="one_to_one")
    bridge = read(R3 / "assignment_bridge.csv")
    country_ledger = bridge.merge(base.drop(columns="countries"), on=KEY, how="left", validate="many_to_one")
    country = aggregate(country_ledger, ["region", "country", "category", "sampling_group_id", "nutrition_population"])
    states = base.groupby(["region", "category", "nutrition_population", "coverage_status"], sort=False).size().rename("products").reset_index()
    reconciliation = base.groupby(["historical_ocr_status", "latest_success_status", "existing_successful_ocr_llm", "prior_failed_or_unusable", "history_uncertain_evidence"], dropna=False, sort=False).size().rename("regional_products").reset_index()
    history_regions = base.groupby(["region", "category"], sort=False).agg(regional_products=("barcode", "size"),
        frozen_success=("historical_ocr_status", lambda s: int(s.isin(SUCCESS).sum())),
        refreshed_success=("existing_successful_ocr_llm", "sum"), newly_recognized_success=("history_newly_recognized_success", "sum"),
        prior_failure_evidence=("prior_failed_or_unusable", "sum"), prior_success_latest_not_success=("prior_success_latest_not_success", "sum")).reset_index()
    hold_counts = register.groupby(["region", "category", "disposition", "reason"], sort=False).size().rename("review_reason_rows").reset_index()
    tables = {"candidate_ledger.csv": base, "check_05_remaining_coverage.csv": coverage,
              "check_05_missing_m1_population.csv": missing_summary, "check_05_region_category.csv": overall,
              "check_05_candidate_status_counts.csv": states, "check_05_country_composition.csv": country,
              "check_05_beverage_populations.csv": beverage_population, "check_05_beverage_form_coverage.csv": forms,
              "check_05_history_reconciliation.csv": reconciliation, "check_05_history_by_region_category.csv": history_regions,
              "history_observations.csv": events, "history_source_inventory.csv": inventory,
              "manual_review_register.csv": register, "manual_review_counts_by_reason.csv": hold_counts}
    validate(tables, bridge, member, frozen)
    for name, data in tables.items():
        save(name, data)
    approval = {"status": "CHECK04_sampling_groupings_approved", "approved_by": "Julia, explicit instruction in this conversation",
                "designs": 11, "groups": 24, "regional_grouped_products": 218115,
                "decision_table": rel(FOLLOW / "sampling_grouping_decisions.csv"),
                "decision_table_sha256": sha(FOLLOW / "sampling_grouping_decisions.csv"),
                "memberships": rel(FOLLOW / "proposed_group_membership.csv"), "memberships_sha256": sha(FOLLOW / "proposed_group_membership.csv"),
                "scope": "sampling groups only; no final nutritional/market segments, quotas or sample approved",
                "original_consolidated_report_snapshot": rel(FROZEN_R4DOC), "original_report_sha256": sha(FROZEN_R4DOC),
                "updated_consolidated_report": rel(R4DOC), "updated_report_sha256": sha(R4DOC)}
    (OUT / "check_04_approval.json").write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    write_report(tables)
    manifest = {"run": "RUN_05_CANDIDATE_UNIVERSE_V1", "status": "CHECK 05 — Pending review", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "script": rel(Path(__file__).resolve()), "script_sha256": sha(Path(__file__).resolve()), "source_release": r3["source_release"],
                "protected_source_hashes": frozen, "document_snapshot_exception": {rel(R4DOC): rel(FROZEN_R4DOC)},
                "approval_sha256": sha(OUT / "check_04_approval.json"),
                "populations": {"regional_products": len(base), "grouped_m1": len(grouped), "missing_m1": len(missing), "country_assignments": len(bridge), "approved_groups": 24},
                "rules": {"successful_history": "union of valid success evidence, including no claims; later failures do not erase earlier success",
                          "success_claims_csv": "existing Stage 11 PACK_CLAIM_FIELDS; explicit llm success and completed extraction; missing/invalid booleans are not false",
                          "latest_evidence": "explicit ISO/mixed and compact YYYYMMDD_HHMMSS timestamp parsing; naive timestamps ordered as recorded without verified timezone; tie priority working DB > normalized CSV > other CSV > checkpoint > frozen history; affects descriptive latest status, not union-of-success coverage",
                          "review_holds": "finite exact regional keys from prior reviewed evidence and explicit manual review policy; no warning/nutrient threshold gate",
                          "available_first_or_retry": "no successful history, image available, no manual hold or unresolved history; missing-M1 population remains separately undecided",
                          "beverage_forms": "conservative explicit saved name/tag signals; diagnostic only, no nutrient-based inference or eligibility effect",
                          "country_counts": "assignment counts; multi-country products appear in both countries and must not be summed as regional unique products"},
                "outputs": {name: {"rows": len(data), "sha256": sha(OUT / name)} for name, data in tables.items()},
                "report": {"path": rel(REPORT), "sha256": sha(REPORT)},
                "validation": {"source_files_unchanged": len(frozen), "no_new_exclusions": True, "no_sample_selected": True, "image_requests": 0, "ocr_llm_calls": 0}}
    (OUT / "run_05_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["populations"]), flush=True)
    print(f"CHECK 05: {REPORT}", flush=True)


def validate(t, bridge, member, frozen):
    b = t["candidate_ledger.csv"]
    if len(b) != 476626 or b.duplicated(KEY).any() or b.m1_eligible.sum() != 218115 or b.missing_m1_nutrition.sum() != 258511:
        raise ValueError("Population balance failed")
    selected = b.loc[b.m1_eligible.eq(1), KEY + ["sampling_group_id"]].merge(member[KEY + ["proposed_group_id"]], on=KEY, validate="one_to_one")
    if not selected.sampling_group_id.eq(selected.proposed_group_id).all():
        raise ValueError("An approved sampling group changed")
    if len(t["check_05_remaining_coverage.csv"]) != 24 or len(t["check_05_missing_m1_population.csv"]) != 11:
        raise ValueError("Coverage stratum count mismatch")
    if len(bridge) != 477917 or b.country_assignment_count.sum() != len(bridge):
        raise ValueError("Country bridge does not balance")
    if ((b.region == "US+CA") & b.category.eq("dairies")).any():
        raise ValueError("US/CA dairy unexpectedly included")
    if (b.loc[b.available_first_attempt.eq(1)|b.available_retry.eq(1), ["manual_review_hold", "history_uncertain_evidence", "existing_successful_ocr_llm"]].to_numpy() != 0).any():
        raise ValueError("Available candidates violate review/history status")
    frozen_success = b.historical_ocr_status.isin(SUCCESS)
    if not b.loc[frozen_success, "existing_successful_ocr_llm"].eq(1).all():
        raise ValueError("A historical success was lost")
    if b.fibre_available.sum() != b.fiber_100g.notna().sum():
        raise ValueError("NULL fibre was misclassified")
    if t["check_05_beverage_form_coverage.csv"].products.sum() != b.category.eq("beverages").sum():
        raise ValueError("Beverage form partition does not balance")
    for name, digest in frozen.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Protected source changed during RUN 05: {name}")


def write_report(t):
    b = t["candidate_ledger.csv"]
    c = t["check_05_remaining_coverage.csv"]
    missing = t["check_05_missing_m1_population.csv"]
    regions = t["check_05_history_by_region_category.csv"]
    inv = t["history_source_inventory.csv"]
    events = t["history_observations.csv"]
    scoped = events.loc[events.in_current_regional_population.eq(1)]
    lines = ["# RUN 05 — Candidate universe and remaining OCR/LLM coverage", "", "**CHECK 05 — Pending review. CHECK 04 sampling groups are approved.**", "",
             "The ledger retains all 476,626 corrected physically valid regional products in the 11-stratum main scope. Exactly 218,115 products use the approved 24 saved sampling groups; 258,511 lack M1-required nutrition and remain separately identified. US/CA dairy remains excluded. No quotas, OCR sample, image preflight or paid processing were performed.", "",
             "## Candidate status and denominators", "",
             "Existing successful processing includes completed, valid no-claim outcomes. Any trustworthy historical success makes a product already processed for this new-processing universe, even when another saved attempt failed. Image availability is the preserved RUN 01 structural URL flag; URL reachability and image usability were not tested. Warnings and identified preparations are not eligibility gates. Finite manual-review holds are candidate holds, not removals from the source or ledger.", "",
             "| Population | Products | With image | Already successful | Unprocessed + image before holds | Available first attempt | Available retry | Manual holds (all products) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, g in (("Approved M1 groups", b.loc[b.m1_eligible.eq(1)]), ("Missing M1 — allocation undecided", b.loc[b.missing_m1_nutrition.eq(1)]), ("Full regional population", b)):
        s = summary(g)
        lines.append(f"| {name} | {s['products']:,} | {s['with_image']:,} | {s['successful_ocr_llm']:,} | {s['unprocessed_image_equipped_before_holds']:,} | {s['available_first_attempt']:,} | {s['available_retry']:,} | {s['manual_review_hold']:,} |")
    lines += ["", "Available first-attempt and retry counts require no successful history, an available image, no manual hold and no unresolved history. Retry counts are reported separately for allocation approval; they are not authorized processing. Missing-M1 products satisfying these conditions are potential candidates only: their allocation status remains undecided. Manual holds and other reasons may overlap; the product-level coverage_status assigns one mutually exclusive primary status so population totals are not double-counted.", "",
              "## Approved-group remaining coverage", "",
              "These are sampling groups, not final nutritional/market segments or validated product-form classifications. Group shares are not market shares.", "",
              "| Region | Category | Group | Products | Prior success | Unprocessed + image | First attempt | Retry | Holds among unprocessed + image | Available warning % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in c.itertuples():
        warning = f"{r.available_warning_pct:.1f}%" if pd.notna(r.available_warning_pct) else "—"
        lines.append(f"| {r.region} | {r.category} | {r.sampling_group_id} | {r.products:,} | {r.successful_ocr_llm:,} | {r.unprocessed_image_equipped_before_holds:,} | {r.available_first_attempt:,} | {r.available_retry:,} | {r.held_among_unprocessed_image_equipped:,} | {warning} |")
    lines += ["", "## Products without M1-complete nutrition", "",
              "Missing is not zero. The ledger names each missing required feature, preserves observed fibre and raw nutrient values, and assigns no nutritional group to these products.", "",
              "| Region | Category | Missing-M1 products | With image | Prior success | First attempt potential | Retry potential |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for r in missing.itertuples():
        lines.append(f"| {r.region} | {r.category} | {r.products:,} | {r.with_image:,} | {r.successful_ocr_llm:,} | {r.available_first_attempt:,} | {r.available_retry:,} |")
    lines += ["", "## Processing-history reconciliation", "",
              f"Refreshed history inspected the current working-database product_analysis rows and {len(inv)-2} saved result/checkpoint CSVs, alongside frozen pre-masking RUN 01 history. The release database's masked claim fields were not treated as proof of no prior processing. In the regional population, prior-success coverage changes from {int(regions.frozen_success.sum()):,} to {int(regions.refreshed_success.sum()):,}; {int(regions.newly_recognized_success.sum()):,} regional assignments gain recognized historical success. This is reconciliation of saved work, not new OCR processing.", "",
              "| Region | Category | Frozen prior success | Refreshed prior success | Newly recognized | Prior failed/unusable evidence |",
              "|---|---|---:|---:|---:|---:|"]
    for r in regions.itertuples():
        lines.append(f"| {r.region} | {r.category} | {r.frozen_success:,} | {r.refreshed_success:,} | {r.newly_recognized_success:,} | {r.prior_failure_evidence:,} |")
    lines += ["", f"The saved history contains {len(scoped):,} evidence rows for {scoped.barcode.nunique():,} distinct in-scope barcode strings. Rows across databases, raw/normalized results and checkpoints can describe the same attempt and must not be summed as unique paid attempts. Completed CSV rows require explicit llm_status=success and extraction_status=completed; claim/no-claim classification reuses Stage 11's boolean claim fields. NULL or absent booleans are not false. Latest status is descriptive only: event timestamp and recorded source tie priorities resolve display order, while any prior valid success remains preserved. Existing success is historical barcode-level coverage, not certification that the current image/evidence version is unchanged.", "",
              f"Among refreshed successful regional records, {b.latest_success_status.eq('success_with_claims').sum():,} have a latest recognized success with claims, {b.latest_success_status.eq('success_no_claims').sum():,} with no claims, and {b.latest_success_status.eq('success_claim_state_unknown').sum():,} with unknown claim state. One barcode, `5000119126139` (FR and UK+IE snacks), gains recognized valid no-claim history from `vision_results_mainstream_uk_ie_targeted_en.csv`; an ambiguous stored status does not erase that successful saved result.", "",
              f"Stage timestamps in compact YYYYMMDD_HHMMSS form are explicitly parsed alongside ISO/mixed dates. Naive timestamps have no independently verified timezone and are ordered as recorded only for descriptive latest-status fields. {scoped.loc[scoped.timestamp_parse_state.eq('unparsed_original')].shape[0]:,} in-scope evidence rows have a nonempty timestamp that remains unparsed. Timestamp ordering does not determine whether any valid success exists.", "",
              "## Beverage populations and remaining candidates", "",
              "| Region | Full physically valid products | M1 eligible | M1 % | Missing M1 |",
              "|---|---:|---:|---:|---:|"]
    beverage = b.loc[b.category.eq("beverages")]
    for region, g in beverage.groupby("region", sort=False):
        lines.append(f"| {region} | {len(g):,} | {g.m1_eligible.sum():,} | {100*g.m1_eligible.mean():.2f}% | {g.missing_m1_nutrition.sum():,} |")
    lines += ["", "FR and UK+IE each use one approved broad-M1 random group. US+CA retains three provisional groups, including specialist preparations with elevated warning/extreme rates. The table below reports each group's remaining pool without excluding those preparations or warning-flagged records.", "",
              "| Region / group | Unprocessed + image before holds | Available first attempt | Available retry | Available warning n (%) |",
              "|---|---:|---:|---:|---|"]
    for r in c.loc[c.category.eq("beverages")].itertuples():
        warning = f"{r.available_warning_pct:.1f}%" if pd.notna(r.available_warning_pct) else "—"
        lines.append(f"| {r.region} / {r.sampling_group_id} | {r.unprocessed_image_equipped_before_holds:,} | {r.available_first_attempt:,} | {r.available_retry:,} | {r.available_warning_records:,} ({warning}) |")
    lines += ["", "### Saved-metadata evidence for preparation and specialist forms", "",
              "Form profiling is diagnostic only. It uses explicit names/tags for powders/dehydrated mixes, syrups/cordials/concentrates and brewing materials; ready-to-drink juice 'from concentrate' is protected. Generic beverage/plant-based ancestry and unusual nutrient values do not establish form. Specialist protein/collagen/electrolyte/meal-replacement wording is an independent, potentially overlapping signal. Unknown/conflicting form is retained. The existing MVP beverage split is also carried for audit, but its combined preparation/alcohol category is not treated as verified concentrated form.", "",
              "| Region | Nutrition population | Products | Explicit preparation forms | Specialist wording/tag signal | Unknown/conflicting form |",
              "|---|---|---:|---:|---:|---:|"]
    for (region, pop), g in beverage.groupby(["region", "nutrition_population"], sort=False):
        lines.append(f"| {region} | {pop} | {len(g):,} | {g.beverage_preparation_identified.sum():,} | {g.beverage_specialist_signal.sum():,} | {g.beverage_form_metadata.eq('unknown_or_conflicting_form').sum():,} |")
    lines += ["", "See the beverage-form coverage CSV for preparation types, unknown form and specialist signals within each approved group and the separate missing-M1 populations, including remaining candidates, holds and warning shares. These metadata signals are not validated pack-form classifications and do not define new sampling groups.", "",
              "## Country composition and manual review", "",
              "The country-composition CSV preserves FR, UK, IE, US and CA assignments within each approved group and missing-M1 population. A product tagged in both countries is counted in both country rows but once in its regional group; country totals must not be summed as regional unique products.", "",
              "| Region | Country | Category | Country products | M1 products | First-attempt potential in approved groups | First-attempt potential missing M1 |",
              "|---|---|---|---:|---:|---:|---:|"]
    country = t["check_05_country_composition.csv"]
    for (region, nation, category), g in country.loc[country.region.ne("FR")].groupby(["region", "country", "category"], sort=False):
        first_grouped = int(g.loc[g.nutrition_population.eq("M1_complete_approved_group"), "available_first_attempt"].sum())
        first_missing = int(g.loc[g.nutrition_population.eq("missing_M1_required_nutrition"), "available_first_attempt"].sum())
        lines.append(f"| {region} | {nation} | {category} | {g.products.sum():,} | {g.m1_eligible.sum():,} | {first_grouped:,} | {first_missing:,} |")
    lines += ["", f"The exact-key review register has {len(t['manual_review_register.csv']):,} reason rows affecting {b.manual_review_reasons.ne('').sum():,} regional products; {b.manual_review_hold.sum():,} products have a candidate hold. Multiple reasons can apply to one product, so reason-row counts are not unique held-product counts. High-confidence scope mismatches and suspect nutrition entries are held for candidate review; product-form uncertainty without sufficient evidence is recorded separately as a flag. Genuine powders, specialist preparations, warning flags and high z-scores do not automatically create holds.", "",
              "## Questions remaining before allocation", "",
              "1. Decide whether and how to allocate to the separately reported missing-M1 population, particularly US+CA beverages; it has no approved nutritional grouping.",
              "2. Decide whether previously failed/unusable products are eligible for a retry allocation. First-attempt and retry pools remain separate.",
              "3. Resolve finite manual holds and any unclassifiable historical observations before those records enter an executable sample.",
              "4. Set country representation within merged regions, quotas, success targets and cost ceiling. Country assignments and distinct barcode/image evidence are not interchangeable paid-work units.",
              "5. Image reachability/usability, evidence-version-aware checkpoints and merge readiness remain later execution work. Historical success is not a freshness check; this new-processing pool does not automatically schedule reruns for changed products.", "",
              "## Supporting outputs", ""]
    labels = {"candidate_ledger.csv": "Full product-level candidate ledger",
              "check_05_remaining_coverage.csv": "24-group remaining-coverage matrix",
              "check_05_missing_m1_population.csv": "Missing-M1 populations",
              "check_05_region_category.csv": "Full region-category summaries",
              "check_05_candidate_status_counts.csv": "Mutually exclusive candidate-status counts",
              "check_05_country_composition.csv": "Country composition within groups and missing-M1 populations",
              "check_05_beverage_populations.csv": "Full versus M1 beverage populations",
              "check_05_beverage_form_coverage.csv": "Beverage form/specialist evidence and remaining coverage",
              "check_05_history_reconciliation.csv": "Frozen versus refreshed history transitions",
              "check_05_history_by_region_category.csv": "History reconciliation by stratum",
              "history_observations.csv": "Saved history observations with source and row provenance",
              "history_source_inventory.csv": "History source inventory and checksums",
              "manual_review_register.csv": "Finite exact-key review register",
              "manual_review_counts_by_reason.csv": "Review reason counts, potentially overlapping",
              "manual_review_policy.json": "Explicit manual-review policy",
              "check_04_approval.json": "CHECK 04 approval and exact source hashes",
              "run_05_manifest.json": "RUN 05 configuration, source hashes and output hashes"}
    for name, label in labels.items():
        lines.append(f"- [{label}](run_05_v1/{name})")
    lines += ["", "**CHECK 05: Pending review. Stop before quotas, sample selection, image preflight and paid OCR/LLM processing.**", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace-own-draft", action="store_true", help="Replace only hash-verified outputs of this same unreviewed RUN 05 draft")
    REPLACE_OWN_DRAFT = parser.parse_args().replace_own_draft
    main()
