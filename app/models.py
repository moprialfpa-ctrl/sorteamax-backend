# app/models.py
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payments = relationship("Payment", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")
    free_ticket_credits = relationship("FreeTicketCredit", back_populates="user")
    bank_account = relationship("BankAccount", back_populates="user", uselist=False)


class Draw(Base):
    __tablename__ = "draws"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    ticket_price = Column(Float, default=1.0, nullable=False)
    sales_threshold_amount = Column(Float, default=100.0, nullable=False)
    tickets_sold = Column(Integer, default=0, nullable=False)
    sales_amount = Column(Float, default=0.0, nullable=False)
    jackpot_pool = Column(Float, default=0.0, nullable=False)
    tier10_pool = Column(Float, default=0.0, nullable=False)
    free_ticket_pool = Column(Float, default=0.0, nullable=False)
    admin_margin = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="draft", nullable=False)
    winning_numbers = Column(Text, nullable=True)
    extraction_order = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    payments = relationship("Payment", back_populates="draw")
    tickets = relationship("Ticket", back_populates="draw")
    free_ticket_credits = relationship("FreeTicketCredit", back_populates="draw")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    draw_id = Column(String, ForeignKey("draws.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending_manual", nullable=False)
    provider = Column(String, default="deuna_qr", nullable=True)
    reference_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="payments")
    draw = relationship("Draw", back_populates="payments")
    tickets = relationship("Ticket", back_populates="payment")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    draw_id = Column(String, ForeignKey("draws.id"), nullable=False)
    numbers = Column(Text, nullable=False)
    hits = Column(Integer, default=0, nullable=False)
    prize_type = Column(String, nullable=True)
    prize_amount = Column(Float, default=0.0, nullable=False)
    is_free_ticket = Column(Boolean, default=False, nullable=False)
    source_credit_id = Column(String, ForeignKey("free_ticket_credits.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment = relationship("Payment", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    draw = relationship("Draw", back_populates="tickets")
    source_credit = relationship(
        "FreeTicketCredit",
        back_populates="generated_tickets",
        foreign_keys=[source_credit_id]
    )


class FreeTicketCredit(Base):
    __tablename__ = "free_ticket_credits"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    draw_id = Column(String, ForeignKey("draws.id"), nullable=False)
    source_ticket_id = Column(String, ForeignKey("tickets.id"), nullable=True)
    status = Column(String, default="available", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="free_ticket_credits")
    draw = relationship("Draw", back_populates="free_ticket_credits")
    generated_tickets = relationship(
        "Ticket",
        back_populates="source_credit",
        foreign_keys="Ticket.source_credit_id"
    )
    source_ticket = relationship(
        "Ticket",
        foreign_keys=[source_ticket_id]
    )


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    full_name = Column(String, nullable=False)
    id_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    deuna_phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="bank_account")