"""Initialize the database with tables and seed data"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Source

def init_database():
    """Initialize database with tables and seed data"""
    app = create_app('development')
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created successfully")
        
        # Add sources
        print("\nAdding data sources...")
        sources = [
            {'name': 'amazon', 'base_url': 'https://www.amazon.in', 'is_active': True},
            {'name': 'flipkart', 'base_url': 'https://www.flipkart.com', 'is_active': True},
        ]
        
        for source_data in sources:
            existing = Source.query.filter_by(name=source_data['name']).first()
            if not existing:
                source = Source(**source_data)
                db.session.add(source)
                print(f"✓ Added source: {source_data['name']}")
            else:
                print(f"- Source already exists: {source_data['name']}")
        
        db.session.commit()
        print("\n✓ Database initialized successfully!")
        print(f"\nDatabase location: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == '__main__':
    init_database()