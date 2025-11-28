"""
Vercel serverless entry point
"""
from serverless_app import app

# Export app for Vercel
__all__ = ['app']
