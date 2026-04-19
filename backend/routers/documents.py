from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging

from ..database import get_db
from ..models import Document, AuditLog, Ledger, Transaction, Company
from ..schemas import DocumentResponse, AuditLogResponse
from ..services.ai_ocr import extract_invoice_data_with_llm
from ..services.tax_engine import process_taxation_and_audit
from ..services.tally_sync import push_voucher_to_tally

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    maker_id: str = Form("maker_user_1"),
    doc_type: str = Form("invoices"),
    company_id: int = Form(1),
    db: Session = Depends(get_db)
):
    """
    1. Maker uploads a document.
    2. AI OCR extracts data.
    3. Tax Engine validates rules and calculates GST/TDS.
    """
    file_bytes = await file.read()
    
    # 1. AI OCR Extraction (mocked)
    extracted_data = extract_invoice_data_with_llm(file_bytes, doc_type=doc_type)
    
    # 2. Tax Logic Validation
    # In a real scenario, we might have uploaded proofs. Mocking an empty dict here.
    uploaded_proofs = {"pan_card_verified": extracted_data.get("pan_number") is not None}
    tax_audit_result = process_taxation_and_audit(extracted_data, uploaded_proofs)
    
    # Create DB Record
    db_doc = Document(
        company_id=company_id,
        filename=file.filename,
        status="PENDING_VALIDATION",
        vendor_name=extracted_data.get("vendor_name"),
        suggested_group=extracted_data.get("suggested_group"),
        gstin=extracted_data.get("gstin"),
        pan_number=extracted_data.get("pan_number"),
        total_amount=extracted_data.get("total_amount"),
        cgst=tax_audit_result.get("calculated_taxes", {}).get("CGST", 0.0),
        sgst=tax_audit_result.get("calculated_taxes", {}).get("SGST", 0.0),
        igst=tax_audit_result.get("calculated_taxes", {}).get("IGST", 0.0),
        tds=tax_audit_result.get("calculated_taxes", {}).get("TDS", 0.0),
        date=extracted_data.get("date"),
        calculated_taxes=tax_audit_result.get("calculated_taxes"),
        missing_proofs=tax_audit_result.get("missing_proofs")
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Insert Immutable Audit Log
    audit_log = AuditLog(
        document_id=db_doc.id,
        user_id=maker_id,
        action="UPLOADED_AND_EXTRACTED",
        data_snapshot={
            "raw_extraction": extracted_data,
            "tax_result": tax_audit_result
        }
    )
    db.add(audit_log)
    db.commit()

    return db_doc

@router.get("/pending", response_model=List[DocumentResponse])
def get_pending_documents(company_id: int = Query(...), db: Session = Depends(get_db)):
    """Fetch documents waiting for Checker to Approve."""
    docs = db.query(Document).filter(Document.status == "PENDING_VALIDATION", Document.company_id == company_id).all()
    return docs

@router.post("/{doc_id}/approve", response_model=DocumentResponse)
def approve_document(
    doc_id: int, 
    company_id: int = Form(1),
    checker_id: str = Form("checker_user_1"), 
    ledger_group: str = Form("Uncategorized"),
    db: Session = Depends(get_db)
):
    """Maker-Checker Flow: Checker approves the document, auto-generating local Ledgers."""
    from datetime import datetime

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc.status = "READY_FOR_TALLY"
    
    # AUTO-GENERATE LEDGER & TRANSACTION
    if doc.vendor_name and doc.total_amount:
        # Ensure company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            mock_name = "Autara Demo Corp" if company_id == 1 else "Acme Industries"
            company = Company(id=company_id, name=mock_name, tally_guid=f"GUID-{company_id}")
            db.add(company)
            db.commit()
            
        ledger = db.query(Ledger).filter(Ledger.company_id == company_id, Ledger.name == doc.vendor_name).first()
        if not ledger:
            ledger = Ledger(company_id=company_id, name=doc.vendor_name, group=ledger_group)
            db.add(ledger)
            db.commit()
            db.refresh(ledger)
        
        # Link document to ledger
        doc.ledger_id = ledger.id
            
        txn = Transaction(
            company_id=company_id,
            ledger_id=ledger.id,
            date=datetime.utcnow(),
            amount=doc.total_amount,
            type="Debit", # Assuming expense uploading for this flow
            voucher_type="Journal",
            narration=f"Auto-ingested from {doc.filename}"
        )
        db.add(txn)
    
    db.commit()
    db.refresh(doc)
    
    # Audit Log
    audit_log = AuditLog(
        document_id=doc.id,
        user_id=checker_id,
        action="APPROVED_AND_BOOKED",
        data_snapshot={"status": "READY_FOR_TALLY", "booked_to_ledger": doc.vendor_name}
    )
    db.add(audit_log)
    db.commit()
    
    return doc

@router.post("/{doc_id}/sync-tally")
def sync_to_tally(doc_id: int, user_id: str = Form("system_user"), db: Session = Depends(get_db)):
    """Push the JSON object to Tally UI via HTTP XML API."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status != "READY_FOR_TALLY":
        raise HTTPException(status_code=400, detail="Document is not approved yet")
        
    narration = f"Invoice from {doc.vendor_name}"
    success = push_voucher_to_tally(doc.vendor_name, doc.date, doc.total_amount, narration)
    
    if success:
        doc.status = "SYNCED"
        db.commit()
        db.refresh(doc)
        
        audit_log = AuditLog(
            document_id=doc.id,
            user_id=user_id,
            action="PUSHED_TO_TALLY",
            data_snapshot={"success": True}
        )
        db.add(audit_log)
        db.commit()
        
        return {"status": "success", "message": "Synced to Tally"}
    else:
        raise HTTPException(status_code=500, detail="Failed to sync to Tally")

@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    """Get the immutable audit ledger."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return logs
