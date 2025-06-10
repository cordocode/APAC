#!/usr/bin/env python3
"""
Test Algorithm Data Request
Simulates what an algorithm would request every time it runs
Tests data availability and freshness from our pipeline
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path to import from database
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Change working directory to parent so imports work correctly
os.chdir(parent_dir)

from database import db_manager


def simulate_algorithm_request(ticker: str, current_time_utc: str):
    """
    Simulate what an algorithm would do when requesting data.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
        current_time_utc: Current UTC time in format '2025-06-09T14:30:00Z'
                         (This would be passed by orchestrator)
    """
    print(f"\n{'='*60}")
    print(f"ALGORITHM DATA REQUEST SIMULATION")
    print(f"{'='*60}")
    print(f"Ticker: {ticker}")
    print(f"Current Time (UTC): {current_time_utc}")
    print(f"Requesting: Last 50 bars before {current_time_utc}")
    
    # This is exactly what the algorithm would do
    bars = db_manager.get_data_for_algorithm(
        ticker=ticker,
        requirement_type='last_n_bars',
        n=50,
        before_timestamp=current_time_utc
    )
    
    print(f"\nReceived {len(bars)} bars")
    
    if len(bars) > 0:
        # Show first and last few bars
        print("\nFirst 3 bars:")
        for i, bar in enumerate(bars[:3]):
            print(f"  [{i}] {bar['timestamp']} - "
                  f"O:{bar['ohlcv']['o']:.2f} H:{bar['ohlcv']['h']:.2f} "
                  f"L:{bar['ohlcv']['l']:.2f} C:{bar['ohlcv']['c']:.2f} "
                  f"V:{bar['ohlcv']['v']}")
        
        print("\nLast 3 bars:")
        for i, bar in enumerate(bars[-3:], len(bars)-3):
            print(f"  [{i}] {bar['timestamp']} - "
                  f"O:{bar['ohlcv']['o']:.2f} H:{bar['ohlcv']['h']:.2f} "
                  f"L:{bar['ohlcv']['l']:.2f} C:{bar['ohlcv']['c']:.2f} "
                  f"V:{bar['ohlcv']['v']}")
        
        # Check data freshness
        last_bar_time = datetime.strptime(bars[-1]['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
        current_time = datetime.strptime(current_time_utc, '%Y-%m-%dT%H:%M:%SZ')
        
        time_diff = current_time - last_bar_time
        print(f"\nData Freshness Check:")
        print(f"  Last bar timestamp: {bars[-1]['timestamp']}")
        print(f"  Current time:       {current_time_utc}")
        print(f"  Delay:              {time_diff}")
        
        # Warn if data seems stale
        if time_diff > timedelta(minutes=5):
            print(f"\n⚠️  WARNING: Data appears to be {time_diff} old!")
            print("  This might indicate:")
            print("  - Alpaca free tier delay")
            print("  - Market is closed")
            print("  - Data fetch issues")
    else:
        print("\n❌ ERROR: No data received!")


def main():
    """Run various test scenarios"""
    
    # Test 1: Current time during market hours
    print("\n" + "="*60)
    print("TEST 1: Simulating algorithm request during market hours")
    print("="*60)
    
    # Get current UTC time
    now_utc = datetime.now(timezone.utc)
    current_time = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Test with a popular ticker
    simulate_algorithm_request('NVDA', current_time)
    
    # Test 2: Different ticker
    print("\n\n" + "="*60)
    print("TEST 2: Testing with different ticker (AAPL)")
    print("="*60)
    
    simulate_algorithm_request('AAPL', current_time)
    
    # Test 3: Simulate what would happen at market open
    print("\n\n" + "="*60)
    print("TEST 3: Simulating request at market open (9:31 AM EST)")
    print("="*60)
    
    # Create a time at 9:31 AM EST today
    from datetime import date
    import pytz
    
    eastern = pytz.timezone('US/Eastern')
    today = date.today()
    market_open = eastern.localize(datetime(today.year, today.month, today.day, 9, 31, 0))
    market_open_utc = market_open.astimezone(timezone.utc)
    
    simulate_algorithm_request('NVDA', market_open_utc.strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    # Test 4: Test with a ticker that might not have data
    print("\n\n" + "="*60)
    print("TEST 4: Testing with less common ticker (PLTR)")
    print("="*60)
    
    simulate_algorithm_request('PLTR', current_time)


if __name__ == "__main__":
    print("Starting Algorithm Data Request Tests...")
    print(f"Current system time: {datetime.now()}")
    print(f"Current UTC time: {datetime.now(timezone.utc)}")
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()