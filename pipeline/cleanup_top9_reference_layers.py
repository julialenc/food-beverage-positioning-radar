"""Clean Top-9 reference layers without changing locked product results.

This is a maintenance utility for the post-audit reference cleanup described in
docs/BRAND_COMPANY_MAPPING.md. It snapshots the current Streamlit-facing
product mapping, cleans duplicate/unsafe reusable reference rows, regenerates
the standard Top-9 extract from SQLite, and validates pre/post equality.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
import argparse
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "data" / "reference"
REVIEW_DIR = ROOT / "data" / "brand_mapping_review"
DB_PATH = ROOT / "database" / "positioning_radar.db"

ALIAS_PATH = REFERENCE_DIR / "brand_alias_mapping.csv"
COMPANY_PATH = REFERENCE_DIR / "company_brand_mapping.csv"
MATRIX_PATH = REFERENCE_DIR / "top_company_brand_portfolio_matrix.csv"
OVERRIDE_PATH = REFERENCE_DIR / "reviewed_product_mapping_overrides.csv"

PRE_TOP9_PATH = REVIEW_DIR / "top9_reference_cleanup_pre_top9_current.csv"
POST_TOP9_PATH = REVIEW_DIR / "top9_reference_cleanup_post_top9_current.csv"
TOP9_EXTRACT_PATH = REVIEW_DIR / "top9_product_level_audit_current.csv"
PRE_UNIVERSE_PATH = REVIEW_DIR / "top9_reference_cleanup_pre_mapped_universe.csv"
POST_UNIVERSE_PATH = REVIEW_DIR / "top9_reference_cleanup_post_mapped_universe.csv"

TOP9_COMPANIES = {
    "Nestlé",
    "PepsiCo",
    "PepsiCo (NACP)",
    "The Coca-Cola Company",
    "Mondelēz International",
    "Danone",
    "Kraft Heinz",
    "The Hershey Company",
    "Starbucks",
    "Starbucks Coffee Company",
    "Unilever",
}
REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}
CATEGORIES = {"snacks", "beverages", "cereals", "dairies"}
COMPANY_OTHER = "Other / not mapped to a company"
COMPANY_MANUAL = "Manual review"

ALIAS_PRESERVE = {
    "hershey's kisses": "Hershey's Kisses",
    "reese's puffs": "Reese's Puffs",
    "starbucks via": "Starbucks VIA",
    "starbucks by nespresso": "Starbucks by Nespresso",
    "kraft singles": "Kraft Singles",
    "cadbury dairy milk": "Cadbury Dairy Milk",
    "core power": "Core Power",
    "honest kids": "Honest Kids",
}

STALE_COMPANY_ROUTES = {
    ("wyler's", "Kraft Heinz"),
    ("scharffen berger", "The Hershey Company"),
    ("trident", "Mondelēz International"),
    ("tropicana", "PepsiCo"),
    ("fulfil", "The Hershey Company"),
    ("reese's puffs", "The Hershey Company"),
    ("maxwell house", "Kraft Heinz"),
    ("philadelphia", "Kraft Heinz"),
    ("gevalia", "Kraft Heinz"),
    ("capri sun", "Kraft Heinz"),
    ("kraft cheese", "Kraft Heinz"),
    ("starbucks", "Starbucks Coffee Company"),
    ("starbucks rtd", "PepsiCo (NACP)"),
    ("starbucks rtd", "Arla Foods"),
    ("lipton dry tea", "Unilever"),
    ("royco europe", "Unilever"),
}

UNILEVER_ICE_CREAM = {
    "ben & jerry's",
    "breyers",
    "carte d'or",
    "cornetto",
    "magnum ice cream",
    "miko",
    "solero",
    "viennetta",
    "wall's ice cream",
}


def text_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold()).strip()


def route_key(value: str) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_scope(value: str) -> str:
    return "|".join(v.strip() for v in str(value or "").split("|") if v.strip())


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def load_overrides() -> dict[str, list[dict[str, str]]]:
    if not OVERRIDE_PATH.exists():
        return {}
    overrides: dict[str, list[dict[str, str]]] = defaultdict(list)
    with OVERRIDE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("status", "").strip().lower() != "active":
                continue
            gtin = row.get("gtin", "").strip()
            if not gtin:
                continue
            overrides[gtin].append(
                {
                    "region": row.get("region", "").strip(),
                    "brand": row.get("reviewed_brand", "").strip(),
                    "company": row.get("reviewed_company", "").strip(),
                    "category": row.get("reviewed_category", "").strip(),
                }
            )
    return dict(overrides)


def override_for(
    overrides: dict[str, list[dict[str, str]]],
    gtin: str,
    region: str,
) -> dict[str, str] | None:
    candidates = overrides.get(str(gtin or "").strip()) or []
    unscoped = None
    for candidate in candidates:
        candidate_region = candidate.get("region", "")
        if not candidate_region:
            unscoped = candidate
        elif candidate_region == region:
            return candidate
    return unscoped


def export_current_mapping(output_path: Path, *, top9_only: bool) -> pd.DataFrame:
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    latest = conn.execute("select max(ingested_at) from products").fetchone()[0]
    base = pd.read_sql_query(
        """
        select
            barcode as gtin,
            product_name as product,
            query_category as category,
            coalesce(nullif(trim(normalized_brand), ''), primary_brand) as brand,
            resolved_company as company,
            observed_market_region_codes as region_codes
        from products
        where ingested_at = ?
        """,
        conn,
        params=[latest],
        dtype={"gtin": str},
    ).fillna("")
    conn.close()

    overrides = load_overrides()
    records = []
    for gtin, product, category, brand, company, region_codes in base.itertuples(
        index=False, name=None
    ):
        for region in [v.strip() for v in str(region_codes).split("|") if v.strip()]:
            if region not in REGIONS:
                continue
            row = {
                "region": region,
                "category": category,
                "company": company,
                "brand": brand,
                "gtin": str(gtin),
                "product": product,
            }
            reviewed = override_for(overrides, str(gtin), region)
            if reviewed:
                row["brand"] = reviewed["brand"] or row["brand"]
                row["company"] = reviewed["company"] or row["company"]
                row["category"] = reviewed["category"] or row["category"]
            if row["category"] == "OUT_OF_SCOPE" or row["category"] not in CATEGORIES:
                continue
            if top9_only and row["company"] not in TOP9_COMPANIES:
                continue
            records.append(row)

    out = pd.DataFrame(
        records,
        columns=["region", "category", "company", "brand", "gtin", "product"],
    )
    out = out.sort_values(
        ["company", "region", "category", "brand", "product", "gtin"],
        kind="stable",
    )
    write_csv(out, output_path)
    return out


def snapshot_current() -> tuple[pd.DataFrame, pd.DataFrame]:
    if PRE_TOP9_PATH.exists() or PRE_UNIVERSE_PATH.exists():
        raise FileExistsError(
            "Pre-cleanup snapshots already exist; move them intentionally "
            "before taking a new cleanup baseline."
        )
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    top9 = export_current_mapping(PRE_TOP9_PATH, top9_only=True)
    universe = export_current_mapping(PRE_UNIVERSE_PATH, top9_only=False)
    return top9, universe


def concise_note(existing: str, fallback: str) -> str:
    parts = []
    for raw in re.split(r"\s*;\s*", str(existing or "")):
        text = raw.strip()
        if not text:
            continue
        if re.search(r"\bdisabled 2026-\d\d-\d\d\b", text, flags=re.I):
            continue
        if re.search(r"C:[/\\]Users[/\\]", text, flags=re.I):
            continue
        if text not in parts:
            parts.append(text)
    if not parts:
        parts.append(fallback)
    return "; ".join(parts[:3])


def clean_alias_mapping() -> dict[str, int]:
    before = read_csv(ALIAS_PATH)
    deduped = before.drop_duplicates(keep="first").copy()

    for col in ["variant_brand", "canonical_brand", "pattern", "action", "notes"]:
        deduped[col] = deduped[col].astype(str).str.strip()
    deduped["notes"] = deduped["notes"].map(
        lambda value: concise_note(
            value,
            "Non-executable guardrail; exact reviewed evidence required.",
        )
    )

    executable = deduped["action"].str.strip().str.lower().eq("confirm")
    work = deduped[executable].copy()
    work["_variant_key"] = work["variant_brand"].map(text_key)
    work["_canonical_key"] = work["canonical_brand"].map(text_key)

    demote_indices: set[int] = set()
    for key, group in work.groupby("_variant_key", sort=False):
        if group["_canonical_key"].nunique() <= 1:
            continue

        preserve = ALIAS_PRESERVE.get(key)
        keep_indices: list[int] = []
        if preserve:
            preserve_key = text_key(preserve)
            keep_indices = list(group[group["_canonical_key"].eq(preserve_key)].index[:1])

        if not keep_indices:
            self_rows = group[group["_canonical_key"].eq(key)]
            if not self_rows.empty:
                keep_indices = [self_rows.index[0]]

        if not keep_indices:
            non_prefix = group[
                ~group["pattern"].str.strip().str.lower().eq("prefix")
            ]
            if non_prefix["_canonical_key"].nunique() == 1 and not non_prefix.empty:
                keep_indices = [non_prefix.index[0]]

        for idx in group.index:
            if idx not in keep_indices:
                demote_indices.add(idx)

    if demote_indices:
        deduped.loc[list(demote_indices), "action"] = "manual_review"
        deduped.loc[list(demote_indices), "confidence"] = "review"
        deduped.loc[list(demote_indices), "notes"] = (
            "Non-executable guardrail; exact reviewed evidence required."
        )

    write_csv(deduped, ALIAS_PATH)
    return {
        "rows_before": len(before),
        "rows_after": len(deduped),
        "exact_duplicates_removed": len(before) - len(deduped),
        "demoted_conflicting_confirm_rows": len(demote_indices),
    }


def is_manual_company_row(row: pd.Series) -> bool:
    status = str(row.get("ownership_resolution_status", "")).strip().lower()
    parent = str(row.get("parent_company", "")).strip().lower()
    needs = str(row.get("needs_manual_review", "")).strip().lower()
    return (
        status == "manual_review"
        or status.startswith("reviewed_not")
        or parent == COMPANY_MANUAL.lower()
        or needs == "yes"
    )


def company_row_executable(row: pd.Series) -> bool:
    if is_manual_company_row(row):
        return False
    status = str(row.get("ownership_resolution_status", "")).strip().lower() or "direct"
    parent = str(row.get("parent_company", "")).strip()
    return bool(parent and status in {
        "direct",
        "recently_demerged",
        "recently_sold_or_spun_off",
        "licensed_or_partnered",
        "market_scoped",
    })


def company_executable_key(row: pd.Series) -> tuple[str, str, str, str, str, str]:
    category = str(row.get("category_scope") or row.get("category") or "").strip().lower()
    return (
        route_key(row.get("primary_brand_db") or row.get("normalized_brand") or row.get("brand")),
        category,
        compact_scope(row.get("country_tags_include", "")),
        compact_scope(row.get("country_tags_exclude", "")),
        compact_scope(row.get("region_codes_include", "")),
        compact_scope(row.get("region_codes_exclude", "")),
    )


def demote_company_rows(df: pd.DataFrame, indices: set[int]) -> None:
    if not indices:
        return
    idx = list(indices)
    df.loc[idx, "ownership_resolution_status"] = "manual_review"
    df.loc[idx, "needs_manual_review"] = "yes"
    df.loc[idx, "review_note"] = (
        "Non-executable guardrail; exact reviewed/scoped evidence required."
    )
    df.loc[idx, "source_note"] = df.loc[idx, "source_note"].map(
        lambda value: concise_note(
            value,
            "Reference cleanup guardrail; not an automatic company assignment.",
        )
    )


def merge_text_values(values: list[str], fallback: str = "") -> str:
    parts: list[str] = []
    for value in values:
        text = concise_note(value, "").strip()
        if text and text not in parts:
            parts.append(text)
    if not parts and fallback:
        parts.append(fallback)
    return "; ".join(parts[:4])


def company_duplicate_keep_index(group: pd.DataFrame) -> int:
    """Prefer later reviewed/scoped rows when duplicate executable keys agree."""
    def score(row: pd.Series) -> tuple[int, int, int, int]:
        source = str(row.get("brand_mapping_source", "")).lower()
        status = str(row.get("ownership_resolution_status", "")).lower()
        reviewed = int(any(token in source for token in ["top9", "step3", "audit"]))
        layer3 = int("layer3" not in source)
        scoped = int(status == "market_scoped")
        note_len = len(str(row.get("review_note", "")))
        return (reviewed, layer3, scoped, note_len)

    ranked = sorted(group.index, key=lambda idx: score(group.loc[idx]), reverse=True)
    return int(ranked[0])


def micro_cleanup_company_mapping() -> dict[str, int]:
    """Final company-only cleanup: no Manual-review owner labels, no same-owner dupes."""
    before = read_csv(COMPANY_PATH)
    df = before.copy()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    manual_parent_mask = df["parent_company"].eq(COMPANY_MANUAL)
    eligible_manual_parent = manual_parent_mask & df.apply(is_manual_company_row, axis=1)
    if int(manual_parent_mask.sum()) != int(eligible_manual_parent.sum()):
        raise ValueError(
            "Some parent_company=Manual review rows are not non-executable; "
            "leaving the CSV unchanged."
        )
    df.loc[eligible_manual_parent, "parent_company"] = COMPANY_OTHER

    executable = df[df.apply(company_row_executable, axis=1)].copy()
    executable["_dup_key"] = executable.apply(
        lambda row: (company_executable_key(row), row["parent_company"]),
        axis=1,
    )
    duplicate_groups = [
        group for _, group in executable.groupby("_dup_key", sort=False)
        if len(group) > 1
    ]

    drop_indices: set[int] = set()
    for group in duplicate_groups:
        keep = company_duplicate_keep_index(group)
        merge_indices = [idx for idx in group.index if idx != keep]
        drop_indices.update(merge_indices)
        for col in ["notes", "source_note", "review_note", "product_scope_note"]:
            if col in df.columns:
                df.at[keep, col] = merge_text_values(
                    [df.at[keep, col], *[df.at[idx, col] for idx in merge_indices]]
                )
        if "brand_mapping_source" in df.columns:
            df.at[keep, "brand_mapping_source"] = merge_text_values(
                [
                    df.at[keep, "brand_mapping_source"],
                    *[df.at[idx, "brand_mapping_source"] for idx in merge_indices],
                ]
            )

    if drop_indices:
        df = df.drop(index=sorted(drop_indices)).reset_index(drop=True)

    write_csv(df, COMPANY_PATH)
    return {
        "rows_before": len(before),
        "rows_after": len(df),
        "manual_review_parent_rows_relabelled": int(eligible_manual_parent.sum()),
        "duplicate_executable_groups_consolidated": len(duplicate_groups),
        "duplicate_executable_rows_removed": len(drop_indices),
    }


def clean_company_mapping() -> dict[str, int]:
    before = read_csv(COMPANY_PATH)
    deduped = before.drop_duplicates(keep="first").copy()

    for col in deduped.columns:
        deduped[col] = deduped[col].astype(str).str.strip()
    for col in ["notes", "source_note", "review_note", "product_scope_note"]:
        if col in deduped.columns:
            deduped[col] = deduped[col].map(
                lambda value: concise_note(
                    value,
                    "Current-state reference row.",
                )
            )

    stale_indices = set()
    for idx, row in deduped.iterrows():
        brand_key = route_key(row.get("primary_brand_db") or row.get("normalized_brand") or row.get("brand"))
        parent = row.get("parent_company", "").strip()
        if (brand_key, parent) in STALE_COMPANY_ROUTES and company_row_executable(row):
            stale_indices.add(idx)
        if parent == "Unilever" and brand_key in UNILEVER_ICE_CREAM and company_row_executable(row):
            stale_indices.add(idx)
        if parent in {"Unilever Foods", "Liptea / Ekaterra", "Coca-Cola"}:
            if parent == "Unilever Foods":
                deduped.at[idx, "parent_company"] = "Unilever"
            elif parent == "Liptea / Ekaterra":
                deduped.at[idx, "parent_company"] = "LIPTON Teas and Infusions / Ekaterra"
            elif parent == "Coca-Cola":
                deduped.at[idx, "parent_company"] = "The Coca-Cola Company"

    demote_company_rows(deduped, stale_indices)

    for idx, row in deduped.iterrows():
        status = str(row.get("ownership_resolution_status", "")).strip().lower()
        parent = str(row.get("parent_company", "")).strip().lower()
        if status.startswith("reviewed_not"):
            deduped.at[idx, "ownership_resolution_status"] = "manual_review"
            deduped.at[idx, "needs_manual_review"] = "yes"
        elif status == "manual_review" or parent == COMPANY_MANUAL.lower():
            deduped.at[idx, "needs_manual_review"] = "yes"
        elif deduped.at[idx, "needs_manual_review"].strip().lower() == "yes":
            deduped.at[idx, "needs_manual_review"] = "no"

    conflict_indices: set[int] = set()
    work = deduped[deduped.apply(company_row_executable, axis=1)].copy()
    work["_key"] = work.apply(company_executable_key, axis=1)
    for _, group in work.groupby("_key", sort=False):
        if group["parent_company"].nunique() > 1:
            conflict_indices.update(group.index)
    demote_company_rows(deduped, conflict_indices)

    write_csv(deduped, COMPANY_PATH)
    return {
        "rows_before": len(before),
        "rows_after": len(deduped),
        "exact_duplicates_removed": len(before) - len(deduped),
        "stale_routes_demoted": len(stale_indices),
        "conflicting_executable_rows_demoted": len(conflict_indices),
    }


def cleanup_source_value(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(
        r"C:[/\\]Users[/\\][^;|,\n]+[/\\]Downloads_temp[/\\]([^;|,\n]+)",
        r"\1",
        text,
        flags=re.I,
    )
    text = re.sub(r"C:/Users/julia/OneDrive/Desktop/Downloads_temp/", "", text, flags=re.I)
    text = text.replace("Nestle", "Nestlé")
    text = text.replace("Mondelez International", "Mondelēz International")
    text = text.replace("Liptea / Ekaterra", "LIPTON Teas and Infusions / Ekaterra")
    return concise_note(text, "")


def clean_matrix() -> dict[str, int]:
    before = read_csv(MATRIX_PATH)
    matrix = before.drop_duplicates(keep="first").copy()
    assignment_cols = [
        "default_assigned_company",
        "us_assigned_company",
        "ca_assigned_company",
        "uk_assigned_company",
        "ie_assigned_company",
        "fr_assigned_company",
    ]

    for col in matrix.columns:
        matrix[col] = matrix[col].astype(str).str.strip()
        matrix[col] = matrix[col].map(cleanup_source_value)

    ice_mask = matrix["brand"].map(route_key).isin({route_key(v) for v in UNILEVER_ICE_CREAM})
    matrix.loc[ice_mask, assignment_cols] = "The Magnum Ice Cream Company"
    matrix.loc[ice_mask, "ownership_resolution_status"] = "recently_demerged"
    matrix.loc[ice_mask, "needs_manual_review"] = "no"
    matrix.loc[ice_mask, "ownership_architecture_notes"] = (
        "Current ice-cream operating owner is The Magnum Ice Cream Company."
    )

    tea_mask = matrix["brand"].map(route_key).eq("lipton dry tea")
    matrix.loc[tea_mask, assignment_cols] = "LIPTON Teas and Infusions / Ekaterra"
    matrix.loc[tea_mask, "ownership_resolution_status"] = "manual_review"
    matrix.loc[tea_mask, "needs_manual_review"] = "yes"
    matrix.loc[tea_mask, "ownership_architecture_notes"] = (
        "Former Unilever tea architecture; exact reviewed/scoped evidence required."
    )

    rtd_keys = {
        "starbucks rtd",
        "starbucks chilled frappuccino",
        "starbucks doubleshot canned",
    }
    rtd_mask = matrix["brand"].map(route_key).isin(rtd_keys)
    matrix.loc[rtd_mask, "default_assigned_company"] = ""
    matrix.loc[rtd_mask, "us_assigned_company"] = "PepsiCo (NACP)"
    matrix.loc[rtd_mask, "ca_assigned_company"] = "PepsiCo (NACP)"
    matrix.loc[rtd_mask, "uk_assigned_company"] = "Arla Foods"
    matrix.loc[rtd_mask, "ie_assigned_company"] = "Arla Foods"
    matrix.loc[rtd_mask, "fr_assigned_company"] = "Arla Foods"
    matrix.loc[rtd_mask, "ownership_resolution_status"] = "manual_review"
    matrix.loc[rtd_mask, "needs_manual_review"] = "yes"
    matrix.loc[rtd_mask, "ownership_architecture_notes"] = (
        "Starbucks RTD is product-form and market scoped; exact reviewed/scoped evidence required."
    )

    at_home_keys = {
        "starbucks k cup",
        "starbucks via soluble",
        "starbucks whole bean",
        "starbucks coffee at home",
    }
    at_home_mask = matrix["brand"].map(route_key).isin(at_home_keys)
    matrix.loc[at_home_mask, assignment_cols] = "Nestlé"
    matrix.loc[at_home_mask, "ownership_architecture_notes"] = (
        "Reviewed at-home packaged coffee/capsule/instant route."
    )

    write_csv(matrix, MATRIX_PATH)
    local_paths = int(
        matrix.apply(
            lambda col: col.astype(str).str.contains(r"C:[/\\]Users[/\\]", case=False, regex=True).any()
        ).any()
    )
    return {
        "rows_before": len(before),
        "rows_after": len(matrix),
        "exact_duplicates_removed": len(before) - len(matrix),
        "local_path_cells_remaining": local_paths,
        "ice_cream_rows_corrected": int(ice_mask.sum()),
        "starbucks_rtd_rows_corrected": int(rtd_mask.sum()),
    }


def validate_overrides() -> dict[str, int]:
    df = read_csv(OVERRIDE_PATH)
    active = df[df["status"].str.strip().str.lower().eq("active")].copy()
    keys = active[["gtin", "region"]].apply(tuple, axis=1)
    duplicates = int(keys.duplicated(keep=False).sum())
    decision_cols = ["reviewed_brand", "reviewed_company", "reviewed_category"]
    conflicts = 0
    for _, group in active.groupby(["gtin", "region"], dropna=False):
        if group[decision_cols].drop_duplicates().shape[0] > 1:
            conflicts += 1
    return {
        "rows": len(df),
        "active": len(active),
        "duplicate_key_rows": duplicates,
        "conflicting_keys": conflicts,
    }


def validate_aliases() -> dict[str, int]:
    df = read_csv(ALIAS_PATH)
    exact_duplicates = int(df.duplicated(keep=False).sum())
    exe = df[df["action"].str.strip().str.lower().eq("confirm")].copy()
    exe["_variant_key"] = exe["variant_brand"].map(text_key)
    exe["_canonical_key"] = exe["canonical_brand"].map(text_key)
    conflicts = int((exe.groupby("_variant_key")["_canonical_key"].nunique() > 1).sum())
    return {
        "rows": len(df),
        "exact_duplicate_rows": exact_duplicates,
        "conflicting_executable_alias_groups": conflicts,
    }


def validate_company() -> dict[str, int]:
    df = read_csv(COMPANY_PATH)
    exact_duplicates = int(df.duplicated(keep=False).sum())
    exe = df[df.apply(company_row_executable, axis=1)].copy()
    exe["_key"] = exe.apply(company_executable_key, axis=1)
    conflicts = int((exe.groupby("_key")["parent_company"].nunique() > 1).sum())
    return {
        "rows": len(df),
        "exact_duplicate_rows": exact_duplicates,
        "conflicting_executable_owner_groups": conflicts,
    }


def validate_matrix() -> dict[str, int]:
    df = read_csv(MATRIX_PATH)
    local_path_cells = 0
    for col in df.columns:
        local_path_cells += int(
            df[col].astype(str).str.contains(r"C:[/\\]Users[/\\]", case=False, regex=True).sum()
        )

    stale = 0
    assignment_cols = [
        "default_assigned_company",
        "us_assigned_company",
        "ca_assigned_company",
        "uk_assigned_company",
        "ie_assigned_company",
        "fr_assigned_company",
    ]
    for _, row in df.iterrows():
        brand_key = route_key(row.get("brand", ""))
        if brand_key in {route_key(v) for v in UNILEVER_ICE_CREAM}:
            stale += sum(row.get(col, "") == "Unilever" for col in assignment_cols)
        if brand_key == "lipton dry tea":
            stale += sum(row.get(col, "") == "Unilever" for col in assignment_cols)
        if brand_key in {"starbucks rtd", "starbucks chilled frappuccino", "starbucks doubleshot canned"}:
            stale += sum(row.get(col, "") == "PepsiCo (NACP)" for col in ["uk_assigned_company", "ie_assigned_company", "fr_assigned_company"])
    return {
        "rows": len(df),
        "local_absolute_path_cells": local_path_cells,
        "known_stale_assignment_cells": stale,
    }


def row_counter(df: pd.DataFrame) -> Counter[tuple[str, ...]]:
    return Counter(tuple(map(str, row)) for row in df.itertuples(index=False, name=None))


def compare_row_sets(before_path: Path, after_path: Path) -> dict[str, int]:
    before = read_csv(before_path)
    after = read_csv(after_path)
    before_counter = row_counter(before)
    after_counter = row_counter(after)
    added = +(after_counter - before_counter)
    removed = +(before_counter - after_counter)
    return {
        "rows_before": len(before),
        "rows_after": len(after),
        "unique_gtins_after": after["gtin"].nunique() if "gtin" in after.columns else 0,
        "added_rows": sum(added.values()),
        "removed_rows": sum(removed.values()),
    }


def restore_db_from_pre_snapshot() -> int:
    """Restore Streamlit-facing derived product mapping from the frozen baseline."""
    if not PRE_UNIVERSE_PATH.exists():
        raise FileNotFoundError(PRE_UNIVERSE_PATH)
    snapshot = read_csv(PRE_UNIVERSE_PATH)
    snapshot = snapshot.sort_values(
        ["gtin", "region", "company", "brand", "category"],
        kind="stable",
    )
    # The products table is GTIN keyed. Region-specific exceptions are still
    # applied by reviewed_product_mapping_overrides.csv at display/export time.
    per_gtin = snapshot.drop_duplicates("gtin", keep="first")
    updates = [
        (
            row["gtin"],
            row["brand"],
            row["brand"],
            row["company"],
            None if row["category"] == "OUT_OF_SCOPE" else row["category"],
        )
        for _, row in per_gtin.iterrows()
    ]
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("drop table if exists temp_restore_product_mapping")
        conn.execute(
            """
            create temp table temp_restore_product_mapping (
                barcode text primary key,
                normalized_brand text,
                primary_brand text,
                resolved_company text,
                query_category text
            )
            """
        )
        conn.executemany(
            """
            insert into temp_restore_product_mapping (
                barcode,
                normalized_brand,
                primary_brand,
                resolved_company,
                query_category
            ) values (?, ?, ?, ?, ?)
            """,
            updates,
        )
        conn.execute(
            """
            update products
            set
                normalized_brand = (
                    select normalized_brand
                    from temp_restore_product_mapping
                    where barcode = products.barcode
                ),
                primary_brand = (
                    select primary_brand
                    from temp_restore_product_mapping
                    where barcode = products.barcode
                ),
                resolved_company = (
                    select resolved_company
                    from temp_restore_product_mapping
                    where barcode = products.barcode
                ),
                query_category = (
                    select query_category
                    from temp_restore_product_mapping
                    where barcode = products.barcode
                )
            where exists (
                select 1
                from temp_restore_product_mapping
                where barcode = products.barcode
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    return len(updates)


def run_cleanup() -> None:
    top9, universe = snapshot_current()
    alias_stats = clean_alias_mapping()
    company_stats = clean_company_mapping()
    matrix_stats = clean_matrix()

    post_top9 = export_current_mapping(POST_TOP9_PATH, top9_only=True)
    write_csv(post_top9, TOP9_EXTRACT_PATH)
    export_current_mapping(POST_UNIVERSE_PATH, top9_only=False)

    print("Pre-cleanup Top-9 rows:", len(top9))
    print("Pre-cleanup Top-9 unique GTINs:", top9["gtin"].nunique())
    print("Pre-cleanup mapped universe rows:", len(universe))
    print("Alias cleanup:", alias_stats)
    print("Company cleanup:", company_stats)
    print("Matrix cleanup:", matrix_stats)
    print("Overrides validation:", validate_overrides())
    print("Alias validation:", validate_aliases())
    print("Company validation:", validate_company())
    print("Matrix validation:", validate_matrix())
    print("Top-9 equality:", compare_row_sets(PRE_TOP9_PATH, POST_TOP9_PATH))
    print("Mapped-universe equality:", compare_row_sets(PRE_UNIVERSE_PATH, POST_UNIVERSE_PATH))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run structural validations and pre/post equality checks only.",
    )
    parser.add_argument(
        "--restore-db-from-pre",
        action="store_true",
        help="Restore derived product mapping fields from the frozen pre-cleanup universe.",
    )
    parser.add_argument(
        "--micro-clean-company",
        action="store_true",
        help="Relabel non-executable Manual review owner placeholders and consolidate same-owner executable duplicate keys.",
    )
    args = parser.parse_args()
    if args.micro_clean_company:
        print("Company micro-cleanup:", micro_cleanup_company_mapping())
    elif args.restore_db_from_pre:
        count = restore_db_from_pre_snapshot()
        print(f"Restored derived product mapping fields for {count:,} GTINs")
    elif args.validate_only:
        export_current_mapping(POST_TOP9_PATH, top9_only=True)
        export_current_mapping(POST_UNIVERSE_PATH, top9_only=False)
        print("Overrides validation:", validate_overrides())
        print("Alias validation:", validate_aliases())
        print("Company validation:", validate_company())
        print("Matrix validation:", validate_matrix())
        print("Top-9 equality:", compare_row_sets(PRE_TOP9_PATH, POST_TOP9_PATH))
        print("Mapped-universe equality:", compare_row_sets(PRE_UNIVERSE_PATH, POST_UNIVERSE_PATH))
    else:
        run_cleanup()
