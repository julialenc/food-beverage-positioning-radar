# v1.0.0 — Food & Beverage Positioning Radar: Wave 2 audit and replay

First formal release of Food & Beverage Positioning Radar, bringing the existing beta Streamlit board, standalone private-label presentations and accepted Wave 2 segmentation research into one versioned project snapshot.

## Reproducible segmentation

The repository includes the governed starting inputs, accepted reference tables, frozen analytical package and a single offline replay command. The large source database is compressed into four parts and restored by hash in a separate workspace. The master Parquet is included directly. Both human-review source versions and their provenance are preserved.

The analysis follows commercial identity → nutritional formulation → communicated positioning. It retains five descriptive nutritional profiles alongside continuous variation, commercial distinctions and insufficient-evidence conclusions. The exploratory k=5 control is a methodological reference, not universal food segments.

## Validation

A fresh isolated run passed all 25 stages using only the candidate's bundled inputs and declared Python environment. The rebuilt master and all six final data tables matched accepted bytes exactly; 72 pinned original files were unchanged. The independent verifier checked 393 cohort key sets, 13,602 communication coverage cells, 15 regional profile cells, missing/zero guards, 12 separate human observations and 32,336 boundary annotations. Report verification covered 63 table instances.

Tiny adjusted-q differences and the already documented three-population processing metadata discrepancy are retained transparently. No statistical decisions or accepted findings changed. The frozen analytical package remains wave2_analytical_v1; this project tag does not create a new analytical wave.

## Scope and limitations

Wave 2 was retrieved on 17 October 2026 with a 29 September reporting cutoff. Replay starts from the dated governed data and saved observations; it does not repeat timestamped downloads, OCR/LLM calls or human judgments. A fresh dependency installation has not been certified. Wave 3 and unapproved local app changes are excluded. No new Streamlit deployment is claimed.

Open Food Facts is crowdsourced and unevenly covered. Product/assignment counts are not sales or market share. Packaging comparisons use selected known assessments and do not establish population prevalence, healthfulness or legal claim compliance.

Code: Apache-2.0. Open Food Facts data/derived databases: ODbL with attribution. See LICENSE and CITATION.md. The standalone research website is https://segmentation-food-beverage-radar.lovable.app/; the beta board is https://food-beverage-positioning-radar.streamlit.app/.

See presentations/segmentation/audit_replay/release/README.md for installation, replay and verification commands, and SCOPE.md and manifest.json for exact release contents.
