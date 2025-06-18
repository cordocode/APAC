"""
################################################################################
# FILE: realtime_pull.py
# PURPOSE: Real-time data streamer for WebSocket connections to Alpaca
################################################################################
"""

import os
import asyncio
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed
from datetime import datetime
import pytz
from typing import Set
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# REAL-TIME DATA STREAMER CLASS
################################################################################

class RealtimeStreamer:
    """
    Manages WebSocket connections to Alpaca for real-time minute bar data.
    Automatically stores incoming data in the database.
    """
    
    def __init__(self):
        """Initialize WebSocket client for real-time data streaming"""
        
        # Determine the correct feed enum from environment variable
        feed_str = os.getenv('ALPACA_FEED', 'iex').upper()
        try:
            feed_enum = getattr(DataFeed, feed_str)
        except AttributeError:
            print(f"[WARN] Invalid ALPACA_FEED '{feed_str}' in .env - defaulting to IEX")
            feed_enum = DataFeed.IEX

        # Initialize websocket client
        self.stream = StockDataStream(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET'),
            raw_data=False,  # Get parsed objects, not raw JSON
            feed=feed_enum
        )
        
        self.subscribed_symbols: Set[str] = set()
        self.utc = pytz.UTC
        
        print(f"[OK] Realtime streamer initialized with feed: {feed_str}")


################################################################################
# WEBSOCKET DATA HANDLING
################################################################################

    async def handle_bar(self, data):
        """
        Handle incoming bar data from WebSocket stream.
        Automatically stores data in the database.
        
        Args:
            data: Bar object from Alpaca WebSocket
        """
        try:
            # Convert timestamp to our UTC format
            timestamp = data.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Create OHLCV dictionary
            ohlcv = {
                "o": float(data.open),
                "h": float(data.high),
                "l": float(data.low),
                "c": float(data.close),
                "v": int(data.volume)
            }
            
            # Store in database
            from database.db_manager import insert_minute_data
            rows_updated = insert_minute_data(data.symbol, timestamp, ohlcv)
            
            # Silent operation - no prints for successful storage (too frequent)
            # Only print errors which are handled in except block
                
        except Exception as e:
            print(f"[ERROR] Failed to store bar for {data.symbol} at {data.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')}: {str(e)}")


################################################################################
# SUBSCRIPTION MANAGEMENT
################################################################################

    def subscribe(self, symbols):
        """
        Subscribe to real-time bars for given symbols.
        
        Args:
            symbols: String or list of ticker symbols
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Add to WebSocket subscription
        self.stream.subscribe_bars(self.handle_bar, *symbols)
        
        # Update our tracking set
        new_symbols = set(symbols) - self.subscribed_symbols
        self.subscribed_symbols.update(symbols)
        
        # Silent operation - WebSocket manager handles logging

    def unsubscribe(self, symbols):
        """
        Unsubscribe from symbols.
        
        Args:
            symbols: String or list of ticker symbols to unsubscribe from
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Remove from WebSocket subscription
        self.stream.unsubscribe_bars(*symbols)
        
        # Update our tracking set
        removed_symbols = set(symbols) & self.subscribed_symbols
        self.subscribed_symbols.difference_update(symbols)
        
        # Silent operation - WebSocket manager handles logging

    def get_subscribed_symbols(self) -> Set[str]:
        """
        Get currently subscribed symbols.
        
        Returns:
            Set of currently subscribed ticker symbols
        """
        return self.subscribed_symbols.copy()

    def subscribe_multiple(self, symbols: list):
        """
        Subscribe to multiple symbols efficiently.
        
        Args:
            symbols: List of ticker symbols
        """
        if not symbols:
            return
        
        self.subscribe(symbols)


################################################################################
# STREAM LIFECYCLE MANAGEMENT
################################################################################

    def run(self):
        """
        Start the WebSocket stream.
        This is a blocking call that runs the WebSocket event loop.
        """
        try:
            self.stream.run()
        except KeyboardInterrupt:
            print("[INFO] WebSocket stream stopped by user")
        except Exception as e:
            print(f"[ERROR] WebSocket stream crashed: {str(e)}")
            raise

    async def run_async(self):
        """
        Start the WebSocket stream asynchronously.
        Use this when running the stream in a separate thread or async context.
        """
        try:
            await self.stream._run_forever()
        except KeyboardInterrupt:
            print("[INFO] WebSocket stream stopped by user")
        except Exception as e:
            print(f"[ERROR] WebSocket stream crashed: {str(e)}")
            raise

    def stop(self):
        """
        Stop the WebSocket stream gracefully.
        """
        try:
            self.stream.stop()
            # Silent - orchestrator handles shutdown logging
        except Exception as e:
            print(f"[ERROR] Failed to stop WebSocket stream: {str(e)}")


################################################################################
# UTILITY AND DEBUGGING FUNCTIONS
################################################################################

    def get_stream_status(self) -> dict:
        """
        Get current stream status and statistics.
        
        Returns:
            Dict with stream status information
        """
        return {
            "subscribed_symbols": list(self.subscribed_symbols),
            "subscription_count": len(self.subscribed_symbols),
            "feed_type": os.getenv('ALPACA_FEED', 'iex'),
            "is_paper_trading": os.getenv('ALPACA_PAPER', 'True').lower() == 'true'
        }

    def print_status(self):
        """Print current stream status to console"""
        # This function is not used in production - removing verbose output
        pass