#!/usr/bin/env python3
"""
Database Manager - Clean Production Version
Handles all stock price database operations with market-hours-only structure
"""

import sqlite3
import json
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional

#==============================================================================
# DATABASE INITIALIZATION
#==============================================================================

def initialize_database():
    """
    Creates the market-hours-only stock_prices table using Alpaca Calendar API.
    Only contains valid market minutes from 2018-2028, no weekends/holidays.
    """
    print("🔄 Initializing database with market hours only...")
    
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
    if cursor.fetchone()[0] > 0:
        print("✅ Database already initialized")
        conn.close()
        return
    
    # Generate all valid market minutes using Alpaca Calendar
    calendar = MarketCalendar()
    market_minutes = calendar.generate_all_market_minutes(2018, 2028)
    
    # Insert all valid market minutes
    print(f"📥 Inserting {len(market_minutes):,} market minutes into database...")
    cursor.executemany(
        'INSERT INTO stock_prices (minute_timestamp) VALUES (?)',
        [(minute,) for minute in market_minutes]
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized with {len(market_minutes):,} market-only timestamps")
    print("🎯 Every row is guaranteed to be a valid market minute")

#==============================================================================
# TICKER MANAGEMENT
#==============================================================================

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
            print(f"✅ Added column for ticker: {ticker}")
            
    except Exception as e:
        print(f"❌ Error in add_ticker_if_missing: {e}")
        raise
    finally:
        conn.close()

#==============================================================================
# DATA WRITING FUNCTIONS
#==============================================================================

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
        print(f"❌ Error inserting data: {e}")
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
        
        print(f"📥 Bulk updated {rows_updated} rows for {ticker}")
        return rows_updated
        
    except Exception as e:
        print(f"❌ Error in bulk insert: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

#==============================================================================
# DATA READING FUNCTIONS
#==============================================================================

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
        print(f"❌ Error getting latest price: {e}")
        raise
    finally:
        conn.close()

#==============================================================================
# ALGORITHM DATA INTERFACE
#==============================================================================

def get_data_for_algorithm(ticker: str, requirement_type: str, **kwargs) -> List[Dict]:
    """
    Primary interface for algorithm data needs.
    Every timestamp in database is guaranteed to be a valid market minute.
    
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
        
        print(f"🔍 Getting last {n} bars for {ticker} before {before_timestamp}")
        
        # Step 1: Try to get data from database
        conn = sqlite3.connect('database/stocks.db')
        cursor = conn.cursor()
        
        query = f"""
            SELECT minute_timestamp, {ticker}
            FROM stock_prices 
            WHERE minute_timestamp <= ?
            AND {ticker} IS NOT NULL
            ORDER BY minute_timestamp DESC
            LIMIT ?
        """
        cursor.execute(query, (before_timestamp, n))
        rows = cursor.fetchall()
        conn.close()
        
        print(f"📊 Found {len(rows)} existing bars in database")
        
        # Step 2: If missing data, fetch more intelligently
        if len(rows) < n:
            missing_count = n - len(rows)
            print(f"📥 Need {missing_count} more bars, fetching from Alpaca...")
            
            # Calculate fetch range
            if rows:
                # Start from oldest existing data
                oldest_existing = rows[-1][0]  # oldest timestamp in results
                fetch_end_date = oldest_existing[:10]
            else:
                # No existing data, start from before_timestamp
                fetch_end_date = before_timestamp[:10]
            
            # Estimate how many days back to fetch (conservative approach)
            # ~390 bars per trading day, but account for weekends/holidays
            trading_days_needed = (missing_count // 300) + 3  # Conservative estimate
            calendar_days_back = trading_days_needed * 1.5  # Account for weekends/holidays
            
            fetch_start_date = (
                datetime.strptime(fetch_end_date, '%Y-%m-%d') - 
                timedelta(days=int(calendar_days_back))
            ).strftime('%Y-%m-%d')
            
            # Import and use historical fetcher
            from historical_pull import HistoricalFetcher
            fetcher = HistoricalFetcher()
            
            print(f"🔄 Auto-fetching {ticker} from {fetch_start_date} to {fetch_end_date}")
            result = fetcher.fetch_and_store(ticker, fetch_start_date, fetch_end_date)
            print(f"✅ Fetch result: {result}")
            
            # Step 3: Re-query after fetching
            conn = sqlite3.connect('database/stocks.db')
            cursor = conn.cursor()
            cursor.execute(query, (before_timestamp, n))
            rows = cursor.fetchall()
            conn.close()
            
            print(f"📈 After fetching: found {len(rows)} total bars")
        
        # Step 4: Convert to chronological order and return
        results = []
        for row in reversed(rows):  # Reverse to get oldest first
            timestamp, json_data = row
            ohlcv = json.loads(json_data)
            results.append({"timestamp": timestamp, "ohlcv": ohlcv})
        
        if len(results) < n:
            print(f"⚠️  Warning: Algorithm requested {n} bars but only {len(results)} available")
            print(f"⚠️  This may indicate new ticker or limited historical data")
        
        return results
        
    elif requirement_type == 'time_range':
        start = kwargs['start']
        end = kwargs['end']
        
        print(f"🔍 Getting time range data for {ticker}: {start} to {end}")
        
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
            print(f"📥 Missing data: have {len(rows)}, expected {expected_count}")
            
            # Fetch missing data for the date range
            start_date = start[:10]
            end_date = end[:10]
            
            from historical_pull import HistoricalFetcher
            fetcher = HistoricalFetcher()
            
            print(f"🔄 Fetching missing {ticker} data from {start_date} to {end_date}")
            result = fetcher.fetch_and_store(ticker, start_date, end_date)
            print(f"✅ Fetch result: {result}")
            
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
        
        print(f"📊 Returning {len(results)} bars for time range")
        return results
    
    else:
        raise ValueError(f"Unknown requirement type: {requirement_type}")

#==============================================================================
# DATABASE UTILITIES
#==============================================================================

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
        print(f"❌ Error getting database stats: {e}")
        raise
    finally:
        conn.close()