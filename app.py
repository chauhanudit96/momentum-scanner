"""
NSE Elite Swing Terminal v8
CRITICAL FIX: Plotly Candlestick does NOT accept 8-digit hex colors.
All colors use rgba() format. No hex+alpha anywhere.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="NSE Swing Terminal", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background:#0d1117; color:#c9d1d9; }
.main .block-container { padding-top:0.5rem; max-width:1400px; }
.stTabs [data-baseweb="tab"] { color:#8b949e !important; font-weight:600 !important; }
.stTabs [aria-selected="true"] { color:#58a6ff !important; border-bottom-color:#58a6ff !important; }
.stButton button {
    background: linear-gradient(135deg,#1f6feb,#388bfd) !important;
    color: #fff !important; font-weight: 700 !important;
    border: none !important; border-radius: 6px !important;
}
.stTextInput input { background:#161b22 !important; border:1px solid #30363d !important; color:#c9d1d9 !important; }
.stNumberInput input { background:#161b22 !important; border:1px solid #30363d !important; color:#c9d1d9 !important; }
div[data-testid="stMetricValue"] { font-size:16px !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
POPULAR = sorted([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","ITC","SBIN","BAJFINANCE",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "WIPRO","SUNPHARMA","HCLTECH","NTPC","ONGC","TATAMOTORS","JSWSTEEL",
    "ADANIENT","ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP",
    "EICHERMOT","HEROMOTOCO","M&M","BRITANNIA","DABUR","MARICO","PIDILITIND",
    "HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL","DATAPATTNS","KAYNES",
    "DIXON","COALINDIA","RVNL","DMART","IRCTC","IRFC","COCHINSHIP","GRSE",
    "TATAPOWER","POLYCAB","AKUMS","MARKSANS","SURYODAY","DEEPAKNTR",
    "NESTLEIND","BERGEPAINT","HINDUNILVR","ULTRACEMCO","BAJAJFINSV",
    "TATASTEEL","HINDALCO","TATACHEM","VOLTAS","WHIRLPOOL","CROMPTON",
    "CUMMINSIND","THERMAX","SCHAEFFLER","TIMKEN","GRINDWELL","ASTRAL",
])

SECTORS = {
    "Defense":   ["BEL","HAL","BHEL","COCHINSHIP","GRSE","DATAPATTNS"],
    "Pharma":    ["SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AKUMS","MARKSANS"],
    "Banking":   ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK"],
    "Finance":   ["BAJFINANCE","BAJAJFINSV","SURYODAY"],
    "IT":        ["TCS","INFY","HCLTECH","WIPRO"],
    "Auto":      ["MARUTI","TATAMOTORS","EICHERMOT","HEROMOTOCO","M&M"],
    "CapGoods":  ["SIEMENS","ABB","HAVELLS","POLYCAB","KAYNES","CUMMINSIND"],
    "FMCG":      ["HINDUNILVR","ITC","BRITANNIA","DABUR","MARICO"],
    "Metals":    ["JSWSTEEL","TATASTEEL","COALINDIA","HINDALCO"],
}

SETUPS = {
    "VCP": {
        "color":"#3fb950","icon":"🌀","name":"Volatility Contraction Pattern",
        "tagline":"Stock coiling near highs, volume shrinking — explosive breakout building",
        "enter":"Volume breaks above the tight range on 2x+ average volume",
        "avoid":"Volume still contracting OR price breaks below the base low",
        "sl":"ema10","min":72,"risk":"LOW","hold":"5–15 days",
        "desc":"A VCP forms when a stock makes progressively smaller pullbacks near its highs with declining volume. Supply is exhausted. Institutions quietly accumulating. The tighter the coil, the bigger the breakout. Minervini's primary setup.",
        "weights":{"Volume Contraction":25,"Price Tightness":20,"52W Proximity":20,"EMA Stack":15,"RSI":10,"MACD":10},
    },
    "BREAKOUT": {
        "color":"#58a6ff","icon":"🚀","name":"52-Week High Breakout",
        "tagline":"Breaking above 52W high on institutional volume — no overhead resistance",
        "enter":"Price closes above 52W high with 1.5x+ volume — enter next day open or intraday",
        "avoid":"Breakout on below-average volume, first 15 min, or VIX above 20",
        "sl":"ema20","min":75,"risk":"MEDIUM","hold":"5–20 days",
        "desc":"Clearing the 52-week high means every seller from the past year is at breakeven or profit — zero overhead resistance. When institutional volume confirms, this is the single highest-probability momentum signal in markets.",
        "weights":{"Breakout Volume":30,"EMA Stack":20,"52W Proximity":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "BULL_FLAG": {
        "color":"#e3b341","icon":"🏴","name":"Bull Flag",
        "tagline":"Strong pole + tight flag — second surge building with declining volume",
        "enter":"Break above flag high on expanding volume — buy the breakout candle only",
        "avoid":"Buying inside the flag before breakout, or flag range is wider than 8%",
        "sl":"flag_low","min":70,"risk":"LOW-MEDIUM","hold":"3–10 days",
        "desc":"After a fast 15-30% pole move, stock consolidates tightly 5-10 days with declining volume. Volume drops during flag = institutions holding, not selling. When volume expands and price breaks the flag, next leg begins. Qullamaggie's favourite setup.",
        "weights":{"Pole Strength":25,"Flag Tightness":25,"Volume Pattern":20,"EMA Stack":15,"RSI":10,"MACD":5},
    },
    "EMA_PULLBACK": {
        "color":"#79c0ff","icon":"↩️","name":"EMA Pullback",
        "tagline":"Dip to EMA20 in uptrend — lowest risk, best risk:reward entry",
        "enter":"First green candle closing above EMA20 after a low-volume dip",
        "avoid":"High volume on the dip (means distribution), or EMA20 is flat or declining",
        "sl":"ema20","min":68,"risk":"LOWEST","hold":"5–15 days",
        "desc":"In Stage 2 uptrends, stocks pull back to EMA20 between surges. Low volume on dip = no panic selling. Stop just below EMA20 = risk 2-3% for potential 15-25% move. Best risk-reward of all setup types.",
        "weights":{"EMA Stack":25,"Pullback Quality":25,"Volume on Dip":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "SECOND_LEG": {
        "color":"#bc8cff","icon":"⚡","name":"Second Leg",
        "tagline":"Big first move + tight base = second surge often even bigger",
        "enter":"Breakout above base high with 1.5x+ volume after a tight base forms",
        "avoid":"Base depth more than 35%, MACD went negative during base",
        "sl":"base_low","min":75,"risk":"MEDIUM","hold":"10–30 days",
        "desc":"After a 30-80% first move, stock builds a tight base. Tight base = institutions holding. When it breaks out again, institutional commitment is proven. HAL, BEL, DATAPATTNS ran 3-4 legs in 2023-24 without losing Stage 2.",
        "weights":{"First Leg":25,"Base Quality":25,"Breakout Volume":20,"RS vs Nifty":15,"MACD":10,"EMA Stack":5},
    },
    "FLAT_BASE": {
        "color":"#56d364","icon":"📊","name":"Flat Base",
        "tagline":"Tight sideways range near highs with drying volume — supply absorbed",
        "enter":"Breakout above flat base ceiling on 1.5x+ volume",
        "avoid":"Base range wider than 10%, less than 3 weeks old, volume not drying",
        "sl":"base_low","min":68,"risk":"LOW","hold":"5–20 days",
        "desc":"Stock moves sideways in less than 8% range for 3-6 weeks near highs with declining volume. O'Neil: the flatter and tighter the base, the bigger the breakout. Very reliable when quality criteria are met.",
        "weights":{"Base Tightness":30,"52W Proximity":20,"Volume Dry-up":20,"EMA Stack":15,"Duration":10,"MACD":5},
    },
    "NO_SETUP": {
        "color":"#484f58","icon":"⏳","name":"No Clear Setup",
        "tagline":"No tradeable pattern — patience is a position",
        "enter":"Wait for VCP, Breakout, Flag, Pullback, or Base to form",
        "avoid":"Trading now without a clear setup",
        "sl":None,"min":999,"risk":"N/A","hold":"N/A",
        "desc":"No tradeable swing pattern detected. The correct trade is no trade.",
        "weights":{},
    },
}

# ── SAFE HELPER ────────────────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        f = float(v)
        return d if (f != f) else f  # nan check without numpy
    except:
        return d

# ── INDICATORS ─────────────────────────────────────────────────────────────────
def enrich(df):
    df = df.copy()
    c  = df["Close"]
    for p in [10, 20, 50, 200]:
        df[f"E{p}"] = c.ewm(span=p, adjust=False).mean()
    df["V50"]  = df["Volume"].rolling(50).mean()
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=60).max()
    df["L52"]  = df["Low"].rolling(252,  min_periods=60).min()
    delta      = c.diff()
    gain       = delta.clip(lower=0).rolling(14).mean()
    loss       = (-delta.clip(upper=0)).rolling(14).mean()
    rs_ind     = gain / loss.replace(0, np.nan)
    df["RSI"]  = 100 - 100 / (1 + rs_ind)
    ema12      = c.ewm(span=12, adjust=False).mean()
    ema26      = c.ewm(span=26, adjust=False).mean()
    macd_line  = ema12 - ema26
    signal     = macd_line.ewm(span=9, adjust=False).mean()
    df["MACD"] = macd_line
    df["HIST"] = macd_line - signal
    df["ATR"]  = (df["High"] - df["Low"]).rolling(14).mean()
    return df

# ── DATA FETCH ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock(sym):
    for sfx in [".NS", ".BO"]:
        try:
            df = yf.Ticker(sym + sfx).history(period="1y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 50:
                return df.dropna(subset=["Close"]), sym + sfx
        except:
            continue
    return None, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_idx(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 30:
            return df.dropna(subset=["Close"])
    except:
        pass
    return None

# ── SETUP DETECTION ────────────────────────────────────────────────────────────
def detect_setup(df):
    if len(df) < 30:
        return "NO_SETUP", {}
    l     = df.iloc[-1]
    p     = safe(l["Close"])
    e10   = safe(l["E10"]); e20 = safe(l["E20"])
    e50   = safe(l["E50"]); e200 = safe(l["E200"])
    h52   = safe(l["H52"], p)
    vr    = safe(l["VR"], 1.0)
    mac   = safe(l["MACD"]); hist = safe(l["HIST"])
    atr   = safe(l["ATR"], p * 0.02)
    c20   = df["Close"].tail(20); c7 = df["Close"].tail(7)
    v10   = df["Volume"].tail(10).mean(); v50 = df["Volume"].tail(50).mean()
    ph    = (h52 - p) / h52 * 100 if h52 > 0 else 100
    r20   = (c20.max() - c20.min()) / c20.mean() * 100 if c20.mean() > 0 else 100
    r7    = (c7.max() - c7.min()) / c7.mean() * 100 if c7.mean() > 0 else 100
    vr10  = v10 / v50 if v50 > 0 else 1.0
    mv20  = (c20.iloc[-1] - c20.iloc[0]) / c20.iloc[0] * 100 if c20.iloc[0] > 0 else 0
    emas  = (p > e20) and (e20 > e50) and (e50 > e200)
    n20   = abs(p - e20) / p < 0.04 if p > 0 else False
    n50   = abs(p - e50) / p < 0.05 if p > 0 else False
    df6   = df.tail(126)
    lmx   = float(df6["High"].max()); lmn = float(df6["Low"].min())
    l1mv  = (lmx - lmn) / lmn * 100 if lmn > 0 else 0
    pidx  = df6["High"].idxmax()
    aftr  = df6.loc[pidx:]
    blow  = float(aftr["Low"].min()) if len(aftr) > 3 else p
    bdp   = (lmx - blow) / lmx * 100 if lmx > 0 else 100
    p2p   = (lmx - p) / lmx * 100 if lmx > 0 else 100
    sd = dict(
        p=p, e10=e10, e20=e20, e50=e50, e200=e200,
        h52=h52, ph=ph, vr=vr, rsi=safe(l["RSI"], 50),
        mac=mac, hist=hist, atr=atr,
        r20=r20, r7=r7, vr10=vr10, mv20=mv20,
        emas=emas, n20=n20, n50=n50,
        l1=l1mv, bdp=bdp, blow=blow, p2p=p2p,
        fh=float(c7.max()),
        bh=float(df["High"].tail(20).max()),
        bl=float(df["Low"].tail(20).min()),
    )
    if l1mv >= 30 and bdp <= 30 and p2p <= 10 and emas and vr >= 1.2: return "SECOND_LEG", sd
    if ph <= 1.5 and vr >= 1.5 and emas:                              return "BREAKOUT",   sd
    if ph <= 12 and r20 < 15 and vr10 < 0.80 and e20 > e50 > e200:  return "VCP",        sd
    if mv20 >= 12 and r7 < 6 and vr10 < 0.90 and p > e20:           return "BULL_FLAG",  sd
    if r20 < 10 and ph <= 18 and e20 > e50 > e200 and vr10 < 0.95:  return "FLAT_BASE",  sd
    if e50 > e200:
        if n20 and e20 > e50: return "EMA_PULLBACK", sd
        if n50 and p > e200:  return "EMA_PULLBACK", sd
    return "NO_SETUP", sd

# ── SCORING ────────────────────────────────────────────────────────────────────
def score_setup(sname, sd, r6, r12, rs):
    meta   = SETUPS.get(sname, SETUPS["NO_SETUP"])
    w      = meta["weights"]
    scores = {}
    flags  = []  # (type, label, value_str, explanation)

    p=sd["p"]; ph=sd["ph"]; vr=sd["vr"]; rsi_=sd["rsi"]
    mac=sd["mac"]; hist=sd["hist"]; r20=sd["r20"]; r7=sd["r7"]
    vr10=sd["vr10"]; mv20=sd["mv20"]; emas=sd["emas"]
    e20=sd["e20"]; e50=sd["e50"]; e200=sd["e200"]
    l1=sd["l1"]; bdp=sd["bdp"]; n20=sd["n20"]; n50=sd["n50"]

    def add(key, pts, typ, lbl, val, expl):
        scores[key] = pts
        flags.append((typ, lbl, val, expl))

    # EMA STACK
    if "EMA Stack" in w:
        mx = w["EMA Stack"]
        if p > e20 > e50 > e200:
            add("EMA Stack", mx, "bull", "EMA Stack", "Price > 20 > 50 > 200",
                "Full Stage 2 uptrend confirmed. Price above all EMAs in bullish order. The ONLY stage where momentum strategies work consistently.")
        elif e20 > e50 > e200:
            add("EMA Stack", int(mx*.65), "warn", "EMA Stack", "20>50>200, price below 20",
                "EMAs bullish but price dipped below EMA20. Wait for price to reclaim EMA20 before entering.")
        elif e20 > e50 or e50 > e200:
            add("EMA Stack", int(mx*.3), "warn", "EMA Stack", "Partial alignment",
                "Stage 2 still developing. Higher risk entry.")
        else:
            add("EMA Stack", 0, "bear", "EMA Stack", "Bearish order",
                "Stock in Stage 3 or Stage 4. Do not buy declining stocks.")

    # 52W PROXIMITY
    if "52W Proximity" in w:
        mx = w["52W Proximity"]; ph_s = str(round(ph, 1)) + "%"
        if ph <= 0:    add("52W Proximity", mx,           "bull", "52W High", "AT / ABOVE HIGH", "No overhead resistance. Every seller from the past year is at profit. Maximum momentum signal.")
        elif ph <= 2:  add("52W Proximity", int(mx*.90),  "bull", "52W High", ph_s+" below",     "Breakout imminent. Set GTT alert at 52W high level now.")
        elif ph <= 5:  add("52W Proximity", int(mx*.75),  "bull", "52W High", ph_s+" below",     "Near breakout zone. Good stage but needs to actually break before aggressive entry.")
        elif ph <= 10: add("52W Proximity", int(mx*.50),  "warn", "52W High", ph_s+" below",     "In base formation territory. Needs other signals to confirm direction.")
        elif ph <= 20: add("52W Proximity", int(mx*.25),  "warn", "52W High", ph_s+" below",     "Too far for ideal setup. Watch but don't act yet.")
        else:          add("52W Proximity", 0,             "bear", "52W High", ph_s+" below",     "More than 20% below the high. Not a momentum setup.")

    # VOLUME CONTRACTION
    if "Volume Contraction" in w:
        mx = w["Volume Contraction"]; pv = str(round(vr10 * 100)) + "% of avg"
        if vr10 < 0.40:   add("Volume Contraction", mx,          "bull", "Vol Contraction", pv, "Deep contraction — supply fully exhausted. The quieter before breakout, the bigger the move.")
        elif vr10 < 0.60: add("Volume Contraction", int(mx*.80), "bull", "Vol Contraction", pv, "Strong VCP signature. Institutions accumulating quietly.")
        elif vr10 < 0.75: add("Volume Contraction", int(mx*.55), "warn", "Vol Contraction", pv, "Moderate drying. Not deep enough for classic VCP yet.")
        else:              add("Volume Contraction", int(mx*.15), "bear", "Vol Contraction", pv, "Not contracting enough. Wait for more drying.")

    # PRICE / BASE TIGHTNESS
    for key in ["Price Tightness", "Base Tightness"]:
        if key in w:
            mx = w[key]; rs20 = str(round(r20, 1)) + "%"
            if r20 < 5:    add(key, mx,          "bull", key, rs20, "Exceptional tightness. Spring fully wound. Breakouts from <5% ranges are typically explosive.")
            elif r20 < 8:  add(key, int(mx*.80), "bull", key, rs20, "Solid base — institutions absorbing supply without much price movement.")
            elif r20 < 12: add(key, int(mx*.55), "warn", key, rs20, "Acceptable but not ideal. Tighter range would give higher confidence.")
            elif r20 < 18: add(key, int(mx*.25), "warn", key, rs20, "Wide base — lower conviction, higher risk of failed breakout.")
            else:           add(key, 0,           "bear", key, rs20, "Too wide to be called a base. Wait for consolidation.")

    # BREAKOUT VOLUME
    if "Breakout Volume" in w:
        mx = w["Breakout Volume"]; vrs = str(round(vr, 1)) + "x avg"
        if vr >= 4:    add("Breakout Volume", mx,          "bull", "Breakout Volume", vrs, "Institutional stampede. Very high probability of continuation.")
        elif vr >= 2.5:add("Breakout Volume", int(mx*.85), "bull", "Breakout Volume", vrs, "Strong institutional participation. Breakout has strong legs.")
        elif vr >= 1.5:add("Breakout Volume", int(mx*.65), "bull", "Breakout Volume", vrs, "Meets minimum. Watch next 2-3 sessions for follow-through.")
        elif vr >= 1:  add("Breakout Volume", int(mx*.30), "warn", "Breakout Volume", vrs, "Below average — could be a fake breakout. Caution.")
        else:          add("Breakout Volume", 0,            "bear", "Breakout Volume", vrs, "Very weak. High probability of failed breakout.")

    # POLE STRENGTH
    if "Pole Strength" in w:
        mx = w["Pole Strength"]; mvs = "+" + str(round(mv20, 1)) + "%"
        if mv20 >= 35:   add("Pole Strength", mx,          "bull", "Pole Strength", mvs, "Exceptional institutional move. Strong poles produce powerful second legs.")
        elif mv20 >= 22: add("Pole Strength", int(mx*.85), "bull", "Pole Strength", mvs, "Solid bull flag pole. Flag should resolve to the upside.")
        elif mv20 >= 12: add("Pole Strength", int(mx*.60), "warn", "Pole Strength", mvs, "Moderate. Follow-through may be proportionally smaller.")
        else:            add("Pole Strength", 0,            "bear", "Pole Strength", mvs, "Too weak for a reliable bull flag.")

    # FLAG TIGHTNESS
    if "Flag Tightness" in w:
        mx = w["Flag Tightness"]; r7s = str(round(r7, 1)) + "%"
        if r7 < 3:   add("Flag Tightness", mx,          "bull", "Flag Tightness", r7s, "Very tight flag — institutions not selling at all. High probability breakout.")
        elif r7 < 5: add("Flag Tightness", int(mx*.85), "bull", "Flag Tightness", r7s, "Good flag tightness. Orderly consolidation after the pole.")
        elif r7 < 8: add("Flag Tightness", int(mx*.55), "warn", "Flag Tightness", r7s, "A bit wide. Use a tighter stop.")
        else:        add("Flag Tightness", 0,            "bear", "Flag Tightness", r7s, "Too wide — not a proper flag.")

    # VOLUME PATTERN
    if "Volume Pattern" in w:
        mx = w["Volume Pattern"]
        if vr10 < 0.55 and vr >= 1.5:
            add("Volume Pattern", mx,          "bull", "Volume Pattern", "High pole / Low flag", "Textbook bull flag. Institutions bought on pole and sitting tight during flag.")
        elif vr10 < 0.75:
            add("Volume Pattern", int(mx*.65), "warn", "Volume Pattern", "Partially drying",     "Volume drying but not perfectly.")
        else:
            add("Volume Pattern", int(mx*.20), "bear", "Volume Pattern", "Volume elevated",      "Distribution may be occurring during flag.")

    # PULLBACK QUALITY
    if "Pullback Quality" in w:
        mx = w["Pullback Quality"]
        if n20 and vr10 < 0.70:
            add("Pullback Quality", mx,          "bull", "Pullback Quality", "At EMA20, vol drying", "Ideal Minervini entry. Trend intact, sellers gone quiet.")
        elif n20:
            add("Pullback Quality", int(mx*.70), "warn", "Pullback Quality", "At EMA20, vol OK",    "At EMA20 but volume not drying enough.")
        elif n50 and vr10 < 0.80:
            add("Pullback Quality", int(mx*.55), "warn", "Pullback Quality", "At EMA50, drying",    "Deeper pullback. Tradeable but stop will be wider.")
        else:
            add("Pullback Quality", int(mx*.20), "bear", "Pullback Quality", "Not at clean EMA",    "Not at a clean EMA level. No clear stop anchor.")

    # VOLUME ON DIP
    if "Volume on Dip" in w:
        mx = w["Volume on Dip"]; pvs = str(round(vr10 * 100)) + "% of avg"
        if vr10 < 0.50:   add("Volume on Dip", mx,          "bull", "Vol on Dip", pvs, "Nobody selling. Institutions holding all shares.")
        elif vr10 < 0.70: add("Volume on Dip", int(mx*.80), "bull", "Vol on Dip", pvs, "Selling is light and orderly — profit-taking, not distribution.")
        elif vr10 < 0.85: add("Volume on Dip", int(mx*.50), "warn", "Vol on Dip", pvs, "Volume somewhat elevated. Watch next session.")
        else:              add("Volume on Dip", int(mx*.15), "bear", "Vol on Dip", pvs, "High volume on dip — someone with significant holdings is selling.")

    # FIRST LEG
    if "First Leg" in w:
        mx = w["First Leg"]; l1s = "+" + str(int(l1)) + "%"
        if l1 >= 70:   add("First Leg", mx,          "bull", "First Leg Move", l1s, "Major institutional stock. Very powerful second leg expected.")
        elif l1 >= 45: add("First Leg", int(mx*.85), "bull", "First Leg Move", l1s, "Strong. Good foundation for second leg.")
        elif l1 >= 28: add("First Leg", int(mx*.60), "warn", "First Leg Move", l1s, "Moderate. Second leg potential proportionally smaller.")
        else:          add("First Leg", 0,            "bear", "First Leg Move", l1s, "Too small to qualify as a second-leg setup.")

    # BASE QUALITY
    if "Base Quality" in w:
        mx = w["Base Quality"]; bds = str(round(bdp, 1)) + "% deep"
        if bdp <= 12:   add("Base Quality", mx,          "bull", "Base Quality", bds, "Exceptional — institutions barely sold. Highest conviction.")
        elif bdp <= 20: add("Base Quality", int(mx*.80), "bull", "Base Quality", bds, "Good — bulk of position intact.")
        elif bdp <= 30: add("Base Quality", int(mx*.55), "warn", "Base Quality", bds, "Some distribution. Second leg may be smaller.")
        else:           add("Base Quality", 0,            "bear", "Base Quality", bds, "Too deep. Institutions took most profits.")

    # VOLUME DRY-UP
    if "Volume Dry-up" in w:
        mx = w["Volume Dry-up"]; pvs = str(round(vr10 * 100)) + "% of avg"
        if vr10 < 0.55:   add("Volume Dry-up", mx,          "bull", "Volume Dry-up", pvs, "Near-complete supply exhaustion. High quality flat base.")
        elif vr10 < 0.70: add("Volume Dry-up", int(mx*.75), "bull", "Volume Dry-up", pvs, "Volume declining nicely.")
        elif vr10 < 0.85: add("Volume Dry-up", int(mx*.45), "warn", "Volume Dry-up", pvs, "Partially drying.")
        else:              add("Volume Dry-up", int(mx*.10), "bear", "Volume Dry-up", pvs, "Volume not drying. Could be distribution.")

    # DURATION
    if "Duration" in w:
        mx = w["Duration"]
        if vr10 < 0.90: add("Duration", mx,          "bull", "Duration", "Adequate", "Base building long enough. 3+ weeks needed for reliability.")
        else:           add("Duration", int(mx*.40), "warn", "Duration", "May be short", "Base may not be mature enough. 3-6 weeks is ideal.")

    # RSI
    if "RSI" in w:
        mx = w["RSI"]; rs_s = str(round(rsi_))
        if 50 <= rsi_ <= 65:    add("RSI", mx,          "bull", "RSI", rs_s + " — Sweet Spot",    "RSI 50-65: trending but not overbought. Maximum room to run.")
        elif 45 <= rsi_ < 50:   add("RSI", int(mx*.65), "warn", "RSI", rs_s + " — Recovering",    "Below 50 but recovering. Needs to push above 50.")
        elif 65 < rsi_ <= 72:   add("RSI", int(mx*.55), "warn", "RSI", rs_s + " — Near OB",       "Approaching overbought. Ready for 1-3 day pullback soon.")
        elif 72 < rsi_ <= 80:   add("RSI", int(mx*.20), "warn", "RSI", rs_s + " — Overbought",    "Extended. Wait for RSI to pull back to 55-65.")
        elif rsi_ > 80:         add("RSI", 0,            "bear", "RSI", rs_s + " — Extreme OB",    "Very overbought. High probability of sharp pullback.")
        else:                   add("RSI", 0,            "bear", "RSI", rs_s + " — Downtrend",     "Below 45. Momentum strategies fail here.")

    # MACD
    if "MACD" in w:
        mx = w["MACD"]
        if mac > 0 and hist > 0:  add("MACD", mx,          "bull", "MACD", "Positive + Expanding", "Best MACD state. Momentum accelerating, not topping.")
        elif mac > 0:             add("MACD", int(mx*.65), "warn", "MACD", "Positive, slowing",    "Positive but decelerating. Still acceptable for entry.")
        elif -0.5 < mac <= 0:     add("MACD", int(mx*.30), "warn", "MACD", "Near zero",            "Watch for bullish crossover above zero.")
        else:                     add("MACD", 0,            "bear", "MACD", "Negative",             "Bearish momentum. Wait for MACD to recover above zero.")

    # RS VS NIFTY
    if "RS vs Nifty" in w:
        mx = w["RS vs Nifty"]
        if rs is None:
            scores["RS vs Nifty"] = int(mx * .50)
            flags.append(("warn", "RS vs Nifty", "No data", "Could not calculate relative strength."))
        elif rs >= 20:   add("RS vs Nifty", mx,          "bull", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Massive outperformer. FIIs overweight this stock.")
        elif rs >= 10:   add("RS vs Nifty", int(mx*.85), "bull", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Strong relative strength. Market leader.")
        elif rs >= 3:    add("RS vs Nifty", int(mx*.65), "warn", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Marginally outperforming. Not yet a clear leader.")
        elif rs >= 0:    add("RS vs Nifty", int(mx*.35), "warn", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Matching market. Leaders outperform by 10%+.")
        else:            add("RS vs Nifty", 0,            "bear", "RS vs Nifty", str(round(rs,1)) + "%",  "Underperforming. Will fall harder when market dips.")

    raw = sum(scores.values())
    return scores, flags, raw

# ── TRADE PLAN ─────────────────────────────────────────────────────────────────
def make_trade(sname, sd, raw, capital, risk_pct, regime_pen):
    meta  = SETUPS.get(sname, SETUPS["NO_SETUP"])
    final = max(0, raw - regime_pen)
    if sname == "NO_SETUP" or final < meta["min"]:
        return {"ok": False, "final": final, "verdict": "NO TRADE", "vc": "#484f58",
                "reason": "Score " + str(final) + " is below minimum " + str(meta["min"]) + " for " + meta["name"] + ". Wait for a better setup."}
    if final >= 90:   verdict, vc = "ELITE SETUP",    "#3fb950"
    elif final >= 78: verdict, vc = "STRONG SETUP",   "#58a6ff"
    elif final >= 65: verdict, vc = "TRADABLE",       "#e3b341"
    else:             return {"ok": False, "final": final, "verdict": "BELOW MINIMUM", "vc": "#f85149",
                              "reason": "Score " + str(final) + " below minimum " + str(meta["min"]) + ". Quality insufficient. Wait."}
    p=sd["p"]; e10=sd["e10"]; e20=sd["e20"]; e50=sd["e50"]
    h52=sd["h52"]; fh=sd["fh"]; bh=sd["bh"]; bl=sd["bl"]; blow=sd["blow"]; n20=sd["n20"]
    anchor = meta["sl"]
    if anchor == "ema10":    sl=e10*.99;   sl_l="1% below EMA10 (Rs." + str(round(e10,1)) + ")"
    elif anchor == "ema20":  sl=e20*.99;   sl_l="1% below EMA20 (Rs." + str(round(e20,1)) + ")"
    elif anchor == "flag_low": sl=bl*.995; sl_l="Below flag low (Rs." + str(round(bl,1)) + ")"
    elif anchor == "base_low": sl=blow*.99;sl_l="1% below base low (Rs." + str(round(blow,1)) + ")"
    else:                    sl=p*.95;     sl_l="5% mechanical"
    sl_pct = (p - sl) / p * 100 if p > 0 else 5
    if sl_pct > 6: sl=p*.94; sl_pct=6.0; sl_l="6% hard cap applied"
    if sname in ("BREAKOUT", "VCP"):
        ea=p; ec=round(h52*1.005,1); er=round(h52*.99,1)
        note = ("Buy above Rs." + str(round(h52,1)) + ". "
                "Aggressive: buy now at Rs." + str(round(p,1)) + ". "
                "Conservative: wait for close above Rs." + str(round(ec,1)) + " with 1.5x+ volume. "
                "Retest: if price pulls back to Rs." + str(round(er,1)) + " and holds, that is the best entry.")
    elif sname == "BULL_FLAG":
        ea=fh; ec=round(fh*1.01,1); er=round(fh*.995,1)
        note = ("Do NOT buy inside the flag. Wait for break above flag high Rs." + str(round(fh,1)) + ". "
                "Aggressive: buy as price breaks Rs." + str(round(fh,1)) + ". "
                "Conservative: buy next candle after a confirmed breakout close.")
    elif sname == "EMA_PULLBACK":
        te=e20 if n20 else e50; en="EMA20" if n20 else "EMA50"
        ea=round(te*1.002,1); ec=round(te*1.01,1); er=round(te*.998,1)
        note = (en + " pullback entry. "
                "Aggressive: buy as price reclaims Rs." + str(round(te,1)) + ". "
                "Conservative: first green candle closing above " + en + ". "
                "Retest at Rs." + str(round(er,1)) + " if touched again.")
    else:
        ea=bh; ec=round(bh*1.01,1); er=round(bh*.995,1)
        note = ("Enter on break above base high Rs." + str(round(bh,1)) + " with volume. "
                "Aggressive: buy on breakout candle. "
                "Conservative: wait for 1.5x+ volume confirmation.")
    r=p-sl; t1=round(p+1.5*r,1); t2=round(p+3*r,1); t3=round(p+5*r,1)
    ra=capital*risk_pct/100; rps=p*sl_pct/100
    qty=int(ra/rps) if rps>0 else 0
    return {
        "ok":True,"final":final,"verdict":verdict,"vc":vc,
        "ea":round(ea,1),"ec":round(ec,1),"er":round(er,1),"note":note,
        "sl":round(sl,1),"sl_pct":round(sl_pct,1),"sl_l":sl_l,
        "t1":t1,"t2":t2,"t3":t3,
        "t1p":round((t1-p)/p*100,1),"t2p":round((t2-p)/p*100,1),"t3p":round((t3-p)/p*100,1),
        "qty":qty,"pv":round(qty*p),"ra":round(ra),"rr":3.0,"e10":round(e10,1),
    }

def get_rets(df, ndf):
    p=safe(df["Close"].iloc[-1]); r6=r12=rs=None
    if len(df)>=126:
        p6=safe(df["Close"].iloc[-126])
        if p6>0: r6=(p-p6)/p6*100
    if len(df)>=252:
        p12=safe(df["Close"].iloc[-252])
        if p12>0: r12=(p-p12)/p12*100
    if ndf is not None and len(ndf)>=126 and r6 is not None:
        np_=safe(ndf["Close"].iloc[-1]); np6=safe(ndf["Close"].iloc[-126])
        if np6>0: rs=r6-(np_-np6)/np6*100
    return r6,r12,rs

def rp(v):
    if v is None: return "—"
    return ("+" if v >= 0 else "") + str(round(v, 1)) + "%"

# ── CHARTS ─────────────────────────────────────────────────────────────────────
# IMPORTANT: All colors use rgba() format. NO 8-digit hex. NO hex+alpha.
BG   = "#0d1117"
GRID = "#21262d"
TXT  = "#8b949e"

# Pre-defined rgba colors (safe for all Plotly versions)
C_GREEN       = "rgba(63,185,80,1)"
C_RED         = "rgba(248,81,73,1)"
C_YELLOW      = "rgba(227,179,65,1)"
C_BLUE        = "rgba(88,166,255,1)"
C_PURPLE      = "rgba(188,140,255,1)"
C_GREEN_DIM   = "rgba(63,185,80,0.4)"   # volume bar green
C_RED_DIM     = "rgba(248,81,73,0.4)"   # volume bar red
C_GREEN_ZONE  = "rgba(63,185,80,0.06)"  # profit zone fill
C_RED_ZONE    = "rgba(248,81,73,0.06)"  # risk zone fill


def build_price_chart(df, sd, tp, ticker, sname):
    d = df.tail(100).copy()

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.02,
    )

    # ── Candlestick — NO fillcolor params (let Plotly use defaults)
    fig.add_trace(go.Candlestick(
        x=d.index,
        open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
        increasing_line_color=C_GREEN,
        decreasing_line_color=C_RED,
        name="Price",
        showlegend=False,
    ), row=1, col=1)

    # ── EMAs
    ema_cfg = [("E20", C_YELLOW, 1.5, "EMA20"), ("E50", C_BLUE, 1.5, "EMA50"), ("E200", C_PURPLE, 1.0, "EMA200")]
    for col_key, col_val, width, name in ema_cfg:
        if col_key in d.columns:
            fig.add_trace(go.Scatter(
                x=d.index, y=d[col_key],
                line=dict(color=col_val, width=width),
                name=name, showlegend=True,
            ), row=1, col=1)

    # ── 52W High line
    h52 = sd.get("h52", 0)
    if h52 > 0:
        fig.add_hline(
            y=h52,
            line=dict(color=C_RED, width=1, dash="dot"),
            annotation_text="52W High " + str(round(h52, 0)),
            annotation_position="top right",
            annotation_font_color=C_RED,
            row=1, col=1,
        )

    # ── Trade levels and zones
    if tp.get("ok"):
        p = sd["p"]
        sl = tp["sl"]; ea = tp["ea"]; t1 = tp["t1"]; t2 = tp["t2"]

        # Risk zone (red fill: SL to entry)
        fig.add_shape(type="rect",
            x0=d.index[0], x1=d.index[-1],
            y0=sl, y1=ea,
            fillcolor=C_RED_ZONE, line_width=0,
            row=1, col=1)

        # Profit zone (green fill: entry to T2)
        fig.add_shape(type="rect",
            x0=d.index[0], x1=d.index[-1],
            y0=ea, y1=t2,
            fillcolor=C_GREEN_ZONE, line_width=0,
            row=1, col=1)

        # Level lines
        fig.add_hline(y=sl, line=dict(color=C_RED, width=2, dash="dash"),
            annotation_text="SL " + str(sl),
            annotation_position="bottom right",
            annotation_font_color=C_RED, row=1, col=1)

        fig.add_hline(y=ea, line=dict(color=C_BLUE, width=1.5, dash="dash"),
            annotation_text="Entry " + str(ea),
            annotation_position="right",
            annotation_font_color=C_BLUE, row=1, col=1)

        fig.add_hline(y=t1, line=dict(color=C_YELLOW, width=1, dash="dot"),
            annotation_text="T1 " + str(t1),
            annotation_position="right",
            annotation_font_color=C_YELLOW, row=1, col=1)

        fig.add_hline(y=t2, line=dict(color=C_GREEN, width=1.5, dash="dot"),
            annotation_text="T2 " + str(t2),
            annotation_position="right",
            annotation_font_color=C_GREEN, row=1, col=1)

    # ── Volume bars
    vol_colors = [C_GREEN_DIM if c >= o else C_RED_DIM
                  for c, o in zip(d["Close"], d["Open"])]
    fig.add_trace(go.Bar(
        x=d.index, y=d["Volume"],
        marker_color=vol_colors,
        name="Volume", showlegend=False,
    ), row=2, col=1)

    if "V50" in d.columns:
        fig.add_trace(go.Scatter(
            x=d.index, y=d["V50"],
            line=dict(color=C_YELLOW, width=1),
            name="Vol 50MA", showlegend=False,
        ), row=2, col=1)

    # ── RSI
    if "RSI" in d.columns:
        fig.add_trace(go.Scatter(
            x=d.index, y=d["RSI"],
            line=dict(color=C_BLUE, width=1.5),
            name="RSI", showlegend=False,
        ), row=3, col=1)
        for level, col in [(70, C_RED), (50, "rgba(72,79,88,1)"), (30, C_GREEN)]:
            fig.add_hline(y=level,
                line=dict(color=col, width=0.8, dash="dot"),
                row=3, col=1)

    # ── Layout
    setup_label = sname.replace("_", " ")
    fig.update_layout(
        height=580,
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(color=TXT, size=11),
        legend=dict(bgcolor=BG, bordercolor=GRID, orientation="h", y=1.02),
        margin=dict(l=0, r=100, t=40, b=0),
        title=dict(
            text=ticker + "  |  " + setup_label + " Setup  |  EMAs · Volume · RSI",
            font=dict(color="#c9d1d9", size=13),
        ),
        xaxis_rangeslider_visible=False,
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor=GRID, showgrid=True, row=i, col=1)
        fig.update_yaxes(gridcolor=GRID, showgrid=True, row=i, col=1)
    fig.update_yaxes(title_text="Price (Rs.)", title_font_color=TXT, row=1, col=1)
    fig.update_yaxes(title_text="Volume",      title_font_color=TXT, row=2, col=1)
    fig.update_yaxes(title_text="RSI",         title_font_color=TXT, row=3, col=1, range=[0, 100])
    return fig


def build_gauge(score, verdict, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": verdict, "font": {"size": 15, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TXT, "tickfont": {"color": TXT}},
            "bar":  {"color": color, "thickness": 0.35},
            "bgcolor": BG,
            "bordercolor": GRID,
            "steps": [
                {"range": [0,  68], "color": "#161b22"},
                {"range": [68, 78], "color": "#1a1f28"},
                {"range": [78, 90], "color": "#0d1e0d"},
                {"range": [90,100], "color": "#0b2010"},
            ],
            "threshold": {
                "line": {"color": C_YELLOW, "width": 3},
                "thickness": 0.8,
                "value": 80,
            },
        },
        number={"font": {"size": 44, "color": color}, "suffix": "/100"},
    ))
    fig.update_layout(
        height=260,
        paper_bgcolor=BG,
        font_color=TXT,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig


def build_bars(scores_dict, weights_dict):
    if not weights_dict:
        return None
    keys   = [k for k in weights_dict if k in scores_dict]
    if not keys:
        return None
    scored = [scores_dict[k] for k in keys]
    maxes  = [weights_dict[k] for k in keys]
    pcts   = [s / m * 100 if m > 0 else 0 for s, m in zip(scored, maxes)]
    colors = [C_GREEN if x >= 75 else C_YELLOW if x >= 50 else C_RED for x in pcts]
    labels = [k + " (" + str(scored[i]) + "/" + str(maxes[i]) + ")" for i, k in enumerate(keys)]

    fig = go.Figure(go.Bar(
        x=pcts, y=labels,
        orientation="h",
        marker_color=colors,
        text=[str(round(x, 0)) + "%" for x in pcts],
        textposition="outside",
        textfont=dict(color=TXT, size=11),
    ))
    fig.update_layout(
        height=max(200, len(keys) * 42),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font_color=TXT,
        showlegend=False,
        margin=dict(l=0, r=60, t=30, b=0),
        xaxis=dict(range=[0, 130], showgrid=True, gridcolor=GRID,
                   ticksuffix="%", title="Score %"),
        yaxis=dict(showgrid=False),
        title=dict(text="Score Breakdown by Factor",
                   font=dict(color="#c9d1d9", size=12)),
    )
    return fig

# ── REGIME ─────────────────────────────────────────────────────────────────────
def get_regime(ndf, bndf):
    rows = []; pen = 0
    for name, df in [("Nifty 50", ndf), ("Bank Nifty", bndf)]:
        if df is None or len(df) < 30:
            rows.append((name, "UNKNOWN", "⚪", 0)); continue
        d    = enrich(df); p = safe(d["Close"].iloc[-1])
        e50  = safe(d["E50"].iloc[-1]); e200 = safe(d["E200"].iloc[-1])
        if p < e200:
            rows.append((name, "BEARISH", "🔴", 20)); pen = max(pen, 20)
        elif p < e50:
            rows.append((name, "CAUTION", "🟠", 10)); pen = max(pen, 10)
        else:
            rows.append((name, "HEALTHY", "🟢", 0))
    return rows, pen

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Header
    st.markdown(
        "<div style='background:#161b22;border-bottom:1px solid #21262d;"
        "padding:10px 0;margin-bottom:12px;'>"
        "<span style='color:#58a6ff;font-size:18px;font-weight:800;font-family:monospace;'>"
        "📈 NSE ELITE SWING TERMINAL</span>"
        "<span style='color:#484f58;font-size:12px;margin-left:12px;'>"
        + datetime.now().strftime("%a %d %b %Y") + "</span></div>",
        unsafe_allow_html=True,
    )

    # Market regime
    with st.spinner("Loading market data..."):
        nifty_df  = fetch_idx("^NSEI")
        bnifty_df = fetch_idx("^NSEBANK")
        vix_df    = fetch_idx("^INDIAVIX")

    regime_rows, regime_pen = get_regime(nifty_df, bnifty_df)
    vix_val = safe(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df) > 0 else None

    rc = st.columns(5)
    for i, (name, status, dot, pen) in enumerate(regime_rows):
        with rc[i]:
            st.metric(
                name,
                dot + " " + status,
                delta=("-" + str(pen) + " pts to all scores") if pen > 0 else "Full scoring active",
                delta_color="inverse" if pen > 0 else "off",
            )
    with rc[2]:
        if vix_val:
            vs = "LOW ✅" if vix_val < 15 else "ELEVATED ⚠️" if vix_val < 20 else "HIGH 🔴"
            st.metric("India VIX", str(round(vix_val, 1)), delta=vs, delta_color="off")
    with rc[3]:
        st.metric("Regime Penalty", "-" + str(regime_pen) + " pts",
                  delta_color="inverse" if regime_pen > 0 else "off")

    if regime_pen >= 20:
        st.error("🚫 CAPITAL PRESERVATION MODE — Nifty below 200 EMA. Only scores 85+ qualify. Cut ALL position sizes by 50%.")
    elif regime_pen >= 10:
        st.warning("⚠️ CAUTION — Market below 50 EMA. Half position sizes. Prefer EMA pullback setups.")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚡ Stock Analyzer",
        "📚 Setup School",
        "📡 Chartink Scanners",
        "📋 Trading Rules",
        "🏭 Sector Watch",
    ])

    # ══ TAB 1 ═════════════════════════════════════════════════════════════════
    with tab1:
        left, right = st.columns([1, 2.5], gap="large")

        with left:
            st.markdown("#### 🔍 Stock Lookup")
            sym  = st.text_input("NSE Symbol", placeholder="e.g. AKUMS, BEL, TCS").upper().strip()
            pick = st.selectbox("Or pick from popular list", [""] + POPULAR)
            if pick and not sym:
                sym = pick
            cap = st.number_input("Capital (Rs.)", min_value=50000, max_value=10000000,
                                   value=300000, step=50000, format="%d")
            rsk = st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25,
                             help="Use 0.5% on expiry or high-VIX days")
            go  = st.button("⚡ Detect Setup & Score", use_container_width=True)
            st.info("The app detects which setup the stock is in (VCP, Breakout, Flag, Pullback, Second Leg), then scores it with weights specific to that setup type. Chart shows EMAs, volume, RSI, and your exact trade levels.")

        with right:
            if not go:
                st.markdown("#### ← Enter a symbol and click Analyze")
                for k, m in SETUPS.items():
                    if k == "NO_SETUP": continue
                    st.markdown(m["icon"] + " **" + m["name"] + "** — " + m["tagline"])

            elif not sym:
                st.warning("Please enter a stock symbol or pick from the list.")

            else:
                with st.spinner("Fetching " + sym + " from NSE..."):
                    df_raw, ticker = fetch_stock(sym)

                if df_raw is None:
                    st.error("Could not fetch '" + sym + "'. Check the NSE ticker. Try: RELIANCE, TCS, AKUMS, BEL, DATAPATTNS")
                else:
                    # ── COMPUTE ────────────────────────────────────────────────
                    df   = enrich(df_raw)
                    l    = df.iloc[-1]
                    p    = safe(l["Close"])
                    pv   = safe(df["Close"].iloc[-2])
                    dchg = (p - pv) / pv * 100 if pv > 0 else 0
                    avg_vol  = df["Volume"].tail(50).mean()
                    turnover = avg_vol * p
                    r6, r12, rs    = get_rets(df, nifty_df)
                    sname, sd      = detect_setup(df)
                    sc, flags, raw = score_setup(sname, sd, r6, r12, rs)
                    tp             = make_trade(sname, sd, raw, cap, rsk, regime_pen)
                    meta           = SETUPS[sname]
                    color          = meta["color"]

                    h52  = safe(l["H52"], p); e20=safe(l["E20"]); e50=safe(l["E50"]); e200=safe(l["E200"])
                    vr_  = safe(l["VR"], 1); rsi_=safe(l["RSI"], 50)

                    # Spike check
                    if abs(dchg) >= 10:   sp=-20; sp_msg="🚨 SPIKE: +" + str(round(abs(dchg),1)) + "% today — -20 pts. Do not chase."
                    elif abs(dchg) >= 8:  sp=-10; sp_msg="⚠️ BIG MOVE: +" + str(round(abs(dchg),1)) + "% — -10 pts. Wait next session."
                    elif abs(dchg) >= 5:  sp=-5;  sp_msg="ℹ️ MOVE: +" + str(round(abs(dchg),1)) + "% — -5 pts. Prefer next day."
                    else:                  sp=0;   sp_msg=""

                    final = max(0, tp.get("final", raw - regime_pen) + sp)

                    # ── STOCK HEADER ───────────────────────────────────────────
                    d_sign = "+" if dchg >= 0 else ""
                    hc = st.columns(5)
                    with hc[0]: st.metric("Symbol", ticker.replace(".NS","").replace(".BO",""))
                    with hc[1]: st.metric("Price", "Rs." + "{:,.2f}".format(p),
                                           delta=d_sign + str(round(dchg,2)) + "%")
                    with hc[2]:
                        ph = (h52-p)/h52*100 if h52>0 else 0
                        st.metric("52W High", "Rs." + "{:,.1f}".format(h52),
                                   delta=str(round(ph,1)) + "% away" if ph>0 else "AT HIGH ✓",
                                   delta_color="inverse" if ph>5 else "off")
                    with hc[3]: st.metric("Turnover", "Rs." + str(round(turnover/1e7,1)) + " Cr/day")
                    with hc[4]: st.metric("Date", df.index[-1].strftime("%d %b %Y"))

                    if sp_msg:
                        st.warning(sp_msg)

                    st.divider()

                    # ── SETUP CARD ─────────────────────────────────────────────
                    st.markdown("### " + meta["icon"] + " Setup: **" + meta["name"].upper() + "**")
                    st.markdown("*" + meta["tagline"] + "*")

                    sa, sb, sc_col = st.columns(3)
                    with sa:
                        st.metric("Risk Profile", meta["risk"])
                        st.metric("Ideal Hold",   meta["hold"])
                        st.metric("Min Score Needed", str(meta["min"]) + "/100")
                    with sb:
                        st.markdown("**What is this setup?**")
                        st.write(meta["desc"])
                    with sc_col:
                        st.success("✅ ENTER WHEN: " + meta["enter"])
                        st.error("❌ AVOID WHEN: " + meta["avoid"])

                    st.divider()

                    # ── KEY METRICS ────────────────────────────────────────────
                    st.markdown("#### Key Metrics")
                    mc = st.columns(8)
                    ph2 = (h52-p)/h52*100 if h52>0 else 0
                    items = [
                        ("52W High", "Rs." + "{:,.0f}".format(h52), "#3fb950" if ph2<=3 else "#e3b341" if ph2<=10 else "#f85149"),
                        ("EMA 20",   "Rs." + "{:,.0f}".format(e20), "#3fb950" if p>e20 else "#f85149"),
                        ("EMA 50",   "Rs." + "{:,.0f}".format(e50), "#3fb950" if e20>e50 else "#f85149"),
                        ("EMA 200",  "Rs." + "{:,.0f}".format(e200),"#3fb950" if e50>e200 else "#f85149"),
                        ("Volume",   str(round(vr_,1))+"x",  "#3fb950" if vr_>=1.5 else "#e3b341" if vr_>=1 else "#f85149"),
                        ("RSI",      str(round(rsi_)),        "#3fb950" if 50<=rsi_<=65 else "#e3b341" if rsi_<80 else "#f85149"),
                        ("6M Ret",   rp(r6),                  "#3fb950" if r6 and r6>=20 else "#e3b341" if r6 and r6>=0 else "#f85149"),
                        ("RS>Nifty", rp(rs),                  "#3fb950" if rs and rs>=10 else "#e3b341" if rs and rs>=0 else "#f85149"),
                    ]
                    for i, (lbl, val, col) in enumerate(items):
                        with mc[i]:
                            st.markdown(
                                "<div style='background:#161b22;border:1px solid #21262d;"
                                "border-radius:6px;padding:8px;text-align:center;'>"
                                "<div style='color:#8b949e;font-size:9px;font-weight:700;'>" + lbl + "</div>"
                                "<div style='color:" + col + ";font-size:14px;font-weight:800;"
                                "font-family:monospace;'>" + val + "</div>"
                                "</div>",
                                unsafe_allow_html=True,
                            )

                    st.divider()

                    # ── SCORE + CHART ──────────────────────────────────────────
                    vc      = tp.get("vc", "#484f58")
                    verdict = tp.get("verdict", "—")

                    chart_col, gauge_col = st.columns([3, 1])

                    with gauge_col:
                        st.plotly_chart(build_gauge(final, verdict, vc), use_container_width=True)
                        if final >= 90:   st.success("**ELITE** — Full 1% risk.")
                        elif final >= 78: st.info("**STRONG** — Full 1% risk.")
                        elif final >= 65: st.warning("**TRADABLE** — Use 0.5% risk.")
                        else:             st.error("**AVOID** — Below minimum.")
                        rp_s = " — Regime: -" + str(regime_pen) if regime_pen > 0 else ""
                        sp_s = " — Spike: "   + str(sp)        if sp < 0            else ""
                        st.caption("Raw: " + str(raw) + rp_s + sp_s + " = **" + str(final) + "**")

                    with chart_col:
                        st.plotly_chart(
                            build_price_chart(df, sd, tp, ticker, sname),
                            use_container_width=True,
                        )

                    # ── SCORE BREAKDOWN BARS ───────────────────────────────────
                    if meta["weights"]:
                        fig_b = build_bars(sc, meta["weights"])
                        if fig_b:
                            st.plotly_chart(fig_b, use_container_width=True)

                    st.divider()

                    # ── SIGNAL ANALYSIS ────────────────────────────────────────
                    st.markdown("#### Signal Analysis — Why This Score")
                    bull = [f for f in flags if f[0] == "bull"]
                    warn = [f for f in flags if f[0] == "warn"]
                    bear = [f for f in flags if f[0] == "bear"]

                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        st.markdown("✅ **Bullish Signals (" + str(len(bull)) + ")**")
                        for _, lbl, val, desc in bull:
                            with st.expander("▲ " + lbl + ": " + val):
                                st.write(desc)
                    with fc2:
                        st.markdown("⚠️ **Caution Signals (" + str(len(warn)) + ")**")
                        for _, lbl, val, desc in warn:
                            with st.expander("◆ " + lbl + ": " + val):
                                st.write(desc)
                    with fc3:
                        st.markdown("❌ **Bearish Signals (" + str(len(bear)) + ")**")
                        for _, lbl, val, desc in bear:
                            with st.expander("▼ " + lbl + ": " + val):
                                st.write(desc)

                    st.divider()

                    # ── TRADE PLAN ─────────────────────────────────────────────
                    if tp.get("ok"):
                        st.markdown("#### Trade Plan")
                        st.info("**HOW TO ENTER:** " + tp["note"])

                        lc = st.columns(7)
                        lvls = [
                            ("AGGRESSIVE\nENTRY",              "Rs."+"{:,.1f}".format(tp["ea"]), "#58a6ff", "Enter now / at open"),
                            ("CONSERVATIVE\nENTRY",            "Rs."+"{:,.1f}".format(tp["ec"]), "#79c0ff", "Wait for confirm"),
                            ("STOP LOSS\n"+str(tp["sl_pct"])+"%","Rs."+"{:,.1f}".format(tp["sl"]), "#f85149", tp["sl_l"]),
                            ("RETEST\nENTRY",                   "Rs."+"{:,.1f}".format(tp["er"]), "#484f58", "If price pulls back"),
                            ("TARGET 1\n+"+str(tp["t1p"])+"%", "Rs."+"{:,.1f}".format(tp["t1"]), "#e3b341", "Book 30% here"),
                            ("TARGET 2\n+"+str(tp["t2p"])+"%", "Rs."+"{:,.1f}".format(tp["t2"]), "#3fb950", "Book 30% here"),
                            ("TARGET 3\n+"+str(tp["t3p"])+"%", "Rs."+"{:,.1f}".format(tp["t3"]), "#56d364", "Trail 40%"),
                        ]
                        for i, (lbl, val, col, sub) in enumerate(lvls):
                            with lc[i]:
                                st.markdown(
                                    "<div style='background:#161b22;border:1px solid " + col + "40;"
                                    "border-radius:8px;padding:10px;text-align:center;'>"
                                    "<div style='color:#8b949e;font-size:9px;font-weight:700;"
                                    "white-space:pre-line;'>" + lbl + "</div>"
                                    "<div style='color:" + col + ";font-size:13px;font-weight:800;"
                                    "font-family:monospace;margin:5px 0;'>" + val + "</div>"
                                    "<div style='color:#6e7681;font-size:9px;'>" + sub + "</div>"
                                    "</div>",
                                    unsafe_allow_html=True,
                                )

                        pc1, pc2 = st.columns(2)
                        with pc1:
                            st.metric("Risk : Reward", "1 : " + str(tp["rr"]), delta="Minimum 3:1 ✓")
                        with pc2:
                            st.metric(
                                "Position Size (" + str(rsk) + "% risk)",
                                str(tp["qty"]) + " shares = Rs." + "{:,}".format(tp["pv"]),
                                delta="Max risk: Rs." + "{:,}".format(tp["ra"]),
                            )

                        st.divider()
                        st.markdown("#### Exit Plan")
                        exit_steps = [
                            ("After fill",                  "Place GTT stop at Rs." + str(tp["sl"]) + " IMMEDIATELY. A trade without a stop is not a trade — it is gambling."),
                            ("At T1 (Rs." + str(tp["t1"]) + ")", "Book 30%. Move stop to your entry price. Trade is now RISK-FREE."),
                            ("At T2 (Rs." + str(tp["t2"]) + ")", "Book 30%. Move stop to T1 level. Let last 40% run."),
                            ("Trailing 40%",                "Trail stop using daily close below EMA10 (Rs." + str(tp["e10"]) + "). Never lower the stop."),
                            ("Hard stop",                   "If price closes below Rs." + str(tp["sl"]) + " — exit ENTIRE position next morning. No debate."),
                            ("Time stop",                   "No progress in 15 trading days? Exit and redeploy capital."),
                            ("Pre-event exit",              "Exit 1 day before earnings results, RBI policy, or Budget. No exceptions."),
                        ]
                        for step, desc in exit_steps:
                            st.markdown("**" + step + ":** " + desc)

                    else:
                        st.error("NO TRADE — " + tp.get("reason", "Score below minimum for this setup."))

    # ══ TAB 2 ═════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## 📚 Setup School")
        st.markdown("A complete guide to every setup the app detects. Understanding the logic makes you a better trader.")
        for key, meta in SETUPS.items():
            if key == "NO_SETUP": continue
            with st.expander(meta["icon"] + " " + meta["name"] + " — " + meta["tagline"]):
                st.write(meta["desc"])
                c1, c2 = st.columns(2)
                with c1:
                    st.success("**ENTER WHEN:** " + meta["enter"])
                    st.metric("Risk Profile", meta["risk"])
                    st.metric("Ideal Hold",   meta["hold"])
                    st.metric("Min Score",    str(meta["min"]) + "/100")
                with c2:
                    st.error("**AVOID WHEN:** " + meta["avoid"])
                    st.markdown("**Scoring weights:**")
                    total = sum(meta["weights"].values()) if meta["weights"] else 1
                    for wk, wv in meta["weights"].items():
                        st.progress(wv / total, text=wk + ": " + str(wv) + " pts")

    # ══ TAB 3 ═════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## 📡 Chartink Scanners")
        st.markdown("**How to use:** chartink.com → Screens → Create New Screen → paste code → Generate → Run after 4 PM IST")

        scanners = [
            ("🟢 Tier 1 — 52W High Breakout", "HIGHEST — Act immediately",
             "Nifty 200 stocks breaking above 52-week high THIS WEEK with 1.5x+ volume and full Stage 2 EMA stack.",
             "The 52W high breakout on institutional volume is the #1 momentum signal. No overhead resistance.",
             "Run FIRST after 4 PM every day.",
             "Enter at market open next day or on a retest. Set GTT stop immediately.",
             "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
             [("{nifty 200}", "Nifty 200 universe. No penny stocks."),
              ("close > 1 weeks max(52,high)", "Price is ABOVE the 52-week high. The breakout is happening."),
              ("volume > 1.5x sma(50)", "Non-negotiable. Low-volume breakouts fail 60%+ of the time."),
              ("EMA20 > EMA50 > EMA200", "Confirms Stage 2 uptrend across all timeframes."),
              ("Turnover > Rs.25Cr", "Minimum liquidity gate.")]),
            ("🟠 Tier 2 — VCP / Pre-Breakout", "HIGH — Build GTT watchlist",
             "Nifty 200 stocks within 3% of 52W high with 10-day volume below 50-day average.",
             "Catches the setup BEFORE Tier 1 fires. Volume drying near highs = supply exhaustion. Better price and tighter stop.",
             "Run after Tier 1. Results = GTT alert list.",
             "Set alert at 52W high. Enter ONLY when price breaks with 1.5x+ volume.",
             "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
             [("close > 0.97x 52W high", "Within 3% of breakout."),
              ("close < 52W high", "Has NOT broken out yet."),
              ("sma(vol,10) < sma(vol,50)", "VCP signal. Volume contracting near highs = supply exhausting."),
              ("Full EMA stack", "Coil forming in uptrend, not downtrend.")]),
            ("🔵 Tier 3 — Momentum Leaders", "MEDIUM — Enter on EMA20 dips only",
             "Stage 2 stocks up 25%+ in both 6M and 12M. Proven momentum leaders.",
             "Counter-intuitive but proven: stocks up 40% with bullish EMA stack are MORE likely to keep rising.",
             "Run weekly. Results = core momentum watchlist.",
             "Do NOT buy now. Wait for 2-5 day pullback to EMA20 with drying volume THEN enter.",
             "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
             [("Full EMA stack", "Confirmed Stage 2."),
              ("close > 1.25x 26wk ago", "Up 25%+ in 6 months."),
              ("close > 1.25x 52wk ago", "Up 25%+ in 12 months. Sustained momentum.")]),
            ("🟣 Tier 4 — Pure VCP / Tight Base", "HIGH — Chart review required",
             "Within 10% of highs with volume contracted 25%+. Most explosive when it fires.",
             "Deep volume contraction near highs = supply exhausted. When buyers return, move is sharp and fast.",
             "Run daily. Every result needs chart verification in TradingView.",
             "Confirm: tightening daily range + declining volume bars. Enter on breakout on 2x+ volume.",
             "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
             [("close > 0.90x 52W high", "Within 10% of highs."),
              ("EMA stack", "Base in uptrend."),
              ("sma(vol,10) < 0.75x sma(vol,50)", "Volume contracted 25%+. The VCP squeeze.")]),
        ]

        for sc_name, prio, what, why, when_, action, code, conds in scanners:
            with st.expander(sc_name + " — " + prio):
                st.markdown("**What it finds:** " + what)
                st.markdown("**Why it works:** " + why)
                st.markdown("**When to run:** " + when_)
                st.success("**Action:** " + action)
                st.markdown("**Conditions explained:**")
                for cond, expl in conds:
                    st.markdown("- `" + cond + "` — " + expl)
                st.code(code, language="text")

    # ══ TAB 4 ═════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## 📋 Trading Rules")
        st.markdown("Every rule here was discovered through losses. Each has a specific reason.")

        rule_blocks = [
            ("🎯 Prime Directive", [
                ("No trade is the best trade", "When unclear, market weak, or unsure — do nothing. Missing a trade costs nothing. A bad trade can cost weeks of gains."),
                ("Score minimums are not optional", "Below minimum, the statistical edge disappears. Trading below minimum = gambling."),
                ("Always 3:1 risk-reward minimum", "Stop 5% away? Target must be 15% minimum. At 3:1 you can be right 35% of the time and still profit."),
            ]),
            ("💰 Position Sizing", [
                ("1% risk per trade maximum", "At 1%, 20 consecutive losses leaves 82% of capital. At 3%, you're down 46%. The math is unforgiving."),
                ("0.5% on uncertain days", "F&O expiry, VIX above 20, Caution or Bearish regime — use half size."),
                ("25% max in any single stock", "Unexpected news can gap a stock 20% down overnight. Concentration kills accounts."),
                ("Max 5 positions simultaneously", "More than 5 and you can't monitor properly."),
                ("5% total portfolio heat max", "Sum of risk on ALL open trades must never exceed 5% of capital."),
            ]),
            ("🚫 Hard Rules — Never Break", [
                ("GTT stop immediately after entry", "The moment your order fills, place the GTT stop. Most accounts are destroyed by refusing to exit."),
                ("Never average down", "If stock reaches your stop, exit. Don't add. Averaging down turns small losses into catastrophic ones."),
                ("Never widen your stop", "You set the stop before emotion entered. Trust your pre-trade analysis. Never move it wider."),
                ("No trades 9:15–9:30 AM", "First 15 minutes = overnight order unwinding, gap fills, market maker games."),
                ("No new entries after 3:15 PM", "Closing auction distorts prices. Never open a new swing position in this window."),
                ("No earnings holds", "Check for results in next 5 days. Exit before results. Even the best setup can gap 20% down."),
                ("No revenge trades", "After a stop loss, step away 15 minutes. The urge to immediately recover is the most dangerous emotion."),
            ]),
            ("🇮🇳 India-Specific Rules", [
                ("F&O Expiry", "Monthly = last Thursday. Weekly = every Thursday. On expiry: 0.5% risk only. No new entries 1-3 PM."),
                ("Bank Nifty leads Nifty", "If Bank Nifty weak while Nifty flat, expect Nifty to follow lower."),
                ("FII/DII data", "Check NSE data after 3:30 PM. FIIs selling Rs.3000+ Cr net = reduce all sizes next day."),
                ("Delivery percentage", "Breakouts with delivery above 40% have higher success rates. Below 30% = possible operator activity."),
                ("RBI policy and Budget", "Reduce open positions 50% the day before. These can move sectors 5-10% in one session."),
            ]),
            ("📅 Daily Routine", [
                ("9:00 AM", "Check Nifty futures direction. Check India VIX. Set GTT orders for watchlist."),
                ("9:15–9:30 AM", "Watch only. No new trades."),
                ("9:30–11:00 AM", "Primary execution window."),
                ("After 4 PM", "Run Chartink scanners (Tier 1 first). Build watchlist. Check results calendar. Update journal."),
            ]),
        ]

        for section, rules in rule_blocks:
            with st.expander(section):
                for rule_name, rule_desc in rules:
                    st.markdown("**" + rule_name + ":** " + rule_desc)
                    st.divider()

    # ══ TAB 5 ═════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("## 🏭 Sector Watch")
        st.markdown("Scan an entire sector at once. Results ranked by score.")

        sel = st.selectbox("Select Sector", list(SECTORS.keys()))
        if st.button("📡 Scan " + sel + " Sector"):
            stocks  = SECTORS[sel]
            results = []
            prog    = st.progress(0)
            stat    = st.empty()

            for i, sym_s in enumerate(stocks):
                stat.text("Scanning " + sym_s + "... (" + str(i+1) + "/" + str(len(stocks)) + ")")
                try:
                    df_s, _ = fetch_stock(sym_s)
                    if df_s is None:
                        results.append({"sym":sym_s,"setup":"NO DATA","score":0,"r6":"—","r12":"—","verdict":"—","price":"—"})
                    else:
                        df_s      = enrich(df_s)
                        r6_s, r12_s, rs_s = get_rets(df_s, nifty_df)
                        sn_s, sd_s        = detect_setup(df_s)
                        sc_s, _, raw_s    = score_setup(sn_s, sd_s, r6_s, r12_s, rs_s)
                        tp_s              = make_trade(sn_s, sd_s, raw_s, 300000, 1.0, regime_pen)
                        m_s               = SETUPS[sn_s]
                        results.append({
                            "sym":     sym_s,
                            "setup":   m_s["icon"] + " " + sn_s.replace("_"," "),
                            "score":   tp_s.get("final", raw_s - regime_pen),
                            "r6":      rp(r6_s),
                            "r12":     rp(r12_s),
                            "verdict": tp_s.get("verdict", "—"),
                            "price":   "Rs." + "{:,.1f}".format(safe(df_s["Close"].iloc[-1])),
                        })
                except Exception:
                    results.append({"sym":sym_s,"setup":"ERROR","score":0,"r6":"—","r12":"—","verdict":"—","price":"—"})
                prog.progress((i + 1) / len(stocks))

            prog.empty(); stat.empty()
            results.sort(key=lambda x: x["score"], reverse=True)

            df_out = pd.DataFrame(results)[["sym","price","setup","score","r6","r12","verdict"]]
            df_out.columns = ["Symbol","Price","Setup Detected","Score/100","6M Return","12M Return","Verdict"]

            def color_score(v):
                if not isinstance(v, (int, float)): return ""
                if v >= 80: return "background-color:#0b2010;color:#3fb950;font-weight:bold"
                if v >= 65: return "background-color:#1c1a0a;color:#e3b341"
                if v >  0:  return "background-color:#1c0a0a;color:#f85149"
                return "color:#484f58"

            st.dataframe(
                df_out.style.applymap(color_score, subset=["Score/100"]),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    st.caption("Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day. Always verify on NSE before trading.")

if __name__ == "__main__":
    main()
