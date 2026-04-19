from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from ..database import get_db
from ..models import Company, Ledger, Transaction
from ..schemas import CostBreakdownResponse, PnLSummaryResponse, LedgerResponse, BalanceSheetResponse
from ..services.analytics import calculate_cost_breakdown, calculate_pnl, calculate_balance_sheet
from ..services.tally_sync import pull_data_from_tally

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

# Usually you'd derive company_id from auth or request headers, fixing to 1 for demo
COMPANY_ID = 1

@router.post("/tally-pull")
def trigger_tally_pull(db: Session = Depends(get_db)):
    """Pulls data from connected Tally Server and saves it to the local analytics database."""
    # Ensure our demo company exists
    company = db.query(Company).filter(Company.id == COMPANY_ID).first()
    if not company:
        company = Company(name="Autara Demo Corp", tally_guid="GUID-123")
        db.add(company)
        db.commit()
    
    # Poll mock Tally Sync logic
    tally_data = pull_data_from_tally()
    
    # 1. Update Ledgers
    ledger_map = {} # Mapping ledger names to DB IDs
    for l_data in tally_data["ledgers"]:
        ledger = db.query(Ledger).filter(Ledger.company_id == COMPANY_ID, Ledger.name == l_data["name"]).first()
        if not ledger:
            ledger = Ledger(company_id=COMPANY_ID, name=l_data["name"], group=l_data["group"])
            db.add(ledger)
            db.commit()
            db.refresh(ledger)
        ledger_map[ledger.name] = ledger.id
        
    # 2. Ingest Transactions
    for t_data in tally_data["transactions"]:
        ledger_id = ledger_map.get(t_data["ledger_name"])
        if ledger_id:
            txn = Transaction(
                company_id=COMPANY_ID,
                ledger_id=ledger_id,
                date=datetime.utcnow(),
                amount=t_data["amount"],
                type=t_data["type"],
                voucher_type="Journal",
                narration="Pulled from Tally"
            )
            db.add(txn)
    
    db.commit()
    return {"status": "success", "message": "Imported ledgers and transactions from Tally"}

@router.get("/cost-breakdown", response_model=CostBreakdownResponse)
def get_cost_breakdown(db: Session = Depends(get_db)):
    """Returns a breakdown of direct vs indirect costs."""
    return calculate_cost_breakdown(db, COMPANY_ID)

@router.get("/pnl-summary", response_model=PnLSummaryResponse)
def get_pnl_summary(db: Session = Depends(get_db)):
    """Returns Gross and Net Profit summaries."""
    return calculate_pnl(db, COMPANY_ID)

@router.get("/balance-sheet", response_model=BalanceSheetResponse)
def get_balance_sheet(db: Session = Depends(get_db)):
    """Returns Assets, Liabilities, and Equity."""
    return calculate_balance_sheet(db, COMPANY_ID)

@router.get("/ledgers", response_model=list[LedgerResponse])
def get_ledgers(db: Session = Depends(get_db)):
    """Returns all Ledgers belonging to the company, including nested transactions."""
    from sqlalchemy.orm import selectinload
    
    # We use selectinload to eagerly fetch the nested transactions efficiently
    ledgers = db.query(Ledger).filter(
        Ledger.company_id == COMPANY_ID
    ).options(selectinload(Ledger.transactions)).all()
    
    return ledgers
