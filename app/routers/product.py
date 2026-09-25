from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db

from models.product import Product
from models.product_shop import ProductShop
from models.category import Category
from models.shop import Shop


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class CreateProductRequest(BaseModel):
    name: str
    category_id: int
    unit: str
    price: float
    shop_ids: list[int]


class UpdateProductRequest(BaseModel):
    name: str | None = None
    category_id: int | None = None
    unit: str | None = None
    price: float | None = None
    shop_ids: list[int] | None = None
    is_active: bool | None = None


# =========================================================
# CREATE PRODUCT
# =========================================================

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_product(
    request: CreateProductRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------
    # Validate category
    # -----------------------------------------

    category = db.query(Category).filter(
        Category.id == request.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    # -----------------------------------------
    # Validate shop list
    # -----------------------------------------

    if not request.shop_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one shop must be selected"
        )

    # Remove duplicate shop IDs
    shop_ids = list(set(request.shop_ids))

    # -----------------------------------------
    # Check all shops exist
    # -----------------------------------------

    shops = db.query(Shop).filter(
        Shop.id.in_(shop_ids)
    ).all()

    if len(shops) != len(shop_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more shops not found"
        )

    # -----------------------------------------
    # Create Product
    # -----------------------------------------

    product = Product(
        name=request.name,
        category_id=request.category_id,
        unit=request.unit,
        price=request.price,
        is_active=True
    )

    db.add(product)

    # Get generated product ID
    db.flush()

    # -----------------------------------------
    # Assign product to shops
    # -----------------------------------------

    for shop_id in shop_ids:

        product_shop = ProductShop(
            product_id=product.id,
            shop_id=shop_id
        )

        db.add(product_shop)

    db.commit()

    db.refresh(product)

    return {
        "message": "Product created successfully",
        "product_id": product.id,
        "name": product.name,
        "price": float(product.price),
        "shop_ids": shop_ids
    }


# =========================================================
# GET ALL PRODUCTS
# =========================================================

@router.get("/")
def get_products(
    shop_id: int | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Product)

    # -----------------------------------------
    # Filter by category
    # -----------------------------------------

    if category_id:
        query = query.filter(
            Product.category_id == category_id
        )

    # -----------------------------------------
    # Filter by shop
    # -----------------------------------------

    if shop_id:

        product_ids = db.query(
            ProductShop.product_id
        ).filter(
            ProductShop.shop_id == shop_id
        ).subquery()

        query = query.filter(
            Product.id.in_(product_ids)
        )

    products = query.order_by(
        Product.id.desc()
    ).all()

    result = []

    for product in products:

        assignments = db.query(
            ProductShop
        ).filter(
            ProductShop.product_id == product.id
        ).all()

        result.append({
            "id": product.id,
            "name": product.name,
            "category_id": product.category_id,
            "unit": product.unit,
            "price": float(product.price),
            "is_active": product.is_active,
            "shop_ids": [
                item.shop_id
                for item in assignments
            ],
            "created_at": product.created_at,
            "updated_at": product.updated_at
        })

    return result


# =========================================================
# GET PRODUCT BY ID
# =========================================================

@router.get("/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    assignments = db.query(
        ProductShop
    ).filter(
        ProductShop.product_id == product.id
    ).all()

    return {
        "id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "unit": product.unit,
        "price": float(product.price),
        "is_active": product.is_active,
        "shop_ids": [
            item.shop_id
            for item in assignments
        ],
        "created_at": product.created_at,
        "updated_at": product.updated_at
    }


# =========================================================
# UPDATE PRODUCT
# =========================================================

@router.put("/{product_id}")
def update_product(
    product_id: int,
    request: UpdateProductRequest,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # -----------------------------------------
    # Update product fields
    # -----------------------------------------

    if request.name is not None:
        product.name = request.name

    if request.category_id is not None:

        category = db.query(Category).filter(
            Category.id == request.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        product.category_id = request.category_id

    if request.unit is not None:
        product.unit = request.unit

    if request.price is not None:
        product.price = request.price

    if request.is_active is not None:
        product.is_active = request.is_active

    # -----------------------------------------
    # Update shop assignments
    # -----------------------------------------

    if request.shop_ids is not None:

        if not request.shop_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one shop must be selected"
            )

        shop_ids = list(set(request.shop_ids))

        # Check shops
        shops = db.query(Shop).filter(
            Shop.id.in_(shop_ids)
        ).all()

        if len(shops) != len(shop_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more shops not found"
            )

        # Remove old assignments
        db.query(ProductShop).filter(
            ProductShop.product_id == product.id
        ).delete(
            synchronize_session=False
        )

        # Add new assignments
        for shop_id in shop_ids:

            db.add(
                ProductShop(
                    product_id=product.id,
                    shop_id=shop_id
                )
            )

    db.commit()

    db.refresh(product)

    assignments = db.query(
        ProductShop
    ).filter(
        ProductShop.product_id == product.id
    ).all()

    return {
        "message": "Product updated successfully",
        "product_id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "unit": product.unit,
        "price": float(product.price),
        "is_active": product.is_active,
        "shop_ids": [
            item.shop_id
            for item in assignments
        ]
    }


# =========================================================
# DELETE PRODUCT
# =========================================================

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.delete(product)

    db.commit()

    return {
        "message": "Product deleted successfully"
    }

