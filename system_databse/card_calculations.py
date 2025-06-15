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
    return result[0] if result[0] is not None else 0


def calculate_trade_count(algo_id: int) -> int:
    """Calculate total number of transactions"""
    conn = system_db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM transactions WHERE algorithm_id = ?
    """, (algo_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0]


################################################################################
# P&L CALCULATIONS
################################################################################

def calculate_invested_amount(algo_id: int) -> float:
    """Calculate how much cash is currently invested (buy_cost - sell_proceeds)"""
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
    
    return result[0] if result[0] is not None else 0.0


def calculate_current_value(algo_id: int, current_price: float, initial_capital: float) -> float:
    """Calculate current total value of the algorithm's position"""
    current_shares = calculate_position(algo_id)
    invested_amount = calculate_invested_amount(algo_id)
    
    # Current value = (shares × current_price) + uninvested_cash
    uninvested_cash = initial_capital - invested_amount
    current_value = (current_shares * current_price) + uninvested_cash
    
    return current_value


def calculate_pnl(current_value: float, initial_capital: float) -> float:
    """Calculate profit/loss"""
    return current_value - initial_capital


################################################################################
# COMPLETE CARD DATA
################################################################################

def get_algorithm_with_calculations(algo_id: int, current_price: float) -> Optional[Dict[str, Any]]:
    """Get algorithm with all calculated fields for frontend display"""
    
    # Get basic algorithm info
    conn = system_db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM algorithm_instances WHERE id = ? AND status = 'running'", (algo_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    # Convert to dict
    algo_data = dict(result)
    
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
    
    return algo_data