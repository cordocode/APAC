#!/usr/bin/env python3
"""
Debug exactly what timestamp Alpaca returns for problematic dates.
"""

import os
import sys
sys.path.append('database')

from datetime import datetime
import pytz
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

load_dotenv()

def debug_alpaca_timestamps():
    """See exactly what Alpaca returns."""
    
    print("🔍 DEBUGGING ALPACA TIMESTAMPS")
    print("=" * 60)
    
    # Initialize client
    client = StockHistoricalDataClient(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET')
    )
    
    # Test dates that showed the problem
    test_cases = [
        ("2024-12-20", "Friday - got 1 point, 0 updates"),
        ("2024-12-19", "Thursday - got 1 point, 0 updates"),
        ("2025-01-03", "Recent Friday - got 1 point, 0 updates"),
        ("2024-01-02", "Known good date from other tests"),
    ]
    
    for test_date, description in test_cases:
        print(f"\n📊 Testing {test_date} ({description})")
        print("-" * 40)
        
        # Create request
        request = StockBarsRequest(
            symbol_or_symbols="NVDA",
            timeframe=TimeFrame.Minute,
            start=datetime.strptime(test_date, '%Y-%m-%d'),
            end=datetime.strptime(test_date, '%Y-%m-%d')
        )
        
        try:
            # Get bars
            bars_dict = client.get_stock_bars(request)
            
            # Check if we got data
            if "NVDA" in bars_dict:
                bars = bars_dict["NVDA"]
                
                # Try to iterate
                bar_list = []
                try:
                    for bar in bars:
                        bar_list.append(bar)
                except:
                    print("   ⚠️  Could not iterate bars")
                
                print(f"   Total bars: {len(bar_list)}")
                
                if bar_list:
                    # Show ALL bars with their exact timestamps
                    print(f"\n   ALL {len(bar_list)} bars returned:")
                    for i, bar in enumerate(bar_list[:10]):  # Show first 10
                        raw_ts = bar.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
                        print(f"   Bar {i+1}: {raw_ts} -> O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}")
                        
                        # Check the hour
                        if bar.timestamp.hour == 0:
                            print(f"          ⚠️  MIDNIGHT TIMESTAMP!")
                        elif bar.timestamp.hour < 14 or bar.timestamp.hour > 21:
                            print(f"          ⚠️  OUTSIDE MARKET HOURS (hour={bar.timestamp.hour} UTC)")
                    
                    if len(bar_list) > 10:
                        print(f"   ... and {len(bar_list) - 10} more bars")
                else:
                    print("   ❌ Empty bar list")
            else:
                print("   ❌ No NVDA key in response")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Now let's check what happens with explicit time boundaries
    print("\n\n📊 Testing with explicit time boundaries")
    print("=" * 60)
    
    test_date = "2024-12-20"
    eastern = pytz.timezone('US/Eastern')
    
    # Create start/end with explicit times
    start_dt = eastern.localize(datetime.strptime(f"{test_date} 09:30:00", '%Y-%m-%d %H:%M:%S'))
    end_dt = eastern.localize(datetime.strptime(f"{test_date} 16:00:00", '%Y-%m-%d %H:%M:%S'))
    
    print(f"\nRequesting with explicit times:")
    print(f"   Start: {start_dt} ({start_dt.astimezone(pytz.UTC)})")
    print(f"   End: {end_dt} ({end_dt.astimezone(pytz.UTC)})")
    
    request = StockBarsRequest(
        symbol_or_symbols="NVDA",
        timeframe=TimeFrame.Minute,
        start=start_dt,
        end=end_dt
    )
    
    try:
        bars_dict = client.get_stock_bars(request)
        
        if "NVDA" in bars_dict:
            bars = list(bars_dict["NVDA"])
            print(f"\n   Got {len(bars)} bars with explicit times")
            
            if bars:
                print(f"   First bar: {bars[0].timestamp}")
                print(f"   Last bar: {bars[-1].timestamp}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def check_fetch_and_store_internals():
    """Debug what's happening inside fetch_and_store."""
    
    print("\n\n🔍 DEBUGGING fetch_and_store INTERNALS")
    print("=" * 60)
    
    from historical_pull import HistoricalFetcher
    
    # Monkey-patch to add debugging
    original_fetch = HistoricalFetcher.fetch_and_store
    
    def debug_fetch_and_store(self, ticker, start_date, end_date):
        print(f"\n[DEBUG] fetch_and_store called with:")
        print(f"   ticker: {ticker}")
        print(f"   start_date: {start_date}")
        print(f"   end_date: {end_date}")
        
        # Call original but intercept the data_array
        import db_manager
        original_insert = db_manager.insert_historical_data
        
        def debug_insert(ticker, data_array):
            print(f"\n[DEBUG] insert_historical_data called with:")
            print(f"   ticker: {ticker}")
            print(f"   data_array length: {len(data_array)}")
            
            if data_array:
                print(f"\n   First few data points:")
                for i, item in enumerate(data_array[:3]):
                    print(f"   [{i}] timestamp: {item['timestamp']}")
                    print(f"       ohlcv: {item['ohlcv']}")
            
            # Call original
            return original_insert(ticker, data_array)
        
        # Temporarily replace
        db_manager.insert_historical_data = debug_insert
        
        try:
            result = original_fetch(self, ticker, start_date, end_date)
            print(f"\n[DEBUG] fetch_and_store result: {result}")
            return result
        finally:
            # Restore original
            db_manager.insert_historical_data = original_insert
    
    # Apply monkey patch
    HistoricalFetcher.fetch_and_store = debug_fetch_and_store
    
    # Now test
    fetcher = HistoricalFetcher()
    result = fetcher.fetch_and_store("NVDA", "2024-12-20", "2024-12-20")


if __name__ == "__main__":
    debug_alpaca_timestamps()
    check_fetch_and_store_internals()