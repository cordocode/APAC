import sqlite3
import json
from datetime import datetime, timedelta
import pytz

def initialize_database():
    """
    Creates the stock_prices table if it doesn't exist and populates 
    with minute timestamps from 2018-2030 between 9:30 AM - 4:00 PM EST.
    All ticker columns start as NULL.
    Only needs to run once ever.
    """
    conn = sqlite3.connect('database/stocks.db')
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

    import pytz
    eastern = pytz.timezone('US/Eastern')
    utc = pytz.UTC
    
    start_year = 2018
    end_year = 2030
    timestamps = []
    
    current_date = datetime(start_year, 1, 2)  # first trading day in 2018
    end_date = datetime(end_year, 12, 31)

    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:
            # Market hours in EST
            market_open_est = eastern.localize(
                current_date.replace(hour=9, minute=30, second=0, microsecond=0)
            )
            market_close_est = eastern.localize(
                current_date.replace(hour=16, minute=0, second=0, microsecond=0)
            )

            # Convert to UTC and walk minute-by-minute
            current_time = market_open_est.astimezone(utc)
            market_close_utc = market_close_est.astimezone(utc)
            while current_time <= market_close_utc:
                # Store key as canonical UTC with trailing Z
                timestamps.append((current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),))
                current_time += timedelta(minutes=1)
        
        current_date += timedelta(days=1)
    
    cursor.executemany('INSERT INTO stock_prices (minute_timestamp) VALUES (?)', timestamps)
    conn.commit()
    conn.close()
    print(f"Inserted {len(timestamps)} rows.")


def add_ticker_if_missing(ticker):
    """
    Checks if ticker column exists in table and adds it if missing.
    Called automatically by other functions before any ticker operation.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'NVDA', 'AAPL')
    
    Returns:
        None - just ensures column exists
    """
    # Sanitize ticker to prevent SQL injection
    # Only allow alphanumeric characters and underscores
    if not ticker.replace('_', '').isalnum():
        raise ValueError(f"Invalid ticker symbol: {ticker}")
    
    # Connect to database
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Get all column info from the table
        cursor.execute("PRAGMA table_info(stock_prices)")
        columns = cursor.fetchall()
        
        # Check if ticker column already exists
        # PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
        column_names = [column[1] for column in columns]
        
        if ticker not in column_names:
            # Add the column as TEXT type (for JSON storage)
            alter_query = f"ALTER TABLE stock_prices ADD COLUMN {ticker} TEXT"
            cursor.execute(alter_query)
            conn.commit()
            print(f"Added column for ticker: {ticker}")
        # If column exists, do nothing (silent success)
            
    except Exception as e:
        print(f"Error in add_ticker_if_missing: {e}")
        raise
    finally:
        conn.close()

def insert_minute_data(ticker, timestamp, ohlcv_dict):
    """
    Insert a single minute of data. Works for both historical and realtime.
    
    Args:
        ticker: 'NVDA'
        timestamp: '2024-01-02T09:30:00'
        ohlcv_dict: {'o': 450.23, 'h': 451.00, 'l': 449.50, 'c': 450.75, 'v': 1000000}
    """
    add_ticker_if_missing(ticker)
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Convert dict to JSON string
        ohlcv_json = json.dumps(ohlcv_dict)
        
        # Update the single row
        query = f"UPDATE stock_prices SET {ticker} = ? WHERE minute_timestamp = ?"
        cursor.execute(query, (ohlcv_json, timestamp))
        
        conn.commit()
        return cursor.rowcount
        
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_historical_data(ticker, start_date, end_date):
    """
    Fetches all non-NULL data in date range from our database.
    Returns array of {timestamp, ohlcv} objects.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
        start_date: Start timestamp (e.g., '2024-01-02T14:30:00Z')
        end_date: End timestamp (e.g., '2024-01-02T21:00:00Z')
    
    Returns:
        List of dicts: [{"timestamp": "...", "ohlcv": {...}}, ...]
    """
    add_ticker_if_missing(ticker)
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Get all non-NULL data in the range
        query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE minute_timestamp >= ? 
            AND minute_timestamp <= ?
            AND {ticker} IS NOT NULL
            ORDER BY minute_timestamp
        """
        
        cursor.execute(query, (start_date, end_date))
        
        # Convert to list of dicts
        results = []
        for row in cursor.fetchall():
            timestamp, json_data = row
            ohlcv = json.loads(json_data)  # Parse JSON string back to dict
            results.append({
                "timestamp": timestamp,
                "ohlcv": ohlcv
            })
        
        return results
        
    except Exception as e:
        print(f"Error getting historical data: {e}")
        raise
    finally:
        conn.close()


def get_latest_price(ticker):
    """
    Returns most recent non-NULL entry for ticker.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
    
    Returns:
        Dict with {timestamp, ohlcv} or None if no data
    """
    add_ticker_if_missing(ticker)
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Get the most recent non-NULL entry
        query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE {ticker} IS NOT NULL
            ORDER BY minute_timestamp DESC
            LIMIT 1
        """
        
        cursor.execute(query)
        row = cursor.fetchone()
        
        if row:
            timestamp, json_data = row
            ohlcv = json.loads(json_data)
            return {
                "timestamp": timestamp,
                "ohlcv": ohlcv
            }
        else:
            return None
            
    except Exception as e:
        print(f"Error getting latest price: {e}")
        raise
    finally:
        conn.close()


def insert_historical_data(ticker, data_array):
    """
    Bulk insert for efficiency with historical data.
    Takes array of {timestamp, ohlcv} objects and updates rows with JSON strings.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
        data_array: List of dicts with 'timestamp' and 'ohlcv' keys
    
    Returns:
        int: Number of rows updated
    """
    add_ticker_if_missing(ticker)
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Prepare data for bulk update
        update_data = []
        for item in data_array:
            timestamp = item['timestamp']
            ohlcv_json = json.dumps(item['ohlcv'])
            update_data.append((ohlcv_json, timestamp))
        
        # Bulk update
        query = (
        f"UPDATE stock_prices "
        f"SET {ticker} = ? "
        f"WHERE minute_timestamp = ? "
        f"  AND {ticker} IS NULL"
        )
        cursor.executemany(query, update_data)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        print(f"Bulk updated {rows_updated} rows for {ticker}")
        return rows_updated
        
    except Exception as e:
        print(f"Error in bulk insert: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def check_data_exists(ticker, start_date, end_date):
    """
    Check if data exists for a ticker in the given date range.
    Returns list of date ranges where data is missing (NULL).
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
        start_date: Start timestamp (e.g., '2024-01-02T14:30:00Z')
        end_date: End timestamp (e.g., '2024-01-02T21:00:00Z')
    
    Returns:
        Empty list if all data exists, or
        List with missing range: [{"start": start_date, "end": end_date}]
    """
    add_ticker_if_missing(ticker)
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Count NULL values in the date range
        query = f"""
            SELECT COUNT(*) 
            FROM stock_prices 
            WHERE minute_timestamp >= ? 
            AND minute_timestamp <= ?
            AND {ticker} IS NULL
        """
        
        cursor.execute(query, (start_date, end_date))
        null_count = cursor.fetchone()[0]
        
        if null_count == 0:
            # All data exists
            return []
        else:
            # Some or all data is missing
            # For simplicity, return the full range as missing
            # (In a more complex implementation, you might return specific gaps)
            return [{"start": start_date, "end": end_date}]
            
    except Exception as e:
        print(f"Error checking data existence: {e}")
        raise
    finally:
        conn.close()