"""Bounded control comparison; invoke from the project environment."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT.parent/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"))
from shared_feature_diagnostics_v1 import read_master, CORE, KEY

OUT=ROOT/"05_unsupervised_control"

def ecdf(frame, reference):
    result=[]
    for name in CORE:
        values=np.sort(reference[name].to_numpy())
        x=frame[name].to_numpy()
        result.append((np.searchsorted(values,x,"left")+np.searchsorted(values,x,"right"))/(2*len(values)))
    return np.column_stack(result)

def fit(x,k):
    return KMeans(n_clusters=k,n_init=20,random_state=42,algorithm="lloyd").fit(x)

def main():
    source,_=read_master()
    foods=source[source.peer & source.basis_group.eq("per_100g_food")]
    ref=foods[foods.region.isin(["FR","UK-IE"])].sort_values(KEY).drop_duplicates("barcode").dropna(subset=CORE)
    us=foods[foods.region.eq("US-CA")].sort_values(KEY).dropna(subset=CORE).drop_duplicates("barcode")
    assert len(ref)==114146 and len(us)==13911
    x=ecdf(ref,ref); xu=ecdf(us,ref)
    evaluation=np.random.default_rng(42).choice(len(ref),4000,replace=False)
    all_rows=pd.concat([ref,us],ignore_index=True)
    assignments=all_rows[KEY+["subtype"]].copy()
    assignments["population"]=["reference"]*len(ref)+list(np.where(us.barcode.isin(ref.barcode),"US seen","US unseen"))
    assert assignments.population.eq("US unseen").sum()==12036
    rows=[]
    for k in [4,3,5]:
        model=fit(x,k)
        labels=model.labels_
        stability=[]
        for seed in range(12):
            sample=np.random.default_rng(2000+seed).integers(0,len(x),len(x))
            test=fit(x[sample],k)
            stability.append(adjusted_rand_score(labels,test.predict(x)))
        sil=silhouette_score(x[evaluation],labels[evaluation])
        names=np.argsort(np.argsort(model.cluster_centers_[:,2]))+1
        lab=names[np.r_[labels,model.predict(xu)]]
        assignments[f"k{k}"]=lab
        mix=adjusted_mutual_info_score(ref.subtype,labels)
        rows.append(dict(kind="evaluation",k=k,n=len(x),ari_median=np.median(stability),
                         ari_min=min(stability),ari_max=max(stability),silhouette=sil,format_ami=mix,
                         min_share=np.bincount(labels).min()/len(labels),inertia=model.inertia_))
        for (pop,group),g in all_rows.assign(population=assignments.population,group=lab).groupby(["population","group"]):
            row=dict(kind="profile",k=k,population=pop,group=group,n=len(g),top_format=g.subtype.mode()[0],
                     top_format_share=g.subtype.value_counts(normalize=True).iloc[0])
            for m in CORE:
                row[m]=g[m].median()
                row[m+"_q1"],row[m+"_q3"]=g[m].quantile([.25,.75])
            rows.append(row)
            for col in ["category","region","subtype"]:
                for val,n in g[col].value_counts().items():
                    rows.append(dict(kind="profile_mix",population=pop,k=k,group=group,variable=col,value=val,n=n,denominator=len(g)))
            for c in ["protein_claim","organic_claim","plant_based_claim","fibre_claim"]:
                a=g[g.assessed_layer & g.claims_source_market_limitation.fillna("").eq("")]
                positive=a["claims_claim_"+c].eq(True).sum()
                negative=a["claims_state_"+c].eq("DOCUMENTED_NOT_DETECTED").sum()
                rows.append(dict(kind="claim_profile",population=pop,k=k,group=group,variable=c,n=positive,
                                 denominator=positive+negative,assessed_layer_n=len(a),group_n=len(g)))
        print("control",k,sil,np.median(stability),flush=True)
    pd.DataFrame(rows).to_csv(OUT/"control_comparison_v1.csv",index=False)
    assignments.to_parquet(OUT/"control_assignments_v1.parquet",index=False)

if __name__=="__main__":
    with threadpool_limits(limits=2):
        main()
