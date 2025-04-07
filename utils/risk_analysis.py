import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
import requests
import os 
from dotenv import load_dotenv

load_dotenv()

# Add the get_api_key utility function
def get_api_key(key_name, default=""):
    """Get API key with fallback logic"""
    # First check session state
    if "api_keys" in st.session_state and key_name in st.session_state.api_keys and st.session_state.api_keys[key_name]:
        return st.session_state.api_keys[key_name]
    # Then fall back to environment variable
    return os.getenv(key_name, default)

def calculate_risk_metrics(df, benchmark_df=None, risk_free_rate=0.03, period_days=252):
    """
    Calculate comprehensive risk metrics for a stock.
    
    Args:
        df (pd.DataFrame): DataFrame with stock price data
        benchmark_df (pd.DataFrame, optional): DataFrame with benchmark data (e.g., S&P 500)
        risk_free_rate (float): Annual risk-free rate as decimal (default: 3%)
        period_days (int): Trading days per year (default: 252)
    
    Returns:
        dict: Dictionary containing risk metrics
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Sort by date to ensure chronological order
    df = df.sort_values('date')
    
    # Calculate daily returns
    df['daily_return'] = df['close'].pct_change()
    
    # Calculate logarithmic returns (better for statistical analysis)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    # Calculate benchmark returns if available
    if benchmark_df is not None:
        benchmark_df = benchmark_df.copy()
        benchmark_df = benchmark_df.sort_values('date')
        benchmark_df['daily_return'] = benchmark_df['close'].pct_change()
        
        # Align dates between stock and benchmark
        aligned_data = pd.merge(
            df[['date', 'daily_return']].rename(columns={'daily_return': 'stock_return'}),
            benchmark_df[['date', 'daily_return']].rename(columns={'daily_return': 'benchmark_return'}),
            on='date', how='inner'
        )
        
        # Calculate beta if we have enough aligned data points
        if len(aligned_data) > 20:
            covariance = aligned_data['stock_return'].cov(aligned_data['benchmark_return'])
            benchmark_variance = aligned_data['benchmark_return'].var()
            beta = covariance / benchmark_variance if benchmark_variance != 0 else np.nan
        else:
            beta = np.nan
    else:
        beta = np.nan
    
    # Drop NaN values from returns
    returns = df['daily_return'].dropna()
    log_returns = df['log_return'].dropna()
    
    # Calculate volatility metrics
    daily_volatility = returns.std()
    annual_volatility = daily_volatility * np.sqrt(period_days)
    
    # Calculate downside deviation (only negative returns)
    downside_returns = returns[returns < 0]
    downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
    
    # Calculate average return
    avg_daily_return = returns.mean()
    avg_annual_return = ((1 + avg_daily_return) ** period_days) - 1
    
    # Calculate Sharpe ratio
    daily_risk_free = ((1 + risk_free_rate) ** (1 / period_days)) - 1
    excess_return = avg_daily_return - daily_risk_free
    sharpe_ratio = (excess_return / daily_volatility) * np.sqrt(period_days) if daily_volatility != 0 else 0
    
    # Calculate Sortino ratio (using downside deviation)
    sortino_ratio = (excess_return / downside_deviation) * np.sqrt(period_days) if downside_deviation != 0 else 0
    
    # Calculate drawdowns
    df['cum_return'] = (1 + df['daily_return']).cumprod()
    df['running_max'] = df['cum_return'].cummax()
    df['drawdown'] = df['cum_return'] / df['running_max'] - 1
    max_drawdown = df['drawdown'].min()
    
    # Calculate Calmar ratio
    calmar_ratio = -avg_annual_return / max_drawdown if max_drawdown != 0 else 0
    
    # Calculate Value at Risk (VaR)
    var_95 = np.percentile(returns, 5)  # 95% confidence VaR
    var_99 = np.percentile(returns, 1)  # 99% confidence VaR
    
    # Calculate Conditional VaR (CVaR) / Expected Shortfall
    cvar_95 = returns[returns <= var_95].mean()
    cvar_99 = returns[returns <= var_99].mean()
    
    # Calculate ATR (Average True Range)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['true_range'].rolling(window=14).mean()
    
    # ATR as percentage of price
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # Calculate drawdown statistics
    drawdown_series = df['drawdown']
    underwater_periods = []
    current_period = None
    
    for i, (date, drawdown) in enumerate(zip(df['date'], drawdown_series)):
        if drawdown < 0:
            if current_period is None:
                current_period = {'start': date, 'start_idx': i}
        elif current_period is not None:
            current_period['end'] = df['date'].iloc[i-1]
            current_period['end_idx'] = i-1
            current_period['duration'] = (current_period['end'] - current_period['start']).days
            current_period['max_drawdown'] = df['drawdown'].iloc[current_period['start_idx']:current_period['end_idx']+1].min()
            underwater_periods.append(current_period)
            current_period = None
    
    # Handle case where we're still in a drawdown at the end of the data
    if current_period is not None:
        current_period['end'] = df['date'].iloc[-1]
        current_period['end_idx'] = len(df) - 1
        current_period['duration'] = (current_period['end'] - current_period['start']).days
        current_period['max_drawdown'] = df['drawdown'].iloc[current_period['start_idx']:current_period['end_idx']+1].min()
        underwater_periods.append(current_period)
    
    # Sort underwater periods by max drawdown (worst first)
    underwater_periods.sort(key=lambda x: x['max_drawdown'])
    
    # Calculate average drawdown and average recovery time
    if underwater_periods:
        avg_drawdown = sum(p['max_drawdown'] for p in underwater_periods) / len(underwater_periods)
        avg_duration = sum(p['duration'] for p in underwater_periods) / len(underwater_periods)
        max_duration = max(p['duration'] for p in underwater_periods) if underwater_periods else 0
    else:
        avg_drawdown = 0
        avg_duration = 0
        max_duration = 0
    
    # Check if we're currently in a drawdown
    current_drawdown = df['drawdown'].iloc[-1]
    days_in_current_drawdown = 0
    
    if current_drawdown < 0:
        # Find when this drawdown started
        last_peak_idx = df['running_max'].values.argmax()
        if last_peak_idx < len(df) - 1:  # Make sure we're not at the peak right now
            days_in_current_drawdown = (df['date'].iloc[-1] - df['date'].iloc[last_peak_idx]).days
    
    # Return comprehensive risk metrics
    return {
        'volatility': {
            'daily': daily_volatility,
            'annual': annual_volatility,
            'downside_deviation': downside_deviation
        },
        'returns': {
            'daily_avg': avg_daily_return,
            'annual_avg': avg_annual_return,
        },
        'risk_adjusted': {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio
        },
        'drawdown': {
            'max_drawdown': max_drawdown,
            'avg_drawdown': avg_drawdown,
            'avg_duration': avg_duration,
            'max_duration': max_duration,
            'current_drawdown': current_drawdown,
            'days_in_current_drawdown': days_in_current_drawdown,
            'underwater_periods': underwater_periods
        },
        'var': {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99
        },
        'technical': {
            'atr_last': df['atr'].iloc[-1] if not df['atr'].empty else np.nan,
            'atr_pct_last': df['atr_pct'].iloc[-1] if not df['atr_pct'].empty else np.nan,
            'beta': beta
        },
        'data': df
    }

def run_monte_carlo_simulation(df, num_simulations=1000, days=252, percentiles=[5, 25, 50, 75, 95]):
    """
    Run Monte Carlo simulation to project potential future price paths.
    
    Args:
        df (pd.DataFrame): DataFrame with stock price data
        num_simulations (int): Number of simulations to run
        days (int): Number of days to simulate
        percentiles (list): Percentiles to calculate for the simulation results
    
    Returns:
        dict: Dictionary containing simulation results
    """
    # Make a copy and ensure data is sorted
    df = df.copy().sort_values('date')
    
    # Calculate log returns
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    log_returns = df['log_return'].dropna()
    
    # Get parameters for the simulation
    mu = log_returns.mean()
    sigma = log_returns.std()
    
    # Starting price
    last_price = df['close'].iloc[-1]
    
    # Initialize simulation array
    simulation = np.zeros((days, num_simulations))
    simulation[0] = last_price
    
    # Generate random returns
    for i in range(1, days):
        # Generate random returns from normal distribution
        random_returns = np.random.normal(mu, sigma, num_simulations)
        simulation[i] = simulation[i-1] * np.exp(random_returns)
    
    # Calculate percentiles for each day
    percentile_results = {}
    for p in percentiles:
        percentile_results[p] = np.percentile(simulation, p, axis=1)
    
    # Calculate final price statistics
    final_prices = simulation[-1]
    final_returns = (final_prices / last_price) - 1
    
    # Expected final values and probabilities
    expected_return = final_returns.mean()
    probability_positive = (final_returns > 0).sum() / num_simulations
    
    # Value at Risk (VaR) from simulation
    var_95 = np.percentile(final_returns, 5)
    var_99 = np.percentile(final_returns, 1)
    
    return {
        'simulation': simulation,
        'percentiles': percentile_results,
        'last_price': last_price,
        'days': days,
        'stats': {
            'expected_return': expected_return,
            'probability_positive': probability_positive,
            'var_95': var_95,
            'var_99': var_99,
            'final_price_mean': final_prices.mean(),
            'final_price_median': np.median(final_prices),
            'final_price_std': final_prices.std()
        }
    }

def plot_drawdowns(metrics):
    """
    Create drawdown visualization.
    
    Args:
        metrics (dict): Risk metrics from calculate_risk_metrics
    
    Returns:
        plotly.graph_objects.Figure: Drawdown chart
    """
    df = metrics['data']
    
    # Create figure
    fig = go.Figure()
    
    # Add drawdown area chart
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['drawdown'] * 100,  # Convert to percentage
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(220, 38, 38, 0.5)', width=1),
            name='Drawdown'
        )
    )
    
    # Highlight underwater periods
    for period in metrics['drawdown']['underwater_periods'][:5]:  # Show top 5 worst drawdowns
        if period['max_drawdown'] <= -0.05:  # Only highlight significant drawdowns (>= 5%)
            fig.add_vrect(
                x0=period['start'],
                x1=period['end'],
                fillcolor="rgba(220, 38, 38, 0.1)",
                layer="below",
                line_width=0,
            )
    
    # Add zero line
    fig.add_shape(
        type="line",
        x0=df['date'].iloc[0],
        y0=0,
        x1=df['date'].iloc[-1],
        y1=0,
        line=dict(color="black", width=1, dash="solid")
    )
    
    # Update layout
    fig.update_layout(
        title="Drawdown Analysis",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        height=400,
        hovermode="x unified",
        yaxis=dict(tickformat=".1f")
    )
    
    # Update y-axis to be reversed (negative values at top)
    fig.update_yaxes(autorange="reversed")
    
    return fig

def plot_monte_carlo(simulation_results):
    """
    Create Monte Carlo simulation visualization.
    
    Args:
        simulation_results (dict): Results from run_monte_carlo_simulation
    
    Returns:
        plotly.graph_objects.Figure: Monte Carlo simulation chart
    """
    # Create figure
    fig = go.Figure()
    
    # Create date range for x-axis
    start_date = datetime.now()
    dates = [start_date + timedelta(days=i) for i in range(simulation_results['days'])]
    
    # Add percentile lines
    percentiles = simulation_results['percentiles']
    
    # Add median line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=percentiles[50],
            mode='lines',
            line=dict(color='blue', width=2),
            name='Median Projection'
        )
    )
    
    # Add 25-75 percentile range
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=percentiles[75],
            mode='lines',
            line=dict(color='rgba(0, 0, 255, 0)', width=0),
            showlegend=False
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=percentiles[25],
            mode='lines',
            line=dict(color='rgba(0, 0, 255, 0)', width=0),
            fill='tonexty',
            fillcolor='rgba(0, 0, 255, 0.2)',
            name='50% Confidence Interval'
        )
    )
    
    # Add 5-95 percentile range
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=percentiles[95],
            mode='lines',
            line=dict(color='rgba(173, 216, 230, 0)', width=0),
            showlegend=False
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=percentiles[5],
            mode='lines',
            line=dict(color='rgba(173, 216, 230, 0)', width=0),
            fill='tonexty',
            fillcolor='rgba(173, 216, 230, 0.2)',
            name='90% Confidence Interval'
        )
    )
    
    # Add horizontal line at the last known price
    fig.add_shape(
        type="line",
        x0=dates[0],
        y0=simulation_results['last_price'],
        x1=dates[0],
        y1=simulation_results['last_price'],
        line=dict(color="red", width=3, dash="dash")
    )
    
    # Update layout
    fig.update_layout(
        title="Monte Carlo Price Simulation",
        xaxis_title="Date",
        yaxis_title="Projected Price ($)",
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def plot_var_analysis(metrics):
    """
    Create Value at Risk visualization.
    
    Args:
        metrics (dict): Risk metrics from calculate_risk_metrics
    
    Returns:
        plotly.graph_objects.Figure: VaR analysis chart
    """
    daily_returns = metrics['data']['daily_return'].dropna()
    
    # Create histogram of daily returns
    fig = go.Figure()
    
    fig.add_trace(
        go.Histogram(
            x=daily_returns * 100,  # Convert to percentage
            nbinsx=50,
            histnorm='probability',
            marker_color='rgba(0, 114, 189, 0.6)',
            name='Daily Returns'
        )
    )
    
    # Add VaR lines
    var_95 = metrics['var']['var_95'] * 100
    var_99 = metrics['var']['var_99'] * 100
    
    fig.add_trace(
        go.Scatter(
            x=[var_95, var_95],
            y=[0, 0.08],  # Adjust based on your histogram height
            mode='lines',
            line=dict(color='red', width=2, dash='dash'),
            name='95% VaR'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=[var_99, var_99],
            y=[0, 0.08],  # Adjust based on your histogram height
            mode='lines',
            line=dict(color='darkred', width=2, dash='dash'),
            name='99% VaR'
        )
    )
    
    # Add annotations
    fig.add_annotation(
        x=var_95,
        y=0.07,
        text=f"95% VaR: {var_95:.2f}%",
        showarrow=True,
        arrowhead=1,
        ax=-50,
        ay=-30
    )
    
    fig.add_annotation(
        x=var_99,
        y=0.06,
        text=f"99% VaR: {var_99:.2f}%",
        showarrow=True,
        arrowhead=1,
        ax=-50,
        ay=30
    )
    
    # Update layout
    fig.update_layout(
        title="Value at Risk (VaR) Analysis",
        xaxis_title="Daily Return (%)",
        yaxis_title="Probability",
        height=400,
        bargap=0.1,
        xaxis=dict(tickformat=".1f")
    )
    
    return fig

def render_risk_metrics_ui(ticker, data,benchmark_data=None):
    """
    Render the risk metrics UI in Streamlit.
    
    Args:
        ticker (str): Stock ticker symbol
        data (pd.DataFrame): DataFrame with stock price data
    """
    st.subheader("Risk Analysis Dashboard")
    
    # Calculate risk metrics
    with st.spinner("Calculating risk metrics..."):
        metrics = calculate_risk_metrics(data)
    
    # Create a tab layout for different risk analysis components
    risk_tabs = st.tabs([
        "Key Metrics", 
        "Drawdown Analysis", 
        "VaR & Distributions", 
        "Monte Carlo Simulation"
    ])
    
    # Key Metrics Tab
    with risk_tabs[0]:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Annualized Volatility",
                value=f"{metrics['volatility']['annual'] * 100:.2f}%"
            )
            st.metric(
                label="Max Drawdown",
                value=f"{metrics['drawdown']['max_drawdown'] * 100:.2f}%"
            )
            st.metric(
                label="Beta",
                value=f"{metrics['technical']['beta']:.2f}" if not np.isnan(metrics['technical']['beta']) else "N/A"
            )
        
        with col2:
            st.metric(
                label="Sharpe Ratio",
                value=f"{metrics['risk_adjusted']['sharpe_ratio']:.2f}"
            )
            st.metric(
                label="Sortino Ratio",
                value=f"{metrics['risk_adjusted']['sortino_ratio']:.2f}"
            )
            st.metric(
                label="Calmar Ratio",
                value=f"{metrics['risk_adjusted']['calmar_ratio']:.2f}"
            )
        
        with col3:
            st.metric(
                label="Daily VaR (95%)",
                value=f"{metrics['var']['var_95'] * 100:.2f}%"
            )
            st.metric(
                label="Current Drawdown",
                value=f"{metrics['drawdown']['current_drawdown'] * 100:.2f}%"
            )
            st.metric(
                label="ATR (% of Price)",
                value=f"{metrics['technical']['atr_pct_last']:.2f}%"
            )
        
        # Risk metrics details
        with st.expander("Detailed Risk Metrics", expanded=True):
            st.markdown("""
            ### Volatility Metrics
            - **Daily Volatility**: Standard deviation of daily returns.
            - **Annualized Volatility**: Daily volatility scaled to an annual measure.
            - **Downside Deviation**: Standard deviation of negative returns only.
            
            ### Risk-Adjusted Return Metrics
            - **Sharpe Ratio**: Return in excess of the risk-free rate per unit of risk.
            - **Sortino Ratio**: Return in excess of the risk-free rate per unit of downside risk.
            - **Calmar Ratio**: Annual return divided by the maximum drawdown.
            
            ### Value at Risk (VaR)
            - **Daily VaR (95%)**: Maximum expected loss on 95% of days.
            - **Daily VaR (99%)**: Maximum expected loss on 99% of days.
            - **Conditional VaR (95%)**: Expected loss when exceeding the 95% VaR.
            """)
            
            # Detailed metrics table
            detailed_metrics = {
                "Volatility": {
                    "Daily Volatility": f"{metrics['volatility']['daily'] * 100:.4f}%",
                    "Annualized Volatility": f"{metrics['volatility']['annual'] * 100:.4f}%",
                    "Downside Deviation": f"{metrics['volatility']['downside_deviation'] * 100:.4f}%"
                },
                "Returns": {
                    "Avg. Daily Return": f"{metrics['returns']['daily_avg'] * 100:.4f}%",
                    "Avg. Annual Return": f"{metrics['returns']['annual_avg'] * 100:.4f}%",
                },
                "Risk-Adjusted": {
                    "Sharpe Ratio": f"{metrics['risk_adjusted']['sharpe_ratio']:.4f}",
                    "Sortino Ratio": f"{metrics['risk_adjusted']['sortino_ratio']:.4f}",
                    "Calmar Ratio": f"{metrics['risk_adjusted']['calmar_ratio']:.4f}"
                },
                "Value at Risk": {
                    "Daily VaR (95%)": f"{metrics['var']['var_95'] * 100:.4f}%",
                    "Daily VaR (99%)": f"{metrics['var']['var_99'] * 100:.4f}%",
                    "Conditional VaR (95%)": f"{metrics['var']['cvar_95'] * 100:.4f}%",
                    "Conditional VaR (99%)": f"{metrics['var']['cvar_99'] * 100:.4f}%"
                },
                "Drawdown": {
                    "Maximum Drawdown": f"{metrics['drawdown']['max_drawdown'] * 100:.4f}%",
                    "Average Drawdown": f"{metrics['drawdown']['avg_drawdown'] * 100:.4f}%",
                    "Max Drawdown Duration": f"{metrics['drawdown']['max_duration']} days",
                    "Current Drawdown": f"{metrics['drawdown']['current_drawdown'] * 100:.4f}%",
                    "Days in Current Drawdown": f"{metrics['drawdown']['days_in_current_drawdown']}"
                },
                "Technical": {
                    "ATR (14-day)": f"${metrics['technical']['atr_last']:.4f}",
                    "ATR (% of Price)": f"{metrics['technical']['atr_pct_last']:.4f}%",
                    "Beta": f"{metrics['technical']['beta']:.4f}" if not np.isnan(metrics['technical']['beta']) else "N/A"
                }
            }
            
            # Display the detailed metrics in a more structured way
            for category, metrics_dict in detailed_metrics.items():
                st.markdown(f"**{category}**")
                metrics_df = pd.DataFrame(list(metrics_dict.items()), columns=["Metric", "Value"])
                st.dataframe(metrics_df, hide_index=True)
    
    # Drawdown Analysis Tab
    with risk_tabs[1]:
        drawdown_fig = plot_drawdowns(metrics)
        st.plotly_chart(drawdown_fig, use_container_width=True)
        
        # Drawdown periods table
        st.subheader("Major Drawdown Periods")
        
        underwater_periods = metrics['drawdown']['underwater_periods']
        if underwater_periods:
            # Sort by max drawdown (worst first)
            underwater_periods.sort(key=lambda x: x['max_drawdown'])
            
            # Create a table of the worst drawdowns
            worst_drawdowns = underwater_periods[:5]  # Show top 5 worst drawdowns
            
            drawdown_data = []
            for period in worst_drawdowns:
                drawdown_data.append({
                    "Start Date": period['start'].strftime('%Y-%m-%d'),
                    "End Date": period['end'].strftime('%Y-%m-%d'),
                    "Duration (Days)": period['duration'],
                    "Max Drawdown": f"{period['max_drawdown'] * 100:.2f}%"
                })
            
            drawdown_df = pd.DataFrame(drawdown_data)
            st.dataframe(drawdown_df, hide_index=True)
        else:
            st.info("No significant drawdown periods detected in the data.")
    
    # VaR & Distributions Tab
    with risk_tabs[2]:
        var_fig = plot_var_analysis(metrics)
        st.plotly_chart(var_fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="Expected Daily Loss (95% VaR)",
                value=f"{metrics['var']['var_95'] * 100:.2f}% of investment"
            )
            st.metric(
                label="Expected Daily Loss (99% VaR)",
                value=f"{metrics['var']['var_99'] * 100:.2f}% of investment"
            )
        
        with col2:
            # Convert VaR to dollar amount for a hypothetical $10,000 investment
            investment_amount = 10000
            var_95_dollars = abs(metrics['var']['var_95'] * investment_amount)
            var_99_dollars = abs(metrics['var']['var_99'] * investment_amount)
            
            st.metric(
                label=f"$ Loss on ${investment_amount:,} investment (95% VaR)",
                value=f"${var_95_dollars:.2f}"
            )
            st.metric(
                label=f"$ Loss on ${investment_amount:,} investment (99% VaR)",
                value=f"${var_99_dollars:.2f}"
            )
        
        # VaR explanation
        st.markdown("""
        ### Understanding Value at Risk (VaR)
        
        Value at Risk measures the maximum expected loss over a specific time period at a given confidence level.
        
        - **95% VaR**: On 95% of days, your losses should not exceed this amount. Conversely, on 5% of days, losses may be larger.
        - **99% VaR**: On 99% of days, your losses should not exceed this amount. Conversely, on 1% of days, losses may be larger.
        - **Conditional VaR (CVaR)**: The expected loss during the worst days that exceed the VaR threshold.
        
        VaR is useful for understanding potential downside risk, but it doesn't tell you how severe losses might be beyond the threshold.
        """)
    
    # Monte Carlo Simulation Tab
    with risk_tabs[3]:
        # Monte Carlo simulation controls
        st.markdown("### Monte Carlo Simulation Settings")
        
        sim_col1, sim_col2 = st.columns(2)
        
        with sim_col1:
            num_simulations = st.slider(
                "Number of Simulations",
                min_value=100,
                max_value=5000,
                value=1000,
                step=100,
                help="More simulations provide more stable results but take longer to compute"
            )
        
        with sim_col2:
            forecast_days = st.slider(
                "Forecast Days",
                min_value=30,
                max_value=504,  # About 2 years of trading days
                value=252,  # About 1 year of trading days
                step=21,
                help="Number of trading days to forecast (252 ≈ 1 year)"
            )
        
        # Run simulation when user clicks button
        if st.button("Run Monte Carlo Simulation"):
            with st.spinner("Running Monte Carlo simulation..."):
                mc_results = run_monte_carlo_simulation(
                    data,
                    num_simulations=num_simulations,
                    days=forecast_days
                )
                
                # Plot simulation results
                mc_fig = plot_monte_carlo(mc_results)
                st.plotly_chart(mc_fig, use_container_width=True)
                
                # Display simulation statistics
                st.subheader("Simulation Statistics")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="Expected Return",
                        value=f"{mc_results['stats']['expected_return'] * 100:.2f}%"
                    )
                    st.metric(
                        label="Final Price (Mean)",
                        value=f"${mc_results['stats']['final_price_mean']:.2f}"
                    )
                
                with col2:
                    st.metric(
                        label="Probability of Positive Return",
                        value=f"{mc_results['stats']['probability_positive'] * 100:.2f}%"
                    )
                    st.metric(
                        label="Final Price (Median)",
                        value=f"${mc_results['stats']['final_price_median']:.2f}"
                    )
                
                with col3:
                    st.metric(
                        label="Potential Downside (5th percentile)",
                        value=f"{mc_results['stats']['var_95'] * 100:.2f}%"
                    )
                    st.metric(
                        label="Price Volatility",
                        value=f"${mc_results['stats']['final_price_std']:.2f}"
                    )
                
                # Monte Carlo explanation
                with st.expander("Understanding Monte Carlo Simulation"):
                    st.markdown("""
                    ### How Monte Carlo Simulation Works
                    
                    The simulation generates thousands of potential future price paths based on the stock's historical volatility and returns.
                    
                    **Key insights:**
                    
                    - **Median Projection** (50th percentile): The middle path among all simulations.
                    - **50% Confidence Interval** (25th-75th percentiles): There's a 50% chance the actual price will fall within this range.
                    - **90% Confidence Interval** (5th-95th percentiles): There's a 90% chance the actual price will fall within this range.
                    
                    **Limitations:** This simulation assumes returns follow a log-normal distribution and that past volatility patterns will continue in the future. It doesn't account for extreme events, regime changes, or fundamental shifts in the company or market.
                    """)
        else:
            st.info("Click 'Run Monte Carlo Simulation' to see potential future price paths.")
    
    # AI Risk Analysis
    st.subheader("AI Risk Interpretation")
    
    if st.button("Generate AI Risk Analysis"):
        with st.spinner("Analyzing risk metrics with AI..."):
            risk_interpretation = generate_risk_analysis(ticker, metrics)
            st.markdown(risk_interpretation)
    else:
        st.info("Click 'Generate AI Risk Analysis' for an AI-powered interpretation of these risk metrics.")

def generate_risk_analysis(ticker, metrics):
    """
    Generate an AI interpretation of risk metrics using Gemini via OpenRouter.
    
    Args:
        ticker (str): Stock ticker symbol
        metrics (dict): Risk metrics
    
    Returns:
        str: AI-generated risk analysis
    """
    # Check if in demo mode
    demo_mode = st.session_state.get("demo_mode", False)
    
    # Use appropriate cache directory based on mode
    cache_dir = "demo_cache/risk" if demo_mode else "cache/risk"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{cache_dir}/{ticker}_risk_analysis.txt"
    
    # Check if we have cached analysis first (for demo mode)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                print(f"Using cached {'demo ' if demo_mode else ''}risk analysis for {ticker}")
                return f.read()
        except Exception as e:
            print(f"Error reading cached risk analysis: {str(e)}")
    
    # Format the metrics to include in the prompt
    beta_val = metrics['technical']['beta']
    beta_str = f"{beta_val:.2f}" if not np.isnan(beta_val) else "N/A"
    metrics_summary = f"""
    Ticker: {ticker}
    
    Volatility Metrics:
    - Annualized Volatility: {metrics['volatility']['annual'] * 100:.2f}%
    - Daily Volatility: {metrics['volatility']['daily'] * 100:.4f}%
    - Downside Deviation: {metrics['volatility']['downside_deviation'] * 100:.4f}%
    
    Return Metrics:
    - Average Daily Return: {metrics['returns']['daily_avg'] * 100:.4f}%
    - Average Annual Return: {metrics['returns']['annual_avg'] * 100:.4f}%
    
    Risk-Adjusted Metrics:
    - Sharpe Ratio: {metrics['risk_adjusted']['sharpe_ratio']:.4f}
    - Sortino Ratio: {metrics['risk_adjusted']['sortino_ratio']:.4f}
    - Calmar Ratio: {metrics['risk_adjusted']['calmar_ratio']:.4f}
    
    Drawdown Analysis:
    - Maximum Drawdown: {metrics['drawdown']['max_drawdown'] * 100:.2f}%
    - Average Drawdown: {metrics['drawdown']['avg_drawdown'] * 100:.2f}%
    - Maximum Drawdown Duration: {metrics['drawdown']['max_duration']} days
    - Current Drawdown: {metrics['drawdown']['current_drawdown'] * 100:.2f}%
    - Days in Current Drawdown: {metrics['drawdown']['days_in_current_drawdown']}
    
    Value at Risk:
    - Daily VaR (95%): {metrics['var']['var_95'] * 100:.2f}%
    - Daily VaR (99%): {metrics['var']['var_99'] * 100:.2f}%
    - Conditional VaR (95%): {metrics['var']['cvar_95'] * 100:.2f}%
    
    Technical:
    - ATR (14-day): ${metrics['technical']['atr_last']:.2f}
    - ATR (% of Price): {metrics['technical']['atr_pct_last']:.2f}%
    - Beta: {beta_str}

    """
    
    # Don't make API calls in demo mode if we don't have cached data
    if demo_mode and not os.path.exists(cache_file):
        fallback_analysis = f"""
        # Risk Analysis for {ticker}

        No demo risk analysis available. In production mode, a comprehensive risk assessment would be generated here.
        
        ## Risk Metrics Summary
        
        - Maximum Drawdown: {metrics['drawdown']['max_drawdown'] * 100:.2f}%
        - Annualized Volatility: {metrics['volatility']['annual'] * 100:.2f}%
        - Sharpe Ratio: {metrics['risk_adjusted']['sharpe_ratio']:.2f}
        """
        
        # Save the fallback analysis to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(fallback_analysis)
            
        return fallback_analysis
    
    # Build the prompt for Gemini
    prompt = f"""You are an expert financial risk analyst. Based on the risk metrics provided below for {ticker} stock, provide a thorough risk analysis and interpretation.

    {metrics_summary}

    Please structure your analysis as follows:
    1. Risk Profile Summary - A concise overview of the stock's overall risk profile
    2. Volatility Analysis - Interpret what the volatility metrics suggest about price stability
    3. Drawdown Analysis - Assess the severity and frequency of drawdowns and what they indicate
    4. Risk-Adjusted Return - Evaluate the return metrics in the context of risk taken
    5. Value at Risk Interpretation - Explain what the VaR numbers mean for a typical investor
    6. Risk Outlook - Provide a forward-looking perspective based on these metrics
    7. Investor Suitability - Suggest what type of investor might be appropriate for this risk profile

    Keep your analysis professional, data-driven, and provide specific insights that would help an investor understand the risk characteristics of this stock.
    """
    
    # Call the OpenRouter API to get Gemini analysis
    OPENROUTER_KEY = get_api_key("OPENROUTER_KEY") # Default key
    GEMINI_MODEL = "google/gemini-2.5-pro-exp-03-25:free"
    
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://stock-analyzer.app',
        'X-Title': 'Stock Analysis Dashboard'
    }
    
    payload = {
        'model': GEMINI_MODEL,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    try:
        print(f"Calling OpenRouter API for risk analysis of {ticker}...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        analysis = result.get('choices', [{}])[0].get('message', {}).get('content', 'No analysis generated')
        print(f"Successfully generated risk analysis for {ticker}")
        
        # Save to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(analysis)
        print(f"Saved risk analysis to cache: {cache_file}")
        
        return analysis
    except Exception as e:
        print(f"Error generating risk analysis: {str(e)}")
        
        fallback_analysis = f"""
        # AI Risk Analysis

        I couldn't generate a complete analysis at this time due to an API error: {str(e)}
        
        Based on the metrics shown above, here's a brief interpretation:
        
        - The maximum drawdown of {metrics['drawdown']['max_drawdown'] * 100:.2f}% indicates the largest historical drop from peak to trough.
        - With an annualized volatility of {metrics['volatility']['annual'] * 100:.2f}%, this stock shows {"high" if metrics['volatility']['annual'] > 0.25 else "moderate" if metrics['volatility']['annual'] > 0.15 else "relatively low"} price fluctuation.
        - The Sharpe ratio of {metrics['risk_adjusted']['sharpe_ratio']:.2f} suggests {"good" if metrics['risk_adjusted']['sharpe_ratio'] > 1 else "moderate" if metrics['risk_adjusted']['sharpe_ratio'] > 0.5 else "poor"} risk-adjusted returns.
        
        For a more detailed analysis, please try again later.
        """
        
        return fallback_analysis