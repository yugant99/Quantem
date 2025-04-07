import os
import json
import time
import datetime
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import timezone, timedelta
import praw
import re
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

# Replace direct env variable references with get_api_key calls
REDDIT_CLIENT_ID = get_api_key("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = get_api_key("REDDIT_CLIENT_SECRET") 
REDDIT_USERNAME = get_api_key("REDDIT_USERNAME")
REDDIT_PASSWORD = get_api_key("REDDIT_PASSWORD")
NEWSAPI_KEY = get_api_key("NEWSAPI_KEY")
ALPHA_VANTAGE_KEY = get_api_key("ALPHA_VANTAGE_KEY")
OPENROUTER_KEY = get_api_key("OPENROUTER_KEY")
GEMINI_MODEL = "google/gemini-2.5-pro-exp-03-25:free"

# Create cache directory
os.makedirs("cache/sentiment", exist_ok=True)

def fetch_reddit_data(ticker, days=7, max_posts=100):
    """
    Fetch Reddit posts mentioning a specific stock ticker
    
    Args:
        ticker (str): Stock ticker symbol
        days (int): Number of days to look back
        max_posts (int): Maximum number of posts to retrieve per subreddit
        
    Returns:
        list: List of Reddit submissions
    """
    ticker = ticker.upper()
    
    # Calculate time range
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    # Convert to Unix timestamps
    start_timestamp = start_time.timestamp()
    
    # Pattern to match the ticker symbol (whole word only)
    ticker_pattern = r'\b' + re.escape(ticker) + r'\b'
    
    # Initialize Reddit client
    try:
        reddit = praw.Reddit(
            client_id=get_api_key("REDDIT_CLIENT_ID"),
            client_secret=get_api_key("REDDIT_CLIENT_SECRET"),
            username=get_api_key("REDDIT_USERNAME"),
            password=get_api_key("REDDIT_PASSWORD"),
            user_agent=f"script:stock-dashboard:v1.0 (by /u/{get_api_key('REDDIT_USERNAME')})"
        )
    except Exception as e:
        st.error(f"Error connecting to Reddit: {str(e)}")
        return []
    
    # Subreddits to search
    subreddits = ["wallstreetbets", "stocks", "investing", "StockMarket", "options"]
    
    # Results container
    submissions = []
    processed_ids = set()
    
    # Search each subreddit
    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            
            # Search submission titles and content
            for submission in subreddit.new(limit=max_posts):
                # Skip if outside our time range or already processed
                if submission.created_utc < start_timestamp or submission.id in processed_ids:
                    continue
                
                # Check if the ticker is mentioned in title or selftext
                title_match = re.search(ticker_pattern, submission.title)
                selftext_match = False
                
                # Some submissions don't have selftext
                if hasattr(submission, 'selftext'):
                    selftext_match = re.search(ticker_pattern, submission.selftext)
                
                if title_match or selftext_match:
                    # Add to our results
                    submission_data = {
                        "id": submission.id,
                        "subreddit": subreddit_name,
                        "title": submission.title,
                        "author": submission.author.name if submission.author else "[deleted]",
                        "created_utc": submission.created_utc,
                        "created_datetime": datetime.datetime.fromtimestamp(submission.created_utc).isoformat(),
                        "upvote_ratio": submission.upvote_ratio,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "url": submission.url,
                        "permalink": f"https://www.reddit.com{submission.permalink}"
                    }
                    
                    # Add selftext if available
                    if hasattr(submission, 'selftext') and submission.selftext:
                        submission_data["selftext"] = submission.selftext
                    
                    submissions.append(submission_data)
                    processed_ids.add(submission.id)
                
                # Avoid hitting rate limits
                time.sleep(0.1)
                
        except Exception as e:
            st.warning(f"Error searching r/{subreddit_name}: {str(e)}")
            continue
    
    return submissions

def fetch_news_data(ticker,days =7):
    ticker = ticker.upper()
    articles = []
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    from_date = start_time.strftime('%Y-%m-%d')
    to_date = end_time.strftime('%Y-%m-%d')
    
    # Updated to use get_api_key
    newsapi_key = get_api_key("NEWSAPI_KEY")
    if newsapi_key:
        try:
            # News API endpoint
            url = 'https://newsapi.org/v2/everything'
            
            # Parameters
            params = {
                'q': ticker,
                'from': from_date,
                'to': to_date,
                'language': 'en',
                'sortBy': 'publishedAt',
                'apiKey': newsapi_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'ok':
                for article in data['articles']:
                    article_data = {
                        "source": article['source']['name'],
                        "author": article['author'] if article['author'] else "Unknown",
                        "title": article['title'],
                        "description": article['description'],
                        "url": article['url'],
                        "published_at": article['publishedAt'],
                        "content": article['content'] if article['content'] else article['description']
                    }
                    articles.append(article_data)
        except Exception as e:
            st.warning(f"Error fetching news from News API: {str(e)}")
    
    # Updated to use get_api_key
    alpha_vantage_key = get_api_key("ALPHA_VANTAGE_KEY")
    if alpha_vantage_key:
        try:
            # Alpha Vantage News API endpoint
            url = 'https://www.alphavantage.co/query'
            
            # Parameters
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': ticker,
                'apikey': alpha_vantage_key,
                'limit': 50  # Maximum allowed by Alpha Vantage
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate time range for filtering
            start_timestamp = start_time.timestamp()
            
            # Alpha Vantage returns a feed of articles
            if 'feed' in data:
                for article in data['feed']:
                    # Parse time string to datetime
                    try:
                        time_published = datetime.datetime.strptime(
                            article['time_published'], 
                            '%Y%m%dT%H%M%S'
                        ).replace(tzinfo=timezone.utc)
                        
                        # Skip if outside our time range
                        if time_published.timestamp() < start_timestamp:
                            continue
                        
                        article_data = {
                            "source": article['source'],
                            "author": article.get('authors', ['Unknown'])[0] if article.get('authors') else "Unknown",
                            "title": article['title'],
                            "description": article.get('summary', ''),
                            "url": article['url'],
                            "published_at": time_published.isoformat(),
                            "content": article.get('summary', ''),
                            "sentiment_score": article.get('overall_sentiment_score'),
                            "sentiment_label": article.get('overall_sentiment_label')
                        }
                        articles.append(article_data)
                    except Exception as e:
                        continue  # Skip this article if there's an error
            else:
                st.warning(f"Alpha Vantage API returned unexpected data format: {data.get('Note', '')}")
        except Exception as e:
            st.warning(f"Error fetching news from Alpha Vantage: {str(e)}")
    
    return articles    

def combine_sentiment_data(ticker, reddit_data, news_data):
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    if reddit_data and len(reddit_data) > 0:
        # Try to extract the actual time range from the data
        submission_dates = [datetime.datetime.fromisoformat(s["created_datetime"]) for s in reddit_data if "created_datetime" in s]
        if submission_dates:
            min_date = min(submission_dates)
            if min_date.tzinfo is None:
                min_date = min_date.replace(tzinfo=timezone.utc)
            if min_date < start_time:
                start_time = min_date
    
    return {
        "ticker": ticker,
        "company_name": None,  # Could be fetched from a financial API if needed
        "search_period": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "sources": {
            "reddit": {
                "submissions": reddit_data,
                "comments": []  # Not collecting comments for simplicity
            },
            "news": {
                "articles": news_data
            }
        },
        "summary": {
            "reddit_submissions_count": len(reddit_data),
            "reddit_comments_count": 0,
            "news_articles_count": len(news_data),
            "total_content_count": len(reddit_data) + len(news_data)
        }
    }

def fetch_sentiment_data(ticker, days=7, use_cache=True):
    ticker = ticker.upper()
    
    # Check if in demo mode
    demo_mode = st.session_state.get("demo_mode", False)
    
    # Use appropriate cache directory based on mode
    cache_dir = "demo_cache/sentiment" if demo_mode else "cache/sentiment"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Check cache first if enabled
    cache_file = f"{cache_dir}/{ticker}_sentiment_{days}d.json"
    
    if use_cache and os.path.exists(cache_file):
        # Check if cache is recent enough (less than 6 hours old)
        if time.time() - os.path.getmtime(cache_file) < 21600:  # 6 hours in seconds
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    mode_text = "demo " if demo_mode else ""
                    st.success(f"Using cached {mode_text}sentiment data for {ticker} (less than 6 hours old)")
                    return json.load(f)
            except Exception as e:
                st.warning(f"Error reading cached sentiment data: {str(e)}")
    
    # If demo mode and cache not available, don't try to fetch new data
    if demo_mode and not os.path.exists(cache_file):
        return None
    
    # If cache is not available or not recent, fetch new data
    with st.spinner(f"Fetching sentiment data for {ticker}..."):
        # Fetch Reddit data
        reddit_data = fetch_reddit_data(ticker, days)
        
        # Fetch news data
        news_data = fetch_news_data(ticker, days)
        
        # Combine data
        data = combine_sentiment_data(ticker, reddit_data, news_data)
        
        # Save to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return data

def analyze_sentiment(data, api_key=None, model=GEMINI_MODEL):
    """
    Analyze sentiment data using Gemini via OpenRouter API
    
    Args:
        data (dict): Sentiment data to analyze
        api_key (str): OpenRouter API key
        model (str): Model ID to use
        
    Returns:
        str: Analysis results
    """
    # Check if in demo mode
    demo_mode = st.session_state.get("demo_mode", False)
    
    # Updated to use get_api_key if api_key not provided
    if api_key is None:
        api_key = get_api_key("OPENROUTER_KEY")
        
    if not data:
        print("DEBUG: No data provided to analyze_sentiment")
        return "No data available for analysis."
    
    ticker = data.get("ticker", "UNKNOWN")
    print(f"DEBUG: Starting sentiment analysis for {ticker}")
    
    # Use appropriate cache directory based on mode
    cache_dir = "demo_cache/sentiment" if demo_mode else "cache/sentiment"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{cache_dir}/{ticker}_analysis.txt"
    
    # Check if we have cached analysis first (for demo mode)
    if demo_mode and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                print(f"DEBUG: Using cached demo analysis for {ticker}")
                return f.read()
        except Exception as e:
            print(f"DEBUG: Error reading cached analysis: {str(e)}")
    
    # Create a prompt for the analysis
    prompt = create_analysis_prompt(data)
    print(f"DEBUG: Prompt created, length: {len(prompt)} characters")
    print(f"DEBUG: First 200 chars of prompt: {prompt[:200]}")
    
    # Don't make API calls in demo mode if we don't have cached data
    if demo_mode and not os.path.exists(cache_file):
        return f"No demo analysis available for {ticker}. In production mode, a real-time analysis would be generated here."
    
    # Call the API
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://stock-analyzer.app',
        'X-Title': 'Stock Analysis Dashboard'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    print(f"DEBUG: Preparing to call OpenRouter API with model: {model}")
    print(f"DEBUG: Headers: {headers}")
    print(f"DEBUG: API Key (first 10 chars): {api_key[:10]}...")
    
    with st.spinner(f"Analyzing sentiment for {ticker}..."):
        try:
            print(f"DEBUG: Sending POST request to {url}")
            response = requests.post(url, headers=headers, json=payload)
            print(f"DEBUG: Received response with status code: {response.status_code}")
            
            # Print response details for debugging
            print(f"DEBUG: Response headers: {response.headers}")
            print(f"DEBUG: Response content preview: {response.text[:200]}")
            
            try:
                response.raise_for_status()  # Raise for status codes >= 400
            except requests.exceptions.HTTPError as e:
                print(f"DEBUG: HTTP error occurred: {e}")
                print(f"DEBUG: Response content: {response.text}")
                return f"Error analyzing sentiment: {str(e)}"
            
            try:
                result = response.json()
                print(f"DEBUG: Successfully parsed JSON response")
                
                # Print token usage if available
                usage = result.get('usage', {})
                if usage:
                    print(f"DEBUG: Token usage - Prompt: {usage.get('prompt_tokens', 'N/A')}, Completion: {usage.get('completion_tokens', 'N/A')}, Total: {usage.get('total_tokens', 'N/A')}")
                
                analysis = result.get('choices', [{}])[0].get('message', {}).get('content', 'No analysis generated')
                print(f"DEBUG: Analysis content length: {len(analysis)}")
                print(f"DEBUG: Analysis preview: {analysis[:200]}")
                
                # Cache the analysis
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(analysis)
                print(f"DEBUG: Analysis cached to {cache_file}")
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error: {e}")
                print(f"DEBUG: Raw response: {response.text}")
                return f"Error parsing response: {str(e)}"
            
        except Exception as e:
            print(f"DEBUG: Unexpected error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error analyzing sentiment: {str(e)}"

def create_analysis_prompt(data):
    """
    Create a prompt for sentiment analysis
    
    Args:
        data (dict): Sentiment data
        
    Returns:
        str: Formatted prompt
    """
    ticker = data.get("ticker", "UNKNOWN")
    
    # Extract recent news and reddit data (limit to avoid token issues)
    news_data = data.get("sources", {}).get("news", {}).get("articles", [])
    reddit_data = data.get("sources", {}).get("reddit", {}).get("submissions", [])
    
    # Limit to fewer items to reduce token count - REDUCED LIMITS
    recent_news = news_data[:10] if len(news_data) > 10 else news_data
    recent_reddit = reddit_data[:5] if len(reddit_data) > 5 else reddit_data
    
    # Format news section - SIMPLIFIED
    news_section = "\n\n### NEWS ARTICLES:\n\n"
    for i, item in enumerate(recent_news):
        published_date = item.get("published_at", "unknown").split("T")[0]
        news_section += f"{i+1}. [{published_date}] {item.get('title', 'No title')}\n"
        news_section += f"   Source: {item.get('source', 'Unknown')}\n"
        
        # Include sentiment if available
        sentiment_score = item.get("sentiment_score")
        sentiment_label = item.get("sentiment_label")
        if sentiment_score is not None and sentiment_label:
            news_section += f"   Sentiment: {sentiment_label} ({sentiment_score:.2f})\n"
        
        # Include only a brief summary of content if available
        content = item.get("content", "")
        if content and len(content) > 10:
            # Truncate to much shorter length
            if len(content) > 150:
                content = content[:150] + "..."
            news_section += f"   Summary: {content}\n"
        news_section += "\n"
    
    # Format reddit section - SIMPLIFIED
    reddit_section = "\n\n### REDDIT DISCUSSIONS:\n\n"
    for i, item in enumerate(recent_reddit):
        created_date = item.get("created_datetime", "unknown").split("T")[0]
        reddit_section += f"{i+1}. [{created_date}] {item.get('title', 'No title')}\n"
        reddit_section += f"   Subreddit: r/{item.get('subreddit', 'Unknown')}\n"
        
        # Skip selftext completely to save tokens
        reddit_section += "\n"
    
    # Create the main prompt - SIMPLIFIED
    prompt = f"""You are a financial analyst specialized in stock market analysis. 
Analyze sentiment for {ticker} stock based on these news and social media items.

{news_section}

{reddit_section}

Please structure your analysis as follows:
1. SENTIMENT ANALYSIS: Overall sentiment score and breakdown
2. KEY THEMES: Major themes and developments identified
3. POTENTIAL IMPACT: How the news might affect the stock price
4. MARKET OUTLOOK: Your assessment of {ticker}'s short-term prospects
5. NOTEWORTHY POINTS: Any significant points investors should be aware of

Keep your analysis professional, data-driven, and concise.
"""
    return prompt

def calculate_sentiment_metrics(data):
    """
    Calculate sentiment metrics from the data
    
    Args:
        data (dict): Sentiment data
        
    Returns:
        dict: Sentiment metrics
    """
    if not data or not isinstance(data, dict):
        return {
            "avg_sentiment": 0.5,
            "sentiment_counts": {"Neutral": 1},
            "sentiment_trend": [0.5] * 7,
            "dates": [(datetime.datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        }
    
    # Extract news articles
    articles = data.get("sources", {}).get("news", {}).get("articles", [])
    
    # Default values in case of no data
    if not articles:
        return {
            "avg_sentiment": 0.5,
            "sentiment_counts": {"Neutral": 1},
            "sentiment_trend": [0.5] * 7,
            "dates": [(datetime.datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        }
    
    # Calculate average sentiment
    sentiments = [article.get("sentiment_score", 0.5) for article in articles if "sentiment_score" in article]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.5
    
    # Count sentiment labels
    sentiment_counts = {}
    for article in articles:
        label = article.get("sentiment_label", "Neutral")
        sentiment_counts[label] = sentiment_counts.get(label, 0) + 1
    
    # Calculate sentiment trend (last 7 days)
    end_date = datetime.datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Group by date
    daily_sentiments = {}
    dates = []
    
    for i in range(7):
        current_date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
        dates.insert(0, current_date)  # Insert at beginning to get chronological order
        daily_sentiments[current_date] = []
    
    for article in articles:
        try:
            # Parse date from published_at
            published_str = article.get("published_at", "")
            if not published_str:
                continue
                
            # Handle different datetime formats
            if "T" in published_str:
                published_date = published_str.split("T")[0]
            else:
                published_date = published_str.split(" ")[0]
            
            # Only consider last 7 days
            if published_date in daily_sentiments:
                daily_sentiments[published_date].append(article.get("sentiment_score", 0.5))
        except Exception:
            continue
    
    # Calculate average sentiment for each day
    sentiment_trend = []
    for date in dates:
        day_sentiments = daily_sentiments.get(date, [])
        if day_sentiments:
            sentiment_trend.append(sum(day_sentiments) / len(day_sentiments))
        else:
            # If no sentiment for a day, use previous day or default
            if sentiment_trend:
                sentiment_trend.append(sentiment_trend[-1])
            else:
                sentiment_trend.append(0.5)
    
    return {
        "avg_sentiment": avg_sentiment,
        "sentiment_counts": sentiment_counts,
        "sentiment_trend": sentiment_trend,
        "dates": dates
    }

def create_sentiment_charts(metrics):
    """
    Create charts for sentiment analysis
    
    Args:
        metrics (dict): Sentiment metrics
        
    Returns:
        tuple: (trend_fig, dist_fig) Plotly figures for trend and distribution
    """
    # Create trend chart
    trend_fig = go.Figure()
    trend_fig.add_trace(
        go.Scatter(
            x=metrics["dates"],
            y=metrics["sentiment_trend"],
            mode='lines+markers',
            name='Sentiment',
            line=dict(color='royalblue', width=3),
            marker=dict(size=8)
        )
    )
    
    # Add neutral line
    trend_fig.add_shape(
        type="line",
        x0=metrics["dates"][0],
        y0=0.5,
        x1=metrics["dates"][-1],
        y1=0.5,
        line=dict(color="gray", width=1, dash="dash")
    )
    
    trend_fig.update_layout(
        title="Sentiment Trend (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        yaxis=dict(
            range=[0, 1],
            tickvals=[0, 0.25, 0.5, 0.75, 1],
            ticktext=["Very Bearish", "Bearish", "Neutral", "Bullish", "Very Bullish"]
        ),
        height=400,
        hovermode="x unified"
    )
    
    # Create distribution chart
    labels = list(metrics["sentiment_counts"].keys())
    values = list(metrics["sentiment_counts"].values())
    
    # Define colors based on sentiment labels
    colors = []
    for label in labels:
        if "Bullish" in label:
            colors.append('green')
        elif "Bearish" in label:
            colors.append('red')
        else:
            colors.append('gray')
    
    dist_fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=colors
            )
        ]
    )
    
    dist_fig.update_layout(
        title="Sentiment Distribution",
        height=400
    )
    
    return trend_fig, dist_fig

def get_sentiment_score_color(score):
    """
    Get color based on sentiment score
    
    Args:
        score (float): Sentiment score (0-1)
        
    Returns:
        str: Color in hexadecimal format
    """
    if score >= 0.7:
        return "#2E7D32"  # Green
    elif score >= 0.55:
        return "#66BB6A"  # Light green
    elif score >= 0.45:
        return "#9E9E9E"  # Gray (neutral)
    elif score >= 0.3:
        return "#EF5350"  # Light red
    else:
        return "#C62828"  # Red

def chat_with_ai(question, sentiment_data, stock_data, api_key=None, model=GEMINI_MODEL):
    """
    Chat with AI about stock sentiment and performance
    
    Args:
        question (str): User's question
        sentiment_data (dict): Sentiment data
        stock_data (dict): Stock price data
        api_key (str): OpenRouter API key
        model (str): Model to use
        
    Returns:
        str: AI response
    """
    # Updated to use get_api_key if api_key not provided
    if api_key is None:
        api_key = get_api_key("OPENROUTER_KEY")
        
    if not question or not sentiment_data:
        return "Please provide a question and ensure sentiment data is available."
    
    ticker = sentiment_data.get("ticker", "UNKNOWN")
    
    # Create context with available data
    prompt = f"""You are a financial analyst and investment advisor specialized in stock analysis. 
Answer the following question about {ticker} stock using the provided context.

QUESTION: {question}

CONTEXT:
"""
    
    # Add sentiment data summary
    prompt += f"\nSentiment Data for {ticker}:\n"
    prompt += f"- Total news articles: {sentiment_data['summary']['news_articles_count']}\n"
    prompt += f"- Total Reddit posts: {sentiment_data['summary']['reddit_submissions_count']}\n"
    
    # Add some recent news headlines
    news_data = sentiment_data.get("sources", {}).get("news", {}).get("articles", [])
    if news_data:
        prompt += "\nRecent News Headlines:\n"
        for i, article in enumerate(news_data[:5]):
            prompt += f"- {article.get('title', 'No title')}\n"
    
    # Add stock data if available
    if stock_data:
        prompt += "\nCurrent Stock Data:\n"
        for key, value in stock_data.items():
            if key in ['open', 'high', 'low', 'close', 'volume']:
                prompt += f"- {key.capitalize()}: {value}\n"
    
    # Call the API
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://stock-analyzer.app',
        'X-Title': 'Stock Analysis Dashboard'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    with st.spinner(f"Getting AI response..."):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            answer = result.get('choices', [{}])[0].get('message', {}).get('content', 'I could not generate an answer.')
            
            return answer
            
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"