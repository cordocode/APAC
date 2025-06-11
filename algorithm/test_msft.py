#!/usr/bin/env python3
"""
Test with MSFT - a ticker that's NOT in the database
This will trigger auto-fetch from Alpaca
"""

import sys
sys.path.append('.')

print("=== Testing with NEW TICKER: MSFT ===\n")

# Mock get_transactions
import system_databse.system_db_manager
system_databse.system_db_manager.get_transactions = lambda x: []

# Create algorithm for MSFT
from algorithm.sma_crossover import Algorithm
algo = Algorithm("MSFT", 10000)
print(f"✓ Created algorithm for {algo.ticker} (NEW TICKER)")

# Test with March 2024 date
print(f"\n✓ Testing with date: 2024-03-15T20:00:00Z")
print("  This should trigger auto-fetch from Alpaca...\n")

try:
    action, shares = algo.run("2024-03-15T20:00:00Z", 1)
    print(f"\n✓ Algorithm returned: {action} {shares} shares")
    print("\n=== SUCCESS ===")
    print("Algorithm successfully:")
    print("1. Triggered auto-fetch for missing data")
    print("2. Stored new data in database")
    print("3. Processed the data")
    print("4. Made a trading decision")
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Now verify the data is in the database
print("\n=== Verifying MSFT data in database ===")
from database.db_manager import get_latest_price
latest = get_latest_price("MSFT")
if latest:
    print(f"✓ MSFT data confirmed in database")
    print(f"  Latest timestamp: {latest['timestamp']}")
    print(f"  Latest price: ${latest['ohlcv']['c']:.2f}")
else:
    print("✗ No MSFT data found in database")