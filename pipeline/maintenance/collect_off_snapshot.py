"""Download a pinned OFF bulk export with resumable, fail-closed transport.

Only downloads evidence; never opens a product database. Use --output-dir under
data/02_raw_off_downloads/incremental_snapshots/. Rerun the same command to resume.
An incomplete download never receives a complete manifest. Retrieval timestamps
are actual UTC clock readings, never the proxy cutoff date.
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.maintenance.capture_database_baseline import sha256

SNAPSHOTS = ROOT / 'data/02_raw_off_downloads/incremental_snapshots'
URL = 'https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz'
USER_AGENT = 'FoodBeveragePositioningRadar/1.0 (github.com/julialenc/food-beverage-positioning-radar)'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def collect(output, session=None):
    import requests
    output = Path(output).resolve()
    if not output.is_relative_to(SNAPSHOTS.resolve()) or output == SNAPSHOTS.resolve():
        raise ValueError('Snapshot output must be a child of incremental_snapshots')
    output.mkdir(parents=True, exist_ok=True)
    partial, source = output / 'source.csv.gz.part', output / 'source.csv.gz'
    metadata_path, completed = output / 'transport.json', output / 'manifest.json'
    lock = output / 'collection.lock'
    with lock.open('x'):
        pass
    owned_session = session is None
    session = session or requests.Session()
    try:
        if completed.exists():
            manifest = json.loads(completed.read_text(encoding='utf-8'))
            if manifest.get('status') != 'complete' or sha256(source) != manifest['sha256']:
                raise ValueError('Completed snapshot changed')
            return completed
        metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else None
        if metadata is not None and metadata['url'] != URL:
            raise ValueError('Source identity changed')
        if source.exists():
            if metadata is None or source.stat().st_size != metadata['expected_bytes']:
                raise ValueError('Unverified final snapshot')
        else:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'}
            if offset:
                if metadata is None or not metadata.get('etag') or metadata['etag'].startswith('W/'):
                    raise ValueError('Safe resume requires the original strong ETag; use a new output directory')
                if offset > metadata['expected_bytes']:
                    raise ValueError('Partial file exceeds declared length')
                headers.update({'Range': f'bytes={offset}-', 'If-Range': metadata['etag']})
            if not metadata or offset < metadata['expected_bytes']:
                with session.get(URL, headers=headers, stream=True, timeout=(30, 60)) as response:
                    response.raise_for_status()
                    if response.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ValueError('Unexpected HTTP content encoding')
                    if offset:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                        if (response.status_code != 206 or not match or
                                tuple(map(int, match.groups())) != (offset, metadata['expected_bytes'] - 1, metadata['expected_bytes'])
                                or response.headers.get('ETag') != metadata['etag']):
                            raise ValueError('Server changed the snapshot or refused exact range resume')
                    else:
                        if response.status_code != 200:
                            raise ValueError('Expected full download response')
                        length = int(response.headers.get('Content-Length', 0))
                        if length <= 0:
                            raise ValueError('Content-Length required to establish transport completeness')
                        metadata = dict(url=URL, resolved_url=response.url,
                                        retrieval_started_at=now(), expected_bytes=length,
                                        etag=response.headers.get('ETag'),
                                        export_last_modified=response.headers.get('Last-Modified'))
                        save(metadata_path, metadata)
                    length = int(response.headers.get('Content-Length', 0))
                    if length != metadata['expected_bytes'] - offset:
                        raise ValueError('Response length does not match remaining source bytes')
                    with partial.open('ab' if offset else 'wb') as stream:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                if stream.tell() + len(chunk) > metadata['expected_bytes']:
                                    raise ValueError('Response exceeds declared source length')
                                stream.write(chunk)
                    if partial.stat().st_size != metadata['expected_bytes']:
                        raise ValueError('Incomplete response; rerun to resume')
                metadata['retrieval_finished_at'] = now()
                save(metadata_path, metadata)
            # gzip EOF validates truncation and CRC before the source is finalized.
            with gzip.open(partial, 'rb') as stream:
                while stream.read(1024 * 1024):
                    pass
            partial.replace(source)
        if 'retrieval_finished_at' not in metadata:
            # Recovery after interruption immediately after the last byte.
            metadata['retrieval_finished_at'] = now()
            save(metadata_path, metadata)
        with gzip.open(source, 'rb') as stream:
            while stream.read(1024 * 1024):
                pass
        manifest = dict(status='complete', format='off-tsv-gzip-v1', file=source.name,
                        sha256=sha256(source), bytes=source.stat().st_size,
                        **metadata, verified_at=now(),
                        interpretation='Bulk export retrieved at the recorded time; export age is separate from retrieval and proxy cutoff.')
        save(completed, manifest)
        return completed
    finally:
        if owned_session:
            session.close()
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(collect(args.output_dir))
