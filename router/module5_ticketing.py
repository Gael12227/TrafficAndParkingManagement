from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Using the correct schema models from schemas.py
from schemas import TicketBase, AppealBase
from db import get_db, Ticket, Appeal, Violation

# Removed the /v1 prefix for direct Streamlit integration
router = APIRouter(prefix="/api/v1/ticketing", tags=["Module 5: Ticketing & Appeals"])

# ---------------------------------------------------------
# E-CHALLAN (TICKETING) CRUD
# ---------------------------------------------------------

@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def issue_ticket(ticket: TicketBase, session: AsyncSession = Depends(get_db)):
    violation = await session.get(Violation, ticket.violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Cannot issue ticket: Violation ID not found")
    stmt = select(Ticket).where(Ticket.violation_id == ticket.violation_id)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="A ticket has already been issued for this violation")

    new_ticket = Ticket(**ticket.model_dump())
    if new_ticket.issue_date.tzinfo is None:
        new_ticket.issue_date = new_ticket.issue_date.replace(tzinfo=timezone.utc)
    if new_ticket.due_date.tzinfo is None:
        new_ticket.due_date = new_ticket.due_date.replace(tzinfo=timezone.utc)

    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket

@router.get("/tickets")
async def get_all_tickets(session: AsyncSession = Depends(get_db)):
    return (await session.execute(select(Ticket))).scalars().all()

@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, status_update: dict, session: AsyncSession = Depends(get_db)):
    new_status = status_update.get("ticket_status", "").upper()
    if new_status not in ["UNPAID", "PAID", "OVERDUE", "DISMISSED"]:
        raise HTTPException(status_code=400, detail="Status must be UNPAID, PAID, OVERDUE, or DISMISSED")
        
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.ticket_status = new_status
    await session.commit()
    await session.refresh(ticket)
    return ticket

@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await session.delete(ticket)
    await session.commit()
    return None

# ---------------------------------------------------------
# APPEALS & DISPUTES
# ---------------------------------------------------------

@router.post("/appeals", status_code=status.HTTP_201_CREATED)
async def file_appeal(appeal: AppealBase, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, appeal.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Cannot file appeal: Ticket ID not found")
    if ticket.ticket_status in ["PAID", "DISMISSED"]:
        raise HTTPException(status_code=400, detail=f"Cannot appeal a ticket that is already {ticket.ticket_status}")

    new_appeal = Appeal(**appeal.model_dump())
    if new_appeal.appeal_date.tzinfo is None:
        new_appeal.appeal_date = new_appeal.appeal_date.replace(tzinfo=timezone.utc)

    session.add(new_appeal)
    await session.commit()
    await session.refresh(new_appeal)
    return new_appeal

@router.get("/appeals")
async def get_all_appeals(session: AsyncSession = Depends(get_db)):
    return (await session.execute(select(Appeal))).scalars().all()

@router.patch("/appeals/{appeal_id}/decision")
async def resolve_appeal(appeal_id: int, decision_update: dict, session: AsyncSession = Depends(get_db)):
    decision = decision_update.get("appeal_decision", "").upper()
    if decision not in ["PENDING", "APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Decision must be PENDING, APPROVED, or REJECTED")
        
    appeal = await session.get(Appeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
        
    appeal.appeal_decision = decision
    if decision == "APPROVED":
        ticket = await session.get(Ticket, appeal.ticket_id)
        if ticket:
            ticket.ticket_status = "DISMISSED"
            
    await session.commit()
    await session.refresh(appeal)
    return appeal

@router.delete("/appeals/{appeal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appeal(appeal_id: int, session: AsyncSession = Depends(get_db)):
    appeal = await session.get(Appeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    await session.delete(appeal)
    await session.commit()
    return None