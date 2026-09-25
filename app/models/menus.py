# models/menu.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime
)
from datetime import datetime
from database import Base


class MenuMaster(Base):
    __tablename__ = "menu_master"

    id = Column(Integer, primary_key=True, index=True)
    menu_name = Column(String(200), nullable=False)
    menu_code = Column(String(100), unique=True, nullable=False)
    path = Column(String(255), nullable=True)
    icon = Column(String(100), nullable=True)
    parent_id = Column(
        Integer,
        ForeignKey("menu_master.id"),
        nullable=True
    )
    sort_order = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

# class RolePermission(Base):
#     __tablename__ = "role_permissions"

#     id = Column(Integer, primary_key=True, index=True)
#     role = Column(String(50), nullable=False)
#     menu_id = Column(
#         Integer,
#         ForeignKey("menu_master.id"),
#         nullable=False
#     )
#     shop_id = Column(Integer)   # ✅ IMPORTANT
#     can_view = Column(Boolean, default=True)
#     can_add = Column(Boolean, default=False)
#     can_edit = Column(Boolean, default=False)
#     can_delete = Column(Boolean, default=False)

#     is_active = Column(Boolean, default=True)
#     created_at = Column(
#         DateTime,
#         default=datetime.utcnow
#     )

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)

    # Instead of role
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    menu_id = Column(
        Integer,
        ForeignKey("menu_master.id", ondelete="CASCADE"),
        nullable=False
    )

    can_view = Column(Boolean, default=True)
    can_add = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )