import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os
import json
# In stock_data.py
def get_stock_data(ticker, period="6mo", interval="1d", alpha_vantage_key=None):
    """
    Fetch stock data with multiple fallback methods.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        interval (str): Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        alpha_vantage_key (str, optional): Alpha Vantage API key for fallback
    
    Returns:
        pd.DataFrame: DataFrame containing the stock data
        str: Error message if any, None otherwise
    """
    # First try: Using yfinance download method
    try:
        print(f"Attempting to fetch {ticker} data using yfinance download method...")
        end_date = datetime.now()
        
        if period == "1mo":
            start_date = end_date - timedelta(days=30)
        elif period == "3mo":
            start_date = end_date - timedelta(days=90)
        elif period == "6mo":
            start_date = end_date - timedelta(days=180)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "2y":
            start_date = end_date - timedelta(days=730)
        elif period == "5y":
            start_date = end_date - timedelta(days=1825)
        elif period == "max":
            start_date = end_date - timedelta(days=3650)  # 10 years as "max"
        else:
            start_date = end_date - timedelta(days=180)
            
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        data = yf.download(ticker, start=start_str, end=end_str, interval=interval)
        
        if not data.empty:
            print(f"Successfully retrieved {len(data)} rows for {ticker} using download method")
            data = data.reset_index()
            data.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            }, inplace=True)
            return data, None
        else:
            print(f"Empty data returned for {ticker} using download method")
    except Exception as e:
        print(f"Error using yfinance download method: {str(e)}")

    # Try the history method if download fails
    try:
        print(f"Attempting to fetch {ticker} data using yfinance history method...")
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        
        if not data.empty:
            print(f"Successfully retrieved {len(data)} rows for {ticker}")
            data = data.reset_index()
            data.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            }, inplace=True)
            return data, None
        else:
            print(f"Empty data returned for {ticker} using history method")
    except Exception as e:
        print(f"Error using yfinance history method: {str(e)}")

    # Alpha Vantage as last resort
    if alpha_vantage_key:
        try:
            print(f"Attempting to fetch {ticker} data using Alpha Vantage API...")
            # Determine the Alpha Vantage function based on the interval
            if interval in ['1d', '5d', '1wk', '1mo']:
                function = 'TIME_SERIES_DAILY'
                
                # Map period to outputsize
                outputsize = 'full' if period in ['1y', '2y', '5y', 'max'] else 'compact'
                
                url = f'https://www.alphavantage.co/query?function={function}&symbol={ticker}&outputsize={outputsize}&apikey={alpha_vantage_key}'
                response = requests.get(url)
                result = response.json()
                
                # Check if we have valid data
                if 'Time Series (Daily)' in result:
                    time_series = result['Time Series (Daily)']
                    data_list = []
                    
                    for date, values in time_series.items():
                        data_list.append({
                            'date': datetime.strptime(date, '%Y-%m-%d'),
                            'open': float(values['1. open']),
                            'high': float(values['2. high']),
                            'low': float(values['3. low']),
                            'close': float(values['4. close']),
                            'volume': int(values['5. volume'])
                        })
                    
                    # Convert to DataFrame and sort by date
                    av_data = pd.DataFrame(data_list)
                    av_data = av_data.sort_values('date')
                    
                    # Filter based on period
                    end_date = av_data['date'].max()
                    if period == "1mo":
                        start_date = end_date - timedelta(days=30)
                    elif period == "3mo":
                        start_date = end_date - timedelta(days=90)
                    elif period == "6mo":
                        start_date = end_date - timedelta(days=180)
                    elif period == "1y":
                        start_date = end_date - timedelta(days=365)
                    elif period == "2y":
                        start_date = end_date - timedelta(days=730)
                    else:  # 5y or max
                        start_date = end_date - timedelta(days=1825)
                        
                    av_data = av_data[av_data['date'] >= start_date]
                    
                    if not av_data.empty:
                        print(f"Successfully retrieved {len(av_data)} rows for {ticker} using Alpha Vantage")
                        return av_data, None
                    else:
                        print("Filtered Alpha Vantage data is empty")
                else:
                    error_message = "No time series data in Alpha Vantage response"
                    if 'Error Message' in result:
                        error_message += f": {result['Error Message']}"
                    print(f"{error_message} for {ticker}")
            else:
                print("Alpha Vantage only supports daily, weekly, and monthly intervals in the free tier")
        except Exception as e:
            print(f"Error using Alpha Vantage API: {str(e)}")

    # If we've reached here, all methods failed
    # Let's check if the ticker is actually valid first
    is_valid = verify_ticker(ticker)
    if is_valid:
        return None, f"Could not fetch data for {ticker} using multiple methods. The ticker appears valid but data could not be retrieved. This may be due to API limits or connectivity issues."
    else:
        return None, f"Could not fetch data for {ticker}. Please verify that the ticker symbol is valid."

def get_available_periods():
    """
    Return a list of available time periods for data fetching.
    """
    return [
        {"value": "1mo", "label": "1 Month"},
        {"value": "3mo", "label": "3 Months"},
        {"value": "6mo", "label": "6 Months"},
        {"value": "1y", "label": "1 Year"},
        {"value": "2y", "label": "2 Years"},
        {"value": "5y", "label": "5 Years"},
        {"value": "max", "label": "Maximum"}
    ]

def get_popular_stocks():
    """
    Return a list of popular stocks for the dropdown.
    """
    return [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "GOOG", "name": "Alphabet Inc. (Class C)"},  # Changed from GOOGL to GOOG
        {"symbol": "AMZN", "name": "Amazon.com, Inc."},
        {"symbol": "TSLA", "name": "Tesla, Inc."},
        {"symbol": "META", "name": "Meta Platforms, Inc."},
        {"symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
        {"symbol": "V", "name": "Visa Inc."},
        {"symbol": "WMT", "name": "Walmart Inc."}
    ]

def verify_ticker(ticker):
    """
    Verify if a ticker symbol is valid.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Check if we have a name key, which all valid tickers should have
        return 'shortName' in info or 'longName' in info
    except:
        return False
def get_cached_data(ticker, period):
    """
    Get stock data from cache if available.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Time period
    
    Returns:
        pd.DataFrame: DataFrame containing the stock data, or None if not cached
        str: Error message if any, None otherwise
    """
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = f"{cache_dir}/{ticker.upper()}_{period}.csv"
    
    # Check if cache file exists and is less than 24 hours old
    if os.path.exists(cache_file):
        file_modified = datetime.fromtimestamp(os.path.getmtime(cache_file))
        # Cache is valid for 24 hours
        if datetime.now() - file_modified < timedelta(hours=24):
            try:
                data = pd.read_csv(cache_file)
                data['date'] = pd.to_datetime(data['date'])
                print(f"Using cached data for {ticker} ({period})")
                return data, None
            except Exception as e:
                print(f"Error reading cached data: {str(e)}")
    
    return None, "No cached data available or cache expired"

def save_to_cache(data, ticker, period):
    """
    Save stock data to cache.
    
    Args:
        data (pd.DataFrame): DataFrame containing stock data
        ticker (str): Stock ticker symbol
        period (str): Time period
    """
    if data is None or data.empty:
        return
    
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = f"{cache_dir}/{ticker.upper()}_{period}.csv"
    data.to_csv(cache_file, index=False)
    print(f"Saved data to cache: {cache_file}")

# Update the get_stock_data function to use cache
def get_stock_data_with_cache(ticker, period="6mo", interval="1d", alpha_vantage_key=None):
    """
    Fetch stock data with caching and multiple fallback methods.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        interval (str): Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        alpha_vantage_key (str, optional): Alpha Vantage API key for fallback
    
    Returns:
        pd.DataFrame: DataFrame containing the stock data
        str: Error message if any, None otherwise
    """
    # First try: Check cache
    data, error = get_cached_data(ticker, period)
    if data is not None:
        return data, None
    
    # If not in cache, fetch from APIs
    data, error = get_stock_data(ticker, period, interval, alpha_vantage_key)
    
    # Save to cache if successful
    if data is not None and not data.empty:
        save_to_cache(data, ticker, period)
    
    return data, error