from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class QuoteItem(BaseModel):
    request_id: int
    qty: Optional[float] = None
    price: float
    delivery_date: Optional[datetime] = None
    remark: Optional[str] = None

class QuoteSubmission(BaseModel):
    items: List[QuoteItem]
    force_submit: Optional[bool] = False

class SupplierQuoteResponse(BaseModel):
    message: str
    next_action: str # "wait", "re-quote", "deal"
    ai_feedback: Optional[str] = None

class SupplierUpdate(BaseModel):
    status: Optional[str] = None
    level: Optional[str] = None


class SupplierContractInfoSubmit(BaseModel):
    address: str = Field(..., min_length=1)
    legal_rep: str = Field(..., min_length=1)
    agent: Optional[str] = None
    phone: str = Field(..., min_length=1)
    bank_name: str = Field(..., min_length=1)
    bank_account: str = Field(..., min_length=1)
    tax_id: str = Field(..., min_length=1)
    fax: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=1)
