# app/routers/deuna_manual.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import Payment, Draw
from app.schemas import PaymentOut
from app.dependencies import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/deuna", tags=["deuna-manual"])


class DeunaManualPaymentCreate(BaseModel):
    draw_id: str = Field(..., description="ID del sorteo")
    amount: float = Field(..., gt=0, description="Monto a pagar en USD")
    quantity: int = Field(default=1, gt=0, description="Cantidad de boletos")
    reference_note: Optional[str] = Field(default=None, description="Nota del pago")
    transaction_number: Optional[str] = Field(default=None, description="Numero de transaccion del comprobante")
    receipt_image: Optional[str] = Field(default=None, description="Imagen del comprobante en base64")


class DeunaManualPaymentOut(PaymentOut):
    reference_note: Optional[str] = None
    transaction_number: Optional[str] = None
    receipt_image: Optional[str] = None


@router.post("/payments/manual", response_model=DeunaManualPaymentOut)
def create_manual_deuna_payment(
    payload: DeunaManualPaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    El usuario ve el QR Deuna, paga en la app y luego llama a este endpoint
    para registrar el pago adjuntando numero de transaccion y/o comprobante.
    """
    draw = db.query(Draw).filter(Draw.id == payload.draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    expected_amount = payload.quantity * draw.ticket_price
    if abs(payload.amount - expected_amount) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"El monto esperado es {expected_amount:.2f} para {payload.quantity} boletos"
        )

    # Validar que venga al menos numero de transaccion O comprobante
    if not payload.transaction_number and not payload.receipt_image:
        raise HTTPException(
            status_code=400,
            detail="Debes ingresar el numero de transaccion o adjuntar el comprobante de pago"
        )

    payment = Payment(
        user_id=current_user.id,
        draw_id=draw.id,
        quantity=payload.quantity,
        amount=payload.amount,
        status="pending_manual",
        reference_note=payload.reference_note,
        transaction_number=payload.transaction_number,
        receipt_image=payload.receipt_image,
        created_at=datetime.utcnow(),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return DeunaManualPaymentOut(
        id=payment.id,
        user_id=payment.user_id,
        draw_id=payment.draw_id,
        quantity=payment.quantity,
        amount=payment.amount,
        status=payment.status,
        created_at=payment.created_at,
        confirmed_at=payment.confirmed_at,
        reference_note=payment.reference_note,
        transaction_number=payment.transaction_number,
        receipt_image=payment.receipt_image,
    )


@router.get("/payments/mine", response_model=list[PaymentOut])
def list_my_deuna_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
