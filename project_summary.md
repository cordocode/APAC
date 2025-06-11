# AutoTrader Architecture Blueprint

## OVERVIEW

**AutoTrader** is a wall-mounted Raspberry Pi trading terminal that automates stock trading through pluggable algorithms. The system executes trades via Alpaca's API and displays real-time P&L on a terminal-aesthetic dashboard.

### Core Design Principles
- **Market-Hours-Only Database**: Every timestamp is guaranteed to be a valid trading minute
- **Self-Contained Algorithms**: Each algorithm fetches its own data and manages state independently
- **Zero Calendar Logic**: No algorithm needs to handle weekends, holidays, or market hours
- **Allocation-Based Trading**: Each algorithm receives a fixed capital allocation to manage
- **UTC Everywhere**: All internal timestamps use UTC with 'Z' suffix format

### Technology Stack
- **Backend**: Python with Flask API server
- **Frontend**: Vanilla HTML/CSS/JavaScript with terminal aesthetics
- **Database**: SQLite (system.db for state, stocks.db for market data)
- **Trading**: Alpaca API for execution and market data
- **Real-time Data**: WebSocket streams managed by orchestrator

## IMPORT PATTERNS (CRITICAL)

**All Python files run from APAC root directory**. This affects how imports must be structured.

### Working Import Pattern
```python
# For files in subdirectories importing from other subdirectories:
from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
from orchestra.alpaca_wrapper import AlpacaWrapper

# For test files in algorithm/ folder:
import sys
sys.path.append('.')  # Add APAC root to path

# Then import other modules
from algorithm.sma_crossover import Algorithm
```

### Running Scripts
```bash
# ALWAYS run from APAC root:
cd /Volumes/SSD/APAC  # or your APAC path
python3 algorithm/test_file.py   # ✅ Correct
# NOT: cd algorithm && python3 test_file.py ❌
```

### Key Rules
1. **Always use full paths from APAC root** (e.g., `database.db_manager`, not just `db_manager`)
2. **System path adjustment for test files**: Add `sys.path.append('.')` when in subdirectories
3. **Run all scripts from APAC root directory** to ensure imports resolve correctly
4. **Special case**: When db_manager imports from same directory, still use `from database.historical_pull`
5. **Note typos**: `system_databse` (not system_database), `algorithm` (not algorithms)

### Common Issues & Solutions
- **Import not found**: Check you're running from APAC root, not from subdirectory
- **Module not found**: Add appropriate `sys.path.append('.')` 
- **Relative imports failing**: Switch to absolute imports from root

## SYSTEM DATABASE

**Location**: `system_databse/system.db` (misspelling intentional)
**Runtime**: All components run from APAC root directory
**DB Path**: system_db_manager.py must use `DB_PATH = "system_databse/system.db"`

### Database Structure Detail

**Table: algorithm_instances**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | INTEGER PRIMARY KEY | Auto-increment ID | 1, 2, 3... |
| display_name | TEXT NOT NULL | Unique identifier | "NVDA_sma_crossover_20240604_143022" |
| algorithm_type | TEXT NOT NULL | Algorithm filename | "sma_crossover" |
| ticker | TEXT NOT NULL | Stock symbol | "NVDA" |
| initial_capital | REAL NOT NULL | Allocation amount | 10000.0 |
| status | TEXT NOT NULL | Running/stopped | "running" |
| created_at | TEXT NOT NULL | UTC timestamp | "2024-06-04T14:30:22Z" |
| stopped_at | TEXT | UTC when stopped | NULL or "2024-06-04T16:45:00Z" |

**Table: transactions**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | INTEGER PRIMARY KEY | Auto-increment ID | 1, 2, 3... |
| algorithm_id | INTEGER NOT NULL | Links to algorithm | 1 |
| type | TEXT NOT NULL | Buy or sell | "buy" |
| shares | INTEGER NOT NULL | Share count | 100 |
| price | REAL NOT NULL | Execution price | 152.45 |
| timestamp | TEXT NOT NULL | UTC timestamp | "2024-06-04T14:30:00Z" |

**Table: system_config**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| key | TEXT PRIMARY KEY | Config key | "pin" |
| value | TEXT NOT NULL | Config value | "2020" |

### Schema

```sql
-- Algorithm instances with auto-increment IDs
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
```

### Key Functions (`system_db_manager.py`)
- `create_algorithm(ticker, algo_type, initial_capital) -> int`
- `stop_algorithm(algo_id) -> bool`
- `record_buy(algo_id, shares, price) -> int`
- `record_sell(algo_id, shares, price) -> int`
- `get_transactions(algo_id) -> List[Dict]`
- `get_all_algorithms(status=None) -> List[Dict]`

### Common Queries
```sql
-- Get all running algorithms
SELECT * FROM algorithm_instances WHERE status = 'running';

-- Get position for algorithm
SELECT SUM(CASE WHEN type='buy' THEN shares ELSE -shares END) as position
FROM transactions WHERE algorithm_id = ?;

-- Get latest transaction
SELECT * FROM transactions WHERE algorithm_id = ? 
ORDER BY timestamp DESC LIMIT 1;

-- Calculate P&L components
SELECT 
    SUM(CASE WHEN type='buy' THEN shares*price ELSE -(shares*price) END) as net_invested
FROM transactions WHERE algorithm_id = ?;
```

### Calculation Engine (`card_calculations.py`)
- **Current Position**: Sum of buy shares minus sell shares
- **P&L Formula**: Current Value - Initial Capital
- **Current Value**: (Shares × Price) + Uninvested Cash
- **Never Store**: Calculations are always derived from transaction history

## STOCK PRICE DATABASE

**Location**: `database/stocks.db`

### Database Structure Detail

**Table: stock_prices**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| minute_timestamp | TEXT PRIMARY KEY | UTC market minute | "2024-01-02T14:30:00Z" |
| AAPL | TEXT | JSON OHLCV data | '{"o":150.25,"h":150.50,"l":150.00,"c":150.45,"v":1000000}' |
| NVDA | TEXT | JSON OHLCV data | '{"o":450.00,"h":451.25,"l":449.75,"c":450.50,"v":500000}' |
| [ticker] | TEXT | Dynamic columns | Added as needed per ticker |

**Key Points:**
- Primary key is minute_timestamp (guaranteed market hours only)
- Each ticker gets its own column added dynamically
- Data stored as JSON strings with OHLCV structure
- NULL values indicate no data for that minute/ticker

### JSON Structure Per Cell
```json
{
    "o": 150.25,    // Open price
    "h": 150.50,    // High price
    "l": 150.00,    // Low price
    "c": 150.45,    // Close price
    "v": 1000000    // Volume
}
```

### Structure
- **~1 million rows** of market-hours-only timestamps (2018-2028)
- **No weekends, holidays, or after-hours data**
- **Dynamic ticker columns** added as needed
- **JSON storage** for OHLCV data per cell

### Calendar Integration (`calendar_manager.py`)
```python
class MarketCalendar:
    def get_market_schedule(start_date, end_date) -> List[Dict]
    def is_market_open_now() -> bool
    def generate_all_market_minutes(start_year, end_year) -> List[str]
```

### Data Access (`db_manager.py`)
```python
def get_data_for_algorithm(ticker, requirement_type, **kwargs):
    """
    Primary interface - guarantees valid market minutes only
    
    Types:
    - 'last_n_bars': n=200, before_timestamp=None
    - 'time_range': start='2024-01-02T09:30:00Z', end='2024-01-02T20:59:00Z'
    
    Returns:
    List of dicts: [{'timestamp': '...', 'ohlcv': {'o':..., 'h':..., 'l':..., 'c':..., 'v':...}}]
    """
```

**Auto-Fetch Behavior**: 
- If requested data not found, automatically fetches from Alpaca
- Creates ticker column if needed
- Stores fetched data in database
- Returns exactly what was requested

### Common Queries
```sql
-- Get latest price for ticker (note: minute_timestamp not timestamp)
SELECT minute_timestamp, NVDA FROM stock_prices 
WHERE NVDA IS NOT NULL 
ORDER BY minute_timestamp DESC LIMIT 1;

-- Get last 200 bars
SELECT minute_timestamp, NVDA FROM stock_prices 
WHERE minute_timestamp <= '2024-01-02T20:59:00Z' 
AND NVDA IS NOT NULL 
ORDER BY minute_timestamp DESC LIMIT 200;

-- Check specific data point
SELECT minute_timestamp, AAPL FROM stock_prices 
WHERE minute_timestamp = '2024-01-31T19:10:00Z';
-- Returns: 2024-01-31T19:10:00Z|{"o": 185.81, "h": 185.81, "l": 185.67, "c": 185.7, "v": 1820}

-- Check data completeness
SELECT COUNT(*) as total_minutes,
       COUNT(NVDA) as nvda_data_points,
       COUNT(AAPL) as aapl_data_points
FROM stock_prices;
```

### Data Pipeline
- **Historical**: `historical_pull.py` fetches past data from Alpaca
- **Real-time**: `realtime_pull.py` manages WebSocket streams
- **Storage**: Both write to the same market-hours-only structure
- **Import Note**: When `db_manager.py` imports from same directory, use `from database.historical_pull`

## ORCHESTRATOR

**File**: `orchestra/orchestrator.py`

### Core Responsibilities
1. **Execute algorithms** every minute during market hours
2. **Manage WebSocket subscriptions** based on active algorithms
3. **Execute trades** through Alpaca and record transactions
4. **Handle errors** without crashing (algorithm failures isolated)

### Timing Loop
```python
while True:
    if calendar.is_market_open_now():
        run_all_algorithms()
        
        # Sleep until 2 seconds past next minute
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        wakeup_time = next_minute + timedelta(seconds=2)
        sleep_until(wakeup_time)
    else:
        sleep(15 * 60)  # 15 minutes when market closed
```

### WebSocket Management
- **Reference counting** for shared tickers
- **Automatic subscription** on algorithm start
- **Automatic unsubscription** when last algorithm stops
- **Restart resilience** - restores all subscriptions on startup

### Trade Execution
```python
if action == 'buy':
    fill_price = alpaca_wrapper.place_market_buy(ticker, shares)
    system_db_manager.record_buy(algo_id, shares, fill_price)
```

## ALGORITHMS

**Location**: `/algorithm/` directory (NOTE: singular, not /algorithms/)

### Base Structure
```python
class Algorithm:
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
    
    def run(self, current_time, algo_id):
        # Get market data - zero calendar logic needed
        bars = db_manager.get_data_for_algorithm(
            ticker=self.ticker,
            requirement_type='last_n_bars',
            n=200  # Gets exactly 200 market minutes
        )
        
        # Get transaction history
        transactions = system_db_manager.get_transactions(algo_id)
        
        # Make decision
        return ('buy', shares) or ('sell', shares) or ('hold', 0)
```

### Required Imports
```python
from database.db_manager import get_data_for_algorithm
from system_databse.system_db_manager import get_transactions
```

### Data Format from get_data_for_algorithm
```python
# Each bar in the returned list has this exact structure:
{
    'timestamp': '2024-03-15T19:59:00Z',
    'ohlcv': {
        'o': 416.305,  # Open
        'h': 416.67,   # High
        'l': 416.28,   # Low
        'c': 416.52,   # Close
        'v': 12449     # Volume
    }
}

# Access pattern:
close_prices = []
for bar in bars:
    if 'ohlcv' in bar and bar['ohlcv']:
        close_prices.append(bar['ohlcv']['c'])  # ✅ Correct
        # NOT bar['data']['c'] ❌
        # NOT bar[ticker]['c'] ❌
```

### Algorithm Contract
**Inputs to run():**
- `current_time`: UTC string like "2024-03-15T20:00:00Z"
- `algo_id`: Integer from system database

**Required Output:**
- Must return tuple: `(action, shares)`
- `action`: String - exactly 'buy', 'sell', or 'hold'
- `shares`: Integer - number of shares (0 for hold)

### Position Calculation Pattern
```python
# Calculate current position from transactions
current_shares = 0
for tx in transactions:
    if tx['type'] == 'buy':
        current_shares += tx['shares']
    else:  # sell
        current_shares -= tx['shares']

# Or more concise:
current_shares = sum(tx['shares'] if tx['type'] == 'buy' else -tx['shares'] 
                    for tx in transactions)
```

### Testing Algorithms
```python
# Mock pattern for testing without full system
import sys
sys.path.append('.')  # Add APAC root to path

# Mock get_transactions BEFORE importing algorithm
import system_databse.system_db_manager
system_databse.system_db_manager.get_transactions = lambda x: []

# Then import and test algorithm
from algorithm.sma_crossover import Algorithm
algo = Algorithm("AAPL", 10000)
action, shares = algo.run("2024-01-31T20:00:00Z", 1)
```

### Key Design Points
- **Self-contained**: Import and use `db_manager` directly
- **Stateless**: All state derived from transaction history
- **Position tracking**: Can implement complex multi-position strategies
- **No calendar logic**: Database guarantees valid market minutes
- **Auto-fetch**: If data missing, automatically fetches from Alpaca

## FRONTEND

**Location**: `/frontend/` directory
**Configuration**: `config.js` sets API base URL (http://localhost:5000)

### Display Components
- **Algorithm cards** with colored borders (green=profit, red=loss, white=break-even)
- **PIN pad** for secure actions (default: 2020)
- **Add algorithm modal** for creating new instances
- **Horizontal scrolling** for multiple cards

### Polling Strategy
- **Market hours**: Every 30 seconds
- **After hours**: Every 60 minutes
- **Market status**: Determined by `market_open` field in API response

### Card Data Structure
```json
{
    "id": 1,
    "display_name": "NVDA_sma_crossover_20240604_143022",
    "ticker": "NVDA",
    "initial_capital": 10000.0,
    "current_shares": 125,
    "trade_count": 3,
    "current_value": 10581.25,
    "pnl": 581.25,
    "current_price": 152.00,
    "last_updated": "2024-06-04T14:35:00Z"  // From most recent transaction
}
```

## ENDPOINTS (CONNECTIVITY)

### API Server (`orchestra/api_server.py`)

**Port**: 5000

**Authentication**
- `POST /api/validate-pin` - Verify PIN for secure actions

**Algorithm Management**
- `GET /api/algorithms` - List running algorithms with calculations
  ```json
  {
      "algorithms": [...],
      "market_open": true,
      "total_account_value": 50000.00
  }
  ```
- `POST /api/algorithms` - Create new algorithm instance
- `DELETE /api/algorithms/{id}` - Stop algorithm

**System Status**
- `GET /api/available-algorithms` - Scan `/algorithm/` directory (singular)
- `GET /api/account/cash` - Available cash for new allocations
- `GET /api/market-status` - Current market open/closed state
- `GET /api/validate-ticker?symbol=NVDA` - Validate ticker for trading

### Alpaca Integration (`alpaca_wrapper.py`)
```python
class AlpacaWrapper:
    def validate_ticker(symbol) -> bool
    def get_account_cash() -> float
    def place_market_buy(ticker, shares) -> float  # Returns fill price
    def place_market_sell(ticker, shares) -> float
```

### Environment Configuration (`.env`)
```
ALPACA_API_KEY=your_api_key
ALPACA_SECRET=your_secret_key
ALPACA_PAPER=True    # False for real trading
ALPACA_FEED=iex      # 'sip' for paid tier
```

## FULL FLOW

### Algorithm Lifecycle
1. **Creation**: Frontend calls `/api/algorithms` with ticker, type, and capital
2. **Registration**: System creates database entry with auto-generated ID
3. **Execution**: Orchestrator loads algorithm module from `/algorithm/` and calls `run()` every minute
4. **Data Access**: Algorithm fetches guaranteed market-minute data (auto-fetch if missing)
5. **Decision**: Algorithm returns tuple: ('buy'/'sell'/'hold', shares)
6. **Trade**: Orchestrator executes via Alpaca and records transaction
7. **Display**: Frontend polls API and shows updated P&L

### Data Flow
1. **Real-time**: Alpaca WebSocket → `realtime_pull.py` → `stocks.db`
2. **Historical**: Algorithm request → `db_manager` → Auto-fetch if missing → `stocks.db`
3. **Calculations**: Transaction history → `card_calculations.py` → Frontend display

### Available Cash Calculation
```
Available = Alpaca Account Cash - SUM(Running Algorithm Allocations)
```

### Total Account Value
```
Total = Alpaca Account Cash + SUM(All Algorithm Current Values)
```

### File Structure
```
/APAC/
├── .env
├── system_databse/
│   ├── system.db
│   ├── system_db_manager.py
│   └── card_calculations.py
├── database/
│   ├── stocks.db
│   ├── db_manager.py
│   ├── calendar_manager.py
│   ├── historical_pull.py
│   └── realtime_pull.py
├── orchestra/
│   └── alpaca_wrapper.py
├── algorithms/
│   └── sma_crossover.py
├── api_server.py
├── orchestrator.py
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js
```