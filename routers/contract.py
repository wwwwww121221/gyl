from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from models import Contract, InquirySupplier, InquiryTask, Supplier, User, get_db
from routers.inquiry import get_current_user


router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[1]


def _require_buyer_or_admin(current_user: User):
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/list")
def get_contract_list(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    if limit <= 0:
        limit = 20
    if limit > 200:
        limit = 200

    query = (
        db.query(
            Contract,
            InquiryTask.title.label("task_title"),
            Supplier.name.label("supplier_name"),
        )
        .join(InquiryTask, Contract.task_id == InquiryTask.id)
        .join(InquirySupplier, Contract.inquiry_supplier_id == InquirySupplier.id)
        .join(Supplier, InquirySupplier.supplier_id == Supplier.id)
        .order_by(Contract.id.desc())
    )
    total = query.count()
    rows = query.offset(skip).limit(limit).all()

    items = []
    for contract, task_title, supplier_name in rows:
        contract_no = f"HT-{contract.task_id}-{contract.inquiry_supplier_id}"
        items.append(
            {
                "id": contract.id,
                "contract_no": contract_no,
                "inquiry_name": task_title,
                "supplier_name": supplier_name,
                "total_amount": contract.total_amount,
                "status": contract.status,
            }
        )
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{contract_id}/pdf")
def preview_or_download_contract_pdf(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_buyer_or_admin(current_user)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.pdf_path:
        raise HTTPException(status_code=404, detail="Contract PDF not generated")

    if contract.pdf_path.startswith("/static/"):
        local_path = BASE_DIR / contract.pdf_path.lstrip("/")
    else:
        candidate = Path(contract.pdf_path)
        local_path = candidate if candidate.is_absolute() else BASE_DIR / contract.pdf_path
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=str(local_path),
        media_type="application/pdf",
        filename=local_path.name,
    )
