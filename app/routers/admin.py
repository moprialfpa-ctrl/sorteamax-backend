# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import json

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import User, BankAccount, Payment, Ticket, Draw, FreeTicketCredit
from app.schemas import (
    AdminDashboardSummaryOut,
    AdminUserListItemOut,
    AdminUserDetailOut,
    AdminPaymentDetailOut,
    AdminTicketDetailOut,
    AdminWinnerOut,
    AdminFreeTicketCreditOut,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def parse_numbers(raw_value):
    if not raw_value:
        return []
    try:
        return json.loads(raw_value)
    except Exception:
        return []


@router.get("/dashboard/summary", response_model=AdminDashboardSummaryOut)
def admin_dashboard_summary(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_admins = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
    total_bank_accounts = db.query(func.count(BankAccount.id)).scalar() or 0

    total_draws = db.query(func.count(Draw.id)).scalar() or 0
    selling_draws = db.query(func.count(Draw.id)).filter(Draw.status == "selling").scalar() or 0
    closed_draws = db.query(func.count(Draw.id)).filter(Draw.status == "closed").scalar() or 0
    drawn_draws = db.query(func.count(Draw.id)).filter(Draw.status == "drawn").scalar() or 0

    total_payments = db.query(func.count(Payment.id)).scalar() or 0
    pending_payments = db.query(func.count(Payment.id)).filter(Payment.status == "pending_manual").scalar() or 0
    confirmed_payments = db.query(func.count(Payment.id)).filter(Payment.confirmed_at.isnot(None)).scalar() or 0

    total_tickets = db.query(func.count(Ticket.id)).scalar() or 0
    total_winning_tickets = db.query(func.count(Ticket.id)).filter(Ticket.prize_type.isnot(None)).scalar() or 0

    total_free_ticket_credits = db.query(func.count(FreeTicketCredit.id)).scalar() or 0
    available_free_ticket_credits = (
        db.query(func.count(FreeTicketCredit.id))
        .filter(FreeTicketCredit.status == "available")
        .scalar() or 0
    )
    used_free_ticket_credits = (
        db.query(func.count(FreeTicketCredit.id))
        .filter(FreeTicketCredit.status == "used")
        .scalar() or 0
    )

    total_paid_prizes = db.query(func.coalesce(func.sum(Ticket.prize_amount), 0.0)).scalar() or 0.0

    return AdminDashboardSummaryOut(
        total_users=total_users,
        total_admins=total_admins,
        total_bank_accounts=total_bank_accounts,
        total_draws=total_draws,
        selling_draws=selling_draws,
        closed_draws=closed_draws,
        drawn_draws=drawn_draws,
        total_payments=total_payments,
        pending_payments=pending_payments,
        confirmed_payments=confirmed_payments,
        total_tickets=total_tickets,
        total_winning_tickets=total_winning_tickets,
        total_free_ticket_credits=total_free_ticket_credits,
        available_free_ticket_credits=available_free_ticket_credits,
        used_free_ticket_credits=used_free_ticket_credits,
        total_paid_prizes=round(float(total_paid_prizes), 2),
    )


@router.get("/users", response_model=list[AdminUserListItemOut])
def admin_list_users(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    query = db.query(User).options(
        joinedload(User.bank_account),
        joinedload(User.payments),
        joinedload(User.tickets),
    )

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            (User.full_name.ilike(like)) |
            (User.email.ilike(like))
        )

    users = query.order_by(User.created_at.desc()).all()

    result = []
    for user in users:
        winning_tickets_count = sum(1 for t in user.tickets if t.prize_type is not None)
        free_tickets_count = sum(1 for t in user.tickets if t.is_free_ticket)

        result.append(
            AdminUserListItemOut(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                created_at=user.created_at,
                has_bank_account=user.bank_account is not None,
                bank_name=user.bank_account.bank_name if user.bank_account else None,
                payments_count=len(user.payments),
                tickets_count=len(user.tickets),
                winning_tickets_count=winning_tickets_count,
                free_tickets_count=free_tickets_count,
            )
        )

    return result


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def admin_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    user = (
        db.query(User)
        .options(
            joinedload(User.bank_account),
            joinedload(User.payments).joinedload(Payment.draw),
            joinedload(User.tickets).joinedload(Ticket.draw),
            joinedload(User.free_ticket_credits).joinedload(FreeTicketCredit.draw),
        )
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    payments = []
    for payment in sorted(user.payments, key=lambda x: x.created_at, reverse=True):
        generated_tickets_count = len([t for t in user.tickets if t.payment_id == payment.id])
        payments.append(
            AdminPaymentDetailOut(
                id=payment.id,
                user_id=payment.user_id,
                user_name=user.full_name,
                user_email=user.email,
                draw_id=payment.draw_id,
                draw_title=payment.draw.title if payment.draw else None,
                quantity=payment.quantity,
                amount=payment.amount,
                status=payment.status,
                provider=payment.provider,
                reference_note=payment.reference_note,
                created_at=payment.created_at,
                confirmed_at=payment.confirmed_at,
                generated_tickets_count=generated_tickets_count,
            )
        )

    tickets = []
    winning_tickets = []
    for ticket in sorted(user.tickets, key=lambda x: x.created_at, reverse=True):
        ticket_data = AdminTicketDetailOut(
            id=ticket.id,
            payment_id=ticket.payment_id,
            user_id=ticket.user_id,
            draw_id=ticket.draw_id,
            draw_title=ticket.draw.title if ticket.draw else None,
            numbers=parse_numbers(ticket.numbers),
            hits=ticket.hits,
            prize_type=ticket.prize_type,
            prize_amount=float(ticket.prize_amount or 0.0),
            is_free_ticket=ticket.is_free_ticket,
            source_credit_id=ticket.source_credit_id,
            created_at=ticket.created_at,
        )
        tickets.append(ticket_data)

        if ticket.prize_type is not None:
            winning_tickets.append(
                AdminWinnerOut(
                    ticket_id=ticket.id,
                    user_id=ticket.user_id,
                    user_name=user.full_name,
                    user_email=user.email,
                    draw_id=ticket.draw_id,
                    draw_title=ticket.draw.title if ticket.draw else None,
                    numbers=parse_numbers(ticket.numbers),
                    hits=ticket.hits,
                    prize_type=ticket.prize_type,
                    prize_amount=float(ticket.prize_amount or 0.0),
                    is_free_ticket=ticket.is_free_ticket,
                    created_at=ticket.created_at,
                )
            )

    free_ticket_credits = []
    for credit in sorted(user.free_ticket_credits, key=lambda x: x.created_at, reverse=True):
        free_ticket_credits.append(
            AdminFreeTicketCreditOut(
                id=credit.id,
                user_id=credit.user_id,
                draw_id=credit.draw_id,
                draw_title=credit.draw.title if credit.draw else None,
                source_ticket_id=credit.source_ticket_id,
                status=credit.status,
                created_at=credit.created_at,
                used_at=credit.used_at,
            )
        )

    return AdminUserDetailOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        bank_account=user.bank_account,
        payments=payments,
        tickets=tickets,
        winning_tickets=winning_tickets,
        free_ticket_credits=free_ticket_credits,
    )


@router.get("/payments", response_model=list[AdminPaymentDetailOut])
def admin_list_payments(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    payments = (
        db.query(Payment)
        .options(
            joinedload(Payment.user),
            joinedload(Payment.draw),
            joinedload(Payment.tickets),
        )
        .order_by(Payment.created_at.desc())
        .all()
    )

    if status:
        payments = [p for p in payments if p.status == status]

    result = []
    for payment in payments:
        result.append(
            AdminPaymentDetailOut(
                id=payment.id,
                user_id=payment.user_id,
                user_name=payment.user.full_name if payment.user else None,
                user_email=payment.user.email if payment.user else None,
                draw_id=payment.draw_id,
                draw_title=payment.draw.title if payment.draw else None,
                quantity=payment.quantity,
                amount=payment.amount,
                status=payment.status,
                provider=payment.provider,
                reference_note=payment.reference_note,
                created_at=payment.created_at,
                confirmed_at=payment.confirmed_at,
                generated_tickets_count=len(payment.tickets),
            )
        )

    return result


@router.get("/tickets", response_model=list[AdminTicketDetailOut])
def admin_list_tickets(
    only_winners: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.draw))
        .order_by(Ticket.created_at.desc())
        .all()
    )

    if only_winners:
        tickets = [t for t in tickets if t.prize_type is not None]

    return [
        AdminTicketDetailOut(
            id=t.id,
            payment_id=t.payment_id,
            user_id=t.user_id,
            draw_id=t.draw_id,
            draw_title=t.draw.title if t.draw else None,
            numbers=parse_numbers(t.numbers),
            hits=t.hits,
            prize_type=t.prize_type,
            prize_amount=float(t.prize_amount or 0.0),
            is_free_ticket=t.is_free_ticket,
            source_credit_id=t.source_credit_id,
            created_at=t.created_at,
        )
        for t in tickets
    ]


@router.get("/winners", response_model=list[AdminWinnerOut])
def admin_list_winners(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.user),
            joinedload(Ticket.draw),
        )
        .filter(Ticket.prize_type.isnot(None))
        .order_by(Ticket.created_at.desc())
        .all()
    )

    return [
        AdminWinnerOut(
            ticket_id=t.id,
            user_id=t.user_id,
            user_name=t.user.full_name if t.user else None,
            user_email=t.user.email if t.user else None,
            draw_id=t.draw_id,
            draw_title=t.draw.title if t.draw else None,
            numbers=parse_numbers(t.numbers),
            hits=t.hits,
            prize_type=t.prize_type,
            prize_amount=float(t.prize_amount or 0.0),
            is_free_ticket=t.is_free_ticket,
            created_at=t.created_at,
        )
        for t in tickets
    ]


@router.get("/bank-accounts")
def admin_list_bank_accounts(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    accounts = (
        db.query(BankAccount)
        .options(joinedload(BankAccount.user))
        .order_by(BankAccount.created_at.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_name": a.user.full_name if a.user else None,
            "user_email": a.user.email if a.user else None,
            "full_name": a.full_name,
            "id_number": a.id_number,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "account_type": a.account_type,
            "phone": a.phone,
            "deuna_phone": a.deuna_phone,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }
        for a in accounts
    ]

@router.post("/reset-admin-password")
def reset_admin_password(db: Session = Depends(get_db)):
    from app.security import hash_password
    user = db.query(User).filter(User.email == "admin@sorteamax.com").first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin no encontrado")
    user.hashed_password = hash_password("Admin2026!")
    db.commit()
    return {"message": "Contrasena del admin reseteada a: Admin2026!"}
