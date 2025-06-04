AUTOTRADER: Wall-Mounted Trading Terminal
A Personal Trading System Built for Simplicity and Awesomeness
Project Philosophy
This isn't enterprise software. This is a personal trading terminal that lives on your wall - like a financial command center from a sci-fi movie. Every line of code must earn its place. If it doesn't directly make the system work or look awesome, it doesn't belong here.
Core Principles:

Simplicity First: Maximum 5,000 lines of code total
Single User: No auth systems, no multi-tenancy, no scaling concerns
Wall Display: Always-on Raspberry Pi with terminal aesthetic
It Just Works: Should run for months without intervention
Looks Awesome: Green text, clean cards, real-time updates

System Architecture Overview
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   USER INTERFACE│────▶│  ORCHESTRATION   │────▶│   DATA SUPPLY   │
│   (Frontend)    │◀────│  (API Endpoints) │◀────│  (stocks.db)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │      ▲
                               ▼      │
                        ┌──────────────────┐     ┌─────────────────┐
                        │   ALGORITHMS     │────▶│ API INTEGRATION │
                        │ (Trading Logic)  │◀────│    (Alpaca)     │
                        └──────────────────┘     └─────────────────┘
                               │      ▲
                               ▼      │
                        ┌──────────────────┐
                        │ SYSTEM DATABASE  │
                        │ (Card States)    │
                        └──────────────────┘
Chapter Breakdown
✅ Chapter 1: Data Supply (COMPLETE)
Status: Production-ready
Purpose: Feed minute-by-minute stock data to algorithms
What's Built:

SQLite database with 1.3M pre-populated timestamps (2018-2030)
Historical data fetcher (390 bars/day)
Real-time WebSocket streamer
Auto-expanding ticker columns

✅ Chapter 2: User Interface (COMPLETE)
Status: Fully specified, ready to build
Purpose: Monitor and control algorithms from the wall
What's Defined:

Terminal-aesthetic cards showing P&L
Horizontal scrolling for multiple algorithms
PIN-protected actions
30-second polling during market hours

📝 Chapter 3: System Database
Purpose: Remember what algorithms are running
Scope: Dead simple state storage
sqlCREATE TABLE algorithm_instances (
    id TEXT PRIMARY KEY,  -- UUID
    ticker TEXT,
    algorithm_type TEXT,
    initial_capital REAL,
    current_shares INTEGER,
    cash_balance REAL,
    status TEXT,  -- 'running' or 'stopped'
    created_at TEXT,
    stopped_at TEXT
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    algorithm_id TEXT,
    type TEXT,  -- 'buy' or 'sell'
    shares INTEGER,
    price REAL,
    timestamp TEXT
);
📝 Chapter 4: Algorithms
Purpose: The actual trading logic
Scope: Simple, pluggable strategy files
python# /algorithms/sma_crossover.py
class SMAcrossover:
    def __init__(self, ticker, capital):
        self.ticker = ticker
        self.capital = capital
        self.position = 0
        
    def on_data(self, bars):
        # Calculate 20 and 50 period SMAs
        # Return 'buy', 'sell', or 'hold'
        pass
📝 Chapter 5: Orchestration
Purpose: Connect everything together
Scope: Minimal REST API + Algorithm Runner

API Endpoints (for frontend):

POST /api/algorithms - Create new card
GET /api/algorithms - Get all cards
DELETE /api/algorithms/{id} - Stop algorithm
GET /api/account/cash - Alpaca balance


Algorithm Runner (background process):

Polls each algorithm every minute
Feeds data from stocks.db
Executes trades via Alpaca
Updates system database



📝 Chapter 6: API Integration
Purpose: Actually place trades
Scope: Thin wrapper around Alpaca
pythondef buy_shares(ticker, shares):
    # Place market order
    # Return fill price
    
def sell_shares(ticker, shares):
    # Place market order
    # Return fill price
    
def get_positions():
    # Current holdings
    
def get_buying_power():
    # Available cash
📝 Chapter 7: Miscellaneous
Purpose: Everything else discovered along the way

Error handling patterns
Timezone management
Configuration files
Startup scripts
Installation guide

Build Order (Minimizing Rework)
Phase 1: Foundation (1 week)
Order matters here - each builds on the last

System Database (Chapter 3)

Can't test anything without state storage
Simple schema, maybe 200 lines total


API Integration (Chapter 6)

Need this to validate our approach
Test with paper trading immediately


First Algorithm (Chapter 4)

Just one - SMA Crossover
Proves the pattern works



Phase 2: Integration (1 week)

Orchestration (Chapter 5)

Now we can connect the pieces
API endpoints for frontend
Algorithm runner for backend



Phase 3: Polish (3 days)

Frontend Build (Chapter 2)

Everything else works, now make it pretty
Should be straightforward with working API


Miscellaneous (Chapter 7)

Clean up discoveries from build
Add startup scripts



Success Metrics

It works: Trades execute, cards update, money flows
It's reliable: Runs for 30 days without restart
It looks awesome: Would make visitors say "what is THAT?"