"""Stage a completed OFF snapshot on a fresh copy; no product writes.

Create: --policy-trial PATH --snapshot-dir PATH --wave-id ID
Resume: --database PATH --snapshot-dir PATH --wave-id ID
A copied database and raw evidence stay local; no production stage is invoked.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules import incremental_ingestion as writer
from pipeline.rules.proxy_wave import stage
from pipeline.maintenance.collect_off_snapshot import save


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument('--policy-trial', type=Path)
    location.add_argument('--database', type=Path)
    parser.add_argument('--snapshot-dir', type=Path, required=True)
    parser.add_argument('--wave-id', required=True)
    parser.add_argument('--cutoff', default='2026-09-29')
    parser.add_argument('--cutoff-timezone', default='Europe/Berlin')
    args = parser.parse_args()
    database = args.database
    if database is None:
        output = writer.TRIALS / datetime.now(timezone.utc).strftime('proxy_%Y%m%dT%H%M%S_%fZ')
        database = writer.create_copy(args.policy_trial, output)
    print(f'Copy: {database}', flush=True)
    report = stage(database, args.snapshot_dir, wave_id=args.wave_id,
                   cutoff=args.cutoff, cutoff_timezone=args.cutoff_timezone)
    save(database.parent / 'proxy_report.json', report)
    print(report)
