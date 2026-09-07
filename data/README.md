# Data Folder Principles

This folder separates committed production inputs from ignored local outputs
created while running or auditing the pipeline.

## Frozen Principles

- `pipeline/` contains scripts, prompt files, package markers, and pipeline
  navigation documentation only; generated CSV outputs must not live there.
- `data/01_reference_inputs/` contains committed production reference inputs only.
- All raw Open Food Facts downloads, intermediate CSVs, audit exports, release
  samples, and local review files are generated outputs and remain ignored
  unless explicitly promoted to production reference status.
- Ignored output folders should stay visible on GitHub through `.gitkeep`
  placeholders so another user can see where regenerated files will appear.
- A forked repo should contain every committed reference input needed to run
  the non-credentialed pipeline stages from public Open Food Facts data.
- Scripts that consume ignored outputs must either generate those outputs in an
  earlier step or fail with a clear message naming the missing upstream step.
- Generated outputs that represent a pipeline run should include a run timestamp
  in the filename or database metadata where practical.
- Open Food Facts is live and crowdsourced; a fresh download can differ from a
  prior run, so audits must record the download or run timestamp.
- Azure credentials are required only for the paid OCR/LLM vision extraction
  stage; non-vision OFF refreshes should remain runnable without Azure.
- Local full SQLite databases and uncompressed deployment databases remain
  ignored; the committed deployable database artifact is the compressed public
  MVP database.

## Current Status

The final `data/` folder structure and any file renames will be decided after
the Phase 8 dependency audit. These principles govern that cleanup.
