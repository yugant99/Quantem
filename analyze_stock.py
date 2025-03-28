#!/usr/bin/env python3
"""
analyze_stock_news.py - Send stock news data to Gemini model for analysis
"""

import os
import json
import requests
import argparse
import time
from pathlib import Path
from datetime import datetime

class StockNewsAnalyzer:
    def __init__(self, api_key, model="google/gemini-2.5-pro-exp-03-25:free"):
        """Initialize the analyzer with API key and model"""
        self.api_key = api_key
        self.model = model
        self.url = 'https://openrouter.ai/api/v1/chat/completions'
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://stock-analyzer.app',
            'X-Title': 'Stock Analysis Tool'
        }
        
        # Create output directory
        self.output_dir = Path("./data/ai_analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_data(self, file_path):
        """Load news data from the specified file"""
        print(f"🔍 CHECKPOINT: Loading data from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Handle the expected structure from aapl_stock_data_1743047262.json
            if 'sources' in data and 'news' in data['sources'] and 'articles' in data['sources']['news']:
                news_data = data['sources']['news']['articles']
                print(f"✅ CHECKPOINT: Successfully loaded data with {len(news_data)} news items")
                return news_data
            elif 'sources' in data and 'reddit' in data['sources'] and 'submissions' in data['sources']['reddit']:
                # If there's no news but there are Reddit submissions, use those
                reddit_data = data['sources']['reddit']['submissions']
                print(f"✅ CHECKPOINT: Successfully loaded data with {len(reddit_data)} Reddit submissions")
                return reddit_data
            else:
                print(f"❌ ERROR: Unexpected data structure - could not find news articles or Reddit submissions")
                return None
        except Exception as e:
            print(f"❌ ERROR: Failed to load data - {str(e)}")
            return None
    
    def load_stock_data(self, file_path):
        """Load stock price data if available"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            print(f"✅ CHECKPOINT: Successfully loaded stock data")
            return data
        except Exception as e:
            print(f"⚠️ WARNING: No stock data found or error loading - {str(e)}")
            return None
    
    def prepare_prompt(self, news_data, stock_data=None, ticker="UNKNOWN"):
        """Create a comprehensive prompt for the LLM"""
        print(f"🔍 CHECKPOINT: Preparing prompt for {ticker} with {len(news_data)} news items")
        
        # Extract recent news items (limit to avoid token issues)
        recent_news = news_data[:20] if len(news_data) > 20 else news_data
        
        # Create a news summary section
        news_section = "\n\n### NEWS ARTICLES:\n\n"
        
        # Check the structure of the first item to determine if we're dealing with news or Reddit posts
        first_item = recent_news[0] if recent_news else {}
        
        if isinstance(first_item, dict):
            # Handle structure based on data type
            if 'source' in first_item and 'title' in first_item:  # News article
                for i, item in enumerate(recent_news):
                    published_date = item.get("published_at", "unknown").split("T")[0]  # Just get the date part
                    news_section += f"{i+1}. [{published_date}] {item.get('title', 'No title')}\n"
                    news_section += f"   Source: {item.get('source', 'Unknown')}\n"
                    
                    # Include content if available and not too long
                    content = item.get("content", "")
                    if content and len(content) > 10:  # Make sure it's not empty or tiny
                        # Truncate if too long
                        if len(content) > 500:
                            content = content[:500] + "..."
                        news_section += f"   Summary: {content}\n"
                    news_section += "\n"
            elif 'subreddit' in first_item and 'title' in first_item:  # Reddit post
                for i, item in enumerate(recent_news):
                    created_date = item.get("created_datetime", "unknown").split("T")[0]  # Just get the date part
                    news_section += f"{i+1}. [{created_date}] {item.get('title', 'No title')}\n"
                    news_section += f"   Subreddit: r/{item.get('subreddit', 'Unknown')}\n"
                    
                    # Include content if available and not too long
                    content = item.get("selftext", "")
                    if content and len(content) > 10:  # Make sure it's not empty or tiny
                        # Truncate if too long
                        if len(content) > 500:
                            content = content[:500] + "..."
                        news_section += f"   Content: {content}\n"
                    news_section += "\n"
            else:  # Generic handling for other dictionary structures
                for i, item in enumerate(recent_news):
                    news_section += f"{i+1}. Item {i+1}\n"
                    for key, value in item.items():
                        if isinstance(value, str) and len(value) <= 500:
                            news_section += f"   {key}: {value}\n"
                        elif isinstance(value, str):
                            news_section += f"   {key}: {value[:500]}...\n"
                    news_section += "\n"
        else:  # Handle non-dictionary items as strings
            news_section += "Could not parse news data in expected format. Raw data:\n\n"
            for i, item in enumerate(recent_news[:5]):  # Only show first 5 items
                news_section += f"{i+1}. {str(item)[:300]}...\n\n"
        
        # Add stock price data if available
        stock_section = ""
        if stock_data:
            stock_section = "\n\n### STOCK PRICE DATA:\n"
            
            if 'ticker' in stock_data:
                stock_section += f"Ticker: {stock_data.get('ticker', 'UNKNOWN')}\n"
            
            if 'search_period' in stock_data:
                period = stock_data.get('search_period', {})
                stock_section += f"Data period: {period.get('start', 'unknown')} to {period.get('end', 'unknown')}\n"
            
            # Include any other top-level information that might be useful
            for key, value in stock_data.items():
                if key not in ['ticker', 'search_period', 'sources', 'summary'] and isinstance(value, (str, int, float)):
                    stock_section += f"{key}: {value}\n"
        
        # Create the main prompt
        prompt = f"""You are a financial analyst specialized in stock market analysis. 
I'll provide you with recent news articles and data about {ticker} stock.

Your task is to:
1. Analyze the sentiment of these news articles (bullish, bearish, or neutral)
2. Identify key themes and trends in the news
3. Provide insights on how these news items might impact the stock
4. Summarize the overall market sentiment towards {ticker}
5. If possible, highlight any potential trading opportunities or risks

{news_section}

{stock_section}

Please structure your analysis as follows:
1. SENTIMENT ANALYSIS: Overall sentiment score and breakdown
2. KEY THEMES: Major themes and developments identified
3. POTENTIAL IMPACT: How the news might affect the stock price
4. MARKET OUTLOOK: Your assessment of {ticker}'s short-term prospects
5. NOTEWORTHY POINTS: Any significant points investors should be aware of

Keep your analysis professional, data-driven, and concise.
"""
        print(f"✅ CHECKPOINT: Prompt prepared with length {len(prompt)} characters")
        return prompt
    
    def analyze(self, prompt):
        """Send the prompt to the LLM and get analysis"""
        print(f"🔍 CHECKPOINT: Sending request to {self.model}")
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }
            ]
        }
        
        start_time = time.time()
        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(data))
            
            if response.status_code == 200:
                elapsed_time = time.time() - start_time
                print(f"✅ CHECKPOINT: Received response in {elapsed_time:.2f} seconds")
                
                result = response.json()
                generated_text = result.get('choices', [{}])[0].get('message', {}).get('content', 'No analysis generated')
                return generated_text, result
            else:
                print(f"❌ ERROR: API request failed with code {response.status_code}")
                print(f"Error details: {response.text}")
                return f"Error {response.status_code}: {response.text}", None
        except Exception as e:
            print(f"❌ ERROR: Exception during API call - {str(e)}")
            return f"Error: {str(e)}", None
    
    def save_analysis(self, ticker, analysis, full_response=None):
        """Save the analysis to a file"""
        timestamp = int(time.time())
        output_file = self.output_dir / f"{ticker}_analysis_{timestamp}.txt"
        debug_file = self.output_dir / f"{ticker}_full_response_{timestamp}.json"
        
        try:
            with open(output_file, 'w') as f:
                f.write(f"STOCK ANALYSIS FOR {ticker}\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(analysis)
            
            print(f"✅ CHECKPOINT: Analysis saved to {output_file}")
            
            # Optionally save the full API response for debugging
            if full_response:
                with open(debug_file, 'w') as f:
                    json.dump(full_response, f, indent=2)
                print(f"✅ CHECKPOINT: Full response saved to {debug_file}")
                
            return output_file
        except Exception as e:
            print(f"❌ ERROR: Failed to save analysis - {str(e)}")
            return None


def main():
    """Main function to run the stock news analyzer"""
    parser = argparse.ArgumentParser(description='Analyze stock news with Gemini model')
    parser.add_argument('news_file', help='Path to the news data JSON file')
    parser.add_argument('--ticker', help='Stock ticker symbol', default=None)
    parser.add_argument('--stock-data', help='Path to stock price data JSON file', default=None)
    parser.add_argument('--api-key', help='OpenRouter API key', 
                       default='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')
    args = parser.parse_args()
    
    # Extract ticker from filename if not provided
    ticker = args.ticker
    if not ticker:
        file_name = os.path.basename(args.news_file)
        ticker_match = file_name.split('_')[0].upper()
        ticker = ticker_match if ticker_match else "UNKNOWN"
    
    print(f"=" * 50)
    print(f"STOCK NEWS ANALYSIS FOR {ticker}")
    print(f"=" * 50)
    
    # Initialize the analyzer
    analyzer = StockNewsAnalyzer(args.api_key)
    
    # Load news data
    news_data = analyzer.load_data(args.news_file)
    if not news_data:
        return
    
    # Load stock data if provided
    stock_data = None
    if args.stock_data:
        stock_data = analyzer.load_stock_data(args.stock_data)
    else:
        # Try to extract some stock data from the news file if it has the expected structure
        try:
            with open(args.news_file, 'r') as f:
                data = json.load(f)
            if 'ticker' in data:
                # We can use the same file for stock metadata
                stock_data = {
                    'ticker': data.get('ticker'),
                    'search_period': data.get('search_period', {}),
                    'company_name': data.get('company_name')
                }
                print(f"✅ CHECKPOINT: Extracted basic stock data from the news file")
        except Exception as e:
            print(f"⚠️ WARNING: Could not extract stock data from news file - {str(e)}")
    
    # Prepare the prompt
    prompt = analyzer.prepare_prompt(news_data, stock_data, ticker)
    
    # Get analysis from LLM
    print(f"⏳ CHECKPOINT: Waiting for model response...")
    analysis, full_response = analyzer.analyze(prompt)
    
    # Save the results
    output_file = analyzer.save_analysis(ticker, analysis, full_response)
    
    # Print summary to console
    if output_file:
        print(f"=" * 50)
        print(f"Analysis complete! Results saved to: {output_file}")
        print(f"=" * 50)
        
        # Print a preview of the analysis
        print("\nANALYSIS PREVIEW:")
        preview_lines = analysis.split('\n')[:10]
        print('\n'.join(preview_lines))
        print("...\n")


if __name__ == "__main__":
    main()