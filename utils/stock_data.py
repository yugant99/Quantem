import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import os

def get_stock_data(ticker, period="6mo", interval="1d", fmp_api_key=None):
    alpha_vantage_key = fmp_api_key  # map for fallback usage

    try:
        print(f"Attempting to fetch {ticker} data using yfinance...")
        end_date = datetime.now()

        periods_days = {
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "max": 3650
        }

        start_date = end_date - timedelta(days=periods_days.get(period, 180))
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        data = yf.download(ticker, start=start_str, end=end_str, interval=interval)

        if not data.empty:
            data = data.reset_index()
            data.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            }, inplace=True)
            return data, None
    except Exception as e:
        print(f"yfinance download method failed: {e}")

    # fallback to Alpha Vantage
    if alpha_vantage_key:
        try:
            print(f"Using Alpha Vantage fallback for {ticker}")
            function = 'TIME_SERIES_DAILY'
            outputsize = 'full' if period in ['1y', '2y', '5y', 'max'] else 'compact'

            url = f'https://www.alphavantage.co/query?function={function}&symbol={ticker}&outputsize={outputsize}&apikey={alpha_vantage_key}'
            response = requests.get(url)
            result = response.json()

            if 'Time Series (Daily)' in result:
                ts = result['Time Series (Daily)']
                records = [
                    {
                        'date': datetime.strptime(date, '%Y-%m-%d'),
                        'open': float(values['1. open']),
                        'high': float(values['2. high']),
                        'low': float(values['3. low']),
                        'close': float(values['4. close']),
                        'volume': int(values['5. volume'])
                    }
                    for date, values in ts.items()
                ]

                df = pd.DataFrame(records).sort_values('date')
                end_date = df['date'].max()
                start_date = end_date - timedelta(days=periods_days.get(period, 180))
                df = df[df['date'] >= start_date]

                if not df.empty:
                    return df, None
        except Exception as e:
            print(f"Alpha Vantage fallback failed: {e}")

    return None, f"Failed to fetch data for {ticker}"

def get_stock_data_with_cache(ticker, period="6mo", interval="1d", fmp_api_key=None):
    data, error = get_cached_data(ticker, period)
    if data is not None:
        return data, None

    data, error = get_stock_data(ticker, period, interval, fmp_api_key)
    if data is not None and not data.empty:
        save_to_cache(data, ticker, period)

    return data, error

def get_cached_data(ticker, period):
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{cache_dir}/{ticker.upper()}_{period}.csv"

    if os.path.exists(cache_file):
        file_modified = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - file_modified < timedelta(hours=24):
            try:
                data = pd.read_csv(cache_file)
                data['date'] = pd.to_datetime(data['date'])
                print(f"Using cached data for {ticker} ({period})")
                return data, None
            except Exception as e:
                print(f"Cache read error: {e}")

    return None, "No valid cached data"

def save_to_cache(data, ticker, period):
    if data is None or data.empty:
        return
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{cache_dir}/{ticker.upper()}_{period}.csv"
    data.to_csv(cache_file, index=False)
    print(f"Saved cache: {cache_file}")

def get_available_periods():
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

def verify_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return 'shortName' in info or 'longName' in info
    except:
        return False
