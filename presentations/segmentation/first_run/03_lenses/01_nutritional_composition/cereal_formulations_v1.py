"""One consolidated cereal follow-up. Rebuild the Markdown evidence tables from the frozen H2 cohort."""
import hashlib
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_master_v1.parquet"
REPORT = HERE / "cereal_formulations_v1.md"
FIELDS = dict(energy="energy_kcal", sugars="sugars_100g", protein="protein_100g",
              fat="fat_100g", carbs="carbs_100g", fibre="fiber_100g")
CUES = {
    "FLAKES": {"corn":r"corn[ -]?flakes?|flocons? de mais", "bran":r"\bbran\b|son de (?:ble|froment)",
               "multigrain":r"multi[ -]?(?:grain|cereale)|[345] cereales",
               "frosted":r"frost(?:ed|ies)|glace(?:s|es)? au sucre|givrees?"},
    "GRANOLA": {"chocolate":r"chocolat|cacao|cocoa", "nuts":r"almond|amande|hazelnut|noisette|walnut|pecan|cashew",
                "fruit":r"berr(?:y|ies)|raisin|cranberr|framboise|myrtille|fruits? rouges|strawberr"}}

def cues(row):
    text=" ".join(str(row[k]) for k in ["product_name","off_categories"])
    text=unicodedata.normalize("NFKD",text.lower()).encode("ascii","ignore").decode()
    found=[name for name,pattern in CUES[row.effective_type_code].items() if re.search(pattern,text)]
    return "+".join(found) or "unknown"

def pairs(group,tolerance=10,reverse=False):
    seq=group[group.h2_pair_valid.eq(True)].sort_values(["energy","barcode"])
    if reverse: seq=seq.iloc[::-1]
    records=[]; i=0
    ids=seq.index.tolist()
    while i+1<len(seq):
        a,b=ids[i:i+2]
        if abs(group.at[a,"energy"]-group.at[b,"energy"])>tolerance:
            i+=1; continue
        if group.at[a,"sugars"]>group.at[b,"sugars"]: a,b=b,a
        rec={k:group.at[a,k]-group.at[b,k] for k in ["protein","fat","carbs","fibre","sugars"]}
        rec["gap"]=-rec["sugars"]
        rec["remainder"]=rec["carbs"]-rec["sugars"] if all(group.at[t,"carbs"]>=group.at[t,"sugars"] for t in [a,b]) else np.nan
        rec["cue"]="unknown" if "unknown" in [group.at[a,"cue"],group.at[b,"cue"]] else (
            "same" if group.at[a,"cue"]==group.at[b,"cue"] else "different")
        records.append(rec); i+=2
    return pd.DataFrame(records)

def table(head,rows):
    return "\n".join(["| "+" | ".join(head)+" |","|"+"|".join(["---"]*len(head))+"|"]+
                     ["| "+" | ".join(map(str,row))+" |" for row in rows])

def summary(series):
    s=series.dropna()
    return f"{s.median():+.1f} [{s.quantile(.25):+.1f}, {s.quantile(.75):+.1f}] ({len(s)})" if len(s) else "—"

def main():
    with SOURCE.open("rb") as f:
        assert hashlib.file_digest(f,"sha256").hexdigest()=="2f3859a401fada540b119424a91b2a924db6c084320f175cb0c8a58119027837"
    df=pd.read_parquet(SOURCE)
    df=df[df.h2_format_candidate.eq(True)].copy()
    for m,k in FIELDS.items():
        ok=df[k].between(0,900 if m=="energy" else 100)&df[k].eq(df[k+"_off_raw"])&df[k+"_missing"].eq(0)
        df[m]=df[k].where(ok)
    df["cue"]=df.apply(cues,axis=1)
    prior=pd.read_csv(HERE/"hypothesis_results_v1.csv").query("h=='H2' and variant=='primary' and direction=='forward' and tol==10")
    detail=[]; textrows=[]; profiles=[]; gradients=[]; robustness=[]; combinations=[]
    for fmt,base in df.groupby("effective_type_code"):
        fr=base[base.region.eq("FR")]
        for reg,g in base.groupby("region"):
            p=pairs(g); big=p[p.gap>=5]
            saved=prior[(prior.region==reg)&(prior.subtype==fmt)].iloc[0]
            assert len(p)==saved.pairs and len(big)==saved.success_n
            for label,frame in [("≥5",big),("<5",p[p.gap<5])]:
                detail.append([fmt,reg,label,len(frame)]+[summary(frame[k]) for k in ["protein","fat","carbs","fibre","remainder"]])
                measured=frame.dropna(subset=["protein","carbs"])
                joint=(measured.protein.gt(0)&measured.carbs.lt(0)).sum()
                combinations.append([fmt,reg,label,len(measured),joint,f"{100*joint/len(measured):.1f}%"])
            for label,arm in p.groupby("cue"):
                hit=arm[arm.gap>=5]
                textrows.append([fmt,reg,label,len(arm),len(hit),f"{100*len(hit)/len(arm):.0f}%",summary(hit.carbs)])
            variants=[pairs(g,t,rev) for t in [5,10,20] for rev in [False,True]]
            robustness.append([fmt,reg]+[f"{min(v.loc[v.gap>=5,k].median() for v in variants):+.1f} to {max(v.loc[v.gap>=5,k].median() for v in variants):+.1f}" for k in ["protein","fat","carbs","fibre"]])
            for m in ["protein","fat","carbs","fibre"]:
                # Candidate screen learned once in France. Compare coverage on all measurable individual products.
                ref=fr.dropna(subset=["sugars",m]); local=g.dropna(subset=["sugars",m])
                cuts=ref.sugars.quantile(.25),ref[m].quantile(.75)
                qualifies=(local.sugars<=cuts[0])&(local[m]>=cuts[1])
                def rate(q):
                    return 100*((local.sugars<=ref.sugars.quantile(q))&(local[m]>=ref[m].quantile(1-q))).mean()
                profiles.append([fmt,reg,m,f"≤{cuts[0]:.2f} / ≥{cuts[1]:.2f}",len(g),len(local),int(qualifies.sum()),
                                 f"{100*qualifies.mean():.1f}%",f"{rate(.20):.1f}–{rate(.30):.1f}%"])
            edges=fr.sugars.dropna().quantile([.25,.5,.75]).to_numpy()
            for j in range(4):
                sugar=g.sugars
                z=g[sugar.notna() & ((sugar>edges[j-1]) if j else True) & ((sugar<=edges[j]) if j<3 else True)]
                gradients.append([fmt,reg,j+1,len(z)]+[f"{z[k].median():.1f}" for k in ["sugars","protein","fat","carbs","fibre"]])
    assert len(df)==5829 and sum(r[3] for r in detail)==2095
    sections=[
      ("Matched pairs","Differences are lower-sugar minus higher-sugar, in g/100 g. Each cell gives median [Q1, Q3] and paired measurement count. The <5 g group includes exact sugar ties, whose ordering follows the energy/GTIN sort. Remainder is total carbohydrate minus sugars on coherent measurements. Interpret within region only. It is mathematically coupled to the sugar gap and cannot identify starch or ingredient substitution.",["Format","Region","Sugar gap","Pairs","Protein","Fat","Carbohydrate","Fibre","Remainder"],detail),
      ("Joint direction on the same pairs","Count of pairs where the lower-sugar member has both strictly higher protein and strictly lower total carbohydrate. Small nonzero differences count here; magnitude is reported above.",["Format","Region","Sugar gap","Measurable","Both differences","Share"],combinations),
      ("Commercial wording","Compare the fraction of pairs with a large sugar gap within each wording group. Same means identical detected cue sets on both products. Unknown includes any pair with an uncued member. The screen uses product names and OFF tags; plain and unlabelled cannot be distinguished reliably.",["Format","Region","Wording","Pairs","Gap ≥5","Share","Carbohydrate difference among large gaps"],textrows),
      ("Matching sensitivity","Range of median differences among large-gap pairs across forward/reverse matching at 5, 10 and 20 kcal/100 g.",["Format","Region","Protein","Fat","Carbohydrate","Fibre"],robustness),
      ("Candidate individual-product definitions and coverage","Each screen requires sugars at or below the French format Q1 and the named nutrient at or above its French format Q3, both in g/100 g. Cutoffs use French products measurable on those two fields, including products without energy. Apply full-precision French cutoffs unchanged within each format. Rows overlap. Share uses measurable products. Sensitivity tightens both tails to 20% or widens both to 30%. US/Canada coverage is exploratory, especially for carbohydrates.",["Format","Region","Higher nutrient","Sugar / nutrient cutoff","Format N","Measurable","Qualify","Share","Sensitivity"],profiles),
      ("Individual-product gradient","Products grouped by the three French format sugar quartiles from lowest to highest. Each nutrient column is the median of its observed values in that band. These bands describe variation and are not proposed classes.",["Format","Region","Sugar band","N","Sugars","Protein","Fat","Carbohydrate","Fibre"],gradients)]
    body="\n\n".join("## "+title+"\n\n"+note+"\n\n"+table(head,rows) for title,note,head,rows in sections)
    intro=REPORT.read_text(encoding="utf8").split("<!-- generated evidence -->")[0] if REPORT.exists() else "# Cereal formulation follow-up · Wave 2\n\n"
    REPORT.write_text(intro+"<!-- generated evidence -->\n\n"+body+"\n",encoding="utf8")

if __name__=="__main__":
    main()
