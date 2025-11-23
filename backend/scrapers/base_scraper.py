from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
import random
import hashlib

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Enhanced base scraper"""
    
    def __init__(self, config):
        self.config = config
        self.request_count = 0
        self.session = self._create_session()
        self.last_request_time = 0
        
        logger.info(f"Initialized {self.get_source_name()} scraper")
    
    def _create_session(self):
        """Create a new session with rotating headers"""
        session = requests.Session()
        session.headers.update(self._get_random_headers())
        
        # Add connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # We handle retries manually
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def _get_random_headers(self):
       
        # Get random user agent from config
        if hasattr(self.config, 'USER_AGENTS'):
            user_agents = self.config.USER_AGENTS
        elif hasattr(self.config, 'get'):
            user_agents = self.config.get('USER_AGENTS', [])
        else:
            user_agents = []
        
        # Fallback to default if no user agents configured
        if not user_agents:
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
        
        user_agent = random.choice(user_agents)
        
        # More realistic browser headers
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # Randomly add referer
        if random.random() > 0.3:
            referers = [
                'https://www.google.com/',
                'https://www.google.co.in/',
                'https://www.google.co.in/search?q=',
            ]
            headers['Referer'] = random.choice(referers)
        
        return headers
    
    def _rotate_session(self):
        """Rotate session after certain number of requests"""
        if self.request_count >= self.config.get('MAX_REQUESTS_PER_SESSION', 20):
            logger.info("🔄 Rotating session to avoid detection")
            self.session.close()
            self.session = self._create_session()
            self.request_count = 0
            # Add extra delay after rotation
            delay = random.uniform(15, 25)
            logger.info(f"💤 Sleeping {delay:.1f}s after session rotation")
            time.sleep(delay)
    
    def _rate_limit(self):
        """Implement rate limiting with random delays"""
        if not self.config.get('RATE_LIMIT_ENABLED', True) if hasattr(self.config, 'get') else True:
            return
        
        # Get random delay
        if hasattr(self.config, 'get_random_delay'):
            delay = self.config.get_random_delay()
        elif hasattr(self.config, 'get'):
            min_delay = self.config.get('SCRAPING_DELAY_MIN', 5)
            max_delay = self.config.get('SCRAPING_DELAY_MAX', 10)
            delay = random.uniform(min_delay, max_delay)
        else:
            delay = random.uniform(5, 10)
        
        # Calculate time since last request
        current_time = time.time()
        
        # If this is not the first request
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            
            # If not enough time has passed, wait
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                logger.debug(f"⏰ Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        else:
            # First request - also apply delay
            logger.debug(f"⏰ First request: applying initial delay of {delay:.2f}s")
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch page with enhanced anti-blocking measures"""
        for attempt in range(retries):
            try:
                # Rate limiting
                self._rate_limit()
                
                # Rotate session if needed
                self._rotate_session()
                
                # Randomize headers for each request
                self.session.headers.update(self._get_random_headers())
                
                # Add cookies to appear more legitimate
                if not self.session.cookies:
                    self.session.cookies.set('session-id', f'session-{random.randint(100000, 999999)}')
                
                # Make request with longer timeout
                logger.info(f"🌐 Fetching: {url[:80]}... (attempt {attempt + 1}/{retries})")
                
                response = self.session.get(
                    url, 
                    timeout=30,
                    allow_redirects=True
                )
                
                # Check for blocking indicators
                if self._is_blocked(response):
                    logger.warning(f"🚫 Blocking detected on attempt {attempt + 1}")
                    
                    if attempt < retries - 1:
                        # Exponential backoff with jitter
                        backoff = (3 ** attempt) + random.uniform(2, 5)
                        logger.info(f"⏳ Backing off for {backoff:.2f}s")
                        time.sleep(backoff)
                        
                        # Create new session on blocking
                        if attempt > 0:
                            logger.info("🔄 Creating new session due to blocking")
                            self.session.close()
                            self.session = self._create_session()
                        
                        continue
                    else:
                        logger.error("❌ Max retries reached, still blocked")
                        return None
                
                response.raise_for_status()
                self.request_count += 1
                
                # Check if we got actual HTML content
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    logger.warning(f"⚠️ Unexpected content type: {content_type}")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(5, 10))
                        continue
                    return None
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check if we got meaningful content
                if not soup.find('body') or len(soup.get_text().strip()) < 100:
                    logger.warning("⚠️ Page content seems empty or invalid")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(5, 10))
                        continue
                    return None
                
                # Add random delay to appear more human
                human_delay = random.uniform(1.0, 3.0)
                logger.debug(f"😴 Human-like delay: {human_delay:.2f}s")
                time.sleep(human_delay)
                
                logger.info(f"✅ Successfully fetched page")
                return soup
                
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout on attempt {attempt + 1} for {url[:80]}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Connection error on attempt {attempt + 1}: {str(e)[:100]}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request failed on attempt {attempt + 1}: {str(e)[:100]}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
        
        logger.error(f"❌ Failed to fetch page after {retries} attempts")
        return None
    
    def _is_blocked(self, response):
        """Check if response indicates blocking - with better detection"""
        # Check status code
        if response.status_code in [403, 429, 503]:
            logger.warning(f"🚫 Blocked status code: {response.status_code}")
            return True
        
        # Check for redirect to CAPTCHA or blocking page
        if 'captcha' in response.url.lower() or 'block' in response.url.lower():
            logger.warning(f"🚫 Redirected to blocking page: {response.url}")
            return True
        
        # Check content length - blocked pages are usually very short
        if len(response.content) < 500:
            logger.warning(f"🚫 Suspiciously short response: {len(response.content)} bytes")
            return True
        
        # Check for common blocking indicators in content
        content_lower = response.text.lower()
        blocking_indicators = [
            'sorry, we just need to make sure you\'re not a robot',
            'enter the characters you see below',
            'captcha',
            'robot check',
            'access denied',
            'blocked',
            'unusual traffic',
            'automated access',
            'to discuss automated access',
            'security check',
            'please verify',
            'are you a robot',
        ]
        
        for indicator in blocking_indicators:
            if indicator in content_lower:
                logger.warning(f"🚫 Blocking indicator found: '{indicator}'")
                return True
        
        return False
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the source"""
        pass
    
    @abstractmethod
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for products"""
        pass
    
    @abstractmethod
    def scrape_product_details(self, product_url: str) -> Dict:
        """Scrape product details"""
        pass
    
    @abstractmethod
    def scrape_reviews(self, product_url: str, max_reviews: int = 100) -> List[Dict]:
        """Scrape reviews"""
        pass
    
    def normalize_rating(self, rating: float, max_rating: float = 5.0) -> float:
        """Normalize rating to 1-5 scale"""
        if max_rating == 5.0:
            return rating
        return (rating / max_rating) * 5.0
    
    def parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        formats = [
            '%B %d, %Y',
            '%d %B %Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        logger.debug(f"Could not parse date: {date_string}")
        return None
    
    def clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        text = ' '.join(text.split())
        return text.strip()
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from URL"""
        return url.split('/')[-1] if url else None
    
    def get_session_fingerprint(self) -> str:
        """Get unique fingerprint for current session"""
        user_agent = self.session.headers.get('User-Agent', '')
        fingerprint = hashlib.md5(f"{user_agent}{time.time()}".encode()).hexdigest()[:8]
        return fingerprint
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except:
                pass