# AutoTrader Completion Roadmap

## Current Status
✅ **Completed**: System database, market-hours database, Alpaca integration, data pipelines, frontend
❌ **Remaining**: Algorithms, Orchestrator, API Server

---

## Phase 1: First Algorithm (1-2 days)

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

---

## Phase 2: API Server (2 days)

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

## Phase 3: Orchestrator Core (2-3 days)

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

## Phase 4: WebSocket Integration (2 days)

### Enhance `orchestra/orchestrator.py` - Part 2
Add WebSocketManager class for real-time data:

1. **Reference counting** for shared tickers
2. **Automatic subscription** management
3. **Separate thread** for WebSocket stream
4. **Graceful reconnection** on failures

```python
class WebSocketManager:
    def __init__(self):
        self.streamer = RealtimeStreamer()
        self.active_tickers = {}  # ticker -> count
        
    def update_subscriptions(self, running_algorithms):
        # Add/remove subscriptions based on active algorithms
```

**Testing**: Verify data flows from WebSocket → database → algorithms

---

## Phase 5: Integration Testing (2 days)

### End-to-End Testing Checklist

1. **System startup sequence**
   - Start API server on port 5000
   - Start orchestrator (initializes WebSockets)
   - Open frontend in browser

2. **Create algorithm flow**
   - Enter PIN → Add algorithm → Verify card appears
   - Check WebSocket subscription starts
   - Wait for first trade → Verify transaction recorded

3. **Market hours testing**
   - Verify orchestrator sleeps when market closed
   - Verify frontend polling adjusts (30s vs 60min)

4. **Error scenarios**
   - Algorithm crash doesn't kill orchestrator
   - WebSocket disconnect/reconnect
   - Invalid ticker handling

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
   python orchestra/api_server.py &
   python orchestra/orchestrator.py &
   chromium-browser --kiosk http://localhost:5000/frontend/dashboard.html
   ```

3. **Error recovery**
   - Automatic restart on crash
   - State persistence across restarts
   - WebSocket reconnection logic

4. **Configuration management**
   - Move hardcoded values to config file
   - Environment-specific settings

---

## Testing Strategy Throughout

### Unit Testing Priority
1. Algorithm logic (buy/sell decisions)
2. API endpoint responses
3. WebSocket subscription management
4. Trade execution flow

### Integration Testing Priority
1. Frontend → API → Database flow
2. Orchestrator → Algorithm → Alpaca flow
3. WebSocket → Database → Algorithm flow

---

## Success Metrics

✅ **Phase 1-2**: Frontend can create/display algorithm cards  
✅ **Phase 3**: Algorithms execute trades during market hours  
✅ **Phase 4**: Real-time data flows to all components  
✅ **Phase 5**: System runs for 24 hours without intervention  
✅ **Phase 6**: System auto-recovers from common failures  

**Total Timeline**: 10-14 days of focused development

---

## Critical Reminders

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
python3 algorithm/test.py    # ✅
# NOT: cd algorithm && python3 test.py ❌
```

### Return Format
Algorithms MUST return exactly: `('buy', shares)` or `('sell', shares)` or `('hold', 0)`