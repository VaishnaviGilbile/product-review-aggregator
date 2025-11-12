from .base_scraper import BaseScraper
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus
from datetime import datetime

logger = logging.getLogger(__name__)

class AmazonScraper(BaseScraper):
    """Scraper for Amazon India"""
    
    BASE_URL = 'https://www.amazon.in'
    
    def get_source_name(self) -> str:
        return 'amazon'
    
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Amazon for products"""
        search_url = f"{self.BASE_URL}/s?k={quote_plus(query)}"
        soup = self._get_page(search_url)
        
        if not soup:
            return []
        
        products = []
        items = soup.select('[data-component-type="s-search-result"]')[:max_results]
        
        for item in items:
            try:
                # Extract product details
                title_elem = item.select_one('h2 a span')
                link_elem = item.select_one('h2 a')
                image_elem = item.select_one('img.s-image')
                price_elem = item.select_one('.a-price-whole')
                rating_elem = item.select_one('.a-icon-star-small span.a-icon-alt')
                
                if not title_elem or not link_elem:
                    continue
                
                product_url = urljoin(self.BASE_URL, link_elem['href'])
                asin = self._extract_asin(product_url)
                
                product = {
                    'name': self.clean_text(title_elem.text),
                    'url': product_url,
                    'source_product_id': asin,
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
        asin = self._extract_asin(product_url)
        if not asin:
            logger.error(f"Could not extract ASIN from {product_url}")
            return []
        
        reviews = []
        page = 1
        
        while len(reviews) < max_reviews:
            review_url = f"{self.BASE_URL}/product-reviews/{asin}/ref=cm_cr_arp_d_paging_btm_next_{page}?pageNumber={page}"
            soup = self._get_page(review_url)
            
            if not soup:
                break
            
            page_reviews = self._parse_reviews_page(soup)
            if not page_reviews:
                break
            
            reviews.extend(page_reviews)
            page += 1
            
            # Stop if we've reached max or no more reviews
            if len(reviews) >= max_reviews or len(page_reviews) < 10:
                break
        
        return reviews[:max_reviews]
    
    def _parse_reviews_page(self, soup) -> List[Dict]:
        """Parse reviews from a single page"""
        reviews = []
        review_divs = soup.select('[data-hook="review"]')
        
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
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL"""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float"""
        try:
            # Remove currency symbols and commas
            price = re.sub(r'[^\d.]', '', price_text)
            return float(price)
        except:
            return None
    
    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating from text like '4.5 out of 5 stars'"""
        try:
            match = re.search(r'([\d.]+)', rating_text)
            return float(match.group(1)) if match else None
        except:
            return None
    
    def _extract_title(self, soup) -> str:
        title = soup.select_one('#productTitle')
        return self.clean_text(title.text) if title else ""
    
    def _extract_description(self, soup) -> str:
        desc = soup.select_one('#feature-bullets')
        return self.clean_text(desc.text) if desc else ""
    
    def _extract_overall_rating(self, soup) -> Optional[float]:
        rating = soup.select_one('[data-hook="rating-out-of-text"]')
        if rating:
            return self._parse_rating(rating.text)
        return None
    
    def _extract_review_count(self, soup) -> int:
        count = soup.select_one('[data-hook="total-review-count"]')
        if count:
            try:
                return int(re.sub(r'\D', '', count.text))
            except:
                pass
        return 0
    
    def _extract_image(self, soup) -> Optional[str]:
        img = soup.select_one('#landingImage')
        return img['src'] if img else None
    
    def _extract_price(self, soup) -> Optional[float]:
        price = soup.select_one('.a-price-whole')
        return self._parse_price(price.text) if price else None
    
    def _extract_review_title(self, review_div) -> str:
        title = review_div.select_one('[data-hook="review-title"]')
        return self.clean_text(title.text) if title else ""
    
    def _extract_review_text(self, review_div) -> str:
        text = review_div.select_one('[data-hook="review-body"]')
        return self.clean_text(text.text) if text else ""
    
    def _extract_review_rating(self, review_div) -> float:
        rating = review_div.select_one('[data-hook="review-star-rating"]')
        if rating:
            return self._parse_rating(rating.text) or 0.0
        return 0.0
    
    def _extract_review_author(self, review_div) -> str:
        author = review_div.select_one('.a-profile-name')
        return self.clean_text(author.text) if author else "Anonymous"
    
    def _extract_review_date(self, review_div) -> Optional[datetime]:
        date = review_div.select_one('[data-hook="review-date"]')
        if date:
            date_text = date.text.replace('Reviewed in India on ', '')
            return self.parse_date(date_text)
        return None
    
    def _is_verified_purchase(self, review_div) -> bool:
        verified = review_div.select_one('[data-hook="avp-badge"]')
        return verified is not None
    
    def _extract_helpful_count(self, review_div) -> int:
        helpful = review_div.select_one('[data-hook="helpful-vote-statement"]')
        if helpful:
            try:
                match = re.search(r'(\d+)', helpful.text)
                return int(match.group(1)) if match else 0
            except:
                pass
        return 0