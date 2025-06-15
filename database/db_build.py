"""
################################################################################
# FILE: db_build.py
# PURPOSE: Database build script that creates the market-hours-only database
################################################################################
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


################################################################################
# DATABASE CREATION
################################################################################

def create_database():
    """Create the market-hours-only database"""
    print(f"[{datetime.now().isoformat()}] Creating database")
    print("="*50)
    
    try:
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        
        # Import and initialize the database
        from db_manager import initialize_database
        
        # Create the database
        initialize_database()
        
        print(f"\n[{datetime.now().isoformat()}] Database creation completed")
        print("="*50)
        
    except Exception as e:
        print(f"\n[{datetime.now().isoformat()}] Database creation failed")
        raise

if __name__ == "__main__":
    create_database()