"""Verify cross-lens population reconciliation and record the reviewed control selection."""
from pathlib import Path
import hashlib
import json
import platform
import sys
from importlib.metadata import version
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
EDA=ROOT.parent/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
MASTER=ROOT.parent/"01_ingestion/05_master_parquet/output"
SELECTED_K=5

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def main(write_manifest=True):
    files=sorted(ROOT.glob("*/hypothesis_results_v1.csv"))
    assert len(files)==4
    all_rows=pd.concat([pd.read_csv(p) for p in files],ignore_index=True)
    primary=all_rows[all_rows.variant.eq("primary")]
    assert set(primary.h)=={f"H{i}" for i in range(1,13)}
    pairs=primary[(primary.h=="H2") & (primary.tol==10) & (primary.direction=="forward")]
    assert len(pairs)==6 and pairs.n.sum()==4230 and pairs.pairs.sum()==2095
    assert (pairs.pairs*2<=pairs.n).all() and (pairs.max_energy_gap<=10).all()
    assert np.allclose(pairs.success_n/pairs.pairs,pairs.effect)
    for _,g in primary[(primary.h=="H8") & primary.test.str.startswith("joint")].groupby("test"):
        assert g.state_n.sum()==1866 and g[g.state.isin(["True/True","False/False","True/False","False/True"])].state_n.sum()==45
        assert g[g.state=="True/True"].state_n.sum()==0
    assert all_rows[all_rows.h=="H8"].p.isna().all()
    h10=all_rows[all_rows.h=="H10"]
    assert len(h10)==1 and (h10.iloc[0][["region","category","subtype"]].tolist()==["US-CA","cereal","GRANOLA"])
    assert h10.iloc[0].pos==42 and h10.iloc[0].neg==38
    assert np.isclose(h10.iloc[0].effect,8/42-1/38)
    control=next(ROOT.glob("*/control_assignments_v1.parquet"))
    labels=pd.read_parquet(control)
    assert labels.barcode.map(lambda s:isinstance(s,str)).all() and labels.barcode.str.startswith("0").any()
    assert not labels.duplicated(["barcode","region","category"]).any()
    assert labels.groupby("population").size().to_dict()=={"reference":114146,"US seen":1875,"US unseen":12036}
    ref=labels[labels.population.eq("reference")]
    assert ref.barcode.is_unique
    assert not set(ref.barcode).intersection(labels.loc[labels.population.eq("US unseen"),"barcode"])
    metrics=pd.read_csv(control.parent/"control_comparison_v1.csv")
    for k in [3,4,5]:
        profiles=metrics[(metrics.kind=="profile") & (metrics.population=="reference") & (metrics.k==k)]
        assert profiles.set_index("group").n.sort_index().tolist()==ref[f"k{k}"].value_counts().sort_index().tolist()
        assert len(profiles)==k
    diag=pd.read_csv(EDA/"FEATURE_DECISIONS.csv")
    for h,n in [("H5",14),("H9",13)]:
        a=primary[primary.h.eq(h) & primary.effect.notna()]
        if h=="H5": a=a[a.provenance=="all"]
        else: a=a[a.supported==True]
        assert len(a)==n==int(diag[diag.scope.str.startswith(h+" ") & diag.record_kind.eq("claim_comparison")].cells_20_each.sum())
    high=primary[(primary.h=="H11")&(primary.known_n>=30)]
    assert high.groupby("test").size().to_dict()=={"fibre_claim":12,"protein_claim":15}
    assert set(all_rows[all_rows.variant=="ingredient language FR"].h)=={"H7"}
    assert len(all_rows[(all_rows.variant=="exclude LOW")&(all_rows.h=="H12")])>0
    review=next(ROOT.glob("*/ingredient_validation_v1.csv"))
    audit=pd.read_csv(review,dtype={"barcode":str})
    assert len(audit)==72 and len(audit[audit.review_label=="unassessable"])==6
    assert (audit.loc[audit.review_label!="unassessable","pea_soy_text_cue"].to_numpy()==
            audit.loc[audit.review_label!="unassessable","review_label"].eq("present").to_numpy()).all()
    frozen=json.loads((MASTER/"manifest.json").read_text(encoding="utf8"))
    assert digest(MASTER/"master_products.parquet")==frozen["master_sha256"]
    outputs=files+[control,control.parent/"control_comparison_v1.csv",review]
    paths=outputs+sorted(ROOT.rglob("*.py"))+[EDA/"shared_feature_diagnostics_v1.py",EDA/"H1_H12_ANALYTICAL_PLAN.md",
                                             EDA/"subtype_assignments.csv"]
    first=ROOT.parent
    manifest=dict(version=1,master_sha256=frozen["master_sha256"],locked_claims_sha256=frozen["claims_sha256"],
                  cutoff=frozen["release"]["reporting_date"],retrieved_at=frozen["release"]["retrieved_at"],
                  governed_assignments=376845,named_peers=292302,selected_k=SELECTED_K,assignment_column="k5",
                  primary_rows_by_hypothesis=primary.groupby("h").size().to_dict(),python=platform.python_version(),
                  packages={pkg:version(pkg) for pkg in ["numpy","pandas","scipy","scikit-learn","pyarrow"]},
                  sha256={str(p.relative_to(first).as_posix()):digest(p) for p in paths})
    path=ROOT/"run_manifest_v1.json"
    previous=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if write_manifest:
        # Preserve source archives and documentation revisions during a later approved rebuild.
        manifest={**previous,**manifest}
        path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    else:
        # Integrity verification does not rewrite the accepted manifest or any output.
        for relative,expected in previous.get("sha256",{}).items():
            assert digest(ROOT.parent/relative)==expected,("research dependency changed",relative)
        for relative,entry in previous.get("housekeeping_v1",{}).get("source_archive",{}).items():
            assert hashlib.sha256(entry["text"].encode("utf-8")).hexdigest()==entry["sha256"],relative
    print("PASS: 12 hypotheses, H8 joint and unknown states, H10 scope, all 3 control candidates, GTIN and population checks, source hash, sensitivities and validation sample.")

if __name__=="__main__":
    main(write_manifest="--check-only" not in sys.argv)
