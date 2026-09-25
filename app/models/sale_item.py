from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)

    sale_id = Column(
        Integer,
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    quantity = Column(
        Numeric(12, 3),
        nullable=False
    )

    unit_price = Column(
        Numeric(12, 2),
        nullable=False
    )

    total_price = Column(
        Numeric(12, 2),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )