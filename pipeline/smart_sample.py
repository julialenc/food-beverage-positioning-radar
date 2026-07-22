"""
smart_sample.py — stratified enriched sampler for the clean OCR/LLM run.

COMPLETE REPLACEMENT of the original smart_sample.py, which was built
around composition_marker_score (now deprecated — see llm_sampling_design_log.md
and ADR.md). The design is fully documented in llm_sampling_design_log.md.

Current scope: US & Canada + UK & Ireland only.
France: deferred pending a French keyword dictionary for the positioning
proxy. See llm_sampling_design_log.md for the reasoning.

INPUTS (all pre-computed pipeline outputs — run these first):
  pipeline/positioning_signals_us_uk.csv  (detect_positioning_signals.py)
  pipeline/reality_bands.csv              (assign_reality_bands.py)
  pipeline/formulation_families.csv       (classify_formulation_families.py)
  database/positioning_radar.db           (for prompt calibration panel)

OUTPUTS:
  pipeline/sample_clean_run.csv           (selected products + full metadata)
  pipeline/sample_clean_run_summary.csv   (quota fill report)

THREE SAMPLING COMPONENTS per region-category:
  35% BACKBONE   -- proportional to formulation-family distribution, random
                    within family; exact inclusion probabilities; brand-capped.
  50% MATRIX     -- positioning(explicit/none) x reality(favorable/typical/
                    unfavorable) per priority territory; deliberately enriches
                    analytically important cells; approximate weights.
  15% CALIBRATION -- rare territory enrichment (immune/gut-health/fibre
                     formulation pools) + 5% prompt-comparison panel from
                     the prior ~5k LLM run.

DESIGN PRINCIPLES:
  - No exclusion of previously analyzed products -- clean run.
  - Formulation families used where available; positioning + reality bands
    are the primary strata for cereals (84% other = data sparsity + bootstrap
    contamination, not a classifier failure).
  - Territory-specific reality: "favorable" = high for protein/fibre,
    low for sugar/satfat/energy.
  - Zero-heavy bands (zero/positive_lower/positive_upper) mapped to
    low/typical/high for sampling purposes.
  - Exact weights for backbone; approximate/flagged for matrix and
    calibration (greedy multi-cell deduplication prevents exact calc).
  - Random seed 42, stored with every output row for reproducibility.

Usage: python pipeline/smart_sample.py [--seed 42] [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"

POSITIONING_CSV = Path(__file__).resolve().parent / "positioning_signals_us_uk.csv"
REALITY_CSV     = Path(__file__).resolve().parent / "reality_bands.csv"
FAMILIES_CSV    = Path(__file__).resolve().parent / "formulation_families.csv"
OUT_SAMPLE_CSV  = Path(__file__).resolve().parent / "sample_clean_run.csv"
OUT_SUMMARY_CSV = Path(__file__).resolve().parent / "sample_clean_run_summary.csv"

RANDOM_SEED = 42
RUN_ID      = "release-01-image-eligible"

IN_SCOPE_REGIONS = {"US_CANADA", "UK_IE"}

# -- Quota targets (products per region-category) ----------------------------
QUOTA_TARGET: dict[tuple[str, str], int] = {
    ("US_CANADA", "snacks"):    2450,
    ("US_CANADA", "dairies"):   2450,
    ("US_CANADA", "cereals"):   1400,
    ("US_CANADA", "beverages"):  700,
    ("UK_IE",     "snacks"):    2450,
    ("UK_IE",     "dairies"):   2450,
    ("UK_IE",     "cereals"):   1400,
    ("UK_IE",     "beverages"):  700,
}

COMPONENT_SPLIT = {"backbone": 0.35, "matrix": 0.50, "calibration": 0.15}

# Per category: territory priority order for matrix enrichment
TERRITORY_PRIORITY: dict[str, list[str]] = {
    "snacks":    ["protein", "fibre", "sugar", "satfat", "energy"],
    "dairies":   ["protein", "sugar", "satfat", "energy"],
    "cereals":   ["fibre", "sugar", "protein", "energy"],
    "beverages": ["sugar", "energy", "protein", "satfat"],
}

# territory -> (reality_band_column, favorable_direction)
TERRITORY_REALITY: dict[str, tuple[str, str]] = {
    "protein": ("protein_band", "high"),
    "fibre":   ("fibre_band",   "high"),
    "sugar":   ("sugars_band",  "low"),
    "satfat":  ("satfat_band",  "low"),
    "energy":  ("energy_band",  "low"),
}

# Matrix cell priority weights {(signal, reality_class): weight}
CELL_WEIGHTS: dict[tuple[str, str], float] = {
    ("explicit", "favorable"):   0.25,
    ("explicit", "typical"):     0.20,
    ("explicit", "unfavorable"): 0.20,
    ("none",     "favorable"):   0.25,
    ("none",     "typical"):     0.05,
    ("none",     "unfavorable"): 0.05,
}

MAX_BRAND_SHARE          = 0.15
CALIBRATION_PANEL_SHARE  = 0.05


# -- Helpers -----------------------------------------------------------------

def load_inputs() -> pd.DataFrame:
    pos = pd.read_csv(POSITIONING_CSV)
    rea = pd.read_csv(REALITY_CSV)
    fam = pd.read_csv(FAMILIES_CSV)
    for df in (pos, rea, fam):
        df["barcode"] = df["barcode"].astype(str)

    # The pre-computed CSVs contain signal/band/family columns but not the
    # product-level fields needed for scope filtering and brand-capping.
    # Load those directly from the DB so we don't depend on the CSVs
    # including every product field.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    product_fields = pd.read_sql_query("""
        SELECT barcode, product_name, primary_brand, query_category AS category,
               observed_market_region_codes, image_url
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
          AND image_url IS NOT NULL
          AND TRIM(image_url) <> ''
          AND LOWER(TRIM(image_url)) NOT IN ('nan', 'none', 'null')
          AND (
              LOWER(TRIM(image_url)) LIKE 'http://%'
              OR LOWER(TRIM(image_url)) LIKE 'https://%'
          )
    """, conn)
    # image_url filter is intentional: products without a usable image URL are
    # not eligible for front-of-pack claim analysis. They are still valid for
    # nutrition/landscape/ingredient analysis — they are simply excluded from
    # the OCR/LLM sampling universe. See notes_data_quality_local.md and the
    # us_release_sample_preflight.csv QA archive for the coverage breakdown.
    conn.close()
    product_fields["barcode"] = product_fields["barcode"].astype(str)

    # Drop category/region columns from CSVs that duplicate the DB version —
    # after pandas merges, duplicated column names become _x/_y suffixes which
    # breaks downstream lookups. product_fields from the DB is the authoritative
    # source for category and observed_market_region_codes.
    rea_clean = rea.drop(columns=[c for c in ("category", "region_code",
                                               "observed_market_region_codes")
                                   if c in rea.columns])
    pos_clean = pos.drop(columns=[c for c in ("category", "query_category",
                                               "observed_market_region_codes")
                                   if c in pos.columns])

    merged = (rea_clean
              .merge(pos_clean, on="barcode", how="left")
              .merge(fam[["barcode", "formulation_family", "family_source",
                           "family_rule_version"]].rename(
                               columns={"family_rule_version": "family_rule_ver"}),
                     on="barcode", how="left")
              .merge(product_fields, on="barcode", how="inner"))

    def primary_region(codes):
        for c in str(codes or "").split("|"):
            if c in IN_SCOPE_REGIONS:
                return c
        return None

    merged["primary_region"] = merged["observed_market_region_codes"].apply(
        primary_region)
    merged["pre_llm_positioning_signal"] = merged[
        "pre_llm_positioning_signal"].fillna("none")
    merged["formulation_family"] = merged["formulation_family"].fillna(
        "other_" + merged["category"])
    return merged[merged["primary_region"].notna()].copy()


def normalize_band(band) -> str | None:
    if pd.isna(band) or band is None:
        return None
    b = str(band)
    mapping = {"zero": "low", "positive_lower": "typical",
               "positive_upper": "high"}
    return mapping.get(b, b if b in ("low", "typical", "high") else None)


def get_reality_class(row: pd.Series, territory: str) -> str:
    band_col, favorable_dir = TERRITORY_REALITY[territory]
    band = normalize_band(row.get(band_col))
    if band is None:
        return "unknown"
    if band == favorable_dir:
        return "favorable"
    if band in ("low", "high"):
        return "unfavorable"
    return "typical"


def has_territory_signal(row: pd.Series, territory: str) -> bool:
    terrs = str(row.get("pre_llm_positioning_territories") or "")
    return territory in terrs.split("|")


def apply_brand_cap(df: pd.DataFrame, target_n: int,
                    rng: np.random.Generator) -> pd.DataFrame:
    max_per_brand = max(1, int(target_n * MAX_BRAND_SHARE))
    parts = []
    for _, grp in df.groupby("primary_brand", dropna=False):
        if len(grp) > max_per_brand:
            grp = grp.sample(max_per_brand, random_state=int(rng.integers(0, 2**31)))
        parts.append(grp)
    return pd.concat(parts) if parts else df.head(0)


# -- Component 1: backbone ---------------------------------------------------

def sample_backbone(df: pd.DataFrame, target_n: int,
                    rng: np.random.Generator) -> pd.DataFrame:
    df = apply_brand_cap(df, target_n, rng)
    family_counts = df["formulation_family"].value_counts()
    total = max(len(df), 1)
    parts = []
    for family, n_available in family_counts.items():
        proportion = n_available / total
        n_target = max(1, round(proportion * target_n))
        grp = df[df["formulation_family"] == family]
        n_draw = min(n_target, len(grp))
        sampled = grp.sample(n_draw, random_state=int(rng.integers(0, 2**31))).copy()
        sampled["sample_component"] = "backbone"
        sampled["primary_stratum_id"] = f"backbone|{family}"
        sampled["stratum_population_n"] = len(grp)
        sampled["stratum_target_n"] = n_draw
        sampled["inclusion_probability"] = n_draw / len(grp)
        sampled["sampling_weight"] = len(grp) / n_draw
        # Weights are approximate, not exact: the eligible pool is first
        # randomly brand-capped (apply_brand_cap), so the probability is
        # calculated relative to the post-cap pool, not the full eligible
        # region-category-family population. Use the backbone for prevalence
        # calibration but treat weights as approximate.
        sampled["weight_status"] = "approximate_brand_capped"
        sampled["sampling_reason"] = f"backbone: {family}"
        parts.append(sampled)
    if not parts:
        return pd.DataFrame()
    result = pd.concat(parts)
    if len(result) > target_n:
        result = result.sample(target_n, random_state=int(rng.integers(0, 2**31)))
    return result


# -- Component 2: matrix enrichment -----------------------------------------

def sample_matrix(df: pd.DataFrame, target_n: int, category: str,
                  rng: np.random.Generator,
                  already_selected: set) -> pd.DataFrame:
    territories = TERRITORY_PRIORITY.get(category, [])
    if not territories:
        return pd.DataFrame()

    n_per_territory = max(1, target_n // len(territories))
    parts = []
    selected_here: set = set()

    for territory in territories:
        band_col = TERRITORY_REALITY[territory][0]
        pool = df[
            (~df["barcode"].isin(already_selected))
            & (~df["barcode"].isin(selected_here))
            & df[band_col].notna()
        ].copy()
        if pool.empty:
            continue

        pool["_signal"] = pool.apply(
            lambda r: "explicit" if has_territory_signal(r, territory) else "none",
            axis=1)
        pool["_reality"] = pool.apply(
            lambda r: get_reality_class(r, territory), axis=1)
        pool["_cell"] = list(zip(pool["_signal"], pool["_reality"]))

        total_weight = sum(CELL_WEIGHTS.get(c, 0.01)
                           for c in pool["_cell"].unique())
        for cell, grp in pool.groupby("_cell"):
            cw = CELL_WEIGHTS.get(cell, 0.01)
            n_draw = min(max(1, round(n_per_territory * cw / total_weight)),
                         len(grp))
            sampled = grp.sample(n_draw, random_state=int(rng.integers(0, 2**31))).copy()
            sig, rea = cell if isinstance(cell, tuple) else (cell, "unknown")
            sampled["sample_component"] = "matrix"
            sampled["primary_stratum_id"] = f"matrix|{territory}|{sig}|{rea}"
            sampled["stratum_population_n"] = len(grp)
            sampled["stratum_target_n"] = n_draw
            sampled["inclusion_probability"] = None
            sampled["sampling_weight"] = None
            sampled["weight_status"] = "approximate"
            sampled["sampling_reason"] = (
                f"matrix: {territory}, signal={sig}, reality={rea}")
            parts.append(sampled)
            selected_here.update(sampled["barcode"].tolist())

    if not parts:
        return pd.DataFrame()
    result = pd.concat(parts)
    result = result[~result["barcode"].duplicated(keep="first")]
    if len(result) > target_n:
        result = result.sample(target_n, random_state=int(rng.integers(0, 2**31)))
    return result


# -- Component 3: calibration ------------------------------------------------

def sample_calibration(df: pd.DataFrame, target_n: int, category: str,
                        rng: np.random.Generator, already_selected: set,
                        prior_analyzed: set) -> pd.DataFrame:
    available = df[~df["barcode"].isin(already_selected)].copy()
    parts = []
    in_cal: set = set()

    # (a) Prompt-comparison panel
    panel_target = max(1, round(target_n * CALIBRATION_PANEL_SHARE /
                                COMPONENT_SPLIT["calibration"]))
    prior_pool = available[available["barcode"].isin(prior_analyzed)]
    n_panel = min(panel_target, len(prior_pool))
    if n_panel > 0:
        panel = prior_pool.sample(n_panel, random_state=int(rng.integers(0, 2**31))).copy()
        panel["sample_component"] = "calibration_panel"
        panel["primary_stratum_id"] = "calibration|prompt_comparison"
        panel["stratum_population_n"] = len(prior_pool)
        panel["stratum_target_n"] = n_panel
        panel["inclusion_probability"] = None
        panel["sampling_weight"] = None
        panel["weight_status"] = "approximate"
        panel["sampling_reason"] = "prompt-comparison panel: prior LLM run"
        parts.append(panel)
        in_cal.update(panel["barcode"].tolist())

    # (b) Rare territory enrichment
    rare_remaining = target_n - len(in_cal)
    avail_rare = available[~available["barcode"].isin(in_cal)]
    rare_pools = [("immune", "immune"), ("gut_health", "gut_health"),
                  ("fibre_form", "fibre")]
    for pool_label, territory in rare_pools:
        pool = avail_rare[
            avail_rare["formulation_territories"].fillna("").str.contains(
                territory, na=False)
            & ~avail_rare["barcode"].isin(in_cal)
        ]
        if pool.empty:
            continue
        n_draw = min(max(1, rare_remaining // len(rare_pools)), len(pool))
        sampled = pool.sample(n_draw, random_state=int(rng.integers(0, 2**31))).copy()
        sampled["sample_component"] = "calibration_rare"
        sampled["primary_stratum_id"] = f"calibration|rare|{pool_label}"
        sampled["stratum_population_n"] = len(pool)
        sampled["stratum_target_n"] = n_draw
        sampled["inclusion_probability"] = None
        sampled["sampling_weight"] = None
        sampled["weight_status"] = "approximate"
        sampled["sampling_reason"] = f"rare enrichment: {territory} formulation"
        parts.append(sampled)
        in_cal.update(sampled["barcode"].tolist())

    # (c) Random fill
    filled = sum(len(p) for p in parts)
    if filled < target_n:
        fill_pool = available[~available["barcode"].isin(in_cal)]
        fill_n = min(target_n - filled, len(fill_pool))
        if fill_n > 0:
            filler = fill_pool.sample(fill_n, random_state=int(rng.integers(0, 2**31))).copy()
            filler["sample_component"] = "calibration_random"
            filler["primary_stratum_id"] = "calibration|random_fill"
            filler["stratum_population_n"] = len(fill_pool)
            filler["stratum_target_n"] = fill_n
            filler["inclusion_probability"] = None
            filler["sampling_weight"] = None
            filler["weight_status"] = "approximate"
            filler["sampling_reason"] = "calibration random fill"
            parts.append(filler)

    return pd.concat(parts) if parts else pd.DataFrame()


# -- Main orchestrator -------------------------------------------------------

def get_prior_analyzed_barcodes() -> set:
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT barcode FROM product_analysis WHERE claim_source = 'vision'"
        ).fetchall()
        conn.close()
        return {str(r[0]) for r in rows}
    except Exception:
        return set()


def build_sample(df: pd.DataFrame, region: str, category: str,
                 rng: np.random.Generator, prior_analyzed: set,
                 seed_used: int = RANDOM_SEED) -> pd.DataFrame:
    scope = df[
        (df["primary_region"] == region)
        & (df["category"].str.lower() == category)
    ].copy()
    if scope.empty:
        return pd.DataFrame()
    quota = QUOTA_TARGET.get((region, category), 0)
    if quota == 0:
        return pd.DataFrame()

    n_backbone    = round(quota * COMPONENT_SPLIT["backbone"])
    n_matrix      = round(quota * COMPONENT_SPLIT["matrix"])
    n_calibration = quota - n_backbone - n_matrix

    backbone = sample_backbone(scope, n_backbone, rng)
    selected = set(backbone["barcode"].tolist()) if not backbone.empty else set()

    matrix = sample_matrix(scope, n_matrix, category, rng, selected)
    if not matrix.empty:
        selected.update(matrix["barcode"].tolist())

    calibration = sample_calibration(scope, n_calibration, category, rng,
                                      selected, prior_analyzed)

    parts = [p for p in [backbone, matrix, calibration] if not p.empty]
    if not parts:
        return pd.DataFrame()
    result = pd.concat(parts)
    result = result[~result["barcode"].duplicated(keep="first")]
    result["sampling_run_id"]   = RUN_ID
    result["sampling_region"]   = region
    result["sampling_category"] = category
    result["quota_target"]      = quota
    result["random_seed"]       = seed_used  # the actual CLI --seed value, not the constant
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    print("Loading input files...")
    df = load_inputs()
    print(f"  {len(df):,} products in scope (US/UK with valid region, image-eligible)")

    # Image-coverage breakdown by region × category
    print("\n  Image-eligible universe:")
    print(f"  {'Region':<12} {'Category':<10} {'Eligible':>10}")
    print(f"  {'-'*12} {'-'*10} {'-'*10}")
    for (region, category), _ in QUOTA_TARGET.items():
        n = len(df[
            (df["primary_region"] == region)
            & (df["category"].str.lower() == category)
        ])
        print(f"  {region:<12} {category:<10} {n:>10,}")

    prior_analyzed = get_prior_analyzed_barcodes()
    print(f"  {len(prior_analyzed):,} prior LLM run products "
          f"(prompt-comparison panel candidates)")

    if args.dry_run:
        print("\n--- DRY RUN: quota plan (image-eligible universe) ---")
        print(f"  {'Region':<12} {'Category':<10} {'Target':>8} {'Eligible':>10} {'Coverage':>10}")
        for (region, category), quota in QUOTA_TARGET.items():
            scope = df[(df["primary_region"] == region)
                       & (df["category"].str.lower() == category)]
            pct = 100 * len(scope) / quota if quota else 0
            print(f"  {region:<12} {category:<10} {quota:>8,} {len(scope):>10,} {pct:>9.0f}%")
        return

    all_parts = []
    summary_rows = []
    for (region, category), quota in QUOTA_TARGET.items():
        print(f"\n{region} / {category} (target {quota:,})...")
        part = build_sample(df, region, category, rng, prior_analyzed, seed_used=args.seed)
        if part.empty:
            print("  WARNING: no products sampled")
            continue
        n = len(part)
        comp_counts = part["sample_component"].value_counts().to_dict()
        print(f"  Selected {n:,} / {quota:,} ({n/quota:.0%}) | "
              f"{comp_counts}")
        all_parts.append(part)
        summary_rows.append({
            "region": region, "category": category,
            "quota_target": quota, "selected": n,
            "pct_filled": round(n / quota * 100, 1),
        })

    if not all_parts:
        print("No products sampled — check inputs.")
        return

    OUTPUT_COLS = [
        # Product identity — needed by vision_extract.py for OCR handoff
        "barcode", "product_name", "primary_brand", "image_url",
        "sampling_run_id", "sampling_region", "sampling_category",
        "sample_component", "primary_stratum_id",
        "stratum_population_n", "stratum_target_n",
        "inclusion_probability", "sampling_weight", "weight_status",
        "random_seed", "quota_target",
        "formulation_family", "family_source",
        "pre_llm_positioning_signal", "pre_llm_positioning_territories",
        "name_confidence", "formulation_likelihood_signal",
        "formulation_territories", "positioning_rule_version",
        "energy_band", "protein_band", "fibre_band", "satfat_band",
        "sugars_band", "metric_basis",
        "sampling_reason",
    ]
    out = pd.concat(all_parts)
    cols = [c for c in OUTPUT_COLS if c in out.columns]
    out[cols].to_csv(OUT_SAMPLE_CSV, index=False)
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY_CSV, index=False)

    print(f"\nTotal sample: {len(out):,} products")
    print(f"Wrote: {OUT_SAMPLE_CSV}")
    print(f"Wrote: {OUT_SUMMARY_CSV}")
    print("\nQuota fill summary:")
    print(pd.DataFrame(summary_rows).to_string(index=False))


if __name__ == "__main__":
    main()
