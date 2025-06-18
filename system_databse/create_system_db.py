#!/usr/bin/env python3
"""
################################################################################
# FILE: create_system_db.py
# PURPOSE: Create the system.db database with initial schema
################################################################################
"""

import sqlite3
import os
from datetime import datetime


################################################################################
# DATABASE CREATION
################################################################################

def create_system_database():
    """Create system.db with complete schema"""
    
    # Ensure system_database directory exists
    db_dir = "system_databse"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[OK] Created directory: {db_dir}")
    
    db_path = os.path.join(db_dir, "system.db")
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create algorithm_instances table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS algorithm_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                algorithm_type TEXT NOT NULL,
                ticker TEXT NOT NULL,
                initial_capital REAL NOT NULL CHECK(initial_capital > 0),
                status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running', 'stopped')),
                created_at TEXT NOT NULL,
                stopped_at TEXT
            )
        """)
        
        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algorithm_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('buy', 'sell')),
                shares INTEGER NOT NULL CHECK(shares > 0),
                price REAL NOT NULL CHECK(price > 0),
                timestamp TEXT NOT NULL,
                FOREIGN KEY (algorithm_id) REFERENCES algorithm_instances(id)
            )
        """)
        
        # Create system_config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Insert default PIN
        cursor.execute("""
            INSERT OR IGNORE INTO system_config (key, value) 
            VALUES ('pin', '2020')
        """)
        
        # Commit all changes
        conn.commit()
        
        # Verify the schema by listing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if len(tables) == 3:  # Should have 3 tables
            print(f"[OK] Database created at {db_path}")
            print(f"[OK] All tables created successfully: {', '.join([t[0] for t in tables])}")
            
            # Verify PIN was set
            cursor.execute("SELECT value FROM system_config WHERE key='pin'")
            pin_result = cursor.fetchone()
            if pin_result:
                print("[OK] Default PIN configured")
            else:
                print("[ERROR] Default PIN not set")
        else:
            print(f"[ERROR] Expected 3 tables, found {len(tables)}")
        
    except Exception as e:
        print(f"[ERROR] Database creation failed: {str(e)}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    create_system_database()