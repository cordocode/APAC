"""
################################################################################
# FILE: historical_pull.py
# PURPOSE: Historical data fetcher that pulls minute bars from Alpaca API
################################################################################
"""

import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pytz
from typing import Dict
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# HISTORICAL DATA FETCHER CLASS
################################################################################

class HistoricalFetcher:
    """
    Fetches historical minute bars from Alpaca API and stores in database.
    """
    
    def __init__(self):
        """Initialize Alpaca historical data client"""
        self.client = StockHistoricalDataClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET')
        )
        self.eastern = pytz.timezone('US/Eastern')
        self.utc = pytz.UTC
        
        print(f"[{datetime.now().isoformat()}] Historical fetcher initialized")


################################################################################
# CORE FETCHING FUNCTIONALITY
################################################################################

    def fetch_and_store(self, ticker: str, start_date: str, end_date: str) -> Dict:
        """
        Main function to fetch historical data and store in database.
        
        Args:
            ticker: Stock symbol (e.g., 'NVDA')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format  
        
        Returns:
            Dict with fetch status and details
        """
        print(f"[{datetime.now().isoformat()}] Fetching historical data")
        
        # Fetch from Alpaca API
        try:
            # Create timezone-aware datetime objects for market hours
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Set to market open/close times in Eastern timezone
            start_dt = self.eastern.localize(start_dt.replace(hour=9, minute=30))
            end_dt = self.eastern.localize(end_dt.replace(hour=16, minute=0))
            
            # Create request with timezone-aware datetimes
            request_params = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=TimeFrame.Minute,
                start=start_dt,
                end=end_dt,
                feed=os.getenv('ALPACA_FEED', 'iex')
            )
            
            print(f"[{datetime.now().isoformat()}] Requesting Alpaca data")
            bars = self.client.get_stock_bars(request_params)
            
            # Convert Alpaca response to our format
            data_array = []
            
            try:
                ticker_bars = list(bars[ticker])
                if ticker_bars:
                    print(f"[{datetime.now().isoformat()}] Received data bars")

                    self.stored_count = 0
                    self.orphaned_bars = []
                    for bar in ticker_bars:
                        timestamp = bar.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    for bar in ticker_bars:
                        # Convert Alpaca timestamp to our UTC format
                        timestamp = bar.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
                        
                        data_array.append({
                            "timestamp": timestamp,
                            "ohlcv": {
                                "o": float(bar.open),
                                "h": float(bar.high),
                                "l": float(bar.low),
                                "c": float(bar.close),
                                "v": int(bar.volume)
                            }
                        })
                    
                    # Store in database
                    import sys
                    from pathlib import Path
                    sys.path.append(str(Path(__file__).parent))
                    from db_manager import insert_historical_data
                    rows_updated = insert_historical_data(ticker, data_array)
                    
                    return {
                        "status": "fetched",
                        "rows_updated": rows_updated,
                        "data_points": len(data_array),
                        "date_range": f"{start_date} to {end_date}"
                    }
                else:
                    print(f"[{datetime.now().isoformat()}] No data returned")
                    return {
                        "status": "no_data", 
                        "rows_updated": 0,
                        "data_points": 0,
                        "reason": "No bars returned from Alpaca API"
                    }
                    
            except (KeyError, IndexError) as e:
                print(f"[{datetime.now().isoformat()}] Data retrieval error")
                return {
                    "status": "no_data", 
                    "rows_updated": 0,
                    "data_points": 0,
                    "reason": f"Ticker not found or no data available: {e}"
                }
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Alpaca fetch error")
            return {
                "status": "error", 
                "error": str(e),
                "rows_updated": 0,
                "data_points": 0
            }


################################################################################
# UTILITY FUNCTIONS
################################################################################

    def fetch_multiple_tickers(self, tickers: list, start_date: str, end_date: str) -> Dict:
        """
        Fetch historical data for multiple tickers efficiently.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Dict with results for each ticker
        """
        print(f"[{datetime.now().isoformat()}] Batch fetch started")
        
        results = {}
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{datetime.now().isoformat()}] Processing ticker batch")
            
            try:
                result = self.fetch_and_store(ticker, start_date, end_date)
                results[ticker] = result
                
                # Brief pause to be respectful to API
                import time
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Ticker fetch failed")
                results[ticker] = {
                    "status": "error",
                    "error": str(e),
                    "rows_updated": 0,
                    "data_points": 0
                }
        
        # Summary
        successful = sum(1 for r in results.values() if r['status'] == 'fetched')
        total_rows = sum(r.get('rows_updated', 0) for r in results.values())
        
        print(f"\n[{datetime.now().isoformat()}] Batch fetch complete")
        print(f"[{datetime.now().isoformat()}] Fetch summary calculated")
        print(f"[{datetime.now().isoformat()}] Total rows updated")
        
        return {
            "summary": {
                "total_tickers": len(tickers),
                "successful": successful,
                "failed": len(tickers) - successful,
                "total_rows_updated": total_rows
            },
            "ticker_results": results
        }