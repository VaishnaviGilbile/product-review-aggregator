from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_caching import Cache
from config import config
from models import db, Product, Review, Source, ProductSource, ProductKeyword
from services.sentiment_service import SentimentService
from services.aggregation_service import AggregationService
from services.search_service import SearchService

# Try to import Selenium scrapers, fallback to regular scrapers
try:
    from scrapers.selenium_scraper import SeleniumAmazonScraper, SeleniumFlipkartScraper
    SELENIUM_AVAILABLE = True
    print("✅ Selenium scrapers loaded (anti-CAPTCHA enabled)")
except ImportError:
    from scrapers.amazon_scraper import AmazonScraper
    from scrapers.flipkart_scraper import FlipkartScraper
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available, using basic scrapers")

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__, 
                template_folder='../frontend/templates',
                static_folder='../frontend/static')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Initialize cache
    try:
        cache = Cache(app)
        logger.info(f"Cache initialized: {app.config.get('CACHE_TYPE')}")
    except Exception as e:
        logger.warning(f"Cache initialization failed, using SimpleCache: {e}")
        app.config['CACHE_TYPE'] = 'simple'
        cache = Cache(app)
    
    # Initialize services
    sentiment_service = SentimentService(use_vader=True)
    aggregation_service = AggregationService(db, sentiment_service)
    search_service = SearchService(db)
    
    # Initialize scrapers (Selenium if available, otherwise basic)
    if SELENIUM_AVAILABLE:
        scrapers = {
            'amazon': SeleniumAmazonScraper(app.config),
            'flipkart': SeleniumFlipkartScraper(app.config)
        }
        logger.info("🚀 Using Selenium-based scrapers (CAPTCHA bypass)")
    else:
        scrapers = {
            'amazon': AmazonScraper(app.config),
            'flipkart': FlipkartScraper(app.config)
        }
        logger.info("📡 Using basic HTTP scrapers")
    
    # Create tables and initialize sources
    with app.app_context():
        db.create_all()
        for source_name, scraper in scrapers.items():
            source = Source.query.filter_by(name=source_name).first()
            if not source:
                base_url = 'https://www.amazon.in' if source_name == 'amazon' else 'https://www.flipkart.com'
                source = Source(
                    name=source_name,
                    base_url=base_url,
                    is_active=True
                )
                db.session.add(source)
        db.session.commit()
        logger.info("Database initialized successfully")
    
    def clean_product_url(url: str) -> str:
        """Clean product URL by removing tracking parameters"""
        import re
        
        url_lower = url.lower()
        
        # Clean Amazon URL
        if 'amazon' in url_lower:
            match = re.search(r'/dp/([A-Z0-9]{10})', url)
            if match:
                asin = match.group(1)
                if 'amazon.in' in url_lower:
                    return f"https://www.amazon.in/dp/{asin}"
                else:
                    return f"https://www.amazon.com/dp/{asin}"
        
        # Clean Flipkart URL
        elif 'flipkart' in url_lower:
            if '?' in url:
                url = url.split('?')[0]
            return url
        
        return url
    
    def detect_source_from_url(url: str):
        """Detect source from URL"""
        url_lower = url.lower()
        if 'amazon.in' in url_lower or 'amazon.com' in url_lower:
            return 'amazon'
        elif 'flipkart.com' in url_lower:
            return 'flipkart'
        return None
    
    # ==================== ROUTES ====================
    
    @app.route('/')
    def index():
        """Render main page"""
        return render_template('index.html')
    
    @app.route('/product/<int:product_id>')
    def product_page(product_id):
        """Render product detail page"""
        return render_template('product.html', product_id=product_id)
    
    @app.route('/compare')
    def compare_page():
        """Render comparison page"""
        return render_template('compare.html')
    
    # ==================== API ENDPOINTS ====================
    
    @app.route('/api/add-product', methods=['POST'])
    def add_product_from_url():
        """Add a product by URL and scrape reviews"""
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        # Clean the URL
        original_url = url
        url = clean_product_url(url)
        if url != original_url:
            logger.info(f"🧹 Cleaned URL: {original_url[:50]}... → {url}")
        
        # Detect source
        source_name = detect_source_from_url(url)
        if not source_name:
            return jsonify({
                'success': False,
                'error': 'Invalid URL. Please provide an Amazon.in or Flipkart.com product URL'
            }), 400
        
        if source_name not in scrapers:
            return jsonify({'success': False, 'error': f'Scraper not available for {source_name}'}), 400
        
        scraper = scrapers[source_name]
        
        try:
            logger.info(f"🎯 Processing URL from {source_name}: {url}")
            
            # Step 1: Scrape product details
            logger.info("📦 Step 1: Scraping product details...")
            details = scraper.scrape_product_details(url)
            
            if not details or not details.get('name'):
                return jsonify({
                    'success': False,
                    'error': 'Could not extract product details. The page may be blocked or unavailable.'
                }), 400
            
            # Extract source product ID
            if source_name == 'amazon':
                source_product_id = scraper._extract_asin(url)
            else:
                source_product_id = scraper._extract_product_id(url)
            
            # Check if product exists
            existing_product = None
            if source_product_id:
                existing_product = search_service.get_product_by_source_id(source_name, source_product_id)
            
            if existing_product:
                logger.info(f"♻️ Product already exists: {existing_product.name}")
                return jsonify({
                    'success': True,
                    'message': 'Product already exists in database',
                    'product_id': existing_product.id,
                    'product': existing_product.to_dict(),
                    'already_exists': True
                })
            
            # Step 2: Create product
            logger.info("💾 Step 2: Creating product in database...")
            product = search_service.create_or_update_product(
                name=details.get('name'),
                source_name=source_name,
                source_url=url,
                source_product_id=source_product_id,
                image_url=details.get('image_url'),
                price=details.get('price'),
                description=details.get('description'),
                category=details.get('category')
            )
            
            # Step 3: Scrape reviews
            logger.info("📝 Step 3: Scraping reviews...")
            reviews_data = scraper.scrape_reviews(
                url,
                max_reviews=app.config['MAX_REVIEWS_PER_PRODUCT']
            )
            
            logger.info(f"✅ Found {len(reviews_data)} reviews")
            
            # Get product source
            source = Source.query.filter_by(name=source_name).first()
            product_source = ProductSource.query.filter_by(
                product_id=product.id,
                source_id=source.id
            ).first()
            
            # Step 4: Process and save reviews
            logger.info("🧠 Step 4: Analyzing sentiment and saving reviews...")
            saved_count = 0
            for review_data in reviews_data:
                sentiment = sentiment_service.analyze_text(review_data['text'])
                
                review = Review(
                    product_id=product.id,
                    source_id=product_source.source_id,
                    title=review_data.get('title'),
                    text=review_data['text'],
                    rating=review_data['rating'],
                    author=review_data.get('author'),
                    is_verified=review_data.get('verified', False),
                    review_date=review_data.get('date'),
                    helpful_count=review_data.get('helpful_count', 0),
                    sentiment_score=sentiment['score'],
                    sentiment_label=sentiment['label'],
                    sentiment_confidence=sentiment['confidence']
                )
                db.session.add(review)
                saved_count += 1
            
            db.session.commit()
            
            # Step 5: Update aggregates
            logger.info("📊 Step 5: Calculating aggregates...")
            aggregation_service.update_product_aggregates(product.id)
            
            logger.info(f"🎉 Successfully added product with {saved_count} reviews")
            
            # Close Selenium browser if used
            if SELENIUM_AVAILABLE:
                scraper.close()
            
            return jsonify({
                'success': True,
                'message': f'Product added successfully with {saved_count} reviews',
                'product_id': product.id,
                'product': product.to_dict(),
                'reviews_count': saved_count
            })
            
        except Exception as e:
            logger.error(f"❌ Error adding product: {str(e)}", exc_info=True)
            db.session.rollback()
            
            # Close Selenium browser on error
            if SELENIUM_AVAILABLE:
                try:
                    scraper.close()
                except:
                    pass
            
            return jsonify({
                'success': False,
                'error': f'Failed to add product: {str(e)}'
            }), 500
    
    @app.route('/api/products', methods=['GET'])
    def list_products():
        """List all products"""
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        try:
            products = Product.query.order_by(
                Product.updated_at.desc()
            ).limit(limit).offset(offset).all()
            
            total = Product.query.count()
            
            return jsonify({
                'success': True,
                'total': total,
                'limit': limit,
                'offset': offset,
                'products': [p.to_dict() for p in products]
            })
        except Exception as e:
            logger.error(f"Error listing products: {e}")
            return jsonify({'success': False, 'error': 'Failed to list products'}), 500
    
    @app.route('/api/product/<int:product_id>', methods=['GET'])
    def get_product(product_id):
        """Get product details"""
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'success': True,
            'product': product.to_dict()
        })
    
    @app.route('/api/product/<int:product_id>/reviews', methods=['GET'])
    def get_product_reviews(product_id):
        """Get product reviews with filtering"""
        product = Product.query.get_or_404(product_id)
        
        sentiment_filter = request.args.get('sentiment')
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        query = Review.query.filter_by(product_id=product_id)
        
        if sentiment_filter in ['positive', 'neutral', 'negative']:
            query = query.filter_by(sentiment_label=sentiment_filter)
        
        total = query.count()
        reviews = query.order_by(Review.review_date.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'total': total,
            'limit': limit,
            'offset': offset,
            'reviews': [r.to_dict() for r in reviews]
        })
    
    @app.route('/api/product/<int:product_id>/aggregate', methods=['GET'])
    def get_aggregate_data(product_id):
        """Get aggregated analysis"""
        product = Product.query.get_or_404(product_id)
        
        try:
            aggregate = aggregation_service.get_product_aggregate(product_id)
            return jsonify({
                'success': True,
                'aggregate': aggregate
            })
        except Exception as e:
            logger.error(f"Aggregation error: {e}")
            return jsonify({'success': False, 'error': 'Aggregation failed'}), 500
    
    @app.route('/api/compare', methods=['GET'])
    def compare_products():
        """Compare multiple products"""
        ids_str = request.args.get('ids', '')
        try:
            product_ids = [int(x) for x in ids_str.split(',') if x.strip()]
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid product IDs'}), 400
        
        if not product_ids or len(product_ids) > 5:
            return jsonify({'success': False, 'error': 'Provide 1-5 product IDs'}), 400
        
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        
        comparison = []
        for product in products:
            aggregate = aggregation_service.get_product_aggregate(product.id)
            comparison.append({
                'product': product.to_dict(),
                'aggregate': aggregate
            })
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
    
    @app.route('/health')
    def health_check():
        """Health check"""
        try:
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'selenium': SELENIUM_AVAILABLE
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    port = int(os.environ.get('PORT', 5001))
    print(f"\n{'='*60}")
    print(f"🚀 Product Review Aggregator Server Starting")
    print(f"{'='*60}")
    print(f"📡 Server: http://localhost:{port}")
    print(f"💾 Database: SQLite (reviews.db)")
    print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"🤖 Selenium: {'✅ Enabled (CAPTCHA bypass)' if SELENIUM_AVAILABLE else '❌ Disabled'}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=True)