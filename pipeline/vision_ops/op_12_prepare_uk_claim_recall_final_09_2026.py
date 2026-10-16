"""Prepare and optionally run the final UK/Ireland claim-recall rerun.

This reruns the five mainstream UK/Ireland retailer products currently exported
as NO_CLAIM_IDENTIFIED through the final Sep-2026 UK prompt/profile. The goal is
to reduce false negatives found during Tesco/Sainsbury's QA without reopening
the whole retailer OCR sample.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = (
    ROOT
    / "presentations"
    / "private_label_analysis"
    / "mainstream_uk_ie_retailers"
)
SAMPLE_PATH = (
    ROOT
    / "data"
    / "04_vision_sampling"
    / "mainstream_uk_ie_claim_recall_final_09_2026_ocr_llm_input.csv"
)
OUTPUT_PATH = (
    ROOT
    / "data"
    / "05_vision_release"
    / "vision_results_mainstream_uk_ie_claim_recall_final_09_2026_"
    "uk_test_09_2026_final.csv"
)
STAGE_10 = ROOT / "pipeline" / "stages" / "stage_10_extract_pack_claims.py"

LANGUAGE_PROFILE = "uk_test_09_2026_final"
EXPECTED_ROWS = 919
RETAILER_FILES = {
    "Asda": "asda_uk_ie_products_full_macro_positioning_details.csv",
    "Morrisons": "morrisons_uk_ie_products_full_macro_positioning_details.csv",
    "Sainsbury's": "sainsbury_uk_ie_products_full_macro_positioning_details.csv",
    "Tesco": "tesco_uk_ie_products_full_macro_positioning_details.csv",
    "Waitrose": "waitrose_uk_ie_products_full_macro_positioning_details.csv",
}


def clean_gtin(value: object) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def build_sample() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for retailer, filename in RETAILER_FILES.items():
        path = INPUT_DIR / filename
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        required = ["region", "category", "company", "GTIN", "Positioning", "image_url"]
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"{path} is missing columns: {missing}")

        subset = df[df["Positioning"].eq("NO_CLAIM_IDENTIFIED")].copy()
        subset["barcode"] = subset["GTIN"].map(clean_gtin)
        subset = subset[subset["barcode"].ne("")]
        subset["source_review_file"] = path.name
        subset["source_review_row"] = (subset.index + 2).astype(str)
        subset["retailer_label"] = retailer
        rows.append(subset)

    sample_source = pd.concat(rows, ignore_index=True)
    sample_source = sample_source.sort_values(
        ["company", "category", "brand", "product", "barcode"],
        kind="stable",
    )

    if len(sample_source) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} current UK/Ireland NO_CLAIM_IDENTIFIED "
            f"rows, found {len(sample_source)}. Refresh the retailer files or "
            "update EXPECTED_ROWS after reviewing the population change."
        )

    if sample_source["barcode"].duplicated().any():
        duplicates = sample_source.loc[
            sample_source["barcode"].duplicated(keep=False),
            ["barcode", "company", "product"],
        ]
        raise ValueError(
            "Duplicate GTINs found in recall sample:\n"
            + duplicates.to_string(index=False)
        )

    return pd.DataFrame(
        {
            "barcode": sample_source["barcode"],
            "sampling_region": sample_source["region"],
            "sampling_category": sample_source["category"],
            "sample_component": "uk_claim_recall_final_09_2026",
            "primary_stratum_id": (
                sample_source["company"]
                + "|"
                + sample_source["region"]
                + "|"
                + sample_source["category"]
            ),
            "sampling_weight": "",
            "weight_status": "targeted_unweighted",
            "target_company": sample_source["company"],
            "source_review_file": sample_source["source_review_file"],
            "source_review_row": sample_source["source_review_row"],
            "reviewed_positioning": sample_source["Positioning"],
            "image_language": "uk_test_09_2026_final",
            "image_url_present": sample_source["image_url"].str.strip().ne("").astype(int),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare and optionally run final UK claim-recall OCR/LLM."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run stage_10_extract_pack_claims.py after writing the sample.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use when --execute calls stage 10.",
    )
    args = parser.parse_args()

    sample = build_sample()
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(SAMPLE_PATH, index=False, encoding="utf-8-sig")

    print("\nFood & Beverage Positioning Radar - final UK claim recall prep")
    print(f"Sample: {SAMPLE_PATH}")
    print(f"Rows:   {len(sample):,}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Prompt profile: {LANGUAGE_PROFILE}")

    cmd = [
        args.python,
        str(STAGE_10),
        "--input",
        str(SAMPLE_PATH),
        "--language",
        LANGUAGE_PROFILE,
        "--output",
        str(OUTPUT_PATH),
    ]

    if args.execute:
        print("\nRunning stage 10:")
        print("  " + " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
    else:
        print("\nNo OCR/LLM calls made. To run from cmd:")
        print(
            "  python pipeline\\vision_ops\\"
            "op_12_prepare_uk_claim_recall_final_09_2026.py --execute"
        )
        print("\nAfter extraction completes, merge with:")
        print(
            "  python pipeline\\stages\\stage_11_merge_vision_results.py "
            f"--input {OUTPUT_PATH} "
            "--release-id release_2026_09_mainstream_uk_ie_claim_recall_final"
        )


if __name__ == "__main__":
    main()
