Frontend Roadmap for Autotrader Dashboard
Project Philosophy

Simplicity First: Raw HTML/CSS/JavaScript - no frameworks
Localhost Raspberry Pi: Always-on wall display
Minimal Complexity: ~1000 lines of code total
Single Purpose: Monitor and control trading algorithms


Component Specifications
1. Algorithm Card (COMPLETE SPEC)
Visual Layout:
┌─────────────────────────────────┐
│ NVDA                     +$1,245 │  <- Ticker (left), Total P&L (right)
│ SMA Crossover                   │  <- Algorithm type name
│                                 │
│ Current Total Value:    $11,245 │  
│ Original Capital:       $10,000 │  
│ Current Shares:              45 │  
│ Transactions:                23 │  <- Total buy + sell count
│                                 │
│ Last Updated: 2:34 PM          │  
│                                 │
│ [STOP]                         │  <- Single action button
└─────────────────────────────────┘
Key Decisions:

Each card = separate "sub-account" with own capital
P&L = Current Total Value - Original Capital
Current Total Value = (Shares × Price) + Uninvested Cash
All text is white
Border colors:

Green: Profitable (P&L > $0)
Red: Losing (P&L < $0)
White: Break even (P&L = $0)


NO pause functionality - only STOP
Removed: Liquid cash display, individual buy/sell counts

2. STOP Button Behavior (COMPLETE SPEC)
Flow:

User clicks STOP
PIN pad appears
User enters 4-digit PIN
Confirmation modal shows:

"Stopping [TICKER] algorithm will sell all [X] shares"
"This will realize a [profit/loss] of $X,XXX"
[CONFIRM] [CANCEL]


On confirm: Card disappears immediately
Algorithm is terminated forever (but can recreate similar)

Key Decisions:

PIN required for security
No restart capability
Cash returns to Alpaca account (we never touch actual money)

3. Add Algorithm Modal (COMPLETE SPEC)
Trigger:

Empty card slot with "+" symbol in the grid
Always leftmost position

Flow:

Click "+" card
PIN pad appears
After correct PIN, modal shows:

Create New Algorithm
─────────────────────
Ticker: [______]              

Algorithm: [Dropdown ▼]       

Allocation: $[______]         

Available Cash: $12,450       

[CREATE] [CANCEL]
Key Decisions:

Ticker validation via Alpaca API (real ticker check)
Algorithm dropdown dynamically populated from /algorithms/*.py
Only validation: allocation ≤ Alpaca available cash
Allow duplicate ticker+algorithm combinations
Show error if allocation > available cash
Minimum allocation rules TBD based on algorithm requirements

4. Header Design (COMPLETE SPEC)
Layout:
●●○●○                                    $52,450
Key Decisions:

Left: Position indicator dots

One dot per algorithm (in creation order)
Green = has shares, Red = no shares (liquid)
Small, not clickable
Aligns with cards below


Right: Total account value (sum of all cards)
NO connection status indicator (avoid complexity)
Clean, minimal display

5. Page Layout (COMPLETE SPEC)
Horizontal Scrolling Design:

Cards in single horizontal row
3 cards visible at once
"+" card always leftmost (position 0)
New algorithms appear at position 1, pushing others right
Scroll left/right to see additional cards
Header dots align with cards below

Visual Example:
●●○●○                          $52,450
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[+][NVDA][AAPL][TSLA]→→→
Key Decisions:

Expecting max 5-6 algorithms (no need for complex layouts)
Cards are large for wall display readability
Creation order matches header dots

6. Screen Update Strategy (COMPLETE SPEC)
Polling Schedule:

Market hours (Mon-Fri 9:30 AM - 4:00 PM ET): Every 30 seconds
Off hours: Every 60 minutes
Simple time-based logic (no complex holiday handling)

Implementation:

Frontend polls /api/algorithms endpoint
Updates all cards with fresh data
No WebSockets needed (keep it simple)

CRITICAL TIMEZONE ISSUE:

Backend uses ET for market hours
Frontend JavaScript uses browser local time
Must ensure timezone alignment or polling schedule breaks
Consider: All times in UTC? Or explicit ET conversion?

7. PIN Pad Interface (COMPLETE SPEC)
Design:
┌─────────────────┐
│   Enter PIN   X │
├─────────────────┤
│  [1] [2] [3]   │
│  [4] [5] [6]   │
│  [7] [8] [9]   │
│      [0]       │
│                │
│   ● ● ○ ○      │  
└─────────────────┘
Key Decisions:

Overlay modal (darkened background)
Shows dots as typing
X button cancels action
"Incorrect PIN" message on failure
Used for both ADD and STOP actions


Still To Be Determined
1. Error Handling Strategy

How to display API errors?
Connection failure handling?
Invalid data handling?
Logging strategy (frontend vs backend)?

2. Backend API Endpoints
Need to define exact endpoints:

GET /api/algorithms - Get all algorithm states
POST /api/algorithms - Create new algorithm
DELETE /api/algorithms/{id} - Stop algorithm
GET /api/validate-ticker?symbol=X - Check valid ticker
GET /api/available-algorithms - List algorithm types
GET /api/account/cash - Get Alpaca available cash

3. Algorithm Identification

How does frontend identify each algorithm uniquely?
UUID? Incrementing ID? Ticker+Algorithm combo?

4. Initial Load Behavior

What shows when no algorithms exist?
Loading states during initial data fetch?

5. Timezone Strategy

Convert everything to UTC?
Use ET everywhere?
How to handle daylight savings?


Implementation Order
Phase 1: Static Foundation

Create HTML structure with mock data
Style cards with CSS (terminal aesthetic)
Implement horizontal scrolling layout
Add header with static dots

Phase 2: Interactivity

Build PIN pad component
Add STOP button with confirmation flow
Create Add Algorithm modal
Implement form validations

Phase 3: Backend Integration

Define API endpoints (see TBD section)
Implement polling mechanism
Connect real data to display
Add timezone handling

Phase 4: Polish

Error handling
Loading states
Smooth transitions
Final testing on Raspberry Pi


File Structure
/frontend/
  dashboard.html    # Everything could go here
  styles.css       # Or inline it
  dashboard.js     # Or inline it  
  config.js        # API endpoints, polling intervals

Success Criteria

Runs for 30 days without restart
Updates every 30 seconds during market hours
All actions complete in <1 second
Works smoothly on Raspberry Pi 3