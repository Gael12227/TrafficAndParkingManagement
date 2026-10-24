from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from schemas import AppealRequest, AppealBase, TicketBase
from db import get_db, Ticket, Appeal, Violation, Vehicle

router = APIRouter(prefix="/api/v1/ticketing", tags=["Module 5: Ticketing & Appeals"])

# 1. INSERT: File a new appeal against a ticket
@router.post("/appeals", response_model=AppealBase, status_code=status.HTTP_201_CREATED)
async def submit_appeal(appeal: AppealRequest, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, appeal.ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.ticket_status == "PAID":
        raise HTTPException(status_code=400, detail="Cannot appeal a paid ticket")
    if ticket.ticket_status == "APPEALED":
        raise HTTPException(status_code=400, detail="Ticket is already under appeal")

    new_appeal = Appeal(
        reason_text=appeal.reason_text,
        appeal_date=datetime.now(),
        appeal_decision="PENDING",
        ticket_id=appeal.ticket_id
    )
    
    # Flag the ticket status to reflect the active dispute
    ticket.ticket_status = "APPEALED" 
    
    session.add(new_appeal)
    await session.commit()
    await session.refresh(new_appeal)
    
    return new_appeal

# 2. UPDATE: Pay a ticket (Change status from UNPAID to PAID)
@router.patch("/tickets/{ticket_id}/pay", response_model=TicketBase)
async def pay_ticket(ticket_id: int, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.ticket_status == "PAID":
        raise HTTPException(status_code=400, detail="Ticket is already paid")
    if ticket.ticket_status == "APPEALED":
        raise HTTPException(status_code=400, detail="Cannot pay a ticket currently under appeal")

    ticket.ticket_status = "PAID"
    await session.commit()
    await session.refresh(ticket)
    return ticket

# 3. DELETE: Withdraw an appeal and revert the ticket status
@router.delete("/appeals/{appeal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_appeal(appeal_id: int, session: AsyncSession = Depends(get_db)):
    appeal = await session.get(Appeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
        
    ticket = await session.get(Ticket, appeal.ticket_id)
    if ticket and ticket.ticket_status == "APPEALED":
        ticket.ticket_status = "UNPAID"  # Revert status so it can be paid
        
    await session.delete(appeal)
    await session.commit()
    return None

# 4. SELECT (1): Show all unpaid tickets for a specific user across their entire fleet
@router.get("/users/{user_id}/tickets/unpaid", response_model=list[TicketBase])
async def get_user_unpaid_tickets(user_id: int, session: AsyncSession = Depends(get_db)):
    stmt = (
        select(Ticket)
        .join(Violation, Ticket.violation_id == Violation.violation_id)
        .join(Vehicle, Violation.plate_no == Vehicle.plate_no)
        .where((Vehicle.user_id == user_id) & (Ticket.ticket_status == "UNPAID"))
    )
    result = await session.execute(stmt)
    return result.scalars().all()

# 5. SELECT (2): List all pending appeals for admin review
@router.get("/appeals/pending", response_model=list[AppealBase])
async def get_pending_appeals(session: AsyncSession = Depends(get_db)):
    stmt = select(Appeal).where(Appeal.appeal_decision == "PENDING")
    result = await session.execute(stmt)
    return result.scalars().all()

# 6. SELECT (3): Calculate the total unpaid fine amount across the database
@router.get("/tickets/unpaid/total")
async def get_total_unpaid_fines(session: AsyncSession = Depends(get_db)):
    stmt = select(func.sum(Ticket.fine_amt)).where(Ticket.ticket_status == "UNPAID")
    result = await session.execute(stmt)
    total = result.scalar() or 0.00
    return {"status_filter": "UNPAID", "total_outstanding_revenue": float(total)}

# 7. SELECT (4): View all appeals filed against a specific ticket
@router.get("/tickets/{ticket_id}/appeals", response_model=list[AppealBase])
async def get_ticket_appeals(ticket_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(Appeal).where(Appeal.ticket_id == ticket_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# 8. SELECT (5): List all tickets in the system
@router.get("/tickets", response_model=list[TicketBase])
async def get_all_tickets(session: AsyncSession = Depends(get_db)):
    stmt = select(Ticket)
    result = await session.execute(stmt)
    return result.scalars().all()