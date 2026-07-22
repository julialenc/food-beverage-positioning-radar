"""
qa_release.py
--------------
Automated release QA over the final vision files and merged files for the
first release (US + UK). Hard checks fail the run; soft checks warn.

Usage:
    python pipeline/qa_release.py
    python pipeline/qa_release.py --us-merged data/sample/merged_results_20260722_210439.csv ^
                                 --uk-merged data/sample/merged_results_20260722_210446.csv
    python pipeline/qa_release.py --output-dir data/sample/qa

Exit code is 1 if any hard check fails, else 0.

Notes
  * The flattened extraction columns use a "v3_" prefix regardless of
    PROMPT_VERSION. That is cosmetic; the prefix is treated as the schema
    namespace here.
  * pack_claims_found semantics are load-sensitive: "" (assessed front pack,
    no claims) must not collapse into NaN (no valid observation). All CSVs
    are read with keep_default_na=False and normalised explicitly.
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT  = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "sample"
P = "v3_"   # flattened extraction-schema prefix

# ── Expected contracts ────────────────────────────────────────────────────────
EXPECTED_STATUS = {
    "front_of_pack":             "completed",
    "mixed_pack_text":           "completed",
    "ingredient_or_legal_panel": "not_applicable_non_front",
    "nutrition_label":           "not_applicable_non_front",
    "price_sticker":             "not_applicable_non_front",
    "uncertain":                 "unreadable",
}

# Must mirror PACK_CLAIM_FIELDS in merge_scores.py.
PACK_CLAIM_FIELDS = [
    "protein_claim", "sugar_free_claim", "reduced_sugar",
    "no_palm_oil", "no_artificial", "natural_claim",
    "fortification_claim", "fibre_claim", "probiotic_claim",
    "immune_claim", "energy_claim", "vitalite_concept",
    "sustainability_halo", "reformulation_claim", "comparative_claim",
    "glp1_positioning", "origin_quality_claim", "clean_label_claim",
    "minimal_ingredients_claim", "artisan_claim", "vegan_claim",
    "organic_claim", "dairy_free_claim", "lactose_free_claim",
    "plant_based_claim", "heritage_claim", "gluten_free_claim",
    "gender_targeting_claim", "gut_health_claim", "prebiotic_claim",
    "sleep_claim", "brain_health_claim", "reduced_fat_claim",
    "whole_grain_claim",
]

NUMERIC_IMPLIES = {
    "protein_amount_g":     "protein_claim",
    "sugar_reduction_pct":  "reduced_sugar",
    "fat_reduction_pct":    "reduced_fat_claim",
    "comparative_reference": "comparative_claim",
}
PCT_FIELDS = ["sugar_reduction_pct", "fat_reduction_pct"]

REQUIRED_COLS = [
    "barcode", "sampling_region", "sampling_category", "sample_component",
    "primary_stratum_id", "prompt_version", "vision_model",
    "ocr_status", "llm_status", "ocr_text",
    P + "image_context", P + "claim_extraction_status",
    P + "no_claims_detected", P + "detected_claim_phrases",
]

# ── Result collection ─────────────────────────────────────────────────────────
FAILURES, WARNINGS = [], []


def hard(label, ok, detail=""):
    if ok:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))
        FAILURES.append(f"{label}: {detail}")


def warn(label, ok, detail=""):
    if ok:
        print(f"  [ok]   {label}")
    else:
        print(f"  [WARN] {label}" + (f" — {detail}" if detail else ""))
        WARNINGS.append(f"{label}: {detail}")


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# ── Loading ───────────────────────────────────────────────────────────────────
def to_bool(series: pd.Series) -> pd.Series:
    """Map 'True'/'False'/'' to True/False/NA without collapsing '' into False."""
    m = {"True": True, "true": True, "TRUE": True, "1": True,
         "False": False, "false": False, "FALSE": False, "0": False}
    return series.astype(str).str.strip().map(m).astype("boolean")


def load_csv(path: Path) -> pd.DataFrame:
    """Read preserving '' vs missing, then normalise boolean columns."""
    df = pd.read_csv(path, dtype={"barcode": str}, keep_default_na=False,
                     low_memory=False)
    for col in df.columns:
        if col.startswith(P) and (
            col[len(P):] in PACK_CLAIM_FIELDS
            or col[len(P):] in {"no_claims_detected", "status_normalised"}
        ):
            df[col] = to_bool(df[col])
    return df


def blank(series: pd.Series) -> pd.Series:
    """True where the value is empty/whitespace."""
    return series.astype(str).str.strip().eq("")


def normalise_text(value) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


# ── A. Population integrity ───────────────────────────────────────────────────
def check_population(df, name, expected_rows, expected_region):
    section(f"A. Population integrity — {name}")
    hard(f"row count == {expected_rows:,}", len(df) == expected_rows,
         f"got {len(df):,}")
    hard("barcode has no blanks", not blank(df["barcode"]).any(),
         f"{blank(df['barcode']).sum()} blank")
    dupes = df["barcode"].duplicated().sum()
    hard("barcode is unique", dupes == 0, f"{dupes} duplicates")

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    hard("all required columns present", not missing, f"missing {missing}")

    for col, expected in [("sampling_region", expected_region)]:
        vals = set(df[col].unique())
        hard(f"{col} == {{{expected}}}", vals == {expected}, f"got {sorted(vals)}")

    for col in ["prompt_version", "vision_model"]:
        vals = {v for v in df[col].unique() if str(v).strip()}
        hard(f"{col} has exactly one value", len(vals) == 1, f"got {sorted(vals)}")
        if len(vals) == 1:
            print(f"         → {col} = {list(vals)[0]}")


# ── B. Pipeline status logic ──────────────────────────────────────────────────
def check_status_logic(df, name):
    section(f"B. Pipeline status logic — {name}")
    llm_ok = df["llm_status"] == "success"
    ocr_ok = df["ocr_status"] == "success"

    bad = df[llm_ok & ~ocr_ok]
    hard("llm success implies ocr success", bad.empty, f"{len(bad)} rows")

    bad = df[llm_ok & blank(df["ocr_text"])]
    hard("llm success implies non-empty ocr_text", bad.empty, f"{len(bad)} rows")

    bad = df[~ocr_ok & llm_ok]
    hard("ocr failure implies llm not success", bad.empty, f"{len(bad)} rows")

    for col in ["ocr_status", "llm_status"]:
        print(f"\n  {col} distribution:")
        for val, n in df[col].value_counts(dropna=False).items():
            print(f"    {str(val):<36} {n:>6,}")


# ── C. Context vs extraction status ───────────────────────────────────────────
def check_context_status(df, name):
    section(f"C. image_context vs claim_extraction_status — {name}")
    ctx    = df[P + "image_context"]
    status = df[P + "claim_extraction_status"]
    known  = ctx.isin(EXPECTED_STATUS)

    unknown = sorted(set(ctx[~known & ~blank(ctx)].unique()))
    hard("no unknown image_context values", not unknown, f"got {unknown}")

    expected = ctx.map(EXPECTED_STATUS)
    bad = df[known & (expected != status)]
    hard("context implies expected status", bad.empty,
         f"{len(bad)} contradictions")

    print(f"\n  image_context distribution:")
    for val, n in ctx.value_counts(dropna=False).items():
        print(f"    {str(val):<30} {n:>6,}  ({100*n/len(df):.1f}%)")

    if P + "status_normalised" in df.columns:
        norm = df[P + "status_normalised"].fillna(False)
        rate = 100 * norm.sum() / len(df)
        level = "normal" if rate <= 2 else ("review" if rate <= 5 else "investigate")
        warn(f"status_normalised rate {rate:.1f}% ({level})", rate <= 5,
             f"{norm.sum():,} rows corrected by the validator")


# ── D. Claim-state consistency ────────────────────────────────────────────────
def check_claim_states(df, name, out_dir=None):
    section(f"D. Claim-state consistency — {name}")
    completed = df[P + "claim_extraction_status"] == "completed"
    ncd       = df[P + "no_claims_detected"]

    bool_cols = [P + c for c in PACK_CLAIM_FIELDS if P + c in df.columns]
    any_claim = df[bool_cols].fillna(False).any(axis=1)

    # State 1 — completed, claims present
    bad = df[completed & (ncd == False) & ~any_claim]  # noqa: E712
    other = df.get(P + "other_claims", pd.Series("", index=df.index))
    has_other = ~blank(other)

    n_bad          = len(bad)
    n_bad_w_other  = int((completed & (ncd == False) & ~any_claim & has_other).sum())  # noqa: E712
    n_bad_no_other = n_bad - n_bad_w_other

    hard("completed + claims detected implies a mapped claim field",
         n_bad == 0,
         f"{n_bad} rows have no_claims_detected=False but no PACK_CLAIM_FIELD set "
         f"({n_bad_w_other} carry other_claims text, {n_bad_no_other} carry nothing)")

    if n_bad and out_dir:
        cols = ["barcode", "product_name", "brands",
                P + "image_context", P + "other_claims",
                P + "detected_claim_phrases"]
        cols = [c for c in cols if c in df.columns]
        path = out_dir / f"qa_{name}_unmapped_claims.csv"
        bad[cols].to_csv(path, index=False, encoding="utf-8-sig")
        print(f"         → written to {path.name}")

    # State 2 — completed, no claims
    bad = df[completed & (ncd == True) & any_claim]  # noqa: E712
    hard("completed + no claims implies every claim field False", bad.empty,
         f"{len(bad)} rows")

    # State 3 — not a valid observation
    bad = df[~completed & any_claim]
    hard("non-completed rows carry no claim fields", bad.empty,
         f"{len(bad)} rows")

    print(f"\n  Completed observations: {completed.sum():,}")
    print(f"    with a mapped claim:  {int((completed & any_claim).sum()):,}")
    print(f"    no claims:            {int((completed & ~any_claim).sum()):,}")


# ── E. Evidence checks ────────────────────────────────────────────────────────
def check_evidence(df, name):
    section(f"E. OCR-to-claim evidence — {name} (warnings)")
    phr_col = P + "detected_claim_phrases"
    if phr_col not in df.columns:
        warn("detected_claim_phrases present", False, "column missing")
        return

    completed = df[P + "claim_extraction_status"] == "completed"
    bool_cols = [P + c for c in PACK_CLAIM_FIELDS if P + c in df.columns]
    any_claim = df[bool_cols].fillna(False).any(axis=1)
    claim_rows = df[completed & any_claim]

    no_phrases = blank(claim_rows[phr_col]).sum()
    warn("claim rows carry evidence phrases",
         no_phrases / max(len(claim_rows), 1) < 0.10,
         f"{no_phrases:,} of {len(claim_rows):,} claim rows have no phrases")

    phrases = claim_rows[phr_col].astype(str).str.split("|")
    counts  = phrases.apply(lambda ps: len([p for p in ps if p.strip()]))
    warn("no more than 5 phrases per product", (counts > 5).sum() == 0,
         f"{int((counts > 5).sum()):,} rows exceed 5 phrases")

    long_phrase = phrases.apply(
        lambda ps: any(len(p.split()) > 10 for p in ps if p.strip())
    )
    warn("no phrase longer than 10 words", long_phrase.sum() == 0,
         f"{int(long_phrase.sum()):,} rows have an over-long phrase")

    # Phrase occurs in OCR text
    sample = claim_rows[~blank(claim_rows[phr_col])]
    missing_rows = 0
    for _, row in sample.iterrows():
        ocr = normalise_text(row["ocr_text"])
        ps  = [p for p in str(row[phr_col]).split("|") if p.strip()]
        if any(normalise_text(p) not in ocr for p in ps):
            missing_rows += 1
    pct = 100 * missing_rows / max(len(sample), 1)
    warn(f"evidence phrases occur in OCR text ({pct:.1f}% mismatched)",
         pct < 10, f"{missing_rows:,} of {len(sample):,} rows")


# ── F. Numeric-field consistency ──────────────────────────────────────────────
def check_numeric(df, name):
    section(f"F. Numeric-field consistency — {name}")
    for num, implied in NUMERIC_IMPLIES.items():
        ncol, icol = P + num, P + implied
        if ncol not in df.columns or icol not in df.columns:
            continue
        present = ~blank(df[ncol])
        bad = df[present & ~df[icol].fillna(False)]
        hard(f"{num} set implies {implied} True", bad.empty, f"{len(bad)} rows")

    col = P + "protein_amount_g"
    if col in df.columns:
        v = pd.to_numeric(df[col], errors="coerce")
        bad = ((v < 0) | (v > 100)).sum()
        hard("protein_amount_g within 0-100", bad == 0, f"{bad} out of range")

    for f in PCT_FIELDS:
        col = P + f
        if col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce")
            bad = ((v < 0) | (v > 100)).sum()
            hard(f"{f} within 0-100", bad == 0, f"{bad} out of range")


# ── G. Claim-key coverage ─────────────────────────────────────────────────────
def check_claim_keys(merged, name):
    section(f"G. Claim-key coverage — {name}")
    if merged is None or "pack_claims_found" not in merged.columns:
        warn("merged file available for key coverage", False, "skipped")
        return

    try:
        sys.path.insert(0, str(REPO_ROOT / "pipeline"))
        from tag_claims import CLAIM_TAXONOMY  # noqa
        taxonomy = set(CLAIM_TAXONOMY)
    except Exception as exc:
        warn("CLAIM_TAXONOMY importable from tag_claims", False, str(exc))
        return

    observed = {
        c for v in merged["pack_claims_found"]
        if str(v).strip()
        for c in str(v).split("|") if c.strip()
    }
    unmapped = sorted(observed - taxonomy)
    hard("every pack_claims_found key exists in CLAIM_TAXONOMY",
         not unmapped, f"unmapped: {unmapped}")
    print(f"         → {len(observed)} distinct claim keys observed")


# ── D2. pack_claims_found semantics in the merged file ────────────────────────
def check_merged_semantics(merged, name):
    section(f"D2. pack_claims_found semantics — {name}")
    if merged is None:
        warn("merged file available", False, "skipped")
        return

    pcf    = merged["pack_claims_found"]
    status = merged.get(P + "claim_extraction_status",
                        pd.Series("", index=merged.index))
    completed = status == "completed"

    is_null  = blank(pcf) & ~completed   # missing observation
    is_empty = blank(pcf) & completed    # assessed, no claims

    bad = merged[~completed & ~blank(pcf)]
    hard("non-completed rows have null pack_claims_found", bad.empty,
         f"{len(bad)} rows carry claims without a completed status")

    print(f"\n  pack_claims_found states:")
    print(f"    with claims (completed):    {int((completed & ~blank(pcf)).sum()):,}")
    print(f"    '' no claims (completed):   {int(is_empty.sum()):,}")
    print(f"    null (not a valid obs):     {int(is_null.sum()):,}")


# ── I. Failure bias by stratum ────────────────────────────────────────────────
def check_failure_bias(df, name):
    section(f"I. Completion rate by stratum — {name} (warnings)")
    completed = df[P + "claim_extraction_status"] == "completed"
    df = df.assign(_completed=completed)

    overall = 100 * completed.mean()
    print(f"  Overall completion: {overall:.1f}%\n")

    for dim in ["sampling_category", "sample_component",
                "pre_llm_positioning_signal", "formulation_family"]:
        if dim not in df.columns:
            continue
        g = df.groupby(dim)["_completed"].agg(["sum", "count"])
        g["pct"] = 100 * g["sum"] / g["count"]
        print(f"  By {dim}:")
        for idx, row in g.sort_values("pct").iterrows():
            flag = "  <-- LOW" if row["pct"] < 90 else ""
            print(f"    {str(idx)[:34]:<36} {int(row['sum']):>5,}/{int(row['count']):>5,}"
                  f"  {row['pct']:>5.1f}%{flag}")
        low = g[g["pct"] < 90]
        warn(f"all {dim} groups >= 90% completion", low.empty,
             f"{len(low)} below 90%: {list(low.index)[:5]}")
        print()

    if "primary_stratum_id" in df.columns:
        g = df.groupby("primary_stratum_id")["_completed"].agg(["sum", "count"])
        g["pct"] = 100 * g["sum"] / g["count"]
        low = g[(g["pct"] < 85) & (g["count"] >= 20)]
        warn("all strata (n>=20) >= 85% completion", low.empty,
             f"{len(low)} strata below 85%")
        small = g[g["sum"] < 10]
        warn("no stratum with achieved n < 10", small.empty,
             f"{len(small)} strata have fewer than 10 completed observations")


# ── J. Distribution sanity ────────────────────────────────────────────────────
def check_distributions(df, name):
    section(f"J. Distribution sanity — {name} (warnings)")
    completed = df[P + "claim_extraction_status"] == "completed"
    sub = df[completed]
    bool_cols = [P + c for c in PACK_CLAIM_FIELDS if P + c in df.columns]

    counts = {c[len(P):]: int(sub[c].fillna(False).sum()) for c in bool_cols}
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])

    print("  Top 20 claim fields (completed observations):")
    for claim, n in ranked[:20]:
        print(f"    {claim:<30} {n:>6,}  ({100*n/max(len(sub),1):.1f}%)")

    zero = [c for c, n in counts.items() if n == 0]
    warn("no claim field with zero observations", not zero,
         f"zero-count fields: {zero}")

    dominant = [c for c, n in counts.items() if n > 0.5 * len(sub)]
    warn("no claim field true for >50% of products", not dominant,
         f"dominant fields: {dominant}")

    per_product = sub[bool_cols].fillna(False).sum(axis=1)
    warn("no product with more than 10 claims", (per_product > 10).sum() == 0,
         f"{int((per_product > 10).sum())} rows")
    print(f"\n  Claims per completed product: "
          f"mean {per_product.mean():.2f}, max {int(per_product.max())}")

    words = sub["ocr_text"].astype(str).str.split().str.len()
    warn("completed rows have readable OCR text", (words < 3).sum() == 0,
         f"{int((words < 3).sum())} completed rows with fewer than 3 words")
    print(f"  OCR words on completed rows: "
          f"median {words.median():.0f}, p90 {words.quantile(0.9):.0f}")

    if P + "ocr_quality" in df.columns:
        print(f"\n  ocr_quality distribution:")
        for val, n in df[P + "ocr_quality"].value_counts(dropna=False).items():
            print(f"    {str(val):<20} {n:>6,}")


# ── Combined release checks ───────────────────────────────────────────────────
def check_combined(us, uk):
    section("A2. Combined release integrity")
    overlap = set(us["barcode"]) & set(uk["barcode"])
    hard("US and UK barcode sets do not overlap", not overlap,
         f"{len(overlap)} shared barcodes — the second merge would overwrite the first")
    if overlap:
        print(f"         → e.g. {sorted(overlap)[:5]}")

    total = len(us) + len(uk)
    print(f"\n  US rows:        {len(us):,}")
    print(f"  UK rows:        {len(uk):,}")
    print(f"  Combined:       {total:,}")

    us_ok = (us[P + "claim_extraction_status"] == "completed").sum()
    uk_ok = (uk[P + "claim_extraction_status"] == "completed").sum()
    print(f"\n  Valid observations — US: {us_ok:,}  UK: {uk_ok:,}  "
          f"total: {us_ok + uk_ok:,}")
    print(f"  This total is the release claim-prevalence denominator.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Release QA for the US/UK vision run.")
    ap.add_argument("--us-vision", default=str(SAMPLE_DIR / "vision_results_us_canada_final.csv"))
    ap.add_argument("--uk-vision", default=str(SAMPLE_DIR / "vision_results_uk_ie_final.csv"))
    ap.add_argument("--us-sample", default=str(SAMPLE_DIR / "us_release_sample.csv"))
    ap.add_argument("--uk-sample", default=str(SAMPLE_DIR / "uk_release_sample.csv"))
    ap.add_argument("--us-merged", default=None)
    ap.add_argument("--uk-merged", default=None)
    ap.add_argument("--output-dir", default=str(SAMPLE_DIR / "qa"))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\nFood & Beverage Positioning Radar - qa_release.py")
    print(f"Output dir: {out_dir}")

    us = load_csv(Path(args.us_vision))
    uk = load_csv(Path(args.uk_vision))

    n_us = len(pd.read_csv(args.us_sample, usecols=["barcode"], dtype=str))
    n_uk = len(pd.read_csv(args.uk_sample, usecols=["barcode"], dtype=str))

    us_merged = load_csv(Path(args.us_merged)) if args.us_merged else None
    uk_merged = load_csv(Path(args.uk_merged)) if args.uk_merged else None

    for df, name, n, region, merged in [
        (us, "US_CANADA", n_us, "US_CANADA", us_merged),
        (uk, "UK_IE",     n_uk, "UK_IE",     uk_merged),
    ]:
        check_population(df, name, n, region)
        check_status_logic(df, name)
        check_context_status(df, name)
        check_claim_states(df, name, out_dir)
        check_evidence(df, name)
        check_numeric(df, name)
        check_merged_semantics(merged, name)
        check_claim_keys(merged, name)
        check_failure_bias(df, name)
        check_distributions(df, name)

    check_combined(us, uk)

    # ── Summary ───────────────────────────────────────────────────────────────
    section("SUMMARY")
    print(f"  Hard failures: {len(FAILURES)}")
    for f in FAILURES:
        print(f"    FAIL  {f}")
    print(f"\n  Warnings: {len(WARNINGS)}")
    for w in WARNINGS:
        print(f"    WARN  {w}")

    if FAILURES:
        print(f"\n  RELEASE NOT READY — resolve hard failures first.\n")
        sys.exit(1)
    print(f"\n  All hard checks passed.\n")


if __name__ == "__main__":
    main()
