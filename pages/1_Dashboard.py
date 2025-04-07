import os
from dotenv import load_dotenv
import time
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from utils.stock_data import get_stock_data, get_available_periods, get_popular_stocks, verify_ticker
from utils.indicators import get_available_indicators, calculate_indicators, get_indicator_info
from utils.strategies import get_available_strategies, apply_strategy, get_strategy_params_by_period
from utils.sentiment_analysis import (
    fetch_sentiment_data, analyze_sentiment, 
    calculate_sentiment_metrics, create_sentiment_charts,
    chat_with_ai, get_sentiment_score_color
)
from utils.prophet_forecasting import render_forecast_ui  # Import the forecasting UI
from utils.risk_analysis import render_risk_metrics_ui  # Import the risk analysis UI
from utils.comparative_analysis import render_comparative_analysis_ui  # Import the comparative analysis UI
load_dotenv()

# Page configuration - THIS MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Finbud - An AI Powered Technical Analysis Platform",
    page_icon="📈",
    layout="wide"
)

# Check for demo mode AFTER page config
demo_mode = st.session_state.get("demo_mode", False)

if demo_mode:
    st.warning(
        "🔬 **DEMO MODE ACTIVE** - Using pre-cached data instead of live API calls. "
        "Some features have limited functionality. For full functionality, add your API keys in the API Setup page."
    )
    demo_dirs = [
        "demo_cache",
        "demo_cache/sentiment",
        "demo_cache/risk",
        "demo_cache/comparative",
        "demo_cache/forecast"
    ]
    
    for directory in demo_dirs:
        os.makedirs(directory, exist_ok=True)

def get_api_key(key_name, default=""):
    """Get API key with fallback logic"""
    # First check session state
    if "api_keys" in st.session_state and key_name in st.session_state.api_keys and st.session_state.api_keys[key_name]:
        return st.session_state.api_keys[key_name]
    # Then fall back to environment variable
    return os.getenv(key_name, default)

# Load custom CSS - MOVED AFTER set_page_config
def load_css():
    try:
        with open('custom.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("custom.css file not found. UI enhancements will be limited.")

# HTML templates for UI components
def get_header_html(date_str):
    return f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">📈 Stock Technical Analysis Dashboard</h1>
            <p class="dashboard-subtitle">Professional-grade market analysis and forecasting tools</p>
        </div>
        <div class="dashboard-meta">
            Last updated: {date_str} | <span class="gold-accent">Alpha Vantage API</span>
        </div>
    </div>
    """

def get_kpi_card_html(label, value, change=None, change_pct=None, is_positive=True, subtitle=None):
    if change is not None and change_pct is not None:
        if is_positive:
            return f"""
            <div class="metric-card positive">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-change positive-change">
                    +{change} ({change_pct}%) ↑
                </div>
            </div>
            """
        else:
            return f"""
            <div class="metric-card negative">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-change negative-change">
                    {change} ({change_pct}%) ↓
                </div>
            </div>
            """
    else:
        return f"""
        <div class="metric-card neutral">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-change">
                {subtitle if subtitle else ''}
            </div>
        </div>
        """

def get_strategy_alert_html(strategy_name, num_trades, win_rate, strategy_return):
    return f"""
    <div class="strategy-alert">
        <strong>⚡ {strategy_name} Strategy Applied</strong> | 
        {num_trades} trades | Win rate: {win_rate}% | Return: {strategy_return}%
    </div>
    """

def get_chart_container_start_html(title):
    return f"""
    <div class="chart-container">
        <div class="chart-title">{title}</div>
    """

def get_chart_container_end_html():
    return """
    </div>
    """

def get_footer_html():
    return """
    <div class="dashboard-footer">
        Developed with 💙 using Streamlit, Alpha Vantage API, and pandas-ta | 
        <a href="https://github.com/yourusername/stock-analysis-dashboard" target="_blank">View on GitHub</a>
    </div>
    """

# Apply custom styling after page config
load_css()

# Display header
current_date = datetime.now().strftime('%B %d, %Y')
st.markdown(get_header_html(current_date), unsafe_allow_html=True)

# Create tabs for different types of analysis
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Technical Analysis", 
    "Forecasting", 
    "Sentiment Analysis", 
    "Risk Analysis",
    "Comparative Analysis"
])

# Initialize session state variables
if 'selected_indicators' not in st.session_state:
    st.session_state.selected_indicators = []

# Sidebar (kept outside tabs for shared settings)
st.sidebar.markdown('<div class="sidebar-header">Settings</div>', unsafe_allow_html=True)

# Stock selection
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
popular_stocks = get_popular_stocks()
stock_options = [f"{stock['symbol']} - {stock['name']}" for stock in popular_stocks]
selected_stock_option = st.sidebar.selectbox(
    "Select a stock:",
    options=stock_options,
    index=0
)
selected_stock = selected_stock_option.split(" - ")[0]

# Custom ticker input
custom_ticker = st.sidebar.text_input(
    "Or enter a custom ticker symbol:",
    value="",
    help="Enter a valid ticker symbol (e.g., AAPL, MSFT, GOOG)"
)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

##alpha_vantage_key = "BZW2K8SFI3GETDOV"
fmp_api_key = os.getenv("FMP_API_KEY")

if custom_ticker:
    with st.sidebar:
        with st.spinner(f"Verifying ticker {custom_ticker.upper()}..."):
            if verify_ticker(custom_ticker.upper(),fmp_api_key=fmp_api_key):
                selected_stock = custom_ticker.upper()
                st.sidebar.success(f"✅ {selected_stock} is a valid ticker")
            else:
                st.sidebar.error(f"❌ {custom_ticker.upper()} doesn't appear to be a valid ticker")
                st.sidebar.info(f"Using {selected_stock} instead")

# Time period selection
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
st.sidebar.markdown('<div class="filter-label">Time Period:</div>', unsafe_allow_html=True)

periods = get_available_periods()
period_options = [period['label'] for period in periods]
period_values = [period['value'] for period in periods]
selected_period_index = st.sidebar.selectbox(
    "Select time period:",
    options=range(len(period_options)),
    format_func=lambda x: period_options[x]
)
selected_period = period_values[selected_period_index]
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Indicator selection
st.sidebar.markdown('<div class="sidebar-header">Technical Indicators</div>', unsafe_allow_html=True)
all_indicators = get_available_indicators()

indicators_by_category = {}
for indicator in all_indicators:
    category = indicator['category']
    if category not in indicators_by_category:
        indicators_by_category[category] = []
    indicators_by_category[category].append(indicator)

for category, indicators in indicators_by_category.items():
    st.sidebar.markdown(f'<div class="filter-section"><div class="indicator-group-title">{category}</div>', unsafe_allow_html=True)
    for indicator in indicators:
        indicator_key = f"indicator_{indicator['id']}"
        if st.sidebar.checkbox(indicator['name'], key=indicator_key):
            if indicator['id'] not in st.session_state.selected_indicators:
                st.session_state.selected_indicators.append(indicator['id'])
        else:
            if indicator['id'] in st.session_state.selected_indicators:
                st.session_state.selected_indicators.remove(indicator['id'])
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Trading Strategy selection
st.sidebar.markdown('<div class="sidebar-header">Trading Strategies</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
all_strategies = get_available_strategies()
strategy_options = [f"{strategy['name']}" for strategy in all_strategies]
selected_strategy_index = st.sidebar.selectbox(
    "Select a trading strategy:",
    options=range(len(strategy_options)),
    format_func=lambda x: strategy_options[x]
)
selected_strategy_id = all_strategies[selected_strategy_index]["id"]

# Strategy parameter inputs
st.sidebar.markdown('<div class="indicator-group-title">Strategy Parameters</div>', unsafe_allow_html=True)
strategy_params = {}
default_params = get_strategy_params_by_period(selected_strategy_id, selected_period)
for param in all_strategies[selected_strategy_index]["parameters"]:
    param_id = param["id"]
    param_default = default_params.get(param_id, param["default"])
    if "options" in param:
        strategy_params[param_id] = st.sidebar.selectbox(
            param["name"],
            options=param["options"],
            index=param["options"].index(param_default) if param_default in param["options"] else 0
        )
    elif "min" in param and "max" in param:
        step = param.get("step", 1)
        strategy_params[param_id] = st.sidebar.slider(
            param["name"],
            min_value=param["min"],
            max_value=param["max"],
            value=param_default,
            step=step
        )
    else:
        strategy_params[param_id] = st.sidebar.number_input(
            param["name"],
            value=param_default
        )

apply_strategy_checkbox = st.sidebar.checkbox("Apply Trading Strategy")
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Sentiment Analysis settings
st.sidebar.markdown('<div class="sidebar-header">Sentiment Analysis</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
enable_sentiment = st.sidebar.checkbox("Enable Sentiment Analysis", value=False)

if enable_sentiment:
    sentiment_days = st.sidebar.slider(
        "Days of sentiment data",
        min_value=1,
        max_value=30,
        value=7
    )
    default_openrouter = get_api_key("OPENROUTER_KEY", "")
    openrouter_key = st.sidebar.text_input(
        "OpenRouter API Key (optional)",
        value=default_openrouter,
        type="password",
        help="API key for OpenRouter to access Gemini"
    )
    use_sentiment_cache = st.sidebar.checkbox("Use cached data if available", value=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Risk Analysis settings
st.sidebar.markdown('<div class="sidebar-header">Risk Analysis</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
enable_benchmark = st.sidebar.checkbox("Include Benchmark Comparison", value=False)

if enable_benchmark:
    benchmark_ticker = st.sidebar.selectbox(
        "Select benchmark:",
        options=["SPY", "QQQ", "DIA", "IWM"],
        index=0,
        help="SPY (S&P 500), QQQ (Nasdaq), DIA (Dow Jones), IWM (Russell 2000)"
    )
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Comparative Analysis settings
# Comparative Analysis settings
st.sidebar.markdown('<div class="sidebar-header">Comparative Analysis</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
enable_comparison = st.sidebar.checkbox("Enable Stock Comparison", value=False)

if enable_comparison:
    # Initialize empty list to store comparison tickers
    comparison_tickers = []
    
    # Allow up to 3 comparison stocks
    for i in range(3):
        st.sidebar.markdown(f"#### Comparison Stock {i+1}")
        
        # Dropdown selection
        stock_options = [f"{stock['symbol']} - {stock['name']}" for stock in popular_stocks 
                         if stock['symbol'] != selected_stock and stock['symbol'] not in comparison_tickers]
        comparison_default = "" if not stock_options else stock_options[0]
        comp_stock_option = st.sidebar.selectbox(
            f"Select stock {i+1}:",
            options=[""] + stock_options,  # Add empty option
            index=0,
            key=f"comp_stock_{i}"
        )
        
        # Extract ticker if selected from dropdown
        selected_comp_ticker = ""
        if comp_stock_option and " - " in comp_stock_option:
            selected_comp_ticker = comp_stock_option.split(" - ")[0]
        
        # Or allow custom ticker input
        custom_comp_ticker = st.sidebar.text_input(
            f"Or enter custom ticker {i+1}:",
            value="",
            key=f"custom_comp_{i}",
            help="Enter a valid ticker symbol (e.g., AAPL, MSFT, GOOG)"
        )
        
        # Validate custom ticker if provided
        final_ticker = selected_comp_ticker
        if custom_comp_ticker:
            with st.sidebar:
                with st.spinner(f"Verifying ticker {custom_comp_ticker.upper()}..."):
                    if verify_ticker(custom_comp_ticker.upper(), fmp_api_key=fmp_api_key):
                        final_ticker = custom_comp_ticker.upper()
                        st.sidebar.success(f"✅ {final_ticker} is a valid ticker")
                    else:
                        st.sidebar.error(f"❌ {custom_comp_ticker.upper()} doesn't appear to be a valid ticker")
                        if selected_comp_ticker:
                            st.sidebar.info(f"Using {selected_comp_ticker} from dropdown instead")
                            final_ticker = selected_comp_ticker
                        else:
                            final_ticker = ""
        
        # Add valid ticker to comparison list
        if final_ticker and final_ticker != selected_stock and final_ticker not in comparison_tickers:
            comparison_tickers.append(final_ticker)
        
        st.sidebar.markdown("---")
    
    if not comparison_tickers:
        st.sidebar.warning("Please select at least one valid comparison stock")

st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Button to fetch data - styled button
st.sidebar.markdown('<div style="padding: 20px 0 10px 0; text-align: center;">', unsafe_allow_html=True)
fetch_button = st.sidebar.button("Fetch Data & Generate Charts", key="fetch_data_button", 
                               use_container_width=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Technical Analysis Tab
with tab1:
    st.markdown("""
        Select a stock, time period, and technical indicators to visualize and analyze stock performance.
        This app uses Alpha Vantage and/or Yahoo Finance for data and pandas-ta for calculating technical indicators.
    """)
    
    if fetch_button:
    # Get API key from session state or environment
        fmp_api_key = get_api_key("FMP_API_KEY")
        
        # If in demo mode or we have a key, proceed
        if demo_mode or fmp_api_key:
            with st.spinner(f'Fetching data for {selected_stock}...'):
                data, error,cache_info = get_stock_data(
                    selected_stock, 
                    period=selected_period,
                    fmp_api_key=fmp_api_key
                )
                if cache_info and cache_info.get("used", False):
                    last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                    if cache_info and cache_info.get("used", False):
                        st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                    else:
                        st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
                
            
            if error:
                st.markdown(f"""
                <div class="alert alert-error">
                    <strong>Error:</strong> {error}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("""
                <div class="alert alert-info">
                    Try the following troubleshooting steps:
                    <ul>
                        <li>Verify the ticker symbol is correct</li>
                        <li>Try a different ticker</li>
                        <li>Use a shorter time period</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            elif data is None or data.empty:
                st.markdown(f"""
                <div class="alert alert-error">
                    <strong>No data available for {selected_stock}</strong>
                </div>
                <div class="alert alert-info">
                    This could be due to the stock being delisted or the data provider having issues.
                </div>
                """, unsafe_allow_html=True)
            else:
                # Calculate selected indicators
                if st.session_state.selected_indicators:
                    data = calculate_indicators(data, st.session_state.selected_indicators)
                
                # Apply strategy if selected
                if apply_strategy_checkbox:
                    with st.spinner(f'Applying {all_strategies[selected_strategy_index]["name"]} strategy...'):
                        data = apply_strategy(data, selected_strategy_id, strategy_params)
                
                # Display basic stock info with styled KPI cards
                latest_data = data.iloc[-1]
                previous_data = data.iloc[-2]
                price_change = latest_data['close'] - previous_data['close']
                price_change_pct = (price_change / previous_data['close']) * 100
                
                # Create container for metrics
                st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    is_positive = price_change >= 0
                    change_str = f"${abs(price_change):.2f}"
                    st.markdown(
                        get_kpi_card_html(
                            "Current Price", 
                            f"${latest_data['close']:.2f}", 
                            change_str, 
                            f"{abs(price_change_pct):.2f}", 
                            is_positive
                        ),
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        get_kpi_card_html(
                            "Volume", 
                            f"{latest_data['volume']:,.0f}", 
                            subtitle=f"Avg: {data['volume'].mean():,.0f}"
                        ),
                        unsafe_allow_html=True
                    )
                with col3:
                    day_range = f"${latest_data['low']:.2f} - ${latest_data['high']:.2f}"
                    st.markdown(
                        get_kpi_card_html(
                            "Day Range", 
                            day_range, 
                            subtitle=f"Spread: ${latest_data['high'] - latest_data['low']:.2f}"
                        ),
                        unsafe_allow_html=True
                    )
                with col4:
                    date_range = f"{data['date'].min().strftime('%Y-%m-%d')} to {data['date'].max().strftime('%Y-%m-%d')}"
                    st.markdown(
                        get_kpi_card_html(
                            "Date Range", 
                            f"{len(data)} days", 
                            subtitle=date_range
                        ),
                        unsafe_allow_html=True
                    )
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show strategy performance metrics if strategy was applied
                if apply_strategy_checkbox and 'total_trades' in data.columns:
                    # Strategy alert with performance stats
                    st.markdown(
                        get_strategy_alert_html(
                            all_strategies[selected_strategy_index]["name"],
                            f"{data.loc[0, 'total_trades']:.0f}",
                            f"{data.loc[0, 'win_rate']:.2f}",
                            f"{(data['cumulative_return'].iloc[-1] * 100 - 100):.2f}"
                        ),
                        unsafe_allow_html=True
                    )
                
                # Wrap charts in containers
                st.markdown(get_chart_container_start_html(f"{selected_stock} Stock Analysis"), unsafe_allow_html=True)
                
                # Create figure with subplots
                fig = make_subplots(
                    rows=2, 
                    cols=1, 
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    row_heights=[0.7, 0.3],
                    subplot_titles=("Price Chart", "Volume")
                )
                
                # Add candlestick chart
                fig.add_trace(
                    go.Candlestick(
                        x=data['date'],
                        open=data['open'],
                        high=data['high'],
                        low=data['low'],
                        close=data['close'],
                        name="Price"
                    ),
                    row=1, col=1
                )
                
                # Add volume bar chart
                fig.add_trace(
                    go.Bar(
                        x=data['date'],
                        y=data['volume'],
                        name="Volume",
                        marker_color='rgba(26, 35, 126, 0.5)'  # Primary blue with transparency
                    ),
                    row=2, col=1
                )
                
                # Add selected indicators to the chart
                for indicator_id in st.session_state.selected_indicators:
                    if indicator_id.startswith("sma") or indicator_id.startswith("ema") or indicator_id == "psar":
                        if indicator_id in data.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data[indicator_id],
                                    mode='lines',
                                    name=next((ind['name'] for ind in all_indicators if ind['id'] == indicator_id), indicator_id),
                                    line=dict(width=1.5)
                                ),
                                row=1, col=1
                            )
                    elif indicator_id == "bbands":
                        if 'bollinger_upper' in data.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['bollinger_upper'],
                                    mode='lines',
                                    name='Bollinger Upper',
                                    line=dict(width=1, dash='dash', color="#534bae")  # Primary light color
                                ),
                                row=1, col=1
                            )
                        if 'bollinger_middle' in data.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['bollinger_middle'],
                                    mode='lines',
                                    name='Bollinger Middle',
                                    line=dict(width=1, color="#1A237E")  # Primary color
                                ),
                                row=1, col=1
                            )
                        if 'bollinger_lower' in data.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['bollinger_lower'],
                                    mode='lines',
                                    name='Bollinger Lower',
                                    line=dict(width=1, dash='dash', color="#534bae")  # Primary light color
                                ),
                                row=1, col=1
                            )
                
                # Add buy/sell markers if strategy applied
                if apply_strategy_checkbox:
                    if 'buy_signal' in data.columns:
                        buy_points = data[data['buy_signal'] == 1]
                        if not buy_points.empty:
                            fig.add_trace(
                                go.Scatter(
                                    x=buy_points['date'],
                                    y=buy_points['close'],
                                    mode='markers',
                                    name='Buy Signal',
                                    marker=dict(
                                        symbol='triangle-up',
                                        size=15,
                                        color='#388E3C',  # Positive color
                                        line=dict(width=2, color='#2E7D32')  # Darker green
                                    )
                                ),
                                row=1, col=1
                            )
                    if 'sell_signal' in data.columns:
                        sell_points = data[data['sell_signal'] == 1]
                        if not sell_points.empty:
                            fig.add_trace(
                                go.Scatter(
                                    x=sell_points['date'],
                                    y=sell_points['close'],
                                    mode='markers',
                                    name='Sell Signal',
                                    marker=dict(
                                        symbol='triangle-down',
                                        size=15,
                                        color='#D32F2F',  # Negative color
                                        line=dict(width=2, color='#B71C1C')  # Darker red
                                    )
                                ),
                                row=1, col=1
                            )
                
                # Update layout with our styling
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=600,  # Slightly smaller height
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",  # Clean white template
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=1,
                        font=dict(size=12)
                    ),
                    margin=dict(l=40, r=40, t=40, b=40),
                    font=dict(family="Arial, sans-serif", size=12, color="#37474F"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                
                # Update gridlines
                fig.update_xaxes(
                    showgrid=True,
                    gridcolor='#ECEFF1',
                    zeroline=False
                )
                
                fig.update_yaxes(
                    showgrid=True,
                    gridcolor='#ECEFF1',
                    zeroline=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
                
                # Show equity curve if strategy applied
                if apply_strategy_checkbox and 'cumulative_return' in data.columns:
                    st.markdown(get_chart_container_start_html("Strategy Equity Curve"), unsafe_allow_html=True)
                    equity_fig = go.Figure()
                    equity_fig.add_trace(
                        go.Scatter(
                            x=data['date'],
                            y=data['cumulative_return'],
                            mode='lines',
                            name='Strategy Equity',
                            line=dict(color='#388E3C', width=2)  # Positive color
                        )
                    )
                    equity_fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Equity Multiplier",
                        height=300,
                        template="plotly_white",
                        font=dict(family="Arial, sans-serif", size=12, color="#37474F"),
                        margin=dict(l=40, r=40, t=10, b=40),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    # Update gridlines
                    equity_fig.update_xaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    equity_fig.update_yaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    st.plotly_chart(equity_fig, use_container_width=True)
                    st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
                
                # Create additional charts for oscillators
                oscillator_indicators = [ind for ind in st.session_state.selected_indicators 
                                      if ind in ['rsi_14', 'cci', 'willr', 'stoch', 'mfi']]
                if oscillator_indicators:
                    st.markdown(get_chart_container_start_html("Oscillator Indicators"), unsafe_allow_html=True)
                    osc_fig = make_subplots(
                        rows=len(oscillator_indicators), 
                        cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        subplot_titles=[next((ind['name'] for ind in all_indicators if ind['id'] == osc_id), osc_id) 
                                       for osc_id in oscillator_indicators]
                    )
                    for i, indicator_id in enumerate(oscillator_indicators, 1):
                        if indicator_id == 'rsi_14' and 'rsi_14' in data.columns:
                            osc_fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['rsi_14'],
                                    mode='lines',
                                    name='RSI (14)',
                                    line=dict(color='#1A237E', width=1.5)  # Primary color
                                ),
                                row=i, col=1
                            )
                            osc_fig.add_hline(y=70, line_dash="dash", line_color="#D32F2F", row=i, col=1)  # Negative color
                            osc_fig.add_hline(y=30, line_dash="dash", line_color="#388E3C", row=i, col=1)  # Positive color
                        elif indicator_id == 'stoch' and 'stoch_k' in data.columns:
                            osc_fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['stoch_k'],
                                    mode='lines',
                                    name='Stochastic %K',
                                    line=dict(color='#1A237E', width=1.5)  # Primary color
                                ),
                                row=i, col=1
                            )
                            osc_fig.add_trace(
                                go.Scatter(
                                    x=data['date'],
                                    y=data['stoch_d'],
                                    mode='lines',
                                    name='Stochastic %D',
                                    line=dict(color='#FFA000', width=1.5)  # Warning color
                                ),
                                row=i, col=1
                            )
                            osc_fig.add_hline(y=80, line_dash="dash", line_color="#D32F2F", row=i, col=1)  # Negative color
                            osc_fig.add_hline(y=20, line_dash="dash", line_color="#388E3C", row=i, col=1)  # Positive color
                    osc_fig.update_layout(
                        height=180 * len(oscillator_indicators),
                        showlegend=True,
                        template="plotly_white",
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=1.02, 
                            xanchor="right", 
                            x=1,
                            font=dict(size=12)
                        ),
                        margin=dict(l=40, r=40, t=40, b=40),
                        font=dict(family="Arial, sans-serif", size=12, color="#37474F"),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    # Update gridlines
                    osc_fig.update_xaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    osc_fig.update_yaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    st.plotly_chart(osc_fig, use_container_width=True)
                    st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
                
                # Show MACD if selected
                if 'macd' in st.session_state.selected_indicators and 'macd' in data.columns:
                    st.markdown(get_chart_container_start_html("MACD Indicator"), unsafe_allow_html=True)
                    macd_fig = make_subplots(rows=1, cols=1)
                    macd_fig.add_trace(
                        go.Scatter(
                            x=data['date'],
                            y=data['macd'],
                            mode='lines',
                            name='MACD',
                            line=dict(color='#1A237E', width=1.5)  # Primary color
                        )
                    )
                    macd_fig.add_trace(
                        go.Scatter(
                            x=data['date'],
                            y=data['macd_signal'],
                            mode='lines',
                            name='Signal Line',
                            line=dict(color='#FFA000', width=1.5)  # Warning color
                        )
                    )
                    macd_fig.add_trace(
                        go.Bar(
                            x=data['date'],
                            y=data['macd_hist'],
                            name='Histogram',
                            marker_color=np.where(data['macd_hist'] >= 0, '#388E3C', '#D32F2F')  # Positive/negative colors
                        )
                    )
                    macd_fig.update_layout(
                        height=300,
                        showlegend=True,
                        template="plotly_white",
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=1.02, 
                            xanchor="right", 
                            x=1,
                            font=dict(size=12)
                        ),
                        margin=dict(l=40, r=40, t=10, b=40),
                        font=dict(family="Arial, sans-serif", size=12, color="#37474F"),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    # Update gridlines
                    macd_fig.update_xaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    macd_fig.update_yaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    st.plotly_chart(macd_fig, use_container_width=True)
                    st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
                
                # Display data table
                with st.expander("View Data Table"):
                    st.dataframe(data)
                
                # Download CSV button
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download Data as CSV",
                    data=csv,
                    file_name=f"{selected_stock}_{selected_period}_data.csv",
                    mime="text/csv"
                )
                
                # Store data in session state for other tabs
                st.session_state.stock_data = data
                st.session_state.selected_ticker = selected_stock

    # Indicators explanation
    with st.expander("Indicators Explanation"):
        st.subheader("Technical Indicators Overview")
        st.markdown("""
        This dashboard supports various technical indicators categorized as follows:
        - **Trend Indicators**: Help identify the direction of market movement
        - **Momentum Indicators**: Measure the rate of price changes
        - **Volatility Indicators**: Measure the rate of price fluctuations
        - **Volume Indicators**: Analyze trading volume to confirm price movements
        """)
        if st.session_state.selected_indicators:
            for indicator_id in st.session_state.selected_indicators:
                info = get_indicator_info(indicator_id)
                st.markdown(f"""
                **{info['name']}**
                {info['description']}
                *Interpretation*: {info['interpretation']}
                """)

    # Strategy explanation
    with st.expander("Trading Strategies Explanation"):
        st.subheader("Trading Strategies Overview")
        st.markdown("""
        This dashboard implements several common trading strategies that can be visualized and backtested:
        - **Moving Average Crossover**: Generates signals when a fast MA crosses a slow MA
        - **Bollinger Bands Bounce**: Identifies potential reversals when price touches the bands
        - **RSI Overbought/Oversold**: Uses RSI to identify potential reversal points
        - **MACD Crossover**: Generates signals when MACD crosses its signal line
        Each strategy comes with configurable parameters that can be adjusted to suit different markets and timeframes.
        """)
        selected_strategy = next((s for s in all_strategies if s["id"] == selected_strategy_id), None)
        if selected_strategy:
            st.markdown(f"""
            **{selected_strategy['name']}**
            {selected_strategy['description']}
            *Parameters*:
            """)
            for param in selected_strategy["parameters"]:
                st.markdown(f"- **{param['name']}**: Default value: {param['default']}")

# Forecasting Tab
with tab2:
    st.title("📈 Stock Price Forecasting")
    st.markdown("""
        Use Prophet time-series forecasting to predict future stock prices. 
        This model uses historical price data and technical indicators to generate forecasts.
    """)
    
    # Create a container for forecast controls
    forecast_container = st.container()
    
    # Create a dedicated "Fetch Data for Forecasting" button inside this tab
    if st.button("Fetch Data for Forecasting", key="fetch_forecast_btn"):
        with st.spinner(f'Fetching data for {selected_stock}...'):
            data, error,cache_info = get_stock_data(
                selected_stock, 
                period=selected_period,
                fmp_api_key = fmp_api_key
            )
            if cache_info and cache_info.get("used", False):
                    last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                    if cache_info and cache_info.get("used", False):
                        st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                    else:
                        st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
            
            if error:
                st.error(f"Error: {error}")
            elif data is None or data.empty:
                st.error(f"No data available for {selected_stock}")
            else:
                # Store data in session state so it persists
                st.session_state.forecast_data = data
                
                # Calculate selected indicators for potential use in forecasting
                if st.session_state.selected_indicators:
                    st.session_state.forecast_data = calculate_indicators(st.session_state.forecast_data, st.session_state.selected_indicators)
                
                # Display basic stock info
                latest_data = st.session_state.forecast_data.iloc[-1]
                st.markdown(
                    get_kpi_card_html(
                        "Current Price", 
                        f"${latest_data['close']:.2f}", 
                        subtitle="Available for forecasting"
                    ),
                    unsafe_allow_html=True
                )
                
                st.success(f"Data for {selected_stock} successfully loaded! You can now generate a forecast below.")
    
    # Check if we have forecast data stored
    if 'forecast_data' in st.session_state:
        with forecast_container:
            # Render the Prophet forecasting UI
            render_forecast_ui(st.session_state.forecast_data, selected_stock, selected_period)
    else:
        with forecast_container:
            st.info("Click 'Fetch Data for Forecasting' above to load stock data before generating a forecast.")

# Sentiment Analysis Tab
with tab3:
    st.title("📰 Stock Sentiment Analysis")
    st.markdown("""
        Analyze sentiment from news articles and social media to gauge market perception.
        This can provide additional context to technical analysis and forecasting.
    """)
    
    if enable_sentiment and fetch_button:
        with st.spinner(f"Analyzing sentiment for {selected_stock}..."):
            sentiment_data = fetch_sentiment_data(
                selected_stock, 
                days=sentiment_days,
                use_cache=use_sentiment_cache
            )
            if sentiment_data:
                metrics = calculate_sentiment_metrics(sentiment_data)
                sentiment_score = metrics["avg_sentiment"]
                sentiment_color = get_sentiment_score_color(sentiment_score)
                
                st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    sentiment_class = "positive" if sentiment_score > 0.5 else "negative"
                    delta = sentiment_score - 0.5
                    st.markdown(
                        get_kpi_card_html(
                            "Overall Sentiment", 
                            f"{sentiment_score:.2f}", 
                            f"{abs(delta):.2f}", 
                            "from neutral", 
                            delta >= 0
                        ),
                        unsafe_allow_html=True
                    )
                with col2:
                    sentiment_label = "Bullish" if sentiment_score > 0.6 else "Bearish" if sentiment_score < 0.4 else "Neutral"
                    st.markdown(
                        get_kpi_card_html(
                            "Market Sentiment", 
                            sentiment_label
                        ),
                        unsafe_allow_html=True
                    )
                with col3:
                    st.markdown(
                        get_kpi_card_html(
                            "Data Sources", 
                            f"{sentiment_data['summary']['reddit_submissions_count'] + sentiment_data['summary']['news_articles_count']} total sources",
                            subtitle=f"Reddit: {sentiment_data['summary']['reddit_submissions_count']} | News: {sentiment_data['summary']['news_articles_count']}"
                        ),
                        unsafe_allow_html=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Sentiment charts in a container
                st.markdown(get_chart_container_start_html("Sentiment Analysis"), unsafe_allow_html=True)
                trend_fig, dist_fig = create_sentiment_charts(metrics)
                
                # Update chart styling
                for fig in [trend_fig, dist_fig]:
                    fig.update_layout(
                        template="plotly_white",
                        font=dict(family="Arial, sans-serif", size=12, color="#37474F"),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=40, r=40, t=40, b=40),
                    )
                    fig.update_xaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                    fig.update_yaxes(
                        showgrid=True,
                        gridcolor='#ECEFF1',
                        zeroline=False
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(trend_fig, use_container_width=True)
                with col2:
                    st.plotly_chart(dist_fig, use_container_width=True)
                st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
                
                # AI Analysis
                st.markdown(get_chart_container_start_html("AI Sentiment Analysis"), unsafe_allow_html=True)
                cache_file = f"cache/sentiment/{selected_stock}_analysis.txt"
                analysis = None
                if use_sentiment_cache and os.path.exists(cache_file):
                    cache_age = time.time() - os.path.getmtime(cache_file)
                    if cache_age < 21600:  # 6 hours
                        with open(cache_file, 'r') as f:
                            analysis = f.read()
                        st.info("Using cached analysis (less than 6 hours old)")
                if analysis is None:
                    analysis = analyze_sentiment(sentiment_data, api_key=openrouter_key)
                st.markdown(analysis)
                st.markdown(get_chart_container_end_html(), unsafe_allow_html=True)
            else:
                st.error(f"Could not fetch sentiment data for {selected_stock}")
    elif not enable_sentiment:
        st.info("Enable Sentiment Analysis in the sidebar to see results here.")
    elif not fetch_button:
        st.info("Click 'Fetch Data & Generate Charts' in the sidebar to load sentiment analysis.")

# Risk Analysis Tab
with tab4:
    st.title("⚠️ Stock Risk Analysis")
    st.markdown("""
        Comprehensive risk assessment to understand the potential downside and volatility characteristics.
        This analysis helps in determining if a stock's risk profile matches your investment goals.
    """)
    
    # Create a container for risk analysis
    risk_container = st.container()
    
    # Check if we have data stored from the Technical Analysis tab
    if fetch_button and 'stock_data' in st.session_state:
        with risk_container:
            # If benchmark comparison is enabled, fetch benchmark data
            benchmark_data = None
            if enable_benchmark:
                with st.spinner(f"Fetching benchmark data ({benchmark_ticker})..."):
                    benchmark_data, error,cache_info = get_stock_data(
                        benchmark_ticker, 
                        period=selected_period,
                        fmp_api_key = fmp_api_key
                    )
                    if cache_info and cache_info.get("used", False):
                        last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                        if cache_info and cache_info.get("used", False):
                            st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                        else:
                            st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
                    if error:
                        st.warning(f"Error fetching benchmark data: {error}")
                        st.info("Proceeding with risk analysis without benchmark comparison.")
                    elif benchmark_data is None or benchmark_data.empty:
                        st.warning(f"No data available for benchmark {benchmark_ticker}")
                        st.info("Proceeding with risk analysis without benchmark comparison.")
            
            # Render the Risk Analysis UI
            render_risk_metrics_ui(selected_stock, st.session_state.stock_data, benchmark_data)
    elif 'stock_data' in st.session_state:
        with risk_container:
            # If benchmark comparison is enabled, fetch benchmark data
            benchmark_data = None
            if enable_benchmark:
                with st.spinner(f"Fetching benchmark data ({benchmark_ticker})..."):
                    benchmark_data, error,cache_info = get_stock_data(
                        benchmark_ticker, 
                        period=selected_period,
                        fmp_api_key = fmp_api_key
                    )
                    if cache_info and cache_info.get("used", False):
                        last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                        if cache_info and cache_info.get("used", False):
                            st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                        else:
                            st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
                    if error:
                        st.warning(f"Error fetching benchmark data: {error}")
                        st.info("Proceeding with risk analysis without benchmark comparison.")
                    elif benchmark_data is None or benchmark_data.empty:
                        st.warning(f"No data available for benchmark {benchmark_ticker}")
                        st.info("Proceeding with risk analysis without benchmark comparison.")
                        
            # Render the Risk Analysis UI with previously loaded data
            render_risk_metrics_ui(st.session_state.selected_ticker, st.session_state.stock_data, benchmark_data)
    else:
        with risk_container:
            st.info("Click 'Fetch Data & Generate Charts' in the sidebar to load risk analysis.")

# Comparative Analysis Tab
with tab5:
    st.title("🔍 Comparative Stock Analysis")
    st.markdown("""
        Compare multiple stocks to identify relative strength, correlation, and performance differences.
        This helps in making informed decisions when considering alternative investments.
    """)
    
    if enable_comparison:
        if fetch_button:
            if not comparison_tickers:
                st.warning("Please select at least one comparison stock in the sidebar.")
            else:
                with st.spinner(f"Fetching comparison data for {', '.join(comparison_tickers)}..."):
                    # Fetch data for the main stock if not already available
                    if 'stock_data' not in st.session_state:
                        main_data, error,cache_info = get_stock_data(
                            selected_stock, 
                            period=selected_period,
                            fmp_api_key=fmp_api_key
                        )
                        if cache_info and cache_info.get("used", False):
                            last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                            if cache_info and cache_info.get("used", False):
                                st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                            else:
                                st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
                        if error:
                            st.error(f"Error fetching data for {selected_stock}: {error}")
                            main_data = None
                    else:
                        main_data = st.session_state.stock_data
                    
                    if main_data is not None and not main_data.empty:
                        comparative_data = {selected_stock: main_data}
                        for comp_ticker in comparison_tickers:
                            comp_data, comp_error,cache_info = get_stock_data(
                                comp_ticker, 
                                period=selected_period,
                                fmp_api_key=fmp_api_key
                            )
                            if cache_info and cache_info.get("used", False):
                                last_updated = cache_info.get("last_updated").strftime('%Y-%m-%d %H:%M:%S')
                                if cache_info and cache_info.get("used", False):
                                    st.info(f"📊 Using demo data for {selected_stock}. This is pre-cached example data.")
                                else:
                                    st.info(f"📦 Using cached data for {selected_stock}. Last updated: {last_updated}")
                            if not comp_error and comp_data is not None and not comp_data.empty:
                                comparative_data[comp_ticker] = comp_data
                            else:
                                st.warning(f"Error fetching data for {comp_ticker}: {comp_error or 'No data'}")
                        
                        if len(comparative_data) > 1:
                            # Store in session state
                            st.session_state.comparative_data = comparative_data
                            render_comparative_analysis_ui(comparative_data)
                        else:
                            st.warning("Need at least two stocks with valid data for comparison.")
                    else:
                        st.error(f"No data available for the main stock {selected_stock}")
        elif 'comparative_data' in st.session_state:
            # Render UI with stored data if available
            render_comparative_analysis_ui(st.session_state.comparative_data)
        else:
            st.info("Click 'Fetch Data & Generate Charts' in the sidebar to load comparison data.")
    else:
        st.info("Enable Stock Comparison in the sidebar to compare multiple stocks.")

# Footer (outside tabs)
st.markdown(get_footer_html(), unsafe_allow_html=True)