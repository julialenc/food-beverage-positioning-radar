# Reference Data

Small, hand-maintained reference files committed to the repository for
reproducibility. These are **inputs and lookups** that the pipeline reads,
as distinct from generated outputs (which live in `data/sample/` and
`database/`, both gitignored).

Region grouping for the Market / region filter is defined one level up,
in `data/country_region_mapping.csv` — see the main `README.md` and the
product brief's Market / region section.

## Files

### company_brand_mapping.csv
276 in-scope brands mapped to their parent companies, with category and
HQ-country reference columns. Used to enable company-level roll-up and the
Product Explorer's Company / owner filter; product-level analysis is always
run at the brand level and rolled up, never computed at the company level.
Schema and maintenance notes are documented in `docs/BRAND_COMPANY_MAPPING.md`.
See `docs/ADR.md` ADR-007 for the storage rationale.

## Generated outputs (not stored here)

These are produced by running the pipeline and are intentionally **not**
committed (see `.gitignore` and `docs/ADR.md` ADR-010 for the data-flow
contract):

- `data/sample/smart_sample_<timestamp>.csv` — the priority image sample,
  produced by `pipeline/smart_sample.py` (four-tier sampling; see ADR-010).
- `data/reference/vision_results_<timestamp>.csv` — Azure Vision OCR plus
  LLM claim-extraction results, produced by `pipeline/vision_extract.py`
  and consumed by `pipeline/merge_scores.py --input`. A fresh extraction
  run writes a new timestamped file here.

## Reproducing from scratch

Run the pipeline stages in order as documented in the main `README.md`.
The vision-extraction stage calls a paid Azure service, so it is the one
stage worth running deliberately rather than as part of an automatic loop.
