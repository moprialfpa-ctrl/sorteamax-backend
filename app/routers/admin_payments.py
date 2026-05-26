# app/routers/admin_payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
import random
import uuid

from app.database import get_db
from app.models import Payment, Ticket, Draw
from app.schemas import PaymentOut
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


def create_tickets_from_payment(db: Session, payment: Payment):
    draw = db.query(Draw).filter(Draw.id == payment.draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    tickets = []
    for _ in range(payment.quantity):
        numbers = sorted(random.sample(range(1, 27), 11))
        numbers_json = json.dumps(numbers)

        ticket = Ticket(
            id=str(uuid.uuid4()),
            payment_id=payment.id,
            user_id=payment.user_id,
            draw_id=draw.id,
            numbers=numbers_json,
            hits=0,
            prize_type=None,
            prize_amount=0.0,
            is_free_ticket=False,
            created_at=datetime.utcnow(),
        )
        db.add(ticket)
        tickets.append(ticket)

    draw.tickets_sold += payment.quantity
    draw.sales_amount += payment.amount

    jackpot_share = payment.amount * 0.50
    tier10_share = payment.amount * 0.35
    free_ticket_share = payment.amount * 0.10
    admin_share = payment.amount - (jackpot_share + tier10_share + free_ticket_share)

    draw.jackpot_pool += jackpot_share
    draw.tier10_pool += tier10_share
    draw.free_ticket_pool += free_ticket_share
    draw.admin_margin += admin_share

    return tickets


@router.get("/pending-manual", response_model=list[PaymentOut])
def list_pending_manual(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    return (
        db.query(Payment)
        .filter(Payment.status == "pending_manual")
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.post("/{payment_id}/confirm", response_model=PaymentOut)
def confirm_manual_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if payment.status != "pending_manual":
        raise HTTPException(status_code=400, detail="Pago ya procesado")

    payment.status = "confirmed"
    payment.confirmed_at = datetime.utcnow()

    create_tickets_from_payment(db, payment)

    db.commit()
    db.refresh(payment)

    return payment


@router.post("/{payment_id}/reject", response_model=PaymentOut)
def reject_manual_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if payment.status != "pending_manual":
        raise HTTPException(status_code=400, detail="Pago ya procesado")

    payment.status = "rejected"
    db.commit()
    db.refresh(payment)

    return payment