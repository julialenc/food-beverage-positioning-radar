"""Wave 2 biscuit/wafer follow-up. Render one CHECK with reproducible evidence tables."""
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EDA=HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import read_master, KEY, CORE

METRICS=["fat","salt","protein"]
REPORT=HERE/"biscuits_and_wafers_CHECK_v1.md"
def norm(text):
    return re.sub(r"[-_]"," ",unicodedata.normalize("NFKD",str(text).lower()).encode("ascii","ignore").decode())
def classify(row):
    name,tags=norm(row.product_name),norm(row.off_categories)
    tags=re.sub(r"biscuits? (?:and|et) (?:cakes?|gateaux|crackers?)"," ",tags)
    text=name+" "+tags
    wafer=bool(re.search(r"\b(wafers?|gaufrettes?|oblea[s]?|waffelblaettchen)\b",text))
    specific=bool(re.search(r"\b(cookies?|shortbread|sables?|speculoos|digestives?|palets bretons|galettes bretonnes)\b",text))
    biscuit=specific or bool(re.search(r"\b(biscuits?|galletas?)\b",text))
    if re.search(r"\b(macaroons?|macarons?|crackers?|pretzels?|pancakes?|waffles?|gaufres?|ice cream|glaces?|cookie dough|biscuit mix|palmiers?|moelleux|banana wafers?|potato wafers?)\b",name) or re.search(r"\b(crackers?|macarons?|ice creams?)\b",tags):
        form="scope caution"
    elif wafer and specific: form="conflicting"
    elif wafer: form="wafer"
    elif biscuit: form="biscuit"
    else: form="unresolved"
    filled=bool(re.search(r"\b(filled|fourre\w*|sandwich\w*|filling|rellen\w*)\b",text))
    coated=bool(re.search(r"\b(coat(?:ed|ing)|cover(?:ed|ing)|enrob\w*|napp\w*|recouvert\w*|dipped)\b",text))
    modifier="both" if filled and coated else "filled" if filled else "coated" if coated else "unspecified"
    return form,modifier

def match(g,tol,seed,control=False,directional=False):
    a=g.copy()
    # Stable randomized tie ordering avoids systematically matching adjacent barcodes.
    a["tie"]=np.random.default_rng(seed).permutation(len(a))
    a=a.sort_values(["sugars","tie"])
    def seq(x):return list(zip(x.index,x.sugars))
    pairs=[]
    if control:
        l,r=seq(a[a.k5==2]),seq(a[a.k5==3]); i=j=0
        while i<len(l) and j<len(r):
            u,x=l[i];v,y=r[j]
            if abs(x-y)<=tol:pairs.append((u,v));i+=1;j+=1
            elif x<y:i+=1
            else:j+=1
    else:
        items=seq(a);i=0
        while i+1<len(items):
            u,x=items[i];v,y=items[i+1]
            if y-x<=tol:pairs.append((u,v));i+=2
            else:i+=1
    if not pairs:return np.empty((0,3))
    l,r=zip(*pairs)
    assert len(set(l)|set(r))==2*len(pairs)
    assert (g.loc[list(l),"sugars"].to_numpy()-g.loc[list(r),"sugars"].to_numpy()).__abs__().max()<=tol
    delta=g.loc[list(l),METRICS].to_numpy()-g.loc[list(r),METRICS].to_numpy()
    return delta if control or directional else abs(delta)
def summary(x):
    return " / ".join(f"{v:.2f}" for v in np.median(x,axis=0)) if len(x) else "—"
def table(h,rows):
    return "\n".join("| "+" | ".join(map(str,r))+" |" for r in [h,["---"]*len(h),*rows])
def main():
    d,_=read_master()
    a=d[d.peer & d.subtype.eq("BISCUITS_WAFERS") & d.category.eq("snacks")].copy()
    m=pd.read_csv(EDA/"subtype_assignments.csv",usecols=KEY+["product_name","off_categories"],dtype=str)
    a=a.merge(m,on=KEY,validate="one_to_one")
    a[["form","construction"]]=pd.DataFrame([classify(x) for x in a.itertuples()],index=a.index)
    labels=pd.read_parquet(HERE.parent/"05_unsupervised_control/control_assignments_v1.parquet")
    a=a.merge(labels[KEY+["k5","population"]],on=KEY,how="left",validate="one_to_one")
    assert a.groupby("region").size().to_dict()=={"FR":18083,"UK-IE":1863,"US-CA":10749}
    valid=a.dropna(subset=CORE)
    assert valid.groupby("region").size().to_dict()=={"FR":16425,"UK-IE":1691,"US-CA":1018}
    counts=[];paired=[];ctrl=[];screen=[];examples=[];alignment=[]
    for (form,reg),base in a.groupby(["form","region"]):
        g=valid[(valid.form==form)&(valid.region==reg)]
        counts.append([form,reg,len(base),len(g)])
        if form not in ["wafer","biscuit"]:continue
        parts=[x for _,x in g.groupby("construction")]
        subsets={"all":g}
        if form=="biscuit":
            for style,pat in [("shortbread / sablé",r"shortbread|\bsables?\b"),("digestive",r"digestives?"),("cookie",r"\bcookies?\b")]:
                subsets[style]=g[g.product_name.map(norm).str.contains(pat)]
        for style,sub in subsets.items():
            if not len(sub):continue
            arr=np.concatenate([match(z,2,42,directional=True) for _,z in sub.groupby("construction")])
            oriented=arr*np.sign(arr[:,0,None])
            eligible=oriented[oriented[:,0]>=5]
            aligned=((eligible[:,1]>=.10)&(eligible[:,2]<=-.5)).sum()
            opposite=((eligible[:,1]<=-.10)&(eligible[:,2]>=.5)).sum()
            alignment.append([form,reg,style,len(arr),len(eligible),int(aligned),int(opposite),
                              f"{aligned/len(eligible):.1%}" if len(eligible) else "—"])
        primary=np.concatenate([match(x,2,42) for x in parts])
        alt=np.concatenate([match(x,1,73) for x in parts])
        paired.append([form,reg,"all, matched within wording",len(g),len(primary),summary(primary),len(alt),summary(alt)])
        for tag,z in g.groupby("construction"):
            x=match(z,2,42);y=match(z,1,73)
            paired.append([form,reg,tag,len(z),len(x),summary(x),len(y),summary(y)])
        # Match the existing reference groups on form, construction and sugars.
        # US projection is separate. Regional duplicates omitted by reference fitting have no label.
        joint=np.concatenate([match(x,2,42,True) for x in parts])
        other=np.concatenate([match(x,1,73,True) for x in parts])
        l,r=g[g.k5.eq(2)],g[g.k5.eq(3)]
        ctrl.append([form,reg,len(l),len(r),summary(np.array([l[METRICS].median()-r[METRICS].median()])),
                     len(joint),summary(joint),len(other),summary(other)])
        fr=valid[(valid.form==form)&(valid.region=="FR")]
        # Profile suggested by the control: higher fat AND salt AND lower protein.
        # Evaluate stricter percentile thresholds to see whether the apparent group has a boundary.
        def tagged(x,q):
            v=fr[METRICS].quantile(q); p=fr.protein.quantile(1-q)
            return (x.fat>=v.fat)&(x.salt>=v.salt)&(x.protein<=p)
        hits=tagged(g,.65)
        v=fr[METRICS].quantile(.65); pl=fr.protein.quantile(.35)
        freq=[tagged(g,q).mean() for q in [.60,.65,.70]]
        screen.append([form,reg,f"{v.fat:.5g} / {v.salt:.5g} / {pl:.5g}",len(g),int(hits.sum()),*[f"{f:.1%}" for f in freq]])
        for inside in [True,False]:
            z=g[(hits==inside)&g.product_name.fillna("").ne("")].copy()
            if z.empty:continue
            # Show a typical qualifying example and a nearest nonqualifier on reference IQR scales.
            scale=(fr[METRICS].quantile(.75)-fr[METRICS].quantile(.25)).replace(0,1)
            if inside:dist=(z[METRICS]-g.loc[hits,METRICS].median()).abs().div(scale).sum(axis=1)
            else:dist=((v.fat-z.fat).clip(lower=0)/scale.fat+(v.salt-z.salt).clip(lower=0)/scale.salt+(z.protein-pl).clip(lower=0)/scale.protein)
            u=z.assign(dist=dist).sort_values(["dist","barcode"]).iloc[0]
            examples.append([form,reg,"typical qualifier" if inside else "near miss",u.barcode,str(u.product_name).replace("|","/"),u.construction,*[f"{u[k]:.6g}" for k in ["sugars",*METRICS]]])
    panels=[("Format and nutrient coverage",["Format evidence","Region","Assignments","Valid core four"],counts),
            ("Similar-sugar pair differences",["Form","Region","Construction cue","Valid","Pairs","Absolute gap F/S/P","Sensitivity pairs","Sensitivity gap F/S/P"],paired),
            ("Existing control groups 2 versus 3",["Form","Region","Group 2 N","Group 3 N","Raw median difference F/S/P","Matched pairs","Paired difference F/S/P","Sensitivity pairs","Sensitivity difference F/S/P"],ctrl),
            ("Co-occurrence independently of the control",["Form","Region","Name restriction","Pairs","Fat gap ≥5","Aligned","Opposite","Aligned share of fat-gap pairs"],alignment),
            ("Candidate product definition",["Form","Region","Fat ≥ / salt ≥ / protein ≤","Valid","Qualifiers","60/40","65/35","70/30"],screen),
            ("Individual products",["Form","Region","Example","Text GTIN","Recorded name","Construction","Sugars","Fat","Salt","Protein"],examples)]
    intro=REPORT.read_text(encoding="utf8").split("<!-- evidence -->")[0] if REPORT.exists() else "# Biscuits and wafers · formulation CHECK\n\n"
    REPORT.write_text(intro+"<!-- evidence -->\n\n"+"\n\n".join("## "+title+"\n\n"+table(h,rows) for title,h,rows in panels)+"\n",encoding="utf8")

if __name__=="__main__":main()
