"""RUN 06B Step 2: reconcile frozen CSV evidence only; never promote reserves.

Creates one local, versioned candidate package. No database, image, provider,
sampling or paid-work ownership operations are imported or invoked.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/segmentation"
OUT = BASE / "run_06b_step2_v1"
SELECTED = "run_06b_v2/selected_manifest.csv"
RESERVES = "run_06b_v2/reserve_manifest.csv"
DECISIONS = "beverage_final_v1/eligibility_decisions.csv"
IMPACT = "beverage_final_v1/run_06b_eligibility_impact.csv"
LINKS = "run_06b_v2/secondary_coverage_links.csv"
COUNTRY_PLAN = "run_06a_v1/country_component_plan.csv"
ALLOCATION = "run_06a_v1/proposed_allocation.csv"
UNFILLED = "run_06b_v2/unfilled_slots.csv"
GROUPS = "run_06b_v2/group_quota_reconciliation.csv"
SOURCES = [SELECTED, RESERVES, DECISIONS, IMPACT, LINKS, COUNTRY_PLAN,
           ALLOCATION, UNFILLED, GROUPS, "run_06a_v1/check_06a_approval.json",
           "run_06b_v2/run_06b_manifest.json",
           "beverage_final_v1/final_lock_manifest.json"]
TARGETS = {"upper_observed_fibre": "targeted_upper_fibre",
           "explicit_preparation_or_specialist": "targeted_beverage_preparation_or_specialist"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(data: bytes):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    return list(reader.fieldnames or []), list(reader)


def key(row):
    return row["barcode"], row["region"], row["category"]


def cell(row):
    return row["sampling_group_id"], row["country_cell"], row["accounting_component"]


def write_csv(name, fields, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite a versioned package: {OUT}")
    # Check only this operation's immediate inputs. Step 1 is already approved.
    source_bytes = {name: (BASE / name).read_bytes() for name in SOURCES}
    before = {name: digest(data) for name, data in source_bytes.items()}
    frozen = json.loads(source_bytes["run_06b_v2/run_06b_manifest.json"])
    lock = json.loads(source_bytes["beverage_final_v1/final_lock_manifest.json"])
    approval = json.loads(source_bytes["run_06a_v1/check_06a_approval.json"])
    checks = {}

    def require(name, condition):
        checks[name] = "PASS" if condition else "FAIL"
        if not condition:
            raise ValueError(f"Step 2 stopped: {name}")

    require("immediate_frozen_input_hashes", all(
        before[name] == expected
        for section in (frozen["outputs_sha256"], frozen["protected_source_sha256"],
                        lock["data_outputs_sha256"], lock["protected_inputs_sha256"])
        for path, expected in section.items()
        for name in SOURCES if path == "presentations/segmentation/" + name))
    sf, selected = read_csv(source_bytes[SELECTED])
    rf, reserves = read_csv(source_bytes[RESERVES])
    df, decisions = read_csv(source_bytes[DECISIONS])
    _, impact = read_csv(source_bytes[IMPACT])
    _, unfilled = read_csv(source_bytes[UNFILLED])
    _, groups = read_csv(source_bytes[GROUPS])
    _, plan = read_csv(source_bytes[COUNTRY_PLAN])
    _, allocation = read_csv(source_bytes[ALLOCATION])
    _, links = read_csv(source_bytes[LINKS])
    lookup = {(r["barcode"], r["region"]): r for r in decisions}
    require("unique_locked_beverage_decision_keys", len(lookup) == len(decisions))
    require("locked_decision_category_and_status", all(
        r["category"] == "beverages" and r["status"] in {"eligible", "excluded", "hold"}
        and r["rule_version"] == "beverage_current_wave_v1" for r in decisions))

    def decision(row):
        return lookup.get((row["barcode"], row["region"])) if row["category"] == "beverages" else None

    def blocked(row):
        d = decision(row)
        return d is not None and d["status"] in {"excluded", "hold"}

    # All source columns stay unchanged, including legacy candidate status fields.
    # Only prefixed Step 2 fields describe the new eligibility restriction.
    extra = ["step2_source_manifest", "step2_source_row", "step2_disposition",
             "step2_eligibility_qualified", "step2_execution_authorized",
             "step2_beverage_decision_present", "step2_decision_sidecar_sha256"]
    extra += ["step2_beverage_" + f for f in df]

    def annotate(row, ordinal, source, role):
        d = decision(row)
        disposition = ("excluded" if d["status"] == "excluded" else "held") if blocked(row) else (
            "retained_candidate_pending_technical_validation" if role == "selected"
            else "eligibility_qualified_reserve_pending_technical_validation")
        added = dict(step2_source_manifest="presentations/segmentation/" + source,
                     step2_source_row=str(ordinal), step2_disposition=disposition,
                     step2_eligibility_qualified="0" if blocked(row) else "1",
                     step2_execution_authorized="False", step2_beverage_decision_present="1" if d else "0",
                     step2_decision_sidecar_sha256=before[DECISIONS] if d else "")
        added.update({"step2_beverage_" + f: d[f] if d else "" for f in df})
        return {**row, **added}

    candidates, blocked_selected = [], []
    for i, row in enumerate(selected, 1):
        (blocked_selected if blocked(row) else candidates).append(annotate(row, i, SELECTED, "selected"))
    reserve_register = [annotate(row, i, RESERVES, "reserve") for i, row in enumerate(reserves, 1)]
    qualified_reserves = [r for r in reserve_register if r["step2_eligibility_qualified"] == "1"]
    blocked_reserves = [r for r in reserve_register if r["step2_eligibility_qualified"] == "0"]

    selected_counts = Counter(r["step2_beverage_status"] for r in blocked_selected)
    reserve_counts = Counter(r["step2_beverage_status"] for r in blocked_reserves)
    require("selected_accounted_once", len(selected) == 11937 and len(candidates) == 11832
            and len(blocked_selected) == 105 and len({key(r) for r in selected}) == len(selected)
            and {key(r) for r in candidates}.isdisjoint({key(r) for r in blocked_selected})
            and {key(r) for r in candidates + blocked_selected} == {key(r) for r in selected})
    require("reserves_accounted_once_in_original_order", len(reserves) == len(reserve_register) == 2233
            and len({key(r) for r in reserves}) == 2233
            and all(all(out[f] == src[f] for f in rf) for out, src in zip(reserve_register, reserves)))
    require("locked_blocked_counts", selected_counts == {"excluded": 39, "hold": 66}
            and reserve_counts == {"excluded": 6, "hold": 7}
            and len(qualified_reserves) == 2220
            and sum(r["category"] == "beverages" for r in qualified_reserves) == 580)
    actual_blocked = {(role, r["barcode"], r["region"], decision(r)["status"])
                      for role, rs in [("selected", selected), ("reserve", reserves)] for r in rs if blocked(r)}
    impact_blocked = {(r["role"], r["barcode"], r["region"], r["eligibility"])
                      for r in impact if r["eligibility"] in {"excluded", "hold"}}
    require("blocked_exact_keys_match_frozen_impact", actual_blocked == impact_blocked and len(actual_blocked) == 118)
    impact_lookup = {(r["role"], r["barcode"], r["region"]): r for r in impact}
    require("all_beverage_rows_match_impact", all(
        (r["role"], r["barcode"], r["region"]) in impact_lookup
        for r in impact) and len(impact_lookup) == len(impact) == 4156 and all(
            (i := impact_lookup[(role, row["barcode"], row["region"])])["eligibility"]
            == (decision(row)["status"] if decision(row) else "eligible")
            and i["sampling_group_id"] == row["sampling_group_id"]
            and i["country_cell"] == row["country_cell"]
            and i["sampling_component"] == row["accounting_component"]
            and i["manifest_sha256"] == before[src]
            for role, rs, src in [("selected", selected, SELECTED), ("reserve", reserves, RESERVES)]
            for row in rs if row["category"] == "beverages"))

    source_selected = {int(r["step2_source_row"]): r for r in candidates + blocked_selected}
    require("source_columns_gtin_country_sampling_and_evidence_preserved", all(
        all(source_selected[i][f] == row[f] for f in sf) for i, row in enumerate(selected, 1)))
    leading_zeros = {role: sum(r["barcode"].startswith("0") for r in rs)
                     for role, rs in [("original_selected", selected), ("retained", candidates),
                                      ("blocked_selected", blocked_selected), ("original_reserves", reserves),
                                      ("reconciled_reserves", reserve_register)]}

    vacancy_fields = ["slot_id", "barcode", "region", "category", "sampling_group_id", "country_cell",
                      "accounting_component", "vacancy_origin", "reason", "disposition",
                      "selected_source_row", "original_draw_barcode", "decision_source", "decision_authority",
                      "decision_sidecar_sha256", "replacement_promoted"]
    vacancies = []
    for row in unfilled:
        vacancies.append({**{f: row.get(f, "") for f in vacancy_fields}, "vacancy_origin": "preexisting_v2_shortfall",
                          "replacement_promoted": "False"})
    for row in blocked_selected:
        vacancies.append(dict(slot_id=row["slot_id"], barcode=row["barcode"], region=row["region"],
                              category=row["category"], sampling_group_id=row["sampling_group_id"],
                              country_cell=row["country_cell"], accounting_component=row["accounting_component"],
                              vacancy_origin="locked_beverage_" + row["step2_beverage_status"],
                              reason=row["step2_beverage_reason"], disposition="vacant_pending_review_no_promotion",
                              selected_source_row=row["step2_source_row"], original_draw_barcode=row["original_draw_barcode"],
                              decision_source=row["step2_beverage_decision_source"],
                              decision_authority=row["step2_beverage_decision_authority"],
                              decision_sidecar_sha256=before[DECISIONS], replacement_promoted="False"))
    require("168_unique_vacant_slots_without_promotion", len(unfilled) == 63 and len(vacancies) == 168
            and len({r["slot_id"] for r in vacancies}) == 168
            and {r["slot_id"] for r in candidates}.isdisjoint({r["slot_id"] for r in vacancies}))

    quotas = Counter()
    for row in plan:
        quotas[(row["sampling_group_id"], row["country_cell"], "random_baseline")] += int(row["random_baseline"])
        if int(row["targeted_attempts"]):
            quotas[(row["sampling_group_id"], row["country_cell"], TARGETS[row["target_component"]])] += int(row["targeted_attempts"])
    retained_n = Counter(cell(r) for r in candidates)
    blocked_n = Counter(cell(r) for r in blocked_selected)
    vacancy_n = Counter(cell(r) for r in vacancies)
    original_gap_n = Counter(cell(r) for r in unfilled)
    reserves_n = Counter(cell(r) for r in reserves)
    qualified_n = Counter(cell(r) for r in qualified_reserves)
    blocked_reserve_n = Counter(cell(r) for r in blocked_reserves)
    require("24_groups_56_country_cells_quotas_unchanged", len(allocation) == 24 and len(plan) == 56
            and sum(quotas.values()) == 12000 and len({r["sampling_group_id"] for r in plan}) == 24
            and len({(r["region"], r["category"]) for r in plan}) == 11
            and all(retained_n[k] + vacancy_n[k] == n for k, n in quotas.items())
            and all(cell(r) in quotas for r in candidates + vacancies + reserves))
    require("us_ca_dairy_missing_m1_retries_remain_excluded", approval["approved_design"]["us_ca_dairy_excluded"]
            and not any(r["region"] == "US+CA" and r["category"] == "dairies" for r in candidates + reserves)
            and all(r["m1_eligible"] == "1" and r["available_first_attempt"] == "1" for r in candidates + reserves))
    meta = {r["sampling_group_id"]: (r["region"], r["category"]) for r in allocation}
    availability = []
    for k, quota in quotas.items():
        group, country, component = k
        availability.append(dict(sampling_group_id=group, region=meta[group][0], category=meta[group][1],
            country_cell=country, accounting_component=component, approved_quota=quota,
            retained_candidates=retained_n[k], preexisting_v2_vacancies=original_gap_n[k],
            newly_blocked_selected=blocked_n[k], vacancies=vacancy_n[k], original_remaining_reserves=reserves_n[k],
            blocked_reserves=blocked_reserve_n[k], eligibility_qualified_matching_reserves=qualified_n[k],
            arithmetic_shortfall_if_all_matching_reserves_passed=max(0, vacancy_n[k] - qualified_n[k]),
            promoted_reserves=0, technical_executability="not_certified"))
    potential, matching_position = [], Counter()
    for row in qualified_reserves:
        k = cell(row)
        if vacancy_n[k]:
            matching_position[k] += 1
            potential.append(dict(barcode=row["barcode"], region=row["region"], category=row["category"],
                countries=row["countries"], sampling_group_id=k[0], country_cell=k[1], accounting_component=k[2],
                reserve_source_row=row["step2_source_row"], draw_stage=row["draw_stage"], draw_rank=row["draw_rank"],
                matching_sequence=matching_position[k], matching_vacancies=vacancy_n[k],
                status="potential_only_pending_technical_validation", promoted="False"))
    reserve_by_row = {r["step2_source_row"]: r for r in reserve_register}
    require("potential_replacements_match_exact_cell_component_and_frozen_order", all(
        cell(r) == cell(reserve_by_row[r["reserve_source_row"]])
        and reserve_by_row[r["reserve_source_row"]]["step2_eligibility_qualified"] == "1"
        and vacancy_n[cell(r)] > 0 and r["promoted"] == "False" for r in potential)
        and [int(r["reserve_source_row"]) for r in potential] == sorted(int(r["reserve_source_row"]) for r in potential))

    group_summary = []
    for row in allocation:
        group = row["sampling_group_id"]
        rs = [r for r in availability if r["sampling_group_id"] == group]
        group_summary.append(dict(sampling_group_id=group, region=row["region"], category=row["category"],
            approved_quota=int(row["proposed_new_attempts"]), retained_candidates=sum(r["retained_candidates"] for r in rs),
            newly_blocked_selected=sum(r["newly_blocked_selected"] for r in rs), vacancies=sum(r["vacancies"] for r in rs),
            eligibility_qualified_reserves=sum(r["eligibility_qualified_matching_reserves"] for r in rs),
            arithmetic_shortfall_if_all_matching_reserves_passed=sum(r["arithmetic_shortfall_if_all_matching_reserves_passed"] for r in rs),
            promoted_reserves=0))
    country_summary = []
    for row in plan:
        rs = [r for r in availability if r["sampling_group_id"] == row["sampling_group_id"] and r["country_cell"] == row["country_cell"]]
        country_summary.append(dict(sampling_group_id=row["sampling_group_id"], region=row["region"], category=row["category"],
            country_cell=row["country_cell"], approved_quota=int(row["proposed_primary_attempts"]),
            retained_candidates=sum(r["retained_candidates"] for r in rs), vacancies=sum(r["vacancies"] for r in rs),
            eligibility_qualified_reserves=sum(r["eligibility_qualified_matching_reserves"] for r in rs), promoted_reserves=0))
    require("all_group_and_country_quotas_reconcile", all(r["approved_quota"] == r["retained_candidates"] + r["vacancies"]
                                                            for r in group_summary + country_summary))
    retained_slots = {r["slot_id"] for r in candidates}
    vacant_slots = {r["slot_id"] for r in vacancies}
    link_annotations = []
    for i, row in enumerate(links, 1):
        state = "retained_candidate" if row["owner_slot_id"] in retained_slots else (
            "vacant_pending_review" if row["owner_slot_id"] in vacant_slots else "unresolved_original_owner_reference")
        link_annotations.append(dict(source_link_row=i, owner_slot_id=row["owner_slot_id"],
            owner_slot_step2_state=state, reassigned="False",
            note="Original link preserved as provenance; secondary coverage is not newly certified."))
    require("no_original_execution_or_paid_flags_enabled", all(
        r["execution_authorized"] == "False" and r["planned_paid_job"] == "0" for r in candidates + reserve_register))

    OUT.mkdir()
    (OUT / ".gitignore").write_text("# Local product-level reconciliation evidence; no publication approval.\n*\n", encoding="utf-8")
    write_csv("candidate_selected_manifest.csv", sf + extra, candidates)
    write_csv("blocked_selected_register.csv", sf + extra, blocked_selected)
    write_csv("eligibility_reconciled_reserves.csv", rf + extra, reserve_register)
    write_csv("vacancies.csv", vacancy_fields, vacancies)
    for name, rs in [("vacancy_reserve_availability.csv", availability),
                     ("potential_replacements.csv", potential), ("group_reconciliation.csv", group_summary),
                     ("country_cell_reconciliation.csv", country_summary),
                     ("secondary_link_step2_annotations.csv", link_annotations)]:
        write_csv(name, list(rs[0]), rs)
    for source, target in [(LINKS, "secondary_coverage_links_frozen.csv"),
                           (ALLOCATION, "approved_group_quotas_frozen.csv"),
                           (COUNTRY_PLAN, "approved_country_component_plan_frozen.csv")]:
        (OUT / target).write_bytes(source_bytes[source])
    require("duplicate_evidence_links_and_approved_quota_copies_byte_identical", all(
        (OUT / target).read_bytes() == source_bytes[source]
        for source, target in [(LINKS, "secondary_coverage_links_frozen.csv"),
                               (ALLOCATION, "approved_group_quotas_frozen.csv"),
                               (COUNTRY_PLAN, "approved_country_component_plan_frozen.csv")]))
    after = {name: digest((BASE / name).read_bytes()) for name in SOURCES}
    require("all_immediate_source_hashes_unchanged_after_writing", before == after)
    # Read serialized CSVs back to verify exact GTIN strings, row order and fields.
    require("serialized_source_columns_and_row_order_roundtrip", all(
        [dict((f, r[f]) for f in fields) for r in read_csv((OUT / name).read_bytes())[1]]
        == [dict((f, r[f]) for f in fields) for r in expected]
        for name, fields, expected in [("candidate_selected_manifest.csv", sf, candidates),
            ("blocked_selected_register.csv", sf, blocked_selected),
            ("eligibility_reconciled_reserves.csv", rf, reserves)]))
    counts = dict(original_selected=11937, retained_candidates=len(candidates), blocked_selected=dict(selected_counts),
                  original_reserves=2233, eligibility_qualified_reserves=len(qualified_reserves), blocked_reserves=dict(reserve_counts),
                  qualified_beverage_reserves=580, preexisting_vacancies=63, vacancies=len(vacancies),
                  matching_potential_reserves=len(potential), group_quotas=24, group_country_cells=56,
                  group_country_component_cells=len(availability), preserved_secondary_links=len(links),
                  secondary_links_with_vacant_owner=sum(r["owner_slot_step2_state"] == "vacant_pending_review" for r in link_annotations),
                  promoted_reserves=0, paid_calls=0)
    write_json("validation.json", dict(status="PASS", checks=checks, leading_zero_gtin_counts=leading_zeros,
                                       counts=counts, source_hashes_unchanged=True))
    generated = sorted(p.name for p in OUT.iterdir() if p.is_file())
    hashes = {name: digest((OUT / name).read_bytes()) for name in generated}
    shortage = [r for r in availability if r["arithmetic_shortfall_if_all_matching_reserves_passed"]]
    table = "\n".join(f"| {r['sampling_group_id']} | {r['country_cell']} | {r['accounting_component']} | {r['vacancies']} | {r['eligibility_qualified_matching_reserves']} | {r['arithmetic_shortfall_if_all_matching_reserves_passed']} |" for r in shortage)
    report = f"""# RUN 06B — Step 2 eligibility reconciliation, v1

Status: **PASS — candidate preparation only; pending Julia's review before Step 3.**

Julia approved Step 1 and authorized only Step 2. The draw and eligibility rules were not recomputed.

| Population | Original | Retained / eligibility-qualified | EXCLUDE | HOLD |
|---|---:|---:|---:|---:|
| Selected | 11,937 | 11,832 | 39 | 66 |
| Remaining reserves | 2,233 | 2,220 | 6 | 7 |
| Beverage reserves | 593 | 580 | 6 | 7 |

**168 vacant positions** = 63 preexisting v2 shortfalls + 105 blocked selected records.
All 24 group quotas, 56 group/country cells and the 12,000 allocation remain unchanged.
US+CA dairy, missing-M1 work and retries stay outside the allocation.

## Method and limits

Applied the locked sidecar only to category `beverages` by exact text `(barcode, region)`.
Every original source column is preserved. Prefixed Step 2 fields record decisions and retain the full sidecar reason, evidence, authority and provenance.
Absence of a sidecar decision means no locked cleaning decision was supplied; it does not imply individual review or technical approval.
Selected partitions retain their original relative order. The 2,233-row reserve register retains the entire frozen sequence, including the 13 blocked rows.
Potential replacements are listed in that frozen sequence, only for an exact group × country cell × accounting component with vacancies.
No target-to-random conversion, cross-cell transfer, draw, replacement or promotion occurred.

The frozen duplicate-evidence link table is copied byte-for-byte ({len(links)} links).
{counts['secondary_links_with_vacant_owner']} links reference an owner slot now vacant; the separate annotation table flags this without deleting links or reassigning ownership.
All original evidence/configuration and execution blocks remain. Source image paths are metadata only; no image was opened or decoded.

## Matching reserve availability

`vacancy_reserve_availability.csv` covers {len(availability)} approved group/country/component cells.
`potential_replacements.csv` lists {len(potential)} eligibility-qualified reserves in cells with vacancies; these are options, not assignments to slots.
The counts below are arithmetic shortages assuming every matching reserve passes later checks. They do not certify independent paid work, image usability or executability; later losses may increase shortages.

| Group | Country cell | Component | Vacancies | Qualified matching reserves | Arithmetic shortage |
|---|---|---|---:|---:|---:|
{table}

Existing quota shortages remain explicit. No quota transfer or promotion is proposed or authorized by this package.

## Validation

All {len(checks)} checks PASS. Selected records partition exactly once into 11,832 candidates and 105 blocked records; all 2,233 reserves are accounted for once.
The 105/13 exact blocked identities and statuses match BEVERAGE FINAL's saved impact table; every impact row's group, country, component and source-manifest hash agrees.
Serialized CSV roundtrips preserve every original field, including leading-zero GTINs, countries, sampling reasons, evidence keys, provisional ownership and unresolved paid-work keys.
All 168 slot IDs are unique, disjoint from retained slots and remain vacant.
Source hashes matched immediately before and after writing. Step 1's broad verification was not repeated.

## Files and SHA256

`candidate_selected_manifest.csv`, `blocked_selected_register.csv` and `eligibility_reconciled_reserves.csv` are the principal row-level outputs.
`vacancies.csv`, `potential_replacements.csv`, component/country/group summaries and the preserved evidence-link tables provide the audit trail.
Full hashes of every output, including this report and the package manifest, are in `checksums.sha256`.

| Output | SHA256 |
|---|---|
"""
    report += "\n".join(f"| `{name}` | `{value}` |" for name, value in hashes.items())
    report += "\n\n## Source references\n\n| Frozen source | SHA256 |\n|---|---|\n"
    report += "\n".join(f"| `presentations/segmentation/{name}` | `{value}` |" for name, value in before.items())
    report += "\n\n**STOP — Julia's Step 2 review is required before Step 3. No executable manifest was generated and no OCR/LLM calls were made.**\n"
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    hashes["REPORT.md"] = digest((OUT / "REPORT.md").read_bytes())
    write_json("manifest.json", dict(package="RUN_06B_STEP2_V1", status="candidate_only_pending_Julia_review",
        created_at_utc=datetime.now(timezone.utc).isoformat(), script=str(Path(__file__).relative_to(ROOT).as_posix()),
        script_sha256=digest(Path(__file__).read_bytes()), source_files_sha256=before, source_files_after_sha256=after,
        outputs_sha256=hashes, counts=counts, validation="validation.json", reserves_promoted=False,
        paid_work_ownership_reassigned=False, image_usability_certified=False, executable_manifest_generated=False,
        execution_authorized=False, continuation="STOP_before_Step_3", product_artifacts_local_only=True))
    hashes["manifest.json"] = digest((OUT / "manifest.json").read_bytes())
    (OUT / "checksums.sha256").write_text("".join(f"{value}  {name}\n" for name, value in sorted(hashes.items())), encoding="utf-8")
    print(json.dumps(dict(package=str(OUT), counts=counts, validation=checks,
                          arithmetic_shortage_cells=shortage, leading_zero_gtin_counts=leading_zeros), indent=2))


if __name__ == "__main__":
    main()
