from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    tally_guid = Column(String, unique=True, index=True)
    
    ledgers = relationship("Ledger", back_populates="company")
    transactions = relationship("Transaction", back_populates="company")

class Ledger(Base):
    __tablename__ = "ledgers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String, index=True)
    group = Column(String) # "Direct Expenses", "Indirect Expenses", "Sales Accounts", etc.
    
    company = relationship("Company", back_populates="ledgers")
    transactions = relationship("Transaction", back_populates="ledger")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    ledger_id = Column(Integer, ForeignKey("ledgers.id"))
    date = Column(DateTime)
    amount = Column(Float)
    type = Column(String) # "Debit" or "Credit"
    voucher_type = Column(String) # "Journal", "Payment", "Receipt", "Sales", "Purchase"
    narration = Column(String)
    
    company = relationship("Company", back_populates="transactions")
    ledger = relationship("Ledger", back_populates="transactions")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="PENDING_VALIDATION") # PENDING_VALIDATION, READY_FOR_TALLY, SYNCED
    
    # Ledger mapping
    ledger_id = Column(Integer, ForeignKey("ledgers.id"), nullable=True)
    
    # Extracted data
    vendor_name = Column(String, nullable=True)
    suggested_group = Column(String, nullable=True) # E.g., "Direct Expenses"
    gstin = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    cgst = Column(Float, nullable=True)
    sgst = Column(Float, nullable=True)
    igst = Column(Float, nullable=True)
    tds = Column(Float, nullable=True)
    date = Column(String, nullable=True)
    
    # Tax Engine results / validation flags
    calculated_taxes = Column(JSON, nullable=True)
    missing_proofs = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    audit_logs = relationship("AuditLog", back_populates="document")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    user_id = Column(String) # Mocked Maker/Checker IDs
    action = Column(String) # UPLOADED, AI_EXTRACTED, APPROVED, PUSHED_TO_TALLY
    data_snapshot = Column(JSON, nullable=True) # Immutable snapshot of the data or hash at that moment
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="audit_logs")
