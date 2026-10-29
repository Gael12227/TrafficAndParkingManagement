from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import TicketBase, AppealBase, UserBase, TicketStatusUpdate, AppealDecisionUpdate
from db import User, Vehicle, Violation, Ticket, Appeal, get_db

router = APIRouter(prefix="/api/ticketing", tags=["Module 5: Ticketing & Appeals"])

# ---------------------------------------------------------
# TICKETING CRUD & PAYMENTS
# ---------------------------------------------------------

@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def issue_ticket(ticket: TicketBase, session: AsyncSession = Depends(get_db)):
    # 1. Enforce chronological date constraint
    if ticket.due_date <= ticket.issue_date:
        raise HTTPException(status_code=400, detail="Due date must be strictly after the issue date")
        
    violation = await session.get(Violation, ticket.violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Cannot issue ticket: Violation ID not found")
        
    stmt = select(Ticket).where(Ticket.violation_id == ticket.violation_id)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="A ticket has already been issued for this violation")

    new_ticket = Ticket(**ticket.model_dump())
    new_ticket.ticket_status = "PENDING" 
    
    if new_ticket.issue_date.tzinfo is None:
        new_ticket.issue_date = new_ticket.issue_date.replace(tzinfo=timezone.utc)
    if new_ticket.due_date.tzinfo is None:
        new_ticket.due_date = new_ticket.due_date.replace(tzinfo=timezone.utc)

    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket

@router.patch("/tickets/{ticket_id}/pay")
async def pay_ticket(ticket_id: int, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.ticket_status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Ticket is already {ticket.ticket_status}")
        
    ticket.ticket_status = "PAID"
    await session.commit()
    await session.refresh(ticket)
    return ticket

@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int, 
    status_update: TicketStatusUpdate, 
    session: AsyncSession = Depends(get_db)
):
    new_status = status_update.ticket_status.upper()
    if new_status not in ["PAID", "NULLIFIED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Status must be PAID, NULLIFIED, or PENDING")
        
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.ticket_status = new_status
    await session.commit()
    await session.refresh(ticket)
    return ticket

@router.get("/tickets")
async def get_all_tickets(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Ticket))
    return result.scalars().all()

# APPEALS & DISPUTES

@router.post("/appeals", status_code=status.HTTP_201_CREATED)
async def file_appeal(appeal: AppealBase, session: AsyncSession = Depends(get_db)):
    ticket = await session.get(Ticket, appeal.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Cannot file appeal: Ticket ID not found")
        
    # Prevent appealing a resolved ticket
    if ticket.ticket_status in ["PAID", "NULLIFIED"]:
        raise HTTPException(status_code=400, detail=f"Cannot appeal a ticket that is {ticket.ticket_status}")

    new_appeal = Appeal(**appeal.model_dump())
    new_appeal.appeal_decision = "PENDING"
    
    if new_appeal.appeal_date.tzinfo is None:
        new_appeal.appeal_date = new_appeal.appeal_date.replace(tzinfo=timezone.utc)

    session.add(new_appeal)
    await session.commit()
    await session.refresh(new_appeal)
    return new_appeal

@router.patch("/appeals/{appeal_id}/decision")
async def resolve_appeal(
    appeal_id: int, 
    decision_update: AppealDecisionUpdate, 
    session: AsyncSession = Depends(get_db)
):
    decision = decision_update.appeal_decision.upper()
    if decision not in ["ACCEPTED", "REJECTED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Decision must be ACCEPTED, REJECTED, or PENDING")
        
    appeal = await session.get(Appeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
        
    appeal.appeal_decision = decision
    if decision == "ACCEPTED":
        ticket = await session.get(Ticket, appeal.ticket_id)
        if ticket:
            ticket.ticket_status = "NULLIFIED"
            
    await session.commit()
    await session.refresh(appeal)
    return appeal

# USER-SPECIFIC CROSS-TABLE QUERIES

@router.get("/tickets/{ticket_id}/user")
async def get_user_from_ticket(ticket_id: int, session: AsyncSession = Depends(get_db)):
    """Query user info from violation no in tickets"""
    stmt = select(User).join(Vehicle, User.user_id == Vehicle.user_id)\
                       .join(Violation, Vehicle.plate_no == Violation.plate_no)\
                       .join(Ticket, Violation.violation_id == Ticket.violation_id)\
                       .where(Ticket.ticket_id == ticket_id)
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this ticket")
    return user

@router.get("/users/{gmail}/tickets/pending")
async def get_user_pending_tickets(gmail: str, session: AsyncSession = Depends(get_db)):
    """Pending tickets of a user"""
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Ticket).join(Violation).join(Vehicle)\
                         .where((Vehicle.user_id == user.user_id) & (Ticket.ticket_status == "PENDING"))
    tickets = (await session.execute(stmt)).scalars().all()
    if not tickets:
        raise HTTPException(status_code=404, detail="No pending tickets found for this user")
    return tickets

@router.get("/users/{gmail}/fines/pending")
async def get_user_total_pending_fines(gmail: str, session: AsyncSession = Depends(get_db)):
    """Total valid pending fine amount of a user"""
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(func.sum(Ticket.fine_amt)).join(Violation).join(Vehicle)\
                                            .where((Vehicle.user_id == user.user_id) & (Ticket.ticket_status == "PENDING"))
    total = (await session.execute(stmt)).scalar() or 0.00
    return {"gmail": gmail, "total_pending_fine": float(total)}

@router.get("/users/{gmail}/appeals")
async def get_user_appeals(gmail: str, session: AsyncSession = Depends(get_db)):
    """Appeal info of a user"""
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Appeal).join(Ticket).join(Violation).join(Vehicle).where(Vehicle.user_id == user.user_id)
    appeals = (await session.execute(stmt)).scalars().all()
    if not appeals:
        raise HTTPException(status_code=404, detail="No appeals found for this user")
    return appeals

@router.get("/users/{gmail}/appeals/pending")
async def get_user_pending_appeals(gmail: str, session: AsyncSession = Depends(get_db)):
    """Pending appeal hearings info of a user"""
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Appeal).join(Ticket).join(Violation).join(Vehicle)\
                         .where((Vehicle.user_id == user.user_id) & (Appeal.appeal_decision == "PENDING"))
    appeals = (await session.execute(stmt)).scalars().all()
    if not appeals:
        raise HTTPException(status_code=404, detail="No pending appeals found for this user")
    return appeals

@router.get("/appeals/pending")
async def get_all_pending_appeals(session: AsyncSession = Depends(get_db)):
    stmt = select(Appeal).where(Appeal.appeal_decision == "PENDING")
    appeals = (await session.execute(stmt)).scalars().all()
    if not appeals:
        raise HTTPException(status_code=404, detail="no pending appeals found")
    return appeals
