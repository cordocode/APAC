#!/usr/bin/env python3
"""
################################################################################
# FILE: orchestrator.py
# PURPOSE: Core execution engine for AutoTrader with integrated API server
################################################################################
"""

import sys
import time
import importlib
import traceback
import threading
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our modules
from system_databse.system_db_manager import (
    get_all_algorithms, get_algorithm, 
    record_buy, record_sell, stop_algorithm
)
from orchestra.alpaca_wrapper import AlpacaWrapper
from orchestra.websocket_manager import WebSocketManager
from database.calendar_manager import MarketCalendar


################################################################################
# ORCHESTRATOR CLASS
################################################################################

class Orchestrator:
    """Main orchestrator that coordinates algorithm execution and trading"""
    
    def __init__(self):
        self.calendar = MarketCalendar()
        self.alpaca = AlpacaWrapper()
        self.ws_manager = WebSocketManager()  # Initialize WebSocket Manager
        self.loaded_modules = {}  # Cache for algorithm modules
        self.failed_algorithms = set()  # Track failed algorithm IDs
        self.running = True
        self.last_execution = None
        self.api_thread = None  # Thread for API server
        print("[OK] Orchestrator initialized")
        
    def load_algorithm_module(self, algo_type):
        """
        Dynamically load an algorithm module
        
        Args:
            algo_type: Name of algorithm file (e.g., 'sma_crossover')
            
        Returns:
            Loaded module or None if error
        """
        if algo_type in self.loaded_modules:
            return self.loaded_modules[algo_type]
        
        try:
            module_path = f'algorithm.{algo_type}'
            module = importlib.import_module(module_path)
            
            if not hasattr(module, 'Algorithm'):
                print(f"[ERROR] Algorithm module '{algo_type}' missing required 'Algorithm' class")
                return None
            
            self.loaded_modules[algo_type] = module
            print(f"[OK] Algorithm module '{algo_type}' loaded successfully")
            return module
            
        except Exception as e:
            print(f"[ERROR] Failed loading algorithm module '{algo_type}': {str(e)}")
            return None
    
    def execute_algorithm(self, algo_data):
        """
        Execute a single algorithm and handle its trading decision
        
        Args:
            algo_data: Dictionary with algorithm details from database
            
        Returns:
            True if successful, False if error
        """
        algo_id = algo_data['id']
        
        # Skip if previously failed
        if algo_id in self.failed_algorithms:
            print(f"[WARN] Skipping previously failed algorithm: {algo_data['display_name']} (ID: {algo_id})")
            return False
        
        try:
            # Load algorithm module
            module = self.load_algorithm_module(algo_data['algorithm_type'])
            if not module:
                self.failed_algorithms.add(algo_id)
                return False
            
            # Create algorithm instance
            algo_instance = module.Algorithm(
                ticker=algo_data['ticker'],
                initial_capital=algo_data['initial_capital']
            )
            
            # Get current time
            current_time = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Run algorithm
            action, shares = algo_instance.run(current_time, algo_id)
            
            # Validate response
            if not self._validate_algorithm_response(action, shares):
                print(f"[ERROR] Algorithm {algo_data['display_name']} returned invalid response: action='{action}', shares={shares}")
                return False
            
            # Execute trading decision
            if action == 'buy' and shares > 0:
                self._execute_buy(algo_id, algo_data['ticker'], shares, algo_data['display_name'])
            elif action == 'sell' and shares > 0:
                self._execute_sell(algo_id, algo_data['ticker'], shares, algo_data['display_name'])
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [INFO] {algo_data['display_name']} holding position")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Algorithm {algo_data['display_name']} crashed: {str(e)}")
            traceback.print_exc()
            self.failed_algorithms.add(algo_id)
            return False
    
    def _validate_algorithm_response(self, action, shares):
        """Validate algorithm response format"""
        if action not in ['buy', 'sell', 'hold']:
            return False
        if not isinstance(shares, int) or shares < 0:
            return False
        return True
    
    def _execute_buy(self, algo_id, ticker, shares, display_name):
        """Execute buy order and record transaction"""
        try:
            # Place market buy order
            fill_price = self.alpaca.place_market_buy(ticker, shares)
            
            # Record transaction
            tx_id = record_buy(algo_id, shares, fill_price)
            
            if tx_id:
                print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [OK] Buy executed: {shares} {ticker} @ ${fill_price:.2f} (TX: {tx_id}) for {display_name}")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [ERROR] Buy failed for {ticker}: {str(e)}")
    
    def _execute_sell(self, algo_id, ticker, shares, display_name):
        """Execute sell order and record transaction"""
        try:
            # Place market sell order
            fill_price = self.alpaca.place_market_sell(ticker, shares)
            
            # Record transaction
            tx_id = record_sell(algo_id, shares, fill_price)
            
            if tx_id:
                print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [OK] Sell executed: {shares} {ticker} @ ${fill_price:.2f} (TX: {tx_id}) for {display_name}")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [ERROR] Sell failed for {ticker}: {str(e)}")
    
    def execute_all_algorithms(self):
        """Execute all running algorithms"""
        # Get all running algorithms
        running_algos = get_all_algorithms(status='running')
        
        if not running_algos:
            print("[INFO] No running algorithms found")
            return
        
        print(f"[INFO] Found {len(running_algos)} running algorithms")
        
        # Execute each algorithm
        success_count = 0
        for algo in running_algos:
            if self.execute_algorithm(algo):
                success_count += 1
        
        print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [OK] Algorithm execution complete: {success_count}/{len(running_algos)} succeeded")
        self.last_execution = datetime.now(pytz.UTC)
    

################################################################################
# API SERVER INTEGRATION
################################################################################
    
    def _start_api_server(self):
        """Start the API server in a separate thread"""
        try:
            # Import and run the API server with our WebSocket manager
            from orchestra.api_server import run_api_server
            
            # Run API server in a daemon thread
            self.api_thread = threading.Thread(
                target=run_api_server,
                args=(self.ws_manager,),  # Pass WebSocket manager
                kwargs={'port': 5001},
                name="APIServer",
                daemon=True  # Dies when main program exits
            )
            self.api_thread.start()
            
            # Give it a moment to start
            time.sleep(2)
            print("[OK] API server thread started on port 5001")
            
        except Exception as e:
            print(f"[ERROR] API server failed to start: {str(e)}")
            traceback.print_exc()
    

################################################################################
# MAIN RUN LOOP
################################################################################
    
    def run(self):
        """Main execution loop - runs forever"""
        # START API SERVER FIRST
        self._start_api_server()
        
        # INITIALIZE WEBSOCKET MANAGER
        self.ws_manager.initialize_from_db()
        self.ws_manager.start()
        
        last_market_state = None
        
        try:
            while self.running:
                # Check if market is open
                market_open = self.calendar.is_market_open_now()
                
                # Log market state changes
                if market_open != last_market_state:
                    if market_open:
                        print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [OK] Market opened")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [INFO] Market closed")
                    last_market_state = market_open
                
                if market_open:
                    # Market is open - execute algorithms
                    self.execute_all_algorithms()
                    
                    # Calculate next execution time (next minute + 2 seconds)
                    now = datetime.now(pytz.UTC)
                    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
                    next_execution = next_minute + timedelta(seconds=2)
                    sleep_duration = (next_execution - datetime.now(pytz.UTC)).total_seconds()
                    
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
                else:
                    # Market is closed - sleep until market open
                    self._sleep_until_market_open()
                    
        except KeyboardInterrupt:
            print("[INFO] Orchestrator stopped by user")
        except Exception as e:
            print(f"[ERROR] Orchestrator crashed: {str(e)}")
            traceback.print_exc()
        finally:
            # CLEAN SHUTDOWN
            print("[INFO] Shutting down orchestrator")
            
            # Stop WebSocket stream
            self.ws_manager.stop()
            
            # API server will stop automatically (daemon thread)
            
            print("[OK] Shutdown complete")
    
    def _sleep_until_market_open(self):
        """Sleep until exactly when market opens"""
        current_time = datetime.now(pytz.UTC)
        
        # Try to get next market open time
        next_open = self._get_next_market_open()
        
        if next_open:
            time_until_open = (next_open - current_time).total_seconds()
            
            if time_until_open > 0:
                # Convert to hours and minutes for display
                hours = int(time_until_open // 3600)
                minutes = int((time_until_open % 3600) // 60)
                
                print(f"[INFO] Market opens in {hours}h {minutes}m")
                
                # Sleep until 10 seconds before market open
                sleep_duration = time_until_open - 10
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                
                # Final approach - check every second
                while datetime.now(pytz.UTC) < next_open:
                    time.sleep(1)
                
                print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] [INFO] Market opening soon")
            else:
                # Market should be open but isn't? Check again in 10 seconds
                print("[WARN] Market schedule inconsistency: calculated open time is in the past, rechecking in 10 seconds")
                time.sleep(10)
        else:
            # Couldn't determine next open, check again in 60 seconds
            print("[WARN] Cannot determine next market open time, checking again in 60 seconds")
            time.sleep(60)
    
    def _get_next_market_open(self):
        """Get the next market open time"""
        current_time = datetime.now(pytz.UTC)
        
        # Check next 7 days for market open
        for days_ahead in range(7):
            check_date = (current_time + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            schedule = self.calendar.get_market_schedule(check_date, check_date)
            
            if schedule and len(schedule) > 0:
                try:
                    open_time_str = schedule[0]['open']
                    
                    # Handle different time formats
                    if len(open_time_str) == 5 and ':' in open_time_str:
                        # Just time like "09:30"
                        market_open = datetime.strptime(f"{check_date} {open_time_str}", '%Y-%m-%d %H:%M')
                        market_open = pytz.timezone('America/New_York').localize(market_open)
                        market_open = market_open.astimezone(pytz.UTC)
                    else:
                        # Full timestamp
                        market_open = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
                    
                    # If this open time is in the future, return it
                    if market_open > current_time:
                        return market_open
                        
                except Exception as e:
                    print(f"[ERROR] Error parsing market schedule for {check_date}: {str(e)}")
                    continue
        
        return None


################################################################################
# MAIN ENTRY POINT
################################################################################

def main():
    """Main entry point"""
    orchestrator = Orchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()