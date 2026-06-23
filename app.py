"""
NSE Elite Swing Trading Advisor - v4
Complete rewrite: zero nested f-strings, zero HTML rendering bugs.
All HTML blocks are built using pre-computed plain string variables only.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Elite Swing Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp { background-color: #060e1c; color: #e0e8ff; }
.main .block-container { padding-top: 1rem; max-width: 1200px; }
h1,h2,h3,h4 { color: #e0e8ff !important; }
.stButton button {
    background: linear-gradient(135deg,#1565c0,#0d47a1) !important;
    color: white !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
}
.stTabs [data-baseweb="tab"] { color: #7b8fba !important; }
.stTabs [aria-selected="true"] { color: #e0e8ff !important; border-bottom-color: #2979ff !important; }
.stSelectbox label, .stTextInput label, .stNumberInput label, .stSlider label { color: #7b8fba !important; }
.stExpander { background: #0d1b2e !important; border: 1px solid #1a2744 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ── POPULAR STOCKS ────────────────────────────────────────────────────────────
POPULAR = sorted([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "TITAN","WIPRO","ULTRACEMCO","NESTLEIND","SUNPHARMA","HCLTECH","TECHM",
    "POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP","BAJAJFINSV",
    "EICHERMOT","HEROMOTOCO","M&M","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL",
    "DATAPATTNS","LALPATHLAB","METROPOLIS","AKUMS","MARKSANS","SURYODAY",
    "INDSWFTLAB","THYROCARE","KAYNES","DIXON","AMBER","COALINDIA",
    "GRASIM","DMART","NAUKRI","ZOMATO","IRCTC","IRFC","COCHINSHIP","RVNL",
])

# ── HTML BUILDER — SAFE, NO NESTING ──────────────────────────────────────────
def html_card(content, border_color="#1a2744", left_bar=False):
    """Wraps content in a dark card. All inputs must be plain strings."""
    border = "border-left:4px solid " + border_color + ";" if left_bar else ""
    return (
        '<div style="background:#0d1b2e;border:1px solid ' + border_color + '30;'
        + border
        + 'border-radius:10px;padding:14px 16px;margin-bottom:12px;">'
        + content
        + '</div>'
    )

def html_tile(label, value, color, sub=""):
    """Single data tile. All inputs must be pre-computed plain strings."""
    sub_part = ""
    if sub:
        sub_part = '<div style="color:#5c7099;font-size:10px;margin-top:2px;">' + sub + '</div>'
    return (
        '<div style="background:#060e1c;border:1px solid ' + color + '25;border-radius:8px;padding:10px 12px;">'
        '<div style="color:#5c7099;font-size:9px;font-weight:600;letter-spacing:0.5px;margin-bottom:3px;">' + label + '</div>'
        '<div style="color:' + color + ';font-size:13px;font-weight:700;">' + value + '</div>'
        + sub_part +
        '</div>'
    )

def html_badge(text, color):
    """Small badge/tag. Input must be plain string."""
    return (
        '<span style="background:' + color + '20;color:' + color + ';border:1px solid ' + color + '40;'
        'border-radius:4px;padding:2px 10px;font-size:10px;font-weight:800;letter-spacing:1px;">'
        + text + '</span>'
    )

def html_score_bar(label, score, max_pts):
    """Progress bar for score breakdown. All numbers pre-computed."""
    pct = min(int(score / max_pts * 100), 100)
    if pct >= 75:
        color = "#00c853"
        symbol = "✓"
    elif pct >= 50:
        color = "#ff9100"
        symbol = "◆"
    else:
        color = "#f44336"
        symbol = "✗"
    score_str = str(score) + "/" + str(max_pts)
    pct_str   = str(pct) + "%"
    return (
        '<div style="margin-bottom:9px;">'
        '<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
        '<span style="color:#7b8fba;font-size:12px;">' + label + '</span>'
        '<span style="color:' + color + ';font-size:12px;font-weight:700;">' + symbol + ' ' + score_str + '</span>'
        '</div>'
        '<div style="height:5px;background:#1a2744;border-radius:3px;overflow:hidden;">'
        '<div style="height:100%;width:' + pct_str + ';background:' + color + ';border-radius:3px;"></div>'
        '</div></div>'
    )

def html_flag(flag_type, message):
    """Single signal flag row."""
    colors  = {"bull": "#00c853", "warn": "#ff9100", "bear": "#f44336"}
    icons   = {"bull": "▲",       "warn": "◆",       "bear": "▼"}
    color   = colors.get(flag_type, "#7b8fba")
    icon    = icons.get(flag_type, "•")
    return (
        '<div style="display:flex;gap:8px;padding:7px 11px;background:#060e1c;'
        'border:1px solid ' + color + '20;border-radius:6px;margin-bottom:5px;">'
        '<span style="color:' + color + ';font-weight:700;min-width:12px;">' + icon + '</span>'
        '<span style="color:#7b8fba;font-size:12px;line-height:1.5;">' + message + '</span>'
        '</div>'
    )

def html_level_box(label, value, color, sub=""):
    """Trade level box (entry/SL/target)."""
    sub_part = ""
    if sub:
        sub_part = '<div style="color:#5c7099;font-size:9px;margin-top:2px;">' + sub + '</div>'
    return (
        '<div style="background:#060e1c;border:1px solid ' + color + '30;border-radius:8px;padding:12px;">'
        '<div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">' + label + '</div>'
        '<div style="color:' + color + ';font-size:14px;font-weight:700;">' + value + '</div>'
        + sub_part +
        '</div>'
    )

# ── INDICATORS ────────────────────────────────────────────────────────────────
def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def calc_sma(s, p):
    return s.rolling(p).mean()

def calc_rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(s):
    m   = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()
    sig = m.ewm(span=9, adjust=False).mean()
    return m, sig, m - sig

def enrich(df):
    df       = df.copy()
    df["E10"]  = calc_ema(df["Close"], 10)
    df["E20"]  = calc_ema(df["Close"], 20)
    df["E50"]  = calc_ema(df["Close"], 50)
    df["E200"] = calc_ema(df["Close"], 200)
    df["V50"]  = calc_sma(df["Volume"], 50)
    df["V10"]  = calc_sma(df["Volume"], 10)
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=100).max()
    df["RSI"]  = calc_rsi(df["Close"])
    df["ATR"]  = (df["High"] - df["Low"]).rolling(14).mean()
    m, sig, hist   = calc_macd(df["Close"])
    df["MACD"] = m
    df["SIG"]  = sig
    df["HIST"] = hist
    return df

# ── DATA FETCH ────────────────────────────────────────────────────────────────
def fetch_stock(symbol):
    for sfx in [".NS", ".BO"]:
        try:
            df = yf.Ticker(symbol + sfx).history(period="2y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 60:
                return df.dropna(subset=["Close"]), symbol + sfx
        except Exception:
            continue
    return None, None

def fetch_index(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 50:
            return df.dropna(subset=["Close"])
    except Exception:
        pass
    return None

def safe_float(val):
    """Return float or 0.0 if NaN."""
    try:
        f = float(val)
        return 0.0 if np.isnan(f) else f
    except Exception:
        return 0.0

# ── MARKET REGIME ─────────────────────────────────────────────────────────────
def market_regime(nifty_df, bnifty_df):
    penalty = 0
    rows    = []
    for name, df in [("Nifty 50", nifty_df), ("Bank Nifty", bnifty_df)]:
        if df is None or len(df) < 50:
            rows.append((name, "UNKNOWN", "#7b8fba", 0))
            continue
        d    = enrich(df)
        p    = safe_float(d["Close"].iloc[-1])
        e50  = safe_float(d["E50"].iloc[-1])
        e200 = safe_float(d["E200"].iloc[-1])
        if p < e200:
            rows.append((name, "BEARISH — below 200 EMA", "#f44336", 20))
            penalty = max(penalty, 20)
        elif p < e50:
            rows.append((name, "CAUTION — below 50 EMA", "#ff9100", 10))
            penalty = max(penalty, 10)
        else:
            rows.append((name, "HEALTHY — above all EMAs", "#00c853", 0))
    return rows, penalty

# ── LIQUIDITY GATE ────────────────────────────────────────────────────────────
def liquidity_gate(df):
    price   = safe_float(df["Close"].iloc[-1])
    avg_vol = df["Volume"].tail(50).mean()
    to      = avg_vol * price
    return to, to >= 25_00_00_000

# ── RETURNS ───────────────────────────────────────────────────────────────────
def compute_returns(df, nifty_df):
    p    = safe_float(df["Close"].iloc[-1])
    r6   = None
    r12  = None
    rs   = None
    if len(df) >= 126:
        p6  = safe_float(df["Close"].iloc[-126])
        r6  = (p - p6) / p6 * 100 if p6 > 0 else None
    if len(df) >= 252:
        p12 = safe_float(df["Close"].iloc[-252])
        r12 = (p - p12) / p12 * 100 if p12 > 0 else None
    if nifty_df is not None and len(nifty_df) >= 126 and r6 is not None:
        np_  = safe_float(nifty_df["Close"].iloc[-1])
        np6  = safe_float(nifty_df["Close"].iloc[-126])
        n6   = (np_ - np6) / np6 * 100 if np6 > 0 else 0
        rs   = r6 - n6
    return r6, r12, rs

# ── SPIKE DETECTION ───────────────────────────────────────────────────────────
def spike_info(df):
    if len(df) < 2:
        return 0.0, 0
    p    = safe_float(df["Close"].iloc[-1])
    prev = safe_float(df["Close"].iloc[-2])
    move = (p - prev) / prev * 100 if prev > 0 else 0.0
    if move >= 10:   pen = -20
    elif move >= 8:  pen = -10
    elif move >= 5:  pen = -5
    else:            pen = 0
    return move, pen

# ── PATTERN DETECTION ─────────────────────────────────────────────────────────
def detect_pattern(df):
    if len(df) < 30:
        return "INSUFFICIENT DATA", 0, "Not enough price history."

    l    = df.iloc[-1]
    p    = safe_float(l["Close"])
    h52  = safe_float(l["H52"])  if not np.isnan(l["H52"])  else p
    e20  = safe_float(l["E20"])
    e50  = safe_float(l["E50"])
    e200 = safe_float(l["E200"])
    vr   = safe_float(l["VR"])   if not np.isnan(l["VR"])   else 1.0

    last20  = df["Close"].tail(20)
    last7   = df["Close"].tail(7)
    v10avg  = df["Volume"].tail(10).mean()
    v50avg  = df["Volume"].tail(50).mean()
    vc_ratio= v10avg / v50avg if v50avg > 0 else 1.0
    rng20   = (last20.max() - last20.min()) / last20.mean() * 100 if last20.mean() > 0 else 100
    rng7    = (last7.max()  - last7.min())  / last7.mean()  * 100 if last7.mean()  > 0 else 100
    pct_h   = (h52 - p) / h52 * 100 if h52 > 0 else 100
    move20  = (last20.iloc[-1] - last20.iloc[0]) / last20.iloc[0] * 100 if last20.iloc[0] > 0 else 0

    # VCP
    if pct_h <= 10 and vc_ratio < 0.75 and rng20 < 12 and e20 > e50 > e200:
        conf = 92 if vc_ratio < 0.5 and pct_h < 5 else 85
        expl = (
            "Volume has contracted to " + str(round(vc_ratio * 100)) + "% of 50-day avg. "
            "Price range in last 20 days is only " + str(round(rng20, 1)) + "%. "
            "Stock is " + str(round(pct_h, 1)) + "% from 52W high. "
            "Classic VCP coil — wait for a volume expansion breakout."
        )
        return "VCP", conf, expl

    # Breakout
    if pct_h <= 1 and vr >= 1.5 and p > e20 > e50 > e200:
        conf = 93 if vr >= 2.5 else 88
        expl = (
            "Breaking above 52W high of Rs." + str(round(h52, 1)) + " with volume " + str(round(vr, 1)) + "x average. "
            "Full EMA stack bullish. High-probability momentum entry. "
            "Enter now or on a retest of the breakout level."
        )
        return "BREAKOUT", conf, expl

    # Bull Flag
    if move20 >= 10 and rng7 < 5 and vc_ratio < 0.85 and p > e20:
        conf = 87 if move20 >= 20 else 80
        flag_high = str(round(float(last7.max()), 1))
        expl = (
            "Stock moved +" + str(round(move20, 1)) + "% in last 20 days (the pole). "
            "Now consolidating tightly — last 7 days range only " + str(round(rng7, 1)) + "% (the flag). "
            "Volume contracting during flag = healthy. "
            "Entry on breakout above flag high Rs." + flag_high + " on volume."
        )
        return "BULL FLAG", conf, expl

    # Flat Base
    if rng20 < 8 and pct_h <= 15 and e20 > e50 > e200 and vc_ratio < 0.9:
        expl = (
            "Stock trading in a " + str(round(rng20, 1)) + "% range near its highs for ~20 days. "
            "Volume drying up = healthy base. "
            "Entry when price breaks above base high on 1.5x+ volume."
        )
        return "FLAT BASE", 75, expl

    # EMA20 Pullback
    if p > e50 > e200 and abs(p - e20) / p < 0.03:
        expl = (
            "Stock in Stage 2 uptrend, pulled back to 20 EMA at Rs." + str(round(e20, 1)) + ". "
            "This is the ideal Minervini low-risk entry. "
            "Enter near EMA20 with stop just below it. Tiny risk, big potential."
        )
        return "EMA20 PULLBACK", 80, expl

    # Momentum
    if p > e20 > e50 > e200:
        expl = (
            "Stock in Stage 2 uptrend. No specific base pattern visible yet. "
            "Best entry on pullback to EMA10 or EMA20 — do not chase."
        )
        return "MOMENTUM CONTINUATION", 70, expl

    return "NO CLEAR PATTERN", 40, (
        "No tradable pattern. Price between key levels without a clear setup. "
        "Wait for a VCP, breakout, or EMA pullback."
    )

# ── SECOND LEG DETECTOR ───────────────────────────────────────────────────────
def second_leg(df):
    if len(df) < 60:
        return False, "", 0
    df_r     = df.tail(126)
    max_p    = float(df_r["High"].max())
    min_p    = float(df_r["Low"].min())
    move     = (max_p - min_p) / min_p * 100 if min_p > 0 else 0
    peak_idx = df_r["High"].idxmax()
    after    = df_r.loc[peak_idx:]
    if len(after) < 10:
        return False, "", 0
    base_low  = float(after["Low"].min())
    depth     = (max_p - base_low) / max_p * 100
    price_now = float(df["Close"].iloc[-1])
    pct_peak  = (max_p - price_now) / max_p * 100
    if move >= 25 and depth <= 35 and pct_peak <= 15:
        strength = "STRONG" if move >= 50 and depth <= 20 else "MODERATE"
        msg = (
            "Second Leg Detected (" + strength + "): Stock made a " + str(round(move)) + "% first move, "
            "corrected only " + str(round(depth)) + "% (tight base = institutional holding). "
            "Now " + str(round(pct_peak, 1)) + "% from the prior high. "
            "Base low Rs." + str(round(base_low, 1)) + " is your key support."
        )
        return True, msg, min(95, 75 + int(move / 10))
    return False, "", 0

# ── STOP LOSS ─────────────────────────────────────────────────────────────────
def smart_sl(df, price):
    l    = df.iloc[-1]
    e10  = safe_float(l["E10"])
    e20  = safe_float(l["E20"])
    e50  = safe_float(l["E50"])
    atr  = safe_float(l["ATR"]) if not np.isnan(l["ATR"]) else price * 0.02
    candidates = [
        ("1% below EMA10", e10 * 0.99),
        ("1% below EMA20", e20 * 0.99),
        ("2% below EMA50", e50 * 0.98),
        ("2x ATR below price", price - 2 * atr),
    ]
    for label, sl_price in candidates:
        pct = (price - sl_price) / price * 100
        if 1.0 <= pct <= 6.0:
            return sl_price, pct, label, True
    return None, None, None, False

# ── SCORING ───────────────────────────────────────────────────────────────────
def score_stock(df, r6, r12, rs, regime_pen, pattern, pconf):
    l    = df.iloc[-1]
    p    = safe_float(l["Close"])
    e20  = safe_float(l["E20"])
    e50  = safe_float(l["E50"])
    e200 = safe_float(l["E200"])
    h52  = safe_float(l["H52"]) if not np.isnan(l["H52"]) else p
    vr   = safe_float(l["VR"])  if not np.isnan(l["VR"])  else 1.0
    rsi  = safe_float(l["RSI"]) if not np.isnan(l["RSI"]) else 50.0
    mac  = safe_float(l["MACD"])if not np.isnan(l["MACD"])else 0.0
    hist = safe_float(l["HIST"])if not np.isnan(l["HIST"])else 0.0
    pct_h= (h52 - p) / h52 * 100 if h52 > 0 else 100

    sc    = {}
    flags = []

    # EMA Stack — 20pts
    if p > e20 > e50 > e200:
        sc["ema"] = 20; flags.append(("bull", "Full EMA stack: Price > 20 > 50 > 200 — Stage 2 confirmed"))
    elif e20 > e50 > e200:
        sc["ema"] = 14; flags.append(("warn", "EMA aligned but price below EMA20 — wait for reclaim"))
    elif e20 > e50 or e50 > e200:
        sc["ema"] = 7;  flags.append(("warn", "Partial EMA alignment — developing"))
    else:
        sc["ema"] = 0;  flags.append(("bear", "EMA stack fully bearish — avoid"))

    # 52W High — 15pts
    if pct_h <= 0:    sc["h52"] = 15; flags.append(("bull", "At or above 52W high — breakout confirmed"))
    elif pct_h <= 1:  sc["h52"] = 13; flags.append(("bull", str(round(pct_h,1)) + "% from 52W high — imminent breakout"))
    elif pct_h <= 3:  sc["h52"] = 11; flags.append(("bull", str(round(pct_h,1)) + "% from 52W high — launchpad zone"))
    elif pct_h <= 7:  sc["h52"] = 7;  flags.append(("warn", str(round(pct_h,1)) + "% from 52W high — in base"))
    elif pct_h <= 15: sc["h52"] = 3;  flags.append(("warn", str(round(pct_h,1)) + "% from 52W high — extended base"))
    else:             sc["h52"] = 0;  flags.append(("bear", str(round(pct_h,1)) + "% from 52W high — too far"))

    # Volume — 15pts
    if vr >= 3.0:   sc["vol"] = 15; flags.append(("bull", "Volume " + str(round(vr,1)) + "x avg — exceptional institutional surge"))
    elif vr >= 2.0: sc["vol"] = 12; flags.append(("bull", "Volume " + str(round(vr,1)) + "x avg — strong buying"))
    elif vr >= 1.5: sc["vol"] = 10; flags.append(("bull", "Volume " + str(round(vr,1)) + "x avg — confirmed breakout volume"))
    elif vr >= 1.0: sc["vol"] = 6;  flags.append(("warn", "Volume " + str(round(vr,1)) + "x avg — average"))
    else:           sc["vol"] = 2;  flags.append(("warn", "Volume drying up (" + str(round(vr,1)) + "x) — VCP forming"))

    # MACD — 15pts
    if mac > 0 and hist > 0:
        sc["macd"] = 15; flags.append(("bull", "MACD positive and histogram expanding — momentum accelerating"))
    elif mac > 0:
        sc["macd"] = 10; flags.append(("warn", "MACD positive but histogram contracting — momentum slowing"))
    elif mac > -0.5:
        sc["macd"] = 5;  flags.append(("warn", "MACD near zero — watch for crossover"))
    else:
        sc["macd"] = 0;  flags.append(("bear", "MACD negative — bearish momentum"))

    # RSI — 10pts
    rsi_r = round(rsi)
    if 50 <= rsi <= 65:   sc["rsi"] = 10; flags.append(("bull", "RSI " + str(rsi_r) + " — sweet spot, room to run"))
    elif 65 < rsi <= 70:  sc["rsi"] = 7;  flags.append(("warn", "RSI " + str(rsi_r) + " — approaching overbought"))
    elif 45 <= rsi < 50:  sc["rsi"] = 5;  flags.append(("warn", "RSI " + str(rsi_r) + " — recovering"))
    elif 70 < rsi <= 80:  sc["rsi"] = 2;  flags.append(("warn", "RSI " + str(rsi_r) + " — overbought, chase risk"))
    elif rsi > 80:        sc["rsi"] = 0;  flags.append(("bear", "RSI " + str(rsi_r) + " — extremely overbought"))
    else:                 sc["rsi"] = 0;  flags.append(("bear", "RSI " + str(rsi_r) + " — downtrend territory"))

    # 6M Return — 10pts
    if r6 is None:       sc["r6"] = 5
    elif r6 >= 50:       sc["r6"] = 10; flags.append(("bull", "6M: +" + str(round(r6,1)) + "% — exceptional"))
    elif r6 >= 35:       sc["r6"] = 8;  flags.append(("bull", "6M: +" + str(round(r6,1)) + "% — strong"))
    elif r6 >= 20:       sc["r6"] = 6;  flags.append(("bull", "6M: +" + str(round(r6,1)) + "% — above average"))
    elif r6 >= 10:       sc["r6"] = 4;  flags.append(("warn", "6M: +" + str(round(r6,1)) + "% — moderate"))
    elif r6 >= 0:        sc["r6"] = 2;  flags.append(("warn", "6M: +" + str(round(r6,1)) + "% — weak"))
    else:                sc["r6"] = 0;  flags.append(("bear", "6M: " + str(round(r6,1)) + "% — negative"))

    # 12M Return — 10pts
    if r12 is None:      sc["r12"] = 5
    elif r12 >= 60:      sc["r12"] = 10; flags.append(("bull", "12M: +" + str(round(r12,1)) + "% — multi-bagger"))
    elif r12 >= 40:      sc["r12"] = 8;  flags.append(("bull", "12M: +" + str(round(r12,1)) + "% — strong"))
    elif r12 >= 25:      sc["r12"] = 6;  flags.append(("bull", "12M: +" + str(round(r12,1)) + "% — solid"))
    elif r12 >= 10:      sc["r12"] = 4;  flags.append(("warn", "12M: +" + str(round(r12,1)) + "% — modest"))
    elif r12 >= 0:       sc["r12"] = 2;  flags.append(("warn", "12M: +" + str(round(r12,1)) + "% — weak"))
    else:                sc["r12"] = 0;  flags.append(("bear", "12M: " + str(round(r12,1)) + "% — negative"))

    # RS vs Nifty — 10pts
    if rs is None:       sc["rs"] = 5
    elif rs >= 20:       sc["rs"] = 10; flags.append(("bull", "RS vs Nifty: +" + str(round(rs,1)) + "% — massively outperforming"))
    elif rs >= 10:       sc["rs"] = 8;  flags.append(("bull", "RS vs Nifty: +" + str(round(rs,1)) + "% — outperforming"))
    elif rs >= 5:        sc["rs"] = 6;  flags.append(("bull", "RS vs Nifty: +" + str(round(rs,1)) + "% — slightly ahead"))
    elif rs >= 0:        sc["rs"] = 4;  flags.append(("warn", "RS vs Nifty: +" + str(round(rs,1)) + "% — matching market"))
    else:                sc["rs"] = 0;  flags.append(("bear", "RS vs Nifty: " + str(round(rs,1)) + "% — underperforming"))

    # Pattern bonus — 5pts
    if pconf >= 85:      sc["pat"] = 5; flags.append(("bull", "Pattern: " + pattern + " (confidence " + str(pconf) + "%)"))
    elif pconf >= 70:    sc["pat"] = 3; flags.append(("warn", "Pattern: " + pattern + " (confidence " + str(pconf) + "%)"))
    else:                sc["pat"] = 0; flags.append(("bear", "Pattern: " + pattern + " — low confidence"))

    sc["liq"] = 5  # Liquidity passed gate

    raw   = sum(sc.values())
    norm  = int(raw / 115 * 100)
    move, sp = spike_info(df)
    if sp < 0:
        flags.append(("bear", "SPIKE PENALTY: +" + str(round(move,1)) + "% today — do not chase. Penalty: " + str(sp) + " pts"))

    final = max(0, norm + sp - regime_pen)

    if final >= 90:   verdict = "ELITE SETUP"
    elif final >= 80: verdict = "STRONG SETUP"
    elif final >= 70: verdict = "TRADABLE"
    else:             verdict = "AVOID"

    return final, norm, sp, verdict, sc, flags, move, pct_h

# ── ENTRY LOGIC ───────────────────────────────────────────────────────────────
def entry_logic(df, price, pattern):
    l    = df.iloc[-1]
    e10  = safe_float(l["E10"])
    e20  = safe_float(l["E20"])
    e50  = safe_float(l["E50"])
    e200 = safe_float(l["E200"])
    h52  = safe_float(l["H52"]) if not np.isnan(l["H52"]) else price
    pct_h= (h52 - price) / h52 * 100 if h52 > 0 else 100

    if pattern in ("BREAKOUT",) or pct_h <= 1:
        return {
            "type": "BREAKOUT",
            "agg":  price,
            "con":  round(h52 * 1.005, 1),
            "ret":  round(h52 * 0.99, 1),
            "note": ("Buy the breakout above Rs." + str(round(h52,1)) + ". "
                     "Aggressive = buy now. Conservative = wait for daily close above Rs." + str(round(h52*1.005,1)) + ". "
                     "Retest = if price pulls back to Rs." + str(round(h52*0.99,1)) + " that is the safest add.")
        }
    elif pattern in ("VCP", "FLAT BASE") or (1 < pct_h <= 5):
        return {
            "type": "PRE-BREAKOUT — WAIT",
            "agg":  price,
            "con":  round(h52 * 1.002, 1),
            "ret":  round(e20 * 1.005, 1),
            "note": ("Do NOT chase. Set a price alert at Rs." + str(round(h52,1)) + ". "
                     "Entry only when price breaks Rs." + str(round(h52,1)) + " on volume at least 1.5x average. "
                     "Premature entry risks getting stopped before the move.")
        }
    elif pattern == "BULL FLAG":
        fh = round(float(df["Close"].tail(7).max()), 1)
        return {
            "type": "BULL FLAG BREAKOUT",
            "agg":  fh,
            "con":  round(fh * 1.01, 1),
            "ret":  round(fh * 0.995, 1),
            "note": ("Enter on break above flag high Rs." + str(fh) + " on volume. "
                     "Do not buy inside the flag. Wait for the breakout candle.")
        }
    elif pattern == "EMA20 PULLBACK":
        return {
            "type": "EMA20 PULLBACK — Best R:R",
            "agg":  round(e20 * 1.002, 1),
            "con":  round(e20 * 1.01, 1),
            "ret":  round(e20 * 0.995, 1),
            "note": ("Ideal Minervini entry — buying the dip in an uptrend. "
                     "Enter near EMA20 (Rs." + str(round(e20,1)) + "). "
                     "Stop just below EMA20 = minimal risk, strong R:R.")
        }
    elif pattern == "MOMENTUM CONTINUATION" and p > e20:
        p = price
        return {
            "type": "MOMENTUM — WAIT FOR DIP",
            "agg":  price,
            "con":  round(e10 * 1.005, 1),
            "ret":  round(e20 * 1.005, 1),
            "note": ("Stock is running. Best not to chase. "
                     "Wait for 1-3 day pullback to EMA10 (Rs." + str(round(e10,1)) + ") "
                     "or EMA20 (Rs." + str(round(e20,1)) + "). "
                     "Chasing extended stocks is the number one mistake.")
        }
    else:
        return {
            "type": "WAIT — NO ENTRY",
            "agg":  0,
            "con":  0,
            "ret":  0,
            "note": ("No clean entry. Either wait for a breakout above Rs." + str(round(h52,1)) +
                     " or a pullback to EMA20 (Rs." + str(round(e20,1)) + ").")
        }

# ── TARGETS ───────────────────────────────────────────────────────────────────
def compute_targets(price, sl_price):
    if sl_price is None or sl_price <= 0:
        return None, None, None, 0
    r  = price - sl_price
    return round(price + 1.5*r, 1), round(price + 3.0*r, 1), round(price + 5.0*r, 1), 3.0

# ── CHARTINK SCANNERS ─────────────────────────────────────────────────────────
SCANNERS = {
    "Tier 1 — Fresh 52W High Breakout": {
        "priority": "HIGHEST — ACT IMMEDIATELY",
        "color":    "#00c853",
        "what":     "Stocks that broke their 52-week high THIS WEEK with strong volume.",
        "why":      "A 52W high breakout is the #1 momentum signal. Stocks making new highs tend to keep making new highs. Core of O'Neil CANSLIM and Minervini methodology.",
        "action":   "Run this FIRST after 4 PM IST. Any result here is your highest priority trade for tomorrow. Enter at open or on a retest.",
        "code":     "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions": [
            ("{nifty 200}", "Universe: Only Nifty 200 large/midcap stocks. Filters out penny stocks and operator stocks."),
            ("close > 1 weeks max(52, high)", "Price closed ABOVE the 52-week high. This IS the breakout. No breakout = not in this scan."),
            ("volume > 1.5 x sma(volume,50)", "Volume is 50% above average. Without institutional volume a breakout is fake and will reverse."),
            ("close > ema(20)", "Price above EMA20 = immediate short-term momentum is bullish."),
            ("ema(20) > ema(50) > ema(200)", "All EMAs in bullish order = confirmed Stage 2 uptrend across all timeframes."),
            ("volume x close > 25 Crore", "Minimum Rs.25Cr daily turnover. You must be able to enter and exit without moving the price."),
        ],
    },
    "Tier 2 — Near 52W High / VCP Setup": {
        "priority": "HIGH — BUILD GTT WATCHLIST",
        "color":    "#ff9100",
        "what":     "Stocks within 3% of 52W high with volume DRYING UP — classic VCP/coiling setup before breakout.",
        "why":      "This catches the setup BEFORE Tier 1 fires. Volume drying up = institutions holding, not selling. The spring is coiling. Entry here gives tighter stop and better R:R than chasing the breakout.",
        "action":   "Set a GTT price alert at the 52W high for each result. When it breaks with volume, THEN enter.",
        "code":     "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions": [
            ("close > 0.97 x weekly max(52,high)", "Within 3% of the 52W high — close enough to be a real candidate, not just noise."),
            ("close < weekly max(52,high)", "Has NOT broken out yet. This is anticipation, not confirmation."),
            ("ema(20) > ema(50) > ema(200)", "Base is forming in an UPTREND, not a downtrend. Critical filter."),
            ("sma(volume,10) < sma(volume,50)", "10-day avg volume LESS than 50-day avg = volume is drying up. This IS the VCP signal. Supply being exhausted."),
            ("volume x close > 25 Crore", "Minimum liquidity filter."),
        ],
    },
    "Tier 3 — Momentum Continuation / Second Leg": {
        "priority": "MEDIUM — ENTER ON PULLBACKS ONLY",
        "color":    "#2979ff",
        "what":     "Confirmed Stage 2 stocks up 25%+ in both 6M and 12M — sustained momentum leaders.",
        "why":      "Counter-intuitive but proven: a stock up 50% with a bullish EMA stack is MORE likely to keep rising. This is the Nifty200 Momentum30 methodology that delivered 19.3% CAGR over 20 years.",
        "action":   "Do NOT buy at current price. Wait for 2-5 day pullback to EMA20 with drying volume. Enter at EMA20 with stop below it.",
        "code":     "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "conditions": [
            ("close > ema(20) > ema(50) > ema(200)", "Full bullish EMA alignment = Stage 2 uptrend confirmed."),
            ("close > 1.25 x 26 weeks ago close", "Stock is up at least 25% in 6 months. Strong intermediate momentum."),
            ("close > 1.25 x 52 weeks ago close", "Stock is up at least 25% in 12 months. Long-term momentum is sustained, not a flash."),
            ("volume x close > 25 Crore", "Minimum liquidity filter."),
        ],
    },
    "Tier 4 — VCP / Tight Base Detector": {
        "priority": "HIGH — CHART REVIEW REQUIRED",
        "color":    "#aa00ff",
        "what":     "Pure VCP: within 10% of highs with volume contracted more than 25%.",
        "why":      "When volume contracts sharply while price stays near highs, supply is exhausted. The eventual breakout is explosive. This is Minervini's primary setup.",
        "action":   "Open each result in TradingView. Look for tightening price bars + shrinking ATR + volume dry-up. Entry on breakout above the tight range on 2x+ volume.",
        "code":     "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions": [
            ("close > 0.90 x weekly max(52,high)", "Within 10% of the 52W high — base is forming near the top, not the bottom."),
            ("ema(20) > ema(50) > ema(200)", "Base forming in an uptrend. A base in a downtrend is a falling knife."),
            ("sma(volume,10) < 0.75 x sma(volume,50)", "10-day avg volume is less than 75% of 50-day avg. Volume contracted 25%+. Classic VCP squeeze."),
            ("volume x close > 25 Crore", "Minimum liquidity."),
        ],
    },
}

# ── VERDICT COLORS ────────────────────────────────────────────────────────────
VERDICT_COLORS = {
    "ELITE SETUP":  "#00c853",
    "STRONG SETUP": "#ff9100",
    "TRADABLE":     "#2979ff",
    "AVOID":        "#f44336",
}
PATTERN_COLORS = {
    "VCP":                   "#00c853",
    "BREAKOUT":              "#00c853",
    "BULL FLAG":             "#ff9100",
    "FLAT BASE":             "#ff9100",
    "EMA20 PULLBACK":        "#2979ff",
    "MOMENTUM CONTINUATION": "#90caf9",
    "NO CLEAR PATTERN":      "#f44336",
    "INSUFFICIENT DATA":     "#f44336",
}

# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main():
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">'
        '<div style="width:42px;height:42px;background:linear-gradient(135deg,#1565c0,#0d47a1);'
        'border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;">📈</div>'
        '<div>'
        '<div style="font-size:18px;font-weight:800;color:#e0e8ff;">NSE ELITE SWING ADVISOR</div>'
        '<div style="font-size:11px;color:#5c7099;">Minervini x O\'Neil x Weinstein x Qullamaggie · v4</div>'
        '</div></div>',
        unsafe_allow_html=True
    )

    # Market regime
    with st.spinner("Checking market regime..."):
        nifty_df  = fetch_index("^NSEI")
        bnifty_df = fetch_index("^NSEBANK")
    regime_rows, regime_pen = market_regime(nifty_df, bnifty_df)

    regime_inner = ""
    for name, msg, color, pen in regime_rows:
        dot = "🟢" if color == "#00c853" else "🟠" if color == "#ff9100" else "🔴"
        pen_txt = " (-" + str(pen) + " pts)" if pen > 0 else ""
        regime_inner += (
            '<div style="margin-bottom:4px;">'
            '<span style="color:#5c7099;font-size:10px;font-weight:600;">' + name + ': </span>'
            '<span style="color:' + color + ';font-weight:700;font-size:13px;">' + dot + ' ' + msg + '</span>'
            '<span style="color:#5c7099;font-size:11px;">' + pen_txt + '</span>'
            '</div>'
        )

    if regime_pen >= 20:
        regime_inner += (
            '<div style="color:#f44336;font-size:13px;font-weight:700;margin-top:8px;">'
            'CAPITAL PRESERVATION MODE — Only setups scoring 85+ qualify. Reduce position sizes 50%.'
            '</div>'
        )

    border_col = "#00c853" if regime_pen == 0 else "#f44336"
    st.markdown(
        '<div style="background:#0d1b2e;border:2px solid ' + border_col + '40;border-radius:10px;padding:14px 18px;margin-bottom:18px;">'
        '<div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">MARKET REGIME — LIVE</div>'
        + regime_inner +
        '</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Stock Scorer", "🔍 Pattern Guide", "📡 Chartink Scanners", "📖 System Rules"])

    # ── TAB 1: SCORER ─────────────────────────────────────────────────────────
    with tab1:
        col_l, col_r = st.columns([1, 1.9], gap="large")

        with col_l:
            st.markdown("### 🔍 Stock Analysis")
            symbol  = st.text_input("NSE Symbol", placeholder="TCS, DATAPATTNS, AKUMS...").upper().strip()
            pick    = st.selectbox("Or pick from list", [""] + POPULAR)
            if pick:
                symbol = pick
            capital = st.number_input("Capital (Rs.)", min_value=100000, max_value=10000000, value=300000, step=50000, format="%d")
            risk_pct= st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25)
            go      = st.button("⚡ Analyze Stock", use_container_width=True)

        with col_r:
            if not go:
                st.markdown(
                    '<div style="background:#0d1b2e;border:1px solid #2979ff30;border-radius:10px;padding:30px;text-align:center;margin-top:20px;">'
                    '<div style="font-size:36px;margin-bottom:12px;">🔍</div>'
                    '<div style="color:#e0e8ff;font-size:15px;font-weight:600;margin-bottom:8px;">Enter a stock symbol and click Analyze</div>'
                    '<div style="color:#5c7099;font-size:13px;line-height:1.8;">'
                    'Detects: VCP · Bull Flag · Flat Base · Second Leg<br>'
                    'Scores: EMA · MACD · RSI · Volume · Returns · RS vs Nifty<br>'
                    'Outputs: Smart SL · 3 Targets · Entry Types · Position Size'
                    '</div></div>',
                    unsafe_allow_html=True
                )

            elif go and symbol:
                with st.spinner("Fetching " + symbol + "..."):
                    df, ticker = fetch_stock(symbol)

                if df is None:
                    st.error("Could not fetch " + symbol + ". Check the symbol and try again.")
                else:
                    df = enrich(df)

                    # Liquidity gate
                    turnover, liq_ok = liquidity_gate(df)
                    if not liq_ok:
                        t_str = str(round(turnover / 1e7, 1))
                        st.markdown(
                            '<div style="background:#1a0a0a;border:2px solid #f44336;border-radius:10px;padding:20px;text-align:center;">'
                            '<div style="font-size:28px;">🚫</div>'
                            '<div style="color:#f44336;font-size:18px;font-weight:800;margin-top:8px;">LIQUIDITY FAIL — NOT SCORED</div>'
                            '<div style="color:#7b8fba;font-size:13px;margin-top:8px;">'
                            'Daily turnover: Rs.' + t_str + ' Cr — Minimum required: Rs.25 Cr'
                            '</div></div>',
                            unsafe_allow_html=True
                        )
                        st.stop()

                    # Compute everything
                    r6, r12, rs         = compute_returns(df, nifty_df)
                    pattern, pconf, pexpl = detect_pattern(df)
                    is_2leg, leg2_msg, _ = second_leg(df)
                    final, raw, sp, verdict, sc, flags, today_mv, pct_h = score_stock(
                        df, r6, r12, rs, regime_pen, pattern, pconf
                    )
                    price     = safe_float(df["Close"].iloc[-1])
                    sl, sl_pct, sl_lbl, sl_ok = smart_sl(df, price)
                    ei        = entry_logic(df, price, pattern)
                    t1, t2, t3, rr = compute_targets(price, sl)

                    # Pre-compute all display values — plain strings, no ternaries inside HTML
                    l      = df.iloc[-1]
                    prev_p = safe_float(df["Close"].iloc[-2])
                    day_chg= (price - prev_p) / prev_p * 100 if prev_p > 0 else 0
                    h52    = safe_float(l["H52"]) if not np.isnan(l["H52"]) else price
                    e10    = safe_float(l["E10"])
                    e20    = safe_float(l["E20"])
                    e50    = safe_float(l["E50"])
                    e200   = safe_float(l["E200"])
                    vr_    = safe_float(l["VR"])  if not np.isnan(l["VR"])  else 0.0
                    rsi_   = safe_float(l["RSI"]) if not np.isnan(l["RSI"]) else 0.0
                    mac_   = safe_float(l["MACD"])if not np.isnan(l["MACD"])else 0.0

                    vc     = VERDICT_COLORS.get(verdict, "#7b8fba")
                    pc     = PATTERN_COLORS.get(pattern, "#7b8fba")
                    qty    = int((capital * risk_pct / 100) / (price * sl_pct / 100)) if sl_ok and sl_pct else 0

                    # All string variables — no logic inside HTML strings
                    date_str  = df.index[-1].strftime("%d %b %Y")
                    to_str    = str(round(turnover / 1e7, 1))
                    price_str = "{:,.2f}".format(price)
                    chg_str   = str(round(abs(day_chg), 2))
                    chg_col   = "#00c853" if day_chg >= 0 else "#f44336"
                    chg_arrow = "UP" if day_chg >= 0 else "DOWN"
                    spike_warning = ""
                    if abs(today_mv) >= 5:
                        spike_warning = (
                            '<div style="color:#f44336;font-size:11px;font-weight:600;">'
                            'BIG MOVE TODAY +' + str(round(today_mv,1)) + '% — spike penalty applied</div>'
                        )

                    # Stock header
                    st.markdown(
                        '<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:12px;">'
                        '<div style="display:flex;justify-content:space-between;">'
                        '<div>'
                        '<div style="color:#90caf9;font-size:11px;font-weight:600;letter-spacing:1px;">'
                        + ticker + ' · ' + date_str + ' · Turnover Rs.' + to_str + 'Cr/day'
                        '</div>'
                        '<div style="color:#e0e8ff;font-size:26px;font-weight:900;margin-top:4px;">Rs.' + price_str + '</div>'
                        '</div>'
                        '<div style="text-align:right;">'
                        '<div style="color:' + chg_col + ';font-size:16px;font-weight:700;">' + chg_arrow + ' ' + chg_str + '%</div>'
                        + spike_warning +
                        '</div></div></div>',
                        unsafe_allow_html=True
                    )

                    # Tile values — all pre-computed
                    h52_val  = "Rs." + "{:,.1f}".format(h52)
                    h52_sub  = "ABOVE 52W HIGH" if pct_h <= 0 else str(round(pct_h,1)) + "% below 52W high"
                    h52_col  = "#00c853" if pct_h <= 3 else "#ff9100" if pct_h <= 10 else "#f44336"

                    vr_val   = str(round(vr_,1)) + "x avg"
                    vr_col   = "#00c853" if vr_ >= 1.5 else "#ff9100" if vr_ >= 1 else "#f44336"

                    rsi_val  = str(round(rsi_))
                    rsi_col  = "#00c853" if 50 <= rsi_ <= 65 else "#ff9100" if rsi_ < 80 else "#f44336"

                    mac_dir  = "UP " if mac_ > 0 else "DOWN "
                    mac_val  = mac_dir + str(round(abs(mac_),2))
                    mac_col  = "#00c853" if mac_ > 0 and safe_float(l["HIST"]) > 0 else "#ff9100" if mac_ > 0 else "#f44336"

                    e20_col  = "#00c853" if price > e20 else "#f44336"
                    e20_sub  = "Price above EMA20" if price > e20 else "Price below EMA20"

                    e50_col  = "#00c853" if e20 > e50 else "#f44336"
                    e50_sub  = "EMA20 > EMA50" if e20 > e50 else "EMA20 < EMA50"

                    e200_col = "#00c853" if e50 > e200 else "#f44336"
                    e200_sub = "EMA50 > EMA200" if e50 > e200 else "EMA50 < EMA200"

                    if r6 is None:   r6_val = "No data"
                    elif r6 >= 0:    r6_val = "+" + str(round(r6,1)) + "%"
                    else:            r6_val = str(round(r6,1)) + "%"
                    r6_col   = "#00c853" if r6 and r6 >= 20 else "#ff9100" if r6 and r6 >= 0 else "#f44336"

                    # Render tiles using the safe html_tile function
                    c1,c2,c3,c4 = st.columns(4)
                    with c1: st.markdown(html_tile("52W HIGH",  h52_val, h52_col, h52_sub),  unsafe_allow_html=True)
                    with c2: st.markdown(html_tile("VOLUME",    vr_val,  vr_col),             unsafe_allow_html=True)
                    with c3: st.markdown(html_tile("RSI (14)",  rsi_val, rsi_col),            unsafe_allow_html=True)
                    with c4: st.markdown(html_tile("MACD",      mac_val, mac_col),            unsafe_allow_html=True)

                    c5,c6,c7,c8 = st.columns(4)
                    with c5: st.markdown(html_tile("EMA 20",  "Rs."+"{:,.1f}".format(e20),  e20_col,  e20_sub),  unsafe_allow_html=True)
                    with c6: st.markdown(html_tile("EMA 50",  "Rs."+"{:,.1f}".format(e50),  e50_col,  e50_sub),  unsafe_allow_html=True)
                    with c7: st.markdown(html_tile("EMA 200", "Rs."+"{:,.1f}".format(e200), e200_col, e200_sub), unsafe_allow_html=True)
                    with c8: st.markdown(html_tile("6M RETURN", r6_val, r6_col),             unsafe_allow_html=True)

                    st.markdown("---")

                    # Pattern card
                    st.markdown(
                        '<div style="background:#0d1b2e;border:1px solid ' + pc + '40;border-left:4px solid ' + pc + ';border-radius:10px;padding:14px;margin-bottom:12px;">'
                        + html_badge("PATTERN: " + pattern, pc)
                        + ' <span style="color:#5c7099;font-size:11px;margin-left:8px;">Confidence: ' + str(pconf) + '%</span>'
                        '<div style="color:#7b8fba;font-size:13px;line-height:1.7;margin-top:8px;">' + pexpl + '</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )

                    # Second leg
                    if is_2leg:
                        st.markdown(
                            '<div style="background:#0d1b2e;border:1px solid #00c85340;border-left:4px solid #00c853;border-radius:10px;padding:14px;margin-bottom:12px;">'
                            + html_badge("SECOND LEG DETECTED — HIGHEST CONVICTION", "#00c853")
                            + '<div style="color:#7b8fba;font-size:13px;line-height:1.7;margin-top:8px;">' + leg2_msg + '</div>'
                            '</div>',
                            unsafe_allow_html=True
                        )

                    # Big score card
                    raw_str = str(raw)
                    sp_str  = " · Spike: " + str(sp) if sp < 0 else ""
                    rp_str  = " · Regime: -" + str(regime_pen) if regime_pen > 0 else ""
                    subtitle= "OUT OF 100 · Raw: " + raw_str + sp_str + rp_str

                    if verdict == "AVOID":
                        action_line = '<div style="color:#f44336;font-size:13px;font-weight:700;margin-top:12px;">NO TRADE IS THE BEST TRADE</div>'
                    elif final >= 80:
                        action_line = '<div style="color:' + vc + ';font-size:13px;font-weight:700;margin-top:12px;">BUY / STRONG SETUP</div>'
                    else:
                        action_line = '<div style="color:' + vc + ';font-size:13px;font-weight:700;margin-top:12px;">TRADABLE — HALF SIZE ONLY</div>'

                    st.markdown(
                        '<div style="background:#060e1c;border:2px solid ' + vc + '50;border-radius:14px;padding:22px;text-align:center;margin-bottom:14px;">'
                        '<div style="font-size:68px;font-weight:900;color:' + vc + ';line-height:1;">' + str(final) + '</div>'
                        '<div style="color:#5c7099;font-size:11px;margin-bottom:12px;">' + subtitle + '</div>'
                        '<div style="display:inline-block;background:' + vc + '20;color:' + vc + ';border:1px solid ' + vc + '50;'
                        'border-radius:8px;padding:6px 24px;font-size:15px;font-weight:800;letter-spacing:1px;">' + verdict + '</div>'
                        + action_line +
                        '</div>',
                        unsafe_allow_html=True
                    )

                    if verdict != "AVOID":
                        # Entry card
                        et    = ei["type"]
                        et_col = "#00c853" if "BREAKOUT" in et else "#ff9100" if "FLAG" in et or "WAIT" in et else "#2979ff"
                        st.markdown(
                            '<div style="background:#0d1b2e;border:1px solid ' + et_col + '40;border-left:4px solid ' + et_col + ';border-radius:10px;padding:16px;margin-bottom:12px;">'
                            + html_badge("ENTRY: " + et, et_col)
                            + '<div style="color:#7b8fba;font-size:13px;line-height:1.7;margin-top:8px;">' + ei["note"] + '</div>'
                            '</div>',
                            unsafe_allow_html=True
                        )

                        if sl_ok and t1 and t2 and t3:
                            # All level strings pre-computed
                            agg_str = "Rs." + "{:,.1f}".format(ei["agg"]) if ei["agg"] > 0 else "Wait"
                            con_str = "Rs." + "{:,.1f}".format(ei["con"]) if ei["con"] > 0 else "Wait"
                            ret_str = "Rs." + "{:,.1f}".format(ei["ret"]) if ei["ret"] > 0 else "Wait"
                            sl_str  = "Rs." + "{:,.1f}".format(sl)
                            sl_sub  = sl_lbl + " — place GTT immediately"
                            sl_pct_str = str(round(sl_pct,1)) + "%"
                            t1_str  = "Rs." + "{:,.1f}".format(t1)
                            t2_str  = "Rs." + "{:,.1f}".format(t2)
                            t3_str  = "Rs." + "{:,.1f}".format(t3)
                            t1_gain = "+" + str(round((t1-price)/price*100,1)) + "% · 1.5R — Book 30%"
                            t2_gain = "+" + str(round((t2-price)/price*100,1)) + "% · 3R  — Book 30%"
                            t3_gain = "+" + str(round((t3-price)/price*100,1)) + "% · 5R  — Trail 40%"
                            rr_col  = "#00c853" if rr >= 3 else "#f44336"
                            rr_str  = "1 : " + str(round(rr,1)) + (" (minimum met)" if rr >= 3 else " (BELOW 3:1 MINIMUM — SKIP)")
                            qty_str = str(qty) + " shares"
                            pos_str = "Rs." + "{:,.0f}".format(qty * price)
                            risk_str= "Rs." + "{:,.0f}".format(capital * risk_pct / 100)
                            e10_str = "Rs." + "{:,.1f}".format(e10)

                            levels_html = (
                                '<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:12px;">'
                                '<div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">TRADE PLAN</div>'
                                '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px;">'
                                + html_level_box("AGGRESSIVE ENTRY", agg_str, "#2979ff", "Enter now")
                                + html_level_box("CONSERVATIVE", con_str, "#90caf9", "Wait for confirm")
                                + html_level_box("STOP LOSS " + sl_pct_str, sl_str, "#f44336", sl_sub)
                                + html_level_box("RETEST ENTRY", ret_str, "#7b8fba", "If price dips back")
                                + '</div>'
                                '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">'
                                + html_level_box("TARGET 1", t1_str, "#ff9100", t1_gain)
                                + html_level_box("TARGET 2", t2_str, "#00c853", t2_gain)
                                + html_level_box("TARGET 3", t3_str, "#00c853", t3_gain)
                                + '</div>'
                                '<div style="background:#060e1c;border:1px solid ' + rr_col + '30;border-radius:8px;padding:12px;text-align:center;margin-bottom:8px;">'
                                '<span style="color:#5c7099;">RISK : REWARD = </span>'
                                '<span style="color:' + rr_col + ';font-size:16px;font-weight:800;">' + rr_str + '</span>'
                                '</div>'
                                '<div style="background:#060e1c;border:1px solid #2979ff20;border-radius:8px;padding:12px;">'
                                '<div style="color:#5c7099;font-size:10px;font-weight:600;margin-bottom:5px;">POSITION SIZE</div>'
                                '<div style="color:#90caf9;font-size:14px;font-weight:700;">' + qty_str + ' · ' + pos_str + '</div>'
                                '<div style="color:#5c7099;font-size:11px;margin-top:3px;">Max risk = ' + risk_str + '</div>'
                                '</div></div>'
                            )
                            st.markdown(levels_html, unsafe_allow_html=True)

                            # Exit plan
                            exit_html = (
                                '<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;margin-bottom:12px;">'
                                '<div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">EXIT PLAN</div>'
                                '<div style="color:#7b8fba;font-size:12px;line-height:2.1;">'
                                'After fill: Place GTT stop at ' + sl_str + ' immediately — no exceptions.<br>'
                                'At T1 (' + t1_str + '): Book 30%. Move stop to your entry price (breakeven). Trade is now risk-free.<br>'
                                'At T2 (' + t2_str + '): Book 30%. Raise trailing stop to T1 level.<br>'
                                'Remaining 40%: Trail using daily close below EMA10 (' + e10_str + ').<br>'
                                'Hard stop: If price closes below ' + sl_str + ' — exit full position. No debate.<br>'
                                'Time stop: Exit if no movement in 15 trading days. Redeploy capital.'
                                '</div></div>'
                            )
                            st.markdown(exit_html, unsafe_allow_html=True)

                    # Score breakdown
                    bars = (
                        html_score_bar("EMA Stack (20>50>200)", sc.get("ema",0),  20) +
                        html_score_bar("52W High Position",     sc.get("h52",0),  15) +
                        html_score_bar("Volume",                sc.get("vol",0),  15) +
                        html_score_bar("MACD",                  sc.get("macd",0), 15) +
                        html_score_bar("RSI",                   sc.get("rsi",0),  10) +
                        html_score_bar("6M Return",             sc.get("r6",0),   10) +
                        html_score_bar("12M Return",            sc.get("r12",0),  10) +
                        html_score_bar("RS vs Nifty",           sc.get("rs",0),   10) +
                        html_score_bar("Pattern Bonus",         sc.get("pat",0),   5) +
                        html_score_bar("Liquidity",             sc.get("liq",0),   5)
                    )
                    st.markdown(
                        '<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;margin-bottom:12px;">'
                        '<div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">SCORE BREAKDOWN</div>'
                        + bars + '</div>',
                        unsafe_allow_html=True
                    )

                    # Signal flags
                    flags_inner = "".join([html_flag(t, m) for t, m in flags])
                    st.markdown(
                        '<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;">'
                        '<div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">SIGNAL FLAGS</div>'
                        + flags_inner + '</div>',
                        unsafe_allow_html=True
                    )

    # ── TAB 2: PATTERN GUIDE ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### 🔍 Pattern Detection Guide")
        patterns_guide = [
            ("VCP — Volatility Contraction Pattern", "#00c853", "Minervini's primary setup",
             "A series of smaller and smaller price corrections with declining volume. The stock is coiling like a spring before an explosive breakout.",
             ["Big Stage 2 move up first", "Correction 1: large (15-20%) on volume", "Correction 2: smaller (10%) on less volume", "Correction 3: tiny (3-5%) on very low volume — the coil point", "BREAKOUT on 2x+ volume"],
             "Enter on breakout above the tight point. Stop below the last contraction low. Volume must be 2x+ on breakout day."),
            ("Bull Flag", "#ff9100", "Qullamaggie's favourite setup",
             "A strong upward move (the pole) followed by a tight sideways/slightly downward consolidation (the flag) with declining volume.",
             ["Stock moves 15-30%+ in 2-3 weeks (the pole)", "Tight consolidation 5-10 days (the flag)", "Volume drops during flag", "Breakout above flag on high volume"],
             "Enter on breakout above flag high on volume. Stop below flag low. Target = flag pole length added to breakout point."),
            ("Flat Base", "#2979ff", "O'Neil CANSLIM pattern",
             "Stock consolidates in a tight 5-10% range for 3-6 weeks near highs. One of the most reliable bases.",
             ["Near 52W highs", "Range less than 8% for 20 days", "Volume declining", "EMAs bullish below price"],
             "Enter on breakout above flat base high on 1.5x+ volume. Stop below bottom of base."),
            ("EMA20 Pullback", "#00bcd4", "Lowest-risk continuation entry",
             "In a confirmed Stage 2 uptrend, price pulls back to EMA20 and bounces. Minimal risk, strong R:R.",
             ["Stock in Stage 2 uptrend (all EMAs bullish)", "Price touches or comes within 2% of EMA20", "Volume dries up during pullback", "One green candle forms at EMA20 — entry signal"],
             "Enter on first green candle at EMA20. Stop 1% below EMA20. Tightest possible stop in a trending stock."),
            ("Second Leg", "#00c853", "Highest conviction trade",
             "After a big first move and tight base, the stock launches into a second leg up. Often larger than the first move.",
             ["30-80%+ first move", "Pulled back only 15-30% (tight = institutional)", "Volume dried up during base", "Breaking out of base again", "MACD stayed positive throughout"],
             "Enter at the breakout from the base between legs. Stop below base low. Highest success rate because institutional commitment is proven."),
        ]
        for name, color, sub, desc, signals, entry in patterns_guide:
            with st.expander("**" + name + "** — " + sub):
                st.markdown(desc)
                for s in signals:
                    st.markdown("- " + s)
                st.markdown("**Entry and Stop:** " + entry)

    # ── TAB 3: CHARTINK SCANNERS ──────────────────────────────────────────────
    with tab3:
        st.markdown("### 📡 Chartink Scanners — Full Explanation")
        st.caption("Go to chartink.com → Screens → Create New Screen → paste code → Generate → run after 4 PM IST")

        for name, data in SCANNERS.items():
            col = data["color"]
            with st.expander("**" + name + "** — " + data["priority"]):
                st.markdown("**What it finds:** " + data["what"])
                st.markdown("**Why it works:** " + data["why"])
                st.markdown("**Action on results:** " + data["action"])
                st.markdown("**Each condition explained:**")
                for cond, expl in data["conditions"]:
                    inner = (
                        '<div style="background:#060e1c;border:1px solid #1a2744;border-radius:6px;padding:10px;margin-bottom:6px;">'
                        '<div style="color:' + col + ';font-family:monospace;font-size:11px;margin-bottom:4px;">' + cond + '</div>'
                        '<div style="color:#7b8fba;font-size:12px;">' + expl + '</div>'
                        '</div>'
                    )
                    st.markdown(inner, unsafe_allow_html=True)
                st.markdown("**Chartink Code:**")
                st.code(data["code"], language="text")

    # ── TAB 4: SYSTEM RULES ───────────────────────────────────────────────────
    with tab4:
        st.markdown("### 📖 Elite Swing Trading Rules")
        rules = [
            ("The #1 Rule — Capital Preservation", [
                "No trade is the best trade when conditions are not right.",
                "Never force a trade just to be in the market.",
                "One bad trade can wipe out 10 good trades.",
            ]),
            ("Trade Quality Standards", [
                "Only trade setups scoring 80+ (Strong Setup or Elite).",
                "Minimum 3:1 reward-to-risk ratio — no exceptions.",
                "Maximum 6% stop loss — wider than 6% means skip the trade.",
                "If you are not sure, the answer is NO.",
            ]),
            ("Position Sizing Rules", [
                "Never risk more than 1% of capital on a single trade.",
                "Maximum 25% of capital in any single stock.",
                "Never more than 5 simultaneous open positions.",
                "Maximum 5% total portfolio risk at any time.",
                "On high-VIX or expiry days: 0.5% risk per trade (half size).",
            ]),
            ("Hard Rules — Never Break", [
                "Never average down. If stock falls to stop, exit. Period.",
                "Never widen stop losses. Set it and respect it.",
                "Never hold through earnings on a swing trade.",
                "No trades in first 15 minutes (9:15–9:30 AM IST).",
                "No new entries after 3:15 PM IST.",
                "No revenge trades after a loss.",
                "No trades on broadly red market days.",
            ]),
            ("Market Filter — Before Any Trade", [
                "Check Nifty: above 50 EMA? Above 200 EMA?",
                "Check Bank Nifty: confirming or diverging?",
                "Check VIX: below 15 = normal, 15–20 = caution, above 20 = no breakout entries.",
                "If 2+ of these are negative: reduce size or skip entirely.",
            ]),
            ("Daily Routine", [
                "Pre-market 9 AM: Check Nifty/Bank Nifty direction. Set GTT orders.",
                "9:15–9:30 AM: Watch only. No trades.",
                "9:30–11 AM: Primary execution window.",
                "11 AM–2:30 PM: Low conviction period. Avoid new entries.",
                "After 4 PM: Run Chartink scanners. Build next day watchlist. Update journal.",
            ]),
        ]
        for title, points in rules:
            with st.expander("**" + title + "**"):
                for pt in points:
                    st.markdown("- " + pt)

    st.markdown(
        '<div style="margin-top:20px;padding:10px 14px;background:#0d1b2e;border:1px solid #1a2744;'
        'border-radius:8px;color:#3d5070;font-size:10px;line-height:1.6;">'
        'Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day delay. '
        'Always verify before trading.'
        '</div>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
