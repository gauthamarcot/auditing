from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from ..database import get_db
from ..models import Company, Ledger, Transaction
from ..schemas import CostBreakdownResponse, PnLSummaryResponse, LedgerResponse, BalanceSheetResponse, CompanyCreate, CompanyResponse
from ..services.analytics import calculate_cost_breakdown, calculate_pnl, calculate_balance_sheet
from ..services.tally_sync import pull_data_from_tally

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

@router.get("/companies", response_model=list[CompanyResponse])
def get_companies(db: Session = Depends(get_db)):
    """Fetch all registered companies for multi-tenant switching."""
    return db.query(Company).all()

@router.post("/companies", response_model=CompanyResponse)
def create_company(company_in: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new multi-tenant company with an auto-generated GUID."""
    import uuid
    new_guid = f"GUID-{uuid.uuid4().hex[:8]}"
    company = Company(name=company_in.name, tally_guid=new_guid)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.post("/tally-pull")
def trigger_tally_pull(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Pulls data from connected Tally Server and saves it to the local analytics database."""
    # Ensure our demo company exists
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        # Use simple mock name if not created
        mock_name = "Autara Demo Corp" if company_id == 1 else "Acme Industries"
        company = Company(id=company_id, name=mock_name, tally_guid=f"GUID-{company_id}")
        db.add(company)
        db.commit()
    
    # Poll mock Tally Sync logic
    tally_data = pull_data_from_tally()
    
    # 1. Update Ledgers
    ledger_map = {} # Mapping ledger names to DB IDs
    for l_data in tally_data["ledgers"]:
        ledger = db.query(Ledger).filter(Ledger.company_id == company_id, Ledger.name == l_data["name"]).first()
        if not ledger:
            ledger = Ledger(company_id=company_id, name=l_data["name"], group=l_data["group"])
            db.add(ledger)
            db.commit()
            db.refresh(ledger)
        ledger_map[ledger.name] = ledger.id
        
    # 2. Ingest Transactions
    for t_data in tally_data["transactions"]:
        ledger_id = ledger_map.get(t_data["ledger_name"])
        if ledger_id:
            # Check if tally_sync provided a mock date for MoM charts
            t_date = t_data.get("date")
            if t_date and isinstance(t_date, str):
                t_date = datetime.strptime(t_date, "%Y-%m-%d")
            else:
                t_date = datetime.utcnow()
                
            txn = Transaction(
                company_id=company_id,
                ledger_id=ledger_id,
                date=t_date,
                amount=t_data["amount"],
                type=t_data["type"],
                voucher_type="Journal",
                narration="Pulled from Tally"
            )
            db.add(txn)
    
    db.commit()
    return {"status": "success", "message": "Imported ledgers and transactions from Tally"}

@router.get("/cost-breakdown", response_model=CostBreakdownResponse)
def get_cost_breakdown(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Returns a breakdown of direct vs indirect costs."""
    return calculate_cost_breakdown(db, company_id)

@router.get("/pnl-summary", response_model=PnLSummaryResponse)
def get_pnl_summary(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Returns Gross and Net Profit summaries."""
    return calculate_pnl(db, company_id)

@router.get("/balance-sheet", response_model=BalanceSheetResponse)
def get_balance_sheet(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Returns Assets, Liabilities, and Equity."""
    return calculate_balance_sheet(db, company_id)

@router.get("/ledgers", response_model=list[LedgerResponse])
def get_ledgers(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Returns all Ledgers belonging to the company, including nested transactions."""
    from sqlalchemy.orm import selectinload
    
    # We use selectinload to eagerly fetch the nested transactions efficiently
    ledgers = db.query(Ledger).filter(
        Ledger.company_id == company_id
    ).options(selectinload(Ledger.transactions)).all()
    
    return ledgers
