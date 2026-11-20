"""Classify Wave 2 snack assignments using commercial evidence, then profile nutrients."""
from pathlib import Path
import re
import sys
import unicodedata
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EDA=HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import KEY,read_master

PRIMARY=["potato crisps","tortilla/corn chips","puffed/extruded"]
METRICS=["fat","saturated_fat","salt","protein","fibre","energy"]
BROAD={"CHIPS_CRISPS_PUFFS","POPCORN","CRACKERS_PRETZELS","NUTS_SEEDS_SNACK_MIX"}
PAT={
 "potato crisps":r"\b(?:potatoe? (?:chips?|crisps?)|chips? (?:de |a base de )?pommes? de terre|patatas fritas|crisps? made from potatoes)\b",
 "tortilla/corn chips":r"\b(?:tortilla chips?|tortillas? (?:de mais|chips)|corn (?:chips?|crisps?)|chips? (?:de|au) mais|nacho chips?)\b",
 "puffed/extruded":r"\b(?:extrud\w*|cheese (?:puffs?|curls?|balls?)|(?:corn|lentil|chickpea|pea|rice|protein|quinoa|millet) puffs?|puffed (?:corn|rice|snacks?|chips?)|souffles? (?:aperitifs?|au|de)|snacks? souffles?|boules? (?:de mais|au fromage)|popped (?:corn|potato|rice) chips?)\b",
 "popcorn":r"\bpop ?corn\b","pretzels":r"\b[ bp]?retzels?\b|\bbretzels?\b",
 "savoury crackers":r"\b(?:crackers?|biscuits? aperitifs?|biscuits? sales?)\b",
 "nuts/seeds":r"\b(?:mixed nuts|roasted (?:nuts|peanuts|cashews|almonds|seeds)|(?:peanuts|cashews|almonds|nuts|seeds) (?:roasted|salted)|snacking nuts|(?:noix|graines|amandes|arachides|cacahuetes) (?:grillees?|salees?))\b",
 "other chips":r"\b(?:(?:sweet potato|vegetable|plantain|banana|lentil|pita|quinoa|hummus|chickpea|beetroot|rice) (?:chips?|crisps?)|chips? de (?:legumes|lentilles|banane|betterave|patate douce))\b",
 "breadsticks":r"\b(?:breadsticks?|gressins?)\b","rice cakes":r"\b(?:rice cakes?|galettes? de riz)\b",
 "savoury mix":r"\b(?:trail mix|snack mix|melange aperitif)\b","other savoury":r"\b(?:jerky|pork rinds?|wasabi peas|couennes? de porc)\b"}
PAT={k:re.compile(v) for k,v in PAT.items()}
def norm(x):
    return re.sub(r"[-_]"," ",unicodedata.normalize("NFKD",str(x).lower()).encode("ascii","ignore").decode())
def forms(t):
    t=re.sub(r"biscuits and crackers|chips and fries|chips et frites|cereals and potatoes"," ",t)
    if "sweet potato" in t:t=t.replace("sweet potato chips","vegetable chips").replace("sweet potato crisps","vegetable crisps")
    return {k for k,p in PAT.items() if p.search(t)}
def classify(row):
    name=norm(row.product_name);tags=norm(row.off_categories);t=name+" "+tags
    n,b=forms(name),forms(tags)
    if re.search(r"\b(?:popped|pop chips?|pop'd|pop outs?|lentil curls?|potato hoops?|corn hoops?|potato spirals?|corn rings?)\b",name) and not re.search(r"pop ?corn",name):
        n.add("puffed/extruded")
    if re.search(r"chips? (?:bio )?de (?:pois chiche|manioc|lentilles)|lentil (?:crisps?|chips?)",name):n.add("other chips")
    hits=n|b
    savoury=row.subtype in BROAD or bool(hits) or bool(re.search(r"salty snacks|snacks sales|savoury snacks",tags))
    if not savoury: return ("outside screen","", "", "", "")
    if row.membership!="YES": return ("scope unresolved","governed "+row.membership,"","","")
    if row.subtype in {"SWEET_BAKERY","CHOCOLATE_CONFECTIONERY","SUGAR_CONFECTIONERY","CEREAL_PROTEIN_SNACK_BAR","FROZEN_DESSERT","FRUIT_SNACKS","BISCUITS_WAFERS"} or re.search(r"caramel(?:ized)? (?:pop ?corn|nuts)|(?:pop ?corn|cacahuetes) (?:au caramel|sucre)|chocolate covered|kettle corn|breakfast cereals?|cereales (?:pour |du )?petit dejeuner|crispbreads?|pains? croustillants?|baby foods?|baby snacks?|cracottes?|fruity puffs|fingerfoods|cookie crisp|goutine|toast[s]? apero",t):
        return ("scope caution","sweet or mixed context","","","")
    # Puffed construction can coexist with an explicit corn/potato/pulse base.
    if "puffed/extruded" in hits and hits<={"puffed/extruded","potato crisps","tortilla/corn chips","other chips"}: form="puffed/extruded"
    elif len(hits)==1:form=next(iter(hits))
    elif len(hits)>1:form="conflicting"
    else:form="unresolved"
    evidence="name="+",".join(sorted(n))+"; tags="+",".join(sorted(b))
    def label(patterns):
        return "+".join(k for k,p in patterns if re.search(p,t)) or "unspecified"
    flavour=label([("cheese",r"cheese|fromage|cheddar"),("barbecue",r"barbecue|\bbbq\b"),("spiced",r"paprika|chili|chilli|piment"),("vinegar",r"vinegar|vinaigre"),("plain/salt wording",r"ready salted|sea salt|sel de mer|\bnature\b|\boriginal\b")])
    construction=label([("baked",r"\bbaked\b|au four"),("kettle",r"kettle|chaudron"),("ridge",r"ridged|crinkle|ondul"),("popped",r"\bpopped\b|pop chips?|pop'd"),("stacked",r"stacked|reconstitue")])
    material=label([("pulse",r"lentil|lentill|chickpea|pois chiche|pea protein"),("corn",r"\bcorn\b|\bmais\b"),("rice",r"\brice\b|\briz\b"),("potato",r"potato|pomme de terre")])
    return form,evidence,flavour,construction,material

def fmt(x):return f"{x:.2f}" if pd.notna(x) else "—"
def table(head,rows):
    return "\n".join("| "+" | ".join(map(str,row))+" |" for row in [head,["---"]*len(head),*rows])
def main():
    df,_=read_master()
    meta=pd.read_csv(EDA/"subtype_assignments.csv",usecols=KEY+["product_name","off_categories"],dtype=str)
    a=df[df.category.eq("snacks")].merge(meta,on=KEY,validate="one_to_one")
    assert len(a)==151461
    labels=["savoury_format","format_evidence","flavour","construction","base_wording"]
    a[labels]=pd.DataFrame([classify(r) for r in a.itertuples()],index=a.index)
    # Persist the measured low-fat screen separately from commercial format.
    a["fat_le20_screen"]=pd.Series(pd.NA,index=a.index,dtype="boolean")
    target=a.savoury_format.isin(PRIMARY)&a.basis_group.eq("per_100g_food")
    ok=target&a.fat.notna()
    a.loc[ok,"fat_le20_screen"]=a.loc[ok,"fat"].le(20)
    a["formulation_profile"]=pd.Series(pd.NA,index=a.index,dtype="string")
    potato=ok&a.savoury_format.eq("potato crisps")
    a.loc[potato,"formulation_profile"]=np.where(a.loc[potato,"fat"].le(20),"lower-fat potato crisps","outside lower-fat profile")
    out=HERE/"savoury_snack_assignments_v1.parquet"
    a[KEY+["membership","subtype","confidence","basis_group","product_name"]+labels+["fat_le20_screen","formulation_profile"]].to_parquet(out,index=False)
    saved=pd.read_parquet(out)
    assert len(saved)==151461 and not saved.duplicated(KEY).any() and saved.barcode.equals(a.barcode)
    counts=a.groupby(["savoury_format","region"]).size().unstack(fill_value=0)
    coverage=[];screens=[];bins=[];contrasts=[];wording=[];examples=[];robust=[];saturates=[]
    for (form,reg),g in a[target].groupby(["savoury_format","region"]):
        for m in METRICS:
            v=g[m].dropna(); coverage.append([form,reg,m,len(g),len(v),f"{len(v)/len(g):.0%}",*[fmt(v.quantile(q)) for q in [.1,.25,.5,.75,.9]]])
        b=g.dropna(subset=["fat"]);low=b.fat.le(20)
        # Inspect saturated-fat differences at approximately the same total fat.
        band=b[b.fat.between(20,25)&b.saturated_fat.between(0,b.fat)]
        share=band.saturated_fat/band.fat
        saturates.append([form,reg,len(band),fmt(band.saturated_fat.median()),fmt(band.saturated_fat.quantile(.9)),
                          *[int(share.ge(v).sum()) for v in [.25,.30,.35]]])
        alt="UK-IE" if reg=="FR" else "FR"
        for check,z in [("explicit form in name",g[g.format_evidence.str.split(";").str[0].str.contains(form,regex=False)]),
                        ("GTIN absent in "+alt,g[~g.barcode.isin(a.loc[a.region.eq(alt),"barcode"])]),
                        ("construction unspecified",g[g.construction.eq("unspecified")])]:
            v=z.dropna(subset=["fat"])
            hi=z.protein.dropna()
            robust.append([form,reg,check,len(v),int(v.fat.le(20).sum()),len(hi),int(hi.ge(10).sum())])
        if form=="puffed/extruded":
            for check,z in g.groupby("base_wording"):
                v=z.dropna(subset=["fat"]);hi=z.protein.dropna()
                robust.append([form,reg,"base: "+check,len(v),int(v.fat.le(20).sum()),len(hi),int(hi.ge(10).sum())])
        screens.append([form,reg,len(b),*[int(b.fat.le(t).sum()) for t in [15,18,20,22,25]],f"{low.mean():.1%}"])
        bins.append([form,reg,*pd.cut(b.fat,[-1,10,15,20,25,30,35,40,101],right=True).value_counts(sort=False).tolist()])
        def contrast(label,z):
            arms=[z[z.fat.le(20)],z[z.fat.gt(20)]]
            if min(map(len,arms))<3:return
            contrasts.append([form,reg,label,*map(len,arms),*[" / ".join(fmt(x[m].median()) for x in arms) for m in METRICS]])
        contrast("all",b)
        for field,values in [("construction",["baked","kettle","unspecified"]),("flavour",["cheese","plain/salt wording","unspecified"]),("base_wording",["pulse","corn","rice"])]:
            for v in values:
                z=b[b[field].eq(v)]
                if len(z)>=20:contrast(v+" ("+field+")",z)
        # Compare low-fat to higher-fat peers with identical construction/flavour and, for puffs, base cues.
        strata=["construction","flavour"]+(["base_wording"] if form=="puffed/extruded" else [])
        for m in ["energy","protein","salt","saturated_fat","fibre"]:
            diffs=[]; weights=[]
            for _,z in b.dropna(subset=[m]).groupby(strata):
                l=z[z.fat.le(20)];u=z[z.fat.gt(20)]
                if min(len(l),len(u))>=3:
                    diffs.append(l[m].median()-u[m].median());weights.append(len(l))
            wording.append([form,reg,m,len(diffs),sum(weights),fmt(np.average(diffs,weights=weights)) if weights else "—"])
        if form=="potato crisps" and reg in ["FR","UK-IE"]:
            for label,mask in [("typical",low),("near inside",low),("near outside",~low)]:
                z=b[mask&b.product_name.fillna("").ne("")]; goal=b.loc[low,"fat"].median() if label=="typical" else 20
                if len(z):
                    u=z.assign(dist=(z.fat-goal).abs()).sort_values(["dist","barcode"]).iloc[0]
                    examples.append([reg,label,u.barcode,str(u.product_name).replace("|","/"),u.construction,*[fmt(u[m]) for m in ["fat","energy","protein","salt"]]])
    panels=[("Commercial screen",table(["Outcome",*counts.columns],[[k,*v] for k,v in counts.iterrows()])),
            ("Coverage and variation per 100 g",table(["Form","Region","Nutrient","N","Valid","Coverage","P10","Q1","Median","Q3","P90"],coverage)),
            ("Lower-fat sensitivity",table(["Form","Region","Valid fat","≤15 g","≤18 g","≤20 g","≤22 g","≤25 g","Share ≤20 g"],screens)),
            ("Saturated fat at 20–25 g total fat",table(["Form","Region","Valid pair","Median saturated fat","P90","Share ≥25% N","Share ≥30% N","Share ≥35% N"],saturates)),
            ("Fat distribution, counts by upper bin edge (g)",table(["Form","Region","10","15","20","25","30","35","40","above 40"],bins)),
            ("Composition, low / other fat medians",table(["Form","Region","Restriction","≤20 N",">20 N",*METRICS],contrasts)),
            ("Difference within comparable wording strata",table(["Form","Region","Nutrient","Supported strata","Lower-fat products represented","Lower minus other"],wording)),
            ("Commercial and regional sensitivities",table(["Form","Region","Restriction","Valid fat","Fat ≤20","Valid protein","Protein ≥10"],robust))]
    return panels,examples

if __name__=="__main__":
    panels,examples=main()
    p=HERE/"savoury_snacks_CHECK_v1.md"
    intro=p.read_text(encoding="utf8").split("<!-- evidence -->")[0] if p.exists() else "# Savoury snacks · Wave 2 formulation CHECK\n\n"
    panels.append(("Potato crisp examples",table(["Region","Example","GTIN","Name","Construction","Fat","Energy","Protein","Salt"],examples)))
    p.write_text(intro+"<!-- evidence -->\n\n"+"\n\n".join("<details><summary>"+title+"</summary>\n\n"+body+"\n\n</details>" for title,body in panels)+"\n",encoding="utf8")
