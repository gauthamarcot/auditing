import pytest
from unittest.mock import patch
import json

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Auditing and Taxation API"}

@patch("backend.routers.documents.extract_invoice_data_with_llm")
@patch("backend.routers.documents.process_taxation_and_audit")
def test_upload_document(mock_process, mock_extract, client):
    mock_extract.return_value = {
        "vendor_name": "Test Vendor",
        "suggested_group": "Direct Expenses",
        "gstin": "12ABCDE3456F7Z8",
        "pan_number": "ABCDE3456F",
        "total_amount": 1180.0,
        "date": "2023-10-01"
    }
    
    mock_process.return_value = {
        "calculated_taxes": {
            "CGST": 90.0,
            "SGST": 90.0,
            "IGST": 0.0,
            "TDS": 0.0
        },
        "missing_proofs": []
    }

    # Since we use File(...), we need to upload a test file
    file_content = b"fake invoice data"
    files = {"file": ("invoice.pdf", file_content, "application/pdf")}
    data = {
        "maker_id": "test_maker_1",
        "doc_type": "invoices"
    }

    response = client.post("/api/documents/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["filename"] == "invoice.pdf"
    assert res_data["status"] == "PENDING_VALIDATION"
    assert res_data["vendor_name"] == "Test Vendor"
    assert res_data["total_amount"] == 1180.0
    
    # Store doc_id for next tests if needed
    doc_id = res_data["id"]

    # Verify pending
    resp_pending = client.get("/api/documents/pending")
    assert resp_pending.status_code == 200
    docs = resp_pending.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id

    # Test Approval
    appr_data = {
        "checker_id": "test_checker_1",
        "ledger_group": "Direct Expenses"
    }
    resp_appr = client.post(f"/api/documents/{doc_id}/approve", data=appr_data)
    assert resp_appr.status_code == 200
    assert resp_appr.json()["status"] == "READY_FOR_TALLY"

@patch("backend.routers.documents.push_voucher_to_tally")
def test_sync_to_tally(mock_push, client, db_session):
    mock_push.return_value = True
    
    # Create doc directly in DB for testing
    from backend.models import Document, Company
    from datetime import datetime
    
    comp = Company(name="Test Corp", tally_guid="TEST-123", id=1)
    db_session.add(comp)
    db_session.commit()
    
    doc = Document(
        filename="test.pdf",
        status="READY_FOR_TALLY",
        vendor_name="Test Vendor",
        total_amount=100.0,
        date="2023-10-01"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    
    sync_data = {"user_id": "system_user"}
    response = client.post(f"/api/documents/{doc.id}/sync-tally", data=sync_data)
    
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Synced to Tally"}
    
    db_session.refresh(doc)
    assert doc.status == "SYNCED"

def test_get_audit_logs(client):
    response = client.get("/api/documents/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
