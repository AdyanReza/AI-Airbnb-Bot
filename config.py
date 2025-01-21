import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # API Settings
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    AIRBNB_API_KEY = os.getenv('AIRBNB_API_KEY')
    
    # Database Settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    
    # Redis Cache Settings
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # ML Model Settings
    MODEL_PATH = os.getenv('MODEL_PATH', 'app/models/trained_model.pkl')
    
    # Application Settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 3600))  # 1 hour default
