"""pages/2_Industries.py — Redirects to merged Screener page"""
import streamlit as st
from utils.theme import page_config, inject_css
page_config("Industries · Weinstein V5")
inject_css()
st.markdown("# 🔍 Industries")
st.info("The Industries screener has been merged into the **🏦 Sectors** page for a better top-down workflow.")
st.page_link("pages/1_Sectors.py", label="→ Go to Screener (Sectors + Industries)", icon="📈")
