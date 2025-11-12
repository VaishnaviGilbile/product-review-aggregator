from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False, index=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(1000))
    
    # Aggregated metrics
    avg_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    sentiment_positive = db.Column(db.Float, default=0.0)
    sentiment_neutral = db.Column(db.Float, default=0.0)
    sentiment_negative = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sources = db.relationship('ProductSource', back_populates='product', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='product', cascade='all, delete-orphan')
    keywords = db.relationship('ProductKeyword', back_populates='product', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'image_url': self.image_url,
            'avg_rating': round(self.avg_rating, 2),
            'total_reviews': self.total_reviews,
            'sentiment': {
                'positive': round(self.sentiment_positive, 2),
                'neutral': round(self.sentiment_neutral, 2),
                'negative': round(self.sentiment_negative, 2)
            },
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Source(db.Model):
    __tablename__ = 'sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # amazon, flipkart
    base_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    
    product_sources = db.relationship('ProductSource', back_populates='source')

class ProductSource(db.Model):
    """Links products to their sources with source-specific data"""
    __tablename__ = 'product_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'), nullable=False)
    
    source_product_id = db.Column(db.String(200))  # ASIN, etc.
    source_url = db.Column(db.String(1000))
    source_rating = db.Column(db.Float)
    source_review_count = db.Column(db.Integer, default=0)
    price = db.Column(db.Float)
    currency = db.Column(db.String(10), default='INR')
    
    last_scraped = db.Column(db.DateTime)
    is_available = db.Column(db.Boolean, default=True)
    
    # Relationships
    product = db.relationship('Product', back_populates='sources')
    source = db.relationship('Source', back_populates='product_sources')
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'source_id', name='unique_product_source'),
    )

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'), nullable=False)
    
    # Review content
    title = db.Column(db.String(500))
    text = db.Column(db.Text)
    rating = db.Column(db.Float)  # Normalized 1-5 scale
    original_rating = db.Column(db.Float)  # Original source rating
    
    # Metadata
    author = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    review_date = db.Column(db.DateTime)
    helpful_count = db.Column(db.Integer, default=0)
    
    # Sentiment analysis results
    sentiment_score = db.Column(db.Float)  # -1 to 1
    sentiment_label = db.Column(db.String(20))  # positive, neutral, negative
    sentiment_confidence = db.Column(db.Float)
    
    # Source tracking
    source_review_id = db.Column(db.String(200))
    source_url = db.Column(db.String(1000))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    product = db.relationship('Product', back_populates='reviews')
    source = db.relationship('Source')
    
    __table_args__ = (
        db.Index('idx_product_sentiment', 'product_id', 'sentiment_label'),
        db.Index('idx_product_date', 'product_id', 'review_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'rating': self.rating,
            'author': self.author,
            'is_verified': self.is_verified,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'helpful_count': self.helpful_count,
            'sentiment': {
                'score': round(self.sentiment_score, 3) if self.sentiment_score else None,
                'label': self.sentiment_label,
                'confidence': round(self.sentiment_confidence, 3) if self.sentiment_confidence else None
            },
            'source': self.source.name if self.source else None
        }

class ProductKeyword(db.Model):
    """Stores extracted pros/cons keywords for products"""
    __tablename__ = 'product_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    keyword = db.Column(db.String(200), nullable=False)
    keyword_type = db.Column(db.String(20))  # 'pro' or 'con'
    frequency = db.Column(db.Integer, default=1)
    tfidf_score = db.Column(db.Float)
    
    product = db.relationship('Product', back_populates='keywords')
    
    __table_args__ = (
        db.Index('idx_product_keyword', 'product_id', 'keyword_type'),
    )

class ScrapingJob(db.Model):
    """Track scraping jobs for monitoring"""
    __tablename__ = 'scraping_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'))
    
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    task_id = db.Column(db.String(200))  # Celery task ID
    
    reviews_scraped = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)