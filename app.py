"""
NSE Elite Swing Terminal — v8 FINAL
====================================
Architecture rules (never break these):
1. ALL structure = Streamlit native: st.tabs, st.expander, st.columns, st.markdown, st.metric
2. HTML used ONLY for 3 helpers: metric_card(), flag_card(), level_card()
3. Those 3 helpers accept ONLY pre-computed plain strings — no logic, no f-strings inside
4. st.expander() titles are ALWAYS plain strings — never HTML
5. Zero nested f-strings anywhere
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ── PAGE ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Swing Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp{background:#060e1c;color:#c9d1d9;}
.main .block-container{padding-top:.5rem;max-width:1280px;}
h1,h2,h3,h4{color:#c9d1d9!important;}
.stTabs [data-baseweb="tab"]{color:#8b949e!important;font-size:13px!important;font-weight:600!important;}
.stTabs [aria-selected="true"]{color:#58a6ff!important;border-bottom-color:#58a6ff!important;}
.stButton button{background:linear-gradient(135deg,#1f6feb,#388bfd)!important;color:#fff!important;font-weight:700!important;border:none!important;border-radius:6px!important;}
.stTextInput input,.stNumberInput input{background:#0d1117!important;border:1px solid #30363d!important;color:#c9d1d9!important;border-radius:6px!important;}
.stTextInput label,.stNumberInput label,.stSelectbox label,.stSlider label{color:#8b949e!important;font-size:11px!important;font-weight:600!important;}
.stExpander{background:#0d1117!important;border:1px solid #21262d!important;border-radius:8px!important;}
.stExpander summary p{color:#c9d1d9!important;font-weight:600!important;}
div[data-testid="stMetricValue"]{color:#58a6ff!important;font-size:22px!important;font-weight:800!important;}
div[data-testid="stMetricLabel"]{color:#8b949e!important;font-size:11px!important;}
div[data-testid="stMetricDelta"]{font-size:11px!important;}
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
    "Defense":      ["BEL","HAL","BHEL","COCHINSHIP","GRSE","DATAPATTNS"],
    "Pharma":       ["SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AKUMS","MARKSANS"],
    "Banking":      ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK"],
    "Finance/NBFC": ["BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","SURYODAY"],
    "IT":           ["TCS","INFY","HCLTECH","WIPRO","TECHM","PERSISTENT"],
    "Auto":         ["MARUTI","TATAMOTORS","EICHERMOT","HEROMOTOCO","M&M"],
    "Capital Goods":["SIEMENS","ABB","HAVELLS","THERMAX","CUMMINSIND","POLYCAB","KAYNES"],
    "FMCG":         ["HINDUNILVR","ITC","BRITANNIA","DABUR","MARICO","NESTLEIND"],
    "Metals":       ["JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","NMDC"],
}

# Setup definitions — all plain data, no HTML
SETUPS = {
    "VCP": {
        "name":    "Volatility Contraction Pattern (VCP)",
        "icon":    "🌀",
        "color":   "#3fb950",
        "risk":    "LOW",
        "hold":    "5–15 days",
        "min":     72,
        "sl":      "ema10",
        "entry":   "breakout",
        "what":    "A series of smaller pullbacks with declining volume near highs. The stock is coiling like a spring. Minervini's primary setup.",
        "trigger": "Buy ONLY on breakout above the tight range on 2x+ volume. Do not enter before the breakout.",
        "checks":  [
            "Volume below 50-day average by 30–50% — confirms the coil",
            "Price range getting smaller each day (ATR shrinking)",
            "Stock staying above EMA20 during each pullback",
            "Within 10% of 52-week high",
        ],
        "weights": {"Volume Contraction":25,"Price Tightness":20,"52W Proximity":20,"EMA Stack":15,"RSI":10,"MACD":10},
    },
    "BREAKOUT": {
        "name":    "52-Week High Breakout",
        "icon":    "🚀",
        "color":   "#58a6ff",
        "risk":    "MEDIUM",
        "hold":    "5–20 days",
        "min":     75,
        "sl":      "ema20",
        "entry":   "breakout",
        "what":    "Price clears 52-week high on institutional volume. No overhead resistance. O'Neil, Darvas, Weinstein all use this as primary entry signal.",
        "trigger": "Daily close above 52W high on 1.5x+ volume. Or intraday when price holds above high for 30+ minutes.",
        "checks":  [
            "Volume on breakout day at least 1.5x average — non-negotiable",
            "Base before breakout at least 3 weeks",
            "Delivery percentage above 40% confirms institutional buying",
            "Breakout between 9:30–11:30 AM shows strong conviction",
        ],
        "weights": {"Breakout Volume":30,"EMA Stack":20,"52W Proximity":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "BULL_FLAG": {
        "name":    "Bull Flag",
        "icon":    "🏴",
        "color":   "#e3b341",
        "risk":    "LOW-MEDIUM",
        "hold":    "3–10 days",
        "min":     70,
        "sl":      "flag_low",
        "entry":   "flag_break",
        "what":    "Strong pole move (15–35%) followed by tight 5–10 day consolidation with declining volume. Qullamaggie's favourite setup.",
        "trigger": "Break above flag high on expanding volume. Do NOT buy inside the flag.",
        "checks":  [
            "Pole: 15–35% move in 2–3 weeks",
            "Flag: tight, 5–12 day consolidation, volume drops 40–60%",
            "Flag channel: slight downslope or flat, less than 6% range",
            "Break above flag high on volume = entry",
        ],
        "weights": {"Pole Strength":25,"Flag Tightness":25,"Volume Pattern":20,"EMA Stack":15,"RSI":10,"MACD":5},
    },
    "EMA_PULLBACK": {
        "name":    "EMA Pullback (Best Risk:Reward)",
        "icon":    "↩️",
        "color":   "#79c0ff",
        "risk":    "LOWEST",
        "hold":    "5–15 days",
        "min":     68,
        "sl":      "ema20",
        "entry":   "ema_reclaim",
        "what":    "Stock in Stage 2 uptrend dips to EMA20 with low volume then bounces. Tightest stop, best R:R of all setups.",
        "trigger": "First green daily candle closing above EMA20 on slightly higher volume.",
        "checks":  [
            "Volume MUST dry up on the dip — high volume dips are dangerous",
            "RSI drops to 45–55 range during pullback",
            "Price touches or comes within 3% of EMA20",
            "EMA20 must be rising — flat EMA20 is not a pullback zone",
        ],
        "weights": {"EMA Stack":25,"Pullback Quality":25,"Volume on Dip":20,"RS vs Nifty":15,"MACD":10,"RSI":5},
    },
    "SECOND_LEG": {
        "name":    "Second Leg / Multi-Leg Momentum",
        "icon":    "⚡",
        "color":   "#bc8cff",
        "risk":    "MEDIUM",
        "hold":    "10–30 days",
        "min":     75,
        "sl":      "base_low",
        "entry":   "base_break",
        "what":    "Big first move (30–80%), tight base, then breaks out again. HAL, BEL, DATAPATTNS ran 3–4 legs in 2023–24. Highest conviction trade.",
        "trigger": "Breakout above base high with 1.5x+ volume. The base IS the setup — it needs to break first.",
        "checks":  [
            "First leg: at least 30% move from base to peak",
            "Correction: less than 35% (tight = institutions holding)",
            "Volume dries up completely during the base",
            "MACD stays positive throughout the base",
        ],
        "weights": {"First Leg":25,"Base Quality":25,"Breakout Volume":20,"RS vs Nifty":15,"MACD":10,"EMA Stack":5},
    },
    "FLAT_BASE": {
        "name":    "Flat Base",
        "icon":    "📊",
        "color":   "#56d364",
        "risk":    "LOW",
        "hold":    "5–20 days",
        "min":     68,
        "sl":      "base_low",
        "entry":   "base_break",
        "what":    "Stock sideways in tight range (<8%) for 3–6 weeks near highs with declining volume. O'Neil CANSLIM pattern.",
        "trigger": "Breakout above the top of the flat base on 1.5x+ volume.",
        "checks":  [
            "Range of last 20 days less than 8% (less than 5% = exceptional)",
            "Duration at least 3 weeks (15 trading days)",
            "Volume declining throughout the base",
            "Price within 15% of 52-week high",
        ],
        "weights": {"Base Tightness":30,"52W Proximity":20,"Volume Dryup":20,"EMA Stack":15,"Duration":10,"MACD":5},
    },
    "NO_SETUP": {
        "name":    "No Clear Setup",
        "icon":    "⏳",
        "color":   "#484f58",
        "risk":    "DO NOT TRADE",
        "hold":    "N/A",
        "min":     999,
        "sl":      None,
        "entry":   "none",
        "what":    "No tradeable swing pattern detected. Stock is between key levels without a clear entry trigger.",
        "trigger": "Wait for a VCP, breakout, or EMA pullback to form.",
        "checks":  [],
        "weights": {},
    },
}

CHARTINK_SCANS = [
    {
        "name":   "Tier 1 — 52W High Breakout",
        "color":  "#3fb950",
        "when":   "Run FIRST after 4 PM IST every day",
        "action": "These are your highest priority trades for next session. Enter at open or on confirmed retest.",
        "what":   "Nifty 200 stocks that broke their 52-week high THIS WEEK with 1.5x+ volume and full Stage 2 EMA stack.",
        "why":    "52W high breakout on volume is the single strongest momentum signal. No overhead resistance above the high. Every seller from the past year is at breakeven or profit.",
        "code":   "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "conds":  [
            ("{nifty 200}",                   "Nifty 200 universe only — liquid large/midcaps. No penny stocks, no operator stocks."),
            ("close > 1 weeks max(52, high)", "Price IS above the 52-week high right now. The breakout is happening or just happened."),
            ("volume > 1.5x sma(volume,50)",  "Volume 50% above average. Fake breakouts on low volume fail 60%+ of the time in Indian markets."),
            ("EMA(20) > EMA(50) > EMA(200)",  "Confirmed Stage 2 uptrend across all timeframes. Critical filter."),
            ("Turnover > Rs.25 Crore",         "Minimum liquidity. Below this, your entry/exit moves the price against you."),
        ],
    },
    {
        "name":   "Tier 2 — VCP / Pre-Breakout Coil",
        "color":  "#e3b341",
        "when":   "Run second, build your GTT watchlist",
        "action": "Set GTT price alert at the 52W high for each result. Enter ONLY when price breaks with 1.5x+ volume.",
        "what":   "Nifty 200 stocks within 3% of 52W high with volume contracting. The spring is coiling.",
        "why":    "Catches setups BEFORE Tier 1 fires. Volume drying near highs = supply exhaustion = institutions accumulating quietly.",
        "code":   "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conds":  [
            ("close > 0.97x 52W high",     "Within 3% of breakout level — close enough to matter."),
            ("close < 52W high",            "Has NOT broken out yet. Anticipation, not confirmation."),
            ("sma(vol,10) < sma(vol,50)",   "10-day volume below 50-day volume = volume drying. THIS is the VCP signal."),
            ("Full EMA stack",              "Coil forming in uptrend — not a downtrend."),
        ],
    },
    {
        "name":   "Tier 3 — Momentum Leaders",
        "color":  "#bc8cff",
        "when":   "Run weekly, build momentum watchlist",
        "action": "Do NOT buy at current price. Add to watchlist. Buy only when stock dips to EMA20 with drying volume.",
        "what":   "Stage 2 stocks up 25%+ in both 6M and 12M. Proven momentum leaders.",
        "why":    "Counter-intuitive but proven: a stock already up 40% with bullish EMAs is MORE likely to keep rising. Nifty200 Momentum30 index using this principle = 19.3% CAGR over 20 years.",
        "code":   "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "conds":  [
            ("Full EMA stack",             "Confirmed Stage 2 across all timeframes."),
            ("close > 1.25x 26wk ago",    "Up at least 25% in 6 months. Sustained momentum."),
            ("close > 1.25x 52wk ago",    "Up at least 25% over 12 months. Not a flash move."),
        ],
    },
    {
        "name":   "Tier 4 — Pure VCP / Tight Base",
        "color":  "#79c0ff",
        "when":   "Run daily, verify each result in TradingView",
        "action": "Confirm: tightening ATR + volume bars getting smaller daily. Enter on breakout above the coiling range on 2x+ volume.",
        "what":   "Strongest VCP filter: within 10% of highs, volume contracted 25%+. Most explosive setup when it fires.",
        "why":    "When volume contracts 25%+ while price stays near highs = supply exhaustion. Breakouts from these setups are sharp and fast.",
        "code":   "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conds":  [
            ("close > 0.90x 52W high",               "Within 10% of highs — base forming near top."),
            ("EMA(20) > EMA(50) > EMA(200)",          "Base in uptrend. Critical — a coil in a downtrend is a falling knife."),
            ("sma(vol,10) < 0.75x sma(vol,50)",       "Volume contracted 25%+. The VCP squeeze is happening."),
        ],
    },
]

RULES = [
    ("🎯 Prime Directive — Capital First", [
        ("No trade is the best trade", "When setup is unclear, market is weak, or you are unsure — do nothing. Preserving capital means you live to trade another day. Missing a trade costs nothing. Making a bad trade can cost weeks of gains."),
        ("Score minimums are not optional", "Each setup has a minimum score threshold. Below it, the statistical edge disappears. Trading below minimum is gambling, not trading."),
        ("3:1 minimum risk-reward always", "If stop is 5% away, target must be at least 15% away. With 3:1 R:R you can be right only 35% of the time and still be profitable over time."),
    ]),
    ("💰 Position Sizing", [
        ("1% risk per trade maximum", "At 1%, 20 consecutive losing trades leaves you with 82% of capital. At 3%, the same losses wipe out 46%. The math does not forgive aggression."),
        ("0.5% on uncertain days", "F&O expiry, VIX above 20, bearish market regime — cut to half size. You do not need to make money every day."),
        ("25% max in any single stock", "Unexpected news can gap a stock down 20% overnight. Concentration kills accounts."),
        ("5 positions maximum, 5% total heat", "More than 5 open positions and you cannot monitor them properly. Total risk on all open trades must never exceed 5% of capital."),
    ]),
    ("🚫 Hard Rules — Never Break", [
        ("GTT stop immediately after entry", "The moment your order fills, place the GTT stop loss. Most accounts are destroyed not by bad entries but by refusing to exit when the stop is hit."),
        ("Never average down", "If a trade goes against you to the stop, EXIT — do not add more. Averaging down turns a small loss into an account-destroying one."),
        ("Never widen your stop", "You set the stop based on the chart, before emotion entered. Do not move it wider to give it more room. Trust your pre-trade analysis."),
        ("No trades 9:15–9:30 AM", "First 15 minutes dominated by gap fills and order unwinding. Spreads widest, moves most random. Watch, do not click."),
        ("No new entries after 3:15 PM", "Institutional rebalancing and closing auction distort prices. Never open a new swing position in this window."),
        ("No earnings holds", "Check if stock has results in next 5 days. Exit before. Even the most bullish setup can gap down 20% on bad results."),
        ("No revenge trades", "After a stop loss, step away 15 minutes minimum. The urge to immediately recover a loss is the most dangerous emotion in trading."),
    ]),
    ("🇮🇳 India-Specific Rules", [
        ("F&O Expiry Awareness", "Monthly expiry = last Thursday. Weekly = every Thursday. On expiry days: use 0.5% risk, no new entries between 1–3 PM (max pain pinning active), expect higher intraday volatility."),
        ("Bank Nifty leads Nifty", "If Bank Nifty is weak while Nifty is flat, Nifty will follow lower. Avoid banking/NBFC stocks when Bank Nifty is below its 50 EMA."),
        ("FII/DII data daily", "Check NSE provisional FII/DII data after 3:30 PM. If FIIs sell Rs.3000+ Cr net, reduce all position sizes next day. FII selling is the strongest predictor of Indian market direction."),
        ("Delivery percentage on breakouts", "NSE delivery % above 40% on breakout = institutional conviction. Below 30% = possible operator/intraday activity. Be very cautious."),
        ("Mark RBI and Budget dates", "Reduce open positions by 50% the day before RBI policy and Budget. These events move sectors 5–10% in a single session."),
        ("Operator stock warning", "Stocks below Rs.50 Cr daily turnover showing 5x+ volume spikes are often operator-driven. Do not chase. Wait 3+ days of sustained volume before trusting the move."),
    ]),
    ("📅 Daily Routine", [
        ("Pre-market 9 AM", "Check Nifty and Bank Nifty futures direction. Check India VIX. Set GTT orders. Review open positions — any overnight news?"),
        ("9:15–9:30 AM — Watch Only", "Do not trade the first 15 minutes. Let the opening auction settle. Observe, do not click."),
        ("9:30–11:00 AM — Primary Window", "Main execution window. Your GTT orders will trigger here if setups fire."),
        ("11 AM–2:30 PM — Low Conviction", "Avoid new entries unless a setup fires with very clear conviction."),
        ("After 4 PM — Daily Prep", "Run Chartink scanners (Tier 1 first). Build next day watchlist. Check results calendar for next 5 days. Update trading journal."),
    ]),
]

# ── SAFE FLOAT ────────────────────────────────────────────────────────────────
def sf(v, d=0.0):
    try:
        f = float(v)
        return d if (f != f) else f   # NaN check without np
    except:
        return d

# ── INDICATORS ────────────────────────────────────────────────────────────────
def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def calc_sma(s, p):
    return s.rolling(p).mean()

def calc_rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    rs = g / l.replace(0, float('nan'))
    return 100 - 100 / (1 + rs)

def calc_macd(s):
    m   = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()
    sig = m.ewm(span=9, adjust=False).mean()
    return m, m - sig   # macd line, histogram

def enrich(df):
    df = df.copy()
    c  = df["Close"]
    df["E10"]  = calc_ema(c, 10)
    df["E20"]  = calc_ema(c, 20)
    df["E50"]  = calc_ema(c, 50)
    df["E200"] = calc_ema(c, 200)
    df["V50"]  = calc_sma(df["Volume"], 50)
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=100).max()
    df["RSI"]  = calc_rsi(c)
    df["ATR"]  = (df["High"] - df["Low"]).rolling(14).mean()
    m, h       = calc_macd(c)
    df["MACD"] = m
    df["HIST"] = h
    return df

# ── FETCH ─────────────────────────────────────────────────────────────────────
def fetch(sym):
    for sfx in [".NS", ".BO"]:
        try:
            df = yf.Ticker(sym + sfx).history(period="2y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 60:
                return df.dropna(subset=["Close"]), sym + sfx
        except:
            continue
    return None, None

def fetch_idx(t):
    try:
        df = yf.Ticker(t).history(period="1y", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 50:
            return df.dropna(subset=["Close"])
    except:
        pass
    return None

# ── MARKET REGIME ─────────────────────────────────────────────────────────────
def regime(ndf, bndf):
    rows = []
    pen  = 0
    for name, df in [("Nifty 50", ndf), ("Bank Nifty", bndf)]:
        if df is None or len(df) < 50:
            rows.append((name, "UNKNOWN", "off", 0)); continue
        d    = enrich(df)
        p    = sf(d["Close"].iloc[-1])
        e50  = sf(d["E50"].iloc[-1])
        e200 = sf(d["E200"].iloc[-1])
        if p < e200:
            rows.append((name, "BEARISH — below 200 EMA", "inverse", 20)); pen = max(pen, 20)
        elif p < e50:
            rows.append((name, "CAUTION — below 50 EMA", "off", 10)); pen = max(pen, 10)
        else:
            rows.append((name, "HEALTHY — above all EMAs", "normal", 0))
    return rows, pen

# ── SETUP DETECTION ───────────────────────────────────────────────────────────
def detect(df):
    if len(df) < 40:
        return "NO_SETUP", {}
    l   = df.iloc[-1]
    p   = sf(l["Close"]); e20 = sf(l["E20"]); e50 = sf(l["E50"]); e200 = sf(l["E200"])
    h52 = sf(l["H52"], p); vr = sf(l["VR"], 1.0); mac = sf(l["MACD"]); hist = sf(l["HIST"])
    atr = sf(l["ATR"], p * 0.02)
    c20 = df["Close"].tail(20); c7 = df["Close"].tail(7)
    v10 = df["Volume"].tail(10).mean(); v50 = df["Volume"].tail(50).mean()
    pch = (h52 - p) / h52 * 100 if h52 > 0 else 100
    r20 = (c20.max() - c20.min()) / c20.mean() * 100 if c20.mean() > 0 else 100
    r7  = (c7.max()  - c7.min())  / c7.mean()  * 100 if c7.mean()  > 0 else 100
    vc  = v10 / v50 if v50 > 0 else 1.0
    m20 = (c20.iloc[-1] - c20.iloc[0]) / c20.iloc[0] * 100 if c20.iloc[0] > 0 else 0
    es  = (p > e20) and (e20 > e50) and (e50 > e200)
    n20 = abs(p - e20) / p < 0.04 if p > 0 else False
    n50 = abs(p - e50) / p < 0.05 if p > 0 else False
    d6  = df.tail(126)
    lm  = float(d6["High"].max()); lmn = float(d6["Low"].min())
    l1  = (lm - lmn) / lmn * 100 if lmn > 0 else 0
    pi  = d6["High"].idxmax(); af = d6.loc[pi:]
    bl  = float(af["Low"].min()) if len(af) > 5 else p
    bd  = (lm - bl) / lm * 100 if lm > 0 else 100
    p2p = (lm - p) / lm * 100 if lm > 0 else 100
    sd  = {
        "p":p,"e10":sf(l["E10"]),"e20":e20,"e50":e50,"e200":e200,
        "h52":h52,"pch":pch,"vr":vr,"rsi":sf(l["RSI"],50),
        "mac":mac,"hist":hist,"atr":atr,
        "r20":r20,"r7":r7,"vc":vc,"m20":m20,
        "es":es,"n20":n20,"n50":n50,
        "l1":l1,"bd":bd,"bl":bl,"p2p":p2p,
        "fh":float(c7.max()),
        "bh":float(df["High"].tail(20).max()),
        "blo":float(df["Low"].tail(20).min()),
    }
    if l1>=30 and bd<=30 and p2p<=10 and es and vr>=1.2: return "SECOND_LEG", sd
    if pch<=1.5 and vr>=1.5 and es:                      return "BREAKOUT",    sd
    if pch<=12 and r20<15 and vc<0.80 and e20>e50>e200:  return "VCP",         sd
    if m20>=12 and r7<6   and vc<0.90 and p>e20:         return "BULL_FLAG",   sd
    if r20<10  and pch<=18 and e20>e50>e200 and vc<0.95: return "FLAT_BASE",   sd
    if e50 > e200:
        if n20 and e20 > e50: return "EMA_PULLBACK", sd
        if n50 and p  > e200: return "EMA_PULLBACK", sd
    return "NO_SETUP", sd

# ── SCORE ─────────────────────────────────────────────────────────────────────
def score(setup, sd, r6, r12, rs):
    cfg  = SETUPS.get(setup, SETUPS["NO_SETUP"])
    w    = cfg["weights"]
    sc   = {}
    fl   = []  # (type, title, message) — ALL plain strings

    p=sd.get("p",0); pch=sd.get("pch",100); vr=sd.get("vr",1.0)
    rsi_=sd.get("rsi",50); mac=sd.get("mac",0); hist=sd.get("hist",0)
    r20=sd.get("r20",100); r7=sd.get("r7",100); vc=sd.get("vc",1.0)
    m20=sd.get("m20",0); es=sd.get("es",False)
    e20=sd.get("e20",0); e50=sd.get("e50",0); e200=sd.get("e200",0)
    l1=sd.get("l1",0); bd=sd.get("bd",100)
    n20=sd.get("n20",False); n50=sd.get("n50",False)

    # Helper
    def add(key, val, mx, tiers):
        # tiers: list of (min_val, fraction, ftype, title, msg)
        for mn, frac, ft, title, msg in tiers:
            if val >= mn:
                sc[key] = int(mx * frac)
                fl.append((ft, title, msg))
                return
        sc[key] = 0

    # EMA STACK
    if "EMA Stack" in w:
        mx = w["EMA Stack"]
        if p>e20>e50>e200:      sc["EMA Stack"]=mx;           fl.append(("bull","Stage 2 Confirmed (EMA Stack)","Price above EMA20 > EMA50 > EMA200. Weinstein Stage 2 — the only stage where momentum strategies work consistently. All timeframes bullish. This is the foundation of every good swing trade."))
        elif e20>e50>e200:      sc["EMA Stack"]=int(mx*.65);  fl.append(("warn","Stage 2 Forming (Price below EMA20)","EMAs are in bullish order but price is below EMA20. Trend is intact but stock is slightly weak. Wait for price to reclaim EMA20 before entering. Not ideal for aggressive entry."))
        elif e20>e50 or e50>e200: sc["EMA Stack"]=int(mx*.30); fl.append(("warn","Partial Stage 2","Only partial EMA alignment. Stage 2 is developing but not fully confirmed. Higher risk — the trend may not be established enough for a reliable swing trade."))
        else:                   sc["EMA Stack"]=0;             fl.append(("bear","EMA Stack Bearish","EMAs are in bearish order — Stage 3 (topping) or Stage 4 (downtrend). Do not buy declining stocks hoping for a recovery. Wait for Stage 2 to re-establish."))

    # 52W PROXIMITY
    if "52W Proximity" in w:
        mx = w["52W Proximity"]; pch_s = str(round(pch,1))
        if pch<=0:     sc["52W Proximity"]=mx;           fl.append(("bull","At 52-Week High — No Overhead Resistance","Stock is at or above its 52-week high. Every seller from the past year is now at breakeven or profit — no one is desperate to sell. This is maximum momentum."))
        elif pch<=2:   sc["52W Proximity"]=int(mx*.90);  fl.append(("bull","Within 2% of 52W High","Extremely close to breakout. A single strong session could trigger it. Set your GTT alert at the 52W high level now."))
        elif pch<=5:   sc["52W Proximity"]=int(mx*.75);  fl.append(("bull","Within 5% of 52W High — Launchpad Zone","Good proximity. Stock is in the pre-breakout zone. Do not enter yet — wait for the actual breakout with volume."))
        elif pch<=10:  sc["52W Proximity"]=int(mx*.50);  fl.append(("warn",pch_s+"% Below 52W High — In Base","Base formation territory. The stock is working off its prior move. Could break out or could roll over. Need other confirming signals."))
        elif pch<=20:  sc["52W Proximity"]=int(mx*.25);  fl.append(("warn",pch_s+"% Below 52W High — Extended Base","Too far from breakout zone for an ideal setup. Could be a recovery story or just a laggard. Watch but do not act yet."))
        else:          sc["52W Proximity"]=0;             fl.append(("bear","More Than 20% Below 52W High","Not a momentum setup. This far below the high, you are not buying strength — you are catching a falling knife or making a recovery bet. Avoid."))

    # VOLUME CONTRACTION
    if "Volume Contraction" in w:
        mx = w["Volume Contraction"]; pv = str(round(vc*100))
        if vc<0.40:    sc["Volume Contraction"]=mx;           fl.append(("bull","Deep Volume Contraction — " + pv + "% of Avg","Volume at only " + pv + "% of 50-day average. Near-complete supply exhaustion. Institutions have finished selling and are holding quietly. The quieter the stock gets before a breakout, the more explosive the move will be."))
        elif vc<0.60:  sc["Volume Contraction"]=int(mx*.80);  fl.append(("bull","Strong Volume Contraction — " + pv + "% of Avg","Volume at " + pv + "% of average. Healthy VCP signature. Institutions accumulating quietly while retail attention wanders. Ideal coiling behavior."))
        elif vc<0.75:  sc["Volume Contraction"]=int(mx*.55);  fl.append(("warn","Moderate Volume Contraction — " + pv + "% of Avg","Volume at " + pv + "% of average. Some drying but not deep enough for a classic VCP. Setup is developing — watch daily for further contraction."))
        else:          sc["Volume Contraction"]=int(mx*.15);  fl.append(("bear","Insufficient Volume Contraction — " + pv + "% of Avg","Volume at " + pv + "% of average — not contracting enough for VCP. Wait for volume to dry further. Without real contraction, the coil is not wound tightly enough."))

    # PRICE TIGHTNESS
    for key in ["Price Tightness", "Base Tightness"]:
        if key in w:
            mx = w[key]; rs = str(round(r20,1))
            if r20<5:    sc[key]=mx;           fl.append(("bull","Exceptional Tightness — " + rs + "% Range","20-day range only " + rs + "%. The spring is fully wound. Stocks moving less than 5% over 20 days near their highs have historically produced the most explosive breakouts."))
            elif r20<8:  sc[key]=int(mx*.80);  fl.append(("bull","Strong Tightness — " + rs + "% Range","20-day range of " + rs + "%. Solid base formation. Institutions are absorbing supply without allowing much price fluctuation — a bullish sign."))
            elif r20<12: sc[key]=int(mx*.55);  fl.append(("warn","Moderate Tightness — " + rs + "% Range","20-day range of " + rs + "%. Acceptable but not ideal. A tighter range gives higher confidence and a better-defined stop loss level."))
            elif r20<18: sc[key]=int(mx*.25);  fl.append(("warn","Loose Base — " + rs + "% Range","20-day range of " + rs + "%. Wide base suggests lower institutional conviction or distribution. Higher risk of a failed breakout."))
            else:        sc[key]=0;             fl.append(("bear","No Base Forming — " + rs + "% Range","20-day range of " + rs + "% — too wide. Price is oscillating without building structure. Wait for consolidation to tighten before considering entry."))

    # BREAKOUT VOLUME
    for key in ["Breakout Volume", "Breakout Volume"]:
        if key in w:
            mx = w[key]; vr_s = str(round(vr,1))
            if vr>=4:    sc[key]=mx;           fl.append(("bull","Exceptional Breakout Volume — " + vr_s + "x","Volume " + vr_s + "x average. Institutional stampede. Large funds are urgently building positions. Very high probability of sustained continuation."))
            elif vr>=2.5:sc[key]=int(mx*.85);  fl.append(("bull","Strong Breakout Volume — " + vr_s + "x","Volume " + vr_s + "x average. Clear institutional participation. The big players are behind this move."))
            elif vr>=1.5:sc[key]=int(mx*.65);  fl.append(("bull","Confirmed Breakout Volume — " + vr_s + "x","Volume " + vr_s + "x average — meets the minimum threshold. Breakout is real but watch next few sessions to confirm follow-through."))
            elif vr>=1.0:sc[key]=int(mx*.30);  fl.append(("warn","Below-Average Breakout Volume — " + vr_s + "x","Volume " + vr_s + "x average. Marginal — breakouts on below-average volume in Nifty 200 stocks fail more than 50% of the time. Caution."))
            else:        sc[key]=0;             fl.append(("bear","Weak Volume — " + vr_s + "x Average","Volume only " + vr_s + "x. High probability of a failed or fake breakout. Wait for a retest with better volume before considering entry."))
            break  # Only score once

    # POLE STRENGTH
    if "Pole Strength" in w:
        mx = w["Pole Strength"]; ms = str(round(m20,1))
        if m20>=35:  sc["Pole Strength"]=mx;          fl.append(("bull","Exceptional Pole — +" + ms + "% in 20 Days","Powerful institutional move. Strong poles consistently produce strong second legs after the flag. Very high conviction setup."))
        elif m20>=22:sc["Pole Strength"]=int(mx*.85); fl.append(("bull","Strong Pole — +" + ms + "%","Solid bull flag pole. The move was driven by real buying. Flag should resolve upward."))
        elif m20>=12:sc["Pole Strength"]=int(mx*.60); fl.append(("warn","Moderate Pole — +" + ms + "%","Acceptable for a bull flag but not exceptional. Follow-through from moderate poles is typically smaller. Adjust your profit targets accordingly."))
        else:        sc["Pole Strength"]=0;            fl.append(("bear","Weak Pole — +" + ms + "%","Too weak for a reliable bull flag. The follow-through from weak poles is often disappointing. Look for stronger setups."))

    # FLAG TIGHTNESS
    if "Flag Tightness" in w:
        mx = w["Flag Tightness"]; r7s = str(round(r7,1))
        if r7<3:    sc["Flag Tightness"]=mx;          fl.append(("bull","Very Tight Flag — " + r7s + "% Range","Extremely tight flag. Institutions are not selling at all during the consolidation. Highest probability bull flag setup."))
        elif r7<5:  sc["Flag Tightness"]=int(mx*.85); fl.append(("bull","Tight Flag — " + r7s + "% Range","Good flag tightness. Orderly consolidation after the pole move. This is what a healthy bull flag looks like."))
        elif r7<8:  sc["Flag Tightness"]=int(mx*.55); fl.append(("warn","Moderate Flag — " + r7s + "% Range","Acceptable but slightly wide. The wider the flag, the higher the risk of a failed breakout. Use a tighter stop."))
        else:       sc["Flag Tightness"]=0;            fl.append(("bear","Wide Flag — " + r7s + "% Range","Too wide to be called a proper flag. Risk of the full pole move being retraced is higher. Look for tighter setups."))

    # VOLUME PATTERN (bull flag)
    if "Volume Pattern" in w:
        mx = w["Volume Pattern"]
        if vc<0.55 and vr>=1.5: sc["Volume Pattern"]=mx;          fl.append(("bull","Perfect Volume Pattern","High volume on pole, very low on flag. Textbook bull flag behavior. Institutions bought aggressively on the pole and are sitting tight during the flag — not selling. Highest conviction pattern."))
        elif vc<0.75:            sc["Volume Pattern"]=int(mx*.65); fl.append(("warn","Decent Volume Pattern","Volume partially drying during flag. Good but not perfect. Watch for volume expansion on the breakout above the flag."))
        else:                    sc["Volume Pattern"]=int(mx*.20); fl.append(("bear","Volume Not Drying on Flag","Volume during flag is not significantly lower than the pole. Suggests possible distribution during consolidation. Higher risk of failed breakout."))

    # PULLBACK QUALITY
    if "Pullback Quality" in w:
        mx = w["Pullback Quality"]
        if n20 and vc<0.70:   sc["Pullback Quality"]=mx;          fl.append(("bull","Perfect EMA20 Pullback","Price resting on EMA20 with very low volume. Sellers have gone quiet. This is Minervini's ideal low-risk entry — the trend is intact and the stock is ready to bounce. Best entry of any setup type."))
        elif n20:              sc["Pullback Quality"]=int(mx*.70); fl.append(("warn","EMA20 Pullback — Volume Still High","Price is at EMA20 but volume has not dried up enough. Could be temporary support or could be distribution. Wait for volume to decline before entering."))
        elif n50 and vc<0.80: sc["Pullback Quality"]=int(mx*.55); fl.append(("warn","EMA50 Pullback — Deeper Dip","Pulled back all the way to EMA50 — deeper than ideal. Still tradeable if EMA50 is rising and RSI is not oversold. Stop loss will need to be wider."))
        else:                  sc["Pullback Quality"]=int(mx*.20); fl.append(("bear","Not at a Clean EMA Level","Price is not cleanly at EMA20 or EMA50. No clear stop loss anchor point. Wait for price to reach one of these levels before entering."))

    # VOLUME ON DIP
    if "Volume on Dip" in w:
        mx = w["Volume on Dip"]; pv2 = str(round(vc*100))
        if vc<0.50:    sc["Volume on Dip"]=mx;          fl.append(("bull","Volume Very Low on Dip — " + pv2 + "% of Avg","Nobody is panic-selling. Volume at " + pv2 + "% of average means institutions are holding all their shares through the dip. Natural, healthy pullback — the uptrend is intact."))
        elif vc<0.70:  sc["Volume on Dip"]=int(mx*.80); fl.append(("bull","Volume Drying on Dip — " + pv2 + "% of Avg","Selling is light and orderly at " + pv2 + "% of average. Profit-taking, not distribution. Good quality pullback — the trend remains healthy."))
        elif vc<0.85:  sc["Volume on Dip"]=int(mx*.50); fl.append(("warn","Volume Moderate on Dip — " + pv2 + "% of Avg","Somewhat elevated at " + pv2 + "% of average. Could be light distribution. Watch next session's volume closely before entering."))
        else:          sc["Volume on Dip"]=int(mx*.15); fl.append(("bear","High Volume on Dip — " + pv2 + "% of Avg","Volume at " + pv2 + "% during the dip is too high. Someone with significant holdings is selling. Not a healthy pullback — avoid entering until volume normalizes."))

    # FIRST LEG
    if "First Leg" in w:
        mx = w["First Leg"]; l1s = str(int(l1))
        if l1>=70:    sc["First Leg"]=mx;          fl.append(("bull","Exceptional First Leg — +" + l1s + "%","A " + l1s + "% first move proves this is a major institutional stock. Large funds built this move over months. Second legs from this kind of first move tend to be powerful and sustained."))
        elif l1>=45:  sc["First Leg"]=int(mx*.85); fl.append(("bull","Strong First Leg — +" + l1s + "%","Strong institutional interest shown. Good foundation for a second leg. The bigger the first move, the bigger the second leg tends to be."))
        elif l1>=28:  sc["First Leg"]=int(mx*.60); fl.append(("warn","Moderate First Leg — +" + l1s + "%","Acceptable but not exceptional. Second legs from smaller first moves have proportionally smaller potential upside. Adjust your profit targets."))
        else:         sc["First Leg"]=0;            fl.append(("bear","First Leg Too Small — +" + l1s + "%","Insufficient institutional conviction demonstrated. A second-leg setup needs at least a 30% first move to be reliable. Look for stocks with larger first legs."))

    # BASE QUALITY
    if "Base Quality" in w:
        mx = w["Base Quality"]; bds = str(round(bd,1))
        if bd<=12:    sc["Base Quality"]=mx;          fl.append(("bull","Very Tight Base — " + bds + "% Correction","Institutions barely sold anything after the first leg. A " + bds + "% correction means they held almost their entire position. This is the highest conviction second-leg setup."))
        elif bd<=20:  sc["Base Quality"]=int(mx*.80); fl.append(("bull","Tight Base — " + bds + "% Correction","Good base quality. Institutions took some profit but the bulk of their position is intact. Solid foundation for a second leg."))
        elif bd<=30:  sc["Base Quality"]=int(mx*.55); fl.append(("warn","Moderate Base — " + bds + "% Correction","Some distribution occurred during the base. Still tradeable but the second leg may be smaller. Ensure volume really dried up during the base."))
        else:         sc["Base Quality"]=0;            fl.append(("bear","Deep Correction — " + bds + "%","A " + bds + "% correction after the first leg suggests institutions took most of their profits. This is more of a full retracement than a healthy base."))

    # VOLUME DRYUP
    if "Volume Dryup" in w:
        mx = w["Volume Dryup"]; pv3 = str(round(vc*100))
        if vc<0.55:    sc["Volume Dryup"]=mx;          fl.append(("bull","Excellent Volume Dry-Up — " + pv3 + "% of Avg","Near-complete supply exhaustion during the base. Volume at " + pv3 + "% of average means very few people are selling. High quality flat base — breakout should be clean."))
        elif vc<0.70:  sc["Volume Dryup"]=int(mx*.75); fl.append(("bull","Good Volume Dry-Up — " + pv3 + "% of Avg","Volume declining nicely at " + pv3 + "% of average during the base. Healthy flat base behavior."))
        elif vc<0.85:  sc["Volume Dryup"]=int(mx*.45); fl.append(("warn","Partial Volume Dry-Up — " + pv3 + "% of Avg","Volume declining but not enough for a classic flat base. Give it more time — ideally wait for volume to drop below 70% of average."))
        else:          sc["Volume Dryup"]=int(mx*.10); fl.append(("bear","Volume Not Drying — " + pv3 + "% of Avg","Volume still close to average during consolidation. Could be distribution disguised as a base. Wait for real volume dry-up before considering entry."))

    # DURATION
    if "Duration" in w:
        mx = w["Duration"]
        sc["Duration"] = mx if vc < 0.90 else int(mx*.40)
        msg = "Base has been building long enough. Proper bases need at least 3 weeks to clear overhead supply. This base meets the duration requirement." if vc<0.90 else "Base may not be mature enough yet. Ideal flat bases take 3–6 weeks to develop. Consider waiting for more time to pass."
        fl.append(("bull" if vc<0.90 else "warn", "Base Duration", msg))

    # RSI
    if "RSI" in w:
        mx = w["RSI"]; rs2 = str(round(rsi_))
        if 50<=rsi_<=65:    sc["RSI"]=mx;          fl.append(("bull","RSI " + rs2 + " — Sweet Spot","RSI between 50–65 is the ideal momentum zone. Strong enough to confirm the upward trend, not yet overbought. Maximum room to run before hitting resistance."))
        elif 45<=rsi_<50:   sc["RSI"]=int(mx*.65); fl.append(("warn","RSI " + rs2 + " — Recovering","RSI is below 50 but recovering. The trend may be weakening temporarily. Watch for RSI to push above 50 to confirm the uptrend is resuming."))
        elif 65<rsi_<=72:   sc["RSI"]=int(mx*.55); fl.append(("warn","RSI " + rs2 + " — Approaching Overbought","Gaining momentum but entering caution territory. Still tradeable but be prepared for a 1–3 day pullback before continuation."))
        elif 72<rsi_<=80:   sc["RSI"]=int(mx*.20); fl.append(("warn","RSI " + rs2 + " — Overbought","Extended short-term. High risk of buying at the top of a minor wave. Wait for RSI to pull back to the 55–65 range before entering."))
        elif rsi_>80:       sc["RSI"]=0;            fl.append(("bear","RSI " + rs2 + " — Extremely Overbought","RSI above 80 signals an unsustainable short-term move. High probability of a sharp pullback before any continuation. Missing this entry is better than chasing."))
        else:               sc["RSI"]=0;            fl.append(("bear","RSI " + rs2 + " — Downtrend Territory","RSI below 45 means the stock is in a downtrend or weakening significantly. Momentum strategies have poor win rates at this RSI level."))

    # MACD
    if "MACD" in w:
        mx = w["MACD"]
        if mac>0 and hist>0: sc["MACD"]=mx;          fl.append(("bull","MACD Positive and Accelerating","MACD is positive AND the histogram is expanding — momentum is building, not topping. This is the best possible MACD state for a swing entry. The trend engine is running hot."))
        elif mac>0:          sc["MACD"]=int(mx*.65); fl.append(("warn","MACD Positive but Slowing","MACD is positive (bullish) but the histogram is shrinking. Momentum exists but is decelerating. Acceptable for entry but the move may need a rest before continuing higher."))
        elif -0.5<mac<=0:    sc["MACD"]=int(mx*.30); fl.append(("warn","MACD Near Zero — Watch for Crossover","MACD just below zero. A bullish crossover here with expanding histogram would be a strong secondary buy signal. Not ideal for entry yet."))
        else:                sc["MACD"]=0;            fl.append(("bear","MACD Negative — Avoid","MACD is negative — bearish momentum is dominating. Entering against negative MACD is an uphill battle. Wait for MACD to recover above zero."))

    # RS vs NIFTY
    if "RS vs Nifty" in w:
        mx = w["RS vs Nifty"]
        if rs is None:    sc["RS vs Nifty"]=int(mx*.50)
        elif rs>=20:      sc["RS vs Nifty"]=mx;          fl.append(("bull","Massive Outperformer — +" + str(round(rs,1)) + "% vs Nifty","This stock is outperforming Nifty 50 by " + str(round(rs,1)) + "% over 6 months. This is a genuine market leader. FIIs and large mutual funds are overweight. These are your best swing trades."))
        elif rs>=10:      sc["RS vs Nifty"]=int(mx*.85); fl.append(("bull","Outperforming Nifty — +" + str(round(rs,1)) + "%","Strong relative strength. Stock is outperforming the market. Will likely continue to lead when the market rallies."))
        elif rs>=3:       sc["RS vs Nifty"]=int(mx*.65); fl.append(("warn","Slightly Ahead of Nifty — +" + str(round(rs,1)) + "%","Marginally outperforming. Not a market leader. For the best swing trades, look for stocks outperforming Nifty by 10%+ over 6 months."))
        elif rs>=0:       sc["RS vs Nifty"]=int(mx*.35); fl.append(("warn","Matching Nifty — +" + str(round(rs,1)) + "%","Barely keeping pace with the index. Not a leader. Best swing trades strongly outperform the index."))
        else:             sc["RS vs Nifty"]=0;            fl.append(("bear","Underperforming Nifty — " + str(round(rs,1)) + "%","Stock is behind Nifty over 6 months. If the market dips, this stock will fall even harder. Only trade relative strength leaders."))

    raw = sum(sc.values())
    return sc, fl, raw

# ── TRADE PLAN ────────────────────────────────────────────────────────────────
def trade_plan(setup, sd, raw, capital, risk_pct, regime_pen, spike_pen):
    cfg   = SETUPS.get(setup, SETUPS["NO_SETUP"])
    final = max(0, raw - regime_pen + spike_pen)
    min_s = cfg["min"]
    p     = sd.get("p", 0)

    if setup == "NO_SETUP":
        return {"ok":False,"final":final,"verdict":"NO SETUP","vc":"#484f58","reason":"No tradeable swing pattern detected. " + cfg["trigger"]}

    if final < min_s:
        return {"ok":False,"final":final,"verdict":"SCORE TOO LOW","vc":"#f85149",
                "reason":"Score " + str(final) + " is below the minimum " + str(min_s) + " required for a " + cfg["name"] + " setup. The pattern is detected but quality is insufficient. Wait for the score to improve — usually means waiting for volume to contract further, MACD to recover, or RSI to reach the sweet spot."}

    if final>=90:   verdict,vc = "ELITE SETUP",  "#3fb950"
    elif final>=78: verdict,vc = "STRONG SETUP", "#58a6ff"
    elif final>=65: verdict,vc = "TRADABLE",     "#e3b341"
    else:
        return {"ok":False,"final":final,"verdict":"BELOW MINIMUM","vc":"#f85149",
                "reason":"Score " + str(final) + " below minimum " + str(min_s) + " for this setup. Do not force this trade."}

    e10=sd.get("e10",0); e20=sd.get("e20",0); e50=sd.get("e50",0)
    h52=sd.get("h52",0); fh=sd.get("fh",p); bh=sd.get("bh",p)
    blo=sd.get("blo",p*.95); bl=sd.get("bl",p*.95)
    n20=sd.get("n20",False)

    anchor = cfg["sl"]
    if anchor=="ema10":    sl=e10*.99;   lbl="1% below EMA10"
    elif anchor=="ema20":  sl=e20*.99;   lbl="1% below EMA20"
    elif anchor=="flag_low": sl=blo*.995; lbl="Below flag low"
    elif anchor=="base_low": sl=bl*.99;   lbl="1% below base low"
    else:                  sl=p*.95;     lbl="5% mechanical"

    sl_pct = (p-sl)/p*100 if p>0 else 5
    if sl_pct > 6:
        sl = p*.94; sl_pct = 6.0; lbl = "6% cap (logical SL too wide)"

    rule = cfg["entry"]
    if rule in ("breakout",):
        ea=p; ec=round(h52*1.005,1); er=round(h52*.99,1)
        note = ("Buy the breakout above Rs." + str(round(h52,1)) + ". "
                "Aggressive entry: buy at market now. "
                "Conservative entry: wait for daily close above Rs." + str(round(h52*1.005,1)) + " with 1.5x+ volume. "
                "Retest entry: if price pulls back to Rs." + str(round(er,1)) + " (old resistance becomes support), that is the safest add point.")
    elif rule=="flag_break":
        ea=fh; ec=round(fh*1.01,1); er=round(fh*.995,1)
        note = ("Buy above flag high Rs." + str(round(fh,1)) + " ONLY — do not buy inside the flag. "
                "Aggressive: buy as price breaks above Rs." + str(round(fh,1)) + ". "
                "Conservative: buy next candle after a breakout close. "
                "Retest: flag high becomes support at Rs." + str(round(er,1)) + " — any dip back to this level is a second entry.")
    elif rule=="ema_reclaim":
        te=e20 if n20 else e50; en="EMA20" if n20 else "EMA50"
        ea=round(te*1.002,1); ec=round(te*1.01,1); er=round(te*.998,1)
        note = (en + " pullback entry. "
                "Aggressive: buy as price reclaims " + en + " at Rs." + str(round(ea,1)) + ". "
                "Conservative: wait for first green daily candle closing above " + en + ". "
                "Retest: if " + en + " is touched again at Rs." + str(round(er,1)) + " without breaking down = second add point.")
    else:
        ea=bh; ec=round(bh*1.01,1); er=round(bh*.995,1)
        note = ("Enter on break above base high Rs." + str(round(bh,1)) + " on volume. "
                "Aggressive: buy as price clears Rs." + str(round(bh,1)) + ". "
                "Conservative: wait for 1.5x+ volume on the breakout candle. "
                "Retest: base high becomes support at Rs." + str(round(er,1)) + " if retested.")

    r = p - sl
    t1 = round(p + 1.5*r, 1); t2 = round(p + 3.0*r, 1); t3 = round(p + 5.0*r, 1)
    ra = capital * risk_pct / 100
    qty = int(ra / (p * sl_pct/100)) if p*sl_pct > 0 else 0

    return {
        "ok":True,"final":final,"verdict":verdict,"vc":vc,
        "ea":ea,"ec":ec,"er":er,"note":note,
        "sl":sl,"sl_pct":round(sl_pct,1),"sl_lbl":lbl,
        "t1":t1,"t2":t2,"t3":t3,"rr":3.0,
        "qty":qty,"pos_val":round(qty*p),"ra":round(ra),"e10":e10,
    }

def get_returns(df, ndf):
    p=sf(df["Close"].iloc[-1]); r6=r12=rs=None
    if len(df)>=126:
        p6=sf(df["Close"].iloc[-126])
        if p6>0: r6=(p-p6)/p6*100
    if len(df)>=252:
        p12=sf(df["Close"].iloc[-252])
        if p12>0: r12=(p-p12)/p12*100
    if ndf is not None and len(ndf)>=126 and r6 is not None:
        np_=sf(ndf["Close"].iloc[-1]); np6=sf(ndf["Close"].iloc[-126])
        if np6>0: rs=r6-(np_-np6)/np6*100
    return r6,r12,rs

def liq(df):
    p=sf(df["Close"].iloc[-1]); av=df["Volume"].tail(50).mean()
    to=av*p; return to, to>=25_00_00_000

def pct_str(v):
    if v is None: return "—"
    return ("+" if v>=0 else "") + str(round(v,1)) + "%"

def Rs(v): return "Rs." + "{:,.1f}".format(v)

# ── HTML HELPERS — 3 only, all plain string inputs ────────────────────────────
def metric_card(label, value, color, sub, desc):
    return (
        "<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 12px;height:100%;'>"
        "<div style='color:#8b949e;font-size:9px;font-weight:700;letter-spacing:.5px;margin-bottom:4px;'>" + label + "</div>"
        "<div style='color:" + color + ";font-size:15px;font-weight:800;font-family:monospace;'>" + value + "</div>"
        "<div style='color:#8b949e;font-size:10px;margin-top:2px;'>" + sub + "</div>"
        "<div style='color:#6e7681;font-size:9px;margin-top:4px;line-height:1.4;'>" + desc + "</div>"
        "</div>"
    )

def flag_card(ftype, title, message):
    c = {"bull":"#3fb950","warn":"#e3b341","bear":"#f85149","info":"#58a6ff"}.get(ftype,"#8b949e")
    i = {"bull":"▲","warn":"◆","bear":"▼","info":"●"}.get(ftype,"•")
    return (
        "<div style='background:#0d1117;border-left:3px solid " + c + ";border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;'>"
        "<div style='color:" + c + ";font-size:11px;font-weight:700;margin-bottom:3px;'>" + i + "  " + title + "</div>"
        "<div style='color:#8b949e;font-size:11px;line-height:1.6;'>" + message + "</div>"
        "</div>"
    )

def level_card(label, value, color, sub):
    return (
        "<div style='background:#0d1117;border:1px solid " + color + "30;border-radius:6px;padding:10px;'>"
        "<div style='color:#8b949e;font-size:9px;font-weight:700;margin-bottom:4px;'>" + label + "</div>"
        "<div style='color:" + color + ";font-size:13px;font-weight:800;font-family:monospace;'>" + value + "</div>"
        "<div style='color:#8b949e;font-size:9px;margin-top:3px;'>" + sub + "</div>"
        "</div>"
    )

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown(
        "<div style='background:#0d1117;border-bottom:1px solid #21262d;padding:10px 0 10px 4px;margin-bottom:14px;'>"
        "<span style='color:#58a6ff;font-size:16px;font-weight:800;font-family:monospace;'>📈 NSE ELITE SWING TERMINAL</span>"
        "<span style='color:#484f58;font-size:12px;'> · v8 · " + datetime.now().strftime("%a %d %b %Y") + "</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # Fetch indices
    with st.spinner("Fetching market data..."):
        nifty_df  = fetch_idx("^NSEI")
        bnifty_df = fetch_idx("^NSEBANK")
        vix_df    = fetch_idx("^INDIAVIX")

    regime_rows, regime_pen = regime(nifty_df, bnifty_df)
    vix_val = sf(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df) > 0 else None

    # Regime bar — native columns
    r1, r2, r3, r4 = st.columns(4)
    regime_col_map = {"normal":"#3fb950","off":"#e3b341","inverse":"#f85149"}
    for col_widget, (name, status, col_key, pen) in zip([r1,r2], regime_rows):
        col_hex = regime_col_map.get(col_key, "#8b949e")
        dot = "🟢" if col_key=="normal" else "🟠" if col_key=="off" else "🔴" if col_key=="inverse" else "⚪"
        pen_txt = " (penalty -" + str(pen) + " pts)" if pen>0 else ""
        with col_widget:
            st.markdown(
                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;'>"
                "<div style='color:#8b949e;font-size:9px;font-weight:700;'>" + name + "</div>"
                "<div style='color:" + col_hex + ";font-size:13px;font-weight:700;'>" + dot + " " + status + "</div>"
                "<div style='color:#484f58;font-size:10px;'>" + pen_txt + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
    if vix_val:
        vc2 = "#3fb950" if vix_val<15 else "#e3b341" if vix_val<20 else "#f85149"
        vl  = "LOW — Full sizing ok" if vix_val<15 else "ELEVATED — Reduce size 25%" if vix_val<20 else "HIGH — No breakout entries!"
        with r3:
            st.markdown(
                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;'>"
                "<div style='color:#8b949e;font-size:9px;font-weight:700;'>INDIA VIX</div>"
                "<div style='color:" + vc2 + ";font-size:13px;font-weight:700;'>" + str(round(vix_val,1)) + "</div>"
                "<div style='color:#484f58;font-size:10px;'>" + vl + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
    with r4:
        regime_status = "BEARISH — Capital Preservation" if regime_pen>=20 else "CAUTION — Half Size" if regime_pen>=10 else "HEALTHY — Trade Normally"
        regime_hex    = "#f85149" if regime_pen>=20 else "#e3b341" if regime_pen>=10 else "#3fb950"
        st.markdown(
            "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;'>"
            "<div style='color:#8b949e;font-size:9px;font-weight:700;'>OVERALL REGIME</div>"
            "<div style='color:" + regime_hex + ";font-size:11px;font-weight:700;'>" + regime_status + "</div>"
            "<div style='color:#484f58;font-size:10px;'>Regime penalty: -" + str(regime_pen) + " pts</div>"
            "</div>",
            unsafe_allow_html=True
        )

    if regime_pen >= 20:
        st.error("🚫 CAPITAL PRESERVATION MODE — Market is in bearish phase. Only setups scoring 85+ qualify. Cut all position sizes by 50%. Prioritize protecting capital.")
    elif regime_pen >= 10:
        st.warning("⚠️ CAUTION MODE — Market below 50 EMA. Half position sizes on all new trades. No breakout entries on red market days.")
    if vix_val and vix_val > 20:
        st.error("⚠️ HIGH VIX (" + str(round(vix_val,1)) + ") — No new breakout entries. Use 0.5% risk only. Widen mental stops by 1 ATR.")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚡  Stock Analyzer",
        "📚  Setup School",
        "📡  Chartink Scanners",
        "📋  System Rules",
        "🏭  Sector Watch",
    ])

    # ════════════════════════════════════════
    # TAB 1 — STOCK ANALYZER
    # ════════════════════════════════════════
    with tab1:
        left, right = st.columns([1, 2], gap="large")

        with left:
            st.markdown("#### Stock Lookup")
            sym_input = st.text_input("NSE Symbol", placeholder="e.g. DATAPATTNS, BEL, AKUMS").upper().strip()
            pick      = st.selectbox("Or pick from list", [""] + POPULAR)
            if pick: sym_input = pick
            capital   = st.number_input("Trading Capital (Rs.)", 100000, 10000000, 300000, 50000, format="%d")
            risk_pct  = st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25, help="1% standard. 0.5% on uncertain days.")
            go        = st.button("⚡ Detect Setup & Score", use_container_width=True)
            st.info("The app detects which swing setup the stock is in, then scores it with weights specific to that setup type. Each setup has its own entry rules, SL anchor, and minimum score.")

        with right:
            if not go:
                st.markdown("#### Available Setup Types")
                for k, v in SETUPS.items():
                    if k == "NO_SETUP": continue
                    st.markdown(v["icon"] + " **" + v["name"] + "** — " + v["what"])
                st.markdown("Enter a symbol on the left and click **Detect Setup & Score** to analyze.")

            elif sym_input:
                with st.spinner("Fetching " + sym_input + " from Yahoo Finance..."):
                    df, ticker = fetch(sym_input)

                if df is None:
                    st.error("Could not fetch '" + sym_input + "'. Try: RELIANCE, TCS, HDFCBANK, DATAPATTNS, BEL, HAL")
                else:
                    df = enrich(df)
                    to, liq_ok = liq(df)
                    if not liq_ok:
                        st.error("LIQUIDITY FAIL — Avg daily turnover Rs." + str(round(to/1e7,1)) + " Cr is below Rs.25 Cr minimum. Execution risk too high. Find a more liquid stock.")
                    else:
                        r6, r12, rs_nifty = get_returns(df, nifty_df)
                        setup, sd         = detect(df)
                        sc, fl, raw       = score(setup, sd, r6, r12, rs_nifty)

                        l     = df.iloc[-1]
                        p     = sf(l["Close"]); prev = sf(df["Close"].iloc[-2])
                        dchg  = (p-prev)/prev*100 if prev>0 else 0
                        h52   = sf(l["H52"],p); e10=sf(l["E10"]); e20=sf(l["E20"]); e50=sf(l["E50"]); e200=sf(l["E200"])
                        vr_   = sf(l["VR"],1.0); rsi_=sf(l["RSI"],50); mac_=sf(l["MACD"]); hist_=sf(l["HIST"])
                        pch   = (h52-p)/h52*100 if h52>0 else 0

                        # Spike
                        if abs(dchg)>=10:  spike_pen=-20; spike_msg="SPIKE: +" + str(round(abs(dchg),1)) + "% today (-20 pts). Do not chase. Wait 2–3 sessions."
                        elif abs(dchg)>=8: spike_pen=-10; spike_msg="BIG MOVE: +" + str(round(abs(dchg),1)) + "% today (-10 pts). Prefer next session entry."
                        elif abs(dchg)>=5: spike_pen=-5;  spike_msg="MOVE: +" + str(round(abs(dchg),1)) + "% today (-5 pts). Slightly extended."
                        else:               spike_pen=0;   spike_msg=""

                        trade = trade_plan(setup, sd, raw, capital, risk_pct, regime_pen, spike_pen)
                        final = trade["final"]
                        cfg   = SETUPS[setup]
                        color = cfg["color"]

                        # ── STOCK HEADER ──────────────────────────────────────
                        d_col = "#3fb950" if dchg>=0 else "#f85149"
                        d_arr = "▲" if dchg>=0 else "▼"
                        st.markdown(
                            "<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;margin-bottom:12px;'>"
                            "<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                            "<div>"
                            "<div style='color:#58a6ff;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:3px;'>" + ticker + " · " + df.index[-1].strftime("%d %b %Y") + " · Turnover Rs." + str(round(to/1e7,1)) + "Cr ✓</div>"
                            "<div style='color:#c9d1d9;font-size:28px;font-weight:800;font-family:monospace;'>Rs." + "{:,.2f}".format(p) + "</div>"
                            "</div>"
                            "<div style='text-align:right;'>"
                            "<div style='color:" + d_col + ";font-size:18px;font-weight:700;font-family:monospace;'>" + d_arr + " " + str(round(abs(dchg),2)) + "%</div>"
                            "<div style='color:#484f58;font-size:10px;'>Day Change</div>"
                            "</div>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        if spike_msg: st.warning(spike_msg)

                        # ── SETUP DETECTION RESULT (BIG & CLEAR) ─────────────
                        st.markdown(
                            "<div style='background:#0d1117;border:2px solid " + color + ";border-radius:10px;padding:16px;margin-bottom:14px;'>"
                            "<div style='color:" + color + ";font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:6px;'>SETUP DETECTED</div>"
                            "<div style='font-size:24px;font-weight:900;color:" + color + ";margin-bottom:4px;'>" + cfg["icon"] + "  " + cfg["name"] + "</div>"
                            "<div style='color:#c9d1d9;font-size:13px;line-height:1.6;margin-bottom:10px;'>" + cfg["what"] + "</div>"
                            "<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
                            "<span style='color:#8b949e;font-size:11px;'>Risk: <strong style='color:" + color + ";'>" + cfg["risk"] + "</strong></span>"
                            "<span style='color:#8b949e;font-size:11px;'>Hold: <strong style='color:#c9d1d9;'>" + cfg["hold"] + "</strong></span>"
                            "<span style='color:#8b949e;font-size:11px;'>Min Score: <strong style='color:#c9d1d9;'>" + str(cfg["min"]) + "/100</strong></span>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ── SCORE — BIG AND PROMINENT ─────────────────────────
                        vc  = trade["vc"]; verdict = trade["verdict"]
                        raw_s = str(raw)
                        rp_s  = " − Regime: -" + str(regime_pen) if regime_pen>0 else ""
                        sp_s  = " − Spike: " + str(spike_pen) if spike_pen<0 else ""
                        score_detail = "Raw: " + raw_s + rp_s + sp_s + " = Final: " + str(final)

                        verdict_explain = {
                            "ELITE SETUP":  "All criteria met at highest level. Rare setup. Full position size appropriate.",
                            "STRONG SETUP": "Strong setup with good scores across key criteria. Full 1% risk appropriate.",
                            "TRADABLE":     "Setup valid but some criteria marginal. Use 0.5% risk. Tight monitoring required.",
                            "NO SETUP":     "No tradeable swing pattern. Wait.",
                            "SCORE TOO LOW":"Pattern detected but quality insufficient. Wait for score to improve.",
                            "BELOW MINIMUM":"Score below minimum for this setup type. Do not force this trade.",
                        }.get(verdict, "")

                        st.markdown(
                            "<div style='background:#0d1117;border:2px solid " + vc + ";border-radius:10px;padding:20px;margin-bottom:14px;'>"
                            "<div style='display:flex;align-items:center;gap:20px;'>"
                            "<div style='text-align:center;padding-right:20px;border-right:1px solid #21262d;min-width:110px;'>"
                            "<div style='font-size:72px;font-weight:900;color:" + vc + ";line-height:1;font-family:monospace;'>" + str(final) + "</div>"
                            "<div style='color:#484f58;font-size:12px;font-weight:600;'>out of 100</div>"
                            "</div>"
                            "<div>"
                            "<div style='color:" + vc + ";font-size:22px;font-weight:800;letter-spacing:.5px;margin-bottom:6px;'>" + verdict + "</div>"
                            "<div style='color:#484f58;font-size:10px;font-family:monospace;margin-bottom:8px;'>" + score_detail + "</div>"
                            "<div style='color:#8b949e;font-size:12px;line-height:1.5;'>" + verdict_explain + "</div>"
                            "</div>"
                            "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ── DATA TILES ────────────────────────────────────────
                        h52c="#3fb950" if pch<=3 else "#e3b341" if pch<=10 else "#f85149"
                        vrc ="#3fb950" if vr_>=1.5 else "#e3b341" if vr_>=1 else "#f85149"
                        rc  ="#3fb950" if 50<=rsi_<=65 else "#e3b341" if rsi_<80 else "#f85149"
                        mc  ="#3fb950" if mac_>0 and hist_>0 else "#e3b341" if mac_>0 else "#f85149"
                        e20c="#3fb950" if p>e20 else "#f85149"
                        e50c="#3fb950" if e20>e50 else "#f85149"
                        e200c="#3fb950" if e50>e200 else "#f85149"
                        r6c ="#3fb950" if r6 and r6>=20 else "#e3b341" if r6 and r6>=0 else "#f85149"
                        h52s="ABOVE HIGH" if pch<=0 else str(round(pch,1))+"% below"

                        c1,c2,c3,c4 = st.columns(4)
                        with c1: st.markdown(metric_card("52W HIGH","Rs."+"{:,.1f}".format(h52),h52c,h52s,"Near high = momentum. Far below = catching falling knife."),unsafe_allow_html=True)
                        with c2: st.markdown(metric_card("VOLUME",str(round(vr_,1))+"x avg",vrc,"vs 50-day average","Above 1.5x = institutions active. Below 0.8x on dip = healthy pullback."),unsafe_allow_html=True)
                        with c3: st.markdown(metric_card("RSI (14)",str(round(rsi_)),rc,"14-period","Sweet spot: 50–65. Above 75 = overbought. Below 45 = weakening."),unsafe_allow_html=True)
                        with c4: st.markdown(metric_card("MACD",("UP " if mac_>0 else "DN ")+str(round(abs(mac_),2)),mc,"hist: "+str(round(hist_,2)),"Positive+expanding = best entry. Negative = avoid."),unsafe_allow_html=True)

                        c5,c6,c7,c8 = st.columns(4)
                        with c5: st.markdown(metric_card("EMA 20","Rs."+"{:,.1f}".format(e20),e20c,"above" if p>e20 else "BELOW","Price must be above EMA20 for swing longs."),unsafe_allow_html=True)
                        with c6: st.markdown(metric_card("EMA 50","Rs."+"{:,.1f}".format(e50),e50c,"20>50" if e20>e50 else "20<50","EMA20 > EMA50 = intermediate uptrend."),unsafe_allow_html=True)
                        with c7: st.markdown(metric_card("EMA 200","Rs."+"{:,.1f}".format(e200),e200c,"50>200" if e50>e200 else "50<200","Long-term Stage 2 line."),unsafe_allow_html=True)
                        with c8: st.markdown(metric_card("6M RETURN",pct_str(r6),r6c,"12M: "+pct_str(r12),"Leaders return 20%+ when Nifty returns 5–10%."),unsafe_allow_html=True)

                        st.markdown("---")

                        # ── SCORE BREAKDOWN ───────────────────────────────────
                        st.markdown("#### Score Breakdown — " + cfg["name"] + " Weights")
                        st.caption("Each setup type uses different scoring weights. A VCP is scored differently from a Breakout — the factors that matter most differ.")

                        for key, max_pts in cfg["weights"].items():
                            sc_val = sc.get(key, 0)
                            pct_s  = min(int(sc_val/max_pts*100),100) if max_pts>0 else 0
                            col_s  = "#3fb950" if pct_s>=75 else "#e3b341" if pct_s>=50 else "#f85149"
                            sym_s  = "✓" if pct_s>=75 else "~" if pct_s>=50 else "✗"
                            st.markdown(
                                "<div style='margin-bottom:8px;'>"
                                "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;'>"
                                "<span style='color:#c9d1d9;font-size:12px;'>" + key + "</span>"
                                "<span style='color:" + col_s + ";font-size:12px;font-weight:700;'>" + sym_s + "  " + str(sc_val) + " / " + str(max_pts) + " pts</span>"
                                "</div>"
                                "<div style='height:5px;background:#21262d;border-radius:3px;overflow:hidden;'>"
                                "<div style='height:100%;width:" + str(pct_s) + "%;background:" + col_s + ";border-radius:3px;'></div>"
                                "</div>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                        st.markdown("---")

                        # ── SIGNAL FLAGS ──────────────────────────────────────
                        st.markdown("#### Signal Analysis — Why This Score")
                        st.caption("Every metric explained in plain English. Green = bullish, Orange = caution, Red = avoid signal.")
                        for ft, title, msg in fl:
                            st.markdown(flag_card(ft, title, msg), unsafe_allow_html=True)

                        st.markdown("---")

                        # ── TRADE PLAN ────────────────────────────────────────
                        if trade["ok"]:
                            st.markdown("#### Entry Checklist — " + cfg["name"])
                            for item in cfg["checks"]:
                                st.markdown("☐ " + item)
                            st.success("**Entry trigger:** " + cfg["trigger"])

                            st.markdown("#### Entry Plan")
                            st.info(trade["note"])

                            st.markdown("#### Trade Levels")
                            ea_s = Rs(trade["ea"]) if trade.get("ea",0)>0 else "See plan above"
                            ec_s = Rs(trade["ec"]) if trade.get("ec",0)>0 else "See plan above"
                            er_s = Rs(trade["er"]) if trade.get("er",0)>0 else "See plan above"
                            t1g  = pct_str((trade["t1"]-p)/p*100) + " · 1.5R · Book 30%"
                            t2g  = pct_str((trade["t2"]-p)/p*100) + " · 3R  · Book 30%"
                            t3g  = pct_str((trade["t3"]-p)/p*100) + " · 5R  · Trail 40%"

                            la,lb,lc,ld = st.columns(4)
                            with la: st.markdown(level_card("AGGRESSIVE ENTRY", ea_s, "#58a6ff", "Buy now / at open"), unsafe_allow_html=True)
                            with lb: st.markdown(level_card("CONSERVATIVE", ec_s, "#79c0ff", "Wait for confirmation"), unsafe_allow_html=True)
                            with lc: st.markdown(level_card("STOP LOSS "+str(trade["sl_pct"])+"%", Rs(trade["sl"]), "#f85149", trade["sl_lbl"]), unsafe_allow_html=True)
                            with ld: st.markdown(level_card("RETEST ENTRY", er_s, "#484f58", "If price pulls back"), unsafe_allow_html=True)

                            ta,tb,tc = st.columns(3)
                            with ta: st.markdown(level_card("TARGET 1", Rs(trade["t1"]), "#e3b341", t1g), unsafe_allow_html=True)
                            with tb: st.markdown(level_card("TARGET 2", Rs(trade["t2"]), "#3fb950", t2g), unsafe_allow_html=True)
                            with tc: st.markdown(level_card("TARGET 3", Rs(trade["t3"]), "#56d364", t3g), unsafe_allow_html=True)

                            rr_c = "#3fb950" if trade["rr"]>=3 else "#f85149"
                            st.markdown(
                                "<div style='background:#0d1117;border:1px solid " + rr_c + "30;border-radius:6px;padding:12px;text-align:center;margin:8px 0;'>"
                                "<span style='color:#8b949e;font-size:13px;'>Risk : Reward = </span>"
                                "<span style='color:" + rr_c + ";font-size:18px;font-weight:800;font-family:monospace;'>1 : " + str(trade["rr"]) + "</span>"
                                "<span style='color:" + rr_c + ";font-size:12px;'> · minimum 3:1 " + ("✓ met" if trade["rr"]>=3 else "✗ NOT MET — SKIP") + "</span>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            qty_s = str(trade["qty"]) + " shares · Rs." + "{:,.0f}".format(trade["pos_val"])
                            st.markdown(
                                "<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:12px;margin-bottom:14px;'>"
                                "<div style='color:#8b949e;font-size:10px;font-weight:700;margin-bottom:4px;'>POSITION SIZE — " + str(risk_pct) + "% risk on Rs." + "{:,}".format(int(capital)) + "</div>"
                                "<div style='color:#58a6ff;font-size:15px;font-weight:700;font-family:monospace;'>" + qty_s + "</div>"
                                "<div style='color:#6e7681;font-size:11px;margin-top:3px;'>Max risk = Rs." + "{:,.0f}".format(trade["ra"]) + " · Stop at " + Rs(trade["sl"]) + " (" + str(trade["sl_pct"]) + "% below entry)</div>"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            st.markdown("#### Exit Plan")
                            e10_s = Rs(trade.get("e10",0))
                            for ft, ttl, msg in [
                                ("info","1. Immediate — Place GTT Stop","After your order fills, place GTT stop at " + Rs(trade["sl"]) + " immediately. Do not wait. A trade without a stop is gambling."),
                                ("info","2. At Target 1 (" + Rs(trade["t1"]) + ")","Book 30% of your position. Move stop up to your exact entry price. The trade is now risk-free — you cannot lose money."),
                                ("info","3. At Target 2 (" + Rs(trade["t2"]) + ")","Book another 30%. Move stop to T1 level. The remaining 40% continues running."),
                                ("info","4. Trail Final 40%","Trail stop using daily close below EMA10 (" + e10_s + "). As EMA10 rises, raise your stop. Never lower it."),
                                ("bear","Hard Stop — No Debate","If price closes below " + Rs(trade["sl"]) + ", exit the entire position at next day's open. No hoping, no averaging, no exceptions."),
                                ("warn","Time Stop","No meaningful progress in 15 trading days? Exit and redeploy capital elsewhere."),
                                ("warn","Pre-Event Exit","Exit 1 day before: quarterly results, RBI policy, Budget. Holding through events on a swing trade is speculation, not trading."),
                            ]:
                                st.markdown(flag_card(ft, ttl, msg), unsafe_allow_html=True)

                        else:
                            st.error("NO TRADE — " + trade.get("reason","Score below minimum for this setup."))

    # ════════════════════════════════════════
    # TAB 2 — SETUP SCHOOL
    # ════════════════════════════════════════
    with tab2:
        st.markdown("## 📚 Setup School")
        st.markdown("A complete guide to every setup the analyzer detects. Understanding the *why* behind each pattern makes you a better trader — you will stop chasing bad setups and recognize good ones instantly.")

        for key, cfg in SETUPS.items():
            if key == "NO_SETUP": continue
            with st.expander(cfg["icon"] + "  " + cfg["name"]):
                st.markdown("**What is a " + cfg["name"] + "?**")
                st.markdown(cfg["what"])
                st.markdown("**What to look for:**")
                for item in cfg["checks"]:
                    st.markdown("- " + item)
                st.success("**Entry trigger:** " + cfg["trigger"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Risk Profile", cfg["risk"])
                c2.metric("Ideal Hold", cfg["hold"])
                c3.metric("Min Score Needed", str(cfg["min"]) + "/100")
                st.markdown("**Why this setup scores what it scores — weight breakdown:**")
                for k, v in cfg["weights"].items():
                    st.markdown("- **" + k + "**: " + str(v) + " points")

    # ════════════════════════════════════════
    # TAB 3 — CHARTINK SCANNERS
    # ════════════════════════════════════════
    with tab3:
        st.markdown("## 📡 Chartink Scanners")
        st.markdown("Ready-to-use scanner codes with full explanations. **Go to chartink.com → Screens → Create New Screen → paste code → Generate.** Run after 4 PM IST.")

        for sc_item in CHARTINK_SCANS:
            with st.expander(sc_item["name"] + " — " + sc_item["when"]):
                st.markdown("**What it finds:** " + sc_item["what"])
                st.markdown("**Why it works:** " + sc_item["why"])
                st.success("**Action on results:** " + sc_item["action"])
                st.markdown("**Each condition explained:**")
                for cond, expl in sc_item["conds"]:
                    st.markdown(flag_card("info", cond, expl), unsafe_allow_html=True)
                st.markdown("**Chartink Code — copy and paste this exactly:**")
                st.code(sc_item["code"], language="text")

    # ════════════════════════════════════════
    # TAB 4 — SYSTEM RULES
    # ════════════════════════════════════════
    with tab4:
        st.markdown("## 📋 Elite Swing Trading Rules")
        st.markdown("Every rule here exists because professional traders discovered it the hard way — through losses. Each rule has a specific reason.")

        for section_title, rules in RULES:
            with st.expander(section_title):
                for rule_title, rule_desc in rules:
                    st.markdown("**" + rule_title + "**")
                    st.markdown(rule_desc)
                    st.divider()

    # ════════════════════════════════════════
    # TAB 5 — SECTOR WATCH
    # ════════════════════════════════════════
    with tab5:
        st.markdown("## 🏭 Sector Watch")
        st.markdown("Scan an entire sector at once. Results ranked by final score. Use this to find the strongest stock in the strongest sector.")

        sector_choice = st.selectbox("Select Sector", list(SECTORS.keys()))
        scan_sector   = st.button("📡 Scan " + sector_choice)

        if scan_sector:
            stocks  = SECTORS[sector_choice]
            results = []
            prog    = st.progress(0)
            status  = st.empty()

            for i, sym in enumerate(stocks):
                status.text("Scanning " + sym + " (" + str(i+1) + "/" + str(len(stocks)) + ")...")
                try:
                    df_s, tkr_s = fetch(sym)
                    if df_s is None:
                        results.append({"sym":sym,"setup":"NO DATA","score":0,"color":"#484f58","price":"—","verdict":"SKIP","r6":"—","r12":"—"})
                    else:
                        df_s = enrich(df_s)
                        to_s, lq_s = liq(df_s)
                        if not lq_s:
                            results.append({"sym":sym,"setup":"LIQ FAIL","score":0,"color":"#484f58","price":Rs(sf(df_s["Close"].iloc[-1])),"verdict":"SKIP","r6":"—","r12":"—"})
                        else:
                            r6_s, r12_s, rs_s = get_returns(df_s, nifty_df)
                            setup_s, sd_s     = detect(df_s)
                            sc_s, fl_s, raw_s = score(setup_s, sd_s, r6_s, r12_s, rs_s)
                            tr_s              = trade_plan(setup_s, sd_s, raw_s, 100000, 1.0, regime_pen, 0)
                            cfg_s             = SETUPS[setup_s]
                            results.append({
                                "sym":sym, "setup":cfg_s["icon"]+" "+setup_s.replace("_"," "),
                                "score":tr_s["final"], "color":cfg_s["color"],
                                "price":Rs(sf(df_s["Close"].iloc[-1])),
                                "verdict":tr_s["verdict"],
                                "r6":pct_str(r6_s), "r12":pct_str(r12_s),
                            })
                except Exception as e:
                    results.append({"sym":sym,"setup":"ERROR","score":0,"color":"#484f58","price":"—","verdict":"ERROR","r6":"—","r12":"—"})
                prog.progress((i+1)/len(stocks))

            status.empty(); prog.empty()
            results.sort(key=lambda x: x["score"], reverse=True)

            # Results table
            st.markdown("### Results — " + sector_choice + " (" + str(len(results)) + " stocks scanned)")
            hdr = st.columns([1.2, 2, 0.8, 0.9, 0.9, 1.5])
            for col, label in zip(hdr, ["SYMBOL","SETUP","SCORE","6M","12M","VERDICT"]):
                col.markdown("**" + label + "**")
            st.divider()

            for r in results:
                sc_c = "#3fb950" if r["score"]>=80 else "#e3b341" if r["score"]>=65 else "#f85149" if r["score"]>0 else "#484f58"
                row  = st.columns([1.2, 2, 0.8, 0.9, 0.9, 1.5])
                row[0].markdown("**" + r["sym"] + "**")
                row[1].markdown("<span style='color:" + r["color"] + ";font-weight:600;'>" + r["setup"] + "</span>", unsafe_allow_html=True)
                row[2].markdown("<span style='color:" + sc_c + ";font-size:16px;font-weight:800;font-family:monospace;'>" + str(r["score"]) + "</span>", unsafe_allow_html=True)
                row[3].markdown(r["r6"])
                row[4].markdown(r["r12"])
                row[5].markdown("<span style='color:" + sc_c + ";font-weight:600;'>" + r["verdict"] + "</span>", unsafe_allow_html=True)

    st.divider()
    st.caption("Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance (end-of-day). Always verify on NSE before trading. Past performance does not guarantee future returns.")

if __name__ == "__main__":
    main()
