"""
utils/screener.py — Weinstein Stage Analysis engine
=====================================================
All indicator calculations and evaluation logic.
Designed for batch efficiency.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import StringIO
import json
import warnings
warnings.filterwarnings("ignore")

# ── Config ──────────────────────────────────────────────────
SMA_WEEKS            = 50
RS_MA_WEEKS          = 10
SMA_SLOPE_LOOKBACK   = 10
BREAKOUT_LOOKBACK    = 52
MAX_ABOVE_SMA        = 0.30
RECENT_CROSS_WEEKS   = 8
VOLUME_AVG_WEEKS     = 26
VOLUME_BREAKOUT_MULT = 1.5
BASE_RANGE_PCT       = 0.15
SWING_LOOKBACK_WEEKS = 8
YEARS_OF_DATA        = 4
SLOPE_THRESHOLD      = 0.0005
BENCHMARK            = "SPY"


# ── Data fetching ─────────────────────────────────────────────

@st.cache_data(ttl=6*3600, show_spinner=False)
def fetch_weekly(ticker: str, years: int = YEARS_OF_DATA) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(weeks=years * 52 + 10)
    try:
        df = yf.download(ticker, start=start, end=end, interval="1wk",
                         auto_adjust=True, progress=False, threads=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=24*3600, show_spinner=False)
def fetch_nyse_tickers() -> list:
    import urllib.request
    urls = [
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nyse/nyse_tickers.txt",
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.txt",
    ]
    tickers = []
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = r.read().decode("utf-8")
            tickers += [t.strip() for t in data.strip().splitlines()
                        if t.strip() and "." not in t and len(t.strip()) <= 5]
        except Exception:
            pass
    return sorted(set(tickers))


@st.cache_data(ttl=6*3600, show_spinner=False)
def get_spx_data() -> tuple:
    """Return (spx_eval, sec_df, spx_close_json)"""
    from utils.screener import fetch_weekly, evaluate, SECTORS
    spx_df = fetch_weekly(BENCHMARK)
    if spx_df.empty:
        return None, None, None
    spx_close = spx_df["Close"]
    spx_ev = evaluate(spx_df, spx_close)
    spx_ev["ticker"] = "SPY"; spx_ev["name"] = "S&P 500"
    rows = []
    for tk, nm in SECTORS.items():
        df = fetch_weekly(tk)
        if df.empty: continue
        ev = evaluate(df, spx_close)
        ev["ticker"] = tk; ev["name"] = nm
        rows.append(ev)
    sec_df = pd.DataFrame(rows).sort_values(["score","rs"], ascending=[False,False]).reset_index(drop=True)
    return spx_ev, sec_df, spx_close.to_json()


# ── Indicators ────────────────────────────────────────────────

def _sma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w).mean()

def _slope(s: pd.Series, lb: int) -> float:
    v = s.dropna().iloc[-lb:]
    if len(v) < lb: return np.nan
    slope, _ = np.polyfit(np.arange(len(v)), v.values, 1)
    return slope / v.iloc[-1]

def _rs_line(a: pd.Series, b: pd.Series) -> pd.Series:
    c = pd.concat([a, b], axis=1).dropna()
    return c.iloc[:, 0] / c.iloc[:, 1]

def _rs_score(rs: pd.Series, w: int = RS_MA_WEEKS) -> float:
    if len(rs) < w + 5: return np.nan
    rm = _sma(rs, w)
    if pd.isna(rm.iloc[-1]) or rm.iloc[-1] == 0: return np.nan
    above = (rs.iloc[-1] / rm.iloc[-1]) - 1
    past  = rs.iloc[-(w+1)]
    if past == 0 or pd.isna(past): return np.nan
    return round((above + (rs.iloc[-1]/past - 1)) * 100, 2)

def _detect_cross(price: pd.Series, ma: pd.Series, weeks: int) -> int:
    c = pd.concat([price, ma], axis=1).dropna().iloc[-(weeks+5):]
    if len(c) < 2: return -1
    above = (c.iloc[:,0] > c.iloc[:,1]).values
    for i in range(len(above)-1, 0, -1):
        if above[i] and not above[i-1]:
            w = len(above)-1-i
            return w if w <= weeks else -1
    return -1

def _base_len(close: pd.Series, ma: pd.Series, cross_wks: int) -> int:
    if cross_wks < 0:
        c = pd.concat([close, ma], axis=1).dropna()
        if c.empty: return 0
        weeks = 0
        for i in range(len(c)-1, -1, -1):
            p, m = c.iloc[i, 0], c.iloc[i, 1]
            if pd.isna(m) or m == 0: break
            if abs(p/m - 1) <= BASE_RANGE_PCT: weeks += 1
            else: break
        return weeks
    bx  = len(close) - 1 - cross_wks
    if bx < 5: return 0
    bp  = float(close.iloc[bx])
    base_start = 0
    for i in range(bx-1, -1, -1):
        if float(close.iloc[i]) >= bp * 0.92:
            base_start = i
            break
    return bx - base_start

def _base_quality(w: int) -> str:
    if w < 15: return "Short"
    if w < 40: return "Medium"
    if w < 80: return "Long"
    return "V.Long"

def _bo_vol(volume: pd.Series, cross_wks: int):
    if cross_wks < 0: return None
    idx = len(volume)-1-cross_wks
    if idx < VOLUME_AVG_WEEKS: return None
    bv = float(volume.iloc[idx])
    bl = float(volume.iloc[idx-VOLUME_AVG_WEEKS:idx].mean())
    return round(bv/bl, 2) if bl > 0 else None

def _rec_vol(volume: pd.Series, wb: int = 4):
    if len(volume) < VOLUME_AVG_WEEKS+wb: return None
    bl = float(volume.iloc[-(VOLUME_AVG_WEEKS+wb):-wb].mean())
    rc = float(volume.iloc[-wb:].mean())
    return round(rc/bl, 2) if bl > 0 else None

def _calc_stop(close: pd.Series, ma: pd.Series):
    cp = float(close.iloc[-1]); cm = float(ma.iloc[-1])
    sl = float(close.iloc[-SWING_LOOKBACK_WEEKS:].min())
    cands = [v for v in [cm, sl] if v < cp and not pd.isna(v)]
    if not cands: return None, None
    stop = max(cands)
    return round(stop, 2), round((stop/cp - 1)*100, 1)

def _stage(price: pd.Series, ma: pd.Series, slope: float) -> str:
    if pd.isna(ma.iloc[-1]) or pd.isna(slope): return "Unknown"
    ab = price.iloc[-1] > ma.iloc[-1]
    if ab and slope > SLOPE_THRESHOLD:       return "Stage 2"
    if ab and slope <= SLOPE_THRESHOLD:      return "Stage 3"
    if not ab and slope < -SLOPE_THRESHOLD:  return "Stage 4"
    return "Stage 1"


# ── Main evaluation ──────────────────────────────────────────

def evaluate(df: pd.DataFrame, spx_close: pd.Series) -> dict:
    r = dict(price=None, sma50w=None, pct_above=None,
             above_sma=False, sma_rising=False, rs_up=False,
             near_high=False, not_extended=False,
             rs=None, stage="Unknown", cross=-1, early=False,
             vol=None, vol_ok=False, base_w=0, base_q="Short",
             stop=None, risk=None, score=0, label="Not Stage 2",
             early_sig=False, premium=False, base_tightness=None)
    if df.empty or len(df) < SMA_WEEKS+5: return r

    close = df["Close"]; volume = df["Volume"]
    ma50  = _sma(close, SMA_WEEKS)
    cp, cm = float(close.iloc[-1]), float(ma50.iloc[-1])
    if pd.isna(cm): return r

    r["price"] = round(cp, 2); r["sma50w"] = round(cm, 2)
    pct = (cp/cm)-1; r["pct_above"] = round(pct*100, 1)
    slope = _slope(ma50, SMA_SLOPE_LOOKBACK)
    r["above_sma"]  = cp > cm
    r["sma_rising"] = not pd.isna(slope) and slope > SLOPE_THRESHOLD
    rs = _rs_line(close, spx_close)
    sc = _rs_score(rs)
    r["rs"] = sc; r["rs_up"] = not pd.isna(sc) and sc > 0
    wh = float(close.iloc[-BREAKOUT_LOOKBACK:].max())
    r["near_high"]    = (cp/wh)-1 >= -0.15
    r["not_extended"] = 0 < pct < MAX_ABOVE_SMA
    r["stage"]        = _stage(close, ma50, slope)
    cross = _detect_cross(close, ma50, RECENT_CROSS_WEEKS)
    r["cross"] = cross; r["early"] = 0 <= cross <= RECENT_CROSS_WEEKS
    bv = _bo_vol(volume, cross) if cross >= 0 else None
    rv = _rec_vol(volume)
    r["vol"]    = bv if bv is not None else rv
    r["vol_ok"] = r["vol"] is not None and r["vol"] >= VOLUME_BREAKOUT_MULT
    bw = _base_len(close, ma50, cross)
    r["base_w"] = bw; r["base_q"] = _base_quality(bw)
    r["stop"], r["risk"] = _calc_stop(close, ma50)
    r["score"] = sum([r["above_sma"], r["sma_rising"], r["rs_up"], r["near_high"], r["not_extended"]])
    labels = {5:"STRONG Stage 2", 4:"Stage 2", 3:"Borderline"}
    r["label"] = labels.get(r["score"], "Not Stage 2")
    r["early_sig"] = r["early"] and r["sma_rising"] and r["rs_up"] and r["vol_ok"]
    r["premium"]   = r["early_sig"] and bw >= 40
    # Tightness
    if bw >= 10:
        bsi = max(0, len(close) - bw - max(cross, 0) - 2)
        bsl = close.iloc[bsi:len(close)-max(cross,0)]
        msl = ma50.iloc[bsi:len(close)-max(cross,0)]
        rat = (bsl / msl - 1).dropna()
        r["base_tightness"] = round(float(rat.std())*100, 2) if len(rat) > 3 else None
    return r


# ── Batch scanning ───────────────────────────────────────────

@st.cache_data(ttl=6*3600, show_spinner=False)
def scan_tickers(tickers_json: str, spx_close_json: str) -> pd.DataFrame:
    tickers   = json.loads(tickers_json)
    spx_close = pd.read_json(StringIO(spx_close_json), typ="series")
    rows = []
    for tk in tickers:
        df = fetch_weekly(tk)
        if df.empty: continue
        ev = evaluate(df, spx_close)
        ev["ticker"] = tk
        rows.append(ev)
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["score","rs"], ascending=[False,False]).reset_index(drop=True)


@st.cache_data(ttl=6*3600, show_spinner=False)
def scan_batch(tickers_json: str, spx_close_json: str, min_score: int = 0,
               min_price: float = 0) -> list:
    """Fast batch download + evaluate. Returns list of dicts."""
    tickers   = json.loads(tickers_json)
    spx_close = pd.read_json(StringIO(spx_close_json), typ="series")
    end   = datetime.today()
    start = end - timedelta(weeks=YEARS_OF_DATA * 52 + 10)
    results   = []
    batch_size = 200

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            raw = yf.download(batch, start=start, end=end, interval="1wk",
                              auto_adjust=True, progress=False,
                              group_by="ticker", threads=False)
        except Exception:
            continue
        for tk in batch:
            try:
                if len(batch) == 1:
                    df = raw.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                else:
                    if tk not in raw.columns.get_level_values(0): continue
                    df = raw[tk].dropna(how="all")
                if df.empty or len(df) < SMA_WEEKS+5: continue
                ev = evaluate(df, spx_close)
                if (ev.get("price") or 0) < min_price:  continue
                if ev.get("score", 0) < min_score:       continue
                ev["ticker"] = tk
                results.append(ev)
            except Exception:
                continue

    results.sort(key=lambda x: (
        -int(x.get("premium", False)),
        -int(x.get("early_sig", False)),
        -x.get("score", 0),
        -(x.get("rs") or -99)
    ))
    return results


# ── Display helpers ───────────────────────────────────────────

def fmt(v, sfx="", d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "–"
    return f"{v:.{d}f}{sfx}"

def rs_tag(score) -> str:
    if score is None or (isinstance(score, float) and np.isnan(score)): return "n/a"
    if score >= 15:  return "▲▲ Strong bull"
    if score >= 5:   return "▲ Bullish"
    if score >= -3:  return "→ Neutral"
    if score >= -15: return "▼ Bearish"
    return "▼▼ Strong bear"

def sig_icon(r: dict) -> str:
    if r.get("premium"):      return "🟢 PREMIUM"
    if r.get("early_sig"):    return "🟡 EARLY"
    if r.get("score",0) >= 4: return "🔵 S2"
    return ""

def export_tv(tickers: list) -> str:
    return ",".join(tickers)

def export_tv_lines(tickers: list) -> str:
    return "\n".join(tickers)

def signal_card_html(r: dict, name: str = "", C: dict = None) -> str:
    if C is None:
        C = {"GREEN":"#4ade80","YELLOW":"#fbbf24","CARD":"#1c1f2e",
             "BORDER":"#2d3149","SUB":"#7b83a6"}
    tag = "PREMIUM" if r.get("premium") else "EARLY"
    cls = "wcard-premium" if r.get("premium") else "wcard-early"
    col = C["GREEN"] if r.get("premium") else C["YELLOW"]
    cross = f"{r['cross']}w ago" if r.get("cross", -1) >= 0 else "–"
    nm = name or r.get("name", r.get("ticker", ""))
    return f"""<div class="{cls}">
      <span style="color:{col};font-weight:700">{tag}</span> &nbsp;
      <strong>{r['ticker']}</strong> {nm} &nbsp;·&nbsp;
      Crossed {cross} &nbsp;·&nbsp; Base {r['base_w']}w ({r['base_q']}) &nbsp;·&nbsp;
      RS {fmt(r['rs'],'',1)} &nbsp;·&nbsp; Vol {fmt(r['vol'],'x',1)} &nbsp;·&nbsp;
      Stop {fmt(r['stop'])} ({fmt(r['risk'],'%',1)})
    </div>"""


# ── Universe definitions ──────────────────────────────────────

SECTORS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Health Care", "XLI": "Industrials", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLU": "Utilities", "XLRE": "Real Estate",
    "XLB": "Materials", "XLC": "Communication Services",
}

SECTOR_STOCKS = {
    "XLK":  ["AAPL","NVDA","MSFT","AVGO","ORCL","CRM","AMD","ACN","ADBE","CSCO",
              "NOW","PANW","FTNT","SNPS","CDNS","AMAT","KLAC","LRCX","MU","TXN","QCOM",
              "ANET","MCHP","ADI","MRVL","ON","ZS","NET","DDOG","MDB","SNOW","PLTR","CRWD"],
    "XLF":  ["BRK-B","JPM","V","MA","BAC","GS","MS","WFC","SPGI","BLK",
              "AXP","C","USB","PNC","TFC","SCHW","COF","CME","ICE","MMC","AON","MET"],
    "XLE":  ["XOM","CVX","COP","EOG","SLB","MPC","PSX","OXY","VLO","WMB",
              "HES","KMI","OKE","BKR","DVN","HAL","CTRA","OVV","EQT","TPL","AR","MTDR"],
    "XLV":  ["LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","DHR","PFE","AMGN",
              "ISRG","BMY","ELV","MDT","GILD","CVS","REGN","VRTX","BSX","CI","HCA","ZTS"],
    "XLI":  ["GE","RTX","CAT","HON","UPS","DE","BA","LMT","MMM","ETN",
              "NOC","GD","EMR","PH","ITW","CSX","NSC","UNP","FDX","WM","TT","AME"],
    "XLY":  ["AMZN","TSLA","HD","MCD","NKE","LOW","SBUX","TJX","BKNG","CMG",
              "ABNB","MAR","GM","ORLY","AZO","ROST","YUM","RCL","LULU","DECK","ULTA"],
    "XLP":  ["PG","COST","KO","PEP","WMT","PM","MDLZ","CL","MO","GIS",
              "STZ","KMB","KR","SYY","KDP","HSY","CHD","EL","MNST","TGT"],
    "XLU":  ["NEE","SO","DUK","AEP","SRE","D","EXC","XEL","PEG","ED",
              "WEC","EIX","AWK","ETR","DTE","FE","AEE","PPL","CMS","VST","CEG"],
    "XLRE": ["PLD","AMT","EQIX","WELL","SPG","PSA","O","DLR","CCI","VICI",
              "AVB","EXR","EQR","MAA","SBAC","INVH","ESS","ARE","UDR","VTR"],
    "XLB":  ["LIN","SHW","FCX","ECL","APD","NEM","DD","CTVA","DOW","PPG",
              "NUE","STLD","VMC","MLM","CF","MOS","RPM","IFF","ALB","FMC"],
    "XLC":  ["META","GOOGL","GOOG","NFLX","TMUS","DIS","VZ","T","CMCSA","EA",
              "TTWO","OMC","IPG","CHTR","FOXA","WBD","LYV","ROKU","PINS","SNAP","TTD"],
}
