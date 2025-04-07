import numpy as np
import pandas as pd
import pandas_ta as ta

def get_available_indicators():
    """
    Return a list of available technical indicators organized by category.
    
    Returns:
        list: List of dictionaries containing indicator info
    """
    return [
        # Trend Indicators
        {"id": "sma_20", "name": "Simple Moving Average (20)", "category": "Trend"},
        {"id": "sma_50", "name": "Simple Moving Average (50)", "category": "Trend"},
        {"id": "sma_200", "name": "Simple Moving Average (200)", "category": "Trend"},
        {"id": "ema_12", "name": "Exponential Moving Average (12)", "category": "Trend"},
        {"id": "ema_26", "name": "Exponential Moving Average (26)", "category": "Trend"},
        {"id": "adx", "name": "Average Directional Index", "category": "Trend"},
        {"id": "psar", "name": "Parabolic SAR", "category": "Trend"},
        
        # Momentum Indicators
        {"id": "rsi_14", "name": "Relative Strength Index (14)", "category": "Momentum"},
        {"id": "macd", "name": "MACD", "category": "Momentum"},
        {"id": "stoch", "name": "Stochastic Oscillator", "category": "Momentum"},
        {"id": "cci", "name": "Commodity Channel Index", "category": "Momentum"},
        {"id": "willr", "name": "Williams %R", "category": "Momentum"},
        
        # Volatility Indicators
        {"id": "bbands", "name": "Bollinger Bands", "category": "Volatility"},
        {"id": "atr", "name": "Average True Range", "category": "Volatility"},
        {"id": "std_dev", "name": "Standard Deviation", "category": "Volatility"},
        
        # Volume Indicators
        {"id": "obv", "name": "On-Balance Volume", "category": "Volume"},
        {"id": "ad", "name": "Accumulation/Distribution Line", "category": "Volume"},
        {"id": "mfi", "name": "Money Flow Index", "category": "Volume"}
    ]

def calculate_indicators(df, selected_indicators):
    """
    Calculate the selected technical indicators for the given stock data using pandas_ta.
    
    Args:
        df (pd.DataFrame): DataFrame containing stock data with OHLCV columns
        selected_indicators (list): List of indicator IDs to calculate
    
    Returns:
        pd.DataFrame: DataFrame with added indicator columns
    """
    # Create a copy to avoid modifying the original dataframe
    result_df = df.copy()
    
    # Ensure we have numeric data
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
    
    # Calculate selected indicators
    for indicator in selected_indicators:
        if indicator == "sma_20":
            result_df['sma_20'] = ta.sma(result_df['close'], length=20)
        
        elif indicator == "sma_50":
            result_df['sma_50'] = ta.sma(result_df['close'], length=50)
        
        elif indicator == "sma_200":
            result_df['sma_200'] = ta.sma(result_df['close'], length=200)
        
        elif indicator == "ema_12":
            result_df['ema_12'] = ta.ema(result_df['close'], length=12)
        
        elif indicator == "ema_26":
            result_df['ema_26'] = ta.ema(result_df['close'], length=26)
        
        elif indicator == "rsi_14":
            result_df['rsi_14'] = ta.rsi(result_df['close'], length=14)
        
        elif indicator == "macd":
            macd = ta.macd(result_df['close'], fast=12, slow=26, signal=9)
            result_df['macd'] = macd['MACD_12_26_9']
            result_df['macd_signal'] = macd['MACDs_12_26_9']
            result_df['macd_hist'] = macd['MACDh_12_26_9']
        
        elif indicator == "bbands":
            bbands = ta.bbands(result_df['close'], length=20, std=2)
            result_df['bollinger_upper'] = bbands['BBU_20_2.0']
            result_df['bollinger_middle'] = bbands['BBM_20_2.0']
            result_df['bollinger_lower'] = bbands['BBL_20_2.0']
        
        elif indicator == "adx":
            adx = ta.adx(result_df['high'], result_df['low'], result_df['close'], length=14)
            result_df['adx'] = adx['ADX_14']
        
        elif indicator == "atr":
            result_df['atr'] = ta.atr(result_df['high'], result_df['low'], result_df['close'], length=14)
        
        elif indicator == "obv":
            result_df['obv'] = ta.obv(result_df['close'], result_df['volume'])
        
        elif indicator == "stoch":
            stoch = ta.stoch(result_df['high'], result_df['low'], result_df['close'], k=14, d=3, smooth_k=3)
            result_df['stoch_k'] = stoch['STOCHk_14_3_3']
            result_df['stoch_d'] = stoch['STOCHd_14_3_3']
        
        elif indicator == "cci":
            result_df['cci'] = ta.cci(result_df['high'], result_df['low'], result_df['close'], length=14)
        
        elif indicator == "willr":
            result_df['williams_r'] = ta.willr(result_df['high'], result_df['low'], result_df['close'], length=14)
        
        elif indicator == "psar":
            psar = ta.psar(result_df['high'], result_df['low'])
            result_df['parabolic_sar'] = psar['PSARl_0.02_0.2']
        
        elif indicator == "std_dev":
            result_df['std_dev'] = ta.stdev(result_df['close'], length=20)
        
        elif indicator == "ad":
            result_df['ad'] = ta.ad(result_df['high'], result_df['low'], result_df['close'], result_df['volume'])
        
        elif indicator == "mfi":
            result_df['mfi'] = ta.mfi(result_df['high'], result_df['low'], result_df['close'], result_df['volume'], length=14)
    
    return result_df

def get_indicator_info(indicator_id):
    """
    Get information about a specific indicator.
    
    Args:
        indicator_id (str): ID of the indicator
    
    Returns:
        dict: Dictionary with indicator information
    """
    indicators = {
        "sma_20": {
            "name": "Simple Moving Average (20)",
            "description": "Average price over the last 20 periods.",
            "interpretation": "Price above SMA indicates uptrend, below indicates downtrend."
        },
        "sma_50": {
            "name": "Simple Moving Average (50)",
            "description": "Average price over the last 50 periods.",
            "interpretation": "Medium-term trend indicator."
        },
        "sma_200": {
            "name": "Simple Moving Average (200)",
            "description": "Average price over the last 200 periods.",
            "interpretation": "Long-term trend indicator. The 200-day SMA is often used to identify bull and bear markets."
        },
        "rsi_14": {
            "name": "Relative Strength Index (14)",
            "description": "Momentum oscillator that measures the speed and change of price movements.",
            "interpretation": "Values above 70 indicate overbought conditions, below 30 indicate oversold conditions."
        },
        "macd": {
            "name": "Moving Average Convergence Divergence",
            "description": "Trend-following momentum indicator showing the relationship between two moving averages of a security's price.",
            "interpretation": "MACD crossing above signal line is bullish, crossing below is bearish."
        }
        # Additional indicators can be added here
    }
    
    return indicators.get(indicator_id, {
        "name": indicator_id,
        "description": "Technical indicator",
        "interpretation": "Refer to technical analysis resources for interpretation."
    })