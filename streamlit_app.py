import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure page
st.set_page_config(
      page_title="PSX Investment Agent",
      page_icon="📈",
      layout="wide",
      initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
            font-size: 2.5rem;
                    font-weight: bold;
                            color: #1f77b4;
                                    margin-bottom: 1rem;
                                        }
                                        </style>
                                        """, unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
      st.markdown("## ⚙️ Configuration")

    analysis_type = st.radio(
              "Select Analysis Type",
              ["📊 Dashboard", "💧 Liquidity", "🔍 Anomalies", "📰 News", "📉 Technical", "📢 Announcements"],
              label_visibility="collapsed"
    )

    st.divider()

    st.markdown("### Stock Selection")
    ticker = st.text_input(
              "Enter Stock Ticker",
              value="TRG",
              placeholder="e.g., TRG, LUCK, PSO"
    ).upper()

# Main Content
st.markdown("<h1 class='main-header'>📊 PSX Investment Analysis Dashboard</h1>", unsafe_allow_html=True)

if "Dashboard" in analysis_type:
      st.subheader(f"📊 Investment Dashboard - {ticker}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
              st.metric("Current Price", "₨ 245.50", "+2.5%", delta_color="normal")
          with col2:
                    st.metric("Volume (M)", "12.5M", "-5.2%", delta_color="inverse")
                with col3:
                          st.metric("Market Cap (B)", "₨ 125.8B", "+3.1%", delta_color="normal")
                      with col4:
                                st.metric("P/E Ratio", "18.5x", "Neutral", delta_color="off")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
              st.markdown("### 📈 Price Trend")
              days = pd.date_range(end=datetime.now(), periods=30)
              prices = 245 + np.cumsum(np.random.randn(30) * 2)
              df_chart = pd.DataFrame({'Date': days, 'Price': prices})
              st.line_chart(df_chart.set_index('Date'))

    with col2:
              st.markdown("### 💹 Trading Volume")
              volumes = np.abs(np.random.randn(30) * 5 + 12)
              df_vol = pd.DataFrame({'Date': days, 'Volume': volumes})
              st.bar_chart(df_vol.set_index('Date'))

elif "Liquidity" in analysis_type:
    st.subheader(f"💧 Liquidity Screener - {ticker}")

    col1, col2, col3 = st.columns(3)
    with col1:
              min_volume = st.number_input("Min Daily Volume (M)", value=1.0, min_value=0.1)
          with col2:
                    min_price = st.number_input("Min Price (₨)", value=20.0, min_value=1.0)
                with col3:
                          date_range = st.slider("Period (Days)", 1, 365, 30)

    st.divider()

    liquidity_data = {
              'Ticker': ['TRG', 'LUCK', 'PSO', 'MCB', 'HBL'],
              'Price': [245.50, 35.60, 28.20, 520.75, 1245.50],
              'Volume (M)': [12.5, 8.2, 15.3, 3.5, 2.1],
              'Turnover (B)': [3.06, 2.92, 4.32, 1.82, 2.61],
              'Bid-Ask Spread': ['0.10%', '0.15%', '0.08%', '0.12%', '0.20%'],
    }

    df_liquidity = pd.DataFrame(liquidity_data)
    st.dataframe(df_liquidity, use_container_width=True, hide_index=True)

elif "Anomalies" in analysis_type:
    st.subheader(f"🔍 Anomaly Detection - {ticker}")

    col1, col2 = st.columns(2)
    with col1:
              sensitivity = st.slider("Detection Sensitivity", 1, 5, 3)
          with col2:
                    st.metric("Anomalies Detected", "7", "+2 from yesterday")

    st.divider()

    anomalies_data = {
              'Date': ['2025-02-14', '2025-02-13', '2025-02-12', '2025-02-11', '2025-02-10'],
              'Type': ['Volume Spike', 'Price Gap', 'Volatility Surge', 'Volume Spike', 'Price Gap'],
              'Magnitude': ['15.2%', '8.5%', '12.3%', '9.8%', '6.5%'],
              'Z-Score': [4.2, 3.1, 3.8, 2.9, 2.5],
    }

    df_anomalies = pd.DataFrame(anomalies_data)
    st.dataframe(df_anomalies, use_container_width=True, hide_index=True)

elif "News" in analysis_type:
    st.subheader(f"📰 News Intelligence - {ticker}")

    st.markdown("### 📰 Latest News")

    news_items = [
              {'title': f'{ticker} Reports Strong Q4 Earnings', 'source': 'Business Recorder', 'date': '2 hours ago', 'sentiment': '✅ Positive', 'impact': '+2.5%'},
              {'title': f'Market Analyst Upgrades {ticker} Rating', 'source': 'Profit', 'date': '5 hours ago', 'sentiment': '✅ Positive', 'impact': '+1.2%'},
              {'title': f'{ticker} Announces New Board Members', 'source': 'The News', 'date': '1 day ago', 'sentiment': '⚪ Neutral', 'impact': '0.0%'},
    ]

    for news in news_items:
              with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                              st.markdown(f"**{news['title']}**")
                                              st.caption(f"{news['source']} • {news['date']}")
                                          with col2:
                                st.metric("Impact", news['impact'], label_visibility="collapsed")

elif "Technical" in analysis_type:
    st.subheader(f"📉 Technical Analysis - {ticker}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
              st.metric("RSI (14)", "65.2", "Overbought Zone", delta_color="off")
          with col2:
                    st.metric("MACD", "5.23", "Positive", delta_color="normal")
                with col3:
                          st.metric("SMA Trend", "Above", "+3.2% from SMA", delta_color="normal")
                      with col4:
                                st.metric("ADX (14)", "32.1", "Strong Trend", delta_color="off")

else:  # Announcements
    st.subheader("📢 PSX Announcements")

      announcements = [
          {'company': 'TRG', 'type': 'Dividend', 'title': 'Cash Dividend of Rs. 3.00 per share announced', 'date': '2025-02-12', 'impact': '+1.5%'},
                {'company': 'LUCK', 'type': 'Results', 'title': 'Q4 2024 Financial Results Announced', 'date': '2025-02-10', 'impact': '+2.3%'},
                {'company': 'PSO', 'type': 'Board Meeting', 'title': 'Board of Directors Meeting scheduled for February 15', 'date': '2025-02-08', 'impact': '0.0%'},
      ]

    for ann in announcements:
              with st.container(border=True):
                            col1, col2, col3 = st.columns([1, 3, 1])
                            with col1:
                                              st.markdown(f"**{ann['company']}**")
                                              st.caption(f"*{ann['type']}*")
                                          with col2:
                                st.markdown(ann['title'])
                                                            st.caption(ann['date'])
                                                        with col3:
                                                            st.metric("Impact", ann['impact'], label_visibility="collapsed")

                                            # Footer
                                            st.divider()
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.caption("📊 Data Source: Pakistan Stock Exchange")
                                              with col2:
                                                st.caption(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                                with col3:
                                                      st.caption("🔄 Powered by AI Agents")
