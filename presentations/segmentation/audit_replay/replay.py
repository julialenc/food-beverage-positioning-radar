"""Offline replay of accepted Wave 2 research; never writes the source repository.

Controller exports Git HEAD and restores explicitly hashed local inputs. Workers
run unchanged published source with network/provider/subprocess guards. Historical
reports are reference inputs; regenerated reports are retained separately.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.parse

STUDY = Path("presentations/segmentation/first_run")
PKG = STUDY / "04_analytical_package"
EDA = STUDY / "02_shared_preprocessing_and_eda/02_eda"
BASE = EDA / "00_shared_baseline_and_feature_diagnostics"
CEREAL = EDA / "01_nutritional_composition"
L = STUDY / "03_lenses"
L1 = L / "01_nutritional_composition"
L2 = L / "02_nutrient_density"
L3 = L / "03_claims_composition_and_ingredients"
L4 = L / "04_positioning_tradeoffs"
L5 = L / "05_unsupervised_control"
SHARED = L / "00_shared_research"
HUMAN_ORIGINAL = "002a1df55b94f778ab300bfd375836bdc98f16f2a879a62ce8f1730ca410ce0d"
HUMAN_FROZEN = "df98236abe148b916fe44175625d6880ffb3b8756fd3d5d01fa3ac233eee97eb"
HUMAN_RESULT = "debc7a3296a112dceb7dac49e0dee2fd2afd4addd1819ee5b7ab0c034295b9cf"


def longpath(path):
    path = Path(path).resolve()
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path))
    return path


def canonical(path):
    value = str(Path(path).resolve())
    return Path(value[4:] if value.startswith("\\\\?\\") else value)


def sha(p):
    with Path(p).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recover_human(source):
    """Recover exact historical bytes from preserved fields; do not infer GTINs."""
    frozen = source / L3 / "human_claim_decisions_v1.csv"
    sidecar = source / L3 / "human_claim_adjudications_v1.csv"
    assert sha(frozen) == HUMAN_FROZEN and sha(sidecar) == HUMAN_RESULT
    with frozen.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    with sidecar.open(encoding="utf-8-sig", newline="") as stream:
        accepted = {r["review_id"]: r for r in csv.DictReader(stream)}
    mapping = dict(barcode="barcode_recorded", human_reviewer="reviewer",
                   human_review_date="review_date_recorded", human_claim_state="human_claim_state_recorded",
                   human_exact_wording="human_exact_wording_recorded",
                   human_other_wording="human_other_wording_recorded", human_notes="human_notes_recorded",
                   human_image_used="image_url")
    differences = []
    for row in rows:
        original = accepted[row["review_id"]]
        for key, field in mapping.items():
            if row[key] != original[field]:
                differences.append(dict(review_id=row["review_id"], field=key,
                                        frozen=row[key], original=original[field]))
            row[key] = original[field]
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = b"\xef\xbb\xbf" + text.getvalue().encode("utf8")
    assert hashlib.sha256(raw).hexdigest() == HUMAN_ORIGINAL
    assert sum(d["field"] == "barcode" for d in differences) == 7
    assert sum(d["field"] == "human_review_date" for d in differences) == 11
    return raw, differences


STAGES = [
    ("environment", None, []),
    ("master", STUDY / "01_ingestion/05_master_parquet/build.py", []),
    ("inventory", STUDY / "02_shared_preprocessing_and_eda/01_preprocessing/field_use_inventory_v1.py", []),
    ("cereal", CEREAL / "lens1_cereal_master_v1.py", [CEREAL / "lens1_cereal_master_v1.parquet"]),
    ("baseline", BASE / "h2_four_category_baseline_v1.py", [BASE / n for n in ["subtype_assignments.csv", "nutrient_availability.csv", "nutrient_distributions.csv"]]),
    ("features", BASE / "shared_feature_diagnostics_v1.py", [BASE / "FEATURE_DECISIONS.csv"]),
    ("ingredients", L3 / "ingredient_validation_v1.py", [L3 / "ingredient_validation_v1.csv"]),
    ("hypotheses", SHARED / "hypothesis_run_v1.py", [p / "hypothesis_results_v1.csv" for p in [L1, L2, L3, L4]]),
    ("control", L5 / "control_comparison_v1.py", [L5 / "control_assignments_v1.parquet", L5 / "control_comparison_v1.csv"]),
    ("cereal_followup", L1 / "cereal_formulations_v1.py", []),
    ("snacks", L1 / "savoury_snacks_v1.py", [L1 / "savoury_snack_assignments_v1.parquet"]),
    ("beverages", L1 / "beverages_v1.py", [L1 / "beverage_assignments_v1.parquet"]),
    ("juice", L1 / "juice_formulations_v1.py", [L1 / "juice_assignments_v1.parquet"]),
    ("dairy", L2 / "dairy_dessert_formulations_v1.py", []),
    ("biscuits", L1 / "biscuits_and_wafers_v1.py", []),
    ("human", L3 / "use_human_review_v1.py", [L3 / "human_claim_adjudications_v1.csv"]),
    ("synthesis", SHARED / "formulation_synthesis_v1.py", [L / "FORMULATION_DECISIONS_v1.csv"]),
    ("coverage", L3 / "communication_coverage_v1.py", [L3 / "communication_coverage_v1.csv"]),
    ("overlays", L3 / "communication_overlays_v1.py", [L3 / "communication_overlays_v1.csv"]),
    ("backlog", None, [L3 / "post_v1_evidence_gaps_v1.csv"]),
    ("processing", L4 / "processing_boundaries_v1.py", [L4 / "organic_nova_v1.csv", L4 / "category_boundaries_v1.csv", L4 / "processing_boundary_evidence_v1.parquet"]),
    ("juice_sensitivity", L1 / "juice_confidence_sensitivity_v1.py", [L1 / "juice_confidence_sensitivity_v1.csv"]),
    ("research_validation", SHARED / "validate_run_v1.py", []),
    ("report_tables", None, []),
    ("package", None, []),
]


def prepare(source, home):
    assert not home.exists(), "Use a new replay directory; existing results are never overwritten"
    assert shutil.disk_usage(source).free > 11 * 1024**3, "Need at least 11 GiB free"
    home.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    clone, refs = home / "checkout", home / "references"
    clone.mkdir(); refs.mkdir()
    with (home / "source.tar").open("wb") as stream:
        subprocess.run(["git", "archive", commit, "presentations/segmentation", "pipeline", "shared",
                        "data/01_reference_inputs", "requirements.txt", ".gitattributes"], cwd=source, stdout=stream, check=True)
    with tarfile.open(home / "source.tar") as archive:
        archive.extractall(clone, filter="data")
    tree = {}
    for line in subprocess.check_output(["git", "ls-tree", "-r", commit], cwd=source, text=True).splitlines():
        head, path = line.split("\t", 1)
        if head.split()[1] == "blob": tree[path] = head.split()[2]
    package = json.loads((source / PKG / "output/manifest_v1.json").read_bytes())
    research = json.loads((source / SHARED / "run_manifest_v1.json").read_bytes())
    required = {x["path"] for name in ["inputs", "evidence_references", "validation_references"] for x in package[name].values()}
    required.update((STUDY / p).as_posix() for p in research["sha256"])
    required.update(p.relative_to(source).as_posix() for p in (source / PKG).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    required.update((BASE / n).as_posix() for n in ["FEATURE_DECISIONS.csv", "nutrient_distributions.csv"])
    required.update("data/06_brand_governance_outputs/wave2_identity_fix_v1/" + n for n in ["release_work.db", "manifest.json", "barcode_aliases.csv"])
    required.add((L3 / "human_claim_review_v1.csv").as_posix())
    originals = {}
    for rel in sorted(required):
        original = source / rel
        assert original.is_file(), rel
        originals[rel] = sha(original)
        reference = refs / rel
        reference.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, reference)
        destination = clone / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists(): shutil.copyfile(original, destination)
        else:
            actual = destination.read_bytes()
            expected = original.read_bytes()
            assert actual == expected or actual.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), rel
            # Preserve exact bytes for hashed original sources (Git checkout conversions).
            if actual != expected: shutil.copyfile(original, destination)
    provenance = home / "human_source_versions"
    provenance.mkdir()
    raw, differences = recover_human(source)
    archived_original = source / "presentations/segmentation/audit_replay/human_source_versions/original_submission.csv"
    if archived_original.exists():
        # Once recovered, the preserved original is an explicit starting input.
        # Reconciliation against preserved fields remains an independent check.
        archived_bytes = archived_original.read_bytes()
        assert hashlib.sha256(archived_bytes).hexdigest() == HUMAN_ORIGINAL and archived_bytes == raw
        raw = archived_bytes
        originals[archived_original.relative_to(source).as_posix()] = HUMAN_ORIGINAL
    (provenance / "original_submission.csv").write_bytes(raw)
    shutil.copyfile(source / L3 / "human_claim_decisions_v1.csv", provenance / "frozen_submission.csv")
    save(provenance / "provenance.json", dict(original_sha256=HUMAN_ORIGINAL, frozen_sha256=HUMAN_FROZEN,
         accepted_sidecar_sha256=HUMAN_RESULT, recovery="Exact reconstruction from preserved sidecar fields, verified against historical source hash; not a new human submission", differences=differences))
    config = dict(source=str(source), home=str(home), commit=commit, original_hashes=originals,
                  published_tree=tree, runner_sha256=sha(Path(__file__)), comparisons="Exact hashes preferred; tabular fallback rtol=1e-8, atol=1e-11; strings, keys and missing states preserved")
    save(home / "config.json", config)
    shutil.copyfile(__file__, home / "replay.py")
    print("PREPARED", len(originals), "hash-pinned originals", flush=True)


def candidate_source(candidate, manifest):
    return candidate.parents[3] if manifest.get("layout") == "repository" else candidate / "source"


def candidate_file(candidate, manifest, relative):
    part = Path(relative)
    assert not part.is_absolute() and ".." not in part.parts, relative
    if relative.startswith("source/"):
        return candidate_source(candidate, manifest) / relative[7:]
    return candidate / relative


def verify_candidate_files(candidate, manifest):
    for relative, expected in manifest["files"].items():
        path = candidate_file(candidate, manifest, relative)
        if sha(path) != expected:
            # Ordinary legacy text may follow core.autocrlf. Fixed evidence and
            # new audit assets have no fallback and are protected with -text.
            normalized = manifest.get("normalized_text_sha256", {}).get(relative)
            assert normalized and hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == normalized, "Candidate file mismatch: " + relative
    print("CANDIDATE_FILE_HASHES_PASS", len(manifest["files"]), flush=True)


def verify_candidate(candidate, home):
    import gzip
    assert not home.exists(), "Use a new verification destination"
    manifest = json.loads((candidate / "manifest.json").read_bytes())
    verify_candidate_files(candidate, manifest)
    home.mkdir(parents=True)
    for item in manifest["inputs"]:
        if "parts" not in item:
            assert sha(candidate_source(candidate, manifest) / item["path"]) == item["sha256"], item["path"]
            continue
        compressed = home / "verify.gz"
        with compressed.open("wb") as output:
            for part in item["parts"]:
                path = candidate_file(candidate, manifest, part["path"])
                assert sha(path) == part["sha256"]
                with path.open("rb") as incoming: shutil.copyfileobj(incoming, output)
        with gzip.open(compressed, "rb") as restored:
            assert hashlib.file_digest(restored, "sha256").hexdigest() == item["sha256"]
        compressed.unlink()
    save(home / "verification.json", dict(status="PASS", files=len(manifest["files"]), inputs=len(manifest["inputs"]), manifest_sha256=sha(candidate/"manifest.json")))
    print("RELEASE_LAYOUT_AND_RESTORATION_PASS", flush=True)
    return 0


def prepare_candidate(candidate, home):
    """Prepare exclusively from the distributable candidate, without Git."""
    import gzip
    assert not home.exists(), "Use a new isolated destination"
    manifest = json.loads((candidate / "manifest.json").read_bytes())
    verify_candidate_files(candidate, manifest)
    home.mkdir(parents=True)
    source = home / "starting_inputs"
    source.mkdir()
    for relative in manifest["files"]:
        if not relative.startswith("source/"): continue
        target = source / relative[7:]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate_file(candidate, manifest, relative), target)
    for item in manifest["inputs"]:
        destination = source / item["path"]
        if "parts" in item:
            print("RESTORING", item["path"], flush=True)
            compressed = home / "restore.gz"
            with compressed.open("wb") as output:
                for part in item["parts"]:
                    assert sha(candidate_file(candidate, manifest, part["path"])) == part["sha256"]
                    with candidate_file(candidate, manifest, part["path"]).open("rb") as incoming:
                        shutil.copyfileobj(incoming, output)
            with gzip.open(compressed, "rb") as incoming, destination.open("wb") as output:
                shutil.copyfileobj(incoming, output)
            compressed.unlink()
        assert sha(destination) == item["sha256"], item["path"]
    print("STARTING_INPUT_HASHES_PASS", len(manifest["inputs"]), flush=True)
    clone, refs = home / "checkout", home / "references"
    shutil.copytree(source, clone)
    print("ISOLATED_CHECKOUT_COPIED", flush=True)
    refs.mkdir()
    # The large database is a starting input, never an output-comparison reference.
    for item in manifest["inputs"]:
        if "parts" not in item:
            target = refs / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / item["path"], target)
    shutil.copytree(source / "presentations/segmentation/audit_replay/human_source_versions", home / "human_source_versions")
    config = dict(source=str(source), home=str(home), commit=manifest["commit"],
                  original_hashes={x["path"]: x["sha256"] for x in manifest["inputs"]},
                  published_tree=manifest["published_tree"], runner_sha256=sha(Path(__file__)),
                  isolation_forbidden_root=str(candidate_source(candidate, manifest) if manifest.get("layout") == "repository" else candidate.parent.parent),
                  candidate_sha256=sha(candidate / "manifest.json"))
    save(home / "config.json", config)
    shutil.copyfile(__file__, home / "replay.py")
    print("PREPARED_FROM_CANDIDATE", len(config["original_hashes"]), "inputs; no Git or prior replay", flush=True)


def worker(home, stage):
    worker_runner_sha256 = sha(Path(__file__))
    config = json.loads((home / "config.json").read_bytes())
    source, clone, refs = Path(config["source"]), home / "checkout", home / "references"
    os.chdir(clone); sys.path.insert(0, str(clone))
    if os.name == "nt":
        # Extended Win32 paths are for filesystem calls, not URI authorities.
        # Keep published SQLite read-only URI code unchanged; adapt only the
        # platform representation used by pathlib in this worker.
        original_as_uri = Path.as_uri
        Path.as_uri = lambda p: original_as_uri(canonical(p))
        original_exists = Path.exists
        # Win32 extended paths do not interpret '..' during filesystem lookup.
        Path.exists = lambda p, *a, **k: original_exists(Path(os.path.normpath(str(p))), *a, **k)
        import platform
        win = sys.getwindowsversion()
        # Avoid platform's three fallback `cmd /c ver` probes. Supply the same
        # OS-version information directly; subprocess dispatch stays forbidden.
        platform._syscmd_ver = lambda *a, **k: ("Windows", str(win.major), f"{win.major}.{win.minor}.{win.build}")
    temp = home / "temporary"; temp.mkdir(exist_ok=True)
    os.environ["TMP"] = os.environ["TEMP"] = str(temp)
    import tempfile
    tempfile.tempdir = str(temp)
    observations = dict(network=0, providers=0, subprocess=0, outside_write=0, source_read=0)
    denied_details = []
    compiled, writes = set(), set()
    busy = False
    source_check, home_check, refs_check, pkg_check = map(canonical, [source, home, refs, clone / PKG])
    immutable_inputs = source_check if source_check.is_relative_to(home_check) else None
    forbidden_root = canonical(config["isolation_forbidden_root"]) if config.get("isolation_forbidden_root") else None
    environment_root = canonical(Path(sys.executable).parent.parent)

    def audit(event, args):
        nonlocal busy
        if busy: return
        busy = True
        try:
            if event.startswith("socket.") and event in ["socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.bind"]:
                observations["network"] += 1; raise PermissionError("Replay forbids network calls")
            if event == "subprocess.Popen":
                denied_details.append(dict(event=event, executable=str(args[0]), arguments=str(args[1])[:600]))
                observations["subprocess"] += 1; raise PermissionError("Replay worker forbids subprocess dispatch")
            if event == "import" and str(args[0]).split(".")[0] in ["azure", "openai", "anthropic", "boto3"]:
                observations["providers"] += 1; raise PermissionError("Replay forbids provider SDKs")
            if event == "sqlite3.connect" and str(args[0]) != ":memory:":
                value = str(args[0])
                if value.startswith("file:"):
                    value = urllib.parse.unquote(urllib.parse.urlsplit(value).path)
                    if os.name == "nt" and re.match(r"^/[A-Za-z]:", value): value = value[1:]
                p = canonical(value)
                if not p.is_relative_to(home_check) or p.is_relative_to(refs_check) or p.is_relative_to(pkg_check) or (immutable_inputs and p.is_relative_to(immutable_inputs)):
                    observations["source_read"] += 1
                    denied_details.append(dict(event=event,path=str(p)))
                    raise PermissionError("SQLite connection outside mutable replay workspace")
            if event == "compile" and len(args) > 1 and isinstance(args[1], str):
                p = Path(args[1])
                if p.is_absolute() and p.is_relative_to(clone) and p.suffix == ".py": compiled.add(p)
            if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
                p = canonical(os.fsdecode(args[0])); mode = str(args[1] or ""); flags = args[2] if isinstance(args[2], int) else 0
                if os.name == "nt" and str(p).upper() == "\\\\.\\NUL":
                    return  # Native numerical libraries use the nonpersistent null sink.
                writing = any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                if writing:
                    if not p.is_relative_to(home_check) or p.is_relative_to(refs_check) or p.is_relative_to(pkg_check) or (immutable_inputs and p.is_relative_to(immutable_inputs)):
                        denied_details.append(dict(event=event,path=str(p),mode=mode))
                        observations["outside_write"] += 1; raise PermissionError("Protected write: " + str(p))
                    writes.add(p)
                elif p.is_relative_to(source_check) and (immutable_inputs or not p.is_relative_to(home_check)) and not p.is_relative_to(source_check / ".venv"):
                    observations["source_read"] += 1; raise PermissionError("Undeclared original-tree read: " + str(p))
                elif forbidden_root and p.is_relative_to(forbidden_root) and not p.is_relative_to(home_check) and not p.is_relative_to(environment_root):
                    observations["source_read"] += 1; raise PermissionError("Isolation forbids original workspace read: " + str(p))
            if event in ["os.rename", "os.remove", "os.rmdir", "os.mkdir", "shutil.rmtree"]:
                paths = args[:2] if event == "os.rename" else args[:1]
                for value in paths:
                    if isinstance(value, (str, bytes, os.PathLike)):
                        p = canonical(os.fsdecode(value))
                        if not p.is_relative_to(home_check) or p.is_relative_to(refs_check) or p.is_relative_to(pkg_check) or (immutable_inputs and p.is_relative_to(immutable_inputs)):
                            denied_details.append(dict(event=event,path=str(p)))
                            observations["outside_write"] += 1; raise PermissionError("Protected filesystem operation: " + str(p))
                        if event == "os.rename": writes.add(p)
        finally: busy = False

    sys.addaudithook(audit)
    for event, args in [("socket.connect", (None, ("127.0.0.1", 9))),
                        ("open", (str(source / "replay_probe"), "w", os.O_WRONLY | os.O_CREAT)),
                        ("open", (str(source / "README.md"), "r", 0)),
                        ("sqlite3.connect", (str(source / "sqlite_probe.db"),)),
                        ("subprocess.Popen", ("blocked", [], None, None)),
                        ("import", ("openai", None, None, None, None))]:
        try: sys.audit(event, *args); raise AssertionError("Guard self-test failed")
        except PermissionError: pass
    if forbidden_root:
        try:
            sys.audit("open", str(forbidden_root / "README.md"), "r", 0)
            raise AssertionError("Original-workspace read guard failed")
        except PermissionError: pass
    baseline = dict(observations)
    started = time.time(); result = dict(stage=stage, status="FAIL", runner_sha256=worker_runner_sha256)
    try:
        import numpy as np
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        from threadpoolctl import threadpool_limits
        pa.set_memory_pool(pa.system_memory_pool()); pa.set_cpu_count(1); pa.set_io_thread_count(1)
        sys.path[:0] = [str(clone / BASE), str(clone / L1), str(clone / L3)]
        entry = next(x for x in STAGES if x[0] == stage)
        script, outputs = entry[1], entry[2]
        output_before = {p:((clone/p).stat().st_size,(clone/p).stat().st_mtime_ns) if (clone/p).exists() else None for p in outputs}
        report_before = {p: sha(p) for p in (clone / L).rglob("*.md")}

        def run(path, args=()):
            sys.argv = [str(clone / path), *map(str, args)]
            with threadpool_limits(limits=1 if stage != "control" else 2):
                runpy.run_path(str(clone / path), run_name="__main__")

        def compare(path, reference=None):
            actual = clone / path; expected = reference or refs / path
            assert actual.exists() and expected.exists(), str(path)
            answer = dict(path=path.as_posix(), actual_sha256=sha(actual), reference_sha256=sha(expected))
            if answer["actual_sha256"] == answer["reference_sha256"]:
                answer["comparison"] = "BYTE_IDENTICAL"
            elif actual.suffix == ".csv":
                # Reading as strings first prevents identifier conversion. Numeric columns
                # are compared numerically only when both complete column types agree.
                identifiers = {k:str for k in ["barcode", "GTIN", "source_barcode", "canonical_barcode", "barcode_recorded"]}
                a = pd.read_csv(actual,dtype=identifiers); b = pd.read_csv(expected,dtype=identifiers)
                assert set(a.columns) == set(b.columns), "CSV fields differ: " + str(path)
                answer["column_order_differs"] = list(a.columns) != list(b.columns)
                a = a[b.columns]
                if path == L4 / "organic_nova_v1.csv":
                    # Accepted CHECK.md already documents these historical metadata
                    # exceptions. Constrain every key, population and zero-evidence
                    # condition; compare all other cells unchanged. Neither CSV is edited.
                    identity = ["category","commercial_type","region"]
                    aa,bb = a.set_index(identity),b.set_index(identity)
                    assert aa.index.is_unique and bb.index.is_unique and set(aa.index)==set(bb.index)
                    differences = {k for k in aa.index if aa.loc[k,"comparable_type"] != bb.loc[k,"comparable_type"]}
                    expected_exceptions = {("beverages","ambiguous composition",r):n for r,n in [("FR",54),("UK-IE",2),("US-CA",7)]}
                    if differences:
                        assert differences == set(expected_exceptions)
                        ledger = []
                        for key,population in expected_exceptions.items():
                            x,y = aa.loc[key],bb.loc[key]
                            assert not bool(x.comparable_type) and bool(y.comparable_type)
                            assert x.full_commercial_n == y.full_commercial_n == population
                            assert x.jointly_known_n == y.jointly_known_n == 0
                            for c in ["risk_difference_pp","p","q"]: assert pd.isna(x[c]) and pd.isna(y[c])
                            assert x.decision == "descriptive only: heterogeneous or unresolved parent"
                            assert y.decision == "insufficient evidence"
                            ledger.append(dict(category=key[0],commercial_type=key[1],region=key[2],population=population,
                                               fields=["comparable_type","decision"],basis="Frozen CHECK.md documented comparability metadata exception; zero joint evidence and no effects"))
                            # A comparison view only; generated and reference files stay intact.
                            bb.loc[key,["comparable_type","decision"]] = x[["comparable_type","decision"]].to_numpy()
                        b = bb.reset_index()[a.columns]
                        answer["documented_v1_metadata_exceptions"] = ledger
                keys = [c for c in b if pd.api.types.is_string_dtype(b[c].dtype)]
                keys += [c for c in ["energy_floor", "tol", "k", "group", "priority"] if c in b and c not in keys]
                if keys:
                    for frame in [a,b]: frame["__occurrence"] = frame.groupby(keys,dropna=False,sort=False).cumcount()
                    def rowkeys(frame):
                        return [tuple("<NA>" if pd.isna(v) else str(v) for v in row) for row in frame[keys+["__occurrence"]].itertuples(index=False,name=None)]
                    left,right = rowkeys(a),rowkeys(b)
                    assert len(set(left)) == len(a) and set(left) == set(right), "CSV row identities differ: " + str(path)
                    indices = {key:i for i,key in enumerate(left)}
                    answer["row_order_differs"] = left != right
                    a = a.iloc[[indices[key] for key in right]].drop(columns="__occurrence").reset_index(drop=True)
                    b = b.drop(columns="__occurrence").reset_index(drop=True)
                pd.testing.assert_frame_equal(a, b, check_dtype=True, check_exact=False, rtol=1e-8, atol=1e-11)
                numeric = {}
                for col in b:
                    if pd.api.types.is_numeric_dtype(b[col]) and not pd.api.types.is_bool_dtype(b[col]):
                        delta = (a[col]-b[col]).abs()
                        if (delta > 0).any(): numeric[col] = dict(cells=int((delta>0).sum()),max_absolute=float(delta.max()))
                if "q" in b:
                    for cutoff in [.01,.05,.1]:
                        assert a.q.le(cutoff).equals(b.q.le(cutoff)), "Adjusted-significance decisions changed"
                answer["numeric_differences"] = numeric
                answer["comparison"] = "NUMERICALLY_EQUIVALENT_CSV"
            elif actual.suffix == ".parquet":
                a, b = pq.read_table(actual), pq.read_table(expected)
                assert a.schema.equals(b.schema, check_metadata=True), "Schema/metadata mismatch: " + str(path)
                pd.testing.assert_frame_equal(a.to_pandas(), b.to_pandas(), check_exact=False, rtol=1e-8, atol=1e-11)
                answer["comparison"] = "NUMERICALLY_EQUIVALENT_PARQUET"
            else: raise AssertionError("Non-identical artifact: " + str(path))
            return answer

        checkpoint = home / "checkpoints" / (stage + ".json")
        used_checkpoint = False

        if stage == "environment":
            from importlib.metadata import version
            import platform
            expected = json.loads((clone / SHARED / "run_manifest_v1.json").read_bytes())
            installed = {name:version(name) for name in expected["packages"]}
            assert installed == expected["packages"], (installed,expected["packages"])
            assert platform.python_version() == expected["python"]
            result.update(python=platform.python_version(),packages=installed)
        elif stage == "master":
            fresh = home / "rebuilt_master"
            if fresh.exists():
                # Retain/revalidate a completed build after a controller/guard failure;
                # never replace or silently rerun an existing governed destination.
                prior = json.loads((home / "master_result.json").read_bytes())
                assert prior.get("master_sha256") == sha(fresh / "master_products.parquet")
                result["checkpoint"] = "Revalidated previously executed master build; retained failure/guard log in attempt_history"
            else:
                run(script, ["--output", fresh])
            actual = fresh / "master_products.parquet"; expected = refs / STUDY / "01_ingestion/05_master_parquet/output/master_products.parquet"
            assert sha(actual) == sha(expected), "Regenerated master differs"
            result["master_sha256"] = sha(actual)
            shutil.copyfile(actual, clone / STUDY / "01_ingestion/05_master_parquet/output/master_products.parquet")
        elif stage == "inventory":
            run(script, ["--output", home / "field_inventory.json"])
        elif stage == "human":
            private = home / "human_original_replay"; private.mkdir(exist_ok=True)
            for name in ["use_human_review_v1.py", "human_claim_review_v1.csv"]: shutil.copyfile(clone / L3 / name, private / name)
            assert sha(private / "use_human_review_v1.py") == sha(clone / L3 / "use_human_review_v1.py")
            shutil.copyfile(home / "human_source_versions/original_submission.csv", private / "human_claim_decisions_v1.csv")
            with threadpool_limits(limits=1): runpy.run_path(str(private / "use_human_review_v1.py"), run_name="__main__")
            assert sha(private / "human_claim_adjudications_v1.csv") == HUMAN_RESULT
            shutil.copyfile(private / "human_claim_adjudications_v1.csv", clone / L3 / "human_claim_adjudications_v1.csv")
            assert sha(clone / L3 / "human_claim_decisions_v1.csv") == HUMAN_FROZEN
            result["original_submission_sha256"] = HUMAN_ORIGINAL
        elif stage == "backlog":
            manifest = json.loads((clone / SHARED / "run_manifest_v1.json").read_bytes())
            archive = manifest["housekeeping_v1"]["source_archive"]
            key = next(k for k in archive if k.endswith("prepare_human_review_v1.py"))
            source_text = archive[key]["text"]
            assert hashlib.sha256(source_text.encode()) .hexdigest() == archive[key]["sha256"]
            tree = ast.parse(source_text)
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
            # Reuse the exact archived backlog statements, excluding selection and HTTP
            # checks. The historical 12-row review/image audit is a declared fixed input.
            offset = next(i for i, n in enumerate(fn.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "plans" for t in n.targets))
            tail = fn.body[offset:]
            tail = tail[:next(i for i,n in enumerate(tail) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == "print")]
            coverage = load(clone / L3 / "communication_coverage_v1.py", "backlog_coverage")
            pointer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "pointer")
            namespace = dict(pd=pd,pq=pq,HERE=clone / L3,KEY=coverage.KEY,MASTER=coverage.MASTER,
                             read_master=coverage.read_master,populations=coverage.populations)
            # Preserve the archived pure-data prefix, including image/evidence pointer
            # fields required for gap counts, and stop before selection/HTTP work.
            prefix = fn.body[:8]
            exec(compile(ast.fix_missing_locations(ast.Module(body=[pointer]+prefix+tail, type_ignores=[])), "<archived-offline-backlog>", "exec"), namespace)
            result["archived_source_sha256"] = archive[key]["sha256"]
        elif stage == "report_tables":
            import math

            def tables(path):
                found, active = [], []
                for line in path.read_text(encoding="utf8").splitlines() + [""]:
                    if line.lstrip().startswith("|"):
                        active.append([re.sub(r"\s+", " ", c.strip()) for c in line.strip().strip("|").split("|")])
                    elif active:
                        if len(active) >= 2 and all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in active[1]):
                            found.append([active[0]] + active[2:])
                        active = []
                return found

            def equal_cell(a, b):
                if a == b: return True
                # Product identifiers are text; never numerically coerce long digit strings.
                if re.fullmatch(r"\d{8,}", a) or re.fullmatch(r"\d{8,}", b): return False
                if a.endswith("%") != b.endswith("%"): return False
                try: return math.isclose(float(a.rstrip("%").replace(",", "")), float(b.rstrip("%").replace(",", "")), rel_tol=1e-8, abs_tol=1e-11)
                except ValueError: return False

            def equal_table(a, b):
                return len(a) == len(b) and all(len(x) == len(y) and all(equal_cell(u,v) for u,v in zip(x,y)) for x,y in zip(a,b))

            checked = []
            for generated in sorted((home / "generated_reports").rglob("*.md")):
                rel = Path(*generated.relative_to(home / "generated_reports").parts[1:])
                reference = refs / rel
                assert reference.exists(), "No historical report reference: " + str(rel)
                accepted = tables(reference); replayed = tables(generated)
                for i, table in enumerate(replayed):
                    assert any(equal_table(table, old) for old in accepted), f"Report table differs: {generated}, table {i}, header {table[0]}"
                checked.append(dict(report=generated.relative_to(home).as_posix(), compared_tables=len(replayed)))
            identical_followups = []
            followups = [("cereal_followup",L1/"cereal_formulations_v1.md"),
                         ("snacks",L1/"savoury_snacks_CHECK_v1.md"),
                         ("beverages",L1/"beverages_CHECK_v1.md"),
                         ("juice",L1/"juice_formulations_v1.md"),
                         ("dairy",L2/"dairy_dessert_formulations_v1.md"),
                         ("biscuits",L1/"biscuits_and_wafers_CHECK_v1.md")]
            for prior_stage,path in followups:
                execution = home/(prior_stage+"_result.json")
                prior = json.loads(execution.read_bytes())
                assert prior["status"]=="PASS"
                current,reference = clone/path,refs/path
                # An unchanged report was not captured/restored by older harness
                # revisions. Require its bytes AND write timestamp from the actual
                # successful published-script execution, rather than assuming a
                # prefilled reference was regenerated.
                if not prior.get("generated_reports"):
                    ended=execution.stat().st_mtime
                    assert ended-prior["seconds"]-5 <= current.stat().st_mtime <= ended+5, "No execution-time report write: "+str(path)
                    assert sha(current)==sha(reference), "Uncaptured report differs"
                    identical_followups.append(dict(report=path.as_posix(),comparison="BYTE_IDENTICAL",compared_tables=len(tables(current))))
            assert checked, "No regenerated report evidence"
            result["reports"] = checked
            result["byte_identical_followup_reports"] = identical_followups
            result["table_count"] = sum(x["compared_tables"] for x in checked+identical_followups)
        elif stage == "package":
            package_checkpoint = home / "checkpoints/package_build.json"
            if package_checkpoint.exists():
                completed = json.loads(package_checkpoint.read_bytes())
                assert sha(home/completed["execution_result"]) == completed["execution_result_sha256"]
                candidate = clone / completed["candidate_directory"]
                for relative, digest in completed["files"].items(): assert sha(candidate/relative) == digest
                result["build_checkpoint"] = "Revalidated completed candidate build; independent verifier and comparisons rerun"
            else:
                candidate = clone / STUDY / "04_replay_candidate"
                attempt = 1
                while candidate.exists():
                    attempt += 1
                    candidate = clone / STUDY / f"04_replay_candidate_{attempt}"
                candidate.mkdir()
            result["candidate_directory"] = candidate.relative_to(clone).as_posix()
            for name in ["analytical_rules_v1.py", "build_analytical_package_v1.py", "verify_analytical_package_v1.py"]: shutil.copyfile(clone / PKG / name, candidate / name)
            sys.path.insert(0, str(candidate))
            b = load(candidate / "build_analytical_package_v1.py", "build_analytical_package_v1")
            sys.modules["build_analytical_package_v1"] = b
            assert not b.FREEZE.exists()
            original_population_summary = b.population_summary
            population_columns = list(dict.fromkeys(["region", "category", "product_scope_eligible",
                "commercial_format", "commercial_status", "profile_family", "profile_status"] + list(b.rules.RAW)))
            def projected_population_summary(frame):
                # The original function reads only these fields. Avoid copying all
                # unrelated evidence columns for each group on low-memory hosts.
                # A truncated sample containing only unknown measurements for a
                # profile makes the historical function divide by zero.
                sample = frame.head(1000)
                sample = sample[sample.profile_status.ne("REQUIRED_MEASUREMENT_UNKNOWN")]
                pd.testing.assert_frame_equal(original_population_summary(sample),
                    original_population_summary(sample[population_columns]))
                return original_population_summary(frame[population_columns])
            b.population_summary = projected_population_summary
            result["resource_adapter"] = dict(population_summary_columns=population_columns,
                equivalence="Unchanged original function, projected inputs; sample equality asserted")
            if not package_checkpoint.exists(): b.build()
            import gc
            gc.collect(); pa.default_memory_pool().release_unused()
            v = load(candidate / "verify_analytical_package_v1.py", "replay_package_verify")
            result["independent_checks"] = v.verify()
            result["comparisons"] = []
            for name in ["analytical_assignments_v1.parquet", "assessed_communication_v1.parquet", "human_observations_v1.parquet", "boundary_annotations_v1.parquet", "population_summary_v1.csv", "communication_coverage_v1.csv"]:
                result["comparisons"].append(compare(candidate.relative_to(clone) / "output" / name, refs / PKG / "output" / name))
            a = json.loads((candidate / "output/approved_findings_v1.json").read_bytes())
            e = json.loads((refs / PKG / "output/approved_findings_v1.json").read_bytes())
            assert a.pop("status") == "VALIDATED_CANDIDATE_FOR_REVIEW" and e.pop("status") == "ACCEPTED_FROZEN"
            differences = []
            def json_equal(left,right,path=""):
                if isinstance(left,bool) or isinstance(right,bool) or left is None or right is None:
                    assert left is right, path
                elif isinstance(left,(int,float)) and isinstance(right,(int,float)):
                    import math
                    assert math.isclose(left,right,rel_tol=1e-8,abs_tol=1e-11), path
                    if left != right: differences.append(dict(path=path,actual=left,reference=right))
                elif isinstance(left,dict) and isinstance(right,dict):
                    assert left.keys()==right.keys(), path
                    for key in left: json_equal(left[key],right[key],path+"/"+key)
                elif isinstance(left,list) and isinstance(right,list):
                    assert len(left)==len(right),path
                    for i,(x,y) in enumerate(zip(left,right)): json_equal(x,y,path+f"/{i}")
                else: assert left==right,path
            json_equal(a,e)
            result["findings"] = dict(status_difference="candidate versus accepted",numeric_differences=differences)
        else:
            if checkpoint.exists():
                evidence = json.loads(checkpoint.read_bytes())
                assert evidence["script_sha256"] == sha(clone/script)
                assert sha(home/evidence["execution_result"]) == evidence["execution_result_sha256"]
                for relative,digest in evidence["outputs"].items(): assert sha(clone/relative)==digest
                result["checkpoint"] = "Revalidated fresh calculation completed in retained earlier attempt; only comparison repeated"
                used_checkpoint = True
            else:
                run(script, ["--check-only"] if stage == "research_validation" else [])
        if outputs:
            if not used_checkpoint:
                native_writes = []
                for p in outputs:
                    if canonical(clone/p) not in writes:
                        current = ((clone/p).stat().st_size,(clone/p).stat().st_mtime_ns)
                        assert current != output_before[p], "Expected output not regenerated: " + str(p)
                        native_writes.append(p.as_posix())
                result["native_writes_confirmed_by_stat"] = native_writes
            result["comparisons"] = [compare(p) for p in outputs]
            # The original manifest identifies historical serialization. Create a
            # distinct replay manifest only after each generated output passes its
            # scientific comparison. Keep original source/code hashes untouched.
            manifest_path = clone / SHARED / "run_manifest_v1.json"
            manifest = json.loads(manifest_path.read_bytes())
            changed = []
            for p in outputs:
                relative = p.relative_to(STUDY).as_posix()
                if relative in manifest["sha256"] and manifest["sha256"][relative] != sha(clone/p):
                    changed.append(dict(path=relative,accepted_sha256=manifest["sha256"][relative],replayed_sha256=sha(clone/p)))
                    manifest["sha256"][relative] = sha(clone/p)
            if changed:
                original = home / "accepted_research_manifest.json"
                if not original.exists(): shutil.copyfile(manifest_path,original)
                manifest.setdefault("isolated_replay",dict(original_manifest_sha256=sha(original),scope="Generated numerical-equivalence candidate; not accepted v1"))
                manifest["isolated_replay"].setdefault("generated_hashes",[]).extend(changed)
                save(manifest_path,manifest)
                result["candidate_manifest_updates"] = changed
        # Preserve generated narratives, then restore exact historical reports that
        # subsequent frozen decision/hash contracts identify as immutable references.
        reports = []
        for p in (clone / L).rglob("*.md"):
            if p not in report_before or sha(p) != report_before[p]:
                rel = p.relative_to(clone)
                capture = home / "generated_reports" / stage / rel
                capture.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, capture)
                reports.append(rel.as_posix())
                expected = refs / rel
                if expected.exists(): shutil.copyfile(expected, p)
        result.update(status="PASS", generated_reports=reports)
    except BaseException:
        result["error"] = traceback.format_exc()
        print(result["error"], flush=True)
    finally:
        observed = {}
        for p in sorted(compiled):
            rel = p.relative_to(clone).as_posix()
            origin = re.sub(r"/04_replay_candidate(?:_\d+)?/", "/04_analytical_package/", rel)
            raw = p.read_bytes(); normalized = raw.replace(b"\r\n", b"\n")
            oids = [hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest() for x in [raw,normalized]]
            if config["published_tree"].get(origin) not in oids:
                result.update(status="FAIL", source_error="Executed unpublished or modified source: " + rel)
            observed[rel] = sha(p)
        result.update(seconds=round(time.time()-started,2), source_files=observed,
                      guard_self_tests=baseline, denied_details=denied_details,
                      actual_denials={k:observations[k]-baseline[k] for k in observations})
        if any(result["actual_denials"].values()): result["status"] = "FAIL"
        save(home / (stage + "_result.json"), result)
        print("STAGE_RESULT", stage, result["status"], result["seconds"], flush=True)
    return 0 if result["status"] == "PASS" else 1


def drive(home, resume=False):
    config = json.loads((home / "config.json").read_bytes())
    assert sha(Path(__file__)) == config["runner_sha256"], "Runner changed; use a new run or explicitly record a revision"
    results = []
    for name, _, _ in STAGES:
        result_path = home / (name + "_result.json")
        if resume and result_path.exists() and json.loads(result_path.read_bytes())["status"] == "PASS":
            result = json.loads(result_path.read_bytes())
            for rel, digest in result.get("source_files", {}).items():
                assert sha(home / "checkout" / rel) == digest, "Completed stage source changed: " + rel
            for comparison in result.get("comparisons", []):
                assert sha(home / "checkout" / comparison["path"]) == comparison["actual_sha256"], "Completed stage output changed"
            results.append(result); print("VERIFIED_COMPLETED_STAGE", name, flush=True); continue
        print("START", name, flush=True)
        if result_path.exists():
            attempt = home / "attempt_history" / name / str(time.time_ns())
            attempt.mkdir(parents=True)
            shutil.copyfile(result_path, attempt / "result.json")
            if (home / (name + ".log")).exists():
                shutil.copyfile(home / (name + ".log"), attempt / "stage.log")
        env = {k:v for k,v in os.environ.items() if not k.startswith(("AZURE_","OPENAI_","ANTHROPIC_"))}
        env.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2", PYTHONIOENCODING="utf-8")
        with (home / (name + ".log")).open("w", encoding="utf8") as stream:
            rc = subprocess.call([sys.executable,"-I","-B","-X","utf8",str(home / "replay.py"),"--worker",name,"--workspace",str(home)], cwd=home / "checkout",env=env,stdout=stream,stderr=subprocess.STDOUT)
        if result_path.exists(): result = json.loads(result_path.read_bytes())
        else: result = dict(stage=name,status="FAIL",error="Worker exited without result",exit_code=rc)
        results.append(result); print("FINISHED",name,result["status"],result.get("seconds"),flush=True)
        save(home / "results.json", dict(status="RUNNING" if rc==0 else "FAIL",commit=config["commit"],stages=results))
        if rc: return rc
    differences = [p for p,h in config["original_hashes"].items() if sha(Path(config["source"])/p)!=h]
    assert not differences, differences
    save(home / "results.json", dict(status="PASS",commit=config["commit"],stages=results,original_files_unchanged=len(config["original_hashes"]),
         limits=["Exact dated governed source and saved provider observations are fixed inputs; no new ingestion/OCR/LLM", "Installed recorded analytical environment reused; not a fresh dependency installation test", "Historical reports remain evidence references; generated narratives are captured separately"]))
    print("FULL_REPLAY_PASS",len(results),"stages; original hashes unchanged",flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--candidate-root",type=Path,help="Use only a declared release candidate; no Git/local-input restoration")
    p.add_argument("--verify-candidate",action="store_true",help="Verify release files and exact streamed database restoration without rerunning research")
    p.add_argument("--resume",action="store_true")
    p.add_argument("--accept-runner-revision",action="store_true", help="Retain old runner and record its successor before resume")
    p.add_argument("--revision-only",action="store_true", help="Record/copy an approved harness revision without launching another controller")
    p.add_argument("--worker",choices=[x[0] for x in STAGES])
    a=p.parse_args(); home=longpath(a.workspace)
    if a.verify_candidate:
        assert a.candidate_root, "Supply --candidate-root"
        return verify_candidate(longpath(a.candidate_root), home)
    if a.worker: return worker(home,a.worker)
    if not a.resume:
        if a.candidate_root: prepare_candidate(longpath(a.candidate_root),home)
        else: prepare(longpath(a.source_root),home)
    elif a.accept_runner_revision:
        config = json.loads((home / "config.json").read_bytes())
        old, new = config["runner_sha256"], sha(Path(__file__))
        if old != new:
            archive = home / "runner_revisions"; archive.mkdir(exist_ok=True)
            shutil.copyfile(home / "replay.py", archive / (old + ".py"))
            config.setdefault("runner_revisions", []).append(dict(previous=old, successor=new, time=time.time()))
            config["runner_sha256"] = new
            save(home / "config.json", config)
            shutil.copyfile(__file__, home / "replay.py")
    if a.revision_only:
        assert a.resume and a.accept_runner_revision, "Revision-only requires explicit resume/revision flags"
        return 0
    return drive(home,a.resume)


if __name__ == "__main__":
    raise SystemExit(main())
