"""Connect a completed staged wave to governed processing on its copy only."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules.governed_ingestion import connect

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--wave-id', required=True)
    args = parser.parse_args()
    print(connect(args.database, args.wave_id))
