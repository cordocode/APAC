# Clean Database System - Production Ready

## Overview

Market-hours-only stock price database that eliminates all calendar complexity from algorithm requests. Every timestamp is guaranteed to be a valid market minute.

## 🚀 **Quick Start**

### **1. Create Database**
```bash
python database_setup.py create
```

### **2. Test System**
```python
from db_manager import get_data_for_algorithm

# Get last 50 bars - guaranteed to be valid market minutes
bars = get_data_for_algorithm('NVDA', 'last_n_bars', n=50)

# Get time range - automatically excludes weekends/holidays
bars = get_data_for_algorithm('NVDA', 'time_range', 
                            start='2025-06-16T13:30:00Z', 
                            end='2025-06-20T20:59:00Z')
```

### **3. Real-time Data**
```python
from database.realtime_pull import RealtimeStreamer

streamer = RealtimeStreamer()
streamer.subscribe(['NVDA', 'AAPL', 'TSLA'])
streamer.run()
```

---

## 📁 **Files**

| File | Purpose |
|------|---------|
| `calendar_manager.py` | Alpaca Calendar API integration |
| `db_manager.py` | Clean database operations |
| `historical_pull.py` | Fetch historical data from Alpaca |
| `realtime_pull.py` | WebSocket streaming |
| `database_setup.py` | Database initialization script |

---

## 🎯 **Key Benefits**

✅ **Every timestamp guaranteed to be valid market minute**  
✅ **Zero calendar logic needed in algorithm code**  
✅ **Bulletproof holiday and early-close handling**  
✅ **Simple SQL queries for all data requests**  

---

## 🔧 **Algorithm Requests**

### **Before (Complex)**
```python
# OLD: Required complex calendar logic
def get_last_50_bars_old(ticker):
    # 1. Calculate which timestamps SHOULD exist
    # 2. Handle holidays manually
    # 3. Skip weekends 
    # 4. Handle early closes
    # ~50 lines of complex code
```

### **After (Simple)**
```python
# NEW: Dead simple
def get_last_50_bars_new(ticker):
    return get_data_for_algorithm(ticker, 'last_n_bars', n=50)
```

---

## 🧪 **Testing**

```bash
# Test database functionality
python database_setup.py test

# Test historical data fetching
python database_setup.py test-fetch

# Test calendar integration
python calendar_manager.py

# Test real-time streaming setup
python realtime_pull.py
```

---

## 🛠️ **Environment Setup**

Create `.env` file:
```
ALPACA_API_KEY=your_api_key
ALPACA_SECRET=your_secret_key
ALPACA_PAPER=True
ALPACA_FEED=iex
```

---

## 📊 **Database Structure**

**Market Hours Only Database:**
- 2018-2028 timeframe
- Only valid market minutes (9:30 AM - 3:59 PM ET)
- No weekends, holidays, or after-hours
- Automatic early-close handling

**Time Range Queries:**
- Request: "Jan 1, 2019 through Jan 1, 2020"
- Returns: All market minutes between those dates
- Automatically skips holidays/weekends

---

## ✅ **Success Criteria**

After setup, your system should:

✅ Handle "last 50 bars" requests on Monday after holidays  
✅ Process time ranges correctly (auto-exclude weekends/holidays)  
✅ Require zero calendar logic in algorithm code  
✅ Fetch missing data automatically when needed  
✅ Work with real-time data streams seamlessly  

**The Monday-after-Juneteenth scenario? Completely solved.**