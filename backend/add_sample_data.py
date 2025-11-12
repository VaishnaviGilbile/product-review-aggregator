"""Add sample data for testing without scraping"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Product, Review, Source, ProductSource
from services.sentiment_service import SentimentService

def add_sample_data():
    """Add sample products and reviews"""
    app = create_app('development')
    sentiment_service = SentimentService(use_vader=True)
    
    with app.app_context():
        # Get Amazon source
        amazon = Source.query.filter_by(name='amazon').first()
        
        # Sample products
        products_data = [
            {
                'name': 'Wireless Bluetooth Headphones',
                'description': 'High-quality wireless headphones with noise cancellation',
                'image_url': 'https://via.placeholder.com/300x300?text=Headphones',
                'reviews': [
                    ('Amazing sound quality!', 5.0, True),
                    ('Great battery life, very comfortable', 4.5, True),
                    ('Good but a bit expensive', 3.5, False),
                    ('Best headphones I ever bought', 5.0, True),
                    ('Not worth the price', 2.0, False),
                ]
            },
            {
                'name': 'Smart Fitness Watch',
                'description': 'Track your fitness goals with this smart watch',
                'image_url': 'https://via.placeholder.com/300x300?text=Fitness+Watch',
                'reviews': [
                    ('Perfect for my workouts!', 5.0, True),
                    ('Accurate heart rate monitoring', 4.0, True),
                    ('Battery drains quickly', 2.5, True),
                    ('Great value for money', 4.5, True),
                    ('Screen too small', 3.0, False),
                ]
            },
            {
                'name': 'USB-C Fast Charger',
                'description': 'Fast charging adapter for all your devices',
                'image_url': 'https://via.placeholder.com/300x300?text=Charger',
                'reviews': [
                    ('Charges super fast!', 5.0, True),
                    ('Compact and portable', 4.0, True),
                    ('Stopped working after a month', 1.0, True),
                    ('Does the job well', 4.0, True),
                    ('Gets hot while charging', 3.0, False),
                ]
            }
        ]
        
        print("Adding sample products and reviews...\n")
        
        for prod_data in products_data:
            # Create product
            product = Product(
                name=prod_data['name'],
                description=prod_data['description'],
                image_url=prod_data['image_url']
            )
            db.session.add(product)
            db.session.flush()
            
            # Add product source
            product_source = ProductSource(
                product_id=product.id,
                source_id=amazon.id,
                source_url=f'https://www.amazon.in/dp/SAMPLE{product.id}',
                source_product_id=f'SAMPLE{product.id}',
                price=random.uniform(500, 5000)
            )
            db.session.add(product_source)
            
            # Add reviews
            for i, (text, rating, verified) in enumerate(prod_data['reviews']):
                # Analyze sentiment
                sentiment = sentiment_service.analyze_text(text)
                
                review = Review(
                    product_id=product.id,
                    source_id=amazon.id,
                    text=text,
                    rating=rating,
                    author=f'User{i+1}',
                    is_verified=verified,
                    review_date=datetime.now() - timedelta(days=random.randint(1, 90)),
                    sentiment_score=sentiment['score'],
                    sentiment_label=sentiment['label'],
                    sentiment_confidence=sentiment['confidence']
                )
                db.session.add(review)
            
            print(f"✓ Added: {product.name} ({len(prod_data['reviews'])} reviews)")
        
        db.session.commit()
        
        # Update aggregates
        print("\nUpdating product aggregates...")
        from services.aggregation_service import AggregationService
        agg_service = AggregationService(db, sentiment_service)
        
        products = Product.query.all()
        for product in products:
            agg_service.update_product_aggregates(product.id)
            print(f"✓ Updated: {product.name}")
        
        print(f"\n✓ Successfully added {len(products_data)} products with reviews!")
        print("\nYou can now search for:")
        for prod in products_data:
            print(f"  - {prod['name']}")

if __name__ == '__main__':
    add_sample_data()