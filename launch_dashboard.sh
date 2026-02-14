#!/bin/bash

# PSX Trading Dashboard Launcher
echo "🚀 Starting PSX Trading Dashboard..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "📦 Streamlit not found. Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Launch the dashboard
echo "✅ Launching dashboard at http://localhost:8501"
echo ""
streamlit run psx_trading_dashboard.py
