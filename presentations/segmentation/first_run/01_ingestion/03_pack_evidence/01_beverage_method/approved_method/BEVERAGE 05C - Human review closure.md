# BEVERAGE 05C — Human review closure

**Date:** 24 October 2026. **Status:** Julia's five manual decisions recorded; the 47-case register is frozen for review. No operational shortlist change has been made.

## Decision record

Julia reviewed the five `borderline_for_julia_review = YES` cases in `C:\Users\julia\OneDrive\Desktop\beverage_05c_coconut_decisions.xlsx` and confirmed **EXCLUDE — non-beverage** for all five. Four are cooking ingredients; the Savoy coconut cream is a dessert/cooking ingredient. The exact reviewer wording below is preserved, including its original spelling.

| Exact frozen GTIN | Region / role | Julia's original note | Registered status |
|---|---|---|---|
| `3760198300821` | FR / reserve | `NOT BEVERAGE - pack says it can be added to sauces or meals` | EXCLUDE — human approved |
| `5018922117718` | UK+IE / selected | `NOT BEVERAGE - I checked GTIN, it's cooking ingredient` | EXCLUDE — human approved |
| `737628082506` | US+CA / reserve | `NOT BEVERAGE - cooking ongredient for Thai cuisine` | EXCLUDE — human approved |
| `0854134004003` | US+CA / selected | `NOT BEVERAGE - cooking ingredient` | EXCLUDE — human approved |
| `16229004019` | US+CA / selected | `NOT BEVERAGE - coconut cream (dessert)` | EXCLUDE — human approved |

These are Julia's human-reviewed decisions, not conclusions from a new Codex image assessment. The prior BEVERAGE 05C report, image evidence and original Codex rationale remain preserved.

## Frozen 47-case register

The [human-reviewed decision register](beverage_05c_coconut_decisions_human_reviewed.csv) has **exactly 47 rows**. It carries forward the frozen BEVERAGE 05C product, region, role, group, source URL, category and image-evidence fields and keeps the earlier Codex proposal separate from the new final classification and approval status. `human_review_note_original` preserves Julia's text verbatim; `human_review_source_row`, workbook path and workbook SHA256 provide approval provenance. `operationally_applied` is `NO` for every row.

| Final disposition / approval | Selected | Reserve | Total |
|---|---:|---:|---:|
| EXCLUDE — human approved | 3 | 2 | 5 |
| EXCLUDE — proposed by Codex, pending case-specific approval | 2 | 0 | 2 |
| RETAIN — proposed by Codex, pending case-specific approval | 1 | 0 | 1 |
| HOLD — intended use unresolved | 32 | 7 | 39 |
| **Total** | **38** | **9** | **47** |

The two Codex exclusion proposals (`5010338014964`, `0016229005122`) and one retention proposal (`0016229005474`) remain **unapproved**. All 39 other products remain HOLD. No HOLD was converted based on the workbook's blank approval cells.

### Identity reconciliation

The workbook has 47 product rows, five flagged rows and five filled reviewer notes. Excel stored some barcode fields numerically. For example, its `854134004003` cell corresponds to the frozen exact GTIN `0854134004003`; the final register uses the latter. Each workbook row was matched to the frozen BEVERAGE 05C/05B evidence using **original product URL + region + selected/reserve role + cached-image SHA256**, then cross-checked against product name, approved group, country cell, original image URL and cached-image path. The numeric workbook barcode was never used to construct or repair a GTIN. Zero-padded source-URL equivalents remain recorded as provenance, not replacements for the exact frozen barcode.

## Hypothetical RUN 06B quota impact — not implemented

RUN 06B v2 still has **63 unfilled project slots**: 37 beverages and 26 other categories. Of Julia's five approved coconut exclusions, **three are selected** and **two are reserves**. No reserve is promoted and the frozen selected/reserve files are unchanged.

| Scenario | Additional selected losses | Beverage slots to fill incl. existing 37 | Project shortfall without replacement | Maximum same-cell/component capacity from current unflagged beverage reserves | Project gaps after hypothetical capacity |
|---|---:|---:|---:|---:|---:|
| Five human-approved exclusions only, if operationally applied later | 3 | 40 | 66 | 2 | 64 |
| Those five plus both Codex exclusion proposals, **only if separately approved later** | 5 | 42 | 68 | 3 | 65 |

Capacity uses only the **580 beverage reserves without any BEVERAGE 05A suspicion flag** and matches the exact approved group, country cell and sampling component. The 13 suspected reserves, including Julia's two excluded reserves, are not credited. These are sensitivity calculations, not executable replacement plans; technical reserve availability does not establish image usability or paid-run readiness.

## Freeze and verification

| Input or output | SHA256 |
|---|---|
| Julia's reviewed Excel workbook | `e04f97c0facec2beced5a7fb06e4a08b862a1de40e72ab7b2618c2cad57ae94e` |
| Frozen BEVERAGE 05C proposed register | `f9206f2ed5bdd5468b890742fb92f23bfb50248805ea80082a238d83026c519b` |
| Frozen BEVERAGE 05B register | `c47bb949f24b5748e3c90c078dc3d68bbebad7dfd6a288d108962c33283083c5` |
| New human-reviewed 47-case register | `9dd5a092c13fa47e1c5dcd474f55c104797ce65523be0f2968f9c5f5ae8a662e` |

Validation confirmed 47 unique exact GTIN–region pairs, all five human notes matched to the flagged source rows, source identity/evidence fields preserved, and disposition/role counts reconciled. The frozen RUN 06B selected and reserve manifest hashes remain `ce98cbb88120543819756459c253d56d69bc71abd3deb5271ce24e1eddcacdbb` and `753ce5b29e599e50e37c4f4a0a522d37a9c81cc3015312839f5c3ff67b6a6d89`.

**STOP.** No exclusions or holds have been applied to RUN 06B or source data; no reserve promotion, sample redraw, image download or OCR/LLM call occurred.

The earlier proposal covered 47 coconut holds from the 05B register. Cached images and OFF categories alone could not establish pack identity. Its scope excluded the other 74 cases.
