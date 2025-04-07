import pandas as pd
import pandas_ta as ta
import numpy as np

def get_available_strategies():
    """
    Return a list of available trading strategies.
    """
    return [
        {
            "id": "moving_average_crossover",
            "name": "Moving Average Crossover",
            "description": "Generates signals when a fast MA crosses a slow MA. This strategy is based on the idea that when short-term momentum overtakes long-term momentum (fast MA crosses above slow MA), it's a buy signal, and when short-term momentum falls below long-term momentum, it's a sell signal.",
            "parameters": [
                {"id": "fast_period", "name": "Fast MA Period", "default": 20, "min": 5, "max": 50},
                {"id": "slow_period", "name": "Slow MA Period", "default": 50, "min": 10, "max": 200},
                {"id": "ma_type", "name": "MA Type", "default": "sma", "options": ["sma", "ema"]}
            ]
        },
        {
            "id": "bollinger_bands_bounce",
            "name": "Bollinger Bands Bounce",
            "description": "Generates signals based on price movements near Bollinger Bands. This strategy buys when price touches the lower band and sells when price touches the upper band, capturing mean reversion movements.",
            "parameters": [
                {"id": "bb_length", "name": "BB Length", "default": 20, "min": 10, "max": 50},
                {"id": "bb_std", "name": "BB Standard Deviation", "default": 2.0, "min": 1.0, "max": 3.0, "step": 0.1},
                {"id": "entry_threshold", "name": "Entry Threshold %", "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1}
            ]
        },
        {
            "id": "rsi_overbought_oversold",
            "name": "RSI Overbought/Oversold",
            "description": "Generates signals when RSI enters overbought or oversold zones. This strategy buys when RSI drops below the oversold threshold and sells when it rises above the overbought threshold.",
            "parameters": [
                {"id": "rsi_length", "name": "RSI Length", "default": 14, "min": 7, "max": 30},
                {"id": "overbought", "name": "Overbought Threshold", "default": 70, "min": 60, "max": 90},
                {"id": "oversold", "name": "Oversold Threshold", "default": 30, "min": 10, "max": 40}
            ]
        },
        {
            "id": "macd_crossover",
            "name": "MACD Crossover",
            "description": "Generates signals when MACD line crosses the signal line. This strategy buys when MACD crosses above the signal line and sells when MACD crosses below the signal line.",
            "parameters": [
                {"id": "fast_length", "name": "Fast Length", "default": 12, "min": 8, "max": 20},
                {"id": "slow_length", "name": "Slow Length", "default": 26, "min": 15, "max": 40},
                {"id": "signal_length", "name": "Signal Length", "default": 9, "min": 5, "max": 15}
            ]
        },
        {
            "id": "supertrend",
            "name": "SuperTrend",
            "description": "A trend-following indicator that uses ATR to determine potential trend direction and reversal points. It generates signals when the price crosses the SuperTrend line.",
            "parameters": [
                {"id": "atr_period", "name": "ATR Period", "default": 10, "min": 5, "max": 30},
                {"id": "atr_multiplier", "name": "ATR Multiplier", "default": 3.0, "min": 1.0, "max": 8.0, "step": 0.1}
            ]
        },
        {
            "id": "ichimoku_cloud",
            "name": "Ichimoku Cloud",
            "description": "A comprehensive indicator that provides information on support/resistance, trend direction, and momentum. It generates signals based on multiple components of the Ichimoku system.",
            "parameters": [
                {"id": "tenkan_period", "name": "Tenkan Period", "default": 9, "min": 5, "max": 20},
                {"id": "kijun_period", "name": "Kijun Period", "default": 26, "min": 15, "max": 50},
                {"id": "senkou_span_b_period", "name": "Senkou Span B Period", "default": 52, "min": 30, "max": 100}
            ]
        }
    ]

def apply_strategy(df, strategy_id, params):
    """
    Apply a trading strategy to the dataframe and return signals.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data
        strategy_id (str): ID of the strategy to apply
        params (dict): Parameters for the strategy
    
    Returns:
        pd.DataFrame: DataFrame with added signal columns
    """
    result_df = df.copy()
    
    if strategy_id == "moving_average_crossover":
        fast_period = params.get("fast_period", 20)
        slow_period = params.get("slow_period", 50)
        ma_type = params.get("ma_type", "sma")
        
        if ma_type == "sma":
            result_df['fast_ma'] = ta.sma(result_df['close'], length=fast_period)
            result_df['slow_ma'] = ta.sma(result_df['close'], length=slow_period)
        else:  # ema
            result_df['fast_ma'] = ta.ema(result_df['close'], length=fast_period)
            result_df['slow_ma'] = ta.ema(result_df['close'], length=slow_period)
        
        # Generate crossover signals
        result_df['signal'] = 0
        result_df.loc[result_df['fast_ma'] > result_df['slow_ma'], 'signal'] = 1  # Buy signal
        result_df.loc[result_df['fast_ma'] < result_df['slow_ma'], 'signal'] = -1  # Sell signal
        
        # Find actual buy/sell points (when signal changes)
        result_df['signal_change'] = result_df['signal'].diff().fillna(0)
        result_df['buy_signal'] = (result_df['signal_change'] == 2).astype(int)
        result_df['sell_signal'] = (result_df['signal_change'] == -2).astype(int)
    
    elif strategy_id == "bollinger_bands_bounce":
        bb_length = params.get("bb_length", 20)
        bb_std = params.get("bb_std", 2.0)
        entry_threshold = params.get("entry_threshold", 1.0) / 100  # Convert to decimal
        
        bbands = ta.bbands(result_df['close'], length=bb_length, std=bb_std)
        result_df['bb_upper'] = bbands['BBU_' + str(bb_length) + '_' + str(bb_std)]
        result_df['bb_middle'] = bbands['BBM_' + str(bb_length) + '_' + str(bb_std)]
        result_df['bb_lower'] = bbands['BBL_' + str(bb_length) + '_' + str(bb_std)]
        
        # Calculate percentage distance from price to bands
        result_df['pct_b'] = (result_df['close'] - result_df['bb_lower']) / (result_df['bb_upper'] - result_df['bb_lower'])
        
        # Generate signals
        result_df['buy_signal'] = ((result_df['pct_b'] < entry_threshold) & 
                                   (result_df['pct_b'].shift(1) >= entry_threshold)).astype(int)
        result_df['sell_signal'] = ((result_df['pct_b'] > 1 - entry_threshold) & 
                                    (result_df['pct_b'].shift(1) <= 1 - entry_threshold)).astype(int)
    
    elif strategy_id == "rsi_overbought_oversold":
        rsi_length = params.get("rsi_length", 14)
        overbought = params.get("overbought", 70)
        oversold = params.get("oversold", 30)
        
        result_df['rsi'] = ta.rsi(result_df['close'], length=rsi_length)
        
        # Generate signals when RSI crosses the thresholds
        result_df['buy_signal'] = ((result_df['rsi'] < oversold) & 
                                   (result_df['rsi'].shift(1) >= oversold)).astype(int)
        result_df['sell_signal'] = ((result_df['rsi'] > overbought) & 
                                   (result_df['rsi'].shift(1) <= overbought)).astype(int)
    
    elif strategy_id == "macd_crossover":
        fast_length = params.get("fast_length", 12)
        slow_length = params.get("slow_length", 26)
        signal_length = params.get("signal_length", 9)
        
        macd = ta.macd(result_df['close'], fast=fast_length, slow=slow_length, signal=signal_length)
        result_df['macd_line'] = macd[f'MACD_{fast_length}_{slow_length}_{signal_length}']
        result_df['macd_signal'] = macd[f'MACDs_{fast_length}_{slow_length}_{signal_length}']
        result_df['macd_hist'] = macd[f'MACDh_{fast_length}_{slow_length}_{signal_length}']
        
        # Generate signals on MACD crossover
        result_df['buy_signal'] = ((result_df['macd_line'] > result_df['macd_signal']) & 
                                  (result_df['macd_line'].shift(1) <= result_df['macd_signal'].shift(1))).astype(int)
        result_df['sell_signal'] = ((result_df['macd_line'] < result_df['macd_signal']) & 
                                   (result_df['macd_line'].shift(1) >= result_df['macd_signal'].shift(1))).astype(int)
    
    elif strategy_id == "supertrend":
        atr_period = params.get("atr_period", 10)
        atr_multiplier = params.get("atr_multiplier", 3.0)
        
        # Calculate ATR
        result_df['atr'] = ta.atr(result_df['high'], result_df['low'], result_df['close'], length=atr_period)
        
        # Calculate basic upper and lower bands
        result_df['basic_upper'] = ((result_df['high'] + result_df['low']) / 2) + (atr_multiplier * result_df['atr'])
        result_df['basic_lower'] = ((result_df['high'] + result_df['low']) / 2) - (atr_multiplier * result_df['atr'])
        
        # Initialize SuperTrend columns
        result_df['supertrend_upper'] = 0.0
        result_df['supertrend_lower'] = 0.0
        result_df['supertrend'] = 0.0
        result_df['supertrend_direction'] = 0  # 1 for uptrend, -1 for downtrend
        
        # Calculate SuperTrend
        for i in range(1, len(result_df)):
            # Lower band
            if result_df['basic_lower'].iloc[i] > result_df['supertrend_lower'].iloc[i-1] or \
               result_df['close'].iloc[i-1] < result_df['supertrend_lower'].iloc[i-1]:
                result_df.loc[result_df.index[i], 'supertrend_lower'] = result_df['basic_lower'].iloc[i]
            else:
                result_df.loc[result_df.index[i], 'supertrend_lower'] = result_df['supertrend_lower'].iloc[i-1]
            
            # Upper band
            if result_df['basic_upper'].iloc[i] < result_df['supertrend_upper'].iloc[i-1] or \
               result_df['close'].iloc[i-1] > result_df['supertrend_upper'].iloc[i-1]:
                result_df.loc[result_df.index[i], 'supertrend_upper'] = result_df['basic_upper'].iloc[i]
            else:
                result_df.loc[result_df.index[i], 'supertrend_upper'] = result_df['supertrend_upper'].iloc[i-1]
            
            # SuperTrend
            if result_df['supertrend'].iloc[i-1] == result_df['supertrend_upper'].iloc[i-1] and \
               result_df['close'].iloc[i] <= result_df['supertrend_upper'].iloc[i]:
                result_df.loc[result_df.index[i], 'supertrend'] = result_df['supertrend_upper'].iloc[i]
            elif result_df['supertrend'].iloc[i-1] == result_df['supertrend_upper'].iloc[i-1] and \
                 result_df['close'].iloc[i] > result_df['supertrend_upper'].iloc[i]:
                result_df.loc[result_df.index[i], 'supertrend'] = result_df['supertrend_lower'].iloc[i]
            elif result_df['supertrend'].iloc[i-1] == result_df['supertrend_lower'].iloc[i-1] and \
                 result_df['close'].iloc[i] >= result_df['supertrend_lower'].iloc[i]:
                result_df.loc[result_df.index[i], 'supertrend'] = result_df['supertrend_lower'].iloc[i]
            elif result_df['supertrend'].iloc[i-1] == result_df['supertrend_lower'].iloc[i-1] and \
                 result_df['close'].iloc[i] < result_df['supertrend_lower'].iloc[i]:
                result_df.loc[result_df.index[i], 'supertrend'] = result_df['supertrend_upper'].iloc[i]
            
            # Direction
            if result_df['close'].iloc[i] > result_df['supertrend'].iloc[i]:
                result_df.loc[result_df.index[i], 'supertrend_direction'] = 1
            else:
                result_df.loc[result_df.index[i], 'supertrend_direction'] = -1
        
        # Generate signals on direction change
        result_df['direction_change'] = result_df['supertrend_direction'].diff().fillna(0)
        result_df['buy_signal'] = (result_df['direction_change'] == 2).astype(int)
        result_df['sell_signal'] = (result_df['direction_change'] == -2).astype(int)
    
    elif strategy_id == "ichimoku_cloud":
        tenkan_period = params.get("tenkan_period", 9)
        kijun_period = params.get("kijun_period", 26)
        senkou_span_b_period = params.get("senkou_span_b_period", 52)
        
        # Calculate Ichimoku components
        # Tenkan-sen (Conversion Line): (highest high + lowest low)/2 for the past 9 periods
        high_tenkan = result_df['high'].rolling(window=tenkan_period).max()
        low_tenkan = result_df['low'].rolling(window=tenkan_period).min()
        result_df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2
        
        # Kijun-sen (Base Line): (highest high + lowest low)/2 for the past 26 periods
        high_kijun = result_df['high'].rolling(window=kijun_period).max()
        low_kijun = result_df['low'].rolling(window=kijun_period).min()
        result_df['kijun_sen'] = (high_kijun + low_kijun) / 2
        
        # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2 plotted 26 periods ahead
        result_df['senkou_span_a'] = ((result_df['tenkan_sen'] + result_df['kijun_sen']) / 2).shift(kijun_period)
        
        # Senkou Span B (Leading Span B): (highest high + lowest low)/2 for the past 52 periods plotted 26 periods ahead
        high_senkou = result_df['high'].rolling(window=senkou_span_b_period).max()
        low_senkou = result_df['low'].rolling(window=senkou_span_b_period).min()
        result_df['senkou_span_b'] = ((high_senkou + low_senkou) / 2).shift(kijun_period)
        
        # Chikou Span (Lagging Span): Close plotted 26 periods back
        result_df['chikou_span'] = result_df['close'].shift(-kijun_period)
        
        # Generate signals
        # Buy when Tenkan-sen crosses above Kijun-sen
        result_df['buy_signal'] = ((result_df['tenkan_sen'] > result_df['kijun_sen']) & 
                                   (result_df['tenkan_sen'].shift(1) <= result_df['kijun_sen'].shift(1)) & 
                                   (result_df['close'] > result_df['senkou_span_a']) & 
                                   (result_df['close'] > result_df['senkou_span_b'])).astype(int)
        
        # Sell when Tenkan-sen crosses below Kijun-sen
        result_df['sell_signal'] = ((result_df['tenkan_sen'] < result_df['kijun_sen']) & 
                                    (result_df['tenkan_sen'].shift(1) >= result_df['kijun_sen'].shift(1)) & 
                                    (result_df['close'] < result_df['senkou_span_a']) & 
                                    (result_df['close'] < result_df['senkou_span_b'])).astype(int)
    
    # Calculate strategy performance
    calculate_performance(result_df)
    
    return result_df

def calculate_performance(df):
    """
    Calculate performance metrics for a strategy.
    
    Args:
        df (pd.DataFrame): DataFrame with signal columns
    """
    if 'buy_signal' not in df.columns or 'sell_signal' not in df.columns:
        return
    
    # Find all buy and sell points
    buy_points = df[df['buy_signal'] == 1].index
    sell_points = df[df['sell_signal'] == 1].index
    
    trades = []
    position_open = False
    entry_price = 0
    entry_date = None
    
    # Simulate trades
    for i in range(len(df)):
        if i in buy_points and not position_open:
            position_open = True
            entry_price = df.iloc[i]['close']
            entry_date = df.iloc[i]['date']
        elif i in sell_points and position_open:
            position_open = False
            exit_price = df.iloc[i]['close']
            exit_date = df.iloc[i]['date']
            pct_return = (exit_price / entry_price - 1) * 100
            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': exit_date,
                'exit_price': exit_price,
                'return_pct': pct_return
            })
    
    # Calculate metrics
    if trades:
        df.loc[:, 'total_trades'] = len(trades)
        df.loc[:, 'winning_trades'] = sum(1 for t in trades if t['return_pct'] > 0)
        df.loc[:, 'win_rate'] = df.loc[0, 'winning_trades'] / df.loc[0, 'total_trades'] * 100 if df.loc[0, 'total_trades'] > 0 else 0
        df.loc[:, 'avg_return'] = sum(t['return_pct'] for t in trades) / len(trades) if trades else 0
        
        # Calculate cumulative return
        df.loc[:, 'strategy_return'] = 0
        
        # Initialize the columns if they don't exist
        if 'in_position' not in df.columns:
            df['in_position'] = False
        if 'cumulative_return' not in df.columns:
            df['cumulative_return'] = 1.0  # Start with 100% of initial capital
        
        # Simulate strategy performance
        in_position = False
        for i in range(1, len(df)):
            if df.iloc[i-1]['buy_signal'] == 1:
                in_position = True
            elif df.iloc[i-1]['sell_signal'] == 1:
                in_position = False
            
            if in_position:
                daily_return = df.iloc[i]['close'] / df.iloc[i-1]['close']
                df.loc[df.index[i], 'strategy_return'] = daily_return - 1
            else:
                df.loc[df.index[i], 'strategy_return'] = 0
            
            df.loc[df.index[i], 'in_position'] = in_position
            df.loc[df.index[i], 'cumulative_return'] = df.loc[df.index[i-1], 'cumulative_return'] * (1 + df.loc[df.index[i], 'strategy_return'])
    else:
        # No trades executed
        df.loc[:, 'total_trades'] = 0
        df.loc[:, 'winning_trades'] = 0
        df.loc[:, 'win_rate'] = 0
        df.loc[:, 'avg_return'] = 0
        df.loc[:, 'cumulative_return'] = 1.0

def get_strategy_params_by_period(strategy_id, period):
    """
    Get optimized strategy parameters based on the selected time period.
    
    Args:
        strategy_id (str): ID of the strategy
        period (str): Selected time period (e.g., '1mo', '3mo', '1y')
    
    Returns:
        dict: Optimized parameters for the strategy
    """
    # Default parameters
    defaults = {
        "moving_average_crossover": {
            "fast_period": 20,
            "slow_period": 50,
            "ma_type": "sma"
        },
        "bollinger_bands_bounce": {
            "bb_length": 20,
            "bb_std": 2.0,
            "entry_threshold": 1.0
        },
        "rsi_overbought_oversold": {
            "rsi_length": 14,
            "overbought": 70,
            "oversold": 30
        },
        "macd_crossover": {
            "fast_length": 12,
            "slow_length": 26,
            "signal_length": 9
        },
        "supertrend": {
            "atr_period": 10,
            "atr_multiplier": 3.0
        },
        "ichimoku_cloud": {
            "tenkan_period": 9,
            "kijun_period": 26,
            "senkou_span_b_period": 52
        }
    }
    
    # Optimized parameters based on time period
    period_params = {
        "1mo": {
            "moving_average_crossover": {"fast_period": 5, "slow_period": 20},
            "bollinger_bands_bounce": {"bb_length": 10},
            "rsi_overbought_oversold": {"rsi_length": 7},
            "macd_crossover": {"fast_length": 8, "slow_length": 17},
            "supertrend": {"atr_period": 5, "atr_multiplier": 2.0},
            "ichimoku_cloud": {"tenkan_period": 5, "kijun_period": 15, "senkou_span_b_period": 30}
        },
        "3mo": {
            "moving_average_crossover": {"fast_period": 10, "slow_period": 30},
            "bollinger_bands_bounce": {"bb_length": 15},
            "rsi_overbought_oversold": {"rsi_length": 10},
            "macd_crossover": {"fast_length": 10, "slow_length": 21},
            "supertrend": {"atr_period": 7, "atr_multiplier": 2.5},
            "ichimoku_cloud": {"tenkan_period": 7, "kijun_period": 22, "senkou_span_b_period": 44}
        },
        "6mo": {
            "moving_average_crossover": {"fast_period": 15, "slow_period": 40},
            "bollinger_bands_bounce": {"bb_length": 20},
            "rsi_overbought_oversold": {"rsi_length": 14},
            "macd_crossover": {"fast_length": 12, "slow_length": 26},
            "supertrend": {"atr_period": 10, "atr_multiplier": 3.0},
            "ichimoku_cloud": {"tenkan_period": 9, "kijun_period": 26, "senkou_span_b_period": 52}
        },
        "1y": {
            "moving_average_crossover": {"fast_period": 20, "slow_period": 50},
            "bollinger_bands_bounce": {"bb_length": 20},
            "rsi_overbought_oversold": {"rsi_length": 14},
            "macd_crossover": {"fast_length": 12, "slow_length": 26},
            "supertrend": {"atr_period": 14, "atr_multiplier": 3.0},
            "ichimoku_cloud": {"tenkan_period": 9, "kijun_period": 26, "senkou_span_b_period": 52}
        },
        "2y": {
            "moving_average_crossover": {"fast_period": 30, "slow_period": 100},
            "bollinger_bands_bounce": {"bb_length": 30},
            "rsi_overbought_oversold": {"rsi_length": 21},
            "macd_crossover": {"fast_length": 15, "slow_length": 30},
            "supertrend": {"atr_period": 20, "atr_multiplier": 3.5},
            "ichimoku_cloud": {"tenkan_period": 10, "kijun_period": 30, "senkou_span_b_period": 60}
        },
        "5y": {
            "moving_average_crossover": {"fast_period": 50, "slow_period": 200},
            "bollinger_bands_bounce": {"bb_length": 50},
            "rsi_overbought_oversold": {"rsi_length": 28},
            "macd_crossover": {"fast_length": 18, "slow_length": 39},
            "supertrend": {"atr_period": 25, "atr_multiplier": 4.0},
            "ichimoku_cloud": {"tenkan_period": 12, "kijun_period": 36, "senkou_span_b_period": 72}
        }
    }
    
    # Get base parameters
    params = defaults.get(strategy_id, {}).copy()
    
    # Update with period-specific parameters if available
    if period in period_params and strategy_id in period_params[period]:
        params.update(period_params[period][strategy_id])
    
    return params