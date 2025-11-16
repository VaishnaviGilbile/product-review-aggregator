from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_caching import Cache
from config import config
from models import db, Product, Review, Source, ProductSource, ProductKeyword
from services.sentiment_service import SentimentService
from services.aggregation_service import AggregationService
from services.search_service import SearchService
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
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
    
    # Initialize cache with fallback to SimpleCache
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
    
    # Initialize scrapers
    scrapers = {
        'amazon': AmazonScraper(app.config),
        'flipkart': FlipkartScraper(app.config)
    }
    
    # Create tables and initialize sources
    with app.app_context():
        db.create_all()
        for source_name, scraper in scrapers.items():
            source = Source.query.filter_by(name=source_name).first()
            if not source:
                source = Source(
                    name=source_name,
                    base_url=scraper.BASE_URL,
                    is_active=True
                )
                db.session.add(source)
        db.session.commit()
    
    # Routes
    
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
    
    # API Routes
    
    @app.route('/api/search', methods=['GET'])
    def search_products():
        """
        Search for products
        Query params: q (query string), source (optional)
        """
        query = request.args.get('q', '').strip()
        source_name = request.args.get('source', 'amazon')
        
        if not query:
            return jsonify({'error': 'Query parameter q is required'}), 400
        
        if source_name not in scrapers:
            return jsonify({'error': f'Invalid source: {source_name}'}), 400
        
        try:
            # First, search local database
            local_products = search_service.search_products(query)
            
            # If not enough results, scrape
            if len(local_products) < 5:
                logger.info(f"Fetching fresh data for '{query}' from {source_name}")
                
                scraper = scrapers[source_name]
                scraped_products = scraper.search_products(query, max_results=10)
                
                # Save to database
                for item in scraped_products:
                    try:
                        search_service.create_or_update_product(
                            name=item['name'],
                            source_name=source_name,
                            source_url=item['url'],
                            source_product_id=item.get('source_product_id'),
                            image_url=item.get('image_url'),
                            price=item.get('price'),
                            description=item.get('description'),
                            category=item.get('category')
                        )
                    except Exception as e:
                        logger.error(f"Failed to save product: {e}")
                        continue
                
                # Search again
                local_products = search_service.search_products(query)
            
            return jsonify({
                'success': True,
                'query': query,
                'results': [p.to_dict() for p in local_products],
                'source': source_name
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return jsonify({'error': 'Search failed'}), 500
    
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
        """
        Get reviews for a product
        Query params: sentiment (optional), limit, offset
        """
        product = Product.query.get_or_404(product_id)
        
        sentiment_filter = request.args.get('sentiment')
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Review.query.filter_by(product_id=product_id)
        
        if sentiment_filter in ['positive', 'neutral', 'negative']:
            query = query.filter_by(sentiment_label=sentiment_filter)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
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
        """Get aggregated analysis for product"""
        product = Product.query.get_or_404(product_id)
        
        try:
            aggregate = aggregation_service.get_product_aggregate(product_id)
            return jsonify({
                'success': True,
                'aggregate': aggregate
            })
        except Exception as e:
            logger.error(f"Aggregation error: {e}")
            return jsonify({'error': 'Aggregation failed'}), 500
    
    @app.route('/api/product/<int:product_id>/scrape', methods=['POST'])
    def scrape_product_reviews(product_id):
        """
        Trigger scraping for a product
        """
        product = Product.query.get_or_404(product_id)
        
        # Get product source
        product_source = ProductSource.query.filter_by(product_id=product_id).first()
        if not product_source:
            return jsonify({'error': 'No source URL for this product'}), 400
        
        source_name = product_source.source.name
        if source_name not in scrapers:
            return jsonify({'error': 'Scraper not available'}), 400
        
        try:
            scraper = scrapers[source_name]
            
            # Scrape product details first
            logger.info(f"Scraping product details for {product.name}")
            details = scraper.scrape_product_details(product_source.source_url)
            
            # Update product with fresh details if available
            if details:
                if details.get('description'):
                    product.description = details.get('description')
                if details.get('image_url'):
                    product.image_url = details.get('image_url')
                if details.get('category'):
                    product.category = details.get('category')
                db.session.commit()
                logger.info("Updated product details")
            
            # Scrape reviews
            logger.info(f"Scraping reviews (max {app.config['MAX_REVIEWS_PER_PRODUCT']})")
            reviews_data = scraper.scrape_reviews(
                product_source.source_url,
                max_reviews=app.config['MAX_REVIEWS_PER_PRODUCT']
            )
            
            # Process and save reviews
            saved_count = 0
            for review_data in reviews_data:
                # Analyze sentiment
                sentiment = sentiment_service.analyze_text(review_data['text'])
                
                # Check if review already exists
                existing = Review.query.filter_by(
                    product_id=product_id,
                    source_id=product_source.source_id,
                    text=review_data['text']
                ).first()
                
                if not existing:
                    review = Review(
                        product_id=product_id,
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
            
            # Update aggregates
            aggregation_service.update_product_aggregates(product_id)
            
            logger.info(f"Successfully scraped {saved_count} new reviews")
            
            return jsonify({
                'success': True,
                'message': f'Scraped {len(reviews_data)} reviews ({saved_count} new)',
                'reviews_count': len(reviews_data),
                'new_reviews': saved_count
            })
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/compare', methods=['GET'])
    def compare_products():
        """
        Compare multiple products
        Query params: ids (comma-separated product IDs)
        """
        ids_str = request.args.get('ids', '')
        try:
            product_ids = [int(x) for x in ids_str.split(',') if x.strip()]
        except ValueError:
            return jsonify({'error': 'Invalid product IDs'}), 400
        
        if not product_ids or len(product_ids) > 5:
            return jsonify({'error': 'Provide 1-5 product IDs'}), 400
        
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
        """Health check endpoint"""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'database': 'connected'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    # Error handlers
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)