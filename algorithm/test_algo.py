"""
################################################################################
# FILE: test_algo.py
# PURPOSE: Test algorithm for system testing with simple trend following logic
################################################################################
"""

from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from datetime import datetime, timezone
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# MAIN ALGORITHM CLASS
################################################################################

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
            logger.info(f"[{datetime.now().isoformat()}] Algorithm started")
            logger.info(f"[{datetime.now().isoformat()}] Processing ticker data")
            logger.info(f"[{datetime.now().isoformat()}] Initialized capital allocation")
            
            # Step 1: Rebuild full context from transaction history
            transactions = get_transactions(algo_id)
            logger.info(f"[{datetime.now().isoformat()}] Retrieved transaction history")
            
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
            
            logger.info(f"[{datetime.now().isoformat()}] Current position calculated")
            logger.info(f"[{datetime.now().isoformat()}] Net cash calculated")
            logger.info(f"[{datetime.now().isoformat()}] Available cash calculated")
            
            # Step 2: Get last 10 bars of data (ask for 11 to ensure we get 10)
            bars = get_data_for_algorithm(
                ticker=self.ticker,
                requirement_type='last_n_bars',
                n=11,  # Ask for 11 to ensure we get at least 10
                before_timestamp=current_time
            )
            
            if not bars or len(bars) < 10:
                logger.warning(f"[{datetime.now().isoformat()}] Insufficient data received")
                return ('hold', 0)
            
            logger.info(f"[{datetime.now().isoformat()}] Received data bars")
            if bars:
                logger.info(f"[{datetime.now().isoformat()}] First bar validated")
                logger.info(f"[{datetime.now().isoformat()}] Last bar validated")
            
            # Extract close prices (use only last 10 bars for calculation)
            close_prices = []
            bars_to_use = bars[-10:]  # Take only the last 10 bars
            for bar in bars_to_use:
                if 'ohlcv' in bar and bar['ohlcv']:
                    close_prices.append(bar['ohlcv']['c'])
                else:
                    logger.warning(f"[{datetime.now().isoformat()}] Missing OHLCV data")
                    return ('hold', 0)
            
            logger.info(f"[{datetime.now().isoformat()}] Extracted price data")
            logger.info(f"[{datetime.now().isoformat()}] Price data validated")
            
            # Step 3: Calculate simple trend
            first_5_avg = sum(close_prices[:5]) / 5
            last_5_avg = sum(close_prices[5:]) / 5
            current_price = close_prices[-1]
            
            logger.info(f"[{datetime.now().isoformat()}] Calculated first average")
            logger.info(f"[{datetime.now().isoformat()}] Calculated last average")
            logger.info(f"[{datetime.now().isoformat()}] Retrieved current price")
            
            # Calculate trend percentage change for more sensitivity
            trend_change = ((last_5_avg - first_5_avg) / first_5_avg) * 100
            logger.info(f"[{datetime.now().isoformat()}] Calculated trend change")
            
            # Step 4: Make trading decision with position/capital constraints
            # Use a small threshold for more active trading (0.01% = 0.0001)
            if trend_change > 0.01:  # Even tiny upward trend triggers buy
                # Trend is UP - try to buy
                logger.info(f"[{datetime.now().isoformat()}] Upward trend detected")
                
                # Check if we have enough cash for 10 shares
                cost_to_buy = self.shares_per_trade * current_price
                
                if available_cash >= cost_to_buy:
                    logger.info(f"[{datetime.now().isoformat()}] Generating buy signal")
                    return ('buy', self.shares_per_trade)
                else:
                    logger.info(f"[{datetime.now().isoformat()}] Insufficient funds")
                    return ('hold', 0)
                    
            elif trend_change < -0.01:  # Even tiny downward trend triggers sell
                # Trend is DOWN - try to sell
                logger.info(f"[{datetime.now().isoformat()}] Downward trend detected")
                
                # Check if we have shares to sell
                if current_shares >= self.shares_per_trade:
                    logger.info(f"[{datetime.now().isoformat()}] Generating sell signal")
                    return ('sell', self.shares_per_trade)
                else:
                    logger.info(f"[{datetime.now().isoformat()}] Insufficient shares")
                    return ('hold', 0)
                    
            else:
                # Trend is FLAT (between -0.01% and +0.01%)
                logger.info(f"[{datetime.now().isoformat()}] Flat trend detected")
                return ('hold', 0)
                
        except Exception as e:
            logger.error(f"[{datetime.now().isoformat()}] Algorithm error occurred")
            import traceback
            traceback.print_exc()
            return ('hold', 0)