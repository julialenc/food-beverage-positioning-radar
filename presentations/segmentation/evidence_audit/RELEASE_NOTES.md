# v1.1.0 — Retained OCR/LLM evidence and offline audit replay

## Important historical evidence gap

**35 historical assessments reused in the locked claims have saved OCR text,
extracted results and source provenance, but no retained original image bytes or
raw model response envelopes were found.** Their original image-to-raw-response
chain cannot be fully audited or reconstructed. This release does not invent
missing originals or substitute newly generated provider outputs.

The case register is published at
[presentations/segmentation/evidence_audit/historical_gaps.json](https://github.com/julialenc/food-beverage-positioning-radar/blob/v1.1.0/presentations/segmentation/evidence_audit/historical_gaps.json).

## Added

- All retained evidence in the declared scope: cached images, execution ledgers,
  saved OCR/model observations, prompts, source, authorization/review records,
  historical exports and governed starting inputs.
- A file-by-file SHA-256 manifest and 13 split asset parts (each at most 512 MiB).
  **A normal Git clone alone is insufficient; download every part.**
- Offline reconstruction through quality exports, claims reconciliation and a
  fresh claims lock, followed by the existing analytical replay.
- Dependency pins, restoration instructions, validation records and a streamed
  download verifier.

## Validation

**34/34 local isolated checks passed.** The population/history tables, all four
claims-lock outputs and rebuilt master reproduced byte-for-byte. The remaining
scientific comparisons use the v1.0 tolerances and previously documented metadata
exceptions. All final passed workers recorded zero actual network/provider,
subprocess, outside-write or original-tree-read denials beyond guard self-tests.
No OCR/LLM provider calls occurred. The final source asset is bound to 52 executed
scientific-source identities; data assets retain the verified starting bytes.

The replay reused the recorded installed Python environment; fresh dependency
installation was not certified. Human decisions and sampling choices remain
fixed evidence inputs. Exploratory selection models and human judgments are not
regenerated. Historical failed harness attempts and platform corrections are
recorded in the validation documentation.

## Preservation and scope

The frozen analytical package, v1.0.0 tag/release, accepted findings, Streamlit
application and research website are unchanged. Segmentation remains an
**IN PROGRESS** research workstream. The base archive preserves source/data from
`e344c202`; the root README was independently restructured in `d92b0485`.

Timestamped raw OFF downloads, credentials, working environments and unrelated
trial databases are excluded. Broader legacy CSVs are preserved extraction
records, not replacements for unretained provider envelopes. OFF data/images
retain ODbL / CC BY-SA attribution; project code/docs retain Apache 2.0.

[Download/restoration instructions](https://github.com/julialenc/food-beverage-positioning-radar/blob/v1.1.0/presentations/segmentation/evidence_audit/README.md) ·
[Scope](https://github.com/julialenc/food-beverage-positioning-radar/blob/v1.1.0/presentations/segmentation/evidence_audit/RELEASE_SCOPE.md) ·
[Validation](https://github.com/julialenc/food-beverage-positioning-radar/blob/v1.1.0/presentations/segmentation/evidence_audit/CHECK.md)

## Public download verification

Publication-time verification will be recorded below after anonymous downloads.
It checks the tagged source archive, every asset part and every declared restored
file. It does not repeat the 34-stage analytical run.
