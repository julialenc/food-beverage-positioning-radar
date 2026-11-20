"""Frozen v6 adapter: independent saved-OCR entry points plus legacy opt-in API.

The caller must supply an approved Guard policy and a provider adapter. This
module does not import an API client, download images, or modify legacy claims.
The integrated RUN 06B runner uses saved OCR even when core extraction fails.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pipeline.vision_ops.validate_emerging_benefits_v1 import validate_input, validate_pair

ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "presentations/segmentation/beverage_04_closed_v1/closure_manifest.json"
PROMPT = ROOT / "pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v1.txt"
DEFINITION_VERSION = "1.0.0"
PROMPT_VERSION = "emerging_benefits_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_contract() -> tuple[str, dict[str, str]]:
    """Fail closed if any approved prompt, schema, validator or definition changed."""
    registry = json.loads(CLOSURE.read_text(encoding="utf-8"))["registry"]
    expected = {entry["repository_path"]: entry["sha256"] for entry in registry}
    required = [
        "pipeline/vision_prompts/emerging_benefits/prompt_emerging_benefits_v1.txt",
        "pipeline/vision_prompts/emerging_benefits/emerging_benefits_input_v1.schema.json",
        "pipeline/vision_prompts/emerging_benefits/emerging_benefits_output_v1.schema.json",
        "pipeline/vision_ops/validate_emerging_benefits_v1.py",
        "presentations/segmentation/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json",
    ]
    for relative in required:
        if relative not in expected or _sha(ROOT / relative) != expected[relative]:
            raise ValueError(f"Frozen emerging-benefit contract mismatch: {relative}")
    return PROMPT.read_text(encoding="utf-8"), {key: expected[key] for key in required}


def build_input(*, barcode: str, product_name: str | None, regions: list[str],
                country_assignments: list[str], ocr_text: str, source_reference: str,
                source_artifact_sha256: str | None, original_image_url: str | None,
                image_provenance_note: str, prior_panel_context: str | None,
                prior_profile: str | None, request_id: str) -> dict:
    """Use the exact full saved OCR; never trim it to legacy core-prompt limits."""
    record = dict(schema_version="emerging_benefits_input_v1", request_id=request_id,
        barcode=barcode, product_name=product_name, regions=regions,
        country_assignments=country_assignments, ocr_text=ocr_text,
        ocr_sha256=hashlib.sha256(ocr_text.encode("utf-8")).hexdigest(),
        source_reference=source_reference, source_artifact_sha256=source_artifact_sha256,
        original_image_URL=original_image_url, image_provenance_note=image_provenance_note,
        prior_panel_context=prior_panel_context, prior_profile=prior_profile,
        context_facts=[])
    validate_input(record)
    return record


def prepare_saved_ocr(input_record: dict):
    """RUN 06B independent v6 input: successful full OCR, regardless of core outcome.

    Dispatch and reservation belong to the integrated runner. The older opt-in
    run_authorized interface below retains its original compatibility contract.
    """
    validated = validate_input(input_record)
    if not validated.ocr_text or not validated.ocr_text.strip():
        raise ValueError("Reusable full OCR is required")
    prompt, hashes = frozen_contract()
    return prompt, hashes


def validate_saved_ocr_result(input_record: dict, output: dict):
    """Validate independent v6 output against the frozen evidence contract."""
    result = validate_pair(input_record, output)
    statuses = [getattr(result, name).front_status for name in ("hydration", "electrolyte")]
    status = ("success_with_claims" if "detected" in statuses else
              "success_no_claims" if all(s == "not_detected" for s in statuses) else "unusable")
    return result.model_dump(), status


def run_authorized(*, input_record: dict, core_success: bool, guard, core_work_key: str,
                   approved_manifest_sha256: str, call_id: str, dispatch):
    """Reserve cost before one provider call and return a versioned observation.

    Supply a dedicated emerging-benefits Guard ledger with an approved policy;
    the core runner's success records are not reused as emerging assessments.
    `dispatch(prompt, input_record)` must return (output, receipt). A missing or
    uncertain receipt remains reserved in Guard and must be reconciled manually.
    This function is intentionally not called by stage_10 or RUN 06B by default.
    """
    if not core_success:
        raise PermissionError("Emerging layer requires completed core extraction, including valid no-claim")
    validated = validate_input(input_record)
    if not validated.ocr_text or not validated.ocr_text.strip():
        raise ValueError("Reusable full OCR is required")
    prompt, hashes = frozen_contract()
    guard.begin_job(core_work_key, approved_manifest_sha256)
    if guard.has_success(core_work_key):
        raise PermissionError("Existing successful observation; reconcile before billable dispatch")
    guard.reserve_call(call_id, core_work_key, "emerging_benefits")
    output, receipt = dispatch(prompt, input_record)
    guard.receipt(call_id, receipt["provider_request_id"], receipt["actual_nanochf"],
                  receipt["outcome"], usage=receipt["usage"],
                  tariff_sha256=receipt["tariff_sha256"],
                  raw_receipt_sha256=receipt["raw_receipt_sha256"])
    result = validate_pair(input_record, output)
    observation = dict(layer="emerging_benefits", prompt_version=PROMPT_VERSION,
        definition_version=DEFINITION_VERSION, contract_sha256=hashes,
        source_ocr_sha256=validated.ocr_sha256, source_reference=validated.source_reference,
        core_work_key=core_work_key, call_id=call_id, assessment=result.model_dump())
    status = "success_with_claims" if any(
        getattr(result, name).front_status == "detected" for name in ("hydration", "electrolyte")) else "success_no_claims"
    guard.append_observation(core_work_key, status, observation)
    return observation
