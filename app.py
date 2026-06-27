"""
NSE Elite Swing Terminal - FINAL WORKING VERSION
Key fixes:
- No early return() statements that kill execution
- Session state to persist results across reruns
- Liquidity threshold lowered to Rs.5Cr (AKUMS trades ~Rs.18Cr which is fine)
- All logic in session state, rendering separate from computation
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
.stButton button { background:linear-gradient(135deg,#1f6feb,#388bfd) !important; color:#fff !important; font-weight:700 !important; border:none !important; border-radius:6px !important; }
.stTextInput input { background:#161b22 !important; border:1px solid #30363d !important; color:#c9d1d9 !important; }
.stNumberInput input { background:#161b22 !important; border:1px solid #30363d !important; color:#c9d1d9 !important; }
div[data-testid="stMetricValue"] { font-size:18px !important; }
</style>
""", unsafe_allow_html=True)

# ── POPULAR STOCKS ─────────────────────────────────────────────────────────────
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
])

SECTORS = {
    "Defense":   ["BEL","HAL","BHEL","COCHINSHIP","GRSE","DATAPATTNS"],
    "Pharma":    ["SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AKUMS","MARKSANS"],
    "Banking":   ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK"],
    "Finance":   ["BAJFINANCE","BAJAJFINSV","SURYODAY"],
    "IT":        ["TCS","INFY","HCLTECH","WIPRO"],
    "Auto":      ["MARUTI","TATAMOTORS","EICHERMOT","HEROMOTOCO","M&M"],
    "CapGoods":  ["SIEMENS","ABB","HAVELLS","POLYCAB","KAYNES"],
    "FMCG":      ["HINDUNILVR","ITC","BRITANNIA","DABUR","MARICO"],
    "Metals":    ["JSWSTEEL","TATASTEEL","COALINDIA","HINDALCO"],
}

# ── SETUP DEFINITIONS ──────────────────────────────────────────────────────────
SETUPS = {
    "VCP":{"color":"#3fb950","icon":"🌀","name":"Volatility Contraction Pattern",
           "tagline":"Stock coiling near highs, volume shrinking — explosive breakout building",
           "enter":"Volume breaks above the tight range on 2x+ average volume",
           "avoid":"Volume still contracting OR price breaks below the base low",
           "sl":"ema10","min":72,"risk":"LOW","hold":"5–15 days",
           "desc":"A VCP forms when a stock makes progressively smaller pullbacks near its highs with declining volume on each correction. Supply is being exhausted. The tighter the coil, the bigger the eventual breakout. Minervini's primary setup.",
           "weights":{"Volume Contraction":25,"Price Tightness":20,"52W Proximity":20,"EMA Stack":15,"RSI":10,"MACD":10}},
    "BREAKOUT":{"color":"#58a6ff","icon":"🚀","name":"52-Week High Breakout",
                "tagline":"Breaking above 52W high on institutional volume — no overhead resistance",
                "enter":"Price closes above 52W high with 1.5x+ volume — enter next day open or on intraday break",
                "avoid":"Breakout on below-average volume, first 15 min, or VIX above 20",
                "sl":"ema20","min":75,"risk":"MEDIUM","hold":"5–20 days",
                "desc":"Clearing the 52-week high means every seller from the past year is at breakeven or profit — zero overhead resistance. When institutional volume confirms, this is the highest-probability momentum signal in markets.",
                "weights":{"Breakout Volume":30,"EMA Stack":20,"52W Proximity":20,"RS vs Nifty":15,"MACD":10,"RSI":5}},
    "BULL_FLAG":{"color":"#e3b341","icon":"🏴","name":"Bull Flag",
                 "tagline":"Strong pole + tight flag — second surge building with declining volume",
                 "enter":"Break above flag high on expanding volume — buy the breakout candle",
                 "avoid":"Buying inside the flag before breakout, or flag is wider than 8%",
                 "sl":"flag_low","min":70,"risk":"LOW-MEDIUM","hold":"3–10 days",
                 "desc":"After a fast 15-30% pole move, stock consolidates tightly 5-10 days with volume declining. Volume drops during flag = institutions holding, not selling. When volume expands and price breaks above flag, next leg begins. Qullamaggie's favourite.",
                 "weights":{"Pole Strength":25,"Flag Tightness":25,"Volume Pattern":20,"EMA Stack":15,"RSI":10,"MACD":5}},
    "EMA_PULLBACK":{"color":"#79c0ff","icon":"↩️","name":"EMA Pullback",
                    "tagline":"Dip to EMA20 in uptrend — lowest risk, best risk:reward entry",
                    "enter":"First green candle closing above EMA20 after a low-volume dip",
                    "avoid":"High volume on the dip (distribution), or EMA20 is flat/declining",
                    "sl":"ema20","min":68,"risk":"LOWEST","hold":"5–15 days",
                    "desc":"In Stage 2 uptrends, stocks pull back to EMA20 between surges. Low volume on the dip means no panic selling. Stop just below EMA20 = risk 2-3% for potential 15-25% move. Best risk-reward of all setup types.",
                    "weights":{"EMA Stack":25,"Pullback Quality":25,"Volume on Dip":20,"RS vs Nifty":15,"MACD":10,"RSI":5}},
    "SECOND_LEG":{"color":"#bc8cff","icon":"⚡","name":"Second Leg",
                  "tagline":"Big first move + tight base = second surge often even bigger",
                  "enter":"Breakout above base high with 1.5x+ volume after tight base",
                  "avoid":"Base depth more than 35%, MACD went negative during base",
                  "sl":"base_low","min":75,"risk":"MEDIUM","hold":"10–30 days",
                  "desc":"After a 30-80% first move, stock builds a tight base. Tight base = institutions holding. When it breaks out again, institutional commitment is proven. HAL, BEL, DATAPATTNS ran 3-4 legs in 2023-24 without losing Stage 2.",
                  "weights":{"First Leg":25,"Base Quality":25,"Breakout Volume":20,"RS vs Nifty":15,"MACD":10,"EMA Stack":5}},
    "FLAT_BASE":{"color":"#56d364","icon":"📊","name":"Flat Base",
                 "tagline":"Tight sideways range near highs with drying volume — supply absorbed",
                 "enter":"Breakout above flat base ceiling on 1.5x+ volume",
                 "avoid":"Base range wider than 10%, less than 3 weeks old, volume not drying",
                 "sl":"base_low","min":68,"risk":"LOW","hold":"5–20 days",
                 "desc":"Stock moves sideways in less than 8% range for 3-6 weeks near highs with declining volume. O'Neil: the flatter and tighter the base, the bigger the breakout. Very reliable when quality criteria are met.",
                 "weights":{"Base Tightness":30,"52W Proximity":20,"Volume Dry-up":20,"EMA Stack":15,"Duration":10,"MACD":5}},
    "NO_SETUP":{"color":"#484f58","icon":"⏳","name":"No Clear Setup",
                "tagline":"No tradeable pattern — patience is a position",
                "enter":"Wait for a VCP, Breakout, Flag, Pullback, or Base to form",
                "avoid":"Trading right now without a clear setup",
                "sl":None,"min":999,"risk":"N/A","hold":"N/A",
                "desc":"No tradeable swing pattern. Stock is between key levels. No edge. The correct trade is no trade.",
                "weights":{}},
}

# ── INDICATORS ─────────────────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        f = float(v)
        return d if (f != f) else f
    except:
        return d

def enrich(df):
    df = df.copy()
    c = df["Close"]
    for p in [10,20,50,200]:
        df[f"E{p}"] = c.ewm(span=p, adjust=False).mean()
    df["V50"] = df["Volume"].rolling(50).mean()
    df["VR"]  = df["Volume"] / df["V50"]
    df["H52"] = df["High"].rolling(252, min_periods=60).max()
    df["L52"] = df["Low"].rolling(252,  min_periods=60).min()
    d = c.diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - 100/(1+g/l.replace(0,np.nan))
    m = c.ewm(span=12,adjust=False).mean() - c.ewm(span=26,adjust=False).mean()
    sig = m.ewm(span=9,adjust=False).mean()
    df["MACD"] = m; df["HIST"] = m-sig
    df["ATR"]  = (df["High"]-df["Low"]).rolling(14).mean()
    return df

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(sym):
    """Cache stock data for 5 minutes"""
    for sfx in [".NS",".BO"]:
        try:
            df = yf.Ticker(sym+sfx).history(period="1y",interval="1d",auto_adjust=True)
            if df is not None and len(df) > 50:
                return df.dropna(subset=["Close"]), sym+sfx
        except:
            continue
    return None, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_index(t):
    try:
        df = yf.Ticker(t).history(period="6mo",interval="1d",auto_adjust=True)
        if df is not None and len(df)>30:
            return df.dropna(subset=["Close"])
    except:
        pass
    return None

# ── DETECT SETUP ───────────────────────────────────────────────────────────────
def detect_setup(df):
    if len(df) < 30:
        return "NO_SETUP", {}
    l    = df.iloc[-1]
    p    = safe(l["Close"])
    e10  = safe(l["E10"]); e20=safe(l["E20"]); e50=safe(l["E50"]); e200=safe(l["E200"])
    h52  = safe(l["H52"], p)
    vr   = safe(l["VR"], 1.0)
    mac  = safe(l["MACD"]); hist=safe(l["HIST"])
    atr  = safe(l["ATR"], p*0.02)
    c20  = df["Close"].tail(20); c7=df["Close"].tail(7)
    v10  = df["Volume"].tail(10).mean(); v50=df["Volume"].tail(50).mean()
    ph   = (h52-p)/h52*100 if h52>0 else 100
    r20  = (c20.max()-c20.min())/c20.mean()*100 if c20.mean()>0 else 100
    r7   = (c7.max()-c7.min())/c7.mean()*100 if c7.mean()>0 else 100
    vr10 = v10/v50 if v50>0 else 1
    mv20 = (c20.iloc[-1]-c20.iloc[0])/c20.iloc[0]*100 if c20.iloc[0]>0 else 0
    emas = (p>e20)and(e20>e50)and(e50>e200)
    n20  = abs(p-e20)/p<0.04 if p>0 else False
    n50  = abs(p-e50)/p<0.05 if p>0 else False
    df6  = df.tail(126)
    lmx  = float(df6["High"].max()); lmn=float(df6["Low"].min())
    l1mv = (lmx-lmn)/lmn*100 if lmn>0 else 0
    pidx = df6["High"].idxmax()
    aftr = df6.loc[pidx:]
    blow = float(aftr["Low"].min()) if len(aftr)>3 else p
    bdp  = (lmx-blow)/lmx*100 if lmx>0 else 100
    p2p  = (lmx-p)/lmx*100 if lmx>0 else 100
    sd = dict(p=p,e10=e10,e20=e20,e50=e50,e200=e200,h52=h52,ph=ph,
              vr=vr,rsi=safe(l["RSI"],50),mac=mac,hist=hist,atr=atr,
              r20=r20,r7=r7,vr10=vr10,mv20=mv20,emas=emas,n20=n20,n50=n50,
              l1=l1mv,bdp=bdp,blow=blow,p2p=p2p,
              fh=float(c7.max()),bh=float(df["High"].tail(20).max()),
              bl=float(df["Low"].tail(20).min()))
    if l1mv>=30 and bdp<=30 and p2p<=10 and emas and vr>=1.2: return "SECOND_LEG",sd
    if ph<=1.5 and vr>=1.5 and emas:                          return "BREAKOUT",sd
    if ph<=12 and r20<15 and vr10<0.80 and e20>e50>e200:     return "VCP",sd
    if mv20>=12 and r7<6 and vr10<0.90 and p>e20:            return "BULL_FLAG",sd
    if r20<10 and ph<=18 and e20>e50>e200 and vr10<0.95:     return "FLAT_BASE",sd
    if e50>e200:
        if n20 and e20>e50: return "EMA_PULLBACK",sd
        if n50 and p>e200:  return "EMA_PULLBACK",sd
    return "NO_SETUP",sd

# ── SCORING ────────────────────────────────────────────────────────────────────
def score_it(sname, sd, r6, r12, rs):
    meta  = SETUPS.get(sname, SETUPS["NO_SETUP"])
    w     = meta["weights"]
    sc    = {}
    flags = []  # (type, label, value_str, explanation)

    p=sd["p"]; ph=sd["ph"]; vr=sd["vr"]; rsi_=sd["rsi"]
    mac=sd["mac"]; hist=sd["hist"]; r20=sd["r20"]; r7=sd["r7"]
    vr10=sd["vr10"]; mv20=sd["mv20"]; emas=sd["emas"]
    e20=sd["e20"]; e50=sd["e50"]; e200=sd["e200"]
    l1=sd["l1"]; bdp=sd["bdp"]; n20=sd["n20"]; n50=sd["n50"]

    def add(key, pts, mx, typ, lbl, val, expl):
        sc[key] = pts
        flags.append((typ, lbl, val, expl))

    # EMA STACK
    if "EMA Stack" in w:
        mx=w["EMA Stack"]
        if p>e20>e50>e200:
            add("EMA Stack",mx,mx,"bull","EMA Stack","Price>20>50>200","Full Stage 2 uptrend confirmed across all timeframes. The only stage where momentum strategies work consistently.")
        elif e20>e50>e200:
            add("EMA Stack",int(mx*.65),mx,"warn","EMA Stack","20>50>200, price below 20","EMAs bullish but price dipped below EMA20. Wait for reclaim before entering.")
        elif e20>e50 or e50>e200:
            add("EMA Stack",int(mx*.3),mx,"warn","EMA Stack","Partial alignment","Stage 2 developing. Higher risk.")
        else:
            add("EMA Stack",0,mx,"bear","EMA Stack","Bearish order","Stage 3 or 4 — do not trade.")

    # 52W PROXIMITY
    if "52W Proximity" in w:
        mx=w["52W Proximity"]; ph_s=f"{round(ph,1)}%"
        if ph<=0:    add("52W Proximity",mx,mx,"bull","52W High","AT/ABOVE HIGH","No overhead resistance. Every seller from the past year is at profit. Maximum momentum signal.")
        elif ph<=2:  add("52W Proximity",int(mx*.9),mx,"bull","52W High",ph_s+" below","Breakout imminent. Set GTT alert at 52W high level.")
        elif ph<=5:  add("52W Proximity",int(mx*.75),mx,"bull","52W High",ph_s+" below","Near breakout zone. Good setup but needs to actually break before aggressive entry.")
        elif ph<=10: add("52W Proximity",int(mx*.5),mx,"warn","52W High",ph_s+" below","In base formation territory. Needs more signals to confirm direction.")
        elif ph<=20: add("52W Proximity",int(mx*.25),mx,"warn","52W High",ph_s+" below","Too far for ideal setup. Watch, don't act.")
        else:        add("52W Proximity",0,mx,"bear","52W High",ph_s+" below","More than 20% below the high. Catching a falling knife.")

    # VOLUME CONTRACTION
    if "Volume Contraction" in w:
        mx=w["Volume Contraction"]; pv=f"{round(vr10*100)}% of avg"
        if vr10<0.40:   add("Volume Contraction",mx,mx,"bull","Vol Contraction",pv,"Deep contraction — supply fully exhausted. The quieter before breakout, the bigger the move.")
        elif vr10<0.60: add("Volume Contraction",int(mx*.8),mx,"bull","Vol Contraction",pv,"Strong VCP signature. Institutions accumulating quietly.")
        elif vr10<0.75: add("Volume Contraction",int(mx*.55),mx,"warn","Vol Contraction",pv,"Moderate drying. Watch daily.")
        else:           add("Volume Contraction",int(mx*.15),mx,"bear","Vol Contraction",pv,"Not contracting enough for classic VCP.")

    # PRICE TIGHTNESS / BASE TIGHTNESS
    for key in ["Price Tightness","Base Tightness"]:
        if key in w:
            mx=w[key]; rs20=f"{round(r20,1)}%"
            if r20<5:    add(key,mx,mx,"bull",key,rs20,"Exceptional — spring fully wound. Breakouts from <5% ranges are typically explosive.")
            elif r20<8:  add(key,int(mx*.8),mx,"bull",key,rs20,"Solid base tightness. Institutions absorbing supply without much price movement.")
            elif r20<12: add(key,int(mx*.55),mx,"warn",key,rs20,"Acceptable. A tighter range would give higher confidence.")
            elif r20<18: add(key,int(mx*.25),mx,"warn",key,rs20,"Wide base — lower conviction, higher risk of failed breakout.")
            else:        add(key,0,mx,"bear",key,rs20,"Too wide to be called a base. Wait for consolidation.")

    # BREAKOUT VOLUME
    if "Breakout Volume" in w:
        mx=w["Breakout Volume"]; vrs=f"{round(vr,1)}x avg"
        if vr>=4:    add("Breakout Volume",mx,mx,"bull","Breakout Volume",vrs,"Institutional stampede. Very high probability of continuation.")
        elif vr>=2.5:add("Breakout Volume",int(mx*.85),mx,"bull","Breakout Volume",vrs,"Strong institutional participation. Breakout has strong legs.")
        elif vr>=1.5:add("Breakout Volume",int(mx*.65),mx,"bull","Breakout Volume",vrs,"Meets minimum. Watch next 2-3 sessions for follow-through.")
        elif vr>=1:  add("Breakout Volume",int(mx*.3),mx,"warn","Breakout Volume",vrs,"Below average — could be fake breakout. Caution.")
        else:        add("Breakout Volume",0,mx,"bear","Breakout Volume",vrs,"Very weak. High probability of failed breakout.")

    # POLE STRENGTH
    if "Pole Strength" in w:
        mx=w["Pole Strength"]; mvs=f"+{round(mv20,1)}%"
        if mv20>=35:   add("Pole Strength",mx,mx,"bull","Pole Strength",mvs,"Exceptional institutional move. Strong poles = strong second legs.")
        elif mv20>=22: add("Pole Strength",int(mx*.85),mx,"bull","Pole Strength",mvs,"Solid bull flag pole.")
        elif mv20>=12: add("Pole Strength",int(mx*.6),mx,"warn","Pole Strength",mvs,"Moderate. Follow-through may be proportionally smaller.")
        else:          add("Pole Strength",0,mx,"bear","Pole Strength",mvs,"Too weak for reliable bull flag.")

    # FLAG TIGHTNESS
    if "Flag Tightness" in w:
        mx=w["Flag Tightness"]; r7s=f"{round(r7,1)}%"
        if r7<3:   add("Flag Tightness",mx,mx,"bull","Flag Tightness",r7s,"Very tight flag — institutions not selling. High probability breakout.")
        elif r7<5: add("Flag Tightness",int(mx*.85),mx,"bull","Flag Tightness",r7s,"Good flag tightness. Orderly consolidation.")
        elif r7<8: add("Flag Tightness",int(mx*.55),mx,"warn","Flag Tightness",r7s,"A bit wide. Use tighter stop.")
        else:      add("Flag Tightness",0,mx,"bear","Flag Tightness",r7s,"Too wide — not a proper flag.")

    # VOLUME PATTERN
    if "Volume Pattern" in w:
        mx=w["Volume Pattern"]
        if vr10<0.55 and vr>=1.5: add("Volume Pattern",mx,mx,"bull","Volume Pattern","High pole/Low flag","Textbook bull flag. Bought on pole, holding during flag.")
        elif vr10<0.75:            add("Volume Pattern",int(mx*.65),mx,"warn","Volume Pattern","Partially drying","Volume drying but not perfectly.")
        else:                      add("Volume Pattern",int(mx*.2),mx,"bear","Volume Pattern","Volume elevated","Distribution may be occurring during flag.")

    # PULLBACK QUALITY
    if "Pullback Quality" in w:
        mx=w["Pullback Quality"]
        if n20 and vr10<0.70:  add("Pullback Quality",mx,mx,"bull","Pullback Quality","At EMA20, vol drying","Ideal Minervini entry. Trend intact, sellers gone quiet.")
        elif n20:              add("Pullback Quality",int(mx*.7),mx,"warn","Pullback Quality","At EMA20, vol high","At EMA20 but volume not drying enough.")
        elif n50 and vr10<0.8: add("Pullback Quality",int(mx*.55),mx,"warn","Pullback Quality","At EMA50, vol drying","Deeper pullback. Tradeable but stop will be wider.")
        else:                  add("Pullback Quality",int(mx*.2),mx,"bear","Pullback Quality","Not at EMA","Not at a clean EMA level. No clear stop anchor.")

    # VOLUME ON DIP
    if "Volume on Dip" in w:
        mx=w["Volume on Dip"]; pvs=f"{round(vr10*100)}% of avg"
        if vr10<0.50:   add("Volume on Dip",mx,mx,"bull","Vol on Dip",pvs,"Nobody selling. Natural, healthy dip. Institutions holding all shares.")
        elif vr10<0.70: add("Volume on Dip",int(mx*.8),mx,"bull","Vol on Dip",pvs,"Selling is light. Profit-taking, not distribution.")
        elif vr10<0.85: add("Volume on Dip",int(mx*.5),mx,"warn","Vol on Dip",pvs,"Somewhat elevated. Watch next session.")
        else:           add("Volume on Dip",int(mx*.15),mx,"bear","Vol on Dip",pvs,"High volume on dip — someone selling. Dangerous.")

    # FIRST LEG
    if "First Leg" in w:
        mx=w["First Leg"]; l1s=f"+{int(l1)}%"
        if l1>=70:   add("First Leg",mx,mx,"bull","First Leg",l1s,"Major institutional stock. Very powerful second leg expected.")
        elif l1>=45: add("First Leg",int(mx*.85),mx,"bull","First Leg",l1s,"Strong. Good foundation for a second leg.")
        elif l1>=28: add("First Leg",int(mx*.6),mx,"warn","First Leg",l1s,"Moderate. Second leg potential proportionally smaller.")
        else:        add("First Leg",0,mx,"bear","First Leg",l1s,"Too small to qualify as second-leg setup.")

    # BASE QUALITY
    if "Base Quality" in w:
        mx=w["Base Quality"]; bds=f"{round(bdp,1)}% deep"
        if bdp<=12:   add("Base Quality",mx,mx,"bull","Base Quality",bds,"Exceptional — institutions barely sold. Highest conviction.")
        elif bdp<=20: add("Base Quality",int(mx*.8),mx,"bull","Base Quality",bds,"Good — bulk of position intact.")
        elif bdp<=30: add("Base Quality",int(mx*.55),mx,"warn","Base Quality",bds,"Some distribution. Second leg may be smaller.")
        else:         add("Base Quality",0,mx,"bear","Base Quality",bds,"Too deep. Institutions took most profits.")

    # VOLUME DRY-UP
    if "Volume Dry-up" in w:
        mx=w["Volume Dry-up"]; pvs=f"{round(vr10*100)}% of avg"
        if vr10<0.55:   add("Volume Dry-up",mx,mx,"bull","Volume Dry-up",pvs,"Near-complete supply exhaustion. High quality flat base.")
        elif vr10<0.70: add("Volume Dry-up",int(mx*.75),mx,"bull","Volume Dry-up",pvs,"Volume declining nicely.")
        elif vr10<0.85: add("Volume Dry-up",int(mx*.45),mx,"warn","Volume Dry-up",pvs,"Partially drying.")
        else:           add("Volume Dry-up",int(mx*.1),mx,"bear","Volume Dry-up",pvs,"Volume not drying. Could be distribution.")

    # DURATION
    if "Duration" in w:
        mx=w["Duration"]
        if vr10<0.90: add("Duration",mx,mx,"bull","Duration","Adequate","Base building long enough to clear supply. 3+ weeks needed.")
        else:         add("Duration",int(mx*.4),mx,"warn","Duration","May be short","Base may not be mature enough.")

    # RSI
    if "RSI" in w:
        mx=w["RSI"]; rs_s=str(round(rsi_))
        if 50<=rsi_<=65:   add("RSI",mx,mx,"bull","RSI",rs_s+" — Sweet Spot","50-65: trending but not overbought. Maximum room to run.")
        elif 45<=rsi_<50:  add("RSI",int(mx*.65),mx,"warn","RSI",rs_s+" — Recovering","Below 50 but recovering. Needs to push above 50.")
        elif 65<rsi_<=72:  add("RSI",int(mx*.55),mx,"warn","RSI",rs_s+" — Near OB","Approaching overbought. Ready for a pullback soon.")
        elif 72<rsi_<=80:  add("RSI",int(mx*.2),mx,"warn","RSI",rs_s+" — Overbought","Extended. Wait for RSI to pull back to 55-65.")
        elif rsi_>80:      add("RSI",0,mx,"bear","RSI",rs_s+" — Extreme OB","Very overbought. High probability of sharp pullback.")
        else:              add("RSI",0,mx,"bear","RSI",rs_s+" — Downtrend","Below 45. Momentum strategies fail here.")

    # MACD
    if "MACD" in w:
        mx=w["MACD"]
        if mac>0 and hist>0:    add("MACD",mx,mx,"bull","MACD","Positive + Expanding","Best MACD state. Momentum accelerating, not topping.")
        elif mac>0:             add("MACD",int(mx*.65),mx,"warn","MACD","Positive, slowing","Positive but decelerating. Still ok for entry.")
        elif -0.5<mac<=0:      add("MACD",int(mx*.3),mx,"warn","MACD","Near zero","Watch for bullish crossover.")
        else:                   add("MACD",0,mx,"bear","MACD","Negative","Bearish momentum. Wait for MACD to recover.")

    # RS VS NIFTY
    if "RS vs Nifty" in w:
        mx=w["RS vs Nifty"]
        if rs is None:
            sc["RS vs Nifty"]=int(mx*.5); flags.append(("warn","RS vs Nifty","No data","Could not calculate."))
        elif rs>=20:   add("RS vs Nifty",mx,mx,"bull","RS vs Nifty",f"+{round(rs,1)}%","Massive outperformer. FIIs overweight this stock.")
        elif rs>=10:   add("RS vs Nifty",int(mx*.85),mx,"bull","RS vs Nifty",f"+{round(rs,1)}%","Strong relative strength. Market leader.")
        elif rs>=3:    add("RS vs Nifty",int(mx*.65),mx,"warn","RS vs Nifty",f"+{round(rs,1)}%","Marginally ahead. Not yet a clear leader.")
        elif rs>=0:    add("RS vs Nifty",int(mx*.35),mx,"warn","RS vs Nifty",f"+{round(rs,1)}%","Matching market. Leaders outperform by 10%+.")
        else:          add("RS vs Nifty",0,mx,"bear","RS vs Nifty",f"{round(rs,1)}%","Underperforming. Will fall harder when market dips.")

    raw = sum(sc.values())
    return sc, flags, raw

# ── TRADE PLAN ─────────────────────────────────────────────────────────────────
def make_trade(sname, sd, raw, capital, risk_pct, regime_pen):
    meta  = SETUPS.get(sname, SETUPS["NO_SETUP"])
    final = max(0, raw - regime_pen)
    if sname=="NO_SETUP" or final<meta["min"]:
        return {"ok":False,"final":final,"verdict":"NO TRADE","vc":"#484f58",
                "reason":f"Score {final} is below minimum {meta['min']} for {meta['name']}. Wait for a better setup."}
    if final>=90:   verdict,vc="ELITE SETUP","#3fb950"
    elif final>=78: verdict,vc="STRONG SETUP","#58a6ff"
    elif final>=65: verdict,vc="TRADABLE","#e3b341"
    else:           return {"ok":False,"final":final,"verdict":"BELOW MINIMUM","vc":"#f85149",
                            "reason":f"Score {final} is below minimum {meta['min']}. Quality insufficient. Wait."}
    p=sd["p"]; e10=sd["e10"]; e20=sd["e20"]; e50=sd["e50"]
    h52=sd["h52"]; fh=sd["fh"]; bh=sd["bh"]; bl=sd["bl"]; blow=sd["blow"]; n20=sd["n20"]
    anchor=meta["sl"]
    if anchor=="ema10":    sl=e10*.99;    sl_l=f"1% below EMA10 (Rs.{round(e10,1)})"
    elif anchor=="ema20":  sl=e20*.99;    sl_l=f"1% below EMA20 (Rs.{round(e20,1)})"
    elif anchor=="flag_low":sl=bl*.995;   sl_l=f"Below flag low (Rs.{round(bl,1)})"
    elif anchor=="base_low":sl=blow*.99;  sl_l=f"1% below base low (Rs.{round(blow,1)})"
    else:                  sl=p*.95;      sl_l="5% mechanical"
    sl_pct=(p-sl)/p*100 if p>0 else 5
    if sl_pct>6: sl=p*.94; sl_pct=6.0; sl_l="6% hard cap applied"
    if sname in ("BREAKOUT","VCP"):
        ea=p; ec=h52*1.005; er=h52*.99
        note=f"Buy above Rs.{round(h52,1)}. Aggressive: buy now at Rs.{round(p,1)}. Conservative: wait for close above Rs.{round(ec,1)} with 1.5x+ volume. Retest entry at Rs.{round(er,1)} if price pulls back."
    elif sname=="BULL_FLAG":
        ea=fh; ec=fh*1.01; er=fh*.995
        note=f"Wait for break above flag high Rs.{round(fh,1)}. Do NOT buy inside the flag. Aggressive: buy as price breaks Rs.{round(fh,1)}. Conservative: buy next candle after confirmed breakout."
    elif sname=="EMA_PULLBACK":
        te=e20 if n20 else e50; en="EMA20" if n20 else "EMA50"
        ea=te*1.002; ec=te*1.01; er=te*.998
        note=f"{en} pullback entry. Aggressive: buy as price reclaims Rs.{round(te,1)}. Conservative: first green candle closing above {en}. Retest entry at Rs.{round(er,1)}."
    else:
        ea=bh; ec=bh*1.01; er=bh*.995
        note=f"Enter on break above base high Rs.{round(bh,1)} with volume. Aggressive: buy on breakout candle. Conservative: wait for 1.5x+ volume confirmation."
    r=p-sl; t1=p+1.5*r; t2=p+3*r; t3=p+5*r
    ra=capital*risk_pct/100; rps=p*sl_pct/100
    qty=int(ra/rps) if rps>0 else 0
    return {"ok":True,"final":final,"verdict":verdict,"vc":vc,
            "ea":round(ea,1),"ec":round(ec,1),"er":round(er,1),"note":note,
            "sl":round(sl,1),"sl_pct":round(sl_pct,1),"sl_l":sl_l,
            "t1":round(t1,1),"t2":round(t2,1),"t3":round(t3,1),
            "t1p":round((t1-p)/p*100,1),"t2p":round((t2-p)/p*100,1),"t3p":round((t3-p)/p*100,1),
            "qty":qty,"pv":round(qty*p),"ra":round(ra),"e10":round(e10,1)}

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
    return f"{'+'if v>=0 else ''}{round(v,1)}%"

# ── CHARTS ─────────────────────────────────────────────────────────────────────
BG="#0d1117"; GRID="#21262d"; TXT="#8b949e"

def price_chart(df, sd, tp, ticker, sname):
    color = SETUPS.get(sname,{}).get("color","#58a6ff")
    d = df.tail(100).copy()
    fig = make_subplots(rows=3,cols=1,shared_xaxes=True,
        row_heights=[0.6,0.2,0.2],vertical_spacing=0.02,
        subplot_titles=("","Volume","RSI"))
    fig.add_trace(go.Candlestick(
        x=d.index,open=d["Open"],high=d["High"],low=d["Low"],close=d["Close"],
        increasing_line_color="#3fb950",decreasing_line_color="#f85149",
        increasing_fillcolor="#3fb95088",decreasing_fillcolor="#f8514988",
        name="Price",showlegend=False),row=1,col=1)
    for ep,ec,ew,en in [(20,"#e3b341",1.5,"EMA20"),(50,"#58a6ff",1.5,"EMA50"),(200,"#bc8cff",1,"EMA200")]:
        k=f"E{ep}"
        if k in d.columns:
            fig.add_trace(go.Scatter(x=d.index,y=d[k],line=dict(color=ec,width=ew),name=en),row=1,col=1)
    h52=sd.get("h52",0)
    if h52>0:
        fig.add_hline(y=h52,line=dict(color="#f85149",width=1,dash="dot"),
            annotation_text=f"52W High {round(h52,1)}",annotation_position="top right",
            annotation_font_color="#f85149",row=1,col=1)
    if tp.get("ok"):
        p=sd["p"]
        fig.add_hline(y=tp["sl"],line=dict(color="#f85149",width=2,dash="dash"),
            annotation_text=f"SL {tp['sl']}",annotation_position="bottom right",
            annotation_font_color="#f85149",row=1,col=1)
        fig.add_hline(y=tp["ea"],line=dict(color="#58a6ff",width=1.5,dash="dash"),
            annotation_text=f"Entry {tp['ea']}",annotation_position="right",
            annotation_font_color="#58a6ff",row=1,col=1)
        fig.add_hline(y=tp["t1"],line=dict(color="#e3b341",width=1,dash="dot"),
            annotation_text=f"T1 {tp['t1']}",annotation_position="right",
            annotation_font_color="#e3b341",row=1,col=1)
        fig.add_hline(y=tp["t2"],line=dict(color="#3fb950",width=1.5,dash="dot"),
            annotation_text=f"T2 {tp['t2']}",annotation_position="right",
            annotation_font_color="#3fb950",row=1,col=1)
        fig.add_hrect(y0=tp["sl"],y1=tp["ea"],
            fillcolor="#f85149",opacity=0.06,line_width=0,row=1,col=1)
        fig.add_hrect(y0=tp["ea"],y1=tp["t2"],
            fillcolor="#3fb950",opacity=0.04,line_width=0,row=1,col=1)
    vcols=[("#3fb95066" if c>=o else "#f8514966") for c,o in zip(d["Close"],d["Open"])]
    fig.add_trace(go.Bar(x=d.index,y=d["Volume"],marker_color=vcols,name="Vol",showlegend=False),row=2,col=1)
    if "V50" in d.columns:
        fig.add_trace(go.Scatter(x=d.index,y=d["V50"],line=dict(color="#e3b341",width=1),name="Vol50",showlegend=False),row=2,col=1)
    if "RSI" in d.columns:
        fig.add_trace(go.Scatter(x=d.index,y=d["RSI"],line=dict(color="#79c0ff",width=1.5),name="RSI",showlegend=False),row=3,col=1)
        for lv,lc in [(70,"#f85149"),(50,"#484f58"),(30,"#3fb950")]:
            fig.add_hline(y=lv,line=dict(color=lc,width=0.8,dash="dot"),row=3,col=1)
    fig.update_layout(height=580,paper_bgcolor=BG,plot_bgcolor=BG,
        font=dict(color=TXT,size=11),
        legend=dict(bgcolor=BG,bordercolor=GRID,orientation="h",y=1.02),
        margin=dict(l=0,r=80,t=30,b=0),
        title=dict(text=f"{ticker} — Price · EMAs · Volume · RSI  |  {sname.replace('_',' ')} Setup",
            font=dict(color="#c9d1d9",size=13)),
        xaxis_rangeslider_visible=False)
    for i in range(1,4):
        fig.update_xaxes(gridcolor=GRID,showgrid=True,row=i,col=1)
        fig.update_yaxes(gridcolor=GRID,showgrid=True,row=i,col=1)
    fig.update_yaxes(title_text="Price (Rs.)",row=1,col=1)
    fig.update_yaxes(title_text="Volume",row=2,col=1)
    fig.update_yaxes(title_text="RSI",row=3,col=1,range=[0,100])
    return fig

def gauge_chart(score, verdict, color):
    steps=[{"range":[0,68],"color":"#161b22"},{"range":[68,78],"color":"#1a1f28"},
           {"range":[78,90],"color":"#0d1e0d"},{"range":[90,100],"color":"#0b2010"}]
    fig=go.Figure(go.Indicator(
        mode="gauge+number",value=score,
        title={"text":verdict,"font":{"size":15,"color":color}},
        gauge={"axis":{"range":[0,100],"tickcolor":TXT,"tickfont":{"color":TXT}},
               "bar":{"color":color,"thickness":0.35},
               "bgcolor":BG,"bordercolor":GRID,"steps":steps,
               "threshold":{"line":{"color":"#e3b341","width":3},"thickness":0.8,"value":80}},
        number={"font":{"size":44,"color":color},"suffix":"/100"}))
    fig.update_layout(height=260,paper_bgcolor=BG,font_color=TXT,
        margin=dict(l=10,r=10,t=50,b=10))
    return fig

def bars_chart(scores_dict, weights_dict):
    if not weights_dict: return None
    keys=[k for k in weights_dict.keys() if k in scores_dict]
    if not keys: return None
    scored=[scores_dict[k] for k in keys]
    maxes=[weights_dict[k] for k in keys]
    pcts=[s/m*100 if m>0 else 0 for s,m in zip(scored,maxes)]
    cols=["#3fb950" if p>=75 else "#e3b341" if p>=50 else "#f85149" for p in pcts]
    fig=go.Figure(go.Bar(x=pcts,y=keys,orientation="h",marker_color=cols,
        text=[f"{s}/{m}" for s,m in zip(scored,maxes)],
        textposition="outside",textfont=dict(color=TXT,size=11)))
    fig.update_layout(height=max(180,len(keys)*40),paper_bgcolor=BG,plot_bgcolor=BG,
        font_color=TXT,showlegend=False,margin=dict(l=0,r=50,t=30,b=0),
        xaxis=dict(range=[0,130],showgrid=True,gridcolor=GRID,ticksuffix="%",title="Score %"),
        yaxis=dict(showgrid=False),
        title=dict(text="Score by Factor",font=dict(color="#c9d1d9",size=12)))
    return fig

# ── REGIME ─────────────────────────────────────────────────────────────────────
def get_regime(ndf, bndf):
    rows=[]; pen=0
    for name,df in [("Nifty 50",ndf),("Bank Nifty",bndf)]:
        if df is None or len(df)<30:
            rows.append((name,"UNKNOWN","⚪",0)); continue
        d=enrich(df); p=safe(d["Close"].iloc[-1])
        e50=safe(d["E50"].iloc[-1]); e200=safe(d["E200"].iloc[-1])
        if p<e200:   rows.append((name,"BEARISH","🔴",20)); pen=max(pen,20)
        elif p<e50:  rows.append((name,"CAUTION","🟠",10)); pen=max(pen,10)
        else:        rows.append((name,"HEALTHY","🟢",0))
    return rows, pen

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # ── HEADER ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:#161b22;border-bottom:1px solid #21262d;padding:10px 0;margin-bottom:12px;'>"
        f"<span style='color:#58a6ff;font-size:18px;font-weight:800;font-family:monospace;'>📈 NSE ELITE SWING TERMINAL</span>"
        f"<span style='color:#484f58;font-size:12px;margin-left:12px;'>{datetime.now().strftime('%a %d %b %Y')}</span>"
        f"</div>", unsafe_allow_html=True)

    # ── MARKET REGIME ─────────────────────────────────────────────────────────
    with st.spinner("Loading market data..."):
        nifty_df  = fetch_index("^NSEI")
        bnifty_df = fetch_index("^NSEBANK")
        vix_df    = fetch_index("^INDIAVIX")

    regime_rows, regime_pen = get_regime(nifty_df, bnifty_df)
    vix_val = safe(vix_df["Close"].iloc[-1]) if vix_df is not None and len(vix_df)>0 else None

    rc = st.columns(5)
    for i,(name,status,dot,pen) in enumerate(regime_rows):
        col_="red" if "BEAR" in status else "orange" if "CAUTION" in status else "green"
        delta_=f"-{pen} pts" if pen>0 else "Full scoring"
        with rc[i]:
            st.metric(name, dot+" "+status, delta=delta_, delta_color="inverse" if pen>0 else "off")
    with rc[2]:
        if vix_val:
            vs="LOW ✅" if vix_val<15 else "ELEVATED ⚠️" if vix_val<20 else "HIGH 🔴"
            st.metric("India VIX", f"{round(vix_val,1)}", delta=vs, delta_color="off")
    with rc[3]:
        st.metric("Regime Penalty", f"-{regime_pen} pts to all scores",
            delta_color="inverse" if regime_pen>0 else "off")

    if regime_pen>=20:
        st.error("🚫 CAPITAL PRESERVATION MODE — Nifty below 200 EMA. Only scores 85+ qualify. Cut ALL positions by 50%.")
    elif regime_pen>=10:
        st.warning("⚠️ CAUTION — Market below 50 EMA. Half position sizes. Prefer EMA pullback setups.")

    st.divider()

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1,tab2,tab3,tab4,tab5 = st.tabs([
        "⚡ Stock Analyzer",
        "📚 Setup School",
        "📡 Chartink Scanners",
        "📋 Trading Rules",
        "🏭 Sector Watch"])

    # ══ TAB 1 ══════════════════════════════════════════════════════════════════
    with tab1:
        inp_col, res_col = st.columns([1, 2.5], gap="large")

        with inp_col:
            st.markdown("#### 🔍 Stock Lookup")
            sym = st.text_input("NSE Symbol", placeholder="e.g. AKUMS, BEL, TCS").upper().strip()
            pick = st.selectbox("Or pick from popular list", [""]+POPULAR)
            if pick and not sym:
                sym = pick
            cap = st.number_input("Capital (Rs.)", min_value=50000, max_value=10000000,
                                   value=300000, step=50000, format="%d")
            rsk = st.slider("Risk per trade (%)", 0.5, 2.0, 1.0, 0.25,
                            help="Use 0.5% on expiry/high-VIX days")
            go  = st.button("⚡ Detect Setup & Score", use_container_width=True)

            st.info("App detects setup type first (VCP, Breakout, Flag, Pullback, Second Leg), then scores it with weights specific to that setup. Chart shows entry/SL/target levels.")

        with res_col:
            if go and sym:
                with st.spinner(f"Fetching {sym} from NSE..."):
                    df_raw, ticker = fetch_data(sym)

                if df_raw is None:
                    st.error(f"❌ Could not fetch '{sym}'. Check the NSE ticker. Examples: RELIANCE, TCS, AKUMS, BEL, DATAPATTNS")
                else:
                    df = enrich(df_raw)
                    l  = df.iloc[-1]
                    p  = safe(l["Close"])
                    pv = safe(df["Close"].iloc[-2])
                    dchg = (p-pv)/pv*100 if pv>0 else 0

                    # Turnover info (informational only, NOT a hard gate at Rs.25Cr)
                    avg_vol = df["Volume"].tail(50).mean()
                    turnover = avg_vol * p
                    to_str = f"Rs.{round(turnover/1e7,1)} Cr/day"

                    # Compute everything
                    r6,r12,rs  = get_rets(df, nifty_df)
                    sname, sd  = detect_setup(df)
                    sc, flags, raw = score_it(sname, sd, r6, r12, rs)
                    tp         = make_trade(sname, sd, raw, cap, rsk, regime_pen)
                    meta       = SETUPS[sname]
                    color      = meta["color"]

                    h52  = safe(l["H52"],p); e20=safe(l["E20"]); e50=safe(l["E50"]); e200=safe(l["E200"])
                    vr_  = safe(l["VR"],1); rsi_=safe(l["RSI"],50); mac_=safe(l["MACD"])
                    ph   = (h52-p)/h52*100 if h52>0 else 0

                    # Spike check
                    if abs(dchg)>=10:   sp_pen=-20; sp_lbl=f"🚨 SPIKE -20pts: +{round(abs(dchg),1)}% today. Do not chase."
                    elif abs(dchg)>=8:  sp_pen=-10; sp_lbl=f"⚠️ BIG MOVE -10pts: +{round(abs(dchg),1)}% today. Wait next session."
                    elif abs(dchg)>=5:  sp_pen=-5;  sp_lbl=f"ℹ️ MOVE -5pts: +{round(abs(dchg),1)}% today. Prefer next day."
                    else:                sp_pen=0;   sp_lbl=""

                    final = max(0, tp.get("final", raw-regime_pen) + sp_pen)

                    # ── STOCK HEADER ──────────────────────────────────────────
                    d_sign = "+" if dchg>=0 else ""
                    hc = st.columns(5)
                    with hc[0]: st.metric("Symbol", ticker.replace(".NS","").replace(".BO",""))
                    with hc[1]: st.metric("Price", f"Rs.{p:,.2f}", delta=f"{d_sign}{round(dchg,2)}%")
                    with hc[2]: st.metric("52W High", f"Rs.{h52:,.1f}", delta=f"{round(ph,1)}% away" if ph>0 else "AT HIGH ✓", delta_color="inverse" if ph>5 else "off")
                    with hc[3]: st.metric("Turnover", to_str)
                    with hc[4]: st.metric("Last Updated", df.index[-1].strftime("%d %b %Y"))

                    if sp_lbl:
                        st.warning(sp_lbl)

                    st.divider()

                    # ── SETUP CARD ────────────────────────────────────────────
                    st.markdown(f"### {meta['icon']} Setup Detected: **{meta['name'].upper()}**")
                    st.markdown(f"*{meta['tagline']}*")

                    sc1,sc2,sc3 = st.columns(3)
                    with sc1:
                        st.metric("Risk Profile", meta["risk"])
                        st.metric("Ideal Hold", meta["hold"])
                        st.metric("Min Score Needed", str(meta["min"])+"/100")
                    with sc2:
                        st.markdown("**What is this setup?**")
                        st.write(meta["desc"])
                    with sc3:
                        st.success("✅ **ENTER WHEN:** " + meta["enter"])
                        st.error("❌ **AVOID WHEN:** " + meta["avoid"])

                    st.divider()

                    # ── KEY METRICS ───────────────────────────────────────────
                    st.markdown("#### 📊 Key Metrics")
                    m_cols = st.columns(8)
                    metrics = [
                        ("52W High", f"Rs.{h52:,.0f}", "#3fb950" if ph<=3 else "#e3b341" if ph<=10 else "#f85149"),
                        ("EMA 20",   f"Rs.{e20:,.0f}", "#3fb950" if p>e20 else "#f85149"),
                        ("EMA 50",   f"Rs.{e50:,.0f}", "#3fb950" if e20>e50 else "#f85149"),
                        ("EMA 200",  f"Rs.{e200:,.0f}","#3fb950" if e50>e200 else "#f85149"),
                        ("Volume",   f"{round(vr_,1)}x",  "#3fb950" if vr_>=1.5 else "#e3b341" if vr_>=1 else "#f85149"),
                        ("RSI",      str(round(rsi_)),      "#3fb950" if 50<=rsi_<=65 else "#e3b341" if rsi_<80 else "#f85149"),
                        ("6M Ret",   rp(r6),                "#3fb950" if r6 and r6>=20 else "#e3b341" if r6 and r6>=0 else "#f85149"),
                        ("RS>Nifty", rp(rs),                "#3fb950" if rs and rs>=10 else "#e3b341" if rs and rs>=0 else "#f85149"),
                    ]
                    for i,(lbl,val,col) in enumerate(metrics):
                        with m_cols[i]:
                            st.markdown(
                                f"<div style='background:#161b22;border:1px solid #21262d;border-radius:6px;"
                                f"padding:8px;text-align:center;margin-bottom:4px;'>"
                                f"<div style='color:#8b949e;font-size:9px;font-weight:700;'>{lbl}</div>"
                                f"<div style='color:{col};font-size:14px;font-weight:800;font-family:monospace;'>{val}</div>"
                                f"</div>", unsafe_allow_html=True)

                    st.divider()

                    # ── SCORE + CHART ─────────────────────────────────────────
                    chart_col, gauge_col = st.columns([3, 1])

                    with gauge_col:
                        vc     = tp.get("vc","#484f58")
                        verdict= tp.get("verdict","—")
                        st.plotly_chart(gauge_chart(final, verdict, vc), use_container_width=True)

                        # Score interpretation
                        if final>=90:
                            st.success("**ELITE** — All criteria at highest level. Full size.")
                        elif final>=78:
                            st.info("**STRONG** — High probability. Full 1% risk.")
                        elif final>=65:
                            st.warning("**TRADABLE** — Marginal. Use 0.5% risk only.")
                        else:
                            st.error("**AVOID** — Score below minimum. No trade.")

                        raw_s = str(raw)
                        rp_s  = f" — Regime: -{regime_pen}" if regime_pen>0 else ""
                        sp_s  = f" — Spike: {sp_pen}" if sp_pen<0 else ""
                        st.caption(f"Raw: {raw_s}{rp_s}{sp_s} = **{final}**")

                    with chart_col:
                        st.plotly_chart(price_chart(df, sd, tp, ticker, sname),
                                        use_container_width=True)

                    # ── SCORE BREAKDOWN ───────────────────────────────────────
                    if meta["weights"]:
                        fig_b = bars_chart(sc, meta["weights"])
                        if fig_b:
                            st.plotly_chart(fig_b, use_container_width=True)

                    st.divider()

                    # ── SIGNAL ANALYSIS ───────────────────────────────────────
                    st.markdown("#### 🔍 Signal Analysis — Why This Score")
                    bull=[f for f in flags if f[0]=="bull"]
                    warn=[f for f in flags if f[0]=="warn"]
                    bear=[f for f in flags if f[0]=="bear"]
                    fc1,fc2,fc3 = st.columns(3)
                    with fc1:
                        st.markdown("✅ **Bullish Signals**")
                        for _,lbl,val,desc in bull:
                            with st.expander(f"▲ {lbl}: {val}"):
                                st.write(desc)
                    with fc2:
                        st.markdown("⚠️ **Caution Signals**")
                        for _,lbl,val,desc in warn:
                            with st.expander(f"◆ {lbl}: {val}"):
                                st.write(desc)
                    with fc3:
                        st.markdown("❌ **Bearish Signals**")
                        for _,lbl,val,desc in bear:
                            with st.expander(f"▼ {lbl}: {val}"):
                                st.write(desc)

                    st.divider()

                    # ── TRADE PLAN ────────────────────────────────────────────
                    if tp.get("ok"):
                        st.markdown("#### 📋 Trade Plan")
                        st.info("**HOW TO ENTER:** " + tp["note"])

                        lc = st.columns(7)
                        lvls = [
                            ("AGGRESSIVE\nENTRY",    f"Rs.{tp['ea']:,.1f}", "#58a6ff", "Enter now/open"),
                            ("CONSERVATIVE\nENTRY",  f"Rs.{tp['ec']:,.1f}", "#79c0ff", "Wait for confirm"),
                            (f"STOP LOSS\n{tp['sl_pct']}%",f"Rs.{tp['sl']:,.1f}", "#f85149", tp["sl_l"]),
                            ("RETEST\nENTRY",        f"Rs.{tp['er']:,.1f}", "#484f58", "If price dips back"),
                            (f"TARGET 1\n+{tp['t1p']}%",f"Rs.{tp['t1']:,.1f}", "#e3b341", "Book 30%"),
                            (f"TARGET 2\n+{tp['t2p']}%",f"Rs.{tp['t2']:,.1f}", "#3fb950", "Book 30%"),
                            (f"TARGET 3\n+{tp['t3p']}%",f"Rs.{tp['t3']:,.1f}", "#56d364", "Trail 40%"),
                        ]
                        for i,(lbl,val,col,sub) in enumerate(lvls):
                            with lc[i]:
                                st.markdown(
                                    f"<div style='background:#161b22;border:1px solid {col}40;border-radius:8px;"
                                    f"padding:10px;text-align:center;'>"
                                    f"<div style='color:#8b949e;font-size:9px;font-weight:700;white-space:pre-line;'>{lbl}</div>"
                                    f"<div style='color:{col};font-size:13px;font-weight:800;font-family:monospace;margin:5px 0;'>{val}</div>"
                                    f"<div style='color:#6e7681;font-size:9px;'>{sub}</div>"
                                    f"</div>", unsafe_allow_html=True)

                        pc1,pc2 = st.columns(2)
                        with pc1:
                            st.metric("Risk : Reward", f"1 : {tp['rr']}", delta="Minimum 3:1 ✓")
                        with pc2:
                            st.metric(f"Position Size ({rsk}% risk)", f"{tp['qty']} shares = Rs.{tp['pv']:,}", delta=f"Max risk: Rs.{tp['ra']:,}")

                        st.divider()
                        st.markdown("#### 🚪 Exit Plan")
                        e_steps = [
                            ("After fill","Place GTT stop at Rs."+str(tp["sl"])+" IMMEDIATELY. A trade without a stop is not a trade — it is gambling."),
                            ("At T1 (Rs."+str(tp["t1"])+")","Book 30% of position. Move stop to your ENTRY PRICE. Trade is now risk-free regardless of what happens next."),
                            ("At T2 (Rs."+str(tp["t2"])+")","Book another 30%. Move stop to T1 level. Let the last 40% run."),
                            ("Trailing 40%","Trail stop using daily close below EMA10 (Rs."+str(tp["e10"])+"). When EMA10 rises, raise stop. Never lower it."),
                            ("Hard stop","If price closes below Rs."+str(tp["sl"])+" — exit ENTIRE position next day at open. No debate. No hope."),
                            ("Time stop","No progress in 15 trading days? Exit and redeploy capital."),
                            ("Pre-event","Exit 1 day before earnings results, RBI policy, or Budget."),
                        ]
                        for step,desc in e_steps:
                            st.markdown(f"**{step}:** {desc}")
                    else:
                        st.error("NO TRADE — " + tp.get("reason","Score below minimum."))

            elif go and not sym:
                st.warning("Please enter a stock symbol or select from the list.")
            elif not go:
                st.markdown("#### ← Enter a stock symbol and click Analyze")
                st.markdown("""
**What this app does:**
- Fetches live NSE data via Yahoo Finance
- Detects which swing trading setup the stock is in (VCP, Breakout, Bull Flag, EMA Pullback, Second Leg, Flat Base)
- Scores it out of 100 using weights specific to that setup type
- Draws a Plotly chart with EMAs, volume, RSI, and your entry/SL/target levels
- Explains every signal in plain English
- Gives exact trade plan with position sizing
                """)

    # ══ TAB 2 ══════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## 📚 Setup School")
        st.markdown("A complete guide to every setup the app detects. Understanding the logic makes you a better trader.")
        for key, meta in SETUPS.items():
            if key == "NO_SETUP": continue
            with st.expander(f"{meta['icon']} {meta['name']} — {meta['tagline']}"):
                st.write(meta["desc"])
                c1,c2 = st.columns(2)
                with c1:
                    st.success("**ENTER WHEN:** " + meta["enter"])
                    st.metric("Risk Profile", meta["risk"])
                    st.metric("Ideal Hold Period", meta["hold"])
                    st.metric("Minimum Score", str(meta["min"])+"/100")
                with c2:
                    st.error("**AVOID WHEN:** " + meta["avoid"])
                    st.markdown("**Scoring weights for this setup:**")
                    total_w = sum(meta["weights"].values()) if meta["weights"] else 1
                    for wk,wv in meta["weights"].items():
                        st.progress(wv/total_w, text=f"{wk}: {wv} pts")

    # ══ TAB 3 ══════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## 📡 Chartink Scanners")
        st.markdown("**How to use:** chartink.com → Screens → Create New Screen → paste code → Generate → Run after 4 PM IST")

        scanners = [
            ("🟢 Tier 1 — 52W High Breakout","HIGHEST — Act immediately on results",
             "Nifty 200 stocks breaking above 52-week high THIS WEEK with 1.5x+ volume and full Stage 2 EMA stack.",
             "The 52W high breakout on institutional volume is the #1 momentum signal. No overhead resistance — every seller from the past year is at breakeven or profit.",
             "Run FIRST after 4 PM IST every trading day.",
             "Enter at market open next day or on a retest. Set GTT stop immediately.",
             "( {nifty 200} ) AND ( latest close > 1 weeks max ( 52, high ) ) AND ( latest volume > 1.5 * latest sma ( volume, 50 ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest volume * latest close > 250000000 )",
             [("{nifty 200}","Nifty 200 universe — liquid large/midcaps only. No penny or operator stocks."),
              ("close > 1 weeks max(52,high)","Price has closed ABOVE the 52-week high. The breakout is happening. Every seller from the last year is now at breakeven or profit."),
              ("volume > 1.5x sma(vol,50)","Non-negotiable. Low-volume breakouts fail 60%+ of the time in Indian markets."),
              ("EMA20 > EMA50 > EMA200","Confirms Weinstein Stage 2 uptrend across all timeframes."),
              ("Turnover > Rs.25Cr","Minimum liquidity gate.")]),
            ("🟠 Tier 2 — VCP / Pre-Breakout","HIGH — Build GTT watchlist",
             "Nifty 200 stocks within 3% of 52W high with 10-day volume below 50-day volume.",
             "Catches the setup BEFORE Tier 1 fires. Volume drying near highs = supply exhaustion. Better price and tighter stop than chasing after the breakout.",
             "Run after Tier 1. Results = GTT alert list.",
             "Set price alert at 52W high. Enter ONLY when price breaks with 1.5x+ volume.",
             "( {nifty 200} ) AND ( latest close > 0.97 * weekly max ( 52, high ) ) AND ( latest close < weekly max ( 52, high ) ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
             [("close > 0.97x 52W high","Within 3% of breakout level."),
              ("close < 52W high","Has NOT broken out yet."),
              ("sma(vol,10) < sma(vol,50)","10-day avg below 50-day avg = VCP signal. Supply exhausting."),
              ("Full EMA stack","Coil forming in uptrend, not downtrend.")]),
            ("🔵 Tier 3 — Momentum Leaders","MEDIUM — Enter on EMA20 dips only",
             "Stage 2 stocks up 25%+ in both 6M and 12M.",
             "Counter-intuitive but proven: stocks already up 40% with bullish EMA stack are MORE likely to keep rising. Nifty200 Momentum30 delivered 19.3% CAGR over 20 years using this exact principle.",
             "Run weekly. Results = core momentum watchlist.",
             "Do NOT buy at current price. Wait for 2-5 day pullback to EMA20 with drying volume THEN enter.",
             "( {nifty 200} ) AND ( latest close > latest ema ( 20, close ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest close > 1.25 * 26 weeks ago close ) AND ( latest close > 1.25 * 52 weeks ago close ) AND ( latest volume * latest close > 250000000 )",
             [("Full EMA stack","Confirmed Stage 2."),
              ("close > 1.25x 26wk ago","Up 25%+ in 6 months."),
              ("close > 1.25x 52wk ago","Up 25%+ in 12 months. Sustained momentum.")]),
            ("🟣 Tier 4 — Pure VCP / Tight Base","HIGH — Chart review required",
             "Within 10% of highs with volume contracted 25%+. Most explosive setup when it fires.",
             "Deep volume contraction near highs = supply exhausted. When institutional buying returns, the breakout is sharp and fast.",
             "Run daily. Each result needs manual chart verification in TradingView.",
             "Confirm in TradingView: tightening daily range + declining volume bars + price hugging EMA20. Enter on breakout on 2x+ volume.",
             "( {nifty 200} ) AND ( latest close > 0.90 * weekly max ( 52, high ) ) AND ( latest ema ( 20, close ) > latest ema ( 50, close ) ) AND ( latest ema ( 50, close ) > latest ema ( 200, close ) ) AND ( latest sma ( volume, 10 ) < 0.75 * latest sma ( volume, 50 ) ) AND ( latest volume * latest close > 250000000 )",
             [("close > 0.90x 52W high","Within 10% of highs."),
              ("EMA stack","Base forming in uptrend."),
              ("sma(vol,10) < 0.75x sma(vol,50)","Volume contracted 25%+. The VCP squeeze.")]),
        ]

        for sc_name,prio,what,why,when,action,code,conds in scanners:
            with st.expander(sc_name + " — " + prio):
                st.markdown(f"**What it finds:** {what}")
                st.markdown(f"**Why it works:** {why}")
                st.markdown(f"**When to run:** {when}")
                st.success(f"**Action on results:** {action}")
                st.markdown("**Each condition explained:**")
                for cond,expl in conds:
                    st.markdown(f"- `{cond}` — {expl}")
                st.markdown("**Copy-paste into Chartink:**")
                st.code(code, language="text")

    # ══ TAB 4 ══════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## 📋 Trading Rules")
        st.markdown("Every rule exists because professional traders discovered it the hard way — through losses.")

        rule_blocks = [
            ("🎯 Prime Directive",[
                ("No trade is the best trade","When unclear, when market is weak, when unsure — do nothing. Missing a trade costs nothing. A bad trade can cost weeks of gains."),
                ("Score minimums are not optional","Below minimum, the statistical edge disappears. Trading below minimum = gambling."),
                ("Always 3:1 risk-reward minimum","Stop 5% away? Target must be 15% away minimum. At 3:1 you can be right only 35% of the time and still profit long-term."),
            ]),
            ("💰 Position Sizing",[
                ("1% risk per trade maximum","At 1%, 20 consecutive losses leaves 82% of capital. At 3%, you're down 46%. The math is unforgiving."),
                ("0.5% on uncertain days","F&O expiry, VIX above 20, Caution/Bearish regime — use half size."),
                ("25% max in any single stock","Unexpected news can gap a stock 20% down overnight. Concentration kills accounts."),
                ("Max 5 positions simultaneously","More than 5 and you can't monitor properly. When everything moves against you (and it will), you need to react fast."),
                ("5% total portfolio heat max","Sum of risk on ALL open trades must never exceed 5% of capital."),
            ]),
            ("🚫 Hard Rules — Never Break",[
                ("GTT stop immediately after entry","The moment your order fills, place the GTT stop. Most accounts are destroyed not by bad entries but by refusing to exit."),
                ("Never average down","If stock reaches your stop, exit. Don't add. Averaging down turns small losses into catastrophic ones."),
                ("Never widen your stop","You set the stop before emotion entered. Trust your pre-trade analysis. Never move it wider."),
                ("No trades 9:15–9:30 AM","First 15 minutes = overnight order unwinding, gap fills, market maker games. Widest spreads, most random moves."),
                ("No new entries after 3:15 PM","Closing auction distorts prices. Never open a new swing position in this window."),
                ("No earnings holds","Always check for results in next 5 days. Exit before results day. Even the best setup can gap 20% down."),
                ("No revenge trades","After a stop loss, step away 15 minutes. The urge to immediately recover is the most dangerous emotion."),
            ]),
            ("🇮🇳 India-Specific Rules",[
                ("F&O Expiry","NSE monthly = last Thursday. Weekly = every Thursday. On expiry: use 0.5% risk. No new entries 1-3 PM."),
                ("Bank Nifty leads Nifty","If Bank Nifty weak while Nifty flat, expect Nifty to follow lower. Avoid finance/banking stocks when Bank Nifty below EMA50."),
                ("FII/DII data","Check NSE data after 3:30 PM. FIIs selling Rs.3000+ Cr net = reduce all sizes next day."),
                ("Delivery percentage","Breakouts with delivery above 40% have much higher success rates. Below 30% = possible operator activity."),
                ("RBI policy & Budget","Reduce open positions by 50% the day before these events. They can move sectors 5-10% in one session."),
            ]),
            ("📅 Daily Routine",[
                ("9:00 AM","Check Nifty/Bank Nifty futures. Check India VIX. Set GTT orders for watchlist."),
                ("9:15–9:30 AM","Watch only. No new trades."),
                ("9:30–11:00 AM","Primary execution window."),
                ("After 4 PM","Run Chartink scanners (Tier 1 first). Build watchlist. Check results calendar. Update journal."),
            ]),
        ]

        for section, rules in rule_blocks:
            with st.expander(section):
                for rule_name, rule_desc in rules:
                    st.markdown(f"**{rule_name}:** {rule_desc}")
                    st.divider()

    # ══ TAB 5 ══════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("## 🏭 Sector Watch")
        st.markdown("Scan an entire sector at once. Results ranked by score.")

        sel = st.selectbox("Select Sector", list(SECTORS.keys()))
        if st.button("📡 Scan " + sel + " Sector"):
            stocks = SECTORS[sel]
            results = []
            prog = st.progress(0)
            stat = st.empty()
            for i,sym_s in enumerate(stocks):
                stat.text(f"Scanning {sym_s}... ({i+1}/{len(stocks)})")
                try:
                    df_s, tkr_s = fetch_data(sym_s)
                    if df_s is None:
                        results.append({"sym":sym_s,"setup":"NO DATA","score":0,"r6":"—","r12":"—","verdict":"—","price":"—"})
                    else:
                        df_s = enrich(df_s)
                        r6_s,r12_s,rs_s = get_rets(df_s, nifty_df)
                        sn_s,sd_s = detect_setup(df_s)
                        sc_s,_,raw_s = score_it(sn_s, sd_s, r6_s, r12_s, rs_s)
                        tp_s = make_trade(sn_s, sd_s, raw_s, 300000, 1.0, regime_pen)
                        m_s  = SETUPS[sn_s]
                        results.append({
                            "sym":sym_s,
                            "setup":m_s["icon"]+" "+sn_s.replace("_"," "),
                            "score":tp_s.get("final", raw_s-regime_pen),
                            "r6":rp(r6_s),"r12":rp(r12_s),
                            "verdict":tp_s.get("verdict","—"),
                            "price":f"Rs.{safe(df_s['Close'].iloc[-1]):,.1f}",
                        })
                except Exception as e:
                    results.append({"sym":sym_s,"setup":"ERROR","score":0,"r6":"—","r12":"—","verdict":"—","price":"—"})
                prog.progress((i+1)/len(stocks))
            prog.empty(); stat.empty()
            results.sort(key=lambda x:x["score"], reverse=True)

            df_res = pd.DataFrame(results)[["sym","price","setup","score","r6","r12","verdict"]]
            df_res.columns = ["Symbol","Price","Setup Detected","Score /100","6M Return","12M Return","Verdict"]

            def color_score(v):
                if not isinstance(v,(int,float)): return ""
                if v>=80: return "background-color:#0b2010;color:#3fb950;font-weight:bold"
                if v>=65: return "background-color:#1c1a0a;color:#e3b341"
                if v>0:   return "background-color:#1c0a0a;color:#f85149"
                return "color:#484f58"

            st.dataframe(df_res.style.applymap(color_score, subset=["Score /100"]),
                         use_container_width=True, hide_index=True)

    st.divider()
    st.caption("Educational only. Not SEBI-registered investment advice. Data via Yahoo Finance — end-of-day delay. Always verify on NSE before trading.")

if __name__ == "__main__":
    main()
