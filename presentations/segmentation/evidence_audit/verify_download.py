"""Verify downloaded v1.1.0 assets and tagged source without extracting data.

The manifest is bound to a source ZIP whose Git blob IDs match --commit.
Every split asset and every restored file is streamed through SHA-256. This
performs no network/provider calls and does not repeat the scientific replay.
"""
import argparse,gzip,hashlib,importlib.util,io,json,subprocess,tarfile,time,zipfile
from pathlib import Path

def digest(stream,algorithm='sha256',prefix=b''):
 h=hashlib.new(algorithm);h.update(prefix)
 while block:=stream.read(1024*1024):h.update(block)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--candidate',type=Path,required=True)
 p.add_argument('--source-archive',type=Path,required=True)
 p.add_argument('--commit',required=True)
 p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[3])
 p.add_argument('--report',type=Path,required=True)
 a=p.parse_args();started=time.time()
 spec=importlib.util.spec_from_file_location('offline_restore',Path(__file__).with_name('validate.py'))
 v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 candidate=v.lp(a.candidate)
 manifest_bytes=(candidate/'manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
 tree={}
 raw=subprocess.check_output(['git','ls-tree','-rz','--full-tree',a.commit],cwd=a.repo_root)
 for entry in raw.split(b'\0'):
  if not entry:continue
  header,path=entry.split(b'\t',1);mode,kind,oid=header.decode().split()
  assert kind=='blob' and mode in ['100644','100755'],path
  tree[path.decode('utf-8')]=oid
 with zipfile.ZipFile(a.source_archive) as archive:
  members=[m for m in archive.infolist() if not m.is_dir()]
  prefixes={m.filename.split('/',1)[0] for m in members};assert len(prefixes)==1
  prefix=prefixes.pop()+'/'
  paths={m.filename[len(prefix):]:m for m in members}
  assert set(paths)==set(tree),'Tagged archive file list differs from Git tree'
  for rel,member in paths.items():
   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
   with archive.open(member) as stream:
    actual=digest(stream,'sha1',b'blob '+str(member.file_size).encode()+b'\0')
   assert actual==tree[rel],rel
  rel='presentations/segmentation/evidence_audit/manifest.json'
  assert archive.read(paths[rel])==manifest_bytes,'Downloaded manifest differs from tagged source'
 print('TAGGED_SOURCE_ARCHIVE_PASS',len(tree),'Git blobs',flush=True)
 observed=set();restored_bytes=0;part_count=0;asset_bytes=0
 for group,parts in manifest['assets'].items():
  paths=[]
  for meta in parts:
   assert Path(meta['name']).name==meta['name']
   path=candidate/'assets'/meta['name']
   assert path.stat().st_size==meta['bytes'],path.name
   with path.open('rb') as stream:assert digest(stream)==meta['sha256'],path.name
   paths.append(path);part_count+=1;asset_bytes+=meta['bytes']
  print('DOWNLOADED_PART_HASHES_PASS',group,len(parts),flush=True)
  with v.Parts(paths) as raw,io.BufferedReader(raw) as stream,gzip.GzipFile(fileobj=stream) as gz,tarfile.open(fileobj=gz,mode='r|') as archive:
   for member in archive:
    rel=member.name
    assert member.isfile() and rel not in observed and not Path(rel).is_absolute() and '..' not in Path(rel).parts,rel
    meta=manifest['files'][rel]
    assert meta['asset_group']==group and member.size==meta['bytes'],rel
    with archive.extractfile(member) as incoming:assert digest(incoming)==meta['sha256'],rel
    observed.add(rel);restored_bytes+=member.size
  print('RESTORED_FILE_HASHES_PASS',group,flush=True)
 assert observed==set(manifest['files']),'Missing/extra restored files'
 report=dict(status='PASS',tag='v1.1.0',source_commit=a.commit,source_archive_git_blobs=len(tree),manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),downloaded_asset_parts=part_count,downloaded_asset_bytes=asset_bytes,restored_files=len(observed),restored_bytes=restored_bytes,historical_gaps=manifest['historical_gaps'],seconds=round(time.time()-started,2),limits=['Byte/hash verification of anonymously downloaded release assets and tagged source ZIP','No full extraction, new 34-stage replay, fresh dependency installation or provider calls','35 historical cases still lack retained original images and raw model envelopes'])
 a.report.parent.mkdir(parents=True,exist_ok=True)
 a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PUBLIC_DOWNLOAD_VERIFICATION_PASS',len(observed),'files;',part_count,'asset parts',flush=True)

if __name__=='__main__':main()
