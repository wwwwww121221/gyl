from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    role: Optional[str] = "buyer"

class UserCreate(UserBase):
    password: str
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Inquiry Pool Schemas ---

class InquiryRequestBase(BaseModel):
    erp_request_id: str
    bill_no: Optional[str] = None
    bill_type: Optional[str] = None
    project_info: Optional[dict] = None
    material_code: str
    material_name: str
    qty: float
    delivery_date: Optional[datetime] = None

class InquiryRequestCreate(InquiryRequestBase):
    target_price: Optional[float] = None

class InquiryRequest(InquiryRequestBase):
    id: Optional[int] = None # Make id optional for non-persisted data
    status: str
    target_price: Optional[float] = None
    created_at: Optional[datetime] = None # Make optional

    class Config:
        from_attributes = True

# --- Task Schemas ---

class StrategyConfig(BaseModel):
    max_rounds: int = 3
    bargain_ratio: float = 0.05
    target_price_rule: Optional[dict] = None

class InquiryTaskBase(BaseModel):
    title: str
    strategy_config: Optional[StrategyConfig] = None
    deadline: Optional[datetime] = None

class InquiryTaskCreate(InquiryTaskBase):
    deadline: Optional[datetime] = None
    request_ids: Optional[List[int]] = None
    raw_requests: Optional[List[InquiryRequestCreate]] = None
    supplier_ids: Optional[List[int]] = None

class InquiryTask(InquiryTaskBase):
    deadline: Optional[datetime] = None
    id: int
    status: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# --- LLM Schemas ---

class ChatMessage(BaseModel):
    role: str
    content: str

class LLMResponse(BaseModel):
    content: str
    raw_response: Any = None
