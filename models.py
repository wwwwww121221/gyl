from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON, Enum, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 直接从环境变量读取，如果没有则提供一个备用默认值
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/supply_chain_agent")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- 枚举类型 ---

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    BUYER = "buyer"
    SUPPLIER = "supplier"

class InquiryStatus(str, enum.Enum):
    PENDING_POOL = "pending_pool"  # 在池中
    IN_PROCESS = "in_process"      # 处理中
    COMPLETED = "completed"        # 已完成

class TaskStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"

class LinkStatus(str, enum.Enum):
    SENT = "sent"            # 已发送
    QUOTED = "quoted"        # 已报价
    NEGOTIATION = "negotiation" # 谈判中
    DEAL = "deal"            # 成交
    REJECT = "reject"        # 拒绝/淘汰

# --- 数据库模型 ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default=UserRole.BUYER)
    created_at = Column(DateTime, default=datetime.now)

class InquiryRequest(Base):
    """
    询价需求池：从ERP拉取的快照数据
    """
    __tablename__ = "inquiry_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    erp_request_id = Column(String, index=True, comment="ERP采购申请单号+行号")
    bill_no = Column(String, index=True, comment="ERP单据编号") # 对应 FBILLNO
    project_info = Column(JSON, comment="项目信息 {number, name}")
    material_code = Column(String, index=True)
    material_name = Column(String)
    qty = Column(Float)
    target_price = Column(Float, nullable=True, comment="期望单价")
    delivery_date = Column(DateTime)
    status = Column(String, default=InquiryStatus.PENDING_POOL)
    created_at = Column(DateTime, default=datetime.now)

class InquiryTask(Base):
    """
    询价任务单：一次具体的询价活动
    """
    __tablename__ = "inquiry_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    strategy_config = Column(JSON, comment="谈判策略配置 {max_rounds, bargain_ratio...}")
    deadline = Column(DateTime, nullable=True, comment="询价截止时间")
    status = Column(String, default=TaskStatus.DRAFT)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    creator = relationship("User")
    items = relationship("InquiryTaskItem", back_populates="task")
    suppliers = relationship("InquirySupplier", back_populates="task")
    contracts = relationship("Contract", back_populates="task")

class InquiryTaskItem(Base):
    """
    任务与需求的关联表
    """
    __tablename__ = "inquiry_task_items"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("inquiry_tasks.id"))
    request_id = Column(Integer, ForeignKey("inquiry_requests.id"))
    
    task = relationship("InquiryTask", back_populates="items")
    request = relationship("InquiryRequest")

class Supplier(Base):
    """
    供应商库
    """
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    level = Column(String, default="general", comment="general/core")
    status = Column(String, default="approved", comment="pending/approved/rejected")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rating_score = Column(Float, default=0.0)

    user = relationship("User", backref="supplier_profile")

class InquirySupplier(Base):
    """
    询价任务与供应商的关联状态
    """
    __tablename__ = "inquiry_suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("inquiry_tasks.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    current_round = Column(Integer, default=1)
    status = Column(String, default=LinkStatus.SENT)
    latest_ai_feedback = Column(Text, nullable=True, comment="最新的AI谈判反馈")
    contract_pdf = Column(String, nullable=True)
    contract_pdf_path = Column(String, nullable=True)
    address = Column(String, nullable=True)
    legal_rep = Column(String, nullable=True)
    agent = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    fax = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    task = relationship("InquiryTask", back_populates="suppliers")
    supplier = relationship("Supplier")
    quotations = relationship("Quotation", back_populates="inquiry_supplier")
    contracts = relationship("Contract", back_populates="inquiry_supplier")

class Quotation(Base):
    """
    报价记录
    """
    __tablename__ = "quotations"
    
    id = Column(Integer, primary_key=True, index=True)
    inquiry_supplier_id = Column(Integer, ForeignKey("inquiry_suppliers.id"))
    round = Column(Integer, nullable=False)
    item_id = Column(Integer, ForeignKey("inquiry_task_items.id"))
    qty = Column(Float, nullable=True, comment="供应商可供数量")
    price = Column(Float, nullable=False)
    delivery_date = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)
    ai_analysis = Column(JSON, nullable=True, comment="AI分析结果")
    created_at = Column(DateTime, default=datetime.now)

    inquiry_supplier = relationship("InquirySupplier", back_populates="quotations")
    item = relationship("InquiryTaskItem") # 关联到具体的任务明细项 (从而知道是对哪个物料报价)

class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (UniqueConstraint("inquiry_supplier_id", name="uq_contracts_inquiry_supplier_id"),)
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("inquiry_tasks.id"), nullable=False)
    inquiry_supplier_id = Column(Integer, ForeignKey("inquiry_suppliers.id"), nullable=False)
    pdf_path = Column(Text, nullable=False)
    status = Column(String, default="generated")
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    task = relationship("InquiryTask", back_populates="contracts")
    inquiry_supplier = relationship("InquirySupplier", back_populates="contracts")
    generator = relationship("User")

class SupplierMetric(Base):
    """
    供应商绩效指标
    """
    __tablename__ = "supplier_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    task_id = Column(Integer, ForeignKey("inquiry_tasks.id"))
    response_time_minutes = Column(Integer)
    total_rounds = Column(Integer)
    final_deal_rate = Column(Float)
    price_competitiveness = Column(Float)
    created_at = Column(DateTime, default=datetime.now)

class WarningMessage(Base):
    """
    采购员发给供应商的预警消息
    """
    __tablename__ = "warning_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    is_read = Column(Boolean, default=False)
    
    supplier = relationship("Supplier")

# 依赖注入 Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
