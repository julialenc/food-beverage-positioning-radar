"""
op_01_make_regional_samples.py
------------------------------
Splits sample_clean_run.csv into one file per region.
Reads in chunks to stay within memory limits.

Output:
    data/05_vision_release/us_release_sample.csv   (US_CANADA rows)
    data/05_vision_release/uk_release_sample.csv   (UK_IE rows)

Usage:
    python pipeline/vision_ops/op_01_make_regional_samples.py
"""
from pathlib import Path
import pandas as pd

REPO_ROOT  = Path(__file__).resolve().parents[2]
INPUT      = REPO_ROOT / "data" / "04_vision_sampling" / "sample_clean_run.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "05_vision_release"

REGIONS = {
    "US_CANADA": OUTPUT_DIR / "us_release_sample.csv",
    "UK_IE":     OUTPUT_DIR / "uk_release_sample.csv",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    buckets = {k: [] for k in REGIONS}

    print(f"Reading {INPUT.name} in chunks...")
    for chunk in pd.read_csv(INPUT, dtype={"barcode": str}, chunksize=500):
        for region in REGIONS:
            match = chunk[chunk["sampling_region"] == region]
            if not match.empty:
                buckets[region].append(match)

    for region, path in REGIONS.items():
        if buckets[region]:
            df = pd.concat(buckets[region], ignore_index=True)
            df.to_csv(path, index=False)
            print(f"  {region}: {len(df):,} rows -> {path.name}")
        else:
            print(f"  {region}: 0 rows - check sampling_region values")


if __name__ == "__main__":
    main()
