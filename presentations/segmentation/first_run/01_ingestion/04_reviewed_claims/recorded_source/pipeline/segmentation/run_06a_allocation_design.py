"""RUN 06A: aggregate allocation design only; no product selection or services.

Use the approved CHECK 05 files unchanged. Run with bundled Python/pandas.
Before approval, --verify-only recomputes draft deliverables in memory.
After CHECK 06A closure, --verify-only validates the approved cost-reconciled
artifacts and original snapshots without rerunning allocation or selecting items.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "presentations/segmentation/run_05_v1"
OUT = ROOT / "presentations/segmentation/run_06a_v1"
REPORT = ROOT / "presentations/segmentation/RUN 06A_no US.md"
SEED = 20261022

# Proposed primary-owned distinct-work slots, in the approved CHECK 05 order.
# Deliberate allocation decisions, not a product-count-proportional estimate.
QUOTAS = [900, 400, 550, 450, 600, 600, 1300,
          600, 300, 390, 310, 360, 480, 60, 1100,
          550, 500, 250, 200, 450, 450, 980, 120, 100]
RATIONALE = {
    "FR_snacks_C1": "Largest broad group; random diversity with an upper-fibre supplement.",
    "FR_snacks_C2": "Oversample the smaller coarse group; retain mixed identities and warnings.",
    "FR_cereals_C1": "Substantial cereal coverage plus upper observed fibre, without requiring fibre for baseline.",
    "FR_cereals_C2": "Protect the smaller cereal group from count-proportional under-allocation.",
    "FR_dairies_C1": "Equal effort across the two coarse dairy groups; no fibre targeting.",
    "FR_dairies_C2": "Equal effort across dairy groups; warning flags remain eligible.",
    "FR_beverages_ALL": "Regional random baseline with a small explicit preparation/specialist supplement.",
    "UK_IE_snacks_C1": "Broad snack diversity and upper-fibre supplement; country cells protect Ireland.",
    "UK_IE_snacks_C2": "Oversample smaller coarse snack group; upper-fibre supplement remains bounded.",
    "UK_IE_cereals_C1": "Useful cereal coverage despite a smaller remaining population; retain reserves.",
    "UK_IE_cereals_C2": "Meaningful comparison of both cereal groups; avoid exhausting the small pool.",
    "UK_IE_dairies_C1": "Preserve the first approved dairy group and its warning composition.",
    "UK_IE_dairies_C2": "Largest remaining UK/IE dairy group; complement existing successes.",
    "UK_IE_dairies_C3": "Small mixed preparation/dessert group; 60 slots, not a census or validated product type.",
    "UK_IE_beverages_ALL": "Regional random baseline, with explicit preparation/specialist supplement.",
    "US_CA_snacks_C1": "Broad snack comparison with upper-fibre supplement and Canadian representation.",
    "US_CA_snacks_C2": "Broad snack comparison; warnings and legitimate unusual products retained.",
    "US_CA_snacks_C3": "Protect smaller protein-rich mixed group; do not infer a market territory.",
    "US_CA_cereals_C1": "Small protein/fat-rich group receives useful coverage despite high warning rates.",
    "US_CA_cereals_C2": "Equal effort in the two large cereal groups; upper-fibre supplement.",
    "US_CA_cereals_C3": "Equal effort in the two large cereal groups; upper-fibre supplement.",
    "US_CA_beverages_C1": "Largest M1-complete beverage group; strong limit on inference to missing-M1 beverages.",
    "US_CA_beverages_C2": "Protect provisional specialist/preparation group; high warnings are not an exclusion.",
    "US_CA_beverages_C3": "Protect provisional mixed preparation group; no validated product-form interpretation.",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def table(rows, headings):
    def fmt(v):
        return f"{v:,}" if isinstance(v, int) else str(v)
    return "\n".join([
        "| " + " | ".join(headings) + " |",
        "|" + "---|" * len(headings),
        *["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows],
    ])


def apportion(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Hamilton integer allocation, ties resolved by canonical cell identifier."""
    assert total >= 0 and total <= sum(weights.values())
    denominator = sum(weights.values())
    if not denominator:
        assert total == 0
        return {k: 0 for k in weights}
    exact = {k: total * v / denominator for k, v in weights.items()}
    result = {k: math.floor(v) for k, v in exact.items()}
    order = sorted(weights, key=lambda k: (-(exact[k] - result[k]), k))
    for k in order[:total - sum(result.values())]:
        result[k] += 1
    assert sum(result.values()) == total
    assert all(result[k] <= weights[k] for k in weights)
    return result


def planning_rates(region, group):
    if group in {"US_CA_beverages_C2", "US_CA_beverages_C3"}:
        return .85, .70
    return (.90, .80) if region == "FR" else (.94, .85)


def verify_inputs():
    approval = json.loads((BASE / "check_05_approval.json").read_text(encoding="utf-8"))
    manifest = json.loads((BASE / "run_05_manifest.json").read_text(encoding="utf-8"))
    hashes = {}

    def check(path, expected=None):
        digest = sha(path)
        if expected is not None:
            assert digest == expected, f"Input checksum mismatch: {path}"
        hashes[rel(path)] = digest

    assert approval["status"] == "Approved and closed"
    check(BASE / "check_05_approval.json")
    check(BASE / "run_05_manifest.json", approval["baseline_manifest"]["sha256"])
    assert approval["baseline_outputs"] == manifest["outputs"]
    for name, info in manifest["outputs"].items():
        check(BASE / name, info["sha256"])
    for key in ("pre_approval_report", "approved_report"):
        check(ROOT / approval[key]["path"], approval[key]["sha256"])
    assert approval["ledger"]["sha256"] == manifest["outputs"]["candidate_ledger.csv"]["sha256"]
    check(BASE / "check_04_approval.json", manifest["approval_sha256"])
    a4 = json.loads((BASE / "check_04_approval.json").read_text())
    for key in ("decision_table", "memberships"):
        check(ROOT / a4[key], a4[key + "_sha256"])
    check(BASE / "manual_review_policy.json", manifest["protected_source_hashes"][rel(BASE / "manual_review_policy.json")])
    for name in ("docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md",
                 "pipeline/stages/stage_10_extract_pack_claims.py",
                 "pipeline/vision_ops/op_02_preflight_images.py", "SEGMENTATION.md"):
        check(ROOT / name)
    assert a4["groups"] == 24 and a4["designs"] == 11
    return hashes, approval


def read_candidates():
    # No copied ledger, product shortlist, barcode export or URL request.
    columns = ["barcode", "region", "category", "countries", "sampling_group_id",
               "m1_eligible", "available_first_attempt", "available_retry",
               "existing_successful_ocr_llm", "nutrition_warning_present",
               "fiber_100g", "beverage_preparation_identified", "beverage_specialist_signal",
               "manual_review_hold", "image_available"]
    chunks = []
    total = 0
    for chunk in pd.read_csv(BASE / "candidate_ledger.csv", usecols=columns,
                             dtype={"barcode": str}, low_memory=False, chunksize=50000):
        total += len(chunk)
        chunks.append(chunk.loc[chunk.available_first_attempt.eq(1) & chunk.m1_eligible.eq(1)])
    assert total == 476626
    candidates = pd.concat(chunks, ignore_index=True)
    assert len(candidates) == 194895
    assert not candidates.duplicated(["barcode", "region", "category"]).any()
    assert candidates.image_available.eq(1).all()
    assert candidates.manual_review_hold.eq(0).all()
    assert candidates.existing_successful_ocr_llm.eq(0).all()
    return candidates


def plan_cells(s, quota, threshold, category):
    counts = {str(k): int(v) for k, v in s.countries.value_counts().items()}
    region = s.region.iloc[0]
    if region == "FR":
        cells = {"FR": quota}
    else:
        minor = "IE" if region == "UK+IE" else "CA"
        minority = {k: v for k, v in counts.items() if minor in k.split("|")}
        majority = {k: v for k, v in counts.items() if minor not in k.split("|")}
        n_minor = sum(minority.values())
        # Proposed minimum minority effort; rare country cells can be a census.
        n_quota = min(math.ceil(.10 * quota), math.ceil(.50 * n_minor), n_minor)
        cells = {**apportion(n_quota, minority), **apportion(quota - n_quota, majority)}
    result = []
    for country_cell in sorted(counts):
        z = s.loc[s.countries.eq(country_cell)]
        q = cells.get(country_cell, 0)
        high = z.fiber_100g.notna() & z.fiber_100g.gt(0) & z.fiber_100g.ge(threshold)
        specialist = z.beverage_preparation_identified.eq(1) | z.beverage_specialist_signal.eq(1)
        component = "upper_observed_fibre" if category in {"snacks", "cereals"} else (
            "explicit_preparation_or_specialist" if category == "beverages" else "none")
        target_pool = int(high.sum()) if component == "upper_observed_fibre" else (
            int(specialist.sum()) if component == "explicit_preparation_or_specialist" else 0)
        target_fraction = .20 if component == "upper_observed_fibre" else .15
        target = min(math.floor(target_fraction * q), math.floor(.50 * target_pool))
        result.append({
            "region": region, "category": category, "sampling_group_id": s.sampling_group_id.iloc[0],
            "country_cell": country_cell, "available_first_attempt": len(z),
            "proposed_primary_attempts": q, "random_baseline": q - target,
            "target_component": component, "targeted_attempts": target,
            "target_pool_before_baseline": target_pool,
            "fibre_group_p75_non_null": threshold,
            "initial_random_inclusion_probability": round((q - target) / len(z), 10),
            "reserve_capacity_in_cell": len(z) - q,
            "country_cell_census": bool(q > 0 and q == len(z)),
            "status": "Proposed; not approved; no products selected",
        })
    assert sum(x["proposed_primary_attempts"] for x in result) == quota
    assert all(x["proposed_primary_attempts"] <= x["available_first_attempt"] for x in result)
    return result


def optional_proposals():
    missing = pd.read_csv(BASE / "check_05_missing_m1_population.csv").set_index(["region", "category"])
    coverage = pd.read_csv(BASE / "check_05_region_category.csv").set_index(["region", "category"])
    specs = [
        ("missing_M1_exploratory", "FR", "beverages", 100, .85),
        ("missing_M1_exploratory", "UK+IE", "beverages", 100, .90),
        ("missing_M1_exploratory", "US+CA", "beverages", 300, .90),
        ("retry", "FR", "snacks", 20, .70),
        ("retry", "FR", "dairies", 20, .70),
        ("retry", "FR", "beverages", 10, .70),
        ("retry", "UK+IE", "snacks", 10, .70),
        ("retry", "UK+IE", "dairies", 10, .70),
        ("retry", "UK+IE", "beverages", 10, .70),
        ("retry", "US+CA", "snacks", 10, .70),
        ("retry", "US+CA", "beverages", 10, .70),
    ]
    rows = []
    for component, region, category, quota, rate in specs:
        is_missing = component == "missing_M1_exploratory"
        row = (missing if is_missing else coverage).loc[(region, category)]
        available = int(row["available_first_attempt" if is_missing else "available_retry"])
        assert quota <= available
        rows.append({
            "optional_component": component, "region": region, "category": category,
            "sampling_group_id": "UNASSIGNED_MISSING_M1" if is_missing else "UNALLOCATED_RETRY_POOL",
            "remaining_available": available, "recommended_attempts": 0,
            "separately_proposed_optional_attempts": quota,
            "assumed_success_rate": rate, "expected_successes_if_approved": quota * rate,
            "rationale": ("Random exploration of missing-M1 beverage coverage bias; no nutritional cluster." if is_missing
                          else "Only after explicit retry approval and candidate-specific recoverability evidence; mix of M1 and missing-M1 remains undecided."),
            "authorization": "Separate approval required; excluded from recommended 12000",
        })
    return rows


def historical_evidence():
    events = pd.read_csv(BASE / "history_observations.csv", dtype={"barcode": str}, low_memory=False)
    rows = []
    for region, n, successes, azure_spend in [("FR", 6170, 5719, 8), ("UK+IE", 5956, 5748, None), ("US+CA", 5894, 5660, None)]:
        rows.append({"evidence_type": "documented_original_release", "source": "docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md sections 6.5 and 7",
                     "region_or_artifact": region, "records": n, "valid_success_records": successes,
                     "valid_success_fraction": round(successes / n, 10), "approx_azure_spend_chf": azure_spend,
                     "limitation": "Historical regional sample; prompt and selection differ; spend is approximate, not current all-in billing."})
    raw = events.loc[events.source.str.endswith(".csv") & ~events.source.str.contains("normalised|checkpoint", regex=True)]
    for source, s in raw.groupby("source", sort=True):
        valid = int(s.valid_success.astype(str).str.lower().eq("true").sum())
        rows.append({"evidence_type": "saved_raw_result_artifact_via_approved_RUN05_history", "source": source,
                     "region_or_artifact": Path(source).stem, "records": len(s), "valid_success_records": valid,
                     "valid_success_fraction": round(valid / len(s), 10), "approx_azure_spend_chf": None,
                     "limitation": "Per-artifact outcomes incl no-claim success; overlapping releases cannot be summed as independent attempts or used as current-population success rates."})
    return rows


def quality_spec():
    specs = [
        ("H01", "hard", "Approval and input hashes", "Exact approved CHECK 05 ledger, manifest, approval and CHECK 04 memberships match SHA256; approved RUN 06A config recorded.", "Stop on any mismatch; never regenerate RUN 05."),
        ("H02", "hard", "Exact eligibility", "Every primary and reserve key exists once in approved regional ledger and saved group; M1 complete and available_first_attempt=1 for core; no US/CA dairy.", "Zero unauthorized or unmatched keys."),
        ("H03", "hard", "Current history and holds", "Refresh before executable-manifest freeze and again immediately before execution; no success, unresolved history, failed/unusable history or active hold enters a first-attempt slot.", "Replace before payment; no silent retries or reruns."),
        ("H04", "hard", "Country assignments", "Exact original country set preserved; no duplicate country expansion; primary ownership and secondary links recorded separately.", "Zero rewritten country sets; reconcile exclusive-cell quotas."),
        ("H05", "hard", "Image preflight", "Only proposed shortlist and bounded reserves checked; actual image decodes, is reachable and has front/usable or review-approved status; unresolved status stays pending.", "Zero unresolved/unusable images in executable primary manifest; no full-universe crawl."),
        ("H06", "hard", "Paid evidence uniqueness", "One primary owner per exact evidence/configuration work key; unique immutable bytes hash plus OCR and extraction configuration; derivative equivalents resolved; metadata used by prompt included.", "Zero duplicate independent paid slots; retain regional secondary links."),
        ("H07", "hard", "Quota reconciliation", "Primary owned units reconcile to approved group/country quotas and mutually exclusive random/fibre/specialist components including recorded conversions; reserves carry zero planned payment.", "No silent group/country transfers; shortfall requires review."),
        ("H08", "hard", "Attempt and cost caps", "Core <= approved attempt cap; optional pools remain zero unless explicitly approved; all billable retry/review calls counted separately within validated cost guard.", "No auto-top-up after paid failures; billing guard and exact manifest approved before Julia executes."),
        ("H09", "hard", "Deterministic selection", "Seed 20261022, fixed canonical SHA256 order, canonical country/group cells and source/config hashes; identical frozen inputs yield byte-identical selection.", "Exact keys, order, components, primary ownership and output hashes reproduce."),
        ("H10", "hard", "Evidence-version checkpoint and merge", "Resume and merge keyed by evidence/configuration version; old observations preserved; successful no-claim counts as processed; round-trip/resume/changed-image tests pass.", "Execution blocker until validated; existing barcode-only resume is insufficient."),
        ("H11", "hard", "Selection provenance", "Every drawn primary/reserve retains frame N, non-NULL fibre N, target threshold, component/reasons, stage quota, rank, nominal and conditional probabilities where calculable.", "No unsupported final inclusion weights; zero missing required provenance."),
        ("H12", "hard", "Reserves and replacement", "At most ceil(25% group quota) reserves, assigned to same cells/components subject to availability; source and destination reasons logged for each replacement.", "Reserve shortage reported; expansion or country/group reallocation needs approval."),
        ("S01", "soft", "Nutrition distribution", "Compare baseline with eligible cell/frame and full shortlist separately: per-feature median/IQR/P5/P95, exact zero %, missingness; flag |median difference|/frame IQR >0.5 or empirical CDF distance >0.10.", "Review differences; zero IQR reported separately; no clipping/exclusion."),
        ("S02", "soft", "Fibre enrichment", "Report observed-fibre coverage/missingness, threshold and observed upper-fibre share; compare random baseline separately from targeted total.", "Flag missingness differences >5 percentage points and targeted achievement <80% of proposal; explain conversions."),
        ("S03", "soft", "Nutrition warnings", "Report any-warning and type shares by group/country/component; flag baseline vs frame absolute difference >5 percentage points.", "Review sampling deviations; warnings alone never exclude."),
        ("S04", "soft", "Country representation", "Show exclusive cells and inclusive country-assignment shares, prior coverage and new work; compare actual against approved cell plan.", "Document deliberate IE/CA oversampling; a dual-country product is one regional product."),
        ("S05", "soft", "Beverage signals", "Compare known preparations, specialist signal, ready-to-drink signal, alcohol signal, unknown/conflicting form and their overlaps by component.", "Flag baseline share shifts >5 percentage points; no validated form labels or market shares."),
        ("S06", "soft", "Prior and projected coverage", "Report prior success incl no-claims plus projected new successes / unchanged group population; secondary credits shown without double-paid units.", "Separate actual success, expected success and proposed attempts; no claim prevalence inference."),
        ("S07", "soft", "Selection deviations", "List preflight losses, history removals, overlap replacements, scarce cells, target-to-random conversions and reserve shortfalls.", "Material shortfalls or changed design returned for approval; no silent denominator change."),
        ("S08", "soft", "Bias and inference", "Compare random baseline, deliberate targets and combined sample; preserve OFF-frame denominators and note missing-M1 coverage limits.", "No combined-sample or historical-plus-new unweighted market/prevalence estimates."),
    ]
    return [{"check_id": k, "severity": severity, "check": name, "acceptance_criterion": criterion,
             "required_action": action, "stage": "RUN 06B / final pre-execution refresh; NOT performed in RUN 06A"}
            for k, severity, name, criterion, action in specs]


RULES = """# RUN 06B selection rules proposed by RUN 06A

**CHECK 06A: Pending approval. Specification only. No product selection, preflight or paid work has occurred.**

## 1. Frozen frames, scope and units

Use the exact local RUN 05 candidate ledger, approved coverage tables, CHECK 04 saved memberships, CHECK 05 manifest and approval record, with the hashes in `run_06a_manifest.json`. Do not recreate eligibility, clusters or source nutrition. US/CA dairy stays excluded. Core eligibility is the ledger's `m1_eligible=1 AND available_first_attempt=1`, not a new criterion. Retain exact `(barcode, region, category)` and original pipe-delimited country set. All baseline counts use regional products, not expanded country assignments.

Refresh saved history before freezing the executable manifest and again just before paid work. Use the RUN 05 success rules including no-claim success. Append dated history/review overlays with source hashes; preserve RUN 05. A new success, failure/unusable attempt, unresolved history or manual hold makes a first-attempt shortlist entry unavailable. Review conflicts, preserve observations and replace before payment. Do not remove warnings, legitimate concentrates or extremes. Missing-M1 and retry pools remain zero in the recommended scenario. Optional variants require separate approval and a frozen, separately reviewed suballocation before selection. Retry recoverability must be evidenced at candidate level, not inferred from the size of the historical failure pool.

## 2. Quotas and country cells

The recommended design has 12,000 proposed primary-owned distinct-work slots. Start from `proposed_allocation.csv`, then the mutually exclusive country cells in `country_component_plan.csv`. Cells are FR; UK only / IE only / both; US only / CA only / both. A dual-tagged item consumes one cell slot and preserves both country tags. Prior country successes are inclusive assignment counts and must not be summed as regional unique successes.

For each merged-region group, reserve minority-assigned slots = min(ceil(10% of group quota), ceil(50% of available minority-assigned candidates), available minority candidates). Divide these between minority-only and dual cells using Hamilton apportionment proportional to availability, with canonical cell string as remainder tie-breaker. Allocate the remainder to majority-only. This deliberately favours IE/CA inspection; it is not population-proportional sampling. A one-record cell may be allocated its one record: explicitly report it, no guaranteed reserve. Never silently substitute a majority-only item if a minority cell fails. The approved-group quota itself is not exhausted. A country-cell shortfall goes back for review.

## 3. Mutually exclusive components and precedence

Within each country cell, draw the **random baseline first**, without replacement from the entire eligible cell, including products that qualify for later targets. It has priority for accounting. Preserve all qualifying reason flags even though the accounting component is unique.

For snacks/cereals only, targeted nutrition means observed fibre > 0 and >= the group's P75 of non-NULL fibre among RUN 05 M1 first-attempt candidates. P75 uses linear interpolation; all ties qualify. Freeze the numerical threshold recorded in the proposal. This is relative upper observed fibre, not a legal 'high fibre' claim, no new feature and no eligibility gate. Missing fibre remains eligible for random baseline. No targeted fibre quota for dairy or beverages.

For beverages only, target `beverage_preparation_identified=1 OR beverage_specialist_signal=1`, reusing RUN 05 saved metadata. Unknown forms remain eligible for baseline. Do not infer form from nutrients or the legacy combined preparation/alcohol view; no fresh keyword classifier or claim-based selection. A form signal identifies metadata, not a validated commercial type.

Before baseline selection, plan targeted count per cell = min(floor(20% of cell quota) for snacks/cereals, or floor(15%) for beverages; floor(50% of that cell's target pool)). Dairy targeted count = 0. Random quota = cell total minus targeted count. Draw the target quota from qualifying residual products after baseline draw. If too few remain, assign the shortage to additional random products in the same cell, using the declared random order. This conversion is permitted, recorded explicitly and included in quality review. It never increases a group or country quota. Baseline > fibre > specialist > optional missing-M1 > optional retry is accounting precedence if an optional variant is later approved; the current fibre/specialist categories do not overlap. Missing-M1 and retries have their own exclusive frames and may not consume a core slot.

## 4. Reproducibility, probabilities and denominators

Seed = **20261022**. Canonical UTF-8 SHA256 ranking string is JSON array `[seed, scenario_id, stage, sampling_group_id, country_cell, barcode, region, category]`, serialized with `ensure_ascii=False,separators=(',',':')`. Stages are `baseline`, `target`, `random_fill`, `reserve_baseline`, `reserve_target`; order by hexadecimal digest, then exact regional key. This defines the later draw; RUN 06A has calculated no ranks or selected barcodes.

Freeze the original frame N, country-cell N, observed-fibre N and threshold, target-pool N before baseline, target-residual N after baseline, stage draw count and random order. Initial random-baseline inclusion probability is n_baseline / N_cell. Conditional target-stage probability given the baseline realization is n_target / N_target_residual. These are distinct quantities: do not multiply them or call either the combined final inclusion probability. For products not qualifying for targets the original baseline probability is known before subsequent losses. Reserves, replacements, preflight conditioning and cross-group paid deduplication can change final probabilities. Record final probability/weight as unavailable unless the complete realized design has been derived; do not invent q/N weights for targeted or convenience replacements. Preserve the original random draw and diagnostics even when preflight rejects a product. Do not infer market prevalence from the combined sample or from pooled historical results.

## 5. Distinct paid evidence, shared assignments and ownership

Treat quotas as primary-owned work slots; a regional assignment is not automatically a distinct billable unit. Before paid execution define the evidence/configuration work key from the actual decoded image evidence/content hash and transformations, OCR engine/version/options, exact extraction model/deployment/version, prompt content hashes/language profile, taxonomy/schema and deterministic post-processing version, plus exact product/brand/context metadata supplied to extraction. Include these in validated checkpoint and merge identities. Normalized URL or barcode alone is insufficient. Do not conflate distinct regional pack evidence or language/configuration variants. Multiple sizes of the same image require derivative/evidence reconciliation during preflight. If bytes are equal but metadata/configuration differ, extraction units differ; OCR reuse, if possible, must be separately validated and counted. No such optimization is assumed in the budget.

After provisional draws and preflight, exact duplicates with identical evidence/configuration get one primary owner: ascending RUN 05 first-attempt group population, then canonical group ID, then exact regional key. Keep secondary assignment links for coverage. A product/work unit never funds two independent quotas. Replace a duplicate non-owner slot from its own deterministic same-cell/component reserve, rechecking uniqueness and history. Secondary results can increase linked regional coverage, but do not satisfy a second independent paid quota. Finish only when primary-owned work counts meet approved quotas, or report an explicit shortfall for approval. Known repeated barcodes do not prove work equivalence; exact paid-unit count is unknown until these checks. Different barcodes with identical evidence/configuration also require reconciliation. Current pipeline product metadata can prevent sharing even for an identical image.

## 6. Bounded reserves, image preflight and replacements

Propose reserves = ceil(25% of each group quota), separate from payment. Allocate this reserve budget to country cells by Hamilton apportionment proportional to their primary quotas, with canonical cell strings as tie-breakers. Cap each cell's reserve count by its remaining available population; report an unfilled reserve instead of transferring it to another country cell. Split a cell's reserves between its random/target components by Hamilton apportionment proportional to primary component counts. Cap by residual qualifying capacity after primary selection, allowing a depleted target reserve to convert to random within the same cell. Never duplicate a reserve or a primary. Report unfillable reserves; no silent country transfer. Keep target and random reserve orders separate. Preflight only selected primary shortlist and these reserves, deduplicating image fetches. No full-universe reachability scan. If bounded reserves do not suffice, stop and seek review before expanding the shortlist.

Reuse `op_02_preflight_images.py` reachability/content-type/size checks where suitable, with a later wrapper retaining exact keys, original and resolved URLs, bytes checksum, decode/dimension evidence and review status. Its `available` flag alone does not establish pack usability. Use deterministic technical checks and unresolved/manual review states for front/legibility concerns; no paid OCR/LLM for preflight. Keep unresolved cases out of the executable primary manifest. No minimum image dimension or subjective product-form filter is invented here; any proposed new usability threshold needs review before implementation. Preserve failures and reason codes. A preflight rejection is not a paid attempt. Replace only before payment within same group/country/component; record original key, reserve key and reason. A depleted target reserve may convert to random in the same cell with an explicit target shortfall. No automatic replacement for a paid failure and no retry authorization is implied.

## 7. Execution gate and budget semantics

A planned attempt is one authorized product/evidence/configuration processing job, not one HTTP/API request. Nominally one OCR plus one initial extraction; API retries and context review can generate more billable calls. Track jobs, OCR calls, extraction calls, review/re-extraction calls, provider retries, successful extractions (including valid no-claim), failures and spend separately. A failed paid job consumes an attempt slot. Reserves never create extra attempt budget. No success-target top-up or automatic paid retry.

Pipeline defaults used only for planning: OCR CHF 1.50 / 1,000 calls; LLM CHF 0.20 / 1,000 calls. Nominal job cost CHF 0.0017. Cost stress allowance = 2 OCR + 3 LLM calls per job, then 25% contingency: CHF 0.0045 per planned distinct job. Round aggregate stress envelope upward to the next CHF 10. These are local estimate parameters, not current tariffs or an invoice guarantee. Provider retries could exceed this allowance; the executable pipeline must have validated complete-call accounting and a stop-before-next-call guard against the approved cap. Default CostTracker increments logical OCR invocations and can omit underlying retries. Existing CHF 45 default alert is not the proposed scenario's approved cap.

Before Julia launches any paid command: approve exact manifest, attempt cap, cost ceiling and profiles, validate evidence-version checkpoint/merge, refresh history again and validate actual price/deployment assumptions. RUN 06A does not modify the processing pipeline. The present barcode-only resume is an execution blocker for this evidence-version design. New prompts/benefits, deployment changes and rerunning historical successes require their own review.

## 8. Quality review

Implement `selection_quality_checks.csv`. Hard gates must all pass before executable approval. Soft flags require explanation, never automatic nutrient/warning exclusions. Report baseline versus frame and complete shortlist versus frame separately, with deliberate targets and country oversampling visible. Preserve observed zeros versus NULL, fibre missingness, warnings, beverage form unknowns, original denominators, expected versus actual coverage and all deviations. RUN 06B approval of a usable shortlist remains separate from paid execution by Julia.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--replace-own-draft", action="store_true",
                        help="Replace only this run's hash-verified unapproved draft; never approved files.")
    args = parser.parse_args()
    assert not (args.verify_only and args.replace_own_draft)
    if (OUT / "check_06a_approval.json").exists():
        if not args.verify_only:
            raise SystemExit("CHECK 06A is closed. Approved outputs cannot be regenerated; use --verify-only.")
        from close_check_06a import verify_closure
        verify_closure()
        return
    if args.replace_own_draft:
        old_manifest = json.loads((OUT / "run_06a_manifest.json").read_text(encoding="utf-8"))
        assert old_manifest["status"] == "CHECK 06A - Pending approval"
        assert old_manifest["run"] == "RUN_06A_ALLOCATION_DESIGN_V1"
        for name, digest in old_manifest["outputs_sha256"].items():
            assert sha(ROOT / name) == digest, f"Draft changed externally: {name}"
        assert "CHECK 06A — Pending approval" in REPORT.read_text(encoding="utf-8")
    hashes, approval = verify_inputs()
    groups = pd.read_csv(BASE / "check_05_remaining_coverage.csv")
    assert len(groups) == len(QUOTAS) == 24
    assert int(groups.products.sum()) == 218115
    assert int(groups.available_first_attempt.sum()) == 194895
    assert list(groups.sampling_group_id) == list(RATIONALE)
    candidates = read_candidates()
    indexed = {k: v for k, v in candidates.groupby("sampling_group_id", sort=False)}
    allocations, all_scenarios, cells = [], [], []
    for budget in (10000, 12000, 15000):
        # Hamilton applies to proposed slot weights, not candidate population counts.
        weights = {g: q for g, q in zip(groups.sampling_group_id, QUOTAS)}
        # The 15k scenario exceeds sum(weights); scale integer weights first.
        expanded = {k: v * 10 for k, v in weights.items()}
        scenario_quotas = apportion(budget, expanded)
        for _, g in groups.iterrows():
            group = g.sampling_group_id
            s = indexed[group]
            assert len(s) == int(g.available_first_attempt)
            q = scenario_quotas[group]
            reserve = math.ceil(.25 * q)
            assert q + reserve <= len(s), f"Group shortage: {group}"
            f = s.fiber_100g.dropna()
            threshold = float(f.quantile(.75, interpolation="linear")) if len(f) else float("inf")
            cell_plan = plan_cells(s, q, threshold, g.category)
            random = sum(x["random_baseline"] for x in cell_plan)
            target = q - random
            success, downside = planning_rates(g.region, group)
            high_count = int((s.fiber_100g.notna() & s.fiber_100g.gt(0) & s.fiber_100g.ge(threshold)).sum())
            special_count = int((s.beverage_preparation_identified.eq(1) | s.beverage_specialist_signal.eq(1)).sum())
            row = {
                "scenario_id": f"core_{budget}", "region": g.region, "category": g.category,
                "sampling_group_id": group, "total_group_population": int(g.products),
                "prior_successful_ocr_llm": int(g.successful_ocr_llm),
                "prior_success_pct_of_group": round(100 * g.successful_ocr_llm / g.products, 4),
                "remaining_eligible_first_attempts": len(s),
                "first_attempt_warning_records": int(g.first_attempt_warning_records),
                "first_attempt_warning_pct": round(100 * g.first_attempt_warning_records / len(s), 4),
                "first_attempt_fibre_observed": len(f),
                "fibre_p75_non_null": threshold, "upper_observed_fibre_pool": high_count,
                "preparation_or_specialist_pool": special_count,
                "proposed_new_attempts": q, "random_baseline": random,
                "targeted_upper_fibre": target if g.category in {"snacks", "cereals"} else 0,
                "targeted_beverage_preparation_or_specialist": target if g.category == "beverages" else 0,
                "missing_m1_attempts": 0, "retry_attempts": 0,
                "bounded_preflight_reserves_proposed": reserve,
                "group_capacity_after_primary_and_reserves": len(s) - q - reserve,
                "assumed_success_fraction": success, "assumed_downside_success_fraction": downside,
                "expected_new_successes": round(q * success, 2),
                "expected_downside_new_successes": round(q * downside, 2),
                "budget_share_pct": round(100 * q / budget, 6),
                "quota_pct_of_first_attempt_pool": round(100 * q / len(s), 4),
                "projected_group_successes": round(g.successful_ocr_llm + q * success, 2),
                "projected_success_pct_of_group": round(100 * (g.successful_ocr_llm + q * success) / g.products, 4),
                "distinct_paid_units": "Quota target after ownership/dedup; exact evidence/configuration count pending RUN 06B",
                "quota_rationale": RATIONALE[group], "approval_status": "Proposed; CHECK 06A pending approval",
            }
            all_scenarios.append(row)
            if budget == 12000:
                allocations.append(row)
                cells.extend(cell_plan)
    assert sum(x["proposed_new_attempts"] for x in allocations) == 12000
    assert sum(x["random_baseline"] + x["targeted_upper_fibre"] + x["targeted_beverage_preparation_or_specialist"] for x in allocations) == 12000
    optional = optional_proposals()
    scenarios = []
    for name, core_budget, missing_budget, retry_budget, recommended in [
        ("core_10000", 10000, 0, 0, False), ("core_12000", 12000, 0, 0, True),
        ("core_15000", 15000, 0, 0, False),
        ("core_12000_plus_missing_500", 12000, 500, 0, False),
        ("core_12000_plus_retry_100", 12000, 0, 100, False),
    ]:
        core = [x for x in all_scenarios if x["scenario_id"] == f"core_{core_budget}"]
        expected = sum(x["expected_new_successes"] for x in core)
        downside = sum(x["expected_downside_new_successes"] for x in core)
        if missing_budget:
            expected += sum(x["expected_successes_if_approved"] for x in optional if x["optional_component"] == "missing_M1_exploratory")
            downside += 500 * .75
        if retry_budget:
            expected += 100 * .70
            downside += 100 * .50
        total = core_budget + missing_budget + retry_budget
        stress = total * (2 * .0015 + 3 * .0002) * 1.25
        scenarios.append({
            "scenario_id": name, "recommended": recommended, "core_first_attempts": core_budget,
            "optional_missing_m1_attempts": missing_budget, "optional_retry_attempts": retry_budget,
            "planned_processing_attempts_cap": total,
            "distinct_paid_work_units": "Primary-owned target equals attempts cap after dedup; exact units not yet enumerated",
            "expected_successful_extractions": round(expected, 2),
            "downside_expected_successful_extractions": round(downside, 2),
            "nominal_ocr_calls_per_job": 1, "nominal_llm_calls_per_job": 1,
            "assumed_ocr_chf_per_1000_calls": 1.50, "assumed_llm_chf_per_1000_calls": .20,
            "nominal_estimated_cost_chf": round(total * .0017, 2),
            "stress_ocr_calls_per_job": 2, "stress_llm_calls_per_job": 3,
            "stress_contingency_fraction": .25, "stress_estimated_cost_chf": round(stress, 2),
            "proposed_cost_envelope_chf": 10 * math.ceil(round(stress, 8) / 10),
            "pricing_basis": "Local Stage 10 estimate defaults; historical Azure spend corroborates scale only; not verified tariffs/all-in invoice",
            "success_basis": "FR .90/.80; UKIE and USCA .94/.85; USCA beverage C2/C3 .85/.70. Missing .85 FR/.90 others, downside .75; retry .70/.50. Planning assumptions, not forecasts.",
            "status": "Proposal only; attempt cap, optional pool and cost ceiling require approval",
        })
    history = historical_evidence()
    cross_region_repeat = int(candidates.barcode.duplicated().sum())
    unique_barcodes = int(candidates.barcode.nunique())
    country_totals = Counter()
    for x in cells:
        for country in x["country_cell"].split("|"):
            country_totals[country] += x["proposed_primary_attempts"]
    recommended = next(x for x in scenarios if x["recommended"])
    random_total = sum(x["random_baseline"] for x in allocations)
    fibre_total = sum(x["targeted_upper_fibre"] for x in allocations)
    specialist_total = sum(x["targeted_beverage_preparation_or_specialist"] for x in allocations)
    country_source = pd.read_csv(BASE / "check_05_country_composition.csv")
    country_source = country_source.loc[country_source.nutrition_population.eq("M1_complete_approved_group")]
    country_rows = []
    for country in ["FR", "UK", "IE", "US", "CA"]:
        z = country_source.loc[country_source.country.eq(country)]
        country_rows.append([country, int(z.successful_ocr_llm.sum()), int(z.available_first_attempt.sum()), country_totals[country]])
    region_rows = []
    for region in ["FR", "UK+IE", "US+CA"]:
        z = [x for x in allocations if x["region"] == region]
        region_rows.append([region, sum(x["proposed_new_attempts"] for x in z), round(sum(x["expected_new_successes"] for x in z), 1), sum(x["random_baseline"] for x in z), sum(x["targeted_upper_fibre"] for x in z), sum(x["targeted_beverage_preparation_or_specialist"] for x in z)])
    category_rows = []
    for region in ["FR", "UK+IE", "US+CA"]:
        for category in ["snacks", "cereals", "dairies", "beverages"]:
            z = [x for x in allocations if x["region"] == region and x["category"] == category]
            if z:
                category_rows.append([region, category, sum(x["total_group_population"] for x in z), sum(x["prior_successful_ocr_llm"] for x in z), sum(x["remaining_eligible_first_attempts"] for x in z), sum(x["proposed_new_attempts"] for x in z)])
    report = f"""# RUN 06A — Sampling allocation design (US/CA dairy excluded)

**CHECK 06A — Pending approval. Prepared 22 October 2026. Recommendation: Proceed with the proposed design after approval and RUN 06B validation.**

## Recommended decision

Propose **12,000 additional first-attempt jobs** from the M1-complete population, allocated to all 24 approved sampling groups in 11 strata. Propose **zero missing-M1 jobs and zero retries in the core scenario**. The 500-product missing-M1 beverage exploration and 100-retry variants are separate alternatives requiring explicit approval. No products, barcodes or ranks have been selected, no images requested, no processing pipeline modified and no paid calls made.

The core comprises **{random_total:,} random-baseline slots**, **{fibre_total:,} targeted upper-observed-fibre slots** in snacks/cereals and **{specialist_total:,} targeted explicit preparation/specialist slots** in beverages. All components are disjoint accounting allocations. Targeted slots supplement the original nutritional sampling groups without changing them. FR and UK/IE beverages retain one regional group each, US/CA beverages retain three provisional groups; this proposal adds within-group sampling components, not new clusters.

Expected valid successful extractions, including valid no-claim outcomes: **{recommended['expected_successful_extractions']:,.1f}**, with **{recommended['downside_expected_successful_extractions']:,.1f}** under the downside assumptions. These are planning expectations, not a guarantee or a success quota. Proposed cost envelope: **CHF {recommended['proposed_cost_envelope_chf']:,}**, subject to actual deployment/prices and complete-call accounting before execution. This is not paid-run approval.

## Inputs and immutable baseline

The exact [CHECK 05 approval](run_05_v1/check_05_approval.json), [manifest](run_05_v1/run_05_manifest.json), all 14 hashed baseline outputs, approved report/snapshot, manual-review policy and CHECK 04 decision/membership files were verified before design. The ledger stays local and is not copied. Hashes are in the [RUN 06A manifest](run_06a_v1/run_06a_manifest.json). Original eligibility, history, warnings, nutrition and memberships are unchanged. No current-history refresh is claimed here; it is mandatory again in RUN 06B and immediately before paid execution.

Input ledger: **476,626 regional products**, **218,115 M1-group products**, **258,511 missing M1**, **18,642 historical successes**, **194,895 core first-attempt candidates**, **108,882 missing-M1 first-attempt candidates**, **988 potential retries**, **45 manual holds**. Core allocation reads only the 194,895 approved M1 first-attempt candidates. Warnings, extreme nutrients, genuine concentrates and NULL fibre are not exclusions.

## Allocation logic and review tables

Quotas deliberately balance region/category comparison, remaining coverage and smaller nutritional groups. They are design choices, not the solution of a product-count-proportional optimizer. France receives the largest regional allocation but not a count-proportional share; UK/IE receives more intensive coverage of its smaller frame. Each core group has room for its primary quota plus ceil(25%) reserves. Reserves are preflight-only, not extra paid attempts. Tiny country cells may not have reserves and are explicitly flagged.

{table(region_rows, ['Region', 'Proposed attempts', 'Expected successes', 'Random', 'Upper fibre', 'Preparation/specialist'])}

{table(category_rows, ['Region', 'Category', 'M1 products', 'Prior success', 'First-attempt available', 'Proposed attempts'])}

### All 24 groups — principal approval table

{table([[x['region'], x['category'], x['sampling_group_id'], x['remaining_eligible_first_attempts'], x['proposed_new_attempts'], x['random_baseline'], x['targeted_upper_fibre'], x['targeted_beverage_preparation_or_specialist'], x['expected_new_successes']] for x in allocations], ['Region', 'Category', 'Group', 'Available', 'Proposed', 'Random', 'Fibre', 'Preparation/specialist', 'Expected success'])}

The [group allocation CSV](run_06a_v1/proposed_allocation.csv) additionally records full populations, prior success, budget shares, warnings, fibre thresholds/pools, reserves, projected coverage and quota-specific rationale. The smaller UK/IE dairy C3 receives 60 of 118 available first attempts; US/CA beverage C2 receives 120/256 and C3 100/202. These deliberately inspect small mixed groups without automatically exhausting them. Warning-heavy specialist groups remain eligible.

### Countries within merged regions

{table(country_rows, ['Country assignment', 'Prior M1 success', 'M1 first-attempt available', 'Proposed primary assignment count'])}

The last column is inclusive country-assignment composition of proposed primary regional slots. A both-country cell contributes to both country rows, so country rows must not be added as distinct jobs. The [country/component plan](run_06a_v1/country_component_plan.csv) contains mutually exclusive cells that do reconcile to exactly 12,000 slots, frame sizes, target pools and initial random probabilities. The proposed minority-assigned minimum is 10% of each group quota, capped at ceil(50%) of the available IE/CA-tagged pool. This protects Ireland and Canada while acknowledging scarcity, including US/CA cereal C1 with only one CA-tagged candidate and beverage C3 with five. Country presence is a saved OFF assignment, not a validated unique national pack. Oversampling changes selection weights and must remain visible.

## Selection components, probabilities and paid units

Draw the random baseline first from all candidates in each country cell. Then draw targets from the qualifying remainder. Fibre targets require observed positive fibre at or above the group's non-NULL P75; this is a relative sampling signal, not a regulatory claim. Beverage targets use only saved explicit preparation/specialist signals. Unknown forms and missing fibre stay in baseline. Targets are capped by cell pool size; residual target shortage converts to additional random selection in the same cell and is reported. See [selection rules](run_06a_v1/selection_rules.md) for exact thresholds, precedence and fallback rules.

There are **{unique_barcodes:,} distinct barcodes among 194,895 regional core candidates**, or **{cross_region_repeat:,} repeated regional barcode assignments**. This does not establish identical images/configuration. Proposed group slots are primary-owned work quotas. RUN 06B must reconcile actual image evidence and complete OCR/LLM configuration, retain secondary regional links, replace duplicate non-owner slots and prevent double-paid independent quotas. Exact distinct-work identities and counts are unknown now. Costs conservatively assume every primary slot becomes one distinct job; no overlap savings or secondary-coverage gains are budgeted. One job can contain several billable calls.

Retain exact source keys, original countries, every selection reason, exclusive accounting component, original frame/target denominators and deterministic order. Initial random-cell probability n/N is calculable; target-stage probability is conditional on the realized baseline. Final combined inclusion probabilities after targets, shared-work reconciliation and preflight are not simply group quota/N and are unavailable unless derived. Preserve initial random-draw evidence, report random and targeted samples separately, and do not pool them or historical coverage into unweighted population or market prevalence.

## Success, costs and alternative budgets

Original releases documented FR 5,719/6,170 (92.69%), UK/IE 5,748/5,956 (96.51%) and US/CA 5,660/5,894 (96.03%) completed outcomes. Saved later raw-result artifacts include FR additional targeted 1,118/1,277 (87.55%), Aldi/Lidl English 355/404 (87.87%), UK/IE additional English 197/210 (93.81%) and US/CA additional English 90/100 (90.00%). These heterogeneous artifacts overlap, use different prompts/selection and are not a pooled attempt denominator. The [historical evidence table](run_06a_v1/historical_success_evidence.csv) uses approved RUN 05 classified history, not a new interpretation of claims or unnormalized result headers. Technical LLM success alone does not prove a usable completed extraction. Valid no-claim outcomes count as successes.

Core planning assumptions: FR 90% (downside 80%), UK/IE and US/CA 94% (downside 85%), except provisional US/CA beverage C2/C3 at 85% (downside 70%). These are uncertain design assumptions informed by history, not fitted group-level predictions. Different prompts, languages, lower-quality remaining images and preparations can reduce success. Preflight attrition is unknown and is handled by reserves, not counted as paid success. No validated end-to-end success rate for this new sample exists.

Stage 10 defaults estimate OCR CHF 1.50 and LLM CHF 0.20 per 1,000 calls, yielding CHF 0.0017 for one of each. Historical approximate Azure spend was CHF 12/11,850 English products and CHF 8/6,170 French products; this corroborates scale but is not verified current all-in pricing. Nominal 12,000-job estimate = CHF 20.40. Stress assumption = 2 OCR + 3 LLM calls per job (allows for review/re-extraction), plus 25% contingency = CHF 54.00, rounded up to proposed **CHF 60** envelope. The existing tracker counts logical OCR invocations and does not establish complete retry billing; its default CHF 45 alert cannot be treated as the new validated ceiling. Actual provider accounting and deployment estimates must be checked before Julia launches any batch. More calls than the stress allowance are possible; no cap is guaranteed without the guard.

{table([[x['scenario_id'], x['planned_processing_attempts_cap'], x['optional_missing_m1_attempts'], x['optional_retry_attempts'], x['expected_successful_extractions'], x['downside_expected_successful_extractions'], x['nominal_estimated_cost_chf'], x['proposed_cost_envelope_chf']] for x in scenarios], ['Scenario', 'Jobs cap', 'Missing M1', 'Retries', 'Expected success', 'Downside', 'Nominal CHF', 'Proposed envelope CHF'])}

The [budget scenarios](run_06a_v1/budget_scenarios.csv) expose every assumption and distinguish jobs, work units, expected outcomes and costs. The [all-core-scenario quotas](run_06a_v1/allocation_scenarios.csv) show the feasible 24-group allocations for 10,000 / 12,000 / 15,000 attempts. Alternatives rescale the proposed effort weights by Hamilton allocation; they do not redesign groups. Recommend 12,000 because it expects about 11,000 usable outcomes while retaining margin below 15,000 jobs. The downside remains below 10,000 successes; no automatic success top-up is authorized.

## Optional populations kept separate

Recommend leaving both optional components at zero for the core approval. A separate 500-job missing-M1 exploration would allocate FR beverages 100, UK/IE 100 and US/CA 300, all without nutritional group labels. This could test material coverage bias: only 4,942/80,705 US/CA beverage products are M1 eligible (6.12%). The main core alone cannot represent the other 93.88%. FR and UK/IE M1 coverage is 58.83% and 60.22%, respectively. Exploration would not impute nutrition or make those products part of M1 clusters.

A separate 100-retry trial is listed by region/category only, conditional on demonstrably recoverable failures and explicit retry approval. It is not an instruction to retry the first 100 failed records. Retry pool mixes M1 and missing-M1 and must be suballocated before selection; no expected 70% rate is validated. The [optional proposals](run_06a_v1/optional_population_proposals.csv) expose capacity, quota, rationale and assumptions. Optional scenarios are alternatives, not additions automatically stacked on the core or 15,000-job option.

## RUN 06B checks and material dependencies

The [quality-check specification](run_06a_v1/selection_quality_checks.csv) contains 12 hard gates and 8 analytical review checks. Hard checks cover exact hashes/keys/countries, refreshed history and holds, image preflight, paid-work uniqueness, quota/replacement reconciliation, fixed seed, reproducibility, provenance and cost/checkpoint/merge controls. Analytical checks compare baseline and combined shortlist against their appropriate frames for nutrients, fibre, warnings, countries, beverage signals, projected coverage and deviations. Numeric soft thresholds prompt review, not automatic exclusions.

Seed 20261022 and canonical SHA256 ranking are specified for later selection. Preflight only the selected shortlist plus bounded reserves: ceil(25% group quota), capped by available same-cell/component reserves. No full-frame image scan. Rare cells can have no reserve; shortfalls must be reported. A paid failure consumes a slot and is not automatically replaced by another paid attempt.

**Execution dependency:** the existing Stage 10 checkpoint loads done barcodes, so it is not evidence-version aware. A validated evidence/configuration-aware checkpoint and merge path, complete-call budget guard, exact approved profiles/manifest, and repeated history checks are required before payment. RUN 06A changes no processing scripts and does not claim these gates have passed. Hydration prompt changes and reruns of historical successes are outside this core allocation.

## CHECK 06A — Decisions requested

1. Approve or adjust the recommended 12,000-slot, 24-group allocation and its country-cell composition.
2. Approve or adjust the random/fibre/preparation components, their thresholds, precedence, reserves and deviation rules.
3. Choose whether to keep missing-M1 exploration and retries at zero as recommended, or explicitly approve an optional variant with its detailed suballocation.
4. Approve or adjust the provisional CHF 60 envelope and planning expectations, subject to validated current deployment/pricing and complete-call guard before paid execution.
5. Authorize RUN 06B reproducible local selection and bounded preflight separately. Paid processing remains a later decision and is launched by Julia.

## Files and validation

- [Proposed allocation — recommended scenario](run_06a_v1/proposed_allocation.csv)
- [Country/component plan](run_06a_v1/country_component_plan.csv)
- [Selection rules](run_06a_v1/selection_rules.md)
- [Hard/soft quality-check specification](run_06a_v1/selection_quality_checks.csv)
- [Budget scenarios](run_06a_v1/budget_scenarios.csv)
- [Core quotas for all three budgets](run_06a_v1/allocation_scenarios.csv)
- [Separate optional populations](run_06a_v1/optional_population_proposals.csv)
- [Historical success evidence](run_06a_v1/historical_success_evidence.csv)
- [Inputs, outputs and validation manifest](run_06a_v1/run_06a_manifest.json)
- [Reproducible design script](../../pipeline/segmentation/run_06a_allocation_design.py)

Read 476,626 ledger rows in chunks; retained 194,895 core candidates in memory for aggregates only. Produced 24 recommended group rows, 72 core-scenario rows, {len(cells)} country/component cells, 5 budget scenarios, 11 optional-pool rows, {len(history)} historical evidence rows and 20 quality specifications. Verified input hashes, group/country/component sums, capacity including group reserves, projected successes, unchanged baseline and local output links. No data-quality correction or new exclusion was applied. Known limits: country-cell reserves, shared-work reconciliation, unknown preflight yield, uncertain success/cost and evidence-version pipeline readiness.

**CHECK 06A — Pending approval. Stop before barcode selection, image preflight or paid OCR/LLM processing.**
"""
    payloads = {
        OUT / "proposed_allocation.csv": csv_bytes(allocations),
        OUT / "allocation_scenarios.csv": csv_bytes(all_scenarios),
        OUT / "country_component_plan.csv": csv_bytes(cells),
        OUT / "budget_scenarios.csv": csv_bytes(scenarios),
        OUT / "optional_population_proposals.csv": csv_bytes(optional),
        OUT / "historical_success_evidence.csv": csv_bytes(history),
        OUT / "selection_quality_checks.csv": csv_bytes(quality_spec()),
        OUT / "selection_rules.md": RULES.encode("utf-8"),
        REPORT: report.encode("utf-8"),
    }
    manifest = {
        "run": "RUN_06A_ALLOCATION_DESIGN_V1", "status": "CHECK 06A - Pending approval",
        "design_date": "2026-10-22", "script": rel(Path(__file__)), "script_sha256": sha(Path(__file__)),
        "inputs_sha256": hashes, "approved_baseline_counts": approval["approved_counts"],
        "recommended_scenario": "core_12000", "random_seed_proposed_for_06b": SEED,
        "core_components": {"random_baseline": random_total, "upper_observed_fibre": fibre_total,
                            "explicit_preparation_or_specialist": specialist_total, "missing_m1": 0, "retry": 0},
        "candidate_barcode_reconciliation": {"regional_candidates": len(candidates), "distinct_barcodes": unique_barcodes,
                                             "repeated_assignments": cross_region_repeat, "distinct_paid_units_known": False},
        "outputs_sha256": {rel(p): hashlib.sha256(b).hexdigest() for p, b in payloads.items()},
        "validation": {"input_hashes_verified": len(hashes), "baseline_rows_read": 476626,
                       "core_candidate_rows_aggregated": len(candidates), "recommended_groups": 24,
                       "recommended_attempts": 12000, "scenario_capacity_including_group_reserves_passed": True,
                       "country_cell_capacities_passed": True, "no_product_selection": True,
                       "no_ledger_copy": True, "no_source_changes": True, "image_requests": 0, "ocr_llm_calls": 0},
    }
    payloads[OUT / "run_06a_manifest.json"] = json_bytes(manifest)
    # Verify immutable inputs again; no huge source databases are read or rehashed.
    assert all(sha(ROOT / name) == digest for name, digest in hashes.items())
    if args.verify_only:
        for path, data in payloads.items():
            assert path.read_bytes() == data, f"Reproducibility mismatch: {path}"
        print(json.dumps({"byte_identical_outputs": len(payloads), "inputs_unchanged": len(hashes),
                          "selection_performed": False}, indent=2))
    else:
        if not args.replace_own_draft:
            assert not OUT.exists() and not REPORT.exists(), "Versioned output already exists; use --verify-only."
            OUT.mkdir()
        else:
            assert old_manifest["inputs_sha256"] == hashes, "Draft source inputs changed."
        for path, data in payloads.items():
            path.write_bytes(data)
        print(json.dumps({"report": rel(REPORT), "recommended": recommended,
                          "components": manifest["core_components"], "country_assignments": dict(country_totals),
                          "outputs": len(payloads), "inputs_verified": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
