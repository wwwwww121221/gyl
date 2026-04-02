from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models import (
    Contract,
    InquiryRequest,
    InquirySupplier,
    InquiryTaskItem,
    Quotation,
    Supplier,
    User,
    get_db,
)
from routers.inquiry import get_current_user


router = APIRouter()


def _require_buyer_or_admin(current_user: User):
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/history")
def get_material_history(
    material_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    keyword = material_name.strip()

    latest_quote_subquery = (
        db.query(
            Quotation.inquiry_supplier_id.label("inquiry_supplier_id"),
            Quotation.item_id.label("item_id"),
            func.max(Quotation.round).label("latest_round"),
        )
        .group_by(Quotation.inquiry_supplier_id, Quotation.item_id)
        .subquery()
    )

    rows = (
        db.query(
            Contract.created_at.label("created_at"),
            Supplier.name.label("supplier_name"),
            InquiryRequest.material_name.label("material_name"),
            Quotation.price.label("price"),
            func.coalesce(Quotation.qty, InquiryRequest.qty).label("qty"),
            Contract.id.label("contract_id"),
        )
        .join(InquirySupplier, Contract.inquiry_supplier_id == InquirySupplier.id)
        .join(Supplier, InquirySupplier.supplier_id == Supplier.id)
        .join(
            latest_quote_subquery,
            latest_quote_subquery.c.inquiry_supplier_id == InquirySupplier.id,
        )
        .join(
            Quotation,
            and_(
                Quotation.inquiry_supplier_id == latest_quote_subquery.c.inquiry_supplier_id,
                Quotation.item_id == latest_quote_subquery.c.item_id,
                Quotation.round == latest_quote_subquery.c.latest_round,
            ),
        )
        .join(InquiryTaskItem, Quotation.item_id == InquiryTaskItem.id)
        .join(InquiryRequest, InquiryTaskItem.request_id == InquiryRequest.id)
        .filter(Contract.pdf_path.isnot(None))
        .filter(InquiryRequest.material_name.ilike(f"%{keyword}%"))
        .order_by(Contract.created_at.asc())
        .all()
    )

    return {
        "items": [
            {
                "date": row.created_at.strftime("%Y-%m-%d") if row.created_at else "",
                "supplier_name": row.supplier_name or "",
                "material_name": row.material_name or "",
                "price": float(row.price) if row.price is not None else 0,
                "qty": float(row.qty) if row.qty is not None else 0,
                "contract_id": row.contract_id,
            }
            for row in rows
        ]
    }
