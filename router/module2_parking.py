from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import ParkingZoneBase, ParkingZoneResponse, ParkingSlotBase, ParkingSlotResponse, SlotStatusUpdate
from db import get_db, ParkingZone, ParkingSlot

router = APIRouter(prefix="/api/v1/parking", tags=["Module 2: Smart Parking Infrastructure"])

# 1. INSERT: Add a newly built parking zone
@router.post("/zones", response_model=ParkingZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_zone(zone: ParkingZoneBase, session: AsyncSession = Depends(get_db)):
    new_zone = ParkingZone(
        location_name=zone.location_name,
        total_cap=zone.total_cap,
        base_rate=zone.base_rate
    )
    session.add(new_zone)
    await session.commit()
    await session.refresh(new_zone)
    return new_zone

# 2. UPDATE: Admin manually changes slot status
@router.patch("/slots/{slot_id}/status", response_model=ParkingSlotResponse)
async def update_slot_status(slot_id: int, update_data: SlotStatusUpdate, session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingSlot).where(ParkingSlot.slot_id == slot_id)
    result = await session.execute(stmt)
    slot = result.scalars().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    slot.status = update_data.status
    await session.commit()
    await session.refresh(slot)
    return slot

# 3. DELETE: Remove a decommissioned parking slot
@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_slot(slot_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingSlot).where(ParkingSlot.slot_id == slot_id)
    result = await session.execute(stmt)
    slot = result.scalars().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
        
    await session.delete(slot)
    await session.commit()
    return None

# 4. SELECT (1): View all parking zones
@router.get("/zones", response_model=list[ParkingZoneResponse])
async def get_all_zones(session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingZone)
    result = await session.execute(stmt)
    return result.scalars().all()

# 5. SELECT (2): View all slots in a specific zone
@router.get("/zones/{zone_id}/slots", response_model=list[ParkingSlotResponse])
async def get_zone_slots(zone_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingSlot).where(ParkingSlot.zone_id == zone_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# 6. SELECT (3): View all 'FREE' slots globally
@router.get("/slots/free", response_model=list[ParkingSlotResponse])
async def get_all_free_slots(session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingSlot).where(ParkingSlot.status == 'FREE')
    result = await session.execute(stmt)
    return result.scalars().all()

# 7. SELECT (4): Show total city parking capacity (Aggregate)
@router.get("/capacity/total")
async def get_total_capacity(session: AsyncSession = Depends(get_db)):
    stmt = select(func.sum(ParkingZone.total_cap))
    result = await session.execute(stmt)
    total = result.scalar() or 0
    return {"total_city_capacity": total}

# 8. SELECT (5): List all zones sorted by hourly rate (ORDER BY)
@router.get("/zones/rates/sorted", response_model=list[ParkingZoneResponse])
async def get_zones_sorted_by_rate(session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingZone).order_by(ParkingZone.base_rate.desc())
    result = await session.execute(stmt)
    return result.scalars().all()