"""Restore only declared evidence assets and run offline isolated replay."""
import argparse,gzip,hashlib,importlib.util,io,json,os,shutil,subprocess,sys,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def lp(p):
 p=Path(p).resolve()
 return Path('\\\\?\\'+str(p)) if os.name=='nt' and not str(p).startswith('\\\\?\\') else p
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
I=Path('presentations/segmentation/first_run/01_ingestion')
REVIEW=I/'04_reviewed_claims'
ENTRY=Path('presentations/segmentation/evidence_audit/upstream_entry.py')
LOCK=REVIEW/'03_final_lock/wave2_ocr_llm_lock_v1'
NEWLOCK=REVIEW/'03_final_lock/replay_lock_candidate'
POP=['eligibility_ledger.csv','candidate_population.csv','check_01_country_category.csv','check_01_nutrient_completeness.csv','check_01_warning_breakdown.csv','check_01_ocr_coverage.csv']
UP=[('ledger_security',ENTRY,[]),('population_snapshot',ENTRY,[I/'01_population/replay_population'/x for x in POP]),
 ('historical_history',ENTRY,[I/'03_pack_evidence/02_image_selection_and_identity/replay_history'/x for x in ['history_status_refreshed.csv','history_observations_refreshed.csv','history_source_inventory_refreshed.csv']]),
 ('image_selection_lineage',ENTRY,[]),
 ('main_quality',ENTRY,[REVIEW/'01_completion_reviews/run_06b_completion_quality_v1'/x for x in ['products.csv','issues.csv','region_category_summary.csv','reason_summary.csv','product_evidence.jsonl']]),
 ('dairy_quality',ENTRY,[REVIEW/'01_completion_reviews/wave2_dairy_completion_quality_v1'/x for x in ['products.csv','issues.csv']]),
 ('combined_review',ENTRY,[REVIEW/'02_reconciliation_and_exceptions/wave2_combined_ocr_llm_review_v1/all_processed_products.csv']),
 ('claims_reconciliation',ENTRY,[REVIEW/'02_reconciliation_and_exceptions/wave2_claims_reconciliation_v1/reconciled_review.csv']),
 ('claim_lock',ENTRY,[NEWLOCK/x for x in ['claims_join.parquet','new_processed_audit.parquet','historical_reuses.parquet','historical_handoff.json']])]
def module(path):
 spec=importlib.util.spec_from_file_location('offline_replay',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Parts(io.RawIOBase):
 def __init__(self,paths):self.paths=iter(paths);self.f=None
 def readable(self):return True
 def readinto(self,b):
  while True:
   if self.f is None:
    try:self.f=next(self.paths).open('rb')
    except StopIteration:return 0
   n=self.f.readinto(b)
   if n:return n
   self.f.close();self.f=None
 def close(self):
  if self.f:self.f.close()
  super().close()
def unpack(candidate,home):
 assert not home.exists(),'Use a new isolated workspace'
 home.mkdir(parents=True);clone=home/'checkout';clone.mkdir();refs=home/'references';refs.mkdir()
 manifest=json.loads((candidate/'manifest.json').read_bytes())
 observed=set()
 for group,parts in manifest['assets'].items():
  paths=[candidate/'assets'/p['name'] for p in parts]
  for p,meta in zip(paths,parts):assert p.stat().st_size==meta['bytes'] and sha(p)==meta['sha256'],p.name
  print('RESTORING',group,flush=True)
  with Parts(paths) as raw,io.BufferedReader(raw) as stream,gzip.GzipFile(fileobj=stream) as gz,tarfile.open(fileobj=gz,mode='r|') as tar:
   for item in tar:
    rel=Path(item.name);assert not rel.is_absolute() and '..' not in rel.parts and item.isfile(),item.name
    dest=clone/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    key=rel.as_posix();assert key in manifest['files'] and key not in observed,key
    digest=hashlib.sha256();size=0
    with tar.extractfile(item) as incoming,dest.open('wb') as out:
     while block:=incoming.read(1024*1024):out.write(block);digest.update(block);size+=len(block)
    meta=manifest['files'][key];assert digest.hexdigest()==meta['sha256'] and size==meta['bytes'],key
    observed.add(key)
 assert observed==set(manifest['files']),'Incomplete assets'
 print('ALL_ASSET_FILE_HASHES_PASS',len(manifest['files']),flush=True)
 prior=json.loads((clone/'presentations/segmentation/audit_replay/release/manifest.json').read_bytes())
 for item in prior['inputs']:
  dest=clone/item['path']
  if 'parts' in item:
   dest.parent.mkdir(parents=True,exist_ok=True)
   paths=[clone/'presentations/segmentation/audit_replay/release'/p['path'] for p in item['parts']]
   with Parts(paths) as raw,io.BufferedReader(raw) as stream,gzip.GzipFile(fileobj=stream) as gz,dest.open('wb') as out:shutil.copyfileobj(gz,out)
  assert sha(dest)==item['sha256'],item['path']
  if 'parts' not in item:
   target=refs/item['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dest,target)
 for stage,_,outputs in UP:
  for rel in outputs:
   original=Path(str(rel).replace('replay_population','run_01').replace('replay_lock_candidate','wave2_ocr_llm_lock_v1').replace('replay_history','run_06b_v1'))
   target=refs/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(clone/original,target)
 shutil.copytree(clone/'presentations/segmentation/audit_replay/human_source_versions',home/'human_source_versions')
 tree={}
 for rel in manifest['files']:
  if rel.endswith('.py'):
   raw=(clone/rel).read_bytes();tree[rel]=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 replay=clone/'presentations/segmentation/audit_replay/replay.py';shutil.copyfile(replay,home/'replay.py')
 save(home/'config.json',dict(source=manifest['source_root_recorded'],home=str(home),commit=manifest['base_commit'],original_hashes={},published_tree=tree,runner_sha256=sha(replay),isolation_forbidden_root=manifest['source_root_recorded'],evidence_original_root=manifest['source_root_recorded'],evidence_manifest_sha256=sha(candidate/'manifest.json')))
 shutil.copyfile(candidate/'manifest.json',home/'evidence_manifest.json')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path);p.add_argument('--workspace',required=True,type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--sync-source',action='store_true');p.add_argument('--worker');a=p.parse_args();home=lp(a.workspace)
 if not a.worker and not a.resume:unpack(lp(a.candidate),home)
 if a.sync_source:
  assert a.resume and not a.worker
  config=json.loads((home/'config.json').read_bytes());archive=home/'harness_revisions'/str(time.time_ns());archive.mkdir(parents=True)
  changes=[]
  for source in HERE.glob('*.py'):
   rel=source.relative_to(ROOT);dest=home/'checkout'/rel
   if dest.exists() and sha(source)==sha(dest):continue
   if dest.exists():shutil.copyfile(dest,archive/source.name)
   shutil.copyfile(source,dest);raw=dest.read_bytes();config['published_tree'][rel.as_posix()]=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();changes.append(dict(path=rel.as_posix(),sha256=sha(dest)))
  for log in home.glob('*.log'):shutil.copyfile(log,archive/log.name)
  config.setdefault('harness_revisions',[]).append(dict(directory=str(archive),changes=changes));save(home/'config.json',config)
 clone=home/'checkout';m=module(home/'replay.py');old=list(m.STAGES);m.STAGES=UP+old
 if a.worker:
  # urllib3 otherwise binds ::1 during import to probe IPv6 availability.
  # Offline replay never needs that capability; transport remains audit-blocked.
  import socket
  socket.has_ipv6=False
  if a.worker in {x[0] for x in UP}:os.environ['FBR_EVIDENCE_STAGE']=a.worker
  return m.worker(home,a.worker)
 results=[]
 for name,_,outputs in m.STAGES:
  path=home/(name+'_result.json')
  if a.resume and path.exists() and json.loads(path.read_bytes())['status']=='PASS':
   r=json.loads(path.read_bytes());print('RETAINED_PASS',name,flush=True)
   for rel,digest in r.get('source_files',{}).items():assert sha(clone/rel)==digest,'Completed source changed: '+rel
  else:
   if path.exists():
    hist=home/'attempt_history'/name/str(time.time_ns());hist.mkdir(parents=True);shutil.copyfile(path,hist/'result.json')
    if (home/(name+'.log')).exists():shutil.copyfile(home/(name+'.log'),hist/'stage.log')
    for rel in outputs:
     if (clone/rel).exists():
      target=hist/'outputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(clone/rel,target)
   env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['AZURE','OPENAI','ANTHROPIC','API_KEY','TOKEN','SECRET','PASSWORD'])}
   env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONIOENCODING='utf-8')
   print('START',name,flush=True)
   with (home/(name+'.log')).open('w',encoding='utf-8') as log:rc=subprocess.call([sys.executable,'-I','-B','-X','utf8',str(clone/'presentations/segmentation/evidence_audit/validate.py'),'--workspace',str(home),'--worker',name],cwd=clone,env=env,stdout=log,stderr=subprocess.STDOUT)
   r=json.loads(path.read_bytes()) if path.exists() else dict(stage=name,status='FAIL',exit_code=rc)
  results.append(r);save(home/'results.json',dict(status='RUNNING' if r['status']=='PASS' else 'FAIL',stages=results));print('FINISHED',name,r['status'],r.get('seconds'),flush=True)
  if r['status']!='PASS':return 1
  if name=='claim_lock':
   assert sha(clone/NEWLOCK/'claims_join.parquet')==sha(home/'references'/NEWLOCK/'claims_join.parquet'),'Downstream fixed-byte contract requires exact derived claims'
   shutil.copyfile(clone/NEWLOCK/'claims_join.parquet',clone/LOCK/'claims_join.parquet')
 save(home/'results.json',dict(status='PASS',stages=results,limits=['35 historical raw model envelopes unavailable; retained OCR and extracted evidence preserved','No new provider calls; historical saved observations are starting evidence','Recorded installed environment reused']))
 print('OFFLINE_EVIDENCE_AND_ANALYSIS_PASS',len(results),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
