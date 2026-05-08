"""pages/1_Sectors.py — Sector Screener + Stage 1 Watchlist"""

import streamlit as st
import pandas as pd
import json
from utils.theme import page_config, inject_css, get_colors, signal_pill, stage_pill
from utils.screener import (
    get_spx_data, scan_tickers, scan_batch, fetch_weekly, evaluate,
    SECTORS, SECTOR_STOCKS, fmt, rs_tag, sig_icon, signal_card_html,
    export_tv, export_tv_lines, fetch_nyse_tickers
)

page_config("Sectors · Weinstein V5")
inject_css()
C = get_colors()

# ── Load core data ────────────────────────────────────────────
with st.spinner("Loading market data…"):
    spx_ev, sec_df, spx_close_json = get_spx_data()

if spx_ev is None:
    st.error("Could not load SPY data. Check your internet connection.")
    st.stop()

# ── Header ────────────────────────────────────────────────────
st.markdown("# 🏦 Sector Screener")
st.markdown(f"<p class='subtext'>50w SMA · Relative Strength vs SPX · Volume · Base Length · Stop Levels</p>", unsafe_allow_html=True)

# ── Market Regime ─────────────────────────────────────────────
st.markdown("### Market Regime")
pct = spx_ev.get("pct_above") or 0
stage = spx_ev.get("stage","")

items = [
    ("SPY Stage",    stage),
    ("Price",        fmt(spx_ev["price"])),
    ("50w SMA",      fmt(spx_ev["sma50w"])),
    ("% above SMA",  fmt(pct,"%",1)),
    ("Stage Score",  f"{spx_ev['score']}/5"),
]
cols = st.columns(5)
for col, (label, val) in zip(cols, items):
    col.metric(label, val)

if "Stage 2" not in stage:
    st.markdown(f'<div class="wcard-warn">⚠ <strong>SPY not in Stage 2.</strong> Per Weinstein, all buy signals should be ignored until the market recovers.</div>', unsafe_allow_html=True)
elif pct > 10:
    st.markdown(f'<div class="wcard-warn" style="border-left-color:{C["YELLOW"]}">⚡ <strong>SPY extended</strong> ({pct:.1f}% above SMA). Fresh EARLY signals are rare here. Wait for a pullback or sector rotation.</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="wcard-info">✓ <strong>SPY in Stage 2.</strong> Market conditions are favourable. Buy signals are valid.</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Sector Ranking ────────────────────────────────────────────
st.markdown("### Sector Ranking")
sec_rows = []
for _, r in sec_df.iterrows():
    vol   = r["vol"]
    cross = f"{int(r['cross'])}w" if r.get("cross",-1) >= 0 else "–"
    sec_rows.append({
        "Sector":   r.get("name", r["ticker"]),
        "Price":    fmt(r["price"]),
        "%>SMA":    fmt(r["pct_above"],"%",1),
        "RS":       fmt(r["rs"],"",1),
        "RS Trend": rs_tag(r["rs"]),
        "Vol":      fmt(vol,"x",1),
        "Base":     f"{r['base_w']}w",
        "Cross":    cross,
        "Score":    f"{r['score']}/5",
        "Label":    r["label"],
        "Signal":   sig_icon(r),
    })
st.dataframe(pd.DataFrame(sec_rows), width="stretch", hide_index=True, height=430)

# ── Early Signals ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### Early Signals")
early_secs = sec_df[sec_df["early_sig"]]
if early_secs.empty:
    st.markdown(f'<div class="wcard-info">No fresh sector signals right now. Market is mid-trend or extended. Re-check after a 5%+ pullback in SPY or when a new sector starts showing RS leadership.</div>', unsafe_allow_html=True)
else:
    for _, r in early_secs.iterrows():
        st.markdown(signal_card_html(r, r["name"], C), unsafe_allow_html=True)

# ── Stocks in Top Sectors ─────────────────────────────────────
st.markdown("---")
st.markdown("### Stocks within Top Sectors")
st.markdown(f"<p class='subtext'>Only stocks with Stage 2 score ≥ 4 shown. Sorted by signal quality.</p>", unsafe_allow_html=True)

with st.spinner("Scanning sector stocks…"):
    stock_results = {}
    for sec_tk, stocks in SECTOR_STOCKS.items():
        df_res = scan_tickers(json.dumps(stocks), spx_close_json)
        stock_results[sec_tk] = df_res

master_premium, master_early = [], []

for _, sec in sec_df[sec_df["score"] >= 3].head(5).iterrows():
    tk  = sec["ticker"]
    stk = stock_results.get(tk, pd.DataFrame())

    icon  = "🟢" if sec.get("premium") else "🟡" if sec.get("early_sig") else "📊"
    label = f"{icon} {tk} — {sec['name']}  ·  RS {fmt(sec['rs'],'',1)}  ·  {sec['label']}  ·  Base {sec['base_w']}w"
    expanded = bool(sec.get("early_sig") or sec.get("premium"))

    with st.expander(label, expanded=expanded):
        if stk.empty or len(stk[stk["score"] >= 4]) == 0:
            st.caption("No stocks meet Stage 2 threshold in this sector.")
        else:
            filtered = stk[stk["score"] >= 4].head(12)
            rows = []
            for _, r in filtered.iterrows():
                vol = r["vol"]
                cross = f"{int(r['cross'])}w" if r.get("cross",-1) >= 0 else "–"
                rows.append({
                    "Ticker":   r["ticker"],
                    "Price":    fmt(r["price"]),
                    "%>SMA":    fmt(r["pct_above"],"%",1),
                    "RS":       fmt(r["rs"],"",1),
                    "RS Trend": rs_tag(r["rs"]),
                    "Vol":      fmt(vol,"x",1),
                    "Base":     f"{r['base_w']}w",
                    "Cross":    cross,
                    "Stop":     fmt(r["stop"]),
                    "Risk":     fmt(r["risk"],"%",1),
                    "Stage":    r["stage"],
                    "Signal":   sig_icon(r),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            for _, r in filtered.iterrows():
                if r.get("premium"):   master_premium.append((r.to_dict(), sec["name"]))
                elif r.get("early_sig"): master_early.append((r.to_dict(), sec["name"]))

# ── Master Shortlist ──────────────────────────────────────────
st.markdown("---")
sh_hdr, sh_ctrl1, sh_ctrl2 = st.columns([3,1,1])
with sh_hdr:
    st.markdown("### Master Shortlist")
with sh_ctrl1:
    ms_min = st.selectbox("Min score", [3,4,5], index=1, key="ms_min")
with sh_ctrl2:
    ms_nyse = st.toggle("Full NYSE+NASDAQ", value=False, key="ms_nyse",
                         help="Scans ~6000 US stocks. Cached 6h after first run (~10-15 min).")

if ms_nyse:
    st.info("📡 Batch scanning full NYSE + NASDAQ universe…")
    with st.spinner("This takes 10-15 min on first run, then cached 6h…"):
        tks = fetch_nyse_tickers()
        nyse_results = scan_batch(json.dumps(tks), spx_close_json, min_score=ms_min, min_price=2.0)

    if nyse_results:
        df_nyse = pd.DataFrame(nyse_results)
        n_p = len(df_nyse[df_nyse["premium"]])
        n_e = len(df_nyse[df_nyse["early_sig"]])

        cols = st.columns(5)
        cols[0].metric("Total", len(df_nyse))
        cols[1].metric("🟢 Premium", n_p)
        cols[2].metric("🟡 Early", n_e)
        cols[3].metric("🔵 S2", len(df_nyse)-n_p-n_e)

        filt = cols[4].selectbox("Show", ["All","🟢+🟡 Best","🟢 Premium","🟡 Early","🔵 S2"], key="nyse_filt")
        if filt == "🟢+🟡 Best":   df_nyse = df_nyse[df_nyse["premium"] | df_nyse["early_sig"]]
        elif filt == "🟢 Premium": df_nyse = df_nyse[df_nyse["premium"]]
        elif filt == "🟡 Early":   df_nyse = df_nyse[df_nyse["early_sig"]]
        elif filt == "🔵 S2":      df_nyse = df_nyse[~(df_nyse["premium"] | df_nyse["early_sig"]) & (df_nyse["score"] >= 4)]

        rows = []
        for _, r in df_nyse.iterrows():
            cross = f"{int(r['cross'])}w" if r.get("cross",-1) >= 0 else "–"
            rows.append({
                "Signal": sig_icon(r.to_dict()), "Ticker": r["ticker"],
                "Stage": r["stage"], "Score": f"{r['score']}/5",
                "RS": fmt(r["rs"],"",1), "RS Trend": rs_tag(r["rs"]),
                "Price": fmt(r["price"]), "%>SMA": fmt(r["pct_above"],"%",1),
                "Vol": fmt(r["vol"],"x",1), "Base": f"{r['base_w']}w",
                "Cross": cross, "Stop": fmt(r["stop"]), "Risk": fmt(r["risk"],"%",1),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=550)

        st.markdown("---")
        ex1, ex2 = st.columns(2)
        all_tks  = df_nyse["ticker"].tolist()
        best_tks = df_nyse[df_nyse["premium"] | df_nyse["early_sig"]]["ticker"].tolist()
        with ex1:
            st.caption("All shown signals")
            st.code(export_tv(all_tks[:60]), language=None)
            st.download_button("⬇️ Download (.txt)", export_tv_lines(all_tks),
                               file_name="TV_stage2_full.txt", mime="text/plain", key="dl_nyse_all")
        with ex2:
            st.caption("PREMIUM + EARLY only")
            st.code(export_tv(best_tks) if best_tks else "–", language=None)
            if best_tks:
                st.download_button("⬇️ Best signals (.txt)", export_tv_lines(best_tks),
                                   file_name="TV_stage2_best.txt", mime="text/plain", key="dl_nyse_best")
    else:
        st.warning("No signals found or data unavailable.")

else:
    if not master_premium and not master_early:
        st.info("No PREMIUM or EARLY signals in sector universe today. Enable 'Full NYSE+NASDAQ' for a broader scan.")
    else:
        if master_premium:
            st.markdown("#### 🟢 Premium Signals")
            for r, sname in master_premium:
                st.markdown(signal_card_html(r, sname, C), unsafe_allow_html=True)
        if master_early:
            st.markdown("#### 🟡 Early Signals")
            for r, sname in master_early:
                st.markdown(signal_card_html(r, sname, C), unsafe_allow_html=True)

# ── Stage 1 Watchlist ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 👁 Stage 1 Watchlist — Bases Building")
st.markdown(f"<p class='subtext'>Stocks in Stage 1 with 40+ week bases. Not buy signals yet — set TradingView alerts for when price closes above 50w SMA on high volume.</p>", unsafe_allow_html=True)

s1_c1, s1_c2, s1_c3, s1_c4 = st.columns(4)
min_base = s1_c1.slider("Min base (weeks)", 40, 120, 40, 5, key="s1_base")
max_tight = s1_c2.slider("Max tightness %", 2.0, 20.0, 12.0, 0.5, key="s1_tight")
sec_filt = s1_c3.selectbox("Sector", ["All","Bullish only","Bearish only"], key="s1_sec")
s1_nyse  = s1_c4.toggle("Include NYSE+NASDAQ", value=False, key="s1_nyse",
                          help="Scans all ~6000 US stocks for Stage 1 bases.")

with st.spinner("Scanning for Stage 1 bases…"):
    all_s1 = []
    # Always scan sector stocks
    for sec_tk, stocks in SECTOR_STOCKS.items():
        stk_df = stock_results.get(sec_tk, pd.DataFrame())
        if stk_df.empty: continue
        for _, r in stk_df.iterrows():
            if "Stage 1" not in r.get("stage",""): continue
            if r.get("base_w",0) < 40: continue
            rd = r.to_dict()
            rd["sec_tk"]   = sec_tk
            rd["sec_name"] = SECTORS.get(sec_tk,"")
            all_s1.append(rd)

    if s1_nyse:
        nyse_tks = fetch_nyse_tickers()
        nyse_s1  = scan_batch(json.dumps(nyse_tks), spx_close_json, min_score=0, min_price=2.0)
        for r in nyse_s1:
            if "Stage 1" not in r.get("stage",""): continue
            if r.get("base_w",0) < 40: continue
            all_s1.append(r)

if not all_s1:
    st.info("No Stage 1 bases of 40+ weeks found.")
else:
    s1_df = pd.DataFrame(all_s1)

    # Add sector RS
    def get_sec_rs(sec_tk):
        if not sec_tk: return None
        row = sec_df[sec_df["ticker"] == sec_tk]
        return float(row.iloc[0]["rs"]) if not row.empty else None

    if "sec_tk" in s1_df.columns:
        s1_df["sec_rs"] = s1_df["sec_tk"].apply(get_sec_rs)
    else:
        s1_df["sec_rs"] = None

    # Filters
    s1_df = s1_df[s1_df["base_w"] >= min_base]
    if "base_tightness" in s1_df.columns:
        s1_df = s1_df[s1_df["base_tightness"].isna() | (s1_df["base_tightness"] <= max_tight)]
    if sec_filt == "Bullish only":
        s1_df = s1_df[s1_df["sec_rs"].notna() & (s1_df["sec_rs"] > 0)]
    elif sec_filt == "Bearish only":
        s1_df = s1_df[s1_df["sec_rs"].notna() & (s1_df["sec_rs"] <= 0)]

    if "base_tightness" in s1_df.columns:
        s1_df = s1_df.sort_values(["base_tightness","base_w"], ascending=[True,False], na_position="last")

    st.caption(f"{len(s1_df)} stocks found")

    if not s1_df.empty:
        # Top 5 cards
        top5 = s1_df.head(5)
        cols5 = st.columns(min(5, len(top5)))
        for idx, (_, r) in enumerate(top5.iterrows()):
            sr = r.get("sec_rs")
            sc = C["GREEN"] if (sr and sr > 0) else C["RED"]
            tight = r.get("base_tightness")
            with cols5[idx]:
                st.markdown(f"""
                <div class="wcard" style="text-align:center;padding:14px 12px">
                  <div style="font-size:1.15rem;font-weight:800">🔵 {r['ticker']}</div>
                  <div style="color:{C['SUB']};font-size:0.75rem">{r.get('sec_name','–')}</div>
                  <div style="font-size:1rem;font-weight:700;margin:8px 0">{r['base_w']}w base</div>
                  <div style="font-size:0.8rem">Tightness: <strong>{fmt(tight,'%',1) if tight else '–'}</strong></div>
                  <div style="font-size:0.75rem;color:{sc}">Sec RS: {fmt(sr,'',1)} ({rs_tag(sr)})</div>
                  <div style="font-size:0.72rem;color:{C['SUB']};margin-top:4px">
                    {fmt(r['price'])} · Trigger: {fmt(r['sma50w'])}
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Full table
        rows = []
        for _, r in s1_df.iterrows():
            sr    = r.get("sec_rs")
            tight = r.get("base_tightness")
            if tight is None:     bq = "–"
            elif tight < 5:       bq = "⭐ Extremely tight"
            elif tight < 8:       bq = "✓ Clean"
            elif tight < 12:      bq = "~ Moderate"
            else:                 bq = "✗ Wide/choppy"
            rows.append({
                "Ticker":     r["ticker"],
                "Sector":     r.get("sec_name","–"),
                "Sec RS":     fmt(sr,"",1),
                "Sec Trend":  rs_tag(sr),
                "Base (wks)": r["base_w"],
                "Tightness":  fmt(tight,"%",1) if tight else "–",
                "Quality":    bq,
                "Price":      fmt(r["price"]),
                "vs SMA":     fmt(r["pct_above"],"%",1),
                "RS":         fmt(r["rs"],"",1),
                "Trigger at": fmt(r["sma50w"]) + " + vol",
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=450)

        # Export
        s1_tks = s1_df["ticker"].tolist()
        ec1, ec2 = st.columns(2)
        with ec1:
            st.code(export_tv(s1_tks), language=None)
        with ec2:
            st.download_button("⬇️ Stage 1 Watchlist (.txt)", export_tv_lines(s1_tks),
                               file_name="TV_stage1_watchlist.txt", mime="text/plain", key="dl_s1")

# ── Legend ────────────────────────────────────────────────────
with st.expander("📖 Legend & Guide"):
    st.markdown(f"""
| Term | Meaning |
|---|---|
| **🟢 PREMIUM** | Recent SMA crossover (≤8w) + SMA rising + RS positive + volume ≥1.5x + base ≥40 weeks. Weinstein's gold setup. |
| **🟡 EARLY** | Recent SMA crossover (≤8w) + SMA rising + RS positive + volume confirmed. Fresh entry, no base minimum. |
| **🔵 S2** | In Stage 2 uptrend (4-5/5 criteria) but no recent crossover — you're late to this move. |
| RS Score | >+15 Strong bull · +5..15 Bullish · -3..+5 Neutral · -15..-3 Bearish · <-15 Strong bear |
| Tightness % | Std dev of price vs SMA during base. <5% = extremely tight · 5-8% = clean · >12% = wide/choppy |
| Stage 3 | Above SMA but SMA slope flat/declining. Yellow flag — momentum fading. |
| Stage 1 | Basing below or near SMA. Not actionable yet. Set alert for SMA crossover on high volume. |
""")

st.markdown(f"<p class='subtext'>Data cached 6h · {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} UTC · Weekly closes (Fri)</p>", unsafe_allow_html=True)
