from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class DocumentBase(BaseModel):
    vendor_name: Optional[str] = None
    suggested_group: Optional[str] = None
    gstin: Optional[str] = None
    pan_number: Optional[str] = None
    total_amount: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    tds: Optional[float] = None
    date: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(DocumentBase):
    status: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    filename: Optional[str] = None
    status: str
    calculated_taxes: Optional[Dict[str, Any]] = None
    missing_proofs: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    document_id: int
    user_id: str
    action: str
    data_snapshot: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True

# Analytics Schemas
class CostBreakdownResponse(BaseModel):
    direct_expenses: float
    indirect_expenses: float
    total_expenses: float
    details: Dict[str, float] # E.g., {"Raw Materials": 5000, "Electricity": 2000}

class PnLSummaryResponse(BaseModel):
    total_revenue: float
    direct_expenses: float
    indirect_expenses: float
    gross_profit: float
    net_profit: float

class BalanceSheetResponse(BaseModel):
    assets_total: float
    assets_details: Dict[str, float]
    liabilities_total: float
    liabilities_details: Dict[str, float]
    equity_total: float
    equity_details: Dict[str, float]

class TransactionResponse(BaseModel):
    id: int
    date: datetime
    amount: float
    type: str
    voucher_type: str
    narration: Optional[str] = None

    class Config:
        from_attributes = True

class LedgerResponse(BaseModel):
    id: int
    name: str
    group: str
    transactions: List[TransactionResponse] = []

    class Config:
        from_attributes = True
