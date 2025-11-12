from .base_scraper import BaseScraper
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus
from datetime import datetime

logger = logging.getLogger(__name__)

class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart India"""
    
    BASE_URL = 'https://www.flipkart.com'
    
    def get_source_name(self) -> str:
        return 'flipkart'
    
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Flipkart for products"""
        search_url = f"{self.BASE_URL}/search?q={quote_plus(query)}"
        soup = self._get_page(search_url)
        
        if not soup:
            return []
        
        products = []
        
        # Flipkart uses different CSS classes - try multiple selectors
        product_containers = soup.select('div[data-id]')[:max_results]
        
        if not product_containers:
            # Try alternative selector
            product_containers = soup.select('div._1AtVbE')[:max_results]
        
        for item in product_containers:
            try:
                # Extract product details
                title_elem = item.select_one('div._4rR01T, a._1fQZEK, div.IRpwTa')
                link_elem = item.select_one('a._1fQZEK, a._2rpwqI')
                image_elem = item.select_one('img._396cs4')
                price_elem = item.select_one('div._30jeq3, div._30jeq3._1_WHN1')
                rating_elem = item.select_one('div._3LWZlK')
                
                if not title_elem or not link_elem:
                    continue
                
                product_url = urljoin(self.BASE_URL, link_elem.get('href', ''))
                product_id = self._extract_product_id(product_url)
                
                # Get title text
                title = title_elem.get('title') or title_elem.text.strip()
                
                product = {
                    'name': self.clean_text(title),
                    'url': product_url,
                    'source_product_id': product_id,
                    'image_url': image_elem['src'] if image_elem else None,
                    'price': self._parse_price(price_elem.text) if price_elem else None,
                    'rating': self._parse_rating(rating_elem.text) if rating_elem else None
                }
                products.append(product)
                
            except Exception as e:
                logger.error(f"Error parsing product: {e}")
                continue
        
        return products
    
    def scrape_product_details(self, product_url: str) -> Dict:
        """Scrape detailed product information"""
        soup = self._get_page(product_url)
        
        if not soup:
            return {}
        
        details = {
            'name': self._extract_title(soup),
            'description': self._extract_description(soup),
            'rating': self._extract_overall_rating(soup),
            'review_count': self._extract_review_count(soup),
            'image_url': self._extract_image(soup),
            'price': self._extract_price(soup)
        }
        
        return details
    
    def scrape_reviews(self, product_url: str, max_reviews: int = 100) -> List[Dict]:
        """Scrape product reviews"""
        product_id = self._extract_product_id(product_url)
        if not product_id:
            logger.error(f"Could not extract product ID from {product_url}")
            return []
        
        reviews = []
        page = 1
        
        while len(reviews) < max_reviews:
            # Flipkart review URL format
            review_url = f"{product_url}&page={page}"
            
            # If URL doesn't have reviews section, construct it
            if '/product-reviews/' not in review_url:
                # Extract product ID and construct review URL
                review_url = product_url.replace('/p/', '/product-reviews/')
                if '?' in review_url:
                    review_url = review_url.split('?')[0]
                review_url = f"{review_url}?page={page}"
            
            soup = self._get_page(review_url)
            
            if not soup:
                break
            
            page_reviews = self._parse_reviews_page(soup)
            if not page_reviews:
                break
            
            reviews.extend(page_reviews)
            page += 1
            
            # Stop if we've reached max or no more reviews
            if len(reviews) >= max_reviews or len(page_reviews) < 5:
                break
        
        return reviews[:max_reviews]
    
    def _parse_reviews_page(self, soup) -> List[Dict]:
        """Parse reviews from a single page"""
        reviews = []
        
        # Flipkart review containers
        review_divs = soup.select('div._1AtVbE, div.col._2wzgFH')
        
        for review_div in review_divs:
            try:
                review = {
                    'title': self._extract_review_title(review_div),
                    'text': self._extract_review_text(review_div),
                    'rating': self._extract_review_rating(review_div),
                    'author': self._extract_review_author(review_div),
                    'date': self._extract_review_date(review_div),
                    'verified': self._is_verified_purchase(review_div),
                    'helpful_count': self._extract_helpful_count(review_div)
                }
                
                if review['text']:  # Only add if review has text
                    reviews.append(review)
                    
            except Exception as e:
                logger.error(f"Error parsing review: {e}")
                continue
        
        return reviews
    
    # Helper methods for extraction
    
    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Flipkart URL"""
        # Flipkart product IDs are in format: /product-name/p/itm123456789
        patterns = [
            r'/p/itm([A-Za-z0-9]+)',
            r'pid=([A-Za-z0-9]+)',
            r'/([A-Z0-9]{16})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float"""
        try:
            # Remove ₹ symbol and commas
            price = re.sub(r'[^\d.]', '', price_text)
            return float(price)
        except:
            return None
    
    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating from text"""
        try:
            match = re.search(r'([\d.]+)', rating_text)
            return float(match.group(1)) if match else None
        except:
            return None
    
    def _extract_title(self, soup) -> str:
        """Extract product title"""
        # Try multiple selectors
        selectors = ['span.B_NuCI', 'h1.yhB1nd', 'h1 span']
        for selector in selectors:
            title = soup.select_one(selector)
            if title:
                return self.clean_text(title.text)
        return ""
    
    def _extract_description(self, soup) -> str:
        """Extract product description"""
        desc_div = soup.select_one('div._1mXcCf, div._3WHvuP')
        if desc_div:
            # Get all text from description
            desc_parts = desc_div.find_all(['li', 'p'])
            if desc_parts:
                return self.clean_text(' '.join([p.text for p in desc_parts]))
            return self.clean_text(desc_div.text)
        return ""
    
    def _extract_overall_rating(self, soup) -> Optional[float]:
        """Extract overall rating"""
        rating = soup.select_one('div._3LWZlK, div._3i9cDe')
        if rating:
            return self._parse_rating(rating.text)
        return None
    
    def _extract_review_count(self, soup) -> int:
        """Extract review count"""
        count_elem = soup.select_one('span._2_R_DZ, span._13vcmD')
        if count_elem:
            try:
                # Extract number from text like "1,234 Ratings & 567 Reviews"
                text = count_elem.text
                match = re.search(r'(\d+(?:,\d+)*)\s*(?:Reviews?|Ratings?)', text, re.IGNORECASE)
                if match:
                    return int(match.group(1).replace(',', ''))
            except:
                pass
        return 0
    
    def _extract_image(self, soup) -> Optional[str]:
        """Extract product image"""
        img = soup.select_one('img._396cs4, img._2r_T1I')
        return img['src'] if img else None
    
    def _extract_price(self, soup) -> Optional[float]:
        """Extract product price"""
        price = soup.select_one('div._30jeq3, div._30jeq3._1_WHN1')
        return self._parse_price(price.text) if price else None
    
    def _extract_review_title(self, review_div) -> str:
        """Extract review title"""
        title = review_div.select_one('p._2-N8zT')
        return self.clean_text(title.text) if title else ""
    
    def _extract_review_text(self, review_div) -> str:
        """Extract review text"""
        # Try multiple selectors
        text = review_div.select_one('div.t-ZTKy, div._2ZibVB')
        if text:
            # Check for "READ MORE" button and get full text
            full_text = text.get('data-full-text') or text.text
            return self.clean_text(full_text)
        return ""
    
    def _extract_review_rating(self, review_div) -> float:
        """Extract review rating"""
        rating = review_div.select_one('div._3LWZlK, div._3i9cDe')
        if rating:
            rating_val = self._parse_rating(rating.text)
            return rating_val if rating_val else 0.0
        return 0.0
    
    def _extract_review_author(self, review_div) -> str:
        """Extract review author"""
        author = review_div.select_one('p._2sc7ZR, p._2NsDsF')
        return self.clean_text(author.text) if author else "Anonymous"
    
    def _extract_review_date(self, review_div) -> Optional[datetime]:
        """Extract review date"""
        date_elem = review_div.select_one('p._2sc7ZR._3j50Xe, p._2NsDsF')
        if date_elem:
            date_text = date_elem.text
            # Flipkart date formats: "15 days ago", "2 months ago", "1 Jan 2024"
            return self._parse_flipkart_date(date_text)
        return None
    
    def _parse_flipkart_date(self, date_string: str) -> Optional[datetime]:
        """Parse Flipkart-specific date formats"""
        from datetime import timedelta
        
        date_string = date_string.lower().strip()
        now = datetime.now()
        
        # Handle relative dates
        if 'day' in date_string or 'days' in date_string:
            match = re.search(r'(\d+)\s*days?', date_string)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)
        
        elif 'month' in date_string or 'months' in date_string:
            match = re.search(r'(\d+)\s*months?', date_string)
            if match:
                months = int(match.group(1))
                return now - timedelta(days=months * 30)
        
        elif 'year' in date_string or 'years' in date_string:
            match = re.search(r'(\d+)\s*years?', date_string)
            if match:
                years = int(match.group(1))
                return now - timedelta(days=years * 365)
        
        # Try standard date parsing
        return self.parse_date(date_string)
    
    def _is_verified_purchase(self, review_div) -> bool:
        """Check if review is from verified purchase"""
        # Flipkart shows "Certified Buyer" badge
        verified = review_div.select_one('span._2NsDsF:contains("Certified Buyer")')
        if not verified:
            # Alternative check
            verified = review_div.find(string=re.compile('Certified Buyer', re.IGNORECASE))
        return verified is not None
    
    def _extract_helpful_count(self, review_div) -> int:
        """Extract helpful count"""
        helpful = review_div.select_one('div._1i2dFb')
        if helpful:
            try:
                match = re.search(r'(\d+)', helpful.text)
                return int(match.group(1)) if match else 0
            except:
                pass
        return 0