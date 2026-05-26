# app/routers/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import json

from app.database import get_db
from app.models import Payment, Ticket, Draw
from app.dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentOut(BaseModel):
    id: str
    user_id: str
    draw_id: str | None
    quantity: int
    amount: float
    status: str
    provider: str | None
    reference_note: str | None
    created_at: datetime
    confirmed_at: datetime | None

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    ticket_id: str
    draw_id: str
    draw_title: str | None
    user_id: str
    numbers: list
    hits: int
    prize_type: str | None
    prize_amount: float
    is_free_ticket: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[PaymentOut])
def get_my_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(desc(Payment.created_at))
        .all()
    )
    return payments


@router.get("/tickets/mine", response_model=List[TicketOut])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.user_id == current_user.id)
        .order_by(desc(Ticket.created_at))
        .all()
    )

    result = []
    for t in tickets:
        try:
            numbers = json.loads(t.numbers) if t.numbers else []
        except Exception:
            numbers = []

        draw_title = None
        if t.draw_id:
            draw = db.query(Draw).filter(Draw.id == t.draw_id).first()
            if draw:
                draw_title = draw.title

        result.append(TicketOut(
            ticket_id=t.id,
            draw_id=t.draw_id,
            draw_title=draw_title,
            user_id=t.user_id,
            numbers=numbers,
            hits=t.hits,
            prize_type=t.prize_type,
            prize_amount=t.prize_amount or 0.0,
            is_free_ticket=t.is_free_ticket,
            created_at=t.created_at,
        ))

    return result