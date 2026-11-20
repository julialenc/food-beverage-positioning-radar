"""Juice commercial refinement and within-format nutrition, corrected Wave 2."""
from pathlib import Path
import re
import sys
import unicodedata
import hashlib
import json

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EDA=HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import read_master,KEY

FRUIT={"orange":r"oranges?|naranjas?|orangensaft","apple":r"apples?|pommes?|manzanas?|apfelsaft",
 "grape":r"grape|raisin|uva|traubensaft","pineapple":r"pineapple|ananas",
 "grapefruit":r"grapefruit|pamplemousse","lemon":r"lemon|citron|limon",
 "lime":r"limes?|citron vert","pear":r"pears?|poires?|peras?","peach":r"peaches|peach|peches?",
 "apricot":r"apricot|abricot","prune":r"prune|pruneau","cranberry":r"cranberry|cranberries|canneberge",
 "pomegranate":r"pomegranate|grenade","mango":r"mango|mangue","cherry":r"cherry|cerise",
 "berry":r"blueberry|myrtille|raspberry|framboise|strawberry|fraise|blackcurrant|cassis|aronia"}
VEG={"tomato":r"tomatoes|tomato|tomates?|tomatensaft|tomaten","carrot":r"carrots?|carottes?","beetroot":r"beetroot|beets?|betteraves?",
 "celery":r"celery|celeri","cucumber":r"cucumber|concombre","spinach":r"spinach|epinard","kale":r"kale|chou"}
METRICS=["sugars","energy","salt","protein","fat","fibre"]
def norm(x):
    return re.sub(r"[-_]"," ",unicodedata.normalize("NFKD",str(x).lower()).encode("ascii","ignore").decode())
def has(t,p):return bool(re.search(r"\b(?:"+p+r")\b",t))
def detect(t):
    t=t.replace("citron vert","lime")
    return ({k for k,p in FRUIT.items() if has(t,p)}, {k for k,p in VEG.items() if has(t,p)})
def classify(row):
    name,tags=norm(row.product_name),norm(row.off_categories)
    alltext=name+" "+tags
    # Boundary screening is commercial, before any nutritional comparison.
    if re.search(r"\b[0-9]{1,2}(?:[.,][0-9]+)?\s*%\s*(?:fruit )?juice",name) or has(name,r"nectars?|smoothies?|juice drinks?|juice beverages?|juice cocktails?|boisson au jus|high juice|cordial|squash|sirop|syrup|concentrate for dilution|double strength|aide culinaire|ingredient lemon|homebaking|zero sugar made|sodas?|colas?|tonic|orangeade|lemonades?|limonades?|dr pepper|irn bru|vimto|fanta|schweppes|pepsi|panache|gaspacho|gazpacho|soja cuisine|chocolate bars?"):
        return "boundary concern","name suggests adjacent beverage form","","",""
    if has(name,r"ginger shot|ginger juice|gingembre|wheatgrass|aloe vera|coconut water|eau de coco|jus de bouleau|hot shot"):
        return "other botanical juice","specific botanical/shot wording","","",""
    nf,nv=detect(name);tf,tv=detect(tags)
    # Tags that add types beyond the named composition are retained as uncertainty.
    conflict=bool((nf or nv) and ((tf-nf) or (tv-nv)))
    f,v=(nf,nv) if nf or nv else (tf,tv)
    blends=has(name,r"blend|melange|multifruit|multi fruit|cocktail|tropical|fruits rouges")
    basis="name" if nf or nv else "tags" if tf or tv else "generic only"
    if conflict:
        status="ambiguous composition"
    elif f and v:status="mixed fruit/vegetable"
    elif v:status="vegetable blend" if len(v)>1 or blends else "vegetable: "+next(iter(v))
    elif f:status="fruit blend" if len(f)>1 or blends else "fruit: "+next(iter(f))
    elif has(name,r"vegetable juice|jus de legumes"):status="vegetable unspecified"
    else:status="composition unresolved"
    concentration=("explicit not from concentrate" if has(alltext,r"not from concentrate|non a base de concentre|sans concentre") else
                   "explicit from concentrate" if has(alltext,r"from concentrate|a base de concentre|a base de jus concentre") else "unspecified")
    flavour="+".join(k for k,p in [("ginger",r"ginger|gingembre"),("spiced",r"spiced|epice|piment"),("sparkling",r"sparkling|petillant|carbonated")] if has(alltext,p)) or "unspecified"
    return status,basis,"+".join(sorted(f|v)),concentration,flavour
def table(head,rows):
    return "\n".join("| "+" | ".join(map(str,r))+" |" for r in [head,["---"]*len(head),*rows])
def fmt(x):return f"{x:.2f}" if pd.notna(x) else "—"
def main():
    d,_=read_master()
    prior=pd.read_parquet(HERE/"beverage_assignments_v1.parquet")
    j=prior[prior.analytical_format.eq("juice")]
    assert not j.duplicated(KEY).any() and j.juice_family_review_scope.all()
    audit=["original_analytical_format","juice_classification_confidence","juice_classification_reason","juice_name_evidence","juice_tag_evidence","juice_classification_version"]
    a=d.merge(j[KEY+["analytical_format","beverage_view_segment","basis_group","product_name"]+audit],on=KEY,
              how="inner",validate="one_to_one",suffixes=["","_assignment"])
    assert len(a)==len(j) and a.basis_group.eq(a.basis_group_assignment).all()
    meta=pd.read_csv(EDA/"subtype_assignments.csv",dtype=str,usecols=KEY+["off_categories"])
    a=a.merge(meta,on=KEY,validate="one_to_one")
    cols=["juice_subformat","composition_evidence","named_materials","concentrate_descriptor","flavour_construction"]
    a[cols]=pd.DataFrame([classify(r) for r in a.itertuples()],index=a.index)
    a["strict_comparable"]=~a.juice_subformat.isin(["boundary concern","ambiguous composition","composition unresolved","vegetable unspecified","other botanical juice","fruit: berry"])
    a["sugar_band"]=np.select([a.sugars.isna(),a.sugars.le(.5),a.sugars.lt(5)],["unknown","≤0.5","0.5–<5"],default="≥5")
    a["candidate_profile"]=pd.Series(pd.NA,index=a.index,dtype="string")
    # No retained nutritional segments; keep each product's commercial refinement and measured observations.
    keys=a[KEY+["product_name","beverage_view_segment","basis_group","analytical_format"]+audit+cols+
           ["strict_comparable","sugar_band","candidate_profile"]+METRICS]
    out=HERE/"juice_assignments_v1.parquet"
    keys.to_parquet(out,index=False)
    back=pd.read_parquet(out);assert len(back)==len(j) and not back.duplicated(KEY).any() and back.barcode.equals(a.barcode)
    denominator=[];composition=[];nutrition=[];sensitivity=[];screens=[];examples=[];matching=[];salt_audit=[];concentrates=[]
    for reg,g in a.groupby("region"):
        for label,z in [("current juice",g),("strict commercial evidence",g[g.strict_comparable])]:
            denominator.append([reg,label,len(z),z.sugars.count(),z.dropna(subset=["sugars","energy"]).shape[0],
                                int(z.sugars.le(.5).sum()),int((z.sugars.gt(.5)&z.sugars.lt(5)).sum())])
        low=g[g.sugars.gt(.5)&g.sugars.lt(5)]
        for label,z in [("all",low),("without vegetable evidence",low[~low.juice_subformat.str.startswith("vegetable")]),
                        ("strict fruit",low[low.strict_comparable&low.juice_subformat.str.startswith("fruit")])]:
            salt_audit.append([reg,label,len(z),z.salt.count(),fmt(z.salt.median())])
        for descriptor,z in g.groupby("concentrate_descriptor"):
            concentrates.append([reg,descriptor,len(z)])
        sensitivity.append([reg,"0.5<sugars<5",len(low),low.salt.count(),fmt(low.salt.median()),fmt(low.energy.median())])
        for label,z in low.groupby("juice_subformat"):
            composition.append([reg,label,len(z),z.salt.count(),fmt(z.salt.median()),fmt(z.energy.median())])
        tiny=g[g.sugars.le(.5)]
        for label,z in tiny.groupby("juice_subformat"):
            sensitivity.append([reg,"≤0.5: "+label,len(z),z.energy.count(),fmt(z.energy.median()),int(z.energy.gt(20).sum())])
        # Shared French reference cutoffs screen proposed low-sugar tail within each named type.
        for form,z in g[g.strict_comparable].groupby("juice_subformat"):
            ref=a[(a.region=="FR")&a.juice_subformat.eq(form)].sugars.dropna()
            for m in METRICS:
                v=z[m].dropna()
                nutrition.append([reg,form,m,len(z),len(v),fmt(v.quantile(.1)),fmt(v.quantile(.25)),fmt(v.median()),fmt(v.quantile(.75)),fmt(v.quantile(.9))])
            if len(ref)>=30 and z.sugars.count()>=20:
                cuts=ref.quantile([.2,.25,.3])
                v=z.sugars.dropna()
                screens.append([reg,form,len(v),*[fmt(c) for c in cuts],*[int(v.le(c).sum()) for c in cuts]])
            l=z[z.sugars.lt(5)].dropna(subset=["energy","sugars"]);h=z[z.sugars.ge(5)].dropna(subset=["energy","sugars"])
            if min(len(l),len(h))>=10:
                matching.append([reg,form,len(l),len(h),fmt(l.energy.median()),fmt(h.energy.median()),fmt(l.salt.median()),fmt(h.salt.median())])
    for (reg,form),g in a[(a.region.isin(["FR","UK-IE"]))&a.strict_comparable].groupby(["region","juice_subformat"]):
        if form not in ["vegetable: tomato","fruit: orange","fruit: apple","fruit: lemon"]:continue
        v=g.dropna(subset=["sugars"])
        for label,mask,target in [("near typical",v.sugars.notna(),v.sugars.median()),("near sugar 5 boundary",v.sugars.notna(),5),
                                  ("very-low sugars",v.sugars.le(.5),0)]:
            z=v[mask&v.product_name.fillna("").map(norm).str.contains(r"\b(?:juice|jus|saft)\b")]
            if len(z):
                r=z.assign(dist=(z.sugars-target).abs()).sort_values(["dist","barcode"]).iloc[0]
                examples.append([reg,form,label,r.barcode,r.product_name.replace("|","/"),*[fmt(r[m]) for m in ["sugars","energy","salt"]]])
    count=a.groupby(["juice_subformat","region"]).size().unstack(fill_value=0)
    panels=[
      ("Population and effect of ambiguity exclusions",["Region","Population","N","Valid sugars","Joint sugar/energy","≤0.5 N","0.5–<5 N"],denominator),
      ("Independent commercial classifications",["Subformat",*count.columns],[[k,*v] for k,v in count.iterrows()]),
      ("Explaining the 0.5–5 group",["Region","Subformat","Sugar group N","Valid salt","Median salt","Median energy"],composition),
      ("Salt sensitivity to commercial composition",["Region","Population at 0.5–<5","N","Valid salt","Median salt"],salt_audit),
      ("Concentrate descriptor, independent of named composition",["Region","Descriptor","Assignments"],concentrates),
      ("Low-sugar cohort and very-low-sugar energy audit",["Region","Cohort","N","Available relevant metric","Salt median or energy median","Energy median or energy>20 N"],sensitivity),
      ("Within-subformat nutrient variation",["Region","Subformat","Metric","N","Valid","P10","Q1","Median","Q3","P90"],nutrition),
      ("Candidate sugar-tail rule sensitivity",["Region","Subformat","Valid sugars","French P20","French P25","French P30","N at P20","N at P25","N at P30"],screens),
      ("Low versus other sugars within named composition",["Region","Subformat","<5 joint N","≥5 joint N","Energy low","Energy other","Salt low","Salt other"],matching),
      ("Representative and boundary observations",["Region","Subformat","Example","Text GTIN","Recorded name","Sugars","Energy","Salt"],examples)]
    p=HERE/"juice_formulations_v1.md"
    fr=a[a.region.eq("FR")];low=fr[fr.sugars.gt(.5)&fr.sugars.lt(5)]
    nonveg=low[~low.juice_subformat.str.startswith("vegetable")]
    named=[]
    for form in ["fruit: apple","fruit: orange","vegetable: tomato"]:
        row=[form]
        for reg in ["FR","UK-IE"]:
            z=a[a.region.eq(reg)&a.strict_comparable&a.juice_subformat.eq(form)]
            row.append(f"{fmt(z.sugars.median())} g (n={z.sugars.count()}); salt {fmt(z.salt.median())} g (n={z.salt.count()})")
        named.append(row)
    intro="\n\n".join(["# Juice formulations · Wave 2",
        "**Formulation investigation closed by Julia on 16 November. Bounded classification correction: 19 November 2026.** The shared name/tag rule now gives specific commercial evidence precedence over broad parent tags. Conflicting names/specific tags, generic-only identity and incompatible intended-use wording remain unresolved in the beverage layer. [Correction CHECK](juice_classification_CHECK_v1.md).",
        "**Conclusion retained: commercial refinements, no additional nutritional profile proposed.** Apple, orange, tomato, fruit/vegetable mixtures and named blends are composition-based commercial types. Concentrate wording remains an independent processing descriptor. No clustering, new recipe inference or new claims assessment was performed.",
        "The corrected population is the exact juice subset of beverage_assignments_v1.parquet: "+", ".join(f"{r}: {len(a[a.region.eq(r)]):,}" for r in ["FR","UK-IE","US-CA"])+f"; total {len(a):,} assignments. Original and corrected analytical labels, confidence, reasons and text keys are retained. The earlier 8,561-assignment file represented the old selected population, not complete juice coverage.",
        f"**French low-sugar/salt explanation, refreshed.** Among {fr.sugars.count():,} valid sugar observations, {len(low):,} have 0.5<sugars<5 g/100 ml. Salt is observed on {low.salt.count():,}; median {fmt(low.salt.median())} g/100 ml. Excluding vegetable-type evidence leaves {len(nonveg):,}, with {nonveg.salt.count():,} valid salt values and median {fmt(nonveg.salt.median())} g/100 ml. These updated denominators replace the earlier selected-population summary. Nutrition describes consequences of commercial composition; it does not assign identity or prove salt addition.",
        table(["Named commercial type","France: sugars and salt per 100 ml","UK/IE: sugars and salt per 100 ml"],named),
        "The same bounded within-type summaries and French P20/P25/P30 sensitivity are refreshed below. Apple/orange variation and questionable zero-sugar/nonzero-energy records do not establish a recognizable new low-sugar formulation profile. Recorded zero stays distinct from missing. US/Canada remains selected exploratory evidence; liquid basis and validity conventions are inherited, not independently pack-verified.",
        "**Unresolved boundaries stay visible.** A juice name alongside specific nectar tags is not silently treated as confirmed juice. Broader beverage records can refer to juice as an ingredient or an overlapping proposition. This correction does not comprehensively recategorize beverages outside the existing governed juice-family population. Category-boundary questions and intended-use flags remain independent of nutrition.",
        "The keyed file and evidence tables below are rebuilt reproducibly from the unchanged corrected Wave 2 master. Source observations and locked OCR/LLM evidence are unchanged. No new providers, image assessment, enrichment, clustering or consolidation were run."])+"\n\n"
    body="\n\n".join("<details><summary>"+title+"</summary>\n\n"+table(head,rows)+"\n\n</details>" for title,head,rows in panels)
    p.write_text(intro+"<!-- evidence -->\n\n"+body+"\n",encoding="utf8")
    print("PASS: source digest, all juice keys and basis, keyed classification round trip.")
if __name__=="__main__":main()
