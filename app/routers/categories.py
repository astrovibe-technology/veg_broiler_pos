from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.category import Category
from models.category_shop import CategoryShop
from models.shop import Shop


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class CreateCategoryRequest(BaseModel):
    name: str
    description: str | None = None
    shop_ids: list[int]


class UpdateCategoryRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    shop_ids: list[int] | None = None


# --------------------------------------------------
# CREATE CATEGORY
# --------------------------------------------------

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_category(
    request: CreateCategoryRequest,
    db: Session = Depends(get_db)
):

    # Check duplicate category
    existing_category = db.query(Category).filter(
        Category.name == request.name
    ).first()

    if existing_category:
        raise HTTPException(
            status_code=400,
            detail="Category already exists"
        )

    # Check that at least one shop is selected
    if not request.shop_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one shop must be selected"
        )

    # Remove duplicate shop IDs
    shop_ids = list(set(request.shop_ids))

    # Check all shops
    shops = db.query(Shop).filter(
        Shop.id.in_(shop_ids)
    ).all()

    if len(shops) != len(shop_ids):
        found_shop_ids = {shop.id for shop in shops}

        invalid_shop_ids = [
            shop_id
            for shop_id in shop_ids
            if shop_id not in found_shop_ids
        ]

        raise HTTPException(
            status_code=404,
            detail={
                "message": "One or more shops not found",
                "invalid_shop_ids": invalid_shop_ids
            }
        )

    # Create category
    category = Category(
        name=request.name,
        description=request.description,
        is_active=True
    )

    db.add(category)
    db.flush()

    # Assign category to shops
    for shop_id in shop_ids:

        category_shop = CategoryShop(
            category_id=category.id,
            shop_id=shop_id
        )

        db.add(category_shop)

    db.commit()
    db.refresh(category)

    return {
        "message": "Category created successfully",
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "shop_ids": shop_ids,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        }
    }


# --------------------------------------------------
# GET ALL CATEGORIES
# --------------------------------------------------

@router.get("/")
def get_all_categories(
    shop_id: int | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Category)

    # Filter categories by shop
    if shop_id is not None:

        shop = db.query(Shop).filter(
            Shop.id == shop_id
        ).first()

        if not shop:
            raise HTTPException(
                status_code=404,
                detail="Shop not found"
            )

        query = query.join(
            CategoryShop,
            Category.id == CategoryShop.category_id
        ).filter(
            CategoryShop.shop_id == shop_id
        )

    categories = query.order_by(
        Category.id.desc()
    ).all()

    result = []

    for category in categories:

        mappings = db.query(CategoryShop).filter(
            CategoryShop.category_id == category.id
        ).all()

        shop_ids = [
            mapping.shop_id
            for mapping in mappings
        ]

        result.append({
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "shop_ids": shop_ids,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        })

    return {
        "message": "Categories retrieved successfully",
        "total": len(result),
        "categories": result
    }


# --------------------------------------------------
# GET CATEGORY BY ID
# --------------------------------------------------

@router.get("/{category_id}")
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    mappings = db.query(CategoryShop).filter(
        CategoryShop.category_id == category.id
    ).all()

    shop_ids = [
        mapping.shop_id
        for mapping in mappings
    ]

    return {
        "message": "Category retrieved successfully",
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "shop_ids": shop_ids,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        }
    }


# --------------------------------------------------
# UPDATE CATEGORY
# --------------------------------------------------

@router.put("/{category_id}")
def update_category(
    category_id: int,
    request: UpdateCategoryRequest,
    db: Session = Depends(get_db)
):

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    # Update name
    if request.name is not None:

        existing_category = db.query(Category).filter(
            Category.name == request.name,
            Category.id != category_id
        ).first()

        if existing_category:
            raise HTTPException(
                status_code=400,
                detail="Category already exists"
            )

        category.name = request.name

    # Update description
    if request.description is not None:
        category.description = request.description

    # Update active status
    if request.is_active is not None:
        category.is_active = request.is_active

    # Update shop assignments
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

            found_shop_ids = {
                shop.id for shop in shops
            }

            invalid_shop_ids = [
                shop_id
                for shop_id in shop_ids
                if shop_id not in found_shop_ids
            ]

            raise HTTPException(
                status_code=404,
                detail={
                    "message": "One or more shops not found",
                    "invalid_shop_ids": invalid_shop_ids
                }
            )

        # Remove existing assignments
        db.query(CategoryShop).filter(
            CategoryShop.category_id == category_id
        ).delete(
            synchronize_session=False
        )

        # Add new assignments
        for shop_id in shop_ids:

            category_shop = CategoryShop(
                category_id=category_id,
                shop_id=shop_id
            )

            db.add(category_shop)

    db.commit()
    db.refresh(category)

    # Get updated shops
    mappings = db.query(CategoryShop).filter(
        CategoryShop.category_id == category_id
    ).all()

    shop_ids = [
        mapping.shop_id
        for mapping in mappings
    ]

    return {
        "message": "Category updated successfully",
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "shop_ids": shop_ids,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        }
    }


# --------------------------------------------------
# DELETE CATEGORY
# --------------------------------------------------

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    # Delete category
    # category_shops will be deleted automatically
    # because of ON DELETE CASCADE
    db.delete(category)

    db.commit()

    return {
        "message": "Category deleted successfully",
        "category_id": category_id
    }
