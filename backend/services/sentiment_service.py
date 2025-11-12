import logging
from typing import List, Dict, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk
from textblob import TextBlob

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class SentimentService:
    """Service for analyzing sentiment of reviews"""
    
    def __init__(self, use_vader=True):
        """
        Initialize sentiment analyzer
        Args:
            use_vader: If True, use VADER. If False, use TextBlob (for baseline)
        """
        self.use_vader = use_vader
        if use_vader:
            self.analyzer = SentimentIntensityAnalyzer()
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a single text
        Returns: {score, label, confidence}
        """
        if not text or not text.strip():
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        if self.use_vader:
            return self._analyze_vader(text)
        else:
            return self._analyze_textblob(text)
    
    def _analyze_vader(self, text: str) -> Dict[str, float]:
        """Analyze using VADER"""
        scores = self.analyzer.polarity_scores(text)
        
        # VADER compound score ranges from -1 (most negative) to 1 (most positive)
        compound = scores['compound']
        
        # Classify based on compound score
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        # Confidence is the absolute value of compound score
        confidence = abs(compound)
        
        return {
            'score': compound,
            'label': label,
            'confidence': confidence
        }
    
    def _analyze_textblob(self, text: str) -> Dict[str, float]:
        """Analyze using TextBlob (baseline)"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        
        # Classify
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        confidence = abs(polarity)
        
        return {
            'score': polarity,
            'label': label,
            'confidence': confidence
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """Analyze multiple texts"""
        return [self.analyze_text(text) for text in texts]
    
    def get_sentiment_distribution(self, reviews: List[Dict]) -> Dict[str, float]:
        """
        Calculate sentiment distribution from reviews
        Returns percentages for positive, neutral, negative
        """
        if not reviews:
            return {'positive': 0.0, 'neutral': 0.0, 'negative': 0.0}
        
        total = len(reviews)
        positive = sum(1 for r in reviews if r.get('sentiment_label') == 'positive')
        negative = sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        neutral = sum(1 for r in reviews if r.get('sentiment_label') == 'neutral')
        
        return {
            'positive': (positive / total) * 100,
            'neutral': (neutral / total) * 100,
            'negative': (negative / total) * 100
        }
    
    def analyze_with_rating(self, text: str, rating: float) -> Dict[str, float]:
        """
        Analyze text sentiment and compare with rating
        This helps detect sarcasm or inconsistencies
        """
        text_sentiment = self.analyze_text(text)
        
        # Normalize rating to -1 to 1 scale (assuming 1-5 rating)
        normalized_rating = (rating - 3) / 2  # 1->-1, 3->0, 5->1
        
        # Check for inconsistency
        inconsistent = False
        if (normalized_rating > 0.5 and text_sentiment['score'] < -0.2) or \
           (normalized_rating < -0.5 and text_sentiment['score'] > 0.2):
            inconsistent = True
        
        return {
            **text_sentiment,
            'rating_sentiment': normalized_rating,
            'inconsistent': inconsistent
        }


class HuggingFaceSentimentService:
    """
    Advanced sentiment analysis using Hugging Face transformers
    Requires: pip install transformers torch
    """
    
    def __init__(self, model_name='distilbert-base-uncased-finetuned-sst-2-english'):
        """
        Initialize with a pre-trained model
        Default model is good for general sentiment, can use domain-specific models
        """
        try:
            from transformers import pipeline
            self.pipeline = pipeline('sentiment-analysis', model=model_name)
            self.available = True
        except ImportError:
            logger.warning("Transformers not installed. Install with: pip install transformers torch")
            self.available = False
            self.fallback = SentimentService(use_vader=True)
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using transformer model"""
        if not self.available:
            return self.fallback.analyze_text(text)
        
        if not text or not text.strip():
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        # Truncate to model's max length (512 tokens for most BERT models)
        text = text[:512]
        
        try:
            result = self.pipeline(text)[0]
            
            # Convert to our format
            label = result['label'].lower()
            confidence = result['score']
            
            # Convert to -1 to 1 score
            if label == 'positive':
                score = confidence
            elif label == 'negative':
                score = -confidence
            else:
                score = 0.0
            
            return {
                'score': score,
                'label': label,
                'confidence': confidence
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return self.fallback.analyze_text(text)
    
    def analyze_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, float]]:
        """Analyze multiple texts efficiently"""
        if not self.available:
            return self.fallback.analyze_batch(texts)
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = [self.analyze_text(text) for text in batch]
            results.extend(batch_results)
        
        return results