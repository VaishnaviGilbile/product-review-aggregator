import pytest
from backend.services.sentiment_service import SentimentService, HuggingFaceSentimentService

@pytest.fixture
def vader_service():
    """Create VADER sentiment service"""
    return SentimentService(use_vader=True)

@pytest.fixture
def textblob_service():
    """Create TextBlob sentiment service"""
    return SentimentService(use_vader=False)

class TestSentimentService:
    
    def test_positive_sentiment_vader(self, vader_service):
        """Test positive sentiment detection with VADER"""
        text = "This product is absolutely amazing! Best purchase ever!"
        result = vader_service.analyze_text(text)
        
        assert result['label'] == 'positive'
        assert result['score'] > 0
        assert 0 <= result['confidence'] <= 1
    
    def test_negative_sentiment_vader(self, vader_service):
        """Test negative sentiment detection with VADER"""
        text = "Terrible product. Complete waste of money. Very disappointed."
        result = vader_service.analyze_text(text)
        
        assert result['label'] == 'negative'
        assert result['score'] < 0
        assert 0 <= result['confidence'] <= 1
    
    def test_neutral_sentiment_vader(self, vader_service):
        """Test neutral sentiment detection with VADER"""
        text = "The product arrived on time. It has a blue color."
        result = vader_service.analyze_text(text)
        
        assert result['label'] == 'neutral'
        assert -0.05 <= result['score'] <= 0.05
    
    def test_empty_text(self, vader_service):
        """Test handling of empty text"""
        result = vader_service.analyze_text("")
        
        assert result['label'] == 'neutral'
        assert result['score'] == 0.0
        assert result['confidence'] == 0.0
    
    def test_batch_analysis(self, vader_service):
        """Test batch sentiment analysis"""
        texts = [
            "Great product!",
            "Terrible experience.",
            "It's okay, nothing special."
        ]
        
        results = vader_service.analyze_batch(texts)
        
        assert len(results) == 3
        assert results[0]['label'] == 'positive'
        assert results[1]['label'] == 'negative'
        assert results[2]['label'] in ['neutral', 'positive', 'negative']
    
    def test_emoji_handling(self, vader_service):
        """Test emoji sentiment detection"""
        text = "Love this! 😍❤️"
        result = vader_service.analyze_text(text)
        
        assert result['label'] == 'positive'
        assert result['score'] > 0
    
    def test_mixed_sentiment(self, vader_service):
        """Test mixed sentiment text"""
        text = "Great quality but very expensive. Not sure if it's worth it."
        result = vader_service.analyze_text(text)
        
        # Should detect some sentiment, not necessarily strongly positive or negative
        assert result['label'] in ['positive', 'negative', 'neutral']
    
    def test_sentiment_distribution(self, vader_service):
        """Test sentiment distribution calculation"""
        reviews = [
            {'sentiment_label': 'positive'},
            {'sentiment_label': 'positive'},
            {'sentiment_label': 'negative'},
            {'sentiment_label': 'neutral'}
        ]
        
        distribution = vader_service.get_sentiment_distribution(reviews)
        
        assert distribution['positive'] == 50.0  # 2/4
        assert distribution['negative'] == 25.0  # 1/4
        assert distribution['neutral'] == 25.0   # 1/4
    
    def test_empty_reviews_distribution(self, vader_service):
        """Test distribution with no reviews"""
        distribution = vader_service.get_sentiment_distribution([])
        
        assert distribution['positive'] == 0.0
        assert distribution['neutral'] == 0.0
        assert distribution['negative'] == 0.0
    
    def test_textblob_positive(self, textblob_service):
        """Test positive sentiment with TextBlob"""
        text = "Excellent product! Highly recommend!"
        result = textblob_service.analyze_text(text)
        
        assert result['label'] == 'positive'
        assert result['score'] > 0
    
    def test_textblob_negative(self, textblob_service):
        """Test negative sentiment with TextBlob"""
        text = "Poor quality. Very disappointing."
        result = textblob_service.analyze_text(text)
        
        assert result['label'] == 'negative'
        assert result['score'] < 0
    
    def test_analyze_with_rating(self, vader_service):
        """Test sentiment analysis with rating comparison"""
        # Positive text with high rating (consistent)
        result1 = vader_service.analyze_with_rating("Great product!", rating=5.0)
        assert result1['inconsistent'] is False
        
        # Positive text with low rating (inconsistent)
        result2 = vader_service.analyze_with_rating("Great product!", rating=1.0)
        assert result2['inconsistent'] is True
        
        # Negative text with high rating (inconsistent)
        result3 = vader_service.analyze_with_rating("Terrible product.", rating=5.0)
        assert result3['inconsistent'] is True
    
    def test_sentiment_confidence_scores(self, vader_service):
        """Test that confidence scores are reasonable"""
        texts = [
            "This is THE BEST product EVER!!!",  # Strong positive
            "okay",  # Weak sentiment
            "This is the WORST product ever!!!",  # Strong negative
        ]
        
        results = vader_service.analyze_batch(texts)
        
        # Strong sentiments should have higher confidence
        assert results[0]['confidence'] > results[1]['confidence']
        assert results[2]['confidence'] > results[1]['confidence']
    
    def test_case_insensitivity(self, vader_service):
        """Test that sentiment is case-insensitive"""
        text_lower = "great product"
        text_upper = "GREAT PRODUCT"
        text_mixed = "GrEaT pRoDuCt"
        
        result_lower = vader_service.analyze_text(text_lower)
        result_upper = vader_service.analyze_text(text_upper)
        result_mixed = vader_service.analyze_text(text_mixed)
        
        # All should be positive
        assert result_lower['label'] == 'positive'
        assert result_upper['label'] == 'positive'
        assert result_mixed['label'] == 'positive'


class TestHuggingFaceSentiment:
    """Tests for Hugging Face sentiment service"""
    
    @pytest.fixture
    def hf_service(self):
        """Create HF sentiment service"""
        return HuggingFaceSentimentService()
    
    def test_service_initialization(self, hf_service):
        """Test that service initializes properly"""
        # Should either have transformer available or fallback to VADER
        assert hf_service.available in [True, False]
        if not hf_service.available:
            assert hf_service.fallback is not None
    
    def test_fallback_on_error(self, hf_service):
        """Test that service falls back gracefully on errors"""
        # Test with text that might cause issues
        text = "A" * 1000  # Very long text
        result = hf_service.analyze_text(text)
        
        # Should return a valid result even if it uses fallback
        assert 'label' in result
        assert 'score' in result
        assert 'confidence' in result
    
    def test_text_truncation(self, hf_service):
        """Test that long texts are handled properly"""
        long_text = "Great product! " * 200  # > 512 tokens
        result = hf_service.analyze_text(long_text)
        
        assert result['label'] in ['positive', 'negative', 'neutral']


class TestSentimentEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def service(self):
        return SentimentService(use_vader=True)
    
    def test_none_text(self, service):
        """Test handling of None text"""
        result = service.analyze_text(None)
        assert result['score'] == 0.0
        assert result['label'] == 'neutral'
    
    def test_whitespace_only(self, service):
        """Test handling of whitespace-only text"""
        result = service.analyze_text("   \n\t  ")
        assert result['score'] == 0.0
    
    def test_special_characters(self, service):
        """Test handling of special characters"""
        text = "Great!!! @#$%^&* Product!!!"
        result = service.analyze_text(text)
        assert result['label'] == 'positive'
    
    def test_numbers_only(self, service):
        """Test handling of numbers"""
        result = service.analyze_text("12345")
        assert result['label'] == 'neutral'
    
    def test_mixed_languages(self, service):
        """Test handling of mixed language text"""
        # English with some non-English characters
        text = "Great product! बहुत अच्छा"
        result = service.analyze_text(text)
        # Should at least process the English part
        assert result['label'] in ['positive', 'negative', 'neutral']
    
    def test_sarcasm(self, service):
        """Test handling of sarcasm (known limitation)"""
        text = "Oh great, another broken product. Just what I needed!"
        result = service.analyze_text(text)
        # Note: VADER might not catch sarcasm correctly
        # This test documents the behavior
        assert result['label'] in ['positive', 'negative', 'neutral']