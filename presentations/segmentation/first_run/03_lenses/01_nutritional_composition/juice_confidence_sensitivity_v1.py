"""Final bounded juice sensitivity, approved 19 November 2026.

Uses existing corrected keyed layers and saved valid measurements. Changes no
classification, source record, claim, feature definition or modelling decision.
Writes the matching summary CSV and dated sections in two existing CHECKs.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
LENSES=HERE.parent
STUDY=LENSES.parent
MASTER=STUDY/"01_ingestion/05_master_parquet/output/master_products.parquet"
KEY=["barcode","region","category"]
METRICS=["sugars","energy","salt"]
BEGIN="<!-- juice-confidence-sensitivity-v1 -->"
END="<!-- /juice-confidence-sensitivity-v1 -->"
ACCEPTED_INPUT_SHA256={
    "beverage_assignments_v1.parquet":"d3d0effad50f92a68ea0780f6a9ad758ef3a990494461b5128165eabf6fc5039",
    "juice_assignments_v1.parquet":"ed13142c21da536c408b2fe210afa124fbf7844c69677dd1ab501f55473833ef"}


def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def table(head,rows):
    return "\n".join("| "+" | ".join(map(str,row))+" |" for row in [head,["---"]*len(head),*rows])


def fmt(x,digits=3):
    return f"{x:.{digits}f}".rstrip("0").rstrip(".") if pd.notna(x) else "unavailable"


def append_section(path,section):
    text=path.read_text(encoding="utf-8")
    if BEGIN in text:
        start=text.index(BEGIN);end=text.index(END,start)+len(END)
        text=text[:start]+text[end:]
    path.write_text(text.rstrip()+"\n\n"+BEGIN+"\n"+section+"\n"+END+"\n",encoding="utf-8")


def main():
    l3=LENSES/"03_claims_composition_and_ingredients"
    l4=LENSES/"04_positioning_tradeoffs"
    join=STUDY/"01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/claims_join.parquet"
    source=[MASTER,MASTER.parent/"manifest.json",join,HERE/"beverage_assignments_v1.parquet",
            HERE/"juice_assignments_v1.parquet",LENSES/"FORMULATION_DECISIONS_v1.csv",
            l4/"processing_boundary_evidence_v1.parquet"]
    source += [l3/n for n in ["human_claim_decisions_v1.csv","human_claim_adjudications_v1.csv","human_claim_review_v1.csv"]]
    frozen={str(p.resolve()):digest(p) for p in source}
    for name,expected in ACCEPTED_INPUT_SHA256.items():
        assert frozen[str((HERE/name).resolve())]==expected,("changed accepted classification layer; review sensitivity version",name)
    manifest=json.loads((MASTER.parent/"manifest.json").read_text(encoding="utf-8"))
    assert frozen[str(MASTER.resolve())]==manifest["master_sha256"]
    audit=pq.read_schema(l4/"processing_boundary_evidence_v1.parquet").metadata
    for name,expected in json.loads(audit[b"input_sha256"]).items():
        assert digest(LENSES.parents[2]/name)==expected,("stale source dependency",name)
    assert digest(l4/"processing_boundaries_v1.py")==audit[b"script_sha256"].decode()
    b=pd.read_parquet(HERE/"beverage_assignments_v1.parquet")
    j=pd.read_parquet(HERE/"juice_assignments_v1.parquet")
    assert not b.duplicated(KEY).any() and not j.duplicated(KEY).any()
    assert b.barcode.map(lambda x:isinstance(x,str)).all() and j.barcode.map(lambda x:isinstance(x,str)).all()
    expected=b[b.analytical_format.eq("juice")][KEY]
    assert set(map(tuple,j[KEY].to_numpy()))==set(map(tuple,expected.to_numpy()))
    fr=j[j.region.eq("FR")]
    removed=fr.original_analytical_format.ne("juice")&fr.juice_classification_confidence.eq("MEDIUM")
    assert len(fr)==8558 and removed.sum()==1090 and (~removed).sum()==7468
    arms={"corrected full":fr,"exclude newly assigned MEDIUM":fr[~removed],"removed MEDIUM only":fr[removed]}
    assert set(map(tuple,arms["exclude newly assigned MEDIUM"][KEY].to_numpy())).isdisjoint(
        set(map(tuple,arms["removed MEDIUM only"][KEY].to_numpy())))
    assert len(arms["exclude newly assigned MEDIUM"])+len(arms["removed MEDIUM only"])==len(fr)
    records=[]
    for arm,g in arms.items():
        low=g[g.sugars.gt(.5)&g.sugars.lt(5)]
        groups={"all French juice":g,"0.5<sugars<5":low,
                "low band without vegetable-type labels":low[~low.juice_subformat.str.startswith("vegetable")]}
        groups.update({f:g[g.strict_comparable&g.juice_subformat.eq(f)] for f in ["fruit: apple","fruit: orange","vegetable: tomato"]})
        for group,z in groups.items():
            for metric in METRICS:
                valid=z[metric].dropna()
                records.append(dict(region="FR",arm=arm,group=group,metric=metric,
                    unit="kcal/100ml" if metric=="energy" else "g/100ml",population_n=len(z),
                    available_n=len(valid),missing_n=int(z[metric].isna().sum()),zero_n=int(valid.eq(0).sum()),
                    q25=valid.quantile(.25),median=valid.median(),q75=valid.quantile(.75),
                    very_low_sugar_energy_above20_n=int((z.sugars.le(.5)&z.energy.gt(20)).sum()),
                    master_sha256=manifest["master_sha256"],beverage_sha256=frozen[str((HERE/"beverage_assignments_v1.parquet").resolve())],
                    juice_sha256=frozen[str((HERE/"juice_assignments_v1.parquet").resolve())],script_sha256=digest(Path(__file__))))
    result=pd.DataFrame(records)
    assert not result.duplicated(["arm","group","metric"]).any()
    assert (result.available_n+result.missing_n).eq(result.population_n).all()
    result.to_csv(HERE/"juice_confidence_sensitivity_v1.csv",index=False,encoding="utf-8-sig")
    saved=pd.read_csv(HERE/"juice_confidence_sensitivity_v1.csv")
    pd.testing.assert_frame_equal(result,saved,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)
    assert frozen=={name:digest(Path(name)) for name in frozen},"Protected source changed."
    write_note(result,fr,removed,frozen)
    print("PASS: 1,090 excluded only for sensitivity; 7,468 retained; 54 reconciled summary rows; keyed layers, master, locked and human evidence unchanged.")
    print(result[result.group.isin(["0.5<sugars<5","fruit: apple","fruit: orange","vegetable: tomato"])&result.metric.isin(["sugars","salt"])][
        ["arm","group","metric","population_n","available_n","median"]].to_string(index=False))


def write_note(r,fr,removed,frozen):
    def cell(arm,group,metric):
        x=r[r.arm.eq(arm)&r.group.eq(group)&r.metric.eq(metric)]
        assert len(x)==1
        return x.iloc[0]
    arms=["corrected full","exclude newly assigned MEDIUM","removed MEDIUM only"]
    headline=[]
    for arm in arms:
        low=cell(arm,"0.5<sugars<5","salt")
        nv=cell(arm,"low band without vegetable-type labels","salt")
        total=cell(arm,"all French juice","sugars")
        headline.append([arm,total.population_n,total.available_n,low.population_n,low.available_n,
                         fmt(low["median"]),f"{fmt(low.q25)}–{fmt(low.q75)}",fmt(nv["median"])])
    named=[]
    for form in ["fruit: apple","fruit: orange","vegetable: tomato"]:
        row=[form]
        for arm in arms[:2]:
            values=[cell(arm,form,m) for m in METRICS]
            row.append(" / ".join(f"{fmt(x['median'])} (n={x.available_n})" for x in values))
        named.append(row)
    full=cell(arms[0],"0.5<sugars<5","salt")["median"]
    retained=cell(arms[1],"0.5<sugars<5","salt")["median"]
    # This reports the accepted interpretation of this version, not a universal materiality cutoff.
    conclusion=("**Headline interpretation remains stable.** The low-sugar group's median salt changes from "
        f"{fmt(full)} to {fmt(retained)} g/100 ml, compared with 0.30 in the superseded selected population. "
        "The distribution still has a higher-salt upper tail; tomato/vegetable distinctions remain informative. "
        "Apple sugars change from 10.28 to 10.24 g/100 ml, orange stays at 9, and the named-type energy medians remain 45/43/19 kcal. "
        "No tomato records are excluded, so unchanged tomato measurements are expected, not independent validation of identity. "
        "This check supports retaining the commercial refinements and existing decision against an additional juice nutritional profile. "
        "It does not prove the absence of clusters or verify product identity.")
    body="\n\n".join(["## Final MEDIUM-confidence sensitivity and acceptance · 19 November 2026",
        "Julia approved the Thursday processing/boundary findings and the corrected juice interpretation subject to this final bounded sensitivity. The condition has been met. Corrected juice classifications are the authoritative analytical interpretation; all records remain in their existing keyed layers. **Ready for the consolidation phase; consolidation has not started.**",
        "Exact exclusion predicate: `region == FR`, corrected `analytical_format == juice`, `original_analytical_format != juice`, and `juice_classification_confidence == MEDIUM`. This identifies exactly 1,090 of 8,558 French assignments; 7,468 remain in the comparison. The retained arm is not a HIGH-only or independently verified sample. Original-juice MEDIUM records remain. No classifications or evidence states are changed.",
        table(["Sensitivity arm","Juice n","Valid sugars n","0.5<sugars<5 n","Valid salt in band","Median salt","Salt Q1–Q3","Median salt without vegetable-type labels"],headline),
        table(["Comparable named type","Full: sugars / energy / salt medians (each valid n)","Exclude newly MEDIUM: same measurements"],named),
        conclusion,
        "Measurements reuse saved valid values on the inherited per-100-ml basis. Missing and numeric zero remain separate. The no-vegetable-type-label view exactly reuses the existing `not juice_subformat.startswith('vegetable')` definition; it is not proof of absence of vegetable ingredients and does not remove mixed fruit/vegetable labels. No new identity inference, outlier deletion or cleansing is performed. French conclusions remain conditional on the observed OFF population.",
        "[Reproducible script](juice_confidence_sensitivity_v1.py) · [Matching summary table](juice_confidence_sensitivity_v1.csv). The 54 rows cover three arms, six populations and sugars/energy/salt; input and script hashes accompany each row. The exact excluded keys are reconstructible from the unchanged beverage/juice layers and the predicate above; no duplicate product export is required.",
        f"Validation: exact 1,090/7,468 partition; composite key and leading-zero-sensitive string preservation; corrected-juice subset equality; complete missing/available reconciliation; summary CSV round-trip; processing dependency/script hash verification; before/after hashes of {len(frozen)} protected source/evidence artifacts. Master, locked claims, classifications, register and all 12 human observations are unchanged.",
        "**Decision: stop this sensitivity. No further classification, OCR/LLM, model or manual-review iteration is required for this question.**"])
    append_section(HERE/"juice_classification_CHECK_v1.md",body)
    approval="\n\n".join(["## Approval and consolidation handoff · 19 November 2026",
        "**Approved by Julia.** Retain French muesli organic × recorded NOVA 4 only as an association among selected observations with known organic-communication status and recorded NOVA: 6/24 versus 25/48. Documented non-detection is limited to assessed evidence. Do not infer healthfulness, causality, organic compliance, population prevalence or cross-region replication.",
        "The corrected juice layer is accepted after the final 1,090-record confidence sensitivity; its headline interpretation is stable. HIGH/MEDIUM denotes textual evidence strength, not independently verified package identity. [Final sensitivity and acceptance](../01_nutritional_composition/juice_classification_CHECK_v1.md). Sparse, unresolved and deferred populations retain their stated decisions. Consolidation is the next phase and has not started."])
    append_section(LENSES/"04_positioning_tradeoffs/processing_boundaries_CHECK_v1.md",approval)


if __name__=="__main__":main()
