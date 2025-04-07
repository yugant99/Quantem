import pandas as pd
import numpy as np
import json
import os
import streamlit as st
from prophet import Prophet
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Check multiple possible locations for the parameter database
possible_paths = [
    "prophet_parameter_db.json",  # Current directory
    "/Users/yuganthareshsoni/stock_analyzer/prophet_parameter_db.json",  # Absolute path
    os.path.join(os.path.dirname(__file__), "../prophet_parameter_db.json"),  # One level up
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "prophet_parameter_db.json")  # Same dir as script
]

# Find the first path that exists
PARAM_DB_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        PARAM_DB_PATH = path
        print(f"Found parameter database at: {PARAM_DB_PATH}")
        break

if PARAM_DB_PATH is None:
    print("WARNING: Could not find prophet_parameter_db.json in any expected location!")
    PARAM_DB_PATH = "prophet_parameter_db.json"  # Default fallback

def load_parameter_db():
    """
    Load the Prophet parameter database from JSON file.
    
    Returns:
        dict: The parameter database
    """
    try:
        if os.path.exists(PARAM_DB_PATH):
            with open(PARAM_DB_PATH, 'r') as f:
                param_db = json.load(f)
                print(f"Successfully loaded parameter database with {len(param_db)} period entries")
                return param_db
        else:
            st.warning(f"Parameter database file not found: {PARAM_DB_PATH}")
            print(f"WARNING: Parameter database file not found: {PARAM_DB_PATH}")
            return {}
    except Exception as e:
        st.error(f"Error loading parameter database: {str(e)}")
        print(f"ERROR loading parameter database: {str(e)}")
        return {}

def get_best_parameters(period, forecast_days, ticker=None):
    """
    Get the best parameters for Prophet model based on period and forecast horizon.
    
    Args:
        period (str): Time period (e.g., '1mo', '3mo', '1y')
        forecast_days (int): Forecast horizon in days
        ticker (str, optional): Specific ticker symbol to find optimized parameters
        
    Returns:
        tuple: (parameters dict, list of features to use)
    """
    param_db = load_parameter_db()
    
    # Find the closest forecast days in the database
    available_forecast_days = []
    
    if period in param_db:
        available_forecast_days = [int(days) for days in param_db[period].keys() 
                                  if days.isdigit()]
    
    # Default parameters if nothing specific is found
    default_params = {
        "changepoint_prior_scale": 0.05,
        "seasonality_prior_scale": 10.0,
        "seasonality_mode": "multiplicative",
        "changepoint_range": 0.8
    }
    
    default_features = ["close"]
    
    # If no forecast days are available, return defaults
    if not available_forecast_days:
        print(f"No parameters found for period {period}. Using defaults.")
        return default_params, default_features
    
    # Find the closest forecast days
    closest_days = min(available_forecast_days, key=lambda x: abs(x - forecast_days))
    print(f"Using parameters for {closest_days} days (requested: {forecast_days} days)")
    
    # Get parameters for the closest forecast days
    closest_days_str = str(closest_days)
    
    # Try to find period-specific parameters
    if period in param_db and closest_days_str in param_db[period]:
        period_params = param_db[period][closest_days_str]
        
        # If ticker is provided, try to find ticker-specific parameters
        if ticker and 'stock_results' in period_params:
            ticker = ticker.upper()  # Ensure consistent uppercase format
            for stock_result in period_params['stock_results']:
                if stock_result['ticker'].upper() == ticker:
                    print(f"Found ticker-specific parameters for {ticker}")
                    return stock_result['params'], stock_result['features']
            
            print(f"No ticker-specific parameters found for {ticker}. Using period parameters.")
        
        # If no ticker-specific parameters, return period-specific ones
        return period_params['parameters'], period_params['features']
    
    # If no period-specific parameters, return defaults
    print(f"No parameters found for period {period} and forecast days {forecast_days}. Using defaults.")
    return default_params, default_features

def prepare_prophet_data(df, features):
    """
    Prepare data for Prophet model with proper feature calculation using indicators module.
    """
    # Copy the dataframe to avoid modifying the original
    prophet_df = df.copy()
    
    # Prophet requires columns named 'ds' and 'y'
    prophet_df['ds'] = prophet_df['date']
    prophet_df['y'] = prophet_df['close']
    
    # Import the indicators module
    from utils.indicators import calculate_indicators
    
    # Determine which indicators to calculate
    basic_indicators = [f for f in features if f != 'close' and not (
        f.startswith('close_') or '_ratio' in f)]
    
    # Get the set of indicators that need to be calculated
    missing_indicators = [ind for ind in basic_indicators if ind not in prophet_df.columns]
    
    if missing_indicators:
        print(f"Calculating missing indicators: {missing_indicators}")
        # Use the existing calculate_indicators function to add all needed indicators
        prophet_df = calculate_indicators(prophet_df, missing_indicators)
    
    # Handle any derived features that might not be directly from calculate_indicators
    if 'close_sma50_ratio' in features and 'close_sma50_ratio' not in prophet_df.columns:
        if 'sma_50' in prophet_df.columns:
            prophet_df['close_sma50_ratio'] = prophet_df['close'] / prophet_df['sma_50']
            print("Created derived feature: close_sma50_ratio")
    
    if 'close_sma20_ratio' in features and 'close_sma20_ratio' not in prophet_df.columns:
        if 'sma_20' in prophet_df.columns:
            prophet_df['close_sma20_ratio'] = prophet_df['close'] / prophet_df['sma_20']
            print("Created derived feature: close_sma20_ratio")
    
    # Check for any still-missing features
    still_missing = [f for f in features if f != 'close' and f not in prophet_df.columns]
    if still_missing:
        print(f"WARNING: Could not calculate these features: {still_missing}")
    
    # Check for and handle NaN values in all feature columns
    for column in prophet_df.columns:
        if column not in ['ds', 'y', 'date']:
            nan_count = prophet_df[column].isna().sum()
            if nan_count > 0:
                print(f"Found {nan_count} NaN values in column '{column}' - filling with forward/backward fill")
                # Fill NaN values using forward fill and then backward fill
                prophet_df[column] = prophet_df[column].fillna(method='ffill')
                prophet_df[column] = prophet_df[column].fillna(method='bfill')
                
                # If still NaN (possible if all values are NaN), fill with zeros
                if prophet_df[column].isna().sum() > 0:
                    print(f"Still have NaN values in '{column}' after ffill/bfill - filling with zeros")
                    prophet_df[column] = prophet_df[column].fillna(0)
    
    # Select only necessary columns that exist
    available_features = [f for f in features if f == 'close' or f in prophet_df.columns]
    cols_to_use = ['ds', 'y'] + [f for f in available_features if f != 'close' and f in prophet_df.columns]
    
    prophet_df = prophet_df[cols_to_use]
    print(f"Prepared data with features: {list(prophet_df.columns)}")
    
    return prophet_df

def build_prophet_model(df, features, params, forecast_days, include_history=True):
    """
    Build and fit a Prophet model with robust error handling.
    
    Args:
        df (pd.DataFrame): Prepared DataFrame for Prophet
        features (list): List of feature columns to include as regressors
        params (dict): Prophet parameters
        forecast_days (int): Number of days to forecast
        include_history (bool): Whether to include historical data in predictions
        
    Returns:
        tuple: (Prophet model, DataFrame with predictions)
    """
    # Create Prophet model with parameters
    model = Prophet(
        changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
        seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0),
        seasonality_mode=params.get('seasonality_mode', 'multiplicative'),
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_range=params.get('changepoint_range', 0.8)
    )
    
    # Add regressors for features that actually exist in the dataframe
    actual_features = [col for col in df.columns if col not in ['ds', 'y']]
    for feature in actual_features:
        model.add_regressor(feature)
    
    print(f"Fitting Prophet model with {len(actual_features)} features: {actual_features}")
    
    # Fit the model
    with st.spinner("Training Prophet model... This may take a minute."):
        model.fit(df)
    
    # Create future dataframe for predictions
    future = model.make_future_dataframe(periods=forecast_days)
    
    # Add regressor values for historical dates
    for feature in actual_features:
        future[feature] = None
        # Add historical values
        for i, row in df.iterrows():
            date_idx = future[future['ds'] == row['ds']].index
            if not date_idx.empty:
                future.loc[date_idx, feature] = row[feature]
    
    # Fill future regressor values with last known values
    # This is a simple approach - more sophisticated methods could be used
    for feature in actual_features:
        last_known_values = df[feature].iloc[-1]
        # Fill NaN values with last known values
        future[feature].fillna(last_known_values, inplace=True)
    
    # Make predictions
    forecast = model.predict(future)
    
    if not include_history:
        # Filter out historical dates
        last_date = df['ds'].max()
        forecast = forecast[forecast['ds'] > last_date]
    
    return model, forecast

def evaluate_forecast(df, forecast):
    """
    Evaluate forecast accuracy using RMSE and MAPE.
    
    Args:
        df (pd.DataFrame): DataFrame with actual values
        forecast (pd.DataFrame): DataFrame with predictions
        
    Returns:
        dict: Evaluation metrics
    """
    try:
        # Merge actual and predicted values
        eval_df = pd.merge(
            df[['ds', 'y']], 
            forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], 
            on='ds', 
            how='inner'
        )
        
        # Calculate errors
        eval_df['error'] = eval_df['y'] - eval_df['yhat']
        eval_df['abs_error'] = abs(eval_df['error'])
        eval_df['pct_error'] = abs(eval_df['error'] / eval_df['y'])
        
        # Calculate metrics
        rmse = np.sqrt(np.mean(eval_df['error'] ** 2))
        mape = np.mean(eval_df['pct_error']) * 100
        
        # Calculate percentage of actual values within prediction interval
        eval_df['within_interval'] = (
            (eval_df['y'] >= eval_df['yhat_lower']) & 
            (eval_df['y'] <= eval_df['yhat_upper'])
        )
        interval_accuracy = eval_df['within_interval'].mean() * 100
        
        return {
            'rmse': rmse,
            'mape': mape,
            'interval_accuracy': interval_accuracy
        }
    except Exception as e:
        print(f"Error evaluating forecast: {str(e)}")
        return {
            'rmse': 0.0,
            'mape': 0.0,
            'interval_accuracy': 0.0
        }

def plot_prophet_forecast(df, forecast, ticker):
    """
    Create Plotly figure with Prophet forecast.
    
    Args:
        df (pd.DataFrame): Original stock data
        forecast (pd.DataFrame): Prophet forecast results
        ticker (str): Stock ticker symbol
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    # Create figure
    fig = go.Figure()
    
    # Add historical prices
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['close'],
            mode='lines',
            name='Historical Price',
            line=dict(color='royalblue', width=2)
        )
    )
    
    # Add forecast
    # Filter out historical dates
    last_date = df['date'].max()
    future_forecast = forecast[forecast['ds'] > last_date]
    
    if not future_forecast.empty:
        fig.add_trace(
            go.Scatter(
                x=future_forecast['ds'],
                y=future_forecast['yhat'],
                mode='lines',
                name='Forecast',
                line=dict(color='green', width=2)
            )
        )
        
        # Add prediction intervals
        fig.add_trace(
            go.Scatter(
                x=future_forecast['ds'].tolist() + future_forecast['ds'].tolist()[::-1],
                y=future_forecast['yhat_upper'].tolist() + future_forecast['yhat_lower'].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(0, 176, 0, 0.2)',
                line=dict(color='rgba(255, 255, 255, 0)'),
                name='95% Confidence Interval'
            )
        )
    
    # Update layout
    fig.update_layout(
        title=f"{ticker} Stock Price Forecast",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def plot_prophet_components(model, forecast, ticker):
    """
    Create Plotly figure with Prophet forecast components.
    
    Args:
        model (Prophet): Fitted Prophet model
        forecast (pd.DataFrame): Prophet forecast results
        ticker (str): Stock ticker symbol
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure with components
    """
    try:
        # Create figure with subplots
        fig = make_subplots(
            rows=3, 
            cols=1,
            subplot_titles=("Trend", "Yearly Seasonality", "Weekly Seasonality"),
            vertical_spacing=0.1,
            shared_xaxes=False
        )
        
        # Add trend component
        fig.add_trace(
            go.Scatter(
                x=forecast['ds'],
                y=forecast['trend'],
                mode='lines',
                name='Trend',
                line=dict(color='royalblue', width=2)
            ),
            row=1, col=1
        )
        
        # Add yearly seasonality if available
        if 'yearly' in model.seasonalities:
            # Get yearly seasonality component
            if 'yearly' in forecast.columns:
                fig.add_trace(
                    go.Scatter(
                        x=forecast['ds'],
                        y=forecast['yearly'],
                        mode='lines',
                        name='Yearly Seasonality',
                        line=dict(color='green', width=2)
                    ),
                    row=2, col=1
                )
            else:
                fig.add_annotation(
                    text="Yearly seasonality component not available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    row=2, col=1
                )
        
        # Add weekly seasonality if available
        if 'weekly' in model.seasonalities:
            # Get weekly seasonality component
            if 'weekly' in forecast.columns:
                fig.add_trace(
                    go.Scatter(
                        x=forecast['ds'],
                        y=forecast['weekly'],
                        mode='lines',
                        name='Weekly Seasonality',
                        line=dict(color='orange', width=2)
                    ),
                    row=3, col=1
                )
            else:
                fig.add_annotation(
                    text="Weekly seasonality component not available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    row=3, col=1
                )
        
        # Update layout
        fig.update_layout(
            title=f"{ticker} Forecast Components",
            height=800,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
    except Exception as e:
        print(f"Error plotting components: {str(e)}")
        # Return a simple error figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"Could not generate components plot: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title=f"{ticker} Forecast Components - Error",
            height=400
        )
        return fig

def interpret_forecast(forecast, ticker, forecast_days):
    """
    Generate a text interpretation of the forecast.
    
    Args:
        forecast (pd.DataFrame): Prophet forecast results
        ticker (str): Stock ticker symbol
        forecast_days (int): Number of days in the forecast
        
    Returns:
        str: Interpretation text
    """
    try:
        # Get the latest historical date and the forecast dates
        historical_dates = forecast[forecast['ds'] <= datetime.now()]
        future_forecast = forecast[forecast['ds'] > datetime.now()]
        
        if future_forecast.empty:
            return "No future forecast data available."
        
        # Get current price and forecast for various horizons
        current_price = historical_dates.iloc[-1]['yhat'] if not historical_dates.empty else future_forecast.iloc[0]['yhat']
        
        # Short-term forecast (7 days or less)
        short_term_idx = min(7, len(future_forecast)-1)
        short_term_price = future_forecast.iloc[short_term_idx]['yhat']
        short_term_change = (short_term_price / current_price - 1) * 100
        
        # Mid-term forecast (30 days or forecast_days/2, whichever is less)
        mid_term_idx = min(30, len(future_forecast)//2, len(future_forecast)-1)
        mid_term_price = future_forecast.iloc[mid_term_idx]['yhat']
        mid_term_change = (mid_term_price / current_price - 1) * 100
        
        # End of forecast
        end_price = future_forecast.iloc[-1]['yhat']
        end_change = (end_price / current_price - 1) * 100
        
        # Check if there's a clear trend
        is_uptrend = end_price > current_price
        
        # Calculate volatility (standard deviation of percentage changes)
        daily_changes = future_forecast['yhat'].pct_change().dropna()
        volatility = daily_changes.std() * 100
        
        # Generate interpretation
        interpretation = f"""
## {ticker} Forecast Interpretation

Based on the Prophet model forecast for the next {forecast_days} days:

### Price Projections
- Current projected price: ${current_price:.2f}
- Short-term (7 days) projection: ${short_term_price:.2f} ({short_term_change:+.2f}%)
- Mid-term ({mid_term_idx} days) projection: ${mid_term_price:.2f} ({mid_term_change:+.2f}%)
- End of forecast period ({forecast_days} days) projection: ${end_price:.2f} ({end_change:+.2f}%)

### Trend Analysis
The model forecasts a general {'upward' if is_uptrend else 'downward'} trend over the forecast period.
Projected volatility: {volatility:.2f}% (daily standard deviation)

### Confidence Intervals
- The lower bound estimate for {forecast_days} days is ${future_forecast.iloc[-1]['yhat_lower']:.2f}
- The upper bound estimate for {forecast_days} days is ${future_forecast.iloc[-1]['yhat_upper']:.2f}

This represents a potential range of {((future_forecast.iloc[-1]['yhat_upper'] / future_forecast.iloc[-1]['yhat_lower']) - 1) * 100:.2f}% between the lower and upper bounds.

### Key Considerations
- This forecast is based on historical patterns and technical indicators
- External factors like earnings reports, market news, and broader economic events are not fully captured
- For investment decisions, consider combining this technical forecast with fundamental analysis and current market news
        """
        
        return interpretation
    except Exception as e:
        print(f"Error interpreting forecast: {str(e)}")
        return f"""
## {ticker} Forecast Interpretation

Could not generate a detailed interpretation due to an error: {str(e)}

The Prophet model has generated a forecast, but please review the chart and metrics directly.

### Key Considerations
- This forecast is based on historical patterns and technical indicators
- External factors like earnings reports, market news, and broader economic events are not captured
- For investment decisions, consider combining this technical forecast with fundamental analysis and current market news
        """

def render_forecast_ui(df, ticker, period):
    """
    Render the Prophet forecast UI in Streamlit with improved error handling and feedback.
    
    Args:
        df (pd.DataFrame): DataFrame with stock data
        ticker (str): Stock ticker symbol
        period (str): Time period (e.g., '1mo', '3mo', '1y')
    """
    st.subheader("Prophet Stock Price Forecasting")
    
    # Create a container for status messages
    status_container = st.container()
    
    # Data information
    st.info(f"Data loaded for {ticker}: {len(df)} data points from {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        forecast_days = st.slider(
            "Forecast Horizon (Days)", 
            min_value=7, 
            max_value=90, 
            value=30, 
            step=7,
            help="Number of days to forecast into the future"
        )
    
    with col2:
        show_components = st.checkbox(
            "Show Forecast Components", 
            value=False,
            help="Display trend and seasonality components of the forecast"
        )
    
    # Generate forecast button
    if st.button("Generate Forecast", key="generate_forecast_btn"):
        # Create a placeholder for status messages
        status_placeholder = status_container.empty()
        status_placeholder.info("Starting forecast generation...")
        
        # Check if we have enough data
        if len(df) < 30:
            status_placeholder.warning("Not enough historical data for reliable forecasting. At least 30 data points are recommended.")
            return
        
        try:
            # Print debugging info
            print(f"Data shape: {df.shape}")
            print(f"Columns available: {df.columns.tolist()}")
            
            # Step 1: Load parameters
            status_placeholder.info(f"Step 1/4: Loading optimized parameters for {ticker}...")
            params, features = get_best_parameters(period, forecast_days, ticker)
            print(f"Using parameters: {params}")
            print(f"Using features: {features}")
            
            # Step 2: Prepare data
            status_placeholder.info(f"Step 2/4: Preparing data with {len(features)} features...")
            prophet_df = prepare_prophet_data(df, features)
            
            # Step 3: Train model
            status_placeholder.info(f"Step 3/4: Training Prophet model (this may take a minute)...")
            with st.spinner("Model training in progress..."):
                model, forecast = build_prophet_model(prophet_df, features, params, forecast_days)
            
            # Step 4: Generate visualizations
            status_placeholder.info(f"Step 4/4: Generating visualizations...")
            metrics = evaluate_forecast(prophet_df, forecast)
            forecast_fig = plot_prophet_forecast(df, forecast, ticker)
            components_fig = plot_prophet_components(model, forecast, ticker)
            
            # Clear status and display success
            status_placeholder.success(f"Forecast successfully generated for {ticker}!")
            
            # Display metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                st.metric(
                    label="RMSE", 
                    value=f"${metrics['rmse']:.2f}"
                )
            
            with metric_col2:
                st.metric(
                    label="MAPE", 
                    value=f"{metrics['mape']:.2f}%"
                )
            
            with metric_col3:
                st.metric(
                    label="Interval Accuracy", 
                    value=f"{metrics['interval_accuracy']:.2f}%"
                )
            
            # Display forecast chart
            st.plotly_chart(forecast_fig, use_container_width=True)
            
            # Display interpretation
            with st.expander("Forecast Interpretation", expanded=True):
                interpretation = interpret_forecast(forecast, ticker, forecast_days)
                st.markdown(interpretation)
            
            # Display components if requested
            if show_components:
                st.subheader("Forecast Components")
                st.plotly_chart(components_fig, use_container_width=True)
            
            # Download forecast as CSV
            csv = forecast.to_csv(index=False)
            st.download_button(
                label="Download Forecast as CSV",
                data=csv,
                file_name=f"{ticker}_forecast_{forecast_days}d.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            import traceback
            print(f"ERROR in forecast generation: {str(e)}")
            print(traceback.format_exc())  # Print full stack trace to terminal
            status_placeholder.error(f"Error generating forecast: {str(e)}")
            st.exception(e)  # Show detailed error in UI