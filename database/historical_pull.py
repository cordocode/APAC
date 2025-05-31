import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pytz
from db_manager import insert_historical_data, check_data_exists

# Load environment variables
load_dotenv()

class HistoricalFetcher:
    def __init__(self):
        # Initialize Alpaca client
        self.client = StockHistoricalDataClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET')
        )
        self.eastern = pytz.timezone('US/Eastern')
        self.utc = pytz.UTC

    def fetch_and_store(self, ticker, start_date, end_date):
        """
        Main function to fetch historical data and store in database.
        
        Args:
            ticker: 'NVDA'
            start_date: '2024-01-02' (date string)
            end_date: '2024-01-03' (date string)
        
        Returns:
            dict with status and details
        """
        # Convert date strings to UTC timestamps for database check
        start_utc = self._convert_to_utc_timestamp(start_date, "09:30:00")
        end_utc = self._convert_to_utc_timestamp(end_date, "16:00:00")
        
        # Check what data we're missing
        missing = check_data_exists(ticker, start_utc, end_utc)
        
        if not missing:
            print(f"All data exists for {ticker} from {start_date} to {end_date}")
            return {"status": "already_exists", "rows_updated": 0}
        
        print(f"Missing {len(missing)} data points for {ticker}")
        
        # Fetch from Alpaca
        try:
            # FIXED: Create datetime objects with explicit times to ensure minute bars
            eastern = pytz.timezone('US/Eastern')
            
            # Parse dates and add market hours
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Set to market open/close times
            start_dt = eastern.localize(start_dt.replace(hour=9, minute=30))
            end_dt = eastern.localize(end_dt.replace(hour=16, minute=0))
            
            # Create request with timezone-aware datetimes
            request_params = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=TimeFrame.Minute,
                start=start_dt,
                end=end_dt,
                feed='iex'  # Explicitly use IEX feed for free tier
            )
            
            # Get the bars
            bars = self.client.get_stock_bars(request_params)
            
            # Convert to our format
            data_array = []
            
            # Check if we got any bars back
            try:
                ticker_bars = list(bars[ticker])
                if ticker_bars:
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
                    rows_updated = insert_historical_data(ticker, data_array)
                    
                    return {
                        "status": "fetched",
                        "rows_updated": rows_updated,
                        "data_points": len(data_array)
                    }
                else:
                    print(f"No data returned for {ticker} from {start_date} to {end_date}")
                    return {
                        "status": "no_data", 
                        "rows_updated": 0,
                        "data_points": 0
                    }
            except (KeyError, IndexError):
                print(f"No data returned for {ticker} from {start_date} to {end_date}")
                return {
                    "status": "no_data", 
                    "rows_updated": 0,
                    "data_points": 0
                }
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            return {"status": "error", "error": str(e)}

    def _convert_to_utc_timestamp(self, date_str, time_str):
        """Convert date and time to UTC timestamp string."""
        # Combine date and time
        dt_str = f"{date_str} {time_str}"
        # Parse as Eastern time
        eastern_dt = self.eastern.localize(
            datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        )
        # Convert to UTC
        utc_dt = eastern_dt.astimezone(self.utc)
        # Return formatted string
        return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')


# Test function
if __name__ == "__main__":
    fetcher = HistoricalFetcher()
    
    # Test with a recent date
    result = fetcher.fetch_and_store("NVDA", "2024-01-03", "2024-01-03")
    print(f"Result: {result}")