# v1.0.0 prepublication check

**PASS — step 7 complete locally.** Planned version/tag: 1.0.0 / v1.0.0. Nothing is staged, committed, pushed, tagged or published.

The final layout keeps code/data at canonical repository paths and puts only compressed database parts and release controls under audit_replay/release/. The candidate's 25-stage replay remains valid: all 36 executed scientific source files are equivalent (three ordinary checkout EOL differences), all fixed input hashes are unchanged, and the frozen integrity verifier passes. The updated harness's repository-layout path resolution, file hashes and streamed database restoration passed separately. A second full analytical calculation was unnecessary because no scientific code or data changed.

Git attributes set text=unset for fixed evidence, the human archive, audit tooling and governed contracts. Explicit allowlists expose only the reviewed inputs; the raw database, workspaces, credentials and local construction helpers remain ignored. The frozen .gitignore is untouched: six new accepted-package outputs are named in PUBLICATION_FILES.json force_add_paths for explicit force-add after commit authorization. Two already tracked output references remain tracked normally. Do not use git add -A.

PUBLICATION_FILES.json is the exact future commit inventory and expected hash record. Scope and exclusions are in SCOPE.md; the GitHub-ready release text is RELEASE_NOTES.md. The original analytical identifier and release digest are unchanged. The declared installed environment was reused; clean dependency installation and final public-tag download remain unclaimed.

Next gates: user-authorized commit/push; user-authorized tag/GitHub publication; download and verify that published release. No website republication or Streamlit deployment is required.

Final checks: 348 exact publication paths (344 dependency hashes plus four publication/review controls); all published Python syntax/JSON and entry-point links pass; every file is below 100 MiB. All 72 original hashes remain unchanged, the frozen integrity verifier passes, and the Git index is empty. See PREPUBLICATION_VALIDATION.json for machine-readable results.
