import praw
import pandas as pd
import datetime
import time
import re
import json
import requests
from datetime import timezone
import argparse

class StockDataCollector:
    def __init__(self, reddit_client_id, reddit_client_secret, reddit_username, reddit_password,
                 newsapi_key=None, alpha_vantage_key=None):
        """
        Initialize the stock data collector with API credentials.
        
        Args:
            reddit_client_id (str): Reddit API client ID
            reddit_client_secret (str): Reddit API client secret
            reddit_username (str): Reddit username
            reddit_password (str): Reddit password
            newsapi_key (str, optional): News API key
            alpha_vantage_key (str, optional): Alpha Vantage API key
        """
        # Initialize Reddit connection
        self.reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password,
            user_agent=f"script:stock-data-collector:v1.0 (by /u/{reddit_username})"
        )
        
        # Store API keys
        self.newsapi_key = newsapi_key
        self.alpha_vantage_key = alpha_vantage_key
        
        # Define subreddits to search
        self.subreddits = [
            "wallstreetbets", 
            "stocks", 
            "investing", 
            "StockMarket", 
            "options"
        ]
        
        print(f"Connected to Reddit as: {self.reddit.user.me()}")
    
    def collect_reddit_mentions(self, ticker, days=7, max_posts=100):
        """
        Collect mentions of a specific stock ticker from Reddit.
        
        Args:
            ticker (str): Stock ticker symbol (e.g., AAPL, TSLA)
            days (int): Number of days to look back
            max_posts (int): Maximum number of posts to retrieve per subreddit
            
        Returns:
            dict: Collected Reddit data with submissions and comments
        """
        # Standardize ticker format
        ticker = ticker.upper()
        
        # Calculate time range
        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - datetime.timedelta(days=days)
        
        # Convert to Unix timestamps
        start_timestamp = start_time.timestamp()
        
        # Pattern to match the ticker symbol (whole word only)
        ticker_pattern = r'\b' + re.escape(ticker) + r'\b'
        
        # Results container
        results = {
            "ticker": ticker,
            "search_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "submissions": [],
            "comments": []
        }
        
        # Search each subreddit
        for subreddit_name in self.subreddits:
            print(f"Searching r/{subreddit_name} for {ticker} mentions...")
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Track posts to avoid duplicates
            processed_submissions = set()
            
            try:
                # Search submission titles and content
                for submission in subreddit.new(limit=max_posts):
                    # Skip if outside our time range
                    if submission.created_utc < start_timestamp:
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
                        
                        results["submissions"].append(submission_data)
                        processed_submissions.add(submission.id)
                        
                        print(f"Found submission mentioning {ticker}: {submission.title}")
                    
                    # Avoid hitting rate limits
                    time.sleep(0.1)
                
                # Also search for the ticker in comments
                for comment in subreddit.comments(limit=max_posts):
                    # Skip if outside our time range
                    if comment.created_utc < start_timestamp:
                        continue
                    
                    # Check if the ticker is mentioned in the comment
                    if re.search(ticker_pattern, comment.body):
                        comment_data = {
                            "id": comment.id,
                            "subreddit": subreddit_name,
                            "submission_id": comment.submission.id,
                            "submission_title": comment.submission.title,
                            "author": comment.author.name if comment.author else "[deleted]",
                            "body": comment.body,
                            "created_utc": comment.created_utc,
                            "created_datetime": datetime.datetime.fromtimestamp(comment.created_utc).isoformat(),
                            "score": comment.score,
                            "permalink": f"https://www.reddit.com{comment.permalink}"
                        }
                        
                        results["comments"].append(comment_data)
                        
                        # If this comment's submission isn't already processed, add it
                        if comment.submission.id not in processed_submissions:
                            submission = comment.submission
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
                            
                            results["submissions"].append(submission_data)
                            processed_submissions.add(submission.id)
                        
                        print(f"Found comment mentioning {ticker} in post: {comment.submission.title}")
                    
                    # Avoid hitting rate limits
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Error searching r/{subreddit_name}: {e}")
                continue
        
        # Summary
        print(f"\nReddit Summary for {ticker}:")
        print(f"Found {len(results['submissions'])} submissions")
        print(f"Found {len(results['comments'])} comments")
        
        return results
    
    def collect_newsapi_articles(self, ticker, company_name=None, days=7):
        """
        Collect news articles about a stock using News API.
        
        Args:
            ticker (str): Stock ticker symbol
            company_name (str, optional): Company name for better search results
            days (int): Number of days to look back
            
        Returns:
            dict: Collected news data
        """
        if not self.newsapi_key:
            print("News API key not provided. Skipping news collection.")
            return {"articles": []}
        
        # Standardize ticker format
        ticker = ticker.upper()
        
        # Calculate time range
        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - datetime.timedelta(days=days)
        
        # Format dates for News API (YYYY-MM-DD)
        from_date = start_time.strftime('%Y-%m-%d')
        to_date = end_time.strftime('%Y-%m-%d')
        
        # Construct search query
        query = ticker
        if company_name:
            query = f"{ticker} OR {company_name}"
        
        # News API endpoint
        url = 'https://newsapi.org/v2/everything'
        
        # Parameters
        params = {
            'q': query,
            'from': from_date,
            'to': to_date,
            'language': 'en',
            'sortBy': 'publishedAt',
            'apiKey': self.newsapi_key
        }
        
        print(f"Fetching news articles for {ticker} from {from_date} to {to_date}...")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            data = response.json()
            
            if data['status'] != 'ok':
                print(f"News API error: {data.get('message', 'Unknown error')}")
                return {"articles": []}
            
            # Process articles
            articles = []
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
            
            print(f"Found {len(articles)} news articles for {ticker}")
            
            return {
                "ticker": ticker,
                "search_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "articles": articles
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news articles: {e}")
            return {"articles": []}
    
    def collect_alpha_vantage_news(self, ticker, days=7):
        """
        Collect news articles about a stock using Alpha Vantage.
        
        Args:
            ticker (str): Stock ticker symbol
            days (int): Number of days to look back
            
        Returns:
            dict: Collected news data
        """
        if not self.alpha_vantage_key:
            print("Alpha Vantage API key not provided. Skipping news collection.")
            return {"articles": []}
        
        # Standardize ticker format
        ticker = ticker.upper()
        
        # Alpha Vantage News API endpoint
        url = 'https://www.alphavantage.co/query'
        
        # Parameters
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker,
            'apikey': self.alpha_vantage_key,
            'limit': 50  # Maximum allowed by Alpha Vantage
        }
        
        print(f"Fetching news articles for {ticker} from Alpha Vantage...")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            data = response.json()
            
            # Calculate time range for filtering
            end_time = datetime.datetime.now(timezone.utc)
            start_time = end_time - datetime.timedelta(days=days)
            start_timestamp = start_time.timestamp()
            
            # Alpha Vantage returns a feed of articles
            if 'feed' not in data:
                print(f"Alpha Vantage API error: {data.get('Note', 'Unknown error')}")
                return {"articles": []}
            
            # Process articles
            articles = []
            
            for article in data['feed']:
                # Parse time string to datetime
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
                    "summary": article['summary'],
                    "url": article['url'],
                    "published_at": time_published.isoformat(),
                    "sentiment_score": article.get('overall_sentiment_score'),
                    "sentiment_label": article.get('overall_sentiment_label')
                }
                articles.append(article_data)
            
            print(f"Found {len(articles)} news articles for {ticker} from Alpha Vantage")
            
            return {
                "ticker": ticker,
                "search_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "articles": articles
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Alpha Vantage news: {e}")
            return {"articles": []}
    
    def collect_all_data(self, ticker, company_name=None, days=7, max_posts=100, save_to_file=True):
        """
        Collect all available data (Reddit + News) for a stock ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            company_name (str, optional): Company name for better news search
            days (int): Number of days to look back
            max_posts (int): Maximum Reddit posts per subreddit
            save_to_file (bool): Whether to save results to files
            
        Returns:
            dict: Consolidated data from all sources
        """
        # Collect Reddit data
        reddit_data = self.collect_reddit_mentions(ticker, days, max_posts)
        
        # Collect news data from available sources
        news_data = {"articles": []}
        
        if self.newsapi_key:
            newsapi_data = self.collect_newsapi_articles(ticker, company_name, days)
            news_data["articles"].extend(newsapi_data["articles"])
        
        if self.alpha_vantage_key:
            alphavantage_data = self.collect_alpha_vantage_news(ticker, days)
            news_data["articles"].extend(alphavantage_data["articles"])
        
        # Combine all data
        consolidated_data = {
            "ticker": ticker,
            "company_name": company_name,
            "search_period": reddit_data["search_period"],
            "sources": {
                "reddit": {
                    "submissions": reddit_data["submissions"],
                    "comments": reddit_data["comments"]
                },
                "news": {
                    "articles": news_data["articles"]
                }
            },
            "summary": {
                "reddit_submissions_count": len(reddit_data["submissions"]),
                "reddit_comments_count": len(reddit_data["comments"]),
                "news_articles_count": len(news_data["articles"]),
                "total_content_count": len(reddit_data["submissions"]) + len(reddit_data["comments"]) + len(news_data["articles"])
            }
        }
        
        # Save to file if requested
        if save_to_file:
            timestamp = int(time.time())
            json_filename = f"{ticker.lower()}_stock_data_{timestamp}.json"
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(consolidated_data, f, ensure_ascii=False, indent=4)
            
            print(f"Saved consolidated data to {json_filename}")
            
            # Also save separate CSVs for easier analysis
            if reddit_data["submissions"]:
                submissions_df = pd.DataFrame(reddit_data["submissions"])
                submissions_csv = f"{ticker.lower()}_reddit_submissions_{timestamp}.csv"
                submissions_df.to_csv(submissions_csv, index=False, encoding='utf-8')
                print(f"Saved Reddit submissions to {submissions_csv}")
            
            if reddit_data["comments"]:
                comments_df = pd.DataFrame(reddit_data["comments"])
                comments_csv = f"{ticker.lower()}_reddit_comments_{timestamp}.csv"
                comments_df.to_csv(comments_csv, index=False, encoding='utf-8')
                print(f"Saved Reddit comments to {comments_csv}")
            
            if news_data["articles"]:
                articles_df = pd.DataFrame(news_data["articles"])
                articles_csv = f"{ticker.lower()}_news_articles_{timestamp}.csv"
                articles_df.to_csv(articles_csv, index=False, encoding='utf-8')
                print(f"Saved news articles to {articles_csv}")
        
        return consolidated_data

def main():
    parser = argparse.ArgumentParser(description='Collect stock data from Reddit and news sources')
    parser.add_argument('ticker', type=str, help='Stock ticker symbol (e.g., AAPL, TSLA)')
    parser.add_argument('--company-name', type=str, help='Company name for better news search results')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--max-posts', type=int, default=100, help='Maximum Reddit posts per subreddit')
    parser.add_argument('--no-save', action='store_true', help='Do not save results to files')
    parser.add_argument('--newsapi-key', type=str, help='News API key')
    parser.add_argument('--alphavantage-key', type=str, help='Alpha Vantage API key')
    args = parser.parse_args()
    
    # Your Reddit API credentials
    REDDIT_CLIENT_ID = "3GrrAP6Z7iOSvgQY3oMH1w"
    REDDIT_CLIENT_SECRET = "YQya7ob0iBJDCx10S4sfb6Jr_vK4LQ"
    REDDIT_USERNAME = "yugs111"
    REDDIT_PASSWORD = "hotpizza"
    
    # Initialize collector
    collector = StockDataCollector(
        REDDIT_CLIENT_ID,
        REDDIT_CLIENT_SECRET,
        REDDIT_USERNAME,
        REDDIT_PASSWORD,
        newsapi_key="9314b4e1b6a14929a813544e3ec27586",
        alpha_vantage_key= "JCSUIVFWE2F6FXSB"
    )
    
    # Collect all data
    collector.collect_all_data(
        args.ticker,
        company_name=args.company_name,
        days=args.days,
        max_posts=args.max_posts,
        save_to_file=not args.no_save
    )

if __name__ == "__main__":
    main()