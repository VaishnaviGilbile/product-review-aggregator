import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///reviews.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis for Celery
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Scraping settings
    SCRAPING_DELAY = 2  # seconds between requests
    MAX_REVIEWS_PER_PRODUCT = 100
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

    
    # Sentiment analysis
    SENTIMENT_MODEL = 'distilbert-base-uncased-finetuned-sst-2-english'
    SENTIMENT_BATCH_SIZE = 32
    
    # Cache settings
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/2'
    RATELIMIT_DEFAULT = "100 per hour"

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/reviews'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously in tests

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}