"""Read-only original-file verification against the pre-cleanup inventory."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if os.name=='nt' and not str(ROOT).startswith('\\\\?\\'):ROOT=Path('\\\\?\\'+str(ROOT))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 baseline=json.loads((ROOT/'outputs/cleanup_20261123_audit/protected_before.json').read_bytes());bad=[];managed=[]
 for i,(rel,meta) in enumerate(baseline.items(),1):
  p=ROOT/rel
  if not p.is_file() or p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:
   (managed if rel.startswith('.git/refs/codex/turn-diffs/') else bad).append(rel)
  if i%5000==0:print('CHECKED_ORIGINALS',i,flush=True)
 tag=subprocess.check_output(['git','rev-parse','v1.0.0'],cwd=ROOT,text=True).strip()
 assert tag=='ba592459b4c355e94b1c2088d0d9d9b78910a320',tag
 assert not bad,'Original file differences: '+str(bad)
 result=dict(status='PASS',original_files_checked=len(baseline),differences=bad,app_managed_tracking_ref_changes=managed,tracking_ref_note='Codex desktop maintains its own turn-diff capture/checkpoint refs; no project branches, tags or Git objects are exempted',v1_0_0_tag_object=tag,main_readme_sha256=sha(ROOT/'README.md'),baseline_sha256=sha(ROOT/'outputs/cleanup_20261123_audit/protected_before.json'))
 (ROOT/'outputs/ocr_llm_evidence_candidate_v1/preservation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('ORIGINALS_UNCHANGED',len(baseline),flush=True)
if __name__=='__main__':main()
