import os
import sqlite3
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(__file__)          # …/database
DB_PATH  = os.path.join(BASE_DIR, "stocks.db")

def initialize_database():
    """Creates the stock_prices table"""

    conn = sqlite3.connect('stocks.db')
    cursor = conn.cursor()
    
    # Create table with just timestamp column - tickers added dynamically
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            minute_timestamp TEXT PRIMARY KEY
        )
    ''')
    
    # Check if table is already populated
    cursor.execute('SELECT COUNT(*) FROM stock_prices')
    if cursor.fetchone()[0] > 0:
        print("Database already initialized")
        conn.close()
        return
    
    print("Initializing database with timestamps...")
    
    # Generate all timestamps
    timestamps = []
    start_date = datetime(2018, 1, 1)
    end_date = datetime(2030, 12, 31)
    
    current_date = start_date
    while current_date <= end_date:
        # For each day, generate minutes from 9:30 AM to 4:00 PM EST
        # Just use the times directly as EST
        market_open = datetime.combine(
            current_date.date(), 
            datetime.strptime("09:30", "%H:%M").time()
        )
        market_close = datetime.combine(
            current_date.date(), 
            datetime.strptime("16:00", "%H:%M").time()
        )
        
        # Generate each minute
        current_minute = market_open
        while current_minute <= market_close:
            # Format as ISO 8601 with EST offset
            # -05:00 for EST (standard time) or -04:00 for EDT (daylight time)
            # For simplicity, using -05:00 throughout
            timestamp_str = current_minute.strftime("%Y-%m-%dT%H:%M:%S-05:00")
            timestamps.append((timestamp_str,))
            current_minute += timedelta(minutes=1)
        
        current_date += timedelta(days=1)
        
        # Progress indicator every 100 days
        if (current_date - start_date).days % 100 == 0:
            print(f"Processing {current_date.date()}...")
    
    # Bulk insert all timestamps
    print(f"Inserting {len(timestamps)} timestamps...")
    cursor.executemany('INSERT INTO stock_prices (minute_timestamp) VALUES (?)', timestamps)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized with {len(timestamps)} minute timestamps")