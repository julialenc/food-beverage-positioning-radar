# v1.0.0 release scope and placement

**Version: 1.0.0. Planned tag: v1.0.0. Status: locally prepared; no tag or publication.** This is the first formal project release. The Streamlit board remains beta; no new Streamlit deployment is claimed. The frozen segmentation analytical identifier remains wave2_analytical_v1 and its digest is unchanged.

## Included

- Existing tracked Streamlit source, governance, attribution and private-label presentations at their established paths.
- The exact 72 declared segmentation inputs/references at their original repository paths, except the large governed database. These include the accepted master, locked claims, keyed research and final-package tables, manifests, approved decisions and historical report references.
- data/06_brand_governance_outputs/wave2_identity_fix_v1/: manifest.json and barcode_aliases.csv. The database is delivered as release/payload/source.db.gz.000 through .003; replay restores it only in a disposable workspace.
- presentations/segmentation/audit_replay/: replay.py, pinned requirements, documentation and the original/later human submissions plus provenance. The original human hash is recovered from preserved fields and verified against its historical identity; it is not a new review.
- release/: manifest, version, scope, release notes, validated replay evidence and four payload parts. No duplicate repository under source/ is needed. PUBLICATION_FILES.json is the exact future commit allowlist, including expected hashes.

## Excluded

Timestamped OFF ingestion downloads; raw image collections and OCR/LLM request/response/receipt ledgers; credentials and .venv; Wave 3; unrelated local experiments; candidate construction helpers; all outputs/ test workspaces; the uncompressed 3.44 GiB database; parked unapproved Streamlit changes. The separate Lovable website and UI test copy are outside this repository release.

## Reproduction boundary

The replay starts from the dated governed database and saved provider/human observations, rebuilds the master, recalculates H1–H12 and the control, runs format follow-ups and creates a new final package. It does not regenerate historical snapshots, provider decisions or human judgments. The accepted package is independently verified without alteration.

Wave 2 retrieval: 17 October 2026. Reporting cutoff: 29 September 2026. Open Food Facts coverage is uneven; selected communication assessments do not estimate market prevalence, healthfulness or legal compliance. Code is Apache-2.0; OFF data/derived databases retain ODbL attribution and obligations as described in the project citation and licensing documentation.

## Validation and remaining gates

The standalone input package passed a fresh 25-stage isolated replay, including 63 report-table instances. All six final data tables and the master matched accepted bytes. Small q differences and the pre-existing three-population processing metadata exception are recorded. The final repository layout is additionally checked for hashes, streamed restoration, Git ignore eligibility and byte-preservation attributes; scientific source and fixed input identities are compared with that tested package.

Commit/push and tag/publication remain separate actions requiring Julia's instruction. The eventual public release download must be checked. No analytical rerun, website republication or Streamlit deployment is part of this release preparation.
