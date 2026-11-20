"""Create local runner-readiness artifacts only; never invokes a provider."""
from __future__ import annotations
import csv
import io
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from dotenv import dotenv_values
from pipeline.vision_ops.run_06b_runner import ROOT, PACKAGE, KINDS, sha, stable_hash, emerging

OUT = ROOT / "presentations/segmentation/run_06b_runner_validation_v1"
SOURCE = PACKAGE / "proposed_primary_processing_manifest.csv"
CODE = ["pipeline/vision_ops/run_06b_runner.py", "pipeline/vision_ops/run_06b_execution_guard.py",
        "pipeline/vision_ops/emerging_benefits_stage.py", "pipeline/stages/stage_10_extract_pack_claims.py",
        "pipeline/vision_ops/validate_emerging_benefits_v1.py",
        "pipeline/vision_ops/test_run_06b_runner.py", "pipeline/vision_ops/prepare_run_06b_runner_readiness.py"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ".gitignore").write_text("*\n", encoding="utf-8")
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["outputs_sha256"][SOURCE.name]
    assert sha(SOURCE.read_bytes()) == expected
    rows = list(csv.DictReader(io.StringIO(SOURCE.read_text(encoding="utf-8-sig"))))
    assert len(rows) == 11902
    # A proposed operational subset of the already accepted sample, not a
    # redraw/population change. Four per approved group, deterministic slot order.
    groups = defaultdict(list)
    for row in rows:
        groups[row["sampling_group_id"]].append(row)
    pilot = []
    for group in sorted(groups):
        pool = sorted(groups[group], key=lambda r: r["proposed_primary_slot_id"])
        picked = []
        for predicate in (lambda r: not r["product_name"],
                          lambda r: r["proposed_primary_origin"] == "matching_reserve_replacement",
                          lambda r: r["proposed_ocr_relationship"] != "new_OCR_owner"):
            match = next((r for r in pool if r not in picked and predicate(r)), None)
            if match:
                picked.append(match)
        while len(picked) < 4:
            prior = {(r["country_cell"], r["accounting_component"]) for r in picked}
            match = next((r for r in pool if r not in picked and (r["country_cell"], r["accounting_component"]) not in prior), None)
            picked.append(match or next(r for r in pool if r not in picked))
        pilot.extend(picked)
    assert len(pilot) == 96 and len(groups) == 24
    with (OUT / "proposed_pilot_96.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(pilot)
    env = dotenv_values(ROOT / ".env")
    config = json.loads((PACKAGE / "core_configuration_proposal_frozen.json").read_text())
    config.update(configuration_version="run06b_integrated_runner_v1", status="PROPOSED_NOT_AUTHORIZED",
        emerging_contract_sha256=emerging.frozen_contract()[1],
        emerging_benefits_enabled=True, v6_max_output_tokens=2000, max_request_utf8_bytes=32768,
        ocr={"engine": "Azure AI Vision Read", "api_version": "v3.2", "transport": "frozen_binary_bytes",
             "transforms": "none", "fallbacks": 0},
        provider={"vision_endpoint": env.get("AZURE_VISION_ENDPOINT", "").rstrip("/"),
            "openai_endpoint": env.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
            "deployment": env.get("AZURE_OPENAI_DEPLOYMENT", ""), "deployment_verified": False,
            "model_version": None, "response_model": None, "verification_source_path": None,
            "verification_source_sha256": None},
        tariffs={"account_tariffs_verified": False, "currency": "CHF", "ocr_nanochf": 1500000,
            "input_nanochf_per_token": 100, "output_nanochf_per_token": 400,
            "source_path": None, "source_sha256": None,
            "assumption_only": "OCR historical CHF1.50/1000; LLM USD0.10/0.40 per million with CHF/USD=1 planning factor; no free/cached tier credit."})
    rates = {"ocr": 1500000}
    for kind, tokens in (("core", 800), ("dairy_review", 60), ("dairy_reextract", 800), ("emerging_benefits", 2000)):
        rates[kind] = (config["max_request_utf8_bytes"] + 1024) * 100 + tokens * 400
    source_hashes = {p: sha((ROOT / p).read_bytes()) for p in CODE}
    policy = {"execution_authorized": False, "tariffs_validated": False,
        "approval_sha256": None, "approval_record_path": None, "manifest_sha256": expected, "configuration_sha256": stable_hash(config),
        "attempt_cap": 60000, "ceiling_nanochf": 2000000000,
        "worst_case_nanochf_per_call": rates, "max_calls_per_job": {k: 1 for k in KINDS},
        "staging_path": str(ROOT / "presentations/segmentation/run_06b_execution_staging_v1/staging.sqlite"),
        "history_receipt_path": str(OUT / "prepayment_history_receipt.json"),
        "authorization_valid_until_utc": None, "runtime_files_sha256": source_hashes,
        "authorized_primary_slots": sorted(r["proposed_primary_slot_id"] for r in pilot)}
    def workload(subset):
        n, b, d = len(subset), sum(r["category"] == "beverages" for r in subset), sum(r["category"] in ("dairy", "dairies") for r in subset)
        return {"primary_records": n, "ocr_upper": n, "ocr_with_verified_sharing": len({r["image_sha256"] for r in subset}),
            "core_initial": n, "v6_upper": b, "dairy_review_upper": d, "dairy_reextract_upper": d,
            "total_paid_post_upper": 2*n+b+2*d,
            "estimated_chf_assumption": round(n*.0015 + n*(2500*100+350*400)/1e9 +
                b*(4000*100+700*400)/1e9 + d*.2*(2000*100+60*400+2500*100+350*400)/1e9, 4),
            "all_dairy_conditional_chf_assumption": round(n*.0015+n*(5000*100+800*400)/1e9+
                b*(10000*100+2000*400)/1e9+d*((5000*100+60*400)+(5000*100+800*400))/1e9,4),
            "maximum_reservation_chf_assumption": round((n*rates["ocr"]+n*rates["core"]+b*rates["emerging_benefits"]+
                d*(rates["dairy_review"]+rates["dairy_reextract"]))/1e9, 6)}
    costs = {"planning_only_not_tariff_verification": True, "full": workload(rows), "pilot": workload(pilot),
        "proposed_pilot_ceiling_chf": 2, "proposed_full_ceiling_chf": 100,
        "timeouts_and_failures": "Full reservation retained; no automatic paid retries; uncertain calls cannot be redispatched. Fixed manifest implies no extra retry workload.",
        "v6_prompt": "mandatory emerging_benefits_v1 for all successful beverage OCR including core failure/no claims",
        "public_sources": ["https://azure.microsoft.com/en-us/pricing/details/computer-vision/",
            "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/",
            "https://developers.openai.com/api/docs/models/gpt-4.1-nano"],
        "actual_account_tariff_status": "UNVERIFIED: Azure public prices are region/offer-specific; public OCR page displays placeholders; no account management query or provider request performed."}
    receipt = {"checked_at_utc": None, "manifest_sha256": expected, "configuration_sha256": stable_hash(config),
        "primary_identities_sha256": stable_hash(sorted({(r["barcode"], r["region"]) for r in rows})),
        "all_saved_sources_reconciled": False, "secondary_identities_included": False,
        "unresolved_matches": None, "new_ineligible_events": None, "reviewed_by": None, "source_inventory": [],
        "note": "TEMPLATE ONLY. Actual bounded delta immediately before first paid dispatch, repeat at startup/resume; include all primary and linked GTINs, image revisions, valid no-claim and failed/uncertain events. No unrestricted history refresh."}
    for name, obj in (("runtime_configuration.proposed.json", config), ("pilot_policy.NOT_AUTHORIZED.json", policy),
                      ("cost_scenarios.json", costs), ("prepayment_history_receipt.TEMPLATE.json", receipt)):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    full_policy = dict(policy, ceiling_nanochf=100000000000,
                       authorized_primary_slots=sorted(r["proposed_primary_slot_id"] for r in rows))
    (OUT / "full_policy.NOT_AUTHORIZED.json").write_text(json.dumps(full_policy, indent=2)+"\n", encoding="utf-8")
    validations = {"primary_count": len(rows), "pilot_count": len(pilot),
        "pilot_groups": dict(Counter(r["sampling_group_id"] for r in pilot)),
        "pilot_region_category": dict(Counter(r["region"]+"|"+r["category"] for r in pilot)),
        "all_pilot_rows_exact_frozen_primary_records": all(r in rows for r in pilot),
        "frozen_primary_manifest_unchanged": sha(SOURCE.read_bytes()) == expected,
        "provider_calls": 0, "image_reads": 0, "database_reads": 0,
        "runtime_sources_sha256": source_hashes,
        "frozen_sources_sha256": {str(p.relative_to(ROOT)).replace('\\','/'): sha(p.read_bytes()) for p in
            [SOURCE, PACKAGE/"manifest.json", PACKAGE/"core_configuration_proposal_frozen.json",
             ROOT/"presentations/segmentation/run_06b_v2/history_observations_refreshed.csv"]}}
    (OUT / "preparation_validation.json").write_text(json.dumps(validations, indent=2)+"\n", encoding="utf-8")
    tests_path = OUT / "offline_test_results.json"
    tests = json.loads(tests_path.read_text()) if tests_path.exists() else {"tests": "not yet recorded", "successful": False}
    report = f"""# RUN 06B — Execution runner readiness

Status: **offline integration implemented; paid execution BLOCKED pending verification and Julia's approval**.
This report supersedes older onboarding wording that left v6 opt-in. Julia's current execution brief makes v6 mandatory for beverages. Sampling, eligibility and allocation were not reopened.

## Changes and validation

Created `pipeline/vision_ops/run_06b_runner.py`, `test_run_06b_runner.py` and `prepare_run_06b_runner_readiness.py`.
Extended `run_06b_execution_guard.py` with append-only compatible approval extensions and stale-worker rejection.
Extended `emerging_benefits_stage.py` with saved-OCR preparation/validation entry points independent of core success; retained its older opt-in interface for compatibility.
The actual regional message builders, validators, UK rescue rules and dairy context criteria are reused through isolated legacy-contract instances. Legacy paid transport/retries/enrichment are bypassed. Stage 10, Stage 11, all three core prompts, both dairy prompts, v6 prompt/schema/validator, taxonomy and historical observations are unchanged.

Recorded focused offline results: **{tests['tests']} tests; success={tests['successful']}**. See `offline_test_results.json` for every case and `preparation_validation.json` for source locks.
Coverage: FR/UK+IE/US+CA profiles; beverage base→v6; non-beverage base only; valid no-claim; core failure with independent v6; OCR failure; v6 failure; dairy review/re-extraction; shared bytes/different regional cores; blank identities/leading zeros; short OCR; abrupt crash and saved-result recovery; concurrent threads and two separate processes; spending stop; append-only history; immutable source gates; bounded indexed history lookup and valid no-claim recognition; actual execution-policy/receipt branches with mock transport; exact binary OCR transport using synthetic bytes only.
No provider dispatch, real-image access, URL preflight or production database read occurred. An initial test setup failed because the sandbox temp location was not writable; fixtures now use disposable workspace directories. Final result is recorded above.

## Processing and durable staging

For each authorized exact frozen primary row: Azure OCR → save full OCR → regional core; all beverages additionally get independent `emerging_benefits_v1` from that same full OCR, including core no-claim/failure. Non-beverages never get v6. Eligible dairy legal-panel outcomes get saved-OCR review and, if rescued, re-extraction. Each operation has its own evidence/configuration key and reservation. No extra OCR for v6 or dairy review.

At runtime OCR submits the exact hash-checked frozen cached bytes as `application/octet-stream`; no mutable URL transport, paid fallback or silent higher-resolution substitution. Original/requested/resolved URL provenance and complete original rows remain in dispatch events. The runner makes no claim about current URL bytes. Identical OCR byte/configuration keys share successful OCR; regional LLM keys remain distinct. Existing technical checks suffice for candidacy; no universal visual certification.

Canonical shared ledger: `presentations/segmentation/run_06b_execution_staging_v1/staging.sqlite`.
SQLite FULL durability, atomic reservations, append-only triggers and separate events/results/observations/receipts preserve full OCR, raw responses, outputs, no-claim successes, unusable results, failures, operation URLs/IDs and usage. Resume never repeats a successful stage. Saved provider results can finish local validation; recorded OCR operation recovery uses GET only. Timed-out/uncertain LLM calls remain reserved and held for receipt reconciliation; no blind paid retry. A lost response that has no recoverable provider receipt remains blocked.

All workers must use the canonical ledger. Pilot→full approval extensions preserve prior reservations and completed stages; changed evidence/configuration cannot be smuggled through an extension. Old workers stop when superseded. No destructive production merge is wired.

## Provider configuration and outstanding blockers

Local `.env` specifies deployment `{config['provider']['deployment']}`; endpoint strings are preserved only in the local configuration proposal, with no keys copied. Credentials are present locally, but **actual deployment version, response model identifier, Azure region/offer/tier and CHF tariffs remain unverified**. Do not infer them from the deployment alias. Azure Read v3.2 and the existing Azure OpenAI `/openai/v1/chat/completions` transport are implemented. No provider or management request was issued to verify availability.

Before payment: obtain read-only deployment metadata and account tariff evidence (including currency conversion/tax basis); bind their saved hashes; set exact response-model identity; recompute configuration SHA, tariff bounds and policies; record Julia's explicit approval and its hash. Config/source/history/endpoint/model mismatches fail closed.
The v6 prompt/schema/validator/definition hashes are bound to the new configuration identity. Core 800, review 60 and v6 2,000 output-token caps are explicit. Requests above 32,768 UTF-8 bytes are held before dispatch, never truncated to fit; v6 retains full OCR. A larger approved request allowance requires re-costing and a new configuration, not an unaccounted call.

## Workload and costs

| Operation | Full maximum | Pilot maximum |
|---|---:|---:|
| Primary regional records / initial core calls | 11,902 | 96 |
| OCR submissions without sharing | 11,902 | 96 |
| OCR with verified byte/configuration sharing | 11,821 | {costs['pilot']['ocr_with_verified_sharing']} |
| Mandatory beverage v6 after successful OCR | 3,535 | 20 |
| Conditional dairy review | 2,100 | 20 |
| Conditional dairy re-extraction | 2,100 | 20 |
| Total potentially billable submissions, no sharing | 31,539 | 252 |

| CHF planning scenario | Full | Pilot |
|---|---:|---:|
| Estimated (20% dairy review+rescue assumption) | {costs['full']['estimated_chf_assumption']:.4f} | {costs['pilot']['estimated_chf_assumption']:.4f} |
| Higher tokens, every dairy reviewed and re-extracted | {costs['full']['all_dairy_conditional_chf_assumption']:.4f} | {costs['pilot']['all_dairy_conditional_chf_assumption']:.4f} |
| Every call reserves its maximum input/output allowance | {costs['full']['maximum_reservation_chf_assumption']:.6f} | {costs['pilot']['maximum_reservation_chf_assumption']:.6f} |
| **Proposed hard ceiling, NOT authorized** | **100** | **2** |

Assumptions: OCR historical CHF 1.50/1,000; input/output token planning rates 100/400 nanoCHF per token (USD 0.10/0.40 per million at planning CHF/USD=1). No free-tier/cached-token discounts. Exact token scenarios and fixed request bounds are in `cost_scenarios.json`. Estimated core uses 2,500 input/350 output, v6 4,000/700; higher-use core 5,000/800 and v6 10,000/2,000. Dairy review 2,000/60 estimated, 5,000/60 higher-use; re-extraction follows core. These are scenario assumptions, not observed pilot usage or verified Azure prices.

The [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-4.1-nano) supplies the public USD token reference; it is not an Azure account tariff. The [Azure model catalog](https://ai.azure.com/catalog/models/gpt-4.1-nano?publisher=openai) lists version 2025-04-14, without proving this account's deployment. [Azure Vision pricing](https://azure.microsoft.com/en-us/pricing/details/computer-vision/) is offer/region-specific and rendered numeric Read prices as placeholders; the [Azure OpenAI pricing page](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/) could not be fetched. Actual tariff verification remains a blocker.

Each attempted/failed/timeout call keeps its full reservation, so failures do not free budget for more calls. Paid automatic retries=0; any extra retry requires separate reconciliation/approval. All categories, v6 and conditional calls use one hard ceiling. Per-call rates must cover request-byte token bounds plus envelope allowance and output caps, verified before dispatch. The previous CHF 30 plan is not authorization. A full approval ceiling includes the pilot already spent/reserved, not CHF 100 plus pilot.

## Proposed pilot and final bounded history check

`proposed_pilot_96.csv` contains four unchanged primary records from each of the 24 approved groups, spanning all 11 regional/category strata. Deterministic frozen slot order prioritizes available blank-name, reserve-replacement and conditional-OCR-sharing cases, then country/component diversity within each group. This operational subset changes no final sampling assignments. Its 20 beverages require up to 20 v6 calls; 20 dairy records allow up to 40 additional conditional calls. Pilot completions count toward the 11,902 full primary records.

`indexed_history_delta` validates EXPLAIN plans and queries only exact GTIN keys (all historical regions conservatively). `classify_bounded_history_delta` also checks linked GTINs and frozen image hashes/OFF revision families in supplied bounded new exports. Same-image-family/different-GTIN results remain HOLDs; valid no-claim successes block duplicate first attempts. The offline suite probes a valid no-claim event from the frozen saved ledger without opening a production database. Source snapshot hash is recorded.

Immediately before the first authorized paid call, discover/reconcile saved CSV/checkpoint/staging increments since `2026-10-23T20:56:41.172018+00:00`, including all linked identities and possibly equivalent image revisions. Use existing barcode indexes for any required database lookups and reject SCAN plans; never rerun unrestricted history refresh. Unknown source coverage, new successes/failures/uncertain events, or possible equivalence stop startup for versioned reconciliation. This source-inventory completeness review cannot be inferred from a successful indexed lookup.
For resume, distinguish this run's own exact stage keys, verified from the canonical ledger: they remain under its success/pending reservation locks rather than becoming new external-history exclusions. Never trust an external event's unverified claim to belong to that set. Existing own-stage successes are reused and uncertain own calls remain blocked from resubmission, while independent stages may continue within approval.
Produce the reviewed receipt at the configured path using the provided **incomplete template**, with exact manifest/configuration/identity hashes, saved-source hashes, no unresolved matches and zero new ineligible events. Startup/resume requires a receipt no older than 15 minutes and an unexpired paid authorization. **The actual last-minute check has not been performed.** No historical result was updated.

## Startup / resume commands

Run from the repository root. Safe now, no dispatch:

```powershell
.venv/Scripts/python.exe -B -m pipeline.vision_ops.run_06b_runner
.venv/Scripts/python.exe -B -m unittest pipeline.vision_ops.test_run_06b_runner -v
```

Only AFTER provider/tariff/history verification and explicit Julia approval, create versioned `pilot_policy.AUTHORIZED.json` and verified configuration; the NOT_AUTHORIZED templates intentionally cannot run:

```powershell
.venv/Scripts/python.exe -B -m pipeline.vision_ops.run_06b_runner --execute --configuration presentations/segmentation/run_06b_runner_validation_v1/runtime_configuration.VERIFIED.json --policy presentations/segmentation/run_06b_runner_validation_v1/pilot_policy.AUTHORIZED.json
```

Ordinary resume: the same command and canonical ledger, after refreshing the bounded history receipt. `--recover-ocr` additionally polls only recorded incomplete OCR operations; never resubmits them. Pending LLM receipts require reconciliation, not a new ledger or a repeated paid call. After pilot review and separately approved full-run extension, use the full authorized policy plus `--extend-approved-policy`; historical staging and previous spend remain intact. Do not delete/copy/reset the ledger to bypass locks. A configuration change needs a separately reviewed reconciliation, not this scope extension.

**STOP: no paid pilot/full run was executed, no production merge occurred, and no payment authorization is declared.**
"""
    (OUT / "RUN 06B - Execution runner readiness.md").write_text(report, encoding="utf-8")
    package_files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in {"checksums.sha256", "manifest.json"})
    package_manifest = {"status": "OFFLINE_VALIDATED_NOT_AUTHORIZED", "provider_calls": 0,
        "source_sha256": source_hashes, "frozen_sources_sha256": validations["frozen_sources_sha256"],
        "outputs_sha256": {p.name: sha(p.read_bytes()) for p in package_files}}
    (OUT / "manifest.json").write_text(json.dumps(package_manifest, indent=2)+"\n", encoding="utf-8")
    package_files.append(OUT/"manifest.json")
    (OUT/"checksums.sha256").write_text("\n".join(sha(p.read_bytes())+"  "+p.name for p in package_files)+"\n", encoding="utf-8")
    print(json.dumps(costs, indent=2))


if __name__ == "__main__":
    main()
