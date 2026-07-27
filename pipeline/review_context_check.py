"""
review_context_check.py
-----------------------
Applies the second-pass panel-context reviewer to rows an existing run
already classified as ingredient_or_legal_panel, using their SAVED OCR text.
No Azure Vision calls — one small LLM call per eligible row.

Use this to validate the reviewer before wiring it into a production run,
rather than re-running a whole 100-product OCR test.

It reuses review_image_context() from vision_extract.py, so the check and
the production path cannot drift apart.

Usage:
    python pipeline/review_context_check.py --input data/sample/vision_results_<ts>.csv
    python pipeline/review_context_check.py --input <file> --all-categories
    python pipeline/review_context_check.py --input <file> --language fr

Exit code is 0 always — this is a diagnostic, not a gate.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_extract as ve  # noqa: E402

P = "v3_"


def main():
    ap = argparse.ArgumentParser(
        description="Apply the context reviewer to existing legal-panel rows."
    )
    ap.add_argument("--input", required=True,
                    help="A vision_results CSV from a previous run")
    ap.add_argument("--language", default="fr", choices=sorted(ve.LANGUAGE_PROFILES),
                    help="Language profile supplying the review prompt (default: fr)")
    ap.add_argument("--all-categories", action="store_true",
                    help="Review every legal-panel row, not just the review "
                         "categories. Useful for measuring how many true "
                         "legal panels the reviewer would wrongly rescue.")
    ap.add_argument("--output", default=None,
                    help="Optional CSV of the per-row review results")
    args = ap.parse_args()

    profile = ve.LANGUAGE_PROFILES[args.language]
    review_file = profile.get("context_review_prompt")
    if not review_file:
        print(f"\n  Language '{args.language}' defines no context_review_prompt.\n")
        return
    path = ve.PROMPTS_DIR / review_file
    if not path.exists():
        print(f"\n  Review prompt not found: {path}\n")
        return
    ve.CONTEXT_REVIEW_PROMPT = path.read_text(encoding="utf-8").strip()

    df = pd.read_csv(args.input, dtype={"barcode": str},
                     keep_default_na=False, low_memory=False)

    ctx_col = P + "image_context"
    if ctx_col not in df.columns:
        print(f"\n  {ctx_col} not in {Path(args.input).name}\n")
        return

    panel = df[df[ctx_col] == "ingredient_or_legal_panel"].copy()

    cat_col = next((c for c in ("sampling_category", "query_category")
                    if c in df.columns), None)
    if cat_col and not args.all_categories:
        eligible = panel[panel[cat_col].str.lower()
                         .isin(ve.CONTEXT_REVIEW_CATEGORIES)]
    else:
        eligible = panel

    print(f"\nFood & Beverage Positioning Radar - review_context_check.py")
    print(f"\n  Input:            {Path(args.input).name}")
    print(f"  Review prompt:    {review_file}")
    print(f"  Rows in file:     {len(df):,}")
    print(f"  Legal-panel rows: {len(panel)}")
    print(f"  Eligible:         {len(eligible)}"
          + ("" if args.all_categories
             else f"  (categories {sorted(ve.CONTEXT_REVIEW_CATEGORIES)})"))

    if eligible.empty:
        print("\n  Nothing to review.\n")
        return

    rows = []
    for _, r in eligible.iterrows():
        ocr     = str(r.get("ocr_text", ""))
        product = str(r.get("product_name", ""))
        brand   = str(r.get("brands", ""))
        new_ctx, status = ve.review_image_context(ocr, product, brand)
        changed = new_ctx in ve.FRONT_CONTEXTS
        rows.append({
            "barcode":       r["barcode"],
            "product_name":  product,
            "brands":        brand,
            "category":      r.get(cat_col, "") if cat_col else "",
            "initial":       "ingredient_or_legal_panel",
            "reviewed":      new_ctx or "(unchanged)",
            "changed":       changed,
            "review_status": status,
            "ocr_words":     len(ocr.split()),
        })
        mark = "->" if changed else "  "
        print(f"\n  {mark} {product[:44]:<46} [{brand[:18]}]")
        print(f"       {r.get(cat_col,'') if cat_col else '':<10} "
              f"words={len(ocr.split()):<4} "
              f"reviewed={new_ctx or '(unchanged)'}  [{status}]")
        print(f"       {ocr[:150].replace(chr(10), ' | ')}")

    out = pd.DataFrame(rows)
    print(f"\n  -- Summary --------------------------------------------------")
    print(f"  Reviewed:            {len(out)}")
    print(f"  Rescued to front:    {int((out['reviewed'] == 'front_of_pack').sum())}")
    print(f"  Rescued to mixed:    {int((out['reviewed'] == 'mixed_pack_text').sum())}")
    print(f"  Kept as legal panel: {int(len(out) - out['changed'].sum())}")
    failed = out[~out["review_status"].eq("success")]
    if len(failed):
        print(f"  Review call failed:  {len(failed)} "
              f"({failed['review_status'].value_counts().to_dict()})")

    if args.output:
        out.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\n  Saved -> {Path(args.output).name}")

    print(f"\n  A rescued row still needs its claims extracted again — the "
          f"first pass\n  zeroed every claim field once it decided the image "
          f"was a legal panel.\n  That happens automatically in "
          f"vision_extract.py; this script only\n  reports what the reviewer "
          f"would decide.\n")


if __name__ == "__main__":
    main()
