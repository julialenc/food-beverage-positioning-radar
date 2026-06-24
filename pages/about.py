"""
About — SCAFFOLD ONLY, not yet built out.

This page covers project background only. Metric definitions and
methodology have moved to pages/methodology.py.

Confirmed content for when this page is built:
1. Project purpose — why this tool was built and for whom.
2. Data source — Open Food Facts, ODbL license, contributor model.
3. License and citation — how to attribute the tool in reports or
   publications. Link to LICENSE file in the repo.
4. GitHub / contact / credits — repo link, author, acknowledgements.

Source: final README.md plus license/citation notes.
"""

from __future__ import annotations

import streamlit as st

from shared import components

components.inject_base_css()
components.render_header(
    "About",
    "Project purpose, data source, license, and credits.",
)

st.info(
    "This page is not built out yet. For now, see the project README on GitHub "
    "for purpose, data source, and license information, and `docs/METHODOLOGY.md` "
    "for metric definitions (also available in the Methodology tab).\n\n"
    "Source data: Open Food Facts (openfoodfacts.org), licensed under ODbL."
)
