from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any
import logging

from models import get_db, InquiryRequest, InquiryStatus
from schemas import InquiryRequest as InquiryRequestSchema
from kingdee_erp_tool.services.purchase import get_processed_purchase_data
from kingdee_erp_tool.services.inventory import get_inventory_warning_data

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/requisitions", response_model=List[InquiryRequestSchema])
def sync_purchase_requisitions(
    db: Session = Depends(get_db)
) -> Any:
    """
    从 ERP 获取采购申请单数据（不保存到数据库，仅返回给前端展示）
    """
    try:
        # 1. 从 ERP 拉取数据
        erp_data = get_processed_purchase_data()
        
        display_items = []
        for item in erp_data:
            bill_no = item.get("bill_no", "")
            material_id = item.get("material_id", "")
            unique_key = f"{bill_no}_{material_id}" 
            
            # 创建临时对象，不存库
            temp_request = InquiryRequestSchema(
                erp_request_id=unique_key,
                bill_no=bill_no,
                bill_type=item.get("bill_type"),
                project_info={
                    "number": item.get("project_number"),
                    "name": item.get("project_name")
                },
                material_code=material_id,
                material_name=item.get("material_name"),
                qty=item.get("purchase_qty", 0),
                delivery_date=item.get("delivery_date"),
                status=InquiryStatus.PENDING_POOL,
                id=None, # No ID yet
                created_at=item.get("created_date")
            )
            display_items.append(temp_request)
        
        return display_items
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"ERP Sync failed: {str(e)}")

@router.get("/pool", response_model=List[InquiryRequestSchema])
def get_inquiry_pool(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取本地需求池列表
    """
    return db.query(InquiryRequest).filter(
        InquiryRequest.status == InquiryStatus.PENDING_POOL
    ).offset(skip).limit(limit).all()
