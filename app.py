import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 200 Momentum Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #060e1c; color: #e0e8ff; }
    .main .block-container { padding-top: 1.5rem; max-width: 1100px; }
    
    .metric-card {
        background: #0d1b2e;
        border: 1px solid #1a2744;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .metric-label { color: #5c7099; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 4px; }
    .metric-value { color: #e0e8ff; font-size: 20px; font-weight: 800; }
    
    .verdict-elite  { color: #00c853; }
    .verdict-strong { color: #ff9100; }
    .verdict-trade  { color: #2979ff; }
    .verdict-avoid  { color: #f44336; }
    
    .flag-bull { color: #00c853; }
    .flag-warn { color: #ff9100; }
    .flag-bear { color: #f44336; }

    .scanner-code {
        background: #060e1c;
        border: 1px solid #1a2744;
        border-radius: 8px;
        padding: 14px;
        font-family: monospace;
        font-size: 12px;
        color: #a5d6a7;
        line-height: 1.9;
        white-space: pre-wrap;
        word-break: break-word;
    }
    div[data-testid="stMetricValue"] { color: #e0e8ff !important; }
    .stButton button {
        background: linear-gradient(135deg, #1565c0, #0d47a1) !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }
    h1, h2, h3 { color: #e0e8ff !important; }
    .stSelectbox label, .stTextInput label, .stNumberInput label { color: #7b8fba !important; }
    .stTabs [data-baseweb="tab"] { color: #7b8fba !important; }
    .stTabs [aria-selected="true"] { color: #e0e8ff !important; border-bottom-color: #2979ff !important; }
</style>
""", unsafe_allow_html=True)

# ─── NIFTY 200 POPULAR TICKERS ───────────────────────────────────────────────
POPULAR_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "LT",
    "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN", "WIPRO", "ULTRACEMCO",
    "NESTLEIND", "SUNPHARMA", "HCLTECH", "TECHM", "POWERGRID", "NTPC",
    "ONGC", "TATAMOTORS", "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "CIPLA", "DRREDDY", "DIVISLAB", "APOLLOHOSP", "BAJAJFINSV",
    "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "M&M", "TATACONSUM",
    "BRITANNIA", "DABUR", "MARICO", "PIDILITIND", "BERGEPAINT",
    "HAVELLS", "VOLTAS", "WHIRLPOOL", "SIEMENS", "ABB",
    "DATAPATTNS", "BEL", "HAL", "BHEL", "COCHINSHIP",
    "INDSWFTLAB", "LALPATHLAB", "METROPOLIS", "THYROCARE",
]

# ─── DATA FETCH ──────────────────────────────────────────────────────────────
def fetch_stock_data(symbol: str):
    ticker_ns  = f"{symbol}.NS"
    ticker_bse = f"{symbol}.BO"

    for ticker in [ticker_ns, ticker_bse]:
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period="2y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 50:
                df = df.dropna(subset=["Close"])
                return df, {}, ticker
        except Exception:
            continue
    return None, None, None



def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA20"]   = calc_ema(df["Close"], 20)
    df["EMA50"]   = calc_ema(df["Close"], 50)
    df["EMA200"]  = calc_ema(df["Close"], 200)
    df["SMA50V"]  = calc_sma(df["Volume"], 50)
    df["SMA10V"]  = calc_sma(df["Volume"], 10)
    df["VolRatio"] = df["Volume"] / df["SMA50V"]
    df["High52W"] = df["High"].rolling(window=252, min_periods=100).max()
    return df


def compute_returns(df: pd.DataFrame):
    price_now = df["Close"].iloc[-1]
    r6m  = None
    r12m = None
    if len(df) >= 126:
        p6  = df["Close"].iloc[-126]
        r6m = ((price_now - p6) / p6) * 100
    if len(df) >= 252:
        p12  = df["Close"].iloc[-252]
        r12m = ((price_now - p12) / p12) * 100
    return r6m, r12m

# ─── SCORER ──────────────────────────────────────────────────────────────────
def score_stock(row: dict) -> dict:
    p    = row.get("price", 0)
    h52  = row.get("high52w", 0)
    e20  = row.get("ema20", 0)
    e50  = row.get("ema50", 0)
    e200 = row.get("ema200", 0)
    r6   = row.get("return6m")
    r12  = row.get("return12m")
    vr   = row.get("vol_ratio")

    es=hs=vs=s6=s12=0
    ls = 3
    flags = []

    # EMA Stack — 20pts
    if p and e20 and e50 and e200:
        if p > e20 > e50 > e200:
            es = 20; flags.append(("bull", "Full EMA stack bullish — Stage 2 confirmed ✓"))
        elif e20 > e50 > e200:
            es = 14; flags.append(("warn", "Stack aligned but price below EMA20 — wait for reclaim"))
        elif e20 > e50 or e50 > e200:
            es = 7;  flags.append(("warn", "Partial EMA alignment — Stage 2 developing"))
        else:
            es = 0;  flags.append(("bear", "EMA stack bearish — not Stage 2, avoid"))

    # 52W High — 20pts
    pct = ((h52 - p) / h52 * 100) if (p and h52) else None
    if pct is not None:
        if   pct <= 0:   hs=20; flags.append(("bull", f"AT or ABOVE 52W high — confirmed breakout ✓"))
        elif pct <= 1:   hs=18; flags.append(("bull", f"{pct:.1f}% from 52W high — breakout imminent ✓"))
        elif pct <= 3:   hs=15; flags.append(("bull", f"{pct:.1f}% from 52W high — launchpad zone"))
        elif pct <= 7:   hs=10; flags.append(("warn", f"{pct:.1f}% from 52W high — in base"))
        elif pct <= 15:  hs=5;  flags.append(("warn", f"{pct:.1f}% from 52W high — extended base"))
        else:            hs=0;  flags.append(("bear", f"{pct:.1f}% from 52W high — too far, wait"))

    # Volume — 20pts
    if vr is not None:
        if   vr >= 3.0:  vs=20; flags.append(("bull", f"Vol {vr:.1f}x avg — exceptional institutional surge ✓"))
        elif vr >= 2.0:  vs=17; flags.append(("bull", f"Vol {vr:.1f}x avg — strong institutional buying"))
        elif vr >= 1.5:  vs=14; flags.append(("bull", f"Vol {vr:.1f}x avg — confirmed breakout volume ✓"))
        elif vr >= 1.0:  vs=8;  flags.append(("warn", f"Vol {vr:.1f}x avg — average, needs conviction"))
        else:            vs=3;  flags.append(("warn", f"Vol drying up ({vr:.1f}x) — VCP forming"))
    else:
        vs = 10

    # 6M Return — 20pts
    if r6 is not None:
        if   r6 >= 50:  s6=20; flags.append(("bull", f"6M: +{r6:.1f}% — exceptional momentum leader ✓"))
        elif r6 >= 35:  s6=17; flags.append(("bull", f"6M: +{r6:.1f}% — strong outperformer"))
        elif r6 >= 20:  s6=13; flags.append(("bull", f"6M: +{r6:.1f}% — above-average momentum"))
        elif r6 >= 10:  s6=8;  flags.append(("warn", f"6M: +{r6:.1f}% — moderate momentum"))
        elif r6 >= 0:   s6=4;  flags.append(("warn", f"6M: +{r6:.1f}% — weak, market laggard"))
        else:           s6=0;  flags.append(("bear", f"6M: {r6:.1f}% — negative momentum, avoid"))
    else:
        s6 = 10

    # 12M Return — 15pts
    if r12 is not None:
        if   r12 >= 60:  s12=15; flags.append(("bull", f"12M: +{r12:.1f}% — multi-bagger ✓"))
        elif r12 >= 40:  s12=12; flags.append(("bull", f"12M: +{r12:.1f}% — strong annual performer"))
        elif r12 >= 25:  s12=9;  flags.append(("bull", f"12M: +{r12:.1f}% — solid annual momentum"))
        elif r12 >= 10:  s12=6;  flags.append(("warn", f"12M: +{r12:.1f}% — modest annual gain"))
        elif r12 >= 0:   s12=3;  flags.append(("warn", f"12M: +{r12:.1f}% — weak annual"))
        else:            s12=0;  flags.append(("bear", f"12M: {r12:.1f}% — negative annual, avoid"))
    else:
        s12 = 8

    total = es + hs + vs + s6 + s12 + ls

    if total >= 90:   verdict="ELITE SETUP";  action="BUY BREAKOUT"
    elif total >= 80: verdict="STRONG SETUP"; action="BUY BREAKOUT" if (pct is not None and pct <= 3) else "WATCH FOR PULLBACK"
    elif total >= 70: verdict="TRADABLE";     action="WAIT — NOT YET"
    else:             verdict="AVOID";         action="AVOID"

    bs = ("FRESH BREAKOUT ✓" if pct is not None and pct <= 0
          else "NEAR BREAKOUT (<3%)" if pct is not None and pct <= 3
          else "IN BASE" if pct is not None and pct <= 10
          else "EXTENDED" if pct is not None
          else "—")

    sl   = p * 0.95 if p else 0
    t1   = p * 1.08 if p else 0
    t2   = p * 1.15 if p else 0
    t3   = p * 1.25 if p else 0
    qty  = int(10000 / (p * 0.05)) if p else 0

    return dict(
        total=total, verdict=verdict, action=action,
        breakout_status=bs, pct_from_high=pct,
        ema_score=es, high52_score=hs, vol_score=vs,
        mom6_score=s6, mom12_score=s12, liq_score=ls,
        flags=flags, sl=sl, t1=t1, t2=t2, t3=t3,
        qty_1pct=qty,
    )

# ─── CHARTINK SCANNERS ───────────────────────────────────────────────────────
SCANNERS = {
    "🟢 Tier 1 — Fresh 52W Breakout": {
        "desc": "Nifty 200 stocks that broke to 52-week highs this week with volume surge. Act immediately.",
        "code": "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "color": "🟢",
    },
    "🟠 Tier 2 — Near 52W High (Within 3%)": {
        "desc": "Coiling just below 52W highs with drying volume. GTT watchlist candidates.",
        "code": "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "color": "🟠",
    },
    "🔵 Tier 3 — Momentum Continuation": {
        "desc": "Stage 2 stocks with 25%+ in both 6M and 12M. Enter on EMA 20 pullbacks.",
        "code": "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "color": "🔵",
    },
    "🟣 Tier 4 — VCP / Tight Base": {
        "desc": "Volume contraction >25%, within 10% of 52W high. Wait for the squeeze break.",
        "code": "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "color": "🟣",
    },
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def verdict_color(v):
    return {"ELITE SETUP":"#00c853","STRONG SETUP":"#ff9100","TRADABLE":"#2979ff","AVOID":"#f44336"}.get(v,"#fff")

def score_bar_html(label, sc, mx):
    pct = (sc / mx) * 100
    col = "#00c853" if pct >= 75 else "#ff9100" if pct >= 50 else "#f44336"
    return f"""
    <div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <span style="color:#7b8fba;font-size:13px;">{label}</span>
        <span style="color:#e0e8ff;font-size:13px;font-weight:700;">{sc}/{mx}</span>
      </div>
      <div style="height:6px;background:#1a2744;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:{pct}%;background:{col};border-radius:3px;transition:width 0.4s;"></div>
      </div>
    </div>"""

def flag_html(flags):
    icons = {"bull":"▲","warn":"◆","bear":"▼"}
    colors = {"bull":"#00c853","warn":"#ff9100","bear":"#f44336"}
    html = ""
    for t, msg in flags:
        c = colors[t]; ic = icons[t]
        html += f"""<div style="display:flex;gap:8px;padding:8px 12px;background:#060e1c;border:1px solid {c}20;border-radius:6px;margin-bottom:6px;">
            <span style="color:{c};font-weight:700;min-width:14px;">{ic}</span>
            <span style="color:#7b8fba;font-size:13px;line-height:1.5;">{msg}</span>
        </div>"""
    return html

# ─── MAIN APP ────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;">
      <div style="width:44px;height:44px;background:linear-gradient(135deg,#1565c0,#0d47a1);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">📈</div>
      <div>
        <div style="font-size:20px;font-weight:800;color:#e0e8ff;letter-spacing:0.5px;">NIFTY 200 MOMENTUM SCANNER</div>
        <div style="font-size:12px;color:#5c7099;">Live NSE Data via yfinance · Strategy 1 · Minervini × O'Neil × Weinstein</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["⚡ Live Stock Scorer", "📡 Chartink Scanners", "📖 Score Logic"])

    # ── TAB 1: LIVE SCORER ────────────────────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns([1, 1.6], gap="large")

        with col_left:
            st.markdown("### 🔍 Stock Lookup")
            st.markdown("<p style='color:#7b8fba;font-size:13px;'>Type any NSE symbol. Data auto-fetched via yfinance — no API key needed.</p>", unsafe_allow_html=True)

            symbol = st.text_input(
                "NSE Symbol",
                placeholder="e.g. TCS, RELIANCE, HDFCBANK, DATAPATTNS",
                help="Enter exact NSE ticker symbol"
            ).upper().strip()

            or_pick = st.selectbox(
                "Or pick from popular stocks",
                [""] + sorted(POPULAR_STOCKS),
                index=0
            )
            if or_pick:
                symbol = or_pick

            capital = st.number_input(
                "Your Trading Capital (₹)",
                min_value=100000,
                max_value=10000000,
                value=500000,
                step=50000,
                format="%d",
                help="Used to calculate position size at 1% risk"
            )

            fetch_btn = st.button("⚡ Fetch Live Data & Score", use_container_width=True)

        with col_right:
            if fetch_btn and symbol:
                with st.spinner(f"Fetching {symbol} from NSE via yfinance..."):
                    df, info, used_ticker = fetch_stock_data(symbol)

                if df is None:
                    st.error(f"❌ Could not fetch data for **{symbol}**. Check the symbol and try again.\n\nTry: RELIANCE, TCS, HDFCBANK, INFY, DATAPATTNS, BEL, HAL")
                else:
                    df = enrich(df)
                    latest = df.iloc[-1]
                    prev   = df.iloc[-2]
                    r6m, r12m = compute_returns(df)

                    price    = float(latest["Close"])
                    high52w  = float(latest["High52W"]) if not np.isnan(latest["High52W"]) else float(df["High"].max())
                    ema20    = float(latest["EMA20"])
                    ema50    = float(latest["EMA50"])
                    ema200   = float(latest["EMA200"])
                    vol_ratio= float(latest["VolRatio"]) if not np.isnan(latest["VolRatio"]) else None
                    day_chg  = ((price - float(prev["Close"])) / float(prev["Close"])) * 100

                    row = dict(price=price, high52w=high52w, ema20=ema20, ema50=ema50,
                               ema200=ema200, return6m=r6m, return12m=r12m, vol_ratio=vol_ratio)
                    res = score_stock(row)

                    vc = verdict_color(res["verdict"])
                    qty = int(capital * 0.01 / (price * 0.05)) if price else 0
                    pos_val = qty * price

                    # Stock header
                    chg_col = "#00c853" if day_chg >= 0 else "#f44336"
                    chg_arrow = "▲" if day_chg >= 0 else "▼"
                    st.markdown(f"""
                    <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                          <div style="color:#90caf9;font-size:12px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">{used_ticker}</div>
                          <div style="color:#e0e8ff;font-size:26px;font-weight:900;">₹{price:,.2f}</div>
                        </div>
                        <div style="text-align:right;">
                          <div style="color:{chg_col};font-size:16px;font-weight:700;">{chg_arrow} {abs(day_chg):.2f}%</div>
                          <div style="color:#5c7099;font-size:11px;">Today</div>
                          <div style="color:#5c7099;font-size:11px;">{df.index[-1].strftime('%d %b %Y')}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Data tiles
                    c1,c2,c3 = st.columns(3)
                    pct_h = res["pct_from_high"]
                    pct_col = "#00c853" if pct_h is not None and pct_h<=3 else "#ff9100"
                    pct_txt = "ABOVE ✓" if pct_h is not None and pct_h<=0 else f"{pct_h:.1f}% below" if pct_h else "—"

                    with c1:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">52W HIGH</div><div class="metric-value" style="font-size:15px;">₹{high52w:,.1f}</div></div>', unsafe_allow_html=True)
                        e20c = "#00c853" if price > ema20 else "#f44336"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">EMA 20</div><div class="metric-value" style="color:{e20c};font-size:15px;">₹{ema20:,.1f}</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">FROM 52W HIGH</div><div class="metric-value" style="color:{pct_col};font-size:15px;">{pct_txt}</div></div>', unsafe_allow_html=True)
                        e50c = "#00c853" if ema20 > ema50 else "#f44336"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">EMA 50</div><div class="metric-value" style="color:{e50c};font-size:15px;">₹{ema50:,.1f}</div></div>', unsafe_allow_html=True)
                    with c3:
                        vrc = "#00c853" if vol_ratio and vol_ratio>=1.5 else "#ff9100" if vol_ratio and vol_ratio>=1 else "#f44336"
                        vrt = f"{vol_ratio:.1f}x" if vol_ratio else "—"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">VOLUME RATIO</div><div class="metric-value" style="color:{vrc};font-size:15px;">{vrt}</div></div>', unsafe_allow_html=True)
                        e200c = "#00c853" if ema50 > ema200 else "#f44336"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">EMA 200</div><div class="metric-value" style="color:{e200c};font-size:15px;">₹{ema200:,.1f}</div></div>', unsafe_allow_html=True)

                    rc1, rc2 = st.columns(2)
                    with rc1:
                        r6c = "#00c853" if r6m and r6m>=20 else "#ff9100" if r6m and r6m>=0 else "#f44336"
                        r6t = f"+{r6m:.1f}%" if r6m and r6m>=0 else f"{r6m:.1f}%" if r6m else "< 6M data"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">6-MONTH RETURN</div><div class="metric-value" style="color:{r6c};font-size:18px;">{r6t}</div></div>', unsafe_allow_html=True)
                    with rc2:
                        r12c = "#00c853" if r12m and r12m>=25 else "#ff9100" if r12m and r12m>=0 else "#f44336"
                        r12t = f"+{r12m:.1f}%" if r12m and r12m>=0 else f"{r12m:.1f}%" if r12m else "< 12M data"
                        st.markdown(f'<div class="metric-card"><div class="metric-label">12-MONTH RETURN</div><div class="metric-value" style="color:{r12c};font-size:18px;">{r12t}</div></div>', unsafe_allow_html=True)

                    st.markdown("---")

                    # Big score
                    ac = {"BUY BREAKOUT":"#00c853","WATCH FOR PULLBACK":"#ff9100","WAIT — NOT YET":"#2979ff","AVOID":"#f44336"}.get(res["action"],"#fff")
                    st.markdown(f"""
                    <div style="background:#060e1c;border:2px solid {vc}40;border-radius:14px;padding:24px;text-align:center;margin-bottom:16px;">
                      <div style="font-size:72px;font-weight:900;color:{vc};line-height:1;">{res['total']}</div>
                      <div style="color:#5c7099;font-size:12px;margin-bottom:14px;">OUT OF 100</div>
                      <div style="display:inline-block;background:{vc}20;color:{vc};border:1px solid {vc}50;border-radius:8px;padding:6px 24px;font-size:16px;font-weight:800;letter-spacing:1px;">{res['verdict']}</div>
                      <div style="color:{ac};font-size:15px;font-weight:700;margin-top:14px;">→ {res['action']}</div>
                      <div style="color:#5c7099;font-size:12px;margin-top:8px;">Status: <span style="color:{'#00c853' if res['pct_from_high'] is not None and res['pct_from_high']<=3 else '#7b8fba'}">{res['breakout_status']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Score bars
                    bars_html = "".join([
                        score_bar_html("EMA Stack (20>50>200)",   res["ema_score"],  20),
                        score_bar_html("52W High Position",        res["high52_score"],20),
                        score_bar_html("Volume Confirmation",       res["vol_score"],  20),
                        score_bar_html("6M Momentum Return",        res["mom6_score"], 20),
                        score_bar_html("12M Momentum Return",       res["mom12_score"],15),
                        score_bar_html("Liquidity Filter",          res["liq_score"],  5),
                    ])
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:14px;">SCORE BREAKDOWN</div>{bars_html}</div>', unsafe_allow_html=True)

                    # Trade levels
                    st.markdown(f"""
                    <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;">
                      <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:14px;">TRADE LEVELS</div>
                      <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:12px;">
                        <div style="background:#060e1c;border:1px solid #2979ff30;border-radius:8px;padding:10px;">
                          <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">ENTRY</div>
                          <div style="color:#2979ff;font-size:13px;font-weight:700;">₹{price:,.1f}</div>
                        </div>
                        <div style="background:#060e1c;border:1px solid #f4433630;border-radius:8px;padding:10px;">
                          <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">STOP LOSS 5%</div>
                          <div style="color:#f44336;font-size:13px;font-weight:700;">₹{res['sl']:,.1f}</div>
                        </div>
                        <div style="background:#060e1c;border:1px solid #ff910030;border-radius:8px;padding:10px;">
                          <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">TARGET 1 +8%</div>
                          <div style="color:#ff9100;font-size:13px;font-weight:700;">₹{res['t1']:,.1f}</div>
                        </div>
                        <div style="background:#060e1c;border:1px solid #00c85330;border-radius:8px;padding:10px;">
                          <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">TARGET 2 +15%</div>
                          <div style="color:#00c853;font-size:13px;font-weight:700;">₹{res['t2']:,.1f}</div>
                        </div>
                      </div>
                      <div style="background:#060e1c;border:1px solid #00c85320;border-radius:8px;padding:12px;text-align:center;margin-bottom:10px;">
                        <span style="color:#5c7099;font-size:12px;">RISK : REWARD = </span>
                        <span style="color:#00c853;font-size:16px;font-weight:800;">1 : 3.0 &nbsp;</span>
                        <span style="color:#5c7099;font-size:12px;">(5% SL → 15% Target)</span>
                      </div>
                      <div style="background:#060e1c;border:1px solid #2979ff20;border-radius:8px;padding:12px;">
                        <div style="color:#5c7099;font-size:10px;font-weight:600;margin-bottom:5px;">POSITION SIZE — 1% RISK ON ₹{capital:,}</div>
                        <div style="color:#90caf9;font-size:14px;font-weight:700;">{qty} shares &nbsp;·&nbsp; Position value: ₹{pos_val:,.0f}</div>
                        <div style="color:#5c7099;font-size:11px;margin-top:4px;">Max risk = ₹{capital*0.01:,.0f} &nbsp;|&nbsp; SL at ₹{res['sl']:,.1f}</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Signal flags
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">SIGNAL FLAGS</div>{flag_html(res["flags"])}</div>', unsafe_allow_html=True)

            elif not fetch_btn:
                st.markdown("""
                <div style="background:#0d1b2e;border:1px solid #2979ff30;border-radius:10px;padding:24px;text-align:center;margin-top:20px;">
                  <div style="font-size:32px;margin-bottom:12px;">🔍</div>
                  <div style="color:#e0e8ff;font-size:15px;font-weight:600;margin-bottom:8px;">Enter a stock symbol and click Fetch</div>
                  <div style="color:#5c7099;font-size:13px;line-height:1.7;">
                    Works with any NSE stock.<br>
                    Data is fetched live from Yahoo Finance.<br>
                    No API key needed.
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: CHARTINK SCANNERS ─────────────────────────────────────────────
    with tab2:
        st.markdown("### 📡 Chartink Scanner Codes")
        st.markdown("<p style='color:#7b8fba;'>Run these after 4 PM IST. Paste into chartink.com → Screens → Create New Screen.</p>", unsafe_allow_html=True)

        for name, data in SCANNERS.items():
            with st.expander(name):
                st.markdown(f"<p style='color:#7b8fba;font-size:13px;'>{data['desc']}</p>", unsafe_allow_html=True)
                st.code(data["code"], language="text")
                st.caption("Copy the code above → paste into Chartink → click Generate")

    # ── TAB 3: SCORE LOGIC ───────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📖 Scoring Methodology")
        st.markdown("""
        <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:16px;">
          <div style="color:#5c7099;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">NSE NIFTY200 MOMENTUM30 — OFFICIAL FORMULA</div>
          <div style="background:#060e1c;border:1px solid #1a2744;border-radius:8px;padding:14px;font-family:monospace;font-size:13px;line-height:2;color:#a5d6a7;">
            Score_6M  = (6M Return) ÷ (6M Daily Std Dev)<br>
            Score_12M = (12M Return) ÷ (12M Daily Std Dev)<br>
            <span style="color:#90caf9;">Final Score = Z(Score_6M) + Z(Score_12M)</span><br>
            <span style="color:#5c7099;font-size:11px;">Z = z-scored across the Nifty200 universe · Top 30 stocks held monthly</span>
          </div>
          <div style="color:#7b8fba;font-size:13px;line-height:1.7;margin-top:12px;">
            Strategy delivered <strong style="color:#00c853;">19.3% CAGR</strong> (Apr 2005–Sep 2025) vs 14.3% for Nifty200 TRI. Source: HDFC AMC / NSE Indices whitepaper.
          </div>
        </div>
        """, unsafe_allow_html=True)

        criteria = [
            ("EMA Stack (20 > 50 > 200)", 20, "Full bullish = 20 | Partial = 7–14 | Broken = 0"),
            ("Price vs 52W High",          20, "At/above=20 | <1%=18 | <3%=15 | <7%=10 | <15%=5 | Far=0"),
            ("Volume vs 50D Average",      20, "≥3x=20 | ≥2x=17 | ≥1.5x=14 | ≥1x=8 | <1x=3"),
            ("6-Month Return (%)",         20, "≥50%=20 | ≥35%=17 | ≥20%=13 | ≥10%=8 | ≥0%=4 | Negative=0"),
            ("12-Month Return (%)",        15, "≥60%=15 | ≥40%=12 | ≥25%=9 | ≥10%=6 | ≥0%=3 | Negative=0"),
            ("Liquidity (Nifty200)",        5, "Nifty200 stock assumed ≥₹25Cr turnover = 3pts baseline"),
        ]
        for lbl, wt, desc in criteria:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{lbl}**")
                st.caption(desc)
            with c2:
                st.markdown(f"<div style='text-align:center;background:#060e1c;border:1px solid #2979ff30;border-radius:8px;padding:8px;'><div style='color:#2979ff;font-weight:800;font-size:18px;'>{wt}</div><div style='color:#5c7099;font-size:10px;'>PTS</div></div>", unsafe_allow_html=True)
            st.markdown("---")

        st.markdown("#### Verdict Thresholds")
        for rng, lbl, col, desc in [
            ("90–100","ELITE SETUP","#00c853","Act immediately — rare setup"),
            ("80–89","STRONG SETUP","#ff9100","Full 1% risk — high conviction"),
            ("70–79","TRADABLE","#2979ff","Half size — 0.5% risk only"),
            ("Below 70","AVOID","#f44336","No trade is the best trade"),
        ]:
            st.markdown(f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:10px;'><span style='background:{col}20;color:{col};border:1px solid {col}40;border-radius:4px;padding:3px 10px;font-size:11px;font-weight:800;min-width:90px;text-align:center;'>{lbl}</span><span style='color:#7b8fba;'>{rng} — {desc}</span></div>", unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div style="margin-top:30px;padding:12px 16px;background:#0d1b2e;border:1px solid #1a2744;border-radius:8px;color:#3d5070;font-size:11px;line-height:1.6;">
    Educational only. Not SEBI-registered investment advice. Data sourced from Yahoo Finance via yfinance — may have end-of-day delay.
    Always verify on NSE/TradingView before trading. Past performance does not guarantee future returns.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
