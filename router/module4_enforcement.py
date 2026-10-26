from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import CameraBase, ViolationBase, CameraStatusUpdate
from db import get_db, Camera, Violation, Vehicle, User

router = APIRouter(prefix="/api/enforcement", tags=["Module 4: Enforcement & Violations"])

@router.post("/cameras", status_code=status.HTTP_201_CREATED)
async def create_camera(camera: CameraBase, session: AsyncSession = Depends(get_db)):
    stmt_duplicate = select(Camera).where(
        (Camera.intersection == camera.intersection) &
        (Camera.ip_address == camera.ip_address) &
        (Camera.operational_status == camera.operational_status)
    )
    if (await session.execute(stmt_duplicate)).scalars().first():
        raise HTTPException(status_code=400, detail="An exact copy of this camera record already exists")
    stmt_ip = select(Camera).where(Camera.ip_address == camera.ip_address)
    if (await session.execute(stmt_ip)).scalars().first():
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

@router.get("/cameras/inactive")
async def get_inactive_cameras(session: AsyncSession = Depends(get_db)):
    stmt = select(Camera).where(Camera.operational_status == "INACTIVE")
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/locations/{intersection}/cameras/inactive")
async def get_inactive_cameras_by_location(intersection: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Camera).where(
        (Camera.operational_status == "INACTIVE") & 
        (Camera.intersection == intersection)
    )
    cameras = (await session.execute(stmt)).scalars().all()
    if not cameras:
        raise HTTPException(status_code=404, detail="no inactive cameras found")
    return cameras

@router.patch("/cameras/{camera_id}/status")
async def update_camera_status(camera_id: int, status_update: CameraStatusUpdate, session: AsyncSession = Depends(get_db)):
    new_status = status_update.operational_status.upper()
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

@router.post("/violations", status_code=status.HTTP_201_CREATED)
async def log_violation(violation: ViolationBase, session: AsyncSession = Depends(get_db)):
    if violation.violation_time.tzinfo is None:
        violation.violation_time = violation.violation_time.replace(tzinfo=timezone.utc)

    stmt_duplicate = select(Violation).where(
        (Violation.rules_broken == violation.rules_broken) &
        (Violation.violation_time == violation.violation_time) &
        (Violation.img_link == violation.img_link) &
        (Violation.plate_no == violation.plate_no) &
        (Violation.camera_id == violation.camera_id)
    )
    if (await session.execute(stmt_duplicate)).scalars().first():
        raise HTTPException(status_code=400, detail="An exact copy of this violation record already exists")

    camera = await session.get(Camera, violation.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # NEW: Reject violations if the camera is not active
    if camera.operational_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Cannot log violation: Camera is inactive or under maintenance")

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
        await session.flush() 

    new_violation = Violation(**violation.model_dump())
    new_violation.violation_time = violation.violation_time
    
    session.add(new_violation)
    await session.commit()
    await session.refresh(new_violation)
    return new_violation

@router.get("/violations")
async def get_all_violations(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Violation))
    return result.scalars().all()

@router.get("/locations/{intersection}/violations")
async def get_violations_by_location(intersection: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Violation).join(Camera).where(Camera.intersection == intersection)
    violations = (await session.execute(stmt)).scalars().all()
    if not violations:
        raise HTTPException(status_code=404, detail="no violations found")
    return violations

@router.get("/violations/{violation_id}/camera")
async def get_violation_camera(violation_id: int, session: AsyncSession = Depends(get_db)):
    violation = await session.get(Violation, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
        
    camera = await session.get(Camera, violation.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera associated with this violation not found")
        
    return camera

@router.get("/vehicles/{plate_no}/violations")
async def get_vehicle_violations(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Violation).where(Violation.plate_no == plate_no)
    violations = (await session.execute(stmt)).scalars().all()
    if not violations:
        raise HTTPException(status_code=404, detail="no violation for the given plate_no")
    return violations

@router.delete("/violations/{violation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_violation(violation_id: int, session: AsyncSession = Depends(get_db)):
    violation = await session.get(Violation, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    await session.delete(violation)
    await session.commit()
    return None

@router.get("/violations/plate/{plate_no}/user")
async def get_user_from_violation_plate(plate_no: str, session: AsyncSession = Depends(get_db)):
    """Query user info from plate no in violations"""
    stmt = select(User).join(Vehicle, User.user_id == Vehicle.user_id)\
                       .join(Violation, Vehicle.plate_no == Violation.plate_no)\
                       .where(Violation.plate_no == plate_no)
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="No registered user found for this violation's vehicle")
    return user