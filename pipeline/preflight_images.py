"""
preflight_images.py
--------------------
Tests every image URL in the release sample before spending on Azure OCR.
Writes a preflight CSV with HTTP status, content type, and image size for
each barcode. Use the results to exclude unavailable images before the run.

Usage:
    python pipeline/preflight_images.py --input data/sample/us_release_sample.csv
    python pipeline/preflight_images.py --input data/sample/us_release_sample.csv --workers 32

Output:
    data/sample/us_release_sample_preflight.csv

Retention rule: keep only rows where image_preflight_status == "available".
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent


def clean_url(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def check_image(barcode: str, url: str) -> dict:
    url = clean_url(url)
    if not url:
        return {"barcode": barcode, "image_preflight_status": "missing",
                "image_content_type": None, "image_bytes": None}
    if not url.lower().startswith(("http://", "https://")):
        return {"barcode": barcode, "image_preflight_status": "invalid_url",
                "image_content_type": None, "image_bytes": None}
    try:
        r = requests.get(url, timeout=20, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        ct   = r.headers.get("Content-Type", "").lower()
        size = len(r.content)
        if r.status_code != 200:
            status = f"http_{r.status_code}"
        elif not ct.startswith("image/"):
            status = "not_image"
        elif size < 500:
            status = "too_small"
        else:
            status = "available"
        return {"barcode": barcode, "image_preflight_status": status,
                "image_content_type": ct, "image_bytes": size}
    except Exception as exc:
        return {"barcode": barcode,
                "image_preflight_status": f"error_{type(exc).__name__}",
                "image_content_type": None, "image_bytes": None}


def main():
    parser = argparse.ArgumentParser(
        description="Preflight-check image URLs in a release sample CSV."
    )
    parser.add_argument("--input", required=True,
                        help="Regional release sample CSV (must have barcode + image_url columns)")
    parser.add_argument("--workers", type=int, default=16,
                        help="Parallel HTTP workers (default: 16)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Not found: {input_path}")

    output_path = input_path.with_name(
        input_path.stem + "_preflight" + input_path.suffix
    )

    print(f"\nFood & Beverage Positioning Radar - preflight_images.py")
    print(f"\n  Input:   {input_path.name}")
    print(f"  Workers: {args.workers}")

    # Read only the columns we need — avoids memory error on wide CSV
    df = pd.read_csv(input_path, usecols=["barcode", "image_url"],
                     dtype={"barcode": str})
    print(f"  Rows:    {len(df):,}")
    print(f"  Missing image_url: {df['image_url'].isna().sum():,}")
    print(f"\n  Checking URLs (this may take a few minutes)...")

    rows = df[["barcode", "image_url"]].to_dict("records")
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(check_image, r["barcode"], r.get("image_url")): r["barcode"]
            for r in rows
        }
        done = 0
        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if done % 500 == 0:
                print(f"  ... {done:,} / {len(rows):,}")

    checks = pd.DataFrame(results)
    out = df.merge(checks[["barcode", "image_preflight_status",
                            "image_content_type", "image_bytes"]],
                   on="barcode", how="left")
    out.to_csv(output_path, index=False)

    print(f"\n  -- Preflight summary ------------------------------------")
    counts = out["image_preflight_status"].value_counts(dropna=False)
    for status, n in counts.items():
        pct = 100 * n / len(out)
        print(f"  {str(status):<30} {n:>5,}  ({pct:.1f}%)")

    available = (out["image_preflight_status"] == "available").sum()
    print(f"\n  Eligible for Azure OCR: {available:,} / {len(out):,} "
          f"({100*available/len(out):.1f}%)")
    print(f"\n  Saved → {output_path.name}")
    print(f"\n  Next step: filter to image_preflight_status == 'available'")
    print(f"  before running reset_release_sample.py and vision_extract.py.\n")


if __name__ == "__main__":
    main()
