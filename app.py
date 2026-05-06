"""
app.py — Weinstein Stage Screener V5
=====================================
Entry point. Handles auth state and sidebar navigation.
"""

import streamlit as st
from utils.theme import page_config, inject_css, get_colors
from utils.db import check_login, create_user, validate_invite, use_invite, user_exists, is_admin

# ── Page setup ───────────────────────────────────────────────
page_config("Weinstein Screener V5")
inject_css()

# ── Session defaults ─────────────────────────────────────────
if "logged_in"    not in st.session_state: st.session_state.logged_in    = False
if "username"     not in st.session_state: st.session_state.username     = ""
if "dark_mode"    not in st.session_state: st.session_state.dark_mode    = False

C = get_colors()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    # Logo + title
    st.markdown(f"""
    <div style="padding: 16px 8px 8px; margin-bottom: 8px;">
      <div style="font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; color: {C['TEXT']}">
        📈 Weinstein V5
      </div>
      <div style="font-size: 0.75rem; color: {C['SUB']}; margin-top: 2px;">
        Stage Analysis · RS · Volume
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Theme toggle
    col_t, col_btn = st.columns([3, 1])
    with col_t:
        sub = C["SUB"]
        st.markdown(f"<span style='color:{sub};font-size:0.82rem'>Appearance</span>", unsafe_allow_html=True)
    with col_btn:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️", key="theme"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.divider()

    if st.session_state.logged_in:
        st.markdown(f"<span style='color:{C['SUB']};font-size:0.78rem'>Signed in as</span>", unsafe_allow_html=True)
        st.markdown(f"**{st.session_state.username}**")
        if st.button("Sign out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username  = ""
            st.rerun()
    else:
        st.markdown(f"<span style='color:{C['SUB']};font-size:0.78rem'>Sign in for Dashboard access</span>", unsafe_allow_html=True)

# ── Main content ─────────────────────────────────────────────

if not st.session_state.logged_in:
    # Public landing page
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("# 📈 Weinstein Stage Screener")
        st.markdown(f"<p style='color:{C['SUB']};font-size:1rem;line-height:1.7'>Built on Stan Weinstein's Stage Analysis methodology. Scan sectors, industries, and 6000+ stocks for Stage 2 breakouts, RS leadership, and volume confirmation.</p>", unsafe_allow_html=True)

        st.markdown("---")

        # Feature pills
        features = [
            ("🏦", "Sector Screener", "11 SPDR sectors with RS ranking and stage analysis"),
            ("🔍", "Industry Screener", "150+ Finviz-style industries with drill-down"),
            ("📋", "Full Market Scan", "NYSE + NASDAQ Stage 2 signals with one click"),
            ("👁", "Stage 1 Watchlist", "40+ week bases with tightness scoring"),
            ("🔒", "Private Dashboard", "Portfolio tracking, P&L, performance charts"),
            ("📤", "TradingView Export", "One-click watchlist export"),
        ]
        for icon, title, desc in features:
            st.markdown(f"""
            <div class="wcard" style="display:flex;gap:14px;align-items:flex-start;padding:12px 16px;margin:4px 0">
              <span style="font-size:1.3rem">{icon}</span>
              <div>
                <div style="font-weight:600;font-size:0.9rem">{title}</div>
                <div style="color:{C['SUB']};font-size:0.78rem">{desc}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<p style='color:{C['SUB']};font-size:0.78rem'>Data via Yahoo Finance · Weekly closes (Friday) · Not financial advice</p>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<h3 style='text-align:center'>Sign in</h3>", unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
                if submitted:
                    if check_login(username.strip(), password):
                        st.session_state.logged_in = True
                        st.session_state.username  = username.strip()
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

            st.markdown(f"<p style='color:{C['SUB']};font-size:0.78rem;text-align:center'>The screener tabs are publicly accessible without signing in.<br>Sign in for portfolio tracking and watchlists.</p>", unsafe_allow_html=True)

        with register_tab:
            with st.form("register_form"):
                inv_code = st.text_input("Invite code")
                new_user = st.text_input("Choose username")
                new_pw   = st.text_input("Choose password", type="password")
                new_pw2  = st.text_input("Repeat password", type="password")
                reg_sub  = st.form_submit_button("Create account", use_container_width=True)
                if reg_sub:
                    if not validate_invite(inv_code):
                        st.error("Invalid or already-used invite code")
                    elif len(new_user) < 3:
                        st.error("Username must be at least 3 characters")
                    elif user_exists(new_user):
                        st.error("Username already taken")
                    elif new_pw != new_pw2:
                        st.error("Passwords do not match")
                    elif len(new_pw) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        create_user(new_user, new_pw)
                        use_invite(inv_code, new_user)
                        st.success(f"Account created! Sign in as **{new_user}**.")

else:
    # Logged-in home: redirect hint
    st.markdown(f"# Welcome, {st.session_state.username} 👋")
    st.markdown(f"<p style='color:{C['SUB']}'>Use the navigation in the sidebar to access the screener tabs.</p>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.page_link("pages/1_Sectors.py",    label="🏦 Sector Screener", use_container_width=True)
    col2.page_link("pages/2_Industries.py", label="🔍 Industries",      use_container_width=True)
    col3.page_link("pages/3_All_Stocks.py", label="📋 All Stocks",       use_container_width=True)
    col4.page_link("pages/4_Dashboard.py",  label="🔒 Dashboard",        use_container_width=True)
