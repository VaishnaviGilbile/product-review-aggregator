"""
Selenium-based scraper to bypass CAPTCHA and bot detection
Install: pip install selenium webdriver-manager
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random
import logging

logger = logging.getLogger(__name__)

class SeleniumScraper:
    """Browser-based scraper that bypasses CAPTCHA"""
    
    def __init__(self):
        self.driver = None
    
    def _create_driver(self):
        """Create Chrome driver with anti-detection settings"""
        options = Options()
        
        # Define user agents FIRST
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        # Anti-detection settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Make it look like real browser
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # Random user agent
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Uncomment to run headless (no visible browser)
        # options.add_argument('--headless')
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            # Execute CDP commands to avoid detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": random.choice(user_agents)
            })
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Selenium driver created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create driver: {e}")
            return None
    
    def get_page_source(self, url: str, wait_time: int = 5) -> str:
        """Get page source using Selenium"""
        try:
            if not self.driver:
                self.driver = self._create_driver()
            
            if not self.driver:
                return None
            
            logger.info(f"🌐 Loading URL with Selenium: {url[:80]}...")
            
            # Navigate to URL
            self.driver.get(url)
            
            # Random wait to mimic human behavior
            human_delay = random.uniform(3, 6)
            logger.info(f"⏰ Waiting {human_delay:.1f}s for page load...")
            time.sleep(human_delay)
            
            # Scroll down to load dynamic content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Check if CAPTCHA is present
            page_text = self.driver.page_source.lower()
            if 'captcha' in page_text or 'robot' in page_text:
                logger.warning("⚠️ CAPTCHA detected - manual intervention may be needed")
                # Wait longer for manual CAPTCHA solving
                logger.info("Waiting 60s for potential CAPTCHA solving...")
                logger.info("👉 Please solve the CAPTCHA in the browser window if it appears")
                time.sleep(60)  # Increased from 30 to 60 seconds
            
            html = self.driver.page_source
            logger.info("✅ Page source retrieved successfully")
            return html
            
        except Exception as e:
            logger.error(f"❌ Error getting page source: {e}")
            return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔒 Browser closed")
            except:
                pass
            self.driver = None
    
    def __del__(self):
        """Cleanup"""
        self.close()


# Integration with existing scrapers
class SeleniumAmazonScraper:
    """Amazon scraper using Selenium"""
    
    def __init__(self, config):
        self.config = config
        self.selenium = SeleniumScraper()
        self.BASE_URL = 'https://www.amazon.in'
    
    def scrape_product_details(self, product_url: str):
        """Scrape product details using Selenium"""
        try:
            html = self.selenium.get_page_source(product_url)
            if not html:
                return {}
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product details
            details = {}
            
            # Title
            title = soup.select_one('#productTitle, h1.product-title')
            details['name'] = title.text.strip() if title else "Unknown Product"
            
            # Image
            img = soup.select_one('#landingImage, .a-dynamic-image, img[data-old-hires]')
            if img:
                details['image_url'] = img.get('src') or img.get('data-old-hires')
            else:
                details['image_url'] = None
            
            # Description
            desc = soup.select_one('#feature-bullets, #productDescription')
            details['description'] = desc.text.strip()[:500] if desc else ""
            
            # Rating
            rating = soup.select_one('[data-hook="rating-out-of-text"], .a-icon-star')
            if rating:
                import re
                match = re.search(r'([\d.]+)', rating.text)
                details['rating'] = float(match.group(1)) if match else None
            
            # Price
            price = soup.select_one('.a-price-whole, .a-price .a-offscreen')
            if price:
                import re
                price_text = price.text.replace(',', '').replace('₹', '')
                match = re.search(r'([\d.]+)', price_text)
                details['price'] = float(match.group(1)) if match else None
            
            # Category
            breadcrumb = soup.select_one('#wayfinding-breadcrumbs_container')
            details['category'] = breadcrumb.text.strip()[:100] if breadcrumb else None
            
            logger.info(f"✅ Scraped product: {details['name'][:50]}...")
            return details
            
        except Exception as e:
            logger.error(f"❌ Error scraping product details: {e}")
            return {}
    
    def scrape_reviews(self, product_url: str, max_reviews: int = 30):
        """Scrape reviews using Selenium"""
        try:
            # Get ASIN
            import re
            match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
            if not match:
                return []
            
            asin = match.group(1)
            
            # Visit product page first (more human-like)
            logger.info("🌐 First visiting product page to appear more human...")
            product_html = self.selenium.get_page_source(product_url, wait_time=5)
            time.sleep(random.uniform(3, 6))  # Wait between pages
            
            # Now go to reviews
            review_url = f"{self.BASE_URL}/product-reviews/{asin}"
            
            html = self.selenium.get_page_source(review_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            reviews = []
            
            # Find review containers
            review_divs = soup.select('[data-hook="review"]')
            
            for div in review_divs[:max_reviews]:
                try:
                    review = {}
                    
                    # Title
                    title = div.select_one('[data-hook="review-title"]')
                    review['title'] = title.text.strip() if title else ""
                    
                    # Text
                    text = div.select_one('[data-hook="review-body"]')
                    review['text'] = text.text.strip() if text else ""
                    
                    # Rating
                    rating = div.select_one('[data-hook="review-star-rating"]')
                    if rating:
                        import re
                        match = re.search(r'([\d.]+)', rating.text)
                        review['rating'] = float(match.group(1)) if match else 0.0
                    else:
                        review['rating'] = 0.0
                    
                    # Author
                    author = div.select_one('.a-profile-name')
                    review['author'] = author.text.strip() if author else "Anonymous"
                    
                    # Date
                    date = div.select_one('[data-hook="review-date"]')
                    review['date'] = None  # Parse date if needed
                    
                    # Verified
                    verified = div.select_one('[data-hook="avp-badge"]')
                    review['verified'] = verified is not None
                    
                    # Helpful count
                    helpful = div.select_one('[data-hook="helpful-vote-statement"]')
                    review['helpful_count'] = 0
                    if helpful:
                        import re
                        match = re.search(r'(\d+)', helpful.text)
                        review['helpful_count'] = int(match.group(1)) if match else 0
                    
                    if review['text']:
                        reviews.append(review)
                        
                except Exception as e:
                    logger.error(f"Error parsing review: {e}")
                    continue
            
            logger.info(f"✅ Scraped {len(reviews)} reviews")
            return reviews
            
        except Exception as e:
            logger.error(f"❌ Error scraping reviews: {e}")
            return []
    
    def _extract_asin(self, url: str):
        """Extract ASIN from URL"""
        import re
        match = re.search(r'/dp/([A-Z0-9]{10})', url)
        return match.group(1) if match else None
    
    def close(self):
        """Close browser"""
        self.selenium.close()


class SeleniumFlipkartScraper:
    """Flipkart scraper using Selenium"""
    
    def __init__(self, config):
        self.config = config
        self.selenium = SeleniumScraper()
        self.BASE_URL = 'https://www.flipkart.com'
    
    def scrape_product_details(self, product_url: str):
        """Scrape Flipkart product details"""
        try:
            html = self.selenium.get_page_source(product_url)
            if not html:
                return {}
            
            soup = BeautifulSoup(html, 'html.parser')
            details = {}
            
            # Title
            title = soup.select_one('span.B_NuCI, h1.yhB1nd, span.VU-ZEz')
            details['name'] = title.text.strip() if title else "Unknown Product"
            
            # Image
            img = soup.select_one('img._396cs4, img._2r_T1I')
            details['image_url'] = img.get('src') if img else None
            
            # Description
            desc = soup.select_one('div._1mXcCf, div._3WHvuP')
            details['description'] = desc.text.strip()[:500] if desc else ""
            
            # Rating
            rating = soup.select_one('div._3LWZlK, div._3i9cDe')
            if rating:
                import re
                match = re.search(r'([\d.]+)', rating.text)
                details['rating'] = float(match.group(1)) if match else None
            
            # Price
            price = soup.select_one('div._30jeq3, div._16Jk6d')
            if price:
                import re
                price_text = price.text.replace(',', '').replace('₹', '')
                match = re.search(r'([\d.]+)', price_text)
                details['price'] = float(match.group(1)) if match else None
            
            # Category
            breadcrumb = soup.select_one('div._2whKao')
            details['category'] = breadcrumb.text.strip()[:100] if breadcrumb else None
            
            logger.info(f"✅ Scraped Flipkart product: {details['name'][:50]}...")
            return details
            
        except Exception as e:
            logger.error(f"❌ Error scraping Flipkart product: {e}")
            return {}
    
    def scrape_reviews(self, product_url: str, max_reviews: int = 30):
        """Scrape Flipkart reviews"""
        try:
            # Visit product page first
            logger.info("🌐 First visiting product page...")
            product_html = self.selenium.get_page_source(product_url, wait_time=5)
            time.sleep(random.uniform(3, 6))
            
            # Get reviews from same page or reviews section
            html = self.selenium.get_page_source(product_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            reviews = []
            
            # Find review containers
            review_divs = soup.select('div._1AtVbE, div.col._2wzgFH, div._27M-vq')
            
            for div in review_divs[:max_reviews]:
                try:
                    review = {}
                    
                    # Title
                    title = div.select_one('p._2-N8zT')
                    review['title'] = title.text.strip() if title else ""
                    
                    # Text
                    text = div.select_one('div.t-ZTKy, div._2ZibVB')
                    review['text'] = text.text.strip() if text else ""
                    
                    # Rating
                    rating = div.select_one('div._3LWZlK, div._3i9cDe')
                    if rating:
                        import re
                        match = re.search(r'([\d.]+)', rating.text)
                        review['rating'] = float(match.group(1)) if match else 0.0
                    else:
                        review['rating'] = 0.0
                    
                    # Author
                    author = div.select_one('p._2sc7ZR, p._2NsDsF')
                    review['author'] = author.text.strip() if author else "Anonymous"
                    
                    # Date
                    review['date'] = None
                    
                    # Verified
                    review['verified'] = 'Certified Buyer' in div.text
                    
                    review['helpful_count'] = 0
                    
                    if review['text']:
                        reviews.append(review)
                        
                except Exception as e:
                    logger.error(f"Error parsing Flipkart review: {e}")
                    continue
            
            logger.info(f"✅ Scraped {len(reviews)} Flipkart reviews")
            return reviews
            
        except Exception as e:
            logger.error(f"❌ Error scraping Flipkart reviews: {e}")
            return []
    
    def _extract_product_id(self, url: str):
        """Extract product ID from URL"""
        import re
        match = re.search(r'/p/([A-Za-z0-9]+)', url)
        return match.group(1) if match else None
    
    def close(self):
        """Close browser"""
        self.selenium.close()