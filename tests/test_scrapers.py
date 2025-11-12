import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from backend.scrapers.amazon_scraper import AmazonScraper
from backend.config import TestingConfig

@pytest.fixture
def scraper():
    """Create a test scraper instance"""
    config = TestingConfig()
    return AmazonScraper(config)

@pytest.fixture
def mock_product_html():
    """Mock HTML for product page"""
    return """
    <html>
        <body>
            <div data-component-type="s-search-result">
                <h2>
                    <a href="/product/B08N5WRWNW">
                        <span>Sample Product Name</span>
                    </a>
                </h2>
                <img class="s-image" src="https://example.com/image.jpg" />
                <span class="a-price-whole">999</span>
                <span class="a-icon-alt">4.5 out of 5 stars</span>
            </div>
        </body>
    </html>
    """

@pytest.fixture
def mock_review_html():
    """Mock HTML for review page"""
    return """
    <html>
        <body>
            <div data-hook="review">
                <span data-hook="review-title">Great product!</span>
                <span data-hook="review-body">This is a great product. Highly recommend.</span>
                <i data-hook="review-star-rating">5.0 out of 5 stars</i>
                <span class="a-profile-name">John Doe</span>
                <span data-hook="review-date">Reviewed in India on January 1, 2024</span>
                <span data-hook="avp-badge">Verified Purchase</span>
                <span data-hook="helpful-vote-statement">5 people found this helpful</span>
            </div>
        </body>
    </html>
    """

class TestAmazonScraper:
    
    def test_get_source_name(self, scraper):
        """Test source name retrieval"""
        assert scraper.get_source_name() == 'amazon'
    
    def test_extract_asin(self, scraper):
        """Test ASIN extraction from URLs"""
        urls = [
            ('https://www.amazon.in/dp/B08N5WRWNW', 'B08N5WRWNW'),
            ('https://www.amazon.in/product/B08N5WRWNW', 'B08N5WRWNW'),
            ('https://www.amazon.in/gp/product/B08N5WRWNW', 'B08N5WRWNW'),
        ]
        
        for url, expected_asin in urls:
            assert scraper._extract_asin(url) == expected_asin
    
    def test_parse_price(self, scraper):
        """Test price parsing"""
        assert scraper._parse_price('999') == 999.0
        assert scraper._parse_price('1,999') == 1999.0
        assert scraper._parse_price('₹999.99') == 999.99
        assert scraper._parse_price('invalid') is None
    
    def test_parse_rating(self, scraper):
        """Test rating parsing"""
        assert scraper._parse_rating('4.5 out of 5 stars') == 4.5
        assert scraper._parse_rating('5.0 out of 5 stars') == 5.0
        assert scraper._parse_rating('invalid') is None
    
    def test_normalize_rating(self, scraper):
        """Test rating normalization"""
        assert scraper.normalize_rating(5.0, 5.0) == 5.0
        assert scraper.normalize_rating(10.0, 10.0) == 5.0
        assert scraper.normalize_rating(4.0, 10.0) == 2.0
    
    def test_clean_text(self, scraper):
        """Test text cleaning"""
        assert scraper.clean_text('  Hello   World  ') == 'Hello World'
        assert scraper.clean_text(None) == ''
        assert scraper.clean_text('Multiple\n\nLines') == 'Multiple Lines'
    
    @patch('backend.scrapers.amazon_scraper.AmazonScraper._get_page')
    def test_search_products(self, mock_get_page, scraper, mock_product_html):
        """Test product search"""
        mock_get_page.return_value = BeautifulSoup(mock_product_html, 'html.parser')
        
        results = scraper.search_products('test product', max_results=10)
        
        assert len(results) == 1
        assert results[0]['name'] == 'Sample Product Name'
        assert results[0]['source_product_id'] == 'B08N5WRWNW'
        assert results[0]['price'] == 999.0
    
    @patch('backend.scrapers.amazon_scraper.AmazonScraper._get_page')
    def test_scrape_reviews(self, mock_get_page, scraper, mock_review_html):
        """Test review scraping"""
        mock_get_page.return_value = BeautifulSoup(mock_review_html, 'html.parser')
        
        reviews = scraper.scrape_reviews('https://www.amazon.in/dp/B08N5WRWNW', max_reviews=10)
        
        assert len(reviews) == 1
        review = reviews[0]
        assert review['title'] == 'Great product!'
        assert 'great product' in review['text'].lower()
        assert review['rating'] == 5.0
        assert review['author'] == 'John Doe'
        assert review['verified'] is True
        assert review['helpful_count'] == 5
    
    @patch('backend.scrapers.amazon_scraper.AmazonScraper._get_page')
    def test_scrape_reviews_pagination(self, mock_get_page, scraper):
        """Test review scraping with pagination"""
        # First page returns reviews, second returns None (end of pagination)
        mock_get_page.side_effect = [
            BeautifulSoup('<div data-hook="review"></div>', 'html.parser'),
            None
        ]
        
        reviews = scraper.scrape_reviews('https://www.amazon.in/dp/B08N5WRWNW', max_reviews=100)
        
        # Should stop when _get_page returns None
        assert mock_get_page.call_count == 2
    
    def test_get_page_retry_logic(self, scraper):
        """Test retry logic for failed requests"""
        with patch('backend.scrapers.amazon_scraper.requests.Session.get') as mock_get:
            # Simulate network errors
            mock_get.side_effect = Exception('Network error')
            
            result = scraper._get_page('https://example.com', retries=3)
            
            assert result is None
            assert mock_get.call_count == 3

@pytest.fixture
def app():
    """Create test Flask app"""
    from backend.app import create_app
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

class TestScraperIntegration:
    """Integration tests for scrapers"""
    
    def test_scraper_initialization(self, scraper):
        """Test scraper is properly initialized"""
        assert scraper.session is not None
        assert scraper.delay > 0
        assert 'User-Agent' in scraper.session.headers
    
    @patch('backend.scrapers.amazon_scraper.time.sleep')
    @patch('backend.scrapers.amazon_scraper.requests.Session.get')
    def test_rate_limiting(self, mock_get, mock_sleep, scraper):
        """Test that rate limiting is applied"""
        mock_response = Mock()
        mock_response.content = b'<html></html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        scraper._get_page('https://example.com')
        
        # Verify sleep was called for rate limiting
        mock_sleep.assert_called()