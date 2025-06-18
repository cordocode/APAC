#!/usr/bin/env python3
"""
################################################################################
# FILE: card_calculations.py
# PURPOSE: Functions to calculate display values for frontend algorithm cards
################################################################################
"""

from system_databse import system_db_manager
from typing import Optional, Dict, Any


################################################################################
# POSITION CALCULATIONS
################################################################################

def calculate_position(algo_id: int) -> int:
    """Calculate current shares from transaction history"""
    try:
        conn = system_db_manager.get_connection()
        cursor = conn.cursor()
        
        # Sum all buy shares minus all sell shares
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'buy' THEN shares ELSE -shares END) as current_shares
            FROM transactions 
            WHERE algorithm_id = ?
        """, (algo_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        # Handle case where no transactions exist yet
        position = result[0] if result[0] is not None else 0
        return position
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate position for algorithm {algo_id}: {str(e)}")
        if conn:
            conn.close()
        return 0


def calculate_trade_count(algo_id: int) -> int:
    """Calculate total number of transactions"""
    try:
        conn = system_db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM transactions WHERE algorithm_id = ?
        """, (algo_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0]
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate trade count for algorithm {algo_id}: {str(e)}")
        if conn:
            conn.close()
        return 0


################################################################################
# P&L CALCULATIONS
################################################################################

def calculate_invested_amount(algo_id: int) -> float:
    """Calculate how much cash is currently invested (buy_cost - sell_proceeds)"""
    try:
        conn = system_db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'buy' THEN shares * price ELSE -(shares * price) END) as invested
            FROM transactions 
            WHERE algorithm_id = ?
        """, (algo_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        invested = result[0] if result[0] is not None else 0.0
        return invested
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate invested amount for algorithm {algo_id}: {str(e)}")
        if conn:
            conn.close()
        return 0.0


def calculate_current_value(algo_id: int, current_price: float, initial_capital: float) -> float:
    """Calculate current total value of the algorithm's position"""
    try:
        current_shares = calculate_position(algo_id)
        invested_amount = calculate_invested_amount(algo_id)
        
        # Current value = (shares × current_price) + uninvested_cash
        uninvested_cash = initial_capital - invested_amount
        current_value = (current_shares * current_price) + uninvested_cash
        
        # Sanity check - warn if current value seems unreasonable
        if current_value < 0:
            print(f"[WARN] Negative current value calculated for algorithm {algo_id}: ${current_value:.2f}")
        elif current_value > initial_capital * 10:
            print(f"[WARN] Unusually high current value for algorithm {algo_id}: ${current_value:.2f} (10x initial capital)")
        
        return current_value
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate current value for algorithm {algo_id}: {str(e)}")
        return initial_capital  # Return initial capital as fallback


def calculate_pnl(current_value: float, initial_capital: float) -> float:
    """Calculate profit/loss"""
    pnl = current_value - initial_capital
    
    # Log extreme P&L for monitoring
    pnl_percent = (pnl / initial_capital) * 100
    if abs(pnl_percent) > 50:
        if pnl > 0:
            print(f"[INFO] Large profit detected: +${pnl:.2f} ({pnl_percent:.1f}%)")
        else:
            print(f"[WARN] Large loss detected: -${abs(pnl):.2f} ({pnl_percent:.1f}%)")
    
    return pnl


################################################################################
# COMPLETE CARD DATA
################################################################################

def get_algorithm_with_calculations(algo_id: int, current_price: float) -> Optional[Dict[str, Any]]:
    """Get algorithm with all calculated fields for frontend display"""
    
    try:
        # Get basic algorithm info
        conn = system_db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM algorithm_instances WHERE id = ? AND status = 'running'", (algo_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            # Don't log for stopped algorithms - this is expected
            return None
        
        # Convert to dict
        algo_data = dict(result)
        
        # Validate current price
        if current_price <= 0:
            print(f"[ERROR] Invalid current price (${current_price}) for {algo_data['ticker']} - algorithm {algo_id}")
            return None
        
        # Add calculated fields
        current_shares = calculate_position(algo_id)
        trade_count = calculate_trade_count(algo_id)
        current_value = calculate_current_value(algo_id, current_price, algo_data['initial_capital'])
        pnl = calculate_pnl(current_value, algo_data['initial_capital'])
        
        # Add calculations to the data
        algo_data.update({
            'current_shares': current_shares,
            'trade_count': trade_count,
            'current_value': current_value,
            'pnl': pnl,
            'current_price': current_price
        })
        
        # Log successful calculation only if there's meaningful activity
        if trade_count > 0:
            pnl_display = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            print(f"[OK] Card calculated for {algo_data['display_name']}: {current_shares} shares, {trade_count} trades, P&L: {pnl_display}")
        
        return algo_data
        
    except Exception as e:
        print(f"[ERROR] Failed to get algorithm data with calculations for ID {algo_id}: {str(e)}")
        if conn:
            conn.close()
        return None