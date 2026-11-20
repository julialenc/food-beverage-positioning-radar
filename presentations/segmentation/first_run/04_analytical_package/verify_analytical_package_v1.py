"""Independent equivalence acceptance for the canonical analytical package.

Reads historical references but calls no original research main, EDA, model,
provider or ingestion function. Writes this stage's CHECK/manifest/log only.
"""
from pathlib import Path
import ast
import importlib.util
import json
import re
import unicodedata
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import analytical_rules_v1 as rules
import build_analytical_package_v1 as build

HERE=build.HERE;OUT=build.OUT;KEY=rules.KEY


def equivalent(a,b,keys,columns=None):
    if columns:a=a[columns];b=b[columns]
    a=a.sort_values(keys).reset_index(drop=True);b=b.sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-11,atol=1e-11)


def load_module(path):
    spec=importlib.util.spec_from_file_location("reference_"+path.stem,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


def reference_classifier(path,names,constants=()):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:nodes.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in node.targets):nodes.append(node)
    namespace=dict(re=re,unicodedata=unicodedata)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),namespace)
    return namespace["classify"]


def keymap(groups):
    result={}
    for family,branch,slice_name,g in groups:
        for region,z in g.groupby("region"):
            key=(family,branch,slice_name,region)
            assert key not in result,key
            result[key]=frozenset(map(tuple,z[KEY].to_numpy()))
    return result


def organic_counts(a):
    part=rules.organic_partition(a)
    states=rules.claim_states(part,"organic_claim")
    part["org_positive"]=states["positive_n"];part["org_negative"]=states["documented_non_detection_n"]
    part["nova_valid"]=part.nova_group.isin([1,2,3,4])
    rows=[]
    for (category,form,region),g in part.groupby(["category","commercial_type","region"]):
        pos=g.org_positive;neg=g.org_negative;nova=g.nova_valid
        rows.append(dict(category=category,commercial_type=form,region=region,full_commercial_n=len(g),
            organic_positive_n=int(pos.sum()),organic_documented_non_detection_n=int(neg.sum()),organic_known_n=int((pos|neg).sum()),
            organic_unknown_n=int((~(pos|neg)).sum()),nova_known_n=int(nova.sum()),nova_missing_n=int(g.nova_group.isna().sum()),
            nova_invalid_n=int((g.nova_group.notna()&~nova).sum()),jointly_known_n=int(((pos|neg)&nova).sum()),
            joint_organic_positive_n=int((pos&nova).sum()),joint_non_detection_n=int((neg&nova).sum()),
            organic_positive_nova4_n=int((pos&nova&g.nova_group.eq(4)).sum()),non_detection_nova4_n=int((neg&nova&g.nova_group.eq(4)).sum()),
            comparable_type=bool(g.comparison_eligible_type.all())))
    return pd.DataFrame(rows),part


def verify():
    if build.FREEZE.exists():
        receipt,manifest=build.verify_frozen_release()
        print("PASS accepted frozen release integrity; no files written. Release digest:",receipt["release_digest"],flush=True)
        return manifest["validation"]
    manifest=json.loads((OUT/"manifest_v1.json").read_text(encoding="utf-8"))
    for key,info in {**manifest["inputs"],**manifest["evidence_references"],**manifest["validation_references"]}.items():
        assert build.digest(build.PROJECT/info["path"])==info["sha256"],("changed accepted source",key)
    for name,expected in manifest["code"].items():assert build.digest(HERE/name)==expected,("code changed after build",name)
    for key,info in manifest["outputs"].items():assert build.digest(OUT/info["path"])==info["sha256"],("changed output",key)
    a=pd.read_parquet(OUT/"analytical_assignments_v1.parquet")
    assert len(a)==382527 and not a.duplicated(KEY).any() and a.product_scope_eligible.sum()==376845
    assert a.barcode.map(lambda x:isinstance(x,str)).all() and a.barcode.str.startswith("0").any()
    fields=KEY+build.SOURCE_COLS+[f+s for f in rules.RAW.values() for s in ["","_off_raw","_missing"]]
    raw=pq.read_table(build.MASTER,columns=fields).to_pandas()
    equivalent(a,raw,KEY,fields)
    baseline=pd.read_csv(build.EDA/"nutrient_availability.csv").query("subtype == 'ALL'")
    checks={"master_rows":len(a),"eligible_assignments":int(a.product_scope_eligible.sum()),"outside_scope_retained":int((~a.product_scope_eligible).sum())}
    for metric in rules.RAW:
        expected=baseline.set_index(["region","category"])[metric+"_valid_n"].sort_index()
        actual=a[a.product_scope_eligible].groupby(["region","category"])[metric].count().sort_index()
        assert actual.equals(expected),metric
    checks["nutrient_validity_cells"]=96
    saved=pd.read_parquet(build.INPUTS["JUICE_DECISIONS"])
    joined=saved.merge(a[KEY+list(rules.RAW)],on=KEY,validate="one_to_one",suffixes=("_reference","_canonical"))
    for metric in ["energy","sugars","salt","protein","fat","fibre"]:
        pd.testing.assert_series_equal(joined[metric+"_reference"],joined[metric+"_canonical"],check_names=False,check_dtype=False)
    assert len(joined)==13861
    checks["corrected_juice_keys_and_nutrition"]=len(joined)
    # Independent retained source functions, not the new shared implementation.
    dairy=reference_classifier(build.LENSES/"02_nutrient_density/dairy_dessert_formulations_v1.py",["norm","cues","classify"],["PATTERNS","FLAG"])
    biscuits=reference_classifier(build.L1/"biscuits_and_wafers_v1.py",["norm","classify"])
    dessert=a[a.peer&a.subtype.eq("DAIRY_DESSERT")]
    assert [dairy(r) for r in dessert.itertuples()]==dessert.dairy_format.tolist()
    biscuit=a[a.peer&a.subtype.eq("BISCUITS_WAFERS")]
    pairs=[biscuits(r) for r in biscuit.itertuples()]
    assert pairs==list(zip(biscuit.biscuit_format,biscuit.biscuit_construction))
    checks["dairy_classifier_assignments"]=len(dessert);checks["biscuit_classifier_assignments"]=len(biscuit)
    ref=load_module(build.L3/"communication_coverage_v1.py")
    fields=KEY+list(rules.RAW)+["membership","subtype","confidence","basis_group","cereal_bar_review_flag","peer"]
    source_frame=a.loc[a.product_scope_eligible,fields].copy()
    reference=keymap(ref.populations(source_frame));canonical=keymap(rules.coverage_populations(a))
    assert reference.keys()==canonical.keys(),"Coverage cohort identities differ"
    for key in reference:assert reference[key]==canonical[key],("product-level cohort mismatch",key)
    checks["exact_cohort_key_sets"]=len(reference)
    cov=pd.read_csv(OUT/"communication_coverage_v1.csv")
    old_cov=pd.read_csv(build.L3/"communication_coverage_v1.csv")
    equivalent(cov,old_cov,["cohort_family","branch","slice","region","proposition"])
    checks["communication_coverage_cells"]=len(cov)
    summary=pd.read_csv(OUT/"population_summary_v1.csv")
    p=summary[summary.record_kind.eq("approved profile")].copy()
    old=pd.read_csv(build.INPUTS["FORMULATION_DECISIONS"]);old=old[old.decision.eq("approved descriptive profile")].copy()
    old["profile_family"]=old.branch.replace({"Granola":"granola","Cream/pudding":"dessert cream/pudding","Potato crisps":"potato crisps"})
    old=old.rename(columns={"starting_n":"population_n"})
    cols=["region","profile_family","population_n","eligible_n","retained_n","unknown_required_n"]
    equivalent(p,old,["region","profile_family"],cols)
    for family,expected in rules.EXPECTED_PROFILES.items():assert p[p.profile_family.eq(family)].set_index("region").reindex(rules.REGIONS).retained_n.tolist()==expected
    checks["approved_regional_profile_cells"]=len(p)
    source=pq.read_table(build.MASTER,columns=KEY+[n for n in pq.read_schema(build.MASTER).names if n.startswith("claims_")]).to_pandas()
    claims=pd.read_parquet(OUT/"assessed_communication_v1.parquet")
    cols=KEY+[c for c in source if c.startswith("claims_")]
    equivalent(claims,source[source.claims_matched.eq(True)],KEY,cols)
    checks["locked_assessments_preserved"]=len(claims)
    states=pd.read_csv(build.INPUTS["HUMAN_DECISIONS"],dtype=str,keep_default_na=False)
    human=pd.read_parquet(OUT/"human_observations_v1.parquet")
    equivalent(human,states,["review_id"]);assert len(human)==12
    assert set(map(tuple,human[KEY].to_numpy()))<=set(map(tuple,a[KEY].to_numpy()))
    checks["separate_human_observations"]=len(human)
    bound=pd.read_parquet(OUT/"boundary_annotations_v1.parquet")
    original=pd.read_parquet(build.INPUTS["BOUNDARY_EVIDENCE"]);original=original[original.record_kind.eq("boundary evidence")]
    equivalent(bound,original,KEY+["boundary_family"],bound.columns.tolist())
    assert not bound.duplicated(KEY+["boundary_family"]).any()
    assert set(map(tuple,bound[KEY].to_numpy()))<=set(map(tuple,a[KEY].to_numpy()))
    checks["unchanged_boundary_annotations"]=len(bound)
    # Reconcile every organic/NOVA comparison denominator without rerunning statistics.
    org_fields=KEY+["product_name","off_categories","product_scope_eligible","peer","membership","subtype","dairy_format","biscuit_format","savoury_format","analytical_format","juice_subformat","nova_group"]
    source_org=source[[c for c in source if c in KEY+["claims_matched","claims_analytical_eligible","claims_source_market_limitation","claims_claim_organic_claim","claims_state_organic_claim"]]]
    org=a[org_fields].merge(source_org,on=KEY,validate="one_to_one")
    counts,part=organic_counts(org)
    approved=pd.read_csv(build.INPUTS["PROCESSING_RESULTS"])
    equivalent(counts,approved,["category","commercial_type","region"],[c for c in counts if c!="comparable_type"])
    flags=counts.merge(approved[["category","commercial_type","region","comparable_type","risk_difference_pp"]],
        on=["category","commercial_type","region"],suffixes=("_canonical","_recorded"),validate="one_to_one")
    exceptions=flags[flags.comparable_type_canonical.ne(flags.comparable_type_recorded)]
    assert exceptions.commercial_type.eq("ambiguous composition").all()
    assert exceptions.comparable_type_canonical.eq(False).all() and exceptions.comparable_type_recorded.eq(True).all()
    assert exceptions.jointly_known_n.eq(0).all() and exceptions.risk_difference_pp.isna().all()
    checks["documented_comparability_metadata_exceptions"]=len(exceptions)
    checks["organic_nova_population_cells"]=len(counts)
    # Density formula, missing/zero distinction and sparse-claims negative guard.
    assert a.loc[a.energy.isna()|a.energy.eq(0),["protein_per100kcal","fibre_per100kcal"]].isna().all().all()
    sample=pd.DataFrame(dict(claims_matched=[False,True,True,True],claims_analytical_eligible=[None,True,True,True],
        claims_source_market_limitation=[None,"","",""],claims_claim_organic_claim=[None,False,False,True],
        claims_state_organic_claim=[None,"UNCERTAIN","DOCUMENTED_NOT_DETECTED","DIRECT_POSITIVE"]))
    statuses=rules.claim_states(sample,"organic_claim")
    assert statuses["unassessed_n"].tolist()==[True,False,False,False]
    assert statuses["documented_non_detection_n"].tolist()==[False,False,True,False]
    assert statuses["uncertain_n"].tolist()==[False,True,False,False]
    checks["claim_unknown_and_zero_denominator_guards"]="PASS"
    decisions=json.loads((OUT/"approved_findings_v1.json").read_text(encoding="utf-8"))
    assert len(decisions["formulation"]["decisions"])==33 and decisions["control"]["selected_k"]==5
    assert decisions["communication"]["display_label_for_sugar_free_claim"]=="sugar-related communication"
    assert decisions["human_review"]["overrides_locked_claims"] is False
    for info in manifest["inputs"].values():assert build.digest(build.PROJECT/info["path"])==info["sha256"]
    for path in HERE.glob("*.py"):ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    check_links()
    checks["input_output_hashes_and_document_links"]="PASS"
    manifest["status"]="VALIDATED_CANDIDATE_AWAITING_JULIA_REVIEW";manifest["validation"]=checks
    write_check(checks,p,manifest)
    manifest["documentation"]={name:build.digest(HERE/name) for name in ["DATA_DICTIONARY.md","ARTIFACT_INDEX.md","CHECK.md"]}
    build.write_json(OUT/"manifest_v1.json",manifest)
    print("PASS",json.dumps(checks),flush=True)
    return checks


def check_links():
    for name in ["DATA_DICTIONARY.md","ARTIFACT_INDEX.md"]:
        text=(HERE/name).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)",text):
            target=target.strip("<>").split("#")[0]
            if "://" not in target and target and target!="CHECK.md":assert (HERE/target).exists(),(name,target)


def write_check(checks,profiles,manifest):
    table="| Profile | FR | UK/IE | US/CA |\n|---|---:|---:|---:|\n"+"\n".join(
        "| "+family+" | "+" | ".join(str(int(v)) for v in profiles[profiles.profile_family.eq(family)].set_index("region").reindex(rules.REGIONS).retained_n)+" |" for family in rules.PROFILE_IDS)
    text=["# Friday analytical consolidation — CHECK v1",
        "**PASS — validated candidate for Julia's review.** Friday 20 November scope, executed 19 November 2026. No deletions, historical reruns, model fitting, provider calls, GitHub push, Streamlit changes or Lovable integration. Master and locked evidence are unchanged.",
        "## What changed","One shared rule implementation and one build command now produce canonical keyed assignments, sparse communication, separate human observations, boundary annotations, population/evidence summaries and accepted findings. Routine execution reads frozen master and approved decisions; it does not import research runners or repeat preprocessing/EDA/models. The separate verifier uses retained decision evidence for independent equivalence. [Artifact index](ARTIFACT_INDEX.md) · [Data dictionary](DATA_DICTIONARY.md) · [Manifest](output/manifest_v1.json).",
        "## Populations and profiles",
        "382,527 master assignments are retained; 376,845 are product-scope eligible and 5,682 remain explicitly outside scope. All keys preserve barcode strings and region/category assignments. 12,161 locked pack-assessment rows remain a sparse separate layer, including ineligible source observations. Unmatched records retain unknown communication. All 12 human observations remain qualitative and separate.",table,
        "These five profiles reproduce the accepted 15 regional cells and exact product memberships. They are descriptive research rules, not natural clusters or market-prevalence estimates. Other formats retain commercial distinctions, continuous variation, uncertainty, deferrals or uninvestigated status. The k=5 control remains a completed reference, not final food segmentation.",
        "## Evidence and interpretation carried forward",
        "The corrected juice assignments remain FR 8,558 / UK-IE 798 / US-CA 4,505 with original and reviewed labels, textual confidence and reasons. The final 1,090-record French sensitivity remains closed and stable; no record is deleted. HIGH/MEDIUM does not mean independently verified identity. The discarded French fruit-drink regional contrast stays withdrawn.",
        "UK/Irish soda retains the selected 28/43 versus 1/43 comparison under **sugar-related communication**, with saved wording and the Cloudy Lemonade exception. Granola overlays remain descriptive; sparse cream/pudding, crisp and energy-drink communication remains unresolved. H8 stays descriptive and H10 stays US/Canada granola only. H11 is not a marketing-opportunity estimate.",
        "French muesli organic × recorded NOVA 4 stays conditional on selected jointly known observations (6/24 versus 25/48). No healthfulness, causality, claim-compliance or market-prevalence inference. NOVA and pack communication are overlays, not nutritional clustering requirements. Preparations retain unverified basis; alcohol stays outside nutritional segmentation while source records remain.",
        "## Equivalence and integrity",
        "| Check | Result |\n|---|---:|\n"+"\n".join(f"| {k} | {v} |" for k,v in checks.items()),
        "Verification compares every raw nutrition/source field, exact saved juice nutrition, all derived profile populations and overlapping coverage cohort key sets, all 13,602 proposition-specific coverage cells, all 377 organic/NOVA population counts, accepted classifier outputs, all matched claim source fields, 12 human rows, 32,336 boundary annotations and frozen input hashes. The accepted statistical results are reused without refitting; their supporting populations are verified. Missing and recorded-zero guards pass.",
        "**Documented metadata exception:** the historical organic/NOVA table marks three ambiguous-composition groups as comparable (54 FR, 2 UK/IE and 7 US/CA assignments). Canonical rules correctly mark ambiguous composition non-comparable under the approved uncertainty framework. Each group has zero joint organic/NOVA observations and no reported effect; no membership, denominator or substantive finding changes. The original table and evidence are preserved. This is not a new nutritional classification or comparison.",
        "## Reproduce, review and stop",
        "From the repository: `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/build_analytical_package_v1.py`, then `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/verify_analytical_package_v1.py`.",
        "Julia's next decision is acceptance of this consolidated analytical contract and its evidence/uncertainty presentation. No new research decision, segment count or evidence expansion is requested. Keep current research files and frozen records; propose exact housekeeping candidates only after acceptance. The package is local and has not been published or connected to the Lovable prototype. **STOP for review.**"]
    (HERE/"CHECK.md").write_text("\n\n".join(text)+"\n",encoding="utf-8")
    (HERE/"logs.md").write_text("# Consolidation log\n\n- 19 November 2026: built and independently verified the Friday v1 analytical candidate. See CHECK.md and output/manifest_v1.json for exact results, source/code/output identities and schemas. No files deleted; no commit/push or publication.\n",encoding="utf-8")
    (HERE/"learnings.md").write_text("# Consolidation learnings\n\n- A canonical rerun can reuse frozen commercial decisions and approved rules without executing exploratory research.\n- Runtime inputs, independent equivalence references and research decision evidence have different retention roles. Removing a research script from runtime does not authorize deleting it.\n- Full master grain, question-specific profile eligibility and sparse separate claims preserve uncertainty; a missing join is never a negative claim.\n- Existing prototypes should consume the accepted data contract after analytical acceptance.\n",encoding="utf-8")


if __name__=="__main__":verify()
