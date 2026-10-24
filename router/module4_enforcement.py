from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from schemas import CameraBase, CameraResponse, ViolationRequest, ViolationBase, TicketBase
from db import get_db, Camera, Violation, Ticket, Vehicle

router = APIRouter(prefix="/api/v1/enforcement", tags=["Module 4: Traffic Enforcement"])

# 1. INSERT: Log a new violation and automatically generate a Ticket
@router.post("/violations", status_code=status.HTTP_201_CREATED)
async def report_violation(violation: ViolationRequest, session: AsyncSession = Depends(get_db)):
    vehicle = await session.get(Vehicle, violation.plate_no)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found in registry")

    camera = await session.get(Camera, violation.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera ID not found")

    new_violation = Violation(
        rules_broken=violation.rules_broken,
        violation_time=datetime.now(),
        img_link=violation.img_link,
        plate_no=violation.plate_no,
        camera_id=violation.camera_id
    )
    session.add(new_violation)
    await session.flush() # Flush to acquire violation_id for 1:1 ticket generation

    # Automated logic to calculate fine based on the rule broken
    fine = 50.00
    if violation.rules_broken.lower() == "speeding":
        fine = 100.00
    elif violation.rules_broken.lower() == "red_light_violation":
        fine = 150.00

    new_ticket = Ticket(
        fine_amt=fine,
        issue_date=datetime.now(),
        due_date=datetime.now() + timedelta(days=30),
        ticket_status="UNPAID",
        violation_id=new_violation.violation_id
    )
    session.add(new_ticket)
    await session.commit()
    
    return {"message": "Violation logged and e-Challan generated", "violation_id": new_violation.violation_id}

# 2. UPDATE: Change a camera's operational status
@router.patch("/cameras/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(camera_id: int, new_status: str, session: AsyncSession = Depends(get_db)):
    camera = await session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    camera.operational_status = new_status.upper()
    await session.commit()
    await session.refresh(camera)
    return camera

# 3. DELETE: Delete a violation logged in error (Cascades to the Ticket)
@router.delete("/violations/{violation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_violation(violation_id: int, session: AsyncSession = Depends(get_db)):
    violation = await session.get(Violation, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
        
    # Deleting the violation automatically deletes the associated ticket due to the CASCADE constraint
    await session.delete(violation)
    await session.commit()
    return None

# 4. SELECT (1): View all violations for a specific intersection (via Camera)
@router.get("/cameras/{camera_id}/violations", response_model=list[ViolationBase])
async def get_camera_violations(camera_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(Violation).where(Violation.camera_id == camera_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# 5. SELECT (2): Count the total number of violations captured by a specific camera
@router.get("/cameras/{camera_id}/violations/count")
async def count_camera_violations(camera_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(func.count()).where(Violation.camera_id == camera_id)
    result = await session.execute(stmt)
    count = result.scalar() or 0
    return {"camera_id": camera_id, "total_violations_captured": count}

# 6. SELECT (3): Find the most common traffic rule broken
@router.get("/violations/frequent-rule")
async def get_most_frequent_rule(session: AsyncSession = Depends(get_db)):
    stmt = select(Violation.rules_broken, func.count(Violation.violation_id).label("total"))\
        .group_by(Violation.rules_broken)\
        .order_by(desc("total")).limit(1)
    
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        return {"message": "No violations recorded yet"}
    return {"most_common_rule": row[0], "occurrences": row[1]}

# 7. SELECT (4): List all active cameras
@router.get("/cameras/active", response_model=list[CameraResponse])
async def get_active_cameras(session: AsyncSession = Depends(get_db)):
    stmt = select(Camera).where(Camera.operational_status == 'ACTIVE')
    result = await session.execute(stmt)
    return result.scalars().all()

# 8. SELECT (5): Retrieve a comprehensive violation history for a specific vehicle
@router.get("/violations/vehicle/{plate_no}", response_model=list[ViolationBase])
async def get_vehicle_violations(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Violation).where(Violation.plate_no == plate_no)
    result = await session.execute(stmt)
    return result.scalars().all()