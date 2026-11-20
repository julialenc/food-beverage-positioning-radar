"""Bounded RUN 06B Step 3 using existing CSVs and cached evidence only.

prepare: check cached bytes without decoding, identify risks and duplicate
evidence, and render exactly 48 unique review images as six contact sheets.
finalize: record the agent's visual decisions; no additional image opens.
Neither command changes candidates, reserves, policy, prompts or ownership.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import re
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/segmentation"
OUT = BASE / "run_06b_step3_v1"
STEP2 = BASE / "run_06b_step2_v1"
CACHE = (BASE / "run_06b_v1/image_evidence").resolve()
REPORT = "RUN 06B - Step 3 image evidence review.md"
INPUTS = [
    "run_06b_step2_v1/manifest.json", "run_06b_step2_v1/candidate_selected_manifest.csv",
    "run_06b_step2_v1/eligibility_reconciled_reserves.csv", "run_06b_step2_v1/secondary_coverage_links_frozen.csv",
    "run_06b_step2_v1/secondary_link_step2_annotations.csv", "run_06b_step2_v1/blocked_selected_register.csv",
    "run_06b_step2_v1/group_reconciliation.csv", "run_06b_v2/run_06b_manifest.json",
    "run_06b_v2/image_evidence_inventory.csv", "run_06b_v2/image_preflight_products.csv",
    "run_06b_v2/image_preflight_urls.csv", "run_06b_v2/evidence_equivalence_review.csv",
    "run_06b_v2/core_configuration_proposal.json", "beverage_05a_v1/suspected_products_review.csv",
    "beverage_05d_identity_decisions.csv", "beverage_final_v1/eligibility_decisions.csv",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save_csv(name, rows, fields=None):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_inputs():
    blobs = {name: (BASE / name).read_bytes() for name in INPUTS}
    hashes = {name: sha(value) for name, value in blobs.items()}
    step2 = json.loads(blobs[INPUTS[0]])
    for filename in ["candidate_selected_manifest.csv", "eligibility_reconciled_reserves.csv",
                     "secondary_coverage_links_frozen.csv", "secondary_link_step2_annotations.csv",
                     "blocked_selected_register.csv", "group_reconciliation.csv"]:
        assert hashes["run_06b_step2_v1/" + filename] == step2["outputs_sha256"][filename]
    v2 = json.loads(blobs["run_06b_v2/run_06b_manifest.json"])
    for name in INPUTS:
        if name.startswith("run_06b_v2/") and not name.endswith("run_06b_manifest.json"):
            assert hashes[name] == v2["outputs_sha256"]["presentations/segmentation/" + name]
    selected = load_csv(STEP2 / "candidate_selected_manifest.csv")
    reserves = load_csv(STEP2 / "eligibility_reconciled_reserves.csv")
    rows = []
    for role, source in [("selected", selected), ("reserve", reserves)]:
        for index, row in enumerate(source, 1):
            rows.append({**row, "step3_role": role, "step3_source_row": str(index),
                         "case_key": json.dumps([role, row["barcode"], row["region"], row["category"]], separators=(",", ":"))})
    return blobs, hashes, rows


def family(url):
    # Same OFF product path, image language and revision; no identity alias merge.
    match = re.search(r"(images/products/[0-9/]+/front_[a-z_]+\.\d+)\.(?:\d+|full)\.", url)
    return match.group(1) if match else ""


def product_path(url):
    match = re.search(r"images/products/([0-9/]+)/", url)
    return match.group(1).replace("/", "") if match else ""


def eligible(row):
    return row["step2_eligibility_qualified"] == "1"


def prepare():
    if OUT.exists():
        raise FileExistsError(f"Preserve existing package: {OUT}")
    blobs, hashes, rows = load_inputs()
    inventory = {r["image_sha256"]: r for r in load_csv(BASE / "run_06b_v2/image_evidence_inventory.csv")}
    url_records = load_csv(BASE / "run_06b_v2/image_preflight_urls.csv")
    product_records = load_csv(BASE / "run_06b_v2/image_preflight_products.csv")
    product_index = defaultdict(list)
    for r in product_records:
        product_index[(r["barcode"], r["region"], r["category"])].append(r)
    urls = {r["requested_url"]: r for r in url_records}
    families = defaultdict(list)
    for r in url_records:
        if r["status"] == "technical_pass" and r["image_sha256"] and family(r["requested_url"]):
            families[family(r["requested_url"])].append(r)
    active = [r for r in rows if eligible(r)]
    raw_groups = defaultdict(list)
    for r in active:
        raw_groups[r["image_sha256"]].append(r)
    suspicious = {(r["barcode"], r["region"]): r for r in load_csv(BASE / "beverage_05a_v1/suspected_products_review.csv")}
    old_identity = {(r["barcode_exact_text"], r["region"]): r for r in load_csv(BASE / "beverage_05d_identity_decisions.csv")}
    configs = json.loads(blobs["run_06b_v2/core_configuration_proposal.json"])
    # Only bytes are read here, never decoded. Each unique referenced cache file once.
    integrity, integrity_map = [], {}
    refs = defaultdict(list)
    for r in rows:
        refs[(r["immutable_image_path"], r["image_sha256"])].append(r)
    for (relative, expected), references in refs.items():
        path = (ROOT / relative).resolve()
        safe = path.is_relative_to(CACHE)
        exists = safe and path.is_file()
        actual = sha(path.read_bytes()) if exists else ""
        inv = inventory.get(expected)
        size = path.stat().st_size if exists else 0
        valid = bool(exists and actual == expected and inv and inv["path"] == relative
                     and int(inv["bytes"]) == size and all(int(r["image_bytes"]) == size for r in references))
        result = dict(immutable_image_path=relative, expected_image_sha256=expected, actual_image_sha256=actual,
                      cache_exists=exists, file_bytes=size, inventory_matches=bool(inv and inv["path"] == relative),
                      cache_integrity="PASS" if valid else "HOLD", referenced_rows=len(references))
        integrity.append(result)
        integrity_map[(relative, expected)] = result
    assessments, alternatives, risk_rows = [], [], []
    for row in rows:
        cache = integrity_map[(row["immutable_image_path"], row["image_sha256"])]
        prior = product_index[(row["barcode"], row["region"], row["category"])]
        fields = ["image_sha256", "immutable_image_path", "status", "http_status", "width", "height",
                  "image_bytes", "decoded_rgb_sha256", "original_image_url", "requested_url", "resolved_url"]
        preflight_match = any(all(r[k] == row[k] for k in fields) for r in prior)
        url = urls.get(row["requested_url"])
        url_match = bool(url and all(url[k] == row[k] for k in fields if k != "original_image_url"))
        tech = cache["cache_integrity"] == "PASS" and preflight_match and url_match and row["status"] == "technical_pass"
        width, height = int(row["width"]), int(row["height"])
        risks, score = [], 0
        if min(width, height) < 60:
            risks.append("very_narrow_recorded_dimension_under_60_triage_only"); score += 100
        elif min(width, height) < 100:
            risks.append("narrow_recorded_dimension_under_100_triage_only"); score += 55
        if max(width, height) / max(1, min(width, height)) > 6:
            risks.append("extreme_aspect_ratio_triage_only"); score += 65
        if width * height < 30000:
            risks.append("small_recorded_pixel_area_triage_only"); score += 35
        if not row["prompt_product_name"].strip():
            risks.append("missing_reference_product_name"); score += 30
        if not row["prompt_brand"].strip():
            risks.append("missing_reference_brand"); score += 5
        lang = re.search(r"/front_([a-z]+)", row["requested_url"])
        language = lang.group(1) if lang else "unknown"
        if language != ("fr" if row["region"] == "FR" else "en"):
            risks.append("image_language_tag_differs_from_regional_profile_not_visual_proof"); score += 10
        if len(raw_groups.get(row["image_sha256"], [])) > 1:
            risks.append("identical_bytes_shared_with_other_eligible_record"); score += 15
        known = suspicious.get((row["barcode"], row["region"])) if row["category"] == "beverages" else None
        identity = old_identity.get((row["barcode"], row["region"])) if row["category"] == "beverages" else None
        if known:
            risks.append("previous_beverage_review_exists_locked_decision_preserved"); score += 90
        if not tech:
            risks.append("cache_or_saved_preflight_provenance_mismatch"); score += 200
        available_alternatives = []
        for alt in families.get(family(row["requested_url"]), []):
            alt_path = (ROOT / alt["immutable_image_path"]).resolve()
            if (int(alt["width"]) * int(alt["height"]) > width * height and alt["image_sha256"] != row["image_sha256"]
                    and alt_path.is_relative_to(CACHE) and alt_path.is_file()):
                available_alternatives.append(alt)
                alternatives.append(dict(case_key=row["case_key"], barcode=row["barcode"], region=row["region"],
                    recorded_requested_url=alt["requested_url"], cached_alternative_path=alt["immutable_image_path"],
                    cached_alternative_sha256=alt["image_sha256"], recorded_width=alt["width"], recorded_height=alt["height"],
                    status="saved_same_image_revision_larger_variant_not_adopted_or_visually_reviewed"))
        assessment = dict(case_key=row["case_key"], role=row["step3_role"], source_row=row["step3_source_row"],
            barcode=row["barcode"], region=row["region"], category=row["category"], sampling_group_id=row["sampling_group_id"],
            countries=row["countries"], country_cell=row["country_cell"], accounting_component=row["accounting_component"],
            step2_eligibility_qualified=row["step2_eligibility_qualified"], image_sha256=row["image_sha256"],
            immutable_image_path=row["immutable_image_path"], cache_integrity=cache["cache_integrity"],
            recorded_http_status=row["http_status"], recorded_decoding_status=row["status"],
            recorded_width=width, recorded_height=height, saved_product_preflight_matches=preflight_match,
            saved_url_preflight_matches=url_match, original_image_url=row["original_image_url"], requested_url=row["requested_url"],
            resolved_url=row["resolved_url"], front_panel_metadata_hint=row["front_panel_metadata_hint"],
            existing_usability_status=row["usability_review_status"], technical_validity="valid_saved_preflight_and_verified_cache" if tech else "unresolved_hold",
            image_language_metadata=language, available_cached_larger_variants=len(available_alternatives),
            triage_score=score, triage_flags=" | ".join(risks), previously_recorded_issue=known["evidence"] if known else "",
            previously_recorded_identity_finding=identity["image_and_source_finding"] if identity else "",
            step2_beverage_status=row.get("step2_beverage_status", ""),
            visual_review_status="unreviewed", image_disposition="hold_technical_evidence_mismatch" if not tech else "unresolved_unreviewed_front_usability",
            execution_authorized="False")
        assessments.append(assessment)
        if risks:
            risk_rows.append(assessment)
    assessment_map = {r["case_key"]: r for r in assessments}
    # Two review-only images per approved group. Preserve source order for ties.
    # First: highest-risk selected candidate. Second: highest-risk qualified
    # reserve, falling back to another selected candidate if no reserve exists.
    group_order = [r["sampling_group_id"] for r in load_csv(STEP2 / "group_reconciliation.csv")]
    reviewed_hashes, review = set(), []
    def rank(r):
        a = assessment_map[r["case_key"]]
        return -a["triage_score"], int(r["width"]) * int(r["height"]), int(r["step3_source_row"])
    for group in group_order:
        for which in range(2):
            pool = [r for r in active if r["sampling_group_id"] == group
                    and r["step3_role"] == ("selected" if which == 0 else "reserve")
                    and r["image_sha256"] not in reviewed_hashes
                    and assessment_map[r["case_key"]]["cache_integrity"] == "PASS"]
            if not pool:
                pool = [r for r in active if r["sampling_group_id"] == group and r["image_sha256"] not in reviewed_hashes
                        and assessment_map[r["case_key"]]["cache_integrity"] == "PASS"]
            chosen = sorted(pool, key=rank)[0]
            reviewed_hashes.add(chosen["image_sha256"])
            review.append({"review_id": f"V{len(review)+1:02}", **assessment_map[chosen["case_key"]],
                "product_name": chosen["prompt_product_name"], "brand": chosen["prompt_brand"],
                "review_reason": "highest_metadata_risk_selected_in_group" if which == 0 else "highest_metadata_risk_qualified_reserve_or_selected_fallback"})
    assert len(review) == len(reviewed_hashes) == 48 and len(group_order) == 24

    pair_groups = defaultdict(list)
    for r in active:
        pair_groups[("identical_image_bytes", r["image_sha256"])].append(r)
        pair_groups[("identical_saved_decoded_pixels", r["decoded_rgb_sha256"])].append(r)
        if family(r["requested_url"]):
            pair_groups[("same_off_image_revision_family", family(r["requested_url"]))].append(r)
    pairs, seen = [], set()
    for (basis, value), members in pair_groups.items():
        if not value or len(members) < 2:
            continue
        for a, z in itertools.combinations(members, 2):
            pair_key = tuple(sorted((a["case_key"], z["case_key"])))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            same_bytes = a["image_sha256"] == z["image_sha256"]
            profile_a, profile_b = configs["regional_profiles"][a["region"]], configs["regional_profiles"][z["region"]]
            same_profile = profile_a == profile_b
            same_context = all(a[k] == z[k] for k in ["prompt_product_name", "prompt_brand", "category"])
            pairs.append(dict(pair_id=f"D{len(pairs)+1:04}", basis=basis,
                left_role=a["step3_role"], left_barcode=a["barcode"], left_region=a["region"], left_category=a["category"],
                left_group=a["sampling_group_id"], left_countries=a["countries"], left_source_row=a["step3_source_row"],
                right_role=z["step3_role"], right_barcode=z["barcode"], right_region=z["region"], right_category=z["category"],
                right_group=z["sampling_group_id"], right_countries=z["countries"], right_source_row=z["step3_source_row"],
                left_image_sha256=a["image_sha256"], right_image_sha256=z["image_sha256"], identical_image_bytes=same_bytes,
                identical_saved_decoded_pixels=a["decoded_rgb_sha256"] == z["decoded_rgb_sha256"],
                identical_exact_barcode=a["barcode"] == z["barcode"],
                identical_source_product_path=product_path(a["original_image_url"]) == product_path(z["original_image_url"]),
                leading_zero_alias_signal_only=a["barcode"] != z["barcode"] and a["barcode"].lstrip("0") == z["barcode"].lstrip("0"),
                identical_reference_context=same_context, left_prompt_profile=profile_a["profile"], right_prompt_profile=profile_b["profile"],
                left_prompt_sha256=profile_a["prompt_sha256"], right_prompt_sha256=profile_b["prompt_sha256"],
                identical_regional_profile_proposal=same_profile, provider_configuration_verified="False",
                potentially_equivalent_paid_work=("possible_same_bytes_profile_and_context_pending_provider_and_identity_review"
                    if same_bytes and same_profile and same_context else "not_established_different_profile_context_or_image_variant"),
                possible_ocr_reuse="same_bytes_only_pending_actual_ocr_options_and_ledger_review" if same_bytes else "unresolved_image_variant",
                ownership_finalized="False", history_refreshed="False"))
    known80 = [r for r in pairs if r["identical_image_bytes"] and r["left_role"] == r["right_role"] == "selected"]
    assert len(known80) == 80
    blocked = {r["slot_id"]: r for r in load_csv(STEP2 / "blocked_selected_register.csv")}
    owner_issues = []
    for index, link in enumerate(load_csv(STEP2 / "secondary_coverage_links_frozen.csv"), 1):
        if link["owner_slot_id"] in blocked:
            original = blocked[link["owner_slot_id"]]
            owner_issues.append(dict(source_link_row=index, **link, owner_barcode=original["barcode"], owner_region=original["region"],
                owner_category=original["category"], owner_locked_status=original["step2_beverage_status"],
                owner_locked_reason=original["step2_beverage_reason"], owner_decision_source=original["step2_beverage_decision_source"],
                action="retain_link_but_do_not_credit_coverage_or_reassign_owner_in_step3", ownership_reassigned="False"))
    assert len(owner_issues) == 13
    OUT.mkdir()
    (OUT / ".gitignore").write_text("# Local product/image review evidence; no publication approval.\n*\n", encoding="utf-8")
    save_csv("cache_integrity.csv", integrity)
    save_csv("image_evidence_assessment_previsual.csv", assessments)
    save_csv("metadata_risk_register.csv", risk_rows)
    save_csv("cached_higher_resolution_alternatives.csv", alternatives, fields=["case_key", "barcode", "region", "recorded_requested_url",
        "cached_alternative_path", "cached_alternative_sha256", "recorded_width", "recorded_height", "status"])
    save_csv("visual_review_manifest.csv", review)
    save_csv("duplicate_evidence_exceptions.csv", pairs)
    save_csv("secondary_owner_exceptions.csv", owner_issues)
    (OUT / "secondary_coverage_links_frozen.csv").write_bytes(blobs["run_06b_step2_v1/secondary_coverage_links_frozen.csv"])
    save_json("review_protocol.json", dict(maximum_unique_images=48, review_images=48, groups=24,
        selection="Deterministic review-only risk triage: two distinct cached images per group; selected then qualified reserve, selected fallback. No OCR sample draw.",
        triage="Scores in source code prioritize narrow dimensions/aspect, small area, missing identity metadata, prior issues, duplicate bytes and language tags; these are review priorities, never exclusion rules.",
        image_reason_exclusion="Only direct visual confirmation of unsuitable evidence; unresolved identity conflicts held.",
        unreviewed="Unresolved; technical validity and front URL naming do not establish front-pack suitability.",
        no_statistical_accuracy_claim=True, review_scope="Agent visual inspection of cached evidence only; printed GTIN not independently verified."))
    save_json("preparation.json", dict(status="pending_visual_review", source_sha256=hashes, rows=len(rows),
        eligible_rows=len(active), unique_cache_references=len(integrity), cache_failures=sum(r["cache_integrity"] != "PASS" for r in integrity),
        technical_unresolved_rows=sum(r["technical_validity"] == "unresolved_hold" for r in assessments),
        pair_counts=dict(Counter(r["left_role"] + "_" + r["right_role"] for r in pairs)),
        pair_bases=dict(Counter(r["basis"] for r in pairs)), owner_exceptions=13, reserved_review_unique_hashes=48))
    render_review_sheets(review)
    assert hashes == {name: sha((BASE / name).read_bytes()) for name in INPUTS}
    print((OUT / "preparation.json").read_text())
    print("CONTACT_SHEETS", *[str(p) for p in sorted((OUT / "review_sheets").glob("*.jpg"))], sep="\n")


def render_review_sheets(review):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    sheet_dir = OUT / "review_sheets"
    sheet_dir.mkdir()
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), 15) if font_path.exists() else ImageFont.load_default()
    small = ImageFont.truetype(str(font_path), 12) if font_path.exists() else ImageFont.load_default()
    for page in range(6):
        sheet = Image.new("RGB", (1600, 1200), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for position, row in enumerate(review[page*8:(page+1)*8]):
            x, y = (position % 4) * 400, (position // 4) * 600
            draw.rectangle((x+2, y+2, x+397, y+597), fill="white", outline="#888888")
            label = f"{row['review_id']}  {row['role']}  {row['barcode']}\n{row['sampling_group_id']}\n{row['recorded_width']}x{row['recorded_height']} risk={row['triage_score']}"
            draw.multiline_text((x+10, y+8), label, fill="black", font=font, spacing=3)
            name = row["product_name"] or "[source product name missing]"
            draw.multiline_text((x+10, y+81), "\n".join(textwrap.wrap(name, 43)[:2]), fill="black", font=small)
            path = ROOT / row["immutable_image_path"]
            with Image.open(path) as source:
                picture = ImageOps.exif_transpose(source).convert("RGB")
                picture.thumbnail((380, 470), Image.Resampling.LANCZOS)
                sheet.paste(picture, (x + (400-picture.width)//2, y+120+(470-picture.height)//2))
        sheet.save(sheet_dir / f"review_{page+1:02}.jpg", quality=94)


def finalize():
    _, hashes, rows = load_inputs()
    preparation = json.loads((OUT / "preparation.json").read_text())
    assert hashes == preparation["source_sha256"]
    review = load_csv(OUT / "visual_review_manifest.csv")
    decisions = json.loads((OUT / "visual_decisions.json").read_text(encoding="utf-8"))
    assert len(decisions) == 48 and {r["review_id"] for r in decisions} == {r["review_id"] for r in review}
    reviewed = {r["review_id"]: r for r in review}
    decision_rows, decisions_by_key = [], {}
    for d in decisions:
        assert d["decision"] in {"suitable", "unsuitable", "hold", "unresolved"}
        assert d["reason"] and d["visible_evidence"]
        source = reviewed[d["review_id"]]
        result = {**source, **d, "visual_review_status": "visually_reviewed", "printed_gtin_independently_verified": "False",
                  "reviewer": "Codex visual inspection of 48 cached images via six contact sheets; no provider calls",
                  "decision_scope": "exact reviewed role/barcode/region/category and frozen image hash only",
                  "execution_authorized": "False"}
        decision_rows.append(result)
        decisions_by_key[result["case_key"]] = result
    # Ensure identical column sets even if manual decision key order differs.
    fields = list(decision_rows[0])
    save_csv("image_usability_decisions.csv", decision_rows, fields)
    assessments = load_csv(OUT / "image_evidence_assessment_previsual.csv")
    counts = defaultdict(Counter)
    for row in assessments:
        d = decisions_by_key.get(row["case_key"])
        qualified = row["step2_eligibility_qualified"] == "1"
        c = counts[(row["sampling_group_id"], row["role"])]
        c["total_records"] += 1
        c["eligibility_qualified_before_image_assessment"] += qualified
        c["locked_step2_blocked"] += not qualified
        c["technically_valid"] += row["technical_validity"] == "valid_saved_preflight_and_verified_cache"
        c["unresolved_technical_hold"] += row["technical_validity"] == "unresolved_hold"
        if d:
            row["visual_review_status"] = "visually_reviewed"
            row["image_disposition"] = {"suitable": "visually_reviewed_suitable", "unsuitable": "exclude_this_image_confirmed_unsuitable",
                "hold": "hold_unresolved_attribution", "unresolved": "unresolved_visually_reviewed_usability"}[d["decision"]]
            c["visually_reviewed"] += 1
            c["visually_" + d["decision"]] += 1
        else:
            c["unreviewed_front_usability"] += 1
        c["eligibility_qualified_not_confirmed_unsuitable"] += qualified and not (d and d["decision"] == "unsuitable")
        c["front_usability_unresolved_or_held"] += qualified and (not d or d["decision"] in {"hold", "unresolved"})
        row["step3_review_id"] = d["review_id"] if d else ""
        row["step3_image_reason"] = d["reason"] if d else "No direct visual assessment; retain pending front-usability status."
    save_csv("image_evidence_assessment.csv", assessments)
    columns = ["total_records", "eligibility_qualified_before_image_assessment", "locked_step2_blocked", "technically_valid",
               "unresolved_technical_hold", "visually_reviewed", "visually_suitable", "visually_unsuitable", "visually_hold", "visually_unresolved",
               "unreviewed_front_usability", "eligibility_qualified_not_confirmed_unsuitable", "front_usability_unresolved_or_held"]
    group_rows = [dict(sampling_group_id=k[0], role=k[1], **{f: v[f] for f in columns}) for k, v in counts.items()]
    save_csv("group_image_usability_counts.csv", group_rows)
    totals = {role: {col: sum(r[col] for r in group_rows if r["role"] == role) for col in columns} for role in ["selected", "reserve"]}
    linked = load_csv(OUT / "secondary_owner_exceptions.csv")
    pairs = load_csv(OUT / "duplicate_evidence_exceptions.csv")
    checks = dict(source_hashes_unchanged=hashes == {name: sha((BASE / name).read_bytes()) for name in INPUTS},
        review_cap_and_group_coverage=len(review) == len({r["image_sha256"] for r in review}) == 48
            and len({r["sampling_group_id"] for r in review}) == 24,
        review_no_blocked_beverage_reserves=all(r["step2_eligibility_qualified"] == "1" for r in review),
        decisions_exactly_cover_review_cases=len(decisions_by_key) == 48,
        all_step2_rows_preserved=len(assessments) == 11832 + 2233,
        role_counts_reconcile=totals["selected"]["total_records"] == 11832 and totals["reserve"]["total_records"] == 2233,
        groups_reconcile=all(r["visually_reviewed"] + r["unreviewed_front_usability"] == r["total_records"]
            and sum(r[f] for f in ["visually_suitable", "visually_unsuitable", "visually_hold", "visually_unresolved"]) == r["visually_reviewed"] for r in group_rows),
        original_secondary_links_preserved=(OUT / "secondary_coverage_links_frozen.csv").read_bytes() == (STEP2 / "secondary_coverage_links_frozen.csv").read_bytes(),
        thirteen_blocked_owner_exceptions=len(linked) == 13,
        known_eighty_selected_byte_pairs=sum(r["left_role"] == r["right_role"] == "selected" and r["identical_image_bytes"] == "True" for r in pairs) == 80,
        no_execution_enabled=all(r["execution_authorized"] == "False" for r in assessments))
    assert all(checks.values()), checks
    save_json("validation.json", dict(status="PASS", checks=checks, totals=totals,
        review_decisions=dict(Counter(r["decision"] for r in decisions)), unique_images_decoded_for_review=48,
        network_calls=0, ocr_llm_calls=0, ownership_finalized=False, history_refreshed=False,
        reserves_promoted=0, approved_executable_manifest_generated=False))
    table = "\n".join(f"| {r['sampling_group_id']} | {r['role']} | {r['total_records']} | {r['visually_reviewed']} | {r['visually_suitable']} | {r['visually_unsuitable']} | {r['visually_hold']+r['visually_unresolved']} | {r['unreviewed_front_usability']} |" for r in group_rows)
    summaries = "\n".join(f"| {role} | {v['total_records']} | {v['technically_valid']} | {v['visually_reviewed']} | {v['visually_suitable']} | {v['visually_unsuitable']} | {v['visually_hold']+v['visually_unresolved']} | {v['unreviewed_front_usability']} |" for role, v in totals.items())
    pair_summary = Counter((r["left_role"], r["right_role"],
                            "identical_bytes" if r["identical_image_bytes"] == "True" else "same_image_revision_different_bytes")
                           for r in pairs)
    byte_pairs = [r for r in pairs if r["identical_image_bytes"] == "True"]
    different_profiles = sum(r["identical_regional_profile_proposal"] == "False" for r in byte_pairs)
    alternatives = load_csv(OUT / "cached_higher_resolution_alternatives.csv")
    category_cases = [r for r in decisions if r["category_issue"]]
    assert {r["review_id"] for r in category_cases} == {"V27", "V28"}
    report = f"""# RUN 06B — Step 3 image evidence review

Status: **Completed bounded assessment; pending Julia's review before ownership/history reconciliation.**
Steps 1 and 2 are approved. Their broad verification, sampling and eligibility decisions were not repeated.

## Technical evidence

Reused saved RUN 06B v2 HTTP/decoding status, dimensions, front URL hints and original/requested/resolved URL provenance.
Checked {preparation['unique_cache_references']:,} distinct cache path/hash references by hashing bytes once, without decoding them; cache integrity failures: {preparation['cache_failures']}.
Technical rows with a cache or saved-preflight mismatch: {preparation['technical_unresolved_rows']}.
There are {len(alternatives)} saved larger-variant references for these cases. These variants were not adopted, redownloaded or visually certified.
No new higher-resolution URL was invented or fetched; where none is recorded, availability remains unknown.
Every original front metadata hint is a URL naming indicator; it does not prove panel scope or legibility.

## Bounded visual review

Exactly **48 unique cached images** were opened for six labelled contact sheets: two per approved sampling group, covering all 24 groups and 11 strata.
The deterministic review-only triage prioritizes narrow dimensions, extreme aspect, small area, missing reference identity, previously recorded issues, shared bytes and language metadata.
It chooses one high-risk selected candidate plus one high-risk eligible reserve per group, with selected fallback where reserves are unavailable.
This changes no sampling draw or ordering. These biased review cases cannot estimate an error rate or visually certify the other products.
Metadata thresholds prioritize review only; they never create automatic image exclusions.
Directly observed unsuitable images are excluded at the evidence level only. Conflicting identity remains held. Unreviewed cases remain unresolved.
Visible front identity correspondence is not verification of the physical pack GTIN. Decisions apply only to exact reviewed role/barcode/region/category plus frozen hash; visual suitability is not propagated to other regional records sharing bytes.

| Role | Records | Technically valid | Reviewed | Suitable | Unsuitable | Reviewed hold/unresolved | Unreviewed |
|---|---:|---:|---:|---:|---:|---:|---:|
{summaries}

The reserve population includes the 13 already blocked Step 2 beverage reserves; none was visually reviewed or reinstated.
`eligibility_qualified_not_confirmed_unsuitable` in the counts retains unreviewed and held cases for audit accounting. It is not an executable or visually certified population.

Material findings: V07/V08 are text-only crops; V09 is an ingredient strip; V29 is an isolated product-description strip; V34/V41 show legal/nutrition panels. These six exact images are confirmed unsuitable for the planned front-pack task.
Seven readable fronts have both reference identity fields missing (V05/V06/V12/V18/V22/V24/V47); they are attribution holds rather than image exclusions.
V10 has a visible Bocage versus frozen Lactel professionnel brand discrepancy; V39's small logo does not confidently establish the frozen brand. Both remain held without asserting corrected identities.
V27 (`5060042640768`, selected) and V28 (`00481342`, reserve) match named potato snacks while assigned to `UK_IE_dairies_C3`. Their clear images are not judged unusable; the category conflict is held for Julia's decision. No category or segmentation assignment was changed.
V13/V14/V40/V43 retain unresolved label-legibility or panel-scope status. No missing words were inferred.

## Duplicate evidence and owner exceptions

Recorded {len(pairs)} pair-level exceptions: {json.dumps({' / '.join(k): v for k, v in pair_summary.items()}, ensure_ascii=False)}.
All 80 known selected identical-byte pairs were reconciled, along with 20 selected-to-eligible-reserve pairs and one eligible-reserve-to-reserve pair. {different_profiles} of {len(byte_pairs)} identical-byte pairs have different regional profile proposals (France versus US/Canada).
Of the 101 identical-byte pairs, 58 retain the same exact barcode and 43 retain different exact barcode strings; all share the recorded OFF source product path. A shared path does not independently verify the physical pack GTIN or authorize alias correction.
The register distinguishes exact barcode equality, OFF source product path, leading-zero alias signals, reference metadata, prompt hashes and saved pixel/image-revision similarity.
Exact strings and regional/country assignments remain intact; alias signals do not authorize merging identities.
Identical bytes with different regional prompts do not establish equivalent LLM work. OCR reuse is only a possibility pending actual OCR configuration, provider operation and subsequent history reconciliation.
Different byte sizes or encodings are not assumed to be different independent pack evidence. Variant equivalence remains unresolved.
The original 806 secondary links are copied byte-for-byte. The 13 links whose owner was blocked are detailed with owner status, locked reason and source; no secondary coverage is newly credited and no owner is reassigned.

## Next ownership/history reconciliation

1. Carry explicit visual exclusions and attribution holds by exact identity and hash; leave unreviewed front usability unresolved.
2. Review raw-byte and saved-variant relationships against exact approved regional prompts, full metadata and actual provider configuration before defining paid-work equivalence.
3. Resolve the 13 vacant-owner links without erasing assignments, automatically crediting coverage or reviving blocked beverage records.
4. In that subsequent authorized step, reconcile saved historical successes/no-claim and failures against immutable image/configuration identities; this step performs no history refresh.
5. Return material evidence gaps for review rather than expanding image fetching, sampling or paid scope. The bounded review does not close universal front-usability approval.

## Group counts

| Group | Role | Records | Reviewed | Suitable | Unsuitable | Reviewed hold/unresolved | Unreviewed |
|---|---|---:|---:|---:|---:|---:|---:|
{table}

## Audit files and checksums

`image_usability_decisions.csv`: compact 48-case decision register with visible evidence and reasons.
`image_evidence_assessment.csv`: all source row identities, technical metadata and explicit review state.
`duplicate_evidence_exceptions.csv` and `secondary_owner_exceptions.csv`: unresolved duplicate/owner risks.
`group_image_usability_counts.csv`: eligibility, technical, suitable, unsuitable, reviewed/unreviewed counts by group and role.
`visual_review_manifest.csv`, `visual_decisions.json`, contact sheets and `review_protocol.json`: bounded visual evidence trail.
`cache_integrity.csv` and `cached_higher_resolution_alternatives.csv`: local cache identity and saved alternatives.
`manifest.json` records exact source/output hashes; `checksums.sha256` includes this report and manifest.
All {len(checks)} validations PASS. Immediate source hashes remain unchanged.

**STOP — Julia's review is required before the next RUN 06B step. No authorized executable manifest, ownership decision, reserve promotion, history refresh or provider call was produced.**
"""
    (OUT / REPORT).write_text(report, encoding="utf-8")
    output_hashes = {p.relative_to(OUT).as_posix(): sha(p.read_bytes()) for p in sorted(OUT.rglob("*"))
                     if p.is_file() and p.name not in {"manifest.json", "checksums.sha256"}}
    save_json("manifest.json", dict(package="RUN_06B_STEP3_V1", status="bounded_assessment_pending_Julia_review",
        script="pipeline/segmentation/review_run_06b_step3.py", script_sha256=sha(Path(__file__).read_bytes()),
        source_sha256=hashes, outputs_sha256=output_hashes, validation="validation.json", review_unique_images=48,
        ownership_finalized=False, history_refreshed=False, reserves_promoted=0, provider_calls=0, execution_authorized=False,
        stop="before_next_RUN_06B_step"))
    output_hashes["manifest.json"] = sha((OUT / "manifest.json").read_bytes())
    (OUT / "checksums.sha256").write_text("".join(f"{value}  {name}\n" for name, value in sorted(output_hashes.items())), encoding="utf-8")
    print((OUT / "validation.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "finalize"])
    args = parser.parse_args()
    prepare() if args.stage == "prepare" else finalize()
