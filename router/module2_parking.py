from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import ParkingZoneBase, ParkingSlotBase, SensorBase, SlotStatusUpdate
from db import get_db, ParkingZone, ParkingSlot, Sensor, Reservation

router = APIRouter(prefix="/api/parking", tags=["Module 2: Parking Zones & Slots"])

# SYSTEM-WIDE CAPACITY & RATE ROUTES

@router.get("/capacity/total")
async def get_total_system_capacity(session: AsyncSession = Depends(get_db)):
    stmt_total = select(func.count()).select_from(ParkingSlot)
    total_slots = (await session.execute(stmt_total)).scalar() or 0
    
    stmt_free = select(func.count()).select_from(ParkingSlot).where(ParkingSlot.status == "FREE")
    total_free = (await session.execute(stmt_free)).scalar() or 0
    
    return {
        "system_total_capacity": total_slots,
        "system_free_slots": total_free,
        "system_occupied_or_reserved": total_slots - total_free
    }

@router.get("/zones/rates/sorted")
async def get_zones_sorted_by_rate(session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingZone).order_by(ParkingZone.base_rate.desc())
    zones = (await session.execute(stmt)).scalars().all()
    
    result = []
    for zone in zones:
        stmt_cap = select(func.count()).select_from(ParkingSlot).where(ParkingSlot.zone_id == zone.zone_id)
        actual_cap = (await session.execute(stmt_cap)).scalar() or 0
        
        result.append({
            "zone_id": zone.zone_id,
            "location_name": zone.location_name,
            "base_rate": zone.base_rate,
            "true_capacity": actual_cap
        })
        
    return result

# PARKING ZONES CRUD

@router.post("/zones", status_code=status.HTTP_201_CREATED)
async def create_zone(zone_in: ParkingZoneBase, session: AsyncSession = Depends(get_db)):
    new_zone = ParkingZone(**zone_in.model_dump())
    session.add(new_zone)
    await session.flush() 

    current_time = datetime.now(timezone.utc)
    for i in range(1, new_zone.total_cap + 1):
        generated_sensor_id = f"Z{new_zone.zone_id}-SLOT{i}"
        new_sensor = Sensor(
            sensor_id=generated_sensor_id,
            manufacture="Auto-Generated",
            date_of_manufacture=current_time,
            model="Generic-V1",
            status="active"
        )
        session.add(new_sensor)
        new_slot = ParkingSlot(
            zone_id=new_zone.zone_id,
            slot_id=i,
            sensor_id=generated_sensor_id,
            status="FREE"
        )
        session.add(new_slot)

    await session.commit()
    await session.refresh(new_zone)
    
    return new_zone

@router.get("/zones/{zone_id}")
async def get_zone(zone_id: int, session: AsyncSession = Depends(get_db)):
    zone = await session.get(ParkingZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.get("/zones/{zone_id}/capacity")
async def get_zone_capacity(zone_id: int, session: AsyncSession = Depends(get_db)):
    zone = await session.get(ParkingZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    stmt_total = select(func.count()).select_from(ParkingSlot).where(ParkingSlot.zone_id == zone_id)
    actual_total_slots = (await session.execute(stmt_total)).scalar() or 0
    
    stmt_free = select(func.count()).select_from(ParkingSlot).where(
        (ParkingSlot.zone_id == zone_id) & (ParkingSlot.status == "FREE")
    )
    free_slots = (await session.execute(stmt_free)).scalar() or 0
    
    return {
        "zone_id": zone_id,
        "location_name": zone.location_name,
        "total_capacity": actual_total_slots,
        "available_free_slots": free_slots
    }

@router.get("/zones/search/{location}")
async def search_zone_by_location(location: str, session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingZone).where(ParkingZone.location_name.ilike(f"%{location}%"))
    zones = (await session.execute(stmt)).scalars().all()
    if not zones:
        raise HTTPException(status_code=404, detail="No zones found matching this location")
    return zones

@router.get("/zones/{zone_id}/slots")
async def get_zone_slots(zone_id: int, status_filter: Optional[str] = None, session: AsyncSession = Depends(get_db)):
    zone = await session.get(ParkingZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone ID {zone_id} does not exist.")
        
    stmt = select(ParkingSlot).where(ParkingSlot.zone_id == zone_id)
    if status_filter:
        stmt = stmt.where(ParkingSlot.status == status_filter.upper())
        
    slots = (await session.execute(stmt)).scalars().all()
    
    if not slots:
        status_msg = f" with status '{status_filter.upper()}'" if status_filter else ""
        raise HTTPException(status_code=404, detail=f"No slots exist for Zone ID {zone_id}{status_msg}.")
        
    return slots

@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: int, session: AsyncSession = Depends(get_db)):
    zone = await session.get(ParkingZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await session.delete(zone)
    await session.commit()
    return None

# PARKING SLOTS CRUD & TELEMETRY

@router.post("/slots/release-expired-reservations")
async def release_expired_reservations(session: AsyncSession = Depends(get_db)):
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    stmt = select(Reservation).join(
        ParkingSlot, 
        (Reservation.zone_id == ParkingSlot.zone_id) & (Reservation.slot_id == ParkingSlot.slot_id)
    ).where(
        (ParkingSlot.status == "RESERVED") & 
        (Reservation.start_time <= one_hour_ago)
    )
    
    expired_reservations = (await session.execute(stmt)).scalars().all()
    freed_slots = []
    
    for res in expired_reservations:
        slot = await session.get(ParkingSlot, (res.zone_id, res.slot_id))
        slot.status = "FREE"
        freed_slots.append({"zone_id": slot.zone_id, "slot_id": slot.slot_id})
        
    await session.commit()
    return {"message": f"Released {len(freed_slots)} expired reservations.", "freed_slots": freed_slots}

@router.post("/slots", status_code=status.HTTP_201_CREATED)
async def create_parking_slot(slot: ParkingSlotBase, session: AsyncSession = Depends(get_db)):
    zone = await session.get(ParkingZone, slot.zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Parking Zone not found")
        
    stmt_max = select(func.max(ParkingSlot.slot_id)).where(ParkingSlot.zone_id == slot.zone_id)
    max_slot_id = (await session.execute(stmt_max)).scalar() or 0
    next_slot_id = max_slot_id + 1

    new_slot = ParkingSlot(
        zone_id=slot.zone_id,
        slot_id=next_slot_id,
        sensor_id=slot.sensor_id,
        status=slot.status
    )
    session.add(new_slot)
    zone.total_cap += 1 
    
    await session.commit()
    return new_slot

@router.get("/slots")
async def get_all_slots(status_filter: Optional[str] = None, session: AsyncSession = Depends(get_db)):
    stmt = select(ParkingSlot)
    if status_filter:
        stmt = stmt.where(ParkingSlot.status == status_filter.upper())
    return (await session.execute(stmt)).scalars().all()

@router.patch("/slots/{zone_id}/{slot_id}/status", response_model=ParkingSlotBase)
async def update_slot_status(
    zone_id: int, 
    slot_id: int, 
    status_update: SlotStatusUpdate, 
    session: AsyncSession = Depends(get_db)
):
    stmt = select(ParkingSlot).where(
        (ParkingSlot.zone_id == zone_id) & 
        (ParkingSlot.slot_id == slot_id)
    )
    slot = (await session.execute(stmt)).scalars().first()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
        
    slot.status = status_update.status
    await session.commit()
    await session.refresh(slot)
    return slot

@router.delete("/slots/{zone_id}/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(zone_id: int, slot_id: int, session: AsyncSession = Depends(get_db)):
    slot = await session.get(ParkingSlot, (zone_id, slot_id))
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    zone = await session.get(ParkingZone, zone_id)
    if zone:
        zone.total_cap -= 1
        
    await session.delete(slot)
    await session.commit()
    return None

# SENSORS CRUD

@router.post("/sensors", status_code=status.HTTP_201_CREATED)
async def create_sensor(sensor: SensorBase, session: AsyncSession = Depends(get_db)):
    stmt = select(Sensor).where(Sensor.sensor_id == sensor.sensor_id)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="Sensor ID already exists")
    
    new_sensor = Sensor(**sensor.model_dump())
    session.add(new_sensor)
    await session.commit()
    return new_sensor

@router.get("/sensors")
async def get_all_sensors(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Sensor))
    return result.scalars().all()

@router.delete("/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(sensor_id: str, session: AsyncSession = Depends(get_db)):
    sensor = await session.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    await session.delete(sensor)
    await session.commit()
    return None
