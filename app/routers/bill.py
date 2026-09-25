from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
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

    shop = db.query(Shop).filter(
        Shop.id == data.shop_id
    ).first()

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
    # 4. Prevent duplicate product IDs
    # --------------------------------------------------------

    product_ids = [item.product_id for item in data.items]

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

        # ----------------------------------------------------
        # Check product is assigned to this shop
        # ----------------------------------------------------

        product_shop = db.query(ProductShop).filter(
            ProductShop.product_id == item.product_id,
            ProductShop.shop_id == data.shop_id
        ).first()

        if not product_shop:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Product {item.product_id} "
                    f"is not available in this shop"
                )
            )

        # ----------------------------------------------------
        # Get product
        # ----------------------------------------------------

        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # ----------------------------------------------------
        # Calculate item total
        # ----------------------------------------------------

        unit_price = Decimal(str(product.price))

        total_price = (
            unit_price * item.quantity
        ).quantize(Decimal("0.01"))

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
    ).quantize(Decimal("0.01"))

    # --------------------------------------------------------
    # 8. Get billing user
    # --------------------------------------------------------
    #
    # For now this example uses the first active user of the
    # shop.
    #
    # Later, replace this with your JWT logged-in user.
    #

    created_by = db.query(User).filter(
        User.shop_id == data.shop_id,
        User.is_active == True
    ).first()

    if not created_by:
        raise HTTPException(
            status_code=400,
            detail="No active user found for this shop"
        )

    # --------------------------------------------------------
    # 9. Generate bill number
    # --------------------------------------------------------

    last_sale = db.query(Sale).filter(
        Sale.shop_id == data.shop_id
    ).order_by(
        Sale.id.desc()
    ).first()

    if last_sale:
        next_number = last_sale.id + 1
    else:
        next_number = 1

    bill_no = f"INV-{data.shop_id}-{next_number:05d}"

    # --------------------------------------------------------
    # 10. Create Sale
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

    # Flush so sale.id is available
    db.flush()

    # --------------------------------------------------------
    # 11. Create Sale Items
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
    # 12. Commit everything
    # --------------------------------------------------------

    db.commit()

    # Refresh sale
    db.refresh(sale)

    # --------------------------------------------------------
    # 13. Response
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

