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
# COMMON DATE FILTER
# ============================================================

def get_date_range(
    from_date: date | None,
    to_date: date | None
):
    """
    If no dates are provided:
        return today's date range.

    If only from_date is provided:
        use from_date to from_date.

    If only to_date is provided:
        use to_date to to_date.

    If both are provided:
        use the complete date range.
    """

    if from_date is None and to_date is None:
        today = date.today()

        start_datetime = datetime.combine(
            today,
            time.min
        )

        end_datetime = datetime.combine(
            today,
            time.max
        )

        return start_datetime, end_datetime

    if from_date is None:
        from_date = to_date

    if to_date is None:
        to_date = from_date

    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be greater than to_date"
        )

    start_datetime = datetime.combine(
        from_date,
        time.min
    )

    end_datetime = datetime.combine(
        to_date,
        time.max
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
            func.lower(Shop.name) == shop_name.strip().lower()
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

    # Apply shop filter
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

    # Apply shop filter
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
    shop_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Time-wise sales report.

    Default:
        Today's data.

    Time format:
        12-hour format with AM / PM.

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

    # Apply shop filter
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

        # ----------------------------------------------------
        # Convert time to 12-hour format
        # ----------------------------------------------------

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
        "shop_name": shop_name,
        "total_bills": total_bills,
        "total_amount": float(total_amount),
        "data": report
    }