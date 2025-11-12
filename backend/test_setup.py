"""Test script to verify all dependencies are installed correctly"""
import sys

def test_imports():
    """Test that all required packages can be imported"""
    tests = []
    
    # Core dependencies
    print("Testing imports...\n")
    
    try:
        import flask
        print(f"✓ Flask {flask.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        tests.append(False)
    
    try:
        import flask_sqlalchemy
        print("✓ Flask-SQLAlchemy")
        tests.append(True)
    except ImportError as e:
        print(f"✗ Flask-SQLAlchemy import failed: {e}")
        tests.append(False)
    
    try:
        import requests
        print(f"✓ Requests {requests.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"✗ Requests import failed: {e}")
        tests.append(False)
    
    try:
        from bs4 import BeautifulSoup
        print("✓ BeautifulSoup4")
        tests.append(True)
    except ImportError as e:
        print(f"✗ BeautifulSoup4 import failed: {e}")
        tests.append(False)
    
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        print("✓ VADER Sentiment")
        tests.append(True)
    except ImportError as e:
        print(f"✗ VADER Sentiment import failed: {e}")
        tests.append(False)
    
    try:
        from textblob import TextBlob
        print("✓ TextBlob")
        tests.append(True)
    except ImportError as e:
        print(f"✗ TextBlob import failed: {e}")
        tests.append(False)
    
    try:
        import nltk
        print(f"✓ NLTK {nltk.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"✗ NLTK import failed: {e}")
        tests.append(False)
    
    try:
        import sklearn
        print(f"✓ scikit-learn {sklearn.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"✗ scikit-learn import failed: {e}")
        tests.append(False)
    
    print("\n" + "="*50)
    
    if all(tests):
        print("✓ All dependencies installed successfully!")
        return True
    else:
        print("✗ Some dependencies are missing. Please install them.")
        return False

def test_nltk_data():
    """Test NLTK data downloads"""
    print("\nTesting NLTK data...\n")
    
    import nltk
    tests = []
    
    try:
        nltk.data.find('tokenizers/punkt')
        print("✓ NLTK punkt tokenizer")
        tests.append(True)
    except LookupError:
        print("✗ NLTK punkt tokenizer not found")
        print("  Run: python -c \"import nltk; nltk.download('punkt')\"")
        tests.append(False)
    
    try:
        nltk.data.find('corpora/stopwords')
        print("✓ NLTK stopwords")
        tests.append(True)
    except LookupError:
        print("✗ NLTK stopwords not found")
        print("  Run: python -c \"import nltk; nltk.download('stopwords')\"")
        tests.append(False)
    
    return all(tests)

def test_sentiment():
    """Test sentiment analysis"""
    print("\nTesting sentiment analysis...\n")
    
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        
        text = "This is a great product!"
        scores = analyzer.polarity_scores(text)
        
        print(f"Test text: '{text}'")
        print(f"Sentiment scores: {scores}")
        
        if scores['compound'] > 0:
            print("✓ Sentiment analysis working correctly!")
            return True
        else:
            print("✗ Unexpected sentiment result")
            return False
    except Exception as e:
        print(f"✗ Sentiment analysis failed: {e}")
        return False

def test_database():
    """Test database connection"""
    print("\nTesting database...\n")
    
    try:
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from app import create_app
        from models import db, Source
        
        app = create_app('development')
        with app.app_context():
            # Try to query sources
            sources = Source.query.all()
            print(f"✓ Database connection successful!")
            print(f"✓ Found {len(sources)} sources in database")
            return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        print("  Make sure you ran: python init_db.py")
        return False

if __name__ == '__main__':
    print("="*50)
    print("SETUP VERIFICATION TEST")
    print("="*50 + "\n")
    
    results = []
    
    results.append(test_imports())
    results.append(test_nltk_data())
    results.append(test_sentiment())
    results.append(test_database())
    
    print("\n" + "="*50)
    if all(results):
        print("✓✓✓ ALL TESTS PASSED! ")
        print("You're ready to run the application!")
        print("\nNext step: python app.py")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        sys.exit(1)
    print("="*50)