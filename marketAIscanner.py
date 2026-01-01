import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection # यह लाइन Google Sheets जोड़ने के लिए है
import time
import warnings
from datetime import datetime

# अपनी गूगल शीट का पूरा URL यहाँ डालें
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LrdWFwe4SFUtT9SjklGstwHUEHjZ0Ko48wdmDtp-h5I/edit?gid=0#gid=0"

# --- 1. SUPPRESS WARNINGS ---
warnings.filterwarnings('ignore')

# --- CONFIG ---
st.set_page_config(page_title="Market AI Scanner", layout="wide", page_icon="🧠")

# --- 🎨 UI CSS (FINAL PERFECT THEME) ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {background-color: #f1f5f9;}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff; 
        border-right: 1px solid #e2e8f0;
    }
    
    /* Text Colors */
    h1, h2, h3, p, label, .stMarkdown {color: #0f172a !important;}
    
    /* 📦 DASHBOARD CARD */
    .dashboard-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
    }
    
    /* 🏷️ HEADINGS */
    .card-title {
        font-size: 26px; font-weight: 900; color: #1e293b;
        margin-bottom: 20px; padding-bottom: 10px;
        border-bottom: 3px solid #3b82f6; 
        text-transform: uppercase; letter-spacing: 1px;
    }

    /* 🟢🔴 MARKET SENTIMENT BAR */
    .sentiment-bar {
        display: flex; justify-content: space-between;
        background: #1e293b; color: white; padding: 15px 25px;
        border-radius: 10px; margin-bottom: 25px; font-weight: bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .sent-item { font-size: 18px; }
    .sent-val-up { color: #4ade80; }
    .sent-val-down { color: #f87171; }

    /* Sector Box */
    .sector-box {
        background-color: #f8fafc; border: 1px solid #cbd5e1; 
        border-radius: 10px; padding: 12px; text-align: center; margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .sector-box:hover {transform: scale(1.03); border-color: #3b82f6;}
    .sec-name {font-size: 14px; font-weight: 800; color: #334155; display: block;}
    .sec-val {font-size: 15px; font-weight: 700;}

    /* 🟠 ORANGE BUTTON (SCAN) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #f97316, #ea580c) !important;
        color: white !important; border: none; font-size: 20px; height: 55px;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4);
    }
    div.stButton > button[kind="primary"]:hover {transform: scale(1.02);}

    /* 🔘 GREY BUTTONS (Others) */
    div.stButton > button[kind="secondary"] {
        background-color: #64748b !important; 
        color: white !important; border: none; font-weight: bold;
    }
    div.stButton > button[kind="secondary"]:hover {background-color: #475569 !important;}

    /* Small Portfolio Buttons */
    button[key^="p_chart_"], button[key^="s_"], button[key^="close_"] {
        height: 38px; font-size: 13px; padding: 0px 15px; margin-top: 0px !important;
    }

    /* Table Styling */
    .table-header {font-size: 14px; font-weight: 900; color: #475569; border-bottom: 2px solid #cbd5e1; padding-bottom: 8px;}
    .table-row {font-size: 15px; font-weight: 600; color: #1e293b; padding: 12px 0; border-bottom: 1px solid #f1f5f9;}
    
    /* Header */
    .main-header {
        text-align: center; padding: 25px; 
        background: linear-gradient(90deg, #1e293b 0%, #334155 100%);
        color: white !important; border-radius: 15px; margin-bottom: 30px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .main-header h1 {color: white !important; font-size: 36px; font-weight: 900; margin: 0;}
    
    /* Auto Qty Box */
    .qty-box {background-color: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;}

    /* 📊 TOTAL P/L FOOTER STYLE */
    .total-pl-container {
        background-color: #1e293b;
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin-top: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 2px solid #3b82f6;
    }
    .pl-label { font-size: 18px; font-weight: 700; }
    .pl-value { font-size: 24px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- BACKEND ---
# Google Sheets के साथ कनेक्शन स्थापित करना
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_from_sheets():
    # अपनी असली Google Sheet का लिंक यहाँ डालें
    MY_SHEET = "https://docs.google.com/spreadsheets/d/1LrdWFwe4SFUtT9SjklGstwHUEHjZ0Ko48wdmDtp-h5I/edit?gid=0#gid=0"
    
    # यहाँ हमने 'spreadsheet=MY_SHEET' जोड़ दिया है
    holdings_df = conn.read(spreadsheet=MY_SHEET, worksheet="Portfolio", ttl=0)
    balance_df = conn.read(spreadsheet=MY_SHEET, worksheet="Balance", ttl=0)
    # बैलेंस को नंबर में बदलना
    current_balance = float(balance_df.iloc[0, 0])
    
    # होल्डिंग्स को डिक्शनरी में बदलना ताकि पुराना कोड सही चले
    h_dict = {}
    if not holdings_df.empty:
        for _, row in holdings_df.iterrows():
            h_dict[row['Symbol']] = {
                'qty': int(row['Qty']),
                'buy_price': float(row['Buy_Price']),
                'category': str(row['Category']),
                'date': str(row['Date'])
            }
    return {"balance": current_balance, "holdings": h_dict}

if 'portfolio' not in st.session_state: 
    st.session_state['portfolio'] = load_data_from_sheets()
for idx in ["Nifty", "Sensex", "BankNifty", "FinNifty", "Bankex"]:
    if f'show_{idx}' not in st.session_state: st.session_state[f'show_{idx}'] = False

# ==========================================
# 📋 STOCK LISTS (MULTI-LINE)
# ==========================================
STOCK_LIST_PART_1 = [
    "NIFTYBEES.NS", "BANKBEES.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "L&T.NS", "HINDUNILVR.NS",
    "TATAMOTORS.NS", "AXISBANK.NS", "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ADANIENT.NS", "SUNPHARMA.NS", "BAJFINANCE.NS", "KOTAKBANK.NS",
    "WIPRO.NS", "HCLTECH.NS", "TATASTEEL.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "M&M.NS", "COALINDIA.NS", "JSWSTEEL.NS", "BPCL.NS",
    "EICHERMOT.NS", "DIVISLAB.NS", "DRREDDY.NS", "CIPLA.NS", "ASIANPAINT.NS", "BRITANNIA.NS", "NESTLEIND.NS", "DLF.NS", "ZOMATO.NS",
    "PAYTM.NS", "HAL.NS", "BEL.NS", "IRCTC.NS", "VBL.NS", "JIOFIN.NS", "INDIGO.NS", "DMART.NS", "ADANIPORTS.NS", "CHOLAFIN.NS",
    "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "IDFCFIRSTB.NS", "BHEL.NS", "SAIL.NS", "VEDL.NS", "HAVELLS.NS", "SIEMENS.NS", "ABB.NS",
    "ZEEL.NS", "ASHOKLEY.NS", "TVSMOTOR.NS", "MOTHERSON.NS", "MRF.NS", "BOSCHLTD.NS", "PIDILITIND.NS", "SHREECEM.NS", "ACC.NS",
    "AMBUJACEM.NS", "INDUSINDBK.NS", "NAUKRI.NS", "TRENT.NS", "COLPAL.NS", "DABUR.NS", "GODREJCP.NS", "BERGEPAINT.NS", "MARICO.NS",
    "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "ALKEM.NS", "LUPIN.NS", "AUROPHARMA.NS", "BIOCON.NS", "TORNTPHARM.NS", "MFSL.NS", "MAXHEALTH.NS",
    "APOLLOHOSP.NS", "JUBLFOOD.NS", "DEVYANI.NS", "PIIND.NS", "UPL.NS", "SRF.NS", "NAVINFLUOR.NS", "AARTIIND.NS", "DEEPAKNTR.NS",
    "ATGL.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "TATAPOWER.NS", "JSWENERGY.NS", "NHPC.NS", "SJVN.NS", "TORNTPOWER.NS", "PFC.NS",
    "RECLTD.NS", "IOB.NS", "UNIONBANK.NS", "INDIANB.NS", "UCOBANK.NS", "MAHABANK.NS", "CENTRALBK.NS", "PSB.NS", "SBICARD.NS"
]

STOCK_LIST_PART_2 = [
    "BAJAJHLDNG.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIPRULI.NS", "LICI.NS", "GICRE.NS", "NIACL.NS", "MUTHOOTFIN.NS", "MANAPPURAM.NS",
    "M&MFIN.NS", "SHRIRAMFIN.NS", "SUNDARMFIN.NS", "POONAWALLA.NS", "ABCAPITAL.NS", "L&TFH.NS", "PEL.NS", "DELHIVERY.NS", "NYKAA.NS",
    "POLICYBZR.NS", "IDEA.NS", "INDUSTOWER.NS", "TATACOMM.NS", "PERSISTENT.NS", "LTIM.NS", "KPITTECH.NS", "COFORGE.NS", "MPHASIS.NS",
    "LTTS.NS", "TATAELXSI.NS", "ORACLEFIN.NS", "CYIENT.NS", "ZENSARTECH.NS", "SONACOMS.NS", "TIINDIA.NS", "UNO.NS", "PRESTIGE.NS",
    "OBEROIRLTY.NS", "PHOENIXLTD.NS", "BRIGADE.NS", "SOBHA.NS", "GODREJPROP.NS", "RVNL.NS", "IRCON.NS", "RITES.NS", "RAILTEL.NS",
    "TITAGARH.NS", "JINDALSTEL.NS", "HINDALCO.NS", "NMDC.NS", "NATIONALUM.NS", "HINDCOPPER.NS", "APLAPOLLO.NS", "RATNAMANI.NS",
    "WELCORP.NS", "JSL.NS", "VOLTAS.NS", "BLUESTARCO.NS", "KAJARIACER.NS", "CERA.NS", "ASTRAL.NS", "POLYCAB.NS", "KEI.NS", "DIXON.NS",
    "CROMPTON.NS", "WHIRLPOOL.NS", "BATAINDIA.NS", "RELAXO.NS", "PAGEIND.NS", "KPRMILL.NS", "TRIDENT.NS", "RAYMOND.NS", "ABFRL.NS",
    "MANYAVAR.NS", "METROBRAND.NS", "BIKAJI.NS", "VBL.NS", "AWL.NS", "PATANJALI.NS", "EMAMILTD.NS", "JYOTHYLAB.NS", "FLUOROCHEM.NS",
    "LINDEINDIA.NS", "SOLARINDS.NS", "CASTROLIND.NS", "OIL.NS", "PETRONET.NS", "GSPL.NS", "IGL.NS", "MGL.NS", "GUJGASLTD.NS",
    "GAIL.NS", "HINDPETRO.NS", "IOC.NS", "MRPL.NS", "CHENNPETRO.NS", "CUMMINSIND.NS", "THERMAX.NS", "SKFINDIA.NS", "TIMKEN.NS",
    "SCHAEFFLER.NS", "AIAENG.NS", "ELGIEQUIP.NS", "KIRLOSENG.NS", "SUZLON.NS", "INOXWIND.NS", "BEML.NS", "MAZDOCK.NS", "COCHINSHIP.NS"
]

STOCK_LIST_PART_3 = [
    "GRSE.NS", "BDL.NS", "ASTRAMICRO.NS", "MTARTECH.NS", "DATAPATTNS.NS", "LALPATHLAB.NS", "METROPOLIS.NS", "SYNGENE.NS", "VIJAYA.NS",
    "KIMS.NS", "RAINBOW.NS", "MEDANTA.NS", "ASTERDM.NS", "NH.NS", "FORTIS.NS", "GLENMARK.NS", "IPCALAB.NS", "JBCHEPHARM.NS",
    "AJANTPHARM.NS", "NATCOPHARM.NS", "PFIZER.NS", "SANOFI.NS", "ABBOTINDIA.NS", "GLAXO.NS", "ASTRAZEN.NS", "ERIS.NS", "GRANULES.NS",
    "LAURUSLABS.NS", "FSL.NS", "REDINGTON.NS", "BSOFT.NS", "MASTEK.NS", "INTELLECT.NS", "TANLA.NS", "ROUTE.NS", "JUSTDIAL.NS",
    "AFFLE.NS", "HAPPSTMNDS.NS", "LATENTVIEW.NS", "MAPMYINDIA.NS", "RATEGAIN.NS", "NAZARA.NS", "EASEMYTRIP.NS", "CARTRADE.NS",
    "PBFINTECH.NS", "SAPPHIRE.NS", "RBA.NS", "WESTLIFE.NS", "CHALET.NS", "LEMONTREE.NS", "EIHOTEL.NS", "IHCL.NS", "DELTACO.NS",
    "PVRINOX.NS", "SAREGAMA.NS", "SUNTV.NS", "NETWORK18.NS", "TV18BRDCST.NS", "HATHWAY.NS", "DEN.NS", "DISHMAN.NS", "GTPL.NS",
    "UJJIVANSFB.NS", "EQUITASBNK.NS", "AUBANK.NS", "BANDHANBNK.NS", "FEDERALBNK.NS", "RBLBANK.NS", "CSBBANK.NS", "KARURVYSYA.NS",
    "CUB.NS", "DCBBANK.NS", "SOUTHBANK.NS", "J&KBANK.NS", "MAHSEAMLES.NS", "EPL.NS", "POLYPLEX.NS", "UFRLEX.NS", "SUPREMEIND.NS",
    "FINPIPE.NS", "PRINCEPIPE.NS", "RESPONIND.NS", "CENTURYPLY.NS", "GREENPANEL.NS", "GREENPLY.NS", "KAJARIACER.NS", "SOMANYCERA.NS",
    "ASAHIINDIA.NS", "LAOPALA.NS", "BORORENEW.NS", "VIPIND.NS", "SAFARI.NS", "TTKPRESTIG.NS", "HAWKINS.NS", "SYMPHONY.NS",
    "ORIENTELEC.NS", "IFBIND.NS", "VGUARD.NS", "AMBER.NS", "PGHH.NS", "GILLETTE.NS", "AKZOINDIA.NS", "KANSAINER.NS", "INDIGOPNTS.NS",
    "SIRCA.NS", "SHALPAINTS.NS", "GARFIBRES.NS", "LUXIND.NS", "RUPA.NS", "DOLLAR.NS", "TCNSBRANDS.NS", "GOKEX.NS", "SWANENERGY.NS"
]

def buy_stock(symbol, qty, price, category):
    data = load_data_from_sheets() 
    cost = qty * price
    if data['balance'] >= cost:
        new_balance = data['balance'] - cost
        today_date = datetime.now().strftime("%d-%m-%Y")
        holdings_list = []
        found = False
        for s, v in data['holdings'].items():
            if s == symbol:
                new_qty = v['qty'] + qty
                new_avg = ((v['qty'] * v['buy_price']) + cost) / new_qty
                holdings_list.append([s, new_avg, new_qty, category, today_date])
                found = True
            else:
                holdings_list.append([s, v['buy_price'], v['qty'], v['category'], v['date']])
        if not found:
            holdings_list.append([symbol, float(price), int(qty), category, today_date])
        new_holdings_df = pd.DataFrame(holdings_list, columns=['Symbol', 'Buy_Price', 'Qty', 'Category', 'Date'])
        new_balance_df = pd.DataFrame([[new_balance]], columns=['Cash'])
        # नया तरीका (इसे इस्तेमाल करें)
        MY_SHEET = "https://docs.google.com/spreadsheets/d/1LrdWFwe4SFUtT9SjklGstwHUEHjZ0Ko48wdmDtp-h5I/edit?gid=0#gid=0"
        conn.update(spreadsheet=MY_SHEET, worksheet="Portfolio", data=new_holdings_df)
        conn.update(spreadsheet=MY_SHEET, worksheet="Balance", data=new_balance_df)
        st.session_state['portfolio']['balance'] = new_balance
        st.session_state['portfolio']['holdings'] = load_data_from_sheets()['holdings']
        return True
    return False

def sell_stock(symbol, live_price):
    data = load_data_from_sheets()
    if symbol in data['holdings']:
        qty = data['holdings'][symbol]['qty']
        new_balance = data['balance'] + (qty * live_price)
        holdings_list = [[s, v['buy_price'], v['qty'], v['category'], v['date']] 
                         for s, v in data['holdings'].items() if s != symbol]
        new_holdings_df = pd.DataFrame(holdings_list, columns=['Symbol', 'Buy_Price', 'Qty', 'Category', 'Date'])
        new_balance_df = pd.DataFrame([[new_balance]], columns=['Cash'])
        # नया तरीका (इसे इस्तेमाल करें)
        MY_SHEET = "https://docs.google.com/spreadsheets/d/1LrdWFwe4SFUtT9SjklGstwHUEHjZ0Ko48wdmDtp-h5I/edit?gid=0#gid=0"
        conn.update(spreadsheet=MY_SHEET, worksheet="Portfolio", data=new_holdings_df)
        conn.update(spreadsheet=MY_SHEET, worksheet="Balance", data=new_balance_df)
        st.session_state['portfolio']['balance'] = new_balance
        st.session_state['portfolio']['holdings'] = load_data_from_sheets()['holdings']
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Settings")
    
    st.markdown("### ⏱️ Trading Mode")
    scan_mode = st.radio("Choose Mode", ["Swing (Daily)", "Intraday (15 Min)"])
    
    st.markdown("---")
    st.markdown("### 💰 My Wallet")
    balance = st.session_state['portfolio']['balance']
    st.metric("Cash Balance", f"₹ {balance:,.2f}")
    if st.button("Reset Cash", type="secondary"):
        # नए डेटा का ढांचा तैयार करें
        new_balance_df = pd.DataFrame([[1000000.0]], columns=['Cash'])
        new_holdings_df = pd.DataFrame(columns=['Symbol', 'Buy_Price', 'Qty', 'Category', 'Date'])
        
        # Google Sheets को अपडेट करें (सही पैरामीटर के साथ)
        conn.update(data=new_balance_df, worksheet="Balance")
        conn.update(data=new_holdings_df, worksheet="Portfolio")
        
        # ऐप को ताज़ा डेटा के साथ रीस्टार्ट करें
        st.session_state['portfolio'] = load_data_from_sheets()
        st.rerun()
        
    
    st.markdown("---")
    st.markdown("### 🛡️ Risk & Auto-Qty")
    capital = st.number_input("Capital (₹)", 10000, 10000000, 100000, step=10000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.5, 5.0, 2.0, 0.5)
    sl_multiplier = 2.0 
    
    st.markdown("---")
    auto_run = st.checkbox("🔄 Auto-Run (Live Loop)", False)

# --- NEW FEATURES: NEWS & RESULT PREDICTION ---
def get_news_sentiment(symbol):
    try:
        stock = yf.Ticker(symbol)
        news = stock.news
        if not news: return "⚪"
        text = " ".join([n['title'] for n in news[:3]]).lower()
        pos_words = ['growth', 'profit', 'rise', 'gain', 'buy', 'positive', 'order', 'win']
        neg_words = ['loss', 'fall', 'drop', 'sell', 'negative', 'issue', 'notice']
        score = 0
        for w in pos_words: score += text.count(w)
        for w in neg_words: score -= text.count(w)
        if score > 0: return "🟢"
        if score < 0: return "🔴"
        return "⚪"
    except: return "⚪"

def predict_results(symbol):
    try:
        stock = yf.Ticker(symbol)
        fin = stock.quarterly_financials
        if fin is None or fin.empty: return "N/A"
        try:
            income = fin.loc['Net Income'].iloc[:3]
            if income.iloc[0] > income.iloc[1] > income.iloc[2]: return "🚀 Bullish Exp."
            elif income.iloc[0] < income.iloc[1]: return "⚠️ Caution"
            else: return "Neutral"
        except: return "N/A"
    except: return "N/A"

# --- MARKET ANALYSIS ---
@st.cache_data(ttl=600)
def get_smart_sectors():
    # 🔥 FULL HEATMAP 🔥
    sectors = {
        "🏦 Bank": "^NSEBANK", "💻 IT": "^CNXIT", "🚗 Auto": "^CNXAUTO",
        "💊 Pharma": "^CNXPHARMA", "🛒 FMCG": "^CNXFMCG", "⚙️ Metal": "^CNXMETAL",
        "⚡ Energy": "^CNXENERGY", "🏠 Realty": "^CNXREALTY",
        "💰 PSU Bank": "^CNXPSUB", "🏗️ Infra": "^CNXINFRA", "📺 Media": "^CNXMEDIA"
    }
    results = {}
    for name, ticker in sectors.items():
        try:
            stock = yf.Ticker(ticker); hist = stock.history(period="3mo")
            curr = hist['Close'].iloc[-1]; prev = hist['Close'].iloc[-2]
            change = ((curr - prev) / prev) * 100
            sma50 = ta.sma(hist['Close'], length=50).iloc[-1]
            trend = "🟢 BULL" if curr > sma50 else "🔴 BEAR"
            border_col = "#22c55e" if change >= 0 else "#ef4444"
            text_col = "#15803d" if change >= 0 else "#b91c1c"
            bg_col = "#f0fdf4" if change >= 0 else "#fef2f2"
            results[name] = {"change": round(change, 2), "trend": trend, "bc": border_col, "tc": text_col, "bg": bg_col}
        except:
            results[name] = {"change": 0.0, "trend": "-", "bc": "#ccc", "tc": "#333", "bg": "#fff"}
    return results

def analyze_market_index(symbol):
    try:
        idx = yf.Ticker(symbol); df = idx.history(period="1y")
        if df.empty: return None
        curr = df['Close'].iloc[-1]; change = ((curr - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        st_data = ta.supertrend(df['High'], df['Low'], df['Close'], length=7, multiplier=3)
        st_dir = st_data.iloc[-1, 1]
        trend_txt = "🟢 BULL" if st_dir == 1 else "🔴 BEAR"
        trend_col = "green" if st_dir == 1 else "red"
        return {"price": curr, "change": change, "trend": trend_txt, "t_col": trend_col, "df": df}
    except: return None

def get_market_mood_strip():
    try:
        sp500 = yf.Ticker("^GSPC").history(period="2d")
        sp_chg = ((sp500['Close'].iloc[-1] - sp500['Close'].iloc[-2]) / sp500['Close'].iloc[-2]) * 100
        global_mood = "🟢 Bullish" if sp_chg > 0 else "🔴 Bearish"
        nifty_chg = yf.Ticker("^NSEI").history(period="1d")['Close'].iloc[-1]
        fii_est = "+1250 Cr" if sp_chg > 0 else "-900 Cr" 
        dii_est = "+800 Cr"
        return global_mood, fii_est, dii_est
    except: return "Neutral", "N/A", "N/A"

# --- PLOT CHART ---
def plot_chart(symbol, df, title_extra="", current_atr_mult=2.0, min_idx=None, max_idx=None, is_daily=True):
    try:
        if df is None or df.empty:
            st.warning("Chart data unavailable")
            return

        current_price = df['Close'].iloc[-1]
        try:
            atr_val = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
            sl_price = current_price - (atr_val * current_atr_mult)
            tgt_price = current_price + (atr_val * (current_atr_mult * 2))
        except: sl_price = 0; tgt_price = 0

        if min_idx is None:
            lows = df['Low'].values; highs = df['High'].values
            min_idx = argrelextrema(lows, np.less, order=5)[0]
            max_idx = argrelextrema(highs, np.greater, order=5)[0]

        if isinstance(df.index, pd.DatetimeIndex):
            if is_daily: df.index = df.index.strftime('%Y-%m-%d')
            else: df.index = df.index.strftime('%d-%m %H:%M')

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
        
        # 🔥 ADDING 20, 50, 200 SMA 🔥
        if len(df) > 20: fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=20), line=dict(color='#3b82f6', width=1.5), name='SMA 20'))
        if len(df) > 50: fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=50), line=dict(color='#f97316', width=1.5), name='SMA 50'))
        if len(df) > 200: fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=200), line=dict(color='#000000', width=1.5), name='SMA 200'))
        
        if sl_price > 0: fig.add_hline(y=sl_price, line_dash="dash", line_color="red", annotation_text=f"SL: {sl_price:.1f}")
        if tgt_price > 0: fig.add_hline(y=tgt_price, line_dash="dash", line_color="green", annotation_text=f"TGT: {tgt_price:.1f}")
        
        valid_min = [i for i in min_idx if i < len(df)]
        if valid_min: fig.add_trace(go.Scatter(x=df.iloc[valid_min].index, y=df.iloc[valid_min]['Low'], mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'), name='Support'))
        valid_max = [i for i in max_idx if i < len(df)]
        if valid_max: fig.add_trace(go.Scatter(x=df.iloc[valid_max].index, y=df.iloc[valid_max]['High'], mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'), name='Resistance'))

        fig.update_layout(title=f"{symbol} {title_extra}", xaxis_rangeslider_visible=False, height=400, margin=dict(l=10, r=10, t=50, b=10), template="plotly_white", xaxis={'type': 'category'})
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.error(f"Chart Error: {str(e)}")

# 🔥 HYBRID ANALYZER (WITH 2 PM REVERSAL & RECENT SUPPORT) 🔥
def analyze_stock_hybrid(symbol):
    try:
        stock = yf.Ticker(symbol)
        df_daily = stock.history(period="1y", interval="1d", auto_adjust=True)
        df_intra = stock.history(period="5d", interval="15m", auto_adjust=True)
        
        if df_daily is None or len(df_daily) < 50: return None
        try: info = stock.info
        except: info = {}
        
        curr = df_daily['Close'].iloc[-1]
        change_pct = ((curr - df_daily['Close'].iloc[-2]) / df_daily['Close'].iloc[-2]) * 100
        
        # INDICATORS
        df_daily['SMA200'] = ta.sma(df_daily['Close'], length=200)
        df_daily['RSI'] = ta.rsi(df_daily['Close'], length=14)
        df_daily['Vol_Avg'] = ta.sma(df_daily['Volume'], length=10)
        df_daily['EMA20'] = ta.ema(df_daily['Close'], length=20)
        try:
            st_data_d = ta.supertrend(df_daily['High'], df_daily['Low'], df_daily['Close'], length=7, multiplier=3)
            st_dir_d = st_data_d.iloc[-1, 1]
            adx_val_d = ta.adx(df_daily['High'], df_daily['Low'], df_daily['Close'], length=14)[ta.adx(df_daily['High'], df_daily['Low'], df_daily['Close'], length=14).columns[0]].iloc[-1]
        except: st_dir_d = 0; adx_val_d = 0

        # INTRADAY
        intra_buy = False; intra_sell = False; reversal_2pm = False
        if df_intra is not None and len(df_intra) > 20:
            df_intra['RSI'] = ta.rsi(df_intra['Close'], length=14)
            try:
                st_data_i = ta.supertrend(df_intra['High'], df_intra['Low'], df_intra['Close'], length=7, multiplier=3)
                st_dir_i = st_data_i.iloc[-1, 1]
                df_intra['VWAP'] = (df_intra['Volume'] * (df_intra['High'] + df_intra['Low'] + df_intra['Close']) / 3).cumsum() / df_intra['Volume'].cumsum()
                curr_intra = df_intra['Close'].iloc[-1]
                vwap_val = df_intra['VWAP'].iloc[-1]
                if (curr_intra > vwap_val) and (st_dir_i == 1): intra_buy = True
                if (curr_intra < vwap_val) and (st_dir_i == -1): intra_sell = True
                
                # ⚡ 2 PM REVERSAL LOGIC
                last_time = df_intra.index[-1]
                if last_time.hour >= 13 and (last_time.hour > 13 or last_time.minute >= 30):
                    prev_close = df_intra['Close'].iloc[-2]; prev_vwap = df_intra['VWAP'].iloc[-2]
                    vol_now = df_intra['Volume'].iloc[-1]; vol_avg = df_intra['Volume'].tail(10).mean()
                    if (prev_close < prev_vwap) and (curr_intra > vwap_val) and (vol_now > vol_avg * 1.5): reversal_2pm = True
            except: pass

        try: atr_val = ta.atr(df_daily['High'], df_daily['Low'], df_daily['Close'], length=14).iloc[-1]
        except: atr_val = 0
        sl_fix = round(curr - (atr_val * 2.0), 1)
        tgt_fix = round(curr + (atr_val * 4.0), 1)
        
        lows = df_daily['Low'].values; highs = df_daily['High'].values
        min_idx = argrelextrema(lows, np.less, order=5)[0]
        max_idx = argrelextrema(highs, np.greater, order=5)[0]

        # 🧱 FRESH SUPPORT & RESISTANCE LOGIC (Today or Yesterday)
        last_idx = len(df_daily) - 1
        fresh_support = False
        fresh_resistance = False

        if len(min_idx) > 0 and min_idx[-1] >= (last_idx - 1): fresh_support = True
        if len(max_idx) > 0 and max_idx[-1] >= (last_idx - 1): fresh_resistance = True

        weekly_trend = "⚪ Neutral"
        try:
            df_wk = stock.history(period="1y", interval="1wk")
            wk_curr = df_wk['Close'].iloc[-1]; wk_sma20 = ta.sma(df_wk['Close'], length=20).iloc[-1]
            weekly_trend = "🟢 UP" if wk_curr > wk_sma20 else "🔴 DOWN"
        except: pass

        news_dot = get_news_sentiment(symbol)
        
        res = {
            "Symbol": symbol, "Price": round(curr, 2), "Change": round(change_pct, 2),
            "F_Jackpot": False, "F_CE_100": False, "F_CE_80": False, "F_PE_100": False, "F_PE_80": False,
            "F_Day_Buy": intra_buy, "F_Day_Sell": intra_sell, "F_2PM": reversal_2pm,
            "F_Swing": False, "F_Double": False, "F_Tech": False, "F_Fund": False, "F_Trend": False,
            "F_Support": fresh_support, "F_Resistance": fresh_resistance,
            "F_Result": False, "Result_Text": "-",
            "DF_Daily": df_daily, "DF_Intra": df_intra, "ATR": atr_val, "Weekly": weekly_trend, "Alert_Trigger": False,
            "SL": sl_fix, "TGT": tgt_fix, "Min_Idx": min_idx, "Max_Idx": max_idx, "News": news_dot
        }

        # Strategies Logic
        sma200 = df_daily['SMA200'].iloc[-1]; rsi_d = df_daily['RSI'].iloc[-1]
        vol_blast = df_daily['Volume'].iloc[-1] > (df_daily['Vol_Avg'].iloc[-1] * 1.5)
        
        pe_ratio = info.get('trailingPE', 100); roe = info.get('returnOnEquity', 0)
        is_fund = (0 < pe_ratio < 60 and roe > 0.12)
        is_tech = (curr > sma200 and rsi_d > 55)
        
        if is_fund and is_tech and vol_blast and weekly_trend == "🟢 UP": res["F_Jackpot"] = True
        if st_dir_d == 1 and rsi_d > 60 and adx_val_d > 25 and weekly_trend == "🟢 UP": res['F_CE_100'] = True
        elif st_dir_d == 1 and rsi_d > 55: res['F_CE_80'] = True
        if st_dir_d == -1 and rsi_d < 40 and adx_val_d > 25 and weekly_trend == "🔴 DOWN": res['F_PE_100'] = True
        elif st_dir_d == -1 and rsi_d < 45: res['F_PE_80'] = True
        if curr > sma200: res["F_Tech"] = True
        if curr > df_daily['Close'].iloc[-20]: res["F_Trend"] = True
        if 0 < pe_ratio < 60: res["F_Fund"] = True
        if res["F_Fund"] and res["F_Tech"]: res["F_Double"] = True
        if vol_blast and (curr > df_daily['EMA20'].iloc[-1]): res["Alert_Trigger"] = True
            
        return res
    except: return None
# ==========================================
# 👇 LAYOUT 👇
# ==========================================

st.markdown('<div class="main-header"><h1>🧠 MARKET AI SCANNER</h1></div>', unsafe_allow_html=True)

# 1. MARKET SENTIMENT STRIP
gm, fii, dii = get_market_mood_strip()
st.markdown(f"""
    <div class='sentiment-bar'>
        <span class='sent-item'>🌎 Global Mood: {gm}</span>
        <span class='sent-item'>🏦 FII (Est): <span class='{ "sent-val-up" if "+" in fii else "sent-val-down" }'>{fii}</span></span>
        <span class='sent-item'>🇮🇳 DII (Est): <span class='sent-val-up'>{dii}</span></span>
    </div>
""", unsafe_allow_html=True)

# 2. MARKET INDICES (IN BOX)
st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">🌍 Market Indices</div>', unsafe_allow_html=True)
nifty = analyze_market_index("^NSEI")
idx_cols = st.columns(5)
data_list = [("Nifty 50", nifty, "Nifty"), ("Sensex", analyze_market_index("^BSESN"), "Sensex"), ("Bank Nifty", analyze_market_index("^NSEBANK"), "BankNifty"), ("Fin Nifty", analyze_market_index("NIFTY_FIN_SERVICE.NS"), "FinNifty"), ("Bankex", analyze_market_index("^BSEBANK"), "Bankex")]

for i, (name, d, key) in enumerate(data_list):
    with idx_cols[i]:
        if d:
            c = "green" if d['change']>=0 else "red"
            st.metric(label=name, value=f"₹{d['price']:.0f}", delta=f"{d['change']:.2f}%")
            if st.button("📉 Chart", key=f"chart_{key}", type="secondary"): st.session_state[f'show_{key}'] = not st.session_state[f'show_{key}']
        else: st.warning(f"{name} N/A")

for name, d, key in data_list:
    if d and st.session_state[f'show_{key}']: plot_chart(name, d['df'], f"({d['trend']})", is_daily=True)
st.markdown('</div>', unsafe_allow_html=True)

# 3. HEATMAP (IN BOX)
st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">🌡️ Sector Heatmap</div>', unsafe_allow_html=True)
mood = get_smart_sectors()
hm_cols = st.columns(8)
for i, (sec, val) in enumerate(mood.items()):
    with hm_cols[i % 8]:
        tc = "green" if "BULL" in val['trend'] else "red"
        st.markdown(f"<div class='sector-box'><span class='sec-name'>{sec}</span><span class='sec-val' style='color:{val['tc']}'>{val['change']}%</span><br><span class='sec-trend' style='color:{tc}'>{val['trend']}</span></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 4. SCANNER CONFIG (IN BOX)
st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">⚙️ Scanner Configuration</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("**Select Source**")
    scan_source = st.radio("S", ["Part 1 (Large)", "Part 2 (Mid)", "Part 3 (Small)", "Custom"], horizontal=True, label_visibility="collapsed")

tickers = []
if "Part 1" in scan_source: tickers = STOCK_LIST_PART_1
elif "Part 2" in scan_source: tickers = STOCK_LIST_PART_2
elif "Part 3" in scan_source: tickers = STOCK_LIST_PART_3
elif "Custom" in scan_source:
    csv_file = st.file_uploader("Upload CSV", type=["csv", "xlsx"])
    if csv_file:
        try:
            df_up = pd.read_csv(csv_file) if csv_file.name.endswith('.csv') else pd.read_excel(csv_file)
            col = next((c for c in df_up.columns if "SYMBOL" in c.upper()), None)
            if col: tickers = [f"{x.strip()}.NS" if not str(x).endswith(".NS") else x for x in df_up[col].dropna().unique()]
        except: st.error("File Error")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 START AI SCANNING", type="primary"):
    if not tickers: st.error("List Empty")
    else:
        L_All = []
        bar = st.progress(0)
        for i, t in enumerate(tickers):
            d = analyze_stock_hybrid(t)
            if d: L_All.append(d)
            bar.progress((i+1)/len(tickers))
        bar.empty()
        st.session_state['scan_data'] = L_All
st.markdown('</div>', unsafe_allow_html=True)

# 5. RESULTS
if 'scan_data' in st.session_state:
    data = st.session_state['scan_data']
    logic_map = {}
    if "Intraday" in scan_mode:
        logic_map = {
            "🚀 Day Buy": "F_Day_Buy", 
            "🐻 Day Sell": "F_Day_Sell", 
            "⚡ 2 PM Reversal": "F_2PM", 
            "🟢 Fresh Support": "F_Support", # बदला हुआ
            "🔴 Fresh Resistance": "F_Resistance", # नया
            "🔥 Alerts": "Alert_Trigger"
        }
    else:
        logic_map = {
            "🚀 CE (100%)": "F_CE_100", "⚡ CE (80%)": "F_CE_80", "🐻 PE (100%)": "F_PE_100", "📉 PE (80%)": "F_PE_80",
            "🏆 Jackpot": "F_Jackpot", "🚀 Swing": "F_Swing", "🥈 Double": "F_Double",
            "🟢 Fresh Support": "F_Support", # बदला हुआ
            "🔴 Fresh Resistance": "F_Resistance", # नया
            "🌊 Trend": "F_Trend", "📈 Tech": "F_Tech", "💎 Fund": "F_Fund", "🔥 Alerts": "Alert_Trigger"
        }
    
    final_tabs = {}
    for name, key in logic_map.items():
        f = [x for x in data if x.get(key)]
        if f: final_tabs[name] = f
    
    if len(data) > 0: final_tabs["🔮 Result Magic"] = data 
    
    if final_tabs:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🎯 Scan Results</div>', unsafe_allow_html=True)
        tabs = st.tabs(list(final_tabs.keys()))
        for i, (name, lst) in enumerate(final_tabs.items()):
            with tabs[i]:
                if name == "🔮 Result Magic":
                    st.info("AI checking recent 3 quarters for financial trend...")
                    res_list = []
                    # Limit to 10 for performance
                    for item in lst[:10]:
                        pred = predict_results(item['Symbol'])
                        if "Bullish" in pred or "Caution" in pred:
                            item['Result_Text'] = pred
                            res_list.append(item)
                    if not res_list: st.warning("No clear result patterns found.")
                    else:
                        df_view = pd.DataFrame(res_list)
                        st.dataframe(df_view[["Symbol", "Price", "Change", "Result_Text", "News"]], use_container_width=True)
                else:
                    df_view = pd.DataFrame(lst)
                    event = st.dataframe(df_view[["Symbol", "Price", "Change", "SL", "TGT", "Weekly", "News"]], use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"tbl_{i}")
                    if len(event.selection.rows) > 0:
                        idx = event.selection.rows[0]; sel_sym = df_view.iloc[idx]['Symbol']
                        sel_item = next((x for x in lst if x['Symbol'] == sel_sym), None)
                        cc1, cc2 = st.columns([3, 1])
                        with cc1: 
                            chart_df = sel_item['DF_Intra'] if "Day" in name else sel_item['DF_Daily']
                            is_daily = "Day" not in name
                            plot_chart(sel_sym, chart_df, f"({scan_mode})", sl_multiplier, sel_item['Min_Idx'], sel_item['Max_Idx'], is_daily)
                        with cc2:
                            st.subheader(f"Trade {sel_sym}")
                            atr_val = sel_item['ATR']
                            if atr_val > 0:
                                dyn_sl = sel_item['Price'] - (atr_val * sl_multiplier)
                                sl_gap = sel_item['Price'] - dyn_sl
                                if sl_gap > 0:
                                    max_risk_amt = capital * (risk_pct / 100)
                                    auto_qty = int(max_risk_amt / sl_gap)
                                    st.markdown(f"<div class='qty-box'>💡 Auto Qty: {auto_qty}</div>", unsafe_allow_html=True)
                                    st.write(f"Risk: ₹{sl_gap:.1f} / share")
                            qty = st.number_input("Final Qty", 1, 10000, auto_qty if 'auto_qty' in locals() else 1, key=f"q_{sel_sym}")
                            if st.button("BUY NOW", key=f"b_{sel_sym}", type="secondary"):
                                if buy_stock(sel_sym, qty, sel_item['Price'], name): st.success("Bought!")
                                else: st.error("No Cash!")
        st.markdown('</div>', unsafe_allow_html=True)

# 6. PORTFOLIO (IN BOX)
st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📋 My Holdings</div>', unsafe_allow_html=True)
if not st.session_state['portfolio']['holdings']:
    st.info("No active trades.")
else:
    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2.5, 1.5, 1.5, 1, 1.5, 1.5, 1.5, 0.8, 0.8])
    headers = ["STOCK", "DATE", "CAT", "QTY", "AVG", "LTP", "P/L", "CHART", "SELL"]
    for c, h in zip([c1,c2,c3,c4,c5,c6,c7,c8,c9], headers): c.markdown(f"<div class='table-header'>{h}</div>", unsafe_allow_html=True)

    # 🟢 NEW: Initialize Total P/L variable
    total_pl_sum = 0.0

    for s, v in st.session_state['portfolio']['holdings'].items():
        try: live = yf.Ticker(s).fast_info['last_price']
        except: live = v['buy_price']
        pl = (live - v['buy_price']) * v['qty']
        
        # 🟢 NEW: Add current stock P/L to total
        total_pl_sum += pl
        
        pl_c = "green" if pl >= 0 else "#ef4444" # red color
        
        with st.container():
            c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2.5, 1.5, 1.5, 1, 1.5, 1.5, 1.5, 0.8, 0.8])
            c1.markdown(f"<div class='table-row'><b>{s}</b></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='table-row'>{v['date']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='table-row'>{v['category']}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='table-row'>{v['qty']}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div class='table-row'>{v['buy_price']:.1f}</div>", unsafe_allow_html=True)
            c6.markdown(f"<div class='table-row'>{live:.1f}</div>", unsafe_allow_html=True)
            c7.markdown(f"<div class='table-row' style='color:{pl_c}'><b>{pl:.1f}</b></div>", unsafe_allow_html=True)
            
            if c8.button("📉", key=f"p_chart_{s}", type="secondary"):
                if st.session_state.get('active_chart') == s:
                    del st.session_state['active_chart']
                else:
                    st.session_state['active_chart'] = s
            
            if c9.button("✕", key=f"sell_{s}", type="secondary"):
                sell_stock(s, live); st.rerun()

        if st.session_state.get('active_chart') == s:
            try:
                with st.spinner("Loading Chart..."):
                    d_hold = analyze_stock_hybrid(s)
                    if d_hold:
                        chart_df_h = d_hold['DF_Daily'] if "Swing" in scan_mode else d_hold['DF_Intra']
                        is_daily_h = "Swing" in scan_mode
                        plot_chart(s, chart_df_h, "(Live Portfolio View)", 2.0, d_hold['Min_Idx'], d_hold['Max_Idx'], is_daily_h)
                        if st.button("Close Chart", key=f"close_{s}", type="secondary"):
                            del st.session_state['active_chart']; st.rerun()
            except: st.error("Chart Error")

    # 🟢 NEW: Display Total Portfolio P/L at the bottom
    total_col = "#4ade80" if total_pl_sum >= 0 else "#f87171"
    st.markdown(f"""
        <div class="total-pl-container">
            <div class="pl-label">TOTAL PORTFOLIO PERFORMANCE</div>
            <div class="pl-value" style="color: {total_col};">₹ {total_pl_sum:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
