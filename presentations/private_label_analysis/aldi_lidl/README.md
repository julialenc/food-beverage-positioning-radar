# Aldi/Lidl analysis evidence

Review checkpoint: 2026-10-15. Source: Open Food Facts-derived local exports,
supplemented for qualitative illustration with retailer information. Julia Lenc
reviewed the four product-specific territory decisions.

## Release status

`aldi_lidl_architecture.pdf` is the original presentation, moved without content
changes. It awaits Julia's revision. The reviewed aggregate evidence differs in
four Plant-based / vegan cells; it must not be described as an exact reproduction
of that PDF. The PDF's original SHA-256 is retained in the manifest and aggregate.

| Scope | Original PDF | Code-only count / claim-bearing base | Reviewed count / base | Reviewed share |
|---|---:|---:|---:|---:|
| Aldi / France | 10% | 7 / 67 | 8 / 67 | 12% |
| Aldi / UK_IE | 5% | 8 / 128 | 8 / 128 | 6% |
| Aldi / US_CANADA | 6% | 8 / 129 | 9 / 129 | 7% |
| Lidl / UK_IE | 9% | 12 / 132 | 13 / 132 | 10% |

The brownies' originally empty territory is manually overridden to vegan. Its
original claim codes already support that classification, so it adds no record
beyond the code-only calculation. Three plant drinks have confirmed contextual
vegan classifications based on their identity and dairy-free claim, adding one
record each beyond explicit code detection. All four decisions are scoped to
retailer, region, category and GTIN in `reviewed_territory_decisions.csv`.
The original codes and historical derived columns remain unchanged.

Other limitations: the Harvest Morn Cookie Dough Bar illustration came from the
Aldi UK website, not these CSVs; the original URL/access date has not been
recovered. Julia plans to revise the broad sugars comparison. Dairy assortment
mix evidence is strongest in France; small Lidl US/Canada samples do not support
equally strong conclusions in every scope. See OBS-025 for the review record.

## Files and retention

| Location | Purpose | Intended publication |
|---|---|---|
| `aldi_lidl_architecture.pdf` | Original publicly shared presentation, with unresolved differences documented above | GitHub candidate; not yet reconciled with reviewed evidence |
| `aldi_lidl_claims_denominator_check.csv` | 78 territory cells, original codes, reviewed additions, both denominators, original PDF comparison | GitHub candidate |
| `aldi_lidl_claims_denominator_summary.csv` | Six regional and two pooled scope counts, incidence, original-tag stacking | GitHub candidate |
| `reviewed_territory_decisions.csv` | Four exact reviewed decisions, reason, reviewer, original state | GitHub candidate |
| `snapshot_manifest.json` | Original hashes and cleanup disposition; hash capture is not proof of historical creation date | GitHub candidate |
| `source_snapshots/` | Five unchanged historical product-level inputs | Local only |
| `archive/` | Five unchanged exploratory/audit exports | Local only |

Source snapshots:

- `aldi_products_full_macro_positioning_details.csv`: 4,104 records; core input.
- `lidl_products_full_macro_positioning_details.csv`: 5,893 records; core input.
- `conclusion_02_aldi_positioning_evidence.csv`: 895 analyzed Aldi records;
  historical derived territory fields retained, including the empty brownies field.
- `conclusion_03_lidl_positioning_evidence.csv`: 778 analyzed Lidl records;
  historical derived territory fields retained.
- `aldi_lidl_dairies_subtype.csv`: 3,818 dairy records, subtype interpretation and
  two review flags; supporting mix investigation, not new production exclusions.

Archives:

- `lidl_products_macro_positioning.csv`: earlier claims snapshot, only 431
  analyzed records; same non-claim projection as the fuller export.
- `aldi_products_investigation_details.csv`: 122 selected investigation records;
  still the selection input for the optional Aldi refresh script.
- `lidl_products_investigation_details.csv`: 135 investigation records; one older
  positioning status; not a complete claims population.
- `retailer_brand_protein_levels_by_region_category.csv`: exploratory brand-level
  statistics using strictly positive protein; not the slide's category medians.
- `selected_retailer_products_protein_pull.csv`: 425 selected products across
  retailers; exploratory history, not a complete analytical population.

`aldi_products_macro_positioning.csv` was removed only after confirming that
all its rows and 15 columns are preserved in the full Aldi export. Its original
hash is recorded in the manifest. The refresh script no longer generates it.

## Claim rules: reconstructed and reviewed, version 2026-10-15_reviewed_v1

| Territory | Original claim codes counted (union, once per product) |
|---|---|
| Protein | `protein_claim` |
| Fibre / wholegrain | `fibre_claim`, `whole_grain_claim` |
| Fortification | `fortification_claim` |
| Energy | `energy_claim` |
| Gut health | `gut_health_claim`, `prebiotic_claim`, `probiotic_claim` |
| Immune | `immune_claim` |
| Sugar / fat reduction | `sugar_free_claim`, `reduced_sugar`, `reduced_fat_claim` |
| Free-from (gluten / lactose / dairy) | `gluten_free_claim`, `lactose_free_claim`, `dairy_free_claim` |
| Organic / natural | `organic_claim`, `natural_claim` |
| Origin / provenance / quality | `origin_quality_claim`, `heritage_claim`, `artisan_claim` |
| Clean label / no-additives | `clean_label_claim`, `no_artificial`, `no_palm_oil` |
| Plant-based / vegan | `plant_based_claim`, `vegan_claim`, plus the separately identified reviewed contextual decisions |
| Sustainability | `sustainability_halo` |

This mapping reconstructs 77 of the 78 original slide-4 percentages before the
contextual additions. Aldi UK Plant-based / vegan is the remaining cell: original
claim codes give 8/128, while the old derived territory field missed the brownies.
The original generation script is not retained. These rules are explicit new
reconstruction rules, not a claim to have recovered the original prompt/code.
Do not substitute the later US mappings that also include `vitalite_concept` in
Energy or `comparative_claim` in Reduction.

`NOT_ANALYZED` is excluded from analysis denominators. `NO_CLAIM_IDENTIFIED`
counts as analyzed, but not claim-bearing. Unexpected blanks fail validation.
No image validity is reassessed here: these exports carry the retained analysis
status, and this reconstruction does not independently re-audit pack images.

Claim incidence = claim-bearing / analyzed. Territory share = territory-bearing
/ claim-bearing. A product may appear in several territories; shares need not sum
to 100%. Stacking = at least two distinct original claim codes / claim-bearing.
Manual territories do not create new extracted codes or change stacking.

The check exposes code-only counts, contextual additions, reviewed counts,
percentages with both denominators, reviewed GTINs and source/review hashes.
The columns named `pct_among_claimed_products_*` use reviewed counts; use
`pct_code_only_among_claimed_products_exact` for explicit detection alone.
Decimal division is retained to 28 significant digits; displayed percentages
use half-up rounding. A zero denominator produces an empty percentage, not zero.

The two `ALL_REGIONS_RECORDS` summary rows reproduce the original pooled headline
incidence. They count regional records, not globally deduplicated GTINs; one GTIN
may occur in multiple regions. Territory comparisons remain within region.

## Rebuild and validate

From the repository root:

```powershell
python -B pipeline/exports/export_aldi_lidl_claims_evidence.py --check
```

Without `--check`, missing outputs are created. Existing identical outputs are
accepted; differing outputs are refused and require explicit review. The script
checks frozen input hashes and the original states of reviewed records. It uses
no live database, network calls, LLM, or current website data. A public checkout
without the local-only source snapshots cannot rerun this reconstruction; the
aggregate arithmetic and decisions remain publicly inspectable when published.

Database refreshes are separate from this evidence:

```powershell
python pipeline/maintenance/refresh_aldi_private_label_analysis_exports.py --output-dir data/06_brand_governance_outputs/private_label_refresh_YYYYMMDD
python pipeline/maintenance/expand_private_label_macro_benchmarks.py --output data/06_brand_governance_outputs/private_label_refresh_YYYYMMDD/nutrition_values_vs_market_median_all_retailers.csv
```

Choose a new run path. Both commands reject outputs inside the retained analysis
tree and refuse existing destinations. The benchmark command preserves the
retained regional baseline and recalculates company rows from the selected DB;
it does not recreate the regional baseline from scratch. No database refresh was
run during cleanup.

The repository's explicit Git allowlist exposes this guide, the PDF, the two
aggregate CSVs, reviewed decisions and snapshot manifest. `source_snapshots/`
and `archive/` remain ignored and local-only. Do not force-add those folders.
No publication is performed by the migration; the original PDF still awaits
Julia's revision and alignment with the reviewed evidence.
