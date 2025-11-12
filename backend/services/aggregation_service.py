import logging
from typing import Dict, List
from models import Product, Review, ProductKeyword
from utils.keyword_extractor import KeywordExtractor

logger = logging.getLogger(__name__)

class AggregationService:
    """Service for aggregating and analyzing product reviews"""
    
    def __init__(self, db, sentiment_service):
        self.db = db
        self.sentiment_service = sentiment_service
        self.keyword_extractor = KeywordExtractor()
    
    def update_product_aggregates(self, product_id: int):
        """Update all aggregate metrics for a product"""
        product = Product.query.get(product_id)
        if not product:
            logger.error(f"Product {product_id} not found")
            return
        
        reviews = Review.query.filter_by(product_id=product_id).all()
        
        if not reviews:
            return
        
        # Calculate average rating
        total_rating = sum(r.rating for r in reviews if r.rating)
        product.avg_rating = total_rating / len(reviews) if reviews else 0.0
        product.total_reviews = len(reviews)
        
        # Calculate sentiment distribution
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        for review in reviews:
            sentiment_counts[review.sentiment_label] += 1
        
        total = len(reviews)
        product.sentiment_positive = (sentiment_counts['positive'] / total) * 100
        product.sentiment_neutral = (sentiment_counts['neutral'] / total) * 100
        product.sentiment_negative = (sentiment_counts['negative'] / total) * 100
        
        # Extract and save keywords
        self._update_product_keywords(product, reviews)
        
        self.db.session.commit()
        logger.info(f"Updated aggregates for product {product_id}")
    
    def _update_product_keywords(self, product: Product, reviews: List[Review]):
        """Extract and save keywords for product"""
        # Delete old keywords
        ProductKeyword.query.filter_by(product_id=product.id).delete()
        
        # Extract new keywords
        review_dicts = [{'text': r.text, 'sentiment_label': r.sentiment_label} 
                       for r in reviews]
        
        pros_cons = self.keyword_extractor.extract_pros_cons(review_dicts)
        
        # Save pros
        for keyword, score in pros_cons['pros']:
            kw = ProductKeyword(
                product_id=product.id,
                keyword=keyword,
                keyword_type='pro',
                tfidf_score=score
            )
            self.db.session.add(kw)
        
        # Save cons
        for keyword, score in pros_cons['cons']:
            kw = ProductKeyword(
                product_id=product.id,
                keyword=keyword,
                keyword_type='con',
                tfidf_score=score
            )
            self.db.session.add(kw)
    
    def get_product_aggregate(self, product_id: int) -> Dict:
        """Get comprehensive aggregate data for a product"""
        product = Product.query.get(product_id)
        if not product:
            return {}
        
        reviews = Review.query.filter_by(product_id=product_id).all()
        
        # Basic stats
        aggregate = {
            'product_id': product_id,
            'total_reviews': product.total_reviews,
            'avg_rating': round(product.avg_rating, 2),
            'sentiment_distribution': {
                'positive': round(product.sentiment_positive, 1),
                'neutral': round(product.sentiment_neutral, 1),
                'negative': round(product.sentiment_negative, 1)
            }
        }
        
        # Rating distribution
        rating_dist = self._get_rating_distribution(reviews)
        aggregate['rating_distribution'] = rating_dist
        
        # Pros and cons
        pros = ProductKeyword.query.filter_by(
            product_id=product_id, 
            keyword_type='pro'
        ).order_by(ProductKeyword.tfidf_score.desc()).limit(10).all()
        
        cons = ProductKeyword.query.filter_by(
            product_id=product_id, 
            keyword_type='con'
        ).order_by(ProductKeyword.tfidf_score.desc()).limit(10).all()
        
        aggregate['pros'] = [kw.keyword for kw in pros]
        aggregate['cons'] = [kw.keyword for kw in cons]
        
        # Recent reviews
        recent = Review.query.filter_by(product_id=product_id)\
            .order_by(Review.review_date.desc())\
            .limit(5)\
            .all()
        
        aggregate['recent_reviews'] = [r.to_dict() for r in recent]
        
        # Top positive and negative reviews
        top_positive = Review.query.filter_by(
            product_id=product_id, 
            sentiment_label='positive'
        ).order_by(Review.sentiment_confidence.desc()).limit(3).all()
        
        top_negative = Review.query.filter_by(
            product_id=product_id, 
            sentiment_label='negative'
        ).order_by(Review.sentiment_confidence.desc()).limit(3).all()
        
        aggregate['top_positive_reviews'] = [r.to_dict() for r in top_positive]
        aggregate['top_negative_reviews'] = [r.to_dict() for r in top_negative]
        
        # Verified vs unverified sentiment
        verified_reviews = [r for r in reviews if r.is_verified]
        if verified_reviews:
            verified_sentiment = self._calculate_sentiment_stats(verified_reviews)
            aggregate['verified_sentiment'] = verified_sentiment
        
        # Time-based trends (if enough data)
        if len(reviews) > 20:
            trends = self._get_sentiment_trends(reviews)
            aggregate['sentiment_trends'] = trends
        
        return aggregate
    
    def _get_rating_distribution(self, reviews: List[Review]) -> Dict[str, int]:
        """Calculate distribution of ratings"""
        distribution = {str(i): 0 for i in range(1, 6)}
        
        for review in reviews:
            if review.rating:
                rating_bucket = str(int(round(review.rating)))
                if rating_bucket in distribution:
                    distribution[rating_bucket] += 1
        
        return distribution
    
    def _calculate_sentiment_stats(self, reviews: List[Review]) -> Dict:
        """Calculate sentiment statistics for a set of reviews"""
        if not reviews:
            return {}
        
        total = len(reviews)
        positive = sum(1 for r in reviews if r.sentiment_label == 'positive')
        neutral = sum(1 for r in reviews if r.sentiment_label == 'neutral')
        negative = sum(1 for r in reviews if r.sentiment_label == 'negative')
        
        avg_score = sum(r.sentiment_score for r in reviews if r.sentiment_score) / total
        
        return {
            'positive_pct': round((positive / total) * 100, 1),
            'neutral_pct': round((neutral / total) * 100, 1),
            'negative_pct': round((negative / total) * 100, 1),
            'avg_sentiment_score': round(avg_score, 3)
        }
    
    def _get_sentiment_trends(self, reviews: List[Review]) -> Dict:
        """
        Analyze sentiment trends over time
        Returns monthly sentiment breakdown
        """
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        # Group by month
        monthly_sentiments = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0})
        
        for review in reviews:
            if not review.review_date:
                continue
            
            month_key = review.review_date.strftime('%Y-%m')
            monthly_sentiments[month_key][review.sentiment_label] += 1
            monthly_sentiments[month_key]['total'] += 1
        
        # Calculate percentages
        trends = []
        for month, counts in sorted(monthly_sentiments.items()):
            total = counts['total']
            trends.append({
                'month': month,
                'positive': round((counts['positive'] / total) * 100, 1),
                'neutral': round((counts['neutral'] / total) * 100, 1),
                'negative': round((counts['negative'] / total) * 100, 1),
                'total_reviews': total
            })
        
        return trends[-12:]  # Last 12 months
    
    def compare_products(self, product_ids: List[int]) -> Dict:
        """Compare multiple products side by side"""
        comparison = {
            'products': [],
            'metrics': ['avg_rating', 'total_reviews', 'sentiment_positive', 'sentiment_negative']
        }
        
        for pid in product_ids:
            product = Product.query.get(pid)
            if product:
                aggregate = self.get_product_aggregate(pid)
                comparison['products'].append({
                    'id': product.id,
                    'name': product.name,
                    'aggregate': aggregate
                })
        
        return comparison