# app/routers/deuna_manual.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Payment, Draw
from app.schemas import PaymentOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/deuna", tags=["deuna-manual"])


class DeunaManualPaymentRequest:
    """
    Usaremos un esquema simple interno, para no tocar schemas.py.
    Si quieres, luego lo pasamos a Pydantic en schemas.py.
    """
    def __init__(self, draw_id: str, amount: float, quantity: int = 1, reference_note: str | None = None):
        self.draw_id = draw_id
        self.amount = amount
        self.quantity = quantity
        self.reference_note = reference_note


from pydantic import BaseModel, Field


class DeunaManualPaymentCreate(BaseModel):
    draw_id: str = Field(..., description="ID del sorteo")
    amount: float = Field(..., gt=0, description="Monto a pagar en USD")
    quantity: int = Field(default=1, gt=0, description="Cantidad de boletos (coincide con tu lógica)")
    reference_note: str | None = Field(
        default=None,
        description="Referencia del usuario: 'pagué a las 15h10, nombre en Deuna...'"
    )


class DeunaManualPaymentOut(PaymentOut):
    reference_note: str | None = None


@router.post("/payments/manual", response_model=DeunaManualPaymentOut)
def create_manual_deuna_payment(
    payload: DeunaManualPaymentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    El usuario ve el QR Deuna, paga en la app y luego llama a este endpoint para registrar el pago.
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

    payment = Payment(
        user_id=current_user.id,
        draw_id=draw.id,
        quantity=payload.quantity,
        amount=payload.amount,
        status="pending_manual",  # usamos string porque tu modelo usa String
        created_at=datetime.utcnow(),
    )

    # Guardamos la nota de referencia en un campo adicional si quieres:
    # como tu modelo Payment no tiene reference_note, la podemos ignorar
    # o agregar un campo nuevo en la BD; por ahora solo la ignoramos a nivel de modelo.

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Convertimos a PaymentOut y le añadimos reference_note (None por ahora)
    return DeunaManualPaymentOut(
        id=payment.id,
        user_id=payment.user_id,
        draw_id=payment.draw_id,
        quantity=payment.quantity,
        amount=payment.amount,
        status=payment.status,
        created_at=payment.created_at,
        confirmed_at=payment.confirmed_at,
        reference_note=payload.reference_note,
    )


@router.get("/payments/mine", response_model=list[PaymentOut])
def list_my_deuna_payments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lista los pagos (de cualquier tipo) del usuario actual.
    Puedes filtrar por status/provider en el frontend.
    """
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )