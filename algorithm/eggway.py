"""
################################################################################
# FILE: eggway.py
# PURPOSE: Support resistance long only scalper trading algorithm
################################################################################
"""

from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from datetime import datetime, time, timezone
import logging

# Configure formatter for unified logging format
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# ALGORITHM CLASS
################################################################################

class Algorithm:
    """
    Support Resistance Long Only Scalper
    
    Strategy Logic:
    - Uses ATR (14) and lookback (20 bars) to find support zone
    - Only takes long trades near support (close <= support + 0.2 * ATR)
    - Sets stop loss at entry - 1.2 * ATR
    - Sets target price at entry + 1.2 * ATR * risk-reward ratio
    - Trades only within session (9:35am - 3:55pm EST)
    - Position size calculated as % risk of available capital per trade
    """

    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        
        # Parameters
        self.atr_period = 14
        self.lookback = 20
        self.risk_per_trade = 0.01  # 1% of available capital per trade
        self.rr_ratio = 2.0
        self.session_start = time(9, 35)
        self.session_end = time(15, 55)
        
        # State variables to track active trade
        self.entry_price = None
        self.stop_price = None
        self.target_price = None
        self.position_size = 0  # shares currently held

    def in_session(self, current_time):
        # Check if current_time (datetime) is within trading session
        local_time = current_time.astimezone().time()  # convert to local time zone if needed
        return self.session_start <= local_time <= self.session_end

    def calculate_atr(self, bars):
        # Calculate ATR (Average True Range) for last atr_period bars
        # ATR = average of true ranges:
        # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        if len(bars) < self.atr_period + 1:
            return None  # Not enough data
        trs = []
        for i in range(1, self.atr_period + 1):
            high = bars[-i]['ohlcv']['h']
            low = bars[-i]['ohlcv']['l']
            prev_close = bars[-i - 1]['ohlcv']['c']
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / self.atr_period

    def run(self, current_time, algo_id):
        """
        Main method called each cycle.
        
        Args:
            current_time: datetime object in UTC
            algo_id: algorithm instance ID
            
        Returns:
            tuple: ('buy'/'sell'/'hold', shares)
        """
        try:
            logger.info("Algorithm cycle started")
            logger.info("Running scalper algorithm")
            logger.info("Initial capital loaded")

            # Step 1: Check if within session
            if not self.in_session(current_time):
                logger.info("Outside trading session")
                return ('hold', 0)

            # Step 2: Get historical transactions and calculate current position & available cash
            transactions = get_transactions(algo_id)
            current_shares = sum(tx['shares'] if tx['type'] == 'buy' else -tx['shares'] for tx in transactions)
            net_cash_used = sum(tx['shares']*tx['price'] if tx['type']=='buy' else -tx['shares']*tx['price'] for tx in transactions)
            available_cash = self.initial_capital - net_cash_used
            
            logger.info("Current position calculated")
            logger.info("Cash position calculated")
            logger.info("Available cash calculated")

            # Step 3: Get bar data (lookback + 1 for ATR calculation)
            bars = get_data_for_algorithm(
                ticker=self.ticker,
                requirement_type='last_n_bars',
                n=self.lookback + self.atr_period + 1,  # To calculate ATR + support
                before_timestamp=current_time
            )
            if not bars or len(bars) < self.lookback + self.atr_period + 1:
                logger.warning("Insufficient bar data")
                return ('hold', 0)

            # Extract OHLC for lookback bars
            closes = [bar['ohlcv']['c'] for bar in bars[-self.lookback:]]
            highs = [bar['ohlcv']['h'] for bar in bars[-self.lookback:]]
            lows = [bar['ohlcv']['l'] for bar in bars[-self.lookback:]]

            # Step 4: Calculate ATR
            atr = self.calculate_atr(bars)
            if atr is None:
                logger.warning("ATR calculation failed")
                return ('hold', 0)
            logger.info("ATR calculated")

            # Step 5: Determine support zone (lowest low over lookback period)
            support = min(lows)
            logger.info("Support zone calculated")

            current_price = bars[-1]['ohlcv']['c']

            # Step 6: Check if we currently hold a position
            if current_shares > 0:
                # We have an open position - check target or stop
                
                # If we lost track of prices (e.g. fresh instance), estimate prices
                if self.entry_price is None or self.stop_price is None or self.target_price is None:
                    logger.info("Position detected incomplete")
                    return ('sell', current_shares)

                if current_price >= self.target_price:
                    logger.info("Target price reached")
                    self.entry_price = None
                    self.stop_price = None
                    self.target_price = None
                    return ('sell', current_shares)

                if current_price <= self.stop_price:
                    logger.info("Stop loss triggered")
                    self.entry_price = None
                    self.stop_price = None
                    self.target_price = None
                    return ('sell', current_shares)

                logger.info("Position held unchanged")
                return ('hold', 0)

            # Step 7: Check entry conditions - only long near support + 0.2*ATR
            entry_zone = support + 0.2 * atr
            if current_price <= entry_zone:
                # Calculate risk per share (distance from entry to stop)
                stop_price = current_price - 1.2 * atr
                risk_per_share = current_price - stop_price

                if risk_per_share <= 0:
                    logger.warning("Invalid risk calculation")
                    return ('hold', 0)

                # Calculate position size based on risk per trade and available cash
                max_risk_amount = available_cash * self.risk_per_trade
                position_size = int(max_risk_amount / risk_per_share)

                if position_size <= 0:
                    logger.info("Insufficient available cash")
                    return ('hold', 0)

                target_price = current_price + 1.2 * atr * self.rr_ratio

                # Save trade parameters for next run
                self.entry_price = current_price
                self.stop_price = stop_price
                self.target_price = target_price
                self.position_size = position_size

                logger.info("Entry signal generated")
                return ('buy', position_size)

            logger.info("No entry signal")
            return ('hold', 0)

        except Exception as e:
            logger.error("Algorithm error occurred")
            return ('hold', 0)