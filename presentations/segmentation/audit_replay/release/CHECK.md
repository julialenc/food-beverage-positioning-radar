# Release candidate and isolated replay — CHECK

**PASS — steps 5 and 6 complete locally, 22 November 2026.**

## Candidate

The distribution comprises 340 hashed files plus its manifest (341 total), 695.87 MiB. It exports the 278 tracked source files at 015f3a6d329a30cd7e562140137243111fb8d719 and adds the declared data/contracts, human-source archive, replay tooling, dependency pins and database parts. Existing tracked files match their Git identities: zero changed existing files. PROPOSED_FILES.md lists 63 additions including the manifest. Local review reports are separate from that declared distribution.

The 3.44 GiB database is stored as four compressed parts (90, 90, 90 and approximately 47 MiB). Each distributed file is below 100 MiB. Database restoration matched its original SHA-256 before analysis. The accepted master remains one ordinary 75.96 MiB file. Both human submissions and provenance are bundled and hashed.

## Independent test

The runner verified all candidate file hashes, copied only the declared package into a fresh workspace, restored the database from its parts, and ran all 25 stages. It did not use Git, original local data, older computation checkpoints or the earlier replay workspace during scientific execution. All analytical stages computed afresh. Workers denied original-workspace reads, network/provider use, external writes and subprocess calls; synthetic probes verified the guards and all actual violation counters are zero.

The first environment guard self-check exposed a layout assumption before any analysis ran. The harness was corrected, candidate hashes updated and the revision recorded; the failed guard log remains retained. There were no subsequent scientific-stage failures. Python audit hooks are regression controls, not an operating-system hostile-code boundary.

All six final data tables and the freshly rebuilt master match accepted bytes exactly. The independent verifier passed, including 393 cohort key sets, 15 regional profile cells, 13,602 communication coverage cells, 12 human observations, 32,336 boundary annotations and unknown/zero guards. The report check covered 63 table instances.

Small q-value differences and the already documented metadata exception for three ambiguous-composition groups remain explicitly recorded. No statistical decisions or findings changed. Candidate findings differ only by the declared status and two tiny inherited q values. Neither historical data nor generated values were overwritten to force equivalence.

The original 72 pinned files were independently rehashed after completion and remain unchanged. The frozen verifier was also rerun separately; its console result is retained in frozen-integrity.log.

## Scope and limits

This is an offline segmentation replay from the dated governed database and saved provider/human observations. Timestamped OFF downloads are not redownloaded, provider decisions and human judgments are not regenerated, and no provider calls occur. No website runtime or test copy is involved.

The test reused the exact declared Python environment; it does not certify a new dependency installation. This proves a complete standalone candidate, not an already published GitHub clone. Publication layout, byte-preserving Git attributes/ignore rules, scope, version and notes remain the next review step (see GIT_INTEGRATION.md). The eventual published tag/archive requires its final download check.

No commit, push, tag, publication or frozen-package modification occurred.

## Stage results

| Stage | Result | Seconds |
|---|---|---:|
| environment | PASS | 7.37 |
| master | PASS | 279.13 |
| inventory | PASS | 6.05 |
| cereal | PASS | 13.91 |
| baseline | PASS | 65.9 |
| features | PASS | 39.74 |
| ingredients | PASS | 24.01 |
| hypotheses | PASS | 376.96 |
| control | PASS | 128.9 |
| cereal_followup | PASS | 19.91 |
| snacks | PASS | 69.02 |
| beverages | PASS | 131.02 |
| juice | PASS | 36.16 |
| dairy | PASS | 26.24 |
| biscuits | PASS | 32.66 |
| human | PASS | 3.93 |
| synthesis | PASS | 29.43 |
| coverage | PASS | 118.13 |
| overlays | PASS | 13.78 |
| backlog | PASS | 77.55 |
| processing | PASS | 84.58 |
| juice_sensitivity | PASS | 5.65 |
| research_validation | PASS | 5.04 |
| report_tables | PASS | 3.45 |
| package | PASS | 278.08 |

Authoritative machine results: VALIDATION.json here and results.json, config.json, per-stage logs/results and runner revisions in the sibling segmentation_candidate_isolation_v1 workspace.
