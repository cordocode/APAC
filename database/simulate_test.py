#!/usr/bin/env python3
"""
Simulate a real frontend request for TSLA with 5 days of data + websocket.
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta

sys.path.append('database')

from historical_pull import HistoricalFetcher
from realtime_pull import RealtimeStreamer
from db_manager import get_historical_data, get_latest_price

def simulate_frontend_request():
    """Simulate what happens when frontend requests TSLA algorithm."""
    
    print("🚀 SIMULATING FRONTEND REQUEST FOR TSLA ALGORITHM")
    print("=" * 60)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Request: Last 5 days of TSLA data + start websocket")
    print("=" * 60)
    
    # Step 1: Calculate date range (May 25 - May 31)
    # Since today is Saturday May 31, market data only goes through Friday May 30
    end_date = "2025-05-30"  # Friday
    start_date = "2025-05-26"  # Monday (May 25 is Sunday, so start Monday)
    ticker = "TSLA"
    
    print(f"\n📅 Date range: {start_date} to {end_date}")
    print("   (Adjusted to weekdays only)")
    
    # Step 2: Fetch historical data
    print(f"\n📊 STEP 1: Fetching historical data for {ticker}...")
    print("-" * 50)
    
    fetcher = HistoricalFetcher()
    
    # Fetch the date range
    result = fetcher.fetch_and_store(ticker, start_date, end_date)
    
    print(f"\nFetch result: {result}")
    
    if result['status'] == 'fetched':
        print(f"✅ Successfully fetched {result['data_points']} minute bars")
        print(f"✅ Updated {result['rows_updated']} rows in database")
    elif result['status'] == 'already_exists':
        print("ℹ️  Data already exists in database")
    
    # Step 3: Verify data is in database
    print(f"\n📊 STEP 2: Verifying data in database...")
    print("-" * 50)
    
    # Check each day
    days_to_check = ["2025-05-26", "2025-05-27", "2025-05-28", "2025-05-29", "2025-05-30"]
    
    total_bars = 0
    for day in days_to_check:
        start_utc = f"{day}T14:30:00Z"  # 9:30 AM EST
        end_utc = f"{day}T21:00:00Z"    # 4:00 PM EST
        
        data = get_historical_data(ticker, start_utc, end_utc)
        bars_count = len(data)
        total_bars += bars_count
        
        if bars_count > 0:
            print(f"✅ {day}: {bars_count} minute bars")
            print(f"   First: {data[0]['timestamp']} -> ${data[0]['ohlcv']['c']}")
            print(f"   Last:  {data[-1]['timestamp']} -> ${data[-1]['ohlcv']['c']}")
        else:
            print(f"❌ {day}: No data")
    
    print(f"\n📊 Total bars in database: {total_bars}")
    
    # Get latest price
    latest = get_latest_price(ticker)
    if latest:
        print(f"\n💰 Latest {ticker} price: ${latest['ohlcv']['c']} at {latest['timestamp']}")
    
    # Step 4: Start websocket (even though market is closed)
    print(f"\n📡 STEP 3: Starting websocket for real-time data...")
    print("-" * 50)
    
    streamer = RealtimeStreamer()
    
    # Subscribe to TSLA
    streamer.subscribe([ticker])
    
    # Start stream in background thread
    stream_thread = threading.Thread(target=streamer.run)
    stream_thread.daemon = True
    stream_thread.start()
    
    print("✅ Websocket started and subscribed to TSLA")
    print("ℹ️  Note: Market is closed, so no new data will arrive")
    print("ℹ️  Websocket is running in background (for 30 seconds)...")
    
    # Keep alive for 30 seconds to show websocket is running
    for i in range(6):
        time.sleep(5)
        print(f"   ⏱️  Websocket active... {30 - i*5} seconds remaining")
    
    print("\n✅ Simulation complete!")
    
    # Provide SQL commands
    print("\n" + "=" * 60)
    print("📋 SQL COMMANDS TO VERIFY DATA:")
    print("=" * 60)
    print("\nOpen SQLite:")
    print("sqlite3 database/stocks.db")
    
    print("\n1. Check total TSLA data points:")
    print("SELECT COUNT(*) FROM stock_prices WHERE TSLA IS NOT NULL;")
    
    print("\n2. Show first 10 TSLA entries:")
    print("SELECT minute_timestamp, TSLA FROM stock_prices WHERE TSLA IS NOT NULL ORDER BY minute_timestamp LIMIT 10;")
    
    print("\n3. Show last 10 TSLA entries:")
    print("SELECT minute_timestamp, TSLA FROM stock_prices WHERE TSLA IS NOT NULL ORDER BY minute_timestamp DESC LIMIT 10;")
    
    print("\n4. Check specific date (May 30, 2025):")
    print("SELECT COUNT(*) FROM stock_prices WHERE minute_timestamp LIKE '2025-05-30%' AND TSLA IS NOT NULL;")
    
    print("\n5. Show TSLA data for 9:30-9:40 AM EST on May 30:")
    print("SELECT minute_timestamp, TSLA FROM stock_prices WHERE minute_timestamp >= '2025-05-30T14:30:00Z' AND minute_timestamp <= '2025-05-30T14:40:00Z' AND TSLA IS NOT NULL;")
    
    print("\n6. Get latest TSLA price:")
    print("SELECT minute_timestamp, TSLA FROM stock_prices WHERE TSLA IS NOT NULL ORDER BY minute_timestamp DESC LIMIT 1;")
    
    print("\nNote: Timestamps in quotes to avoid SQL parse errors!")
    print("=" * 60)


if __name__ == "__main__":
    simulate_frontend_request()