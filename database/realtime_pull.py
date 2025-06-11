#!/usr/bin/env python3
"""
Real-time Data Streamer - Production Version
Handles WebSocket connections to Alpaca for live minute bar data
"""

import os
import asyncio
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed
from datetime import datetime
import pytz
from typing import Set

# Load environment variables
load_dotenv()

#==============================================================================
# REAL-TIME DATA STREAMER CLASS
#==============================================================================

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
            print(f"⚠️  Warning: Invalid ALPACA_FEED '{feed_str}'. Defaulting to IEX.")
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
        
        print(f"✅ Real-time streamer initialized")
        print(f"📡 Using {feed_str} data feed")

#==============================================================================
# WEBSOCKET DATA HANDLING
#==============================================================================

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
            
            if rows_updated > 0:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"[{current_time}] 📊 Stored {data.symbol}: ${data.close:.2f} at {timestamp}")
            else:
                # This could happen if timestamp doesn't exist in database (non-market hours)
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"[{current_time}] ⚠️  {data.symbol} bar at {timestamp} not stored (non-market hours)")
                
        except Exception as e:
            print(f"❌ Error handling bar data for {data.symbol}: {e}")

#==============================================================================
# SUBSCRIPTION MANAGEMENT
#==============================================================================

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
        
        if new_symbols:
            print(f"📡 Subscribed to real-time bars: {', '.join(new_symbols)}")
        
        print(f"📊 Total active subscriptions: {len(self.subscribed_symbols)}")

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
        
        if removed_symbols:
            print(f"📡 Unsubscribed from: {', '.join(removed_symbols)}")
        
        print(f"📊 Remaining active subscriptions: {len(self.subscribed_symbols)}")

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
        
        print(f"📡 Batch subscribing to {len(symbols)} symbols...")
        self.subscribe(symbols)

#==============================================================================
# STREAM LIFECYCLE MANAGEMENT
#==============================================================================

    def run(self):
        """
        Start the WebSocket stream.
        This is a blocking call that runs the WebSocket event loop.
        """
        if not self.subscribed_symbols:
            print("⚠️  Warning: No symbols subscribed. Stream will start but receive no data.")
        
        print(f"🚀 Starting real-time data stream...")
        print(f"📊 Subscribed symbols: {', '.join(sorted(self.subscribed_symbols)) if self.subscribed_symbols else 'None'}")
        print("🔄 Stream running... (Press Ctrl+C to stop)")
        
        try:
            self.stream.run()
        except KeyboardInterrupt:
            print("\n🛑 Stream stopped by user")
        except Exception as e:
            print(f"\n❌ Stream error: {e}")
            raise

    async def run_async(self):
        """
        Start the WebSocket stream asynchronously.
        Use this when running the stream in a separate thread or async context.
        """
        print(f"🚀 Starting async real-time data stream...")
        
        try:
            await self.stream._run_forever()
        except KeyboardInterrupt:
            print("\n🛑 Async stream stopped by user")
        except Exception as e:
            print(f"\n❌ Async stream error: {e}")
            raise

    def stop(self):
        """
        Stop the WebSocket stream gracefully.
        """
        try:
            self.stream.stop()
            print("🛑 WebSocket stream stopped")
        except Exception as e:
            print(f"❌ Error stopping stream: {e}")

#==============================================================================
# UTILITY AND DEBUGGING FUNCTIONS
#==============================================================================

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
        status = self.get_stream_status()
        
        print("\n" + "="*50)
        print("📊 REAL-TIME STREAM STATUS")
        print("="*50)
        print(f"📡 Data Feed: {status['feed_type'].upper()}")
        print(f"🔄 Paper Trading: {status['is_paper_trading']}")
        print(f"📈 Active Subscriptions: {status['subscription_count']}")
        
        if status['subscribed_symbols']:
            print(f"📊 Symbols: {', '.join(sorted(status['subscribed_symbols']))}")
        else:
            print("📊 Symbols: None")
        
        print("="*50 + "\n")