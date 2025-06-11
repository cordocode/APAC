from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from datetime import datetime, timezone
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Algorithm:
    """
    Simple Moving Average (SMA) Crossover Algorithm
    
    Buys when short SMA crosses above long SMA
    Sells when short SMA crosses below long SMA
    """
    
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.sma_short = 20  # 20-period SMA
        self.sma_long = 50   # 50-period SMA
        
    def run(self, current_time, algo_id):
        """
        Main execution method called by orchestrator every minute
        
        Args:
            current_time: Current UTC timestamp
            algo_id: Database ID of this algorithm instance
            
        Returns:
            tuple: ('buy'/'sell'/'hold', shares)
        """
        try:
            # Get market data - need enough bars for long SMA
            bars = get_data_for_algorithm(
                ticker=self.ticker,
                requirement_type='last_n_bars',
                n=self.sma_long + 1,  # Need 51 bars to calculate 50-period SMA and detect crossover
                before_timestamp=current_time  # Get data before the current execution time
            )
            
            if not bars or len(bars) < self.sma_long + 1:
                logger.warning(f"Insufficient data for {self.ticker}. Need {self.sma_long + 1} bars, got {len(bars) if bars else 0}")
                return ('hold', 0)
            
            # Debug: Check what we actually got
            logger.info(f"Got {len(bars)} bars")
            logger.info(f"First bar: {bars[0]}")
            logger.info(f"Last bar: {bars[-1]}")
            
            # Parse OHLCV data and extract close prices
            close_prices = []
            for bar in bars:
                if 'ohlcv' in bar and bar['ohlcv']:
                    close_prices.append(bar['ohlcv']['c'])
                else:
                    logger.warning(f"Missing ohlcv data for timestamp {bar.get('timestamp', 'unknown')}")
                    return ('hold', 0)
            
            logger.info(f"Successfully parsed {len(close_prices)} close prices")
            logger.info(f"Price range: ${min(close_prices):.2f} - ${max(close_prices):.2f}")
            
            # Calculate SMAs
            current_short_sma = sum(close_prices[-self.sma_short:]) / self.sma_short
            current_long_sma = sum(close_prices[-self.sma_long:]) / self.sma_long
            
            # Calculate previous SMAs for crossover detection
            prev_short_sma = sum(close_prices[-self.sma_short-1:-1]) / self.sma_short
            prev_long_sma = sum(close_prices[-self.sma_long-1:-1]) / self.sma_long
            
            logger.info(f"Current SMAs - Short: ${current_short_sma:.2f}, Long: ${current_long_sma:.2f}")
            logger.info(f"Previous SMAs - Short: ${prev_short_sma:.2f}, Long: ${prev_long_sma:.2f}")
            
            # Get current position from transaction history
            transactions = get_transactions(algo_id)
            current_shares = self._calculate_current_position(transactions)
            
            # Get current price (most recent close)
            current_price = close_prices[-1]
            
            # Calculate how much cash we have available
            cash_used = self._calculate_cash_used(transactions)
            available_cash = self.initial_capital - cash_used
            
            # Detect crossovers and make trading decisions
            if prev_short_sma <= prev_long_sma and current_short_sma > current_long_sma:
                # Golden cross - bullish signal
                logger.info("Golden cross detected!")
                if current_shares == 0 and available_cash > current_price:
                    # Calculate how many shares we can buy with available cash
                    shares_to_buy = int(available_cash * 0.95 / current_price)  # Use 95% to leave buffer
                    if shares_to_buy > 0:
                        logger.info(f"Golden cross detected for {self.ticker}. Buying {shares_to_buy} shares at ~${current_price:.2f}")
                        return ('buy', shares_to_buy)
                else:
                    logger.info(f"Golden cross but can't buy - shares: {current_shares}, cash: ${available_cash:.2f}")
                        
            elif prev_short_sma >= prev_long_sma and current_short_sma < current_long_sma:
                # Death cross - bearish signal
                logger.info("Death cross detected!")
                if current_shares > 0:
                    logger.info(f"Death cross detected for {self.ticker}. Selling all {current_shares} shares at ~${current_price:.2f}")
                    return ('sell', current_shares)
                else:
                    logger.info("Death cross but no shares to sell")
            
            # No action needed
            logger.info("No crossover detected - holding")
            
            # No action needed
            return ('hold', 0)
            
        except Exception as e:
            logger.error(f"Error in SMA crossover algorithm for {self.ticker}: {str(e)}")
            return ('hold', 0)
    
    def _calculate_current_position(self, transactions):
        """Calculate current share position from transaction history"""
        shares = 0
        for tx in transactions:
            if tx['type'] == 'buy':
                shares += tx['shares']
            else:  # sell
                shares -= tx['shares']
        return shares
    
    def _calculate_cash_used(self, transactions):
        """Calculate net cash used (buys minus sells)"""
        cash_used = 0
        for tx in transactions:
            if tx['type'] == 'buy':
                cash_used += tx['shares'] * tx['price']
            else:  # sell
                cash_used -= tx['shares'] * tx['price']
        return cash_used


# For testing the algorithm independently
if __name__ == "__main__":
    # Test initialization
    algo = Algorithm("AAPL", 10000)
    
    # Mock test - would need actual database setup to fully test
    print(f"Algorithm initialized for {algo.ticker} with ${algo.initial_capital:,.2f}")
    print(f"Using {algo.sma_short}-period short SMA and {algo.sma_long}-period long SMA")
    
    # You could add more comprehensive tests here with mock data