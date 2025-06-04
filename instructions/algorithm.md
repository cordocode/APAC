You're absolutely right! I was being too conservative with the limitations. Let me revise this - your infrastructure can definitely support these features:

# Algorithm Chapter Roadmap (Revised)

## Project Context
Algorithms are the brain of the autotrader system. They're simple Python files that make buy/sell decisions based on market data AND external signals. Each algorithm runs independently, manages a single ticker with allocated capital, and executes trades through Alpaca. The orchestrator feeds them data every minute and executes their decisions.

## Core Philosophy
- **Simple but Powerful**: Each algorithm ~200-300 lines, but can use multiple data sources
- **Pluggable**: Drop a new .py file in /algorithms/ to add a strategy
- **State-Aware**: Algorithms track entry prices for risk management
- **Multi-Signal**: Combine technical, fundamental, and sentiment data
- **Minute Resolution**: Primary execution on minute bars, but can use any data source

## What Algorithms CAN Do

### Core Capabilities
- **Buy/Sell/Stop Decisions**: Return 'buy', 'sell', 'hold', or 'stop_loss'
- **Access Multiple Data Sources**:
  - Historical price data from stocks.db
  - News sentiment from Alpha Vantage
  - Fundamental data from various APIs
  - Economic indicators
- **Risk Management**: Built-in stop loss and take profit levels
- **Position Tracking**: Entry price, current P&L, time in position
- **Backtesting**: Run against historical data before going live

### Enhanced Data Structure
```python
def on_data(self, market_data, external_data, position_info):
    # market_data: {
    #     'current_price': 234.50,
    #     'historical_bars': DataFrame
    # }
    
    # external_data: {
    #     'news_sentiment': 0.7,  # -1 to 1
    #     'news_articles': [...],
    #     'fundamental_score': 8.2
    # }
    
    # position_info: {
    #     'shares': 45,
    #     'entry_price': 230.00,  # NEW: Track entry
    #     'current_pnl': 202.50,  # NEW: Real-time P&L
    #     'time_held': 1440,      # NEW: Minutes in position
    #     'cash_available': 1245.00
    # }
```

## Enhanced Algorithm Interface

### With Risk Management
```python
# /algorithms/news_sentiment_trader.py
class Algorithm:
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        
        # Risk parameters
        self.stop_loss_pct = 0.02  # 2% stop loss
        self.take_profit_pct = 0.05  # 5% take profit
        
        # News parameters
        self.sentiment_threshold = 0.6
        self.min_articles = 3
    
    def on_data(self, market_data, external_data, position_info):
        """Enhanced with stop loss and news sentiment"""
        
        # Check stop loss first
        if position_info['shares'] > 0:
            pnl_pct = position_info['current_pnl'] / (position_info['entry_price'] * position_info['shares'])
            
            if pnl_pct <= -self.stop_loss_pct:
                return ('stop_loss', position_info['shares'])
            
            if pnl_pct >= self.take_profit_pct:
                return ('take_profit', position_info['shares'])
        
        # News-based entry
        if position_info['shares'] == 0:
            if (external_data['news_sentiment'] > self.sentiment_threshold and 
                len(external_data['news_articles']) >= self.min_articles):
                shares_to_buy = position_info['cash_available'] // market_data['current_price']
                return ('buy', shares_to_buy)
        
        # Sentiment-based exit
        elif external_data['news_sentiment'] < -0.3:
            return ('sell', position_info['shares'])
        
        return ('hold', 0)
```

## Data Integration Architecture

### News Sentiment Pipeline
```python
# /data_providers/alpha_vantage.py
class AlphaVantageProvider:
    def get_news_sentiment(self, ticker):
        # Fetch last 50 news articles
        # Calculate aggregate sentiment
        # Return sentiment score + articles
        
# Orchestrator calls every minute:
external_data = {
    'news_sentiment': alpha_vantage.get_news_sentiment(ticker),
    'fundamental_score': alpha_vantage.get_fundamental_score(ticker)
}
```

### Backtesting Framework
```python
# /backtesting/backtest_runner.py
def backtest_algorithm(algorithm, ticker, start_date, end_date):
    """Run algorithm against historical data"""
    
    # Pull historical data from stocks.db
    historical_data = get_historical_data(ticker, start_date, end_date)
    
    # Simulate trades minute by minute
    for minute in historical_data:
        decision = algorithm.on_data(...)
        simulate_trade(decision)
    
    # Return performance metrics
    return {
        'total_return': 0.23,
        'sharpe_ratio': 1.8,
        'max_drawdown': -0.05,
        'trade_count': 47
    }
```

## Planned Algorithm Types

### 1. Technical Algorithms
- SMA Crossover (with stop loss)
- RSI Mean Reversion
- MACD Momentum
- Bollinger Band Squeeze

### 2. Sentiment Algorithms
- News Sentiment Trader
- Social Media Momentum
- Earnings Reaction Player
- FDA Approval Trader (pharma)

### 3. Fundamental Algorithms
- P/E Ratio Value Hunter
- Revenue Growth Momentum
- Analyst Upgrade Trader

### 4. Hybrid Algorithms
- Technical + Sentiment Confirmation
- Fundamental Value + Technical Entry
- Multi-Signal Consensus Trader

## Risk Management Features

### Stop Loss Types
```python
# Percentage-based
if current_price < entry_price * 0.98:  # 2% stop

# Volatility-based
if current_price < entry_price - (2 * atr):  # 2x ATR stop

# Time-based
if time_held > 1440 and pnl < 0:  # Exit if losing after 1 day

# Trailing stop
if current_price < highest_price * 0.95:  # 5% trailing stop
```

## External Data Sources

### Alpha Vantage (Free Tier)
- News sentiment API
- Fundamental data
- Economic indicators
- 5 API calls/minute, 100/day

### Other Potential Sources
- NewsAPI for broader coverage
- Reddit API for WSB sentiment
- Twitter API for social signals
- FRED for economic data

## What Algorithms Still CANNOT Do

### Actual Limitations
- **No Sub-Minute Trading**: Still minute-based execution
- **No Options/Futures**: Stocks only via Alpaca free tier  
- **No Portfolio Optimization**: Each algorithm is independent
- **No Margin/Leverage**: Cash accounts only
- **API Rate Limits**: Must respect external API limits

## Implementation Priority

1. **Phase 1**: Basic technical algorithms with stop losses
2. **Phase 2**: Alpha Vantage integration for sentiment
3. **Phase 3**: Backtesting framework
4. **Phase 4**: Advanced hybrid strategies

You're right - this system is way more capable than I initially suggested! Stop losses are essential, and news sentiment trading opens up really interesting possibilities.