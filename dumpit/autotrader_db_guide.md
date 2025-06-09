# Auto Trader Database Implementation Guide - Revised

## Overview
A SQLite database system for automated stock trading that stores historical and real-time stock data. The database runs independently and provides data to trading algorithms.

## Recent Implementation Updates

### Fixed Minute Bar Fetching (CRITICAL FIX - May 2025)
- **Problem**: Alpaca was returning single daily bars instead of minute bars when passed bare dates
- **Solution**: Modified `fetch_and_store()` to explicitly specify market hours (9:30 AM - 4:00 PM EST)
- **Impact**: Now correctly fetches ~390 minute bars per trading day

### UTC Timestamp Conversion (IMPLEMENTED)
- **Format**: All timestamps stored as UTC with 'Z' suffix (e.g., `2024-01-02T14:30:00Z`)
- **Database**: Pre-populated with every minute from 9:30 AM - 4:00 PM EST for 2018-2030
- **Note**: Missing 4:00 PM closing bar (minor issue, not critical)

### Core Database Functions (COMPLETE)
1. **insert_historical_data()** - Bulk inserts with NULL checking to prevent overwrites
2. **check_data_exists()** - Returns date ranges with missing data
3. **get_historical_data()** - Retrieves and parses JSON data
4. **insert_minute_data()** - Single minute updates for websocket
5. **get_latest_price()** - Gets most recent price for a ticker

## Current Implementation Status

✅ Database initialization with UTC timestamps  
✅ Core database functions (all tested and working)  
✅ Historical data fetcher with minute bar fix  
✅ Real-time websocket streamer  
✅ Automatic ticker column management  

## File Structure

```
/autotrader/
├── database/
│   ├── db_manager.py          # Core database operations
│   ├── historical_pull.py     # Fetch historical data from Alpaca  
│   ├── realtime_pull.py       # Stream real-time data via websocket
│   └── stocks.db              # SQLite database (~81.5 MB)
├── .env                       # Alpaca API keys
└── venv/                      # Python virtual environment
```

## Database Schema

```sql
CREATE TABLE stock_prices (
    minute_timestamp TEXT PRIMARY KEY,
    -- Ticker columns added dynamically as needed
);
```

- **Rows**: ~1.3 million (every market minute 2018-2030)
- **Data Format**: JSON strings per ticker: `{"o": 450.23, "h": 451.00, "l": 449.50, "c": 450.75, "v": 1000000}`

## Key Implementation Details

### Historical Data Fetching
```python
# CRITICAL: Must specify market hours explicitly
start_dt = eastern.localize(start_dt.replace(hour=9, minute=30))
end_dt = eastern.localize(end_dt.replace(hour=16, minute=0))

request_params = StockBarsRequest(
    symbol_or_symbols=ticker,
    timeframe=TimeFrame.Minute,
    start=start_dt,
    end=end_dt,
    feed='iex'  # Use IEX feed for free tier
)
```

### Data Flow Patterns

**Historical Request**: Algorithm → check_data_exists() → fetch_and_store() → Alpaca API → insert_historical_data() → Database

**Real-time Stream**: Websocket → handle_bar() → insert_minute_data() → Database

**New Ticker**: Request → add_ticker_if_missing() → ALTER TABLE → Fetch historical → Store

## Testing Summary

- Single date fetches: ✅ Working (returns ~390 minute bars)
- Date range fetches: ✅ Working (handles weekends/holidays correctly)
- Websocket streaming: ✅ Working (tested during market hours)
- Database operations: ✅ All functions tested and verified

## Next Steps

1. **Build REST API endpoints** for algorithm access
2. **Create algorithm framework** for trading strategies
3. **Implement crash recovery** and error handling
4. **Add monitoring/logging** system
5. **Build simple web UI** for monitoring

## Important Notes

- Database won't overwrite existing data (safe to re-run fetches)
- Timestamps are UTC but represent EST/EDT market hours
- Missing 4:00 PM bars is a known issue (not critical)
- System handles weekends/holidays gracefully (returns no data)
- Free tier uses IEX feed (15-minute delay for historical)