import os
from datetime import timedelta
import random

class Config:
    """Base configuration with enhanced anti-blocking settings"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///reviews.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Scraping delays - INCREASED to avoid blocking
    SCRAPING_DELAY_MIN = 5   # Minimum delay between requests (increased from 3)
    SCRAPING_DELAY_MAX = 12  # Maximum delay between requests (increased from 8)
    
    # Request limits
    MAX_REVIEWS_PER_PRODUCT = 30  # Reduced from 50 to be less aggressive
    MAX_PRODUCTS_PER_SEARCH = 10
    MAX_REQUESTS_PER_SESSION = 15  # Reduced from 20
    
    # Rotating User Agents - More variety
    USER_AGENTS = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        
        # Chrome on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Safari on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        
        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
        
        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        
        # Chrome on Linux
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ]
    
    # Request headers
    ACCEPT_LANGUAGE = 'en-US,en;q=0.9,hi;q=0.8'
    ACCEPT_ENCODING = 'gzip, deflate, br'
    
    # Retry strategy - MORE CONSERVATIVE
    MAX_RETRIES = 4  # Increased from 3
    RETRY_BACKOFF_FACTOR = 3  # Increased from 2 - more aggressive backoff
    
    # Rate limiting
    RATE_LIMIT_ENABLED = True
    MIN_TIME_BETWEEN_REQUESTS = 5  # Increased from 3 seconds
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 3600
    CACHE_SEARCH_RESULTS = 1800
    
    # Proxy settings (optional)
    USE_PROXY = os.environ.get('USE_PROXY', 'false').lower() == 'true'
    PROXY_LIST = os.environ.get('PROXY_LIST', '').split(',') if os.environ.get('PROXY_LIST') else []
    
    @staticmethod
    def get_random_user_agent():
        """Get a random user agent"""
        return random.choice(Config.USER_AGENTS)
    
    @staticmethod
    def get_random_delay():
        """Get a random delay between min and max"""
        return random.uniform(Config.SCRAPING_DELAY_MIN, Config.SCRAPING_DELAY_MAX)
    
    def get(self, key, default=None):
        """Dictionary-like access to config values"""
        return getattr(self, key, default)

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SCRAPING_DELAY_MIN = 5
    SCRAPING_DELAY_MAX = 12
    MAX_REVIEWS_PER_PRODUCT = 30

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/reviews'
    SCRAPING_DELAY_MIN = 8
    SCRAPING_DELAY_MAX = 15
    MAX_REQUESTS_PER_SESSION = 10  # More conservative in production
    MAX_REVIEWS_PER_PRODUCT = 25

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SCRAPING_DELAY_MIN = 0
    SCRAPING_DELAY_MAX = 0

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}