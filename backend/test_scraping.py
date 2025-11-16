"""
Comprehensive scraping test suite
Tests scraper functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
import time
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def test_amazon_search(scraper, query="laptop", max_results=5):
    """Test Amazon product search"""
    print_header("Test 1: Amazon Product Search")
    print_info(f"Searching for: '{query}' (max {max_results} results)")
    
    try:
        start_time = time.time()
        results = scraper.search_products(query, max_results=max_results)
        elapsed = time.time() - start_time
        
        if results:
            print_success(f"Found {len(results)} products in {elapsed:.2f}s")
            
            # Display first result
            if len(results) > 0:
                product = results[0]
                print(f"\n  Example product:")
                print(f"    Name: {product.get('name', 'N/A')[:60]}...")
                print(f"    Price: ₹{product.get('price', 'N/A')}")
                print(f"    Rating: {product.get('rating', 'N/A')} ⭐")
                print(f"    URL: {product.get('url', 'N/A')[:60]}...")
            
            return True, results
        else:
            print_error("No results found")
            return False, []
            
    except Exception as e:
        print_error(f"Search failed: {e}")
        return False, []

def test_amazon_product_details(scraper, url):
    """Test Amazon product details scraping"""
    print_header("Test 2: Amazon Product Details")
    print_info(f"Fetching details from: {url[:60]}...")
    
    try:
        start_time = time.time()
        details = scraper.scrape_product_details(url)
        elapsed = time.time() - start_time
        
        if details:
            print_success(f"Successfully scraped details in {elapsed:.2f}s")
            
            print(f"\n  Product Details:")
            print(f"    Name: {details.get('name', 'N/A')[:60]}...")
            print(f"    Rating: {details.get('rating', 'N/A')} ⭐")
            print(f"    Reviews: {details.get('review_count', 0)}")
            print(f"    Price: ₹{details.get('price', 'N/A')}")
            print(f"    Description: {details.get('description', 'N/A')[:80]}...")
            
            return True, details
        else:
            print_error("Failed to scrape product details")
            return False, None
            
    except Exception as e:
        print_error(f"Details scraping failed: {e}")
        return False, None

def test_amazon_reviews(scraper, url, max_reviews=10):
    """Test Amazon reviews scraping"""
    print_header("Test 3: Amazon Reviews Scraping")
    print_info(f"Fetching {max_reviews} reviews...")
    
    try:
        start_time = time.time()
        reviews = scraper.scrape_reviews(url, max_reviews=max_reviews)
        elapsed = time.time() - start_time
        
        if reviews:
            print_success(f"Scraped {len(reviews)} reviews in {elapsed:.2f}s")
            
            # Show sample review
            if len(reviews) > 0:
                review = reviews[0]
                print(f"\n  Sample Review:")
                print(f"    Rating: {review.get('rating', 'N/A')} ⭐")
                print(f"    Author: {review.get('author', 'N/A')}")
                print(f"    Verified: {'Yes' if review.get('verified') else 'No'}")
                print(f"    Text: {review.get('text', 'N/A')[:100]}...")
            
            # Statistics
            verified_count = sum(1 for r in reviews if r.get('verified'))
            avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews)
            
            print(f"\n  Statistics:")
            print(f"    Verified Reviews: {verified_count}/{len(reviews)}")
            print(f"    Average Rating: {avg_rating:.2f} ⭐")
            
            return True, reviews
        else:
            print_warning("No reviews found")
            return False, []
            
    except Exception as e:
        print_error(f"Review scraping failed: {e}")
        return False, []

def test_flipkart_search(scraper, query="laptop", max_results=5):
    """Test Flipkart product search"""
    print_header("Test 4: Flipkart Product Search")
    print_info(f"Searching for: '{query}' (max {max_results} results)")
    
    try:
        start_time = time.time()
        results = scraper.search_products(query, max_results=max_results)
        elapsed = time.time() - start_time
        
        if results:
            print_success(f"Found {len(results)} products in {elapsed:.2f}s")
            
            if len(results) > 0:
                product = results[0]
                print(f"\n  Example product:")
                print(f"    Name: {product.get('name', 'N/A')[:60]}...")
                print(f"    Price: ₹{product.get('price', 'N/A')}")
                print(f"    Rating: {product.get('rating', 'N/A')} ⭐")
            
            return True, results
        else:
            print_error("No results found")
            return False, []
            
    except Exception as e:
        print_error(f"Search failed: {e}")
        return False, []

def test_anti_blocking_measures(scraper):
    """Test anti-blocking measures"""
    print_header("Test 5: Anti-Blocking Measures")
    
    print_info("Testing user agent rotation...")
    user_agents = set()
    for _ in range(5):
        scraper.session.headers.update(scraper._get_random_headers())
        user_agents.add(scraper.session.headers.get('User-Agent'))
    
    if len(user_agents) > 1:
        print_success(f"User agent rotation working ({len(user_agents)} different agents)")
    else:
        print_warning("User agent not rotating")
    
    print_info("Testing rate limiting...")
    times = []
    for i in range(3):
        start = time.time()
        scraper._rate_limit()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Request {i+1}: Delayed {elapsed:.2f}s")
    
    if all(t >= 2 for t in times):
        print_success("Rate limiting working properly")
    else:
        print_warning("Rate limiting may not be effective")
    
    print_info("Testing session rotation...")
    initial_session_id = id(scraper.session)
    scraper.request_count = 25  # Trigger rotation
    scraper._rotate_session()
    new_session_id = id(scraper.session)
    
    if initial_session_id != new_session_id:
        print_success("Session rotation working")
    else:
        print_warning("Session not rotating")

def test_stress_test(scraper, num_requests=5):
    """Test scraper under load"""
    print_header("Test 6: Stress Test")
    print_info(f"Making {num_requests} sequential requests...")
    
    successful = 0
    blocked = 0
    errors = 0
    
    test_urls = [
        "https://www.amazon.in/",
        "https://www.amazon.in/s?k=laptop",
        "https://www.amazon.in/s?k=phone",
        "https://www.amazon.in/s?k=headphone",
        "https://www.amazon.in/s?k=watch",
    ]
    
    for i in range(num_requests):
        url = test_urls[i % len(test_urls)]
        try:
            print(f"  Request {i+1}/{num_requests}...", end=" ")
            soup = scraper._get_page(url)
            
            if soup:
                successful += 1
                print("✓")
            else:
                blocked += 1
                print("✗ (blocked)")
                
        except Exception as e:
            errors += 1
            print(f"✗ (error: {str(e)[:30]})")
    
    print(f"\n  Results:")
    print(f"    Successful: {successful}/{num_requests}")
    print(f"    Blocked: {blocked}/{num_requests}")
    print(f"    Errors: {errors}/{num_requests}")
    
    success_rate = (successful / num_requests) * 100
    
    if success_rate >= 80:
        print_success(f"Stress test passed ({success_rate:.0f}% success rate)")
        return True
    else:
        print_warning(f"Stress test marginal ({success_rate:.0f}% success rate)")
        return False

def main():
    """Run all tests"""
    print_header("SCRAPING TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize app and scrapers
    app = create_app('development')
    
    with app.app_context():
        amazon_scraper = AmazonScraper(app.config)
        flipkart_scraper = FlipkartScraper(app.config)
        
        results = {}
        
        # Test Amazon
        print_info("Testing Amazon scraper...")
        results['amazon_search'], search_results = test_amazon_search(amazon_scraper, max_results=3)
        
        if search_results:
            # Use first result for detailed tests
            test_url = search_results[0].get('url')
            if test_url:
                results['amazon_details'], details = test_amazon_product_details(amazon_scraper, test_url)
                results['amazon_reviews'], reviews = test_amazon_reviews(amazon_scraper, test_url, max_reviews=5)
        
        # Test Flipkart
        print_info("\nTesting Flipkart scraper...")
        results['flipkart_search'], _ = test_flipkart_search(flipkart_scraper, max_results=3)
        
        # Test anti-blocking
        test_anti_blocking_measures(amazon_scraper)
        
        # Stress test (optional - comment out if you want to be extra safe)
        print_warning("\nStress test will make multiple requests. Continue? (y/n)")
        if input().lower() == 'y':
            results['stress_test'] = test_stress_test(amazon_scraper, num_requests=5)
        
        # Summary
        print_header("TEST SUMMARY")
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\nTests passed: {passed}/{total}")
        
        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            color = Colors.GREEN if result else Colors.RED
            print(f"  {color}{status}{Colors.END} - {test_name}")
        
        print(f"\n{Colors.BOLD}Overall: {'✓ SUCCESS' if passed == total else '⚠ PARTIAL SUCCESS'}{Colors.END}")
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if passed == total:
            print(f"{Colors.GREEN}{'='*70}")
            print("All tests passed! Your scraper is working well.")
            print(f"{'='*70}{Colors.END}\n")
        else:
            print(f"{Colors.YELLOW}{'='*70}")
            print("Some tests failed. Check the errors above.")
            print("This may be due to website changes or blocking.")
            print(f"{'='*70}{Colors.END}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()