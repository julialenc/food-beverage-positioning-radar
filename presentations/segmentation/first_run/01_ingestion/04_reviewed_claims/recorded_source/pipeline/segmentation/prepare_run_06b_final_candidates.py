"""Allocate approved Step 4 reserve options to an exact proposed RUN 06B sample.

Frozen CSV/JSON inputs only. No image access, history recomputation, SQL,
sampling, provider access or paid authorization. Original packages stay intact.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/segmentation"
SOURCE = BASE / "run_06b_step4_v1"
OUT = BASE / "run_06b_final_candidates_v1"
INPUT_NAMES = [
    "manifest.json", "candidate_selected_manifest.csv", "selected_reconciliation_register.csv",
    "reserve_reconciliation_register.csv", "vacancies.csv", "matching_reserve_availability.csv",
    "proposed_paid_work_ownership.csv", "secondary_link_reconciliation.csv",
    "secondary_coverage_links_frozen.csv", "original_13_owner_exceptions.csv",
    "duplicate_evidence_reconciliation.csv", "historical_overlap_reconciliation.csv",
    "human_decision_reconciliation.csv", "missing_name_attribution.csv", "historical_source_hash_checks.csv",
]
OTHER_INPUTS = [
    "run_06b_step2_v1/approved_group_quotas_frozen.csv",
    "run_06b_step2_v1/approved_country_component_plan_frozen.csv",
    "run_06b_v2/core_configuration_proposal.json", "run_06b_v2/selection_snapshot.json",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def csv_rows(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    return list(reader.fieldnames or []), list(reader)


def write_csv(name, rows, fields=None):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def key(row):
    return row["barcode"], row["region"], row["category"]


def cell(row):
    return row["sampling_group_id"], row["country_cell"], row["accounting_component"]


def work_id(row):
    return row["step4_proposed_core_key"]


def main():
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite versioned proposal: {OUT}")
    blobs = {"run_06b_step4_v1/" + n: (SOURCE / n).read_bytes() for n in INPUT_NAMES}
    blobs.update({p: (BASE / p).read_bytes() for p in OTHER_INPUTS})
    before = {p: digest(b) for p, b in blobs.items()}
    source_manifest = json.loads(blobs["run_06b_step4_v1/manifest.json"])
    checks = {}

    def require(name, passed):
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            raise ValueError(f"STOP final proposal: {name}")

    for name in INPUT_NAMES:
        if name != "manifest.json":
            require("frozen_step4_input_" + name, before["run_06b_step4_v1/" + name] == source_manifest["outputs_sha256"][name])
    for name in OTHER_INPUTS[:3]:
        require("frozen_dependency_" + name, before[name] == source_manifest["source_files_sha256"][name])
    # Quota files are byte-identical Step 2 copies, already protected by Step 4.
    tables = {name: csv_rows(blob) for name, blob in blobs.items() if name.endswith(".csv")}

    def rows(name):
        return tables["run_06b_step4_v1/" + name][1]

    selected, reserves, vacancies = rows("candidate_selected_manifest.csv"), rows("reserve_reconciliation_register.csv"), rows("vacancies.csv")
    originals = rows("selected_reconciliation_register.csv")
    groups = tables[OTHER_INPUTS[0]][1]
    country_plan = tables[OTHER_INPUTS[1]][1]
    config = json.loads(blobs["run_06b_v2/core_configuration_proposal.json"])
    config_hash = before["run_06b_v2/core_configuration_proposal.json"]
    source_ownership = {(r["role"], *key(r)): r for r in rows("proposed_paid_work_ownership.csv")}
    human_excluded = {(r["role"], *key(r), r["image_sha256"]) for r in rows("human_decision_reconciliation.csv") if r["step4_human_action"] == "EXCLUDE"}
    require("approved_step4_counts", len(selected) == 11730 and len(reserves) == 2233 and len(vacancies) == 270
            and Counter(r["step4_status"] for r in originals) == {"PROCESS": 11730, "PRE-EXECUTION HOLD": 95, "EXCLUDE": 7})
    require("original_primary_core_units_unique", len({work_id(r) for r in selected}) == len(selected))
    require("original_seed_preserved_without_new_draw", json.loads(blobs["run_06b_v2/selection_snapshot.json"])["seed"] == 20261022
            and all(r["seed"] == "20261022" for r in selected + reserves))
    require("original_primary_slots_unique_and_vacant_slots_disjoint", len({r["slot_id"] for r in selected}) == len(selected)
            and len({r["slot_id"] for r in vacancies}) == 270
            and {r["slot_id"] for r in selected}.isdisjoint({r["slot_id"] for r in vacancies}))
    require("all_retained_selected_first_attempt_eligible", all(r["step4_status"] == "PROCESS"
            and r["step2_eligibility_qualified"] == "1" and r["step4_history_status"] == "NO_MATCH_IN_FROZEN_HISTORY_LEDGER"
            and r["status"] == "technical_pass" and r["m1_eligible"] == "1" and r["available_first_attempt"] == "1"
            and ("selected", *key(r), r["image_sha256"]) not in human_excluded for r in selected))
    # Existing selected owners are locked globally before any replacement.
    primary_by_core = {work_id(r): ("selected", r, r["slot_id"]) for r in selected}
    primary = [("selected", r, r["slot_id"], None, None) for r in selected]
    waiting = defaultdict(list)
    for vacant in sorted(vacancies, key=lambda r: r["slot_id"]):
        waiting[cell(vacant)].append(vacant)
    reserve_decisions, replacements, redundant_links = [], [], []
    for order, r in enumerate(reserves, 1):
        require(f"reserve_frozen_order_{order}", r["step2_source_row"] == str(order))
        status, reason, target_slot, prior, existing_owner = "", "", "", None, None
        if r["step4_status"] != "PROCESS":
            status, reason = "UNAVAILABLE_" + r["step4_status"].replace(" ", "_"), r["step4_reasons"]
        elif (r["step2_eligibility_qualified"] != "1" or r["step4_history_status"] != "NO_MATCH_IN_FROZEN_HISTORY_LEDGER"
              or ("reserve", *key(r), r["image_sha256"]) in human_excluded):
            raise ValueError(f"Inconsistent approved PROCESS reserve: {key(r)}")
        elif work_id(r) in primary_by_core:
            existing_owner = primary_by_core[work_id(r)]
            status, reason = "UNUSED_EQUIVALENT_CORE_WORK", "Equivalent proposed regional core work already has a primary owner; no second independent quota."
            redundant_links.append(dict(reserve_source_row=order, barcode=r["barcode"], region=r["region"], category=r["category"],
                countries=r["countries"], proposed_core_key=work_id(r), owner_slot=existing_owner[2],
                owner_barcode=existing_owner[1]["barcode"], owner_region=existing_owner[1]["region"], coverage_credited=False))
        elif waiting[cell(r)]:
            require(f"replacement_saved_technical_evidence_{order}", r["status"] == "technical_pass"
                    and len(r["image_sha256"]) == 64 and bool(r["immutable_image_path"]))
            prior = waiting[cell(r)].pop(0)
            require(f"replacement_exact_cell_and_scope_{order}", cell(prior) == cell(r) and prior["region"] == r["region"] and prior["category"] == r["category"])
            target_slot = prior["slot_id"]
            status, reason = "PROPOSED_REPLACEMENT", "First available eligible reserve in frozen order for this exact group/country/component; vacancy order is ascending frozen slot ID."
            primary.append(("reserve", r, target_slot, order, prior))
            primary_by_core[work_id(r)] = ("reserve", r, target_slot)
            replacements.append(dict(proposed_slot_id=target_slot, replaced_barcode=prior["barcode"], replaced_region=prior["region"],
                replaced_category=prior["category"], vacancy_origin=prior["step4_vacancy_origin"], vacancy_reason=prior["step4_reason"],
                replacement_barcode=r["barcode"], replacement_region=r["region"], replacement_category=r["category"],
                replacement_countries=r["countries"], sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"],
                accounting_component=r["accounting_component"], frozen_reserve_sequence=order, source_draw_rank=r["draw_rank"],
                source_draw_stage=r["draw_stage"], source_image_sha256=r["image_sha256"], proposed_core_key=work_id(r),
                allocation_status="PROPOSED_ONLY", paid_execution_authorized=False))
        else:
            status, reason = "ELIGIBLE_UNUSED_NO_REMAINING_MATCHING_VACANCY", "Retain frozen order as a remaining reserve; no cross-cell/component substitution."
        reserve_decisions.append({**r, "final_reserve_sequence": order, "final_proposal_reserve_status": status,
            "final_proposed_target_slot": target_slot, "final_proposal_reason": reason,
            "final_equivalent_core_owner_slot": existing_owner[2] if existing_owner else "", "final_execution_authorized": False})
    primary.sort(key=lambda x: x[2])
    remaining_vacancies = sorted([r for rs in waiting.values() for r in rs], key=lambda r: r["slot_id"])
    require("only_exact_matching_frozen_reserves_used", all(r["step4_status"] == "PROCESS" for role, r, _, _, _ in primary)
            and len({slot for _, _, slot, _, _ in primary}) == len(primary)
            and len({work_id(r) for _, r, _, _, _ in primary}) == len(primary))

    # Group current byte-equivalent OCR inputs. No historical text is reused.
    ocr_groups = defaultdict(list)
    for item in primary:
        ocr_groups[item[1]["step4_proposed_ocr_key"]].append(item)
    ocr_owners = {}
    old_ocr_owner = {r["proposed_ocr_key"]: r["proposed_ocr_owner_slot"] for r in source_ownership.values() if r["role"] == "selected" and r["step4_status"] == "PROCESS"}
    for okey, members in ocr_groups.items():
        prior_slot = old_ocr_owner.get(okey)
        previous = [r for r in members if r[2] == prior_slot]
        chosen = previous[0] if previous else min(members, key=lambda x: (0 if x[0] == "selected" else 1,
            int(x[1]["frozen_group_frame_N"]), x[1]["sampling_group_id"], x[2], *key(x[1])))
        require("ocr_key_same_bytes_" + okey[:12], len({m[1]["image_sha256"] for m in members}) == 1)
        ocr_owners[okey] = chosen
    sf = tables["run_06b_step4_v1/candidate_selected_manifest.csv"][0]
    rf = tables["run_06b_step4_v1/reserve_reconciliation_register.csv"][0]
    source_fields = sf + [f for f in rf if f not in sf]
    proposed, ocr_links = [], []
    for role, r, slot, sequence, prior in primary:
        okey = r["step4_proposed_ocr_key"]
        owner = ocr_owners[okey]
        profile = config["regional_profiles"][r["region"]]
        core = work_id(r)
        proc_id = digest(json.dumps(["RUN06B_FINAL_CANDIDATES_V1", slot, *key(r), r["image_sha256"], core], separators=(",", ":")).encode())
        additions = dict(proposed_processing_id=proc_id, proposed_primary_slot_id=slot,
            proposed_primary_origin="retained_step4_selected" if role == "selected" else "matching_reserve_replacement",
            proposed_source_role=role, proposed_source_sequence=r["step2_source_row"],
            proposed_reserve_sequence=sequence if sequence is not None else "", proposed_replaced_barcode=prior["barcode"] if prior else "",
            proposed_vacancy_reason=prior["step4_reason"] if prior else "", proposed_core_llm_key=core,
            proposed_regional_profile=profile["profile"], proposed_core_prompt_version=profile["recorded_prompt_version"],
            proposed_core_prompt_path=profile["prompt_path"], proposed_core_prompt_sha256=profile["prompt_sha256"],
            proposed_context_prompt_sha256=profile["context_prompt_sha256"], proposed_configuration_sha256=config_hash,
            proposed_model_deployment=config["model_deployment_proposed"], proposed_actual_model_version="UNVERIFIED",
            proposed_ocr_unit_key=okey, proposed_ocr_owner_slot=owner[2], proposed_ocr_owner_barcode=owner[1]["barcode"],
            proposed_ocr_owner_region=owner[1]["region"], proposed_ocr_relationship="new_OCR_owner" if owner[2] == slot else "conditional_same_bytes_OCR_reuse",
            proposed_core_llm_owner_slot=slot, proposed_front_usability_policy="saved_technical_checks_plus_known_exclusions; unreviewed_images_remain_candidates",
            proposed_history_baseline="RUN06B_Step4_frozen_saved_ledger", proposed_bounded_prepaid_history_check_required=True,
            proposed_provider_configuration_verified=False, proposed_paid_authorization=False, proposed_paid_attempts_consumed=0)
        proposed.append({**{f: r.get(f, "") for f in source_fields}, **additions})
        ocr_links.append(dict(proposed_processing_id=proc_id, slot_id=slot, barcode=r["barcode"], region=r["region"], category=r["category"],
            countries=r["countries"], image_sha256=r["image_sha256"], ocr_unit_key=okey, owner_slot=owner[2],
            owner_barcode=owner[1]["barcode"], owner_region=owner[1]["region"], core_llm_unit_key=core,
            identical_frozen_byte_relationship_confirmed=True, conditional_ocr_reuse=owner[2] != slot,
            operational_reuse_authorized=False, historical_ocr_reused=False, separate_regional_llm_preserved=True))
    proposed_by_core = {r["proposed_core_llm_key"]: r for r in proposed}
    secondary_links = []
    for row in rows("secondary_link_reconciliation.csv"):
        owner = proposed_by_core.get(row["core_equivalence_proposal_sha256"])
        if row["step4_secondary_status"] != "PROCESS": owner = None
        secondary_links.append({**row, "final_proposed_owner_slot": owner["proposed_primary_slot_id"] if owner else "",
            "final_proposed_owner_barcode": owner["barcode"] if owner else "", "final_proposed_owner_region": owner["region"] if owner else "",
            "final_link_status": ("PROPOSED_OWNER_RETAINED" if owner["proposed_primary_slot_id"] == row["owner_slot_id"] else "PROPOSED_OWNER_RESOLVED_BY_REPLACEMENT") if owner else "UNRESOLVED_NO_PROPOSED_OWNER",
            "final_coverage_credited": False, "final_paid_authorization": False})
    # Preserve every original relation and record current sample membership.
    members = {(r["proposed_source_role"], *key(r)): r for r in proposed}
    duplicate_links = []
    for row in rows("duplicate_evidence_reconciliation.csv"):
        left = members.get(tuple(row["left_" + k] for k in ["role", "barcode", "region", "category"]))
        right = members.get(tuple(row["right_" + k] for k in ["role", "barcode", "region", "category"]))
        duplicate_links.append({**row, "final_left_primary_slot": left["proposed_primary_slot_id"] if left else "",
            "final_right_primary_slot": right["proposed_primary_slot_id"] if right else "",
            "final_shared_ocr_proposed": bool(left and right and left["proposed_ocr_unit_key"] == right["proposed_ocr_unit_key"]),
            "final_core_llm_units_merged": False, "final_execution_authorized": False})

    # Quotas are reconciled at component, country cell, group and stratum levels.
    component_quota = Counter()
    target = {"upper_observed_fibre": "targeted_upper_fibre", "explicit_preparation_or_specialist": "targeted_beverage_preparation_or_specialist"}
    for r in country_plan:
        component_quota[(r["sampling_group_id"], r["country_cell"], "random_baseline")] += int(r["random_baseline"])
        if int(r["targeted_attempts"]): component_quota[(r["sampling_group_id"], r["country_cell"], target[r["target_component"]])] += int(r["targeted_attempts"])
    original_n = Counter(cell(r) for r in selected)
    final_n = Counter(cell(r) for r in proposed)
    vacancy_n = Counter(cell(r) for r in remaining_vacancies)
    replaced_n = Counter((r["sampling_group_id"], r["country_cell"], r["accounting_component"]) for r in replacements)
    unused = [r for r in reserve_decisions if r["final_proposal_reserve_status"] != "PROPOSED_REPLACEMENT"]
    eligible_unused_n = Counter(cell(r) for r in unused if r["step4_status"] == "PROCESS" and r["final_proposal_reserve_status"] != "UNUSED_EQUIVALENT_CORE_WORK")
    require("residual_vacancies_have_no_unused_matching_independent_reserve", all(eligible_unused_n[cell(r)] == 0 for r in remaining_vacancies))
    remaining_vacancies = [{**r, "final_shortfall_reason": "no_unused_eligible_nonredundant_reserve_in_exact_group_country_component",
        "final_unused_eligible_matching_reserves": eligible_unused_n[cell(r)], "final_cross_cell_transfer_permitted": False}
        for r in remaining_vacancies]
    component_rows = [dict(sampling_group_id=k[0], country_cell=k[1], accounting_component=k[2], approved_quota=n,
        retained_step4_selected=original_n[k], proposed_reserve_replacements=replaced_n[k], proposed_primary_records=final_n[k],
        remaining_vacancies=vacancy_n[k], remaining_eligible_reserves=eligible_unused_n[k], cross_cell_transfers=0) for k, n in component_quota.items()]
    country_rows = []
    for r in country_plan:
        matching = [x for x in component_rows if x["sampling_group_id"] == r["sampling_group_id"] and x["country_cell"] == r["country_cell"]]
        country_rows.append(dict(region=r["region"], category=r["category"], sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"],
            approved_quota=int(r["proposed_primary_attempts"]), proposed_primary_records=sum(x["proposed_primary_records"] for x in matching),
            replacements=sum(x["proposed_reserve_replacements"] for x in matching), remaining_vacancies=sum(x["remaining_vacancies"] for x in matching)))
    group_rows = []
    for r in groups:
        matching = [x for x in country_rows if x["sampling_group_id"] == r["sampling_group_id"]]
        group_rows.append(dict(region=r["region"], category=r["category"], sampling_group_id=r["sampling_group_id"],
            approved_quota=int(r["proposed_new_attempts"]), proposed_primary_records=sum(x["proposed_primary_records"] for x in matching),
            replacements=sum(x["replacements"] for x in matching), remaining_vacancies=sum(x["remaining_vacancies"] for x in matching)))
    stratum_rows = []
    for region, category in dict.fromkeys((r["region"], r["category"]) for r in groups):
        matching = [x for x in group_rows if x["region"] == region and x["category"] == category]
        stratum_rows.append(dict(region=region, category=category, approved_quota=sum(x["approved_quota"] for x in matching),
            proposed_primary_records=sum(x["proposed_primary_records"] for x in matching), replacements=sum(x["replacements"] for x in matching),
            remaining_vacancies=sum(x["remaining_vacancies"] for x in matching)))
    require("quota_reconciliation_all_levels", len(group_rows) == 24 and len(country_rows) == 56 and len(stratum_rows) == 11
            and sum(component_quota.values()) == len(proposed) + len(remaining_vacancies) == 12000
            and all(r["approved_quota"] == r["proposed_primary_records"] + r["remaining_vacancies"] for r in component_rows + country_rows + group_rows + stratum_rows))
    require("reserve_accounting_2233_once", len(unused) + len(replacements) == len(reserve_decisions) == 2233
            and len({(r["proposed_source_role"], r["proposed_source_sequence"]) for r in proposed}) == len(proposed))
    require("all_original_selected_preserved", {r["proposed_primary_slot_id"] for r in proposed if r["proposed_source_role"] == "selected"} == {r["slot_id"] for r in selected})
    require("source_fields_gtins_blank_names_and_sampling_reasons_preserved", all(
        all(p[f] == source[f] for f in (sf if role == "selected" else rf))
        for p, (role, source, _, _, _) in zip(proposed, primary)))
    require("frozen_reserve_sequence_for_all_replacements", [r["frozen_reserve_sequence"] for r in replacements] == sorted(r["frozen_reserve_sequence"] for r in replacements))
    require("no_excluded_or_held_rows_proposed", all(p["step4_status"] == "PROCESS" and p["step2_eligibility_qualified"] == "1" for p in proposed))
    require("distinct_regional_llm_work_never_merged", len(proposed_by_core) == len(proposed)
            and all(len({m[1]["step4_proposed_core_key"] for m in values}) == len(values) for values in ocr_groups.values()))
    require("no_new_visual_certification_required", not any(p["proposed_front_usability_policy"] == "all_images_visually_certified" for p in proposed))
    require("no_US_CA_dairy_or_extra_paid_authorization", not any(p["region"] == "US+CA" and p["category"] == "dairies" for p in proposed)
            and all(p["execution_authorized"] == "False" and p["planned_paid_job"] == "0" and p["proposed_paid_authorization"] is False for p in proposed))
    holds = []
    for role, entries in [("selected", originals), ("reserve", reserves)]:
        for r in entries:
            if r["step4_status"] == "PRE-EXECUTION HOLD":
                holds.append(dict(role=role, barcode=r["barcode"], region=r["region"], category=r["category"], countries=r["countries"],
                    sampling_group_id=r["sampling_group_id"], country_cell=r["country_cell"], accounting_component=r["accounting_component"],
                    image_sha256=r["image_sha256"], history_status=r["step4_history_status"], reasons=r["step4_reasons"], paid_attempts_consumed=0))
    history_snapshot = json.loads(blobs["run_06b_v2/selection_snapshot.json"])
    history_plan = dict(required_before_first_paid_call=True, performed_in_this_step=False,
        frozen_history_timestamp_utc=history_snapshot["actual_history_refresh_timestamp_utc"],
        baseline="Existing RUN 06B v2 historical ledger reconciled by approved Step 4; no history recomputation here.",
        scope="Bounded delta check for exact proposed and linked GTINs and recorded image revisions; saved result inventories/new checkpoint or observation ledgers since the frozen refresh. Use verified barcode indexes if database lookups are needed.",
        stop_conditions=["New exact-barcode success including valid no-claim", "New failure/unusable event outside first-attempt scope", "Changed image/configuration", "Unresolved possible historical equivalence", "Changed manifest or provider policy"],
        no_full_database_scan=True, no_automatic_release_of_existing_holds=True,
        action_if_changed="Stop, version and reconcile only affected assignments before paid authorization.")
    counts = dict(retained_step4_selected=len(selected), proposed_replacements=len(replacements), primary_processing_records=len(proposed),
        distinct_exact_gtins=len({r["barcode"] for r in proposed}), proposed_ocr_units_with_conditional_sharing=len(ocr_groups),
        ocr_submissions_without_sharing=len(proposed), conditional_ocr_submissions_avoided=len(proposed) - len(ocr_groups),
        confirmed_identical_byte_shared_ocr_groups=sum(len(x) > 1 for x in ocr_groups.values()), operational_ocr_reuse_authorizations=0,
        historical_ocr_reuse_units=0, core_llm_units=len(proposed_by_core), remaining_vacancies=len(remaining_vacancies),
        reserve_records_total=2233, unused_reserve_records=len(unused), unused_reserve_status=dict(Counter(r["step4_status"] for r in unused)),
        reserve_proposal_status=dict(Counter(r["final_proposal_reserve_status"] for r in reserve_decisions)),
        unresolved_hold_status=dict(Counter(r["role"] for r in holds)), secondary_link_status=dict(Counter(r["final_link_status"] for r in secondary_links)),
        original_13_orphan_link_status=dict(Counter(r["final_link_status"] for r in secondary_links if r["original_owner_blocked_in_step2"] == "True")),
        proposed_primary_blank_names=sum(not r["prompt_product_name"].strip() for r in proposed),
        proposed_primary_blank_name_and_brand=sum(not r["prompt_product_name"].strip() and not r["prompt_brand"].strip() for r in proposed))
    OUT.mkdir()
    (OUT / ".gitignore").write_text("# Local product-level proposed sample; no publication or paid authorization.\n*\n", encoding="utf-8")
    write_csv("proposed_primary_processing_manifest.csv", proposed)
    write_csv("reserve_allocation_register.csv", reserve_decisions)
    write_csv("remaining_reserve_register.csv", unused)
    for name, records, empty_fields in [
        ("reserve_replacements.csv", replacements, None), ("proposed_ocr_reuse_links.csv", ocr_links, None),
        ("secondary_coverage_proposal.csv", secondary_links, None), ("duplicate_evidence_proposal_links.csv", duplicate_links, None),
        ("redundant_reserve_core_links.csv", redundant_links, ["reserve_source_row", "barcode", "region", "category", "countries", "proposed_core_key", "owner_slot", "owner_barcode", "owner_region", "coverage_credited"]),
        ("quota_component_reconciliation.csv", component_rows, None), ("quota_country_cell_reconciliation.csv", country_rows, None),
        ("quota_group_reconciliation.csv", group_rows, None), ("quota_region_category_reconciliation.csv", stratum_rows, None),
        ("remaining_vacancies.csv", remaining_vacancies, None), ("unresolved_holds.csv", holds, None)]:
        write_csv(name, records, empty_fields)
    (OUT / "core_configuration_proposal_frozen.json").write_bytes(blobs["run_06b_v2/core_configuration_proposal.json"])
    (OUT / "original_secondary_links_frozen.csv").write_bytes(blobs["run_06b_step4_v1/secondary_coverage_links_frozen.csv"])
    write_json("prepaid_history_update_plan.json", history_plan)
    require("inputs_unchanged_after_package_creation", before == {p: digest((BASE / p).read_bytes()) for p in blobs})
    require("serialized_proposed_records_roundtrip", csv_rows((OUT / "proposed_primary_processing_manifest.csv").read_bytes())[1]
            == [{k: str(v) for k, v in p.items()} for p in proposed])
    require("source_secondary_links_byte_identical", (OUT / "original_secondary_links_frozen.csv").read_bytes() == blobs["run_06b_step4_v1/secondary_coverage_links_frozen.csv"])
    write_json("validation.json", dict(status="PASS", checks=checks, counts=counts, paid_calls=0, source_files_modified=False,
        proposed_allocation_only=True, runner_executed=False, authorized_executable_manifest_created=False))
    group_table = "\n".join(f"| {r['sampling_group_id']} | {r['approved_quota']} | {r['proposed_primary_records']} | {r['replacements']} | {r['remaining_vacancies']} |" for r in group_rows)
    report = f"""# RUN 06B — Proposed final candidate manifest and reserve allocation

Status: **Exact versioned proposal; pending Julia's review before runner validation and paid authorization.**

## Proposed sample

| Measure | Count |
|---|---:|
| Retained Step 4 selected candidates | {len(selected):,} |
| Proposed matching reserve replacements | {len(replacements):,} |
| Primary processing records | **{len(proposed):,}** |
| Distinct exact GTIN strings | {counts['distinct_exact_gtins']:,} |
| Remaining approved-slot vacancies | **{len(remaining_vacancies)}** |
| Original reserves not allocated | {len(unused):,} |
| Core initial LLM units | {len(proposed_by_core):,} |
| OCR inputs under conditional identical-byte sharing | {len(ocr_groups):,} |
| OCR submissions without sharing | {len(proposed):,} |
| Conditionally avoided OCR submissions | {counts['conditional_ocr_submissions_avoided']} |

The 24 group quotas, 56 group/country cells, 92 group/country/component cells and 11 strata remain unchanged. Proposed primaries plus vacancies total 12,000.
Country assignments are retained exactly; US+CA dairy, missing-M1 work and retry jobs remain outside the sample.
Counts represent regional processing records, not a count of independently verified physical SKUs or market prevalence.

## Allocation method

Locked all 11,730 retained selected records and their proposed regional core keys before considering reserves.
Processed the 2,233-row frozen reserve register in its original order. Eligible PROCESS reserves may fill only the exact group × country cell × accounting component; region and category must also agree.
Within each matching cell, vacant slots are considered in ascending original slot ID. No new product draw, seed, quota transfer or success top-up was introduced.
Held/excluded records remain outside the proposal. Equivalent regional core work is never assigned a second independent primary quota; skipped equivalents remain linked for provenance.
All original metadata columns are preserved, including source role, old slot/ownership fields and blank names. **`proposed_primary_slot_id`** is the proposed assignment; **`proposed_source_role`** identifies retained selected versus reserve input.
Every original draw stage/rank/seed, source GTIN, country set, selection reason, original/requested/resolved image URL, cache path, byte hash and Step 4 history/eligibility status remains available.
The proposed manifest has {counts['proposed_primary_blank_names']} blank product names, including {counts['proposed_primary_blank_name_and_brand']} records also missing brands. Their approved attribution remains valid; names are not manufactured.

## OCR and LLM ownership

The confirmed relationship is equality of frozen cached bytes under the existing proposal. Sharing an OCR submission remains conditional on the runner using exactly the same verified OCR engine/API/options and immutable bytes.
There are {counts['confirmed_identical_byte_shared_ocr_groups']} shared identical-byte groups; operational reuse authorizations and historical OCR reuse remain zero.
Existing selected OCR owners are preserved when still in the sample; new groups choose a deterministic proposed owner without displacing retained primary slots.
All {len(proposed_by_core):,} regional core LLM units remain distinct. Different France/US+Canada prompts are not merged because their image bytes agree.
The frozen configuration proposal and exact regional prompt hashes are attached. The original `configuration_proposal_sha256` column is source provenance; **`proposed_configuration_sha256`** identifies the configuration used by this proposal.
Actual immutable provider model/deployment identity is still unverified. Proposed keys and owners are not authorized paid-work identities.
The 100 different-raster pairs from Step 3 retain distinct OCR inputs; no source image was swapped or silently replaced by a larger variant.
Core LLM counts refer to initial extractions. Conditional dairy context review/re-extraction may add calls under existing rules and must be accounted for by the eventual runner.
The independent hydration/electrolyte LLM stage is not silently enabled by this core sample; any paid use needs its separately scoped pilot/call budget.

## Secondary relationships and remaining reserves

All 806 original secondary links are preserved byte-for-byte and reconciled against the proposed core owners.
Proposed secondary outcomes: {json.dumps(counts['secondary_link_status'])}.
Original 13 orphan outcomes: {json.dumps(counts['original_13_orphan_link_status'])}.
No secondary coverage is credited before processing. Secondary assignments do not consume another independent primary quota.
Unused reserves by Step 4 status: {json.dumps(counts['unused_reserve_status'])}. These remain in frozen order with explicit nonallocation reasons.
Unresolved source holds: {json.dumps(counts['unresolved_hold_status'])}. None is released by this allocation.

## History and pre-execution readiness

Used the accepted Step 4 historical outcomes and saved ledger references without recomputing history or opening a database.
All proposed rows retain the frozen-ledger no-match/first-attempt status. Historical-equivalence uncertainty stays on HOLD.
The saved refresh is dated **{history_plan['frozen_history_timestamp_utc']}**. A **bounded last-minute delta check is required before the first paid call** because a frozen no-match does not establish absence of subsequent processing.
`prepaid_history_update_plan.json` specifies exact proposed/linked GTINs, recorded image revisions, saved-result/checkpoint changes and indexed lookups if required. No full database scan is called for or performed here.
Outstanding execution blockers: exact provider/version and transport configuration; evidence-aware runner/checkpoint/resume and append-only result integration; validated per-call tariffs, complete reservations/receipts and enforceable spending limits; the bounded pre-call history check; explicit paid authorization.
Existing technical image checks and specific known exclusions suffice for candidacy. **No universal visual certification is required.** Actual front/OCR usability will be observed during authorized processing; failures and valid no-claim results must remain distinct.
The runner must consume frozen cached bytes or verify retrieved byte identity before dispatch; changed images/configuration cannot silently enter this proposal.

## Group reconciliation

| Group | Approved quota | Proposed primaries | Reserve replacements | Remaining vacancies |
|---|---:|---:|---:|---:|
{group_table}

Component and country-cell shortfalls and original reasons are in the quota tables and `remaining_vacancies.csv`; no cell is topped up from another country or component.

## Audit outputs and validation

The primary deliverable is `proposed_primary_processing_manifest.csv`.
Reserve allocation/remaining registers, `reserve_replacements.csv`, `secondary_coverage_proposal.csv`, `proposed_ocr_reuse_links.csv`, duplicate links, four quota summaries and hold/vacancy registers provide the audit trail.
All {len(checks)} checks PASS. Inputs remain unchanged; exact source columns and serialized GTIN strings are preserved.
`manifest.json` records source and output SHA256 hashes; `checksums.sha256` includes this report and the package manifest.
One preparation script and a new local product package were created. Steps 1–4 were not rerun; no images, URL preflight, database scans, historical modification or provider calls occurred.

**STOP for Julia's review before execution-runner validation and paid authorization. This proposed sample does not authorize payment.**
"""
    (OUT / "RUN 06B - Final candidate readiness.md").write_text(report, encoding="utf-8")
    output_hashes = {p.name: digest(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()}
    write_json("manifest.json", dict(package="RUN_06B_FINAL_CANDIDATES_V1", status="PROPOSED_NOT_AUTHORIZED_FOR_PAYMENT",
        script="pipeline/segmentation/prepare_run_06b_final_candidates.py", script_sha256=digest(Path(__file__).read_bytes()),
        source_files_sha256=before, outputs_sha256=output_hashes, counts=counts,
        seed_preserved=20261022, allocation=12000, groups=24, group_country_cells=56, strata=11,
        allocation_order="lock retained primaries, then frozen reserve order; ascending slot ID within exact group/country/component",
        ocr_reuse_status="conditional_pending_actual_provider_options", last_minute_history_delta_required=True,
        universal_visual_certification_required=False, execution_authorized=False, paid_calls=0, runner_executed=False,
        original_packages_modified=False, stop="Julia_review_before_runner_validation_and_paid_authorization"))
    output_hashes["manifest.json"] = digest((OUT / "manifest.json").read_bytes())
    (OUT / "checksums.sha256").write_text("".join(f"{value}  {name}\n" for name, value in sorted(output_hashes.items())), encoding="utf-8")
    print(json.dumps(dict(package=str(OUT), counts=counts, checks_passed=len(checks)), indent=2))


if __name__ == "__main__":
    main()
