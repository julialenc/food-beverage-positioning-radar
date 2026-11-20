"""Reproduce the within-format dairy dessert comparison from corrected Wave 2."""
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EDA=HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import read_master, KEY

PATTERNS={"rice pudding":r"rice pudding|riz au lait|arroz con leche",
          "semolina":r"semolina|semoule au lait|gateau de semoule",
          "flan":r"\bflans?\b|cremes? caramel|cremes? renversees?",
          "dessert cream / pudding":r"cremes? desserts?|\bpuddings?\b|\bpudins?\b",
          "mousse":r"\bmousses?\b","creme brulee":r"cremes? brulees?",
          "panna cotta":r"panna cotta","tiramisu":r"tiramis[uù]",
          "custard":r"\bcustards?\b"}
FLAG=r"instant|poudre|powder|pie filling|dessert sauces?|baby foods?|aliments pour bebes|frozen desserts?|ice cream|cremes? glacees?"
def norm(value):
    text=unicodedata.normalize("NFKD",str(value).lower()).encode("ascii","ignore").decode()
    return re.sub(r"[-_]"," ",text)
def cues(text):
    text=re.sub(r"entremets\s+mousses et cremes? desserts?|custards? and pastry creams?"," ",text)
    if re.search(PATTERNS["rice pudding"],text):text=re.sub("rice puddings?","rice form",text); rice=True
    else: rice=False
    found={k for k,p in PATTERNS.items() if re.search(p,text)}
    if rice: found.add("rice pudding")
    return found
def classify(row):
    name,tags=norm(row.product_name),norm(row.off_categories)
    if re.search(FLAG,name+" "+tags):return "scope caution"
    n,t=cues(name),cues(tags)
    # Generic pudding can describe a more specific named dessert.
    found=n|t
    if found & {"rice pudding","semolina"}:found.discard("dessert cream / pudding")
    if len(found)==1:return found.pop()
    return "conflicting cues" if found else "unspecified"
def table(header,rows):
    return "\n".join("| "+" | ".join(map(str,row))+" |" for row in [header,["---"]*len(header),*rows])
def med(x): return f"{x.median():.1f}" if x.notna().any() else "—"
def main():
    df,_=read_master()
    g=df[df.peer & df.subtype.eq("DAIRY_DESSERT")].copy()
    meta=pd.read_csv(EDA/"subtype_assignments.csv",dtype=str,usecols=KEY+["product_name","off_categories"])
    g=g.merge(meta,on=KEY,validate="one_to_one")
    g["form"]=g.apply(classify,axis=1)
    g["valid"]=g.energy.ge(10)&g.protein_density.notna()
    prior=pd.read_csv(HERE/"hypothesis_results_v1.csv").query("h=='H3' and variant=='primary' and subtype=='DAIRY_DESSERT' and test=='protein' and energy_floor==10")
    for row in prior.itertuples():
        a=g[(g.region==row.region)&g.valid]; assert len(a)==row.n
        change=a.protein_density.rank(pct=True)-a.protein.rank(pct=True)
        assert np.isclose(change.abs().ge(.25).mean(),row.effect)
    counts=[]; ranks=[]; profiles=[]; bands=[]; examples=[]; sensitivity=[]; checks=[]; tradeoffs=[]
    for (form,reg),all_rows in g.groupby(["form","region"]):
        a=all_rows[all_rows.valid].copy()
        counts.append([form,reg,len(all_rows),len(a)])
        if form in ["scope caution","unspecified","conflicting cues"] or not len(a):continue
        hit=a.protein.ge(8)&a.energy.le(110)
        if form=="dessert cream / pudding":
            peer_region={"FR":"UK-IE","UK-IE":"FR"}.get(reg)
            shared=g.loc[g.region.eq(peer_region),"barcode"]
            for label,mask in [("distinct from other primary region",~a.barcode.isin(shared)),
                               ("explicit pudding in name",a.product_name.map(norm).str.contains(r"\bpuddings?\b")),
                               ("explicit dessert cream in name",a.product_name.map(norm).str.contains(r"cremes? desserts?"))]:
                checks.append([reg,label,int(mask.sum()),int((hit&mask).sum())])
        profiles.append([form,reg,len(a),int(hit.sum()),f"{hit.mean():.1%}",int((a.protein.ge(9)&a.energy.le(100)).sum()),int((a.protein.ge(7)&a.energy.le(120)).sum())])
        if len(a)<30:continue
        bands.append([form,reg,*[int(v) for v in pd.cut(a.protein,[-1,4,6,8,10,np.inf],right=False).value_counts(sort=False)],int(hit.sum())])
        for floor in [0,5,10,20]:
            b=all_rows[all_rows.protein_density.notna()&all_rows.energy.ge(floor)]
            change=b.protein_density.rank(pct=True)-b.protein.rank(pct=True)
            sensitivity.append([form,reg,floor,len(b),f"{change.abs().ge(.25).mean():.1%}"])
        delta=a.protein_density.rank(pct=True)-a.protein.rank(pct=True)
        high=a.protein.ge(a.protein.quantile(.75))
        costly=high&a.energy.ge(a.energy.quantile(.75))&a.protein_density.le(a.protein_density.median())
        tradeoffs.append([form,reg,len(a),int(high.sum()),int(costly.sum()),f"{costly.sum()/high.sum():.1%}"])
        for label,mask in [("rises ≥25 points",delta>=.25),("falls ≥25 points",delta<=-.25),("moves <25 points",delta.abs()<.25),
                           ("meets screen",hit),("other measurable",~hit)]:
            z=a[mask]
            if len(z):ranks.append([form,reg,label,len(z),*[med(z[m]) for m in ["protein","energy","protein_density","fat","sugars"]],f"{z.fat.count()}/{z.sugars.count()}"])
        if hit.sum()>=3:
            # Representative by proximity to median protein and energy in the qualifying arm.
            for label,mask in [("representative",hit),("inside boundary",hit),("outside boundary",~hit)]:
                z=a[mask & a.product_name.fillna("").ne("")].copy()
                if z.empty:continue
                if label=="representative":distance=(z.protein-z.protein.median()).abs()+(z.energy-z.energy.median()).abs()/10
                elif label=="inside boundary":distance=np.minimum(z.protein-8,(110-z.energy)/10)
                else:distance=np.maximum(8-z.protein,0)+np.maximum(z.energy-110,0)/10
                row=z.assign(distance=distance).sort_values(["distance","barcode"]).iloc[0]
                examples.append([form,reg,label,row.barcode,str(row.product_name).replace("|","/"),*[f"{row[m]:.1f}" for m in ["protein","energy","protein_density","fat","sugars"]]])
    sections=[("Form evidence and coverage",["Commercial evidence","Region","Assignments","Valid protein and energy"],counts),
              ("Individual-product screen",["Form","Region","Measurable","Qualifying","Share","≥9 g and ≤100 kcal","≥7 g and ≤120 kcal"],profiles),
              ("Pudding wording and shared-barcode sensitivity",["Region","Restriction","Measurable","Qualifying"],checks),
              ("H4 recomputed within each form",["Form","Region","Measurable","Upper protein quartile","Also upper energy quartile and at/below median density","Share of upper protein group"],tradeoffs),
              ("Distribution of protein per 100 g",["Form","Region","<4","4 to <6","6 to <8","8 to <10","≥10","Qualifying on both fields"],bands),
              ("Within-form ranks and composition",["Form","Region","Comparison","N","Protein","Energy","Protein/100 kcal","Fat","Sugars","Fat/sugars observed N"],ranks),
              ("Energy-floor sensitivity",["Form","Region","Minimum kcal (always >0)","Measurable","Move ≥25 points"],sensitivity),
              ("Representative and boundary products",["Form","Region","Example","GTIN","Recorded name","Protein","Energy","Protein/100 kcal","Fat","Sugars"],examples)]
    dest=HERE/"dairy_dessert_formulations_v1.md"
    intro=dest.read_text(encoding="utf8").split("<!-- tables -->")[0] if dest.exists() else "# Dairy desserts · formulation within format\n\n"
    dest.write_text(intro+"<!-- tables -->\n\n"+"\n\n".join("## "+title+"\n\n"+table(header,rows) for title,header,rows in sections)+"\n",encoding="utf8")
if __name__=="__main__":main()
