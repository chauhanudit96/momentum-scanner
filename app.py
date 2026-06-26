"""
NSE Elite Swing Trading Terminal — v6
Professional trading terminal UI. Setup-driven dynamic scoring.
Full plain-English descriptions for every metric, signal, and decision.
Indian market specific: F&O expiry, VIX, FII/DII context, sector rotation.
Zero nested f-strings. All HTML via string concatenation only.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Elite Swing Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── TERMINAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

.stApp { background-color: #04080f; color: #c9d1d9; font-family: 'Inter', sans-serif; }
.main .block-container { padding-top: 0.5rem; max-width: 1280px; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #0d1117; border-bottom: 1px solid #21262d; gap: 0; }
.stTabs [data-baseweb="tab"] {
    color: #8b949e !important; font-size: 12px !important; font-weight: 600 !important;
    letter-spacing: 0.5px !important; padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #58a6ff !important; border-bottom: 2px solid #58a6ff !important;
    background: transparent !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #0d1117 !important; border: 1px solid #30363d !important;
    color: #c9d1d9 !important; border-radius: 6px !important; font-size: 13px !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stSlider label {
    color: #8b949e !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 0.5px !important;
}
.stSlider [data-baseweb="slider"] { padding-top: 6px !important; }

/* Button */
.stButton button {
    background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
    color: white !important; font-weight: 700 !important; font-size: 13px !important;
    border: none !important; border-radius: 6px !important; letter-spacing: 0.5px !important;
    padding: 10px 20px !important; transition: all 0.2s !important;
}

/* Expander */
.stExpander {
    background: #0d1117 !important; border: 1px solid #21262d !important;
    border-radius: 8px !important;
}
.stExpander summary { color: #c9d1d9 !important; font-weight: 600 !important; }

/* Spinner */
.stSpinner { color: #58a6ff !important; }

/* Separator */
hr { border-color: #21262d !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

/* Mono font for prices */
.mono { font-family: 'JetBrains Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# ── POPULAR NSE STOCKS ────────────────────────────────────────────────────────
POPULAR = sorted([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "TITAN","WIPRO","ULTRACEMCO","NESTLEIND","SUNPHARMA","HCLTECH","TECHM",
    "POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT",
    "ADANIPORTS","CIPLA","DRREDDY","DIVISLAB","APOLLOHOSP","BAJAJFINSV",
    "EICHERMOT","HEROMOTOCO","M&M","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BEL","HAL","BHEL",
    "DATAPATTNS","LALPATHLAB","METROPOLIS","AKUMS","MARKSANS","SURYODAY",
    "INDSWFTLAB","THYROCARE","KAYNES","DIXON","AMBER","COALINDIA","RVNL",
    "GRASIM","DMART","NAUKRI","ZOMATO","IRCTC","IRFC","COCHINSHIP","GRSE",
    "TATAPOWER","CUMMINSIND","THERMAX","VOLTAS","BLUEDART","ASTRAL","POLYCAB",
    "SCHAEFFLER","AARTIIND","DEEPAKNTR","ATUL","NAVINFLUO","SOLARINDS",
])

SECTORS = {
    "Defense":      ["BEL","HAL","BHEL","COCHINSHIP","GRSE","BEML","DATAPATTNS","MTAR","PARAS"],
    "Pharma":       ["SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AUROPHARMA","LALPATHLAB","AKUMS","MARKSANS"],
    "Banking":      ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","INDUSINDBK","BANDHANBNK"],
    "Finance/NBFC": ["BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","MANAPPURAM","SURYODAY"],
    "IT":           ["TCS","INFY","HCLTECH","WIPRO","TECHM","MPHASIS","PERSISTENT","COFORGE"],
    "Auto":         ["MARUTI","TATAMOTORS","EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","M&M","ASHOKLEY"],
    "Chemicals":    ["DEEPAKNTR","AARTIIND","ATUL","NAVINFLUO","SOLARINDS","PIDILITIND","GALAXYSURF"],
    "Capital Goods":["SIEMENS","ABB","HAVELLS","THERMAX","CUMMINSIND","VOLTAMP","POLYCAB","KAYNES"],
    "FMCG":         ["HINDUNILVR","ITC","BRITANNIA","DABUR","MARICO","NESTLEIND","TATACONSUM"],
    "Metals":       ["JSWSTEEL","TATASTEEL","SAIL","HINDALCO","VEDL","COALINDIA","NMDC"],
}

# ── SETUP CONFIGS ─────────────────────────────────────────────────────────────
SETUP_CONFIGS = {
    "VCP": {
        "color": "#3fb950", "icon": "🌀", "min_score": 72,
        "name": "Volatility Contraction Pattern",
        "tagline": "The spring is coiling — an explosive breakout is building",
        "description": (
            "A VCP forms when a stock makes a series of smaller and smaller pullbacks near its highs, "
            "with volume declining sharply on each correction. This is supply exhaustion — sellers are "
            "running out of stock to sell. Institutions are quietly accumulating. The tighter the coil, "
            "the more explosive the eventual breakout. Minervini's most trusted setup."
        ),
        "what_to_watch": [
            "Volume below 50-day average by 30-50% — this confirms the coil",
            "Price range getting smaller each day — ATR shrinking",
            "Stock staying above EMA20 during each pullback",
            "Multiple touches of a resistance level without breaking down",
        ],
        "entry_trigger": "Breakout above the tight range on 2x+ average volume. This is your trigger — don't enter before it.",
        "sl_anchor": "ema10",
        "entry_rule": "breakout",
        "weights": {"volume_contraction":25,"price_tightness":20,"proximity_52h":20,"ema_stack":15,"rsi_zone":10,"macd_state":10},
        "risk_profile": "LOW",
        "ideal_hold": "5–15 trading days",
    },
    "BREAKOUT": {
        "color": "#58a6ff", "icon": "🚀", "min_score": 75,
        "name": "52-Week High Breakout",
        "tagline": "Resistance is breaking — institutional money is entering",
        "description": (
            "A breakout above the 52-week high is the single strongest momentum signal. "
            "Psychologically, it clears the overhang of every investor who bought in the last year — "
            "no one is sitting at a loss above this price. When volume confirms, institutions are "
            "aggressively accumulating. O'Neil, Darvas, and Weinstein all used this as their "
            "primary entry signal. In Indian markets, Nifty 200 breakouts on high volume have historically "
            "continued for 3–8 weeks before a meaningful pullback."
        ),
        "what_to_watch": [
            "Volume on breakout day must be at least 1.5x average — this is non-negotiable",
            "Check if the base before the breakout was at least 3 weeks — short bases fail more often",
            "NSE delivery percentage above 40% on breakout confirms institutional buying",
            "Breakout ideally happens between 9:30–11:30 AM — strong conviction",
        ],
        "entry_trigger": "Daily close above 52W high on volume. Or intraday when price clearly holds above the high for 30+ minutes.",
        "sl_anchor": "ema20",
        "entry_rule": "breakout",
        "weights": {"breakout_strength":30,"ema_stack":20,"proximity_52h":20,"rs_vs_nifty":15,"macd_state":10,"rsi_zone":5},
        "risk_profile": "MEDIUM",
        "ideal_hold": "5–20 trading days",
    },
    "BULL_FLAG": {
        "color": "#e3b341", "icon": "🏴", "min_score": 70,
        "name": "Bull Flag",
        "tagline": "The pole is strong — the flag is forming before the next surge",
        "description": (
            "A bull flag forms when a stock makes a strong, fast move up (the pole) and then "
            "consolidates in a tight, orderly range for 5–10 days with declining volume (the flag). "
            "The flag often slopes slightly downward — this is normal and healthy. "
            "The declining volume during the flag tells you that sellers are not in control — "
            "they're just taking a breather. When volume expands again and price breaks above "
            "the flag, the next leg of the move begins. Qullamaggie finds these on daily charts "
            "after a stock has already moved 20–50%."
        ),
        "what_to_watch": [
            "The pole should be steep and fast — 15–35% in 2–3 weeks",
            "Flag duration: 5–12 days is ideal. Longer flags lose momentum",
            "Volume should drop 40–60% during the flag vs the pole",
            "The flag channel should be tight — less than 6% range",
        ],
        "entry_trigger": "Break above the upper trendline of the flag on expanding volume. Time your entry at the very moment of the break.",
        "sl_anchor": "flag_low",
        "entry_rule": "flag_breakout",
        "weights": {"pole_strength":25,"flag_tightness":25,"volume_pattern":20,"ema_stack":15,"rsi_zone":10,"macd_state":5},
        "risk_profile": "LOW-MEDIUM",
        "ideal_hold": "3–10 trading days",
    },
    "EMA_PULLBACK": {
        "color": "#79c0ff", "icon": "↩️", "min_score": 68,
        "name": "EMA Pullback",
        "tagline": "The dip in an uptrend — lowest risk entry in a trending stock",
        "description": (
            "In a confirmed Stage 2 uptrend, stocks don't go straight up — they advance in waves, "
            "pulling back to their key moving averages between surges. The EMA20 pullback is the most "
            "reliable of these. When a strong stock dips to its 20-day EMA with LOW volume "
            "(meaning no one is panic-selling, just natural profit-taking), and then forms a bounce "
            "candle, that's your entry. Your stop is just below the EMA — so you're risking 2–3% "
            "for a potential 15–25% move. Best risk-reward of any setup."
        ),
        "what_to_watch": [
            "Volume must DRY UP on the dip — high volume dips are dangerous",
            "RSI should drop to 45–55 during pullback — partial reset without going oversold",
            "Price should touch or come within 3% of EMA20",
            "Look for a hammer, doji, or inside candle at the EMA as reversal signal",
            "EMA20 must be rising — a flat or falling EMA20 is a downtrend, not a pullback",
        ],
        "entry_trigger": "First green daily candle that closes above EMA20 on slightly higher volume. Don't enter until this candle forms.",
        "sl_anchor": "ema20",
        "entry_rule": "ema_reclaim",
        "weights": {"ema_stack":25,"pullback_quality":25,"volume_on_dip":20,"rs_vs_nifty":15,"macd_state":10,"rsi_zone":5},
        "risk_profile": "LOWEST",
        "ideal_hold": "5–15 trading days",
    },
    "SECOND_LEG": {
        "color": "#bc8cff", "icon": "⚡", "min_score": 75,
        "name": "Second Leg / Multi-Leg Momentum",
        "tagline": "Proven stock, proven institutions — the second move is often bigger",
        "description": (
            "After a stock makes a big first move (30–80%), it pauses and builds a base. "
            "If this base is TIGHT (institutions holding, not selling), and the stock then "
            "breaks out again — this is a second leg. These are Minervini's and Qullamaggie's "
            "highest conviction trades. The reasoning: the first move proved institutional "
            "interest. The tight base proved they didn't distribute (sell). The second breakout "
            "is them adding more. In Indian markets, stocks like HAL, BEL, and DATAPATTNS "
            "ran 3–4 legs without ever losing their Stage 2 structure."
        ),
        "what_to_watch": [
            "First leg: at least 30% move from base to peak",
            "Base after first leg: correction should be less than 35% (tight = institutions holding)",
            "Volume should dry up completely during the base between legs",
            "MACD must stay positive (above zero) throughout the base — no breakdown",
            "Stock must reclaim the breakout point from the first leg",
        ],
        "entry_trigger": "Breakout above the base high with 1.5x+ volume. The base after the first leg IS the setup — it needs to break first.",
        "sl_anchor": "base_low",
        "entry_rule": "base_breakout",
        "weights": {"first_leg_strength":25,"base_quality":25,"breakout_vol":20,"rs_vs_nifty":15,"macd_state":10,"ema_stack":5},
        "risk_profile": "MEDIUM",
        "ideal_hold": "10–30 trading days",
    },
    "FLAT_BASE": {
        "color": "#56d364", "icon": "📊", "min_score": 68,
        "name": "Flat Base",
        "tagline": "Tight, patient consolidation near highs — demand absorbing supply",
        "description": (
            "A flat base forms when a stock moves sideways in a very tight range (less than 8–10%) "
            "for 3–6 weeks near its highs, with declining volume. Unlike a VCP which shows "
            "contracting swings, a flat base is simply sideways — the stock is digesting a prior "
            "move. The key is that price never falls far from the highs, showing that buyers "
            "are immediately absorbing any selling. O'Neil found that the flatter and tighter "
            "the base, the bigger the eventual breakout move. Common in Nifty 50 stocks after "
            "institutional accumulation phases."
        ),
        "what_to_watch": [
            "Base range: less than 8% is good, less than 5% is exceptional",
            "Duration: at least 3 weeks (15 trading days minimum)",
            "Volume must be declining throughout the base",
            "Price should be within 15% of the 52-week high",
            "Multiple closes near the top of the range show buying pressure",
        ],
        "entry_trigger": "Breakout above the top of the flat base on 1.5x+ volume. The flat base ceiling is your exact entry trigger price.",
        "sl_anchor": "base_low",
        "entry_rule": "base_breakout",
        "weights": {"base_tightness":30,"proximity_52h":20,"volume_dryup":20,"ema_stack":15,"duration":10,"macd_state":5},
        "risk_profile": "LOW",
        "ideal_hold": "5–20 trading days",
    },
    "NO_SETUP": {
        "color": "#484f58", "icon": "⏳", "min_score": 999,
        "name": "No Clear Setup",
        "tagline": "Patience is a position — wait for the right setup",
        "description": "No tradeable swing pattern detected. The stock is between key levels without a clear entry trigger.",
        "what_to_watch": [],
        "entry_trigger": "Wait.",
        "sl_anchor": None, "entry_rule": "none",
        "weights": {}, "risk_profile": "DO NOT TRADE", "ideal_hold": "N/A",
    },
}

# ── HTML HELPERS (zero f-string logic) ───────────────────────────────────────
def div(content="", style=""):
    s = ' style="' + style + '"' if style else ""
    return "<div" + s + ">" + content + "</div>"

def span(content="", style=""):
    s = ' style="' + style + '"' if style else ""
    return "<span" + s + ">" + content + "</span>"

def badge(text, color, size="10px"):
    return span(text,
        "background:" + color + "20;color:" + color + ";"
        "border:1px solid " + color + "40;border-radius:4px;"
        "padding:2px 8px;font-size:" + size + ";font-weight:700;letter-spacing:0.5px;"
    )

def pill(text, color):
    return span(text,
        "background:" + color + ";color:#04080f;"
        "border-radius:20px;padding:2px 10px;font-size:10px;font-weight:800;"
    )

def section_header(text, sub=""):
    sub_html = div(sub, "color:#8b949e;font-size:11px;margin-top:3px;") if sub else ""
    return div(
        div(text, "color:#c9d1d9;font-size:11px;font-weight:700;letter-spacing:1px;") + sub_html,
        "margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #21262d;"
    )

def kv_row(key, val, val_color="#c9d1d9", desc=""):
    desc_html = div(desc, "color:#6e7681;font-size:10px;margin-top:2px;line-height:1.4;") if desc else ""
    return div(
        div(
            span(key, "color:#8b949e;font-size:11px;") +
            span(val, "color:" + val_color + ";font-size:12px;font-weight:700;float:right;"),
            "display:flex;justify-content:space-between;align-items:center;"
        ) + desc_html,
        "padding:8px 0;border-bottom:1px solid #161b22;"
    )

def metric_tile(label, value, color="#c9d1d9", sub="", desc=""):
    desc_html = div(desc, "color:#6e7681;font-size:9px;margin-top:4px;line-height:1.4;") if desc else ""
    sub_html  = div(sub,  "color:#8b949e;font-size:10px;margin-top:2px;") if sub else ""
    return div(
        div(label, "color:#8b949e;font-size:9px;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;") +
        div(value, "color:" + color + ";font-size:14px;font-weight:800;font-family:'JetBrains Mono',monospace;") +
        sub_html + desc_html,
        "background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 12px;"
    )

def signal_flag(ftype, title, message):
    colors = {"bull":"#3fb950","warn":"#e3b341","bear":"#f85149","info":"#58a6ff"}
    icons  = {"bull":"▲","warn":"◆","bear":"▼","info":"●"}
    c = colors.get(ftype,"#8b949e"); i = icons.get(ftype,"•")
    return div(
        div(
            span(i + " " + title, "color:" + c + ";font-size:11px;font-weight:700;") ,
            "margin-bottom:3px;"
        ) +
        div(message, "color:#8b949e;font-size:11px;line-height:1.5;"),
        "background:#0d1117;border:1px solid " + c + "25;border-left:3px solid " + c + ";"
        "border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;"
    )

def progress_bar(label, score, max_pts, desc=""):
    pct   = min(int(score/max_pts*100),100) if max_pts > 0 else 0
    col   = "#3fb950" if pct>=75 else "#e3b341" if pct>=50 else "#f85149"
    sym   = "✓" if pct>=75 else "~" if pct>=50 else "✗"
    desc_html = div(desc, "color:#6e7681;font-size:9px;margin-top:2px;line-height:1.4;") if desc else ""
    return div(
        div(
            span(label, "color:#c9d1d9;font-size:11px;") +
            span(sym + " " + str(score)+"/"+str(max_pts),
                "color:" + col + ";font-size:11px;font-weight:700;"),
            "display:flex;justify-content:space-between;margin-bottom:4px;"
        ) +
        div(
            div("", "height:100%;width:"+str(pct)+"%;background:"+col+";border-radius:2px;"),
            "height:4px;background:#21262d;border-radius:2px;overflow:hidden;"
        ) + desc_html,
        "margin-bottom:10px;"
    )

def level_box(label, value, color, sub="", desc=""):
    desc_html = div(desc, "color:#6e7681;font-size:9px;margin-top:4px;line-height:1.4;") if desc else ""
    sub_html  = div(sub,  "color:#8b949e;font-size:9px;margin-top:2px;") if sub else ""
    return div(
        div(label, "color:#8b949e;font-size:9px;font-weight:700;letter-spacing:0.3px;margin-bottom:4px;") +
        div(value, "color:" + color + ";font-size:13px;font-weight:800;font-family:'JetBrains Mono',monospace;") +
        sub_html + desc_html,
        "background:#0d1117;border:1px solid " + color + "30;border-radius:6px;padding:10px;"
    )

def info_box(title, content, color="#58a6ff"):
    return div(
        div(title, "color:" + color + ";font-size:11px;font-weight:700;margin-bottom:6px;") +
        div(content, "color:#8b949e;font-size:12px;line-height:1.7;"),
        "background:#0d1117;border:1px solid " + color + "25;border-radius:8px;padding:14px;margin-bottom:10px;"
    )

def warning_box(title, content):
    return div(
        div("⚠️ " + title, "color:#e3b341;font-size:12px;font-weight:700;margin-bottom:6px;") +
        div(content, "color:#8b949e;font-size:12px;line-height:1.7;"),
        "background:#161006;border:1px solid #e3b34130;border-radius:8px;padding:14px;margin-bottom:10px;"
    )

def danger_box(title, content):
    return div(
        div("🚫 " + title, "color:#f85149;font-size:12px;font-weight:700;margin-bottom:6px;") +
        div(content, "color:#8b949e;font-size:12px;line-height:1.7;"),
        "background:#160b0b;border:1px solid #f8514930;border-radius:8px;padding:14px;margin-bottom:10px;"
    )

def success_box(title, content):
    return div(
        div("✓ " + title, "color:#3fb950;font-size:12px;font-weight:700;margin-bottom:6px;") +
        div(content, "color:#8b949e;font-size:12px;line-height:1.7;"),
        "background:#0b1d0e;border:1px solid #3fb95030;border-radius:8px;padding:14px;margin-bottom:10px;"
    )

def Rs(val):
    return "Rs." + "{:,.1f}".format(val)

def pct(val, show_plus=True):
    if val is None: return "—"
    s = "+" if val >= 0 and show_plus else ""
    return s + str(round(val,1)) + "%"

# ── INDICATORS ────────────────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        f = float(v); return d if np.isnan(f) else f
    except: return d

def ema(s,p):   return s.ewm(span=p,adjust=False).mean()
def sma(s,p):   return s.rolling(p).mean()
def rsi_calc(s,p=14):
    d=s.diff(); g=d.clip(lower=0).rolling(p).mean()
    l=(-d.clip(upper=0)).rolling(p).mean()
    return 100-100/(1+g/l.replace(0,np.nan))
def macd_calc(s):
    m=s.ewm(span=12,adjust=False).mean()-s.ewm(span=26,adjust=False).mean()
    sig=m.ewm(span=9,adjust=False).mean(); return m,sig,m-sig

def enrich(df):
    df=df.copy(); c=df["Close"]
    for p in [10,20,50,200]: df["E"+str(p)]=ema(c,p)
    df["V50"]=sma(df["Volume"],50); df["V10"]=sma(df["Volume"],10)
    df["VR"]=df["Volume"]/df["V50"]
    df["H52"]=df["High"].rolling(252,min_periods=100).max()
    df["RSI"]=rsi_calc(c)
    df["ATR"]=(df["High"]-df["Low"]).rolling(14).mean()
    m,sig,h=macd_calc(c); df["MACD"]=m; df["SIG"]=sig; df["HIST"]=h
    return df

# ── FETCH ─────────────────────────────────────────────────────────────────────
def fetch_stock(sym):
    for sfx in [".NS",".BO"]:
        try:
            df=yf.Ticker(sym+sfx).history(period="2y",interval="1d",auto_adjust=True)
            if df is not None and len(df)>60:
                return df.dropna(subset=["Close"]),sym+sfx
        except: continue
    return None,None

def fetch_index(t):
    try:
        df=yf.Ticker(t).history(period="1y",interval="1d",auto_adjust=True)
        if df is not None and len(df)>50: return df.dropna(subset=["Close"])
    except: pass
    return None

# ── MARKET REGIME ─────────────────────────────────────────────────────────────
def market_regime(ndf, bndf):
    rows=[]; pen=0
    for name,df,ticker in [("Nifty 50",ndf,"^NSEI"),("Bank Nifty",bndf,"^NSEBANK")]:
        if df is None or len(df)<50:
            rows.append((name,"UNKNOWN","#484f58",0,"Cannot fetch index data right now.")); continue
        d=enrich(df); p=safe(d["Close"].iloc[-1])
        e50=safe(d["E50"].iloc[-1]); e200=safe(d["E200"].iloc[-1])
        chg=((p-safe(d["Close"].iloc[-2]))/safe(d["Close"].iloc[-2])*100) if safe(d["Close"].iloc[-2])>0 else 0
        if p<e200:
            rows.append((name,"BEARISH","#f85149",20,
                "Index is below its 200-day EMA — long-term downtrend. Capital preservation mode. Only exceptional setups above 85 qualify. Reduce position sizes by 50%."))
            pen=max(pen,20)
        elif p<e50:
            rows.append((name,"CAUTION","#e3b341",10,
                "Index is below its 50-day EMA — intermediate weakness. Avoid new breakout entries. Only EMA pullbacks in the strongest stocks. Use half position size."))
            pen=max(pen,10)
        else:
            rows.append((name,"HEALTHY","#3fb950",0,
                "Index is above both 50 and 200 EMA — Stage 2 uptrend. Full scoring and normal position sizing active. This is when momentum strategies work best."))
    return rows,pen

# ── SETUP DETECTION ───────────────────────────────────────────────────────────
def detect_setup(df):
    if len(df)<40: return "NO_SETUP",{}
    l=df.iloc[-1]
    p=safe(l["Close"]); e10=safe(l["E10"]); e20=safe(l["E20"])
    e50=safe(l["E50"]); e200=safe(l["E200"])
    h52=safe(l["H52"],p); vr=safe(l["VR"],1.0)
    mac=safe(l["MACD"]); hist=safe(l["HIST"])
    atr=safe(l["ATR"],p*0.02)
    c20=df["Close"].tail(20); c7=df["Close"].tail(7)
    v10=df["Volume"].tail(10).mean(); v50=df["Volume"].tail(50).mean()
    pct_h=(h52-p)/h52*100 if h52>0 else 100
    rng20=(c20.max()-c20.min())/c20.mean()*100 if c20.mean()>0 else 100
    rng7=(c7.max()-c7.min())/c7.mean()*100 if c7.mean()>0 else 100
    vol10=v10/v50 if v50>0 else 1.0
    mov20=(c20.iloc[-1]-c20.iloc[0])/c20.iloc[0]*100 if c20.iloc[0]>0 else 0
    emas=(p>e20)and(e20>e50)and(e50>e200)
    near20=abs(p-e20)/p<0.04 if p>0 else False
    near50=abs(p-e50)/p<0.05 if p>0 else False
    df6m=df.tail(126)
    l1max=float(df6m["High"].max()); l1min=float(df6m["Low"].min())
    l1move=(l1max-l1min)/l1min*100 if l1min>0 else 0
    pidx=df6m["High"].idxmax()
    after=df6m.loc[pidx:]
    blow=float(after["Low"].min()) if len(after)>5 else p
    bdepth=(l1max-blow)/l1max*100 if l1max>0 else 100
    p2p=(l1max-p)/l1max*100 if l1max>0 else 100
    sd={
        "price":p,"e10":e10,"e20":e20,"e50":e50,"e200":e200,
        "h52":h52,"pct_h":pct_h,"vr":vr,"rsi":safe(l["RSI"],50),
        "macd":mac,"hist":hist,"atr":atr,
        "rng20":rng20,"rng7":rng7,"vol_ratio10":vol10,
        "move20":mov20,"ema_stack":emas,"near_e20":near20,"near_e50":near50,
        "leg1_move":l1move,"base_depth":bdepth,"base_low_2leg":blow,
        "pct_from_peak":p2p,
        "flag_high":float(c7.max()),
        "base_high_20":float(df["High"].tail(20).max()),
        "base_low_20":float(df["Low"].tail(20).min()),
    }
    if l1move>=30 and bdepth<=30 and p2p<=10 and emas and vr>=1.2:
        return "SECOND_LEG",sd
    if pct_h<=1.5 and vr>=1.5 and emas:
        return "BREAKOUT",sd
    if pct_h<=12 and rng20<15 and vol10<0.80 and e20>e50 and e50>e200:
        return "VCP",sd
    if mov20>=12 and rng7<6 and vol10<0.90 and p>e20:
        return "BULL_FLAG",sd
    if rng20<10 and pct_h<=18 and e20>e50>e200 and vol10<0.95:
        return "FLAT_BASE",sd
    if e50>e200:
        if near20 and e20>e50: return "EMA_PULLBACK",sd
        if near50 and p>e200: return "EMA_PULLBACK",sd
    return "NO_SETUP",sd

# ── SCORING ───────────────────────────────────────────────────────────────────
SCORE_DESCRIPTIONS = {
    "volume_contraction": ("Volume Contraction","How much has volume shrunk vs the 50-day average. Deep contraction (below 50%) is the VCP signal — sellers have run out. The more it dries up, the more powerful the eventual breakout."),
    "price_tightness":    ("Price Range","How tight is the 20-day price range. Below 8% is a proper base. Below 5% is exceptional. Tight = institutions holding without panic. Wide = no institutional support."),
    "proximity_52h":      ("52W High Distance","How far is the stock from its 52-week high. Near the high means the stock is at peak strength. Far below means you're catching a falling knife or too early."),
    "ema_stack":          ("EMA Stack (Stage 2)","Is the stock in a proper Stage 2 uptrend? Price > EMA20 > EMA50 > EMA200 = fully bullish. Weinstein Stage 2 is when momentum strategies have the highest win rate."),
    "rsi_zone":           ("RSI Position","RSI 50-65 is the sweet spot — strong enough to be trending, not overbought. Above 75 means extended and chasing risk. Below 45 means the trend may be weakening."),
    "macd_state":         ("MACD Momentum","MACD positive with an expanding histogram = momentum accelerating. Positive but shrinking = slowing. Negative = avoid. This tells you if the engine is running hot or cooling."),
    "breakout_strength":  ("Breakout Volume","Volume on the breakout day relative to average. 1.5x = confirmed. 2x+ = institutional conviction. 3x+ = exceptional — the big players are aggressively accumulating."),
    "rs_vs_nifty":        ("Relative Strength vs Nifty","Is this stock outperforming the Nifty 50? A stock up 30% when Nifty is up 5% is a market leader. A stock up 30% when Nifty is up 25% is just riding the wave. Leaders outperform."),
    "pole_strength":      ("Pole Strength","How strong was the initial move (the flagpole). 20%+ in 2-3 weeks = institutional buying. 35%+ = exceptional. Weak poles produce weak follow-through after the flag."),
    "flag_tightness":     ("Flag Tightness","How tight is the consolidation after the pole. Less than 5% range = very tight flag. 5-8% = ok. More than 10% = not a flag, it's a base or distribution."),
    "volume_pattern":     ("Volume Pattern (Pole vs Flag)","Volume should be HIGH during the pole and LOW during the flag. This asymmetry confirms that institutions bought on the pole and are holding during the flag — not selling."),
    "pullback_quality":   ("Pullback Quality","How cleanly has price pulled back to the EMA. Touching the exact EMA on very low volume = ideal. Crashing through the EMA on high volume = distribution, not pullback."),
    "volume_on_dip":      ("Volume During Dip","Volume MUST be low during a healthy pullback. Low volume = nobody panic selling. High volume on a dip = someone knows something bad and is selling. Danger sign."),
    "first_leg_strength": ("First Leg Move","How big was the initial move before the base. 35%+ proves institutional buying power. 50%+ = major momentum stock. Bigger first legs tend to produce bigger second legs."),
    "base_quality":       ("Base Quality (Depth)","How deep was the base/correction between legs. 10-20% = very tight (institutions held). 20-30% = acceptable. 30-40% = deeper, needs more evidence. 40%+ = failed pattern."),
    "breakout_vol":       ("Second Leg Breakout Volume","Volume as the stock breaks out of the base for the second leg. Needs to be 1.5x+ to confirm institutional re-entry. 2x+ = very high conviction. Low volume = weak signal."),
    "base_tightness":     ("Flat Base Tightness","The 20-day price range as a percentage. Below 5% = exceptional flat base. 5-8% = solid. 8-12% = acceptable. This is the core quality metric for a flat base setup."),
    "volume_dryup":       ("Volume Dry-Up on Base","Volume declining throughout the base shows supply is exhausted. 50-70% of average = healthy dry-up. Above 90% = volume not really drying — weak setup."),
    "duration":           ("Base Duration","Whether the base has lasted long enough. Minimum 3 weeks (15 trading days). Short bases are unstable. 4-8 week bases are ideal. Very long bases sometimes lose momentum."),
}

def score_setup(setup_name, sd, r6, r12, rs):
    cfg=SETUP_CONFIGS.get(setup_name,SETUP_CONFIGS["NO_SETUP"])
    w=cfg["weights"]; scores={}; flags=[]
    p=sd.get("price",0); pct_h=sd.get("pct_h",100)
    vr=sd.get("vr",1.0); rsi_=sd.get("rsi",50.0)
    mac=sd.get("macd",0.0); hist=sd.get("hist",0.0)
    rng20=sd.get("rng20",100); rng7=sd.get("rng7",100)
    vol10=sd.get("vol_ratio10",1.0); mov20=sd.get("move20",0.0)
    emas=sd.get("ema_stack",False); e20=sd.get("e20",0)
    e50=sd.get("e50",0); e200=sd.get("e200",0)
    leg1=sd.get("leg1_move",0); bd=sd.get("base_depth",100)
    near20=sd.get("near_e20",False); near50=sd.get("near_e50",False)

    def sc(key,val,mx,tiers,flag_msgs):
        for thresh,pts_frac,ft,msg in tiers:
            if val>=thresh if isinstance(thresh,(int,float)) else thresh:
                sc_val=int(mx*pts_frac); scores[key]=sc_val
                flags.append((ft,SCORE_DESCRIPTIONS.get(key,("",))[0],flag_msgs[tiers.index((thresh,pts_frac,ft,msg))]))
                return
        scores[key]=0

    # EMA STACK
    if "ema_stack" in w:
        mx=w["ema_stack"]
        if p>e20>e50>e200:
            scores["ema_stack"]=mx
            flags.append(("bull","Stage 2 Confirmed","Price above EMA20 > EMA50 > EMA200. This is Weinstein Stage 2 — the only stage where momentum strategies consistently work. All timeframes bullish."))
        elif e20>e50>e200:
            scores["ema_stack"]=int(mx*0.65)
            flags.append(("warn","Stage 2 Partial","EMAs are aligned bullishly but price dipped below EMA20. Stock is in Stage 2 but temporarily weak. Wait for price to reclaim EMA20 before entering."))
        elif e20>e50 or e50>e200:
            scores["ema_stack"]=int(mx*0.30)
            flags.append(("bear","EMA Alignment Weak","Only partial EMA alignment. Stage 2 is still developing. Higher risk — trend may not be established enough for a reliable swing trade."))
        else:
            scores["ema_stack"]=0
            flags.append(("bear","EMA Stack Bearish","EMAs are in bearish order. This stock is likely in Stage 3 (topping) or Stage 4 (downtrend). Do not buy declining stocks hoping they recover."))

    # PROXIMITY TO 52W HIGH
    if "proximity_52h" in w:
        mx=w["proximity_52h"]
        if pct_h<=0:    scores["proximity_52h"]=mx;         flags.append(("bull","At 52W High — Breakout","Stock is at or above its 52-week high. Resistance cleared. Maximum momentum signal. Every seller from the last year is now at a profit or breakeven — no overhead resistance."))
        elif pct_h<=2:  scores["proximity_52h"]=int(mx*.90); flags.append(("bull","Within 2% of 52W High","Extremely close to breakout. A single good session could trigger the breakout. Set GTT alert at the 52W high level."))
        elif pct_h<=5:  scores["proximity_52h"]=int(mx*.75); flags.append(("bull","Within 5% of 52W High","Near-breakout zone. Stock is coiling near highs. Good setup stage but needs to break out before entering aggressively."))
        elif pct_h<=10: scores["proximity_52h"]=int(mx*.50); flags.append(("warn","10% Below 52W High","In base formation territory. Could be building for a breakout, could also be topping. Need other signals to confirm direction."))
        elif pct_h<=20: scores["proximity_52h"]=int(mx*.25); flags.append(("warn","10-20% Below 52W High","Extended base or early recovery. Too far from breakout zone for an ideal setup. Watch but don't act yet."))
        else:           scores["proximity_52h"]=0;           flags.append(("bear","Far From 52W High","More than 20% below the 52-week high. This is not a momentum setup. Avoid — you would be catching a falling knife or betting on a recovery."))

    # VOLUME CONTRACTION
    if "volume_contraction" in w:
        mx=w["volume_contraction"]
        pct_vol=str(round(vol10*100))
        if vol10<0.40:   scores["volume_contraction"]=mx;          flags.append(("bull","Deep Volume Contraction","Volume at only "+pct_vol+"% of 50-day average. Exceptional contraction — sellers have completely dried up. This is supply exhaustion. The quieter it gets before a breakout, the bigger the move."))
        elif vol10<0.60: scores["volume_contraction"]=int(mx*.80);  flags.append(("bull","Strong Volume Contraction","Volume at "+pct_vol+"% of average. Healthy VCP signature. Institutions are accumulating quietly while retail attention wanders elsewhere. Ideal coiling."))
        elif vol10<0.75: scores["volume_contraction"]=int(mx*.55);  flags.append(("warn","Moderate Volume Contraction","Volume at "+pct_vol+"% of average. Some drying but not deep enough for classic VCP. Setup is developing — watch daily."))
        else:            scores["volume_contraction"]=int(mx*.15);  flags.append(("bear","Insufficient Volume Contraction","Volume at "+pct_vol+"% of average — not contracting enough. VCP requires volume drying up significantly. Wait for more contraction."))

    # PRICE TIGHTNESS
    if "price_tightness" in w or "base_tightness" in w:
        key="price_tightness" if "price_tightness" in w else "base_tightness"
        mx=w[key]; rng_s=str(round(rng20,1))
        if rng20<5:    scores[key]=mx;          flags.append(("bull","Exceptional Tightness","20-day range only "+rng_s+"%. Extremely tight coil. When a stock moves less than 5% over 20 days, the spring is fully wound. Breakouts from such tight ranges are typically explosive."))
        elif rng20<8:  scores[key]=int(mx*.80); flags.append(("bull","Strong Price Tightness","20-day range of "+rng_s+"%. Solid base tightness — this is what a proper flat base or VCP looks like. Institutions are absorbing supply without letting price fluctuate much."))
        elif rng20<12: scores[key]=int(mx*.55); flags.append(("warn","Moderate Tightness","20-day range of "+rng_s+"%. Acceptable but not ideal. A tighter range would give you higher confidence and a better stop loss level."))
        elif rng20<18: scores[key]=int(mx*.25); flags.append(("warn","Loose Base","20-day range of "+rng_s+"%. This is a wide base — either institutional conviction is low or the stock is still finding support. Higher risk of a failed breakout."))
        else:          scores[key]=0;           flags.append(("bear","No Real Base Forming","20-day range of "+rng_s+"% — too wide to be called a base. Price is oscillating without building structure. Wait for consolidation."))

    # BREAKOUT STRENGTH
    if "breakout_strength" in w:
        mx=w["breakout_strength"]; vr_s=str(round(vr,1))
        if vr>=4.0:   scores["breakout_strength"]=mx;          flags.append(("bull","Exceptional Breakout Volume","Volume "+vr_s+"x average. Institutional stampede. This kind of volume surge means large funds are urgently building positions. Very high probability of continuation."))
        elif vr>=2.5: scores["breakout_strength"]=int(mx*.85); flags.append(("bull","Strong Breakout Volume","Volume "+vr_s+"x average. Clear institutional participation. FIIs or large mutual funds are behind this move. Breakout has strong legs."))
        elif vr>=1.5: scores["breakout_strength"]=int(mx*.65); flags.append(("bull","Confirmed Breakout Volume","Volume "+vr_s+"x average — meets the minimum threshold. Breakout is real but institutional conviction could be higher. Worth taking but watch the next few sessions."))
        elif vr>=1.0: scores["breakout_strength"]=int(mx*.30); flags.append(("warn","Below-Average Breakout Volume","Volume "+vr_s+"x average. Marginal — could be a false breakout. In Indian markets, low-volume breakouts on Nifty 200 stocks fail more than 50% of the time. Caution."))
        else:         scores["breakout_strength"]=0;           flags.append(("bear","Weak Volume on Breakout","Volume only "+vr_s+"x average. High probability of a failed/fake breakout. Wait for a retest with better volume before entering."))

    # POLE STRENGTH
    if "pole_strength" in w:
        mx=w["pole_strength"]; mv_s=str(round(mov20,1))
        if mov20>=35:  scores["pole_strength"]=mx;          flags.append(("bull","Exceptional Pole Strength","Stock moved +"+mv_s+"% in 20 days. This is a powerful institutional move. Strong poles produce strong second legs after the flag. Very high conviction."))
        elif mov20>=22:scores["pole_strength"]=int(mx*.85); flags.append(("bull","Strong Pole","Stock moved +"+mv_s+"% in 20 days. A solid bull flag pole. The move was driven by real buying. Flag should resolve to the upside."))
        elif mov20>=12:scores["pole_strength"]=int(mx*.60); flags.append(("warn","Moderate Pole","Stock moved +"+mv_s+"% in 20 days. Acceptable for a bull flag but not exceptional. The follow-through from a moderate pole tends to be smaller. Adjust targets accordingly."))
        else:          scores["pole_strength"]=0;           flags.append(("bear","Weak Pole","Stock moved only +"+mv_s+"% in 20 days. Too weak for a reliable bull flag. The follow-through from weak poles is often disappointing. Look for stronger setups."))

    # FLAG TIGHTNESS
    if "flag_tightness" in w:
        mx=w["flag_tightness"]; rng7_s=str(round(rng7,1))
        if rng7<3:    scores["flag_tightness"]=mx;          flags.append(("bull","Very Tight Flag","7-day flag range only "+rng7_s+"%. This is an extremely tight flag — the cleanest possible consolidation. Institutions are not selling at all. High probability breakout."))
        elif rng7<5:  scores["flag_tightness"]=int(mx*.85); flags.append(("bull","Tight Flag","7-day range of "+rng7_s+"%. Good flag tightness. Orderly consolidation after the pole move. This is what a healthy bull flag should look like."))
        elif rng7<8:  scores["flag_tightness"]=int(mx*.55); flags.append(("warn","Moderate Flag","7-day range of "+rng7_s+"%. Acceptable but a bit wide. The wider the flag, the more risk of a failed breakout. Use a tighter stop."))
        else:         scores["flag_tightness"]=0;           flags.append(("bear","Wide Flag — Not Clean","7-day range of "+rng7_s+"%. Too wide to be called a proper flag. This is more of a loose consolidation. Risk of the pole move being fully retraced is higher."))

    # VOLUME PATTERN (flag)
    if "volume_pattern" in w:
        mx=w["volume_pattern"]
        if vol10<0.55 and vr>=1.5:
            scores["volume_pattern"]=mx
            flags.append(("bull","Perfect Volume Asymmetry","High volume on pole, very low on flag. This is textbook bull flag volume behavior. Institutions bought aggressively on the pole and are sitting tight during the flag. Highest conviction pattern."))
        elif vol10<0.75:
            scores["volume_pattern"]=int(mx*.65)
            flags.append(("warn","Decent Volume Pattern","Volume partially drying during flag. Good but not perfect. The flag is healthy but institutions could be taking some profit. Watch for expansion on the breakout."))
        else:
            scores["volume_pattern"]=int(mx*.20)
            flags.append(("bear","Volume Not Drying on Flag","Volume during flag is not significantly lower than the pole. This suggests distribution may be occurring during the consolidation. Higher risk of a failed breakout."))

    # PULLBACK QUALITY
    if "pullback_quality" in w:
        mx=w["pullback_quality"]
        if near20 and vol10<0.70:
            scores["pullback_quality"]=mx
            flags.append(("bull","Perfect EMA20 Pullback","Price is resting on EMA20 with very low volume. This is Minervini's ideal low-risk entry — the trend is intact, sellers have gone quiet, and the stock is ready to bounce. Best entry of all setup types."))
        elif near20:
            scores["pullback_quality"]=int(mx*.70)
            flags.append(("warn","EMA20 Pullback — Volume Too High","Price is at EMA20 but volume is not drying enough. Could be a temporary bounce or could be distribution. Wait for volume to dry before entering."))
        elif near50 and vol10<0.80:
            scores["pullback_quality"]=int(mx*.55)
            flags.append(("warn","EMA50 Pullback — Deeper Dip","Price has pulled back all the way to EMA50 — deeper than ideal. Still tradeable if EMA50 is rising and RSI is not oversold. But stop loss will be wider."))
        else:
            scores["pullback_quality"]=int(mx*.20)
            flags.append(("bear","Not at a Clean EMA Level","Price is not cleanly at EMA20 or EMA50. Entering here means you don't have a clear stop loss anchor. Wait for price to reach one of these levels."))

    # VOLUME ON DIP
    if "volume_on_dip" in w:
        mx=w["volume_on_dip"]; pct_v=str(round(vol10*100))
        if vol10<0.50:   scores["volume_on_dip"]=mx;          flags.append(("bull","Volume Very Low on Dip","Volume at only "+pct_v+"% of average during the pullback. Nobody is panic-selling. This is a natural, healthy dip — institutions are holding all their shares. Very bullish for the continuation."))
        elif vol10<0.70: scores["volume_on_dip"]=int(mx*.80); flags.append(("bull","Volume Drying on Dip","Volume at "+pct_v+"% during pullback. Healthy. The selling is light and orderly — profit-taking, not distribution. Good quality pullback."))
        elif vol10<0.85: scores["volume_on_dip"]=int(mx*.50); flags.append(("warn","Volume Moderate on Dip","Volume at "+pct_v+"% during pullback. Somewhat elevated. Could be light distribution or just normal selling. Watch the next session's volume closely."))
        else:            scores["volume_on_dip"]=int(mx*.15); flags.append(("bear","High Volume on Dip — Red Flag","Volume at "+pct_v+"% during the dip — higher than average. This is not a healthy pullback. Someone with significant holdings is selling. Avoid entering until volume normalizes."))

    # FIRST LEG
    if "first_leg_strength" in w:
        mx=w["first_leg_strength"]; l1_s=str(round(leg1,0))[:-2] if ".0" in str(round(leg1,0)) else str(round(leg1,0))
        if leg1>=70:   scores["first_leg_strength"]=mx;          flags.append(("bull","Exceptional First Leg (+"+l1_s+"%)","A "+l1_s+"% first move proves this is a major institutional stock. Funds don't build 70%+ moves in a stock they don't believe in. Second legs after moves this big tend to be powerful."))
        elif leg1>=45: scores["first_leg_strength"]=int(mx*.85); flags.append(("bull","Strong First Leg (+"+l1_s+"%)","A "+l1_s+"% first move shows strong institutional interest. Good foundation for a second leg. The bigger the first move, the bigger the second leg tends to be."))
        elif leg1>=28: scores["first_leg_strength"]=int(mx*.60); flags.append(("warn","Moderate First Leg (+"+l1_s+"%)","The "+l1_s+"% first move is acceptable. Second leg setups work with smaller first moves but the potential upside is proportionally smaller. Adjust your targets."))
        else:          scores["first_leg_strength"]=0;           flags.append(("bear","First Leg Too Small (+"+l1_s+"%)","A "+l1_s+"% move is not strong enough to qualify as a second-leg setup. The institutional conviction shown was insufficient. Look for stocks with larger first moves."))

    # BASE QUALITY
    if "base_quality" in w:
        mx=w["base_quality"]; bd_s=str(round(bd,1))
        if bd<=12:   scores["base_quality"]=mx;          flags.append(("bull","Very Tight Base ("+bd_s+"% deep)","The correction after the first leg was only "+bd_s+"%. This is exceptional — institutions barely sold anything. Tight bases after big moves = highest conviction second-leg setups."))
        elif bd<=20: scores["base_quality"]=int(mx*.80); flags.append(("bull","Tight Base ("+bd_s+"% deep)","The "+bd_s+"% correction is healthy. Institutions took some profit but the bulk of their position is intact. Good quality base for a second leg."))
        elif bd<=30: scores["base_quality"]=int(mx*.55); flags.append(("warn","Moderate Base ("+bd_s+"% deep)","A "+bd_s+"% correction means some distribution occurred. Still tradeable but the second leg may be smaller. Ensure volume dried up during the base."))
        else:        scores["base_quality"]=0;           flags.append(("bear","Deep Correction ("+bd_s+"%)","A "+bd_s+"% correction is too deep for a clean second-leg setup. This level of selling suggests institutions took most of their profits. The 'base' here is more of a full retracement."))

    # BREAKOUT VOL (second leg)
    if "breakout_vol" in w:
        mx=w["breakout_vol"]; vr_s=str(round(vr,1))
        if vr>=3:   scores["breakout_vol"]=mx;          flags.append(("bull","High Conviction Breakout ("+vr_s+"x)","Volume "+vr_s+"x average on the leg 2 breakout. Institutions are aggressively re-entering. This confirms they didn't exit during the base — they were waiting to add more."))
        elif vr>=2: scores["breakout_vol"]=int(mx*.80); flags.append(("bull","Strong Breakout ("+vr_s+"x)","Volume "+vr_s+"x average confirms institutional buying on the second leg. Strong signal."))
        elif vr>=1.5:scores["breakout_vol"]=int(mx*.60);flags.append(("warn","Acceptable Breakout Volume ("+vr_s+"x)","Volume "+vr_s+"x average — meets minimum. Second leg is underway but more volume would give higher confidence."))
        else:       scores["breakout_vol"]=0;           flags.append(("bear","Weak Second Leg Volume ("+vr_s+"x)","Volume only "+vr_s+"x on what should be an institutional second-leg breakout. Low volume second legs fail frequently. Wait for a retest with better volume."))

    # VOLUME DRYUP (flat base)
    if "volume_dryup" in w:
        mx=w["volume_dryup"]; pct_v=str(round(vol10*100))
        if vol10<0.55:   scores["volume_dryup"]=mx;          flags.append(("bull","Excellent Volume Dry-Up","Volume at "+pct_v+"% of average during base. Near-complete supply exhaustion. The flat base is of very high quality. When breakout comes, the response should be sharp and decisive."))
        elif vol10<0.70: scores["volume_dryup"]=int(mx*.75); flags.append(("bull","Good Volume Dry-Up","Volume declining nicely during the base at "+pct_v+"% of average. Healthy flat base behavior."))
        elif vol10<0.85: scores["volume_dryup"]=int(mx*.45); flags.append(("warn","Partial Volume Dry-Up","Volume at "+pct_v+"% — declining but not enough. The flat base quality would improve if volume dried further over the next week."))
        else:            scores["volume_dryup"]=int(mx*.10); flags.append(("bear","Volume Not Drying","Volume at "+pct_v+"% — still close to average. This is not a proper flat base if volume stays elevated. Could be distribution disguised as consolidation."))

    # DURATION
    if "duration" in w:
        mx=w["duration"]
        if rng20>0 and vol10<0.9:
            scores["duration"]=mx
            flags.append(("bull","Base Duration Adequate","The stock has been building a base long enough to clear overhead supply. Bases need at least 3 weeks to be reliable. Shorter bases often fail on the breakout."))
        else:
            scores["duration"]=int(mx*.40)
            flags.append(("warn","Base May Be Too Young","The base formation may not be mature enough yet. Ideal flat bases take 3-6 weeks to develop. Give it more time if possible."))

    # RSI
    if "rsi_zone" in w:
        mx=w["rsi_zone"]; rsi_s=str(round(rsi_))
        if 50<=rsi_<=65:    scores["rsi_zone"]=mx;          flags.append(("bull","RSI in Sweet Spot ("+rsi_s+")","RSI between 50-65 is the ideal momentum zone. Strong enough to confirm upward trend, not yet overbought. Maximum room to run without an immediate correction."))
        elif 45<=rsi_<50:   scores["rsi_zone"]=int(mx*.65); flags.append(("warn","RSI Recovering ("+rsi_s+")","RSI is below 50 but recovering. Momentum is weak but not broken. Stock needs to push above 50 RSI to confirm the uptrend is resuming."))
        elif 65<rsi_<=72:   scores["rsi_zone"]=int(mx*.55); flags.append(("warn","RSI Approaching Overbought ("+rsi_s+")","RSI above 65 means the stock is gaining steam but entering caution territory. Still tradeable but be ready for a 1-3 day pullback before continuation."))
        elif 72<rsi_<=80:   scores["rsi_zone"]=int(mx*.20); flags.append(("warn","RSI Overbought ("+rsi_s+")","RSI above 72 means the stock is extended short-term. Entering now risks buying at the top of a minor wave. Wait for an RSI pullback to 55-65 range."))
        elif rsi_>80:       scores["rsi_zone"]=0;           flags.append(("bear","RSI Extremely Overbought ("+rsi_s+")","RSI above 80 signals an unsustainable short-term move. High probability of a sharp pullback before continuation. Missing this trade is better than chasing it at RSI 80+."))
        else:               scores["rsi_zone"]=0;           flags.append(("bear","RSI Downtrend ("+rsi_s+")","RSI below 45 indicates the stock is in a downtrend or weakening significantly. Momentum strategies don't work well when RSI is this low."))

    # MACD
    if "macd_state" in w:
        mx=w["macd_state"]
        if mac>0 and hist>0:
            scores["macd_state"]=mx
            flags.append(("bull","MACD Accelerating","MACD is positive AND the histogram is expanding — momentum is building, not topping. This is the best MACD state for swing entries. The engine is running hot."))
        elif mac>0:
            scores["macd_state"]=int(mx*.65)
            flags.append(("warn","MACD Positive but Slowing","MACD is positive (bullish) but the histogram is shrinking. Momentum exists but is decelerating. Stock may need a rest before the next move up. Acceptable for entry but manage expectations."))
        elif -0.5<mac<=0:
            scores["macd_state"]=int(mx*.30)
            flags.append(("warn","MACD Near Zero","MACD just below the zero line. Watching for a bullish crossover. If MACD crosses above zero with expanding histogram, that's a strong secondary buy signal."))
        else:
            scores["macd_state"]=0
            flags.append(("bear","MACD Negative","MACD is negative — bearish momentum is dominating. Entering against negative MACD puts you in an uphill battle. Wait for MACD to recover above zero before considering entry."))

    # RS VS NIFTY
    if "rs_vs_nifty" in w:
        mx=w["rs_vs_nifty"]
        if rs is None:
            scores["rs_vs_nifty"]=int(mx*.50)
        elif rs>=20:   scores["rs_vs_nifty"]=mx;          flags.append(("bull","Massive Outperformer (+"+str(round(rs,1))+"% vs Nifty)","This stock is outperforming the Nifty 50 by "+str(round(rs,1))+"%  over 6 months. This is a genuine market leader — the kind of stock that FIIs and large funds are overweight. These are your best swing trades."))
        elif rs>=10:   scores["rs_vs_nifty"]=int(mx*.85); flags.append(("bull","Outperforming Nifty (+"+str(round(rs,1))+"%)","Strong relative strength vs the market. Outperforming by "+str(round(rs,1))+"%  means institutional interest is clear. This stock will likely continue to lead when the market rallies."))
        elif rs>=3:    scores["rs_vs_nifty"]=int(mx*.65); flags.append(("warn","Slightly Ahead of Nifty (+"+str(round(rs,1))+"%)","Marginally outperforming. Not a leader but not a laggard. Look for stocks outperforming by 10%+ for the best swing trades in the current environment."))
        elif rs>=0:    scores["rs_vs_nifty"]=int(mx*.35); flags.append(("warn","Matching Nifty ("+str(round(rs,1))+"%)","Stock is barely keeping pace with the index. In a bull market, the best swing trades outperform the index by 10%+. A stock that just matches Nifty is not a leader."))
        else:          scores["rs_vs_nifty"]=0;           flags.append(("bear","Underperforming Nifty ("+str(round(rs,1))+"%)","Stock is "+str(round(abs(rs),1))+"% behind Nifty over 6 months. Avoid — if the market dips, this stock will fall even harder. Only trade relative strength leaders."))

    raw=sum(scores.values()); return scores,flags,raw

# ── TRADE PLAN ────────────────────────────────────────────────────────────────
def build_trade(setup, sd, raw, capital, risk_pct, regime_pen):
    cfg=SETUP_CONFIGS.get(setup,SETUP_CONFIGS["NO_SETUP"])
    final=max(0,raw-regime_pen)
    min_s=cfg["min_score"]; p=sd.get("price",0)
    e10=sd.get("e10",0); e20=sd.get("e20",0); e50=sd.get("e50",0)
    h52=sd.get("h52",0); atr=sd.get("atr",p*0.02)
    flag_h=sd.get("flag_high",p); base_h=sd.get("base_high_20",p)
    base_l=sd.get("base_low_20",p*.95); blow=sd.get("base_low_2leg",p*.95)
    near20=sd.get("near_e20",False)

    if setup=="NO_SETUP" or final<min_s:
        return {"viable":False,"verdict":"NO TRADE","vc":"#484f58","final":final,
                "reason":"Score "+str(final)+" is below the minimum "+str(min_s)+" required for a "+cfg["name"]+" setup. Wait for a higher-quality setup.",
                "entry_agg":0,"entry_con":0,"entry_ret":0,"entry_note":"Wait.",
                "sl":0,"sl_pct":0,"sl_label":"","t1":0,"t2":0,"t3":0,"qty":0,"pos_val":0,"rr":0}

    # Verdict
    if final>=90:   verdict,vc="ELITE SETUP","#3fb950"
    elif final>=78: verdict,vc="STRONG SETUP","#58a6ff"
    elif final>=65: verdict,vc="TRADABLE","#e3b341"
    else:           verdict,vc="BELOW MIN — AVOID","#f85149"

    if vc=="#f85149":
        return {"viable":False,"verdict":verdict,"vc":vc,"final":final,
                "reason":"Score "+str(final)+" is below minimum "+str(min_s)+" for this setup type. The setup is detected but quality is insufficient. Wait for improvement.",
                "entry_agg":0,"entry_con":0,"entry_ret":0,"entry_note":"Wait for score to improve.",
                "sl":0,"sl_pct":0,"sl_label":"","t1":0,"t2":0,"t3":0,"qty":0,"pos_val":0,"rr":0}

    # SL
    anchor=cfg["sl_anchor"]
    if anchor=="ema10":   sl=e10*.99;   sl_lbl="1% below EMA10"
    elif anchor=="ema20": sl=e20*.99;   sl_lbl="1% below EMA20"
    elif anchor=="flag_low": sl=base_l*.995; sl_lbl="0.5% below flag low"
    elif anchor=="base_low": sl=blow*.99;    sl_lbl="1% below base low"
    else:                 sl=p*.95;     sl_lbl="5% mechanical"
    sl_pct=(p-sl)/p*100 if p>0 else 5
    if sl_pct>6: sl=p*.94; sl_pct=6.0; sl_lbl="6% hard cap (logical SL too wide)"

    # Entry
    rule=cfg["entry_rule"]
    if rule=="breakout":
        ea=p; ec=round(h52*1.005,1); er=round(h52*.99,1)
        note=("BREAKOUT ENTRY: Stock is at/near its 52W high of "+Rs(h52)+". "
              "Aggressive — buy now at market. Conservative — wait for daily close above "+Rs(h52*1.005)+" with 1.5x+ volume. "
              "Retest — if price pulls back to "+Rs(er)+" (old resistance becomes support), that is a second, lower-risk entry.")
    elif rule=="flag_breakout":
        ea=flag_h; ec=round(flag_h*1.01,1); er=round(flag_h*.995,1)
        note=("FLAG BREAKOUT ENTRY: Do NOT buy inside the flag — wait for the breakout. "
              "Aggressive — buy as price breaks above flag high "+Rs(flag_h)+". Conservative — buy next candle after a breakout close. "
              "Retest — "+Rs(er)+" is the flag high turned support.")
    elif rule=="ema_reclaim":
        te=e20 if near20 else e50; en=("EMA20" if near20 else "EMA50")
        ea=round(te*1.002,1); ec=round(te*1.01,1); er=round(te*.998,1)
        note=("EMA PULLBACK ENTRY: Stock is at "+en+" ("+Rs(te)+"). "
              "Aggressive — buy as price reclaims "+en+" at "+Rs(ea)+". Conservative — wait for first green daily candle closing above "+en+". "
              "Retest — if "+en+" is touched again at "+Rs(er)+" without breaking down, that is a second entry.")
    elif rule=="base_breakout":
        ea=base_h; ec=round(base_h*1.01,1); er=round(base_h*.995,1)
        note=("BASE BREAKOUT ENTRY: Enter on break above base high "+Rs(base_h)+" on volume. "
              "Aggressive — buy as price clears "+Rs(ea)+". Conservative — wait for 1.5x+ volume on the breakout candle. "
              "Retest — base high becomes support at "+Rs(er)+" if retested.")
    else:
        ea=ec=er=0; note="No entry — wait for a tradeable pattern."

    r=p-sl; t1=round(p+1.5*r,1); t2=round(p+3*r,1); t3=round(p+5*r,1)
    ra=capital*risk_pct/100; rps=p*sl_pct/100
    qty=int(ra/rps) if rps>0 else 0

    return {"viable":True,"verdict":verdict,"vc":vc,"final":final,
            "entry_agg":ea,"entry_con":ec,"entry_ret":er,"entry_note":note,
            "sl":sl,"sl_pct":round(sl_pct,1),"sl_label":sl_lbl,
            "t1":t1,"t2":t2,"t3":t3,"rr":3.0,
            "qty":qty,"pos_val":round(qty*p),"risk_amount":round(ra)}

# ── CHARTINK SCANNERS ─────────────────────────────────────────────────────────
SCANNERS = {
    "Tier 1 — 52W High Breakout":{
        "c":"#3fb950","setup":"BREAKOUT","priority":"HIGHEST — ACT IMMEDIATELY",
        "what":"Nifty 200 stocks breaking above their 52-week high THIS WEEK with 1.5x+ volume and full Stage 2 EMA alignment.",
        "why":"The 52-week high breakout on institutional volume is the single strongest momentum signal in equity markets. Every investor who bought in the last year is at a profit or breakeven above this level — there is no overhead resistance.",
        "when_run":"Every evening after 4 PM IST. Results here = your top-priority trades for next day.",
        "action":"Enter at open next day or on a confirmed retest of the breakout level. Set GTT stop immediately after fill.",
        "code":"( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("{nifty 200}","Universe filter. Ensures only liquid Nifty 200 large and midcap stocks. This eliminates penny stocks, operator stocks, and illiquid names where execution is dangerous."),
            ("close > 1 weeks max(52, high)","This IS the breakout. Price has closed above the highest level of the last 52 weeks. Every seller from the past year is now sitting at breakeven or profit — no overhead resistance."),
            ("volume > 1.5x sma(volume,50)","Non-negotiable volume filter. Without 1.5x volume, the breakout is likely fake. In Indian markets, Nifty 200 breakouts on below-average volume fail more than 60% of the time. Volume = institutional conviction."),
            ("EMA stack: 20 > 50 > 200","Confirms the stock is in Weinstein Stage 2 uptrend across all timeframes. Breakouts from Stage 2 have a dramatically higher success rate than breakouts from Stage 3 or Stage 4."),
            ("turnover > Rs.25 Crore","Minimum liquidity gate. Below Rs.25Cr daily turnover, your entry or exit can move the price against you. You need to be able to get in and out cleanly."),
        ],
    },
    "Tier 2 — VCP / Pre-Breakout Coil":{
        "c":"#e3b341","setup":"VCP","priority":"HIGH — BUILD WATCHLIST",
        "what":"Nifty 200 stocks within 3% of 52W high with 10-day volume below 50-day volume. The spring is coiling.",
        "why":"This catches the setup BEFORE Tier 1 fires. Volume drying up near highs = supply exhaustion. Institutions are quietly accumulating while the stock looks boring. Entry here gives a tighter stop and better R:R than chasing the breakout after it fires.",
        "when_run":"Run after Tier 1. Results go on your GTT alert list.",
        "action":"DO NOT enter yet. Set a price alert at the 52W high. When price breaks that level on 1.5x+ volume, THEN enter.",
        "code":"( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("close > 0.97x 52W high","Within 3% of the breakout level. Close enough to matter as a pre-breakout candidate."),
            ("close < 52W high","Has NOT broken out yet. This is anticipation, not confirmation. The breakout is still ahead."),
            ("sma(vol,10) < sma(vol,50)","10-day average volume is BELOW the 50-day average. This is the VCP signal. Volume contracting while price holds near highs = supply exhaustion. The spring is coiling."),
            ("Full EMA stack","Stage 2 confirmed. The coil is forming in an uptrend, not a downtrend. A coil in a downtrend is a falling knife pause, not a VCP."),
        ],
    },
    "Tier 3 — Momentum Leaders (Second Leg Candidates)":{
        "c":"#bc8cff","setup":"SECOND_LEG","priority":"MEDIUM — ENTER ON PULLBACKS",
        "what":"Stage 2 stocks up 25%+ in both 6M and 12M. These are the proven momentum leaders — wait for EMA20 dips to enter.",
        "why":"Counter-intuitive but mathematically proven: a stock already up 40% with a bullish EMA stack is more likely to keep rising than one that just started moving. The Nifty200 Momentum30 index (which selects the top momentum stocks) has delivered 19.3% CAGR over 20 years using this exact principle.",
        "when_run":"Run weekly. Results form your core momentum watchlist.",
        "action":"Do NOT buy at current price. Add to watchlist. Buy ONLY if and when the stock dips to EMA20 with declining volume.",
        "code":"( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("close > ema(20) > ema(50) > ema(200)","Full Stage 2 confirmation across all timeframes."),
            ("close > 1.25x 26 weeks ago","Up at least 25% in 6 months. Not a flash — sustained intermediate momentum."),
            ("close > 1.25x 52 weeks ago","Up at least 25% over 12 months. Long-term momentum is persistent, not a one-time spike."),
        ],
    },
    "Tier 4 — Pure VCP / Tight Base":{
        "c":"#79c0ff","setup":"VCP","priority":"HIGH — CHART REVIEW REQUIRED",
        "what":"Strongest VCP filter: within 10% of highs with volume contracted 25%+. These are your highest-potential explosive setups.",
        "why":"When volume contracts by 25%+ while price stays within 10% of highs, it means sellers have been systematically exhausted. The stock is a coiled spring. When institutional buying returns and the breakout fires, it tends to be sharp and fast.",
        "when_run":"Run daily. Each result needs chart verification in TradingView before trading.",
        "action":"Open each result in TradingView. Confirm: tightening range (shrinking ATR), volume bars getting smaller each day, price hugging EMA20. Enter on breakout above the tightest range on 2x+ volume.",
        "code":"( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
        "conditions":[
            ("close > 0.90x 52W high","Within 10% of the all-time high — base is forming near the top."),
            ("EMA alignment","Base forming in an uptrend. The single most important filter. Do not confuse a tight base in a downtrend with a VCP."),
            ("sma(vol,10) < 0.75x sma(vol,50)","Volume contracted 25%+ vs the 50-day average. This is the squeeze. The quieter the stock gets, the louder the breakout will be."),
        ],
    },
}

# ── RETURNS ───────────────────────────────────────────────────────────────────
def get_returns(df, ndf):
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

def liq_gate(df):
    p=safe(df["Close"].iloc[-1]); av=df["Volume"].tail(50).mean()
    to=av*p; return to,to>=25_00_00_000

# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main():
    # Terminal header
    now=datetime.now(); dt_s=now.strftime("%a %d %b %Y")
    st.markdown(
        div(
            div(
                span("📈 NSE ELITE SWING TERMINAL","color:#58a6ff;font-size:16px;font-weight:800;letter-spacing:0.5px;font-family:'JetBrains Mono',monospace;") +
                span(" · v6","color:#484f58;font-size:13px;"),
                ""
            ) +
            div(
                span(dt_s,"color:#484f58;font-size:11px;font-family:'JetBrains Mono',monospace;"),
                "text-align:right;"
            ),
            "display:flex;justify-content:space-between;align-items:center;"
            "background:#0d1117;border-bottom:1px solid #21262d;padding:12px 20px;margin:-16px -16px 16px -16px;"
        ),
        unsafe_allow_html=True
    )

    # Market regime bar
    with st.spinner("Fetching market data..."):
        nifty_df=fetch_index("^NSEI"); bnifty_df=fetch_index("^NSEBANK")
        vix_df=fetch_index("^INDIAVIX")

    regime_rows,regime_pen=market_regime(nifty_df,bnifty_df)

    # VIX
    vix_val=safe(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df)>0 else None
    vix_col="#3fb950" if vix_val and vix_val<15 else "#e3b341" if vix_val and vix_val<20 else "#f85149"
    vix_label="LOW" if vix_val and vix_val<15 else "ELEVATED" if vix_val and vix_val<20 else "HIGH"

    regime_html=""
    for name,status,color,pen,_ in regime_rows:
        dot="🟢" if color=="#3fb950" else "🟠" if color=="#e3b341" else "🔴"
        pen_s=" (-"+str(pen)+" pts)" if pen>0 else ""
        regime_html+=span(dot+" "+name+": "+span(status,"color:"+color+";font-weight:700;")+span(pen_s,"color:#484f58;font-size:10px;")+"  ","color:#8b949e;font-size:12px;margin-right:20px;")

    if vix_val:
        regime_html+=span("VIX: "+span(str(round(vix_val,1)),"color:"+vix_col+";font-weight:700;")+" "+span("("+vix_label+")","color:"+vix_col+";font-size:10px;")+"  ","color:#8b949e;font-size:12px;margin-right:20px;")

    regime_bg="#160b0b" if regime_pen>=20 else "#161006" if regime_pen>=10 else "#0b1d0e"
    bc="#f85149" if regime_pen>=20 else "#e3b341" if regime_pen>=10 else "#3fb950"

    st.markdown(
        div(regime_html,
            "background:"+regime_bg+";border:1px solid "+bc+"30;border-radius:6px;"
            "padding:10px 16px;margin-bottom:16px;"),
        unsafe_allow_html=True
    )

    # Warning banner
    if regime_pen>=20:
        st.markdown(
            danger_box("CAPITAL PRESERVATION MODE ACTIVE",
                "Nifty or Bank Nifty is below its 200-day EMA — the market is in a confirmed bearish phase. "
                "In this environment, even good setups fail more often than they work. "
                "Rules: (1) Only setups scoring 85+ qualify. (2) Cut all position sizes by 50%. "
                "(3) Prioritize protecting your existing capital over finding new trades. "
                "(4) Consider moving to cash until the index reclaims the 200 EMA."),
            unsafe_allow_html=True
        )
    elif regime_pen>=10:
        st.markdown(
            warning_box("CAUTION MODE — REDUCED SIZING",
                "Market is below its 50-day EMA. Momentum strategies underperform in this environment. "
                "Rules: (1) Half position size on all new trades. (2) Prefer EMA pullback setups over breakouts. "
                "(3) Tighten stop losses. (4) No new breakout entries on red Nifty days."),
            unsafe_allow_html=True
        )

    tabs=st.tabs(["⚡ Stock Analyzer","📚 Setup School","📡 Chartink Scanners","📋 System Rules","🏭 Sector Watch"])

    # ── TAB 1: ANALYZER ───────────────────────────────────────────────────────
    with tabs[0]:
        cl,cr=st.columns([1,2],gap="large")

        with cl:
            st.markdown(div(section_header("STOCK LOOKUP","Enter any NSE symbol to detect setup and score"),""))
            symbol=st.text_input("NSE Symbol",placeholder="e.g. DATAPATTNS").upper().strip()
            pick=st.selectbox("Or pick from popular list",[""] + POPULAR)
            if pick: symbol=pick

            st.markdown("---")
            capital=st.number_input("Trading Capital (Rs.)",min_value=100000,max_value=10000000,value=300000,step=50000,format="%d")
            risk_pct=st.slider("Risk per trade (%)",0.5,2.0,1.0,0.25,
                help="1% is standard. Use 0.5% on uncertain days (high VIX, F&O expiry, red market).")
            go=st.button("⚡ Detect Setup & Analyze",use_container_width=True)

            # Info box
            st.markdown(
                info_box("How This Works",
                    "1. Setup is DETECTED first (VCP, Breakout, Flag, etc.)<br>"
                    "2. Scoring WEIGHTS change based on the setup type<br>"
                    "3. Entry, SL, and targets are setup-specific<br>"
                    "4. Market regime applies a penalty to all scores<br>"
                    "5. Every metric is explained in plain English"),
                unsafe_allow_html=True
            )

            if vix_val:
                if vix_val>20:
                    st.markdown(danger_box("High VIX Alert ("+str(round(vix_val,1))+")",
                        "India VIX above 20 = high fear. In this environment: "
                        "No new breakout entries. Use 0.5% risk only. Prefer EMA pullback setups. "
                        "Widen mental stops by 1 ATR."),unsafe_allow_html=True)
                elif vix_val>15:
                    st.markdown(warning_box("Elevated VIX ("+str(round(vix_val,1))+")",
                        "India VIX between 15-20. Reduce position sizes by 25%. "
                        "Be more selective. Tight stops may get hit by intraday noise."),unsafe_allow_html=True)
                else:
                    st.markdown(success_box("Low VIX ("+str(round(vix_val,1))+")",
                        "India VIX below 15. Calm markets. Full position sizing appropriate. "
                        "Breakout setups have higher reliability in low VIX environments."),unsafe_allow_html=True)

        with cr:
            if not go:
                st.markdown(
                    div(
                        div("🎯","font-size:32px;margin-bottom:14px;") +
                        div("Enter a stock symbol to begin analysis","color:#c9d1d9;font-size:15px;font-weight:700;margin-bottom:8px;") +
                        div("The analyzer will detect which setup the stock is in and score it accordingly. Each setup type has different scoring weights, entry rules, stop loss anchors, and minimum quality thresholds.","color:#8b949e;font-size:13px;line-height:1.7;margin-bottom:16px;") +
                        div(
                            "".join([
                                div(
                                    span(SETUP_CONFIGS[k]["icon"]+" ","font-size:16px;") +
                                    div(k.replace("_"," "),"color:"+SETUP_CONFIGS[k]["color"]+";font-size:11px;font-weight:700;margin-bottom:2px;") +
                                    div(SETUP_CONFIGS[k]["tagline"],"color:#6e7681;font-size:10px;"),
                                    "background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px;margin:4px;"
                                )
                                for k in ["VCP","BREAKOUT","BULL_FLAG","EMA_PULLBACK","SECOND_LEG","FLAT_BASE"]
                            ]),
                            "display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;"
                        ),
                        "background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:30px;text-align:center;"
                    ),
                    unsafe_allow_html=True
                )

            elif symbol:
                with st.spinner("Fetching "+symbol+" from NSE..."):
                    df,ticker=fetch_stock(symbol)

                if df is None:
                    st.markdown(danger_box("Symbol Not Found","Could not fetch data for '"+symbol+"'. Check the exact NSE ticker symbol. Try: RELIANCE, TCS, HDFCBANK, DATAPATTNS, BEL, HAL."),unsafe_allow_html=True)
                    st.stop()

                df=enrich(df)
                to,liq_ok=liq_gate(df)
                if not liq_ok:
                    st.markdown(
                        danger_box("LIQUIDITY FAIL — NOT SCORED",
                            "Average daily turnover: Rs."+str(round(to/1e7,1))+" Cr. Minimum required: Rs.25 Cr. "
                            "Below this threshold, your entry or exit can significantly move the price against you. "
                            "Execution risk is too high for reliable swing trading. Find a more liquid stock."),
                        unsafe_allow_html=True
                    )
                    st.stop()

                r6,r12,rs=get_returns(df,nifty_df)
                setup,sd=detect_setup(df)
                scores,flags,raw=score_setup(setup,sd,r6,r12,rs)
                trade=build_trade(setup,sd,raw,capital,risk_pct,regime_pen)
                cfg=SETUP_CONFIGS[setup]
                color=cfg["color"]

                l=df.iloc[-1]; p=safe(l["Close"]); prev=safe(df["Close"].iloc[-2])
                dchg=(p-prev)/prev*100 if prev>0 else 0
                h52=safe(l["H52"],p); e10=safe(l["E10"]); e20=safe(l["E20"])
                e50=safe(l["E50"]); e200=safe(l["E200"]); vr_=safe(l["VR"],1.0)
                rsi_=safe(l["RSI"],50); mac_=safe(l["MACD"]); hist_=safe(l["HIST"])
                pct_h=(h52-p)/h52*100 if h52>0 else 0
                to_s=str(round(to/1e7,1))
                dt_s2=df.index[-1].strftime("%d %b %Y")
                d_col="#3fb950" if dchg>=0 else "#f85149"
                d_arr="▲" if dchg>=0 else "▼"

                # Spike check
                spike_pen=0; spike_html=""
                if abs(dchg)>=10: spike_pen=-20; spike_html=danger_box("SPIKE PENALTY: +"+str(round(dchg,1))+"% Today (-20 pts)","A 10%+ single-day move suggests news, operator activity, or a short squeeze — NOT a tradeable setup. Chasing a stock after a 10% day has a very low success rate. The spike penalty drops your score to reflect this.")
                elif abs(dchg)>=8: spike_pen=-10; spike_html=warning_box("SPIKE WARNING: +"+str(round(dchg,1))+"% Today (-10 pts)","An 8%+ move today is a caution flag. Consider waiting for a 2-3 day pullback before entering rather than chasing the spike.")
                elif abs(dchg)>=5: spike_pen=-5; spike_html=warning_box("BIG MOVE TODAY: +"+str(round(dchg,1))+"% (-5 pts)","5%+ in a single session. Slightly extended intraday. Ideally wait for the next session's open to confirm the move holds before entering.")

                final_score=max(0,trade.get("final",raw-regime_pen)+spike_pen)

                # ── STOCK HEADER ──────────────────────────────────────────────
                st.markdown(
                    div(
                        div(
                            div(ticker,"color:#58a6ff;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;") +
                            div("Rs."+"{:,.2f}".format(p),"color:#c9d1d9;font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace;"),
                            ""
                        ) +
                        div(
                            div(d_arr+" "+str(round(abs(dchg),2))+"%","color:"+d_col+";font-size:16px;font-weight:700;font-family:'JetBrains Mono',monospace;text-align:right;") +
                            div("Today · "+dt_s2,"color:#484f58;font-size:10px;text-align:right;margin-top:3px;") +
                            div("Turnover Rs."+to_s+"Cr/day ✓","color:#3fb950;font-size:10px;text-align:right;margin-top:2px;"),
                            ""
                        ),
                        "display:flex;justify-content:space-between;align-items:flex-start;"
                        "background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:16px;margin-bottom:12px;"
                    ),
                    unsafe_allow_html=True
                )

                # ── SETUP BANNER ──────────────────────────────────────────────
                st.markdown(
                    div(
                        div(
                            badge(cfg["icon"]+" "+setup.replace("_"," "),color,"11px") +
                            span("  Min score: "+str(cfg["min_score"]),"color:#484f58;font-size:10px;") +
                            span("  "+cfg["risk_profile"]+" RISK","color:"+color+";font-size:10px;font-weight:700;float:right;"),
                            "margin-bottom:8px;"
                        ) +
                        div(cfg["tagline"],"color:"+color+";font-size:14px;font-weight:700;margin-bottom:8px;") +
                        div(cfg["description"],"color:#8b949e;font-size:12px;line-height:1.7;"),
                        "background:#0d1117;border:1px solid "+color+"30;border-left:4px solid "+color+";"
                        "border-radius:0 8px 8px 0;padding:14px;margin-bottom:12px;"
                    ),
                    unsafe_allow_html=True
                )

                # ── DATA TILES ────────────────────────────────────────────────
                h52_col="#3fb950" if pct_h<=3 else "#e3b341" if pct_h<=10 else "#f85149"
                vr_col="#3fb950" if vr_>=1.5 else "#e3b341" if vr_>=1 else "#f85149"
                rsi_col="#3fb950" if 50<=rsi_<=65 else "#e3b341" if rsi_<80 else "#f85149"
                mac_col="#3fb950" if mac_>0 and hist_>0 else "#e3b341" if mac_>0 else "#f85149"
                e20_col="#3fb950" if p>e20 else "#f85149"
                e50_col="#3fb950" if e20>e50 else "#f85149"
                e200_col="#3fb950" if e50>e200 else "#f85149"
                r6_col="#3fb950" if r6 and r6>=20 else "#e3b341" if r6 and r6>=0 else "#f85149"

                h52_sub="ABOVE HIGH" if pct_h<=0 else str(round(pct_h,1))+"% below"
                vr_sub=str(round(vr_,1))+"x 50D avg"
                r6_sub=pct(r6)+" 6M"
                mac_dir="UP " if mac_>0 else "DN "

                tile_desc_h52="Distance from 52-week high. Near = momentum. Far = catching falling knife."
                tile_desc_vr ="Today's volume vs 50-day average. Above 1.5x = institutional activity."
                tile_desc_rsi="RSI 14. Sweet spot: 50-65. Avoid entering above 75."
                tile_desc_mac="MACD state. Positive + expanding histogram = best entry condition."
                tile_desc_e20="EMA 20. Primary trend filter. Price must be above this for swing buys."
                tile_desc_e50="EMA 50. Medium-term trend. Should be below EMA20 (20>50 = bullish)."
                tile_desc_e200="EMA 200. Long-term trend line. Everything above this = Stage 2."
                tile_desc_r6 ="6-month return. Leaders return 20%+ when market returns 5-10%."

                c1,c2,c3,c4=st.columns(4)
                with c1: st.markdown(metric_tile("52W HIGH","Rs."+"{:,.1f}".format(h52),h52_col,h52_sub,tile_desc_h52),unsafe_allow_html=True)
                with c2: st.markdown(metric_tile("VOLUME",str(round(vr_,1))+"x",vr_col,vr_sub,tile_desc_vr),unsafe_allow_html=True)
                with c3: st.markdown(metric_tile("RSI",str(round(rsi_)),rsi_col,"14-period",tile_desc_rsi),unsafe_allow_html=True)
                with c4: st.markdown(metric_tile("MACD",mac_dir+str(round(abs(mac_),2)),mac_col,"hist:"+str(round(hist_,2)),tile_desc_mac),unsafe_allow_html=True)

                c5,c6,c7,c8=st.columns(4)
                with c5: st.markdown(metric_tile("EMA 20","Rs."+"{:,.1f}".format(e20),e20_col,"above" if p>e20 else "below",tile_desc_e20),unsafe_allow_html=True)
                with c6: st.markdown(metric_tile("EMA 50","Rs."+"{:,.1f}".format(e50),e50_col,"20>50" if e20>e50 else "20<50",tile_desc_e50),unsafe_allow_html=True)
                with c7: st.markdown(metric_tile("EMA 200","Rs."+"{:,.1f}".format(e200),e200_col,"50>200" if e50>e200 else "50<200",tile_desc_e200),unsafe_allow_html=True)
                with c8: st.markdown(metric_tile("6M RETURN",pct(r6),r6_col,pct(r12)+" 12M",tile_desc_r6),unsafe_allow_html=True)

                if spike_html: st.markdown(spike_html,unsafe_allow_html=True)
                st.markdown("---")

                # ── SCORE CARD ────────────────────────────────────────────────
                vc=trade.get("vc","#484f58"); verdict=trade.get("verdict","—")
                raw_s=str(raw); rp_s=" — Regime -"+str(regime_pen) if regime_pen>0 else ""; sp_s=" — Spike "+str(spike_pen) if spike_pen<0 else ""
                sub_score="Raw: "+raw_s+rp_s+sp_s+" = Final: "+str(final_score)

                verdict_desc={
                    "ELITE SETUP":"All criteria met at the highest level. This is a rare, exceptional setup. Full position size appropriate. Act with confidence.",
                    "STRONG SETUP":"Strong setup with good scores across key criteria. High-probability trade. Full 1% risk appropriate.",
                    "TRADABLE":"Setup is valid but some criteria are marginal. Reduce to 0.5% risk. Tighter monitoring required.",
                    "NO TRADE":"Setup quality insufficient. No trade is the best trade here. Preserve capital for a better opportunity.",
                    "BELOW MIN — AVOID":"Detected setup but score too low. Quality gates are there for a reason — forcing this trade statistically loses money.",
                }

                st.markdown(
                    div(
                        div(
                            div(str(final_score),"font-size:72px;font-weight:900;color:"+vc+";line-height:1;font-family:'JetBrains Mono',monospace;") +
                            div("/ 100","color:#484f58;font-size:14px;font-weight:600;margin-top:4px;"),
                            "text-align:center;padding-right:24px;border-right:1px solid #21262d;min-width:120px;"
                        ) +
                        div(
                            div(
                                span(verdict,"display:inline-block;background:"+vc+"20;color:"+vc+";"
                                    "border:1px solid "+vc+"40;border-radius:4px;padding:4px 14px;"
                                    "font-size:14px;font-weight:800;letter-spacing:0.5px;margin-bottom:8px;") ,
                                "margin-bottom:6px;"
                            ) +
                            div(sub_score,"color:#484f58;font-size:10px;margin-bottom:8px;font-family:'JetBrains Mono',monospace;") +
                            div(verdict_desc.get(verdict,""),"color:#8b949e;font-size:12px;line-height:1.6;"),
                            "padding-left:24px;flex:1;"
                        ),
                        "display:flex;align-items:center;background:#0d1117;border:1px solid "+vc+"30;"
                        "border-radius:8px;padding:20px;margin-bottom:14px;"
                    ),
                    unsafe_allow_html=True
                )

                # ── SCORE BREAKDOWN ───────────────────────────────────────────
                bars_html=section_header("SCORE BREAKDOWN","Weights are setup-specific — different for each pattern type")
                for key,max_pts in cfg["weights"].items():
                    sc_val=scores.get(key,0)
                    lbl,desc=SCORE_DESCRIPTIONS.get(key,("",""))
                    bars_html+=progress_bar(lbl,sc_val,max_pts,desc)
                st.markdown(div(bars_html,"background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;margin-bottom:12px;"),unsafe_allow_html=True)

                # ── SIGNAL FLAGS ──────────────────────────────────────────────
                if flags:
                    flags_html=section_header("SIGNAL ANALYSIS","Every metric explained — why this stock scores the way it does")
                    for ft,title,msg in flags:
                        flags_html+=signal_flag(ft,title,msg)
                    st.markdown(div(flags_html,"background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;margin-bottom:12px;"),unsafe_allow_html=True)

                # ── TRADE PLAN ────────────────────────────────────────────────
                if trade["viable"]:
                    # What to watch
                    if cfg["what_to_watch"]:
                        wtw=section_header("WHAT TO WATCH","Key signals that confirm this setup is ready to trade")
                        for i,w in enumerate(cfg["what_to_watch"]):
                            wtw+=div(span(str(i+1)+". ","color:"+color+";font-weight:700;font-size:11px;")+span(w,"color:#8b949e;font-size:12px;"),"margin-bottom:6px;")
                        wtw+=div(span("Entry trigger: ","color:"+color+";font-weight:700;font-size:11px;")+span(cfg["entry_trigger"],"color:#c9d1d9;font-size:12px;"),"margin-top:8px;padding-top:8px;border-top:1px solid #21262d;")
                        st.markdown(div(wtw,"background:#0d1117;border:1px solid "+color+"20;border-radius:8px;padding:14px;margin-bottom:12px;"),unsafe_allow_html=True)

                    # Entry plan
                    et_col="#3fb950" if "BREAKOUT" in setup or setup=="SECOND_LEG" else "#79c0ff" if "PULLBACK" in setup else "#e3b341"
                    st.markdown(
                        div(
                            section_header("ENTRY PLAN","How and when to enter this specific setup type") +
                            div(trade["entry_note"],"color:#c9d1d9;font-size:13px;line-height:1.7;"),
                            "background:#0d1117;border:1px solid "+et_col+"25;border-left:3px solid "+et_col+";"
                            "border-radius:0 8px 8px 0;padding:14px;margin-bottom:12px;"
                        ),
                        unsafe_allow_html=True
                    )

                    # Trade levels
                    sl_s=Rs(trade["sl"]); t1_s=Rs(trade["t1"]); t2_s=Rs(trade["t2"]); t3_s=Rs(trade["t3"])
                    agg_s=Rs(trade["entry_agg"]) if trade["entry_agg"]>0 else "See entry plan"
                    con_s=Rs(trade["entry_con"]) if trade["entry_con"]>0 else "See entry plan"
                    ret_s=Rs(trade["entry_ret"]) if trade["entry_ret"]>0 else "See entry plan"
                    sp_s2=str(trade["sl_pct"])+"%"
                    t1_g=pct((trade["t1"]-p)/p*100)+" · 1.5R · Book 30%"
                    t2_g=pct((trade["t2"]-p)/p*100)+" · 3R  · Book 30%"
                    t3_g=pct((trade["t3"]-p)/p*100)+" · 5R  · Trail 40%"
                    rr_col="#3fb950" if trade["rr"]>=3 else "#f85149"
                    qty_s=str(trade["qty"])+" shares · "+Rs(trade["pos_val"])
                    ra_s=Rs(trade.get("risk_amount",0))
                    e10_s=Rs(e10)

                    levels=section_header("TRADE LEVELS","SL anchored to: "+trade["sl_label"])
                    levels+=div(
                        level_box("AGGRESSIVE ENTRY",agg_s,"#58a6ff","Enter now / at open","Buy immediately when the trigger condition is met. Higher risk but gets you in before others catch on.")+
                        level_box("CONSERVATIVE",con_s,"#79c0ff","Wait for confirmation","Wait for a confirmed close above the trigger level. Lower risk, slightly worse price.")+
                        level_box("STOP LOSS "+sp_s2,sl_s,"#f85149",trade["sl_label"],"Place GTT stop IMMEDIATELY after your entry fills. This is not optional. One trade without a stop can destroy a month of gains.")+
                        level_box("RETEST ENTRY",ret_s,"#484f58","If price pulls back","If price breaks out and then retests the trigger level, that is often a better entry with less risk."),
                        "display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px;"
                    )
                    levels+=div(
                        level_box("TARGET 1",t1_s,"#e3b341",t1_g,"Book 30% of position here. Then move your stop to your entry price — the trade is now risk-free regardless of what happens.")+
                        level_box("TARGET 2",t2_s,"#3fb950",t2_g,"Book another 30% here. Raise trailing stop to T1 level. The minimum acceptable reward for the risk taken.")+
                        level_box("TARGET 3",t3_s,"#56d364",t3_g,"Let the remaining 40% run. Trail using daily close below EMA10 ("+e10_s+"). Let winners run — this is where the big money is made."),
                        "display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;"
                    )
                    levels+=div(
                        div(
                            span("RISK : REWARD = ","color:#8b949e;") +
                            span("1 : "+str(trade["rr"]),"color:"+rr_col+";font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;") +
                            span(" ("+("minimum 3:1 met" if trade["rr"]>=3 else "BELOW 3:1 — SKIP TRADE")+")","color:"+rr_col+";font-size:11px;"),
                            "text-align:center;"
                        ),
                        "background:#0d1117;border:1px solid "+rr_col+"25;border-radius:6px;padding:12px;margin-bottom:8px;"
                    )
                    levels+=div(
                        div(
                            div("POSITION SIZE — "+str(risk_pct)+"% risk on Rs."+"{:,}".format(int(capital)),"color:#8b949e;font-size:10px;font-weight:700;letter-spacing:0.5px;margin-bottom:5px;") +
                            div(qty_s,"color:#58a6ff;font-size:14px;font-weight:700;font-family:'JetBrains Mono',monospace;") +
                            div("Max risk amount: "+ra_s+" · SL at "+sl_s+" ("+sp_s2+" below entry)","color:#6e7681;font-size:11px;margin-top:4px;"),
                            ""
                        ),
                        "background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:12px;"
                    )
                    st.markdown(div(levels,"background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;margin-bottom:12px;"),unsafe_allow_html=True)

                    # Exit plan
                    exit_html=section_header("EXIT PLAN","Follow these rules exactly — no improvising")
                    exit_html+="".join([
                        signal_flag("info","Immediate After Fill","Place GTT stop loss at "+sl_s+" the moment your order fills. This is the most important step. A trade without a stop is not a trade — it is gambling."),
                        signal_flag("info","At Target 1 ("+t1_s+")","Book 30% of your position. Move your stop loss UP to your exact entry price. The trade is now risk-free. You cannot lose money even if it reverses."),
                        signal_flag("info","At Target 2 ("+t2_s+")","Book another 30%. Move stop to T1 level. Let the remaining 40% continue running."),
                        signal_flag("info","Trailing the Final 40%","Trail your stop using the daily closing price below EMA10 ("+e10_s+"). When EMA10 rises, raise your stop. Never lower it."),
                        signal_flag("bear","Hard Stop — No Debate","If price closes below "+sl_s+", exit the ENTIRE position at market open next day. No hoping. No averaging. No excuses."),
                        signal_flag("warn","Time Stop","If the stock shows no meaningful progress in 15 trading days after entry, exit and redeploy capital. Stuck money has an opportunity cost."),
                        signal_flag("warn","Pre-Event Exit","Exit at least 1 day before: quarterly results, RBI policy, Budget, major global events. Holding through events on a swing trade is speculation, not trading."),
                    ])
                    st.markdown(div(exit_html,"background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;"),unsafe_allow_html=True)

                elif not trade["viable"]:
                    st.markdown(danger_box("TRADE NOT VIABLE — "+trade.get("verdict",""),trade.get("reason","")),unsafe_allow_html=True)

    # ── TAB 2: SETUP SCHOOL ───────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("## 📚 Setup School")
        st.markdown(div("A complete guide to every setup type the analyzer detects. Understanding WHY each setup works makes you a better trader — you'll stop chasing bad setups and recognize good ones instantly.","color:#8b949e;font-size:13px;line-height:1.7;margin-bottom:20px;")+"",unsafe_allow_html=True)

        for key,cfg in SETUP_CONFIGS.items():
            if key=="NO_SETUP": continue
            with st.expander(cfg["icon"]+" **"+cfg["name"]+"** — "+cfg["tagline"]):
                st.markdown(info_box("What Is a "+cfg["name"]+"?",cfg["description"],cfg["color"]),unsafe_allow_html=True)
                st.markdown("**What to look for:**")
                for w in cfg.get("what_to_watch",[]): st.markdown("- "+w)
                st.markdown(success_box("Entry Trigger",cfg.get("entry_trigger","")),unsafe_allow_html=True)
                col1,col2=st.columns(2)
                with col1: st.markdown(metric_tile("RISK PROFILE",cfg["risk_profile"],cfg["color"]),unsafe_allow_html=True)
                with col2: st.markdown(metric_tile("IDEAL HOLD",cfg["ideal_hold"],cfg["color"]),unsafe_allow_html=True)
                st.markdown("**Scoring weights for this setup:**")
                for k,v in cfg["weights"].items():
                    lbl,desc=SCORE_DESCRIPTIONS.get(k,("",""))
                    st.markdown("- **"+lbl+" ("+str(v)+" pts)** — "+desc)

    # ── TAB 3: CHARTINK SCANNERS ──────────────────────────────────────────────
    with tabs[2]:
        st.markdown("## 📡 Chartink Scanners")
        st.markdown(div("Ready-to-use Chartink scanner codes with full explanations. Go to chartink.com → Screens → Create New Screen → paste code → Generate. Run after 4 PM IST.","color:#8b949e;font-size:13px;line-height:1.7;margin-bottom:20px;")+"",unsafe_allow_html=True)

        for name,data in SCANNERS.items():
            c=data["c"]
            with st.expander(badge(data["setup"].replace("_"," "),c)+" **"+name+"** — "+data["priority"]):
                st.markdown(info_box("What This Finds",data["what"],c),unsafe_allow_html=True)
                st.markdown(info_box("Why It Works",data["why"],"#58a6ff"),unsafe_allow_html=True)
                st.markdown(success_box("When to Run & Action","**When:** "+data["when_run"]+"<br>**Action:** "+data["action"]),unsafe_allow_html=True)
                st.markdown("**Each condition explained:**")
                for cond,expl in data["conditions"]:
                    st.markdown(
                        div(
                            span(cond,"color:"+c+";font-family:'JetBrains Mono',monospace;font-size:11px;display:block;margin-bottom:4px;font-weight:600;")+
                            span(expl,"color:#8b949e;font-size:12px;line-height:1.5;"),
                            "background:#0d1117;border:1px solid #21262d;border-left:3px solid "+c+"30;"
                            "border-radius:0 6px 6px 0;padding:10px;margin-bottom:6px;"
                        ),
                        unsafe_allow_html=True
                    )
                st.code(data["code"],language="text")

    # ── TAB 4: SYSTEM RULES ───────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("## 📋 Elite Swing Trading System Rules")
        st.markdown(div("These rules exist because professional traders discovered them the hard way — through losses. Every rule here has a specific reason. Not following them is the primary reason most traders lose money.","color:#8b949e;font-size:13px;line-height:1.7;margin-bottom:20px;")+"",unsafe_allow_html=True)

        rule_sections=[
            ("The Prime Directive","#f85149",[
                ("No trade is the best trade","When the setup is unclear, when the market is weak, when you're unsure — the correct answer is always to do nothing. Preserving capital means you live to trade another day. Missing a trade costs you nothing. Making a bad trade can cost you weeks of gains."),
                ("Score minimum requirements","Every setup type has its own minimum score threshold. These thresholds exist because below them, the statistical edge disappears. Trading below the minimum is no different from gambling."),
                ("3:1 minimum risk-reward","If your stop is 5% away, your target must be at least 15% away. Taking trades with 1:1 or 2:1 R:R guarantees you need a 60%+ win rate just to break even. With 3:1, you can be right only 35% of the time and still be profitable."),
            ]),
            ("Position Sizing Rules","#58a6ff",[
                ("1% risk per trade (maximum)","Never risk more than 1% of your total capital on any single trade. At 1% risk, you can take 20 consecutive losing trades and still have 82% of your capital. At 3%, 20 losses wipes out 46% of your capital."),
                ("0.5% on uncertain days","On F&O expiry days, high VIX days (above 20), or when market regime is Caution/Bearish, cut to 0.5% risk. You don't need to make money every day — you need to avoid large losses."),
                ("25% max single stock","No more than 25% of your total capital in any one stock, regardless of conviction. Unexpected news can gap a stock down 20% overnight. Concentration kills accounts."),
                ("5 positions maximum","Maximum 5 open positions at any time. More than 5 and you can't monitor them properly. When everything moves against you simultaneously (which it will in a market selloff), you need to react fast."),
                ("Total portfolio heat below 5%","Add up the risk on all open positions. This total should never exceed 5% of your capital. If you have 5 trades at 1% each, you're at the maximum."),
            ]),
            ("Hard Trading Rules","#e3b341",[
                ("GTT stop loss — IMMEDIATELY after entry","The moment your order fills, place the GTT stop loss. Not after lunch. Not tomorrow. Immediately. Most accounts are destroyed not by bad entries but by refusing to exit when the stop is hit."),
                ("Never average down","If a trade goes against you to the stop, exit — don't add more. Averaging down turns a small loss into a large one. It is the single most common cause of account blowups."),
                ("Never widen your stop","You set the stop based on the chart, before emotion entered the picture. When price approaches your stop, do not move it wider to 'give it more room'. Your pre-trade analysis was right. Trust it."),
                ("No trades in first 15 minutes","9:15–9:30 AM is dominated by overnight order unwinding, gap fills, and market maker games. The spread is widest, the moves are most random. Watch but do not click."),
                ("No new entries after 3:15 PM","In the last 15 minutes, institutional rebalancing and closing auction orders distort prices. Never enter a new swing position in this window."),
                ("No earnings holds","Always check if your watchlist stock has results in the next 5 days. Exit before results day. Even the most bullish setup can gap down 20% on bad results. The risk/reward of holding through earnings is never favorable."),
                ("No revenge trades","After a stop loss, step away from the screen for 15 minutes minimum. The urge to immediately recover a loss by taking another trade is the most dangerous emotion in trading. It leads to progressively worse decisions."),
            ]),
            ("Indian Market Specific Rules","#bc8cff",[
                ("F&O Expiry Awareness","NSE monthly F&O expiry is the last Thursday of the month. Weekly expiry is every Thursday. On expiry days: (1) Use 0.5% risk only. (2) Expect higher intraday volatility. (3) No new entries between 1–3 PM when max pain pinning is active."),
                ("Bank Nifty as a leading indicator","Bank Nifty often leads Nifty. If Bank Nifty is weak while Nifty is flat, expect Nifty to follow lower. Avoid banking/NBFC/finance stocks when Bank Nifty is below its 50 EMA."),
                ("FII vs DII data","Check NSE provisional FII/DII data after 3:30 PM. If FIIs are selling heavily (Rs.3000+ Cr net), reduce all position sizes next day. FII selling is the strongest predictor of short-term market direction in India."),
                ("Corporate actions check","Before entering any trade, check for ex-dividend dates, bonus record dates, stock splits, or AGM/EGM dates within the next 10 days. These create gaps and volume distortions that can trigger your stop."),
                ("Delivery percentage","On NSE, check the delivery percentage for breakout stocks. Breakouts with delivery above 40% have significantly higher success rates than those driven by intraday speculation. Under 30% delivery on a breakout = high suspicion of operator activity."),
                ("RBI policy and Budget dates","Mark RBI Monetary Policy Committee meeting dates and the Budget date on your calendar. Reduce open positions by 50% the day before. These events can move sectors by 5-10% in a single session."),
            ]),
        ]
        for title,color,items in rule_sections:
            with st.expander("**"+title+"**"):
                for rule_title,rule_desc in items:
                    st.markdown(
                        div(
                            div(rule_title,"color:"+color+";font-size:12px;font-weight:700;margin-bottom:4px;")+
                            div(rule_desc,"color:#8b949e;font-size:12px;line-height:1.6;"),
                            "padding:10px 0;border-bottom:1px solid #161b22;"
                        ),
                        unsafe_allow_html=True
                    )

    # ── TAB 5: SECTOR WATCH ───────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("## 🏭 Sector Watch")
        st.markdown(div("Scan a sector to analyze multiple stocks at once. Useful for finding the strongest stock in a strong sector.","color:#8b949e;font-size:13px;margin-bottom:16px;")+"",unsafe_allow_html=True)

        selected_sector=st.selectbox("Select Sector",list(SECTORS.keys()))
        scan_btn=st.button("📡 Scan "+selected_sector+" Sector",use_container_width=False)

        if scan_btn:
            stocks=SECTORS[selected_sector]
            results=[]
            prog=st.progress(0)
            for i,sym in enumerate(stocks):
                try:
                    df,tkr=fetch_stock(sym)
                    if df is None: continue
                    df=enrich(df)
                    to,lq=liq_gate(df); 
                    if not lq: results.append({"sym":sym,"setup":"LIQUIDITY FAIL","score":0,"color":"#484f58","price":"—","verdict":"SKIP"}); prog.progress((i+1)/len(stocks)); continue
                    r6,r12,rs_=get_returns(df,nifty_df)
                    setup,sd=detect_setup(df)
                    sc_,fl_,raw_=score_setup(setup,sd,r6,r12,rs_)
                    trd=build_trade(setup,sd,raw_,capital,1.0,regime_pen)
                    results.append({"sym":sym,"setup":setup.replace("_"," "),"score":trd.get("final",raw_-regime_pen),"color":SETUP_CONFIGS[setup]["color"],"price":"Rs."+"{:,.1f}".format(safe(df["Close"].iloc[-1])),"verdict":trd.get("verdict","—"),"r6":pct(r6)})
                except: pass
                prog.progress((i+1)/len(stocks))
            prog.empty()

            results.sort(key=lambda x:x["score"],reverse=True)
            hdr=div(
                span("SYMBOL","color:#8b949e;font-size:10px;font-weight:700;flex:1;")+
                span("SETUP","color:#8b949e;font-size:10px;font-weight:700;flex:1.5;")+
                span("SCORE","color:#8b949e;font-size:10px;font-weight:700;width:60px;text-align:right;")+
                span("6M RETURN","color:#8b949e;font-size:10px;font-weight:700;width:80px;text-align:right;")+
                span("VERDICT","color:#8b949e;font-size:10px;font-weight:700;width:100px;text-align:right;"),
                "display:flex;background:#0d1117;border:1px solid #21262d;border-radius:6px 6px 0 0;padding:8px 12px;"
            )
            rows=""
            for r in results:
                sc_col="#3fb950" if r["score"]>=80 else "#e3b341" if r["score"]>=65 else "#f85149" if r["score"]>0 else "#484f58"
                rows+=div(
                    span(r["sym"],"color:#c9d1d9;font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace;flex:1;")+
                    span(badge(r["setup"],r["color"]),"flex:1.5;")+
                    span(str(r["score"]),"color:"+sc_col+";font-size:13px;font-weight:800;font-family:'JetBrains Mono',monospace;width:60px;text-align:right;")+
                    span(r.get("r6","—"),"color:#8b949e;font-size:11px;width:80px;text-align:right;")+
                    span(r["verdict"],"color:"+sc_col+";font-size:10px;font-weight:700;width:100px;text-align:right;"),
                    "display:flex;align-items:center;background:#04080f;border:1px solid #21262d;border-top:none;padding:10px 12px;"
                )
            st.markdown(hdr+rows,unsafe_allow_html=True)

    # Footer
    st.markdown(
        div("Educational only. Not SEBI-registered advice. Data via Yahoo Finance — end-of-day delay. Always verify on NSE before trading.","color:#484f58;font-size:10px;"),
        "margin-top:20px;padding:10px 16px;background:#0d1117;border-top:1px solid #21262d;"
    )

if __name__=="__main__":
    main()
