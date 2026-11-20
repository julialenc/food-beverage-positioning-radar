"""Wave 2 design diagnostics. Computes provisional features in memory; fits no model."""
import hashlib
import itertools
import os
import re
import unicodedata
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "01_nutritional_composition"
MASTER = HERE.parents[2] / "01_ingestion/05_master_parquet/output/master_products.parquet"
KEY = ["barcode", "region", "category"]
RAW = dict(energy="energy_kcal", protein="protein_100g", fat="fat_100g",
           saturated_fat="saturated_fat_100g", carbohydrates="carbs_100g", sugars="sugars_100g",
           fibre="fiber_100g", salt="salt_100g")
CORE = ["protein", "fat", "sugars", "salt"]
RATIOS = {"protein_density": ("protein", "energy", 100), "fibre_density": ("fibre", "energy", 100),
          "sugar_share": ("sugars", "carbohydrates", 1), "satfat_share": ("saturated_fat", "fat", 1)}
CLAIMS = ["protein_claim", "fibre_claim", "reduced_sugar", "sugar_free_claim", "reduced_fat_claim",
          "organic_claim", "plant_based_claim", "no_artificial", "gluten_free_claim", "natural_claim",
          "heritage_claim"]
FUNCTIONAL = ["energy_positioning", "hydration_positioning", "electrolyte_positioning"]
AUX = ["claims_matched", "claims_analytical_eligible", "claims_evidence_cohort",
       "claims_nutrition_qa_hold", "claims_population_qa_note", "claims_source_market_limitation",
       "claims_energy_drink_format", "claims_v6_usable","claims_energy_positioning_basis",
       "claims_hydration_front_status","claims_electrolyte_front_status",
       "ingredient_analysis_eligible", "ingredients_lang", "nova_group","claims_basis_protein_claim"]
G = ["region","category","subtype","basis_group"]
COMPLETE = {"core4": CORE, "core4_and_fibre": CORE+["fibre"], "all8": list(RAW),
            "energy_sugars":["energy","sugars"], "protein_density":["protein_density"],
            "fibre_density":["fibre_density"], "density_both":["protein_density","fibre_density"],
            "sugar_share":["sugar_share"], "satfat_share":["satfat_share"]}
TREAT = dict(energy="Compare directly in H2 and H4; keep outside the grouping matrix.",
             protein="Retain for formulation and matched claims; keep density as a separate representation.",
             fat="Retain total fat in core4; use saturated fat to profile a distinct trade-off.",
             saturated_fat="Profile absolute saturated fat; examine its share only for positive total fat.",
             carbohydrates="Profile total carbohydrate or use as a denominator; assess alongside sugars on common rows.",
             sugars="Retain total sugars in core4 and H2; no added-sugar measurement inferred.",
             fibre="Optional paired sensitivity or targeted H3/H5; joint requirement changes the population.",
             salt="Retain for within-format contrasts; examine high tails before interpreting groups.",
             protein_density="Rank within subtype and basis; compare with concentration on identical products.",
             fibre_density="Use only observed fibre; show denominator sensitivity and sparse cells.",
             sugar_share="Optional interpretation; no zero-denominator substitution or clipping above one.",
             satfat_share="Optional interpretation; consider small parent amounts and independent label rounding.")
ING_PATTERN = re.compile(r"\b(?:pea protein|soy(?:a)? protein|proteines? (?:de |du |de la )?(?:pois|soja))\b")


def read_master():
    with MASTER.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != "ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912":
            raise ValueError("Unexpected Wave 2 release.")
    assigned = pd.read_csv(HERE/"subtype_assignments.csv", dtype=str, keep_default_na=False,
                           usecols=KEY+["subtype","basis_group","membership","cereal_bar_review_flag","confidence"])
    cols = [f+s for f in RAW.values() for s in ("","_off_raw","_missing")]
    qcols = ["claims_"+p+c for c in CLAIMS for p in ("claim_","state_")]
    frames = []
    fields = KEY+cols+AUX+qcols+["claims_"+f for f in FUNCTIONAL]+["ingredients_text","product_scope_eligible"]
    for batch in pq.ParquetFile(MASTER).iter_batches(columns=fields,batch_size=4096):
        x = batch.filter(batch["product_scope_eligible"]).to_pandas()
        for m,f in RAW.items():
            valid = x[f].between(0, 900 if m=="energy" else 50 if m=="salt" else 100)
            x[m] = x[f].where(valid & x[f].eq(x[f+"_off_raw"]) & x[f+"_missing"].eq(0))
        # Match only in usable FR/EN text, for feasibility of one scoped H7 ingredient comparison.
        text=x.pop("ingredients_text").fillna("").str.strip()
        lang=x.ingredients_lang.isin(["FR","EN","BOTH"])
        ok=lang & x.ingredient_analysis_eligible.eq(1) & ~text.str.lower().isin(["","unknown","nan","none","null"])
        x["ingredient_ok"]=ok
        def cue(value):
            plain=unicodedata.normalize("NFKD",value.lower()).encode("ascii","ignore").decode()
            return bool(ING_PATTERN.search(re.sub(r"[-’']"," ",plain)))
        x["pea_soy_text_cue"]=text.where(ok,"").map(cue).where(ok)
        frames.append(x.drop(columns=cols))
    df=pd.concat(frames,ignore_index=True).merge(assigned,on=KEY,how="outer",validate="one_to_one",indicator=True)
    if len(df)!=376845 or not df.pop("_merge").eq("both").all():
        raise ValueError("Subtype keys and corrected master differ.")
    baseline=pd.read_csv(HERE/"nutrient_availability.csv").query("subtype == 'ALL'")
    for m in RAW:
        prior=baseline.set_index(["region","category"])[m+"_valid_n"].sort_index()
        if not df.groupby(["region","category"])[m].count().sort_index().equals(prior):
            raise ValueError("Validity differs from the completed baseline: "+m)
    for target,(num,den,k) in RATIOS.items():
        df[target]=k*df[num]/df[den].where(df[den].gt(0))
    df["peer"]=(df.membership.eq("YES") & ~df.subtype.isin(["OTHER","UNRESOLVED"]) &
                df.basis_group.isin(["per_100g_food","per_100ml_liquid"]) & df.cereal_bar_review_flag.ne("True"))
    df["assessed_layer"]=df.claims_matched.eq(True)&df.claims_analytical_eligible.eq(True)
    return df,baseline


def record(rows,kind,item,scope,base_n,n,**kwargs):
    rows.append(dict(record_kind=kind,feature_or_set=item,scope=scope,base_n=base_n,retained_n=n,
                     retained_pct=100*n/base_n if base_n else None,**kwargs))


def completeness(frame, features):
    return frame[features].notna().all(axis=1)


def diagnostics(df,baseline):
    out=[]; matrices=[]
    peers=df[df.peer]
    foods=peers[peers.basis_group.eq("per_100g_food")]
    primary=foods[foods.region.isin(["FR","UK-IE"])]
    # The control is product-level. A shared barcode contributes once, with FR as reference assignment.
    unique=primary.sort_values(KEY).drop_duplicates("barcode")
    # No row is projected between units. Preparations receive retention diagnostics only.
    pending=df[~df.basis_group.isin(["per_100g_food","per_100ml_liquid"])]
    sets=[("governed assignments",df),("named comparable peers",peers),("FR+UK food control unique GTIN",unique),
          ("US-CA projection food peers",foods[foods.region.eq("US-CA")]),("preparation or unverified basis",pending)]
    sets.extend(("peer "+"/".join(k),v) for k,v in peers.groupby(["region","category"]))
    for scope,frame in sets:
        for key,features in COMPLETE.items():
            n=int(completeness(frame,features).sum())
            record(out,"joint",key,scope,len(frame),n,inputs="+".join(features))
    for key,frame in peers.groupby(G):
        for name in ["core4","energy_sugars","protein_density","fibre_density"]:
            record(out,"peer_retention",name,"/".join(key),len(frame),int(completeness(frame,COMPLETE[name]).sum()),
                   inputs="+".join(COMPLETE[name]))
    us=foods[foods.region.eq("US-CA") & completeness(foods,CORE)]
    novel=us[~us.barcode.isin(unique.loc[completeness(unique,CORE),"barcode"])]
    record(out,"control_projection","distinct unseen US-CA GTIN","US-CA projection food peers",
           us.barcode.nunique(),novel.barcode.nunique(),inputs="core4; exclude GTIN in complete reference")
    for fields in ["core4","energy_sugars","protein_density","fibre_density"]:
        ok=completeness(peers,COMPLETE[fields])
        if fields.endswith("_density"): ok &= peers.energy.ge(10)
        group=["category","subtype","basis_group","region"]
        counts=peers.assign(ok=ok).groupby(group).ok.sum().unstack(fill_value=0)
        for minimum in [30,100]:
            for regions in [["FR","UK-IE"],["FR","UK-IE","US-CA"]]:
                common=counts[regions].ge(minimum).all(axis=1)
                record(out,"H12_common_support",fields,"+".join(regions),len(counts),int(common.sum()),
                       inputs=f"peer cells with >= {minimum} valid in each region; density requires E >= 10")
    # Reuse prior marginal counts and quantiles. No new raw univariate audit.
    previous=pd.read_csv(HERE/"nutrient_distributions.csv")
    if set(previous.metric)!=set(RAW) or previous.empty: raise ValueError("Invalid distribution input")
    for m,f in RAW.items():
        record(out,"raw",m,"governed assignments",len(df),int(df[m].count()),inputs=f,
               source_available_n=int(baseline[m+"_source_available_n"].sum()),
               stored_in_master="yes",recommendation=TREAT[m])
    for name,fields,available,treatment in [
        ("governed assignment","barcode + region + category + product_scope_eligible","yes",
         "Text composite key for assignment comparisons. Deduplicate GTIN only in the specified control."),
        ("approved peer classification","membership + subtype + basis_group + confidence + cereal_bar_review_flag","baseline CSV",
         "Use existing labels and confidence; preserve unresolved cases in the coverage denominator."),
        ("H1/H4/H9/H10 peer quantiles","peer cell + valid nutrient(s)","no; proposed",
         "Derive quartile boundaries on the stated reference population; report ties and zero IQR."),
        ("H2 matched sugar gap","abs(sugars_a - sugars_b) within energy tolerance","no; proposed",
         "Pair without reuse, within subtype and region. Inspect coverage before evaluating outcomes."),
        ("H3 rank movement","density percentile - concentration percentile on identical rows","no; proposed",
         "Use mean ranks for ties; repeat at the stated energy floors."),
        ("H6 caliper distance","core4 differences / peer IQR","no; proposed",
         "Use an absolute 0.25 IQR per-coordinate caliper; require equality on constant dimensions."),
        ("H10 exclusive territories","two assessable propositions + separate both-positive state","no; diagnostic",
         "Compare exclusive arms only on common support; keep overlapping positives visible."),
        ("H11 high density","nutrient density > Q3 of named nutrition peers with E >= 10","no; diagnostic",
         "Require >=30 in the nutritional reference before testing the same-proposition evidence."),
        ("control percentile inputs","midrank empirical CDF of each core4 feature in reference solids","no; proposed",
         "Fit scaling once in the reference; apply the same mapping to exploratory projections.")]:
        out.append(dict(record_kind="design_feature",feature_or_set=name,scope="see question-specific retention rows",
                        inputs=fields,stored_in_master=available,recommendation=treatment))
    for scope,frame in [("all comparable peers",peers),("food peers",foods),
                        ("liquid peers",peers[peers.basis_group.eq("per_100ml_liquid")]),
                        ("preparation or unverified basis",pending)]:
        for name,(num,den,k) in RATIOS.items():
            parent=frame[den]; values=frame[name].dropna()
            record(out,"engineered",name,scope,len(frame),len(values),inputs=f"{k} * {num} / {den}; {den} > 0",
                   stored_in_master="no",recommendation=TREAT[name],zero_n=int(values.eq(0).sum()),
                   denominator_zero_with_numerator_n=int((parent.eq(0)&frame[num].notna()).sum()),
                   small_denominator_n=int(((parent.gt(0)&parent.lt(10 if den=="energy" else 1))&frame[num].notna()).sum()),
                   above_one_n=int(values.gt(1).sum()) if k==1 else None,
                   p50=values.median(),p95=values.quantile(.95),p99=values.quantile(.99),maximum=values.max())
            if den=="energy":
                for low,high in [(0,5),(5,10),(10,20),(20,np.inf)]:
                    mask=(parent.gt(0)&parent.ge(low)&parent.lt(high))
                    z=frame.loc[mask,name].dropna()
                    record(out,"energy_sensitivity",name,scope+f"; E>0 and [{low},{high}) kcal",len(frame),len(z),
                           zero_n=int(z.eq(0).sum()),p50=z.median(),p95=z.quantile(.95),p99=z.quantile(.99),maximum=z.max())
    for key,frame in peers[(peers.category=="cereal")&peers.subtype.isin(["GRANOLA","FLAKES"])].groupby(G):
        vals=np.sort(frame.loc[completeness(frame,["energy","sugars"]),"energy"].to_numpy())
        for tol in [5,10,20]:
            neighbours=np.searchsorted(vals,vals+tol,side="right")-np.searchsorted(vals,vals-tol)-1
            record(out,"H2_energy_only","peers_with_at_least_5_neighbours","/".join(key),len(vals),
                   int((neighbours>=5).sum()),inputs=f"absolute energy difference <= {tol} kcal/100 g")
    features=list(RAW)+list(RATIOS)
    scopes=[("FR+UK food control unique GTIN",unique)]
    scopes.extend(("/".join(k),v) for k,v in peers.groupby(["category","basis_group"]))
    for scope,frame in scopes:
        x=frame[features]
        mask=x.notna().astype("int64")
        counts=mask.T@mask
        prs=x.corr("pearson",min_periods=3); spr=x.corr("spearman",min_periods=3)
        for i,j in itertools.combinations_with_replacement(features,2):
            matrices.append(dict(scope=scope,feature_a=i,feature_b=j,paired_n=int(counts.loc[i,j]),
                                 pearson=prs.loc[i,j],spearman=spr.loc[i,j]))
        for name,fs in [("core4",CORE),("all8",list(RAW))]:
            complete=x[fs].dropna()
            r=complete.corr().to_numpy()
            if np.isfinite(r).all() and np.linalg.matrix_rank(r)==len(fs):
                vif=np.diag(np.linalg.inv(r))
                for feature,value in zip(fs,vif):
                    record(out,"VIF",feature,scope,len(frame),len(complete),inputs=name,vif=value)
    # Exact associations alongside inventory recommendations for each candidate.
    matrix=pd.DataFrame(matrices)
    ref=matrix[(matrix.scope=="FR+UK food control unique GTIN")&(matrix.feature_a!=matrix.feature_b)]
    for row in out:
        if row["record_kind"] in {"raw","engineered"}:
            name=row["feature_or_set"]
            pairs=ref[(ref.feature_a==name)|(ref.feature_b==name)].dropna(subset=["spearman"])
            if len(pairs):
                best=pairs.loc[pairs.spearman.abs().idxmax()]
                row.update(reference_correlate=best.feature_b if best.feature_a==name else best.feature_a,
                           reference_pearson=best.pearson,reference_spearman=best.spearman,reference_pair_n=best.paired_n)
    return out,matrix


def claim_counts(out,frame,name,state,mask,scope,inputs):
    g=frame.loc[mask]
    s=state.loc[g.index]
    pos=s.eq("positive"); neg=s.eq("documented_negative")
    sizes=g.assign(p=pos,n=neg).groupby(G)[["p","n"]].sum()
    ok=sizes[(sizes.p>=20)&(sizes.n>=20)]
    record(out,"claim_comparison",name,scope,len(frame),len(g),inputs=inputs,
           positive_n=int(pos.sum()),documented_negative_n=int(neg.sum()),
           adjudicated_negative_n=int(s.eq("adjudicated_negative").sum()),unknown_n=int(s.eq("unknown").sum()),
           cells_20_each=len(ok),supported_cells=" | ".join("/".join(k) for k in ok.index))


def claim_diagnostics(df,out):
    layer=df[df.assessed_layer].copy()
    if len(layer)!=12159: raise ValueError("Claim layer denominator changed")
    for name in CLAIMS+FUNCTIONAL:
        field=("claims_claim_" if name in CLAIMS else "claims_")+name
        flag=layer[field]
        state=pd.Series("unknown",index=layer.index)
        state.loc[flag.eq(True)]="positive"
        if name in CLAIMS:
            locked=layer["claims_state_"+name]
            state.loc[flag.eq(False)&locked.eq("DOCUMENTED_NOT_DETECTED")]="documented_negative"
            state.loc[flag.eq(False)&locked.eq("HUMAN_CONFIRMED_NEGATIVE")]="adjudicated_negative"
        else:
            state.loc[flag.eq(False)]="documented_negative"
            if name in ["hydration_positioning","electrolyte_positioning"]:
                if ((flag.notna())&~layer.claims_v6_usable.eq(True)).any(): raise ValueError(name)
        layer[name]=state
        applies=layer.category.eq("beverages") if name in FUNCTIONAL else pd.Series(True,index=layer.index)
        states=state[applies]
        detail={}
        if name in CLAIMS:
            for original_label,count in locked[applies].fillna("UNASSESSED").value_counts().items():
                detail["locked_"+original_label.lower()+"_n"]=int(count)
        record(out,"claim_feature",name,"eligible locked evidence"+(" / beverages" if name in FUNCTIONAL else ""),
               int(applies.sum()),int(states.ne("unknown").sum()),stored_in_master="yes",inputs=field,
               positive_n=int(states.eq("positive").sum()),documented_negative_n=int(states.eq("documented_negative").sum()),
               adjudicated_negative_n=int(states.eq("adjudicated_negative").sum()),unknown_n=int(states.eq("unknown").sum()),
               recommendation="Use proposition-specific assessment and provenance. Keep unmatched and ambiguous unknown.",**detail)
    eligible=layer.peer & layer.claims_source_market_limitation.fillna("").eq("")
    tests={"H5 protein":("protein_claim",["protein"]), "H5 fibre":("fibre_claim",["fibre"]),
           "H5 reduced sugar":("reduced_sugar",["sugars"]), "H5 sugar free":("sugar_free_claim",["sugars"]),
           "H5 reduced fat":("reduced_fat_claim",["fat"]), "H9 protein and salt":("protein_claim",["salt"]),
           "H9 fibre and sugars":("fibre_claim",["sugars"]), "H9 reduced fat and sugars":("reduced_fat_claim",["sugars"]),
           "H10 organic and sugars":("organic_claim",["sugars"]), "H10 plant-based and sugars":("plant_based_claim",["sugars"]),
           "H10 protein and sugars":("protein_claim",["sugars"]), "H11 protein":("protein_claim",["protein_density"]),
           "H11 fibre":("fibre_claim",["fibre_density"])}
    for name in ["organic_claim","plant_based_claim","gluten_free_claim","natural_claim","heritage_claim","protein_claim"]:
        tests["H6 "+name]=(name,CORE)
    for prop in FUNCTIONAL: tests["H8 "+prop]=(prop,["energy","sugars"])
    for label,(claim,fields) in tests.items():
        mask=eligible & completeness(layer,fields)
        if "salt" in fields: mask &= layer.claims_nutrition_qa_hold.fillna("").eq("")
        if label.startswith("H8"): mask &= layer.category.eq("beverages") & layer.basis_group.eq("per_100ml_liquid")
        if label.startswith("H11"): mask &= layer.energy.ge(10)
        claim_counts(out,layer,claim,layer[claim],mask,label,"+".join(fields))
        if label=="H5 protein":
            positives=layer[mask & layer[claim].eq("positive")]
            for provenance,count in positives.claims_basis_protein_claim.fillna("UNAVAILABLE").value_counts().items():
                record(out,"protein_claim_provenance",str(provenance),label,len(positives),int(count),
                       inputs="claims_basis_protein_claim",stored_in_master="yes",
                       recommendation="Repeat with rule-supported positives separated from explicit pack evidence.")
    for claim in ["plant_based_claim","no_artificial","protein_claim"]:
        ok=eligible & layer.ingredient_ok
        claim_counts(out,layer,claim,layer[claim],ok,"H7 ingredients","FR/EN/BOTH usable nonempty list")
        for decision in ["positive","documented_negative"]:
            arm=layer[ok & layer[claim].eq(decision)]
            record(out,"H7_text_support",claim,decision,len(arm),int(arm.pea_soy_text_cue.eq(True).sum()),
                   inputs="explicit pea/soy protein phrase in eligible ingredient text")
    for nutrient,claim in [("protein_density","protein_claim"),("fibre_density","fibre_claim")]:
        peer=df[df.peer & df.energy.ge(10) & df[nutrient].notna()].copy()
        cell=peer.groupby(G)[nutrient]
        high=peer[cell.transform("size").ge(30) & peer[nutrient].gt(cell.transform("quantile",q=.75))]
        assessed=layer[eligible & layer.index.isin(high.index)]
        claim_counts(out,assessed,claim,assessed[claim],pd.Series(True,index=assessed.index),
                     "H11 above peer Q3",nutrient+"; above peer Q3; reference n>=30; E>=10")
        known=assessed[assessed[claim].isin(["positive","documented_negative"])]
        cell_n=known.groupby(G).size()
        record(out,"H11_support",claim,"known high-density assessments",len(cell_n),int(cell_n.ge(30).sum()),
               inputs="distinct peer cells with >=30 positives plus documented non-detections")
    for a,b in itertools.combinations(["organic_claim","protein_claim","plant_based_claim"],2):
        valid=["positive","documented_negative"]
        g=layer[eligible & layer.sugars.notna() & layer[a].isin(valid) & layer[b].isin(valid)]
        pa=g[a].eq("positive"); pb=g[b].eq("positive")
        counts=g.assign(only_a=pa & ~pb,only_b=~pa & pb).groupby(G)[["only_a","only_b"]].sum()
        support=counts[(counts.only_a>=20)&(counts.only_b>=20)]
        record(out,"H10_exclusive_support",a+" vs "+b,"jointly assessed named peers with sugars",
               int((eligible & layer.sugars.notna()).sum()),len(g),
               only_first_positive_n=int((pa & ~pb).sum()),only_second_positive_n=int((~pa & pb).sum()),
               both_positive_n=int((pa & pb).sum()),cells_20_each=len(support),
               supported_cells=" | ".join("/".join(k) for k in support.index))
    ok=eligible&layer.ingredient_ok
    record(out,"engineered_text","pea_soy_text_cue","H7 eligible named peers with any locked evidence",int(ok.sum()),
           int(layer.loc[ok,"pea_soy_text_cue"].eq(True).sum()),inputs="EN/FR explicit pea/soy protein phrase",
           stored_in_master="no",recommendation="Count is detected text; validate positive/negative wording by language before using.")
    for region,group in layer.groupby("region"):
        record(out,"claim_selection","assessed layer",region,int(df.region.eq(region).sum()),len(group),
               historical_n=int(group.claims_evidence_cohort.eq("historical_dairy_reuse").sum()),
               population_qa_n=int(group.claims_population_qa_note.fillna("").ne("").sum()),
               market_limited_n=int(group.claims_source_market_limitation.fillna("").ne("").sum()))
    # H8 intersection: do not equate a missing v6 front state with a negative.
    for (reg,basis),g in layer[eligible & layer.category.eq("beverages")].groupby(["region","basis_group"]):
        for other in FUNCTIONAL[1:]:
            mask=(g[other].ne("unknown")&g.energy_positioning.ne("unknown")&completeness(g,["energy","sugars"]))
            record(out,"H8_joint",other,reg+"/"+basis,len(g),int(mask.sum()),
                   positive_n=int((mask & g[other].eq("positive")).sum()),
                   energy_positive_n=int((mask & g.energy_positioning.eq("positive")).sum()),
                   both_positive_n=int((mask & g.energy_positioning.eq("positive") & g[other].eq("positive")).sum()))
    known=layer.claims_energy_drink_format.fillna("").ne("")
    for fmt,g in layer[known&layer.energy_positioning.eq("positive")&layer.category.eq("beverages")].groupby("claims_energy_drink_format"):
        record(out,"H8_locked_format","energy_positioning",str(fmt),len(g),int(completeness(g,["energy","sugars"]).sum()))
    for region,g in df.groupby("region"):
        record(out,"metadata","ingredient_text_usable",region,len(g),int(g.ingredient_ok.sum()),
               inputs="ingredients_text + ingredients_lang + ingredient_analysis_eligible",stored_in_master="yes")
        record(out,"metadata","NOVA",region,len(g),int(g.nova_group.isin([1,2,3,4]).sum()),
               inputs="nova_group",stored_in_master="yes",recommendation="Optional H9 processing context; separate from nutrient observations.")
    return layer


def main():
    df,baseline=read_master()
    out,matrix=diagnostics(df,baseline)
    claim_diagnostics(df,out)
    with TemporaryDirectory(dir=HERE) as temp:
        frames={"FEATURE_DECISIONS.csv":pd.DataFrame(out),"FEATURE_CORRELATIONS.csv":matrix}
        for name,frame in frames.items():
            frame.to_csv(Path(temp)/name,index=False,encoding="utf-8-sig",float_format="%.8g")
        for name in frames: os.replace(Path(temp)/name,HERE/name)
    print("diagnostics:",len(df),len(out),len(matrix))


if __name__=="__main__":
    main()
