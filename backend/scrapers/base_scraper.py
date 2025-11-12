from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.delay = config.get('SCRAPING_DELAY', 2)
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the source (e.g., 'amazon', 'flipkart')"""
        pass
    
    @abstractmethod
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for products by query
        Returns list of dicts with: name, url, image_url, source_product_id, price
        """
        pass
    
    @abstractmethod
    def scrape_product_details(self, product_url: str) -> Dict:
        """
        Scrape product details from URL
        Returns dict with: name, description, rating, review_count, image_url
        """
        pass
    
    @abstractmethod
    def scrape_reviews(self, product_url: str, max_reviews: int = 100) -> List[Dict]:
        """
        Scrape reviews for a product
        Returns list of dicts with: title, text, rating, author, date, verified, helpful_count
        """
        pass
    
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse a page with retry logic"""
        for attempt in range(retries):
            try:
                time.sleep(self.delay)  # Rate limiting
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All retries failed for {url}")
                    return None
                time.sleep(self.delay * (attempt + 1))
        return None
    
    def normalize_rating(self, rating: float, max_rating: float = 5.0) -> float:
        """Normalize rating to 1-5 scale"""
        if max_rating == 5.0:
            return rating
        return (rating / max_rating) * 5.0
    
    def parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string to datetime - override in subclass for site-specific formats"""
        # Common formats to try
        formats = [
            '%B %d, %Y',  # January 1, 2024
            '%d %B %Y',   # 1 January 2024
            '%Y-%m-%d',   # 2024-01-01
            '%d-%m-%Y',   # 01-01-2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_string}")
        return None
    
    def clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from URL - override in subclass"""
        return url.split('/')[-1] if url else None