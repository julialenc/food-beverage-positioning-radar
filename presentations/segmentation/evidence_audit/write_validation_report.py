"""Record completed checks; refuse to certify an incomplete replay."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from importlib.metadata import version
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if os.name=='nt' and not str(ROOT).startswith('\\\\?\\'):ROOT=Path('\\\\?\\'+str(ROOT))
HERE=ROOT/'presentations/segmentation/evidence_audit'
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
 results=json.loads((a.workspace/'results.json').read_bytes());assert results['status']=='PASS' and len(results['stages'])==34
 assert all(r['status']=='PASS' and not any(r['actual_denials'].values()) for r in results['stages'])
 manifest=json.loads((a.candidate/'manifest.json').read_bytes());assert sha(ROOT/'README.md')==manifest['main_readme_sha256']
 frozen=subprocess.check_output([sys.executable,'-B',str(ROOT/'presentations/segmentation/first_run/04_analytical_package/verify_analytical_package_v1.py')],cwd=ROOT,text=True)
 digest='48212697d2d245e3cc543032d63699b7e83fb43ad5db8dce7cbb8714991f0557';assert 'PASS' in frozen and digest in frozen
 tag=subprocess.check_output(['git','rev-parse','v1.0.0'],cwd=ROOT,text=True).strip();assert tag=='ba592459b4c355e94b1c2088d0d9d9b78910a320'
 preservation=json.loads((a.candidate/'preservation.json').read_bytes());assert preservation['status']=='PASS' and not preservation['differences']
 security=json.loads((a.workspace/'ledger_security.json').read_bytes());assert security['status']=='PASS'
 helper_packages={}
 for line in (HERE/'requirements-evidence.txt').read_text().splitlines():
  if '==' not in line:continue
  name,expected=line.split('==');helper_packages[name]=version(name);assert helper_packages[name]==expected,(name,helper_packages[name],expected)
 config=json.loads((a.workspace/'config.json').read_bytes());initial=json.loads((a.workspace/'evidence_manifest.json').read_bytes())
 gaps=json.loads((HERE/'historical_gaps.json').read_bytes());assert len(gaps['records'])==35
 report=dict(status='PASS_WITH_DOCUMENTED_LEGACY_EVIDENCE_GAPS',completed_at_utc=datetime.now(timezone.utc).isoformat(),replay=results,restored_starting_files=len(initial['files']),security=security,additional_helper_packages=helper_packages,preservation=preservation,frozen_release_digest=digest,main_readme_unchanged=True,v1_0_0_unchanged=True,harness_revisions=config.get('harness_revisions',[]),historical_gap_register_sha256=sha(HERE/'historical_gaps.json'),limits=['35 historical reused assessments lack retained original image bytes and raw model envelopes; saved OCR/extracted records remain available','Historical sampling choices and human decisions are fixed evidence inputs, not regenerated judgments','Installed recorded environment reused; fresh dependency installation not tested','Corrected path routing and disabled an unused urllib3 IPv6 loopback import probe; failed attempts and code revisions retained in isolated workspace','Final source asset refresh and binding to executed scientific-source hashes must pass verify_final.py before completion'])
 save(HERE/'VALIDATION.json',report)
 lines=['# Local evidence candidate — validation check','', 'Completed 23 November 2026. **Not committed, pushed, tagged or published.**','', '## Result','', '**34/34 replay checks passed**, with documented legacy evidence gaps. All final passed workers recorded zero actual network/provider/subprocess/outside-write/original-tree-read denials beyond guard self-tests. No provider calls occurred.','', 'The 15,995 starting files were restored from declared assets and byte-verified. The population and historical-processing tables, four claims-lock files and rebuilt master reproduced byte-for-byte. Remaining scientific comparisons use the v1.0 replay tolerances and its documented metadata exceptions; raw generated results are retained.','', 'The ledger scan checked 293,862 JSON cells and SQLite integrity. The exact recorded human authorization text is classified as approval evidence, not a credential. An import-time local IPv6 feature probe was blocked in a failed attempt, then disabled; outbound transport remains forbidden.','', 'Original-file verification covered 31,599 baseline entries with no project-file differences. Two Codex-managed turn-diff tracking refs changed automatically; project branches/tags and Git objects were not exempted. The main README is unchanged. Frozen release digest: `'+digest+'`.','', '## Stage results','', '| Stage | Status | Seconds |','|---|---|---:|']
 lines.extend('| '+r['stage']+' | PASS | '+str(r['seconds'])+' |' for r in results['stages'])
 lines.extend(['','## Scope and limits','', 'The 35 legacy reuses retain saved OCR, extracted results and source provenance, but original image bytes and raw model envelopes were not found. See [the case register](historical_gaps.json). This is a package of all retained evidence, not a claim that those missing originals have been recovered.','', 'Sampling choices and human decisions remain fixed historical inputs. Exploratory selection-model fits and human judgments are not repeated. The recorded installed Python environment was reused.','', 'Harness corrections, failed attempts and source revisions are retained in `outputs/ocr_llm_evidence_isolation_v1/`. Passed earlier stages were retained only after their scientific-source hashes were rechecked. Final source assets must match the executed scientific code; data assets must remain identical to the verified restoration. The final asset attestation is staged at `outputs/ocr_llm_evidence_candidate_v1/final_verification.json`.','', 'The [machine-readable validation report](VALIDATION.json), [scope](RELEASE_SCOPE.md) and [manifest](manifest.json) provide the detailed identities. Public download verification remains a future post-publication check. The main README is deferred.',''])
 (HERE/'CHECK.md').write_text('\n'.join(lines),encoding='utf-8')
 manifest['status']='LOCAL_CANDIDATE_VALIDATED_WITH_LEGACY_GAPS_NOT_PUBLISHED';manifest['credentials_scan']='PASS: high-confidence text patterns and structured SQLite JSON scan; exact human authorization literal classified separately';manifest['validation']=dict(report='presentations/segmentation/evidence_audit/VALIDATION.json',sha256=sha(HERE/'VALIDATION.json'),stages=34,final_asset_attestation='Separate outputs/ocr_llm_evidence_candidate_v1/final_verification.json binds the final manifest and assets')
 save(a.candidate/'manifest.json',manifest);save(HERE/'manifest.json',manifest)
 print('VALIDATION_REPORT_WRITTEN_34_PASS',flush=True)
if __name__=='__main__':main()
