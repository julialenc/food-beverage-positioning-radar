# Wave 2 audit replay

The v1.0.0 release includes the declared inputs and accepted references needed to rebuild the master and segmentation tables. Start with [release instructions](release/README.md), [scope](release/SCOPE.md), [release notes](release/RELEASE_NOTES.md) and [validation](release/CHECK.md).

Use Python 3.12.4 and requirements-replay.txt. From the repository root:

```powershell
.venv/Scripts/python.exe -B -u presentations/segmentation/audit_replay/replay.py --candidate-root presentations/segmentation/audit_replay/release --workspace outputs/release_replay
```

The runner checks release hashes, restores the large database, and computes all 25 stages in a separate workspace. It preserves the accepted package. Workers block original-workspace reads, provider/network calls, subprocesses and writes outside the workspace. Synthetic probes verify the guards; Python audit hooks are regression controls rather than an OS security sandbox.

Both human submissions are retained in human_source_versions/. The original source was recovered from preserved fields and matched its historical hash. Seven barcode strings and eleven dates differ; no GTIN digits are guessed. The unchanged interpretation reproduces the accepted sidecar in a separate original-source directory. The later frozen submission stays untouched.

Exact byte equality is preferred. Other tables require explicit schemas/identities/states and rtol 1e-8, atol 1e-11. Product identifiers stay strings. Q decisions at 0.01, 0.05 and 0.1 cannot change. The recorded three-population processing metadata exception is narrowly checked without editing either table. Generated results are retained; a separate replay manifest records their actual hashes after comparison. Historical report references stay unchanged.

Windows path/URI and OS-version adapters avoid unsupported path forms and subprocess probes. Arrow uses one CPU/I/O thread; numerical thread limits and the population-summary column projection reduce memory without changing rows or rules. Full final tables must still match accepted bytes.

The recorded isolated run passed 25 stages with all 72 pinned original files unchanged. The current release keeps the same scientific source and fixed inputs; repository layout and Git publication rules are checked separately. The installed declared environment was reused; a fresh dependency installation is not certified. Use --resume only for the same workspace; source/output hashes are rechecked. --accept-runner-revision records an explicit harness revision.

The old local candidate-construction helpers are excluded from the release. They reference retained development workspaces and are not part of the public replay command. No provider reruns, future-wave work or analytical method changes are authorized by these instructions.
