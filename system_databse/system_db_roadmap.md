# System Database Roadmap

## Project Context
The system database is the central state manager for all running algorithms. While `stocks.db` provides market data, this database tracks what algorithms exist, their transactions, and system configuration. It's the "memory" that persists between restarts and enables the dashboard to display real-time algorithm performance.

## Core Philosophy
- **Calculate, Don't Store**: Never store values that can be calculated from transactions
- **Simplicity First**: No complex indexing, caching, or optimization for 5-6 algorithms
- **Single Source of Truth**: Alpaca has the money, we just track what we told it to do
- **Crash-Proof**: System can restart anytime and pick up exactly where it left off

## Database Design

### File Structure
```
/autotrader/
├── database/
│   ├── stocks.db              # Market data (already built)
│   ├── system.db              # Algorithm state (this chapter)
│   ├── db_manager.py          # Market data functions (already built)
│   └── system_db_manager.py   # Algorithm state functions (this chapter)
├── algorithms/                # Algorithm files (source of truth)
│   ├── sma_crossover.py
│   ├── rsi_bounce.py
│   └── macd_signal.py
```

### Complete Schema
```sql
-- Algorithm tracking
CREATE TABLE algorithm_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,         -- "NVDA_SMA_20240102_143022"
    algorithm_type TEXT NOT NULL,       -- "sma_crossover"
    ticker TEXT NOT NULL,               -- "NVDA"
    initial_capital REAL NOT NULL CHECK(initial_capital > 0),
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running', 'stopped')),
    created_at TEXT NOT NULL,           -- "2024-01-02T14:30:22Z"
    stopped_at TEXT                     -- NULL until stopped
);

-- Transaction history
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('buy', 'sell')),
    shares INTEGER NOT NULL CHECK(shares > 0),
    price REAL NOT NULL CHECK(price > 0),
    timestamp TEXT NOT NULL,            -- "2024-01-02T14:30:00Z"
    FOREIGN KEY (algorithm_id) REFERENCES algorithm_instances(id)
);

-- System configuration
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initial PIN setup
INSERT INTO system_config (key, value) VALUES ('pin', '1234');
```

## Design Decisions & Rationale

### 1. Primary Key Strategy
**Decision**: Auto-incrementing integers (1, 2, 3...)
- Simple URLs: `/api/algorithms/3`
- Efficient foreign keys in transactions table
- Display name provides human readability for debugging

### 2. No Stored Calculations
**Decision**: Calculate everything on-demand
- Current shares: `SUM(buy) - SUM(sell)` from transactions
- Current value: shares × latest price from stocks.db
- P&L: current value - initial capital
- Trade count: `COUNT(*)` from transactions

**Why**: Prevents sync issues, always accurate, trivially fast for small scale

### 3. Algorithm Type Storage (UPDATED)
**Decision**: Store only the selected algorithm filename (no extension)
- Database stores: `"sma_crossover"` when user selects that algorithm
- Available algorithms come from `/algorithms/` directory scan
- No list of algorithms stored in database

**How It Works**:
1. Frontend requests available algorithms from API
2. API scans `/algorithms/` folder for .py files
3. Database only stores which algorithm each card uses
4. Add new algorithm = drop new .py file in folder
5. Orchestrator loads: `algorithms/{algorithm_type}.py`

### 4. Cash Tracking
**Decision**: No cash balance tracking
- Alpaca account is source of truth for money
- Cards track "allocations" not actual cash
- Initial capital is just for P&L calculation

### 5. Transaction History
**Decision**: Store every buy/sell as immutable history
- Enables accurate position calculation
- Provides audit trail
- Supports P&L analysis
- Never updated or deleted

### 6. Status Management
**Decision**: Soft delete with status field
- 'running': Active on dashboard
- 'stopped': Hidden but preserved for history
- Stopped algorithms never restart (create new instead)

### 7. PIN Storage
**Decision**: Simple key-value in system_config table
- No encryption (it's a home system)
- Could expand for other settings later
- Frontend validates PIN before sensitive actions

## Integration Points

### With Frontend (via API)
```
GET /api/algorithms
Returns: All 'running' algorithms with calculated fields:
{
  "id": 3,
  "display_name": "NVDA_SMA_20240102_143022",
  "ticker": "NVDA",
  "algorithm_type": "sma_crossover",
  "initial_capital": 10000,
  "current_shares": 45,        # Calculated
  "current_value": 11245,      # Calculated
  "trade_count": 23,           # Calculated
  "last_update": "2:34 PM"     # From latest transaction
}

GET /api/available-algorithms
Returns: List of algorithm files from /algorithms/ directory:
["sma_crossover", "rsi_bounce", "macd_signal"]
```

### With Orchestrator
```python
# Every minute:
1. Query all algorithms WHERE status = 'running'
2. For each algorithm:
   - Load algorithm_type.py
   - Get transaction history
   - Calculate current position
   - Feed market data
   - Execute any trades
   - Record new transactions
```

### With stocks.db
- Pull latest prices for current value calculations
- Timestamps use identical UTC format with 'Z' suffix
- Join on minute_timestamp for historical analysis

## Implementation Plan

### Phase 1: Core Schema
1. Create `system.db` file
2. Run schema creation SQL
3. Insert default PIN
4. Verify foreign key constraints work

### Phase 2: Basic Functions (system_db_manager.py)
```python
# Algorithm lifecycle
initialize_system_db()
create_algorithm(ticker, algo_type, capital) -> id
stop_algorithm(id)
get_algorithm(id) -> dict
get_all_algorithms(status=None) -> list

# Transactions
record_buy(algo_id, shares, price)
record_sell(algo_id, shares, price)
get_transactions(algo_id) -> list

# Calculations
calculate_position(algo_id) -> shares
calculate_trade_count(algo_id) -> int
get_algorithm_with_calculations(id) -> dict

# Config
get_pin() -> str
update_pin(new_pin)
```

### Phase 3: Display Name Generation
```python
def generate_display_name(ticker, algo_type):
    # NVDA_SMA_20240102_143022
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ticker}_{algo_type}_{timestamp}"
```

### Phase 4: Testing Harness
- Create test algorithm
- Record sample transactions
- Verify calculations match
- Test status transitions
- Ensure restart resilience

## Error Handling Strategy

### Database Integrity
- Foreign key constraints prevent orphan transactions
- CHECK constraints ensure valid data
- All functions use proper transactions (BEGIN/COMMIT/ROLLBACK)

### Missing Data Handling  
- If algorithm not found: Return None, let API handle 404
- If no transactions: Return 0 shares, 0 trades
- If stocks.db missing price: Use last known price

### Timezone Consistency
- All timestamps stored as UTC with 'Z' suffix
- Match stocks.db format exactly
- Convert to local time only for display

## What This Does NOT Handle

1. **Authentication**: No user system, single PIN for all actions
2. **Audit Logging**: No record of WHO did WHAT WHEN  
3. **Backtesting**: No paper trading or simulation mode
4. **Complex State**: No algorithm memory between runs
5. **Performance Optimization**: No caching, indexing, or connection pooling
6. **Multi-threading**: No concurrent access protection beyond SQLite defaults

## Success Criteria

- [ ] Can create/stop algorithms via API
- [ ] Dashboard shows accurate P&L and positions
- [ ] Survives Raspberry Pi restart without data loss
- [ ] Transaction history provides complete audit trail
- [ ] All calculations match Alpaca account exactly
- [ ] PIN protection works for sensitive actions
- [ ] Runs for 30 days without database corruption

## Next Steps

After this chapter:
1. Build API endpoints that use these functions
2. Create orchestrator that runs algorithms
3. Integrate with frontend for live updates

## Important Notes

- **Algorithm Discovery**: The frontend is responsible for asking the API what algorithms are available via `GET /api/available-algorithms`. The database never stores a list of available algorithms - it only records which algorithm each card is using. The `/algorithms/` directory is the single source of truth for what algorithms exist.