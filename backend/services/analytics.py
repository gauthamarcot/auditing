from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Transaction, Ledger
import logging

logger = logging.getLogger(__name__)

def calculate_cost_breakdown(db: Session, company_id: int):
    """Calculates Direct vs Indirect expenses for a given company."""
    transactions = db.query(Transaction, Ledger).join(Ledger, Transaction.ledger_id == Ledger.id).filter(
        Transaction.company_id == company_id,
        Transaction.type == "Debit" # Expenses are debits
    ).all()

    direct_expenses = 0.0
    indirect_expenses = 0.0
    details = {}

    for txn, ledger in transactions:
        amount = txn.amount
        group = ledger.group
        
        details[ledger.name] = details.get(ledger.name, 0.0) + amount

        if group == "Direct Expenses":
            direct_expenses += amount
        elif group == "Indirect Expenses":
            indirect_expenses += amount

    total_expenses = direct_expenses + indirect_expenses

    return {
        "direct_expenses": direct_expenses,
        "indirect_expenses": indirect_expenses,
        "total_expenses": total_expenses,
        "details": details
    }

def calculate_pnl(db: Session, company_id: int):
    """Calculates Gross Profit and Net Profit based on standard accounting rules."""
    
    # Get Revenue (Direct Income)
    revenue_txns = db.query(Transaction, Ledger).join(Ledger, Transaction.ledger_id == Ledger.id).filter(
        Transaction.company_id == company_id,
        Ledger.group == "Direct Income",
        Transaction.type == "Credit" # Incomes are credits
    ).all()
    
    total_revenue = sum([txn.amount for txn, _ in revenue_txns])
    
    # Get Expenses
    cost_data = calculate_cost_breakdown(db, company_id)
    
    # Calculations
    gross_profit = total_revenue - cost_data["direct_expenses"]
    net_profit = gross_profit - cost_data["indirect_expenses"]
    
    return {
        "total_revenue": total_revenue,
        "direct_expenses": cost_data["direct_expenses"],
        "indirect_expenses": cost_data["indirect_expenses"],
        "gross_profit": gross_profit,
        "net_profit": net_profit
    }

def calculate_balance_sheet(db: Session, company_id: int):
    # Groups typically considered assets
    asset_groups = ["Bank Accounts", "Fixed Assets"]
    # Groups typically considered liabilities and equity
    liability_groups = ["Sundry Creditors"]
    equity_groups = ["Capital Account"]

    # Calculate net profit to route into retained earnings
    pnl = calculate_pnl(db, company_id)
    retained_earnings = pnl["net_profit"]

    # Calculate Ledger balances
    ledgers = db.query(Ledger).filter(Ledger.company_id == company_id).all()
    
    assets_total = 0.0
    assets_details = {}
    
    liabilities_total = 0.0
    liabilities_details = {}
    
    equity_total = 0.0
    equity_details = {"Retained Earnings (Net Profit)": retained_earnings}

    for ledger in ledgers:
        # Calculate balance. Using Debit - Credit for Assets, Credit - Debit for Liab/Equity
        balance = 0.0
        for txn in ledger.transactions:
            if txn.type == "Debit":
                balance += txn.amount
            elif txn.type == "Credit":
                balance -= txn.amount
                
        if ledger.group in asset_groups:
            # Assets normally have debit balances
            assets_details[ledger.name] = balance
            assets_total += balance
        elif ledger.group in liability_groups:
            # Liab normally have credit balances
            liabilities_details[ledger.name] = -balance
            liabilities_total += -balance
        elif ledger.group in equity_groups:
            # Equity normally has credit balance
            equity_details[ledger.name] = -balance
            equity_total += -balance

    # Add retained earnings to equity total
    equity_total += retained_earnings

    return {
        "assets_total": assets_total,
        "assets_details": assets_details,
        "liabilities_total": liabilities_total,
        "liabilities_details": liabilities_details,
        "equity_total": equity_total,
        "equity_details": equity_details
    }
