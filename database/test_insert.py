# test_insert.py
from db_manager import insert_minute_data

print("Testing insert_minute_data with UTC keys...")

rows1 = insert_minute_data(
    "NVDA",
    "2024-01-02T14:30:00Z",           # 09:30 EST in UTC
    {"o": 450.23, "h": 451.00, "l": 449.50, "c": 450.75, "v": 1_000_000}
)
print(f"First insert → {rows1} row(s) updated")

rows2 = insert_minute_data(
    "NVDA",
    "2024-01-02T14:31:00Z",
    {"o": 450.75, "h": 451.20, "l": 450.60, "c": 451.10, "v": 750_000}
)
print(f"Second insert → {rows2} row(s) updated")

print("✓ Test complete")
