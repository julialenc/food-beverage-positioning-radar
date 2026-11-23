"""Execute only offline historical functions, with hash-bound path relocation."""
import ast,builtins,collections,csv,hashlib,importlib.util,io,json,os,re,sqlite3,sys,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HOME=ROOT.parent;STUDY=ROOT/'presentations/segmentation/first_run';ING=STUDY/'01_ingestion'
STAGE=os.environ['FBR_EVIDENCE_STAGE'];CONFIG=json.loads((HOME/'config.json').read_bytes())
ORIGINAL=CONFIG['evidence_original_root'].replace('\\','/').removeprefix('//?/').rstrip('/')
MOVES=json.loads((ING/'historical_paths.json').read_bytes());aliases=[]
original_open=builtins.open;original_io_open=io.open;original_exists=Path.exists;original_uri=Path.as_uri;original_connect=sqlite3.connect
def norm(p):return str(p).replace('\\','/').removeprefix('//?/')
def route(path):
 if isinstance(path,int):return path
 raw=norm(os.fsdecode(path));new=raw
 local_prefixes=[norm(HOME).lower()+'/',norm(Path(sys.executable).parent.parent).lower()+'/']
 if not any(raw.lower().startswith(p) for p in local_prefixes) and raw.lower().startswith(ORIGINAL.lower()+'/'):new=norm(ROOT)+raw[len(ORIGINAL):]
 prefix=norm(ROOT/'presentations/segmentation')+'/'
 if new.lower().startswith(prefix.lower()):
  suffix=new[len(prefix):]
  for key in sorted(MOVES,key=len,reverse=True):
   if suffix==key or suffix.startswith(key+'/'):
    new=prefix+MOVES[key]+suffix[len(key):];break
 if new!=raw:aliases.append(dict(recorded=raw,resolved=new))
 if os.name=='nt' and len(new)>240 and not new.startswith('//?/'):new='//?/'+new
 return Path(new)
def opened(file,*args,**kw):return original_open(route(file) if isinstance(file,(str,bytes,os.PathLike)) else file,*args,**kw)
builtins.open=opened
io.open=lambda file,*a,**kw: original_io_open(route(file) if isinstance(file,(str,bytes,os.PathLike)) else file,*a,**kw)
Path.exists=lambda p,*a,**kw:original_exists(route(p),*a,**kw)
Path.as_uri=lambda p:original_uri(Path(norm(route(p))))
def connect(database,*args,**kwargs):
 value=str(database)
 if value.startswith('file:'):
  url=urllib.parse.urlsplit(value);path=urllib.parse.unquote(url.path)
  if os.name=='nt' and len(path)>2 and path[0]=='/' and path[2]==':':path=path[1:]
  database=original_uri(Path(norm(route(path))))+'?mode=ro&immutable=1';kwargs['uri']=True
 return original_connect(database,*args,**kwargs)
sqlite3.connect=connect
import dotenv
dotenv.load_dotenv=lambda *a,**kw:False
sys.path[:0]=[str(ROOT),str(ROOT/'pipeline/segmentation')]
csv.field_size_limit(100000000)
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(relative,name):
 path=ROOT/relative;spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if STAGE=='ledger_security':
 sensitive={'api_key','apikey','authorization','ocp-apim-subscription-key','subscription_key','access_token','refresh_token','client_secret','password','private_key'}
 tree=ast.parse((ROOT/'pipeline/vision_ops/run_06b_execution_guard.py').read_text(encoding='utf-8'))
 human_authorization=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONTENT_FILTER_AUTHORIZATION' for t in n.targets))
 hits=[];counts={};cells=0
 def inspect(value,where):
  if isinstance(value,dict):
   for k,v in value.items():
    if k.lower().replace('-','_') in {x.replace('-','_') for x in sensitive} and isinstance(v,str) and len(v)>12 and v.lower() not in ['offline-capture','not-used-offline','offline-placeholder'] and not (k=='authorization' and v==human_authorization):hits.append(where+':'+k)
    inspect(v,where)
  elif isinstance(value,list):
   for v in value:inspect(v,where)
 for path in sorted(ING.rglob('*.sqlite')):
  if not path.stat().st_size:continue
  db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
  assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok',str(path)
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
  counts[str(path.relative_to(ROOT))]={}
  for table in tables:
   quoted='"'+table.replace('"','""')+'"';columns=db.execute('PRAGMA table_info('+quoted+')').fetchall()
   counts[str(path.relative_to(ROOT))][table]=db.execute('SELECT count(*) FROM '+quoted).fetchone()[0]
   names=[c[1] for c in columns if 'json' in c[1].lower() or c[1] in ['payload','body']]
   if not names:continue
   select=','.join('"'+n.replace('"','""')+'"' for n in names)
   for row in db.execute('SELECT '+select+' FROM '+quoted):
    for value in row:
     if not isinstance(value,str):continue
     try:parsed=json.loads(value)
     except (ValueError,TypeError):continue
     cells+=1;inspect(parsed,str(path.relative_to(ROOT))+'/'+table)
  db.close()
 assert not hits,'Sensitive credential fields require review: '+str(sorted(set(hits)))
 (HOME/'ledger_security.json').write_text(json.dumps(dict(status='PASS',json_cells_scanned=cells,ledger_tables=counts,credential_findings=0),indent=2),encoding='utf-8')
 print('LEDGER_INTEGRITY_AND_STRUCTURED_CREDENTIAL_SCAN_PASS',cells,flush=True)
elif STAGE=='population_snapshot':
 m=load('presentations/segmentation/first_run/01_ingestion/01_population/run_01/run_01_source_snapshot.py','population_snapshot_source')
 m.ROOT=ROOT;m.run(ROOT/'data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/release_work.db',ING/'01_population/replay_population',ROOT/'data/01_reference_inputs/01_country_region_mapping.csv')
elif STAGE=='historical_history':
 m=load('pipeline/segmentation/run_06b_prepare.py','historical_selection_source')
 history,_=m.run05_functions();base=m.read(m.FIVE/'candidate_ledger.csv')
 agg,events,inventory,_=history(base)
 out=ING/'03_pack_evidence/02_image_selection_and_identity/replay_history';out.mkdir()
 for name,frame in [('history_status_refreshed.csv',agg),('history_observations_refreshed.csv',events),('history_source_inventory_refreshed.csv',inventory)]:frame.to_csv(out/name,index=False,lineterminator='\n',float_format='%.12g')
 print('HISTORICAL_HISTORY_REBUILT',len(agg),len(events),flush=True)
elif STAGE=='image_selection_lineage':
 path=ING/'02_nutrition_and_sampling/04_final_selection/run_06b_final_candidates_v1/proposed_primary_processing_manifest.csv'
 with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==11902 and len({r['proposed_primary_slot_id'] for r in rows})==11902
 cache=ING/'03_pack_evidence/02_image_selection_and_identity/run_06b_v1/image_evidence'
 seen=set()
 for r in rows:
  h=r['image_sha256'];assert h and (cache/(h+'.bin')).is_file()
  if h not in seen:assert sha(cache/(h+'.bin'))==h;seen.add(h)
 policy=json.loads((ING/'03_pack_evidence/04_pilot_and_authorization/run_06b_main_readiness_v1/main_policy.AUTHORIZED.json').read_bytes())
 assert sha(path)==policy['manifest_sha256'] and set(policy['authorized_primary_slots'])=={r['proposed_primary_slot_id'] for r in rows}
 dairy=json.loads((ING/'03_pack_evidence/05_execution_ledgers/wave2_dairy_execution_v1/frozen_inputs.json').read_bytes());assert len(dairy['jobs'])==224
 for job in dairy['jobs']:assert sha(route(ROOT/job['immutable_image_path']))==job['image_sha256']
 packaged=json.loads((HOME/'evidence_manifest.json').read_bytes())['files']
 cached=[(rel,meta) for rel,meta in packaged.items() if '/run_06b_v1/image_evidence/' in rel]
 for rel,meta in cached:assert Path(rel).stem==meta['sha256'],rel
 assert len(cached)==14395
 print('IMAGE_AND_AUTHORIZED_SELECTION_PASS',len(seen),'distinct main images; 224 dairy jobs',flush=True)
elif STAGE in ['main_quality','dairy_quality','combined_review','claims_reconciliation','claim_lock']:
 names={'main_quality':'summarize_run_06b_completion_quality','dairy_quality':'export_wave2_dairy_review','combined_review':'export_wave2_combined_review','claims_reconciliation':'reconcile_wave2_claims','claim_lock':'lock_wave2_ocr_llm'}
 m=load('pipeline/segmentation/'+names[STAGE]+'.py','evidence_'+STAGE)
 if hasattr(m,'file_hash'):m.file_hash=sha
 if hasattr(m,'digest') and STAGE=='dairy_quality':m.digest=sha
 if STAGE=='claims_reconciliation':sys.argv=[str(m.__file__),'--rebuild']
 else:sys.argv=[str(m.__file__)]
 if STAGE=='claim_lock':
  m.OUT=ING/'04_reviewed_claims/03_final_lock/replay_lock_candidate'
  m.APPROVAL=ING/'04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/final_approval.md'
  if m.OUT.exists():sys.argv.append('--rebuild-unlocked')
 m.main()
else:raise ValueError(STAGE)
(HOME/(STAGE+'_path_aliases.json')).write_text(json.dumps(aliases,indent=2),encoding='utf-8')
