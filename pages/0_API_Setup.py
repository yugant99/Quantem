import streamlit as st
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="Quantem - API Setup",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply the same custom CSS as your home page, but fix the privacy notice
st.markdown("""
<style>
/* Overall background */
.stApp {
    background-color: #0c1929 !important;
    background-image: url("ChatGPT Image Apr 5, 2025, 03_30_12 PM.png");
    background-size: cover;
    background-position: center;
    background-blend-mode: overlay;
}

/* Make containers transparent */
.main .block-container {
    background-color: transparent !important;
}

/* Text colors */
p, h1, h2, h3, h4, h5, h6, span, li, td, th {
    color: white !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header {
    visibility: hidden;
}

/* Button styling */
div.stButton > button {
    background-color: #FFD700 !important;
    color: #0c1929 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    border-radius: 6px !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

div.stButton > button:hover {
    background-color: #ffeb3b !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255, 215, 0, 0.3) !important;
}

/* Center button */
.center-button {
    display: flex;
    justify-content: center;
    margin-top: 40px;
}

/* Card styling for API inputs */
.api-card {
    background-color: rgba(255, 255, 255, 0.07) !important;
    border-radius: 8px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Warning notice - IMPROVED LEGIBILITY */
.warning-notice {
    background-color: rgba(255, 193, 7, 0.2) !important;
    border-left: 4px solid #ffc107 !important;
    padding: 15px !important;
    margin: 20px 0 !important;
    border-radius: 4px !important;
    color: #ffffff !important;
    font-weight: 500 !important;
}

.warning-notice strong {
    color: #ffd700 !important;
}

/* Demo mode banner */
.demo-banner {
    background-color: rgba(0, 150, 255, 0.15) !important;
    border-left: 4px solid #0096ff !important;
    padding: 15px !important;
    margin: 20px 0 !important;
    border-radius: 4px !important;
    color: #ffffff !important;
    font-weight: 500 !important;
}

.demo-banner strong {
    color: #0096ff !important;
}
</style>
""", unsafe_allow_html=True)

# Load existing environment variables - but ONLY for development purposes
# In production, this should be disabled or used carefully
dev_mode = False  # Set this to True ONLY during development
if dev_mode:
    load_dotenv()

# Page title and description
st.markdown("<h1 style='text-align: center; font-size: 48px; margin-bottom: 20px;'>API Setup</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; max-width: 900px; margin: 0 auto; margin-bottom: 20px;'>Configure your API keys to access all platform features</p>", unsafe_allow_html=True)

st.markdown("<div class='warning-notice'><strong>Privacy Notice:</strong> Your API keys and credentials are stored only in your browser's session. When you close the browser, these credentials will be cleared and you'll need to enter them again. We never save or transmit your credentials to any server.</div>", unsafe_allow_html=True)

# Create columns for better layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='api-card'>", unsafe_allow_html=True)
    st.subheader("Financial Data APIs")
    
    # Financial Modeling Prep
    st.markdown("#### Financial Modeling Prep API")
    st.markdown("Used for stock price data, company information, and financial metrics. Essential for the platform's core functionality.")
    st.markdown("Get your free API key: [Financial Modeling Prep](https://financialmodelingprep.com/developer/docs/)")
    
    # Only use environment variables for defaults in development mode
    default_fmp = os.getenv("FMP_API_KEY", "") if dev_mode else ""
    fmp_key = st.text_input("FMP API Key", 
                            value=default_fmp, 
                            type="password",
                            help="Required for stock price data")
    
    # Alpha Vantage
    st.markdown("#### Alpha Vantage API")
    st.markdown("Provides additional financial data, intraday prices, and technical indicators.")
    st.markdown("Get your free API key: [Alpha Vantage](https://www.alphavantage.co/support/#api-key)")
    
    # Only use environment variables for defaults in development mode
    default_alpha = os.getenv("ALPHA_VANTAGE_KEY", "") if dev_mode else ""
    alpha_key = st.text_input("Alpha Vantage API Key", 
                             value=default_alpha, 
                             type="password",
                             help="For additional financial data sources")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='api-card'>", unsafe_allow_html=True)
    st.subheader("Sentiment Analysis APIs")
    
    # News API
    st.markdown("#### News API")
    st.markdown("Used to gather news articles for sentiment analysis related to stocks.")
    st.markdown("Get your free API key: [News API](https://newsapi.org/register)")
    
    # Only use environment variables for defaults in development mode
    default_news = os.getenv("NEWSAPI_KEY", "") if dev_mode else ""
    news_key = st.text_input("News API Key", 
                            value=default_news, 
                            type="password",
                            help="For news sentiment analysis")
    
    # Reddit API (multiple fields)
    st.markdown("#### Reddit API")
    st.markdown("Used to gather social media sentiment about stocks. Requires a Reddit account and API credentials.")
    st.markdown("Get your Reddit API credentials: [Reddit API](https://www.reddit.com/prefs/apps)")
    
    # Only use environment variables for defaults in development mode
    default_reddit_id = os.getenv("REDDIT_CLIENT_ID", "") if dev_mode else ""
    default_reddit_secret = os.getenv("REDDIT_CLIENT_SECRET", "") if dev_mode else ""
    default_reddit_user = os.getenv("REDDIT_USERNAME", "") if dev_mode else ""
    default_reddit_pass = os.getenv("REDDIT_PASSWORD", "") if dev_mode else ""
    
    reddit_client_id = st.text_input("Reddit Client ID", 
                                    value=default_reddit_id, 
                                    help="Found in your Reddit Developer App")
    
    reddit_client_secret = st.text_input("Reddit Client Secret", 
                                        value=default_reddit_secret, 
                                        type="password",
                                        help="Found in your Reddit Developer App")
    
    reddit_username = st.text_input("Reddit Username", 
                                   value=default_reddit_user,
                                   help="Your Reddit account username")
    
    reddit_password = st.text_input("Reddit Password", 
                                   value=default_reddit_pass, 
                                   type="password",
                                   help="Your Reddit account password")
    st.markdown("</div>", unsafe_allow_html=True)

# AI API
st.markdown("<div class='api-card'>", unsafe_allow_html=True)
st.subheader("AI Analysis API")
st.markdown("#### OpenRouter API")
st.markdown("Powers the AI-driven analysis features, including sentiment interpretation and stock comparisons.")
st.markdown("Get your free API key: [OpenRouter](https://openrouter.ai/)")

# Only use environment variables for defaults in development mode
default_openrouter = os.getenv("OPENROUTER_KEY", "") if dev_mode else ""
openrouter_key = st.text_input("OpenRouter API Key", 
                              value=default_openrouter, 
                              type="password",
                              help="For AI-powered analysis features")
st.markdown("</div>", unsafe_allow_html=True)

# Store API keys in session state
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {}

# Update session state with current values
if st.button("Save API Keys and Continue to Dashboard", use_container_width=True):
    # Store all keys in session state
    st.session_state.api_keys = {
        "FMP_API_KEY": fmp_key,
        "ALPHA_VANTAGE_KEY": alpha_key,
        "NEWSAPI_KEY": news_key,
        "REDDIT_CLIENT_ID": reddit_client_id,
        "REDDIT_CLIENT_SECRET": reddit_client_secret,
        "REDDIT_USERNAME": reddit_username,
        "REDDIT_PASSWORD": reddit_password,
        "OPENROUTER_KEY": openrouter_key
    }
    
    # Check if essential keys are provided
    if fmp_key:
        st.session_state.demo_mode = False
    if not fmp_key:
        st.error("Financial Modeling Prep API key is required to proceed.")
    else:
        # Redirect to dashboard
        st.switch_page("pages/1_Dashboard.py")

# Demo mode section with more info
st.markdown("<div class='demo-banner'><strong>Demo Mode:</strong> Try the platform with pre-cached data without entering API keys. Some features will have limited functionality.</div>", unsafe_allow_html=True)

# Demo mode info expander
with st.expander("What works in Demo Mode?"):
    st.markdown("""
    ### Demo Mode Features:
    
    ✅ **Technical Analysis**: View pre-cached stock data and apply indicators and strategies  
    ✅ **Basic Forecasting**: View sample forecasts for selected stocks  
    ✅ **Sample Sentiment Analysis**: View pre-generated sentiment reports  
    ✅ **Risk Analysis**: View simulated risk metrics  
    ✅ **Comparative Analysis**: Compare selected demo stocks  
    
    ### Available Demo Stocks:
    - AAPL (Apple)
    - MSFT (Microsoft)
    - GOOG (Google)
    - AMZN (Amazon)
    - TSLA (Tesla)
    - META (Meta/Facebook)
    - NVDA (NVIDIA)
    - JPM (JPMorgan Chase)
    - V (Visa)
    - WMT (Walmart)
    
    Demo mode uses cached data from recent history. For real-time data and full functionality, please enter your API keys.
    """)

# Skip option with sample data
st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
if st.button("Skip with Demo Data", key="skip_demo", use_container_width=False):
    # Set demo mode flag
    st.session_state.demo_mode = True
    
    # Set demo API keys (these are non-functional placeholders)
    st.session_state.api_keys = {
        "FMP_API_KEY": "demo_mode_placeholder_key",
        "ALPHA_VANTAGE_KEY": "demo_mode_placeholder_key",
        "NEWSAPI_KEY": "demo_mode_placeholder_key",
        "REDDIT_CLIENT_ID": "demo_mode_placeholder_key",
        "REDDIT_CLIENT_SECRET": "demo_mode_placeholder_key",
        "REDDIT_USERNAME": "demo_user",
        "REDDIT_PASSWORD": "demo_password",
        "OPENROUTER_KEY": "demo_mode_placeholder_key"
    }
    
    st.switch_page("pages/1_Dashboard.py")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<p style='text-align: center; font-size: 14px; color: rgba(255,255,255,0.8) !important; margin-top: 20px;'>Note: Demo mode uses cached data with limited functionality.</p>", unsafe_allow_html=True)