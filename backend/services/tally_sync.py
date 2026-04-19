import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

def push_voucher_to_tally(vendor_name, date, amount, narration):
    tally_url = "http://localhost:9000"
    
    # Standard Tally XML Envelope for an Accounting Voucher
    tally_xml = f"""
    <ENVELOPE>
      <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
      </HEADER>
      ...
    </ENVELOPE>
    """
    
    logger.info(f"Mocking Tally Push for Vendor: {vendor_name}, Amount: {amount}")
    try:
        return True
    except Exception as e:
        logger.error(f"Failed to post to Tally: {e}")
        return False

def pull_data_from_tally():
    """
    Mocks an XML <EXPORTDATA> request to the local Tally server to fetch Day Book/Trial Balance.
    Returns mocked structure of Ledgers and Transactions.
    """
    logger.info("Mocking Tally Pull...")
    
    # Mocking standard Indian Accounting ledger taxonomy
    mock_ledgers = [
        {"name": "Raw Materials A", "group": "Direct Expenses"},
        {"name": "Factory Electricity", "group": "Direct Expenses"},
        {"name": "Machine Maintenance", "group": "Direct Expenses"},
        {"name": "Office Rent", "group": "Indirect Expenses"},
        {"name": "Marketing & Ads", "group": "Indirect Expenses"},
        {"name": "Product Sales", "group": "Direct Income"}
    ]
    
    # Mocking transactions over the current month
    mock_transactions = [
        {"ledger_name": "Product Sales", "amount": 800000.0, "type": "Credit"},
        {"ledger_name": "Raw Materials A", "amount": 350000.0, "type": "Debit"},
        {"ledger_name": "Factory Electricity", "amount": 40000.0, "type": "Debit"},
        {"ledger_name": "Machine Maintenance", "amount": 15000.0, "type": "Debit"},
        {"ledger_name": "Office Rent", "amount": 50000.0, "type": "Debit"},
        {"ledger_name": "Marketing & Ads", "amount": 25000.0, "type": "Debit"}
    ]
    
    return {"ledgers": mock_ledgers, "transactions": mock_transactions}
