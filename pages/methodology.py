"""
Methodology — SCAFFOLD ONLY, not yet built out.

Confirmed 5-section structure for when this page is built:

1. What this tool is — neutral market intelligence for packaged food
   positioning. Not a regulatory, health, or consumer tool.
2. What it is not — not legal/regulatory assessment, not a health
   verdict, not a consumer recommendation, not product shaming.
3. How to read the metrics — plain-language cards for:
   - Claim taxonomy (claim_category_1 / claim_category_2)
   - Ingredient-processing markers (composition_marker_score/band)
   - Nutrition reference flags (nutrition_benchmark_flags via UK FSA thresholds)
   - Claim–reference intersections (claim_benchmark_intersections)
   - Positioning signal score (positioning_composition_gap + composite formula)
4. Evidence coverage — explain claim_source: vision-extracted vs.
   ingredient/name-derived fallback, and what that means for how
   much weight to put on a given product's claim category.
5. Data source and limitations — Open Food Facts, crowdsourced data
   quality, no sales-volume data, non-representative vision sample,
   geographic coverage limits.

Build this page after pages/search.py's metric captions and expander
text are confirmed final, so the two pages don't drift or duplicate
each other's definitions.
Source: docs/METHODOLOGY.md and docs/LIMITATIONS.md.
"""

from __future__ import annotations

import streamlit as st

from shared import components

components.inject_base_css()
components.render_header(
    "Methodology",
    "How the metrics work, what they measure, and what they do not.",
)

st.info(
    "This page is not built out yet. For now, see `docs/METHODOLOGY.md` for "
    "the full metric definitions, `docs/LIMITATIONS.md` for known data-quality "
    "and coverage caveats, and `docs/ADR.md` for architecture decisions.\n\n"
    "In short: every metric in this tool is a structured observation — "
    "ingredient signals, positioning category, nutrition reference points — "
    "not a verdict, score of quality, or legal assessment."
)
