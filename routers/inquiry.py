from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
import uuid
import asyncio
import logging

from models import (
    get_db, SessionLocal, User, InquiryRequest, InquiryTask, InquiryTaskItem, 
    Supplier, InquirySupplier, InquiryStatus, TaskStatus, LinkStatus
)
from schemas import InquiryTaskCreate, InquiryTask as InquiryTaskSchema, StrategyConfig, InquiryRequest as InquiryRequestSchema
from routers.auth import oauth2_scheme, login_access_token # reuse auth but simpler dependency
from services.contract_service import generate_contract_pdf

# 简单的用户获取依赖
from jose import jwt, JWTError
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

class ManualInterventionPayload(BaseModel):
    message: Optional[str] = None


def _generate_contract_pdf_background(inquiry_id: int) -> None:
    db = SessionLocal()
    try:
        asyncio.run(generate_contract_pdf(db, inquiry_id))
    except Exception:
        logger.exception("合同生成失败, inquiry_id=%s", inquiry_id)
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/tasks", response_model=InquiryTaskSchema)
def create_inquiry_task(
    task_in: InquiryTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    创建询价任务：
    1. 接收原始需求列表（raw_requests）
    2. 将这些需求持久化到数据库（如果尚未存在）
    3. 创建任务并关联这些需求
    """
    request_ids = []
    
    # 1. 处理原始需求数据（如果提供）
    if task_in.raw_requests:
        for raw_req in task_in.raw_requests:
            # 检查是否存在
            existing = db.query(InquiryRequest).filter(
                InquiryRequest.erp_request_id == raw_req.erp_request_id
            ).first()
            
            if existing:
                # 更新状态
                if existing.status == InquiryStatus.PENDING_POOL:
                    existing.status = InquiryStatus.IN_PROCESS
                # 更新期望价格（如果提供）
                if getattr(raw_req, 'target_price', None) is not None:
                    existing.target_price = raw_req.target_price
                request_ids.append(existing.id)
            else:
                # 创建新记录
                new_req = InquiryRequest(
                    erp_request_id=raw_req.erp_request_id,
                    bill_no=raw_req.bill_no,
                    project_info=raw_req.project_info,
                    material_code=raw_req.material_code,
                    material_name=raw_req.material_name,
                    qty=raw_req.qty,
                    target_price=getattr(raw_req, 'target_price', None),
                    delivery_date=raw_req.delivery_date,
                    status=InquiryStatus.IN_PROCESS
                )
                db.add(new_req)
                db.flush()
                request_ids.append(new_req.id)
    
    # 兼容旧逻辑：如果直接传了 request_ids
    if task_in.request_ids:
        for rid in task_in.request_ids:
            if rid not in request_ids:
                request_ids.append(rid)
    
    if not request_ids:
        raise HTTPException(status_code=400, detail="No valid requests provided")

    # 2. 创建任务
    new_task = InquiryTask(
        title=task_in.title,
        strategy_config=task_in.strategy_config.dict() if task_in.strategy_config else {},
        deadline=task_in.deadline,
        status=TaskStatus.ACTIVE,
        created_by=current_user.id
    )
    db.add(new_task)
    db.flush()

    # 3. 创建关联项
    for rid in request_ids:
        # 确保请求状态已更新（对于仅传ID的情况）
        req = db.query(InquiryRequest).get(rid)
        if req:
            if req.status == InquiryStatus.PENDING_POOL:
                req.status = InquiryStatus.IN_PROCESS
            
            # 如果在 task_in 的 raw_requests 中找到了对应的目标价格，更新它
            if task_in.raw_requests:
                for raw_req in task_in.raw_requests:
                    if (getattr(raw_req, 'id', None) == rid) or (raw_req.erp_request_id == req.erp_request_id):
                        if getattr(raw_req, 'target_price', None) is not None:
                            req.target_price = raw_req.target_price
                        if getattr(raw_req, 'qty', None) is not None:
                            req.qty = raw_req.qty
                        if getattr(raw_req, 'delivery_date', None) is not None:
                            req.delivery_date = raw_req.delivery_date
                        break
            
        item = InquiryTaskItem(
            task_id=new_task.id,
            request_id=rid
        )
        db.add(item)
    
    # 4. 如果传了供应商ID，自动创建关联
    if getattr(task_in, 'supplier_ids', None):
        for sup_id in task_in.supplier_ids:
            supplier = db.query(Supplier).get(sup_id)
            if supplier:
                link = InquirySupplier(
                    task_id=new_task.id,
                    supplier_id=supplier.id,
                    status=LinkStatus.SENT
                )
                db.add(link)

    db.commit()
    db.refresh(new_task)
    return new_task

@router.post("/tasks/{task_id}/suppliers")
def add_supplier_to_task(
    task_id: int,
    supplier_name: str,
    contact_person: str = None,
    phone: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    为询价任务添加供应商
    """
    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 1. 查找或创建供应商
    supplier = db.query(Supplier).filter(Supplier.name == supplier_name).first()
    if not supplier:
        supplier = Supplier(
            name=supplier_name,
            contact_person=contact_person,
            phone=phone
        )
        db.add(supplier)
        db.flush()

    # 2. 检查是否已经添加
    existing_link = db.query(InquirySupplier).filter(
        InquirySupplier.task_id == task_id,
        InquirySupplier.supplier_id == supplier.id
    ).first()
    if existing_link:
        raise HTTPException(status_code=400, detail="Supplier already added to this task")

    # 3. 创建关联
    new_link = InquirySupplier(
        task_id=task.id,
        supplier_id=supplier.id,
        status=LinkStatus.SENT
    )
    db.add(new_link)
    db.commit()
    
    return {"message": "Supplier added successfully"}

@router.get("/tasks", response_model=List[InquiryTaskSchema])
def get_my_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取我的询价任务列表
    """
    return db.query(InquiryTask).filter(
        InquiryTask.created_by == current_user.id
    ).offset(skip).limit(limit).all()



@router.get("/tasks/{task_id}/details")
def get_task_details(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取任务的详细信息，包含需求项、供应商链接、以及每轮报价
    """
    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    items = []
    for item in task.items:
        items.append({
            "id": item.id,
            "material_name": item.request.material_name,
            "material_code": item.request.material_code,
            "qty": item.request.qty,
            "target_price": item.request.target_price,
            "delivery_date": item.request.delivery_date
        })

    # 建立任务明细项(item_id)到期望单价(target_price)的映射
    target_price_map = {item.id: item.request.target_price for item in task.items if item.request.target_price is not None}

    links = []
    for link in task.suppliers:
        quotes_by_round = {}
        for q in link.quotations:
            if q.round not in quotes_by_round:
                quotes_by_round[q.round] = []
            
            target_p = target_price_map.get(q.item_id)
            is_anomaly = False
            anomaly_reason = ""
            
            # 完全以期望单价作为唯一基准进行异常检测
            if target_p is not None and target_p > 0:
                if q.price <= target_p * 0.5:
                    is_anomaly = True
                    anomaly_reason = "异常低价：低于期望单价 50% 以上，存在错报风险"
                elif q.price >= target_p * 1.5:
                    is_anomaly = True
                    anomaly_reason = "异常高价：大幅偏离期望单价，请警惕溢价风险"
            quotes_by_round[q.round].append({
                "item_id": q.item_id,
                "qty": q.qty,
                "price": q.price,
                "delivery_date": q.delivery_date,
                "remark": q.remark,
                "is_anomaly": is_anomaly,
                "anomaly_reason": anomaly_reason
            })

        links.append({
            "link_id": link.id,
            "supplier_name": link.supplier.name,
            "status": link.status,
            "current_round": link.current_round,
            "quotes": quotes_by_round
        })

    return {
        "id": task.id,
        "title": task.title,
        "deadline": task.deadline,
        "status": task.status,
        "strategy_config": task.strategy_config,
        "items": items,
        "links": links
    }

@router.delete("/tasks/{task_id}")
def delete_inquiry_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    删除已关闭的询价任务
    """
    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != TaskStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Only closed tasks can be deleted")
        
    # 先删除相关的报价记录和供应商关联
    for link in task.suppliers:
        # 删除相关的 quotations
        from models import Quotation
        db.query(Quotation).filter(Quotation.inquiry_supplier_id == link.id).delete()
        db.delete(link)
        
    # 删除相关的 task items
    for item in task.items:
        # 将关联的需求池状态重置
        if item.request:
            item.request.status = InquiryStatus.PENDING_POOL
        db.delete(item)
        
    # 删除任务本身
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}
@router.post("/tasks/{task_id}/close")
def close_inquiry_task(
    task_id: int,
    selected_link_id: Optional[int] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    手动关闭询价任务。如果指定了 selected_link_id，则该供应商成交，其他淘汰。
    如果不指定，则直接关闭（流标）。
    """
    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.CLOSED
    selected_link = None

    for link in task.suppliers:
        if selected_link_id and link.id == selected_link_id:
            link.status = LinkStatus.DEAL
            selected_link = link
        else:
            if link.status not in [LinkStatus.REJECT, LinkStatus.DEAL]:
                link.status = LinkStatus.REJECT

    if selected_link_id and not selected_link:
        raise HTTPException(status_code=404, detail="Selected supplier link not found in this task")

    db.commit()
    if selected_link and background_tasks:
        background_tasks.add_task(_generate_contract_pdf_background, selected_link.id)
    return {"message": "Task closed successfully."}

@router.post("/tasks/{task_id}/links/{link_id}/manual-continue")
def manual_continue_negotiation(
    task_id: int,
    link_id: int,
    payload: ManualInterventionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    link = db.query(InquirySupplier).filter(
        InquirySupplier.id == link_id,
        InquirySupplier.task_id == task_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Supplier link not found")

    if task.status != TaskStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Task is not active")

    link.status = LinkStatus.NEGOTIATION
    link.latest_ai_feedback = payload.message or "采购员已人工复核报价，请基于目标区间重新提交报价。"
    db.commit()
    return {"message": "已人工确认，供应商可继续谈判。"}

@router.post("/tasks/{task_id}/links/{link_id}/manual-reject")
def manual_reject_link(
    task_id: int,
    link_id: int,
    payload: ManualInterventionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    link = db.query(InquirySupplier).filter(
        InquirySupplier.id == link_id,
        InquirySupplier.task_id == task_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Supplier link not found")

    link.status = LinkStatus.REJECT
    link.latest_ai_feedback = payload.message or "经采购员人工复核，当前报价不满足要求，本轮已终止。"
    db.commit()
    return {"message": "已人工淘汰该供应商。"}
