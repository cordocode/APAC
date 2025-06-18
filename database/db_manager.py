"""
################################################################################
# FILE: db_manager.py
# PURPOSE: Database manager for stock price operations with market-hours-only structure
################################################################################
"""

import sqlite3
import json
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# DATABASE INITIALIZATION
################################################################################

def initialize_database():
    """
    Creates the market-hours-only stock_prices table using Alpaca Calendar API.
    Only contains valid market minutes from 2018-2028, no weekends/holidays.
    """
    print("[INFO] Initializing stock price database")
    
    # Import calendar manager
    from calendar_manager import MarketCalendar
    
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
    row_count = cursor.fetchone()[0]
    if row_count > 0:
        print(f"[INFO] Database already initialized with {row_count:,} market minutes")
        conn.close()
        return
    
    # Generate all valid market minutes using Alpaca Calendar
    calendar = MarketCalendar()
    market_minutes = calendar.generate_all_market_minutes(2018, 2028)
    
    # Insert all valid market minutes
    cursor.executemany(
        'INSERT INTO stock_prices (minute_timestamp) VALUES (?)',
        [(minute,) for minute in market_minutes]
    )
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Database initialized with {len(market_minutes):,} market minutes (2018-2028)")


################################################################################
# TICKER MANAGEMENT
################################################################################

def add_ticker_if_missing(ticker: str):
    """
    Checks if ticker column exists in table and adds it if missing.
    Called automatically by other functions before any ticker operation.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')
    """
    # Sanitize ticker to prevent SQL injection
    if not ticker.replace('_', '').isalnum():
        raise ValueError(f"Invalid ticker symbol: {ticker}")
    
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Get all column info from the table
        cursor.execute("PRAGMA table_info(stock_prices)")
        columns = cursor.fetchall()
        
        # Check if ticker column already exists
        column_names = [column[1] for column in columns]
        
        if ticker not in column_names:
            # Add the column as TEXT type (for JSON storage)
            alter_query = f"ALTER TABLE stock_prices ADD COLUMN {ticker} TEXT"
            cursor.execute(alter_query)
            conn.commit()
            print(f"[OK] Added column for ticker: {ticker}")
            
    except Exception as e:
        print(f"[ERROR] Failed to add column for {ticker}: {str(e)}")
        raise
    finally:
        conn.close()


################################################################################
# DATA WRITING FUNCTIONS
################################################################################

def insert_minute_data(ticker: str, timestamp: str, ohlcv_dict: Dict):
    """
    Insert a single minute of data. Works for both historical and realtime.
    
    Args:
        ticker: 'NVDA'
        timestamp: '2024-01-02T09:30:00Z'
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
        print(f"[ERROR] Failed to insert {ticker} data at {timestamp}: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_historical_data(ticker: str, data_array: List[Dict]):
    """
    Bulk insert for efficiency with historical data.
    Takes array of {timestamp, ohlcv} objects and updates rows with JSON strings.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA')
        data_array: List of dicts with 'timestamp' and 'ohlcv' keys
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
        
        # Bulk update - only update NULL values to avoid overwriting existing data
        query = f"""
            UPDATE stock_prices 
            SET {ticker} = ? 
            WHERE minute_timestamp = ? 
            AND {ticker} IS NULL
        """
        cursor.executemany(query, update_data)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        if rows_updated > 0:
            print(f"[INFO] Stored {rows_updated} historical bars for {ticker}")
        
        return rows_updated
        
    except Exception as e:
        print(f"[ERROR] Failed to store historical data for {ticker}: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


################################################################################
# DATA READING FUNCTIONS
################################################################################

def get_latest_price(ticker: str) -> Optional[Dict]:
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
        print(f"[ERROR] Failed to get latest price for {ticker}: {str(e)}")
        raise
    finally:
        conn.close()


################################################################################
# ALGORITHM DATA INTERFACE
################################################################################

def get_data_for_algorithm(ticker: str, requirement_type: str, **kwargs) -> List[Dict]:
    """
    Primary interface for algorithm data needs.
    FIXED: Always returns the most recent N bars relative to requested time.
    
    Args:
        ticker: Stock symbol
        requirement_type: Either 'last_n_bars' or 'time_range'
        **kwargs: 
            For 'last_n_bars': n=200, before_timestamp=None
            For 'time_range': start='2024-01-02T09:30:00Z', end='2024-01-02T20:59:00Z'
    
    Returns:
        List of bars with {timestamp, ohlcv} dicts in chronological order
    """
    add_ticker_if_missing(ticker)
    
    if requirement_type == 'last_n_bars':
        n = kwargs['n']
        before_timestamp = kwargs.get('before_timestamp')
        
        if before_timestamp is None:
            before_timestamp = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        conn = sqlite3.connect('database/stocks.db')
        cursor = conn.cursor()
        
        # Step 1: Get the N most recent timestamps before the requested time
        # This ensures we're looking at the RIGHT time range, not just any old data
        timestamp_query = """
            SELECT minute_timestamp
            FROM stock_prices 
            WHERE minute_timestamp <= ?
            ORDER BY minute_timestamp DESC
            LIMIT ?
        """
        cursor.execute(timestamp_query, (before_timestamp, n))
        timestamp_rows = cursor.fetchall()
        
        if not timestamp_rows:
            print(f"[WARN] No timestamps found for {ticker} before {before_timestamp}")
            conn.close()
            return []
        
        # Get the range we're looking at
        timestamps = [row[0] for row in timestamp_rows]
        newest_timestamp = timestamps[0]
        oldest_timestamp = timestamps[-1]
        
        # Step 2: Check which of these timestamps have data
        placeholders = ','.join(['?' for _ in timestamps])
        data_check_query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE minute_timestamp IN ({placeholders})
            ORDER BY minute_timestamp DESC
        """
        cursor.execute(data_check_query, timestamps)
        data_rows = cursor.fetchall()
        
        # Count how many have data vs NULL
        non_null_count = sum(1 for row in data_rows if row[1] is not None)
        null_count = len(timestamps) - non_null_count
        
        # Step 3: If ANY data is missing, fetch it
        if null_count > 0 or non_null_count < n:
            print(f"[INFO] Missing {null_count} bars for {ticker} in range {oldest_timestamp[:10]} to {newest_timestamp[:10]}")
            
            # Calculate date range to fetch
            fetch_start_date = oldest_timestamp[:10]
            fetch_end_date = newest_timestamp[:10]
            
            # If dates are the same, extend the range
            if fetch_start_date == fetch_end_date:
                # Go back one more day to ensure we get enough data
                fetch_start_dt = datetime.strptime(fetch_start_date, '%Y-%m-%d') - timedelta(days=1)
                fetch_start_date = fetch_start_dt.strftime('%Y-%m-%d')
            
            conn.close()  # Close before fetching
            
            from database.historical_pull import HistoricalFetcher
            fetcher = HistoricalFetcher()
            result = fetcher.fetch_and_store(ticker, fetch_start_date, fetch_end_date)
            
            # Reconnect after fetch
            conn = sqlite3.connect('database/stocks.db')
            cursor = conn.cursor()
        
        # Step 4: Get the final data
        final_query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE minute_timestamp IN ({placeholders})
            AND {ticker} IS NOT NULL
            ORDER BY minute_timestamp DESC
        """
        cursor.execute(final_query, timestamps)
        final_rows = cursor.fetchall()
        conn.close()
        
        # Convert to chronological order and return
        results = []
        for row in reversed(final_rows):  # Reverse to get oldest first
            timestamp, json_data = row
            if json_data:  # Only include non-NULL data
                ohlcv = json.loads(json_data)
                results.append({"timestamp": timestamp, "ohlcv": ohlcv})
        
        if not results:
            print(f"[WARN] No data available for {ticker} after attempting fetch")
        
        return results
        
    elif requirement_type == 'time_range':
        start = kwargs['start']
        end = kwargs['end']
        
        # Simple range query - non-market times don't exist in DB
        conn = sqlite3.connect('database/stocks.db')
        cursor = conn.cursor()
        
        query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE minute_timestamp >= ?
            AND minute_timestamp <= ?
            AND {ticker} IS NOT NULL
            ORDER BY minute_timestamp
        """
        cursor.execute(query, (start, end))
        rows = cursor.fetchall()
        
        # Check if we need to fetch missing data
        expected_query = """
            SELECT COUNT(*) 
            FROM stock_prices 
            WHERE minute_timestamp >= ? 
            AND minute_timestamp <= ?
        """
        cursor.execute(expected_query, (start, end))
        expected_count = cursor.fetchone()[0]
        conn.close()
        
        if len(rows) < expected_count:
            actual_pct = (len(rows) / expected_count * 100) if expected_count > 0 else 0
            print(f"[INFO] Missing data for {ticker}: have {actual_pct:.1f}% of expected bars in range")
            
            # Fetch missing data for the date range
            start_date = start[:10]
            end_date = end[:10]
            
            from database.historical_pull import HistoricalFetcher
            fetcher = HistoricalFetcher()
            
            result = fetcher.fetch_and_store(ticker, start_date, end_date)
            
            # Re-query after fetch
            conn = sqlite3.connect('database/stocks.db')
            cursor = conn.cursor()
            cursor.execute(query, (start, end))
            rows = cursor.fetchall()
            conn.close()
        
        # Convert to standard format
        results = []
        for row in rows:
            timestamp, json_data = row
            ohlcv = json.loads(json_data)
            results.append({"timestamp": timestamp, "ohlcv": ohlcv})
        
        return results
    
    else:
        raise ValueError(f"Unknown requirement type: {requirement_type}")


################################################################################
# DATABASE UTILITIES
################################################################################

def get_database_stats() -> Dict:
    """
    Get statistics about the database content.
    Useful for monitoring and debugging.
    
    Returns:
        Dict with database statistics
    """
    conn = sqlite3.connect('database/stocks.db')
    cursor = conn.cursor()
    
    try:
        # Get total timestamps
        cursor.execute("SELECT COUNT(*) FROM stock_prices")
        total_timestamps = cursor.fetchone()[0]
        
        # Get table schema to find all ticker columns
        cursor.execute("PRAGMA table_info(stock_prices)")
        columns = cursor.fetchall()
        ticker_columns = [col[1] for col in columns if col[1] != 'minute_timestamp']
        
        # Get data completion for each ticker
        ticker_stats = {}
        for ticker in ticker_columns:
            cursor.execute(f"SELECT COUNT(*) FROM stock_prices WHERE {ticker} IS NOT NULL")
            data_count = cursor.fetchone()[0]
            completion_rate = (data_count / total_timestamps * 100) if total_timestamps > 0 else 0
            ticker_stats[ticker] = {
                "data_points": data_count,
                "completion_rate": round(completion_rate, 2)
            }
        
        # Get date range
        cursor.execute("SELECT MIN(minute_timestamp), MAX(minute_timestamp) FROM stock_prices")
        min_date, max_date = cursor.fetchone()
        
        return {
            "total_timestamps": total_timestamps,
            "date_range": {"start": min_date, "end": max_date},
            "ticker_count": len(ticker_columns),
            "tickers": ticker_stats
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get database statistics: {str(e)}")
        raise
    finally:
        conn.close()