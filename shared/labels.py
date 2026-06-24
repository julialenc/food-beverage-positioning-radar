"""
Loads the canonical stored-code -> display-label mappings directly from
docs/UI_LABELS.md, instead of duplicating them as a second hardcoded
dict in Python. docs/UI_LABELS.md remains the single source of truth
(per its own "Implementation note" / "Rule" sections) — this module's
only job is to parse it faithfully and fail loudly if it can't.

Why fail loudly rather than fall back: the no-blame brief is explicit
that raw stored codes (FUNCTIONAL, sugar_above_reference, etc.) must
never reach the UI directly. A silently-skipped or silently-defaulted
mapping is exactly the failure mode that would let a raw code leak
through, so this module raises instead of guessing.

If UI_LABELS.md is revised (new code added, label wording changed),
nothing in this file needs to change — it re-reads the file at most
once per process (see lru_cache) and just needs the table format
(`| `code` | label |`) and section headers to stay the same.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_LABELS_PATH = REPO_ROOT / "docs" / "UI_LABELS.md"

# Maps the table key the app asks for -> the exact section header in
# UI_LABELS.md. If that file's headers ever change, update here.
_SECTION_HEADERS = {
    "claim_category_1": "## claim_category_1",
    "claim_category_2": "## claim_category_2",
    "nutrition_benchmark_flags": "## nutrition_benchmark_flags",
}

# Matches a markdown table data row of the form: | `code` | Display label |
# (skips the header row and the |---|---| separator row, neither of
# which has a `code` token wrapped in backticks).
_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*$")


class UILabelsError(RuntimeError):
    """Raised when docs/UI_LABELS.md is missing, malformed, or doesn't
    have an entry for a code the app is trying to display. Deliberately
    not caught anywhere in the app — see module docstring."""


def _parse_section(lines: list[str], header: str) -> dict[str, str]:
    try:
        start = lines.index(header)
    except ValueError:
        raise UILabelsError(
            f"UI_LABELS.md is missing the expected section header "
            f"'{header}'. Either the file was restructured (update "
            f"shared/labels.py to match) or it needs to be restored."
        )
    mapping: dict[str, str] = {}
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break  # reached the next section
        match = _ROW_RE.match(line.strip())
        if match:
            code, label = match.groups()
            mapping[code] = label
    if not mapping:
        raise UILabelsError(
            f"Parsed zero rows out of the '{header}' section of "
            f"UI_LABELS.md — the table format may have changed."
        )
    return mapping


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict[str, str]]:
    if not UI_LABELS_PATH.exists():
        raise UILabelsError(
            f"docs/UI_LABELS.md not found at {UI_LABELS_PATH}. This file "
            f"is the canonical source for every claim/benchmark label "
            f"this app shows — without it, the app refuses to display "
            f"raw stored codes as a substitute."
        )
    lines = UI_LABELS_PATH.read_text(encoding="utf-8").splitlines()
    return {key: _parse_section(lines, header) for key, header in _SECTION_HEADERS.items()}


def label_for(table: str, code: Optional[str]) -> str:
    """Look up the display label for a single stored code.

    `table` is one of 'claim_category_1', 'claim_category_2',
    'nutrition_benchmark_flags'. For claim_category_2, a None/empty
    code is treated as the explicit 'none' code ("No subcategory"),
    matching how tag_claims.py and UI_LABELS.md model "no subcategory"
    as a real value rather than an absence.
    """
    if not code and table == "claim_category_2":
        code = "none"
    mapping = _load_all()[table]
    if code not in mapping:
        raise UILabelsError(
            f"No display label found for {table} code '{code}' in "
            f"UI_LABELS.md. Add it there first, then this lookup will "
            f"pick it up automatically — this app does not fall back "
            f"to showing the raw code."
        )
    return mapping[code]


def labels_for_pipe_list(table: str, value: Optional[str]) -> list[str]:
    """Expands a pipe-separated stored value, for example:
    nutrition_benchmark_flags = 'sugar_above_reference|salt_above_reference'.

    Returns [] for None/empty/NaN input — callers render that as "none
    found", distinct from an unmapped code, which raises. NaN (not just
    None) has to be handled explicitly here: pandas returns NaN, not
    None, for a NULL TEXT column read via read_sql_query in at least
    some cases (confirmed against the actual products/product_analysis
    join), and float has no .split()."""
    if value is None:
        return []

    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return []

    return [label_for(table, code.strip()) for code in text.split("|") if code.strip()]


def safe_label_for(table: str, code: Optional[str], fallback: str = "—") -> str:
    """UI-safe label lookup for display contexts (the product table and
    detail card) where one malformed value should degrade gracefully
    rather than take down the page — unlike label_for(), which stays
    strict for QA scripts and tests. Never returns the raw stored code;
    an unmapped or missing code becomes `fallback`, not the code itself.

    Caveat: unlike label_for(), a None code here always returns
    `fallback` rather than resolving claim_category_2's "none" ->
    "No subcategory" special case, since fallback is checked before
    label_for() is ever called. Not currently reachable in practice —
    every call site already skips calling this when claim_category_2
    is None — but worth knowing if that changes.

    Use label_for() directly wherever an unmapped code should be
    treated as a bug to fix (QA scripts, tests, validate_tags.py-style
    tooling), not papered over."""
    if code is None:
        return fallback

    text = str(code).strip()
    if text == "" or text.lower() == "nan":
        return fallback

    try:
        return label_for(table, text)
    except UILabelsError:
        return fallback


def safe_labels_for_pipe_list(
    table: str, value: Optional[str], fallback: str = "Unmapped reference flag"
) -> list[str]:
    """UI-safe version of labels_for_pipe_list() — an unmapped code
    inside the pipe-separated value becomes `fallback` instead of
    raising, so one bad code doesn't blank out every other (valid)
    flag on the same product. See safe_label_for() for the rationale."""
    if value is None:
        return []

    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return []

    resolved: list[str] = []
    for code in text.split("|"):
        code = code.strip()
        if not code:
            continue
        try:
            resolved.append(label_for(table, code))
        except UILabelsError:
            resolved.append(fallback)
    return resolved


def all_options(table: str) -> dict[str, str]:
    """Full code -> label mapping for a table, e.g. for populating a
    filter dropdown with display labels while keeping the underlying
    codes available for the actual database query."""
    return dict(_load_all()[table])
