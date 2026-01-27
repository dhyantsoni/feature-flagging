"""
Vercel Serverless Function Handler for Flask App
"""
import sys
from pathlib import Path

# Add parent directory to Python path  
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the Flask app (this is a WSGI application)
from api.index import app as application

# Vercel's @vercel/python looks for 'handler' or uses the WSGI app directly
# Just export the Flask app as the handler
handler = application
