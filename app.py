"""
NSE Elite Swing Terminal — Clean Edition
Clean UI. Big score display. Step-by-step guidance. Portfolio tracker. No charting library.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="NSE Swing Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── STYLE ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp { background:#0a0e1a; color:#d0d7e3; font-family:'Inter',sans-serif; }
.main .block-container { max-width:1100px; padding-top:1rem; padding-bottom:3rem; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:#111827; border-bottom:2px solid #1f2937; gap:4px; }
.stTabs [data-baseweb="tab"] {
    color:#6b7280 !important; font-size:13px !important;
    font-weight:600 !important; padding:10px 18px !important;
    border-radius:6px 6px 0 0 !important;
}
.stTabs [aria-selected="true"] {
    color:#f0f6ff !important; background:#1f2937 !important;
    border-bottom:2px solid #3b82f6 !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background:#111827 !important; border:1px solid #374151 !important;
    color:#d0d7e3 !important; border-radius:8px !important; font-size:14px !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stSlider label {
    color:#9ca3af !important; font-size:12px !important; font-weight:600 !important;
    letter-spacing:0.5px !important;
}

/* Button */
.stButton > button {
    background:linear-gradient(135deg,#1d4ed8,#2563eb) !important;
    color:#ffffff !important; font-weight:700 !important; font-size:14px !important;
    border:none !important; border-radius:8px !important; padding:10px 24px !important;
    width:100% !important;
}
.stButton > button:hover { background:linear-gradient(135deg,#1e40af,#1d4ed8) !important; }

/* Expander */
.stExpander { background:#111827 !important; border:1px solid #1f2937 !important; border-radius:10px !important; }

/* Divider */
hr { border-color:#1f2937 !important; margin:1rem 0 !important; }

/* Metric */
div[data-testid="stMetricValue"] { color:#f0f6ff !important; font-size:18px !important; font-weight:700 !important; }
div[data-testid="stMetricLabel"] { color:#6b7280 !important; font-size:11px !important; }
div[data-testid="stMetricDelta"] { font-size:11px !important; }
</style>
""", unsafe_allow_html=True)

# ── SAFE HELPER ────────────────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        f = float(v)
        return d if (f != f) else f
    except:
        return d

def fmt_pct(v):
    if v is None: return "—"
    return ("+" if v >= 0 else "") + str(round(v, 1)) + "%"

def fmt_rs(v):
    return "Rs." + "{:,.1f}".format(v)

# ── STOCK DATA ─────────────────────────────────────────────────────────────────
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
    "TATASTEEL","HINDALCO","CUMMINSIND","THERMAX","ASTRAL","VOLTAS",
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

# ── SETUP CONFIGS ──────────────────────────────────────────────────────────────
SETUPS = {
    "VCP": {
        "color":"#10b981","icon":"🌀","name":"Volatility Contraction Pattern",
        "tagline":"Coiling near highs, volume shrinking",
        "risk":"LOW","hold":"5–15 days","min_score":72,
        "sl_type":"ema10",
        "description":"Stock is making progressively smaller pullbacks near its highs while volume dries up. Supply is being exhausted. The coil is tightening before an explosive breakout.",
        "step_by_step":[
            "WAIT: Do not enter yet. Set a price alert at the 52-week high.",
            "ENTRY TRIGGER: When price breaks above the tight range on 2x+ average volume — that is your entry candle.",
            "ENTER: Buy at the open of the next candle, or on the breakout candle itself.",
            "STOP LOSS: Place GTT stop 1% below EMA10 immediately after your fill.",
            "TARGETS: T1 = 1.5x risk above entry (book 30%). T2 = 3x risk (book 30%). Trail rest with EMA10.",
        ],
        "weights":{"Volume Contraction":25,"Price Tightness":20,"52W Proximity":20,"EMA Stack":15,"RSI":10,"MACD":10},
    },
    "BREAKOUT": {
        "color":"#3b82f6","icon":"🚀","name":"52-Week High Breakout",
        "tagline":"Clearing 52W high on institutional volume",
        "risk":"MEDIUM","hold":"5–20 days","min_score":75,
        "sl_type":"ema20",
        "description":"Stock is breaking above its 52-week high with strong volume. Every seller from the past year is now at profit — no overhead resistance. This is the #1 momentum signal.",
        "step_by_step":[
            "CONFIRM: Volume must be at least 1.5x the 50-day average. Without volume, it is a fake breakout.",
            "ENTRY: Buy at market open the day after the breakout close, or intraday when the break holds for 30 minutes.",
            "AGGRESSIVE ENTRY: Buy on the breakout candle itself if volume is 2x+.",
            "STOP LOSS: Place GTT stop 1% below EMA20 immediately after your fill.",
            "TARGETS: T1 = 1.5x risk (book 30%). T2 = 3x risk (book 30%). Trail rest with EMA10.",
        ],
        "weights":{"Breakout Volume":30,"EMA Stack":20,"52W Proximity":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "BULL_FLAG": {
        "color":"#f59e0b","icon":"🏴","name":"Bull Flag",
        "tagline":"Strong move up, now resting before next surge",
        "risk":"LOW-MEDIUM","hold":"3–10 days","min_score":70,
        "sl_type":"flag_low",
        "description":"Stock made a fast 15-30% move (the pole), then has been consolidating tightly for 5-10 days with declining volume (the flag). Volume dropping during the flag confirms institutions are holding, not selling.",
        "step_by_step":[
            "WAIT: Do NOT buy inside the flag. The setup fires only on the breakout.",
            "ENTRY TRIGGER: Price breaks above the highest point of the flag on expanding volume.",
            "ENTER: Buy on the breakout candle above flag high. Do not wait — flags break fast.",
            "STOP LOSS: Place GTT stop below the flag low immediately after fill.",
            "TARGETS: T1 = 1.5x risk (book 30%). T2 = flag pole length added to breakout (book 30%). Trail rest.",
        ],
        "weights":{"Pole Strength":25,"Flag Tightness":25,"Volume Pattern":20,"EMA Stack":15,"RSI":10,"MACD":5},
    },
    "EMA_PULLBACK": {
        "color":"#60a5fa","icon":"↩️","name":"EMA Pullback",
        "tagline":"Dip to EMA20 in uptrend — lowest risk entry",
        "risk":"LOWEST","hold":"5–15 days","min_score":68,
        "sl_type":"ema20",
        "description":"Stock is in a confirmed uptrend and has dipped back to EMA20 on low volume. This is the classic 'buy the dip in an uptrend' setup. Low volume on the dip means nobody is panic-selling — just natural profit taking.",
        "step_by_step":[
            "CONFIRM: Volume on the dip must be below average. High volume on a dip = danger, not opportunity.",
            "ENTRY TRIGGER: First green daily candle that closes back above EMA20 after the dip.",
            "ENTER: Buy on the open the day after the reversal candle, or as EMA20 is reclaimed intraday.",
            "STOP LOSS: Place GTT stop 1% below EMA20 immediately after fill. This should be a very small stop.",
            "TARGETS: T1 = 1.5x risk (book 30%). T2 = prior swing high (book 30%). Trail rest with EMA10.",
        ],
        "weights":{"EMA Stack":25,"Pullback Quality":25,"Volume on Dip":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "SECOND_LEG": {
        "color":"#a78bfa","icon":"⚡","name":"Second Leg",
        "tagline":"First move proved it — second move often bigger",
        "risk":"MEDIUM","hold":"10–30 days","min_score":75,
        "sl_type":"base_low",
        "description":"Stock made a big first move (30-80%), then built a tight base. The tight base proves institutions didn't sell their holdings. Now breaking out into a second leg — typically even larger than the first.",
        "step_by_step":[
            "VERIFY: Check that the base correction was less than 35%. Deeper than 35% = weak setup.",
            "CONFIRM: MACD must be positive throughout the base. If MACD went negative, the setup is damaged.",
            "ENTRY TRIGGER: Price breaks above the base high with 1.5x+ volume.",
            "ENTER: Buy on the breakout candle or at next day's open.",
            "STOP LOSS: Place GTT stop 1% below the base low immediately after fill.",
            "TARGETS: T1 = 1.5x risk (book 30%). T2 = 3x risk (book 30%). Trail rest with EMA10.",
        ],
        "weights":{"First Leg":25,"Base Quality":25,"Breakout Volume":20,"RS vs Nifty":15,"MACD":10,"EMA Stack":5},
    },
    "FLAT_BASE": {
        "color":"#34d399","icon":"📊","name":"Flat Base",
        "tagline":"Tight sideways range near highs — supply absorbed",
        "risk":"LOW","hold":"5–20 days","min_score":68,
        "sl_type":"base_low",
        "description":"Stock has been moving sideways in a very tight range (less than 8%) for 3+ weeks near its highs. Volume has been declining. This is supply exhaustion — buyers and sellers are in balance, waiting for the next catalyst.",
        "step_by_step":[
            "CONFIRM: Range must be less than 8% and duration at least 3 weeks. Shorter or wider = weaker setup.",
            "ENTRY TRIGGER: Price breaks above the flat base ceiling on 1.5x+ volume.",
            "ENTER: Buy on the breakout candle or at next day's open if breakout happened at end of session.",
            "STOP LOSS: Place GTT stop 1% below the base low immediately after fill.",
            "TARGETS: T1 = 1.5x risk (book 30%). T2 = 3x risk (book 30%). Trail rest with EMA10.",
        ],
        "weights":{"Base Tightness":30,"52W Proximity":20,"Volume Dry-up":20,"EMA Stack":15,"Duration":10,"MACD":5},
    },
    "NO_SETUP": {
        "color":"#6b7280","icon":"⏳","name":"No Clear Setup",
        "tagline":"No tradeable pattern right now",
        "risk":"N/A","hold":"N/A","min_score":999,
        "sl_type":None,
        "description":"No swing trading pattern detected. The stock is between key levels without a clear edge.",
        "step_by_step":["WAIT. No trade is the best trade when there is no clear setup."],
        "weights":{},
    },
}

# ── INDICATORS ─────────────────────────────────────────────────────────────────
def enrich(df):
    df = df.copy()
    c  = df["Close"]
    for p in [10, 20, 50, 200]:
        df[f"E{p}"] = c.ewm(span=p, adjust=False).mean()
    df["V50"]  = df["Volume"].rolling(50).mean()
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=60).max()
    delta      = c.diff()
    gain       = delta.clip(lower=0).rolling(14).mean()
    loss       = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"]  = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12      = c.ewm(span=12, adjust=False).mean()
    ema26      = c.ewm(span=26, adjust=False).mean()
    ml         = ema12 - ema26
    df["MACD"] = ml
    df["HIST"] = ml - ml.ewm(span=9, adjust=False).mean()
    df["ATR"]  = (df["High"] - df["Low"]).rolling(14).mean()
    return df

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
def fetch_idx(t):
    try:
        df = yf.Ticker(t).history(period="6mo", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 30:
            return df.dropna(subset=["Close"])
    except:
        pass
    return None

def detect_setup(df):
    if len(df) < 30:
        return "NO_SETUP", {}
    l    = df.iloc[-1]
    p    = safe(l["Close"])
    e10  = safe(l["E10"]); e20=safe(l["E20"]); e50=safe(l["E50"]); e200=safe(l["E200"])
    h52  = safe(l["H52"], p)
    vr   = safe(l["VR"], 1.0)
    mac  = safe(l["MACD"]); hist=safe(l["HIST"])
    atr  = safe(l["ATR"], p * 0.02)
    c20  = df["Close"].tail(20); c7=df["Close"].tail(7)
    v10  = df["Volume"].tail(10).mean(); v50=df["Volume"].tail(50).mean()
    ph   = (h52 - p) / h52 * 100 if h52 > 0 else 100
    r20  = (c20.max() - c20.min()) / c20.mean() * 100 if c20.mean() > 0 else 100
    r7   = (c7.max() - c7.min()) / c7.mean() * 100 if c7.mean() > 0 else 100
    vr10 = v10 / v50 if v50 > 0 else 1.0
    mv20 = (c20.iloc[-1] - c20.iloc[0]) / c20.iloc[0] * 100 if c20.iloc[0] > 0 else 0
    emas = (p > e20) and (e20 > e50) and (e50 > e200)
    n20  = abs(p - e20) / p < 0.04 if p > 0 else False
    n50  = abs(p - e50) / p < 0.05 if p > 0 else False
    df6  = df.tail(126)
    lmx  = float(df6["High"].max()); lmn=float(df6["Low"].min())
    l1   = (lmx - lmn) / lmn * 100 if lmn > 0 else 0
    pidx = df6["High"].idxmax()
    aftr = df6.loc[pidx:]
    blow = float(aftr["Low"].min()) if len(aftr) > 3 else p
    bdp  = (lmx - blow) / lmx * 100 if lmx > 0 else 100
    p2p  = (lmx - p) / lmx * 100 if lmx > 0 else 100
    sd = dict(p=p, e10=e10, e20=e20, e50=e50, e200=e200,
              h52=h52, ph=ph, vr=vr, rsi=safe(l["RSI"], 50),
              mac=mac, hist=hist, atr=atr,
              r20=r20, r7=r7, vr10=vr10, mv20=mv20,
              emas=emas, n20=n20, n50=n50,
              l1=l1, bdp=bdp, blow=blow, p2p=p2p,
              fh=float(c7.max()),
              bh=float(df["High"].tail(20).max()),
              bl=float(df["Low"].tail(20).min()))
    if l1 >= 30 and bdp <= 30 and p2p <= 10 and emas and vr >= 1.2: return "SECOND_LEG", sd
    if ph <= 1.5 and vr >= 1.5 and emas:                            return "BREAKOUT",   sd
    if ph <= 12 and r20 < 15 and vr10 < 0.80 and e20 > e50 > e200: return "VCP",        sd
    if mv20 >= 12 and r7 < 6 and vr10 < 0.90 and p > e20:          return "BULL_FLAG",  sd
    if r20 < 10 and ph <= 18 and e20 > e50 > e200 and vr10 < 0.95: return "FLAT_BASE",  sd
    if e50 > e200:
        if n20 and e20 > e50: return "EMA_PULLBACK", sd
        if n50 and p > e200:  return "EMA_PULLBACK", sd
    return "NO_SETUP", sd

def score_setup(sname, sd, r6, r12, rs):
    meta   = SETUPS.get(sname, SETUPS["NO_SETUP"])
    w      = meta["weights"]
    scores = {}
    flags  = []

    p=sd.get("p",0); ph=sd.get("ph",100); vr=sd.get("vr",1)
    rsi_=sd.get("rsi",50); mac=sd.get("mac",0); hist=sd.get("hist",0)
    r20=sd.get("r20",100); r7=sd.get("r7",100); vr10=sd.get("vr10",1)
    mv20=sd.get("mv20",0); emas=sd.get("emas",False)
    e20=sd.get("e20",0); e50=sd.get("e50",0); e200=sd.get("e200",0)
    l1=sd.get("l1",0); bdp=sd.get("bdp",100)
    n20=sd.get("n20",False); n50=sd.get("n50",False)

    def add(key, pts, typ, label, val_str, expl):
        scores[key] = pts
        flags.append((typ, label, val_str, expl))

    if "EMA Stack" in w:
        mx = w["EMA Stack"]
        if p > e20 > e50 > e200:
            add("EMA Stack", mx, "bull", "EMA Stack", "Price > 20 > 50 > 200", "Full Stage 2 uptrend. All EMAs in bullish order. Best environment for momentum trades.")
        elif e20 > e50 > e200:
            add("EMA Stack", int(mx*.65), "warn", "EMA Stack", "EMAs aligned, price below EMA20", "EMAs are bullish but price dipped below EMA20. Wait for price to reclaim EMA20 before entering.")
        elif e20 > e50 or e50 > e200:
            add("EMA Stack", int(mx*.3), "warn", "EMA Stack", "Partial alignment only", "Stage 2 is still developing. Higher risk. Wait for all EMAs to align.")
        else:
            add("EMA Stack", 0, "bear", "EMA Stack", "Bearish order", "Stock in Stage 3 or 4 downtrend. Do not trade declining stocks.")

    if "52W Proximity" in w:
        mx = w["52W Proximity"]; s = str(round(ph,1)) + "%"
        if ph <= 0:    add("52W Proximity", mx,         "bull", "52W High", "AT / ABOVE", "No overhead resistance. Every seller from the past year is at profit. Maximum momentum signal.")
        elif ph <= 2:  add("52W Proximity", int(mx*.9), "bull", "52W High", s+" below",   "Breakout imminent. Set GTT alert at the 52W high level right now.")
        elif ph <= 5:  add("52W Proximity", int(mx*.75),"bull", "52W High", s+" below",   "Near breakout zone. Good setup stage — needs to actually break before entering.")
        elif ph <= 10: add("52W Proximity", int(mx*.5), "warn", "52W High", s+" below",   "In base formation territory. Could go either way.")
        elif ph <= 20: add("52W Proximity", int(mx*.25),"warn", "52W High", s+" below",   "Too far from ideal breakout zone for now. Watch but don't act.")
        else:          add("52W Proximity", 0,           "bear", "52W High", s+" below",   "More than 20% below the high. Not a momentum setup. Wait.")

    if "Volume Contraction" in w:
        mx = w["Volume Contraction"]; pv = str(round(vr10*100)) + "%"
        if vr10 < 0.40:   add("Volume Contraction", mx,         "bull", "Volume Contraction", pv+" of avg", "Deep contraction. Supply fully exhausted. The coil is tight. Breakout will be powerful.")
        elif vr10 < 0.60: add("Volume Contraction", int(mx*.8), "bull", "Volume Contraction", pv+" of avg", "Strong VCP signature. Institutions quietly accumulating.")
        elif vr10 < 0.75: add("Volume Contraction", int(mx*.55),"warn", "Volume Contraction", pv+" of avg", "Moderate drying. Not deep enough for a classic VCP yet. Watch daily.")
        else:              add("Volume Contraction", int(mx*.15),"bear", "Volume Contraction", pv+" of avg", "Volume not contracting enough for a proper VCP. Wait for more drying.")

    for key in ["Price Tightness", "Base Tightness"]:
        if key in w:
            mx = w[key]; s = str(round(r20,1)) + "%"
            if r20 < 5:    add(key, mx,         "bull", key, s+" 20D range", "Exceptional tightness. Spring fully wound. Breakouts from this tight tend to be explosive.")
            elif r20 < 8:  add(key, int(mx*.8), "bull", key, s+" 20D range", "Solid base tightness. Institutions holding without letting price move much.")
            elif r20 < 12: add(key, int(mx*.55),"warn", key, s+" 20D range", "Acceptable but not ideal. A tighter base would give more confidence.")
            elif r20 < 18: add(key, int(mx*.25),"warn", key, s+" 20D range", "Wide base. Lower institutional conviction. Risk of failed breakout is higher.")
            else:           add(key, 0,          "bear", key, s+" 20D range", "Too wide to be called a proper base. Wait for real consolidation.")

    if "Breakout Volume" in w:
        mx = w["Breakout Volume"]; s = str(round(vr,1)) + "x avg"
        if vr >= 4:    add("Breakout Volume", mx,         "bull", "Breakout Volume", s, "Exceptional. Institutions rushing in. Very high probability of follow-through.")
        elif vr >= 2.5:add("Breakout Volume", int(mx*.85),"bull", "Breakout Volume", s, "Strong institutional participation. Breakout has real conviction behind it.")
        elif vr >= 1.5:add("Breakout Volume", int(mx*.65),"bull", "Breakout Volume", s, "Meets minimum threshold. Watch next 2-3 sessions for confirmation.")
        elif vr >= 1:  add("Breakout Volume", int(mx*.3), "warn", "Breakout Volume", s, "Below average volume on breakout. Could be a fake-out. Be cautious.")
        else:          add("Breakout Volume", 0,           "bear", "Breakout Volume", s, "Very weak volume. High probability this breakout fails.")

    if "Pole Strength" in w:
        mx = w["Pole Strength"]; s = "+" + str(round(mv20,1)) + "%"
        if mv20 >= 35:   add("Pole Strength", mx,         "bull", "Pole Strength (20D move)", s, "Exceptional institutional move. Strong poles produce powerful second legs.")
        elif mv20 >= 22: add("Pole Strength", int(mx*.85),"bull", "Pole Strength (20D move)", s, "Solid bull flag pole. Flag should resolve upward.")
        elif mv20 >= 12: add("Pole Strength", int(mx*.6), "warn", "Pole Strength (20D move)", s, "Moderate. Follow-through from the flag may be smaller.")
        else:            add("Pole Strength", 0,           "bear", "Pole Strength (20D move)", s, "Too weak for a reliable bull flag.")

    if "Flag Tightness" in w:
        mx = w["Flag Tightness"]; s = str(round(r7,1)) + "%"
        if r7 < 3:   add("Flag Tightness", mx,         "bull", "Flag Tightness (7D range)", s, "Very tight flag. Institutions not selling at all. High probability breakout setup.")
        elif r7 < 5: add("Flag Tightness", int(mx*.85),"bull", "Flag Tightness (7D range)", s, "Good flag tightness. Orderly consolidation after the pole move.")
        elif r7 < 8: add("Flag Tightness", int(mx*.55),"warn", "Flag Tightness (7D range)", s, "A bit wide. Use a tighter stop when entering.")
        else:        add("Flag Tightness", 0,           "bear", "Flag Tightness (7D range)", s, "Too wide to be a proper flag. Risk of full pole retracement.")

    if "Volume Pattern" in w:
        mx = w["Volume Pattern"]
        if vr10 < 0.55 and vr >= 1.5:
            add("Volume Pattern", mx,         "bull", "Volume Pattern", "High pole / Low flag", "Textbook bull flag. High volume on pole, low on flag = institutions holding, not selling.")
        elif vr10 < 0.75:
            add("Volume Pattern", int(mx*.65),"warn", "Volume Pattern", "Partially drying",     "Volume drying somewhat during flag. Decent but not perfect.")
        else:
            add("Volume Pattern", int(mx*.2), "bear", "Volume Pattern", "Volume elevated",      "Volume too high during flag. Could be distribution happening.")

    if "Pullback Quality" in w:
        mx = w["Pullback Quality"]
        if n20 and vr10 < 0.70:
            add("Pullback Quality", mx,         "bull", "Pullback Quality", "At EMA20, low volume", "Ideal Minervini entry. Stock at EMA20 with drying volume — perfect dip.")
        elif n20:
            add("Pullback Quality", int(mx*.7), "warn", "Pullback Quality", "At EMA20, vol OK",    "At EMA20 but volume not drying as much as ideal. Still tradeable.")
        elif n50 and vr10 < 0.80:
            add("Pullback Quality", int(mx*.55),"warn", "Pullback Quality", "At EMA50, low vol",   "Deeper dip to EMA50. Tradeable but stop will be wider.")
        else:
            add("Pullback Quality", int(mx*.2), "bear", "Pullback Quality", "Not at clean EMA",    "Not at a clean EMA level. No good stop anchor. Wait for price to reach EMA20.")

    if "Volume on Dip" in w:
        mx = w["Volume on Dip"]; pv = str(round(vr10*100)) + "%"
        if vr10 < 0.50:   add("Volume on Dip", mx,         "bull", "Volume on Dip", pv+" of avg", "Excellent. Nobody is panic-selling. Natural, healthy dip — institutions holding.")
        elif vr10 < 0.70: add("Volume on Dip", int(mx*.8), "bull", "Volume on Dip", pv+" of avg", "Good. Selling is light and orderly — profit-taking, not distribution.")
        elif vr10 < 0.85: add("Volume on Dip", int(mx*.5), "warn", "Volume on Dip", pv+" of avg", "Somewhat elevated. Keep watching. Volume should dry up more.")
        else:              add("Volume on Dip", int(mx*.15),"bear", "Volume on Dip", pv+" of avg", "High volume on dip = someone selling aggressively. Not a clean pullback.")

    if "First Leg" in w:
        mx = w["First Leg"]; s = "+" + str(int(l1)) + "%"
        if l1 >= 70:   add("First Leg", mx,         "bull", "First Leg Move", s, "Major institutional stock. Very powerful second leg expected after moves this big.")
        elif l1 >= 45: add("First Leg", int(mx*.85),"bull", "First Leg Move", s, "Strong. Good foundation for a solid second leg.")
        elif l1 >= 28: add("First Leg", int(mx*.6), "warn", "First Leg Move", s, "Moderate first leg. Second leg may be smaller in proportion.")
        else:          add("First Leg", 0,           "bear", "First Leg Move", s, "Too small to qualify for a second-leg setup. Need 30%+ first move.")

    if "Base Quality" in w:
        mx = w["Base Quality"]; s = str(round(bdp,1)) + "% deep"
        if bdp <= 12:   add("Base Quality", mx,         "bull", "Base Quality", s, "Exceptional — institutions barely sold any holdings. Tight = highest conviction.")
        elif bdp <= 20: add("Base Quality", int(mx*.8), "bull", "Base Quality", s, "Good — bulk of position intact. Solid quality base.")
        elif bdp <= 30: add("Base Quality", int(mx*.55),"warn", "Base Quality", s, "Some distribution occurred. Second leg may be smaller.")
        else:           add("Base Quality", 0,           "bear", "Base Quality", s, "Too deep. Institutions likely took most profits. Not a tight second-leg base.")

    if "Volume Dry-up" in w:
        mx = w["Volume Dry-up"]; pv = str(round(vr10*100)) + "%"
        if vr10 < 0.55:   add("Volume Dry-up", mx,         "bull", "Volume Dry-up", pv+" of avg", "Near-complete supply exhaustion. Very high quality flat base.")
        elif vr10 < 0.70: add("Volume Dry-up", int(mx*.75),"bull", "Volume Dry-up", pv+" of avg", "Volume declining nicely. Healthy flat base behavior.")
        elif vr10 < 0.85: add("Volume Dry-up", int(mx*.45),"warn", "Volume Dry-up", pv+" of avg", "Partially drying. Base quality would improve with more volume reduction.")
        else:              add("Volume Dry-up", int(mx*.1), "bear", "Volume Dry-up", pv+" of avg", "Volume not drying. Could be distribution disguised as consolidation.")

    if "Duration" in w:
        mx = w["Duration"]
        if vr10 < 0.90:
            add("Duration", mx,         "bull", "Base Duration", "Adequate", "Base has lasted long enough to clear overhead supply. 3+ weeks is the minimum.")
        else:
            add("Duration", int(mx*.4), "warn", "Base Duration", "May be short", "Base may not have lasted long enough. Ideal flat bases take 3-6 weeks.")

    if "RSI" in w:
        mx = w["RSI"]; s = str(round(rsi_))
        if 50 <= rsi_ <= 65:    add("RSI", mx,         "bull", "RSI", s+" (Sweet Spot)",    "RSI 50-65 is ideal. Strong enough to show uptrend, plenty of room to run before overbought.")
        elif 45 <= rsi_ < 50:   add("RSI", int(mx*.65),"warn", "RSI", s+" (Recovering)",    "Just below 50. Momentum recovering. Needs to clear 50 to confirm uptrend.")
        elif 65 < rsi_ <= 72:   add("RSI", int(mx*.55),"warn", "RSI", s+" (Near Overbought)","Approaching overbought zone. A 1-3 day pullback may happen before continuation.")
        elif 72 < rsi_ <= 80:   add("RSI", int(mx*.2), "warn", "RSI", s+" (Overbought)",    "Overbought. Short-term pullback likely. Better to wait for RSI to cool to 55-65.")
        elif rsi_ > 80:         add("RSI", 0,           "bear", "RSI", s+" (Extreme OB)",    "Very overbought. High probability of a sharp pullback. Missing this = smart.")
        else:                   add("RSI", 0,           "bear", "RSI", s+" (Downtrend)",     "RSI below 45 = downtrend momentum. Avoid.")

    if "MACD" in w:
        mx = w["MACD"]
        if mac > 0 and hist > 0:  add("MACD", mx,         "bull", "MACD", "Positive + Expanding", "Best state. Momentum accelerating upward, not topping out.")
        elif mac > 0:             add("MACD", int(mx*.65),"warn", "MACD", "Positive, slowing",    "Positive but decelerating. Still acceptable. Watch for expansion.")
        elif -0.5 < mac <= 0:     add("MACD", int(mx*.3), "warn", "MACD", "Near zero",            "Near the zero line. Watch for a bullish crossover above zero.")
        else:                     add("MACD", 0,           "bear", "MACD", "Negative",             "Bearish momentum. Wait for MACD to recover above zero before entering.")

    if "RS vs Nifty" in w:
        mx = w["RS vs Nifty"]
        if rs is None:
            scores["RS vs Nifty"] = int(mx * .5)
            flags.append(("warn", "RS vs Nifty", "No data", "Cannot calculate relative strength."))
        elif rs >= 20:   add("RS vs Nifty", mx,         "bull", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Massive outperformer. FIIs and institutions heavily overweight this stock.")
        elif rs >= 10:   add("RS vs Nifty", int(mx*.85),"bull", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Strong outperformer. Market leader. Will lead when market rallies.")
        elif rs >= 3:    add("RS vs Nifty", int(mx*.65),"warn", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Marginally outperforming. Not yet a clear leader.")
        elif rs >= 0:    add("RS vs Nifty", int(mx*.35),"warn", "RS vs Nifty", "+" + str(round(rs,1)) + "%", "Matching the index. Leaders outperform by 10%+.")
        else:            add("RS vs Nifty", 0,           "bear", "RS vs Nifty", str(round(rs,1)) + "%",       "Underperforming market. Will fall harder when market dips.")

    raw = sum(scores.values())
    return scores, flags, raw

def make_trade(sname, sd, raw, capital, risk_pct, regime_pen):
    meta  = SETUPS.get(sname, SETUPS["NO_SETUP"])
    final = max(0, raw - regime_pen)
    if sname == "NO_SETUP":
        return {"ok":False,"final":0,"verdict":"NO SETUP","vc":"#6b7280",
                "reason":"No swing trading pattern detected on this stock right now. The stock is between key levels without a clear entry trigger. Watch daily and wait for a VCP, Breakout, Flag, Pullback, or Base to form."}
    if final < meta["min_score"]:
        return {"ok":False,"final":final,"verdict":"BELOW MINIMUM","vc":"#ef4444",
                "reason":"Score " + str(final) + " is below minimum " + str(meta["min_score"]) + " required for a " + meta["name"] + " trade. Setup detected but quality insufficient — wait for it to improve."}
    if final >= 90:   verdict, vc = "ELITE SETUP",  "#10b981"
    elif final >= 78: verdict, vc = "STRONG SETUP", "#3b82f6"
    elif final >= 65: verdict, vc = "TRADABLE",     "#f59e0b"
    else:             verdict, vc = "BELOW MINIMUM","#ef4444"
    p=sd["p"]; e10=sd["e10"]; e20=sd["e20"]; e50=sd["e50"]
    h52=sd["h52"]; fh=sd["fh"]; bh=sd["bh"]; bl=sd["bl"]; blow=sd["blow"]; n20=sd["n20"]
    sl_type = meta["sl_type"]
    if sl_type == "ema10":    sl=e10*.99;    sl_l="1% below EMA10 (" + fmt_rs(e10) + ")"
    elif sl_type == "ema20":  sl=e20*.99;    sl_l="1% below EMA20 (" + fmt_rs(e20) + ")"
    elif sl_type == "flag_low": sl=bl*.995;  sl_l="Below flag low (" + fmt_rs(bl) + ")"
    elif sl_type == "base_low": sl=blow*.99; sl_l="1% below base low (" + fmt_rs(blow) + ")"
    else:                     sl=p*.95;      sl_l="5% mechanical stop"
    sl_pct = (p - sl) / p * 100 if p > 0 else 5
    if sl_pct > 6: sl=p*.94; sl_pct=6.0; sl_l="6% cap applied (logical SL was too wide)"
    if sname in ("BREAKOUT","VCP"):
        ea=p; ec=round(h52*1.005,1); er=round(h52*.99,1)
        note = "Entry above " + fmt_rs(h52) + ". Aggressive: buy now. Conservative: wait for daily close above " + fmt_rs(ec) + " on 1.5x+ volume. Retest entry: if price dips to " + fmt_rs(er) + " and holds."
    elif sname == "BULL_FLAG":
        ea=fh; ec=round(fh*1.01,1); er=round(fh*.995,1)
        note = "Entry above flag high " + fmt_rs(fh) + " only. Do NOT buy inside the flag. Aggressive: buy as price breaks " + fmt_rs(fh) + ". Conservative: next candle after confirmed breakout close."
    elif sname == "EMA_PULLBACK":
        te=e20 if n20 else e50; en="EMA20" if n20 else "EMA50"
        ea=round(te*1.002,1); ec=round(te*1.01,1); er=round(te*.998,1)
        note = en + " pullback at " + fmt_rs(te) + ". Aggressive: buy as price reclaims " + fmt_rs(ea) + ". Conservative: first green candle closing above " + en + "."
    else:
        ea=bh; ec=round(bh*1.01,1); er=round(bh*.995,1)
        note = "Entry on break above base high " + fmt_rs(bh) + " with 1.5x+ volume. Aggressive: buy on breakout candle. Conservative: wait for volume confirmation."
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

def get_regime(ndf, bndf):
    rows=[]; pen=0
    for name,df in [("Nifty 50",ndf),("Bank Nifty",bndf)]:
        if df is None or len(df)<30:
            rows.append((name,"UNKNOWN","⚪",0)); continue
        d=enrich(df); p=safe(d["Close"].iloc[-1])
        e50=safe(d["E50"].iloc[-1]); e200=safe(d["E200"].iloc[-1])
        if p<e200:    rows.append((name,"BEARISH","🔴",20)); pen=max(pen,20)
        elif p<e50:   rows.append((name,"CAUTION","🟠",10)); pen=max(pen,10)
        else:         rows.append((name,"HEALTHY","🟢",0))
    return rows, pen

# ── RENDER HELPERS (minimal HTML for cards only) ───────────────────────────────
def score_card(score, verdict, color, sub):
    """Big score display card"""
    st.markdown(
        "<div style='background:#111827;border:2px solid " + color + "40;border-radius:16px;"
        "padding:28px 24px;text-align:center;margin-bottom:16px;'>"
        "<div style='font-size:80px;font-weight:800;color:" + color + ";line-height:1;font-family:monospace;'>"
        + str(score) + "</div>"
        "<div style='font-size:11px;color:#6b7280;margin-top:4px;margin-bottom:14px;'>OUT OF 100</div>"
        "<div style='display:inline-block;background:" + color + "20;color:" + color + ";"
        "border:1px solid " + color + "50;border-radius:8px;padding:6px 20px;"
        "font-size:14px;font-weight:800;letter-spacing:0.5px;'>" + verdict + "</div>"
        "<div style='color:#9ca3af;font-size:11px;margin-top:10px;'>" + sub + "</div>"
        "</div>",
        unsafe_allow_html=True
    )

def setup_badge(sname):
    meta = SETUPS[sname]
    col  = meta["color"]
    st.markdown(
        "<div style='background:#111827;border:2px solid " + col + "50;border-left:5px solid " + col + ";"
        "border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:16px;'>"
        "<div style='font-size:22px;font-weight:800;color:" + col + ";margin-bottom:4px;'>"
        + meta["icon"] + "  " + meta["name"].upper() + "</div>"
        "<div style='color:#9ca3af;font-size:14px;margin-bottom:8px;'>" + meta["tagline"] + "</div>"
        "<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
        "<span style='color:#6b7280;font-size:12px;'>⏱ Hold: <b style='color:#d0d7e3;'>" + meta["hold"] + "</b></span>"
        "<span style='color:#6b7280;font-size:12px;'>🎯 Risk: <b style='color:" + col + ";'>" + meta["risk"] + "</b></span>"
        "<span style='color:#6b7280;font-size:12px;'>📊 Min score: <b style='color:#d0d7e3;'>" + str(meta["min_score"]) + "/100</b></span>"
        "</div></div>",
        unsafe_allow_html=True
    )

def signal_row(typ, label, val, desc):
    icons = {"bull":"▲","warn":"◆","bear":"▼"}
    cols  = {"bull":"#10b981","warn":"#f59e0b","bear":"#ef4444"}
    c = cols.get(typ,"#6b7280"); i = icons.get(typ,"•")
    st.markdown(
        "<div style='display:flex;gap:12px;padding:9px 14px;background:#0a0e1a;"
        "border:1px solid " + c + "20;border-left:3px solid " + c + ";"
        "border-radius:0 8px 8px 0;margin-bottom:5px;'>"
        "<span style='color:" + c + ";font-weight:700;font-size:13px;min-width:14px;'>" + i + "</span>"
        "<div><span style='color:#d0d7e3;font-size:12px;font-weight:600;'>" + label + ": </span>"
        "<span style='color:" + c + ";font-size:12px;font-weight:700;'>" + val + "</span>"
        "<div style='color:#6b7280;font-size:11px;margin-top:2px;line-height:1.4;'>" + desc + "</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

def level_card(label, value, color, sub=""):
    sub_html = "<div style='color:#6b7280;font-size:10px;margin-top:3px;'>" + sub + "</div>" if sub else ""
    st.markdown(
        "<div style='background:#0a0e1a;border:1px solid " + color + "30;border-radius:10px;padding:12px;'>"
        "<div style='color:#6b7280;font-size:10px;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;'>" + label + "</div>"
        "<div style='color:" + color + ";font-size:15px;font-weight:800;font-family:monospace;'>" + value + "</div>"
        + sub_html + "</div>",
        unsafe_allow_html=True
    )

def pbar(label, score, max_pts):
    pct = min(int(score/max_pts*100),100) if max_pts>0 else 0
    col = "#10b981" if pct>=75 else "#f59e0b" if pct>=50 else "#ef4444"
    sym = "✓" if pct>=75 else "~" if pct>=50 else "✗"
    st.markdown(
        "<div style='margin-bottom:8px;'>"
        "<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
        "<span style='color:#d0d7e3;font-size:12px;'>" + label + "</span>"
        "<span style='color:" + col + ";font-size:12px;font-weight:700;'>" + sym + " " + str(score) + "/" + str(max_pts) + "</span>"
        "</div><div style='height:4px;background:#1f2937;border-radius:2px;overflow:hidden;'>"
        "<div style='height:100%;width:" + str(pct) + "%;background:" + col + ";border-radius:2px;'></div>"
        "</div></div>",
        unsafe_allow_html=True
    )

def step_card(num, text, done=False):
    col = "#10b981" if done else "#3b82f6"
    bg  = "#0b1a12" if done else "#0c1525"
    st.markdown(
        "<div style='display:flex;gap:12px;align-items:flex-start;background:" + bg + ";"
        "border:1px solid " + col + "30;border-radius:10px;padding:12px 16px;margin-bottom:8px;'>"
        "<div style='background:" + col + ";color:#0a0e1a;font-size:11px;font-weight:800;"
        "border-radius:50%;width:24px;height:24px;display:flex;align-items:center;"
        "justify-content:center;flex-shrink:0;'>" + str(num) + "</div>"
        "<div style='color:#d0d7e3;font-size:13px;line-height:1.5;padding-top:3px;'>" + text + "</div>"
        "</div>",
        unsafe_allow_html=True
    )

def info_card(text, color="#3b82f6"):
    st.markdown(
        "<div style='background:" + color + "10;border:1px solid " + color + "30;"
        "border-radius:10px;padding:14px 16px;margin-bottom:12px;'>"
        "<div style='color:#d0d7e3;font-size:13px;line-height:1.6;'>" + text + "</div></div>",
        unsafe_allow_html=True
    )

# ── ANALYSE ONE STOCK ──────────────────────────────────────────────────────────
def analyse_stock(sym, cap, rsk, regime_pen, nifty_df):
    df_raw, ticker = fetch_stock(sym)
    if df_raw is None:
        return None, "Could not fetch '" + sym + "'. Check the NSE ticker symbol."
    df   = enrich(df_raw)
    r6, r12, rs    = get_rets(df, nifty_df)
    sname, sd      = detect_setup(df)
    sc, flags, raw = score_setup(sname, sd, r6, r12, rs)
    tp             = make_trade(sname, sd, raw, cap, rsk, regime_pen)
    l  = df.iloc[-1]
    p  = safe(l["Close"]); pv=safe(df["Close"].iloc[-2])
    dchg = (p-pv)/pv*100 if pv>0 else 0
    avg_vol  = df["Volume"].tail(50).mean()
    to       = avg_vol * p
    h52 = safe(l["H52"],p); e20=safe(l["E20"]); e50=safe(l["E50"]); e200=safe(l["E200"])
    vr_ = safe(l["VR"],1); rsi_=safe(l["RSI"],50)
    # spike
    if abs(dchg)>=10:   sp=-20; sp_msg="🚨 SPIKE: +" + str(round(abs(dchg),1)) + "% today — spike penalty -20 pts. Do NOT chase."
    elif abs(dchg)>=8:  sp=-10; sp_msg="⚠️ BIG MOVE: +" + str(round(abs(dchg),1)) + "% — -10 pts. Wait next session."
    elif abs(dchg)>=5:  sp=-5;  sp_msg="ℹ️ MOVE: +" + str(round(abs(dchg),1)) + "% — -5 pts. Prefer next day entry."
    else:                sp=0;   sp_msg=""
    final = max(0, tp.get("final", raw-regime_pen) + sp)
    result = dict(
        ticker=ticker, sym=sym, df=df, sd=sd, sname=sname,
        sc=sc, flags=flags, raw=raw, tp=tp, r6=r6, r12=r12, rs=rs,
        p=p, dchg=dchg, to=to, h52=h52, e20=e20, e50=e50, e200=e200,
        vr_=vr_, rsi_=rsi_, sp=sp, sp_msg=sp_msg, final=final,
        ph=(h52-p)/h52*100 if h52>0 else 0,
    )
    return result, None

def render_result(res, regime_pen):
    sname = res["sname"]; meta = SETUPS[sname]; color = meta["color"]
    tp    = res["tp"]; sc=res["sc"]; flags=res["flags"]; final=res["final"]
    p     = res["p"]; dchg=res["dchg"]

    # Stock header
    d_sign = "+" if dchg >= 0 else ""
    d_col  = "#10b981" if dchg >= 0 else "#ef4444"
    st.markdown(
        "<div style='background:#111827;border:1px solid #1f2937;border-radius:12px;"
        "padding:16px 20px;margin-bottom:16px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;'>"
        "<div>"
        "<div style='color:#6b7280;font-size:11px;font-weight:700;letter-spacing:1px;'>"
        + res["ticker"] + "  ·  " + res["df"].index[-1].strftime("%d %b %Y") + "  ·  Turnover Rs." + str(round(res["to"]/1e7,1)) + " Cr/day</div>"
        "<div style='color:#f0f6ff;font-size:28px;font-weight:800;font-family:monospace;margin-top:4px;'>Rs." + "{:,.2f}".format(p) + "</div>"
        "</div>"
        "<div style='text-align:right;'>"
        "<div style='color:" + d_col + ";font-size:18px;font-weight:700;font-family:monospace;'>" + d_sign + str(round(dchg,2)) + "% today</div>"
        "<div style='color:#374151;font-size:11px;margin-top:4px;'>6M: " + fmt_pct(res["r6"]) + "  ·  12M: " + fmt_pct(res["r12"]) + "  ·  RS vs Nifty: " + fmt_pct(res["rs"]) + "</div>"
        "</div></div></div>",
        unsafe_allow_html=True
    )

    if res["sp_msg"]:
        st.warning(res["sp_msg"])

    # Two-column: score + setup info
    col_a, col_b = st.columns([1, 2], gap="large")

    with col_a:
        vc = tp.get("vc","#6b7280"); verdict = tp.get("verdict","—")
        rp_s = "Regime: -" + str(regime_pen) + "  " if regime_pen > 0 else ""
        sp_s = "  Spike: " + str(res["sp"]) if res["sp"] < 0 else ""
        display_score = 0 if sname == "NO_SETUP" else final
        score_label = "No pattern detected" if sname == "NO_SETUP" else "Raw " + str(res["raw"]) + "  →  " + rp_s + sp_s + "  Final: " + str(final)
        score_card(display_score, verdict, vc, score_label)

        # Verdict explanation
        if sname == "NO_SETUP":
            st.info("**NO SETUP DETECTED** — This stock is not forming any of the 6 tradeable swing patterns right now. Watch it daily. Check again tomorrow.")
        elif final >= 90:
            st.success("**ELITE** — Rare high-quality setup. Full position size. Act with confidence.")
        elif final >= 78:
            st.info("**STRONG** — High-probability trade. Use full 1% risk.")
        elif final >= 65:
            st.warning("**TRADABLE** — Setup is valid but marginal. Use 0.5% risk only.")
        else:
            st.error("**BELOW MINIMUM** — Setup detected but score too low. Wait for quality to improve.")

        st.divider()

        # Key data in compact form
        st.markdown("**Key Data**")
        ph = res["ph"]
        items = [
            ("52W High",   fmt_rs(res["h52"]),              "#10b981" if ph<=3 else "#f59e0b" if ph<=10 else "#ef4444"),
            ("Below High", str(round(ph,1)) + "%",          "#10b981" if ph<=3 else "#f59e0b" if ph<=10 else "#ef4444"),
            ("EMA 20",     fmt_rs(res["e20"]),               "#10b981" if p>res["e20"] else "#ef4444"),
            ("EMA 50",     fmt_rs(res["e50"]),               "#10b981" if res["e20"]>res["e50"] else "#ef4444"),
            ("EMA 200",    fmt_rs(res["e200"]),              "#10b981" if res["e50"]>res["e200"] else "#ef4444"),
            ("Volume",     str(round(res["vr_"],1))+"x avg","#10b981" if res["vr_"]>=1.5 else "#f59e0b" if res["vr_"]>=1 else "#ef4444"),
            ("RSI",        str(round(res["rsi_"])),         "#10b981" if 50<=res["rsi_"]<=65 else "#f59e0b" if res["rsi_"]<80 else "#ef4444"),
        ]
        for lbl, val, col in items:
            st.markdown(
                "<div style='display:flex;justify-content:space-between;padding:5px 0;"
                "border-bottom:1px solid #1f2937;'>"
                "<span style='color:#6b7280;font-size:12px;'>" + lbl + "</span>"
                "<span style='color:" + col + ";font-size:12px;font-weight:700;font-family:monospace;'>" + val + "</span>"
                "</div>",
                unsafe_allow_html=True
            )

    with col_b:
        setup_badge(sname)
        info_card("<b>What is this setup?</b><br>" + meta["description"])

        # Step-by-step
        st.markdown("**📋 Step-by-Step Action Plan**")
        for i, step in enumerate(meta["step_by_step"], 1):
            step_card(i, step)

    st.divider()

    # Score breakdown
    st.markdown("#### Score Breakdown")
    if sname == "NO_SETUP":
        st.info("No scoring breakdown available. A breakdown is only shown when a pattern is detected. This stock needs to form a VCP, Breakout, Flag, Pullback, or Base first.")
    else:
        cols_pb = st.columns(2)
        w = meta["weights"]
        keys = list(w.keys())
        half = (len(keys)+1)//2
        for i, key in enumerate(keys):
            with cols_pb[0 if i < half else 1]:
                pbar(key, sc.get(key,0), w[key])

    st.divider()

    # Signals
    st.markdown("#### Signal Analysis")
    if sname == "NO_SETUP":
        st.info("No signals to display. Signals are generated only when a setup pattern is detected. Check back when the stock forms a recognisable pattern.")
    else:
        bull=[f for f in flags if f[0]=="bull"]
        warn=[f for f in flags if f[0]=="warn"]
        bear=[f for f in flags if f[0]=="bear"]
        fc1,fc2,fc3 = st.columns(3)
        with fc1:
            st.markdown("\u2705 **Bullish (" + str(len(bull)) + ")**")
            for _,l,v,d in bull: signal_row("bull",l,v,d)
        with fc2:
            st.markdown("\u26a0\ufe0f **Caution (" + str(len(warn)) + ")**")
            for _,l,v,d in warn: signal_row("warn",l,v,d)
        with fc3:
            st.markdown("\u274c **Bearish (" + str(len(bear)) + ")**")
            for _,l,v,d in bear: signal_row("bear",l,v,d)

    st.divider()

    # Trade Plan
    if tp.get("ok"):
        st.markdown("#### Trade Plan")
        info_card("📌 <b>HOW TO ENTER:</b> " + tp["note"])

        c1,c2,c3,c4 = st.columns(4)
        with c1: level_card("AGGRESSIVE ENTRY", fmt_rs(tp["ea"]), "#3b82f6", "Enter now / at open")
        with c2: level_card("CONSERVATIVE ENTRY", fmt_rs(tp["ec"]), "#60a5fa", "Wait for confirmation")
        with c3: level_card("STOP LOSS  " + str(tp["sl_pct"]) + "%", fmt_rs(tp["sl"]), "#ef4444", tp["sl_l"])
        with c4: level_card("RETEST ENTRY", fmt_rs(tp["er"]), "#6b7280", "If price dips back")

        st.markdown("")
        t1,t2,t3 = st.columns(3)
        with t1: level_card("TARGET 1  +" + str(tp["t1p"]) + "%", fmt_rs(tp["t1"]), "#f59e0b", "Book 30% · Move stop to entry · Trade is risk-free")
        with t2: level_card("TARGET 2  +" + str(tp["t2p"]) + "%", fmt_rs(tp["t2"]), "#10b981", "Book 30% · Move stop to T1 level")
        with t3: level_card("TARGET 3  +" + str(tp["t3p"]) + "%", fmt_rs(tp["t3"]), "#34d399", "Trail remaining 40% with EMA10")

        st.markdown("")
        pa,pb = st.columns(2)
        with pa:
            st.metric("Risk : Reward", "1 : " + str(tp["rr"]), delta="Minimum 3:1 ✓")
        with pb:
            st.metric("Position Size (" + str(round(tp["ra"]/tp["pv"]*100,1) if tp["pv"]>0 else 0) + "% of capital)",
                      str(tp["qty"]) + " shares  =  Rs." + "{:,}".format(tp["pv"]),
                      delta="Max risk: Rs." + "{:,}".format(tp["ra"]))

        st.divider()
        st.markdown("#### Exit Rules")
        for i, (title, desc) in enumerate([
            ("Place GTT stop immediately after entry", "The second your order fills — place GTT stop at Rs." + str(tp["sl"]) + ". Not later. Not tomorrow. Right now. A trade without a stop is gambling."),
            ("At Target 1 (Rs." + str(tp["t1"]) + ")", "Book 30% of your position. Then move your stop up to your entry price. The trade is now completely risk-free."),
            ("At Target 2 (Rs." + str(tp["t2"]) + ")", "Book another 30%. Move stop up to T1 level. Let the last 40% run for the big move."),
            ("Trail the last 40%", "Move stop up to 1% below EMA10 (currently Rs." + str(tp["e10"]) + ") after each higher close. Never move the stop down."),
            ("Hard stop — no debate", "If price closes below Rs." + str(tp["sl"]) + " at any point — exit the entire position next morning. No averaging down. No hoping."),
            ("Time stop", "No meaningful price movement after 15 trading days? Exit and redeploy capital elsewhere."),
            ("Exit before events", "Always exit 1 day before: quarterly results, RBI policy meeting, Budget. Holding through these events on a swing trade is speculation."),
        ], 1):
            step_card(i, "<b>" + title + ":</b> " + desc)
    else:
        if sname == "NO_SETUP":
            st.info("**NO SETUP DETECTED** — " + tp.get("reason","No pattern found."))
        else:
            st.error("**BELOW MINIMUM — " + tp.get("reason", "Score below minimum for this setup. Wait for quality to improve."))

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Header
    st.markdown(
        "<div style='background:#111827;border-bottom:2px solid #1f2937;padding:12px 0;margin-bottom:16px;'>"
        "<span style='color:#60a5fa;font-size:20px;font-weight:800;letter-spacing:0.5px;'>📈 NSE SWING ADVISOR</span>"
        "<span style='color:#374151;font-size:13px;margin-left:14px;'>" + datetime.now().strftime("%a %d %b %Y") + "</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # Market regime
    with st.spinner("Loading market data..."):
        nifty_df  = fetch_idx("^NSEI")
        bnifty_df = fetch_idx("^NSEBANK")
        vix_df    = fetch_idx("^INDIAVIX")

    regime_rows, regime_pen = get_regime(nifty_df, bnifty_df)
    vix_val = safe(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df) > 0 else None

    rc = st.columns(5)
    for i,(name,status,dot,pen) in enumerate(regime_rows):
        with rc[i]:
            st.metric(name, dot + " " + status,
                      delta="-" + str(pen) + " pts" if pen > 0 else "Full scoring",
                      delta_color="inverse" if pen > 0 else "off")
    with rc[2]:
        if vix_val:
            vs = "LOW ✅" if vix_val<15 else "ELEVATED ⚠️" if vix_val<20 else "HIGH 🔴"
            st.metric("India VIX", str(round(vix_val,1)), delta=vs, delta_color="off")
    with rc[3]:
        st.metric("Regime Penalty", "-" + str(regime_pen) + " pts to all scores",
                  delta_color="inverse" if regime_pen > 0 else "off")

    if regime_pen >= 20:
        st.error("🚫 CAPITAL PRESERVATION MODE — Nifty is below its 200 EMA. Market is in a confirmed bearish phase. Only setups scoring 85+ qualify. Cut all position sizes by 50%.")
    elif regime_pen >= 10:
        st.warning("⚠️ CAUTION — Market below 50 EMA. Use half position sizes. Prefer EMA pullback setups. No new breakout entries on red days.")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚡  Analyze Stock",
        "📦  My Portfolio",
        "📚  Setup Guide",
        "📡  Chartink Scanners",
        "📋  Trading Rules",
    ])

    # ══ TAB 1: ANALYZE ════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Analyze Any NSE Stock")
        info_card("Enter any NSE stock symbol below. The app will detect which swing trading setup it is currently forming, score it out of 100, and give you exact entry, stop loss, and target levels with a step-by-step action plan.")

        c1,c2,c3,c4 = st.columns([2,1.5,1,1])
        with c1:
            sym  = st.text_input("NSE Symbol", placeholder="e.g. AKUMS, BEL, TCS").upper().strip()
            pick = st.selectbox("Or pick from popular list", [""]+POPULAR)
            if pick and not sym: sym = pick
        with c2:
            cap = st.number_input("Capital (Rs.)", min_value=50000, max_value=10000000, value=300000, step=50000, format="%d")
        with c3:
            rsk = st.slider("Risk %", 0.5, 2.0, 1.0, 0.25, help="0.5% on expiry/high VIX days")
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            go = st.button("⚡ Analyze", use_container_width=True)

        if go and sym:
            with st.spinner("Fetching " + sym + " from NSE..."):
                res, err = analyse_stock(sym, cap, rsk, regime_pen, nifty_df)
            if err:
                st.error(err)
            else:
                render_result(res, regime_pen)
        elif go and not sym:
            st.warning("Please enter a stock symbol.")

    # ══ TAB 2: PORTFOLIO ══════════════════════════════════════════════════════
    with tab2:
        st.markdown("### My Portfolio — Analyze Stocks You Hold")
        info_card("Add stocks you currently hold. The app will analyze each one and tell you: Is it still in a good setup? Should you hold, trail your stop, or exit? What is the current score?")

        # Session state for portfolio
        if "portfolio" not in st.session_state:
            st.session_state.portfolio = []

        # Add stock
        st.markdown("#### Add a Stock")
        pa,pb,pc,pd,pe = st.columns([2,1.5,1.5,1,1])
        with pa: p_sym  = st.text_input("Symbol", placeholder="e.g. BEL", key="p_sym").upper().strip()
        with pb: p_qty  = st.number_input("Qty held", min_value=1, value=100, key="p_qty")
        with pc: p_avg  = st.number_input("Avg buy price (Rs.)", min_value=1.0, value=500.0, step=0.5, key="p_avg")
        with pd: p_sl   = st.number_input("Your SL (Rs.)", min_value=1.0, value=480.0, step=0.5, key="p_sl")
        with pe:
            st.markdown("<br>", unsafe_allow_html=True)
            add_btn = st.button("➕ Add", use_container_width=True)

        if add_btn and p_sym:
            exists = any(h["sym"] == p_sym for h in st.session_state.portfolio)
            if exists:
                st.warning(p_sym + " is already in your portfolio.")
            else:
                st.session_state.portfolio.append({"sym":p_sym,"qty":p_qty,"avg":p_avg,"sl":p_sl})
                st.success("Added " + p_sym + " to portfolio.")

        if st.session_state.portfolio:
            st.divider()
            st.markdown("#### Portfolio Holdings")

            # Remove option
            rm_sym = st.selectbox("Remove a stock", [""]+[h["sym"] for h in st.session_state.portfolio], key="rm_sym")
            if rm_sym:
                if st.button("🗑 Remove " + rm_sym):
                    st.session_state.portfolio = [h for h in st.session_state.portfolio if h["sym"] != rm_sym]
                    st.rerun()

            scan_all = st.button("🔍 Analyze All Holdings", use_container_width=False)
            if scan_all:
                for holding in st.session_state.portfolio:
                    sym_h = holding["sym"]
                    avg_h = holding["avg"]; qty_h = holding["qty"]; sl_h = holding["sl"]
                    with st.spinner("Analyzing " + sym_h + "..."):
                        res_h, err_h = analyse_stock(sym_h, 300000, 1.0, regime_pen, nifty_df)

                    if err_h:
                        st.error(sym_h + ": " + err_h)
                        continue

                    cur_p    = res_h["p"]
                    pnl_pct  = (cur_p - avg_h) / avg_h * 100 if avg_h > 0 else 0
                    pnl_rs   = (cur_p - avg_h) * qty_h
                    sl_dist  = (cur_p - sl_h)  / cur_p * 100 if cur_p > 0 else 0
                    meta_h   = SETUPS[res_h["sname"]]
                    color_h  = meta_h["color"]
                    score_h  = res_h["final"]
                    vc_h     = res_h["tp"].get("vc","#6b7280")

                    # Holding decision
                    if cur_p <= sl_h:
                        decision = "🔴 EXIT NOW — Price is at or below your stop loss. This is the rule: exit."
                        dec_col  = "#ef4444"
                    elif score_h >= 78:
                        decision = "🟢 HOLD — Setup strong. Trail stop to just below EMA10 (" + fmt_rs(res_h["tp"].get("e10",0)) + ")."
                        dec_col  = "#10b981"
                    elif score_h >= 65:
                        decision = "🟡 HOLD with caution — Setup weakening. Consider booking partial profits."
                        dec_col  = "#f59e0b"
                    elif res_h["sname"] == "NO_SETUP":
                        decision = "🟠 REVIEW — No clear setup detected. Consider tightening stop or exiting."
                        dec_col  = "#f59e0b"
                    else:
                        decision = "🔴 CONSIDER EXITING — Score below minimum. Setup has deteriorated."
                        dec_col  = "#ef4444"

                    pnl_col = "#10b981" if pnl_pct >= 0 else "#ef4444"

                    with st.container():
                        st.markdown(
                            "<div style='background:#111827;border:1px solid #1f2937;border-radius:12px;"
                            "padding:16px 20px;margin-bottom:12px;'>"
                            "<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;'>"

                            "<div>"
                            "<span style='color:" + color_h + ";font-size:18px;font-weight:800;'>" + sym_h + "</span>"
                            "<span style='color:#6b7280;font-size:12px;margin-left:10px;'>" + meta_h["icon"] + " " + res_h["sname"].replace("_"," ") + "</span>"
                            "<div style='color:#f0f6ff;font-size:22px;font-weight:700;font-family:monospace;margin-top:4px;'>Rs." + "{:,.2f}".format(cur_p) + "</div>"
                            "<div style='color:#6b7280;font-size:12px;margin-top:2px;'>Avg cost: Rs." + "{:,.2f}".format(avg_h) + "  ·  Qty: " + str(qty_h) + "  ·  SL: Rs." + "{:,.2f}".format(sl_h) + "</div>"
                            "</div>"

                            "<div style='text-align:center;'>"
                            "<div style='font-size:36px;font-weight:900;color:" + vc_h + ";font-family:monospace;line-height:1;'>" + str(score_h) + "</div>"
                            "<div style='color:#6b7280;font-size:10px;'>/100</div>"
                            "<div style='color:" + vc_h + ";font-size:11px;font-weight:700;margin-top:4px;'>" + res_h["tp"].get("verdict","—") + "</div>"
                            "</div>"

                            "<div>"
                            "<div style='color:" + pnl_col + ";font-size:15px;font-weight:700;'>P&L: " + ("+" if pnl_pct>=0 else "") + str(round(pnl_pct,1)) + "%</div>"
                            "<div style='color:" + pnl_col + ";font-size:13px;'>Rs." + ("+" if pnl_rs>=0 else "") + "{:,.0f}".format(pnl_rs) + "</div>"
                            "<div style='color:#6b7280;font-size:11px;margin-top:4px;'>SL dist: " + str(round(sl_dist,1)) + "% above your SL</div>"
                            "</div>"
                            "</div>"

                            "<div style='margin-top:12px;padding:10px 14px;background:#0a0e1a;"
                            "border:1px solid " + dec_col + "30;border-left:3px solid " + dec_col + ";"
                            "border-radius:0 8px 8px 0;'>"
                            "<span style='color:" + dec_col + ";font-size:13px;font-weight:700;'>" + decision + "</span>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

        else:
            st.info("No stocks added yet. Add stocks you currently hold above to get analysis and hold/exit decisions.")

    # ══ TAB 3: SETUP GUIDE ════════════════════════════════════════════════════
    with tab3:
        st.markdown("### Setup Guide")
        info_card("Every setup has different characteristics, risk profiles, and entry rules. Read this guide to understand what you are trading before entering any position.")

        for key, meta in SETUPS.items():
            if key == "NO_SETUP": continue
            with st.expander(meta["icon"] + "  " + meta["name"] + "  —  " + meta["tagline"]):
                c1,c2 = st.columns([2,1])
                with c1:
                    st.markdown("**What is it?**")
                    st.write(meta["description"])
                    st.markdown("**Step-by-step action plan:**")
                    for i, step in enumerate(meta["step_by_step"], 1):
                        step_card(i, step)
                with c2:
                    st.metric("Risk Level", meta["risk"])
                    st.metric("Hold Period", meta["hold"])
                    st.metric("Min Score Required", str(meta["min_score"]) + "/100")
                    st.markdown("**Scoring weights:**")
                    total = sum(meta["weights"].values()) if meta["weights"] else 1
                    for wk,wv in meta["weights"].items():
                        st.progress(wv/total, text=wk + "  (" + str(wv) + " pts)")

    # ══ TAB 4: CHARTINK SCANNERS ══════════════════════════════════════════════
    with tab4:
        st.markdown("### Chartink Scanners")
        info_card("Copy any code below. Go to <b>chartink.com → Screens → Create New Screen → paste → Generate</b>. Run these scanners after 4 PM IST every day.")

        scanners = [
            ("🟢 Tier 1 — 52W High Breakout","HIGHEST PRIORITY — Act on results immediately",
             "Stocks in Nifty 200 that broke above their 52-week high this week with 1.5x+ volume and a full bullish EMA stack.",
             "The 52W high breakout on institutional volume is the single strongest momentum signal in equity markets. Every seller from the last year is now at breakeven or profit — there is no overhead resistance.",
             "Run this FIRST every evening after 4 PM. Results here = your top-priority trades for the next trading session.",
             "Enter at market open next day, or on a confirmed intraday retest of the breakout level. Set GTT stop immediately after fill.",
             "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
             [("{nifty 200}","Nifty 200 universe only. Eliminates penny stocks, operator stocks, and illiquid names."),
              ("close > 1 weeks max(52, high)","Price has closed ABOVE the 52-week high. The breakout is happening right now."),
              ("volume > 1.5x sma(volume, 50)","Volume is 50% above average. Without this, the breakout is likely fake."),
              ("EMA20 > EMA50 > EMA200","Confirms Weinstein Stage 2 uptrend across all timeframes."),
              ("turnover > Rs.25Cr","Minimum liquidity gate. You need to be able to enter and exit cleanly.")]),
            ("🟠 Tier 2 — VCP / Pre-Breakout Coil","HIGH — Build your GTT watchlist from results",
             "Nifty 200 stocks within 3% of their 52W high with 10-day volume below the 50-day average.",
             "This catches the setup BEFORE the Tier 1 breakout fires. Volume drying up near highs = supply exhaustion. Entering here gives a tighter stop and better risk-reward than chasing after the breakout.",
             "Run after Tier 1. Add results to your Zerodha GTT watchlist with an alert at the 52W high.",
             "Do NOT enter yet. Set a GTT price alert at the 52W high. Only enter when price breaks that level on 1.5x+ volume.",
             "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
             [("close > 0.97x 52W high","Within 3% of breakout. Close enough to be a real candidate."),
              ("close < 52W high","Has NOT broken out yet. Anticipation setup — do not enter early."),
              ("sma(vol, 10) < sma(vol, 50)","10-day volume below 50-day = volume drying up. This IS the VCP signal. Supply being exhausted."),
              ("Full EMA stack","Coil forming in an uptrend, not a downtrend.")]),
            ("🔵 Tier 3 — Momentum Leaders","MEDIUM — Enter only on EMA20 pullbacks",
             "Stage 2 stocks up 25%+ in both 6 months and 12 months.",
             "Counter-intuitive but proven: stocks already up 40% with a bullish EMA stack are statistically more likely to keep rising. The Nifty200 Momentum30 index using this principle delivered 19.3% CAGR over 20 years.",
             "Run weekly. These results form your core momentum watchlist.",
             "Do NOT buy at the current price. Add to watchlist. Enter ONLY when stock dips back to EMA20 with low volume.",
             "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
             [("Full EMA stack","Stage 2 uptrend confirmed."),
              ("close > 1.25x 26wk ago close","Up at least 25% in 6 months. Sustained momentum."),
              ("close > 1.25x 52wk ago close","Up at least 25% in 12 months. Not a flash move.")]),
        ]

        for sc_name,prio,what,why,when_,action,code,conds in scanners:
            with st.expander(sc_name + "  —  " + prio):
                st.markdown("**What it finds:** " + what)
                st.markdown("**Why it works:** " + why)
                st.markdown("**When to run:** " + when_)
                st.success("**Action on results:** " + action)
                st.markdown("**Conditions explained:**")
                for cond,expl in conds:
                    st.markdown("- `" + cond + "` — " + expl)
                st.code(code, language="text")

    # ══ TAB 5: TRADING RULES ══════════════════════════════════════════════════
    with tab5:
        st.markdown("### Trading Rules")
        info_card("These rules were discovered through losses by professional traders over decades. Each rule has a specific reason. Breaking them is the primary reason most traders lose money.")

        rule_groups = [
            ("🎯 Core Principles",[
                ("No trade is the best trade","When setup is unclear, market is weak, or you feel uncertain — do nothing. Missing a trade costs nothing. A bad trade can wipe out 10 good trades."),
                ("Score minimums are not guidelines","The minimum score for each setup type represents the point below which the statistical edge disappears. Below that, you are gambling."),
                ("3:1 minimum risk-reward always","If your stop is 5% away, your target must be at least 15% away. At 3:1 you can be right only 35% of the time and still be profitable over the long run."),
            ]),
            ("💰 Position Sizing",[
                ("1% capital risk per trade maximum","At 1% risk, 20 consecutive losing trades leaves you with 82% of capital. At 3%, you're down 46%. The math is brutal."),
                ("0.5% on uncertain days","F&O expiry, VIX above 20, bearish market regime — cut to half size automatically."),
                ("Maximum 25% in any single stock","Unexpected news can gap a stock down 20% overnight. Never let one stock destroy your account."),
                ("Maximum 5 positions simultaneously","More than 5 and you cannot monitor them properly when markets move fast against you."),
                ("5% total portfolio heat maximum","Sum up the risk on all open positions. It must never exceed 5% of your total capital."),
            ]),
            ("🚫 Hard Rules — Never Break",[
                ("GTT stop immediately after entry","The moment your order fills, place the GTT stop. Accounts are destroyed not by bad entries but by refusing to exit at the stop."),
                ("Never average down","If a trade goes against you to the stop, exit — don't add more. Averaging down converts small losses into account-destroying losses."),
                ("Never widen your stop","You set the stop based on the chart before emotion entered the picture. Trust your analysis. The stop is where you are proven wrong."),
                ("No trades between 9:15–9:30 AM","First 15 minutes = overnight order unwinding, gap fills, institutional games. Spreads widest. Moves most random."),
                ("No new entries after 3:15 PM","Closing auction and institutional rebalancing distorts prices. Never open a new swing position in this window."),
                ("No earnings holds","Check the results calendar. Always exit 1 day before quarterly results. Even a perfect setup can gap 20% down on bad earnings."),
                ("No revenge trades","After a stop loss, step away from the screen for at least 15 minutes. The urge to immediately recover a loss is the most dangerous emotion in trading."),
            ]),
            ("🇮🇳 India-Specific",[
                ("F&O Expiry rules","Monthly expiry = last Thursday. Weekly = every Thursday. On expiry: use only 0.5% risk. No new entries between 1-3 PM (max pain manipulation window)."),
                ("Bank Nifty as leading indicator","Bank Nifty often leads Nifty by 1-2 hours. If Bank Nifty is weak while Nifty is flat, expect Nifty to follow lower. Avoid finance/banking stocks on Bank Nifty weakness."),
                ("Check FII/DII data daily","NSE releases provisional FII/DII data after 3:30 PM. If FIIs are net sellers of Rs.3000+ Cr, reduce all position sizes by 50% next day."),
                ("Delivery percentage matters","NSE shows delivery % for every stock. Breakouts with above 40% delivery = institutional. Below 30% = intraday/speculative = higher failure rate."),
                ("RBI and Budget are event risks","Mark RBI policy dates and Budget date. Reduce all open positions by 50% the day before these events. They can move sectors 5-10% in one session."),
            ]),
        ]

        for group_name, rules in rule_groups:
            with st.expander(group_name):
                for rule_title, rule_desc in rules:
                    st.markdown("**" + rule_title + ":** " + rule_desc)
                    st.divider()

    st.divider()
    st.caption("Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance with end-of-day delay. Always verify on NSE before trading.")

if __name__ == "__main__":
    main()
