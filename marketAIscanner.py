import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import plotly.graph_objects as go
import json
import time
import requests
from datetime import datetime
from github import Github # <-- Nayi Library

# --- CONFIG ---
st.set_page_config(page_title="Market AI Cloud", layout="wide", page_icon="☁️")

# ==========================================
# 👇 TELEGRAM SETTINGS 👇
# ==========================================
MY_BOT_TOKEN = "8503524657:AAHNYtJkcaZMISZ8O8yWgmmQ1B5hULvMst4"
MY_CHAT_ID = "5914005185"
# ==========================================

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}
    div[data-testid="stExpander"] {border: 1px solid #ddd; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- CLOUD STORAGE SYSTEM (GitHub) ☁️ ---
PORTFOLIO_FILE = "portfolio_data.json"

def get_github_repo():
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        g = Github(token)
        return g.get_repo(repo_name)
    except: return None

def load_portfolio_cloud():
    try:
        repo = get_github_repo()
        if not repo: return {}
        try:
            content = repo.get_contents(PORTFOLIO_FILE)
            return json.loads(content.decoded_content.decode())
        except: 
            return {} # File nahi mili to khali return karo
    except: return {}

def save_portfolio_cloud(data):
    try:
        repo = get_github_repo()
        if not repo: return
        
        json_str = json.dumps(data, indent=4)
        try:
            # Update existing file
            contents = repo.get_contents(PORTFOLIO_FILE)
            repo.update_file(contents.path, "Update Portfolio", json_str, contents.sha)
        except:
            # Create new file if not exists
            repo.create_file(PORTFOLIO_FILE, "Create Portfolio", json_str)
    except Exception as e:
        st.error(f"Save Error: {e}")

# --- TELEGRAM SENDER ---
def send_telegram_msg(message):
    if MY_BOT_TOKEN and MY_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{MY_BOT_TOKEN}/sendMessage"
            params = {"chat_id": MY_CHAT_ID, "text": message}
            requests.get(url, params=params)
        except: pass

# --- STOCK LIST ---
FULL_STOCK_LIST = [
    # Part 1 (Large)
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "L&T.NS", "HINDUNILVR.NS",
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
    "RECLTD.NS", "IOB.NS", "UNIONBANK.NS", "INDIANB.NS", "UCOBANK.NS", "MAHABANK.NS", "CENTRALBK.NS", "PSB.NS", "SBICARD.NS",
    # Part 2 (Mid)
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
    "SCHAEFFLER.NS", "AIAENG.NS", "ELGIEQUIP.NS", "KIRLOSENG.NS", "SUZLON.NS", "INOXWIND.NS", "BEML.NS", "MAZDOCK.NS", "COCHINSHIP.NS",
    # Part 3 (Small/Others)
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

# --- DATA MANAGER (Cloud Sync) ☁️ ---
if 'my_portfolio' not in st.session_state:
    with st.spinner("Connecting to Cloud..."):
        st.session_state['my_portfolio'] = load_portfolio_cloud()

if 'sent_alerts' not in st.session_state: st.session_state['sent_alerts'] = []

def add_to_portfolio(symbol, qty, price, category):
    today_date = datetime.now().strftime("%d/%m/%Y")
    st.session_state['my_portfolio'][symbol] = {
        "qty": int(qty), "buy_price": float(price), "category": category, "date": today_date
    }
    # Save to Cloud immediately
    save_portfolio_cloud(st.session_state['my_portfolio'])

# --- CHART ENGINE ---
def plot_chart_with_patterns(symbol, min_idx, max_idx, df):
    try:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
        try:
            fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=20), line=dict(color='blue', width=1.5), name='SMA 20'))
            fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=50), line=dict(color='orange', width=1.5), name='SMA 50'))
            fig.add_trace(go.Scatter(x=df.index, y=ta.sma(df['Close'], length=200), line=dict(color='black', width=2), name='SMA 200'))
        except: pass
        if len(min_idx) > 0:
            min_prices = df['Low'].iloc[min_idx]
            fig.add_trace(go.Scatter(x=min_prices.index, y=min_prices.values, mode='markers', marker=dict(color='green', size=8, symbol='triangle-up'), name='Support'))
        if len(max_idx) > 0:
            max_prices = df['High'].iloc[max_idx]
            fig.add_trace(go.Scatter(x=max_prices.index, y=max_prices.values, mode='markers', marker=dict(color='red', size=8, symbol='triangle-down'), name='Resistance'))
        fig.update_layout(title=f"{symbol} Analysis", xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    except: st.error("Chart Error")

# --- AI BRAIN (Safe) 🧠 ---
def analyze_stock_safe(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")
        if df is None or len(df) < 100: return None
        try: info = stock.info
        except: info = {}

        curr = df['Close'].iloc[-1]; prev = df['Close'].iloc[-2]
        change_pct = ((curr - prev) / prev) * 100
        
        lows = df['Low'].values; highs = df['High'].values
        min_idx = argrelextrema(lows, np.less, order=5)[0]
        max_idx = argrelextrema(highs, np.greater, order=5)[0]

        res = {
            "Symbol": symbol, "Price": round(curr, 2), "Change": round(change_pct, 2),
            "F_Jackpot": False, "F_Swing": False, "F_FO_CE": False, "F_FO_PE": False,
            "F_Double": False, "F_Tech": False, "F_Fund": False, "F_Trend": False,
            "Shape_Bull": "-", "Shape_Bear": "-",
            "Min_Idx": min_idx, "Max_Idx": max_idx, "DF": df, "Alert_Trigger": False
        }

        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['Vol_Avg'] = ta.sma(df['Volume'], length=10)

        if pd.isna(df['SMA200'].iloc[-1]): return None

        sma200 = df['SMA200'].iloc[-1]; rsi = df['RSI'].iloc[-1]
        vol_blast = df['Volume'].iloc[-1] > (df['Vol_Avg'].iloc[-1] * 1.5)
        macd_val = macd['MACD_12_26_9'].iloc[-1]; macd_sig = macd['MACDs_12_26_9'].iloc[-1]
        
        pe = info.get('trailingPE', 100); roe = info.get('returnOnEquity', 0)
        is_fund = (0 < pe < 60 and roe > 0.12)
        is_tech = (curr > sma200 and 45 < rsi < 70)
        is_trend = (curr > df['Close'].iloc[-20] * 1.05)

        if is_fund and is_tech and is_trend and vol_blast: res["F_Jackpot"] = True
        high_20 = df['High'].tail(20).max()
        if curr >= high_20 * 0.98 and rsi > 60 and vol_blast: res["F_Swing"] = True
        if curr > df['EMA20'].iloc[-1] and rsi > 55 and macd_val > macd_sig: res["F_FO_CE"] = True
        elif curr < df['EMA20'].iloc[-1] and rsi < 45 and macd_val < macd_sig: res["F_FO_PE"] = True
        if is_fund and is_tech: res["F_Double"] = True
        if is_tech: res["F_Tech"] = True
        if is_fund: res["F_Fund"] = True
        if is_trend: res["F_Trend"] = True
        
        if len(min_idx) >= 2 and abs(lows[min_idx[-1]] - lows[min_idx[-2]]) < (lows[min_idx[-1]]*0.02): res["Shape_Bull"] = "W-Pattern"
        if len(min_idx) >= 3 and not res["Shape_Bull"] == "W-Pattern":
             if lows[min_idx[-2]] < lows[min_idx[-1]] and lows[min_idx[-2]] < lows[min_idx[-3]]: res["Shape_Bull"] = "Inverse H&S"
        if len(max_idx) >= 2 and abs(highs[max_idx[-1]] - highs[max_idx[-2]]) < (highs[max_idx[-1]]*0.02): res["Shape_Bear"] = "M-Pattern"
        if len(max_idx) >= 3 and not res["Shape_Bear"] == "M-Pattern":
             if highs[max_idx[-2]] > highs[max_idx[-1]] and highs[max_idx[-2]] > highs[max_idx[-3]]: res["Shape_Bear"] = "Head & Shoulders"
        
        is_ready = (rsi > 55 and curr > df['EMA20'].iloc[-1])
        if vol_blast and is_ready and (res["Shape_Bull"] != "-" or res["F_Jackpot"]): res["Alert_Trigger"] = True
        
        return res
    except: return None

# --- UI ---
st.title("🚀 Market AI: Cloud Edition")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("🕹️ Scan Settings")
scan_source = st.sidebar.radio("Select Source:", ["Part 1 (Large Cap)", "Part 2 (Mid Cap)", "Part 3 (Small Cap)", "📂 Upload Custom File"])

tickers = []
chunk_size = len(FULL_STOCK_LIST) // 3
if scan_source == "Part 1 (Large Cap)":
    tickers = FULL_STOCK_LIST[:chunk_size]
    st.sidebar.caption(f"Stocks: 1 - {chunk_size}")
elif scan_source == "Part 2 (Mid Cap)":
    tickers = FULL_STOCK_LIST[chunk_size : chunk_size*2]
    st.sidebar.caption(f"Stocks: {chunk_size} - {chunk_size*2}")
elif scan_source == "Part 3 (Small Cap)":
    tickers = FULL_STOCK_LIST[chunk_size*2 :]
    st.sidebar.caption(f"Stocks: {chunk_size*2} - End")
elif scan_source == "📂 Upload Custom File":
    csv_file = st.sidebar.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if csv_file:
        try:
            df_up = pd.read_csv(csv_file) if csv_file.name.endswith('.csv') else pd.read_excel(csv_file)
            col = next((c for c in df_up.columns if "SYMBOL" in c.upper()), None)
            if col: tickers = [f"{x.strip()}.NS" if not str(x).endswith(".NS") else x for x in df_up[col].dropna().unique()]
        except: st.sidebar.error("File Error")

st.sidebar.markdown("---")
auto_run = st.sidebar.checkbox("🔄 Auto-Run Loop (Live)")
refresh_rate = st.sidebar.slider("Refresh (Sec)", 60, 300, 60)

st.sidebar.markdown("---")
st.sidebar.header("💾 Backup")
if st.session_state['my_portfolio']:
    portfolio_json = json.dumps(st.session_state['my_portfolio'], default=str)
    st.sidebar.download_button("📥 Download", portfolio_json, "my_portfolio_cloud.json", "application/json")
up = st.sidebar.file_uploader("📤 Restore", type=["json"])
if up: 
    st.session_state['my_portfolio'] = json.load(up)
    save_portfolio_cloud(st.session_state['my_portfolio']) # Sync with cloud

# --- SCANNER ---
if st.button("🚀 START SCAN") or auto_run:
    if not tickers: st.error("No stocks selected! Check Part or File.")
    else:
        L_All = []
        bar = st.progress(0)
        for i, t in enumerate(tickers):
            d = analyze_stock_safe(t)
            if d:
                L_All.append(d)
                if d['Alert_Trigger'] and d['Symbol'] not in st.session_state['sent_alerts']:
                    msg = f"🚀 SUPER ALERT: {d['Symbol']}\n💰 Price: {d['Price']}\n📈 Pattern: {d['Shape_Bull']}\n🔥 Vol Blast!"
                    send_telegram_msg(msg)
                    st.toast(f"📲 Alert: {d['Symbol']}")
                    st.session_state['sent_alerts'].append(d['Symbol'])
            bar.progress((i+1)/len(tickers))
        bar.empty()
        st.session_state['scan_data'] = L_All
        if auto_run:
            time.sleep(refresh_rate)
            st.rerun()

# --- DISPLAY ---
if 'scan_data' in st.session_state:
    data = st.session_state['scan_data']
    cats = {
        "🔥 Alerts": [x for x in data if x['Alert_Trigger']],
        "🏆 Jackpot": [x for x in data if x['F_Jackpot']],
        "🚀 Swing": [x for x in data if x['F_Swing']],
        "🎰 CE": [x for x in data if x['F_FO_CE']],
        "🐻 PE": [x for x in data if x['F_FO_PE']],
        "🥈 Double": [x for x in data if x['F_Double']],
        "📈 Tech": [x for x in data if x['F_Tech']],
        "💎 Fund": [x for x in data if x['F_Fund']],
        "🌊 Trend": [x for x in data if x['F_Trend']],
        "✨ Bull": [x for x in data if x['Shape_Bull'] != "-"],
        "⚠️ Bear": [x for x in data if x['Shape_Bear'] != "-"],
    }
    tabs = st.tabs(list(cats.keys()))
    for i, (name, lst) in enumerate(cats.items()):
        with tabs[i]:
            if not lst: st.info("No stocks matched.")
            else:
                df_view = pd.DataFrame(lst)
                event = st.dataframe(
                    df_view[["Symbol", "Price", "Change", "Shape_Bull", "Shape_Bear"]], 
                    use_container_width=True, 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row",
                    key=f"df_{name}"
                )
                if len(event.selection.rows) > 0:
                    idx = event.selection.rows[0]; sel_sym = df_view.iloc[idx]['Symbol']
                    sel_item = next((x for x in lst if x['Symbol'] == sel_sym), None)
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        if sel_item: plot_chart_with_patterns(sel_sym, sel_item['Min_Idx'], sel_item['Max_Idx'], sel_item['DF'])
                    with c2:
                        qty = st.number_input("Qty", 1, 1000, 10, key=f"q_{name}")
                        if st.button("Add ➕", key=f"b_{name}"):
                            add_to_portfolio(sel_sym, qty, sel_item['Price'], name)
                            st.success("Added!")
                            time.sleep(1) 
                            st.rerun()

# --- PORTFOLIO ---
st.markdown("---")
st.subheader("💼 Unified Portfolio")
portfolio_container = st.empty()

def render_portfolio():
    if not st.session_state['my_portfolio']:
        portfolio_container.info("Portfolio Empty.")
        return

    p_data = []; tot_pl = 0
    for s, v in st.session_state['my_portfolio'].items():
        try: live = yf.Ticker(s).fast_info['last_price']
        except: live = v['buy_price']
        pl = (live - v['buy_price']) * v['qty']
        tot_pl += pl
        p_data.append({"Date": v.get('date','-'), "Stock": s, "Category": v['category'], "Buy": v['buy_price'], "Live": round(live,2), "P/L": round(pl, 2)})
    
    with portfolio_container.container():
        st.dataframe(pd.DataFrame(p_data).style.applymap(lambda x: 'color: green' if x > 0 else 'color: red', subset=['P/L']), use_container_width=True)
        # TOTAL P&L BOX
        c_val = "green" if tot_pl >= 0 else "red"
        st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin-top: 10px;">
                <h2 style="color: black; margin:0;">Total P&L</h2>
                <h1 style="color: {c_val}; margin:0;">₹ {tot_pl:,.2f}</h1>
                <p>Live Updated: {datetime.now().strftime('%H:%M:%S')}</p>
            </div>
        """, unsafe_allow_html=True)

render_portfolio()

if st.button("🔴 Start Live Updates"):
    while True:
        render_portfolio()
        time.sleep(3)
