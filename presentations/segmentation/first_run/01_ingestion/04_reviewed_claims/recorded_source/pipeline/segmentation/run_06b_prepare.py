"""RUN 06B: frozen allocation, local selection, public-image preflight, no paid APIs.

Phases are separately resumable. Finalization never authorizes execution.
Original RUN 05/06A files and all production scripts are read-only inputs.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sqlite3
import tempfile
import threading
import time
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
A = SEG / "run_06a_v1"
FIVE = SEG / "run_05_v1"
OUT = SEG / "run_06b_v1"
KEY = ["barcode", "region", "category"]
SEED = 20261022
SCENARIO = "core_12000"
COMPONENTS = ["random_baseline", "targeted_upper_fibre", "targeted_beverage_preparation_or_specialist"]
FETCH_LOCK = threading.Lock()
FETCH_NEXT = 0.0


def run05_functions():
    # Reuse the exact approved function ASTs, avoiding the unrelated sklearn
    # import in RUN 05's clustering-document dependencies. No semantic rewrite.
    source = ROOT / "pipeline/segmentation/run_05_candidate_universe.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                 n.name in {"history", "claim_fields", "review_register", "read", "rel"}]
    assert len(functions) == 5
    namespace = {"ROOT": ROOT, "OUT": FIVE, "KEY": KEY, "pd": pd, "np": np, "ast": ast,
                 "json": json, "sqlite3": sqlite3, "sha": sha,
                 "CURRENT_DB": ROOT / "database/positioning_radar.db", "LEDGER01": SEG / "run_01/eligibility_ledger.csv",
                 "SUCCESS": ["success_with_claims", "success_no_claims", "success_claim_state_unknown"]}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["history"], namespace["review_register"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def flag(series):
    return series.astype(str).str.lower().isin(["true", "1", "1.0"])


def save(name, df):
    df.to_csv(OUT / name, index=False, lineterminator="\n", float_format="%.12g")


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def verified_inputs():
    approval = json.loads((A / "check_06a_approval.json").read_text(encoding="utf-8"))
    inputs = {**approval["approved_files_sha256"], **approval["approved_baseline_inputs_sha256"]}
    for p, expected in inputs.items():
        if sha(ROOT / p) != expected:
            raise ValueError(f"Frozen input hash mismatch: {p}")
    inputs[rel(A / "check_06a_approval.json")] = sha(A / "check_06a_approval.json")
    m = json.loads((A / "run_06a_manifest.json").read_text(encoding="utf-8"))
    for p, expected in m["inputs_sha256"].items():
        if sha(ROOT / p) != expected:
            raise ValueError(f"Additional approved input mismatch: {p}")
        inputs[p] = expected
    return inputs


def apportion(n, weights):
    if not sum(weights.values()):
        return {k: 0 for k in weights}
    exact = {k: n * v / sum(weights.values()) for k, v in weights.items()}
    alloc = {k: math.floor(v) for k, v in exact.items()}
    order = sorted(weights, key=lambda k: (-(exact[k] - alloc[k]), k))
    for k in order[:n - sum(alloc.values())]:
        alloc[k] += 1
    return alloc


def rank(frame, stage, group, cell):
    result = frame.copy()
    result["draw_sha256"] = [hashlib.sha256(json.dumps(
        [SEED, SCENARIO, stage, group, cell, r.barcode, r.region, r.category],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() for r in result.itertuples()]
    result = result.sort_values(["draw_sha256", *KEY], kind="stable")
    result["draw_rank"] = range(1, len(result) + 1)
    return result


def draw(frame, n, stage, group, cell, component, role, meta):
    ordered = rank(frame, stage, group, cell)
    selected = ordered.head(n).copy()
    selected["country_cell"] = cell
    selected["accounting_component"] = component
    selected["manifest_role"] = role
    selected["draw_stage"] = stage
    selected["stage_quota"] = n
    for key, value in meta.items():
        selected[key] = value
    selected["final_inclusion_probability"] = "unavailable_after_multistage_selection_and_preflight"
    selected["final_inclusion_weight"] = "not_derived"
    return selected


def select_from(frame, plan, allocation):
    primaries, reserves, cells = [], [], []
    group_N = allocation.set_index("sampling_group_id").remaining_eligible_first_attempts.astype(int).to_dict()
    for group, group_plan in plan.groupby("sampling_group_id", sort=True):
        ralloc = apportion(math.ceil(int(group_plan.proposed_primary_attempts.astype(int).sum()) * .25),
                           dict(zip(group_plan.country_cell, group_plan.proposed_primary_attempts.astype(int))))
        group_frame = frame.loc[frame.sampling_group_id.eq(group)]
        fibre_group_N = pd.to_numeric(group_frame.fiber_100g, errors="coerce").notna().sum()
        for p in group_plan.sort_values("country_cell").itertuples():
            cell = p.country_cell
            f = group_frame.loc[group_frame.countries.eq(cell)]
            fibre = pd.to_numeric(f.fiber_100g, errors="coerce")
            threshold = float(p.fibre_group_p75_non_null)
            is_fibre = p.target_component == "upper_observed_fibre"
            target = ((fibre.gt(0) & fibre.ge(threshold)) if is_fibre else
                      (flag(f.beverage_preparation_identified) | flag(f.beverage_specialist_signal))
                      if p.target_component == "explicit_preparation_or_specialist" else pd.Series(False, index=f.index))
            f = f.copy()
            f["qualifies_approved_target"] = target.astype(int)
            nrandom, ntarget = int(p.random_baseline), int(p.targeted_attempts)
            comp = COMPONENTS[1] if is_fibre else COMPONENTS[2]
            meta = {"seed": SEED, "scenario_id": SCENARIO, "frozen_group_frame_N": group_N[group],
                    "refreshed_group_frame_N": len(group_frame), "frozen_cell_frame_N": int(p.available_first_attempt),
                    "refreshed_cell_frame_N": len(f), "group_fibre_non_null_N": int(fibre_group_N),
                    "cell_fibre_non_null_N": int(fibre.notna().sum()), "fibre_threshold_frozen": threshold,
                    "target_pool_before_baseline_N": int(target.sum()),
                    "initial_random_inclusion_probability": nrandom / len(f) if len(f) else 0,
                    "replacement_status": "original_draw", "planned_paid_job": 0}
            b = draw(f, nrandom, "baseline", group, cell, COMPONENTS[0], "primary", meta)
            rest = f.loc[~f.index.isin(b.index)]
            targets = rest.loc[rest.qualifies_approved_target.eq(1)]
            meta["target_residual_after_baseline_N"] = len(targets)
            meta["conditional_target_probability"] = ntarget / len(targets) if len(targets) else 0
            # Preserve the exact approved component totals; do not silently convert target shortfalls.
            t = draw(targets, ntarget, "target", group, cell, comp, "primary", meta)
            for key in ["target_residual_after_baseline_N", "conditional_target_probability"]:
                b[key] = meta[key]
            primaries.extend([b, t])
            remaining = rest.loc[~rest.index.isin(t.index)]
            rn = min(ralloc[cell], len(remaining))
            split = apportion(rn, {COMPONENTS[0]: nrandom, comp: ntarget})
            rt_n = min(split[comp], int(remaining.qualifies_approved_target.sum()))
            rt = draw(remaining.loc[remaining.qualifies_approved_target.eq(1)], rt_n,
                      "reserve_target", group, cell, comp, "reserve", meta)
            rr = draw(remaining.loc[~remaining.index.isin(rt.index)], rn - rt_n,
                      "reserve_baseline", group, cell, COMPONENTS[0], "reserve", meta)
            rr["reserve_target_to_random_conversion_count_in_cell"] = split[comp] - rt_n
            rt["reserve_target_to_random_conversion_count_in_cell"] = 0
            reserves.extend([rr, rt])
            cells.append({"sampling_group_id": group, "country_cell": cell, "frozen_frame_N": int(p.available_first_attempt),
                          "refreshed_frame_N": len(f), "required_primary": nrandom + ntarget,
                          "drawn_primary": len(b) + len(t), "required_random": nrandom, "drawn_random": len(b),
                          "required_target": ntarget, "drawn_target": len(t), "nominal_reserves": ralloc[cell],
                          "drawn_reserves": len(rr) + len(rt), "reserve_shortfall": ralloc[cell] - rn,
                          "reserve_target_conversions": split[comp] - rt_n})
    return pd.concat(primaries).reset_index(drop=True), pd.concat(reserves).reset_index(drop=True), pd.DataFrame(cells)


def select():
    if (OUT / "selection_snapshot.json").exists():
        raise FileExistsError("Selection is frozen; use verify/preflight/finalize")
    inputs = verified_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    base = read(FIVE / "candidate_ledger.csv")
    assert len(base) == 476626 and not base.duplicated(KEY).any()
    history, review_register = run05_functions()
    agg, events, inventory, paths = history(base)
    register, holds = review_register(base)
    save("history_observations_refreshed.csv", events)
    save("history_source_inventory_refreshed.csv", inventory)
    save("history_status_refreshed.csv", agg)
    save("manual_review_overlay.csv", register)
    hcols = ["existing_successful_ocr_llm", "prior_failed_or_unusable", "history_uncertain_evidence"]
    overlay = base[KEY + ["sampling_group_id", "countries", "m1_eligible", "available_first_attempt", "manual_review_hold"]].merge(
        agg[["barcode", *hcols]], on="barcode", how="left", validate="many_to_one")
    for c in hcols:
        overlay[c] = overlay[c].fillna(False).astype(bool)
    new_holds = set(map(tuple, holds.loc[holds.manual_review_hold, KEY].to_numpy()))
    overlay["refreshed_manual_hold"] = [tuple(v) in new_holds for v in overlay[KEY].to_numpy()]
    overlay["fresh_first_attempt_eligible"] = (flag(overlay.available_first_attempt) & flag(overlay.m1_eligible) &
        ~flag(overlay.manual_review_hold) & ~overlay.refreshed_manual_hold & ~overlay[hcols].any(axis=1))
    reasons = pd.Series("", index=overlay.index)
    for reason, mask in [("frozen_not_first_attempt", ~flag(overlay.available_first_attempt)),
        ("missing_M1", ~flag(overlay.m1_eligible)), ("historical_success_including_no_claim", overlay[hcols[0]]),
        ("previous_failure_or_unusable", overlay[hcols[1]]), ("uncertain_history", overlay[hcols[2]]),
        ("manual_hold", overlay.refreshed_manual_hold | flag(overlay.manual_review_hold))]:
        reasons.loc[mask] += reason + "|"
    overlay["fresh_exclusion_reasons"] = reasons.str.rstrip("|")
    save("eligibility_overlay.csv", overlay)
    frame = base.loc[overlay.fresh_first_attempt_eligible.to_numpy()].copy()
    plan, allocation = read(A / "country_component_plan.csv"), read(A / "proposed_allocation.csv")
    primary, reserve, cells = select_from(frame, plan, allocation)
    # Repeat from independently reordered input to verify canonical ranking and exact row order.
    p2, r2, c2 = select_from(frame.iloc[::-1], plan.iloc[::-1], allocation)
    compare = KEY + ["sampling_group_id", "country_cell", "accounting_component", "draw_sha256", "draw_rank"]
    assert primary[compare].equals(p2[compare]) and reserve[compare].equals(r2[compare])
    assert not pd.concat([primary, reserve]).duplicated(KEY).any()
    save("selected_draw.csv", primary)
    save("reserve_draw.csv", reserve)
    save("country_component_reconciliation.csv", cells)
    recon = overlay.groupby(["region", "category"], sort=True).agg(
        population=("barcode", "size"), historical_successes=(hcols[0], "sum"),
        prior_failed_unusable=(hcols[1], "sum"), uncertain_history=(hcols[2], "sum"),
        holds=("refreshed_manual_hold", "sum"), current_core_first_attempt=("fresh_first_attempt_eligible", "sum")).reset_index()
    save("eligibility_reconciliation.csv", recon)
    for row in inventory.itertuples():
        if row.source == "frozen_RUN01_history":
            continue
        path = ROOT / row.source.split("::")[0]
        inputs[rel(path)] = row.hash
    inputs[rel(FIVE / "manual_review_policy.json")] = sha(FIVE / "manual_review_policy.json")
    write_json(OUT / "selection_snapshot.json", {"run": "RUN 06B", "date": "2026-10-23", "timezone": "Europe/Berlin",
        "seed": SEED, "scenario": SCENARIO, "input_sha256": inputs,
        "frozen_population": len(base), "refreshed_first_attempt_assignments": len(frame),
        "selected": len(primary), "reserves": len(reserve), "deterministic_reordered_input_check": True,
        "selected_sha256": sha(OUT / "selected_draw.csv"), "reserve_sha256": sha(OUT / "reserve_draw.csv"),
        "actual_history_refresh_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "client_decision_date_authoritative": True, "paid_calls": 0})
    print(json.dumps({"selected": len(primary), "reserves": len(reserve), "history_successes_regional": int(overlay[hcols[0]].sum()),
        "eligible": len(frame), "components": primary.accounting_component.value_counts().to_dict(), "reproducible": True}), flush=True)


def fetch_url(url):
    """Windows curl uses system certificate trust; never disable TLS verification."""
    result = {"requested_url": url, "checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "unresolved"}
    host = (urlparse(url).hostname or "").lower()
    if urlparse(url).scheme not in ("https", "http") or not (host == "openfoodfacts.org" or host.endswith(".openfoodfacts.org")):
        return {**result, "status": "unapproved_or_invalid_image_host"}
    temp = OUT / "preflight_tmp"
    temp.mkdir(exist_ok=True)
    target = temp / (hashlib.sha256(url.encode()).hexdigest() + ".download")
    try:
        # Smooth submissions rather than simultaneous worker bursts. On 429,
        # defer the whole queue; never turn a rate limit into a missing image.
        global FETCH_NEXT
        with FETCH_LOCK:
            wait = max(0, FETCH_NEXT - time.monotonic())
            if wait:
                time.sleep(wait)
            FETCH_NEXT = time.monotonic() + .18
        proc = subprocess.run(["curl.exe", "--silent", "--show-error", "--location", "--max-redirs", "4", "--proto", "=http,https",
            "--connect-timeout", "8", "--max-time", "22", "--max-filesize", "20000000",
            "--user-agent", "FoodBeveragePositioningRadar/1.0 (noncommercial technical image preflight)",
            "--output", str(target), "--write-out", "%{json}", url], capture_output=True, timeout=28)
        meta = json.loads(proc.stdout.decode("utf-8", errors="replace") or "{}")
        result.update({"http_status": meta.get("http_code", 0), "resolved_url": meta.get("url_effective", ""),
                       "content_type": meta.get("content_type", ""), "curl_exit": proc.returncode,
                       "transport_error": proc.stderr.decode("utf-8", errors="replace")[:500]})
        if proc.returncode:
            result["status"] = "transport_error"
        elif meta.get("http_code") != 200:
            result["status"] = "http_" + str(meta.get("http_code"))
            if meta.get("http_code") == 429:
                with FETCH_LOCK:
                    FETCH_NEXT = max(FETCH_NEXT, time.monotonic() + 5)
        elif not str(meta.get("content_type", "")).lower().startswith("image/"):
            result["status"] = "not_image"
        elif target.stat().st_size < 500:
            result["status"] = "too_small_existing_preflight_rule"
        else:
            content = target.read_bytes()
            result["image_sha256"] = hashlib.sha256(content).hexdigest()
            result["image_bytes"] = len(content)
            with Image.open(io.BytesIO(content)) as im:
                im.load()
                result.update({"width": im.width, "height": im.height, "format": im.format,
                               "decoded_rgb_sha256": hashlib.sha256(str(im.size).encode() + im.convert("RGB").tobytes()).hexdigest()})
            cache = OUT / "image_evidence" / (result["image_sha256"] + ".bin")
            cache.parent.mkdir(exist_ok=True)
            if not cache.exists():
                cache.write_bytes(content)
            result.update({"status": "technical_pass", "immutable_image_path": rel(cache),
                "front_panel_metadata_hint": "front" if "/front_" in url.lower() else "not_established",
                "usability_review_status": "pending_front_and_usability_review",
                "visual_review_performed": False})
    except Exception as exc:
        result.update({"status": "decode_or_transport_error", "error": type(exc).__name__ + ": " + str(exc)[:300]})
    finally:
        if target.exists():
            target.unlink()
    return result


def image_urls(row):
    url = row.image_url
    if row.region == "UK+IE" and "images.openfoodfacts.org/" in url and url.endswith(".400.jpg"):
        return [url[:-8] + ".full.jpg", url]
    return [url]


def preflight(workers=8, retry_transient=False):
    draws = pd.concat([read(OUT / "selected_draw.csv"), read(OUT / "reserve_draw.csv")], ignore_index=True)
    urls = sorted(set(image_urls(row)[0] for row in draws.itertuples()))
    log = OUT / "image_preflight_observations.jsonl"
    existing = {}
    observations_per_url = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            existing[r["requested_url"]] = r
            observations_per_url[r["requested_url"]] = observations_per_url.get(r["requested_url"], 0) + 1
    def needs_fetch(u):
        return (u not in existing or (observations_per_url.get(u, 0) < 2 and
            (existing[u]["status"] == "http_429" or (retry_transient and existing[u]["status"] == "transport_error"))))
    pending = [u for u in urls if needs_fetch(u)]
    print(f"Preflight: {len(urls)} bounded unique URLs, {len(pending)} pending; {workers} workers", flush=True)
    with log.open("a", encoding="utf-8", newline="\n") as output, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_url, u): u for u in pending}
        for n, future in enumerate(as_completed(futures), 1):
            record = future.result()
            existing[record["requested_url"]] = record
            observations_per_url[record["requested_url"]] = observations_per_url.get(record["requested_url"], 0) + 1
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            if n % 250 == 0:
                print(f"Preflight {n}/{len(pending)}; technical passes {sum(v['status']=='technical_pass' for v in existing.values())}", flush=True)
    # A UK full-size failure may use the original URL, as the approved profile
    # does. A rate limit is unresolved, never a reason to evade the server.
    fallback = sorted(set(image_urls(row)[-1] for row in draws.itertuples()
        if len(image_urls(row)) > 1 and existing[image_urls(row)[0]]["status"] not in {"technical_pass", "http_429"}))
    with log.open("a", encoding="utf-8", newline="\n") as output, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_url, u): u for u in fallback if needs_fetch(u)}
        for future in as_completed(futures):
            record = future.result()
            existing[record["requested_url"]] = record
            observations_per_url[record["requested_url"]] = observations_per_url.get(record["requested_url"], 0) + 1
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
    save("image_preflight_urls.csv", pd.DataFrame([existing[u] for u in sorted(set(urls + fallback))]))
    records = []
    for row in draws.itertuples():
        options = image_urls(row)
        chosen = next((existing[u] for u in options if u in existing and existing[u]["status"] == "technical_pass"), existing[options[0]])
        records.append({**{k: getattr(row, k) for k in KEY}, "manifest_role": row.manifest_role,
                        "original_image_url": row.image_url, **chosen,
                        "full_size_fallback_used": len(options) > 1 and chosen["requested_url"] == options[-1]})
    save("image_preflight_products.csv", pd.DataFrame(records))
    print(json.dumps(pd.DataFrame(records).status.value_counts().to_dict()), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["select", "preflight"])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retry-transient-once", action="store_true", help="One bounded non-paid transport recheck; prior observations retained")
    args = parser.parse_args()
    if args.phase == "select":
        select()
    else:
        preflight(args.workers, args.retry_transient_once)


if __name__ == "__main__":
    main()
