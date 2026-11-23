"""Bind a completed replay to the final distributed evidence/source assets."""
import argparse,gzip,hashlib,importlib.util,io,json,tarfile
from pathlib import Path
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',required=True,type=Path);p.add_argument('--workspace',required=True,type=Path);a=p.parse_args()
 spec=importlib.util.spec_from_file_location('evidence_validator',Path(__file__).with_name('validate.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 candidate,home=v.lp(a.candidate),v.lp(a.workspace)
 manifest=json.loads((candidate/'manifest.json').read_bytes());initial=json.loads((home/'evidence_manifest.json').read_bytes());results=json.loads((home/'results.json').read_bytes())
 assert results['status']=='PASS' and len(results['stages'])==34
 assert all(r['status']=='PASS' and not any(r['actual_denials'].values()) for r in results['stages'])
 for rel,meta in initial['files'].items():
  if meta['asset_group']!='source':assert manifest['files'][rel]==meta,rel
 for group,parts in manifest['assets'].items():
  if group!='source':assert parts==initial['assets'][group],group
  for meta in parts:
   path=candidate/'assets'/meta['name'];assert path.stat().st_size==meta['bytes'] and sha(path)==meta['sha256'],path.name
 observed=set();paths=[candidate/'assets'/m['name'] for m in manifest['assets']['source']]
 with v.Parts(paths) as raw,io.BufferedReader(raw) as stream,gzip.GzipFile(fileobj=stream) as gz,tarfile.open(fileobj=gz,mode='r|') as archive:
  for item in archive:
   assert item.isfile() and item.name not in observed and '..' not in Path(item.name).parts
   meta=manifest['files'][item.name];assert meta['asset_group']=='source'
   with archive.extractfile(item) as incoming:assert hashlib.file_digest(incoming,'sha256').hexdigest()==meta['sha256'],item.name
   observed.add(item.name)
 assert observed=={rel for rel,meta in manifest['files'].items() if meta['asset_group']=='source'}
 executed={}
 for result in results['stages']:
  for rel,digest in result['source_files'].items():
   origin=__import__('re').sub(r'/04_replay_candidate(?:_\d+)?/','/04_analytical_package/',rel)
   assert manifest['files'][origin]['sha256']==digest,rel
   executed[origin]=digest
 for name in ['validate.py','upstream_entry.py']:
  rel='presentations/segmentation/evidence_audit/'+name;assert sha(home/'checkout'/rel)==manifest['files'][rel]['sha256']
 preservation=json.loads((candidate/'preservation.json').read_bytes());assert preservation['status']=='PASS' and not preservation['differences']
 security=json.loads((home/'ledger_security.json').read_bytes());assert security['status']=='PASS' and security['credential_findings']==0
 report=dict(status='PASS',manifest_sha256=sha(candidate/'manifest.json'),stages=34,executed_source_files=len(executed),asset_parts=sum(map(len,manifest['assets'].values())),asset_bytes=sum(m['bytes'] for parts in manifest['assets'].values() for m in parts),data_assets_unchanged_from_verified_restoration=True,final_source_assets_match_executed_code=True,original_preservation=preservation,historical_gaps=manifest['historical_gaps'],harness_revisions_recorded=len(json.loads((home/'config.json').read_bytes()).get('harness_revisions',[])))
 (candidate/'final_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
