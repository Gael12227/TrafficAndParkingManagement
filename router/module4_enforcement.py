from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Using the correct schema names available in your schemas.py
from schemas import CameraBase, ViolationBase
from db import get_db, Camera, Violation, Vehicle

# Removed the /v1 prefix to match your frontend integration architecture
router = APIRouter(prefix="/api/v1/enforcement", tags=["Module 4: Enforcement & Violations"])

# ---------------------------------------------------------
# CAMERAS CRUD & TELEMETRY
# ---------------------------------------------------------

@router.post("/cameras", status_code=status.HTTP_201_CREATED)
async def create_camera(camera: CameraBase, session: AsyncSession = Depends(get_db)):
    # Prevent database crash: IP addresses must be unique according to db.py
    stmt = select(Camera).where(Camera.ip_address == camera.ip_address)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="A camera with this IP address already exists")
        
    new_camera = Camera(**camera.model_dump())
    session.add(new_camera)
    await session.commit()
    await session.refresh(new_camera)
    return new_camera

@router.get("/cameras")
async def get_all_cameras(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Camera))
    return result.scalars().all()

@router.patch("/cameras/{camera_id}/status")
async def update_camera_status(camera_id: int, status_update: dict, session: AsyncSession = Depends(get_db)):
    new_status = status_update.get("operational_status", "").upper()
    if new_status not in ["ACTIVE", "INACTIVE", "MAINTENANCE"]:
        raise HTTPException(status_code=400, detail="Status must be ACTIVE, INACTIVE, or MAINTENANCE")
        
    camera = await session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    camera.operational_status = new_status
    await session.commit()
    await session.refresh(camera)
    return camera

@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, session: AsyncSession = Depends(get_db)):
    camera = await session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    await session.delete(camera)
    await session.commit()
    return None

# ---------------------------------------------------------
# VIOLATIONS LOGGING & RETRIEVAL
# ---------------------------------------------------------

@router.post("/violations", status_code=status.HTTP_201_CREATED)
async def log_violation(violation: ViolationBase, session: AsyncSession = Depends(get_db)):
    # 1. Verify camera exists
    camera = await session.get(Camera, violation.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # 2. Prevent Foreign Key Crash: Auto-register unseen plates
    # If a camera catches a car not in the database, attempting to log a violation 
    # will cause a foreign key constraint failure. We must auto-register it as UNCLAIMED.
    vehicle = await session.get(Vehicle, violation.plate_no)
    if not vehicle:
        new_vehicle = Vehicle(
            plate_no=violation.plate_no,
            make="UNKNOWN",
            model="UNKNOWN",
            colour="UNKNOWN",
            reg_status="UNCLAIMED",
            user_id=None
        )
        session.add(new_vehicle)
        await session.flush() # Push to Oracle to establish the FK before logging the violation

    new_violation = Violation(**violation.model_dump())
    
    # 3. Ensure timezone awareness
    if new_violation.violation_time.tzinfo is None:
        new_violation.violation_time = new_violation.violation_time.replace(tzinfo=timezone.utc)

    session.add(new_violation)
    await session.commit()
    await session.refresh(new_violation)
    return new_violation

@router.get("/violations")
async def get_all_violations(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Violation))
    return result.scalars().all()

@router.get("/vehicles/{plate_no}/violations")
async def get_vehicle_violations(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Violation).where(Violation.plate_no == plate_no)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.delete("/violations/{violation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_violation(violation_id: int, session: AsyncSession = Depends(get_db)):
    violation = await session.get(Violation, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    await session.delete(violation)
    await session.commit()
    return None