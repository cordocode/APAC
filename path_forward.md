# AutoTrader Completion Roadmap

## Current Status
✅ **Completed**: System database, market-hours database, Alpaca integration, data pipelines, frontend, first algorithm, API server, orchestrator core, WebSocket integration
❌ **Remaining**: Full system testing and production hardening

---

## Phase 1: First Algorithm (1-2 days) ✅ COMPLETED

### Build `algorithm/sma_crossover.py` (Note: singular 'algorithm' folder)
Create the algorithm class structure that will serve as template for all future algorithms:

```python
class Algorithm:
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.sma_short = 20
        self.sma_long = 50
    
    def run(self, current_time, algo_id):
        # Import data managers
        from database.db_manager import get_data_for_algorithm
        from system_databse.system_db_manager import get_transactions
        
        # Get data - returns [{'timestamp': '...', 'ohlcv': {...}}]
        bars = get_data_for_algorithm(
            self.ticker, 'last_n_bars', n=51, before_timestamp=current_time
        )
        
        # Extract prices correctly
        close_prices = []
        for bar in bars:
            if 'ohlcv' in bar and bar['ohlcv']:
                close_prices.append(bar['ohlcv']['c'])  # ✅ Correct access
        
        # Get position
        transactions = get_transactions(algo_id)
        position = sum(tx['shares'] if tx['type'] == 'buy' else -tx['shares'] 
                      for tx in transactions)
        
        # Must return exact tuple format
        return ('buy', 100) or ('sell', 50) or ('hold', 0)
```

**Testing**: 
```python
# test_sma.py in algorithm/ folder
import sys
sys.path.append('.')  # Add APAC root

# Mock transactions BEFORE importing
import system_databse.system_db_manager
system_databse.system_db_manager.get_transactions = lambda x: []

from algorithm.sma_crossover import Algorithm
algo = Algorithm("AAPL", 10000)
action, shares = algo.run("2024-01-31T20:00:00Z", 1)
print(f"Decision: {action} {shares} shares")
```

Run from APAC root: `python3 algorithm/test_sma.py`

**Note**: After integration, use `python3 orchestra/orchestrator.py` to run entire system

---

## Phase 2: API Server (2 days) ✅ COMPLETED (Integrated into Orchestrator)

### Build `orchestra/api_server.py`
Start with core endpoints needed for frontend functionality:

1. **PIN validation** (`/api/validate-pin`)
   - Compare against system_db_manager.get_pin()
   
2. **Algorithm listing** (`/api/algorithms`)
   - Get running algorithms with card_calculations
   - Calculate total_account_value
   - Include market_open status
   
3. **Algorithm creation** (`/api/algorithms` POST)
   - Validate ticker via alpaca_wrapper
   - Check available cash
   - Create via system_db_manager
   
4. **Supporting endpoints**
   - `/api/available-algorithms` - Scan algorithm/ directory (singular!)
   - `/api/account/cash` - Calculate available allocation
   - `/api/validate-ticker` - Check tradability

**Key Integration Points**:
- Import paths: Run from /APAC/ root
- System database path: `system_databse/system.db` (note spelling)
- Use calendar_manager for market status
- DB_PATH in system_db_manager must be "system_databse/system.db"

**Testing**: Use Postman/curl to verify each endpoint independently

---

## Phase 3: Orchestrator Core (2-3 days) ✅ COMPLETED

### Build `orchestra/orchestrator.py` - Part 1
Implement the main execution loop without WebSocket management:

1. **Market hours checking**
   ```python
   from database.calendar_manager import MarketCalendar
   calendar = MarketCalendar()
   ```

2. **Algorithm execution loop**
   - Load all running algorithms
   - Dynamically import algorithm modules from `algorithm.` (not algorithms)
   - Execute each algorithm's run() method
   - Handle returned tuple: ('buy'/'sell'/'hold', shares)
   - Execute trades via alpaca_wrapper
   - Record transactions in system.db

3. **Intelligent timing**
   ```python
   # Sleep until 2 seconds past next minute
   next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
   wakeup_time = next_minute + timedelta(seconds=2)
   ```

**Testing**: Run with single algorithm, verify trades execute and get recorded

---

## Phase 4: WebSocket Integration (2 days) ✅ COMPLETED

### Implemented Architecture
**Major Change**: API server now runs as thread inside orchestrator

**Single Process Architecture**:
```
orchestrator.py
├── Main Thread: Algorithm execution, trading
├── API Thread: Flask on port 5001 with direct WebSocket access
└── WebSocket Thread: Real-time data with reference counting
```

**Key Features Implemented**:
- WebSocketManager with reference counting
- Thread-safe operations with locks
- Automatic subscription management
- Direct integration between API and WebSocket
- Single entry point: `python3 orchestra/orchestrator.py`

---

## Phase 5: Integration Testing (2 days) - CURRENT PHASE

### What Needs Testing

#### Frontend Integration
- [ ] Does frontend config need update for port 5001? (was 5000)
- [ ] Do algorithm cards display correct real-time data?
- [ ] Does stopping algorithm from frontend unsubscribe WebSocket?

#### Data Pipeline Verification
- [ ] Are minute bars arriving at correct timestamps (XX:XX:00Z)?
- [ ] Does WebSocket data format match historical format exactly?
- [ ] Is data being stored correctly in market-hours-only database?

#### Trading Execution
- [ ] Does a buy order from algorithm get executed by orchestrator?
- [ ] Does a sell order work correctly?
- [ ] Are transactions recorded properly in system.db?
- [ ] Do Alpaca orders fill and return correct prices?

#### Algorithm Functionality
- [ ] Do algorithms handle position tracking correctly?
- [ ] Does the SMA crossover logic trigger trades as expected?
- [ ] Do algorithms recover from errors gracefully?
- [ ] Can algorithms access sufficient historical data?

---

## Phase 6: Production Hardening (1-2 days)

### Critical Additions

1. **Logging system**
   ```python
   import logging
   logging.basicConfig(
       filename='logs/orchestrator.log',
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s'
   )
   ```

2. **Startup scripts**
   ```bash
   #!/bin/bash
   # start_autotrader.sh
   cd /path/to/APAC
   python3 orchestra/orchestrator.py &
   chromium-browser --kiosk http://localhost:5001/frontend/dashboard.html
   ```

3. **Error recovery**
   - Automatic restart on crash
   - State persistence across restarts
   - WebSocket reconnection logic

4. **Configuration management**
   - Move hardcoded values to config file
   - Environment-specific settings

---

## Comprehensive Testing Checklist

### System Integration Tests
- [ ] Single process startup works (`python3 orchestra/orchestrator.py`)
- [ ] API server accessible at http://localhost:5001
- [ ] WebSocket subscriptions initialize from database on startup
- [ ] All components shut down cleanly on Ctrl+C

### Market Hours & Timing
- [ ] What happens when market closes while system is running?
- [ ] Does system correctly handle market open transition?
- [ ] Does the 2-second delay ensure fresh data for algorithms?
- [ ] Do algorithms skip execution during market closed hours?

### WebSocket & Real-time Data
- [ ] Does system correctly reconnect WebSocket after disconnection?
- [ ] Can multiple algorithms share same ticker correctly?
- [ ] Does reference counting work when stopping algorithms in different orders?
- [ ] What happens on orchestrator restart - do subscriptions restore correctly?
- [ ] Are WebSocket messages appearing in console logs?

### Trading & Position Management
- [ ] Does available cash calculation work with running algorithms?
- [ ] Do algorithm cards show correct P&L calculations?
- [ ] Is position tracking accurate across multiple trades?
- [ ] Do partial fills get handled correctly?

### Error Scenarios
- [ ] What happens if algorithm crashes during execution?
- [ ] How does system handle invalid ticker symbols?
- [ ] What if Alpaca API is down or returns errors?
- [ ] Is there database lock contention between threads?
- [ ] Does system continue if one algorithm fails?

### Edge Cases
- [ ] Can you create algorithm for ticker with no historical data?
- [ ] What happens with extremely volatile price movements?
- [ ] Does system handle pre-market/after-hours data correctly?
- [ ] Can algorithms handle stock splits or corporate actions?

### Performance & Reliability
- [ ] Are there any race conditions between threads?
- [ ] Does system run for 24+ hours without memory leaks?
- [ ] Can system handle 10+ algorithms simultaneously?
- [ ] Is database performance adequate with millions of rows?

---

## Testing Strategy Throughout

### Unit Testing Priority
1. Algorithm logic (buy/sell decisions) ✅
2. API endpoint responses ✅
3. WebSocket subscription management ✅
4. Trade execution flow

### Integration Testing Priority
1. Frontend → API → Database flow
2. Orchestrator → Algorithm → Alpaca flow
3. WebSocket → Database → Algorithm flow
4. Complete trading lifecycle

### Manual Testing Commands
```bash
# Start system
cd /path/to/APAC
python3 orchestra/orchestrator.py

# Check if data flowing (new terminal)
python3
>>> from database.db_manager import get_latest_price
>>> print(get_latest_price('NVDA'))  # Should show recent data

# Monitor logs
tail -f logs/orchestrator.log  # Once logging implemented
```

---

## Success Metrics

✅ **Phase 1-4**: Core system built and integrated  
⏳ **Phase 5**: Full system testing in progress  
❓ **Phase 6**: Production hardening pending  

**Remaining Timeline**: 3-4 days of testing and hardening

---

## Critical Reminders

### Architecture Changes
- **Port is 5001** not 5000 - frontend config may need update
- **Single process** - just run `orchestrator.py`, no separate API server
- **WebSocket Manager** handles all real-time subscriptions with reference counting

### Import Paths
- `realtime_pull.py` uses `from database.db_manager import insert_minute_data`
- All imports must use full paths from APAC root

### Folder Names & Typos
- Algorithm folder is **singular**: `/algorithm/` NOT `/algorithms/`
- System database folder: `/system_databse/` NOT `/system_database/`
- These are intentional and must be consistent everywhere

### Data Access Pattern
```python
# Data from get_data_for_algorithm comes as:
{'timestamp': '...', 'ohlcv': {'o': ..., 'h': ..., 'l': ..., 'c': ..., 'v': ...}}

# Access like:
bar['ohlcv']['c']  # ✅ Correct
# NOT bar['data']['c'] or bar[ticker]['c'] ❌
```

### Running Scripts
Always run from APAC root directory:
```bash
cd /path/to/APAC
python3 orchestra/orchestrator.py    # ✅ Single entry point
```

### Return Format
Algorithms MUST return exactly: `('buy', shares)` or `('sell', shares)` or `('hold', 0)`