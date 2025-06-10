#!/usr/bin/env python3
"""
Database Initialization Script
Creates the market-hours-only database structure
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

#==============================================================================
# DATABASE INITIALIZATION
#==============================================================================

def create_database():
    """
    Create the market-hours-only database with all valid market minutes from 2018-2028.
    """
    print("🔄 CREATING MARKET-HOURS-ONLY DATABASE")
    print("="*50)
    print("📅 Building database (2018-2028)")
    print("🎯 Every timestamp will be a valid market minute")
    print("="*50)
    
    try:
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        
        # Import and initialize the database
        from db_manager import initialize_database
        
        # Create the database
        print("📅 Generating market calendar timestamps...")
        initialize_database()
        
        # Get database stats
        from db_manager import get_database_stats
        stats = get_database_stats()
        
        print("\n🎉 DATABASE CREATION COMPLETED!")
        print("="*50)
        print(f"📊 Total timestamps: {stats['total_timestamps']:,}")
        print(f"📅 Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        print("✅ Ready for algorithm requests")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ DATABASE CREATION FAILED: {e}")
        raise

#==============================================================================
# TESTING FUNCTIONS
#==============================================================================

def test_database():
    """Test basic database functionality"""
    print("\n🧪 Testing database functionality...")
    
    try:
        from db_manager import get_database_stats, add_ticker_if_missing
        
        # Test 1: Database stats
        stats = get_database_stats()
        print(f"✅ Database has {stats['total_timestamps']:,} timestamps")
        
        # Test 2: Add ticker column
        add_ticker_if_missing('TEST')
        print("✅ Ticker column creation works")
        
        # Test 3: Calendar integration
        from calendar_manager import MarketCalendar
        calendar = MarketCalendar()
        status = calendar.get_market_status()
        print(f"✅ Calendar integration works (market open: {status['is_open']})")
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        raise

def test_historical_fetch():
    """Test historical data fetching"""
    print("\n🧪 Testing historical data fetching...")
    
    try:
        from database.historical_pull import HistoricalFetcher
        
        fetcher = HistoricalFetcher()
        print("✅ Historical fetcher initialized")
        
        # Test with a small fetch (don't actually fetch in this test)
        print("✅ Historical fetcher ready")
        print("ℹ️  Run fetcher.fetch_and_store('AAPL', '2024-06-03', '2024-06-03') to test actual fetching")
        
    except Exception as e:
        print(f"❌ Historical fetch test failed: {e}")
        raise

#==============================================================================
# MAIN EXECUTION
#==============================================================================

if __name__ == "__main__":
    print("🚀 Database Setup Script")
    print("="*30)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "create":
            create_database()
        elif command == "test":
            test_database()
        elif command == "test-fetch":
            test_historical_fetch()
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: create, test, test-fetch")
    else:
        print("Available commands:")
        print("  python database_setup.py create      - Create the database")
        print("  python database_setup.py test        - Test database functionality")
        print("  python database_setup.py test-fetch  - Test historical data fetching")
        print("")
        
        response = input("Create database now? (y/N): ")
        if response.lower().startswith('y'):
            create_database()
        else:
            print("ℹ️  Database creation cancelled")