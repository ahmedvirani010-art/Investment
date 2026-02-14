import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="PSX Investment Agent", page_icon="📈", layout="wide")

st.sidebar.markdown("## ⚙️ Configuration")
analysis_type = st.sidebar.radio("Select Analysis Type", ["📊 Dashboard", "💧 Liquidity", "🔍 Anomalies", "📰 News", "📉 Technical", "📢 Announcements"])
st.sidebar.divider()
st.sidebar.markdown("### Stock Selection")
ticker = st.sidebar.text_input("Enter Stock Ticker", value="TRG").upper()

st.title("📊 PSX Investment Analysis Dashboard")

if "Dashboard" in analysis_type:
    st.subheader(f"📊 Investment Dashboard - {ticker}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", "₨ 245.50", "+2.5%")
    c2.metric("Volume (M)", "12.5M", "-5.2%", delta_color="inverse")
    c3.metric("Market Cap (B)", "₨ 125.8B", "+3.1%")
    c4.metric("P/E Ratio", "18.5x", "Neutral", delta_color="off")
    st.divider()

    # Prepare data
    days = pd.date_range(end=datetime.now(), periods=30)
    prices = 245 + np.cumsum(np.random.randn(30) * 2)
    volumes = np.abs(np.random.randn(30) * 5 + 12)

    # Display charts in columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📈 Price Trend")
        st.line_chart(pd.DataFrame({"Price": prices}, index=days))
    with col2:
        st.markdown("### 💹 Trading Volume")
        st.bar_chart(pd.DataFrame({"Volume": volumes}, index=days))

elif "Liquidity" in analysis_type:
    st.subheader(f"💧 Liquidity Screener - {ticker}")
    c1, c2, c3 = st.columns(3)
    c1.number_input("Min Daily Volume (M)", value=1.0, min_value=0.1)
    c2.number_input("Min Price (₨)", value=20.0, min_value=1.0)
    c3.slider("Period (Days)", 1, 365, 30)
    st.divider()
    df = pd.DataFrame({"Ticker": ["TRG", "LUCK", "PSO", "MCB", "HBL"], "Price": [245.50, 35.60, 28.20, 520.75, 1245.50], "Volume (M)": [12.5, 8.2, 15.3, 3.5, 2.1], "Turnover (B)": [3.06, 2.92, 4.32, 1.82, 2.61]})
    st.dataframe(df, use_container_width=True, hide_index=True)

elif "Anomalies" in analysis_type:
    st.subheader(f"🔍 Anomaly Detection - {ticker}")
    c1, c2 = st.columns(2)
    c1.slider("Detection Sensitivity", 1, 5, 3)
    c2.metric("Anomalies Detected", "7", "+2 from yesterday")
    st.divider()
    df = pd.DataFrame({"Date": ["2025-02-14", "2025-02-13", "2025-02-12"], "Type": ["Volume Spike", "Price Gap", "Volatility Surge"], "Magnitude": ["15.2%", "8.5%", "12.3%"], "Z-Score": [4.2, 3.1, 3.8]})
    st.dataframe(df, use_container_width=True, hide_index=True)

elif "News" in analysis_type:
    st.subheader(f"📰 News Intelligence - {ticker}")
    news = [{"t": f"{ticker} Reports Strong Q4 Earnings", "s": "Business Recorder", "d": "2 hours ago", "i": "+2.5%"}, {"t": f"Market Analyst Upgrades {ticker}", "s": "Profit", "d": "5 hours ago", "i": "+1.2%"}, {"t": f"{ticker} Announces New Board Members", "s": "The News", "d": "1 day ago", "i": "0.0%"}]
    for n in news:
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(f"**{n['t']}**")
            a.caption(f"{n['s']} • {n['d']}")
            b.metric("Impact", n["i"], label_visibility="collapsed")

elif "Technical" in analysis_type:
    st.subheader(f"📉 Technical Analysis - {ticker}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RSI (14)", "65.2", "Overbought Zone", delta_color="off")
    c2.metric("MACD", "5.23", "Positive")
    c3.metric("SMA Trend", "Above", "+3.2% from SMA")
    c4.metric("ADX (14)", "32.1", "Strong Trend", delta_color="off")
    st.divider()
    df = pd.DataFrame({"Indicator": ["RSI (14)", "MACD", "SMA 20", "Bollinger Bands", "ADX (14)"], "Value": ["65.2", "5.23", "243.15", "Above", "32.1"], "Signal": ["Overbought", "Bullish", "Bullish", "Bullish", "Strong Trend"]})
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.subheader("📢 PSX Announcements")
    anns = [{"c": "TRG", "tp": "Dividend", "t": "Cash Dividend of Rs. 3.00 per share", "d": "2025-02-12", "i": "+1.5%"}, {"c": "LUCK", "tp": "Results", "t": "Q4 2024 Financial Results Announced", "d": "2025-02-10", "i": "+2.3%"}, {"c": "PSO", "tp": "Board Meeting", "t": "Board of Directors Meeting Feb 15", "d": "2025-02-08", "i": "0.0%"}]
    for a in anns:
        with st.container(border=True):
            x, y, z = st.columns([1, 3, 1])
            x.markdown(f"**{a['c']}**")
            x.caption(f"*{a['tp']}*")
            y.markdown(a["t"])
            y.caption(a["d"])
            z.metric("Impact", a["i"], label_visibility="collapsed")

st.divider()
c1, c2, c3 = st.columns(3)
c1.caption("📊 Data Source: Pakistan Stock Exchange")
c2.caption(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
c3.caption("🔄 Powered by AI Agents")
