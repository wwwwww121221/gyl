from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime
import asyncio

from models import (
    get_db, SessionLocal, InquirySupplier, InquiryTaskItem,
    Quotation, LinkStatus, InquiryRequest, TaskStatus, InquiryTask, Supplier, User
)
from schemas_supplier import QuoteSubmission, SupplierQuoteResponse, SupplierUpdate, SupplierContractInfoSubmit
from services.llm_factory import get_llm_service
from services.contract_service import generate_contract_pdf
from schemas import ChatMessage
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
        
    inquiries = db.query(InquirySupplier).filter(InquirySupplier.supplier_id == supplier.id).all()
    
    result = []
    for link in inquiries:
        task = db.query(InquiryTask).filter(InquiryTask.id == link.task_id).first()
        if not task:
            continue
            
        result.append({
            "inquiry_supplier_id": link.id,
            "task_id": task.id,
            "task_title": task.title,
            "status": link.status,
            "task_status": task.status,
            "current_round": link.current_round,
            "contract_pdf": link.contract_pdf,
            "contract_pdf_path": link.contract_pdf_path,
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
        "contract_pdf": link.contract_pdf,
        "contract_pdf_path": link.contract_pdf_path,
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

    link.address = payload.address
    link.legal_rep = payload.legal_rep
    link.agent = payload.agent
    link.phone = payload.phone
    link.bank_name = payload.bank_name
    link.bank_account = payload.bank_account
    link.tax_id = payload.tax_id
    db.commit()

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

    # 2. 检查期望价格自动成交
    strategy = link_task.strategy_config or {}
    max_rounds = strategy.get("max_rounds", 3)
    bargain_ratio = strategy.get("bargain_ratio", 0.05)

    all_meet_target = True
    has_target_price_set = False

    for q in quote_items:
        # 显式查询，避免 lazy load 报错
        t_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
        r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first() if t_item else None
        target_price = r_item.target_price if r_item else None
        
        if target_price is not None:
            has_target_price_set = True
            # 1. 价格高于期望价，不满足自动成交条件
            if q.price > target_price:
                all_meet_target = False
                break
            # 2. 熔断机制：价格异常过低（低于期望单价的50%），拦截自动成交，强制转为人工确认
            elif target_price > 0 and q.price <= target_price * 0.5:
                all_meet_target = False
                break
    
    if has_target_price_set and all_meet_target:
        link.status = LinkStatus.DEAL
        link_task.status = TaskStatus.CLOSED
        link.latest_ai_feedback = "感谢您的报价，本次询价已达成合作，请等待后续采购订单。"
        
        other_links = db.query(InquirySupplier).filter(
            InquirySupplier.task_id == link.task_id,
            InquirySupplier.id != link.id
        ).all()
        for ol in other_links:
            ol.status = LinkStatus.REJECT
            ol.latest_ai_feedback = "很遗憾，因其他供应商已达到我方期望目标，本次询价已结束。"
            
        db.commit()
        return {
            "message": "恭喜，您的报价已达到我们的期望目标，系统已自动确认成交！",
            "next_action": "deal",
            "ai_feedback": link.latest_ai_feedback
        }

    # 3. 检查是否所有活跃的供应商都已完成本轮报价
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

    # 4. 所有供应商均已报价，统一处理下一轮逻辑或结束
    current_round = link.current_round
    if current_round < max_rounds:
        llm = get_llm_service()
        
        # 为每个 QUOTED 的供应商生成反馈并进入下一轮
        # TODO: 实际生产中这里可以使用 asyncio.gather 并发调用，这里为了稳定先顺序调用或简单并发
        import asyncio
        
        async def process_link(l):
            # 获取该供应商本轮报价
            l_quotes = db.query(Quotation).filter(Quotation.inquiry_supplier_id == l.id, Quotation.round == current_round).all()
            if not l_quotes:
                return
                
            # 显式查询以避免 async def 中的 SQLAlchemy lazy load 问题
            item_summary_lines = []
            needs_manual_review = False
            anomaly_reason = ""
            
            for q in l_quotes:
                t_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
                r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first()
                item_summary_lines.append(f"- 物料名称 '{r_item.material_name}': 报价 ¥{q.price}")
                
                # 检查是否存在异常报价（双向防线：过低或过高）
                target_p = r_item.target_price if r_item else None
                if target_p is not None and target_p > 0:
                    if q.price <= target_p * 0.5:
                        needs_manual_review = True
                        anomaly_reason = "大幅低于期望基准（存在漏报或错报规格风险）"
                    elif q.price >= target_p * 1.5:
                        needs_manual_review = True
                        anomaly_reason = "大幅高于期望基准（存在错报单位或溢价过高风险）"
            
            # 1. 拦截大模型：如果存在异常报价，强制跳过 AI 自动砍价，锁入人工复核状态
            if needs_manual_review:
                l.latest_ai_feedback = f"⚠️ 系统预警：您的报价{anomaly_reason}。系统已暂停您的自动谈判流程，并转交采购员进行人工核对，请等待采购方主动联系。"
                l.current_round += 1
                l.status = LinkStatus.NEGOTIATION
                return
            
            # 2. 只有在正常价格区间内，才进行大模型 5% 的议价谈判逻辑
            item_summary = "\n".join(item_summary_lines)
            
            prompt = f"""
            你是一个专业的采购谈判专家。当前正在进行第 {current_round} 轮谈判（共 {max_rounds} 轮）。
            供应商提交了以下报价：
            {item_summary}
            
            我们的目标是基于当前价格再降低 {bargain_ratio*100}%。
            请生成一段回复给供应商，直接指出价格偏高，要求重新报价。
            语气要专业、礼貌但坚定。
            """
            try:
                response = await llm.chat_completion([
                    ChatMessage(role="system", content="你是一个采购智能体。"),
                    ChatMessage(role="user", content=prompt)
                ])
                l.latest_ai_feedback = response.content
                l.current_round += 1
                l.status = LinkStatus.NEGOTIATION
            except Exception as e:
                logger.error(f"LLM Error for link {l.id}: {e}")
                l.latest_ai_feedback = f"系统已收到报价，请基于目标再下调 {bargain_ratio*100}% 重新报价。"
                l.current_round += 1
                l.status = LinkStatus.NEGOTIATION

        quoted_links = [l for l in all_links if l.status == LinkStatus.QUOTED]
        await asyncio.gather(*(process_link(l) for l in quoted_links))
        db.commit()
        
        return {
            "message": "所有供应商报价已完成，已触发下一轮谈判。",
            "next_action": "re-quote",
            "ai_feedback": link.latest_ai_feedback
        }
        
    else:
        # 达到最大轮数，选择最低价
        best_link = None
        lowest_price = float('inf')
        
        for l in all_links:
            if l.status not in [LinkStatus.QUOTED, LinkStatus.DEAL]:
                continue
                
            quotes = db.query(Quotation).filter(
                Quotation.inquiry_supplier_id == l.id,
                Quotation.round == current_round
            ).all()
            
            if not quotes:
                continue
                
            l_total_price = 0
            for q in quotes:
                # 显式查询，避免 lazy load 报错
                t_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
                r_item = db.query(InquiryRequest).filter(InquiryRequest.id == t_item.request_id).first() if t_item else None
                qty = r_item.qty if r_item else 1
                l_total_price += q.price * qty
                
            if l_total_price < lowest_price:
                lowest_price = l_total_price
                best_link = l
        
        if best_link:
            best_link.status = LinkStatus.DEAL
            best_link.latest_ai_feedback = "感谢您的配合，本次询价已达成合作。"
            for l in all_links:
                if l.id != best_link.id and l.status != LinkStatus.DEAL:
                    l.status = LinkStatus.REJECT
                    l.latest_ai_feedback = "很遗憾，您的最终报价未能成为最低价，本次询价已结束。"
            link_task.status = TaskStatus.CLOSED
            db.commit()
            
            if best_link.id == link.id:
                return {
                    "message": "报价已结束。恭喜，您的报价为最低价，系统已自动确认成交！",
                    "next_action": "deal",
                    "ai_feedback": best_link.latest_ai_feedback
                }

        return {
            "message": "最终报价已收到，请等待比价结果或采购员审批。",
            "next_action": "wait",
            "ai_feedback": link.latest_ai_feedback
        }
