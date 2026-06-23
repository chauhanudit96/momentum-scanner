import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Elite Momentum Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
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
    .stTabs [data-baseweb="tab"] { color: #7b8fba !important; }
    .stTabs [aria-selected="true"] { color: #e0e8ff !important; border-bottom-color: #2979ff !important; }
    .stSelectbox label, .stTextInput label, .stNumberInput label { color: #7b8fba !important; }
    .stExpander { background: #0d1b2e !important; border: 1px solid #1a2744 !important; border-radius: 8px !important; }
    div[data-testid="stMetricValue"] { color: #e0e8ff !important; }
    .stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─── POPULAR NSE STOCKS ───────────────────────────────────────────────────────
POPULAR = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "TITAN","WIPRO","ULTRACEMCO","NESTLEIND","SUNPHARMA","HCLTECH","TECHM",
    "POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP","BAJAJFINSV",
    "EICHERMOT","HEROMOTOCO","M&M","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL",
    "DATAPATTNS","LALPATHLAB","METROPOLIS","AKUMS","MARKSANS","SURYODAY",
    "INDSWFTLAB","ZEEL","THYROCARE","KAYNES","DIXON","AMBER",
]

# ─── DATA FETCH ───────────────────────────────────────────────────────────────
def fetch_stock_data(symbol: str):
    for suffix in [".NS", ".BO"]:
        try:
            tk = yf.Ticker(symbol + suffix)
            df = tk.history(period="2y", interval="1d", auto_adjust=True)
            if df is not None and len(df) > 60:
                df = df.dropna(subset=["Close"])
                return df, symbol + suffix
        except Exception:
            continue
    return None, None

def fetch_nifty_data():
    try:
        tk = yf.Ticker("^NSEI")
        df = tk.history(period="1y", interval="1d", auto_adjust=True)
        if df is not None and len(df) > 50:
            return df.dropna(subset=["Close"])
    except Exception:
        pass
    return None

# ─── INDICATOR CALCULATIONS ───────────────────────────────────────────────────
def calc_ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False).mean()

def calc_sma(s: pd.Series, p: int) -> pd.Series:
    return s.rolling(window=p).mean()

def calc_rsi(s: pd.Series, p: int = 14) -> pd.Series:
    delta = s.diff()
    gain  = delta.clip(lower=0).rolling(p).mean()
    loss  = (-delta.clip(upper=0)).rolling(p).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(s: pd.Series):
    ema12   = s.ewm(span=12, adjust=False).mean()
    ema26   = s.ewm(span=26, adjust=False).mean()
    macd    = ema12 - ema26
    signal  = macd.ewm(span=9, adjust=False).mean()
    hist    = macd - signal
    return macd, signal, hist

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA10"]   = calc_ema(df["Close"], 10)
    df["EMA20"]   = calc_ema(df["Close"], 20)
    df["EMA50"]   = calc_ema(df["Close"], 50)
    df["EMA200"]  = calc_ema(df["Close"], 200)
    df["SMA50V"]  = calc_sma(df["Volume"], 50)
    df["SMA10V"]  = calc_sma(df["Volume"], 10)
    df["VolRatio"]= df["Volume"] / df["SMA50V"]
    df["High52W"] = df["High"].rolling(252, min_periods=100).max()
    df["RSI"]     = calc_rsi(df["Close"])
    macd, signal, hist = calc_macd(df["Close"])
    df["MACD"]    = macd
    df["Signal"]  = signal
    df["MACDHist"]= hist
    df["ATR"]     = (df["High"] - df["Low"]).rolling(14).mean()
    return df

def compute_returns(df, nifty_df=None):
    p = df["Close"].iloc[-1]
    r6m = r12m = rs_vs_nifty = None
    if len(df) >= 126:
        r6m = ((p - df["Close"].iloc[-126]) / df["Close"].iloc[-126]) * 100
    if len(df) >= 252:
        r12m = ((p - df["Close"].iloc[-252]) / df["Close"].iloc[-252]) * 100
    if nifty_df is not None and len(nifty_df) >= 126:
        nifty_now  = nifty_df["Close"].iloc[-1]
        nifty_6m   = nifty_df["Close"].iloc[-126]
        nifty_r6m  = ((nifty_now - nifty_6m) / nifty_6m) * 100
        rs_vs_nifty = (r6m - nifty_r6m) if r6m is not None else None
    return r6m, r12m, rs_vs_nifty

# ─── MARKET REGIME ────────────────────────────────────────────────────────────
def get_market_regime(nifty_df):
    if nifty_df is None or len(nifty_df) < 50:
        return "UNKNOWN", 0, "#7b8fba"
    n = enrich(nifty_df)
    price  = n["Close"].iloc[-1]
    e50    = n["EMA50"].iloc[-1]
    e200   = n["EMA200"].iloc[-1]
    if price < e200:
        return "BEARISH — Capital preservation mode. Avoid new longs.", 20, "#f44336"
    elif price < e50:
        return "CAUTION — Market below EMA50. Half size only.", 10, "#ff9100"
    else:
        return "HEALTHY — Full scoring active.", 0, "#00c853"

# ─── LIQUIDITY GATE ───────────────────────────────────────────────────────────
def liquidity_gate(df):
    latest   = df.iloc[-1]
    price    = float(latest["Close"])
    avg_vol  = df["Volume"].tail(50).mean()
    turnover = avg_vol * price  # in ₹
    return turnover, turnover >= 25_00_00_000  # ₹25 Crore

# ─── STOP LOSS CALCULATOR ─────────────────────────────────────────────────────
def compute_smart_sl(df, price):
    """
    Smart stop loss logic:
    1. First choice: 1% below EMA10 (tight, for breakouts)
    2. Second choice: 1% below EMA20 (for pullback entries)
    3. Third choice: 2% below EMA50 (wider, for base breakouts)
    4. Hard cap: never more than 6%
    Returns the tightest viable SL within 6%
    """
    latest = df.iloc[-1]
    e10    = float(latest["EMA10"])
    e20    = float(latest["EMA20"])
    e50    = float(latest["EMA50"])
    atr    = float(latest["ATR"]) if not np.isnan(latest["ATR"]) else price * 0.02

    candidates = [
        ("1% below EMA10", e10 * 0.99),
        ("1% below EMA20", e20 * 0.99),
        ("2% below EMA50", e50 * 0.98),
        ("2× ATR below price", price - (2 * atr)),
    ]

    best_sl   = None
    best_label= ""
    for label, sl_price in candidates:
        sl_pct = ((price - sl_price) / price) * 100
        if 1.0 <= sl_pct <= 6.0:
            best_sl    = sl_price
            best_label = label
            break  # take the tightest first

    if best_sl is None:
        return None, None, None, False

    sl_pct = ((price - best_sl) / price) * 100
    return best_sl, sl_pct, best_label, True

# ─── ENTRY LOGIC ─────────────────────────────────────────────────────────────
def compute_entry_logic(df, price):
    """
    Determine entry type and price based on price vs EMAs:
    - Breakout entry: price at or just above 52W high
    - EMA20 pullback entry: price pulled back to EMA20 in uptrend
    - EMA50 base entry: price bouncing from EMA50
    - Current price entry: price already above all EMAs, enter at market
    Returns entry type, aggressive entry, conservative entry, and explanation
    """
    latest   = df.iloc[-1]
    e10      = float(latest["EMA10"])
    e20      = float(latest["EMA20"])
    e50      = float(latest["EMA50"])
    e200     = float(latest["EMA200"])
    h52w     = float(latest["High52W"]) if not np.isnan(latest["High52W"]) else price
    rsi      = float(latest["RSI"]) if not np.isnan(latest["RSI"]) else 50
    vol_r    = float(latest["VolRatio"]) if not np.isnan(latest["VolRatio"]) else 1

    pct_from_high = ((h52w - price) / h52w) * 100 if h52w > 0 else 100

    # Case 1: Breakout — price at or above 52W high with volume
    if pct_from_high <= 1.0 and vol_r >= 1.5:
        return {
            "type": "BREAKOUT",
            "aggressive": price,
            "conservative": h52w * 1.005,
            "retest": h52w * 0.99,
            "explanation": (
                f"Stock is breaking out above its 52W high of ₹{h52w:.1f} on strong volume ({vol_r:.1f}x avg). "
                f"**Aggressive entry:** Buy NOW at ₹{price:.1f} as breakout is happening. "
                f"**Conservative entry:** Wait for daily close above ₹{h52w*1.005:.1f} to confirm. "
                f"**Retest entry:** If price pulls back to ₹{h52w*0.99:.1f} (old resistance now support), that's the safest entry."
            )
        }

    # Case 2: Near breakout — within 3% of 52W high, coiling
    elif pct_from_high <= 3.0:
        return {
            "type": "PRE-BREAKOUT",
            "aggressive": price,
            "conservative": h52w * 1.002,
            "retest": e20 * 1.005,
            "explanation": (
                f"Stock is {pct_from_high:.1f}% below its 52W high of ₹{h52w:.1f} — coiling for breakout. "
                f"**Aggressive entry:** Buy NOW at ₹{price:.1f} in anticipation. "
                f"**Conservative entry (recommended):** Wait for breakout above ₹{h52w:.1f} with volume >1.5x avg. "
                f"**Pullback entry:** If market dips, ₹{e20*1.005:.1f} (EMA20 zone) is an ideal add point."
            )
        }

    # Case 3: EMA20 pullback in strong uptrend
    elif price > e50 > e200 and abs(price - e20) / price < 0.03:
        return {
            "type": "EMA20 PULLBACK",
            "aggressive": e20 * 1.005,
            "conservative": e20 * 1.01,
            "retest": e20 * 0.99,
            "explanation": (
                f"Stock is in Stage 2 uptrend and has pulled back to its 20 EMA (₹{e20:.1f}). "
                f"This is a low-risk, high-probability entry point. "
                f"**Aggressive entry:** ₹{e20*1.005:.1f} — as soon as price reclaims EMA20. "
                f"**Conservative entry:** ₹{e20*1.01:.1f} — once price is clearly holding above EMA20 for 1 candle. "
                f"**Stop:** Just below EMA20 at ₹{e20*0.99:.1f}. "
                f"Wait for a green candle on EMA20 with volume pick-up before entering."
            )
        }

    # Case 4: EMA50 bounce
    elif price > e200 and abs(price - e50) / price < 0.04:
        return {
            "type": "EMA50 BOUNCE",
            "aggressive": e50 * 1.01,
            "conservative": e50 * 1.02,
            "retest": e50 * 0.99,
            "explanation": (
                f"Stock has pulled back to its 50 EMA (₹{e50:.1f}) in a longer-term uptrend. "
                f"This is a base-building entry — higher risk than EMA20 pullback but still valid. "
                f"**Aggressive entry:** ₹{e50*1.01:.1f} — once price bounces off EMA50. "
                f"**Conservative entry:** ₹{e50*1.02:.1f} — after a confirmed close above EMA50. "
                f"**Critical:** Volume must expand on the bounce candle. Low-volume bounces often fail."
            )
        }

    # Case 5: Momentum continuation — price above all EMAs
    elif price > e20 > e50 > e200:
        return {
            "type": "MOMENTUM CONTINUATION",
            "aggressive": price,
            "conservative": e10 * 1.005,
            "retest": e20 * 1.005,
            "explanation": (
                f"Stock is in a strong momentum phase above all EMAs. "
                f"Best practice is to wait for a shallow pullback rather than chasing. "
                f"**Aggressive entry:** ₹{price:.1f} — buy now if volume confirms and RSI is not overbought. "
                f"**Conservative entry (recommended):** ₹{e10*1.005:.1f} — wait for a 1-2 day dip to EMA10 (₹{e10:.1f}). "
                f"**Ideal entry:** ₹{e20*1.005:.1f} — if stock pulls back to EMA20, that's the best risk-reward entry."
            )
        }

    # Default
    else:
        return {
            "type": "WAIT",
            "aggressive": price,
            "conservative": e20 * 1.01,
            "retest": e50 * 1.01,
            "explanation": (
                f"No clean entry setup right now. Price is between EMAs without a clear trigger. "
                f"**Do not force an entry.** Wait for price to either: "
                f"(a) Break above ₹{h52w:.1f} on volume, or "
                f"(b) Pull back cleanly to EMA20 (₹{e20:.1f}) or EMA50 (₹{e50:.1f}) with drying volume."
            )
        }

# ─── TARGETS ─────────────────────────────────────────────────────────────────
def compute_targets(price, sl_price, df):
    """
    Target logic based on R-multiples:
    T1 = 1.5R (book 30% — take some off the table)
    T2 = 3R   (book 30% — this is your minimum R:R target)
    T3 = 5R   (trail remaining 40% — let winners run)
    Also checks against 52W high as a natural resistance level.
    """
    if sl_price is None:
        return None, None, None, None

    risk_per_share = price - sl_price
    r = risk_per_share

    t1 = price + (1.5 * r)
    t2 = price + (3.0 * r)
    t3 = price + (5.0 * r)

    latest  = df.iloc[-1]
    h52w    = float(latest["High52W"]) if not np.isnan(latest["High52W"]) else price * 1.15
    rr      = (t2 - price) / r  # should be 3.0

    return t1, t2, t3, rr

# ─── SINGLE DAY SPIKE CHECK ──────────────────────────────────────────────────
def spike_penalty(df):
    if len(df) < 2:
        return 0, 0.0
    price  = float(df["Close"].iloc[-1])
    prev   = float(df["Close"].iloc[-2])
    move   = ((price - prev) / prev) * 100
    if move >= 10:
        return -20, move
    elif move >= 8:
        return -10, move
    elif move >= 5:
        return -5, move
    return 0, move

# ─── MAIN SCORER ─────────────────────────────────────────────────────────────
def score_stock(df, r6m, r12m, rs_nifty, regime_penalty):
    latest    = df.iloc[-1]
    price     = float(latest["Close"])
    e20       = float(latest["EMA20"])
    e50       = float(latest["EMA50"])
    e200      = float(latest["EMA200"])
    h52w      = float(latest["High52W"]) if not np.isnan(latest["High52W"]) else price
    vol_ratio = float(latest["VolRatio"]) if not np.isnan(latest["VolRatio"]) else None
    rsi       = float(latest["RSI"])     if not np.isnan(latest["RSI"])     else 50
    macd_v    = float(latest["MACD"])    if not np.isnan(latest["MACD"])    else 0
    macd_s    = float(latest["Signal"])  if not np.isnan(latest["Signal"])  else 0
    macd_h    = float(latest["MACDHist"])if not np.isnan(latest["MACDHist"])else 0

    scores = {}
    flags  = []

    # 1. EMA STACK — 20pts
    if price > e20 > e50 > e200:
        scores["ema"] = 20
        flags.append(("bull", "Full EMA stack bullish (Price > 20 > 50 > 200) — Stage 2 confirmed ✓"))
    elif e20 > e50 > e200 and price > e50:
        scores["ema"] = 14
        flags.append(("warn", "EMA stack aligned but price below EMA20 — wait for reclaim"))
    elif e20 > e50 or e50 > e200:
        scores["ema"] = 7
        flags.append(("warn", "Partial EMA alignment — Stage 2 developing"))
    else:
        scores["ema"] = 0
        flags.append(("bear", "EMA stack bearish — not Stage 2, avoid entirely"))

    # 2. 52W HIGH POSITION — 15pts
    pct_from_h = ((h52w - price) / h52w * 100) if h52w > 0 else 100
    if pct_from_h <= 0:
        scores["h52"] = 15; flags.append(("bull", f"AT or ABOVE 52W high — breakout confirmed ✓"))
    elif pct_from_h <= 1:
        scores["h52"] = 13; flags.append(("bull", f"{pct_from_h:.1f}% from 52W high — imminent breakout ✓"))
    elif pct_from_h <= 3:
        scores["h52"] = 11; flags.append(("bull", f"{pct_from_h:.1f}% from 52W high — launchpad zone"))
    elif pct_from_h <= 7:
        scores["h52"] = 7;  flags.append(("warn", f"{pct_from_h:.1f}% from 52W high — in base"))
    elif pct_from_h <= 15:
        scores["h52"] = 3;  flags.append(("warn", f"{pct_from_h:.1f}% from 52W high — extended base"))
    else:
        scores["h52"] = 0;  flags.append(("bear", f"{pct_from_h:.1f}% from 52W high — too far from breakout"))

    # 3. VOLUME — 15pts (with spike penalty applied separately)
    if vol_ratio is not None:
        if   vol_ratio >= 3.0: scores["vol"]=15; flags.append(("bull",f"Volume {vol_ratio:.1f}x avg — exceptional institutional surge ✓"))
        elif vol_ratio >= 2.0: scores["vol"]=12; flags.append(("bull",f"Volume {vol_ratio:.1f}x avg — strong institutional buying"))
        elif vol_ratio >= 1.5: scores["vol"]=10; flags.append(("bull",f"Volume {vol_ratio:.1f}x avg — confirmed breakout volume ✓"))
        elif vol_ratio >= 1.0: scores["vol"]=6;  flags.append(("warn",f"Volume {vol_ratio:.1f}x avg — average, needs conviction"))
        else:                  scores["vol"]=2;  flags.append(("warn",f"Volume drying up ({vol_ratio:.1f}x) — VCP forming"))
    else:
        scores["vol"] = 7

    # 4. MACD — 15pts
    if macd_v > 0 and macd_h > 0:
        scores["macd"] = 15; flags.append(("bull", f"MACD positive & histogram expanding — momentum accelerating ✓"))
    elif macd_v > 0 and macd_h <= 0:
        scores["macd"] = 10; flags.append(("warn", f"MACD positive but histogram contracting — momentum slowing"))
    elif -0.5 < macd_v <= 0:
        scores["macd"] = 5;  flags.append(("warn", f"MACD near zero — watch for crossover"))
    else:
        scores["macd"] = 0;  flags.append(("bear", f"MACD negative — bearish momentum, strong avoid"))

    # 5. RSI — 10pts
    if 50 <= rsi <= 65:
        scores["rsi"] = 10; flags.append(("bull", f"RSI {rsi:.0f} — sweet spot, room to run ✓"))
    elif 65 < rsi <= 70:
        scores["rsi"] = 7;  flags.append(("warn", f"RSI {rsi:.0f} — approaching overbought, caution"))
    elif 45 <= rsi < 50:
        scores["rsi"] = 5;  flags.append(("warn", f"RSI {rsi:.0f} — recovering, watch for momentum"))
    elif 70 < rsi <= 80:
        scores["rsi"] = 2;  flags.append(("warn", f"RSI {rsi:.0f} — overbought, high chase risk"))
    else:
        scores["rsi"] = 0;  flags.append(("bear", f"RSI {rsi:.0f} — {'extremely overbought' if rsi>80 else 'downtrend territory'}, avoid"))

    # 6. 6M RETURN — 10pts
    if r6m is not None:
        if   r6m >= 50: scores["r6"]=10; flags.append(("bull",f"6M: +{r6m:.1f}% — exceptional leader ✓"))
        elif r6m >= 35: scores["r6"]=8;  flags.append(("bull",f"6M: +{r6m:.1f}% — strong outperformer"))
        elif r6m >= 20: scores["r6"]=6;  flags.append(("bull",f"6M: +{r6m:.1f}% — above average"))
        elif r6m >= 10: scores["r6"]=4;  flags.append(("warn",f"6M: +{r6m:.1f}% — moderate"))
        elif r6m >= 0:  scores["r6"]=2;  flags.append(("warn",f"6M: +{r6m:.1f}% — weak"))
        else:           scores["r6"]=0;  flags.append(("bear",f"6M: {r6m:.1f}% — negative, avoid"))
    else:
        scores["r6"] = 5

    # 7. 12M RETURN — 10pts
    if r12m is not None:
        if   r12m >= 60: scores["r12"]=10; flags.append(("bull",f"12M: +{r12m:.1f}% — multi-bagger ✓"))
        elif r12m >= 40: scores["r12"]=8;  flags.append(("bull",f"12M: +{r12m:.1f}% — strong annual"))
        elif r12m >= 25: scores["r12"]=6;  flags.append(("bull",f"12M: +{r12m:.1f}% — solid annual"))
        elif r12m >= 10: scores["r12"]=4;  flags.append(("warn",f"12M: +{r12m:.1f}% — modest"))
        elif r12m >= 0:  scores["r12"]=2;  flags.append(("warn",f"12M: +{r12m:.1f}% — weak"))
        else:            scores["r12"]=0;  flags.append(("bear",f"12M: {r12m:.1f}% — negative"))
    else:
        scores["r12"] = 5

    # 8. RELATIVE STRENGTH vs NIFTY — 10pts
    if rs_nifty is not None:
        if   rs_nifty >= 20: scores["rs"]=10; flags.append(("bull",f"RS vs Nifty: +{rs_nifty:.1f}% — massively outperforming ✓"))
        elif rs_nifty >= 10: scores["rs"]=8;  flags.append(("bull",f"RS vs Nifty: +{rs_nifty:.1f}% — outperforming"))
        elif rs_nifty >= 5:  scores["rs"]=6;  flags.append(("bull",f"RS vs Nifty: +{rs_nifty:.1f}% — slightly ahead"))
        elif rs_nifty >= 0:  scores["rs"]=4;  flags.append(("warn",f"RS vs Nifty: +{rs_nifty:.1f}% — matching market"))
        else:                scores["rs"]=0;  flags.append(("bear",f"RS vs Nifty: {rs_nifty:.1f}% — underperforming market, avoid"))
    else:
        scores["rs"] = 5

    # 9. LIQUIDITY — 5pts (binary gate handled before scoring)
    scores["liq"] = 5

    # Raw total (max 110 → normalize to 100)
    raw = sum(scores.values())
    normalized = int((raw / 110) * 100)

    # Penalties
    sp, today_move = spike_penalty(df)
    if sp < 0:
        flags.append(("bear", f"⚠️ Single-day spike: +{today_move:.1f}% today — chasing risk, penalty applied"))

    final_score = max(0, normalized + sp - regime_penalty)

    # Verdict
    if final_score >= 90:   verdict = "ELITE SETUP"
    elif final_score >= 80: verdict = "STRONG SETUP"
    elif final_score >= 70: verdict = "TRADABLE"
    else:                   verdict = "AVOID"

    return {
        "score": final_score,
        "raw_score": normalized,
        "spike_penalty": sp,
        "regime_penalty": regime_penalty,
        "today_move": today_move,
        "verdict": verdict,
        "scores": scores,
        "flags": flags,
        "pct_from_high": pct_from_h,
        "rsi": rsi,
        "macd": macd_v,
        "macd_hist": macd_h,
        "vol_ratio": vol_ratio,
    }

# ─── HTML HELPERS ────────────────────────────────────────────────────────────
VC = {"ELITE SETUP":"#00c853","STRONG SETUP":"#ff9100","TRADABLE":"#2979ff","AVOID":"#f44336"}
AC = {"BUY BREAKOUT":"#00c853","WATCH FOR PULLBACK":"#ff9100","WAIT — NOT YET":"#2979ff","AVOID":"#f44336"}

def bar_html(label, sc, mx):
    pct = min((sc / mx) * 100, 100)
    col = "#00c853" if pct >= 75 else "#ff9100" if pct >= 50 else "#f44336"
    chk = "✓" if pct >= 75 else "◆" if pct >= 50 else "✗"
    cc  = col
    return f"""<div style="margin-bottom:9px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="color:#7b8fba;font-size:12px;">{label}</span>
        <span style="color:{cc};font-size:12px;font-weight:700;">{chk} {sc}/{mx}</span>
      </div>
      <div style="height:5px;background:#1a2744;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:{pct}%;background:{col};border-radius:3px;"></div>
      </div></div>"""

def flag_html(flags):
    ic = {"bull":"▲","warn":"◆","bear":"▼"}
    cl = {"bull":"#00c853","warn":"#ff9100","bear":"#f44336"}
    h  = ""
    for t, msg in flags:
        h += f"""<div style="display:flex;gap:8px;padding:7px 11px;background:#060e1c;border:1px solid {cl[t]}20;border-radius:6px;margin-bottom:5px;">
          <span style="color:{cl[t]};font-weight:700;min-width:12px;">{ic[t]}</span>
          <span style="color:#7b8fba;font-size:12px;line-height:1.5;">{msg}</span></div>"""
    return h

def tile(label, value, color="#e0e8ff", sub=""):
    s = f"<div style='color:#5c7099;font-size:9px;font-weight:600;letter-spacing:0.5px;margin-bottom:3px;'>{label}</div>"
    s += f"<div style='color:{color};font-size:14px;font-weight:700;'>{value}</div>"
    if sub: s += f"<div style='color:#5c7099;font-size:10px;margin-top:2px;'>{sub}</div>"
    return f"<div style='background:#060e1c;border:1px solid {color}25;border-radius:8px;padding:10px 12px;'>{s}</div>"

# ─── CHARTINK SCANNERS ───────────────────────────────────────────────────────
SCANNERS = {
    "🟢 Tier 1 — Fresh 52W Breakout": "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
    "🟠 Tier 2 — Near 52W High (<3%)": "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
    "🔵 Tier 3 — Momentum Continuation": "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
    "🟣 Tier 4 — VCP / Tight Base": "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
}

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div style="width:42px;height:42px;background:linear-gradient(135deg,#1565c0,#0d47a1);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;">📈</div>
      <div>
        <div style="font-size:18px;font-weight:800;color:#e0e8ff;">NSE ELITE MOMENTUM SCANNER</div>
        <div style="font-size:11px;color:#5c7099;">Minervini × O'Neil × Weinstein · 7-Factor Scoring · Live NSE Data</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MARKET REGIME BANNER ─────────────────────────────────────────────────
    with st.spinner("Checking Nifty market regime..."):
        nifty_df = fetch_nifty_data()
    regime_msg, regime_penalty, regime_col = get_market_regime(nifty_df)

    st.markdown(f"""
    <div style="background:#0d1b2e;border:2px solid {regime_col}50;border-radius:10px;padding:12px 18px;margin-bottom:20px;display:flex;align-items:center;gap:12px;">
      <div style="width:12px;height:12px;border-radius:50%;background:{regime_col};flex-shrink:0;"></div>
      <div>
        <span style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;">MARKET REGIME — NIFTY 50</span><br>
        <span style="color:{regime_col};font-size:14px;font-weight:700;">{regime_msg}</span>
        {f'<span style="color:#5c7099;font-size:11px;"> · Score penalty: -{regime_penalty} pts</span>' if regime_penalty > 0 else ''}
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["⚡ Live Stock Scorer", "📡 Chartink Scanners", "📖 Scoring Logic"])

    # ── TAB 1: SCORER ────────────────────────────────────────────────────────
    with tab1:
        col_in, col_out = st.columns([1, 1.8], gap="large")

        with col_in:
            st.markdown("### 🔍 Stock Lookup")
            symbol = st.text_input("Type NSE Symbol", placeholder="TCS, RELIANCE, DATAPATTNS...").upper().strip()
            pick   = st.selectbox("Or pick from list", [""] + sorted(POPULAR))
            if pick: symbol = pick

            capital = st.number_input("Trading Capital (₹)", min_value=100000, max_value=10000000,
                                       value=500000, step=50000, format="%d")
            risk_pct = st.slider("Risk per trade (%)", min_value=0.5, max_value=2.0, value=1.0, step=0.25)

            fetch = st.button("⚡ Fetch & Score", use_container_width=True)

            st.markdown("""
            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:8px;padding:12px;margin-top:12px;">
              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">SCORING FACTORS</div>
              <div style="color:#7b8fba;font-size:11px;line-height:1.9;">
                EMA Stack .......... 20 pts<br>
                52W High Pos ....... 15 pts<br>
                Volume ............. 15 pts<br>
                MACD ............... 15 pts  🆕<br>
                RSI ................ 10 pts  🆕<br>
                6M Return .......... 10 pts<br>
                12M Return ......... 10 pts<br>
                RS vs Nifty ........ 10 pts  🆕<br>
                Liquidity ........... 5 pts<br>
                <span style="color:#f44336;">Spike Penalty ...... up to -20</span><br>
                <span style="color:#f44336;">Regime Penalty ..... up to -20</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_out:
            if fetch and symbol:
                with st.spinner(f"Fetching {symbol} from NSE..."):
                    df, used_ticker = fetch_stock_data(symbol)

                if df is None:
                    st.error(f"❌ Could not fetch **{symbol}**. Check symbol name and try again.")
                else:
                    df = enrich(df)
                    latest = df.iloc[-1]
                    prev   = df.iloc[-2]
                    price  = float(latest["Close"])

                    # ── LIQUIDITY GATE ──────────────────────────────────────
                    turnover, liq_ok = liquidity_gate(df)
                    if not liq_ok:
                        st.markdown(f"""
                        <div style="background:#1a0a0a;border:2px solid #f44336;border-radius:10px;padding:20px;text-align:center;">
                          <div style="font-size:28px;margin-bottom:8px;">🚫</div>
                          <div style="color:#f44336;font-size:18px;font-weight:800;">LIQUIDITY FAIL — NOT SCORED</div>
                          <div style="color:#7b8fba;font-size:13px;margin-top:8px;">
                            Avg daily turnover: ₹{turnover/1e7:.1f} Crore<br>
                            Minimum required: ₹25 Crore<br>
                            <span style="color:#f44336;">This stock does not meet the minimum liquidity threshold. Execution risk is too high.</span>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.stop()

                    # ── COMPUTE ─────────────────────────────────────────────
                    r6m, r12m, rs_nifty = compute_returns(df, nifty_df)
                    res  = score_stock(df, r6m, r12m, rs_nifty, regime_penalty)
                    sl, sl_pct, sl_label, sl_ok = compute_smart_sl(df, price)
                    entry_info = compute_entry_logic(df, price)
                    t1, t2, t3, rr = compute_targets(price, sl, df) if sl_ok else (None, None, None, None)

                    day_chg = ((price - float(prev["Close"])) / float(prev["Close"])) * 100
                    h52w    = float(latest["High52W"]) if not np.isnan(latest["High52W"]) else price
                    e10     = float(latest["EMA10"])
                    e20     = float(latest["EMA20"])
                    e50     = float(latest["EMA50"])
                    e200    = float(latest["EMA200"])

                    vc  = VC[res["verdict"]]
                    qty = int((capital * risk_pct / 100) / (price * (sl_pct / 100))) if sl_ok and sl_pct else 0
                    pos_val = qty * price
                    max_risk = capital * risk_pct / 100

                    # ── STOCK HEADER ────────────────────────────────────────
                    chg_col = "#00c853" if day_chg >= 0 else "#f44336"
                    st.markdown(f"""
                    <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                          <div style="color:#90caf9;font-size:11px;font-weight:600;letter-spacing:1px;">{used_ticker} · {df.index[-1].strftime('%d %b %Y')}</div>
                          <div style="color:#e0e8ff;font-size:28px;font-weight:900;margin-top:4px;">₹{price:,.2f}</div>
                          <div style="color:#5c7099;font-size:11px;margin-top:2px;">Turnover: ₹{turnover/1e7:.1f} Cr/day ✓</div>
                        </div>
                        <div style="text-align:right;">
                          <div style="color:{chg_col};font-size:18px;font-weight:700;">{'▲' if day_chg>=0 else '▼'} {abs(day_chg):.2f}%</div>
                          <div style="color:#5c7099;font-size:11px;">Today</div>
                          {f'<div style="color:#f44336;font-size:11px;font-weight:600;">⚠️ Spike detected</div>' if abs(res["today_move"])>=5 else ''}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── DATA TILES ──────────────────────────────────────────
                    c1,c2,c3,c4 = st.columns(4)
                    pct_h   = res["pct_from_high"]
                    ph_col  = "#00c853" if pct_h<=3 else "#ff9100" if pct_h<=10 else "#f44336"
                    ph_txt  = "ABOVE ✓" if pct_h<=0 else f"{pct_h:.1f}% below"
                    vr      = res["vol_ratio"]
                    vr_col  = "#00c853" if vr and vr>=1.5 else "#ff9100" if vr and vr>=1 else "#f44336"
                    rsi_col = "#00c853" if 50<=res["rsi"]<=65 else "#ff9100" if res["rsi"]<80 else "#f44336"
                    m_col   = "#00c853" if res["macd"]>0 and res["macd_hist"]>0 else "#ff9100" if res["macd"]>0 else "#f44336"

                    with c1: st.markdown(tile("52W HIGH", f"₹{h52w:,.1f}", ph_col, ph_txt), unsafe_allow_html=True)
                    with c2: st.markdown(tile("VOLUME RATIO", f"{vr:.1f}x" if vr else "—", vr_col), unsafe_allow_html=True)
                    with c3: st.markdown(tile("RSI (14)", f"{res['rsi']:.0f}", rsi_col), unsafe_allow_html=True)
                    with c4: st.markdown(tile("MACD", f"{'▲' if res['macd']>0 else '▼'} {res['macd']:.2f}", m_col), unsafe_allow_html=True)

                    c5,c6,c7,c8 = st.columns(4)
                    e20c = "#00c853" if price>e20 else "#f44336"
                    e50c = "#00c853" if e20>e50 else "#f44336"
                    e200c= "#00c853" if e50>e200 else "#f44336"
                    r6c  = "#00c853" if r6m and r6m>=20 else "#ff9100" if r6m and r6m>=0 else "#f44336"
                    with c5: st.markdown(tile("EMA 20", f"₹{e20:,.1f}", e20c, "✓ above" if price>e20 else "✗ below"), unsafe_allow_html=True)
                    with c6: st.markdown(tile("EMA 50", f"₹{e50:,.1f}", e50c, "✓ 20>50" if e20>e50 else "✗"), unsafe_allow_html=True)
                    with c7: st.markdown(tile("EMA 200", f"₹{e200:,.1f}", e200c, "✓ 50>200" if e50>e200 else "✗"), unsafe_allow_html=True)
                    with c8: st.markdown(tile("6M RETURN", f"+{r6m:.1f}%" if r6m and r6m>=0 else f"{r6m:.1f}%" if r6m else "—", r6c), unsafe_allow_html=True)

                    st.markdown("---")

                    # ── BIG SCORE ───────────────────────────────────────────
                    action_map = {"ELITE SETUP":"BUY BREAKOUT","STRONG SETUP":"STRONG BUY / WATCH","TRADABLE":"HALF SIZE ONLY","AVOID":"AVOID — NO TRADE"}
                    action = action_map.get(res["verdict"],"—")
                    ac_col = AC.get(action, vc)

                    st.markdown(f"""
                    <div style="background:#060e1c;border:2px solid {vc}50;border-radius:14px;padding:22px;text-align:center;margin-bottom:16px;">
                      <div style="font-size:68px;font-weight:900;color:{vc};line-height:1;">{res['score']}</div>
                      <div style="color:#5c7099;font-size:11px;margin-bottom:12px;">
                        OUT OF 100 &nbsp;·&nbsp; Raw: {res['raw_score']} &nbsp;
                        {f"· Spike: {res['spike_penalty']}" if res['spike_penalty']<0 else ""}
                        {f"· Regime: -{res['regime_penalty']}" if res['regime_penalty']>0 else ""}
                      </div>
                      <div style="display:inline-block;background:{vc}20;color:{vc};border:1px solid {vc}50;border-radius:8px;padding:6px 24px;font-size:15px;font-weight:800;letter-spacing:1px;">{res['verdict']}</div>
                      <div style="color:{vc};font-size:14px;font-weight:700;margin-top:12px;">→ {action}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if res["verdict"] == "AVOID":
                        st.markdown("""
                        <div style="background:#1a0808;border:1px solid #f4433650;border-radius:8px;padding:14px;text-align:center;margin-bottom:14px;">
                          <div style="color:#f44336;font-size:15px;font-weight:700;">🚫 NO TRADE IS THE BEST TRADE</div>
                          <div style="color:#7b8fba;font-size:12px;margin-top:6px;">This setup does not meet minimum quality standards. Preserve capital.</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # ── ENTRY SECTION ───────────────────────────────────
                        entry_type_col = {"BREAKOUT":"#00c853","PRE-BREAKOUT":"#ff9100","EMA20 PULLBACK":"#2979ff","EMA50 BOUNCE":"#aa00ff","MOMENTUM CONTINUATION":"#00bcd4","WAIT":"#f44336"}.get(entry_info["type"],"#7b8fba")

                        st.markdown(f"""
                        <div style="background:#0d1b2e;border:1px solid {entry_type_col}40;border-left:4px solid {entry_type_col};border-radius:10px;padding:16px;margin-bottom:14px;">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                            <span style="background:{entry_type_col}20;color:{entry_type_col};border:1px solid {entry_type_col}40;border-radius:4px;padding:2px 10px;font-size:10px;font-weight:800;letter-spacing:1px;">ENTRY TYPE: {entry_info['type']}</span>
                          </div>
                          <div style="color:#7b8fba;font-size:13px;line-height:1.7;">{entry_info['explanation']}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # ── SL CHECK ────────────────────────────────────────
                        if not sl_ok:
                            st.markdown("""
                            <div style="background:#1a0a0a;border:1px solid #f44336;border-radius:8px;padding:14px;margin-bottom:14px;">
                              <div style="color:#f44336;font-weight:700;">⚠️ STOP LOSS FAILS 6% RULE</div>
                              <div style="color:#7b8fba;font-size:12px;margin-top:6px;">No logical stop loss can be placed within 6%. Position too risky. Skip this trade.</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # ── TRADE LEVELS ────────────────────────────────
                            st.markdown(f"""
                            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;">
                              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:14px;">TRADE LEVELS — {entry_info['type']}</div>
                              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
                                <div style="background:#060e1c;border:1px solid #2979ff30;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">AGGRESSIVE ENTRY</div>
                                  <div style="color:#2979ff;font-size:15px;font-weight:700;">₹{entry_info['aggressive']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">Enter now / at market open</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #2979ff20;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">CONSERVATIVE ENTRY</div>
                                  <div style="color:#90caf9;font-size:15px;font-weight:700;">₹{entry_info['conservative']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">Wait for confirmation</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #f4433630;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">STOP LOSS ({sl_pct:.1f}%) · {sl_label}</div>
                                  <div style="color:#f44336;font-size:15px;font-weight:700;">₹{sl:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">GTT order — place immediately</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #1a2744;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">RETEST ENTRY</div>
                                  <div style="color:#7b8fba;font-size:15px;font-weight:700;">₹{entry_info['retest']:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">If price pulls back</div>
                                </div>
                              </div>
                              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
                                <div style="background:#060e1c;border:1px solid #ff910030;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">TARGET 1 — Book 30%</div>
                                  <div style="color:#ff9100;font-size:14px;font-weight:700;">₹{t1:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">+{((t1-price)/price*100):.1f}% · 1.5R</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #00c85330;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">TARGET 2 — Book 30%</div>
                                  <div style="color:#00c853;font-size:14px;font-weight:700;">₹{t2:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">+{((t2-price)/price*100):.1f}% · 3R ✓</div>
                                </div>
                                <div style="background:#060e1c;border:1px solid #00c85320;border-radius:8px;padding:12px;">
                                  <div style="color:#5c7099;font-size:9px;font-weight:600;margin-bottom:4px;">TARGET 3 — Trail 40%</div>
                                  <div style="color:#00c853;font-size:14px;font-weight:700;">₹{t3:,.1f}</div>
                                  <div style="color:#5c7099;font-size:10px;margin-top:2px;">+{((t3-price)/price*100):.1f}% · 5R</div>
                                </div>
                              </div>
                              <div style="background:#060e1c;border:1px solid #00c85320;border-radius:8px;padding:12px;text-align:center;margin-bottom:10px;">
                                <span style="color:#5c7099;font-size:12px;">RISK : REWARD = </span>
                                <span style="color:{'#00c853' if rr and rr>=3 else '#f44336'};font-size:16px;font-weight:800;">1 : {rr:.1f}</span>
                                <span style="color:#5c7099;font-size:12px;"> {'✓ Minimum met' if rr and rr>=3 else '✗ Below 3:1 — SKIP'}</span>
                              </div>
                              <div style="background:#060e1c;border:1px solid #2979ff20;border-radius:8px;padding:12px;">
                                <div style="color:#5c7099;font-size:10px;font-weight:600;margin-bottom:6px;">POSITION SIZE — {risk_pct}% RISK ON ₹{capital:,}</div>
                                <div style="color:#90caf9;font-size:15px;font-weight:700;">{qty} shares · ₹{pos_val:,.0f} position value</div>
                                <div style="color:#5c7099;font-size:11px;margin-top:4px;">Max risk = ₹{max_risk:,.0f} · SL at ₹{sl:,.1f} ({sl_pct:.1f}% below entry)</div>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # ── EXIT PLAN ────────────────────────────────────
                            st.markdown(f"""
                            <div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;">
                              <div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">EXIT PLAN</div>
                              <div style="color:#7b8fba;font-size:12px;line-height:2.0;">
                                📌 <strong style="color:#e0e8ff;">At Target 1 (₹{t1:,.1f}):</strong> Book 30% of position. Move stop to breakeven.<br>
                                📌 <strong style="color:#e0e8ff;">At Target 2 (₹{t2:,.1f}):</strong> Book another 30%. Trail stop at EMA10.<br>
                                📌 <strong style="color:#e0e8ff;">Remaining 40%:</strong> Trail using daily close below EMA10 (₹{e10:,.1f}).<br>
                                🚨 <strong style="color:#f44336;">Hard exit:</strong> Close below stop loss ₹{sl:,.1f} — no questions asked.<br>
                                ⏱️ <strong style="color:#ff9100;">Time stop:</strong> Exit if no progress in 15 trading days.
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                    # ── SCORE BREAKDOWN ──────────────────────────────────────
                    sc = res["scores"]
                    bars = "".join([
                        bar_html("EMA Stack (20>50>200)", sc.get("ema",0), 20),
                        bar_html("52W High Position",     sc.get("h52",0), 15),
                        bar_html("Volume Confirmation",   sc.get("vol",0), 15),
                        bar_html("MACD",                  sc.get("macd",0),15),
                        bar_html("RSI (14)",              sc.get("rsi",0), 10),
                        bar_html("6M Momentum",           sc.get("r6",0),  10),
                        bar_html("12M Momentum",          sc.get("r12",0), 10),
                        bar_html("RS vs Nifty",           sc.get("rs",0),  10),
                        bar_html("Liquidity",             sc.get("liq",0),  5),
                    ])
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;margin-bottom:14px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:12px;">SCORE BREAKDOWN (normalized to 100)</div>{bars}</div>', unsafe_allow_html=True)

                    # ── SIGNAL FLAGS ─────────────────────────────────────────
                    st.markdown(f'<div style="background:#0d1b2e;border:1px solid #1a2744;border-radius:10px;padding:16px;"><div style="color:#5c7099;font-size:10px;font-weight:600;letter-spacing:1px;margin-bottom:10px;">SIGNAL FLAGS — WHY THIS SCORE</div>{flag_html(res["flags"])}</div>', unsafe_allow_html=True)

            elif not fetch:
                st.markdown("""
                <div style="background:#0d1b2e;border:1px solid #2979ff30;border-radius:10px;padding:30px;text-align:center;margin-top:20px;">
                  <div style="font-size:36px;margin-bottom:12px;">🔍</div>
                  <div style="color:#e0e8ff;font-size:15px;font-weight:600;margin-bottom:8px;">Enter a stock symbol and click Fetch</div>
                  <div style="color:#5c7099;font-size:13px;line-height:1.8;">
                    7-factor scoring: EMA stack, 52W high, Volume, MACD, RSI, Returns, RS vs Nifty<br>
                    Smart stop loss based on EMA levels · Entry logic explained in plain English<br>
                    Liquidity gate · Single-day spike detection · Market regime filter
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: SCANNERS ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📡 Chartink Scanner Codes")
        st.caption("Run after 4 PM IST · chartink.com → Screens → Create New Screen → Paste → Generate")
        for name, code in SCANNERS.items():
            with st.expander(name):
                st.code(code, language="text")

    # ── TAB 3: LOGIC ─────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📖 How Scoring Works")
        rows = [
            ("EMA Stack",     20, "Full (Price>20>50>200)=20 | Partial=7-14 | Broken=0"),
            ("52W High Pos",  15, "At/above=15 | <1%=13 | <3%=11 | <7%=7 | <15%=3 | Far=0"),
            ("Volume",        15, "≥3x=15 | ≥2x=12 | ≥1.5x=10 | ≥1x=6 | <1x=2"),
            ("MACD 🆕",       15, "Positive+rising=15 | Positive+flat=10 | Near zero=5 | Negative=0"),
            ("RSI 🆕",        10, "50-65=10 | 65-70=7 | 45-50=5 | 70-80=2 | >80 or <40=0"),
            ("6M Return",     10, "≥50%=10 | ≥35%=8 | ≥20%=6 | ≥10%=4 | ≥0%=2 | Neg=0"),
            ("12M Return",    10, "≥60%=10 | ≥40%=8 | ≥25%=6 | ≥10%=4 | ≥0%=2 | Neg=0"),
            ("RS vs Nifty 🆕",10, "≥+20%=10 | ≥+10%=8 | ≥+5%=6 | ≥0%=4 | Negative=0"),
            ("Liquidity",      5, "≥₹25Cr/day = pass. Below = HARD REJECT before scoring."),
        ]
        for lbl, wt, desc in rows:
            c1,c2 = st.columns([5,1])
            with c1: st.markdown(f"**{lbl}**"); st.caption(desc)
            with c2: st.markdown(f"<div style='text-align:center;background:#060e1c;border:1px solid #2979ff30;border-radius:8px;padding:8px;margin-top:4px;'><div style='color:#2979ff;font-weight:800;font-size:18px;'>{wt}</div><div style='color:#5c7099;font-size:10px;'>PTS</div></div>", unsafe_allow_html=True)
            st.markdown("---")

        st.markdown("**Penalties applied after scoring:**")
        st.markdown("""
        - 🔴 **Single-day spike ≥10%:** -20 pts (operator/news move — don't chase)
        - 🔴 **Single-day spike 8-10%:** -10 pts
        - 🔴 **Single-day spike 5-8%:** -5 pts
        - 🟠 **Nifty below EMA50:** -10 pts regime penalty
        - 🔴 **Nifty below EMA200:** -20 pts regime penalty
        """)

        st.markdown("**Entry Type Logic:**")
        for et, desc in [
            ("BREAKOUT", "Price at/above 52W high with volume >1.5x — enter now or on confirmation"),
            ("PRE-BREAKOUT", "Within 3% of 52W high — anticipate or wait for confirmed breakout"),
            ("EMA20 PULLBACK", "Best risk:reward entry — price pulling back to EMA20 in uptrend"),
            ("EMA50 BOUNCE", "Deeper pullback to EMA50 — valid but wider stop needed"),
            ("MOMENTUM CONTINUATION", "Price above all EMAs — wait for EMA10 dip for best entry"),
            ("WAIT", "No clean setup — do not force an entry"),
        ]:
            st.markdown(f"- **{et}:** {desc}")

    st.markdown("""
    <div style="margin-top:20px;padding:10px 14px;background:#0d1b2e;border:1px solid #1a2744;border-radius:8px;color:#3d5070;font-size:10px;line-height:1.6;">
    Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day delay. Always verify before trading.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
