from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt

from database import get_db
from models.shop import Shop
from models.user import User


router = APIRouter(
    prefix="/shops",
    tags=["Shops"]
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class CreateShopRequest(BaseModel):

    # Shop details
    name: str
    shop_type: str

    email: EmailStr
    phone: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    # Login details
    username: str
    password: str


class UpdateShopRequest(BaseModel):

    # Shop details
    name: str | None = None
    shop_type: str | None = None

    email: EmailStr | None = None
    phone: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    # Login details
    username: str | None = None
    password: str | None = None

    is_active: bool | None = None


# =========================================================
# CREATE SHOP
# =========================================================

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_shop(
    request: CreateShopRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Check username
    # -----------------------------------------------------

    existing_username = db.query(User).filter(
        User.username == request.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # -----------------------------------------------------
    # Check email
    # -----------------------------------------------------

    existing_email = db.query(User).filter(
        User.email == request.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # -----------------------------------------------------
    # Create shop
    # -----------------------------------------------------

    shop = Shop(
        name=request.name,
        shop_type=request.shop_type,
        email=request.email,
        phone=request.phone,
        address=request.address,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        is_active=True
    )

    db.add(shop)

    # Get shop ID
    db.flush()

    # -----------------------------------------------------
    # Hash password
    # -----------------------------------------------------

    password_hash = bcrypt.hashpw(
        request.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    # -----------------------------------------------------
    # Create shop user
    # -----------------------------------------------------

    user = User(
        shop_id=shop.id,
        name=request.name,
        username=request.username,
        password_hash=password_hash,
        email=request.email,
        phone=request.phone,
        role="manager",
        is_active=True
    )

    db.add(user)

    # -----------------------------------------------------
    # Commit
    # -----------------------------------------------------

    db.commit()

    db.refresh(shop)
    db.refresh(user)

    return {
        "message": "Shop created successfully",
        "shop": {
            "id": shop.id,
            "name": shop.name,
            "shop_type": shop.shop_type,
            "email": shop.email,
            "phone": shop.phone,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "pincode": shop.pincode,
            "is_active": shop.is_active
        },
        "user": {
            "id": user.id,
            "shop_id": user.shop_id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active
        }
    }


# =========================================================
# GET ALL SHOPS
# =========================================================

@router.get("/")
def get_all_shops(
    db: Session = Depends(get_db)
):

    shops = db.query(Shop).order_by(
        Shop.id.desc()
    ).all()

    result = []

    for shop in shops:

        user = db.query(User).filter(
            User.shop_id == shop.id
        ).first()

        result.append({
            "id": shop.id,
            "name": shop.name,
            "shop_type": shop.shop_type,
            "email": shop.email,
            "phone": shop.phone,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "pincode": shop.pincode,
            "is_active": shop.is_active,

            "user": {
                "id": user.id if user else None,
                "username": user.username if user else None,
                "email": user.email if user else None,
                "role": user.role if user else None,
                "is_active": user.is_active if user else None
            } if user else None
        })

    return {
        "message": "Shops retrieved successfully",
        "total": len(result),
        "shops": result
    }


# =========================================================
# GET SHOP BY ID
# =========================================================

@router.get("/{shop_id}")
def get_shop(
    shop_id: int,
    db: Session = Depends(get_db)
):

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    user = db.query(User).filter(
        User.shop_id == shop.id
    ).first()

    return {
        "message": "Shop retrieved successfully",

        "shop": {
            "id": shop.id,
            "name": shop.name,
            "shop_type": shop.shop_type,
            "email": shop.email,
            "phone": shop.phone,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "pincode": shop.pincode,
            "is_active": shop.is_active
        },

        "user": {
            "id": user.id if user else None,
            "username": user.username if user else None,
            "email": user.email if user else None,
            "phone": user.phone if user else None,
            "role": user.role if user else None,
            "is_active": user.is_active if user else None
        } if user else None
    }


# =========================================================
# UPDATE SHOP
# =========================================================

@router.put("/{shop_id}")
def update_shop(
    shop_id: int,
    request: UpdateShopRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find shop
    # -----------------------------------------------------

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    # -----------------------------------------------------
    # Find shop user
    # -----------------------------------------------------

    user = db.query(User).filter(
        User.shop_id == shop.id
    ).first()

    # -----------------------------------------------------
    # Check username
    # -----------------------------------------------------

    if request.username and user:

        existing_username = db.query(User).filter(
            User.username == request.username,
            User.id != user.id
        ).first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

    # -----------------------------------------------------
    # Check email
    # -----------------------------------------------------

    if request.email and user:

        existing_email = db.query(User).filter(
            User.email == request.email,
            User.id != user.id
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

    # =====================================================
    # UPDATE SHOP
    # =====================================================

    if request.name is not None:
        shop.name = request.name

    if request.shop_type is not None:
        shop.shop_type = request.shop_type

    if request.email is not None:
        shop.email = request.email

    if request.phone is not None:
        shop.phone = request.phone

    if request.address is not None:
        shop.address = request.address

    if request.city is not None:
        shop.city = request.city

    if request.state is not None:
        shop.state = request.state

    if request.pincode is not None:
        shop.pincode = request.pincode

    if request.is_active is not None:
        shop.is_active = request.is_active

    # =====================================================
    # UPDATE SHOP USER
    # =====================================================

    if user:

        if request.name is not None:
            user.name = request.name

        if request.email is not None:
            user.email = request.email

        if request.phone is not None:
            user.phone = request.phone

        if request.username is not None:
            user.username = request.username

        if request.password is not None:

            password_hash = bcrypt.hashpw(
                request.password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            user.password_hash = password_hash

        if request.is_active is not None:
            user.is_active = request.is_active

    # -----------------------------------------------------
    # Commit
    # -----------------------------------------------------

    db.commit()

    db.refresh(shop)

    if user:
        db.refresh(user)

    return {
        "message": "Shop updated successfully",

        "shop": {
            "id": shop.id,
            "name": shop.name,
            "shop_type": shop.shop_type,
            "email": shop.email,
            "phone": shop.phone,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "pincode": shop.pincode,
            "is_active": shop.is_active
        },

        "user": {
            "id": user.id if user else None,
            "shop_id": user.shop_id if user else None,
            "name": user.name if user else None,
            "username": user.username if user else None,
            "email": user.email if user else None,
            "phone": user.phone if user else None,
            "role": user.role if user else None,
            "is_active": user.is_active if user else None
        } if user else None
    }


# =========================================================
# DELETE SHOP
# =========================================================

@router.delete("/{shop_id}")
def delete_shop(
    shop_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find shop
    # -----------------------------------------------------

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    # -----------------------------------------------------
    # Find shop user
    # -----------------------------------------------------

    user = db.query(User).filter(
        User.shop_id == shop.id
    ).first()

    # -----------------------------------------------------
    # Delete user
    # -----------------------------------------------------

    if user:
        db.delete(user)

    # -----------------------------------------------------
    # Delete shop
    # -----------------------------------------------------

    db.delete(shop)

    db.commit()

    return {
        "message": "Shop deleted successfully",
        "shop_id": shop_id
    }
