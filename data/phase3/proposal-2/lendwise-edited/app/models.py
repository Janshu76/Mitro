from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    pan_last4: Mapped[str] = mapped_column(String(4), default="0000")
    date_of_birth: Mapped[str] = mapped_column(String(12), default="")
    full_address: Mapped[str] = mapped_column(Text, default="")
    employer_name: Mapped[str] = mapped_column(String(160), default="")
    bank_account_number: Mapped[str] = mapped_column(String(40), default="")
    consent_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    requested_amount: Mapped[float] = mapped_column(Float)
    purpose: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="submitted", index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class LoanAccount(Base):
    __tablename__ = "loan_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    principal: Mapped[float] = mapped_column(Float)
    outstanding: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="active")

class Repayment(Base):
    __tablename__ = "repayments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loan_accounts.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    reference: Mapped[str] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class PartnerEvent(Base):
    __tablename__ = "partner_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_name: Mapped[str] = mapped_column(String(80), index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loan_accounts.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    payload_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
