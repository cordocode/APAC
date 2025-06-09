# AutoTrader Complete System Data Flows

## Overview
This document details every data flow in the AutoTrader system, including all communication between components, error handling, and timing.

## Table of Contents
1. [System Components](#system-components)
2. [Flow 1: Creating New Algorithm](#flow-1-creating-new-algorithm)
3. [Flow 2: Orchestrator Execution Cycle](#flow-2-orchestrator-execution-cycle)
4. [Flow 3: Frontend Updates](#flow-3-frontend-updates)
5. [Flow 4: Stopping Algorithm](#flow-4-stopping-algorithm)
6. [Error Flows](#error-flows)
7. [Component Communication Summary](#component-communication-summary)

---

## System Components

### Files and Their Roles
- **dashboard.js**: Frontend JavaScript that runs in browser
- **api_server.py**: Flask server listening on port 5000 (the "API")
- **orchestrator.py**: Background process running every minute
- **system_db_manager.py**: Functions for system.db operations
- **db_manager.py**: Functions for stocks.db operations
- **alpaca_wrapper.py**: Interface to Alpaca trading API
- **/algorithms/*.py**: Trading strategy files

### Databases
- **system.db**: Algorithm instances, transactions, PIN
- **stocks.db**: 1.3M minute bars of price data

---

## Flow 1: Creating New Algorithm

### Trigger: User clicks "+" card (9:29 AM)

#### 1.1 PIN Validation
```
User Action: Click "+" → Enter PIN "1234"

dashboard.js → api_server.py
POST /api/validate-pin
Body: {"pin": "1234"}

api_server.py → system_db_manager.py → system.db
Query: SELECT value FROM system_config WHERE key='pin'
Result: "1234"

Response: {"valid": true}
```

#### 1.2 Get Available Algorithms
```
dashboard.js → api_server.py
GET /api/available-algorithms

api_server.py → File System
Scan: /algorithms/ directory
Find: ["sma_crossover.py", "rsi_bounce.py", "macd_signal.py"]

Response: ["sma_crossover", "rsi_bounce", "macd_signal"]
```

#### 1.3 Get Available Cash
```
dashboard.js → api_server.py
GET /api/account/cash

api_server.py → alpaca_wrapper.py → Alpaca API
GET https://api.alpaca.markets/v2/account

Response: {"available_cash": 25000.00}
```

#### 1.4 User Submits Form
```
User fills:
- Ticker: NVDA
- Algorithm: sma_crossover  
- Allocation: $10,000

User clicks: CREATE button
```

#### 1.5 Create Algorithm (with validation)
```
dashboard.js → api_server.py
POST /api/algorithms
Body: {
  "ticker": "NVDA",
  "algorithm_type": "sma_crossover",
  "capital": 10000
}

VALIDATION STEP:
api_server.py → Alpaca API
GET https://api.alpaca.markets/v2/assets/NVDA
If invalid: Return {"error": "Invalid ticker"}
If valid: Continue...

api_server.py → system_db_manager.py
create_algorithm("NVDA", "sma_crossover", 10000)
- Generate display_name: "NVDA_sma_crossover_20240102_092915"
- Insert into algorithm_instances table
- Return id: 1

Response: {"success": true, "id": 1}
```

#### 1.6 Frontend Updates
```
Modal closes
New card appears with:
- NVDA
- SMA Crossover
- Current Total Value: $10,000
- Original Capital: $10,000
- Current Shares: 0
- Transactions: 0
```

---

## Flow 2: Orchestrator Execution Cycle

### Trigger: Market opens or minute timer (9:30 AM)

#### 2.1 Check Market Status
```python
# orchestrator.py main loop
while True:
    if is_market_open():  # Mon-Fri 9:30 AM - 4:00 PM EST
        run_all_algorithms()
    time.sleep(60)
```

#### 2.2 Get Running Algorithms
```
orchestrator.py → system_db_manager.py → system.db
Query: SELECT * FROM algorithm_instances WHERE status='running'
Result: [{
    "id": 1,
    "ticker": "NVDA",
    "algorithm_type": "sma_crossover",
    "initial_capital": 10000
}]
```

#### 2.3 For Each Algorithm...

##### 2.3.1 Load Algorithm Module
```python
orchestrator.py → File System
import algorithms.sma_crossover
algorithm = sma_crossover.Algorithm("NVDA", 10000)
```

##### 2.3.2 Calculate Current Position
```
orchestrator.py → system_db_manager.py → system.db
Query: SELECT type, shares FROM transactions WHERE algorithm_id=1
Calculate: SUM(buy shares) - SUM(sell shares) = 0
```

##### 2.3.3 Get Algorithm's Data Requirements
```
orchestrator.py → algorithm instance
current_time = "2024-01-02T14:30:00Z"
algorithm.get_data_requirements(current_time)

Returns: {
    "start_date": "2024-01-02T11:10:00Z",  # 200 minutes before now
    "end_date": "2024-01-02T14:30:00Z"      # now
}
```

##### 2.3.4 Fetch Market Data
```
orchestrator.py → db_manager.py → stocks.db
get_historical_data("NVDA", start_date, end_date)

Query: SELECT minute_timestamp, NVDA FROM stock_prices 
       WHERE minute_timestamp BETWEEN start AND end
       AND NVDA IS NOT NULL

Returns: 200 bars of OHLCV data
```

##### 2.3.5 Run Algorithm Logic
```python
orchestrator.py → algorithm
decision, shares = algorithm.on_data(bars, position=0)

# Algorithm calculates:
# - 20-period SMA = 233.45
# - 50-period SMA = 232.90
# - 20 > 50, so BUY signal
Returns: ('buy', 42)
```

##### 2.3.6 Execute Trade
```
orchestrator.py → alpaca_wrapper.py → Alpaca API
POST /v2/orders
{
    "symbol": "NVDA",
    "qty": 42,
    "side": "buy",
    "type": "market"
}

Returns: {"filled_avg_price": 234.52}
```

##### 2.3.7 Record Transaction
```
orchestrator.py → system_db_manager.py → system.db
INSERT INTO transactions VALUES (1, 'buy', 42, 234.52, '2024-01-02T14:30:00Z')
```

---

## Flow 3: Frontend Updates

### Trigger: JavaScript timer every 30 seconds (9:30:30 AM)

#### 3.1 Request All Algorithms
```javascript
// dashboard.js
setInterval(function() {
    fetch('/api/algorithms')
        .then(response => response.json())
        .then(data => updateCards(data));
}, 30000);  // 30000ms = 30 seconds
```

#### 3.2 API Gathers Full Data
```
api_server.py → system_db_manager.py
get_all_algorithms_with_calculations()

For each algorithm:
1. Get basic info from algorithm_instances
2. Calculate position from transactions (42 shares)
3. Get latest price from stocks.db (234.45)
4. Calculate:
   - current_value = 42 × 234.45 = 9,846.90
   - pnl = 9,846.90 - 10,000 = -153.10
   - trade_count = 1
5. Get last transaction time
```

#### 3.3 Return Complete Data
```json
[{
    "id": 1,
    "ticker": "NVDA",
    "algorithm_type": "sma_crossover",
    "initial_capital": 10000,
    "current_shares": 42,
    "current_value": 9846.90,
    "pnl": -153.10,
    "trade_count": 1,
    "last_update": "9:30 AM"
}]
```

#### 3.4 Update Display
```
Card border: Red (negative P&L)
P&L display: -$153.10
Current Total Value: $9,847
Current Shares: 42
Transactions: 1
Last Updated: 9:30 AM
```

---

## Flow 4: Stopping Algorithm

### Trigger: User clicks STOP button (10:15 AM)

#### 4.1 PIN Validation
```
Same as Flow 1.1
```

#### 4.2 Get Current State for Confirmation
```
dashboard.js → api_server.py
GET /api/algorithms/1

Shows modal:
"Stopping NVDA algorithm will sell all 42 shares"
"This will realize a loss of $153.10"
[CONFIRM] [CANCEL]
```

#### 4.3 Execute Stop
```
User clicks: CONFIRM

dashboard.js → api_server.py
DELETE /api/algorithms/1
```

#### 4.4 Sell All Shares
```
api_server.py:
1. Calculate position (42 shares)
2. Place sell order via Alpaca
3. Record sell transaction
4. Update algorithm status to 'stopped'
```

#### 4.5 Frontend Updates
```
Card disappears immediately
Header dot changes color
```

---

## Error Flows

### Market Closed
```
orchestrator.py: is_market_open() returns False
Action: Sleep 60 minutes instead of 1 minute
```

### No Price Data
```
db_manager.get_latest_price() returns None
Action: Use last known price or display "No Data"
```

### Alpaca API Error
```
alpaca_wrapper.place_market_buy() throws exception
Action: Log error, skip trade, continue with next algorithm
No transaction recorded
```

### Algorithm Crash
```
algorithm.on_data() throws exception
Action: Catch, log error, continue with next algorithm
```

### Invalid Ticker
```
Alpaca validation returns not tradable
Action: Return error to frontend, keep modal open
```

### Insufficient Funds
```
Capital requested > available cash
Action: Show error in modal
```

---

## Component Communication Summary

### Frontend (dashboard.js) calls:
- `POST /api/validate-pin` - Check PIN
- `GET /api/algorithms` - Get all cards data
- `POST /api/algorithms` - Create new algorithm
- `DELETE /api/algorithms/{id}` - Stop algorithm
- `GET /api/available-algorithms` - List algorithm types
- `GET /api/account/cash` - Available funds

### API Server (api_server.py) calls:
- system_db_manager functions for database operations
- alpaca_wrapper functions for trading
- File system for available algorithms

### Orchestrator (orchestrator.py) calls:
- system_db_manager for algorithm list and transactions
- db_manager for market data
- Algorithm files for trading decisions
- alpaca_wrapper for trade execution

### Internal Functions Never Called by Frontend:
- db_manager functions (only called internally)
- Direct database queries (always through managers)
- Algorithm logic (only orchestrator runs these)

---

## Timing Considerations

### Orchestrator
- Runs every 60 seconds during market hours
- Runs every 60 minutes outside market hours

### Frontend Updates
- Every 30 seconds during market hours
- Every 60 minutes outside market hours

### Critical Timing
- All timestamps stored as UTC with 'Z' suffix
- Display converts to local time
- Market hours: 9:30 AM - 4:00 PM EST/EDT

### Data Freshness
- Price data: Maximum 1 minute old (orchestrator cycle)
- Card display: Maximum 30 seconds old (frontend poll)
- Trades execute within seconds of algorithm decision