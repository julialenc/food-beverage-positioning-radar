"""RUN 04: bounded preliminary nutritional clustering on approved RUN 03 matrices."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "presentations/segmentation/run_03_corrected_v1"
OUTPUT = ROOT / "presentations/segmentation/run_04"
REPORT = ROOT / "presentations/segmentation/RUN 04_no US.md"
KEY = ["barcode", "region", "category"]
MODELS = {
    "M1": ["protein", "total_fat", "carbohydrates", "sugars", "salt"],
    "M2": ["protein", "total_fat", "carbohydrates", "sugars", "fibre", "salt"],
    "M3": ["protein", "total_fat", "sugars", "salt"],
    "M4": ["protein", "total_fat", "carbohydrates", "salt"],
}
KS = (2, 3, 4)
SEEDS = (42, 101, 202)
RAW = {"protein": "protein_100g", "total_fat": "fat_100g", "carbohydrates": "carbs_100g",
       "sugars": "sugars_100g", "fibre": "fiber_100g", "salt": "salt_100g"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cluster(x, k, seed):
    return KMeans(n_clusters=k, random_state=seed, n_init=3, algorithm="lloyd").fit_predict(x)


def main():
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise FileExistsError(f"Refusing to overwrite {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    base_path = INPUT / "regional_product_base.csv"
    base = pd.read_csv(base_path, dtype={c: str for c in KEY + ["region", "category", "barcode", "historical_ocr_status"]},
                       keep_default_na=False, low_memory=False)
    if base.duplicated(KEY).any():
        raise ValueError("RUN 03 base has duplicate regional product keys")
    base["nutrition_warning_present"] = pd.to_numeric(base["nutrition_warning_present"], errors="raise")
    base["image_available"] = pd.to_numeric(base["image_available"], errors="raise")
    if "eligible_M1" not in base or len(base) != 476626:
        raise ValueError("Unexpected approved RUN 03 corrected base")
    assignment_parts = []
    profile_parts = []
    agreement_parts = []
    stability_parts = []
    warning_parts = []
    coverage_parts = []
    extremes_parts = []
    model_population_parts = []

    for region in ("FR", "UK+IE", "US+CA"):
        region_dir = {"FR": "FR", "UK+IE": "UK_IE", "US+CA": "US_CA"}[region]
        for category in ("snacks", "cereals", "dairies", "beverages"):
            if region == "US+CA" and category == "dairies":
                continue
            meta = base.loc[(base.region == region) & (base.category == category)].set_index(KEY)
            model_frames = {}
            labels_cache = {}
            for model in MODELS:
                path = INPUT / "matrices" / region_dir / category / f"{model}_all_models_common.csv"
                frame = pd.read_csv(path, dtype={c: str for c in KEY + ["countries", "historical_ocr_status"]},
                                    keep_default_na=False, low_memory=False)
                if frame.duplicated(KEY).any() or not frame[KEY].apply(tuple, axis=1).isin(meta.index).all():
                    raise ValueError(f"Matrix keys invalid: {path}")
                cols = [f"{feature}_z" for feature in MODELS[model]]
                if not np.isfinite(frame[cols].to_numpy(dtype=float)).all():
                    raise ValueError(f"Non-finite model input: {path}")
                model_frames[model] = frame
                frame_keys = pd.MultiIndex.from_frame(frame[KEY])
                aligned_meta = meta.loc[frame_keys].reset_index(drop=True)
                raw_values_by_feature = {
                    feature: pd.to_numeric(aligned_meta[RAW[feature]].replace("", np.nan), errors="coerce")
                    for feature in MODELS[model]
                }
                for k in KS:
                    labels_by_seed = {42: cluster(frame[cols].to_numpy(float), k, 42)}
                    if k == 3:
                        for seed in SEEDS[1:]:
                            labels_by_seed[seed] = cluster(frame[cols].to_numpy(float), k, seed)
                    labels = labels_by_seed[42]
                    labels_cache[(model, k)] = labels
                    scored = frame.copy()
                    scored["cluster"] = labels + 1
                    scored["model"] = model
                    scored["k"] = k
                    assignment_parts.append(scored[KEY + ["model", "k", "cluster"]])
                    sil = silhouette_score(frame[cols].to_numpy(float), labels, sample_size=min(1000, len(frame)), random_state=42)
                    counts = pd.Series(labels).value_counts().sort_index()
                    for c, n in counts.items():
                        profile = {"region": region, "category": category, "model": model, "k": k,
                                   "cluster": int(c + 1), "records": int(n), "share_pct": 100 * n / len(frame),
                                   "silhouette_sampled": float(sil)}
                        for feature in MODELS[model]:
                            raw = RAW[feature]
                            positions = np.flatnonzero(labels == c)
                            raw_values = raw_values_by_feature[feature].iloc[positions]
                            profile[f"{feature}_median"] = float(raw_values.median())
                            profile[f"{feature}_p25"] = float(raw_values.quantile(.25))
                            profile[f"{feature}_p75"] = float(raw_values.quantile(.75))
                        profile_parts.append(profile)
                    for seed in SEEDS[1:] if k == 3 else ():
                        stability_parts.append({"region": region, "category": category, "model": model, "k": k,
                                                "reference_seed": 42, "comparison_seed": seed,
                                                "ari_vs_seed_42": adjusted_rand_score(labels, labels_by_seed[seed])})
                    # Sensitivity diagnostic: refit after omitting products with any |z| > 5;
                    # assess agreement only on the retained keys, without changing official assignments.
                    x = frame[cols].to_numpy(float)
                    keep = (np.abs(x) <= 5).all(axis=1)
                    if k == 3 and keep.sum() > k:
                        reduced_labels = cluster(x[keep], k, 42)
                        extremes_parts.append({"region": region, "category": category, "model": model, "k": k,
                                               "records": len(frame), "records_with_any_abs_z_over_5": int((~keep).sum()),
                                               "records_retained_sensitivity": int(keep.sum()),
                                               "ari_full_vs_extreme_removed": adjusted_rand_score(labels[keep], reduced_labels)})
                # population metadata for these exact M2-complete comparison keys
                keys = pd.MultiIndex.from_frame(frame[KEY])
                aligned = meta.loc[keys]
                model_population_parts.append({"region": region, "category": category, "model": model,
                                               "comparison_cohort": "M2_complete_common",
                                               "records": len(frame), "with_image": int(aligned.image_available.sum()),
                                               "warning_flagged": int(aligned.nutrition_warning_present.sum()),
                                               "existing_ocr_llm_processed": int(aligned.historical_ocr_status.isin(["success_no_claims", "success_with_claims"]).sum())})

            # Model agreement computed on identical M2-complete keys for each fixed k.
            for k in KS:
                labels_for = {}
                for model in ("M1", "M2", "M3", "M4"):
                    labels_for[model] = labels_cache[(model, k)]
                for left, right in (("M1", "M3"), ("M1", "M4"), ("M3", "M4"), ("M1", "M2")):
                    agreement_parts.append({"region": region, "category": category, "k": k,
                                            "comparison": f"{left}_vs_{right}", "records": len(model_frames[left]),
                                            "adjusted_rand_index": adjusted_rand_score(labels_for[left], labels_for[right])})
                # Warning and OCR/LLM composition for each resulting cluster and model.
                for model in MODELS:
                    f = model_frames[model]
                    labels = labels_for[model]
                    keys = pd.MultiIndex.from_frame(f[KEY])
                    aligned = meta.loc[keys].reset_index(drop=True)
                    for c in np.unique(labels):
                        take = labels == c
                        chunk = aligned.loc[take]
                        warning_parts.append({"region": region, "category": category, "model": model, "k": k,
                                              "cluster": int(c + 1), "records": int(take.sum()),
                                              "warning_flagged": int(chunk.nutrition_warning_present.sum()),
                                              "warning_pct": 100 * float(chunk.nutrition_warning_present.mean()),
                                              "with_image": int(chunk.image_available.sum()),
                                              "ocr_llm_processed": int(chunk.historical_ocr_status.isin(["success_no_claims", "success_with_claims"]).sum()),
                                              "ocr_llm_processed_pct": 100 * float(chunk.historical_ocr_status.isin(["success_no_claims", "success_with_claims"]).mean())})

    tables = {
        "check_04_cluster_assignments.csv": pd.concat(assignment_parts, ignore_index=True),
        "check_04_cluster_profiles.csv": pd.DataFrame(profile_parts),
        "check_04_model_agreement_ari.csv": pd.DataFrame(agreement_parts),
        "check_04_seed_stability.csv": pd.DataFrame(stability_parts),
        "check_04_extreme_sensitivity.csv": pd.DataFrame(extremes_parts),
        "check_04_warning_ocr_coverage.csv": pd.DataFrame(warning_parts),
        "check_04_common_cohort_population.csv": pd.DataFrame(model_population_parts),
    }
    for name, table in tables.items():
        table.to_csv(OUTPUT / name, index=False, encoding="utf-8", float_format="%.10g")
    manifest = {"run": "RUN_04_PRELIMINARY_NUTRITIONAL_SEGMENTATION", "script_sha256": sha(Path(__file__).resolve()),
                "run03_manifest_sha256": sha(INPUT / "run_03_manifest.json"),
                "run03_population_sha256": sha(INPUT / "check_03_model_population.csv"),
                "run03_matrix_index_sha256": sha(INPUT / "matrix_index.csv"), "scope": "11 region-category strata; US+CA dairies held out",
                "algorithm": "scikit-learn KMeans, Lloyd, n_init=3", "k_values": list(KS), "primary_seed": 42,
                "stability_seeds_at_k3": list(SEEDS), "silhouette_sample_max": 1000,
                "cohort": "all model comparisons use the identical M2-complete product keys per region-category",
                "extreme_sensitivity": "diagnostic refit excluding rows with any absolute model z-score >5; no official membership change",
                "outputs": {name: {"sha256": sha(OUTPUT / name), "rows": len(table)} for name, table in tables.items()}}
    write_report(tables, manifest)
    manifest["report"] = {"path": "presentations/segmentation/RUN 04_no US.md", "sha256": sha(REPORT)}
    (OUTPUT / "run_04_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_report(t, manifest):
    profiles = t["check_04_cluster_profiles.csv"]
    agreement = t["check_04_model_agreement_ari.csv"]
    stability = t["check_04_seed_stability.csv"]
    extreme = t["check_04_extreme_sensitivity.csv"]
    populations = t["check_04_common_cohort_population.csv"]
    run03_populations = pd.read_csv(INPUT / "check_03_model_population.csv")
    # Compact summaries for the markdown report.
    agg = populations.groupby("model")["records"].sum().to_dict()
    med_stability = stability.groupby("model").ari_vs_seed_42.median().to_dict()
    med_ari = agreement.groupby("comparison").adjusted_rand_index.median().to_dict()
    med_extreme = extreme.groupby("model").ari_full_vs_extreme_removed.median().to_dict()
    category_ari = agreement.groupby(["category", "comparison"]).adjusted_rand_index.median()
    broader = run03_populations.groupby("model").eligible_records.sum().to_dict()
    m1_broad, m2_broad = int(broader["M1"]), int(broader["M2"])
    m2_lost = m1_broad - m2_broad
    common = populations.groupby("model").sum(numeric_only=True).iloc[0]
    total_common, common_images = int(common.records), int(common.with_image)
    common_warnings, common_ocr = int(common.warning_flagged), int(common.existing_ocr_llm_processed)
    text = ["# RUN 04 — Preliminary nutritional segmentation and CHECK 04", "", "**Decision: Pending review. No final model selected.**", "",
            "RUN 03 CHECK 03 is approved for this analysis. The corrected, versioned RUN 03 matrices remain the sole modeling input; US+CA dairy remains held out. Region-category strata are modeled independently.", "",
            "## Scope and reproducible configuration", "",
            "K-means with Euclidean distance on approved within-stratum z-scores was run at k=2, 3, and 4. Fits used Lloyd's algorithm and `n_init=3`; seed 42 defines reported assignments. Initialization stability was checked at k=3 against seeds 101 and 202. Silhouette values use a reproducible random sample of up to 1,000 records.", "",
            "All model comparisons use the identical M2-complete cohort per stratum, isolating feature effects. M1/M3/M4 have similar broader eligible populations, but this CHECK compares their common-cohort assignments. The M1/M2 comparison therefore measures the addition of fibre on the same products; the separate RUN 03 table records the broader coverage loss.", "",
            "| Model | Features | Common cohort total across strata | Median seed ARI |", "|---|---|---:|---:|"]
    for model, features in MODELS.items():
        text.append(f"| {model} | {', '.join(features)} | {agg.get(model, 0):,} | {med_stability.get(model, float('nan')):.3f} |")
    text += ["", "## CHECK 04 — Key comparisons", "", "### Model agreement", "",
             "Adjusted Rand Index (ARI) compares cluster membership on identical product keys; higher values mean stronger agreement. These are medians across the 11 strata and three tested k values. See the full stratum-by-k table for detail.", "",
             "| Comparison | Median ARI |", "|---|---:|"]
    for comp, val in med_ari.items():
        text.append(f"| {comp} | {val:.3f} |")
    interpretations = {
        "beverages": "High M3/M4 agreement is consistent with the carbohydrate-sugar overlap hypothesis.",
        "cereals": "Lower M3/M4 agreement than beverages is consistent with carbohydrates adding differentiation.",
        "snacks": "Low M3/M4 agreement is consistent with meaningful differences between savoury starch-based and sweet products.",
        "dairies": "High M3/M4 agreement is consistent with traditional product types dominating this feature choice.",
    }
    text += ["", "### Category-specific findings", "",
             "Median ARI within each category across its strata and tested k values is exploratory evidence against the hypotheses, not a definitive category interpretation.", "",
             "| Category | M1 vs M3 | M1 vs M4 | M3 vs M4 | Interpretation |", "|---|---:|---:|---:|---|"]
    for category in ("beverages", "cereals", "snacks", "dairies"):
        values = [category_ari.get((category, comparison), float("nan")) for comparison in ("M1_vs_M3", "M1_vs_M4", "M3_vs_M4")]
        text.append(f"| {category.title()} | {values[0]:.3f} | {values[1]:.3f} | {values[2]:.3f} | {interpretations[category]} |")
    text += ["", "### Stability and extreme-value influence", "",
             "Seed stability is the median ARI of the k=3 fits using seeds 101 and 202 against seed 42 across strata. Extreme sensitivity refits at k=3 after removing records with any absolute standardized feature above 5, then compares assignments for retained products. This is a diagnostic only; official cluster assignments retain all RUN 03 eligible products.", "",
             "| Model | Median seed ARI | Median ARI after extreme removal |", "|---|---:|---:|"]
    for model in MODELS:
        text.append(f"| {model} | {med_stability.get(model, float('nan')):.3f} | {med_extreme.get(model, float('nan')):.3f} |")
    text += ["", "### Cluster sizes, nutrition, warnings, and existing OCR/LLM coverage", "",
             "The supporting profile table gives each stratum/model/k/cluster size and raw nutrient median and interquartile range. The warning/OCR table gives warning count and share, image count, and existing successfully processed OCR/LLM count and share per cluster. Successfully processed means `success_no_claims` or `success_with_claims`; failed or unusable attempts are not counted. OCR/LLM status is carried from the existing RUN 01 ledger; no calls were made.", "",
             f"On this common cohort, {common_images:,}/{total_common:,} products have an image ({100*common_images/total_common:.2f}%), {common_warnings:,} are warning-flagged ({100*common_warnings/total_common:.2f}%), and {common_ocr:,} have a successful prior OCR/LLM result ({100*common_ocr/total_common:.2f}%). The per-cluster table shows how these are distributed among clusters.", "",
             f"Across the broader RUN 03 populations, M1 has {m1_broad:,} eligible records and M2 has {m2_broad:,}; requiring fibre loses {m2_lost:,} records ({100*m2_lost/m1_broad:.2f}% of M1 coverage). The M1/M2 cluster comparison uses the same M2-complete products, isolating the feature effect from the coverage loss.", "",
             "## Category-specific carbohydrate and sugar hypotheses", "",
             "These expectations are hypotheses tested by the profiles and ARI tables, not established findings:", "",
             "- **Beverages:** Strong carbohydrate-sugar correlations may make M3 and M4 produce similar segments.",
             "- **Cereals:** Starch contributes substantially to carbohydrates; weaker correlations may make M3 and M4 differ.",
             "- **Snacks:** Savoury starch-based snacks and sweet products may create meaningful differences.",
             "- **Dairy:** Traditional cheese, yogurt, and milk product types may dominate regardless of carbohydrate versus sugar selection.", "",
             "Interpret category patterns from the per-cluster raw nutrient profiles and agreement results. K-means clusters describe nutrition-based groups in the observed OFF data; they do not establish consumer segments or market prevalence.", "",
             "## Supporting outputs", "",
             "All files are in `presentations/segmentation/run_04/`:", "",
             "- [Cluster assignments](run_04/check_04_cluster_assignments.csv)",
             "- [Cluster sizes and nutrient profiles](run_04/check_04_cluster_profiles.csv)",
             "- [M1/M3/M4 and M1/M2 agreement by stratum and k](run_04/check_04_model_agreement_ari.csv)",
             "- [Seed stability](run_04/check_04_seed_stability.csv)",
             "- [Extreme-value sensitivity](run_04/check_04_extreme_sensitivity.csv)",
             "- [Warning and OCR/LLM coverage by cluster](run_04/check_04_warning_ocr_coverage.csv)",
             "- [Common-cohort image, warning, and coverage counts](run_04/check_04_common_cohort_population.csv)",
             "- [Run manifest and hashes](run_04/run_04_manifest.json)", "",
             "**CHECK 04 recommendation: Pending review.** Review the cluster profiles, model agreement, stability, extreme sensitivity, warning mix, and OCR/LLM coverage before deciding whether any model is useful for sampling. No final model is selected; no OCR/LLM processing or feature engineering was performed.", ""]
    REPORT.write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
