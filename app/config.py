import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Telegram Bot Settings
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not found in environment variables")
    
    # Database Settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    
    # Cache Settings
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 3600))  # 1 hour default
    
    # Debug Settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
