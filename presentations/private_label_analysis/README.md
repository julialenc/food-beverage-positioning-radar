# Private-label analysis evidence

This folder contains four analyses already shared publicly and their retained
evidence. GitHub publication of this organized collection is still a separate step.
It is a standalone business-analysis collection, independent of Streamlit.
The architecture conclusions are qualitative, reviewed interpretations; product
counts describe observed OFF records, not market share or sales.

| Analysis | Presentation | Composition evidence | Claims evidence |
|---|---|---|---|
| Aldi / Lidl | `aldi_lidl/aldi_lidl_architecture.pdf` | Shared benchmark below | `aldi_lidl/aldi_lidl_claims_denominator_check.csv` and `aldi_lidl_claims_denominator_summary.csv` |
| France | `mainstream_france_retailers/private_labels_france_top 5_retailers.pdf` | Shared benchmark below | `france_claims_slide_denominator_check_20260920.csv` and matching summary in that folder |
| UK | `mainstream_uk_ie_retailers/private_labels_uk_top_5_retailers.pdf` | Shared benchmark below | `uk_claims_slide_denominator_check_20260920.csv` and matching summary in that folder |
| US / Canada | `mainstream_us_canada_retailers/private_labels_us_top 5_retailers.pdf` | Shared benchmark below | `us_canada_claims_denominator_check_20260920.csv` and matching summary in that folder |

`nutrition_values_vs_market_median_all_retailers.csv` is the shared composition
benchmark. It contains regional-category and retailer-category medians; do not
recalculate a category median from brand medians. Its original data is unchanged. A fresh retailer refresh retains the regional
baseline and writes to a separate output; it does not recreate that baseline.

The three mainstream folders were not reorganized in the Aldi/Lidl cleanup.
The France PDF's historical filename is retained; its name alone does not define
the six-retailer analytical scope.

## Scope and claims evidence

France covers six mainstream retailers, UK five and US five, alongside the
separate Aldi/Lidl analysis. The data scopes remain FRANCE, UK_IE and US_CANADA.
The working database's expanded 23,403 vision observations describe overall
coverage, not the denominator of each frozen presentation table.

The latest UK method includes approved text rescues for "free from" branding
and origin wording, using product-name, brand and OCR text. The UK check CSV
retains both the requested claim-bearing denominator and the all-analyzed
denominator used by its slide-comparison column. Read those columns explicitly;
do not assume every PDF uses the same denominator. The UK check records 64/65
rounded slide matches to the all-analyzed base. Asda Sugar / fat reduction is
12% on the recorded slide comparison versus 29/256 = 11.328125% (11% rounded);
this existing discrepancy remains unresolved. Final evidence takes
precedence over incomplete historical onboarding notes. See the
[extraction guide](../../docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md)
and [limitations](../../docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md#standalone-private-label-presentations).

## Aldi/Lidl organization

See [the Aldi/Lidl guide](aldi_lidl/README.md) for the rule mapping, manual review,
historical input inventory, reproducibility command, and PDF differences.

The root now holds shared evidence; Aldi/Lidl-specific material lives under
`aldi_lidl/`. Historical source snapshots and exploratory files are local-only.
They should not be overwritten by fresh database exports.

## Publication status

The four PDFs, shared composition benchmark, validated aggregate evidence and
explanatory documentation are intended GitHub candidates. Product-level CSV
exports and exploratory/audit archives remain local-only.

An explicit `.gitignore` allowlist exposes the four PDFs, shared benchmark,
eight aggregate claims CSVs, reviewed territory decisions, snapshot manifest
and the two analysis guides. All other files in this analysis tree are ignored,
including product-level exports, source snapshots and archives. New files require
an intentional allowlist update before publication. Do not force-add this folder.
The migration itself does not stage, commit or push any files.
The Aldi/Lidl PDF still needs Julia's planned revision before it can be described
as aligned with the newly reviewed aggregate evidence.

Methodology: [project methodology](../../docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md).
Manual review: [OBS-025](../../docs/03_PROJECT_REFERENCE/05_OBSERVATIONS.md#obs-025---aldilidl-territory-decisions-and-retained-publication-evidence).
