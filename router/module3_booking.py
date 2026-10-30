from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import ReservationCreate, ReservationResponse
from db import get_db, Reservation, ParkingSlot, ParkingZone, User, Vehicle

router = APIRouter(prefix="/api/booking", tags=["Module 3: Booking & Revenue"])

@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(reservation: ReservationCreate, session: AsyncSession = Depends(get_db)):
    # 1. Verify the vehicle exists
    vehicle = await session.get(Vehicle, reservation.plate_no)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found. Please register the vehicle first.")

    # 2. Check if the vehicle already has an overlapping reservation
    stmt_overlap = select(Reservation).where(
        (Reservation.plate_no == reservation.plate_no) &
        (Reservation.end_time > reservation.start_time) &
        (Reservation.start_time < reservation.end_time)
    )
    if (await session.execute(stmt_overlap)).scalars().first():
        raise HTTPException(status_code=400, detail="This vehicle already has an active reservation during this time.")

    # 3. Verify the slot exists and belongs to the zone
    stmt_slot = select(ParkingSlot).where(
        (ParkingSlot.zone_id == reservation.zone_id) & 
        (ParkingSlot.slot_id == reservation.slot_id)
    )
    slot = (await session.execute(stmt_slot)).scalars().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found in the specified zone.")

    # 4. Check if the slot itself is already booked during this time
    stmt_slot_booked = select(Reservation).where(
        (Reservation.zone_id == reservation.zone_id) &
        (Reservation.slot_id == reservation.slot_id) &
        (Reservation.end_time > reservation.start_time) &
        (Reservation.start_time < reservation.end_time)
    )
    if (await session.execute(stmt_slot_booked)).scalars().first():
        raise HTTPException(status_code=400, detail="This slot is already reserved for the requested time period.")

    # 5. Calculate cost (Duration in hours * zone base rate)
    zone = await session.get(ParkingZone, reservation.zone_id)
    duration_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    calculated_cost = round(duration_hours * float(zone.base_rate), 2)

    # 6. Create the reservation and mark the slot as RESERVED
    new_reservation = Reservation(
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        total_cost=calculated_cost,
        zone_id=reservation.zone_id,
        slot_id=reservation.slot_id,
        plate_no=reservation.plate_no
    )
    session.add(new_reservation)

    # 7. Update slot status → RESERVED so capacity/overview counts it correctly
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

@router.get("/users/{gmail}/spent")
async def get_user_total_spent(gmail: str, session: AsyncSession = Depends(get_db)):
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stmt = (
        select(func.sum(Reservation.total_cost))
        .join(Vehicle, Vehicle.plate_no == Reservation.plate_no)
        .where(Vehicle.user_id == user.user_id)
    )
    result = await session.execute(stmt)
    total = result.scalar() or 0.00
    
    return {"gmail": gmail, "total_spent": float(total)}

@router.get("/zones/{zone_id}/revenue")
async def get_zone_revenue(zone_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(func.sum(Reservation.total_cost)).where(Reservation.zone_id == zone_id)
    result = await session.execute(stmt)
    total = result.scalar() or 0.00
    return {"zone_id": zone_id, "total_revenue": float(total)}

# Updated to use ReservationResponse
@router.get("/users/{gmail}/reservations", response_model=list[ReservationResponse])
async def get_user_reservations(gmail: str, session: AsyncSession = Depends(get_db)):
    user = (await session.execute(select(User).where(User.gmail == gmail))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stmt = (
        select(Reservation)
        .join(Vehicle, Vehicle.plate_no == Reservation.plate_no)
        .where(Vehicle.user_id == user.user_id)
    )
    reservations = (await session.execute(stmt)).scalars().all()
    if not reservations:
        raise HTTPException(status_code=404, detail="No reservations found for this user")
    return reservations

# Updated to use ReservationResponse
@router.get("/vehicles/{plate_no}/reservations", response_model=list[ReservationResponse])
async def get_vehicle_reservations(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Reservation).where(Reservation.plate_no == plate_no)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/reservations/plate/{plate_no}/user")
async def get_user_from_reservation_plate(plate_no: str, session: AsyncSession = Depends(get_db)):
    """Query user info from plate no in reservations"""
    stmt = select(User).join(Vehicle, User.user_id == Vehicle.user_id)\
                       .join(Reservation, Vehicle.plate_no == Reservation.plate_no)\
                       .where(Reservation.plate_no == plate_no)
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="No registered user found for this reservation's vehicle")
    return user