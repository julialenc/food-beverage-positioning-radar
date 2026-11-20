"""Persistent cross-wave pointers to original stage results. No provider I/O."""
import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def assignment(row):
    barcode, region, category = (row[k] for k in ("barcode", "region", "category"))
    if not all(isinstance(s, str) and s and s == s.strip() for s in (barcode, region, category)):
        raise ValueError("Assignment needs exact text barcode, region and category")
    region = {"US+CA": "US-CA", "UK+IE": "UK-IE"}.get(region, region)
    category = {"dairies": "dairy", "cereals": "cereal"}.get(category, category)
    return barcode, region, category


def identity(kind, row, method, body, source=None):
    image = row["image_sha256"]
    if len(image) != 64 or any(c not in "0123456789abcdef" for c in image):
        raise ValueError("A verified image SHA-256 is required")
    if kind == "ocr":
        # The existing runner key already binds the image, OCR options and endpoint.
        return method
    if not method or not source or not isinstance(body, dict) or not body:
        raise ValueError("LLM reuse requires exact runtime, upstream evidence and dispatched request")
    return fingerprint([kind, assignment(row), image, method, source, body])


SCHEMA = """
CREATE TABLE IF NOT EXISTS waves (
 wave TEXT PRIMARY KEY, parent TEXT REFERENCES waves, mode TEXT NOT NULL, input_sha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS members (
 wave TEXT REFERENCES waves, barcode TEXT, region TEXT, category TEXT, selected INTEGER NOT NULL,
 PRIMARY KEY(wave,barcode,region,category));
CREATE TABLE IF NOT EXISTS evidence (
 identity TEXT NOT NULL, kind TEXT NOT NULL, barcode TEXT, region TEXT, category TEXT,
 image_sha TEXT NOT NULL, config_sha TEXT NOT NULL, model TEXT, outcome TEXT NOT NULL,
 usable INTEGER NOT NULL, ledger TEXT NOT NULL, stage_key TEXT NOT NULL, payload_sha TEXT,
 PRIMARY KEY(ledger,stage_key));
CREATE INDEX IF NOT EXISTS evidence_identity ON evidence(identity,kind);
CREATE TABLE IF NOT EXISTS work_intent (
 identity TEXT PRIMARY KEY, ledger TEXT NOT NULL, stage_key TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS claim_refs (
 wave TEXT REFERENCES waves, barcode TEXT, region TEXT, category TEXT, record_id TEXT,
 outcome TEXT, eligible INTEGER, cohort TEXT, join_path TEXT, join_sha TEXT, source_ref TEXT,
 PRIMARY KEY(wave,barcode,region,category));
"""


@contextmanager
def index(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=60)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        with db:
            yield db


def readonly(path):
    return closing(sqlite3.connect(Path(path).resolve(strict=True).as_uri()+"?mode=ro", uri=True))


def additions_frame(current, previous):
    """Newly eligible assignments or explicit changes in the governed sample frame."""
    prior = {}
    for row in previous:
        key = assignment(row)
        if key in prior or type(row["eligible"]) is not bool:
            raise ValueError("Invalid previous governed population")
        prior[key] = row
    additions = set()
    for row in current:
        key = assignment(row)
        if not row["eligible"]:
            continue
        old = prior.get(key)
        if old is None or not old["eligible"] or any(
            row.get(field) and row[field] != old.get(field)
            for field in ("image_sha256","sampling_group_id","selection_revision")
        ):
            additions.add(key)
    return additions


def import_ledger(db, ledger, assessments, reviewed_keys=None):
    """Index actual dispatch identities, including failed/held work. Never infer success."""
    path = str(ledger.resolve(strict=True))
    with readonly(path) as src:
        if src.execute("""SELECT 1 FROM calls WHERE call_id NOT IN
                       (SELECT key FROM stage_events WHERE event='dispatch') LIMIT 1""").fetchone():
            raise ValueError("Unresolved reservation lacks dispatch identity; reconcile before indexing this ledger")
        texts = {}
        for saved, in src.execute("SELECT payload FROM stage_results WHERE kind='ocr' AND status='success'"):
            ocr = json.loads(saved)
            if ocr.get("image_sha256") and ocr.get("text"):
                texts.setdefault(ocr["image_sha256"],set()).add(hashlib.sha256(ocr["text"].encode()).hexdigest())
        query = """SELECT e.key,c.kind,e.payload,s.status,s.payload FROM stage_events e
                   JOIN calls c ON c.call_id=e.key LEFT JOIN stage_results s ON s.key=e.key
                   WHERE e.event='dispatch' ORDER BY e.id"""
        for key, kind, dispatch, state, payload in src.execute(query):
            event = json.loads(dispatch)
            row, method, body = event["row"], event["configuration_sha256"], event["body"]
            unit = assignment(row)
            quality = assessments.get(unit)
            usable = bool(state and state.startswith("success") and payload and quality
                          and (kind == "ocr" or quality["analytical_eligible"] and
                               (quality["v6_usable"] if kind == "emerging_benefits"
                                else quality["original_overall_outcome"] == "PASS")))
            if reviewed_keys is not None and kind != "ocr" and key not in reviewed_keys:
                usable = False
            if kind == "ocr" and usable:
                result = json.loads(payload)
                usable = bool(result.get("text", "").strip() and result.get("image_sha256") == row["image_sha256"])
            sources = texts.get(row["image_sha256"],set())
            # Re-extraction also depends on the prior context review. Its native
            # stage key commits to that complete upstream result.
            source = key if kind=="dairy_reextract" else next(iter(sources)) if len(sources)==1 else None
            if kind!="ocr" and not source:
                usable = False
                source = "unverified:"+key
            lookup = identity(kind, row, key if kind == "ocr" else method, body, source)
            record = (lookup, kind, *unit, row["image_sha256"], method, (body or {}).get("model"),
                      state or "pending_or_failed", int(usable), path, key,
                      hashlib.sha256(payload.encode()).hexdigest() if payload else None)
            db.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", record)


def lookup(db, kind, row, method, body=None, source=None):
    key = identity(kind, row, method, body, source)
    entries = db.execute("SELECT * FROM evidence WHERE identity=? AND kind=? ORDER BY ledger,stage_key",
                         (key, kind)).fetchall()
    if not entries:
        return "process", None
    if not all(e["usable"] for e in entries) or len({e["payload_sha"] for e in entries}) != 1:
        return "hold", None
    e = entries[0]
    with readonly(e["ledger"]) as ledger:
        saved = ledger.execute("SELECT status,payload FROM stage_results WHERE key=? AND kind=?",
                               (e["stage_key"], kind)).fetchone()
    if not saved or saved[0] != e["outcome"] or hashlib.sha256(saved[1].encode()).hexdigest() != e["payload_sha"]:
        raise ValueError("Indexed evidence changed: " + e["stage_key"])
    return "reuse", (e, json.loads(saved[1]))


def membership(db, wave, parent, mode, population, drawn):
    """Plan from a complete governed snapshot and approved draw/additions, atomically."""
    if mode not in ("full", "incremental") or (mode == "incremental" and not parent) or wave == parent:
        raise ValueError("Invalid wave mode or parent")
    current = {}
    for row in population:
        key = assignment(row)
        if key in current or type(row["eligible"]) is not bool:
            raise ValueError("Duplicate assignment or non-boolean eligibility")
        current[key] = row["eligible"]
    picked = [assignment(r) for r in drawn]
    if len(set(picked)) != len(picked) or any(not current.get(k) for k in picked):
        raise ValueError("Draw contains duplicate, absent or ineligible assignment")
    if parent and not db.execute("SELECT 1 FROM waves WHERE wave=?", (parent,)).fetchone():
        raise ValueError("Unknown parent wave")
    prior = {tuple(r) for r in db.execute(
        "SELECT barcode,region,category FROM members WHERE wave=? AND selected=1", (parent,))}
    eligible = {k for k,v in current.items() if v}
    selected = set(picked)
    if mode == "incremental":
        selected |= prior & eligible
    stamp = fingerprint([mode, sorted(population,key=assignment), sorted(drawn,key=assignment)])
    existing = db.execute("SELECT parent,mode,input_sha FROM waves WHERE wave=?", (wave,)).fetchone()
    if existing and tuple(existing) != (parent, mode, stamp):
        raise ValueError("Frozen wave identity reused with changed inputs")
    if not existing:
        db.execute("INSERT INTO waves VALUES (?,?,?,?)", (wave, parent, mode, stamp))
        db.executemany("INSERT INTO members VALUES (?,?,?,?,?)",
                       ((wave,*k,int(k in selected)) for k in sorted(current)))
    return {"selected": sorted(selected), "added": sorted(selected-prior),
            "removed": sorted(k for k in prior if k not in current),
            "ineligible": sorted((prior & current.keys())-eligible),
            "sampled_out": sorted((prior & eligible)-selected)}
