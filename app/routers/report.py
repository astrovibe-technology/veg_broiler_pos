from decimal import Decimal
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db

from models.sale import Sale
from models.sale_item import SaleItem
from models.product import Product
from models.shop import Shop


router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


# ============================================================
# COMMON DATE + TIME FILTER
# ============================================================

def get_date_range(
    from_date: date | None,
    to_date: date | None,
    start_time: time | None = None,
    end_time: time | None = None
):
    """
    Returns datetime range for reports.

    Default:
        Today's complete day.

    Date filters:
        from_date
        to_date

    Time filters:
        start_time
        end_time

    Examples:

        No filters:
            Today 00:00:00 -> Today 23:59:59

        start_time=10:00:
            Today 10:00:00 -> Today 23:59:59

        end_time=18:00:
            Today 00:00:00 -> Today 18:00:00

        start_time=10:00
        end_time=18:00:
            Today 10:00:00 -> Today 18:00:00
    """

    # --------------------------------------------------------
    # DEFAULT DATE = TODAY
    # --------------------------------------------------------

    if from_date is None and to_date is None:

        today = date.today()

        from_date = today
        to_date = today

    elif from_date is None:

        from_date = to_date

    elif to_date is None:

        to_date = from_date

    # --------------------------------------------------------
    # Validate date
    # --------------------------------------------------------

    if from_date > to_date:

        raise HTTPException(
            status_code=400,
            detail="from_date cannot be greater than to_date"
        )

    # --------------------------------------------------------
    # Default times
    # --------------------------------------------------------

    if start_time is None:
        start_time = time.min

    if end_time is None:
        end_time = time.max

    # --------------------------------------------------------
    # If same date, validate time
    # --------------------------------------------------------

    if from_date == to_date:

        if start_time > end_time:

            raise HTTPException(
                status_code=400,
                detail="start_time cannot be greater than end_time"
            )

    # --------------------------------------------------------
    # Build datetime
    # --------------------------------------------------------

    start_datetime = datetime.combine(
        from_date,
        start_time
    )

    end_datetime = datetime.combine(
        to_date,
        end_time
    )

    return start_datetime, end_datetime


# ============================================================
# SHOP FILTER
# ============================================================

def apply_shop_filter(
    query,
    shop_name: str | None
):
    """
    Apply shop name filter if provided.
    """

    if shop_name:

        query = query.filter(
            func.lower(Shop.name)
            == shop_name.strip().lower()
        )

    return query


# ============================================================
# ITEM-WISE REPORT
# ============================================================

@router.get("/item-wise")
def item_wise_report(
    from_date: date | None = None,
    to_date: date | None = None,
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Item-wise sales report.

    Default:
        Today's data.

    Filters:
        from_date
        to_date
        shop_name
    """

    start_datetime, end_datetime = get_date_range(
        from_date,
        to_date
    )

    query = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.unit.label("unit"),

            Shop.id.label("shop_id"),
            Shop.name.label("shop_name"),

            func.sum(
                SaleItem.quantity
            ).label("total_quantity"),

            func.sum(
                SaleItem.total_price
            ).label("total_amount"),

            func.count(
                func.distinct(Sale.id)
            ).label("bill_count")
        )
        .join(
            Sale,
            Sale.id == SaleItem.sale_id
        )
        .join(
            Product,
            Product.id == SaleItem.product_id
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    query = apply_shop_filter(
        query,
        shop_name
    )

    query = (
        query
        .group_by(
            Product.id,
            Product.name,
            Product.unit,
            Shop.id,
            Shop.name
        )
        .order_by(
            Product.name.asc()
        )
    )

    results = query.all()

    report = []

    total_quantity = Decimal("0")
    total_amount = Decimal("0")
    total_bills = 0

    for row in results:

        quantity = Decimal(
            str(row.total_quantity or 0)
        )

        amount = Decimal(
            str(row.total_amount or 0)
        )

        bill_count = row.bill_count or 0

        total_quantity += quantity
        total_amount += amount
        total_bills += bill_count

        report.append({
            "product_id": row.product_id,
            "product_name": row.product_name,
            "unit": row.unit,
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "total_quantity": float(quantity),
            "total_amount": float(amount),
            "bill_count": bill_count
        })

    return {
        "report_type": "item-wise",
        "from_date": start_datetime.date(),
        "to_date": end_datetime.date(),
        "shop_name": shop_name,
        "total_items": len(report),
        "total_quantity": float(total_quantity),
        "total_amount": float(total_amount),
        "total_bills": total_bills,
        "data": report
    }


# ============================================================
# BRANCH-WISE REPORT
# ============================================================

@router.get("/branch-wise")
def branch_wise_report(
    from_date: date | None = None,
    to_date: date | None = None,
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Branch / Shop-wise sales report.

    Default:
        Today's data.

    Filters:
        from_date
        to_date
        shop_name
    """

    start_datetime, end_datetime = get_date_range(
        from_date,
        to_date
    )

    query = (
        db.query(
            Shop.id.label("shop_id"),
            Shop.name.label("shop_name"),

            func.count(
                Sale.id
            ).label("bill_count"),

            func.coalesce(
                func.sum(Sale.subtotal),
                0
            ).label("subtotal"),

            func.coalesce(
                func.sum(Sale.discount),
                0
            ).label("discount"),

            func.coalesce(
                func.sum(Sale.grand_total),
                0
            ).label("grand_total")
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    query = apply_shop_filter(
        query,
        shop_name
    )

    query = (
        query
        .group_by(
            Shop.id,
            Shop.name
        )
        .order_by(
            Shop.name.asc()
        )
    )

    results = query.all()

    report = []

    total_bills = 0
    total_subtotal = Decimal("0")
    total_discount = Decimal("0")
    total_grand_total = Decimal("0")

    for row in results:

        subtotal = Decimal(
            str(row.subtotal or 0)
        )

        discount = Decimal(
            str(row.discount or 0)
        )

        grand_total = Decimal(
            str(row.grand_total or 0)
        )

        bill_count = row.bill_count or 0

        total_bills += bill_count
        total_subtotal += subtotal
        total_discount += discount
        total_grand_total += grand_total

        report.append({
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "bill_count": bill_count,
            "subtotal": float(subtotal),
            "discount": float(discount),
            "grand_total": float(grand_total)
        })

    return {
        "report_type": "branch-wise",
        "from_date": start_datetime.date(),
        "to_date": end_datetime.date(),
        "shop_name": shop_name,
        "total_branches": len(report),
        "total_bills": total_bills,
        "total_subtotal": float(total_subtotal),
        "total_discount": float(total_discount),
        "total_grand_total": float(total_grand_total),
        "data": report
    }


# ============================================================
# TIME-WISE REPORT
# ============================================================

@router.get("/time-wise")
def time_wise_report(
    from_date: date | None = None,
    to_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Time-wise sales report.

    Default:
        Today's complete data.

    Date filters:
        from_date
        to_date

    Time filters:
        start_time
        end_time

    Shop filter:
        shop_name

    Example:

        /reports/time-wise

        /reports/time-wise?start_time=10:00:00&end_time=14:00:00

        /reports/time-wise?from_date=2026-09-01&to_date=2026-09-29

        /reports/time-wise?
        from_date=2026-09-01&
        to_date=2026-09-29&
        start_time=10:00:00&
        end_time=14:00:00&
        shop_name=Alangulam
    """

    start_datetime, end_datetime = get_date_range(
        from_date,
        to_date,
        start_time,
        end_time
    )

    query = (
        db.query(
            Sale.id.label("sale_id"),
            Sale.bill_no.label("bill_no"),
            Sale.grand_total.label("grand_total"),
            Sale.created_at.label("created_at"),

            Shop.id.label("shop_id"),
            Shop.name.label("shop_name")
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    query = apply_shop_filter(
        query,
        shop_name
    )

    query = query.order_by(
        Sale.created_at.asc()
    )

    results = query.all()

    report = []

    total_bills = 0
    total_amount = Decimal("0")

    for row in results:

        amount = Decimal(
            str(row.grand_total or 0)
        )

        created_at = row.created_at

        if created_at:

            formatted_time = created_at.strftime(
                "%I:%M %p"
            )

            formatted_date = created_at.strftime(
                "%d-%m-%Y"
            )

        else:

            formatted_time = ""
            formatted_date = ""

        total_bills += 1
        total_amount += amount

        report.append({
            "sale_id": row.sale_id,
            "bill_no": row.bill_no,
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "date": formatted_date,
            "time": formatted_time,
            "grand_total": float(amount)
        })

    return {
        "report_type": "time-wise",

        "from_date": start_datetime.date(),
        "to_date": end_datetime.date(),

        "start_time": start_datetime.strftime(
            "%I:%M %p"
        ),

        "end_time": end_datetime.strftime(
            "%I:%M %p"
        ),

        "shop_name": shop_name,

        "total_bills": total_bills,
        "total_amount": float(total_amount),

        "data": report
    }


# ============================================================
# OVERALL REPORT
# ============================================================

@router.get("/overall-report")
def overall_report(
    from_date: date | None = None,
    to_date: date | None = None,
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Overall bill-wise sales report.

    Default:
        Today's completed bills.

    Filters:
        from_date
        to_date
        shop_name

    Displays:

        Bill Number
        Date
        Time
        Shop
        Subtotal
        Discount
        Grand Total
        Total Quantity

        Item details inside every bill:
            Product
            Quantity
            Unit
            Rate
            Amount
    """

    start_datetime, end_datetime = get_date_range(
        from_date,
        to_date
    )

    # --------------------------------------------------------
    # Get bills
    # --------------------------------------------------------

    query = (
        db.query(
            Sale.id.label("sale_id"),
            Sale.bill_no.label("bill_no"),

            Sale.subtotal.label("subtotal"),
            Sale.discount.label("discount"),
            Sale.grand_total.label("grand_total"),

            Sale.created_at.label("created_at"),

            Shop.id.label("shop_id"),
            Shop.name.label("shop_name")
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    # --------------------------------------------------------
    # Shop filter
    # --------------------------------------------------------

    query = apply_shop_filter(
        query,
        shop_name
    )

    query = query.order_by(
        Sale.created_at.asc()
    )

    sales = query.all()

    # --------------------------------------------------------
    # No bills
    # --------------------------------------------------------

    if not sales:

        return {
            "report_type": "overall-report",

            "from_date": start_datetime.date(),
            "to_date": end_datetime.date(),

            "shop_name": shop_name,

            "total_bills": 0,
            "total_quantity": 0,
            "total_subtotal": 0,
            "total_discount": 0,
            "total_amount": 0,

            "data": []
        }

    # --------------------------------------------------------
    # Sale IDs
    # --------------------------------------------------------

    sale_ids = [
        sale.sale_id
        for sale in sales
    ]

    # --------------------------------------------------------
    # Get all items in one query
    #
    # This avoids running a separate query for every bill.
    # --------------------------------------------------------

    item_query = (
        db.query(
            SaleItem.sale_id.label("sale_id"),

            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.unit.label("unit"),

            SaleItem.quantity.label("quantity"),
            SaleItem.total_price.label("total_price")
        )
        .join(
            Product,
            Product.id == SaleItem.product_id
        )
        .filter(
            SaleItem.sale_id.in_(sale_ids)
        )
        .order_by(
            SaleItem.sale_id.asc(),
            Product.name.asc()
        )
    )

    item_results = item_query.all()

    # --------------------------------------------------------
    # Group items by sale_id
    # --------------------------------------------------------

    items_by_sale = {}

    for item in item_results:

        if item.sale_id not in items_by_sale:

            items_by_sale[item.sale_id] = []

        quantity = Decimal(
            str(item.quantity or 0)
        )

        total_price = Decimal(
            str(item.total_price or 0)
        )

        # Calculate rate
        if quantity != 0:

            rate = (
                total_price / quantity
            )

        else:

            rate = Decimal("0")

        items_by_sale[item.sale_id].append({
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit": item.unit,

            "quantity": float(quantity),

            "rate": float(rate),

            "amount": float(total_price)
        })

    # --------------------------------------------------------
    # Build final report
    # --------------------------------------------------------

    report = []

    total_bills = 0
    total_quantity = Decimal("0")
    total_subtotal = Decimal("0")
    total_discount = Decimal("0")
    total_amount = Decimal("0")

    for sale in sales:

        subtotal = Decimal(
            str(sale.subtotal or 0)
        )

        discount = Decimal(
            str(sale.discount or 0)
        )

        grand_total = Decimal(
            str(sale.grand_total or 0)
        )

        sale_items = items_by_sale.get(
            sale.sale_id,
            []
        )

        # ----------------------------------------------------
        # Calculate total quantity for this bill
        # ----------------------------------------------------

        bill_quantity = Decimal("0")

        for item in sale_items:

            bill_quantity += Decimal(
                str(item["quantity"])
            )

        # ----------------------------------------------------
        # Date / Time
        # ----------------------------------------------------

        if sale.created_at:

            formatted_date = (
                sale.created_at.strftime(
                    "%d-%m-%Y"
                )
            )

            formatted_time = (
                sale.created_at.strftime(
                    "%I:%M %p"
                )
            )

        else:

            formatted_date = ""
            formatted_time = ""

        # ----------------------------------------------------
        # Totals
        # ----------------------------------------------------

        total_bills += 1

        total_quantity += bill_quantity
        total_subtotal += subtotal
        total_discount += discount
        total_amount += grand_total

        # ----------------------------------------------------
        # Bill report
        # ----------------------------------------------------

        report.append({
            "sale_id": sale.sale_id,

            "bill_no": sale.bill_no,

            "shop_id": sale.shop_id,
            "shop_name": sale.shop_name,

            "date": formatted_date,
            "time": formatted_time,

            "subtotal": float(subtotal),
            "discount": float(discount),
            "grand_total": float(grand_total),

            "total_quantity": float(
                bill_quantity
            ),

            "items": sale_items
        })

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return {
        "report_type": "overall-report",

        "from_date": start_datetime.date(),
        "to_date": end_datetime.date(),

        "shop_name": shop_name,

        "total_bills": total_bills,

        "total_quantity": float(
            total_quantity
        ),

        "total_subtotal": float(
            total_subtotal
        ),

        "total_discount": float(
            total_discount
        ),

        "total_amount": float(
            total_amount
        ),

        "data": report
    }

#---------------Dashboard------------------------#
# ============================================================
# DASHBOARD REPORT
# ============================================================

@router.get("/dashboard")
def dashboard_report(
    from_date: date | None = None,
    to_date: date | None = None,
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Dashboard sales report.

    Default:
        Today's data.

    Filters:
        from_date
        to_date
        shop_name

    Returns:
        - Total sales
        - Total bills
        - Average bill value
        - Shop-wise sales
        - Payment method sales
        - Top 5 selling items
    """

    # ========================================================
    # DATE RANGE
    # ========================================================

    start_datetime, end_datetime = get_date_range(
        from_date,
        to_date
    )

    # ========================================================
    # BASE SALE QUERY
    # ========================================================

    base_query = (
        db.query(Sale)
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    # Shop filter
    if shop_name:

        base_query = base_query.filter(
            func.lower(Shop.name)
            == shop_name.strip().lower()
        )

    sales = base_query.all()

    # ========================================================
    # BASIC DASHBOARD TOTALS
    # ========================================================

    total_bills = len(sales)

    total_sales = Decimal("0")

    for sale in sales:

        total_sales += Decimal(
            str(sale.grand_total or 0)
        )

    # Average bill value
    if total_bills > 0:

        average_bill_value = (
            total_sales / total_bills
        )

    else:

        average_bill_value = Decimal("0")

    # ========================================================
    # SHOP-WISE SALES
    # ========================================================

    shop_query = (
        db.query(
            Shop.id.label("shop_id"),
            Shop.name.label("shop_name"),

            func.count(
                Sale.id
            ).label("bill_count"),

            func.coalesce(
                func.sum(Sale.grand_total),
                0
            ).label("total_sales")
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    if shop_name:

        shop_query = shop_query.filter(
            func.lower(Shop.name)
            == shop_name.strip().lower()
        )

    shop_results = (
        shop_query
        .group_by(
            Shop.id,
            Shop.name
        )
        .order_by(
            func.sum(
                Sale.grand_total
            ).desc()
        )
        .all()
    )

    shop_sales = []

    for row in shop_results:

        amount = Decimal(
            str(row.total_sales or 0)
        )

        shop_sales.append({
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "bill_count": row.bill_count,
            "total_sales": float(amount)
        })

    # ========================================================
    # PAYMENT METHOD SALES
    # ========================================================

    payment_query = (
        db.query(
            Sale.payment_method.label(
                "payment_method"
            ),

            func.count(
                Sale.id
            ).label("bill_count"),

            func.coalesce(
                func.sum(Sale.grand_total),
                0
            ).label("total_amount")
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    if shop_name:

        payment_query = payment_query.filter(
            func.lower(Shop.name)
            == shop_name.strip().lower()
        )

    payment_results = (
        payment_query
        .group_by(
            Sale.payment_method
        )
        .order_by(
            func.sum(
                Sale.grand_total
            ).desc()
        )
        .all()
    )

    # Default payment methods
    payment_sales = {
        "Cash": {
            "bill_count": 0,
            "total_amount": 0
        },
        "Card": {
            "bill_count": 0,
            "total_amount": 0
        },
        "GPay": {
            "bill_count": 0,
            "total_amount": 0
        },
        "Other": {
            "bill_count": 0,
            "total_amount": 0
        }
    }

    for row in payment_results:

        payment_method = (
            row.payment_method or "Other"
        )

        payment_method_clean = (
            payment_method.strip().lower()
        )

        if payment_method_clean == "cash":

            key = "Cash"

        elif payment_method_clean in [
            "card",
            "credit card",
            "debit card"
        ]:

            key = "Card"

        elif payment_method_clean in [
            "gpay",
            "google pay",
            "upi"
        ]:

            key = "GPay"

        else:

            key = "Other"

        amount = Decimal(
            str(row.total_amount or 0)
        )

        payment_sales[key]["bill_count"] += (
            row.bill_count or 0
        )

        payment_sales[key]["total_amount"] += (
            float(amount)
        )

    # ========================================================
    # TOP 5 SELLING ITEMS
    # ========================================================

    item_query = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.unit.label("unit"),

            func.sum(
                SaleItem.quantity
            ).label("total_quantity"),

            func.sum(
                SaleItem.total_price
            ).label("total_amount")
        )
        .join(
            Sale,
            Sale.id == SaleItem.sale_id
        )
        .join(
            Product,
            Product.id == SaleItem.product_id
        )
        .join(
            Shop,
            Shop.id == Sale.shop_id
        )
        .filter(
            Sale.created_at >= start_datetime,
            Sale.created_at <= end_datetime
        )
        .filter(
            Sale.status == "completed"
        )
    )

    if shop_name:

        item_query = item_query.filter(
            func.lower(Shop.name)
            == shop_name.strip().lower()
        )

    item_results = (
        item_query
        .group_by(
            Product.id,
            Product.name,
            Product.unit
        )
        .order_by(
            func.sum(
                SaleItem.quantity
            ).desc()
        )
        .limit(5)
        .all()
    )

    top_selling_items = []

    for row in item_results:

        quantity = Decimal(
            str(row.total_quantity or 0)
        )

        amount = Decimal(
            str(row.total_amount or 0)
        )

        top_selling_items.append({
            "product_id": row.product_id,
            "product_name": row.product_name,
            "unit": row.unit,
            "total_quantity": float(quantity),
            "total_amount": float(amount)
        })

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "report_type": "dashboard",

        "from_date": start_datetime.date(),
        "to_date": end_datetime.date(),

        "shop_name": shop_name,

        # Main cards
        "summary": {
            "total_sales": float(total_sales),
            "total_bills": total_bills,
            "average_bill_value": float(
                average_bill_value
            )
        },

        # Shop sales
        "shop_sales": shop_sales,

        # Payment methods
        "payment_methods": payment_sales,

        # Top 5 items
        "top_selling_items": top_selling_items
    }