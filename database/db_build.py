#!/usr/bin/env python3
"""
Database Build Script - Creates the market-hours-only database
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def create_database():
    """Create the market-hours-only database"""
    print("🔄 Creating market-hours-only database...")
    print("="*50)
    
    try:
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        
        # Import and initialize the database
        from db_manager import initialize_database
        
        # Create the database
        initialize_database()
        
        print("\n✅ Database creation completed!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Database creation failed: {e}")
        raise

if __name__ == "__main__":
    create_database()