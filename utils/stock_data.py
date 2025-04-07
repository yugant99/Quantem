import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os
import json
import streamlit as st 

def get_demo_data(ticker, period="6mo"):
    """Return pre-cached demo data for specific tickers."""
    demo_cache_dir = "demo_cache"
    os.makedirs(demo_cache_dir, exist_ok=True)
    
    demo_file = f"{demo_cache_dir}/{ticker.upper()}_{period}.csv"
    
    if os.path.exists(demo_file):
        try:
            data = pd.read_csv(demo_file)
            data['date'] = pd.to_datetime(data['date'])
            print(f"Using demo data for {ticker} ({period})")
            cache_info = {
                "used": True,
                "file": demo_file,
                "is_demo": True,
                "last_updated": datetime.fromtimestamp(os.path.getmtime(demo_file))
            }
            return data, None, cache_info
        except Exception as e:
            return None, f"Error loading demo data: {str(e)}", None
    else:
        # Don't fall back to regular cache in demo mode
        return None, f"No demo data available for {ticker}", None

def get_stock_data(ticker, period="6mo", interval="1d", fmp_api_key=None):
    """
    Fetch stock data from Financial Modeling Prep.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Period for data (e.g., '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
        interval (str): Data interval (only 'daily' supported in this implementation)
        fmp_api_key (str, optional): Financial Modeling Prep API key
    
    Returns:
        pd.DataFrame: DataFrame containing the stock data
        str: Error message if any, None otherwise
    """
    if "demo_mode" in st.session_state and st.session_state.demo_mode:
        return get_demo_data(ticker, period)
    cached_data, error, cache_info = get_cached_data(ticker, period)
    if cached_data is not None:
        return cached_data, None, cache_info
    if not fmp_api_key:
        return None, "FMP API key is required"
        
    # First check cache
    cached_data, error,cache_info = get_cached_data(ticker, period)
    if cached_data is not None:
        return cached_data, None
        
    try:
        print(f"Fetching {ticker} data using Financial Modeling Prep API...")
        
        # Map period to timeframe for FMP
        if period == "1mo":
            timeframe = "30"
        elif period == "3mo":
            timeframe = "90"
        elif period == "6mo":
            timeframe = "180"
        elif period == "1y":
            timeframe = "365"
        elif period == "2y":
            timeframe = "730"
        elif period == "5y":
            timeframe = "1825"
        else:  # max
            timeframe = "3650"  # ~10 years
            
        # Call FMP API for historical data
        url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?timeseries={timeframe}&apikey={fmp_api_key}'
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        
        # Check if we have valid data
        if 'historical' in result:
            data_list = []
            
            for item in result['historical']:
                data_list.append({
                    'date': datetime.strptime(item['date'], '%Y-%m-%d'),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': int(item['volume'])
                })
            
            # Convert to DataFrame and sort by date
            fmp_data = pd.DataFrame(data_list)
            fmp_data = fmp_data.sort_values('date')
            
            if not fmp_data.empty:
                print(f"Successfully retrieved {len(fmp_data)} rows for {ticker} using FMP")
                
                # Save to cache
                save_to_cache(fmp_data, ticker, period)
                
                return fmp_data, None, None
            else:
                return None, f"No data returned for {ticker}"
        else:
            error_message = "No historical data in FMP response"
            if 'Error Message' in result:
                error_message = result['Error Message']
            return None, f"Error: {error_message}"
            
    except requests.exceptions.RequestException as e:
        return None, f"API request error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def verify_ticker(ticker,fmp_api_key = None):
    """
    Verify if a ticker symbol is valid using FMP API.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Use search API to check if ticker exists
        url = f'https://financialmodelingprep.com/api/v3/search?query={ticker}&limit=1&apikey={fmp_api_key}'
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                return True
        return False
    except:
        return False

# The caching functions can remain largely unchanged
def get_cached_data(ticker, period):
    """
    Get stock data from cache if available.
    
    Returns:
        pd.DataFrame: DataFrame containing the stock data, or None if not cached
        str: Error message if any, None otherwise
        dict: Cache info if used, None otherwise
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
                cache_info = {
                    "used": True,
                    "file": cache_file,
                    "last_updated": file_modified
                }
                return data, None, cache_info
            except Exception as e:
                print(f"Error reading cached data: {str(e)}")
    
    return None, "No cached data available or cache expired", None

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

def get_popular_stocks():
    """
    Return a list of popular stocks for the dropdown.
    """
    return [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "GOOG", "name": "Alphabet Inc. (Class C)"},
        {"symbol": "AMZN", "name": "Amazon.com, Inc."},
        {"symbol": "TSLA", "name": "Tesla, Inc."},
        {"symbol": "META", "name": "Meta Platforms, Inc."},
        {"symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
        {"symbol": "V", "name": "Visa Inc."},
        {"symbol": "WMT", "name": "Walmart Inc."}
    ]

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