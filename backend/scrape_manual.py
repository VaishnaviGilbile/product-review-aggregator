"""
Manual scraping script for real Amazon/Flipkart products
Usage: python scrape_manual.py

This script allows you to:
1. Scrape product details from a URL
2. Scrape and analyze reviews
3. Save everything to the database
4. View sentiment analysis results
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Product, Review, Source, ProductSource
from services.sentiment_service import SentimentService
from services.search_service import SearchService
from services.aggregation_service import AggregationService
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
import time

def print_banner():
    """Print welcome banner"""
    print("\n" + "="*70)
    print("           PRODUCT REVIEW SCRAPER - Manual Mode")
    print("="*70)
    print("\nScrape real product data from Amazon and Flipkart")
    print("Analyze sentiment and save to database\n")

def scrape_product_from_url(url: str):
    """Scrape a product from Amazon or Flipkart URL"""
    app = create_app('development')
    
    with app.app_context():
        # Determine source from URL
        if 'amazon' in url.lower():
            source_name = 'amazon'
            scraper = AmazonScraper(app.config)
            print(f"📦 Source: Amazon India")
        elif 'flipkart' in url.lower():
            source_name = 'flipkart'
            scraper = FlipkartScraper(app.config)
            print(f"📦 Source: Flipkart India")
        else:
            print("❌ Error: URL must be from Amazon.in or Flipkart.com")
            return False
        
        print(f"🔗 URL: {url}")
        print("\n" + "-"*70)
        
        # Get source from database
        source = Source.query.filter_by(name=source_name).first()
        if not source:
            print(f"❌ Error: Source '{source_name}' not found in database")
            print("   Please run: python init_db.py")
            return False
        
        # Initialize services
        sentiment_service = SentimentService(use_vader=True)
        search_service = SearchService(db)
        aggregation_service = AggregationService(db, sentiment_service)
        
        # Step 1: Scrape product details
        print("\n🔍 Step 1/4: Scraping product details...")
        try:
            product_details = scraper.scrape_product_details(url)
            
            if not product_details.get('name'):
                print("❌ Failed to extract product name. The page structure may have changed.")
                return False
            
            print(f"✓ Product Name: {product_details.get('name', 'Unknown')}")
            print(f"  Rating: {product_details.get('rating', 'N/A')} ⭐")
            print(f"  Total Reviews: {product_details.get('review_count', 0)}")
            print(f"  Price: ₹{product_details.get('price', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Failed to scrape product details: {e}")
            print("   The website structure may have changed or you may be blocked.")
            return False
        
        # Step 2: Save product to database
        print("\n💾 Step 2/4: Saving product to database...")
        try:
            product_id = scraper.extract_product_id(url)
            
            # Check if product already exists
            existing_product = search_service.get_product_by_source_id(source_name, product_id) if product_id else None
            
            if existing_product:
                print(f"ℹ️  Product already exists in database (ID: {existing_product.id})")
                product = existing_product
            else:
                product = search_service.create_or_update_product(
                    name=product_details.get('name', 'Unknown Product'),
                    source_name=source_name,
                    source_url=url,
                    source_product_id=product_id,
                    image_url=product_details.get('image_url'),
                    description=product_details.get('description'),
                    price=product_details.get('price')
                )
                print(f"✓ Product saved successfully (ID: {product.id})")
                
        except Exception as e:
            print(f"❌ Failed to save product: {e}")
            return False
        
        # Step 3: Scrape reviews
        max_reviews = app.config['MAX_REVIEWS_PER_PRODUCT']
        print(f"\n💬 Step 3/4: Scraping reviews (max {max_reviews})...")
        print("   This may take 1-2 minutes depending on review count...")
        
        try:
            start_time = time.time()
            reviews_data = scraper.scrape_reviews(url, max_reviews)
            elapsed_time = time.time() - start_time
            
            if not reviews_data:
                print("⚠️  No reviews found. The product may not have reviews yet.")
                return True  # Still consider it a success
            
            print(f"✓ Scraped {len(reviews_data)} reviews in {elapsed_time:.1f} seconds")
            
        except Exception as e:
            print(f"❌ Failed to scrape reviews: {e}")
            print("   You may have been rate-limited. Try again in a few minutes.")
            return False
        
        # Step 4: Process and save reviews with sentiment analysis
        print(f"\n🧠 Step 4/4: Analyzing sentiment and saving reviews...")
        
        saved_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, review_data in enumerate(reviews_data, 1):
            try:
                # Analyze sentiment
                sentiment = sentiment_service.analyze_text(review_data['text'])
                
                # Check if review already exists (avoid duplicates)
                existing = Review.query.filter_by(
                    product_id=product.id,
                    source_id=source.id,
                    text=review_data['text']
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create new review
                review = Review(
                    product_id=product.id,
                    source_id=source.id,
                    title=review_data.get('title', ''),
                    text=review_data['text'],
                    rating=review_data['rating'],
                    author=review_data.get('author', 'Anonymous'),
                    is_verified=review_data.get('verified', False),
                    review_date=review_data.get('date'),
                    helpful_count=review_data.get('helpful_count', 0),
                    sentiment_score=sentiment['score'],
                    sentiment_label=sentiment['label'],
                    sentiment_confidence=sentiment['confidence']
                )
                db.session.add(review)
                saved_count += 1
                
                # Show progress every 10 reviews
                if i % 10 == 0:
                    print(f"   Processed {i}/{len(reviews_data)} reviews...")
                
            except Exception as e:
                error_count += 1
                print(f"   ⚠️ Error processing review {i}: {e}")
                continue
        
        # Commit all reviews to database
        try:
            db.session.commit()
            print(f"\n✓ Successfully saved {saved_count} new reviews")
            if skipped_count > 0:
                print(f"  ℹ️  Skipped {skipped_count} duplicate reviews")
            if error_count > 0:
                print(f"  ⚠️  {error_count} reviews had errors")
        except Exception as e:
            print(f"❌ Failed to commit reviews to database: {e}")
            db.session.rollback()
            return False
        
        # Step 5: Calculate aggregates
        print("\n📊 Calculating sentiment aggregates...")
        try:
            aggregation_service.update_product_aggregates(product.id)
            print("✓ Aggregates calculated successfully")
        except Exception as e:
            print(f"⚠️  Warning: Failed to calculate aggregates: {e}")
        
        # Display summary
        product = Product.query.get(product.id)
        print("\n" + "="*70)
        print("                          SUMMARY")
        print("="*70)
        print(f"\n📦 Product: {product.name}")
        print(f"🔢 Total Reviews: {product.total_reviews}")
        print(f"⭐ Average Rating: {product.avg_rating:.2f}/5.0")
        print(f"\n📊 Sentiment Distribution:")
        print(f"   😊 Positive: {product.sentiment_positive:.1f}%")
        print(f"   😐 Neutral:  {product.sentiment_neutral:.1f}%")
        print(f"   😞 Negative: {product.sentiment_negative:.1f}%")
        
        # Show top pros and cons if available
        pros = ProductKeyword.query.filter_by(
            product_id=product.id, 
            keyword_type='pro'
        ).order_by(ProductKeyword.tfidf_score.desc()).limit(3).all()
        
        cons = ProductKeyword.query.filter_by(
            product_id=product.id, 
            keyword_type='con'
        ).order_by(ProductKeyword.tfidf_score.desc()).limit(3).all()
        
        if pros:
            print(f"\n👍 Top Pros:")
            for pro in pros:
                print(f"   • {pro.keyword}")
        
        if cons:
            print(f"\n👎 Top Cons:")
            for con in cons:
                print(f"   • {con.keyword}")
        
        print(f"\n🌐 View in browser:")
        print(f"   http://localhost:5001/product/{product.id}")
        print("\n" + "="*70 + "\n")
        
        return True

def show_examples():
    """Show example URLs"""
    print("📝 Example URLs:\n")
    print("Amazon:")
    print("  https://www.amazon.in/dp/B0BDJ3SRNN")
    print("  https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY\n")
    print("Flipkart:")
    print("  https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm123456789")
    print("  https://www.flipkart.com/samsung-galaxy-s23/p/itm987654321\n")

def main():
    """Main function"""
    print_banner()
    
    # Check if app is running
    print("⚠️  Make sure the Flask app is NOT running (it will lock the database)")
    print("   If running, press Ctrl+C in that terminal first.\n")
    
    while True:
        print("-"*70)
        print("\nOptions:")
        print("  1. Scrape product from URL")
        print("  2. Show example URLs")
        print("  3. Quit")
        print()
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            print()
            url = input("Enter product URL: ").strip()
            
            if not url:
                print("❌ No URL provided\n")
                continue
            
            if not url.startswith('http'):
                print("❌ Invalid URL. Must start with http:// or https://\n")
                continue
            
            print()
            success = scrape_product_from_url(url)
            
            if success:
                print("✅ Scraping completed successfully!\n")
            else:
                print("❌ Scraping failed. Please check the errors above.\n")
        
        elif choice == '2':
            print()
            show_examples()
        
        elif choice == '3':
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)