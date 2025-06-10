#!/usr/bin/env python3
"""
Market Calendar Manager
Handles all market hours, holidays, and calendar logic using Alpaca Calendar API
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from typing import List, Dict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from parent directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from alpaca.trading.client import TradingClient

#==============================================================================
# MARKET CALENDAR CLASS
#==============================================================================

class MarketCalendar:
    """
    Handles all market hours and calendar operations using Alpaca Calendar API.
    Eliminates all hardcoded holiday logic and market hour calculations.
    """
    
    def __init__(self):
        """Initialize Alpaca client for calendar data"""
        api_key = os.getenv('ALPACA_API_KEY')
        secret = os.getenv('ALPACA_SECRET')
        
        if not api_key or not secret:
            raise ValueError("Missing ALPACA_API_KEY or ALPACA_SECRET in environment")
        
        # Use paper=True for calendar API (works for both paper and live)
        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret,
            paper=True  # Calendar API works the same for both
        )
        
        self.calendar_cache = {}
        self.eastern = pytz.timezone('US/Eastern')
        self.utc = pytz.UTC
        
        print("✅ Market Calendar initialized with Alpaca API")

#==============================================================================
# CALENDAR DATA FETCHING
#==============================================================================

    def get_market_schedule(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get market schedule from Alpaca Calendar API with caching
        
        Args:
            start_date: 'YYYY-MM-DD' format
            end_date: 'YYYY-MM-DD' format
            
        Returns:
            List of market days with open/close times
        """
        cache_key = f"{start_date}_{end_date}"
        
        if cache_key not in self.calendar_cache:
            try:
                # Convert string dates to datetime objects
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # Get calendar from Alpaca
                calendar_response = self.client.get_calendar(start=start_dt, end=end_dt)
                
                # Convert to our format
                calendar_data = []
                for day in calendar_response:
                    calendar_data.append({
                        'date': day.date.strftime('%Y-%m-%d'),
                        'open': day.open.strftime('%H:%M'),
                        'close': day.close.strftime('%H:%M')
                    })
                
                self.calendar_cache[cache_key] = calendar_data
                print(f"📅 Cached calendar data: {len(calendar_data)} trading days from {start_date} to {end_date}")
                
            except Exception as e:
                print(f"❌ Error fetching calendar data: {e}")
                raise
        
        return self.calendar_cache[cache_key]

    def clear_calendar_cache(self):
        """Clear calendar cache (call this daily or when needed)"""
        self.calendar_cache.clear()
        print("🗑️  Calendar cache cleared")

#==============================================================================
# MARKET MINUTE GENERATION
#==============================================================================

    def generate_all_market_minutes(self, start_year: int = 2018, end_year: int = 2028) -> List[str]:
        """
        Generate every valid market minute from start_year to end_year using Alpaca Calendar.
        This is the core function for building the market-hours-only database.
        
        Args:
            start_year: Starting year (default 2018)
            end_year: Ending year (default 2028)
            
        Returns:
            List of UTC timestamp strings in 'YYYY-MM-DDTHH:MM:SSZ' format
        """
        print(f"🔄 Generating all market minutes from {start_year} to {end_year}...")
        
        # Get full calendar for entire range
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        
        market_schedule = self.get_market_schedule(start_date, end_date)
        
        if not market_schedule:
            raise ValueError(f"No market schedule data received for {start_date} to {end_date}")
        
        market_minutes = []
        
        for day_info in market_schedule:
            date_str = day_info['date']       # '2025-06-20'
            open_time = day_info['open']      # '09:30' 
            close_time = day_info['close']    # '16:00' or '13:00' for early close
            
            # Generate every minute for this trading day
            day_minutes = self._generate_minutes_for_trading_day(date_str, open_time, close_time)
            market_minutes.extend(day_minutes)
        
        print(f"✅ Generated {len(market_minutes):,} total market minutes")
        print(f"📅 First minute: {market_minutes[0]}")
        print(f"📅 Last minute: {market_minutes[-1]}")
        print(f"📊 Trading days: {len(market_schedule):,}")
        
        return market_minutes

    def _generate_minutes_for_trading_day(self, date_str: str, open_time: str, close_time: str) -> List[str]:
        """
        Generate all minute timestamps for a single trading day
        
        Args:
            date_str: '2025-06-20'
            open_time: '09:30'
            close_time: '16:00' or '13:00'
            
        Returns:
            List of UTC timestamps for this day
        """
        # Parse the date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Parse open and close times
        open_hour, open_minute = map(int, open_time.split(':'))
        close_hour, close_minute = map(int, close_time.split(':'))
        
        # Create Eastern timezone datetime objects
        market_open_et = self.eastern.localize(
            datetime.combine(date_obj, datetime.min.time().replace(hour=open_hour, minute=open_minute))
        )
        
        # For close time, we want the LAST bar, so if close is 16:00, last bar is 15:59
        # If close is 13:00 (early close), last bar is 12:59
        if close_minute == 0:
            close_minute = 59
            close_hour -= 1
        else:
            close_minute -= 1
            
        market_close_et = self.eastern.localize(
            datetime.combine(date_obj, datetime.min.time().replace(hour=close_hour, minute=close_minute))
        )
        
        # Convert to UTC and generate minute-by-minute
        current_time = market_open_et.astimezone(self.utc)
        market_close_utc = market_close_et.astimezone(self.utc)
        
        day_minutes = []
        while current_time <= market_close_utc:
            day_minutes.append(current_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
            current_time += timedelta(minutes=1)
        
        return day_minutes

#==============================================================================
# MARKET STATUS UTILITIES
#==============================================================================

    def is_market_open_now(self) -> bool:
        """
        Check if market is currently open using Alpaca Clock API
        
        Returns:
            True if market is open right now
        """
        try:
            clock = self.client.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"❌ Error checking market status: {e}")
            return False

    def get_market_status(self) -> Dict:
        """
        Get detailed market status information
        
        Returns:
            Dict with current market status details
        """
        try:
            clock = self.client.get_clock()
            return {
                'is_open': clock.is_open,
                'current_time': clock.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'next_open': clock.next_open.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'next_close': clock.next_close.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
        except Exception as e:
            print(f"❌ Error getting market status: {e}")
            return {
                'is_open': False,
                'current_time': datetime.now(self.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'next_open': None,
                'next_close': None
            }

    def get_next_trading_day(self, from_date: str = None) -> str:
        """
        Get the next trading day after the given date
        
        Args:
            from_date: 'YYYY-MM-DD' format, defaults to today
            
        Returns:
            Next trading day in 'YYYY-MM-DD' format
        """
        if from_date is None:
            from_date = datetime.now(self.eastern).strftime('%Y-%m-%d')
        
        # Get a few weeks of calendar data to find next trading day
        start_date = from_date
        end_date = (datetime.strptime(from_date, '%Y-%m-%d') + timedelta(days=14)).strftime('%Y-%m-%d')
        
        schedule = self.get_market_schedule(start_date, end_date)
        
        for day in schedule:
            if day['date'] > from_date:
                return day['date']
        
        # If we didn't find one, extend the search
        end_date = (datetime.strptime(from_date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
        schedule = self.get_market_schedule(start_date, end_date)
        
        for day in schedule:
            if day['date'] > from_date:
                return day['date']
        
        raise ValueError(f"Could not find next trading day after {from_date}")

#==============================================================================
# TESTING AND VALIDATION
#==============================================================================

if __name__ == "__main__":
    """Test the calendar manager with real scenarios"""
    print("🧪 Testing Market Calendar functionality...")
    
    try:
        calendar = MarketCalendar()
        
        # Test market status
        status = calendar.get_market_status()
        print(f"Market open: {status['is_open']}")
        print(f"Current time: {status['current_time']}")
        
        # Test schedule retrieval
        schedule = calendar.get_market_schedule('2025-06-16', '2025-06-20')
        print(f"Trading days in test week: {len(schedule)}")
        
        # Test next trading day
        next_day = calendar.get_next_trading_day('2025-06-20')
        print(f"Next trading day after Friday: {next_day}")
        
        print("✅ All calendar tests passed!")
        
    except Exception as e:
        print(f"❌ Calendar test failed: {e}")
        raise