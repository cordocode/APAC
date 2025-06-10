#!/usr/bin/env python3
"""
Test fetching fresh data during market hours
This will trigger auto-fetch to get today's data from Alpaca
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent))

from database import db_manager


def test_fresh_data_request():
    """Request last 50 bars - this should fetch today's fresh data"""
    
    ticker = 'NVDA'
    current_time = datetime.now(timezone.utc)
    current_time_str = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print("=" * 60)
    print("FRESH DATA FETCH TEST (Market Open)")
    print("=" * 60)
    print(f"Current UTC time: {current_time_str}")
    print(f"Market opened at: 2025-06-10T13:30:00Z (9:30 AM EST)")
    print(f"Ticker: {ticker}")
    print("=" * 60)
    
    print("\nRequesting last 50 bars (will auto-fetch today's data)...")
    
    # This should trigger auto-fetch for today's data
    bars = db_manager.get_data_for_algorithm(
        ticker=ticker,
        requirement_type='last_n_bars',
        n=50,
        before_timestamp=current_time_str
    )
    
    print(f"\nReceived {len(bars)} bars")
    
    if bars:
        # Show the most recent bars
        print("\nLast 5 bars:")
        for i, bar in enumerate(bars[-5:], len(bars)-4):
            print(f"  [{i}] {bar['timestamp']} - O:{bar['ohlcv']['o']:.2f} "
                  f"H:{bar['ohlcv']['h']:.2f} L:{bar['ohlcv']['l']:.2f} "
                  f"C:{bar['ohlcv']['c']:.2f} V:{bar['ohlcv']['v']}")
        
        # Check freshness of the newest data
        newest_bar_time = datetime.strptime(bars[-1]['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
        newest_bar_time = newest_bar_time.replace(tzinfo=timezone.utc)
        
        gap = current_time - newest_bar_time
        gap_minutes = gap.total_seconds() / 60
        
        print(f"\n" + "="*60)
        print("DATA FRESHNESS ANALYSIS:")
        print("="*60)
        print(f"Current time:      {current_time_str}")
        print(f"Newest bar:        {bars[-1]['timestamp']}")
        print(f"Gap:               {gap} ({gap_minutes:.1f} minutes)")
        
        if gap_minutes < 2:
            print("\n✅ Data is REAL-TIME! (< 2 minute delay)")
        elif gap_minutes < 15:
            print(f"\n⚠️  Data has {gap_minutes:.0f} minute delay")
            print("This might be the free tier delay")
        else:
            print(f"\n❌ Data is {gap_minutes:.0f} minutes old!")
            
        # Check if we got today's market open data
        market_open_today = "2025-06-10T13:30:00Z"
        has_today_open = any(bar['timestamp'] >= market_open_today for bar in bars)
        
        if has_today_open:
            today_bars = [bar for bar in bars if bar['timestamp'] >= market_open_today]
            print(f"\n✅ Successfully fetched {len(today_bars)} bars from today's session")
        else:
            print("\n❌ No data from today's session found!")


if __name__ == "__main__":
    test_fresh_data_request()