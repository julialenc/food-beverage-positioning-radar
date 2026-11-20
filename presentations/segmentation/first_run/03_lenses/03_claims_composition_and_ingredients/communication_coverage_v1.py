"""Tuesday coverage pass. Reuse accepted identity and formulation rules; fit no models."""
from pathlib import Path
import importlib.util
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EDA=ROOT.parent/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import KEY, MASTER, read_master

def load_module(path):
    spec=importlib.util.spec_from_file_location(path.stem,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

def populations(df):
    meta=pd.read_csv(EDA/"subtype_assignments.csv",dtype=str,usecols=KEY+["product_name","off_categories"])
    cohorts=[]
    def add(family,branch,frame,split=None,measurable=None):
        cohorts.append((family,branch,"commercial population",frame))
        if split is not None:
            known=measurable.fillna(False)
            cohorts.extend([(family,branch,"retained profile",frame[known&split.fillna(False)]),
                            (family,branch,"other measurable",frame[known&~split.fillna(False)]),
                            (family,branch,"required measurement unknown",frame[~known])])
    # Baseline branches remain coverage context, not approved new segment definitions.
    for (category,subtype),g in df[df.peer].groupby(["category","subtype"]):
        if subtype=="ALCOHOLIC_STYLE":continue
        add("baseline",category+"/"+subtype,g)
    cereal=pd.read_parquet(EDA.parent/"01_nutritional_composition/lens1_cereal_master_v1.parquet")
    for form in ["GRANOLA","FLAKES"]:
        g=df.merge(cereal[cereal.h2_format_candidate.eq(True)&cereal.effective_type_code.eq(form)][KEY],on=KEY,validate="one_to_one")
        if form=="GRANOLA":
            add("accepted","granola",g,g.sugars.le(14)&g.protein.ge(11),g[["sugars","protein"]].notna().all(axis=1))
        else:add("accepted","flakes",g)
    g=df[df.peer&df.subtype.eq("DAIRY_DESSERT")].merge(meta,on=KEY,validate="one_to_one")
    module=load_module(ROOT/"02_nutrient_density/dairy_dessert_formulations_v1.py")
    g["detail"]=g.apply(module.classify,axis=1)
    for form,d in g.groupby("detail"):
        if form=="dessert cream / pudding":
            add("accepted","dessert cream/pudding",d,d.protein.ge(8)&d.energy.le(110),d.protein.notna()&d.energy.ge(10))
        else:add("accepted","dairy dessert/"+form,d)
    for name,col,valid in [("savoury_snack_assignments_v1.parquet","savoury_format","per_100g_food"),
                           ("beverage_assignments_v1.parquet","analytical_format","per_100ml_liquid"),
                           ("juice_assignments_v1.parquet","juice_subformat","per_100ml_liquid")]:
        a=pd.read_parquet(ROOT/"01_nutritional_composition"/name)
        labels=[col]
        if "beverage" in name:labels+=["comparable_liquid","retained_profile"]
        if "savoury" in name:labels+=["formulation_profile"]
        g=df.merge(a[KEY+labels],on=KEY,validate="one_to_one")
        for form,d in g.groupby(col):
            if form=="outside screen" or form.startswith("alcohol:"):continue
            family="juice detail" if "juice" in name else "accepted"
            branch=("juice/" if "juice" in name else "" if form in ["potato crisps","soda","energy drink"] else
                    "snacks/" if "savoury" in name else "beverages/")+form
            if form=="potato crisps":
                d=d[d.basis_group.eq(valid)]
                add(family,branch,d,d.fat.le(20),d.fat.notna())
            elif form in ["soda","energy drink"]:
                d=d[d.comparable_liquid]
                add(family,branch,d,d.sugars.le(.5),d.sugars.notna())
            else:add(family,branch,d)
    return cohorts

def main():
    df,_=read_master()
    names=pq.ParquetFile(MASTER).schema_arrow.names
    props=[n.removeprefix("claims_state_") for n in names if n.startswith("claims_state_") and n!="claims_state_energy_claim"]
    extra=[n for prop in props for n in ["claims_claim_"+prop,"claims_state_"+prop] if n not in df]
    raw=pq.read_table(MASTER,columns=KEY+extra).to_pandas()
    df=df.merge(raw,on=KEY,validate="one_to_one")
    assert len(df)==376845
    cohorts=populations(df)
    rows=[]
    for family,branch,slice_name,frame in cohorts:
        for region,g in frame.groupby("region"):
            gate=g.assessed_layer
            limited=gate&g.claims_source_market_limitation.fillna("").ne("")
            usable=gate&~limited
            for prop in props+["energy_positioning","hydration_positioning","electrolyte_positioning"]:
                functional=prop in ["energy_positioning","hydration_positioning","electrolyte_positioning"]
                if functional and not g.category.eq("beverages").all():continue
                flag=g["claims_"+prop] if functional else g["claims_claim_"+prop]
                pos=usable&flag.eq(True).fillna(False)
                if functional:
                    neg=usable&flag.eq(False).fillna(False); human=pd.Series(False,index=g.index)
                    uncertain=pd.Series(False,index=g.index)
                else:
                    state=g["claims_state_"+prop]
                    neg=usable&flag.eq(False).fillna(False)&state.eq("DOCUMENTED_NOT_DETECTED").fillna(False)
                    human=usable&flag.eq(False).fillna(False)&state.eq("HUMAN_CONFIRMED_NEGATIVE").fillna(False)
                    uncertain=usable&state.eq("UNCERTAIN").fillna(False)
                unknown=usable&~(pos|neg|human|uncertain)
                known=int(pos.sum()+neg.sum())
                row=dict(cohort_family=family,category=g.category.iloc[0],branch=branch,slice=slice_name,region=region,proposition=prop,
                    population_n=len(g),matched_eligible_n=int(gate.sum()),usable_market_n=int(usable.sum()),
                    positive_n=int(pos.sum()),documented_non_detection_n=int(neg.sum()),human_negative_n=int(human.sum()),
                    uncertain_n=int(uncertain.sum()),other_unknown_assessed_n=int(unknown.sum()),
                    unassessed_n=int((~gate).sum()),market_limited_n=int(limited.sum()),known_primary_n=known,
                    known_pct_of_population=100*known/len(g),historical_reuse_n=int((usable&g.claims_evidence_cohort.eq("historical_dairy_reuse")).sum()),
                    qa_note_n=int((usable&g.claims_population_qa_note.fillna("").ne("")).sum()),
                    two_arm_floor=bool(pos.sum()>=20 and neg.sum()>=20))
                assert sum(row[k] for k in ["positive_n","documented_non_detection_n","human_negative_n","uncertain_n",
                                          "other_unknown_assessed_n","unassessed_n","market_limited_n"])==len(g)
                rows.append(row)
    result=pd.DataFrame(rows)
    assert not result.duplicated(["cohort_family","branch","slice","region","proposition"]).any()
    # Commercial cohort counts and profile partition must reproduce the closed register.
    for branch,expected in [("granola",[251,94,121]),("dessert cream/pudding",[27,15,1]),
                            ("potato crisps",[100,90,53]),("soda",[713,255,96]),("energy drink",[153,88,97])]:
        test=result[(result.cohort_family=="accepted")&(result.branch==branch)&(result.slice=="retained profile")&result.proposition.eq("protein_claim")]
        assert test.sort_values("region").population_n.tolist()==expected,(branch,test.population_n.tolist())
    result.to_csv(HERE/"communication_coverage_v1.csv",index=False,encoding="utf-8-sig")
    print("PASS",len(result),"proposition-specific cells; closed profile counts, primary states and keyed joins.")
if __name__=="__main__":main()
