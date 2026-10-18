"""Explicit population membership, independent of load time and display gates.

This module is not yet wired into production stages or Streamlit. It adds
metadata and views only; it never changes product/source values or quality
flags. Ingestion must preflight membership before writing products, then record
the accepted batch in the same transaction. Source-version ordering, ingestion
completeness and claim freshness remain responsibilities of the future loader.
"""

from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import sqlite3


POLICY_VERSION = "retained_population_v1"
OBJECTS = (
    "population_policy", "population_membership", "population_admissions",
    "retained_products", "retained_deployment_products", "retained_display_products",
)
DDL = (
    """CREATE TABLE population_policy (
        id INTEGER PRIMARY KEY CHECK(id=1), policy_version TEXT NOT NULL,
        baseline_id TEXT NOT NULL, baseline_sha256 TEXT NOT NULL,
        seed_ingested_at TEXT NOT NULL, approved_retained_count INTEGER NOT NULL,
        approved_archived_count INTEGER NOT NULL, off_capture_date TEXT NOT NULL,
        proxy_wave_2_cutoff TEXT NOT NULL, date_basis TEXT NOT NULL,
        encoded_at_utc TEXT NOT NULL
    )""",
    """CREATE TABLE population_membership (
        barcode TEXT PRIMARY KEY REFERENCES products(barcode),
        membership TEXT NOT NULL CHECK(membership IN ('retained','archived')),
        seed_ingested_at TEXT, first_retained_batch TEXT,
        last_accepted_batch TEXT, decision_reason TEXT NOT NULL
    )""",
    """CREATE TABLE population_admissions (
        batch_id TEXT NOT NULL, barcode TEXT NOT NULL REFERENCES products(barcode),
        admission_kind TEXT NOT NULL, review_reference TEXT,
        PRIMARY KEY(batch_id, barcode)
    )""",
    """CREATE VIEW retained_products AS
        SELECT p.* FROM products p JOIN population_membership m USING(barcode)
        WHERE m.membership='retained'""",
    """CREATE VIEW retained_deployment_products AS
        SELECT * FROM retained_products
        WHERE query_category IN ('snacks','cereals','dairies','beverages')
        AND (observed_market_region_codes LIKE '%FRANCE%'
             OR observed_market_region_codes LIKE '%UK_IE%'
             OR observed_market_region_codes LIKE '%US_CANADA%')""",
    """CREATE VIEW retained_display_products AS
        SELECT * FROM retained_deployment_products
        WHERE COALESCE(include_in_product_table,1)=1
          AND COALESCE(NULLIF(TRIM(normalized_brand),''),primary_brand) IS NOT NULL
          AND TRIM(LOWER(COALESCE(NULLIF(TRIM(normalized_brand),''),primary_brand)))
              NOT IN ('unknown','','nan')""",
)


@contextmanager
def atomic(conn: sqlite3.Connection):
    # A SAVEPOINT also composes with a caller-owned transaction.
    conn.execute("SAVEPOINT population_change")
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK TO population_change")
        conn.execute("RELEASE population_change")
        raise
    else:
        conn.execute("RELEASE population_change")


def barcode_digest(conn, sql, params=()):
    digest = hashlib.sha256()
    count = 0
    for (barcode,) in conn.execute(sql, params):
        digest.update((json.dumps(barcode, ensure_ascii=False) + "\n").encode())
        count += 1
    return {"count": count, "sorted_barcodes_sha256": digest.hexdigest()}


def initialize(conn, *, baseline_id, baseline_sha256, seed_ingested_at,
               expected_retained, expected_archived, expected_retained_digest,
               off_capture_date, proxy_wave_2_cutoff):
    """Seed the explicitly approved group; refuse drift or reinitialization."""
    for value in (off_capture_date, proxy_wave_2_cutoff):
        date.fromisoformat(value)
    with atomic(conn):
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        if existing.intersection(OBJECTS):
            raise ValueError("Population objects already exist; refusing to reseed")
        seed = barcode_digest(conn, "SELECT barcode FROM products WHERE ingested_at=? ORDER BY barcode",
                              (seed_ingested_at,))
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if seed != {"count": expected_retained, "sorted_barcodes_sha256": expected_retained_digest}:
            raise ValueError("Approved baseline membership does not match database")
        if total - seed["count"] != expected_archived:
            raise ValueError("Archived population differs from approved baseline")
        for sql in DDL:
            conn.execute(sql)
        conn.execute("INSERT INTO population_policy VALUES (1,?,?,?,?,?,?,?,?,?,?)", (
            POLICY_VERSION, baseline_id, baseline_sha256, seed_ingested_at,
            expected_retained, expected_archived, off_capture_date, proxy_wave_2_cutoff,
            "OFF date and proxy cutoff are owner-approved; cutoff is metadata only, not a filter",
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.execute("""
            INSERT INTO population_membership
            SELECT barcode, CASE WHEN ingested_at=? THEN 'retained' ELSE 'archived' END,
                   ingested_at,
                   CASE WHEN ingested_at=? THEN ? ELSE NULL END,
                   CASE WHEN ingested_at=? THEN ? ELSE NULL END,
                   CASE WHEN ingested_at=? THEN 'approved_baseline'
                        ELSE 'older_or_undated_not_automatically_reactivated' END
            FROM products
        """, (seed_ingested_at, seed_ingested_at, baseline_id,
              seed_ingested_at, baseline_id, seed_ingested_at))
    return counts(conn)


def _barcodes(values):
    values = list(values)
    if any(not isinstance(b, str) or not b or b != b.strip() for b in values):
        raise ValueError("Barcodes must be nonempty strings with no padding")
    if len(values) != len(set(values)):
        raise ValueError("Duplicate barcode in processed batch")
    return values


def preflight_batch(conn, barcodes, reviewed_reentries=None):
    """Reject unreviewed archived re-entry BEFORE product upserts occur.

Unknown barcodes are allowed here: a future loader must independently validate
source evidence and scope. reviewed_reentries maps archived barcodes to review
references; merely appearing in an incremental download is not authorization.
"""
    barcodes = _barcodes(barcodes)
    reviewed = reviewed_reentries or {}
    if not set(reviewed).issubset(barcodes):
        raise ValueError("Re-entry approvals must refer to this batch")
    for barcode in barcodes:
        row = conn.execute("SELECT membership FROM population_membership WHERE barcode=?",
                           (barcode,)).fetchone()
        if row and row[0] == "archived":
            reference = reviewed.get(barcode)
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError(f"Archived barcode requires explicit review: {barcode}")
        elif barcode in reviewed:
            # Allows replay of an explicitly approved re-entry only if recorded.
            prior = conn.execute("SELECT 1 FROM population_admissions WHERE barcode=? "
                                 "AND admission_kind='reviewed_reentry' AND review_reference=?",
                                 (barcode, reviewed[barcode])).fetchone()
            if not prior:
                raise ValueError("Re-entry reference supplied for a non-archived barcode")
    return barcodes


def record_accepted_batch(conn, barcodes, *, batch_id, reviewed_reentries=None):
    """Register membership AFTER validated product upserts; no product writes.

Call preflight_batch before upserts. Future integration must place both product
writes and this registration within one transaction. Batch absence never retires
a member; display flags never affect admission. Repeated registration is safe.
"""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("A nonempty batch identifier is required")
    reviewed = reviewed_reentries or {}
    with atomic(conn):
        barcodes = preflight_batch(conn, barcodes, reviewed)
        for barcode in barcodes:
            if not conn.execute("SELECT 1 FROM products WHERE barcode=?", (barcode,)).fetchone():
                raise ValueError(f"No processed product row for {barcode}")
        for barcode in barcodes:
            row = conn.execute("SELECT membership FROM population_membership WHERE barcode=?",
                               (barcode,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO population_membership VALUES (?, 'retained', NULL, ?, ?, ?)",
                             (barcode, batch_id, batch_id, "accepted_new_product"))
                kind = "new_product"
            elif row[0] == "archived":
                conn.execute("UPDATE population_membership SET membership='retained', "
                             "first_retained_batch=?, last_accepted_batch=?, decision_reason=? WHERE barcode=?",
                             (batch_id, batch_id, "reviewed_reentry", barcode))
                kind = "reviewed_reentry"
            else:
                conn.execute("UPDATE population_membership SET last_accepted_batch=? WHERE barcode=?",
                             (batch_id, barcode))
                kind = "retained_update"
            conn.execute("INSERT OR IGNORE INTO population_admissions VALUES (?,?,?,?)",
                         (batch_id, barcode, kind, reviewed.get(barcode)))
    return counts(conn)


def counts(conn):
    return {
        "all_products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "retained": conn.execute("SELECT COUNT(*) FROM retained_products").fetchone()[0],
        "archived": conn.execute("SELECT COUNT(*) FROM population_membership WHERE membership='archived'").fetchone()[0],
        "deployment_scope": conn.execute("SELECT COUNT(*) FROM retained_deployment_products").fetchone()[0],
        "display_eligible": conn.execute("SELECT COUNT(*) FROM retained_display_products").fetchone()[0],
        "unregistered_products": conn.execute("SELECT COUNT(*) FROM products p LEFT JOIN "
            "population_membership m USING(barcode) WHERE m.barcode IS NULL").fetchone()[0],
    }
