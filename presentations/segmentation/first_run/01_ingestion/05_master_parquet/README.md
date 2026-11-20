# Wave 2 master product Parquet

The local `output/master_products.parquet` contains 382,527 unique barcode/region/category assignments from 374,840 governed products. Country assignments within a region are retained in the assignment_countries list. All governed product columns, including raw nutrients, brand layers, quality flags and source tags, are preserved. The locked claim fields have a claims_ prefix. Of 12,161 matches, two are analytically excluded. The 370,366 unmatched rows retain nulls throughout the claims namespace.

For population analyses, apply product_scope_eligible and the analysis-specific scope. For claim analyses additionally require claims_matched and claims_analytical_eligible, and use the individual flag's nullable assessment as its denominator. The master includes US/CA dairy; the original main-sample dairy hold remains a separate sampling decision. Original nutrition and image-selection QA observations remain preserved; completed analytical decisions are documented in the public research audit. These historical flags do not reopen ingestion. No final segment labels are assigned by the master.

From the repository root, run the script below to reproduce to a new directory. Without an output argument, it publishes to output/ and refuses to replace an existing release.

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/01_ingestion/05_master_parquet/build.py --output <new-directory>
```

The builder uses the corrected Wave 2 database when its manifest is present; the historical fallback checks the original RUN 01 database hash. It validates the governed release contract, cutoff, retrieval and population. The other OFF snapshots are independent releases. The [output manifest](output/manifest.json) records the source, claims and reviewed-rule hashes.

The current output replaces the pre-correction master following OBS-028 on 14 November 2026. Its source is the corrected Wave 2 work database under data/06_brand_governance_outputs/wave2_identity_fix_v1/. The original ingestion release and frozen sampling/claims observations provide historical evidence. Current reporting and analysis use the corrected release and this replaced master. Claims provenance includes the original barcode and category; four joins follow existing reviewed category corrections.

## Publication and dependencies

The master Parquet remains local; the builder, this guide and output manifest are public. See [the consolidated ingestion guide](../README.md#executable-dependencies-and-restoration-contract) for the unchanged shared production modules, reference inputs, original-source archive and local restoration contract. The [isolated smoke test](../../README.md#smoke-test) regenerated this master byte-for-byte from published code and restored inputs. Restore the approved `barcode_aliases.csv` alongside the corrected source database and manifest; its exact hash and the package-stage low-memory settings are recorded in that CHECK summary. These documentation changes do not rebuild or replace the accepted master.
