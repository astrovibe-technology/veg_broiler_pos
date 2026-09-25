from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)

    shop_id = Column(
        Integer,
        ForeignKey("shops.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    bill_no = Column(
        String(50),
        nullable=False,
        index=True
    )

    customer_name = Column(
        String(150),
        nullable=True
    )

    customer_phone = Column(
        String(20),
        nullable=True
    )

    subtotal = Column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    discount = Column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    grand_total = Column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    payment_mode = Column(
        String(30),
        nullable=False
    )

    status = Column(
        String(30),
        nullable=False,
        default="completed"
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )