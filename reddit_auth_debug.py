import requests
from requests.auth import HTTPBasicAuth
import os
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
load_dotenv()
# Reddit API credentials (set these as environment variables)
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
username = os.getenv("REDDIT_USERNAME")
password = os.getenv("REDDIT_PASSWORD")

# Check if credentials are provided
if not all([client_id, client_secret, username, password]):
    raise ValueError("Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, and REDDIT_PASSWORD as environment variables.")

# Get access token
auth = HTTPBasicAuth(client_id, client_secret)
data = {
    "grant_type": "password",
    "username": username,
    "password": password
}
headers = {"User-Agent": "python:wallstreetbets_counter:v1.0 (by /u/your_reddit_username)"}
response = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
access_token = response.json()["access_token"]

# Define the subreddit and time period (e.g., last 7 days)
subreddit = "wallstreetbets"
days = 7

timestamp_start = (datetime.utcnow() - timedelta(days=days)).timestamp()

# Initialize variables for fetching posts
count = 0
after = None
headers = {"Authorization": f"bearer {access_token}", "User-Agent": "python:wallstreetbets_counter:v1.0 (by /u/your_reddit_username)"}
url = f"https://oauth.reddit.com/r/{subreddit}/new"

# Fetch posts and count those within the time period
while True:
    params = {"limit": 100}
    if after:
        params["after"] = after
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    posts = data["data"]["children"]
    
    for post in posts:
        created_utc = post["data"]["created_utc"]
        if created_utc >= timestamp_start:
            count += 1
        else:
            break  # Stop if we reach a post outside the time period
    else:
        # If all posts in this batch are within the period, check for more
        if data["data"]["after"]:
            after = data["data"]["after"]
            time.sleep(1)  # Avoid hitting rate limits
            continue
    break  # Exit if we found an old post or no more posts

# Output the result
print(f"Number of posts in r/{subreddit} in the last {days} days: {count}")