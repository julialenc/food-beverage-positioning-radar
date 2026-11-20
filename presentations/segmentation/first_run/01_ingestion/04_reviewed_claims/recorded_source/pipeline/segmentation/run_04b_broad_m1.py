"""RUN 04B: broad M1, observed-fibre profiles and frozen RUN 04A comparisons.

No input, scaling parameter or RUN 04A artifact is written. All ARIs compare
labels for the same exact regional product keys. M2 is never refitted.
"""

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits

from run_04_preliminary_clustering import KEY, KS, MODELS, SEEDS, cluster, sha


ROOT = Path(__file__).resolve().parents[2]
SEG = ROOT / "presentations/segmentation"
RUN03 = SEG / "run_03_corrected_v1"
RUN04A = SEG / "run_04"
OUTPUT = SEG / "run_04b_v1"
REPORT = OUTPUT / "RUN 04B_no US.md"
RAW = {"protein": "protein_100g", "fat": "fat_100g", "carbohydrates": "carbs_100g",
       "sugars": "sugars_100g", "salt": "salt_100g", "fibre": "fiber_100g",
       "energy": "energy_kcal", "saturated_fat": "saturated_fat_100g"}
SUCCESS = ["success_no_claims", "success_with_claims"]
REGIONS = {"FR": "FR", "UK+IE": "UK_IE", "US+CA": "US_CA"}


def relative(path):
    return path.relative_to(ROOT).as_posix()


def read(path):
    return pd.read_csv(path, dtype={c: str for c in KEY}, keep_default_na=False, low_memory=False)


def profiles(meta, x, labels, cohort, region, category, k):
    """Raw nutrient statistics use observed values only, including declared zero."""
    rows = []
    extreme = (np.abs(x) > 5).any(axis=1)
    stratum_warning_pct = 100 * meta.nutrition_warning_present.mean()
    for lab in sorted(np.unique(labels)):
        take = labels == lab
        g = meta.loc[take]
        n = len(g)
        local_x = x[take]
        squared_distance = ((local_x - local_x.mean(axis=0)) ** 2).sum(axis=1)
        denominator = squared_distance.sum()
        extreme_sse_pct = (100 * squared_distance[extreme[take]].sum() / denominator
                           if denominator > 0 else 0.)
        row = {"region": region, "category": category, "cohort": cohort, "k": k,
               "cluster": int(lab), "records": n, "share_pct": 100 * n / len(meta),
               "warning_records": int(g.nutrition_warning_present.sum()),
               "warning_pct": 100 * g.nutrition_warning_present.mean(),
               "stratum_warning_pct": stratum_warning_pct,
               "with_image": int(g.image_available.sum()), "with_image_pct": 100 * g.image_available.mean(),
               "ocr_llm_success": int(g.historical_ocr_status.isin(SUCCESS).sum()),
               "ocr_llm_success_pct": 100 * g.historical_ocr_status.isin(SUCCESS).mean(),
               "ocr_success_no_claims": int(g.historical_ocr_status.eq("success_no_claims").sum()),
               "ocr_success_with_claims": int(g.historical_ocr_status.eq("success_with_claims").sum()),
               "extreme_records": int(extreme[take].sum()),
               "extreme_pct": 100 * extreme[take].mean(),
               "extreme_within_cluster_sse_pct": extreme_sse_pct}
        for name, field in RAW.items():
            observed = g[field].dropna()
            row.update({f"{name}_observed": len(observed),
                        f"{name}_available_pct": 100 * len(observed) / n,
                        f"{name}_median": observed.median() if len(observed) else np.nan,
                        f"{name}_p25": observed.quantile(.25) if len(observed) else np.nan,
                        f"{name}_p75": observed.quantile(.75) if len(observed) else np.nan,
                        f"{name}_iqr": observed.quantile(.75) - observed.quantile(.25) if len(observed) else np.nan})
        row["flag_small"] = n < 30 or row["share_pct"] < 1
        row["flag_warning_heavy"] = (row["warning_pct"] >= 50 or
                                     (row["warning_pct"] >= 2 * stratum_warning_pct and
                                      row["warning_pct"] - stratum_warning_pct >= 10))
        row["flag_extreme_dominated"] = row["extreme_pct"] >= 50 or extreme_sse_pct >= 50
        rows.append(row)
    return rows


def validate_sources():
    a = json.loads((RUN04A / "run_04_manifest.json").read_text(encoding="utf-8"))
    r3 = json.loads((RUN03 / "run_03_manifest.json").read_text(encoding="utf-8"))
    index = read(RUN03 / "matrix_index.csv")
    if tuple(a["k_values"]) != KS or tuple(a["stability_seeds_at_k3"]) != SEEDS:
        raise ValueError("RUN 04A configuration differs from reused settings")
    protected = {}
    def protect(path, expected=None):
        actual = sha(path)
        if expected is not None and actual != expected:
            raise ValueError(f"Input hash mismatch: {path}")
        protected[relative(path)] = actual
    for p in RUN04A.rglob("*"):
        if p.is_file():
            protect(p, a["outputs"].get(p.name, {}).get("sha256"))
    protect(ROOT / a["report"]["path"], a["report"]["sha256"])
    protect(ROOT / "pipeline/segmentation/run_04_preliminary_clustering.py", a["script_sha256"])
    protect(RUN03 / "run_03_manifest.json", a["run03_manifest_sha256"])
    protect(RUN03 / "matrix_index.csv", a["run03_matrix_index_sha256"])
    for name in ("regional_product_base.csv", "check_03_model_population.csv", "check_03_scaling_parameters.csv"):
        p = RUN03 / name
        protect(p, r3["outputs"][relative(p)]["sha256"])
    needed = index.loc[((index.model == "M1") & (index.cohort == "broad_eligible")) |
                       ((index.model == "M2") & (index.cohort == "M2_all_models_common"))]
    if len(needed) != 22:
        raise ValueError("Expected 11 broad M1 and 11 common M2 matrices")
    for row in needed.itertuples():
        protect(RUN03 / row.relative_path, row.sha256)
    return a, r3, index, protected


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"Versioned RUN 04B directory already exists: {OUTPUT}")
    a_manifest, r3_manifest, index, protected = validate_sources()
    base = read(RUN03 / "regional_product_base.csv")
    for field in RAW.values():
        base[field] = pd.to_numeric(base[field].replace("", np.nan), errors="raise")
    if base.duplicated(KEY).any():
        raise ValueError("Duplicate regional base keys")
    old_assign = read(RUN04A / "check_04_cluster_assignments.csv")
    old_assign = old_assign.loc[old_assign.model.isin(["M1", "M2"])].copy()
    if old_assign.duplicated(KEY + ["model", "k"]).any():
        raise ValueError("Duplicate RUN 04A assignment keys")
    reused = read(RUN04A / "check_04_model_agreement_ari.csv")
    reused = reused.loc[reused.comparison.eq("M1_vs_M2")].copy()
    reused["evidence_source"] = relative(RUN04A / "check_04_model_agreement_ari.csv")
    if len(reused) != 33:
        raise ValueError("Missing existing M1/M2 comparison")
    assignments, all_profiles, comparisons, aligned_profiles = [], [], [], []
    contingency, stability, sensitivity, subprofiles, population = [], [], [], [], []
    for region, dirname in REGIONS.items():
        for category in ("snacks", "cereals", "dairies", "beverages"):
            if (region, category) == ("US+CA", "dairies"):
                continue
            print(f"RUN 04B: {region} / {category}", flush=True)
            matrix = read(RUN03 / "matrices" / dirname / category / "M1_broad.csv")
            m2matrix = read(RUN03 / "matrices" / dirname / category / "M2_all_models_common.csv")
            if matrix.duplicated(KEY).any() or not matrix.region.eq(region).all() or not matrix.category.eq(category).all():
                raise ValueError("Invalid M1 broad keys")
            keys = pd.MultiIndex.from_frame(matrix[KEY])
            meta = base.set_index(KEY).loc[keys].reset_index()
            x = matrix[[f"{f}_z" for f in MODELS["M1"]]].to_numpy(float)
            if not np.isfinite(x).all() or not meta.eligible_M1.eq(1).all():
                raise ValueError("Invalid broad M1 input")
            if len(matrix) != int(index.loc[(index.region == region) & (index.category == category) &
                                             (index.model == "M1") & (index.cohort == "broad_eligible"), "rows"].iloc[0]):
                raise ValueError("Broad M1 count mismatch")
            if len(meta) != base.loc[(base.region == region) & (base.category == category), "eligible_M1"].sum():
                raise ValueError("Broad matrix does not cover all eligible M1 products")
            x2 = m2matrix[[f"{f}_z" for f in MODELS["M2"]]].to_numpy(float)
            m2keys = pd.MultiIndex.from_frame(m2matrix[KEY])
            common_positions = keys.get_indexer(m2keys)
            if (common_positions < 0).any() or len(np.unique(common_positions)) != len(m2keys):
                raise ValueError("M2 common population not a unique subset of broad M1")
            common_meta = meta.iloc[common_positions].reset_index(drop=True)
            if not common_meta.fiber_100g.notna().all():
                raise ValueError("NULL fibre in common cohort")
            population.append({"region": region, "category": category, "broad_m1_records": len(meta),
                               "common_records": len(common_meta), "coverage_gain_records": len(meta) - len(common_meta),
                               "fibre_available_records": int(meta.fiber_100g.notna().sum()),
                               "fibre_available_pct": 100 * meta.fiber_100g.notna().mean(),
                               "with_image": int(meta.image_available.sum()),
                               "warning_records": int(meta.nutrition_warning_present.sum()),
                               "ocr_llm_success": int(meta.historical_ocr_status.isin(SUCCESS).sum())})
            for k in KS:
                labels = cluster(x, k, 42) + 1
                part = matrix[KEY].copy()
                part["k"], part["cluster"] = k, labels
                assignments.append(part)
                broad_p = profiles(meta, x, labels, "M1_broad", region, category, k)
                all_profiles.extend(broad_p)
                common = old_assign.loc[(old_assign.region == region) & (old_assign.category == category) & (old_assign.k == k)]
                old_labels = {}
                for model in ("M1", "M2"):
                    old = common.loc[common.model == model].set_index(KEY)
                    if len(old) != len(m2keys) or not old.index.isin(m2keys).all():
                        raise ValueError("RUN 04A comparison cohort differs from M2 matrix")
                    old_labels[model] = old.loc[m2keys, "cluster"].to_numpy(int)
                c1_p = profiles(common_meta, x[common_positions], old_labels["M1"], "M1_common_04A", region, category, k)
                c2_p = profiles(common_meta, x2, old_labels["M2"], "M2_common_04A", region, category, k)
                all_profiles.extend(c1_p + c2_p)
                reused_row = reused.loc[(reused.region == region) & (reused.category == category) & (reused.k == k)].iloc[0]
                actual_old_ari = adjusted_rand_score(old_labels["M1"], old_labels["M2"])
                if not np.isclose(actual_old_ari, reused_row.adjusted_rand_index, atol=1e-9):
                    raise ValueError("Reused ARI does not match frozen assignments")
                shared_broad_labels = labels[common_positions]
                comparisons.append({"region": region, "category": category, "k": k,
                                    "broad_records": len(meta), "shared_records": len(common_meta),
                                    "ari_broad_m1_vs_common_m1_on_shared_keys": adjusted_rand_score(shared_broad_labels, old_labels["M1"]),
                                    "m1_common_vs_m2_common_ari_reused": reused_row.adjusted_rand_index})
                ct = pd.crosstab(pd.Series(shared_broad_labels, name="broad_cluster"),
                                 pd.Series(old_labels["M1"], name="common_cluster")).reindex(index=range(1, k+1), columns=range(1, k+1), fill_value=0)
                ri, ci = linear_sum_assignment(-ct.to_numpy())
                for r, c in zip(ri, ci):
                    b, old = broad_p[r], c1_p[c]
                    row = {"region": region, "category": category, "k": k, "broad_cluster": r+1,
                           "common_m1_cluster_matched": c+1, "shared_matching_records": int(ct.iloc[r, c]),
                           "broad_full_share_pct": b["share_pct"], "common_m1_share_pct": old["share_pct"],
                           "broad_share_on_shared_keys_pct": 100 * ct.iloc[r].sum() / len(common_meta)}
                    for name in RAW:
                        row[f"broad_{name}_median"] = b[f"{name}_median"]
                        row[f"common_m1_{name}_median"] = old[f"{name}_median"]
                    aligned_profiles.append(row)
                for b in range(1, k+1):
                    for c in range(1, k+1):
                        contingency.append({"region": region, "category": category, "k": k,
                                            "broad_cluster": b, "common_m1_cluster": c, "shared_records": int(ct.loc[b, c])})
                # Descriptive M2 subdivisions of a broad M1 cluster, only on common keys.
                # This is profile evidence, not an ARI between unequal populations.
                for b in range(1, k+1):
                    for c in range(1, k+1):
                        mask = (shared_broad_labels == b) & (old_labels["M2"] == c)
                        if not mask.any():
                            continue
                        g = common_meta.loc[mask]
                        row = {"region": region, "category": category, "k": k,
                               "broad_m1_cluster": b, "m2_cluster": c, "shared_records": len(g),
                               "share_of_broad_cluster_common_products_pct": 100 * mask.sum() / (shared_broad_labels == b).sum()}
                        for name, field in RAW.items():
                            row[f"{name}_median"] = g[field].median()
                            row[f"{name}_p25"] = g[field].quantile(.25)
                            row[f"{name}_p75"] = g[field].quantile(.75)
                        subprofiles.append(row)
                if k == 3:
                    for seed in SEEDS[1:]:
                        other = cluster(x, k, seed) + 1
                        stability.append({"region": region, "category": category, "k": k,
                                          "reference_seed": 42, "comparison_seed": seed,
                                          "ari_vs_seed_42": adjusted_rand_score(labels, other)})
                    keep = (np.abs(x) <= 5).all(axis=1)
                    other = cluster(x[keep], k, 42) + 1
                    sensitivity.append({"region": region, "category": category, "k": k,
                                        "records": len(x), "extreme_records": int((~keep).sum()),
                                        "sensitivity_retained_records": int(keep.sum()),
                                        "ari_on_retained_keys": adjusted_rand_score(labels[keep], other)})
    tables = {"m1_broad_cluster_assignments.csv": pd.concat(assignments, ignore_index=True),
              "check_04b_cluster_profiles_all_k.csv": pd.DataFrame(all_profiles),
              "check_04b_broad_vs_common_m1.csv": pd.DataFrame(comparisons),
              "check_04b_broad_vs_common_m1_profile_alignment.csv": pd.DataFrame(aligned_profiles),
              "check_04b_broad_vs_common_m1_contingency.csv": pd.DataFrame(contingency),
              "check_04b_reused_04a_m1_vs_m2.csv": reused,
              "check_04b_m2_within_broad_m1_profiles.csv": pd.DataFrame(subprofiles),
              "check_04b_seed_stability.csv": pd.DataFrame(stability),
              "check_04b_extreme_sensitivity.csv": pd.DataFrame(sensitivity),
              "check_04b_population.csv": pd.DataFrame(population)}
    p = tables["check_04b_cluster_profiles_all_k.csv"]
    broad_p = p.loc[p.cohort.eq("M1_broad")]
    tables["check_04b_principal_k3.csv"] = broad_p.loc[broad_p.k.eq(3)].copy()
    tables["check_04b_comparison_k2_k4.csv"] = broad_p.loc[broad_p.k.isin([2, 4])].copy()
    validation = validate_results(tables, protected)
    OUTPUT.mkdir()
    for name, data in tables.items():
        data.to_csv(OUTPUT / name, index=False, encoding="utf-8", float_format="%.12g")
    make_report(tables)
    manifest = {"run": "RUN_04B_BROAD_M1_V1", "status": "CHECK 04B — Pending review",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "script": relative(Path(__file__).resolve()), "script_sha256": sha(Path(__file__).resolve()),
                "source_hashes_before_and_after": protected, "source_preservation": "all recorded input files unchanged",
                "source_release": r3_manifest["source_release"],
                "configuration": {"algorithm": "KMeans", "implementation": "reused RUN 04A cluster() helper",
                                  "features": MODELS["M1"], "k_values": list(KS), "primary_seed": 42,
                                  "stability_k": 3, "stability_seeds": list(SEEDS), "n_init": 3,
                                  "init": "k-means++", "algorithm_setting": "lloyd", "max_iter": 300, "tol": .0001,
                                  "threadpool_limit": 1, "scaling": "unchanged RUN 03 M1_broad matrix values",
                                  "extreme_sensitivity": "k=3, refit on records with all abs(z)<=5; compare same retained keys only",
                                  "report_highlights_only": {"extreme_sensitivity_ari_below": .5, "minimum_seed_ari_below": .8},
                                  "flags": {"small": "n<30 OR stratum share<1%",
                                            "warning_heavy": ">=50% OR >=2x stratum and >=10 percentage points higher",
                                            "extreme_dominated": ">=50% extreme products OR >=50% within-cluster SSE from extreme products"}},
                "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                            "scikit_learn": sklearn.__version__, "scipy": scipy.__version__},
                "validation": validation,
                "outputs": {name: {"rows": len(data), "sha256": sha(OUTPUT / name)} for name, data in tables.items()},
                "report": {"path": relative(REPORT), "sha256": sha(REPORT)}}
    (OUTPUT / "run_04b_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation), flush=True)
    print(f"Report: {REPORT}", flush=True)


def validate_results(t, protected):
    pop = t["check_04b_population.csv"]
    ass = t["m1_broad_cluster_assignments.csv"]
    p = t["check_04b_cluster_profiles_all_k.csv"]
    if len(pop) != 11 or int(pop.broad_m1_records.sum()) != 218115 or int(pop.common_records.sum()) != 128701:
        raise ValueError("Unexpected broad/common population counts")
    if ass.duplicated(KEY + ["k"]).any() or len(ass) != 218115 * 3:
        raise ValueError("Assignment keys/count invalid")
    if ((ass.region == "US+CA") & (ass.category == "dairies")).any():
        raise ValueError("US/CA dairy unexpectedly present")
    if len(p) != 297 or len(t["check_04b_principal_k3.csv"]) != 33:
        raise ValueError("Unexpected number of cluster profiles")
    expected = pop.set_index(["region", "category"]).broad_m1_records
    broad = p.loc[p.cohort == "M1_broad"]
    for k in KS:
        sums = broad.loc[broad.k.eq(k)].groupby(["region", "category"]).records.sum()
        pd.testing.assert_series_equal(sums.sort_index(), expected.sort_index(), check_names=False)
    if not np.allclose(p.ocr_llm_success, p.ocr_success_no_claims + p.ocr_success_with_claims):
        raise ValueError("OCR success components do not balance")
    if (p.fibre_observed > p.records).any():
        raise ValueError("Invalid observed fibre denominator")
    changed = [name for name, digest in protected.items() if sha(ROOT / name) != digest]
    if changed:
        raise ValueError(f"Source files unexpectedly changed: {changed}")
    return {"strata": 11, "unique_broad_regional_products": 218115, "common_regional_products": 128701,
            "additional_broad_products": 89414, "assignment_rows_across_three_k": len(ass),
            "broad_k3_cluster_rows": 33, "all_cohort_profile_rows": len(p),
            "source_files_verified_unchanged": len(protected), "m2_fits_executed": 0,
            "broad_m1_vs_m2_ari_calculated": False}


def num(value, digits=2):
    return "—" if pd.isna(value) else f"{value:.{digits}f}".rstrip("0").rstrip(".")


def interval(row, feature):
    return f"{num(row[feature+'_median'])} [{num(row[feature+'_p25'])}–{num(row[feature+'_p75'])}]"


def make_report(t):
    principal = t["check_04b_principal_k3.csv"]
    comparison = t["check_04b_broad_vs_common_m1.csv"]
    pop = t["check_04b_population.csv"]
    allp = t["check_04b_cluster_profiles_all_k.csv"]
    stability = t["check_04b_seed_stability.csv"]
    sensitivity = t["check_04b_extreme_sensitivity.csv"]
    sub = t["check_04b_m2_within_broad_m1_profiles.csv"]
    lines = ["# RUN 04B — Broad M1 and observed-fibre profiling", "", "**CHECK 04B — Pending review.**", "",
             "Broad M1 was fitted to 218,115 unique `(barcode, region, category)` products across 11 strata, versus 128,701 in RUN 04A's common cohort: 89,414 additional products. US/CA dairy remains held out. RUN 04A artifacts and all consumed RUN 03 inputs were verified unchanged.", "",
             "K=3 is the principal review view; k=2 and k=4 are supporting comparisons. K-means settings reuse RUN 04A exactly: approved RUN 03 standardized M1 features, k-means++ initialization, Lloyd algorithm, n_init=3, reference seed 42; k=3 stability uses seeds 101 and 202. No scaling parameters were refitted. Initialization repeatability is measured here; bootstrap or longitudinal stability is not established.", "",
             "The principal checks identify issues that need review before these particular clusters are used for sampling allocation:", ""]
    for _, row in principal.loc[principal.flag_small].iterrows():
        lines.append(f"- **{row.region} {row.category} C{row.cluster}:** {row.records:,} products ({row.share_pct:.2f}% of the stratum), salt median {num(row.salt_median)} g/100 g/ml, {row.warning_pct:.1f}% warnings and {row.extreme_pct:.1f}% with a modeled |z|>5. This identifies a small, unusual nutritional group; it does not itself prove source errors.")
    for _, row in sensitivity.loc[sensitivity.ari_on_retained_keys.lt(.5)].iterrows():
        lines.append(f"- **{row.region} {row.category}:** the extreme-sensitivity ARI is {row.ari_on_retained_keys:.3f} on identical retained keys. The reference k=3 partition is sensitive to extreme observations.")
    unstable = stability.groupby(["region", "category"]).ari_vs_seed_42.min()
    for (region, category), value in unstable.loc[unstable.lt(.8)].items():
        lines.append(f"- **{region} {category}:** minimum seed ARI is {value:.3f}. Population-comparison differences here may also reflect alternative initialization outcomes, so they cannot be attributed solely to fibre-based cohort selection.")
    lines += ["", "The ARI cutoffs of 0.5 and 0.8 above are only reporting thresholds for highlighting sensitivity and initialization differences; they are not acceptance gates. All clusters remain available in the tables, with no automatic removal, merge or model choice.", "",
             "## Principal nutritional profiles — k=3", "",
             "Each value is a median [P25–P75], in g per 100 g/ml; the interval is the IQR span. Percentages use the full broad M1 population within each stratum. Raw source fields are joined through exact regional product keys. Energy (kcal/100 g/ml), saturated fat, all nutrient observed counts, and IQR widths are in the supporting tables.", "",
             "| Region | Category | Cluster | Products | % | Protein | Fat | Carbs | Sugars | Salt |",
             "|---|---|---:|---:|---:|---|---|---|---|---|"]
    for _, row in principal.iterrows():
        lines.append(f"| {row.region} | {row.category} | {row.cluster} | {row.records:,} | {row.share_pct:.2f} | " +
                     " | ".join(interval(row, f) for f in ("protein", "fat", "carbohydrates", "sugars", "salt")) + " |")
    lines += ["", "## Fibre and coverage within broad M1 — k=3", "",
              "Fibre statistics use only non-NULL fibre observations, retaining declared zero. Fibre availability uses all products in the cluster. OCR success includes both success_with_claims and success_no_claims; failed/unusable attempts are excluded from the successful count. Image availability does not establish image usability.", "",
              "| Region | Category | Cluster | Fibre observed n (%) | Fibre median [P25–P75] | Warning n (%) | Images | OCR successes | Extreme % / SSE % | Review flags |",
              "|---|---|---:|---|---|---|---:|---:|---:|---|"]
    for _, row in principal.iterrows():
        flags = [name for name, col in (("small", "flag_small"), ("warnings", "flag_warning_heavy"), ("extremes", "flag_extreme_dominated")) if row[col]]
        lines.append(f"| {row.region} | {row.category} | {row.cluster} | {row.fibre_observed:,} ({row.fibre_available_pct:.1f}%) | {interval(row, 'fibre')} | {row.warning_records:,} ({row.warning_pct:.1f}%) | {row.with_image:,} | {row.ocr_llm_success:,} | {row.extreme_pct:.1f} / {row.extreme_within_cluster_sse_pct:.1f} | {', '.join(flags) or '—'} |")
    lines += ["", "The Extreme % / SSE % column shows the percentage of products with any modeled |z|>5, followed by their percentage contribution to within-cluster squared distances from the cluster centre. A few extreme observations can contribute most of that distance even when their product share is small."]
    lines += ["", "## Population selection versus adding fibre", "",
              "Comparison A fits broad M1 anew and compares it with frozen common-cohort M1 labels only on their identical shared keys. Comparison B copies the frozen RUN 04A common M1/M2 ARI; M2 is not rerun. A measures the observed difference between fits; seed checks qualify whether a difference can be attributed to cohort selection rather than alternative initialization outcomes. B holds products constant while adding fibre, but is also subject to K-means initialization. Cluster IDs have no shared meaning between fits. The profile-alignment CSV uses maximum shared-product overlap solely to align display labels, and includes full-population and shared-population size percentages.", "",
              "| Region | Category | Broad M1 n | Common n (% of broad) | A: broad/common M1 ARI | B: common M1/M2 ARI |",
              "|---|---|---:|---|---:|---:|"]
    for _, row in comparison.loc[comparison.k.eq(3)].iterrows():
        lines.append(f"| {row.region} | {row.category} | {row.broad_records:,} | {row.shared_records:,} ({100*row.shared_records/row.broad_records:.1f}%) | {row.ari_broad_m1_vs_common_m1_on_shared_keys:.3f} | {row.m1_common_vs_m2_common_ari_reused:.3f} |")
    lines += ["", "### Fibre territories: broad M1 versus existing M2", "",
              "These are descriptive fibre profiles, not an ARI across different populations. All M1 fibre summaries describe only observed fibre within each broad cluster; M2 describes its fibre-complete population. Selection into that population may affect the comparison. A larger fibre spread between M2 clusters alone does not establish a useful sampling territory.", "",
              "| Region | Category | Broad M1 cluster fibre medians [P25–P75] | Existing M2 cluster fibre medians [P25–P75] |",
              "|---|---|---|---|"]
    for _, row in pop.iterrows():
        g = allp.loc[(allp.region == row.region) & (allp.category == row.category) & allp.k.eq(3)]
        values = []
        for cohort in ("M1_broad", "M2_common_04A"):
            h = g.loc[g.cohort == cohort]
            values.append("; ".join(f"C{r.cluster}: {interval(r, 'fibre')}" for _, r in h.iterrows()))
        lines.append(f"| {row.region} | {row.category} | {values[0]} | {values[1]} |")
    lines += ["", "The subdivision table shows how common products from one broad M1 cluster are distributed among M2 clusters, with raw macro and fibre profiles. Illustrative k=3 splits below require at least 30 products and at least 5% of the broad cluster's shared products in each displayed M2 subgroup. These thresholds only limit the examples shown; they change no assignment or eligibility.", ""]
    examples = []
    for key, g in sub.loc[sub.k.eq(3) & sub.shared_records.ge(30) & sub.share_of_broad_cluster_common_products_pct.ge(5)].groupby(["region", "category", "broad_m1_cluster"]):
        if len(g) > 1:
            examples.append((g.fibre_median.max() - g.fibre_median.min(), key, g))
    for category in ("snacks", "cereals", "dairies", "beverages"):
        candidates = [x for x in examples if x[1][1] == category]
        if candidates:
            _, (region, _, broad), g = max(candidates, key=lambda x: x[0])
            desc = "; ".join(f"M2 C{r.m2_cluster}: n={r.shared_records:,}, fibre {interval(r, 'fibre')}, protein {num(r.protein_median)}, fat {num(r.fat_median)}, carbs {num(r.carbohydrates_median)}, sugars {num(r.sugars_median)}" for _, r in g.iterrows())
            lines.append(f"- **{region} {category}, broad M1 C{broad}:** {desc}. These subgroup profiles describe possible differentiation for review; they do not establish that fibre alone caused it.")
    lines += ["", "## Robustness and sampling issues — k=3", "",
              "Seed stability and extreme sensitivity reuse RUN 04A methodology. Extreme means any modeled |z|>5. The sensitivity refit omits those products only for that diagnostic, using unchanged scaling, then calculates ARI on identical retained keys. Official assignments retain all eligible products.", "",
              "| Region | Category | Minimum seed ARI | Extreme products | ARI after extreme removal | Flagged clusters |",
              "|---|---|---:|---:|---:|---:|"]
    for _, row in sensitivity.iterrows():
        s = stability.loc[(stability.region == row.region) & (stability.category == row.category)]
        g = principal.loc[(principal.region == row.region) & (principal.category == row.category)]
        flagged = g[["flag_small", "flag_warning_heavy", "flag_extreme_dominated"]].any(axis=1).sum()
        lines.append(f"| {row.region} | {row.category} | {s.ari_vs_seed_42.min():.3f} | {row.extreme_records:,} | {row.ari_on_retained_keys:.3f} | {flagged} |")
    lines += ["", "Review flags are diagnostics, not exclusions: small means n<30 or <1% of the stratum; warning-heavy means >=50% warnings, or >=2 times the stratum warning share and at least 10 percentage points higher; extreme-dominated means >=50% extreme products or >=50% of within-cluster squared distance contributed by extreme products. These review thresholds are recorded choices for RUN 04B, not new eligibility rules.", "",
              "Before approving clusters for sampling, inspect flagged groups and strata with weak seed or extreme-sensitivity agreement. No image or warning gate has been imposed. Zero prior successful OCR/LLM coverage may motivate sampling but does not invalidate a nutritional cluster. Prior success is historical coverage, not evidence-version eligibility to rerun.", "",
              "US/CA beverage nutrient completeness remains limited in the underlying OFF universe (about 93% missing in RUN 03). Broad M1 represents nutrient-complete records, not the beverage market. Fibre missingness can also be selective, and observed-fibre profiles do not describe missing-fibre products. Concentrates and powders remain alongside other beverage forms under the approved scope; nutrition alone does not establish product form. Low minimum seed ARI or a strong change after the extreme sensitivity refit is a material sampling-design issue, even if the reference clusters are reproducible with seed 42.", "",
              "## Supporting tables and provenance", ""]
    labels = {"check_04b_principal_k3.csv": "Principal broad M1 profiles and coverage — k=3",
              "check_04b_comparison_k2_k4.csv": "Broad M1 profiles and coverage — k=2 and k=4",
              "check_04b_population.csv": "Broad versus common population counts",
              "check_04b_cluster_profiles_all_k.csv": "All raw profiles: broad M1, frozen common M1 and frozen M2",
              "check_04b_broad_vs_common_m1.csv": "Comparison A ARI and reused comparison B ARI",
              "check_04b_broad_vs_common_m1_profile_alignment.csv": "Matched profile and relative-size comparisons",
              "check_04b_broad_vs_common_m1_contingency.csv": "Shared-key broad/common M1 contingency counts",
              "check_04b_reused_04a_m1_vs_m2.csv": "Frozen RUN 04A M1/M2 comparison evidence",
              "check_04b_m2_within_broad_m1_profiles.csv": "M2 subdivisions within broad M1 on shared products",
              "check_04b_seed_stability.csv": "k=3 seed stability",
              "check_04b_extreme_sensitivity.csv": "k=3 extreme sensitivity",
              "m1_broad_cluster_assignments.csv": "Full broad M1 assignments for each k"}
    for name, label in labels.items():
        lines.append(f"- [{label}]({name})")
    lines += ["- [Source hashes, configuration, runtime, validation and output hashes](run_04b_manifest.json)", "",
              "**Review recommendation: Adjust / review robustness and fibre territories before sampling allocation. CHECK 04B remains pending review.** No k or final model has been selected, and final methodological conclusions remain open.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
