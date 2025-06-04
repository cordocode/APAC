# AutoTrader Time & Timezone Critical Points

## Overview
This document captures every critical time-related consideration for the AutoTrader system. The golden rule: **UTC everywhere except** checking market hours (ET) and display (user local).

## Component-Specific Time Requirements

### 1. Orchestrator (orchestrator.py)
- **Market hours check**: Must check Eastern Time, not Mountain Time
- **Sleep timing**: 60 seconds during market, 60 minutes after hours
- **Transaction timestamps**: Must match UTC format when recording to system.db
- **"Current time" for algorithms**: Must pass UTC to algorithm's `get_data_requirements()`

### 2. System Database (system.db)
- **created_at**: Must be UTC with 'Z' suffix
- **stopped_at**: Must be UTC with 'Z' suffix  
- **Transaction timestamps**: Must be UTC with 'Z' suffix
- **All timestamps**: Must match stocks.db format exactly: `2024-01-02T14:30:00Z`

### 3. Frontend (dashboard.js)
- **Polling intervals**: 30 seconds market hours, 60 minutes off hours
- **Market hours detection**: Backend must tell frontend, don't let JS guess
- **"Last Updated" display**: Convert UTC to user's local time for display only
- **Time display format**: "2:34 PM" - must handle browser timezone

### 4. API Server (api_server.py)
- **Current time calculations**: When calculating "last update", use UTC internally
- **Market status endpoint**: Must check ET for market hours, not server timezone

### 5. Algorithm Data Requirements
- **get_data_requirements()**: Must accept and return UTC timestamps
- **200-minute lookback**: Calculate in UTC to match database rows

## Critical Edge Cases

### Market Hours Boundaries
- **9:30 AM Market Open**: First bar might be 9:31 (no 9:30 bar)
- **4:00 PM Market Close**: Last bar might be 3:59 (no 4:00 bar)

### Timezone Transitions
- **Daylight Saving Time**: March/November - ET changes but UTC doesn't
- **Weekend gaps**: Pre-populated database handles this correctly

## Implementation Gotchas

### The "Now" Problem
Every time code asks "what time is now":
- Python's `datetime.now()` returns server timezone (Mountain)
- Must use `datetime.now(pytz.UTC)` everywhere
- Or force Python to UTC with environment variable

### Frontend Time Sync
Address the "CRITICAL TIMEZONE ISSUE" mentioned in docs:
- Backend provides `/api/system/time` endpoint
- Tells frontend if market is open
- Tells frontend what polling interval to use
- Frontend never decides timing on its own

### Display Name Generation
- **Algorithm naming**: `NVDA_SMA_20240102_143022` uses server time
- Consider: Should this be UTC for consistency?

### Logging
Not mentioned in original docs but important:
- Any logging should use UTC timestamps
- Makes debugging across components easier

## Summary Rules

### Always UTC
- Database storage (stocks.db and system.db)
- API communication between components
- Internal calculations and logic
- Transaction recording
- Log files

### Eastern Time Only For
- Market hours checks (9:30 AM - 4:00 PM ET)
- Nothing else

### Local Time Only For
- Frontend display to user
- Nothing else

## Verification Checklist
- [ ] All database timestamps end with 'Z'
- [ ] All timestamps are 20 characters: `YYYY-MM-DDTHH:MM:SSZ`
- [ ] Orchestrator checks market hours in ET
- [ ] Frontend receives timing instructions from backend
- [ ] Transaction timestamps match stocks.db format
- [ ] Python code forces UTC timezone