# v1.1.0 evidence supplement — publication scope

Version: **v1.1.0**. This extends audit access; it does not change the
accepted findings, website, Streamlit application or v1.0.0 tag.

## Distribution

Keep the evidence-audit scripts, guide, validation report and exact manifest in
Git. Distribute every manifest-listed asset part as a GitHub Release attachment.
The candidate parts are staged in `outputs/ocr_llm_evidence_candidate_v1/assets/`.
Each part is at most 512 MiB. Asset groups contain the existing public source and
analytical inputs, retained historical evidence, ledgers/governed input, exact
historical working database, cached images, and additional audit source.

The manifest is the file-by-file publication list: every path has a SHA-256,
byte count and asset group. Restoration reads only those assets; it does not
fall back to unpublished analytical files. A Git clone alone is insufficient.
Julia authorized commit, push, v1.1.0 publication and public download verification
on 23 November 2026. Only this evidence-audit namespace and its root
`.gitattributes` byte-preservation rule enter the supplemental source commit.
The approved root README and unrelated working files are outside that commit.

## Preservation rules

All retained source evidence is distributed without changing its bytes. Absolute
historical paths are resolved at I/O in the disposable replay, not edited in
the historical records. Approval text is taken from its byte-identical public
copy. Provider observations, HOLDs, failures, uncertain outcomes and pending
receipts remain distinct. Original databases, images, prompts, responses,
human-review versions and the frozen analytical package are not rewritten.

Timestamped raw OFF downloads, credentials, working environments, unrelated
trial databases and old generated workspaces are excluded. The installed
recorded Python environment was reused for validation; fresh dependency
installation is a separate check. Allow roughly 25 GiB free for assets,
restoration, references and generated outputs.

## Required release wording

Publish **all retained evidence**, not a claim that every historical raw
provider response still exists. The 35 historical assessments reused in the
locked claims retain OCR text, extracted results and provenance, but no retained
original image bytes or raw model envelopes were found. Broader legacy CSVs are
preserved historical extraction records; they are not substitutes for missing
transport envelopes. The complete replay uses saved observations and fixed
human decisions rather than contacting providers or repeating human review.

Suggested release summary: “Adds hash-verified offline OCR/LLM evidence assets
and reproduction from governed input through quality review, reconciliation,
claims lock and accepted analytical tables. Preserves v1.0.0 and explicitly
documents the historical evidence gap.”

Release verification downloads every asset part anonymously, checks all part
and restored-file hashes without extracting the large archive, and verifies the
tagged source archive against the release commit. It does not repeat the full
34-stage analysis or install a fresh environment. The prior isolated replay and
its scientific inputs/source identities remain the runtime validation.

The root README restructuring was separately committed as `d92b0485` and is
preserved. The historical validation record describes its earlier snapshot.
v1.0.0 and the frozen analytical package are not modified or republished.
