"""Bounded Thursday research: recorded NOVA association and two text-only boundaries.

Writes only this folder's four named outputs. No source edits, providers or images.
Run from the repository: .venv/Scripts/python.exe -B <this script>
"""
from pathlib import Path
from datetime import date
import hashlib
import json
import re
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import fisher_exact

HERE = Path(__file__).resolve().parent
LENSES = HERE.parent
L1 = LENSES / "01_nutritional_composition"
L3 = LENSES / "03_claims_composition_and_ingredients"
EDA = LENSES.parent / "02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"
sys.path[:0] = [str(EDA), str(L3)]
sys.path.insert(0,str(L1))
from shared_feature_diagnostics_v1 import KEY, MASTER, read_master
from communication_coverage_v1 import load_module
from communication_overlays_v1 import digest, diff_interval
from juice_classification_v1 import cues as beverage_cues, decide as juice_decide

snack_rules = load_module(L1 / "savoury_snacks_v1.py")
juice_rules = load_module(L1 / "juice_formulations_v1.py")
biscuit_rules = load_module(L1 / "biscuits_and_wafers_v1.py")
dairy_rules = load_module(LENSES / "02_nutrient_density/dairy_dessert_formulations_v1.py")
norm = snack_rules.norm
REGIONS = ["FR", "UK-IE", "US-CA"]
FLOOR = 20
METRICS = ["energy", "sugars", "fat", "saturated_fat", "salt", "protein", "fibre"]
NAMED = {"juice", "nectar", "fruit drink", "smoothie"}


def has(text, pattern):
    return bool(re.search(pattern, text))


def table(head, rows):
    def clean(v):
        return str(v).replace("|", "/").replace("\n", " ")
    return "\n".join("| " + " | ".join(map(clean, row)) + " |" for row in [head, ["---"] * len(head), *rows])


def num(v, places=1):
    return f"{v:.{places}f}" if pd.notna(v) else "—"


def commercial_partition(df, beverage, snacks, juice):
    """One type per assignment, reusing accepted definitions; no nutrition thresholds."""
    a = df.copy()
    a["commercial_type"] = np.where(a.peer, a.subtype, "unresolved: " + a.subtype)
    a["type_source"] = "shared baseline"
    a["comparison_eligible_type"] = a.peer
    # These parents combine materially different commercial types; retain coverage only.
    broad = {"CHEESE", "YOGURT_CULTURED_FRESH", "CHOCOLATE_CONFECTIONERY", "CEREAL_PROTEIN_SNACK_BAR",
             "SWEET_BAKERY", "SUGAR_CONFECTIONERY", "FRUIT_SNACKS", "FROZEN_DESSERT", "PUFFED"}
    a.loc[a.subtype.isin(broad), "comparison_eligible_type"] = False
    dessert = a.peer & a.category.eq("dairy") & a.subtype.eq("DAIRY_DESSERT")
    a.loc[dessert, "commercial_type"] = a.loc[dessert].apply(dairy_rules.classify, axis=1)
    a.loc[dessert, "type_source"] = "accepted dairy classifier"
    biscuit = a.peer & a.category.eq("snacks") & a.subtype.eq("BISCUITS_WAFERS")
    a.loc[biscuit, "commercial_type"] = [biscuit_rules.classify(r)[0] for r in a.loc[biscuit].itertuples()]
    a.loc[biscuit, "type_source"] = "accepted biscuit/wafer classifier"
    for labels, col, source in [(snacks, "savoury_format", "saved savoury assignments"),
                                 (beverage, "analytical_format", "saved beverage assignments"),
                                 (juice, "juice_subformat", "saved juice refinements")]:
        z = a[KEY].merge(labels[KEY + [col]], on=KEY, how="left", validate="one_to_one")[col]
        take = z.notna() & z.ne("outside screen")
        # Sweet/mixed snack caution is not a substitute for the existing biscuit classification.
        if col == "savoury_format":
            take &= ~biscuit & ~z.isin(["scope caution", "scope unresolved"])
        a.loc[take, "commercial_type"] = z.loc[take].to_numpy()
        a.loc[take, "type_source"] = source
        a.loc[take, "comparison_eligible_type"] = True
    bad = a.commercial_type.str.contains("unresolved|unspecified|ambiguous|conflict|concern|caution|other|alcohol:", case=False, regex=True)
    a.loc[bad | ~a.membership.eq("YES"), "comparison_eligible_type"] = False
    # No measurement-complete filter: this is a processing/communication comparison.
    return a


def organic_nova(a):
    rows = []
    gate = a.assessed_layer & a.claims_source_market_limitation.fillna("").eq("")
    state = pd.Series("UNASSESSED", index=a.index)
    state.loc[a.assessed_layer & ~gate] = "MARKET_LIMITED"
    state.loc[gate] = "OTHER_UNKNOWN_ASSESSED"
    state.loc[gate & a.claims_state_organic_claim.eq("UNCERTAIN").fillna(False)] = "UNCERTAIN"
    state.loc[gate & a.claims_claim_organic_claim.eq(False).fillna(False) &
              a.claims_state_organic_claim.eq("HUMAN_CONFIRMED_NEGATIVE").fillna(False)] = "HUMAN_NEGATIVE_SEPARATE"
    state.loc[gate & a.claims_claim_organic_claim.eq(False).fillna(False) &
              a.claims_state_organic_claim.eq("DOCUMENTED_NOT_DETECTED").fillna(False)] = "DOCUMENTED_NON_DETECTION"
    state.loc[gate & a.claims_claim_organic_claim.eq(True).fillna(False)] = "POSITIVE"
    a["organic_status"] = state
    a["nova_valid"] = a.nova_group.isin([1, 2, 3, 4])
    for (category, form, region), g in a.groupby(["category", "commercial_type", "region"]):
        pos = g.organic_status.eq("POSITIVE")
        neg = g.organic_status.eq("DOCUMENTED_NON_DETECTION")
        known = pos | neg
        nova = g.nova_valid
        n, m = int((pos & nova).sum()), int((neg & nova).sum())
        x, y = int((pos & nova & g.nova_group.eq(4)).sum()), int((neg & nova & g.nova_group.eq(4)).sum())
        comparable = bool(g.comparison_eligible_type.all())
        supported = comparable and min(n, m) >= FLOOR
        decision = "retain selected-evidence comparison" if supported and region != "US-CA" else (
            "descriptive only: exploratory US-CA comparison" if supported else
            "descriptive only: heterogeneous or unresolved parent" if not comparable else "insufficient evidence")
        row = dict(category=category, commercial_type=form, region=region, full_commercial_n=len(g),
                   organic_positive_n=int(pos.sum()), organic_documented_non_detection_n=int(neg.sum()),
                   organic_known_n=int(known.sum()), organic_unknown_n=int((~known).sum()),
                   nova_known_n=int(nova.sum()), nova_missing_n=int(g.nova_group.isna().sum()),
                   nova_invalid_n=int((g.nova_group.notna() & ~nova).sum()),
                   organic_positive_nova_missing_or_invalid_n=int((pos & ~nova).sum()),
                   organic_non_detection_nova_missing_or_invalid_n=int((neg & ~nova).sum()),
                   jointly_known_n=int((known & nova).sum()), joint_organic_positive_n=n,
                   joint_non_detection_n=m, organic_positive_nova4_n=x, non_detection_nova4_n=y,
                   organic_positive_nova4_pct=100*x/n if n else np.nan,
                   non_detection_nova4_pct=100*y/m if m else np.nan,
                   joint_unknown_organic_nova_known_n=int((~known & nova).sum()),
                   comparable_type=comparable, two_arm_floor=supported, decision=decision,
                   type_source="; ".join(sorted(g.type_source.unique())),
                   risk_difference_pp=np.nan, ci_low_pp=np.nan, ci_high_pp=np.nan, p=np.nan, q=np.nan)
        for s in ["UNASSESSED", "MARKET_LIMITED", "OTHER_UNKNOWN_ASSESSED", "UNCERTAIN", "HUMAN_NEGATIVE_SEPARATE"]:
            row["organic_" + s.lower() + "_n"] = int(g.organic_status.eq(s).sum())
        assert row["organic_positive_n"] + row["organic_documented_non_detection_n"] + sum(
            row["organic_" + s.lower() + "_n"] for s in ["UNASSESSED", "MARKET_LIMITED", "OTHER_UNKNOWN_ASSESSED", "UNCERTAIN", "HUMAN_NEGATIVE_SEPARATE"]) == len(g)
        assert row["nova_known_n"] + row["nova_missing_n"] + row["nova_invalid_n"] == len(g)
        assert n + m == row["jointly_known_n"]
        if supported:
            lo, hi = diff_interval(x, n, y, m)
            row.update(risk_difference_pp=100*(x/n-y/m), ci_low_pp=100*lo, ci_high_pp=100*hi,
                       p=fisher_exact([[x, n-x], [y, m-y]])[1])
        rows.append(row)
    result = pd.DataFrame(rows)
    # Only supported primary comparisons form the multiple-testing family.
    ix = result.index[result.two_arm_floor & result.region.ne("US-CA")]
    ix = result.loc[ix].sort_values("p").index
    if len(ix):
        q = np.minimum.accumulate((result.loc[ix, "p"].to_numpy()*len(ix)/np.arange(1, len(ix)+1))[::-1])[::-1]
        result.loc[ix, "q"] = np.minimum(q, 1)
    assert result.full_commercial_n.sum() == len(a) == 376845
    return result


def juice_boundary(row):
    n, t = beverage_cues(row.product_name), beverage_cues(row.off_categories, True)
    hits = n | t
    current = row.analytical_format
    candidate = current in NAMED or current == "juice family unresolved" or bool(hits)
    if not candidate: return None
    primary = "UNRESOLVED"
    nested = len(t) > 1 and "juice" in t and len(t - {"juice"}) == 1
    adjacent = has(norm(row.product_name)+" "+norm(row.off_categories),
        r"\b(?:iced tea|the glace|sodas?|soft drinks?|tonic|limonades?|citronnades?|boissons? gazeuses?|energy drinks?|sports? drinks?|gatorade|powerade|boissons? energisantes?|coconut water|eau de coco|almondmilk|almond milk|coffee smoothie|fruit drink water|flavou?red water|sparkling water)\b")
    other_use = has(norm(row.product_name), r"\b(?:salads?|salades?|soups?|soupes?|sauces?|smoothie bowls?|eau de vie|culinary|cooking)\b")
    if row.membership != "YES" or row.basis_group != "per_100ml_liquid" or current.startswith("alcohol:") or other_use:
        status = "scope or preparation-basis concern"
    elif adjacent and current not in NAMED and hits:
        status = "adjacent commercial identity with juice-family wording"
    elif len(n) > 1:
        status = "multiple name identities: possible commercial overlap"
    elif len(n) == 1 and len(t) == 1 and n != t:
        status = "conflicting name and specific tags"
    elif len(hits) == 1:
        primary = next(iter(hits))
        status = "supported identity" if current == primary else "apparent analytical-label mismatch"
    elif nested and (not n or n <= t):
        child = next(iter(t - {"juice"}))
        if n == {"juice"}:
            status = "conflicting juice name and more-specific child tags"
        else:
            primary = child
            status = "nested/overlapping juice-family tags"
    elif len(hits) > 1:
        status = "overlapping or conflicting tags: unresolved"
    else:
        status = "insufficient specific identity evidence"
    # Use exactly the same resolved/unknown decision as the corrected beverage builder.
    if getattr(row,"juice_family_review_scope",False):
        decision=juice_decide(row.product_name,row.off_categories)
        primary=decision["identity"] if decision["identity"] in NAMED else "UNRESOLVED"
        status="supported corrected identity" if primary!="UNRESOLVED" else decision["reason"]
    # Explicit culinary/dilution/other-use cues remain flags, not reclassification.
    caution = has(norm(row.product_name), r"\b(?:syrup|sirop|cordial|powder|poudre|concentre a diluer|a diluer|cooking|culinary|sauce|vinaigr|bouillon)\b")
    original=getattr(row,"original_analytical_format",current)
    return dict(boundary_family="juice family", original_format=original,current_format=current,
                correction_applied=original!=current,
                name_evidence="; ".join(sorted(n)), tag_evidence="; ".join(sorted(t)),
                independently_named=bool(n), independently_tagged=bool(t),
                name_tag_corroborated=bool(n & t), primary_identity=primary, boundary_status=status,
                overlap_flag=len(hits) > 1, unresolved_flag=primary == "UNRESOLVED",
                separate_use_caution=caution, potato_base_evidence="", construction="",
                crisp_descriptor=False, named_composition="; ".join(sorted(set().union(*juice_rules.detect(norm(row.product_name)+" "+norm(row.off_categories))))))


def potato_signals(text):
    t = norm(text)
    t = re.sub(r"cereals and potatoes|cereales et pommes de terre|potatoes and their products|chips and fries|chips et frites", " ", t)
    # Sweet potato is a distinct base, not evidence for this potato boundary.
    t = re.sub(r"sweet potato(?:es)?|patates? douces?", " otherbase ", t)
    potato = has(t, r"\b(?:potato(?:es)?|pommes? de terre|patatas?)\b")
    crisp = has(t, r"\b(?:chips?|crisps?)\b")
    popped = has(t, r"\b(?:popped|poppe\w*|pop chips?|pop'd)\b") and not has(t, r"\bpop ?corn\b")
    formed = has(t, r"\b(?:extrud\w*|puffed|souffle\w*|stacked|reconstitue\w*|potato (?:hoops?|spirals?|rings?))\b")
    # Fried/baked can coexist with extrusion, so neither establishes a sliced identity.
    sliced = has(t, r"\b(?:kettle|hand cooked|sliced|tranche\w*)\b")
    otherbase = has(t, r"\b(?:lentil|chickpea|corn|rice|mais|lentilles?|pois chiches?|wheat|ble|soy|soja|otherbase)\b")
    return potato, crisp, popped, formed, sliced, otherbase


def potato_boundary(row):
    n, t = potato_signals(row.product_name), potato_signals(row.off_categories)
    p, c, popped, formed, sliced, other = [u or v for u, v in zip(n, t)]
    current = row.savoury_format
    candidate = current in {"potato crisps", "puffed/extruded"} or (p and (c or popped or formed))
    if not candidate: return None
    construction = "; ".join(k for k, yes in [("popped", popped), ("puffed/extruded/stacked", formed), ("sliced/kettle wording", sliced)] if yes) or "unspecified"
    primary = "UNRESOLVED"
    if row.membership != "YES" or current in {"scope caution", "scope unresolved"}:
        status = "scope concern"
    elif n[5] and not n[0] and t[0] and not t[5]:
        status = "conflicting name/tag base evidence"
    elif p and (popped or formed) and sliced:
        status = "conflicting or mixed construction evidence"
    elif p and (popped or formed):
        primary = "potato popped/extruded construction"
        status = "supported construction with overlapping crisp descriptor" if c else "supported potato construction"
    elif p and c:
        primary = "potato crisps: construction unspecified" if not sliced else "potato crisps: sliced/kettle wording"
        status = "supported potato-crisp identity"
    elif p:
        status = "potato base known; snack construction unresolved"
    elif other:
        primary = "other-base puffed snack: outside potato comparison"
        status = "independent other-base evidence"
    else:
        status = "insufficient potato-base evidence"
    return dict(boundary_family="potato constructions", original_format=current,
                name_evidence="; ".join(k for k, y in zip(["potato", "crisp", "popped", "puffed/extruded/stacked", "sliced/kettle", "other base"], n) if y),
                tag_evidence="; ".join(k for k, y in zip(["potato", "crisp", "popped", "puffed/extruded/stacked", "sliced/kettle", "other base"], t) if y),
                independently_named=bool(n[0] and any(n[1:5])), independently_tagged=bool(t[0] and any(t[1:5])),
                name_tag_corroborated=bool(n[0] and any(n[1:5]) and t[0] and any(t[1:5])), primary_identity=primary, boundary_status=status,
                overlap_flag=bool(p and c and (popped or formed)), unresolved_flag=primary == "UNRESOLVED",
                separate_use_caution=False, potato_base_evidence="name+tags" if n[0] and t[0] else "name" if n[0] else "tags" if t[0] else "none",
                construction=construction, crisp_descriptor=c, mixed_base_flag=p and other,
                baked_wording=has(norm(row.product_name)+" "+norm(row.off_categories),r"\b(?:baked|au four)\b"),
                named_composition="")


def boundary_layer(a, beverage, snacks):
    base = a[KEY + ["product_name", "off_categories", "basis_group", "membership"] + METRICS]
    layers = []
    for labels, col, function in [(beverage, "analytical_format", juice_boundary), (snacks, "savoury_format", potato_boundary)]:
        extra=["original_analytical_format","juice_family_review_scope"] if col=="analytical_format" else []
        g = base.merge(labels[KEY + [col]+extra], on=KEY, validate="one_to_one")
        rows, positions = [], []
        for i, row in enumerate(g.itertuples(index=False)):
            result = function(row)
            if result is not None: rows.append(result); positions.append(i)
        b = pd.concat([g.iloc[positions].drop(columns=[col]).reset_index(drop=True), pd.DataFrame(rows)], axis=1)
        layers.append(b)
    result = pd.concat(layers, ignore_index=True)
    result["current_format"]=result.current_format.fillna(result.original_format)
    assert not result.duplicated(KEY + ["boundary_family"]).any()
    assert (result.name_tag_corroborated <= result.independently_named).all()
    assert (result.name_tag_corroborated <= result.independently_tagged).all()
    return result


def boundary_summary(b, a):
    rows = []
    for (category, region), g in a[a.category.isin(["beverages", "snacks"])].groupby(["category", "region"]):
        family = "juice family" if category == "beverages" else "potato constructions"
        screened = b[b.boundary_family.eq(family) & b.region.eq(region)]
        rows.append(dict(record_kind="screen denominator", boundary_family=family, region=region,
                         group="entire governed " + category, n=len(g), boundary_candidate_n=len(screened)))
    for (family, region, origin), g in b.groupby(["boundary_family", "region", "original_format"]):
        rows.append(dict(record_kind="origin population", boundary_family=family, region=region, original_format=origin,
                         group=origin, n=len(g), independently_named_n=int(g.independently_named.sum()),
                         independently_tagged_n=int(g.independently_tagged.sum()),
                         corroborated_n=int(g.name_tag_corroborated.sum()), overlap_n=int(g.overlap_flag.sum()),
                         unresolved_n=int(g.unresolved_flag.sum())))
        for status, z in g.groupby("boundary_status"):
            rows.append(dict(record_kind="origin status", boundary_family=family, region=region, original_format=origin,
                             group=status, n=len(z)))
        for identity, z in g.groupby("primary_identity"):
            rows.append(dict(record_kind="origin to independent identity", boundary_family=family, region=region,
                             original_format=origin, group=identity, n=len(z)))
        for current,z in g.groupby("current_format"):
            rows.append(dict(record_kind="original to corrected format",boundary_family=family,region=region,
                             original_format=origin,group=current,n=len(z)))
    # Consequences only. Reuse shared validity masks; same measurement basis in each comparison.
    for (family, region), g in b.groupby(["boundary_family", "region"]):
        if family == "juice family":
            comparable = g.basis_group.eq("per_100ml_liquid") & g.membership.eq("YES")
            sets = {"current juice (corrected assignment)": g[g.current_format.eq("juice") & comparable],
                    "current fruit drink (corrected assignment)": g[g.current_format.eq("fruit drink") & comparable],
                    "original juice assignment":g[g.original_format.eq("juice") & comparable],
                    "original fruit drink assignment":g[g.original_format.eq("fruit drink") & comparable],
                    "independently supported juice (all origins)": g[g.primary_identity.eq("juice") & comparable & ~g.separate_use_caution],
                    "current juice with unresolved text excluded": g[g.current_format.eq("juice") & ~g.unresolved_flag & comparable & ~g.separate_use_caution],
                    "independent nectar": g[g.primary_identity.eq("nectar") & comparable],
                    "independent fruit drink": g[g.primary_identity.eq("fruit drink") & comparable],
                    "independent smoothie": g[g.primary_identity.eq("smoothie") & comparable]}
            basis = "per 100 ml; inherited comparable liquid basis"
        else:
            comparable = g.basis_group.eq("per_100g_food") & g.membership.eq("YES")
            g = g[comparable]
            constructed = g.primary_identity.eq("potato popped/extruded construction")
            sets = {"current potato crisps": g[g.original_format.eq("potato crisps")],
                    "supported potato crisps without explicit formed construction": g[g.primary_identity.str.startswith("potato crisps:")],
                    "explicit popped potato construction": g[constructed & g.construction.str.contains("popped")],
                    "explicit puffed/extruded/stacked potato; no popped wording": g[constructed & ~g.construction.str.contains("popped")],
                    "all supported potato constructions excluding unresolved/conflicting": g[~g.unresolved_flag & g.primary_identity.str.startswith("potato ")]}
            basis = "per 100 g"
        for name, z in sets.items():
            row = dict(record_kind="nutrition consequence", boundary_family=family, region=region, group=name, n=len(z), measurement_basis=basis)
            for metric in METRICS:
                row[metric + "_valid_n"] = int(z[metric].notna().sum())
                row[metric + "_median"] = z[metric].median()
            if family == "potato constructions":
                row["fat_le20_n"] = int(z.fat.le(20).sum())
                row["fat_le20_explicit_constructed_n"] = int((z.fat.le(20) & z.primary_identity.eq("potato popped/extruded construction")).sum())
                row["fat_le20_baked_wording_n"] = int((z.fat.le(20) & z.baked_wording.fillna(False)).sum())
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    inputs = [MASTER, MASTER.parent / "manifest.json", EDA / "subtype_assignments.csv",
              EDA / "shared_feature_diagnostics_v1.py", EDA / "nutrient_availability.csv",
              LENSES / "FORMULATION_DECISIONS_v1.csv", L3 / "communication_coverage_v1.py",
              L3 / "communication_overlays_v1.py", L3 / "human_claim_decisions_v1.csv",
              L3 / "human_claim_adjudications_v1.csv", L3 / "human_claim_review_v1.csv"]
    inputs += [L1 / f for f in ["beverage_assignments_v1.parquet", "savoury_snack_assignments_v1.parquet", "juice_assignments_v1.parquet",
                               "savoury_snacks_v1.py", "juice_formulations_v1.py", "biscuits_and_wafers_v1.py","juice_classification_v1.py","beverages_v1.py"]]
    inputs += [LENSES / "02_nutrient_density/dairy_dessert_formulations_v1.py",
               LENSES.parent / "01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/claims_join.parquet"]
    before = {p: digest(p) for p in inputs}
    human = pd.read_csv(L3 / "human_claim_adjudications_v1.csv", dtype=str, keep_default_na=False)
    submitted = pd.read_csv(L3 / "human_claim_decisions_v1.csv", dtype=str, keep_default_na=False)
    assert len(human) == len(submitted) == 12 and human.review_id.is_unique and not human.duplicated(KEY + ["proposition"]).any()
    assert set(human.review_id) == set(submitted.review_id)
    df, _ = read_master()
    names = pd.read_csv(EDA / "subtype_assignments.csv", dtype=str, keep_default_na=False, usecols=KEY + ["product_name", "off_categories"])
    df = df.merge(names, on=KEY, validate="one_to_one")
    # Organic basis/wording stays in the master; joined by exact original keys.
    extra = pq.read_table(MASTER, columns=KEY + ["claims_basis_organic_claim", "claims_core_claim_evidence_json"]).to_pandas()
    df = df.merge(extra, on=KEY, validate="one_to_one")
    beverage = pd.read_parquet(L1 / "beverage_assignments_v1.parquet")
    snacks = pd.read_parquet(L1 / "savoury_snack_assignments_v1.parquet")
    juice = pd.read_parquet(L1 / "juice_assignments_v1.parquet")
    a = commercial_partition(df, beverage, snacks, juice)
    organic = organic_nova(a)
    boundaries = boundary_layer(a, beverage, snacks)
    summary = boundary_summary(boundaries, a)
    assert sum(len(g) for _, g in a.groupby(["category", "commercial_type", "region"])) == 376845
    for (family, region, origin), g in boundaries.groupby(["boundary_family", "region", "original_format"]):
        z = summary[summary.record_kind.eq("origin status") & summary.boundary_family.eq(family) & summary.region.eq(region) & summary.original_format.eq(origin)]
        assert z.n.sum() == len(g)
    # A compact keyed table includes every organic-known record, plus every boundary candidate.
    evidence = a[a.organic_status.isin(["POSITIVE", "DOCUMENTED_NON_DETECTION", "HUMAN_NEGATIVE_SEPARATE"])][
        KEY + ["commercial_type", "type_source", "comparison_eligible_type", "organic_status", "nova_group", "nova_valid",
               "claims_basis_organic_claim", "claims_state_organic_claim", "claims_evidence_cohort", "claims_core_claim_evidence_json"]].copy()
    evidence["record_kind"] = "organic evidence"
    evidence["boundary_family"] = ""
    boundaries["record_kind"] = "boundary evidence"
    keyed = pd.concat([evidence, boundaries], ignore_index=True)
    assert not keyed.duplicated(KEY + ["record_kind"]).any()
    metadata = {str(p.relative_to(LENSES.parents[2])): h for p, h in before.items()}
    arrow = pa.Table.from_pandas(keyed, preserve_index=False)
    arrow = arrow.replace_schema_metadata({**(arrow.schema.metadata or {}), b"input_sha256": json.dumps(metadata, sort_keys=True).encode(),
                                           b"script_sha256": digest(Path(__file__)).encode()})
    pq.write_table(arrow, HERE / "processing_boundary_evidence_v1.parquet")
    organic.to_csv(HERE / "organic_nova_v1.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(HERE / "category_boundaries_v1.csv", index=False, encoding="utf-8-sig")
    saved = pd.read_parquet(HERE / "processing_boundary_evidence_v1.parquet")
    assert saved.barcode.equals(keyed.barcode) and not saved.duplicated(KEY + ["record_kind"]).any()
    assert {p: digest(p) for p in inputs} == before, "A protected source changed."
    write_check(organic, boundaries, summary, human, before, len(saved))
    print("PASS", len(organic), "organic cells;", len(boundaries), "boundary rows;", len(summary), "summary rows;", len(saved), "keyed evidence rows.")
    print(organic[organic.two_arm_floor | (organic.joint_organic_positive_n.ge(10) & organic.comparable_type)][[
        "category", "commercial_type", "region", "joint_organic_positive_n", "joint_non_detection_n", "risk_difference_pp", "p", "q", "decision"]].to_string(index=False))


def write_check(o, b, s, human, hashes, evidence_n):
    supported = o[o.two_arm_floor]
    close = o[o.comparable_type & ~o.two_arm_floor & o.joint_organic_positive_n.ge(10) & o.joint_non_detection_n.ge(10)]
    rows = []
    for r in pd.concat([supported, close]).sort_values(["category", "commercial_type", "region"]).itertuples():
        rows.append([r.commercial_type, r.region, r.full_commercial_n,
                     f"{r.organic_positive_n} / {r.organic_documented_non_detection_n} / {r.organic_unknown_n}",
                     f"{r.nova_known_n} / {r.nova_missing_n+r.nova_invalid_n}",
                     f"{r.organic_positive_nova4_n}/{r.joint_organic_positive_n} vs {r.non_detection_nova4_n}/{r.joint_non_detection_n}",
                     f"{num(r.risk_difference_pp)} [{num(r.ci_low_pp)}, {num(r.ci_high_pp)}]" if r.two_arm_floor else "not estimated",
                     r.decision])
    juice = b[b.boundary_family.eq("juice family")]
    potato = b[b.boundary_family.eq("potato constructions")]
    mismatch = juice[juice.original_format.eq("fruit drink") & juice.current_format.eq("juice")]
    mismatch_counts = "; ".join(f"{r}: {len(g):,}, including {int(g.name_tag_corroborated.sum()):,} name/tag-corroborated" for r in REGIONS for g in [mismatch[mismatch.region.eq(r)]])
    low = s[s.record_kind.eq("nutrition consequence") & s.group.eq("current potato crisps") & s.region.ne("US-CA")]
    low_text = "; ".join(f"{r.region}: {int(r.fat_le20_explicit_constructed_n)}/{int(r.fat_le20_n)} with explicit popped/puffed/extruded construction and {int(r.fat_le20_baked_wording_n)}/{int(r.fat_le20_n)} with baked wording" for r in low.itertuples())
    sections = ["# Processing and category boundaries — CHECK v1",
        f"Thursday 19 November scope, executed {date.today().isoformat()}. Corrected Wave 2: retrieved 17 October, cutoff 29 September 2026. **Complete for Julia's review; Friday consolidation has not started.**",
        table(["Question", "Decision", "Release implication"], [
            ["Organic × NOVA 4, French muesli", "RETAIN selected-evidence association", "Organic-positive: 6/24 NOVA 4; non-detection: 25/48. Evidence is narrow and not independently replicated in UK/IE."],
            ["US/CA granola", "DESCRIPTIVE ONLY", "Selected exploratory evidence; no population positioning or processing prevalence."],
            ["Other resolved organic/NOVA cells", "INSUFFICIENT EVIDENCE", "Joint arm sizes, not full product counts, limit comparison. Broad/unresolved parents stay descriptive."],
            ["Juice-family commercial boundaries", "RETAIN corrected analytical labels and unresolved flags", "Shared name/tag classifier corrected 19 November; original labels retained alongside corrected labels. See juice_classification_CHECK_v1.md. No source recategorization."],
            ["Potato constructions", "RETAIN commercial descriptors; DESCRIPTIVE ONLY nutritionally", "Popped, puffed/stacked and unspecified construction are not interchangeable. No new nutritional segment."],
            ["Human review", "RETAIN qualitative examples", "All 12 submitted observations and the interpreted sidecar remain separate and unchanged."]]),
        "## Organic × recorded NOVA 4",
        "Organic-positive means communication in the locked field; documented non-detection concerns only the assessed pack evidence, not proof that a product is non-organic. Compare these selected observations within region and commercial type. Recorded NOVA is a separate, crowdsourced attribute, partly dependent on ingredient information. This is not a healthfulness, causal or claim-compliance test. Unknown claims and missing NOVA stay outside the relevant comparison, without deletion from the master.",
        table(["Commercial type", "Region", "Full n", "Organic + / documented non-detection / unknown", "NOVA known / unavailable", "NOVA 4: organic+ vs non-detection", "Difference pp [95% CI]", "Decision"], rows),
        "Support floor, fixed before this comparison: at least 20 jointly known records in each arm and an adequately resolved commercial type. This is a pragmatic minimum, not a guarantee of representativeness or statistical power. Smaller arms retain counts only. Heterogeneous parent categories and unresolved types retain coverage without inferential promotion. US/Canada remains exploratory. No cross-format or cross-region pooled estimate is calculated.",
        "Supported cells use organic-positive minus documented-non-detection risk differences, Newcombe/Wilson 95% intervals and two-sided Fisher exact tests. Benjamini–Hochberg q values cover supported FR/UK comparisons only. Intervals describe sampling uncertainty conditional on these selected observations; they cannot remove selection bias. A non-significant result is not proof of equivalence.",
        table(["Type", "Region", "p", "q (primary family only)"], [[r.commercial_type, r.region, num(r.p, 5), num(r.q, 5)] for r in supported.itertuples()]),
        "All commercial types, including insufficient-evidence and parent-context rows, are retained in `organic_nova_v1.csv`. Its mutually exclusive organic states distinguish positive, documented non-detection, separate human-negative, uncertain, other assessed unknown, unassessed and market-limited records. NOVA 1–4 is recorded/available; missing and invalid codes are separate. Full populations form one disjoint 376,845-assignment partition. Nutrient completeness is not required. Exact organic state, basis, cohort and saved evidence JSON are retained in the keyed table; no human-review observations are merged into the locked comparison.",
        "## Category boundaries: two-sided text evidence",
        "The full governed beverage and snack populations were screened in both directions. Current labels, source name/tags, independent cues, derived identity and uncertainty stay separate. Parent tags are not proof of a specific child identity. Nutrition never enters classification. These are text-supported candidates, not final package adjudications; implicit or unrecognized-language descriptions can be missed. Counts are assignments, not market prevalence."]
    for family in ["juice family", "potato constructions"]:
        g = b[b.boundary_family.eq(family)]
        sides = ["juice", "nectar", "fruit drink", "smoothie"] if family == "juice family" else ["potato crisps", "puffed/extruded"]
        grouped = g.assign(side=np.where(g.original_format.isin(sides), g.original_format, "other current labels"))
        sections += ["### " + family.title(), table(["Region", "Full category screened", "Boundary candidates", "Name support", "Specific tag support", "Corroborated", "Overlap cues", "Unresolved identity"], [
            [r, int(s.loc[s.record_kind.eq("screen denominator") & s.boundary_family.eq(family) & s.region.eq(r), "n"].iloc[0]),
             len(z), int(z.independently_named.sum()), int(z.independently_tagged.sum()), int(z.name_tag_corroborated.sum()), int(z.overlap_flag.sum()), int(z.unresolved_flag.sum())]
            for r in REGIONS for z in [g[g.region.eq(r)]]]),
            table(["Original analytical side", "FR n", "UK/IE n", "US/CA n"], [[origin, *[int((grouped.side.eq(origin)&grouped.region.eq(r)).sum()) for r in REGIONS]] for origin in sides+["other current labels"]]),
            table(["Evidence outcome", "FR n", "UK/IE n", "US/CA n"], [[status, *[int((g.boundary_status.eq(status)&g.region.eq(r)).sum()) for r in REGIONS]] for status in sorted(g.boundary_status.unique())])]
    sections += ["## Nutrition describes consequences, not identity",
        table(["Boundary", "Region", "Population choice", "n", "Energy median (valid n)", "Sugars median (valid n)", "Fat median (valid n)", "Salt median (valid n)"], [
            [r.boundary_family, r.region, r.group, r.n, *[f"{num(getattr(r, m+'_median'),2)} ({int(getattr(r,m+'_valid_n'))})" for m in ["energy", "sugars", "fat", "salt"]]]
            for r in s[s.record_kind.eq("nutrition consequence") & s.region.ne("US-CA") & s.group.isin([
                "current juice (corrected assignment)", "current fruit drink (corrected assignment)", "independently supported juice (all origins)",
                "independent fruit drink", "current potato crisps", "explicit popped potato construction",
                "explicit puffed/extruded/stacked potato; no popped wording"])].itertuples()]),
        "**Juice correction, 19 November.** The shared classifier now prevents broad parent tags from overriding specific commercial identity. Original fruit-drink assignments now supported as juice: " + mismatch_counts + ". Original labels remain in the keyed audit and beverage file. Conflicting names/specific tags, insufficient evidence and incompatible intended-use wording remain unresolved. This is an analytical correction; governed source categories and observations are unchanged. Nested tags can describe compatible parent/child identities; juice wording in tea, coconut water or soda may indicate ingredients or overlapping propositions. Outside-family boundary flags do not automatically reclassify those products.",
        "The beverage/juice layers, nutrition summaries, claim coverage and recorded-NOVA denominators have been rebuilt from the corrected assignments. The bounded correction CHECK in 01_nutritional_composition gives before/after counts, retained findings, unresolved populations and validation. Comprehensive category cleanup stays deferred. No new juice nutritional profile is proposed; Friday consolidation has not started.",
        "**Potato finding.** A crisp descriptor can legitimately coexist with popped or extruded construction. Explicitly popped products have much lower median fat, but other puffed/stacked constructions need not. These descriptors explain some overlap, not the entire retained lower-fat profile. Among the existing lower-fat potato-crisp qualifiers: " + low_text + ". Construction wording is incomplete; absence of a cue is not proof of frying, slicing or recipe. Mixed base wording is separately flagged. Keep the accepted descriptive profile and the independent construction descriptor; do not assume extrusion means lower fat.",
        "Food figures are per 100 g and liquid figures use the inherited per-100-ml comparable-basis flag. Preparations, unresolved bases and scope concerns remain in the text-boundary audit but not numerical comparison. Validity masks are reused unchanged; nulls and zeros remain distinct. Different nutrient medians can use different available subsets. These sensitivities change analytical boundaries only; no source reclassification or accepted profile rule is changed.",
        "## Selected text examples",
        "Examples illustrate evidence outcomes, not verified package identities or a representative sample. No images were opened or assessed."]
    examples = []
    for family in ["juice family", "potato constructions"]:
        g = b[b.boundary_family.eq(family) & b.region.ne("US-CA")]
        wanted = {"apparent analytical-label mismatch", "conflicting name and specific tags", "nested/overlapping juice-family tags",
                  "adjacent commercial identity with juice-family wording", "supported construction with overlapping crisp descriptor",
                  "insufficient potato-base evidence", "conflicting name/tag base evidence"}
        for status in sorted(set(g.boundary_status.unique()) & wanted):
            z = g[g.boundary_status.eq(status)].copy()
            z["nonempty"] = z.product_name.fillna("").str.len().gt(3)
            for r in z.sort_values(["nonempty", "barcode"], ascending=[False, True]).head(1).itertuples():
                examples.append([family, f"`{r.barcode}` · {r.region} · {r.category}", r.product_name, r.original_format, r.primary_identity, status])
    sections += [table(["Boundary", "Exact key", "Name", "Current", "Independent interpretation", "Reason"], examples),
        "## Human evidence and source integrity",
        "Julia's 12 submitted observations and the separate interpreted sidecar are unchanged. They remain qualitative diagnostic examples; no expansion, new image assessment or update of locked negatives is made. Previously flagged date/key limitations remain. Neither human file enters organic/NOVA estimates.",
        f"Validation passed: master SHA-256, all 96 baseline category/region/nutrient validity counts, one-to-one commercial joins, disjoint organic-state and NOVA denominators, boundary-origin/status reconciliation, exact text-key Parquet round-trip ({evidence_n:,} keyed evidence rows), unique keys per evidence purpose, all 12 human review IDs and before/after hashes for every protected dependency. The Parquet schema metadata contains the full input-hash manifest and script hash.",
        "## Reproduce and handover",
        "Run `.venv/Scripts/python.exe -B presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/processing_boundaries_v1.py` from the repository. It writes only this CHECK, `organic_nova_v1.csv`, `category_boundaries_v1.csv` and `processing_boundary_evidence_v1.parquet`. The supporting CSV contains screen denominators, original-side/status cross-tabs, original-to-independent identities and nutrition consequences. Source wording is in the keyed table; source organic evidence is carried with its original field/state/basis and exact key.",
        "Master SHA-256: `" + hashes[MASTER] + "`. Human submission SHA-256: `" + hashes[L3 / "human_claim_decisions_v1.csv"] + "`. Interpreted sidecar SHA-256: `" + hashes[L3 / "human_claim_adjudications_v1.csv"] + "`.",
        "**STOP for Julia's review. No Friday consolidation, provider calls, new segmentation, master/reporting changes or source deletions.**"]
    (HERE / "processing_boundaries_CHECK_v1.md").write_text("\n\n".join(sections)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
