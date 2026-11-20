"""Reconcile approved formulation rules and write the chapter decision register."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import re
import sys

import pandas as pd

HERE=Path(__file__).resolve().parent.parent
MANIFEST=Path(__file__).resolve().parent/"run_manifest_v1.json"
EDA=HERE.parent/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path.insert(0,str(EDA))
from shared_feature_diagnostics_v1 import KEY,read_master
L1=HERE/"01_nutritional_composition"
L2=HERE/"02_nutrient_density"
def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def module(path):
    spec=importlib.util.spec_from_file_location(path.stem,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
def main():
    df,_=read_master()
    records=[]
    def profile(branch,population,fields,predicate,rule,basis,source,expected):
        for region,g in population.groupby("region"):
            valid=g[fields].notna().all(axis=1)
            if branch=="Cream/pudding":valid &= g.energy.ge(10)
            n=int((valid & predicate(g)).sum())
            assert n==expected[region],(branch,region,n)
            records.append(dict(branch=branch,decision="approved descriptive profile",region=region,
                 rule=rule,basis=basis,required_fields="+".join(fields),starting_n=len(g),eligible_n=int(valid.sum()),
                 retained_n=n,unknown_required_n=int((~valid).sum()),coverage_pct=100*n/valid.sum(),
                 evidence=source,source_sha256=digest(HERE/source),scope_note="US-CA selected exploratory population" if region=="US-CA" else "observed products; no market prevalence inference"))
    cereal=pd.read_parquet(EDA.parent/"01_nutritional_composition/lens1_cereal_master_v1.parquet")
    granola=cereal[cereal.h2_format_candidate.eq(True)&cereal.effective_type_code.eq("GRANOLA")]
    granola=df.merge(granola[KEY],on=KEY,validate="one_to_one")
    profile("Granola",granola,["sugars","protein"],lambda g:g.sugars.le(14)&g.protein.ge(11),
            "sugars <=14 g and protein >=11 g","per 100 g","01_nutritional_composition/cereal_formulations_v1.md",{"FR":251,"UK-IE":94,"US-CA":121})
    dairy=df[df.peer&df.subtype.eq("DAIRY_DESSERT")]
    meta=pd.read_csv(EDA/"subtype_assignments.csv",dtype=str,usecols=KEY+["product_name","off_categories"])
    dairy=dairy.merge(meta,on=KEY,validate="one_to_one")
    classifier=module(L2/"dairy_dessert_formulations_v1.py")
    pudding=dairy[dairy.apply(classifier.classify,axis=1).eq("dessert cream / pudding")]
    profile("Cream/pudding",pudding,["protein","energy"],lambda g:g.protein.ge(8)&g.energy.le(110),
            "protein >=8 g and 10<=energy<=110 kcal","per 100 g","02_nutrient_density/dairy_dessert_formulations_v1.md",{"FR":27,"UK-IE":15,"US-CA":1})
    juice_n=int(pd.read_parquet(L1/"beverage_assignments_v1.parquet",columns=["analytical_format"]).analytical_format.eq("juice").sum())
    for filename,total in [("savoury_snack_assignments_v1.parquet",151461),("beverage_assignments_v1.parquet",117596),("juice_assignments_v1.parquet",juice_n)]:
        a=pd.read_parquet(L1/filename)
        assert len(a)==total and not a.duplicated(KEY).any()
        assert a.barcode.map(lambda s:isinstance(s,str)).all() and a.barcode.str.startswith("0").any()
        if filename.startswith("savoury"):
            labels=a[a.savoury_format.eq("potato crisps")&a.basis_group.eq("per_100g_food")]
            g=df.merge(labels[KEY+["formulation_profile"]],on=KEY,validate="one_to_one")
            profile("Potato crisps",g,["fat"],lambda x:x.fat.le(20),"fat <=20 g","per 100 g",
                    "01_nutritional_composition/savoury_snacks_CHECK_v1.md",{"FR":100,"UK-IE":90,"US-CA":53})
            assert g.formulation_profile.eq("lower-fat potato crisps").sum()==g.fat.le(20).sum()
        if filename.startswith("beverage"):
            for branch,expected in [("soda",{"FR":713,"UK-IE":255,"US-CA":96}),("energy drink",{"FR":153,"UK-IE":88,"US-CA":97})]:
                labels=a[a.comparable_liquid & a.analytical_format.eq(branch)]
                g=df.merge(labels[KEY+["retained_profile"]],on=KEY,validate="one_to_one")
                profile(branch,g,["sugars"],lambda x:x.sugars.le(.5),"sugars <=0.5 g","per 100 ml convention",
                        "01_nutritional_composition/beverages_CHECK_v1.md",expected)
                assert g.retained_profile.eq("very-low-sugars formulation").sum()==g.sugars.le(.5).sum()
        if filename.startswith("juice"):assert a.candidate_profile.isna().all()
    decisions=[
        ("Flakes","commercial distinction and nutritional variation","01_nutritional_composition/cereal_formulations_v1.md","Finer cereal wording may explain sugar contrasts; no retained nutritional split."),
        ("Mousse; flan","nutritional variation and density view","02_nutrient_density/dairy_dessert_formulations_v1.md","Retain per-weight and per-calorie views within form."),
        ("Other identified dairy desserts","insufficient evidence for further profile","02_nutrient_density/dairy_dessert_formulations_v1.md","Small comparable regional populations; keep forms."),
        ("Unresolved dairy desserts","unresolved commercial identity","02_nutrient_density/dairy_dessert_formulations_v1.md","1536 unspecified, conflicting or comparability-concern assignments retained broadly."),
        ("Biscuits","nutritional variation","01_nutritional_composition/biscuits_and_wafers_CHECK_v1.md","Control contrast partly persists; independent three-nutrient co-occurrence too weak for segment."),
        ("Wafers","insufficient evidence for further profile","01_nutritional_composition/biscuits_and_wafers_CHECK_v1.md","Weak UK/IE cross-group support."),
        ("Tortilla/corn chips","nutritional variation","01_nutritional_composition/savoury_snacks_CHECK_v1.md","Threshold divides the middle; French saturated-fat tail exploratory."),
        ("Puffed/extruded snacks","commercial base and construction distinction","01_nutritional_composition/savoury_snacks_CHECK_v1.md","Pulse and potato wording contextualize protein; no universal formulation split."),
        ("Other savoury formats","classified; formulation follow-up uninvestigated","01_nutritional_composition/savoury_snacks_CHECK_v1.md","Popcorn, pretzels, crackers, nuts/seeds and other forms have not received this within-format follow-up."),
        ("Plant drinks","commercial base distinction","01_nutritional_composition/beverages_CHECK_v1.md","Soy versus almond useful; captured oat and other bases sparse/incomplete."),
        ("Iced tea; iced coffee; sports/electrolyte liquids","insufficient regional replication","01_nutritional_composition/beverages_CHECK_v1.md","Retain format and descriptive evidence."),
        ("Smoothies; nectars; fruit drinks; fermented soft drinks","commercial distinction and nutritional variation","01_nutritional_composition/beverages_CHECK_v1.md","No further accepted profile."),
        ("Water; flavoured water; coconut water","commercial distinction and unresolved descriptors","01_nutritional_composition/beverages_CHECK_v1.md","Unspecified flavour is not verified plain water."),
        ("Juice","composition-based commercial distinction","01_nutritional_composition/juice_formulations_v1.md","Fruit/vegetable, named types and blends; concentration descriptor independent; no nutritional profile."),
        ("Preparations","deferred measurement basis","01_nutritional_composition/beverages_CHECK_v1.md","Syrups, concentrates, chocolate, coffee, tea, sports powders/tablets kept separate."),
        ("Alcohol","excluded nutritional segmentation scope","01_nutritional_composition/beverages_CHECK_v1.md","Underlying reporting and source population preserved."),
        ("Other cereal and dairy branches","uninvestigated within-format follow-up","CHECK.md","Baseline H1-H12 results do not establish final profiles for every subtype."),
        ("Pooled k=5 control","completed exploratory reference","CHECK.md","No further optimization; format influence and mixed populations limit commercial interpretation.")]
    for branch,status,source,note in decisions:
        records.append(dict(branch=branch,decision=status,region="see source",evidence=source,
                            source_sha256=digest(HERE/source),scope_note=note))
    pd.DataFrame(records).to_csv(HERE/"FORMULATION_DECISIONS_v1.csv",index=False,encoding="utf-8-sig")
    # Check executable input dependencies and evidence referenced by the register.
    assert (EDA/"shared_feature_diagnostics_v1.py").is_file()
    for name in ["subtype_assignments.csv","nutrient_availability.csv","nutrient_distributions.csv"]:assert (EDA/name).is_file()
    for name in ["lens1_cereal_classification.csv","lens1_cereal_master_v1.py","lens1_cereal_master_v1.parquet"]:
        assert (EDA.parent/"01_nutritional_composition"/name).is_file()
    for p in list(HERE.rglob("*.py"))+list(EDA.glob("*.py")):
        ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
    manifest=__import__("json").loads(MANIFEST.read_text(encoding="utf-8"))
    for relative,expected in manifest["sha256"].items():
        p=HERE.parent/relative
        assert p.is_file(),relative
        assert digest(p)==expected,("original run manifest mismatch",relative)
    print("PASS approved counts, eligibility, saved keys/labels, source and original run hashes, shared inputs and all analytical script syntax.")
if __name__=="__main__":main()
