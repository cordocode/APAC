# AutoTrader Complete Build Roadmap

## Project Overview
A personal wall-mounted trading terminal running on Raspberry Pi that automates stock trading through pluggable algorithms. The system displays real-time P&L on a terminal-aesthetic dashboard and executes trades through Alpaca's API.

### Core Architecture
- **Frontend**: Simple HTML/JS dashboard with black background, white text
  - Cards have colored borders: green (profit), red (loss), white (break-even)
- **API Server**: Flask endpoints connecting frontend to backend
- **Orchestrator**: Background process running algorithms every minute
- **Algorithms**: Pluggable Python files making trading decisions
- **Databases**: stocks.db (market data) and system.db (algorithm state)
- **Integration**: Alpaca API wrapper for executing trades

### What's Already Built ✅
1. **stocks.db** - Pre-populated with 1.3M minute timestamps (2018-2030)
2. **db_manager.py** - Functions for reading/writing market data
3. **historical_pull.py** - Fetches historical minute bars from Alpaca
4. **realtime_pull.py** - WebSocket streamer for live data
5. **system.db** - Complete database with algorithm_instances, transactions, system_config tables
6. **system_db_manager.py** - All core database functions with UTC timezone handling
7. **card_calculations.py** - Complete P&L calculation engine for frontend display

## Build Order & Dependencies

### Phase 1: Foundation Components (Build First)

#### 1.1 System Database (system.db)
**Purpose**: Store algorithm instances, transactions, and PIN

**File Location**: `system_databse/system.db` (note: databse intentionally misspelled)
**Creation Script**: `system_databse/create_system_db.py`

**Complete Schema Built**:
```sql
-- Algorithm tracking with auto-increment IDs
CREATE TABLE algorithm_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,         -- "NVDA_sma_crossover_20240604_143022"
    algorithm_type TEXT NOT NULL,       -- "sma_crossover" (matches filename)
    ticker TEXT NOT NULL,               -- "NVDA"
    initial_capital REAL NOT NULL CHECK(initial_capital > 0),
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running', 'stopped')),
    created_at TEXT NOT NULL,           -- "2024-06-04T14:30:22Z" (UTC)
    stopped_at TEXT                     -- NULL until stopped (UTC)
);

-- Transaction history for position tracking
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('buy', 'sell')),
    shares INTEGER NOT NULL CHECK(shares > 0),
    price REAL NOT NULL CHECK(price > 0),
    timestamp TEXT NOT NULL,            -- "2024-06-04T14:30:00Z" (UTC)
    FOREIGN KEY (algorithm_id) REFERENCES algorithm_instances(id)
);

-- System configuration
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Default PIN
INSERT INTO system_config (key, value) VALUES ('pin', '2020');
```

**Critical Database Design Decisions**:
- **No stored calculations**: Never store current_shares, current_value, pnl - always calculate from transactions
- **UTC timestamps only**: All timestamps use format "YYYY-MM-DDTHH:MM:SSZ" to match stocks.db
- **Foreign key constraints**: Enabled to prevent orphan transactions
- **Soft delete pattern**: Use status='stopped' rather than DELETE
- **Auto-incrementing IDs**: SQLite creates sqlite_sequence table automatically

**Key Design Decisions**:
- Auto-incrementing integer IDs for algorithms
- Store initial_capital (the allocation) per algorithm
- Calculate all other values dynamically:
  - Current shares from transaction history
  - Invested amount from transaction costs
  - Uninvested cash = initial_capital - invested
  - Current value = (shares × price) + uninvested cash
  - P&L = current value - initial_capital
- Soft delete with status field ('running' or 'stopped')
- Store algorithm type as string matching filename

**Dependency Note**: Frontend will call APIs that query this database, but those APIs don't exist yet.

#### 1.2 System Database Manager (system_db_manager.py)
**Purpose**: Functions to interact with system.db

**File Location**: `system_databse/system_db_manager.py` (note: databse is intentionally misspelled)
**Database Location**: `system_databse/system.db`

**Core Functions Built**:
```python
# Connection management
get_connection() -> sqlite3.Connection  # Returns dict rows, foreign keys enabled

# PIN management  
get_pin() -> str  # Returns PIN as string

# Algorithm lifecycle
create_algorithm(ticker: str, algo_type: str, initial_capital: float) -> int
stop_algorithm(algo_id: int) -> bool  # Returns True if algorithm was stopped
get_algorithm(algo_id: int) -> Optional[Dict[str, Any]]  # Single algorithm by ID
get_all_algorithms(status: Optional[str] = None) -> List[Dict[str, Any]]  # All or filtered

# Transaction recording
record_buy(algo_id: int, shares: int, price: float) -> int  # Returns transaction ID
record_sell(algo_id: int, shares: int, price: float) -> int  # Returns transaction ID
get_transactions(algo_id: int) -> List[Dict[str, Any]]  # Ordered by timestamp DESC

# Display name generation
generate_display_name(ticker: str, algo_type: str) -> str  # Format: "NVDA_sma_crossover_20240604_143022"
```

**Critical Implementation Details**:
- **All timestamps**: Use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` format
- **Database returns**: Dictionaries (not tuples) due to `conn.row_factory = sqlite3.Row`
- **Foreign keys**: Enabled with `PRAGMA foreign_keys = ON`
- **Error handling**: Functions use try/except with proper rollback on database operations
- **Transaction safety**: All write operations use proper commit/rollback patterns

**Card Calculations (card_calculations.py)**:
**File Location**: `system_databse/card_calculations.py`

**Functions Built**:
```python
# Position calculations
calculate_position(algo_id: int) -> int  # Current shares from transaction history
calculate_trade_count(algo_id: int) -> int  # Total transaction count
calculate_invested_amount(algo_id: int) -> float  # Net invested cash
calculate_current_value(algo_id: int, current_price: float, initial_capital: float) -> float
calculate_pnl(current_value: float, initial_capital: float) -> float

# Complete card data for frontend
get_algorithm_with_calculations(algo_id: int, current_price: float) -> Optional[Dict[str, Any]]
```

**Returned Dict Structure** (from get_algorithm_with_calculations):
```python
{
    # Base algorithm fields from database
    'id': 1,
    'display_name': 'NVDA_sma_crossover_20240604_143022',
    'algorithm_type': 'sma_crossover',
    'ticker': 'NVDA',
    'initial_capital': 10000.0,
    'status': 'running',
    'created_at': '2024-06-04T14:30:22Z',
    'stopped_at': None,
    
    # Calculated fields added by card_calculations
    'current_shares': 125,
    'trade_count': 3,
    'current_value': 10581.25,
    'pnl': 581.25,
    'current_price': 152.00
}
```

**P&L Calculation Logic** (implemented):
```python
# Calculation flow in card_calculations.py:
shares = SUM(buy_shares) - SUM(sell_shares)  # From transaction history
invested_amount = SUM(buy_costs) - SUM(sell_proceeds)  # Net cash invested
uninvested_cash = initial_capital - invested_amount  # Remaining allocation
current_value = (shares * current_price) + uninvested_cash
pnl = current_value - initial_capital
```

**Critical**: All timestamps must use UTC with 'Z' suffix to match stocks.db format.
**Implementation**: Use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` everywhere.

**Built Functions Available for Import**:
```python
# From system_db_manager.py
get_connection() -> sqlite3.Connection  # Dict rows, foreign keys enabled
get_pin() -> str
create_algorithm(ticker: str, algo_type: str, initial_capital: float) -> int
stop_algorithm(algo_id: int) -> bool
get_algorithm(algo_id: int) -> Optional[Dict[str, Any]]
get_all_algorithms(status: Optional[str] = None) -> List[Dict[str, Any]]
record_buy(algo_id: int, shares: int, price: float) -> int
record_sell(algo_id: int, shares: int, price: float) -> int
get_transactions(algo_id: int) -> List[Dict[str, Any]]

# From card_calculations.py  
calculate_position(algo_id: int) -> int
calculate_trade_count(algo_id: int) -> int
get_algorithm_with_calculations(algo_id: int, current_price: float) -> Optional[Dict[str, Any]]
```

**Algorithm Card Data Structure** (returned by get_algorithm_with_calculations):
```python
{
    'id': 1, 'display_name': 'NVDA_sma_crossover_20240604_143022',
    'algorithm_type': 'sma_crossover', 'ticker': 'NVDA', 'initial_capital': 10000.0,
    'status': 'running', 'created_at': '2024-06-04T14:30:22Z', 'stopped_at': None,
    'current_shares': 125, 'trade_count': 3, 'current_value': 10581.25, 
    'pnl': 581.25, 'current_price': 152.00
}
```

#### 1.3 Alpaca Wrapper (alpaca_wrapper.py)
**Purpose**: Interface to Alpaca trading API

**Core Functions**:
```python
validate_ticker(symbol) -> bool
get_account_cash() -> float  # Total cash in Alpaca account
place_market_buy(ticker, shares) -> fill_price
place_market_sell(ticker, shares) -> fill_price
```

**Note**: `get_account_cash()` returns total Alpaca account cash, not available for allocation. The API layer calculates available allocation cash.

**Dependency Note**: Orchestrator will use these functions, but orchestrator doesn't exist yet.

### Phase 2: Algorithm Framework

#### 2.1 Base Algorithm Structure
**Location**: `/algorithms/` directory

**Interface Every Algorithm Must Implement**:
```python
class Algorithm:
    def __init__(self, ticker, initial_capital)
    def get_data_requirements(self, current_time) -> dict
    def on_data(self, bars, transaction_history) -> (action, shares)
```

**Critical Multiple Position Support**:
Algorithms receive complete transaction history for independent position tracking:
```python
transaction_history = [
    {"id": 1, "type": "buy", "shares": 100, "price": 150.50, "timestamp": "2024-06-04T14:30:00Z"},
    {"id": 2, "type": "buy", "shares": 50, "price": 145.25, "timestamp": "2024-06-04T14:31:00Z"},
    {"id": 3, "type": "sell", "shares": 25, "price": 155.75, "timestamp": "2024-06-04T14:32:00Z"}
]
# Algorithm can track: "$150.50 position vs $145.25 position independently"
```

**Important Allocation Concept**:
- Algorithm receives initial_capital (e.g., $10,000) as its allocation
- Algorithm decides how much to invest (might only use $6,000)
- Remaining allocation stays as uninvested cash within that card
- Algorithms don't know about other algorithms or total account balance

**Key Points**:
- Algorithms are stateless between runs
- Return values: ('buy', shares), ('sell', shares), or ('hold', 0)
- Time calculations must be in UTC
- **Data Access**: Call `system_db_manager.get_transactions(algo_id)` for complete history

#### 2.2 First Algorithm (sma_crossover.py)
**Purpose**: Prove the pattern works

**Logic**: Buy when 20-period SMA crosses above 50-period SMA

**Dependency Note**: Will be called by orchestrator which doesn't exist yet.

### Phase 3: Orchestration Layer

#### 3.1 API Server (api_server.py)
**Purpose**: REST endpoints for frontend

**Endpoints**:
- `POST /api/validate-pin` - Check PIN
- `GET /api/algorithms` - Get all running algorithms with calculations
- `POST /api/algorithms` - Create new algorithm
- `DELETE /api/algorithms/{id}` - Stop algorithm
- `GET /api/available-algorithms` - Scan /algorithms/ directory
- `GET /api/account/cash` - Calculate available cash for new allocations
  - Get total cash from Alpaca account
  - Subtract sum of all running algorithms' initial_capital
  - Returns the amount available to allocate to new algorithms
  - NOT the raw Alpaca cash balance

**Critical Integration Requirements**:
- **Import statements needed**:
  ```python
  import system_db_manager
  import card_calculations
  import alpaca_wrapper  # When built
  ```
- **Database path**: Code must run from parent directory of `system_databse/`
- **Function calls**: Use exact function signatures from system_db_manager.py

**Critical Dependency Issue**: 
- Frontend expects `/api/account/cash` which needs both alpaca_wrapper AND system_db_manager
  - Must query Alpaca for total cash
  - Must sum all algorithm allocations from system.db  
- Frontend expects algorithm calculations but needs system_db_manager
- **Solution**: Build these endpoints after dependencies are ready

**Required Import Statements**:
```python
import system_db_manager
import card_calculations  
import alpaca_wrapper  # When built
```

**Critical Function Calls**:
- PIN validation: `system_db_manager.get_pin()` 
- Get algorithms: `system_db_manager.get_all_algorithms('running')`
- Get card data: `card_calculations.get_algorithm_with_calculations(id, current_price)`
- Create algorithm: `system_db_manager.create_algorithm(ticker, algo_type, initial_capital)`
- Stop algorithm: `system_db_manager.stop_algorithm(id)`
- Available cash: `alpaca_wrapper.get_account_cash() - SUM(initial_capital from running algorithms)`

#### 3.2 Orchestrator (orchestrator.py)
**Purpose**: Run algorithms every minute during market hours

**Important**: Orchestrator and frontend are completely separate processes
- Orchestrator doesn't communicate with frontend
- Frontend polls API independently
- They coordinate through the database only

**Flow**:
1. Check if market is open (EST timezone)
2. Get all running algorithms from system.db via `system_db_manager.get_all_algorithms('running')`
3. For each algorithm:
   - Load the Python module from `/algorithms/{algorithm_type}.py`
   - Get required data from stocks.db
   - Get transaction history via `system_db_manager.get_transactions(algo_id)`
   - Run algorithm logic with `algorithm.on_data(bars, transaction_history)`
   - Execute any trades via Alpaca
   - Record transactions via `system_db_manager.record_buy()` or `record_sell()`

**Critical Timezone Issue**: Market hours check must use Eastern Time, not server timezone.

**Dependencies**: Needs everything built so far.
**Required Imports**: `system_db_manager`, `alpaca_wrapper`, algorithm modules

### Phase 4: Frontend

#### 4.1 Dashboard HTML/CSS/JS
**Purpose**: Display algorithm cards and handle user interaction

**Components**:
- Algorithm cards showing P&L, shares, transactions
- PIN pad for secure actions
- Add algorithm modal
- Horizontal scrolling for multiple cards

**Polling Strategy**:
- Market hours: Every 30 seconds
- Off hours: Every 60 minutes
- **How it knows**: Each `/api/algorithms` response includes `"market_open": true/false`
- Frontend adjusts polling interval based on this flag

**Market Hours Coordination**: Backend includes `"market_open": true/false` in API responses so frontend doesn't need to calculate EST time.

**Dependencies**: Needs all API endpoints working.

## File Structure & Integration Map

```
/autotrader/
├── system_databse/                    # System database components
│   ├── system.db                      # Main database file
│   ├── create_system_db.py           # Database creation script
│   ├── system_db_manager.py          # Core database functions
│   └── card_calculations.py          # Frontend calculation engine
├── database/                         # Market data (pre-built)
│   ├── stocks.db                     # Pre-populated market data
│   └── db_manager.py                 # Market data functions
├── algorithms/                       # Algorithm files (to be built)
│   ├── sma_crossover.py
│   └── [other_algorithm].py
├── api_server.py                     # Flask API (to be built)
├── orchestrator.py                   # Algorithm runner (to be built)
├── alpaca_wrapper.py                 # Trading API (to be built)
└── frontend/                         # Dashboard (to be built)
    ├── index.html
    ├── style.css
    └── script.js
```

**Import Dependencies**:
- **api_server.py** imports: `system_db_manager`, `card_calculations`, `alpaca_wrapper`
- **orchestrator.py** imports: `system_db_manager`, `alpaca_wrapper`, algorithm modules
- **card_calculations.py** imports: `system_db_manager`
- **Running location**: All Python files run from `/autotrader/` root directory

## Critical Integration Points & Conflicts

### 1. Timezone Handling
**Conflict**: Multiple components handle time differently
**Solution**: Everything internal uses UTC with 'Z' suffix  
**Exception**: Market hours checks use Eastern Time  
**Display**: Frontend converts UTC to user's local time

**Critical Implementation**: 
- **Python UTC**: Use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` everywhere
- **Database format**: All timestamps exactly match stocks.db: "2024-06-04T14:30:22Z"
- **Never use**: `datetime.now()` without timezone - returns server time (Mountain)

### 2. Algorithm Discovery
**Potential Confusion**: Where does the list of available algorithms come from?
- **Answer**: API server scans `/algorithms/` directory
- **Not**: Stored in database or hardcoded

### 3. Cash Balance & Allocation Tracking
**Two Different Concepts**:

**Algorithm Allocation**: 
- Each card is given an initial_capital amount (e.g., $10,000)
- This is the card's "allocation" - money reserved for this algorithm
- Card might only have $6,000 invested, keeping $4,000 as cash reserve

**Available Cash for New Cards**:
- Formula: `Alpaca Cash - SUM(all running algorithms' initial_capital)`
- This prevents over-allocating beyond actual account balance
- Example: $50k Alpaca cash - $30k allocated = $20k available for new cards

**P&L Calculation** (separate concept):
- P&L = Current Value - Initial Capital
- Current Value = (Shares × Current Price) + Unallocated Cash within card
- This is per-card performance tracking

### 4. Position Calculation
**Critical**: Current shares are CALCULATED from transaction history
- **How**: Sum all buy transactions minus all sell transactions for that algorithm
- **Never**: Store a "current_shares" field in the database
- **Why**: Single source of truth - the transaction history
- **Implementation**: Use `card_calculations.calculate_position(algo_id)` which executes:
  ```sql
  SELECT SUM(CASE WHEN type = 'buy' THEN shares ELSE -shares END) 
  FROM transactions WHERE algorithm_id = ?
  ```

### 5. Frontend Polling & Market Hours
**Issue**: Frontend and orchestrator run independently - how does frontend know market hours?
- **Frontend runs**: Independent JavaScript timer in the browser
- **Orchestrator runs**: Separate Python process on the server
- **They don't communicate directly**

**Solution**: Frontend must determine market status independently
- Option 1: Add `/api/market-status` endpoint that returns `{"is_open": true}`
- Option 2: Frontend calculates EST time in JavaScript
- Option 3: Include market status in every `/api/algorithms` response

**Recommendation**: Option 3 - Include `"market_open": true` in API responses to avoid timezone math in JavaScript

## Multiple Position Tracking Architecture
**Critical Design Decision Made**: Algorithms can track multiple independent positions using transaction history

**How It Works**:
- Algorithm receives complete transaction list via `system_db_manager.get_transactions(algo_id)`
- **Full transaction history structure**:
  ```python
  [
      {"id": 1, "algorithm_id": 2, "type": "buy", "shares": 100, "price": 150.50, "timestamp": "2024-06-04T14:30:00Z"},
      {"id": 2, "algorithm_id": 2, "type": "buy", "shares": 50, "price": 145.25, "timestamp": "2024-06-04T14:31:00Z"},
      {"id": 3, "algorithm_id": 2, "type": "sell", "shares": 25, "price": 155.75, "timestamp": "2024-06-04T14:32:00Z"}
  ]
  ```
- Algorithm can implement position tracking logic like:
  - "Track $150.50 buy separately from $145.25 buy"
  - "Exit $150.50 position when price hits $160"  
  - "Exit $145.25 position when price hits $155"
- **Frontend displays**: Calculated totals only (current_shares: 125, pnl: $581.25)
- **Algorithm receives**: Complete granular history for position management

## Error Handling Requirements

### In system_db_manager.py
```python
def record_buy(algo_id, shares, price):
    try:
        conn.execute("BEGIN")
        # ... insert transaction ...
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise  # Let caller handle
```

### In orchestrator.py
```python
for algorithm in running_algorithms:
    try:
        # Run algorithm logic
        decision, shares = algorithm.on_data(...)
        
        if decision == 'buy':
            try:
                # Attempt trade
                fill_price = alpaca_wrapper.place_market_buy(ticker, shares)
                # Only record if trade succeeds
                system_db_manager.record_buy(algo_id, shares, fill_price)
            except Exception as e:
                log_error(f"Trade failed for {ticker}: {e}")
                # No transaction recorded - continue to next algorithm
                
    except Exception as e:
        log_error(f"Algorithm {algorithm.id} crashed: {e}")
        continue  # Skip to next algorithm, don't crash orchestrator
```

### In alpaca_wrapper.py
```python
def place_market_buy(ticker, shares):
    try:
        response = alpaca_api.submit_order(...)
        return response.filled_avg_price
    except Exception as e:
        log_error(f"Trade failed: {e}")
        raise  # Let orchestrator decide whether to record transaction
```

### In api_server.py
```python
@app.route('/api/algorithms/<int:id>')
def get_algorithm(id):
    algo = system_db_manager.get_algorithm(id)
    if algo is None:
        return jsonify({"error": "Algorithm not found"}), 404
    return jsonify(algo)
```

## Testing Strategy

### Phase 1 Testing
- Create test algorithm instance with $10,000 allocation
- Record sample buy transaction (50 shares at $100)
- Verify position calculation shows 50 shares
- Verify P&L calculation with mock current price
- Test available cash calculation with multiple algorithms

### Phase 2 Testing
- Run single algorithm in isolation
- Verify data requirements work
- Test buy/sell decisions

### Phase 3 Testing
- Start with market closed (no trades)
- Test with single algorithm
- Verify transaction recording
- Confirm orchestrator and frontend work independently

### Phase 4 Testing
- Mock API responses initially
- Test PIN validation
- Verify card updates
- Test market status flag updates polling interval

## Minimal Code Examples

### Display Name Generation
```python
f"{ticker}_{algo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

### Market Hours Check
```python
eastern = pytz.timezone('US/Eastern')
now = datetime.now(eastern)
is_open = weekday < 5 and time(9,30) <= now.time() <= time(16,0)
```

### Position Calculation
```sql
SELECT SUM(CASE WHEN type='buy' THEN shares ELSE -shares END) 
FROM transactions WHERE algorithm_id = ?
```

### Available Cash Calculation
```python
alpaca_cash = alpaca_wrapper.get_account_cash()
running_algos = system_db_manager.get_all_algorithms('running')
allocated = sum(algo['initial_capital'] for algo in running_algos)
available = alpaca_cash - allocated
```

## Missing Components to Add

### 1. Startup Script
**Why Needed**: Raspberry Pi must auto-start everything on boot
- Start API server
- Start orchestrator
- Open browser to dashboard

### 2. Configuration File
**Why Needed**: Store API keys and settings
- Already have .env for Alpaca keys
- May need config.json for other settings

### 3. Error Logging
**Why Needed**: Debug issues on headless Pi
- Simple file-based logging
- Rotate daily to prevent disk fill

## Build Sequence Summary

1. **Day 1-2**: ✅ **COMPLETED** - System database and manager functions
   - Created `system_databse/system.db` with complete schema
   - Built `system_db_manager.py` with all core functions  
   - Built `card_calculations.py` with P&L calculation engine
   - Implemented proper UTC timezone handling
2. **Day 3**: Alpaca wrapper and first algorithm
3. **Day 4-5**: API server and orchestrator  
4. **Day 6-7**: Frontend and testing
5. **Day 8**: Polish, startup scripts, deployment

## Success Criteria
- Trades execute correctly
- P&L calculations match expected values (current value - initial allocation)
- Available cash for new algorithms = Alpaca cash - sum of allocations
- Survives Raspberry Pi restart
- Runs 30 days without intervention
- Dashboard updates every 30 seconds during market hours
- Frontend polling adjusts based on market status flag