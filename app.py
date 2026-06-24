"""
Streamlit entry point. Run with: streamlit run app.py

Navigation uses st.Page / st.navigation (Streamlit >= 1.36) rather than
the older pages/ auto-discovery convention, so each page is a plain
module under pages/ without filename-based ordering or icon hacks.

Page order follows the intended CPG-user journey: understand market
patterns → inspect products → understand the methodology → read project
background. This order is locked by the feedback review (23 Jun 2026).

IMPORTANT — default page:
search_page currently carries default=True (Option B, confirmed 23 Jun
2026). Once pages/overview.py is fully built, move default=True to
overview_page and remove it from search_page. Doing it now would make
the empty Market Overview scaffold the first thing users see.
"""

import streamlit as st

st.set_page_config(
    page_title="Food & Beverage Positioning Radar",
    page_icon="🛰️",
    layout="wide",
)

overview_page     = st.Page("pages/overview.py",     title="Market Overview",  icon="📊")
search_page       = st.Page("pages/search.py",       title="Product Explorer", icon="🔍", default=True)
methodology_page  = st.Page("pages/methodology.py",  title="Methodology",      icon="🧭")
about_page        = st.Page("pages/about.py",        title="About",            icon="ℹ️")

nav = st.navigation([overview_page, search_page, methodology_page, about_page])
nav.run()
