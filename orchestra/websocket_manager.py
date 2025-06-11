#!/usr/bin/env python3
"""
WebSocket Manager
Manages real-time data subscriptions based on running algorithms
Uses reference counting to efficiently share ticker streams
"""

import sys
import threading
import time
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our modules
from database.realtime_pull import RealtimeStreamer
from system_databse.system_db_manager import get_all_algorithms

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
        
        print("🔌 WebSocket Manager initialized")
    
    def initialize_from_db(self):
        """
        On startup, subscribe to all tickers from running algorithms.
        This ensures we don't miss data for algorithms that were already running.
        """
        print("📍 Initializing WebSocket subscriptions from database...")
        
        # Get all running algorithms
        running_algorithms = get_all_algorithms(status='running')
        
        if not running_algorithms:
            print("📭 No running algorithms found - no subscriptions needed")
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
            print(f"📊 Found {len(running_algorithms)} running algorithms using {len(initial_tickers)} unique tickers")
            self.streamer.subscribe_multiple(list(initial_tickers))
            
            # Show the reference counts
            with self._lock:
                for ticker, count in self.ticker_counts.items():
                    if count > 0:
                        print(f"   {ticker}: {count} algorithm(s)")
    
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
            print(f"🆕 First algorithm using {ticker} - subscribing to real-time data")
            self.streamer.subscribe(ticker)
        else:
            print(f"📈 {ticker} reference count increased: {old_count} → {new_count}")
    
    def remove_algorithm(self, ticker: str):
        """
        Called when an algorithm stops.
        Decrements reference count and unsubscribes if no algorithms are using this ticker.
        
        Args:
            ticker: Stock symbol the algorithm was trading
        """
        with self._lock:
            if ticker not in self.ticker_counts or self.ticker_counts[ticker] == 0:
                print(f"⚠️  Warning: Trying to remove {ticker} but count is already 0")
                return
            
            old_count = self.ticker_counts[ticker]
            self.ticker_counts[ticker] -= 1
            new_count = self.ticker_counts[ticker]
        
        # If no algorithms are using this ticker anymore, unsubscribe
        if new_count == 0:
            print(f"🔴 No algorithms using {ticker} - unsubscribing from real-time data")
            self.streamer.unsubscribe(ticker)
            # Clean up the entry
            with self._lock:
                del self.ticker_counts[ticker]
        else:
            print(f"📉 {ticker} reference count decreased: {old_count} → {new_count}")
    
    def start(self):
        """
        Start the WebSocket stream in a separate thread.
        This allows the orchestrator to continue running while receiving real-time data.
        """
        if self.running:
            print("⚠️  WebSocket stream already running")
            return
        
        print("🚀 Starting WebSocket stream in background thread...")
        
        self.running = True
        self.stream_thread = threading.Thread(target=self._run_stream, name="WebSocketStream")
        self.stream_thread.daemon = True  # Dies when main program exits
        self.stream_thread.start()
        
        # Give it a moment to start
        time.sleep(1)
        print("✅ WebSocket stream thread started")
    
    def _run_stream(self):
        """Internal method that runs the stream (called in thread)"""
        try:
            self.streamer.run()
        except Exception as e:
            print(f"❌ WebSocket stream error: {e}")
            self.running = False
    
    def stop(self):
        """
        Gracefully stop the WebSocket stream.
        Called when orchestrator is shutting down.
        """
        if not self.running:
            print("⚠️  WebSocket stream not running")
            return
        
        print("🛑 Stopping WebSocket stream...")
        
        self.running = False
        self.streamer.stop()
        
        # Wait for thread to finish (with timeout)
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                print("⚠️  WebSocket thread didn't stop cleanly")
            else:
                print("✅ WebSocket stream stopped cleanly")
    
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
        
        print("\n" + "="*60)
        print("📡 WEBSOCKET MANAGER STATUS")
        print("="*60)
        print(f"🔌 Manager Running: {status['running']}")
        print(f"🧵 Thread Active: {status['thread_alive']}")
        print(f"📊 Total Subscriptions: {status['total_subscriptions']}")
        
        if status['reference_counts']:
            print("\n📈 Reference Counts:")
            for ticker, count in sorted(status['reference_counts'].items()):
                print(f"   {ticker}: {count} algorithm(s)")
        
        if status['subscribed_symbols']:
            print(f"\n📡 Active WebSocket Subscriptions: {', '.join(sorted(status['subscribed_symbols']))}")
        
        print("="*60 + "\n")

# Example usage and testing
if __name__ == "__main__":
    """Test the WebSocket manager independently"""
    print("🧪 Testing WebSocket Manager...\n")
    
    manager = WebSocketManager()
    
    # Initialize from database
    manager.initialize_from_db()
    
    # Start the stream
    manager.start()
    
    # Print initial status
    manager.print_status()
    
    # Simulate adding an algorithm
    print("\n🧪 Simulating algorithm lifecycle...")
    time.sleep(2)
    
    print("\n📍 Adding TSLA algorithm...")
    manager.add_algorithm("TSLA")
    time.sleep(1)
    
    print("\n📍 Adding another TSLA algorithm...")
    manager.add_algorithm("TSLA")
    time.sleep(1)
    
    print("\n📍 Removing one TSLA algorithm...")
    manager.remove_algorithm("TSLA")
    time.sleep(1)
    
    print("\n📍 Removing last TSLA algorithm...")
    manager.remove_algorithm("TSLA")
    time.sleep(1)
    
    # Final status
    manager.print_status()
    
    # Let it run for a bit
    print("\n⏱️  Letting stream run for 30 seconds...")
    time.sleep(30)
    
    # Clean shutdown
    print("\n🛑 Shutting down...")
    manager.stop()
    
    print("\n✅ Test complete!")