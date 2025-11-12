"""
Search Service - Handle product search and database operations
"""
import logging
from typing import List, Optional
from models import Product, ProductSource, Source
from sqlalchemy import or_, func

logger = logging.getLogger(__name__)

class SearchService:
    """Service for searching products and managing product data"""
    
    def __init__(self, db):
        """
        Initialize search service
        
        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
    
    def search_products(self, query: str, limit: int = 20) -> List[Product]:
        """
        Search for products by name, description, or category
        Uses case-insensitive pattern matching
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of Product objects matching the query
        """
        if not query or not query.strip():
            return []
        
        search_term = f"%{query.lower()}%"
        
        try:
            products = Product.query.filter(
                or_(
                    func.lower(Product.name).like(search_term),
                    func.lower(Product.description).like(search_term),
                    func.lower(Product.category).like(search_term)
                )
            ).order_by(
                Product.total_reviews.desc(),
                Product.avg_rating.desc()
            ).limit(limit).all()
            
            logger.info(f"Search for '{query}' returned {len(products)} results")
            return products
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get product by its ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product object or None if not found
        """
        try:
            return Product.query.get(product_id)
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None
    
    def get_product_by_source_id(self, source_name: str, source_product_id: str) -> Optional[Product]:
        """
        Find product by its source-specific ID (e.g., Amazon ASIN, Flipkart Item ID)
        
        Args:
            source_name: Name of the source ('amazon', 'flipkart', etc.)
            source_product_id: Product ID from the source
            
        Returns:
            Product object or None if not found
        """
        try:
            source = Source.query.filter_by(name=source_name).first()
            if not source:
                logger.warning(f"Source '{source_name}' not found in database")
                return None
            
            product_source = ProductSource.query.filter_by(
                source_id=source.id,
                source_product_id=source_product_id
            ).first()
            
            return product_source.product if product_source else None
            
        except Exception as e:
            logger.error(f"Error getting product by source ID: {e}")
            return None
    
    def create_or_update_product(self, name: str, source_name: str, source_url: str,
                                 source_product_id: str = None, image_url: str = None,
                                 price: float = None, description: str = None,
                                 category: str = None) -> Product:
        """
        Create a new product or update existing one
        
        Args:
            name: Product name
            source_name: Source name ('amazon', 'flipkart')
            source_url: URL of the product on the source
            source_product_id: Product ID from source (optional)
            image_url: Product image URL (optional)
            price: Product price (optional)
            description: Product description (optional)
            category: Product category (optional)
            
        Returns:
            Product object
            
        Raises:
            ValueError: If source not found in database
        """
        try:
            # Get source
            source = Source.query.filter_by(name=source_name).first()
            if not source:
                raise ValueError(f"Source '{source_name}' not found in database. Please run init_db.py")
            
            # Check if product already exists
            existing_product = None
            if source_product_id:
                existing_product = self.get_product_by_source_id(source_name, source_product_id)
            
            if existing_product:
                # Update existing product
                product = existing_product
                logger.info(f"Updating existing product: {product.name} (ID: {product.id})")
                
                # Update fields if provided
                if image_url:
                    product.image_url = image_url
                if description:
                    product.description = description
                if category:
                    product.category = category
                    
            else:
                # Create new product
                logger.info(f"Creating new product: {name}")
                product = Product(
                    name=name,
                    description=description or "",
                    category=category,
                    image_url=image_url
                )
                self.db.session.add(product)
                self.db.session.flush()  # Get product ID before committing
            
            # Create or update product source
            product_source = ProductSource.query.filter_by(
                product_id=product.id,
                source_id=source.id
            ).first()
            
            if product_source:
                # Update existing product source
                product_source.source_url = source_url
                if price is not None:
                    product_source.price = price
                if source_product_id:
                    product_source.source_product_id = source_product_id
                logger.info(f"Updated product source for product {product.id}")
            else:
                # Create new product source
                product_source = ProductSource(
                    product_id=product.id,
                    source_id=source.id,
                    source_product_id=source_product_id,
                    source_url=source_url,
                    price=price
                )
                self.db.session.add(product_source)
                logger.info(f"Created new product source for product {product.id}")
            
            self.db.session.commit()
            logger.info(f"Successfully saved product {product.id}: {product.name}")
            return product
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error creating/updating product: {e}")
            raise
    
    def get_trending_products(self, limit: int = 10) -> List[Product]:
        """
        Get trending products based on review count and rating
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            List of trending Product objects
        """
        try:
            return Product.query.filter(
                Product.total_reviews > 10
            ).order_by(
                (Product.avg_rating * Product.total_reviews).desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting trending products: {e}")
            return []
    
    def get_top_rated_products(self, limit: int = 10, min_reviews: int = 20) -> List[Product]:
        """
        Get top rated products with minimum review threshold
        
        Args:
            limit: Maximum number of products to return
            min_reviews: Minimum number of reviews required
            
        Returns:
            List of top rated Product objects
        """
        try:
            return Product.query.filter(
                Product.total_reviews >= min_reviews
            ).order_by(
                Product.avg_rating.desc(),
                Product.total_reviews.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting top rated products: {e}")
            return []
    
    def get_products_by_category(self, category: str, limit: int = 20) -> List[Product]:
        """
        Get products in a specific category
        
        Args:
            category: Category name
            limit: Maximum number of products to return
            
        Returns:
            List of Product objects in the category
        """
        try:
            return Product.query.filter(
                func.lower(Product.category) == category.lower()
            ).order_by(
                Product.avg_rating.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting products by category '{category}': {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """
        Get list of all unique categories
        
        Returns:
            List of category names
        """
        try:
            categories = self.db.session.query(Product.category).distinct().all()
            return [cat[0] for cat in categories if cat[0]]
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def autocomplete(self, query: str, limit: int = 5) -> List[str]:
        """
        Autocomplete product names for search suggestions
        
        Args:
            query: Partial query string
            limit: Maximum number of suggestions
            
        Returns:
            List of product names matching the query
        """
        if not query or not query.strip():
            return []
        
        try:
            search_term = f"{query.lower()}%"
            
            products = Product.query.filter(
                func.lower(Product.name).like(search_term)
            ).order_by(
                Product.total_reviews.desc()
            ).limit(limit).all()
            
            return [p.name for p in products]
            
        except Exception as e:
            logger.error(f"Error in autocomplete for '{query}': {e}")
            return []
    
    def get_product_sources(self, product_id: int) -> List[ProductSource]:
        """
        Get all sources for a product
        
        Args:
            product_id: Product ID
            
        Returns:
            List of ProductSource objects
        """
        try:
            return ProductSource.query.filter_by(product_id=product_id).all()
        except Exception as e:
            logger.error(f"Error getting sources for product {product_id}: {e}")
            return []
    
    def get_recent_products(self, limit: int = 10) -> List[Product]:
        """
        Get recently added products
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            List of recently added Product objects
        """
        try:
            return Product.query.order_by(
                Product.created_at.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent products: {e}")
            return []
    
    def search_by_price_range(self, min_price: float = None, max_price: float = None, 
                              limit: int = 20) -> List[Product]:
        """
        Search products by price range
        
        Args:
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            limit: Maximum number of products to return
            
        Returns:
            List of Product objects in the price range
        """
        try:
            query = self.db.session.query(Product).join(ProductSource)
            
            if min_price is not None:
                query = query.filter(ProductSource.price >= min_price)
            if max_price is not None:
                query = query.filter(ProductSource.price <= max_price)
            
            return query.order_by(ProductSource.price).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error searching by price range: {e}")
            return []
    
    def get_product_count(self) -> int:
        """
        Get total number of products in database
        
        Returns:
            Number of products
        """
        try:
            return Product.query.count()
        except Exception as e:
            logger.error(f"Error getting product count: {e}")
            return 0
    
    def delete_product(self, product_id: int) -> bool:
        """
        Delete a product and all associated data
        
        Args:
            product_id: Product ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            product = Product.query.get(product_id)
            if not product:
                logger.warning(f"Product {product_id} not found for deletion")
                return False
            
            self.db.session.delete(product)
            self.db.session.commit()
            logger.info(f"Deleted product {product_id}: {product.name}")
            return True
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error deleting product {product_id}: {e}")
            return False