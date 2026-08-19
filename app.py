"""
Streamlit entry point. Run with: streamlit run app.py

Navigation uses st.Page / st.navigation (Streamlit >= 1.36) rather than
the older pages/ auto-discovery convention, so each page is a plain
module under pages/ without filename-based ordering or icon hacks.

Page order follows the intended CPG-user journey: understand market
patterns → inspect products → understand the methodology → read project
background. This order is locked by the feedback review (23 Jun 2026).

IMPORTANT — default page:
Market Overview carries default=True because the MVP landing flow starts
with the high-level country-category views, then lets users inspect
individual products in Product Explorer.
"""

import streamlit as st

st.set_page_config(
    page_title="Food & Beverage Positioning Radar",
    page_icon="🛰️",
    layout="wide",
)

overview_page     = st.Page("pages/overview.py",     title="Market Overview",  icon="📊", default=True)
search_page       = st.Page("pages/search.py",       title="Product Explorer", icon="🔍")
methodology_page  = st.Page("pages/methodology.py",  title="Methodology",      icon="🧭")
about_page        = st.Page("pages/about.py",        title="About",            icon="ℹ️")

nav = st.navigation([overview_page, search_page, methodology_page, about_page])
nav.run()
