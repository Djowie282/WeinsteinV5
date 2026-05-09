"""pages/2_Industries.py — Industry Screener"""

import streamlit as st
import pandas as pd
import json
from utils.theme import page_config, inject_css, get_colors
import plotly.graph_objects as go
from utils.screener import (
    get_spx_data, scan_tickers, scan_batch, fetch_weekly, evaluate,
    SECTORS, fmt, rs_tag, sig_icon, signal_card_html,
    export_tv, export_tv_lines, fetch_nyse_tickers
)
from io import StringIO
import yfinance as yf
from datetime import datetime, timedelta

page_config("Industries · Weinstein V5")
inject_css()
C = get_colors()

# ── Universe ─────────────────────────────────────────────────
FINVIZ_INDUSTRIES = {
    "Semiconductors":                ["NVDA","AMD","AVGO","QCOM","TXN","MCHP","ADI","AMAT","LRCX","KLAC","ASML","ARM","MU","SMCI","ON","MRVL","INTC","NXPI"],
    "Semiconductor Equipment":       ["AMAT","LRCX","KLAC","ASML","ONTO","UCTT","ICHR","ACLS","AMKR","COHU"],
    "Software - Application":        ["CRM","NOW","ADBE","INTU","CDNS","SNPS","ANSS","PTC","MANH","PCTY","PAYC","DOCU","ZI"],
    "Software - Infrastructure":     ["MSFT","ORCL","PLTR","MDB","DDOG","SNOW","NET","ZS","CRWD","PANW","FTNT","OKTA"],
    "Computer Hardware":             ["AAPL","HPQ","HPE","DELL","NTAP","PSTG","WDC","STX","NTNX"],
    "Information Technology Services":["ACN","IBM","INFY","WIT","CTSH","DXC","EPAM","GLOB","EXLS"],
    "Internet Content & Information": ["GOOGL","META","PINS","SNAP","RBLX","MTCH","IAC"],
    "Electronic Components":         ["TE","APH","GLW","FLEX","PLXS","CTS","VICR"],
    "Communication Equipment":       ["CSCO","JNPR","ANET","CIEN","VIAV","CALX","INFN"],
    "Drug Manufacturers - Major":    ["LLY","JNJ","MRK","ABBV","PFE","AMGN","BMY","GILD","BIIB","REGN","VRTX","MRNA"],
    "Drug Manufacturers - Specialty":["JAZZ","SUPN","PRGO","MNKD","IMVT","ARWR","ALNY","IONS"],
    "Biotechnology":                 ["MRNA","BIIB","REGN","VRTX","ALNY","BMRN","EXEL","ARWR","IONS","SRPT"],
    "Medical Devices":               ["ISRG","MDT","BSX","EW","SYK","BDX","ZBH","HOLX","INSP","NARI","SWAV"],
    "Diagnostics & Research":        ["TMO","DHR","IQV","ILMN","A","QGEN","EXAS","NEO","GH","NTRA"],
    "Healthcare Plans":              ["UNH","ELV","CI","HUM","MOH","CNC","OSCR"],
    "Banks - Major":                 ["JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","COF"],
    "Banks - Regional":              ["ZION","MTB","BOKF","EWBC","FFIN","IBOC","CVBF","WAFD"],
    "Asset Management":              ["BLK","APO","KKR","BX","CG","ARES","BAM","OWL"],
    "Insurance - Property & Casualty":["PGR","ALL","TRV","CB","HIG","MKL","CINF","WRB","RLI"],
    "Financial Data & Stock Exchanges":["SPGI","MCO","CME","ICE","MSCI","NDAQ","TW","CBOE"],
    "Credit Services":               ["V","MA","AXP","COF","DFS","SYF","ALLY","AFRM","UPST"],
    "Auto Manufacturers":            ["TSLA","GM","F","RIVN","LCID","STLA","NIO","LI","XPEV"],
    "Specialty Retail":              ["HD","LOW","ORLY","AZO","TSCO","WSM","RH","BBWI","URBN","ANF"],
    "Internet Retail":               ["AMZN","BKNG","EXPE","ABNB","W","ETSY","EBAY","CHWY"],
    "Restaurants":                   ["MCD","SBUX","CMG","YUM","QSR","DPZ","WING","TXRH","DRI","CAVA"],
    "Apparel Retail":                ["NKE","LULU","DECK","ONON","CROX","SKX","VFC"],
    "Leisure":                       ["MAR","HLT","H","WH","EXPE","BKNG","ABNB","RCL","CCL","NCLH"],
    "Gambling":                      ["LVS","MGM","WYNN","CZR","BYD","PENN","DKNG","FLUT"],
    "Discount Stores":               ["WMT","COST","TGT","DG","DLTR","BIG","FIVE"],
    "Household & Personal Products": ["PG","CL","CHD","KMB","ENR","ELF","HIMS","KENVUE"],
    "Beverages - Non-Alcoholic":     ["KO","PEP","MNST","CELH","FIZZ","COKE"],
    "Beverages - Alcoholic":         ["STZ","BUD","TAP","SAM","ABEV","DEO","BF-B"],
    "Packaged Foods":                ["MDLZ","GIS","K","CPB","SJM","CAG","HRL","MKC","POST"],
    "Tobacco":                       ["PM","MO","BTI","VGR","TPB"],
    "Grocery Stores":                ["KR","ACI","VLGEA","CASY"],
    "Oil & Gas E&P":                 ["XOM","CVX","COP","EOG","OXY","DVN","FANG","MRO","APA","AR","RRC","EQT","MTDR","CTRA"],
    "Oil & Gas Integrated":          ["XOM","CVX","BP","SHEL","TTE","EQNR"],
    "Oil & Gas Midstream":           ["WMB","OKE","KMI","EPD","ET","MPLX","TRGP"],
    "Oil & Gas Refining & Marketing":["MPC","VLO","PSX","PBF","DINO"],
    "Oil & Gas Equipment & Services":["SLB","HAL","BKR","NOV","FTI","WHD"],
    "Uranium":                       ["CCJ","UEC","UUUU","DNN","URG","NXE"],
    "Renewable Utilities":           ["NEE","BEP","BEPC","FSLR","ENPH","RUN","NOVA","ARRY"],
    "Aerospace & Defense":           ["LMT","RTX","NOC","GD","BA","HII","TDG","HEI","AXON","KTOS","RKLB"],
    "Airlines":                      ["UAL","DAL","AAL","LUV","JBLU","ALK"],
    "Trucking":                      ["ODFL","SAIA","XPO","WERN","JBHT","KNX","ARCB"],
    "Railroads":                     ["UNP","CSX","NSC","CP","CN","WAB"],
    "Integrated Freight & Logistics":["FDX","UPS","XPO","GXO","CHRW","EXPD"],
    "Farm & Heavy Construction Machinery":["DE","CAT","AGCO","CNHI","OSK"],
    "Specialty Industrial Machinery":["EMR","ROK","ITW","IEX","ROP","FLS","GNRC"],
    "Chemicals":                     ["LIN","APD","ECL","DD","EMN","RPM","IFF","ALB","FMC","CF","MOS","OLN"],
    "Specialty Chemicals":           ["ECL","RPM","IFF","ALB","FMC","AVNT","PLL","LTHM","SQM"],
    "Steel":                         ["NUE","STLD","CMC","CLF","X","MT"],
    "Gold":                          ["NEM","GOLD","AEM","AGI","KGC","AU","EGO","WPM","FNV","RGLD"],
    "Silver":                        ["WPM","PAAS","MAG","AG","SSRM","HL","EXK"],
    "Copper":                        ["FCX","SCCO","HBM","TECK","RIO","BHP"],
    "Building Materials":            ["SHW","VMC","MLM","EXP","LPX","UFPI","BLDR"],
    "REIT - Industrial":             ["PLD","REXR","EGP","FR","LXP","STAG"],
    "REIT - Retail":                 ["SPG","O","KIM","REG","FRT","NNN"],
    "REIT - Residential":            ["EQR","AVB","MAA","ESS","CPT","INVH","AMH","UDR"],
    "REIT - Specialty":              ["AMT","CCI","SBAC","EQIX","DLR","IRM"],
    "REIT - Healthcare":             ["WELL","VTR","OHI","PEAK","NHI"],
    "Utilities - Regulated Electric":["NEE","SO","DUK","AEP","XEL","EXC","ED","SRE","D","PEG"],
    "Utilities - Renewable":         ["NEE","BEP","BEPC","AES","CWEN","FSLR","ENPH"],
    "Utilities - Independent Power": ["VST","CEG","NRG","AES"],
    "Telecom Services":              ["T","VZ","TMUS","LUMN","USM"],
    "Entertainment":                 ["DIS","NFLX","WBD","PARA","FOX","LYV","IMAX"],
    "Advertising Agencies":          ["OMC","IPG","TTD","MGNI","IAS","DV"],
    "Electronic Gaming":             ["EA","TTWO","RBLX","U","ATVI"],
    "Solar":                         ["FSLR","ENPH","RUN","NOVA","ARRY","CSIQ","SEDG"],
    "Luxury Goods":                  ["LVMUY","CPRI","TPR","RL","MOV"],
    "Auto Parts":                    ["APTV","BWA","ALV","GT","LEA","MGA","GNTX"],
    "Waste Management":              ["WM","RSG","CWST","SRCL","CLH","GFL"],
    "Education & Training Services": ["CHGG","LRN","PRDO","STRA","LOPE","DUOL"],
    "Residential Construction":      ["DHI","LEN","TOL","PHM","NVR","MDC","TMHC","MTH","LGIH"],
    "Packaging & Containers":        ["IP","PKG","SON","SLGN","GPK","BERY","CCK"],
    "Medical Distribution":          ["MCK","ABC","CAH","PDCO","HSIC"],
    "Real Estate Services":          ["CBRE","JLL","CWK","RMAX","EXPI"],
}

TICKER_TO_INDUSTRY = {}
for ind, tks in FINVIZ_INDUSTRIES.items():
    for tk in tks:
        if tk not in TICKER_TO_INDUSTRY:
            TICKER_TO_INDUSTRY[tk] = ind

# ── Load core data ────────────────────────────────────────────
with st.spinner("Loading market data…"):
    spx_ev, sec_df, spx_close_json = get_spx_data()

if spx_ev is None:
    st.error("Yahoo Finance is rate-limiting this server. Please wait 30 seconds and refresh the page.")
    if st.button("🔄 Retry now"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# ── Header ────────────────────────────────────────────────────
st.markdown("# 🔍 Industry Screener")
st.markdown(f"<p class='subtext'>{len(FINVIZ_INDUSTRIES)} industries · {sum(len(v) for v in FINVIZ_INDUSTRIES.values())} stocks · Weinstein Stage Analysis · RS vs SPX</p>", unsafe_allow_html=True)

# ── RS helper ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def industry_rs(tickers_json, days):
    tks = json.loads(tickers_json)
    end   = datetime.today()
    start = end - timedelta(days=days + 5)
    try:
        all_tks = list(set(tks + ["SPY"]))
        raw = yf.download(all_tks, start=start, end=end,
                          auto_adjust=False, progress=False, threads=False)["Close"]
        if isinstance(raw, pd.Series): raw = raw.to_frame(all_tks[0])
        raw = raw.ffill().dropna(how="all")
        if len(raw) < 2 or "SPY" not in raw.columns: return None
        n = min(days, len(raw)-1)
        basket = raw[tks].dropna(axis=1).iloc[-(n+1):]
        if basket.empty: return None
        ind_ret = ((basket.iloc[-1] / basket.iloc[0]) - 1).mean() * 100
        spy_ret = (raw["SPY"].iloc[-1] / raw["SPY"].iloc[-n-1] - 1) * 100
        return round(ind_ret - spy_ret, 2)
    except: return None

# ── Sub-tabs ──────────────────────────────────────────────────
ind_tab1, ind_tab2, ind_tab3 = st.tabs(["📊 All Industries", "🔎 Drill-down", "🚨 Signals"])

# ════════════════════════════
# TAB 1: Overview table
# ════════════════════════════
# ── Helper: mini stock chart ──────────────────────────────────
@st.cache_data(ttl=7*24*3600, show_spinner=False)
def get_stock_chart_data(ticker: str) -> pd.DataFrame:
    from utils.screener import fetch_weekly
    return fetch_weekly(ticker, years=5)

def make_mini_chart(ticker: str, C: dict) -> go.Figure:
    df = get_stock_chart_data(ticker)
    if df.empty:
        return None
    close = df["Close"]
    # Last 52 weeks
    df_1y = df.iloc[-52:]
    close_1y = df_1y["Close"]
    dates = df_1y.index

    sma50  = close.rolling(50).mean().iloc[-52:]
    sma200 = close.rolling(200).mean().iloc[-52:]

    fig = go.Figure()
    # Candlestick or line
    fig.add_trace(go.Scatter(
        x=dates, y=close_1y.values,
        mode="lines", name=ticker,
        line=dict(color=C["BLUE"], width=1.8),
        hovertemplate="%{x|%b %d}<br><b>$%{y:.2f}</b><extra></extra>",
    ))
    if not sma50.isna().all():
        fig.add_trace(go.Scatter(
            x=dates, y=sma50.values,
            mode="lines", name="50w SMA",
            line=dict(color=C["YELLOW"], width=1.2, dash="solid"),
            hoverinfo="skip",
        ))
    if not sma200.isna().all():
        fig.add_trace(go.Scatter(
            x=dates, y=sma200.values,
            mode="lines", name="200w SMA",
            line=dict(color=C["RED"], width=1.2, dash="dot"),
            hoverinfo="skip",
        ))
    fig.update_layout(
        height=180, margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["TEXT"], family="Inter", size=10),
        xaxis=dict(showgrid=False, color=C["SUB"], tickfont=dict(size=9), zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C["BORDER"], color=C["SUB"],
                   tickfont=dict(size=9), zeroline=False, tickprefix="$"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9, color=C["SUB"]),
                    orientation="h", x=0, y=1.15),
        hovermode="x unified",
        showlegend=True,
    )
    return fig

with ind_tab1:
    st.markdown("---")
    st.markdown(f"<p class='subtext'>Click a row to drill into that industry. Charts show 1Y weekly with 50w (yellow) and 200w (red) SMA.</p>", unsafe_allow_html=True)

    # Controls row
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        sort_by  = st.selectbox("Sort by", ["RS 3M vs SPX","RS 1M vs SPX","RS 1W vs SPX","Industry"], key="ind_sort")
    with c2:
        rs_filter = st.selectbox("Filter", ["All industries","Positive RS 3M only","RS 3M > 5%","RS 3M > 10%","Negative RS 3M"], key="ind_filter")
    with c3:
        sort_asc = st.toggle("↑ Low → High" if st.session_state.get("ind_asc") else "↓ High → Low",
                              value=False, key="ind_asc")
    with c4:
        show_rs  = st.toggle("RS columns", value=True, key="show_rs")

    # Build data
    rows = []
    for ind_name, tks in FINVIZ_INDUSTRIES.items():
        row = {"Industry": ind_name, "Stocks": len(tks), "_rs1w": None, "_rs1m": None, "_rs3m": None}
        rs1w = industry_rs(json.dumps(tks[:8]), 5)
        rs1m = industry_rs(json.dumps(tks[:8]), 21)
        rs3m = industry_rs(json.dumps(tks[:8]), 63)
        if show_rs:
            row["RS 1W"] = round(rs1w, 1) if rs1w else None
            row["RS 1M"] = round(rs1m, 1) if rs1m else None
            row["RS 3M"] = round(rs3m, 1) if rs3m else None
        row["_rs1w"] = rs1w or -999
        row["_rs1m"] = rs1m or -999
        row["_rs3m"] = rs3m or -999
        row["Top stocks"] = ", ".join(tks[:5]) + ("…" if len(tks) > 5 else "")
        rows.append(row)

    df_ind = pd.DataFrame(rows)

    # Apply filter
    if rs_filter == "Positive RS 3M only":
        df_ind = df_ind[df_ind["_rs3m"] > 0]
    elif rs_filter == "RS 3M > 5%":
        df_ind = df_ind[df_ind["_rs3m"] > 5]
    elif rs_filter == "RS 3M > 10%":
        df_ind = df_ind[df_ind["_rs3m"] > 10]
    elif rs_filter == "Negative RS 3M":
        df_ind = df_ind[df_ind["_rs3m"] < 0]

    # Sort
    sort_map = {"RS 3M vs SPX":"_rs3m","RS 1M vs SPX":"_rs1m","RS 1W vs SPX":"_rs1w","Industry":"Industry"}
    sort_key = sort_map.get(sort_by, "_rs3m")
    if sort_key in df_ind.columns:
        df_ind = df_ind.sort_values(sort_key, ascending=sort_asc).reset_index(drop=True)

    display_cols = [c for c in df_ind.columns if not c.startswith("_")]

    # Style: color RS columns green/red
    def style_rs(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        color = "#16a34a" if val > 0 else "#dc2626" if val < 0 else ""
        return f"color: {color}; font-weight: 600"

    df_show = df_ind[display_cols].copy()
    styler = df_show.style
    rs_cols = [c for c in ["RS 1W","RS 1M","RS 3M"] if c in df_show.columns]
    if rs_cols:
        styler = styler.map(style_rs, subset=rs_cols)
        for rc in rs_cols:
            styler = styler.format("{:+.1f}%", subset=[rc], na_rep="–")

    # Show styled table (visual only — no selection support with Styler)
    st.dataframe(
        styler,
        width="stretch",
        hide_index=True,
        height=550,
    )

    # Separate selector for drill-down
    st.markdown(f"<p class='subtext'>Select an industry to see all stocks and charts:</p>", unsafe_allow_html=True)
    sel_industry_pick = st.selectbox(
        "Industry drill-down",
        ["– select –"] + df_ind["Industry"].tolist(),
        key="ind_drilldown",
        label_visibility="collapsed",
    )

    class _Sel:
        pass
    sel = _Sel()
    sel.selection = type("S", (), {"rows": []})()
    if sel_industry_pick and sel_industry_pick != "– select –":
        idx = df_ind[df_ind["Industry"] == sel_industry_pick].index
        if len(idx) > 0:
            sel.selection.rows = [int(idx[0])]

    # ── Drill-down on row click ───────────────────────────────
    selected_rows = sel.selection.rows if hasattr(sel, "selection") else []
    if selected_rows:
        sel_idx      = selected_rows[0]
        sel_industry = df_ind.iloc[sel_idx]["Industry"]
        sel_tks      = FINVIZ_INDUSTRIES.get(sel_industry, [])

        st.markdown(f"---")
        st.markdown(f"### 📊 {sel_industry}")
        st.markdown(f"<p class='subtext'>{len(sel_tks)} stocks · 1Y weekly chart · 50w SMA (yellow) · 200w SMA (red)</p>",
                    unsafe_allow_html=True)

        with st.spinner(f"Loading {sel_industry} stocks…"):
            ind_scan = scan_tickers(json.dumps(sel_tks), spx_close_json)

        # Show stocks in a grid with mini charts
        cols_per_row = 3
        for i in range(0, len(sel_tks), cols_per_row):
            batch = sel_tks[i:i+cols_per_row]
            grid_cols = st.columns(cols_per_row)
            for col, tk in zip(grid_cols, batch):
                with col:
                    # Get Weinstein data
                    r = {}
                    if not ind_scan.empty:
                        match = ind_scan[ind_scan["ticker"] == tk]
                        if not match.empty:
                            r = match.iloc[0].to_dict()

                    stage   = r.get("stage","–")
                    score   = r.get("score", 0)
                    rs_val  = r.get("rs")
                    sig     = sig_icon(r) if r else ""

                    if "Stage 2" in stage:   dot = "🟢"
                    elif "Stage 3" in stage: dot = "🟡"
                    elif "Stage 4" in stage: dot = "🔴"
                    else:                    dot = "🔵"

                    st.markdown(f"""
                    <div style="padding:8px 4px 2px">
                      <span style="font-weight:700;font-size:0.95rem">{dot} {tk}</span>
                      <span style="color:{C['SUB']};font-size:0.75rem;margin-left:8px">{stage} · {score}/5</span>
                      {"&nbsp;<strong style='color:" + C["GREEN"] + "'>" + sig + "</strong>" if sig else ""}
                    </div>""", unsafe_allow_html=True)

                    fig = make_mini_chart(tk, C)
                    if fig:
                        st.plotly_chart(fig, width="stretch", key=f"chart_{sel_industry}_{tk}")
                    else:
                        st.caption("No chart data")

        # Export
        st.markdown("---")
        ec1, ec2 = st.columns(2)
        with ec1:
            st.caption("All stocks")
            st.download_button("⬇️ TradingView (.txt)", export_tv_lines(sel_tks),
                               file_name=f"TV_{sel_industry.replace(' ','_')}.txt",
                               mime="text/plain", key=f"dl_{sel_industry[:10]}")
        if not ind_scan.empty:
            sig_tks = ind_scan[ind_scan["early_sig"]|ind_scan["premium"]]["ticker"].tolist()
            with ec2:
                if sig_tks:
                    st.caption("Signals only")
                    st.download_button("⬇️ Signals (.txt)", export_tv_lines(sig_tks),
                                       file_name=f"TV_{sel_industry.replace(' ','_')}_signals.txt",
                                       mime="text/plain", key=f"dl_sig_{sel_industry[:10]}")

# ════════════════════════════
# TAB 2: Drill-down
# ════════════════════════════
with ind_tab2:
    st.markdown("---")

    # Search bar
    search_col, btn_col = st.columns([4,1])
    with search_col:
        search_q = st.text_input("🔎 Search stock or industry",
                                  placeholder="e.g. NVDA, ARM, Semiconductors…")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        do_search = st.button("Analyze", width="stretch")

    if search_q and do_search:
        q = search_q.strip().upper()
        spx_close_s = pd.read_json(StringIO(spx_close_json), typ="series")
        looks_like_ticker = len(q) <= 6 and q.replace("-","").isalpha()
        industry_matches  = [ind for ind in FINVIZ_INDUSTRIES if search_q.lower() in ind.lower()]

        if looks_like_ticker:
            st.markdown(f"#### 📊 Weinstein Analysis: {q}")
            with st.spinner(f"Analyzing {q}…"):
                df = fetch_weekly(q)
                if df.empty:
                    st.error(f"Could not find data for {q}.")
                else:
                    r = evaluate(df, spx_close_s)
                    r["ticker"] = q
                    ind_name = TICKER_TO_INDUSTRY.get(q, "–")
                    stage    = r["stage"]

                    # Sector context
                    sec_name_f = "–"; sec_rs_f = None
                    for sec_tk, sec_name in SECTORS.items():
                        if sec_name.lower() in ind_name.lower():
                            sec_row = sec_df[sec_df["ticker"] == sec_tk]
                            if not sec_row.empty:
                                sec_rs_f    = sec_row.iloc[0]["rs"]
                                sec_name_f  = sec_name
                                break

                    # Metrics
                    a1,a2,a3,a4 = st.columns(4)
                    a1.metric("Stage",     stage)
                    a2.metric("Score",     f"{r['score']}/5")
                    a3.metric("RS vs SPX", fmt(r["rs"],"",1))
                    a4.metric("%>50w SMA", fmt(r["pct_above"],"%",1))

                    b1,b2,b3,b4 = st.columns(4)
                    b1.metric("Price",   fmt(r["price"]))
                    b2.metric("50w SMA", fmt(r["sma50w"]))
                    b3.metric("Stop",    fmt(r["stop"]))
                    b4.metric("Risk",    fmt(r["risk"],"%",1))

                    st.markdown("---")
                    st.markdown("#### ✅ Weinstein Checklist")

                    def chk(passed, label, detail):
                        icon  = "✅" if passed else "❌"
                        color = C["GREEN"] if passed else C["RED"]
                        return f'''<div style="display:flex;gap:10px;padding:8px 14px;margin:4px 0;
                            background:{C['CARD']};border-radius:8px;border:1px solid {C['BORDER']}">
                            <span style="font-size:1.1rem">{icon}</span>
                            <div><strong style="color:{color}">{label}</strong><br>
                            <span style="color:{C['SUB']};font-size:0.8rem">{detail}</span></div></div>'''

                    pct = r["pct_above"] or 0
                    st.markdown(chk(r["above_sma"], "Price above 50w SMA",
                        f"Price {fmt(r['price'])} is {fmt(pct,'%',1)} {'above' if pct>=0 else 'below'} the 50w SMA ({fmt(r['sma50w'])})"), unsafe_allow_html=True)
                    st.markdown(chk(r["sma_rising"], "50w SMA is rising",
                        "SMA slope is positive — uptrend confirmed." if r["sma_rising"] else "SMA is flat or declining — key warning sign."), unsafe_allow_html=True)
                    st.markdown(chk(r["rs_up"], "Relative Strength vs SPX positive",
                        f"RS score: {fmt(r['rs'],'',1)} — {rs_tag(r['rs'])}. {'Outperforming the market.' if r['rs_up'] else 'Underperforming — Weinstein avoids buying weak RS stocks.'}"), unsafe_allow_html=True)
                    st.markdown(chk(r["near_high"], "Price near 52-week high (within 15%)",
                        "Within 15% of 52w high — breakout zone." if r["near_high"] else "More than 15% below 52w high — not near a breakout."), unsafe_allow_html=True)
                    st.markdown(chk(r["not_extended"], "Not overextended (<30% above SMA)",
                        f"{fmt(pct,'%',1)} above SMA. {'Ideal entry zone.' if 0<pct<15 else 'Extended — wait for pullback.' if pct>=15 else 'Below SMA.'}"), unsafe_allow_html=True)

                    vol = r["vol"]
                    st.markdown(chk(r["vol_ok"], "Breakout on above-average volume (≥1.5x)",
                        f"Volume ratio: {fmt(vol,'x',1)}. {'Strong institutional buying.' if vol and vol>=2 else 'Confirmed.' if vol and vol>=1.5 else 'Below average — low conviction.' if vol else 'No data.'}"), unsafe_allow_html=True)

                    bw = r["base_w"]
                    st.markdown(chk(bw>=15, "Base ≥15 weeks (longer = better)",
                        f"Base: {bw}w ({r['base_q']}). {'Very long — Weinstein ideal.' if bw>=80 else 'Long.' if bw>=40 else 'Medium.' if bw>=15 else 'Too short — low quality.'}"), unsafe_allow_html=True)

                    sec_bull = sec_rs_f is not None and sec_rs_f > 0
                    st.markdown(chk(sec_bull, "Sector is bullish vs SPX",
                        f"Sector: {sec_name_f}. RS: {fmt(sec_rs_f,'',1)} ({rs_tag(sec_rs_f)}). {'Sector tailwind confirmed.' if sec_bull else 'Buying against sector headwind.'}"), unsafe_allow_html=True)

                    # Verdict
                    st.markdown("---")
                    st.markdown("#### 🧠 Verdict")
                    checks = sum([r["above_sma"], r["sma_rising"], r["rs_up"], r["near_high"],
                                  r["not_extended"], r["vol_ok"], bw>=15, sec_bull])

                    if "Stage 2" in stage and r["score"] >= 4:
                        if r.get("premium"):
                            vc = C["GREEN"]
                            verdict = f"**🟢 PREMIUM SETUP** — {q} is in a textbook Stage 2 breakout with a {bw}-week base. All criteria met. Early entry window still open. Stop at {fmt(r['stop'])} ({fmt(r['risk'],'%',1)} risk)."
                        elif r.get("early_sig"):
                            vc = C["GREEN"]
                            verdict = f"**🟢 EARLY STAGE 2** — {q} crossed above its 50w SMA {r['cross']}w ago with {fmt(vol,'x',1)} volume. SMA is turning up, RS positive. This is the entry window Weinstein targets. Stop at {fmt(r['stop'])}."
                        else:
                            vc = C["BLUE"]
                            verdict = f"**🔵 STAGE 2 — LATE** — {q} is in Stage 2 ({r['score']}/5) but the move is already underway ({fmt(pct,'%',1)} above SMA). Valid to hold, risky to buy fresh. Wait for a pullback toward {fmt(r['sma50w'])}."
                    elif "Stage 1" in stage:
                        vc = C["BLUE"]
                        verdict = f"**🔵 STAGE 1 — WATCHLIST** — {q} is building a {bw}-week base. {'Long base — energy building. ' if bw>=40 else ''}Not actionable yet. Set alert for weekly close above {fmt(r['sma50w'])} on high volume."
                    elif "Stage 3" in stage:
                        vc = C["YELLOW"]
                        verdict = f"**🟡 STAGE 3 — CAUTION** — {q} is topping. SMA is flattening after a run-up. Tighten stops on existing positions. Do not buy."
                    else:
                        vc = C["RED"]
                        rs_note = f" High RS ({fmt(r['rs'],'',1)}) = bounce in downtrend, not a reversal." if r.get("rs") and r["rs"] > 5 else ""
                        verdict = f"**🔴 STAGE 4 — AVOID** — {q} is in a downtrend below a declining 50w SMA. Weinstein's rule: never buy Stage 4 regardless of valuation.{rs_note}"

                    st.markdown(f'''<div style="background:{C['CARD']};border-left:4px solid {vc};
                        border:1px solid {vc}33;border-radius:10px;padding:16px 20px;line-height:1.7">
                        {verdict}<br><br>
                        <span style="color:{C['SUB']};font-size:0.78rem">
                        {checks}/8 checklist criteria met · Industry: {ind_name} · Base: {bw}w · Stop: {fmt(r['stop'])} · Risk: {fmt(r['risk'],'%',1)}
                        </span></div>''', unsafe_allow_html=True)

                    if sig_icon(r):
                        st.success(f"Active signal: {sig_icon(r)}")

        elif industry_matches:
            st.markdown(f"#### Industries matching '{search_q}'")
            for ind in industry_matches[:5]:
                tks = FINVIZ_INDUSTRIES[ind]
                st.markdown(f"**{ind}** — {', '.join(tks[:8])}{'…' if len(tks)>8 else ''}")

    st.markdown("---")

    # Industry drill-down
    st.markdown("#### Scan an Industry")
    dc1, dc2 = st.columns([4,1])
    with dc1:
        sel_ind = st.selectbox("", list(FINVIZ_INDUSTRIES.keys()),
                               key="sel_ind", label_visibility="collapsed")
    with dc2:
        scan_btn = st.button("🔍 Scan", width="stretch")

    if scan_btn:
        st.session_state["scanned_ind"] = sel_ind

    if st.session_state.get("scanned_ind"):
        ind_name = st.session_state["scanned_ind"]
        tks = FINVIZ_INDUSTRIES[ind_name]
        with st.spinner(f"Scanning {ind_name}…"):
            ind_df = scan_tickers(json.dumps(tks), spx_close_json)

        if not ind_df.empty:
            premiums = ind_df[ind_df["premium"]]
            earlys   = ind_df[ind_df["early_sig"]]

            m1,m2,m3,m4 = st.columns(4)
            m1.metric(ind_name, f"{len(ind_df)} stocks")
            m2.metric("🟢 Premium", len(premiums))
            m3.metric("🟡 Early",   len(earlys))
            m4.metric("🔵 Stage 2+", len(ind_df[ind_df["score"]>=4]))

            for _, r in premiums.iterrows():
                st.markdown(signal_card_html(r.to_dict(), "", C), unsafe_allow_html=True)
            for _, r in earlys.iterrows():
                st.markdown(signal_card_html(r.to_dict(), "", C), unsafe_allow_html=True)

            rows = []
            for _, r in ind_df.iterrows():
                cross = f"{int(r['cross'])}w" if r.get("cross",-1)>=0 else "–"
                rows.append({
                    "Ticker":   r["ticker"],
                    "Price":    fmt(r["price"]),
                    "%>SMA":    fmt(r["pct_above"],"%",1),
                    "RS":       fmt(r["rs"],"",1),
                    "RS Trend": rs_tag(r["rs"]),
                    "Vol":      fmt(r["vol"],"x",1),
                    "Base":     f"{r['base_w']}w",
                    "Cross":    cross,
                    "Stop":     fmt(r["stop"]),
                    "Risk":     fmt(r["risk"],"%",1),
                    "Stage":    r["stage"],
                    "Score":    f"{r['score']}/5",
                    "Signal":   sig_icon(r.to_dict()),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

            # Export
            st.markdown("---")
            st.markdown("#### 📤 Export to TradingView")
            ec1,ec2,ec3 = st.columns(3)
            all_tks    = ind_df["ticker"].tolist()
            s2_tks     = ind_df[ind_df["score"]>=4]["ticker"].tolist()
            signal_tks = ind_df[ind_df["early_sig"]|ind_df["premium"]]["ticker"].tolist()
            with ec1:
                st.caption("All stocks")
                st.code(export_tv(all_tks), language=None)
                st.download_button("⬇️ All (.txt)", export_tv_lines(all_tks),
                                   file_name=f"TV_{ind_name.replace(' ','_')}_all.txt",
                                   mime="text/plain", key="dl_all")
            with ec2:
                st.caption("Stage 2+ only")
                st.code(export_tv(s2_tks) if s2_tks else "–", language=None)
                if s2_tks:
                    st.download_button("⬇️ S2+ (.txt)", export_tv_lines(s2_tks),
                                       file_name=f"TV_{ind_name.replace(' ','_')}_s2.txt",
                                       mime="text/plain", key="dl_s2")
            with ec3:
                st.caption("PREMIUM + EARLY")
                st.code(export_tv(signal_tks) if signal_tks else "–", language=None)
                if signal_tks:
                    st.download_button("⬇️ Signals (.txt)", export_tv_lines(signal_tks),
                                       file_name=f"TV_{ind_name.replace(' ','_')}_signals.txt",
                                       mime="text/plain", key="dl_sig")
            st.caption("TradingView → Watchlist → Import → paste or upload file")

# ════════════════════════════
# TAB 3: Signals across industries
# ════════════════════════════
with ind_tab3:
    st.markdown("---")
    st.markdown("### 🚨 Industry Signals")
    st.markdown(f"<p class='subtext'>Scan multiple industries at once. Enable Full NYSE+NASDAQ for a complete market scan.</p>", unsafe_allow_html=True)

    sr1, sr2, sr3, sr4 = st.columns([3,1,1,1])
    with sr1:
        sig_inds = st.multiselect("Industries", list(FINVIZ_INDUSTRIES.keys()),
                                   default=list(FINVIZ_INDUSTRIES.keys())[:10],
                                   label_visibility="collapsed")
    with sr2:
        min_score = st.selectbox("Min score", [3,4,5], index=0, key="sig_min")
    with sr3:
        run_scan = st.button("🔍 Scan", width="stretch", key="run_sig")
    with sr4:
        nyse_toggle = st.toggle("Full NYSE+NASDAQ", value=False, key="ind_nyse")

    if nyse_toggle:
        st.info("📡 Scanning full NYSE + NASDAQ universe. First run ~10-15 min, cached 6h.")
        with st.spinner("Batch scanning…"):
            tks = fetch_nyse_tickers()
            results = scan_batch(json.dumps(tks), spx_close_json, min_score=min_score, min_price=2.0)
        if results:
            df_nyse = pd.DataFrame(results)
            n_p = len(df_nyse[df_nyse["premium"]])
            n_e = len(df_nyse[df_nyse["early_sig"]])

            nm1,nm2,nm3,nm4,nm5 = st.columns(5)
            nm1.metric("Total", len(df_nyse))
            nm2.metric("🟢 Premium", n_p)
            nm3.metric("🟡 Early", n_e)
            nm4.metric("🔵 S2", len(df_nyse)-n_p-n_e)

            filt = nm5.selectbox("Show", ["All","🟢+🟡 Best","🟢 Premium","🟡 Early","🔵 S2 only"], key="nyse_filt2")
            if filt == "🟢+🟡 Best":   df_nyse = df_nyse[df_nyse["premium"]|df_nyse["early_sig"]]
            elif filt == "🟢 Premium": df_nyse = df_nyse[df_nyse["premium"]]
            elif filt == "🟡 Early":   df_nyse = df_nyse[df_nyse["early_sig"]]
            elif filt == "🔵 S2 only": df_nyse = df_nyse[~(df_nyse["premium"]|df_nyse["early_sig"])&(df_nyse["score"]>=4)]

            rows = []
            for _, r in df_nyse.iterrows():
                cross = f"{int(r['cross'])}w" if r.get("cross",-1)>=0 else "–"
                ind = TICKER_TO_INDUSTRY.get(r["ticker"],"–")
                rows.append({
                    "Signal": sig_icon(r.to_dict()), "Ticker": r["ticker"],
                    "Industry": ind, "Stage": r["stage"], "Score": f"{r['score']}/5",
                    "RS": fmt(r["rs"],"",1), "RS Trend": rs_tag(r["rs"]),
                    "Price": fmt(r["price"]), "%>SMA": fmt(r["pct_above"],"%",1),
                    "Vol": fmt(r["vol"],"x",1), "Base": f"{r['base_w']}w",
                    "Cross": cross, "Stop": fmt(r["stop"]), "Risk": fmt(r["risk"],"%",1),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=600)
            all_tks = df_nyse["ticker"].tolist()
            st.download_button("⬇️ Export all to TradingView (.txt)",
                               export_tv_lines(all_tks),
                               file_name="TV_full_universe_stage2.txt",
                               mime="text/plain", key="dl_nyse2")

    elif run_scan and sig_inds:
        all_rows = []
        prog = st.progress(0, text="Scanning…")
        for idx, ind in enumerate(sig_inds):
            prog.progress((idx+1)/len(sig_inds), text=f"Scanning {ind}…")
            tks = FINVIZ_INDUSTRIES[ind]
            df  = scan_tickers(json.dumps(tks), spx_close_json)
            if df.empty: continue
            for _, r in df[df["score"]>=min_score].iterrows():
                # Find sector
                sec_name_i = "–"; sec_rs_i = None
                for sec_tk, sec_name in SECTORS.items():
                    if sec_name.lower() in ind.lower():
                        sr_ = sec_df[sec_df["ticker"]==sec_tk]
                        if not sr_.empty:
                            sec_rs_i = sr_.iloc[0]["rs"]; sec_name_i = sec_name; break
                cross = f"{int(r['cross'])}w" if r.get("cross",-1)>=0 else "–"
                all_rows.append({
                    "Signal":    sig_icon(r.to_dict()),
                    "Ticker":    r["ticker"],
                    "Industry":  ind,
                    "Sector":    sec_name_i,
                    "Sec RS":    fmt(sec_rs_i,"",1),
                    "Sec Trend": rs_tag(sec_rs_i),
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
        prog.empty()

        if all_rows:
            sig_df = pd.DataFrame(all_rows).sort_values(
                ["Signal","Score"], ascending=[True,False])
            sm1,sm2,sm3,sm4 = st.columns(4)
            sm1.metric("Total signals", len(sig_df))
            sm2.metric("🟢 Premium", len(sig_df[sig_df["Signal"].str.contains("PREMIUM",na=False)]))
            sm3.metric("🟡 Early",   len(sig_df[sig_df["Signal"].str.contains("EARLY",  na=False)]))
            sm4.metric("🔵 Stage 2", len(sig_df[sig_df["Signal"].str.contains("S2",     na=False)]))
            st.dataframe(sig_df, width="stretch", hide_index=True, height=600)
            st.download_button("⬇️ Export all signals (.txt)",
                               export_tv_lines(sig_df["Ticker"].tolist()),
                               file_name="TV_industry_signals.txt",
                               mime="text/plain", key="dl_indsig")
        else:
            st.info("No signals found. Try lowering the minimum score or selecting more industries.")
