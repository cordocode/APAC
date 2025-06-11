#!/usr/bin/env python3
"""
Simulate exactly what the orchestrator will do:
1. Call algorithm.run()
2. Algorithm gets data from database
3. Algorithm returns decision

Run from /APAC/: python3 algorithm/test_orchestrator_sim.py
"""

import sys
sys.path.append('.')

print("=== Simulating Orchestrator ===\n")

# 1. Orchestrator creates algorithm instance
print("1. Creating algorithm instance...")
from algorithm.sma_crossover import Algorithm
algo = Algorithm("AAPL", 10000)
print(f"   ✓ Created {algo.ticker} algorithm with ${algo.initial_capital}\n")

# 2. Orchestrator calls run() with current time and algo_id
print("2. Calling algorithm.run()...")
test_timestamp = "2024-01-31T20:00:00Z"
test_algo_id = 1

# Mock get_transactions to return empty list (no prior trades)
import system_databse.system_db_manager
system_databse.system_db_manager.get_transactions = lambda algo_id: []

try:
    # This is exactly what orchestrator will do
    action, shares = algo.run(test_timestamp, test_algo_id)
    
    print(f"   ✓ Algorithm returned: {action} {shares} shares\n")
    
    # 3. Verify the response format
    print("3. Verifying response format...")
    assert action in ['buy', 'sell', 'hold'], f"Invalid action: {action}"
    assert isinstance(shares, (int, float)), f"Invalid shares type: {type(shares)}"
    assert shares >= 0, f"Negative shares: {shares}"
    print("   ✓ Response format is correct\n")
    
    print("=== TEST PASSED ===")
    print("Algorithm can receive data and return valid trading decisions")
    
except Exception as e:
    print(f"   ✗ Algorithm crashed: {str(e)}\n")
    print("=== TEST FAILED ===")
    print("Fix needed in algorithm before building orchestrator")
    
    # Show exactly where it failed
    import traceback
    print("\nError details:")
    traceback.print_exc()