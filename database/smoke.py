from db_manager import initialize_database, add_ticker_if_missing

# Initialize the database (creates table with timestamps)
initialize_database()

# Add a ticker column
add_ticker_if_missing("NVDA")

print("✓ DB ready")