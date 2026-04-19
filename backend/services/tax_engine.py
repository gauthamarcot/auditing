def process_taxation_and_audit(row_data: dict, uploaded_proofs: dict) -> dict:
    audit_status = {
        "status": "PENDING_VALIDATION",
        "missing_proofs": [],
        "calculated_taxes": {}
    }
    
    base_amount = row_data.get('total_amount', 0)
    if base_amount is None:
        base_amount = 0
        
    vendor_state = row_data.get('vendor_state', '')
    company_state = "Karnataka" # Assuming base location
    
    # 1. GST Calculation Logic (Mocked 18% slab for simplicity)
    if vendor_state and vendor_state.lower() == company_state.lower():
        audit_status["calculated_taxes"]["CGST"] = base_amount * 0.09
        audit_status["calculated_taxes"]["SGST"] = base_amount * 0.09
        audit_status["calculated_taxes"]["IGST"] = 0.0
    else:
        audit_status["calculated_taxes"]["CGST"] = 0.0
        audit_status["calculated_taxes"]["SGST"] = 0.0
        audit_status["calculated_taxes"]["IGST"] = base_amount * 0.18

    # 2. TDS Auditing Logic (e.g., Section 194J - Professional Services over 30k)
    category = row_data.get('category', '')
    if category == 'Professional Services' and base_amount > 30000:
        pan_number = row_data.get('pan_number')
        if not pan_number or not uploaded_proofs.get('pan_card_verified'):
            # Trigger the Validation Loop
            audit_status["missing_proofs"].append("PAN_CARD_REQUIRED_FOR_TDS")
            audit_status["calculated_taxes"]["TDS"] = base_amount * 0.20 # 20% if no PAN
        else:
            audit_status["calculated_taxes"]["TDS"] = base_amount * 0.10 # 10% standard 194J

    # Set status ready if no missing proofs
    if not audit_status["missing_proofs"]:
        audit_status["status"] = "PENDING_VALIDATION" # Still requires manual checker to approve it
        # Note: it only becomes READY_FOR_TALLY after Checker Approval

    return audit_status
