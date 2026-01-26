"""
WSGI wrapper for Vercel Python deployment
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the Flask app from the main app.py
from app import app

# Vercel expects a callable WSGI app
if __name__ == '__main__':
    app.run()
