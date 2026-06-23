import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Elite Swing Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #060e1c; color: #e0e8ff; }
    .main .block-container { padding-top: 1.2rem; max-width: 1200px; }
    h1,h2,h3,h4 { color: #e0e8ff !important; }
    .stButton button {
        background: linear-gradient(135deg,#1565c0,#0d47a1) !important;
        color: white !important; font-weight: 700 !important;
        border: none !important; border-radius: 8px !important;
    }
    .stTabs [data-baseweb="tab"] { color: #7b8fba !important; font-size:13px !important; }
    .stTabs [aria-selected="true"] { color: #e0e8ff !important; border-bottom-color: #2979ff !important; }
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stSlider label { color: #7b8fba !important; }
    .stExpander { background: #0d1b2e !important; border: 1px solid #1a2744 !important; border-radius: 8px !important; }
    div[data-testid="stMetricValue"] { color: #e0e8ff !important; }
</style>
""", unsafe_allow_html=True)

# ─── POPULAR NSE STOCKS ───────────────────────────────────────────────────────
POPULAR = sorted([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "TITAN","WIPRO","ULTRACEMCO","NESTLEIND","SUNPHARMA","HCLTECH","TECHM",
    "POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP","BAJAJFINSV",
    "EICHERMOT","HEROMOTOCO","M&M","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL",
    "DATAPATTNS","LALPATHLAB","METROPOLIS","AKUMS","MARKSANS","SURYODAY",
    "INDSWFTLAB","THYROCARE","KAYNES","DIXON","AMBER","ZEEL","COALINDIA",
    "GRASIM","SHREECEM","DMART","NAUKRI","ZOMATO","PAYTM","IRCTC","IRFC",
    "COCHINSHIP","MAZAGON","GRSE","BHEL","RAILTEL","RVNL","IRCON",
])

# ─── DATA FUNCTIONS ───────────────────────────────────────────────────────────
def fetch(symbol, period="2y"):
    for sfx in [".NS", ".BO"]:
        try:
            df = yf.Ticker(symbol + sfx).history(period=period, interval="1d", auto_adjust=True)
            if df is not None and len(df) > 60:
                return df.dropna(subset=["Close"]), symbol + sfx
        except: continue
    return None, None

def fetch_index(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        if df is not None and len(df) > 50:
            return df.dropna(subset=["Close"])
    except: pass
    return None

# ─── INDICATORS ──────────────────────────────────────────────────────────────
def ema(s, p): return s.ewm(span=p, adjust=False).mean()
def sma(s, p): return s.rolling(p).mean()

def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def macd(s):
    m = s.ewm(span=12,adjust=False).mean() - s.ewm(span=26,adjust=False).mean()
    sig = m.ewm(span=9,adjust=False).mean()
    return m, sig, m - sig

def enrich(df):
    df = df.copy()
    df["E10"]  = ema(df["Close"],10)
    df["E20"]  = ema(df["Close"],20)
    df["E50"]  = ema(df["Close"],50)
    df["E200"] = ema(df["Close"],200)
    df["V50"]  = sma(df["Volume"],50)
    df["V10"]  = sma(df["Volume"],10)
    df["VR"]   = df["Volume"] / df["V50"]
    df["H52"]  = df["High"].rolling(252, min_periods=100).max()
    df["RSI"]  = rsi(df["Close"])
    df["ATR"]  = (df["High"]-df["Low"]).rolling(14).mean()
    m,sig,hist = macd(df["Close"])
    df["MACD"] = m; df["SIG"] = sig; df["HIST"] = hist
    # Pullback depth from recent swing high (last 20 days)
    df["SwingH"] = df["High"].rolling(20).max()
    df["PullPct"] = (df["SwingH"] - df["Close"]) / df["SwingH"] * 100
    return df

def returns(df, nifty=None):
    p = df["Close"].iloc[-1]
    r6 = r12 = rs = None
    if len(df)>=126: r6  = (p - df["Close"].iloc[-126]) / df["Close"].iloc[-126] * 100
    if len(df)>=252: r12 = (p - df["Close"].iloc[-252]) / df["Close"].iloc[-252] * 100
    if nifty is not None and len(nifty)>=126:
        np_ = nifty["Close"].iloc[-1]
        n6  = (np_ - nifty["Close"].iloc[-126]) / nifty["Close"].iloc[-126] * 100
        rs  = (r6 - n6) if r6 else None
    return r6, r12, rs

# ─── MARKET REGIME ────────────────────────────────────────────────────────────
def market_regime(nifty_df, banknifty_df):
    results = {}
    penalty = 0
    for name, df in [("Nifty 50", nifty_df), ("Bank Nifty", banknifty_df)]:
        if df is None or len(df) < 50:
            results[name] = ("UNKNOWN", "#7b8fba", 0)
            continue
        d  = enrich(df)
        p  = float(d["Close"].iloc[-1])
        e50  = float(d["E50"].iloc[-1])
        e200 = float(d["E200"].iloc[-1])
        if p < e200:
            results[name] = ("BEARISH — below 200 EMA", "#f44336", 20)
            penalty = max(penalty, 20)
        elif p < e50:
            results[name] = ("CAUTION — below 50 EMA", "#ff9100", 10)
            penalty = max(penalty, 10)
        else:
            results[name] = ("HEALTHY — above all EMAs", "#00c853", 0)
    return results, penalty

# ─── PATTERN DETECTION ───────────────────────────────────────────────────────
def detect_pattern(df):
    """
    Detects:
    - VCP (Volatility Contraction Pattern)
    - Bull Flag
    - Flat Base
    - Cup Handle (simplified)
    - Breakout
    - Ascending Triangle
    Returns pattern name + confidence + explanation
    """
    if len(df) < 30:
        return "INSUFFICIENT DATA", 0, ""

    l  = df.iloc[-1]
    p  = float(l["Close"])
    h52 = float(l["H52"]) if not np.isnan(l["H52"]) else p
    e20  = float(l["E20"])
    e50  = float(l["E50"])
    e200 = float(l["E200"])
    vr   = float(l["VR"]) if not np.isnan(l["VR"]) else 1
    v10  = float(l["V10"]) if not np.isnan(l["V10"]) else 1
    v50  = float(l["V50"]) if not np.isnan(l["V50"]) else 1
    atr  = float(l["ATR"]) if not np.isnan(l["ATR"]) else p*0.02
    pct_from_h52 = (h52 - p) / h52 * 100 if h52 > 0 else 100

    last5  = df["Close"].tail(5)
    last20 = df["Close"].tail(20)
    last10_vol = df["Volume"].tail(10).mean()
    last50_vol = df["Volume"].tail(50).mean()

    price_range_20 = (last20.max() - last20.min()) / last20.mean() * 100
    vol_contraction = last10_vol / last50_vol if last50_vol > 0 else 1

    # ── VCP ──────────────────────────────────────────────────────────────────
    # Criteria: Near 52W high, volume contracting, tight price range, EMA stack bullish
    if (pct_from_h52 <= 10 and
        vol_contraction < 0.75 and
        price_range_20 < 12 and
        p > e50 > e200):
        conf = 85
        if vol_contraction < 0.5: conf = 92
        if pct_from_h52 < 5: conf = min(conf+5, 97)
        return "VCP", conf, (
            f"Volume has contracted to {vol_contraction:.0%} of 50-day avg. "
            f"Price range in last 20 days is only {price_range_20:.1f}%. "
            f"Stock is {pct_from_h52:.1f}% from 52W high. "
            f"This is a classic coiling setup — institutions are holding, retail is bored. "
            f"Wait for a volume expansion breakout above ₹{h52:.1f}."
        )

    # ── BREAKOUT ──────────────────────────────────────────────────────────────
    if pct_from_h52 <= 1 and vr >= 1.5 and p > e20 > e50 > e200:
        conf = 88
        if vr >= 2.5: conf = 93
        return "BREAKOUT", conf, (
            f"Stock is breaking above its 52W high of ₹{h52:.1f} with volume {vr:.1f}x average. "
            f"Full EMA stack bullish. This is a high-probability momentum entry. "
            f"Aggressive entry now. Conservative entry on a retest of ₹{h52:.1f}."
        )

    # ── BULL FLAG ─────────────────────────────────────────────────────────────
    # Big move up (last 20 days), then tight consolidation (last 5-7 days)
    move_20d = (last20.iloc[-1] - last20.iloc[0]) / last20.iloc[0] * 100
    range_5d  = (df["Close"].tail(7).max() - df["Close"].tail(7).min()) / df["Close"].tail(7).mean() * 100
    if (move_20d >= 10 and range_5d < 5 and
        vol_contraction < 0.85 and p > e20):
        conf = 80
        if move_20d >= 20: conf = 87
        return "BULL FLAG", conf, (
            f"Stock moved +{move_20d:.1f}% in last 20 days (the pole). "
            f"Now consolidating tightly — last 7 days range only {range_5d:.1f}% (the flag). "
            f"Volume contracting during flag = healthy. "
            f"Entry on breakout above flag high ₹{df['Close'].tail(7).max():.1f} on volume."
        )

    # ── FLAT BASE ─────────────────────────────────────────────────────────────
    if (price_range_20 < 8 and
        pct_from_h52 <= 15 and
        p > e50 > e200 and
        vol_contraction < 0.9):
        conf = 75
        return "FLAT BASE", conf, (
            f"Stock has been trading in a {price_range_20:.1f}% range for ~20 days near its highs. "
            f"Volume drying up = healthy base. This is a low-risk consolidation. "
            f"Entry when price breaks above the base high on 1.5x+ volume."
        )

    # ── ASCENDING TRIANGLE ────────────────────────────────────────────────────
    highs_20 = df["High"].tail(20)
    lows_20  = df["Low"].tail(20)
    high_flat = (highs_20.max() - highs_20.min()) / highs_20.mean() < 0.03
    low_rising= lows_20.iloc[-1] > lows_20.iloc[0]
    if high_flat and low_rising and p > e50:
        conf = 78
        return "ASCENDING TRIANGLE", conf, (
            f"Highs are flat around ₹{highs_20.max():.1f} (resistance). "
            f"Lows are rising = buyers getting more aggressive. "
            f"Classic breakout setup — entry above ₹{highs_20.max():.1f} on volume."
        )

    # ── MOMENTUM CONTINUATION ─────────────────────────────────────────────────
    if p > e20 > e50 > e200 and vr >= 1:
        conf = 70
        return "MOMENTUM CONTINUATION", conf, (
            f"Stock is in Stage 2 uptrend with full EMA alignment. "
            f"No specific pattern, but trend is intact. "
            f"Best entry on pullback to EMA20 (₹{e20:.1f}) or EMA10."
        )

    # ── PULLBACK TO EMA ───────────────────────────────────────────────────────
    near_e20 = abs(p - e20) / p < 0.03
    near_e50 = abs(p - e50) / p < 0.04
    if near_e20 and p > e50 > e200:
        conf = 76
        return "EMA20 PULLBACK", conf, (
            f"Stock has pulled back to its 20 EMA (₹{e20:.1f}) in an uptrend. "
            f"This is the classic Minervini/Qullamaggie low-risk entry zone. "
            f"Entry now with stop just below EMA20. Risk is minimal."
        )
    if near_e50 and p > e200:
        conf = 68
        return "EMA50 PULLBACK", conf, (
            f"Stock has pulled back to its 50 EMA (₹{e50:.1f}). "
            f"Deeper pullback — wider stop needed. "
            f"Only trade if RSI is not oversold and volume is drying up."
        )

    return "NO CLEAR PATTERN", 40, (
        "No tradable pattern detected. Price is between key levels without a clear setup. "
        "Wait for a VCP, breakout, or clean EMA pullback to form."
    )

# ─── SECOND LEG DETECTOR ─────────────────────────────────────────────────────
def detect_second_leg(df):
    """
    Identifies if a stock has already made one big move, formed a base, 
    and is about to make a SECOND (or third) leg up.
    These are often the highest conviction trades.
    """
    if len(df) < 60:
        return False, "", 0

    closes = df["Close"]
    p = float(closes.iloc[-1])

    # Find the big first move: look for a 30%+ run in any 60-day window in last 6 months
    window = 126  # 6 months
    df_recent = df.tail(window)
    max_price = float(df_recent["High"].max())
    min_price = float(df_recent["Low"].min())
    first_move = (max_price - min_price) / min_price * 100

    # Find if there was a base after the peak (contraction)
    peak_idx = df_recent["High"].idxmax()
    after_peak = df_recent.loc[peak_idx:]

    if len(after_peak) < 10:
        return False, "", 0

    base_low  = float(after_peak["Low"].min())
    base_depth= (max_price - base_low) / max_price * 100
    current_vs_base_low = (p - base_low) / base_low * 100

    # Second leg criteria:
    # 1. First move was at least 25%
    # 2. Base depth was less than 40% (not a crash, just a correction)
    # 3. Current price is recovering from base
    # 4. Stock is within 10% of the peak again
    pct_from_peak = (max_price - p) / max_price * 100

    if (first_move >= 25 and
        base_depth <= 35 and
        current_vs_base_low >= 10 and
        pct_from_peak <= 15):
        strength = "STRONG" if first_move >= 50 and base_depth <= 20 else "MODERATE"
        return True, (
            f"**Second Leg Detected ({strength}):** Stock made a {first_move:.0f}% first move, "
            f"then corrected only {base_depth:.0f}% (tight base = institutional holding). "
            f"Now recovering and {pct_from_peak:.0f}% from the prior high. "
            f"Second legs after tight bases are Minervini's highest conviction trades. "
            f"Base low was ₹{base_low:.1f} — this becomes your key support."
        ), min(95, 75 + int(first_move/10))
    return False, "", 0

# ─── LIQUIDITY GATE ──────────────────────────────────────────────────────────
def liq_gate(df):
    price   = float(df["Close"].iloc[-1])
    avg_vol = df["Volume"].tail(50).mean()
    to      = avg_vol * price
    return to, to >= 25_00_00_000

# ─── STOP LOSS CALCULATOR ────────────────────────────────────────────────────
def smart_sl(df, price):
    l    = df.iloc[-1]
    e10  = float(l["E10"])
    e20  = float(l["E20"])
    e50  = float(l["E50"])
    atr  = float(l["ATR"]) if not np.isnan(l["ATR"]) else price*0.02
    for label, sl in [
        ("1% below EMA10", e10*0.99),
        ("1% below EMA20", e20*0.99),
        ("2% below EMA50", e50*0.98),
        ("2× ATR",         price - 2*atr),
    ]:
        pct = (price - sl) / price * 100
        if 1.0 <= pct <= 6.0:
            return sl, pct, label, True
    return None, None, None, False

# ─── ENTRY LOGIC ─────────────────────────────────────────────────────────────
def entry_logic(df, price, pattern):
    l   = df.iloc[-1]
    e10 = float(l["E10"]); e20 = float(l["E20"])
    e50 = float(l["E50"]); e200= float(l["E200"])
    h52 = float(l["H52"]) if not np.isnan(l["H52"]) else price
    pct_h = (h52 - price) / h52 * 100 if h52 > 0 else 100

    if pattern in ("BREAKOUT",) or pct_h <= 1:
        return {
            "type": "BREAKOUT",
            "aggressive": price,
            "conservative": h52 * 1.005,
            "retest": h52 * 0.99,
            "note": f"Buy the breakout above ₹{h52:.1f}. Aggressive = now. Conservative = daily close above ₹{h52:.1f}. Retest = if price comes back to ₹{h52*0.99:.1f}."
        }
    elif pattern in ("VCP","FLAT BASE","ASCENDING TRIANGLE") or (1 < pct_h <= 5):
        return {
            "type": "PRE-BREAKOUT SETUP",
            "aggressive": price,
            "conservative": h52 * 1.005,
            "retest": e20 * 1.005,
            "note": f"Do NOT chase. Set a GTT alert at ₹{h52:.1f}. Entry only when price breaks ₹{h52:.1f} on volume ≥1.5× avg. Premature entry risks getting stopped out before the move."
        }
    elif pattern == "BULL FLAG":
        flag_high = float(df["Close"].tail(7).max())
        return {
            "type": "BULL FLAG BREAKOUT",
            "aggressive": flag_high * 1.001,
            "conservative": flag_high * 1.01,
            "retest": flag_high * 0.995,
            "note": f"Enter on break of flag high ₹{flag_high:.1f} on volume. Do not buy inside the flag — wait for the breakout candle."
        }
    elif pattern == "EMA20 PULLBACK":
        return {
            "type": "EMA20 PULLBACK (Best R:R)",
            "aggressive": e20 * 1.002,
            "conservative": e20 * 1.01,
            "retest": e20 * 0.995,
            "note": f"This is the ideal Minervini entry — buying the dip in an uptrend. Enter near ₹{e20:.1f}. Stop just below EMA20 = tiny risk, big potential."
        }
    elif pattern == "MOMENTUM CONTINUATION":
        return {
            "type": "MOMENTUM — WAIT FOR DIP",
            "aggressive": price,
            "conservative": e10 * 1.005,
            "retest": e20 * 1.005,
            "note": f"Stock is running. Best NOT to chase. Wait for a 1-3 day pullback to EMA10 (₹{e10:.1f}) or EMA20 (₹{e20:.1f}). Chasing extended stocks is the #1 mistake."
        }
    else:
        return {
            "type": "WAIT — NO ENTRY",
            "aggressive": 0,
            "conservative": 0,
            "retest": 0,
            "note": "No clean entry. Either wait for a breakout or a pullback to a key EMA level."
        }

# ─── TARGETS ─────────────────────────────────────────────────────────────────
def targets(price, sl):
    if not sl: return None, None, None, 0
    r  = price - sl
    t1 = price + 1.5 * r
    t2 = price + 3.0 * r
    t3 = price + 5.0 * r
    rr = 3.0
    return t1, t2, t3, rr

# ─── SCORING ─────────────────────────────────────────────────────────────────
def score(df, r6, r12, rs, regime_pen, pattern, pattern_conf):
    l    = df.iloc[-1]
    p    = float(l["Close"])
    e20  = float(l["E20"]); e50=float(l["E50"]); e200=float(l["E200"])
    h52  = float(l["H52"]) if not np.isnan(l["H52"]) else p
    vr   = float(l["VR"])  if not np.isnan(l["VR"])  else 1
    rsi_ = float(l["RSI"]) if not np.isnan(l["RSI"]) else 50
    mac  = float(l["MACD"])if not np.isnan(l["MACD"])else 0
    hist = float(l["HIST"])if not np.isnan(l["HIST"])else 0
    pct_h= (h52-p)/h52*100 if h52>0 else 100

    sc = {}; flags = []

    # EMA Stack 20pts
    if p>e20>e50>e200:   sc["ema"]=20; flags.append(("bull","Full EMA stack: Price > 20 > 50 > 200 — Stage 2 confirmed ✓"))
    elif e20>e50>e200:   sc["ema"]=14; flags.append(("warn","EMA aligned but price below EMA20 — wait for reclaim"))
    elif e20>e50 or e50>e200: sc["ema"]=7; flags.append(("warn","Partial EMA alignment — Stage 2 developing"))
    else:                sc["ema"]=0;  flags.append(("bear","EMA stack bearish — not Stage 2"))

    # 52W High 15pts
    if pct_h<=0:    sc["h"]=15; flags.append(("bull","AT/ABOVE 52W high — breakout confirmed ✓"))
    elif pct_h<=1:  sc["h"]=13; flags.append(("bull",f"{pct_h:.1f}% from 52W high — imminent ✓"))
    elif pct_h<=3:  sc["h"]=11; flags.append(("bull",f"{pct_h:.1f}% from 52W high — launchpad"))
    elif pct_h<=7:  sc["h"]=7;  flags.append(("warn",f"{pct_h:.1f}% from 52W high — in base"))
    elif pct_h<=15: sc["h"]=3;  flags.append(("warn",f"{pct_h:.1f}% from 52W high — extended base"))
    else:           sc["h"]=0;  flags.append(("bear",f"{pct_h:.1f}% from 52W high — too far"))

    # Volume 15pts
    if vr>=3:   sc["v"]=15; flags.append(("bull",f"Volume {vr:.1f}x avg — exceptional institutional surge ✓"))
    elif vr>=2: sc["v"]=12; flags.append(("bull",f"Volume {vr:.1f}x avg — strong buying"))
    elif vr>=1.5:sc["v"]=10;flags.append(("bull",f"Volume {vr:.1f}x avg — confirmed ✓"))
    elif vr>=1: sc["v"]=6;  flags.append(("warn",f"Volume {vr:.1f}x avg — average"))
    else:       sc["v"]=2;  flags.append(("warn",f"Volume drying ({vr:.1f}x) — VCP forming"))

    # MACD 15pts
    if mac>0 and hist>0:    sc["macd"]=15; flags.append(("bull","MACD positive + histogram expanding — accelerating ✓"))
    elif mac>0:             sc["macd"]=10; flags.append(("warn","MACD positive but slowing"))
    elif mac>-0.5:          sc["macd"]=5;  flags.append(("warn","MACD near zero — watch for crossover"))
    else:                   sc["macd"]=0;  flags.append(("bear","MACD negative — avoid"))

    # RSI 10pts
    if 50<=rsi_<=65:   sc["rsi"]=10; flags.append(("bull",f"RSI {rsi_:.0f} — sweet spot, room to run ✓"))
    elif 65<rsi_<=70:  sc["rsi"]=7;  flags.append(("warn",f"RSI {rsi_:.0f} — approaching overbought"))
    elif 45<=rsi_<50:  sc["rsi"]=5;  flags.append(("warn",f"RSI {rsi_:.0f} — recovering"))
    elif 70<rsi_<=80:  sc["rsi"]=2;  flags.append(("warn",f"RSI {rsi_:.0f} — overbought, chase risk"))
    else:
        rsi_reason = "extremely overbought" if rsi_>80 else "downtrend territory"
        sc["rsi"]=0;  flags.append(("bear",f"RSI {rsi_:.0f} — {rsi_reason}"))

    # 6M Return 10pts
    if r6 is not None:
        if r6>=50:   sc["r6"]=10; flags.append(("bull",f"6M: +{r6:.1f}% — exceptional ✓"))
        elif r6>=35: sc["r6"]=8;  flags.append(("bull",f"6M: +{r6:.1f}% — strong outperformer"))
        elif r6>=20: sc["r6"]=6;  flags.append(("bull",f"6M: +{r6:.1f}% — above average"))
        elif r6>=10: sc["r6"]=4;  flags.append(("warn",f"6M: +{r6:.1f}% — moderate"))
        elif r6>=0:  sc["r6"]=2;  flags.append(("warn",f"6M: +{r6:.1f}% — weak"))
        else:        sc["r6"]=0;  flags.append(("bear",f"6M: {r6:.1f}% — negative"))
    else: sc["r6"]=5

    # 12M Return 10pts
    if r12 is not None:
        if r12>=60:   sc["r12"]=10; flags.append(("bull",f"12M: +{r12:.1f}% — multi-bagger ✓"))
        elif r12>=40: sc["r12"]=8;  flags.append(("bull",f"12M: +{r12:.1f}% — strong"))
        elif r12>=25: sc["r12"]=6;  flags.append(("bull",f"12M: +{r12:.1f}% — solid"))
        elif r12>=10: sc["r12"]=4;  flags.append(("warn",f"12M: +{r12:.1f}% — modest"))
        elif r12>=0:  sc["r12"]=2;  flags.append(("warn",f"12M: +{r12:.1f}% — weak"))
        else:         sc["r12"]=0;  flags.append(("bear",f"12M: {r12:.1f}% — negative"))
    else: sc["r12"]=5

    # RS vs Nifty 10pts
    if rs is not None:
        if rs>=20:   sc["rs"]=10; flags.append(("bull",f"RS vs Nifty: +{rs:.1f}% — massively outperforming ✓"))
        elif rs>=10: sc["rs"]=8;  flags.append(("bull",f"RS vs Nifty: +{rs:.1f}% — outperforming"))
        elif rs>=5:  sc["rs"]=6;  flags.append(("bull",f"RS vs Nifty: +{rs:.1f}% — slightly ahead"))
        elif rs>=0:  sc["rs"]=4;  flags.append(("warn",f"RS vs Nifty: +{rs:.1f}% — matching market"))
        else:        sc["rs"]=0;  flags.append(("bear",f"RS vs Nifty: {rs:.1f}% — underperforming"))
    else: sc["rs"]=5

    # Pattern bonus 5pts
    if pattern_conf >= 85:   sc["pat"]=5; flags.append(("bull",f"Pattern: {pattern} (confidence {pattern_conf}%) ✓"))
    elif pattern_conf >= 70: sc["pat"]=3; flags.append(("warn",f"Pattern: {pattern} (confidence {pattern_conf}%)"))
    else:                    sc["pat"]=0; flags.append(("bear",f"Pattern: {pattern} — low confidence"))

    # Liquidity
    sc["liq"] = 5

    raw   = sum(sc.values())  # max 115
    norm  = int((raw / 115) * 100)

    # Spike penalty
    p2 = float(df["Close"].iloc[-2]) if len(df)>=2 else float(df["Close"].iloc[-1])
    today_move = (float(df["Close"].iloc[-1]) - p2) / p2 * 100
    spike_pen  = -20 if today_move>=10 else -10 if today_move>=8 else -5 if today_move>=5 else 0
    if spike_pen < 0:
        flags.append(("bear",f"⚠️ SPIKE PENALTY: +{today_move:.1f}% today — do not chase, penalty {spike_pen} pts"))

    final = max(0, norm + spike_pen - regime_pen)

    if final>=90:   verdict="ELITE SETUP"
    elif final>=80: verdict="STRONG SETUP"
    elif final>=70: verdict="TRADABLE"
    else:           verdict="AVOID"

    return final, norm, spike_pen, verdict, sc, flags, today_move

# ─── HTML HELPERS ────────────────────────────────────────────────────────────
VC = {"ELITE SETUP":"#00c853","STRONG SETUP":"#ff9100","TRADABLE":"#2979ff","AVOID":"#f44336"}

def bar(label, s, mx):
    pct = min(s/mx*100,100)
    col = "#00c853" if pct>=75 else "#ff9100" if pct>=50 else "#f44336"
    sym = "✓" if pct>=75 else "◆" if pct>=50 else "✗"
    return f"""<div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="color:#7b8fba;font-size:12px;">{label}</span>
        <span style="color:{col};font-size:12px;font-weight:700;">{sym} {s}/{mx}</span>
      </div>
      <div style="height:5px;background:#1a2744;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:{pct}%;background:{col};border-radius:3px;"></div>
      </div></div>"""

def flags_html(flags):
    ic={"bull":"▲","warn":"◆","bear":"▼"}; cl={"bull":"#00c853","warn":"#ff9100","bear":"#f44336"}
    return "".join([f"""<div style="display:flex;gap:8px;padding:7px 11px;background:#060e1c;border:1px solid {cl[t]}20;border-radius:6px;margin-bottom:5px;">
      <span style="color:{cl[t]};font-weight:700;min-width:12px;">{ic[t]}</span>
      <span style="color:#7b8fba;font-size:12px;line-height:1.5;">{m}</span></div>""" for t,m in flags])

def tile(label, val, col="#e0e8ff", sub=""):
    sub_html = f'<div style="color:#5c7099;font-size:10px;margin-top:2px;">{sub}</div>' if sub else ""
    return f"""<div style="background:#060e1c;border:1px solid {col}25;border-radius:8px;padding:10px 12px;">
      <div style="color:#5c7099;font-size:9px;font-weight:600;letter-spacing:0.5px;margin-bottom:3px;">{label}</div>
      <div style="color:{col};font-size:13px;font-weight:700;">{val}</div>
      {sub_html}
    </div>"""

# ─── CHARTINK SCANNERS WITH FULL EXPLANATIONS ─────────────────────────────────
SCANNERS = {
    "🟢 Tier 1 — Fresh 52W High Breakout": {
        "code": "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "what": "Finds stocks that just broke their 52-week high THIS WEEK with strong volume.",
        "why": "A 52-week high breakout is the #1 momentum signal. Stocks making new highs tend to keep making new highs. This is the core of O'Neil's CANSLIM and Minervini's system.",
        "conditions": [
            ("Universe", "{nifty 200}", "Only liquid, large/midcap stocks. No penny stocks, no operator stocks."),
            ("52W High Break", "latest close > 1 weeks max(52, high)", "Price closed ABOVE the highest price of the last 52 weeks. This is the breakout signal."),
            ("Volume Confirmation", "latest volume > 1.5 × sma(volume, 50)", "Volume is 1.5× the 50-day average. Without volume, a breakout is fake. Institutions must be buying."),
            ("EMA 20 Filter", "close > ema(20)", "Price above short-term trend = immediate momentum is bullish."),
            ("EMA Stack", "ema(20) > ema(50) > ema(200)", "All three EMAs in bullish order = confirmed Stage 2 uptrend. Stock is healthy at all timeframes."),
            ("Liquidity Gate", "volume × close > 25,00,00,000", "Daily turnover above ₹25 Crore. Ensures you can enter and exit without moving the price."),
        ],
        "when": "Run this FIRST every evening after 4 PM IST. Any result here = your highest priority trade for tomorrow.",
        "action": "These stocks are actively breaking out. Enter at market open or on a retest of the breakout level.",
        "priority": "HIGHEST",
        "color": "#00c853",
    },
    "🟠 Tier 2 — Near 52W High (VCP / Pre-Breakout)": {
        "code": "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "what": "Finds stocks that are within 3% of their 52W high with volume DRYING UP — classic VCP/coiling setup.",
        "why": "Before every major breakout, volume dries up as weak hands exit and institutions quietly accumulate. This is the setup BEFORE the Tier 1 signal fires. Catching it here gives better entry and tighter stop.",
        "conditions": [
            ("Within 3% of 52W High", "close > 0.97 × weekly max(52, high)", "Within striking distance of the breakout level. Close enough to matter."),
            ("Below 52W High", "close < weekly max(52, high)", "Has NOT broken out yet — this is the anticipation entry, not the breakout entry."),
            ("EMA Stack Bullish", "ema(20) > ema(50) > ema(200)", "Trend is healthy. The base is forming in an uptrend, not a downtrend."),
            ("Volume Contraction", "sma(volume,10) < sma(volume,50)", "10-day average volume is LESS than 50-day average. Volume is drying up = VCP signal. Institutions are holding, not selling."),
            ("Liquidity", "volume × close > ₹25Cr", "Minimum liquidity requirement."),
        ],
        "when": "Run this after Tier 1. Results here go on your GTT alert list. Set price alert at the 52W high.",
        "action": "DO NOT enter yet. Set a GTT alert at the 52W high. When price breaks that level on volume, THEN enter.",
        "priority": "HIGH — BUILD WATCHLIST",
        "color": "#ff9100",
    },
    "🔵 Tier 3 — Momentum Continuation (Second Leg Candidates)": {
        "code": "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "what": "Finds stocks in confirmed Stage 2 uptrend that are up 25%+ in both 6M and 12M — sustained momentum leaders.",
        "why": "These are the stocks that keep going. A stock up 50% in 6 months with a bullish EMA stack is MORE likely to keep rising than a stock that just started moving. This is counter-intuitive but mathematically proven by Nifty200 Momentum30 index (19.3% CAGR).",
        "conditions": [
            ("EMA Stack", "close > ema(20) > ema(50) > ema(200)", "Full bullish alignment across all timeframes."),
            ("6M Momentum", "close > 1.25 × 26 weeks ago close", "Stock is up at least 25% in the last 6 months. Strong intermediate momentum."),
            ("12M Momentum", "close > 1.25 × 52 weeks ago close", "Stock is up at least 25% in the last 12 months. Long-term momentum is sustained."),
            ("Liquidity", "volume × close > ₹25Cr", "Minimum liquidity requirement."),
        ],
        "when": "Run this weekly. Results are your core momentum portfolio candidates. Enter on pullbacks to EMA20.",
        "action": "Don't chase price. Wait for a 2-5 day pullback to EMA20 with drying volume, then enter with stop below EMA20.",
        "priority": "MEDIUM — ENTER ON PULLBACKS",
        "color": "#2979ff",
    },
    "🟣 Tier 4 — VCP / Tight Base Formation": {
        "code": "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "what": "Pure VCP detector — stocks within 10% of highs where volume has contracted more than 25%.",
        "why": "This is Minervini's bread and butter. When volume contracts sharply while price stays near highs, it means the stock is coiling like a spring. The breakout when it comes is explosive because supply has been exhausted.",
        "conditions": [
            ("Within 10% of 52W High", "close > 0.90 × weekly max(52, high)", "Near the highs but still below — base is forming near the top."),
            ("EMA Trend", "ema(20) > ema(50) > ema(200)", "Base is forming in an uptrend, not a downtrend. Critical difference."),
            ("Volume Contraction >25%", "sma(volume,10) < 0.75 × sma(volume,50)", "10-day average volume is less than 75% of 50-day average. Volume has dried up significantly = supply exhaustion."),
            ("Liquidity", "volume × close > ₹25Cr", "Minimum liquidity."),
        ],
        "when": "Run this daily. When combined with ATR contraction visible on charts, these are your highest-conviction setups.",
        "action": "These need chart confirmation. Open each result on TradingView. Look for tightening price bars + shrinking ATR + volume dry-up. Entry on breakout above the tight range.",
        "priority": "HIGH — CHART REVIEW REQUIRED",
        "color": "#aa00ff",
    },
}

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div style="width:42px;height:42px;background:linear-gradient(135deg,#1565c0,#0d47a1);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;">📈</div>
      <div>
        <div style="font-size:18px;font-weight:800;color:#e0e8ff;letter-spacing:0.5px;">NSE ELITE SWING TRADING ADVISOR</div>
        <div style="font-size:11px;color:#5c7099;">Minervini × O'Neil × Weinstein × Qullamaggie · VCP + Pattern Detection · 7-Factor Scoring</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MARKET REGIME ─────────────────────────────────────────────────────────
    with st.spinner("Checking market regime..."):
        nifty_df  = fetch_index("^NSEI")
        bnifty_df = fetch_index("^NSEBANK")
    regime_data, regime_pen = market_regime(nifty_df, bnifty_df)

    regime_html = ""
    overall_ok  = True
    for idx, (msg, col, pen) in regime_data.items():
        dot = "🟢" if col=="#00c853" else "🟠" if col=="#ff9100" else "🔴"
        pen_html = f' <span style="color:#5c7099;font-size:11px;">(-{pen} pts)</span>' if pen > 0 else ""
        regime_html += f"<div style='margin-bottom:4px;'><span style='color:#5c7099;font-size:10px;font-weight:600;'>{idx}:</span> <span style='color:{col};font-weight:700;font-size:13px;'>{dot} {msg}</span>{pen_html}</div>"
        if col != "#00c853": overall_ok = False

    no_trade_banner = ""
    if regime_pen >= 20:
        no_trade_banner = """<div style="color:#f44336;font-size:13px;font-weight:700;margin-top:8px;">
        ⚠️ CAPITAL PRESERVATION MODE RECOMMENDED — Market is in bearish regime. Only exceptional setups above 85 qualify. Reduce position sizes by 50%.</div>"""

    st.markdown(f"""
    <div style="background:#0d1b2e;border:2px solid {'#00c85340' if overall_ok else '#f4433640'};border-radius:10px;padding:14px 18px;margin-bottom:18px;">
      <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">MARKET REGIME — UPDATED LIVE</div>
      {regime_html}{no_trade_banner}
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["⚡ Stock Scorer", "🔍 Pattern Guide", "📡 Chartink Scanners", "📖 System Rules"])

    # ── TAB 1: SCORER ─────────────────────────────────────────────────────────
    with tabs[0]:
        col_l, col_r = st.columns([1, 1.9], gap="large")
        with col_l:
            st.markdown("### 🔍 Stock Analysis")
            symbol  = st.text_input("NSE Symbol", placeholder="TCS, DATAPATTNS, AKUMS...").upper().strip()
            pick    = st.selectbox("Or pick from list", [""]+POPULAR)
            if pick: symbol = pick
            capital = st.number_input("Capital (₹)", min_value=100000, max_value=10000000, value=300000, step=50000, format="%d")
            risk    = st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25)
            go      = st.button("⚡ Analyze Stock", use_container_width=True)

            st.markdown("""
            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:8px;padding:12px;margin-top:12px;">
              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">WHAT THIS ANALYZES</div>
              <div style="color:#7b8fba;font-size:11px;line-height:1.9;">
                ✓ 7 scoring factors<br>
                ✓ Pattern detection (VCP, Flag, Base...)<br>
                ✓ Second leg detector<br>
                ✓ Smart stop loss (EMA-based)<br>
                ✓ 4 entry types (Aggressive/Conservative/Breakout/Retest)<br>
                ✓ 3 targets (1.5R / 3R / 5R)<br>
                ✓ Position sizing<br>
                ✓ Exit plan<br>
                ✓ Spike penalty<br>
                ✓ Market regime filter
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_r:
            if go and symbol:
                with st.spinner(f"Fetching {symbol}..."):
                    df, ticker = fetch(symbol)

                if df is None:
                    st.error(f"❌ Could not fetch {symbol}. Check symbol.")
                else:
                    df = enrich(df)
                    l  = df.iloc[-1]
                    p  = float(l["Close"])

                    # Liquidity gate
                    to, liq_ok = liq_gate(df)
                    if not liq_ok:
                        st.markdown(f"""
                        <div style="background:#1a0a0a;border:2px solid #f44336;border-radius:10px;padding:20px;text-align:center;">
                          <div style="font-size:28px;">🚫</div>
                          <div style="color:#f44336;font-size:18px;font-weight:800;margin-top:8px;">LIQUIDITY FAIL — NOT SCORED</div>
                          <div style="color:#7b8fba;font-size:13px;margin-top:8px;">
                            Daily turnover: ₹{to/1e7:.1f} Cr &nbsp;|&nbsp; Minimum: ₹25 Cr<br>
                            Cannot trade this safely. Execution risk too high.
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.stop()

                    r6, r12, rs = returns(df, nifty_df)
                    pattern, pconf, pexpl = detect_pattern(df)
                    is_2leg, leg2_msg, leg2_conf = detect_second_leg(df)
                    final, raw, sp, verdict, sc, fls, today_mv = score(df, r6, r12, rs, regime_pen, pattern, pconf)
                    sl, sl_pct, sl_lbl, sl_ok = smart_sl(df, p)
                    ei  = entry_logic(df, p, pattern)
                    t1, t2, t3, rr = targets(p, sl)

                    prev    = float(df["Close"].iloc[-2])
                    day_chg = (p - prev) / prev * 100
                    h52     = float(l["H52"]) if not np.isnan(l["H52"]) else p
                    e10=float(l["E10"]); e20=float(l["E20"]); e50=float(l["E50"]); e200=float(l["E200"])
                    vr_=float(l["VR"]) if not np.isnan(l["VR"]) else 0
                    rsi_=float(l["RSI"]) if not np.isnan(l["RSI"]) else 0
                    mac_=float(l["MACD"]) if not np.isnan(l["MACD"]) else 0
                    pct_h=(h52-p)/h52*100 if h52>0 else 0
                    qty = int((capital*risk/100)/(p*sl_pct/100)) if sl_ok and sl_pct else 0

                    chg_col   = "#00c853" if day_chg>=0 else "#f44336"
                    chg_arrow = "▲" if day_chg>=0 else "▼"
                    spike_html= "<div style='color:#f44336;font-size:11px;font-weight:600;'>⚠️ BIG MOVE TODAY — spike penalty applied</div>" if abs(today_mv)>=5 else ""
                    date_str  = df.index[-1].strftime('%d %b %Y')
                    turn_str  = f"{to/1e7:.1f}"
                    chg_str   = f"{abs(day_chg):.2f}"
                    price_str = f"{p:,.2f}"

                    # Header
                    st.markdown(f"""
                    <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:12px;">
                      <div style="display:flex;justify-content:space-between;">
                        <div>
                          <div style="color:#90caf9;font-size:11px;font-weight:600;letter-spacing:1px;">{ticker} · {date_str} · Turnover ₹{turn_str}Cr/day ✓</div>
                          <div style="color:#e0e8ff;font-size:26px;font-weight:900;margin-top:4px;">₹{price_str}</div>
                        </div>
                        <div style="text-align:right;">
                          <div style="color:{chg_col};font-size:16px;font-weight:700;">{chg_arrow} {chg_str}%</div>
                          {spike_html}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Pre-compute all tile values to avoid nested f-strings
                    ph_col   = "#00c853" if pct_h<=3 else "#ff9100" if pct_h<=10 else "#f44336"
                    ph_sub   = "ABOVE ✓" if pct_h<=0 else str(round(pct_h,1))+"% below"
                    ph_val   = "₹"+f"{h52:,.1f}"

                    vr_col   = "#00c853" if vr_>=1.5 else "#ff9100" if vr_>=1 else "#f44336"
                    vr_val   = f"{vr_:.1f}x avg"

                    rsi_col  = "#00c853" if 50<=rsi_<=65 else "#ff9100" if rsi_<80 else "#f44336"
                    rsi_val  = str(round(rsi_,0))[:-2] if rsi_ == int(rsi_) else f"{rsi_:.0f}"

                    mac_arrow = "▲" if mac_>0 else "▼"
                    mac_val  = mac_arrow+" "+f"{abs(mac_):.2f}"
                    mac_col  = "#00c853" if mac_>0 and float(l["HIST"])>0 else "#ff9100" if mac_>0 else "#f44336"

                    e20_col  = "#00c853" if p>e20 else "#f44336"
                    e20_sub  = "✓ above" if p>e20 else "✗ below"
                    e20_val  = "₹"+f"{e20:,.1f}"

                    e50_col  = "#00c853" if e20>e50 else "#f44336"
                    e50_sub  = "✓ 20>50" if e20>e50 else "✗"
                    e50_val  = "₹"+f"{e50:,.1f}"

                    e200_col = "#00c853" if e50>e200 else "#f44336"
                    e200_sub = "✓ 50>200" if e50>e200 else "✗"
                    e200_val = "₹"+f"{e200:,.1f}"

                    r6c      = "#00c853" if r6 and r6>=20 else "#ff9100" if r6 and r6>=0 else "#f44336"
                    if r6 is None:    r6_val = "—"
                    elif r6 >= 0:     r6_val = "+"+f"{r6:.1f}"+"%"
                    else:             r6_val = f"{r6:.1f}"+"%"

                    # Data tiles row 1
                    c1,c2,c3,c4 = st.columns(4)
                    with c1: st.markdown(tile("52W HIGH",   ph_val,  ph_col,  ph_sub),  unsafe_allow_html=True)
                    with c2: st.markdown(tile("VOLUME",     vr_val,  vr_col),            unsafe_allow_html=True)
                    with c3: st.markdown(tile("RSI",        rsi_val, rsi_col),           unsafe_allow_html=True)
                    with c4: st.markdown(tile("MACD",       mac_val, mac_col),           unsafe_allow_html=True)

                    c5,c6,c7,c8 = st.columns(4)
                    with c5: st.markdown(tile("EMA 20",  e20_val,  e20_col,  e20_sub),  unsafe_allow_html=True)
                    with c6: st.markdown(tile("EMA 50",  e50_val,  e50_col,  e50_sub),  unsafe_allow_html=True)
                    with c7: st.markdown(tile("EMA 200", e200_val, e200_col, e200_sub), unsafe_allow_html=True)
                    with c8: st.markdown(tile("6M RETURN", r6_val, r6c),                unsafe_allow_html=True)

                    st.markdown("---")

                    # Pattern + Second Leg
                    pat_col={"VCP":"#00c853","BREAKOUT":"#00c853","BULL FLAG":"#ff9100","FLAT BASE":"#ff9100","ASCENDING TRIANGLE":"#2979ff","EMA20 PULLBACK":"#2979ff","MOMENTUM CONTINUATION":"#90caf9","NO CLEAR PATTERN":"#f44336"}.get(pattern,"#7b8fba")
                    st.markdown(f"""
                    <div style="background:#0d1b2e;border:1px solid {pat_col}40;border-left:4px solid {pat_col};border-radius:10px;padding:14px;margin-bottom:12px;">
                      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                        <span style="background:{pat_col}20;color:{pat_col};border:1px solid {pat_col}40;border-radius:4px;padding:2px 10px;font-size:10px;font-weight:800;letter-spacing:1px;">PATTERN: {pattern}</span>
                        <span style="color:#5c7099;font-size:11px;">Confidence: {pconf}%</span>
                      </div>
                      <div style="color:#7b8fba;font-size:13px;line-height:1.7;">{pexpl}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if is_2leg:
                        st.markdown(f"""
                        <div style="background:#0d1b2e;border:1px solid #00c85340;border-left:4px solid #00c853;border-radius:10px;padding:14px;margin-bottom:12px;">
                          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                            <span style="background:#00c85320;color:#00c853;border:1px solid #00c85340;border-radius:4px;padding:2px 10px;font-size:10px;font-weight:800;letter-spacing:1px;">🚀 SECOND LEG DETECTED — HIGHEST CONVICTION</span>
                          </div>
                          <div style="color:#7b8fba;font-size:13px;line-height:1.7;">{leg2_msg}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Big score
                    vc = VC[verdict]
                    st.markdown(f"""
                    <div style="background:#060e1c;border:2px solid {vc}50;border-radius:14px;padding:22px;text-align:center;margin-bottom:14px;">
                      <div style="font-size:68px;font-weight:900;color:{vc};line-height:1;">{final}</div>
                      <div style="color:#5c7099;font-size:11px;margin-bottom:12px;">OUT OF 100 · Raw: {raw}{" · Spike: "+str(sp) if sp<0 else ""}{" · Regime: -"+str(regime_pen) if regime_pen>0 else ""}</div>
                      <div style="display:inline-block;background:{vc}20;color:{vc};border:1px solid {vc}50;border-radius:8px;padding:6px 24px;font-size:15px;font-weight:800;letter-spacing:1px;">{verdict}</div>
                      {"<div style='color:#f44336;font-size:13px;font-weight:700;margin-top:12px;'>🚫 NO TRADE IS THE BEST TRADE</div>" if verdict=="AVOID" else "<div style='color:" + vc + ";font-size:13px;font-weight:700;margin-top:12px;'>→ " + ("BUY BREAKOUT" if final>=80 else "TRADABLE — HALF SIZE") + "</div>"}
                    </div>
                    """, unsafe_allow_html=True)

                    if verdict != "AVOID":
                        # Entry section
                        et_col={"BREAKOUT":"#00c853","PRE-BREAKOUT SETUP":"#ff9100","BULL FLAG BREAKOUT":"#ff9100","EMA20 PULLBACK (Best R:R)":"#2979ff","MOMENTUM — WAIT FOR DIP":"#90caf9","WAIT — NO ENTRY":"#f44336"}.get(ei["type"],"#7b8fba")
                        st.markdown(f"""
                        <div style="background:#0d1b2e;border:1px solid {et_col}40;border-left:4px solid {et_col};border-radius:10px;padding:16px;margin-bottom:12px;">
                          <div style="margin-bottom:8px;"><span style="background:{et_col}20;color:{et_col};border:1px solid {et_col}40;border-radius:4px;padding:2px 10px;font-size:10px;font-weight:800;letter-spacing:1px;">ENTRY: {ei['type']}</span></div>
                          <div style="color:#7b8fba;font-size:13px;line-height:1.7;">{ei['note']}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if sl_ok and t1:
                            rr_col="#00c853" if rr>=3 else "#f44336"
                            st.markdown(f"""
                            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:12px;">
                              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">TRADE PLAN</div>
                              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
                                <div style="background:#060e1c;border:1px solid #2979ff30;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">AGGRESSIVE ENTRY</div>
                                  <div style="color:#2979ff;font-size:13px;font-weight:700;">₹{ei['aggressive']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">Enter now</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #90caf930;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">CONSERVATIVE</div>
                                  <div style="color:#90caf9;font-size:13px;font-weight:700;">₹{ei['conservative']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">Wait for confirm</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #f4433630;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">STOP LOSS ({sl_pct:.1f}%)</div>
                                  <div style="color:#f44336;font-size:13px;font-weight:700;">₹{sl:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">{sl_lbl}</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #7b8fba30;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">RETEST ENTRY</div>
                                  <div style="color:#7b8fba;font-size:13px;font-weight:700;">₹{ei['retest']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">If price dips</div>
                                </div>
                              </div>
                              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
                                <div style="background:#060e1c;border:1px solid #ff910030;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">TARGET 1 — Book 30%</div>
                                  <div style="color:#ff9100;font-size:13px;font-weight:700;">₹{t1:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">+{(t1-p)/p*100:.1f}% · 1.5R · Move stop to breakeven</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #00c85340;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">TARGET 2 — Book 30%</div>
                                  <div style="color:#00c853;font-size:13px;font-weight:700;">₹{t2:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">+{(t2-p)/p*100:.1f}% · 3R ✓</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #00c85320;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:3px;">TARGET 3 — Trail 40%</div>
                                  <div style="color:#00c853;font-size:13px;font-weight:700;">₹{t3:,.1f}</div>
                                  <div style="color:#5c7099;font-size:9px;margin-top:2px;">+{(t3-p)/p*100:.1f}% · 5R · Trail EMA10</div>
                                </div>
                              </div>
                              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <div style="background:#060e1c;border:1px solid {rr_col}30;border-radius:8px;padding:10px;text-align:center;">
                                  <div style="color:#5c7099;font-size:10px;margin-bottom:3px;">RISK : REWARD</div>
                                  <div style="color:{rr_col};font-size:16px;font-weight:800;">1 : {rr:.1f} {'✓' if rr>=3 else '✗ BELOW MINIMUM'}</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #2979ff20;border-radius:8px;padding:10px;">
                                  <div style="color:#5c7099;font-size:10px;margin-bottom:3px;">POSITION SIZE ({risk}% risk on ₹{capital:,})</div>
                                  <div style="color:#90caf9;font-size:13px;font-weight:700;">{qty} shares · ₹{qty*p:,.0f}</div>
                                </div>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Exit plan
                            st.markdown(f"""
                            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;margin-bottom:12px;">
                              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">EXIT PLAN</div>
                              <div style="color:#7b8fba;font-size:12px;line-height:2.1;">
                                📌 <strong style="color:#e0e8ff;">Entry confirmed:</strong> GTT stop loss at ₹{sl:,.1f} ({sl_lbl}) — place IMMEDIATELY after fill.<br>
                                📌 <strong style="color:#ff9100;">At T1 (₹{t1:,.1f}):</strong> Book 30% profit. Move stop to your entry price (breakeven). Trade is now risk-free.<br>
                                📌 <strong style="color:#00c853;">At T2 (₹{t2:,.1f}):</strong> Book another 30%. Raise trailing stop to T1 level.<br>
                                📌 <strong style="color:#00c853;">Remaining 40%:</strong> Trail using daily close below EMA10 (₹{e10:,.1f}). Let it run.<br>
                                🚨 <strong style="color:#f44336;">Hard stop:</strong> If price closes below ₹{sl:,.1f} — exit entire position. No exceptions.<br>
                                ⏱️ <strong style="color:#ff9100;">Time stop:</strong> If no meaningful movement in 15 trading days — exit and redeploy capital.
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                    # Score breakdown
                    sc_bars = "".join([
                        bar("EMA Stack (20>50>200)", sc.get("ema",0), 20),
                        bar("52W High Position",     sc.get("h",0),   15),
                        bar("Volume",                sc.get("v",0),   15),
                        bar("MACD",                  sc.get("macd",0),15),
                        bar("RSI",                   sc.get("rsi",0), 10),
                        bar("6M Return",             sc.get("r6",0),  10),
                        bar("12M Return",            sc.get("r12",0), 10),
                        bar("RS vs Nifty",           sc.get("rs",0),  10),
                        bar("Pattern Bonus",         sc.get("pat",0),  5),
                        bar("Liquidity",             sc.get("liq",0),  5),
                    ])
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;margin-bottom:12px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">SCORE BREAKDOWN</div>{sc_bars}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:14px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">SIGNAL FLAGS — WHY THIS SCORE</div>{flags_html(fls)}</div>', unsafe_allow_html=True)

            elif not go:
                st.markdown("""
                <div style="background:#0d1b2e;border:1px solid #2979ff30;border-radius:10px;padding:30px;text-align:center;margin-top:10px;">
                  <div style="font-size:36px;margin-bottom:12px;">🔍</div>
                  <div style="color:#e0e8ff;font-size:15px;font-weight:600;margin-bottom:8px;">Enter any NSE stock symbol</div>
                  <div style="color:#5c7099;font-size:13px;line-height:1.9;">
                    Detects: VCP · Bull Flag · Flat Base · Ascending Triangle · Second Leg<br>
                    Scores: EMA Stack · MACD · RSI · Volume · Returns · RS vs Nifty<br>
                    Outputs: Entry · Stop Loss · 3 Targets · Position Size · Exit Plan
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: PATTERN GUIDE ──────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 🔍 Pattern Detection Guide")
        st.markdown("<p style='color:#7b8fba;'>Every pattern detected by the app explained — what it looks like, why it works, and when to enter.</p>", unsafe_allow_html=True)

        patterns = [
            ("VCP — Volatility Contraction Pattern", "#00c853", "Minervini's #1 setup",
             "A series of smaller and smaller price corrections with declining volume — the stock is coiling like a spring.",
             ["Big move up (Stage 2)","Correction 1: large (15-20%) on volume","Correction 2: smaller (10%) on less volume","Correction 3: even smaller (5-7%) on low volume","Correction 4: tiny (2-4%) on very low volume — the VCP tight point","BREAKOUT on huge volume ← entry"],
             "Entry on breakout above the right side of the VCP. Stop below the last contraction low. Volume must be 2x+ on breakout day.",
             "AKUMS, DATAPATTNS before their big moves are classic VCP examples."),
            ("Bull Flag", "#ff9100", "Qullamaggie's favourite",
             "A strong upward move (the pole) followed by a tight sideways or slightly downward consolidation (the flag) with declining volume.",
             ["Stock moves up 15-30%+ in 2-3 weeks (the pole)","Consolidates 5-10 days in a tight range (the flag)","Volume drops during the flag","Flag channel slopes slightly down or is flat","Breakout above flag on high volume ← entry"],
             "Enter on breakout above the top of the flag. Stop below the bottom of the flag. Target = flag pole length added to breakout.",
             "Works best in strongly trending markets. Fails in choppy markets."),
            ("Flat Base", "#2979ff", "O'Neil CANSLIM pattern",
             "Stock consolidates in a tight 5-10% range for 3-6 weeks near its highs. One of the most reliable bases.",
             ["Stock near 52W highs","Range of last 20 days < 8%","Volume declining during base","EMAs all bullish below price","Duration: 3-8 weeks"],
             "Enter on breakout above the top of the flat base on 1.5x+ volume. Stop below the bottom of the base.",
             "The tighter the base, the more powerful the breakout. Less than 5% range = exceptional."),
            ("Ascending Triangle", "#aa00ff", "Classic breakout pattern",
             "Flat resistance at the top (sellers at a price) with higher lows at the bottom (buyers getting more aggressive). Tension builds until breakout.",
             ["Flat highs — multiple touches of same resistance","Rising lows — each pullback is shallower","Volume declining into apex","Breakout expected to the upside","Pattern usually 3-8 weeks"],
             "Enter on breakout above flat resistance on volume. Stop below last higher low.",
             "The more touches of resistance, the stronger the eventual breakout."),
            ("EMA20 Pullback", "#00bcd4", "Minervini's low-risk continuation entry",
             "In a confirmed Stage 2 uptrend, price pulls back to the 20 EMA and bounces. This is the lowest-risk entry in a trending stock.",
             ["Stock in clear Stage 2 uptrend (all EMAs bullish)","Price pulls back to touch or come within 2% of EMA20","Volume dries up during pullback","RSI drops to 40-50 range","A single bullish candle forms at EMA20 ← entry signal"],
             "Enter on the first green candle at EMA20. Stop 1% below EMA20. This is your tightest possible stop in a trending stock.",
             "This is Qullamaggie's primary entry method. Look for this setup in Tier 3 scanner results."),
            ("Second Leg / Multi-Leg", "#00c853", "Highest conviction trade",
             "After a big first move and tight base, the stock launches into a second (or third) leg up. These moves are often larger than the first.",
             ["Stock made a 30-80%+ first move","Pulled back only 15-30% (tight = institutional)","Volume dried up during base","Stock breaking out of the base again","MACD staying positive throughout"],
             "Enter at the breakout from the base between legs. Stop below the base low. These setups have the highest success rate because they prove institutional commitment.",
             "DATAPATTNS, HAL, BEL in 2023-24 were classic multi-leg momentum stocks."),
        ]

        for name, col, sub, desc, signals, entry, note in patterns:
            with st.expander(f"**{name}** — {sub}"):
                st.markdown(f"<p style='color:#7b8fba;'>{desc}</p>", unsafe_allow_html=True)
                st.markdown("**What to look for:**")
                for s in signals:
                    st.markdown(f"- {s}")
                st.markdown(f"**Entry & Stop:** {entry}")
                st.markdown(f"<div style='background:#0d1b2e;border:1px solid {col}30;border-radius:6px;padding:10px;margin-top:8px;color:#7b8fba;font-size:12px;'><strong style='color:{col};'>💡 Note:</strong> {note}</div>", unsafe_allow_html=True)

    # ── TAB 3: CHARTINK SCANNERS ──────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 📡 Chartink Scanners — Complete Guide")
        st.markdown("<p style='color:#7b8fba;'>Each scanner explained in detail — what it finds, why each condition is there, and exactly how to use the results.</p>", unsafe_allow_html=True)

        for name, data in SCANNERS.items():
            col = data["color"]
            with st.expander(f"**{name}** — Priority: {data['priority']}"):
                st.markdown(f"""
                <div style="background:#0d1b2e;border:1px solid {col}30;border-radius:8px;padding:14px;margin-bottom:12px;">
                  <div style="color:{col};font-size:12px;font-weight:700;margin-bottom:6px;">WHAT THIS FINDS</div>
                  <div style="color:#7b8fba;font-size:13px;">{data['what']}</div>
                  <div style="color:#e0e8ff;font-size:12px;margin-top:10px;font-weight:600;">WHY IT WORKS</div>
                  <div style="color:#7b8fba;font-size:13px;margin-top:4px;">{data['why']}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Each condition explained:**")
                for cname, ccode, cexpl in data["conditions"]:
                    st.markdown(f"""
                    <div style="background:#060e1c;border:1px solid #1a2744;border-radius:6px;padding:10px;margin-bottom:6px;">
                      <div style="display:flex;gap:10px;align-items:flex-start;">
                        <div style="min-width:140px;color:{col};font-size:11px;font-weight:700;">{cname}</div>
                        <div>
                          <div style="color:#a5d6a7;font-family:monospace;font-size:11px;margin-bottom:4px;">{ccode}</div>
                          <div style="color:#7b8fba;font-size:12px;">{cexpl}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("**Chartink Code:**")
                st.code(data["code"], language="text")
                st.markdown(f"""
                <div style="background:#0d1b2e;border:1px solid {col}30;border-radius:8px;padding:12px;margin-top:8px;">
                  <div style="color:#5c7099;font-size:10px;font-weight:600;margin-bottom:4px;">WHEN TO RUN</div>
                  <div style="color:#7b8fba;font-size:12px;">{data['when']}</div>
                  <div style="color:#5c7099;font-size:10px;font-weight:600;margin-top:8px;margin-bottom:4px;">ACTION ON RESULTS</div>
                  <div style="color:{col};font-size:12px;font-weight:600;">{data['action']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 4: SYSTEM RULES ───────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📖 Elite Swing Trading System Rules")

        rules = [
            ("🎯 The #1 Rule", "#00c853", [
                "**No trade is the best trade** when conditions are not right.",
                "Never force a trade just to be in the market.",
                "Capital preservation comes before everything else.",
                "One bad trade can wipe out 10 good trades.",
            ]),
            ("📊 Trade Quality Standards", "#2979ff", [
                "Only trade setups scoring **80+** (Strong Setup or Elite Setup).",
                "Minimum **3:1 reward-to-risk ratio** — no exceptions.",
                "Maximum **6% stop loss** — wider than 6% = skip the trade.",
                "Ideal stop loss: **2-5%** from entry.",
                "If you're not sure, the answer is NO.",
            ]),
            ("💰 Position Sizing Rules", "#ff9100", [
                "Never risk more than **1% of capital** on a single trade.",
                "Maximum **25% of capital** in any single stock.",
                "Never more than **5 simultaneous open positions**.",
                "Maximum **5% total portfolio risk** at any time.",
                "On high-VIX or expiry days: **0.5% risk per trade** (half size).",
            ]),
            ("🚫 Hard Rules — Never Break", "#f44336", [
                "**Never average down.** If a stock falls to your stop, exit. Period.",
                "**Never widen stop losses.** Set it and respect it.",
                "**Never hold through earnings** on a swing trade.",
                "**No trades in first 15 minutes** (9:15-9:30 AM IST) — too volatile.",
                "**No new entries after 3:15 PM IST** — closing auction distorts prices.",
                "**No revenge trades** after a loss. Step away for 15 minutes.",
                "**No trades on broadly red market days.**",
            ]),
            ("✅ Market Filter — Before ANY Trade", "#00c853", [
                "Check Nifty: above 50 EMA? Above 200 EMA?",
                "Check Bank Nifty: confirming or diverging?",
                "Check VIX: below 15 = normal, 15-20 = caution, above 20 = no new breakout entries.",
                "Check sector: is the sector in uptrend?",
                "If 2+ of these are negative → reduce size or skip entirely.",
            ]),
            ("📅 Daily Routine", "#90caf9", [
                "**Pre-market (9 AM):** Check Nifty/Bank Nifty direction, set GTT orders for watchlist.",
                "**9:15-9:30 AM:** Watch only. No trades.",
                "**9:30-11 AM:** Primary execution window.",
                "**11 AM-2:30 PM:** Low conviction period. Avoid new entries.",
                "**2:30-3:15 PM:** Monitor existing positions, trail stops.",
                "**After 4 PM:** Run Chartink scanners, build next day watchlist, update journal.",
            ]),
        ]

        for title, col, points in rules:
            with st.expander(f"**{title}**"):
                for pt in points:
                    st.markdown(f"<div style='padding:6px 0;border-bottom:1px solid #1a2744;color:#7b8fba;font-size:13px;'>{pt}</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:20px;padding:10px 14px;background:#0d1b2e;border:1px solid #1a2744;border-radius:8px;color:#3d5070;font-size:10px;line-height:1.6;">
    Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day. Always verify before trading. Past performance does not guarantee future returns.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
