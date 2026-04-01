from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import ContractTemplate, User, get_db
from routers.inquiry import get_current_user


router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "static" / "templates"
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


class ContractTemplatePayload(BaseModel):
    name: str
    file_path: str
    default_buyer_name: Optional[str] = None
    is_active: bool = False


def _require_buyer_or_admin(current_user: User):
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/list")
def list_templates(
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
    query = db.query(ContractTemplate).order_by(ContractTemplate.id.desc())
    total = query.count()
    rows = query.offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "file_path": t.file_path,
                "default_buyer_name": t.default_buyer_name,
                "is_active": t.is_active,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in rows
        ],
    }


@router.get("/{template_id}")
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": template.id,
        "name": template.name,
        "file_path": template.file_path,
        "default_buyer_name": template.default_buyer_name,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


@router.post("")
def create_template(
    payload: ContractTemplatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    exists = db.query(ContractTemplate).filter(ContractTemplate.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Template name already exists")
    if payload.is_active:
        db.query(ContractTemplate).update({ContractTemplate.is_active: False})
    template = ContractTemplate(
        name=payload.name,
        file_path=payload.file_path,
        default_buyer_name=payload.default_buyer_name,
        is_active=payload.is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"id": template.id, "message": "Template created successfully"}


@router.put("/{template_id}")
def update_template(
    template_id: int,
    payload: ContractTemplatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    name_conflict = (
        db.query(ContractTemplate)
        .filter(ContractTemplate.name == payload.name, ContractTemplate.id != template_id)
        .first()
    )
    if name_conflict:
        raise HTTPException(status_code=400, detail="Template name already exists")
    if payload.is_active:
        db.query(ContractTemplate).filter(ContractTemplate.id != template_id).update(
            {ContractTemplate.is_active: False}
        )
    template.name = payload.name
    template.file_path = payload.file_path
    template.default_buyer_name = payload.default_buyer_name
    template.is_active = payload.is_active
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"message": "Template updated successfully", "id": template.id}


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully", "id": template_id}


@router.post("/upload")
async def upload_template_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_buyer_or_admin(current_user)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in [".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls is allowed")
    safe_name = Path(file.filename).name
    saved_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}_{safe_name}"
    saved_path = TEMPLATE_DIR / saved_name
    content = await file.read()
    saved_path.write_bytes(content)
    return {
        "message": "Template uploaded successfully",
        "file_path": f"static/templates/{saved_name}",
        "filename": saved_name,
    }
