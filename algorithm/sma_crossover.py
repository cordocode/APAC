"""
################################################################################
# FILE: sma_crossover.py
# PURPOSE: Simple Moving Average crossover trading algorithm
################################################################################
"""

from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from datetime import datetime, timezone
import json
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
                logger.warning(f"[{datetime.now().isoformat()}] Insufficient data received")
                return ('hold', 0)
            
            # Debug: Check what we actually got
            logger.info(f"[{datetime.now().isoformat()}] Received data bars")
            logger.info(f"[{datetime.now().isoformat()}] Processing bar data")
            logger.info(f"[{datetime.now().isoformat()}] Validating bar data")
            
            # Parse OHLCV data and extract close prices
            close_prices = []
            for bar in bars:
                if 'ohlcv' in bar and bar['ohlcv']:
                    close_prices.append(bar['ohlcv']['c'])
                else:
                    logger.warning(f"[{datetime.now().isoformat()}] Missing OHLCV data")
                    return ('hold', 0)
            
            logger.info(f"[{datetime.now().isoformat()}] Parsed price data")
            logger.info(f"[{datetime.now().isoformat()}] Calculated price range")
            
            # Calculate SMAs
            current_short_sma = sum(close_prices[-self.sma_short:]) / self.sma_short
            current_long_sma = sum(close_prices[-self.sma_long:]) / self.sma_long
            
            # Calculate previous SMAs for crossover detection
            prev_short_sma = sum(close_prices[-self.sma_short-1:-1]) / self.sma_short
            prev_long_sma = sum(close_prices[-self.sma_long-1:-1]) / self.sma_long
            
            logger.info(f"[{datetime.now().isoformat()}] Calculated current SMAs")
            logger.info(f"[{datetime.now().isoformat()}] Calculated previous SMAs")
            
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
                logger.info(f"[{datetime.now().isoformat()}] Golden cross detected")
                if current_shares == 0 and available_cash > current_price:
                    # Calculate how many shares we can buy with available cash
                    shares_to_buy = int(available_cash * 0.95 / current_price)  # Use 95% to leave buffer
                    if shares_to_buy > 0:
                        logger.info(f"[{datetime.now().isoformat()}] Generating buy signal")
                        return ('buy', shares_to_buy)
                else:
                    logger.info(f"[{datetime.now().isoformat()}] Insufficient resources")
                        
            elif prev_short_sma >= prev_long_sma and current_short_sma < current_long_sma:
                # Death cross - bearish signal
                logger.info(f"[{datetime.now().isoformat()}] Death cross detected")
                if current_shares > 0:
                    logger.info(f"[{datetime.now().isoformat()}] Generating sell signal")
                    return ('sell', current_shares)
                else:
                    logger.info(f"[{datetime.now().isoformat()}] No position available")
            
            # No action needed
            logger.info(f"[{datetime.now().isoformat()}] No crossover detected")
            
            # No action needed
            return ('hold', 0)
            
        except Exception as e:
            logger.error(f"[{datetime.now().isoformat()}] Algorithm error occurred")
            return ('hold', 0)
    

    ################################################################################
    # HELPER FUNCTIONS
    ################################################################################
    
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