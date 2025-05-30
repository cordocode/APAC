# test_db_functions.py
from db_manager import (
    insert_minute_data, 
    check_data_exists, 
    get_historical_data, 
    get_latest_price,
    insert_historical_data
)

print("Testing database functions...")

# 1. Test single insert
print("\n1. Testing single insert...")
result = insert_minute_data(
    "AAPL", 
    "2024-01-03T14:30:00Z",
    {"o": 185.50, "h": 186.00, "l": 185.25, "c": 185.75, "v": 1500000}
)
print(f"   Inserted {result} row")

# 2. Test bulk insert
print("\n2. Testing bulk insert...")
bulk_data = [
    {
        "timestamp": "2024-01-03T14:31:00Z",
        "ohlcv": {"o": 185.75, "h": 186.10, "l": 185.70, "c": 186.00, "v": 1200000}
    },
    {
        "timestamp": "2024-01-03T14:32:00Z",
        "ohlcv": {"o": 186.00, "h": 186.25, "l": 185.90, "c": 186.15, "v": 1100000}
    }
]
rows = insert_historical_data("AAPL", bulk_data)
print(f"   Bulk inserted {rows} rows")

# 3. Test check_data_exists
print("\n3. Testing check_data_exists...")
missing = check_data_exists("AAPL", "2024-01-03T14:30:00Z", "2024-01-03T14:35:00Z")
print(f"   Missing timestamps: {len(missing)} (showing first 3: {missing[:3]})")

# 4. Test get_historical_data
print("\n4. Testing get_historical_data...")
data = get_historical_data("AAPL", "2024-01-03T14:30:00Z", "2024-01-03T14:35:00Z")
print(f"   Retrieved {len(data)} data points")
if data:
    print(f"   First entry: {data[0]}")

# 5. Test get_latest_price
print("\n5. Testing get_latest_price...")
latest = get_latest_price("AAPL")
if latest:
    print(f"   Latest price: {latest['ohlcv']['c']} at {latest['timestamp']}")
else:
    print("   No data found")

print("\n✓ All tests complete!")