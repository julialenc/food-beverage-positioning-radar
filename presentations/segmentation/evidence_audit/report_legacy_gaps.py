"""Describe retained/missing evidence for the 35 legacy claims reuses."""
import argparse,hashlib,json,os
from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[3]
if os.name=='nt' and not str(ROOT).startswith('\\\\?\\'):ROOT=Path('\\\\?\\'+str(ROOT))
relative='presentations/segmentation/first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/historical_reuses.parquet'
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,default=ROOT/'outputs/ocr_llm_evidence_isolation_v1');p.add_argument('--candidate',type=Path,default=ROOT/'outputs/ocr_llm_evidence_candidate_v1');a=p.parse_args()
source=a.workspace/'checkout'/relative
with source.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
manifest=json.loads((a.candidate/'manifest.json').read_bytes())
assert manifest['files'][relative]['sha256']==digest
rows=pq.read_table(source).to_pylist();assert len(rows)==35
report=[]
for row in rows:
 assert row['ocr_text_full'] and not row['core_raw_output_json']
 report.append({**{k:row[k] for k in ['barcode','image_url','source_references','historical_prompt_version','historical_model','historical_source_region','source_market_limitation']},'saved_ocr_sha256':hashlib.sha256(row['ocr_text_full'].encode('utf-8')).hexdigest(),'raw_model_envelope_retained':False,'frozen_original_image_bytes_found':False})
out=ROOT/'presentations/segmentation/evidence_audit/historical_gaps.json'
out.write_text(json.dumps(dict(source=relative,source_sha256=digest,records=report,image_search_basis='No URL or same-image-version match in the main content-addressed image inventory; none of the 35 barcode image files in dairy cache; remaining retained images are derived review sheets, not original image bytes',limitation='Retained OCR and extracted records permit downstream reproduction; original image-to-model transport cannot be reconstructed for these legacy cases'),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('LEGACY_GAP_REGISTER_WRITTEN',len(report),flush=True)
