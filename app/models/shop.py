from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from database import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    shop_type = Column(
        String(50),
        nullable=False
    )

    email = Column(String(150), nullable=True)

    phone = Column(String(20), nullable=True)

    address = Column(Text, nullable=True)

    city = Column(String(100), nullable=True)

    state = Column(String(100), nullable=True)

    pincode = Column(String(10), nullable=True)

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
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