"""
Market Overview — SCAFFOLD ONLY, not yet built.

Planned content (pending confirmation): brand/category-level claim
territory shares, pack-claim coverage, and benchmark intersection
rates, sourced from `weekly_brand_positioning_summary` and
`positioning_example_products` (the final reporting tables built by
db_summary.py — see docs/METHODOLOGY.md's "Reporting layers" section).
Deliberately NOT querying `weekly_brand_summary`, which is an
ingredient-stage-only QA table, not the final market-intelligence
summary (see ADR-007/ADR-012 in docs/ADR.md).

Standing rule for whenever this page is built: always show
coverage/denominator context alongside any rate or percentage, not the
rate in isolation. A "68% have a protein claim" figure reads very
differently depending on what it's a percentage of.
`weekly_brand_positioning_summary` already has denominator-paired
columns for exactly this purpose (confirmed against
database/schema.sql — nothing here needs to be added to the pipeline,
just used correctly when this page is built):
- `product_count` — the base population for any category/brand-level rate
- `pack_analyzed_count` / `pct_pack_analyzed` — how much of that
  population actually went through vision analysis
- `positioning_gap_scored_count` / `pct_positioning_gap_scored` —
  denominator for any positioning-composition-gap aggregate
- `pct_with_pack_claims_among_analyzed` — claim-presence rate scoped
  to analyzed products specifically, not diluted by never-analyzed ones
This applies to every aggregate figure on this page, not just one
chart — a rate without its denominator is exactly the kind of
unscoped, verdict-flavored number the no-blame brief is meant to rule
out.
"""

from __future__ import annotations

import streamlit as st

from shared import components, db

components.inject_base_css()
components.render_header(
    "Market Overview",
    "Category, brand, and claim-positioning patterns across the observed product database.",
)

st.info(
    "Not built yet. Planned: claim-territory distribution by category, "
    "brand-level benchmark intersection rates, and the curated examples "
    "from `positioning_example_products`, all sourced from "
    "`weekly_brand_positioning_summary` once `db_summary.py` has been run "
    "against a populated database."
)

if db.database_exists():
    st.caption("A local database was found — this page just hasn't been built against it yet.")
