import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import json
import os
import time

# --- CONFIG ---
st.set_page_config(page_title="Market AI Mega v3 (Volume Locked)", layout="wide", page_icon="🛡️")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}
    .ce-box {background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;}
    .pe-box {background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

# --- PORTFOLIO SYSTEM ---
PORTFOLIO_FILE = "my_mega_portfolio.json"

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE): return {}
    with open(PORTFOLIO_FILE, "r") as f: return json.load(f)

def save_to_portfolio(symbol, qty, buy_price, category):
    data = load_portfolio()
    data[symbol] = {
        "qty": int(qty), 
        "buy_price": float(buy_price),
        "category": category
    }
    with open(PORTFOLIO_FILE, "w") as f: json.dump(data, f)

def remove_from_portfolio(symbol):
    data = load_portfolio()
    if symbol in data: del data[symbol]
    with open(PORTFOLIO_FILE, "w") as f: json.dump(data, f)

# --- STOCK LIST ---
NIFTY_LIQUID_LIST = [
    "^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "ITC.NS", 
    "BHARTIARTL.NS", "L&T.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "AXISBANK.NS", "MARUTI.NS", "TITAN.NS", 
    "ULTRACEMCO.NS", "ADANIENT.NS", "SUNPHARMA.NS", "BAJFINANCE.NS", "KOTAKBANK.NS", "WIPRO.NS", "HCLTECH.NS", 
    "TATASTEEL.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "M&M.NS", "COALINDIA.NS", "JSWSTEEL.NS", "BPCL.NS", 
    "EICHERMOT.NS", "DIVISLAB.NS", "DRREDDY.NS", "CIPLA.NS", "ASIANPAINT.NS", "BRITANNIA.NS", "NESTLEIND.NS", 
    "DLF.NS", "ZOMATO.NS", "PAYTM.NS", "HAL.NS", "BEL.NS", "IRCTC.NS", "VBL.NS", "JIOFIN.NS", "INDIGO.NS", 
    "DMART.NS", "ADANIPORTS.NS", "CHOLAFIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "IDFCFIRSTB.NS", 
    "BHEL.NS", "SAIL.NS", "VEDL.NS", "HAVELLS.NS", "SIEMENS.NS", "ABB.NS", "ZEEL.NS", "ASHOKLEY.NS", 
    "TVSMOTOR.NS", "MOTHERSON.NS", "MRF.NS", "BOSCHLTD.NS", "PIDILITIND.NS", "SHREECEM.NS", "ACC.NS", 
    "AMBUJACEM.NS", "INDUSINDBK.NS", "NAUKRI.NS", "TRENT.NS", "COLPAL.NS", "DABUR.NS"
]

# --- AI BRAIN (All Logic + Volume Lock) 🧠 ---
def analyze_stock_mega(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")
        if len(df) < 100: return None
        try: info = stock.info
        except: info = {}

        curr = df['Close'].iloc[-1]
        
        res = {
            "Symbol": symbol,
            "Price": round(curr, 2),
            "F_Jackpot": False,
            "F_Swing": False,
            "F_FO_CE": False,
            "F_FO_PE": False,
            "F_Double": False,
            "F_Tech": False,
            "F_Fund": False,
            "F_Trend": False,
            "Shape_Bull": None, 
            "Shape_Bear": None
        }

        # --- CALCULATIONS ---
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['EMA20']  = ta.ema(df['Close'], length=20)
        df['RSI']    = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_Sig'] = macd['MACDs_12_26_9']
        df['Vol_Avg'] = ta.sma(df['Volume'], length=10)

        # Values
        sma200 = df['SMA200'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        vol_curr = df['Volume'].iloc[-1]
        vol_avg = df['Vol_Avg'].iloc[-1]
        macd_val = df['MACD'].iloc[-1]
        macd_sig = df['MACD_Sig'].iloc[-1]

        # Fundamentals
        pe = info.get('trailingPE', 100)
        roe = info.get('returnOnEquity', 0)
        debt = info.get('debtToEquity', 100)
        
        # Booleans
        is_fund_strong = (0 < pe < 60 and roe > 0.12 and debt < 1.5)
        is_tech_strong = (curr > sma200 and 45 < rsi < 70)
        is_trend_up    = (curr > df['Close'].iloc[-20] * 1.05)
        is_vol_valid   = (vol_curr > vol_avg) # NEW: Volume Lock 🔒
        
        # 1. Jackpot (All 3 + Volume) - NOW STRICTEST
        if is_fund_strong and is_tech_strong and is_trend_up and is_vol_valid:
            res["F_Jackpot"] = True

        # 2. Rocket Swing (Breakout)
        high_20 = df['High'].tail(20).max()
        if curr >= high_20 * 0.98 and rsi > 60 and vol_curr > (vol_avg * 1.5):
            res["F_Swing"] = True

        # 3. F&O Signals
        if curr > df['EMA20'].iloc[-1] and rsi > 55 and macd_val > macd_sig:
            res["F_FO_CE"] = True
        elif curr < df['EMA20'].iloc[-1] and rsi < 45 and macd_val < macd_sig:
            res["F_FO_PE"] = True

        # 4. Others
        if is_fund_strong and is_tech_strong: res["F_Double"] = True
        if is_tech_strong and is_vol_valid: res["F_Tech"] = True # Tech + Vol
        if is_fund_strong: res["F_Fund"] = True
        if is_trend_up: res["F_Trend"] = True

        # 8. SHAPES
        lows = df['Low'].values
        highs = df['High'].values
        min_idx = argrelextrema(lows, np.less, order=5)[0]
        max_idx = argrelextrema(highs, np.greater, order=5)[0]
        
        if len(min_idx) >= 2:
             if abs(lows[min_idx[-1]] - lows[min_idx[-2]]) < (lows[min_idx[-1]] * 0.02):
                 res["Shape_Bull"] = "W-Pattern"
        if len(min_idx) >= 3 and not res["Shape_Bull"]:
             if lows[min_idx[-2]] < lows[min_idx[-1]] and lows[min_idx[-2]] < lows[min_idx[-3]]:
                 res["Shape_Bull"] = "Inverse H&S"
        
        if len(max_idx) >= 2:
            if abs(highs[max_idx[-1]] - highs[max_idx[-2]]) < (highs[max_idx[-1]] * 0.02):
                res["Shape_Bear"] = "M-Pattern"
        if len(max_idx) >= 3 and not res["Shape_Bear"]:
             if highs[max_idx[-2]] > highs[max_idx[-1]] and highs[max_idx[-2]] > highs[max_idx[-3]]:
                 res["Shape_Bear"] = "Head & Shoulders"

        return res
    except: return None

# --- UI ---
st.title("🛡️ Market AI Mega v3 (Safety Locked)")

tickers = NIFTY_LIQUID_LIST
if st.sidebar.checkbox("Use CSV File?"):
    up = st.sidebar.file_uploader("Upload CSV", type="csv")
    if up:
        d = pd.read_csv(up)
        c = next((col for col in d.columns if "SYMBOL" in col.upper()), None)
        if c: tickers = [f"{x.strip()}.NS" if not str(x).endswith(".NS") else x for x in d[c].dropna().unique()]

# --- PORTFOLIO ---
with st.expander("💼 My Mega Portfolio", expanded=False):
    my_port = load_portfolio()
    if my_port:
        p_list = []
        tot_inv, tot_curr = 0, 0
        for s, v in my_port.items():
            try: live_p = yf.Ticker(s).fast_info['last_price']
            except: live_p = v['buy_price']
            val_now = v['qty'] * live_p
            val_buy = v['qty'] * v['buy_price']
            pl = val_now - val_buy
            tot_inv += val_buy
            tot_curr += val_now
            p_list.append({"Stock": s, "Source": v.get('category','-'), "Qty": v['qty'], "Buy": v['buy_price'], "Live": round(live_p, 2), "P/L": round(pl, 2)})
        st.dataframe(pd.DataFrame(p_list).style.applymap(lambda x: 'color: green' if x > 0 else 'color: red', subset=['P/L']), use_container_width=True)
        c1,c2,c3=st.columns(3)
        c1.metric("Invested", f"₹{tot_inv:,.0f}")
        c2.metric("Current", f"₹{tot_curr:,.0f}")
        c3.metric("Net P/L", f"₹{tot_curr - tot_inv:,.0f}")
        rem_s = st.selectbox("Remove Stock:", list(my_port.keys()))
        if st.button("Remove Selected"):
            remove_from_portfolio(rem_s)
            st.rerun()
    else: st.info("Portfolio Empty.")

st.markdown("---")

# --- SCANNER ---
if st.button(f"🚀 START SAFE SCAN ({len(tickers)} Stocks)"):
    L1, L2, L3, L4, L5, L6, L7, L8, L9, L10 = [],[],[],[],[],[],[],[],[],[]
    bar = st.progress(0)
    status = st.empty()
    for i, t in enumerate(tickers):
        status.text(f"Scanning: {t}")
        d = analyze_stock_mega(t)
        if d:
            if d['F_Jackpot']: L1.append(d)
            if d['F_Swing']:   L2.append(d)
            if d['F_FO_CE']:   L3.append(d)
            if d['F_FO_PE']:   L4.append(d)
            if d['F_Double']:  L5.append(d)
            if d['F_Tech']:    L6.append(d)
            if d['F_Fund']:    L7.append(d)
            if d['F_Trend']:   L8.append(d)
            if d['Shape_Bull']: L9.append(d)
            if d['Shape_Bear']: L10.append(d)
        bar.progress((i+1)/len(tickers))
    bar.empty()
    status.success("✅ Safe Scan Complete!")
    st.session_state['mega_res'] = {"Jackpot": L1, "Swing": L2, "FO_CE": L3, "FO_PE": L4, "Double": L5, "Tech": L6, "Fund": L7, "Trend": L8, "Bull": L9, "Bear": L10}

# --- TABS ---
if 'mega_res' in st.session_state:
    res = st.session_state['mega_res']
    tabs = st.tabs(["🏆 Jackpot", "🚀 Swing", "🎰 CE", "🐻 PE", "🥈 Double", "📈 Tech", "💎 Fund", "🌊 Trend", "✨ Bull", "⚠️ Bear"])
    def render(data, name):
        if data:
            df = pd.DataFrame(data)
            cols = ["Symbol", "Price"]
            if "Shape_Bull" in df.columns: cols.append("Shape_Bull")
            if "Shape_Bear" in df.columns: cols.append("Shape_Bear")
            st.dataframe(df[cols], use_container_width=True)
            st.markdown(f"**➕ Add to {name} Portfolio**")
            c1, c2, c3 = st.columns([2, 1, 1])
            s = c1.selectbox("Stock", [x['Symbol'] for x in data], key=f"s_{name}")
            p = next((x['Price'] for x in data if x['Symbol'] == s), 0)
            q = c2.number_input("Qty", 1, 1000, 10, key=f"q_{name}")
            if c3.button("Add 🛒", key=f"b_{name}"):
                save_to_portfolio(s, q, p, name)
                st.success(f"Added {s}!")
                time.sleep(1)
                st.rerun()
        else: st.info("No stocks found.")

    with tabs[0]: render(res["Jackpot"], "Jackpot")
    with tabs[1]: render(res["Swing"], "Rocket Swing")
    with tabs[2]: 
        st.markdown("<div class='ce-box'>BUY CALL (CE)</div>", unsafe_allow_html=True)
        render(res["FO_CE"], "F&O CE")
    with tabs[3]: 
        st.markdown("<div class='pe-box'>BUY PUT (PE)</div>", unsafe_allow_html=True)
        render(res["FO_PE"], "F&O PE")
    with tabs[4]: render(res["Double"], "Double Power")
    with tabs[5]: render(res["Tech"], "Technical Only")
    with tabs[6]: render(res["Fund"], "Fundamental Only")
    with tabs[7]: render(res["Trend"], "Trend Only")
    with tabs[8]: render(res["Bull"], "Bull Shape")
    with tabs[9]: render(res["Bear"], "Bear Shape")