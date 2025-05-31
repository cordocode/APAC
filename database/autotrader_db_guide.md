# Auto Trader Database Implementation Guide - Revised

## Overview
A SQLite database system for automated stock trading that stores historical and real-time stock data. The database runs independently and provides data to trading algorithms.

## Recent Implementation Updates

### UTC Timestamp Conversion (CRITICAL FIX)
- **Problem**: Initial implementation stored Eastern time timestamps, but Alpaca sends UTC
- **Solution**: Database now stores all timestamps in UTC format with 'Z' suffix
- **Format**: `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2024-01-02T14:30:00Z`)
- **Impact**: Ensures timestamp matching works correctly for both historical and real-time data

### Optimized Database Functions
1. **insert_historical_data()** - Now includes `AND {ticker} IS NULL` in UPDATE query to skip already-filled rows
2. **check_data_exists()** - Simplified to return full date ranges instead of individual timestamps for efficient bulk fetching

### New Implementation Files
- **historical_pull.py** - HistoricalFetcher class using alpaca-py's StockHistoricalDataClient
- **realtime_pull.py** - RealtimeStreamer class using alpaca-py's StockDataStream

## Data Flow - Order of Operations

### Path 1: Historical Data Request
```
Algorithm requests data → DB Service checks if exists → 
    If NO: → Alpaca Historical API → Format data → Store in DB → Return to Algorithm
    If YES: → Fetch from DB → Return to Algorithm
```

### Path 2: Real-time Data Flow
```
WebSocket receives data → DB Service formats → Store in DB
Algorithm polls DB for latest data when needed
```

### Path 3: New Ticker Addition
```
Algorithm requests ticker not in DB → DB Service detects missing column → 
    Automatically adds column → Fetches historical data → Stores → Returns data
```

## Database Schema

### Table Structure
```sql
CREATE TABLE stock_prices (
    minute_timestamp TEXT PRIMARY KEY,
    NVDA TEXT,
    AAPL TEXT,
    TSLA TEXT
);
```

### Key Design Decisions

1. **Pre-populated Timestamps**
   - Every minute from 9:30 AM to 4:00 PM EST (stored as UTC)
   - Every calendar day from 2018-01-01 to 2030-12-31
   - ~1.3 million rows
   - **ALL values start as NULL** until data is added

2. **Data Storage Format**
   - JSON string per ticker per minute
   - Format: `{"o": 450.23, "h": 451.00, "l": 449.50, "c": 450.75, "v": 1000000}`

## Simplified File Structure

```
/database_service/
├── db_manager.py          # Core database operations
├── historical_pull.py     # Fetch historical data from Alpaca  
├── realtime_pull.py       # Stream real-time data via websocket
├── api_endpoints.py       # REST endpoints for algorithms (TODO)
└── stocks.db             # SQLite database
```

## Function Specifications

### db_manager.py - Core Database Functions

**initialize_database()**
```
# Creates the stock_prices table if it doesn't exist
# Populates every minute from 2018-2030 between 9:30 AM - 4:00 PM EST
# Converts all timestamps to UTC before storing (adds 'Z' suffix)
# All ticker columns start as NULL
# Only needs to run once ever
```

**add_ticker_if_missing(ticker)**
```
# Checks if ticker column exists in table
# If not, runs ALTER TABLE ADD COLUMN
# Called automatically by other functions before any ticker operation
# Returns nothing, just ensures column exists
```

**check_data_exists(ticker, start_date, end_date)**
```
# First calls add_ticker_if_missing()
# Uses COUNT to check for NULL values in date range
# Returns empty list if all data exists
# Returns [{"start": start_date, "end": end_date}] if any NULLs found
# Simplified for efficient bulk fetching
```

**insert_historical_data(ticker, data_array)**
```
# First calls add_ticker_if_missing()
# Takes array of {timestamp, ohlcv} objects
# Updates each row with JSON string
# ONLY updates rows where ticker IS NULL (won't overwrite existing data)
# Uses UPDATE not INSERT since timestamps already exist
# Handles bulk operations efficiently
```

**get_historical_data(ticker, start_date, end_date)**
```
# First calls add_ticker_if_missing()
# Fetches all non-NULL data in date range
# Returns array of {timestamp, ohlcv} objects
# Parses JSON strings back to objects
```

**insert_minute_data(ticker, timestamp, ohlcv)**
```
# First calls add_ticker_if_missing()
# Updates single row with new data
# Used by websocket for real-time updates
# Converts ohlcv dict to JSON string
```

**get_latest_price(ticker)**
```
# Returns most recent non-NULL entry for ticker
# Useful for algorithms checking current price
# Returns {timestamp, ohlcv} or None if no data
```

### historical_pull.py - Alpaca Historical Data

**HistoricalFetcher class**
```
# Uses alpaca-py's StockHistoricalDataClient
# Converts date strings to UTC timestamps for database compatibility
# fetch_and_store() method:
  - Calls check_data_exists() to see what's needed
  - If data missing, fetches from Alpaca
  - Converts Alpaca bar objects to our format
  - Stores via insert_historical_data()
  - Returns status and row count
```

### realtime_pull.py - Real-time Data Management

**RealtimeStreamer class**
```
# Uses alpaca-py's StockDataStream for websocket connection
# handle_bar() callback:
  - Receives bar data from websocket
  - Converts to UTC timestamp format
  - Stores via insert_minute_data()
# subscribe() method manages symbol subscriptions
# run() method starts the stream (blocks until stopped)
```

## Complete Process Flow Examples

### Example 1: Algorithm Requests Historical Data
```
1. Algorithm needs MSFT data from Jan 1-15
2. check_data_exists("MSFT", ...) returns [{"start": "...", "end": "..."}]
3. HistoricalFetcher.fetch_and_store() called
4. Alpaca API returns only valid trading minutes
5. Data converted to UTC timestamps
6. insert_historical_data() stores only in NULL cells
7. get_historical_data() returns the complete dataset
```

### Example 2: Real-time Subscription
```
1. RealtimeStreamer.subscribe(['NVDA'])
2. Websocket connection established
3. Every minute, handle_bar() receives new data
4. Timestamp converted to UTC
5. insert_minute_data() stores in database
6. Algorithm can call get_latest_price() anytime
```

## Key Design Principles

1. **Database as Single Source of Truth** - All data goes through DB
2. **UTC Timestamps Throughout** - Avoids timezone confusion
3. **Automatic Column Management** - No manual ticker setup needed
4. **Safe Re-fetching** - Won't overwrite existing data
5. **Bulk Window Fetching** - Efficient API usage

## Current Implementation Status

✓ Database initialization with UTC timestamps
✓ Core database functions with optimizations
✓ Historical data fetcher (historical_pull.py)
✓ Real-time websocket streamer (realtime_pull.py)
→ Next: Test both Alpaca connections during market hours
- TODO: REST API endpoints
- TODO: Crash recovery logic

## Testing Next Steps

The next critical step is to test both historical_pull.py and realtime_pull.py during market hours to verify that data correctly flows from Alpaca into the database.