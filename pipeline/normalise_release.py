"""
normalise_release.py
--------------------
Applies deterministic consistency corrections to a final vision-results CSV.
No LLM calls — every rule is derivable from data already in the file.

Rules applied
  1. Unmapped-claim reconciliation
     completed + no_claims_detected=False + no PACK_CLAIM_FIELD true
       -> no_claims_detected = True
     The model uses no_claims_detected to mean "front-of-pack text worth
     noting"; the pipeline uses it to mean "a taxonomy claim exists". Where
     the model mapped nothing, its own judgement is that no taxonomy claim
     is present. Adds v3_unmapped_pack_text so those rows stay identifiable.
     Does NOT change pack_claims_found or the release denominator.

  0. Non-completed rows carry no claim data
     A partial JSON parse can leave boolean or numeric fields populated on a
     row that never reached "completed". All such values are cleared.

  2. Numeric-implies-flag (completed rows only)
     protein_amount_g      set -> protein_claim      = True
     sugar_reduction_pct   set -> reduced_sugar      = True
     fat_reduction_pct     set -> reduced_fat_claim  = True
     comparative_reference set -> comparative_claim  = True

  3. Out-of-range numerics
     protein_amount_g outside 0-100      -> nulled
     sugar_reduction_pct outside 0-100   -> nulled
     fat_reduction_pct outside 0-100     -> nulled
     Adds v3_numeric_out_of_range.

  4. Low-OCR flag (flag only, no reclassification)
     completed rows with fewer than --min-ocr-words words of OCR text get
     v3_low_ocr_text = True. A minimalist pack with two words is a valid
     no-claim observation, so these are NOT converted to unreadable.

Idempotent: running twice produces the same output.

Usage:
    python pipeline/normalise_release.py --input data/sample/vision_results_us_canada_final.csv
    python pipeline/normalise_release.py --input data/sample/vision_results_uk_ie_final.csv

Output:
    <input>_normalised.csv   plus a per-rule change log
"""

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT  = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "sample"
P = "v3_"   # flattened extraction-schema prefix

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
    "protein_amount_g":      "protein_claim",
    "sugar_reduction_pct":   "reduced_sugar",
    "fat_reduction_pct":     "reduced_fat_claim",
    "comparative_reference": "comparative_claim",
}
RANGE_FIELDS = ["protein_amount_g", "sugar_reduction_pct", "fat_reduction_pct"]


def to_bool(series: pd.Series) -> pd.Series:
    m = {"True": True, "true": True, "TRUE": True, "1": True,
         "False": False, "false": False, "FALSE": False, "0": False}
    return series.astype(str).str.strip().map(m).astype("boolean")


def blank(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().eq("")


def main():
    ap = argparse.ArgumentParser(description="Normalise a release vision-results CSV.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None,
                    help="Defaults to <input>_normalised.csv")
    ap.add_argument("--min-ocr-words", type=int, default=3)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(in_path)
    out_path = (Path(args.output) if args.output
                else in_path.with_name(in_path.stem + "_normalised.csv"))

    print(f"\nFood & Beverage Positioning Radar - normalise_release.py")
    print(f"\n  Input:  {in_path.name}")

    df = pd.read_csv(in_path, dtype={"barcode": str}, keep_default_na=False,
                     low_memory=False)
    print(f"  Rows:   {len(df):,}")

    bool_cols = [P + c for c in PACK_CLAIM_FIELDS if P + c in df.columns]
    for col in bool_cols + [P + "no_claims_detected"]:
        if col in df.columns:
            df[col] = to_bool(df[col])

    completed = df[P + "claim_extraction_status"] == "completed"
    changes = {}

    # ── Rule 0: non-completed rows carry no claim data ───────────────────────
    # Defensive. A partial JSON parse can leave numeric or boolean fields set
    # on a row that never reached "completed". Those values are not valid
    # observations and must not leak into any downstream count.
    not_completed = ~completed
    cleared = 0
    for col in bool_cols:
        bad = not_completed & df[col].fillna(False)
        if bad.any():
            df.loc[bad, col] = False
            cleared += int(bad.sum())
    for num in list(NUMERIC_IMPLIES) + RANGE_FIELDS:
        col = P + num
        if col in df.columns:
            bad = not_completed & ~blank(df[col])
            if bad.any():
                df.loc[bad, col] = ""
                cleared += int(bad.sum())
    if cleared:
        changes["claim data cleared on non-completed rows"] = cleared

    # ── Rule 2: numeric implies flag (completed rows only) ───────────────────
    for num, implied in NUMERIC_IMPLIES.items():
        ncol, icol = P + num, P + implied
        if ncol not in df.columns or icol not in df.columns:
            continue
        present = ~blank(df[ncol])
        fix = completed & present & ~df[icol].fillna(False)
        if fix.any():
            df.loc[fix, icol] = True
            changes[f"{num} -> {implied}=True"] = int(fix.sum())

    # ── Rule 3: out-of-range numerics ────────────────────────────────────────
    oor = pd.Series(False, index=df.index)
    for f in RANGE_FIELDS:
        col = P + f
        if col not in df.columns:
            continue
        v = pd.to_numeric(df[col], errors="coerce")
        bad = completed & v.notna() & ((v < 0) | (v > 100))
        if bad.any():
            print(f"\n  Out-of-range {f}:")
            for _, row in df.loc[bad].iterrows():
                print(f"    {row['barcode']}  {str(row.get('product_name',''))[:40]:<40} "
                      f"= {row[col]}")
            df.loc[bad, col] = ""
            oor |= bad
            changes[f"{f} out of range -> nulled"] = int(bad.sum())
    df[P + "numeric_out_of_range"] = oor

    # ── Rule 1: unmapped-claim reconciliation ────────────────────────────────
    any_claim = df[bool_cols].fillna(False).any(axis=1)
    ncd       = df[P + "no_claims_detected"]
    unmapped  = completed & (ncd == False) & ~any_claim   # noqa: E712

    other   = df.get(P + "other_claims",          pd.Series("", index=df.index))
    phrases = df.get(P + "detected_claim_phrases", pd.Series("", index=df.index))
    has_text = ~blank(other) | ~blank(phrases)

    df[P + "unmapped_pack_text"] = unmapped & has_text
    if unmapped.any():
        df.loc[unmapped, P + "no_claims_detected"] = True
        changes["no_claims_detected -> True (nothing mapped)"] = int(unmapped.sum())
        changes["  ...of which carried unmapped text"] = int(
            (unmapped & has_text).sum())

    # ── Rule 4: low-OCR flag ─────────────────────────────────────────────────
    words = df["ocr_text"].astype(str).str.split().str.len()
    low   = completed & (words < args.min_ocr_words)
    df[P + "low_ocr_text"] = low
    if low.any():
        changes[f"low_ocr_text flagged (<{args.min_ocr_words} words)"] = int(low.sum())
        if P + "ocr_quality" in df.columns:
            print(f"\n  Low-OCR completed rows by ocr_quality:")
            for val, n in df.loc[low, P + "ocr_quality"].value_counts().items():
                print(f"    {str(val) or '(blank)':<20} {n:>5,}")

    # ── Report ───────────────────────────────────────────────────────────────
    print(f"\n  -- Changes applied ------------------------------------------")
    if changes:
        for label, n in changes.items():
            print(f"  {label:<52} {n:>6,}")
    else:
        print("  (none — file already normalised)")

    any_claim_after = df[bool_cols].fillna(False).any(axis=1)
    print(f"\n  -- Release counts after normalisation ------------------------")
    print(f"  Completed observations:        {int(completed.sum()):,}")
    print(f"    with a mapped claim:         {int((completed & any_claim_after).sum()):,}")
    print(f"    no taxonomy claim:           {int((completed & ~any_claim_after).sum()):,}")
    print(f"      ...carrying unmapped text: {int(df[P + 'unmapped_pack_text'].sum()):,}")

    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n  Saved -> {out_path.name}")
    print(f"\n  Next: python pipeline/merge_scores.py --input {out_path.as_posix()}\n")


if __name__ == "__main__":
    main()
