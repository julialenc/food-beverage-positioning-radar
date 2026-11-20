"""Shared accepted Wave 2 analytical rules; no research runners or provider calls.

Commercial decisions are inherited from approved keyed layers. The two formerly
embedded dairy/biscuit classifiers are reproduced here and independently checked
against their research implementations by the acceptance verifier.
"""
import re
import unicodedata
import numpy as np
import pandas as pd

VERSION="wave2_analytical_v1"
KEY=["barcode","region","category"]
RAW=dict(energy="energy_kcal",protein="protein_100g",fat="fat_100g",saturated_fat="saturated_fat_100g",
         carbohydrates="carbs_100g",sugars="sugars_100g",fibre="fiber_100g",salt="salt_100g")
PROFILE_IDS={"granola":"GRANOLA_LOWER_SUGARS_HIGHER_PROTEIN","dessert cream/pudding":"PUDDING_HIGHER_PROTEIN_LOWER_ENERGY",
             "potato crisps":"POTATO_CRISPS_LOWER_FAT","soda":"SODA_VERY_LOW_SUGARS","energy drink":"ENERGY_DRINK_VERY_LOW_SUGARS"}
PROFILE_RULES={"granola":"sugars <=14 and protein >=11 g/100g",
               "dessert cream/pudding":"protein >=8 g/100g and 10<=energy<=110 kcal/100g",
               "potato crisps":"fat <=20 g/100g","soda":"sugars <=0.5 g/100ml","energy drink":"sugars <=0.5 g/100ml"}
EXPECTED_PROFILES={"granola":[251,94,121],"dessert cream/pudding":[27,15,1],"potato crisps":[100,90,53],
                   "soda":[713,255,96],"energy drink":[153,88,97]}
REGIONS=["FR","UK-IE","US-CA"]


def norm(value):
    return re.sub(r"[-_]"," ",unicodedata.normalize("NFKD",str(value).lower()).encode("ascii","ignore").decode())


DAIRY_PATTERNS={"rice pudding":r"rice pudding|riz au lait|arroz con leche","semolina":r"semolina|semoule au lait|gateau de semoule",
    "flan":r"\bflans?\b|cremes? caramel|cremes? renversees?","dessert cream / pudding":r"cremes? desserts?|\bpuddings?\b|\bpudins?\b",
    "mousse":r"\bmousses?\b","creme brulee":r"cremes? brulees?","panna cotta":r"panna cotta","tiramisu":r"tiramis[uù]","custard":r"\bcustards?\b"}
DAIRY_FLAG=r"instant|poudre|powder|pie filling|dessert sauces?|baby foods?|aliments pour bebes|frozen desserts?|ice cream|cremes? glacees?"


def dairy_cues(text):
    text=re.sub(r"entremets\s+mousses et cremes? desserts?|custards? and pastry creams?"," ",text)
    if re.search(DAIRY_PATTERNS["rice pudding"],text):text=re.sub("rice puddings?","rice form",text);rice=True
    else:rice=False
    found={k for k,p in DAIRY_PATTERNS.items() if re.search(p,text)}
    if rice:found.add("rice pudding")
    return found


def dairy_format(row):
    name,tags=norm(row.product_name),norm(row.off_categories)
    if re.search(DAIRY_FLAG,name+" "+tags):return "scope caution"
    found=dairy_cues(name)|dairy_cues(tags)
    if found & {"rice pudding","semolina"}:found.discard("dessert cream / pudding")
    if len(found)==1:return found.pop()
    return "conflicting cues" if found else "unspecified"


def biscuit_format(row):
    name,tags=norm(row.product_name),norm(row.off_categories)
    tags=re.sub(r"biscuits? (?:and|et) (?:cakes?|gateaux|crackers?)"," ",tags)
    text=name+" "+tags
    wafer=bool(re.search(r"\b(wafers?|gaufrettes?|oblea[s]?|waffelblaettchen)\b",text))
    specific=bool(re.search(r"\b(cookies?|shortbread|sables?|speculoos|digestives?|palets bretons|galettes bretonnes)\b",text))
    biscuit=specific or bool(re.search(r"\b(biscuits?|galletas?)\b",text))
    if re.search(r"\b(macaroons?|macarons?|crackers?|pretzels?|pancakes?|waffles?|gaufres?|ice cream|glaces?|cookie dough|biscuit mix|palmiers?|moelleux|banana wafers?|potato wafers?)\b",name) or re.search(r"\b(crackers?|macarons?|ice creams?)\b",tags):form="scope caution"
    elif wafer and specific:form="conflicting"
    elif wafer:form="wafer"
    elif biscuit:form="biscuit"
    else:form="unresolved"
    filled=bool(re.search(r"\b(filled|fourre\w*|sandwich\w*|filling|rellen\w*)\b",text))
    coated=bool(re.search(r"\b(coat(?:ed|ing)|cover(?:ed|ing)|enrob\w*|napp\w*|recouvert\w*|dipped)\b",text))
    return form,"both" if filled and coated else "filled" if filled else "coated" if coated else "unspecified"


def nutrition(frame):
    """Exact existing validity gates, with source values kept in separate columns."""
    for metric,field in RAW.items():
        observed,working,missing=frame[field+"_off_raw"],frame[field],frame[field+"_missing"]
        in_range=working.between(0,900 if metric=="energy" else 50 if metric=="salt" else 100)
        valid=in_range & working.eq(observed) & missing.eq(0)
        frame[metric]=working.where(valid)
        state=pd.Series("VALID_RECORDED",index=frame.index)
        state.loc[~in_range]="OUTSIDE_ACCEPTED_RANGE"
        state.loc[~working.eq(observed)]="WORKING_SOURCE_DISAGREEMENT"
        state.loc[~missing.eq(0)]="SOURCE_MISSING_FLAG"
        state.loc[working.isna()]="WORKING_NULL"
        frame[metric+"_validity"]=state
    frame["protein_per100kcal"]=100*frame.protein/frame.energy.where(frame.energy.gt(0))
    frame["fibre_per100kcal"]=100*frame.fibre/frame.energy.where(frame.energy.gt(0))
    frame["energy_denominator_status"]=np.select([frame.energy.isna(),frame.energy.eq(0),frame.energy.lt(10)],
        ["MISSING_OR_INVALID","ZERO_UNDEFINED","VERY_LOW_ENERGY"],default="AT_LEAST_10_KCAL")
    return frame


def peer_mask(a):
    return (a.product_scope_eligible & a.membership.eq("YES") & ~a.subtype.isin(["OTHER","UNRESOLVED"]) &
            a.basis_group.isin(["per_100g_food","per_100ml_liquid"]) & a.cereal_bar_review_flag.ne("True"))


def classify(a):
    a["peer"]=peer_mask(a)
    dessert=a.peer & a.category.eq("dairy") & a.subtype.eq("DAIRY_DESSERT")
    biscuit=a.peer & a.category.eq("snacks") & a.subtype.eq("BISCUITS_WAFERS")
    a["dairy_format"]=pd.Series(pd.NA,index=a.index,dtype="string")
    a.loc[dessert,"dairy_format"]=[dairy_format(r) for r in a.loc[dessert].itertuples()]
    a["biscuit_format"]=pd.Series(pd.NA,index=a.index,dtype="string")
    a["biscuit_construction"]=pd.Series(pd.NA,index=a.index,dtype="string")
    pairs=[biscuit_format(r) for r in a.loc[biscuit].itertuples()]
    if pairs:a.loc[biscuit,["biscuit_format","biscuit_construction"]]=np.array(pairs,dtype=object)
    a["commercial_format"]=a.subtype.astype("string").str.lower().str.replace("_"," ")
    a["commercial_source"]="accepted baseline classification"
    a["format_confidence"]=a.confidence.astype("string")
    a.loc[dessert,"commercial_format"]=a.loc[dessert,"dairy_format"]
    a.loc[dessert,"commercial_source"]="accepted dairy name/tag rule"
    a.loc[biscuit,"commercial_format"]=a.loc[biscuit,"biscuit_format"]
    a.loc[biscuit,"commercial_source"]="accepted biscuit/wafer name/tag rule"
    take=a.savoury_format.notna() & ~a.savoury_format.isin(["outside screen","scope caution","scope unresolved"]) & ~biscuit
    a.loc[take,"commercial_format"]=a.loc[take,"savoury_format"]
    a.loc[take,"commercial_source"]="accepted savoury keyed layer"
    take=a.analytical_format.notna()
    a.loc[take,"commercial_format"]=a.loc[take,"analytical_format"]
    a.loc[take,"commercial_source"]="accepted corrected beverage keyed layer"
    reviewed=a.juice_family_review_scope.eq(True).fillna(False)
    a.loc[reviewed,"format_confidence"]=a.loc[reviewed,"juice_classification_confidence"]
    status=pd.Series("RESOLVED_TEXTUAL_OR_GOVERNED",index=a.index)
    fmt=a.commercial_format.fillna("")
    status.loc[fmt.str.contains("other") ]="OTHER"
    status.loc[fmt.str.contains("unresolved|unspecified|unknown|unclear",regex=True)]="UNRESOLVED"
    status.loc[fmt.str.contains("conflict|ambiguous",regex=True)]="CONFLICTING"
    status.loc[fmt.str.contains("caution|concern",regex=True)]="COMPARABILITY_CONCERN"
    status.loc[a.membership.eq("UNKNOWN")]="UNRESOLVED"
    status.loc[a.membership.eq("NO")|a.subtype.eq("OUT")]="OUTSIDE_REVIEWED_FORMAT"
    status.loc[~a.product_scope_eligible]="OUTSIDE_PRODUCT_SCOPE"
    a["commercial_status"]=status
    use=pd.Series("OBSERVED_ANALYTICAL_POPULATION",index=a.index)
    use.loc[status.eq("OUTSIDE_REVIEWED_FORMAT")]="OUTSIDE_REVIEWED_FORMAT_BROADER_RECORD_RETAINED"
    use.loc[status.isin(["UNRESOLVED","CONFLICTING","COMPARABILITY_CONCERN"]) ]="FORMAT_UNRESOLVED_BROADER_CATEGORY_RETAINED"
    use.loc[a.basis_group.fillna("").str.contains("preparation|unresolved") ]="BASIS_DEFERRED_OR_UNVERIFIED"
    use.loc[fmt.str.startswith("alcohol:")]="ALCOHOL_EXCLUDED_FROM_NUTRITIONAL_SEGMENTATION"
    use.loc[~a.product_scope_eligible]="OUTSIDE_PRODUCT_SCOPE"
    a["analytical_use_status"]=use
    a["geography_role"]=np.where(a.region.eq("US-CA"),"SELECTED_EXPLORATORY","PRIMARY_REFERENCE")
    return a


def profiles(a):
    a["profile_family"]=pd.Series(pd.NA,index=a.index,dtype="string")
    a["profile_status"]=np.where(a.product_scope_eligible,"NOT_INVESTIGATED_OR_NOT_APPLICABLE","OUTSIDE_PRODUCT_SCOPE")
    a["profile_id"]=pd.Series(pd.NA,index=a.index,dtype="string")
    a["profile_rule"]=pd.Series(pd.NA,index=a.index,dtype="string")
    plans=[("granola",a.h2_format_candidate.eq(True)&a.effective_type_code.eq("GRANOLA"),["sugars","protein"],a.sugars.le(14)&a.protein.ge(11)),
           ("dessert cream/pudding",a.peer&a.subtype.eq("DAIRY_DESSERT")&a.dairy_format.eq("dessert cream / pudding"),["protein","energy"],a.protein.ge(8)&a.energy.le(110)),
           ("potato crisps",a.savoury_format.eq("potato crisps")&a.basis_group.eq("per_100g_food"),["fat"],a.fat.le(20)),
           ("soda",a.analytical_format.eq("soda")&a.comparable_liquid.eq(True),["sugars"],a.sugars.le(.5)),
           ("energy drink",a.analytical_format.eq("energy drink")&a.comparable_liquid.eq(True),["sugars"],a.sugars.le(.5))]
    for family,pop,fields,predicate in plans:
        pop=pop.fillna(False)&a.product_scope_eligible
        assert a.loc[pop,"profile_family"].isna().all(),"Overlapping approved profile populations"
        known=a[fields].notna().all(axis=1)
        if family=="dessert cream/pudding":known &= a.energy.ge(10)
        a.loc[pop,"profile_family"]=family;a.loc[pop,"profile_rule"]=PROFILE_RULES[family]
        a.loc[pop,"profile_status"]=np.where(known[pop],np.where(predicate[pop],"IN_PROFILE","OTHER_MEASURABLE"),"REQUIRED_MEASUREMENT_UNKNOWN")
        a.loc[pop&known&predicate,"profile_id"]=PROFILE_IDS[family]
    return a


def claim_states(g,prop):
    gate=g.claims_matched.eq(True)&g.claims_analytical_eligible.eq(True)
    limited=gate&g.claims_source_market_limitation.fillna("").ne("")
    usable=gate&~limited
    functional=prop in ["energy_positioning","hydration_positioning","electrolyte_positioning"]
    value=g["claims_"+prop] if functional else g["claims_claim_"+prop]
    pos=usable&value.eq(True).fillna(False)
    if functional:
        neg=usable&value.eq(False).fillna(False);human=pd.Series(False,index=g.index);uncertain=human.copy()
    else:
        state=g["claims_state_"+prop]
        neg=usable&value.eq(False).fillna(False)&state.eq("DOCUMENTED_NOT_DETECTED").fillna(False)
        human=usable&value.eq(False).fillna(False)&state.eq("HUMAN_CONFIRMED_NEGATIVE").fillna(False)
        uncertain=usable&state.eq("UNCERTAIN").fillna(False)
    return dict(positive_n=pos,documented_non_detection_n=neg,human_negative_n=human,uncertain_n=uncertain,
                other_unknown_assessed_n=usable&~(pos|neg|human|uncertain),unassessed_n=~gate,market_limited_n=limited)


def coverage_populations(a):
    """Reproduce the accepted overlapping coverage populations from canonical fields."""
    a=a[a.product_scope_eligible]
    groups=[]
    def add(family,branch,g,profile=False):
        groups.append((family,branch,"commercial population",g))
        if profile:
            for label,state in [("retained profile","IN_PROFILE"),("other measurable","OTHER_MEASURABLE"),("required measurement unknown","REQUIRED_MEASUREMENT_UNKNOWN")]:
                groups.append((family,branch,label,g[g.profile_status.eq(state)]))
    for (cat,sub),g in a[a.peer].groupby(["category","subtype"]):
        if sub!="ALCOHOLIC_STYLE":add("baseline",cat+"/"+sub,g)
    for form in ["GRANOLA","FLAKES"]:
        add("accepted",form.lower(),a[a.h2_format_candidate.eq(True)&a.effective_type_code.eq(form)],form=="GRANOLA")
    for form,g in a[a.peer&a.subtype.eq("DAIRY_DESSERT")].groupby("dairy_format"):
        add("accepted","dessert cream/pudding" if form=="dessert cream / pudding" else "dairy dessert/"+form,g,form=="dessert cream / pudding")
    for field,kind in [("savoury_format","snacks"),("analytical_format","beverages"),("juice_subformat","juice")]:
        for form,g in a[a[field].notna()].groupby(field):
            if form=="outside screen" or form.startswith("alcohol:"):continue
            branch=("juice/" if kind=="juice" else "" if form in ["potato crisps","soda","energy drink"] else kind+"/")+form
            profile=form in ["potato crisps","soda","energy drink"]
            if form=="potato crisps":g=g[g.basis_group.eq("per_100g_food")]
            if form in ["soda","energy drink"]:g=g[g.comparable_liquid.eq(True)]
            add("juice detail" if kind=="juice" else "accepted",branch,g,profile)
    return groups


def communication_coverage(a,props):
    rows=[]
    for family,branch,slice_name,frame in coverage_populations(a):
        for region,g in frame.groupby("region"):
            gate=g.claims_matched.eq(True)&g.claims_analytical_eligible.eq(True)
            usable=gate&g.claims_source_market_limitation.fillna("").eq("")
            for prop in props+["energy_positioning","hydration_positioning","electrolyte_positioning"]:
                if prop in ["energy_positioning","hydration_positioning","electrolyte_positioning"] and not g.category.eq("beverages").all():continue
                states=claim_states(g,prop);counts={name:int(mask.sum()) for name,mask in states.items()}
                assert sum(counts.values())==len(g)
                known=counts["positive_n"]+counts["documented_non_detection_n"]
                rows.append(dict(cohort_family=family,category=g.category.iloc[0],branch=branch,slice=slice_name,region=region,proposition=prop,
                    population_n=len(g),matched_eligible_n=int(gate.sum()),usable_market_n=int(usable.sum()),**counts,known_primary_n=known,
                    known_pct_of_population=100*known/len(g),historical_reuse_n=int((usable&g.claims_evidence_cohort.eq("historical_dairy_reuse")).sum()),
                    qa_note_n=int((usable&g.claims_population_qa_note.fillna("").ne("")).sum()),
                    two_arm_floor=counts["positive_n"]>=20 and counts["documented_non_detection_n"]>=20))
    return pd.DataFrame(rows)


def organic_partition(a):
    """Accepted disjoint processing population; separate from display hierarchy."""
    a=a[a.product_scope_eligible].copy()
    a["commercial_type"]=np.where(a.peer,a.subtype,"unresolved: "+a.subtype)
    a["type_source"]="shared baseline";a["comparison_eligible_type"]=a.peer
    broad={"CHEESE","YOGURT_CULTURED_FRESH","CHOCOLATE_CONFECTIONERY","CEREAL_PROTEIN_SNACK_BAR","SWEET_BAKERY","SUGAR_CONFECTIONERY","FRUIT_SNACKS","FROZEN_DESSERT","PUFFED"}
    a.loc[a.subtype.isin(broad),"comparison_eligible_type"]=False
    dessert=a.peer&a.subtype.eq("DAIRY_DESSERT");biscuit=a.peer&a.subtype.eq("BISCUITS_WAFERS")
    a.loc[dessert,"commercial_type"]=a.loc[dessert,"dairy_format"];a.loc[dessert,"type_source"]="accepted dairy classifier"
    a.loc[biscuit,"commercial_type"]=a.loc[biscuit,"biscuit_format"];a.loc[biscuit,"type_source"]="accepted biscuit/wafer classifier"
    for field,source in [("savoury_format","saved savoury assignments"),("analytical_format","saved beverage assignments"),("juice_subformat","saved juice refinements")]:
        take=a[field].notna()&a[field].ne("outside screen")
        if field=="savoury_format":take &= ~biscuit&~a[field].isin(["scope caution","scope unresolved"])
        a.loc[take,"commercial_type"]=a.loc[take,field];a.loc[take,"type_source"]=source;a.loc[take,"comparison_eligible_type"]=True
    bad=a.commercial_type.str.contains("unresolved|unspecified|ambiguous|conflict|concern|caution|other|alcohol:",case=False,regex=True)
    a.loc[bad|~a.membership.eq("YES"),"comparison_eligible_type"]=False
    return a
