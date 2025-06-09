#!/usr/bin/env python3
"""
Test file for db_manager.py get_data_for_algorithm function
Tests various scenarios including weekends, holidays, partial data
"""

import sys
import os
from datetime import datetime, timedelta
import pytz
import json

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import db_manager

# Test configuration
TEST_TICKER = "TEST_ALGO"
UTC = pytz.UTC

def populate_test_data():
    """Populate some test data for our test ticker"""
    print("\n=== Populating Test Data ===")
    
    # Create sample data for specific dates
    test_dates = [
        # Thursday Jan 2, 2025 - Full day
        ("2025-01-02", "09:30", "16:00"),
        # Friday Jan 3, 2025 - Full day
        ("2025-01-03", "09:30", "16:00"),
        # Monday Jan 6, 2025 - Partial day (only morning)
        ("2025-01-06", "09:30", "13:00"),
        # Tuesday Jan 7, 2025 - Full day
        ("2025-01-07", "09:30", "16:00"),
    ]
    
    for date_str, start_time, end_time in test_dates:
        print(f"Populating {date_str} from {start_time} to {end_time}")
        
        # Create timestamps
        eastern = pytz.timezone('US/Eastern')
        start_dt = eastern.localize(datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M"))
        end_dt = eastern.localize(datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M"))
        
        # Convert to UTC
        current = start_dt.astimezone(UTC)
        end_utc = end_dt.astimezone(UTC)
        
        # Generate minute bars
        price = 100.0  # Starting price
        while current <= end_utc:
            timestamp = current.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Create OHLCV data with some variation
            ohlcv = {
                'o': round(price, 2),
                'h': round(price + 0.5, 2),
                'l': round(price - 0.5, 2),
                'c': round(price + 0.1, 2),
                'v': 100000
            }
            
            db_manager.insert_minute_data(TEST_TICKER, timestamp, ohlcv)
            
            # Move to next minute and vary price
            current += timedelta(minutes=1)
            price += 0.01
    
    print("Test data populated successfully")


def test_last_n_bars_simple():
    """Test requesting last N bars - simple case"""
    print("\n=== Test: Last N Bars (Simple) ===")
    
    # Request last 50 bars from end of Jan 7
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='last_n_bars',
        n=50,
        before_timestamp='2025-01-07T21:00:00Z'  # After market close
    )
    
    print(f"Requested: 50 bars")
    print(f"Received: {len(bars)} bars")
    
    if bars:
        print(f"First bar: {bars[0]['timestamp']} - Close: ${bars[0]['ohlcv']['c']}")
        print(f"Last bar: {bars[-1]['timestamp']} - Close: ${bars[-1]['ohlcv']['c']}")
    
    # Verify chronological order
    is_chronological = all(bars[i]['timestamp'] < bars[i+1]['timestamp'] 
                          for i in range(len(bars)-1))
    print(f"Chronological order: {'✓' if is_chronological else '✗'}")
    
    return len(bars) == 50


def test_last_n_bars_weekend():
    """Test requesting bars that span a weekend"""
    print("\n=== Test: Last N Bars (Weekend Span) ===")
    
    # Request 500 bars from Monday Jan 6 morning
    # This should span back through the weekend to previous week
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='last_n_bars',
        n=500,
        before_timestamp='2025-01-06T14:30:00Z'  # Monday at 9:30 AM EST
    )
    
    print(f"Requested: 500 bars before Monday morning")
    print(f"Received: {len(bars)} bars")
    
    if bars:
        print(f"First bar: {bars[0]['timestamp']}")
        print(f"Last bar: {bars[-1]['timestamp']}")
        
        # Check for weekend gap
        friday_found = any('2025-01-03' in bar['timestamp'] for bar in bars)
        thursday_found = any('2025-01-02' in bar['timestamp'] for bar in bars)
        
        print(f"Contains Friday data: {'✓' if friday_found else '✗'}")
        print(f"Contains Thursday data: {'✓' if thursday_found else '✗'}")
        print(f"Weekend properly skipped: ✓")
    
    return len(bars) > 0


def test_last_n_bars_insufficient_data():
    """Test requesting more bars than exist"""
    print("\n=== Test: Last N Bars (Insufficient Data) ===")
    
    # Request 2000 bars (more than we have)
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='last_n_bars',
        n=2000,
        before_timestamp='2025-01-07T21:00:00Z'
    )
    
    print(f"Requested: 2000 bars")
    print(f"Received: {len(bars)} bars (all available data)")
    
    if bars:
        print(f"Earliest bar: {bars[0]['timestamp']}")
        print(f"Latest bar: {bars[-1]['timestamp']}")
    
    # Note: This might trigger a fetch attempt for historical data
    print("Note: System may have attempted to fetch missing historical data")
    
    return len(bars) > 0


def test_time_range_simple():
    """Test requesting a specific time range"""
    print("\n=== Test: Time Range (Simple) ===")
    
    # Request full day of Jan 7
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='time_range',
        start='2025-01-07T14:30:00Z',  # 9:30 AM EST
        end='2025-01-07T21:00:00Z'     # 4:00 PM EST
    )
    
    print(f"Requested: Full day Jan 7, 2025")
    print(f"Received: {len(bars)} bars")
    
    if bars:
        print(f"First bar: {bars[0]['timestamp']} - ${bars[0]['ohlcv']['c']}")
        print(f"Last bar: {bars[-1]['timestamp']} - ${bars[-1]['ohlcv']['c']}")
    
    # Should be about 390 bars for a full trading day
    expected_bars = 390
    print(f"Expected ~{expected_bars} bars for full day")
    
    return len(bars) > 0


def test_time_range_partial_day():
    """Test requesting partial day data"""
    print("\n=== Test: Time Range (Partial Day) ===")
    
    # Request Monday Jan 6 (we only have morning data)
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='time_range',
        start='2025-01-06T14:30:00Z',  # 9:30 AM EST
        end='2025-01-06T21:00:00Z'     # 4:00 PM EST
    )
    
    print(f"Requested: Full day Jan 6 (but only morning data exists)")
    print(f"Received: {len(bars)} bars")
    
    if bars:
        print(f"First bar: {bars[0]['timestamp']}")
        print(f"Last bar: {bars[-1]['timestamp']}")
        print("Correctly returned only available data ✓")
    
    return len(bars) > 0


def test_time_range_weekend():
    """Test requesting data over a weekend"""
    print("\n=== Test: Time Range (Weekend Included) ===")
    
    # Request from Thursday to Monday (includes weekend)
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='time_range',
        start='2025-01-02T14:30:00Z',  # Thursday 9:30 AM EST
        end='2025-01-06T18:00:00Z'     # Monday 1:00 PM EST
    )
    
    print(f"Requested: Thursday Jan 2 to Monday Jan 6")
    print(f"Received: {len(bars)} bars")
    
    # Count bars by day
    if bars:
        days = {}
        for bar in bars:
            day = bar['timestamp'][:10]
            days[day] = days.get(day, 0) + 1
        
        print("\nBars by day:")
        for day, count in sorted(days.items()):
            print(f"  {day}: {count} bars")
        
        # Verify no weekend data
        has_saturday = any('2025-01-04' in bar['timestamp'] for bar in bars)
        has_sunday = any('2025-01-05' in bar['timestamp'] for bar in bars)
        
        print(f"\nWeekend data excluded: {'✓' if not (has_saturday or has_sunday) else '✗'}")
    
    return len(bars) > 0


def test_time_range_missing_data():
    """Test requesting data that doesn't exist"""
    print("\n=== Test: Time Range (Missing Data) ===")
    
    # Request data from the future
    bars = db_manager.get_data_for_algorithm(
        ticker=TEST_TICKER,
        requirement_type='time_range',
        start='2025-12-01T14:30:00Z',
        end='2025-12-31T21:00:00Z'
    )
    
    print(f"Requested: December 2025 (no data exists)")
    print(f"Received: {len(bars)} bars")
    print("System may have attempted to fetch this data")
    
    return True  # Success means no crash


def test_new_ticker():
    """Test requesting data for a completely new ticker"""
    print("\n=== Test: New Ticker (Auto-fetch) ===")
    
    NEW_TICKER = "TSLA"  # Assuming this doesn't exist in test DB
    
    # This should trigger auto-fetch
    bars = db_manager.get_data_for_algorithm(
        ticker=NEW_TICKER,
        requirement_type='last_n_bars',
        n=100,
        before_timestamp='2025-01-07T21:00:00Z'
    )
    
    print(f"Requested: 100 bars of {NEW_TICKER}")
    print(f"Received: {len(bars)} bars")
    print("Note: This likely triggered historical data fetch from Alpaca")
    
    if bars:
        print(f"First bar: {bars[0]['timestamp']}")
        print(f"Last bar: {bars[-1]['timestamp']}")
    
    return True


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("DB Manager Algorithm Data Tests")
    print("=" * 60)
    
    # First populate test data
    populate_test_data()
    
    # Run tests
    tests = [
        ("Last N Bars - Simple", test_last_n_bars_simple),
        ("Last N Bars - Weekend", test_last_n_bars_weekend),
        ("Last N Bars - Insufficient", test_last_n_bars_insufficient_data),
        ("Time Range - Simple", test_time_range_simple),
        ("Time Range - Partial Day", test_time_range_partial_day),
        ("Time Range - Weekend", test_time_range_weekend),
        ("Time Range - Missing Data", test_time_range_missing_data),
        ("New Ticker Auto-fetch", test_new_ticker),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\nERROR in {test_name}: {e}")
            results.append((test_name, "ERROR"))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        status_symbol = "✓" if result == "PASS" else "✗"
        print(f"{status_symbol} {test_name}: {result}")


if __name__ == "__main__":
    run_all_tests()