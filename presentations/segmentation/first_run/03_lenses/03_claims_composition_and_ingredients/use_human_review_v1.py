"""Interpret Julia's bounded visual review without changing original entries or locked claims."""
import datetime
import hashlib
from pathlib import Path

import pandas as pd

HERE=Path(__file__).resolve().parent
EXPECTED="002a1df55b94f778ab300bfd375836bdc98f16f2a879a62ce8f1730ca410ce0d"
KEY=["barcode","region","category","proposition"]
# Explicit interpretations of this reviewed submission, not a general claim extractor.
DECISIONS={
 "HR01":("POSITIVE","Julia explicitly reports protein positioning with high-protein wording."),
 "HR02":("POSITIVE","Julia explicitly reports protein positioning and records protein wording; 18g is not converted to per100g."),
 "HR03":("REPORTED_NOT_DETECTED","Julia reports No claims on the submitted image; formal panel/quality fields are blank."),
 "HR04":("POSITIVE","Julia explicitly reports protein positioning; low-fat wording remains a separate observation."),
 "HR05":("POSITIVE","Julia explicitly reports high-protein wording; low-fat/low-sugar wording remains separate."),
 "HR06":("UNKNOWN","Reported provenance/handmade communication does not explicitly resolve the targeted protein proposition; ganache scope remains provisional."),
 "HR07":("UNCERTAIN","A -50% sign is visible but its comparison attribute is unreadable; reduced fat cannot be established."),
 "HR08":("UNKNOWN","Reported free-from communication does not explicitly resolve the targeted reduced-fat proposition."),
 "HR09":("REPORTED_NOT_DETECTED","Julia reports No claims on the submitted image; formal panel/quality fields are blank."),
 "HR10":("UNKNOWN","Popped not fried and per-serving energy wording do not establish an explicit reduced-fat proposition."),
 "HR11":("POSITIVE","Julia explicitly transcribes Reduced fat; unreadable surrounding words remain unresolved."),
 "HR12":("UNKNOWN","The recorded reduction is 45% less salt; the targeted reduced-fat proposition remains unresolved.")
}
def main():
    source=HERE/"human_claim_decisions_v1.csv"
    before=source.read_bytes()
    assert hashlib.sha256(before).hexdigest()==EXPECTED,"New human submission requires an updated explicit interpretation."
    review=pd.read_csv(source,dtype=str,keep_default_na=False)
    manifest=pd.read_csv(HERE/"human_claim_review_v1.csv",dtype=str,keep_default_na=False)
    assert len(review)==12 and review.review_id.is_unique and set(review.review_id)==set(DECISIONS)
    rows=[]
    for _,entered in review.iterrows():
        saved=manifest[manifest.review_id.eq(entered.review_id)].iloc[0]
        for key in KEY[1:]:assert entered[key]==saved[key],(entered.review_id,key)
        assert entered.barcode.lstrip("0")==saved.barcode.lstrip("0")
        assert entered.human_image_used==saved.image_url
        try:
            date=datetime.datetime.strptime(entered.human_review_date,"%d.%m.%Y").date()
            status="future recorded date" if date>datetime.date(2026,11,18) else "valid recorded date"
            normalized=date.isoformat() if status=="valid recorded date" else ""
        except ValueError:status="unresolved recorded date";normalized=""
        state,reason=DECISIONS[entered.review_id]
        row={k:saved[k] for k in ["review_id"]+KEY+["branch","arm","product_name","image_url"]}
        row.update(barcode_recorded=entered.barcode,key_reconciliation="restored from exact review manifest" if entered.barcode!=saved.barcode else "exact",
           human_claim_state_recorded=entered.human_claim_state,human_exact_wording_recorded=entered.human_exact_wording,
           human_other_wording_recorded=entered.human_other_wording,human_notes_recorded=entered.human_notes,
           reviewer=entered.human_reviewer,review_date_recorded=entered.human_review_date,review_date_normalized=normalized,
           date_status=status,submission_received_date="2026-11-18",derived_target_state=state,interpretation=reason,
           evidence_provenance="JULIA_VISUAL_REVIEW",evidence_scope="submitted front-image reference",
           metadata_limit="identity match, panel scope and image quality not separately entered",
           inferential_usage="bounded diagnostic examples only; no population-rate update",
           source_sha256=EXPECTED,locked_master_sha256=saved.locked_master_sha256)
        for key in ["energy_kcal_per100g","protein_g_per100g","fat_g_per100g","sugars_g_per100g"]:
            row[key]=saved[key]
        rows.append(row)
    result=pd.DataFrame(rows)
    assert not result.duplicated(KEY).any()
    assert result.key_reconciliation.eq("restored from exact review manifest").sum()==5
    assert result.date_status.eq("future recorded date").sum()==11
    assert result.derived_target_state.value_counts().to_dict()=={"POSITIVE":5,"UNKNOWN":4,"REPORTED_NOT_DETECTED":2,"UNCERTAIN":1}
    result.to_csv(HERE/"human_claim_adjudications_v1.csv",index=False,encoding="utf-8-sig")
    assert source.read_bytes()==before
    print(result[["review_id","branch","region","arm","derived_target_state"]].to_string(index=False))
    print("PASS original submission unchanged; 12 exact reconciled keys; five explicit target positives; date/metadata limits retained.")
if __name__=="__main__":main()
