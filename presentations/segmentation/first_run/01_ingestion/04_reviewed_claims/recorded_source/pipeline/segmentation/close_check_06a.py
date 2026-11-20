"""Reconcile RUN 06A costs and record Julia's 2026-10-22 approval.

Documentation/aggregate-CSV work only. No extraction, sampling, preflight or
paid calls. Original draft snapshots are required and are never overwritten.
--verify-only reconstructs the closure bytes and verifies all frozen hashes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "presentations/segmentation/run_06a_v1"
SNAPSHOT = OUT / "source_snapshots/check_06a_original_draft_20261022"
REPORT = ROOT / "presentations/segmentation/RUN 06A_no US.md"
MANIFEST = OUT / "run_06a_manifest.json"
APPROVAL = OUT / "check_06a_approval.json"
GENERATOR = ROOT / "pipeline/segmentation/run_06a_allocation_design.py"
STATUS = "CHECK 06A approved and closed; design only; selection and execution not authorized"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline="")))


def csv_bytes(records):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8-sig")


def replace_once(text, old, new):
    assert text.count(old) == 1, f"Expected one document fragment: {old[:100]}"
    return text.replace(old, new, 1)


def original(path):
    return (SNAPSHOT / rel(path)).read_bytes()


def verify_snapshot_and_inputs():
    index = json.loads((SNAPSHOT / "snapshot_index.json").read_text(encoding="utf-8"))
    for entry in index["files"].values():
        assert sha(ROOT / entry["snapshot_path"]) == entry["sha256"], entry["snapshot_path"]
    draft = json.loads(original(MANIFEST))
    assert draft["status"] == "CHECK 06A - Pending approval"
    for name, value in draft["inputs_sha256"].items():
        assert sha(ROOT / name) == value, f"Approved baseline changed: {name}"
    assert index["files"][rel(MANIFEST)]["sha256"] == digest(original(MANIFEST))
    for name, value in draft["outputs_sha256"].items():
        assert digest(original(ROOT / name)) == value
    assert digest(original(GENERATOR)) == draft["script_sha256"]
    return draft, index


def changed_status_only(data, field, predicate=lambda row: True):
    before = rows(data)
    after = [dict(row) for row in before]
    for row in after:
        if predicate(row):
            row[field] = STATUS
    for left, right in zip(before, after):
        assert {k: v for k, v in left.items() if k != field} == {
            k: v for k, v in right.items() if k != field}
    return csv_bytes(after)


def build_closure():
    draft, snapshot_index = verify_snapshot_and_inputs()
    payloads = {ROOT / name: original(ROOT / name) for name in draft["outputs_sha256"]}
    for filename, field in [("proposed_allocation.csv", "approval_status"),
                            ("country_component_plan.csv", "status")]:
        path = OUT / filename
        payloads[path] = changed_status_only(payloads[path], field)
    path = OUT / "allocation_scenarios.csv"
    payloads[path] = changed_status_only(payloads[path], "approval_status", lambda r: r["scenario_id"] == "core_12000")

    costs = []
    for old in rows(original(OUT / "budget_scenarios.csv")):
        row = {k: v for k, v in old.items() if k not in {"proposed_cost_envelope_chf", "status"}}
        jobs = int(row["planned_processing_attempts_cap"])
        row.update({
            "best_estimate_chf_per_processing_job": .002,
            "best_estimated_cost_chf": round(jobs * .002, 2),
            "planning_contingency_fraction": .25,
            "planning_budget_chf": round(jobs * .002 * 1.25, 2),
            "planning_budget_is_enforceable_hard_ceiling": False,
            "planning_estimate_basis": "Julia's observed approximately CHF 0.002 per processing job; CHECK 06A reconciliation 2026-10-22",
            "multiple_call_stress_rounded_allowance_chf": int(old["proposed_cost_envelope_chf"]),
            "multiple_call_stress_role": "Conservative risk scenario only; not expected spend, planning budget or authorized spending",
            "optional_historical_beverage_backfill_included": False,
            "status": (STATUS if row["scenario_id"] == "core_12000" else
                       "Unapproved alternative only; does not change approved core_12000"),
        })
        assert float(row["stress_estimated_cost_chf"]) == round(jobs * (2 * .0015 + 3 * .0002) * 1.25, 2)
        costs.append(row)
    payloads[OUT / "budget_scenarios.csv"] = csv_bytes(costs)
    core_cost = next(x for x in costs if x["scenario_id"] == "core_12000")
    assert core_cost["best_estimated_cost_chf"] == 24
    assert core_cost["planning_budget_chf"] == 30
    assert core_cost["multiple_call_stress_rounded_allowance_chf"] == 60

    rule_path = OUT / "selection_rules.md"
    rules = original(rule_path).decode("utf-8")
    rules = replace_once(rules,
        "**CHECK 06A: Pending approval. Specification only. No product selection, preflight or paid work has occurred.**",
        "**CHECK 06A: Approved and closed, 22 October 2026. Selection-design specification approved. Preparation of RUN 06B is authorized; product selection, image preflight and paid work are not authorized by this decision.**")
    old_cost = next(p for p in rules.split("\n\n") if p.startswith("Pipeline defaults used only for planning:"))
    new_cost = (
        "Approved cost planning for 12,000 first-attempt jobs: **CHF 24 best estimate**, based on approximately CHF 0.002 per processing job observed by Julia, and **CHF 30 planning budget**, including 25% contingency. CHF 30 is not an enforceable hard ceiling: actual provider-call accounting and spending guards have not been validated. The allocation is approved; the executable attempt cap and enforceable spending ceiling require separate approval. No missing-M1 processing, retries or optional historical beverage backfill are included in the core.\n\n"
        "Separate conservative multiple-call risk scenario retained from the original draft: local defaults OCR CHF 1.50 / 1,000 calls and LLM CHF 0.20 / 1,000 calls; 2 OCR + 3 LLM calls for every job plus 25% contingency yields CHF 54, rounded to CHF 60. This is not expected spend or the approved planning budget and authorizes no additional spending. The one-OCR/one-LLM default calculation (CHF 0.0017/job, CHF 20.40 for 12,000) is retained as a technical reference only; the approved best estimate is CHF 0.002/job. Provider retries can exceed modelled call allowances. Default CostTracker counts logical OCR invocations and can omit underlying retries. The existing CHF 45 default alert is not a validated new-run ceiling. Validate complete-call accounting and a stop-before-next-call spending guard before any paid execution."
    )
    rules = replace_once(rules, old_cost, new_cost)
    rules += "\n## 9. CHECK 06A approval and authorization boundary\n\n" + (
        "Julia approved the 12,000-attempt allocation, all 24 group quotas, the existing country allocation rules, random/targeted components, RUN 06B selection rules, sampling-quality requirements and updated cost planning on 22 October 2026. Zero missing-M1 processing and zero retries are approved for the core. Optional historical beverage backfill remains outside it. The exact files and hashes are recorded in `check_06a_approval.json`.\n\n"
        "This decision authorizes preparation of RUN 06B only. It does not authorize selecting product barcodes tonight, image preflight, paid OCR/LLM processing, historical beverage reprocessing, or changes to hydration/electrolyte taxonomy or extraction prompts. Selection/preflight require a later explicit instruction. The exact executable manifest, validated extraction configuration, pilot, executable attempt cap and enforceable spending ceiling require separate approval. No RUN 06B action is performed by this documentation closure.\n"
    )
    payloads[rule_path] = rules.encode("utf-8")

    report = original(REPORT).decode("utf-8")
    report = replace_once(report,
        "**CHECK 06A — Pending approval. Prepared 22 October 2026. Recommendation: Proceed with the proposed design after approval and RUN 06B validation.**",
        "**CHECK 06A — Approved and closed. Decision date: 22 October 2026. Allocation and selection design approved; preparation of RUN 06B only is authorized.**")
    report = replace_once(report, "## Recommended decision", "## Approved decision")
    report = replace_once(report, "Propose **12,000 additional first-attempt jobs**", "Approved allocation: **12,000 additional first-attempt jobs**")
    report = replace_once(report, "Propose **zero missing-M1 jobs and zero retries in the core scenario**.", "Approved core scope: **zero missing-M1 jobs and zero retries**; optional historical beverage backfill is excluded.")
    report = replace_once(report,
        "Proposed cost envelope: **CHF 60**, subject to actual deployment/prices and complete-call accounting before execution. This is not paid-run approval.",
        "Approved planning figures: **CHF 24 best estimate** and **CHF 30 planning budget**, including 25% contingency. CHF 30 is not an enforceable hard ceiling until actual provider-call accounting and spending guards have been validated. The previous CHF 60 multiple-call stress allowance is retained separately as a conservative risk scenario. This is not paid-run approval.")
    report = replace_once(report, "### All 24 groups — principal approval table", "### All 24 groups — approved allocation table")
    old_cost_paragraph = next(p for p in report.split("\n\n") if p.startswith("Stage 10 defaults estimate OCR"))
    report = replace_once(report, old_cost_paragraph,
        "### Approved expected cost and planning budget\n\n"
        "Julia's observed cost of approximately **CHF 0.002 per processing job** is the approved planning basis: **12,000 × CHF 0.002 = CHF 24 best estimate**. A **25% contingency adds CHF 6**, giving a **CHF 30 planning budget**. This is a planning amount, not a validated enforceable hard ceiling or paid-execution authorization. The job allocation remains 12,000; contingency does not authorize extra jobs, missing-M1 work, retries or historical beverage reruns. Actual provider-call accounting, validated extraction configuration, a pilot and enforceable spending guards require separate approval before execution.\n\n"
        "### Separate conservative multiple-call risk scenario\n\n"
        "The original draft's **CHF 60** remains as a conservative risk scenario only. It assumes 2 OCR + 3 LLM calls for every job at Stage 10's local estimate defaults (CHF 1.50 and CHF 0.20 per 1,000 calls), plus 25% contingency: CHF 54, rounded upward to CHF 60. It is not expected spend, the CHF 30 planning budget or authorization to spend CHF 60. The original one-OCR/one-LLM calculation of CHF 20.40 is a technical reference; the approved best estimate is CHF 24. Historical approximate Azure spend (CHF 12/11,850 English products and CHF 8/6,170 French products) remains background evidence, not verified current all-in tariffs. The current tracker counts logical OCR invocations and may omit underlying retries; its default CHF 45 alert is not a validated run ceiling.")
    old_table = re.search(r"\| Scenario \| Jobs cap \|.*?(?=\n\n)", report, flags=re.S)
    assert old_table
    table = ["| Scenario | Jobs allocation | Missing M1 | Retries | Expected success | Best estimate CHF | Planning budget CHF | Separate stress allowance CHF |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in costs:
        table.append("| " + " | ".join(str(row[k]) for k in ["scenario_id", "planned_processing_attempts_cap", "optional_missing_m1_attempts", "optional_retry_attempts", "expected_successful_extractions", "best_estimated_cost_chf", "planning_budget_chf", "multiple_call_stress_rounded_allowance_chf"]) + " |")
    report = report[:old_table.start()] + "\n".join(table) + report[old_table.end():]
    report = replace_once(report,
        "Recommend leaving both optional components at zero for the core approval.",
        "Both optional components are approved at zero in the core; the alternatives below remain unapproved.")
    report = replace_once(report,
        "Recommend 12,000 because it expects about 11,000 usable outcomes while retaining margin below 15,000 jobs.",
        "The approved scenario is core_12000; 10,000 / 15,000 and optional-pool scenarios remain unapproved alternatives. The 12,000 allocation expects about 11,000 usable outcomes while retaining margin below 15,000 jobs.")
    report = replace_once(report,
        "## CHECK 06A — Decisions requested\n\n1. Approve or adjust the recommended 12,000-slot, 24-group allocation and its country-cell composition.\n2. Approve or adjust the random/fibre/preparation components, their thresholds, precedence, reserves and deviation rules.\n3. Choose whether to keep missing-M1 exploration and retries at zero as recommended, or explicitly approve an optional variant with its detailed suballocation.\n4. Approve or adjust the provisional CHF 60 envelope and planning expectations, subject to validated current deployment/pricing and complete-call guard before paid execution.\n5. Authorize RUN 06B reproducible local selection and bounded preflight separately. Paid processing remains a later decision and is launched by Julia.",
        "## CHECK 06A — Approval and closure\n\n"
        "**Decision: CHECK 06A approved. Decision date: 22 October 2026. Approved by: Julia.**\n\n"
        "Approval covers the 12,000-first-attempt allocation across 24 sampling groups in 11 strata, exact existing group quotas, country allocation rules and random/targeted components; the proposed RUN 06B selection rules and sampling-quality validation requirements; and the reconciled cost assumptions of CHF 24 best estimate / CHF 30 planning budget. Zero missing-M1 processing and zero retries are included in the core. US/CA dairy remains excluded. Alternative budgets and optional pools remain unapproved.\n\n"
        "The [machine-readable approval record](run_06a_v1/check_06a_approval.json) references the exact approved files and hashes. The [immutable original draft snapshot index](run_06a_v1/source_snapshots/check_06a_original_draft_20261022/snapshot_index.json) preserves all nine original outputs, the original manifest and generating script byte-for-byte. The updated manifest records the snapshot, current output hashes and revised cost basis. Numeric allocation fields and selection logic are unchanged; approval status fields are updated only for the approved core. The sampling-quality specification is unchanged.\n\n"
        "### Authorization boundary\n\n"
        "CHECK 06A approval authorizes **preparation of RUN 06B only**. It does **not** authorize:\n\n"
        "- Selecting product barcodes tonight; later selection needs a separate explicit instruction.\n"
        "- Image preflight.\n"
        "- Paid OCR/LLM processing.\n"
        "- Historical beverage reprocessing or optional beverage backfill.\n"
        "- Changing the hydration/electrolyte taxonomy or extraction prompts.\n\n"
        "The exact executable manifest, validated extraction configuration, pilot, executable attempt cap and enforceable spending ceiling require **separate approval**. No RUN 06B activity is performed in this closure.\n\n"
        "The separately discussed approximately CHF 10 for possible historical beverage reprocessing is a provisional discussion estimate only, excluded from both the CHF 24 core estimate and CHF 30 planning budget; no beverage processing or prompt changes are approved here.")
    report = replace_once(report,
        "- [Reproducible design script](../../pipeline/segmentation/run_06a_allocation_design.py)",
        "- [Reproducible design / approved-artifact verification](../../pipeline/segmentation/run_06a_allocation_design.py)\n"
        "- [Reproducible cost reconciliation and closure verification](../../pipeline/segmentation/close_check_06a.py)\n"
        "- [CHECK 06A approval record](run_06a_v1/check_06a_approval.json)\n"
        "- [Immutable original draft snapshot index](run_06a_v1/source_snapshots/check_06a_original_draft_20261022/snapshot_index.json)")
    report = replace_once(report,
        "**CHECK 06A — Pending approval. Stop before barcode selection, image preflight or paid OCR/LLM processing.**",
        "Closure validation: all 26 baseline input hashes verified unchanged; 11 original draft files preserved and checksummed; 24 group quotas, 56 country/component cells, component sums and all numeric design fields verified unchanged. Only cost planning and approval metadata changed. No source extraction, candidate selection, preflight, pilot or paid calls were performed.\n\n"
        "**CHECK 06A approved and closed. Stop after documentation and validation. RUN 06B preparation is authorized, but no selection, preflight or paid execution is authorized by this decision.**")
    payloads[REPORT] = report.encode("utf-8")

    allocation = rows(payloads[OUT / "proposed_allocation.csv"])
    cells = rows(payloads[OUT / "country_component_plan.csv"])
    assert len(allocation) == 24 and len(cells) == 56
    assert len({(r["region"], r["category"]) for r in allocation}) == 11
    assert sum(int(r["proposed_new_attempts"]) for r in allocation) == 12000
    assert sum(int(r["proposed_primary_attempts"]) for r in cells) == 12000
    components = {key: sum(int(r[key]) for r in allocation) for key in ["random_baseline", "targeted_upper_fibre", "targeted_beverage_preparation_or_specialist", "missing_m1_attempts", "retry_attempts"]}
    assert list(components.values()) == [10263, 1246, 491, 0, 0]
    for r in allocation:
        children = [c for c in cells if c["sampling_group_id"] == r["sampling_group_id"]]
        q = int(r["proposed_new_attempts"])
        assert sum(int(c["proposed_primary_attempts"]) for c in children) == q
        assert q + math.ceil(.25 * q) <= int(r["remaining_eligible_first_attempts"])

    index_path = SNAPSHOT / "snapshot_index.json"
    manifest = dict(draft)
    manifest.update({
        "status": "CHECK 06A - Approved and closed",
        "decision_date": "2026-10-22",
        "approval_record": rel(APPROVAL),
        "approval_record_hash_location": "Approval record hashes this manifest; manifest does not hash the approval record to avoid circularity.",
        "script_sha256": sha(GENERATOR),
        "cost_reconciliation_script": rel(Path(__file__)),
        "cost_reconciliation_script_sha256": sha(Path(__file__)),
        "original_draft_snapshot_index": {"path": rel(index_path), "sha256": sha(index_path)},
        "approved_scenario": "core_12000",
        "cost_planning": {"first_attempt_jobs": 12000, "best_estimate_chf_per_job": .002,
                          "best_estimate_chf": 24, "contingency_fraction": .25,
                          "planning_budget_chf": 30, "planning_budget_is_enforceable_hard_ceiling": False,
                          "separate_multiple_call_risk_allowance_chf": 60,
                          "risk_allowance_is_expected_cost": False,
                          "optional_beverage_backfill_included": False},
        "outputs_sha256": {rel(p): digest(b) for p, b in payloads.items()},
        "closure_validation": {"baseline_inputs_verified_unchanged": len(draft["inputs_sha256"]),
                               "immutable_original_files": len(snapshot_index["files"]),
                               "groups": 24, "country_component_cells": 56, "attempts": 12000,
                               "numeric_allocation_fields_unchanged": True,
                               "selection_quality_specification_unchanged": True,
                               "selection_rules_design_unchanged": True,
                               "cost_and_approval_metadata_only": True,
                               "no_run_06b_actions": True, "image_requests": 0, "ocr_llm_calls": 0},
    })
    payloads[MANIFEST] = json_bytes(manifest)
    approved_files = {rel(p): digest(b) for p, b in payloads.items()}
    approved_files.update({rel(GENERATOR): sha(GENERATOR), rel(Path(__file__)): sha(Path(__file__)),
                           rel(index_path): sha(index_path)})
    approval = {
        "check": "CHECK 06A", "status": "Approved and closed", "decision_date": "2026-10-22",
        "approved_by": "Julia", "authorization": "Explicit IMPLEMENT instruction: RUN 06A cost reconciliation and CHECK 06A closure.",
        "approved_scenario": "core_12000", "approved_files_sha256": approved_files,
        "approved_baseline_inputs_sha256": draft["inputs_sha256"],
        "original_draft_snapshot_index": {"path": rel(index_path), "sha256": sha(index_path)},
        "approved_design": {"first_attempts": 12000, "groups": 24, "strata": 11,
                            "group_quotas_unchanged": True, "country_allocation_rules_unchanged": True,
                            "components": components, "selection_rules_approved": True,
                            "sampling_quality_requirements_approved": True,
                            "missing_m1_jobs": 0, "retry_jobs": 0,
                            "us_ca_dairy_excluded": True, "optional_beverage_backfill_included": False},
        "approved_cost_planning": manifest["cost_planning"],
        "authorized_now": {"documentation_and_validation": True, "preparation_of_run_06b": True,
                           "barcode_selection": False, "image_preflight": False, "paid_ocr_llm_processing": False,
                           "historical_beverage_reprocessing": False, "hydration_electrolyte_taxonomy_changes": False,
                           "extraction_prompt_changes": False, "pilot_execution": False},
        "separate_approval_required": ["Product barcode selection and image preflight",
                                       "Exact executable manifest", "Validated extraction configuration",
                                       "Pilot", "Executable attempt cap", "Enforceable spending ceiling",
                                       "Paid OCR/LLM processing", "Historical beverage reprocessing or prompt/taxonomy changes"],
        "beverage_rerun_discussion": {"additional_estimate_discussed_chf": 10, "approved": False,
                                     "excluded_from_core_estimate_and_planning_budget": True},
        "validation": manifest["closure_validation"],
    }
    payloads[APPROVAL] = json_bytes(approval)
    return payloads, draft


def verify_closure():
    payloads, draft = build_closure()
    for path, data in payloads.items():
        assert path.read_bytes() == data, f"Approved file differs from reproducible closure: {rel(path)}"
    for path in [REPORT, OUT / "selection_rules.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip("<>")
            if "://" not in target:
                assert (path.parent / target).exists(), target
    print(json.dumps({"status": "CHECK 06A approved and closed", "reproducible_closure_files": len(payloads),
                      "unchanged_input_hashes": len(draft["inputs_sha256"]),
                      "attempts": 12000, "groups": 24, "best_estimate_chf": 24,
                      "planning_budget_chf": 30, "risk_scenario_chf": 60,
                      "selection_preflight_paid_calls": 0}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--apply", action="store_true")
    actions.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify_closure()
        return
    assert not APPROVAL.exists(), "CHECK 06A approval already exists; use --verify-only."
    payloads, draft = build_closure()
    # The existing draft must still match the preserved original; never clobber
    # a separately edited document or an approved artifact.
    for name, value in draft["outputs_sha256"].items():
        assert sha(ROOT / name) == value, f"Original draft changed: {name}"
    assert MANIFEST.read_bytes() == original(MANIFEST)
    for path, data in payloads.items():
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    verify_closure()


if __name__ == "__main__":
    main()
