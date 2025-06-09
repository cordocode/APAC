AutoTrader Complete Build Roadmap
Project Overview
A personal wall-mounted trading terminal running on Raspberry Pi that automates stock trading through pluggable algorithms. The system displays real-time P&L on a terminal-aesthetic dashboard and executes trades through Alpaca's API.

Core Architecture
Frontend: Simple HTML/JS dashboard with black background, white text

Cards have colored borders: green (profit), red (loss), white (break-even)

API Server: Flask endpoints connecting frontend to backend

Orchestrator: Background process running algorithms every minute and managing WebSockets

Algorithms: Pluggable Python files making trading decisions

Databases: stocks.db (market data) and system.db (algorithm state)

Integration: Alpaca API wrapper for executing trades

Real-time Data: WebSocket streams managed by orchestrator

What's Already Built ✅
stocks.db - Pre-populated with 3.27M minute timestamps (2018-2030) - UPDATED: Now 9:30 AM - 3:59 PM EST (390 bars/day)

db_manager.py - Functions for reading/writing market data - UPDATED: Added smart data fetching

historical_pull.py - Fetches historical minute bars from Alpaca

realtime_pull.py - WebSocket streamer for live data - ✅ VERIFIED & FIXED

system.db - Complete database with algorithm_instances, transactions, system_config tables

system_db_manager.py - All core database functions with UTC timezone handling

card_calculations.py - Complete P&L calculation engine for frontend display

alpaca_wrapper.py - ✅ COMPLETED - Alpaca trading API interface

Build Order & Dependencies
Phase 1: Foundation Components (Build First) ✅ COMPLETED
1.1 System Database (system.db)
Purpose: Store algorithm instances, transactions, and PIN

File Location: system_databse/system.db (note: databse intentionally misspelled)
Creation Script: system_databse/create_system_db.py

Complete Schema Built:

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

Critical Database Design Decisions:

No stored calculations: Never store current_shares, current_value, pnl - always calculate from transactions

UTC timestamps only: All timestamps use format "YYYY-MM-DDTHH:MM:SSZ" to match stocks.db

Foreign key constraints: Enabled to prevent orphan transactions

Soft delete pattern: Use status='stopped' rather than DELETE

Auto-incrementing IDs: SQLite creates sqlite_sequence table automatically

Key Design Decisions:

Auto-incrementing integer IDs for algorithms

Store initial_capital (the allocation) per algorithm

Calculate all other values dynamically:

Current shares from transaction history

Invested amount from transaction costs

Uninvested cash = initial_capital - invested

Current value = (shares × price) + uninvested cash

P&L = current value - initial_capital

Soft delete with status field ('running' or 'stopped')

Store algorithm type as string matching filename

Dependency Note: Frontend will call APIs that query this database, but those APIs don't exist yet.

1.2 System Database Manager (system_db_manager.py)
Purpose: Functions to interact with system.db

File Location: system_databse/system_db_manager.py (note: databse is intentionally misspelled)
Database Location: system_databse/system.db

Core Functions Built:

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

Critical Implementation Details:

All timestamps: Use datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") format

Database returns: Dictionaries (not tuples) due to conn.row_factory = sqlite3.Row

Foreign keys: Enabled with PRAGMA foreign_keys = ON

Error handling: Functions use try/except with proper rollback on database operations

Transaction safety: All write operations use proper commit/rollback patterns

Card Calculations (card_calculations.py):
File Location: system_databse/card_calculations.py

Functions Built:

# Position calculations
calculate_position(algo_id: int) -> int  # Current shares from transaction history
calculate_trade_count(algo_id: int) -> int  # Total transaction count
calculate_invested_amount(algo_id: int) -> float  # Net invested cash
calculate_current_value(algo_id: int, current_price: float, initial_capital: float) -> float
calculate_pnl(current_value: float, initial_capital: float) -> float

# Complete card data for frontend
get_algorithm_with_calculations(algo_id: int, current_price: float) -> Optional[Dict[str, Any]]

Returned Dict Structure (from get_algorithm_with_calculations):

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

P&L Calculation Logic (implemented):

# Calculation flow in card_calculations.py:
shares = SUM(buy_shares) - SUM(sell_shares)  # From transaction history
invested_amount = SUM(buy_costs) - SUM(sell_proceeds)  # Net cash invested
uninvested_cash = initial_capital - invested_amount  # Remaining allocation
current_value = (shares * current_price) + uninvested_cash
pnl = current_value - initial_capital

Critical: All timestamps must use UTC with 'Z' suffix to match stocks.db format.
Implementation: Use datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") everywhere.

Built Functions Available for Import:

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

Algorithm Card Data Structure (returned by get_algorithm_with_calculations):

{
    'id': 1, 'display_name': 'NVDA_sma_crossover_20240604_143022',
    'algorithm_type': 'sma_crossover', 'ticker': 'NVDA', 'initial_capital': 10000.0,
    'status': 'running', 'created_at': '2024-06-04T14:30:22Z', 'stopped_at': None,
    'current_shares': 125, 'trade_count': 3, 'current_value': 10581.25, 
    'pnl': 581.25, 'current_price': 152.00
}

1.3 Alpaca Wrapper (alpaca_wrapper.py) ✅ COMPLETED
Purpose: Interface to Alpaca trading API

File Location: orchestra/alpaca_wrapper.py

Core Functions Built:

class AlpacaWrapper:
    def __init__(self)  # Initializes with paper/real mode from .env
    def validate_ticker(symbol: str) -> bool
    def get_account_cash() -> float  # Total cash in Alpaca account
    def place_market_buy(ticker: str, shares: int) -> float  # Returns fill price
    def place_market_sell(ticker: str, shares: int) -> float  # Returns fill price

Import Statement:

from orchestra.alpaca_wrapper import AlpacaWrapper

Environment Variables Required in .env:

# Alpaca API credentials
ALPACA_API_KEY=your_api_key
ALPACA_SECRET=your_secret_key

# Trading mode configuration
ALPACA_PAPER=True  # Set to False for real trading
ALPACA_FEED=iex    # Use 'iex' for free tier, 'sip' for paid tier

Critical Production vs Paper Trading:

Paper Trading: Set ALPACA_PAPER=True in .env (default)

Real Trading: Set ALPACA_PAPER=False in .env

Data Feed: Free tier must use ALPACA_FEED=iex, paid tier can use ALPACA_FEED=sip

These settings apply to all Alpaca integrations (historical_pull, realtime_pull, alpaca_wrapper)

Integration Notes:

Wrapper prints mode on initialization: "✅ Alpaca client initialized in PAPER mode with iex feed"

All timestamps handled in UTC to match system databases

Market orders only (no limit orders currently)

Includes retry logic for order fills

Note: get_account_cash() returns total Alpaca account cash, not available for allocation. The API layer calculates available allocation cash.

1.4 Database Manager Updates (db_manager.py) ✅ UPDATED
Critical Updates Made:

1. Market Hours Fixed:

Old: 9:30 AM - 4:00 PM EST (391 bars)

New: 9:30 AM - 3:59 PM EST (390 bars)

Last minute bar is now 3:59 PM (20:59 UTC)

Database has ~3.27 million rows total

2. Smart Data Fetching Function Added:

def get_data_for_algorithm(ticker, requirement_type, **kwargs):
    """
    Single entry point for all algorithm data needs.
    Automatically fetches missing data if needed.
    
    Args:
        ticker: Stock symbol
        requirement_type: Either 'last_n_bars' or 'time_range'
        **kwargs: 
            For 'last_n_bars': n=200, before_timestamp=None
            For 'time_range': start='2024-01-02T09:30:00Z', end='2024-01-02T20:59:00Z'
    
    Returns:
        List of bars with {timestamp, ohlcv} dicts in chronological order
    """

Key Features:

Auto-fetches missing data using HistoricalFetcher

Handles weekends/holidays automatically (NULL values skipped)

Returns data in chronological order (oldest first)

Calculates how many days to fetch based on missing bars

Works seamlessly with existing database structure

3. Existing Functions Remain:

initialize_database() - Now creates 390 bars per day

add_ticker_if_missing(ticker) - Auto-adds ticker columns

insert_minute_data() - For real-time updates

get_historical_data() - Basic time range query

get_latest_price() - Most recent price

check_data_exists() - Identifies missing data

insert_historical_data() - Bulk insert

Phase 2: Algorithm Framework
2.1 Base Algorithm Structure
Location: /algorithms/ directory

UPDATED Interface - Algorithms Are Self-Contained:

class Algorithm:
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
    
    def run(self, current_time, algo_id):
        """
        Main entry point called by orchestrator.
        Algorithm handles everything internally.
        
        Args:
            current_time: Current UTC timestamp
            algo_id: Algorithm instance ID for transaction history
            
        Returns:
            tuple: (action, shares) where action is 'buy', 'sell', or 'hold'
        """
        # Algorithm gets its own data
        bars = db_manager.get_data_for_algorithm(
            ticker=self.ticker,
            requirement_type='last_n_bars',  # or 'time_range'
            n=200,  # or start/end for time_range
            before_timestamp=current_time
        )
        
        # Algorithm gets its own transaction history
        transactions = system_db_manager.get_transactions(algo_id)
        
        # Calculate position and make decision
        position = self._calculate_position(transactions)
        action, shares = self._make_decision(bars, position, transactions)
        
        return (action, shares)

Critical Design Change:

Orchestrator only calls algorithm.run(current_time, algo_id)

Algorithm internally imports and uses db_manager and system_db_manager

Algorithm is responsible for getting its own data and transaction history

Data Access Pattern:

# In algorithm file
import sys
sys.path.append('..')  # To import from parent directory
from database import db_manager
import system_db_manager

Critical Multiple Position Support:
Algorithms receive complete transaction history for independent position tracking:

transaction_history = [
    {"id": 1, "type": "buy", "shares": 100, "price": 150.50, "timestamp": "2024-06-04T14:30:00Z"},
    {"id": 2, "type": "buy", "shares": 50, "price": 145.25, "timestamp": "2024-06-04T14:31:00Z"},
    {"id": 3, "type": "sell", "shares": 25, "price": 155.75, "timestamp": "2024-06-04T14:32:00Z"}
]
# Algorithm can track: "$150.50 position vs $145.25 position independently"

Important Allocation Concept:

Algorithm receives initial_capital (e.g., $10,000) as its allocation

Algorithm decides how much to invest (might only use $6,000)

Remaining allocation stays as uninvested cash within that card

Algorithms don't know about other algorithms or total account balance

Key Points:

Algorithms are stateless between runs

Return values: ('buy', shares), ('sell', shares), or ('hold', 0)

Time calculations must be in UTC

Algorithms handle their own data fetching using db_manager

Algorithms get transaction history via system_db_manager

2.2 First Algorithm (sma_crossover.py)
Purpose: Prove the pattern works

Logic: Buy when 20-period SMA crosses above 50-period SMA

Implementation Pattern:

class Algorithm:
    def __init__(self, ticker, initial_capital):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.sma_short = 20
        self.sma_long = 50
    
    def run(self, current_time, algo_id):
        # Get last 50 bars (enough for longest SMA)
        bars = db_manager.get_data_for_algorithm(
            ticker=self.ticker,
            requirement_type='last_n_bars',
            n=self.sma_long,
            before_timestamp=current_time
        )
        
        if len(bars) < self.sma_long:
            return ('hold', 0)  # Not enough data
        
        # Calculate SMAs and make decision...

Phase 3: Orchestration Layer
3.1 API Server (api_server.py)
Purpose: REST endpoints for frontend

Endpoints:

POST /api/validate-pin - Check PIN

GET /api/algorithms - Get all running algorithms with calculations

POST /api/algorithms - Create new algorithm

DELETE /api/algorithms/{id} - Stop algorithm

GET /api/available-algorithms - Scan /algorithms/ directory

GET /api/account/cash - Calculate available cash for new allocations

Get total cash from Alpaca account

Subtract sum of all running algorithms' initial_capital

Returns the amount available to allocate to new algorithms

NOT the raw Alpaca cash balance

Critical Integration Requirements:

Import statements needed:

import system_db_manager
import card_calculations
from orchestra.alpaca_wrapper import AlpacaWrapper  # Now available!

Database path: Code must run from parent directory of system_databse/

Function calls: Use exact function signatures from system_db_manager.py

Note for WebSocket coordination: API server does NOT manage WebSockets - that's the orchestrator's job

Critical Dependency Issue:

Frontend expects /api/account/cash which needs both alpaca_wrapper AND system_db_manager

Must query Alpaca for total cash

Must sum all algorithm allocations from system.db

Frontend expects algorithm calculations but needs system_db_manager

Solution: Build these endpoints after dependencies are ready

Required Import Statements:

import system_db_manager
import card_calculations  
from orchestra.alpaca_wrapper import AlpacaWrapper

Critical Function Calls:

PIN validation: system_db_manager.get_pin()

Get algorithms: system_db_manager.get_all_algorithms('running')

Get card data: card_calculations.get_algorithm_with_calculations(id, current_price)

Create algorithm: system_db_manager.create_algorithm(ticker, algo_type, initial_capital)

Stop algorithm: system_db_manager.stop_algorithm(id)

Available cash:

wrapper = AlpacaWrapper()
alpaca_cash = wrapper.get_account_cash()
available = alpaca_cash - sum(algo['initial_capital'] for algo in running_algorithms)

Handling No Initial Price: When calling card_calculations.get_algorithm_with_calculations, the API server must first get the current_price. If db_manager.get_latest_price() returns None (which will happen for a new ticker with no data yet), the API server must handle this gracefully. It should pass a default price of 0.0, which will correctly result in a calculated P&L of $0.00 until the first price data is recorded.

3.2 Orchestrator (orchestrator.py)
Purpose: Run algorithms every minute during market hours AND manage real-time WebSocket subscriptions

Important: Orchestrator and frontend are completely separate processes. They coordinate through the database only.

Core Responsibilities:

Algorithm Execution: Run each algorithm's logic at the optimal time.

WebSocket Management: Intelligently manage real-time data streams.

Trade Execution: Execute trades via Alpaca and record transactions.

Orchestrator Main Loop - UPDATED & VERIFIED:
The main loop will not use a simple time.sleep(60). It will use an intelligent timing mechanism to ensure algorithms run as close to real-time as possible after new data arrives.

# In orchestrator.py's main loop
import time
from datetime import datetime, timedelta, timezone

def run_orchestrator():
    # ... (websocket_manager setup and initial subscription logic goes here) ...

    while True:
        if is_market_open():
            # --- Run algorithm logic ---
            print(f"Orchestrator cycle started at {datetime.now(timezone.utc)}")
            run_all_algorithms() 
            
            # --- Intelligent Sleep Logic ---
            now = datetime.now(timezone.utc)
            # Calculate the start of the next minute
            next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            
            # Add a 2-second buffer based on verified WebSocket latency
            # This ensures the next bar has arrived and been written to the DB.
            wakeup_time = next_minute + timedelta(seconds=2)
            
            sleep_duration = (wakeup_time - now).total_seconds()
            
            # Ensure sleep duration is not negative if the loop took too long
            if sleep_duration > 0:
                print(f"Sleeping for {sleep_duration:.2f} seconds until {wakeup_time}")
                time.sleep(sleep_duration)
            
        else:
            # If market is closed, sleep for a longer duration
            print("Market is closed. Sleeping for 15 minutes.")
            time.sleep(60 * 15)

Flow:

Startup:

Check if market is open (EST timezone).

Get all running algorithms from system.db.

Initialize WebSocketManager and start subscriptions for all needed tickers.

Every Cycle (During Market Hours):

Wake Up: The loop wakes up at 2 seconds past the minute mark (e.g., at 11:31:02).

Run Algos: It immediately gets all running algorithms and executes their .run() method, passing the current UTC time. The algorithms now have access to the fresh data from the previous minute (e.g., the 11:30 bar).

Execute Trades: It executes any 'buy' or 'sell' signals via the AlpacaWrapper.

Update Sockets: It checks if any algorithms were started/stopped and updates WebSocket subscriptions.

Sleep Intelligently: It calculates the exact duration needed to sleep until 2 seconds past the next minute mark and sleeps.

WebSocket Management Architecture:
The orchestrator includes a WebSocketManager class that:

Tracks which tickers need real-time data based on running algorithms

Subscribes/unsubscribes to WebSocket streams as algorithms start/stop

Handles multiple algorithms using the same ticker (reference counting)

Automatically restores WebSocket connections on system restart

Runs WebSocket stream in a separate daemon thread

Dependencies: Needs everything built so far.
Required Imports:

import system_db_manager
from orchestra.alpaca_wrapper import AlpacaWrapper
from database.realtime_pull import RealtimeStreamer
import threading
import importlib  # For dynamic algorithm loading

Algorithm Loading Pattern:

# Load algorithm module dynamically
module = importlib.import_module(f'algorithms.{algo["algorithm_type"]}')
algorithm = module.Algorithm(algo['ticker'], algo['initial_capital'])

# Run algorithm (it handles its own data fetching)
current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
decision, shares = algorithm.run(current_time, algo['id'])

Trade Execution Pattern:

wrapper = AlpacaWrapper()
if action == 'buy':
    fill_price = wrapper.place_market_buy(ticker, shares)
    system_db_manager.record_buy(algo_id, shares, fill_price)
elif action == 'sell':
    fill_price = wrapper.place_market_sell(ticker, shares)
    system_db_manager.record_sell(algo_id, shares, fill_price)

System Restart Handling:

On startup, orchestrator queries all running algorithms

WebSocketManager automatically subscribes to all needed tickers

No manual intervention required - system self-heals

Integration with Real-time Data:

Uses realtime_pull.RealtimeStreamer class

Runs WebSocket in separate thread to not block algorithm execution

Data flows: WebSocket → stocks.db → algorithms read latest data

Phase 4: Frontend
4.1 Dashboard HTML/CSS/JS
Purpose: Display algorithm cards and handle user interaction

Components:

Algorithm cards showing P&L, shares, transactions

PIN pad for secure actions

Add algorithm modal

Horizontal scrolling for multiple cards

Polling Strategy:

Market hours: Every 30 seconds

Off hours: Every 60 minutes

How it knows: Each /api/algorithms response includes "market_open": true/false

Frontend adjusts polling interval based on this flag

Market Hours Coordination: Backend includes "market_open": true/false in API responses so frontend doesn't need to calculate EST time.

Real-time Data Note: Frontend doesn't need to know about WebSockets - it just polls the API which reads from stocks.db where real-time data is stored.

Dependencies: Needs all API endpoints working.

File Structure & Integration Map
/APAC/                                # Root directory
├── .env                              # Environment variables (API keys, paper/real mode)
├── system_databse/                   # System database components (misspelled intentionally)
│   ├── system.db                     # Main database file
│   ├── create_system_db.py          # Database creation script
│   ├── system_db_manager.py         # Core database functions
│   └── card_calculations.py         # Frontend calculation engine
├── database/                         # Market data
│   ├── stocks.db                     # Pre-populated market data (3.27M rows, 390 bars/day)
│   ├── db_manager.py                # Market data functions (includes smart fetching)
│   ├── historical_pull.py           # Historical data fetcher
│   ├── realtime_pull.py             # WebSocket streamer (managed by orchestrator)
│   └── smoke.py                     # Simple database initialization script
├── orchestra/                        # Orchestration components
│   └── alpaca_wrapper.py            # ✅ Alpaca API wrapper (COMPLETED)
├── algorithms/                       # Algorithm files (to be built)
│   ├── sma_crossover.py
│   └── [other_algorithm].py
├── api_server.py                     # Flask API (to be built)
├── orchestrator.py                   # Algorithm runner + WebSocket manager (to be built)
└── frontend/                         # Dashboard (to be built)
    ├── index.html
    ├── style.css
    └── script.js

Import Dependencies:

api_server.py imports: system_db_manager, card_calculations, AlpacaWrapper

orchestrator.py imports: system_db_manager, AlpacaWrapper, RealtimeStreamer, algorithm modules

algorithms import: db_manager, system_db_manager (they fetch their own data)

card_calculations.py imports: system_db_manager

Running location: All Python files run from /APAC/ root directory

Critical Integration Points & Conflicts
1. Timezone Handling
Conflict: Multiple components handle time differently
Solution: Everything internal uses UTC with 'Z' suffix

Exception: Market hours checks use Eastern Time

Display: Frontend converts UTC to user's local time

Critical Implementation:

Python UTC: Use datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") everywhere

Database format: All timestamps exactly match stocks.db: "2024-06-04T14:30:22Z"

Never use: datetime.now() without timezone - returns server time (Mountain)

Market Hours: 9:30 AM - 4:00 PM EST (last bar at 3:59 PM EST/20:59 UTC)

2. Algorithm Discovery
Potential Confusion: Where does the list of available algorithms come from?

Answer: API server scans /algorithms/ directory

Not: Stored in database or hardcoded

3. Cash Balance & Allocation Tracking
Two Different Concepts:

Algorithm Allocation:

Each card is given an initial_capital amount (e.g., $10,000)

This is the card's "allocation" - money reserved for this algorithm

Card might only have $6,000 invested, keeping $4,000 as cash reserve

Available Cash for New Cards:

Formula: Alpaca Cash - SUM(all running algorithms' initial_capital)

This prevents over-allocating beyond actual account balance

Example: $50k Alpaca cash - $30k allocated = $20k available for new cards

P&L Calculation (separate concept):

P&L = Current Value - Initial Capital

Current Value = (Shares × Current Price) + Unallocated Cash within card

This is per-card performance tracking

4. Position Calculation
Critical: Current shares are CALCULATED from transaction history

How: Sum all buy transactions minus all sell transactions for that algorithm

Never: Store a "current_shares" field in the database

Why: Single source of truth - the transaction history

Implementation: Use card_calculations.calculate_position(algo_id) which executes:

SELECT SUM(CASE WHEN type = 'buy' THEN shares ELSE -shares END) 
FROM transactions WHERE algorithm_id = ?

5. Frontend Polling & Market Hours
Issue: Frontend and orchestrator run independently - how does frontend know market hours?

Frontend runs: Independent JavaScript timer in the browser

Orchestrator runs: Separate Python process on the server

They don't communicate directly

Solution: Frontend must determine market status independently

Option 1: Add /api/market-status endpoint that returns {"is_open": true}

Option 2: Frontend calculates EST time in JavaScript

Option 3: Include market status in every /api/algorithms response

Recommendation: Option 3 - Include "market_open": true in API responses to avoid timezone math in JavaScript

6. Real-time Data Flow
Critical Design: WebSocket management is centralized in the orchestrator

Why orchestrator: Already knows all running algorithms and their tickers

Reference counting: Multiple algorithms can share same ticker WebSocket

Data flow: Alpaca WebSocket → realtime_pull.py → stocks.db → algorithms read

Frontend unaware: Frontend just polls API, doesn't know about WebSockets

Restart resilience: Orchestrator automatically restores all WebSocket connections

WebSocket Lifecycle:

Algorithm created → Orchestrator adds ticker to WebSocket subscriptions

Multiple algorithms same ticker → WebSocket stays open (reference counted)

Algorithm stopped → Orchestrator checks if any other algorithm needs that ticker

Last algorithm using ticker stopped → WebSocket unsubscribed

System restart → Orchestrator queries all algorithms and restores subscriptions

7. Algorithm Data Access
Critical Design Change: Algorithms are self-contained

Old design: Orchestrator fetches data and passes to algorithm

New design: Algorithm uses db_manager.get_data_for_algorithm() internally

Benefits:

Cleaner separation of concerns

Algorithms can request exactly what they need

Orchestrator doesn't need to understand algorithm data requirements

Smart fetching: If data is missing, automatically fetches from Alpaca

Multiple Position Tracking Architecture
Critical Design Decision Made: Algorithms can track multiple independent positions using transaction history

How It Works:

Algorithm receives complete transaction list via system_db_manager.get_transactions(algo_id)

Full transaction history structure:

[
    {"id": 1, "algorithm_id": 2, "type": "buy", "shares": 100, "price": 150.50, "timestamp": "2024-06-04T14:30:00Z"},
    {"id": 2, "algorithm_id": 2, "type": "buy", "shares": 50, "price": 145.25, "timestamp": "2024-06-04T14:31:00Z"},
    {"id": 3, "algorithm_id": 2, "type": "sell", "shares": 25, "price": 155.75, "timestamp": "2024-06-04T14:32:00Z"}
]

Algorithm can implement position tracking logic like:

"Track $150.50 buy separately from $145.25 buy"

"Exit $150.50 position when price hits $160"

"Exit $145.25 position when price hits $155"

Frontend displays: Calculated totals only (current_shares: 125, pnl: $581.25)

Algorithm receives: Complete granular history for position management

Error Handling Requirements
In system_db_manager.py
def record_buy(algo_id, shares, price):
    try:
        conn.execute("BEGIN")
        # ... insert transaction ...
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise  # Let caller handle

In orchestrator.py
wrapper = AlpacaWrapper()
websocket_manager = WebSocketManager()

for algorithm in running_algorithms:
    try:
        # Run algorithm logic
        decision, shares = algorithm.run(current_time, algo['id'])
        
        if decision == 'buy':
            try:
                # Attempt trade
                fill_price = wrapper.place_market_buy(ticker, shares)
                # Only record if trade succeeds
                system_db_manager.record_buy(algo_id, shares, fill_price)
            except Exception as e:
                log_error(f"Trade failed for {ticker}: {e}")
                # No transaction recorded - continue to next algorithm
                
    except Exception as e:
        log_error(f"Algorithm {algorithm.id} crashed: {e}")
        continue  # Skip to next algorithm, don't crash orchestrator

# WebSocket errors handled separately
try:
    websocket_manager.update_subscriptions(running_algorithms)
except Exception as e:
    log_error(f"WebSocket update failed: {e}")
    # Continue running - don't crash on WebSocket issues

In alpaca_wrapper.py ✅ COMPLETED
def place_market_buy(ticker, shares):
    try:
        response = alpaca_api.submit_order(...)
        return response.filled_avg_price
    except Exception as e:
        log_error(f"Trade failed: {e}")
        raise  # Let orchestrator decide whether to record transaction

In api_server.py
@app.route('/api/algorithms/<int:id>')
def get_algorithm(id):
    algo = system_db_manager.get_algorithm(id)
    if algo is None:
        return jsonify({"error": "Algorithm not found"}), 404
    return jsonify(algo)

Testing Strategy
Phase 1 Testing ✅ COMPLETED
Created test algorithm instance with $10,000 allocation

Recorded sample buy transaction (50 shares at $100)

Verified position calculation shows 50 shares

Verified P&L calculation with mock current price

Tested available cash calculation with multiple algorithms

Alpaca Wrapper Testing: Successfully bought and sold AAPL shares in paper account

Database Testing: Verified 390 bars per day, no 4:00 PM timestamps

Phase 2 Testing
Run single algorithm in isolation

Verify data requirements work with smart fetching

Test buy/sell decisions

Test algorithm's internal data fetching

Phase 3 Testing
Start with market closed (no trades)

Test with single algorithm

Verify transaction recording

Confirm orchestrator and frontend work independently

WebSocket Testing:

Start orchestrator with one algorithm

Verify WebSocket opens for that ticker

Add second algorithm with same ticker

Verify WebSocket stays open

Stop first algorithm

Verify WebSocket still open

Stop second algorithm

Verify WebSocket closes

Phase 4 Testing
Mock API responses initially

Test PIN validation

Verify card updates

Test market status flag updates polling interval

Minimal Code Examples
Display Name Generation
f"{ticker}_{algo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

Market Hours Check
eastern = pytz.timezone('US/Eastern')
now = datetime.now(eastern)
is_open = weekday < 5 and time(9,30) <= now.time() <= time(16,0)

Position Calculation
SELECT SUM(CASE WHEN type='buy' THEN shares ELSE -shares END) 
FROM transactions WHERE algorithm_id = ?

Available Cash Calculation
from orchestra.alpaca_wrapper import AlpacaWrapper

wrapper = AlpacaWrapper()
alpaca_cash = wrapper.get_account_cash()
running_algos = system_db_manager.get_all_algorithms('running')
allocated = sum(algo['initial_capital'] for algo in running_algos)
available = alpaca_cash - allocated

WebSocket Subscription Update
# In orchestrator's WebSocketManager
needed_tickers = {}
for algo in running_algorithms:
    ticker = algo['ticker']
    needed_tickers[ticker] = needed_tickers.get(ticker, 0) + 1

# Subscribe to new tickers
for ticker in needed_tickers:
    if ticker not in self.active_tickers:
        self.streamer.subscribe(ticker)

# Unsubscribe from unused tickers
for ticker in list(self.active_tickers.keys()):
    if ticker not in needed_tickers:
        self.streamer.unsubscribe(ticker)

Algorithm Data Fetching
# Inside algorithm's run() method
bars = db_manager.get_data_for_algorithm(
    ticker=self.ticker,
    requirement_type='last_n_bars',
    n=200,
    before_timestamp=current_time
)

# Or for time range
bars = db_manager.get_data_for_algorithm(
    ticker=self.ticker,
    requirement_type='time_range',
    start='2025-01-02T14:30:00Z',
    end='2025-01-07T20:59:00Z'
)

Missing Components to Add
1. Startup Script
Why Needed: Raspberry Pi must auto-start everything on boot

Start API server

Start orchestrator (which handles WebSockets)

Open browser to dashboard

2. Configuration File
Why Needed: Store API keys and settings

Already have .env for Alpaca keys

May need config.json for other settings

3. Error Logging
Why Needed: Debug issues on headless Pi

Simple file-based logging

Rotate daily to prevent disk fill

Separate logs for orchestrator, API, and WebSocket events

Build Sequence Summary
Day 1-2: ✅ COMPLETED - System database and manager functions

Created system_databse/system.db with complete schema

Built system_db_manager.py with all core functions

Built card_calculations.py with P&L calculation engine

Implemented proper UTC timezone handling

Day 3: ✅ COMPLETED - Database updates and Alpaca wrapper

Built orchestra/alpaca_wrapper.py with all trading functions

Fixed market hours to 9:30 AM - 3:59 PM (390 bars/day)

Added get_data_for_algorithm() smart fetching to db_manager.py

Configured paper/real trading via .env variables

Day 4: ✅ COMPLETED - Real-time data pipeline verification and fix.

Day 5: Algorithm framework & Orchestrator Timing Logic.

Build base algorithm structure with self-contained data fetching.

Implement sma_crossover.py as first algorithm.

Implement the Orchestrator's intelligent timing loop as defined above.

Day 6: API server and full Orchestrator implementation.

Day 7-8: Frontend and full system testing.

Success Criteria
Timing Success: Orchestrator consistently runs algorithms 2-3 seconds after the top of each minute during market hours.

Trades execute correctly

P&L calculations match expected values (current value - initial allocation)

Available cash for new algorithms = Alpaca cash - sum of allocations

WebSockets open/close intelligently based on algorithm needs

WebSockets automatically restore after system restart

Multiple algorithms can share same ticker WebSocket

Algorithms fetch their own data with auto-download if missing

Database has correct market hours (390 bars per day)

Survives Raspberry Pi restart

Runs 30 days without intervention

Dashboard updates every 30 seconds during market hours

Frontend polling adjusts based on market status flag