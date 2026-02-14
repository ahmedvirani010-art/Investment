"""
PSX Trading Dashboard
Interactive web UI for PSX Liquidity Screener and Anomaly Detection agents
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from psx_liquidity_screener import PSXLiquidityScreener, StockLiquidity
from psx_anomaly_agent import PSXAnomalyAgent, Anomaly, Severity, AnomalyType

# Page configuration
st.set_page_config(
    page_title="PSX Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 1rem;
    }
    h2 {
        color: #2ca02c;
        padding-top: 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


def format_currency(value):
    """Format currency in billions/millions"""
    if value >= 1_000_000_000:
        return f"Rs {value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"Rs {value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"Rs {value/1_000:.2f}K"
    else:
        return f"Rs {value:.2f}"


def format_number(value):
    """Format large numbers"""
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value/1_000:.2f}K"
    else:
        return f"{value:.0f}"


def main():
    # Sidebar
    st.sidebar.title("🎯 PSX Trading Dashboard")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Select Tool",
        ["🏠 Home", "💧 Liquidity Screener", "🔔 Anomaly Detection", "📊 Combined Analysis"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "**PSX Trading Dashboard** provides real-time analysis of Pakistan Stock Exchange.\n\n"
        "- 💧 Identify most liquid stocks\n"
        "- 🔔 Detect trading anomalies\n"
        "- 📊 Combine insights for better decisions"
    )

    # Main content
    if page == "🏠 Home":
        show_home()
    elif page == "💧 Liquidity Screener":
        show_liquidity_screener()
    elif page == "🔔 Anomaly Detection":
        show_anomaly_detection()
    elif page == "📊 Combined Analysis":
        show_combined_analysis()


def show_home():
    """Home page with overview"""
    st.title("📊 PSX Trading Dashboard")
    st.markdown("### Welcome to Pakistan Stock Exchange Analytics Platform")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ## 💧 Liquidity Screener

        Identify the most actively traded stocks on PSX based on:
        - **30-day average traded value** (Volume × Price)
        - **Customizable price filters** (minimum Rs 20)
        - **Top 100 ranking** by liquidity

        **Use Cases:**
        - Find stocks with sufficient liquidity for trading
        - Identify market leaders and laggards
        - Build liquid portfolios for easy entry/exit
        - Avoid illiquid penny stocks
        """)

        if st.button("🚀 Open Liquidity Screener", key="home_liquidity"):
            st.session_state.page = "💧 Liquidity Screener"
            st.rerun()

    with col2:
        st.markdown("""
        ## 🔔 Anomaly Detection

        Detect unusual trading patterns using statistical analysis:
        - **Volume spikes** (unusual trading activity)
        - **Price movements** (abnormal returns)
        - **Opening gaps** (gap up/down detection)
        - **Volatility spikes** (unusual price ranges)
        - **Liquidity changes** (turnover anomalies)

        **Use Cases:**
        - Catch early signals before major moves
        - Identify potential breakouts/breakdowns
        - Monitor portfolio holdings for risk
        - Find trading opportunities
        """)

        if st.button("🚀 Open Anomaly Detection", key="home_anomaly"):
            st.session_state.page = "🔔 Anomaly Detection"
            st.rerun()

    st.markdown("---")

    # Quick stats
    st.markdown("## 📈 Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Stocks Monitored",
            value="100+",
            delta="All major sectors"
        )

    with col2:
        st.metric(
            label="Analysis Period",
            value="30 Days",
            delta="Rolling window"
        )

    with col3:
        st.metric(
            label="Detection Types",
            value="5",
            delta="Multi-dimensional"
        )

    with col4:
        st.metric(
            label="Update Frequency",
            value="Real-time",
            delta="On-demand"
        )


def show_liquidity_screener():
    """Liquidity screener page"""
    st.title("💧 PSX Liquidity Screener")
    st.markdown("Find the most liquid stocks on Pakistan Stock Exchange")

    # Parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        lookback_days = st.slider(
            "Lookback Period (days)",
            min_value=7,
            max_value=90,
            value=30,
            step=1,
            help="Number of days to calculate average liquidity"
        )

    with col2:
        min_price = st.number_input(
            "Minimum Price (PKR)",
            min_value=0.0,
            max_value=1000.0,
            value=20.0,
            step=5.0,
            help="Filter out stocks below this price"
        )

    with col3:
        top_n = st.slider(
            "Number of Stocks",
            min_value=10,
            max_value=100,
            value=50,
            step=10,
            help="Show top N most liquid stocks"
        )

    # Run button
    if st.button("🔍 Run Liquidity Analysis", type="primary"):
        with st.spinner("Analyzing PSX stocks... This may take a few minutes."):
            try:
                # Run screener
                screener = PSXLiquidityScreener(
                    lookback_days=lookback_days,
                    min_price=min_price
                )

                results = screener.screen_stocks(top_n=100)

                if not results:
                    st.error("❌ No stocks found matching criteria")
                    return

                # Limit to top_n
                top_stocks = results[:top_n]

                # Store in session state
                st.session_state.liquidity_results = top_stocks
                st.session_state.liquidity_params = {
                    'lookback_days': lookback_days,
                    'min_price': min_price,
                    'top_n': top_n
                }

                st.success(f"✅ Analysis complete! Found {len(top_stocks)} liquid stocks.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                return

    # Display results
    if 'liquidity_results' in st.session_state:
        results = st.session_state.liquidity_results
        params = st.session_state.liquidity_params

        # Summary metrics
        st.markdown("## 📊 Summary Statistics")

        col1, col2, col3, col4 = st.columns(4)

        total_value = sum(s.avg_traded_value for s in results)

        with col1:
            st.metric(
                "Total Stocks",
                len(results)
            )

        with col2:
            st.metric(
                "Combined Daily Value",
                format_currency(total_value)
            )

        with col3:
            st.metric(
                "Top Stock",
                results[0].symbol,
                format_currency(results[0].avg_traded_value)
            )

        with col4:
            st.metric(
                "Average per Stock",
                format_currency(total_value / len(results))
            )

        # Charts
        st.markdown("## 📈 Visualization")

        tab1, tab2, tab3 = st.tabs(["📊 Top Stocks", "🥧 Sector Distribution", "📉 Price vs Volume"])

        with tab1:
            # Bar chart of top stocks
            df = pd.DataFrame([
                {
                    'Symbol': s.symbol,
                    'Company': s.name[:30],
                    'Avg Traded Value': s.avg_traded_value / 1_000_000,  # Convert to millions
                    'Price': s.current_price
                }
                for s in results[:20]
            ])

            fig = px.bar(
                df,
                x='Symbol',
                y='Avg Traded Value',
                title=f'Top 20 Most Liquid Stocks',
                labels={'Avg Traded Value': 'Avg Traded Value (Rs Million)'},
                color='Avg Traded Value',
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Pie chart by sector (simplified - you can enhance this)
            st.info("💡 Sector categorization feature coming soon!")

            # For now, show price distribution
            df_price = pd.DataFrame([
                {
                    'Symbol': s.symbol,
                    'Price Range': 'High (>500)' if s.current_price > 500
                                   else 'Medium (100-500)' if s.current_price > 100
                                   else 'Low (<100)'
                }
                for s in results
            ])

            price_dist = df_price['Price Range'].value_counts()

            fig = px.pie(
                values=price_dist.values,
                names=price_dist.index,
                title='Stock Distribution by Price Range'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # Scatter plot
            df_scatter = pd.DataFrame([
                {
                    'Symbol': s.symbol,
                    'Price': s.current_price,
                    'Volume': s.avg_volume,
                    'Traded Value': s.avg_traded_value / 1_000_000
                }
                for s in results
            ])

            fig = px.scatter(
                df_scatter,
                x='Price',
                y='Volume',
                size='Traded Value',
                hover_data=['Symbol'],
                title='Price vs Volume (bubble size = traded value)',
                labels={'Volume': 'Avg Volume', 'Price': 'Current Price (PKR)'},
                color='Traded Value',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        # Data table
        st.markdown("## 📋 Detailed Results")

        df_table = pd.DataFrame([
            {
                'Rank': s.rank,
                'Symbol': s.symbol,
                'Company': s.name,
                'Avg Traded Value': format_currency(s.avg_traded_value),
                'Avg Volume': format_number(s.avg_volume),
                'Current Price': f"Rs {s.current_price:.2f}",
                'Trading Days': s.trading_days
            }
            for s in results
        ])

        st.dataframe(df_table, use_container_width=True, height=400)

        # Export options
        st.markdown("## 💾 Export Data")

        col1, col2 = st.columns(2)

        with col1:
            csv = df_table.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"psx_liquidity_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col2:
            symbols = [s.symbol for s in results]
            st.download_button(
                label="📋 Download Symbols List",
                data=json.dumps(symbols, indent=2),
                file_name=f"psx_symbols_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )


def show_anomaly_detection():
    """Anomaly detection page"""
    st.title("🔔 PSX Anomaly Detection")
    st.markdown("Detect unusual trading patterns and price movements")

    # Parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        lookback_days = st.slider(
            "Lookback Period (days)",
            min_value=30,
            max_value=90,
            value=60,
            step=5,
            help="Number of days for baseline calculation"
        )

    with col2:
        z_threshold = st.slider(
            "Z-Score Threshold",
            min_value=2.0,
            max_value=4.0,
            value=2.5,
            step=0.1,
            help="Higher = fewer but more significant anomalies"
        )

    with col3:
        use_liquid_stocks = st.checkbox(
            "Use Liquid Stocks Only",
            value=True,
            help="Only analyze top 50 liquid stocks"
        )

    # Stock selection
    if use_liquid_stocks:
        st.info("💡 Using top 50 most liquid stocks from screener results")
        if 'liquidity_results' in st.session_state:
            symbols = [s.symbol for s in st.session_state.liquidity_results[:50]]
        else:
            st.warning("⚠️ Run Liquidity Screener first or enter symbols manually")
            symbols = None
    else:
        symbols_input = st.text_area(
            "Enter Stock Symbols (comma-separated)",
            value="LUCK, PSO, HBL, ENGRO, MCB, OGDC, PPL, UBL, HUBC, FFC",
            help="Enter stock symbols separated by commas"
        )
        symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]

    # Run button
    if st.button("🔍 Detect Anomalies", type="primary") and symbols:
        with st.spinner(f"Analyzing {len(symbols)} stocks for anomalies..."):
            try:
                # Run anomaly detection
                agent = PSXAnomalyAgent(
                    lookback_days=lookback_days,
                    z_threshold=z_threshold
                )

                report = agent.generate_report(symbols)

                # Store in session state
                st.session_state.anomaly_report = report
                st.session_state.anomaly_params = {
                    'lookback_days': lookback_days,
                    'z_threshold': z_threshold,
                    'symbols_count': len(symbols)
                }

                if report:
                    total_anomalies = sum(len(anomalies) for anomalies in report.values())
                    st.success(f"✅ Analysis complete! Found {total_anomalies} anomalies across {len(report)} stocks.")
                else:
                    st.info("✅ No anomalies detected. All stocks trading normally.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                return

    # Display results
    if 'anomaly_report' in st.session_state:
        report = st.session_state.anomaly_report
        params = st.session_state.anomaly_params

        if not report:
            st.success("✅ No anomalies detected. Market trading within normal parameters.")
            return

        # Summary metrics
        st.markdown("## 📊 Anomaly Summary")

        total_anomalies = sum(len(anomalies) for anomalies in report.values())
        high_severity = sum(
            1 for anomalies in report.values()
            for a in anomalies if a.severity == Severity.HIGH
        )
        medium_severity = sum(
            1 for anomalies in report.values()
            for a in anomalies if a.severity == Severity.MEDIUM
        )
        low_severity = sum(
            1 for anomalies in report.values()
            for a in anomalies if a.severity == Severity.LOW
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Anomalies", total_anomalies)

        with col2:
            st.metric("🔴 High Severity", high_severity)

        with col3:
            st.metric("🟡 Medium Severity", medium_severity)

        with col4:
            st.metric("🟢 Low Severity", low_severity)

        # Charts
        st.markdown("## 📈 Visualization")

        tab1, tab2 = st.tabs(["🎯 By Stock", "📊 By Type"])

        with tab1:
            # Anomalies by stock
            df_by_stock = pd.DataFrame([
                {
                    'Symbol': symbol,
                    'Anomalies': len(anomalies),
                    'High': sum(1 for a in anomalies if a.severity == Severity.HIGH),
                    'Medium': sum(1 for a in anomalies if a.severity == Severity.MEDIUM),
                    'Low': sum(1 for a in anomalies if a.severity == Severity.LOW)
                }
                for symbol, anomalies in report.items()
            ])

            fig = px.bar(
                df_by_stock,
                x='Symbol',
                y=['High', 'Medium', 'Low'],
                title='Anomalies by Stock and Severity',
                labels={'value': 'Count', 'variable': 'Severity'},
                color_discrete_map={'High': '#FF4B4B', 'Medium': '#FFA500', 'Low': '#90EE90'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Anomalies by type
            type_counts = {}
            for anomalies in report.values():
                for a in anomalies:
                    type_name = a.anomaly_type.value
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1

            fig = px.pie(
                values=list(type_counts.values()),
                names=list(type_counts.keys()),
                title='Anomalies by Type'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        # Detailed anomalies
        st.markdown("## 🔍 Detailed Anomalies")

        for symbol, anomalies in sorted(report.items(), key=lambda x: len(x[1]), reverse=True):
            with st.expander(f"**{symbol}** - {len(anomalies)} anomaly/anomalies", expanded=len(anomalies) > 0):
                for anomaly in sorted(anomalies, key=lambda x: abs(x.z_score), reverse=True):
                    severity_color = {
                        Severity.HIGH: "🔴",
                        Severity.MEDIUM: "🟡",
                        Severity.LOW: "🟢"
                    }

                    severity_bg = {
                        Severity.HIGH: "#ffe6e6",
                        Severity.MEDIUM: "#fff4e6",
                        Severity.LOW: "#e6ffe6"
                    }

                    st.markdown(f"""
                    <div style="background-color: {severity_bg[anomaly.severity]}; padding: 15px; border-radius: 5px; margin: 10px 0;">
                        <h4>{severity_color[anomaly.severity]} {anomaly.severity.value} - {anomaly.anomaly_type.value}</h4>
                        <p><strong>Date:</strong> {anomaly.date}</p>
                        <p><strong>Description:</strong> {anomaly.description}</p>
                        <p><strong>Z-Score:</strong> {anomaly.z_score:.2f}σ</p>
                    </div>
                    """, unsafe_allow_html=True)


def show_combined_analysis():
    """Combined analysis page"""
    st.title("📊 Combined Analysis")
    st.markdown("Combine liquidity and anomaly insights for comprehensive market view")

    # Check if both analyses are available
    has_liquidity = 'liquidity_results' in st.session_state
    has_anomaly = 'anomaly_report' in st.session_state

    if not has_liquidity and not has_anomaly:
        st.warning("⚠️ Please run both Liquidity Screener and Anomaly Detection first")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Run Liquidity Screener"):
                st.session_state.page = "💧 Liquidity Screener"
                st.rerun()
        with col2:
            if st.button("Run Anomaly Detection"):
                st.session_state.page = "🔔 Anomaly Detection"
                st.rerun()
        return

    if has_liquidity and has_anomaly:
        liquidity_results = st.session_state.liquidity_results
        anomaly_report = st.session_state.anomaly_report

        # Create combined view
        st.markdown("## 🎯 Liquid Stocks with Anomalies")
        st.info("These stocks have both high liquidity AND detected anomalies - prime candidates for further analysis")

        # Find intersection
        liquid_symbols = {s.symbol for s in liquidity_results}
        anomaly_symbols = set(anomaly_report.keys())

        intersection = liquid_symbols & anomaly_symbols

        if intersection:
            st.success(f"Found {len(intersection)} liquid stocks with anomalies")

            # Create detailed view
            combined_data = []
            for symbol in intersection:
                # Get liquidity data
                stock_liq = next(s for s in liquidity_results if s.symbol == symbol)

                # Get anomaly data
                anomalies = anomaly_report[symbol]
                high_count = sum(1 for a in anomalies if a.severity == Severity.HIGH)
                med_count = sum(1 for a in anomalies if a.severity == Severity.MEDIUM)
                low_count = sum(1 for a in anomalies if a.severity == Severity.LOW)

                combined_data.append({
                    'Symbol': symbol,
                    'Company': stock_liq.name,
                    'Liquidity Rank': stock_liq.rank,
                    'Avg Traded Value': format_currency(stock_liq.avg_traded_value),
                    'Current Price': f"Rs {stock_liq.current_price:.2f}",
                    'Total Anomalies': len(anomalies),
                    '🔴 High': high_count,
                    '🟡 Medium': med_count,
                    '🟢 Low': low_count,
                    'Latest Anomaly': anomalies[0].anomaly_type.value if anomalies else 'N/A'
                })

            df_combined = pd.DataFrame(combined_data)
            df_combined = df_combined.sort_values('Liquidity Rank')

            st.dataframe(df_combined, use_container_width=True, height=400)

            # Download combined report
            csv = df_combined.to_csv(index=False)
            st.download_button(
                label="📥 Download Combined Report",
                data=csv,
                file_name=f"psx_combined_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No overlap between liquid stocks and anomaly-detected stocks")

        # Separate sections
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("## 💧 Top Liquid Stocks (No Anomalies)")
            liquid_no_anomaly = liquid_symbols - anomaly_symbols
            if liquid_no_anomaly:
                st.success(f"{len(liquid_no_anomaly)} liquid stocks trading normally")
                for symbol in list(liquid_no_anomaly)[:10]:
                    stock = next(s for s in liquidity_results if s.symbol == symbol)
                    st.write(f"**{symbol}** - {format_currency(stock.avg_traded_value)}")
            else:
                st.info("All liquid stocks have detected anomalies")

        with col2:
            st.markdown("## 🔔 Anomalies in Illiquid Stocks")
            anomaly_not_liquid = anomaly_symbols - liquid_symbols
            if anomaly_not_liquid:
                st.warning(f"{len(anomaly_not_liquid)} stocks with anomalies but lower liquidity")
                for symbol in list(anomaly_not_liquid)[:10]:
                    anomaly_count = len(anomaly_report[symbol])
                    st.write(f"**{symbol}** - {anomaly_count} anomaly/anomalies")
            else:
                st.info("All anomaly stocks are in the liquid set")

    elif has_liquidity:
        st.info("✅ Liquidity analysis available. Run Anomaly Detection for combined insights.")
        if st.button("Run Anomaly Detection"):
            st.session_state.page = "🔔 Anomaly Detection"
            st.rerun()

    elif has_anomaly:
        st.info("✅ Anomaly detection available. Run Liquidity Screener for combined insights.")
        if st.button("Run Liquidity Screener"):
            st.session_state.page = "💧 Liquidity Screener"
            st.rerun()


if __name__ == "__main__":
    main()
