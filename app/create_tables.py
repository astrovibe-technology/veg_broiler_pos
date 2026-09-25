
from database import Base, engine

# Import all models
from models.shop import Shop
from models.user import User
from models.category import Category
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.stock_movement import StockMovement
from models.price_history import PriceHistory
from models.audit_log import AuditLog
from models.category_shop import CategoryShop
from models.product_shop import ProductShop


def create_product_tables():

    print("Creating product tables...")

    # Create products table
    Product.__table__.create(
        bind=engine,
        checkfirst=True
    )

    print("products table created successfully.")

    # Create product_shops table
    ProductShop.__table__.create(
        bind=engine,
        checkfirst=True
    )

    print("product_shops table created successfully.")

    print("Product tables created successfully.")


if __name__ == "__main__":
    create_product_tables()

