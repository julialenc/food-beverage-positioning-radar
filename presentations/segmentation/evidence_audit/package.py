"""Prepare immutable offline OCR/LLM evidence assets; never call providers."""
import ast,collections,gzip,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if os.name=='nt' and not str(ROOT).startswith('\\\\?\\'):ROOT=Path('\\\\?\\'+str(ROOT))
HERE=ROOT/'presentations/segmentation/evidence_audit';OUT=ROOT/'outputs/ocr_llm_evidence_candidate_v1'
ING=ROOT/'presentations/segmentation/first_run/01_ingestion'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def source_closure():
 queue=[p for folder in ['pipeline/segmentation','pipeline/vision_ops'] for p in (ROOT/folder).glob('*.py')];seen=set()
 while queue:
  p=queue.pop()
  if p in seen or not p.is_file():continue
  seen.add(p);tree=ast.parse(p.read_text(encoding='utf-8-sig'))
  names=[]
  for node in ast.walk(tree):
   if isinstance(node,ast.Import):names.extend(a.name for a in node.names)
   elif isinstance(node,ast.ImportFrom) and node.module:
    names.append(node.module);names.extend(node.module+'.'+a.name for a in node.names)
  for name in names:
   for candidate in [ROOT/Path(*name.split('.')).with_suffix('.py'),ROOT/Path(*name.split('.'))/'__init__.py',p.parent/Path(*name.split('.')).with_suffix('.py')]:
    if candidate.is_file():queue.append(candidate)
 return seen
class SplitWriter:
 def __init__(self,group):self.group=group;self.i=0;self.f=None;self.size=0;self.parts=[]
 def write(self,data):
  total=len(data);view=memoryview(data)
  while view:
   if self.f is None:
    p=OUT/'assets'/f'{self.group}.tar.gz.{self.i:03d}';self.f=p.open('wb');self.parts.append(p);self.i+=1;self.size=0
   take=min(len(view),512*1024**2-self.size);self.f.write(view[:take]);self.size+=take;view=view[take:]
   if self.size==512*1024**2:self.f.close();self.f=None
  return total
 def flush(self):
  if self.f:self.f.flush()
 def close(self):
  if self.f:self.f.close();self.f=None
secret=re.compile(rb'(?:sk-proj-[A-Za-z0-9_-]{40,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|Authorization[\"\s:]+Bearer [A-Za-z0-9._~-]{30,})')

def refresh_sources():
 manifest=json.loads((OUT/'manifest.json').read_bytes());files=manifest['files']
 paths={ROOT/rel for rel,meta in files.items() if meta['asset_group']=='source'}
 paths.update(p for p in source_closure() if p.relative_to(ROOT).as_posix() not in files)
 paths.update(p for p in HERE.glob('*') if p.is_file() and p.name!='manifest.json')
 for p in paths:
  raw=p.read_bytes();assert not secret.search(raw),'Potential credential in '+p.name
  files[p.relative_to(ROOT).as_posix()]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),asset_group='source')
 archive=OUT/'asset_revisions';archive.mkdir(exist_ok=True)
 for item in manifest['assets']['source']:
  old=OUT/'assets'/item['name'];saved=archive/(item['sha256']+'_'+item['name'])
  if not saved.exists():
   import shutil
   shutil.copyfile(old,saved)
 split=SplitWriter('source')
 with gzip.GzipFile(fileobj=split,mode='wb',compresslevel=1,mtime=0) as gz:
  with tarfile.open(fileobj=gz,mode='w|',format=tarfile.PAX_FORMAT) as tar:
   for p in sorted(paths):tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
 split.close();manifest['assets']['source']=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in split.parts]
 manifest['historical_gaps']['original_image_bytes_unavailable_for_historical_reuses']=35
 manifest['historical_gaps']['historical_saved_ocr_available']=35
 save(HERE/'manifest.json',manifest);save(OUT/'manifest.json',manifest);save(OUT/'source_inventory.json',files)
 print('SOURCE_ASSET_REFRESHED',len(paths),'files; data assets unchanged',flush=True)
def main():
 refresh='--refresh-source' in sys.argv
 if refresh and (OUT/'manifest.json').exists():return refresh_sources()
 resume='--resume-pack' in sys.argv
 assert refresh or resume or not OUT.exists(),'Use a new candidate; never overwrite evidence assets'
 (OUT/'assets').mkdir(parents=True,exist_ok=refresh or resume)
 cached=json.loads((OUT/'source_inventory.json').read_bytes()) if resume or refresh else {}
 base={ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p}
 extra=set(ING.rglob('*'));extra={p for p in extra if p.is_file() and '__pycache__' not in p.parts}
 for name in ['data/05_vision_release','data/04_vision_sampling','data/03_pipeline_intermediates','pipeline/vision_prompts']:
  extra.update(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 old=ROOT/'data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1'
 extra.update(p for p in old.iterdir() if p.is_file() and p.name!='release_public.db')
 extra.add(ROOT/'database/positioning_radar.db')
 extra.update(source_closure())
 for name in ['pipeline/segmentation','pipeline/vision_ops']:
  extra.update((ROOT/name).glob('*.py'))
 extra.update(p for p in HERE.glob('*') if p.is_file() and p.name!='manifest.json')
 groups=collections.defaultdict(list);files={};findings=[]
 for p in sorted(base|extra):
  rel=p.relative_to(ROOT).as_posix();size=p.stat().st_size
  assert 'data/02_raw_off_downloads/' not in rel or p.name=='.gitkeep'
  assert p.suffix not in ['.pyc'] and '.env'!=p.name
  prior=cached.get(rel)
  h=prior['sha256'] if prior and not rel.startswith('presentations/segmentation/evidence_audit/') and prior['bytes']==size else sha(p)
  if p in base:group='base'
  elif '/image_evidence/' in rel or '/wave2_dairy_execution_v1/images/' in rel:group='images'
  elif rel=='database/positioning_radar.db':group='historical_database'
  elif p.suffix in ['.sqlite','.db']:group='ledgers_and_governed_input'
  elif rel.startswith(('pipeline/','shared/','presentations/segmentation/evidence_audit/')):group='source'
  else:group='evidence'
  files[rel]=dict(sha256=h,bytes=size,asset_group=group)
  groups[group].append(p)
  if not prior and (p.suffix in ['.py','.json','.jsonl','.csv','.md','.txt','.toml','.yaml','.yml'] or p.name.startswith('.env')):
   with p.open('rb') as f:
    carry=b''
    while block:=f.read(1024*1024):
     if secret.search(carry+block):findings.append(rel);break
     carry=block[-512:]
 assert not findings,'Potential credential/private-key material: '+str(findings)
 save(OUT/'source_inventory.json',files)
 assets=json.loads((OUT/'manifest.json').read_bytes())['assets'] if refresh else {}
 for group,paths in groups.items():
  if refresh and group not in ['source','historical_database']:continue
  print('PACKING',group,len(paths),'files',round(sum(p.stat().st_size for p in paths)/1024**3,3),'GiB',flush=True)
  split=SplitWriter(group)
  with gzip.GzipFile(fileobj=split,mode='wb',compresslevel=1,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w|',format=tarfile.PAX_FORMAT) as tar:
    for p in paths:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
  split.close();assets[group]=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in split.parts]
  print('PACKED',group,len(split.parts),'parts',flush=True)
 manifest=dict(version='wave2_evidence_v1',planned_release='v1.1.0',status='LOCAL_CANDIDATE_NOT_PUBLISHED',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=files,assets=assets,main_readme_sha256=sha(ROOT/'README.md'),source_root_recorded=str(ROOT),historical_gaps=dict(raw_model_responses_unavailable=35,rule='Do not invent or substitute new responses'),credentials_scan='High-confidence key/private-key patterns checked; structured ledger scan also required',excluded=['timestamped OFF downloads','credentials','working environments','unrelated trial databases','outputs/ workspaces','unapproved parked app changes'])
 if refresh:
  before=json.loads((OUT/'manifest.json').read_bytes())['files']
  assert all(meta==files[rel] for rel,meta in before.items() if meta['asset_group']!='source'),'Non-source inputs changed'
 save(HERE/'manifest.json',manifest);save(OUT/'manifest.json',manifest)
 print('PACKAGE_READY',len(files),'files;',sum(len(v) for v in assets.values()),'asset parts',flush=True)
if __name__=='__main__':main()
