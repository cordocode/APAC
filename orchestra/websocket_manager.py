#!/usr/bin/env python3
"""
################################################################################
# FILE: websocket_manager.py
# PURPOSE: Manages real-time data subscriptions based on running algorithms
# CREATED: 2025-01-10
# MODIFIED: 2025-01-10
################################################################################
"""

import sys
import threading
import time
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our modules
from database.realtime_pull import RealtimeStreamer
from system_databse.system_db_manager import get_all_algorithms


################################################################################
# WEBSOCKET MANAGER CLASS
################################################################################

class WebSocketManager:
    """
    Manages WebSocket subscriptions for real-time market data.
    Uses reference counting to track which tickers need active subscriptions.
    """
    
    def __init__(self):
        """Initialize the WebSocket manager"""
        self.streamer = RealtimeStreamer()
        self.ticker_counts: Dict[str, int] = defaultdict(int)
        self.stream_thread = None
        self.running = False
        self._lock = threading.Lock()  # Thread safety for ticker counts
        
        print(f"[{datetime.now().isoformat()}] WebSocket Manager initialized")
    
    def initialize_from_db(self):
        """
        On startup, subscribe to all tickers from running algorithms.
        This ensures we don't miss data for algorithms that were already running.
        """
        print(f"[{datetime.now().isoformat()}] Initializing subscriptions")
        
        # Get all running algorithms
        running_algorithms = get_all_algorithms(status='running')
        
        if not running_algorithms:
            print(f"[{datetime.now().isoformat()}] No running algorithms")
            return
        
        # Count tickers
        initial_tickers = set()
        for algo in running_algorithms:
            ticker = algo['ticker']
            initial_tickers.add(ticker)
            with self._lock:
                self.ticker_counts[ticker] += 1
        
        # Subscribe to all unique tickers at once
        if initial_tickers:
            print(f"[{datetime.now().isoformat()}] Found algorithms")
            self.streamer.subscribe_multiple(list(initial_tickers))
            
            # Show the reference counts
            with self._lock:
                for ticker, count in self.ticker_counts.items():
                    if count > 0:
                        print(f"[{datetime.now().isoformat()}] Ticker reference count")
    
    def add_algorithm(self, ticker: str):
        """
        Called when a new algorithm starts.
        Increments reference count and subscribes if this is the first algorithm using this ticker.
        
        Args:
            ticker: Stock symbol the algorithm is trading
        """
        with self._lock:
            old_count = self.ticker_counts[ticker]
            self.ticker_counts[ticker] += 1
            new_count = self.ticker_counts[ticker]
        
        # If this is the first algorithm using this ticker, subscribe
        if old_count == 0 and new_count == 1:
            print(f"[{datetime.now().isoformat()}] First algorithm subscribing")
            self.streamer.subscribe(ticker)
        else:
            print(f"[{datetime.now().isoformat()}] Reference count increased")
    
    def remove_algorithm(self, ticker: str):
        """
        Called when an algorithm stops.
        Decrements reference count and unsubscribes if no algorithms are using this ticker.
        
        Args:
            ticker: Stock symbol the algorithm was trading
        """
        with self._lock:
            if ticker not in self.ticker_counts or self.ticker_counts[ticker] == 0:
                print(f"[{datetime.now().isoformat()}] Invalid removal attempt")
                return
            
            old_count = self.ticker_counts[ticker]
            self.ticker_counts[ticker] -= 1
            new_count = self.ticker_counts[ticker]
        
        # If no algorithms are using this ticker anymore, unsubscribe
        if new_count == 0:
            print(f"[{datetime.now().isoformat()}] Last algorithm unsubscribing")
            self.streamer.unsubscribe(ticker)
            # Clean up the entry
            with self._lock:
                del self.ticker_counts[ticker]
        else:
            print(f"[{datetime.now().isoformat()}] Reference count decreased")
    
    def start(self):
        """
        Start the WebSocket stream in a separate thread.
        This allows the orchestrator to continue running while receiving real-time data.
        """
        if self.running:
            print(f"[{datetime.now().isoformat()}] Stream already running")
            return
        
        print(f"[{datetime.now().isoformat()}] Starting stream thread")
        
        self.running = True
        self.stream_thread = threading.Thread(target=self._run_stream, name="WebSocketStream")
        self.stream_thread.daemon = True  # Dies when main program exits
        self.stream_thread.start()
        
        # Give it a moment to start
        time.sleep(1)
        print(f"[{datetime.now().isoformat()}] Stream thread started")
    
    def _run_stream(self):
        """Internal method that runs the stream (called in thread)"""
        try:
            self.streamer.run()
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Stream error occurred")
            self.running = False
    
    def stop(self):
        """
        Gracefully stop the WebSocket stream.
        Called when orchestrator is shutting down.
        """
        if not self.running:
            print(f"[{datetime.now().isoformat()}] Stream not running")
            return
        
        print(f"[{datetime.now().isoformat()}] Stopping stream")
        
        self.running = False
        self.streamer.stop()
        
        # Wait for thread to finish (with timeout)
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                print(f"[{datetime.now().isoformat()}] Thread stop timeout")
            else:
                print(f"[{datetime.now().isoformat()}] Stream stopped cleanly")
    
    def get_status(self) -> Dict:
        """
        Get current status of subscriptions and reference counts.
        
        Returns:
            Dict with status information
        """
        with self._lock:
            active_tickers = {k: v for k, v in self.ticker_counts.items() if v > 0}
        
        stream_status = self.streamer.get_stream_status()
        
        return {
            "running": self.running,
            "thread_alive": self.stream_thread.is_alive() if self.stream_thread else False,
            "reference_counts": active_tickers,
            "total_subscriptions": len(active_tickers),
            "stream_subscriptions": stream_status['subscription_count'],
            "subscribed_symbols": stream_status['subscribed_symbols']
        }
    
    def print_status(self):
        """Print detailed status information"""
        status = self.get_status()
        
        print(f"[{datetime.now().isoformat()}] WebSocket status report")
        print(f"[{datetime.now().isoformat()}] Manager running")
        print(f"[{datetime.now().isoformat()}] Thread active")
        print(f"[{datetime.now().isoformat()}] Total subscriptions")
        
        if status['reference_counts']:
            print(f"[{datetime.now().isoformat()}] Reference counts")
            for ticker, count in sorted(status['reference_counts'].items()):
                print(f"[{datetime.now().isoformat()}] Ticker count details")
        
        if status['subscribed_symbols']:
            print(f"[{datetime.now().isoformat()}] Active subscriptions")