# Quantem: The Future of Free Market Intelligence

![Quantem Banner](https://placehold.co/1200x300/0c1929/FFD700?text=Quantem:+Market+Intelligence+Unleashed)

Quantem is an advanced stock analysis platform that provides professional-grade market analysis tools, forecasting, and AI-powered insights without the traditional paywalls. This platform is designed for traders and investors who need comprehensive technical analysis, sentiment evaluation, risk assessment, and comparative stock analysis in one place.

## 🌟 Features

### 📈 Technical Analysis
- 20+ technical indicators including SMA, EMA, RSI, MACD, Bollinger Bands
- 6 built-in trading strategies with customizable parameters
- Interactive charts with candlestick patterns and volume analysis
- Historical backtesting of strategies with performance metrics

### 🔮 Forecasting
- Prophet-based time series forecasting with customizable horizons
- Multiple forecasting models with confidence intervals
- Trend and seasonality component analysis
- AI-generated forecast interpretations

### 📰 Sentiment Analysis
- News and social media sentiment tracking from Reddit and major news sources
- Real-time sentiment scoring for stocks
- AI-powered analysis of market perception
- Sentiment trend visualization

### ⚠️ Risk Analysis
- Comprehensive risk metrics calculation (Volatility, VaR, Sharpe ratio, etc.)
- Drawdown analysis and visualization
- Monte Carlo simulations for risk projections
- Benchmark comparison against major indices (SPY, QQQ, DIA, IWM)

### 🔍 Comparative Analysis
- Multi-stock comparison tools
- Correlation analysis between securities
- Performance benchmarking
- AI-generated comparative insights

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Pip for package installation

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yugant99/Quantiem.git
cd quantem
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run home.py
```

### API Keys Setup

Quantem uses several APIs to fetch real-time data. You can enter your API keys in the setup page or use demo mode for testing.

Supported APIs:
- Financial Modeling Prep (stock data)
- Alpha Vantage (additional financial data)
- News API (sentiment analysis)
- Reddit API (social sentiment)
- OpenRouter (AI-powered analysis)

## 🎮 Usage

1. Start with the home page to learn about the platform
2. Configure your API keys in the API Setup page
3. Navigate to the Dashboard to select stocks and perform analysis
4. Choose from the different analysis tabs based on your needs
5. Experiment with different indicators, strategies, and timeframes

## 🧪 Demo Mode

If you don't have API keys, you can use Demo Mode which provides pre-cached data of 1 month for popular stocks including:
- AAPL (Apple)
- MSFT (Microsoft)
- GOOG (Google)
- and more

## 🔍 Technical Details

### Core Components
- **Frontend**: Streamlit for interactive web interface
- **Data Processing**: Pandas, Numpy, pandas-ta for technical indicators
- **Visualization**: Plotly for interactive charts
- **Forecasting**: Prophet for time series prediction
- **AI Analysis**: Integration with OpenRouter API for advanced analysis
- **Risk Modeling**: Custom Monte Carlo simulations

### Trading Strategies
- Moving Average Crossover
- Bollinger Bands Bounce
- RSI Overbought/Oversold
- MACD Crossover
- SuperTrend
- Ichimoku Cloud

## 💡 Future Roadmap

- Portfolio optimization tools
- Options analysis module
- Customizable screeners
- Backtesting performance improvements
- Mobile application

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Streamlit for the web application framework
- pandas-ta for technical indicators
- Prophet for time series forecasting
- Plotly for interactive visualizations
- Various API providers for data services