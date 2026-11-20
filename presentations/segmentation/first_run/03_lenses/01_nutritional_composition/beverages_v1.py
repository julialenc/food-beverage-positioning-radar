"""Beverage format follow-up on frozen Wave 2 and existing Streamlit assignments."""
from pathlib import Path
import hashlib
import re
import sys
import unicodedata
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EDA=HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
sys.path.insert(0,str(HERE))
from shared_feature_diagnostics_v1 import KEY, read_master
from juice_classification_v1 import decide as juice_decide, VERSION as JUICE_VERSION, NAMED

REPORT=HERE/"beverages_CHECK_v1.md"
METRICS=["energy","sugars","protein","fat","salt"]
def norm(x):
    return re.sub(r"[-_]"," ",unicodedata.normalize("NFKD",str(x).lower()).encode("ascii","ignore").decode())
def pattern(text,expr):return bool(re.search(r"\b(?:"+expr+r")\b",text))
def refine_original(row):
    """Original analytical label, retained deterministically for the correction audit."""
    name=norm(row.product_name)
    tags=norm(row.off_categories)
    tags=re.sub(r"juices? (?:and|et) nectars?|jus et nectars?"," ",tags)
    text=name+" "+tags
    subtype=row.subtype; basis=row.basis_group
    if row.membership!="YES":return "scope unresolved"
    if pattern(name,"meal replacement|boisson repas|repas a boire|nutrition shake|meal shake"):
        return "basis/form unresolved"
    if basis=="per_100ml_liquid":
        if subtype=="ALCOHOLIC_STYLE":
            candidates=[k for k,p in [("beer",r"beers?|bieres?|lager|cerveza"),("wine",r"wines?|vins?|vinho"),
                         ("cider",r"ciders?|cidres?"),("spirits/liqueurs",r"vodka|whisk(?:ey|y)|rhum|rum|liqueurs?|gin|tequila"),
                         ("cocktail/alcohol-style",r"cocktails?|mocktails?|spritz")] if pattern(text,p)]
            return "alcohol: "+candidates[0] if len(candidates)==1 else "alcohol: unresolved/conflicting"
        if subtype=="JUICE_SMOOTHIE_NECTAR":
            if pattern(text,"smoothies?"):return "smoothie"
            if pattern(text,"nectars?|nektar"):return "nectar"
            if pattern(text,"juice drinks?|juice cocktails?|boissons? aux fruits|fruit drinks?"):return "fruit drink"
            return "juice" if pattern(text,"juices?|jus|zumos?") else "juice family unresolved"
        if subtype=="TEA_COFFEE_RTD":
            a=pattern(text,"coffee|cafe|cold brew");b=pattern(text,"tea|the|icedtea|icetea")
            return "iced coffee" if a and not b else "iced tea" if b and not a else "tea/coffee RTD unresolved"
        if subtype=="PLANT_DRINK":
            bases=[k for k,p in [("oat","oat|avoine"),("soy","soy|soya|soja"),("almond","almond|amande"),
                                 ("rice","rice|riz"),("coconut","coconut|coco")] if pattern(text,p)]
            return "plant drink: "+bases[0] if len(bases)==1 else "plant drink: mixed/unresolved"
        if subtype=="ENERGY_SPORTS_DRINK":
            energy=pattern(text,"energy drinks?|boissons? energisantes?|red bull|monster")
            sports=pattern(text,"sports? drinks?|electrolyte|isotoni|gatorade|powerade|boissons? isotoniques?")
            return "energy drink" if energy and not sports else "sports/electrolyte drink" if sports and not energy else "energy/sports unresolved"
        if subtype=="WATER":
            if pattern(text,"coconut water|eau de coco"):return "coconut water"
            if pattern(text,"flavou?red water|eaux aromatisees|eau aromatisee|water beverages"):return "flavoured water"
            return "water: unspecified flavour"
        return {"SOFT_DRINK":"soda","FERMENTED_SOFT_DRINK":"fermented soft drink"}.get(subtype,"liquid unresolved")
    if "preparation" in basis:
        if subtype=="SYRUP_CONCENTRATE":return "syrup/concentrate"
        if pattern(text,"electrolyte|sports?|isotoni|hydration"):return "sports powder/tablet preparation"
        if pattern(text,"cocoa|cacao|chocolate|chocolat"):return "chocolate preparation"
        if pattern(text,"coffee|cafe|nescafe"):return "coffee preparation"
        if pattern(text,"tea|the|infusion|tisane"):return "tea/infusion preparation"
        return "other preparation"
    return "basis/form unresolved"

def juice_review(row):
    return (row.membership=="YES" and row.basis_group=="per_100ml_liquid" and
            row.subtype=="JUICE_SMOOTHIE_NECTAR" and refine_original(row) in NAMED|{"juice family unresolved"})

def refine(row):
    return juice_decide(row.product_name,row.off_categories)["identity"] if juice_review(row) else refine_original(row)

def tab(head,rows):
    return "\n".join("| "+" | ".join(map(str,r))+" |" for r in [head,["---"]*len(head),*rows])
def num(x):return f"{x:.2f}" if pd.notna(x) else "—"
def main():
    df,_=read_master()
    m=pd.read_csv(EDA/"subtype_assignments.csv",usecols=KEY+["product_name","off_categories","beverage_view_segment"],dtype=str,keep_default_na=False)
    a=df[df.category.eq("beverages")].merge(m,on=KEY,validate="one_to_one")
    assert len(a)==117596 and not a.duplicated(KEY).any()
    a["original_analytical_format"]=a.apply(refine_original,axis=1)
    a["juice_family_review_scope"]=a.apply(juice_review,axis=1)
    decisions=[juice_decide(r.product_name,r.off_categories) if r.juice_family_review_scope else None for r in a.itertuples()]
    a["analytical_format"]=[d["identity"] if d else original for d,original in zip(decisions,a.original_analytical_format)]
    for target,source in [("juice_classification_confidence","confidence"),("juice_classification_reason","reason"),
                          ("juice_name_evidence","name_evidence"),("juice_tag_evidence","tag_evidence")]:
        a[target]=[d[source] if d else "" for d in decisions]
    a["juice_classification_version"]=JUICE_VERSION
    a["juice_correction_applied"]=a.analytical_format.ne(a.original_analytical_format)
    assert not a.loc[~a.juice_family_review_scope,"juice_correction_applied"].any()
    a["comparable_liquid"]=a.basis_group.eq("per_100ml_liquid")&a.membership.eq("YES")&~a.analytical_format.str.contains("unresolved")
    a["composition_band"]=pd.Series(pd.NA,index=a.index,dtype="string")
    ok=a.comparable_liquid&a.sugars.notna()
    a.loc[ok,"composition_band"]=np.select([a.loc[ok,"sugars"].le(.5),a.loc[ok,"sugars"].ge(5)],
                                               ["sugars ≤0.5 g/100ml","sugars ≥5 g/100ml"],default="intermediate sugars")
    a["retained_profile"]=pd.Series(pd.NA,index=a.index,dtype="string")
    retained=ok&a.analytical_format.isin(["soda","energy drink"])
    a.loc[retained,"retained_profile"]=np.where(a.loc[retained,"sugars"].le(.5),
                                              "very-low-sugars formulation","outside very-low-sugars profile")
    out=HERE/"beverage_assignments_v1.parquet"
    a[KEY+["subtype","membership","confidence","beverage_view_segment","basis_group","product_name","analytical_format","comparable_liquid","composition_band","retained_profile",
           "original_analytical_format","juice_family_review_scope","juice_classification_confidence","juice_classification_reason",
           "juice_name_evidence","juice_tag_evidence","juice_classification_version","juice_correction_applied"]].to_parquet(out,index=False)
    check=pd.read_parquet(out)
    assert check.barcode.equals(a.barcode) and len(check)==117596
    counts=[];availability=[];nutrition=[];bands=[];contrasts=[];density=[];examples=[]
    for k,g in a.groupby(["beverage_view_segment","region"]):counts.append([*k,len(g)])
    for (form,reg),g in a.groupby(["analytical_format","region"]):
        available=[int(g[m].notna().sum()) for m in METRICS]
        availability.append([form,reg,len(g),*available])
        if not g.comparable_liquid.all():continue
        for m in METRICS:
            v=g[m].dropna()
            nutrition.append([form,reg,m,len(v),num(v.quantile(.1)),num(v.quantile(.25)),num(v.median()),num(v.quantile(.75)),num(v.quantile(.9))])
        s=g.sugars.dropna()
        bounds=[.1,.5,1,2,5]
        bands.append([form,reg,len(s),*[int(s.le(v).sum()) for v in bounds],int(s.ge(5).sum()),
                      int(s.eq(0).sum())])
        for label,mask in [("≤0.5",g.sugars.le(.5)),("0.5–5",g.sugars.gt(.5)&g.sugars.lt(5)),("≥5",g.sugars.ge(5))]:
            z=g[mask]
            contrasts.append([form,reg,label,len(z),*[num(z[m].median()) for m in METRICS],
                              int(z.energy.count()),int(z.protein.count())])
        # Protein concentrations contextualize plant bases separately from energy ratios.
        if form.startswith("plant drink"):
            valid=g[g.energy.ge(10)&g.protein.notna()]
            both=g.protein.notna()&g.energy.notna()
            density.append([form,reg,len(g),int(g.protein.count()),int(g.protein.ge(2).sum()),len(valid),
                            int((g.energy.eq(0)&g.protein.notna()).sum()),int((g.energy.between(0,10,inclusive="neither")&g.protein.notna()).sum())])
        if form in ["soda","iced tea","energy drink"] and reg in ["FR","UK-IE"]:
            lo=g[g.sugars.le(.5)]; hi=g[g.sugars.ge(5)]
            if min(len(lo),len(hi))<20:continue
            for label,z,goal in [("typical very-low sugars",lo,lo.sugars.median()),
                                 ("near inside",lo,.5),("near outside",g[g.sugars.gt(.5)],.5),
                                 ("typical higher sugars",hi,hi.sugars.median())]:
                z=z[z.product_name.ne("")]
                if len(z):
                    r=z.assign(dist=(z.sugars-goal).abs()).sort_values(["dist","barcode"]).iloc[0]
                    examples.append([form,reg,label,r.barcode,r.product_name.replace("|","/"),num(r.sugars),num(r.energy)])
    # Joint measurement counts for the exact sugar/energy comparison.
    joint=[]
    for (form,reg),g in a[a.comparable_liquid].groupby(["analytical_format","region"]):
        z=g.dropna(subset=["sugars","energy"])
        low=z.sugars.le(.5);high=z.sugars.ge(5)
        if len(z):
            rtd=z.beverage_view_segment.eq("ready_to_drink_beverages")
            alt="UK-IE" if reg=="FR" else "FR"
            unseen=~z.barcode.isin(a.loc[a.region.eq(alt),"barcode"])
            for label,mask in [("all",pd.Series(True,index=z.index)),("Streamlit RTD only",rtd),("unshared GTIN",unseen)]:
                c=z[mask]; l=c[c.sugars.le(.5)];h=c[c.sugars.ge(5)]
                joint.append([form,reg,label,len(c),len(l),len(h),num(l.energy.median()),num(h.energy.median()),
                              int(c.sugars.le(.1).sum()),int(c.sugars.le(1).sum()),int(l.energy.gt(20).sum())])
    panels=[
        ("Streamlit split, retained exactly",["View","Region","Assignments"],counts),
        ("Format coverage and individual nutrient availability",["Form","Region","Assignments","Energy N","Sugars N","Protein N","Fat N","Salt N"],availability),
        ("Comparable liquids, existing-valid values",["Form","Region","Metric","N","P10","Q1","Median","Q3","P90"],nutrition),
        ("Sugar thresholds and zeros",["Form","Region","Valid sugars","≤0.1","≤0.5","≤1","≤2","≤5","≥5","Observed zero"],bands),
        ("Composition by sugar band",["Form","Region","Sugars band","N",*METRICS,"Energy N","Protein N"],contrasts),
        ("Joint sugar/energy population and sensitivity",["Form","Region","Restriction","Joint N","≤0.5 N","≥5 N","Energy median ≤0.5","Energy median ≥5","≤0.1 N","≤1 N","Very-low-sugars with energy >20"],joint),
        ("Plant-base protein evidence",["Form","Region","Assignments","Valid protein","Protein ≥2 N","Valid protein and energy ≥10","Zero-energy denominator","0<E<10"],density),
        ("Product examples",["Form","Region","Example","Text GTIN","Recorded name","Sugars","Energy"],examples)]
    intro=REPORT.read_text(encoding="utf8").split("<!-- evidence -->")[0] if REPORT.exists() else "# Beverages · format-first formulation CHECK\n\n"
    updates={"Juice":"Retain composition-based commercial types and observed variation. The population and distributions below use the corrected 19 November name/tag rule; no additional nutritional profile is proposed.",
             "Nectar":"Retain the independently supported commercial form. Conflicting juice names and nectar tags remain unresolved; no further nutritional subdivision is proposed.",
             "Smoothie":"Retain independently supported smoothies and observed nutritional variation. Nested juice-family tags do not create a second product or a new nutritional profile.",
             "Fruit drinks":"Use explicit fruit-drink evidence, not the broad parent tag ‘boissons aux fruits’. Rebuilt distributions replace the earlier mixture of juices and fruit drinks; the earlier France–UK contrast is withdrawn."}
    for form,message in updates.items():
        intro=re.sub(r"(?m)^\| \*\*"+re.escape(form)+r"\*\* \|.*$",lambda m:"| **"+form+"** | "+message+" |",intro)
    intro=intro.replace("Beverage research remains open pending the [juice follow-up](juice_formulations_v1.md).",
        "The researched formulation chapter closed on 16 November; the bounded juice-classification correction was completed on 19 November. [Correction CHECK](juice_classification_CHECK_v1.md).")
    intro=intro.replace("It removes umbrella juice/nectar tag phrases before assigning finer fruit-drink forms.",
        "It uses juice_classification_v1.py to distinguish specific identities from broad parent tags, retain conflicting evidence as unresolved, and preserve original analytical labels.")
    body="\n\n".join("<details><summary>"+title+"</summary>\n\n"+tab(head,rows)+"\n\n</details>" for title,head,rows in panels)
    REPORT.write_text(intro+"<!-- evidence -->\n\n"+body+"\n",encoding="utf8")
    print("Verified",len(a),"assignments; comparable liquids",a.comparable_liquid.sum())
if __name__=="__main__":main()
