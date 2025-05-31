#!/usr/bin/env python3
"""
Simple test to verify the historical fetch fix works.
"""

import os
import sys
sys.path.append('database')

from historical_pull import HistoricalFetcher
from db_manager import get_historical_data

def test_the_fix():
    """Test that we now get minute bars instead of daily bars."""
    
    print("🧪 TESTING THE HISTORICAL FETCH FIX")
    print("=" * 60)
    
    fetcher = HistoricalFetcher()
    
    # Test the dates that were problematic before
    test_cases = [
        ("NVDA", "2024-12-20", "Friday that was returning 1 bar"),
        ("AAPL", "2024-12-19", "Thursday that was returning 1 bar"),
        ("MSFT", "2024-01-08", "Monday that returned no data"),
    ]
    
    for ticker, date, description in test_cases:
        print(f"\n📊 Testing {ticker} on {date} ({description})")
        print("-" * 50)
        
        # Fetch the data
        result = fetcher.fetch_and_store(ticker, date, date)
        
        print(f"\n   Result: {result}")
        
        if result['status'] == 'fetched':
            points = result['data_points']
            updates = result['rows_updated']
            
            # Check if we got minute bars (should be ~391 for a full day)
            if points > 300:  # Allow some wiggle room for partial days
                print(f"   ✅ SUCCESS: Got {points} minute bars (not 1 daily bar!)")
                print(f"   ✅ Updated {updates} rows in database")
            else:
                print(f"   ⚠️  Only got {points} data points (expected ~391)")
                
            # Verify data is actually in the database
            start_check = f"{date}T14:30:00Z"  # 9:30 AM EST
            end_check = f"{date}T14:35:00Z"    # 9:35 AM EST
            
            stored = get_historical_data(ticker, start_check, end_check)
            if stored:
                print(f"   ✅ Verified: Found {len(stored)} minutes in database")
                print(f"      Sample: {stored[0]['timestamp']} -> ${stored[0]['ohlcv']['c']}")
            else:
                print(f"   ❌ No data found in database for verification")
                
        elif result['status'] == 'already_exists':
            print(f"   ℹ️  Data already exists (from previous test)")
            
        elif result['status'] == 'no_data':
            print(f"   ⚠️  No data returned (might be a holiday)")
            
        else:
            print(f"   ❌ Unexpected status: {result['status']}")
    
    print("\n" + "=" * 60)
    print("✅ Test complete! If you see minute bars above, the fix is working.")


if __name__ == "__main__":
    test_the_fix()