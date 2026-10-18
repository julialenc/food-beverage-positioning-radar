# Incremental population policy

Decision approved by Julia Lenc on 2026-10-17. This policy is encoded and tested
on a separate database copy. It is **not yet connected to the production
ingestion stages, app queries or deployment export**.

## Approved starting population

| Layer | Starting products | Meaning |
|---|---:|---|
| Full preserved working database | 512,937 | All records remain available for provenance and audit. |
| Retained baseline | 378,835 | Explicitly approved group with stored `ingested_at = 20260903_030215`. |
| Archived older group | 134,102 | Preserved but not automatically reactivated. |
| Retained records within deployment scope | 374,066 | Current regions/categories applied to retained records. |
| Display-eligible records within deployment scope | 270,152 | Existing brand and Product Explorer hard-validity gates applied dynamically. |

The initial timestamp is used once to identify the approved baseline. Future
membership must not be derived from `MAX(ingested_at)`. An unchanged product
remains retained when another product is updated.

Retention is separate from data quality and deployment scope. A retained record
with incorrect or implausible metrics remains available in the database even
when its existing inclusion fields hide it. Corrections may make it eligible
later. Conversely, a later invalid update may hide a retained record without
removing its membership. Moving outside the launch category/region scope also
does not erase the record.

No nutrition thresholds, mapping definitions, raw-source fields or chart-range
rules are changed by this policy. Market Overview must continue to use the
Product Explorer hard gate; chart-range controls only affect visualization.

## Dates and provenance

Julia confirms **29 August 2026** as the original OFF capture date and chooses
**29 September 2026** as the wave-2 proxy cutoff. The 3 September timestamp is a
local load of the cleaned August file. The capture date and proxy cutoff are
stored as owner-approved metadata; no retrospective date filtering is
implemented in this step.

Private-label work subsequently added OCR/LLM coverage and reviewed derived
corrections, not another OFF product ingestion. The preserved baseline is the
current enriched working state, not a reconstruction of August claim results.
The frozen local capture is identified by its manifest and database checksum;
the original capture is not rewritten when this policy is added to a copy.

## Encoded behavior

`pipeline/rules/population_policy.py` adds three metadata tables and three views:

- `population_policy` records the approved seed, dates and source identity.
- `population_membership` records retained/archived membership independently
  of the product's last load timestamp and quality flags.
- `population_admissions` records accepted batch membership and reviewed re-entry.
- `retained_products` includes retained products regardless of display gates.
- `retained_deployment_products` applies the existing launch regions/categories.
- `retained_display_products` additionally applies existing brand and
  `include_in_product_table` gates; it is not a fixed barcode whitelist.

Unchanged A is carried forward, updated B remains retained, and an accepted new
C is registered. Absence from a batch never implies deletion or archive status.
An archived barcode needs an explicit review reference before re-entry.
Initialization refuses a mismatched seed or an existing policy. Barcodes remain
strings, including leading zeros.

The batch helpers govern membership only. A future loader must validate the
source revision, resolve scope, preserve raw evidence and history, and enforce
batch completeness before accepting a product. Membership preflight must happen
before product writes. Product upserts and membership registration must then
share a transaction. The current stage-05 loader commits internally; the
separate copy-only writer described below now provides this transaction.

## Local trial and checks

`pipeline/maintenance/prepare_population_policy_trial.py` accepts a completed
baseline capture and creates a new copy under the ignored directory
`data/06_brand_governance_outputs/population_policy_trials/`. It refuses to
overwrite an existing trial. It verifies the frozen baseline checksum, creates
a consistent SQLite backup, then initializes membership under a write guard
that prohibits mutations of original tables. The original schema, row counts
and retained/deployment/display barcode identities must remain unchanged.

`pipeline/validation/check_07_population_policy.py` uses the actual stage-05
product upsert function against disposable in-memory databases. It checks A/B/C
behavior, repeat safety, leading-zero identifiers, dynamic display eligibility,
scope exits, archived re-entry, empty/rejected batches, initialization guards and
membership transaction rollback. Synthetic October records deliberately verify
that the September proxy cutoff has not been implemented as a filter.

These checks do not certify the whole pipeline for incremental ingestion. The
live app and production database continue to use their existing behavior.

## Historical integration boundary

Membership, successive product/analysis snapshots and source-version ordering
are implemented in the copy-only path below. Downstream population alignment,
claim-evidence freshness and release construction have been rehearsed separately.
The real October retrieval has reached ingestion-only staging; governed
processing and writer admission for that wave await Julia's review. Historical
September field values are not reconstructed by this proxy.

## Copy-only transactional path (17 October 2026)

`pipeline/rules/incremental_ingestion.py` now provides a separate processed-batch
writer. It does not change Stage 05 or connect production consumers. The
maintenance entry point `run_incremental_ingestion_trial.py` creates a fresh
copy from a checksum-verified completed population-policy trial. Writable
databases are restricted to marked `trial.db` files under the ignored
`data/06_brand_governance_outputs/incremental_ingestion_trials/` directory.

The transaction includes product and analysis changes, full before/after row
snapshots, membership admissions and a completed batch record with the exact
input payload and checksum. Validation of every record precedes writes. A
failure rolls all these changes back. Unchanged products outside the batch
remain retained, and archived re-entry still requires a review reference.

Input contract (JSON):

- `batch_id`: nonempty immutable identifier; reuse with different content fails.
- `retrieved_at`: ISO datetime, distinct from the source revision and local load.
- `source_reference` and `processing_reference`: nonempty evidence references.
- `completeness`: `complete: true`, exact `record_count`, and an evidence
  `reference`. This is an upstream assertion, not proof that API pages were
  actually collected. The future collector must establish that proof.
- `reviewed_reentries`: barcode-to-review-reference object, empty when unused.
- `records`: objects containing a string `barcode`, a `product` field object
  and an `analysis` field object (which may be empty).

Product patches require `last_modified_t`. Absent keys preserve existing values;
explicit JSON null clears a value; numeric zero remains zero. New products
require every product field except the separately supplied barcode and the
loader-owned `ingested_at`, with explicit nulls for unavailable values. Unknown
fields, inappropriate types, duplicate barcodes and non-finite numbers fail.
The caller must provide governed, internally consistent processed fields; this
writer does not rerun category, brand or nutrition rules on a partial patch.

Source revisions are compared as UTC datetimes. Legacy timezone-free cleaned
timestamps are interpreted as UTC. Missing/unparseable prior revisions fail
closed pending explicit review. Older revisions and conflicting equal revisions
are rejected; an equal revision with unchanged supplied values is accepted
without new product history. Analysis-only recomputation at an unchanged source
revision is deliberately outside this contract and needs a versioned analysis
workflow. A newer source revision cannot postdate retrieval.

An exact batch replay is a no-op even after later batches; it cannot rewind
membership. JSON object key order does not affect identity, but record order
does. New batch identifiers with unchanged product values can register an
accepted observation without changing the product or generating history.

`incremental_batches` retains the input payload and completion time;
`incremental_history` retains complete before/after product and analysis rows
for each changed barcode. A JSON null before-state denotes a new row. Existing
pack evidence is preserved when omitted, but is **not certified fresh** after
a source/image change. Claim versioning, completed-release selection, aggregates
and app/deployment alignment remain required before real ingestion.

Validation entry points:

```text
python -B pipeline/validation/check_08_incremental_ingestion.py
python -B pipeline/maintenance/run_incremental_ingestion_trial.py --policy-trial <completed-policy-trial-directory> --synthetic-check
```

The synthetic full-size check changes one existing product and adds one clearly
labelled synthetic record on a new copy. It checks history, unchanged original
rows/tables, exact replay, population counts, SQLite integrity and foreign keys,
and protected-file hashes. The output is validation evidence, not deployable data.
For an explicit processed JSON batch, use `--batch-file <path>` in place of
`--synthetic-check`; that also creates a new copy and never downloads OFF data.

The agreed September proxy uses records eligible by 29 September with values
retrieved in October, rather than claim historical September values. The
retrieval target is 17 October, but the collector records actual retrieval
timestamps; a later run must not be backdated. The writer itself does not apply
the cutoff; the following staging layer owns that decision.

## Bulk collection and proxy staging (17 October 2026)

`pipeline/maintenance/collect_off_snapshot.py` downloads the full compressed
OFF TSV export into a new local snapshot directory. It does not reuse the old
bootstrap cache. This follows [OFF's bulk collection guidance](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/)
and avoids treating capped or skipped API pages as a complete wave. A full scan
also observes retained products that have left the original category/country
scope. This collection path does not modify the existing Stage 01 scripts.

Transport completeness requires the declared byte length, valid gzip EOF/CRC
and a recorded SHA-256. Interruptions preserve a partial file without a complete
manifest. Resume requires the original strong ETag, exact HTTP byte range and
matching remaining length; changed source versions or ignored Range requests
fail closed. If safe resume is unavailable, use a new snapshot directory rather
than combining versions. The single-writer lock is removed on normal exit;
after a process kill, inspect the lock and partial download before recovery.

The manifest retains retrieval start/end, source URL, ETag and export
Last-Modified where supplied. Export age, retrieval time, OFF product creation,
OFF product revision and the proxy cutoff are distinct. A bulk snapshot scan is
complete relative to that file, not proof of OFF's retail-market coverage or a
simultaneous point-in-time export. The complete compressed source stays local,
including records subsequently excluded or held.

`pipeline/rules/proxy_wave.py` stages evidence on a marked ingestion copy:

| Observation | Staging decision |
|---|---|
| Retained product with newer valid OFF revision | Process update even when the revision is in October. |
| Retained product outside current source scope | Process scope exit; retain its stored membership. |
| Retained product absent from the export | Leave it stored and retained; absence is not deletion. |
| Retained product with equal revision | Carry forward; no new source revision established. |
| Older, invalid or future-to-retrieval revision | Hold for review, without overwriting current evidence. |
| New in-scope candidate created through 29 September | Stage for governed processing, not automatic membership admission. |
| New candidate created after the cutoff | Exclude from this proxy wave; preserve its raw observation. |
| New candidate with empty, zero or invalid creation timestamp | Hold for review. |
| Archived product | Hold unless an explicit reviewed re-entry reference is supplied; reviewed admissions also require cutoff eligibility. |

The default cutoff is **29 September, inclusive, in Europe/Berlin**. Its stored
exclusive UTC boundary is **2026-09-29T22:00:00Z** (midnight starting 30 September
locally). Both date and timezone are explicit CLI inputs and immutable within
a wave. There is no `last_modified_t <= cutoff` filter and no global
`last_modified_t > 29 August` filter: a previously uncaptured old record can
still be a new candidate. Original capture date remains 29 August.

New-candidate scope uses the existing Stage 01 category/country rules unchanged.
Known retained records bypass that candidate filter so scope exits are observed.
Those source rules currently target France, UK and US country tags; this does
not expand acquisition to additional tags or redefine the existing regional
mapping. Reviewed mapping overrides and final scope treatment still belong to
governed processing before writer admission.

Four additive staging tables hold the wave contract, source-record hashes,
raw selected observations with decision reasons, and conflicting raw rows.
Raw source values remain text:
empty and zero are preserved. Product, analysis and membership tables are guarded
against writes. Identical duplicate records are counted but staged once.
Conflicting rows for one barcode are preserved separately; that barcode is
held from admission pending review, with no arbitrary source-row winner.
Each checkpoint commits observations and
its row watermark together. Resume re-streams the same checksum-verified file,
skips already committed rows, and refuses changed source, cutoff or rules. A
parse error, failed checksum, malformed identifier or empty bulk file leaves the
wave incomplete. Only full verified EOF marks it complete. One wave is allowed
per fresh copy, before any writer batch.

Entry points (commands are deliberate actions, not automatic monthly jobs):

```text
python -B pipeline/maintenance/collect_off_snapshot.py --output-dir data/02_raw_off_downloads/incremental_snapshots/<new-capture-directory>
python -B pipeline/maintenance/stage_proxy_wave.py --policy-trial <completed-policy-trial-directory> --snapshot-dir <completed-snapshot-directory> --wave-id <unique-wave-id>
python -B pipeline/maintenance/stage_proxy_wave.py --database <same-copy-trial.db> --snapshot-dir <same-snapshot-directory> --wave-id <same-wave-id>
python -B pipeline/validation/check_09_proxy_wave.py
```

The third command resumes staging, not collection. The Python staging API accepts
reviewed archived re-entry references; the CLI defaults to none. Fifteen offline
checks cover transport resume, scan resume, source drift, cutoff boundaries,
archived review, malformed dates, October revisions, scope exits, duplicate
handling and corrupt/empty input. Full-size synthetic validation is available
with `check_09_proxy_wave.py --full-size-policy-trial <directory>`.

The staging layer is now connected to the writer on marked copies through the
governed adapter below. No live OFF download was performed during these offline
implementation checks. Downstream population/release alignment, claim freshness
and the end-to-end rehearsal remain required before production use.

### Real October retrieval, September proxy: ingestion-only checkpoint

On 17 October, a completed OFF bulk export was retrieved to
`data/02_raw_off_downloads/incremental_snapshots/wave2_proxy_20260929_retrieved_20261017T153127Z/`.
The source manifest records its actual retrieval time and SHA-256. Its 4,535,553
data rows were staged on a fresh guarded copy at
`data/06_brand_governance_outputs/incremental_ingestion_trials/live_proxy_stage_20261017T153127Z_v3/`.
The wave is complete with 4,535,493 distinct source barcodes. The inclusive
29 September Europe/Berlin cutoff has an exclusive UTC boundary of
2026-09-29T22:00:00Z. This is a September-*eligible* proxy using the October
retrieval values, not a reconstruction of historical September field values.

The saved `proxy_report.json` records 153,023 new candidates for later governed
processing, 231,232 equal-revision carry-forwards, 76,624 archived re-entry
holds and 13 conflict holds among selected observations. Sixty source barcodes
have conflicting duplicate rows; all are held from admission, with evidence
preserved in the original snapshot and the staging conflict table. At this
ingestion-only checkpoint, no governed processing, writer batch or downstream
release had run. Those steps were subsequently completed on the separate copy,
as recorded below.

## Governed processing and writer connection (17 October 2026)

`pipeline/rules/governed_ingestion.py` consumes only explicit eligible decisions
from a completed staged wave. It reuses existing cleaning, exact reviewed
overrides, company resolution, nutrition flags and ingredient-analysis rules.
Stages 02 and 04 accept an explicit in-memory input; Stage 03 accepts retained
peer context for incoming within-brand warnings. Their default file-based paths
and governance definitions remain unchanged.

The adapter preserves string identifiers and original staged source evidence.
Missing source columns and records without both name and ingredients are held
with reasons. New candidates outside final governed scope are held; retained
scope exits are written and remain retained. Incoming nutrition warnings use
unchanged retained peers plus incoming records, rather than only the delta.
Unchanged peer rows are not rewritten.

Only ingredient-derived analysis fields are replaced. Ineligible ingredient
analysis clears those fields explicitly; pack observations and their metadata
are preserved, not certified fresh. Empty or entirely held batches are handled
without running the ingredient analyzer on an empty denominator.

Each copy retains `governed_processing/prepared.json` with source, rule,
reference-input and retained-context identities, explicit holds and the exact
processed batch. The transactional writer rechecks these identities under its
write lock before committing product/analysis history, current rows, admissions
and completion together. Exact replay is a no-op; interrupted report writing
can be recovered by replay. Changed inputs or rules require a fresh copy.

```text
python -B pipeline/maintenance/connect_governed_wave.py --database <staged-copy-trial.db> --wave-id <completed-wave-id>
python -B pipeline/validation/check_10_governed_ingestion.py
python -B pipeline/validation/check_10_governed_ingestion.py --full-size-policy-trial <completed-policy-trial-directory>
```

The connection report is separate from the earlier immutable staging report.
It does not rebuild aggregates, certify claim freshness or publish a deployment.

Validation passed: ten integration tests, writer/cutoff regression checks and
the existing nutrition checks. The full-size synthetic copy trial at
`data/06_brand_governance_outputs/incremental_ingestion_trials/governed_validation_20261017T101538_380792Z/`
accepted a retained update, retained scope exit and new product, held an empty
record and excluded a post-cutoff record. History, pack preservation, exact
replay byte identity, unaffected auxiliary tables, SQLite integrity/foreign keys
and protected-file identities passed. Production and frozen evidence are unchanged.

## Downstream release and claim freshness (17 October 2026)

`pipeline/maintenance/build_incremental_release.py` builds a new local release
candidate from one completed governed ingestion copy. It never publishes over
production. The source copy and saved extraction evidence must remain unchanged.
A release manifest distinguishes the September reporting cutoff from actual
retrieval time. Partial builds have no completed manifest and are not usable by
the app. The legacy Stage 17 entry point refuses governed copies.

Stages 12-16 consume explicit retained display membership on this path, including
unchanged products. Nutrition benchmarks, intersections and chart ranges share
the Product Explorer hard gate and normalized-brand eligibility. Category-region
averages and reporting tables are rebuilt from that population. The candidate
contains retained deployment products and an explicit display population; app
queries use that membership instead of the newest product load timestamp.
Legacy app databases continue to use their existing latest-load selection.

Reporting uses the proxy cutoff, not the build date. OFF-new-record counts accept
cleaned ISO dates and legacy epochs and exclude creations after that cutoff.
These are OFF record creations, not product launches. Historical summary rows
are preserved in the working release copy, but changing the reporting population
creates a comparability break; old rows are not retrospectively restated.

Claim freshness is evaluated against original `vision_results*.csv` evidence,
excluding checkpoint files and merged reports. Merged reports can replace the
actual prompt inputs with later database metadata. Matches require barcode, extraction timestamp,
prompt version and stored claims JSON, with successful completed extraction.
A matching revision-bearing OFF front-image URL and unchanged product-name and
brand context permit `matched_image_reference`. This means matching reference,
not a fresh download or byte-for-byte verification of the remote image.
Context uses `primary_brand`, which Stage 10 supplied to the prompt, rather than
the broader raw brand list. Approved UK rules use this name/brand text as well as OCR.
Nutrition-only edits do not invalidate the image evidence.

Changed image references or text context, missing provenance, conflicting
provenance and unversioned image URLs have separate statuses. A failed attempt
cannot certify an older claim result. Missing analysis is distinct from a
successful analysis with no claims. No OCR/LLM requests are made by this check.

The unchanged source preserves all original evidence. The derived working copy
also stores each prior analysis in `claim_freshness.prior_analysis_json`, together
with matched file references and checksums. Unverified pack results are masked
from current release calculations and display; ingredient-only taxonomy remains
a separate evidence layer. Existing private-label presentation files are untouched.
The public candidate carries only freshness status, not private audit payloads.

```text
python -B pipeline/validation/check_11_incremental_release.py
python -B pipeline/maintenance/build_incremental_release.py --database <completed-copy-trial.db> --output data/06_brand_governance_outputs/incremental_ingestion_trials/<new-release-directory> --evidence-dir data/05_vision_release
```

The manual paid sampling/extraction branch is not run by this release builder.
New OCR/LLM runs still need evidence-version-aware sampling and merge handling;
the legacy barcode-only checkpoint/merge path must not be used to refresh this
candidate without that separate work.

### Completed real September proxy release — 18 October 2026

The October 17 OFF retrieval was processed from eligible staged observations
into the guarded copy at
`data/06_brand_governance_outputs/incremental_ingestion_trials/live_proxy_stage_20261017T153127Z_v3/`.
Its governed report records 148,366 accepted writes and 4,657 explicit holds;
the batch, history and admissions are preserved there. The original raw export,
August baseline and working production database were not overwritten.

The downstream candidate at
`data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/`
completed with 522,432 retained deployment products and 360,118
display-eligible products. Its September 29 reporting date and actual October 17
retrieval timestamp are separate fields. It contains 12 region-category
benchmark rows, 3,324 profile-intersection rows and 216 chart-range rows.
Source and protected-file hashes, SQLite integrity and foreign keys, one
completed-release selection, and benchmark/app population counts passed.

The claim-freshness audit recorded 6,649 matching image references, 12,765
observations with unknown image provenance, 27 with unknown text context and
one with unknown attempt provenance. A further 507,759 products have no stored
pack observation. These statuses concern traceability of saved pack evidence;
they do not undo the approved UK contextual origin and free-from rules. Current
release outputs mask unverifiable pack observations while preserving their
earlier analysis in the audit copy. No paid OCR/LLM run was made.
