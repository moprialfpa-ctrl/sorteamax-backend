# app/routers/bank_accounts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.database import get_db
from app.models import BankAccount
from app.dependencies import get_current_user, get_current_admin
from pydantic import BaseModel

router = APIRouter(prefix="/bank-accounts", tags=["bank-accounts"])


class BankAccountCreate(BaseModel):
    full_name: str
    id_number: str
    bank_name: str
    account_number: str
    account_type: str
    phone: str | None = None
    deuna_phone: str | None = None


class BankAccountOut(BaseModel):
    id: str
    user_id: str
    full_name: str
    id_number: str
    bank_name: str
    account_number: str
    account_type: str
    phone: str | None
    deuna_phone: str | None

    class Config:
        from_attributes = True


@router.post("/", response_model=BankAccountOut)
def save_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    existing = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).first()

    if existing:
        existing.full_name = payload.full_name
        existing.id_number = payload.id_number
        existing.bank_name = payload.bank_name
        existing.account_number = payload.account_number
        existing.account_type = payload.account_type
        existing.phone = payload.phone
        existing.deuna_phone = payload.deuna_phone
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    account = BankAccount(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        full_name=payload.full_name,
        id_number=payload.id_number,
        bank_name=payload.bank_name,
        account_number=payload.account_number,
        account_type=payload.account_type,
        phone=payload.phone,
        deuna_phone=payload.deuna_phone,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/mine", response_model=BankAccountOut)
def get_my_bank_account(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    account = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="No tienes cuenta registrada")
    return account


@router.get("/admin/all", response_model=list[BankAccountOut])
def list_all_bank_accounts(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    return db.query(BankAccount).order_by(BankAccount.created_at.desc()).all()


@router.get("/admin/user/{user_id}", response_model=BankAccountOut)
def get_bank_account_by_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    account = db.query(BankAccount).filter(
        BankAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Usuario no tiene cuenta registrada")
    return account