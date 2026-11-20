"""One canonical analytical rerun from frozen Wave 2 and accepted keyed decisions.

Run: .venv/Scripts/python.exe -B <this file>
Then: .venv/Scripts/python.exe -B <sibling verify_analytical_package_v1.py>
No exploratory analyses, source updates, providers, models or publication.
"""
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import analytical_rules_v1 as rules

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
PROJECT=STUDY.parents[2]
LENSES=STUDY/"03_lenses"
L1=LENSES/"01_nutritional_composition"
L3=LENSES/"03_claims_composition_and_ingredients"
L4=LENSES/"04_positioning_tradeoffs"
EDA=STUDY/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
OUT=HERE/"output"
FREEZE=HERE/"RELEASE_FREEZE_v1.json"
KEY=rules.KEY
MASTER=STUDY/"01_ingestion/05_master_parquet/output/master_products.parquet"
LOCK=STUDY/"01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1"
INPUTS={
 "MASTER":MASTER,"MASTER_MANIFEST":MASTER.parent/"manifest.json","LOCKED_CLAIMS":LOCK/"claims_join.parquet",
 "BASELINE_CLASSIFICATIONS":EDA/"subtype_assignments.csv",
 "CEREAL_DECISIONS":EDA.parent/"01_nutritional_composition/lens1_cereal_master_v1.parquet",
 "SAVOURY_DECISIONS":L1/"savoury_snack_assignments_v1.parquet",
 "BEVERAGE_DECISIONS":L1/"beverage_assignments_v1.parquet","JUICE_DECISIONS":L1/"juice_assignments_v1.parquet",
 "HUMAN_SOURCE":L3/"human_claim_decisions_v1.csv","HUMAN_DECISIONS":L3/"human_claim_adjudications_v1.csv",
 "BOUNDARY_EVIDENCE":L4/"processing_boundary_evidence_v1.parquet",
 "FORMULATION_DECISIONS":LENSES/"FORMULATION_DECISIONS_v1.csv",
 "COMMUNICATION_RESULTS":L3/"communication_overlays_v1.csv","PROCESSING_RESULTS":L4/"organic_nova_v1.csv",
 "BOUNDARY_RESULTS":L4/"category_boundaries_v1.csv","FINAL_JUICE_SENSITIVITY":L1/"juice_confidence_sensitivity_v1.csv",
 "POST_V1_BACKLOG":L3/"post_v1_evidence_gaps_v1.csv"}
REFERENCES={"FORMULATION_SYNTHESIS":LENSES/"FORMULATION_SYNTHESIS_v1.md","HYPOTHESIS_CHECK":LENSES/"CHECK.md",
 "CEREAL_REPORT":L1/"cereal_formulations_v1.md","DAIRY_REPORT":LENSES/"02_nutrient_density/dairy_dessert_formulations_v1.md",
 "BISCUIT_REPORT":L1/"biscuits_and_wafers_CHECK_v1.md","SAVOURY_REPORT":L1/"savoury_snacks_CHECK_v1.md",
 "BEVERAGE_REPORT":L1/"beverages_CHECK_v1.md","JUICE_REPORT":L1/"juice_formulations_v1.md",
 "COMMUNICATION_CHECK":L3/"communication_overlays_CHECK_v1.md","PROCESSING_CHECK":L4/"processing_boundaries_CHECK_v1.md",
 "JUICE_CORRECTION_CHECK":L1/"juice_classification_CHECK_v1.md","HUMAN_REVIEW_CHECK":L3/"human_review_preparation_CHECK_v1.md"}
VALIDATION_REFERENCES={"ACCEPTED_NUTRIENT_COUNTS":EDA/"nutrient_availability.csv",
 "ACCEPTED_COMMUNICATION_COUNTS":L3/"communication_coverage_v1.csv",
 "RESEARCH_DAIRY_CLASSIFIER":LENSES/"02_nutrient_density/dairy_dessert_formulations_v1.py",
 "RESEARCH_BISCUIT_CLASSIFIER":L1/"biscuits_and_wafers_v1.py",
 "RESEARCH_COVERAGE_COHORTS":L3/"communication_coverage_v1.py"}
SOURCE_COLS=["product_name","off_categories","normalized_brand","brand_family","resolved_company","quantity","assignment_countries","image_url",
 "nova_group","product_scope_eligible","nutrition_quality_status","nutrition_quality_reason","warning_summary",
 "reviewed_nutrition_category_decision","reviewed_beverage_status"]


def digest(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()


def verify_frozen_release():
    """Read-only integrity check. Accepted v1 is never overwritten by a rerun."""
    receipt=json.loads(FREEZE.read_text(encoding="utf-8"))
    assert receipt["status"]=="ACCEPTED_FROZEN"
    for name,expected in receipt["files"].items():
        assert digest(HERE/name)==expected,("frozen release changed",name)
    expected=hashlib.sha256(json.dumps(receipt["files"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert expected==receipt["release_digest"],"Freeze inventory identity changed"
    manifest=json.loads((OUT/"manifest_v1.json").read_text(encoding="utf-8"))
    for info in {**manifest["inputs"],**manifest["evidence_references"],**manifest["validation_references"]}.values():
        assert digest(PROJECT/info["path"])==info["sha256"],("protected dependency changed",info["path"])
    return receipt,manifest


def relative(path):return path.relative_to(PROJECT).as_posix()


def clean_json(value):
    if isinstance(value,dict):return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,list):return [clean_json(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(np.floating,)):return None if not np.isfinite(value) else float(value)
    if isinstance(value,(np.bool_,)):return bool(value)
    if value is pd.NA or (isinstance(value,float) and not np.isfinite(value)):return None
    return value


def write_json(path,value):
    path.write_text(json.dumps(clean_json(value),ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def join_layer(a,path,columns,renames=None):
    x=pd.read_parquet(path,columns=KEY+columns).rename(columns=renames or {})
    assert not x.duplicated(KEY).any(),path
    assert set(map(tuple,x[KEY].to_numpy()))<=set(map(tuple,a[KEY].to_numpy())),path
    return a.merge(x,on=KEY,how="left",validate="one_to_one",sort=False)


def read_inputs():
    source_names=pq.read_schema(MASTER).names
    claim_cols=[c for c in source_names if c.startswith("claims_")]
    metrics=[field+suffix for field in rules.RAW.values() for suffix in ["","_off_raw","_missing"]]
    raw=pq.read_table(MASTER,columns=KEY+SOURCE_COLS+metrics+claim_cols).to_pandas()
    assert len(raw)==382527 and not raw.duplicated(KEY).any()
    assert raw.product_scope_eligible.sum()==376845
    assert raw.barcode.map(lambda x:isinstance(x,str)).all()
    claims=raw.loc[raw.claims_matched.eq(True),KEY+claim_cols].copy()
    claims["assessment_analytical_gate"]=claims.claims_analytical_eligible.eq(True)
    claims["assessment_market_usable"]=claims.assessment_analytical_gate&claims.claims_source_market_limitation.fillna("").eq("")
    a=rules.nutrition(raw)
    baseline=pd.read_csv(INPUTS["BASELINE_CLASSIFICATIONS"],dtype=str,keep_default_na=False,
        usecols=KEY+["membership","subtype","confidence","reason","basis_group","beverage_view_segment","cereal_bar_review_flag","cereal_review_type_code"])
    assert len(baseline)==376845 and not baseline.duplicated(KEY).any()
    a=a.merge(baseline,on=KEY,how="left",validate="one_to_one",sort=False)
    assert a.loc[a.product_scope_eligible,"membership"].notna().all()
    cereal_cols=["original_screen_status","original_format","original_cereal_proposal","original_type_proposal","review_cereal","review_type","type_code",
        "effective_membership","effective_type_code","decision_source","h2_format_candidate","confidence","manual_review","manual_question","decision_reason","decision_basis"]
    renames={c:"cereal_"+c for c in cereal_cols if c not in ["effective_type_code","h2_format_candidate"]}
    a=join_layer(a,INPUTS["CEREAL_DECISIONS"],cereal_cols,renames)
    a=join_layer(a,INPUTS["SAVOURY_DECISIONS"],["savoury_format","format_evidence","flavour","construction","base_wording","formulation_profile"],
        {"formulation_profile":"accepted_snack_profile"})
    a=join_layer(a,INPUTS["BEVERAGE_DECISIONS"],["analytical_format","comparable_liquid","composition_band","retained_profile","original_analytical_format",
        "juice_family_review_scope","juice_classification_confidence","juice_classification_reason","juice_name_evidence","juice_tag_evidence","juice_classification_version","juice_correction_applied"],
        {"retained_profile":"accepted_beverage_profile"})
    a=join_layer(a,INPUTS["JUICE_DECISIONS"],["juice_subformat","composition_evidence","named_materials","concentrate_descriptor","flavour_construction","strict_comparable","sugar_band"])
    a=rules.profiles(rules.classify(a))
    return a,claims,claim_cols


def assignments(a):
    rawcols=[field+suffix for field in rules.RAW.values() for suffix in ["","_off_raw","_missing"]]
    columns=KEY+SOURCE_COLS+rawcols+list(rules.RAW)+[m+"_validity" for m in rules.RAW]+[
        "protein_per100kcal","fibre_per100kcal","energy_denominator_status",
        "membership","subtype","confidence","reason","basis_group","beverage_view_segment","cereal_bar_review_flag","cereal_review_type_code",
        "peer","dairy_format","biscuit_format","biscuit_construction","commercial_format","commercial_source","commercial_status","format_confidence",
        "analytical_use_status","geography_role","profile_family","profile_status","profile_id","profile_rule",
        "savoury_format","format_evidence","flavour","construction","base_wording","accepted_snack_profile",
        "analytical_format","comparable_liquid","composition_band","accepted_beverage_profile","original_analytical_format",
        "juice_family_review_scope","juice_classification_confidence","juice_classification_reason","juice_name_evidence","juice_tag_evidence","juice_classification_version","juice_correction_applied",
        "juice_subformat","composition_evidence","named_materials","concentrate_descriptor","flavour_construction","strict_comparable","sugar_band",
        "effective_type_code","h2_format_candidate"]
    columns += [c for c in a if c.startswith("cereal_") and c not in columns]
    columns += ["claims_matched","claims_record_id","claims_analytical_eligible","claims_evidence_cohort","claims_source_market_limitation","claims_nutrition_qa_hold","claims_population_qa_note"]
    assert len(columns)==len(set(columns))
    return a[columns].copy()


def population_summary(a):
    rows=[]
    for (region,category),g in a.groupby(["region","category"]):
        rows.append(dict(record_kind="governed population",region=region,category=category,population_n=len(g),eligible_n=int(g.product_scope_eligible.sum()),outside_scope_n=int((~g.product_scope_eligible).sum())))
        for metric in rules.RAW:
            z=g[g.product_scope_eligible]
            rows.append(dict(record_kind="nutrient availability",region=region,category=category,metric=metric,population_n=len(z),
                             available_n=int(z[metric].notna().sum()),missing_or_invalid_n=int(z[metric].isna().sum()),recorded_zero_n=int(z[metric].eq(0).sum())))
    for (region,category,form,status),g in a[a.product_scope_eligible].groupby(["region","category","commercial_format","commercial_status"],dropna=False):
        rows.append(dict(record_kind="commercial population",region=region,category=category,commercial_format=form,commercial_status=status,population_n=len(g)))
    for (region,family),g in a[a.profile_family.notna()].groupby(["region","profile_family"]):
        retained=int(g.profile_status.eq("IN_PROFILE").sum());unknown=int(g.profile_status.eq("REQUIRED_MEASUREMENT_UNKNOWN").sum())
        rows.append(dict(record_kind="approved profile",region=region,category=g.category.iloc[0],profile_family=family,profile_id=rules.PROFILE_IDS[family],
                         population_n=len(g),eligible_n=len(g)-unknown,retained_n=retained,other_measurable_n=int(g.profile_status.eq("OTHER_MEASURABLE").sum()),
                         unknown_required_n=unknown,retained_pct_of_measurable=100*retained/(len(g)-unknown)))
    return pd.DataFrame(rows)


def boundary_annotations():
    frame=pd.read_parquet(INPUTS["BOUNDARY_EVIDENCE"])
    x=frame[frame.record_kind.eq("boundary evidence")].copy()
    columns=KEY+["boundary_family","original_format","current_format","correction_applied","name_evidence","tag_evidence","independently_named",
        "independently_tagged","name_tag_corroborated","primary_identity","boundary_status","overlap_flag","unresolved_flag","separate_use_caution",
        "potato_base_evidence","construction","crisp_descriptor","named_composition","mixed_base_flag","baked_wording"]
    x=x[columns];assert not x.duplicated(KEY+["boundary_family"]).any()
    return x


def approved_findings(a,coverage):
    formulation=pd.read_csv(INPUTS["FORMULATION_DECISIONS"])
    comm=pd.read_csv(INPUTS["COMMUNICATION_RESULTS"],dtype={"barcode":str})
    proc=pd.read_csv(INPUTS["PROCESSING_RESULTS"])
    sens=pd.read_csv(INPUTS["FINAL_JUICE_SENSITIVITY"])
    soda=comm[comm.record_kind.eq("comparison")&comm.branch.eq("soda")&comm.region.eq("UK-IE")].iloc[0]
    anomaly=comm[comm.record_kind.eq("focused_anomaly")].iloc[0]
    muesli=proc[proc.category.eq("cereal")&proc.commercial_type.eq("MUESLI")&proc.region.eq("FR")].iloc[0]
    us=proc[proc.category.eq("cereal")&proc.commercial_type.eq("GRANOLA")&proc.region.eq("US-CA")].iloc[0]
    for branch,expected in [("granola",[251,94,121]),("dessert cream/pudding",[27,15,1]),("potato crisps",[100,90,53]),("soda",[713,255,96]),("energy drink",[153,88,97])]:
        actual=a[a.profile_family.eq(branch)&a.profile_status.eq("IN_PROFILE")].groupby("region").size().reindex(rules.REGIONS).tolist()
        assert actual==expected,(branch,actual)
    assert soda.profile_positive_n==28 and soda.profile_known_n==43 and soda.other_positive_n==1 and soda.other_known_n==43
    assert muesli.organic_positive_nova4_n==6 and muesli.joint_organic_positive_n==24 and muesli.non_detection_nova4_n==25 and muesli.joint_non_detection_n==48
    reuse=comm[comm.record_kind.eq("reused_H5")].to_dict("records")
    missing=[]
    for branch,prop in [("dessert cream/pudding","protein_claim"),("potato crisps","reduced_fat_claim"),("energy drink","sugar_free_claim"),("soda","sugar_free_claim")]:
        z=coverage[coverage.cohort_family.eq("accepted")&coverage.branch.eq(branch)&coverage.slice.eq("retained profile")&coverage.proposition.eq(prop)&coverage.region.isin(["FR","UK-IE"])]
        for row in z.to_dict("records"):
            if branch=="soda" and row["region"]=="UK-IE":continue
            row["decision"]="INSUFFICIENT_ASSESSED_EVIDENCE_FOR_COMPARISON";missing.append(row)
    return dict(version=rules.VERSION,status="VALIDATED_CANDIDATE_FOR_REVIEW",unit="barcode-region-category assignment",
        hierarchy=["commercial identity","nutritional formulation","communicated positioning"],
        limitations=["OFF assortment and selected pack evidence are not market prevalence","US/Canada nutrition subsets are selected exploratory populations",
            "HIGH/MEDIUM classification confidence describes textual support, not verified identity","Recorded zero and missing remain distinct",
            "NOVA is a recorded processing attribute, not a healthfulness, causality or claim-compliance verdict",
            "Profile thresholds are research conventions, not established natural cluster boundaries"],
        formulation=dict(source_id="FORMULATION_DECISIONS",decisions=formulation.to_dict("records")),
        communication=dict(source_id="COMMUNICATION_RESULTS",display_label_for_sugar_free_claim="sugar-related communication",
            supported_uk_soda=dict(decision="SUPPORTED_SELECTED_ASSESSMENT_COMPARISON",result=soda.to_dict(),focused_exception=anomaly.to_dict(),
                wording="Locked sugar_free_claim includes no added sugar and literal sugar free; no literal-claim prevalence inference."),
            granola=dict(decision="DESCRIPTIVE_SELECTED_EVIDENCE",claims=["protein_claim","fibre_claim","organic_claim"],coverage_output="communication_coverage_v1.csv"),
            unresolved_profile_comparisons=missing,reused_H5=reuse,
            other_hypotheses={"H6":"narrow combined-family context; no refined-juice promotion","H7":"selected exploratory ingredient wording evidence",
                "H8":"descriptive only","H9":"limited reduced-fat-cheese/sugar pattern; relative threshold 1.9 g/100g",
                "H10":"US/Canada granola only; exploratory","H11":"density/communication non-coincidence, not missed marketing opportunities",
                "H12":"compare geographies within commercial identity; selected-population qualifications"}),
        processing=dict(source_id="PROCESSING_RESULTS",french_muesli=dict(decision="CONDITIONAL_SELECTED_EVIDENCE_ASSOCIATION",result=muesli.to_dict()),
            us_granola=dict(decision="DESCRIPTIVE_EXPLORATORY",result=us.to_dict()),remaining="descriptive or insufficient; source table retains all denominators",
            ambiguous_composition="Canonical comparison eligibility is false. The saved table marks three ambiguous-composition groups comparable (FR 54, UK-IE 2, US-CA 7); each has zero jointly known observations and no effect. Counts and findings are unchanged; the historical table is preserved."),
        boundaries=dict(source_id="BOUNDARY_RESULTS",keyed_output="boundary_annotations_v1.parquet",
            scope=["juice versus nectar/fruit drinks/smoothies","potato crisps versus popped/puffed/extruded potato snacks"],
            treatment="Independent commercial descriptors and ambiguity; nutrition describes consequences and never assigns identity",
            changed_beverage_assignments_n=int(a.juice_correction_applied.eq(True).sum()),
            current_juice_counts=a[a.analytical_format.eq("juice")].groupby("region").size().to_dict(),
            outside_family_flags="Not automatic canonical category reassignments"),
        juice_sensitivity=dict(source_id="FINAL_JUICE_SENSITIVITY",decision="CLOSED_HEADLINE_STABLE",removed_n=1090,retained_n=7468,
            predicate="FR & original_analytical_format != juice & juice_classification_confidence == MEDIUM within corrected juice",
            summary=sens[sens.group.eq("0.5<sugars<5")&sens.metric.eq("salt")].to_dict("records")),
        human_review=dict(output="human_observations_v1.parquet",n=12,role="QUALITATIVE_DIAGNOSTIC_EXAMPLES_ONLY",overrides_locked_claims=False),
        density=dict(treatment="Complementary per-weight and per-calorie views; no pooled replacement",source_id="DAIRY_REPORT"),
        control=dict(selected_k=5,role="COMPLETED_EXPLORATORY_REFERENCE_ONLY",source_id="HYPOTHESIS_CHECK",not_final_food_segments=True),
        deferred=dict(preparations="Numerical comparison deferred where reporting basis is unverified",alcohol="Excluded from nutritional segmentation; source records retained",
            uninvestigated_formats="Retained with no invented nutritional segmentation",evidence_gaps_source_id="POST_V1_BACKLOG",new_provider_calls_authorized=False))


def write_parquet(path,frame,input_hashes):
    data=pa.Table.from_pandas(frame,preserve_index=False)
    # Retain typed nullable source fields even when a selected column is entirely null.
    source_schema=pq.read_schema(MASTER)
    for i,field in enumerate(data.schema):
        if field.name in source_schema.names and field.type!=source_schema.field(field.name).type:
            target=source_schema.field(field.name)
            data=data.set_column(i,target,data.column(i).cast(target.type))
    md=dict(data.schema.metadata or {});md[b"analytical_version"]=rules.VERSION.encode();md[b"master_sha256"]=input_hashes["MASTER"].encode()
    pq.write_table(data.replace_schema_metadata(md),path)


def build():
    if FREEZE.exists():
        verify_frozen_release()
        raise SystemExit("Accepted v1 is frozen; overwrite refused. Run the verifier for a read-only integrity check. A future rebuild requires a new approved release version/destination.")
    OUT.mkdir(parents=True,exist_ok=True)
    hashes={key:digest(path) for key,path in INPUTS.items()}
    master_manifest=json.loads(INPUTS["MASTER_MANIFEST"].read_text(encoding="utf-8"))
    assert hashes["MASTER"]==master_manifest["master_sha256"]=="ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912"
    assert hashes["LOCKED_CLAIMS"]=="cd79f402e21b574710194e0cd741aee5d12e00677cd3ef37651d537747d23cda"
    print("Reading frozen master and accepted keyed layers...",flush=True)
    a,claims,claim_cols=read_inputs()
    product=assignments(a)
    write_parquet(OUT/"analytical_assignments_v1.parquet",product,hashes)
    write_parquet(OUT/"assessed_communication_v1.parquet",claims,hashes)
    human=pd.read_csv(INPUTS["HUMAN_DECISIONS"],dtype=str,keep_default_na=False)
    assert len(human)==12 and not human.duplicated(KEY+["proposition"]).any()
    write_parquet(OUT/"human_observations_v1.parquet",human,hashes)
    boundaries=boundary_annotations();write_parquet(OUT/"boundary_annotations_v1.parquet",boundaries,hashes)
    population_summary(a).to_csv(OUT/"population_summary_v1.csv",index=False,encoding="utf-8-sig")
    props=[c.removeprefix("claims_state_") for c in claim_cols if c.startswith("claims_state_") and c!="claims_state_energy_claim"]
    light=["product_scope_eligible","peer","subtype","h2_format_candidate","effective_type_code","dairy_format","savoury_format","analytical_format","juice_subformat","basis_group","comparable_liquid","profile_status"]
    qfields=["claims_"+prefix+p for p in props for prefix in ["claim_","state_"]]
    qfields += ["claims_"+p for p in ["energy_positioning","hydration_positioning","electrolyte_positioning"]]
    gate=["claims_matched","claims_analytical_eligible","claims_source_market_limitation","claims_evidence_cohort","claims_population_qa_note"]
    print("Rebuilding proposition-specific coverage from canonical assignments...",flush=True)
    coverage=rules.communication_coverage(a[KEY+light+qfields+gate],props)
    coverage.to_csv(OUT/"communication_coverage_v1.csv",index=False,encoding="utf-8-sig")
    write_json(OUT/"approved_findings_v1.json",approved_findings(a,coverage))
    assert hashes=={key:digest(path) for key,path in INPUTS.items()},"An accepted input changed during the build"
    outputs={}
    for path in sorted(OUT.iterdir()):
        if path.name=="manifest_v1.json":continue
        if path.suffix not in [".parquet",".csv",".json"]:continue
        info=dict(path=path.name,sha256=digest(path),bytes=path.stat().st_size)
        if path.suffix==".parquet":
            pf=pq.ParquetFile(path);info.update(rows=pf.metadata.num_rows,schema={f.name:str(f.type) for f in pf.schema_arrow})
        elif path.suffix==".csv":
            tab=pd.read_csv(path);info.update(rows=len(tab),columns=tab.columns.tolist())
        outputs[path.stem]=info
    manifest=dict(version=rules.VERSION,status="BUILT_PENDING_EQUIVALENCE_CHECK",scope="Friday consolidation; no publication",
        build_date="2026-11-19",planned_scope_date="2026-11-20",cutoff="2026-09-29",retrieved_at="2026-10-17T15:35:30.380864+00:00",
        governed_master_rows=382527,eligible_assignments=376845,key=KEY,publication="LOCAL_ONLY; no automatic GitHub/website publication",
        inputs={key:dict(path=relative(path),sha256=hashes[key]) for key,path in INPUTS.items()},
        evidence_references={key:dict(path=relative(path),sha256=digest(path),role="accepted research decision evidence; not a computation runner") for key,path in REFERENCES.items()},
        validation_references={key:dict(path=relative(path),sha256=digest(path),role="independent equivalence reference only; no research main executed") for key,path in VALIDATION_REFERENCES.items()},
        code={name:digest(HERE/name) for name in ["analytical_rules_v1.py","build_analytical_package_v1.py","verify_analytical_package_v1.py"]},
        packages=dict(python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,pyarrow=pa.__version__),outputs=outputs)
    write_json(OUT/"manifest_v1.json",manifest)
    write_documents(manifest)
    print("BUILT",len(product),"assignments;",len(claims),"assessments;",len(boundaries),"boundary annotations;",len(coverage),"coverage cells.",flush=True)
    return manifest


def write_documents(manifest):
    dictionary=["# Analytical package v1 — data dictionary",
        "Status: candidate pending Julia's acceptance. Wave 2: retrieved 17 October 2026; cutoff 29 September. All outputs are local analytical artifacts, separate from Streamlit and the unchanged master. The package does not publish a website.",
        "## Grain and joins",
        "Primary key everywhere is text `barcode` + `region` + `category`. Preserve leading zeros; never import GTINs as numbers. analytical_assignments_v1.parquet retains all 382,527 master assignments, including 5,682 outside current product scope. `product_scope_eligible` selects the 376,845 governed analytical assignments. No universal nutrition-complete population is created. A shared GTIN across regions/categories is a legitimate separate assignment.",
        "assessed_communication_v1.parquet is sparse: 12,161 matched locked evidence rows. Left-join it to assignments on the full key. An absent row means unknown/unassessed evidence, never a negative claim. The two locked ineligible salami assignments remain identifiable by source flags. Human observations join separately on key + proposition and must not overwrite locked fields. Boundary annotations join on key + boundary_family; their interpretations do not overwrite the accepted commercial layer.",
        "## Nutrition contract",
        "For each of energy/protein/fat/saturated_fat/carbohydrates/sugars/fibre/salt, keep original working field, its `_off_raw` source observation and `_missing` flag. The short metric name is the existing valid analytical value: working is within the accepted inclusive range (0–900 energy, 0–50 salt, 0–100 other nutrients), equals OFF raw, and its missing flag is zero. Otherwise it is null. These are inherited gates, not new corrections. Missing and recorded zero remain distinct. An accepted numerical value is not independent package verification.",
        "`*_validity` is the first displayed explanation in this precedence: WORKING_NULL; SOURCE_MISSING_FLAG; WORKING_SOURCE_DISAGREEMENT; OUTSIDE_ACCEPTED_RANGE; VALID_RECORDED. Source fields preserve overlapping reasons. Foods use per 100 g; beverages require their inherited comparable-liquid per-100-ml basis. Preparations/unverified bases remain deferred. Do not compare raw as-sold powder measurements with ready-to-drink liquids.",
        "protein_per100kcal = 100*protein/energy and fibre_per100kcal = 100*fibre/energy for valid energy >0. Zero denominators are undefined/null. energy_denominator_status distinguishes missing/invalid, zero, 0<E<10 and E>=10; it is not a universal exclusion. The cream/pudding rule specifically requires E>=10. Questionable sugar/energy combinations retain source observations; they are not proof of a novel recipe or a blanket reason to delete a product.",
        "## Commercial identity and profiles",
        "membership/subtype/confidence/reason/basis_group and beverage_view_segment preserve the approved baseline. cereal_* preserves original proposals and reviewed decisions separately; cereal_manual_review/manual_question is historical metadata, not a new blocking review queue. h2_format_candidate/effective_type_code retain the agreed cereal comparison population. savoury_format, construction/base_wording/flavour, corrected analytical_format and original_analytical_format, and juice_subformat/named_materials/concentrate_descriptor retain their accepted decision layers.",
        "commercial_format is a consolidated display identity; commercial_status retains resolved, other, unresolved, conflicting, comparability-concern and outside-scope distinctions. commercial_source and format_confidence identify the interpretation source. HIGH/MEDIUM is textual support, not verified pack identity. analytical_use_status keeps excluded alcohol, deferred basis and unresolved formats explicit; unresolved products can remain useful at broader category level.",
        "profile_status: IN_PROFILE; OTHER_MEASURABLE; REQUIRED_MEASUREMENT_UNKNOWN; NOT_INVESTIGATED_OR_NOT_APPLICABLE; OUTSIDE_PRODUCT_SCOPE. profile_id is populated only for IN_PROFILE. A null profile is not a negative health judgment or an inferred universal comparison arm. Thresholds are descriptive research conventions, not natural cluster boundaries or market prevalence. Granola uses the accepted H2 candidate population; potato crisps use the accepted savoury format, not boundary-driven reassignments."]
    dictionary.append("| Profile family | profile_id | Required rule |\n|---|---|---|\n"+"\n".join(f"| {k} | {rules.PROFILE_IDS[k]} | {v} |" for k,v in rules.PROFILE_RULES.items()))
    dictionary += ["## Presentation outcome resolution — required",
        "NOT_INVESTIGATED_OR_NOT_APPLICABLE is an internal catch-all, never a user-facing research conclusion. Recover the display outcome from the explicit metadata and the 33-row `approved_findings_v1.json.formulation.decisions` register. Resolve record scope/identity/basis first, then the applicable studied-format decision. A missing register match defaults to NOT_INVESTIGATED_WITHIN_FORMAT; it must never default to ‘no meaningful segment found’. This is a presentation interpretation of accepted metadata, not a new nutritional classification.",
        "| Priority / metadata predicate | Presentation outcome | Accepted decision reference |\n|---|---|---|\n"
        "| product_scope_eligible=false | OUTSIDE_PRODUCT_SCOPE | Source eligibility; not a research-negative finding |\n"
        "| membership=NO, subtype=OUT or commercial_status=OUTSIDE_REVIEWED_FORMAT | OUTSIDE_REVIEWED_FORMAT | Reviewed identity; retain broader source record |\n"
        "| analytical_use_status indicates alcohol exclusion | EXCLUDED_FROM_NUTRITIONAL_SCOPE | Alcohol |\n"
        "| commercial_status unresolved/conflicting/comparability-concern, or juice subtype unresolved/ambiguous/boundary concern | IDENTITY_OR_SUBTYPE_UNRESOLVED | Unresolved dairy desserts / saved commercial decisions |\n"
        "| analytical_use_status indicates deferred/unverified basis | DEFERRED_COMPARABILITY | Preparations |\n"
        "| profile_family exists | Use IN_PROFILE, OTHER_MEASURABLE or REQUIRED_MEASUREMENT_UNKNOWN directly | Five approved profiles; unknown measurement is not an uninvestigated format |\n"
        "| cereal: flakes; snacks: biscuit or tortilla/corn chips | RESEARCHED_NUTRITIONAL_VARIATION_NO_ADDITIONAL_PROFILE | Flakes / Biscuits / Tortilla/corn chips |\n"
        "| snacks: puffed/extruded; beverages: juice, smoothie, nectar, fruit drink, fermented soft drink, flavoured/coconut water | RESEARCHED_COMMERCIAL_DISTINCTION_NO_ADDITIONAL_PROFILE | Puffed/extruded snacks / Juice / Smoothies; nectars; fruit drinks; fermented soft drinks / Water; flavoured water; coconut water |\n"
        "| beverages: plant drink soy/almond | COMMERCIAL_BASE_DISTINCTION_WITH_VARIATION | Plant drinks |\n"
        "| snacks: wafer; identified dairy desserts outside cream/pudding/mousse/flan; iced tea/coffee/sports liquids; sparse oat/rice/coconut plant drinks | INVESTIGATED_INSUFFICIENT_EVIDENCE_FOR_SUBDIVISION | Wafers / Other identified dairy desserts / Iced tea; iced coffee; sports/electrolyte liquids / Plant drinks |\n"
        "| dairy: mousse/flan | RESEARCHED_VARIATION_AND_DENSITY_VIEW | Mousse; flan |\n"
        "| other savoury formats (including popcorn, pretzels, crackers, nuts/seeds and other identifiable forms); other cereal/dairy branches; other unmatched formats | NOT_INVESTIGATED_WITHIN_FORMAT | Other savoury formats / Other cereal and dairy branches; broad H1–H12 tests do not establish format-specific closure |",
        "Match on category plus the stored commercial_format/subtype/dairy_format/savoury_format fields; use juice_subformat and strict_comparable for composition uncertainty. Register branch names are scoped labels, not a GTIN join key. Granola-labelled records outside the accepted profile-family population are not automatically assigned that population's research outcome. Display NOT_COVERED_BY_ACCEPTED_PROFILE_POPULATION where applicable. Preserve the independent commercial, formulation and communication dimensions; insufficient claim coverage does not erase a nutritional profile. The safe fallback above covers all unlisted rows without inventing a negative result."]
    dictionary += ["## Locked communication and human evidence",
        "All `claims_*` columns retain the master source values and namespaces. For core proposition p: claims_claim_p is nullable source value; claims_state_p is locked observation state; claims_basis_p is its provenance basis. Source references, record_id, source_barcode/category, image URL, evidence cohort, saved core evidence JSON, QA notes, original outcomes and independent v6 fields remain attached. They concern assessed packaging evidence, not verified package-wide absence, product healthfulness or regulated claim compliance.",
        "Primary population claim status requires claims_matched=true and claims_analytical_eligible=true, with no source_market_limitation. Positive: value=true. Documented non-detection: value=false AND state=DOCUMENTED_NOT_DETECTED. HUMAN_CONFIRMED_NEGATIVE stays separate. UNCERTAIN, other assessed unknown, unassessed/ineligible and market-limited remain separate. Exact positive+documented non-detection is the known denominator; human examples are never added to it. Source gates preserve the distinction between no match and excluded evidence.",
        "Display locked sugar_free_claim as **sugar-related communication**. It includes saved no-added-sugar wording, literal sugar-free wording and model-assessment positives. Keep exact wording/provenance. energy_positioning is the approved derived positioning field; preserve original_energy_claim separately. Hydration/electrolyte positioning and v6 usability/status remain independent of core extraction.",
        "human_observations_v1.parquet preserves the 12 interpreted human submissions, including original and reconciled key, recorded/normalized review dates, source wording, interpretation and limits. Future-date flags remain; recorded dates are not silently corrected. This is a selected qualitative layer, not an expanded representative claims sample.",
        "## Summary and decision contracts",
        "population_summary_v1.csv is long-format: governed population, nutrient availability, commercial population and 15 approved profile cells. Its numeric zeros count observed zeros and never replace missing measurements. communication_coverage_v1.csv reproduces the accepted overlapping baseline/accepted/juice-detail cohorts and profile/comparison/unknown slices. Parent/child rows overlap: never sum them as unique-product counts. It exposes full, matched, usable-market, proposition-known and unknown denominators independently.",
        "approved_findings_v1.json carries the 33 accepted formulation decisions, supported UK soda comparison with its wording anomaly, selected H5 reuse, unresolved communication populations, conditional French muesli/NOVA association, exploratory US granola, bounded boundary scope, stable juice sensitivity, density/control context and deferrals. Its original effect/interval/p/q values are reused from accepted evidence, not refitted. Source IDs resolve through manifest_v1.json and ARTIFACT_INDEX.md.",
        "## Exact output schemas",
        "Types below are serialized Arrow/CSV types; the preceding contracts define meaning and permitted interpretation. Original source labels remain separately named rather than silently replaced."]
    for name,info in manifest["outputs"].items():
        if "schema" in info:
            dictionary += ["### "+info["path"],"| Field | Stored type |\n|---|---|\n"+"\n".join(f"| `{k}` | `{v}` |" for k,v in info["schema"].items())]
        elif "columns" in info:dictionary += ["### "+info["path"],"Columns: "+", ".join("`"+c+"`" for c in info["columns"])+"."]
    (HERE/"DATA_DICTIONARY.md").write_text("\n\n".join(dictionary)+"\n",encoding="utf-8")
    index=["# Analytical package v1 — artifact index","One authoritative candidate package; no source deletion, commit/push or website publication. [CHECK](CHECK.md) · [Data dictionary](DATA_DICTIONARY.md) · [Project methodology](../../SEGMENTATION.md)",
        "## Rerun and acceptance","Run from the repository: `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/build_analytical_package_v1.py`, then the sibling `verify_analytical_package_v1.py`. Routine build imports only analytical_rules_v1.py and ordinary Python libraries. The verifier independently compares against retained accepted evidence; it does not execute original research main functions. Sources and classifications stay frozen. Status is a candidate until Julia accepts the consolidated package.",
        "## Canonical outputs","| Artifact | Rows | Role |\n|---|---:|---|"]
    index[4:4]=["## Protected canonical code dependencies",
        "All three files are protected canonical dependencies and are included in the release manifest/freeze hashes. None is a housekeeping deletion or relocation candidate.\n\n"
        "| File | Role |\n|---|---|\n"
        "| [build_analytical_package_v1.py](build_analytical_package_v1.py) | Canonical builder and input/output contract; frozen-v1 overwrite guard |\n"
        "| [analytical_rules_v1.py](analytical_rules_v1.py) | Shared validity, commercial interpretation, profile and claim-state definitions |\n"
        "| [verify_analytical_package_v1.py](verify_analytical_package_v1.py) | Independent equivalence verifier; read-only frozen-release integrity check |"]
    roles={"analytical_assignments_v1":"Product-level commercial/nutrition/profile foundation; full master grain",
        "assessed_communication_v1":"Sparse locked communication; join by exact key, preserve unknown",
        "human_observations_v1":"Separate qualitative human evidence; no locked-field override",
        "boundary_annotations_v1":"Independent boundary descriptors/uncertainty; no source recategorization",
        "population_summary_v1":"Population and field-specific coverage/profile denominators",
        "communication_coverage_v1":"Reproduced exact-proposition evidence populations",
        "approved_findings_v1":"Accepted decisions/statistical context and limitations"}
    index[-1]+="\n"+"\n".join(f"| [{v['path']}](output/{v['path']}) | {v.get('rows','structured')} | {roles.get(k,'')} |" for k,v in manifest["outputs"].items())
    index += ["[Build/validation manifest](output/manifest_v1.json) supplies exact input, code and output identities/hashes. No output is a market-prevalence estimate.",
        "## Runtime inputs and evidence","All paths below are repository-relative. Runtime data inputs are necessary frozen decisions/evidence, not independent pipelines. Research reports retain the rationale, rejected splits and limitations. Do not delete or move them merely because the canonical rerun no longer imports their scripts.",
        ]
    evidence_rows=["| ID | Role | Path |","|---|---|---|"]
    for key,info in {**manifest["inputs"],**manifest["evidence_references"],**manifest["validation_references"]}.items():
        path=PROJECT/info["path"];target=Path(__import__("os").path.relpath(path,HERE)).as_posix()
        role="runtime accepted input" if key in manifest["inputs"] else "independent validation only" if key in manifest["validation_references"] else "research decision evidence/reference"
        evidence_rows.append(f"| {key} | {role} | [{info['path']}]({target}) |")
    index.append("\n".join(evidence_rows))
    index += ["## Retention boundary","No files are removed or retired here. Old exploration scripts, baseline checks and the pooled control remain research provenance and independent equivalence references. They are not imported by the routine canonical build. A future housekeeping proposal must identify exact replacements and protect hashed snapshots, approved manual decisions and locked source evidence. Production, Streamlit, ingestion, OCR/LLM and the Lovable repository remain untouched."]
    index += ["## approved_findings_v1.json — Lovable contract",
        "| Top-level key | Structure and interpretation |\n|---|---|\n"
        "| version, status, unit, hierarchy, limitations | Release metadata, exact assignment grain, three-level architecture and global interpretation limits |\n"
        "| formulation | source_id plus decisions array (33 accepted register rows). Use branch/decision/scope_note with product metadata to distinguish studied variation, insufficient evidence and uninvestigated formats; see DATA_DICTIONARY.md presentation priority table |\n"
        "| communication | Source ID; sugar-related display label; supported_uk_soda result and focused_exception; descriptive granola; unresolved_profile_comparisons; reused_H5; qualified other_hypotheses. Each result retains its own denominators, units and evidence role |\n"
        "| processing | Conditional french_muesli, exploratory us_granola, remaining-evidence limits and the documented ambiguous-composition metadata exception |\n"
        "| boundaries | Source ID, keyed output, bounded families, treatment, corrected juice counts and outside-family cautions; no automatic source recategorization |\n"
        "| juice_sensitivity | Source ID, closed decision, exact exclusion predicate, removed/retained counts and saved summary rows |\n"
        "| human_review | Separate keyed output, n=12, qualitative role and overrides_locked_claims=false |\n"
        "| density, control, deferred | Complementary density view, completed k=5 reference and explicit alcohol/preparation/evidence deferrals |",
        "Resolve source_id/evidence_gaps_source_id through manifest inputs/evidence_references/validation_references. Relative evidence paths inside copied research rows remain relative to their original source artifact, not output/. Profile IDs are defined in DATA_DICTIONARY.md. Do not sum overlapping coverage cohorts or infer claim absence from a missing sparse-table join. Interpret the internal catch-all profile status only through the documented presentation decision priority; unknown/uninvestigated is not a negative research conclusion."]
    if manifest.get("status")=="ACCEPTED_FROZEN":
        dictionary=[s.replace("Status: candidate pending Julia's acceptance.","Status: accepted frozen v1.") for s in dictionary]
        (HERE/"DATA_DICTIONARY.md").write_text("\n\n".join(dictionary)+"\n",encoding="utf-8")
        index=[s.replace("One authoritative candidate package","Accepted frozen v1 package").replace("Status is a candidate until Julia accepts the consolidated package.",
            "Accepted v1 is frozen: the builder refuses overwrite; the verifier checks integrity read-only. A new build needs an approved new version/destination.") for s in index]
        index += ["[Release freeze receipt](RELEASE_FREEZE_v1.json) protects canonical code, data, manifest and release documentation. Historical source and evidence paths remain protected by the accepted manifest."]
    (HERE/"ARTIFACT_INDEX.md").write_text("\n\n".join(index)+"\n",encoding="utf-8")


if __name__=="__main__":build()
