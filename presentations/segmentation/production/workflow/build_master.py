"""Build the regional product master from one governed work database and its wave's locked claims."""
from pipeline.rules.barcode_identity import resolve as resolve_barcode
import argparse
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pipeline.segmentation.run_01_select_eligible_products import assignments, country_mapping, validate_release
from .evidence_index import assignment
from .artifact_paths import FIRST, ROOT
from .artifact_paths import LOCK, digest

WAVE2 = "real_off_20261017_proxy_20260929"
REGIONS = {"FR":"FR", "IE":"UK-IE", "UK":"UK-IE", "US":"US-CA", "CA":"US-CA"}


def exact_rules(path, decision):
    if path is None:
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        result = {}
        for row in csv.DictReader(stream):
            row["barcode"] = resolve_barcode(row["barcode"])
            key = assignment(row)
            if key in result and result[key] != row[decision]:
                raise ValueError(f"Conflicting reviewed alias key: {key}")
            result[key] = row[decision]
        return result


def build(source, release_manifest, lock, output, wave, exclusions=None, beverages=None):
    source, lock, output = source.resolve(strict=True), lock.resolve(strict=True), output.resolve()
    if output.exists():
        raise FileExistsError(output)
    contract = json.loads((lock/"manifest.json").read_bytes())
    if contract["status"] != "LOCKED" or (contract.get("wave_id") != wave and
                                          not (wave == WAVE2 and lock == LOCK.resolve())):
        raise ValueError("Claims lock is not bound to the requested wave")
    claim_path = lock/"claims_join.parquet"
    if digest(claim_path) != contract["outputs"]["claims_join.parquet"]["sha256"]:
        raise ValueError("Locked claims hash mismatch")
    checks = exact_rules(exclusions, "decision")
    beverage = exact_rules(beverages, "status")
    mapping = country_mapping(ROOT/"data/01_reference_inputs/01_country_region_mapping.csv")
    counts = Counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp, closing(sqlite3.connect(
            source.as_uri()+"?mode=ro",uri=True)) as db, closing(sqlite3.connect(Path(tmp)/"lookup.db")) as evidence:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        release, population, manifest_path, manifest_sha = validate_release(db,source,release_manifest)
        if release["wave_id"] != wave:
            raise ValueError("Governed population differs from requested wave")
        result = Path(tmp)/"output"
        result.mkdir()
        claims = pq.ParquetFile(claim_path)
        from pipeline.stages import stage_05_load_database as loader
        overrides = loader.load_reviewed_product_mapping_overrides()
        category_relinks = []
        evidence.execute("CREATE TABLE claims(barcode TEXT,region TEXT,category TEXT,payload TEXT,PRIMARY KEY(barcode,region,category)) WITHOUT ROWID")
        for batch in claims.iter_batches(batch_size=256,use_threads=False):
            for row in batch.to_pylist():
                row["source_barcode"] = row["barcode"]
                row["source_category"] = row["category"]
                row["barcode"] = resolve_barcode(row["barcode"])
                product = db.execute("SELECT query_category,observed_market_region_codes FROM products WHERE barcode=?",(row["barcode"],)).fetchone()
                current_category = {"dairies":"dairy","cereals":"cereal"}.get(product[0],product[0]) if product else None
                if current_category and current_category != row["category"]:
                    reviewed = loader._product_override_for_row(overrides,row["barcode"],product[1])
                    approved = {"dairies":"dairy","cereals":"cereal"}.get(reviewed.get("category"),reviewed.get("category")) if reviewed else None
                    if approved != current_category:
                        raise ValueError("Claims category change lacks an existing reviewed decision")
                    category_relinks.append(dict(record_id=row["record_id"],barcode=row["barcode"],region=row["region"],source_category=row["source_category"],category=current_category,basis="existing_reviewed_product_mapping"))
                    row["category"] = current_category
                key = assignment(row)
                if key != tuple(row[k] for k in ("barcode","region","category")):
                    raise ValueError("Claims key outside the canonical namespace")
                evidence.execute("INSERT INTO claims VALUES (?,?,?,?)",(*key,json.dumps(row,allow_nan=False)))
        types = {"TEXT":pa.string(),"REAL":pa.float64(),"INTEGER":pa.int64(),"INT":pa.int64()}
        fields = [pa.field(r["name"],types[r["type"]]) for r in db.execute("pragma table_info(retained_deployment_products)")]
        fields += [pa.field("region",pa.string()),pa.field("category",pa.string()),
                   pa.field("assignment_countries",pa.list_(pa.string())),pa.field("claims_matched",pa.bool_()),
                   pa.field("reviewed_nutrition_category_decision",pa.string()),pa.field("reviewed_beverage_status",pa.string()),
                   pa.field("product_scope_eligible",pa.bool_())]
        claim_fields = [f for f in claims.schema_arrow if f.name not in ("barcode","region","category")] + [pa.field("source_barcode",pa.string()),pa.field("source_category",pa.string())]
        schema = pa.schema(fields + [pa.field("claims_"+f.name,f.type) for f in claim_fields],
                           metadata={"wave_id":wave,"reporting_date":release["reporting_date"],
                                     "retrieved_at":release["retrieved_at"],"source_sha256":release["source_sha256"]})
        path = result/"master_products.parquet"
        previous = None
        batch = []
        with pq.ParquetWriter(path,schema,compression="zstd") as writer:
            for product in db.execute("SELECT * FROM retained_deployment_products ORDER BY barcode"):
                raw = dict(product)
                barcode = raw["barcode"]
                if not isinstance(barcode,str) or not barcode or barcode == previous:
                    raise ValueError("Missing or duplicate source barcode")
                previous = barcode
                regions = {}
                for country,_ in assignments(raw["countries"],mapping):
                    regions.setdefault(REGIONS[country],[]).append(country)
                if not regions or raw["include_in_product_table"] not in (0,1):
                    raise ValueError(f"Invalid governed assignment or physical gate: {barcode}")
                counts["products"] += 1
                for region,countries in regions.items():
                    key=assignment(dict(barcode=barcode,region=region,category=raw["query_category"]))
                    hit=evidence.execute("SELECT payload FROM claims WHERE barcode=? AND region=? AND category=?",key).fetchone()
                    eligible = bool(raw["include_in_product_table"]) and checks.get(key) in (None,"review_only_keep") and beverage.get(key) not in ("excluded","hold")
                    record=dict(raw,region=region,category=key[2],assignment_countries=countries,claims_matched=bool(hit),
                                product_scope_eligible=eligible,reviewed_nutrition_category_decision=checks.get(key),
                                reviewed_beverage_status=beverage.get(key))
                    if hit:
                        claim=json.loads(hit[0])
                        record.update({"claims_"+f.name:claim[f.name] for f in claim_fields})
                        counts["matched"]+=1
                        counts["matched_excluded"]+=int(claim["analytical_eligible"] is False)
                    counts["assignments"]+=len(countries)
                    counts["master_rows"]+=1
                    batch.append(record)
                    if len(batch)>=1024:
                        writer.write_table(pa.Table.from_pylist(batch,schema=schema))
                        batch.clear()
            if batch:
                writer.write_table(pa.Table.from_pylist(batch,schema=schema))
        if counts["products"]!=population or counts["matched"]!=claims.metadata.num_rows:
            raise ValueError(f"Incomplete population or claims coverage: {dict(counts)}")
        counts["unmatched"]=counts["master_rows"]-counts["matched"]
        with pq.ParquetFile(path) as check:
            if check.metadata.num_rows!=counts["master_rows"]:
                raise ValueError("Parquet row count mismatch")
        manifest=dict(release=release,release_manifest_sha256=manifest_sha,source_database=str(source),
                      claims_sha256=digest(claim_path),master_sha256=digest(path),counts=dict(counts),
                      category_relinks=category_relinks,join_keys=["barcode","region","category"],rules={str(p):digest(p) for p in (exclusions,beverages) if p})
        (result/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        os.rename(result,output)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","release-manifest","lock","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--wave",required=True)
    parser.add_argument("--exclusions",type=Path)
    parser.add_argument("--beverages",type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.source,args.release_manifest,args.lock,args.output,args.wave,
                           args.exclusions,args.beverages),indent=2))
