"""Reproduce the September 29 Wave 2 master. Run from any working directory."""
import argparse
import json
import sys
from pathlib import Path

MASTER_DIR = Path(__file__).resolve().parent
INGESTION = MASTER_DIR.parent
ROOT = INGESTION.parents[3]
sys.path.insert(0, str(ROOT))
from presentations.segmentation.production.workflow.build_master import build, WAVE2
from presentations.segmentation.production.workflow.artifact_paths import relocated, SEG
from presentations.segmentation.production.workflow.artifact_paths import LOCK, digest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=MASTER_DIR/"output")
    args = parser.parse_args()
    source = ROOT / "data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/release_work.db"
    corrected = ROOT / "data/06_brand_governance_outputs/wave2_identity_fix_v1/release_work.db"
    if corrected.with_name("manifest.json").exists():
        source = corrected
    reference = json.loads((INGESTION/"01_population/run_01/run_01_manifest.json").read_bytes())
    if source != corrected and digest(source) != reference["source_database_sha256"]:
        raise ValueError("Different Wave 2 product database")
    print(json.dumps(build(source,source.with_name("manifest.json"),LOCK,args.output,
                           WAVE2,relocated(SEG/"run_03_exclusions_v1.csv"),
                           relocated(SEG/"beverage_final_v1/eligibility_decisions.csv")),indent=2))
