#!/usr/bin/env python3
"""
################################################################################
# FILE: alpaca_wrapper.py
# PURPOSE: Interface to Alpaca trading API for the AutoTrader system
################################################################################
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import from system_databse later
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from parent directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


################################################################################
# ALPACA CLIENT WRAPPER
################################################################################

class AlpacaWrapper:
    def __init__(self):
        """Initialize Alpaca trading client"""
        # Check if environment variables are loaded
        api_key = os.getenv('ALPACA_API_KEY')
        secret = os.getenv('ALPACA_SECRET')
        
        if not api_key or not secret:
            raise ValueError("Missing ALPACA_API_KEY or ALPACA_SECRET in environment")
        
        # **IMPORTANT**: Set ALPACA_PAPER=False in .env when switching to real trading
        # This controls paper vs real trading across all Alpaca integrations
        paper_trading = os.getenv('ALPACA_PAPER', 'True').lower() == 'true'
        
        # **IMPORTANT**: Set ALPACA_FEED in .env (iex for free tier, sip for paid)
        # Free tier must use 'iex', paid tier can use 'sip' for full market data
        self.data_feed = os.getenv('ALPACA_FEED', 'iex')
        
        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret,
            paper=paper_trading
        )


################################################################################
# ACCOUNT FUNCTIONS
################################################################################

    def get_account_cash(self) -> float:
        """
        Get total cash balance in the Alpaca account
        
        Returns:
            float: Total cash available in the account
        """
        try:
            account = self.client.get_account()
            # Convert string to float
            cash = float(account.cash)
            return cash
        except Exception as e:
            print(f"[ERROR] Failed to get account cash: {str(e)}")
            raise


################################################################################
# VALIDATION FUNCTIONS
################################################################################

    def validate_ticker(self, symbol: str) -> bool:
        """
        Check if a ticker symbol is valid and tradable
        
        Args:
            symbol: Stock ticker symbol (e.g., 'NVDA')
            
        Returns:
            bool: True if symbol is valid and tradable, False otherwise
        """
        try:
            # Get asset information
            asset = self.client.get_asset(symbol)
            
            # Check if it's tradable and active
            is_valid = (
                asset.tradable and 
                asset.status == 'active' and
                asset.exchange != 'OTC'  # Avoid OTC stocks
            )
            
            return is_valid
            
        except Exception as e:
            # If we can't find the asset, it's not valid
            print(f"[INFO] Ticker {symbol} validation failed: {str(e)}")
            return False


################################################################################
# TRADING FUNCTIONS
################################################################################

    def place_market_buy(self, ticker: str, shares: int) -> float:
        """
        Place a market buy order
        
        Args:
            ticker: Stock symbol to buy
            shares: Number of shares to buy
            
        Returns:
            float: Average fill price of the executed order
            
        Raises:
            Exception: If order fails or is rejected
        """
        try:
            # Create market order request
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY  # Good for the day
            )
            
            # Submit order
            order = self.client.submit_order(order_request)
            
            # Wait for fill (market orders should fill immediately)
            # In production, you might want to check order status
            filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
            
            # If no fill price yet, get the order details
            if filled_price == 0.0:
                time.sleep(1)  # Brief wait for fill
                order = self.client.get_order_by_id(order.id)
                filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
            
            return filled_price
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [ERROR] Buy order failed for {ticker}: {str(e)}")
            raise

    def place_market_sell(self, ticker: str, shares: int) -> float:
        """
        Place a market sell order
        
        Args:
            ticker: Stock symbol to sell
            shares: Number of shares to sell
            
        Returns:
            float: Average fill price of the executed order
            
        Raises:
            Exception: If order fails or is rejected
        """
        try:
            # Create market order request
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY  # Good for the day
            )
            
            # Submit order
            order = self.client.submit_order(order_request)
            
            # Wait for fill (market orders should fill immediately)
            filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
            
            # If no fill price yet, get the order details
            if filled_price == 0.0:
                time.sleep(1)  # Brief wait for fill
                order = self.client.get_order_by_id(order.id)
                filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
            
            return filled_price
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [ERROR] Sell order failed for {ticker}: {str(e)}")
            raise