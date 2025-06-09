import os
import asyncio
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed # <-- CORRECTED IMPORT
from datetime import datetime
import pytz
from db_manager import insert_minute_data

# Load environment variables
load_dotenv()

class RealtimeStreamer:
    def __init__(self):
        # Determine the correct feed enum from the environment variable string
        feed_str = os.getenv('ALPACA_FEED', 'iex').upper()
        try:
            # Use getattr to safely get the enum member from DataFeed
            feed_enum = getattr(DataFeed, feed_str)
        except AttributeError:
            print(f"Warning: Invalid ALPACA_FEED '{feed_str}'. Defaulting to IEX.")
            feed_enum = DataFeed.IEX

        # Initialize websocket client
        self.stream = StockDataStream(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET'),
            raw_data=False,  # Get parsed objects, not raw JSON
            feed=feed_enum  # <-- USE THE CORRECT ENUM OBJECT
        )
        self.subscribed_symbols = set()
        self.utc = pytz.UTC
    
    async def handle_bar(self, data):
        """
        Handle incoming bar data from websocket.
        
        Args:
            data: Bar object from Alpaca
        """
        try:
            # Convert timestamp to our UTC format
            timestamp = data.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Create OHLCV dict
            ohlcv = {
                "o": float(data.open),
                "h": float(data.high),
                "l": float(data.low),
                "c": float(data.close),
                "v": int(data.volume)
            }
            
            # Store in database
            rows = insert_minute_data(data.symbol, timestamp, ohlcv)
            
            if rows > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Stored {data.symbol} bar: ${data.close} at {timestamp}")
                
        except Exception as e:
            print(f"Error handling bar data: {e}")
    
    def subscribe(self, symbols):
        """
        Subscribe to real-time bars for given symbols.
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        self.stream.subscribe_bars(self.handle_bar, *symbols)
        self.subscribed_symbols.update(symbols)
        print(f"Subscribed to real-time bars for: {', '.join(symbols)}")
    
    def unsubscribe(self, symbols):
        """Unsubscribe from symbols."""
        if isinstance(symbols, str):
            symbols = [symbols]
        
        self.stream.unsubscribe_bars(*symbols)
        self.subscribed_symbols.difference_update(symbols)
        print(f"Unsubscribed from: {', '.join(symbols)}")
    
    def run(self):
        """Start the websocket stream."""
        print("Starting real-time stream...")
        print(f"Currently subscribed to: {', '.join(self.subscribed_symbols)}")
        
        try:
            self.stream.run()
        except KeyboardInterrupt:
            print("\nStopping stream...")
        except Exception as e:
            print(f"Stream error: {e}")

# Test function
if __name__ == "__main__":
    streamer = RealtimeStreamer()
    streamer.subscribe(['NVDA', 'AAPL', 'TSLA'])
    streamer.run()