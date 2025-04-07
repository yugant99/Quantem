import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import requests
import traceback
import os
import json
import hashlib
from datetime import datetime, timedelta

def calculate_comparative_metrics(data_dict, benchmark_data=None):
    """
    Calculate comparative metrics for multiple stocks.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with stock price data {ticker: dataframe}
        benchmark_data (pd.DataFrame, optional): DataFrame with benchmark data (e.g., S&P 500)
    
    Returns:
        dict: Dictionary containing comparative metrics
    """
    print(f"DEBUG: Starting comparative metrics calculation for {len(data_dict)} stocks")
    results = {}
    
    # Prepare data for correlation analysis
    correlation_data = {}
    returns_data = {}
    
    # Create a normalized price dataframe with all stocks for easy comparison
    normalized_prices = None
    
    # Process each stock's data
    for ticker, df in data_dict.items():
        print(f"DEBUG: Processing data for {ticker}, shape: {df.shape}")
        # Make a copy to avoid modifying the original dataframe
        df = df.copy().sort_values('date')
        
        # Calculate daily returns
        df['daily_return'] = df['close'].pct_change()
        
        # Calculate cumulative returns
        df['cum_return'] = (1 + df['daily_return']).cumprod()
        
        # Extract just the return series for correlation analysis
        returns_data[ticker] = df.set_index('date')['daily_return']
        
        # Extract close prices for correlation
        correlation_data[ticker] = df.set_index('date')['close']
        
        # Create normalized prices (starting at 100)
        if 'date' in df.columns and 'close' in df.columns:
            df_norm = df[['date', 'close']].copy()
            first_close = df_norm['close'].iloc[0]
            df_norm['normalized'] = df_norm['close'] / first_close * 100
            
            if normalized_prices is None:
                normalized_prices = df_norm[['date', 'normalized']].rename(columns={'normalized': ticker})
            else:
                normalized_prices = pd.merge(
                    normalized_prices, 
                    df_norm[['date', 'normalized']].rename(columns={'normalized': ticker}),
                    on='date', 
                    how='outer'
                )
        
        # Calculate volatility
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        log_returns = df['log_return'].dropna()
        
        # Calculate metrics like Volatility, Sharpe, etc.
        daily_volatility = df['daily_return'].std()
        annual_volatility = daily_volatility * np.sqrt(252)  # Annualized
        
        # Calculate max drawdown
        df['running_max'] = df['cum_return'].cummax()
        df['drawdown'] = df['cum_return'] / df['running_max'] - 1
        max_drawdown = df['drawdown'].min()
        
        # Calculate returns over different time periods
        total_return = df['cum_return'].iloc[-1] - 1 if not df['cum_return'].empty else 0
        
        # Calculate Sharpe ratio (assuming 0% risk-free rate for simplicity)
        sharpe_ratio = (df['daily_return'].mean() / df['daily_return'].std()) * np.sqrt(252) if df['daily_return'].std() != 0 else 0
        
        # Store individual stock metrics
        results[ticker] = {
            'total_return': total_return,
            'annual_volatility': annual_volatility,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'data': df
        }
    
    # Calculate correlation matrix if we have sufficient data
    correlation_matrix = None
    if correlation_data:
        try:
            # Create a dataframe with all close prices
            price_df = pd.DataFrame(correlation_data)
            correlation_matrix = price_df.corr()
            print(f"DEBUG: Price correlation matrix shape: {correlation_matrix.shape}")
        except Exception as e:
            print(f"DEBUG: Error calculating price correlation: {str(e)}")
    
    # Calculate returns correlation matrix
    returns_correlation = None
    if returns_data:
        try:
            returns_df = pd.DataFrame(returns_data)
            returns_correlation = returns_df.corr()
            print(f"DEBUG: Returns correlation matrix shape: {returns_correlation.shape}")
        except Exception as e:
            print(f"DEBUG: Error calculating returns correlation: {str(e)}")
    
    print("DEBUG: Comparative metrics calculation completed")
    # Return comparative metrics
    return {
        'individual_metrics': results,
        'price_correlation': correlation_matrix,
        'returns_correlation': returns_correlation,
        'normalized_prices': normalized_prices
    }

def plot_normalized_comparison(comparative_metrics):
    """
    Create a normalized price comparison chart.
    
    Args:
        comparative_metrics (dict): Results from calculate_comparative_metrics
    
    Returns:
        plotly.graph_objects.Figure: Normalized comparison chart
    """
    print("DEBUG: Creating normalized comparison chart")
    normalized_df = comparative_metrics['normalized_prices']
    
    if normalized_df is None or normalized_df.empty:
        print("DEBUG: No normalized price data available")
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for each stock
    for column in normalized_df.columns:
        if column != 'date':
            fig.add_trace(
                go.Scatter(
                    x=normalized_df['date'],
                    y=normalized_df[column],
                    mode='lines',
                    name=column
                )
            )
    
    # Add a reference line at 100 (starting value)
    fig.add_shape(
        type="line",
        x0=normalized_df['date'].min(),
        y0=100,
        x1=normalized_df['date'].max(),
        y1=100,
        line=dict(color="gray", width=1, dash="dash")
    )
    
    # Update layout
    fig.update_layout(
        title="Comparative Performance (Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Price",
        height=500,
        hovermode="x unified"
    )
    
    print("DEBUG: Normalized comparison chart created")
    return fig

def plot_correlation_heatmap(correlation_matrix, title="Correlation Matrix"):
    """
    Create a correlation heatmap.
    
    Args:
        correlation_matrix (pd.DataFrame): Correlation matrix
        title (str): Chart title
    
    Returns:
        plotly.graph_objects.Figure: Correlation heatmap
    """
    print(f"DEBUG: Creating correlation heatmap with title: {title}")
    if correlation_matrix is None or correlation_matrix.empty:
        print("DEBUG: No correlation data available")
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add heatmap
    fig.add_trace(
        go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            colorscale='RdBu_r',  # Red-Blue scale, reversed (blue for positive)
            zmid=0,  # Center the color scale at 0
            text=np.around(correlation_matrix.values, decimals=2),
            texttemplate="%{text:.2f}",
            colorbar=dict(title="Correlation")
        )
    )
    
    # Update layout
    fig.update_layout(
        title=title,
        height=500,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    print("DEBUG: Correlation heatmap created")
    return fig

def plot_comparative_metrics(comparative_metrics):
    """
    Create a comparative metrics visualization.
    
    Args:
        comparative_metrics (dict): Results from calculate_comparative_metrics
    
    Returns:
        plotly.graph_objects.Figure: Comparative metrics chart
    """
    print("DEBUG: Creating comparative metrics charts")
    individual_metrics = comparative_metrics['individual_metrics']
    
    if not individual_metrics:
        print("DEBUG: No individual metrics available")
        return None, None
    
    # Extract metrics for each stock
    tickers = list(individual_metrics.keys())
    print(f"DEBUG: Creating comparative charts for tickers: {tickers}")
    
    # Returns chart
    returns_fig = go.Figure()
    
    # Total returns
    returns = [individual_metrics[ticker]['total_return'] * 100 for ticker in tickers]
    returns_fig.add_trace(
        go.Bar(
            x=tickers,
            y=returns,
            name="Total Return (%)",
            marker_color='blue'
        )
    )
    
    returns_fig.update_layout(
        title="Total Return Comparison",
        xaxis_title="Stock",
        yaxis_title="Return (%)",
        height=400,
        yaxis=dict(tickformat=".2f")
    )
    
    # Risk metrics chart
    risk_fig = go.Figure()
    
    # Extract metrics
    volatilities = [individual_metrics[ticker]['annual_volatility'] * 100 for ticker in tickers]
    drawdowns = [individual_metrics[ticker]['max_drawdown'] * 100 for ticker in tickers]
    sharpe_ratios = [individual_metrics[ticker]['sharpe_ratio'] for ticker in tickers]
    
    # Create subplots for risk metrics
    risk_fig = make_subplots(
        rows=1, 
        cols=3,
        subplot_titles=("Annual Volatility (%)", "Maximum Drawdown (%)", "Sharpe Ratio")
    )
    
    # Add volatility bars
    risk_fig.add_trace(
        go.Bar(
            x=tickers,
            y=volatilities,
            marker_color='orange'
        ),
        row=1, col=1
    )
    
    # Add drawdown bars (negative values)
    risk_fig.add_trace(
        go.Bar(
            x=tickers,
            y=drawdowns,
            marker_color='red'
        ),
        row=1, col=2
    )
    
    # Add sharpe ratio bars
    risk_fig.add_trace(
        go.Bar(
            x=tickers,
            y=sharpe_ratios,
            marker_color='green'
        ),
        row=1, col=3
    )
    
    # Update layout
    risk_fig.update_layout(
        height=400,
        showlegend=False
    )
    
    print("DEBUG: Comparative metrics charts created")
    return returns_fig, risk_fig

def get_cached_analysis(tickers, metrics_hash):
    """
    Try to get cached analysis result to avoid repeat API calls.
    
    Args:
        tickers (list): List of stock tickers
        metrics_hash (str): Hash of metrics for cache identification
    
    Returns:
        str or None: Cached analysis if available, None otherwise
    """
    # Create cache directory if it doesn't exist
    os.makedirs("cache/comparative", exist_ok=True)
    
    # Create cache key from tickers and metrics hash
    tickers_key = "-".join(sorted(tickers))
    cache_key = f"{tickers_key}_{metrics_hash}"
    cache_file = f"cache/comparative/{cache_key}.json"
    
    # Check if cache exists and is fresh (less than 24 hours old)
    if os.path.exists(cache_file):
        file_age_seconds = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if file_age_seconds < 86400:  # 24 hours
            print(f"DEBUG: Found fresh cache for {tickers_key}")
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    return cached_data.get('analysis')
            except Exception as e:
                print(f"DEBUG: Error reading cache: {str(e)}")
    
    print(f"DEBUG: No fresh cache found for {tickers_key}")
    return None

def save_analysis_to_cache(tickers, metrics_hash, analysis):
    """
    Save analysis result to cache.
    
    Args:
        tickers (list): List of stock tickers
        metrics_hash (str): Hash of metrics for cache identification
        analysis (str): Analysis result to cache
    """
    # Create cache directory if it doesn't exist
    os.makedirs("cache/comparative", exist_ok=True)
    
    # Create cache key from tickers and metrics hash
    tickers_key = "-".join(sorted(tickers))
    cache_key = f"{tickers_key}_{metrics_hash}"
    cache_file = f"cache/comparative/{cache_key}.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'tickers': tickers,
                'timestamp': datetime.now().timestamp(),
                'analysis': analysis
            }, f)
        print(f"DEBUG: Saved analysis to cache for {tickers_key}")
    except Exception as e:
        print(f"DEBUG: Error saving to cache: {str(e)}")

def generate_comparative_analysis(data_dict, comparative_metrics):
    """
    Generate an AI interpretation of comparative metrics using Gemini via OpenRouter.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with stock price data {ticker: dataframe}
        comparative_metrics (dict): Results from calculate_comparative_metrics
    
    Returns:
        str: AI-generated comparative analysis
    """
    print("DEBUG: Starting generate_comparative_analysis function")
    
    # Format the metrics to include in the prompt
    tickers = list(data_dict.keys())
    print(f"DEBUG: Analyzing comparison for tickers: {', '.join(tickers)}")
    
    try:
        metrics_summary = f"Stocks being compared: {', '.join(tickers)}\n\nPerformance Metrics:"
        
        # Extract performance metrics
        perf_metrics = {}
        for ticker, metrics in comparative_metrics['individual_metrics'].items():
            perf_metrics[ticker] = {
                'total_return': metrics['total_return'],
                'annual_volatility': metrics['annual_volatility'],
                'max_drawdown': metrics['max_drawdown'],
                'sharpe_ratio': metrics['sharpe_ratio']
            }
            metrics_summary += f"\n\n{ticker}:"
            metrics_summary += f"\n- Total Return: {metrics['total_return'] * 100:.2f}%"
            metrics_summary += f"\n- Annual Volatility: {metrics['annual_volatility'] * 100:.2f}%"
            metrics_summary += f"\n- Maximum Drawdown: {metrics['max_drawdown'] * 100:.2f}%"
            metrics_summary += f"\n- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}"
        
        # Create a hash of the metrics for cache identification
        metrics_hash = hashlib.md5(json.dumps(perf_metrics, sort_keys=True).encode()).hexdigest()[:10]
        
        # Try to get cached analysis first
        cached_analysis = get_cached_analysis(tickers, metrics_hash)
        if cached_analysis:
            print("DEBUG: Using cached analysis result")
            return cached_analysis
        
        print("DEBUG: Metrics summary prepared successfully")
        
        # Add correlation information if available
        if comparative_metrics['returns_correlation'] is not None:
            print("DEBUG: Adding correlation matrix to prompt")
            try:
                metrics_summary += "\n\nReturns Correlation Matrix:\n"
                # Format as string with fixed precision to avoid any potential issues
                corr_matrix = comparative_metrics['returns_correlation'].round(2)
                corr_str = str(corr_matrix)
                metrics_summary += corr_str
                print("DEBUG: Correlation matrix added successfully")
            except Exception as e:
                print(f"DEBUG: Error adding correlation matrix: {str(e)}")
                # Continue without the correlation matrix
        
        # Build the prompt for Gemini
        prompt = f"""You are an expert financial analyst specializing in comparative stock analysis. Based on the metrics provided below, provide a thorough comparative analysis of these stocks.

        {metrics_summary}

        Please structure your analysis as follows:
        1. Performance Overview - Compare the return performance of these stocks
        2. Risk Comparison - Analyze the risk profiles based on volatility and drawdowns
        3. Risk-Adjusted Performance - Evaluate and compare the Sharpe ratios
        4. Correlation Insights - If correlation data is available, discuss diversification implications
        5. Relative Strength Analysis - Identify which stocks have shown stronger relative performance and why
        6. Recommendations - Suggest which stock(s) might be most attractive based on this analysis and why

        Keep your analysis professional, data-driven, and provide specific insights that would help an investor choose between these stocks.
        """
        
        print(f"DEBUG: Prompt prepared, length: {len(prompt)} characters")
        
        # Call the OpenRouter API to get Gemini analysis
        OPENROUTER_KEY = "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"  # Default key
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
        
        print(f"DEBUG: Preparing to call OpenRouter API with model: {GEMINI_MODEL}")
        
        try:
            print(f"DEBUG: Sending POST request to {url}")
            response = requests.post(url, headers=headers, json=payload)
            print(f"DEBUG: Received response with status code: {response.status_code}")
            
            # Print response details for debugging
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            content_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
            print(f"DEBUG: Response content preview: {content_preview}")
            
            response.raise_for_status()  # Raise for status codes >= 400
            print("DEBUG: Response status code is good")
            
            try:
                result = response.json()
                print(f"DEBUG: Successfully parsed JSON response")
                
                # Print token usage if available
                usage = result.get('usage', {})
                if usage:
                    print(f"DEBUG: Token usage - Prompt: {usage.get('prompt_tokens', 'N/A')}, Completion: {usage.get('completion_tokens', 'N/A')}, Total: {usage.get('total_tokens', 'N/A')}")
                
                # Extract the response content
                if 'choices' in result and len(result['choices']) > 0:
                    analysis = result['choices'][0]['message']['content']
                    print(f"DEBUG: Successfully extracted analysis content, length: {len(analysis)}")
                    
                    # Save to cache for future use
                    save_analysis_to_cache(tickers, metrics_hash, analysis)
                    
                    return analysis
                else:
                    print(f"DEBUG: Unexpected response structure: {result}")
                    return "Error: Received unexpected response structure from API"
                
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error: {e}")
                print(f"DEBUG: Raw response: {response.text}")
                return f"Error parsing API response: {str(e)}"
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request error: {str(e)}")
            return f"Error calling AI service: {str(e)}"
            
    except Exception as e:
        print(f"DEBUG: Exception in generate_comparative_analysis: {str(e)}")
        print(traceback.format_exc())
        
        # Generate fallback analysis without complex f-string expressions
        fallback_message = "# Comparative Analysis\n\n"
        fallback_message += f"I couldn't generate a complete analysis at this time due to an error: {str(e)}\n\n"
        fallback_message += "Based on the metrics shown above, here's a brief comparison:\n\n"
        fallback_message += f"- The stocks being compared are: {', '.join(tickers)}\n"
        
        # Calculate best performing stock for total return
        best_return_ticker = None
        best_return_value = float('-inf')
        for ticker, metrics in comparative_metrics['individual_metrics'].items():
            if metrics['total_return'] > best_return_value:
                best_return_value = metrics['total_return']
                best_return_ticker = ticker
        
        if best_return_ticker:
            fallback_message += f"- For total returns, the highest performer is {best_return_ticker}\n"
        
        # Calculate least volatile stock
        least_volatile_ticker = None
        lowest_volatility = float('inf')
        for ticker, metrics in comparative_metrics['individual_metrics'].items():
            if metrics['annual_volatility'] < lowest_volatility:
                lowest_volatility = metrics['annual_volatility']
                least_volatile_ticker = ticker
        
        if least_volatile_ticker:
            fallback_message += f"- From a risk perspective, the least volatile stock is {least_volatile_ticker}\n"
        
        # Calculate stock with best Sharpe ratio
        best_sharpe_ticker = None
        best_sharpe_value = float('-inf')
        for ticker, metrics in comparative_metrics['individual_metrics'].items():
            if metrics['sharpe_ratio'] > best_sharpe_value:
                best_sharpe_value = metrics['sharpe_ratio']
                best_sharpe_ticker = ticker
        
        if best_sharpe_ticker:
            fallback_message += f"- For risk-adjusted returns, the stock with the highest Sharpe ratio is {best_sharpe_ticker}\n"
        
        fallback_message += "\nFor a more detailed analysis, please try again later."
        return fallback_message

def render_comparative_analysis_ui(comparative_data):
    """
    Render the comparative analysis UI in Streamlit.
    
    Args:
        comparative_data (dict): Dictionary of DataFrames with stock price data {ticker: dataframe}
    """
    print(f"DEBUG: Rendering comparative analysis UI with {len(comparative_data)} stocks")
    st.subheader("Comparative Analysis Dashboard")
    
    # Verify we have at least two stocks to compare
    if len(comparative_data) < 2:
        st.warning("Need at least two stocks to perform comparative analysis. Please select more stocks to compare.")
        print("DEBUG: Not enough stocks for comparison (need at least 2)")
        return
    
    # Calculate comparative metrics
    with st.spinner("Calculating comparative metrics..."):
        print("DEBUG: Starting comparative metrics calculation")
        comparative_metrics = calculate_comparative_metrics(comparative_data)
        print("DEBUG: Comparative metrics calculation completed")
    
    # Create a tab layout for different comparative analysis components
    comp_tabs = st.tabs([
        "Performance Comparison", 
        "Correlation Analysis", 
        "Risk Metrics",
        "AI Insights"
    ])
    
    # Performance Comparison Tab
    with comp_tabs[0]:
        print("DEBUG: Rendering Performance Comparison tab")
        # Normalized price comparison
        norm_fig = plot_normalized_comparison(comparative_metrics)
        if norm_fig:
            st.plotly_chart(norm_fig, use_container_width=True)
        else:
            st.warning("Insufficient data for normalized price comparison.")
        
        # Performance metrics table
        st.subheader("Performance Metrics")
        
        # Extract performance metrics
        performance_data = []
        for ticker, metrics in comparative_metrics['individual_metrics'].items():
            performance_data.append({
                "Stock": ticker,
                "Total Return": f"{metrics['total_return'] * 100:.2f}%",
                "Annual Volatility": f"{metrics['annual_volatility'] * 100:.2f}%",
                "Maximum Drawdown": f"{metrics['max_drawdown'] * 100:.2f}%",
                "Sharpe Ratio": f"{metrics['sharpe_ratio']:.2f}"
            })
        
        if performance_data:
            perf_df = pd.DataFrame(performance_data)
            st.dataframe(perf_df, hide_index=True)
        else:
            st.warning("No performance data available.")
        
        # Returns comparison chart
        returns_fig, _ = plot_comparative_metrics(comparative_metrics)
        if returns_fig:
            st.plotly_chart(returns_fig, use_container_width=True)
    
    # Correlation Analysis Tab
    with comp_tabs[1]:
        print("DEBUG: Rendering Correlation Analysis tab")
        # Price correlation heatmap
        st.subheader("Price Correlation")
        st.markdown("""
        Price correlation measures how closely the absolute prices of different stocks move together.
        - A correlation of 1.0 means perfect positive correlation (prices move exactly together)
        - A correlation of -1.0 means perfect negative correlation (prices move exactly opposite)
        - A correlation near 0 means little to no linear relationship
        """)
        
        price_corr_fig = plot_correlation_heatmap(
            comparative_metrics['price_correlation'],
            title="Price Correlation Matrix"
        )
        if price_corr_fig:
            st.plotly_chart(price_corr_fig, use_container_width=True)
        else:
            st.warning("Insufficient data for price correlation analysis.")
        
        # Returns correlation heatmap
        st.subheader("Returns Correlation")
        st.markdown("""
        Returns correlation measures how closely the daily percentage changes of different stocks move together.
        This is often more useful than price correlation for portfolio diversification analysis.
        """)
        
        returns_corr_fig = plot_correlation_heatmap(
            comparative_metrics['returns_correlation'],
            title="Daily Returns Correlation Matrix"
        )
        if returns_corr_fig:
            st.plotly_chart(returns_corr_fig, use_container_width=True)
        else:
            st.warning("Insufficient data for returns correlation analysis.")
    
    # Risk Metrics Tab
    with comp_tabs[2]:
        print("DEBUG: Rendering Risk Metrics tab")
        st.subheader("Risk Metrics Comparison")
        
        # Risk metrics charts
        _, risk_fig = plot_comparative_metrics(comparative_metrics)
        if risk_fig:
            st.plotly_chart(risk_fig, use_container_width=True)
        else:
            st.warning("Insufficient data for risk metrics comparison.")
        
        # Risk metrics explanation
        with st.expander("Risk Metrics Explanation", expanded=True):
            st.markdown("""
            ### Understanding Risk Metrics
            
            - **Annual Volatility**: A measure of price fluctuation. Higher volatility means more dramatic price swings.
            - **Maximum Drawdown**: The largest peak-to-trough decline in value. Measures downside risk and recovery difficulty.
            - **Sharpe Ratio**: Risk-adjusted return metric. Higher is better, indicating more return per unit of risk.
            
            When comparing stocks, look for:
            - Lower volatility for more stable investments
            - Smaller maximum drawdowns for less severe declines
            - Higher Sharpe ratios for better risk-adjusted performance
            """)
    
    # AI Insights Tab
    with comp_tabs[3]:
        print("DEBUG: Rendering AI Insights tab")
        st.subheader("AI Comparative Analysis")
        
        # Define keys for this specific tab to avoid conflicts
        analysis_key = "comp_analysis_result"
        
        # Initialize session state for this specific analysis if not already present
        if analysis_key not in st.session_state:
            st.session_state[analysis_key] = None
        
        # Create a button container to keep the button in the same place
        button_container = st.container()
        
        # If we don't have a result yet, show the generate button
        if st.session_state[analysis_key] is None:
            with button_container:
                if st.button("Generate AI Comparative Analysis", key="generate_ai_analysis"):
                    # Show a spinner while generating
                    with st.spinner("Generating comparative analysis..."):
                        try:
                            # Create metrics hash for caching
                            tickers = list(comparative_data.keys())
                            perf_metrics = {}
                            
                            for ticker, metrics in comparative_metrics['individual_metrics'].items():
                                perf_metrics[ticker] = {
                                    'total_return': metrics['total_return'],
                                    'annual_volatility': metrics['annual_volatility'],
                                    'max_drawdown': metrics['max_drawdown'],
                                    'sharpe_ratio': metrics['sharpe_ratio']
                                }
                            
                            # Create hash for cache key
                            metrics_hash = hashlib.md5(json.dumps(perf_metrics, sort_keys=True).encode()).hexdigest()[:10]
                            
                            # Try to get from cache first
                            cached_result = get_cached_analysis(tickers, metrics_hash)
                            if cached_result:
                                print("DEBUG: Using cached analysis result")
                                st.session_state[analysis_key] = cached_result
                            else:
                                print("DEBUG: No cache found, generating new analysis")
                                st.session_state[analysis_key] = generate_comparative_analysis(
                                    comparative_data, comparative_metrics
                                )
                                
                        except Exception as e:
                            error_msg = f"Error generating AI analysis: {str(e)}"
                            print(f"DEBUG: {error_msg}")
                            print(traceback.format_exc())
                            st.error(error_msg)
                            st.session_state[analysis_key] = f"### Analysis Error\n\n{error_msg}"
                    
                    # Force a rerun to display the result
                    st.experimental_rerun()
                else:
                    st.info("Click 'Generate AI Comparative Analysis' for an AI-powered interpretation of these comparative metrics.")
        else:
            # Display the saved result
            st.markdown(st.session_state[analysis_key])
            
            # Add a reset button to allow regenerating the analysis
            with button_container:
                if st.button("Generate New Analysis", key="reset_analysis"):
                    st.session_state[analysis_key] = None
                    st.experimental_rerun()