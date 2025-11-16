"""
Real-time scraping monitor
Shows live statistics and detects blocking
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from scrapers.amazon_scraper import AmazonScraper
import time
from datetime import datetime
import json

class ScrapingMonitor:
    """Monitor scraping activity and detect issues"""
    
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'blocked_requests': 0,
            'total_time': 0,
            'avg_delay': 0,
            'session_rotations': 0,
            'user_agents_used': set(),
            'start_time': time.time()
        }
    
    def log_request(self, success=True, blocked=False, delay=0, user_agent=None):
        """Log a request"""
        self.stats['total_requests'] += 1
        
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
        
        if blocked:
            self.stats['blocked_requests'] += 1
        
        self.stats['total_time'] += delay
        
        if user_agent:
            self.stats['user_agents_used'].add(user_agent)
        
        if self.stats['total_requests'] > 0:
            self.stats['avg_delay'] = self.stats['total_time'] / self.stats['total_requests']
    
    def get_success_rate(self):
        """Calculate success rate"""
        if self.stats['total_requests'] == 0:
            return 0
        return (self.stats['successful_requests'] / self.stats['total_requests']) * 100
    
    def get_blocking_rate(self):
        """Calculate blocking rate"""
        if self.stats['total_requests'] == 0:
            return 0
        return (self.stats['blocked_requests'] / self.stats['total_requests']) * 100
    
    def print_stats(self):
        """Print current statistics"""
        elapsed = time.time() - self.stats['start_time']
        success_rate = self.get_success_rate()
        blocking_rate = self.get_blocking_rate()
        
        print("\n" + "="*70)
        print(f"{'SCRAPING STATISTICS':^70}")
        print("="*70)
        print(f"Runtime: {elapsed:.1f}s")
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful: {self.stats['successful_requests']} ({success_rate:.1f}%)")
        print(f"Failed: {self.stats['failed_requests']}")
        print(f"Blocked: {self.stats['blocked_requests']} ({blocking_rate:.1f}%)")
        print(f"Average Delay: {self.stats['avg_delay']:.2f}s")
        print(f"User Agents Used: {len(self.stats['user_agents_used'])}")
        print("="*70 + "\n")
        
        # Health assessment
        if blocking_rate > 20:
            print("⚠️  WARNING: High blocking rate detected!")
            print("   Consider increasing delays or rotating IPs\n")
        elif blocking_rate > 10:
            print("⚠️  CAUTION: Moderate blocking detected")
            print("   Monitor closely\n")
        elif success_rate >= 90:
            print("✓ HEALTHY: Scraper operating normally\n")
    
    def save_report(self, filename='scraping_report.json'):
        """Save report to file"""
        report = self.stats.copy()
        report['user_agents_used'] = list(report['user_agents_used'])
        report['success_rate'] = self.get_success_rate()
        report['blocking_rate'] = self.get_blocking_rate()
        report['timestamp'] = datetime.now().isoformat()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to: {filename}")

def interactive_monitor():
    """Interactive monitoring session"""
    print("="*70)
    print("SCRAPING MONITOR - Interactive Mode")
    print("="*70)
    print("\nThis tool monitors scraping activity in real-time")
    print("and helps detect blocking issues.\n")
    
    app = create_app('development')
    monitor = ScrapingMonitor()
    
    with app.app_context():
        scraper = AmazonScraper(app.config)
        
        # Patch scraper to log requests
        original_get_page = scraper._get_page
        
        def monitored_get_page(url, retries=3):
            start = time.time()
            user_agent = scraper.session.headers.get('User-Agent')
            
            result = original_get_page(url, retries)
            
            delay = time.time() - start
            success = result is not None
            blocked = not success  # Simplified
            
            monitor.log_request(success, blocked, delay, user_agent)
            
            return result
        
        scraper._get_page = monitored_get_page
        
        print("Commands:")
        print("  search [query] - Search for products")
        print("  details [url]  - Get product details")
        print("  reviews [url]  - Get reviews")
        print("  stats          - Show statistics")
        print("  report         - Save report")
        print("  quit           - Exit\n")
        
        while True:
            try:
                command = input("scraping-monitor> ").strip().split(maxsplit=1)
                
                if not command:
                    continue
                
                action = command[0].lower()
                
                if action == 'quit':
                    print("\nExiting monitor...")
                    monitor.print_stats()
                    monitor.save_report()
                    break
                
                elif action == 'search':
                    if len(command) < 2:
                        print("Usage: search [query]")
                        continue
                    
                    query = command[1]
                    print(f"\nSearching for: {query}")
                    
                    results = scraper.search_products(query, max_results=5)
                    print(f"Found {len(results)} products")
                    
                    for i, product in enumerate(results, 1):
                        print(f"  {i}. {product.get('name', 'N/A')[:60]}...")
                
                elif action == 'details':
                    if len(command) < 2:
                        print("Usage: details [url]")
                        continue
                    
                    url = command[1]
                    print(f"\nFetching details...")
                    
                    details = scraper.scrape_product_details(url)
                    if details:
                        print(f"Name: {details.get('name', 'N/A')}")
                        print(f"Rating: {details.get('rating', 'N/A')}")
                        print(f"Price: ₹{details.get('price', 'N/A')}")
                
                elif action == 'reviews':
                    if len(command) < 2:
                        print("Usage: reviews [url]")
                        continue
                    
                    url = command[1]
                    print(f"\nFetching reviews...")
                    
                    reviews = scraper.scrape_reviews(url, max_reviews=10)
                    print(f"Found {len(reviews)} reviews")
                
                elif action == 'stats':
                    monitor.print_stats()
                
                elif action == 'report':
                    monitor.save_report()
                
                else:
                    print(f"Unknown command: {action}")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Showing stats...")
                monitor.print_stats()
                break
            
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    try:
        interactive_monitor()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()