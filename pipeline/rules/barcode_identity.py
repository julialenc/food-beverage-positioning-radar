"""Preserve OFF identifiers and resolve verified historical zero aliases."""
import csv
from functools import lru_cache
from pathlib import Path

REGISTER = Path(__file__).resolve().parents[2] / "data/06_brand_governance_outputs/wave2_identity_fix_v1/barcode_aliases.csv"

def valid_gtin(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or len(value) not in (8, 12, 13, 14) or not value.strip("0"):
        return False
    total = sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(value[:-1])))
    return (total + int(value[-1])) % 10 == 0

@lru_cache(maxsize=1)
def aliases():
    if not REGISTER.exists():
        return {}
    with REGISTER.open(encoding="utf-8-sig", newline="") as stream:
        return {row["source_barcode"]: row["canonical_barcode"] for row in csv.DictReader(stream) if row["decision"] == "resolved"}

def resolve(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Barcode must be nonempty text without whitespace")
    return aliases().get(value, value)

def identity_key(value):
    value = resolve(value)
    return "gtin:" + value.zfill(14) if valid_gtin(value) else "off:" + value

def population_lookup(conn):
    bind_aliases(conn)
    result = {}
    physical = {row[0] for row in conn.execute("SELECT barcode FROM products")}
    if any(resolve(code) not in physical for code in physical):
        raise ValueError("Historical aliases require the corrected Wave 2 baseline")
    for code in physical:
        canonical = resolve(code)
        key = identity_key(canonical)
        prior = result.get(key)
        if prior is not None and prior != canonical:
            raise ValueError("Unresolved barcode identity collision: " + key)
        result[key] = canonical
    return result

def bind_aliases(conn):
    """Load the identity register embedded in a deployed release."""
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='barcode_aliases'").fetchone():
        for source, canonical in conn.execute("SELECT source_barcode,canonical_barcode FROM barcode_aliases"):
            previous = aliases().setdefault(source,canonical)
            if previous != canonical:
                raise ValueError("Conflicting deployed barcode alias")

def source_image_barcode(url):
    """Read the OFF product directory from a saved image URL, without network access."""
    from urllib.parse import urlsplit
    path=urlsplit(url or "").path
    if "/products/" not in path:
        return None
    directory=path.split("/products/",1)[1].rsplit("/",1)[0].replace("/","")
    return directory if directory.isascii() and directory.isdigit() else None
