
from database import Base, engine

# Import all models so SQLAlchemy registers their tables
from models.user import User
from models.shop import Shop
from models.category import Category
from models.category_shop import CategoryShop
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.stock_movement import StockMovement
from models.price_history import PriceHistory
from models.audit_log import AuditLog
from models.menus import MenuMaster, RolePermission


def create_tables():
    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("All database tables created successfully.")


if __name__ == "__main__":
    create_tables()

