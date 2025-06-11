#!/usr/bin/env python3
"""
API Server for AutoTrader - INTEGRATED VERSION
Now runs as a thread within the Orchestrator for direct WebSocket Manager access
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path
from datetime import datetime
import importlib.util
import traceback
import threading

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import our modules
from system_databse.system_db_manager import (
    get_pin, create_algorithm, stop_algorithm, 
    get_algorithm, get_all_algorithms, get_transactions
)
from system_databse.card_calculations import get_algorithm_with_calculations
from orchestra.alpaca_wrapper import AlpacaWrapper
from database.calendar_manager import MarketCalendar
from database.db_manager import get_latest_price

# =============================================================================
# GLOBAL VARIABLES - SET BY ORCHESTRATOR
# =============================================================================

# These will be set when run_api_server() is called
ws_manager = None  # WebSocket Manager instance from orchestrator
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize components
alpaca = AlpacaWrapper()
calendar = MarketCalendar()

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.route('/api/validate-pin', methods=['POST'])
def validate_pin():
    """Validate PIN for secure actions"""
    try:
        data = request.json
        submitted_pin = data.get('pin', '')
        
        # Get correct PIN from database
        correct_pin = get_pin()
        
        if submitted_pin == correct_pin:
            return jsonify({'valid': True}), 200
        else:
            return jsonify({'valid': False}), 200
            
    except Exception as e:
        print(f"❌ Error validating PIN: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# ALGORITHM MANAGEMENT ENDPOINTS - NOW WITH WEBSOCKET INTEGRATION
# =============================================================================

@app.route('/api/algorithms', methods=['GET'])
def get_algorithms():
    """Get all running algorithms with calculated metrics"""
    try:
        # Get running algorithms
        algorithms = get_all_algorithms(status='running')
        
        # Calculate card data for each algorithm
        algorithm_cards = []
        total_value = 0
        
        for algo in algorithms:
            try:
                # Get current price for the ticker
                from database.db_manager import get_latest_price
                latest_price_data = get_latest_price(algo['ticker'])
                current_price = 0.0
                if latest_price_data and 'ohlcv' in latest_price_data:
                    current_price = latest_price_data['ohlcv']['c']
                
                # Calculate metrics using card_calculations
                card_data = get_algorithm_with_calculations(algo['id'], current_price)
                
                # get_algorithm_with_calculations returns None for non-running algorithms
                if not card_data:
                    continue
                
                # Add to running total
                if 'current_value' in card_data:
                    total_value += card_data['current_value']
                    
                    # Add last_updated field from most recent transaction
                    transactions = get_transactions(algo['id'])
                    if transactions:
                        card_data['last_updated'] = transactions[0]['timestamp']
                    else:
                        card_data['last_updated'] = card_data['created_at']
                    
                    # Add pnl_percent if not present
                    if 'pnl_percent' not in card_data and 'pnl' in card_data and 'initial_capital' in card_data:
                        card_data['pnl_percent'] = round((card_data['pnl'] / card_data['initial_capital']) * 100, 2)
                    
                    algorithm_cards.append(card_data)
            except Exception as e:
                print(f"❌ Error calculating card for algo {algo['id']}: {e}")
                # Skip this algorithm if calculation fails
                continue
        
        # Get Alpaca account cash
        account_cash = alpaca.get_account_cash()
        
        # Total account value = cash + all algorithm values
        total_account_value = account_cash + total_value
        
        # Check if market is open
        market_open = calendar.is_market_open_now()
        
        return jsonify({
            'algorithms': algorithm_cards,
            'market_open': market_open,
            'total_account_value': total_account_value
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting algorithms: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/algorithms', methods=['POST'])
def create_algorithm_endpoint():
    """Create a new algorithm instance - NOW WITH REAL-TIME DATA"""
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        algo_type = data.get('algorithm_type')
        initial_capital = float(data.get('initial_capital', 0))
        
        # Validate inputs
        if not ticker or not algo_type or initial_capital <= 0:
            return jsonify({'error': 'Invalid input parameters'}), 400
        
        # Validate ticker with Alpaca
        if not alpaca.validate_ticker(ticker):
            return jsonify({'error': f'Invalid or non-tradable ticker: {ticker}'}), 400
        
        # Check if algorithm type exists
        algo_path = Path(__file__).parent.parent / 'algorithm' / f'{algo_type}.py'
        if not algo_path.exists():
            return jsonify({'error': f'Algorithm type not found: {algo_type}'}), 400
        
        # Check available cash
        available_cash = _calculate_available_cash()
        if initial_capital > available_cash:
            return jsonify({
                'error': f'Insufficient cash. Available: ${available_cash:.2f}, Requested: ${initial_capital:.2f}'
            }), 400
        
        # Create algorithm in database
        algo_id = create_algorithm(ticker, algo_type, initial_capital)
        
        # =====================================================================
        # WEBSOCKET INTEGRATION - Subscribe to real-time data immediately
        # =====================================================================
        if ws_manager:
            print(f"🔌 API: Adding {ticker} to WebSocket subscriptions")
            ws_manager.add_algorithm(ticker)
        else:
            print("⚠️  WebSocket Manager not available - running in standalone mode")
        
        # Get the created algorithm
        algorithm = get_algorithm(algo_id)
        
        return jsonify({
            'success': True,
            'algorithm': algorithm
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating algorithm: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/algorithms/<int:algo_id>', methods=['DELETE'])
def stop_algorithm_endpoint(algo_id):
    """Stop a running algorithm - NOW UNSUBSCRIBES FROM REAL-TIME DATA"""
    try:
        # Get algorithm info BEFORE stopping (need ticker for unsubscribe)
        algo_data = get_algorithm(algo_id)
        if not algo_data:
            return jsonify({'error': 'Algorithm not found'}), 404
        
        ticker = algo_data['ticker']
        
        # Stop the algorithm
        success = stop_algorithm(algo_id)
        
        if success:
            # =====================================================================
            # WEBSOCKET INTEGRATION - Unsubscribe from real-time data
            # =====================================================================
            if ws_manager:
                print(f"🔌 API: Removing {ticker} from WebSocket subscriptions")
                ws_manager.remove_algorithm(ticker)
            else:
                print("⚠️  WebSocket Manager not available - running in standalone mode")
            
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Algorithm not found or already stopped'}), 404
            
    except Exception as e:
        print(f"❌ Error stopping algorithm: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# SYSTEM STATUS ENDPOINTS
# =============================================================================

@app.route('/api/available-algorithms', methods=['GET'])
def get_available_algorithms():
    """Scan algorithm directory and return available algorithm types"""
    try:
        # Path to algorithm directory (singular!)
        algo_dir = Path(__file__).parent.parent / 'algorithm'
        
        if not algo_dir.exists():
            return jsonify({'algorithms': []}), 200
        
        # Find all .py files that aren't __pycache__ or test files
        available = []
        for file in algo_dir.glob('*.py'):
            if file.stem.startswith('_') or file.stem.startswith('test'):
                continue
                
            # Try to load the module and check if it has Algorithm class
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'Algorithm'):
                    available.append({
                        'type': file.stem,
                        'name': file.stem.replace('_', ' ').title()
                    })
            except Exception as e:
                print(f"⚠️  Couldn't load algorithm {file.stem}: {e}")
                continue
        
        return jsonify({'algorithms': available}), 200
        
    except Exception as e:
        print(f"❌ Error scanning algorithms: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/account/cash', methods=['GET'])
def get_account_cash():
    """Get available cash for new allocations"""
    try:
        available_cash = _calculate_available_cash()
        total_cash = alpaca.get_account_cash()
        
        return jsonify({
            'available_cash': available_cash,
            'total_cash': total_cash
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting account cash: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate-ticker', methods=['GET'])
def validate_ticker_endpoint():
    """Validate if a ticker is tradable"""
    try:
        symbol = request.args.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'valid': False, 'error': 'No symbol provided'}), 400
        
        # Check with Alpaca
        is_valid = alpaca.validate_ticker(symbol)
        
        return jsonify({'valid': is_valid}), 200
        
    except Exception as e:
        print(f"❌ Error validating ticker: {e}")
        return jsonify({'valid': False, 'error': str(e)}), 500

@app.route('/api/market-status', methods=['GET'])
def get_market_status():
    """Get current market open/closed status"""
    try:
        is_open = calendar.is_market_open_now()
        
        # Get next market open/close time
        now = datetime.now()
        schedule = calendar.get_market_schedule(
            now.strftime('%Y-%m-%d'),
            now.strftime('%Y-%m-%d')
        )
        
        next_event = None
        if schedule:
            today_schedule = schedule[0]
            if is_open:
                next_event = {
                    'type': 'close',
                    'time': today_schedule['close']
                }
            else:
                next_event = {
                    'type': 'open',
                    'time': today_schedule['open']
                }
        
        return jsonify({
            'market_open': is_open,
            'next_event': next_event
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting market status: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _calculate_available_cash():
    """Calculate cash available for new algorithm allocations"""
    # Get total cash in Alpaca account
    total_cash = alpaca.get_account_cash()
    
    # Get all running algorithms
    running_algos = get_all_algorithms(status='running')
    
    # Sum up allocated capital
    allocated = sum(algo['initial_capital'] for algo in running_algos)
    
    # Available = Total - Allocated
    return total_cash - allocated

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# =============================================================================
# ORCHESTRATOR INTEGRATION - NEW ENTRY POINT
# =============================================================================

def run_api_server(websocket_manager, port=5001):
    """
    Run the API server with access to the WebSocket Manager
    Called by the Orchestrator in a separate thread
    
    Args:
        websocket_manager: WebSocketManager instance from orchestrator
        port: Port to run the API server on (default 5001)
    """
    global ws_manager
    ws_manager = websocket_manager
    
    print("\n" + "="*60)
    print("🚀 Starting AutoTrader API Server (Integrated Mode)")
    print("="*60)
    print(f"📡 API endpoints available at http://localhost:{port}/api/")
    print("🔐 Make sure system PIN is set in system.db")
    print("📊 Market status:", "OPEN" if calendar.is_market_open_now() else "CLOSED")
    print("🔌 WebSocket Manager:", "Connected" if ws_manager else "Not Available")
    print("="*60 + "\n")
    
    # Run Flask app
    # Use threaded=False since we're already in a thread
    app.run(host='0.0.0.0', port=port, debug=False, threaded=False)

# =============================================================================
# STANDALONE MODE (for testing)
# =============================================================================

if __name__ == '__main__':
    print("\n⚠️  Running API Server in STANDALONE mode")
    print("⚠️  WebSocket integration will NOT be available")
    print("⚠️  For production, run via orchestrator.py\n")
    
    run_api_server(None, port=5001)