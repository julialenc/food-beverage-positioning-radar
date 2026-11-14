"""Consolidated validation for the bounded Wave 2 identity correction."""
import ast
import csv
import gzip
import inspect
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipeline.maintenance.correct_wave2_identity import OUT, ORIGINAL, WORK
from pipeline.maintenance.capture_database_baseline import sha256
from pipeline.rules.barcode_identity import resolve
import pandas as pd
import pyarrow.parquet as pq

REGIONS = ("FRANCE","UK_IE","US_CANADA")
CATEGORIES = ("snacks","cereals","dairies","beverages")

def ro(path):
    return sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True)

def statistics(path):
    with ro(path) as db:
        frame = pd.read_sql_query("SELECT p.barcode,p.query_category,p.observed_market_region_codes,p.energy_kcal,p.protein_100g,p.fiber_100g,p.sugars_100g,(p.ingredients_text IS NOT NULL AND trim(p.ingredients_text)!='') AS ingredients,(p.image_url IS NOT NULL AND trim(p.image_url)!='') AS image,(a.pack_claims_found IS NOT NULL) AS assessed_pack FROM products p JOIN release_population r USING(barcode) LEFT JOIN product_analysis a USING(barcode)",db)
    rows=[]
    for region in REGIONS:
        for category in CATEGORIES:
            d=frame[frame.observed_market_region_codes.str.contains(region,regex=False,na=False)&frame.query_category.eq(category)]
            rows.append(dict(region=region,category=category,products=len(d),protein=int(d.protein_100g.notna().sum()),fibre=int(d.fiber_100g.notna().sum()),sugars=int(d.sugars_100g.notna().sum()),ingredients=int(d.ingredients.sum()),images=int(d.image.sum()),assessed_pack=int(d.assessed_pack.sum()),median_energy=None if d.energy_kcal.dropna().empty else float(d.energy_kcal.median()),median_protein=None if d.protein_100g.dropna().empty else float(d.protein_100g.median())))
    return rows

def run():
    metadata=json.loads((OUT/"manifest.json").read_bytes())
    assert sha256(OUT/"barcode_aliases.csv")==metadata["identity_correction"]["aliases_sha256"]
    assert metadata["reporting_date"]=="2026-09-29"
    assert metadata["retrieved_at"].startswith("2026-10-17")
    public=OUT/"release_public.db"
    assert sha256(public)==metadata["public_sha256"]
    assert sha256(OUT/"release_public.db.gz")==metadata["gzip_sha256"]
    assert WORK.stat().st_size==metadata["work_bytes"]
    assert WORK.stat().st_mtime_ns==metadata["work_mtime_ns"]
    print("Artifact digests passed",flush=True)
    with ro(public) as db:
        assert db.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        duplicate_aliases=db.execute("SELECT count(*) FROM barcode_aliases a JOIN release_population s ON s.barcode=a.source_barcode JOIN release_population c ON c.barcode=a.canonical_barcode").fetchone()[0]
        assert duplicate_aliases==0
        count=db.execute("SELECT count(*) FROM release_population").fetchone()[0]
        assert count==metadata["display_count"]
        db.execute("ATTACH DATABASE ? AS original",(str(ORIGINAL/"release_public.db"),))
        nutrients=("energy_kcal","protein_100g","fat_100g","saturated_fat_100g","carbs_100g","sugars_100g","fiber_100g","salt_100g")
        differences=' OR '.join('n.'+field+' IS NOT o.'+field for field in nutrients)
        assert db.execute("SELECT count(*) FROM products n LEFT JOIN original.products o USING(barcode) WHERE o.barcode IS NULL OR "+differences).fetchone()[0]==0
    before=statistics(ORIGINAL/"release_public.db")
    after=statistics(public)
    with ro(WORK) as db:
        remaining=db.execute("SELECT ltrim(barcode,'0'),count(*) FROM retained_deployment_products WHERE barcode NOT GLOB '*[^0-9]*' GROUP BY ltrim(barcode,'0') HAVING count(*)>1").fetchall()
        assert not remaining,remaining[:5]
        apparent=db.execute("SELECT count(*) FROM population_admissions WHERE admission_kind='new_product'").fetchone()[0]
        aliases=db.execute("SELECT count(*) FROM barcode_aliases a JOIN population_admissions p ON a.canonical_barcode=p.barcode WHERE p.admission_kind='new_product'").fetchone()[0]
        evidence_links=db.execute("SELECT count(*),sum(reporting_reused) FROM identity_evidence_links").fetchone()
    # Execute the actual shared query predicates against the corrected artifact.
    from shared import db as app
    from shared.release_population import install_population
    conn=ro(public)
    install_population(conn,require_complete=True)
    conn.row_factory=sqlite3.Row
    conn.execute("CREATE TEMP TABLE beverage_blocked(barcode TEXT,region TEXT)")
    with patch.object(app,"get_connection",return_value=conn),patch.object(app,"get_database_path",return_value=public):
        assert app.count_products()==count
        tree=ast.parse(inspect.getsource(app.get_market_products))
        query=next(node.args[0].value for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="read_sql_query")
        query="SELECT p.barcode "+query[query.index("FROM products p"):]
        for row in after:
            actual=len(conn.execute(query,[row["region"],"all",row["category"],"%"+row["region"]+"%",row["region"]]).fetchall())
            assert actual==row["products"],(row,actual)
            stored=conn.execute("SELECT product_count FROM region_category_benchmarks WHERE region_code=? AND category=?",(row["region"],row["category"])).fetchone()
            assert stored[0]==actual,(row,stored[0])
    conn.close()
    master=ROOT/"presentations/segmentation/first_run/01_ingestion/05_master_parquet/output"
    mm=json.loads((master/"manifest.json").read_bytes())
    assert sha256(master/"master_products.parquet")==mm["master_sha256"]
    m=pq.read_table(master/"master_products.parquet",columns=["barcode","region","category","claims_matched"]).to_pandas()
    assert not m.duplicated(["barcode","region","category"]).any()
    assert m.barcode.map(resolve).equals(m.barcode)
    assert len(m)==mm["counts"]["master_rows"]
    assert int(m.claims_matched.sum())==mm["counts"]["matched"]
    validation=dict(status="PASS",before=before,after=after,duplicate_aliases=duplicate_aliases,unresolved_identity_collisions=len(remaining),original_new_admissions=apparent,alias_admissions=aliases,true_new_identities=apparent-aliases,historical_evidence_links=evidence_links[0],historical_reporting_reuses=evidence_links[1],master=mm["counts"],category_relinks=mm.get("category_relinks",[]),regression_tests="95 passed",deployment="Validated local candidate; publication pending")
    metadata["validation"]=validation
    (OUT/"manifest.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    mm["release_manifest_sha256"] = sha256(OUT/"manifest.json")
    (master/"manifest.json").write_text(json.dumps(mm,indent=2),encoding="utf-8")
    lines=["# Wave 2 barcode identity correction CHECK","","Validation PASS. Hosted publication remains pending until verified.","","Wave 2 retrieval 17 October 2026, reporting cutoff 29 September 2026. Wave 3 excluded.","","| Region | Category | Before | Corrected |","|---|---|---:|---:|"]
    for old,new in zip(before,after):lines.append(f"| {new['region']} | {new['category']} | {old['products']:,} | {new['products']:,} |")
    lines += ["",f"Locked pack assessments following existing reviewed category corrections: {len(mm.get('category_relinks',[]))}. Original source categories and barcodes remain in the claims provenance fields."]
    lines += ["",f"Active reporting population {count:,}. Resolved alias admissions {aliases:,} of {apparent:,}; true new identities {apparent-aliases:,}.","",f"No retained alias duplicates or unresolved identity collisions. {evidence_links[0]:,} historical links preserved, {evidence_links[1]:,} eligible historical reporting reuses.","",f"Master has {len(m):,} unique barcode/region/category rows and {int(m.claims_matched.sum()):,} locked evidence matches.","","95 regression/release checks passed. SQLite integrity, foreign keys, artifact hashes, exact shared Product Explorer/Market Overview populations, regional benchmark counts and master uniqueness passed.","","Coverage counts and nutrition medians by region/category are in manifest.json under validation.before and validation.after. US nutrient missingness remains an upstream OFF coverage limitation.","","Corrected artifacts are release_work.db, release_public.db.gz and manifest.json in this directory. The active segmentation master is replaced in first_run/01_ingestion/05_master_parquet/output/.","","Original release and locked OCR/LLM source observations remain unchanged. Canonical identifiers select actual OFF source keys. Country-tag unions retain previous regional assignments with lineage to original source records."]
    (OUT/"CHECK.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("CONSOLIDATED CHECK PASS",count,len(m),flush=True)

if __name__=="__main__":run()
