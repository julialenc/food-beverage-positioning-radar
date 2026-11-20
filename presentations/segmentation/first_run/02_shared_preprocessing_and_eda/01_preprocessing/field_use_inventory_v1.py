"""Fresh field-use baseline from the corrected Wave 2 master; inventory only."""
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent
RELEASE = HERE.parents[1] / "01_ingestion/05_master_parquet/output"
NUTRIENTS = "energy_kcal sugars_100g protein_100g fiber_100g fat_100g saturated_fat_100g carbs_100g salt_100g".split()
CLAIMS = (
    "protein_claim sugar_free_claim reduced_sugar no_palm_oil no_artificial natural_claim fortification_claim "
    "fibre_claim gut_health_claim probiotic_claim prebiotic_claim immune_claim energy_claim sleep_claim "
    "brain_health_claim vitalite_concept sustainability_halo reformulation_claim comparative_claim "
    "glp1_positioning origin_quality_claim clean_label_claim minimal_ingredients_claim artisan_claim vegan_claim "
    "organic_claim dairy_free_claim lactose_free_claim plant_based_claim heritage_claim gluten_free_claim "
    "gender_targeting_claim reduced_fat_claim whole_grain_claim"
).split()
LENSES = {
    "1": "Nutritional composition", "2": "Nutrient density",
    "3": "Claims, composition and ingredients", "4": "Positioning trade-offs",
    "5": "Unsupervised control",
}


def inventory(schema):
    groups = []
    assigned = set()

    def group(purpose, fields, lens_use, disposition):
        if isinstance(fields, str):
            fields = fields.split()
        overlap = assigned.intersection(fields)
        if overlap:
            raise ValueError(f"Fields assigned twice: {overlap}")
        groups.append(dict(purpose=purpose, lens_use=lens_use, disposition=disposition,
                           fields={field: str(schema.field(field).type) for field in fields}))
        assigned.update(fields)

    group("Assignment identity and geography", "barcode region category assignment_countries",
          "1–5: define units, regional/category comparisons and traceability; H12 across lenses.",
          "Keep in every analytical extract. Preserve barcode strings and country lists.")
    group("Product scope and reviewed decisions",
          "product_scope_eligible include_in_product_table reviewed_nutrition_category_decision reviewed_beverage_status",
          "1–5: establish product scope before lens-specific eligibility.",
          "Use existing decisions and retain their reasons.")
    group("Peer-format evidence", "off_categories product_name query_category",
          "1: H2 cereal peers; 2–4: comparable formats where relevant; 5: interpret format effects.",
          "Inspect cereal tags and names when defining H2. Format assignments remain open.")
    group("Working nutrient measurements", NUTRIENTS,
          "1: composition; 2: energy, protein and fibre; 3: claim contrasts; 4: trade-offs; 5: candidate inputs.",
          "Inventory availability. Select measurements separately for each question.")
    group("Preserved nutrient values and missing flags",
          [n + suffix for n in NUTRIENTS for suffix in ("_off_raw", "_missing")],
          "1–5: trace any selected measurement and investigate missingness.",
          "Keep as audit fields. Trace energy and sugars flags in the next review.")
    group("Nutrition warnings and reasons",
          "nutrition_quality_status outlier_type nutrition_quality_reason warning_flag warning_types warning_summary",
          "1–5: interpret flagged records when selected measurements are used.",
          "Retain for QA. Decide any treatment in the relevant analysis.")
    group("Source country and region descriptors", "countries primary_country observed_market_region_codes",
          "1–5: consult when an assignment needs explanation.",
          "Defer normalization. Use governed region and assignment_countries for grouping.")
    group("Ingredient evidence", "ingredients_text ingredients_lang ingredient_analysis_eligible additives_tags",
          "3: conditional H7; 4: only for a specified ingredient trade-off.",
          "Defer parsing and language-specific cleaning until H7 feasibility review.")
    group("Processing classification", "nova_group",
          "4: H9/H10 if the specified trade-off involves processing.",
          "Defer coverage and interpretation until that comparison is chosen.")
    group("Brand and company layers",
          "brands primary_brand off_brands_raw off_brand_tokens legacy_primary_brand brand_entity_raw brand_entity_source "
          "normalized_brand brand_alias_source brand_alias_review_status resolved_company brand_family "
          "company_ownership_resolution_status company_mapping_source",
          "3: optional profiling of brand-related communication under H6.",
          "Defer. Preserve existing governed layers.")
    group("Other source descriptors", "quantity packaging labels nutriscore_grade completeness_score",
          "No current hypothesis requires these fields. An OFF label tag has a different source from reviewed pack evidence.",
          "Defer. Package quantity alone does not establish serving size or preparation basis.")
    group("Reporting controls", "include_in_aggregates include_in_charts",
          "No analytical lens requires reporting display controls as inputs.",
          "Retain for reporting lineage.")
    group("Source timestamps and image pointer", "created_t last_modified_t ingested_at image_url",
          "1–5: provenance if a record needs investigation.",
          "Defer reprocessing. Use the release manifest for wave identity.")
    group("Claim sample, eligibility and cohort",
          "claims_matched claims_analytical_eligible claims_eligibility_reason claims_evidence_cohort "
          "claims_source_country_assignments claims_source_market_limitation",
          "3: claim denominator; 4: denominator for comparisons using pack propositions.",
          "Apply both eligibility gates and claim-specific assessment. Keep historical reuses identifiable.")
    group("Claim evidence, assessment context and QA",
          "claims_record_id claims_product_name claims_image_url claims_original_overall_outcome "
          "claims_core_claim_evidence_json claims_source_references claims_source_barcode claims_source_category claims_core_assessment_context "
          "claims_core_assessment_quality claims_core_assessment_status claims_nutrition_qa_hold claims_population_qa_note",
          "3–4: trace pack assessments. Consult dairy QA notes when a nutrition or population question touches those cases.",
          "Retain evidence and QA context. Defer OCR text processing and detailed exceptions.")
    group("Core pack propositions and evidence states",
          [f"claims_{kind}_{claim}" for claim in CLAIMS for kind in ("claim", "state", "basis")],
          "3: H5–H7; 4: H9–H11 when communication is part of the hypothesis.",
          "Select propositions individually with their state and basis. Preserve unknowns. Use the locked energy-positioning indicator for H8.")
    group("Communicated nutrient amounts and fortification",
          "claims_protein_amount_g claims_protein_amount_basis claims_protein_amount_provenance "
          "claims_fortification_nutrients_json claims_fortification_meaning",
          "3: H5 where a pack amount or fortification wording matters; 4: conditional context.",
          "Defer until needed. Keep amount basis and provenance with the claim.")
    group("Beverage energy positioning", "claims_energy_drink_membership claims_energy_drink_format "
          "claims_energy_positioning claims_energy_positioning_basis claims_original_energy_claim",
          "3: H8 energy positioning and format; 4: conditional on a beverage trade-off.",
          "Use the locked derived indicator. Recorded kcal measures composition.")
    group("Beverage hydration and electrolyte positioning",
          "claims_v6_disposition claims_v6_usable claims_hydration_content_status claims_hydration_front_status "
          "claims_hydration_positioning claims_electrolyte_content_status claims_electrolyte_front_status "
          "claims_electrolyte_positioning",
          "3: H8 benefits have separate assessments; 4: conditional on a beverage trade-off.",
          "Retain independent v6 usability and front/content uncertainty.")
    if assigned != set(schema.names) or len(assigned) != len(schema):
        raise ValueError(f"Schema coverage mismatch: {set(schema.names) - assigned}")
    return groups


def summarize(rows):
    eligible = rows[rows.product_scope_eligible]
    matched = eligible[eligible.claims_matched & eligible.claims_analytical_eligible.eq(True)]
    new = matched[matched.claims_evidence_cohort.eq("new_processed")]
    historical = matched[matched.claims_evidence_cohort.eq("historical_dairy_reuse")]
    if len(new) + len(historical) != len(matched):
        raise ValueError("Unclassified evidence cohort")

    def protein_states(cohort):
        claim = cohort.claims_claim_protein_claim
        return dict(detected=int(claim.eq(True).sum()), documented_negative=int(claim.eq(False).sum()),
                    unknown=int(claim.isna().sum()))

    return dict(master_assignments=len(rows), product_scope_eligible=len(eligible),
                nutrient_non_null={n: int(eligible[n].count()) for n in NUTRIENTS},
                claims_matched_all=int(rows.claims_matched.sum()),
                claims_jointly_eligible=len(matched),
                protein_claim_by_cohort={"new_processed": protein_states(new),
                                         "historical_dairy_reuse": protein_states(historical)})


def build():
    manifest = json.loads((RELEASE / "manifest.json").read_bytes())
    master = RELEASE / "master_products.parquet"
    with master.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if (sha != manifest["master_sha256"]
            or manifest["release"]["wave_id"] != "real_off_20261017_proxy_20260929"
            or manifest["release"]["reporting_date"] != "2026-09-29"
            or not manifest["release"]["retrieved_at"].startswith("2026-10-17")):
        raise ValueError("Expected the verified Wave 2 master")
    with pq.ParquetFile(master) as parquet:
        groups = inventory(parquet.schema_arrow)
        columns = ["region", "category", "product_scope_eligible", "claims_matched",
                   "claims_analytical_eligible", "claims_evidence_cohort", "claims_claim_protein_claim", *NUTRIENTS]
        rows = parquet.read(columns=columns).to_pandas()
        field_count = len(parquet.schema_arrow)
        if parquet.metadata.num_rows != manifest["counts"]["master_rows"]:
            raise ValueError("Master row count differs from its manifest")
    return dict(version="v1", wave=manifest["release"], master_sha256=sha, field_count=field_count,
                source_master="01_ingestion/05_master_parquet/output/master_products.parquet",
                master_manifest_sha256=hashlib.sha256((RELEASE/"manifest.json").read_bytes()).hexdigest(),
                lenses=LENSES, field_groups=groups,
                denominator_notes="Counts are barcode–region–category assignments. Nutrient counts include any non-null "
                "numeric value, including zero, within product scope. Claim states use both eligibility gates and "
                "the individual assessed flag. Counts describe selected evidence.",
                overall=summarize(rows),
                by_region={r: summarize(g) for r, g in rows.groupby("region")},
                by_region_category=[dict(region=r, category=c, **summarize(g))
                                    for (r, c), g in rows.groupby(["region", "category"])])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_suffix(".json"))
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    report = json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False)
    with args.output.open("w" if args.replace else "x", encoding="utf-8", newline="\n") as stream:
        stream.write(report + "\n")

