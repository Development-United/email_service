"""
Vercel serverless entry point
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import modules
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from serverless_app import app

# Export app for Vercel
__all__ = ['app']
