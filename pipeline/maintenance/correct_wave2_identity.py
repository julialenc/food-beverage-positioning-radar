"""Correct the September Wave 2 identity defect from preserved local evidence."""
import argparse
import csv
import gzip
import importlib
import json
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.rules.barcode_identity import valid_gtin, aliases, resolve, identity_key, source_image_barcode
from pipeline.maintenance.build_incremental_release import settings, SNAPSHOT_TABLES
from pipeline.maintenance.capture_database_baseline import sha256
from pipeline.stages import stage_05_load_database as loader
from pipeline.stages import stage_17_build_deployment_database as deployment

OUT = ROOT / "data/06_brand_governance_outputs/wave2_identity_fix_v1"
ORIGINAL = ROOT / "data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1"
WORK = OUT / "release_work.db"
PERIOD = "2026-09-29"

def connect(path):
    return sqlite3.connect(path)

def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2), encoding="utf-8")

def correct():
    OUT.mkdir(exist_ok=True)
    if WORK.exists():
        with connect(WORK) as existing:
            if existing.execute("SELECT 1 FROM sqlite_master WHERE name='barcode_aliases'").fetchone():
                raise FileExistsError("Correction exists; resume at reporting")
    else:
        shutil.copy2(ORIGINAL/"release_work.db", WORK)
    source = ORIGINAL/"release_work.db"
    expected = json.loads((ROOT/"presentations/segmentation/first_run/01_ingestion/01_population/run_01/run_01_manifest.json").read_bytes())["source_database_sha256"]
    if sha256(source) != expected or sha256(WORK) != expected:
        raise ValueError("Wave 2 source or copied bytes differ from the pinned source")
    print("Copying frozen Wave 2", flush=True)
    # Existing incomplete copy is reused only before alias changes were committed.
    db = connect(WORK)
    db.row_factory = sqlite3.Row
    columns = "p.barcode,p.product_name,p.image_url,p.ingested_at,p.created_t,p.countries,p.observed_market_region_codes,p.query_category,p.protein_100g,p.fiber_100g,p.sugars_100g,m.membership"
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("CREATE TEMP TABLE candidate_keys AS SELECT ltrim(barcode,'0') AS identity FROM products WHERE barcode NOT GLOB '*[^0-9]*' AND barcode!='' GROUP BY ltrim(barcode,'0') HAVING count(*)=2")
    print("Indexing compact identity evidence", flush=True)
    db.execute("CREATE TEMP TABLE identity_source AS SELECT " + columns + " FROM products p NOT INDEXED JOIN population_membership m USING(barcode)")
    db.execute("CREATE INDEX temp.identity_source_barcode ON identity_source(barcode)")
    decisions = []
    links = []
    db.execute("CREATE TEMP TABLE identity_keys AS SELECT barcode,ltrim(barcode,'0') AS identity FROM products WHERE ltrim(barcode,'0') IN (SELECT identity FROM candidate_keys)")
    db.execute("CREATE INDEX temp.identity_keys_lookup ON identity_keys(identity)")
    candidate_pairs = db.execute("SELECT a.barcode,b.barcode FROM identity_keys a JOIN identity_keys b USING(identity) WHERE length(a.barcode)<length(b.barcode)").fetchall()
    print("Resolving",len(candidate_pairs),"candidate pairs",flush=True)
    for pair in candidate_pairs:
        rows = [dict(db.execute("SELECT * FROM identity_source WHERE barcode=?", (code,)).fetchone()) for code in pair]
        old,target = rows
        october = target["ingested_at"].startswith("2026-10-17")
        name = bool(old["product_name"]) and old["product_name"] == target["product_name"]
        nutrients = all(old[k] == target[k] for k in ("protein_100g","fiber_100g","sugars_100g"))
        image_code = source_image_barcode(old["image_url"])
        image = bool(image_code) and old["image_url"] == target["image_url"] and image_code.lstrip("0") == target["barcode"].lstrip("0")
        created = bool(old["created_t"]) and str(old["created_t"]).replace(" ","T") == str(target["created_t"]).replace(" ","T")
        approved = october and (valid_gtin(target["barcode"]) or (name and nutrients and created) or image)
        reason = "valid_source_gtin" if valid_gtin(target["barcode"]) else "source_key_matching_name_nutrients_creation" if name and nutrients else "same_source_image"
        decisions.append(dict(source_barcode=old["barcode"],canonical_barcode=target["barcode"],decision="resolved" if approved else "retained_distinct",basis=reason if approved else "insufficient_nonstandard_identity_evidence"))
        if approved: links.append(tuple(pair))
    with (OUT/"barcode_aliases.csv").open("w",encoding="utf-8",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=["source_barcode","canonical_barcode","decision","basis"])
        writer.writeheader();writer.writerows(decisions)
    aliases.cache_clear()
    db.execute("CREATE TABLE barcode_aliases(source_barcode TEXT PRIMARY KEY, canonical_barcode TEXT NOT NULL, basis TEXT NOT NULL)")
    db.execute("CREATE TABLE identity_evidence_links(source_barcode TEXT PRIMARY KEY,canonical_barcode TEXT NOT NULL,reporting_reused INTEGER NOT NULL,reason TEXT NOT NULL)")
    before = db.execute("SELECT count(*) FROM retained_deployment_products").fetchone()[0]
    print("Applying",len(links),"aliases",flush=True)
    for s,l in links:
        old,target = [dict(db.execute("SELECT * FROM identity_source WHERE barcode=?", (code,)).fetchone()) for code in (s,l)]
        reason = "historical_zero_alias"
        db.execute("INSERT INTO barcode_aliases VALUES (?,?,?)",(s,l,reason))
        # A historical archive decision cannot be bypassed through its alias.
        if old["membership"] == "archived":
            db.execute("UPDATE population_membership SET membership='archived',decision_reason='identity_preserved_archive' WHERE barcode=?",(l,))
        db.execute("UPDATE population_membership SET membership='archived',decision_reason='identity_alias:'||? WHERE barcode=?",(l,s))
        countries = "|".join(sorted(set((old["countries"] or "").split("|")) | set((target["countries"] or "").split("|")) - {""}))
        regions = "|".join(sorted(set((old["observed_market_region_codes"] or "").split("|")) | set((target["observed_market_region_codes"] or "").split("|")) - {""}))
        db.execute("UPDATE products SET countries=?,observed_market_region_codes=? WHERE barcode=?",(countries,regions,l))
        freshness = db.execute("SELECT status FROM claim_freshness WHERE barcode=?",(s,)).fetchone()
        reuse = bool(freshness and freshness[0] == "matched_image_reference" and old["image_url"] == target["image_url"] and old["product_name"] == target["product_name"])
        if reuse:
            saved = db.execute("SELECT * FROM product_analysis WHERE barcode=?",(s,)).fetchone()
            current = db.execute("SELECT pack_claims_found FROM product_analysis WHERE barcode=?",(l,)).fetchone()
            if saved and (not current or current[0] is None):
                values = dict(saved);values["barcode"] = l
                names = list(values)
                db.execute('INSERT OR REPLACE INTO product_analysis ('+','.join(names)+') VALUES ('+','.join('?' for _ in names)+')',list(values.values()))
        db.execute("INSERT INTO identity_evidence_links VALUES (?,?,?,?)",(s,l,int(reuse),"same_versioned_image_and_name" if reuse else "preserved_source_evidence_no_automatic_transfer"))
    db.execute("DELETE FROM release_population")
    db.execute("INSERT INTO release_population SELECT barcode FROM retained_display_products")
    db.commit()
    db.close()
    governance()

def governance():
    """Resume exact governance application after the committed identity correction."""
    import pandas as pd
    from pipeline.stages import stage_02_clean_products as cleaning
    db = connect(WORK)
    reviewed_keys = set(cleaning.load_reviewed_product_mapping_overrides()) | set(loader.load_reviewed_product_mapping_overrides())
    reviewed = {code for code, in db.execute("SELECT barcode FROM products") if identity_key(code) in reviewed_keys}
    db.execute("CREATE TEMP TABLE reviewed_identities(barcode TEXT PRIMARY KEY)")
    db.executemany("INSERT INTO reviewed_identities VALUES (?)",((code,) for code in reviewed))
    print("Applying existing exact governance to",len(reviewed),"identities",flush=True)
    frame = pd.read_sql_query("SELECT p.barcode,p.product_name,p.primary_country,p.normalized_brand,p.primary_brand,p.resolved_company,p.query_category,p.observed_market_region_codes,p.countries,p.brand_entity_raw,p.brand_entity_source,p.brand_family,p.brand_alias_source,p.brand_alias_review_status,p.company_ownership_resolution_status,p.company_mapping_source FROM retained_deployment_products p JOIN reviewed_identities USING(barcode)",db)
    frame = cleaning.apply_reviewed_product_mapping_overrides(frame)
    frame = loader.add_resolved_company_column(frame)
    frame = loader.apply_reviewed_product_mapping_overrides(frame)
    fields = ["normalized_brand","primary_brand","resolved_company","query_category","brand_entity_raw","brand_entity_source","brand_family","brand_alias_source","brand_alias_review_status","company_ownership_resolution_status","company_mapping_source"]
    sql = "UPDATE products SET " + ','.join(field+'=?' for field in fields) + " WHERE barcode=?"
    db.executemany(sql, (tuple(None if pd.isna(value) else value for value in row[1:])+ (row[0],) for row in frame[["barcode"]+fields].itertuples(index=False,name=None)))
    db.execute("DELETE FROM release_population")
    db.execute("INSERT INTO release_population SELECT barcode FROM retained_display_products")
    db.commit()
    before = json.loads((ORIGINAL/"manifest.json").read_bytes())["counts"]["products"]
    after = db.execute("SELECT count(*) FROM retained_deployment_products").fetchone()[0]
    with (OUT/"barcode_aliases.csv").open(encoding="utf-8",newline="") as stream:
        decisions = Counter(row["decision"] for row in csv.DictReader(stream))
    save("correction.json",dict(before_products=before,after_products=after,alias_decisions=dict(decisions),historical_evidence_links=db.execute("SELECT count(*) FROM identity_evidence_links").fetchone()[0],reporting_evidence_reused=db.execute("SELECT sum(reporting_reused) FROM identity_evidence_links").fetchone()[0],original_database_sha256=json.loads((ROOT/"presentations/segmentation/first_run/01_ingestion/01_population/run_01/run_01_manifest.json").read_bytes())["source_database_sha256"]))
    db.close()
    print("CORRECTED",before,after,flush=True)

def reporting():
    # Embed the existing reviewed beverage exclusions for every reporting consumer.
    from shared.beverage_eligibility import blocked_keys
    from shared.release_population import reporting_regions, region_exclusions
    with connect(WORK) as db:
        db.execute("CREATE TABLE IF NOT EXISTS reporting_region_exclusions(barcode TEXT,region_code TEXT,PRIMARY KEY(barcode,region_code))")
        regions = {"FR":"FRANCE","UK+IE":"UK_IE","US+CA":"US_CANADA"}
        db.executemany("INSERT OR IGNORE INTO reporting_region_exclusions VALUES (?,?)",((resolve(code),regions[region]) for code,region in blocked_keys()))
        exclusions = region_exclusions(db)
        for code,category,regions in db.execute("SELECT p.barcode,p.query_category,p.observed_market_region_codes FROM products p JOIN release_population USING(barcode)").fetchall():
            if not set(reporting_regions(code,category,regions,exclusions).split("|")) & {"FRANCE","UK_IE","US_CANADA"}:
                db.execute("DELETE FROM release_population WHERE barcode=?",(code,))
    # Rebuild exactly the standard downstream stages, using the corrected population.
    for number in (12,13,14,15,16):
        module_path = next((ROOT/"pipeline/stages").glob(f"stage_{number}_*.py"))
        module = importlib.import_module("pipeline.stages."+module_path.stem)
        values = {"DB_PATH": WORK}
        if number == 12: values["PIPELINE_INTERMEDIATE_DIR"] = OUT
        if number == 13: values["SOURCE_SCOPE"] = "retained_display_population"
        if number in (14,15,16): values["SNAPSHOT"] = PERIOD
        if number == 16: values["AUDIT_DIR"] = OUT
        print("REBUILD",number,flush=True)
        with settings(module,**values):
            module.main(reporting_date=PERIOD) if number == 13 else module.main()
    import pandas as pd
    with connect(WORK) as db:
        frame = pd.read_sql_query("SELECT barcode,query_category,primary_country,normalized_brand,primary_brand,observed_market_region_codes,energy_kcal,protein_100g,fiber_100g,saturated_fat_100g,sugars_100g,salt_100g FROM retained_display_products WHERE barcode IN (SELECT barcode FROM release_population)",db)
        exclusions = region_exclusions(db)
        frame["observed_market_region_codes"] = [reporting_regions(code,category,regions,exclusions) for code,category,regions in zip(frame.barcode,frame.query_category,frame.observed_market_region_codes)]
        loader.compute_category_region_averages(frame,db,PERIOD)
    public = OUT/"release_public.db"
    if public.exists(): public.unlink()
    with connect(WORK) as src, connect(public) as dst:
        dst.execute("ATTACH DATABASE ? AS src",(str(WORK),))
        for table in sorted(deployment.APP_TABLES): deployment.copy_schema(src,dst,table)
        columns = ','.join(deployment.quote_ident(c) for c in deployment.PUBLIC_PRODUCT_COLUMNS)
        dst.execute(f"INSERT INTO products ({columns}) SELECT {columns} FROM src.retained_deployment_products")
        deployment.copy_product_analysis(dst)
        for table in SNAPSHOT_TABLES: dst.execute(f"INSERT INTO {table} SELECT * FROM src.{table} WHERE snapshot=?",(PERIOD,))
        for table in ("release_population","release_manifest","barcode_aliases","identity_evidence_links","reporting_region_exclusions"):
            dst.execute(f"CREATE TABLE {table} AS SELECT * FROM src.{table}")
        dst.execute("CREATE TABLE claim_freshness AS SELECT barcode,status FROM src.claim_freshness WHERE barcode IN (SELECT barcode FROM products)")
        dst.execute("ALTER TABLE products ADD COLUMN source_observed_market_region_codes TEXT")
        dst.execute("UPDATE products SET source_observed_market_region_codes=observed_market_region_codes")
        exclusions = region_exclusions(dst)
        for code,category,regions in dst.execute("SELECT barcode,query_category,observed_market_region_codes FROM products WHERE query_category='beverages'").fetchall():
            effective = reporting_regions(code,category,regions,exclusions)
            if effective != regions:
                dst.execute("UPDATE products SET observed_market_region_codes=? WHERE barcode=?",(effective,code))
        deployment.create_indexes(dst)
        dst.commit()
        assert dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with public.open('rb') as src,gzip.open(OUT/"release_public.db.gz",'wb') as dst: shutil.copyfileobj(src,dst)
    manifest = json.loads((ORIGINAL/"manifest.json").read_bytes())
    with connect(WORK) as db:
        manifest["counts"]["products"] = db.execute("SELECT count(*) FROM retained_deployment_products").fetchone()[0]
        manifest["display_count"] = db.execute("SELECT count(*) FROM release_population").fetchone()[0]
    manifest["identity_correction"] = {"original_manifest_sha256":sha256(ORIGINAL/"manifest.json"),"aliases_sha256":sha256(OUT/"barcode_aliases.csv")}
    manifest["work_sha256"] = sha256(WORK)
    manifest["public_sha256"] = sha256(public)
    manifest["gzip_sha256"] = sha256(OUT/"release_public.db.gz")
    save("manifest.json",manifest)
    print("REPORTING COMPLETE",manifest["display_count"],flush=True)

def finalize():
    """Bind the corrected manifests to effective evidence, code and artifact bytes."""
    from pipeline.maintenance.build_incremental_release import code_identity
    with connect(WORK) as db:
        db.execute("UPDATE claim_freshness SET status='matched_image_reference' WHERE barcode IN (SELECT canonical_barcode FROM identity_evidence_links WHERE reporting_reused=1)")
        freshness = dict(db.execute("SELECT f.status,count(*) FROM claim_freshness f JOIN population_membership m USING(barcode) WHERE m.membership='retained' GROUP BY f.status"))
    import pandas as pd
    from shared.release_population import reporting_regions, region_exclusions
    with connect(WORK) as db:
        frame=pd.read_sql_query("SELECT barcode,query_category,primary_country,normalized_brand,primary_brand,observed_market_region_codes,energy_kcal,protein_100g,fiber_100g,saturated_fat_100g,sugars_100g,salt_100g FROM retained_display_products WHERE barcode IN (SELECT barcode FROM release_population)",db)
        exclusions=region_exclusions(db)
        frame["observed_market_region_codes"]=[reporting_regions(code,category,regions,exclusions) for code,category,regions in zip(frame.barcode,frame.query_category,frame.observed_market_region_codes)]
        loader.compute_category_region_averages(frame,db,PERIOD)
    public=OUT/"release_public.db"
    with connect(public) as db:
        db.execute("ATTACH DATABASE ? AS corrected",(str(WORK),))
        db.execute("DELETE FROM category_region_averages")
        db.execute("INSERT INTO category_region_averages SELECT * FROM corrected.category_region_averages WHERE snapshot=?",(PERIOD,))
        db.execute("UPDATE claim_freshness SET status='matched_image_reference' WHERE barcode IN (SELECT canonical_barcode FROM identity_evidence_links WHERE reporting_reused=1)")
        counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in deployment.APP_TABLES}
        display_count=db.execute("SELECT count(*) FROM release_population").fetchone()[0]
    old=json.loads((OUT/"manifest.json").read_bytes())
    metadata={key:old[key] for key in ("status","wave_id","reporting_date","retrieved_at","source_sha256","identity_correction")}
    metadata["identity_correction"]["aliases_sha256"]=sha256(OUT/"barcode_aliases.csv")
    metadata.update(counts=counts,display_count=display_count,claim_freshness=freshness,code_sha256=code_identity(),correction=json.loads((OUT/"correction.json").read_bytes()))
    metadata["code_sha256"]["pipeline/rules/barcode_identity.py"]=sha256(ROOT/"pipeline/rules/barcode_identity.py")
    metadata["code_sha256"]["pipeline/maintenance/correct_wave2_identity.py"]=sha256(Path(__file__))
    with public.open('rb') as src,gzip.open(OUT/"release_public.db.gz",'wb') as dst:shutil.copyfileobj(src,dst)
    metadata.update(work_sha256=sha256(WORK),public_sha256=sha256(public),gzip_sha256=sha256(OUT/"release_public.db.gz"))
    save("manifest.json",metadata)
    print("FINALIZED",display_count,flush=True)

def master():
    from presentations.segmentation.production.workflow.build_master import build, WAVE2
    from presentations.segmentation.production.workflow.artifact_paths import LOCK, SEG, relocated
    import os
    destination = ROOT/"presentations/segmentation/first_run/01_ingestion/05_master_parquet/output"
    temporary = OUT/"master"
    manifest = build(WORK, OUT/"manifest.json", LOCK, temporary, WAVE2,
                     relocated(SEG/"run_03_exclusions_v1.csv"),
                     relocated(SEG/"beverage_final_v1/eligibility_decisions.csv"))
    for name in ("master_products.parquet","manifest.json"):
        os.replace(temporary/name,destination/name)
    temporary.rmdir()
    print("MASTER COMPLETE",manifest["counts"],flush=True)

def scope():
    """Remove assignments excluded in every supported region and refresh global summaries."""
    import os
    from pipeline.stages import stage_13_build_app_summaries as summary
    sql="SELECT p.barcode FROM products p JOIN release_population USING(barcode) WHERE p.observed_market_region_codes NOT LIKE '%FRANCE%' AND p.observed_market_region_codes NOT LIKE '%UK_IE%' AND p.observed_market_region_codes NOT LIKE '%US_CANADA%'"
    public=OUT/"release_public.db"
    with connect(public) as db:
        excluded=[row[0] for row in db.execute(sql)]
        db.executemany("DELETE FROM release_population WHERE barcode=?",((code,) for code in excluded))
    with connect(WORK) as db:
        db.executemany("DELETE FROM release_population WHERE barcode=?",((code,) for code in excluded))
    print("Removing",len(excluded),"fully excluded regional assignments",flush=True)
    with settings(summary,DB_PATH=WORK,SOURCE_SCOPE="retained_display_population"):
        summary.main(reporting_date=PERIOD)
    metadata=json.loads((OUT/"manifest.json").read_bytes())
    with connect(public) as db:metadata["display_count"]=db.execute("SELECT count(*) FROM release_population").fetchone()[0]
    metadata["correction"]["fully_region_excluded_products"]=len(excluded)
    with public.open('rb') as src,gzip.open(OUT/"release_public.db.gz",'wb') as dst:shutil.copyfileobj(src,dst)
    metadata.update(work_sha256=sha256(WORK),public_sha256=sha256(public),gzip_sha256=sha256(OUT/"release_public.db.gz"),work_bytes=WORK.stat().st_size,work_mtime_ns=WORK.stat().st_mtime_ns)
    from pipeline.maintenance.build_incremental_release import code_identity
    metadata["code_sha256"]=code_identity()
    metadata["code_sha256"]["pipeline/rules/barcode_identity.py"]=sha256(ROOT/"pipeline/rules/barcode_identity.py")
    metadata["code_sha256"]["pipeline/maintenance/correct_wave2_identity.py"]=sha256(Path(__file__))
    save("manifest.json",metadata)
    print("SCOPE COMPLETE",metadata["display_count"],flush=True)

def refresh():
    """Refresh the current field inventory after the preprocessing baseline reset."""
    import subprocess
    script = ROOT / "presentations/segmentation/first_run/02_shared_preprocessing_and_eda/01_preprocessing/field_use_inventory_v1.py"
    subprocess.run([sys.executable, "-B", str(script), "--replace"], check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("correct","governance","reporting","finalize","master","scope","refresh"))
    args = parser.parse_args()
    globals()[args.phase]()
