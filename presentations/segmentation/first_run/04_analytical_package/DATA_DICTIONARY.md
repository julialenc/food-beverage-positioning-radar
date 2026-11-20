# Analytical package v1 — data dictionary

Status: accepted frozen v1. Wave 2: retrieved 17 October 2026; cutoff 29 September. All outputs are local analytical artifacts, separate from Streamlit and the unchanged master. The package does not publish a website.

## Grain and joins

Primary key everywhere is text `barcode` + `region` + `category`. Preserve leading zeros; never import GTINs as numbers. analytical_assignments_v1.parquet retains all 382,527 master assignments, including 5,682 outside current product scope. `product_scope_eligible` selects the 376,845 governed analytical assignments. No universal nutrition-complete population is created. A shared GTIN across regions/categories is a legitimate separate assignment.

assessed_communication_v1.parquet is sparse: 12,161 matched locked evidence rows. Left-join it to assignments on the full key. An absent row means unknown/unassessed evidence, never a negative claim. The two locked ineligible salami assignments remain identifiable by source flags. Human observations join separately on key + proposition and must not overwrite locked fields. Boundary annotations join on key + boundary_family; their interpretations do not overwrite the accepted commercial layer.

## Nutrition contract

For each of energy/protein/fat/saturated_fat/carbohydrates/sugars/fibre/salt, keep original working field, its `_off_raw` source observation and `_missing` flag. The short metric name is the existing valid analytical value: working is within the accepted inclusive range (0–900 energy, 0–50 salt, 0–100 other nutrients), equals OFF raw, and its missing flag is zero. Otherwise it is null. These are inherited gates, not new corrections. Missing and recorded zero remain distinct. An accepted numerical value is not independent package verification.

`*_validity` is the first displayed explanation in this precedence: WORKING_NULL; SOURCE_MISSING_FLAG; WORKING_SOURCE_DISAGREEMENT; OUTSIDE_ACCEPTED_RANGE; VALID_RECORDED. Source fields preserve overlapping reasons. Foods use per 100 g; beverages require their inherited comparable-liquid per-100-ml basis. Preparations/unverified bases remain deferred. Do not compare raw as-sold powder measurements with ready-to-drink liquids.

protein_per100kcal = 100*protein/energy and fibre_per100kcal = 100*fibre/energy for valid energy >0. Zero denominators are undefined/null. energy_denominator_status distinguishes missing/invalid, zero, 0<E<10 and E>=10; it is not a universal exclusion. The cream/pudding rule specifically requires E>=10. Questionable sugar/energy combinations retain source observations; they are not proof of a novel recipe or a blanket reason to delete a product.

## Commercial identity and profiles

membership/subtype/confidence/reason/basis_group and beverage_view_segment preserve the approved baseline. cereal_* preserves original proposals and reviewed decisions separately; cereal_manual_review/manual_question is historical metadata, not a new blocking review queue. h2_format_candidate/effective_type_code retain the agreed cereal comparison population. savoury_format, construction/base_wording/flavour, corrected analytical_format and original_analytical_format, and juice_subformat/named_materials/concentrate_descriptor retain their accepted decision layers.

commercial_format is a consolidated display identity; commercial_status retains resolved, other, unresolved, conflicting, comparability-concern and outside-scope distinctions. commercial_source and format_confidence identify the interpretation source. HIGH/MEDIUM is textual support, not verified pack identity. analytical_use_status keeps excluded alcohol, deferred basis and unresolved formats explicit; unresolved products can remain useful at broader category level.

profile_status: IN_PROFILE; OTHER_MEASURABLE; REQUIRED_MEASUREMENT_UNKNOWN; NOT_INVESTIGATED_OR_NOT_APPLICABLE; OUTSIDE_PRODUCT_SCOPE. profile_id is populated only for IN_PROFILE. A null profile is not a negative health judgment or an inferred universal comparison arm. Thresholds are descriptive research conventions, not natural cluster boundaries or market prevalence. Granola uses the accepted H2 candidate population; potato crisps use the accepted savoury format, not boundary-driven reassignments.

| Profile family | profile_id | Required rule |
|---|---|---|
| granola | GRANOLA_LOWER_SUGARS_HIGHER_PROTEIN | sugars <=14 and protein >=11 g/100g |
| dessert cream/pudding | PUDDING_HIGHER_PROTEIN_LOWER_ENERGY | protein >=8 g/100g and 10<=energy<=110 kcal/100g |
| potato crisps | POTATO_CRISPS_LOWER_FAT | fat <=20 g/100g |
| soda | SODA_VERY_LOW_SUGARS | sugars <=0.5 g/100ml |
| energy drink | ENERGY_DRINK_VERY_LOW_SUGARS | sugars <=0.5 g/100ml |

## Presentation outcome resolution — required

NOT_INVESTIGATED_OR_NOT_APPLICABLE is an internal catch-all, never a user-facing research conclusion. Recover the display outcome from the explicit metadata and the 33-row `approved_findings_v1.json.formulation.decisions` register. Resolve record scope/identity/basis first, then the applicable studied-format decision. A missing register match defaults to NOT_INVESTIGATED_WITHIN_FORMAT; it must never default to ‘no meaningful segment found’. This is a presentation interpretation of accepted metadata, not a new nutritional classification.

| Priority / metadata predicate | Presentation outcome | Accepted decision reference |
|---|---|---|
| product_scope_eligible=false | OUTSIDE_PRODUCT_SCOPE | Source eligibility; not a research-negative finding |
| membership=NO, subtype=OUT or commercial_status=OUTSIDE_REVIEWED_FORMAT | OUTSIDE_REVIEWED_FORMAT | Reviewed identity; retain broader source record |
| analytical_use_status indicates alcohol exclusion | EXCLUDED_FROM_NUTRITIONAL_SCOPE | Alcohol |
| commercial_status unresolved/conflicting/comparability-concern, or juice subtype unresolved/ambiguous/boundary concern | IDENTITY_OR_SUBTYPE_UNRESOLVED | Unresolved dairy desserts / saved commercial decisions |
| analytical_use_status indicates deferred/unverified basis | DEFERRED_COMPARABILITY | Preparations |
| profile_family exists | Use IN_PROFILE, OTHER_MEASURABLE or REQUIRED_MEASUREMENT_UNKNOWN directly | Five approved profiles; unknown measurement is not an uninvestigated format |
| cereal: flakes; snacks: biscuit or tortilla/corn chips | RESEARCHED_NUTRITIONAL_VARIATION_NO_ADDITIONAL_PROFILE | Flakes / Biscuits / Tortilla/corn chips |
| snacks: puffed/extruded; beverages: juice, smoothie, nectar, fruit drink, fermented soft drink, flavoured/coconut water | RESEARCHED_COMMERCIAL_DISTINCTION_NO_ADDITIONAL_PROFILE | Puffed/extruded snacks / Juice / Smoothies; nectars; fruit drinks; fermented soft drinks / Water; flavoured water; coconut water |
| beverages: plant drink soy/almond | COMMERCIAL_BASE_DISTINCTION_WITH_VARIATION | Plant drinks |
| snacks: wafer; identified dairy desserts outside cream/pudding/mousse/flan; iced tea/coffee/sports liquids; sparse oat/rice/coconut plant drinks | INVESTIGATED_INSUFFICIENT_EVIDENCE_FOR_SUBDIVISION | Wafers / Other identified dairy desserts / Iced tea; iced coffee; sports/electrolyte liquids / Plant drinks |
| dairy: mousse/flan | RESEARCHED_VARIATION_AND_DENSITY_VIEW | Mousse; flan |
| other savoury formats (including popcorn, pretzels, crackers, nuts/seeds and other identifiable forms); other cereal/dairy branches; other unmatched formats | NOT_INVESTIGATED_WITHIN_FORMAT | Other savoury formats / Other cereal and dairy branches; broad H1–H12 tests do not establish format-specific closure |

Match on category plus the stored commercial_format/subtype/dairy_format/savoury_format fields; use juice_subformat and strict_comparable for composition uncertainty. Register branch names are scoped labels, not a GTIN join key. Granola-labelled records outside the accepted profile-family population are not automatically assigned that population's research outcome. Display NOT_COVERED_BY_ACCEPTED_PROFILE_POPULATION where applicable. Preserve the independent commercial, formulation and communication dimensions; insufficient claim coverage does not erase a nutritional profile. The safe fallback above covers all unlisted rows without inventing a negative result.

## Locked communication and human evidence

All `claims_*` columns retain the master source values and namespaces. For core proposition p: claims_claim_p is nullable source value; claims_state_p is locked observation state; claims_basis_p is its provenance basis. Source references, record_id, source_barcode/category, image URL, evidence cohort, saved core evidence JSON, QA notes, original outcomes and independent v6 fields remain attached. They concern assessed packaging evidence, not verified package-wide absence, product healthfulness or regulated claim compliance.

Primary population claim status requires claims_matched=true and claims_analytical_eligible=true, with no source_market_limitation. Positive: value=true. Documented non-detection: value=false AND state=DOCUMENTED_NOT_DETECTED. HUMAN_CONFIRMED_NEGATIVE stays separate. UNCERTAIN, other assessed unknown, unassessed/ineligible and market-limited remain separate. Exact positive+documented non-detection is the known denominator; human examples are never added to it. Source gates preserve the distinction between no match and excluded evidence.

Display locked sugar_free_claim as **sugar-related communication**. It includes saved no-added-sugar wording, literal sugar-free wording and model-assessment positives. Keep exact wording/provenance. energy_positioning is the approved derived positioning field; preserve original_energy_claim separately. Hydration/electrolyte positioning and v6 usability/status remain independent of core extraction.

human_observations_v1.parquet preserves the 12 interpreted human submissions, including original and reconciled key, recorded/normalized review dates, source wording, interpretation and limits. Future-date flags remain; recorded dates are not silently corrected. This is a selected qualitative layer, not an expanded representative claims sample.

## Summary and decision contracts

population_summary_v1.csv is long-format: governed population, nutrient availability, commercial population and 15 approved profile cells. Its numeric zeros count observed zeros and never replace missing measurements. communication_coverage_v1.csv reproduces the accepted overlapping baseline/accepted/juice-detail cohorts and profile/comparison/unknown slices. Parent/child rows overlap: never sum them as unique-product counts. It exposes full, matched, usable-market, proposition-known and unknown denominators independently.

approved_findings_v1.json carries the 33 accepted formulation decisions, supported UK soda comparison with its wording anomaly, selected H5 reuse, unresolved communication populations, conditional French muesli/NOVA association, exploratory US granola, bounded boundary scope, stable juice sensitivity, density/control context and deferrals. Its original effect/interval/p/q values are reused from accepted evidence, not refitted. Source IDs resolve through manifest_v1.json and ARTIFACT_INDEX.md.

## Exact output schemas

Types below are serialized Arrow/CSV types; the preceding contracts define meaning and permitted interpretation. Original source labels remain separately named rather than silently replaced.

### analytical_assignments_v1.parquet

| Field | Stored type |
|---|---|
| `barcode` | `string` |
| `region` | `string` |
| `category` | `string` |
| `product_name` | `string` |
| `off_categories` | `string` |
| `normalized_brand` | `string` |
| `brand_family` | `string` |
| `resolved_company` | `string` |
| `quantity` | `string` |
| `assignment_countries` | `list<element: string>` |
| `image_url` | `string` |
| `nova_group` | `double` |
| `product_scope_eligible` | `bool` |
| `nutrition_quality_status` | `string` |
| `nutrition_quality_reason` | `string` |
| `warning_summary` | `string` |
| `reviewed_nutrition_category_decision` | `string` |
| `reviewed_beverage_status` | `string` |
| `energy_kcal` | `double` |
| `energy_kcal_off_raw` | `double` |
| `energy_kcal_missing` | `int64` |
| `protein_100g` | `double` |
| `protein_100g_off_raw` | `double` |
| `protein_100g_missing` | `int64` |
| `fat_100g` | `double` |
| `fat_100g_off_raw` | `double` |
| `fat_100g_missing` | `int64` |
| `saturated_fat_100g` | `double` |
| `saturated_fat_100g_off_raw` | `double` |
| `saturated_fat_100g_missing` | `int64` |
| `carbs_100g` | `double` |
| `carbs_100g_off_raw` | `double` |
| `carbs_100g_missing` | `int64` |
| `sugars_100g` | `double` |
| `sugars_100g_off_raw` | `double` |
| `sugars_100g_missing` | `int64` |
| `fiber_100g` | `double` |
| `fiber_100g_off_raw` | `double` |
| `fiber_100g_missing` | `int64` |
| `salt_100g` | `double` |
| `salt_100g_off_raw` | `double` |
| `salt_100g_missing` | `int64` |
| `energy` | `double` |
| `protein` | `double` |
| `fat` | `double` |
| `saturated_fat` | `double` |
| `carbohydrates` | `double` |
| `sugars` | `double` |
| `fibre` | `double` |
| `salt` | `double` |
| `energy_validity` | `large_string` |
| `protein_validity` | `large_string` |
| `fat_validity` | `large_string` |
| `saturated_fat_validity` | `large_string` |
| `carbohydrates_validity` | `large_string` |
| `sugars_validity` | `large_string` |
| `fibre_validity` | `large_string` |
| `salt_validity` | `large_string` |
| `protein_per100kcal` | `double` |
| `fibre_per100kcal` | `double` |
| `energy_denominator_status` | `large_string` |
| `membership` | `large_string` |
| `subtype` | `large_string` |
| `confidence` | `large_string` |
| `reason` | `large_string` |
| `basis_group` | `large_string` |
| `beverage_view_segment` | `large_string` |
| `cereal_bar_review_flag` | `large_string` |
| `cereal_review_type_code` | `large_string` |
| `peer` | `bool` |
| `dairy_format` | `large_string` |
| `biscuit_format` | `large_string` |
| `biscuit_construction` | `large_string` |
| `commercial_format` | `large_string` |
| `commercial_source` | `large_string` |
| `commercial_status` | `large_string` |
| `format_confidence` | `large_string` |
| `analytical_use_status` | `large_string` |
| `geography_role` | `large_string` |
| `profile_family` | `large_string` |
| `profile_status` | `large_string` |
| `profile_id` | `large_string` |
| `profile_rule` | `large_string` |
| `savoury_format` | `large_string` |
| `format_evidence` | `large_string` |
| `flavour` | `large_string` |
| `construction` | `large_string` |
| `base_wording` | `large_string` |
| `accepted_snack_profile` | `large_string` |
| `analytical_format` | `large_string` |
| `comparable_liquid` | `bool` |
| `composition_band` | `large_string` |
| `accepted_beverage_profile` | `large_string` |
| `original_analytical_format` | `large_string` |
| `juice_family_review_scope` | `bool` |
| `juice_classification_confidence` | `large_string` |
| `juice_classification_reason` | `large_string` |
| `juice_name_evidence` | `large_string` |
| `juice_tag_evidence` | `large_string` |
| `juice_classification_version` | `large_string` |
| `juice_correction_applied` | `bool` |
| `juice_subformat` | `large_string` |
| `composition_evidence` | `large_string` |
| `named_materials` | `large_string` |
| `concentrate_descriptor` | `large_string` |
| `flavour_construction` | `large_string` |
| `strict_comparable` | `bool` |
| `sugar_band` | `large_string` |
| `effective_type_code` | `large_string` |
| `h2_format_candidate` | `bool` |
| `cereal_original_screen_status` | `large_string` |
| `cereal_original_format` | `large_string` |
| `cereal_original_cereal_proposal` | `large_string` |
| `cereal_original_type_proposal` | `large_string` |
| `cereal_review_cereal` | `large_string` |
| `cereal_review_type` | `large_string` |
| `cereal_type_code` | `large_string` |
| `cereal_effective_membership` | `large_string` |
| `cereal_decision_source` | `large_string` |
| `cereal_confidence` | `large_string` |
| `cereal_manual_review` | `large_string` |
| `cereal_manual_question` | `large_string` |
| `cereal_decision_reason` | `large_string` |
| `cereal_decision_basis` | `large_string` |
| `claims_matched` | `bool` |
| `claims_record_id` | `string` |
| `claims_analytical_eligible` | `bool` |
| `claims_evidence_cohort` | `string` |
| `claims_source_market_limitation` | `string` |
| `claims_nutrition_qa_hold` | `string` |
| `claims_population_qa_note` | `string` |

### assessed_communication_v1.parquet

| Field | Stored type |
|---|---|
| `barcode` | `string` |
| `region` | `string` |
| `category` | `string` |
| `claims_matched` | `bool` |
| `claims_record_id` | `string` |
| `claims_product_name` | `string` |
| `claims_image_url` | `string` |
| `claims_evidence_cohort` | `string` |
| `claims_original_overall_outcome` | `string` |
| `claims_source_country_assignments` | `string` |
| `claims_source_market_limitation` | `string` |
| `claims_analytical_eligible` | `bool` |
| `claims_eligibility_reason` | `string` |
| `claims_energy_drink_membership` | `bool` |
| `claims_energy_drink_format` | `string` |
| `claims_energy_positioning` | `bool` |
| `claims_energy_positioning_basis` | `string` |
| `claims_original_energy_claim` | `bool` |
| `claims_core_claim_evidence_json` | `string` |
| `claims_source_references` | `string` |
| `claims_core_assessment_context` | `string` |
| `claims_core_assessment_quality` | `string` |
| `claims_core_assessment_status` | `string` |
| `claims_v6_disposition` | `string` |
| `claims_v6_usable` | `bool` |
| `claims_nutrition_qa_hold` | `string` |
| `claims_population_qa_note` | `string` |
| `claims_claim_protein_claim` | `bool` |
| `claims_state_protein_claim` | `string` |
| `claims_basis_protein_claim` | `string` |
| `claims_claim_sugar_free_claim` | `bool` |
| `claims_state_sugar_free_claim` | `string` |
| `claims_basis_sugar_free_claim` | `string` |
| `claims_claim_reduced_sugar` | `bool` |
| `claims_state_reduced_sugar` | `string` |
| `claims_basis_reduced_sugar` | `string` |
| `claims_claim_no_palm_oil` | `bool` |
| `claims_state_no_palm_oil` | `string` |
| `claims_basis_no_palm_oil` | `string` |
| `claims_claim_no_artificial` | `bool` |
| `claims_state_no_artificial` | `string` |
| `claims_basis_no_artificial` | `string` |
| `claims_claim_natural_claim` | `bool` |
| `claims_state_natural_claim` | `string` |
| `claims_basis_natural_claim` | `string` |
| `claims_claim_fortification_claim` | `bool` |
| `claims_state_fortification_claim` | `string` |
| `claims_basis_fortification_claim` | `string` |
| `claims_claim_fibre_claim` | `bool` |
| `claims_state_fibre_claim` | `string` |
| `claims_basis_fibre_claim` | `string` |
| `claims_claim_gut_health_claim` | `bool` |
| `claims_state_gut_health_claim` | `string` |
| `claims_basis_gut_health_claim` | `string` |
| `claims_claim_probiotic_claim` | `bool` |
| `claims_state_probiotic_claim` | `string` |
| `claims_basis_probiotic_claim` | `string` |
| `claims_claim_prebiotic_claim` | `bool` |
| `claims_state_prebiotic_claim` | `string` |
| `claims_basis_prebiotic_claim` | `string` |
| `claims_claim_immune_claim` | `bool` |
| `claims_state_immune_claim` | `string` |
| `claims_basis_immune_claim` | `string` |
| `claims_claim_energy_claim` | `bool` |
| `claims_state_energy_claim` | `string` |
| `claims_basis_energy_claim` | `string` |
| `claims_claim_sleep_claim` | `bool` |
| `claims_state_sleep_claim` | `string` |
| `claims_basis_sleep_claim` | `string` |
| `claims_claim_brain_health_claim` | `bool` |
| `claims_state_brain_health_claim` | `string` |
| `claims_basis_brain_health_claim` | `string` |
| `claims_claim_vitalite_concept` | `bool` |
| `claims_state_vitalite_concept` | `string` |
| `claims_basis_vitalite_concept` | `string` |
| `claims_claim_sustainability_halo` | `bool` |
| `claims_state_sustainability_halo` | `string` |
| `claims_basis_sustainability_halo` | `string` |
| `claims_claim_reformulation_claim` | `bool` |
| `claims_state_reformulation_claim` | `string` |
| `claims_basis_reformulation_claim` | `string` |
| `claims_claim_comparative_claim` | `bool` |
| `claims_state_comparative_claim` | `string` |
| `claims_basis_comparative_claim` | `string` |
| `claims_claim_glp1_positioning` | `bool` |
| `claims_state_glp1_positioning` | `string` |
| `claims_basis_glp1_positioning` | `string` |
| `claims_claim_origin_quality_claim` | `bool` |
| `claims_state_origin_quality_claim` | `string` |
| `claims_basis_origin_quality_claim` | `string` |
| `claims_claim_clean_label_claim` | `bool` |
| `claims_state_clean_label_claim` | `string` |
| `claims_basis_clean_label_claim` | `string` |
| `claims_claim_minimal_ingredients_claim` | `bool` |
| `claims_state_minimal_ingredients_claim` | `string` |
| `claims_basis_minimal_ingredients_claim` | `string` |
| `claims_claim_artisan_claim` | `bool` |
| `claims_state_artisan_claim` | `string` |
| `claims_basis_artisan_claim` | `string` |
| `claims_claim_vegan_claim` | `bool` |
| `claims_state_vegan_claim` | `string` |
| `claims_basis_vegan_claim` | `string` |
| `claims_claim_organic_claim` | `bool` |
| `claims_state_organic_claim` | `string` |
| `claims_basis_organic_claim` | `string` |
| `claims_claim_dairy_free_claim` | `bool` |
| `claims_state_dairy_free_claim` | `string` |
| `claims_basis_dairy_free_claim` | `string` |
| `claims_claim_lactose_free_claim` | `bool` |
| `claims_state_lactose_free_claim` | `string` |
| `claims_basis_lactose_free_claim` | `string` |
| `claims_claim_plant_based_claim` | `bool` |
| `claims_state_plant_based_claim` | `string` |
| `claims_basis_plant_based_claim` | `string` |
| `claims_claim_heritage_claim` | `bool` |
| `claims_state_heritage_claim` | `string` |
| `claims_basis_heritage_claim` | `string` |
| `claims_claim_gluten_free_claim` | `bool` |
| `claims_state_gluten_free_claim` | `string` |
| `claims_basis_gluten_free_claim` | `string` |
| `claims_claim_gender_targeting_claim` | `bool` |
| `claims_state_gender_targeting_claim` | `string` |
| `claims_basis_gender_targeting_claim` | `string` |
| `claims_claim_reduced_fat_claim` | `bool` |
| `claims_state_reduced_fat_claim` | `string` |
| `claims_basis_reduced_fat_claim` | `string` |
| `claims_claim_whole_grain_claim` | `bool` |
| `claims_state_whole_grain_claim` | `string` |
| `claims_basis_whole_grain_claim` | `string` |
| `claims_protein_amount_g` | `double` |
| `claims_protein_amount_basis` | `string` |
| `claims_protein_amount_provenance` | `string` |
| `claims_fortification_nutrients_json` | `string` |
| `claims_fortification_meaning` | `string` |
| `claims_hydration_content_status` | `string` |
| `claims_hydration_front_status` | `string` |
| `claims_hydration_positioning` | `bool` |
| `claims_electrolyte_content_status` | `string` |
| `claims_electrolyte_front_status` | `string` |
| `claims_electrolyte_positioning` | `bool` |
| `claims_source_barcode` | `string` |
| `claims_source_category` | `string` |
| `assessment_analytical_gate` | `bool` |
| `assessment_market_usable` | `bool` |

### boundary_annotations_v1.parquet

| Field | Stored type |
|---|---|
| `barcode` | `string` |
| `region` | `string` |
| `category` | `string` |
| `boundary_family` | `large_string` |
| `original_format` | `large_string` |
| `current_format` | `large_string` |
| `correction_applied` | `bool` |
| `name_evidence` | `large_string` |
| `tag_evidence` | `large_string` |
| `independently_named` | `bool` |
| `independently_tagged` | `bool` |
| `name_tag_corroborated` | `bool` |
| `primary_identity` | `large_string` |
| `boundary_status` | `large_string` |
| `overlap_flag` | `bool` |
| `unresolved_flag` | `bool` |
| `separate_use_caution` | `bool` |
| `potato_base_evidence` | `large_string` |
| `construction` | `large_string` |
| `crisp_descriptor` | `bool` |
| `named_composition` | `large_string` |
| `mixed_base_flag` | `bool` |
| `baked_wording` | `bool` |

### communication_coverage_v1.csv

Columns: `cohort_family`, `category`, `branch`, `slice`, `region`, `proposition`, `population_n`, `matched_eligible_n`, `usable_market_n`, `positive_n`, `documented_non_detection_n`, `human_negative_n`, `uncertain_n`, `other_unknown_assessed_n`, `unassessed_n`, `market_limited_n`, `known_primary_n`, `known_pct_of_population`, `historical_reuse_n`, `qa_note_n`, `two_arm_floor`.

### human_observations_v1.parquet

| Field | Stored type |
|---|---|
| `review_id` | `large_string` |
| `barcode` | `string` |
| `region` | `string` |
| `category` | `string` |
| `proposition` | `large_string` |
| `branch` | `large_string` |
| `arm` | `large_string` |
| `product_name` | `string` |
| `image_url` | `string` |
| `barcode_recorded` | `large_string` |
| `key_reconciliation` | `large_string` |
| `human_claim_state_recorded` | `large_string` |
| `human_exact_wording_recorded` | `large_string` |
| `human_other_wording_recorded` | `large_string` |
| `human_notes_recorded` | `large_string` |
| `reviewer` | `large_string` |
| `review_date_recorded` | `large_string` |
| `review_date_normalized` | `large_string` |
| `date_status` | `large_string` |
| `submission_received_date` | `large_string` |
| `derived_target_state` | `large_string` |
| `interpretation` | `large_string` |
| `evidence_provenance` | `large_string` |
| `evidence_scope` | `large_string` |
| `metadata_limit` | `large_string` |
| `inferential_usage` | `large_string` |
| `source_sha256` | `large_string` |
| `locked_master_sha256` | `large_string` |
| `energy_kcal_per100g` | `large_string` |
| `protein_g_per100g` | `large_string` |
| `fat_g_per100g` | `large_string` |
| `sugars_g_per100g` | `large_string` |

### population_summary_v1.csv

Columns: `record_kind`, `region`, `category`, `population_n`, `eligible_n`, `outside_scope_n`, `metric`, `available_n`, `missing_or_invalid_n`, `recorded_zero_n`, `commercial_format`, `commercial_status`, `profile_family`, `profile_id`, `retained_n`, `other_measurable_n`, `unknown_required_n`, `retained_pct_of_measurable`.
