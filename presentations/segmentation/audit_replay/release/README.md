# v1.0.0 — segmentation replay

This release keeps repository source and data at their canonical paths. Only the 3.44 GiB governed database is compressed and split: four files under payload/, each below 100 MiB. The manifest names every distributed dependency and exact starting input. In its logical file inventory, source/ denotes the repository root; it is not a second physical copy.

From the repository root, use Python 3.12.4 and install the pinned analytical dependencies into a virtual environment:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r presentations/segmentation/audit_replay/requirements-replay.txt
.venv/Scripts/python.exe -B -u presentations/segmentation/audit_replay/replay.py --candidate-root presentations/segmentation/audit_replay/release --workspace outputs/release_replay
```

Use a new workspace. The command verifies the release manifest, restores the database there, and runs all 25 stages in isolation. It does not write to the accepted package. It uses no Git operations or provider calls. For file verification and streamed database-restoration checking without rerunning research:

```powershell
.venv/Scripts/python.exe -B -u presentations/segmentation/audit_replay/replay.py --candidate-root presentations/segmentation/audit_replay/release --verify-candidate --workspace outputs/release_verify
```

Git attributes preserve exact bytes of audit assets, governed contracts and frozen inputs. Text normalization is accepted only for explicitly identified ordinary legacy source/docs; fixed evidence never uses that fallback. The master is shipped as an ordinary 75.96 MiB Parquet. No uncompressed database is added to Git.

[Scope and file placement](SCOPE.md) · [Release notes](RELEASE_NOTES.md) · [Replay validation](CHECK.md) · [Machine validation](VALIDATION.json) · [Manifest](manifest.json)

The 25-stage isolated run reused the declared installed environment; a fresh pip installation has not been certified. The final public tag/archive will receive a separate download check. This is the locally prepared first formal release, not a published tag.
