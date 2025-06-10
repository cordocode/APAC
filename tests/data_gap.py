#!/usr/bin/env python3
"""
Test data freshness during market hours
Compare historical pull vs what's in database vs current time
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import sqlite3

sys.path.append(str(Path(__file__).parent.parent))

from database import db_manager


def check_data_freshness():
    """Check how fresh our data is during market hours"""
    
    ticker = 'NVDA'
    current_time = datetime.now(timezone.utc)
    current_time_str = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print("=" * 60)
    print("MARKET OPEN DATA FRESHNESS CHECK")
    print("=" * 60)
    print(f"Current UTC time: {current_time_str}")
    print(f"Current EST time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (subtract 5 hours)")
    print(f"Ticker: {ticker}")
    print("-" * 60)
    
    # Get latest price from database
    latest = db_manager.get_latest_price(ticker)
    
    if latest:
        print(f"\nLatest bar in database:")
        print(f"  Timestamp: {latest['timestamp']}")
        print(f"  Close: ${latest['ohlcv']['c']:.2f}")
        
        # Calculate gap
        latest_time = datetime.strptime(latest['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
        gap = current_time - latest_time
        
        print(f"\nData freshness gap: {gap}")
        
        # Determine if this is expected
        gap_minutes = gap.total_seconds() / 60
        if gap_minutes < 2:
            print("✅ Data is VERY fresh! (< 2 minutes old)")
        elif gap_minutes < 15:
            print("⚠️  Data has minor delay (expected for free tier)")
        else:
            print(f"❌ Data is {gap_minutes:.0f} minutes old!")
            
    # Now check what get_data_for_algorithm would return
    print("\n" + "-" * 60)
    print("Testing algorithm data request (last 10 bars):")
    
    bars = db_manager.get_data_for_algorithm(
        ticker=ticker,
        requirement_type='last_n_bars',
        n=10,
        before_timestamp=current_time_str
    )
    
    if bars:
        print(f"\nReceived {len(bars)} bars")
        print("\nLast 3 bars:")
        for bar in bars[-3:]:
            print(f"  {bar['timestamp']} - C: ${bar['ohlcv']['c']:.2f} V: {bar['ohlcv']['v']}")
            
    # Check in SQLite directly
    print("\n" + "-" * 60)
    print("Direct SQLite verification:")
    print("Run this in SQLite to verify:")
    print(f"""
sqlite3 database/stocks.db "
SELECT minute_timestamp, NVDA 
FROM stock_prices 
WHERE NVDA IS NOT NULL 
ORDER BY minute_timestamp DESC 
LIMIT 5;"
""")


def check_websocket_readiness():
    """Check if we should expect websocket data"""
    
    print("\n" + "=" * 60)
    print("WEBSOCKET READINESS CHECK")
    print("=" * 60)
    
    print("\nTo test WebSocket real-time data:")
    print("1. Run: python database/realtime_pull.py")
    print("2. It will subscribe to NVDA and show live bars")
    print("3. Compare timestamps with historical data")
    print("\nExpected behavior:")
    print("- Free tier: Might have 15-minute delay")
    print("- WebSocket bars should arrive ~2 seconds after each minute")
    print("- Each bar represents the PREVIOUS minute's data")


if __name__ == "__main__":
    check_data_freshness()
    check_websocket_readiness()