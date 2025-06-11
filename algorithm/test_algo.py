from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from datetime import datetime, timezone
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Algorithm:
    """
    Test Algorithm - Super simple trend follower for system testing
    
    Logic:
    - Gets last 10 bars
    - If average of last 5 > average of first 5: BUY 10 shares
    - If average of last 5 < average of first 5: SELL 10 shares
    - If equal: HOLD
    
    Always respects position limits and capital constraints
    """
    
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.shares_per_trade = 10  # Always trade exactly 10 shares
        
    def run(self, current_time, algo_id):
        """
        Main execution method - rebuilds full context each time
        
        Args:
            current_time: Current UTC timestamp
            algo_id: Database ID of this algorithm instance
            
        Returns:
            tuple: ('buy'/'sell'/'hold', shares)
        """
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"TEST_ALGO running for {self.ticker} (algo_id: {algo_id})")
            logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
            
            # Step 1: Rebuild full context from transaction history
            transactions = get_transactions(algo_id)
            logger.info(f"Found {len(transactions)} historical transactions")
            
            # Calculate current position and cash used
            current_shares = 0
            net_cash_used = 0
            
            for tx in transactions:
                if tx['type'] == 'buy':
                    current_shares += tx['shares']
                    net_cash_used += tx['shares'] * tx['price']
                else:  # sell
                    current_shares -= tx['shares'] 
                    net_cash_used -= tx['shares'] * tx['price']
            
            available_cash = self.initial_capital - net_cash_used
            
            logger.info(f"Current position: {current_shares} shares")
            logger.info(f"Net cash used: ${net_cash_used:,.2f}")
            logger.info(f"Available cash: ${available_cash:,.2f}")
            
            # Step 2: Get last 10 bars of data
            bars = get_data_for_algorithm(
                ticker=self.ticker,
                requirement_type='last_n_bars',
                n=10,
                before_timestamp=current_time
            )
            
            if not bars or len(bars) < 10:
                logger.warning(f"Insufficient data. Need 10 bars, got {len(bars) if bars else 0}")
                return ('hold', 0)
            
            # Extract close prices
            close_prices = []
            for bar in bars:
                if 'ohlcv' in bar and bar['ohlcv']:
                    close_prices.append(bar['ohlcv']['c'])
                else:
                    logger.warning(f"Missing ohlcv data in bar")
                    return ('hold', 0)
            
            logger.info(f"Got {len(close_prices)} close prices")
            logger.info(f"Prices: {[f'${p:.2f}' for p in close_prices]}")
            
            # Step 3: Calculate simple trend
            first_5_avg = sum(close_prices[:5]) / 5
            last_5_avg = sum(close_prices[5:]) / 5
            current_price = close_prices[-1]
            
            logger.info(f"First 5 bars average: ${first_5_avg:.2f}")
            logger.info(f"Last 5 bars average: ${last_5_avg:.2f}")
            logger.info(f"Current price: ${current_price:.2f}")
            
            # Step 4: Make trading decision with position/capital constraints
            if last_5_avg > first_5_avg:
                # Trend is UP - try to buy
                logger.info("📈 TREND IS UP")
                
                # Check if we have enough cash for 10 shares
                cost_to_buy = self.shares_per_trade * current_price
                
                if available_cash >= cost_to_buy:
                    logger.info(f"✅ Buying {self.shares_per_trade} shares (cost: ${cost_to_buy:.2f})")
                    return ('buy', self.shares_per_trade)
                else:
                    logger.info(f"❌ Not enough cash. Need ${cost_to_buy:.2f}, have ${available_cash:.2f}")
                    return ('hold', 0)
                    
            elif last_5_avg < first_5_avg:
                # Trend is DOWN - try to sell
                logger.info("📉 TREND IS DOWN")
                
                # Check if we have shares to sell
                if current_shares >= self.shares_per_trade:
                    logger.info(f"✅ Selling {self.shares_per_trade} shares")
                    return ('sell', self.shares_per_trade)
                else:
                    logger.info(f"❌ Not enough shares. Have {current_shares}, need {self.shares_per_trade}")
                    return ('hold', 0)
                    
            else:
                # Trend is FLAT
                logger.info("➡️ TREND IS FLAT - holding")
                return ('hold', 0)
                
        except Exception as e:
            logger.error(f"❌ Error in test_algo for {self.ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
            return ('hold', 0)


# For testing the algorithm independently
if __name__ == "__main__":
    # Test initialization
    algo = Algorithm("AAPL", 1000)  # $1000 allocation
    
    print(f"Test algorithm initialized for {algo.ticker}")
    print(f"Initial capital: ${algo.initial_capital}")
    print(f"Shares per trade: {algo.shares_per_trade}")
    
    # You could add mock tests here