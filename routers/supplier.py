from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime, date
import asyncio

from models import (
    get_db, SessionLocal, InquirySupplier, InquiryTaskItem,
    Quotation, LinkStatus, InquiryRequest, TaskStatus, InquiryTask, Supplier, User, Contract, ContractTemplate
)
from schemas_supplier import QuoteSubmission, SupplierQuoteResponse, SupplierUpdate, SupplierContractInfoSubmit
from services.contract_service import generate_contract_pdf
from services.negotiation_service import calculate_bargain_feedback, calculate_supplier_scores
import logging
from routers.inquiry import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_contract_pdf_background(inquiry_id: int) -> None:
    db = SessionLocal()
    try:
        asyncio.run(generate_contract_pdf(db, inquiry_id))
    except Exception:
        logger.exception("合同生成失败, inquiry_id=%s", inquiry_id)
    finally:
        db.close()

@router.get("/list")
def get_supplier_list(db: Session = Depends(get_db)):
    """
    采购员获取所有供应商列表（用于选择派发询价及供应商管理）
    """
    suppliers = db.query(Supplier).all()
    return [{
        "id": s.id, 
        "name": s.name, 
        "contact_person": s.contact_person, 
        "phone": s.phone,
        "email": s.email,
        "level": s.level, 
        "status": s.status
    } for s in suppliers]

@router.put("/{supplier_id}")
def update_supplier(
    supplier_id: int, 
    supplier_update: SupplierUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    采购员审核/定级供应商
    """
    if current_user.role not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    if supplier_update.status:
        supplier.status = supplier_update.status
    if supplier_update.level:
        supplier.level = supplier_update.level
        
    db.commit()
    db.refresh(supplier)
    return {"message": "Supplier updated successfully", "id": supplier.id, "status": supplier.status, "level": supplier.level}

@router.get("/my-inquiries")
def get_my_inquiries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    供应商登录后获取自己的询价任务列表
    """
    if current_user.role != "supplier":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")
        
    inquiries = db.query(InquirySupplier).filter(
        InquirySupplier.supplier_id == supplier.id
    ).order_by(InquirySupplier.id.desc()).all()
    
    result = []
    for link in inquiries:
        task = db.query(InquiryTask).filter(InquiryTask.id == link.task_id).first()
        if not task:
            continue
        contract_record = db.query(Contract).filter(Contract.inquiry_supplier_id == link.id).first()
        contract_pdf_path = contract_record.pdf_path if contract_record else None
            
        result.append({
            "inquiry_supplier_id": link.id,
            "task_id": task.id,
            "task_title": task.title,
            "status": link.status,
            "task_status": task.status,
            "current_round": link.current_round,
            "contract_pdf": contract_pdf_path,
            "contract_pdf_path": contract_pdf_path,
            "created_at": link.created_at
        })
        
    return result

@router.get("/inquiry/{inquiry_supplier_id}")
def get_inquiry_details(
    inquiry_supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    供应商获取特定询价单的明细（用于报价）
    """
    if current_user.role != "supplier":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
    
    link = db.query(InquirySupplier).filter(
        InquirySupplier.id == inquiry_supplier_id,
        InquirySupplier.supplier_id == supplier.id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Inquiry not found")
        
    task = db.query(InquiryTask).filter(InquiryTask.id == link.task_id).first()
    contract_record = db.query(Contract).filter(Contract.inquiry_supplier_id == link.id).first()
    contract_pdf_path = contract_record.pdf_path if contract_record else None
    
    items = []
    for item in task.items:
        items.append({
            "request_id": item.request_id,
            "material_name": item.request.material_name,
            "material_code": item.request.material_code,
            "qty": item.request.qty,
            "delivery_date": item.request.delivery_date,
            "project_name": item.request.project_info.get("name") if item.request.project_info else ""
        })
        
    return {
        "task_title": task.title,
        "task_status": task.status,
        "deadline": task.deadline,
        "round": link.current_round,
        "status": link.status,
        "latest_ai_feedback": link.latest_ai_feedback,
        "contract_pdf": contract_pdf_path,
        "contract_pdf_path": contract_pdf_path,
        "items": items
    }


@router.post("/inquiries/{inquiry_id}/confirm-contract")
def confirm_contract(
    inquiry_id: int,
    payload: SupplierContractInfoSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    if current_user.role != "supplier":
        raise HTTPException(status_code=403, detail="Not authorized")

    supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")

    link = db.query(InquirySupplier).filter(
        InquirySupplier.id == inquiry_id,
        InquirySupplier.supplier_id == supplier.id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if link.status != LinkStatus.DEAL:
        raise HTTPException(status_code=400, detail="Only deal inquiry can confirm contract")

    contract_record = db.query(Contract).filter(Contract.inquiry_supplier_id == link.id).first()
    if not contract_record:
        contract_record = Contract(
            task_id=link.task_id,
            inquiry_supplier_id=link.id,
            status="pending"
        )
    contract_record.address = payload.address
    contract_record.legal_representative = payload.legal_representative
    contract_record.agent = payload.agent
    contract_record.contact_phone = payload.contact_phone
    contract_record.bank_name = payload.bank_name
    contract_record.bank_account = payload.bank_account
    contract_record.tax_id = payload.tax_id
    contract_record.fax = payload.fax
    contract_record.postal_code = payload.postal_code
    if payload.buyer_company_name:
        contract_record.buyer_company_name = payload.buyer_company_name
    if contract_record.pdf_path:
        history_versions = list(contract_record.history_versions or [])
        history_versions.append({
            "pdf_path": contract_record.pdf_path,
            "generated_at": datetime.now().isoformat(),
            "event": "supplier_resubmitted"
        })
        contract_record.history_versions = history_versions
        contract_record.pdf_path = None
    contract_record.status = "待供应商填写"
    db.add(contract_record)
    db.commit()
    db.refresh(contract_record)

    background_tasks.add_task(_generate_contract_pdf_background, link.id)
    return {"message": "合同信息已提交，正在生成合同", "inquiry_id": link.id}

@router.post("/inquiry/{inquiry_supplier_id}/quote", response_model=SupplierQuoteResponse)
async def submit_quote(
    inquiry_supplier_id: int,
    submission: QuoteSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    供应商提交报价
    """
    if current_user.role != "supplier":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
    
    link = db.query(InquirySupplier).filter(
        InquirySupplier.id == inquiry_supplier_id,
        InquirySupplier.supplier_id == supplier.id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    link_task = db.query(InquiryTask).filter(InquiryTask.id == link.task_id).first()
    if not link_task:
        raise HTTPException(status_code=404, detail="Inquiry task not found")

    if link_task.deadline and datetime.now() > link_task.deadline:
        raise HTTPException(status_code=400, detail="Inquiry deadline has passed. Quotation submission is closed.")
        
    if link.status == LinkStatus.DEAL or link.status == LinkStatus.REJECT:
        raise HTTPException(status_code=400, detail="Inquiry is already closed for you.")

    if link.status == LinkStatus.QUOTED:
        quote_items = db.query(Quotation).filter(
            Quotation.inquiry_supplier_id == link.id,
            Quotation.round == link.current_round
        ).all()
    elif link.status in [LinkStatus.SENT, LinkStatus.NEGOTIATION]:
        # === 新增：异常报价前置预检 ===
        if not getattr(submission, 'force_submit', False):
            anomaly_names = []
            for item in submission.items:
                # 预查期望价
                t_item = db.query(InquiryTaskItem).filter(
                    InquiryTaskItem.task_id == link.task_id,
                    InquiryTaskItem.request_id == item.request_id
                ).first()
                r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first() if t_item else None
                
                if r_item and r_item.target_price and r_item.target_price > 0:
                    # 如果报价偏离期望价 50% 以上，记录异常
                    if item.price <= r_item.target_price * 0.5 or item.price >= r_item.target_price * 1.5:
                        anomaly_names.append(r_item.material_name)
            
            # 如果发现异常，拦截提交并返回特定 action 让前端弹窗
            if anomaly_names:
                names_str = ", ".join(anomaly_names[:3]) + (" 等" if len(anomaly_names) > 3 else "")
                return {
                    "message": f"预警：系统检测到【{names_str}】的报价大幅偏离常规预期，请仔细核对是否报错了规格或单位。如确认无误，请在弹窗中强行提交。",
                    "next_action": "confirm_anomaly",
                    "ai_feedback": ""
                }
        # === 预检结束 ===

        quote_items = []
        for item in submission.items:
            task_item = db.query(InquiryTaskItem).filter(
                InquiryTaskItem.task_id == link.task_id,
                InquiryTaskItem.request_id == item.request_id
            ).first()
            
            if task_item:
                quote = Quotation(
                    inquiry_supplier_id=link.id,
                    round=link.current_round,
                    item_id=task_item.id,
                    qty=item.qty,
                    price=item.price,
                    delivery_date=item.delivery_date,
                    remark=item.remark
                )
                db.add(quote)
                quote_items.append(quote)
        
        link.status = LinkStatus.QUOTED
        db.commit() # 先提交报价记录
    else:
        raise HTTPException(status_code=400, detail="Current link status does not allow quoting.")

    # 2. 检查是否所有活跃的供应商都已完成本轮报价
    all_links = db.query(InquirySupplier).filter(InquirySupplier.task_id == link.task_id).all()
    
    # 获取本轮还在参与的供应商 (状态是 SENT, NEGOTIATION 或 QUOTED)
    # 如果有人还是 SENT 或 NEGOTIATION，说明他还没报完
    all_quoted = True
    for l in all_links:
        if l.status in [LinkStatus.SENT, LinkStatus.NEGOTIATION]:
            all_quoted = False
            break
            
    if not all_quoted:
        link.latest_ai_feedback = "已收到您的报价。目前正在等待其他供应商完成本轮报价，待所有供应商报价完成后，系统将统一下发反馈，请耐心等待。"
        db.commit()
        return {
            "message": "报价已收到，等待其他供应商完成。",
            "next_action": "wait",
            "ai_feedback": link.latest_ai_feedback
        }

    # 3. 所有供应商均已报价，统一处理下一轮逻辑或结束
    strategy = link_task.strategy_config or {}
    max_rounds = strategy.get("max_rounds", 3)
    current_round = link.current_round
    if current_round < max_rounds:
        market_quotes = (
            db.query(Quotation)
            .join(InquirySupplier, Quotation.inquiry_supplier_id == InquirySupplier.id)
            .filter(
                InquirySupplier.task_id == link.task_id,
                InquirySupplier.status != LinkStatus.REJECT,
                Quotation.round == current_round
            )
            .all()
        )
        market_min_price_map = {}
        for mq in market_quotes:
            price = float(mq.price or 0)
            if price <= 0:
                continue
            if mq.item_id not in market_min_price_map or price < market_min_price_map[mq.item_id]:
                market_min_price_map[mq.item_id] = price

        def process_link(l):
            # 获取该供应商本轮报价
            l_quotes = db.query(Quotation).filter(Quotation.inquiry_supplier_id == l.id, Quotation.round == current_round).all()
            if not l_quotes:
                return
                
            feedback_lines = []
            
            for q in l_quotes:
                t_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
                r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first()
                target_price = float(r_item.target_price) if r_item and r_item.target_price is not None else 0.0
                market_min_price = float(market_min_price_map.get(q.item_id, q.price or 0))
                drop_ratio, suggested_price, feedback = calculate_bargain_feedback(
                    target_price=target_price,
                    market_min_price=market_min_price,
                    current_price=float(q.price or 0),
                    current_round=current_round,
                    max_rounds=max_rounds,
                )
                material_name = r_item.material_name if r_item else f"物料#{q.item_id}"
                if feedback:
                    feedback_lines.append(
                        f"{material_name}：当前报价{float(q.price or 0):.4f}元，建议下调{drop_ratio * 100:.2f}%至{suggested_price:.4f}元。"
                    )
                else:
                    feedback_lines.append(
                        f"{material_name}：当前报价{float(q.price or 0):.4f}元，已接近目标区间，可保持或小幅优化。"
                    )

            l.latest_ai_feedback = "系统已完成本轮价格分析，请参考以下建议进行下一轮报价：\n" + "\n".join(feedback_lines)
            l.current_round += 1
            l.status = LinkStatus.NEGOTIATION

        quoted_links = [l for l in all_links if l.status == LinkStatus.QUOTED]
        for l in quoted_links:
            process_link(l)
        db.commit()
        
        return {
            "message": "所有供应商报价已完成，已触发下一轮谈判。",
            "next_action": "re-quote",
            "ai_feedback": link.latest_ai_feedback
        }
        
    else:
        # 达到最大轮数，按综合评分自动定标
        today = datetime.now().date()
        score_input = []
        best_link = None

        for l in all_links:
            if l.status not in [LinkStatus.QUOTED, LinkStatus.DEAL]:
                continue

            quotes = db.query(Quotation).filter(
                Quotation.inquiry_supplier_id == l.id,
                Quotation.round == current_round
            ).all()

            if not quotes:
                continue

            score_items = []
            for q in quotes:
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
            score_input.append({"supplier_id": l.id, "items": score_items})

        score_rows = calculate_supplier_scores(score_input)
        if score_rows:
            best_row = max(score_rows, key=lambda row: float(row.get("total_score", 0)))
            best_supplier_id = best_row.get("supplier_id")
            for l in all_links:
                if l.id == best_supplier_id:
                    best_link = l
                    break

        if best_link:
            best_link.status = LinkStatus.DEAL
            best_link.latest_ai_feedback = "感谢您的配合，本次询价已达成合作。"
            best_quotes = db.query(Quotation).filter(
                Quotation.inquiry_supplier_id == best_link.id,
                Quotation.round == current_round
            ).all()
            total_amount = 0.0
            for q in best_quotes:
                t_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
                r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first() if t_item else None
                qty = r_item.qty if r_item and r_item.qty is not None else (q.qty or 0)
                total_amount += float(q.price or 0) * float(qty or 0)
            active_template = db.query(ContractTemplate).filter(
                ContractTemplate.is_active == True
            ).order_by(ContractTemplate.id.desc()).first()
            contract_record = db.query(Contract).filter(
                Contract.inquiry_supplier_id == best_link.id
            ).first()
            if not contract_record:
                contract_record = Contract(
                    task_id=best_link.task_id,
                    inquiry_supplier_id=best_link.id,
                    status="待供应商填写"
                )
            contract_record.total_amount = total_amount
            if active_template and active_template.default_buyer_name and not contract_record.buyer_company_name:
                contract_record.buyer_company_name = active_template.default_buyer_name
            db.add(contract_record)
            for l in all_links:
                if l.id != best_link.id and l.status != LinkStatus.DEAL:
                    l.status = LinkStatus.REJECT
                    l.latest_ai_feedback = "很遗憾，您的综合评分未能排名第一，本次询价已结束。"
            link_task.status = TaskStatus.CLOSED
            db.commit()
            
            if best_link.id == link.id:
                return {
                    "message": "报价已结束。恭喜，您的综合评分排名第一，系统已自动确认成交！",
                    "next_action": "deal",
                    "ai_feedback": best_link.latest_ai_feedback
                }

        return {
            "message": "最终报价已收到，请等待比价结果或采购员审批。",
            "next_action": "wait",
            "ai_feedback": link.latest_ai_feedback
        }
