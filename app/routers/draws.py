from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random
import json

from app.database import get_db
from app.models import Draw, Ticket, FreeTicketCredit
from app.schemas import DrawCreate
from app.dependencies import get_current_user

router = APIRouter(prefix="/draws", tags=["Draws"])


def generate_extraction_order():
    return random.sample(range(1, 27), 11)


@router.post("/")
def create_draw(
    payload: DrawCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede crear sorteos")

    draw = Draw(
        title=payload.title,
        ticket_price=payload.ticket_price,
        sales_threshold_amount=payload.sales_threshold_amount,
        status="selling"
    )

    db.add(draw)
    db.commit()
    db.refresh(draw)
    return draw


@router.get("/")
def list_draws(db: Session = Depends(get_db)):
    return db.query(Draw).all()


@router.get("/{draw_id}")
def get_draw(draw_id: str, db: Session = Depends(get_db)):
    draw = db.query(Draw).filter(Draw.id == draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no existe")
    return draw


@router.post("/{draw_id}/close")
def close_draw(
    draw_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede cerrar sorteos")

    draw = db.query(Draw).filter(Draw.id == draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no existe")

    if draw.status not in ["selling", "ready"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cerrar un sorteo en estado {draw.status}"
        )

    if draw.sales_amount < draw.sales_threshold_amount:
        raise HTTPException(
            status_code=400,
            detail=f"El sorteo aún no alcanza el umbral mínimo de ventas (${draw.sales_threshold_amount})"
        )

    draw.status = "closed"
    draw.closed_at = datetime.utcnow()

    db.commit()
    db.refresh(draw)

    return {
        "message": "Ventas cerradas, sorteo listo para ejecución",
        "draw_id": draw.id,
        "sales_amount": draw.sales_amount,
        "tickets_sold": draw.tickets_sold,
        "status": draw.status,
    }


@router.post("/{draw_id}/run")
def run_draw(
    draw_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede ejecutar sorteos")

    draw = db.query(Draw).filter(Draw.id == draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no existe")

    if draw.status != "closed":
        raise HTTPException(
            status_code=400,
            detail=f"El sorteo debe estar en estado 'closed', no '{draw.status}'"
        )

    extraction_order = generate_extraction_order()
    winning_numbers = sorted(extraction_order)

    draw.extraction_order = json.dumps(extraction_order)
    draw.winning_numbers = json.dumps(winning_numbers)
    draw.executed_at = datetime.utcnow()
    draw.status = "drawn"

    tickets = db.query(Ticket).filter(Ticket.draw_id == draw_id).all()

    jackpot_winners = []
    tier10_winners = []
    tier9_winners = []

    for ticket in tickets:
        numbers = json.loads(ticket.numbers)
        hits = len(set(numbers) & set(winning_numbers))

        ticket.hits = hits
        ticket.prize_type = None
        ticket.prize_amount = 0.0

        if hits == 11:
            ticket.prize_type = "jackpot"
            jackpot_winners.append(ticket)
        elif hits == 10:
            ticket.prize_type = "tier10"
            tier10_winners.append(ticket)
        elif hits == 9:
            ticket.prize_type = "free_ticket"
            tier9_winners.append(ticket)

    jackpot_prize_per_winner = 0.0
    tier10_prize_per_winner = 0.0

    if jackpot_winners:
        jackpot_prize_per_winner = round(draw.jackpot_pool / len(jackpot_winners), 2)
        for ticket in jackpot_winners:
            ticket.prize_amount = jackpot_prize_per_winner
        draw.jackpot_pool = 0.0

    if tier10_winners:
        tier10_prize_per_winner = round(draw.tier10_pool / len(tier10_winners), 2)
        for ticket in tier10_winners:
            ticket.prize_amount = tier10_prize_per_winner
        draw.tier10_pool = 0.0

    for ticket in tier9_winners:
        credit = FreeTicketCredit(
            user_id=ticket.user_id,
            draw_id=draw.id,
            source_ticket_id=ticket.id,
            status="available"
        )
        db.add(credit)

    db.commit()

    return {
        "message": "Sorteo ejecutado correctamente",
        "draw_id": draw.id,
        "winning_numbers": winning_numbers,
        "extraction_order": extraction_order,
        "total_tickets": len(tickets),
        "jackpot_winners": len(jackpot_winners),
        "tier10_winners": len(tier10_winners),
        "tier9_winners": len(tier9_winners),
        "jackpot_prize_per_winner": jackpot_prize_per_winner,
        "tier10_prize_per_winner": tier10_prize_per_winner,
    }


@router.get("/{draw_id}/results")
def get_results(draw_id: str, db: Session = Depends(get_db)):
    draw = db.query(Draw).filter(Draw.id == draw_id).first()
    if not draw:
        raise HTTPException(status_code=404, detail="Sorteo no existe")

    tickets = db.query(Ticket).filter(Ticket.draw_id == draw_id).all()

    return {
        "draw_id": draw.id,
        "status": draw.status,
        "winning_numbers": json.loads(draw.winning_numbers) if draw.winning_numbers else [],
        "extraction_order": json.loads(draw.extraction_order) if draw.extraction_order else [],
        "results": [
            {
                "ticket_id": t.id,
                "user_id": t.user_id,
                "numbers": json.loads(t.numbers),
                "hits": t.hits,
                "prize_type": t.prize_type,
                "prize_amount": t.prize_amount,
                "is_free_ticket": t.is_free_ticket,
            }
            for t in tickets
        ],
    }