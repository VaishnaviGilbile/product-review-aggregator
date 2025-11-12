import logging
from typing import List, Dict, Tuple
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class KeywordExtractor:
    """Extract meaningful keywords and phrases from reviews"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        # Add common review words that aren't useful
        self.stop_words.update([
            'product', 'item', 'bought', 'purchase', 'ordered', 'received',
            'delivery', 'amazon', 'flipkart', 'seller', 'one', 'two', 'get'
        ])
    
    def extract_pros_cons(self, reviews: List[Dict]) -> Dict[str, List[Tuple[str, int]]]:
        """
        Extract top pros and cons from reviews
        Returns: {pros: [(keyword, frequency)], cons: [(keyword, frequency)]}
        """
        positive_reviews = [r for r in reviews if r.get('sentiment_label') == 'positive']
        negative_reviews = [r for r in reviews if r.get('sentiment_label') == 'negative']
        
        pros = self._extract_keywords_tfidf(positive_reviews, top_n=10)
        cons = self._extract_keywords_tfidf(negative_reviews, top_n=10)
        
        return {
            'pros': pros,
            'cons': cons
        }
    
    def _extract_keywords_tfidf(self, reviews: List[Dict], top_n: int = 10) -> List[Tuple[str, float]]:
        """Extract keywords using TF-IDF"""
        if not reviews:
            return []
        
        # Combine all review texts
        texts = [r.get('text', '') for r in reviews if r.get('text')]
        if not texts:
            return []
        
        # Clean texts
        texts = [self._clean_text(text) for text in texts]
        
        try:
            # Use TF-IDF with bigrams
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words=list(self.stop_words),
                ngram_range=(1, 2),  # unigrams and bigrams
                min_df=2  # keyword must appear in at least 2 reviews
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            scores = tfidf_matrix.mean(axis=0).A1
            
            # Sort by score
            keywords = [(feature_names[i], scores[i]) for i in range(len(feature_names))]
            keywords.sort(key=lambda x: x[1], reverse=True)
            
            return keywords[:top_n]
            
        except Exception as e:
            logger.error(f"Error in TF-IDF extraction: {e}")
            # Fallback to frequency-based extraction
            return self._extract_keywords_frequency(reviews, top_n)
    
    def _extract_keywords_frequency(self, reviews: List[Dict], top_n: int = 10) -> List[Tuple[str, int]]:
        """Fallback method using word frequency"""
        words = []
        
        for review in reviews:
            text = review.get('text', '')
            clean = self._clean_text(text)
            words.extend(clean.split())
        
        # Count frequencies
        counter = Counter(words)
        
        # Filter out stopwords and short words
        filtered = [(word, count) for word, count in counter.items() 
                   if word not in self.stop_words and len(word) > 3]
        
        filtered.sort(key=lambda x: x[1], reverse=True)
        return filtered[:top_n]
    
    def _clean_text(self, text: str) -> str:
        """Clean text for keyword extraction"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-z\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_phrases(self, reviews: List[Dict], min_length: int = 2, max_length: int = 5) -> List[Tuple[str, int]]:
        """
        Extract common phrases using RAKE-like approach
        """
        phrases = []
        
        for review in reviews:
            text = review.get('text', '')
            # Split by sentence delimiters and stopwords
            candidates = self._get_phrase_candidates(text)
            phrases.extend(candidates)
        
        # Count phrase frequencies
        phrase_counts = Counter(phrases)
        
        # Filter by length
        filtered = [(phrase, count) for phrase, count in phrase_counts.items()
                   if min_length <= len(phrase.split()) <= max_length and count >= 2]
        
        filtered.sort(key=lambda x: x[1], reverse=True)
        return filtered[:20]
    
    def _get_phrase_candidates(self, text: str) -> List[str]:
        """Get phrase candidates by splitting on stopwords"""
        text = self._clean_text(text)
        words = text.split()
        
        phrases = []
        current_phrase = []
        
        for word in words:
            if word in self.stop_words or len(word) < 3:
                if len(current_phrase) >= 2:
                    phrases.append(' '.join(current_phrase))
                current_phrase = []
            else:
                current_phrase.append(word)
        
        if len(current_phrase) >= 2:
            phrases.append(' '.join(current_phrase))
        
        return phrases
    
    def get_aspect_sentiments(self, reviews: List[Dict], aspects: List[str]) -> Dict[str, Dict]:
        """
        Analyze sentiment for specific aspects (e.g., 'battery', 'camera', 'price')
        Returns: {aspect: {positive: count, negative: count, neutral: count}}
        """
        aspect_sentiments = {aspect: {'positive': 0, 'negative': 0, 'neutral': 0} 
                            for aspect in aspects}
        
        for review in reviews:
            text = review.get('text', '').lower()
            sentiment = review.get('sentiment_label', 'neutral')
            
            for aspect in aspects:
                if aspect.lower() in text:
                    aspect_sentiments[aspect][sentiment] += 1
        
        return aspect_sentiments