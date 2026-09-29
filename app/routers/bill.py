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

# @router.post(
#     "/create",
#     status_code=status.HTTP_201_CREATED
# )
# def create_bill(
#     data: BillingCreate,
#     db: Session = Depends(get_db)
# ):

#     # --------------------------------------------------------
#     # 1. Validate shop
#     # --------------------------------------------------------

#     shop = (
#         db.query(Shop)
#         .filter(
#             Shop.id == data.shop_id
#         )
#         .first()
#     )

#     if not shop:
#         raise HTTPException(
#             status_code=404,
#             detail="Shop not found"
#         )

#     # --------------------------------------------------------
#     # 2. Validate billing items
#     # --------------------------------------------------------

#     if not data.items:
#         raise HTTPException(
#             status_code=400,
#             detail="At least one product is required"
#         )

#     # --------------------------------------------------------
#     # 3. Validate payment mode
#     # --------------------------------------------------------

#     allowed_payment_modes = [
#         "Cash",
#         "Card",
#         "UPI",
#         "Other"
#     ]

#     if data.payment_mode not in allowed_payment_modes:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid payment mode"
#         )

#     # --------------------------------------------------------
#     # 4. Prevent duplicate products
#     # --------------------------------------------------------

#     product_ids = [
#         item.product_id
#         for item in data.items
#     ]

#     if len(product_ids) != len(set(product_ids)):
#         raise HTTPException(
#             status_code=400,
#             detail="Duplicate products are not allowed in one bill"
#         )

#     # --------------------------------------------------------
#     # 5. Calculate bill
#     # --------------------------------------------------------

#     subtotal = Decimal("0")

#     sale_items_data = []

#     for item in data.items:

#         # Check product assigned to shop
#         product_shop = (
#             db.query(ProductShop)
#             .filter(
#                 ProductShop.product_id == item.product_id,
#                 ProductShop.shop_id == data.shop_id
#             )
#             .first()
#         )

#         if not product_shop:
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"Product {item.product_id} "
#                     f"is not available in this shop"
#                 )
#             )

#         # Get product
#         product = (
#             db.query(Product)
#             .filter(
#                 Product.id == item.product_id,
#                 Product.is_active == True
#             )
#             .first()
#         )

#         if not product:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Product {item.product_id} not found"
#             )

#         # Calculate item total
#         unit_price = Decimal(
#             str(product.price)
#         )

#         total_price = (
#             unit_price * item.quantity
#         ).quantize(
#             Decimal("0.01")
#         )

#         subtotal += total_price

#         sale_items_data.append({
#             "product": product,
#             "quantity": item.quantity,
#             "unit_price": unit_price,
#             "total_price": total_price
#         })

#     # --------------------------------------------------------
#     # 6. Validate discount
#     # --------------------------------------------------------

#     discount = data.discount

#     if discount > subtotal:
#         raise HTTPException(
#             status_code=400,
#             detail="Discount cannot be greater than subtotal"
#         )

#     # --------------------------------------------------------
#     # 7. Calculate grand total
#     # --------------------------------------------------------

#     grand_total = (
#         subtotal - discount
#     ).quantize(
#         Decimal("0.01")
#     )

#     # --------------------------------------------------------
#     # 8. Get billing user
#     # --------------------------------------------------------

#     created_by = (
#         db.query(User)
#         .filter(
#             User.shop_id == data.shop_id,
#             User.is_active == True
#         )
#         .first()
#     )

#     if not created_by:
#         raise HTTPException(
#             status_code=400,
#             detail="No active user found for this shop"
#         )

#     # --------------------------------------------------------
#     # 9. Generate bill prefix
#     # --------------------------------------------------------

#     bill_prefix = generate_bill_prefix(shop)

#     # --------------------------------------------------------
#     # 10. Get today's date
#     # --------------------------------------------------------

#     today = func.current_date()

#     # --------------------------------------------------------
#     # 11. Get today's last bill
#     # --------------------------------------------------------

#     last_sale = (
#         db.query(Sale)
#         .filter(
#             Sale.shop_id == data.shop_id,
#             func.date(Sale.created_at) == today
#         )
#         .order_by(
#             Sale.id.desc()
#         )
#         .first()
#     )

#     # --------------------------------------------------------
#     # 12. Generate daily number
#     # --------------------------------------------------------

#     if last_sale:

#         try:
#             last_number = int(
#                 last_sale.bill_no.split("-")[-1]
#             )

#         except (ValueError, AttributeError):
#             last_number = 0

#         next_number = last_number + 1

#     else:
#         next_number = 1

#     # --------------------------------------------------------
#     # 13. Generate bill number
#     # --------------------------------------------------------

#     bill_no = (
#         f"{bill_prefix}-{next_number:03d}"
#     )

#     # --------------------------------------------------------
#     # 14. Create Sale
#     # --------------------------------------------------------

#     sale = Sale(
#         shop_id=data.shop_id,
#         bill_no=bill_no,
#         customer_name=data.customer_name,
#         customer_phone=data.customer_phone,
#         subtotal=subtotal,
#         discount=discount,
#         grand_total=grand_total,
#         payment_mode=data.payment_mode,
#         status="completed",
#         created_by=created_by.id
#     )

#     db.add(sale)

#     db.flush()

#     # --------------------------------------------------------
#     # 15. Create Sale Items
#     # --------------------------------------------------------

#     for item_data in sale_items_data:

#         sale_item = SaleItem(
#             sale_id=sale.id,
#             product_id=item_data["product"].id,
#             quantity=item_data["quantity"],
#             unit_price=item_data["unit_price"],
#             total_price=item_data["total_price"]
#         )

#         db.add(sale_item)

#     # --------------------------------------------------------
#     # 16. Commit
#     # --------------------------------------------------------

#     db.commit()

#     db.refresh(sale)

#     # --------------------------------------------------------
#     # 17. Response
#     # --------------------------------------------------------

#     return {
#         "message": "Bill created successfully",
#         "sale_id": sale.id,
#         "bill_no": sale.bill_no,
#         "shop_id": sale.shop_id,
#         "customer_name": sale.customer_name,
#         "customer_phone": sale.customer_phone,
#         "subtotal": float(sale.subtotal),
#         "discount": float(sale.discount),
#         "grand_total": float(sale.grand_total),
#         "payment_mode": sale.payment_mode,
#         "status": sale.status,
#         "created_by": sale.created_by
#     }
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db

from models.sale import Sale
from models.sale_item import SaleItem
from models.product import Product
from models.product_shop import ProductShop
from models.shop import Shop
from models.user import User


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


# ============================================================
# HELPERS
# ============================================================

TWO_DECIMAL = Decimal("0.01")


def money(value):
    """
    Convert a value into Decimal with 2 decimal places.
    """
    return Decimal(str(value)).quantize(
        TWO_DECIMAL,
        rounding=ROUND_HALF_UP
    )


def get_shop_bill_prefix(shop: Shop):
    """
    Generate bill prefix based on shop name.

    Vegetable shop:
        V

    Broiler shop:
        B

    Example:
        HBVA-001
        HBBA-001
    """

    shop_name = (getattr(shop, "name", "") or "").strip().lower()

    if "vegetable" in shop_name:
        return "V"

    if "broiler" in shop_name:
        return "B"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Unable to determine shop type. "
            "Shop name must contain 'vegetable' or 'broiler'."
        )
    )


def get_address_code(shop: Shop):
    """
    First character of shop address is used
    as the bill address code.
    """

    address = (getattr(shop, "address", "") or "").strip()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop address is required to generate bill number."
        )

    return address[0].upper()


def get_bill_prefix(shop: Shop):
    """
    Example:

    Vegetable + Alangulam
        HBVA

    Broiler + Alangulam
        HBBA
    """

    shop_type = get_shop_bill_prefix(shop)
    address_code = get_address_code(shop)

    return f"HB{shop_type}{address_code}"


def get_next_bill_number(db: Session, shop: Shop):
    """
    Generate next bill number for the current day.

    Example:
        HBVA-001
        HBVA-002
        HBVA-003
    """

    prefix = get_bill_prefix(shop)

    last_sale = (
        db.query(Sale)
        .filter(
            Sale.shop_id == shop.id,
            Sale.bill_no.like(f"{prefix}-%"),
            func.date(Sale.created_at) == func.current_date()
        )
        .order_by(desc(Sale.id))
        .first()
    )

    next_number = 1

    if last_sale and last_sale.bill_no:
        try:
            last_number = int(
                last_sale.bill_no.split("-")[-1]
            )

            next_number = last_number + 1

        except (ValueError, IndexError):
            next_number = 1

    return f"{prefix}-{next_number:03d}"


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class BillingItem(BaseModel):
    product_id: int
    quantity: Decimal = Field(
        gt=0
    )


class BillingCreate(BaseModel):

    shop_id: int

    customer_name: str | None = None

    customer_phone: str | None = None

    discount: Decimal = Field(
        default=Decimal("0"),
        ge=0
    )

    payment_mode: str

    order_type: str = "Walk-in"

    items: list[BillingItem]


# ============================================================
# NEXT BILL NUMBER
# ============================================================

@router.get("/next-bill-number")
def next_bill_number(
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the next bill number for a shop.

    Example:

    GET /billing/next-bill-number?shop_id=1
    """

    shop = (
        db.query(Shop)
        .filter(Shop.id == shop_id)
        .first()
    )

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found."
        )

    bill_no = get_next_bill_number(
        db,
        shop
    )

    return {
        "status": True,
        "shop_id": shop.id,
        "bill_no": bill_no
    }


# ============================================================
# CREATE BILL
# ============================================================

@router.post("/create")
def create_bill(
    data: BillingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new sale/bill.

    The response contains all information required
    by the frontend printer EXE.
    """

    # ========================================================
    # VALIDATE SHOP
    # ========================================================

    shop = (
        db.query(Shop)
        .filter(Shop.id == data.shop_id)
        .first()
    )

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found."
        )

    # ========================================================
    # VALIDATE ITEMS
    # ========================================================

    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one product is required."
        )

    # ========================================================
    # VALIDATE PAYMENT MODE
    # ========================================================

    allowed_payment_modes = {
        "Cash",
        "Card",
        "UPI",
        "Other"
    }

    if data.payment_mode not in allowed_payment_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid payment mode. "
                "Allowed values: Cash, Card, UPI, Other."
            )
        )

    # ========================================================
    # VALIDATE ORDER TYPE
    # ========================================================

    allowed_order_types = {
        "Walk-in",
        "Delivery"
    }

    if data.order_type not in allowed_order_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid order type. "
                "Allowed values: Walk-in, Delivery."
            )
        )

    # ========================================================
    # CHECK DUPLICATE PRODUCTS
    # ========================================================

    product_ids = [
        item.product_id
        for item in data.items
    ]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate products are not allowed in one bill."
        )

    # ========================================================
    # PREPARE ITEMS
    # ========================================================

    sale_items = []

    subtotal = Decimal("0.00")

    for item_data in data.items:

        # ----------------------------------------------------
        # PRODUCT
        # ----------------------------------------------------

        product = (
            db.query(Product)
            .filter(Product.id == item_data.product_id)
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Product ID "
                    f"{item_data.product_id} not found."
                )
            )

        # ----------------------------------------------------
        # ACTIVE PRODUCT
        # ----------------------------------------------------

        if hasattr(product, "is_active"):

            if product.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Product '{product.name}' "
                        f"is inactive."
                    )
                )

        # ----------------------------------------------------
        # PRODUCT SHOP VALIDATION
        # ----------------------------------------------------

        product_shop = (
            db.query(ProductShop)
            .filter(
                ProductShop.product_id == product.id,
                ProductShop.shop_id == shop.id
            )
            .first()
        )

        if not product_shop:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Product '{product.name}' "
                    f"is not assigned to this shop."
                )
            )

        # ----------------------------------------------------
        # PRODUCT PRICE
        # ----------------------------------------------------

        product_price = getattr(
            product,
            "price",
            None
        )

        if product_price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Price is not configured "
                    f"for product '{product.name}'."
                )
            )

        unit_price = money(product_price)

        quantity = Decimal(
            str(item_data.quantity)
        )

        item_total = money(
            unit_price * quantity
        )

        subtotal += item_total

        sale_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": item_total
            }
        )

    # ========================================================
    # SUBTOTAL
    # ========================================================

    subtotal = money(subtotal)

    # ========================================================
    # DISCOUNT
    # ========================================================

    discount = money(data.discount)

    if discount < Decimal("0.00"):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot be negative."
        )

    if discount > subtotal:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot be greater than subtotal."
        )

    # ========================================================
    # GRAND TOTAL
    # ========================================================

    grand_total = money(
        subtotal - discount
    )

    # ========================================================
    # FIND USER FOR SHOP
    # ========================================================

    created_user = (
        db.query(User)
        .filter(
            User.shop_id == shop.id
        )
        .first()
    )

    if not created_user:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No user is available for this shop. "
                "Cannot create bill."
            )
        )

    # ========================================================
    # BILL NUMBER
    # ========================================================

    bill_no = get_next_bill_number(
        db,
        shop
    )

    # ========================================================
    # SHOP INFORMATION
    # ========================================================

    shop_name = getattr(
        shop,
        "name",
        ""
    ) or ""

    shop_address = getattr(
        shop,
        "address",
        ""
    ) or ""

    # Support either mobile or phone field.
    shop_mobile = getattr(
        shop,
        "mobile",
        None
    )

    if not shop_mobile:

        shop_mobile = getattr(
            shop,
            "phone",
            ""
        ) or ""

    # ========================================================
    # CREATE SALE
    # ========================================================

    sale_data = {
        "shop_id": shop.id,
        "bill_no": bill_no,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "subtotal": subtotal,
        "discount": discount,
        "grand_total": grand_total,
        "payment_mode": data.payment_mode,
        "status": "completed",
        "created_by": created_user.id
    }

    # --------------------------------------------------------
    # ORDER TYPE
    # --------------------------------------------------------

    # Add order_type only if Sale model supports it.
    sale_columns = {
        column.name
        for column in Sale.__table__.columns
    }

    if "order_type" in sale_columns:

        sale_data["order_type"] = data.order_type

    # --------------------------------------------------------
    # CREATE SALE
    # --------------------------------------------------------

    sale = Sale(
        **sale_data
    )

    db.add(sale)

    db.flush()

    # ========================================================
    # CREATE SALE ITEMS
    # ========================================================

    printer_items = []

    for item_data in sale_items:

        product = item_data["product"]

        quantity = item_data["quantity"]

        unit_price = item_data["unit_price"]

        total_price = item_data["total_price"]

        # ----------------------------------------------------
        # SALE ITEM
        # ----------------------------------------------------

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price
        )

        db.add(sale_item)

        # ----------------------------------------------------
        # PRINTER ITEM
        # ----------------------------------------------------

        printer_items.append(
            {
                "product_id": product.id,

                "product_name": getattr(
                    product,
                    "name",
                    ""
                ),

                "name": getattr(
                    product,
                    "name",
                    ""
                ),

                "quantity": float(
                    quantity
                ),

                "unit_price": float(
                    unit_price
                ),

                "total_price": float(
                    total_price
                )
            }
        )

    # ========================================================
    # COMMIT
    # ========================================================

    try:

        db.commit()

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Unable to create bill: {str(e)}"
            )
        )

    # ========================================================
    # REFRESH SALE
    # ========================================================

    db.refresh(sale)

    # ========================================================
    # RETURN BILL
    # ========================================================

    return {
        "status": True,

        "message": "Bill created successfully.",

        # ----------------------------------------------------
        # BILL DETAILS
        # ----------------------------------------------------

        "sale_id": sale.id,

        "bill_no": sale.bill_no,

        "shop_id": shop.id,

        "shop_name": shop_name,

        "shop_address": shop_address,

        "shop_mobile": shop_mobile,

        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------

        "customer_name": (
            data.customer_name
            if data.customer_name
            else "Walk-in Customer"
        ),

        "customer_phone": (
            data.customer_phone
            if data.customer_phone
            else ""
        ),

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

        "order_type": data.order_type,

        # ----------------------------------------------------
        # AMOUNTS
        # ----------------------------------------------------

        "subtotal": float(
            subtotal
        ),

        "discount": float(
            discount
        ),

        "grand_total": float(
            grand_total
        ),

        "total": float(
            grand_total
        ),

        # ----------------------------------------------------
        # PAYMENT
        # ----------------------------------------------------

        "payment_mode": data.payment_mode,

        "status": "completed",

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        "created_by": created_user.id,

        # ----------------------------------------------------
        # ITEMS
        # ----------------------------------------------------

        "items": printer_items
    }


# ============================================================
# GET BILL BY ID
# ============================================================

@router.get("/{sale_id}")
def get_bill(
    sale_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single bill with its items.
    """

    sale = (
        db.query(Sale)
        .filter(Sale.id == sale_id)
        .first()
    )

    if not sale:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found."
        )

    shop = (
        db.query(Shop)
        .filter(Shop.id == sale.shop_id)
        .first()
    )

    sale_items = (
        db.query(SaleItem)
        .filter(
            SaleItem.sale_id == sale.id
        )
        .all()
    )

    items = []

    for sale_item in sale_items:

        product = (
            db.query(Product)
            .filter(
                Product.id == sale_item.product_id
            )
            .first()
        )

        product_name = ""

        if product:
            product_name = getattr(
                product,
                "name",
                ""
            )

        items.append(
            {
                "product_id": sale_item.product_id,

                "product_name": product_name,

                "name": product_name,

                "quantity": float(
                    sale_item.quantity
                ),

                "unit_price": float(
                    sale_item.unit_price
                ),

                "total_price": float(
                    sale_item.total_price
                )
            }
        )

    shop_name = ""

    shop_address = ""

    shop_mobile = ""

    if shop:

        shop_name = getattr(
            shop,
            "name",
            ""
        ) or ""

        shop_address = getattr(
            shop,
            "address",
            ""
        ) or ""

        shop_mobile = getattr(
            shop,
            "mobile",
            None
        )

        if not shop_mobile:

            shop_mobile = getattr(
                shop,
                "phone",
                ""
            ) or ""

    order_type = getattr(
        sale,
        "order_type",
        "Walk-in"
    )

    return {
        "status": True,

        "sale_id": sale.id,

        "bill_no": sale.bill_no,

        "shop_id": sale.shop_id,

        "shop_name": shop_name,

        "shop_address": shop_address,

        "shop_mobile": shop_mobile,

        "customer_name": (
            sale.customer_name
            if sale.customer_name
            else "Walk-in Customer"
        ),

        "customer_phone": (
            sale.customer_phone
            if sale.customer_phone
            else ""
        ),

        "order_type": order_type,

        "subtotal": float(
            sale.subtotal
        ),

        "discount": float(
            sale.discount
        ),

        "grand_total": float(
            sale.grand_total
        ),

        "total": float(
            sale.grand_total
        ),

        "payment_mode": sale.payment_mode,

        "status_value": sale.status,

        "created_by": sale.created_by,

        "items": items
    }