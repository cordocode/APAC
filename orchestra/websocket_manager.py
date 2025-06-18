#!/usr/bin/env python3
"""
################################################################################
# FILE: websocket_manager.py
# PURPOSE: Manages real-time data subscriptions based on running algorithms
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
        
        print("[OK] WebSocket Manager initialized")
    
    def initialize_from_db(self):
        """
        On startup, subscribe to all tickers from running algorithms.
        This ensures we don't miss data for algorithms that were already running.
        """
        # Get all running algorithms
        running_algorithms = get_all_algorithms(status='running')
        
        if not running_algorithms:
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
            print(f"[INFO] Found {len(running_algorithms)} running algorithms using {len(initial_tickers)} unique tickers")
            self.streamer.subscribe_multiple(list(initial_tickers))
            
            # Show the reference counts
            with self._lock:
                for ticker, count in self.ticker_counts.items():
                    if count > 0:
                        print(f"[INFO] {ticker}: {count} algorithms")
    
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
            print(f"[OK] First algorithm using {ticker} - subscribing to real-time data")
            self.streamer.subscribe(ticker)
        else:
            print(f"[INFO] {ticker} reference count: {old_count} -> {new_count}")
    
    def remove_algorithm(self, ticker: str):
        """
        Called when an algorithm stops.
        Decrements reference count and unsubscribes if no algorithms are using this ticker.
        
        Args:
            ticker: Stock symbol the algorithm was trading
        """
        with self._lock:
            if ticker not in self.ticker_counts or self.ticker_counts[ticker] == 0:
                print(f"[WARN] Cannot remove algorithm for {ticker} - not in active subscriptions")
                return
            
            old_count = self.ticker_counts[ticker]
            self.ticker_counts[ticker] -= 1
            new_count = self.ticker_counts[ticker]
        
        # If no algorithms are using this ticker anymore, unsubscribe
        if new_count == 0:
            print(f"[INFO] Last algorithm stopped using {ticker} - unsubscribing from real-time data")
            self.streamer.unsubscribe(ticker)
            # Clean up the entry
            with self._lock:
                del self.ticker_counts[ticker]
        else:
            print(f"[INFO] {ticker} reference count: {old_count} -> {new_count}")
    
    def start(self):
        """
        Start the WebSocket stream in a separate thread.
        This allows the orchestrator to continue running while receiving real-time data.
        """
        if self.running:
            print("[WARN] WebSocket stream already running - ignoring start request")
            return
        
        self.running = True
        self.stream_thread = threading.Thread(target=self._run_stream, name="WebSocketStream")
        self.stream_thread.daemon = True  # Dies when main program exits
        self.stream_thread.start()
        
        # Give it a moment to start
        time.sleep(1)
        
        # Verify thread actually started
        if self.stream_thread.is_alive():
            print("[OK] WebSocket stream thread started")
        else:
            print("[ERROR] WebSocket stream thread failed to start")
            self.running = False
    
    def _run_stream(self):
        """Internal method that runs the stream (called in thread)"""
        try:
            self.streamer.run()
        except Exception as e:
            print(f"[ERROR] WebSocket stream crashed: {str(e)}")
            self.running = False
    
    def stop(self):
        """
        Gracefully stop the WebSocket stream.
        Called when orchestrator is shutting down.
        """
        if not self.running:
            print("[INFO] WebSocket stream not running - ignoring stop request")
            return
        
        self.running = False
        self.streamer.stop()
        
        # Wait for thread to finish (with timeout)
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                print("[WARN] WebSocket thread failed to stop after 5 seconds")
            else:
                print("[OK] WebSocket stream stopped cleanly")
    
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
        
        print("[INFO] WebSocket Manager Status:")
        print(f"  - Running: {status['running']}")
        print(f"  - Thread alive: {status['thread_alive']}")
        print(f"  - Total subscriptions: {status['total_subscriptions']}")
        
        if status['reference_counts']:
            print(f"  - Active tickers:")
            for ticker, count in sorted(status['reference_counts'].items()):
                print(f"    - {ticker}: {count} algorithms")
        else:
            print("  - No active ticker subscriptions")
        
        # Show any discrepancies
        if status['stream_subscriptions'] != status['total_subscriptions']:
            print(f"[WARN] Subscription count mismatch: Manager has {status['total_subscriptions']}, Stream has {status['stream_subscriptions']}")