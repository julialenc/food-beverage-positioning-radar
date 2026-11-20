"""Register unchanged offline BEVERAGE 04 artifacts; never deploy or call services."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
OUT = SEG / "beverage_04_closed_v1"
REPORT = SEG / "BEVERAGE 04 - Preparation closure.md"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_map(mapping):
    for name, digest in mapping.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Protected artifact changed: {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest_path = OUT / "closure_manifest.json"
    if args.verify_only:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        verify_map(m["protected_files_sha256"])
        verify_map({m["report"]["path"]: m["report"]["sha256"]})
        print(json.dumps({"closure_verified": True, "protected_files": len(m["protected_files_sha256"]), "paid_calls": 0}))
        return
    if manifest_path.exists() or REPORT.exists():
        raise FileExistsError("BEVERAGE 04 closure already exists; verify instead")
    prep_path = SEG / "emerging_benefits_prompt_v1/preparation_manifest.json"
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    verify_map(prep["protected_input_sha256"])
    verify_map({"pipeline/vision_prompts/current/" + name: digest for name, digest in prep["unchanged_core_prompt_sha256"].items()})
    # Preparation output keys are repo-relative, as are protected inputs.
    verify_map(prep["output_sha256"])
    verify_map({prep["prompt"]: prep["prompt_sha256"], prep["script"]: prep["script_sha256"],
                prep["standalone_validator"]: prep["standalone_validator_sha256"]})
    register = [
        (prep["prompt"], "emerging_benefits_v1", "Independent prompt"),
        ("pipeline/vision_prompts/emerging_benefits/emerging_benefits_input_v1.schema.json", "emerging_benefits_input_v1", "Input JSON Schema"),
        ("pipeline/vision_prompts/emerging_benefits/emerging_benefits_output_v1.schema.json", "emerging_benefits_output_v1", "Output JSON Schema"),
        ("pipeline/vision_prompts/emerging_benefits/CONTRACT_v1.md", "v1", "Observation contract"),
        ("presentations/segmentation/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json", "1.0.0", "Approved human-reviewed definitions"),
        (prep["standalone_validator"], "v1", "Standalone offline validator"),
        ("presentations/segmentation/emerging_benefits_prompt_v1/contract_fixtures.json", "v1", "Synthetic hand-authored fixtures; not model predictions"),
        ("presentations/segmentation/emerging_benefits_prompt_v1/offline_validation_results.json", "v1", "45 offline checks"),
        (prep["script"], "v1", "Reproducible offline preparation"),
        (prep_path.relative_to(ROOT).as_posix(), "v1", "Original preparation manifest"),
    ]
    registry = [{"path": str((ROOT / path).resolve()), "repository_path": path, "version": version,
                 "role": role, "sha256": sha(ROOT / path)} for path, version, role in register]
    protected = dict(prep["protected_input_sha256"])
    protected.update(prep["output_sha256"])
    protected.update({item["repository_path"]: item["sha256"] for item in registry})
    protected[Path(__file__).relative_to(ROOT).as_posix()] = sha(__file__)
    checks = json.loads((SEG / "emerging_benefits_prompt_v1/offline_validation_results.json").read_text(encoding="utf-8"))
    assert len(checks["checks"]) == 45 and all(c["passed"] for c in checks["checks"])
    table = "\n".join(f"| {r['role']} | `{r['path']}` | {r['version']} | `{r['sha256']}` |" for r in registry)
    REPORT.write_text("# BEVERAGE 04 — Preparation closure\n\n"
        "**23 October 2026 · Europe/Berlin. Prepared and technically documented; not deployed.**\n\n"
        "Julia authorized closure and registration. The approved BEVERAGE 03 registry v1.0.0 is unchanged. "
        "The independent saved-OCR layer is prepared for future approved testing. Hydration/electrolyte extraction "
        "has not been deployed or run against the historical corpus. A separately approved emerging-benefit pilot remains necessary.\n\n"
        "All three core extraction prompts and both dairy context-review prompts match their preparation hashes. "
        "The legacy validator, 34 claim flags, taxonomy, saved OCR, database and historical classifications remain unchanged. "
        "No paid calls, historical backfill, core allocation changes or new benefit decisions were made.\n\n"
        "## Frozen registry\n\n| Artifact | Exact location | Version | SHA256 |\n|---|---|---|---|\n" + table +
        "\n\n## Verification and limits\n\n"
        "45 offline contract checks passed (19 accepted synthetic fixtures, 23 rejected invalid mutations, three profile checks). "
        "These check contract enforcement, not model accuracy. Human image review and its provenance limitations remain as documented "
        "in BEVERAGE 03; Codex did not independently inspect those images. Existing approvals and original artifacts are preserved.\n\n"
        "The machine-readable closure manifest registers upstream hashes, this report and the exact five unchanged prompt hashes. "
        "Verify with `pipeline/segmentation/close_beverage_04.py --verify-only`.\n", encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    m = {"check": "BEVERAGE 04", "status": "Prepared and technically documented; not deployed", "decision_date": "2026-10-23",
         "timezone": "Europe/Berlin", "authorized_by": "Julia", "registry": registry,
         "definition_version": "1.0.0", "protected_files_sha256": protected,
         "unchanged_core_prompt_sha256": prep["unchanged_core_prompt_sha256"],
         "offline_checks": 45, "paid_calls": 0, "deployed": False, "historical_corpus_run": False,
         "legacy_flags_taxonomy_classifications_changed": False, "separate_pilot_approval_required": True,
         "report": {"path": REPORT.relative_to(ROOT).as_posix(), "sha256": sha(REPORT)}}
    manifest_path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"closed": True, "registered_artifacts": len(registry), "protected_files": len(protected), "paid_calls": 0}))


if __name__ == "__main__":
    main()
