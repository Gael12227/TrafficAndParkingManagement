from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Use only the updated schemas
from schemas import ReservationCreate, ReservationResponse
from db import get_db, Reservation, ParkingSlot, ParkingZone, User, Vehicle

router = APIRouter(prefix="/api/booking", tags=["Module 3: Booking & Revenue"])

@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(reservation: ReservationCreate, session: AsyncSession = Depends(get_db)):
    if reservation.start_time >= reservation.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")

    user = await session.get(User, reservation.user_id)
    vehicle = await session.get(Vehicle, reservation.plate_no)
    slot = await session.get(ParkingSlot, (reservation.zone_id, reservation.slot_id))

    if not user or not vehicle or not slot:
        raise HTTPException(status_code=404, detail="User, Vehicle, or Slot not found")

    if vehicle.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Vehicle does not belong to the requesting user")

    if slot.status == "UNDER MAINTENANCE":
        raise HTTPException(status_code=400, detail="Slot is currently under maintenance and cannot be booked")

    stmt_res = select(Reservation).where(
        (Reservation.zone_id == reservation.zone_id) &
        (Reservation.slot_id == reservation.slot_id) &
        (Reservation.start_time < reservation.end_time) &
        (Reservation.end_time > reservation.start_time)
    )
    if (await session.execute(stmt_res)).scalars().first():
        raise HTTPException(status_code=400, detail="Slot is already reserved for this timeframe")

    zone = await session.get(ParkingZone, slot.zone_id)
    
    # Strictly calculated internally
    duration_seconds = (reservation.end_time - reservation.start_time).total_seconds()
    duration_hours = duration_seconds / 3600.0
    calculated_cost = round(duration_hours * float(zone.base_rate), 2)

    new_reservation = Reservation(
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        total_cost=calculated_cost,
        zone_id=reservation.zone_id,
        slot_id=reservation.slot_id,
        plate_no=reservation.plate_no,
        user_id=reservation.user_id
    )

    session.add(new_reservation)
    slot.status = "RESERVED"
    
    await session.commit()
    await session.refresh(new_reservation)
    
    return new_reservation

@router.patch("/reservations/{res_id}/extend", response_model=ReservationResponse)
async def extend_reservation(res_id: int, new_end_time: datetime, session: AsyncSession = Depends(get_db)):
    reservation = await session.get(Reservation, res_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
        
    if new_end_time <= reservation.end_time:
        raise HTTPException(status_code=400, detail="New end time must be after the current end time")
        
    stmt_overlap = select(Reservation).where(
        (Reservation.zone_id == reservation.zone_id) &
        (Reservation.slot_id == reservation.slot_id) &
        (Reservation.res_id != res_id) & 
        (Reservation.start_time < new_end_time) &
        (Reservation.end_time > reservation.start_time)
    )
    if (await session.execute(stmt_overlap)).scalars().first():
        raise HTTPException(status_code=400, detail="Cannot extend: Slot is already reserved during the new timeframe")

    slot = await session.get(ParkingSlot, (reservation.zone_id, reservation.slot_id))
    zone = await session.get(ParkingZone, slot.zone_id)
    
    duration_seconds = (new_end_time - reservation.start_time).total_seconds()
    duration_hours = duration_seconds / 3600.0
    
    reservation.total_cost = round(duration_hours * float(zone.base_rate), 2)
    reservation.end_time = new_end_time
    
    await session.commit()
    await session.refresh(reservation)
    return reservation

@router.delete("/reservations/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(res_id: int, session: AsyncSession = Depends(get_db)):
    reservation = await session.get(Reservation, res_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
        
    slot = await session.get(ParkingSlot, (reservation.zone_id, reservation.slot_id))
    
    if slot and slot.status == "RESERVED":
        slot.status = "FREE"
        
    await session.delete(reservation)
    await session.commit()
    return None

# Updated to use ReservationResponse
@router.get("/reservations", response_model=list[ReservationResponse])
async def get_all_reservations(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Reservation))
    return result.scalars().all()

# Updated to use ReservationResponse
@router.get("/reservations/active", response_model=list[ReservationResponse])
async def get_active_reservations(session: AsyncSession = Depends(get_db)):
    current_time = datetime.now(timezone.utc)
    stmt = select(Reservation).where(
        (Reservation.start_time <= current_time) & (Reservation.end_time >= current_time)
    )
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/users/{user_id}/spent")
async def get_user_total_spent(user_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(func.sum(Reservation.total_cost)).where(Reservation.user_id == user_id)
    result = await session.execute(stmt)
    total = result.scalar() or 0.00
    return {"user_id": user_id, "total_spent": float(total)}

@router.get("/zones/{zone_id}/revenue")
async def get_zone_revenue(zone_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(func.sum(Reservation.total_cost)).where(Reservation.zone_id == zone_id)
    result = await session.execute(stmt)
    total = result.scalar() or 0.00
    return {"zone_id": zone_id, "total_revenue": float(total)}

# Updated to use ReservationResponse
@router.get("/users/{user_id}/reservations", response_model=list[ReservationResponse])
async def get_user_reservations(user_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(Reservation).where(Reservation.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# Updated to use ReservationResponse
@router.get("/vehicles/{plate_no}/reservations", response_model=list[ReservationResponse])
async def get_vehicle_reservations(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Reservation).where(Reservation.plate_no == plate_no)
    result = await session.execute(stmt)
    return result.scalars().all()