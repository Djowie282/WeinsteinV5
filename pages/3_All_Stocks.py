"""pages/3_All_Stocks.py — Full market scan"""

import streamlit as st
import pandas as pd
import json
import yfinance as yf
from utils.theme import page_config, inject_css, get_colors
from utils.screener import (
    get_spx_data, scan_tickers, scan_batch,
    SECTORS, SECTOR_STOCKS, fmt, rs_tag, sig_icon,
    export_tv, export_tv_lines, fetch_nyse_tickers
)

page_config("All Stocks · Weinstein V5")
inject_css()
C = get_colors()

@st.cache_data(ttl=24*3600, show_spinner=False)
def get_mcap_billions(ticker: str) -> float | None:
    """Return market cap in billions, or None if unavailable."""
    try:
        info = yf.Ticker(ticker).fast_info
        mc = getattr(info, "market_cap", None)
        if mc and mc > 0:
            return round(mc / 1e9, 2)
    except Exception:
        pass
    return None

with st.spinner("Loading market data…"):
    spx_ev, sec_df, spx_close_json = get_spx_data()

if spx_ev is None:
    st.error("Yahoo Finance is rate-limiting this server. Please wait 30 seconds and refresh the page.")
    if st.button("🔄 Retry now"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

st.markdown("# 📋 All Stocks")
st.markdown(f"<p class='subtext'>Cross-sector view of all stocks. Filter by signal type, sector, and score. Enable Full NYSE+NASDAQ for a complete market scan.</p>", unsafe_allow_html=True)

# ── Controls ──────────────────────────────────────────────────
st.markdown("---")
f1,f2,f3,f4 = st.columns([2,2,2,2])
with f1: sig_filter = st.selectbox("Signal",["All","🟢+🟡 Best","🟢 Premium","🟡 Early","🔵 Stage 2+"])
with f2: sec_filter = st.selectbox("Sector",["All"]+list(SECTORS.values()))
with f3: min_score  = st.selectbox("Min score",[0,1,2,3,4,5],index=2)
with f4: nyse_mode  = st.toggle("Full NYSE+NASDAQ",value=False,key="all_nyse",help="Scans ~6000 US stocks. Cached 7 days.")

f5,f6,f7,_ = st.columns([2,2,2,2])
with f5: min_vol = st.number_input("Min volume ratio (x avg)", min_value=0.0, max_value=10.0, value=0.0, step=0.5, help="0 = no filter. E.g. 1.5 = only stocks with 1.5x above-average volume")
with f6: mcap_min = st.number_input("Min market cap ($B)", min_value=0.0, value=0.0, step=1.0, help="0 = no minimum")
with f7: mcap_max = st.number_input("Max market cap ($B)", min_value=0.0, value=0.0, step=10.0, help="0 = no maximum")
mcap_active = mcap_min > 0 or mcap_max > 0

# Market cap filter
mc1, mc2, mc3 = st.columns([2,2,2])
with mc1:
    mcap_min = st.number_input("Min market cap ($B)", min_value=0.0,
                                max_value=10000.0, value=0.0, step=1.0,
                                help="0 = no minimum")
with mc2:
    mcap_max = st.number_input("Max market cap ($B)", min_value=0.0,
                                max_value=10000.0, value=0.0, step=10.0,
                                help="0 = no maximum")
with mc3:
    mcap_active = (mcap_min > 0 or mcap_max > 0)
    if mcap_active:
        min_str = f"${mcap_min:.0f}B" if mcap_min > 0 else "no min"
        max_str = f"${mcap_max:.0f}B" if mcap_max > 0 else "no max"
        st.markdown(f"<br><span class='subtext'>Filter: {min_str} – {max_str}</span>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<br><span class='subtext'>No market cap filter active</span>",
                    unsafe_allow_html=True)

def apply_mcap_filter(tickers: list) -> list:
    """Filter tickers by market cap. Returns filtered list."""
    if not mcap_active:
        return tickers
    filtered = []
    for tk in tickers:
        mc = get_mcap_billions(tk)
        if mc is None:
            filtered.append(tk)  # keep if unknown
            continue
        if mcap_min > 0 and mc < mcap_min:
            continue
        if mcap_max > 0 and mc > mcap_max:
            continue
        filtered.append(tk)
    return filtered

def add_mcap_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add Mkt Cap column to dataframe."""
    if df.empty: return df
    def fmt_mc(tk):
        mc = get_mcap_billions(tk)
        if mc is None: return "–"
        if mc >= 1000: return f"${mc/1000:.1f}T"
        if mc >= 1:    return f"${mc:.1f}B"
        return f"${mc*1000:.0f}M"
    df = df.copy()
    df["mcap_b"] = df["ticker"].apply(get_mcap_billions)
    return df

# ── Sector universe ───────────────────────────────────────────
if not nyse_mode:
    with st.spinner("Loading sector stocks…"):
        all_rows = []
        for sec_tk, sec_name in SECTORS.items():
            if sec_filter != "All" and sec_name != sec_filter:
                continue
            stocks = SECTOR_STOCKS.get(sec_tk, [])
            if mcap_active:
                stocks = apply_mcap_filter(stocks)
            if not stocks: continue
            df = scan_tickers(json.dumps(stocks), spx_close_json)
            if df.empty: continue
            sec_rs_val = sec_df[sec_df["ticker"]==sec_tk]["rs"].values
            sec_rs = float(sec_rs_val[0]) if len(sec_rs_val) > 0 else None
            for _, r in df.iterrows():
                r2 = r.to_dict()
                r2["sector"]   = sec_name
                r2["sec_tk"]   = sec_tk
                r2["sec_rs"]   = sec_rs
                all_rows.append(r2)

    if all_rows:
        df_all = pd.DataFrame(all_rows)

        # Apply filters
        df_all = df_all[df_all["score"] >= min_score]
        if min_vol > 0:
            df_all = df_all[df_all["vol"].notna() & (df_all["vol"] >= min_vol)]
        if sig_filter == "🟢+🟡 Best":   df_all = df_all[df_all["premium"]|df_all["early_sig"]]
        elif sig_filter == "🟢 Premium": df_all = df_all[df_all["premium"]]
        elif sig_filter == "🟡 Early":   df_all = df_all[df_all["early_sig"]]
        elif sig_filter == "🔵 Stage 2+":df_all = df_all[df_all["score"]>=4]

        df_all = df_all.sort_values(
            ["premium","early_sig","score","rs"],
            ascending=[False,False,False,False]
        ).reset_index(drop=True)

        # Metrics
        n_p = len(df_all[df_all["premium"]])
        n_e = len(df_all[df_all["early_sig"]])
        n_s = len(df_all[df_all["score"]>=4])
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Stocks shown", len(df_all))
        m2.metric("🟢 Premium",   n_p)
        m3.metric("🟡 Early",     n_e)
        m4.metric("🔵 Stage 2+",  n_s)

        # Table
        rows = []
        for _, r in df_all.iterrows():
            cross   = f"{int(r['cross'])}w" if r.get("cross",-1)>=0 else "–"
            sec_rs  = r.get("sec_rs")
            mc = get_mcap_billions(r["ticker"])
            mc_str = f"${mc:.1f}B" if mc and mc>=1 else f"${mc*1000:.0f}M" if mc else "–"
            rows.append({
                "Signal":    sig_icon(r),
                "Ticker":    r["ticker"],
                "Sector":    r.get("sector",""),
                "Mkt Cap":   mc_str,
                "Sec RS":    fmt(sec_rs,"",1),
                "Sec Trend": rs_tag(sec_rs),
                "Stage":     r["stage"],
                "Score":     f"{r['score']}/5",
                "RS":        fmt(r["rs"],"",1),
                "RS Trend":  rs_tag(r["rs"]),
                "Price":     fmt(r["price"]),
                "%>SMA":     fmt(r["pct_above"],"%",1),
                "Vol":       fmt(r["vol"],"x",1),
                "Base":      f"{r['base_w']}w",
                "Cross":     cross,
                "Stop":      fmt(r["stop"]),
                "Risk":      fmt(r["risk"],"%",1),
            })

        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=700)

        # Export
        st.markdown("---")
        ex1, ex2 = st.columns(2)
        all_tks  = df_all["ticker"].tolist()
        best_tks = df_all[df_all["premium"]|df_all["early_sig"]]["ticker"].tolist()
        with ex1:
            st.caption("All shown stocks")
            st.code(export_tv(all_tks[:60]), language=None)
            st.download_button("⬇️ Download (.txt)", export_tv_lines(all_tks),
                               file_name="TV_all_stocks.txt", mime="text/plain", key="dl_all")
        with ex2:
            st.caption("PREMIUM + EARLY only")
            st.code(export_tv(best_tks) if best_tks else "–", language=None)
            if best_tks:
                st.download_button("⬇️ Best signals (.txt)", export_tv_lines(best_tks),
                                   file_name="TV_best_signals.txt", mime="text/plain", key="dl_best")
    else:
        st.info("No stocks found with current filters.")

# ── Full NYSE+NASDAQ scan ────────────────────────────────────
else:
    st.info("📡 Full NYSE + NASDAQ scan. First run ~10-15 min, cached 6h after.")
    with st.spinner("Batch scanning full universe…"):
        nyse_tks = fetch_nyse_tickers()
        min_price_nyse = max(2.0, mcap_min * 0.1) if mcap_min > 0 else 2.0
        results  = scan_batch(json.dumps(nyse_tks), spx_close_json,
                              min_score=min_score, min_price=min_price_nyse)
        # Apply mcap filter post-scan
        if mcap_active and results:
            filtered = []
            for r in results:
                mc = get_mcap_billions(r["ticker"])
                if mc is None: filtered.append(r); continue
                if mcap_min > 0 and mc < mcap_min: continue
                if mcap_max > 0 and mc > mcap_max: continue
                r["mcap_b"] = mc
                filtered.append(r)
            results = filtered

    if results:
        df_nyse = pd.DataFrame(results)

        # Apply signal filter
        if sig_filter == "🟢+🟡 Best":   df_nyse = df_nyse[df_nyse["premium"]|df_nyse["early_sig"]]
        elif sig_filter == "🟢 Premium": df_nyse = df_nyse[df_nyse["premium"]]
        elif sig_filter == "🟡 Early":   df_nyse = df_nyse[df_nyse["early_sig"]]
        elif sig_filter == "🔵 Stage 2+":df_nyse = df_nyse[df_nyse["score"]>=4]

        n_p = len(df_nyse[df_nyse["premium"]])
        n_e = len(df_nyse[df_nyse["early_sig"]])

        nm1,nm2,nm3,nm4 = st.columns(4)
        nm1.metric("Total", len(df_nyse))
        nm2.metric("🟢 Premium", n_p)
        nm3.metric("🟡 Early",   n_e)
        nm4.metric("🔵 S2",      len(df_nyse)-n_p-n_e)

        rows = []
        for _, r in df_nyse.iterrows():
            cross = f"{int(r['cross'])}w" if r.get("cross",-1)>=0 else "–"
            mc = r.get("mcap_b") or get_mcap_billions(r["ticker"])
            mc_str = f"${mc:.1f}B" if mc and mc>=1 else f"${mc*1000:.0f}M" if mc else "–"
            rows.append({
                "Signal":   sig_icon(r.to_dict()),
                "Ticker":   r["ticker"],
                "Mkt Cap":  mc_str,
                "Stage":    r["stage"],
                "Score":    f"{r['score']}/5",
                "RS":       fmt(r["rs"],"",1),
                "RS Trend": rs_tag(r["rs"]),
                "Price":    fmt(r["price"]),
                "%>SMA":    fmt(r["pct_above"],"%",1),
                "Vol":      fmt(r["vol"],"x",1),
                "Base":     f"{r['base_w']}w",
                "Cross":    cross,
                "Stop":     fmt(r["stop"]),
                "Risk":     fmt(r["risk"],"%",1),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=700)

        all_tks  = df_nyse["ticker"].tolist()
        best_tks = df_nyse[df_nyse["premium"]|df_nyse["early_sig"]]["ticker"].tolist()
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("⬇️ All signals (.txt)", export_tv_lines(all_tks),
                               file_name="TV_nyse_all.txt", mime="text/plain", key="dl_nyse_all")
        with ex2:
            if best_tks:
                st.download_button("⬇️ PREMIUM+EARLY (.txt)", export_tv_lines(best_tks),
                                   file_name="TV_nyse_best.txt", mime="text/plain", key="dl_nyse_best")
    else:
        st.warning("No signals found or data unavailable.")
