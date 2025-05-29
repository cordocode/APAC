# Auto Trader Database Implementation Guide - Revised

## Overview
A SQLite database system for automated stock trading that stores historical and real-time stock data. The database runs independently and provides data to trading algorithms.

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

### Key Design Decisions

1. **Pre-populated Timestamps**
   - Every minute from 9:30 AM to 4:00 PM EST
   - Every calendar day from 2018-01-01 to 2030-12-31
   - ~3.9 million rows
   - **ALL values start as NULL** until data is added

2. **Data Storage Format**
   - JSON string per ticker per minute
   - Format: `{"o": 450.23, "h": 451.00, "l": 449.50, "c": 450.75, "v": 1000000}`

## Simplified File Structure

```
/database_service/
├── db_manager.py          # Core database operations
├── websocket_handler.py   # Alpaca websocket management
├── historical_fetcher.py  # Fetch historical data from Alpaca
├── api_endpoints.py       # REST endpoints for algorithms
└── stocks.db             # SQLite database
```

## Function Specifications

### db_manager.py - Core Database Functions

**initialize_database()**
```
# Creates the stock_prices table if it doesn't exist
# Populates every minute from 2018-2030 between 9:30 AM - 4:00 PM EST (converted to UTC)
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
# Queries database for NULL values in date range
# Returns list of timestamp ranges where data is missing
# Empty list means all data exists
```

**insert_historical_data(ticker, data_array)**
```
# First calls add_ticker_if_missing()
# Takes array of {timestamp, ohlcv} objects
# Updates each row with JSON string
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

### historical_fetcher.py - Alpaca Historical Data

**fetch_and_store_historical(ticker, start_date, end_date)**
```
# Main function that orchestrates historical data fetch
# Calls db_manager.check_data_exists() first
# If data missing, connects to Alpaca Historical API
# Fetches 1-minute bars for date range
# Formats Alpaca response to match our schema
# Calls db_manager.insert_historical_data()
# Returns status (already exists, fetched, error)
```

**handle_rate_limits()**
```
# Tracks API calls to avoid hitting limits
# Returns wait time if limit reached
# Implements exponential backoff if needed
```

**backfill_missed_realtime_data(ticker, last_known_timestamp)**
```
# Called during crash recovery
# Fetches data between last_known_timestamp and now
# Fills gaps when websocket was disconnected
# Uses same historical API but for recent timeframe
```

### websocket_handler.py - Real-time Data Management

**initialize_stream()**
```
# Creates Alpaca websocket connection
# Sets up callback for incoming data
# Must be called on service startup
```

**subscribe_ticker(ticker, algo_id)**
```
# Implements reference counting for subscriptions
# If first subscriber for ticker, starts websocket
# Increments counter for existing subscriptions
# Returns current subscription count
```

**unsubscribe_ticker(ticker, algo_id)**
```
# Decrements reference counter
# If last subscriber, stops websocket for ticker
# Cleans up subscription tracking
# Returns whether stream was closed
```

**on_bar_received(bar)**
```
# Callback function for websocket data
# Formats incoming bar to our ohlcv structure
# Calls db_manager.insert_minute_data()
# Handles any websocket errors gracefully
```

**check_active_streams()**
```
# Returns dict of {ticker: subscriber_count}
# Used for crash recovery
# Helps debug which streams are active
```

**restart_streams_for_active_algos()**
```
# Called on service restart
# Queries all algorithms for their needs
# Re-establishes dropped websocket connections
```

### api_endpoints.py - REST Interface

**POST /request_data**
```
# Main endpoint for algorithms requesting historical data
# Expects: {ticker, start_date, end_date}
# Checks database first via db_manager
# If missing, calls historical_fetcher
# Always returns data from database (single source of truth)
# Response: {ticker, data[], fetched_from_api: bool}
```

**POST /subscribe_realtime**
```
# Starts real-time data flow for a ticker
# Expects: {ticker, algo_id}
# Calls websocket_handler.subscribe_ticker()
# Response: {subscribed: true, active_count: N}
```

**POST /unsubscribe_realtime**
```
# Stops real-time data flow
# Expects: {ticker, algo_id}
# Calls websocket_handler.unsubscribe_ticker()
# Response: {unsubscribed: true, stream_closed: bool}
```

**GET /get_latest**
```
# Quick endpoint for current price
# Query param: ticker
# Calls db_manager.get_latest_price()
# Response: {timestamp, ohlcv} or 404 if no data
```

**GET /check_websocket_status**
```
# Debugging endpoint
# Query param: ticker (optional)
# Returns active websocket subscriptions
# Helps verify what's currently streaming
```

**POST /startup_recovery**
```
# Called when service restarts
# Triggers websocket_handler.restart_streams_for_active_algos()
# Checks for data gaps and backfills if needed
# Response: {streams_restarted: [], gaps_filled: []}
```

**GET /database_stats**
```
# Returns overall database health and statistics
# Shows total rows, size on disk, tickers with data
# For each ticker: first/last data point, total non-NULL entries
# Helps monitor database growth and identify gaps
```

**POST /add_algorithm**
```
# Comprehensive endpoint for algorithm initialization
# Expects: {algo_id, ticker, algo_type, needs_historical, date_range, needs_realtime}
# Orchestrates entire setup process:
#   - Adds ticker column if needed
#   - Fetches historical data if required
#   - Subscribes to websocket if needed
# Returns: {data_ready: bool, websocket_active: bool, can_start: bool}
```

## Complete Process Flow Examples

### Example 1: Algorithm Requests Historical Data
```
1. Algorithm calls POST /request_data for MSFT from Jan 1-15
2. Endpoint calls db_manager.check_data_exists("MSFT", ...)
3. add_ticker_if_missing("MSFT") runs automatically, adds column
4. check_data_exists finds all NULLs, returns missing ranges
5. historical_fetcher.fetch_and_store_historical() called
6. Alpaca API returns only valid trading minutes (skips weekends/holidays)
7. Data formatted and stored via db_manager.insert_historical_data()
8. db_manager.get_historical_data() fetches fresh data
9. Endpoint returns data to algorithm
```

### Example 2: Real-time Subscription
```
1. Algorithm calls POST /subscribe_realtime for NVDA
2. websocket_handler.subscribe_ticker("NVDA", "algo_001") called
3. Reference counter: NVDA = 1 (first subscriber)
4. Websocket stream started for NVDA
5. As each minute bar arrives, on_bar_received() triggered
6. Data immediately stored via db_manager.insert_minute_data()
7. Algorithm polls GET /get_latest as needed for current price
```

### Example 3: Multiple Algorithms Same Ticker
```
1. Algo_001 subscribes to AAPL (counter: 1, stream starts)
2. Algo_002 subscribes to AAPL (counter: 2, stream already active)
3. Algo_001 unsubscribes (counter: 1, stream continues)
4. Algo_002 unsubscribes (counter: 0, stream stops)
```

## Key Design Principles

1. **Database as Single Source of Truth** - All data goes through DB
2. **Automatic Column Management** - No manual ticker setup needed
3. **Reference Counting** - Efficient websocket sharing
4. **NULL as Unknown** - Simple way to track what data exists
5. **Function-Based** - Each function has one clear purpose

## Implementation Order

1. Create database with initialize_database()
2. Build db_manager.py functions
3. Test database operations manually
4. Add historical_fetcher.py
5. Create basic REST endpoints
6. Test full historical data flow
7. Add websocket functionality last

## Error Handling Considerations

- Database connection failures
- Alpaca API downtime
- Rate limit responses
- Websocket disconnections
- Invalid date ranges
- Missing tickers in Alpaca

## Time Synchronization Strategy

**All timestamps stored in UTC**
- 9:30 AM EST = 14:30 UTC (standard time)
- Database always uses UTC to avoid confusion

**"Latest" price definition**
- Always means most recent non-NULL timestamp
- Accounts for potential 1-2 second websocket delay
- No conflict between historical and real-time data

## Rate Limit Management

**Alpaca API Limits**
- Historical data: 200 requests per minute
- Each request can fetch multiple days of data
- Strategy: Fetch in larger chunks when possible
- Return clear error messages when limit hit
- Queue requests if multiple algorithms need same data

## Crash Recovery Process

1. **On service startup**
   - Call /startup_recovery endpoint
   - Check which algorithms were active (need separate algo tracking)
   - Identify last successful timestamp for each ticker

2. **Backfill missing data**
   - For each active ticker, find most recent non-NULL entry
   - Use historical API to fill gap between last entry and current time
   - Re-subscribe to necessary websockets

3. **Notify algorithms**
   - Return status of what was recovered
   - Algorithms can decide whether to continue or restart

## Storage Monitoring

**Database growth tracking**
- ~100 bytes per ticker per minute with JSON
- 10 tickers × 390 minutes/day × 252 days = ~1M records/year actual data
- Monitor disk usage via /database_stats endpoint
- No automatic pruning for now (manual decision)

## Missing Considerations Now Addressed

1. **Timezone handling** - Everything in UTC
2. **Crash recovery with backfill** - Added backfill_missed_realtime_data()
3. **Rate limit specifics** - Clear limits and handling strategy
4. **Database monitoring** - Stats endpoint for growth tracking
5. **Algorithm initialization** - Single endpoint to handle all setup
6. **Time sync between historical/realtime** - Latest = most recent non-NULL