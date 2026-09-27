from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db

from models.sale import Sale
from models.sale_item import SaleItem
from models.product import Product
from models.product_shop import ProductShop
from models.shop import Shop
from models.user import User


router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class BillingItem(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class BillingCreate(BaseModel):
    shop_id: int
    customer_name: str | None = None
    customer_phone: str | None = None

    discount: Decimal = Field(
        default=Decimal("0"),
        ge=0
    )

    payment_mode: str

    items: list[BillingItem]


# ============================================================
# BILL PREFIX
# ============================================================

def generate_bill_prefix(shop: Shop):

    shop_name = (shop.name or "").strip()

    if not shop_name:
        raise HTTPException(
            status_code=400,
            detail="Shop name is required for bill number generation"
        )

    shop_name_lower = shop_name.lower()

    if "vegetable" in shop_name_lower:
        type_code = "V"

    elif "broiler" in shop_name_lower:
        type_code = "B"

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Shop name must contain either "
                "'Vegetable' or 'Broiler'"
            )
        )

    address = (shop.address or "").strip()

    if not address:
        raise HTTPException(
            status_code=400,
            detail="Shop address is required for bill number generation"
        )

    address_code = address[0].upper()

    return f"HB{type_code}{address_code}"


# ============================================================
# GET NEXT BILL NUMBER
# ============================================================

@router.get(
    "/next-bill-number",
    status_code=status.HTTP_200_OK
)
def get_next_bill_number(
    shop_id: int,
    db: Session = Depends(get_db)
):

    # Check shop
    shop = (
        db.query(Shop)
        .filter(
            Shop.id == shop_id
        )
        .first()
    )

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    # Generate prefix
    bill_prefix = generate_bill_prefix(shop)

    # Today's date
    today = func.current_date()

    # Get today's last bill
    last_sale = (
        db.query(Sale)
        .filter(
            Sale.shop_id == shop_id,
            func.date(Sale.created_at) == today
        )
        .order_by(
            Sale.id.desc()
        )
        .first()
    )

    # Generate next number
    if last_sale:

        try:
            last_number = int(
                last_sale.bill_no.split("-")[-1]
            )

        except (ValueError, AttributeError):
            last_number = 0

        next_number = last_number + 1

    else:
        next_number = 1

    # Final bill number
    next_bill_number = (
        f"{bill_prefix}-{next_number:03d}"
    )

    return {
        "shop_id": shop_id,
        "bill_prefix": bill_prefix,
        "next_bill_number": next_bill_number
    }


# ============================================================
# CREATE BILL
# ============================================================

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_bill(
    data: BillingCreate,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # 1. Validate shop
    # --------------------------------------------------------

    shop = (
        db.query(Shop)
        .filter(
            Shop.id == data.shop_id
        )
        .first()
    )

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    # --------------------------------------------------------
    # 2. Validate billing items
    # --------------------------------------------------------

    if not data.items:
        raise HTTPException(
            status_code=400,
            detail="At least one product is required"
        )

    # --------------------------------------------------------
    # 3. Validate payment mode
    # --------------------------------------------------------

    allowed_payment_modes = [
        "Cash",
        "Card",
        "UPI",
        "Other"
    ]

    if data.payment_mode not in allowed_payment_modes:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment mode"
        )

    # --------------------------------------------------------
    # 4. Prevent duplicate products
    # --------------------------------------------------------

    product_ids = [
        item.product_id
        for item in data.items
    ]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate products are not allowed in one bill"
        )

    # --------------------------------------------------------
    # 5. Calculate bill
    # --------------------------------------------------------

    subtotal = Decimal("0")

    sale_items_data = []

    for item in data.items:

        # Check product assigned to shop
        product_shop = (
            db.query(ProductShop)
            .filter(
                ProductShop.product_id == item.product_id,
                ProductShop.shop_id == data.shop_id
            )
            .first()
        )

        if not product_shop:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Product {item.product_id} "
                    f"is not available in this shop"
                )
            )

        # Get product
        product = (
            db.query(Product)
            .filter(
                Product.id == item.product_id,
                Product.is_active == True
            )
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Calculate item total
        unit_price = Decimal(
            str(product.price)
        )

        total_price = (
            unit_price * item.quantity
        ).quantize(
            Decimal("0.01")
        )

        subtotal += total_price

        sale_items_data.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "total_price": total_price
        })

    # --------------------------------------------------------
    # 6. Validate discount
    # --------------------------------------------------------

    discount = data.discount

    if discount > subtotal:
        raise HTTPException(
            status_code=400,
            detail="Discount cannot be greater than subtotal"
        )

    # --------------------------------------------------------
    # 7. Calculate grand total
    # --------------------------------------------------------

    grand_total = (
        subtotal - discount
    ).quantize(
        Decimal("0.01")
    )

    # --------------------------------------------------------
    # 8. Get billing user
    # --------------------------------------------------------

    created_by = (
        db.query(User)
        .filter(
            User.shop_id == data.shop_id,
            User.is_active == True
        )
        .first()
    )

    if not created_by:
        raise HTTPException(
            status_code=400,
            detail="No active user found for this shop"
        )

    # --------------------------------------------------------
    # 9. Generate bill prefix
    # --------------------------------------------------------

    bill_prefix = generate_bill_prefix(shop)

    # --------------------------------------------------------
    # 10. Get today's date
    # --------------------------------------------------------

    today = func.current_date()

    # --------------------------------------------------------
    # 11. Get today's last bill
    # --------------------------------------------------------

    last_sale = (
        db.query(Sale)
        .filter(
            Sale.shop_id == data.shop_id,
            func.date(Sale.created_at) == today
        )
        .order_by(
            Sale.id.desc()
        )
        .first()
    )

    # --------------------------------------------------------
    # 12. Generate daily number
    # --------------------------------------------------------

    if last_sale:

        try:
            last_number = int(
                last_sale.bill_no.split("-")[-1]
            )

        except (ValueError, AttributeError):
            last_number = 0

        next_number = last_number + 1

    else:
        next_number = 1

    # --------------------------------------------------------
    # 13. Generate bill number
    # --------------------------------------------------------

    bill_no = (
        f"{bill_prefix}-{next_number:03d}"
    )

    # --------------------------------------------------------
    # 14. Create Sale
    # --------------------------------------------------------

    sale = Sale(
        shop_id=data.shop_id,
        bill_no=bill_no,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        subtotal=subtotal,
        discount=discount,
        grand_total=grand_total,
        payment_mode=data.payment_mode,
        status="completed",
        created_by=created_by.id
    )

    db.add(sale)

    db.flush()

    # --------------------------------------------------------
    # 15. Create Sale Items
    # --------------------------------------------------------

    for item_data in sale_items_data:

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"]
        )

        db.add(sale_item)

    # --------------------------------------------------------
    # 16. Commit
    # --------------------------------------------------------

    db.commit()

    db.refresh(sale)

    # --------------------------------------------------------
    # 17. Response
    # --------------------------------------------------------

    return {
        "message": "Bill created successfully",
        "sale_id": sale.id,
        "bill_no": sale.bill_no,
        "shop_id": sale.shop_id,
        "customer_name": sale.customer_name,
        "customer_phone": sale.customer_phone,
        "subtotal": float(sale.subtotal),
        "discount": float(sale.discount),
        "grand_total": float(sale.grand_total),
        "payment_mode": sale.payment_mode,
        "status": sale.status,
        "created_by": sale.created_by
    }