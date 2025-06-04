#!/usr/bin/env python3
"""
System Database Manager
Functions to interact with system.db for algorithm state management
"""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Database path
DB_PATH = "system.db"


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def get_connection():
    """Get database connection with foreign keys enabled"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Return rows as dictionaries instead of tuples
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# PIN MANAGEMENT
# =============================================================================

def get_pin() -> str:
    """Get the current PIN from system_config"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM system_config WHERE key = 'pin'")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    else:
        raise ValueError("PIN not found in system configuration")


# =============================================================================
# ALGORITHM LIFECYCLE MANAGEMENT
# =============================================================================

def generate_display_name(ticker: str, algo_type: str) -> str:
    """Generate display name: NVDA_SMA_20240102_143022"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{ticker}_{algo_type}_{timestamp}"

def create_algorithm(ticker: str, algo_type: str, initial_capital: float) -> int:
    """Create a new algorithm instance and return its ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Generate display name and current timestamp
        display_name = generate_display_name(ticker, algo_type)
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Insert new algorithm
        cursor.execute("""
            INSERT INTO algorithm_instances 
            (display_name, algorithm_type, ticker, initial_capital, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (display_name, algo_type, ticker, initial_capital, created_at))
        
        # Get the auto-generated ID
        algorithm_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return algorithm_id
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise e

def stop_algorithm(algo_id: int) -> bool:
    """Stop an algorithm by setting status to 'stopped'"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        stopped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        cursor.execute("""
            UPDATE algorithm_instances 
            SET status = 'stopped', stopped_at = ?
            WHERE id = ? AND status = 'running'
        """, (stopped_at, algo_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise e

def get_algorithm(algo_id: int) -> Optional[Dict[str, Any]]:
    """Get a single algorithm by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM algorithm_instances WHERE id = ?", (algo_id,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def get_all_algorithms(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all algorithms, optionally filtered by status"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute("SELECT * FROM algorithm_instances WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM algorithm_instances ORDER BY created_at DESC")
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


# =============================================================================
# TRANSACTION MANAGEMENT
# =============================================================================

def record_buy(algo_id: int, shares: int, price: float) -> int:
    """Record a buy transaction and return transaction ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        cursor.execute("""
            INSERT INTO transactions 
            (algorithm_id, type, shares, price, timestamp)
            VALUES (?, 'buy', ?, ?, ?)
        """, (algo_id, shares, price, timestamp))
        
        transaction_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return transaction_id
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise e

def record_sell(algo_id: int, shares: int, price: float) -> int:
    """Record a sell transaction and return transaction ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        cursor.execute("""
            INSERT INTO transactions 
            (algorithm_id, type, shares, price, timestamp)
            VALUES (?, 'sell', ?, ?, ?)
        """, (algo_id, shares, price, timestamp))
        
        transaction_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return transaction_id
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise e

def get_transactions(algo_id: int) -> List[Dict[str, Any]]:
    """Get all transactions for an algorithm"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM transactions 
        WHERE algorithm_id = ? 
        ORDER BY timestamp DESC
    """, (algo_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]