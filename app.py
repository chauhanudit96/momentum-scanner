"""
NSE Elite Swing Terminal v7
- Streamlit native components for ALL structure (tabs, expanders, columns, headers)
- HTML used ONLY for styled metric tiles and flag rows — never for structure
- Zero nested f-strings
- All 5 tabs guaranteed to render
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="NSE Swing Terminal", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background:#060e1c; color:#c9d1d9; font-family:'Inter',sans-serif; }
.main .block-container { padding-top:0.8rem; max-width:1280px; }
h1,h2,h3 { color:#c9d1d9 !important; }
.stTabs [data-baseweb="tab"] { color:#8b949e !important; font-size:12px !important; font-weight:600 !important; }
.stTabs [aria-selected="true"] { color:#58a6ff !important; border-bottom-color:#58a6ff !important; }
.stButton button { background:linear-gradient(135deg,#1f6feb,#388bfd) !important; color:#fff !important; font-weight:700 !important; border:none !important; border-radius:6px !important; }
.stTextInput input,.stNumberInput input { background:#0d1117 !important; border:1px solid #30363d !important; color:#c9d1d9 !important; border-radius:6px !important; }
.stTextInput label,.stNumberInput label,.stSelectbox label,.stSlider label { color:#8b949e !important; font-size:11px !important; font-weight:600 !important; }
.stExpander { background:#0d1117 !important; border:1px solid #21262d !important; border-radius:8px !important; }
.stSelectbox [data-baseweb="select"] { background:#0d1117 !important; border-color:#30363d !important; }
div[data-testid="stMetricValue"] { color:#c9d1d9 !important; font-size:20px !important; }
div[data-testid="stMetricLabel"] { color:#8b949e !important; font-size:11px !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
POPULAR = sorted([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "TITAN","WIPRO","ULTRACEMCO","NESTLEIND","SUNPHARMA","HCLTECH","TECHM",
    "POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP","BAJAJFINSV",
    "EICHERMOT","HEROMOTOCO","M&M","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL",
    "DATAPATTNS","LALPATHLAB","METROPOLIS","AKUMS","MARKSANS","SURYODAY",
    "KAYNES","DIXON","AMBER","COALINDIA","RVNL","GRASIM","DMART","IRCTC",
    "IRFC","COCHINSHIP","GRSE","TATAPOWER","CUMMINSIND","THERMAX","POLYCAB",
])

SECTORS = {
    "Defense":       ["BEL","HAL","BHEL","COCHINSHIP","GRSE","DATAPATTNS"],
    "Pharma":        ["SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AKUMS","MARKSANS"],
    "Banking":       ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK"],
    "Finance/NBFC":  ["BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","SURYODAY"],
    "IT":            ["TCS","INFY","HCLTECH","WIPRO","TECHM","PERSISTENT"],
    "Auto":          ["MARUTI","TATAMOTORS","EICHERMOT","HEROMOTOCO","M&M"],
    "Capital Goods": ["SIEMENS","ABB","HAVELLS","THERMAX","CUMMINSIND","POLYCAB","KAYNES"],
    "Chemicals":     ["DEEPAKNTR","AARTIIND","PIDILITIND","SOLARINDS"],
    "FMCG":          ["HINDUNILVR","ITC","BRITANNIA","DABUR","MARICO","NESTLEIND"],
    "Metals":        ["JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","NMDC"],
}

SETUP_META = {
    "VCP": {
        "color":"#3fb950","icon":"🌀","label":"Volatility Contraction Pattern",
        "tagline":"The spring is coiling — an explosive breakout is building",
        "min_score":72,"risk":"LOW","hold":"5–15 days","sl_anchor":"ema10",
        "description":(
            "A VCP forms when a stock makes a series of smaller and smaller pullbacks near its highs, "
            "with volume declining sharply on each correction. This is supply exhaustion — sellers are "
            "running out of stock to sell. Institutions are quietly accumulating. The tighter the coil, "
            "the more explosive the eventual breakout. Minervini's most trusted setup."
        ),
        "checklist":[
            "Volume below 50-day average by 30–50% — confirms the coil",
            "Price range getting smaller each day — ATR shrinking",
            "Stock staying above EMA20 during each pullback",
            "Within 10% of 52-week high",
        ],
        "trigger":"Breakout above the tight range on 2x+ volume. Only enter on the breakout candle.",
        "weights":{"Volume Contraction":25,"Price Tightness":20,"52W High Proximity":20,"EMA Stack":15,"RSI Zone":10,"MACD State":10},
    },
    "BREAKOUT": {
        "color":"#58a6ff","icon":"🚀","label":"52-Week High Breakout",
        "tagline":"Resistance is breaking — institutional money is entering",
        "min_score":75,"risk":"MEDIUM","hold":"5–20 days","sl_anchor":"ema20",
        "description":(
            "A breakout above the 52-week high is the single strongest momentum signal. "
            "Psychologically, it clears the overhang of every investor who bought in the last year. "
            "When volume confirms, institutions are aggressively accumulating. O'Neil, Darvas, and "
            "Weinstein all used this as their primary entry signal."
        ),
        "checklist":[
            "Volume on breakout day must be at least 1.5x average — non-negotiable",
            "Base before breakout should be at least 3 weeks",
            "NSE delivery percentage above 40% confirms institutional buying",
            "Breakout between 9:30–11:30 AM = strong conviction",
        ],
        "trigger":"Daily close above 52W high on volume. Or intraday when price holds above the high for 30+ minutes.",
        "weights":{"Breakout Volume":30,"EMA Stack":20,"52W High Proximity":20,"RS vs Nifty":15,"MACD State":10,"RSI Zone":5},
    },
    "BULL_FLAG": {
        "color":"#e3b341","icon":"🏴","label":"Bull Flag",
        "tagline":"The pole is strong — flag forming before the next surge",
        "min_score":70,"risk":"LOW-MEDIUM","hold":"3–10 days","sl_anchor":"flag_low",
        "description":(
            "A bull flag forms when a stock makes a strong fast move up (the pole) then consolidates "
            "in a tight range for 5–10 days with declining volume (the flag). Volume drops during the "
            "flag — this is healthy. When volume expands again and price breaks above the flag, the "
            "next leg begins. Qullamaggie's favourite setup."
        ),
        "checklist":[
            "Pole: 15–35% move in 2–3 weeks",
            "Flag: tight, 5–12 day consolidation with volume dropping 40–60%",
            "Flag channel: slight downslope or flat — less than 6% range",
            "Break above flag high on expanding volume = entry",
        ],
        "trigger":"Break above the upper trendline of the flag on expanding volume.",
        "weights":{"Pole Strength":25,"Flag Tightness":25,"Volume Pattern":20,"EMA Stack":15,"RSI Zone":10,"MACD State":5},
    },
    "EMA_PULLBACK": {
        "color":"#79c0ff","icon":"↩️","label":"EMA Pullback",
        "tagline":"Dip in an uptrend — lowest risk entry in a trending stock",
        "min_score":68,"risk":"LOWEST","hold":"5–15 days","sl_anchor":"ema20",
        "description":(
            "In a Stage 2 uptrend, stocks advance in waves, pulling back to their key EMAs between "
            "surges. When a strong stock dips to its 20 EMA with LOW volume and forms a bounce candle, "
            "that is your entry. Stop is just below the EMA — risking 2–3% for a potential 15–25% move. "
            "Best risk-reward of all setup types."
        ),
        "checklist":[
            "Volume MUST dry up on the dip — high volume dips are dangerous",
            "RSI drops to 45–55 during pullback — partial reset",
            "Price touches or comes within 3% of EMA20",
            "Look for a hammer or inside candle at EMA as reversal signal",
            "EMA20 must be rising — a flat EMA20 is not a pullback zone",
        ],
        "trigger":"First green daily candle closing above EMA20 on slightly higher volume.",
        "weights":{"EMA Stack":25,"Pullback Quality":25,"Volume on Dip":20,"RS vs Nifty":15,"MACD State":10,"RSI Zone":5},
    },
    "SECOND_LEG": {
        "color":"#bc8cff","icon":"⚡","label":"Second Leg / Multi-Leg",
        "tagline":"Proven stock, proven institutions — second move often bigger",
        "min_score":75,"risk":"MEDIUM","hold":"10–30 days","sl_anchor":"base_low",
        "description":(
            "After a stock makes a big first move (30–80%), it pauses and builds a base. "
            "If this base is TIGHT (institutions holding, not selling), and the stock breaks out "
            "again — this is a second leg. Minervini's and Qullamaggie's highest conviction trade. "
            "HAL, BEL, DATAPATTNS in 2023–24 ran 3–4 legs without losing Stage 2 structure."
        ),
        "checklist":[
            "First leg: at least 30% move from base to peak",
            "Correction after first leg: less than 35% (tight = institutions holding)",
            "Volume dries up completely during the base between legs",
            "MACD stays positive (above zero) throughout the base",
        ],
        "trigger":"Breakout above base high with 1.5x+ volume. The base IS the setup — it needs to break first.",
        "weights":{"First Leg Strength":25,"Base Quality":25,"Breakout Volume":20,"RS vs Nifty":15,"MACD State":10,"EMA Stack":5},
    },
    "FLAT_BASE": {
        "color":"#56d364","icon":"📊","label":"Flat Base",
        "tagline":"Tight patient consolidation near highs — supply being absorbed",
        "min_score":68,"risk":"LOW","hold":"5–20 days","sl_anchor":"base_low",
        "description":(
            "A flat base forms when a stock moves sideways in a tight range (less than 8–10%) "
            "for 3–6 weeks near highs, with declining volume. The stock is digesting a prior move. "
            "Price never falls far from highs, showing buyers absorbing any selling. O'Neil found "
            "the flatter and tighter the base, the bigger the eventual breakout."
        ),
        "checklist":[
            "Range: less than 8% is good, less than 5% is exceptional",
            "Duration: at least 3 weeks (15 trading days minimum)",
            "Volume must be declining throughout the base",
            "Price within 15% of the 52-week high",
        ],
        "trigger":"Breakout above the top of the flat base on 1.5x+ volume.",
        "weights":{"Base Tightness":30,"52W High Proximity":20,"Volume Dry-up":20,"EMA Stack":15,"Duration":10,"MACD State":5},
    },
    "NO_SETUP": {
        "color":"#484f58","icon":"⏳","label":"No Clear Setup",
        "tagline":"Patience is a position — wait for the right setup",
        "min_score":999,"risk":"DO NOT TRADE","hold":"N/A","sl_anchor":None,
        "description":"No tradeable swing pattern detected. Stock is between key levels without a clear entry trigger.",
        "checklist":[],"trigger":"Wait.",
        "weights":{},
    },
}

SCANNERS = [
    {
        "name":"Tier 1 — 52W High Breakout",
        "setup":"BREAKOUT","color":"#3fb950","priority":"HIGHEST — Act immediately",
        "what":"Nifty 200 stocks breaking above 52-week high this week with 1.5x+ volume and full Stage 2 EMA stack.",
        "why":"The 52W high breakout on institutional volume is the single strongest momentum signal. Every seller from the last year is at breakeven above this level — no overhead resistance.",
        "when":"Run first after 4 PM IST. Results = top priority trades for next day.",
        "action":"Enter at open or on confirmed retest of breakout level. Set GTT stop immediately.",
        "code":"( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("{nifty 200}","Nifty 200 universe only. Eliminates penny stocks, operator stocks, and illiquid names where execution is dangerous."),
            ("close > 1 weeks max(52, high)","Price has closed ABOVE the highest level of the last 52 weeks. This IS the breakout — every seller from the past year is now at breakeven or profit. No overhead resistance."),
            ("volume > 1.5x sma(volume,50)","Non-negotiable volume filter. Below-average volume breakouts fail 60%+ of the time in Indian markets. Volume = institutional conviction."),
            ("EMA(20) > EMA(50) > EMA(200)","Confirms Weinstein Stage 2 uptrend across all timeframes. Breakouts from Stage 2 have dramatically higher success rates."),
            ("Turnover > Rs.25Cr","Minimum liquidity. Below this, your entry or exit can move the price against you."),
        ],
    },
    {
        "name":"Tier 2 — VCP / Pre-Breakout Coil",
        "setup":"VCP","color":"#e3b341","priority":"HIGH — Build GTT watchlist",
        "what":"Nifty 200 stocks within 3% of 52W high with 10-day volume below 50-day volume. Spring is coiling.",
        "why":"Catches the setup BEFORE Tier 1 fires. Volume drying up near highs = supply exhaustion. Entry here gives a tighter stop and better R:R than chasing the breakout after it fires.",
        "when":"Run after Tier 1. Results go on your GTT alert list.",
        "action":"DO NOT enter yet. Set price alert at 52W high. Enter ONLY when price breaks with 1.5x+ volume.",
        "code":"( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("close > 0.97x 52W high","Within 3% of breakout level. Close enough to be a real pre-breakout candidate."),
            ("close < 52W high","Has NOT broken out yet. Anticipation, not confirmation. Breakout is still ahead."),
            ("sma(vol,10) < sma(vol,50)","10-day average volume is BELOW 50-day. This IS the VCP signal. Volume contracting near highs = supply exhaustion. Spring coiling."),
            ("Full EMA stack","Stage 2 confirmed. The coil is forming in an uptrend, not a downtrend."),
        ],
    },
    {
        "name":"Tier 3 — Momentum Leaders",
        "setup":"SECOND_LEG","color":"#bc8cff","priority":"MEDIUM — Enter on EMA20 dips only",
        "what":"Stage 2 stocks up 25%+ in both 6M and 12M. Proven momentum leaders.",
        "why":"Counter-intuitive but proven: a stock already up 40% with a bullish EMA stack is MORE likely to keep rising. The Nifty200 Momentum30 index using this principle delivered 19.3% CAGR over 20 years.",
        "when":"Run weekly. Results form your core momentum watchlist.",
        "action":"Do NOT buy at current price. Wait for a 2–5 day pullback to EMA20 with drying volume.",
        "code":"( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("Full EMA stack","Confirmed Stage 2 uptrend across all timeframes."),
            ("close > 1.25x 26wk ago","Up at least 25% in 6 months. Sustained intermediate momentum."),
            ("close > 1.25x 52wk ago","Up at least 25% in 12 months. Long-term momentum, not a flash move."),
        ],
    },
    {
        "name":"Tier 4 — Pure VCP / Tight Base",
        "setup":"VCP","color":"#79c0ff","priority":"HIGH — Chart review required before trading",
        "what":"Strongest VCP filter: within 10% of highs, volume contracted 25%+. Most explosive setup when it fires.",
        "why":"Volume contracting 25%+ while price stays near highs = supply exhaustion. When institutional buying returns, the breakout is sharp and fast.",
        "when":"Run daily. Every result needs chart verification in TradingView.",
        "action":"Open each result in TradingView. Confirm: tightening range + shrinking ATR + volume bars getting smaller. Enter on breakout above tight range on 2x+ volume.",
        "code":"( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("close > 0.90x 52W high","Within 10% of highs — base forming near the top."),
            ("EMA(20) > EMA(50) > EMA(200)","Base forming in uptrend — the most critical filter."),
            ("sma(vol,10) < 0.75x sma(vol,50)","Volume contracted 25%+. This is the VCP squeeze."),
        ],
    },
]

# ── INDICATORS ────────────────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        f = float(v)
        return d if np.isnan(f) else f
    except:
        return d

def ema(s, p):   return s.ewm(span=p, adjust=False).mean()
def sma(s, p):   return s.rolling(p).mean()

def rsi_fn(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))

def macd_fn(s):
    m   = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()
    sig = m.ewm(span=9, adjust=False).mean()
    return m, sig, m - sig

def enrich(df):
    df = df.copy()
    c  = df["Close"]
    for p in [10, 20, 50, 200]:
        df["E" + str(p)] = ema(c, p)
    df["V50"]  = sma(df["Volume"], 50)
    df["V10"]  = sma(df["Volume"], 10)
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=100).max()
    df["RSI"]  = rsi_fn(c)
    df["ATR"]  = (df["High"] - df["Low"]).rolling(14).mean()
    m, sig, h  = macd_fn(c)
    df["MACD"] = m
    df["HIST"] = h
    return df

# ── FETCH ─────────────────────────────────────────────────────────────────────
def fetch_stock(sym):
    for sfx in [".NS", ".BO"]:
        try:
            df = yf.Ticker(sym + sfx).history(period="2y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 60:
                return df.dropna(subset=["Close"]), sym + sfx
        except:
            continue
    return None, None

def fetch_index(t):
    try:
        df = yf.Ticker(t).history(period="1y", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 50:
            return df.dropna(subset=["Close"])
    except:
        pass
    return None

# ── MARKET REGIME ─────────────────────────────────────────────────────────────
def market_regime(ndf, bndf):
    rows = []
    penalty = 0
    for name, df in [("Nifty 50", ndf), ("Bank Nifty", bndf)]:
        if df is None or len(df) < 50:
            rows.append((name, "UNKNOWN", "grey", 0))
            continue
        d    = enrich(df)
        p    = safe(d["Close"].iloc[-1])
        e50  = safe(d["E50"].iloc[-1])
        e200 = safe(d["E200"].iloc[-1])
        if p < e200:
            rows.append((name, "BEARISH", "red", 20))
            penalty = max(penalty, 20)
        elif p < e50:
            rows.append((name, "CAUTION", "orange", 10))
            penalty = max(penalty, 10)
        else:
            rows.append((name, "HEALTHY", "green", 0))
    return rows, penalty

# ── SETUP DETECTION ───────────────────────────────────────────────────────────
def detect_setup(df):
    if len(df) < 40:
        return "NO_SETUP", {}
    l    = df.iloc[-1]
    p    = safe(l["Close"])
    e20  = safe(l["E20"]); e50 = safe(l["E50"]); e200 = safe(l["E200"])
    h52  = safe(l["H52"], p)
    vr   = safe(l["VR"],  1.0)
    mac  = safe(l["MACD"])
    atr  = safe(l["ATR"], p * 0.02)
    c20  = df["Close"].tail(20)
    c7   = df["Close"].tail(7)
    v10  = df["Volume"].tail(10).mean()
    v50  = df["Volume"].tail(50).mean()
    pct_h   = (h52 - p) / h52 * 100 if h52 > 0 else 100
    rng20   = (c20.max() - c20.min()) / c20.mean() * 100 if c20.mean() > 0 else 100
    rng7    = (c7.max()  - c7.min())  / c7.mean()  * 100 if c7.mean()  > 0 else 100
    vol10   = v10 / v50 if v50 > 0 else 1.0
    mov20   = (c20.iloc[-1] - c20.iloc[0]) / c20.iloc[0] * 100 if c20.iloc[0] > 0 else 0
    emas    = (p > e20) and (e20 > e50) and (e50 > e200)
    near20  = abs(p - e20) / p < 0.04 if p > 0 else False
    near50  = abs(p - e50) / p < 0.05 if p > 0 else False
    df6m    = df.tail(126)
    l1max   = float(df6m["High"].max())
    l1min   = float(df6m["Low"].min())
    l1move  = (l1max - l1min) / l1min * 100 if l1min > 0 else 0
    pidx    = df6m["High"].idxmax()
    after   = df6m.loc[pidx:]
    blow    = float(after["Low"].min()) if len(after) > 5 else p
    bdepth  = (l1max - blow) / l1max * 100 if l1max > 0 else 100
    p2p     = (l1max - p) / l1max * 100 if l1max > 0 else 100
    sd = {
        "price": p, "e10": safe(l["E10"]), "e20": e20, "e50": e50, "e200": e200,
        "h52": h52, "pct_h": pct_h, "vr": vr, "rsi": safe(l["RSI"], 50),
        "macd": mac, "hist": safe(l["HIST"]), "atr": atr,
        "rng20": rng20, "rng7": rng7, "vol10": vol10, "move20": mov20,
        "emas": emas, "near20": near20, "near50": near50,
        "leg1": l1move, "bdepth": bdepth, "blow": blow, "p2p": p2p,
        "flag_high": float(c7.max()),
        "base_high": float(df["High"].tail(20).max()),
        "base_low":  float(df["Low"].tail(20).min()),
    }
    if l1move >= 30 and bdepth <= 30 and p2p <= 10 and emas and vr >= 1.2:
        return "SECOND_LEG", sd
    if pct_h <= 1.5 and vr >= 1.5 and emas:
        return "BREAKOUT", sd
    if pct_h <= 12 and rng20 < 15 and vol10 < 0.80 and e20 > e50 and e50 > e200:
        return "VCP", sd
    if mov20 >= 12 and rng7 < 6 and vol10 < 0.90 and p > e20:
        return "BULL_FLAG", sd
    if rng20 < 10 and pct_h <= 18 and e20 > e50 > e200 and vol10 < 0.95:
        return "FLAT_BASE", sd
    if e50 > e200:
        if near20 and e20 > e50:
            return "EMA_PULLBACK", sd
        if near50 and p > e200:
            return "EMA_PULLBACK", sd
    return "NO_SETUP", sd

# ── SCORING ───────────────────────────────────────────────────────────────────
def score_setup(setup, sd, r6, r12, rs):
    meta   = SETUP_META.get(setup, SETUP_META["NO_SETUP"])
    scores = {}
    flags  = []   # list of (type, title, message)
    p=sd.get("price",0); pct_h=sd.get("pct_h",100)
    vr=sd.get("vr",1.0); rsi_=sd.get("rsi",50)
    mac=sd.get("macd",0); hist=sd.get("hist",0)
    rng20=sd.get("rng20",100); rng7=sd.get("rng7",100)
    vol10=sd.get("vol10",1.0); mov20=sd.get("move20",0)
    emas=sd.get("emas",False); e20=sd.get("e20",0)
    e50=sd.get("e50",0); e200=sd.get("e200",0)
    leg1=sd.get("leg1",0); bd=sd.get("bdepth",100)
    near20=sd.get("near20",False); near50=sd.get("near50",False)

    w = meta["weights"]

    # ── EMA STACK ──────────────────────────────────────────────────────────────
    key = "EMA Stack"
    if key in w:
        mx = w[key]
        if p > e20 > e50 > e200:
            scores[key] = mx
            flags.append(("bull","Stage 2 Confirmed","Price above EMA20 > EMA50 > EMA200. Weinstein Stage 2 — the only stage where momentum strategies work consistently across all timeframes."))
        elif e20 > e50 > e200:
            scores[key] = int(mx * 0.65)
            flags.append(("warn","Stage 2 Partial","EMAs aligned bullishly but price dipped below EMA20. Wait for price to reclaim EMA20 before entering."))
        elif e20 > e50 or e50 > e200:
            scores[key] = int(mx * 0.30)
            flags.append(("warn","EMA Alignment Weak","Only partial EMA alignment. Stage 2 still developing. Higher risk."))
        else:
            scores[key] = 0
            flags.append(("bear","EMA Stack Bearish","EMAs in bearish order. Do not buy stocks in Stage 3 or Stage 4 downtrends."))

    # ── 52W HIGH PROXIMITY ─────────────────────────────────────────────────────
    key = "52W High Proximity"
    if key in w:
        mx = w[key]
        if pct_h <= 0:    scores[key] = mx;          flags.append(("bull","At 52W High — Breakout","Stock is at or above its 52-week high. No overhead resistance. Maximum momentum signal."))
        elif pct_h <= 2:  scores[key] = int(mx*.90);  flags.append(("bull","Within 2% of 52W High","Extremely close. A single good session could trigger the breakout. Set GTT alert."))
        elif pct_h <= 5:  scores[key] = int(mx*.75);  flags.append(("bull","Within 5% of 52W High","Near-breakout zone. Good stage but needs to break before entering aggressively."))
        elif pct_h <= 10: scores[key] = int(mx*.50);  flags.append(("warn","10% Below 52W High","In base formation territory. Need other signals to confirm direction."))
        elif pct_h <= 20: scores[key] = int(mx*.25);  flags.append(("warn","10–20% Below 52W High","Too far from breakout zone for ideal setup. Watch but don't act yet."))
        else:             scores[key] = 0;             flags.append(("bear","Far From 52W High","More than 20% below the high. Not a momentum setup."))

    # ── VOLUME CONTRACTION ─────────────────────────────────────────────────────
    key = "Volume Contraction"
    if key in w:
        mx  = w[key]
        pv  = str(round(vol10 * 100))
        if vol10 < 0.40:   scores[key] = mx;          flags.append(("bull","Deep Volume Contraction","Volume at only " + pv + "% of 50-day average. Complete supply exhaustion. The quieter before the breakout, the bigger the move."))
        elif vol10 < 0.60: scores[key] = int(mx*.80);  flags.append(("bull","Strong Volume Contraction","Volume at " + pv + "% of average. Healthy VCP signature. Institutions accumulating quietly."))
        elif vol10 < 0.75: scores[key] = int(mx*.55);  flags.append(("warn","Moderate Volume Contraction","Volume at " + pv + "% of average. Some drying but not deep enough for classic VCP."))
        else:              scores[key] = int(mx*.15);  flags.append(("bear","Insufficient Contraction","Volume at " + pv + "% of average. VCP requires significantly lower volume. Not ready."))

    # ── PRICE TIGHTNESS ────────────────────────────────────────────────────────
    for key in ["Price Tightness", "Base Tightness"]:
        if key in w:
            mx   = w[key]
            r_s  = str(round(rng20, 1))
            if rng20 < 5:    scores[key] = mx;          flags.append(("bull","Exceptional Tightness","20-day range only " + r_s + "%. Spring fully wound. Breakouts from this tightness are typically explosive."))
            elif rng20 < 8:  scores[key] = int(mx*.80);  flags.append(("bull","Strong Tightness","20-day range of " + r_s + "%. Solid base — institutions absorbing supply without much price fluctuation."))
            elif rng20 < 12: scores[key] = int(mx*.55);  flags.append(("warn","Moderate Tightness","20-day range of " + r_s + "%. Acceptable but not ideal. A tighter range would give higher confidence."))
            elif rng20 < 18: scores[key] = int(mx*.25);  flags.append(("warn","Loose Base","20-day range of " + r_s + "%. Wide base suggests lower institutional conviction. Higher risk of failed breakout."))
            else:            scores[key] = 0;             flags.append(("bear","No Real Base Forming","20-day range of " + r_s + "%. Too wide to be called a base. Wait for consolidation."))

    # ── BREAKOUT VOLUME ────────────────────────────────────────────────────────
    key = "Breakout Volume"
    if key in w:
        mx   = w[key]
        vr_s = str(round(vr, 1))
        if vr >= 4.0:   scores[key] = mx;          flags.append(("bull","Exceptional Breakout Volume","Volume " + vr_s + "x average. Institutional stampede. Very high probability of continuation."))
        elif vr >= 2.5: scores[key] = int(mx*.85);  flags.append(("bull","Strong Breakout Volume","Volume " + vr_s + "x average. Clear institutional participation. Breakout has strong legs."))
        elif vr >= 1.5: scores[key] = int(mx*.65);  flags.append(("bull","Confirmed Breakout Volume","Volume " + vr_s + "x average — meets minimum. Real breakout but watch next few sessions."))
        elif vr >= 1.0: scores[key] = int(mx*.30);  flags.append(("warn","Below-Average Breakout Volume","Volume " + vr_s + "x average. Could be a false breakout. Caution."))
        else:           scores[key] = 0;             flags.append(("bear","Weak Volume on Breakout","Volume only " + vr_s + "x. High probability of failed breakout. Wait for retest with better volume."))

    # ── POLE STRENGTH ──────────────────────────────────────────────────────────
    key = "Pole Strength"
    if key in w:
        mx   = w[key]
        mv_s = str(round(mov20, 1))
        if mov20 >= 35:   scores[key] = mx;          flags.append(("bull","Exceptional Pole (+" + mv_s + "%)","Powerful institutional move. Strong poles produce strong second legs after the flag."))
        elif mov20 >= 22: scores[key] = int(mx*.85);  flags.append(("bull","Strong Pole (+" + mv_s + "%)","Solid bull flag pole. Flag should resolve to the upside."))
        elif mov20 >= 12: scores[key] = int(mx*.60);  flags.append(("warn","Moderate Pole (+" + mv_s + "%)","Acceptable but not exceptional. Follow-through from moderate poles tends to be smaller."))
        else:             scores[key] = 0;             flags.append(("bear","Weak Pole (+" + mv_s + "%)","Too weak for reliable bull flag. Look for stronger setups."))

    # ── FLAG TIGHTNESS ─────────────────────────────────────────────────────────
    key = "Flag Tightness"
    if key in w:
        mx   = w[key]
        r7_s = str(round(rng7, 1))
        if rng7 < 3:    scores[key] = mx;          flags.append(("bull","Very Tight Flag (" + r7_s + "%)","Extremely tight flag — institutions not selling at all. High probability breakout."))
        elif rng7 < 5:  scores[key] = int(mx*.85);  flags.append(("bull","Tight Flag (" + r7_s + "%)","Good flag tightness. Orderly consolidation after the pole."))
        elif rng7 < 8:  scores[key] = int(mx*.55);  flags.append(("warn","Moderate Flag (" + r7_s + "%)","Acceptable but a bit wide. Use a tighter stop."))
        else:           scores[key] = 0;             flags.append(("bear","Wide Flag (" + r7_s + "%)","Too wide to be a proper flag. Risk of full pole retracement is higher."))

    # ── VOLUME PATTERN ─────────────────────────────────────────────────────────
    key = "Volume Pattern"
    if key in w:
        mx = w[key]
        if vol10 < 0.55 and vr >= 1.5:
            scores[key] = mx
            flags.append(("bull","Perfect Volume Asymmetry","High volume on pole, very low on flag. Textbook bull flag. Institutions bought aggressively on the pole and are sitting tight during the flag."))
        elif vol10 < 0.75:
            scores[key] = int(mx * .65)
            flags.append(("warn","Decent Volume Pattern","Volume partially drying during flag. Good but not perfect."))
        else:
            scores[key] = int(mx * .20)
            flags.append(("bear","Volume Not Drying on Flag","Volume during flag is not significantly lower. Distribution may be occurring."))

    # ── PULLBACK QUALITY ───────────────────────────────────────────────────────
    key = "Pullback Quality"
    if key in w:
        mx = w[key]
        if near20 and vol10 < 0.70:
            scores[key] = mx
            flags.append(("bull","Perfect EMA20 Pullback","Price resting on EMA20 with very low volume. Ideal Minervini low-risk entry — trend intact, sellers gone quiet."))
        elif near20:
            scores[key] = int(mx * .70)
            flags.append(("warn","EMA20 Pullback — Volume High","At EMA20 but volume not drying enough. Wait for volume to dry before entering."))
        elif near50 and vol10 < 0.80:
            scores[key] = int(mx * .55)
            flags.append(("warn","EMA50 Pullback — Deeper Dip","Pulled back to EMA50. Still tradeable if EMA50 is rising. Stop will be wider."))
        else:
            scores[key] = int(mx * .20)
            flags.append(("bear","Not at Clean EMA Level","Price not cleanly at EMA20 or EMA50. No clear stop loss anchor. Wait."))

    # ── VOLUME ON DIP ──────────────────────────────────────────────────────────
    key = "Volume on Dip"
    if key in w:
        mx  = w[key]
        pv  = str(round(vol10 * 100))
        if vol10 < 0.50:   scores[key] = mx;          flags.append(("bull","Volume Very Low on Dip","Volume at " + pv + "% during pullback. Nobody panic-selling. Natural healthy dip — institutions holding all shares."))
        elif vol10 < 0.70: scores[key] = int(mx*.80);  flags.append(("bull","Volume Drying on Dip","Volume at " + pv + "% during pullback. Healthy. Selling is light and orderly — profit-taking, not distribution."))
        elif vol10 < 0.85: scores[key] = int(mx*.50);  flags.append(("warn","Volume Moderate on Dip","Volume at " + pv + "% during dip. Could be light distribution. Watch next session's volume closely."))
        else:              scores[key] = int(mx*.15);  flags.append(("bear","High Volume on Dip","Volume at " + pv + "% during dip — elevated. Someone is selling. Avoid until volume normalizes."))

    # ── FIRST LEG STRENGTH ─────────────────────────────────────────────────────
    key = "First Leg Strength"
    if key in w:
        mx   = w[key]
        l1_s = str(int(leg1))
        if leg1 >= 70:   scores[key] = mx;          flags.append(("bull","Exceptional First Leg (+" + l1_s + "%)","Major institutional stock. Second legs after moves this big tend to be powerful."))
        elif leg1 >= 45: scores[key] = int(mx*.85);  flags.append(("bull","Strong First Leg (+" + l1_s + "%)","Strong institutional interest. Good foundation for a second leg."))
        elif leg1 >= 28: scores[key] = int(mx*.60);  flags.append(("warn","Moderate First Leg (+" + l1_s + "%)","Acceptable. Second legs from smaller first moves have smaller potential upside."))
        else:            scores[key] = 0;             flags.append(("bear","First Leg Too Small (+" + l1_s + "%)","Insufficient institutional conviction shown. Look for stocks with larger first moves."))

    # ── BASE QUALITY ───────────────────────────────────────────────────────────
    key = "Base Quality"
    if key in w:
        mx   = w[key]
        bd_s = str(round(bd, 1))
        if bd <= 12:   scores[key] = mx;          flags.append(("bull","Very Tight Base (" + bd_s + "% deep)","Institutions barely sold anything. Tight bases after big moves = highest conviction second-leg setups."))
        elif bd <= 20: scores[key] = int(mx*.80);  flags.append(("bull","Tight Base (" + bd_s + "% deep)","Institutions took some profit but bulk of position intact. Good quality base."))
        elif bd <= 30: scores[key] = int(mx*.55);  flags.append(("warn","Moderate Base (" + bd_s + "% deep)","Some distribution occurred. Still tradeable but second leg may be smaller."))
        else:          scores[key] = 0;             flags.append(("bear","Deep Correction (" + bd_s + "%)","Too deep. Suggests institutions took most of their profits. Base here is more of a full retracement."))

    # ── BREAKOUT VOLUME (second leg) ───────────────────────────────────────────
    key = "Breakout Volume"
    if key in w and "First Leg Strength" in w:  # second leg context
        mx   = w[key]
        vr_s = str(round(vr, 1))
        if vr >= 3:    scores[key] = mx;          flags.append(("bull","High Conviction Second Leg (" + vr_s + "x)","Institutions aggressively re-entering. They didn't exit during the base — they were waiting to add."))
        elif vr >= 2:  scores[key] = int(mx*.80);  flags.append(("bull","Strong Second Leg Volume (" + vr_s + "x)","Good institutional buying on second leg."))
        elif vr >= 1.5:scores[key] = int(mx*.60);  flags.append(("warn","Acceptable Volume (" + vr_s + "x)","Meets minimum but more volume would give higher confidence."))
        else:          scores[key] = 0;             flags.append(("bear","Weak Second Leg Volume (" + vr_s + "x)","Low volume second legs fail frequently. Wait for retest with better volume."))

    # ── VOLUME DRY-UP ──────────────────────────────────────────────────────────
    key = "Volume Dry-up"
    if key in w:
        mx  = w[key]
        pv  = str(round(vol10 * 100))
        if vol10 < 0.55:   scores[key] = mx;          flags.append(("bull","Excellent Volume Dry-Up","Volume at " + pv + "% of average. Near-complete supply exhaustion. High quality flat base."))
        elif vol10 < 0.70: scores[key] = int(mx*.75);  flags.append(("bull","Good Volume Dry-Up","Volume declining nicely at " + pv + "% of average. Healthy flat base behavior."))
        elif vol10 < 0.85: scores[key] = int(mx*.45);  flags.append(("warn","Partial Volume Dry-Up","Volume at " + pv + "%. Declining but not enough for classic flat base."))
        else:              scores[key] = int(mx*.10);  flags.append(("bear","Volume Not Drying","Volume at " + pv + "%. Could be distribution disguised as consolidation."))

    # ── DURATION ───────────────────────────────────────────────────────────────
    key = "Duration"
    if key in w:
        mx = w[key]
        if vol10 < 0.90:
            scores[key] = mx
            flags.append(("bull","Base Duration Adequate","Base has been building long enough to clear overhead supply. Bases need at least 3 weeks to be reliable."))
        else:
            scores[key] = int(mx * .40)
            flags.append(("warn","Base May Be Too Young","Base formation may not be mature enough. Ideal flat bases take 3–6 weeks to develop."))

    # ── RSI ZONE ───────────────────────────────────────────────────────────────
    key = "RSI Zone"
    if key in w:
        mx   = w[key]
        rs_s = str(round(rsi_))
        if 50 <= rsi_ <= 65:    scores[key] = mx;          flags.append(("bull","RSI Sweet Spot (" + rs_s + ")","RSI 50–65 is the ideal momentum zone. Strong enough to confirm upward trend, room to run without being overbought."))
        elif 45 <= rsi_ < 50:   scores[key] = int(mx*.65);  flags.append(("warn","RSI Recovering (" + rs_s + ")","Below 50 but recovering. Needs to push above 50 to confirm uptrend resuming."))
        elif 65 < rsi_ <= 72:   scores[key] = int(mx*.55);  flags.append(("warn","RSI Approaching Overbought (" + rs_s + ")","Gaining steam but entering caution territory. Be ready for 1–3 day pullback."))
        elif 72 < rsi_ <= 80:   scores[key] = int(mx*.20);  flags.append(("warn","RSI Overbought (" + rs_s + ")","Extended short-term. Wait for RSI pullback to 55–65 range before entering."))
        elif rsi_ > 80:         scores[key] = 0;             flags.append(("bear","RSI Extremely Overbought (" + rs_s + ")","RSI above 80. High probability of sharp pullback. Missing this trade is better than chasing."))
        else:                   scores[key] = 0;             flags.append(("bear","RSI Downtrend (" + rs_s + ")","RSI below 45. Momentum strategies don't work well at this level."))

    # ── MACD STATE ─────────────────────────────────────────────────────────────
    key = "MACD State"
    if key in w:
        mx = w[key]
        if mac > 0 and hist > 0:
            scores[key] = mx
            flags.append(("bull","MACD Accelerating","MACD positive AND histogram expanding. Momentum building, not topping. Best MACD state for swing entries."))
        elif mac > 0:
            scores[key] = int(mx * .65)
            flags.append(("warn","MACD Positive but Slowing","MACD positive but histogram shrinking. Momentum exists but decelerating. Acceptable for entry but manage expectations."))
        elif -0.5 < mac <= 0:
            scores[key] = int(mx * .30)
            flags.append(("warn","MACD Near Zero","Just below zero. Watching for bullish crossover. If MACD crosses above zero with expanding histogram = strong secondary buy signal."))
        else:
            scores[key] = 0
            flags.append(("bear","MACD Negative","Bearish momentum dominating. Entering against negative MACD is an uphill battle. Wait for MACD to recover."))

    # ── RS VS NIFTY ────────────────────────────────────────────────────────────
    key = "RS vs Nifty"
    if key in w:
        mx = w[key]
        if rs is None:
            scores[key] = int(mx * .50)
        elif rs >= 20:   scores[key] = mx;           flags.append(("bull","Massive Outperformer (+" + str(round(rs,1)) + "%)","Stock outperforming Nifty by " + str(round(rs,1)) + "% over 6M. Genuine market leader — FIIs and large funds are overweight."))
        elif rs >= 10:   scores[key] = int(mx*.85);   flags.append(("bull","Outperforming Nifty (+" + str(round(rs,1)) + "%)","Strong relative strength. Will likely continue to lead when market rallies."))
        elif rs >= 3:    scores[key] = int(mx*.65);   flags.append(("warn","Slightly Ahead of Nifty (+" + str(round(rs,1)) + "%)","Marginally outperforming. Not a leader — look for stocks outperforming by 10%+ for best setups."))
        elif rs >= 0:    scores[key] = int(mx*.35);   flags.append(("warn","Matching Nifty (+" + str(round(rs,1)) + "%)","Barely keeping pace with the index. Leaders should outperform by 10%+."))
        else:            scores[key] = 0;              flags.append(("bear","Underperforming Nifty (" + str(round(rs,1)) + "%)","Behind Nifty over 6M. If market dips, this stock will fall even harder."))

    raw = sum(scores.values())
    return scores, flags, raw

# ── TRADE PLAN ────────────────────────────────────────────────────────────────
def build_trade(setup, sd, raw, capital, risk_pct, regime_pen):
    meta   = SETUP_META.get(setup, SETUP_META["NO_SETUP"])
    final  = max(0, raw - regime_pen)
    min_s  = meta["min_score"]
    p      = sd.get("price", 0)
    e10    = sd.get("e10", 0); e20 = sd.get("e20", 0); e50 = sd.get("e50", 0)
    h52    = sd.get("h52", 0)
    atr    = sd.get("atr", p * 0.02)
    fh     = sd.get("flag_high", p)
    bh     = sd.get("base_high", p)
    bl     = sd.get("base_low",  p * 0.95)
    blow   = sd.get("blow",      p * 0.95)
    near20 = sd.get("near20", False)

    if setup == "NO_SETUP" or final < min_s:
        return {"viable": False, "final": final, "verdict": "NO TRADE", "vc": "#484f58",
                "reason": "Score " + str(final) + " is below minimum " + str(min_s) + " required for " + meta["label"] + ". Wait for a better setup."}

    if final >= 90:   verdict, vc = "ELITE SETUP",  "#3fb950"
    elif final >= 78: verdict, vc = "STRONG SETUP", "#58a6ff"
    elif final >= 65: verdict, vc = "TRADABLE",     "#e3b341"
    else:
        return {"viable": False, "final": final, "verdict": "BELOW MIN — AVOID", "vc": "#f85149",
                "reason": "Score " + str(final) + " is below minimum " + str(min_s) + " for this setup type. Quality insufficient. Wait for improvement."}

    anchor = meta["sl_anchor"]
    if anchor == "ema10":    sl = e10 * 0.99;   sl_lbl = "1% below EMA10"
    elif anchor == "ema20":  sl = e20 * 0.99;   sl_lbl = "1% below EMA20"
    elif anchor == "flag_low": sl = bl * 0.995; sl_lbl = "below flag low"
    elif anchor == "base_low": sl = blow * 0.99; sl_lbl = "1% below base low"
    else:                    sl = p * 0.95;     sl_lbl = "5% mechanical"
    sl_pct = (p - sl) / p * 100 if p > 0 else 5
    if sl_pct > 6:
        sl = p * 0.94; sl_pct = 6.0; sl_lbl = "6% hard cap"

    rule = setup
    if rule in ("BREAKOUT", "VCP"):
        ea = p; ec = round(h52 * 1.005, 1); er = round(h52 * 0.99, 1)
        note = ("Buy the breakout above Rs." + str(round(h52,1)) + ". "
                "Aggressive: buy now at market. "
                "Conservative: wait for daily close above Rs." + str(round(h52*1.005,1)) + " with 1.5x+ volume. "
                "Retest: if price pulls back to Rs." + str(round(er,1)) + " that is the safest second entry.")
    elif rule == "BULL_FLAG":
        ea = fh; ec = round(fh * 1.01, 1); er = round(fh * 0.995, 1)
        note = ("Buy above flag high Rs." + str(round(fh,1)) + " only — do NOT buy inside the flag. "
                "Aggressive: buy as price breaks above Rs." + str(round(fh,1)) + ". "
                "Conservative: buy next candle after a breakout close. "
                "Retest: flag high becomes support at Rs." + str(round(er,1)) + ".")
    elif rule == "EMA_PULLBACK":
        te = e20 if near20 else e50
        en = "EMA20" if near20 else "EMA50"
        ea = round(te * 1.002, 1); ec = round(te * 1.01, 1); er = round(te * 0.998, 1)
        note = (en + " pullback entry. "
                "Aggressive: buy as price reclaims " + en + " at Rs." + str(round(ea,1)) + ". "
                "Conservative: first green daily candle closing above " + en + ". "
                "Retest: if " + en + " is touched again at Rs." + str(round(er,1)) + " without breaking down = second entry.")
    elif rule in ("SECOND_LEG", "FLAT_BASE"):
        ea = bh; ec = round(bh * 1.01, 1); er = round(bh * 0.995, 1)
        note = ("Enter on break above base high Rs." + str(round(bh,1)) + " on volume. "
                "Aggressive: buy as price clears Rs." + str(round(bh,1)) + ". "
                "Conservative: wait for 1.5x+ volume on breakout candle. "
                "Retest: Rs." + str(round(er,1)) + " becomes support if retested.")
    else:
        ea = ec = er = 0; note = "No entry — wait for a tradeable pattern."

    r  = p - sl
    t1 = round(p + 1.5 * r, 1)
    t2 = round(p + 3.0 * r, 1)
    t3 = round(p + 5.0 * r, 1)
    ra = capital * risk_pct / 100
    rps = p * sl_pct / 100
    qty = int(ra / rps) if rps > 0 else 0

    return {
        "viable": True, "final": final, "verdict": verdict, "vc": vc,
        "ea": ea, "ec": ec, "er": er, "note": note,
        "sl": sl, "sl_pct": round(sl_pct, 1), "sl_lbl": sl_lbl,
        "t1": t1, "t2": t2, "t3": t3, "rr": 3.0,
        "qty": qty, "pos_val": round(qty * p), "ra": round(ra),
        "e10": e10,
    }

def get_returns(df, ndf):
    p = safe(df["Close"].iloc[-1])
    r6 = r12 = rs = None
    if len(df) >= 126:
        p6 = safe(df["Close"].iloc[-126])
        if p6 > 0: r6 = (p - p6) / p6 * 100
    if len(df) >= 252:
        p12 = safe(df["Close"].iloc[-252])
        if p12 > 0: r12 = (p - p12) / p12 * 100
    if ndf is not None and len(ndf) >= 126 and r6 is not None:
        np_ = safe(ndf["Close"].iloc[-1]); np6 = safe(ndf["Close"].iloc[-126])
        if np6 > 0: rs = r6 - (np_ - np6) / np6 * 100
    return r6, r12, rs

def liq_gate(df):
    p  = safe(df["Close"].iloc[-1])
    av = df["Volume"].tail(50).mean()
    to = av * p
    return to, to >= 25_00_00_000

# ── SIMPLE HTML CARD HELPERS (no nesting, no logic inside HTML) ───────────────
def metric_card(label, value, color, sub="", desc=""):
    sub_html  = "<div style='color:#8b949e;font-size:10px;margin-top:2px;'>" + sub  + "</div>" if sub  else ""
    desc_html = "<div style='color:#6e7681;font-size:9px;margin-top:4px;line-height:1.4;'>" + desc + "</div>" if desc else ""
    return (
        "<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 12px;margin-bottom:2px;'>"
        "<div style='color:#8b949e;font-size:9px;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;'>" + label + "</div>"
        "<div style='color:" + color + ";font-size:14px;font-weight:800;font-family:monospace;'>" + value + "</div>"
        + sub_html + desc_html +
        "</div>"
    )

def flag_card(ftype, title, message):
    colors = {"bull": "#3fb950", "warn": "#e3b341", "bear": "#f85149", "info": "#58a6ff"}
    icons  = {"bull": "▲", "warn": "◆", "bear": "▼", "info": "●"}
    c = colors.get(ftype, "#8b949e")
    i = icons.get(ftype, "•")
    return (
        "<div style='background:#0d1117;border:1px solid " + c + "25;border-left:3px solid " + c + ";border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;'>"
        "<div style='color:" + c + ";font-size:11px;font-weight:700;margin-bottom:3px;'>" + i + " " + title + "</div>"
        "<div style='color:#8b949e;font-size:11px;line-height:1.5;'>" + message + "</div>"
        "</div>"
    )

def level_card(label, value, color, sub=""):
    sub_html = "<div style='color:#8b949e;font-size:9px;margin-top:3px;'>" + sub + "</div>" if sub else ""
    return (
        "<div style='background:#0d1117;border:1px solid " + color + "30;border-radius:6px;padding:10px;'>"
        "<div style='color:#8b949e;font-size:9px;font-weight:700;margin-bottom:4px;'>" + label + "</div>"
        "<div style='color:" + color + ";font-size:13px;font-weight:800;font-family:monospace;'>" + value + "</div>"
        + sub_html +
        "</div>"
    )

def rp(val):
    if val is None: return "—"
    s = "+" if val >= 0 else ""
    return s + str(round(val, 1)) + "%"

def Rs(val):
    return "Rs." + "{:,.1f}".format(val)

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown(
        "<div style='background:#0d1117;border-bottom:1px solid #21262d;padding:10px 0;margin-bottom:12px;'>"
        "<span style='color:#58a6ff;font-size:16px;font-weight:800;font-family:monospace;letter-spacing:1px;'>📈 NSE ELITE SWING TERMINAL</span>"
        "<span style='color:#484f58;font-size:13px;'> · v7 · " + datetime.now().strftime("%a %d %b %Y") + "</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # Market regime
    with st.spinner("Checking market regime..."):
        nifty_df  = fetch_index("^NSEI")
        bnifty_df = fetch_index("^NSEBANK")
        vix_df    = fetch_index("^INDIAVIX")

    regime_rows, regime_pen = market_regime(nifty_df, bnifty_df)
    vix_val = safe(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df) > 0 else None

    # Regime bar using Streamlit columns (not HTML)
    rcols = st.columns(4)
    for i, (name, status, color, pen) in enumerate(regime_rows):
        dot  = "🟢" if color == "green" else "🟠" if color == "orange" else "🔴" if color == "red" else "⚪"
        col_ = "#3fb950" if color=="green" else "#e3b341" if color=="orange" else "#f85149" if color=="red" else "#8b949e"
        pen_txt = " (-" + str(pen) + " pts)" if pen > 0 else ""
        with rcols[i]:
            st.markdown(
                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;'>"
                "<div style='color:#8b949e;font-size:9px;font-weight:700;'>" + name + "</div>"
                "<div style='color:" + col_ + ";font-size:13px;font-weight:700;'>" + dot + " " + status + "</div>"
                "<div style='color:#484f58;font-size:10px;'>" + pen_txt + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
    if vix_val is not None:
        vix_col = "#3fb950" if vix_val < 15 else "#e3b341" if vix_val < 20 else "#f85149"
        vix_lbl = "LOW" if vix_val < 15 else "ELEVATED" if vix_val < 20 else "HIGH"
        with rcols[3]:
            st.markdown(
                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;'>"
                "<div style='color:#8b949e;font-size:9px;font-weight:700;'>INDIA VIX</div>"
                "<div style='color:" + vix_col + ";font-size:13px;font-weight:700;'>" + str(round(vix_val,1)) + " (" + vix_lbl + ")</div>"
                "<div style='color:#484f58;font-size:10px;'>Volatility index</div>"
                "</div>",
                unsafe_allow_html=True
            )

    # Regime warnings
    if regime_pen >= 20:
        st.error("🚫 CAPITAL PRESERVATION MODE — Nifty is below 200 EMA (bearish phase). Only setups scoring 85+ qualify. Cut all position sizes by 50%. Prioritize protecting capital over finding trades.")
    elif regime_pen >= 10:
        st.warning("⚠️ CAUTION MODE — Market below 50 EMA. Half position sizes. No new breakout entries on red days. Prefer EMA pullback setups only.")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Stock Analyzer","📚 Setup School","📡 Chartink Scanners","📋 System Rules","🏭 Sector Watch"])

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 1 — STOCK ANALYZER
    # ════════════════════════════════════════════════════════════════════════════
    with tab1:
        col_l, col_r = st.columns([1, 2], gap="large")

        with col_l:
            st.markdown("#### 🔍 Stock Lookup")
            symbol  = st.text_input("NSE Symbol", placeholder="e.g. DATAPATTNS, BEL, TCS").upper().strip()
            pick    = st.selectbox("Or pick from popular list", [""] + POPULAR)
            if pick: symbol = pick
            capital = st.number_input("Trading Capital (Rs.)", min_value=100000, max_value=10000000, value=300000, step=50000, format="%d")
            risk_pct= st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25, help="1% standard. Use 0.5% on uncertain days.")
            go      = st.button("⚡ Detect Setup & Analyze", use_container_width=True)

            st.markdown("---")
            st.markdown("**Setup types detected:**")
            for key, meta in SETUP_META.items():
                if key == "NO_SETUP": continue
                st.markdown(meta["icon"] + " **" + meta["label"] + "** — " + meta["tagline"])

        with col_r:
            if not go:
                st.info("Enter a stock symbol on the left and click Analyze. The app detects which swing trading setup the stock is currently in, then scores it accordingly. Each setup type has different scoring weights, entry rules, and stop loss anchors.")

            elif symbol:
                with st.spinner("Fetching " + symbol + "..."):
                    df, ticker = fetch_stock(symbol)

                if df is None:
                    st.error("Could not fetch '" + symbol + "'. Check the NSE symbol and try again. Examples: RELIANCE, TCS, HDFCBANK, DATAPATTNS, BEL")
                else:
                    df = enrich(df)
                    to, liq_ok = liq_gate(df)
                    if not liq_ok:
                        st.error("LIQUIDITY FAIL — Daily turnover Rs." + str(round(to/1e7,1)) + " Cr is below the Rs.25 Cr minimum. Execution risk is too high. Find a more liquid stock.")
                    else:
                        r6, r12, rs     = get_returns(df, nifty_df)
                        setup, sd       = detect_setup(df)
                        scores, flags, raw = score_setup(setup, sd, r6, r12, rs)
                        trade           = build_trade(setup, sd, raw, capital, risk_pct, regime_pen)
                        meta            = SETUP_META[setup]
                        color           = meta["color"]

                        l     = df.iloc[-1]
                        p     = safe(l["Close"])
                        prev  = safe(df["Close"].iloc[-2])
                        dchg  = (p - prev) / prev * 100 if prev > 0 else 0
                        h52   = safe(l["H52"], p)
                        e10   = safe(l["E10"]); e20 = safe(l["E20"]); e50 = safe(l["E50"]); e200 = safe(l["E200"])
                        vr_   = safe(l["VR"], 1.0)
                        rsi_  = safe(l["RSI"], 50)
                        mac_  = safe(l["MACD"]); hist_ = safe(l["HIST"])
                        pct_h = (h52 - p) / h52 * 100 if h52 > 0 else 0

                        # Spike check
                        if abs(dchg) >= 10:   spike_pen = -20; spike_msg = "SPIKE -20pts: +" + str(round(abs(dchg),1)) + "% today. Do not chase. Wait 2–3 days."
                        elif abs(dchg) >= 8:  spike_pen = -10; spike_msg = "BIG MOVE -10pts: +" + str(round(abs(dchg),1)) + "% today. Wait for next session before entering."
                        elif abs(dchg) >= 5:  spike_pen = -5;  spike_msg = "MOVE -5pts: +" + str(round(abs(dchg),1)) + "% today. Slightly extended — prefer next day entry."
                        else:                  spike_pen = 0;   spike_msg = ""

                        final_score = max(0, trade.get("final", raw - regime_pen) + spike_pen)

                        # ── STOCK HEADER ──────────────────────────────────────
                        d_col = "#3fb950" if dchg >= 0 else "#f85149"
                        d_arr = "▲" if dchg >= 0 else "▼"
                        st.markdown(
                            "<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;'>"
                            "<div>"
                            "<div style='color:#58a6ff;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:3px;'>" + ticker + " · " + df.index[-1].strftime("%d %b %Y") + " · Turnover Rs." + str(round(to/1e7,1)) + "Cr ✓</div>"
                            "<div style='color:#c9d1d9;font-size:26px;font-weight:800;font-family:monospace;'>Rs." + "{:,.2f}".format(p) + "</div>"
                            "</div>"
                            "<div style='text-align:right;'>"
                            "<div style='color:" + d_col + ";font-size:16px;font-weight:700;font-family:monospace;'>" + d_arr + " " + str(round(abs(dchg),2)) + "%</div>"
                            "<div style='color:#484f58;font-size:10px;'>Today</div>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        if spike_msg:
                            st.warning(spike_msg)

                        # ── SETUP BANNER ──────────────────────────────────────
                        st.markdown(
                            "<div style='background:#0d1117;border:1px solid " + color + "30;border-left:4px solid " + color + ";border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:12px;'>"
                            "<div style='color:" + color + ";font-size:11px;font-weight:700;margin-bottom:4px;'>" + meta["icon"] + " SETUP DETECTED: " + meta["label"].upper() + " · " + meta["risk"] + " RISK · Hold: " + meta["hold"] + "</div>"
                            "<div style='color:" + color + ";font-size:13px;font-weight:700;margin-bottom:6px;'>" + meta["tagline"] + "</div>"
                            "<div style='color:#8b949e;font-size:12px;line-height:1.6;'>" + meta["description"] + "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ── DATA TILES ────────────────────────────────────────
                        h52_col = "#3fb950" if pct_h<=3 else "#e3b341" if pct_h<=10 else "#f85149"
                        vr_col  = "#3fb950" if vr_>=1.5 else "#e3b341" if vr_>=1 else "#f85149"
                        rsi_col = "#3fb950" if 50<=rsi_<=65 else "#e3b341" if rsi_<80 else "#f85149"
                        mac_col = "#3fb950" if mac_>0 and hist_>0 else "#e3b341" if mac_>0 else "#f85149"
                        e20_col = "#3fb950" if p>e20 else "#f85149"
                        e50_col = "#3fb950" if e20>e50 else "#f85149"
                        e200_col= "#3fb950" if e50>e200 else "#f85149"
                        r6_col  = "#3fb950" if r6 and r6>=20 else "#e3b341" if r6 and r6>=0 else "#f85149"

                        h52_sub = "ABOVE HIGH" if pct_h<=0 else str(round(pct_h,1))+"% below"
                        mac_dir = "UP " if mac_>0 else "DN "

                        c1,c2,c3,c4 = st.columns(4)
                        with c1: st.markdown(metric_card("52W HIGH","Rs."+"{:,.1f}".format(h52),h52_col,h52_sub,"Distance from peak. Near = momentum. Far = catching falling knife."),unsafe_allow_html=True)
                        with c2: st.markdown(metric_card("VOLUME",str(round(vr_,1))+"x avg",vr_col,"vs 50D average","Above 1.5x = institutional activity. Below 0.8x on dip = healthy pullback."),unsafe_allow_html=True)
                        with c3: st.markdown(metric_card("RSI (14)",str(round(rsi_)),rsi_col,"14-period RSI","Sweet spot: 50–65. Above 75 = overbought/avoid. Below 45 = weakening."),unsafe_allow_html=True)
                        with c4: st.markdown(metric_card("MACD",mac_dir+str(round(abs(mac_),2)),mac_col,"histogram: "+str(round(hist_,2)),"Positive+expanding = best entry. Negative = avoid."),unsafe_allow_html=True)

                        c5,c6,c7,c8 = st.columns(4)
                        with c5: st.markdown(metric_card("EMA 20","Rs."+"{:,.1f}".format(e20),e20_col,"above" if p>e20 else "below","Primary swing trend filter. Price must be above."),unsafe_allow_html=True)
                        with c6: st.markdown(metric_card("EMA 50","Rs."+"{:,.1f}".format(e50),e50_col,"20>50" if e20>e50 else "20<50","Medium-term trend. EMA20 > EMA50 = bullish."),unsafe_allow_html=True)
                        with c7: st.markdown(metric_card("EMA 200","Rs."+"{:,.1f}".format(e200),e200_col,"50>200" if e50>e200 else "50<200","Long-term Stage 2 line. Everything above = bullish."),unsafe_allow_html=True)
                        with c8: st.markdown(metric_card("6M RETURN",rp(r6),r6_col,"12M: "+rp(r12),"Leaders return 20%+ when market returns 5–10%."),unsafe_allow_html=True)

                        st.markdown("---")

                        # ── SCORE CARD ────────────────────────────────────────
                        vc      = trade.get("vc", "#484f58")
                        verdict = trade.get("verdict", "—")
                        final   = trade.get("final", 0)
                        rp_s    = " — Regime: -" + str(regime_pen) if regime_pen > 0 else ""
                        sp_s    = " — Spike: " + str(spike_pen) if spike_pen < 0 else ""
                        sub_sc  = "Raw: " + str(raw) + rp_s + sp_s + " = Final: " + str(final_score)

                        st.markdown(
                            "<div style='background:#0d1117;border:1px solid " + vc + "30;border-radius:8px;padding:20px;margin-bottom:14px;display:flex;align-items:center;gap:24px;'>"
                            "<div style='text-align:center;min-width:100px;border-right:1px solid #21262d;padding-right:24px;'>"
                            "<div style='font-size:64px;font-weight:900;color:" + vc + ";font-family:monospace;line-height:1;'>" + str(final_score) + "</div>"
                            "<div style='color:#484f58;font-size:11px;'>/100</div>"
                            "</div>"
                            "<div>"
                            "<div style='color:" + vc + ";font-size:16px;font-weight:800;letter-spacing:0.5px;margin-bottom:6px;'>" + verdict + "</div>"
                            "<div style='color:#484f58;font-size:10px;font-family:monospace;margin-bottom:8px;'>" + sub_sc + "</div>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ── SCORE BREAKDOWN ───────────────────────────────────
                        st.markdown("**Score Breakdown — " + meta["label"] + " weights:**")
                        for key, max_pts in meta["weights"].items():
                            sc_val = scores.get(key, 0)
                            pct_s  = min(int(sc_val / max_pts * 100), 100) if max_pts > 0 else 0
                            col_s  = "#3fb950" if pct_s >= 75 else "#e3b341" if pct_s >= 50 else "#f85149"
                            sym_s  = "✓" if pct_s >= 75 else "~" if pct_s >= 50 else "✗"
                            st.markdown(
                                "<div style='margin-bottom:8px;'>"
                                "<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
                                "<span style='color:#c9d1d9;font-size:12px;'>" + key + "</span>"
                                "<span style='color:" + col_s + ";font-size:12px;font-weight:700;'>" + sym_s + " " + str(sc_val) + "/" + str(max_pts) + "</span>"
                                "</div>"
                                "<div style='height:4px;background:#21262d;border-radius:2px;overflow:hidden;'>"
                                "<div style='height:100%;width:" + str(pct_s) + "%;background:" + col_s + ";border-radius:2px;'></div>"
                                "</div>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                        # ── SIGNAL FLAGS ──────────────────────────────────────
                        if flags:
                            st.markdown("**Signal Analysis — why this score:**")
                            for ft, title, msg in flags:
                                st.markdown(flag_card(ft, title, msg), unsafe_allow_html=True)

                        # ── TRADE PLAN ────────────────────────────────────────
                        if trade.get("viable"):
                            st.markdown("---")

                            # What to watch
                            if meta["checklist"]:
                                st.markdown("**What to watch before entering:**")
                                for item in meta["checklist"]:
                                    st.markdown("- " + item)
                                st.markdown("**Entry trigger:** " + meta["trigger"])

                            st.markdown("---")
                            st.markdown("**Entry Plan:**")
                            st.info(trade["note"])

                            st.markdown("**Trade Levels:**")
                            lc1,lc2,lc3,lc4 = st.columns(4)
                            ea_s = Rs(trade["ea"]) if trade.get("ea",0)>0 else "See plan"
                            ec_s = Rs(trade["ec"]) if trade.get("ec",0)>0 else "See plan"
                            er_s = Rs(trade["er"]) if trade.get("er",0)>0 else "See plan"
                            with lc1: st.markdown(level_card("AGGRESSIVE ENTRY", ea_s, "#58a6ff", "Buy now / at open"), unsafe_allow_html=True)
                            with lc2: st.markdown(level_card("CONSERVATIVE", ec_s, "#79c0ff", "Wait for confirm"), unsafe_allow_html=True)
                            with lc3: st.markdown(level_card("STOP LOSS " + str(trade["sl_pct"]) + "%", Rs(trade["sl"]), "#f85149", trade["sl_lbl"]), unsafe_allow_html=True)
                            with lc4: st.markdown(level_card("RETEST ENTRY", er_s, "#484f58", "If price pulls back"), unsafe_allow_html=True)

                            tc1,tc2,tc3 = st.columns(3)
                            t1_g = rp((trade["t1"]-p)/p*100) + " · 1.5R · Book 30%"
                            t2_g = rp((trade["t2"]-p)/p*100) + " · 3R  · Book 30%"
                            t3_g = rp((trade["t3"]-p)/p*100) + " · 5R  · Trail 40%"
                            with tc1: st.markdown(level_card("TARGET 1", Rs(trade["t1"]), "#e3b341", t1_g), unsafe_allow_html=True)
                            with tc2: st.markdown(level_card("TARGET 2", Rs(trade["t2"]), "#3fb950", t2_g), unsafe_allow_html=True)
                            with tc3: st.markdown(level_card("TARGET 3", Rs(trade["t3"]), "#56d364", t3_g), unsafe_allow_html=True)

                            rr_col = "#3fb950" if trade["rr"] >= 3 else "#f85149"
                            st.markdown(
                                "<div style='background:#0d1117;border:1px solid " + rr_col + "25;border-radius:6px;padding:10px;text-align:center;margin:8px 0;'>"
                                "<span style='color:#8b949e;'>RISK : REWARD = </span>"
                                "<span style='color:" + rr_col + ";font-size:16px;font-weight:800;font-family:monospace;'>1 : " + str(trade["rr"]) + "</span>"
                                "<span style='color:" + rr_col + ";font-size:11px;'> (minimum 3:1 met)</span>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            ps_s  = str(trade["qty"]) + " shares · Rs." + "{:,.0f}".format(trade["pos_val"])
                            ra_s  = "Rs." + "{:,.0f}".format(trade["ra"])
                            st.markdown(
                                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px;margin-bottom:8px;'>"
                                "<div style='color:#8b949e;font-size:10px;font-weight:700;margin-bottom:4px;'>POSITION SIZE — " + str(risk_pct) + "% risk on Rs." + "{:,}".format(int(capital)) + "</div>"
                                "<div style='color:#58a6ff;font-size:14px;font-weight:700;font-family:monospace;'>" + ps_s + "</div>"
                                "<div style='color:#6e7681;font-size:11px;margin-top:3px;'>Max risk = " + ra_s + " · Stop at " + Rs(trade["sl"]) + "</div>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            # Exit plan
                            st.markdown("**Exit Plan:**")
                            e10_s = Rs(trade.get("e10",0))
                            sl_s  = Rs(trade["sl"])
                            t1_s  = Rs(trade["t1"]); t2_s = Rs(trade["t2"])
                            for ft, title, msg in [
                                ("info","Place GTT Stop Immediately","The moment your order fills, place GTT stop at " + sl_s + ". Not later. Not tomorrow. A trade without a stop is gambling, not trading."),
                                ("info","At Target 1 (" + t1_s + ")","Book 30% of position. Move stop up to your exact entry price. The trade is now risk-free — you cannot lose money even if it reverses."),
                                ("info","At Target 2 (" + t2_s + ")","Book another 30%. Move stop to T1 level. Let the remaining 40% continue running."),
                                ("info","Trailing the Final 40%","Trail stop using daily close below EMA10 (" + e10_s + "). When EMA10 rises, raise your stop. Never lower it."),
                                ("bear","Hard Stop — No Debate","If price closes below " + sl_s + ", exit the ENTIRE position next day at market open. No hoping. No averaging. No excuses."),
                                ("warn","Time Stop","No meaningful progress in 15 trading days after entry? Exit and redeploy. Stuck money has an opportunity cost."),
                                ("warn","Pre-Event Exit","Exit 1 day before: quarterly results, RBI policy, Budget, major global events. Holding through events on a swing trade is speculation."),
                            ]:
                                st.markdown(flag_card(ft, title, msg), unsafe_allow_html=True)

                        elif not trade.get("viable"):
                            st.error("NO TRADE — " + trade.get("reason","Score below minimum for this setup."))

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 2 — SETUP SCHOOL
    # ════════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## 📚 Setup School")
        st.markdown("A complete guide to every setup the analyzer detects. Understanding WHY each setup works makes you a better trader.")

        for key, meta in SETUP_META.items():
            if key == "NO_SETUP": continue
            with st.expander(meta["icon"] + " " + meta["label"] + " — " + meta["tagline"]):
                st.markdown("**What is it?**")
                st.markdown(meta["description"])
                st.markdown("**What to look for:**")
                for item in meta["checklist"]:
                    st.markdown("- " + item)
                st.success("**Entry trigger:** " + meta["trigger"])
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Risk Profile", meta["risk"])
                with col_b:
                    st.metric("Ideal Hold Period", meta["hold"])
                st.markdown("**Scoring weights for this setup:**")
                for k, v in meta["weights"].items():
                    st.markdown("- **" + k + " (" + str(v) + " pts)**")

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 3 — CHARTINK SCANNERS
    # ════════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## 📡 Chartink Scanners")
        st.markdown("Ready-to-use scanner codes with full explanations. Go to **chartink.com → Screens → Create New Screen → paste code → Generate**. Run after 4 PM IST.")

        for sc in SCANNERS:
            with st.expander(sc["name"] + " — " + sc["priority"]):
                st.markdown("**What it finds:** " + sc["what"])
                st.markdown("**Why it works:** " + sc["why"])
                st.markdown("**When to run:** " + sc["when"])
                st.success("**Action on results:** " + sc["action"])
                st.markdown("**Each condition explained:**")
                for cond, expl in sc["conditions"]:
                    st.markdown(flag_card("info", cond, expl), unsafe_allow_html=True)
                st.markdown("**Chartink Code — copy and paste:**")
                st.code(sc["code"], language="text")

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 4 — SYSTEM RULES
    # ════════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## 📋 Elite Swing Trading Rules")
        st.markdown("These rules exist because professional traders discovered them the hard way — through losses. Every rule has a specific reason.")

        rule_sections = [
            ("🎯 The Prime Directive", [
                ("No trade is the best trade","When setup is unclear, market is weak, or you're unsure — do nothing. Preserving capital means you live to trade another day. Missing a trade costs nothing. Making a bad trade can cost weeks of gains."),
                ("Score minimums are not optional","Each setup has a minimum score. Below it, the statistical edge disappears. Trading below minimum is no different from gambling."),
                ("3:1 minimum risk-reward","Stop 5% away? Target must be 15% away. With 3:1, you can be right only 35% of the time and still be profitable over the long run."),
            ]),
            ("💰 Position Sizing Rules", [
                ("1% risk per trade maximum","At 1%, 20 consecutive losses leaves you with 82% of capital. At 3%, you're down 46%. The math is unforgiving."),
                ("0.5% on uncertain days","F&O expiry, high VIX (above 20), Caution/Bearish market regime — cut to half size. You don't need to make money every day."),
                ("25% max in any single stock","Unexpected news can gap a stock down 20% overnight. Concentration kills accounts."),
                ("5 positions maximum","More than 5 and you can't monitor them. When markets move against you (and they will), you need to react fast."),
                ("5% total portfolio heat max","Add up risk on all open positions. Total should never exceed 5% of capital."),
            ]),
            ("🚫 Hard Rules — Never Break", [
                ("GTT stop immediately after entry","The moment your order fills, place the GTT stop. Most accounts are destroyed not by bad entries but by refusing to exit when the stop is hit."),
                ("Never average down","If a trade goes against you to the stop, exit — don't add more. Averaging down turns a small loss into a large one."),
                ("Never widen your stop","You set the stop based on the chart, before emotion entered. When price approaches, do NOT move it wider. Trust your pre-trade analysis."),
                ("No trades in first 15 minutes","9:15–9:30 AM is dominated by overnight order unwinding and gap fills. Spreads are widest, moves most random."),
                ("No new entries after 3:15 PM","Institutional rebalancing and closing auction orders distort prices. Never open a new swing position in this window."),
                ("No earnings holds","Always check if your stock has results in the next 5 days. Even the most bullish setup can gap down 20% on bad results."),
                ("No revenge trades","After a stop loss, step away 15 minutes minimum. The urge to immediately recover a loss is the most dangerous emotion in trading."),
            ]),
            ("🇮🇳 Indian Market Specific Rules", [
                ("F&O Expiry Awareness","NSE monthly expiry = last Thursday of month. Weekly = every Thursday. On expiry: 0.5% risk only. Expect higher intraday volatility. No new entries between 1–3 PM (max pain pinning)."),
                ("Bank Nifty as leading indicator","Bank Nifty often leads Nifty. If Bank Nifty is weak while Nifty is flat, expect Nifty to follow lower. Avoid banking/NBFC stocks when Bank Nifty is below its 50 EMA."),
                ("FII vs DII data","Check NSE provisional FII/DII data after 3:30 PM. If FIIs are selling Rs.3000+ Cr net, reduce all position sizes next day. FII selling is the strongest predictor of short-term market direction in India."),
                ("Delivery percentage on breakouts","Check NSE delivery % for breakout stocks. Above 40% delivery = high conviction. Below 30% = possible operator/intraday activity. Be cautious."),
                ("Corporate actions check","Before entering any trade, check for ex-dividend, bonus, split, or AGM/EGM dates within 10 days. These create gaps that can trigger your stop."),
                ("RBI policy and Budget dates","Mark RBI MPC meeting dates and Budget date on your calendar. Reduce open positions by 50% the day before. These can move sectors by 5–10% in a session."),
                ("Operator activity warning","Stocks with average daily turnover below Rs.50 Cr that suddenly show 5x+ volume are often operator-driven. Do not chase. Wait for 3+ days of sustained volume before trusting the move."),
            ]),
            ("📅 Daily Routine", [
                ("Pre-market 9 AM","Check Nifty and Bank Nifty futures direction. Check India VIX. Set GTT orders for watchlist stocks. Review open positions — any news?"),
                ("9:15–9:30 AM","Watch only. No new trades. Let the opening auction settle."),
                ("9:30–11:00 AM","Primary execution window. Your GTT orders will trigger here if setups fire."),
                ("11:00 AM–2:30 PM","Low conviction period. Avoid new entries unless a setup fires with very clear conviction."),
                ("2:30–3:15 PM","Monitor existing positions. Trail stops if approaching targets."),
                ("After 4 PM","Run Chartink scanners (Tier 1 first). Build next day watchlist. Check results calendar for next 5 days. Update trading journal."),
            ]),
        ]

        for section_title, rules in rule_sections:
            with st.expander(section_title):
                for rule_title, rule_desc in rules:
                    st.markdown("**" + rule_title + "**")
                    st.markdown(rule_desc)
                    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # TAB 5 — SECTOR WATCH
    # ════════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("## 🏭 Sector Watch")
        st.markdown("Scan an entire sector to find the strongest stocks. Results are ranked by score.")

        selected = st.selectbox("Select Sector to Scan", list(SECTORS.keys()))
        scan_btn = st.button("📡 Scan " + selected + " Sector")

        if scan_btn:
            stocks  = SECTORS[selected]
            results = []
            prog    = st.progress(0)
            status_txt = st.empty()

            for i, sym in enumerate(stocks):
                status_txt.text("Scanning " + sym + "...")
                try:
                    df_s, tkr_s = fetch_stock(sym)
                    if df_s is None:
                        results.append({"sym": sym, "setup": "NO DATA", "score": 0, "color": "#484f58", "price": "—", "verdict": "—", "r6": "—", "r12": "—"})
                    else:
                        df_s = enrich(df_s)
                        to_s, lq_s = liq_gate(df_s)
                        if not lq_s:
                            results.append({"sym": sym, "setup": "LIQ FAIL", "score": 0, "color": "#484f58", "price": Rs(safe(df_s["Close"].iloc[-1])), "verdict": "SKIP", "r6": "—", "r12": "—"})
                        else:
                            r6_s, r12_s, rs_s = get_returns(df_s, nifty_df)
                            setup_s, sd_s     = detect_setup(df_s)
                            sc_s, fl_s, raw_s = score_setup(setup_s, sd_s, r6_s, r12_s, rs_s)
                            trd_s             = build_trade(setup_s, sd_s, raw_s, capital, 1.0, regime_pen)
                            meta_s            = SETUP_META[setup_s]
                            results.append({
                                "sym":     sym,
                                "setup":   meta_s["icon"] + " " + setup_s.replace("_"," "),
                                "score":   trd_s.get("final", raw_s - regime_pen),
                                "color":   meta_s["color"],
                                "price":   Rs(safe(df_s["Close"].iloc[-1])),
                                "verdict": trd_s.get("verdict","—"),
                                "r6":      rp(r6_s),
                                "r12":     rp(r12_s),
                            })
                except Exception as e:
                    results.append({"sym": sym, "setup": "ERROR", "score": 0, "color": "#484f58", "price": "—", "verdict": "—", "r6": "—", "r12": "—"})
                prog.progress((i + 1) / len(stocks))

            status_txt.empty(); prog.empty()

            results.sort(key=lambda x: x["score"], reverse=True)

            # Table header
            st.markdown(
                "<div style='display:grid;grid-template-columns:80px 180px 70px 90px 90px 120px;gap:4px;"
                "background:#0d1117;border:1px solid #21262d;border-radius:6px 6px 0 0;padding:8px 12px;'>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>SYMBOL</span>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>SETUP</span>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>SCORE</span>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>6M RETURN</span>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>12M RETURN</span>"
                "<span style='color:#8b949e;font-size:10px;font-weight:700;'>VERDICT</span>"
                "</div>",
                unsafe_allow_html=True
            )

            for r in results:
                sc_c = "#3fb950" if r["score"]>=80 else "#e3b341" if r["score"]>=65 else "#f85149" if r["score"]>0 else "#484f58"
                st.markdown(
                    "<div style='display:grid;grid-template-columns:80px 180px 70px 90px 90px 120px;gap:4px;"
                    "background:#04080f;border:1px solid #21262d;border-top:none;padding:10px 12px;'>"
                    "<span style='color:#c9d1d9;font-size:12px;font-weight:700;font-family:monospace;'>" + r["sym"] + "</span>"
                    "<span style='color:" + r["color"] + ";font-size:11px;font-weight:600;'>" + r["setup"] + "</span>"
                    "<span style='color:" + sc_c + ";font-size:13px;font-weight:800;font-family:monospace;'>" + str(r["score"]) + "</span>"
                    "<span style='color:#8b949e;font-size:11px;'>" + r["r6"] + "</span>"
                    "<span style='color:#8b949e;font-size:11px;'>" + r["r12"] + "</span>"
                    "<span style='color:" + sc_c + ";font-size:11px;font-weight:600;'>" + r["verdict"] + "</span>"
                    "</div>",
                    unsafe_allow_html=True
                )

    st.markdown("---")
    st.caption("Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day delay. Always verify on NSE before trading.")

if __name__ == "__main__":
    main()
