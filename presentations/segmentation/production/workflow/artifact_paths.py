"""Resolve recorded first-wave paths without modifying signed manifests."""
import hashlib
import json
from pathlib import Path

PRODUCTION = Path(__file__).resolve().parents[1]
ROOT = PRODUCTION.parents[2]
LOCAL = PRODUCTION / "local"
SEG = ROOT / "presentations/segmentation"
FIRST = SEG / "first_run"
INGESTION = FIRST / "01_ingestion"
RECORDED_SOURCE = INGESTION / "04_reviewed_claims/recorded_source"
MOVES = json.loads((INGESTION / "historical_paths.json").read_text(encoding="utf-8-sig"))


def relocated(path):
    path = Path(path)
    try:
        relative = path.relative_to(SEG)
    except ValueError:
        return path
    parts = relative.parts
    if not parts:
        return path
    for length in range(len(parts), 0, -1):
        key = "/".join(parts[:length])
        target = MOVES.get(key)
        if target is None and length == 1 and key != "first_run":
            target = MOVES.get("first_run/"+key)
        if target:
            return SEG/target/Path(*parts[length:])
    return path


class HistoricalPath(type(Path())):
    """Used by legacy modules that compose frozen relative filenames in stages."""
    def __truediv__(self, value):
        return type(self)(relocated(Path(self)/value))


def verified_contract_file(path, expected):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual == expected:
        return True
    # Only these location-only migrations are accepted for a signed contract.
    migrated = CONTRACT_MIGRATION.get(expected)
    if not migrated or actual != migrated:
        return False
    original = RECORDED_SOURCE / path.relative_to(ROOT)
    return hashlib.sha256(original.read_bytes()).hexdigest() == expected

CONTRACT_MIGRATION = {
    "8594571cc543245bae178927fd9664176005c6882d670d1798ec11236e4fd11e": "d6a179dba88ea690cd978ef1c3eceda514092391268ce525878e1da6c1fa30d7",
    "1a7bee917434660be461caa16a41e1940af41724cdaaf9ed7904ce4b5eedaeec": "876c4b6f33aec9e741202acbcc270192faa318e8bd224c89ba2ae7fa0139e9ac"
}


LOCK = relocated(SEG / "wave2_ocr_llm_lock_v1")

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
