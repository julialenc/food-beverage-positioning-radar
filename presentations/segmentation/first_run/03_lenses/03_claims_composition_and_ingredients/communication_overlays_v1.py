"""Wednesday overlays from frozen Tuesday coverage and existing H5-H11 results."""
from pathlib import Path
import hashlib
import json
import re
import unicodedata

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import fisher_exact,norm

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
KEY=["barcode","region","category"]
MASTER=ROOT.parent/"01_ingestion/05_master_parquet/output/master_products.parquet"
COVERAGE=HERE/"communication_coverage_v1.csv"
PLAN=[("granola","protein_claim"),("granola","fibre_claim"),("granola","organic_claim"),
      ("soda","sugar_free_claim"),("energy drink","sugar_free_claim"),("dessert cream/pudding","protein_claim"),
      ("potato crisps","reduced_fat_claim")]
def digest(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def wilson(k,n):
    if not n:return np.nan,np.nan
    z=norm.ppf(.975);p=k/n;den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return centre-half,centre+half
def diff_interval(a,n,b,m):
    p,q=a/n,b/m;al,ah=wilson(a,n);bl,bh=wilson(b,m)
    return p-q-np.sqrt((p-al)**2+(bh-q)**2),p-q+np.sqrt((ah-p)**2+(q-bl)**2)
def main():
    manifest=json.loads((MASTER.parent/"manifest.json").read_text())
    assert digest(MASTER)==manifest["master_sha256"]
    coverage=pd.read_csv(COVERAGE)
    rows=[]
    states=["positive_n","documented_non_detection_n","human_negative_n","uncertain_n",
            "other_unknown_assessed_n","unassessed_n","market_limited_n"]
    for branch,prop in PLAN:
        frame=coverage[(coverage.cohort_family=="accepted")&(coverage.branch==branch)&coverage.proposition.eq(prop)]
        for r in frame.to_dict("records"):
            if r["slice"]=="commercial population":continue
            assert sum(r[k] for k in states)==r["population_n"]
            lo,hi=wilson(r["positive_n"],r["known_primary_n"])
            rows.append(dict(record_kind="coverage",**r,observed_positive_fraction=r["positive_n"]/r["known_primary_n"] if r["known_primary_n"] else np.nan,lo=lo,hi=hi))
        for region in ["FR","UK-IE","US-CA"]:
            pair=frame[frame.region.eq(region)].set_index("slice")
            if not {"retained profile","other measurable"}.issubset(pair.index):continue
            a,b=pair.loc["retained profile"],pair.loc["other measurable"]
            n,m=int(a.known_primary_n),int(b.known_primary_n)
            if not min(n,m):continue
            x,y=int(a.positive_n),int(b.positive_n)
            sufficient=min(n,m)>=20
            lo,hi=diff_interval(x,n,y,m) if sufficient else (np.nan,np.nan)
            supported=branch=="soda" and region=="UK-IE"
            rows.append(dict(record_kind="comparison",branch=branch,region=region,proposition=prop,
                 profile_population_n=a.population_n,other_population_n=b.population_n,profile_known_n=n,other_known_n=m,
                 profile_positive_n=x,other_positive_n=y,effect=x/n-y/m if sufficient else np.nan,lo=lo,hi=hi,
                 p=fisher_exact([[x,n-x],[y,m-y]])[1] if supported else np.nan,
                 analysis_role="supported selected-assessment comparison" if supported else
                    "descriptive selected-assessment association" if sufficient else "unresolved; insufficient assessed evidence"))
    # Reproduce exact frozen cohorts needed for provenance; no broad population rebuild.
    cereal=pd.read_parquet(ROOT.parent/"02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_master_v1.parquet")
    granola=cereal[cereal.h2_format_candidate.eq(True)&cereal.effective_type_code.eq("GRANOLA")].copy()
    for name in ["sugars_100g","protein_100g"]:
        granola[name]=granola[name].where(granola[name].eq(granola[name+"_off_raw"])&granola[name+"_missing"].eq(0)&granola[name].between(0,100))
    granola=granola.dropna(subset=["sugars_100g","protein_100g"])
    granola["branch"]="granola"
    granola["slice"]=np.where(granola.sugars_100g.le(14)&granola.protein_100g.ge(11),"retained profile","other measurable")
    beverage=pd.read_parquet(ROOT/"01_nutritional_composition/beverage_assignments_v1.parquet")
    beverage=beverage[beverage.comparable_liquid&beverage.analytical_format.isin(["soda","energy drink"])&beverage.retained_profile.notna()].copy()
    beverage["branch"]=beverage.analytical_format
    beverage["slice"]=np.where(beverage.retained_profile.eq("very-low-sugars formulation"),"retained profile","other measurable")
    keys=pd.concat([granola[KEY+["branch","slice"]],beverage[KEY+["branch","slice"]]],ignore_index=True)
    assert not keys.duplicated(KEY).any()
    props=["protein_claim","fibre_claim","organic_claim","sugar_free_claim"]
    fields=KEY+["product_name","off_categories","sugars_100g","sugars_100g_off_raw","sugars_100g_missing","energy_kcal","claims_matched","claims_analytical_eligible",
        "claims_source_market_limitation","claims_evidence_cohort","claims_image_url","claims_original_overall_outcome","claims_core_claim_evidence_json"]+[
        "claims_"+prefix+prop for prop in props for prefix in ["claim_","state_","basis_"]]
    source=pq.read_table(MASTER,columns=fields).to_pandas()
    data=keys.merge(source,on=KEY,validate="one_to_one")
    gate=data.claims_matched.eq(True)&data.claims_analytical_eligible.eq(True)&data.claims_source_market_limitation.fillna("").eq("")
    for branch,prop in PLAN:
        if branch not in ["granola","soda","energy drink"]:continue
        g=data[gate&data.branch.eq(branch)]
        for (region,slice_name,basis,state),group in g.groupby(["region","slice","claims_basis_"+prop,"claims_state_"+prop],dropna=False):
            rows.append(dict(record_kind="provenance",branch=branch,region=region,slice=slice_name,proposition=prop,basis=basis,
                             state=state,n=len(group),historical_n=int(group.claims_evidence_cohort.eq("historical_dairy_reuse").sum())))
        if prop!="sugar_free_claim":continue
        positive=g[g["claims_claim_"+prop].eq(True)].copy()
        def wording(row):
            item=json.loads(row.claims_core_claim_evidence_json or "{}").get(prop,{})
            return str(item.get("ocr_wording_normalized",""))
        positive["saved_wording"]=positive.apply(wording,axis=1)
        for (region,slice_name,basis,word),group in positive.groupby(["region","slice","claims_basis_"+prop,"saved_wording"],dropna=False):
            rows.append(dict(record_kind="saved_positive_wording",branch=branch,region=region,slice=slice_name,
                             proposition=prop,basis=basis,wording=word,n=len(group)))
        anomaly=positive[positive.region.eq("UK-IE")&positive.slice.eq("other measurable")&positive.branch.eq("soda")]
        if len(anomaly):
            assert len(anomaly)==1
            r=anomaly.iloc[0];assert r.barcode=="5060054132725" and r.sugars_100g==3.3 and r.saved_wording=="no added sugar"
            assert r.sugars_100g==r.sugars_100g_off_raw and r.sugars_100g_missing==0
            rows.append(dict(record_kind="focused_anomaly",branch=branch,region=r.region,category=r.category,barcode=r.barcode,
                 product_name=r.product_name,proposition=prop,wording=r.saved_wording,basis=r["claims_basis_"+prop],
                 state=r["claims_state_"+prop],sugars=r.sugars_100g,energy=r.energy_kcal,image_url=r.claims_image_url,
                 evidence_cohort=r.claims_evidence_cohort,outcome=r.claims_original_overall_outcome,
                 saved_evidence=json.dumps(json.loads(r.claims_core_claim_evidence_json)[prop],sort_keys=True)))
    earlier=pd.read_csv(HERE/"hypothesis_results_v1.csv")
    earlier=earlier[(earlier.h=="H5")&earlier.variant.eq("primary")&earlier.provenance.eq("all")]
    for (region,subtype,test) in [("FR","FLAKES","fibre_claim"),("UK-IE","FLAKES","fibre_claim"),
          ("FR","GRANOLA","fibre_claim"),("UK-IE","GRANOLA","fibre_claim"),
          ("UK-IE","SOFT_DRINK","sugar_free_claim"),("UK-IE","CHEESE","reduced_fat_claim"),
          ("UK-IE","YOGURT_CULTURED_FRESH","reduced_fat_claim")]:
        r=earlier[(earlier.region==region)&(earlier.subtype==subtype)&(earlier.test==test)].iloc[0]
        rows.append(dict(record_kind="reused_H5",region=region,branch=subtype,proposition=test,pos=r.pos,neg=r.neg,
                         effect=r.effect,lo=r.lo,hi=r.hi,p=r.p,q=r.q,source_path="hypothesis_results_v1.csv",
                         analysis_role="existing commercial-format contrast; granola fibre does not clear materiality/significance"))
    out=pd.DataFrame(rows)
    anomaly_rows=out[out.record_kind.eq("focused_anomaly")]
    assert len(anomaly_rows)==1
    # Focused leave-one-record-out sensitivity; preserve the primary locked evidence comparison.
    low=out[out.record_kind.eq("coverage")&out.branch.eq("soda")&out.region.eq("UK-IE")&
            out.proposition.eq("sugar_free_claim")&out.slice.eq("retained profile")].iloc[0]
    lo,hi=diff_interval(int(low.positive_n),int(low.known_primary_n),0,42)
    extra=dict(record_kind="anomaly_sensitivity",branch="soda",region="UK-IE",proposition="sugar_free_claim",
               effect=low.positive_n/low.known_primary_n,lo=lo,hi=hi,profile_positive_n=28,profile_known_n=43,
               other_positive_n=0,other_known_n=42,analysis_role="exclude the one no-added-sugar anomaly only; locked flags retained")
    out=pd.concat([out,pd.DataFrame([extra])],ignore_index=True)
    # Provenance counts must reconcile to Tuesday matched-market-usable counts.
    for branch,prop in PLAN:
        if branch not in ["granola","soda","energy drink"]:continue
        for region in ["FR","UK-IE","US-CA"]:
            for sl in ["retained profile","other measurable"]:
                d=out[(out.record_kind=="coverage")&out.branch.eq(branch)&out.region.eq(region)&out.proposition.eq(prop)&out.slice.eq(sl)]
                pr=out[(out.record_kind=="provenance")&out.branch.eq(branch)&out.region.eq(region)&out.proposition.eq(prop)&out.slice.eq(sl)]
                assert len(d)==1 and pr.n.sum()==d.iloc[0].usable_market_n
    out["master_sha256"]=manifest["master_sha256"]
    out["coverage_sha256"]=digest(COVERAGE)
    out["display_label"]=np.where(out.proposition.eq("sugar_free_claim"),
                                 "sugar-related communication",out.proposition)
    out.to_csv(HERE/"communication_overlays_v1.csv",index=False,encoding="utf-8-sig")
    print("PASS",len(out),"rows; fixed source, coverage reconciliation, exact anomaly, provenance and reused H5 checks.")
if __name__=="__main__":main()
