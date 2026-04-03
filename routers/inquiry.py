from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, date

from models import (
    get_db, User, InquiryRequest, InquiryTask, InquiryTaskItem,
    Supplier, InquirySupplier, InquiryStatus, TaskStatus, LinkStatus, Quotation, Contract, ContractTemplate
)
from schemas import InquiryTaskCreate, InquiryTask as InquiryTaskSchema, StrategyConfig, InquiryRequest as InquiryRequestSchema
from routers.auth import oauth2_scheme, login_access_token # reuse auth but simpler dependency
from services.negotiation_service import calculate_supplier_scores

# 简单的用户获取依赖
from jose import jwt, JWTError
from core.config import settings

router = APIRouter()

class ManualInterventionPayload(BaseModel):
    message: Optional[str] = None


def _calc_link_total_amount(db: Session, link: InquirySupplier) -> float:
    quotes = db.query(Quotation).filter(
        Quotation.inquiry_supplier_id == link.id,
        Quotation.round == link.current_round
    ).all()
    if not quotes:
        quotes = db.query(Quotation).filter(
            Quotation.inquiry_supplier_id == link.id
        ).order_by(Quotation.round.desc(), Quotation.id.asc()).all()
        if quotes:
            max_round = quotes[0].round
            quotes = [q for q in quotes if q.round == max_round]
    total_amount = 0.0
    for q in quotes:
        task_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
        req = db.query(InquiryRequest).filter(InquiryRequest.id == task_item.request_id).first() if task_item else None
        qty = req.qty if req and req.qty is not None else (q.qty or 0)
        total_amount += float(q.price or 0) * float(qty or 0)
    return total_amount


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
    ).order_by(InquiryTask.id.desc()).offset(skip).limit(limit).all()



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

    today = datetime.now().date()
    score_input = []
    for link in task.suppliers:
        if link.status == LinkStatus.REJECT:
            continue
        current_round_quotes = [q for q in link.quotations if q.round == link.current_round]
        score_items = []
        for q in current_round_quotes:
            delivery_days = 0.0
            if isinstance(q.delivery_date, (datetime, date)):
                d_date = q.delivery_date.date() if isinstance(q.delivery_date, datetime) else q.delivery_date
                delivery_days = float((d_date - today).days)
                if delivery_days < 0:
                    delivery_days = 0.0
            elif q.delivery_date is not None:
                try:
                    delivery_days = float(q.delivery_date)
                    if delivery_days < 0:
                        delivery_days = 0.0
                except (TypeError, ValueError):
                    delivery_days = 0.0
            score_items.append({
                "price": float(q.price or 0),
                "qty": float(q.qty or 0),
                "delivery_days": delivery_days,
            })
        score_input.append({
            "supplier_id": link.id,
            "items": score_items,
        })

    score_rows = calculate_supplier_scores(score_input)
    score_map = {row.get("supplier_id"): row for row in score_rows}
    # 按照 1.综合得分(降序) 2.总价(升序) 3.交期(升序) 进行多级排序
    rank_candidates = sorted(
        score_rows,
        key=lambda row: (
            float(row.get("total_score", 0)),
            -float(row.get("total_price", 0)),
            -float(row.get("avg_delivery_days", 0))
        ),
        reverse=True
    )

    rank_map = {}
    for i, row in enumerate(rank_candidates):
        if i > 0:
            prev_row = rank_candidates[i - 1]
            # 如果三项核心指标完全一致，则赋予完全相同的名次（并列）
            if (float(row.get("total_score", 0)) == float(prev_row.get("total_score", 0)) and
                float(row.get("total_price", 0)) == float(prev_row.get("total_price", 0)) and
                float(row.get("avg_delivery_days", 0)) == float(prev_row.get("avg_delivery_days", 0))):
                rank_map[row.get("supplier_id")] = rank_map[prev_row.get("supplier_id")]
                continue
        # 否则按当前所处位置赋予标准名次（例如若有并列第一，下一个就是第三名）
        rank_map[row.get("supplier_id")] = i + 1

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

        score_info = score_map.get(link.id, {})
        links.append({
            "link_id": link.id,
            "supplier_name": link.supplier.name,
            "status": link.status,
            "current_round": link.current_round,
            "quotes": quotes_by_round,
            "total_price": float(score_info.get("total_price", 0)),
            "avg_delivery_days": float(score_info.get("avg_delivery_days", 0)),
            "price_score": float(score_info.get("price_score", 0)),
            "delivery_score": float(score_info.get("delivery_score", 0)),
            "total_score": float(score_info.get("total_score", 0)),
            "score_rank": rank_map.get(link.id)
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

    # === 新增：先删除关联的电子合同记录 ===
    from models import Quotation, Contract
    db.query(Contract).filter(Contract.task_id == task_id).delete()

    # 先删除相关的报价记录和供应商关联
    for link in task.suppliers:
        # 删除相关的 quotations
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    手动关闭询价任务。如果指定了 selected_link_id，则该供应商成交，其他淘汰。
    如果不指定，则按综合评分自动定标；若无有效候选则流标。
    """
    task = db.query(InquiryTask).filter(InquiryTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.CLOSED
    selected_link = None
    selected_link_key = selected_link_id

    for link in task.suppliers:
        if selected_link_key is not None and link.id == selected_link_key:
            link.status = LinkStatus.DEAL
            link.latest_ai_feedback = "恭喜，采购员已确认您中标，本次询价已达成合作。"
            selected_link = link
        else:
            link.status = LinkStatus.REJECT
            if selected_link_key is None:
                link.latest_ai_feedback = "本次询价任务已终止（流标），所有报价已作废，感谢您的参与。"
            else:
                link.latest_ai_feedback = "很遗憾，采购员最终选择了其他供应商，本次询价已结束。"

    if selected_link_key is not None and not selected_link:
        raise HTTPException(status_code=404, detail="Selected supplier link not found in this task")

    if selected_link:
        total_amount = _calc_link_total_amount(db, selected_link)
        active_template = db.query(ContractTemplate).filter(
            ContractTemplate.is_active == True
        ).order_by(ContractTemplate.id.desc()).first()
        contract_record = db.query(Contract).filter(
            Contract.inquiry_supplier_id == selected_link.id
        ).first()
        if not contract_record:
            contract_record = Contract(
                task_id=task.id,
                inquiry_supplier_id=selected_link.id,
                status="待供应商填写"
            )
        contract_record.total_amount = total_amount
        if active_template and active_template.default_buyer_name and not contract_record.buyer_company_name:
            contract_record.buyer_company_name = active_template.default_buyer_name
        db.add(contract_record)

    db.commit()
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
